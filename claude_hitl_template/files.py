"""File management for Kodosumi integration.

This module handles scanning for generated files and uploading them
to Kodosumi's /out directory for user download.
"""

import os
from pathlib import Path
from typing import List
import logging
from kodosumi.core import Tracer

logger = logging.getLogger(__name__)


async def scan_generated_files(exclusions: List[str]) -> List[str]:
    """
    Scan working directory for files likely generated during execution.

    Args:
        exclusions: List of patterns to exclude (extensions, directory names)

    Returns:
        List of absolute file paths to generated files
    """
    cwd = Path.cwd()
    generated = []

    logger.info(f"Scanning {cwd} for generated files...")

    # Recursively find all files
    for path in cwd.rglob("*"):
        if path.is_file() and not _should_exclude(path, exclusions):
            generated.append(str(path.absolute()))
            logger.debug(f"Found generated file: {path.name}")

    logger.info(f"Found {len(generated)} generated files")
    return generated


def _should_exclude(path: Path, exclusions: List[str]) -> bool:
    """
    Check if file should be excluded from upload.

    Args:
        path: File path to check
        exclusions: List of patterns to exclude

    Returns:
        True if file should be excluded, False otherwise
    """
    # Check if file is in excluded directory
    for part in path.parts:
        if part in exclusions or part.startswith('.'):
            return True

    # Check file extension
    if path.suffix in exclusions:
        return True

    # Check specific filenames
    if path.name in ['Dockerfile', 'pyproject.toml', 'README.md']:
        return True

    return False


async def upload_files_to_kodosumi(
    tracer: Tracer,
    file_paths: List[str]
) -> List[str]:
    """
    Upload files to Kodosumi /out directory.

    Args:
        tracer: Kodosumi tracer instance
        file_paths: List of absolute file paths to upload

    Returns:
        List of successfully uploaded filenames
    """
    if not file_paths:
        logger.info("No files to upload")
        return []

    await tracer.markdown(f"📤 Uploading {len(file_paths)} generated files...")

    # Get filesystem interface (sync version for Ray remote)
    fs = tracer.fs_sync()
    uploaded = []
    errors = []

    for file_path in file_paths:
        filename = os.path.basename(file_path)
        dest_path = f"/out/{filename}"

        try:
            logger.info(f"Uploading {filename} to {dest_path}")

            # Read file content
            with open(file_path, 'rb') as f:
                content = f.read()

            # Upload to Kodosumi
            with fs.open(dest_path, 'wb') as out_f:
                out_f.write(content)

            uploaded.append(filename)
            logger.info(f"✓ Uploaded {filename}")

        except Exception as e:
            error_msg = f"Failed to upload {filename}: {str(e)}"
            logger.error(error_msg)
            errors.append(error_msg)
            await tracer.markdown(f"⚠️ {error_msg}")

    # Report results
    if uploaded:
        await tracer.markdown(f"✓ Successfully uploaded {len(uploaded)} files")

    if errors:
        await tracer.markdown(f"⚠️ {len(errors)} upload(s) failed")

    return uploaded
