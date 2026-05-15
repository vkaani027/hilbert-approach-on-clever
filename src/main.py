from __future__ import annotations

import argparse
import json
from pathlib import Path
from .pipeline import run_pipeline
from .config import load_config


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('--config', default='configs/default.yaml')
    args = parser.parse_args()
    config = load_config(Path(args.config))
    run_pipeline(config)


if __name__ == '__main__':
    main()
