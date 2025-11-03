---
description: Analyze system and create setup/validation todo list
allowed-tools: [Task]
---

Analyze your system and create a comprehensive todo list for setup or validation.

## Your Task

Use the Task tool to invoke the setup agent with subagent_type "general-purpose".

Tell the agent to follow the instructions in `.claude/agents/setup.md` exactly.

The setup agent will:
1. Analyze your current system state
2. Check what's installed vs missing (prerequisites, venv, config, services)
3. Detect if setup was completed before
4. Create a comprehensive todo list with TodoWrite

**The agent does NOT install or configure anything - it only analyzes and creates the todo list.**

## Expected Outcome

After running `/cc-setup`, you'll receive:

**Todo List** showing:
- ✅ What's already completed (green checkmarks)
- ⏳ What needs to be done (pending items with exact commands)

**Analysis Summary** including:
- System type (macOS/Linux)
- Setup state (Fresh / Partial / Complete / Running)
- Prerequisites status
- Services status

## Next Steps

After the agent completes analysis, you'll work through the todo list with the main Claude Code agent:
- Execute each pending item one by one
- Get guidance and commands for each step
- Approve system modifications as needed
- Track progress in real-time via the todo list

This approach gives you full visibility and control over the setup process.
