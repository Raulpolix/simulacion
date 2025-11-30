# persona.py
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Tuple, Optional
import random

# Lista de roles que usamos en la simulación
ROLES = ["recolector", "guerrero", "comerciante", "explorador", "avaro"]


@dataclass
class Persona:
    id_: int
    x: int
    y: int
    rol: str
    energia: int = 10
    monedas: int = 0
    vivo: bool = True
    edad_turnos: int = 0
    objetos: List[str] = field(default_factory=list)

    # estadísticas
    combates_ganados: int = 0
    combates_totales: int = 0
    intercambios_realizados: int = 0
    territorio_actual: Optional[str] = None

    # para exploradores (casillas ya visitadas)
    celdas_visitadas: set = field(default_factory=set)

    def posicion(self) -> Tuple[int, int]:
        return self.x, self.y

    def marcar_celda_visitada(self) -> None:
        self.celdas_visitadas.add((self.x, self.y))

    def esta_en_territorio(self, nombre: str) -> bool:
        return self.territorio_actual == nombre

    def esta_vivo(self) -> bool:
        return self.vivo and self.energia > 0

    def recibir_daño(self, cantidad: int) -> None:
        self.energia -= cantidad
        if self.energia <= 0:
            self.vivo = False

    def ganar_monedas(self, cantidad: int) -> None:
        if cantidad > 0:
            self.monedas += cantidad

    def gastar_monedas(self, cantidad: int) -> bool:
        if cantidad <= self.monedas:
            self.monedas -= cantidad
            return True
        return False

    def mover(self, dx: int, dy: int, ancho: int, alto: int) -> None:
        """Movimiento con wrap-around (toroidal)."""
        self.x = (self.x + dx) % ancho
        self.y = (self.y + dy) % alto
        self.marcar_celda_visitada()

    def decidir_movimiento(
        self,
        ancho: int,
        alto: int,
        personas: List["Persona"],
        monedas: dict,
        territorios: List["Territorio"],
    ) -> Tuple[int, int]:
        """
        Devuelve (dx, dy) según el rol.
        personas incluye a esta persona.
        monedas es un dict {(x, y): [valores]}
        """
        # movimientos vecinos (incluye quedarse)
        opciones = [
            (0, 0), (1, 0), (-1, 0),
            (0, 1), (0, -1),
            (1, 1), (1, -1), (-1, 1), (-1, -1)
        ]

        otros = [p for p in personas if p is not self and p.esta_vivo()]
        pos = self.posicion()

        def vecino_mas_cercano(filtro=None):
            candidatos = otros
            if filtro is not None:
                candidatos = [p for p in otros if filtro(p)]
            if not candidatos:
                return None
            px, py = pos
            p_obj = min(
                candidatos,
                key=lambda p: abs(p.x - px) + abs(p.y - py)
            )
            return p_obj.posicion()

        def moneda_mas_cercana():
            if not monedas:
                return None
            px, py = pos
            (mx, my), _ = min(
                monedas.items(),
                key=lambda item: abs(item[0][0] - px) + abs(item[0][1] - py)
            )
            return (mx, my)

        objetivo_persona = vecino_mas_cercano()
        objetivo_comerciable = vecino_mas_cercano(lambda p: p.rol != "guerrero")
        objetivo_moneda = moneda_mas_cercana()

        def paso_hacia(obj, huir: bool = False) -> Tuple[int, int]:
            if obj is None:
                return random.choice(opciones)
            x, y = pos
            tx, ty = obj
            dx = 0 if x == tx else (1 if tx > x else -1)
            dy = 0 if y == ty else (1 if ty > y else -1)
            if huir:
                dx, dy = -dx, -dy
            return dx, dy

        # comportamiento según rol
        if self.rol == "guerrero":
            # busca combate
            dx, dy = paso_hacia(objetivo_persona)
        elif self.rol == "comerciante":
            # busca a otros para intercambiar
            dx, dy = paso_hacia(objetivo_comerciable or objetivo_persona)
        elif self.rol == "recolector":
            # se mueve hacia monedas, huye de guerreros
            guerrero_cercano = vecino_mas_cercano(lambda p: p.rol == "guerrero")
            if guerrero_cercano is not None:
                dx, dy = paso_hacia(guerrero_cercano, huir=True)
            elif objetivo_moneda is not None:
                dx, dy = paso_hacia(objetivo_moneda)
            else:
                dx, dy = random.choice(opciones)
        elif self.rol == "explorador":
            # prioriza casillas no visitadas
            candidatos = []
            for dx, dy in opciones:
                nx = (self.x + dx) % ancho
                ny = (self.y + dy) % alto
                if (nx, ny) not in self.celdas_visitadas:
                    candidatos.append((dx, dy))
            if candidatos:
                dx, dy = random.choice(candidatos)
            else:
                dx, dy = random.choice(opciones)
        else:  # avaro
            # avaro persigue monedas pero se mueve poco
            if random.random() < 0.4 and objetivo_moneda is not None:
                dx, dy = paso_hacia(objetivo_moneda)
            else:
                dx, dy = random.choice(
                    [(0, 0), (1, 0), (0, 1), (-1, 0), (0, -1)]
                )

        # efecto bosque: menos movimiento
        territorio = None
        for t in territorios:
            if t.contiene(*pos):
                territorio = t
                break
        if territorio and territorio.tipo == "bosque":
            # 50% de no moverse
            if random.random() < 0.5:
                dx, dy = (0, 0)

        return dx, dy
