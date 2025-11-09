#!/usr/bin/env python3
"""Test script to verify real Gemini API integration."""

import asyncio
import sys

from app.services.gemini import get_gemini_service
from app.core.config import get_settings


async def test_real_gemini():
    """Test real Gemini API with a sample goal."""
    settings = get_settings()

    print("=" * 60)
    print("Testing Real Gemini API Integration")
    print("=" * 60)
    print(f"Project ID: {settings.PROJECT_ID}")
    print(f"Location: {settings.LOCATION}")
    print(f"Model: {settings.GEMINI_MODEL}")
    print(f"Mock Mode: {settings.USE_MOCK_GEMINI}")
    print("=" * 60)

    if settings.USE_MOCK_GEMINI:
        print("⚠️  WARNING: Mock mode is enabled!")
        print("Set USE_MOCK_GEMINI=false in .env to test real API")
        return 1

    try:
        gemini_service = get_gemini_service()

        # Test with a real marketing goal
        test_goal = "Launch awareness campaign for new AI-powered code assistant"

        print(f"\n📝 Test Goal: {test_goal}")
        print("\n🔄 Calling Gemini API...")

        task_list = await gemini_service.generate_task_list(test_goal)

        print("\n✅ SUCCESS! Gemini API Response:")
        print("=" * 60)
        print(f"Goal: {task_list.goal}")
        print(f"\nCaptions:")
        if task_list.captions:
            print(f"  - Count: {task_list.captions.n}")
            print(f"  - Style: {task_list.captions.style}")
        else:
            print("  - None")

        print(f"\nImage:")
        if task_list.image:
            print(f"  - Prompt: {task_list.image.prompt}")
            print(f"  - Size: {task_list.image.size}")
        else:
            print("  - None")

        print(f"\nVideo:")
        if task_list.video:
            print(f"  - Prompt: {task_list.video.prompt}")
            print(f"  - Duration: {task_list.video.duration_sec}s")
        else:
            print("  - None")

        print("\n" + "=" * 60)
        print("✅ Real Gemini API test PASSED!")
        print("=" * 60)

        return 0

    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        print(f"Error type: {type(e).__name__}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(test_real_gemini())
    sys.exit(exit_code)
