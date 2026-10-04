import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from backend.app.pipeline_orchestrator import FullPipelineOrchestrator, PipelinePhase


class PipelineOrchestratorTests(unittest.TestCase):
    def test_phase_plan_exposes_all_configured_phases(self):
        orchestrator = FullPipelineOrchestrator(memory_store=Mock(), phases=(
            PipelinePhase("phase_a", ("cmd", "a"), "a.json"),
            PipelinePhase("phase_b", ("cmd", "b"), "b.json"),
        ))

        plan = orchestrator.phase_plan()

        self.assertEqual([item["phase"] for item in plan], ["phase_a", "phase_b"])
        self.assertEqual(plan[0]["primaryArtifact"], "a.json")

    def test_run_logs_failure_and_stops(self):
        memory = Mock()
        orchestrator = FullPipelineOrchestrator(
            root=Path("."),
            memory_store=memory,
            phases=(PipelinePhase("phase_a", ("cmd", "a"), "a.json"),),
        )
        failed_process = Mock(returncode=1, stdout="out", stderr="err")

        with patch("backend.app.pipeline_orchestrator.subprocess.run", return_value=failed_process):
            result = orchestrator.run("SIM-1")

        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["failed_phase"], "phase_a")
        memory.clear_phase_logs.assert_called_once_with("SIM-1")
        memory.update_run_status.assert_any_call("SIM-1", "running")
        self.assertTrue(any(call.args[2] == "failed" for call in memory.log_phase.call_args_list))

    def test_run_completes_all_phases(self):
        memory = Mock()
        orchestrator = FullPipelineOrchestrator(
            root=Path("."),
            memory_store=memory,
            phases=(
                PipelinePhase("phase_a", ("cmd", "a"), "a.json"),
                PipelinePhase("phase_b", ("cmd", "b"), "b.json"),
            ),
        )
        completed_process = Mock(returncode=0, stdout="out", stderr="")

        with patch("backend.app.pipeline_orchestrator.subprocess.run", return_value=completed_process):
            result = orchestrator.run("SIM-1")

        self.assertEqual(result["status"], "completed")
        self.assertEqual(result["completed_phases"], ["phase_a", "phase_b"])
        memory.update_run_status.assert_any_call("SIM-1", "completed", result)


if __name__ == "__main__":
    unittest.main()
