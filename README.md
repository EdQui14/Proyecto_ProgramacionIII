# 🎯 HabitTracker

Un seguidor de hábitos simple y eficiente desarrollado en Python, que te permite registrar, monitorear y analizar tus hábitos diarios para fomentar la constancia y el crecimiento personal.

## 📋 Descripción

**HabitTracker** es una aplicación de línea de comandos (o de escritorio, según tu implementación) que ayuda a los usuarios a crear hábitos personalizados, marcarlos como completados día a día, y visualizar su progreso a través de estadísticas y rachas (streaks).

## ✨ Características

- ➕ Crear, editar y eliminar hábitos
- ✅ Marcar hábitos como completados por fecha
- 🔥 Seguimiento de rachas (días consecutivos completando un hábito)
- 📊 Visualización de estadísticas y progreso (porcentaje de cumplimiento)
- 📅 Historial de hábitos por día, semana o mes
- 💾 Persistencia de datos (archivo local o base de datos)
- 🔔 Recordatorios opcionales (si aplica)

## 🛠️ Tecnologías utilizadas

- **Python 3.10+**
- `XAMPP` / `Php` — almacenamiento de datos
- `datetime` — manejo de fechas y cálculo de rachas
- `argparse` / `click` — interfaz de línea de comandos (opcional)
- `matplotlib` — gráficas de progreso (opcional)

## 📦 Instalación

1. Clona el repositorio:
   ```bash
   git clone https://github.com/tu-usuario/habit-tracker.git
   cd habit-tracker
   ```

2. Crea un entorno virtual (recomendado):
   ```bash
   python -m venv venv
   source venv/bin/activate   # En Windows: venv\Scripts\activate
   ```

3. Instala las dependencias:
   ```bash
   pip install -r requirements.txt
   ```

## 🚀 Uso

Ejecuta el programa principal:
```bash
python main.py
```

### Ejemplos de comandos

```bash
# Agregar un nuevo hábito
python main.py add "Leer 20 minutos"

# Marcar un hábito como completado hoy
python main.py check "Leer 20 minutos"

# Ver estadísticas de un hábito
python main.py stats "Leer 20 minutos"

# Listar todos los hábitos
python main.py list
```

## 📂 Estructura del proyecto

```
habit-tracker/
├── main.py                # Punto de entrada de la aplicación
├── habits/
│   ├── __init__.py
│   ├── habit.py            # Clase Habit y lógica principal
│   ├── tracker.py          # Lógica de seguimiento y rachas
│   └── storage.py          # Manejo de persistencia de datos
├── tests/
│   └── test_habit.py       # Pruebas unitarias
├── requirements.txt
└── README.md
```

## 🧪 Pruebas

Para ejecutar las pruebas unitarias:
```bash
python -m pytest tests/
```

## 🗺️ Roadmap / Próximas mejoras

- [ ] Interfaz gráfica (GUI) con Tkinter o PyQt
- [ ] Exportación de datos a CSV/Excel
- [ ] Notificaciones push o por correo
- [ ] Sincronización en la nube
- [ ] Modo multiusuario

## 🤝 Contribuciones

Las contribuciones son bienvenidas. Si deseas colaborar:

1. Haz un fork del proyecto
2. Crea una rama para tu funcionalidad (`git checkout -b feature/nueva-funcionalidad`)
3. Haz commit de tus cambios (`git commit -m 'Agrega nueva funcionalidad'`)
4. Haz push a la rama (`git push origin feature/nueva-funcionalidad`)
5. Abre un Pull Request

## 📄 Licencia

Este proyecto está bajo la licencia MIT. Consulta el archivo `LICENSE` para más detalles.

## ✍️ Autor

Desarrollado por [Alexis Gonzalez, Edson Quintana, Liliana Prospero] — [https://github.com/EdQui14/Proyecto_ProgramacionIII]
