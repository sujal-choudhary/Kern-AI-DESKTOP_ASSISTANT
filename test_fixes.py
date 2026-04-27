#!/usr/bin/env python3
"""Quick test script to verify the fixes"""

import sys
import logging
from pathlib import Path

# Add project to path
sys.path.insert(0, str(Path(__file__).parent))

logging.basicConfig(level=logging.INFO, format='%(levelname)s - %(message)s')

def test_command_parsing():
    """Test if music commands are parsed correctly"""
    from core.commands import parse_command
    
    test_cases = [
        ("play despacito", "Should parse as music search"),
        ("search for uptown funk", "Should parse as music search"),
        ("play song thriller", "Should parse as music search"),
        ("search despacito on youtube", "Should parse as YouTube search"),
    ]
    
    print("\n=== Testing Command Parsing ===")
    for command, description in test_cases:
        result = parse_command(command)
        if result:
            print(f"✓ '{command}' -> {description}")
            print(f"  Result: {result}")
        else:
            print(f"✗ '{command}' -> Failed to parse")
    print()

def test_actions_import():
    """Test if actions module imports correctly with fixes"""
    print("=== Testing Actions Module ===")
    try:
        from core import actions
        print("✓ actions.py imported successfully")
        
        # Check if functions exist
        functions = ['close_app', 'open_app', 'youtube_search', 'open_url']
        for func in functions:
            if hasattr(actions, func):
                print(f"  ✓ {func} found")
            else:
                print(f"  ✗ {func} NOT found")
    except Exception as e:
        print(f"✗ Error importing actions: {e}")
    print()

def test_command_module():
    """Test if commands module imports correctly with music support"""
    print("=== Testing Commands Module ===")
    try:
        from core import commands
        print("✓ commands.py imported successfully")
        
        # Check parse_command exists
        if hasattr(commands, 'parse_command'):
            print("  ✓ parse_command function found")
        else:
            print("  ✗ parse_command function NOT found")
    except Exception as e:
        print(f"✗ Error importing commands: {e}")
    print()

if __name__ == "__main__":
    print("=" * 50)
    print("MENU ASSISTANT - FIXES VERIFICATION TEST")
    print("=" * 50)
    
    test_actions_import()
    test_command_module()
    test_command_parsing()
    
    print("=" * 50)
    print("TEST COMPLETE")
    print("=" * 50)
