"""
Claude Agent SDK integration using Ray Actors for persistent sessions.

This module contains all Claude SDK-related logic:
- ClaudeSessionActor: Ray Actor managing persistent Claude SDK subprocess
- Helper functions: create_actor, get_actor, cleanup_actor

The Ray Actor pattern solves the subprocess lifecycle problem by:
1. Running Claude SDK in a dedicated, persistent Ray worker process
2. Maintaining subprocess state across Kodosumi HITL pauses
3. Surviving worker state changes during long conversations
"""
import ray
import time
import os
from typing import Optional, Dict, List
from claude_agent_sdk import (
    ClaudeSDKClient,
    ClaudeAgentOptions,
    AssistantMessage,
    TextBlock,
    ThinkingBlock,
    ToolUseBlock,
    ToolResultBlock,
    SystemMessage,
    ResultMessage
)


@ray.remote
class ClaudeSessionActor:
    """
    Persistent Ray Actor managing a single Claude SDK session.

    This actor:
    - Owns a ClaudeSDKClient instance with subprocess
    - Maintains conversation state across HITL pauses
    - Collects messages until ready for user input
    - Handles timeout detection
    - Manages subprocess cleanup

    Lifecycle:
    1. Created via create_actor() with unique execution_id
    2. connect() initializes Claude SDK subprocess
    3. query() sends messages and collects responses
    4. disconnect() cleans up subprocess
    5. Actor killed via cleanup_actor()
    """

    def __init__(self, cwd: Optional[str] = None, permission_mode: str = "acceptEdits"):
        """
        Initialize actor (subprocess not started yet).

        Args:
            cwd: Working directory for Claude SDK (default: current dir)
            permission_mode: Claude permission mode ("acceptEdits" or "plan")
        """
        self.options = ClaudeAgentOptions(
            permission_mode=permission_mode,
            cwd=cwd or os.getcwd()
        )
        self.client: Optional[ClaudeSDKClient] = None
        self.connected = False
        self.last_activity = time.time()
        self.timeout_seconds = 660  # 11 minutes (10 min conversation + 1 min buffer)

    async def connect(self, prompt: str) -> Dict:
        """
        Start Claude SDK session with initial prompt.

        This method:
        1. Creates ClaudeSDKClient instance
        2. Spawns Claude Code CLI subprocess with connect(None)
        3. Sends initial prompt via query()
        4. Collects and returns initial response

        Args:
            prompt: Initial user prompt to start conversation

        Returns:
            {
                "status": "ready" | "complete",
                "messages": [{"type": "text" | "tool", "content": str, ...}]
            }
        """
        self.client = ClaudeSDKClient(options=self.options)

        # IMPORTANT: Must use connect(None) to keep stdin open for control protocol
        # Passing a string prompt directly causes "ProcessTransport not ready" error
        await self.client.connect(None)

        # Now send the initial prompt via query()
        await self.client.query(prompt)

        self.connected = True
        self._update_activity()

        # Collect initial response
        return await self._collect_response()

    async def query(self, message: str) -> Dict:
        """
        Send user message and collect Claude's response.

        Args:
            message: User's text input

        Returns:
            {
                "status": "ready" | "complete",
                "messages": [...]
            }

        Raises:
            RuntimeError: If not connected (call connect() first)
        """
        if not self.client or not self.connected:
            raise RuntimeError("Not connected. Call connect() first.")

        self._update_activity()
        await self.client.query(message)
        return await self._collect_response()

    async def _collect_response(self) -> Dict:
        """
        Collect all messages from Claude until ready for next user input.

        This method streams messages from the Claude SDK and batches them
        until the stream is exhausted (indicating Claude is waiting for input).

        Messages are categorized into two types:
        - user_messages: Clean, final messages for HITL lock form (TextBlock only)
        - context_messages: Rich execution context for admin panel (thinking, tool results, system)

        Message Types Handled:
        - TextBlock: Claude's text response (user-facing)
        - ThinkingBlock: Claude's internal reasoning (context)
        - ToolUseBlock: Tool execution request (context)
        - ToolResultBlock: Tool execution result (context)
        - SystemMessage: System events/metadata (context)
        - ResultMessage: Task completed

        Returns:
            {
                "status": "ready" | "complete",
                "user_messages": [{"type": "text", "content": "..."}],
                "context_messages": [
                    {"type": "thinking", "content": "..."},
                    {"type": "tool_use", "name": "...", "input": {...}},
                    {"type": "tool_result", "content": "...", "is_error": bool},
                    {"type": "system", "subtype": "...", "data": {...}}
                ]
            }
        """
        user_messages = []
        context_messages = []

        async for message in self.client.receive_response():
            # Check if task is complete
            if isinstance(message, ResultMessage):
                return {
                    "status": "complete",
                    "user_messages": user_messages,
                    "context_messages": context_messages
                }

            # Process system messages
            if isinstance(message, SystemMessage):
                context_messages.append({
                    "type": "system",
                    "subtype": message.subtype,
                    "data": message.data
                })

            # Process assistant messages
            if isinstance(message, AssistantMessage):
                for block in message.content:
                    if isinstance(block, TextBlock):
                        # User-facing text goes to both (for HITL lock display)
                        user_messages.append({
                            "type": "text",
                            "content": block.text
                        })
                    elif isinstance(block, ThinkingBlock):
                        # Extended thinking/reasoning output (context only)
                        context_messages.append({
                            "type": "thinking",
                            "content": block.thinking,
                            "signature": block.signature
                        })
                    elif isinstance(block, ToolUseBlock):
                        # Tool execution request (context only)
                        context_messages.append({
                            "type": "tool_use",
                            "name": block.name,
                            "id": block.id,
                            "input": block.input
                        })
                    elif isinstance(block, ToolResultBlock):
                        # Tool execution result (context only)
                        context_messages.append({
                            "type": "tool_result",
                            "tool_use_id": block.tool_use_id,
                            "content": block.content,
                            "is_error": block.is_error or False
                        })

        # Stream exhausted = Claude is ready for next input
        return {
            "status": "ready",
            "user_messages": user_messages,
            "context_messages": context_messages
        }

    async def check_timeout(self) -> bool:
        """
        Check if actor has exceeded idle timeout.

        Returns:
            True if timed out, False otherwise
        """
        elapsed = time.time() - self.last_activity
        return elapsed > self.timeout_seconds

    async def disconnect(self) -> Dict:
        """
        Cleanup Claude SDK subprocess.

        This should be called before killing the actor to ensure
        the subprocess is properly terminated.

        Returns:
            {"status": "disconnected"}
        """
        if self.client:
            try:
                await self.client.disconnect()
            except Exception as e:
                print(f"Disconnect error: {e}")
            finally:
                self.client = None

        self.connected = False
        return {"status": "disconnected"}

    def _update_activity(self):
        """Update last activity timestamp."""
        self.last_activity = time.time()


# Helper functions for actor management

def create_actor(execution_id: str, cwd: Optional[str] = None) -> ray.actor.ActorHandle:
    """
    Create a new ClaudeSessionActor with unique name.

    The actor is created with:
    - Named: "claude-session-{execution_id}" for retrieval
    - Detached lifetime: Survives driver crashes
    - No auto-restart: Subprocess can't be recovered
    - Resource allocation: 1 CPU, 512MB memory

    Args:
        execution_id: Unique identifier for this conversation
        cwd: Working directory for Claude SDK (default: current dir)

    Returns:
        Ray actor handle
    """
    actor_name = f"claude-session-{execution_id}"

    return ClaudeSessionActor.options(
        name=actor_name,
        lifetime="detached",       # Survives driver crashes
        max_restarts=0,             # Don't auto-restart (subprocess can't recover)
        num_cpus=1,                 # 1 CPU for actor + subprocess
        memory=1024 * 1024 * 1024   # 1GB (recommended by Claude SDK docs)
    ).remote(cwd=cwd)


def get_actor(execution_id: str) -> Optional[ray.actor.ActorHandle]:
    """
    Retrieve existing actor by execution ID.

    This is useful for:
    - Resuming conversation after HITL pause
    - Checking if actor still exists
    - Recovering actor handle after worker restart

    Args:
        execution_id: Unique identifier for conversation

    Returns:
        Actor handle or None if not found
    """
    actor_name = f"claude-session-{execution_id}"
    try:
        return ray.get_actor(actor_name)
    except ValueError:
        # Actor doesn't exist
        return None


async def cleanup_actor(execution_id: str):
    """
    Disconnect and kill actor.

    This should be called:
    - When conversation ends normally
    - After timeout
    - On error cleanup

    The function is idempotent - safe to call multiple times.

    Args:
        execution_id: Unique identifier for conversation
    """
    actor = get_actor(execution_id)
    if actor:
        try:
            # Disconnect Claude SDK subprocess
            await actor.disconnect.remote()
        except Exception as e:
            print(f"Disconnect error for {execution_id}: {e}")

        try:
            # Kill the actor
            ray.kill(actor)
        except Exception as e:
            print(f"Kill error for {execution_id}: {e}")
