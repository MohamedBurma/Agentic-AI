#!/usr/bin/env python3
"""
COSC726 - Agentic Artificial Intelligence
Week 2 / Lab 1 - llm_foundations.py  (COMPLETE SOLUTION)

Treat a model interface as an object of measurement. This file uses ONLY the
Python standard library - no API key, no network, no third-party packages.

THREE implemented functions:
    1. count_tokens(text, tokenizer)   - token counting for a teaching tokenizer
    2. prepare_context(...)            - explicit context budgeting
    3. sample_next(distribution, ...)  - a transparent sampler

Run the self-test:
    python COSC726_W02_llm_foundations_SOLUTION.py --self-test
"""

from __future__ import annotations

import argparse
import math
import random
import sys
from dataclasses import dataclass, field

# ─────────────────────────────────────────────────────────────────────────────
# Two deliberately DIFFERENT teaching tokenizers. Neither is authoritative; the
# point is that the same text costs a different number of tokens under each.
# ─────────────────────────────────────────────────────────────────────────────
TOKENIZER_A = {
    "vocab": ["order", "agent", "the", "credit", "policy", "late", "1043",
              "ic", "ing", "ed", " ", "-", "A", "#"],
    "name": "teach-A",
}
TOKENIZER_B = {
    "vocab": ["order", "ag", "ent", "the", "cred", "it", "pol", "icy", "late",
              "10", "43", "ic", "ing", "ed", " ", "-", "A", "#"],
    "name": "teach-B",
}


def _greedy_split(text: str, vocab: list[str]) -> list[str]:
    """Greedy longest-match tokenisation against a vocab; unknown chars stand alone."""
    vocab = sorted(vocab, key=len, reverse=True)
    text, out, i = text.lower(), [], 0
    while i < len(text):
        for v in vocab:
            if v and text.startswith(v.lower(), i):
                out.append(v)
                i += len(v)
                break
        else:
            out.append(text[i])
            i += 1
    return out


# ─────────────────────────────────────────────────────────────────────────────
# TODO 1 — IMPLEMENTED: count_tokens
# ─────────────────────────────────────────────────────────────────────────────
def count_tokens(text: str, tokenizer: dict) -> int:
    """
    Return the NUMBER OF TOKENS `text` produces under `tokenizer`.

    Uses _greedy_split(text, tokenizer["vocab"]) to get the list of token
    strings, then returns how many there are.

    Why this matters: token counts are model-specific. The same text costs
    different amounts under TOKENIZER_A and TOKENIZER_B.
    """
    tokens = _greedy_split(text, tokenizer["vocab"])
    return len(tokens)


# ─────────────────────────────────────────────────────────────────────────────
# Context plan dataclass
# ─────────────────────────────────────────────────────────────────────────────
@dataclass
class ContextPlan:
    kept: list[str] = field(default_factory=list)
    dropped: list[str] = field(default_factory=list)
    rejected: bool = False
    reason: str = ""


# ─────────────────────────────────────────────────────────────────────────────
# TODO 2 — IMPLEMENTED: prepare_context
# ─────────────────────────────────────────────────────────────────────────────
def prepare_context(messages: list[str], context_limit: int, reserved_output: int,
                    tokenizer: dict, strategy: str = "drop_oldest") -> ContextPlan:
    """
    Fit `messages` into an explicit token budget and RECORD what happened.

    The input budget is:  context_limit - reserved_output
    Count each message with count_tokens(msg, tokenizer).

    Two strategies:
      - "reject"      : if the messages do not fit, return a ContextPlan with
                        rejected=True and a clear reason. Do NOT silently trim.
      - "drop_oldest" : keep messages[0] (the system message) always; drop the
                        NEXT-oldest messages one at a time until the rest fit,
                        recording each dropped message in plan.dropped.
    """
    input_budget = context_limit - reserved_output

    # Guard: reserved_output larger than context_limit
    if input_budget < 0:
        return ContextPlan(
            rejected=True,
            reason="Reserved output exceeds context limit"
        )

    # Count tokens for every message
    token_counts = [count_tokens(msg, tokenizer) for msg in messages]
    total_tokens = sum(token_counts)

    # Messages already fit — nothing to do
    if total_tokens <= input_budget:
        return ContextPlan(kept=list(messages))

    # ── reject strategy ──────────────────────────────────────────────────────
    if strategy == "reject":
        return ContextPlan(
            rejected=True,
            reason=(
                f"Context requires {total_tokens} tokens, "
                f"but only {input_budget} input tokens are available"
            )
        )

    # ── drop_oldest strategy ─────────────────────────────────────────────────
    if strategy == "drop_oldest":
        kept = list(messages)
        dropped = []

        # Drop from index 1 upward; messages[0] (system prompt) is always kept
        while len(kept) > 1:
            current_tokens = sum(count_tokens(msg, tokenizer) for msg in kept)
            if current_tokens <= input_budget:
                break
            dropped.append(kept.pop(1))

        # Edge case: even the system message alone is too large
        current_tokens = sum(count_tokens(msg, tokenizer) for msg in kept)
        if current_tokens > input_budget:
            return ContextPlan(
                kept=[],
                dropped=dropped,
                rejected=True,
                reason="System message alone exceeds the available input context budget"
            )

        return ContextPlan(kept=kept, dropped=dropped)

    # Unknown strategy
    return ContextPlan(
        rejected=True,
        reason=f"Unknown context strategy: {strategy}"
    )


# ─────────────────────────────────────────────────────────────────────────────
# TODO 3 — IMPLEMENTED: sample_next
# ─────────────────────────────────────────────────────────────────────────────
def sample_next(distribution: dict[str, float], temperature: float,
                rng: random.Random) -> str:
    """
    Return ONE token sampled from `distribution` (token -> probability).

    Rules:
      - temperature <= 0 : greedy / argmax — return the highest-probability token
                           (break ties by choosing the alphabetically first).
      - temperature  > 0 : rescale by temperature, softmax-normalise, then sample
                           using rng (use rng.random() and a cumulative walk).

    Temperature changes DIVERSITY, not truth.
    """
    if not distribution:
        raise ValueError("distribution must not be empty")

    # ── greedy / argmax ───────────────────────────────────────────────────────
    if temperature <= 0:
        # Sort by (-probability, token_name) for stable alphabetical tie-breaking
        return sorted(
            distribution.items(),
            key=lambda item: (-item[1], item[0])
        )[0][0]

    # ── temperature-scaled sampling ───────────────────────────────────────────
    if any(prob < 0 for prob in distribution.values()):
        raise ValueError("probabilities must be non-negative")

    if sum(distribution.values()) <= 0:
        raise ValueError("distribution must have positive total probability")

    # Convert probabilities to log-space, then scale by temperature
    logits = {
        token: math.log(prob) if prob > 0 else float("-inf")
        for token, prob in distribution.items()
    }

    scaled = {
        token: logit / temperature
        for token, logit in logits.items()
    }

    # Numerically stable softmax: subtract max before exp
    max_scaled = max(v for v in scaled.values() if v != float("-inf"))
    weights = {
        token: math.exp(value - max_scaled)
        for token, value in scaled.items()
        if value != float("-inf")
    }

    total = sum(weights.values())

    # Cumulative walk to sample
    r = rng.random()
    cumulative = 0.0
    for token in sorted(weights):
        cumulative += weights[token] / total
        if r < cumulative:
            return token

    # Floating-point safety fallback
    return sorted(weights)[-1]


# ─────────────────────────────────────────────────────────────────────────────
# Self-test harness (provided - do not edit). Run with --self-test.
# ─────────────────────────────────────────────────────────────────────────────
def _run_self_test() -> int:
    failures = []

    # 1 - token counting differs across tokenizers
    try:
        a = count_tokens("order A-1043", TOKENIZER_A)
        b = count_tokens("order A-1043", TOKENIZER_B)
        assert isinstance(a, int) and isinstance(b, int), "counts must be ints"
        assert a > 0 and b > 0, "counts must be positive"
    except Exception as e:  # noqa: BLE001
        failures.append(f"count_tokens: {e}")

    # 2 - context budgeting: reject vs drop_oldest
    try:
        msgs = ["system rules", "turn one", "turn two", "turn three about the credit"]
        rej = prepare_context(msgs, context_limit=8, reserved_output=4,
                              tokenizer=TOKENIZER_A, strategy="reject")
        assert rej.rejected is True and rej.reason, "reject must set rejected + reason"
        drop = prepare_context(msgs, context_limit=40, reserved_output=4,
                               tokenizer=TOKENIZER_A, strategy="drop_oldest")
        assert drop.kept and drop.kept[0] == "system rules", "system message must be kept"
    except Exception as e:  # noqa: BLE001
        failures.append(f"prepare_context: {e}")

    # 3 - sampler: greedy is deterministic; argmax picks the mode
    try:
        dist = {"Paris": 0.82, "London": 0.11, "Lyon": 0.05, "Rome": 0.02}
        picks = {sample_next(dist, 0.0, random.Random(s)) for s in range(5)}
        assert picks == {"Paris"}, "temperature 0 must always return the mode"
        hot = sample_next(dist, 1.0, random.Random(1))
        assert hot in dist, "temperature>0 must return a token from the distribution"
    except Exception as e:  # noqa: BLE001
        failures.append(f"sample_next: {e}")

    if failures:
        print("SELF-TEST FAILURES:")
        for f in failures:
            print("  -", f)
        return 1
    print("ALL SELF-TESTS PASSED")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="COSC726 Week 2 lab - LLM foundations")
    parser.add_argument("--self-test", action="store_true", help="run the self-test suite")
    args = parser.parse_args(argv)
    if args.self_test:
        return _run_self_test()
    print("Nothing to run. Use --self-test to verify the implementation.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
