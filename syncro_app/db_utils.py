import os
import json
import pyodbc
from django.conf import settings

def get_db_connection():
    """
    Obtiene una conexión a la base de datos SQL Server de forma segura y dinámica
    leyendo las credenciales desde un archivo de configuración JSON local (db_config.json).
    Prueba secuencialmente diferentes controladores ODBC instalados en el sistema.
    """
    base_dir = getattr(settings, 'BASE_DIR')
    json_path = os.path.join(base_dir, 'db_config.json')
    
    if not os.path.exists(json_path):
        raise FileNotFoundError(f"Archivo de credenciales JSON no encontrado en: {json_path}")
        
    with open(json_path, 'r', encoding='utf-8') as f:
        config = json.load(f)
        
    server = config.get('SERVER', r'localhost\SQLEXPRESS')
    database = config.get('DATABASE', 'Syncro')
    uid = config.get('UID', 'SyncroUser')
    pwd = config.get('PWD', 'Syncro_Secure_2026!')
    
    # Lista de controladores a intentar con sus respectivas propiedades adicionales
    connection_attempts = [
        {
            "name": "ODBC Driver 18 for SQL Server",
            "conn_str": f"Driver={{ODBC Driver 18 for SQL Server}};Server={server};Database={database};UID={uid};PWD={pwd};TrustServerCertificate=yes;Encrypt=no;"
        },
        {
            "name": "ODBC Driver 17 for SQL Server",
            "conn_str": f"Driver={{ODBC Driver 17 for SQL Server}};Server={server};Database={database};UID={uid};PWD={pwd};"
        },
        {
            "name": "SQL Server (Legacy)",
            "conn_str": f"Driver={{SQL Server}};Server={server};Database={database};UID={uid};PWD={pwd};"
        }
    ]
    
    last_error = None
    for attempt in connection_attempts:
        try:
            # Intentar la conexión con un tiempo de espera de 3 segundos
            conn = pyodbc.connect(attempt['conn_str'], timeout=3)
            return conn
        except Exception as e:
            last_error = e
            # Continuar intentando con el siguiente controlador
            continue
            
    # Si todos los intentos fallaron, lanzar el error detallado
    raise ConnectionError(
        f"No se pudo conectar a SQL Server '{server}' usando las credenciales del archivo JSON.\n"
        f"Último error registrado: {last_error}"
    )
