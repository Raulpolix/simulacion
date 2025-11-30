# territorio.py
from dataclasses import dataclass
from typing import Tuple


@dataclass
class Territorio:
    nombre: str
    tipo: str   # "bosque", "ciudad", "montaña", etc.
    x_min: int
    x_max: int
    y_min: int
    y_max: int

    def contiene(self, x: int, y: int) -> bool:
        return self.x_min <= x <= self.x_max and self.y_min <= y <= self.y_max

    def rango(self) -> Tuple[Tuple[int, int], Tuple[int, int]]:
        return (self.x_min, self.y_min), (self.x_max, self.y_max)
