"""COSC726 Lab 7 submission: baseline, sequential crew, and measurement."""
from __future__ import annotations

import json
import re
import time
from pathlib import Path

import lab8_kit as K
from pydantic import ValidationError
from lab8_kit import AgentRun, Brief, CrewTrace, Memo, Message, Research, Analysis, Verdict

CLIENT = K.make_client()
JSON_OBJ = re.compile(r"\{.*\}", re.S)


def call_agent(role_system, user, contract, label, tries=3):
    """Call the configured model and validate its JSON response."""
    run = AgentRun(role=label)
    prompt = user
    started = time.time()
    for attempt in range(tries):
        response = CLIENT.chat.completions.create(
            model=K.MODEL,
            temperature=0,
            max_tokens=800,
            messages=[
                {"role": "system", "content": role_system},
                {"role": "user", "content": prompt},
            ],
        )
        run.tokens += getattr(response.usage, "total_tokens", 0) or 0
        raw = response.choices[0].message.content or ""
        obj = None
        try:
            obj = json.loads(raw)
        except json.JSONDecodeError:
            match = JSON_OBJ.search(raw)
            if match:
                try:
                    obj = json.loads(match.group(0))
                except json.JSONDecodeError:
                    obj = None
        if obj is not None:
            try:
                result = contract.model_validate(obj)
                run.seconds = time.time() - started
                return result, run
            except ValidationError as exc:
                reason = exc.errors()[0]["msg"]
        else:
            reason = "not valid JSON"
        run.retries += 1
        prompt = f"{user}\n\nPrevious response rejected: {reason}. Return ONLY corrected JSON."
    run.ok = False
    run.error = "no valid output"
    run.seconds = time.time() - started
    return None, run


def evidence(brief: Brief, k: int = 4) -> str:
    hits = K.search(brief.question, k=k)
    return "\n".join(f"[{h['doc_id']}] {h['text']}" for h in hits) or "(the search returned nothing)"


def single_agent(brief: Brief) -> CrewTrace:
    """Baseline: one model call with all retrieved evidence."""
    trace = CrewTrace(brief_id=brief.brief_id, topology="single")
    prompt = (
        f"Brief: {brief.question}\n\nEvidence from the closed corpus:\n{evidence(brief)}\n\n"
        "Answer the brief using only this evidence."
    )
    memo, run = call_agent(K.SINGLE_AGENT_SYSTEM, prompt, Memo, "single_agent")
    trace.agents.append(run)
    trace.memo = memo
    trace.stop_reason = "single call"
    return trace


def crew(brief: Brief, with_critic: bool = True, max_revisions: int = 1) -> CrewTrace:
    """Sequential researcher -> analyst -> writer, optionally critic and revision."""
    trace = CrewTrace(brief_id=brief.brief_id,
                      topology="critic" if with_critic else "sequential")
    corpus = evidence(brief)
    research_prompt = f"Brief: {brief.question}\nSearch results:\n{corpus}"
    research, run = call_agent(K.SYSTEMS[K.Role.RESEARCHER], research_prompt, Research, "researcher")
    trace.agents.append(run)
    if research is None:
        trace.stop_reason = "researcher failed"
        return trace

    findings = json.dumps(research.model_dump(), ensure_ascii=False)
    trace.messages.append(Message("researcher", "analyst", findings))
    analysis, run = call_agent(
        K.SYSTEMS[K.Role.ANALYST],
        f"Brief: {brief.question}\nResearch findings only:\n{findings}",
        Analysis, "analyst",
    )
    trace.agents.append(run)
    if analysis is None:
        trace.stop_reason = "analyst failed"
        return trace

    analysis_payload = json.dumps(analysis.model_dump(), ensure_ascii=False)
    trace.messages.append(Message("analyst", "writer", analysis_payload))
    writer_prompt = (
        f"Brief: {brief.question}\nResearch findings:\n{findings}\n"
        f"Analyst conclusion:\n{analysis_payload}"
    )
    memo, run = call_agent(K.SYSTEMS[K.Role.WRITER], writer_prompt, Memo, "writer")
    trace.agents.append(run)
    trace.memo = memo
    if memo is None:
        trace.stop_reason = "writer failed"
        return trace

    if not with_critic:
        trace.stop_reason = "critic disabled"
        return trace

    for revision in range(max(0, max_revisions) + 1):
        memo_payload = json.dumps(memo.model_dump(), ensure_ascii=False)
        trace.messages.append(Message("writer", "critic", memo_payload))
        verdict, run = call_agent(
            K.SYSTEMS[K.Role.CRITIC],
            f"Brief: {brief.question}\nFindings:\n{findings}\nMemo:\n{memo_payload}",
            Verdict, "critic",
        )
        trace.agents.append(run)
        trace.verdict = verdict
        if verdict is None or verdict.approved:
            trace.stop_reason = "critic approved" if verdict else "critic failed"
            return trace
        if revision >= max_revisions:
            trace.stop_reason = "revision limit reached"
            return trace
        feedback = json.dumps(verdict.model_dump(), ensure_ascii=False)
        trace.messages.append(Message("critic", "writer", feedback))
        memo, run = call_agent(
            K.SYSTEMS[K.Role.WRITER],
            f"Brief: {brief.question}\nResearch findings:\n{findings}\n"
            f"Analyst conclusion:\n{analysis_payload}\nCritic feedback:\n{feedback}",
            Memo, "writer_revision",
        )
        trace.agents.append(run)
        trace.memo = memo
        if memo is None:
            trace.stop_reason = "writer revision failed"
            return trace
    trace.stop_reason = "revision limit reached"
    return trace


def measure(briefs=None, with_critic: bool = True, output_path="ledger.md"):
    """Run both implementations on every brief and write the comparison ledger."""
    briefs = list(briefs or K.BRIEFS)
    rows = []
    records = []
    for brief in briefs:
        baseline = single_agent(brief)
        crew_trace = crew(brief, with_critic=with_critic)
        rows.extend([
            ("baseline", baseline, K.score_output(brief, baseline.memo)),
            ("crew", crew_trace, K.score_output(brief, crew_trace.memo)),
        ])
        records.extend([(brief, baseline), (brief, crew_trace)])
    table = K.compare(rows)
    Path(output_path).write_text("# COSC726 Lab 7 Ledger\n\n```text\n" + table + "\n```\n", encoding="utf-8")
    return table, records


if __name__ == "__main__":
    print(measure()[0])
    print("Ledger written to ledger.md")

__all__ = ["single_agent", "crew", "measure", "evidence"]
