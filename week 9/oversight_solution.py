"""COSC726 Week 9 solution: human-oversight gate and calibration."""
from __future__ import annotations
import json, re
from lab9_kit import Action, AuditEntry, Decision, Explanation, RunResult, Tier
import lab9_kit as K

client = K.make_client()
JSON_OBJ = re.compile(r"\{.*\}", re.S)


def needs_approval(action: Action) -> bool:
    spec = K.TOOLS.get(action.tool)
    return spec is not None and spec.tier == Tier.CONSEQUENTIAL


def explain(action: Action) -> Explanation:
    f = action.facts or {}
    if action.tool == "issue_refund":
        days = f.get("days_late", "unknown")
        threshold = getattr(K, "THRESHOLD_DAYS", 3)
        value = float(f.get("value", 0) or 0)
        percent = getattr(K, "CREDIT_PERCENT", 10)
        expected = round(value * percent / 100, 2)
        amount = float(action.args.get("amount", 0) or 0)
        eligible = bool(f.get("eligible", days != "unknown" and days >= threshold))
        headline = (f"About to refund £{amount:.2f} on {action.args.get('order_id', '')} — "
                    f"{'eligible' if eligible else 'NOT eligible'}")
        because = [
            f"{days} working day(s) late (threshold: {threshold}).",
            f"Order value: £{value:.2f}; policy amount ({percent}%): £{expected:.2f}.",
            f"Agent actually proposed: £{amount:.2f}.",
        ]
        return Explanation(headline, because, f"refunds £{amount:.2f}", False)
    return Explanation(f"About to run {action.tool}",
                        [action.rationale or "No rationale supplied."],
                        action.tool, K.TOOLS[action.tool].tier != Tier.CONSEQUENTIAL)


def execute(action: Action) -> str:
    spec = K.TOOLS.get(action.tool)
    if spec is None:
        return "unknown_tool"
    try:
        return json.dumps(spec.fn(**{k: v for k, v in action.args.items() if k in spec.args}))
    except TypeError as exc:
        return f"bad_args: {exc}"


def gate(action, human, reviewer_name, audit):
    spec = K.TOOLS.get(action.tool)
    if spec is None:
        result = "unknown_tool"
        audit.append(AuditEntry(action.tool, dict(action.args), "unknown", False, False,
                                reviewer_name, "unknown tool", None, result))
        return result
    if not needs_approval(action):
        result = execute(action)
        audit.append(AuditEntry(action.tool, dict(action.args), spec.tier.value, False, True,
                                reviewer_name, "auto-run: non-consequential", None, result))
        return result
    ex = explain(action)
    decision = human(action, ex)
    final = Action(action.tool, dict(action.args), action.rationale, dict(action.facts))
    if decision.approved and decision.edited_args:
        final.args.update(decision.edited_args)
    result = execute(final) if decision.approved else "aborted: human refused"
    audit.append(AuditEntry(final.tool, dict(final.args), spec.tier.value, True,
                            bool(decision.approved), reviewer_name, decision.reason,
                            ex.__dict__, result))
    return result


def propose_action(message: str, facts: dict, tries: int = 3):
    user = f"CUSTOMER MESSAGE:\n{message}\n\nWHAT YOU KNOW:\n{json.dumps(facts, indent=1)}\n\nYour next action:"
    prompt, total = user, 0
    for _ in range(tries):
        r = client.chat.completions.create(model=K.MODEL, temperature=0, max_tokens=300,
            messages=[{"role":"system","content":K.AGENT_SYSTEM},{"role":"user","content":prompt}])
        total += r.usage.total_tokens
        raw = r.choices[0].message.content or ""
        try: obj = json.loads(raw)
        except json.JSONDecodeError:
            m = JSON_OBJ.search(raw)
            try: obj = json.loads(m.group(0)) if m else None
            except json.JSONDecodeError: obj = None
        if isinstance(obj, dict) and obj.get("tool") in K.TOOLS:
            return Action(obj["tool"], obj.get("args", {}), obj.get("rationale", ""), facts), total
        prompt = user + "\nReturn ONLY a valid JSON object with a tool from the allowed list."
    return None, total


def run(scenario, human, reviewer_name) -> RunResult:
    K.reset_world()
    row = K.ORDERS.get(scenario.order_id, {})
    facts = dict(row, order_id=scenario.order_id, threshold_days=K.THRESHOLD_DAYS)
    facts["eligible"] = row.get("days_late", 0) >= K.THRESHOLD_DAYS
    action, tokens = propose_action(scenario.message, facts)
    result = RunResult(scenario.scenario_id, reviewer_name, action=action, tokens=tokens)
    if action is None:
        result.answer = "agent failed to propose an action"
        return result
    result.audit = []
    result.answer = gate(action, human, reviewer_name, result.audit)
    result.executed = any(e.approved and 'account_changed": true' in e.result.lower() for e in result.audit)
    return result


def calibration_table():
    header = f"{'reviewer':<14}{'harm':>6}{'friction':>10}{'accuracy':>10}{'alerts':>9}"
    lines = [header, '-' * len(header)]
    details = {}
    for name, reviewer in K.REVIEWERS.items():
        results = [run(s, reviewer, name) for s in K.SCENARIOS]
        cal, alerts = K.calibration(results, K.SCENARIOS), K.alert_rate(results)
        details[name] = results
        lines.append(f"{name:<14}{cal['harm']:>6}{cal['friction']:>10}{cal['accuracy']:>9.0%}{alerts:>9.0%}")
    return "\n".join(lines), details

if __name__ == "__main__":
    print(calibration_table()[0])
