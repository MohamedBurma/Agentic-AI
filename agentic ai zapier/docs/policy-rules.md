# Policy Rules

## 1. Purpose

The policy rules control which requests can continue through the workflow. They help the prototype avoid incomplete, unsupported, or unsafe actions.

## 2. Supported Request Types

The prototype supports only the following request types:

- `meeting`
- `follow_up_task`
- `record_update`

Any other request type is marked as unsupported and escalated for review.

## 3. Required Fields

### Meeting Request

A meeting request should include:

- Requester
- At least one participant or target group
- Meeting purpose or title
- Date or acceptable date range
- Time or acceptable time range
- Meeting duration

If an important field is missing, the request is sent to `needs_information`.

### Follow-up Task Request

A follow-up task should include:

- Requester
- Task description
- Responsible person or team
- Due date, when required by the request

### Operations Record Update

A record update should include:

- Requester
- Record description or reference
- Information to be added or updated
- Target mock tracker

## 4. Action Allowlist

Only the following mock actions are permitted:

- `create_calendar_event`
- `create_follow_up_task`
- `update_operations_tracker`

The workflow must not select arbitrary actions outside this list.

## 5. Confidence Rule

The AI interpretation includes a confidence value.

- Confidence of `0.75` or higher: the request may continue to policy validation.
- Confidence below `0.75`: the request requires human review.

The confidence value is a routing signal and does not replace human approval.

## 6. Approval Rule

Every mock write operation requires human approval. No calendar row, task row, or tracker row may be created before approval.

Possible approval results are:

- `approved`
- `rejected`
- `needs_clarification`

## 7. Duplicate Rule

Before executing an action, the workflow checks the action key in the execution log.

```text
action_key = request_id + action_type + normalized_target
```

If the key already exists, the action is marked as `duplicate` and is not executed again.

## 8. Error Handling Rules

| Situation | Result |
|---|---|
| Temporary mock timeout | Retry once |
| Missing required field | Request clarification |
| Low AI confidence | Human review |
| Unsupported request type | Escalate |
| Unauthorized action | Escalate |
| Duplicate action | Skip the write |
| Repeated technical failure | Mark as failed and escalate |

## 9. Data Safety Rules

- Use synthetic people, dates, and records.
- Do not connect the prototype to production systems.
- Do not send real messages.
- Do not create real calendar events.
- Do not make financial, legal, or medical decisions.
- Record only the information needed for the academic test.

## 10. Policy Decision Outcomes

Each request must receive one of the following outcomes:

- `continue_to_approval`
- `request_clarification`
- `escalate_for_review`
- `skip_duplicate`
