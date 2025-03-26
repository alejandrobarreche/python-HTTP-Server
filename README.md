# Servidor HTTP Concurrente

Este proyecto implementa un servidor HTTP concurrente que atiende múltiples solicitudes de clientes de manera simultánea. Se basa en el módulo `socketserver` de Python, que simplifica la tarea de crear servidores de red. La arquitectura del servidor está diseñada para separar la configuración, el manejo de recursos, el procesamiento de solicitudes y la generación de respuestas, facilitando su mantenimiento y escalabilidad.

## Instrucciones para Utilizar el Servidor

1. **Instalación:**
   - Asegúrate de tener Python 3 instalado.
   - Clona el repositorio o descarga el código fuente.

2. **Configuración:**
   - Revisa el archivo `config.py` para ajustar parámetros como HOST, PORT y DEBUG_MODE según sea necesario.

3. **Ejecutar el Servidor:**
   - Abre una terminal y navega hasta el directorio del proyecto.
   - Ejecuta el siguiente comando:
     ```
     python main.py --host localhost --port 8000 --debug
     ```
   - El servidor se iniciará y mostrará mensajes de log indicando que está activo.

4. **Probar los Endpoints:**
   - Abre un navegador y visita:
     - [http://localhost:8000/](http://localhost:8000/) para la página de inicio.
     - [http://localhost:8000/status](http://localhost:8000/status) para ver el estado del servidor.
   - Utiliza herramientas como `curl` o Postman para hacer peticiones a los endpoints API (por ejemplo, `GET /api/status`, `POST /data`, etc.).

5. **Ejecutar Pruebas de Concurrencia:**
   - Se incluye un cliente de prueba en `client.py` que permite enviar múltiples solicitudes concurrentes al servidor.
   - Ejecuta el cliente desde otra terminal:
     ```
     python client.py --host localhost --port 8000 --solicitudes 100 --concurrencia 10 --tipo mixed
     ```
   - El cliente mostrará un resumen de las pruebas realizadas y estadísticas de respuesta.

## Arquitectura del Servidor

El servidor se ejecuta en **un único proceso de Python** y utiliza **múltiples hilos (threads)** para gestionar las solicitudes concurrentes. La estructura y el flujo de ejecución se organizan de la siguiente manera:

1. **Proceso del Servidor**  
   Al iniciar la aplicación (ejecutando `python main.py`), se crea un único proceso que contiene todos los componentes necesarios para la operación concurrente, evitando el uso de múltiples procesos.

2. **Hilo Principal**  
   - Es el primer hilo que se ejecuta y se encarga de la configuración inicial.
   - Crea una instancia de `ThreadingHTTPServer`, que escucha y acepta conexiones entrantes.
   - Inicia un hilo para ejecutar el método `serve_forever()` del servidor, que queda a la espera de nuevas conexiones.
   - Arranca un hilo denominado `ProcesadorColaThread`, encargado de consumir la cola de solicitudes en segundo plano.
   - Permanece en ejecución (por ejemplo, mediante un bucle de espera) para evitar que el proceso finalice.

3. **Hilo del Servidor (ThreadingHTTPServer)**  
   - Ejecuta `serve_forever()`, poniendo al servidor a la "escucha".
   - Al recibir una conexión, crea automáticamente un nuevo hilo (HTTPRequestHandlerThread) para atender cada solicitud de forma individual.
   - Utiliza `ThreadingMixIn` para procesar cada solicitud en un hilo separado y un `BoundedSemaphore(20)` para limitar el número máximo de hilos concurrentes.

4. **Hilos de Petición (HTTPRequestHandlerThread)**  
   Cada solicitud entrante es atendida por un hilo dedicado que:
   - Procesa la solicitud HTTP (lee y analiza el método y la ruta).
   - Registra y encola la solicitud mediante el método `agregar_solicitud_a_cola()` del objeto `RecursosCompartidos`.
   - Genera y envía la respuesta correspondiente al cliente.

5. **Procesador de Cola (ProcesadorColaThread)**  
   - Opera en un bucle continuo, extrayendo solicitudes de la cola (usando `get()`).
   - Procesa cada solicitud en segundo plano (por ejemplo, simulando un retardo o realizando otras operaciones).
   - Marca cada tarea como completada.

## Decisiones Concurrentes

- **Servidor Multihilo:** Se utiliza `ThreadingHTTPServer` (basado en `socketserver.ThreadingTCPServer`) para atender cada conexión en un hilo independiente.
- **Control de Concurrencia:** Se implementa un `BoundedSemaphore(20)` en el handler para limitar el número máximo de conexiones concurrentes, evitando la saturación del servidor.
- **Locks y Semáforos:** Se utilizan locks para proteger estructuras compartidas y semáforos para controlar el acceso a recursos críticos.
- **Colas para Comunicación:** Se emplea una cola (`queue.Queue`) para desacoplar la recepción de solicitudes de su procesamiento, gestionada por el `ProcesadorColaThread`.

## Endpoints del Servidor

A continuación se detalla la funcionalidad de cada endpoint:

### 1. `GET /` o `GET /index`
- **Descripción:**  
  Muestra una página de inicio (HTML) con un resumen del servidor y enlaces a los demás endpoints. Sirve como un menú principal para la navegación.

### 2. `GET /status`
- **Descripción:**  
  Retorna un HTML con información detallada del servidor, que incluye:
  - Estadísticas generales (número de solicitudes, tamaño de la cola, etc.)
  - Información del sistema (SO, hostname, arquitectura, versión de Python)
  - Información sobre hilos (número de hilos activos, PID, etc.)
  - Uso de recursos (CPU, memoria, etc.)
  - Detalles del servidor (IP, puerto, clase de servidor)

### 3. `GET /api/status`
- **Descripción:**  
  Devuelve la misma información que `/status`, pero en formato JSON. Es útil para ser consumido por aplicaciones o scripts que requieran datos estructurados.

### 4. `GET /data`
- **Descripción:**  
  Muestra un HTML con estadísticas sobre los datos almacenados, usualmente obtenidos de la carpeta `./data`.

### 5. `POST /data`
- **Descripción:**  
  Permite almacenar datos enviados en formato JSON. El flujo es el siguiente:
  - Se lee el cuerpo de la solicitud y se parsea el JSON.
  - Se le añade un timestamp y un identificador único.
  - Se guarda el dato en memoria (en `RecursosCompartidos.datos`) y se registra en un archivo JSON en `./data/peticiones.json`.
  - Se envía una respuesta confirmando el almacenamiento.

### 6. `GET /api/data`
- **Descripción:**  
  Devuelve en formato JSON las estadísticas sobre los datos almacenados, similar a lo que muestra `/data` en HTML.

### 7. `GET /solicitudes`
- **Descripción:**  
  Muestra un HTML con la lista de solicitudes registradas (incluyendo IP, método, ruta, timestamp).

### 8. `GET /api/solicitudes`
- **Descripción:**  
  Devuelve en formato JSON la misma lista de solicitudes registradas, útil para análisis automatizados.

### 9. `GET /sleep/<seconds>`
- **Descripción:**  
  Simula una carga artificial haciendo que el hilo se “duerma” por el número de segundos especificado en la URL (máximo 10 segundos). Devuelve un JSON indicando el tiempo de espera, el hilo que lo procesó y la marca de tiempo.


## Conclusión

Este servidor HTTP concurrente está diseñado para atender múltiples solicitudes de manera eficiente, utilizando un único proceso de Python y aprovechando la concurrencia a través de hilos. La separación clara entre la configuración, el manejo de recursos, el procesamiento de solicitudes y la generación de respuestas facilita el mantenimiento y la escalabilidad del sistema.

¡Esperamos que este proyecto te sea de utilidad!

