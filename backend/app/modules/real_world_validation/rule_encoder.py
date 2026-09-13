"""
Rule encoder parsing formal government order YAML definitions into Policy Engine configurations.
"""

import os
import yaml
from typing import Dict, Any

class RuleEncoder:
    """Encodes official policy rules into executable Phase 6 Policy Engine configuration files."""

    @staticmethod
    def parse_official_rules(yaml_path: str) -> Dict[str, Any]:
        if not os.path.exists(yaml_path):
            raise FileNotFoundError(f"Official policy rules file not found: {yaml_path}")

        with open(yaml_path, "r", encoding="utf-8") as f:
            raw = yaml.safe_load(f)

        return raw
