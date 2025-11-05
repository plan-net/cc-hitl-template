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
import json
import logging
from pathlib import Path
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

# Set up logging
logger = logging.getLogger(__name__)


def get_container_image_config() -> dict:
    """
    Get container image configuration from environment.

    Returns:
        {
            "uri": "ghcr.io/user/image@sha256:...",  # Full URI with digest
            "registry_path": "ghcr.io/user/image",     # Without digest
            "digest": "sha256:...",                     # Just the digest
            "use_container": bool                       # Whether to use containers
        }
    """
    image_uri = os.getenv("CONTAINER_IMAGE_URI", "")

    # Container mode is enabled if image URI is configured
    use_container = bool(image_uri)

    # Parse digest from URI if present (format: image@sha256:...)
    registry_path = ""
    digest = ""
    if image_uri and "@" in image_uri:
        registry_path, digest = image_uri.split("@", 1)
    elif image_uri:
        registry_path = image_uri

    return {
        "uri": image_uri,
        "registry_path": registry_path,
        "digest": digest,
        "use_container": use_container
    }


def load_marketplace_settings() -> Dict:
    """
    Read and merge marketplace settings from master and project configs.

    Master config provides baseline plugins (user-level).
    Project config adds/overrides plugins (project-level).

    Returns:
        Dict with 'marketplaces' and 'enabled_plugins' keys
    """
    marketplaces = {}
    enabled_plugins = {}

    # Read master config (user-level settings)
    master_settings_path = Path("/app/template_user/.claude/settings.json")
    if master_settings_path.exists():
        try:
            data = json.loads(master_settings_path.read_text())
            marketplaces.update(data.get("extraKnownMarketplaces", {}))
            enabled_plugins.update(data.get("enabledPlugins", {}))
            logger.info(f"Loaded master settings: {len(enabled_plugins)} plugins declared")
        except Exception as e:
            logger.error(f"Failed to read master settings from {master_settings_path}: {e}")
    else:
        logger.warning(f"Master settings not found at {master_settings_path}")

    # Read project config (project-level settings, overrides master)
    project_settings_path = Path("/app/.claude/settings.json")
    if project_settings_path.exists():
        try:
            data = json.loads(project_settings_path.read_text())
            marketplaces.update(data.get("extraKnownMarketplaces", {}))
            enabled_plugins.update(data.get("enabledPlugins", {}))
            logger.info(f"Loaded project settings: {len(enabled_plugins)} total plugins after merge")
        except Exception as e:
            logger.error(f"Failed to read project settings from {project_settings_path}: {e}")
    else:
        logger.info(f"Project settings not found at {project_settings_path} (optional)")

    return {
        "marketplaces": marketplaces,
        "enabled_plugins": enabled_plugins
    }


def resolve_plugin_paths(settings: Dict) -> List[Dict[str, str]]:
    """
    Convert enabledPlugins to Agent SDK plugin specs.

    Parses "plugin-name@marketplace-name" format and resolves to filesystem paths.
    Plugins must exist at /app/plugins/{marketplace}/plugins/{plugin}/

    Args:
        settings: Dict from load_marketplace_settings()

    Returns:
        List of plugin specs for ClaudeAgentOptions
    """
    plugin_specs = []

    for plugin_key, enabled in settings["enabled_plugins"].items():
        if not enabled:
            logger.debug(f"Skipping disabled plugin: {plugin_key}")
            continue

        # Parse "plugin-name@marketplace-name" format
        if "@" not in plugin_key:
            logger.warning(f"Invalid plugin key format (missing @): {plugin_key}")
            continue

        plugin_name, marketplace_name = plugin_key.split("@", 1)

        # Plugins are baked into /app/plugins/{marketplace}/plugins/{plugin}
        # This path structure matches how build.sh copies them
        plugin_path = f"/app/plugins/{marketplace_name}/plugins/{plugin_name}"

        if Path(plugin_path).exists():
            plugin_specs.append({
                "type": "local",
                "path": plugin_path
            })
            logger.info(f"✓ Found plugin: {plugin_name}@{marketplace_name}")
        else:
            logger.warning(f"✗ Plugin path not found: {plugin_path} (declared but not baked into image)")

    return plugin_specs


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
        # Check if running in container
        # In container, HOME is set to /app/template_user by Dockerfile ENV
        is_containerized = os.getenv("HOME") == "/app/template_user"

        # Store resource allocation (matches create_actor() settings)
        self.num_cpus = 1
        self.memory_bytes = 1024 * 1024 * 1024  # 1GB

        # Load plugins from settings.json
        plugin_specs = []
        self.settings = None  # Store for metadata
        if is_containerized:
            # In container: Load plugins from marketplace settings
            logger.info("=" * 70)
            logger.info("PLUGIN LOADING")
            logger.info("=" * 70)

            self.settings = load_marketplace_settings()
            plugin_specs = resolve_plugin_paths(self.settings)

            if plugin_specs:
                logger.info(f"Successfully loaded {len(plugin_specs)} plugins:")
                for spec in plugin_specs:
                    logger.info(f"  → {spec['path']}")
            else:
                logger.warning("No plugins loaded - agent will run without plugins")
                logger.warning("Check that settings.json has enabledPlugins configured")

            logger.info("=" * 70)

            # In container: Enable setting_sources to merge .claude folders
            # - "user" → /app/template_user/.claude/ (baked into image)
            # - "project" → .claude/ in deployed code directory
            # - "local" → .claude/settings.local.json (if exists)
            setting_sources = ["user", "project", "local"]
        else:
            # Native execution: Don't load filesystem settings to avoid mixing with personal ~/.claude/
            setting_sources = None

        self.options = ClaudeAgentOptions(
            permission_mode=permission_mode,
            cwd=cwd or os.getcwd(),
            setting_sources=setting_sources,
            plugins=plugin_specs  # Add loaded plugins
        )
        self.plugin_specs = plugin_specs  # Store for metadata
        self.setting_sources = setting_sources  # Store for metadata
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

    async def get_metadata(self) -> Dict:
        """
        Get comprehensive metadata about agent configuration.

        Returns metadata including:
        - Container configuration (image, digest, registry)
        - Resource allocation (CPUs, memory)
        - Loaded plugins with enumerated capabilities
        - Tool permissions
        - Settings resolution tiers

        Returns:
            Dict with metadata organized by category
        """
        metadata = {
            "container": get_container_image_config(),
            "resources": {
                "cpus": self.num_cpus,
                "memory_bytes": self.memory_bytes,
                "memory_gb": round(self.memory_bytes / (1024**3), 2)
            },
            "settings": {
                "sources": self.setting_sources or [],
                "permissions": []
            },
            "plugins": []
        }

        # Scan plugins for capabilities
        for plugin_spec in self.plugin_specs:
            plugin_path = Path(plugin_spec["path"])
            plugin_name = plugin_path.name
            marketplace_name = plugin_path.parent.parent.parent.name

            plugin_info = {
                "name": plugin_name,
                "marketplace": marketplace_name,
                "path": str(plugin_path),
                "commands": [],
                "agents": [],
                "skills": [],
                "mcp_servers": []
            }

            # Scan for commands (*.md in commands/)
            commands_dir = plugin_path / "commands"
            if commands_dir.exists():
                for cmd_file in commands_dir.glob("*.md"):
                    plugin_info["commands"].append(cmd_file.stem)

            # Scan for agents (*.md in agents/)
            agents_dir = plugin_path / "agents"
            if agents_dir.exists():
                for agent_file in agents_dir.glob("*.md"):
                    plugin_info["agents"].append(agent_file.stem)

            # Scan for skills (subdirectories in skills/)
            skills_dir = plugin_path / "skills"
            if skills_dir.exists():
                for skill_dir in skills_dir.iterdir():
                    if skill_dir.is_dir() and not skill_dir.name.startswith("."):
                        plugin_info["skills"].append(skill_dir.name)

            # Check for MCP servers in plugin settings.json
            plugin_settings_path = plugin_path / "settings.json"
            if plugin_settings_path.exists():
                try:
                    plugin_settings = json.loads(plugin_settings_path.read_text())
                    mcp_servers = plugin_settings.get("mcp_servers", {})
                    plugin_info["mcp_servers"] = list(mcp_servers.keys())
                except Exception as e:
                    logger.warning(f"Failed to read plugin settings from {plugin_settings_path}: {e}")

            metadata["plugins"].append(plugin_info)

        # Get permissions from settings
        if self.settings:
            # Read permissions from both master and project configs
            permissions = set()

            # Master permissions
            master_settings_path = Path("/app/template_user/.claude/settings.json")
            if master_settings_path.exists():
                try:
                    data = json.loads(master_settings_path.read_text())
                    perms = data.get("permissions", {}).get("allow", [])
                    permissions.update(perms)
                except Exception as e:
                    logger.warning(f"Failed to read master permissions: {e}")

            # Project permissions (overrides/adds to master)
            project_settings_path = Path("/app/.claude/settings.json")
            if project_settings_path.exists():
                try:
                    data = json.loads(project_settings_path.read_text())
                    perms = data.get("permissions", {}).get("allow", [])
                    permissions.update(perms)
                except Exception as e:
                    logger.warning(f"Failed to read project permissions: {e}")

            metadata["settings"]["permissions"] = sorted(list(permissions))

        return metadata

    def _update_activity(self):
        """Update last activity timestamp."""
        self.last_activity = time.time()


# Helper functions for actor management

def create_actor(execution_id: str, cwd: Optional[str] = None, use_container: Optional[bool] = None) -> ray.actor.ActorHandle:
    """
    Create a new ClaudeSessionActor with unique name.

    The actor is created with:
    - Named: "claude-session-{execution_id}" for retrieval
    - Detached lifetime: Survives driver crashes
    - No auto-restart: Subprocess can't be recovered
    - Resource allocation: 1 CPU, 1GB memory
    - Optional: Container runtime for .claude/ folder isolation

    Args:
        execution_id: Unique identifier for this conversation
        cwd: Working directory for Claude SDK (default: current dir)
        use_container: If True, run actor in container with isolated .claude folders.
                      If None (default), auto-detects from CONTAINER_IMAGE_URI env var.
                      Requires image URI with digest in environment configuration.

    Returns:
        Ray actor handle
    """
    from ray.runtime_env import RuntimeEnv

    actor_name = f"claude-session-{execution_id}"

    # Get project root
    project_root = cwd or os.getcwd()

    # Get container image configuration from environment
    image_config = get_container_image_config()

    # Auto-detect container usage from environment if not explicitly set
    if use_container is None:
        use_container = image_config["use_container"]

    # Build runtime environment
    if use_container:
        # Container isolation for .claude/ folders:
        # - Master config .claude/ is baked into the image (template/user-level config)
        # - Project config .claude/ is baked into the image (project-specific config)
        # Ray's image_uri can only be used with env_vars (no 'container' field or volume mounts)
        #
        # Image URI must include digest for immutable reference:
        # Format: ghcr.io/<username>/claude-hitl-worker@sha256:<digest>
        runtime_env = RuntimeEnv(
            image_uri=image_config["uri"],  # Full URI with digest from CONTAINER_IMAGE_URI env var
            env_vars={
                "ANTHROPIC_API_KEY": os.getenv("ANTHROPIC_API_KEY", ""),
                "CONTAINER_IMAGE_URI": image_config["uri"],      # Pass to actor for logging
                "CONTAINER_IMAGE_DIGEST": image_config["digest"], # Pass digest for validation
                # HOME is set to /app/template_user in Dockerfile
                # This makes "user" settings load from master config .claude/
            }
        )
        # Ray will deploy code to container, actor runs in that context
        actor_cwd = None  # Let Ray handle cwd
    else:
        # Native execution (no container)
        runtime_env = None
        actor_cwd = project_root

    return ClaudeSessionActor.options(
        name=actor_name,
        runtime_env=runtime_env,
        lifetime="detached",       # Survives driver crashes
        max_restarts=0,             # Don't auto-restart (subprocess can't recover)
        num_cpus=1,                 # 1 CPU for actor + subprocess
        memory=1024 * 1024 * 1024   # 1GB (recommended by Claude SDK docs)
    ).remote(cwd=actor_cwd)


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
