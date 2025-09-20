from dataclasses import dataclass
from typing import Tuple


@dataclass
class Waypoint:
    name: str
    coordinates: Tuple[float, float]


