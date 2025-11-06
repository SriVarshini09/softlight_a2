import json
from pathlib import Path
from typing import List, Dict, Any

class MetadataHandler:
    def __init__(self, out_root: str):
        self.out_root = Path(out_root)

    def write(self, app: str, task: str, steps: List[Dict[str, Any]]):
        from slugify import slugify
        tslug = slugify(task)
        td = self.out_root / app / tslug
        td.mkdir(parents=True, exist_ok=True)
        (td / "metadata.json").write_text(json.dumps({"app": app, "task": task, "steps": steps}, indent=2))
