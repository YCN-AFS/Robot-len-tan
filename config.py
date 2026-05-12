"""
ROBOT RECEPTIONIST — CONFIG
All constants, greeting templates, and knowledge base for Q&A
are centralized here for easy editing.
"""

import os

# Force pure-Python protobuf so alphamini SDK works with protobuf 5.x
os.environ["PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION"] = "python"

import logging
from pathlib import Path
from dotenv import load_dotenv

# ─────────────────────────────────────────────
# Load environment variables
# ─────────────────────────────────────────────
_env_path = Path(__file__).parent / ".env"
load_dotenv(dotenv_path=_env_path)

# ─────────────────────────────────────────────
# ROBOT CONNECTION
# ─────────────────────────────────────────────
ROBOT_IP: str = os.getenv("ROBOT_IP", "192.168.100.141")
ROBOT_PORT: int = int(os.getenv("ROBOT_PORT", "5100"))
ROBOT_NAME: str = "AlphaMini"
CONNECTION_RETRY: int = 3
CONNECTION_RETRY_DELAY: float = 2.0

# ─────────────────────────────────────────────
# ROBOT SETTINGS
# ─────────────────────────────────────────────
ROBOT_VOLUME: float = float(os.getenv("ROBOT_VOLUME", "0.8"))  # [0.0 - 1.0]

# ─────────────────────────────────────────────
# VISION & DETECTION
# ─────────────────────────────────────────────
FACE_DETECT_TIMEOUT: int = 10
FACE_ANALYSIS_TIMEOUT: int = 10
PERSON_POLL_INTERVAL: float = 3.0
GENDER_THRESHOLD: int = 50  # < 50 = Female, >= 50 = Male

# ─────────────────────────────────────────────
# SPEECH & LISTENING
# ─────────────────────────────────────────────
USE_LOCAL_STT: bool = os.getenv("USE_LOCAL_STT", "false").lower() in ("true", "1", "yes")
LOCAL_STT_LANGUAGE: str = os.getenv("LOCAL_STT_LANGUAGE", "vi-VN")

LISTEN_TIMEOUT_MS: int = int(os.getenv("LISTEN_TIMEOUT_MS", "10000"))  # ms
LISTEN_TIMEOUT_EXTENDED_MS: int = 15000  # ms — longer timeout for retry
MAX_RETRY_LISTEN: int = int(os.getenv("MAX_RETRY_LISTEN", "2"))
GESTURE_FALLBACK_TIMEOUT: int = 15  # seconds

# ─────────────────────────────────────────────
# Q&A SYSTEM
# ─────────────────────────────────────────────
QA_LEVEL: int = int(os.getenv("QA_LEVEL", "10"))  # 5 = Rule-based, 10 = RAG (LLM + Knowledge)
LLM_PROVIDER: str = os.getenv("LLM_PROVIDER", "gemini")
LLM_API_KEY: str = os.getenv("LLM_API_KEY", "")
LLM_MODEL_OPENAI: str = os.getenv("LLM_MODEL_OPENAI", "gpt-4o-mini")
LLM_MODEL_GEMINI: str = os.getenv("LLM_MODEL_GEMINI", "models/gemini-2.5-flash-lite")
LLM_TIMEOUT: int = 15
LLM_MAX_TOKENS: int = 200

# ─────────────────────────────────────────────
# GREETING TEMPLATES
# ─────────────────────────────────────────────
GREETINGS = {
    "male": [
        "Hello sir! Welcome to the AI Lab! How can I help you today?",
        "Hi there! Great to see you at the AI Lab. What can I do for you?",
        "Welcome! I'm Alpha Mini, the AI Lab receptionist. What would you like to know?",
    ],
    "female": [
        "Hello! Welcome to the AI Lab! How can I help you today?",
        "Hi there! Great to see you at the AI Lab. What can I do for you?",
        "Welcome! I'm Alpha Mini, the AI Lab receptionist. What would you like to know?",
    ],
    "unknown": [
        "Hello! Welcome to the AI Lab! How can I help you?",
        "Hi there! Great to see you at the AI Lab. What can I do for you?",
    ],
}

GOODBYE_MESSAGES = [
    "Thank you for visiting the AI Lab! See you again!",
    "It was great helping you. Have a wonderful day!",
    "Thank you for coming to the AI Lab! Wish you all the best!",
]

# ─────────────────────────────────────────────
# NOISE HANDLING MESSAGES
# ─────────────────────────────────────────────
NOISE_RETRY_MESSAGES = [
    "Sorry, I didn't catch that. Could you please say it again?",
    "I couldn't hear you. Could you speak a bit louder please?",
]

NOISE_FALLBACK_MESSAGE = (
    "It's a bit noisy here. You can use hand gestures instead! "
    "Hold up one finger to ask about products, "
    "two fingers for contact info, "
    "or wave to say goodbye!"
)

ASK_CONTINUE_MESSAGE = "Is there anything else I can help you with?"

# ─────────────────────────────────────────────
# GESTURE MAPPING
# ─────────────────────────────────────────────
GESTURE_TO_QUESTION = {
    "THUMBS_UP": "product",
    "FINGER_HEART": "contact",
    "OK": "working hour",
    "PAPER": "goodbye",
    "FIST": "wifi",
    "握拳": "wifi",          # Fist (Chinese SDK label)
    "竖大拇指": "product",   # Thumbs up
    "OK手势": "working hour",
    "比心": "contact",      # Heart
}

# ─────────────────────────────────────────────
# ROBOT GESTURES / ACTIONS
# ─────────────────────────────────────────────
GESTURE_WAVE = "010"
GESTURE_NOD = "009"
GESTURE_SHAKE_HEAD = "009"   # 011 not available — use nod instead
GESTURE_DANCE = "dance_0001"
GESTURE_BOW = "013"
GESTURE_LISTEN = "012"

# ─────────────────────────────────────────────
# Q&A LEVEL 5 — KNOWLEDGE BASE (Rule-based)
# ─────────────────────────────────────────────
KNOWLEDGE_BASE = {
    # ══ AI LAB / SMART THINGS CLUB INFO ══════

    # ── Lab overview
    "ai lab": (
        "The AI Lab, also known as the Smart Things Club, is a research and creative space "
        "for students passionate about Artificial Intelligence, Robotics, and IoT "
        "at Lac Hong University. It belongs to the Faculty of Information Technology."
    ),
    "smart things": (
        "Smart Things is the student club operating in this AI Lab. "
        "We focus on AI, Robotics, and Internet of Things projects. "
        "It's managed by Mr. Phan Thien Phuoc."
    ),
    "about this room": (
        "This is the AI Lab of Lac Hong University's Faculty of Information Technology. "
        "It's also the home of the Smart Things Club, where students work on AI, Robotics, and IoT projects."
    ),
    "introduce": (
        "Welcome to the AI Lab! This is a research and innovation space under "
        "the Faculty of Information Technology at Lac Hong University. "
        "Here, students explore AI, Robotics, and IoT technologies."
    ),
    "what is this place": (
        "This is the AI Lab and Smart Things Club at Lac Hong University. "
        "We research and develop projects in Artificial Intelligence, Robotics, and IoT."
    ),
    "lab": (
        "This is the AI Lab under the Faculty of Information Technology at Lac Hong University. "
        "We specialize in AI, Robotics, and IoT research. Would you like to know more?"
    ),
    "what is this": (
        "This is the AI Lab, also known as the Smart Things Club. "
        "I can tell you about our achievements, team, facilities, or activities!"
    ),

    # ── University & Faculty
    "lac hong": (
        "Lac Hong University's Faculty of Information Technology has internationally accredited programs, "
        "certified by AUN-QA and ABET for Information Technology Engineering."
    ),
    "university": (
        "This lab belongs to Lac Hong University, specifically the Faculty of Information Technology. "
        "Our AI program has been growing rapidly and successfully met enrollment targets for 2025-2026."
    ),
    "faculty": (
        "The Faculty of Information Technology at Lac Hong University offers high-quality programs "
        "accredited by AUN-QA and ABET. The AI major is one of our fastest-growing programs."
    ),
    "aun": (
        "Yes! The Faculty of Information Technology at Lac Hong University has achieved "
        "AUN-QA accreditation, demonstrating international quality standards."
    ),
    "abet": (
        "The Information Technology Engineering program at Lac Hong University "
        "has achieved ABET accreditation, an internationally recognized quality standard."
    ),
    "accreditation": (
        "Our faculty holds both AUN-QA and ABET accreditations, "
        "proving our education meets international quality standards."
    ),

    # ── Manager & Instructor
    "manager": (
        "The AI Lab is managed by Mr. Phan Thien Phuoc, "
        "who is also a teaching assistant at the Faculty of Information Technology."
    ),
    "phan thien phuoc": (
        "Mr. Phan Thien Phuoc manages the AI Lab and serves as a teaching assistant. "
        "He has guided students in competitions like ROBOG 2024 and co-organized the Algorand Hackathon."
    ),
    "teacher": (
        "The AI Lab is supervised by Mr. Phan Thien Phuoc. He's very dedicated to students "
        "and has won awards including third place at the school-level Innovation Solutions Workshop."
    ),
    "who manages": (
        "Mr. Phan Thien Phuoc manages this AI Lab. He's a teaching assistant "
        "at the Faculty of IT and has led students to many achievements."
    ),
    "instructor": (
        "Our main instructor is Mr. Phan Thien Phuoc. He organized the Algorand Hackathon 2024, "
        "guided ROBOG 2024 competitors, and received a commendation from Dong Nai VUSTA."
    ),

    # ── Achievements
    "achievement": (
        "Our lab has won many awards, including First Prize at the Dong Nai Innovation "
        "and Startup Competition in 2019, worth 40 million VND, and an Encouragement Prize "
        "at the China-Vietnam Blockchain Metaverse Competition."
    ),
    "award": (
        "Notable awards include First Prize at Dong Nai Innovation Competition 2019 "
        "and an Encouragement Prize at the China-Vietnam Blockchain Metaverse Contest."
    ),
    "competition": (
        "Our students have participated in competitions like ROBOG 2024, "
        "the Algorand University Hackathon, and the Dong Nai Innovation Competition, "
        "winning multiple prizes."
    ),
    "hackathon": (
        "In June 2024, the AI Lab co-organized the Algorand University Hackathon, "
        "providing students a great platform for blockchain technology innovation."
    ),
    "algorand": (
        "The Algorand University Hackathon was organized in June 2024 "
        "with the participation of our AI Lab team."
    ),
    "robog": (
        "In September 2024, Mr. Phan Thien Phuoc guided students in the ROBOG Competition "
        "held in Dong Nai, organized by the Department of Information and Communications."
    ),
    "dong nai": (
        "In 2019, our team won First Prize at the Dong Nai Innovation and Startup Competition, "
        "valued at 40 million VND. Mr. Phuoc also received a commendation from Dong Nai VUSTA in 2024."
    ),
    "blockchain": (
        "Our team won an Encouragement Prize at the China-Vietnam Blockchain and Metaverse "
        "Innovation Competition, sponsored by the Guilin Bank Cup."
    ),
    "prize": (
        "Key prizes include First Place at Dong Nai Startup Competition 2019 "
        "and an Encouragement Prize at the Blockchain Metaverse Competition."
    ),
    "vusta": (
        "In December 2024, Mr. Phan Thien Phuoc received a commendation from "
        "the Dong Nai Union of Science and Technology Associations for his contributions."
    ),

    # ── Facilities & Equipment
    "facility": (
        "The AI Lab is well-equipped with modern tools for IoT, smart home, "
        "and automation projects. THOMI Technology sponsored 20 smart electrical boards "
        "worth 26 million VND in May 2022."
    ),
    "equipment": (
        "We have modern equipment for IoT and automation research. "
        "THOMI Technology donated 20 smart electrical boards for our projects."
    ),
    "sponsor": (
        "In May 2022, THOMI Technology Solutions Company sponsored 20 smart electrical boards, "
        "valued at 26 million VND, for our IoT and smart home research projects."
    ),
    "thomi": (
        "THOMI Technology Solutions is a key corporate partner. They sponsored 20 smart boards "
        "worth 26 million VND for our lab's IoT research in May 2022."
    ),
    "smart board": (
        "Our lab has 20 smart electrical boards donated by THOMI Technology, "
        "used for IoT, smart home, and automation projects."
    ),
    "partnership": (
        "The AI Lab partners with tech companies like THOMI Technology "
        "to provide modern equipment and real-world project opportunities for students."
    ),
    "corporate": (
        "We collaborate with companies like THOMI Technology Solutions "
        "to equip students with modern tools and practical experience."
    ),

    # ── Vision & Mission
    "vision": (
        "The AI Lab aims to build a passionate tech student community "
        "where classroom ideas become real products solving practical problems."
    ),
    "mission": (
        "Our mission is to be a strong launchpad for future AI and IT engineers, "
        "helping them develop skills, compete in major contests, and meet global job market demands."
    ),
    "future": (
        "The AI Lab is building a community where students turn ideas into real products. "
        "We prepare future engineers for the global technology job market."
    ),
    "goal": (
        "Our goal is to transform classroom knowledge into practical solutions, "
        "creating a strong foundation for future AI engineers."
    ),

    # ── Research Areas
    "research": (
        "We focus on Artificial Intelligence, Robotics, and Internet of Things. "
        "Our projects include smart home systems, automation, and AI solutions."
    ),
    "iot": (
        "IoT is one of our key research areas. We work on smart home systems, "
        "automation projects, and connected devices."
    ),
    "artificial intelligence": (
        "AI is our core focus. The AI program at Lac Hong University is growing fast "
        "and has met its enrollment targets for 2025-2026."
    ),
    "robotics": (
        "Robotics is a key research area here. I, Alpha Mini, am one of the lab's robotics projects, "
        "serving as a receptionist to demonstrate human-robot interaction."
    ),
    "smart home": (
        "Smart home technology is one of our IoT research areas. "
        "We use smart electrical boards sponsored by THOMI Technology for these projects."
    ),

    # ── How to join
    "join": (
        "If you're interested in joining the Smart Things Club, "
        "you can talk to Mr. Phan Thien Phuoc or contact the Faculty of Information Technology "
        "at Lac Hong University."
    ),
    "member": (
        "The Smart Things Club welcomes all Lac Hong University students "
        "passionate about AI, Robotics, and IoT. Contact Mr. Phan Thien Phuoc to join!"
    ),
    "register": (
        "To register for the Smart Things Club, please contact Mr. Phan Thien Phuoc "
        "or visit the Faculty of Information Technology office."
    ),
    "student": (
        "The AI Lab is a great place for students to learn and practice AI, Robotics, "
        "and IoT. All Lac Hong University students are welcome to join!"
    ),

    # ══ GENERAL ROBOT INFO ══════════════════════

    # ── Self-intro
    "what do you do": (
        "I'm Alpha Mini, the AI Lab's receptionist robot! "
        "I can greet visitors, answer questions about the lab, and provide information."
    ),
    "who are you": (
        "I'm Alpha Mini! A smart robot working as a receptionist at the AI Lab. "
        "Feel free to ask me anything about the lab!"
    ),

    # ── Products & Projects
    "product": (
        "Our Lab is developing exciting projects including "
        "this receptionist robot, IoT systems, smart home solutions, "
        "and AI applications. Which one interests you?"
    ),
    "project": (
        "We're working on AI, Robotics, and IoT projects, "
        "including smart receptionist robots, automation systems, and smart home technology."
    ),
    "robot": (
        "I'm Alpha Mini, an AI-powered receptionist robot at the AI Lab. "
        "I can greet visitors, answer questions, and demonstrate human-robot interaction!"
    ),

    # ── Contact
    "contact": "You can reach the AI Lab by contacting Mr. Phan Thien Phuoc at the Faculty of IT, Lac Hong University.",
    "email": "For email inquiries, please contact the Faculty of Information Technology at Lac Hong University.",
    "phone": "Please contact the Faculty of Information Technology at Lac Hong University for phone inquiries.",

    # ── WiFi
    "wifi": "The WiFi password is Lab@2024. Connect to the network called Lab-Guest.",
    "password": "WiFi password is Lab@2024, network name: Lab-Guest.",
    "internet": "Connect to WiFi network Lab-Guest, password: Lab@2024.",

    # ── Working hours
    "working hour": "The AI Lab is open from 8 AM to 5 PM, Monday through Friday.",
    "open": "The AI Lab is open 8 AM to 5 PM, Monday to Friday.",
    "schedule": "We're open Monday to Friday, 8 AM to 5 PM.",
    "time": "The AI Lab is open from 8 AM to 5 PM, Monday through Friday.",
    "hour": "Our working hours are 8 AM to 5 PM, Monday to Friday.",

    # ── Location
    "where": "The AI Lab is located at the Faculty of Information Technology, Lac Hong University.",
    "location": "We're at the Faculty of Information Technology, Lac Hong University, Dong Nai province.",
    "address": "The AI Lab is at the Faculty of IT, Lac Hong University.",
    "floor": "Please ask a staff member for the exact room location in the building.",

    # ── Help
    "help": (
        "I can help you with info about the AI Lab, Smart Things Club, achievements, "
        "research areas, how to join, WiFi, or working hours!"
    ),
    "can you": "Yes! Ask me about the lab, achievements, research, WiFi, contact info, or how to join!",
    "what can": "I can tell you about the AI Lab, Smart Things Club, achievements, research, and more!",

    # ── Greetings
    "hello": "Hello! Great to meet you! Welcome to the AI Lab!",
    "hi": "Hi there! I'm Alpha Mini, the AI Lab receptionist. What can I do for you?",
    "hey": "Hey! Welcome to the AI Lab! I'm ready to help!",
    "good morning": "Good morning! Welcome to the AI Lab!",
    "good afternoon": "Good afternoon! How can I help you at the AI Lab?",

    # ── Goodbye
    "goodbye": "Goodbye! Thanks for visiting the AI Lab!",
    "bye": "Bye bye! Hope to see you again at the AI Lab!",
    "see you": "See you later! Have a great day!",

    # ── Thanks
    "thank": "You're welcome! Happy to help!",
    "thanks": "You're welcome! Glad I could help!",
}

# Default answer when no keyword matches
QA_DEFAULT_ANSWER = (
    "I'm sorry, I didn't quite understand that. "
    "You can ask me about the AI Lab, Smart Things Club, our achievements, "
    "research areas, how to join, WiFi, or working hours!"
)

# ─────────────────────────────────────────────
# LLM SYSTEM PROMPT
# ─────────────────────────────────────────────
LLM_SYSTEM_PROMPT = """You are Alpha Mini, a receptionist robot at the AI Lab (Smart Things Club) at Lac Hong University.

CRITICAL: Your answer will be spoken aloud by a robot via TTS. Follow these rules strictly:
- Keep answers SHORT: max 1-2 sentences, under 150 characters if possible
- Be friendly, warm, and natural — like a real receptionist
- Be proud and enthusiastic about the lab
- If the question is NOT about the lab, politely redirect
- ONLY use information from the CONTEXT below. Do NOT make up facts.
- If the context doesn't contain enough info, say you're not sure and suggest asking Mr. Phuoc
"""

# ─────────────────────────────────────────────
# RAG KNOWLEDGE DOCUMENT (extracted from Smart-Things.pdf)
# Full document used as retrieval source for RAG pipeline
# ─────────────────────────────────────────────
AI_LAB_DOCUMENT = """
# AI Lab (Smart Things Club) — Lac Hong University

## 1. Overview
The AI Lab, also the workspace of the Smart Things Club, is a research, learning, and
creative environment for students passionate about Artificial Intelligence, Robotics, and
Internet of Things (IoT) at Lac Hong University (LHU). It belongs to the Faculty of
Information Technology.

The Faculty of IT is proud to have high-quality training programs, certified by international
standards including AUN-QA and ABET (for Information Technology Engineering).

The Artificial Intelligence major is growing rapidly, demonstrated by successfully meeting
all enrollment targets for the 2025-2026 academic year.

## 2. Management & Instructors
The lab is directly managed by Mr. Phan Thien Phuoc, AI Lab Manager and Teaching
Assistant at the Faculty of Information Technology. He is deeply dedicated to students
and has achieved notable accomplishments:

- Organized the Algorand University Hackathon (June 2024)
- Guided students in the ROBOG 2024 Competition in Dong Nai (September 2024)
- Won Third Prize at the school-level Innovation Solutions Workshop 2023-2024
  (with Ms. Phan Thi Huong, June 2024)
- Received commendation from Dong Nai VUSTA for outstanding contributions (December 2024)

## 3. Achievements
| Year | Achievement |
|------|-------------|
| 2019 | First Prize — Dong Nai Innovation & Startup Competition (40,000,000 VND) |
| -    | Encouragement Prize — China-Vietnam Blockchain-Metaverse Innovation Competition (Guilin Bank Cup, 1st edition) |

## 4. Facilities & Corporate Partnerships
The AI Lab emphasizes connecting with technology companies for modern equipment.
In May 2022, THOMI Technology Solutions Company sponsored 20 Smart Electrical Boards
(total value: 26,000,000 VND) for IoT, smart home, and automation research projects.

## 5. Vision
The AI Lab (Smart Things Club) aims to build a passionate tech student community where
classroom ideas become real products solving practical problems. It serves as a strong
launchpad for future AI and IT engineers to develop skills, compete in major competitions,
and meet the demands of the global job market.

## 6. Operational Info
- Working hours: 8 AM - 5 PM, Monday to Friday
- WiFi network: "Lab-Guest", password: "Lab@2024"
- Contact: Mr. Phan Thien Phuoc, Faculty of IT, Lac Hong University
- Location: Faculty of Information Technology, Lac Hong University, Dong Nai
"""

# ─────────────────────────────────────────────
# LOGGING
# ─────────────────────────────────────────────
LOG_LEVEL = logging.INFO
LOG_FORMAT = "%(asctime)s | %(name)-18s | %(levelname)-7s | %(message)s"
LOG_DATE_FORMAT = "%H:%M:%S"
