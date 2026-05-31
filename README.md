# Syncro - Sistema de Gestión de Suscripciones y Usuarios (Streaming)

Syncro es una aplicación web empresarial desarrollada para la gestión de usuarios y suscriptores de una plataforma de streaming de música, construida en **Python / Django** e integrada directamente con **Microsoft SQL Server**.

El proyecto está diseñado bajo una arquitectura modular desacoplada que separa la lógica de interfaz web de la interacción con la base de datos utilizando una **Capa de Servicios (Service Layer)** y consultas directas SQL nativas parametrizadas (Evitando el uso de Django ORM).

---

## 🎨 Características de Diseño
* **Estética Premium (Estilo Spotify)**: Interfaz en modo oscuro con paleta de colores oscuros (`#121212`, `#1e1e1e`), tipografía Montserrat y detalles resaltados en verde corporativo (`#1DB954`).
* **Fácil navegación**: Barra lateral para alternar entre el panel principal, la edición de usuarios y el cierre de sesión.
* **Componentes Responsivos**: Diseño totalmente adaptable a dispositivos móviles y de escritorio utilizando Bootstrap 5.

---

## 🏗️ Arquitectura de Software
Para garantizar legibilidad, encapsulación y seguridad, el proyecto sigue el siguiente flujo de datos:
1. **Interfaz de Usuario (HTML/CSS/JS)**: Captura las interacciones y envía peticiones HTTP al servidor Django.
2. **Controladores (views.py)**: Vistas web encargadas puramente del flujo HTTP y la validación de sesiones de usuario.
3. **Capa de Servicios (db_services.py)**: Contiene toda la lógica de negocio y las consultas directas `pyodbc`. Ninguna consulta SQL cruda se ejecuta fuera de esta capa.
4. **Utilidad de Conexión (db_utils.py)**: Gestiona la comunicación resiliente contra SQL Server con intentos secuenciales de drivers ODBC.

---

## 🔐 Credenciales de Evaluación Escolar
El panel administrativo está protegido por una sesión segura. Para calificar y evaluar la plataforma, use las siguientes credenciales:
* **Correo de acceso**: `admin@syncro.com`
* **Contraseña**: `admin123`

---

## 🛠️ Requisitos e Instalación

### 1. Requisitos Previos
* **Python 3.10** o superior instalado en el sistema.
* **Microsoft SQL Server Express** ejecutándose localmente.
* **ODBC Driver for SQL Server** (versión 18 o 17).

### 2. Configuración de la Base de Datos en SQL Server
Asegúrate de que la base de datos `Syncro` existe y crea el usuario de acceso dedicado `SyncroUser`:
```sql
-- Ejecutar en SQL Server Management Studio (SSMS) como Administrador:
CREATE DATABASE Syncro;
GO

USE Syncro;
GO

-- Crear Login y Usuario con privilegios
CREATE LOGIN SyncroUser WITH PASSWORD = 'Syncro_Secure_2026!', DEFAULT_DATABASE = Syncro;
CREATE USER SyncroUser FOR LOGIN SyncroUser;
ALTER ROLE db_owner ADD MEMBER SyncroUser;
GO
```

### 3. Preparación del Proyecto Django
1. Abre una terminal de comandos (CMD o PowerShell) en la carpeta raíz del proyecto.
2. Activa el entorno virtual:
   ```powershell
   .\venv\Scripts\activate
   ```
3. Ejecuta las migraciones internas de Django (necesarias para el control de sesiones de usuario):
   ```powershell
   python manage.py migrate
   ```

---

## 🖥️ Uso de la Consola Interactiva (Recomendado)
El proyecto incluye un script automatizado para facilitar la administración del servidor en Windows. 
Solo haz **doble clic** en:
📂 **`ejecutar_syncro.bat`**

Este panel te permitirá:
1. **Iniciar Servidor de Syncro**: Inicia el servidor Django en segundo plano, redirige los logs de peticiones a `server.log` y abre automáticamente tu navegador en `http://127.0.0.1:8000/`.
2. **Detener Servidor**: Libera el puerto `8000` deteniendo el proceso de Python activo.
3. **Ver logs en tiempo real**: Monitorea peticiones de red y depuración.
4. **Probar conexión a SQL Server**: Ejecuta un script rápido de diagnóstico en consola para comprobar el estado de conexión del controlador ODBC contra tu motor de SQL Server local.
5. **Abrir página**: Abre directamente el sitio web local.
6. **Salir**: Cierra el panel de control.
