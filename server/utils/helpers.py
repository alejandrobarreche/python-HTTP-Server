from datetime import datetime
import json
import os
import time
import glob

from ..config import logger


def guardar_peticion_en_archivo(peticion: dict, archivo: str = "./data/peticiones.json") -> None:
    """
    Guarda una petición en un archivo JSON.

    Args:
        peticion (dict): La petición a guardar.
        archivo (str, optional): Ruta del archivo donde se almacenarán las peticiones.
                                 Por defecto es "./data/peticiones.json".
    """
    os.makedirs(os.path.dirname(archivo), exist_ok=True)
    try:
        if os.path.exists(archivo):
            with open(archivo, "r") as f:
                data = json.load(f)
        else:
            data = []

        data.append(peticion)

        with open(archivo, "w") as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        logger.error(f"Error guardando petición en archivo: {e}")

def obtener_info_estadisticas_cliente(carpeta_data: str = "./data/") -> dict:
    """
    Obtiene la información de estadísticas del cliente basadas en los archivos de resultados,
    es decir, los datos que se utilizan para formar el HTML en 'generar_html_estadisticas_cliente'.

    Args:
        carpeta_data (str, optional): Carpeta donde se buscan los archivos de resultados.
                                      Por defecto es "../data/".

    Returns:
        dict: Diccionario con la información de estadísticas, que incluye:
            - analisis: Resumen general de la prueba.
            - tiempos: Tiempos de respuesta (promedio, mínimo, máximo, percentiles, etc.).
            - codigos_respuesta: Códigos de respuesta y sus cantidades.
            - timestamp: Hora de generación de la información.
    """

    # Esperar unos segundos para asegurar que se generen los archivos
    time.sleep(2)

    try:
        archivos = glob.glob(os.path.join(carpeta_data, "resultados_prueba_*.json"))
        if not archivos:
            raise FileNotFoundError("No se encontraron archivos de resultados")

        # Seleccionar el archivo más reciente
        archivo_json = max(archivos, key=os.path.getmtime)
        with open(archivo_json, "r") as f:
            data = json.load(f)

        # Si el archivo contiene una lista, se toma el último elemento
        cliente = data[-1] if isinstance(data, list) else data
    except Exception as e:
        print(f"Error leyendo archivo de resultados: {e}")
        cliente = {}

    resumen = cliente.get("analisis", {})
    tiempos = resumen.get("tiempos", {})
    codigos = resumen.get("codigos_respuesta", {})

    return {
        "analisis": resumen,
        "tiempos": tiempos,
        "codigos_respuesta": codigos,
        "timestamp": datetime.now().isoformat(),
    }

def obtener_info_recursos_compartidos(recursos) -> dict:
    """
    Retorna toda la información relevante de los recursos compartidos.

    Args:
        recursos: Instancia de RecursosCompartidos.

    Returns:
        dict: Diccionario con información sobre el contador de solicitudes,
              cantidad de datos almacenados, tamaño actual de la cola y solicitudes registradas.
    """
    return {
        "contador_solicitudes": recursos.contador_solicitudes,
        "datos_almacenados": len(recursos.datos),
        "max_datos": recursos.max_datos,
        "tamano_cola": recursos.cola_solicitudes.qsize(),
        "solicitudes_realizadas": recursos.obtener_solicitudes(),
        "max_solicitudes": recursos.max_solicitudes,
    }

def generar_html_index(titulo: str = "Servidor HTTP", endpoint: str = None) -> str:
    """
    Genera el HTML para la página de inicio del servidor.

    Args:
        titulo (str, optional): Título de la página. Por defecto es "Servidor HTTP".
        endpoint (str, optional): URL para visualizar el JSON, si aplica.

    Returns:
        str: Código HTML de la página de índice.
    """
    return f"""<!DOCTYPE html>
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
</html>"""


def generar_html_status(titulo: str, stats: dict, sistema: dict, threads: dict,
                        servidor: dict, recursos: dict, endpoint: str = None) -> str:
    """
    Genera el HTML para la página de estado del servidor.

    Args:
        titulo (str): Título de la página.
        stats (dict): Estadísticas generales del servidor.
        sistema (dict): Información del sistema.
        threads (dict): Información sobre los hilos (threads).
        servidor (dict): Información del servidor HTTP.
        recursos (dict): Información de recursos del sistema.
        endpoint (str, optional): URL para ver el JSON de la información. Defaults to None.

    Returns:
        str: Código HTML generado.
    """
    return f"""<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <title>{titulo or "Estado del Servidor"}</title>
    <style>
        body {{
            font-family: 'Segoe UI', Tahoma, sans-serif;
            background-color: #f4f4f4;
            margin: 0;
            padding: 0;
        }}
        .container {{
            max-width: 1000px;
            margin: 30px auto;
            padding: 20px;
            background: white;
            border-radius: 10px;
            box-shadow: 0 4px 10px rgba(0,0,0,0.1);
        }}
        h1, h2 {{
            color: #2c3e50;
        }}
        .section {{
            margin-top: 30px;
            padding: 15px;
            border-left: 6px solid #3498db;
            background: #fafafa;
            border-radius: 6px;
        }}
        .section h3 {{
            margin-top: 0;
            color: #2980b9;
        }}
        ul {{
            list-style: none;
            padding: 0;
        }}
        li {{
            padding: 6px 0;
        }}
        .nav a {{
            margin-right: 15px;
            color: #2980b9;
            text-decoration: none;
        }}
        .timestamp {{
            margin-top: 30px;
            font-size: 0.85em;
            text-align: right;
            color: #aaa;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>{titulo}</h1>
        
        <div class="section">
            <h3>🧵 Estadisticas del servidor</h3>
            <ul>
                <li><strong>Total solicitudes:</strong> {stats['total_solicitudes']}</li>
                <li><strong>Datos Almacenados:</strong> {stats['datos_almacenados']}</li>
                <li><strong>Tamaño de la cola:</strong> {stats['tamano_cola']}</li>
            </ul>
        </div>
        
        <div class="section">
            <h3>🖥️ Información del Sistema</h3>
            <ul>
                <li><strong>SO:</strong> {sistema['sistema_operativo']}</li>
                <li><strong>Host:</strong> {sistema['nombre_host']}</li>
                <li><strong>Arquitectura:</strong> {sistema['arquitectura']}</li>
                <li><strong>Python:</strong> {sistema['version_python']}</li>
                <li><strong>UUID:</strong> {sistema['uuid_servidor']}</li>
                <li><strong>Hora:</strong> {sistema['timestamp']}</li>
            </ul>
        </div>

        <div class="section">
            <h3>🧵 Información de Threads</h3>
            <ul>
                <li><strong>Actual:</strong> {threads['thread_actual']}</li>
                <li><strong>Activos:</strong> {threads['threads_activos']}</li>
                <li><strong>Daemon:</strong> {threads['threads_daemon']}</li>
                <li><strong>PID:</strong> {threads['proceso_pid']}</li>
            </ul>
        </div>

        <div class="section">
            <h3>⚙️ Información del Servidor HTTP</h3>
            <ul>
                <li><strong>IP Servidor:</strong> {servidor['ip_servidor']}</li>
                <li><strong>Puerto:</strong> {servidor['puerto_servidor']}</li>
                <li><strong>Clase de Servidor:</strong> {servidor['clase_servidor']}</li>
                <li><strong>Tipo de Handler:</strong> {servidor['tipo_handler']}</li>
            </ul>
        </div>
        
        <div class="section">
            <h3>💻 Recursos del Sistema</h3>
            <ul>
                <li><strong>CPU Cores:</strong> {recursos['cpu_cores']}</li>
                <li><strong>Frecuencia CPU:</strong> {recursos['cpu_frecuencia']}</li>
                <li><strong>Memoria Total:</strong> {recursos['memoria_total']}</li>
                <li><strong>Memoria Disponible:</strong> {recursos['memoria_disponible']}</li>
                <li><strong>Uso de Memoria:</strong> {recursos['memoria_porcentaje']}</li>
            </ul>
        </div>

        <div class="nav">
            <a href="/">🏠 Inicio</a>
            <a href="/data">📂 Datos</a>
            <a href="/solicitudes">🧾 Solicitudes</a>
            {f'<a href="{endpoint}">📄 Ver JSON</a>' if endpoint else ''}
        </div>

        <div class="timestamp">Generado: {datetime.now().isoformat()}</div>
    </div>
</body>
</html>"""


def generar_html_estadisticas_cliente(titulo: str, carpeta_data: str = "../data/") -> str:
    """
    Genera el HTML para mostrar las estadísticas del cliente basadas en los archivos de resultados.

    Args:
        titulo (str): Título de la página.
        carpeta_data (str, optional): Carpeta donde se buscan los archivos de resultados.
                                      Por defecto es "../data/".

    Returns:
        str: Código HTML con las estadísticas del cliente.
    """
    # Esperar unos segundos antes de buscar el archivo
    time.sleep(2)  # Ajustar el tiempo de espera si es necesario

    try:
        resultado = obtener_info_estadisticas_cliente()
        resumen = resultado.get("analisis", {})
        tiempos = resultado.get("tiempos", {})
        codigos = resultado.get("codigos_respuesta", {})


        return f"""<!DOCTYPE html>
    <html lang="es">
    <head>
        <meta charset="UTF-8">
        <title>{titulo or "Estadísticas de Cliente"}</title>
        <style>
            body {{
                font-family: 'Segoe UI', Tahoma, sans-serif;
                background-color: #f4f4f4;
                margin: 0;
                padding: 0;
            }}
            .container {{
                max-width: 1000px;
                margin: 30px auto;
                padding: 20px;
                background: white;
                border-radius: 10px;
                box-shadow: 0 4px 10px rgba(0,0,0,0.1);
            }}
            h1 {{
                color: #2c3e50;
                margin-bottom: 20px;
            }}
            .section {{
                margin-top: 30px;
                padding: 15px 20px;
                border-left: 6px solid #3498db;
                background: #fafafa;
                border-radius: 6px;
            }}
            .section h3 {{
                margin-top: 0;
                color: #2980b9;
            }}
            table {{
                width: 100%;
                border-collapse: collapse;
                margin-top: 10px;
            }}
            th, td {{
                padding: 10px;
                text-align: left;
                border-bottom: 1px solid #eee;
            }}
            th {{
                background-color: #f0f8ff;
                color: #333;
            }}
            .nav {{
                margin-top: 30px;
            }}
            .nav a {{
                margin-right: 15px;
                color: #2980b9;
                text-decoration: none;
                font-weight: bold;
            }}
            .timestamp {{
                margin-top: 30px;
                font-size: 0.85em;
                text-align: right;
                color: #aaa;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>{titulo}</h1>
    
            <div class="section">
                <h3>📋 Resumen de la Prueba</h3>
                <table>
                    <tr>
                        <th>Total de Solicitudes</th>
                        <td>{resumen.get("total_solicitudes", "N/A")}</td>
                    </tr>
                    <tr>
                        <th>Solicitudes Exitosas</th>
                        <td>{resumen.get("solicitudes_exitosas", "N/A")}</td>
                    </tr>
                    <tr>
                        <th>Tasa de Éxito</th>
                        <td>{resumen.get("tasa_exito", 0)*100:.1f}%</td>
                    </tr>
                </table>
            </div>
    
            <div class="section">
                <h3>⏱️ Tiempos de Respuesta</h3>
                <table>
                    <tr>
                        <th>Promedio</th>
                        <td>{tiempos.get("promedio", 0)*1000:.1f} ms</td>
                    </tr>
                    <tr>
                        <th>Mínimo</th>
                        <td>{tiempos.get("minimo", 0)*1000:.1f} ms</td>
                    </tr>
                    <tr>
                        <th>Máximo</th>
                        <td>{tiempos.get("maximo", 0)*1000:.1f} ms</td>
                    </tr>
                    <tr>
                        <th>P50</th>
                        <td>{tiempos.get("p50", 0)*1000:.1f} ms</td>
                    </tr>
                    <tr>
                        <th>P90</th>
                        <td>{tiempos.get("p90", 0)*1000:.1f} ms</td>
                    </tr>
                    <tr>
                        <th>P95</th>
                        <td>{tiempos.get("p95", 0)*1000:.1f} ms</td>
                    </tr>
                    <tr>
                        <th>P99</th>
                        <td>{tiempos.get("p99", 0)*1000:.1f} ms</td>
                    </tr>
                </table>
            </div>
    
            <div class="section">
                <h3>📦 Códigos de Respuesta</h3>
                <table>
                    <tr>
                        <th>Código</th>
                        <th>Cantidad</th>
                        <th>Porcentaje</th>
                    </tr>
                    {''.join(
            f"<tr><td>{codigo}</td><td>{cantidad}</td><td>{(cantidad / resumen.get('total_solicitudes', 1)) * 100:.1f}%</td></tr>"
            for codigo, cantidad in sorted(codigos.items())
        )}
                </table>
            </div>
    
            <div class="nav">
                <a href="/">🏠 Inicio</a>
                <a href="/status">📊 Estado</a>
                <a href="/data">📂 Datos</a>
            </div>
    
            <div class="timestamp">Generado: {datetime.now().isoformat()}</div>
        </div>
    </body>
    </html>"""
    except Exception as e:
        print(f"Error leyendo archivo de resultados: {e}")
        cliente = {}


def generar_html_recursos(titulo: str, info: dict) -> str:
    """
    Genera el HTML para mostrar la información de recursos compartidos.

    Args:
        titulo (str): Título de la página.
        info (dict): Diccionario con la información de recursos compartidos, por ejemplo:
            {
                "contador_solicitudes": ...,
                "datos_alamcenados": ...,
                "max_datos": ...,
                "tamano_cola": ...,
                "solicitudes_realizadas": [...],
                "max_solicitudes": ...,
            }

    Returns:
        str: Código HTML con la información de recursos compartidos.
    """
    return f"""<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <title>{titulo or "Información de Recursos"}</title>
    <style>
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background-color: #f4f4f4;
            margin: 0;
            padding: 0;
        }}
        .container {{
            max-width: 1000px;
            margin: 30px auto;
            padding: 20px;
            background: white;
            border-radius: 10px;
            box-shadow: 0 4px 10px rgba(0,0,0,0.1);
        }}
        h1 {{
            color: #2c3e50;
            margin-bottom: 20px;
        }}
        .section {{
            margin-top: 30px;
            padding: 15px 20px;
            border-left: 6px solid #3498db;
            background: #fafafa;
            border-radius: 6px;
        }}
        .section h3 {{
            margin-top: 0;
            color: #2980b9;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin-top: 10px;
        }}
        th, td {{
            padding: 10px;
            text-align: left;
            border-bottom: 1px solid #eee;
        }}
        th {{
            background-color: #f0f8ff;
            color: #333;
        }}
        .nav {{
            margin-top: 30px;
        }}
        .nav a {{
            margin-right: 15px;
            color: #2980b9;
            text-decoration: none;
            font-weight: bold;
        }}
        .timestamp {{
            margin-top: 30px;
            font-size: 0.85em;
            text-align: right;
            color: #aaa;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>{titulo}</h1>
        <div class="section">
            <h3>Resumen de Recursos Compartidos</h3>
            <table>
                <tr>
                    <th>Contador de Solicitudes</th>
                    <td>{info.get("contador_solicitudes", "N/A")}</td>
                </tr>
                <tr>
                    <th>Datos Almacenados</th>
                    <td>{info.get("datos_alamcenados", "N/A")} / {info.get("max_datos", "N/A")}</td>
                </tr>
                <tr>
                    <th>Tamaño de la Cola</th>
                    <td>{info.get("tamano_cola", "N/A")}</td>
                </tr>
                <tr>
                    <th>Máximo de Solicitudes Permitidas</th>
                    <td>{info.get("max_solicitudes", "N/A")}</td>
                </tr>
                <tr>
                    <th>Total de Solicitudes Registradas</th>
                    <td>{len(info.get("solicitudes_realizadas", []))}</td>
                </tr>
            </table>
        </div>
        <div class="section">
            <h3>Solicitudes Realizadas</h3>
            <table>
                <tr>
                    <th>Timestamp</th>
                    <th>IP</th>
                    <th>Método</th>
                    <th>Ruta</th>
                </tr>
                {''.join(
        f"<tr><td>{solicitud.get('timestamp', '')}</td><td>{solicitud.get('ip', '')}</td><td>{solicitud.get('metodo', '')}</td><td>{solicitud.get('ruta', '')}</td></tr>"
        for solicitud in info.get("solicitudes_realizadas", [])
    )}
            </table>
        </div>
        <div class="nav">
            <a href="/">🏠 Inicio</a>
            <a href="/status">📊 Estado</a>
            <a href="/data">📂 Datos</a>
            <a href="/solicitudes">🧾 Solicitudes</a>
        </div>
        <div class="timestamp">Generado: {datetime.now().isoformat()}</div>
    </div>
</body>
</html>"""
