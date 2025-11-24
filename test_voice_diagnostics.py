#!/usr/bin/env python3
"""
Diagnostic script to test voice assistant and identify issues
"""

import sys
import os
import time

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_microphone():
    """Test if microphone is accessible"""
    print("=" * 60)
    print("Testing Microphone Access")
    print("=" * 60)
    
    try:
        import speech_recognition as sr
        print("✅ SpeechRecognition module imported")
    except ImportError:
        print("❌ FAILED: speech_recognition module not installed")
        print("   Install with: pip install SpeechRecognition")
        return False
    
    try:
        r = sr.Recognizer()
        print("✅ Recognizer created")
    except Exception as e:
        print(f"❌ FAILED: Could not create Recognizer: {e}")
        return False
    
    try:
        mic = sr.Microphone()
        print("✅ Microphone object created")
    except Exception as e:
        print(f"❌ FAILED: Could not access microphone: {e}")
        print("   Check microphone permissions in Windows settings")
        return False
    
    try:
        with mic as source:
            print("   Adjusting for ambient noise (2 seconds)...")
            r.adjust_for_ambient_noise(source, duration=2)
            print("✅ Microphone calibrated")
    except Exception as e:
        print(f"⚠️  WARNING: Could not calibrate microphone: {e}")
        print("   This might still work, but accuracy may be reduced")
    
    print("\n✅ Microphone test PASSED")
    return True

def test_voice_assistant():
    """Test voice assistant initialization and startup"""
    print("\n" + "=" * 60)
    print("Testing Voice Assistant")
    print("=" * 60)
    
    from voice import VoiceAssistant
    
    callback_received = []
    
    def test_callback(text: str):
        callback_received.append(text)
        print(f"\n{'='*60}")
        print(f"✅ CALLBACK RECEIVED: '{text}'")
        print(f"{'='*60}\n")
    
    print("\n1. Creating VoiceAssistant...")
    try:
        va = VoiceAssistant(test_callback)
        print("✅ VoiceAssistant created")
    except Exception as e:
        print(f"❌ FAILED: Could not create VoiceAssistant: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    print("\n2. Checking diagnostics...")
    diag = va.diagnostics()
    print(diag)
    
    print("\n3. Starting voice assistant...")
    try:
        if va.start():
            print("✅ Voice assistant started")
        else:
            print("❌ FAILED: Voice assistant failed to start")
            print(f"   Error: {va.last_error}")
            return False
    except Exception as e:
        print(f"❌ FAILED: Exception while starting: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    print("\n4. Verifying voice assistant is running...")
    time.sleep(2)  # Give it time to start
    
    if va.is_running():
        print("✅ Voice assistant is running")
    else:
        print("❌ FAILED: Voice assistant is NOT running")
        print("   Attempting restart...")
        if va.restart():
            print("✅ Restarted successfully")
            time.sleep(1)
        else:
            print("❌ Restart failed")
            return False
    
    print("\n5. Checking callback attachment...")
    if va.on_transcript == test_callback:
        print("✅ Callback is properly attached")
    else:
        print("⚠️  WARNING: Callback may not be properly attached")
        print(f"   Expected: {test_callback}")
        print(f"   Got: {va.on_transcript}")
    
    print("\n6. Testing voice input (15 seconds)...")
    print("   Please say 'Bittu' followed by a command")
    print("   Or say anything to test if the assistant is listening")
    print("   Listening...")
    
    start_time = time.time()
    while time.time() - start_time < 15:
        if callback_received:
            print(f"\n✅ SUCCESS! Voice assistant received: '{callback_received[-1]}'")
            print("   Voice assistant is working correctly!")
            va.stop()
            return True
        time.sleep(0.5)
    
    if not callback_received:
        print("\n⚠️  No voice input received in 15 seconds")
        print("   Possible issues:")
        print("   - Microphone not picking up sound")
        print("   - Speech recognition service unavailable")
        print("   - Background noise too high")
        print("   - Microphone permissions not granted")
    
    print("\n7. Cleaning up...")
    va.stop()
    
    return len(callback_received) > 0

def main():
    """Run all diagnostic tests"""
    print("\n" + "=" * 60)
    print("Voice Assistant Diagnostic Tool")
    print("=" * 60)
    print("\nThis script will test:")
    print("1. Microphone access")
    print("2. Voice assistant initialization")
    print("3. Voice assistant startup")
    print("4. Voice input reception")
    print("\n" + "=" * 60 + "\n")
    
    # Test microphone
    mic_ok = test_microphone()
    if not mic_ok:
        print("\n❌ Microphone test failed. Please fix microphone issues first.")
        return False
    
    # Test voice assistant
    va_ok = test_voice_assistant()
    
    print("\n" + "=" * 60)
    if va_ok:
        print("✅ ALL TESTS PASSED")
        print("   Voice assistant should be working correctly")
    else:
        print("⚠️  SOME TESTS FAILED OR INCONCLUSIVE")
        print("   Check the output above for specific issues")
    print("=" * 60)
    
    return va_ok

if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ TEST FAILED with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

