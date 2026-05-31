from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.hashers import make_password
from django.http import JsonResponse
from .db_services import UsuarioService

def check_session(view_func):
    """
    Decorador de seguridad para proteger las vistas de la app.
    Si el usuario no ha iniciado sesión, lo redirige a la pantalla de login.
    """
    def wrapper(request, *args, **kwargs):
        if 'usuario_id' not in request.session:
            messages.error(request, "Por favor, inicia sesión para acceder al sistema.")
            return redirect('login')
        return view_func(request, *args, **kwargs)
    return wrapper


def login_view(request):
    """
    Vista de Login: Permite iniciar sesión.
    Soporta autenticación de base de datos y un bypass especial de pruebas (admin@syncro.com / admin123).
    """
    if 'usuario_id' in request.session:
        return redirect('usuarios_list')
        
    if request.method == 'POST':
        email = request.POST.get('email', '').strip()
        password = request.POST.get('password', '').strip()
        
        if not (email and password):
            messages.error(request, "Todos los campos son obligatorios.")
            return render(request, 'syncro_app/login.html')
            
        # 1. Bypass especial de calificación para el profesor
        if email == 'admin@syncro.com' and password == 'admin123':
            request.session['usuario_id'] = 999999
            request.session['usuario_nombre'] = "Admin (Calificación)"
            request.session['usuario_rol'] = "Administrador"
            messages.success(request, "¡Sesión iniciada (Perfil de Calificación)!")
            return redirect('usuarios_list')
            
        # 2. Autenticación con la base de datos a través de UsuarioService
        user_info = UsuarioService.authenticate_user(email, password)
        if user_info:
            request.session['usuario_id'] = user_info['usuarioId']
            request.session['usuario_nombre'] = user_info['nombreUsuario']
            request.session['usuario_rol'] = user_info['tipoUsuario']
            messages.success(request, f"¡Bienvenido de vuelta, {user_info['nombreUsuario']}!")
            return redirect('usuarios_list')
        else:
            messages.error(request, "El correo electrónico o la contraseña ingresada son incorrectos.")
            
    return render(request, 'syncro_app/login.html')


def logout_view(request):
    """
    Cierra la sesión de usuario y redirige al login.
    """
    request.session.flush()
    messages.success(request, "Has cerrado sesión correctamente.")
    return redirect('login')


@check_session
def usuarios_list(request):
    """
    Vista READ: Muestra el listado de usuarios del sistema y el panel
    de estadísticas agregadas. Soporta búsquedas y filtros dinámicos.
    """
    search_query = request.GET.get('search', '').strip()
    role_filter = request.GET.get('role', '').strip()
    plan_filter = request.GET.get('plan', '').strip()
    
    try:
        # Invocar a la capa de servicios para obtener analíticas y la lista filtrada
        stats = UsuarioService.get_dashboard_stats()
        users = UsuarioService.list_users(search_query, role_filter, plan_filter)
    except Exception as e:
        stats = {'total_users': 0, 'premium_users': 0, 'total_revenue': 0.00}
        users = []
        messages.error(request, f"Error al recuperar datos de SQL Server: {e}")
        
    context = {
        'users': users,
        'stats': stats,
        'search_query': search_query,
        'role_filter': role_filter,
        'plan_filter': plan_filter
    }
    return render(request, 'syncro_app/lista_usuarios.html', context)


@check_session
def usuario_crear(request):
    """
    Vista CREATE: Muestra el formulario en GET y llama al Stored Procedure
    a través del servicio en POST para registrar nuevos usuarios oyentes.
    """
    if request.method == 'POST':
        nombre = request.POST.get('nombreUsuario', '').strip()
        apellido = request.POST.get('apellidoUsuario', '').strip()
        email = request.POST.get('emailUsuario', '').strip()
        password = request.POST.get('password', '').strip()
        
        if not (nombre and apellido and email and password):
            messages.error(request, "Todos los campos son obligatorios.")
            return render(request, 'syncro_app/formulario.html', {'action': 'crear'})
            
        hashed_password = make_password(password)
        
        try:
            UsuarioService.create_user(nombre, apellido, email, hashed_password)
            messages.success(request, f"¡Usuario {nombre} {apellido} registrado exitosamente con plan Gratis!")
            return redirect('usuarios_list')
        except Exception as e:
            err_str = str(e)
            if "2627" in err_str or "duplicate" in err_str.lower() or "unique" in err_str.lower():
                messages.error(request, f"El correo electrónico '{email}' ya se encuentra registrado.")
            else:
                messages.error(request, f"Error de base de datos al registrar: {e}")
                
    return render(request, 'syncro_app/formulario.html', {'action': 'crear'})


@check_session
def usuario_editar(request, user_id):
    """
    Vista UPDATE: Recupera datos en GET y ejecuta el proceso de actualización
    del perfil y plan de suscripción en POST por medio del servicio.
    """
    # 1. Recuperar información del usuario
    try:
        user_data = UsuarioService.get_user_by_id(user_id)
        if not user_data:
            messages.error(request, "El usuario especificado no existe.")
            return redirect('usuarios_list')
    except Exception as e:
        messages.error(request, f"Error al consultar base de datos: {e}")
        return redirect('usuarios_list')
        
    # 2. Guardar cambios del formulario en POST
    if request.method == 'POST':
        nombre = request.POST.get('nombreUsuario', '').strip()
        apellido = request.POST.get('apellidoUsuario', '').strip()
        tipo = request.POST.get('tipoUsuario', '').strip()
        plan = request.POST.get('tipoPlanSuscripcion', '').strip()
        
        if not (nombre and apellido and tipo and plan):
            messages.error(request, "Todos los campos son obligatorios.")
            return render(request, 'syncro_app/formulario.html', {'action': 'editar', 'user': user_data})
            
        try:
            UsuarioService.update_user_and_plan(user_id, nombre, apellido, tipo, plan)
            messages.success(request, f"¡Usuario {nombre} {apellido} actualizado correctamente!")
            return redirect('usuarios_list')
        except Exception as e:
            err_str = str(e)
            if "547" in err_str or "check" in err_str.lower():
                messages.error(request, "Error de validación: Los valores violan las restricciones CHECK de la base de datos.")
            else:
                messages.error(request, f"Error al actualizar la base de datos: {e}")
                
    return render(request, 'syncro_app/formulario.html', {'action': 'editar', 'user': user_data})


@check_session
def usuario_eliminar(request, user_id):
    """
    Vista DELETE: Llama a la baja transaccional segura del servicio en POST.
    """
    if request.method == 'POST':
        try:
            UsuarioService.delete_user(user_id)
            messages.success(request, "¡El usuario y todos sus registros asociados han sido eliminados de forma definitiva!")
        except Exception as e:
            messages.error(request, f"Error al eliminar de forma transaccional: {e}")
            
    return redirect('usuarios_list')


@check_session
def usuario_exportar_json(request):
    """
    Vista EXPORT: Retorna el archivo JSON desnormalizado de documentos NoSQL.
    """
    try:
        nosql_data = UsuarioService.export_users_to_json()
        response = JsonResponse(nosql_data, safe=False, json_dumps_params={'indent': 2})
        response['Content-Disposition'] = 'attachment; filename="syncro_usuarios_document_db.json"'
        return response
    except Exception as e:
        messages.error(request, f"Error al exportar datos relacionales a NoSQL: {e}")
        return redirect('usuarios_list')
