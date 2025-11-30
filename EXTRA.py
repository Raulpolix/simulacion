from time import time, sleep
import tkinter as tk

# -------- Pseudo-azar SIN 'random' --------
class PseudoAzar:
    def __init__(self, semilla=None):
        self.s = semilla if semilla is not None else int(time() * 1000)

    def next_u32(self):
        tms = int(time() * 1000)
        # mezcla tipo xorshift + LCG simple
        self.s ^= (tms & 0xFFFFFFFF)
        self.s ^= (self.s << 13) & 0xFFFFFFFF
        self.s ^= (self.s >> 17)
        self.s ^= (self.s << 5) & 0xFFFFFFFF
        self.s = (1103515245 * self.s + 12345) & 0xFFFFFFFF
        return self.s

    def indice(self, modulo: int) -> int:
        return self.next_u32() % modulo

    def rand01(self) -> float:
        return (self.next_u32() & 0xFFFFFF) / float(0x1000000)


# -------- Lógica de movimiento --------
class Desplazamiento:
    # 8 direcciones + quedarse
    OPC = [(-1, 0), (1, 0), (0, -1), (0, 1),
           (-1, -1), (-1, 1), (1, -1), (1, 1),
           (0, 0)]

    def __init__(self, rng: PseudoAzar):
        self.rng = rng

    def paso_aleatorio(self):
        return self.OPC[self.rng.indice(len(self.OPC))]

    def paso_hacia(self, x, y, tx, ty):
        dx = 0 if x == tx else (1 if tx > x else -1)
        dy = 0 if y == ty else (1 if ty > y else -1)
        return (dx, dy)


# -------- Agente --------
class Persona:
    def __init__(self, nombre, x, y, rng, ancho, alto, energia=10, ideas=1):
        self.nombre = nombre
        self.ancho, self.alto = ancho, alto
        self.x, self.y = 0, 0
        self.set_pos(x, y)     # usar siempre esto
        self.energia = energia
        self.ideas = ideas
        self.move = Desplazamiento(rng)
        self.rng = rng

    def set_pos(self, x, y):
        self.x = x % self.ancho
        self.y = y % self.alto

    def posicion(self):
        return (self.x, self.y)

    def mover_hacia(self, objetivo):
        dx, dy = self.move.paso_hacia(self.x, self.y, *objetivo)
        self.set_pos(self.x + dx, self.y + dy)

    def mover_aleatorio(self):
        dx, dy = self.move.paso_aleatorio()
        self.set_pos(self.x + dx, self.y + dy)

    def paso(self, vecinos):
        """4 pasos por tick, 60% sesgo a acercarse al más cercano"""
        for _ in range(4):
            if vecinos:
                tx, ty = min(vecinos, key=lambda p: abs(p[0] - self.x) + abs(p[1] - self.y))
                if self.rng.rand01() < 0.6:
                    self.mover_hacia((tx, ty))
                else:
                    self.mover_aleatorio()
            else:
                self.mover_aleatorio()

    def interactuar(self, otra, nombre_nuevo_cb):
        """
        Interacción: varias mini-acciones.
        Si en total se transfieren >=2 puntos de energía en este encuentro,
        nace una nueva persona en la misma celda.
        """
        print(f"\n🤝 {self.nombre} y {otra.nombre} se encuentran en {self.posicion()}")
        energia_transferida = 0
        nuevos = []

        for _ in range(3):  # tres mini-acciones
            accion = self.rng.indice(4)
            if accion == 0:
                # cooperación
                self.energia += 1
                otra.energia += 1
                print(f"   🔧 Cooperan → {self.nombre}:{self.energia} | {otra.nombre}:{otra.energia}")

            elif accion == 1:
                # debate
                if self.energia > 0:
                    self.energia -= 1
                if otra.energia > 0:
                    otra.energia -= 1
                print(f"   🗣 Debaten → {self.nombre}:{self.energia} | {otra.nombre}:{otra.energia}")

            elif accion == 2:
                # trueque de ideas
                if self.ideas > 0:
                    self.ideas -= 1
                    otra.ideas += 1
                    print(f"   🔄 {self.nombre} comparte una idea → {self.nombre}:{self.ideas} | {otra.nombre}:{otra.ideas}")
                elif otra.ideas > 0:
                    otra.ideas -= 1
                    self.ideas += 1
                    print(f"   🔄 {otra.nombre} comparte una idea → {self.nombre}:{self.ideas} | {otra.nombre}:{otra.ideas}")
                else:
                    print("   🤷 No tenían ideas que intercambiar.")

            else:
                # transferencia de energía (cuenta)
                if int(time() * 1000) % 2 == 0 and self.energia > 0:
                    self.energia -= 1
                    otra.energia += 1
                    energia_transferida += 1
                    print(f"   ⚡ {self.nombre} cede 1 energía → {self.nombre}:{self.energia} | {otra.nombre}:{otra.energia}")
                elif otra.energia > 0:
                    otra.energia -= 1
                    self.energia += 1
                    energia_transferida += 1
                    print(f"   ⚡ {otra.nombre} cede 1 energía → {self.nombre}:{self.energia} | {otra.nombre}:{otra.energia}")

            # nacimiento
            if energia_transferida >= 2 and not nuevos:
                nombre = nombre_nuevo_cb()
                bebe = Persona(nombre, self.x, self.y, self.rng,
                               ancho=self.ancho, alto=self.alto,
                               energia=5, ideas=1)
                print(f"   👶 Nace {nombre} en {bebe.posicion()} (E5, I1)")
                nuevos.append(bebe)

        return nuevos


# -------- Simulador (CONEXIÓN entre lógica y GUI) --------
class Simulador:
    def __init__(self, ancho=4, alto=4):
        self.ancho = ancho
        self.alto = alto
        self.rng = PseudoAzar()

        # contador para nombres de nuevos agentes
        self._contador_nuevos = {"n": 1}

        def nombre_nuevo():
            n = self._contador_nuevos["n"]
            self._contador_nuevos["n"] += 1
            return f"Nuevo{n}"

        self.nombre_nuevo = nombre_nuevo

        # lista de personas
        self.personas = [
            Persona("Ana", 0, 0, self.rng, ancho, alto),
            Persona("Luis", 1, 1, self.rng, ancho, alto),
            Persona("Iris", 2, 2, self.rng, ancho, alto),
            Persona("Omar", 3, 3, self.rng, ancho, alto),
        ]

        self._ultima_interacciones = []  # para que la GUI dibuje líneas rojas

    def step(self):
        """Un 'tick' de simulación."""
        # mover todos
        posiciones = [p.posicion() for p in self.personas]
        for idx, p in enumerate(self.personas):
            otros = posiciones[:idx] + posiciones[idx + 1:]
            p.paso(otros)

        # validación de límites
        for p in self.personas:
            assert 0 <= p.x < p.ancho and 0 <= p.y < p.alto, (p.nombre, p.posicion(), p.ancho, p.alto)

        # estado por consola (opcional)
        estado = " | ".join(f"{p.nombre}:{p.posicion()} E{p.energia} I{p.ideas}" for p in self.personas)
        print(f"[Tablero {self.ancho}x{self.alto}] {estado}")

        # encuentros
        nacimientos = []
        interacciones = []
        for i in range(len(self.personas)):
            for j in range(i + 1, len(self.personas)):
                if self.personas[i].posicion() == self.personas[j].posicion():
                    interacciones.append((self.personas[i], self.personas[j]))
                    nac = self.personas[i].interactuar(self.personas[j], self.nombre_nuevo)
                    nacimientos.extend(nac)

        if nacimientos:
            self.personas.extend(nacimientos)

        self._ultima_interacciones = interacciones

    def obtener_interacciones(self):
        """Usado por la GUI para dibujar líneas entre agentes que se encuentran."""
        return self._ultima_interacciones


# --------- PARTE GUI (Tkinter) ---------
GRID_SIZE = 4          # tamaño del espacio (4x4)
CELL_SIZE = 80         # tamaño de cada casilla en píxeles


class VentanaSimulacion:
    def __init__(self, simulador):
        self.sim = simulador

        # Crear ventana
        self.root = tk.Tk()
        self.root.title("Simulación 4x4")

        # Canvas donde dibujamos el grid y los elementos
        w = GRID_SIZE * CELL_SIZE
        h = GRID_SIZE * CELL_SIZE
        self.canvas = tk.Canvas(self.root, width=w, height=h)
        self.canvas.pack()

        # Botones
        frame = tk.Frame(self.root)
        frame.pack(pady=5)
        tk.Button(frame, text="Paso", command=self.un_paso).pack(side=tk.LEFT, padx=5)
        tk.Button(frame, text="Auto", command=self.modo_auto).pack(side=tk.LEFT, padx=5)
        tk.Button(frame, text="Parar", command=self.parar_auto).pack(side=tk.LEFT, padx=5)

        self.auto = False

        # Dibujar inicial
        self.dibujar()

    # ---------------------- DIBUJO ----------------------------

    def dibujar(self):
        self.canvas.delete("all")     # limpia canvas
        self.dibujar_grid()
        self.dibujar_personas()
        self.dibujar_interacciones()

    def dibujar_grid(self):
        for i in range(GRID_SIZE + 1):
            x = i * CELL_SIZE
            y = i * CELL_SIZE

            # Líneas verticales
            self.canvas.create_line(x, 0, x, GRID_SIZE * CELL_SIZE, width=2)

            # Líneas horizontales
            self.canvas.create_line(0, y, GRID_SIZE * CELL_SIZE, y, width=2)

    def dibujar_personas(self):
        """Dibuja cada persona como un círculo con su nombre."""
        for p in self.sim.personas:
            cx = p.x * CELL_SIZE + CELL_SIZE / 2
            cy = p.y * CELL_SIZE + CELL_SIZE / 2
            r = CELL_SIZE * 0.3

            self.canvas.create_oval(
                cx - r, cy - r, cx + r, cy + r,
                fill="lightblue", outline="black", width=2
            )
            self.canvas.create_text(cx, cy, text=p.nombre)

    def dibujar_interacciones(self):
        """Dibuja líneas rojas entre personas que se han encontrado en el último step()."""
        interacciones = self.sim.obtener_interacciones()

        for p1, p2 in interacciones:
            x1 = p1.x * CELL_SIZE + CELL_SIZE / 2
            y1 = p1.y * CELL_SIZE + CELL_SIZE / 2
            x2 = p2.x * CELL_SIZE + CELL_SIZE / 2
            y2 = p2.y * CELL_SIZE + CELL_SIZE / 2

            self.canvas.create_line(x1, y1, x2, y2, width=3, fill="red")

    # ------------------ CONTROL DEL TIEMPO --------------------

    def un_paso(self):
        self.sim.step()   # aquí llamas tu lógica
        self.dibujar()

    def modo_auto(self):
        self.auto = True
        self.loop_auto()

    def parar_auto(self):
        self.auto = False

    def loop_auto(self):
        if self.auto:
            self.un_paso()
            self.root.after(500, self.loop_auto)

    def ejecutar(self):
        self.root.mainloop()


# -------- Punto de entrada --------
if __name__ == "__main__":
    print(">>> Entrando en main()")
    sim = Simulador(ancho=GRID_SIZE, alto=GRID_SIZE)
    print(">>> Simulador creado, lanzando ventana...")
    app = VentanaSimulacion(sim)
    app.ejecutar()
