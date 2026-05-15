# my_method

`my_method` is a Lean proof-search pipeline for CLEVER-derived benchmark data.
It uses two LLMs and a Lean verifier to repeatedly try, debug, and split proof tasks.

## What this project does

Given a dataset of Lean theorems, the system:
- reads the input files
- asks an informal LLM for a proof plan
- asks a formal LLM to generate Lean proof code
- checks the code with Lean
- feeds verifier errors back into the next attempt
- optionally decomposes hard goals into lemmas
- saves successful proofs and run logs to disk

## What you need before running

You do not need to understand AI tooling deeply, but you do need:
- a Linux server with CUDA and 8 GPUs
- a working Lean 4.24-compatible environment on that server
- access to two OpenAI-compatible LLM endpoints
- Python 3.10 or newer

This repository does **not** download or provide the two LLMs automatically.
You will configure their URLs and model names in `configs/default.yaml`.

## Project layout

- `configs/default.yaml` — all runtime settings
- `src/` — Python source code
- `proofs/` — successful Lean proof files
- `results/` — JSON/JSONL result summaries
- `traces/` — prompts, verifier errors, and intermediate decisions

## Quick start

### 1. Create a conda environment

```bash
conda create -n my_method python=3.10 -y
conda activate my_method
```

### 2. Install the Python package

From inside `my_method/`:

```bash
pip install -e .
```

If editable install does not work, install the dependencies directly:

```bash
pip install pyyaml pydantic httpx openai tenacity tqdm
```

### 3. Prepare Lean

The CLEVER-derived benchmark was built with Lean 4.24.
If your machine has a different Lean version, switch it with `elan`:

```bash
source "$HOME/.elan/env"
elan default 4.24.0
```

If you need the project to always use this version, run:

```bash
elan override set 4.24.0
```

### 4. Verify Lean works

From a Lean project directory, confirm the verifier command works:

```bash
lake env lean --version
```

The pipeline uses the same command to verify each proof file.

### 5. Edit the config

Open `configs/default.yaml` and set:
- `data.input_path` to your `converted_proofs*.jsonl` or `.json` file
- `data.output_dir`, `data.proofs_dir`, `data.traces_dir`
- `formal_llm.base_url`, `formal_llm.api_key`, `formal_llm.model`
- `informal_llm.base_url`, `informal_llm.api_key`, `informal_llm.model`
- retry and worker settings as needed

### 6. Run the pipeline

```bash
python -m src.main --config configs/default.yaml
```

## Input format

The pipeline accepts either JSONL or JSON.
Use the files produced from `converted_proofs*.json` and `converted_proofs*.jsonl`.

Each item should represent one theorem and should contain at least:

- `name`: theorem identifier
- `header`: Lean imports and shared setup
- `formal_statement`: theorem statement and proof body start
- `informal_prefix`: natural-language problem description
- `split`: dataset split label, if available

Example JSONL record:

```json
{"name":"example_theorem","header":"import Mathlib\n\nset_option maxHeartbeats 0\n","formal_statement":"theorem example : True := by","informal_prefix":"Prove that the theorem is true.","split":"test"}
```

If you use a JSON file, it may either contain a single object or an array of such objects.

## Output format

The pipeline writes:
- `results/results.jsonl` — one line per theorem, including status and elapsed time
- `results/metrics_summary.json` — aggregate success summary
- `proofs/<name>.lean` — successful proof files
- `traces/<name>.json` — prompts, verifier output, and retry decisions
- `traces/events.jsonl` — timestamped progress log
- `traces/<name>_lemma_tree.json` — lemma-tree expansion for each theorem

## Lean verifier

The project verifies proofs with:

```bash
lake env lean <file.lean>
```

This means your Lean project must already be set up so that `lake env lean` can compile the generated file.

## Configuration notes\n\n- The informal model name sent to `http://yunwu.ai/v1` should not include provider prefixes.\n- The formal model is expected to be served locally from `Goedel-LM/` through a vLLM OpenAI-compatible endpoint.\n- Increase `data.workers` to use more parallel proof attempts.\n- Increase retry limits only if you have enough model budget.\n- Set `runtime.show_progress` to `true` to print timestamped progress messages while the pipeline runs.\n- Set `runtime.save_lemma_tree` to `true` to save theorem-to-lemma expansion trees.\n\n## Academic integrity

This is an original thesis implementation.
It is informed by the design ideas of:
- `clever-prover`
- `Goedel-Prover-V2-8B`
- `ml-hilbert`
- `Prover-Agent`

See `CITATION_AND_ATTRIBUTION.md` for attribution guidance.


