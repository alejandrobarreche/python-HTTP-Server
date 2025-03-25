import socketserver
from ..config import logger


class ThreadingHTTPServer(socketserver.ThreadingTCPServer):
    """
    Servidor HTTP concurrente basado en ThreadingTCPServer.

    Permite reutilizar la dirección y configura el manejo de errores de las solicitudes.
    """

    allow_reuse_address = True
    daemon_threads = False

    def __init__(self, server_address, RequestHandlerClass, bind_and_activate=True):
        """
        Inicializa el servidor y muestra mensajes de inicio.

        Args:
            server_address (tuple): Tupla con (host, puerto) donde el servidor escuchará.
            RequestHandlerClass: Clase encargada de procesar las solicitudes entrantes.
            bind_and_activate (bool): Si True, enlaza y activa el servidor automáticamente.
        """
        super().__init__(server_address, RequestHandlerClass, bind_and_activate)
        logger.info(f"Servidor iniciado en {server_address[0]}:{server_address[1]}")
        logger.info("Presione Ctrl+C para detener el servidor")

    def handle_error(self, request, client_address):
        """
        Maneja errores durante la atención de solicitudes.

        Args:
            request: La solicitud que produjo el error.
            client_address: Dirección del cliente que realizó la solicitud.
        """
        logger.error(f"Error al manejar solicitud de {client_address}", exc_info=True)
