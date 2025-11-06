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
        Formatted markdown string
    """
    lines = ["# Task Completed", ""]

    # Add main content from Claude's messages
    lines.append("## Result")
    lines.append("")

    for msg in messages:
        if msg.get("type") == "text":
            content = msg.get("content", "")
            if content:
                # Strip completion marker from final output
                content = content.replace("[TASK_COMPLETE]", "").strip()
                if content:  # Only add if still has content after stripping
                    lines.append(content)
                    lines.append("")

    # Add file download links if any
    if files:
        lines.append("## Generated Files")
        lines.append("")
        for filename in files:
            # Kodosumi file download URL pattern
            lines.append(f"- 📄 [{filename}](/files/download/out/{filename})")
        lines.append("")

    # Add metadata footer
    lines.append("---")
    lines.append("")
    lines.append(f"**Status:** {reason}")
    lines.append(f"**Conversation turns:** {iteration}")
    lines.append(f"**Completed:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    return "\n".join(lines)


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
        Formatted markdown string
    """
    lines = ["# Conversation Ended", ""]
    lines.append(f"**Reason:** {reason}")
    lines.append(f"**Turns completed:** {iteration}")
    lines.append("")

    # Include last few messages if provided
    if messages:
        lines.append("## Last Messages")
        lines.append("")
        # Show last 3 messages
        for msg in messages[-3:]:
            if msg.get("type") == "text":
                content = msg.get("content", "")
                if content:
                    # Truncate long messages
                    if len(content) > 500:
                        content = content[:500] + "..."
                    lines.append(f"> {content}")
                    lines.append("")

    lines.append("---")
    lines.append(f"**Timestamp:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    return "\n".join(lines)
