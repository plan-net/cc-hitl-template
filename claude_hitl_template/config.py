"""Configuration management for Kodosumi integration.

This module loads runtime configuration for job completion behavior,
file management, and other Kodosumi-specific settings.

Configuration sources (in order of precedence):
1. Environment variables
2. Hardcoded defaults

Note: settings.json is for Claude Code CLI config only (marketplaces, plugins).
Runtime behavior should use environment variables or CLAUDE.md instructions.
"""

import os
import logging
from typing import Dict, List

logger = logging.getLogger(__name__)

# Default configuration
DEFAULT_CONFIG = {
    "completion_mode": "auto-complete",  # or "continuous"
    "upload_files": True,
    "max_turns": 50,
    "file_exclusions": [
        # Source code files
        ".py", ".pyc", ".pyo", ".pyd",

        # Config files
        ".json", ".yaml", ".yml", ".toml", ".ini",

        # Python artifacts
        ".egg-info", ".dist-info", "__pycache__",

        # Virtual environments
        ".venv", "venv", "env",

        # Version control
        ".git", ".gitignore", ".gitattributes",

        # IDE files
        ".vscode", ".idea", ".pytest_cache",

        # Other
        ".md", ".txt", ".log"
    ]
}


def load_kodosumi_config() -> Dict:
    """
    Load Kodosumi integration configuration from environment variables.

    Environment variables:
        COMPLETION_MODE: "auto-complete" (default) or "continuous"
        UPLOAD_FILES: "true" (default) or "false"
        MAX_TURNS: Maximum conversation iterations (default: 50)

    Returns:
        Dict with configuration keys:
        - completion_mode: str
        - upload_files: bool
        - max_turns: int
        - file_exclusions: List[str]
    """
    config = DEFAULT_CONFIG.copy()

    # Load completion mode
    completion_mode = os.getenv("COMPLETION_MODE", "").lower()
    if completion_mode in ["auto-complete", "continuous"]:
        config["completion_mode"] = completion_mode
        logger.info(f"Completion mode set to: {completion_mode}")

    # Load file upload setting
    upload_files = os.getenv("UPLOAD_FILES", "").lower()
    if upload_files in ["true", "false"]:
        config["upload_files"] = upload_files == "true"
        logger.info(f"File upload enabled: {config['upload_files']}")

    # Load max turns
    try:
        max_turns = int(os.getenv("MAX_TURNS", "50"))
        config["max_turns"] = max_turns
        logger.info(f"Max turns set to: {max_turns}")
    except ValueError:
        logger.warning("Invalid MAX_TURNS value, using default: 50")

    return config


def get_file_exclusions() -> List[str]:
    """
    Get list of file patterns to exclude from upload.

    Returns:
        List of file extensions and directory names to exclude
    """
    return DEFAULT_CONFIG["file_exclusions"]
