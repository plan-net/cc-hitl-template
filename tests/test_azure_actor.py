#!/usr/bin/env python3
"""
Test Azure Foundry integration with Ray Actor (non-containerized).

This test validates Layer 2: Ray Actor with env vars passthrough.
It does NOT require container builds - tests the create_actor code path directly.

Usage:
    # Option 1: Set env vars manually
    export CLAUDE_USE_AZURE_FOUNDRY=1
    export ANTHROPIC_FOUNDRY_BASE_URL="https://claude-sweden-gateway.azure-api.net/claude-sweden/anthropic"
    export ANTHROPIC_FOUNDRY_API_KEY="your-key"
    export CLAUDE_MODEL=sonnet
    python tests/test_azure_actor.py

    # Option 2: Source .env file (if configured for Azure)
    source .env
    python tests/test_azure_actor.py

    # Option 3: Run with pytest
    pytest tests/test_azure_actor.py -v -s
"""
import asyncio
import os
import sys
import uuid

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def check_azure_config() -> bool:
    """Check if Azure Foundry configuration is present."""
    use_azure = os.getenv("CLAUDE_USE_AZURE_FOUNDRY", "0") == "1"
    has_key = bool(os.getenv("ANTHROPIC_FOUNDRY_API_KEY"))
    has_url = bool(os.getenv("ANTHROPIC_FOUNDRY_BASE_URL"))

    if not use_azure:
        print("CLAUDE_USE_AZURE_FOUNDRY is not set to '1'")
        print("Set CLAUDE_USE_AZURE_FOUNDRY=1 to enable Azure Foundry testing")
        return False

    if not has_key:
        print("ANTHROPIC_FOUNDRY_API_KEY is not set")
        return False

    if not has_url:
        print("ANTHROPIC_FOUNDRY_BASE_URL is not set (using default)")

    return True


def check_public_config() -> bool:
    """Check if Public API configuration is present."""
    has_key = bool(os.getenv("ANTHROPIC_API_KEY"))

    if not has_key:
        print("ANTHROPIC_API_KEY is not set")
        return False

    return True


async def test_actor_creation(use_azure: bool = True):
    """
    Test creating an actor and getting a simple response.

    Args:
        use_azure: If True, test Azure Foundry; if False, test Public API
    """
    import ray

    # Initialize Ray (local mode for testing)
    if not ray.is_initialized():
        ray.init(ignore_reinit_error=True)

    # Import after Ray init
    from claude_hitl_template.agent import create_actor, cleanup_actor

    execution_id = f"test-{'azure' if use_azure else 'public'}-{uuid.uuid4().hex[:8]}"

    api_type = "Azure Foundry" if use_azure else "Public Anthropic"
    model_tier = os.getenv("CLAUDE_MODEL", "sonnet")

    print(f"\n{'='*60}")
    print(f"Testing {api_type} API")
    print(f"{'='*60}")
    print(f"Execution ID: {execution_id}")
    print(f"Model tier: {model_tier}")
    print(f"CPUs: {os.getenv('CLAUDE_ACTOR_CPUS', '1')}")
    print(f"Memory: {os.getenv('CLAUDE_ACTOR_MEMORY_GB', '1')}GB")
    print(f"{'='*60}\n")

    try:
        # Create actor WITHOUT container (use_container=False)
        print("Creating Ray actor...")
        actor = create_actor(execution_id, use_container=False)
        print(f"Actor created: claude-session-{execution_id}")

        # Get actor metadata to verify configuration
        print("\nVerifying actor configuration...")
        # Note: get_metadata requires connected client, skip for now

        # Connect and send simple query
        print(f"\nConnecting to Claude via {api_type}...")
        result = await actor.connect.remote(
            "Respond with exactly: 'API test successful - [API_TYPE]' "
            "replacing [API_TYPE] with either 'Azure Foundry' or 'Public API' "
            "based on which API you're using. Nothing else."
        )

        print(f"\nResponse status: {result['status']}")

        # Display user messages
        if result.get('user_messages'):
            print("\nClaude's response:")
            for msg in result['user_messages']:
                print(f"  {msg['content']}")

        # Display context messages (tool use, thinking, etc.)
        if result.get('context_messages'):
            print(f"\nContext messages: {len(result['context_messages'])} items")
            for ctx in result['context_messages'][:3]:  # Show first 3
                print(f"  - {ctx['type']}: {str(ctx.get('content', ctx.get('name', '')))[:50]}...")

        # Verify we got a response
        if result.get('user_messages'):
            print(f"\n{'='*60}")
            print(f"SUCCESS: {api_type} integration working!")
            print(f"{'='*60}")
            return True
        else:
            print(f"\n{'='*60}")
            print(f"FAILED: No response received from {api_type}")
            print(f"{'='*60}")
            return False

    except Exception as e:
        print(f"\n{'='*60}")
        print(f"ERROR: {type(e).__name__}: {e}")
        print(f"{'='*60}")
        import traceback
        traceback.print_exc()
        return False

    finally:
        # Cleanup
        print(f"\nCleaning up actor: {execution_id}")
        try:
            await cleanup_actor(execution_id)
            print("Cleanup complete")
        except Exception as e:
            print(f"Cleanup warning: {e}")


async def main():
    """Run the appropriate test based on environment configuration."""
    print("\n" + "="*60)
    print("Azure Foundry / Public API Integration Test")
    print("="*60)

    # Check which API is configured
    use_azure = os.getenv("CLAUDE_USE_AZURE_FOUNDRY", "0") == "1"

    if use_azure:
        print("\nMode: Azure Foundry (CLAUDE_USE_AZURE_FOUNDRY=1)")
        if not check_azure_config():
            print("\nAzure configuration incomplete. Exiting.")
            return False
    else:
        print("\nMode: Public API (CLAUDE_USE_AZURE_FOUNDRY=0 or unset)")
        if not check_public_config():
            print("\nPublic API configuration incomplete. Exiting.")
            return False

    # Run the test
    success = await test_actor_creation(use_azure=use_azure)

    return success


# Pytest-compatible test function
def test_azure_foundry_integration():
    """Pytest entry point for Azure Foundry test."""
    # Skip if not configured for Azure
    if os.getenv("CLAUDE_USE_AZURE_FOUNDRY", "0") != "1":
        import pytest
        pytest.skip("CLAUDE_USE_AZURE_FOUNDRY not set to 1")

    if not check_azure_config():
        import pytest
        pytest.skip("Azure Foundry configuration incomplete")

    success = asyncio.run(test_actor_creation(use_azure=True))
    assert success, "Azure Foundry integration test failed"


def test_public_api_integration():
    """Pytest entry point for Public API test."""
    # Skip if configured for Azure
    if os.getenv("CLAUDE_USE_AZURE_FOUNDRY", "0") == "1":
        import pytest
        pytest.skip("CLAUDE_USE_AZURE_FOUNDRY is set to 1 (Azure mode)")

    if not check_public_config():
        import pytest
        pytest.skip("Public API configuration incomplete")

    success = asyncio.run(test_actor_creation(use_azure=False))
    assert success, "Public API integration test failed"


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
