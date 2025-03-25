"""
Cliente de Prueba para Servidor HTTP Concurrente
-----------------------------------------------
Este script implementa un cliente que realiza múltiples solicitudes concurrentes
al servidor HTTP para probar su capacidad de manejo de carga.
"""

import argparse
import concurrent.futures
import datetime
import json
import logging


import requests
import time
from typing import Dict, List, Tuple


# Configuración del logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger('cliente_test')

def realizar_solicitud(url: str, metodo: str = 'GET', datos: Dict = None,
                       timeout: int = 10, identificador: int = 0) -> Tuple[int, float, Dict]:
    """
    Realiza una solicitud HTTP al servidor

    Args:
        url: URL a la que hacer la solicitud
        metodo: Metodo HTTP (GET o POST)
        datos: Datos a enviar en caso de POST
        timeout: Tiempo máximo de espera
        identificador: ID de la solicitud para seguimiento

    Returns:
        Tupla con (código de estado, tiempo de respuesta, contenido)
    """
    inicio = time.time()
    try:
        if metodo.upper() == 'GET':
            respuesta = requests.get(url, timeout=timeout)
        elif metodo.upper() == 'POST':
            respuesta = requests.post(url, json=datos, timeout=timeout)
        else:
            raise ValueError(f"Método HTTP no soportado: {metodo}")

        tiempo_total = time.time() - inicio

        # Intentar parsear la respuesta como JSON
        try:
            contenido = respuesta.json()
        except:
            contenido = {"texto": respuesta.text[:100] + "..." if len(respuesta.text) > 100 else respuesta.text}

        return respuesta.status_code, tiempo_total, contenido

    except requests.exceptions.Timeout:
        tiempo_total = time.time() - inicio
        logger.warning(f"Solicitud {identificador} agotó el tiempo de espera ({timeout}s)")
        return 408, tiempo_total, {"error": "Timeout"}
    except requests.exceptions.ConnectionError:
        tiempo_total = time.time() - inicio
        logger.error(f"Error de conexión en solicitud {identificador}")
        return 503, tiempo_total, {"error": "Connection Error"}
    except Exception as e:
        tiempo_total = time.time() - inicio
        logger.error(f"Error en solicitud {identificador}: {str(e)}")
        return 500, tiempo_total, {"error": str(e)}

def ejecutar_prueba_concurrente(url_base: str, num_solicitudes: int,
                                concurrencia: int, tipo_prueba: str) -> List[Dict]:
    """
    Ejecuta múltiples solicitudes concurrentes al servidor

    Args:
        url_base: URL base del servidor
        num_solicitudes: Número total de solicitudes a realizar
        concurrencia: Número máximo de solicitudes concurrentes
        tipo_prueba: Tipo de prueba a realizar (get, sleep, mixed)

    Returns:
        Lista con resultados de las solicitudes
    """
    resultados = []

    # Preparar las URLs según el tipo de prueba
    urls = []
    metodos = []
    datos = []

    for i in range(num_solicitudes):
        if tipo_prueba == 'get':
            # Prueba simple de GET a diferentes endpoints
            endpoint = '/status' if i % 3 == 0 else '/data' if i % 3 == 1 else '/'
            urls.append(f"{url_base}{endpoint}")
            metodos.append('GET')
            datos.append(None)
        elif tipo_prueba == 'sleep':
            # Prueba de carga con diferentes tiempos de espera
            tiempo_espera = i % 5 + 1  # Entre 1 y 5 segundos
            urls.append(f"{url_base}/sleep/{tiempo_espera}")
            metodos.append('GET')
            datos.append(None)
        elif tipo_prueba == 'post':
            # Prueba de POST con diferentes datos
            urls.append(f"{url_base}/data")
            metodos.append('POST')
            datos.append({
                "valor": i,
                "nombre": f"Test {i}",
                "timestamp_cliente": time.time()
            })
        else:  # mixed
            # Prueba mixta
            if i % 4 == 0:
                urls.append(f"{url_base}/status")
                metodos.append('GET')
                datos.append(None)
            elif i % 4 == 1:
                urls.append(f"{url_base}/data")
                metodos.append('GET')
                datos.append(None)
            elif i % 4 == 2:
                tiempo_espera = i % 3 + 1
                urls.append(f"{url_base}/sleep/{tiempo_espera}")
                metodos.append('GET')
                datos.append(None)
            else:
                urls.append(f"{url_base}/data")
                metodos.append('POST')
                datos.append({
                    "valor": i,
                    "nombre": f"Test {i}",
                    "timestamp_cliente": time.time()
                })

    # Ejecutar solicitudes concurrentemente
    logger.info(f"Iniciando prueba con {num_solicitudes} solicitudes, {concurrencia} concurrentes")
    inicio_global = time.time()

    with concurrent.futures.ThreadPoolExecutor(max_workers=concurrencia) as executor:
        # Crear futuras para cada solicitud
        futures = [
            executor.submit(
                realizar_solicitud, urls[i], metodos[i], datos[i], 30, i
            )
            for i in range(num_solicitudes)
        ]

        # Procesar resultados a medida que completan
        for i, future in enumerate(concurrent.futures.as_completed(futures)):
            try:
                status, tiempo, contenido = future.result()
                resultado = {
                    "id": i,
                    "url": urls[i] if i < len(urls) else "desconocida",
                    "metodo": metodos[i] if i < len(metodos) else "desconocido",
                    "status_code": status,
                    "tiempo_segundos": tiempo,
                    "exito": 200 <= status < 300
                }
                resultados.append(resultado)

                # Mostrar progreso
                if (i + 1) % 10 == 0 or i == 0 or i == num_solicitudes - 1:
                    logger.info(f"Completadas {i+1}/{num_solicitudes} solicitudes")

            except Exception as e:
                logger.error(f"Error procesando resultado {i}: {str(e)}")

    # Calcular estadísticas
    tiempo_total = time.time() - inicio_global
    solicitudes_exitosas = sum(1 for r in resultados if r["exito"])
    tiempos = [r["tiempo_segundos"] for r in resultados]

    logger.info(f"Prueba completada en {tiempo_total:.2f} segundos")
    logger.info(f"Éxito: {solicitudes_exitosas}/{num_solicitudes} ({solicitudes_exitosas/num_solicitudes*100:.1f}%)")
    if tiempos:
        logger.info(f"Tiempo promedio: {sum(tiempos)/len(tiempos):.3f}s, Min: {min(tiempos):.3f}s, Max: {max(tiempos):.3f}s")

    return resultados

def analizar_resultados(resultados: List[Dict]) -> Dict:
    """
    Analiza los resultados de la prueba

    Args:
        resultados: Lista con resultados de las solicitudes

    Returns:
        Diccionario con estadísticas
    """
    if not resultados:
        return {"error": "No hay resultados para analizar"}

    # Extraer métricas
    tiempos = [r["tiempo_segundos"] for r in resultados]
    codigos = {}
    for r in resultados:
        codigo = r["status_code"]
        codigos[codigo] = codigos.get(codigo, 0) + 1

    # Calcular métricas de rendimiento
    tiempo_promedio = sum(tiempos) / len(tiempos)
    tiempo_minimo = min(tiempos)
    tiempo_maximo = max(tiempos)

    # Ordenar tiempos para calcular percentiles
    tiempos_ordenados = sorted(tiempos)
    p50 = tiempos_ordenados[len(tiempos_ordenados) // 2]
    p90 = tiempos_ordenados[int(len(tiempos_ordenados) * 0.9)]
    p95 = tiempos_ordenados[int(len(tiempos_ordenados) * 0.95)]
    p99 = tiempos_ordenados[int(len(tiempos_ordenados) * 0.99)]

    # Calcular tasa de éxito
    solicitudes_exitosas = sum(1 for r in resultados if r["exito"])
    tasa_exito = solicitudes_exitosas / len(resultados)

    return {
        "total_solicitudes": len(resultados),
        "solicitudes_exitosas": solicitudes_exitosas,
        "tasa_exito": tasa_exito,
        "tiempos": {
            "promedio": tiempo_promedio,
            "minimo": tiempo_minimo,
            "maximo": tiempo_maximo,
            "p50": p50,
            "p90": p90,
            "p95": p95,
            "p99": p99
        },
        "codigos_respuesta": codigos
    }

def guardar_resultados(resultados: List[Dict], analisis: Dict, archivo: str):
    """
    Guarda los resultados y análisis en un archivo JSON

    Args:
        resultados: Lista con resultados de las solicitudes
        analisis: Diccionario con análisis de los resultados
        archivo: Nombre del archivo donde guardar los resultados
    """
    datos = {
        "timestamp": time.time(),
        "fecha": time.strftime("%Y-%m-%d %H:%M:%S"),
        "analisis": analisis,
        "resultados_detallados": resultados
    }
    timestamp_str = datetime.datetime.now().isoformat().replace(":", "_").replace(".", "_")
    archivo = archivo + '_' + str(timestamp_str) + ".json"

    try:
        with open(archivo, 'w') as f:
            json.dump(datos, f, indent=2)
        logger.info(f"Resultados guardados en {archivo}")
    except Exception as e:
        logger.error(f"Error al guardar resultados: {str(e)}")

def main():
    """Función principal para ejecutar pruebas desde línea de comandos"""
    parser = argparse.ArgumentParser(description="Cliente de prueba para servidor HTTP concurrente")
    parser.add_argument("--host", default="localhost", help="Host del servidor (default: localhost)")
    parser.add_argument("--port", type=int, default=8000, help="Puerto del servidor (default: 8000)")
    parser.add_argument("--solicitudes", type=int, default=100, help="Número total de solicitudes (default: 100)")
    parser.add_argument("--concurrencia", type=int, default=10, help="Nivel de concurrencia (default: 10)")
    parser.add_argument("--tipo", choices=["get", "sleep", "post", "mixed"], default="mixed",
                        help="Tipo de prueba a realizar (default: mixed)")
    parser.add_argument("--output", default=f"./data/resultados_prueba",
                        help="Archivo de salida para resultados (default: resultados_prueba.json)")

    args = parser.parse_args()

    # Construir URL base
    url_base = f"http://{args.host}:{args.port}"

    # Ejecutar prueba
    resultados = ejecutar_prueba_concurrente(
        url_base=url_base,
        num_solicitudes=args.solicitudes,
        concurrencia=args.concurrencia,
        tipo_prueba=args.tipo
    )

    # Analizar y guardar resultados
    analisis = analizar_resultados(resultados)
    guardar_resultados(resultados, analisis, args.output)

    # Mostrar resumen
    print("\nRESUMEN DE LA PRUEBA:")
    print(f"Total solicitudes: {analisis['total_solicitudes']}")
    print(f"Tasa de éxito: {analisis['tasa_exito']*100:.1f}%")
    print(f"Tiempo promedio: {analisis['tiempos']['promedio']*1000:.1f}ms")
    print(f"Percentil 95: {analisis['tiempos']['p95']*1000:.1f}ms")
    print("\nCódigos de respuesta:")
    for codigo, cantidad in sorted(analisis['codigos_respuesta'].items()):
        print(f"  {codigo}: {cantidad} ({cantidad/analisis['total_solicitudes']*100:.1f}%)")

if __name__ == "__main__":
    main()
    # python client.py --host localhost --port 8000 --solicitudes 100 --concurrencia 10 --tipo mixed --output resultados_prueba.json