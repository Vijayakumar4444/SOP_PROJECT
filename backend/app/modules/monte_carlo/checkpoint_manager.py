from __future__ import annotations

from pathlib import Path
from typing import Any
from datetime import datetime, timezone
import hashlib
import json

from backend.app.modules.data_foundation.io_utils import write_json


class CheckpointManager:
    """Manages atomic simulation checkpointing and resumption."""

    def __init__(self, experiment_dir: Path) -> None:
        self.exp_dir = experiment_dir
        self.checkpoint_dir = experiment_dir / "checkpoints"
        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)
        self.latest_cp_path = self.checkpoint_dir / "latest_checkpoint.json"

    def save_checkpoint(
        self,
        experiment_id: str,
        completed_iterations: list[dict[str, Any]],
        current_iteration_number: int,
        total_requested: int,
        config_hash: str,
    ) -> Path:
        cp_data = {
            "experiment_id": experiment_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "config_hash": config_hash,
            "completed_iteration_count": len([r for r in completed_iterations if r.get("iteration_status") == "COMPLETED"]),
            "failed_iteration_count": len([r for r in completed_iterations if r.get("iteration_status") != "COMPLETED"]),
            "last_iteration_number": current_iteration_number,
            "total_requested_iterations": total_requested,
            "completed_iterations_data": completed_iterations,
        }

        # Atomic write
        write_json(self.latest_cp_path, cp_data)
        return self.latest_cp_path

    def load_latest_checkpoint(self, expected_config_hash: str) -> dict[str, Any] | None:
        if not self.latest_cp_path.exists():
            return None

        cp_data = json.loads(self.latest_cp_path.read_text(encoding="utf-8"))
        saved_hash = cp_data.get("config_hash")

        if saved_hash and saved_hash != expected_config_hash:
            raise ValueError(
                f"Checkpoint configuration hash mismatch. Saved ({saved_hash}) vs Current ({expected_config_hash}). Cannot resume safely."
            )

        return cp_data

    @staticmethod
    def compute_config_hash(raw_config_dict: dict[str, Any]) -> str:
        serialized = json.dumps(raw_config_dict, sort_keys=True)
        return hashlib.sha256(serialized.encode("utf-8")).hexdigest()[:12].upper()
