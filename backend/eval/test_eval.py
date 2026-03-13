import os
import pathlib
import subprocess
import sys

import dotenv
import pytest
from google.adk.evaluation.agent_evaluator import AgentEvaluator

pytest_plugins = ("pytest_asyncio",)

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


@pytest.fixture(scope="session", autouse=True)
def load_env():
    dotenv.load_dotenv(ROOT / ".env", override=True)
    os.environ["MODEL_ID"] = "gemini-2.5-flash"
    os.environ.setdefault("GOOGLE_GENAI_USE_VERTEXAI", "TRUE")
    for mod in ("app.agents.live_incident_agent", "app.agents.agent"):
        if mod in sys.modules:
            sys.modules.pop(mod)


@pytest.mark.asyncio
async def test_tool_trajectory_eval():
    os.environ.setdefault("MODEL_ID", "gemini-2.5-flash")
    eval_file = pathlib.Path(__file__).parent / "data/tool_trajectory.evalset.json"
    await AgentEvaluator.evaluate(
        agent_module="eval.eval_agent",
        eval_dataset_file_path_or_dir=str(eval_file),
        num_runs=1,
    )


def test_grounding_eval_script():
    eval_script = pathlib.Path(__file__).parent / "eval_grounding.py"
    eval_set = pathlib.Path(__file__).parent / "data/grounding_eval_set.jsonl"
    output = pathlib.Path(__file__).parent / "data/grounding_eval_report.json"
    result = subprocess.run(
        [
            sys.executable,
            str(eval_script),
            "--eval-set",
            str(eval_set),
            "--output",
            str(output),
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
