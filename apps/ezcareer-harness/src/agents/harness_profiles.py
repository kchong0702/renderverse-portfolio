from functools import cache
from pathlib import Path

import yaml
from deepagents import HarnessProfileConfig, register_harness_profile


@cache
def register_harness_profiles(path: Path) -> None:
    """Registers each model's harness profile in path, keyed by provider or
    provider:model, once per process"""
    for key, profile in yaml.safe_load(path.read_text()).items():
        register_harness_profile(key, HarnessProfileConfig.from_dict(profile))
