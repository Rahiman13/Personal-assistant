"""Quick diagnostic script for VoiceAssistant settings."""

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from voice import VoiceAssistant

def main() -> None:
    # Ensure default behavior (no override)
    os.environ.pop("VOICE_ALLOW_LISTEN_DURING_TTS", None)
    assistant = VoiceAssistant(lambda text: None)
    print("VOICE_ALLOW_LISTEN_DURING_TTS env:", os.getenv("VOICE_ALLOW_LISTEN_DURING_TTS"))
    print("_allow_listen_during_tts internal flag:", assistant._allow_listen_during_tts)

if __name__ == "__main__":
    main()

