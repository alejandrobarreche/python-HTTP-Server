import threading
import queue
import time
from ..config import logger


class ProcesadorCola(threading.Thread):
    """
    Hilo de fondo que procesa la cola de solicitudes.

    Este thread se encarga de obtener solicitudes de la cola, simular su procesamiento
    y registrar la operación realizada, demostrando el uso de colas para la comunicación
    entre threads.
    """

    def __init__(self, recursos):
        """
        Inicializa el procesador de cola.

        Args:
            recursos: Objeto que contiene la cola de solicitudes y otros recursos compartidos.
        """
        super().__init__(daemon=True)
        self.recursos = recursos
        self.running = True
        self.name = "ProcesadorCola"

    def run(self):
        """
        Ejecuta el procesamiento continuo de la cola de solicitudes.

        Obtiene elementos de la cola con un timeout, simula el procesamiento y marca
        cada tarea como completada.
        """
        logger.info(f"Iniciando {self.name}")
        while self.running:
            try:
                # Obtener un elemento de la cola con timeout para permitir la finalización
                solicitud = self.recursos.cola_solicitudes.get(timeout=1)

                # Simulación del procesamiento de la solicitud
                time.sleep(0.1)

                # Registrar la solicitud procesada (se muestra solo los primeros 50 caracteres)
                logger.debug(f"Procesada solicitud: {solicitud[:50]}...")

                # Marcar la tarea como completada
                self.recursos.cola_solicitudes.task_done()
            except queue.Empty:
                # No hay solicitudes en la cola, continuar esperando
                continue
            except Exception as e:
                logger.error(f"Error en {self.name}: {str(e)}")

    def stop(self):
        """
        Detiene el procesador de la cola.
        """
        self.running = False
        logger.info(f"Deteniendo {self.name}")
