"""
Utility script to regression-test the voice command pipeline without needing a live microphone.

It launches ``python main.py`` and pipes a series of ``voice simulate`` commands into the CLI,
which exercises the exact same path that Bittu uses when actual speech is transcribed.
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent

DEFAULT_COMMANDS = [
    "Bittu open Google",
    "Bittu open YouTube",
    "Bittu open notepad",
    "Bittu set a alarm for 15 seconds",
]
# DEFAULT_COMMANDS = [
#     "Bittu open Google",
#     "Bittu open YouTube",
#     "Bittu open notepad",
#     "Bittu set a reminder for 15 seconds",
# ]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Feed echo commands into main.py via `voice simulate ...`."
    )
    parser.add_argument(
        "--commands",
        nargs="*",
        help="Commands to simulate (defaults exercise 4 voice requests).",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=20.0,
        help="Seconds to wait between commands for completion (default: 20.0).",
    )
    parser.add_argument(
        "--keep-alive",
        action="store_true",
        help="If set, keep main.py running after tests instead of sending 'exit'.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    commands = args.commands or DEFAULT_COMMANDS
    if not commands:
        print("No commands supplied.")
        return

    env = os.environ.copy()
    env.setdefault("VOICE_READY_PROMPT", "Waiting for your next command.")
    env.setdefault("VOICE_AUTO_LISTEN_AFTER_COMMAND", "1")
    # Fix Windows console encoding for emojis
    env.setdefault("PYTHONIOENCODING", "utf-8")

    process = subprocess.Popen(
        [sys.executable, "main.py"],
        cwd=PROJECT_ROOT,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
        encoding='utf-8',
        errors='replace',
        env=env,
    )

    output_lines = []
    
    def read_output():
        """Read and print output in real-time"""
        if process.stdout:
            try:
                while True:
                    line = process.stdout.readline()
                    if not line:
                        if process.poll() is not None:
                            break
                        continue
                    line_clean = line.rstrip()
                    if line_clean:
                        print(line_clean)
                        output_lines.append(line_clean)
            except Exception as e:
                print(f"⚠️ Error reading output: {e}")

    import threading
    output_thread = threading.Thread(target=read_output, daemon=True)
    output_thread.start()

    try:
        print("✅ Started main.py for echo testing.")
        # Wait a bit for initialization
        time.sleep(2)
        
        for idx, command in enumerate(commands, start=1):
            line = command.strip()
            if not line:
                continue
            payload = f"voice simulate {line}"
            print(f"\n{'='*60}")
            print(f"[{idx}/{len(commands)}] → {payload}")
            print(f"{'='*60}")
            if process.stdin:
                try:
                    process.stdin.write(payload + "\n")
                    process.stdin.flush()
                except (OSError, BrokenPipeError):
                    print(f"⚠️ Process ended before command {idx} could be sent")
                    break
            
            # Wait for command completion indicators
            max_wait = max(20.0, args.delay)
            wait_start = time.time()
            command_completed = False
            output_count_before = len(output_lines)
            
            while (time.time() - wait_start) < max_wait:
                time.sleep(0.5)
                # Check if we see NEW completion messages (after this command was sent)
                if len(output_lines) > output_count_before:
                    recent_output = "\n".join(output_lines[output_count_before:])
                    # Look for completion indicators that appeared AFTER we sent this command
                    if "Command completed" in recent_output or "Waiting for your next command" in recent_output:
                        # Also check that we see "Processing command" or "Step 5" to ensure it actually processed
                        if "Processing command" in recent_output or "Step 5" in recent_output or "_start_voice_task" in recent_output:
                            command_completed = True
                            print(f"✅ Command {idx} completed, proceeding to next...")
                            time.sleep(2)  # Longer pause to ensure TTS finishes
                            break
                if process.poll() is not None:
                    print(f"⚠️ Process ended while waiting for command {idx}")
                    break
            
            if not command_completed and (time.time() - wait_start) >= max_wait:
                print(f"⏱️ Timeout waiting for command {idx} to complete, proceeding anyway...")
                # Check if command at least started processing
                if len(output_lines) > output_count_before:
                    recent_output = "\n".join(output_lines[output_count_before:])
                    if "Step 3" in recent_output or "Step 4" in recent_output or "Step 5" in recent_output:
                        print(f"⚠️ Command {idx} started processing but didn't complete in time")
                    else:
                        print(f"⚠️ Command {idx} may not have started processing")
    except KeyboardInterrupt:
        print("\n⏹️  Interrupted by user.")
    finally:
        if not args.keep_alive and process.stdin:
            print("\n⏹️  Sending 'exit' command...")
            try:
                process.stdin.write("exit\n")
                process.stdin.flush()
                time.sleep(2)  # Give time for exit message
            except (OSError, BrokenPipeError):
                print("⚠️ Process already ended")
        try:
            process.wait(timeout=60)
        except subprocess.TimeoutExpired:
            print("⚠️ Process didn't exit in time, terminating...")
            process.terminate()
            process.wait(timeout=5)
        print("\n🧪 Voice echo test finished.")


if __name__ == "__main__":
    main()

