# 🤖 Robot Lễ Tân — AI Lab Receptionist

> Robot lễ tân thông minh sử dụng **UBTECH Alpha Mini** kết hợp **AI (Gemini/GPT)** để chào đón và trả lời câu hỏi của khách tham quan tại **Phòng AI Lab — CLB Smart Things**, Khoa CNTT, Đại học Lạc Hồng.

---

## ✨ Tính năng chính

| Tính năng | Mô tả |
|-----------|-------|
| 👁️ **Nhận diện khuôn mặt** | Tự động phát hiện khách, phân tích giới tính & tuổi |
| 👋 **Chào hỏi thông minh** | Chào theo giới tính + cử chỉ vẫy tay |
| 🎙️ **Nhận diện giọng nói** | Speech-to-Text (Robot STT / Google STT) |
| 🧠 **RAG Q&A** | Trả lời tự nhiên dựa trên Knowledge Base + LLM (Gemini) |
| 🖐️ **Nhận diện cử chỉ tay** | Fallback khi môi trường ồn — dùng cử chỉ thay giọng nói |
| 🔊 **Text-to-Speech** | Robot phát âm câu trả lời qua loa tích hợp |

## 🏗️ Kiến trúc hệ thống

```
┌─────────────────────────────────────────────────────────┐
│                    main.py (State Machine)               │
│   IDLE → GREETING → LISTENING → ANSWERING → GOODBYE     │
├─────────┬──────────┬───────────────┬────────────────────┤
│ vision  │ actions  │ noise_handler │    qa_system       │
│  .py    │  .py     │    .py        │      .py           │
│         │          │               │                    │
│ Face    │ TTS      │ STT + Retry   │ ┌────────────────┐ │
│ Detect  │ Gesture  │ + Gesture     │ │  RAG Pipeline   │ │
│ Gender  │ Dance    │   Fallback    │ │ Retrieve→LLM   │ │
│ Age     │ Wave     │               │ │ + Fallback L5  │ │
└────┬────┴────┬─────┴───────┬───────┴─┴───────┬────────┘─┘
     │         │             │                 │
     ▼         ▼             ▼                 ▼
┌─────────────────┐  ┌─────────────┐  ┌──────────────┐
│  Alpha Mini SDK │  │ Google STT  │  │ Gemini / GPT │
└─────────────────┘  └─────────────┘  └──────────────┘
```

## 📁 Cấu trúc dự án

```
Robot-letan/
├── main.py              # 🎯 Entry point — State Machine chính
├── config.py            # ⚙️ Cấu hình, Knowledge Base, LLM Prompt
├── qa_system.py         # 🧠 Hệ thống Q&A (Rule-Based + RAG)
├── noise_handler.py     # 🎙️ Xử lý STT + môi trường ồn
├── vision.py            # 👁️ Nhận diện khuôn mặt, giới tính, tuổi
├── actions.py           # 🤖 TTS, cử chỉ robot (vẫy tay, gật đầu)
├── connection.py        # 🔌 Kết nối robot Alpha Mini
├── Smart-Things.pdf     # 📄 Tài liệu gốc về AI Lab
├── system_flow_diagram.md # 📊 Sơ đồ luồng xử lý
├── requirements.txt     # 📦 Dependencies
├── .env                 # 🔑 API keys (không push lên git)
└── .gitignore
```

## 🚀 Cài đặt & Chạy

### 1. Clone repository

```bash
git clone https://github.com/YCN-AFS/Robot-len-tan.git
cd Robot-len-tan
```

### 2. Tạo virtual environment

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Cài dependencies

```bash
pip install -r requirements.txt
```

### 4. Cấu hình `.env`

```bash
cp .env.example .env
```

Chỉnh sửa file `.env`:

```env
ROBOT_IP=192.168.100.141
QA_LEVEL=10
LLM_PROVIDER=gemini
LLM_API_KEY=your-gemini-api-key-here
```

### 5. Chạy robot

```bash
# Mặc định: RAG mode (Level 10)
python main.py

# Chỉ Rule-Based (không cần API key)
python main.py --level 5

# Đổi IP robot
python main.py --ip 192.168.1.50

# Xem danh sách actions của robot
python main.py --list-actions
```

## 🧠 Hệ thống Q&A

### Level 5 — Rule-Based
- Tìm keyword trong câu hỏi → trả lời từ mẫu có sẵn
- **Ưu điểm**: Nhanh, không cần internet
- **Nhược điểm**: Chỉ trả lời được câu hỏi đã định sẵn

### Level 10 — RAG (Mặc định)
Pipeline: **Retrieve → Augment → Generate**

1. **Retrieve**: Tìm keyword-matched entries từ Knowledge Base
2. **Augment**: Ghép retrieved context + toàn bộ tài liệu AI Lab vào prompt
3. **Generate**: Gemini/GPT sinh câu trả lời tự nhiên

```
Câu hỏi: "Tell me about ROBOG competition"
    ↓
Retrieve: [robog, competition, achievement] → 3 context chunks
    ↓
Augment: System Prompt + AI Lab Document + Chunks + Question
    ↓
Generate: "Mr. Phuoc guided our students in ROBOG 2024 in Dong Nai!"
```

> Nếu LLM lỗi/timeout/hết quota → tự động fallback về Rule-Based.

## 🖐️ Nhận diện cử chỉ tay

Khi môi trường quá ồn, robot tự động chuyển sang chế độ cử chỉ:

| Cử chỉ | Ý nghĩa |
|---------|----------|
| 👍 Thumbs Up | Hỏi về sản phẩm/dự án |
| 💕 Finger Heart | Thông tin liên hệ |
| 👌 OK | Giờ làm việc |
| ✊ Fist | Mật khẩu WiFi |
| ✋ Paper | Tạm biệt |

## 📊 State Machine

```
IDLE ──▶ GREETING ──▶ LISTENING ──▶ ANSWERING ──┐
 ▲                        │                      │
 │                        ▼                      │
 │                     GOODBYE ◀─────────────────┘
 │                        │
 └────────────────────────┘
```

## ⚙️ Yêu cầu

- **Python** 3.8+
- **Robot**: UBTECH Alpha Mini
- **Mạng**: PC và Robot cùng mạng WiFi
- **API Key** (cho RAG mode): Google Gemini hoặc OpenAI

## 👥 Đội ngũ

- **Quản lý AI Lab**: Thầy Phan Thiện Phước — Khoa CNTT, Đại học Lạc Hồng
- **CLB Smart Things** — Phòng AI Lab, Khoa Công nghệ Thông tin

## 📄 License

Dự án thuộc **AI Lab — CLB Smart Things**, Khoa CNTT, Đại học Lạc Hồng (LHU).
