#!/usr/bin/env python3
"""
test_openrouter.py — Test OpenRouter Llama integration
Tests the connection to OpenRouter with the new Llama credentials
"""

import os
import json
import sys
from pathlib import Path

# Add the .claude settings to environment
settings_path = Path(__file__).parent / ".claude" / "settings.local.json"
if settings_path.exists():
    with open(settings_path, "r") as f:
        settings = json.load(f)
        for key, value in settings.get("env", {}).items():
            os.environ[key] = value
            print(f"✓ Set {key}")

# Test imports
try:
    import requests
    print("✓ requests library available")
except ImportError:
    print("✗ requests library not found. Install with: pip install requests")
    sys.exit(1)

# Test OpenRouter connection
def test_openrouter():
    """Test basic OpenRouter connectivity with Llama model"""
    api_key = os.getenv("ANTHROPIC_API_KEY")
    api_base = os.getenv("ANTHROPIC_BASE_URL")
    model = os.getenv("LLM_MODEL", "meta-llama/llama-4-scout-17b-16e-instruct")
    
    if not api_key:
        print("✗ ANTHROPIC_API_KEY not set in settings")
        return False
    
    if not api_base:
        print("✗ ANTHROPIC_BASE_URL not set in settings")
        return False
    
    print(f"\n📡 Testing OpenRouter Connection:")
    print(f"  API Base: {api_base}")
    print(f"  Model: {model}")
    print(f"  API Key: {api_key[:10]}...{api_key[-4:]}")
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    
    payload = {
        "model": model,
        "messages": [
            {
                "role": "user",
                "content": "Say 'Hello from OpenRouter Llama!' in one sentence."
            }
        ],
        "max_tokens": 256,
        "temperature": 0.7,
    }
    
    try:
        response = requests.post(
            f"{api_base}/chat/completions",
            headers=headers,
            json=payload,
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            message = result.get("choices", [{}])[0].get("message", {}).get("content", "")
            print(f"\n✓ OpenRouter Connection Successful!")
            print(f"\nResponse from Llama:")
            print(f"  {message}")
            return True
        else:
            print(f"\n✗ OpenRouter API Error (Status {response.status_code}):")
            print(f"  {response.text}")
            return False
            
    except requests.exceptions.Timeout:
        print(f"\n✗ Request timeout. OpenRouter may be unreachable or slow.")
        return False
    except requests.exceptions.ConnectionError:
        print(f"\n✗ Connection error. Check your internet connection and API base URL.")
        return False
    except Exception as e:
        print(f"\n✗ Unexpected error: {e}")
        return False

if __name__ == "__main__":
    print("=" * 60)
    print("OpenRouter Llama Integration Test")
    print("=" * 60)
    
    success = test_openrouter()
    
    print("\n" + "=" * 60)
    if success:
        print("✓ All tests passed! OpenRouter is configured correctly.")
        print("=" * 60)
        sys.exit(0)
    else:
        print("✗ Tests failed. Please check your configuration.")
        print("=" * 60)
        sys.exit(1)
