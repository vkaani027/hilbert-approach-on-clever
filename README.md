# my_method

`my_method` is a staged Lean proof-search pipeline for CLEVER-derived benchmark data.

## Workflow

1. Informal LLM writes a proof plan only, with no Lean code.
2. Formal LLM attempts a Lean proof.
3. Lean verifier returns compile errors when proof fails.
4. Formal LLM retries with error feedback.
5. After repeated failure, Informal LLM decides whether to continue, fail, or decompose into lemmas.
6. Successful proofs are saved to `proofs/`, while results and traces are saved under `results/` and `traces/`.

## Configuration

All runtime settings live in `configs/default.yaml`:
- dataset input path and output directories
- local formal LLM endpoint and remote informal LLM endpoint
- retry / loop / lemma limits
- worker count
- prompt templates
- Lean verifier command

## Lean version

The benchmark source was generated with Lean 4.24. If the server toolchain differs, switch with:

```bash
source "$HOME/.elan/env"
elan default 4.24.0
# or
elan override set 4.24.0
```

Verification uses:

```bash
lake env lean <file.lean>
```

## Input and output

Input supports `.jsonl` and `.json` files derived from `converted_proofs*.json/jsonl`.

Outputs:
- `results/results.jsonl`: per-theorem status and timing
- `results/metrics_summary.json`: aggregate summary
- `proofs/*.lean`: successful proof files
- `traces/*.json`: prompts, verifier errors, and intermediate decisions

## Environment

Suggested Python dependencies are listed in `pyproject.toml`.
The server also needs:
- Lean / Lake installed via `elan`
- a vLLM OpenAI-compatible endpoint for `Goedel-Prover-V2-8B`
- access to the remote OpenAI-compatible informal model endpoint

## Academic integrity

This project is an original implementation for a thesis workflow. It borrows ideas from:
- `clever-prover`
- `Goedel-Prover-V2-8B`
- `ml-hilbert`
- `Prover-Agent`

These are reference inspirations, not copied implementation. See `CITATION_AND_ATTRIBUTION.md` for the attribution record.
