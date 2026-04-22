import os
import shutil
import subprocess
import threading
import json
from pathlib import Path
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

CONFIG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")

COMPRESSION_LEVELS = {
    "Store (Sin compresión)": "-mx0",
    "Fast (Rápido)": "-mx1",
    "Normal": "-mx5",
    "Maximum (Máximo)": "-mx7",
    "Ultra (Lento pero efectivo)": "-mx9"
}

TARGET_EXTENSIONS = {'.exe', '.dll', '.bat', '.cmd', '.scr', '.vbs', '.ps1'}

def find_7z():
    # 1. Buscar en la carpeta del script/ejecutable (donde suele estar 7za.exe)
    script_dir = os.path.dirname(os.path.abspath(__file__))
    p_local = os.path.join(script_dir, "7za.exe")
    if os.path.exists(p_local):
        return p_local
        
    # 2. Buscar en rutas estándar si no está en la local
    for p in ["C:\\Program Files\\7-Zip\\7z.exe", "C:\\Program Files (x86)\\7-Zip\\7z.exe"]:
        if os.path.exists(p):
            return p
    return None

class SaneadorApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Cosechadora de Archivos v2.0 - Saneador GUI")
        self.geometry("750x780")
        self.minsize(700, 700)
        
        # Tema básico y colores
        style = ttk.Style(self)
        try:
            style.theme_use("vista")
        except:
            pass

        self.seven_z_path = find_7z()
        if not self.seven_z_path:
            messagebox.showwarning("7-Zip no encontrado", "No se detectó 7z.exe en C:\\Program Files\\7-Zip. Selecciona la ruta de tu 7z.exe.")
            self.seven_z_path = filedialog.askopenfilename(title="Selecciona 7z.exe", filetypes=[("Executables", "*.exe")])
            if not self.seven_z_path:
                messagebox.showerror("Error", "7-Zip es requerido para funcionar. Saliendo...")
                self.destroy()
                return

        self.found_files = []
        self.is_processing = False
        
        # Cargar configuración
        self.config_data = {"dir_scan": os.path.abspath("."), "dupli_a": os.path.abspath("."), "dupli_b": ""}
        self.load_config()
        
        self.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        self.create_widgets()
        self.create_loading_overlay()

    def load_config(self):
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    self.config_data.update(json.load(f))
            except Exception:
                pass

    def save_config(self):
        # Actualizamos variables antes de guardar
        if hasattr(self, 'dir_var'):
            self.config_data["dir_scan"] = self.dir_var.get()
            self.config_data["dupli_a"] = self.dupli_dir_a.get()
            self.config_data["dupli_b"] = self.dupli_dir_b.get()
        try:
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(self.config_data, f, indent=4)
        except Exception:
            pass

    def on_closing(self):
        self.save_config()
        self.destroy()

    def log(self, text):
        self.log_text.config(state="normal")
        self.log_text.insert(tk.END, text + "\n")
        self.log_text.see(tk.END)
        self.log_text.config(state="disabled")
        self.update_idletasks()

    def create_widgets(self):
        # Frame superior para el Notebook
        self.top_frame = ttk.Frame(self)
        self.top_frame.pack(fill=tk.BOTH, expand=True)

        self.notebook = ttk.Notebook(self.top_frame)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # PESTAÑA 1: COSECHADORA
        self.tab_cosecha = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_cosecha, text="Cosechadora V2")
        self.setup_cosechadora_tab(self.tab_cosecha)
        
        # PESTAÑA 2: DUPLIMINAR
        self.tab_dupli = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_dupli, text="Dupliminar")
        self.setup_dupliminar_tab(self.tab_dupli)

        # BARRA INFERIOR COMPARTIDA (Log y Progreso)
        self.bottom_frame = ttk.Frame(self, padding="10")
        self.bottom_frame.pack(fill=tk.X, side=tk.BOTTOM)

        self.progress_var = tk.DoubleVar()
        self.progress = ttk.Progressbar(self.bottom_frame, variable=self.progress_var, maximum=100)
        self.progress.pack(fill=tk.X, pady=(0, 5))

        self.log_text = tk.Text(self.bottom_frame, height=6, state="disabled", bg="#f4f4f4", wrap="word", font=("Consolas", 9))
        self.log_text.pack(fill=tk.X)

    def setup_cosechadora_tab(self, parent):
        main_frame = ttk.Frame(parent, padding="15")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # SECCIÓN: Configuración de Escaneo
        scan_frame = ttk.LabelFrame(main_frame, text="Configuración de Escaneo", padding="10")
        scan_frame.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(scan_frame, text="Directorio a Analizar:").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.dir_var = tk.StringVar(value=self.config_data["dir_scan"])
        ttk.Entry(scan_frame, textvariable=self.dir_var, width=50).grid(row=0, column=1, padx=5, sticky=tk.EW)
        ttk.Button(scan_frame, text="Examinar...", command=self.browse_dir).grid(row=0, column=2)
        
        scan_frame.columnconfigure(1, weight=1)

        # SECCIÓN: Opciones de Compresión
        comp_frame = ttk.LabelFrame(main_frame, text="Opciones de Compresión (7-Zip)", padding="10")
        comp_frame.pack(fill=tk.X, pady=(0, 10))

        # Formato
        ttk.Label(comp_frame, text="Formato:").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.format_var = tk.StringVar(value="zip")
        format_cb = ttk.Combobox(comp_frame, textvariable=self.format_var, values=["zip", "7z"], state="readonly", width=15)
        format_cb.grid(row=0, column=1, sticky=tk.W, padx=5)

        # Nivel de compresión
        ttk.Label(comp_frame, text="Nivel Compresión:").grid(row=0, column=2, sticky=tk.E, padx=(20,5), pady=5)
        self.level_var = tk.StringVar(value="Normal")
        level_cb = ttk.Combobox(comp_frame, textvariable=self.level_var, values=list(COMPRESSION_LEVELS.keys()), state="readonly", width=25)
        level_cb.grid(row=0, column=3, sticky=tk.EW, padx=5)

        # Split en Partes
        ttk.Label(comp_frame, text="Dividir en partes:").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.split_enabled_var = tk.BooleanVar(value=False)
        self.split_check = ttk.Checkbutton(comp_frame, text="Habilitar división", variable=self.split_enabled_var, command=self.toggle_split)
        self.split_check.grid(row=1, column=1, sticky=tk.W, padx=5)

        ttk.Label(comp_frame, text="MB por archivo:").grid(row=1, column=2, sticky=tk.E, padx=(20,5), pady=5)
        self.split_size_var = tk.StringVar(value="50")
        self.split_entry = ttk.Entry(comp_frame, textvariable=self.split_size_var, width=10)
        self.split_entry.grid(row=1, column=3, sticky=tk.W, padx=5)
        
        # Opciones extra
        self.toggle_split()

        comp_frame.columnconfigure(3, weight=1)

        # BOTÓN DE EJECUCIÓN
        self.run_btn = ttk.Button(main_frame, text="▶ INICIAR COSECHA Y COMPRESIÓN", command=self.start_process, style="TButton")
        self.run_btn.pack(fill=tk.X, pady=10)

        # SECCIÓN: Resultados y Post-Procesamiento
        res_frame = ttk.LabelFrame(main_frame, text="Archivos Recolectados", padding="10")
        res_frame.pack(fill=tk.BOTH, expand=True)

        # Treeview para la lista
        columns = ("path", "status")
        self.tree = ttk.Treeview(res_frame, columns=columns, show="headings", selectmode="extended")
        self.tree.heading("path", text="Ruta Original del Archivo")
        self.tree.heading("status", text="Estado")
        self.tree.column("path", width=450)
        self.tree.column("status", width=100)
        
        scrollbar = ttk.Scrollbar(res_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscroll=scrollbar.set)
        
        self.tree.grid(row=0, column=0, columnspan=2, sticky=tk.NSEW)
        scrollbar.grid(row=0, column=2, sticky=tk.NS)
        res_frame.rowconfigure(0, weight=1)
        res_frame.columnconfigure(0, weight=1)

        # Botones de Post-Procesamiento
        btn_frame = ttk.Frame(res_frame)
        btn_frame.grid(row=1, column=0, columnspan=3, pady=10, sticky=tk.EW)

        self.btn_del = ttk.Button(btn_frame, text="Eliminar Originales", command=self.delete_selected, state=tk.DISABLED)
        self.btn_del.pack(side=tk.LEFT, padx=5)

        self.btn_move = ttk.Button(btn_frame, text="Mover Originales (Estructura)", command=self.move_selected, state=tk.DISABLED)
        self.btn_move.pack(side=tk.LEFT, padx=5)

        self.btn_copy = ttk.Button(btn_frame, text="Copiar Originales (Estructura)", command=self.copy_selected, state=tk.DISABLED)
        self.btn_copy.pack(side=tk.LEFT, padx=5)

    def setup_dupliminar_tab(self, parent):
        main_dupli = ttk.Frame(parent, padding="15")
        main_dupli.pack(fill=tk.BOTH, expand=True)
        
        cfg_frame = ttk.LabelFrame(main_dupli, text="Configuración Dupliminar", padding="10")
        cfg_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Directorio A (Objetivo)
        ttk.Label(cfg_frame, text="Directorio A (Objetivo):").grid(row=0, column=0, sticky=tk.W, pady=2)
        self.dupli_dir_a = tk.StringVar(value=self.config_data["dupli_a"])
        ttk.Entry(cfg_frame, textvariable=self.dupli_dir_a, width=50).grid(row=0, column=1, padx=5, sticky=tk.EW)
        ttk.Button(cfg_frame, text="...", command=lambda: self.browse_generic(self.dupli_dir_a)).grid(row=0, column=2)

        # Directorio B (Referencia)
        ttk.Label(cfg_frame, text="Directorio B (Referencia):").grid(row=1, column=0, sticky=tk.W, pady=2)
        self.dupli_dir_b = tk.StringVar(value=self.config_data["dupli_b"])
        ttk.Entry(cfg_frame, textvariable=self.dupli_dir_b, width=50).grid(row=1, column=1, padx=5, sticky=tk.EW)
        ttk.Button(cfg_frame, text="...", command=lambda: self.browse_generic(self.dupli_dir_b)).grid(row=1, column=2)
        
        cfg_frame.columnconfigure(1, weight=1)
        
        self.dupli_btn = ttk.Button(cfg_frame, text="🔍 BUSCAR DUPLICADOS", command=self.start_dupliminar)
        self.dupli_btn.grid(row=2, column=0, columnspan=3, pady=10, sticky=tk.EW)
        
        # Resultados Duplicados
        res_dupli = ttk.LabelFrame(main_dupli, text="Archivos Duplicados Encontrados", padding="10")
        res_dupli.pack(fill=tk.BOTH, expand=True)
        
        tree_frame = ttk.Frame(res_dupli)
        tree_frame.pack(fill=tk.BOTH, expand=True)
        
        # Dos Listas Sincronizadas
        self.tree_a = ttk.Treeview(tree_frame, columns=("path",), show="headings", height=10)
        self.tree_a.heading("path", text="Ruta en A (Originario)")
        self.tree_a.tag_configure("dup", background="#ffe8cc")
        
        self.tree_b = ttk.Treeview(tree_frame, columns=("path",), show="headings", height=10)
        self.tree_b.heading("path", text="Ruta en B (Referente)")
        self.tree_b.tag_configure("dup", background="#ffe8cc")
        
        sb_dupli = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=self.sync_trees_y)
        self.tree_a.configure(yscroll=sb_dupli.set)
        self.tree_b.configure(yscroll=sb_dupli.set)
        
        self.tree_a.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.tree_b.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        sb_dupli.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Botones de Acción para Dupliminar
        dupli_btns = ttk.Frame(main_dupli)
        dupli_btns.pack(fill=tk.X, pady=10)
        
        self.btn_dupli_del = ttk.Button(dupli_btns, text="Eliminar de A", state=tk.DISABLED, command=lambda: self.dupli_action("delete"))
        self.btn_dupli_del.pack(side=tk.LEFT, padx=5)
        
        self.btn_dupli_move = ttk.Button(dupli_btns, text="Mover de A", state=tk.DISABLED, command=lambda: self.dupli_action("move"))
        self.btn_dupli_move.pack(side=tk.LEFT, padx=5)
        
        self.btn_dupli_copy = ttk.Button(dupli_btns, text="Copiar de A", state=tk.DISABLED, command=lambda: self.dupli_action("copy"))
        self.btn_dupli_copy.pack(side=tk.LEFT, padx=5)

    def browse_generic(self, var):
        d = filedialog.askdirectory(initialdir=var.get())
        if d: 
            var.set(os.path.abspath(d))
            self.save_config()

    def sync_trees_y(self, *args):
        self.tree_a.yview(*args)
        self.tree_b.yview(*args)

    def create_loading_overlay(self):
        # Canvas de carga pixelado
        self.loading_canvas = tk.Canvas(self, width=280, height=140, bg="#ffffff", highlightthickness=3, highlightbackground="#000000")
        self.loading_text = tk.Label(self.loading_canvas, text="COSECHANDO\nSOSPECHOSOS...", font=("Consolas", 14, "bold"), bg="#ffffff", fg="#000000", justify=tk.CENTER)
        self.loading_text.place(relx=0.5, rely=0.35, anchor=tk.CENTER)
        
        # Bloques "pixeles" para la animación
        self.pixel_blocks = []
        for _ in range(8):
            p = self.loading_canvas.create_rectangle(0, 0, 12, 12, fill="#00aa00", outline="#003300")
            self.pixel_blocks.append(p)
        
        self.loading_canvas.place_forget()

    def animate_loading(self, step=0):
        if not self.is_processing:
            self.loading_canvas.place_forget()
            return
        
        import math
        cx, cy = 140, 95
        r = 30
        for i, p in enumerate(self.pixel_blocks):
            angle = (step + i * 45) * (math.pi / 180)
            x = cx + r * math.cos(angle)
            y = cy + r * math.sin(angle)
            x = round(x / 4) * 4
            y = round(y / 4) * 4
            self.loading_canvas.coords(p, x-6, y-6, x+6, y+6)
            
        self.after(60, self.animate_loading, step + 15)

    def toggle_split(self):
        state = tk.NORMAL if self.split_enabled_var.get() else tk.DISABLED
        self.split_entry.config(state=state)

    def browse_dir(self):
        d = filedialog.askdirectory(initialdir=self.dir_var.get())
        if d: 
            self.dir_var.set(os.path.abspath(d))
            self.save_config()

    def update_tree(self):
        for item in self.tree.get_children():
            self.tree.delete(item)
        # Mostrar los archivos encontrados primero apilados desde arriba
        for f in reversed(self.found_files):
            self.tree.insert("", tk.END, values=(f['path'], f['status']))

    def set_gui_state(self, state):
        self.run_btn.config(state=state)
        self.btn_del.config(state=tk.DISABLED if state == tk.DISABLED else tk.NORMAL)
        self.btn_move.config(state=tk.DISABLED if state == tk.DISABLED else tk.NORMAL)
        self.btn_copy.config(state=tk.DISABLED if state == tk.DISABLED else tk.NORMAL)

    def start_process(self):
        self.log_text.config(state="normal")
        self.log_text.delete(1.0, tk.END)
        self.log_text.config(state="disabled")
        
        self.found_files.clear()
        self.update_tree()
        self.progress_var.set(0)
        self.set_gui_state(tk.DISABLED)
        
        self.is_processing = True
        self.loading_canvas.place(relx=0.5, rely=0.4, anchor=tk.CENTER)
        self.animate_loading()
        
        threading.Thread(target=self.process_files, daemon=True).start()

    def process_files(self):
        root_dir = Path(self.dir_var.get())
        if not root_dir.exists() or not root_dir.is_dir():
            self.log(f"Error: El directorio {root_dir} no existe.")
            self.after(0, lambda: self.set_gui_state(tk.NORMAL))
            return

        fmt = self.format_var.get()
        level_switch = COMPRESSION_LEVELS[self.level_var.get()]
        split_enabled = self.split_enabled_var.get()
        
        # Sanitizar split_size: solo números
        split_size_raw = self.split_size_var.get().strip()
        split_size = "".join(filter(str.isdigit, split_size_raw))
        if not split_size: split_size = "50"

        self.log(f"Buscando archivos en: {root_dir}")
        output_folder = root_dir / "_zanaeado"
        
        # Buscar archivos
        targets = []
        try:
            for p in root_dir.rglob("*"):
                # Excluir la carpeta de salida para no entrar en bucle infinito
                if output_folder in p.parents or p == output_folder:
                    continue
                if p.is_file() and p.suffix.lower() in TARGET_EXTENSIONS:
                    targets.append(p)
        except Exception as e:
            self.log(f"Error escaneando: {e}")

        if not targets:
            self.log("No se encontraron archivos sospechosos.")
            self.after(0, lambda: self.set_gui_state(tk.NORMAL))
            return

        self.log(f"Se encontraron {len(targets)} archivo(s).")
        
        # Setup paths
        output_folder.mkdir(exist_ok=True)

        total = len(targets)
        for fpath in targets:
            self.found_files.append({"path": str(fpath), "status": "Preparado"})
        self.after(0, self.update_tree)

        # Collect paths to a temp list file for 7-zip (utf-8-sig adds BOM, automatically detected by 7-zip)
        list_file = output_folder / "file_list_to_compress.txt"
        with open(list_file, "w", encoding="utf-8-sig") as lf:
            for fpath in targets:
                try:
                    # Usar rutas relativas para mantener la estructura en el zip
                    rel = fpath.relative_to(root_dir)
                    lf.write(str(rel) + "\n")
                except ValueError:
                    lf.write(str(fpath) + "\n")
        
        self.log(f"Lista de archivos creada con {len(targets)} entradas.")

        # Zip path
        zip_path = output_folder / f"Analisis_Completo.{fmt}"
        if zip_path.exists():
            try: zip_path.unlink()
            except: pass
            
        # Command setup
        # Simplificamos banderas para evitar "Parámetro incorrecto" en versiones viejas de 7za
        # -bb1 para ver archivos procesados (ayuda a ver dónde se traba)
        cmd = [self.seven_z_path, "a", level_switch, "-y", "-ssw", "-bsp1", "-bb1", str(zip_path), f"@{list_file}"]
        
        if split_enabled:
            cmd.append(f"-v{split_size}m")
            
        self.log(f"Ejecutando: {' '.join(cmd)}")

        try:
            self.log(f"Comprimiendo {len(targets)} archivos...")
            # cwd=root_dir es vital para que las rutas relativas funcionen
            process = subprocess.Popen(cmd, cwd=str(root_dir), creationflags=subprocess.CREATE_NO_WINDOW, 
                                     stdout=subprocess.PIPE, stderr=subprocess.STDOUT, 
                                     text=True, encoding='latin-1', errors='replace') 
            
            for line in process.stdout:
                # 7-zip con -bsp1 usa caracteres de control (CR/BS)
                clean_line = line.replace('\b', '').replace('\r', '').strip()
                if not clean_line: continue
                
                # Buscar porcentaje (ej: " 10%")
                if "%" in clean_line:
                    try:
                        perc_str = clean_line.split('%')[0].split()[-1]
                        self.after(0, self.progress_var.set, float(perc_str))
                    except: pass
                else:
                    # Loggear info relevante o errores
                    if "Error" in clean_line or "WARNING" in clean_line:
                        self.log(f"7-Zip: {clean_line}")
                    elif not any(ign in clean_line for ign in ["7-Zip", "Copyright", "Scanning", "Creating archive", "Everything is Ok", "Items to compress", "Files read"]):
                        # Solo loggear si parece importante
                        if len(clean_line) > 2:
                            self.log(f"7z info: {clean_line}")

            rc = process.wait()
            if rc != 0:
                self.log(f"7-Zip finalizó con código {rc} (posible error).")
            else:
                self.log("7-Zip finalizó correctamente.")
            
            # Update all to compressed status
            for f in self.found_files: 
                if f['status'] == "Preparado":
                    f['status'] = "Comprimido"
            
            # Cleanup list file
            try: list_file.unlink()
            except: pass

        except Exception as e:
            self.log(f"Error crítico en compresión: {e}")
            for f in self.found_files: f['status'] = "Error"
        
        self.after(0, self.update_tree)
        self.after(0, self.progress_var.set, 100)
        self.is_processing = False # Detiene animación
        self.log(f"Proceso finalizado. Archivos guardados en: {output_folder}")
        self.log("Archivos listos. Usá los botones de abajo para eliminarlos o moverlos de sus ubicaciones originales.")
        self.after(0, lambda: self.set_gui_state(tk.NORMAL))

    def get_selected_files(self):
        selected = self.tree.selection()
        if not selected:
            # If nothing is selected, ask if they want to process all
            if messagebox.askyesno("Ninguno seleccionado", "¿Deseas aplicar la acción a TODOS los archivos listados?"):
                selected = self.tree.get_children()
            else:
                return []
        
        file_paths = []
        for item in selected:
            file_paths.append(self.tree.item(item, "values")[0])
        return file_paths

    def update_status(self, path_str, new_status):
        for item in self.tree.get_children():
            if self.tree.item(item, "values")[0] == path_str:
                self.tree.item(item, "values", (path_str, new_status))
                break

    def delete_selected(self):
        files = self.get_selected_files()
        if not files: return
        
        if not messagebox.askyesno("Confirmar Eliminación", f"¿Estás seguro que deseas ELIMINAR permanentemente {len(files)} archivo(s)?"):
            return

        for path_str in files:
            p = Path(path_str)
            if p.exists():
                try:
                    p.unlink()
                    self.update_status(path_str, "Eliminado")
                    self.log(f"Eliminado: {path_str}")
                except Exception as e:
                    self.update_status(path_str, "Error")
                    self.log(f"Error eliminando {path_str}: {e}")
            else:
                self.update_status(path_str, "No encontrado")

    def move_selected(self):
        files = self.get_selected_files()
        if not files: return

        dest_folder = filedialog.askdirectory(title="Selecciona la carpeta destino para mover los originales")
        if not dest_folder: return
        
        threading.Thread(target=self._run_move_copy, args=(files, dest_folder, "move"), daemon=True).start()

    def copy_selected(self):
        files = self.get_selected_files()
        if not files: return

        dest_folder = filedialog.askdirectory(title="Selecciona la carpeta destino para copiar los originales")
        if not dest_folder: return
        
        threading.Thread(target=self._run_move_copy, args=(files, dest_folder, "copy"), daemon=True).start()

    def _run_move_copy(self, files, dest_folder, action):
        dest_root = Path(dest_folder)
        base_dir = Path(self.dir_var.get())
        total = len(files)
        
        self.after(0, lambda: self.set_gui_state(tk.DISABLED))
        self.after(0, self.progress_var.set, 0)
        
        for i, path_str in enumerate(files):
            p = Path(path_str)
            if p.exists():
                try:
                    # Calcular ruta relativa al root del escaneo
                    if p.is_relative_to(base_dir):
                        rel = p.relative_to(base_dir)
                    else:
                        rel = p.name

                    target_path = dest_root / rel
                    target_path.parent.mkdir(parents=True, exist_ok=True)
                    
                    if action == "move":
                        shutil.move(str(p), str(target_path))
                        self.after(0, self.update_status, path_str, "Movido")
                        self.log(f"Movido a: {target_path}")
                    else:
                        shutil.copy2(str(p), str(target_path))
                        self.after(0, self.update_status, path_str, "Copiado")
                        self.log(f"Copiado a: {target_path}")
                except Exception as e:
                    self.after(0, self.update_status, path_str, "Error")
                    self.log(f"Error operando sobre {path_str}: {e}")
            else:
                self.after(0, self.update_status, path_str, "No encontrado")
                
            # Actualizar barra
            prog = ((i + 1) / total) * 100
            self.after(0, self.progress_var.set, prog)

    def start_dupliminar(self):
        dir_a = self.dupli_dir_a.get()
        dir_b = self.dupli_dir_b.get()
        if not dir_a or not dir_b:
            messagebox.showwarning("Faltan Datos", "Selecciona ambos directorios.")
            return
        
        self.is_processing = True
        # Eliminado el cartel de carga central para disfrutar de la vista en vivo
        
        # Limpiar
        for i in self.tree_a.get_children(): self.tree_a.delete(i)
        for i in self.tree_b.get_children(): self.tree_b.delete(i)
        
        threading.Thread(target=self._run_dupliminar, args=(dir_a, dir_b), daemon=True).start()

    def _run_dupliminar(self, dir_a, dir_b):
        path_a = Path(dir_a)
        path_b = Path(dir_b)
        
        self.log(f"Buscando coincidencias relativas de A ({dir_a}) en B ({dir_b})...")
        
        duplis = []
        count_a = 0
        matches_path = 0
        
        batch_a = []
        batch_b = []
        batch_tags = []
        
        for p_a in path_a.rglob("*"):
            if not self.is_processing: break
            
            if p_a.is_file():
                count_a += 1
                try:
                    rel_path = p_a.relative_to(path_a)
                    p_b = path_b / rel_path
                    
                    is_dup = p_b.exists() and p_b.is_file()
                    t = ("dup",) if is_dup else ()
                    
                    if is_dup:
                        matches_path += 1
                        duplis.append((str(p_a), str(p_b)))
                    
                    # Añadir a lote para la UI
                    batch_a.append(str(p_a))
                    batch_b.append(str(p_b) if is_dup else "--- No encontrado ---")
                    batch_tags.append(t)
                    
                    if len(batch_a) >= 20: 
                        def flush(ba, bb, bt):
                            for a, b, tag_ in zip(ba, bb, bt):
                                self.tree_a.insert("", 0, values=(a,), tags=tag_)
                                self.tree_b.insert("", 0, values=(b,), tags=tag_)
                        self.after(0, flush, list(batch_a), list(batch_b), list(batch_tags))
                        batch_a.clear(); batch_b.clear(); batch_tags.clear()
                        import time
                        time.sleep(0.01) # Pausa micro para que Tkinter respire y se vea fluido
                        
                except Exception as e:
                    self.log(f"Error procesando {p_a.name}: {e}")
                    
        # Flush final
        if batch_a:
            def flush(ba, bb, bt):
                for a, b, tag_ in zip(ba, bb, bt):
                    self.tree_a.insert("", 0, values=(a,), tags=tag_)
                    self.tree_b.insert("", 0, values=(b,), tags=tag_)
            self.after(0, flush, batch_a, batch_b, batch_tags)
                    
        self.log(f"-> Archivos leídos en A: {count_a}")
        self.log(f"-> Comparten exactamente la misma ruta relativa en B: {matches_path}")
        
        # Actualizar UI final
        def update_ui():
            state = tk.NORMAL if duplis else tk.DISABLED
            self.btn_dupli_del.config(state=state)
            self.btn_dupli_move.config(state=state)
            self.btn_dupli_copy.config(state=state)
            
            self.is_processing = False
            messagebox.showinfo("Dupliminar", f"Búsqueda finalizada.\nLeídos: {count_a}\nDuplicados Encontrados: {matches_path}")

        self.after(0, update_ui)

    def dupli_action(self, action):
        selected = self.tree_a.get_children() 
        # Filtrar solo aquellos ítems que tienen la etiqueta naranja "dup"
        file_paths = [self.tree_a.item(item, "values")[0] for item in selected if "dup" in self.tree_a.item(item, "tags")]
        
        if not file_paths: return
        
        self.is_processing = True
        self.loading_canvas.place(relx=0.5, rely=0.4, anchor=tk.CENTER)
        self.animate_loading()

        def _run_action():
            total = len(file_paths)
            if action == "delete":
                if not messagebox.askyesno("Confirmar", f"¿Eliminar {total} archivos de la ubicación A?"): 
                    self.after(0, self._stop_dupli_processing)
                    return
                for i, p_str in enumerate(file_paths):
                    try: 
                        Path(p_str).unlink()
                        self.log(f"Eliminado: {p_str}")
                    except Exception as e: self.log(f"Error: {e}")
                    self.after(0, self.progress_var.set, (i+1)/total*100)
            else:
                dest = filedialog.askdirectory(title="Selecciona destino")
                if not dest: 
                    self.after(0, self._stop_dupli_processing)
                    return
                
                for i, p_str in enumerate(file_paths):
                    p = Path(p_str)
                    target = Path(dest) / p.name
                    try:
                        if action == "move": shutil.move(str(p), str(target)); self.log(f"Movido: {p_str}")
                        else: shutil.copy2(str(p), str(target)); self.log(f"Copiado: {p_str}")
                    except Exception as e: self.log(f"Error: {e}")
                    self.after(0, self.progress_var.set, (i+1)/total*100)
            
            self.after(0, self._stop_dupli_processing)
            self.after(0, self.start_dupliminar) # Refrescar

        threading.Thread(target=_run_action, daemon=True).start()

    def _stop_dupli_processing(self):
        self.is_processing = False
        self.progress_var.set(0)

if __name__ == "__main__":
    app = SaneadorApp()
    app.mainloop()
