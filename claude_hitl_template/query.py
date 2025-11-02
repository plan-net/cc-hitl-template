"""
Kodosumi service wrapper integrating Claude Agent SDK with HITL functionality.

This module demonstrates how to:
1. Create a Kodosumi service with a simple input form
2. Launch Claude Agent SDK conversations
3. Use Kodosumi HITL (lock/lease) for back-and-forth interaction with Claude
4. Handle timeouts and termination conditions
"""
import asyncio
import os
import ray
import fastapi
from kodosumi.core import Launch, ServeAPI, InputsError, Tracer
from kodosumi.core import forms as F
from kodosumi import dtypes
from ray import serve
from datetime import datetime
from claude_agent_sdk import (
    ClaudeSDKClient,
    ClaudeAgentOptions,
    AssistantMessage,
    TextBlock,
    ToolUseBlock,
    ToolResultBlock,
    ResultMessage
)

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
    Main conversation loop integrating Claude SDK with Kodosumi HITL.

    This function:
    1. Initializes Claude SDK client
    2. Sends initial prompt
    3. Streams responses from Claude
    4. Uses Kodosumi HITL (lock/lease) when Claude needs user input
    5. Handles termination conditions

    Args:
        inputs: Execution inputs including initial prompt
        tracer: Kodosumi tracer for progress updates and HITL
    """
    prompt = inputs["prompt"]
    conversation_history = []

    # Show initial status
    await tracer.markdown(f"""
## Conversation Started
**Timestamp:** {inputs["timestamp"]}
**Initial Prompt:** {prompt}

---

Initializing Claude Agent SDK...
    """)

    try:
        # Initialize Claude SDK client
        # Note: Authentication handled by Claude Code CLI
        client = ClaudeSDKClient(
            options=ClaudeAgentOptions(
                permission_mode="acceptEdits",  # Allow Claude to make edits if needed
                cwd=os.getcwd()  # Use current working directory
            )
        )

        await tracer.markdown("✓ Claude SDK initialized\n\nConnecting to Claude...")

        # Start conversation with initial prompt
        await client.connect(prompt)
        conversation_history.append({"role": "user", "content": prompt})

        await tracer.markdown("✓ Connected to Claude\n\nStreaming response...")

        # Main conversation loop
        iteration = 0
        start_time = asyncio.get_event_loop().time()

        while iteration < MAX_MESSAGE_ITERATIONS:
            iteration += 1

            # Check timeout
            elapsed = asyncio.get_event_loop().time() - start_time
            if elapsed > CONVERSATION_TIMEOUT_SECONDS:
                await tracer.markdown(f"\n\n⏱️ **Conversation timeout reached ({CONVERSATION_TIMEOUT_SECONDS / 60:.0f} minutes)**\n")
                break

            # Receive messages from Claude
            try:
                async for message in client.receive_response():
                    # Handle different message types
                    if isinstance(message, AssistantMessage):
                        # Process assistant's text response
                        for block in message.content:
                            if isinstance(block, TextBlock):
                                text = block.text
                                await tracer.markdown(f"\n\n**Claude:** {text}\n")
                                conversation_history.append({"role": "assistant", "content": text})

                                # Check if user wants to end conversation
                                if any(keyword in text.lower() for keyword in ["done", "exit", "goodbye"]):
                                    await tracer.markdown("\n\n✓ Conversation completed\n")
                                    await _show_conversation_summary(tracer, conversation_history)
                                    return

                            elif isinstance(block, ToolUseBlock):
                                # Show tool usage (optional, for transparency)
                                await tracer.markdown(f"\n🔧 *Using tool: {block.name}*\n")

                    elif isinstance(message, ResultMessage):
                        # Claude has finished the task
                        await tracer.markdown("\n\n✓ **Claude has completed the task**\n")
                        await _show_conversation_summary(tracer, conversation_history)
                        return

                # After receiving Claude's response, check if we need user input
                # This is where HITL happens - we pause execution and ask the user

                user_input = await tracer.lease(
                    "claude-input",
                    F.Model(
                        F.Markdown(f"""
### Continue Conversation?

The conversation has been running for {elapsed / 60:.1f} minutes.

You can:
- Provide more input to continue the conversation
- Type 'done' or 'exit' to end the conversation
- Let the 10-minute timeout end it automatically
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

                # User cancelled or provided input
                if not user_input or user_input.get("cancelled"):
                    await tracer.markdown("\n\n⏹️ **Conversation ended by user**\n")
                    await _show_conversation_summary(tracer, conversation_history)
                    return

                response_text = user_input.get("response", "").strip()

                # Check for termination keywords
                if response_text.lower() in ["done", "exit", "quit", "stop"]:
                    await tracer.markdown("\n\n✓ **Conversation completed**\n")
                    await _show_conversation_summary(tracer, conversation_history)
                    return

                if not response_text:
                    await tracer.markdown("\n\n⚠️ Empty response - ending conversation\n")
                    await _show_conversation_summary(tracer, conversation_history)
                    return

                # Send user's response back to Claude
                await tracer.markdown(f"\n\n**You:** {response_text}\n")
                conversation_history.append({"role": "user", "content": response_text})

                # Continue conversation with new input
                await client.query(response_text)
                await tracer.markdown("\n*Waiting for Claude's response...*\n")

            except asyncio.TimeoutError:
                await tracer.markdown("\n\n⏱️ **Timeout waiting for Claude's response**\n")
                break
            except Exception as e:
                await tracer.markdown(f"\n\n❌ **Error:** {str(e)}\n")
                break

        # Max iterations reached
        if iteration >= MAX_MESSAGE_ITERATIONS:
            await tracer.markdown(f"\n\n⚠️ **Maximum iteration limit reached ({MAX_MESSAGE_ITERATIONS})**\n")

        await _show_conversation_summary(tracer, conversation_history)

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
        # Cleanup
        try:
            await client.disconnect()
        except:
            pass


async def _show_conversation_summary(tracer: Tracer, history: list):
    """
    Display a summary of the conversation.

    Args:
        tracer: Kodosumi tracer for output
        history: List of conversation messages
    """
    await tracer.markdown(f"""
---

## Conversation Summary

**Total Messages:** {len(history)}

**Message Breakdown:**
- User messages: {sum(1 for m in history if m['role'] == 'user')}
- Assistant messages: {sum(1 for m in history if m['role'] == 'assistant')}

---

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
