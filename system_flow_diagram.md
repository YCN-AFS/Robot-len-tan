# 🤖 Sơ đồ luồng xử lý — Robot Lễ Tân AI Lab

## 1. State Machine — Vòng đời chính

```mermaid
stateDiagram-v2
    [*] --> IDLE

    IDLE --> GREETING: 😊 Phát hiện khuôn mặt
    IDLE --> SHUTDOWN: 🛑 Ctrl+C

    GREETING --> LISTENING: 👋 Chào xong

    LISTENING --> ANSWERING: ✅ Nhận được câu hỏi
    LISTENING --> GOODBYE: 👋 Khách nói "bye"
    LISTENING --> GOODBYE: 🚫 Không nghe được gì

    ANSWERING --> LISTENING: 🔄 Hỏi tiếp?

    GOODBYE --> IDLE: 🔄 Chờ khách mới

    SHUTDOWN --> [*]
```

## 2. Luồng xử lý chính — End to End

```mermaid
flowchart TD
    A["🟢 IDLE<br/>Camera quét liên tục"] -->|Phát hiện khuôn mặt| B["👁️ VisionModule<br/>Phân tích giới tính + tuổi"]
    B --> C["👋 GREETING<br/>Chào theo giới tính<br/>+ Vẫy tay"]
    C --> D["🎙️ LISTENING<br/>NoiseHandler.robust_listen()"]

    D --> E{"STT thành công?"}
    E -->|✅ Có text| F{"Là lời tạm biệt?"}
    E -->|❌ Không nghe| G["🔄 Retry (tối đa 2 lần)<br/>Robot: 'Bạn nói lại được không?'"]

    G --> H{"Retry thành công?"}
    H -->|✅ Có| F
    H -->|❌ Không| I["🖐️ GESTURE FALLBACK<br/>Robot: 'Dùng cử chỉ tay nhé!'<br/>Camera nhận diện cử chỉ"]

    I --> J{"Nhận diện được?"}
    J -->|✅ 👍👌✊| K["Mapping cử chỉ → keyword<br/>VD: FIST → 'wifi'"]
    J -->|❌ Không| L["😢 Không giao tiếp được<br/>→ GOODBYE"]

    K --> M
    F -->|Không phải bye| M["🧠 ANSWERING<br/>QASystem.get_answer()"]
    F -->|"bye/goodbye"| N["👋 GOODBYE<br/>Chào tạm biệt → IDLE"]

    M --> O{"QA_LEVEL?"}
    O -->|"Level 5"| P["📚 Rule-Based<br/>Keyword matching"]
    O -->|"Level 10"| Q["🤖 RAG Pipeline"]

    Q --> Q1["1️⃣ RETRIEVE<br/>Tìm keyword trong Knowledge Base"]
    Q1 --> Q2["2️⃣ AUGMENT<br/>Ghép context + AI_LAB_DOCUMENT<br/>vào prompt"]
    Q2 --> Q3["3️⃣ GENERATE<br/>Gemini/GPT sinh câu trả lời"]
    Q3 --> Q4{"LLM thành công?"}
    Q4 -->|✅| R
    Q4 -->|"❌ Lỗi/Timeout/Quota"| P

    P --> R["🔊 Robot nói câu trả lời<br/>+ Gật đầu"]
    R --> S{"Khách hỏi tiếp?"}
    S -->|"🔄 Quay lại LISTENING"| D
    S -->|"👋 Bye"| N

    L --> N
    N --> A
```

## 3. RAG Pipeline — Chi tiết

```mermaid
flowchart LR
    Q["❓ Câu hỏi<br/>'Tell me about ROBOG'"] --> R["🔍 RETRIEVE<br/>Keyword search<br/>trong KNOWLEDGE_BASE"]

    R --> R1["Top 5 matches:<br/>• robog → '...'<br/>• competition → '...'<br/>• achievement → '...'"]

    R1 --> A["📝 AUGMENT<br/>Build RAG Prompt"]

    A --> A1["System Prompt<br/>+ AI_LAB_DOCUMENT (full PDF)<br/>+ Retrieved snippets<br/>+ User question"]

    A1 --> G["🤖 GENERATE<br/>Gemini API"]

    G --> ANS["💬 'Mr. Phuoc guided our<br/>students in ROBOG 2024<br/>in Dong Nai!'"]

    G -.->|"❌ Lỗi"| FB["📚 Fallback<br/>Rule-Based answer"]
```

## 4. Module Architecture

```mermaid
flowchart TB
    subgraph main["main.py — ReceptionRobot"]
        SM["State Machine<br/>IDLE → GREETING → LISTENING → ANSWERING → GOODBYE"]
    end

    subgraph modules["Các module"]
        V["👁️ vision.py<br/>VisionModule<br/>Face detect + Gender"]
        A["🤖 actions.py<br/>ActionModule<br/>TTS + Gestures"]
        N["🎙️ noise_handler.py<br/>NoiseHandler<br/>STT + Retry + Gesture fallback"]
        QA["🧠 qa_system.py<br/>RAGBasedQA / RuleBasedQA"]
    end

    subgraph config["config.py"]
        KB["📚 KNOWLEDGE_BASE<br/>~50 keyword entries"]
        DOC["📄 AI_LAB_DOCUMENT<br/>Full PDF content"]
        SP["💬 LLM_SYSTEM_PROMPT"]
    end

    subgraph external["External"]
        SDK["UBTECH Alpha Mini SDK"]
        LLM["Gemini / GPT API"]
    end

    SM --> V
    SM --> A
    SM --> N
    SM --> QA

    V --> SDK
    A --> SDK
    N --> SDK
    QA --> KB
    QA --> DOC
    QA --> SP
    QA --> LLM
```

## 5. Gesture Mapping

```mermaid
flowchart LR
    subgraph gestures["Cử chỉ tay"]
        G1["👍 Thumbs Up"]
        G2["💕 Finger Heart"]
        G3["👌 OK"]
        G4["✋ Paper"]
        G5["✊ Fist"]
    end

    subgraph keywords["Keyword"]
        K1["product"]
        K2["contact"]
        K3["working hour"]
        K4["goodbye"]
        K5["wifi"]
    end

    G1 --> K1
    G2 --> K2
    G3 --> K3
    G4 --> K4
    G5 --> K5

    K1 --> QA["🧠 RAG Pipeline<br/>→ Trả lời tự nhiên"]
    K2 --> QA
    K3 --> QA
    K5 --> QA
    K4 --> BYE["👋 GOODBYE State"]
```
