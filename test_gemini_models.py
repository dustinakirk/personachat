#!/usr/bin/env python3
"""Test script to verify all three Gemini models are working correctly."""

import sys
import os
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from app.services.gemini_service import GeminiService
from app.config import Config

def test_model(service, model_name, prompt="Say 'Hello' in exactly 3 words."):
    """Test a specific model."""
    print(f"\n{'='*60}")
    print(f"Testing Model: {model_name}")
    print(f"{'='*60}")
    print(f"Prompt: {prompt}")
    print("-" * 60)

    # Test non-streaming
    print("\n[Non-Streaming Response]")
    result = service.generate_response(prompt, model=model_name)

    if result.success:
        print(f"✓ Success!")
        print(f"Response: {result.data}")
    else:
        print(f"✗ Failed!")
        print(f"Error: {result.error}")
        return False

    # Test streaming
    print("\n[Streaming Response]")
    try:
        streaming_text = ""
        for chunk in service.generate_streaming_response(prompt, model=model_name):
            streaming_text += chunk
            print(chunk, end="", flush=True)
        print()  # New line after streaming
        print(f"✓ Streaming successful!")
        print(f"Total streamed length: {len(streaming_text)} characters")
    except Exception as e:
        print(f"✗ Streaming failed!")
        print(f"Error: {str(e)}")
        return False

    return True

def main():
    """Main test function."""
    print("\n" + "="*60)
    print("GEMINI MODEL INTEGRATION TEST")
    print("="*60)

    # Initialize service
    api_key = Config.GEMINI_API_KEY
    if not api_key:
        print("✗ ERROR: GEMINI_API_KEY not set in environment!")
        print("Please set GEMINI_API_KEY in your .env file")
        return 1

    print(f"\n✓ API Key found: {api_key[:10]}...{api_key[-10:]}")

    service = GeminiService(api_key=api_key)

    if not service.is_configured:
        print("✗ ERROR: GeminiService failed to initialize!")
        return 1

    print(f"✓ GeminiService initialized successfully")
    print(f"✓ Default model: {service.default_model}")
    print(f"✓ Available models: {', '.join(service.available_models)}")

    # Test each model
    test_prompt = "What is 2+2? Answer in exactly 5 words."

    results = {}
    for model in service.available_models:
        results[model] = test_model(service, model, test_prompt)

    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)

    all_passed = True
    for model, passed in results.items():
        status = "✓ PASSED" if passed else "✗ FAILED"
        print(f"{model}: {status}")
        if not passed:
            all_passed = False

    print("="*60)

    if all_passed:
        print("\n🎉 All tests passed! All Gemini models are working correctly.")
        return 0
    else:
        print("\n⚠️  Some tests failed. Please check the errors above.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
