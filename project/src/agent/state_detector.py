import hashlib
import json
import time
from typing import Any, Dict
from loguru import logger
from playwright.async_api import Page

class StateDetector:
    def __init__(self, networkidle_ms: int = 1500, capture_delay_ms: int = 500, significance_threshold: float = 0.12):
        self.networkidle_ms = networkidle_ms
        self.capture_delay_ms = capture_delay_ms
        self.significance_threshold = significance_threshold
        self._last_signature = None

    async def stabilize(self, page: Page):
        try:
            await page.wait_for_load_state("networkidle")
        except Exception:
            pass
        await page.wait_for_timeout(self.networkidle_ms)
        await page.wait_for_timeout(self.capture_delay_ms)

    async def dom_signature(self, page: Page) -> str:
        html = await page.content()
        # Normalize by stripping dynamic attrs that often change
        simplified = html.encode("utf-8", errors="ignore")
        return hashlib.sha256(simplified).hexdigest()

    async def detect(self, page: Page) -> Dict[str, Any]:
        await self.stabilize(page)
        url = page.url
        has_modal = await page.evaluate("""
            () => !!document.querySelector('[role="dialog"], .modal, [class*="Dialog"], [data-modal="true"]')
        """)
        has_overlay = await page.evaluate("""
            () => !!document.querySelector('[class*="overlay"], [class*="Popover"], [class*="dropdown"]')
        """)
        signature = await self.dom_signature(page)
        changed = (self._last_signature is None) or (self._last_signature != signature)
        self._last_signature = signature
        return {
            "url": url,
            "has_modal": bool(has_modal),
            "has_overlay": bool(has_overlay),
            "signature": signature,
            "changed": changed,
            "significant": changed or has_modal or has_overlay,
            "timestamp": time.time(),
        }
