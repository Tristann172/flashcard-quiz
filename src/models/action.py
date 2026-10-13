from __future__ import annotations

from dataclasses import dataclass
from typing import Any

DELETE_CARD = "DELETE_CARD"


@dataclass(frozen=True)
class ActionRecord:
    action_type: str
    payload: Any