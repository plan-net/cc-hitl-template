"""Result formatting for job completion.

This module handles building the final markdown result that gets
returned when a job completes.
"""

from datetime import datetime
from typing import List, Dict


def build_final_result(
    messages: List[Dict],
    files: List[str],
    iteration: int,
    reason: str = "Task completed"
) -> str:
    """
    Build final markdown result for job completion.

    Args:
        messages: List of message dicts with "type" and "content"
        files: List of uploaded filenames
        iteration: Number of conversation turns
        reason: Completion reason/status

    Returns:
        Formatted markdown string (clean, no technical details)
    """
    lines = []

    # Add main content from Claude's messages (clean, no extra headers)
    for msg in messages:
        if msg.get("type") == "text":
            content = msg.get("content", "")
            if content:
                # Strip HITL markers from final output
                content = content.replace("[TASK_COMPLETE]", "")
                content = content.replace("[WAITING_FOR_INPUT]", "")
                content = content.strip()
                if content:  # Only add if still has content after stripping
                    lines.append(content)
                    lines.append("")

    # Add file download links if any (clean format)
    if files:
        lines.append("")
        lines.append("**Downloads:**")
        for filename in files:
            # Kodosumi file download URL pattern
            lines.append(f"- 📄 [{filename}](/files/download/out/{filename})")
        lines.append("")

    return "\n".join(lines).strip()


def build_conversation_summary(
    iteration: int,
    reason: str,
    messages: List[Dict] = None
) -> str:
    """
    Build summary for abnormal termination (timeout, error, max iterations).

    Args:
        iteration: Number of conversation turns completed
        reason: Why the conversation ended
        messages: Optional message history to include

    Returns:
        Formatted markdown string (clean, user-friendly)
    """
    # Clean user-friendly messages based on reason
    if "timed out" in reason.lower():
        return "⏱️ **Session timed out.** Please start a new research session."
    elif "cancelled" in reason.lower() or "ended by user" in reason.lower():
        return "**Session ended.** Thank you for using Advanced Web Research!"
    elif "error" in reason.lower():
        return "⚠️ **Something went wrong.** Please try again."
    elif "empty response" in reason.lower():
        return "**Session ended.** Thank you for using Advanced Web Research!"
    elif "maximum" in reason.lower():
        return "**Session limit reached.** Please start a new research session."
    else:
        return "**Research complete.** Thank you for using Advanced Web Research!"
