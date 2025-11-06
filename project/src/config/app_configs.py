from dataclasses import dataclass
from typing import Optional, Dict

@dataclass
class AppConfig:
    name: str
    base_url: str
    login_url: Optional[str] = None
    workspace_url: Optional[str] = None

APPS: Dict[str, AppConfig] = {
    "trello": AppConfig(
        name="trello",
        base_url="https://trello.com",
        login_url="https://trello.com/login",
        workspace_url="https://trello.com"
    ),
    "notion": AppConfig(
        name="notion",
        base_url="https://www.notion.so",
        login_url="https://www.notion.so/login",
        workspace_url="https://www.notion.so"
    ),
    "linear": AppConfig(
        name="linear",
        base_url="https://linear.app",
        login_url="https://linear.app/login",
        workspace_url="https://linear.app"
    ),
}
