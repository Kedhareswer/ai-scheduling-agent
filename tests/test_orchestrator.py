import os
import pytest

# Ensure no OPENAI_API_KEY for this unit test to use fallback parsing
os.environ.pop("OPENAI_API_KEY", None)

from utils.agents import SchedulingAgentOrchestrator


def test_orchestrator_basic_flow():
    # Sample patient input covering required fields for fallback parser
    patient_input = "Jane Doe, 1990-05-14, Cigna, 123456789, G12345, jane@example.com, +1-555-111-2222"

    orchestrator = SchedulingAgentOrchestrator()
    result = orchestrator.process_patient_request(patient_input)

    # Basic assertions
    assert isinstance(result, dict)
    assert "messages" in result
    assert "errors" in result

    # Expect no errors for normal happy-path
    assert not result["errors"], f"Errors encountered in orchestrator: {result['errors']}"

    # Verify that appointment was booked and communications were sent
    workflow_steps = result.get("current_step") or result.get("state", {}).get("current_step")
    # Final step should be workflow_complete or error_handled
    assert workflow_steps in ("workflow_complete", "error_handled"), f"Unexpected final step: {workflow_steps}"

    # Check at least one success message exists in messages
    success_msgs = [m for m in result["messages"] if "✅" in m or "📧" in m]
    assert success_msgs, "Expected success messages not found in orchestrator output"
