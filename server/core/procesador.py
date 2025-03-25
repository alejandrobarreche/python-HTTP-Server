
import threading
import queue
import time
from ..config import logger

# Procesador en segundo plano para la cola de solicitudes
class ProcesadorCola(threading.Thread):
    """
    Thread en segundo plano que procesa la cola de solicitudes.
    Demuestra el uso de colas para comunicación entre threads.
    """
    def __init__(self, recursos):
        super().__init__(daemon=True)
        self.recursos = recursos
        self.running = True
        self.name = "ProcesadorCola"

    def run(self):
        """Procesa elementos de la cola continuamente"""
        logger.info(f"Iniciando {self.name}")
        while self.running:
            try:
                # Obtener un elemento de la cola con timeout para permitir finalización
                solicitud = self.recursos.cola_solicitudes.get(timeout=1)

                # Simulación de procesamiento
                time.sleep(0.1)

                # Registrar procesamiento
                logger.debug(f"Procesada solicitud: {solicitud[:50]}...")

                # Marcar tarea como completada
                self.recursos.cola_solicitudes.task_done()
            except queue.Empty:
                # Timeout, verificar si debemos seguir ejecutando
                pass
            except Exception as e:
                logger.error(f"Error en {self.name}: {str(e)}")

    def stop(self):
        """Detiene el procesador de cola"""
        self.running = False
        logger.info(f"Deteniendo {self.name}")
