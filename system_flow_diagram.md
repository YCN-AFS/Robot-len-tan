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

---

## 6. BPMN — Quy trình tiếp đón khách tổng thể

```mermaid
flowchart TD
    subgraph Pool["🏢 Robot Receptionist System"]

        subgraph Lane1["👤 Visitor"]
            V1(("⚫ Start"))
            V2["Bước vào phòng AI Lab"]
            V3["Đặt câu hỏi bằng giọng nói"]
            V4{"Hỏi tiếp?"}
            V5["Nói goodbye / rời đi"]
            V6(("⭕ End"))
        end

        subgraph Lane2["🤖 Alpha Mini Robot"]
            R1["Quét camera liên tục"]
            R2["Phân tích giới tính + tuổi"]
            R3["Chào khách + Vẫy tay"]
            R4["Lắng nghe câu hỏi"]
            R5["Phát câu trả lời qua TTS + Gật đầu"]
            R6["Hỏi: 'Anything else?'"]
            R7["Nói lời tạm biệt + Cúi chào"]
        end

        subgraph Lane3["🧠 AI Backend"]
            A1{"Phát hiện khuôn mặt?"}
            A2["NoiseHandler: STT Processing"]
            A3["RAG Pipeline: Retrieve + Augment + Generate"]
            A4{"Câu trả lời hợp lệ?"}
            A5["Fallback: Rule-Based answer"]
        end
    end

    V1 --> V2
    V2 --> R1
    R1 --> A1
    A1 -->|Không| R1
    A1 -->|Có| R2
    R2 --> R3
    R3 --> V3
    V3 --> R4
    R4 --> A2
    A2 --> A3
    A3 --> A4
    A4 -->|✅ Có| R5
    A4 -->|❌ Lỗi| A5
    A5 --> R5
    R5 --> R6
    R6 --> V4
    V4 -->|Có| V3
    V4 -->|Không| V5
    V5 --> R7
    R7 --> V6
```

## 7. BPMN — Quy trình xử lý câu hỏi (RAG Pipeline)

```mermaid
flowchart TD
    subgraph Pool2["🧠 Q&A Processing"]

        subgraph Lane_Input["📥 Input Layer"]
            I1(("⚫ Nhận câu hỏi"))
            I2["Chuẩn hóa text: lowercase + strip"]
            I3{"Câu hỏi rỗng?"}
            I4["Trả default answer"]
        end

        subgraph Lane_Retrieve["🔍 Retrieval Layer"]
            RE1["Duyệt tất cả keyword trong Knowledge Base"]
            RE2{"Tìm thấy keyword match?"}
            RE3["Sắp xếp: dài nhất trước"]
            RE4["Lấy top-5 relevant entries"]
            RE5["Không có context bổ sung"]
        end

        subgraph Lane_Augment["📝 Augmentation Layer"]
            AU1["Lấy System Prompt"]
            AU2["Lấy AI_LAB_DOCUMENT: toàn bộ PDF"]
            AU3["Ghép: Prompt + Document + Retrieved chunks + Question"]
        end

        subgraph Lane_Generate["🤖 Generation Layer"]
            G1{"Provider?"}
            G2["Gọi Gemini API"]
            G3["Gọi OpenAI API"]
            G4{"Response OK?"}
            G5["Trả câu trả lời tự nhiên"]
            G6(("⭕ Done"))
        end

        subgraph Lane_Fallback["🔄 Fallback Layer"]
            F1{"Loại lỗi?"}
            F2["429 / RESOURCE_EXHAUSTED: Cooldown 120s"]
            F3["Timeout / Other error"]
            F4["Rule-Based: keyword matching"]
        end
    end

    I1 --> I2 --> I3
    I3 -->|Có| I4 --> G6
    I3 -->|Không| RE1

    RE1 --> RE2
    RE2 -->|Có| RE3 --> RE4
    RE2 -->|Không| RE5

    RE4 --> AU1
    RE5 --> AU1
    AU1 --> AU2 --> AU3

    AU3 --> G1
    G1 -->|Gemini| G2
    G1 -->|OpenAI| G3
    G2 --> G4
    G3 --> G4

    G4 -->|✅ Thành công| G5 --> G6
    G4 -->|❌ Lỗi| F1
    F1 -->|Quota hết| F2 --> F4
    F1 -->|Timeout / Lỗi khác| F3 --> F4
    F4 --> G5
```

## 8. BPMN — Quy trình xử lý tiếng ồn (Noise Handling)

```mermaid
flowchart TD
    subgraph Pool3["🎙️ Noise Handling Process"]

        subgraph Lane_STT["🔊 Speech-to-Text"]
            S1(("⚫ Start Listen"))
            S2["Mute robot speaker"]
            S3{"Chế độ STT?"}
            S4["Robot mic: Record audio"]
            S5["Download audio từ robot"]
            S6["Google STT API"]
            S7["Robot built-in STT: English"]
            S8["Unmute robot speaker"]
            S9{"Nhận diện được text?"}
        end

        subgraph Lane_Retry["🔄 Retry"]
            RT1{"Còn lượt retry?<br/>Max: 2 lần"}
            RT2["Robot nói: 'Could you say it again?'"]
            RT3["Robot lắc đầu"]
            RT4["Tăng timeout: 15s"]
        end

        subgraph Lane_Gesture["🖐️ Gesture Fallback"]
            GE1["Robot nói: 'Use hand gestures!'"]
            GE2["Robot chuyển tư thế lắng nghe"]
            GE3["Camera: ObjectRecognise GESTURE"]
            GE4{"Nhận diện cử chỉ?"}
            GE5["Mapping: Gesture → Keyword"]
            GE6["Robot: 'Got it! You want to know about ...'"]
            GE7["Không giao tiếp được"]
            GE8["Robot: 'Please try again later!'"]
        end

        subgraph Lane_Output["📤 Output"]
            O1["Trả về text cho QA System"]
            O2["Trả về None"]
            O3(("⭕ End"))
        end
    end

    S1 --> S2 --> S3
    S3 -->|LOCAL| S4 --> S5 --> S6 --> S8
    S3 -->|ROBOT| S7 --> S8
    S8 --> S9

    S9 -->|✅ Có text| O1 --> O3
    S9 -->|❌ Không| RT1

    RT1 -->|Còn| RT2 --> RT3 --> RT4 --> S2
    RT1 -->|Hết lượt| GE1

    GE1 --> GE2 --> GE3 --> GE4
    GE4 -->|✅ Nhận diện được| GE5 --> GE6 --> O1
    GE4 -->|❌ Không| GE7 --> GE8 --> O2 --> O3
```
