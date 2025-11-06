"""
Kodosumi service wrapper for Claude Agent SDK with HITL functionality.

This module handles Kodosumi integration only:
1. Input forms and validation
2. Launch async executions
3. HITL (lock/lease) orchestration
4. Actor lifecycle management

All Claude SDK logic is in agent.py (ClaudeSessionActor).
"""
import os
import uuid
import ray
import fastapi
from kodosumi.core import Launch, ServeAPI, InputsError, Tracer
from kodosumi.core import forms as F
from kodosumi import dtypes
from ray import serve
from datetime import datetime
from .agent import create_actor, get_actor, cleanup_actor, get_container_image_config
from .config import load_kodosumi_config, get_file_exclusions
from .files import scan_generated_files, upload_files_to_kodosumi
from .results import build_final_result, build_conversation_summary

# Configuration
CONVERSATION_TIMEOUT_SECONDS = 600  # 10 minutes
MAX_MESSAGE_ITERATIONS = 50  # Safety limit to prevent infinite loops

# Create ServeAPI instance
app = ServeAPI()


# Helper function for dependency suggestions
async def send_dependency_suggestion(
    tracer: Tracer,
    task: str,
    missing_packages: list[dict],
    current_approach: str,
    ask_user: bool = True
) -> dict | None:
    """
    Send structured dependency improvement suggestion to user via Kodosumi.

    This function helps agents communicate clearly when they encounter missing
    dependencies in the immutable container environment. It explains what's
    missing, why it's needed, and how to add it for future builds.

    Args:
        tracer: Kodosumi tracer for sending messages
        task: Brief description of what you're trying to accomplish
        missing_packages: List of dicts with keys:
            - name (str): Package name
            - type (str): Package type ("python", "nodejs", or "system")
            - purpose (str): Why this package is needed
        current_approach: What you'll do instead without these packages
        ask_user: If True, ask user if they want to proceed with workaround

    Returns:
        User response dict if ask_user=True, else None

    Example:
        response = await send_dependency_suggestion(
            tracer=tracer,
            task="Generate Word document report",
            missing_packages=[
                {
                    "name": "docx",
                    "type": "nodejs",
                    "purpose": "Generate .docx files with formatting"
                }
            ],
            current_approach="Generate Markdown report instead",
            ask_user=True
        )
        if response and response.get("proceed") == "no":
            await tracer.markdown("Please add dependencies and rebuild.")
            return
    """
    # Build package list
    pkg_list = "\n".join([
        f"- **{pkg['name']}** ({pkg['type']}): {pkg['purpose']}"
        for pkg in missing_packages
    ])

    # Create dependency addition instructions
    instructions = []
    for pkg in missing_packages:
        if pkg['type'] == 'python':
            instructions.append(f"   - Add `{pkg['name']}` to `dependencies/requirements.txt`")
        elif pkg['type'] == 'nodejs':
            instructions.append(f"   - Add `\"{pkg['name']}\": \"^X.Y.Z\"` to `dependencies/package.json`")
        elif pkg['type'] == 'system':
            instructions.append(f"   - Add `{pkg['name']}` to `dependencies/system-packages.txt`")

    instruction_text = "\n".join(instructions)

    message = f"""
## ⚠️ Dependency Limitation

**Task**: {task}

**Missing Packages**:
{pkg_list}

**To Add These Packages**:
1. Edit your config repository's `dependencies/` directory:
{instruction_text}
2. Commit and push changes
3. Run `/cc-deploy` to rebuild container
4. Next execution will have these capabilities

**Current Approach**: {current_approach}

---
*This is an automated suggestion to help improve future capabilities.*
    """

    await tracer.markdown(message.strip())

    if ask_user:
        # Ask if user wants to proceed with workaround
        response = await tracer.lease(
            "dependency-workaround-approval",
            F.Model(
                F.Markdown(f"### Proceed with {current_approach}?"),
                F.Radio(
                    label="Your choice",
                    name="proceed",
                    options=[
                        {"label": "Yes, use workaround", "value": "yes"},
                        {"label": "No, I'll add dependencies first", "value": "no"}
                    ]
                ),
                F.Submit("Continue")
            )
        )
        return response
    return None


# Simple input form for user prompts
prompt_form = F.Model(
    F.Markdown("""
    # Claude + Kodosumi HITL Template

    This template demonstrates integrating **Claude Agent SDK** with **Kodosumi's Human-in-the-Loop (HITL)** functionality.

    Enter a prompt below to start a conversation with Claude. The conversation will pause when Claude needs your input,
    and you can respond through Kodosumi's HITL interface.

    **Conversation ends when:**
    - Claude determines the task is complete
    - 10-minute timeout is reached
    - User types 'done' or 'exit'
    """),
    F.InputArea(
        label="Your Prompt",
        name="prompt",
        placeholder="e.g., 'Help me brainstorm ideas for a blog post about AI' or 'Analyze this data...'",
        required=True,
        rows=5
    ),
    F.Submit("Start Conversation"),
    F.Cancel("Cancel")
)


@app.lock("claude-input")
async def claude_conversation_lock(data: dict):
    """
    Lock handler for Claude conversation HITL.
    Shows Claude's messages and response form to user.

    Args:
        data: Context data including:
            - messages: List of message dicts from Claude
            - status: "ready" or "complete"
            - iteration: Current iteration count

    Returns:
        Form model with Claude's messages and user input field
    """
    # Extract data
    messages = data.get("messages", [])
    status = data.get("status", "ready")
    iteration = data.get("iteration", 0)

    # Build markdown content with Claude's messages
    content = "## Claude's Response\n\n"

    for msg in messages:
        if msg["type"] == "text":
            content += f"{msg['content']}\n\n"
        elif msg["type"] == "tool":
            content += f"🔧 *{msg['content']}*\n\n"

    # Add status indicator if task is complete
    if status == "complete":
        content += "*Claude has finished responding. You can continue the conversation or type 'done' to end.*\n\n"

    # Add instructions
    content += "---\n\n### Continue the conversation\n\n"
    content += "Type your response to continue, or type **'done'** to end the conversation.\n"

    return F.Model(
        F.Markdown(content),
        F.InputArea(
            label="Your Response",
            name="response",
            placeholder="Type your response or 'done' to finish...",
            required=False,
            rows=3
        ),
        F.Submit("Send")
    )


@app.lease("claude-input")
async def claude_conversation_lease(inputs: dict):
    """
    Lease handler for Claude conversation HITL.
    Processes user's response from the lock form.

    Args:
        inputs: User inputs from the form (can be None for empty submissions)

    Returns:
        Dict with response text and cancellation status
    """
    # Handle None or non-dict inputs defensively
    if not isinstance(inputs, dict):
        inputs = {}

    # Return user's response
    response_text = inputs.get("response", "").strip()
    return {
        "response": response_text,
        "cancelled": False
    }


@app.enter(
    path="/",
    model=prompt_form,
    summary="Claude HITL Template",
    description="Interactive conversation with Claude Agent SDK using Kodosumi HITL",
    tags=["Claude", "AI", "HITL"],
    version="0.1.0"
)
async def enter(request: fastapi.Request, inputs: dict):
    """
    Entry point for Claude conversation with HITL support.

    Args:
        request: FastAPI request object
        inputs: User inputs from the form

    Returns:
        Launch object to start async execution
    """
    # Validate inputs
    prompt = inputs.get("prompt", "").strip()

    error = InputsError()
    if not prompt:
        error.add(prompt="Please provide a prompt to start the conversation")
    if error.has_errors():
        raise error

    # Launch async conversation execution
    # IMPORTANT: Use module path string (not function reference) so Kodosumi
    # imports the module in execution context, registering lock/lease handlers
    return Launch(request, "claude_hitl_template.query:run_conversation", inputs={
        "prompt": prompt,
        "timestamp": datetime.now().isoformat()
    })


async def run_conversation(inputs: dict, tracer: Tracer):
    """
    Orchestrate Claude conversation with HITL using Ray Actor.

    This function (Kodosumi orchestration only):
    1. Creates/retrieves ClaudeSessionActor
    2. Displays messages via tracer.markdown()
    3. Handles HITL pauses via tracer.lease()
    4. Manages actor lifecycle and cleanup
    5. Implements auto-retry on actor crashes

    Args:
        inputs: Execution inputs including initial prompt
        tracer: Kodosumi tracer for progress updates and HITL
    """
    # Load configuration for completion behavior
    config = load_kodosumi_config()

    # Generate unique execution ID
    execution_id = inputs.get("execution_id", str(uuid.uuid4()))
    prompt = inputs["prompt"]

    # Get container image configuration for visibility
    image_config = get_container_image_config()

    # Build initialization message with image info
    init_message = f"""
## Conversation Started
**Timestamp:** {inputs["timestamp"]}
**Execution ID:** {execution_id}

"""

    # Add container image info if using containers
    if image_config["use_container"]:
        # Truncate digest for readability (first 12 + last 6 chars)
        digest = image_config["digest"]
        if digest and len(digest) > 25:
            digest_display = f"{digest[:19]}...{digest[-6:]}"
        else:
            digest_display = digest or "unknown"

        init_message += f"""### Container Image Configuration
**Registry Path:** `{image_config["registry_path"]}`
**Digest:** `{digest_display}` (SHA256)

This conversation will run in a containerized Ray Actor with baked `.claude` configurations.

"""

    init_message += "Initializing Claude Agent SDK...\n"

    # Show initial status
    await tracer.markdown(init_message)

    retry_count = 0
    max_retries = 1

    try:
        while retry_count <= max_retries:
            try:
                # Get or create actor
                actor = get_actor(execution_id)
                if actor is None:
                    await tracer.markdown("Creating Ray Actor for persistent session...")
                    # Pass current working directory to actor
                    # (Ray worker's cwd may differ from orchestration process)
                    actor = create_actor(execution_id, cwd=os.getcwd())
                    is_first_connect = True
                else:
                    # Actor exists (resuming after retry)
                    is_first_connect = False

                # Connect or reconnect
                if is_first_connect:
                    await tracer.markdown("✓ Actor created\n\nConnecting to Claude...")
                    result = await actor.connect.remote(prompt)
                else:
                    # Reconnect after retry
                    await tracer.markdown("🔄 Reconnecting to Claude...")
                    result = await actor.connect.remote(f"Continuing conversation: {prompt}")

                await tracer.markdown("✓ Connected\n")

                # Get and display agent metadata
                if is_first_connect:
                    await tracer.markdown("Loading agent configuration...")
                    metadata = await actor.get_metadata.remote()
                    formatted_metadata = _format_metadata(metadata)
                    await tracer.markdown(formatted_metadata)

                # Check for autonomous completion on initial connection (ResultMessage received)
                if result["status"] == "complete" and config.get("completion_mode") == "auto-complete":
                    completion_type = result.get("completion_type", "unknown")
                    await tracer.markdown(f"\n✓ **Task complete** (via {completion_type}) - Finalizing job...")
                    final_result = await _finalize_job(
                        tracer=tracer,
                        messages=result.get("user_messages", []),
                        iteration=1,
                        config=config
                    )
                    return dtypes.Markdown(body=final_result)

                # Main conversation loop
                iteration = 0
                while iteration < MAX_MESSAGE_ITERATIONS:
                    iteration += 1

                    # Check timeout
                    is_timeout = await actor.check_timeout.remote()
                    if is_timeout:
                        summary = _build_conversation_summary(iteration, "⏱️ Session timed out (11 minutes idle)")
                        return dtypes.Markdown(body=summary)

                    # Check for autonomous completion after each query (ResultMessage received)
                    if result["status"] == "complete" and config.get("completion_mode") == "auto-complete":
                        completion_type = result.get("completion_type", "unknown")
                        await tracer.markdown(f"\n✓ **Task complete** (via {completion_type}) - Finalizing job...")
                        final_result = await _finalize_job(
                            tracer=tracer,
                            messages=result.get("user_messages", []),
                            iteration=iteration,
                            config=config
                        )
                        return dtypes.Markdown(body=final_result)

                    # Note: result["status"] == "complete" just means this turn is done,
                    # NOT that the conversation should end. Continue to HITL loop to let
                    # user decide whether to respond or end conversation.

                    # Display context messages in admin panel (thinking, tool results, etc.)
                    await _display_context_messages(tracer, result.get("context_messages", []))

                    # HITL pause - Pass only user-facing messages to lock handler
                    user_input = await tracer.lock(
                        "claude-input",
                        {
                            "iteration": iteration,
                            "messages": result.get("user_messages", []),
                            "status": result["status"]
                        }
                    )

                    # Check for cancellation
                    if not user_input or user_input.get("cancelled"):
                        summary = _build_conversation_summary(iteration, "⏹️ Conversation ended by user")
                        return dtypes.Markdown(body=summary)

                    response_text = user_input.get("response", "").strip()

                    # Check for termination keywords
                    if response_text.lower() in ["done", "exit", "quit", "stop"]:
                        summary = _build_conversation_summary(iteration, "✓ Conversation completed successfully")
                        return dtypes.Markdown(body=summary)

                    if not response_text:
                        summary = _build_conversation_summary(iteration, "⚠️ Empty response - conversation ended")
                        return dtypes.Markdown(body=summary)

                    # Send to Claude
                    await tracer.markdown(f"\n**You:** {response_text}\n\n*Waiting for Claude's response...*\n")
                    result = await actor.query.remote(response_text)

                # Max iterations check
                if iteration >= MAX_MESSAGE_ITERATIONS:
                    summary = _build_conversation_summary(iteration, f"⚠️ Maximum iteration limit reached ({MAX_MESSAGE_ITERATIONS})")
                    return dtypes.Markdown(body=summary)

                # Success - exit retry loop (this should be unreachable now)
                break

            except ray.exceptions.RayActorError as e:
                # Actor crashed
                retry_count += 1
                if retry_count <= max_retries:
                    await tracer.markdown(
                        f"\n⚠️ **Session crashed. Retrying ({retry_count}/{max_retries})...**\n"
                    )
                    # Kill crashed actor (new one created in next iteration)
                    try:
                        await cleanup_actor(execution_id)
                    except:
                        pass
                else:
                    summary = _build_conversation_summary(0, "❌ Session failed after retries")
                    return dtypes.Markdown(body=summary)

        # If we reach here, conversation loop exited normally
        # This should not happen with current logic but handle it gracefully
        summary = _build_conversation_summary(iteration, "✓ Conversation completed")
        return dtypes.Markdown(body=summary)

    except Exception as e:
        # Handle any errors with proper completion
        summary = _build_conversation_summary(0, f"❌ Error: {str(e)[:100]}")
        return dtypes.Markdown(body=summary)

    finally:
        # Always cleanup actor
        await cleanup_actor(execution_id)


async def _display_context_messages(tracer: Tracer, context_messages: list):
    """
    Display context messages (thinking, tool usage, results) in Kodosumi admin panel.

    These messages provide rich execution context that helps users understand
    what Claude is doing internally, separate from the clean user-facing messages
    shown in the HITL lock form.

    Args:
        tracer: Kodosumi tracer for markdown output
        context_messages: List of context message dicts
    """
    if not context_messages:
        return

    for msg in context_messages:
        msg_type = msg.get("type")

        if msg_type == "thinking":
            # Extended thinking/reasoning output
            thinking_content = msg.get("content", "")
            # Truncate very long thinking for readability
            if len(thinking_content) > 500:
                thinking_preview = thinking_content[:500] + "..."
            else:
                thinking_preview = thinking_content
            await tracer.markdown(f"🧠 **Claude is thinking:**\n\n```\n{thinking_preview}\n```\n")

        elif msg_type == "tool_use":
            # Tool execution request
            tool_name = msg.get("name", "unknown")
            tool_input = msg.get("input", {})
            await tracer.markdown(f"🔧 **Using tool: {tool_name}**\n\n```json\n{str(tool_input)[:200]}\n```\n")

        elif msg_type == "tool_result":
            # Tool execution result
            content = msg.get("content", "")
            is_error = msg.get("is_error", False)
            emoji = "❌" if is_error else "✅"
            status = "Error" if is_error else "Success"

            # Truncate long results
            content_str = str(content)
            if len(content_str) > 300:
                content_preview = content_str[:300] + "..."
            else:
                content_preview = content_str

            await tracer.markdown(f"{emoji} **Tool result ({status}):**\n\n```\n{content_preview}\n```\n")

        elif msg_type == "system":
            # System messages
            subtype = msg.get("subtype", "unknown")
            data = msg.get("data", {})
            await tracer.markdown(f"ℹ️ **System ({subtype}):** {str(data)[:200]}\n")


def _format_metadata(metadata: dict) -> str:
    """
    Format agent metadata as readable markdown.

    Args:
        metadata: Metadata dict from actor.get_metadata()

    Returns:
        Formatted markdown string
    """
    lines = []
    lines.append("## Agent Configuration\n")

    # Container Configuration
    container = metadata.get("container", {})
    if container.get("use_container"):
        lines.append("### Container Image")
        lines.append(f"**Registry Path:** `{container.get('registry_path', 'unknown')}`")

        # Truncate digest for readability
        digest = container.get('digest', '')
        if digest and len(digest) > 25:
            digest_display = f"{digest[:19]}...{digest[-6:]}"
        else:
            digest_display = digest or "unknown"
        lines.append(f"**Digest:** `{digest_display}` (SHA256)\n")

    # Resource Allocation
    resources = metadata.get("resources", {})
    lines.append("### Resource Allocation")
    lines.append(f"**CPUs:** {resources.get('cpus', 'unknown')}")
    lines.append(f"**Memory:** {resources.get('memory_gb', 'unknown')} GB\n")

    # Loaded Plugins and Capabilities
    plugins = metadata.get("plugins", [])
    if plugins:
        lines.append("### Loaded Plugins\n")
        for plugin in plugins:
            plugin_name = plugin.get("name", "unknown")
            marketplace = plugin.get("marketplace", "unknown")
            lines.append(f"**{plugin_name}** (`{marketplace}`)")

            # List capabilities
            capabilities = []
            if plugin.get("commands"):
                capabilities.append(f"Commands: {', '.join(plugin['commands'])}")
            if plugin.get("agents"):
                capabilities.append(f"Agents: {', '.join(plugin['agents'])}")
            if plugin.get("skills"):
                capabilities.append(f"Skills: {', '.join(plugin['skills'])}")
            if plugin.get("mcp_servers"):
                capabilities.append(f"MCP Servers: {', '.join(plugin['mcp_servers'])}")

            if capabilities:
                for cap in capabilities:
                    lines.append(f"  - {cap}")
            else:
                lines.append("  - No capabilities discovered")
            lines.append("")
    else:
        lines.append("### Loaded Plugins\n")
        lines.append("*No plugins loaded*\n")

    # Tool Permissions
    settings = metadata.get("settings", {})
    permissions = settings.get("permissions", [])
    if permissions:
        lines.append("### Tool Permissions")
        # Group permissions by category for readability
        lines.append(f"**Allowed Tools:** {len(permissions)} configured")
        lines.append("<details><summary>View all permissions</summary>\n")
        for perm in permissions:
            lines.append(f"- `{perm}`")
        lines.append("\n</details>\n")

    # Settings Resolution
    sources = settings.get("sources", [])
    if sources:
        lines.append("### Settings Resolution")
        lines.append(f"**Active Tiers:** {', '.join(sources)}\n")

    lines.append("---\n")

    return "\n".join(lines)


async def _finalize_job(
    tracer: Tracer,
    messages: list,
    iteration: int,
    config: dict
) -> str:
    """
    Finalize job completion: scan files, upload, and build final result.

    Args:
        tracer: Kodosumi tracer for progress updates
        messages: Claude's messages from this turn
        iteration: Current iteration count
        config: Configuration dict with upload_files setting

    Returns:
        Formatted markdown result
    """
    uploaded_files = []

    # Handle file uploads if enabled
    if config.get("upload_files", True):
        exclusions = get_file_exclusions()
        file_paths = await scan_generated_files(exclusions)

        if file_paths:
            uploaded_files = await upload_files_to_kodosumi(tracer, file_paths)

    # Build final result
    return build_final_result(
        messages=messages,
        files=uploaded_files,
        iteration=iteration,
        reason="Task completed"
    )


def _build_conversation_summary(iterations: int, reason: str) -> str:
    """
    Build a markdown summary of the conversation.

    Args:
        iterations: Number of conversation iterations
        reason: Reason for conversation ending

    Returns:
        Formatted markdown string
    """
    return f"""---

## Conversation Complete

**Status:** {reason}
**Total Interactions:** {iterations}
**Ended at:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

---

Thank you for using Claude HITL Template!
"""


# Ray Serve deployment wrapper for Kodosumi ServeAPI
@serve.deployment
@serve.ingress(app)
class ClaudeHitlTemplate:
    """
    Ray Serve deployment class wrapping the Kodosumi ServeAPI.
    This pattern is required for Kodosumi applications deployed via Ray Serve.
    """
    pass


fast_app = ClaudeHitlTemplate.bind()
