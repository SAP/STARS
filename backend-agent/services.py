import json
from pathlib import Path

from attack import AttackSuite


def run_all_attacks(
    spec_path: str = "data/all/default.json",
    target: str = None
):
    """
    Run all LLM attacks with specified target and evaluation models.

    Returns a dict:
        - success: bool
        - results: list (if success)
        - error: str (if failure)
    """
    if not target:
        return {"success": False, "error": "Target parameter is required"}
    default_spec_path = Path(spec_path)
    if not default_spec_path.exists():
        return {"success": False, "error": f"File not found: {spec_path}"}

    try:
        with default_spec_path.open("r") as f:
            spec = json.load(f)
    except json.JSONDecodeError as e:
        return {"success": False, "error": f"Invalid JSON format: {e}"}
    except PermissionError:
        return {
            "success": False,
            "error": f"Permission denied reading file: {spec_path}"
        }
    try:
        if "attacks" in spec:
            suite = AttackSuite.from_dict(spec)
            if target:
                suite.set_target(target)
            results = suite.run()
            return {"success": True, "results": results}
        else:
            return {"success": False, "error": "JSON is invalid. No attacks run."}
    except Exception as e:
        return {"success": False, "error": f"Failed to run attacks: {str(e)}"}
