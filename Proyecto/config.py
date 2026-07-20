"""
Configuración general del proyecto.
Ajusta aquí los datos de conexión a tu servidor MySQL (XAMPP)
y las carpetas donde se guardan los assets (fotos y música).
"""

import os

# --------------------------------------------------------
# Conexión a MySQL (XAMPP)
# --------------------------------------------------------
DB_CONFIG = {
    "host": "localhost",
    "user": "root",
    "password": "",
    "database": "planificador_habitos",
    "port": 3306,
}

# --------------------------------------------------------
# Carpetas de assets
# --------------------------------------------------------
CARPETA_BASE = os.path.dirname(os.path.abspath(__file__))
CARPETA_FOTOS = os.path.join(CARPETA_BASE, "assets", "fotos")
CARPETA_MUSICA = os.path.join(CARPETA_BASE, "assets", "musica")

# --------------------------------------------------------
# Paleta de colores de la aplicación
# --------------------------------------------------------
COLORES_CLARO = {
    "primario": "#6C63FF",
    "primario_oscuro": "#4B45C6",
    "primario_claro": "#EDEBFF",
    "secundario": "#00C2A8",
    "acento": "#FF6B6B",
    "acento_2": "#FFB84D",
    "fondo": "#F4F5FB",
    "tarjeta": "#FFFFFF",
    "texto": "#2B2D42",
    "texto_suave": "#8A8FA3",
    "borde": "#E6E8F0",
}

COLORES_OSCURO = {
    "primario": "#8B83FF",
    "primario_oscuro": "#6C63FF",
    "primario_claro": "#312E50",
    "secundario": "#00D6B8",
    "acento": "#FF7676",
    "acento_2": "#FFC261",
    "fondo": "#181824",
    "tarjeta": "#242435",
    "texto": "#F2F2F7",
    "texto_suave": "#A7A7B8",
    "borde": "#3A3A4F",
}

# El programa empieza usando el modo claro
COLORES = COLORES_CLARO.copy()
# Icono + color por categoría de hábito
CATEGORIAS_INFO = {
    "Salud":    {"icono": "💪", "color": "#00C2A8"},
    "Estudio":  {"icono": "📚", "color": "#6C63FF"},
    "Trabajo":  {"icono": "💼", "color": "#4B45C6"},
    "Personal": {"icono": "🌱", "color": "#FF6B6B"},
    "Otro":     {"icono": "✨", "color": "#FFB84D"},
}

FRASES_MOTIVACION = [
    "¡Cada pequeño paso cuenta! 🚀",
    "La constancia vence al talento. 🔥",
    "Hoy es un gran día para mejorar. 🌤️",
    "Un hábito a la vez, un tú mejor cada día. 💜",
    "¡Vas muy bien, no te detengas! 🏆",
    "El progreso, no la perfección. ✅",
    "¡Sigue así, lo estás logrando! ⭐",
]