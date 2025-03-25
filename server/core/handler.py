import json
import os
import platform
import socket
import threading
import time
import uuid
import base64

import psutil
from datetime import datetime
from http import HTTPStatus
from socketserver import BaseRequestHandler
from typing import Tuple, Dict, List

import plotly.graph_objs as go
import plotly.offline as pyo

from ..config import logger
from .recursos import RecursosCompartidos
from ..utils.helpers import (
    generar_html_index,
    generar_html_status,
    guardar_peticion_en_archivo,
    obtener_info_recursos_compartidos,
    obtener_info_estadisticas_cliente,
    generar_html_estadisticas_cliente,
    generar_html_recursos
)


class HTTPRequestHandler(BaseRequestHandler):
    """
    Manejador de solicitudes HTTP que procesa peticiones concurrentemente.

    Este handler utiliza recursos compartidos para gestionar solicitudes, datos,
    y proveer endpoints para información del servidor, estadísticas, datos y solicitudes.
    """

    # Recursos compartidos para todos los manejadores
    recursos = RecursosCompartidos()
    # Semáforo para limitar el número máximo de conexiones concurrentes
    semaforo_conexiones = threading.BoundedSemaphore(20)

    @classmethod
    def generar_grafica_recursos(cls) -> str:
        """
        Genera una gráfica de recursos del sistema usando Plotly y devuelve
        el gráfico embebido en HTML.

        Returns:
            str: HTML con el gráfico generado.
        """
        try:
            # Obtener datos de recursos
            cpu_percent = psutil.cpu_percent(interval=1)
            memoria = psutil.virtual_memory()
            memoria_percent = memoria.percent

            # Crear figura con indicadores tipo Gauge para CPU y Memoria
            fig = go.Figure()
            fig.add_trace(
                go.Gauge(
                    domain={'x': [0, 1], 'y': [0, 1]},
                    value=cpu_percent,
                    mode="gauge+number",
                    title={'text': "Uso de CPU"},
                    gauge={
                        'axis': {'range': [0, 100]},
                        'bar': {'color': "darkblue"},
                        'steps': [
                            {'range': [0, 50], 'color': "lightgreen"},
                            {'range': [50, 75], 'color': "yellow"},
                            {'range': [75, 100], 'color': "red"},
                        ],
                    },
                )
            )
            fig.add_trace(
                go.Gauge(
                    domain={'x': [0, 1], 'y': [0, 1]},
                    value=memoria_percent,
                    mode="gauge+number",
                    title={'text': "Uso de Memoria"},
                    gauge={
                        'axis': {'range': [0, 100]},
                        'bar': {'color': "darkred"},
                        'steps': [
                            {'range': [0, 50], 'color': "lightblue"},
                            {'range': [50, 75], 'color': "orange"},
                            {'range': [75, 100], 'color': "red"},
                        ],
                    },
                )
            )

            # Configurar layout del gráfico
            fig.update_layout(
                title='Monitoreo de Recursos del Servidor',
                height=400,
                width=800,
                template='plotly_white',
            )

            # Convertir figura a HTML
            grafica_html = pyo.plot(fig, output_type='div', include_plotlyjs='cdn')
            return grafica_html

        except Exception as e:
            logger.error(f"Error generando gráfica de recursos: {e}")
            return f"<p>Error generando gráfica: {e}</p>"

    def contar_solicitudes_por_metodo(self, solicitudes: List[Dict]) -> Dict:
        """
        Cuenta la cantidad de solicitudes realizadas por cada método HTTP.

        Args:
            solicitudes (List[Dict]): Lista de solicitudes.

        Returns:
            Dict: Diccionario con el conteo de solicitudes por método.
        """
        conteo = {}
        for solicitud in solicitudes:
            metodo = solicitud.get('metodo', 'Desconocido')
            conteo[metodo] = conteo.get(metodo, 0) + 1
        return conteo

    def agrupar_solicitudes_por_hora(self, solicitudes: List[Dict]) -> Dict:
        """
        Agrupa las solicitudes por la hora en que fueron realizadas.

        Args:
            solicitudes (List[Dict]): Lista de solicitudes.

        Returns:
            Dict: Diccionario con la agrupación de solicitudes por hora.
        """
        agrupacion = {}
        for solicitud in solicitudes:
            # Extraer la hora a partir del timestamp
            hora = datetime.fromisoformat(
                solicitud.get('timestamp', datetime.now().isoformat())
            ).strftime("%H")
            agrupacion[hora] = agrupacion.get(hora, 0) + 1
        return dict(sorted(agrupacion.items()))

    def handle(self) -> None:
        """
        Procesa una solicitud HTTP.

        Controla el acceso concurrente mediante un semáforo, incrementa el contador
        de solicitudes, registra la solicitud, y dirige la petición al manejador
        correspondiente según la ruta y el método HTTP.
        """
        with self.semaforo_conexiones:
            # Incrementar contador de solicitudes de forma segura
            num_solicitud = self.recursos.incrementar_contador()
            client_address = self.client_address[0]
            logger.info(f"Conexión desde {client_address} - Solicitud #{num_solicitud}")

            try:
                # Recibir datos del cliente
                data = self.request.recv(1024).strip()
                if not data:
                    return

                request_text = data.decode('utf-8')
                method, path, _ = self.parse_request(request_text)

                # Registrar y encolar la solicitud
                self.recursos.agregar_solicitud_a_cola(request_text)
                self.recursos.registrar_solicitud(client_address, method, path)

                # Volver a analizar la solicitud para procesar la petición
                method, path, _ = self.parse_request(request_text)

                if method == "GET":
                    if path == "/" or path == "/index":
                        self.handle_index()
                    elif path == "/status":
                        self.handle_status()
                    elif path == "/api/status":
                        self.handle_api_status()
                    elif path == "/data":
                        self.handle_data()
                    elif path == "/api/data":
                        self.handle_api_data()
                    elif path == "/solicitudes":
                        self.handle_solicitudes()
                    elif path == "/api/solicitudes":
                        self.handle_api_solicitudes()
                    elif path.startswith("/sleep/"):
                        try:
                            seconds = int(path.split("/")[2])
                            self.handle_sleep(seconds)
                        except (IndexError, ValueError):
                            self.send_error(400, "Parámetro inválido")
                    else:
                        self.send_error(404, "Ruta no encontrada")
                elif method == "POST" and path == "/data":
                    self.handle_post_data(request_text)
                else:
                    self.send_error(405, "Método no permitido")

            except Exception as e:
                logger.error(f"Error al procesar solicitud: {str(e)}")
                self.send_error(500, "Error interno del servidor")

    def generar_pagina_html(self, titulo: str, contenido: Dict, endpoint: str = None) -> str:
        """
        Genera una página HTML con un estilo definido y enlaces a los endpoints.

        Args:
            titulo (str): Título de la página.
            contenido (Dict): Contenido adicional (usado en el template).
            endpoint (str, optional): URL para ver el JSON de la información. Defaults to None.

        Returns:
            str: Página HTML generada.
        """
        html_template = f"""
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <title>{titulo}</title>
    <style>
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: #ecf0f1;
            margin: 0;
            padding: 0;
        }}
        header {{
            background: #2c3e50;
            color: white;
            padding: 20px;
            text-align: center;
        }}
        .container {{
            max-width: 900px;
            margin: 30px auto;
            padding: 20px;
            background: white;
            border-radius: 10px;
            box-shadow: 0 4px 10px rgba(0, 0, 0, 0.1);
        }}
        .endpoint {{
            border-left: 6px solid #3498db;
            background: #f9f9f9;
            padding: 15px 20px;
            margin-bottom: 20px;
            border-radius: 6px;
        }}
        .endpoint h3 {{
            margin: 0;
            color: #2980b9;
        }}
        .endpoint p {{
            margin: 5px 0 0;
            color: #7f8c8d;
        }}
        .json-link {{
            margin-top: 10px;
            display: inline-block;
            color: #27ae60;
            text-decoration: none;
        }}
        nav a {{
            margin-right: 15px;
            color: #2980b9;
            text-decoration: none;
        }}
        .timestamp {{
            font-size: 0.9em;
            color: #999;
            margin-top: 30px;
            text-align: right;
        }}
    </style>
</head>
<body>
    <header>
        <h1>🚀 Servidor HTTP Concurrente</h1>
        <p>Procesamiento rápido y concurrente con Python</p>
    </header>
    <div class="container">
        <h2>{titulo}</h2>
        <div class="endpoint">
            <h3>📄 / (Raíz)</h3>
            <p>Bienvenida al servidor, muestra información general</p>
        </div>
        <div class="endpoint">
            <h3>📊 /status</h3>
            <p>Estado en tiempo real y métricas del servidor</p>
        </div>
        <div class="endpoint">
            <h3>🔄 /data (GET & POST)</h3>
            <p>Obtiene o almacena datos estructurados</p>
        </div>
        <div class="endpoint">
            <h3>⏳ /sleep/[segundos]</h3>
            <p>Simula tiempo de espera para pruebas de concurrencia</p>
        </div>
        <div class="endpoint">
            <h3>🧾 /solicitudes</h3>
            <p>Lista de solicitudes recibidas por el servidor</p>
        </div>
        <div class="endpoint">
            <h3>🛠 /api/*</h3>
            <p>Versiones API en JSON para status, data y solicitudes</p>
        </div>
        <nav>
            <a href="/">🏠 Inicio</a>
            <a href="/status">📊 Estado</a>
            <a href="/data">📂 Datos</a>
            <a href="/solicitudes">🧾 Solicitudes</a>
            {f'<a class="json-link" href="{endpoint}">Ver JSON 📄</a>' if endpoint else ''}
        </nav>
        <div class="timestamp">
            Generado: {datetime.now().isoformat()}
        </div>
    </div>
</body>
</html>
"""
        return html_template

    def parse_request(self, request_text: str) -> Tuple[str, str, str]:
        """
        Analiza la solicitud HTTP para extraer el método, la ruta y la versión.

        Args:
            request_text (str): Texto completo de la solicitud.

        Returns:
            Tuple[str, str, str]: Método HTTP, ruta y versión.
        """
        request_line = request_text.split('\r\n')[0]
        try:
            method, path, version = request_line.split()
            return method, path, version
        except ValueError:
            # En caso de error, retornar valores por defecto
            return "GET", "/", "HTTP/1.1"

    def send_response(self, status_code: int, content_type: str, content: str) -> None:
        """
        Envía una respuesta HTTP al cliente.

        Args:
            status_code (int): Código de estado HTTP.
            content_type (str): Tipo de contenido de la respuesta.
            content (str): Contenido del mensaje.
        """
        status_message = HTTPStatus(status_code).phrase
        headers = [
            f"HTTP/1.1 {status_code} {status_message}",
            f"Content-Type: {content_type}",
            f"Content-Length: {len(content)}",
            "Server: PythonConcurrentServer/1.0",
            "Connection: close",
            "\r\n",
        ]
        response = "\r\n".join(headers) + content
        self.request.sendall(response.encode())

    def send_error(self, status_code: int, mensaje: str) -> None:
        """
        Envía una respuesta de error HTTP al cliente.

        Args:
            status_code (int): Código de error HTTP.
            mensaje (str): Mensaje de error.
        """
        error_data = json.dumps({"error": mensaje, "code": status_code})
        self.send_response(status_code, "application/json", error_data)

    def handle_index(self) -> None:
        """
        Maneja la ruta raíz del servidor.
        """
        contenido = {
            "mensaje": "Servidor HTTP Concurrente en Python",
            "endpoints": [
                {"ruta": "/", "descripcion": "Información del servidor"},
                {"ruta": "/status", "descripcion": "Estado y estadísticas del servidor"},
                {"ruta": "/data", "descripcion": "Acceso a datos (GET/POST)"},
                {"ruta": "/sleep/{seconds}", "descripcion": "Simula carga con espera"},
                {"ruta": "/api/status", "descripcion": "Status en formato JSON"},
                {"ruta": "/api/data", "descripcion": "Datos en formato JSON"},
                {"ruta": "/api/solicitudes", "descripcion": "Lista de solicitudes realizadas"},
            ],
            "timestamp": datetime.now().isoformat(),
        }
        html = generar_html_index("Servidor HTTP Concurrente", contenido)
        self.send_response(200, "text/html", html)

    def handle_status(self) -> None:
        """
        Maneja la ruta /status mostrando información detallada del servidor.
        """
        try:
            # Obtener estadísticas generales
            stats = self.recursos.obtener_stats()

            # Información del sistema
            system_info = {
                "sistema_operativo": platform.platform(),
                "nombre_host": socket.gethostname(),
                "arquitectura": platform.machine(),
                "version_python": platform.python_version(),
                "timestamp": datetime.now().isoformat(),
                "uuid_servidor": str(uuid.uuid4()),
            }

            # Información de threads y procesos
            thread_info = {
                "thread_actual": threading.current_thread().name,
                "threads_activos": threading.active_count(),
                "threads_daemon": sum(1 for t in threading.enumerate() if t.daemon),
                "proceso_pid": os.getpid(),
            }

            # Recursos del sistema
            recursos_sistema = {
                "cpu_cores": psutil.cpu_count(),
                "cpu_frecuencia": f"{psutil.cpu_freq().current:.2f} MHz",
                "memoria_total": f"{psutil.virtual_memory().total / (1024**3):.2f} GB",
                "memoria_disponible": f"{psutil.virtual_memory().available / (1024**3):.2f} GB",
                "memoria_porcentaje": f"{psutil.virtual_memory().percent}%",
            }

            servidor_info = {
                "ip_servidor": self.server.server_address[0],
                "puerto_servidor": self.server.server_address[1],
                "clase_servidor": self.server.__class__.__name__,
                "tipo_handler": self.__class__.__name__,
            }

            # Generar página HTML con información del servidor
            html = generar_html_status(
                "Estado Detallado del Servidor",
                stats,
                system_info,
                thread_info,
                servidor_info,
                recursos_sistema,
                "/api/status",
            )
            self.send_response(200, "text/html", html)

        except Exception as e:
            logger.error(f"Error en handle_status: {e}")
            self.send_error(500, f"Error interno: {e}")

    def handle_api_status(self) -> None:
        """
        Maneja la ruta /api/status devolviendo información en formato JSON.
        """
        stats = self.recursos.obtener_stats()

        system_info = {
            "sistema_operativo": platform.platform(),
            "nombre_host": socket.gethostname(),
            "arquitectura": platform.machine(),
            "version_python": platform.python_version(),
            "timestamp": datetime.now().isoformat(),
            "uuid_servidor": str(uuid.uuid4()),
        }

        thread_info = {
            "thread_actual": threading.current_thread().name,
            "threads_activos": threading.active_count(),
            "threads_daemon": sum(1 for t in threading.enumerate() if t.daemon),
            "proceso_pid": os.getpid(),
        }

        recursos_sistema = {
            "cpu_cores": psutil.cpu_count(),
            "cpu_frecuencia": f"{psutil.cpu_freq().current:.2f} MHz",
            "memoria_total": f"{psutil.virtual_memory().total / (1024**3):.2f} GB",
            "memoria_disponible": f"{psutil.virtual_memory().available / (1024**3):.2f} GB",
            "memoria_porcentaje": f"{psutil.virtual_memory().percent}%",
        }

        servidor_info = {
            "ip_servidor": self.server.server_address[0],
            "puerto_servidor": self.server.server_address[1],
            "clase_servidor": self.server.__class__.__name__,
            "tipo_handler": self.__class__.__name__,
        }

        contenido = {
            "servidor": "Servidor HTTP Concurrente en Python",
            "estado": "activo",
            "estadisticas": stats,
            "sistema": system_info,
            "threads": thread_info,
            "server": servidor_info,
            "recursos": recursos_sistema,
        }
        self.send_response(200, "application/json", json.dumps(contenido, indent=2))

    def handle_data(self) -> None:
        """
        Maneja la ruta /data mostrando estadísticas de datos almacenados en HTML.
        """
        try:
            html = generar_html_estadisticas_cliente("Datos Almacenados", carpeta_data="./data")
            self.send_response(200, "text/html", html)
        except Exception as e:
            self.send_error(500, f"Error generando HTML de estadísticas: {e}")

    def handle_post_data(self, request_text: str) -> None:
        """
        Maneja la ruta POST /data para almacenar datos enviados en formato JSON.

        Args:
            request_text (str): Texto completo de la solicitud HTTP.
        """
        try:
            headers, _, body = request_text.partition('\r\n\r\n')
            if not body:
                self.send_error(400, "Cuerpo de solicitud vacío")
                return

            data = json.loads(body)
            data["timestamp"] = datetime.now().isoformat()
            data["id"] = self.recursos.incrementar_contador()

            self.recursos.agregar_dato(data)

            respuesta = json.dumps({
                "mensaje": "Datos almacenados correctamente",
                "id": data["id"],
            })

            peticion_archivo = {
                "id": data["id"],
                "timestamp": data["timestamp"],
                "metodo": "POST",
                "path": "/data",
                "data": data,
            }

            guardar_peticion_en_archivo(peticion_archivo)
            self.send_response(201, "application/json", respuesta)

        except json.JSONDecodeError:
            self.send_error(400, "JSON inválido")
        except Exception as e:
            logger.error(f"Error al procesar POST /data: {str(e)}")
            self.send_error(500, "Error interno al procesar los datos")

    def handle_sleep(self, seconds: int) -> None:
        """
        Maneja la ruta /sleep/{seconds} para simular una carga con una espera determinada.

        Args:
            seconds (int): Número de segundos a esperar (máximo 10).
        """
        seconds = min(seconds, 10)
        logger.info(f"Thread {threading.current_thread().name} durmiendo por {seconds}s")
        time.sleep(seconds)
        content = json.dumps({
            "mensaje": f"El servidor esperó {seconds} segundos",
            "thread": threading.current_thread().name,
            "timestamp": datetime.now().isoformat(),
        })
        self.send_response(200, "application/json", content)

    def handle_api_data(self) -> None:
        """
        Maneja la ruta /api/data devolviendo los datos almacenados en formato JSON.
        """
        contenido = obtener_info_estadisticas_cliente()
        self.send_response(200, "application/json", json.dumps(contenido, indent=2))

    def resolver_ip(self, ip: str) -> Dict[str, str]:
        """
        Intenta resolver información adicional de una dirección IP.

        Args:
            ip (str): Dirección IP a resolver.

        Returns:
            Dict[str, str]: Información adicional sobre la IP.
        """
        try:
            try:
                nombre_host = socket.gethostbyaddr(ip)[0]
            except (socket.herror, socket.gaierror):
                nombre_host = "No resoluble"

            return {
                "nombre_host": nombre_host,
                "es_local": ip.startswith(('127.', '192.168.', '10.', '172.16.')),
                "es_ipv6": ':' in ip,
            }
        except Exception as e:
            logger.error(f"Error resolviendo IP {ip}: {e}")
            return {"error": "No se pudo resolver"}

    def handle_solicitudes(self) -> None:
        """
        Maneja la ruta /solicitudes mostrando información detallada de las solicitudes realizadas.
        """
        try:
            contenido = obtener_info_recursos_compartidos(self.recursos)
            html = generar_html_recursos("Detalle de Recursos Compartidos", contenido)
            self.send_response(200, "text/html", html)

        except Exception as e:
            logger.error(f"Error en handle_solicitudes: {e}")
            self.send_error(500, f"Error interno: {e}")

    def handle_api_solicitudes(self) -> None:
        """
        Maneja la ruta /api/solicitudes devolviendo la lista de solicitudes en formato JSON.
        """
        contenido = obtener_info_recursos_compartidos(self.recursos)

        self.send_response(200, "application/json", json.dumps(contenido, indent=2))
