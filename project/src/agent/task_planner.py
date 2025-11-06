from typing import Any, Dict
from loguru import logger
from src.utils.ai_helpers import AIClient

class TaskPlanner:
    def __init__(self):
        self.ai = AIClient()

    def plan(self, app: str, task: str, start_url: str) -> Dict[str, Any]:
        logger.info(f"Planning task for app={app}: {task}")
        plan = self.ai.plan(app, task, start_url)
        if not isinstance(plan, dict) or "steps" not in plan:
            plan = {"steps": []}
        return plan
