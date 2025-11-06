import os
import json
from typing import Any, Dict, List
from loguru import logger

class AIClient:
    def __init__(self):
        self.anthropic_key = os.getenv("ANTHROPIC_API_KEY")
        self.openai_key = os.getenv("OPENAI_API_KEY")
        self.provider = "anthropic" if self.anthropic_key else ("openai" if self.openai_key else None)

        if self.provider == "anthropic":
            try:
                from anthropic import Anthropic
                self.client = Anthropic(api_key=self.anthropic_key)
            except Exception as e:
                logger.warning(f"Anthropic client init failed: {e}")
                self.provider = None
        elif self.provider == "openai":
            try:
                from openai import OpenAI
                self.client = OpenAI(api_key=self.openai_key)
            except Exception as e:
                logger.warning(f"OpenAI client init failed: {e}")
                self.provider = None
        else:
            self.client = None

    def plan(self, app: str, task: str, url: str) -> Dict[str, Any]:
        if not self.provider:
            logger.info("No AI provider configured, using heuristic plan")
            return self._heuristic_plan(app, task, url)
        
        logger.info(f"Planning with {self.provider} for {app}: {task}")
        try:
            system_prompt = (
                "You plan UI automation steps for web applications. "
                "Return ONLY valid JSON with this structure: {\"steps\": [{\"description\": \"...\", \"action\": \"...\", \"selector\": {...}, \"input\": \"...\", \"wait_ms\": 500, \"capture_hint\": true}]}\n\n"
                "Actions: goto, click, hover, type, press, wait_for, scroll\n"
                "Selectors: {\"role\": \"button\", \"name\": \"New page\"} OR {\"text\": \"Create\"} OR {\"placeholder\": \"Search...\"} OR {\"css\": \".button\"} OR {\"xpath\": \"//button[text()='OK']\"} OR {\"label\": \"Email\"}\n\n"
                "CRITICAL TRELLO INSTRUCTIONS:\n"
                "- FIRST STEP: If on Trello home, click on board name like {\"text\": \"My Trello board\"} to open it\n"
                "- To dismiss cookie banner: Click {\"text\": \"Accept all\"} or {\"text\": \"Only necessary\"}, wait 1000ms\n"
                "- To add card: Click {\"text\": \"Add a card\"} in the specific list, wait 1500ms, type into focused textarea, press Enter\n"
                "- To open card: Click card name using {\"text\": \"Card Name Exact\"}\n"
                "- Card modal buttons: {\"text\": \"Labels\"}, {\"text\": \"Members\"}, {\"text\": \"Dates\"}, {\"text\": \"Checklist\"}\n"
                "- Input fields: {\"placeholder\": \"Enter a title for this card…\"} or focused element (no selector)\n"
                "- ALWAYS wait 1500-2000ms after clicks that open modals/cards\n"
                "- Use exact text matching: {\"text\": \"Add a card\"} not partial match\n\n"
                "NOTION INSTRUCTIONS:\n"
                "- FIRST STEP: From Notion home/workspace, click existing page from sidebar using {\"text\": \"Page Name\"}\n"
                "- To open page: Click page title in sidebar: {\"text\": \"Budget Template\"}, {\"text\": \"Job Finder\"}, etc.\n"
                "- Buttons work with: {\"text\": \"Share\"}, {\"text\": \"Settings\"}, {\"role\": \"button\", \"name\": \"...\"}\n"
                "- AVOID page creation (New page/keyboard shortcuts don't work reliably)\n"
                "- Focus on navigation, opening existing pages, clicking buttons, using search\n"
                "- Wait 1500-2000ms after navigation for page to fully load\n\n"
                "Keep steps concise (4-7 steps). Add wait_ms: 1500-2000 after clicks that open modals."
            )
            
            user_prompt = f"App: {app}\nTask: {task}\nStart URL: {url}\n\nGenerate automation steps."
            
            if self.provider == "anthropic":
                msg = self.client.messages.create(
                    model="claude-3-5-sonnet-latest",
                    system=system_prompt,
                    max_tokens=2000,
                    messages=[{"role": "user", "content": user_prompt}]
                )
                content = msg.content[0].text if msg and msg.content else "{}"
            else:
                resp = self.client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    temperature=0.2
                )
                content = resp.choices[0].message.content
            
            # Try to extract JSON if wrapped in markdown
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()
            
            data = json.loads(content)
            if isinstance(data, dict) and "steps" in data and len(data["steps"]) > 0:
                logger.info(f"✓ AI plan generated with {len(data['steps'])} steps")
                return data
            else:
                logger.warning(f"AI returned invalid plan structure: {data}")
        except json.JSONDecodeError as e:
            logger.warning(f"AI returned non-JSON response: {content[:200]}... | Error: {e}")
        except Exception as e:
            logger.warning(f"AI planning failed: {e}")
        
        logger.info("Falling back to heuristic plan")
        return self._heuristic_plan(app, task, url)

    def _heuristic_plan(self, app: str, task: str, url: str) -> Dict[str, Any]:
        logger.info(f"Using heuristic plan for {app}")
        # More targeted exploratory strategy: fewer steps, longer waits, better selectors
        plan: List[Dict[str, Any]] = [
            {
                "description": f"Navigate to {app} workspace",
                "action": "goto",
                "selector": {"css": url},
                "wait_ms": 2000,
                "capture_hint": True
            },
            {
                "description": "Wait for page to stabilize",
                "action": "scroll",
                "input": "0",
                "wait_ms": 1500,
                "capture_hint": True
            }
        ]
        
        # Add task-specific steps based on keywords
        task_lower = task.lower()
        if "create" in task_lower or "new" in task_lower:
            if "database" in task_lower:
                plan.extend([
                    {"description": "Look for New page button", "action": "click", "selector": {"text": "New page"}, "wait_ms": 1200, "capture_hint": True},
                    {"description": "Click Table/Database option", "action": "click", "selector": {"text": "Table"}, "wait_ms": 1000, "capture_hint": True},
                ])
            elif "page" in task_lower:
                plan.append({"description": "Click New page", "action": "click", "selector": {"text": "New page"}, "wait_ms": 1200, "capture_hint": True})
        
        if "filter" in task_lower:
            plan.extend([
                {"description": "Look for filter button", "action": "click", "selector": {"role": "button", "name_regex": "filter|Filter"}, "wait_ms": 1000, "capture_hint": True},
                {"description": "Wait for filter UI", "action": "scroll", "input": "0", "wait_ms": 800, "capture_hint": True},
            ])
        
        # Final capture
        plan.append({
            "description": "Final state capture",
            "action": "scroll",
            "input": "0",
            "wait_ms": 500,
            "capture_hint": True
        })
        
        return {"steps": plan}
