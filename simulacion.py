# simulacion.py
from __future__ import annotations
from typing import List, Dict, Tuple
import random

import matplotlib.pyplot as plt

from persona import Persona, ROLES
from territorio import Territorio
from utils import (
    recoger_monedas,
    combate,
    intercambiar,
    generar_evento,
    aplicar_evento,
    territorio_en_posicion,
)

# -------------------------------------------------------------------
# PARÁMETROS GLOBALES
# -------------------------------------------------------------------

GRID_ANCHO = 20
GRID_ALTO = 20
N_PERSONAS_INICIALES = 30
N_TURNOS = 200

# -------------------------------------------------------------------
# CREACIÓN DE TERRITORIOS Y PERSONAS
# -------------------------------------------------------------------

def crear_territorios() -> List[Territorio]:
    """
    Define algunos territorios:
    - bosque: arriba izquierda
    - ciudad: centro
    - montaña: abajo derecha
    """
    return [
        Territorio("Bosque Umbrío", "bosque", 0, 6, 0, 6),
        Territorio("Ciudad Central", "ciudad", 7, 12, 7, 12),
        Territorio("Cumbres Rocosas", "montaña", 13, 19, 13, 19),
    ]


def crear_personas() -> List[Persona]:
    personas: List[Persona] = []
    for i in range(N_PERSONAS_INICIALES):
        x = random.randrange(GRID_ANCHO)
        y = random.randrange(GRID_ALTO)
        rol = random.choice(ROLES)
        p = Persona(id_=i, x=x, y=y, rol=rol)
        # algunos roles empiezan con objetos
        if rol in ("comerciante", "explorador"):
            p.objetos.extend(["poción", "mapa"])
        elif rol == "guerrero":
            p.objetos.append("espada")
        elif rol == "recolector":
            p.objetos.append("cesta")
        else:  # avaro
            p.objetos.append("caja fuerte")
        p.marcar_celda_visitada()
        personas.append(p)
    return personas


def inicializar_monedas(territorios: List[Territorio]) -> Dict[Tuple[int, int], List[int]]:
    """
    Genera algunas monedas al principio.
    En montaña mayor probabilidad de monedas de alto valor.
    """
    monedas: Dict[Tuple[int, int], List[int]] = {}

    for _ in range(50):
        x = random.randrange(GRID_ANCHO)
        y = random.randrange(GRID_ALTO)
        territorio = territorio_en_posicion(x, y, territorios)
        if territorio and territorio.tipo == "montaña":
            valor = random.randint(3, 10)
        else:
            valor = random.randint(1, 5)
        monedas.setdefault((x, y), []).append(valor)

    return monedas


def agrupar_por_posicion(personas: List[Persona]) -> Dict[Tuple[int, int], List[Persona]]:
    celdas: Dict[Tuple[int, int], List[Persona]] = {}
    for p in personas:
        if not p.esta_vivo():
            continue
        celdas.setdefault(p.posicion(), []).append(p)
    return celdas

# -------------------------------------------------------------------
# SIMULACIÓN PRINCIPAL
# -------------------------------------------------------------------

def simular():
    territorios = crear_territorios()
    personas = crear_personas()
    monedas = inicializar_monedas(territorios)

    # estadísticas por turno
    historia_roles = {rol: [] for rol in ROLES}
    historia_riqueza = {rol: [] for rol in ROLES}
    muertes_por_rol = {rol: 0 for rol in ROLES}
    muertes_en_territorio = {t.nombre: 0 for t in territorios}
    total_comercios = 0

    for turno in range(N_TURNOS):
        # evento global
        evento = generar_evento()
        info_evento = {}
        if evento:
            info_evento = aplicar_evento(
                evento,
                personas,
                monedas,
                ancho=GRID_ANCHO,
                alto=GRID_ALTO,
            )
            # registrar muertes por evento
            for victima in info_evento.get("muertes", []):
                muertes_por_rol[victima.rol] += 1
                terr = territorio_en_posicion(victima.x, victima.y, territorios)
                if terr:
                    muertes_en_territorio[terr.nombre] += 1

        # 1) Actualizar territorio actual de cada persona
        for p in personas:
            if not p.esta_vivo():
                continue
            terr = territorio_en_posicion(p.x, p.y, territorios)
            p.territorio_actual = terr.nombre if terr else None

        # 2) Movimiento
        for p in personas:
            if not p.esta_vivo():
                continue
            dx, dy = p.decidir_movimiento(
                GRID_ANCHO, GRID_ALTO, personas, monedas, territorios
            )
            p.mover(dx, dy, GRID_ANCHO, GRID_ALTO)
            p.edad_turnos += 1

        # 3) Recoger monedas
        for p in personas:
            if not p.esta_vivo():
                continue
            recoger_monedas(p, monedas)

        # 4) Interacciones (combate/comercio) por casilla
        celdas = agrupar_por_posicion(personas)

        for pos, agentes in celdas.items():
            if len(agentes) < 2:
                continue

            # niebla: nadie pelea
            hay_niebla = evento == "niebla"

            # todas las parejas en la casilla
            for i in range(len(agentes)):
                for j in range(i + 1, len(agentes)):
                    a = agentes[i]
                    b = agentes[j]
                    if not (a.esta_vivo() and b.esta_vivo()):
                        continue

                    # intento de comercio primero
                    hubo_comercio = intercambiar(a, b, territorios, evento_actual=evento)
                    if hubo_comercio:
                        total_comercios += 1
                        continue

                    # luego combate (si no hay niebla)
                    if not hay_niebla:
                        ganador = combate(a, b)
                        if ganador is not None:
                            perdedor = b if ganador is a else a
                            if not perdedor.esta_vivo():
                                muertes_por_rol[perdedor.rol] += 1
                                terr = territorio_en_posicion(
                                    perdedor.x, perdedor.y, territorios
                                )
                                if terr:
                                    muertes_en_territorio[terr.nombre] += 1

        # 5) Estadísticas por turno
        for rol in ROLES:
            vivos_rol = [p for p in personas if p.esta_vivo() and p.rol == rol]
            historia_roles[rol].append(len(vivos_rol))
            riqueza_rol = sum(p.monedas for p in vivos_rol)
            historia_riqueza[rol].append(riqueza_rol)

    # métricas finales
    riqueza_final_por_rol = {
        rol: sum(p.monedas for p in personas if p.rol == rol)
        for rol in ROLES
    }
    rol_mas_rico = max(riqueza_final_por_rol, key=riqueza_final_por_rol.get)

    # rol más longevo (edad media)
    edad_media_por_rol = {}
    for rol in ROLES:
        agentes = [p for p in personas if p.rol == rol]
        if agentes:
            edad_media = sum(p.edad_turnos for p in agentes) / len(agentes)
        else:
            edad_media = 0
        edad_media_por_rol[rol] = edad_media
    rol_mas_longevo = max(edad_media_por_rol, key=edad_media_por_rol.get)

    # rol más violento (más combates totales)
    combates_por_rol = {
        rol: sum(p.combates_totales for p in personas if p.rol == rol)
        for rol in ROLES
    }
    rol_mas_violento = max(combates_por_rol, key=combates_por_rol.get)

    territorio_mas_letal = max(
        muertes_en_territorio, key=muertes_en_territorio.get
    )

    media_comercio_por_turno = total_comercios / N_TURNOS

    resultados = {
        "personas": personas,
        "territorios": territorios,
        "monedas": monedas,
        "historia_roles": historia_roles,
        "historia_riqueza": historia_riqueza,
        "muertes_por_rol": muertes_por_rol,
        "muertes_en_territorio": muertes_en_territorio,
        "riqueza_final_por_rol": riqueza_final_por_rol,
        "edad_media_por_rol": edad_media_por_rol,
        "combates_por_rol": combates_por_rol,
        "rol_mas_rico": rol_mas_rico,
        "rol_mas_longevo": rol_mas_longevo,
        "rol_mas_violento": rol_mas_violento,
        "territorio_mas_letal": territorio_mas_letal,
        "media_comercio_por_turno": media_comercio_por_turno,
    }

    return resultados

# -------------------------------------------------------------------
# FUNCIONES DE GRÁFICA (ANTES ESTABAN EN visualizacion.py)
# -------------------------------------------------------------------

def graficar_evolucion_roles(historia_roles: Dict[str, List[int]]) -> None:
    turnos = range(len(next(iter(historia_roles.values()))))
    for rol in ROLES:
        plt.plot(turnos, historia_roles[rol], label=rol)
    plt.xlabel("Turno")
    plt.ylabel("Nº de agentes")
    plt.title("Evolución de agentes por rol")
    plt.legend()
    plt.tight_layout()
    plt.show()


def graficar_riqueza_por_rol(historia_riqueza: Dict[str, List[int]]) -> None:
    turnos = range(len(next(iter(historia_riqueza.values()))))
    for rol in ROLES:
        plt.plot(turnos, historia_riqueza[rol], label=rol)
    plt.xlabel("Turno")
    plt.ylabel("Riqueza total")
    plt.title("Evolución de riqueza total por rol")
    plt.legend()
    plt.tight_layout()
    plt.show()


def graficar_muertes(muertes_por_rol: Dict[str, int]) -> None:
    roles = list(muertes_por_rol.keys())
    valores = [muertes_por_rol[r] for r in roles]
    plt.bar(roles, valores)
    plt.xlabel("Rol")
    plt.ylabel("Muertes")
    plt.title("Muertes por rol")
    plt.tight_layout()
    plt.show()


def mapa_final(
    personas: List[Persona],
    territorios: List[Territorio],
    monedas: Dict[Tuple[int, int], List[int]],
    ancho: int,
    alto: int
) -> None:
    """
    Scatter del turno final:
    - personas coloreadas por rol
    - monedas en amarillo
    - territorios como rectángulos semitransparentes
    """
    fig, ax = plt.subplots()

    # territorios
    for t in territorios:
        ancho_rect = t.x_max - t.x_min + 1
        alto_rect = t.y_max - t.y_min + 1
        ax.add_patch(
            plt.Rectangle(
                (t.x_min, t.y_min),
                ancho_rect,
                alto_rect,
                alpha=0.2,
                label=t.nombre
            )
        )

    # monedas
    xs_m = [x for (x, y) in monedas.keys() for _ in monedas[(x, y)]]
    ys_m = [y for (x, y) in monedas.keys() for _ in monedas[(x, y)]]
    if xs_m:
        ax.scatter(xs_m, ys_m, c="yellow", marker="*", label="moneda", alpha=0.6)

    # personas por rol
    colores_por_rol = {
        "recolector": "green",
        "guerrero": "red",
        "comerciante": "blue",
        "explorador": "purple",
        "avaro": "black",
    }

    for rol in ROLES:
        xs = [p.x for p in personas if p.esta_vivo() and p.rol == rol]
        ys = [p.y for p in personas if p.esta_vivo() and p.rol == rol]
        if xs:
            ax.scatter(xs, ys, c=colores_por_rol.get(rol, "gray"),
                       label=rol, alpha=0.8)

    ax.set_xlim(-0.5, ancho - 0.5)
    ax.set_ylim(-0.5, alto - 0.5)
    ax.set_xlabel("X")
    ax.set_ylabel("Y")
    ax.set_title("Mapa del turno final")
    ax.legend()
    ax.set_aspect("equal", "box")
    plt.tight_layout()
    plt.show()

# -------------------------------------------------------------------
# MAIN
# -------------------------------------------------------------------

if __name__ == "__main__":
    res = simular()

    print("Rol más rico:", res["rol_mas_rico"])
    print("Rol más longevo:", res["rol_mas_longevo"])
    print("Rol más violento:", res["rol_mas_violento"])
    print("Territorio con más muertes:", res["territorio_mas_letal"])
    print("Comercios por turno:", res["media_comercio_por_turno"])

    # --- gráficas ---
    graficar_evolucion_roles(res["historia_roles"])
    graficar_riqueza_por_rol(res["historia_riqueza"])
    graficar_muertes(res["muertes_por_rol"])
    mapa_final(res["personas"], res["territorios"], res["monedas"],
               GRID_ANCHO, GRID_ALTO)
