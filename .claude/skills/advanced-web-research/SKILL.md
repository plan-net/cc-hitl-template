---
name: advanced-web-research
description: Conduct comprehensive web research using AI-powered analysis (Exa.ai) and generate professional PPTX presentations (Gamma AI). Executes silently with clean output and 2 HITL checkpoints for user control.
tools: Bash, Read, Write
parameters:
  - name: silent_execution
    type: boolean
    default: true
    description: Execute API calls and processing steps without showing technical status messages, polling updates, or generation IDs. Only show clean final results.
  - name: show_complete_report
    type: boolean
    default: true
    description: Display the full research report from Exa API without truncation, summarization, or length limits. Essential for traceability and audit purposes.
  - name: use_cdn_links
    type: boolean
    default: true
    description: Show Digital Ocean Spaces CDN links for PPTX downloads instead of Gamma editor links. CDN links are directly downloadable without login.
  - name: exa_api_key
    type: env_var
    required: true
    env: EXA_API_KEY
    description: Exa.ai Research API authentication key for comprehensive web research
  - name: gamma_api_key
    type: env_var
    required: true
    env: GAMMA_API_KEY
    description: Gamma AI API authentication key for PPTX presentation generation
  - name: do_spaces_access_key
    type: env_var
    required: true
    env: DO_SPACES_ACCESS_KEY
    description: Digital Ocean Spaces S3-compatible access key for CDN uploads
  - name: do_spaces_secret_key
    type: env_var
    required: true
    env: DO_SPACES_SECRET_KEY
    description: Digital Ocean Spaces S3-compatible secret key for CDN uploads
---

# Advanced Web Research Skill

## Purpose

Conduct comprehensive web research on any topic using Exa.ai's AI-powered analysis and deliver results in two formats:
1. **Detailed markdown research report** with embedded source citations
2. **Professional PPTX presentation** via Gamma AI (optional, user-controlled)

## When to Use This Skill

**Appropriate Use Cases:**
- Strategic research requiring multi-source analysis
- Executive briefings needing presentation-ready deliverables
- Competitive intelligence gathering with synthesis
- Market trend research with actionable insights
- Technology landscape analysis with evaluation

**NOT Appropriate For:**
- Simple factual questions (use WebSearch instead - free and instant)
- Real-time information (use direct APIs)
- Content creation tasks (use specialized agents)

## Workflow Overview

This skill follows a simplified 6-step workflow with 2 HITL checkpoints:

1. **Focus Areas Clarification** (HITL Checkpoint 1) - Ask user about priorities
2. **Execute Research** (Silent) - Call Exa API, poll until complete
3. **Display Research Report** - Show full report with citations
4. **Presentation Decision** (HITL Checkpoint 2) - Confirm presentation generation if requested
5. **Generate Presentation** (Silent) - Call Gamma API, upload to CDN
6. **Final Output** - Show report + CDN download link, mark [TASK_COMPLETE]

**Estimated Time:** 3-8 minutes (depending on research depth and presentation)

---

## Step 1: Focus Areas Clarification (HITL Checkpoint 1)

### Purpose
Allow user to refine research focus before expensive API call.

### Instructions

**CRITICAL: Start directly with the question below. NO preamble, NO explanation, NO narration about reading/understanding the workflow.**

**Ask ONE brief question with contextual examples:**
```
Any specific focus areas or aspects you'd like me to prioritize in this research?

(e.g., [generate 3-4 relevant examples based on the research topic])
```

**Then immediately output:**
```
[WAITING_FOR_INPUT]
```

**Do NOT:**
- Show cost estimates (user already accepted via form)
- Provide multiple options or complex forms
- Add any other text, greetings, or explanations
- Show technical details about APIs or execution

**User Response Handling:**
- ANY text response: Incorporate into research instructions
- Empty response: Proceed with original question as-is

---

## Step 2: Execute Research (Silent)

### Purpose
Call Exa Research API and poll until completion. Execute entirely silently.

### Prerequisites
- `EXA_API_KEY` environment variable set
- User has responded to Step 1 focus question

### Instructions

**2.1 Create Research Task**

Execute this bash command silently (DO NOT show output to user):
```bash
RESEARCH_ID=$(curl -s -X POST "https://api.exa.ai/research/v1" \
  -H "Authorization: Bearer $EXA_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"instructions": "USER_RESEARCH_QUESTION_WITH_FOCUS_AREAS"}' | jq -r '.researchId')
```

Replace `USER_RESEARCH_QUESTION_WITH_FOCUS_AREAS` with the actual question from form input combined with focus areas from Step 1.

**2.2 Poll for Completion**

Poll every 10 seconds until status is "completed":
```bash
# Poll silently - DO NOT show status messages to user
while true; do
  RESPONSE=$(curl -s "https://api.exa.ai/research/v1/$RESEARCH_ID" \
    -H "Authorization: Bearer $EXA_API_KEY")

  STATUS=$(echo "$RESPONSE" | jq -r '.status')

  if [ "$STATUS" = "completed" ]; then
    # Save result for next step
    echo "$RESPONSE" > /tmp/research_result.json
    break
  elif [ "$STATUS" = "failed" ]; then
    # Handle error (see Error Handling section)
    echo "ERROR" > /tmp/research_status.txt
    break
  fi

  sleep 10
done
```

**Critical Rules:**
- DO NOT display polling status ("Checking status...", "Still running...")
- DO NOT show the research ID or task ID to user
- DO NOT show intermediate status messages
- Only proceed to Step 3 when status is "completed"

**Tracing Note:**
Orchestration-level tracing is handled automatically by query.py using Python SDK.
No manual tracing commands needed in this workflow.

---

## Step 3: Display Research Report

### Purpose
Show the complete research report to the user with proper formatting.

### Prerequisites
- Research completed successfully (Step 2)
- Result saved in `/tmp/research_result.json`

### Instructions

**3.1 Extract Report Content**

```bash
# Extract the full research report
REPORT=$(cat /tmp/research_result.json | jq -r '.output.content')
COST=$(cat /tmp/research_result.json | jq -r '.costDollars.total')
PAGES=$(cat /tmp/research_result.json | jq -r '.costDollars.numPages')
SEARCHES=$(cat /tmp/research_result.json | jq -r '.costDollars.numSearches')
```

**3.2 Display Full Report**

Show the COMPLETE report without any modifications:
```markdown
$REPORT
```

**Critical Rules:**
- NEVER truncate the report (no length limits, no "..." summaries)
- NEVER summarize or paraphrase the report content
- Show ALL sections, ALL citations, ALL details
- The full report is essential for traceability and audit
- If report is very long, that's fine - show it all

---

## Step 4: Presentation Decision (HITL Checkpoint 2)

### Purpose
Get user confirmation before spending Gamma AI credits on presentation generation.

### Prerequisites
- Research report displayed (Step 3)
- Form input `generate_presentation` flag available

### Instructions

**4.1 Check Form Flag**

The `generate_presentation` flag from the form indicates user's initial preference.

**4.2 If False: Skip to Step 6**

If presentation was not requested in the form, skip directly to Step 6 (Final Output).

**4.3 If True: Ask Confirmation**

Show this brief prompt:
```
Generate presentation (~10-15 slides)?

Your answer: [Yes/No]

[WAITING_FOR_INPUT]
```

**User Response Handling:**
- "Yes" / "yes" / "y" / "generate" → Proceed to Step 5
- "No" / "no" / "n" / "skip" → Skip to Step 6
- Any other text → Assume "Yes" (safer default for positive intent)

**Do NOT:**
- Show detailed slide count calculations
- Provide multiple options or complex forms
- Add explanations about what slides will contain
- Show technical details about Gamma API or costs

---

## Step 5: Generate Presentation (Silent)

### Purpose
Generate PPTX presentation via Gamma AI and upload to Digital Ocean Spaces CDN. Execute entirely silently.

### Prerequisites
- `GAMMA_API_KEY` environment variable set
- `DO_SPACES_ACCESS_KEY` and `DO_SPACES_SECRET_KEY` environment variables set
- User confirmed presentation generation (Step 4)

### Instructions

**5.1 Prepare Content for Gamma**

```bash
# Read research report
RESEARCH_CONTENT=$(cat /tmp/research_result.json | jq -r '.output.content')

# Save to file for Python script
echo "$RESEARCH_CONTENT" > /tmp/research_content.txt
```

**5.2 Create Presentation via Gamma API**

```bash
# Create presentation (silent - no output to user)
RESPONSE=$(curl -s -X POST "https://public-api.gamma.app/v1.0/generations" \
  -H "X-API-KEY: $GAMMA_API_KEY" \
  -H "Content-Type: application/json" \
  -d "{
    \"inputText\": $(cat /tmp/research_content.txt | jq -Rs .),
    \"format\": \"presentation\",
    \"numCards\": 12,
    \"exportAs\": \"pptx\",
    \"textMode\": \"generate\",
    \"textOptions\": {
      \"amount\": \"detailed\",
      \"tone\": \"Professional, analytical, research-focused\",
      \"language\": \"en\"
    }
  }")

GENERATION_ID=$(echo "$RESPONSE" | jq -r '.generationId')
```

**5.3 Poll for Completion**

```bash
# Poll silently - DO NOT show status to user
while true; do
  RESULT=$(curl -s "https://public-api.gamma.app/v1.0/generations/$GENERATION_ID" \
    -H "X-API-KEY: $GAMMA_API_KEY")

  STATUS=$(echo "$RESULT" | jq -r '.status')

  if [ "$STATUS" = "completed" ]; then
    EXPORT_URL=$(echo "$RESULT" | jq -r '.exportUrl')
    echo "$EXPORT_URL" > /tmp/export_url.txt
    break
  elif [ "$STATUS" = "failed" ]; then
    # Handle error (see Error Handling section)
    echo "ERROR" > /tmp/presentation_status.txt
    break
  fi

  sleep 10
done
```

**5.4 Download PPTX**

```bash
# Generate filename with timestamp
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
FILENAME="research_presentation_${TIMESTAMP}.pptx"

# Download from Gamma export URL
EXPORT_URL=$(cat /tmp/export_url.txt)
curl -s -L -o "/tmp/$FILENAME" "$EXPORT_URL"
```

**5.5 Upload to Digital Ocean Spaces**

```bash
python3 << 'UPLOAD_SCRIPT'
import boto3
from botocore.config import Config
from datetime import datetime
import os

# Generate filename
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
filename = f"research_presentation_{timestamp}.pptx"

# S3 client for DO Spaces
s3 = boto3.client('s3',
    endpoint_url="https://fra1.digitaloceanspaces.com",
    region_name="fra1",
    aws_access_key_id=os.getenv("DO_SPACES_ACCESS_KEY"),
    aws_secret_access_key=os.getenv("DO_SPACES_SECRET_KEY"),
    config=Config(signature_version='s3v4'))

# Upload with public-read ACL
s3.upload_file(
    f'/tmp/{filename}',
    'studios-general-bucket',
    f'research-presentations/{filename}',
    ExtraArgs={
        'ACL': 'public-read',
        'ContentType': 'application/vnd.openxmlformats-officedocument.presentationml.presentation'
    }
)

# Construct CDN URL
cdn_url = f"https://studios-general-bucket.fra1.digitaloceanspaces.com/research-presentations/{filename}"

# Save for Step 6
with open('/tmp/cdn_url.txt', 'w') as f:
    f.write(cdn_url)

print(cdn_url)
UPLOAD_SCRIPT
```

**Critical Rules:**
- DO NOT show "Generating presentation..." messages
- DO NOT show polling status or generation IDs
- DO NOT show the Gamma editor URL (gamma.app/docs/...)
- ONLY the DO Spaces CDN URL should be shown in final output
- Verify the file was uploaded successfully before showing the link

**Tracing Note:**
Orchestration-level tracing is handled automatically by query.py.
No manual tracing commands needed.

---

## Step 6: Final Output

### Purpose
Display final clean output with research report and optional presentation link.

### Prerequisites
- Research report displayed (Step 3)
- Presentation generated (Step 5) OR skipped (Step 4)

### Instructions

**6.1 Check if Presentation Was Generated**

```bash
if [ -f /tmp/cdn_url.txt ]; then
  CDN_URL=$(cat /tmp/cdn_url.txt)
fi
```

**6.2 Build Final Output**

If presentation was generated:
```markdown
$REPORT

---

**Download Presentation:** [research_presentation_TIMESTAMP.pptx]($CDN_URL)

[TASK_COMPLETE]
```

If presentation was skipped:
```markdown
$REPORT

[TASK_COMPLETE]
```

**Critical Rules:**
- Show the complete research report again (same content from Step 3)
- ONLY show DO Spaces CDN link (not gamma.app link)
- DO NOT add "Thank you", "Let me know if...", or other closing remarks
- The [TASK_COMPLETE] marker MUST be on its own line at the very end
- Verify the CDN URL file actually exists before showing link

---

## Silent Execution Rules

**These rules apply to ALL steps:**

### What NOT to Show

**❌ Phase Numbers or Technical Labels:**
- "Phase 1", "Step 2.1", "Checkpoint A"
- "Executing workflow step..."
- "Processing phase 3 of 6..."

**❌ Polling Status Messages:**
- "Checking status every 10 seconds..."
- "Research still running..."
- "Waiting for API response..."
- "Poll #5 - Status: pending"

**❌ Generation IDs or Task IDs:**
- "Research ID: r_abc123"
- "Generation ID: gen_xyz789"
- "Task ID: task_456def"

**❌ Intermediate Narration:**
- "Thank you! I'll now start researching..."
- "Let me generate a presentation for you..."
- "Now I'm going to..."
- "Hold on while I..."
- "Analyzing the results..."

**❌ Agent Meta-Narration:**
- "Let me read the skill definition to understand the workflow"
- "Now I understand the workflow. Let me begin with..."
- "I see the workflow involves X steps..."
- "Let me analyze what I need to do..."
- "I'll follow the SKILL.md instructions..."

**❌ Technical Details:**
- API endpoints, HTTP status codes
- JSON responses or curl commands
- Container logs or subprocess output
- Environment variable names

### What TO Show

**✅ HITL Questions (Steps 1 and 4):**
- Brief, clear questions for user decisions
- [WAITING_FOR_INPUT] marker after questions

**✅ Research Report (Step 3):**
- Complete markdown report from Exa API

**✅ Final Output (Step 6):**
- Complete research report (repeated from Step 3)
- DO Spaces CDN download link (if presentation generated)
- [TASK_COMPLETE] marker

**✅ Error Messages (if errors occur):**
- User-actionable error guidance
- No stack traces or technical debugging info

---

## Error Handling

### Pattern 1: Research API Failure

**Trigger:** Exa API returns status="failed" or HTTP error

**Response:**
```markdown
⚠️ **Research Failed**

Unable to complete research request. This may be due to:
- Temporary API service issue
- Invalid API key configuration
- Research question violates content policies

**Recommended Actions:**
1. Try again in a few minutes
2. Rephrase your research question
3. For urgent needs, use the free WebSearch tool

[TASK_COMPLETE]
```

### Pattern 2: Presentation API Failure

**Trigger:** Gamma API returns status="failed" or HTTP error

**Response:**
```markdown
[RESEARCH REPORT ALREADY SHOWN FROM STEP 3]

---

⚠️ **Presentation Generation Failed**

Research completed successfully, but unable to generate PPTX presentation.

**Possible Causes:**
- Gamma AI credit quota exhausted
- Presentation service temporarily unavailable
- Report content exceeds maximum length

**Your research report is complete above.** You can use it directly or try presentation generation again later.

[TASK_COMPLETE]
```

**Key:** Research is the core deliverable. Presentation failure does not fail the entire job.

### Pattern 3: CDN Upload Failure

**Trigger:** boto3 upload raises exception or file not accessible

**Response:**
```markdown
[RESEARCH REPORT ALREADY SHOWN FROM STEP 3]

---

⚠️ **CDN Upload Failed**

Presentation generated but unable to upload to cloud storage.

**Your research report is complete above.** The presentation was created but could not be hosted for download. Please try again or contact support.

[TASK_COMPLETE]
```

**Key:** Graceful degradation. Research report is always the primary deliverable.

---

## API Configuration

### Exa Research API

**Endpoint:** https://api.exa.ai/research/v1
**Method:** POST (create), GET (poll status)
**Auth:** Bearer token in Authorization header
**Environment Variable:** `EXA_API_KEY`

**Request Example:**
```bash
curl -X POST "https://api.exa.ai/research/v1" \
  -H "Authorization: Bearer $EXA_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"instructions": "Research question here"}'
```

**Response Format:**
```json
{
  "researchId": "r_abc123",
  "status": "running" | "completed" | "failed",
  "output": {"content": "Full markdown report..."},
  "costDollars": {"total": 0.35, "numPages": 45, "numSearches": 12}
}
```

### Gamma Presentation API

**Endpoint:** https://public-api.gamma.app/v1.0/generations
**Method:** POST (create), GET (poll status)
**Auth:** X-API-KEY header
**Environment Variable:** `GAMMA_API_KEY`

**Request Example:**
```bash
curl -X POST "https://public-api.gamma.app/v1.0/generations" \
  -H "X-API-KEY: $GAMMA_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"inputText": "...", "format": "presentation", "exportAs": "pptx"}'
```

**Response Format:**
```json
{
  "generationId": "gen_xyz789",
  "status": "pending" | "completed" | "failed",
  "exportUrl": "https://gamma-export.s3.amazonaws.com/...",
  "gammaUrl": "https://gamma.app/docs/...",
  "credits": {"deducted": 10, "remaining": 90}
}
```

### Digital Ocean Spaces (S3-Compatible CDN)

**Endpoint:** https://fra1.digitaloceanspaces.com
**Bucket:** studios-general-bucket
**Region:** fra1
**Auth:** AWS Signature V4 (via boto3)
**Environment Variables:** `DO_SPACES_ACCESS_KEY`, `DO_SPACES_SECRET_KEY`

**Upload Example:**
```python
import boto3
from botocore.config import Config
import os

s3 = boto3.client('s3',
    endpoint_url="https://fra1.digitaloceanspaces.com",
    region_name="fra1",
    aws_access_key_id=os.getenv("DO_SPACES_ACCESS_KEY"),
    aws_secret_access_key=os.getenv("DO_SPACES_SECRET_KEY"),
    config=Config(signature_version='s3v4'))

s3.upload_file('/tmp/file.pptx', 'studios-general-bucket',
    'research-presentations/file.pptx',
    ExtraArgs={'ACL': 'public-read'})
```

**Public URL Format:**
```
https://studios-general-bucket.fra1.digitaloceanspaces.com/research-presentations/{filename}
```

---

## Tracing (Handled Automatically)

**Orchestration-Level Tracing:**
All conversation tracing is handled automatically by the orchestration layer (`query.py`) using Python SDK from `claude_hitl_template/tracing.py`.

**What Gets Traced:**
- Research session start (input: research question, depth, parameters)
- HITL checkpoints (focus areas, presentation confirmation)
- Research execution timing
- Presentation generation timing
- Final output (research report content, CDN links)
- Errors and failures

**Configuration:**
Tracing is configured via environment variables:
- `LANGFUSE_PUBLIC_KEY`
- `LANGFUSE_SECRET_KEY`
- `LANGFUSE_HOST`

If these variables are not set, tracing is disabled (conversations continue normally).

**No Manual Tracing Required:**
You do not need to add any tracing commands in this workflow. The orchestration layer handles all trace creation, span management, and data flushing automatically.

---

## Version History

- **v3.0** (2026-01-12): Simplified from 8-phase to 6-step workflow. Replaced inline Bash curl Langfuse tracing with automatic Python SDK orchestration tracing. Extracted silent execution rules from hardcoded prompt. Reduced verbosity from 2,194 lines to ~850 lines. Added presentation confirmation HITL checkpoint.
- **v2.6** (2025-12-23): Added warnings against truncating research reports in Langfuse output.
- **v2.0** (2025-12-16): Replaced MCP tools with direct Exa Research API calls via Bash/curl.
- **v1.0** (2025-11-26): Initial release with MCP-based research tools.
