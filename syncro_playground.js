// ======================================================================
// MONGODB DATABASE PLAYGROUND SCRIPT (SYNCRO)
// MATERIA: Base de Datos II - Proyecto Integrador: Fase 6
// EQUIPO: Grupo 8
// ======================================================================

// 1. INICIALIZAR Y USAR LA BASE DE DATOS
use('SyncroNoSQL');

// Limpiar colecciones previas para garantizar repetibilidad del playground
db.Usuarios.drop();
db.Playlists.drop();
db.Artistas.drop();
db.HistorialReproducciones.drop();
db.Regalias.drop();
db.Notificaciones.drop();

// ======================================================================
// 2. CREACIÓN DE COLECCIONES CON VALIDACIÓN DE ESQUEMAS ($jsonSchema)
// ======================================================================

// Colección: Usuarios (con planes de suscripción, historial de pagos, likes y seguidos embebidos)
db.createCollection("Usuarios", {
  validator: {
    $jsonSchema: {
      bsonType: "object",
      title: "Usuarios Schema Validation",
      required: ["usuarioId", "nombreUsuario", "apellidoUsuario", "emailUsuario", "passwordHash", "fechaRegistro"],
      properties: {
        usuarioId: {
          bsonType: "int",
          description: "ID único de negocio para el usuario."
        },
        nombreUsuario: {
          bsonType: "string",
          description: "Nombre del usuario."
        },
        apellidoUsuario: {
          bsonType: "string",
          description: "Apellido del usuario."
        },
        emailUsuario: {
          bsonType: "string",
          pattern: "^.+@.+$",
          description: "Email único de acceso con patrón de validación."
        },
        passwordHash: {
          bsonType: "string",
          description: "Hash de la contraseña de acceso."
        },
        tipoUsuario: {
          enum: ["Oyente", "Artista", "Administrador"],
          description: "Rol del usuario en el sistema."
        },
        fechaRegistro: {
          bsonType: "string",
          description: "Fecha de registro en formato ISO."
        },
        plan_suscripcion_actual: {
          bsonType: "object",
          required: ["plan", "monto", "fechaPago", "metodo_pago"],
          properties: {
            plan: { enum: ["Gratis", "Estudiante", "Premium Individual", "Premium Familiar"] },
            monto: { bsonType: "double" },
            fechaPago: { bsonType: "string" },
            fechaVencimiento: { bsonType: "string" },
            metodo_pago: { enum: ["Tarjeta", "Paypal", "Ninguno"] }
          }
        },
        historial_pagos: {
          bsonType: "array",
          items: {
            bsonType: "object",
            required: ["pagoId", "tipoPlanSuscripcion", "montoPagoSuscripcion", "fechaPagoSuscripcion"],
            properties: {
              pagoId: { bsonType: "int" },
              tipoPlanSuscripcion: { bsonType: "string" },
              montoPagoSuscripcion: { bsonType: "double" },
              fechaPagoSuscripcion: { bsonType: "string" },
              fechaVencimientoSuscripcion: { bsonType: "string" },
              metodoPagoSuscripcion: { bsonType: "string" }
            }
          }
        },
        playlistIds: {
          bsonType: "array",
          items: { bsonType: "int" },
          description: "IDs de las playlists creadas por este usuario."
        },
        artistas_seguidos: {
          bsonType: "array",
          items: { bsonType: "int" },
          description: "IDs de los artistas que sigue el usuario."
        },
        canciones_gustadas: {
          bsonType: "array",
          items: { bsonType: "int" },
          description: "IDs de las canciones con Like por el usuario."
        }
      }
    }
  }
});

// Colección: Playlists
db.createCollection("Playlists", {
  validator: {
    $jsonSchema: {
      bsonType: "object",
      required: ["playlistId", "nombrePlaylist", "fechaCreacionPlaylist", "usuarioId"],
      properties: {
        playlistId: { bsonType: "int" },
        nombrePlaylist: { bsonType: "string" },
        descripcionPlaylist: { bsonType: "string" },
        fechaCreacionPlaylist: { bsonType: "string" },
        usuarioId: { bsonType: "int" },
        canciones: {
          bsonType: "array",
          items: {
            bsonType: "object",
            required: ["cancionId", "tituloCancion", "duracionCancion"],
            properties: {
              cancionId: { bsonType: "int" },
              tituloCancion: { bsonType: "string" },
              duracionCancion: { bsonType: "double" }
            }
          }
        }
      }
    }
  }
});

// Colección: Artistas (con álbumes y canciones embebidos)
db.createCollection("Artistas", {
  validator: {
    $jsonSchema: {
      bsonType: "object",
      required: ["artistaId", "nombreArtistico", "biografiaArtista"],
      properties: {
        artistaId: { bsonType: "int" },
        nombreArtistico: { bsonType: "string" },
        biografiaArtista: { bsonType: "string" },
        albumes: {
          bsonType: "array",
          items: {
            bsonType: "object",
            required: ["albumId", "tituloAlbum", "fechaLanzamientoAlbum"],
            properties: {
              albumId: { bsonType: "int" },
              tituloAlbum: { bsonType: "string" },
              fechaLanzamientoAlbum: { bsonType: "string" },
              canciones: {
                bsonType: "array",
                items: {
                  bsonType: "object",
                  required: ["cancionId", "tituloCancion", "duracionCancion"],
                  properties: {
                    cancionId: { bsonType: "int" },
                    tituloCancion: { bsonType: "string" },
                    duracionCancion: { bsonType: "double" },
                    genero: {
                      bsonType: "object",
                      required: ["generoId", "nombreGenero"],
                      properties: {
                        generoId: { bsonType: "int" },
                        nombreGenero: { bsonType: "string" }
                      }
                    }
                  }
                }
              }
            }
          }
        }
      }
    }
  }
});

// ======================================================================
// 3. ESTRATEGIA DE ÍNDICES (UNÍCOS, COMPUESTOS Y TTL)
// ======================================================================

// Índice Único: Garantizar que no se repitan correos electrónicos en Usuarios
db.Usuarios.createIndex({ "emailUsuario": 1 }, { unique: true });

// Índice Compuesto: Optimizar la consulta de regalías por Artista y Periodo Contable
db.Regalias.createIndex({ "artistaId": 1, "periodoContableRegalia": 1 });

// Índice TTL (Time-To-Live): Eliminar notificaciones automáticamente después de 30 días
db.Notificaciones.createIndex({ "fechaEnvioNotificacion": 1 }, { expireAfterSeconds: 2592000 });

// ======================================================================
// 4. INSERCIÓN DE DATOS SEMILLA (MIGRACIÓN RELACIONAL)
// ======================================================================

// Insertar Usuarios de prueba
db.Usuarios.insertMany([
  {
    usuarioId: 1,
    nombreUsuario: "Admin",
    apellidoUsuario: "Syncro",
    emailUsuario: "admin@syncro.com",
    passwordHash: "pbkdf2_sha256$1200000$LHLdXOHJUu61dYZ4soYgE5$Cv53YJ/akdsrmtG/5G1mU91RhPKobWDV2uHWKlLddv8=",
    tipoUsuario: "Administrador",
    fechaRegistro: "2026-01-01",
    artistas_seguidos: [],
    canciones_gustadas: [],
    playlistIds: [1, 6]
  },
  {
    usuarioId: 2,
    nombreUsuario: "Juan",
    apellidoUsuario: "Perez",
    emailUsuario: "juan@gmail.com",
    passwordHash: "pbkdf2_sha256$1200000$LHLdXOHJUu61dYZ4soYgE5$Cv53YJ/akdsrmtG/5G1mU91RhPKobWDV2uHWKlLddv8=",
    tipoUsuario: "Oyente",
    fechaRegistro: "2026-02-15",
    plan_suscripcion_actual: {
      plan: "Estudiante",
      monto: 2.99,
      fechaPago: "2026-06-01",
      fechaVencimiento: "2026-07-01",
      metodo_pago: "Tarjeta"
    },
    historial_pagos: [
      {
        pagoId: 1,
        tipoPlanSuscripcion: "Estudiante",
        montoPagoSuscripcion: 2.99,
        fechaPagoSuscripcion: "2026-06-01",
        fechaVencimientoSuscripcion: "2026-07-01",
        metodoPagoSuscripcion: "Tarjeta"
      }
    ],
    artistas_seguidos: [1, 3],
    canciones_gustadas: [1, 3, 15],
    playlistIds: [2]
  },
  {
    usuarioId: 3,
    nombreUsuario: "Maria",
    apellidoUsuario: "Lopez",
    emailUsuario: "maria@hotmail.com",
    passwordHash: "pbkdf2_sha256$1200000$LHLdXOHJUu61dYZ4soYgE5$Cv53YJ/akdsrmtG/5G1mU91RhPKobWDV2uHWKlLddv8=",
    tipoUsuario: "Oyente",
    fechaRegistro: "2026-03-10",
    plan_suscripcion_actual: {
      plan: "Premium Individual",
      monto: 5.99,
      fechaPago: "2026-06-02",
      fechaVencimiento: "2026-07-02",
      metodo_pago: "Tarjeta"
    },
    historial_pagos: [
      {
        pagoId: 2,
        tipoPlanSuscripcion: "Premium Individual",
        montoPagoSuscripcion: 5.99,
        fechaPagoSuscripcion: "2026-06-02",
        fechaVencimientoSuscripcion: "2026-07-02",
        metodoPagoSuscripcion: "Tarjeta"
      }
    ],
    artistas_seguidos: [2, 4],
    canciones_gustadas: [4, 7, 20],
    playlistIds: [3]
  }
]);

// Insertar Playlists de prueba
db.Playlists.insertMany([
  {
    playlistId: 1,
    nombrePlaylist: "Hits del Momento",
    descripcionPlaylist: "Las canciones más sonadas del planeta.",
    fechaCreacionPlaylist: "2026-06-01",
    usuarioId: 1,
    canciones: [
      { cancionId: 1, tituloCancion: "One More Time", duracionCancion: 5.2 },
      { cancionId: 3, tituloCancion: "Get Lucky", duracionCancion: 6.09 },
      { cancionId: 7, tituloCancion: "Whenever, Wherever", duracionCancion: 3.16 }
    ]
  },
  {
    playlistId: 2,
    nombrePlaylist: "Rock Alternativo",
    descripcionPlaylist: "Clásicos modernos para concentrarse o activarse.",
    fechaCreacionPlaylist: "2026-06-02",
    usuarioId: 2,
    canciones: [
      { cancionId: 4, tituloCancion: "In the End", duracionCancion: 3.36 },
      { cancionId: 15, tituloCancion: "Billie Jean", duracionCancion: 4.54 }
    ]
  }
]);

// Insertar Artistas de prueba
db.Artistas.insertMany([
  {
    artistaId: 1,
    nombreArtistico: "Daft Punk",
    biografiaArtista: "Dúo francés de música electrónica fundado en 1993.",
    albumes: [
      {
        albumId: 1,
        tituloAlbum: "Discovery",
        fechaLanzamientoAlbum: "2001-03-12",
        canciones: [
          { cancionId: 1, tituloCancion: "One More Time", duracionCancion: 5.2, genero: { generoId: 1, nombreGenero: "Electrónica" } },
          { cancionId: 2, tituloCancion: "Harder, Better, Faster, Stronger", duracionCancion: 3.44, genero: { generoId: 1, nombreGenero: "Electrónica" } }
        ]
      },
      {
        albumId: 2,
        tituloAlbum: "Random Access Memories",
        fechaLanzamientoAlbum: "2013-05-17",
        canciones: [
          { cancionId: 3, tituloCancion: "Get Lucky", duracionCancion: 6.09, genero: { generoId: 1, nombreGenero: "Electrónica" } }
        ]
      }
    ]
  },
  {
    artistaId: 2,
    nombreArtistico: "Michael Jackson",
    biografiaArtista: "El Rey del Pop americano.",
    albumes: [
      {
        albumId: 3,
        tituloAlbum: "Thriller",
        fechaLanzamientoAlbum: "1982-11-30",
        canciones: [
          { cancionId: 15, tituloCancion: "Billie Jean", duracionCancion: 4.54, genero: { generoId: 2, nombreGenero: "Pop" } }
        ]
      }
    ]
  }
]);

// Insertar Historial de Reproducciones de prueba
db.HistorialReproducciones.insertMany([
  {
    reproduccionId: 1,
    fechaHoraReproduccion: "2026-06-10T14:32:00Z",
    dispositivoReproduccion: "web",
    cancion: { cancionId: 1, tituloCancion: "One More Time", albumId: 1, tituloAlbum: "Discovery", nombreGenero: "Electrónica" },
    artista: { artistaId: 1, nombreArtistico: "Daft Punk" }
  },
  {
    reproduccionId: 2,
    fechaHoraReproduccion: "2026-06-10T14:38:00Z",
    dispositivoReproduccion: "web",
    cancion: { cancionId: 1, tituloCancion: "One More Time", albumId: 1, tituloAlbum: "Discovery", nombreGenero: "Electrónica" },
    artista: { artistaId: 1, nombreArtistico: "Daft Punk" }
  },
  {
    reproduccionId: 3,
    fechaHoraReproduccion: "2026-06-10T14:45:00Z",
    dispositivoReproduccion: "android",
    cancion: { cancionId: 3, tituloCancion: "Get Lucky", albumId: 2, tituloAlbum: "Random Access Memories", nombreGenero: "Electrónica" },
    artista: { artistaId: 1, nombreArtistico: "Daft Punk" }
  },
  {
    reproduccionId: 4,
    fechaHoraReproduccion: "2026-06-11T09:12:00Z",
    dispositivoReproduccion: "ios",
    cancion: { cancionId: 15, tituloCancion: "Billie Jean", albumId: 3, tituloAlbum: "Thriller", nombreGenero: "Pop" },
    artista: { artistaId: 2, nombreArtistico: "Michael Jackson" }
  }
]);

// Insertar Regalías de prueba
db.Regalias.insertMany([
  {
    regaliaId: 1,
    artistaId: 1,
    periodoContableRegalia: "2026-05-31T23:59:59Z",
    totalReproduccionesRegalia: 14500,
    montoGanadoRegalia: 145.00,
    estadoPagoRegalia: "Pagado"
  },
  {
    regaliaId: 2,
    artistaId: 2,
    periodoContableRegalia: "2026-05-31T23:59:59Z",
    totalReproduccionesRegalia: 8900,
    montoGanadoRegalia: 89.00,
    estadoPagoRegalia: "Pendiente"
  }
]);

// Insertar Notificaciones de prueba (con fecha actual para índice TTL)
db.Notificaciones.insertMany([
  {
    notificacionId: 1,
    usuarioId: 2,
    mensajeNotificacion: "Tu plan de suscripción Estudiante ha sido renovado con éxito.",
    fechaEnvioNotificacion: new Date(),
    leida: false
  },
  {
    notificacionId: 2,
    usuarioId: 3,
    mensajeNotificacion: "¡Daft Punk ha lanzado un nuevo álbum!",
    fechaEnvioNotificacion: new Date(),
    leida: true
  }
]);

// ======================================================================
// 5. CONSULTAS CRUD COMPLETAS
// ======================================================================

// --- CREATE (Operaciones de inserción) ---
// Insertar un nuevo usuario oyente de prueba
db.Usuarios.insertOne({
  usuarioId: 4,
  nombreUsuario: "Carlos",
  apellidoUsuario: "Gomez",
  emailUsuario: "carlos@gmail.com",
  passwordHash: "hash_carlos_2026",
  tipoUsuario: "Oyente",
  fechaRegistro: "2026-06-15",
  plan_suscripcion_actual: {
    plan: "Gratis",
    monto: 0.0,
    fechaPago: "2026-06-15",
    metodo_pago: "Ninguno"
  },
  historial_pagos: [],
  artistas_seguidos: [],
  canciones_gustadas: [],
  playlistIds: []
});

// --- READ (Operaciones de consulta y filtros) ---
// Consultar todos los usuarios que tienen una suscripción Premium activa (monto > 0.0)
db.Usuarios.find(
  { "plan_suscripcion_actual.monto": { $gt: 0.0 } },
  { nombreUsuario: 1, apellidoUsuario: 1, emailUsuario: 1, "plan_suscripcion_actual.plan": 1 }
);

// Buscar canciones pertenecientes a un artista específico dentro de su catálogo embebido
db.Artistas.find(
  { nombreArtistico: "Daft Punk" },
  { "albumes.tituloAlbum": 1, "albumes.canciones.tituloCancion": 1 }
);

// --- UPDATE (Operaciones de actualización) ---
// Actualizar la suscripción de Carlos (Id: 4) a Premium Individual
db.Usuarios.updateOne(
  { usuarioId: 4 },
  {
    $set: {
      plan_suscripcion_actual: {
        plan: "Premium Individual",
        monto: 5.99,
        fechaPago: "2026-06-15",
        fechaVencimiento: "2026-07-15",
        metodo_pago: "Tarjeta"
      }
    },
    $push: {
      historial_pagos: {
        pagoId: 3,
        tipoPlanSuscripcion: "Premium Individual",
        montoPagoSuscripcion: 5.99,
        fechaPagoSuscripcion: "2026-06-15",
        fechaVencimientoSuscripcion: "2026-07-15",
        metodoPagoSuscripcion: "Tarjeta"
      }
    }
  }
);

// Agregar una nueva canción embebida a la Playlist de hits (Id: 1)
db.Playlists.updateOne(
  { playlistId: 1 },
  {
    $push: {
      canciones: {
        cancionId: 15,
        tituloCancion: "Billie Jean",
        duracionCancion: 4.54
      }
    }
  }
);

// --- DELETE (Operaciones de eliminación) ---
// Eliminar permanentemente la notificación leída (Id: 2)
db.Notificaciones.deleteOne({ notificacionId: 2 });

// ======================================================================
// 6. PIPELINES DE AGREGACIÓN ANALÍTICA (REPORTE COMPLEJO)
// ======================================================================

// Reporte 1: Top 5 Canciones más escuchadas en la plataforma
db.HistorialReproducciones.aggregate([
  {
    $group: {
      _id: {
        cancionId: "$cancion.cancionId",
        titulo: "$cancion.tituloCancion",
        artista: "$artista.nombreArtistico",
        genero: "$cancion.nombreGenero"
      },
      totalEscuchas: { $sum: 1 }
    }
  },
  {
    $sort: { totalEscuchas: -1 }
  },
  {
    $limit: 5
  },
  {
    $project: {
      _id: 0,
      cancionId: "$_id.cancionId",
      tituloCancion: "$_id.titulo",
      nombreArtistico: "$_id.artista",
      nombreGenero: "$_id.genero",
      totalReproducciones: "$totalEscuchas"
    }
  }
]);

// Reporte 2: Ingresos Totales y cantidad de usuarios por Tipo de Plan de Suscripción
db.Usuarios.aggregate([
  // Desenrollar el historial de pagos para analizar transacciones individuales
  { $unwind: "$historial_pagos" },
  {
    $group: {
      _id: "$historial_pagos.tipoPlanSuscripcion",
      totalTransacciones: { $sum: 1 },
      ingresosTotales: { $sum: "$historial_pagos.montoPagoSuscripcion" }
    }
  },
  {
    $sort: { ingresosTotales: -1 }
  },
  {
    $project: {
      _id: 0,
      planSuscripcion: "$_id",
      transaccionesProcesadas: "$totalTransacciones",
      recaudadoDolares: { $round: ["$ingresosTotales", 2] }
    }
  }
]);
