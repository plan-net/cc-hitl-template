"""
Basic smoke tests for Claude + Kodosumi HITL Template.

These tests verify that the basic structure is intact and imports work correctly.
"""
import pytest


def test_agent_module_imports():
    """Test that agent module can be imported."""
    from claude_hitl_template import agent
    assert hasattr(agent, 'process_message')


def test_agent_process_message():
    """Test the placeholder process_message function."""
    from claude_hitl_template.agent import process_message

    result = process_message("Hello world")
    assert isinstance(result, str)
    assert "Hello world" in result


def test_query_module_imports():
    """Test that query module can be imported."""
    from claude_hitl_template import query
    assert hasattr(query, 'app')
    assert hasattr(query, 'fast_app')
    assert hasattr(query, 'prompt_form')


def test_configuration_constants():
    """Test that configuration constants are properly defined."""
    from claude_hitl_template.query import (
        CONVERSATION_TIMEOUT_SECONDS,
        MAX_MESSAGE_ITERATIONS
    )

    assert CONVERSATION_TIMEOUT_SECONDS == 600  # 10 minutes
    assert MAX_MESSAGE_ITERATIONS == 50


def test_package_metadata():
    """Test that package is properly installed."""
    import claude_hitl_template
    assert claude_hitl_template.__name__ == 'claude_hitl_template'
