import os
import sys

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'syncro_project.settings')
try:
    import django
    django.setup()
except ImportError:
    print("ERROR: Django no está instalado o no se activó el entorno virtual venv.")
    sys.exit(1)

from syncro_app.db_utils import get_db_connection

print("======================================================================")
print(" DIAGNÓSTICO DE CONEXIÓN A BASE DE DATOS - SYNCRO ")
print("======================================================================")

try:
    conn = get_db_connection()
    print(" [+] Conexión exitosa a SQL Server!")
    cursor = conn.cursor()
    
    # Check total users
    cursor.execute("SELECT COUNT(*) FROM Usuarios")
    user_count = cursor.fetchone()[0]
    print(f" [+] Cantidad de usuarios en la tabla 'Usuarios': {user_count}")
    
    # Check total payments
    cursor.execute("SELECT COUNT(*) FROM SuscripcionesPagos")
    payment_count = cursor.fetchone()[0]
    print(f" [+] Cantidad de registros en 'SuscripcionesPagos': {payment_count}")
    
    conn.close()
    print("======================================================================")
    print(" [OK] DIAGNÓSTICO COMPLETADO SIN ERRORES")
    print("======================================================================")
except Exception as e:
    print(f" [X] ERROR al intentar conectar a SQL Server:")
    print(f"     Detalles: {e}")
    print("======================================================================")
    print(" [!] Sugerencia: Revisa que el servicio MSSQL$SQLEXPRESS esté iniciado")
    print("     y que tus credenciales en settings.py sean correctas.")
    print("======================================================================")
    sys.exit(1)
