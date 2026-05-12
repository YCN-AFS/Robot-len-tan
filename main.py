"""
ROBOT RECEPTIONIST — MAIN
Main orchestrator — State Machine controlling the robot.

State flow:
  ┌──────────┐     ┌───────────┐     ┌───────────┐     ┌───────────┐
  │   IDLE   │────▶│ GREETING  │────▶│ LISTENING │────▶│ ANSWERING │
  │(wait)    │     │(greet)    │     │(listen)   │     │(answer)   │
  └──────────┘     └───────────┘     └───────────┘     └─────┬─────┘
       ▲                                                       │
       └───────────────────────────────────────────────────────┘
                        (visitor done with questions)

Usage:
  python main.py                    # Default Q&A Level 5
  python main.py --level 10         # Use LLM
  python main.py --ip 192.168.1.50  # Change robot IP
  python main.py --list-actions     # List robot actions
"""

import asyncio
import enum
import logging
import signal
import sys
import argparse
from typing import Optional

from config import (
    ROBOT_IP,
    QA_LEVEL,
    LOG_LEVEL,
    LOG_FORMAT,
    LOG_DATE_FORMAT,
)
from connection import RobotConnection
from vision import VisionModule, PersonInfo
from actions import ActionModule
from qa_system import create_qa_system, QASystem
from noise_handler import NoiseHandler

# ─────────────────────────────────────────────
# Logging setup
# ─────────────────────────────────────────────
logging.basicConfig(
    level=LOG_LEVEL,
    format=LOG_FORMAT,
    datefmt=LOG_DATE_FORMAT,
)
logger = logging.getLogger("main")


# ═════════════════════════════════════════════
# State Machine States
# ═════════════════════════════════════════════
class RobotState(enum.Enum):
    """States of the receptionist robot."""

    IDLE = "IDLE"               # Waiting for visitor
    GREETING = "GREETING"       # Greeting visitor
    LISTENING = "LISTENING"     # Listening for question
    ANSWERING = "ANSWERING"     # Answering question
    GOODBYE = "GOODBYE"         # Saying goodbye
    SHUTDOWN = "SHUTDOWN"       # Shutting down


# ═════════════════════════════════════════════
# ReceptionRobot — Main orchestrator
# ═════════════════════════════════════════════
class ReceptionRobot:
    """Lab Receptionist Robot — Main orchestrator.

    Combines all modules:
      - VisionModule: Person detection, gender analysis
      - ActionModule: TTS, gestures, movement
      - QASystem: Q&A (Level 5 or 10)
      - NoiseHandler: Noisy environment handling

    Runs a state machine loop continuously until
    a stop signal (Ctrl+C) is received.
    """

    def __init__(
        self,
        robot_ip: str = ROBOT_IP,
        qa_level: int = QA_LEVEL,
    ):
        # Config
        self._robot_ip = robot_ip
        self._qa_level = qa_level

        # Modules (initialized after connection)
        self._connection: Optional[RobotConnection] = None
        self._vision: Optional[VisionModule] = None
        self._action: Optional[ActionModule] = None
        self._qa: Optional[QASystem] = None
        self._noise: Optional[NoiseHandler] = None

        # State
        self._state = RobotState.IDLE
        self._running = False
        self._stop_event = asyncio.Event()
        self._current_person: Optional[PersonInfo] = None

        # Session counter
        self._session_count = 0

    # ─────────────────────────────────────────
    # Initialize modules
    # ─────────────────────────────────────────
    def _init_modules(self):
        """Initialize all sub-modules."""
        self._vision = VisionModule()
        self._action = ActionModule()
        self._qa = create_qa_system(level=self._qa_level)
        self._noise = NoiseHandler(
            action_module=self._action,
            connection=self._connection,
        )

        logger.info("=" * 55)
        logger.info("  🤖 LAB RECEPTIONIST ROBOT")
        logger.info("=" * 55)
        logger.info(f"  📡 Robot IP:  {self._robot_ip}")
        logger.info(f"  🧠 Q&A Level: {self._qa.level_name}")
        logger.info(f"  ⏳ Status:    READY")
        logger.info("=" * 55)

    # ─────────────────────────────────────────
    # State: IDLE — Wait for visitor
    # ─────────────────────────────────────────
    async def _state_idle(self) -> RobotState:
        """Wait until a visitor is detected.

        Robot continuously scans camera. When a face is detected,
        transitions to GREETING state.
        """
        logger.info("👀 [IDLE] Waiting for visitors...")

        person_info = await self._vision.wait_for_person(
            stop_event=self._stop_event,
        )

        if self._stop_event.is_set():
            return RobotState.SHUTDOWN

        if person_info.detected:
            self._current_person = person_info
            self._session_count += 1
            logger.info(
                f"🎉 [IDLE → GREETING] Visitor #{self._session_count} detected! "
                f"({person_info.gender_label}, ~{person_info.age} years old)"
            )
            return RobotState.GREETING

        return RobotState.IDLE

    # ─────────────────────────────────────────
    # State: GREETING — Greet visitor
    # ─────────────────────────────────────────
    async def _state_greeting(self) -> RobotState:
        """Greet visitor based on detected gender.

        Runs TTS + wave gesture simultaneously.
        """
        if not self._current_person:
            return RobotState.IDLE

        gender = self._current_person.gender
        age = self._current_person.age

        logger.info(
            f"👋 [GREETING] Greeting visitor: "
            f"{self._current_person.gender_label}, ~{age} years old"
        )

        await self._action.greet_and_gesture(gender=gender, age=age)
        await asyncio.sleep(1.0)

        return RobotState.LISTENING

    # ─────────────────────────────────────────
    # State: LISTENING — Listen for question
    # ─────────────────────────────────────────
    async def _state_listening(self) -> RobotState:
        """Listen for visitor's question.

        Uses NoiseHandler to handle noisy environments:
          1. Listen for speech (retry up to 2 times)
          2. Fallback to hand gesture if needed
        """
        logger.info("🎙️ [LISTENING] Listening for visitor...")

        question = await self._noise.robust_listen()

        if question:
            # Filter out STT noise (fragments < 2 meaningful words)
            words = question.strip().split()
            if len(words) < 2:
                logger.info(f"🔇 [LISTENING] Ignored short fragment: \"{question}\"")
                question = None
            else:
                # Check goodbye keywords
                bye_keywords = ["bye", "goodbye", "see you", "that's all", "done"]
                if any(kw in question.lower() for kw in bye_keywords):
                    logger.info("👋 [LISTENING → GOODBYE] Guest wants to leave")
                    return RobotState.GOODBYE

                logger.info(
                    f"✅ [LISTENING → ANSWERING] "
                    f"Question: \"{question}\""
                )
                self._current_question = question
                return RobotState.ANSWERING

        if not question:
            # Nothing heard → say goodbye
            logger.info("🤷 [LISTENING] No input received")
            await self._action.say(
                "I didn't catch your question. "
                "If you need help, just speak up or wave at me!"
            )
            await asyncio.sleep(2)
            return RobotState.GOODBYE

    # ─────────────────────────────────────────
    # State: ANSWERING — Answer question
    # ─────────────────────────────────────────
    async def _state_answering(self) -> RobotState:
        """Process question and respond via TTS.

        Flow:
          1. Send question to QASystem
          2. Receive answer
          3. Robot nods + plays TTS
        """
        question = getattr(self, "_current_question", "")
        if not question:
            return RobotState.LISTENING

        logger.info(f"💬 [ANSWERING] Processing: \"{question}\"")

        # Get answer from Q&A engine
        answer = await self._qa.get_answer(question)

        # Trim if too long for robot TTS (robot cuts off at ~200 chars)
        if len(answer) > 220:
            trimmed = answer[:220]
            last_period = max(
                trimmed.rfind('. '),
                trimmed.rfind('! '),
                trimmed.rfind('? '),
            )
            if last_period > 100:
                answer = trimmed[:last_period + 1]
            else:
                answer = trimmed.rstrip() + "."
            logger.debug(f"✂️ Answer trimmed to {len(answer)} chars")

        # Nod + say answer simultaneously
        await asyncio.gather(
            self._action.nod(),
            self._action.say(answer),
            return_exceptions=True,
        )

        await asyncio.sleep(1.5)
        return RobotState.LISTENING

    # ─────────────────────────────────────────
    # State: GOODBYE — Say goodbye
    # ─────────────────────────────────────────
    async def _state_goodbye(self) -> RobotState:
        """Say goodbye to visitor and return to IDLE."""
        logger.info("👋 [GOODBYE] Saying goodbye to visitor!")

        await self._action.say_goodbye()

        # Reset
        self._current_person = None
        self._current_question = ""

        await asyncio.sleep(3.0)

        logger.info("🔄 [GOODBYE → IDLE] Returning to wait mode...")
        return RobotState.IDLE

    # ─────────────────────────────────────────
    # State Machine — Main loop
    # ─────────────────────────────────────────
    async def _run_state_machine(self):
        """Main state machine loop."""
        self._state = RobotState.IDLE
        self._running = True

        state_handlers = {
            RobotState.IDLE: self._state_idle,
            RobotState.GREETING: self._state_greeting,
            RobotState.LISTENING: self._state_listening,
            RobotState.ANSWERING: self._state_answering,
            RobotState.GOODBYE: self._state_goodbye,
        }

        while self._running and self._state != RobotState.SHUTDOWN:
            handler = state_handlers.get(self._state)
            if handler:
                try:
                    next_state = await handler()
                    if self._stop_event.is_set():
                        break
                    if next_state != self._state:
                        logger.debug(
                            f"⚙️ State: {self._state.value} → "
                            f"{next_state.value}"
                        )
                    self._state = next_state
                except asyncio.CancelledError:
                    logger.info("🛑 State machine cancelled.")
                    raise
                except Exception as e:
                    logger.error(
                        f"❌ Error in state {self._state.value}: {e}",
                        exc_info=True,
                    )
                    if self._stop_event.is_set():
                        break
                    # Recover: return to IDLE
                    self._state = RobotState.IDLE
                    await asyncio.sleep(2)
            else:
                logger.error(f"❌ No handler for state: {self._state}")
                break

    # ─────────────────────────────────────────
    # Entry Point — Start robot
    # ─────────────────────────────────────────
    async def run(self):
        """Start the full receptionist robot system.

        Flow:
          1. Connect to robot
          2. Initialize modules
          3. Run state machine as cancellable Task
          4. Graceful shutdown on Ctrl+C
        """
        print()
        print("╔══════════════════════════════════════════════╗")
        print("║     🤖 LAB RECEPTIONIST ROBOT               ║")
        print("║     Starting up...                          ║")
        print("╚══════════════════════════════════════════════╝")
        print()

        try:
            self._connection = RobotConnection(ip=self._robot_ip)
            async with self._connection as conn:
                self._init_modules()

                logger.info("📝 STT: English (robot built-in)")
                await self._action.say(
                    "Hello! I'm the Lab receptionist robot. "
                    "I'm ready to help!"
                )

                sm_task = asyncio.create_task(self._run_state_machine())

                loop = asyncio.get_running_loop()

                def _on_signal():
                    logger.info("\n🛑 Stop signal received (Ctrl+C)...")
                    self._running = False
                    self._stop_event.set()
                    sm_task.cancel()

                for sig in (signal.SIGINT, signal.SIGTERM):
                    loop.add_signal_handler(sig, _on_signal)

                try:
                    await sm_task
                except asyncio.CancelledError:
                    logger.info("🛑 State machine stopped.")

                logger.info("🛑 Shutting down...")
                try:
                    await asyncio.wait_for(
                        self._action.say("I'm going offline now. Goodbye!"),
                        timeout=8,
                    )
                except (asyncio.TimeoutError, Exception):
                    pass

        except ConnectionError as e:
            logger.error(f"🚫 {e}")
            print(f"\n❌ Connection error: {e}")
            print("   Check:")
            print(f"   1. Is the robot powered on and connected to WiFi?")
            print(f"   2. Is IP {self._robot_ip} correct?")
            print(f"   3. Are the PC and robot on the same network?")

        except Exception as e:
            logger.error(f"❌ System error: {e}", exc_info=True)

        finally:
            logger.info(
                f"📊 Session summary: served {self._session_count} visitor(s)."
            )
            print()
            print("╔══════════════════════════════════════════════╗")
            print(f"║  📊 Visitors served: {self._session_count}")
            print("║  🛑 System shut down.")
            print("╚══════════════════════════════════════════════╝")

    # ─────────────────────────────────────────
    # Utility: List robot actions
    # ─────────────────────────────────────────
    async def list_robot_actions(self):
        """Connect to robot and list all available actions."""
        self._connection = RobotConnection(ip=self._robot_ip)
        async with self._connection:
            action = ActionModule()
            print("\n══ BUILT-IN ACTIONS ══")
            await action.list_available_actions()
            print("\n══ CUSTOM ACTIONS ══")
            await action.list_custom_actions()


# ═════════════════════════════════════════════
# CLI Arguments
# ═════════════════════════════════════════════
def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="🤖 Lab Receptionist Robot — UBTECH Alpha Mini",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py                       # Run with default config
  python main.py --level 10            # Use LLM for Q&A
  python main.py --ip 192.168.1.50     # Change robot IP
  python main.py --list-actions        # View available actions
        """,
    )
    parser.add_argument(
        "--ip",
        type=str,
        default=ROBOT_IP,
        help=f"Robot IP address (default: {ROBOT_IP})",
    )
    parser.add_argument(
        "--level",
        type=int,
        default=QA_LEVEL,
        choices=[5, 10],
        help="Q&A Level: 5=Rule-based, 10=LLM (default: from .env)",
    )
    parser.add_argument(
        "--list-actions",
        action="store_true",
        help="List all robot actions and exit",
    )
    return parser.parse_args()


# ═════════════════════════════════════════════
# Entry Point
# ═════════════════════════════════════════════
def main():
    """Main entry point."""
    args = parse_args()

    robot = ReceptionRobot(
        robot_ip=args.ip,
        qa_level=args.level,
    )

    if args.list_actions:
        asyncio.run(robot.list_robot_actions())
    else:
        asyncio.run(robot.run())


if __name__ == "__main__":
    main()
