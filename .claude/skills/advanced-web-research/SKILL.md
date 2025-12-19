---
name: advanced-web-research
description: Conduct comprehensive web research using AI-powered analysis (Exa.ai) and generate professional PPTX presentations (Gamma AI). Use when user needs strategic research, competitive intelligence, market analysis, or presentation-ready deliverables. NOT for simple fact lookup (use WebSearch instead).
tools: Read, Write, Glob, Bash
---

# Advanced Web Research Agent

## Research Method

This plugin uses direct Exa Research API calls via Bash/curl for maximum reliability and transparency.

**API Endpoint:** https://api.exa.ai/research/v1
**Response Format:** Comprehensive markdown report with source citations
**Execution Time:** 3-10 minutes depending on research depth

---

## Workflow Checklist

**Complete these steps in order:**

- [ ] **Step 1:** Validate the research request
- [ ] **Step 2:** Get user cost confirmation
- [ ] **Step 3:** Execute research with Exa MCP tools (tracing is automatic)
- [ ] **Step 4:** Display research results
- [ ] **Step 5:** Generate presentation (if requested)

---

## Purpose

Conduct comprehensive web research on any topic and deliver professional outputs in two formats:
1. **Detailed markdown research report** with embedded source citations
2. **Automatically generated PPTX presentation** ready for stakeholder meetings

**Use this agent when:**
- Strategic research requiring comprehensive multi-source analysis
- Executive briefings needing presentation-ready deliverables
- Competitive intelligence gathering with synthesis
- Market trend research with actionable insights
- Technology landscape analysis with evaluation

**Don't use this agent for:**
- Simple factual questions → Use WebSearch (free, instant)
- Real-time information → Use direct APIs
- Content creation → Use Content Creation Agent

---

## Workflow Overview

This agent follows an 8-phase workflow with 2 HITL checkpoints for cost transparency and quality validation:

**Phase 0:** Validation and Setup
**Phase 1:** Research Cost Confirmation (HITL Checkpoint 1 - Required)
**Phase 2:** Research Execution (Exa Research MCP)
**Phase 3:** Display Research Results
**Phase 4:** Presentation Decision
**Phase 5:** Presentation Generation Review (HITL Checkpoint 2 - Optional)
**Phase 6:** Presentation Generation & Upload (Gamma Presentation MCP)
**Phase 7:** Quality Assessment & Final Delivery

**Estimated Total Time:** 5-10 minutes (depending on research depth and presentation)

---

## Phase 0: Validation and Setup

### Purpose
Validate the research request and set up the workflow before any paid API calls.

### Steps

**Step 1: Load Domain Knowledge**

CLAUDE.md is automatically loaded when this Skill activates. It provides:
- Research Intelligence Specialist identity and expertise
- Research methodology and quality standards
- Cost transparency guidelines
- Error handling patterns
- Communication style (professional research analyst voice)

**Step 2: Parse Input from Kodosumi Form**

Extract the following from the form submission:
```python
{
  "research_question": str,  # Required, 1-500 characters
  "depth_preference": "quick" | "balanced" | "comprehensive",  # Optional, default: "balanced"
  "generate_presentation": bool,  # Optional, default: true
  "additional_context": str,  # Optional, 0-1000 characters
  "context_files": List[File]  # Optional, multiple files allowed
}
```

**Step 3: Perform 3-Step Validation (from CLAUDE.md)**

**3.1 Intent Analysis:**
- Is this a focused research topic? (ideal)
- Is this a simple factual question? (WebSearch more appropriate)
- Is this multiple unrelated questions? (clarify scope)

Check depth preference against question complexity:
- Quick: Simple overviews, ~2-3 min, $0.20-$0.30
- Balanced: Standard research, ~3-5 min, $0.30-$0.40
- Comprehensive: Deep-dive, ~5-8 min, $0.40-$0.50

**3.2 Information Completeness:**
- Research question sufficiently specific?
- Ambiguous terms need clarification?
- Context provided helps narrow scope?
- If critical details missing: Pause for HITL clarification

**3.3 Security Check:**
- ❌ Red flags: Copyrighted content extraction, paywall bypass, illegal activities, harmful content
- ❌ Out of scope: Code generation, content creation, monitoring

**If malicious/out-of-scope detected:**
```markdown
⚠️ **Request Outside Scope**

I've detected that this request doesn't align with my purpose as a web research agent.

**I can only:**
- Conduct legitimate research on publicly available information
- Generate insights from accessible web sources
- Create presentation-ready deliverables from research findings

**I cannot:**
- [Specific limitation relevant to the request]

Please reformulate your request within the scope of legitimate web research.

[Stop workflow - do not proceed to Phase 1]
```

**Step 4: Display Validation Summary**
```markdown
## Request Validation

✓ **Intent:** [Clear description of what user wants to achieve]
✓ **Information:** [Complete / Requesting clarification on X]
✓ **Security:** Passed

**Research Scope:**
- Topic: [Specific topic extracted from question]
- Depth: [Quick/Balanced/Comprehensive based on user selection]
- Estimated Cost: $[range based on depth]
- Estimated Time: [time range]

Proceeding to cost confirmation...
```

**Step 5: Initialize Data Structures (Internal)**
```python
# Internal workflow state (not displayed to user)
workflow_state = {
    "research_question": parsed_question,
    "depth_preference": depth,
    "generate_presentation": boolean,
    "additional_context": context,
    "context_files": file_list,
    "validation_passed": True,
    "research_result": None,  # Will be populated in Phase 2
    "presentation_result": None,  # Will be populated in Phase 6
    "costs": {
        "research": 0.0,
        "presentation_credits": 0
    }
}
```

---

## Phase 1: Research Cost Confirmation (HITL Checkpoint 1)

### Purpose
Required user confirmation before making paid Exa.ai API calls. Prevents surprise costs.

### Display Cost Information

```markdown
## Research Cost Confirmation

Your research question: "{research_question}"

**Estimated Cost:** $0.20 - $0.50 (Exa.ai Research API)
**Estimated Time:** 2-5 minutes (research + presentation if enabled)

Research will include:
- Comprehensive web search with AI analysis
- Source citations and credibility assessment
- Detailed markdown report with insights
{if generate_presentation: "- Professional PPTX presentation (~10 Gamma credits)"}

**Note:** This is a paid API service. Failed attempts count toward usage.

**Depth Preference:** {depth_preference}
{if depth == "quick": "- Breadth: 5-10 sources, Time: ~2-3 min, Cost: $0.20-$0.30"}
{if depth == "balanced": "- Breadth: 10-20 sources, Time: ~3-5 min, Cost: $0.30-$0.40"}
{if depth == "comprehensive": "- Breadth: 20-30+ sources, Time: ~5-8 min, Cost: $0.40-$0.50"}
```

### Present Options

**Use Kodosumi HITL form with 3 options:**

```yaml
# Kodosumi lock structure (pseudo-YAML for illustration)
lock:
  type: selection
  options:
    - id: proceed
      label: "Proceed with Research"
      description: "Start comprehensive research (cost: $0.20-$0.50)"
      action: continue_to_phase_2

    - id: quick_search
      label: "Use Free WebSearch Instead"
      description: "For simple questions, free built-in search may suffice"
      action: hand_off_to_websearch

    - id: cancel
      label: "Cancel"
      description: "Do not perform research"
      action: exit_workflow

  free_form_enabled: true
  placeholder: "Or adjust your question before proceeding..."
```

### Handle User Response

**If user selects "proceed":**
- Continue to Phase 2 (Research Execution)

**If user selects "quick_search":**
```markdown
## Handing Off to WebSearch

For simple factual questions, WebSearch is more cost-effective.

Using WebSearch to answer: "{research_question}"

[Invoke WebSearch tool with question]
[Display WebSearch results]

**Note:** If you need comprehensive analysis with citations and presentation, you can invoke me again.

[TASK_COMPLETE]
```

**If user selects "cancel":**
```markdown
## Research Cancelled

User cancelled research request. No API calls were made, no costs incurred.

**To Conduct Research Later:**
Invoke the research agent again with your question.

**Cost-Saving Tip:** For simple factual questions, the free WebSearch tool may be more appropriate than comprehensive research ($0 vs $0.20-$0.50).

[TASK_COMPLETE]
```

**If user provides free-form response:**
- Parse as adjusted question
- Re-run Phase 0 validation with new question
- Re-display Phase 1 with updated question

---

## Phase 2: Research Execution

### Purpose
Execute comprehensive web research via Exa Research API with async task polling. Each API call is traced to Langfuse for observability.

### API Configuration

**Exa Research API:**
- Endpoint: `https://api.exa.ai/research/v1`
- API Key: `cc1fea87-d577-4b91-b81f-efe42dc06218`

**Langfuse Tracing API:**
- Endpoint: `http://172.211.242.223:3000/api/public/ingestion`
- Auth: `Basic cGstbGYtMDc2NGY0MWQtOTdmZi00YTczLTljY2MtOGQ3NjNiNTg4NmU1OnNrLWxmLTY4ZWRlZjI2LTE0MWMtNDkwMS1hYjViLTJlYmZhNzk2MDJkNQ==`

---

### Step 1: Initialize Langfuse Trace

Before making any Exa API calls, create a Langfuse trace to track this research session.

**Generate unique IDs** (you will reuse these throughout the research):
- `TRACE_ID`: A unique UUID for this trace (e.g., generate with `uuidgen | tr 'A-Z' 'a-z'`)
- `SPAN_ID`: A unique UUID for the research execution span
- `SESSION_ID`: Format as `research-<timestamp>-<random>` (e.g., `research-1766043000-abc123`)

**Execute Langfuse API Call:**

```bash
# Generate IDs for this research session
TRACE_ID=$(uuidgen | tr 'A-Z' 'a-z')
SPAN_ID=$(uuidgen | tr 'A-Z' 'a-z')
OBS_ID=$(uuidgen | tr 'A-Z' 'a-z')
SESSION_ID="research-$(date +%s)-$$"
TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%S.000Z")

# IMPORTANT: Replace <research_question> with the actual question text
RESEARCH_QUESTION="<research_question>"

# Create trace + span + first observation
curl -s -X POST "http://172.211.242.223:3000/api/public/ingestion" \
  -H "Content-Type: application/json" \
  -H "Authorization: Basic cGstbGYtMDc2NGY0MWQtOTdmZi00YTczLTljY2MtOGQ3NjNiNTg4NmU1OnNrLWxmLTY4ZWRlZjI2LTE0MWMtNDkwMS1hYjViLTJlYmZhNzk2MDJkNQ==" \
  -d "{
    \"batch\": [
      {
        \"id\": \"$(uuidgen)\",
        \"type\": \"trace-create\",
        \"timestamp\": \"$TIMESTAMP\",
        \"body\": {
          \"id\": \"$TRACE_ID\",
          \"sessionId\": \"$SESSION_ID\",
          \"name\": \"Advanced Web Research Session\",
          \"input\": {\"research_question\": \"$RESEARCH_QUESTION\"},
          \"metadata\": {\"plugin\": \"advanced-web-research\", \"version\": \"2.2\"}
        }
      },
      {
        \"id\": \"$(uuidgen)\",
        \"type\": \"span-create\",
        \"timestamp\": \"$TIMESTAMP\",
        \"body\": {
          \"id\": \"$SPAN_ID\",
          \"traceId\": \"$TRACE_ID\",
          \"name\": \"Research Execution\",
          \"startTime\": \"$TIMESTAMP\"
        }
      },
      {
        \"id\": \"$(uuidgen)\",
        \"type\": \"generation-create\",
        \"timestamp\": \"$TIMESTAMP\",
        \"body\": {
          \"id\": \"$OBS_ID\",
          \"traceId\": \"$TRACE_ID\",
          \"parentObservationId\": \"$SPAN_ID\",
          \"name\": \"Exa API: Create Research Task (POST)\",
          \"startTime\": \"$TIMESTAMP\",
          \"input\": {\"endpoint\": \"POST /research/v1\", \"instructions\": \"$RESEARCH_QUESTION\"}
        }
      }
    ]
  }"

echo "Langfuse trace initialized: $TRACE_ID"
echo "Session ID: $SESSION_ID"
```

**IMPORTANT:** Save these variables for use in subsequent steps:
- `TRACE_ID`, `SPAN_ID`, `SESSION_ID` - needed for all Langfuse calls
- `OBS_ID` - the current observation ID (will change with each new observation)
- `RESEARCH_QUESTION` - the user's research question

---

### Step 2: Create Research Task (Exa API)

**Display progress:**
```markdown
🔍 **Starting research task...**
Topic: {research_question}
```

**Execute Exa API Call:**

```bash
# Create research task (use RESEARCH_QUESTION from Step 1)
RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "https://api.exa.ai/research/v1" \
  -H "Authorization: Bearer cc1fea87-d577-4b91-b81f-efe42dc06218" \
  -H "Content-Type: application/json" \
  -d "{\"instructions\": \"$RESEARCH_QUESTION\"}")

HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
BODY=$(echo "$RESPONSE" | sed '$d')

if [ "$HTTP_CODE" -eq 200 ] || [ "$HTTP_CODE" -eq 201 ]; then
  RESEARCH_ID=$(echo "$BODY" | jq -r '.researchId')
  echo "✅ Research task created: $RESEARCH_ID"
else
  echo "❌ API Error (HTTP $HTTP_CODE): $BODY"
fi
```

**Expected Response:**
```json
{"researchId": "r_abc123def456"}
```

**IMPORTANT:** Save `RESEARCH_ID` for polling and Langfuse updates.

---

### Step 3: Update Langfuse - Research Task Created

After Exa returns the research ID, update the first observation:

```bash
TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%S.000Z")

curl -s -X POST "http://172.211.242.223:3000/api/public/ingestion" \
  -H "Content-Type: application/json" \
  -H "Authorization: Basic cGstbGYtMDc2NGY0MWQtOTdmZi00YTczLTljY2MtOGQ3NjNiNTg4NmU1OnNrLWxmLTY4ZWRlZjI2LTE0MWMtNDkwMS1hYjViLTJlYmZhNzk2MDJkNQ==" \
  -d "{
    \"batch\": [
      {
        \"id\": \"$(uuidgen)\",
        \"type\": \"generation-update\",
        \"timestamp\": \"$TIMESTAMP\",
        \"body\": {
          \"id\": \"$OBS_ID\",
          \"traceId\": \"$TRACE_ID\",
          \"output\": {\"research_id\": \"$RESEARCH_ID\", \"status\": \"created\"},
          \"endTime\": \"$TIMESTAMP\"
        }
      }
    ]
  }"
```

---

### Step 4: Poll for Completion (Loop)

Poll the Exa API every 10 seconds until research completes. For EACH poll iteration:

1. Create a new Langfuse observation (generation-create)
2. Call Exa GET API
3. Update the Langfuse observation with the result (generation-update)
4. If completed, proceed to Step 5

**Display initial progress:**
```markdown
⏳ **Research in progress...** (checking status every 10s)
```

**For each poll iteration, execute these commands IN ORDER:**

#### 4a. Create Langfuse observation for this poll:

```bash
# Generate new observation ID for this poll
POLL_NUM=1  # Increment this for each poll: 1, 2, 3, etc.
OBS_ID=$(uuidgen | tr 'A-Z' 'a-z')
TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%S.000Z")

curl -s -X POST "http://172.211.242.223:3000/api/public/ingestion" \
  -H "Content-Type: application/json" \
  -H "Authorization: Basic cGstbGYtMDc2NGY0MWQtOTdmZi00YTczLTljY2MtOGQ3NjNiNTg4NmU1OnNrLWxmLTY4ZWRlZjI2LTE0MWMtNDkwMS1hYjViLTJlYmZhNzk2MDJkNQ==" \
  -d "{
    \"batch\": [
      {
        \"id\": \"$(uuidgen)\",
        \"type\": \"generation-create\",
        \"timestamp\": \"$TIMESTAMP\",
        \"body\": {
          \"id\": \"$OBS_ID\",
          \"traceId\": \"$TRACE_ID\",
          \"parentObservationId\": \"$SPAN_ID\",
          \"name\": \"Exa API: Poll Status (GET #$POLL_NUM)\",
          \"startTime\": \"$TIMESTAMP\",
          \"input\": {\"endpoint\": \"GET /research/v1/$RESEARCH_ID\", \"poll_number\": $POLL_NUM}
        }
      }
    ]
  }"
```

#### 4b. Call Exa API to check status:

```bash
RESPONSE=$(curl -s -w "\n%{http_code}" -X GET \
  "https://api.exa.ai/research/v1/$RESEARCH_ID" \
  -H "Authorization: Bearer cc1fea87-d577-4b91-b81f-efe42dc06218")

HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
BODY=$(echo "$RESPONSE" | sed '$d')
STATUS=$(echo "$BODY" | jq -r '.status')

echo "Poll #$POLL_NUM - Status: $STATUS"
```

#### 4c. Update Langfuse observation with poll result:

```bash
TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%S.000Z")

curl -s -X POST "http://172.211.242.223:3000/api/public/ingestion" \
  -H "Content-Type: application/json" \
  -H "Authorization: Basic cGstbGYtMDc2NGY0MWQtOTdmZi00YTczLTljY2MtOGQ3NjNiNTg4NmU1OnNrLWxmLTY4ZWRlZjI2LTE0MWMtNDkwMS1hYjViLTJlYmZhNzk2MDJkNQ==" \
  -d "{
    \"batch\": [
      {
        \"id\": \"$(uuidgen)\",
        \"type\": \"generation-update\",
        \"timestamp\": \"$TIMESTAMP\",
        \"body\": {
          \"id\": \"$OBS_ID\",
          \"traceId\": \"$TRACE_ID\",
          \"output\": {\"status\": \"$STATUS\"},
          \"endTime\": \"$TIMESTAMP\"
        }
      }
    ]
  }"
```

#### 4d. Check status and continue or proceed:

- If `STATUS` is `"running"`: Wait 10 seconds, increment `POLL_NUM`, and repeat Step 4
- If `STATUS` is `"completed"`: Proceed to Step 5
- If `STATUS` is `"failed"`: Display error and stop

**Expected Response (when completed):**
```json
{
  "researchId": "r_abc123def456",
  "status": "completed",
  "output": {"content": "# Research Report\n\n## Overview\n..."},
  "costDollars": {"total": 0.446, "numPages": 69, "numSearches": 20},
  "finishedAt": 1765870212995
}
```

---

### Step 5: Complete Langfuse Trace

When research completes successfully, send the FINAL Langfuse update. This updates the trace with output and closes the span.

**IMPORTANT:** The Langfuse ingestion API does NOT support `trace-update` as a separate event type. To add output to an existing trace, you must:
1. Use `trace-create` with the **same trace ID** - Langfuse will merge/update the trace
2. Include the `output` field in the body
3. This is the official way to update traces per Langfuse documentation

**Use Python for proper JSON escaping of the full report:**

```bash
# Save the research result to a temp file first
echo "$BODY" > /tmp/research_result.json

# Use Python to send the FULL report to Langfuse with proper JSON escaping
python3 << PYTHON_SCRIPT
import json
import re
import subprocess
import uuid
from datetime import datetime, timezone

# Read IDs from environment file
def read_env_var(name):
    with open('/tmp/research_ids.env', 'r') as f:
        for line in f:
            if line.startswith(f'{name}='):
                return line.strip().split('=', 1)[1]
    return ''

trace_id = read_env_var('TRACE_ID')
span_id = read_env_var('SPAN_ID')
research_id = read_env_var('RESEARCH_ID')

# Read and clean the research result
with open('/tmp/research_result.json', 'rb') as f:
    raw_bytes = f.read()

cleaned = raw_bytes.decode('utf-8', errors='replace')
cleaned = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f]', '', cleaned)

data = json.loads(cleaned)

# Extract FULL report (not summary!)
full_report = data.get('output', {}).get('content', 'No content')
cost = data.get('costDollars', {})
report_title = full_report.split('\n')[0].replace('# ', '') if full_report else 'Research Report'

# Create output payload with FULL report
output_payload = {
    "status": "completed",
    "research_id": research_id,
    "cost_usd": cost.get('total', 0),
    "num_pages": int(cost.get('numPages', 0)),
    "num_searches": cost.get('numSearches', 0),
    "report_title": report_title,
    "full_research_report": full_report  # FULL REPORT - not summary!
}

timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")

# Batch payload for Langfuse
batch_payload = {
    "batch": [
        {
            "id": str(uuid.uuid4()),
            "type": "trace-create",
            "timestamp": timestamp,
            "body": {
                "id": trace_id,
                "output": output_payload
            }
        },
        {
            "id": str(uuid.uuid4()),
            "type": "span-update",
            "timestamp": timestamp,
            "body": {
                "id": span_id,
                "traceId": trace_id,
                "endTime": timestamp,
                "metadata": {
                    "research_id": research_id,
                    "cost_usd": cost.get('total', 0),
                    "num_pages": int(cost.get('numPages', 0)),
                    "num_searches": cost.get('numSearches', 0)
                }
            }
        }
    ]
}

# Send to Langfuse
result = subprocess.run([
    'curl', '-s', '-X', 'POST',
    'http://172.211.242.223:3000/api/public/ingestion',
    '-H', 'Content-Type: application/json',
    '-H', 'Authorization: Basic cGstbGYtMDc2NGY0MWQtOTdmZi00YTczLTljY2MtOGQ3NjNiNTg4NmU1OnNrLWxmLTY4ZWRlZjI2LTE0MWMtNDkwMS1hYjViLTJlYmZhNzk2MDJkNQ==',
    '-d', json.dumps(batch_payload)
], capture_output=True, text=True)

print(f"Langfuse response: {result.stdout}")
print(f"Trace ID: {trace_id}")
print(f"Report length: {len(full_report)} characters")
PYTHON_SCRIPT
```

---

### Step 6: Parse and Display Results

Save the research result and display to user:

```bash
# Save result to temp file
echo "$BODY" > /tmp/research_result.json

# Parse and display using Python
python3 << 'PYTHON_EOF'
import json

with open('/tmp/research_result.json', 'r') as f:
    data = json.load(f)

report = data.get('output', {}).get('content', '')
cost = data.get('costDollars', {})
created_at = data.get('createdAt', 0)
finished_at = data.get('finishedAt', 0)
time_seconds = (finished_at - created_at) / 1000 if finished_at > created_at else 0

print(f"✅ **Research complete** ({time_seconds:.1f}s)")
print("")
print(f"**Cost:** ${cost.get('total', 0):.2f}")
print(f"**Pages Analyzed:** {cost.get('numPages', 0):.0f} pages")
print(f"**Searches:** {cost.get('numSearches', 0)} queries")
print("")
print("---")
print("")
print(report)
PYTHON_EOF
```

**Display success:**
```markdown
✅ **Research complete** ({time_seconds}s)

**Cost:** ${total_cost}
**Pages Analyzed:** {num_pages} pages
**Searches:** {num_searches} queries

---

{Full markdown report from API}
```

**Continue to Phase 3**

**On timeout (elapsed >= max_wait_time):**
```markdown
⚠️ **Research Timeout**

The research task did not complete within 10 minutes.

**Possible Causes:**
- Complex research question requiring extensive analysis
- High API load causing delays
- Network connectivity issues

**Recommended Actions:**
1. **Simplify question:** Try a more focused research question
2. **Reduce depth:** Select "Quick" instead of "Comprehensive"
3. **Try again:** The task may be retried automatically by Exa
4. **Use WebSearch:** For urgent needs, use free WebSearch tool

**Task ID:** {task_id} (you can check status later via Exa dashboard)

No charges incurred for incomplete research.

[TASK_COMPLETE - Timeout state]
```

**On failure (status == "failed"):**
```markdown
❌ **Research Failed**

The research service encountered an error: {result.get("error", "Unknown error")}

**Possible Causes:**
- API service temporarily unavailable
- Invalid API key (check EXA_API_KEY in .env)
- Rate limit exceeded
- Research question violates content policies

**Recommended Actions:**
1. **Check API key:** Verify EXA_API_KEY is set correctly
2. **Wait and retry:** API may be experiencing temporary issues
3. **Check Exa status:** Visit https://exa.ai/status
4. **Use WebSearch:** For urgent needs, use free WebSearch tool

**Task ID:** {task_id}

No charges incurred for failed research.

[TASK_COMPLETE - Error state]
```

### Step 4: Quality Checkpoint - Research Data Sufficiency

**Internal quality assessment (from CLAUDE.md guidelines):**

```python
# Calculate quality scores
completeness_score = calculate_completeness(
    report=result["report"],
    question=workflow_state["research_question"]
)  # Target: 90%+

confidence_score = assess_confidence(
    status=result["status"],
    report_length=len(result["report"]),
    has_citations=bool(citations_in_report)
)  # Target: High

data_quality_score = assess_data_quality(
    cost_breakdown=result["metadata"]["cost_breakdown"],
    reasoning_tokens=result["metadata"]["reasoning_tokens"],
    page_count=result["metadata"]["page_count"]
)  # Target: Good

overall_quality = (completeness_score + confidence_score + data_quality_score) / 3
```

**If overall_quality < 75%:**
```markdown
⚠️ **Insufficient Research Quality**

Research completed but data quality does not meet standards.

**Quality Assessment:**
- Completeness: {completeness_score}% (target: 90%+)
- Confidence: {confidence_score}
- Data Quality: {data_quality_score}

**Quality Issues Detected:**
{list specific issues: e.g., "Only 1 major section found", "No citations included", etc.}

**Options:**
1. **Retry with 'Comprehensive' depth:** More thorough analysis (higher cost: $0.40-$0.50)
2. **Refine research question:** Add specificity to guide better results
3. **Proceed with partial data:** (Not recommended - may not be actionable)

How would you like to proceed?

[Pause for HITL response - if retry, go back to Phase 1 with adjusted parameters]
```

**If overall_quality ≥ 75%:**
- Continue to Phase 3 (display results)

---

## Phase 3: Display Research Results

### Purpose
Display the complete research report with cost and performance statistics.

### Step 1: Format Research Report

**Structure:**
```markdown
# Research Analysis: {research_question}

## Executive Summary

**Key Findings:**
{extract_top_3_insights(report)}

**Deliverables:**
- 📄 Comprehensive research report (embedded below)
{if generate_presentation: "- 📊 Professional PPTX presentation (generation pending)"}

---

## Research Statistics

**Cost Breakdown:**
- Searches: ${metadata.cost_breakdown.searches}
- Pages processed: ${metadata.cost_breakdown.pages}
- Reasoning tokens: ${metadata.cost_breakdown.reasoning}
- **Total Cost:** ${metadata.cost_breakdown.total}

**Performance Metrics:**
- Execution time: {metadata.execution_time}s
- Model: {metadata.model}
- Pages analyzed: {metadata.page_count}
- Reasoning tokens: {metadata.reasoning_tokens}
- Task ID: `{metadata.task_id}`

---

## Research Report

{result["report"]}

{The report already includes H2 sections and citations from Exa.ai}

---
```

### Step 2: Display Report to User

Use `tracer.markdown()` to display the formatted report in Kodosumi admin panel.

### Step 3: Update Workflow State

```python
workflow_state["research_displayed"] = True
workflow_state["costs"]["research"] = result["metadata"]["cost_breakdown"]["total"]
```

---

## Phase 4: Presentation Decision

### Purpose
Determine whether to generate a PPTX presentation based on user's form selection.

### Decision Logic

```python
if not workflow_state["generate_presentation"]:
    # User opted out of presentation
    # Skip to Phase 7 (Final Delivery without presentation)
    skip_to_phase_7()
else:
    # User wants presentation
    # Continue to Phase 5 (Presentation Review HITL)
    continue_to_phase_5()
```

**If skipping presentation:**
```markdown
## Presentation Generation Skipped

User opted out of presentation generation.

**Deliverable:** Research report only (displayed above)

Proceeding to final delivery...

[Continue to Phase 7]
```

---

## Phase 5: Presentation Generation Review (HITL Checkpoint 2 - Optional)

### Purpose
Optional quality review checkpoint before spending Gamma AI credits on presentation generation.

### Display Research Preview

```markdown
## Research Complete - Review Before Presentation

Research analysis completed successfully.

**Quick Preview:**
- Research cost: ${actual_cost}
- Execution time: {time}s
- {H2_count} major sections identified

**Key Finding:** {extract_first_major_insight_from_report()}

I'm ready to generate a professional PPTX presentation (~{estimated_slide_count} slides, ~10 Gamma credits).
```

### Calculate Estimated Slide Count

**Use heuristic algorithm (from design):**

```python
def calculate_optimal_slide_count(report_markdown: str) -> int:
    """
    Calculate optimal slide count based on report structure.

    Algorithm:
    1. Count H2 headers (natural slide breaks)
    2. If well-structured (≥3 H2s): slide_count = H2_count + 2 (title + summary)
    3. Adjust for bullet point density (+2 if >10 bullets/section)
    4. If poorly structured (<3 H2s): Character-based estimation
    5. Clamp to range: 10-30 slides
    """
    import re

    # Count H2 headers
    h2_pattern = r'^## '
    h2_count = len(re.findall(h2_pattern, report_markdown, re.MULTILINE))

    # Count bullet points
    bullet_pattern = r'^\s*[-*] '
    bullet_count = len(re.findall(bullet_pattern, report_markdown, re.MULTILINE))

    if h2_count >= 3:
        # Well-structured: Use H2 count as base
        slide_count = h2_count + 2  # +2 for title and summary

        # Adjust for bullet density
        avg_bullets_per_section = bullet_count / h2_count if h2_count > 0 else 0
        if avg_bullets_per_section > 10:
            slide_count += 2  # Dense content needs more slides
    else:
        # Poorly structured: Character-based estimation
        char_count = len(report_markdown)

        # Base estimate: 600 chars per slide (or 400 if high bullet density)
        chars_per_slide = 400 if bullet_count > 20 else 600
        slide_count = max(10, char_count // chars_per_slide)

    # Clamp to valid range
    return max(10, min(30, slide_count))
```

**Display calculated estimate:**
```markdown
**Estimated Presentation:**
- Slide count: ~{calculated_slide_count} slides (based on {H2_count} major sections)
- Gamma AI credits: ~10 credits
- Generation time: ~1-2 minutes
```

### Present Options

**Use Kodosumi HITL form with 3 options:**

```yaml
lock:
  type: selection
  options:
    - id: generate
      label: "Yes, Generate Presentation"
      description: "Create PPTX with ~{slide_count} slides (~10 credits)"
      action: continue_to_phase_6

    - id: skip
      label: "Skip Presentation"
      description: "Deliver report only (save Gamma credits)"
      action: skip_to_phase_7

    - id: adjust_slides
      label: "Adjust Slide Count"
      description: "Specify different slide count (10-30 range)"
      action: prompt_for_slide_count

  free_form_enabled: true
  placeholder: "Or provide specific guidance for the presentation (e.g., 'Focus on competitive analysis slides', 'Make it 20 slides')..."
```

### Handle User Response

**If user selects "generate":**
- Continue to Phase 6 with calculated slide count

**If user selects "skip":**
```markdown
## Presentation Generation Skipped

User opted to skip presentation generation.

**Deliverable:** Research report only (displayed above)

**Credits Saved:** ~10 Gamma credits

Proceeding to final delivery...

[Continue to Phase 7 without presentation]
```

**If user selects "adjust_slides":**
- Prompt: "How many slides would you like? (10-30 range)"
- Parse user input for integer
- Validate: 10 ≤ slide_count ≤ 30
- If invalid: Display error, ask again
- If valid: Continue to Phase 6 with user-specified slide count

**If user provides free-form response:**
- Parse for slide count ("20 slides", "make it longer", etc.)
- Parse for specific guidance ("focus on X", "emphasize Y")
- Store guidance in `workflow_state["presentation_guidance"]`
- Continue to Phase 6 with parsed parameters

---

## Phase 6: Presentation Generation & Upload

### Purpose
Generate PPTX presentation via Gamma Presentation MCP and upload to Kodosumi file system (and optionally cloud CDN).

### Step 1: Transform Markdown for Gamma

**Create Gamma-optimized markdown structure:**

```python
def transform_markdown_for_presentation(
    exa_report: str,
    research_question: str,
    disclaimer_card: str = None
) -> str:
    """
    Transform Exa research report into Gamma-optimized markdown.

    Transformations:
    1. Add H1 title slide
    2. Add H2 research question slide
    3. Parse H2 sections from report (skip H1s)
    4. Add H2 report notice slide
    5. Prepend disclaimer card if provided

    Returns: Gamma-ready markdown string
    """
    lines = []

    # Add disclaimer if provided (from .env: GAMMA_DISCLAIMER_CARD)
    if disclaimer_card:
        lines.append(disclaimer_card)
        lines.append("\n---\n")

    # Add title slide
    lines.append("# Advanced Web Research Report\n\n")

    # Add research question slide
    lines.append(f"## Research Question\n{research_question}\n\n")

    # Parse H2 sections from Exa report
    import re
    h2_sections = re.findall(r'^## (.+?)(?=\n##|\Z)', exa_report, re.MULTILINE | re.DOTALL)

    if len(h2_sections) == 0:
        # Fallback: No structure, use first 2000 chars
        lines.append("## Research Findings\n")
        lines.append(exa_report[:2000])
    else:
        # Add each H2 section as slide
        for section in h2_sections:
            lines.append(f"## {section}\n")

    # Add report creation notice
    lines.append("\n## Report Creation Notice\n")
    lines.append("AI-generated comprehensive research report created by Advanced Web Research Agent using Exa.ai Research API.\n")

    return "\n".join(lines)
```

### Step 2: Start Presentation Generation (Custom Gamma MCP)

**Display progress:**
```markdown
📊 **Generating presentation** ({slide_count} slides)...
```

**MCP Tool:** `generate_presentation` (Custom Gamma MCP at .claude/mcp-servers/gamma-presentation)

**Note:** This tool uses environment variables from .env for all configuration (theme, style, tone, etc.)

**Parameters:**
```python
{
    "title": workflow_state["research_question"],  # Presentation title
    "content": transformed_markdown,  # From Step 1
    "num_cards": str(slide_count)  # From Phase 5 calculation or user input (as string)
}
```

**All other settings read from environment variables:**
- `GAMMA_THEME`, `GAMMA_TEXT_MODE`, `GAMMA_TEXT_AMOUNT`
- `GAMMA_TEXT_TONE`, `GAMMA_TEXT_AUDIENCE`, `GAMMA_TEXT_LANGUAGE`
- `GAMMA_IMAGE_SOURCE`, `GAMMA_IMAGE_MODEL`, `GAMMA_IMAGE_STYLE`
- `GAMMA_CARD_DIMENSIONS`, `GAMMA_DISCLAIMER_CARD`, `GAMMA_ADDITIONAL_INSTRUCTIONS`

**Expected Return:**
```python
{
    "task_id": "gamma_abc123",  # Task ID for polling
    "status": "generating",
    "message": "Presentation generation started. Use check_generation_status to poll for completion."
}
```

### Step 3: Poll for Completion (Custom Gamma MCP)

**MCP Tool:** `check_generation_status` (poll every 10 seconds)

**Parameters:**
```python
{
    "task_id": task_id  # From generate_presentation response
}
```

**Polling Logic:**
```python
import time

task_id = start_response["task_id"]
max_wait_time = 300  # 5 minutes max for presentation generation
poll_interval = 10   # 10 seconds between polls
elapsed = 0

while elapsed < max_wait_time:
    time.sleep(poll_interval)
    elapsed += poll_interval

    # Update user every 10 seconds
    print(f"📊 **Generating presentation...** ({elapsed}s elapsed)")

    # Poll for status
    result = check_generation_status(task_id=task_id)

    if result["status"] == "complete":
        # Success - presentation ready
        break
    elif result["status"] == "failed":
        # Error occurred
        raise Exception(result.get("error", "Unknown error"))
    # else: status == "generating", continue polling
```

**Expected Return (when complete):**
```python
{
    "task_id": "gamma_abc123",
    "status": "complete",
    "gamma_url": "https://gamma.app/docs/xyz789",  # Gamma app URL for editing
    "download_url": "https://gamma.app/api/download/xyz789.pptx",  # PPTX download URL
    "credits_used": 8
}
```

### Step 4: Handle MCP Response

**On completion (status == "complete"):**

**Display success:**
```markdown
✅ **Presentation generated** ({result.credits_used} credits used)

**Gamma URL:** {result.gamma_url}
**Download:** {result.download_url}
```

**Download PPTX file:**
```python
import requests

# Download the PPTX file
response = requests.get(result["download_url"])
pptx_bytes = response.content

# Save to temporary file (will be uploaded to S3/DO Spaces in next step)
```

**Continue to Step 5 (File Storage)**

**On timeout (elapsed >= max_wait_time):**
```markdown
✅ **Research Analysis Completed Successfully**

{research report already displayed in Phase 3}

---

⚠️ **Presentation Generation Timeout**

The presentation did not complete within 5 minutes. This is unusual.

**Possible Causes:**
- Complex presentation with many slides
- Gamma AI experiencing high load
- Network connectivity issues

**Your Research Report:**
The core deliverable (research analysis) succeeded and is displayed above.

**Recommended Actions:**
1. **Check Gamma dashboard:** Visit https://gamma.app to see if presentation completed
2. **Retry later:** Try generating the presentation again
3. **Manual creation:** Use the research report above to create presentation manually

**Task ID:** {task_id}

[Continue to Phase 7 - Final Delivery without presentation]
```

**On failure (status == "failed"):**
```markdown
✅ **Research Analysis Completed Successfully**

{research report already displayed in Phase 3}

---

⚠️ **Presentation Generation Failed**

Unable to generate PPTX presentation: {result.get("error", "Unknown error")}

**Possible Causes:**
- Gamma AI credit quota exhausted (check your account at https://gamma.app)
- Gamma API service temporarily unavailable
- Invalid GAMMA_API_KEY in .env file
- Content violates Gamma policies

**Your Research Report:**
The core deliverable (research analysis) succeeded and is displayed above. The presentation is an additional feature.

**Recommended Actions:**
1. **Check credits:** Verify Gamma account has available credits
2. **Check API key:** Ensure GAMMA_API_KEY is set correctly in .env
3. **Retry later:** May succeed if transient error
4. **Manual creation:** Use the research report above to create presentation

**Task ID:** {task_id}

[Continue to Phase 7 - Final Delivery without presentation]
```

### Step 5: File Storage

**Save PPTX to temporary file:**

```python
import os
from datetime import datetime

def sanitize_filename(research_question: str, max_length: int = 50) -> str:
    """
    Convert research question into safe filename.

    Rules:
    - Remove special characters (keep alphanumeric and spaces)
    - Replace multiple spaces with single underscore
    - Convert to lowercase
    - Truncate to max_length characters
    - Add timestamp for uniqueness
    """
    import re

    # Remove special characters
    cleaned = re.sub(r'[^a-zA-Z0-9\s]', '', research_question)

    # Replace multiple spaces with single underscore
    cleaned = re.sub(r'\s+', '_', cleaned.strip())

    # Convert to lowercase
    cleaned = cleaned.lower()

    # Truncate
    if len(cleaned) > max_length:
        cleaned = cleaned[:max_length]

    # Add timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    return f"research_report_{cleaned}_{timestamp}.pptx"

# Generate safe filename
filename = sanitize_filename(workflow_state["research_question"])
temp_dir = "/tmp/research_temp"
os.makedirs(temp_dir, exist_ok=True)
temp_file_path = os.path.join(temp_dir, filename)

# Write PPTX bytes to file
with open(temp_file_path, 'wb') as f:
    f.write(result["pptx_bytes"])
```

**Upload to Kodosumi file system:**

```python
# Use Kodosumi tracer's file system upload
kodosumi_url = tracer.fs().upload(
    file_path=temp_file_path,
    chunk_size=1024*1024  # 1MB chunks
)

# Store URL in workflow state
workflow_state["presentation_kodosumi_url"] = kodosumi_url
```

**Display progress:**
```markdown
📤 **Uploading presentation to file system...**
✅ **Upload complete**
```

### Step 5: Optional Cloud CDN Upload (S3/DO Spaces)

**Only if DO Spaces is configured:**

```python
if os.getenv("DO_SPACES_ACCESS_KEY"):
    # Try S3 Storage MCP
    try:
        result = s3_storage_mcp.upload_file(
            file_path=temp_file_path,
            remote_key=f"research-reports/{filename}",
            bucket=os.getenv("DO_SPACES_BUCKET"),
            acl="public-read",
            content_type="application/vnd.openxmlformats-officedocument.presentationml.presentation"
        )

        if result["status"] == "success":
            cdn_url = result["public_url"]
            workflow_state["presentation_cdn_url"] = cdn_url

            # Display success
            print("✅ Uploaded to cloud CDN")
        else:
            # Graceful degradation
            workflow_state["presentation_cdn_url"] = None
            print("⚠️ Cloud CDN upload failed (using Kodosumi URL only)")

    except Exception as e:
        # Graceful degradation
        workflow_state["presentation_cdn_url"] = None
        print(f"⚠️ Cloud CDN upload error: {str(e)}")
else:
    # DO Spaces not configured - skip
    workflow_state["presentation_cdn_url"] = None
```

### Step 6: Cleanup Temporary Files

```python
# Always clean up temp files, even if errors occurred
import shutil
try:
    shutil.rmtree(temp_dir)
except Exception:
    pass  # Best effort cleanup
```

### Step 7: Update Workflow State

```python
workflow_state["presentation_generated"] = True
workflow_state["costs"]["presentation_credits"] = result["credits_used"]
```

---

## Phase 7: Quality Assessment & Final Delivery

### Purpose
Final quality check and formatted output delivery with completion signal.

### Step 1: Final Quality Assessment

**Internal quality check (from CLAUDE.md):**

```python
# Deliverables checklist
deliverables_complete = {
    "research_report": workflow_state["research_result"] is not None,
    "research_displayed": workflow_state["research_displayed"],
    "citations_present": check_citations_in_report(workflow_state["research_result"]["report"]),
    "cost_displayed": workflow_state["costs"]["research"] > 0,
    "presentation_status": (
        "generated" if workflow_state.get("presentation_generated")
        else "skipped" if not workflow_state["generate_presentation"]
        else "failed_gracefully"
    ),
    "download_links": bool(workflow_state.get("presentation_kodosumi_url"))
}

# Actionability check
actionability = {
    "has_insights": check_for_insights(workflow_state["research_result"]["report"]),
    "has_key_findings": check_for_executive_summary(workflow_state["research_result"]["report"]),
    "has_recommendations": check_for_recommendations(workflow_state["research_result"]["report"])
}

# Clarity check
clarity = {
    "has_executive_summary": check_for_executive_summary_section(workflow_state["research_result"]["report"]),
    "jargon_explained": True,  # Exa.ai handles this
    "presentation_plain_language": workflow_state.get("presentation_generated", True)  # Gamma handles this
}

# Calculate overall quality
overall_quality = calculate_overall_quality(deliverables_complete, actionability, clarity)
```

**If overall_quality < 75%:**
```markdown
⚠️ **Quality Enhancement Needed**

Final quality assessment indicates enhancement opportunities:
{list specific issues}

**Enhancements Applied:**
{add contextual introduction}
{add limitations section if data quality was marginal}
{explain any component failures}
{provide alternative actions}

Proceeding with delivery...
```

**If overall_quality ≥ 75%:**
```markdown
✅ **Quality Assessment: {overall_quality}%** (Target: ≥75%)

All quality standards met. Proceeding with delivery...
```

### Step 2: Format Final Markdown Response

**Complete structured output:**

```markdown
# Research Analysis: {research_question}

## Executive Summary

**Key Findings:**
{extract_top_3_5_insights(report)}

**Deliverables:**
- 📄 Comprehensive research report (embedded below)
{if presentation_generated: "- 📊 Professional PPTX presentation ({slide_count} slides)"}

---

## Research Statistics

**Cost Breakdown:**
- Searches: ${metadata.cost_breakdown.searches}
- Pages processed: ${metadata.cost_breakdown.pages}
- Reasoning tokens: ${metadata.cost_breakdown.reasoning}
- **Total Cost:** ${metadata.cost_breakdown.total}

**Performance Metrics:**
- Execution time: {metadata.execution_time}s
- Model: {metadata.model}
- Pages analyzed: {metadata.page_count}
- Reasoning tokens: {metadata.reasoning_tokens}
- Task ID: `{metadata.task_id}`

---

## Research Report

{full_markdown_report_from_exa}

{The report includes H2 sections and citations}

---

{if presentation_generated:}
## Download Presentation

📊 **[Download PPTX Report]({presentation_kodosumi_url})**

**Presentation Details:**
- Slides: {slide_count}
- Format: PowerPoint (.pptx)
- Credits used: {credits_used}
- Credits remaining: {credits_remaining}

{if presentation_cdn_url:}
**Public CDN Link:** [{presentation_cdn_url}]({presentation_cdn_url})
{endif}

{if cloud_cdn_failed:}
⚠️ **Cloud CDN Note:** Unable to upload to Digital Ocean Spaces ({error_type}). File is available via Kodosumi link above.
{endif}

---
{endif}

## Methodology

**Research Approach:**
- AI-powered comprehensive web search (Exa.ai Research Pro API)
- Source credibility assessment and multi-source synthesis
- Citation tracking for verifiability

**Data Sources:**
- {metadata.page_count} web pages processed
- {metadata.searches} search operations
- {metadata.reasoning_tokens} reasoning tokens for analysis

**Quality Standards:**
- Completeness: {completeness_score}%
- Confidence: {confidence_level}
- Data Quality: {data_quality_level}

**Note:** This is AI-generated research based on publicly available information. Verify critical information independently before making strategic decisions.

---

[TASK_COMPLETE]
```

### Step 3: Strip Completion Marker from Final Output

**Important:** The `[TASK_COMPLETE]` marker is used for auto-completion detection but should NOT appear in the final user-facing output.

**The system (results.py in Bansumi) strips this marker automatically.**

User sees everything EXCEPT the `[TASK_COMPLETE]` line.

### Step 4: Signal Completion

**Auto-Completion Behavior:**

When the Skill outputs `[TASK_COMPLETE]` at the end of the response:
1. Bansumi detects the completion signal
2. If `COMPLETION_MODE=auto-complete` (set in config), job auto-finalizes
3. User receives complete deliverable in Kodosumi inbox
4. NO additional "Continue" button required

**Completion Conditions Met:**
- ✅ Research report retrieved and displayed
- ✅ Presentation generated (or gracefully skipped/failed)
- ✅ All files uploaded to file system
- ✅ Download links provided
- ✅ Cost statistics displayed
- ✅ No further user input needed

---

## Error Recovery Patterns

### Pattern 1: Research Failure After All Retries

**Trigger:** Exa Research API returns `status="failed"`

**Response:**
```markdown
❌ **Research Backend Unavailable**

{display attempt logs showing all 3 failures}

**Recommended Actions:**
1. Wait a few minutes and try again
2. Check Exa.ai status page
3. For urgent needs, use free WebSearch

No costs incurred beyond failed attempts.

[TASK_COMPLETE - Error state]
```

**Key:** Clean error exit with actionable guidance.

### Pattern 2: Research Quality Insufficient

**Trigger:** Quality assessment scores < 75% in Phase 2 Step 4

**Response:**
```markdown
⚠️ **Insufficient Research Quality**

{display quality scores and specific issues}

**Options:**
1. Retry with 'Comprehensive' depth
2. Refine research question
3. Proceed with partial data (not recommended)

[Pause for HITL - if retry, return to Phase 1 with adjusted parameters]
```

**Key:** Give user control over retry vs. proceed decision.

### Pattern 3: Presentation Generation Failure

**Trigger:** Gamma Presentation MCP returns `status="failed"`

**Response:**
```markdown
✅ **Research Analysis Completed Successfully**

{display full research report from Phase 3}

⚠️ **Presentation Generation Failed**

{explain error, possible causes, alternatives}

[Continue to Phase 7 - deliver report without presentation]
```

**Key:** Graceful degradation. Research is the core deliverable; presentation is an enhancement.

### Pattern 4: Cloud CDN Upload Failure

**Trigger:** S3 Storage MCP upload fails (credentials, network, quota)

**Response:**
```markdown
{display full research and presentation normally}

⚠️ **Cloud CDN Upload Failed**

Unable to upload to Digital Ocean Spaces: {error_type}

File is available via Kodosumi link above. Cloud CDN is optional.

[Continue with delivery]
```

**Key:** Graceful degradation. Kodosumi URL is primary; CDN is convenience.

### Pattern 5: Mid-Workflow User Adjustment

**Trigger:** User provides free-form response at HITL checkpoints

**Phase 1 Adjustment (Question Refinement):**
```markdown
## Adjusted Research Question

Original: "{original_question}"
Adjusted: "{parsed_adjusted_question}"

Re-validating request...

{Go back to Phase 0 with new question}
```

**Phase 5 Adjustment (Slide Count or Guidance):**
```markdown
## Presentation Customization

{if slide_count_specified: "Slide count: {user_specified_count}"}
{if guidance_provided: "Guidance: {user_guidance}"}

Proceeding with customized presentation generation...

{Continue to Phase 6 with adjusted parameters}
```

### Pattern 6: Invalid Slide Count Input

**Trigger:** User specifies slide count outside 10-30 range

**Response:**
```markdown
⚠️ **Invalid Slide Count**

Requested slide count: {user_input}

Valid range: 10-30 slides (Gamma AI limitation)

Please specify a slide count within the valid range, or select "Yes, Generate Presentation" to use the recommended count ({calculated_slide_count} slides).

[Re-display Phase 5 options]
```

**Key:** Clear validation error with guidance to fix.

---

## Custom Code Functions (Python Standard Library Only)

### Function 1: Markdown Transformation for Presentation

**Location:** Inline in SKILL.md or small helper script in skills/advanced-web-research/scripts/

```python
def transform_markdown_for_presentation(
    exa_report: str,
    research_question: str,
    disclaimer_card: str = None
) -> str:
    """
    Transform Exa research report into Gamma-optimized markdown.

    See Phase 6 Step 1 for complete implementation.
    """
    # Implementation provided in Phase 6 Step 1
    pass
```

### Function 2: Optimal Slide Count Calculation

```python
def calculate_optimal_slide_count(report_markdown: str) -> int:
    """
    Calculate optimal slide count based on report structure.

    See Phase 5 for complete implementation.
    """
    # Implementation provided in Phase 5
    pass
```

### Function 3: Filename Sanitization

```python
def sanitize_filename(research_question: str, max_length: int = 50) -> str:
    """
    Convert research question into safe filename.

    See Phase 6 Step 4 for complete implementation.
    """
    # Implementation provided in Phase 6 Step 4
    pass
```

**All functions use Python standard library only:**
- `re` (regex) - Always available
- `datetime` - Always available
- `os` - Always available

No external packages required.

---

## Integration Points

### With CLAUDE.md (Config Repo)

**CLAUDE.md provides:**
- Agent identity: Research Intelligence Specialist
- Domain expertise: Research methodology, source assessment
- Behavioral guidelines: Professional analyst voice
- Cost transparency: How to communicate costs
- Error handling: How to respond to failures
- Quality standards: 75% threshold, assessment criteria

**SKILL.md references:**
- "Load domain knowledge from CLAUDE.md" (Phase 0 Step 1)
- "Apply 3-step validation from CLAUDE.md" (Phase 0 Step 3)
- "Use cost communication pattern from CLAUDE.md" (Phase 1)
- "Apply quality assessment from CLAUDE.md" (Phase 2 Step 4, Phase 7 Step 1)
- "Follow error communication guidelines from CLAUDE.md" (all error patterns)

**Separation:**
- CLAUDE.md = WHO you are, WHAT you know, HOW you should behave
- SKILL.md = WHEN to do things, WHICH steps to execute, WHERE to delegate

### With External APIs

**Exa Research API (https://api.exa.ai/research/v1):**
- Invoked: Phase 2 Step 1 & Step 2 via Bash/curl
- Authentication: Bearer token in Authorization header
- API Key: cc1fea87-d577-4b91-b81f-efe42dc06218
- Method: POST to create task, GET to poll status
- Returns: Async task ID (researchId), then research report markdown with sources
- Error handling: HTTP status codes, JSON error responses

**Custom Gamma Presentation MCP (.claude/mcp-servers/gamma-presentation):**
- Invoked: Phase 6 Step 2 & Step 3
- Tools: `generate_presentation`, `check_generation_status`
- Parameters: title, content (markdown), num_cards (configured via env vars)
- Returns: Async task ID, then Gamma URL and PPTX download URL

**S3 Storage MCP (Optional):**
- Invoked: Phase 6 Step 5
- Tool: `upload_file`
- Parameters: file_path, remote_key, bucket, acl
- Returns: Public CDN URL or error

**Error Handling:**
- Each API call includes HTTP status code checking
- Graceful degradation on failure
- User-facing error messages explain impact

### With Kodosumi Form

**Form provides initial input:**
- research_question (required)
- depth_preference (optional, default: "balanced")
- generate_presentation (optional, default: true)
- additional_context (optional)
- context_files (optional)

**Parsed in Phase 0 Step 2**

### With Kodosumi HITL Locks

**HITL Checkpoint 1 (Phase 1):**
- Lock type: selection
- Options: [Proceed] [Use WebSearch] [Cancel]
- Free-form: enabled (question adjustment)

**HITL Checkpoint 2 (Phase 5):**
- Lock type: selection
- Options: [Generate] [Skip] [Adjust]
- Free-form: enabled (presentation guidance)

**Quality Check Pauses (conditional):**
- Phase 2 Step 4: If quality < 75%, pause for user decision
- Phase 5: Always pause for presentation review (unless user skipped)

---

## Time Estimates

- **Full workflow (with presentation):** 5-10 minutes
  - Phase 0 (Validation): 10-20 seconds
  - Phase 1 (Cost Confirmation): 15-30 seconds (HITL wait time)
  - Phase 2 (Research Execution): 2-8 minutes (depends on depth)
  - Phase 3 (Display Results): 5-10 seconds
  - Phase 4 (Decision Logic): Immediate
  - Phase 5 (Presentation Review): 15-30 seconds (HITL wait time)
  - Phase 6 (Presentation Generation): 1-2 minutes
  - Phase 7 (Final Delivery): 5-10 seconds

- **Quick depth (no presentation):** 2-3 minutes
- **Balanced depth (with presentation):** 5-7 minutes
- **Comprehensive depth (with presentation):** 8-12 minutes

**Note:** HITL wait times depend on user responsiveness.

---

## For Advanced Usage

### Environment Variables (Gamma Customization)

All Gamma Presentation MCP parameters can be customized via environment variables:

**Theme:**
- `GAMMA_THEME` - Presentation theme (default: "Serviceplan_Light")

**Text Generation:**
- `GAMMA_TEXT_MODE` - "generate" | "preserve" (default: "generate")
- `GAMMA_TEXT_TONE` - Tone of generated text
- `GAMMA_TEXT_AUDIENCE` - Target audience for text
- `GAMMA_TEXT_AMOUNT` - "concise" | "balanced" | "detailed" (default: "detailed")

**Image Generation:**
- `GAMMA_IMAGE_SOURCE` - "aiGenerated" | "web" (default: "aiGenerated")
- `GAMMA_IMAGE_MODEL` - "recraft-v3-svg" | other models (default: "recraft-v3-svg")
- `GAMMA_IMAGE_STYLE` - Visual style for generated images

**Layout:**
- `GAMMA_CARD_DIMENSIONS` - "16x9" | "4x3" (default: "16x9")

**Other:**
- `GAMMA_ADDITIONAL_INSTRUCTIONS` - Free-form guidance for presentation generation
- `GAMMA_DISCLAIMER_CARD` - Markdown content for prepended disclaimer slide

**Digital Ocean Spaces (Optional CDN):**
- `DO_SPACES_ACCESS_KEY` - Access key for DO Spaces
- `DO_SPACES_SECRET_KEY` - Secret key for DO Spaces
- `DO_SPACES_BUCKET` - Bucket name
- `DO_SPACES_REGION` - Region (e.g., "nyc3")
- `DO_SPACES_ENDPOINT` - Full endpoint URL

---

## Notes for Maintainers

### Critical Implementation Priorities

**1. Direct API Calls are THE Critical Path**
- Plugin uses direct Exa Research API calls via Bash/curl
- No MCP server dependencies for research functionality
- API Key embedded in SKILL.md for simplicity
- Polling and retry logic handled in bash scripts

**2. HITL Checkpoints are Non-Negotiable**
- Checkpoint 1 (cost confirmation): REQUIRED before Exa API
- Checkpoint 2 (presentation review): OPTIONAL but valuable for quality
- Don't skip these for user trust

**3. Graceful Degradation is Essential**
- Presentation failure doesn't fail research (core deliverable)
- Cloud CDN failure doesn't fail presentation (Kodosumi URL works)
- Each component can fail independently

**4. Custom Code is Minimal and Simple**
- 3 functions, all use Python stdlib only
- No external dependencies
- Easy to test, easy to maintain

**5. Error Handling is Comprehensive**
- 6 error patterns documented in SKILL.md
- Each pattern has specific user-facing message
- Always provide actionable recommendations

### Common Pitfalls to Avoid

**❌ Don't add Python packages for API integration**
- All API calls go through MCP servers
- MCP servers handle their own dependencies
- Plugin stays lightweight and portable

**❌ Don't skip progress updates**
- Long-running operations (research, presentation) need visibility
- Use emoji indicators (⏳, ✅, ⚠️, 📊)
- Update every 10 seconds during long operations

**❌ Don't hardcode slide counts**
- Use heuristic algorithm (calculate_optimal_slide_count)
- Clamp to 10-30 range (Gamma requirement)
- Allow user adjustment at HITL Checkpoint 2

**❌ Don't block on optional features**
- Presentation generation is optional (user can skip)
- Cloud CDN is optional (graceful degradation)
- Core deliverable is research report (always deliver this)

**❌ Don't forget [TASK_COMPLETE] signal**
- Required for auto-completion
- Placed at end of final response
- Stripped from user-facing output (system handles this)

---

**Version:** 2.5
**Last Updated:** 2025-12-18
**Estimated Size:** 1,800 lines

**Changelog:**
- v2.5 (2025-12-18): **Fix** - Send FULL research report to Langfuse output (not just summary). Uses Python for proper JSON escaping of large reports with special characters.
- v2.4 (2025-12-18): **Fix** - Correctly update trace output using `trace-create` with same trace ID (Langfuse merges/updates when same ID is used). This is the official Langfuse approach per their documentation.
- v2.3 (2025-12-18): **Fix** - Removed invalid `trace-update` API call (not supported by Langfuse). Output is now stored in span-update and generation-update instead.
- v2.2 (2025-12-18): **Breaking change** - Removed helper scripts entirely. All Langfuse API calls are now inline in SKILL.md with step-by-step instructions. Fixed trace-update vs trace-create bug. Synchronous curl calls ensure all traces complete.
- v2.1 (2025-12-18): Replaced hooks-based Langfuse tracing with helper script (reverted in v2.2 due to bugs).
- v2.0 (2025-12-16): **Breaking change** - Replaced MCP tool calls with direct Exa Research API calls via Bash/curl.
- v1.2 (2025-12-12): Implemented automatic Langfuse tracing via Claude Code hooks.
- v1.1 (2025-12-11): Updated Langfuse trace format with structured metadata.
- v1.0 (2025-11-26): Initial release with MCP-based research tools.
