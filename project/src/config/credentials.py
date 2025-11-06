import os
from dataclasses import dataclass
from typing import Optional

@dataclass
class Credentials:
    email: Optional[str]
    password: Optional[str]

    @staticmethod
    def load_for(app: str) -> "Credentials":
        email = os.getenv(f"{app.upper()}_EMAIL")
        password = os.getenv(f"{app.upper()}_PASSWORD")
        return Credentials(email=email, password=password)
