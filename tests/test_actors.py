"""
Integration tests for ClaudeSessionActor with real Ray cluster.

These tests verify:
- Actor creation and retrieval
- Connect and query operations
- Timeout detection
- Cleanup functionality
- Actor crash recovery

NOTE: These tests require a running Ray cluster and Claude Code CLI authentication.
"""
import ray
import pytest
import asyncio
from claude_hitl_template.agent import (
    ClaudeSessionActor,
    create_actor,
    get_actor,
    cleanup_actor
)


@pytest.fixture(scope="module")
def ray_cluster():
    """
    Initialize Ray for testing.

    This fixture:
    - Starts Ray if not already running
    - Yields to tests
    - Shuts down Ray after all tests complete
    """
    if not ray.is_initialized():
        ray.init(ignore_reinit_error=True)
    yield
    # Note: Don't shutdown Ray here - it may be used by other services
    # ray.shutdown()


def test_environment_requirements():
    """
    Verify that all system dependencies are available.

    This test checks for:
    - Node.js 18+
    - Claude Code CLI
    - ANTHROPIC_API_KEY environment variable

    These are REQUIRED for ClaudeSessionActor to work.
    """
    import subprocess
    import os

    # Check Node.js
    try:
        result = subprocess.run(
            ["node", "--version"],
            capture_output=True,
            text=True,
            timeout=5
        )
        assert result.returncode == 0, "Node.js not found. Install Node.js 18+ from https://nodejs.org"

        # Parse version (format: v18.x.x)
        version = result.stdout.strip()
        major_version = int(version.split('.')[0].replace('v', ''))
        assert major_version >= 18, f"Node.js version {version} is too old. Need 18+"

    except FileNotFoundError:
        pytest.fail("Node.js not found. Install with: apt-get install nodejs (or brew install node)")
    except subprocess.TimeoutExpired:
        pytest.fail("Node.js command timed out")

    # Check Claude Code CLI
    try:
        result = subprocess.run(
            ["claude", "--version"],
            capture_output=True,
            text=True,
            timeout=5
        )
        assert result.returncode == 0, "Claude CLI not found. Install with: npm install -g @anthropic-ai/claude-code"

    except FileNotFoundError:
        pytest.fail("Claude Code CLI not found. Install with: npm install -g @anthropic-ai/claude-code")
    except subprocess.TimeoutExpired:
        pytest.fail("Claude CLI command timed out")

    # Check ANTHROPIC_API_KEY
    api_key = os.getenv("ANTHROPIC_API_KEY")
    assert api_key, (
        "ANTHROPIC_API_KEY not set. "
        "1. Create .env file from .env.example "
        "2. Add your API key "
        "3. Run: source .env && export ANTHROPIC_API_KEY"
    )
    assert api_key.startswith("sk-ant-"), "ANTHROPIC_API_KEY should start with 'sk-ant-'"


def test_ray_worker_can_find_binaries(ray_cluster):
    """
    Verify Ray workers can access node and claude binaries.

    This test runs IN a Ray worker (isolated virtualenv) to verify that
    the PATH environment variable is correctly configured in runtime_env,
    allowing ClaudeSDKClient subprocess to find system binaries.
    """
    import subprocess
    import os

    @ray.remote
    def check_binaries():
        """This function runs in Ray worker's isolated virtualenv"""
        import subprocess
        import os

        # Try to find node binary
        node_result = subprocess.run(
            ["which", "node"],
            capture_output=True,
            text=True,
            timeout=5
        )

        # Try to find claude binary
        claude_result = subprocess.run(
            ["which", "claude"],
            capture_output=True,
            text=True,
            timeout=5
        )

        return {
            "node_found": node_result.returncode == 0,
            "node_path": node_result.stdout.strip() if node_result.returncode == 0 else None,
            "claude_found": claude_result.returncode == 0,
            "claude_path": claude_result.stdout.strip() if claude_result.returncode == 0 else None,
            "worker_path": os.environ.get("PATH", ""),
        }

    # Run check in Ray worker
    result = ray.get(check_binaries.remote())

    # Verify node is found
    assert result["node_found"], (
        f"Node.js not found in Ray worker. "
        f"Add PATH to runtime_env in claude_hitl_template.yaml. "
        f"Worker PATH: {result['worker_path']}"
    )

    # Verify claude is found
    assert result["claude_found"], (
        f"Claude CLI not found in Ray worker. "
        f"Add PATH to runtime_env in claude_hitl_template.yaml. "
        f"Worker PATH: {result['worker_path']}"
    )

    print(f"✅ Node.js found at: {result['node_path']}")
    print(f"✅ Claude CLI found at: {result['claude_path']}")


@pytest.mark.asyncio
async def test_actor_creation(ray_cluster):
    """Test that actor can be created with unique name."""
    exec_id = "test-creation-001"

    try:
        # Create actor
        actor = create_actor(exec_id)
        assert actor is not None, "Actor creation should return handle"

        # Verify actor exists
        retrieved = get_actor(exec_id)
        assert retrieved is not None, "Created actor should be retrievable"

    finally:
        # Cleanup
        await cleanup_actor(exec_id)


@pytest.mark.asyncio
async def test_actor_retrieval(ray_cluster):
    """Test that actors can be retrieved by execution ID."""
    exec_id = "test-retrieval-001"

    try:
        # Before creation
        actor = get_actor(exec_id)
        assert actor is None, "Non-existent actor should return None"

        # Create actor
        created = create_actor(exec_id)

        # After creation
        retrieved = get_actor(exec_id)
        assert retrieved is not None, "Created actor should be retrievable"

    finally:
        await cleanup_actor(exec_id)


@pytest.mark.asyncio
async def test_actor_connect_simple(ray_cluster):
    """
    Test that actor can connect to Claude SDK and return response.

    NOTE: This test requires Claude Code CLI to be authenticated.
    """
    exec_id = "test-connect-001"

    try:
        # Create actor
        actor = create_actor(exec_id)

        # Connect with simple prompt
        result = await actor.connect.remote("Say 'Hello, World!' and nothing else.")

        # Verify result structure
        assert isinstance(result, dict), "Result should be dict"
        assert "status" in result, "Result should have status"
        assert "messages" in result, "Result should have messages"
        assert result["status"] in ["ready", "complete"], f"Status should be ready or complete, got: {result['status']}"

        # Should have at least one message
        assert len(result["messages"]) > 0, "Should receive at least one message from Claude"

    finally:
        await cleanup_actor(exec_id)


@pytest.mark.asyncio
async def test_actor_query(ray_cluster):
    """Test that actor can handle query after connect."""
    exec_id = "test-query-001"

    try:
        actor = create_actor(exec_id)

        # Connect first
        await actor.connect.remote("Let's have a simple conversation.")

        # Send query
        result = await actor.query.remote("What is 2+2? Answer only with the number.")

        # Verify response
        assert isinstance(result, dict), "Query result should be dict"
        assert "status" in result, "Query result should have status"
        assert "messages" in result, "Query result should have messages"

    finally:
        await cleanup_actor(exec_id)


@pytest.mark.asyncio
async def test_actor_timeout_not_triggered_immediately(ray_cluster):
    """Test that timeout is not triggered immediately after creation."""
    exec_id = "test-timeout-001"

    try:
        actor = create_actor(exec_id)

        # Check timeout immediately (should be False)
        is_timeout = await actor.check_timeout.remote()
        assert is_timeout is False, "Timeout should not be triggered immediately"

    finally:
        await cleanup_actor(exec_id)


@pytest.mark.asyncio
async def test_actor_disconnect(ray_cluster):
    """Test that actor can disconnect cleanly."""
    exec_id = "test-disconnect-001"

    try:
        actor = create_actor(exec_id)

        # Connect
        await actor.connect.remote("Hello")

        # Disconnect
        result = await actor.disconnect.remote()
        assert result["status"] == "disconnected", "Should return disconnected status"

    finally:
        await cleanup_actor(exec_id)


@pytest.mark.asyncio
async def test_cleanup_removes_actor(ray_cluster):
    """Test that cleanup_actor removes actor from Ray."""
    exec_id = "test-cleanup-001"

    # Create actor
    actor = create_actor(exec_id)
    assert get_actor(exec_id) is not None, "Actor should exist after creation"

    # Cleanup
    await cleanup_actor(exec_id)

    # Verify removed
    assert get_actor(exec_id) is None, "Actor should not exist after cleanup"


@pytest.mark.asyncio
async def test_cleanup_idempotent(ray_cluster):
    """Test that cleanup is safe to call multiple times."""
    exec_id = "test-cleanup-idempotent-001"

    # Create and cleanup
    actor = create_actor(exec_id)
    await cleanup_actor(exec_id)

    # Cleanup again (should not raise error)
    await cleanup_actor(exec_id)

    # Cleanup non-existent actor (should not raise error)
    await cleanup_actor("non-existent-id")


@pytest.mark.asyncio
async def test_message_types(ray_cluster):
    """Test that different message types are properly serialized."""
    exec_id = "test-message-types-001"

    try:
        actor = create_actor(exec_id)

        # Connect with prompt that should trigger text response
        result = await actor.connect.remote("Respond with: 'This is a text message'")

        # Check message structure
        for msg in result["messages"]:
            assert "type" in msg, "Message should have type"
            assert "content" in msg, "Message should have content"
            assert msg["type"] in ["text", "tool"], f"Message type should be text or tool, got: {msg['type']}"

    finally:
        await cleanup_actor(exec_id)


@pytest.mark.asyncio
async def test_actor_error_on_query_without_connect(ray_cluster):
    """Test that querying without connecting raises error."""
    exec_id = "test-error-no-connect-001"

    try:
        actor = create_actor(exec_id)

        # Try to query without connecting (should raise RuntimeError)
        with pytest.raises(Exception):  # Will be RuntimeError wrapped in Ray exception
            await actor.query.remote("This should fail")

    finally:
        await cleanup_actor(exec_id)


def test_actor_name_format():
    """Test that actor naming follows expected pattern."""
    exec_id = "test-123"
    actor = create_actor(exec_id)

    # Actor should be retrievable with same ID
    retrieved = get_actor(exec_id)
    assert retrieved is not None

    # Different ID should not retrieve same actor
    other = get_actor("different-id")
    assert other is None

    # Cleanup
    import asyncio
    asyncio.run(cleanup_actor(exec_id))
