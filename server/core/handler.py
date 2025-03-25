

from ..config import logger
from .recursos import RecursosCompartidos
import json
from socketserver import BaseRequestHandler
import threading
import time
import os
import psutil
import platform
import socket
import uuid
from datetime import datetime
from http import HTTPStatus
from typing import Tuple, Dict, List
import base64
import plotly.graph_objs as go
import plotly.offline as pyo
from ..utils.helpers import generar_html_index, generar_html_status, guardar_peticion_en_archivo, generar_html_estadisticas_cliente



class HTTPRequestHandler(BaseRequestHandler):
    """
    Manejador de solicitudes HTTP que procesa peticiones concurrentemente.
    """


    # Variable de clase para compartir recursos entre todos los manejadores
    recursos = RecursosCompartidos()

    # Semáforo para limitar el número máximo de conexiones concurrentes
    # Esto ayuda a prevenir agotamiento de recursos
    semaforo_conexiones = threading.BoundedSemaphore(20)

    @classmethod
    def generar_grafica_recursos(cls) -> str:
        """
        Genera una gráfica de recursos del sistema usando Plotly
        Devuelve un gráfico HTML embebido
        """
        try:
            # Obtener datos de recursos
            cpu_percent = psutil.cpu_percent(interval=1)
            memoria = psutil.virtual_memory()
            memoria_percent = memoria.percent

            # Crear figura con subplots
            fig = go.Figure()
            fig.add_trace(go.Gauge(
                domain={'x': [0, 1], 'y': [0, 1]},
                value=cpu_percent,
                mode="gauge+number",
                title={'text': "Uso de CPU"},
                gauge={'axis': {'range': [0, 100]},
                       'bar': {'color': "darkblue"},
                       'steps': [
                           {'range': [0, 50], 'color': "lightgreen"},
                           {'range': [50, 75], 'color': "yellow"},
                           {'range': [75, 100], 'color': "red"}
                       ]}
            ))

            fig.add_trace(go.Gauge(
                domain={'x': [0, 1], 'y': [0, 1]},
                value=memoria_percent,
                mode="gauge+number",
                title={'text': "Uso de Memoria"},
                gauge={'axis': {'range': [0, 100]},
                       'bar': {'color': "darkred"},
                       'steps': [
                           {'range': [0, 50], 'color': "lightblue"},
                           {'range': [50, 75], 'color': "orange"},
                           {'range': [75, 100], 'color': "red"}
                       ]}
            ))

            # Configurar layout
            fig.update_layout(
                title='Monitoreo de Recursos del Servidor',
                height=400,
                width=800,
                template='plotly_white'
            )

            # Convertir a HTML
            grafica_html = pyo.plot(fig, output_type='div', include_plotlyjs='cdn')
            return grafica_html

        except Exception as e:
            logger.error(f"Error generando gráfica de recursos: {e}")
            return f"<p>Error generando gráfica: {e}</p>"

    def contar_solicitudes_por_metodo(self, solicitudes: List[Dict]) -> Dict:
        """Cuenta solicitudes por método HTTP"""
        conteo = {}
        for solicitud in solicitudes:
            metodo = solicitud.get('metodo', 'Desconocido')
            conteo[metodo] = conteo.get(metodo, 0) + 1
        return conteo

    def agrupar_solicitudes_por_hora(self, solicitudes: List[Dict]) -> Dict:
        """
        Agrupa solicitudes por hora del día
        """
        agrupacion = {}
        for solicitud in solicitudes:
            hora = datetime.fromisoformat(solicitud.get('timestamp', datetime.now().isoformat())).strftime("%H")
            agrupacion[hora] = agrupacion.get(hora, 0) + 1
        return dict(sorted(agrupacion.items()))

    def handle(self) -> None:
        """Procesa una solicitud HTTP"""
        # Adquirir semáforo para limitar conexiones concurrentes
        # Si ya hay 20 conexiones activas, las demás esperarán
        with self.semaforo_conexiones:
            # Incrementar contador de forma segura
            num_solicitud = self.recursos.incrementar_contador()

            client_address = self.client_address[0]
            logger.info(f"Conexión desde {client_address} - Solicitud #{num_solicitud}")

            try:
                # Recibir datos del cliente
                data = self.request.recv(1024).strip()
                if not data:
                    return


                # Procesar la solicitud HTTP
                request_text = data.decode('utf-8')
                method, path, _ = self.parse_request(request_text)

                self.recursos.agregar_solicitud_a_cola(request_text)
                self.recursos.registrar_solicitud(client_address, method, path)

                # Analizar el método y la ruta
                method, path, _ = self.parse_request(request_text)

                # Procesar la solicitud según la ruta
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
                        # Ruta que simula procesamiento lento
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
        """Genera una página HTML con mejor estilo y descripciones para cada endpoint"""
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
        """Analiza una solicitud HTTP para extraer metodo, ruta y versión"""
        request_line = request_text.split('\r\n')[0]
        try:
            method, path, version = request_line.split()
            return method, path, version
        except ValueError:
            # Si no se puede dividir correctamente, devolver valores por defecto
            return "GET", "/", "HTTP/1.1"

    def send_response(self, status_code: int, content_type: str, content: str) -> None:
        """Envía una respuesta HTTP al cliente"""
        status_message = HTTPStatus(status_code).phrase
        headers = [
            f"HTTP/1.1 {status_code} {status_message}",
            f"Content-Type: {content_type}",
            f"Content-Length: {len(content)}",
            "Server: PythonConcurrentServer/1.0",
            "Connection: close",
            "\r\n"
        ]
        response = "\r\n".join(headers) + content
        self.request.sendall(response.encode())

    def send_error(self, status_code: int, mensaje: str) -> None:
        """Envía una respuesta de error HTTP"""
        error_data = json.dumps({"error": mensaje, "code": status_code})
        self.send_response(status_code, "application/json", error_data)



    def handle_index(self) -> None:
        """Maneja la ruta raíz """
        contenido = {
            "mensaje": "Servidor HTTP Concurrente en Python",
            "endpoints": [
                {"ruta": "/", "descripcion": "Informacion del servidor"},
                {"ruta": "/status", "descripcion": "Estado y estadisticas del servidor"},
                {"ruta": "/data", "descripcion": "Acceso a datos (GET/POST)"},
                {"ruta": "/sleep/{seconds}", "descripcion": "Simula carga con espera"},
                {"ruta": "/api/status", "descripcion": "Status en formato JSON"},
                {"ruta": "/api/data", "descripcion": "Datos en formato JSON"},
                {"ruta": "/api/solicitudes", "descripcion": "Lista de solicitudes realizadas"}
            ],
            "timestamp": datetime.now().isoformat()
        }
        html = generar_html_index("Servidor HTTP Concurrente", contenido)
        self.send_response(200, "text/html", html)

    def handle_status(self) -> None:
        """Maneja la ruta /status con información detallada y gráficos"""
        # Información del sistema
        try:
            # Obtener estadísticas del sistema
            stats = self.recursos.obtener_stats()

            # Información detallada de sistema
            system_info = {
                "sistema_operativo": platform.platform(),
                "nombre_host": socket.gethostname(),
                "arquitectura": platform.machine(),
                "version_python": platform.python_version(),
                "timestamp": datetime.now().isoformat(),
                "uuid_servidor": str(uuid.uuid4())
            }

            # Información de threads y procesos
            thread_info = {
                "thread_actual": threading.current_thread().name,
                "threads_activos": threading.active_count(),
                "threads_daemon": sum(1 for t in threading.enumerate() if t.daemon),
                "proceso_pid": os.getpid()
            }

            # Recursos del sistema
            recursos_sistema = {
                "cpu_cores": psutil.cpu_count(),
                "cpu_frecuencia": f"{psutil.cpu_freq().current:.2f} MHz",
                "memoria_total": f"{psutil.virtual_memory().total / (1024**3):.2f} GB",
                "memoria_disponible": f"{psutil.virtual_memory().available / (1024**3):.2f} GB",
                "memoria_porcentaje": f"{psutil.virtual_memory().percent}%"
            }

            servidor_info = {
                "ip_servidor": self.server.server_address[0],
                "puerto_servidor": self.server.server_address[1],
                "clase_servidor": self.server.__class__.__name__,
                "tipo_handler": self.__class__.__name__
            }


            # Contenido completo
            contenido = {
                "servidor": "Servidor HTTP Concurrente en Python",
                "estado": "activo",
                "estadisticas": stats,
                "sistema": system_info,
                "threads": thread_info,
                "recursos": recursos_sistema,
            }

            # Generar página HTML
            html = generar_html_status("Estado Detallado del Servidor", stats, system_info, thread_info, servidor_info, recursos_sistema,"/api/status")
            self.send_response(200, "text/html", html)

        except Exception as e:
            logger.error(f"Error en handle_status: {e}")
            self.send_error(500, f"Error interno: {e}")

    def handle_api_status(self) -> None:
        """Maneja la ruta /api/status"""
        # Obtener estadísticas del sistema
        stats = self.recursos.obtener_stats()

        # Información detallada de sistema
        system_info = {
            "sistema_operativo": platform.platform(),
            "nombre_host": socket.gethostname(),
            "arquitectura": platform.machine(),
            "version_python": platform.python_version(),
            "timestamp": datetime.now().isoformat(),
            "uuid_servidor": str(uuid.uuid4())
        }

        # Información de threads y procesos
        thread_info = {
            "thread_actual": threading.current_thread().name,
            "threads_activos": threading.active_count(),
            "threads_daemon": sum(1 for t in threading.enumerate() if t.daemon),
            "proceso_pid": os.getpid()
        }

        # Recursos del sistema
        recursos_sistema = {
            "cpu_cores": psutil.cpu_count(),
            "cpu_frecuencia": f"{psutil.cpu_freq().current:.2f} MHz",
            "memoria_total": f"{psutil.virtual_memory().total / (1024**3):.2f} GB",
            "memoria_disponible": f"{psutil.virtual_memory().available / (1024**3):.2f} GB",
            "memoria_porcentaje": f"{psutil.virtual_memory().percent}%"
        }

        servidor_info = {
            "ip_servidor": self.server.server_address[0],
            "puerto_servidor": self.server.server_address[1],
            "clase_servidor": self.server.__class__.__name__,
            "tipo_handler": self.__class__.__name__
        }


        # Contenido completo
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
        try:
            html = generar_html_estadisticas_cliente("Datos Almacenados", carpeta_data="./data")
            self.send_response(200, "text/html", html)
        except Exception as e:
            self.send_error(500, f"Error generando HTML de estadísticas: {e}")


    def handle_post_data(self, request_text: str) -> None:
        """Maneja la ruta POST /data"""
        # Intentar extraer el cuerpo JSON
        try:
            # Encontrar el cuerpo de la solicitud POST después de la línea en blanco
            headers, _, body = request_text.partition('\r\n\r\n')
            if not body:
                self.send_error(400, "Cuerpo de solicitud vacío")
                return

            # Parsear el cuerpo JSON
            data = json.loads(body)

            # Agregar timestamp
            data["timestamp"] = datetime.now().isoformat()
            data["id"] = self.recursos.incrementar_contador()

            # Almacenar dato de forma segura
            self.recursos.agregar_dato(data)

            # Responder con éxito
            respuesta = json.dumps({
                "mensaje": "Datos almacenados correctamente",
                "id": data["id"]
            })

            peticion_archivo = {
                "id": data["id"],
                "timestamp": data["timestamp"],
                "metodo": "POST",
                "path": "/data",
                "data": data
            }

            # Guardar la petición en un archivo
            guardar_peticion_en_archivo(peticion_archivo)

            self.send_response(201, "application/json", respuesta)

        except json.JSONDecodeError:
            self.send_error(400, "JSON inválido")
        except Exception as e:
            logger.error(f"Error al procesar POST /data: {str(e)}")
            self.send_error(500, "Error interno al procesar los datos")

    def handle_sleep(self, seconds: int) -> None:
        """Maneja la ruta /sleep/{seconds} para simular carga"""
        # Limitar el tiempo máximo para evitar abusos
        seconds = min(seconds, 10)

        logger.info(f"Thread {threading.current_thread().name} durmiendo por {seconds}s")

        # Simular trabajo pesado
        time.sleep(seconds)

        content = json.dumps({
            "mensaje": f"El servidor esperó {seconds} segundos",
            "thread": threading.current_thread().name,
            "timestamp": datetime.now().isoformat()
        })
        self.send_response(200, "application/json", content)

    def handle_api_data(self) -> None:
        """Maneja la ruta /api/data"""
        datos = self.recursos.obtener_datos()
        contenido = {
            "datos": datos,
            "total": len(datos),
            "timestamp": datetime.now().isoformat()
        }
        self.send_response(200, "application/json", json.dumps(contenido, indent=2))

    def resolver_ip(self, ip: str) -> Dict[str, str]:
        """
        Intenta resolver información adicional de una dirección IP
        """
        try:
            # Intentar resolver nombre de host
            try:
                nombre_host = socket.gethostbyaddr(ip)[0]
            except (socket.herror, socket.gaierror):
                nombre_host = "No resoluble"

            return {
                "nombre_host": nombre_host,
                "es_local": ip.startswith(('127.', '192.168.', '10.', '172.16.')),
                "es_ipv6": ':' in ip
            }
        except Exception as e:
            logger.error(f"Error resolviendo IP {ip}: {e}")
            return {"error": "No se pudo resolver"}

    def handle_solicitudes(self) -> None:
        """
        Maneja la ruta para ver solicitudes realizadas con información detallada
        """
        try:
            # Obtener solicitudes
            solicitudes_raw = self.recursos.obtener_solicitudes()

            # Enriquecer información de solicitudes
            solicitudes_enriquecidas = []
            for solicitud in solicitudes_raw:
                info_solicitud = {
                    "ip": solicitud.get('ip', 'Desconocida'),
                    "timestamp": solicitud.get('timestamp', datetime.now().isoformat()),
                    "metodo": solicitud.get('method', 'N/A'),
                    "ruta": solicitud.get('path', 'N/A'),
                    "detalles_adicionales": {
                        "hora_legible": datetime.fromisoformat(solicitud.get('timestamp', datetime.now().isoformat())).strftime("%d/%m/%Y %H:%M:%S"),
                        "dia_semana": datetime.fromisoformat(solicitud.get('timestamp', datetime.now().isoformat())).strftime("%A"),
                        "resolucion_ip": self.resolver_ip(solicitud.get('ip', 'Desconocida'))
                    }
                }
                solicitudes_enriquecidas.append(info_solicitud)

            # Contenido para renderizar
            contenido = {
                "total_solicitudes": len(solicitudes_enriquecidas),
                "solicitudes": solicitudes_enriquecidas,
                "resumen": {
                    "solicitudes_por_metodo": self.contar_solicitudes_por_metodo(solicitudes_enriquecidas),
                    "solicitudes_por_hora": self.agrupar_solicitudes_por_hora(solicitudes_enriquecidas)
                }
            }

            # Generar página HTML
            html = self.generar_pagina_html(
                "Detalle de Solicitudes al Servidor",
                contenido,
                "/api/solicitudes"
            )
            self.send_response(200, "text/html", html)

        except Exception as e:
            logger.error(f"Error en handle_solicitudes: {e}")
            self.send_error(500, f"Error interno: {e}")

    def handle_api_solicitudes(self) -> None:
        """Maneja la ruta /api/solicitudes"""
        solicitudes = self.recursos.obtener_solicitudes()
        contenido = {
            "total_solicitudes": len(solicitudes),
            "solicitudes": solicitudes
        }
        self.send_response(200, "application/json", json.dumps(contenido, indent=2))