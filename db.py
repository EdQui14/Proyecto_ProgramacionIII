import datetime
import mysql.connector
from mysql.connector import Error as MySQLError
import bcrypt

from config import DB_CONFIG


# ============================================================
# Conexión y creación de esquema
# ============================================================
def obtener_conexion():
    try:
        conexion = mysql.connector.connect(**DB_CONFIG)
        return conexion
    except MySQLError as e:
        raise ConnectionError(
            f"No se pudo conectar a la base de datos MySQL.\n"
            f"Verifica que XAMPP esté corriendo y la base '{DB_CONFIG['database']}' exista.\n"
            f"Detalle: {e}"
        )


def _crear_base_datos_si_no_existe():
    """Se conecta sin seleccionar base de datos y la crea si hace falta (útil en XAMPP)."""
    config_sin_db = {k: v for k, v in DB_CONFIG.items() if k != "database"}
    try:
        conexion = mysql.connector.connect(**config_sin_db)
        cursor = conexion.cursor()
        cursor.execute(
            f"CREATE DATABASE IF NOT EXISTS {DB_CONFIG['database']} "
            f"CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
        )
        conexion.commit()
        cursor.close()
        conexion.close()
    except MySQLError as e:
        raise ConnectionError(
            f"No se pudo crear/verificar la base de datos '{DB_CONFIG['database']}'.\n"
            f"Verifica que XAMPP (MySQL) esté corriendo.\nDetalle: {e}"
        )


def inicializar_base_datos():
    """Crea la base de datos (si hace falta) y las tablas necesarias. Llamar una vez al iniciar la app."""
    _crear_base_datos_si_no_existe()
    conexion = obtener_conexion()
    cursor = conexion.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS usuarios (
            id INT AUTO_INCREMENT PRIMARY KEY,
            nombre VARCHAR(120) NOT NULL,
            usuario VARCHAR(60) NOT NULL UNIQUE,
            contrasena_hash VARCHAR(255) NOT NULL,
            foto_perfil VARCHAR(255) NULL
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS habitos (
            id INT AUTO_INCREMENT PRIMARY KEY,
            usuario_id INT NOT NULL,
            nombre VARCHAR(150) NOT NULL,
            categoria VARCHAR(60) NOT NULL,
            frecuencia VARCHAR(60) NOT NULL,
            completado_hoy TINYINT(1) NOT NULL DEFAULT 0,
            fecha_registro DATE NOT NULL,
            racha INT NOT NULL DEFAULT 0,
            FOREIGN KEY (usuario_id) REFERENCES usuarios(id) ON DELETE CASCADE
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS subtareas (
            id INT AUTO_INCREMENT PRIMARY KEY,
            habito_id INT NOT NULL,
            nombre VARCHAR(150) NOT NULL,
            completado TINYINT(1) NOT NULL DEFAULT 0,
            orden INT NOT NULL DEFAULT 0,
            FOREIGN KEY (habito_id) REFERENCES habitos(id) ON DELETE CASCADE
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS logros_usuario (
            id INT AUTO_INCREMENT PRIMARY KEY,
            usuario_id INT NOT NULL,
            logro_codigo VARCHAR(60) NOT NULL,
            fecha_desbloqueo DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            UNIQUE KEY unico_logro_usuario (usuario_id, logro_codigo),
            FOREIGN KEY (usuario_id) REFERENCES usuarios(id) ON DELETE CASCADE
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """)

    conexion.commit()
    cursor.close()
    conexion.close()


# ============================================================
# Usuarios
# ============================================================
def registrar_usuario(nombre, usuario, contrasena, foto_perfil=None):
    conexion = obtener_conexion()
    cursor = conexion.cursor()

    cursor.execute("SELECT id FROM usuarios WHERE usuario = %s", (usuario,))
    if cursor.fetchone():
        cursor.close()
        conexion.close()
        return False, "Ese nombre de usuario ya existe."

    hash_contrasena = bcrypt.hashpw(contrasena.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

    cursor.execute(
        "INSERT INTO usuarios (nombre, usuario, contrasena_hash, foto_perfil) VALUES (%s, %s, %s, %s)",
        (nombre, usuario, hash_contrasena, foto_perfil)
    )
    conexion.commit()
    cursor.close()
    conexion.close()
    return True, "Cuenta creada con éxito. Ahora puedes iniciar sesión."


def verificar_login(usuario, contrasena):
    conexion = obtener_conexion()
    cursor = conexion.cursor(dictionary=True)
    cursor.execute("SELECT * FROM usuarios WHERE usuario = %s", (usuario,))
    fila = cursor.fetchone()
    cursor.close()
    conexion.close()

    if not fila:
        return None

    if bcrypt.checkpw(contrasena.encode("utf-8"), fila["contrasena_hash"].encode("utf-8")):
        return fila
    return None


def actualizar_foto_perfil(usuario_id, ruta_foto):
    """Actualiza la foto de perfil de un usuario ya registrado."""
    conexion = obtener_conexion()
    cursor = conexion.cursor()
    cursor.execute(
        "UPDATE usuarios SET foto_perfil = %s WHERE id = %s",
        (ruta_foto, usuario_id)
    )
    conexion.commit()
    cursor.close()
    conexion.close()


# ============================================================
# Hábitos
# ============================================================
def crear_habito(usuario_id, nombre, categoria, frecuencia, subtareas=None):
    """Crea un hábito y, opcionalmente, su lista inicial de subtareas."""
    conexion = obtener_conexion()
    cursor = conexion.cursor()

    cursor.execute(
        """INSERT INTO habitos (usuario_id, nombre, categoria, frecuencia, completado_hoy, fecha_registro, racha)
           VALUES (%s, %s, %s, %s, 0, %s, 0)""",
        (usuario_id, nombre, categoria, frecuencia, datetime.date.today())
    )
    habito_id = cursor.lastrowid

    if subtareas:
        for orden, texto in enumerate(subtareas):
            texto = texto.strip()
            if texto:
                cursor.execute(
                    "INSERT INTO subtareas (habito_id, nombre, completado, orden) VALUES (%s, %s, 0, %s)",
                    (habito_id, texto, orden)
                )

    conexion.commit()
    cursor.close()
    conexion.close()
    return habito_id


def _revisar_cambio_de_dia(cursor, habito):
    """Si el hábito no se ha tocado hoy, actualiza racha y reinicia los checks."""
    hoy = datetime.date.today()
    fecha_registro = habito["fecha_registro"]
    if isinstance(fecha_registro, datetime.datetime):
        fecha_registro = fecha_registro.date()

    if fecha_registro == hoy:
        return  # mismo día, nada que hacer

    dias_transcurridos = (hoy - fecha_registro).days
    nueva_racha = habito["racha"] + 1 if (habito["completado_hoy"] and dias_transcurridos == 1) else 0

    cursor.execute(
        "UPDATE habitos SET completado_hoy = 0, fecha_registro = %s, racha = %s WHERE id = %s",
        (hoy, nueva_racha, habito["id"])
    )
    cursor.execute("UPDATE subtareas SET completado = 0 WHERE habito_id = %s", (habito["id"],))


def obtener_habitos(usuario_id):
    """Devuelve la lista de hábitos del usuario, cada uno con sus subtareas y % de progreso."""
    conexion = obtener_conexion()
    cursor = conexion.cursor(dictionary=True)

    cursor.execute("SELECT * FROM habitos WHERE usuario_id = %s ORDER BY id DESC", (usuario_id,))
    habitos = cursor.fetchall()

    for habito in habitos:
        _revisar_cambio_de_dia(cursor, habito)
    conexion.commit()

    # Volver a leer ya con los datos del día actualizados
    cursor.execute("SELECT * FROM habitos WHERE usuario_id = %s ORDER BY id DESC", (usuario_id,))
    habitos = cursor.fetchall()

    for habito in habitos:
        cursor.execute(
            "SELECT * FROM subtareas WHERE habito_id = %s ORDER BY orden, id", (habito["id"],)
        )
        subtareas = cursor.fetchall()
        habito["subtareas"] = subtareas

        if subtareas:
            completadas = sum(1 for s in subtareas if s["completado"])
            habito["progreso"] = int(round((completadas / len(subtareas)) * 100))
            habito["completado_hoy"] = 1 if completadas == len(subtareas) else 0
        else:
            habito["progreso"] = 100 if habito["completado_hoy"] else 0

    cursor.close()
    conexion.close()
    return habitos


def obtener_progreso(usuario_id):
    """Devuelve (completados, total) hábitos del día para la barra general."""
    habitos = obtener_habitos(usuario_id)
    total = len(habitos)
    completados = sum(1 for h in habitos if h["completado_hoy"])
    return completados, total


def marcar_habito(habito_id, completado):
    """Marca un hábito SIN subtareas como completado/no completado."""
    conexion = obtener_conexion()
    cursor = conexion.cursor()
    cursor.execute(
        "UPDATE habitos SET completado_hoy = %s WHERE id = %s",
        (1 if completado else 0, habito_id)
    )
    conexion.commit()
    cursor.close()
    conexion.close()


def eliminar_habito(habito_id):
    conexion = obtener_conexion()
    cursor = conexion.cursor()
    cursor.execute("DELETE FROM habitos WHERE id = %s", (habito_id,))
    conexion.commit()
    cursor.close()
    conexion.close()


# ============================================================
# Estadísticas
# ============================================================
def obtener_estadisticas(usuario_id):
    """Calcula estadísticas generales del usuario con los datos actuales."""
    habitos = obtener_habitos(usuario_id)

    total_habitos = len(habitos)
    completados_hoy = sum(1 for h in habitos if h["completado_hoy"])
    pendientes_hoy = total_habitos - completados_hoy
    porcentaje_hoy = int(round((completados_hoy / total_habitos) * 100)) if total_habitos else 0

    mejor_racha = max((int(h.get("racha") or 0) for h in habitos), default=0)
    habito_mejor_racha = "Sin hábitos"
    if habitos:
        mejor = max(habitos, key=lambda h: int(h.get("racha") or 0))
        habito_mejor_racha = mejor["nombre"]

    total_subtareas = 0
    subtareas_completadas = 0
    categorias = {}

    for habito in habitos:
        categoria = habito.get("categoria") or "Otro"
        if categoria not in categorias:
            categorias[categoria] = {"total": 0, "completados": 0}

        categorias[categoria]["total"] += 1
        if habito["completado_hoy"]:
            categorias[categoria]["completados"] += 1

        subtareas = habito.get("subtareas", [])
        total_subtareas += len(subtareas)
        subtareas_completadas += sum(1 for s in subtareas if s["completado"])

    return {
        "total_habitos": total_habitos,
        "completados_hoy": completados_hoy,
        "pendientes_hoy": pendientes_hoy,
        "porcentaje_hoy": porcentaje_hoy,
        "mejor_racha": mejor_racha,
        "habito_mejor_racha": habito_mejor_racha,
        "total_subtareas": total_subtareas,
        "subtareas_completadas": subtareas_completadas,
        "categorias": categorias,
    }


# ============================================================
# Rachas, logros y experiencia
# ============================================================
LOGROS = [
    {
        "codigo": "primer_habito",
        "icono": "🌱",
        "nombre": "El comienzo",
        "descripcion": "Crea tu primer hábito.",
        "xp": 25,
    },
    {
        "codigo": "cinco_habitos",
        "icono": "📋",
        "nombre": "Agenda llena",
        "descripcion": "Ten al menos 5 hábitos creados.",
        "xp": 50,
    },
    {
        "codigo": "primer_completado",
        "icono": "✅",
        "nombre": "Primer paso",
        "descripcion": "Completa un hábito durante el día.",
        "xp": 30,
    },
    {
        "codigo": "dia_perfecto",
        "icono": "💯",
        "nombre": "Día perfecto",
        "descripcion": "Completa todos tus hábitos del día.",
        "xp": 75,
    },
    {
        "codigo": "racha_3",
        "icono": "🔥",
        "nombre": "Tomando ritmo",
        "descripcion": "Consigue una racha de 3 días.",
        "xp": 60,
    },
    {
        "codigo": "racha_7",
        "icono": "🏆",
        "nombre": "Una semana imparable",
        "descripcion": "Consigue una racha de 7 días.",
        "xp": 120,
    },
    {
        "codigo": "subtareas_10",
        "icono": "🧩",
        "nombre": "Paso a paso",
        "descripcion": "Completa 10 subtareas en un mismo día.",
        "xp": 80,
    },
]


def _codigos_logros_cumplidos(usuario_id):
    """Calcula qué logros cumple el usuario con sus datos actuales."""
    datos = obtener_estadisticas(usuario_id)
    cumplidos = set()

    if datos["total_habitos"] >= 1:
        cumplidos.add("primer_habito")
    if datos["total_habitos"] >= 5:
        cumplidos.add("cinco_habitos")
    if datos["completados_hoy"] >= 1:
        cumplidos.add("primer_completado")
    if datos["total_habitos"] > 0 and datos["completados_hoy"] == datos["total_habitos"]:
        cumplidos.add("dia_perfecto")
    if datos["mejor_racha"] >= 3:
        cumplidos.add("racha_3")
    if datos["mejor_racha"] >= 7:
        cumplidos.add("racha_7")
    if datos["subtareas_completadas"] >= 10:
        cumplidos.add("subtareas_10")

    return cumplidos


def evaluar_logros(usuario_id):
    """Guarda logros nuevos y devuelve solo los que se acaban de desbloquear."""
    cumplidos = _codigos_logros_cumplidos(usuario_id)
    if not cumplidos:
        return []

    conexion = obtener_conexion()
    cursor = conexion.cursor()
    nuevos_codigos = []

    try:
        for codigo in cumplidos:
            cursor.execute(
                "INSERT IGNORE INTO logros_usuario (usuario_id, logro_codigo) VALUES (%s, %s)",
                (usuario_id, codigo),
            )
            if cursor.rowcount == 1:
                nuevos_codigos.append(codigo)
        conexion.commit()
    finally:
        cursor.close()
        conexion.close()

    por_codigo = {logro["codigo"]: logro for logro in LOGROS}
    return [por_codigo[codigo] for codigo in nuevos_codigos if codigo in por_codigo]


def obtener_logros(usuario_id):
    """Devuelve todos los logros, su estado, XP y nivel actual."""
    evaluar_logros(usuario_id)

    conexion = obtener_conexion()
    cursor = conexion.cursor(dictionary=True)
    try:
        cursor.execute(
            "SELECT logro_codigo, fecha_desbloqueo FROM logros_usuario WHERE usuario_id = %s",
            (usuario_id,),
        )
        filas = cursor.fetchall()
    finally:
        cursor.close()
        conexion.close()

    desbloqueados = {fila["logro_codigo"]: fila["fecha_desbloqueo"] for fila in filas}
    resultado = []
    xp_total = 0

    for logro in LOGROS:
        copia = logro.copy()
        copia["desbloqueado"] = logro["codigo"] in desbloqueados
        copia["fecha_desbloqueo"] = desbloqueados.get(logro["codigo"])
        if copia["desbloqueado"]:
            xp_total += logro["xp"]
        resultado.append(copia)

    nivel = (xp_total // 100) + 1
    xp_nivel = xp_total % 100

    return {
        "logros": resultado,
        "desbloqueados": sum(1 for logro in resultado if logro["desbloqueado"]),
        "total": len(resultado),
        "xp_total": xp_total,
        "nivel": nivel,
        "xp_nivel": xp_nivel,
        "xp_siguiente": 100,
    }


# ============================================================
# Subtareas
# ============================================================
def agregar_subtarea(habito_id, nombre):
    conexion = obtener_conexion()
    cursor = conexion.cursor()
    cursor.execute("SELECT COALESCE(MAX(orden), -1) + 1 FROM subtareas WHERE habito_id = %s", (habito_id,))
    siguiente_orden = cursor.fetchone()[0]
    cursor.execute(
        "INSERT INTO subtareas (habito_id, nombre, completado, orden) VALUES (%s, %s, 0, %s)",
        (habito_id, nombre, siguiente_orden)
    )
    conexion.commit()
    cursor.close()
    conexion.close()


def marcar_subtarea(subtarea_id, completado):
    conexion = obtener_conexion()
    cursor = conexion.cursor()
    cursor.execute(
        "UPDATE subtareas SET completado = %s WHERE id = %s",
        (1 if completado else 0, subtarea_id)
    )
    conexion.commit()
    cursor.close()
    conexion.close()


def eliminar_subtarea(subtarea_id):
    conexion = obtener_conexion()
    cursor = conexion.cursor()
    cursor.execute("DELETE FROM subtareas WHERE id = %s", (subtarea_id,))
    conexion.commit()
    cursor.close()
    conexion.close()