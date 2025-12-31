"""
Advanced Web Research Agent - Kodosumi HITL Service.

This module handles Kodosumi integration for the Advanced Web Research agent:
1. Research configuration form (question, depth, presentation options)
2. Launch async executions
3. HITL (lock/lease) orchestration for research workflow
4. Actor lifecycle management

All Claude SDK logic is in agent.py (ClaudeSessionActor).
The agent follows instructions from .claude/skills/advanced-web-research/SKILL.md
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

# API Keys from environment variables
EXA_API_KEY = os.getenv("EXA_API_KEY", "")
GAMMA_API_KEY = os.getenv("GAMMA_API_KEY", "")
DO_SPACES_ACCESS_KEY = os.getenv("DO_SPACES_ACCESS_KEY", "")
DO_SPACES_SECRET_KEY = os.getenv("DO_SPACES_SECRET_KEY", "")

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


# Research configuration form
research_form = F.Model(
    F.Markdown("""
# Advanced Web Research Agent

Conduct comprehensive web research using **AI-powered analysis (Exa.ai)** and generate professional **PPTX presentations (Gamma AI)**.

**Use this agent for:**
- Strategic research requiring comprehensive multi-source analysis
- Executive briefings needing presentation-ready deliverables
- Competitive intelligence gathering with synthesis
- Market trend research with actionable insights

**Estimated Cost:** $0.20 - $0.50 per research (Exa.ai API)
    """),
    F.InputArea(
        label="Research Question",
        name="research_question",
        placeholder="Example: What are the key factors driving electric vehicle adoption in Europe?",
        required=True,
        rows=3
    ),
    F.Select(
        name="depth_preference",
        label="Research Depth",
        option=[
            F.InputOption(name="quick", label="Quick - Fast overview (~2-3 min, $0.20-$0.30)"),
            F.InputOption(name="balanced", label="Balanced - Standard depth (Recommended) (~3-5 min, $0.30-$0.40)"),
            F.InputOption(name="comprehensive", label="Comprehensive - Deep-dive (~5-8 min, $0.40-$0.50)")
        ],
        value="balanced"
    ),
    F.Checkbox(
        name="generate_presentation",
        label="Generate Presentation (creates PPTX, ~10 Gamma AI credits)",
        value=True
    ),
    F.InputArea(
        label="Additional Context (Optional)",
        name="additional_context",
        placeholder="Example: Focus on enterprise solutions, emphasize cost comparisons, include regulatory considerations...",
        required=False,
        rows=2
    ),
    F.Submit("Start Research"),
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

    # Build clean content with Claude's messages (no technical headers)
    content = ""

    for msg in messages:
        if msg["type"] == "text":
            text = msg['content']
            # Remove HITL markers from display
            text = text.replace("[WAITING_FOR_INPUT]", "").replace("[TASK_COMPLETE]", "")
            content += f"{text.strip()}\n\n"

    # Simple prompt for user input
    if status == "complete":
        content += "\n---\n*You can ask follow-up questions or type 'done' to finish.*\n"

    return F.Model(
        F.Markdown(content),
        F.InputArea(
            label="Your Response",
            name="response",
            placeholder="Type your answer or 'done' to finish...",
            required=False,
            rows=3
        ),
        F.Submit("Continue")
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
    path="/research",
    model=research_form,
    summary="Advanced Web Research",
    description="Comprehensive web research with AI-powered analysis and PPTX presentation generation",
    tags=["Research", "Exa.ai", "Gamma", "HITL"],
    version="2.2.0"
)
async def enter(request: fastapi.Request, inputs: dict):
    """
    Entry point for Advanced Web Research agent with HITL support.

    Args:
        request: FastAPI request object
        inputs: User inputs from the research form

    Returns:
        Launch object to start async execution
    """
    # Validate inputs
    research_question = inputs.get("research_question", "").strip()

    error = InputsError()
    if not research_question:
        error.add(research_question="Please provide a research question")
    if len(research_question) > 500:
        error.add(research_question="Research question must be 500 characters or less")
    if error.has_errors():
        raise error

    # Extract form values with defaults
    depth_preference = inputs.get("depth_preference", "balanced")
    generate_presentation = inputs.get("generate_presentation", True)
    additional_context = inputs.get("additional_context", "").strip()

    # Build the initial prompt with DIRECT instructions (don't read SKILL.md)
    initial_prompt = f"""You are an Advanced Web Research Agent. Execute the following workflow silently and show only clean results.

**RESEARCH REQUEST:**
- Question: {research_question}
- Depth: {depth_preference}
- Generate Presentation: {generate_presentation}
- Context: {additional_context if additional_context else "None"}

**STEP 1: ASK ONE QUESTION**
Ask briefly: "Any specific focus areas or aspects you'd like me to prioritize in this research?"
Then output [WAITING_FOR_INPUT] and wait.

**STEP 2: EXECUTE EXA RESEARCH (after user responds)**
Run this curl command silently using Bash tool:

```bash
RESEARCH_ID=$(curl -s -X POST "https://api.exa.ai/research/v1" \\
  -H "Authorization: Bearer {EXA_API_KEY}" \\
  -H "Content-Type: application/json" \\
  -d '{{"instructions": "{research_question}"}}' | jq -r '.researchId')
echo $RESEARCH_ID
```

Then poll every 10 seconds until complete:
```bash
curl -s "https://api.exa.ai/research/v1/$RESEARCH_ID" \\
  -H "Authorization: Bearer {EXA_API_KEY}"
```

**STEP 3: SHOW FULL RESEARCH REPORT**
Display the COMPLETE research report from the API response (output.content field).
DO NOT summarize or shorten it. Show the ENTIRE report with all sections and citations.

**STEP 4: GENERATE PRESENTATION (if {generate_presentation})**
If presentation is enabled, follow these steps silently:

4a. Create presentation via Gamma API:
```bash
GAMMA_RESPONSE=$(curl -s -X POST "https://public-api.gamma.app/v1.0/generations" \
  -H "X-API-KEY: {GAMMA_API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{{"inputText": "YOUR_RESEARCH_CONTENT_HERE", "format": "presentation", "numCards": 12, "exportAs": "pptx"}}')
GENERATION_ID=$(echo $GAMMA_RESPONSE | jq -r '.generationId')
```

4b. Poll until complete (every 10 seconds):
```bash
RESULT=$(curl -s "https://public-api.gamma.app/v1.0/generations/$GENERATION_ID" \
  -H "X-API-KEY: {GAMMA_API_KEY}")
```

4c. Download PPTX from exportUrl in response:
```bash
EXPORT_URL=$(echo $RESULT | jq -r '.exportUrl')
curl -L -o /tmp/presentation.pptx "$EXPORT_URL"
```

4d. Upload to Digital Ocean Spaces for public download:
```bash
python3 << 'EOF'
import boto3
from botocore.config import Config
from datetime import datetime

# Generate filename with timestamp
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
filename = f"research_presentation_{{timestamp}}.pptx"

s3 = boto3.client('s3',
    endpoint_url="https://fra1.digitaloceanspaces.com",
    region_name="fra1",
    aws_access_key_id="{DO_SPACES_ACCESS_KEY}",
    aws_secret_access_key="{DO_SPACES_SECRET_KEY}",
    config=Config(signature_version='s3v4'))

s3.upload_file('/tmp/presentation.pptx', 'studios-general-bucket',
    f'research-presentations/{{filename}}',
    ExtraArgs={{'ACL': 'public-read', 'ContentType': 'application/vnd.openxmlformats-officedocument.presentationml.presentation'}})

print(f"https://studios-general-bucket.fra1.digitaloceanspaces.com/research-presentations/{{filename}}")
EOF
```

The final CDN URL is directly downloadable (no login required)

**STEP 5: FINAL OUTPUT**
Show:
1. The FULL research report (all sections, all citations - NOT summarized)
2. If presentation generated, show the DO Spaces CDN download link like:
   **Download Presentation:** [research_presentation_TIMESTAMP.pptx](https://studios-general-bucket.fra1.digitaloceanspaces.com/research-presentations/research_presentation_TIMESTAMP.pptx)
   (This is a direct download link - no login required)
3. [TASK_COMPLETE]

IMPORTANT: Show the DO Spaces CDN link (studios-general-bucket.fra1.digitaloceanspaces.com), NOT the Gamma editor link (gamma.app/docs/...).

**CRITICAL RULES:**
- NO phase numbers or technical labels
- NO polling status messages
- NO generation IDs or task IDs
- NO "Generating...", "Polling...", "Status: pending"
- NO intermediate messages like "Thank you! I'll research...", "Now let me generate...", "Let me...", etc.
- NO narration of what you're doing
- Show COMPLETE research report - NEVER truncate or summarize
- Execute silently, show only final clean results
- ONLY show the DO Spaces CDN link for presentation (NOT gamma.app link)
- The DO Spaces link MUST be from an actual upload - verify the file exists before showing link

**FINAL OUTPUT FORMAT (NOTHING ELSE):**
```
[Full Research Report Here - all sections, all citations]

---

**Download Presentation:** [filename.pptx](DO_SPACES_URL)
```

DO NOT include any other text, greetings, or explanations in the final output.

Start now with Step 1."""

    # Launch async research execution
    return Launch(request, "advanced_web_research.query:run_conversation", inputs={
        "prompt": initial_prompt,
        "research_question": research_question,
        "depth_preference": depth_preference,
        "generate_presentation": generate_presentation,
        "additional_context": additional_context,
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

    # Build clean initialization message for end users
    research_question = inputs.get("research_question", "N/A")
    depth = inputs.get("depth_preference", "balanced")

    # Map depth to user-friendly description
    depth_labels = {
        "quick": "Quick (~2-3 min)",
        "balanced": "Balanced (~3-5 min)",
        "comprehensive": "Comprehensive (~5-8 min)"
    }
    depth_label = depth_labels.get(depth, depth)

    init_message = f"""
## 🔍 Starting Research

**Your Question:** {research_question}

**Research Depth:** {depth_label}

Please wait while we gather and analyze information from multiple sources...
"""

    # Show clean initial status (no technical details)
    await tracer.markdown(init_message)

    retry_count = 0
    max_retries = 1

    try:
        while retry_count <= max_retries:
            try:
                # Get or create actor (no technical messages shown to user)
                actor = get_actor(execution_id)
                if actor is None:
                    # Pass current working directory to actor
                    # (Ray worker's cwd may differ from orchestration process)
                    actor = create_actor(execution_id, cwd=os.getcwd())
                    is_first_connect = True
                else:
                    # Actor exists (resuming after retry)
                    is_first_connect = False

                # Connect or reconnect silently
                if is_first_connect:
                    result = await actor.connect.remote(prompt)
                else:
                    result = await actor.connect.remote(f"Continuing conversation: {prompt}")

                # Check for autonomous completion on initial connection (ResultMessage received)
                # But DON'T auto-complete if Claude signaled it needs input
                if result["status"] == "complete" and config.get("completion_mode") == "auto-complete":
                    if not _is_waiting_for_input(result.get("user_messages", [])):
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
                        # Include the last Claude response (the report) in final output
                        last_messages = result.get("user_messages", [])
                        summary = _build_final_report(last_messages, iteration, "✓ Research completed successfully")
                        return dtypes.Markdown(body=summary)

                    if not response_text:
                        summary = _build_conversation_summary(iteration, "⚠️ Empty response - conversation ended")
                        return dtypes.Markdown(body=summary)

                    # Send to Claude
                    await tracer.markdown(f"\n**You:** {response_text}\n\n*Waiting for Claude's response...*\n")
                    result = await actor.query.remote(response_text)

                    # Check for autonomous completion after query
                    # But DON'T auto-complete if Claude signaled it needs input
                    if result["status"] == "complete" and config.get("completion_mode") == "auto-complete":
                        if not _is_waiting_for_input(result.get("user_messages", [])):
                            completion_type = result.get("completion_type", "unknown")
                            await tracer.markdown(f"\n✓ **Task complete** (via {completion_type}) - Finalizing job...")
                            final_result = await _finalize_job(
                                tracer=tracer,
                                messages=result.get("user_messages", []),
                                iteration=iteration,
                                config=config
                            )
                            return dtypes.Markdown(body=final_result)

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


def _is_waiting_for_input(messages: list) -> bool:
    """
    Detect if Claude is waiting for human input based on explicit markers.

    Claude is instructed to end responses with:
    - [WAITING_FOR_INPUT] - needs human input
    - [TASK_COMPLETE] - task is done

    Args:
        messages: List of message dicts from Claude's response

    Returns:
        True if Claude signaled it needs input, False if task complete or no marker
    """
    if not messages:
        return False

    # Get the last text message
    last_text = ""
    for msg in reversed(messages):
        if msg.get("type") == "text":
            last_text = msg.get("content", "").strip()
            break

    if not last_text:
        return False

    # Check for explicit markers (Claude decides)
    if "[WAITING_FOR_INPUT]" in last_text:
        return True

    if "[TASK_COMPLETE]" in last_text:
        return False

    # Fallback: if no marker found, assume waiting for input (safer)
    # This prevents premature auto-completion
    return True


def _build_final_report(messages: list, iterations: int, reason: str) -> str:
    """
    Build final report including Claude's last response (the research report).

    Args:
        messages: List of Claude's messages (user_messages from last response)
        iterations: Number of conversation iterations
        reason: Reason for session ending

    Returns:
        Formatted markdown string with full report (clean, no technical details)
    """
    # Extract text content from messages
    report_content = ""
    for msg in messages:
        if msg.get("type") == "text":
            content = msg.get("content", "")
            # Strip HITL markers from output
            content = content.replace("[TASK_COMPLETE]", "").replace("[WAITING_FOR_INPUT]", "")
            report_content += content.strip() + "\n\n"

    # Return clean report without technical details
    return report_content.strip()


def _build_conversation_summary(iterations: int, reason: str) -> str:
    """
    Build a markdown summary of the research session (without report content).

    Args:
        iterations: Number of conversation iterations
        reason: Reason for session ending

    Returns:
        Formatted markdown string (clean, user-friendly)
    """
    # Clean user-friendly messages based on reason
    if "timed out" in reason.lower():
        return "⏱️ **Session timed out.** Please start a new research session."
    elif "cancelled" in reason.lower() or "ended by user" in reason.lower():
        return "**Session ended.** Thank you for using Advanced Web Research!"
    elif "error" in reason.lower():
        return f"⚠️ **Something went wrong.** Please try again.\n\n*Details: {reason}*"
    elif "empty response" in reason.lower():
        return "**Session ended.** Thank you for using Advanced Web Research!"
    else:
        return "**Research complete.** Thank you for using Advanced Web Research!"


# Ray Serve deployment wrapper for Kodosumi ServeAPI
@serve.deployment
@serve.ingress(app)
class AdvancedWebResearch:
    """
    Ray Serve deployment class for Advanced Web Research agent.
    This pattern is required for Kodosumi applications deployed via Ray Serve.
    """
    pass


fast_app = AdvancedWebResearch.bind()
