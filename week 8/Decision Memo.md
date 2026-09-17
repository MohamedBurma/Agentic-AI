# COSC726 Lab 7 — Decision Memo

## 1. Baseline versus crew

After running both implementations on B1–B4, compare **coverage** and **grounding** separately. State on which briefs the crew improved, matched, or underperformed the single-agent baseline. A higher score on only one metric is not sufficient evidence of superiority.

| Brief | Baseline coverage | Crew coverage | Baseline grounding | Crew grounding | Decision |
|---|---:|---:|---:|---:|---|
| B1 | [fill from ledger] | [fill from ledger] | [fill from ledger] | [fill from ledger] | [fill] |
| B2 | [fill from ledger] | [fill from ledger] | [fill from ledger] | [fill from ledger] | [fill] |
| B3 | [fill from ledger] | [fill from ledger] | [fill from ledger] | [fill from ledger] | [fill] |
| B4 | [fill from ledger] | [fill from ledger] | [fill from ledger] | [fill from ledger] | [fill] |

## 2. Token ratio

The measured total-token ratio of the crew to the baseline was **[fill]×**. This is [below/within/above] the reported industry range of 3–10×. The extra calls [did/did not] buy improved coverage or grounding consistently.

## 3. Context loss

The intended context-loss point is the **researcher → analyst handoff**. The analyst receives findings only and never receives the original corpus. In B1, losing or omitting `LEG-0455` can remove the legal constraint that the liquidated-damages clause is the sole remedy and that customer credits cannot additionally be recovered. This is an **inter-agent** failure because the problem occurs at a boundary between agents rather than because an individual agent necessarily lied.

## 4. The critic: benefit and cost

The critic adds a verification call and, when it rejects a memo, may cause a bounded writer revision. Record the token and time deltas from the runs with `with_critic=False` and `with_critic=True`:

- Additional tokens: **[fill]**
- Additional seconds: **[fill]**
- Outcome changes: **[fill]**

The critic checks grounding against the findings it receives. It cannot detect evidence that was lost before the critic saw it. Whether this cost is justified is a product decision: it depends on the cost of publishing an unsupported answer.

## 5. Failure classification

| Observation | MAST family | Explanation |
|---|---|---|
| `LEG-0455` is lost at the researcher–analyst boundary | Inter-agent | Required context does not survive the handoff. |
| B2 receives multiple calls for two simple numbers | Specification / design trade-off | The multi-agent decomposition is unnecessary for this brief, so coordination cost exceeds its value. |
| Analyst repeats a one-sided researcher framing in B3 | Inter-agent | The analyst may agree with the framing instead of independently weighing both sides. |
| B4 produces an answer despite no Q3 evidence | Verification | The system fails to verify that the requested fact exists before writing a memo. |
| Critic approves a grounded but one-sided conclusion | Verification limitation | Grounding is checked, but balance and alternative hypotheses are not. |

## 6. What I would ship

For short, sequential, closed-corpus briefs like these, I would ship the **single-agent baseline with deterministic retrieval and explicit citation checks** unless the ledger demonstrates a material quality improvement from the crew. I would add a bounded critic only when the cost of an unsupported answer is high and the critic has access to the right evidence. I would not treat this lab as evidence about parallel workloads, because it does not test parallelism; four briefs with one run each provide no variance estimate; and a 7B model may fail differently from a frontier model.

## Reproducibility

Run the following after creating `lab8_kit.py` from the notebook and starting Ollama with `qwen2.5:7b`:

```bash
python crew.py
```

This writes the measured comparison to `ledger.md`. Replace the placeholders in this memo with the observed values before submission.
