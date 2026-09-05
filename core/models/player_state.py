from dataclasses import dataclass
from typing import Optional


@dataclass
class PlayerState:
    weapon_name: Optional[str] = None
