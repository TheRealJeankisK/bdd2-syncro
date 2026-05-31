import pyodbc
from django.conf import settings

def get_db_connection():
    """
    Obtiene una conexión a la base de datos SQL Server de forma segura y dinámica.
    Prueba secuencialmente diferentes controladores ODBC instalados en el sistema
    (ODBC Driver 18, 17 o el controlador heredado 'SQL Server') para garantizar
    compatibilidad automática en cualquier máquina.
    """
    # Obtener el perfil activo y sus credenciales
    active_profile = getattr(settings, 'ACTIVE_DB_CONFIG', 'localhost_user')
    db_configs = getattr(settings, 'SQL_SERVER_CONFIGS', {})
    
    if active_profile not in db_configs:
        raise ValueError(f"El perfil de base de datos '{active_profile}' no está definido en settings.py")
        
    config = db_configs[active_profile]
    server = config['SERVER']
    database = config['DATABASE']
    uid = config['UID']
    pwd = config['PWD']
    
    # Lista de controladores a intentar con sus respectivas propiedades adicionales
    # Para ODBC Driver 18, se fuerza TrustServerCertificate=yes y Encrypt=no para evitar problemas de SSL local.
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
        f"No se pudo conectar a SQL Server '{server}' usando el perfil '{active_profile}'.\n"
        f"Último error registrado: {last_error}"
    )
