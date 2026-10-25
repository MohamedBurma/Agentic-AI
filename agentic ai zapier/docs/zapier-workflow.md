# Zapier Workflow Implementation

## 1. Purpose

This document describes the prototype workflow implemented with Zapier and AI by Zapier. The workflow processes synthetic operations requests and prepares controlled actions in mock systems.

## 2. Workflow Trigger

The workflow starts when a synthetic request is received through a webhook or a test form.

### Trigger Data

The trigger should provide:

- `request_id`
- `requester`
- `request_text`

Example:

```json
{
  "request_id": "REQ-001",
  "requester": "student_01",
  "request_text": "Please arrange a 30-minute project review with Lina next Tuesday at 2 PM."
}
```

## 3. Zap Steps

### Step 1: Trigger

Application: `Webhooks by Zapier` or a test form.

Purpose: Receive one synthetic request and start the workflow.

### Step 2: AI Interpretation

Application: `AI by Zapier`.

Purpose: Classify the request and extract structured fields using the prompt in `prompts/ai-extraction-prompt.md`.

Expected output fields:

- Request type
- Confidence
- Entities
- Requested actions
- Missing information
- Policy flags
- Recommended next step

### Step 3: Policy Routing

Application: `Paths by Zapier` or `Filter by Zapier`.

The workflow uses the following routes:

- Valid request: continue to duplicate check and approval.
- Missing information: stop and request clarification.
- Unsupported action: escalate for review.
- Low confidence: send to human review.

### Step 4: Duplicate Check

The workflow creates an action key using the request ID, action type, and normalized target.

Example:

```text
REQ-001_create_calendar_event_lina
```

The workflow searches the execution log for this key.

- Existing key: mark the request as `duplicate` and skip the write.
- New key: continue to approval.

### Step 5: Human Approval

The proposed action is reviewed before any mock table is updated.

The approval information should include:

- Original request
- Extracted fields
- Proposed action
- Policy result
- Action key

Possible results:

- `approved`
- `rejected`
- `needs_clarification`

### Step 6: Mock Action

After approval, the workflow writes to one of the mock systems:

- `mock-calendar.csv` or its corresponding test table.
- `mock-tasks.csv` or its corresponding test table.
- `operations-tracker.csv` or its corresponding test table.

### Step 7: Execution Log

The final step records the result, including the request ID, action key, approval status, tool response, and final state.

## 4. Workflow States

```text
received → interpreted → awaiting_approval → approved → executed
```

Alternative paths:

```text
interpreted → needs_information
interpreted → escalated
interpreted → duplicate
approved → failed → escalated
```

## 5. Safety Controls

- All test data is synthetic.
- Mock systems are used instead of production applications.
- Approval is required before every simulated write.
- Only actions in the project allowlist are permitted.
- Duplicate action keys prevent repeated writes.
- The workflow does not send real messages or create real appointments.

## 6. Implementation Evidence

The final project documentation should include screenshots of:

1. The trigger configuration.
2. The AI by Zapier step.
3. The policy routing step.
4. The approval step.
5. The mock action step.
6. The execution log after a test run.

Screenshots should be added after the Zap is configured and tested.
