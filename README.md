# my_method

`my_method` is a Lean proof-search pipeline for the CLEVER-derived benchmark.
It uses three models:
- an informal model for deciding what to do next
- a formal prover model for Lean proofs
- a formalizer model for turning natural-language lemmas into Lean statements

## What you need

- A Linux server with CUDA
- Lean 4.24 and `lake`
- Python 3.10+
- Access to the model endpoints configured in `configs/default.yaml`

## Quick start

1. Create a conda environment:

```bash
conda create -n my_method python=3.10 -y
conda activate my_method
```

2. Install the project:

```bash
cd my_method
pip install -e .
```

3. Make sure Lean works:

```bash
source "$HOME/.elan/env"
elan default 4.24.0
lake env lean --version
```

4. Edit `configs/default.yaml`:
- set `data.input_path` to your `converted_proofs*.jsonl` or `.json` file
- set the model endpoints and model names
- adjust `data.workers` or retry counts if needed

5. Run the pipeline:

```bash
python -m src.main --config configs/default.yaml
```

## Input

The input is the converted CLEVER proof dataset.
Each record should at least contain:
- `name`
- `header`
- `formal_statement`
- `informal_prefix`
- `split`

## Output

The pipeline writes results, proofs, and traces to the directories configured in `configs/default.yaml`.

## Notes

- The project expects Lean 4.24-compatible tooling.
- The local prover model should be served through an OpenAI-compatible endpoint.
- The informal model endpoint should also be OpenAI-compatible.
- You can change retry counts, worker count, and paths in the config file.

## Attribution

This project is an original implementation informed by `clever-prover`, `Goedel-Prover-V2-8B`, `Goedel-Formalizer-V2-8B`, `ml-hilbert`, and `Prover-Agent`.
See `CITATION_AND_ATTRIBUTION.md`.
