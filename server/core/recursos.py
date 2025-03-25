from datetime import datetime
import threading
import queue
from typing import Dict, List

from ..config import logger


class RecursosCompartidos:
    """
    Gestiona los recursos compartidos del servidor, incluyendo el contador de solicitudes,
    almacenamiento de datos, cola de solicitudes y registro de solicitudes realizadas.
    """

    def __init__(self):
        self.lock = threading.Lock()
        self.semaforo_datos = threading.Semaphore(1)
        self.contador_solicitudes = 0
        self.datos = []
        self.max_datos = 100
        self.cola_solicitudes = queue.Queue(maxsize=50)
        self.solicitudes_realizadas = []  # Lista para rastrear solicitudes
        self.max_solicitudes = 1000  # Límite para evitar consumo excesivo de memoria

    def registrar_solicitud(self, ip: str, metodo: str, ruta: str) -> None:
        """
        Registra una solicitud realizada al servidor.

        Args:
            ip (str): Dirección IP del cliente.
            metodo (str): Método HTTP utilizado.
            ruta (str): Ruta solicitada.
        """
        solicitud = {
            "timestamp": datetime.now().isoformat(),
            "ip": ip,
            "metodo": metodo,
            "ruta": ruta
        }

        with self.lock:
            if len(self.solicitudes_realizadas) >= self.max_solicitudes:
                # Eliminar la solicitud más antigua si se supera el límite
                self.solicitudes_realizadas.pop(0)
            self.solicitudes_realizadas.append(solicitud)

    def obtener_solicitudes(self) -> List[Dict]:
        """
        Obtiene una copia de las solicitudes realizadas.

        Returns:
            List[Dict]: Lista de solicitudes.
        """
        with self.lock:
            return self.solicitudes_realizadas.copy()

    def incrementar_contador(self) -> int:
        """
        Incrementa el contador de solicitudes de forma segura.

        Returns:
            int: El nuevo valor del contador.
        """
        with self.lock:
            self.contador_solicitudes += 1
            return self.contador_solicitudes

    def agregar_dato(self, dato: Dict) -> bool:
        """
        Agrega un dato a la lista. Si se alcanza el límite, elimina el dato más antiguo.

        Args:
            dato (Dict): Dato a agregar.

        Returns:
            bool: True si el dato se agregó correctamente.
        """
        with self.semaforo_datos:
            if len(self.datos) >= self.max_datos:
                self.datos.pop(0)
            self.datos.append(dato)
            return True

    def obtener_datos(self) -> List[Dict]:
        """
        Obtiene una copia de los datos almacenados.

        Returns:
            List[Dict]: Lista de datos.
        """
        with self.semaforo_datos:
            return self.datos.copy()

    def agregar_solicitud_a_cola(self, solicitud: str) -> bool:
        """
        Intenta agregar una solicitud a la cola con un timeout para evitar bloqueos indefinidos.

        Args:
            solicitud (str): Solicitud a agregar.

        Returns:
            bool: True si se agregó la solicitud, False si la cola está llena.
        """
        try:
            self.cola_solicitudes.put(solicitud, timeout=2)
            return True
        except queue.Full:
            logger.warning("Cola de solicitudes llena, descartando solicitud")
            return False

    def obtener_stats(self) -> Dict:
        """
        Retorna estadísticas del servidor.

        Returns:
            Dict: Estadísticas que incluyen total de solicitudes, cantidad de datos almacenados
                  y tamaño actual de la cola.
        """
        with self.lock:
            return {
                "total_solicitudes": self.contador_solicitudes,
                "datos_almacenados": len(self.datos),
                "tamano_cola": self.cola_solicitudes.qsize()
            }
