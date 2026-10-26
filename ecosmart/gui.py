"""Interfaz gráfica de EcoSmart (Tkinter + matplotlib).

El análisis corre en un hilo aparte para que la ventana no se congele. El hilo
nunca toca widgets de Tk: deja el resultado en una cola y el hilo principal lo
recoge con root.after().
"""

import queue
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from PIL import Image, ImageTk

from . import aire, config as cfg, graficos, imagenes, recompensas, reportes, vegetacion

TEXTO_ACERCA = (
    "EcoSmart CDMX, versión 2.0\n\n"
    "Desarrollado por: Sergio Alejandro Vera Martínez\n"
    "IPN - ESCOM · Grupo 3BM1\n"
    "Materia: Procesamiento de Imágenes Digitales\n\n"
    "Limitaciones:\n"
    "• La cobertura verde se mide sobre la imagen, no sobre superficie real.\n"
    "• La 'salud' es la saturación del verde, no NDVI (requiere infrarrojo).\n"
    "• El índice de aire es una estimación visual sin calibrar. Para datos "
    "oficiales consulta la red SIMAT de la CDMX.\n"
)


class EcoSmartApp:
    """Ventana principal con las pestañas Análisis, Gráficas, Progreso y Acerca de."""

    TAM_VISTA = (480, 360)

    def __init__(self, root):
        self.root = root
        self.root.title(cfg.NOMBRE_APP)
        self.root.geometry("1140x740")
        self.root.minsize(940, 620)

        self.imagen = None            # BGR uint8 ya redimensionada
        self.resultado_veg = None
        self.resultado_aire = None
        self.ultimo_reporte = None
        self.cola = queue.Queue()
        self._foto = None             # referencia viva para que Tk no borre la imagen
        self._lienzo = None

        self.ruta_progreso = cfg.DIRECTORIO_DATOS / cfg.NOMBRE_ARCHIVO_PROGRESO
        self.progreso, aviso = recompensas.Progreso.cargar(self.ruta_progreso)

        self.var_usuario = tk.StringVar(value=self.progreso.usuario)
        self.var_escenario = tk.StringVar(value=imagenes.ESCENARIOS[0])
        self.var_ods = tk.StringVar(value="ods_11")
        self.var_registrar = tk.BooleanVar(value=True)
        self.var_estado = tk.StringVar(value="Abre una imagen o genera un escenario de prueba.")

        self._construir_ui()
        self._actualizar_progreso()
        if aviso:
            messagebox.showwarning(cfg.NOMBRE_APP, aviso, parent=self.root)
        self.root.protocol("WM_DELETE_WINDOW", self._cerrar)

    # ------------------------------------------------------------------
    # Construcción de la interfaz
    # ------------------------------------------------------------------
    def _construir_ui(self):
        self.cuaderno = ttk.Notebook(self.root)
        self.cuaderno.pack(fill="both", expand=True, padx=10, pady=10)
        self.pestana_analisis = ttk.Frame(self.cuaderno)
        self.pestana_graficas = ttk.Frame(self.cuaderno)
        self.pestana_progreso = ttk.Frame(self.cuaderno)
        self.pestana_acerca = ttk.Frame(self.cuaderno)
        self.cuaderno.add(self.pestana_analisis, text="Análisis")
        self.cuaderno.add(self.pestana_graficas, text="Gráficas")
        self.cuaderno.add(self.pestana_progreso, text="Mi progreso")
        self.cuaderno.add(self.pestana_acerca, text="Acerca de")
        self._construir_analisis()
        self._construir_graficas()
        self._construir_progreso()
        ttk.Label(self.pestana_acerca, text=TEXTO_ACERCA, justify="left", padding=20).pack(anchor="w")

    def _construir_analisis(self):
        panel = ttk.Frame(self.pestana_analisis, padding=8)
        panel.pack(side="left", fill="y")

        ttk.Label(panel, text="Usuario").pack(anchor="w")
        ttk.Entry(panel, textvariable=self.var_usuario, width=28).pack(fill="x", pady=(0, 8))

        ttk.Button(panel, text="Abrir imagen…", command=self._abrir_imagen).pack(fill="x", pady=2)
        fila = ttk.Frame(panel)
        fila.pack(fill="x", pady=2)
        ttk.Combobox(fila, textvariable=self.var_escenario, values=imagenes.ESCENARIOS,
                     state="readonly", width=14).pack(side="left")
        ttk.Button(fila, text="Generar", command=self._generar_escenario).pack(side="left", padx=4)

        ttk.Separator(panel).pack(fill="x", pady=8)
        ttk.Label(panel, text="ODS para el progreso").pack(anchor="w")
        ttk.Combobox(panel, textvariable=self.var_ods, values=list(cfg.PUNTOS_BASE_POR_ODS),
                     state="readonly").pack(fill="x")
        ttk.Checkbutton(panel, text="Registrar en mi progreso",
                        variable=self.var_registrar).pack(anchor="w", pady=4)

        self.btn_analizar = ttk.Button(panel, text="Analizar", command=self._iniciar_analisis, state="disabled")
        self.btn_analizar.pack(fill="x", pady=2)
        self.barra = ttk.Progressbar(panel, mode="indeterminate")
        self.barra.pack(fill="x", pady=6)

        ttk.Button(panel, text="Guardar reporte JSON…", command=self._guardar_reporte).pack(fill="x", pady=2)
        ttk.Button(panel, text="Guardar máscara PNG…", command=self._guardar_mascara).pack(fill="x", pady=2)
        ttk.Label(panel, textvariable=self.var_estado, wraplength=260,
                  foreground="#555555").pack(anchor="w", pady=8)

        derecha = ttk.Frame(self.pestana_analisis, padding=8)
        derecha.pack(side="left", fill="both", expand=True)
        self.lbl_imagen = ttk.Label(derecha, anchor="center")
        self.lbl_imagen.pack(fill="x")

        marco_texto = ttk.Frame(derecha)
        marco_texto.pack(fill="both", expand=True, pady=(8, 0))
        scroll = ttk.Scrollbar(marco_texto)
        scroll.pack(side="right", fill="y")
        self.texto = tk.Text(marco_texto, wrap="word", height=16, yscrollcommand=scroll.set)
        self.texto.pack(side="left", fill="both", expand=True)
        scroll.config(command=self.texto.yview)
        self.texto.insert("1.0", "Sin resultados todavía.")
        self.texto.config(state="disabled")

    def _construir_graficas(self):
        self.marco_graficas = ttk.Frame(self.pestana_graficas, padding=8)
        self.marco_graficas.pack(fill="both", expand=True)
        ttk.Label(self.marco_graficas,
                  text="Las gráficas aparecen después de un análisis.").pack(anchor="w")

    def _construir_progreso(self):
        arriba = ttk.Frame(self.pestana_progreso, padding=10)
        arriba.pack(fill="x")
        self.lbl_resumen = ttk.Label(arriba, font=("TkDefaultFont", 13, "bold"))
        self.lbl_resumen.pack(anchor="w")
        self.lbl_medallas = ttk.Label(arriba, wraplength=900)
        self.lbl_medallas.pack(anchor="w", pady=4)

        columnas = ("fecha", "ods", "puntos", "cobertura", "aire")
        encabezados = ("Fecha", "ODS", "Puntos", "Cobertura verde (%)", "Calidad del aire")
        self.tabla = ttk.Treeview(self.pestana_progreso, columns=columnas, show="headings", height=14)
        for columna, texto in zip(columnas, encabezados):
            self.tabla.heading(columna, text=texto)
            self.tabla.column(columna, anchor="center", width=170)
        self.tabla.pack(fill="both", expand=True, padx=10, pady=4)

        botones = ttk.Frame(self.pestana_progreso, padding=10)
        botones.pack(fill="x")
        ttk.Button(botones, text="Reiniciar progreso", command=self._reiniciar_progreso).pack(side="right")
        ttk.Button(botones, text="Actualizar", command=self._actualizar_progreso).pack(side="right", padx=6)

    # ------------------------------------------------------------------
    # Acciones de la interfaz
    # ------------------------------------------------------------------
    def _abrir_imagen(self):
        ruta = filedialog.askopenfilename(
            parent=self.root,
            title="Elige una imagen",
            filetypes=[("Imágenes", " ".join("*" + e for e in imagenes.EXTENSIONES_IMAGEN))],
        )
        if not ruta:
            return
        try:
            imagen = imagenes.cargar_imagen(ruta)
        except (ValueError, OSError) as exc:
            messagebox.showerror(cfg.NOMBRE_APP, str(exc), parent=self.root)
            return
        self._establecer_imagen(imagen, f"Imagen: {ruta.split('/')[-1]}")

    def _generar_escenario(self):
        imagen = imagenes.generar_escenario(self.var_escenario.get())
        self._establecer_imagen(imagen, f"Escenario de prueba: {self.var_escenario.get()}")

    def _establecer_imagen(self, imagen, descripcion):
        self.imagen = imagenes.redimensionar_maximo(imagen)
        self.resultado_veg = self.resultado_aire = self.ultimo_reporte = None
        self._mostrar_bgr(self.imagen)
        self.btn_analizar.config(state="normal")
        self.var_estado.set(f"{descripcion}. Lista para analizar.")

    def _mostrar_bgr(self, imagen_bgr):
        pil = Image.fromarray(reportes.convertir_para_mostrar(imagen_bgr))
        pil.thumbnail(self.TAM_VISTA)
        self._foto = ImageTk.PhotoImage(pil)
        self.lbl_imagen.config(image=self._foto)

    def _iniciar_analisis(self):
        if self.imagen is None:
            return
        self.btn_analizar.config(state="disabled")
        self.barra.start(12)
        self.var_estado.set("Analizando…")
        copia = self.imagen.copy()
        threading.Thread(target=self._trabajo_analisis, args=(copia,), daemon=True).start()
        self.root.after(100, self._revisar_cola)

    def _trabajo_analisis(self, imagen):
        """Corre en un hilo secundario. No toca widgets de Tk."""
        try:
            veg = vegetacion.analizar(imagen)
            air = aire.estimar(imagen)
            self.cola.put(("ok", (veg, air)))
        except Exception as exc:  # cualquier fallo se muestra en el hilo principal
            self.cola.put(("error", str(exc)))

    def _revisar_cola(self):
        try:
            tipo, carga = self.cola.get_nowait()
        except queue.Empty:
            self.root.after(100, self._revisar_cola)
            return
        self.barra.stop()
        self.btn_analizar.config(state="normal")
        if tipo == "error":
            self.var_estado.set("Falló el análisis.")
            messagebox.showerror(cfg.NOMBRE_APP, f"Error en el análisis: {carga}", parent=self.root)
            return
        self.resultado_veg, self.resultado_aire = carga
        self._mostrar_resultados()

    def _mostrar_resultados(self):
        usuario = self.var_usuario.get().strip() or cfg.USUARIO_POR_DEFECTO
        self.ultimo_reporte = reportes.construir_reporte(usuario, self.resultado_veg, self.resultado_aire)
        self._escribir_texto(reportes.resumen_texto(self.ultimo_reporte))
        self._mostrar_bgr(reportes.superponer(self.imagen, self.resultado_veg.mascara))
        self._dibujar_graficas()
        self.var_estado.set(f"Evaluación: {self.resultado_veg.evaluacion}.")

        if self.var_registrar.get():
            self._registrar(usuario)

    def _registrar(self, usuario):
        try:
            self.progreso.usuario = usuario
            resumen = reportes.datos_para_progreso(self.resultado_veg, self.resultado_aire)
            puntos, nuevas = self.progreso.registrar(self.var_ods.get(), resumen)
            self.progreso.guardar(self.ruta_progreso)
        except (ValueError, TypeError, OSError) as exc:
            messagebox.showerror(cfg.NOMBRE_APP, f"No se pudo registrar: {exc}", parent=self.root)
            return
        self._actualizar_progreso()
        mensaje = f"Ganaste {puntos} puntos. Nivel {self.progreso.nivel}."
        for medalla in nuevas:
            mensaje += f"\n¡Medalla nueva: {medalla}!"
        messagebox.showinfo(cfg.NOMBRE_APP, mensaje, parent=self.root)

    def _escribir_texto(self, contenido):
        self.texto.config(state="normal")
        self.texto.delete("1.0", "end")
        self.texto.insert("1.0", contenido)
        self.texto.config(state="disabled")

    def _dibujar_graficas(self):
        if self._lienzo is not None:
            self._lienzo.get_tk_widget().destroy()
        figura = graficos.figura_resumen(self.imagen, self.resultado_veg)
        self._lienzo = FigureCanvasTkAgg(figura, master=self.marco_graficas)
        self._lienzo.draw()
        self._lienzo.get_tk_widget().pack(fill="both", expand=True)
        self.cuaderno.select(self.pestana_graficas)

    def _guardar_reporte(self):
        if self.ultimo_reporte is None:
            messagebox.showinfo(cfg.NOMBRE_APP, "Primero analiza una imagen.", parent=self.root)
            return
        ruta = filedialog.asksaveasfilename(parent=self.root, defaultextension=".json",
                                            filetypes=[("JSON", "*.json")], initialfile="reporte_ecosmart.json")
        if ruta:
            reportes.guardar_reporte(self.ultimo_reporte, ruta)
            self.var_estado.set(f"Reporte guardado en {ruta.split('/')[-1]}.")

    def _guardar_mascara(self):
        if self.resultado_veg is None:
            messagebox.showinfo(cfg.NOMBRE_APP, "Primero analiza una imagen.", parent=self.root)
            return
        ruta = filedialog.asksaveasfilename(parent=self.root, defaultextension=".png",
                                            filetypes=[("PNG", "*.png")], initialfile="mascara_verde.png")
        if ruta:
            reportes.guardar_mascara(self.resultado_veg.mascara, ruta)
            self.var_estado.set("Máscara guardada.")

    # ------------------------------------------------------------------
    # Progreso
    # ------------------------------------------------------------------
    def _actualizar_progreso(self):
        self.lbl_resumen.config(text=f"{self.progreso.usuario} · {self.progreso.puntos} puntos · nivel {self.progreso.nivel}")
        medallas = ", ".join(self.progreso.medallas) if self.progreso.medallas else "Sin medallas todavía"
        self.lbl_medallas.config(text=f"Medallas: {medallas}")
        self.tabla.delete(*self.tabla.get_children())
        for contribucion in reversed(self.progreso.contribuciones):
            resumen = contribucion.get("resumen", {})
            self.tabla.insert("", "end", values=(
                contribucion.get("fecha", ""),
                contribucion.get("ods", ""),
                contribucion.get("puntos", 0),
                resumen.get("porcentaje_cobertura", "-"),
                resumen.get("categoria_aire", "-"),
            ))

    def _reiniciar_progreso(self):
        if not messagebox.askyesno(cfg.NOMBRE_APP, "¿Borrar todo tu progreso? Esta acción no se puede deshacer.",
                                   parent=self.root):
            return
        self.progreso = recompensas.Progreso(self.var_usuario.get().strip() or cfg.USUARIO_POR_DEFECTO)
        self.progreso.guardar(self.ruta_progreso)
        self._actualizar_progreso()

    def _cerrar(self):
        try:
            self.progreso.guardar(self.ruta_progreso)
        finally:
            self.root.destroy()
