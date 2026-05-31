import pyodbc
from django.contrib.auth.hashers import check_password
from .db_utils import get_db_connection

class UsuarioService:
    """
    Capa de Servicios de Base de Datos (Service Layer / Repository Pattern).
    Encapsula todas las operaciones SQL nativas, transacciones y llamadas a 
    procedimientos almacenados de SQL Server para el sistema Syncro.
    """

    @staticmethod
    def get_dashboard_stats():
        """
        Ejecuta consultas de agregación (COUNT, SUM) en SQL Server y retorna
        las estadísticas globales del dashboard.
        """
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            stats = {
                'total_users': 0,
                'premium_users': 0,
                'total_revenue': 0.00
            }
            
            # 1. Total de usuarios registrados
            cursor.execute("SELECT COUNT(*) FROM Usuarios")
            stats['total_users'] = cursor.fetchone()[0]
            
            # 2. Total de usuarios Premium activos
            cursor.execute("""
                SELECT COUNT(DISTINCT u.usuarioId)
                FROM Usuarios u
                INNER JOIN SuscripcionesPagos s ON s.pagoId = (
                    SELECT TOP 1 sp.pagoId
                    FROM SuscripcionesPagos sp
                    WHERE sp.usuarioId = u.usuarioId
                    ORDER BY sp.fechaPagoSuscripcion DESC, sp.pagoId DESC
                )
                WHERE s.tipoPlanSuscripcion IN ('Estudiante', 'Premium Individual', 'Premium Familiar')
            """)
            stats['premium_users'] = cursor.fetchone()[0]
            
            # 3. Suma total de los ingresos mensuales estimados
            cursor.execute("""
                SELECT ISNULL(SUM(s.montoPagoSuscripcion), 0)
                FROM Usuarios u
                INNER JOIN SuscripcionesPagos s ON s.pagoId = (
                    SELECT TOP 1 sp.pagoId
                    FROM SuscripcionesPagos sp
                    WHERE sp.usuarioId = u.usuarioId
                    ORDER BY sp.fechaPagoSuscripcion DESC, sp.pagoId DESC
                )
            """)
            stats['total_revenue'] = float(cursor.fetchone()[0])
            
            return stats
        finally:
            conn.close()

    @staticmethod
    def list_users(search_query='', role_filter='Todos', plan_filter='Todos'):
        """
        Construye y ejecuta una consulta SQL dinámica y parametrizada para listar 
        y buscar usuarios de forma segura contra inyecciones SQL.
        """
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            query = """
            SELECT u.usuarioId, u.nombreUsuario, u.apellidoUsuario, u.emailUsuario, u.tipoUsuario,
                   s.tipoPlanSuscripcion, s.montoPagoSuscripcion
            FROM Usuarios u
            LEFT JOIN SuscripcionesPagos s ON s.pagoId = (
                SELECT TOP 1 sp.pagoId
                FROM SuscripcionesPagos sp
                WHERE sp.usuarioId = u.usuarioId
                ORDER BY sp.fechaPagoSuscripcion DESC, sp.pagoId DESC
            )
            """
            
            where_clauses = []
            params = []
            
            # Filtro por término de búsqueda (Nombre, Correo o ID si es numérico)
            if search_query:
                if search_query.isdigit():
                    where_clauses.append("(u.usuarioId = ? OR u.nombreUsuario LIKE ? OR u.apellidoUsuario LIKE ? OR u.emailUsuario LIKE ?)")
                    params.extend([int(search_query), f"%{search_query}%", f"%{search_query}%", f"%{search_query}%"])
                else:
                    where_clauses.append("(u.nombreUsuario LIKE ? OR u.apellidoUsuario LIKE ? OR u.emailUsuario LIKE ?)")
                    params.extend([f"%{search_query}%", f"%{search_query}%", f"%{search_query}%"])
                    
            # Filtro de Rol
            if role_filter and role_filter != 'Todos':
                where_clauses.append("u.tipoUsuario = ?")
                params.append(role_filter)
                
            # Filtro de Plan de Suscripción
            if plan_filter and plan_filter != 'Todos':
                where_clauses.append("s.tipoPlanSuscripcion = ?")
                params.append(plan_filter)
                
            if where_clauses:
                query += " WHERE " + " AND ".join(where_clauses)
                
            query += " ORDER BY u.usuarioId DESC"
            
            cursor.execute(query, params)
            
            # Transformación manual a lista de diccionarios
            columns = [column[0] for column in cursor.description]
            users = []
            for row in cursor.fetchall():
                users.append(dict(zip(columns, row)))
            return users
        finally:
            conn.close()

    @staticmethod
    def get_user_by_id(user_id):
        """
        Obtiene los datos detallados de un usuario y su plan de suscripción actual 
        por medio de su identificador ID.
        """
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            query = """
            SELECT u.usuarioId, u.nombreUsuario, u.apellidoUsuario, u.emailUsuario, u.tipoUsuario,
                   s.tipoPlanSuscripcion
            FROM Usuarios u
            LEFT JOIN SuscripcionesPagos s ON s.pagoId = (
                SELECT TOP 1 sp.pagoId
                FROM SuscripcionesPagos sp
                WHERE sp.usuarioId = u.usuarioId
                ORDER BY sp.fechaPagoSuscripcion DESC, sp.pagoId DESC
            )
            WHERE u.usuarioId = ?
            """
            cursor.execute(query, (user_id,))
            row = cursor.fetchone()
            if not row:
                return None
                
            columns = [column[0] for column in cursor.description]
            return dict(zip(columns, row))
        finally:
            conn.close()

    @staticmethod
    def create_user(nombre, apellido, email, hashed_password):
        """
        Registra un usuario llamando al procedimiento almacenado SP_RegistrarNuevoUsuario.
        Esto crea al usuario e inserta su suscripción Gratis atómicamente en SQL Server.
        """
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("{CALL SP_RegistrarNuevoUsuario (?, ?, ?, ?)}", (nombre, apellido, email, hashed_password))
            conn.commit()
            return True
        finally:
            conn.close()

    @staticmethod
    def update_user_and_plan(user_id, nombre, apellido, role, plan):
        """
        Actualiza el perfil del usuario y su suscripción de forma transaccional.
        Calcula las tarifas del plan en el servidor y ejecuta las consultas correspondientes.
        """
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            # Tarifas fijas del sistema
            tarifas = {
                'Gratis': (0.00, 'Ninguno'),
                'Estudiante': (2.99, 'Tarjeta'),
                'Premium Individual': (5.99, 'Tarjeta'),
                'Premium Familiar': (9.99, 'Tarjeta')
            }
            monto, metodo = tarifas.get(plan, (0.00, 'Ninguno'))
            
            # pyodbc inicia la transacción de forma implícita (autocommit=False por defecto)
            # 1. Actualizar tabla Usuarios
            cursor.execute(
                "UPDATE Usuarios SET nombreUsuario = ?, apellidoUsuario = ?, tipoUsuario = ? WHERE usuarioId = ?",
                (nombre, apellido, role, user_id)
            )
            
            # 2. Verificar si ya tiene suscripción vinculada
            cursor.execute("SELECT COUNT(*) FROM SuscripcionesPagos WHERE usuarioId = ?", (user_id,))
            has_subscription = cursor.fetchone()[0] > 0
            
            if has_subscription:
                # Actualizar la suscripción existente
                cursor.execute(
                    """
                    UPDATE SuscripcionesPagos 
                    SET tipoPlanSuscripcion = ?, montoPagoSuscripcion = ?, fechaPagoSuscripcion = GETDATE(), metodoPagoSuscripcion = ? 
                    WHERE usuarioId = ?
                    """,
                    (plan, monto, metodo, user_id)
                )
            else:
                # Insertar un nuevo pago/suscripción
                nuevo_pago_id = cursor.execute("SELECT ISNULL(MAX(pagoId), 0) + 1 FROM SuscripcionesPagos").fetchone()[0]
                cursor.execute(
                    """
                    INSERT INTO SuscripcionesPagos (pagoId, tipoPlanSuscripcion, montoPagoSuscripcion, fechaPagoSuscripcion, fechaVencimientoSuscripcion, metodoPagoSuscripcion, usuarioId)
                    VALUES (?, ?, ?, GETDATE(), '2099-12-31', ?, ?)
                    """,
                    (nuevo_pago_id, plan, monto, metodo, user_id)
                )
            
            # Confirmar la transacción
            conn.commit()
            return True
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()

    @staticmethod
    def delete_user(user_id):
        """
        Da de baja permanente a un usuario. Borra secuencialmente todos sus registros 
        relacionados en las tablas hijas y luego su usuario principal, todo atómicamente.
        """
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            # 1. Borrar registros dependientes en orden
            cursor.execute("DELETE FROM LikesCanciones WHERE usuarioId = ?", (user_id,))
            cursor.execute("DELETE FROM ArtistasSeguidos WHERE usuarioId = ?", (user_id,))
            cursor.execute("DELETE FROM Notificaciones WHERE usuarioId = ?", (user_id,))
            cursor.execute("DELETE FROM SuscripcionesPagos WHERE usuarioId = ?", (user_id,))
            
            # 2. Borrar de la tabla principal
            cursor.execute("DELETE FROM Usuarios WHERE usuarioId = ?", (user_id,))
            
            # Confirmar la transacción
            conn.commit()
            return True
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()

    @staticmethod
    def authenticate_user(email, password):
        """
        Autentica al usuario contra SQL Server, validando el hash de la contraseña.
        Retorna la información del usuario si tiene éxito, o None si falla.
        """
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                "SELECT usuarioId, nombreUsuario, apellidoUsuario, passwordHash, tipoUsuario FROM Usuarios WHERE emailUsuario = ?",
                (email,)
            )
            row = cursor.fetchone()
            if row:
                user_id, nombre, apellido, pwd_hash, rol = row
                if check_password(password, pwd_hash):
                    return {
                        "usuarioId": user_id,
                        "nombreUsuario": f"{nombre} {apellido}",
                        "tipoUsuario": rol
                    }
            return None
        finally:
            conn.close()

    @staticmethod
    def export_users_to_json():
        """
        Consulta y estructura toda la base de datos de usuarios de forma desnormalizada
        y anidada (jerárquica), simulando una estructura de base de datos documental NoSQL.
        """
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("""
                SELECT usuarioId, nombreUsuario, apellidoUsuario, emailUsuario, tipoUsuario, fechaRegistro 
                FROM Usuarios 
                ORDER BY usuarioId ASC
            """)
            users_rows = cursor.fetchall()
            
            nosql_documents = []
            for row in users_rows:
                u_id, nombre, apellido, email, tipo, fecha_reg = row
                
                # Obtener historial completo de suscripciones/pagos del usuario
                cursor.execute("""
                    SELECT pagoId, tipoPlanSuscripcion, montoPagoSuscripcion, fechaPagoSuscripcion, fechaVencimientoSuscripcion, metodoPagoSuscripcion
                    FROM SuscripcionesPagos
                    WHERE usuarioId = ?
                    ORDER BY fechaPagoSuscripcion DESC, pagoId DESC
                """, (u_id,))
                sub_rows = cursor.fetchall()
                
                historial_pagos = []
                for sub in sub_rows:
                    p_id, plan, monto, f_pago, f_venc, metodo = sub
                    historial_pagos.append({
                        "pagoId": p_id,
                        "tipoPlanSuscripcion": plan,
                        "montoPagoSuscripcion": float(monto) if monto is not None else 0.0,
                        "fechaPagoSuscripcion": f_pago.isoformat() if f_pago else None,
                        "fechaVencimientoSuscripcion": f_venc.isoformat() if f_venc else None,
                        "metodoPagoSuscripcion": metodo
                    })
                    
                plan_actual = None
                if historial_pagos:
                    plan_actual = {
                        "plan": historial_pagos[0]["tipoPlanSuscripcion"],
                        "monto": historial_pagos[0]["montoPagoSuscripcion"],
                        "metodo_pago": historial_pagos[0]["metodoPagoSuscripcion"]
                    }
                    
                nosql_documents.append({
                    "usuarioId": u_id,
                    "nombreUsuario": nombre,
                    "apellidoUsuario": apellido,
                    "emailUsuario": email,
                    "tipoUsuario": tipo,
                    "fechaRegistro": fecha_reg.isoformat() if fecha_reg else None,
                    "plan_suscripcion_actual": plan_actual,
                    "historial_pagos": historial_pagos
                })
            return nosql_documents
        finally:
            conn.close()
