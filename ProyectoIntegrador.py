import threading
import time
import queue
import os
from dataclasses import dataclass, field
from typing import Dict, List, Optional

@dataclass(order=True)
class PCB:
    sort_index: int = field(init=False, repr=False)
    pid: int
    prioridad: int
    rafaga: int
    estado: str = field(default="Listo")
    restante: int = field(init=False)
    recursos: Dict[str, int] = field(default_factory=lambda: {"CPU": 0, "Memoria": 0})

    def __post_init__(self):
        self.restante = self.rafaga
        self.sort_index = self.prioridad

    def resumen(self):
        return f"[PID {self.pid}] Estado: {self.estado:<12} Prioridad: {self.prioridad:<3} Ráfaga Restante: {self.restante:<3} Recursos: {self.recursos}"

class Recursos:
    def __init__(self, cpu_total=1, mem_total=4096):
        self.cpu_total = cpu_total
        self.mem_total = mem_total
        self.cpu_libre = cpu_total
        self.mem_libre = mem_total

    def asignar(self, pcb: PCB, tipo: str, cantidad: int) -> bool:
        if tipo == "CPU" and self.cpu_libre >= cantidad:
            self.cpu_libre -= cantidad
            pcb.recursos["CPU"] += cantidad
            return True
        elif tipo == "Memoria" and self.mem_libre >= cantidad:
            self.mem_libre -= cantidad
            pcb.recursos["Memoria"] += cantidad
            return True
        return False

    def liberar(self, pcb: PCB):
        self.cpu_libre += pcb.recursos["CPU"]
        self.mem_libre += pcb.recursos["Memoria"]
        pcb.recursos = {"CPU": 0, "Memoria": 0}

    def estado(self) -> str:
        return f"CPU disponible: {self.cpu_libre}/{self.cpu_total} | Memoria disponible: {self.mem_libre}/{self.mem_total} MB"

class Kernel:
    def __init__(self, algoritmo: str, quantum: int = 2):
        self.algoritmo = algoritmo
        self.quantum = quantum
        self.procesos: Dict[int, PCB] = {}
        self.cola: List[PCB] = []
        self.recursos = Recursos()
        self.log: List[str] = []
        self.semaforo = threading.Semaphore(1)
        self.buzon: Dict[int, queue.Queue] = {}
        self.pid_counter = 1

    def log_evento(self, mensaje: str):
        t = time.strftime("%H:%M:%S")
        evento = f"[{t}] {mensaje}"
        self.log.append(evento)
        print(evento)

    def nuevo_proceso(self, prioridad: int, rafaga: int):
        pcb = PCB(pid=self.pid_counter, prioridad=prioridad, rafaga=rafaga)
        self.procesos[self.pid_counter] = pcb
        self.cola.append(pcb)
        self.log_evento(f"Proceso {pcb.pid} creado | Prioridad: {prioridad} | Ráfaga: {rafaga}")
        self.pid_counter += 1

    def ordenar_cola(self):
        if self.algoritmo == "SJF":
            self.cola.sort(key=lambda p: p.restante)
        elif self.algoritmo == "Prioridad":
            self.cola.sort(key=lambda p: -p.prioridad)
        elif self.algoritmo == "FCFS":
            self.cola.sort(key=lambda p: p.pid)

    def ejecutar(self):
        self.ordenar_cola()
        while self.cola:
            proc = self.cola.pop(0)
            if not self.recursos.asignar(proc, "CPU", 1):
                self.log_evento(f"Recurso insuficiente: CPU no disponible para Proceso {proc.pid}. Reprogramado.")
                self.cola.append(proc)
                continue
            proc.estado = "Ejecutando"
            uso = min(proc.restante, self.quantum) if self.algoritmo == "RR" else proc.restante
            self.log_evento(f"Ejecutando Proceso {proc.pid} durante {uso} unidades de tiempo...")
            time.sleep(0.1 * uso)
            proc.restante -= uso
            self.recursos.liberar(proc)
            if proc.restante <= 0:
                proc.estado = "Terminado"
                self.log_evento(f"Proceso {proc.pid} finalizado exitosamente.")
            else:
                proc.estado = "Listo"
                self.cola.append(proc)

    def enviar_mensaje(self, de_pid: int, a_pid: int, mensaje: str):
        if a_pid not in self.buzon:
            self.buzon[a_pid] = queue.Queue()
        self.buzon[a_pid].put((de_pid, mensaje))
        self.log_evento(f"Mensaje enviado de PID {de_pid} a PID {a_pid}: '{mensaje}'")

    def recibir_mensaje(self, pid: int):
        if pid in self.buzon and not self.buzon[pid].empty():
            de_pid, mensaje = self.buzon[pid].get()
            self.log_evento(f"PID {pid} recibió mensaje de PID {de_pid}: '{mensaje}'")
        else:
            self.log_evento(f"PID {pid} no tiene mensajes nuevos.")

    def productor_consumidor(self):
        buffer = []

        def productor():
            for i in range(3):
                self.semaforo.acquire()
                buffer.append(f"item-{i}")
                self.log_evento(f"Productor generó item-{i}")
                self.semaforo.release()
                time.sleep(0.1)

        def consumidor():
            for _ in range(3):
                self.semaforo.acquire()
                if buffer:
                    item = buffer.pop(0)
                    self.log_evento(f"Consumidor procesó {item}")
                self.semaforo.release()
                time.sleep(0.1)

        threading.Thread(target=productor).start()
        threading.Thread(target=consumidor).start()

    def mostrar_procesos(self):
        print("\n== Procesos Actuales ==")
        for pcb in self.procesos.values():
            print(pcb.resumen())

    def mostrar_log(self):
        print("\n== Bitácora de Eventos ==")
        for evento in self.log:
            print(evento)

    def estado_recursos(self):
        print("\n== Estado de Recursos ==")
        print(self.recursos.estado())

# === CLI ===
def menu():
    os.system('cls' if os.name == 'nt' else 'clear')
    print("""
<3 _===============================================_ <3
     ´SIMULADOR AVANZADO DE SISTEMA OPERATIVO´
           "Guzman Garcia Lizbeth Neri"
<3 _===============================================_ <3
""")
    print("Seleccione algoritmo de planificación:")
    print("1. FCFS\n2. SJF\n3. Round Robin\n4. Por Prioridad")
    opc = input("Opción: ")
    algoritmo = {"1": "FCFS", "2": "SJF", "3": "RR", "4": "Prioridad"}.get(opc, "FCFS")
    quantum = int(input("Quantum (si aplica): ")) if algoritmo == "RR" else 2
    return Kernel(algoritmo, quantum)

if __name__ == '__main__':
    kernel = menu()

    while True:
        print("""
<3 _================ MENÚ PRINCIPAL ================_ <3
1. Crear nuevo proceso
2. Ejecutar planificación
3. Enviar mensaje entre procesos
4. Recibir mensaje entre procesos
5. Productor/Consumidor
6. Ver procesos activos
7. Ver estado de recursos
8. Ver log
9. Salir
<3 _===============================================_ <3
        """)
        op = input("Seleccione opción: ")

        if op == "1":
            pri = int(input("Prioridad: "))
            raf = int(input("Ráfaga de CPU: "))
            kernel.nuevo_proceso(pri, raf)
        elif op == "2":
            kernel.ejecutar()
        elif op == "3":
            de = int(input("PID Emisor: "))
            a = int(input("PID Receptor: "))
            m = input("Mensaje: ")
            kernel.enviar_mensaje(de, a, m)
        elif op == "4":
            p = int(input("PID receptor: "))
            kernel.recibir_mensaje(p)
        elif op == "5":
            kernel.productor_consumidor()
        elif op == "6":
            kernel.mostrar_procesos()
        elif op == "7":
            kernel.estado_recursos()
        elif op == "8":
            kernel.mostrar_log()
        elif op == "9":
            print("Gracias por usar el simulador avanzado. Hasta pronto!")
            break
        else:
            print("Opción inválida. Intente nuevamente.")
