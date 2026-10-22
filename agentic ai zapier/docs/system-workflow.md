# System Workflow

## 1. Overview

The system follows a controlled workflow for processing synthetic operational requests. The workflow combines natural-language interpretation, policy validation, human approval, mock actions, and execution logging.

## 2. Main Workflow

```text
Incoming Request
        ↓
AI Interpretation
        ↓
Structured JSON
        ↓
Policy Validation
        ↓
Missing Information Check
        ↓
Duplicate Check
        ↓
Human Approval
        ↓
Mock Application Action
        ↓
Execution Trace
        ↓
Final State
```

## 3. Workflow Steps

### Step 1: Receive the Request

A synthetic request is submitted through a Webhook, form, or test table. Each request contains a unique `request_id` and the original request text.

### Step 2: Interpret the Request

AI by Zapier analyzes the request and extracts the request type, entities, requested actions, confidence level, and missing information.

### Step 3: Validate the Request

The extracted information is checked against the project policy. Unsupported actions, missing required fields, and low-confidence interpretations are not sent directly to execution.

### Step 4: Check for Missing Information

If important information is missing, the request is moved to the `needs_information` state. The system does not invent missing details.

### Step 5: Check for Duplicate Actions

The system creates an action key using the request identifier, action type, and target data. If the action key already exists in the execution log, the action is marked as `duplicate` and is skipped.

### Step 6: Request Human Approval

Before a mock application is updated, the system presents the original request, extracted information, proposed action, and policy result for human approval.

### Step 7: Execute a Mock Action

After approval, the workflow writes to a mock calendar, mock task list, or mock operations tracker.

### Step 8: Record the Result

The workflow records the action, approval result, tool response, retry count, and final state in an execution trace.

## 4. Request States

- `received`: The request was received.
- `interpreted`: The request was analyzed by the AI step.
- `needs_information`: Required information is missing.
- `awaiting_approval`: The request is waiting for human approval.
- `approved`: Human approval was provided.
- `executed`: The mock action completed successfully.
- `failed`: The action failed after the allowed attempts.
- `duplicate`: The action was already performed.
- `escalated`: The request requires human review or is not supported.

## 5. Stopping Rules

The workflow stops when:

- All approved mock actions are completed.
- Required information is missing.
- A duplicate action is detected.
- The request is unsupported or unauthorized.
- The maximum retry limit is reached.

## 6. Technology Mapping

| Workflow Function | Proposed Technology |
|---|---|
| Request trigger | Webhooks by Zapier or Google Forms |
| AI interpretation | AI by Zapier |
| Conditions and routing | Filter by Zapier and Paths by Zapier |
| Mock storage | Zapier Tables or Google Sheets |
| Optional data processing | Code by Zapier |
| Execution trace | Operations log table |
