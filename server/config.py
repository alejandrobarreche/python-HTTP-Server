import logging

DEBUG_MODE = False
HOST = 'localhost'
PORT = 8000

# Configurar logging global
logging.basicConfig(
    level=logging.DEBUG if DEBUG_MODE else logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger('servidor_http')