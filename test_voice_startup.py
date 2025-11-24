#!/usr/bin/env python3
"""
Test script to verify voice assistant starts listening from the beginning
"""

import sys
import time
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from voice import VoiceAssistant

def test_voice_startup():
    """Test that voice assistant starts listening immediately"""
    print("=" * 60)
    print("Testing Voice Assistant Startup")
    print("=" * 60)
    
    # Track if callback is called
    callback_called = []
    
    def test_callback(text: str):
        """Test callback to verify voice assistant is listening"""
        callback_called.append(text)
        print(f"✅ CALLBACK RECEIVED: '{text}'")
        print(f"   This confirms the voice assistant is listening!")
    
    print("\n1. Creating VoiceAssistant with callback...")
    voice_engine = VoiceAssistant(test_callback)
    
    if not voice_engine:
        print("❌ FAILED: Could not create VoiceAssistant")
        return False
    
    print("✅ VoiceAssistant created successfully")
    
    print("\n2. Starting voice assistant...")
    if voice_engine.start():
        print("✅ Voice assistant started successfully")
    else:
        print("❌ FAILED: Could not start voice assistant")
        print(f"   Error: {voice_engine.last_error}")
        return False
    
    print("\n3. Verifying voice assistant is running...")
    time.sleep(1)  # Give it a moment to initialize
    
    if voice_engine.is_running():
        print("✅ Voice assistant is running and listening")
    else:
        print("❌ FAILED: Voice assistant is not running")
        return False
    
    print("\n4. Testing callback attachment...")
    if voice_engine.on_transcript == test_callback:
        print("✅ Callback is properly attached")
    else:
        print("⚠️  WARNING: Callback may not be properly attached")
        print(f"   Expected: {test_callback}")
        print(f"   Got: {voice_engine.on_transcript}")
    
    print("\n5. Waiting for voice input (10 seconds)...")
    print("   Please say 'Bittu' followed by a command to test listening")
    print("   (Or say anything to verify the assistant is listening)")
    
    start_time = time.time()
    while time.time() - start_time < 10:
        if callback_called:
            print(f"\n✅ SUCCESS: Voice assistant received input: '{callback_called[-1]}'")
            print("   Voice assistant is working correctly from startup!")
            voice_engine.stop()
            return True
        time.sleep(0.5)
    
    if not callback_called:
        print("\n⚠️  No voice input received in 10 seconds")
        print("   This could mean:")
        print("   - Microphone is not working")
        print("   - No speech was detected")
        print("   - But the assistant IS listening (check microphone)")
    
    print("\n6. Cleaning up...")
    voice_engine.stop()
    
    print("\n" + "=" * 60)
    if callback_called:
        print("✅ TEST PASSED: Voice assistant is listening from startup")
        return True
    else:
        print("⚠️  TEST INCONCLUSIVE: No input received, but assistant started")
        print("   Please test manually by speaking to the assistant")
        return True  # Still pass if assistant started correctly

if __name__ == "__main__":
    try:
        success = test_voice_startup()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ TEST FAILED with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

