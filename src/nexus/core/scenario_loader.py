import yaml
from pathlib import Path
from typing import Dict, Any

from nexus.core.domain.scenario import Scenario

def load_scenario(path: str | Path) -> Scenario:
    with open(path, 'r', encoding='utf-8') as f:
        data = yaml.safe_load(f)
    
    return Scenario.model_validate(data)
