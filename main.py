"""
Servidor HTTP Concurrente en Python
-----------------------------------
Este módulo implementa un servidor HTTP sencillo que utiliza threads para manejar múltiples
conexiones concurrentes.
"""
import argparse
import logging
import threading
import time

from server.config import HOST, PORT, DEBUG_MODE, logger
from server.core.http_server import ThreadingHTTPServer
from server.core.handler import HTTPRequestHandler
from server.core.procesador import ProcesadorCola

# Función principal para iniciar el servidor
def iniciar_servidor(host='localhost', puerto=8080, debug=False):
    """Inicia el servidor HTTP concurrente"""
    # Configurar nivel de logging según modo debug
    if debug:
        logger.setLevel(logging.DEBUG)

    try:
        # Crear servidor
        servidor = ThreadingHTTPServer((host, puerto), HTTPRequestHandler)

        # Iniciar procesador de cola en segundo plano
        procesador = ProcesadorCola(HTTPRequestHandler.recursos)
        procesador.start()

        # Iniciar servidor en un thread separado para poder capturar Ctrl+C
        server_thread = threading.Thread(target=servidor.serve_forever, daemon=True)
        server_thread.start()

        logger.info(f"Servidor HTTP concurrente corriendo en http://{host}:{puerto}/")
        logger.info(f"Presione Ctrl+C para detener el servidor")

        # Mantener el programa principal ejecutándose
        while True:
            time.sleep(1)

    except KeyboardInterrupt:
        logger.info("Interrupción de teclado recibida, cerrando servidor...")
    except Exception as e:
        logger.error(f"Error al iniciar servidor: {str(e)}")
    finally:
        # Cleanup
        try:
            servidor.shutdown()
            servidor.server_close()
            procesador.stop()
            logger.info("Servidor detenido correctamente")
        except UnboundLocalError:
            # Si el servidor no llegó a crearse
            pass

# Punto de entrada si se ejecuta como script
if __name__ == "__main__":
    # Configurar argumentos de línea de comandos
    parser = argparse.ArgumentParser(description="Servidor HTTP Concurrente en Python")
    parser.add_argument("--host", default="localhost", help="Dirección de host (default: localhost)")
    parser.add_argument("--port", type=int, default=8000, help="Puerto (default: 8000)")
    parser.add_argument("--debug", action="store_true", help="Activa modo debug con logging detallado")

    args = parser.parse_args()

    # Iniciar servidor con los parámetros especificados
    iniciar_servidor(host=args.host, puerto=args.port, debug=args.debug)