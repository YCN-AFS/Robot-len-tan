"""
╔══════════════════════════════════════════════════════════════╗
║           ROBOT LỄ TÂN — Q&A SYSTEM MODULE                 ║
║  Hệ thống hỏi đáp: Rule-based (L5) / RAG (L10)            ║
╚══════════════════════════════════════════════════════════════╝

Kiến trúc:
  - QASystem (ABC): Interface chung cho mọi engine Q&A
  - RuleBasedQA (Level 5): Tìm keyword → trả lời từ knowledge base
  - RAGBasedQA (Level 10): Retrieve context + LLM sinh câu trả lời
  - create_qa_system(): Factory function tạo engine phù hợp

RAG Flow:
  Khách hỏi → retrieve relevant chunks từ knowledge base
  → inject context vào LLM prompt → LLM sinh câu trả lời tự nhiên
  → nếu LLM lỗi → fallback về Rule-Based
"""

import asyncio
import logging
import time
from abc import ABC, abstractmethod
from typing import Optional, List, Tuple

# Suppress noisy HTTP/genai logs
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("google_genai.models").setLevel(logging.WARNING)
logging.getLogger("google_genai").setLevel(logging.WARNING)

from config import (
    QA_LEVEL,
    LLM_PROVIDER,
    LLM_API_KEY,
    LLM_MODEL_OPENAI,
    LLM_MODEL_GEMINI,
    LLM_TIMEOUT,
    LLM_MAX_TOKENS,
    LLM_SYSTEM_PROMPT,
    AI_LAB_DOCUMENT,
    KNOWLEDGE_BASE,
    QA_DEFAULT_ANSWER,
)

logger = logging.getLogger("qa_system")


# ═════════════════════════════════════════════
# QASystem — Abstract Base Class
# ═════════════════════════════════════════════
class QASystem(ABC):
    """Common interface for the Q&A system."""

    @abstractmethod
    async def get_answer(self, question: str) -> str:
        """Answer visitor questions."""
        ...

    @property
    @abstractmethod
    def level_name(self) -> str:
        """Q&A level name."""
        ...


# ═════════════════════════════════════════════
# Level 5 — Rule-Based Q&A
# ═════════════════════════════════════════════
class RuleBasedQA(QASystem):
    """Keyword-based Q&A system (Level 5).

    Tìm kiếm keyword trong câu hỏi → match với knowledge base.
    Ưu tiên keyword dài nhất (longest match = most specific).
    """

    def __init__(self, knowledge_base: Optional[dict] = None):
        self._kb = knowledge_base or KNOWLEDGE_BASE
        self._sorted_keys = sorted(self._kb.keys(), key=len, reverse=True)
        logger.info(
            f"📚 RuleBasedQA initialized with {len(self._kb)} knowledge base entries."
        )

    @property
    def level_name(self) -> str:
        return "Level 5 (Rule-Based)"

    async def get_answer(self, question: str) -> str:
        """Find answer by keyword matching.

        Thuật toán:
          1. Chuẩn hóa câu hỏi (lowercase)
          2. Tìm TẤT CẢ keyword có trong câu hỏi
          3. Ưu tiên keyword DÀI NHẤT (cụ thể nhất)
          4. Nếu cùng độ dài → ưu tiên keyword xuất hiện SỚM hơn
          5. Nếu không match → trả default
        """
        if not question or not question.strip():
            return QA_DEFAULT_ANSWER

        q_lower = question.lower().strip()
        logger.info(f'❓ [L5] Question: "{question}"')

        matches = []
        for keyword in self._sorted_keys:
            pos = q_lower.find(keyword.lower())
            if pos >= 0:
                matches.append((-len(keyword), pos, keyword))

        if matches:
            matches.sort()
            best_keyword = matches[0][2]
            answer = self._kb[best_keyword]
            logger.info(f"✅ [L5] Match keyword '{best_keyword}'")
            return answer

        logger.info("🤷 [L5] No keyword match → default answer")
        return QA_DEFAULT_ANSWER

    def retrieve_context(self, question: str, top_k: int = 5) -> List[Tuple[str, str]]:
        """Retrieve relevant knowledge entries for RAG context.

        Returns list of (keyword, answer) tuples ranked by relevance.
        """
        q_lower = question.lower().strip()
        matches = []
        for keyword in self._sorted_keys:
            pos = q_lower.find(keyword.lower())
            if pos >= 0:
                matches.append((-len(keyword), pos, keyword))

        matches.sort()
        results = []
        for _, _, kw in matches[:top_k]:
            results.append((kw, self._kb[kw]))
        return results

    def add_knowledge(self, keyword: str, answer: str):
        """Add an entry to the knowledge base."""
        self._kb[keyword] = answer
        self._sorted_keys = sorted(self._kb.keys(), key=len, reverse=True)
        logger.info(f"📝 Added keyword: '{keyword}'")


# ═════════════════════════════════════════════
# Level 10 — RAG-Based Q&A (Retrieve + LLM)
# ═════════════════════════════════════════════
class RAGBasedQA(QASystem):
    """RAG-based Q&A system (Level 10).

    Pipeline:
      1. Retrieve: tìm keyword-matched entries từ knowledge base
      2. Augment: ghép retrieved context + full document vào prompt
      3. Generate: LLM sinh câu trả lời tự nhiên dựa trên context

    Fallback về RuleBasedQA khi LLM thất bại / quota hết.
    """

    def __init__(
        self,
        provider: str = LLM_PROVIDER,
        api_key: str = LLM_API_KEY,
        model_openai: str = LLM_MODEL_OPENAI,
        model_gemini: str = LLM_MODEL_GEMINI,
    ):
        self._provider = provider.lower()
        self._api_key = api_key
        self._model_openai = model_openai
        self._model_gemini = model_gemini

        # Rule-based engine doubles as retriever + fallback
        self._retriever = RuleBasedQA()
        # Cooldown: skip LLM after quota hit
        self._quota_exhausted_until: float = 0.0
        self._COOLDOWN_SECS: int = 120

        if not self._api_key or self._api_key == "your-api-key-here":
            logger.warning(
                "⚠️ LLM API Key not configured! "
                "Will fallback to Rule-Based when needed."
            )

        logger.info(
            f"🧠 RAGBasedQA initialized: provider={self._provider}, "
            f"model={'GPT-4o-mini' if self._provider == 'openai' else 'Gemini'}"
        )

    @property
    def level_name(self) -> str:
        return f"Level 10 (RAG - {self._provider.title()})"

    def _build_rag_prompt(self, question: str) -> str:
        """Build the RAG prompt with retrieved context + full document.

        Structure:
          [System Prompt]
          [Full AI Lab Document — always included]
          [Retrieved KB entries — keyword-matched snippets]
          [User Question]
        """
        # Retrieve relevant KB entries
        retrieved = self._retriever.retrieve_context(question, top_k=5)

        # Build context block
        parts = [LLM_SYSTEM_PROMPT.strip()]

        # Always include the full document as primary knowledge source
        parts.append(f"\n--- KNOWLEDGE DOCUMENT ---\n{AI_LAB_DOCUMENT.strip()}")

        # Add retrieved snippets as extra hints
        if retrieved:
            snippets = "\n".join(
                f"- [{kw}]: {answer}" for kw, answer in retrieved
            )
            parts.append(
                f"\n--- RETRIEVED CONTEXT (most relevant) ---\n{snippets}"
            )
            logger.info(
                f"📎 [RAG] Retrieved {len(retrieved)} context chunks: "
                f"{[kw for kw, _ in retrieved]}"
            )
        else:
            logger.info("📎 [RAG] No keyword matches, using full document only")

        parts.append(f"\n--- VISITOR QUESTION ---\n{question}")

        return "\n".join(parts)

    async def get_answer(self, question: str) -> str:
        """RAG pipeline: Retrieve context → LLM generates answer.

        Falls back to Rule-Based if LLM fails.
        """
        if not question or not question.strip():
            return QA_DEFAULT_ANSWER

        logger.info(f'❓ [RAG] Question: "{question}"')

        # No API key → fallback immediately
        if not self._api_key or self._api_key == "your-api-key-here":
            logger.warning("⚠️ No API key → fallback Rule-Based")
            return await self._retriever.get_answer(question)

        # Quota cooldown → fallback
        if time.time() < self._quota_exhausted_until:
            remaining = int(self._quota_exhausted_until - time.time())
            logger.info(f"⏳ [RAG] Quota cooldown ({remaining}s left) → fallback")
            return await self._retriever.get_answer(question)

        try:
            # Build RAG prompt
            rag_prompt = self._build_rag_prompt(question)

            # Call LLM
            if self._provider == "openai":
                answer = await self._ask_openai(rag_prompt, question)
            elif self._provider == "gemini":
                answer = await self._ask_gemini(rag_prompt)
            else:
                logger.error(f"❌ Unsupported provider: {self._provider}")
                return await self._retriever.get_answer(question)

            if answer:
                logger.info(f'✅ [RAG] Answer: "{answer[:100]}..."')
                return answer
            else:
                logger.warning("⚠️ LLM returned empty → fallback")
                return await self._retriever.get_answer(question)

        except asyncio.TimeoutError:
            logger.warning("⏱️ LLM timeout → fallback Rule-Based")
            return await self._retriever.get_answer(question)
        except Exception as e:
            err_str = str(e)
            if "429" in err_str or "RESOURCE_EXHAUSTED" in err_str:
                self._quota_exhausted_until = time.time() + self._COOLDOWN_SECS
                logger.warning(
                    f"⚠️ [RAG] Quota hit → fallback for {self._COOLDOWN_SECS}s"
                )
            else:
                logger.error(f"❌ LLM error: {err_str[:120]} → fallback")
            return await self._retriever.get_answer(question)

    # ── OpenAI GPT ──────────────────────────
    async def _ask_openai(self, rag_prompt: str, question: str) -> Optional[str]:
        """Call OpenAI API with RAG prompt."""
        def _call():
            import openai
            client = openai.OpenAI(api_key=self._api_key)
            response = client.chat.completions.create(
                model=self._model_openai,
                messages=[
                    {"role": "system", "content": rag_prompt},
                    {"role": "user", "content": question},
                ],
                max_tokens=LLM_MAX_TOKENS,
                temperature=0.7,
            )
            return response.choices[0].message.content.strip()

        loop = asyncio.get_event_loop()
        return await asyncio.wait_for(
            loop.run_in_executor(None, _call), timeout=LLM_TIMEOUT
        )

    # ── Google Gemini ───────────────────────
    async def _ask_gemini(self, rag_prompt: str) -> Optional[str]:
        """Call Gemini API with RAG prompt."""
        def _call():
            from google import genai
            client = genai.Client(api_key=self._api_key)
            response = client.models.generate_content(
                model=self._model_gemini,
                contents=rag_prompt,
                config={
                    "max_output_tokens": LLM_MAX_TOKENS,
                    "temperature": 0.7,
                },
            )
            return response.text.strip()

        loop = asyncio.get_event_loop()
        return await asyncio.wait_for(
            loop.run_in_executor(None, _call), timeout=LLM_TIMEOUT
        )


# ═════════════════════════════════════════════
# Factory Function
# ═════════════════════════════════════════════
def create_qa_system(level: Optional[int] = None) -> QASystem:
    """Create appropriate Q&A engine by level.

    Args:
        level: 5 = Rule-Based, 10 = RAG (None → read from config)
    """
    if level is None:
        level = QA_LEVEL

    if level >= 10:
        logger.info("🧠 Initializing Q&A Level 10 (RAG)...")
        return RAGBasedQA()
    else:
        logger.info("📚 Initializing Q&A Level 5 (Rule-Based)...")
        return RuleBasedQA()


# ═════════════════════════════════════════════
# Test module
# ═════════════════════════════════════════════
async def _test():
    """Test Q&A system — both Rule-Based and RAG."""

    test_questions = [
        "Tell me about the AI Lab",
        "What is the Smart Things Club?",
        "Who manages this lab?",
        "What achievements does the lab have?",
        "What equipment do you have?",
        "What is the lab's vision for the future?",
        "How can I join the club?",
        "Tell me about Lac Hong University",
        "What is the WiFi password?",
        "What are the working hours?",
        "What competitions has the lab participated in?",
        "Can you tell me about the ROBOG competition?",
        "What is the weather today?",  # Out of scope
    ]

    # Test Level 5
    print("=" * 60)
    print("TEST LEVEL 5 — Rule-Based")
    print("=" * 60)
    qa5 = create_qa_system(level=5)
    print(f"Engine: {qa5.level_name}\n")
    for q in test_questions[:5]:
        answer = await qa5.get_answer(q)
        print(f"Q: {q}")
        print(f"A: {answer}\n")

    # Test Level 10 (RAG)
    if LLM_API_KEY and LLM_API_KEY != "your-api-key-here":
        print("=" * 60)
        print("TEST LEVEL 10 — RAG (LLM + Knowledge)")
        print("=" * 60)
        qa10 = create_qa_system(level=10)
        print(f"Engine: {qa10.level_name}\n")
        for q in test_questions:
            answer = await qa10.get_answer(q)
            print(f"Q: {q}")
            print(f"A: {answer}\n")
    else:
        print("\n⚠️ Skipping Level 10 (RAG) test — no API key configured")


if __name__ == "__main__":
    asyncio.run(_test())
