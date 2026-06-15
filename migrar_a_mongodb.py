# ======================================================================
# SCRIPT DE MIGRACIÓN: SQL SERVER A MONGO DB (SYNCRO)
# MATERIA: Base de Datos II - Proyecto Integrador: Fase 6
# EQUIPO: Grupo 8
# ======================================================================

import os
import json
import pyodbc
import pymongo

# Configuración del entorno
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(BASE_DIR, "db_config.json")
OUTPUT_DIR = os.path.join(os.path.dirname(BASE_DIR), "Datos Migrados JSON")
os.makedirs(OUTPUT_DIR, exist_ok=True)

# 1. Cargar credenciales de SQL Server
if not os.path.exists(CONFIG_PATH):
    print(f"[-] Error: db_config.json no encontrado en: {CONFIG_PATH}")
    exit(1)

with open(CONFIG_PATH, "r", encoding="utf-8") as f:
    config = json.load(f)

server = config.get("SERVER", r"localhost\SQLEXPRESS")
database = config.get("DATABASE", "Syncro")
uid = config.get("UID", "SyncroUser")
pwd = config.get("PWD", "Syncro_Secure_2026!")

# Intentar la conexión a SQL Server
print("[*] Conectando a SQL Server...")
sql_conn = None
connection_strings = [
    f"Driver={{ODBC Driver 18 for SQL Server}};Server={server};Database={database};UID={uid};PWD={pwd};TrustServerCertificate=yes;Encrypt=no;",
    f"Driver={{ODBC Driver 17 for SQL Server}};Server={server};Database={database};UID={uid};PWD={pwd};",
    f"Driver={{SQL Server}};Server={server};Database={database};UID={uid};PWD={pwd};"
]

for conn_str in connection_strings:
    try:
        sql_conn = pyodbc.connect(conn_str, timeout=3)
        print(f" [+] Conexión exitosa a SQL Server!")
        break
    except Exception:
        continue

if not sql_conn:
    print("[-] Error: No se pudo conectar a SQL Server.")
    exit(1)

# Helper para ejecutar consultas FOR JSON PATH y extraer el string completo
def fetch_json_from_sql(query):
    cursor = sql_conn.cursor()
    cursor.execute(query)
    chunks = []
    row = cursor.fetchone()
    while row:
        if row[0] is not None:
            chunks.append(row[0])
        row = cursor.fetchone()
    cursor.close()
    
    full_str = "".join(chunks).strip()
    if not full_str:
        return []
    try:
        return json.loads(full_str)
    except Exception as e:
        print(f"[-] Error al decodificar JSON: {e}")
        print(f"Contenido: {full_str[:500]}")
        return []

# 2. Extracción y formateo NoSQL de colecciones
print("\n[*] Iniciando extracción de colecciones NoSQL desde SQL Server...")

# Colección 1: Usuarios
query_usuarios = """
SELECT 
    u.usuarioId,
    u.nombreUsuario,
    u.apellidoUsuario,
    u.emailUsuario,
    u.passwordHash,
    u.tipoUsuario,
    u.fechaRegistro,
    JSON_QUERY((
        SELECT TOP 1
            sp.tipoPlanSuscripcion AS [plan],
            sp.montoPagoSuscripcion AS [monto],
            sp.fechaPagoSuscripcion AS [fechaPago],
            sp.fechaVencimientoSuscripcion AS [fechaVencimiento],
            sp.metodoPagoSuscripcion AS [metodo_pago]
        FROM Musica.SuscripcionesPagos sp
        WHERE sp.usuarioId = u.usuarioId
        ORDER BY sp.fechaPagoSuscripcion DESC, sp.pagoId DESC
        FOR JSON PATH, WITHOUT_ARRAY_WRAPPER
    )) AS plan_suscripcion_actual,
    JSON_QUERY((
        SELECT 
            sp.pagoId,
            sp.tipoPlanSuscripcion,
            sp.montoPagoSuscripcion,
            sp.fechaPagoSuscripcion,
            sp.fechaVencimientoSuscripcion,
            sp.metodoPagoSuscripcion
        FROM Musica.SuscripcionesPagos sp
        WHERE sp.usuarioId = u.usuarioId
        ORDER BY sp.fechaPagoSuscripcion DESC, sp.pagoId DESC
        FOR JSON PATH
    )) AS historial_pagos,
    JSON_QUERY((
        SELECT s.artistaId AS [value]
        FROM Musica.ArtistasSeguidos s
        WHERE s.usuarioId = u.usuarioId
        FOR JSON PATH
    )) AS artistas_seguidos,
    JSON_QUERY((
        SELECT l.cancionId AS [value]
        FROM Musica.LikesCanciones l
        WHERE l.usuarioId = u.usuarioId
        FOR JSON PATH
    )) AS canciones_gustadas
FROM Musica.Usuarios u
FOR JSON PATH;
"""
usuarios = fetch_json_from_sql(query_usuarios)

# Post-procesar arreglos planos de IDs en Usuarios
for user in usuarios:
    # Aplanar artistas_seguidos
    if "artistas_seguidos" in user and isinstance(user["artistas_seguidos"], list):
        user["artistas_seguidos"] = [item["value"] for item in user["artistas_seguidos"] if "value" in item]
    else:
        user["artistas_seguidos"] = []
        
    # Aplanar canciones_gustadas
    if "canciones_gustadas" in user and isinstance(user["canciones_gustadas"], list):
        user["canciones_gustadas"] = [item["value"] for item in user["canciones_gustadas"] if "value" in item]
    else:
        user["canciones_gustadas"] = []
        
    # Inicializar playlistIds para mapeo posterior en Python
    user["playlistIds"] = []

# Colección 2: Playlists
query_playlists = """
SELECT 
    p.playlistId,
    p.nombrePlaylist,
    p.descripcionPlaylist,
    p.fechaCreacionPlaylist,
    JSON_QUERY((
        SELECT 
            c.cancionId,
            c.tituloCancion,
            c.duracionCancion
        FROM Musica.PlaylistDetalle pd
        INNER JOIN Musica.Canciones c ON pd.cancionId = c.cancionId
        WHERE pd.playlistId = p.playlistId
        FOR JSON PATH
    )) AS canciones
FROM Musica.Playlists p
FOR JSON PATH;
"""
playlists = fetch_json_from_sql(query_playlists)

# Asignar secuencialmente/round-robin las playlists a los usuarios ya que no existe relacion en SQL Server
user_ids = [u["usuarioId"] for u in usuarios] if usuarios else [1, 2, 3, 4, 5]
for i, pl in enumerate(playlists):
    if "canciones" not in pl or pl["canciones"] is None:
        pl["canciones"] = []
        
    assigned_user_id = user_ids[i % len(user_ids)]
    pl["usuarioId"] = assigned_user_id
    
    # Asociar la playlist al usuario en la colección Usuarios
    for user in usuarios:
        if user["usuarioId"] == assigned_user_id:
            user["playlistIds"].append(pl["playlistId"])
            break

# Colección 3: Artistas
query_artistas = """
SELECT 
    ar.artistaId,
    ar.nombreArtistico,
    ar.biografiaArtista,
    JSON_QUERY((
        SELECT 
            al.albumId,
            al.tituloAlbum,
            al.fechaLanzamientoAlbum,
            JSON_QUERY((
                SELECT 
                    c.cancionId,
                    c.tituloCancion,
                    c.duracionCancion,
                    JSON_QUERY((
                        SELECT 
                            g.generoId,
                            g.nombreGenero
                        FROM Musica.Generos g
                        WHERE g.generoId = c.generoId
                        FOR JSON PATH, WITHOUT_ARRAY_WRAPPER
                    )) AS genero
                FROM Musica.Canciones c
                WHERE c.albumId = al.albumId
                FOR JSON PATH
            )) AS canciones
        FROM Musica.Albumes al
        WHERE al.artistaId = ar.artistaId
        FOR JSON PATH
    )) AS albumes
FROM Musica.Artistas ar
FOR JSON PATH;
"""
artistas = fetch_json_from_sql(query_artistas)
for art in artistas:
    if "albumes" not in art or art["albumes"] is None:
        art["albumes"] = []
    else:
        for alb in art["albumes"]:
            if "canciones" not in alb or alb["canciones"] is None:
                alb["canciones"] = []

# Colección 4: HistorialReproducciones
query_reproducciones = """
SELECT 
    h.reproduccionId,
    h.fechaHoraReproduccion,
    h.dispositivoReproduccion,
    JSON_QUERY((
        SELECT 
            c.cancionId,
            c.tituloCancion,
            c.albumId,
            al.tituloAlbum,
            g.nombreGenero
        FROM Musica.Canciones c
        INNER JOIN Musica.Albumes al ON c.albumId = al.albumId
        INNER JOIN Musica.Generos g ON c.generoId = g.generoId
        WHERE c.cancionId = h.cancionId
        FOR JSON PATH, WITHOUT_ARRAY_WRAPPER
    )) AS cancion,
    JSON_QUERY((
        SELECT 
            ar.artistaId,
            ar.nombreArtistico
        FROM Musica.Canciones c
        INNER JOIN Musica.Albumes al ON c.albumId = al.albumId
        INNER JOIN Musica.Artistas ar ON al.artistaId = ar.artistaId
        WHERE c.cancionId = h.cancionId
        FOR JSON PATH, WITHOUT_ARRAY_WRAPPER
    )) AS artista
FROM Musica.HistorialReproducciones h
FOR JSON PATH;
"""
reproducciones = fetch_json_from_sql(query_reproducciones)

# Colección 5: Regalias
query_regalias = """
SELECT 
    r.regaliaId,
    r.artistaId,
    r.periodoContableRegalia,
    r.totalReproduccionesRegalia,
    r.montoGanadoRegalia,
    r.estadoPagoRegalia
FROM Musica.Regalias r
FOR JSON PATH;
"""
regalias = fetch_json_from_sql(query_regalias)

# Colección 6: Notificaciones
query_notificaciones = """
SELECT 
    n.notificacionId,
    n.usuarioId,
    n.contenidoNotificacion AS mensajeNotificacion,
    n.fechaEnvioNotificacion,
    CAST(n.estadoLecturaNotificacion AS BIT) AS leida
FROM Musica.Notificaciones n
FOR JSON PATH;
"""
notificaciones = fetch_json_from_sql(query_notificaciones)

# 3. Guardar archivos JSON físicos
collections_data = {
    "usuarios.json": usuarios,
    "playlists.json": playlists,
    "artistas.json": artistas,
    "reproducciones.json": reproducciones,
    "regalias.json": regalias,
    "notificaciones.json": notificaciones
}

print(f"\n[*] Escribiendo archivos JSON en: {OUTPUT_DIR}")
for filename, data in collections_data.items():
    filepath = os.path.join(OUTPUT_DIR, filename)
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f" [+] Archivo generado: {filename} ({len(data)} documentos)")

# 4. Sembrado automático en MongoDB local/Atlas (Si está disponible)
print("\n[*] Intentando conectar a la base de datos NoSQL MongoDB...")
try:
    mongo_client = pymongo.MongoClient("mongodb://localhost:27017/", serverSelectionTimeoutMS=2000)
    mongo_client.server_info() # Lanzar excepción si no conecta
    
    db = mongo_client["SyncroNoSQL"]
    print(" [+] Conectado a MongoDB local. Sembrando colecciones...")
    
    # Insertar en MongoDB
    for col_name, docs in [
        ("Usuarios", usuarios),
        ("Playlists", playlists),
        ("Artistas", artistas),
        ("HistorialReproducciones", reproducciones),
        ("Regalias", regalias),
        ("Notificaciones", notificaciones)
    ]:
        db[col_name].drop() # Limpiar colección anterior
        if docs:
            db[col_name].insert_many(docs)
            print(f"   - Colección '{col_name}' sembrada con {len(docs)} documentos.")
            
    print("\n[OK] ¡Sembrado exitoso de la Base de Datos NoSQL en MongoDB!")
except Exception as e:
    print(f" [!] Aviso: No se pudo conectar a MongoDB local ({e}).")
    print("     Los archivos JSON formateados están listos para ser importados manualmente a Compass o Atlas.")

# Cerrar SQL Server
sql_conn.close()
print("\n[OK] Proceso de migración relacional-documental finalizado con éxito.")
