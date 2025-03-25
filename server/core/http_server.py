

import socketserver
from ..config import logger


class ThreadingHTTPServer(socketserver.ThreadingTCPServer):

    allow_reuse_address = True
    daemon_threads = False

    def __init__(self, server_address, RequestHandlerClass, bind_and_activate=True):
        super().__init__(server_address, RequestHandlerClass, bind_and_activate)
        logger.info(f"Servidor iniciado en {server_address[0]}:{server_address[1]}")
        logger.info("Presione Ctrl+C para detener el servidor")

    def handle_error(self, request, client_address):
        logger.error(f"Error al manejar solicitud de {client_address}", exc_info=True)