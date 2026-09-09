# COSC726 Lab 6 — Decision Memo

## 1. What planning bought over ReAct

The plan is a typed artefact that exists before any action runs. `validate_plan` catches an unknown tool, missing required arguments, malformed order identifiers, and a `request_approval` step placed before both evidence-gathering steps. In a ReAct loop, the corresponding errors would be discovered only after an action was selected: a hallucinated tool would fail at execution time, malformed arguments would reach a tool boundary, and an approval could be attempted before evidence existed. The plan checkpoint therefore prevents unsafe or meaningless calls before side effects.

## 2. What it cost

Planning adds at least one planner call before execution, and reflection adds a critic call after execution. Re-planning adds another planner/critic pair. The notebook's `measure()` table records the actual token totals for the selected model, together with the number of re-plans and stop reasons. The experiment should be reported with those observed values rather than with a model-independent estimate. Adaptivity is also constrained: every new version must pass validation, drift detection, and the oscillation detector.

## 3. Where reflection helped, and where it did not

Reflection can help when the output exposes a diagnosable omission or wrong argument. A revised plan may add a missing evidence step, separate delivery from billing, or restore a dropped requirement. It cannot repair a structural limitation. For G4, the requested order does not exist and no refund tool exists; rewriting the plan cannot make either fact false. The correct response is to stop and escalate to a human, not to spend the remaining re-plan budget.

## 4. What detectors catch that the critic may miss

`goal_drift()` compares every plan against the original, human-authored requirements. A critic may accept a locally plausible revision that solves one part while silently dropping another, especially the address requirement in G1. The detector makes this loss explicit and prevents an optimistic `goal_met` field from overriding a missing original requirement.

## 5. Where the agent still trusts something it should not

The loop still relies on model-generated plans and critiques, even though both are constrained by Pydantic schemas. A syntactically valid plan can still be semantically poor, and a critic can still be overconfident. The deterministic gates, goal requirements, tool allow-list, and consequential-action policy are therefore more trustworthy than free-form model judgment.

## 6. What this lab did not tell us

The experiment uses four goals written by one person, one model configuration, and one run per goal. It provides no variance estimate, no comparison across models or temperatures, and no statistically meaningful benchmark against ReAct. The critic is also the same model family as the planner, so it is not an independent evaluator. Finally, the toy tool world does not measure latency, real user satisfaction, or production-scale failure rates.
