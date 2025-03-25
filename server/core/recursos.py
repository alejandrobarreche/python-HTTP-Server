from datetime import datetime
import threading
import queue
from typing import Dict, List
from ..config import logger


# Recurso compartido: contador de solicitudes y datos simulados
class RecursosCompartidos:
    def __init__(self):
        self.lock = threading.Lock()
        self.semaforo_datos = threading.Semaphore(1)
        self.contador_solicitudes = 0
        self.datos = []
        self.max_datos = 100
        self.cola_solicitudes = queue.Queue(maxsize=50)
        self.solicitudes_realizadas = []  # Nueva lista para trackear solicitudes
        self.max_solicitudes = 1000  # Límite para evitar consumo excesivo de memoria

    def registrar_solicitud(self, ip: str, metodo: str, ruta: str) -> None:
        """Registra una solicitud realizada al servidor"""
        solicitud = {
            "timestamp": datetime.now().isoformat(),
            "ip": ip,
            "metodo": metodo,
            "ruta": ruta
        }

        # Usar lock para modificar lista de solicitudes de forma segura
        with self.lock:
            if len(self.solicitudes_realizadas) >= self.max_solicitudes:
                # Eliminar la solicitud más antigua si se supera el límite
                self.solicitudes_realizadas.pop(0)
            self.solicitudes_realizadas.append(solicitud)

    def obtener_solicitudes(self) -> List[Dict]:
        """Obtiene una copia de las solicitudes realizadas"""
        with self.lock:
            return self.solicitudes_realizadas.copy()


    def incrementar_contador(self) -> int:
        with self.lock:  # Evitar condiciones de carrera
            self.contador_solicitudes += 1
            return self.contador_solicitudes



    def agregar_dato(self, dato: Dict) -> bool:
        self.semaforo_datos.acquire()
        try:
            if len(self.datos) >= self.max_datos:
                # Evitar crecimiento ilimitado eliminando el dato más antiguo
                self.datos.pop(0)
            self.datos.append(dato)
            return True
        finally:
            # Garantiza liberación del semáforo incluso si ocurre una excepción
            self.semaforo_datos.release()



    def obtener_datos(self) -> List[Dict]:
        self.semaforo_datos.acquire()
        try:
            # Devolver una copia para evitar modificaciones externas
            return self.datos.copy()
        finally:
            self.semaforo_datos.release()



    def agregar_solicitud_a_cola(self, solicitud: str) -> bool:
        try:
            # Intenta agregar a la cola con timeout para evitar bloqueos indefinidos
            self.cola_solicitudes.put(solicitud, timeout=2)
            return True
        except queue.Full:
            logger.warning("Cola de solicitudes llena, descartando solicitud")
            return False



    def obtener_stats(self) -> Dict:
        with self.lock:
            return {
                "total_solicitudes": self.contador_solicitudes,
                "datos_almacenados": len(self.datos),
                "tamano_cola": self.cola_solicitudes.qsize()
            }


