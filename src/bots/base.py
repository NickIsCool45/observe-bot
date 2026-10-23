import json
from abc import ABC, abstractmethod
from typing import Any, List, Optional

class Bot(ABC):
    """Base for all trading desk agents"""

    def __init__(self, name: str, model: str, description: str):
        self.name = name
        self.model = model
        self.description = description

    @abstractmethod
    def build_user_message(self, **kwargs) -> str:
        """Return the user-facing message for this bot"""
        pass

    @abstractmethod
    def parse_response(self, content: str) -> Any:
        """Parse the bot's response into structured data"""
        pass

def load_config(config_path: str = None) -> dict:
    """Load agents.json or rules.json"""
    if config_path is None:
        from pathlib import Path
        script_dir = Path(__file__).parent.parent.parent
        config_path = script_dir / "config" / "agents.json"
    else:
        from pathlib import Path
        config_path = Path(config_path)

    with open(config_path) as f:
        options = json.load(f)

    # Check for local override
    local_path = config_path.parent / f"{config_path.stem}.local.json"
    if local_path.exists():
        with open(local_path) as f:
            local_options = json.load(f)
            options.update(local_options)

    return options