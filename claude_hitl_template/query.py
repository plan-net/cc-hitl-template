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
from ray import serve
from datetime import datetime
from .agent import create_actor, get_actor, cleanup_actor

# Configuration
CONVERSATION_TIMEOUT_SECONDS = 600  # 10 minutes
MAX_MESSAGE_ITERATIONS = 50  # Safety limit to prevent infinite loops

# Create ServeAPI instance
app = ServeAPI()


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
    F.Break(),
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
    return Launch(request, run_conversation, {
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
    # Generate unique execution ID
    execution_id = inputs.get("execution_id", str(uuid.uuid4()))
    prompt = inputs["prompt"]

    # Show initial status
    await tracer.markdown(f"""
## Conversation Started
**Timestamp:** {inputs["timestamp"]}
**Execution ID:** {execution_id}

Initializing Claude Agent SDK...
    """)

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

                # Main conversation loop
                iteration = 0
                while iteration < MAX_MESSAGE_ITERATIONS:
                    iteration += 1

                    # Check timeout
                    is_timeout = await actor.check_timeout.remote()
                    if is_timeout:
                        await tracer.markdown("\n⏱️ **Session timed out (11 minutes idle)**\n")
                        break

                    # Display Claude's messages
                    for msg in result["messages"]:
                        if msg["type"] == "text":
                            await tracer.markdown(f"\n**Claude:** {msg['content']}\n")
                        elif msg["type"] == "tool":
                            await tracer.markdown(f"\n🔧 *{msg['content']}*\n")

                    # Check if complete
                    if result["status"] == "complete":
                        await tracer.markdown("\n✓ **Task completed**\n")
                        await _show_conversation_summary(tracer, iteration)
                        break

                    # HITL pause - get user input
                    user_input = await tracer.lease(
                        "claude-input",
                        F.Model(
                            F.Markdown("""
### Continue Conversation?

You can:
- Provide more input to continue the conversation
- Type 'done', 'exit', or 'quit' to end the conversation
- Click "End Conversation" to stop
                            """),
                            F.InputArea(
                                label="Your Response",
                                name="response",
                                placeholder="Type your response or 'done' to finish...",
                                rows=3
                            ),
                            F.Submit("Send"),
                            F.Cancel("End Conversation")
                        )
                    )

                    # Check for cancellation
                    if not user_input or user_input.get("cancelled"):
                        await tracer.markdown("\n⏹️ **Conversation ended by user**\n")
                        await _show_conversation_summary(tracer, iteration)
                        break

                    response_text = user_input.get("response", "").strip()

                    # Check for termination keywords
                    if response_text.lower() in ["done", "exit", "quit", "stop"]:
                        await tracer.markdown("\n✓ **Conversation completed**\n")
                        await _show_conversation_summary(tracer, iteration)
                        break

                    if not response_text:
                        await tracer.markdown("\n⚠️ **Empty response - ending conversation**\n")
                        await _show_conversation_summary(tracer, iteration)
                        break

                    # Send to Claude
                    await tracer.markdown(f"\n**You:** {response_text}\n\n*Waiting for Claude's response...*\n")
                    result = await actor.query.remote(response_text)

                # Max iterations check
                if iteration >= MAX_MESSAGE_ITERATIONS:
                    await tracer.markdown(f"\n⚠️ **Maximum iteration limit reached ({MAX_MESSAGE_ITERATIONS})**\n")
                    await _show_conversation_summary(tracer, iteration)

                # Success - exit retry loop
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
                    await tracer.markdown("\n❌ **Session failed after retries**\n")
                    raise

    except Exception as e:
        await tracer.markdown(f"""
## Error

An error occurred during conversation:

```
{str(e)}
```

Please check your Claude Code CLI installation and authentication.
        """)
        raise

    finally:
        # Always cleanup actor
        await cleanup_actor(execution_id)


async def _show_conversation_summary(tracer: Tracer, iterations: int):
    """
    Display a summary of the conversation.

    Args:
        tracer: Kodosumi tracer for output
        iterations: Number of conversation iterations
    """
    await tracer.markdown(f"""
---

## Conversation Summary

**Total Iterations:** {iterations}

*Conversation ended at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*
    """)


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
