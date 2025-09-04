#!/usr/bin/env python3
"""
Test script to verify LLM provider functionality
Tests OpenAI, Groq, and Gemini providers with fallback behavior
"""
import os
from utils.llm_provider import LLMProvider, reset_llm_provider

def test_provider(provider_name: str, api_key_name: str, test_key: str = "test_key"):
    """Test a specific LLM provider"""
    print(f"\n🧪 Testing {provider_name} Provider")
    print("-" * 40)
    
    # Set test API key
    original_key = os.environ.get(api_key_name)
    os.environ[api_key_name] = test_key
    
    try:
        # Reset and create new provider
        reset_llm_provider()
        provider = LLMProvider(preferred_provider=provider_name.lower())
        
        info = provider.get_provider_info()
        print(f"Active Provider: {info['active_provider']}")
        print(f"Model: {info['model']}")
        print(f"Available: {info['available']}")
        
        if provider.is_available():
            # Test simple invocation (will fail with test key but shows structure)
            try:
                response = provider.invoke("Hello, this is a test message")
                print(f"Response: {response}")
            except Exception as e:
                print(f"Expected error with test key: {type(e).__name__}")
        
    finally:
        # Restore original key
        if original_key:
            os.environ[api_key_name] = original_key
        else:
            os.environ.pop(api_key_name, None)

def test_fallback_behavior():
    """Test fallback behavior when no providers are available"""
    print(f"\n🧪 Testing Fallback Behavior")
    print("-" * 40)
    
    # Remove all API keys temporarily
    original_keys = {}
    key_names = ["OPENAI_API_KEY", "GROQ_API_KEY", "GOOGLE_API_KEY", "GEMINI_API_KEY"]
    
    for key_name in key_names:
        original_keys[key_name] = os.environ.get(key_name)
        os.environ.pop(key_name, None)
    
    try:
        reset_llm_provider()
        provider = LLMProvider()
        
        info = provider.get_provider_info()
        print(f"Active Provider: {info['active_provider']}")
        print(f"Available: {info['available']}")
        
        response = provider.invoke("Test message")
        print(f"Response: {response}")
        
    finally:
        # Restore original keys
        for key_name, original_value in original_keys.items():
            if original_value:
                os.environ[key_name] = original_value

def test_priority_system():
    """Test provider priority system"""
    print(f"\n🧪 Testing Provider Priority System")
    print("-" * 40)
    
    # Set multiple API keys
    test_keys = {
        "OPENAI_API_KEY": "test_openai_key",
        "GROQ_API_KEY": "test_groq_key", 
        "GOOGLE_API_KEY": "test_google_key"
    }
    
    original_keys = {}
    for key_name, test_key in test_keys.items():
        original_keys[key_name] = os.environ.get(key_name)
        os.environ[key_name] = test_key
    
    try:
        # Test default priority (should pick OpenAI first)
        reset_llm_provider()
        provider = LLMProvider()
        info = provider.get_provider_info()
        print(f"Default priority - Active Provider: {info['active_provider']}")
        
        # Test preferred provider
        reset_llm_provider()
        provider = LLMProvider(preferred_provider="groq")
        info = provider.get_provider_info()
        print(f"Preferred Groq - Active Provider: {info['active_provider']}")
        
        reset_llm_provider()
        provider = LLMProvider(preferred_provider="gemini")
        info = provider.get_provider_info()
        print(f"Preferred Gemini - Active Provider: {info['active_provider']}")
        
    finally:
        # Restore original keys
        for key_name, original_value in original_keys.items():
            if original_value:
                os.environ[key_name] = original_value
            else:
                os.environ.pop(key_name, None)

if __name__ == "__main__":
    print("🚀 LLM Provider System Test")
    print("=" * 50)
    
    # Test individual providers
    test_provider("OpenAI", "OPENAI_API_KEY")
    test_provider("Groq", "GROQ_API_KEY") 
    test_provider("Gemini", "GOOGLE_API_KEY")
    
    # Test fallback behavior
    test_fallback_behavior()
    
    # Test priority system
    test_priority_system()
    
    print(f"\n✅ All tests completed!")
    print("=" * 50)
