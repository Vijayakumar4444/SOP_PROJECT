from __future__ import annotations

import subprocess
import time
import os
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from backend.app.policy_memory import PolicyMemoryStore
from backend.app.policy_priors import write_policy_memory_priors


ROOT = Path(__file__).resolve().parents[2]


@dataclass(frozen=True)
class PipelinePhase:
    name: str
    command: tuple[str, ...]
    primary_artifact: str | None = None


NPM = "npm.cmd" if os.name == "nt" else "npm"


FULL_PIPELINE_PHASES: tuple[PipelinePhase, ...] = (
    PipelinePhase("phase1_data_foundation", (NPM, "run", "phase1:build"), "data/processed/reference_template.csv"),
    PipelinePhase("phase2_compatibility", (NPM, "run", "phase2:build"), "data/synthetic/variable_selection.json"),
    PipelinePhase("phase3_synthetic_population", (NPM, "run", "phase3:finalize"), "data/synthetic/phase4_validation_manifest.json"),
    PipelinePhase("phase4_population_validation", (NPM, "run", "phase4:validate"), "data/synthetic/phase5_calibration_handoff.json"),
    PipelinePhase("phase5_calibration", (NPM, "run", "phase5:calibrate"), "data/synthetic/phase6_policy_engine_handoff.json"),
    PipelinePhase("phase6_policy_engine", (NPM, "run", "phase6:execute"), "data/synthetic/phase7_monte_carlo_handoff.json"),
    PipelinePhase("phase7_monte_carlo", (NPM, "run", "phase7:simulate"), "data/synthetic/phase8_recommendation_handoff.json"),
    PipelinePhase("phase8_recommendation", (NPM, "run", "phase8:recommend"), "artifacts/recommendation/recommendation_summary.json"),
)


class FullPipelineOrchestrator:
    def __init__(
        self,
        root: Path = ROOT,
        memory_store: PolicyMemoryStore | None = None,
        phases: tuple[PipelinePhase, ...] = FULL_PIPELINE_PHASES,
    ) -> None:
        self.root = root
        self.memory = memory_store or PolicyMemoryStore()
        self.phases = phases

    def phase_plan(self) -> list[dict[str, Any]]:
        return [
            {
                "phase": phase.name,
                "command": list(phase.command),
                "primaryArtifact": phase.primary_artifact,
            }
            for phase in self.phases
        ]

    def run(self, run_id: str) -> dict[str, Any]:
        self.memory.ensure_schema()
        self._write_policy_memory_priors(run_id)
        self.memory.update_run_status(run_id, "running")
        completed: list[str] = []
        started_at = time.time()

        try:
            for phase in self.phases:
                self._log(run_id, phase, "running", message="Phase started.")
                phase_started = time.time()
                completed_process = subprocess.run(
                    phase.command,
                    cwd=self.root,
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    timeout=None,
                )
                duration = round(time.time() - phase_started, 3)
                metadata = {
                    "returncode": completed_process.returncode,
                    "duration_seconds": duration,
                    "stdout_tail": completed_process.stdout[-4000:],
                    "stderr_tail": completed_process.stderr[-4000:],
                }
                if completed_process.returncode != 0:
                    self._log(
                        run_id,
                        phase,
                        "failed",
                        message=f"Phase failed with exit code {completed_process.returncode}.",
                        metadata=metadata,
                    )
                    self.memory.update_run_status(run_id, "failed", {"failed_phase": phase.name, "phase_metadata": metadata})
                    return {
                        "status": "failed",
                        "failed_phase": phase.name,
                        "completed_phases": completed,
                        "duration_seconds": round(time.time() - started_at, 3),
                    }

                completed.append(phase.name)
                self._log(
                    run_id,
                    phase,
                    "completed",
                    message="Phase completed.",
                    metadata=metadata,
                )

            result = {
                "status": "completed",
                "completed_phases": completed,
                "duration_seconds": round(time.time() - started_at, 3),
                "final_artifact": self.phases[-1].primary_artifact if self.phases else None,
            }
            self.memory.update_run_status(run_id, "completed", result)
            return result
        except Exception as exc:
            self.memory.log_phase(
                run_id,
                "pipeline",
                "failed",
                message=str(exc),
                metadata={"error_type": exc.__class__.__name__},
            )
            self.memory.update_run_status(run_id, "failed", {"error": str(exc), "error_type": exc.__class__.__name__})
            return {
                "status": "failed",
                "error": str(exc),
                "error_type": exc.__class__.__name__,
                "completed_phases": completed,
                "duration_seconds": round(time.time() - started_at, 3),
            }

    def _log(
        self,
        run_id: str,
        phase: PipelinePhase,
        status: str,
        message: str,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        self.memory.log_phase(
            run_id,
            phase.name,
            status,
            artifact_path=phase.primary_artifact,
            message=message,
            metadata=metadata,
        )

    def _write_policy_memory_priors(self, run_id: str) -> None:
        output_path = self.root / "data" / "synthetic" / "policy_memory_priors.json"
        try:
            write_policy_memory_priors(run_id, self.memory, output_path)
        except Exception as exc:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(
                json.dumps(
                    {
                        "runId": run_id,
                        "createdAt": datetime.now(timezone.utc).isoformat(),
                        "available": False,
                        "reason": "policy_memory_priors_error",
                        "errorType": exc.__class__.__name__,
                        "similarPolicyCount": 0,
                        "similarPolicies": [],
                        "priors": {},
                        "monteCarloCalibration": {},
                    },
                    indent=2,
                    sort_keys=True,
                )
                + "\n",
                encoding="utf-8",
            )
