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
            cursor.execute("SELECT COUNT(*) FROM Musica.Usuarios")
            stats['total_users'] = cursor.fetchone()[0]
            
            # 2. Total de usuarios Premium activos
            cursor.execute("""
                SELECT COUNT(DISTINCT u.usuarioId)
                FROM Musica.Usuarios u
                INNER JOIN Musica.SuscripcionesPagos s ON s.pagoId = (
                    SELECT TOP 1 sp.pagoId
                    FROM Musica.SuscripcionesPagos sp
                    WHERE sp.usuarioId = u.usuarioId
                    ORDER BY sp.fechaPagoSuscripcion DESC, sp.pagoId DESC
                )
                WHERE s.tipoPlanSuscripcion IN ('Estudiante', 'Premium Individual', 'Premium Familiar')
            """)
            stats['premium_users'] = cursor.fetchone()[0]
            
            # 3. Suma total de los ingresos mensuales estimados
            cursor.execute("""
                SELECT ISNULL(SUM(s.montoPagoSuscripcion), 0)
                FROM Musica.Usuarios u
                INNER JOIN Musica.SuscripcionesPagos s ON s.pagoId = (
                    SELECT TOP 1 sp.pagoId
                    FROM Musica.SuscripcionesPagos sp
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
            FROM Musica.Usuarios u
            LEFT JOIN Musica.SuscripcionesPagos s ON s.pagoId = (
                SELECT TOP 1 sp.pagoId
                FROM Musica.SuscripcionesPagos sp
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
            FROM Musica.Usuarios u
            LEFT JOIN Musica.SuscripcionesPagos s ON s.pagoId = (
                SELECT TOP 1 sp.pagoId
                FROM Musica.SuscripcionesPagos sp
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
        Registra un usuario llamando al procedimiento almacenado Musica.SP_RegistrarNuevoUsuario.
        Esto crea al usuario e inserta su suscripción Gratis atómicamente en SQL Server.
        """
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("{CALL Musica.SP_RegistrarNuevoUsuario (?, ?, ?, ?)}", (nombre, apellido, email, hashed_password))
            conn.commit()
            return True
        finally:
            conn.close()

    @staticmethod
    def update_user_and_plan(user_id, nombre, apellido, role, plan):
        """
        Actualiza el perfil del usuario y su suscripción de forma segura llamando al 
        Stored Procedure Musica.SP_ActualizarUsuarioYSuscripcion en SQL Server.
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
            
            # Invocar al SP que realiza la transacción a nivel de Base de Datos
            cursor.execute(
                "{CALL Musica.SP_ActualizarUsuarioYSuscripcion (?, ?, ?, ?, ?, ?, ?)}",
                (user_id, nombre, apellido, role, plan, monto, metodo)
            )
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
        relacionados llamando al Stored Procedure Musica.SP_EliminarUsuario.
        """
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            # Invocar al SP que maneja la eliminación segura en cascada
            cursor.execute("{CALL Musica.SP_EliminarUsuario (?)}", (user_id,))
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
                "SELECT usuarioId, nombreUsuario, apellidoUsuario, passwordHash, tipoUsuario FROM Musica.Usuarios WHERE emailUsuario = ?",
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
                FROM Musica.Usuarios 
                ORDER BY usuarioId ASC
            """)
            users_rows = cursor.fetchall()
            
            nosql_documents = []
            for row in users_rows:
                u_id, nombre, apellido, email, tipo, fecha_reg = row
                
                # Obtener historial completo de suscripciones/pagos del usuario
                cursor.execute("""
                    SELECT pagoId, tipoPlanSuscripcion, montoPagoSuscripcion, fechaPagoSuscripcion, fechaVencimientoSuscripcion, metodoPagoSuscripcion
                    FROM Musica.SuscripcionesPagos
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

    @staticmethod
    def get_artistas():
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT artistaId, nombreArtistico, biografiaArtista FROM Musica.Artistas ORDER BY nombreArtistico ASC")
            columns = [column[0] for column in cursor.description]
            return [dict(zip(columns, row)) for row in cursor.fetchall()]
        finally:
            conn.close()

    @staticmethod
    def get_albumes():
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("""
                SELECT al.albumId, al.tituloAlbum, al.fechaLanzamientoAlbum, ar.nombreArtistico 
                FROM Musica.Albumes al 
                INNER JOIN Musica.Artistas ar ON al.artistaId = ar.artistaId 
                ORDER BY al.tituloAlbum ASC
            """)
            columns = [column[0] for column in cursor.description]
            return [dict(zip(columns, row)) for row in cursor.fetchall()]
        finally:
            conn.close()

    @staticmethod
    def get_playlists():
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT playlistId, nombrePlaylist, descripcionPlaylist, fechaCreacionPlaylist FROM Musica.Playlists ORDER BY nombrePlaylist ASC")
            columns = [column[0] for column in cursor.description]
            return [dict(zip(columns, row)) for row in cursor.fetchall()]
        finally:
            conn.close()

    @staticmethod
    def get_report_top_songs():
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("""
                SELECT TOP 5 c.tituloCancion, a.nombreArtistico, al.tituloAlbum, COUNT(h.reproduccionId) AS totalReproducciones
                FROM Musica.Canciones c
                INNER JOIN Musica.Albumes al ON c.albumId = al.albumId
                INNER JOIN Musica.Artistas a ON al.artistaId = a.artistaId
                LEFT JOIN Musica.HistorialReproducciones h ON c.cancionId = h.cancionId
                GROUP BY c.tituloCancion, a.nombreArtistico, al.tituloAlbum
                ORDER BY totalReproducciones DESC
            """)
            columns = [column[0] for column in cursor.description]
            return [dict(zip(columns, row)) for row in cursor.fetchall()]
        finally:
            conn.close()

    @staticmethod
    def get_report_plan_revenue():
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("""
                SELECT tipoPlanSuscripcion, COUNT(usuarioId) AS totalUsuarios, CAST(SUM(montoPagoSuscripcion) AS FLOAT) AS ingresosTotales
                FROM Musica.SuscripcionesPagos
                GROUP BY tipoPlanSuscripcion
                ORDER BY ingresosTotales DESC
            """)
            columns = [column[0] for column in cursor.description]
            return [dict(zip(columns, row)) for row in cursor.fetchall()]
        finally:
            conn.close()

    @staticmethod
    def get_report_royalties():
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("""
                SELECT ar.nombreArtistico, SUM(r.totalReproduccionesRegalia) AS reproduccionesTotales, CAST(SUM(r.montoGanadoRegalia) AS FLOAT) AS totalMontoAcumulado, r.estadoPagoRegalia
                FROM Musica.Artistas ar
                INNER JOIN Musica.Regalias r ON ar.artistaId = r.artistaId
                GROUP BY ar.nombreArtistico, r.estadoPagoRegalia
                ORDER BY totalMontoAcumulado DESC
            """)
            columns = [column[0] for column in cursor.description]
            return [dict(zip(columns, row)) for row in cursor.fetchall()]
        finally:
            conn.close()

    @staticmethod
    def get_report_genres():
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("""
                SELECT g.nombreGenero, COUNT(h.reproduccionId) AS totalReproducciones
                FROM Musica.Generos g
                INNER JOIN Musica.Canciones c ON g.generoId = c.generoId
                LEFT JOIN Musica.HistorialReproducciones h ON c.cancionId = h.cancionId
                GROUP BY g.nombreGenero
                ORDER BY totalReproducciones DESC
            """)
            columns = [column[0] for column in cursor.description]
            return [dict(zip(columns, row)) for row in cursor.fetchall()]
        finally:
            conn.close()

    @staticmethod
    def incrementar_reproduccion(cancion_id, dispositivo="Play Simulado"):
        """
        Inserta un registro de reproducción en la tabla HistorialReproducciones.
        Genera el ID manualmente ya que no es identity y realiza un commit.
        """
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT ISNULL(MAX(reproduccionId), 0) + 1 FROM Musica.HistorialReproducciones")
            nuevo_id = cursor.fetchone()[0]
            cursor.execute("""
                INSERT INTO Musica.HistorialReproducciones (reproduccionId, fechaHoraReproduccion, dispositivoReproduccion, cancionId)
                VALUES (?, GETDATE(), ?, ?)
            """, (nuevo_id, dispositivo, cancion_id))
            conn.commit()
            return True
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()

    @staticmethod
    def ejecutar_liquidacion_mensual():
        """
        Invoca al Stored Procedure administrativo de liquidación de regalías.
        """
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("{CALL Musica.SP_LiquidacionMensualRegalias}")
            conn.commit()
            return "Cierre contable y liquidación de regalías procesada exitosamente en SQL Server."
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()

    @staticmethod
    def get_canciones():
        """
        Recupera todas las canciones de la base de datos.
        """
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT cancionId, tituloCancion, albumId, duracionCancion FROM Musica.Canciones ORDER BY tituloCancion ASC")
            columns = [column[0] for column in cursor.description]
            return [dict(zip(columns, row)) for row in cursor.fetchall()]
        finally:
            conn.close()

    @staticmethod
    def get_artista_by_id(artista_id):
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT artistaId, nombreArtistico, biografiaArtista FROM Musica.Artistas WHERE artistaId = ?", (artista_id,))
            row = cursor.fetchone()
            if not row:
                return None
            columns = [column[0] for column in cursor.description]
            return dict(zip(columns, row))
        finally:
            conn.close()

    @staticmethod
    def get_album_by_id(album_id):
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT albumId, tituloAlbum, fechaLanzamientoAlbum, artistaId FROM Musica.Albumes WHERE albumId = ?", (album_id,))
            row = cursor.fetchone()
            if not row:
                return None
            columns = [column[0] for column in cursor.description]
            # Convert date object to ISO format string
            album_data = dict(zip(columns, row))
            if album_data.get('fechaLanzamientoAlbum'):
                album_data['fechaLanzamientoAlbum'] = album_data['fechaLanzamientoAlbum'].isoformat()
            return album_data
        finally:
            conn.close()

    @staticmethod
    def get_playlist_by_id(playlist_id):
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT playlistId, nombrePlaylist, descripcionPlaylist, fechaCreacionPlaylist FROM Musica.Playlists WHERE playlistId = ?", (playlist_id,))
            row = cursor.fetchone()
            if not row:
                return None
            columns = [column[0] for column in cursor.description]
            return dict(zip(columns, row))
        finally:
            conn.close()

    @staticmethod
    def create_artista(nombre, bio):
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("{CALL Musica.SP_CrearArtista (?, ?)}", (nombre, bio))
            conn.commit()
            return True
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()

    @staticmethod
    def update_artista(artista_id, nombre, bio):
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("{CALL Musica.SP_ActualizarArtista (?, ?, ?)}", (artista_id, nombre, bio))
            conn.commit()
            return True
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()

    @staticmethod
    def create_album(titulo, fecha, artista_id):
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("{CALL Musica.SP_CrearAlbum (?, ?, ?)}", (titulo, fecha, artista_id))
            conn.commit()
            return True
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()

    @staticmethod
    def update_album(album_id, titulo, fecha, artista_id):
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("{CALL Musica.SP_ActualizarAlbum (?, ?, ?, ?)}", (album_id, titulo, fecha, artista_id))
            conn.commit()
            return True
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()

    @staticmethod
    def create_playlist(nombre, desc):
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("{CALL Musica.SP_CrearPlaylist (?, ?)}", (nombre, desc))
            conn.commit()
            return True
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()

    @staticmethod
    def update_playlist(playlist_id, nombre, desc):
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("{CALL Musica.SP_ActualizarPlaylist (?, ?, ?)}", (playlist_id, nombre, desc))
            conn.commit()
            return True
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()




