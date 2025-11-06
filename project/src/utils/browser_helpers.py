import os
import time
from typing import Optional
from loguru import logger
from playwright.async_api import async_playwright, BrowserContext, Page

class BrowserManager:
    def __init__(self, headless: Optional[bool] = None, profile: Optional[str] = None, navigation_timeout_ms: int = 20000):
        self.headless = (str(os.getenv("HEADLESS", "false")).lower() == "true") if headless is None else headless
        self.profile = os.getenv("PERSISTENT_PROFILE", ".playwright") if profile is None else profile
        self.navigation_timeout_ms = int(os.getenv("NAVIGATION_TIMEOUT_MS", str(navigation_timeout_ms)))
        self._pw = None
        self.context: Optional[BrowserContext] = None

    async def __aenter__(self):
        self._pw = await async_playwright().start()
        self.context = await self._pw.chromium.launch_persistent_context(
            user_data_dir=self.profile,
            headless=self.headless,
            args=["--disable-blink-features=AutomationControlled"],
            viewport={"width": 1400, "height": 900},
            slow_mo=50,
        )
        self.context.set_default_navigation_timeout(self.navigation_timeout_ms)
        return self

    async def __aexit__(self, exc_type, exc, tb):
        try:
            if self.context:
                await self.context.close()
        finally:
            if self._pw:
                await self._pw.stop()

    async def new_page(self) -> Page:
        assert self.context
        page = await self.context.new_page()
        page.set_default_navigation_timeout(self.navigation_timeout_ms)
        return page

    @staticmethod
    async def ensure_logged_in(page: Page, login_url: Optional[str], manual: bool = False):
        if not login_url:
            return
        if manual:
            logger.info("Manual login enabled. Navigating to login page and waiting for user action.")
            await page.goto(login_url)
            logger.info("Please complete login in the opened browser window. Waiting 90s...")
            await page.wait_for_timeout(90000)
            return
        logger.info("Attempting password-based login via environment variables (if present).")
        await page.goto(login_url)
        # Best-effort: try to find email/password fields by role/placeholder, but do not hardcode selectors
        try:
            email = os.getenv("EMAIL") or None
            password = os.getenv("PASSWORD") or None
            if email and password:
                inp = page.get_by_role("textbox").first
                await inp.fill(email)
                await page.get_by_role("textbox").nth(1).fill(password)
                await page.get_by_role("button", name="Log in").first.click()
                await page.wait_for_load_state("networkidle")
            else:
                logger.info("Credentials not provided; waiting for manual login for 60s.")
                await page.wait_for_timeout(60000)
        except Exception as e:
            logger.warning(f"Login helper encountered an issue: {e}")
            await page.wait_for_timeout(30000)
