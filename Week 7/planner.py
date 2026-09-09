"""COSC726 Lab 6 solution: plan -> validate -> execute -> critique -> re-plan."""
from __future__ import annotations
import json
import re
from typing import Any
import lab7_kit as K
from lab7_kit import Critique, Plan, PlanTrace, PlanVersion, StepResult

ORDER_ID_RE = re.compile(r"^A[0-9]{4}$")


def validate_plan(plan: Plan) -> list[str]:
    """Return all pre-execution plan violations."""
    problems: list[str] = []
    prior_tools: set[str] = set()
    for i, step in enumerate(plan.steps, 1):
        if step.tool not in K.TOOLS:
            problems.append(f"step {step.n}: unknown tool '{step.tool}'")
            continue
        spec = K.TOOLS[step.tool]
        missing = [a for a in spec.args if a not in step.args]
        if missing:
            problems.append(f"step {step.n}: missing required argument(s): {', '.join(missing)}")
        if "order_id" in step.args and not ORDER_ID_RE.fullmatch(str(step.args["order_id"])):
            problems.append(f"step {step.n}: invalid order_id '{step.args['order_id']}'")
        if step.tool == "request_approval":
            absent = {"track_order", "get_policy"} - prior_tools
            if absent:
                problems.append(f"step {step.n}: request_approval requires earlier {', '.join(sorted(absent))}")
        prior_tools.add(step.tool)
    return problems


def _result(step, tier, ok, error=None, observation=None):
    return StepResult(step.n, step.tool, step.args, tier.value if tier else None,
                      ok, error, observation or {})


def execute(plan: Plan, allow_consequential: bool = True) -> list[StepResult]:
    """Execute in order; every gate becomes a readable StepResult."""
    results: list[StepResult] = []
    succeeded: set[str] = set()
    evidence: dict[str, Any] = {}
    for step in plan.steps:
        spec = K.TOOLS.get(step.tool)
        if spec is None:
            r = _result(step, None, False, "unknown_tool")
            results.append(r); continue
        if "order_id" in step.args and step.args["order_id"] not in K.KNOWN_IDS:
            r = _result(step, spec.tier, False, "unknown_order")
            results.append(r); continue
        if step.tool == "request_approval":
            if not allow_consequential:
                r = _result(step, spec.tier, False, "consequential_action_not_allowed")
                results.append(r); continue
            if not {"track_order", "get_policy"}.issubset(succeeded):
                r = _result(step, spec.tier, False, "approval_requires_evidence")
                results.append(r); continue
            order = evidence.get("track_order", {})
            policy = evidence.get("get_policy", {})
            if order.get("days_late", 0) < policy.get("threshold_days", K.THRESHOLD_DAYS):
                r = _result(step, spec.tier, False, "below_threshold")
                results.append(r); continue
        try:
            observation = spec.fn(**step.args)
            ok = bool(observation.get("ok", False))
            r = _result(step, spec.tier, ok,
                        None if ok else observation.get("error", "tool_error"), observation)
        except Exception as exc:
            r = _result(step, spec.tier, False, f"tool_exception:{type(exc).__name__}")
        results.append(r)
        if r.ok:
            succeeded.add(step.tool)
            evidence[step.tool] = r.observation
    return results


def _critic(goal, plan, results):
    payload = {
        "goal": goal.text,
        "plan": plan.model_dump(),
        "results": [r.__dict__ for r in results],
    }
    return propose(K.CRITIC_SYSTEM, json.dumps(payload, default=str), Critique)


def propose(system, user, model_cls, tries=3):
    """Use the notebook's existing validate-and-retry seam."""
    # The notebook normally defines this function. This fallback keeps the
    # submitted planner standalone when imported outside the notebook.
    import json as _json
    from pydantic import ValidationError
    client = K.make_client()
    total = 0
    prompt = user
    for _ in range(tries):
        r = client.chat.completions.create(model=K.MODEL, temperature=0, max_tokens=700,
            messages=[{"role":"system", "content": system}, {"role":"user", "content": prompt}])
        total += getattr(r.usage, "total_tokens", 0) or 0
        raw = r.choices[0].message.content or ""
        try:
            obj = _json.loads(raw)
        except _json.JSONDecodeError:
            m = re.search(r"\{.*\}", raw, re.S); obj = _json.loads(m.group(0)) if m else None
        try:
            return model_cls.model_validate(obj), None, total
        except Exception as exc:
            prompt = f"{user}\nReturn ONLY corrected JSON. Previous error: {exc}"
    return None, "model proposal failed", total


def run(goal, max_versions: int = 3, allow_consequential: bool = True):
    trace = PlanTrace(goal_id=goal.goal_id)
    for version in range(1, max_versions + 1):
        plan, why, tokens = propose(K.PLANNER_SYSTEM, f"CUSTOMER MESSAGE:\n{goal.text}", Plan)
        pv = PlanVersion(version=version, plan=plan, tokens=tokens)
        trace.versions.append(pv)
        if plan is None:
            pv.invalid_reason = why
            trace.stop_reason = "planner_failed"
            break
        oscillation = K.detect_oscillation(trace)
        if oscillation:
            trace.stop_reason = "oscillation: " + oscillation
            break
        drift = K.goal_drift(goal, plan)
        if drift:
            trace.stop_reason = "goal_drift: " + ", ".join(drift)
            break
        problems = validate_plan(plan)
        if problems:
            pv.invalid_reason = "; ".join(problems)
            if version == max_versions:
                trace.stop_reason = "invalid_plan_budget_exhausted"
                break
            continue
        pv.results = execute(plan, allow_consequential)
        critique, why, ctok = _critic(goal, plan, pv.results)
        pv.tokens += ctok
        if critique is None:
            trace.stop_reason = "critic_failed"
            break
        pv.critique = critique
        # Human-written goal requirements are authoritative over a critic's
        # optimistic goal_met flag.
        if critique.goal_met and not K.goal_drift(goal, plan):
            trace.stop_reason = "goal_met"; trace.answer = "goal served"; break
        if critique.structural:
            trace.stop_reason = "structural_failure"; break
        if not critique.revise:
            trace.stop_reason = "critic_declined_revision"; break
        if version == max_versions:
            trace.stop_reason = "replan_budget_exhausted"
            break
    if not trace.stop_reason:
        trace.stop_reason = "replan_budget_exhausted"
    return trace


def measure(max_versions: int = 3):
    rows = []
    for goal in K.GOALS:
        t = run(goal, max_versions=max_versions)
        first = next((v for v in t.versions if v.plan), None)
        rows.append({"goal": goal.goal_id,
                     "plan_quality": K.score_plan(goal, first.plan) if first else None,
                     "replans": t.replans, "tokens": t.total_tokens,
                     "stop_reason": t.stop_reason})
    return rows


if __name__ == "__main__":
    for row in measure(): print(row)
