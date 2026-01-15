# Master Agent Configuration

This is the master (user-level) configuration for Claude agents running in containers.

## Container Environment

This configuration is baked into the Docker container at build time and provides:
- Base plugin configurations
- Default permissions
- Template-level behavior settings

## Settings Hierarchy

In containers, settings are resolved in this order:
1. **user** (this file) - `/app/template_user/.claude/`
2. **project** - `/app/.claude/`
3. **local** - Runtime overrides (not used)

Project settings override master settings.
