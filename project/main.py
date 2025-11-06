import argparse
import asyncio
import os
import time
from typing import List, Dict, Any
from loguru import logger
from dotenv import load_dotenv

from src.config.app_configs import APPS
from src.agent.task_planner import TaskPlanner
from src.agent.action_executor import ActionExecutor
from src.agent.state_detector import StateDetector
from src.capture.screenshot_manager import ScreenshotManager
from src.capture.metadata_handler import MetadataHandler
from src.utils.browser_helpers import BrowserManager

async def run_once(app: str, task: str, out_root: str, headless: bool, profile: str, max_steps: int, manual_login: bool):
    cfg = APPS.get(app)
    if not cfg:
        raise SystemExit(f"Unknown app: {app}")

    planner = TaskPlanner()
    detector = StateDetector(
        networkidle_ms=int(os.getenv("NETWORKIDLE_TIMEOUT_MS", "1500")),
        capture_delay_ms=int(os.getenv("CAPTURE_DELAY_MS", "500")),
        significance_threshold=float(os.getenv("SIGNIFICANCE_THRESHOLD", "0.12")),
    )
    shots = ScreenshotManager(out_root)
    meta = MetadataHandler(out_root)

    async with BrowserManager(headless=headless, profile=profile) as bm:
        page = await bm.new_page()
        await BrowserManager.ensure_logged_in(page, cfg.login_url, manual=manual_login)

        # Plan steps
        plan = planner.plan(app, task, cfg.workspace_url or cfg.base_url)
        steps: List[Dict[str, Any]] = plan.get("steps", [])
        execu = ActionExecutor(page)

        recorded: List[Dict[str, Any]] = []
        logger.info(f"Executing {len(steps)} planned steps (max {max_steps})")
        
        for i, step in enumerate(steps[:max_steps], start=1):
            try:
                # Always try to perform action (has internal error handling now)
                await execu.perform(step)
                
                # Always detect state and try to capture
                state = await detector.detect(page)
                do_capture = bool(step.get("capture_hint", False)) or state.get("significant", False)
                img_path = None
                
                # Always capture screenshots for key steps
                if do_capture or i == 1 or i == len(steps):
                    try:
                        img_path = await shots.capture(page, app, task, step.get("description", f"step-{i}"))
                    except Exception as capture_err:
                        logger.warning(f"Screenshot capture failed: {capture_err}")
                
                recorded.append({
                    "index": i,
                    "description": step.get("description"),
                    "action": step.get("action"),
                    "selector": step.get("selector"),
                    "input": step.get("input"),
                    "url": state.get("url"),
                    "has_modal": state.get("has_modal"),
                    "has_overlay": state.get("has_overlay"),
                    "screenshot": img_path,
                    "timestamp": state.get("timestamp"),
                })
            except Exception as e:
                logger.warning(f"Step {i} encountered error (continuing): {e}")
                # Still try to capture current state
                try:
                    img_path = await shots.capture(page, app, task, f"step-{i}-error")
                    recorded.append({
                        "index": i,
                        "description": step.get("description"),
                        "action": step.get("action"),
                        "error": str(e),
                        "screenshot": img_path,
                        "timestamp": time.time(),
                    })
                except:
                    recorded.append({
                        "index": i,
                        "description": step.get("description"),
                        "action": step.get("action"),
                        "error": str(e),
                        "timestamp": time.time(),
                    })
        
        meta.write(app, task, recorded)
        logger.info(f"Workflow complete: {len(recorded)} steps recorded, {len([r for r in recorded if r.get('screenshot')])} screenshots captured")

if __name__ == "__main__":
    load_dotenv()
    parser = argparse.ArgumentParser()
    parser.add_argument("--app", required=True, help="App key (trello, notion, linear)")
    parser.add_argument("--task", required=True, help="Natural language task")
    parser.add_argument("--out", default="dataset", help="Output root directory")
    parser.add_argument("--headless", action="store_true", help="Run headless")
    parser.add_argument("--profile", default=os.getenv("PERSISTENT_PROFILE", ".playwright"))
    parser.add_argument("--max-steps", type=int, default=20)
    parser.add_argument("--manual-login", action="store_true")
    args = parser.parse_args()

    asyncio.run(run_once(
        app=args.app,
        task=args.task,
        out_root=args.out,
        headless=args.headless or (str(os.getenv("HEADLESS", "false")).lower() == "true"),
        profile=args.profile,
        max_steps=args.max_steps,
        manual_login=args.manual_login,
    ))
