import os
import random
import shutil
import datetime
import tkinter as tk
from tkinter import ttk, messagebox, filedialog

from PIL import Image, ImageTk, ImageDraw
try:
    import pygame
except ImportError:
    pygame = None

audio_disponible = False
if pygame is not None:
    try:
        pygame.mixer.init()
        audio_disponible = True
    except Exception:
        audio_disponible = False

import db
from config import (
    CARPETA_FOTOS,
    CARPETA_MUSICA,
    COLORES,
    COLORES_CLARO,
    COLORES_OSCURO,
    CATEGORIAS_INFO,
    FRASES_MOTIVACION
)
# Crear carpetas de assets si no existen
os.makedirs(CARPETA_FOTOS, exist_ok=True)
os.makedirs(CARPETA_MUSICA, exist_ok=True)

CATEGORIAS = list(CATEGORIAS_INFO.keys())
FRECUENCIAS = ["Diario", "Semanal"]

C = COLORES  # alias corto para la paleta de colores


# ============================================================
# UTILIDADES VISUALES
# ============================================================
def hacer_foto_circular(ruta_o_imagen, tamano=64, borde_color=None, borde_ancho=4):
    """Recorta una imagen (ruta o PIL.Image) en un círculo con antialiasing."""
    escala = 4  # se dibuja más grande y se reduce -> bordes suaves
    tam_grande = tamano * escala

    if isinstance(ruta_o_imagen, str) and os.path.exists(ruta_o_imagen):
        base = Image.open(ruta_o_imagen).convert("RGB")
    elif isinstance(ruta_o_imagen, Image.Image):
        base = ruta_o_imagen.convert("RGB")
    else:
        base = Image.new("RGB", (tam_grande, tam_grande), C["primario_claro"])

    # Recorte tipo "cover" al cuadrado
    lado = min(base.size)
    izq = (base.width - lado) // 2
    arriba = (base.height - lado) // 2
    base = base.crop((izq, arriba, izq + lado, arriba + lado)).resize((tam_grande, tam_grande))

    mascara = Image.new("L", (tam_grande, tam_grande), 0)
    ImageDraw.Draw(mascara).ellipse((0, 0, tam_grande, tam_grande), fill=255)

    resultado = Image.new("RGBA", (tam_grande, tam_grande))
    resultado.paste(base, (0, 0), mascara)
    resultado = resultado.resize((tamano, tamano), Image.LANCZOS)

    if borde_color:
        capa_borde = Image.new("RGBA", (tamano, tamano), (0, 0, 0, 0))
        dibujo = ImageDraw.Draw(capa_borde)
        dibujo.ellipse((0, 0, tamano - 1, tamano - 1), outline=borde_color, width=borde_ancho)
        resultado = Image.alpha_composite(resultado, capa_borde)

    return resultado


def configurar_estilos():
    estilo = ttk.Style()
    try:
        estilo.theme_use("clam")
    except tk.TclError:
        pass

    estilo.configure("TScrollbar", background=C["primario_claro"], troughcolor=C["fondo"],
                      bordercolor=C["fondo"], arrowcolor=C["primario"])

    # Una barra de progreso "genérica" + una por cada color de categoría
    def _config_barra(nombre, color):
        estilo.configure(nombre, troughcolor=C["borde"], background=color,
                          bordercolor=C["fondo"], lightcolor=color, darkcolor=color,
                          thickness=10)

    _config_barra("General.Horizontal.TProgressbar", C["secundario"])
    for info in CATEGORIAS_INFO.values():
        _config_barra(f'{info["color"]}.Horizontal.TProgressbar', info["color"])

    return estilo


# ============================================================
# WIDGET: ANILLO DE PROGRESO (canvas circular decorativo)
# ============================================================
class AnilloProgreso(tk.Canvas):
    def __init__(self, parent, tamano=90, grosor=10, **kwargs):
        super().__init__(parent, width=tamano, height=tamano, bg=kwargs.pop("bg", C["primario"]),
                          highlightthickness=0, **kwargs)
        self.tamano = tamano
        self.grosor = grosor
        self.set_progreso(0)

    def set_progreso(self, porcentaje):
        porcentaje = max(0, min(100, porcentaje))
        self.delete("all")
        pad = self.grosor
        caja = (pad, pad, self.tamano - pad, self.tamano - pad)

        # Pista de fondo
        self.create_oval(*caja, outline="white", width=self.grosor)
        # Arco de progreso (empieza arriba, sentido horario)
        if porcentaje > 0:
            self.create_arc(*caja, start=90, extent=-360 * (porcentaje / 100),
                             style="arc", outline="white", width=self.grosor)

        self.create_text(self.tamano / 2, self.tamano / 2, text=f"{int(porcentaje)}%",
                          fill="white", font=("Segoe UI", 14, "bold"))


# ============================================================
# VENTANA PRINCIPAL (controlador de "páginas")
# ============================================================
class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.modo_oscuro = False
        C.clear()
        C.update(COLORES_CLARO)
        self.colores = C
        self.configure(bg=self.colores["fondo"])
        self.title("✨ Planificador de Hábitos")
        self.geometry("1000x660")
        self.minsize(880, 600)
        self.configure(bg=C["fondo"])

        configurar_estilos()

        try:
            db.inicializar_base_datos()
        except ConnectionError as e:
            messagebox.showerror("Error de conexión", str(e))

        self.usuario_actual = None
        self.musica_reproduciendo = False
        self.ruta_musica_actual = None

        contenedor = tk.Frame(self, bg=C["fondo"])
        contenedor.pack(fill="both", expand=True)
        contenedor.grid_rowconfigure(0, weight=1)
        contenedor.grid_columnconfigure(0, weight=1)

        self.frames = {}
        for F in (LoginFrame, RegistroFrame, PanelFrame, EstadisticasFrame, LogrosFrame, PomodoroFrame):
            frame = F(contenedor, self)
            self.frames[F] = frame
            frame.grid(row=0, column=0, sticky="nsew")

        self.mostrar_frame(LoginFrame)
        self.protocol("WM_DELETE_WINDOW", self.al_cerrar)

    def mostrar_frame(self, clase):
        frame = self.frames[clase]
        if clase in (PanelFrame, EstadisticasFrame, LogrosFrame, PomodoroFrame):
            frame.cargar_datos()
        frame.tkraise()

    def al_cerrar(self):
        if pygame is not None:
            try:
                pygame.mixer.music.stop()
            except Exception:
                pass
        self.destroy()

    def cambiar_tema(self):
        """Alterna entre la paleta clara y la oscura sin recrear las pantallas."""
        paleta_anterior = self.colores.copy()
        self.modo_oscuro = not self.modo_oscuro
        nueva_paleta = COLORES_OSCURO if self.modo_oscuro else COLORES_CLARO

        # C es un alias global utilizado por todas las pantallas.
        # Se actualiza en el mismo objeto para que las referencias existentes sigan funcionando.
        C.clear()
        C.update(nueva_paleta)
        self.colores = C

        self.configure(bg=C["fondo"])
        self.aplicar_tema_widget(self, paleta_anterior, C)
        configurar_estilos()

        texto_boton = "☀️ Modo claro" if self.modo_oscuro else "🌙 Modo oscuro"
        panel = self.frames.get(PanelFrame)
        if panel is not None and hasattr(panel, "btn_tema"):
            panel.btn_tema.configure(text=texto_boton)

        # Redibuja elementos creados dinámicamente.
        if panel is not None and self.usuario_actual:
            panel.refrescar_lista_habitos()

        estadisticas = self.frames.get(EstadisticasFrame)
        if estadisticas is not None and self.usuario_actual:
            estadisticas.cargar_datos()

        logros = self.frames.get(LogrosFrame)
        if logros is not None and self.usuario_actual:
            logros.cargar_datos()

        pomodoro = self.frames.get(PomodoroFrame)
        if pomodoro is not None:
            pomodoro.actualizar_tema()

    def aplicar_tema_widget(self, widget, paleta_anterior, nueva_paleta):
        """Sustituye únicamente colores pertenecientes a la paleta anterior."""
        reemplazos = {
            paleta_anterior[clave].lower(): nueva_paleta[clave]
            for clave in paleta_anterior
            if clave in nueva_paleta
        }

        # Algunos elementos originales usan literalmente "white" como fondo de tarjeta.
        reemplazos_fondo = dict(reemplazos)
        reemplazos_fondo["white"] = nueva_paleta["tarjeta"]

        opciones_color = (
            "background", "foreground", "activebackground", "activeforeground",
            "highlightbackground", "highlightcolor", "insertbackground",
            "selectbackground", "selectforeground", "selectcolor", "troughcolor"
        )

        cambios = {}
        for opcion in opciones_color:
            try:
                valor = str(widget.cget(opcion))
            except (tk.TclError, KeyError):
                continue

            mapa = reemplazos_fondo if opcion in {
                "background", "activebackground", "highlightbackground",
                "highlightcolor", "selectbackground", "selectcolor", "troughcolor"
            } else reemplazos

            nuevo_valor = mapa.get(valor.lower())
            if nuevo_valor:
                cambios[opcion] = nuevo_valor

        if cambios:
            try:
                widget.configure(**cambios)
            except tk.TclError:
                pass

        for hijo in widget.winfo_children():
            self.aplicar_tema_widget(hijo, paleta_anterior, nueva_paleta)


# ============================================================
# PANTALLA: LOGIN
# ============================================================
class LoginFrame(tk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent, bg=C["primario"])
        self.controller = controller

        tarjeta = tk.Frame(self, bg="white", padx=40, pady=40)
        tarjeta.place(relx=0.5, rely=0.5, anchor="center")

        tk.Label(tarjeta, text="🌟", font=("Segoe UI", 30), bg="white").pack()
        tk.Label(tarjeta, text="Planificador de Hábitos", font=("Segoe UI", 20, "bold"),
                 bg="white", fg=C["texto"]).pack(pady=(0, 4))
        tk.Label(tarjeta, text="Construye una mejor rutina, un día a la vez",
                 font=("Segoe UI", 10), bg="white", fg=C["texto_suave"]).pack(pady=(0, 20))

        tk.Label(tarjeta, text="Usuario", bg="white", fg=C["texto_suave"], anchor="w").pack(fill="x")
        self.entry_usuario = tk.Entry(tarjeta, width=30, font=("Segoe UI", 11),
                                       relief="flat", bg=C["fondo"])
        self.entry_usuario.pack(pady=(2, 12), ipady=5)

        tk.Label(tarjeta, text="Contraseña", bg="white", fg=C["texto_suave"], anchor="w").pack(fill="x")
        self.entry_contrasena = tk.Entry(tarjeta, width=30, font=("Segoe UI", 11), show="•",
                                          relief="flat", bg=C["fondo"])
        self.entry_contrasena.pack(pady=(2, 20), ipady=5)
        self.entry_contrasena.bind("<Return>", lambda e: self.iniciar_sesion())

        tk.Button(tarjeta, text="Iniciar sesión", bg=C["primario"], fg="white",
                  font=("Segoe UI", 11, "bold"), relief="flat", width=25, pady=8,
                  activebackground=C["primario_oscuro"], activeforeground="white", cursor="hand2",
                  command=self.iniciar_sesion).pack(pady=(0, 10))

        tk.Button(tarjeta, text="¿No tienes cuenta? Regístrate", bg="white", fg=C["primario"],
                  relief="flat", cursor="hand2",
                  command=lambda: controller.mostrar_frame(RegistroFrame)).pack()

    def iniciar_sesion(self):
        usuario = self.entry_usuario.get().strip()
        contrasena = self.entry_contrasena.get().strip()

        if not usuario or not contrasena:
            messagebox.showwarning("Campos vacíos", "Ingresa usuario y contraseña.")
            return

        try:
            datos = db.verificar_login(usuario, contrasena)
        except ConnectionError as e:
            messagebox.showerror("Error de conexión", str(e))
            return

        if datos:
            self.controller.usuario_actual = datos
            self.entry_usuario.delete(0, tk.END)
            self.entry_contrasena.delete(0, tk.END)
            self.controller.mostrar_frame(PanelFrame)
        else:
            messagebox.showerror("Error", "Usuario o contraseña incorrectos.")


# ============================================================
# PANTALLA: REGISTRO
# ============================================================
class RegistroFrame(tk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent, bg=C["primario"])
        self.controller = controller
        self.ruta_foto_seleccionada = None

        tarjeta = tk.Frame(self, bg="white", padx=40, pady=25)
        tarjeta.place(relx=0.5, rely=0.5, anchor="center")

        tk.Label(tarjeta, text="Crear cuenta", font=("Segoe UI", 20, "bold"),
                 bg="white", fg=C["texto"]).pack(pady=(0, 15))

        for etiqueta, attr, oculto in [
            ("Nombre completo", "entry_nombre", False),
            ("Usuario", "entry_usuario", False),
            ("Contraseña", "entry_contrasena", True),
            ("Confirmar contraseña", "entry_confirmar", True),
        ]:
            tk.Label(tarjeta, text=etiqueta, bg="white", fg=C["texto_suave"], anchor="w").pack(fill="x")
            entrada = tk.Entry(tarjeta, width=32, font=("Segoe UI", 11), relief="flat",
                                bg=C["fondo"], show="•" if oculto else "")
            entrada.pack(pady=(2, 8), ipady=4)
            setattr(self, attr, entrada)

        self.boton_foto = tk.Button(tarjeta, text="📷  Elegir foto de perfil (opcional)",
                                     command=self.elegir_foto, relief="flat", bg=C["primario_claro"],
                                     fg=C["primario_oscuro"], cursor="hand2")
        self.boton_foto.pack(pady=(6, 8), fill="x")
        self.label_foto = tk.Label(tarjeta, text="Ninguna foto seleccionada", bg="white", fg="gray")
        self.label_foto.pack(pady=(0, 12))

        tk.Button(tarjeta, text="Registrarme", bg=C["primario"], fg="white",
                  font=("Segoe UI", 11, "bold"), relief="flat", width=25, pady=8, cursor="hand2",
                  activebackground=C["primario_oscuro"], activeforeground="white",
                  command=self.registrar).pack(pady=(0, 10))

        tk.Button(tarjeta, text="Volver al inicio de sesión", bg="white", fg=C["primario"],
                  relief="flat", cursor="hand2",
                  command=lambda: controller.mostrar_frame(LoginFrame)).pack()

    def elegir_foto(self):
        ruta = filedialog.askopenfilename(
            title="Selecciona una foto de perfil",
            filetypes=[("Imágenes", "*.png *.jpg *.jpeg *.gif")]
        )
        if ruta:
            self.ruta_foto_seleccionada = ruta
            self.label_foto.config(text=os.path.basename(ruta), fg=C["texto"])

    def registrar(self):
        nombre = self.entry_nombre.get().strip()
        usuario = self.entry_usuario.get().strip()
        contrasena = self.entry_contrasena.get().strip()
        confirmar = self.entry_confirmar.get().strip()

        if not nombre or not usuario or not contrasena:
            messagebox.showwarning("Campos vacíos", "Completa todos los campos obligatorios.")
            return
        if contrasena != confirmar:
            messagebox.showwarning("Error", "Las contraseñas no coinciden.")
            return

        foto_guardada = None
        if self.ruta_foto_seleccionada:
            extension = os.path.splitext(self.ruta_foto_seleccionada)[1]
            nombre_archivo = f"{usuario}{extension}"
            destino = os.path.join(CARPETA_FOTOS, nombre_archivo)
            shutil.copy(self.ruta_foto_seleccionada, destino)
            foto_guardada = destino

        try:
            ok, mensaje = db.registrar_usuario(nombre, usuario, contrasena, foto_guardada)
        except ConnectionError as e:
            messagebox.showerror("Error de conexión", str(e))
            return

        if ok:
            messagebox.showinfo("Éxito", mensaje)
            self.controller.mostrar_frame(LoginFrame)
            self._limpiar_formulario()
        else:
            messagebox.showerror("Error", mensaje)

    def _limpiar_formulario(self):
        self.entry_nombre.delete(0, tk.END)
        self.entry_usuario.delete(0, tk.END)
        self.entry_contrasena.delete(0, tk.END)
        self.entry_confirmar.delete(0, tk.END)
        self.ruta_foto_seleccionada = None
        self.label_foto.config(text="Ninguna foto seleccionada", fg="gray")


# ============================================================
# TARJETA DE UN HÁBITO (con subtareas y barra de progreso)
# ============================================================
class HabitoCard(tk.Frame):
    def __init__(self, parent, panel, habito):
        super().__init__(parent, bg=C["tarjeta"])
        self.panel = panel
        self.habito = habito
        self.expandido = False

        info_cat = CATEGORIAS_INFO.get(habito["categoria"], CATEGORIAS_INFO["Otro"])
        self.color_categoria = info_cat["color"]

        self.configure(highlightbackground=C["borde"], highlightthickness=1)
        self.contenedor = tk.Frame(self, bg=C["tarjeta"])
        self.contenedor.pack(fill="x")

        # Barra de color lateral según categoría
        tk.Frame(self.contenedor, bg=self.color_categoria, width=6).pack(side="left", fill="y")

        cuerpo = tk.Frame(self.contenedor, bg=C["tarjeta"], padx=12, pady=10)
        cuerpo.pack(side="left", fill="both", expand=True)

        # --- Fila superior: nombre + acciones ---
        fila_top = tk.Frame(cuerpo, bg=C["tarjeta"])
        fila_top.pack(fill="x")

        self.boton_expandir = tk.Button(
            fila_top, text="▸", bg=C["tarjeta"], relief="flat", bd=0, cursor="hand2",
            font=("Segoe UI", 11, "bold"), fg=C["texto_suave"], command=self.alternar_expandido
        )
        self.boton_expandir.pack(side="left")

        titulo = f'{info_cat["icono"]}  {habito["nombre"]}'
        tk.Label(fila_top, text=titulo, font=("Segoe UI", 12, "bold"), bg=C["tarjeta"],
                 fg=C["texto"]).pack(side="left", padx=(4, 10))

        if habito["completado_hoy"]:
            tk.Label(fila_top, text="✔ Completado", bg=C["primario_claro"], fg=C["secundario"],
                     font=("Segoe UI", 9, "bold"), padx=8, pady=2).pack(side="left")

        tk.Button(fila_top, text="🗑", fg="white", bg=C["acento"], relief="flat", bd=0,
                  cursor="hand2", padx=8,
                  command=lambda: self.panel.eliminar_habito(habito["id"])).pack(side="right")

        if habito["racha"] and habito["racha"] > 0:
            tk.Label(fila_top, text=f'🔥 {habito["racha"]} días', bg=C["tarjeta"],
                     fg=C["acento_2"], font=("Segoe UI", 9, "bold")).pack(side="right", padx=10)

        tk.Label(fila_top, text=f'{habito["progreso"]}%', bg=C["tarjeta"], fg=self.color_categoria,
                 font=("Segoe UI", 10, "bold")).pack(side="right", padx=10)

        # --- Subtítulo: categoría / frecuencia ---
        tk.Label(cuerpo, text=f'{habito["categoria"]}  •  {habito["frecuencia"]}',
                 bg=C["tarjeta"], fg=C["texto_suave"], font=("Segoe UI", 9),
                 anchor="w").pack(fill="x", padx=(20, 0))

        # --- Barra de progreso del hábito ---
        estilo_barra = f'{self.color_categoria}.Horizontal.TProgressbar'
        self.barra = ttk.Progressbar(cuerpo, style=estilo_barra, orient="horizontal",
                                      mode="determinate", maximum=100, value=habito["progreso"])
        self.barra.pack(fill="x", pady=(8, 0), padx=(20, 0))

        # --- Zona expandible de subtareas ---
        self.zona_subtareas = tk.Frame(cuerpo, bg=C["tarjeta"])

        if not habito["subtareas"]:
            self.var_check_simple = tk.BooleanVar(value=bool(habito["completado_hoy"]))
        else:
            self.var_check_simple = None

        self._construir_zona_subtareas()

    def _construir_zona_subtareas(self):
        for w in self.zona_subtareas.winfo_children():
            w.destroy()

        contenido = tk.Frame(self.zona_subtareas, bg=C["tarjeta"], padx=20, pady=8)
        contenido.pack(fill="x")

        if self.habito["subtareas"]:
            for sub in self.habito["subtareas"]:
                fila = tk.Frame(contenido, bg=C["fondo"])
                fila.pack(fill="x", pady=2)

                var = tk.BooleanVar(value=bool(sub["completado"]))
                tk.Checkbutton(
                    fila, variable=var, bg=C["fondo"], activebackground=C["fondo"],
                    command=lambda s=sub["id"], v=var: self.panel.marcar_subtarea(s, v)
                ).pack(side="left", padx=(4, 0))

                texto = sub["nombre"]
                if sub["completado"]:
                    tk.Label(fila, text=texto, bg=C["fondo"], fg=C["texto_suave"],
                             font=("Segoe UI", 10, "overstrike")).pack(side="left", padx=6, fill="x", expand=True)
                else:
                    tk.Label(fila, text=texto, bg=C["fondo"], fg=C["texto"],
                             font=("Segoe UI", 10)).pack(side="left", padx=6, fill="x", expand=True)

                tk.Button(fila, text="✕", bg=C["fondo"], fg=C["acento"], relief="flat", bd=0,
                          cursor="hand2",
                          command=lambda s=sub["id"]: self.panel.eliminar_subtarea(s)
                          ).pack(side="right", padx=4)
        else:
            fila_simple = tk.Frame(contenido, bg=C["fondo"])
            fila_simple.pack(fill="x", pady=2)
            tk.Checkbutton(
                fila_simple, text="Marcar como completado hoy", variable=self.var_check_simple,
                bg=C["fondo"], activebackground=C["fondo"],
                command=lambda: self.panel.marcar_completado(self.habito["id"], self.var_check_simple)
            ).pack(side="left", padx=4, fill="x", expand=True)

        # --- Añadir nueva subtarea ---
        fila_nueva = tk.Frame(contenido, bg=C["tarjeta"])
        fila_nueva.pack(fill="x", pady=(8, 0))
        entrada = tk.Entry(fila_nueva, font=("Segoe UI", 10), relief="flat", bg=C["fondo"])
        entrada.pack(side="left", fill="x", expand=True, ipady=3)
        entrada.bind("<Return>", lambda e: self._agregar(entrada))
        tk.Button(fila_nueva, text="+ Subtarea", bg=C["primario_claro"], fg=C["primario_oscuro"],
                  relief="flat", cursor="hand2",
                  command=lambda: self._agregar(entrada)).pack(side="left", padx=(6, 0))

    def _agregar(self, entrada):
        texto = entrada.get().strip()
        if texto:
            self.panel.agregar_subtarea(self.habito["id"], texto)

    def alternar_expandido(self):
        self.expandido = not self.expandido
        if self.expandido:
            self.boton_expandir.config(text="▾")
            self.zona_subtareas.pack(fill="x")
        else:
            self.boton_expandir.config(text="▸")
            self.zona_subtareas.pack_forget()


# ============================================================
# PANTALLA: ESTADÍSTICAS
# ============================================================
class EstadisticasFrame(tk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent, bg=C["fondo"])
        self.controller = controller

        barra_superior = tk.Frame(self, bg=C["primario"], height=82)
        barra_superior.pack(fill="x")
        barra_superior.pack_propagate(False)

        tk.Label(
            barra_superior,
            text="📊 Estadísticas",
            font=("Segoe UI", 20, "bold"),
            bg=C["primario"],
            fg="white"
        ).pack(side="left", padx=24)

        tk.Button(
            barra_superior,
            text="← Volver a mis hábitos",
            command=lambda: controller.mostrar_frame(PanelFrame),
            bg="white",
            fg=C["primario"],
            activebackground=C["primario_claro"],
            activeforeground=C["primario_oscuro"],
            relief="flat",
            cursor="hand2",
            font=("Segoe UI", 10, "bold"),
            padx=12,
            pady=7
        ).pack(side="right", padx=24)

        self.contenido = tk.Frame(self, bg=C["fondo"])
        self.contenido.pack(fill="both", expand=True, padx=22, pady=18)

    def cargar_datos(self):
        usuario = self.controller.usuario_actual
        if not usuario:
            return

        for widget in self.contenido.winfo_children():
            widget.destroy()

        try:
            datos = db.obtener_estadisticas(usuario["id"])
        except ConnectionError as e:
            messagebox.showerror("Error de conexión", str(e))
            return

        encabezado = tk.Frame(self.contenido, bg=C["fondo"])
        encabezado.pack(fill="x", pady=(0, 14))

        tk.Label(
            encabezado,
            text=f"Resumen de {usuario['nombre']}",
            font=("Segoe UI", 17, "bold"),
            bg=C["fondo"],
            fg=C["texto"]
        ).pack(side="left")

        tk.Label(
            encabezado,
            text=datetime.date.today().strftime("%d/%m/%Y"),
            font=("Segoe UI", 10),
            bg=C["fondo"],
            fg=C["texto_suave"]
        ).pack(side="right")

        tarjetas = tk.Frame(self.contenido, bg=C["fondo"])
        tarjetas.pack(fill="x")

        resumen = [
            ("📋", "Hábitos totales", datos["total_habitos"], C["primario"]),
            ("✅", "Completados hoy", datos["completados_hoy"], C["secundario"]),
            ("⏳", "Pendientes hoy", datos["pendientes_hoy"], C["acento_2"]),
            ("📈", "Cumplimiento", f'{datos["porcentaje_hoy"]}%', C["primario_oscuro"]),
        ]

        for columna, (icono, titulo, valor, color) in enumerate(resumen):
            tarjetas.grid_columnconfigure(columna, weight=1)
            tarjeta = tk.Frame(
                tarjetas,
                bg=C["tarjeta"],
                highlightbackground=C["borde"],
                highlightthickness=1,
                padx=14,
                pady=12
            )
            tarjeta.grid(row=0, column=columna, sticky="nsew", padx=6)

            tk.Label(tarjeta, text=icono, font=("Segoe UI Emoji", 19),
                     bg=C["tarjeta"]).pack()
            tk.Label(tarjeta, text=str(valor), font=("Segoe UI", 20, "bold"),
                     bg=C["tarjeta"], fg=color).pack()
            tk.Label(tarjeta, text=titulo, font=("Segoe UI", 9),
                     bg=C["tarjeta"], fg=C["texto_suave"]).pack()

        zona_inferior = tk.Frame(self.contenido, bg=C["fondo"])
        zona_inferior.pack(fill="both", expand=True, pady=(16, 0))
        zona_inferior.grid_columnconfigure(0, weight=1)
        zona_inferior.grid_columnconfigure(1, weight=2)
        zona_inferior.grid_rowconfigure(0, weight=1)

        # Tarjeta de racha y subtareas
        detalle = tk.Frame(
            zona_inferior,
            bg=C["tarjeta"],
            highlightbackground=C["borde"],
            highlightthickness=1,
            padx=18,
            pady=16
        )
        detalle.grid(row=0, column=0, sticky="nsew", padx=(6, 8))

        tk.Label(detalle, text="🏆 Rendimiento", font=("Segoe UI", 13, "bold"),
                 bg=C["tarjeta"], fg=C["texto"]).pack(anchor="w", pady=(0, 14))

        tk.Label(detalle, text="🔥 Mejor racha", bg=C["tarjeta"],
                 fg=C["texto_suave"], font=("Segoe UI", 10)).pack(anchor="w")
        tk.Label(detalle, text=f'{datos["mejor_racha"]} días',
                 bg=C["tarjeta"], fg=C["acento_2"],
                 font=("Segoe UI", 22, "bold")).pack(anchor="w")

        tk.Label(detalle, text="Hábito con mayor racha", bg=C["tarjeta"],
                 fg=C["texto_suave"], font=("Segoe UI", 9)).pack(anchor="w", pady=(12, 2))
        tk.Label(detalle, text=datos["habito_mejor_racha"], bg=C["tarjeta"],
                 fg=C["texto"], font=("Segoe UI", 11, "bold"),
                 wraplength=240, justify="left").pack(anchor="w")

        tk.Frame(detalle, bg=C["borde"], height=1).pack(fill="x", pady=14)

        tk.Label(detalle, text="Subtareas completadas hoy", bg=C["tarjeta"],
                 fg=C["texto_suave"], font=("Segoe UI", 9)).pack(anchor="w")
        tk.Label(
            detalle,
            text=f'{datos["subtareas_completadas"]}/{datos["total_subtareas"]}',
            bg=C["tarjeta"],
            fg=C["secundario"],
            font=("Segoe UI", 16, "bold")
        ).pack(anchor="w")

        # Categorías
        categorias_frame = tk.Frame(
            zona_inferior,
            bg=C["tarjeta"],
            highlightbackground=C["borde"],
            highlightthickness=1,
            padx=18,
            pady=16
        )
        categorias_frame.grid(row=0, column=1, sticky="nsew", padx=(8, 6))

        tk.Label(categorias_frame, text="📚 Progreso por categoría",
                 font=("Segoe UI", 13, "bold"), bg=C["tarjeta"],
                 fg=C["texto"]).pack(anchor="w", pady=(0, 12))

        categorias = datos["categorias"]
        if not categorias:
            tk.Label(
                categorias_frame,
                text="Todavía no hay hábitos para mostrar.",
                bg=C["tarjeta"],
                fg=C["texto_suave"],
                font=("Segoe UI", 10)
            ).pack(pady=30)
            return

        for categoria in CATEGORIAS:
            info = categorias.get(categoria)
            if not info:
                continue

            total = info["total"]
            completados = info["completados"]
            porcentaje = int(round((completados / total) * 100)) if total else 0
            color = CATEGORIAS_INFO.get(categoria, CATEGORIAS_INFO["Otro"])["color"]
            icono = CATEGORIAS_INFO.get(categoria, CATEGORIAS_INFO["Otro"])["icono"]

            fila = tk.Frame(categorias_frame, bg=C["tarjeta"])
            fila.pack(fill="x", pady=6)

            cabecera = tk.Frame(fila, bg=C["tarjeta"])
            cabecera.pack(fill="x")
            tk.Label(cabecera, text=f"{icono} {categoria}",
                     bg=C["tarjeta"], fg=C["texto"],
                     font=("Segoe UI", 10, "bold")).pack(side="left")
            tk.Label(cabecera, text=f"{completados}/{total}  •  {porcentaje}%",
                     bg=C["tarjeta"], fg=C["texto_suave"],
                     font=("Segoe UI", 9)).pack(side="right")

            barra_fondo = tk.Frame(fila, bg=C["borde"], height=10)
            barra_fondo.pack(fill="x", pady=(4, 0))
            barra_fondo.pack_propagate(False)

            if porcentaje > 0:
                barra = tk.Frame(barra_fondo, bg=color)
                barra.place(relx=0, rely=0, relwidth=porcentaje / 100, relheight=1)


# ============================================================
# PANTALLA: LOGROS Y NIVEL
# ============================================================
class LogrosFrame(tk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent, bg=C["fondo"])
        self.controller = controller

        barra_superior = tk.Frame(self, bg=C["primario"], height=82)
        barra_superior.pack(fill="x")
        barra_superior.pack_propagate(False)

        tk.Label(
            barra_superior,
            text="🏆 Logros y nivel",
            font=("Segoe UI", 20, "bold"),
            bg=C["primario"],
            fg="white",
        ).pack(side="left", padx=24)

        tk.Button(
            barra_superior,
            text="← Volver a mis hábitos",
            command=lambda: controller.mostrar_frame(PanelFrame),
            bg="white",
            fg=C["primario"],
            activebackground=C["primario_claro"],
            activeforeground=C["primario_oscuro"],
            relief="flat",
            cursor="hand2",
            font=("Segoe UI", 10, "bold"),
            padx=12,
            pady=7,
        ).pack(side="right", padx=24)

        self.contenido = tk.Frame(self, bg=C["fondo"])
        self.contenido.pack(fill="both", expand=True, padx=22, pady=18)

    def cargar_datos(self):
        usuario = self.controller.usuario_actual
        if not usuario:
            return

        for widget in self.contenido.winfo_children():
            widget.destroy()

        try:
            datos = db.obtener_logros(usuario["id"])
        except ConnectionError as e:
            messagebox.showerror("Error de conexión", str(e))
            return

        resumen = tk.Frame(
            self.contenido,
            bg=C["tarjeta"],
            highlightbackground=C["borde"],
            highlightthickness=1,
            padx=18,
            pady=16,
        )
        resumen.pack(fill="x", pady=(0, 14))

        tk.Label(
            resumen,
            text=f"Nivel {datos['nivel']}",
            font=("Segoe UI", 22, "bold"),
            bg=C["tarjeta"],
            fg=C["primario"],
        ).pack(side="left")

        info = tk.Frame(resumen, bg=C["tarjeta"])
        info.pack(side="left", fill="x", expand=True, padx=22)
        tk.Label(
            info,
            text=f"{datos['xp_total']} XP totales  •  {datos['desbloqueados']}/{datos['total']} logros",
            font=("Segoe UI", 10, "bold"),
            bg=C["tarjeta"],
            fg=C["texto"],
        ).pack(anchor="w")

        barra_fondo = tk.Frame(info, bg=C["borde"], height=12)
        barra_fondo.pack(fill="x", pady=(7, 2))
        barra_fondo.pack_propagate(False)
        progreso = datos["xp_nivel"] / datos["xp_siguiente"]
        if progreso > 0:
            tk.Frame(barra_fondo, bg=C["secundario"]).place(
                relx=0, rely=0, relwidth=progreso, relheight=1
            )
        tk.Label(
            info,
            text=f"{datos['xp_nivel']}/{datos['xp_siguiente']} XP para el siguiente nivel",
            font=("Segoe UI", 9),
            bg=C["tarjeta"],
            fg=C["texto_suave"],
        ).pack(anchor="w")

        contenedor_lista = tk.Frame(self.contenido, bg=C["fondo"])
        contenedor_lista.pack(fill="both", expand=True)

        canvas = tk.Canvas(contenedor_lista, bg=C["fondo"], highlightthickness=0)
        scrollbar = ttk.Scrollbar(contenedor_lista, orient="vertical", command=canvas.yview)
        lista = tk.Frame(canvas, bg=C["fondo"])
        lista.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=lista, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        for indice, logro in enumerate(datos["logros"]):
            desbloqueado = logro["desbloqueado"]
            tarjeta = tk.Frame(
                lista,
                bg=C["tarjeta"],
                highlightbackground=C["secundario"] if desbloqueado else C["borde"],
                highlightthickness=2 if desbloqueado else 1,
                padx=16,
                pady=13,
            )
            tarjeta.grid(row=indice // 2, column=indice % 2, sticky="nsew", padx=6, pady=6)
            lista.grid_columnconfigure(indice % 2, weight=1)

            tk.Label(
                tarjeta,
                text=logro["icono"] if desbloqueado else "🔒",
                font=("Segoe UI Emoji", 24),
                bg=C["tarjeta"],
            ).pack(side="left", padx=(0, 12))

            texto = tk.Frame(tarjeta, bg=C["tarjeta"])
            texto.pack(side="left", fill="both", expand=True)
            tk.Label(
                texto,
                text=logro["nombre"],
                font=("Segoe UI", 12, "bold"),
                bg=C["tarjeta"],
                fg=C["texto"] if desbloqueado else C["texto_suave"],
            ).pack(anchor="w")
            tk.Label(
                texto,
                text=logro["descripcion"],
                font=("Segoe UI", 9),
                bg=C["tarjeta"],
                fg=C["texto_suave"],
                wraplength=310,
                justify="left",
            ).pack(anchor="w", pady=(2, 5))

            estado = f"+{logro['xp']} XP"
            if desbloqueado and logro["fecha_desbloqueo"]:
                fecha = logro["fecha_desbloqueo"]
                estado += f"  •  {fecha.strftime('%d/%m/%Y')}"
            elif not desbloqueado:
                estado += "  •  Bloqueado"

            tk.Label(
                texto,
                text=estado,
                font=("Segoe UI", 9, "bold"),
                bg=C["tarjeta"],
                fg=C["secundario"] if desbloqueado else C["texto_suave"],
            ).pack(anchor="w")


# ============================================================
# PANTALLA: TEMPORIZADOR POMODORO
# ============================================================
class PomodoroFrame(tk.Frame):
    DURACION_TRABAJO = 25 * 60
    DURACION_DESCANSO = 5 * 60

    def __init__(self, parent, controller):
        super().__init__(parent, bg=C["fondo"])
        self.controller = controller
        self.segundos_restantes = self.DURACION_TRABAJO
        self.en_ejecucion = False
        self.es_descanso = False
        self.identificador_after = None
        self.sesiones_completadas = 0

        barra = tk.Frame(self, bg=C["primario"], height=80)
        barra.pack(fill="x")
        barra.pack_propagate(False)

        tk.Label(
            barra, text="🍅 Pomodoro", font=("Segoe UI", 20, "bold"),
            bg=C["primario"], fg="white"
        ).pack(side="left", padx=25)

        tk.Button(
            barra, text="← Volver a mis hábitos",
            command=lambda: controller.mostrar_frame(PanelFrame),
            bg="white", fg=C["primario"], relief="flat", cursor="hand2",
            font=("Segoe UI", 10, "bold"), padx=12, pady=7
        ).pack(side="right", padx=25)

        cuerpo = tk.Frame(self, bg=C["fondo"])
        cuerpo.pack(fill="both", expand=True, padx=35, pady=25)

        tarjeta = tk.Frame(
            cuerpo, bg=C["tarjeta"], padx=45, pady=30,
            highlightbackground=C["borde"], highlightthickness=1
        )
        tarjeta.place(relx=0.5, rely=0.48, anchor="center")

        self.label_estado = tk.Label(
            tarjeta, text="Tiempo de concentración",
            font=("Segoe UI", 16, "bold"), bg=C["tarjeta"], fg=C["texto"]
        )
        self.label_estado.pack(pady=(0, 8))

        self.label_indicacion = tk.Label(
            tarjeta, text="Trabaja durante 25 minutos y después descansa 5.",
            font=("Segoe UI", 10), bg=C["tarjeta"], fg=C["texto_suave"]
        )
        self.label_indicacion.pack(pady=(0, 18))

        self.label_tiempo = tk.Label(
            tarjeta, text="25:00", font=("Segoe UI", 52, "bold"),
            bg=C["tarjeta"], fg=C["primario"]
        )
        self.label_tiempo.pack(pady=8)

        self.barra_tiempo = ttk.Progressbar(
            tarjeta, style="General.Horizontal.TProgressbar", orient="horizontal",
            mode="determinate", maximum=self.DURACION_TRABAJO,
            value=self.DURACION_TRABAJO, length=420
        )
        self.barra_tiempo.pack(pady=(5, 22))

        botones = tk.Frame(tarjeta, bg=C["tarjeta"])
        botones.pack()

        self.btn_iniciar = tk.Button(
            botones, text="▶ Iniciar", command=self.iniciar_pausar,
            bg=C["primario"], fg="white", activebackground=C["primario_oscuro"],
            activeforeground="white", relief="flat", cursor="hand2",
            font=("Segoe UI", 11, "bold"), width=12, pady=8
        )
        self.btn_iniciar.pack(side="left", padx=5)

        tk.Button(
            botones, text="↺ Reiniciar", command=self.reiniciar,
            bg=C["primario_claro"], fg=C["primario_oscuro"], relief="flat",
            cursor="hand2", font=("Segoe UI", 11, "bold"), width=12, pady=8
        ).pack(side="left", padx=5)

        tk.Button(
            botones, text="⇄ Cambiar fase", command=self.cambiar_fase_manual,
            bg=C["secundario"], fg="white", relief="flat", cursor="hand2",
            font=("Segoe UI", 11, "bold"), width=14, pady=8
        ).pack(side="left", padx=5)

        self.label_sesiones = tk.Label(
            tarjeta, text="Sesiones completadas: 0", font=("Segoe UI", 10, "bold"),
            bg=C["tarjeta"], fg=C["texto_suave"]
        )
        self.label_sesiones.pack(pady=(22, 0))

    def cargar_datos(self):
        self.actualizar_pantalla()

    def actualizar_tema(self):
        self.configure(bg=C["fondo"])
        self.actualizar_pantalla()

    def iniciar_pausar(self):
        if self.en_ejecucion:
            self.en_ejecucion = False
            self.btn_iniciar.config(text="▶ Continuar")
            if self.identificador_after is not None:
                self.after_cancel(self.identificador_after)
                self.identificador_after = None
            return

        self.en_ejecucion = True
        self.btn_iniciar.config(text="⏸ Pausar")
        self._cuenta_regresiva()

    def _cuenta_regresiva(self):
        if not self.en_ejecucion:
            return

        if self.segundos_restantes <= 0:
            self.en_ejecucion = False
            self.identificador_after = None
            self.bell()

            if not self.es_descanso:
                self.sesiones_completadas += 1
                messagebox.showinfo(
                    "¡Sesión terminada! 🍅",
                    "Completaste 25 minutos de concentración. Ahora descansa 5 minutos."
                )
            else:
                messagebox.showinfo(
                    "¡Descanso terminado!",
                    "Ya descansaste. Es momento de comenzar otra sesión."
                )

            self._establecer_fase(not self.es_descanso)
            return

        self.segundos_restantes -= 1
        self.actualizar_pantalla()
        self.identificador_after = self.after(1000, self._cuenta_regresiva)

    def _establecer_fase(self, descanso):
        if self.identificador_after is not None:
            try:
                self.after_cancel(self.identificador_after)
            except tk.TclError:
                pass
            self.identificador_after = None

        self.en_ejecucion = False
        self.es_descanso = descanso
        self.segundos_restantes = (
            self.DURACION_DESCANSO if descanso else self.DURACION_TRABAJO
        )
        self.btn_iniciar.config(text="▶ Iniciar")
        self.actualizar_pantalla()

    def cambiar_fase_manual(self):
        self._establecer_fase(not self.es_descanso)

    def reiniciar(self):
        self._establecer_fase(self.es_descanso)

    def actualizar_pantalla(self):
        minutos, segundos = divmod(max(0, self.segundos_restantes), 60)
        self.label_tiempo.config(text=f"{minutos:02d}:{segundos:02d}")

        duracion = self.DURACION_DESCANSO if self.es_descanso else self.DURACION_TRABAJO
        self.barra_tiempo.config(maximum=duracion, value=self.segundos_restantes)

        if self.es_descanso:
            self.label_estado.config(text="Tiempo de descanso", fg=C["secundario"])
            self.label_indicacion.config(text="Relájate durante 5 minutos.")
            self.label_tiempo.config(fg=C["secundario"])
        else:
            self.label_estado.config(text="Tiempo de concentración", fg=C["texto"])
            self.label_indicacion.config(
                text="Trabaja durante 25 minutos y después descansa 5."
            )
            self.label_tiempo.config(fg=C["primario"])

        self.label_sesiones.config(
            text=f"Sesiones completadas: {self.sesiones_completadas}"
        )


# ============================================================
# PANTALLA: PANEL PRINCIPAL (hábitos + música de fondo)
# ============================================================
class PanelFrame(tk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent, bg=C["fondo"])
        self.controller = controller
        self.subtareas_pendientes = []
        self.tarjetas_expandidas = set()

        # -------- Barra superior (perfil + progreso general) --------
        barra_superior = tk.Frame(self, bg=C["primario"], height=110)
        barra_superior.pack(fill="x", side="top")
        barra_superior.pack_propagate(False)
        

        zona_perfil = tk.Frame(barra_superior, bg=C["primario"])
        zona_perfil.pack(side="left", padx=20, pady=15)

        self.label_foto_perfil = tk.Label(zona_perfil, bg=C["primario"], cursor="hand2")
        self.label_foto_perfil.pack(side="left")
        self.label_foto_perfil.bind("<Button-1>", lambda e: self.cambiar_foto_perfil())

        texto_perfil = tk.Frame(zona_perfil, bg=C["primario"])
        texto_perfil.pack(side="left", padx=12)
        self.label_bienvenida = tk.Label(texto_perfil, text="", font=("Segoe UI", 15, "bold"),
                                          bg=C["primario"], fg="white", anchor="w")
        self.label_bienvenida.pack(anchor="w")
        self.label_frase = tk.Label(texto_perfil, text="", font=("Segoe UI", 9, "italic"),
                                     bg=C["primario"], fg="#E8E6FF", anchor="w", wraplength=320)
        self.label_frase.pack(anchor="w", pady=(2, 0))
        tk.Button(texto_perfil, text="📷 Cambiar foto", bg=C["primario_oscuro"], fg="white",
                  relief="flat", cursor="hand2", font=("Segoe UI", 8),
                  command=self.cambiar_foto_perfil).pack(anchor="w", pady=(4, 0))

        self.anillo_progreso = AnilloProgreso(barra_superior, tamano=80, grosor=8, bg=C["primario"])
        self.anillo_progreso.pack(side="left", padx=25)

        tk.Button(barra_superior, text="Cerrar sesión", command=self.cerrar_sesion,
                  bg="white", fg=C["primario"], relief="flat", cursor="hand2",
                  font=("Segoe UI", 9, "bold")).pack(side="right", padx=(8, 20))

        self.btn_tema = tk.Button(
            barra_superior,
            text="🌙 Modo oscuro",
            command=controller.cambiar_tema,
            bg=C["primario_oscuro"],
            fg="white",
            activebackground=C["primario"],
            activeforeground="white",
            relief="flat",
            cursor="hand2",
            font=("Segoe UI", 9, "bold")
        )
        self.btn_tema.pack(side="right", padx=8)

        self.btn_pomodoro = tk.Button(
            barra_superior,
            text="🍅 Pomodoro",
            command=lambda: controller.mostrar_frame(PomodoroFrame),
            bg=C["acento"],
            fg="white",
            activebackground=C["primario_oscuro"],
            activeforeground="white",
            relief="flat",
            cursor="hand2",
            font=("Segoe UI", 9, "bold")
        )
        self.btn_pomodoro.pack(side="right", padx=8)

        self.btn_logros = tk.Button(
            barra_superior,
            text="🏆 Logros",
            command=lambda: controller.mostrar_frame(LogrosFrame),
            bg=C["acento_2"],
            fg="white",
            activebackground=C["primario_oscuro"],
            activeforeground="white",
            relief="flat",
            cursor="hand2",
            font=("Segoe UI", 9, "bold")
        )
        self.btn_logros.pack(side="right", padx=8)

        self.btn_estadisticas = tk.Button(
            barra_superior,
            text="📊 Estadísticas",
            command=lambda: controller.mostrar_frame(EstadisticasFrame),
            bg=C["secundario"],
            fg="white",
            activebackground=C["primario_oscuro"],
            activeforeground="white",
            relief="flat",
            cursor="hand2",
            font=("Segoe UI", 9, "bold")
        )
        self.btn_estadisticas.pack(side="right", padx=8)

        # -------- Cuerpo: formulario + lista de hábitos --------
        cuerpo = tk.Frame(self, bg=C["fondo"])
        cuerpo.pack(fill="both", expand=True, padx=15, pady=15)

        # Panel izquierdo con barra de desplazamiento vertical.
        # Así, aunque se agreguen muchas subtareas, el botón permanece accesible.
        contenedor_izq = tk.Frame(cuerpo, bg=C["tarjeta"], width=290)
        contenedor_izq.pack(side="left", fill="y", padx=(0, 15))
        contenedor_izq.pack_propagate(False)

        self.canvas_formulario = tk.Canvas(
            contenedor_izq, bg=C["tarjeta"], highlightthickness=0, width=265
        )
        scrollbar_formulario = ttk.Scrollbar(
            contenedor_izq, orient="vertical", command=self.canvas_formulario.yview
        )
        panel_izq = tk.Frame(self.canvas_formulario, bg=C["tarjeta"], padx=20, pady=20)

        self.ventana_formulario = self.canvas_formulario.create_window(
            (0, 0), window=panel_izq, anchor="nw"
        )
        panel_izq.bind(
            "<Configure>",
            lambda e: self.canvas_formulario.configure(
                scrollregion=self.canvas_formulario.bbox("all")
            )
        )
        self.canvas_formulario.bind(
            "<Configure>",
            lambda e: self.canvas_formulario.itemconfigure(
                self.ventana_formulario, width=e.width
            )
        )
        self.canvas_formulario.configure(yscrollcommand=scrollbar_formulario.set)
        self.canvas_formulario.pack(side="left", fill="both", expand=True)
        scrollbar_formulario.pack(side="right", fill="y")

        tk.Label(panel_izq, text="✏️  Nuevo hábito", font=("Segoe UI", 13, "bold"),
                 bg=C["tarjeta"], fg=C["texto"]).pack(anchor="w", pady=(0, 10))

        tk.Label(panel_izq, text="Nombre del hábito", bg=C["tarjeta"], fg=C["texto_suave"],
                 anchor="w").pack(fill="x")
        self.entry_habito = tk.Entry(panel_izq, width=28, font=("Segoe UI", 10), relief="flat",
                                      bg=C["fondo"])
        self.entry_habito.pack(pady=(2, 12), ipady=4)

        tk.Label(panel_izq, text="Categoría", bg=C["tarjeta"], fg=C["texto_suave"],
                 anchor="w").pack(fill="x")
        self.var_categoria = tk.StringVar(value=CATEGORIAS[0])
        for cat in CATEGORIAS:
            icono = CATEGORIAS_INFO[cat]["icono"]
            tk.Radiobutton(panel_izq, text=f"{icono} {cat}", variable=self.var_categoria, value=cat,
                            bg=C["tarjeta"], anchor="w", selectcolor=C["primario_claro"]).pack(fill="x")

        tk.Label(panel_izq, text="Frecuencia", bg=C["tarjeta"], fg=C["texto_suave"],
                 anchor="w").pack(fill="x", pady=(12, 0))
        self.var_frecuencia = tk.StringVar(value=FRECUENCIAS[0])
        for frec in FRECUENCIAS:
            tk.Radiobutton(panel_izq, text=frec, variable=self.var_frecuencia, value=frec,
                            bg=C["tarjeta"], anchor="w", selectcolor=C["primario_claro"]).pack(fill="x")

        # Subtareas iniciales (opcional)
        tk.Label(panel_izq, text="Subtareas (opcional)", bg=C["tarjeta"], fg=C["texto_suave"],
                 anchor="w").pack(fill="x", pady=(12, 0))
        fila_subtarea = tk.Frame(panel_izq, bg=C["tarjeta"])
        fila_subtarea.pack(fill="x", pady=(2, 4))
        self.entry_subtarea = tk.Entry(fila_subtarea, font=("Segoe UI", 10), relief="flat", bg=C["fondo"])
        self.entry_subtarea.pack(side="left", fill="x", expand=True, ipady=3)
        self.entry_subtarea.bind("<Return>", lambda e: self.agregar_subtarea_pendiente())
        tk.Button(fila_subtarea, text="+", bg=C["primario_claro"], fg=C["primario_oscuro"],
                  relief="flat", cursor="hand2", width=3,
                  command=self.agregar_subtarea_pendiente).pack(side="left", padx=(4, 0))

        self.lista_subtareas_pendientes = tk.Frame(panel_izq, bg=C["tarjeta"])
        self.lista_subtareas_pendientes.pack(fill="x")

        tk.Button(panel_izq, text="Agregar hábito", bg=C["primario"], fg="white",
                  relief="flat", pady=8, cursor="hand2", font=("Segoe UI", 10, "bold"),
                  activebackground=C["primario_oscuro"], activeforeground="white",
                  command=self.agregar_habito).pack(fill="x", pady=(16, 0))

        # Panel derecho: lista de hábitos y progreso
        panel_der = tk.Frame(cuerpo, bg=C["tarjeta"], padx=20, pady=20)
        panel_der.pack(side="left", fill="both", expand=True)

        encabezado = tk.Frame(panel_der, bg=C["tarjeta"])
        encabezado.pack(fill="x")
        tk.Label(encabezado, text="📋 Mis hábitos de hoy", font=("Segoe UI", 13, "bold"),
                 bg=C["tarjeta"], fg=C["texto"]).pack(side="left")
        self.label_progreso = tk.Label(encabezado, text="", font=("Segoe UI", 11, "bold"),
                                        bg=C["tarjeta"], fg=C["primario"])
        self.label_progreso.pack(side="right")

        # Canvas con scroll para la lista de hábitos
        contenedor_lista = tk.Frame(panel_der, bg=C["tarjeta"])
        contenedor_lista.pack(fill="both", expand=True, pady=(10, 0))

        self.canvas = tk.Canvas(contenedor_lista, bg=C["tarjeta"], highlightthickness=0)
        scrollbar = ttk.Scrollbar(contenedor_lista, orient="vertical", command=self.canvas.yview)
        self.frame_habitos = tk.Frame(self.canvas, bg=C["tarjeta"])

        self.frame_habitos.bind(
            "<Configure>", lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )
        self.canvas.create_window((0, 0), window=self.frame_habitos, anchor="nw")
        self.canvas.configure(yscrollcommand=scrollbar.set)
        self.canvas.bind_all("<MouseWheel>", self._sobre_rueda_raton)

        self.canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # Reproductor compacto flotante en la esquina inferior derecha.
        self.crear_player_musica()
        self.player_frame.lift()

    def crear_player_musica(self):
        """Crea un reproductor horizontal compacto en la esquina inferior derecha."""
        audio_disponible_local = pygame is not None and audio_disponible

        self.player_frame = tk.Frame(
            self,
            bg="#151515",
            bd=0,
            highlightthickness=1,
            highlightbackground="#3A3A3A"
        )
        self.player_frame.place(
            relx=0.988, rely=0.985, anchor="se", width=390, height=145
        )

        # Información superior: portada, nombre y visualizador decorativo.
        superior = tk.Frame(self.player_frame, bg="#151515")
        superior.pack(fill="x", padx=13, pady=(11, 4))

        self.canvas_portada = tk.Canvas(
            superior, width=60, height=60, bg="#151515",
            highlightthickness=1, highlightbackground="#F4F4F4"
        )
        self.canvas_portada.pack(side="left")
        self.canvas_portada.create_text(
            30, 30, text="♫", fill="white", font=("Segoe UI", 22, "bold")
        )

        info = tk.Frame(superior, bg="#151515")
        info.pack(side="left", fill="both", expand=True, padx=(12, 0))

        self.canvas_visualizador = tk.Canvas(
            info, height=26, bg="#151515", highlightthickness=0
        )
        self.canvas_visualizador.pack(fill="x")
        self._dibujar_visualizador()

        self.label_cancion = tk.Label(
            info, text="Sin canción seleccionada", bg="#151515", fg="white",
            anchor="w", font=("Segoe UI", 9, "bold")
        )
        self.label_cancion.pack(fill="x", pady=(2, 0))

        self.label_audio_estado = tk.Label(
            info, text="Carga una canción con el botón +",
            bg="#151515", fg="#BDBDBD", anchor="w",
            font=("Segoe UI", 8)
        )
        self.label_audio_estado.pack(fill="x")

        # Barra de volumen.
        self.slider_volumen = tk.Scale(
            self.player_frame, from_=0, to=100, orient="horizontal",
            bg="#151515", fg="white", troughcolor="#EAEAEA",
            activebackground="white", highlightthickness=0, bd=0,
            showvalue=0, sliderlength=14, command=self.cambiar_volumen,
            state="normal" if audio_disponible_local else "disabled"
        )
        self.slider_volumen.set(70)
        self.slider_volumen.pack(fill="x", padx=18, pady=(0, 0))

        controles = tk.Frame(self.player_frame, bg="#151515")
        controles.pack(fill="x", padx=15, pady=(0, 8))

        self.boton_subir = tk.Button(
            controles, text="+", command=self.subir_cancion,
            bg="#151515", fg="white", activebackground="#2A2A2A",
            activeforeground="white", relief="flat", bd=0,
            cursor="hand2", font=("Segoe UI", 13, "bold"), width=3
        )
        self.boton_subir.pack(side="left")

        self.boton_detener = tk.Button(
            controles, text="■", command=self.detener_musica,
            bg="#151515", fg="white", activebackground="#2A2A2A",
            activeforeground="white", relief="flat", bd=0,
            cursor="hand2", font=("Segoe UI", 11, "bold"), width=3,
            state="normal" if audio_disponible_local else "disabled"
        )
        self.boton_detener.pack(side="left", padx=(3, 0))

        self.boton_play_pausa = tk.Button(
            controles, text="▶", command=self.reproducir_pausar_musica,
            bg="#151515", fg="white", activebackground="#2A2A2A",
            activeforeground="white", relief="flat", bd=0,
            cursor="hand2", font=("Segoe UI", 16, "bold"), width=4,
            state="disabled"
        )
        self.boton_play_pausa.pack(side="left", padx=(7, 0))

        tk.Label(
            controles, text="⟳", bg="#151515", fg="white",
            font=("Segoe UI", 13, "bold")
        ).pack(side="right", padx=5)

        tk.Label(
            controles, text="VOL", bg="#151515", fg="#BDBDBD",
            font=("Segoe UI", 8, "bold")
        ).pack(side="right", padx=8)

        if pygame is not None:
            if audio_disponible:
                pygame.mixer.music.set_volume(0.7)
                self.label_audio_estado.config(text="Listo para reproducir")
            else:
                self.label_audio_estado.config(text="Audio no disponible")
        else:
            self.label_audio_estado.config(text="Instala pygame para usar audio")

    def _dibujar_visualizador(self):
        """Dibuja barras decorativas parecidas a una forma de onda."""
        self.canvas_visualizador.delete("all")
        alturas = [6, 11, 8, 16, 10, 21, 13, 7, 18, 12, 24, 9,
                   15, 20, 8, 13, 22, 11, 17, 7, 14, 19, 10, 16, 8, 12]
        x = 4
        for alto in alturas:
            self.canvas_visualizador.create_line(
                x, 24, x, 24 - alto, fill="white", width=2
            )
            x += 10

    def _sobre_rueda_raton(self, evento):
        self.canvas.yview_scroll(int(-1 * (evento.delta / 120)), "units")

    # ---------------------------------------------------
    # Carga inicial al mostrar el panel
    # ---------------------------------------------------
    def cargar_datos(self):
        usuario = self.controller.usuario_actual
        if not usuario:
            return
        self.label_bienvenida.config(text=f"Hola, {usuario['nombre']} 👋")
        self.label_frase.config(text=random.choice(FRASES_MOTIVACION))
        self._cargar_foto_perfil(usuario.get("foto_perfil"))
        self.subtareas_pendientes = []
        self._refrescar_lista_subtareas_pendientes()
        self.refrescar_lista_habitos()

    def _cargar_foto_perfil(self, ruta_foto):
        try:
            imagen = hacer_foto_circular(ruta_foto, tamano=64, borde_color="white", borde_ancho=3)
            self.foto_tk = ImageTk.PhotoImage(imagen)
            self.label_foto_perfil.config(image=self.foto_tk, text="")
        except Exception:
            self.label_foto_perfil.config(image="", text="👤", font=("Segoe UI", 22), fg="white")

    def cambiar_foto_perfil(self):
        """Permite al usuario actualizar su foto de perfil en cualquier momento."""
        ruta = filedialog.askopenfilename(
            title="Selecciona tu nueva foto de perfil",
            filetypes=[("Imágenes", "*.png *.jpg *.jpeg *.gif")]
        )
        if not ruta:
            return

        usuario = self.controller.usuario_actual
        extension = os.path.splitext(ruta)[1]
        nombre_archivo = f"{usuario['usuario']}{extension}"
        destino = os.path.join(CARPETA_FOTOS, nombre_archivo)

        try:
            if os.path.abspath(ruta) != os.path.abspath(destino):
                shutil.copy(ruta, destino)
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo guardar la imagen.\n{e}")
            return

        try:
            db.actualizar_foto_perfil(usuario["id"], destino)
        except ConnectionError as e:
            messagebox.showerror("Error de conexión", str(e))
            return

        usuario["foto_perfil"] = destino
        self._cargar_foto_perfil(destino)
        messagebox.showinfo("Listo", "Tu foto de perfil se actualizó correctamente 🎉")

    # ---------------------------------------------------
    # Subtareas pendientes (antes de crear el hábito)
    # ---------------------------------------------------
    def agregar_subtarea_pendiente(self):
        texto = self.entry_subtarea.get().strip()
        if texto:
            self.subtareas_pendientes.append(texto)
            self.entry_subtarea.delete(0, tk.END)
            self._refrescar_lista_subtareas_pendientes()

    def _refrescar_lista_subtareas_pendientes(self):
        for w in self.lista_subtareas_pendientes.winfo_children():
            w.destroy()
        for i, texto in enumerate(self.subtareas_pendientes):
            fila = tk.Frame(self.lista_subtareas_pendientes, bg=C["fondo"])
            fila.pack(fill="x", pady=1)
            tk.Label(fila, text=f"• {texto}", bg=C["fondo"], fg=C["texto"],
                     font=("Segoe UI", 9), anchor="w").pack(side="left", fill="x", expand=True, padx=4)
            tk.Button(fila, text="✕", bg=C["fondo"], fg=C["acento"], relief="flat", bd=0,
                      cursor="hand2",
                      command=lambda idx=i: self._quitar_subtarea_pendiente(idx)).pack(side="right")

    def _quitar_subtarea_pendiente(self, indice):
        del self.subtareas_pendientes[indice]
        self._refrescar_lista_subtareas_pendientes()

    # ---------------------------------------------------
    # Hábitos
    # ---------------------------------------------------
    def agregar_habito(self):
        nombre = self.entry_habito.get().strip()
        if not nombre:
            messagebox.showwarning("Campo vacío", "Escribe el nombre del hábito.")
            return

        usuario_id = self.controller.usuario_actual["id"]
        try:
            db.crear_habito(usuario_id, nombre, self.var_categoria.get(), self.var_frecuencia.get(),
                             subtareas=self.subtareas_pendientes)
        except ConnectionError as e:
            messagebox.showerror("Error de conexión", str(e))
            return

        self.entry_habito.delete(0, tk.END)
        self.subtareas_pendientes = []
        self._refrescar_lista_subtareas_pendientes()
        self.refrescar_lista_habitos()
        self._evaluar_y_mostrar_logros()

    def _evaluar_y_mostrar_logros(self):
        """Comprueba logros nuevos y muestra una sola notificación agrupada."""
        usuario = self.controller.usuario_actual
        if not usuario:
            return
        try:
            nuevos = db.evaluar_logros(usuario["id"])
        except ConnectionError as e:
            messagebox.showerror("Error de conexión", str(e))
            return

        if nuevos:
            detalle = "\n".join(
                f'{logro["icono"]} {logro["nombre"]}  (+{logro["xp"]} XP)'
                for logro in nuevos
            )
            messagebox.showinfo("¡Logro desbloqueado! 🏆", detalle)

    def refrescar_lista_habitos(self):
        for widget in self.frame_habitos.winfo_children():
            widget.destroy()

        usuario_id = self.controller.usuario_actual["id"]
        try:
            habitos = db.obtener_habitos(usuario_id)
            completados, total = db.obtener_progreso(usuario_id)
        except ConnectionError as e:
            messagebox.showerror("Error de conexión", str(e))
            return

        self.label_progreso.config(text=f"{completados}/{total} completados hoy")
        porcentaje_general = int(round((completados / total) * 100)) if total else 0
        self.anillo_progreso.set_progreso(porcentaje_general)

        if not habitos:
            tk.Label(self.frame_habitos, text="Aún no tienes hábitos. ¡Agrega el primero! 🚀",
                     bg=C["tarjeta"], fg="gray").pack(pady=20)
            return

        for habito in habitos:
            tarjeta = HabitoCard(self.frame_habitos, self, habito)
            tarjeta.pack(fill="x", pady=6)
            if habito["id"] in self.tarjetas_expandidas:
                tarjeta.alternar_expandido()

    def marcar_completado(self, habito_id, variable):
        try:
            db.marcar_habito(habito_id, variable.get())
        except ConnectionError as e:
            messagebox.showerror("Error de conexión", str(e))
            return
        self.refrescar_lista_habitos()
        self._evaluar_y_mostrar_logros()

    def eliminar_habito(self, habito_id):
        if messagebox.askyesno("Confirmar", "¿Eliminar este hábito y todas sus subtareas?"):
            try:
                db.eliminar_habito(habito_id)
            except ConnectionError as e:
                messagebox.showerror("Error de conexión", str(e))
                return
            self.tarjetas_expandidas.discard(habito_id)
            self.refrescar_lista_habitos()

    # ---------------------------------------------------
    # Subtareas de un hábito ya creado
    # ---------------------------------------------------
    def agregar_subtarea(self, habito_id, nombre):
        try:
            db.agregar_subtarea(habito_id, nombre)
        except ConnectionError as e:
            messagebox.showerror("Error de conexión", str(e))
            return
        self.tarjetas_expandidas.add(habito_id)
        self.refrescar_lista_habitos()

    def marcar_subtarea(self, subtarea_id, variable):
        habito_id = self._buscar_habito_de_subtarea(subtarea_id)
        try:
            db.marcar_subtarea(subtarea_id, variable.get())
        except ConnectionError as e:
            messagebox.showerror("Error de conexión", str(e))
            return
        if habito_id:
            self.tarjetas_expandidas.add(habito_id)
        self.refrescar_lista_habitos()
        self._celebrar_si_corresponde(habito_id)
        self._evaluar_y_mostrar_logros()

    def eliminar_subtarea(self, subtarea_id):
        habito_id = self._buscar_habito_de_subtarea(subtarea_id)
        try:
            db.eliminar_subtarea(subtarea_id)
        except ConnectionError as e:
            messagebox.showerror("Error de conexión", str(e))
            return
        if habito_id:
            self.tarjetas_expandidas.add(habito_id)
        self.refrescar_lista_habitos()

    def _buscar_habito_de_subtarea(self, subtarea_id):
        for widget in self.frame_habitos.winfo_children():
            if isinstance(widget, HabitoCard):
                for sub in widget.habito["subtareas"]:
                    if sub["id"] == subtarea_id:
                        return widget.habito["id"]
        return None

    def _celebrar_si_corresponde(self, habito_id):
        if habito_id is None:
            return
        usuario_id = self.controller.usuario_actual["id"]
        try:
            habitos = db.obtener_habitos(usuario_id)
        except ConnectionError:
            return
        for h in habitos:
            if h["id"] == habito_id and h["completado_hoy"] and h["subtareas"]:
                messagebox.showinfo("¡Hábito completado! 🎉",
                                     f'Terminaste "{h["nombre"]}" por hoy. ¡Sigue así!')
                break

    # ---------------------------------------------------
    # Música de fondo
    # ---------------------------------------------------
    def subir_cancion(self):
        ruta = filedialog.askopenfilename(
            title="Selecciona una canción",
            filetypes=[("Audio", "*.mp3 *.wav *.ogg")]
        )
        if not ruta:
            return

        if pygame is None:
            messagebox.showwarning(
                "Audio no disponible",
                "Pygame no está instalado, por lo que no se puede reproducir audio."
            )
            return

        if not pygame.mixer.get_init():
            try:
                pygame.mixer.init()
            except Exception as e:
                messagebox.showerror("Error de audio", f"No se pudo iniciar el audio.\n{e}")
                return

        destino = os.path.join(CARPETA_MUSICA, os.path.basename(ruta))
        try:
            shutil.copy(ruta, destino)
        except shutil.SameFileError:
            pass
        except OSError as e:
            messagebox.showerror("Error", f"No se pudo copiar la canción.\n{e}")
            return

        self.controller.ruta_musica_actual = destino
        nombre = os.path.basename(destino)
        self.label_cancion.config(text=nombre if len(nombre) <= 35 else nombre[:32] + "...")
        self.boton_play_pausa.config(state="normal", text="▶")

        try:
            pygame.mixer.music.load(destino)
            pygame.mixer.music.play(loops=-1)
            self.controller.musica_reproduciendo = True
            self.boton_play_pausa.config(text="⏸")
            self.label_audio_estado.config(text="Reproduciendo")
        except pygame.error as e:
            self.controller.musica_reproduciendo = False
            self.label_audio_estado.config(text="No se pudo reproducir")
            messagebox.showerror("Error de audio", f"No se pudo reproducir el archivo.\n{e}")

    def reproducir_pausar_musica(self):
        if pygame is None or not self.controller.ruta_musica_actual:
            return

        if self.controller.musica_reproduciendo:
            pygame.mixer.music.pause()
            self.controller.musica_reproduciendo = False
            self.boton_play_pausa.config(text="▶")
            self.label_audio_estado.config(text="Pausado")
        else:
            pygame.mixer.music.unpause()
            self.controller.musica_reproduciendo = True
            self.boton_play_pausa.config(text="⏸")
            self.label_audio_estado.config(text="Reproduciendo")

    def detener_musica(self):
        if pygame is None:
            return
        try:
            pygame.mixer.music.stop()
        except Exception:
            pass
        self.controller.musica_reproduciendo = False
        self.boton_play_pausa.config(text="▶")
        self.label_audio_estado.config(text="Detenido")

    def cambiar_volumen(self, valor):
        if pygame is None:
            return
        try:
            pygame.mixer.music.set_volume(int(float(valor)) / 100)
        except (ValueError, pygame.error):
            pass

    # ---------------------------------------------------
    def cerrar_sesion(self):
        if pygame is not None:
            try:
                pygame.mixer.music.stop()
            except Exception:
                pass
        self.controller.usuario_actual = None
        self.controller.ruta_musica_actual = None
        self.controller.musica_reproduciendo = False
        self.tarjetas_expandidas = set()
        self.controller.mostrar_frame(LoginFrame)


if __name__ == "__main__":
    app = App()
    app.mainloop()
