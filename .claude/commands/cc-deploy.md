---
description: Autonomous deployment with intelligent change detection
allowed-tools: [Task]
---

Deploy the application to Ray cluster with intelligent change detection and automated decision-making.

Use the deployment agent to handle the entire deployment process autonomously:

```
Use the Task tool to invoke the deployment agent.
Tell the agent to analyze the current state, detect what changed, and deploy accordingly.
The agent will handle everything and report back when done.
```

The deployment agent will:
1. Analyze what changed (code, configs, remote repos)
2. Decide what actions are needed
3. Ask for confirmation on risky operations (rebuild Docker image)
4. Execute deployment automatically
5. Validate services
6. Report results

After completion, the admin panel will be available at http://localhost:3370
