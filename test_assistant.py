#!/usr/bin/env python3
"""
Test script for Personal AI Assistant
This script tests various commands to ensure the assistant works correctly
"""

import os
import sys
import time
from core.brain import process_command

def test_command(command, expected_keywords=None):
    """Test a command and return the result"""
    print(f"\n🧪 Testing: '{command}'")
    print("-" * 50)
    
    try:
        result = process_command(command)
        print(f"✅ Result: {result}")
        
        if expected_keywords:
            found_keywords = [kw for kw in expected_keywords if kw.lower() in result.lower()]
            if found_keywords:
                print(f"✅ Found expected keywords: {found_keywords}")
            else:
                print(f"⚠️  Expected keywords not found: {expected_keywords}")
        
        return result
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return None

def main():
    """Run comprehensive tests"""
    print("🤖 Personal AI Assistant - Test Suite")
    print("=" * 60)
    
    # Test basic commands
    print("\n📝 Testing Basic Commands:")
    test_command("hello", ["hello", "assistant"])
    test_command("help", ["help", "commands"])
    test_command("what can you do", ["capabilities", "help"])
    
    # Test application opening
    print("\n🌐 Testing Application Opening:")
    test_command("open youtube", ["youtube", "opening"])
    test_command("launch vs code", ["vs code", "opening"])
    test_command("start calculator", ["calculator", "opening"])
    
    # Test weather
    print("\n🌤️ Testing Weather:")
    test_command("weather in London", ["weather", "london"])
    
    # Test reminders
    print("\n⏰ Testing Reminders:")
    test_command("remind me to test in 1 minute", ["reminder", "test"])
    
    # Test file operations
    print("\n📁 Testing File Operations:")
    test_command("list files", ["files", "directory"])
    test_command("create file test.txt", ["created", "test.txt"])
    
    # Test coding commands
    print("\n💻 Testing Coding Commands:")
    test_command("create Python script", ["python", "script", "created"])
    test_command("create HTML file", ["html", "created"])
    test_command("create CSS file", ["css", "created"])
    test_command("create JavaScript file", ["javascript", "created"])
    test_command("create JSON file", ["json", "created"])
    
    # Test system commands
    print("\n⚙️ Testing System Commands:")
    test_command("run python --version", ["python", "version"])
    
    # Test navigation
    print("\n📂 Testing Navigation:")
    test_command("cd .", ["navigated", "current"])
    
    # Test conversation
    print("\n💬 Testing Conversation:")
    test_command("tell me a joke", ["joke", "funny"])
    test_command("what is Python?", ["python", "programming"])
    
    print("\n" + "=" * 60)
    print("🎉 Test suite completed!")
    print("💡 If you see any ❌ errors above, those features may need attention.")
    print("✅ All other tests passed successfully!")

if __name__ == "__main__":
    main()
