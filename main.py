"""
Servidor HTTP concurrente en Python
------------------------------------
Inicia un servidor HTTP simple usando hilos para manejar múltiples conexiones al mismo tiempo.
"""

import argparse
import logging
import threading
import time

from server.config import HOST, PORT, DEBUG_MODE, logger
from server.core.http_server import ThreadingHTTPServer
from server.core.handler import HTTPRequestHandler
from server.core.procesador import ProcesadorCola


def iniciar_servidor(host='localhost', puerto=8080, debug=False):
    """
    Inicia el servidor HTTP y el procesador de la cola de tareas en hilos separados.

    Args:
        host (str): Dirección del host.
        puerto (int): Puerto en el que se ejecutará el servidor.
        debug (bool): Activa el modo de depuración.
    """
    if debug:
        logger.setLevel(logging.DEBUG)

    try:
        # Crear el servidor HTTP
        server = ThreadingHTTPServer((host, puerto), HTTPRequestHandler)

        # Iniciar el procesador de fondo para gestionar la cola de tareas
        procesador = ProcesadorCola(HTTPRequestHandler.recursos)
        procesador.start()

        # Levantar el servidor en un hilo para permitir la interrupción con Ctrl+C
        thread_server = threading.Thread(target=server.serve_forever, daemon=True)
        thread_server.start()

        logger.info(f"Servidor HTTP activo en http://{host}:{puerto}/")
        logger.info("Presiona Ctrl+C para detenerlo")

        # Mantener el hilo principal activo
        while True:
            time.sleep(1)

    except KeyboardInterrupt:
        logger.info("Detención solicitada por el usuario.")
    except Exception as e:
        logger.error(f"Error al arrancar el servidor: {e}")
    finally:
        try:
            server.shutdown()
            server.server_close()
            procesador.stop()
            logger.info("Servidor cerrado correctamente.")
        except UnboundLocalError:
            pass


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Servidor HTTP multithread en Python"
    )
    parser.add_argument(
        "--host",
        default="localhost",
        help="Dirección del host (por defecto: localhost)"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="Puerto del servidor (por defecto: 8000)"
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Activa logs en modo debug"
    )

    args = parser.parse_args()
    iniciar_servidor(host=args.host, puerto=args.port, debug=args.debug)
