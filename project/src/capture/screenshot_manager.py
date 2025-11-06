import os
import time
from pathlib import Path
from typing import Dict, Any
from loguru import logger
from slugify import slugify
from playwright.async_api import Page

class ScreenshotManager:
    def __init__(self, out_root: str):
        self.out_root = Path(out_root)
        self.out_root.mkdir(parents=True, exist_ok=True)
        self.step_index = 0
        self._last_url = None
        self._last_dom_len = None

    def task_dir(self, app: str, task: str) -> Path:
        app_dir = self.out_root / app
        tslug = slugify(task)[:80]
        td = app_dir / tslug
        td.mkdir(parents=True, exist_ok=True)
        return td

    async def capture(self, page: Page, app: str, task: str, description: str) -> str:
        # Duplicate-state guard (same URL and DOM size)
        try:
            cur_url = page.url
            dom_len = len(await page.content())
        except Exception:
            cur_url = None
            dom_len = None

        if self._last_url == cur_url and self._last_dom_len == dom_len:
            logger.info("Skipping screenshot (no state change detected)")
            return ""

        self.step_index += 1
        td = self.task_dir(app, task)
        dslug = description.lower().replace(" ", "-")[:70]
        fname = f"step-{self.step_index:02d}-{dslug}.png"
        path = td / fname
        await page.screenshot(path=str(path), full_page=False)
        logger.info(f"Captured screenshot: {path}")
        self._last_url, self._last_dom_len = cur_url, dom_len
        return str(path)
