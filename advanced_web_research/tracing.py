"""
Langfuse tracing utilities for Claude + Kodosumi HITL template.

This module provides:
- Langfuse client initialization from environment variables
- Helper functions for creating traces, spans, and observations
- Error handling wrappers (log warnings, don't crash)
- Trace context management for conversation sessions

Architecture:
- Hybrid tracing: SDK-level (agent.py) + orchestration-level (query.py)
- Non-blocking: Tracing failures don't stop conversations
- Hierarchical: Trace → Span → Observations for drill-down analysis
"""
import os
import uuid
import logging
from datetime import datetime, timezone
from typing import Optional, Dict, Any
from contextlib import contextmanager

# Conditional import: Langfuse is optional (graceful degradation)
try:
    from langfuse import Langfuse
    LANGFUSE_AVAILABLE = True
except ImportError:
    LANGFUSE_AVAILABLE = False
    logging.warning("Langfuse not installed - tracing disabled")

# Set up logging
logger = logging.getLogger(__name__)


class TracingContext:
    """
    Context manager for conversation tracing.

    Manages trace lifecycle for a single conversation session:
    - Creates root trace at conversation start
    - Provides trace_id for child spans/observations
    - Updates trace with final output on completion
    - Handles cleanup and error cases
    """

    def __init__(
        self,
        execution_id: str,
        initial_prompt: str,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize tracing context.

        Args:
            execution_id: Unique identifier for this conversation
            initial_prompt: User's initial prompt
            metadata: Additional metadata (container info, plugins, etc.)
        """
        self.execution_id = execution_id
        self.initial_prompt = initial_prompt
        self.metadata = metadata or {}
        self.trace_id: Optional[str] = None
        self.client: Optional[Any] = None  # Langfuse client
        self.enabled = False

    def __enter__(self):
        """Start trace on context entry."""
        self.trace_id = str(uuid.uuid4())

        # Initialize Langfuse client if available
        if not LANGFUSE_AVAILABLE:
            logger.info(f"Tracing disabled for {self.execution_id} (Langfuse not available)")
            return self

        try:
            self.client = get_langfuse_client()
            if self.client:
                # Create root trace
                self.client.trace(
                    id=self.trace_id,
                    name="Claude HITL Conversation",
                    input={
                        "prompt": self.initial_prompt,
                        "execution_id": self.execution_id
                    },
                    metadata={
                        **self.metadata,
                        "template": "claude-kodosumi-hitl",
                        "version": "0.2.0"
                    },
                    session_id=f"session-{self.execution_id}",
                    user_id=None  # Can be set if user auth is implemented
                )
                self.enabled = True
                logger.info(f"✓ Trace created: {self.trace_id} for {self.execution_id}")
        except Exception as e:
            logger.warning(f"Failed to create trace for {self.execution_id}: {e}")
            self.enabled = False

        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Cleanup on context exit."""
        if self.enabled and self.client:
            try:
                # Flush any pending events
                self.client.flush()
            except Exception as e:
                logger.warning(f"Error flushing trace data: {e}")

        return False  # Don't suppress exceptions

    def update_output(self, output: Dict[str, Any]):
        """
        Update trace with final output.

        Args:
            output: Output data (completion_reason, iterations, etc.)
        """
        if not self.enabled or not self.client or not self.trace_id:
            return

        try:
            # Update trace with output
            self.client.trace(
                id=self.trace_id,
                output=output
            )
            logger.debug(f"Updated trace output: {self.trace_id}")
        except Exception as e:
            logger.warning(f"Failed to update trace output: {e}")


def get_langfuse_client() -> Optional[Any]:
    """
    Get or create Langfuse client from environment variables.

    Reads configuration from:
    - LANGFUSE_PUBLIC_KEY: Public API key
    - LANGFUSE_SECRET_KEY: Secret API key
    - LANGFUSE_HOST: Langfuse server URL

    Returns:
        Langfuse client or None if not configured
    """
    if not LANGFUSE_AVAILABLE:
        return None

    try:
        public_key = os.getenv("LANGFUSE_PUBLIC_KEY")
        secret_key = os.getenv("LANGFUSE_SECRET_KEY")
        host = os.getenv("LANGFUSE_HOST")

        # Validate configuration
        if not all([public_key, secret_key, host]):
            missing = []
            if not public_key:
                missing.append("LANGFUSE_PUBLIC_KEY")
            if not secret_key:
                missing.append("LANGFUSE_SECRET_KEY")
            if not host:
                missing.append("LANGFUSE_HOST")
            logger.warning(f"Langfuse configuration incomplete - missing: {', '.join(missing)}")
            return None

        # Create client
        client = Langfuse(
            public_key=public_key,
            secret_key=secret_key,
            host=host
        )

        return client

    except Exception as e:
        logger.warning(f"Failed to initialize Langfuse client: {e}")
        return None


def create_span(
    trace_id: str,
    name: str,
    input_data: Optional[Dict[str, Any]] = None,
    metadata: Optional[Dict[str, Any]] = None,
    parent_observation_id: Optional[str] = None
) -> Optional[str]:
    """
    Create a span within a trace.

    Spans represent logical phases or iterations within a conversation.
    Examples: HITL iteration, query/response cycle, tool execution batch.

    Args:
        trace_id: Parent trace ID
        name: Descriptive span name
        input_data: Input data for this span
        metadata: Additional metadata
        parent_observation_id: Parent observation ID (for nested spans)

    Returns:
        Span ID or None if tracing failed
    """
    if not LANGFUSE_AVAILABLE:
        return None

    try:
        client = get_langfuse_client()
        if not client:
            return None

        span_id = str(uuid.uuid4())

        client.span(
            id=span_id,
            trace_id=trace_id,
            name=name,
            input=input_data or {},
            metadata=metadata or {},
            parent_observation_id=parent_observation_id,
            start_time=datetime.now(timezone.utc)
        )

        logger.debug(f"Created span: {name} ({span_id})")
        return span_id

    except Exception as e:
        logger.warning(f"Failed to create span '{name}': {e}")
        return None


def update_span(
    span_id: str,
    output_data: Optional[Dict[str, Any]] = None,
    metadata: Optional[Dict[str, Any]] = None,
    end_time: Optional[datetime] = None
) -> bool:
    """
    Update an existing span with output data or metadata.

    Args:
        span_id: Span ID to update
        output_data: Output data
        metadata: Additional metadata
        end_time: End timestamp (defaults to now)

    Returns:
        True if successful, False otherwise
    """
    if not LANGFUSE_AVAILABLE:
        return False

    try:
        client = get_langfuse_client()
        if not client:
            return False

        client.span(
            id=span_id,
            output=output_data or {},
            metadata=metadata or {},
            end_time=end_time or datetime.now(timezone.utc)
        )

        logger.debug(f"Updated span: {span_id}")
        return True

    except Exception as e:
        logger.warning(f"Failed to update span {span_id}: {e}")
        return False


def create_generation(
    trace_id: str,
    name: str,
    input_data: Optional[Dict[str, Any]] = None,
    output_data: Optional[Dict[str, Any]] = None,
    metadata: Optional[Dict[str, Any]] = None,
    parent_observation_id: Optional[str] = None,
    model: Optional[str] = None,
    usage: Optional[Dict[str, int]] = None
) -> Optional[str]:
    """
    Create a generation observation (for LLM calls or tool executions).

    Generations represent atomic operations: tool uses, tool results,
    thinking blocks, or text responses.

    Args:
        trace_id: Parent trace ID
        name: Descriptive generation name (e.g., "Tool Use: Read", "Thinking")
        input_data: Input data
        output_data: Output data
        metadata: Additional metadata
        parent_observation_id: Parent span/observation ID
        model: Model name (for LLM calls)
        usage: Token usage (for LLM calls)

    Returns:
        Generation ID or None if tracing failed
    """
    if not LANGFUSE_AVAILABLE:
        return None

    try:
        client = get_langfuse_client()
        if not client:
            return None

        generation_id = str(uuid.uuid4())

        client.generation(
            id=generation_id,
            trace_id=trace_id,
            name=name,
            input=input_data or {},
            output=output_data or {},
            metadata=metadata or {},
            parent_observation_id=parent_observation_id,
            model=model,
            usage=usage,
            start_time=datetime.now(timezone.utc),
            end_time=datetime.now(timezone.utc)  # Instant completion for most events
        )

        logger.debug(f"Created generation: {name} ({generation_id})")
        return generation_id

    except Exception as e:
        logger.warning(f"Failed to create generation '{name}': {e}")
        return None


def create_event(
    trace_id: str,
    name: str,
    input_data: Optional[Dict[str, Any]] = None,
    output_data: Optional[Dict[str, Any]] = None,
    metadata: Optional[Dict[str, Any]] = None,
    parent_observation_id: Optional[str] = None,
    level: str = "DEFAULT"
) -> Optional[str]:
    """
    Create an event observation (for logging important milestones).

    Events represent discrete moments: HITL pause, user input, completion.

    Args:
        trace_id: Parent trace ID
        name: Event name (e.g., "HITL Pause", "User Input")
        input_data: Input data
        output_data: Output data
        metadata: Additional metadata
        parent_observation_id: Parent span/observation ID
        level: Event level ("DEFAULT", "WARNING", "ERROR")

    Returns:
        Event ID or None if tracing failed
    """
    if not LANGFUSE_AVAILABLE:
        return None

    try:
        client = get_langfuse_client()
        if not client:
            return None

        event_id = str(uuid.uuid4())

        client.event(
            id=event_id,
            trace_id=trace_id,
            name=name,
            input=input_data or {},
            output=output_data or {},
            metadata=metadata or {},
            parent_observation_id=parent_observation_id,
            level=level,
            start_time=datetime.now(timezone.utc)
        )

        logger.debug(f"Created event: {name} ({event_id})")
        return event_id

    except Exception as e:
        logger.warning(f"Failed to create event '{name}': {e}")
        return None


@contextmanager
def traced_span(
    trace_id: Optional[str],
    name: str,
    input_data: Optional[Dict[str, Any]] = None,
    metadata: Optional[Dict[str, Any]] = None,
    parent_observation_id: Optional[str] = None
):
    """
    Context manager for automatic span lifecycle management.

    Usage:
        with traced_span(trace_id, "HITL Iteration", {"iteration": 1}) as span_id:
            # Do work
            pass
        # Span automatically updated with end time

    Args:
        trace_id: Parent trace ID
        name: Span name
        input_data: Input data
        metadata: Additional metadata
        parent_observation_id: Parent observation ID

    Yields:
        Span ID or None if tracing disabled
    """
    span_id = None

    if trace_id:
        span_id = create_span(
            trace_id=trace_id,
            name=name,
            input_data=input_data,
            metadata=metadata,
            parent_observation_id=parent_observation_id
        )

    try:
        yield span_id
    finally:
        if span_id:
            update_span(span_id)


def flush_langfuse():
    """
    Flush any pending Langfuse events.

    Call this before process exit to ensure all traces are sent.
    """
    if not LANGFUSE_AVAILABLE:
        return

    try:
        client = get_langfuse_client()
        if client:
            client.flush()
            logger.debug("Flushed Langfuse events")
    except Exception as e:
        logger.warning(f"Failed to flush Langfuse events: {e}")
