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
