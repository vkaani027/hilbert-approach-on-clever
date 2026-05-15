# my_method

`my_method` is a Lean proof-search pipeline for CLEVER-derived benchmark data.
It uses one informal model for planning, one formal prover model for Lean proofs, and one formalizer model for lemma conversion.

## What it does

- reads benchmark files in `.jsonl` or `.json`
- verifies Lean proofs with `lake env lean`
- retries proof generation after verifier errors
- optionally decomposes hard goals into lemmas
- saves proofs, traces, logs, and summary results

## Quick start

1. Create and activate a conda environment:

```bash
conda create -n my_method python=3.10 -y
conda activate my_method
```

2. Install Python dependencies:

```bash
cd my_method
pip install -e .
```

3. Make sure Lean 4.24 is available on the server:

```bash
source "$HOME/.elan/env"
elan default 4.24.0
lake env lean --version
```

4. Edit `configs/default.yaml`:
- set `data.input_path` to a `converted_proofs*.jsonl` or `.json` file
- set the output directories if you want to store results elsewhere
- set the three model endpoints and model names
- adjust retry counts or worker count if needed

5. Run the pipeline:

```bash
python -m src.main --config configs/default.yaml
```

## Input

The input is a Lean benchmark file converted from `copra_generated_proofs_full` and then processed into `converted_proofs*.json` or `converted_proofs*.jsonl`.
Each record should contain at least:
- `name`
- `header`
- `formal_statement`
- `informal_prefix`
- `split`

## Output

The pipeline writes:
- `results/results.jsonl` — per-theorem status and runtime
- `results/metrics_summary.json` — aggregate summary
- `proofs/*.lean` — successful proof files
- `traces/events.jsonl` — progress logs
- `traces/<name>.json` — run trace for each theorem
- `traces/<name>_lemma_tree.json` — theorem-to-lemma tree
- `traces/<lemma>.json` — lemma formalization traces

## Configuration highlights

- `formalizer_llm` is used only for natural-language lemmas after decomposition.
- `formal_llm` proves Lean statements.
- `informal_llm` decides whether to continue, stop, or decompose.
- `runtime.show_progress` controls whether timestamps are printed to the terminal.

## Notes

- The project expects Lean 4.24-compatible tooling.
- The local prover model is expected to be served through an OpenAI-compatible endpoint.
- The informal model endpoint should also be OpenAI-compatible.
- All prompt and retry limits are editable in `configs/default.yaml`.

## Attribution

This project is an original implementation informed by `clever-prover`, `Goedel-Prover-V2-8B`, `Goedel-Formalizer-V2-8B`, `ml-hilbert`, and `Prover-Agent`.
See `CITATION_AND_ATTRIBUTION.md`.
\n\n## Decision rule\n\nThe Informal model is queried once after repeated proof failures. It must choose exactly one of three labels on the first line: CONTINUE, DECOMPOSE, or IMPOSSIBLE. If the final Formal model output cannot be parsed, the raw output is saved in the trace files so you can inspect the parsing strategy.
\n\n## Informal decision\n\nAfter repeated proof failures, the Informal model is queried once and must choose exactly one label on the first line: CONTINUE, DECOMPOSE, or IMPOSSIBLE. CONTINUE means keep trying without regenerating the proof plan. DECOMPOSE means split into lemmas. IMPOSSIBLE means stop the theorem attempt.
\n\n## Lemma workflow\n\nWhen the Informal model chooses DECOMPOSE, it must provide a numbered list of natural-language lemmas. The pipeline then formalizes those lemmas, proves each lemma recursively, and uses the proven lemmas in order before finishing the original theorem. This keeps the lemma chain in the same order as the final proof structure.
\n\n## Proof skeleton\n\nAfter lemmas are decomposed and formalized, the pipeline builds a proof skeleton that places the lemmas in order before the final theorem statement. The formal prover then works on this assembled structure so the final proof reflects the same lemma order used during decomposition.
\n\n## Skeleton order\n\nWhen the pipeline decomposes a theorem, it first writes the lemmas as sorry-filled theorem blocks in front of the final theorem. The Formal model then fills the proof for the lowest theorem in the current skeleton, and the same process is applied recursively to each lemma.
\n\n## Named lemmas\n\nLemma blocks are given explicit names in the skeleton so later stages can reference them in order. The final theorem is always the bottom-most theorem in the current skeleton, and recursive lemma proofs keep the same naming scheme.
\n\n## Skeleton-first lemma workflow\n\nWhen decomposition is chosen, the pipeline first writes a proof skeleton with sorry placeholders for the lemmas and the final theorem. Only after that does it start proving lemmas recursively. This avoids spending time proving lemmas before the main theorem structure is fixed. Lemmas are required to be self-contained: later lemmas may depend on earlier facts only if they restate the full intermediate proposition, not just its conclusion.
\n\n## Ordering\n\nThe pipeline now builds the main theorem skeleton first, with lemma placeholders already in place. Only after that does it recursively prove the lemmas. This matches the intended order: fix the final structure first, then spend time proving subgoals.
\n\n## Formal target\n\nWhen a proof skeleton already contains lemmas above the final theorem, the Formal model is instructed to fill only the bottom-most theorem in the current skeleton. The preceding lemmas are treated as already established and are not to be rewritten.
