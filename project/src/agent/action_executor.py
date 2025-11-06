import re
from typing import Any, Dict, Optional
from loguru import logger
from playwright.async_api import Page, Locator

Selector = Dict[str, Any]

class ActionExecutor:
    def __init__(self, page: Page):
        self.page = page

    def _resolve(self, selector: Optional[Selector]) -> Locator:
        if not selector:
            return self.page.locator("body")
        if sel := selector.get("css"):
            if sel.startswith("http"):
                # used by goto
                return self.page.locator("body")
            return self.page.locator(sel)
        if "role" in selector and selector.get("name_regex"):
            role = selector["role"]
            pattern = selector["name_regex"]
            return self.page.get_by_role(role, name=re.compile(pattern, re.I))
        if "role" in selector and "name" in selector:
            return self.page.get_by_role(selector["role"], name=selector["name"])
        if sel := selector.get("text"):
            return self.page.get_by_text(sel)
        if sel := selector.get("placeholder"):
            return self.page.get_by_placeholder(sel)
        if sel := selector.get("label"):
            return self.page.get_by_label(sel)
        if sel := selector.get("xpath"):
            return self.page.locator(f"xpath={sel}")
        return self.page.locator("body")

    async def perform(self, step: Dict[str, Any]):
        action = step.get("action")
        selector = step.get("selector")
        wait_ms = step.get("wait_ms", 300)
        desc = step.get("description", action)
        logger.info(f"Action: {action} | {desc}")
        
        try:
            if action == "goto":
                url = selector.get("css") if selector else None
                if url:
                    await self.page.goto(url, timeout=30000)
            elif action == "click":
                locator = self._resolve(selector).first
                pre_url = self.page.url
                # simple DOM fingerprint by content length (fast)
                try:
                    pre_len = len(await self.page.content())
                except Exception:
                    pre_len = -1
                # Check if element exists
                if await locator.count() > 0:
                    try:
                        await locator.scroll_into_view_if_needed(timeout=3000)
                    except Exception:
                        pass
                    await locator.click(timeout=6000)
                    # give page a chance to change
                    try:
                        await self.page.wait_for_load_state("networkidle", timeout=6000)
                    except Exception:
                        pass
                    post_url = self.page.url
                    try:
                        post_len = len(await self.page.content())
                    except Exception:
                        post_len = -1
                    if post_url != pre_url or (pre_len != -1 and post_len != pre_len):
                        logger.info(f"✓ Clicked: {desc}")
                    else:
                        # Retry once with force click after another scroll
                        try:
                            await locator.scroll_into_view_if_needed(timeout=3000)
                        except Exception:
                            pass
                        await locator.click(timeout=6000)
                        logger.info(f"✓ Clicked (retry): {desc}")
                else:
                    logger.warning(f"✗ Element not found for click: {desc}")
            elif action == "hover":
                locator = self._resolve(selector).first
                if await locator.count() > 0:
                    await locator.hover(timeout=5000)
                else:
                    logger.warning(f"✗ Element not found for hover: {desc}")
            elif action == "type":
                text = step.get("input", "")
                # If no selector provided, type into currently focused element
                if not selector or selector == {}:
                    await self.page.keyboard.type(text, delay=50)
                    logger.info(f"✓ Typed into focused element: {text[:50]}")
                else:
                    locator = self._resolve(selector).first
                    if await locator.count() > 0:
                        await locator.fill("", timeout=5000)
                        await locator.type(text, delay=50, timeout=5000)
                        logger.info(f"✓ Typed: {text[:50]}")
                    else:
                        logger.warning(f"✗ Element not found for type: {desc}")
            elif action == "press":
                key = step.get("input", "Enter")
                # Support key combinations like "Control+n" or "Escape"
                if "+" in key:
                    # For combinations like "Control+n"
                    parts = key.split("+")
                    modifiers = parts[:-1]
                    final_key = parts[-1]
                    for mod in modifiers:
                        await self.page.keyboard.down(mod)
                    await self.page.keyboard.press(final_key)
                    for mod in reversed(modifiers):
                        await self.page.keyboard.up(mod)
                else:
                    await self.page.keyboard.press(key)
            elif action == "wait_for":
                state = step.get("input", "visible")
                locator = self._resolve(selector).first
                await locator.wait_for(state=state, timeout=10000)
            elif action == "scroll":
                y = int(step.get("input", 800))
                await self.page.mouse.wheel(0, y)
            else:
                logger.warning(f"Unknown action: {action}")
            await self.page.wait_for_timeout(wait_ms)
        except Exception as e:
            logger.warning(f"Action failed (continuing): {action} | {desc} | Error: {e}")
