# utils.py
from __future__ import annotations
from typing import Dict, Tuple, List, Optional
import random

from persona import Persona
from territorio import Territorio


# -------------------------------------------------------------------
# RECOGER MONEDAS
# -------------------------------------------------------------------

def recoger_monedas(persona: Persona, monedas: Dict[Tuple[int, int], List[int]]) -> None:
    """
    Si hay monedas en la celda de la persona, recoge todas.
    """
    pos = persona.posicion()
    if pos in monedas:
        valores = monedas.pop(pos)  # quita todas las monedas de esa casilla
        persona.ganar_monedas(sum(valores))


# -------------------------------------------------------------------
# COMBATE
# -------------------------------------------------------------------

def combate(a: Persona, b: Persona) -> Optional[Persona]:
    """
    Devuelve el ganador o None si empatan.
    El daño y la probabilidad dependen de energía.
    """
    a.combates_totales += 1
    b.combates_totales += 1

    # prob ganador proporcional a energía
    total = max(a.energia + b.energia, 1)
    prob_a = a.energia / total

    if random.random() < prob_a:
        b.recibir_daño(5)
        if not b.esta_vivo():
            a.combates_ganados += 1
            return a
        return None
    else:
        a.recibir_daño(5)
        if not a.esta_vivo():
            b.combates_ganados += 1
            return b
        return None


# -------------------------------------------------------------------
# COMERCIO
# -------------------------------------------------------------------

def intercambiar(p1: Persona, p2: Persona, territorios: List[Territorio], evento_actual=None) -> bool:
    """
    Si ambos aceptan comerciar y tienen moneda/objeto, intercambian.
    Devuelve True si hubo comercio, False si no.
    """
    # reglas por rol
    def quiere_comerciar(p: Persona):
        if p.rol == "comerciante":
            return True
        if p.rol == "guerrero":
            return False
        if p.rol == "explorador":
            return random.random() < 0.2
        if p.rol == "recolector":
            return p.monedas > 0 and bool(p.objetos)
        if p.rol == "avaro":
            return False
        return False

    # niebla = nada de interacciones
    if evento_actual == "niebla":
        return False

    if not (quiere_comerciar(p1) and quiere_comerciar(p2)):
        return False

    if p1.monedas <= 0 or p2.monedas <= 0:
        return False
    if not p1.objetos or not p2.objetos:
        return False

    # intercambio 1 moneda ↔ 1 objeto
    p1.monedas -= 1
    p2.monedas -= 1

    obj1 = p1.objetos.pop()
    obj2 = p2.objetos.pop()

    p1.objetos.append(obj2)
    p2.objetos.append(obj1)

    p1.intercambios_realizados += 1
    p2.intercambios_realizados += 1

    return True


# -------------------------------------------------------------------
# EVENTOS
# -------------------------------------------------------------------

def generar_evento() -> Optional[str]:
    """
    Devuelve un evento aleatorio con prob 5% por turno.
    """
    if random.random() < 0.05:
        return random.choice(["lluvia", "terremoto", "plaga", "niebla", "mercado"])
    return None


def aplicar_evento(evento: str, personas: List[Persona],
                   monedas: Dict[Tuple[int, int], List[int]],
                   ancho: int, alto: int) -> Dict:
    """
    Aplica los efectos del evento y devuelve información
    como lista de muertes.
    """
    info = {"muertes": []}

    if evento == "lluvia":
        # genera monedas nuevas
        for _ in range(10):
            x = random.randrange(ancho)
            y = random.randrange(alto)
            monedas.setdefault((x, y), []).append(random.randint(1, 5))

    elif evento == "terremoto":
        # todas las personas pierden energía
        for p in personas:
            if p.esta_vivo():
                p.recibir_daño(3)
                if not p.esta_vivo():
                    info["muertes"].append(p)

    elif evento == "plaga":
        # algunos mueren al instante
        for p in personas:
            if p.esta_vivo() and random.random() < 0.1:
                p.recibir_daño(p.energia)
                info["muertes"].append(p)

    elif evento == "mercado":
        # aumenta comercio, pero lo hacemos desde simulación, no aquí
        pass

    elif evento == "niebla":
        # impide combate; lo gestiona simulación
        pass

    return info


# -------------------------------------------------------------------
# TERRITORIOS
# -------------------------------------------------------------------

def territorio_en_posicion(x: int, y: int, territorios: List[Territorio]) -> Optional[Territorio]:
    for t in territorios:
        if t.contiene(x, y):
            return t
    return None
