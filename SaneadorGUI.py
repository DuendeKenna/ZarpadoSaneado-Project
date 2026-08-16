import os
import sys
import shutil
import subprocess
import threading
import json
import ctypes
import time
from pathlib import Path

import webview

# ==========================================
# RUTAS Y CONFIGURACIÓN
# ==========================================
if getattr(sys, 'frozen', False):
    BASE_PATH = sys._MEIPASS
    EXE_DIR = os.path.dirname(sys.executable)
else:
    BASE_PATH = os.path.dirname(os.path.abspath(__file__))
    EXE_DIR = BASE_PATH

CONFIG_FILE = os.path.join(os.environ.get('TEMP', os.getcwd()), "Saneador_config.json")
ASSETS_DIR = os.path.join(BASE_PATH, "assets")
UI_HTML_PATH = os.path.join(ASSETS_DIR, "ui.html")

COMPRESSION_LEVELS = {
    "Store (Sin compresión)": "-mx0",
    "Fast (Rápido)": "-mx1",
    "Normal": "-mx5",
    "Maximum (Máximo)": "-mx7",
    "Ultra (Lento pero efectivo)": "-mx9"
}

TARGET_EXTENSIONS = {'.exe', '.dll', '.bat', '.cmd', '.scr', '.vbs', '.ps1'}

def find_7z():
    p_local = os.path.join(BASE_PATH, "7za.exe")
    if os.path.exists(p_local):
        return p_local
    for p in ["C:\\Program Files\\7-Zip\\7z.exe", "C:\\Program Files (x86)\\7-Zip\\7z.exe"]:
        if os.path.exists(p):
            return p
    return None

# ==========================================
# API DE PYTHON PARA PYWEBVIEW
# ==========================================
class ZarpadoSaneadoAPI:
    def __init__(self):
        self._window = None
        self.seven_z_path = find_7z()
        self.found_files = []
        self.is_processing = False
        self.config_data = {
            "dir_scan": os.path.abspath("."),
            "dupli_a": os.path.abspath("."),
            "dupli_b": ""
        }
        self.load_config()

    def set_window(self, window):
        self._window = window

    def on_loaded(self):
        def _async_init():
            self._window.evaluate_js(f"ui.setConfigs({json.dumps(self.config_data)});")
            z_status = Path(self.seven_z_path).name if self.seven_z_path else "No detectado"
            self._window.evaluate_js(f"ui.set7zStatus('{z_status}');")
            dir_scan = self.config_data.get("dir_scan", os.path.abspath("."))
            out_dir = Path(dir_scan) / "_zaneado"
            has_harvested = False
            try:
                has_harvested = out_dir.exists() and any(out_dir.iterdir())
            except Exception:
                pass
            self._window.evaluate_js(f"ui.setHarvestButtonsState(true, {'true' if has_harvested else 'false'});")
            self.log(f"ZarpadoSaneado iniciado. 7-Zip: {z_status}")

        threading.Thread(target=_async_init, daemon=True).start()

    def load_config(self):
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    self.config_data.update(json.load(f))
            except Exception:
                pass

    def save_config(self):
        try:
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(self.config_data, f, indent=4)
        except Exception:
            pass

    def log(self, text):
        clean_txt = str(text).replace("'", "\\'").replace("\n", " ")
        if self._window:
            self._window.evaluate_js(f"ui.log('{clean_txt}');")

    # Controles de ventana
    def start_drag(self):
        try:
            user32 = ctypes.windll.user32
            fg_hwnd = user32.GetForegroundWindow()
            root_hwnd = user32.GetAncestor(fg_hwnd, 2)
            if not root_hwnd:
                root_hwnd = fg_hwnd
            user32.ReleaseCapture()
            user32.SendMessageW(root_hwnd, 0x0112, 0xF012, 0)
        except Exception:
            pass

    def minimize(self):
        if self._window:
            self._window.minimize()

    def toggle_maximize(self):
        if self._window:
            self._window.toggle_fullscreen()

    def close(self):
        self.save_config()
        if self._window:
            self._window.destroy()
        os._exit(0)

    def browse_dir(self, target):
        init_d = self.config_data.get(target, os.path.abspath("."))
        if not os.path.exists(init_d):
            init_d = os.path.abspath(".")

        d = None
        if self._window:
            res = self._window.create_file_dialog(webview.FOLDER_DIALOG, directory=init_d)
            if res and len(res) > 0:
                d = res[0]

        if d:
            abs_d = os.path.abspath(d)
            if target == "scan":
                self.config_data["dir_scan"] = abs_d
            elif target == "dupli_a":
                self.config_data["dupli_a"] = abs_d
            elif target == "dupli_b":
                self.config_data["dupli_b"] = abs_d

            self.save_config()
            self._window.evaluate_js(f"ui.setConfigs({json.dumps(self.config_data)});")

    def open_output_folder(self):
        dir_scan = self.config_data.get("dir_scan", os.path.abspath("."))
        out_dir = Path(dir_scan) / "_zaneado"
        if not out_dir.exists():
            out_dir.mkdir(exist_ok=True)
        try:
            os.startfile(str(out_dir))
            self.log(f"Carpeta abierta: {out_dir}")
        except Exception as e:
            self.log(f"Error abriendo carpeta: {e}")

    def open_virustotal_window(self):
        def _launch():
            try:
                webview.create_window(
                    title="VirusTotal - Analizador de Archivos",
                    url="https://www.virustotal.com/gui/home/upload",
                    width=960,
                    height=700
                )
            except Exception as e:
                self.log(f"Error abriendo ventana de VirusTotal: {e}")
        threading.Thread(target=_launch, daemon=True).start()
        self.log("Abriendo ventana de VirusTotal...")

    def open_virustotal_browser(self):
        def _launch_browser():
            import webbrowser
            webbrowser.open("https://www.virustotal.com/gui/home/upload")
        threading.Thread(target=_launch_browser, daemon=True).start()
        self.log("Abriendo VirusTotal en navegador web...")

    def open_ai_external(self, ai_name, url):
        def _launch():
            import webbrowser
            webbrowser.open(url)
        threading.Thread(target=_launch, daemon=True).start()
        self.log(f"Abriendo {ai_name} en navegador web...")

    def open_ai_browser(self, ai_name, url):
        def _launch():
            try:
                webview.create_window(
                    title=f"{ai_name} - Auditoría IA",
                    url=url,
                    width=1000,
                    height=750
                )
            except Exception as e:
                self.log(f"Error abriendo {ai_name}: {e}")
        threading.Thread(target=_launch, daemon=True).start()
        self.log(f"Abriendo {ai_name} (ventana integrada)...")

    # ==========================================
    # COSECHADORA V2 ENGINE
    # ==========================================
    def start_process(self, config):
        if self.is_processing:
            return

        if not self.seven_z_path:
            self.seven_z_path = find_7z()
            if not self.seven_z_path:
                self.log("ERROR: 7-Zip (7za.exe) no fue encontrado.")
                return

        self.config_data["dir_scan"] = config.get("dir_scan", self.config_data["dir_scan"])
        self.save_config()

        self.found_files.clear()
        self._window.evaluate_js("ui.clearLog(); ui.updateHarvestTree([]); ui.setHarvestButtonsState(false);")
        self._window.evaluate_js("ui.setProgress(0, 'Iniciando búsqueda de archivos...');")

        self.is_processing = True
        threading.Thread(target=self._process_files_thread, args=(config,), daemon=True).start()

    def _process_files_thread(self, config):
        root_dir = Path(config["dir_scan"])
        if not root_dir.exists() or not root_dir.is_dir():
            self.log(f"Error: El directorio {root_dir} no existe.")
            self._window.evaluate_js("ui.setHarvestButtonsState(true); ui.setProgress(0, 'Error');")
            self.is_processing = False
            return

        fmt = config.get("format", "zip")
        level_switch = COMPRESSION_LEVELS.get(config.get("level", "Normal"), "-mx5")
        split_enabled = config.get("split_enabled", False)

        split_size_raw = str(config.get("split_size", "500")).strip()
        split_size = "".join(filter(str.isdigit, split_size_raw))
        if not split_size: split_size = "500"

        self.log(f"Buscando archivos sospechosos en: {root_dir}")
        output_folder = root_dir / "_zaneado"

        targets = []
        scanned_count = 0
        try:
            for root, dirs, files in os.walk(str(root_dir)):
                if "_zaneado" in dirs:
                    dirs.remove("_zaneado")
                for f in files:
                    scanned_count += 1
                    p = Path(root) / f
                    if p.suffix.lower() in TARGET_EXTENSIONS:
                        targets.append(p)
                    if scanned_count % 30 == 0:
                        prog = min(20.0, (scanned_count / 300.0) * 20.0)
                        self._window.evaluate_js(f"ui.setProgress({prog:.1f}, 'Buscando ({scanned_count} analizados, {len(targets)} sospechosos)...');")
        except Exception as e:
            self.log(f"Error escaneando: {e}")

        if not targets:
            self.log("No se encontraron ejecutables ni librerías sospechosas.")
            self._window.evaluate_js("ui.setHarvestButtonsState(true); ui.setProgress(0, 'Sin archivos sospechosos');")
            self.is_processing = False
            return

        self._window.evaluate_js(f"ui.setProgress(20, 'Búsqueda lista: {len(targets)} archivo(s) encontrados.');")
        self.log(f"Se encontraron {len(targets)} archivo(s) sospechoso(s).")

        # Comprobar peso total para alertar si supera 666 MB
        total_bytes = 0
        for p in targets:
            try:
                total_bytes += p.stat().st_size
            except Exception:
                pass
        total_mb = total_bytes / (1024 * 1024)
        self.log(f"Peso total de sospechosos a comprimir: {total_mb:.1f} MB")

        if total_mb > 666 and not split_enabled:
            self.log(f"Aviso: El peso total ({total_mb:.1f} MB) supera los 666 MB recomendados.")
            ask_msg = f"Los archivos a comprimir pesan {total_mb:.1f} MB (superan 666 MB).\\n\\n¿Deseas activar la división en partes de 500 MB para poder subirlos a VirusTotal?"
            try:
                user_wants_split = self._window.evaluate_js(f"confirm('{ask_msg}')")
                if user_wants_split:
                    split_enabled = True
                    split_size = "500"
                    self._window.evaluate_js("document.getElementById('split_enabled').checked = true; toggleSplit();")
                    self.log("División en partes de 500 MB activada automáticamente por confirmación del usuario.")
                else:
                    self.log("El usuario decidió continuar sin división en partes.")
            except Exception as e:
                self.log(f"Consulta de división omitida: {e}")

        output_folder.mkdir(exist_ok=True)

        for fpath in targets:
            self.found_files.append({"path": str(fpath), "status": "Preparado"})

        self._window.evaluate_js(f"ui.updateHarvestTree({json.dumps(self.found_files)});")

        list_file = output_folder / "file_list_to_compress.txt"
        with open(list_file, "w", encoding="utf-8-sig") as lf:
            for fpath in targets:
                try:
                    rel = fpath.relative_to(root_dir)
                    lf.write(str(rel) + "\n")
                except ValueError:
                    lf.write(str(fpath) + "\n")

        self.log(f"Lista de compresión generada con {len(targets)} entradas.")

        zip_path = output_folder / f"Analisis_Completo.{fmt}"
        if zip_path.exists():
            try: zip_path.unlink()
            except Exception: pass

        cmd = [self.seven_z_path, "a", level_switch, "-y", "-ssw", "-bsp1", "-bb1", str(zip_path), f"@{list_file}"]
        if split_enabled:
            cmd.append(f"-v{split_size}m")

        self.log(f"Ejecutando 7-Zip: {' '.join(cmd)}")

        try:
            process = subprocess.Popen(cmd, cwd=str(root_dir), creationflags=subprocess.CREATE_NO_WINDOW,
                                       stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                       text=True, encoding='latin-1', errors='replace')

            for line in process.stdout:
                clean_line = line.replace('\b', '').replace('\r', '').strip()
                if not clean_line: continue

                if "%" in clean_line:
                    try:
                        perc_str = clean_line.split('%')[0].split()[-1]
                        val = float(perc_str)
                        total_progress = 20.0 + (val * 0.8)
                        self._window.evaluate_js(f"ui.setProgress({total_progress:.1f}, 'Comprimiendo con 7-Zip ({val:.0f}%)...');")
                    except Exception:
                        pass
                else:
                    if "Error" in clean_line or "WARNING" in clean_line:
                        self.log(f"7-Zip: {clean_line}")

            rc = process.wait()
            if rc == 0:
                self.log("7-Zip finalizó correctamente.")
                for f in self.found_files:
                    if f['status'] == "Preparado": f['status'] = "Comprimido"
            else:
                self.log(f"7-Zip finalizó con código {rc}.")

            try: list_file.unlink()
            except Exception: pass

        except Exception as e:
            self.log(f"Error crítico en compresión: {e}")
            for f in self.found_files: f['status'] = "Error"

        self.is_processing = False
        self._window.evaluate_js(f"ui.updateHarvestTree({json.dumps(self.found_files)});")
        self._window.evaluate_js("ui.setProgress(100, 'Cosecha completada');")
        self._window.evaluate_js("ui.setHarvestButtonsState(true, true);")
        self._window.evaluate_js("ui.onHarvestComplete();")
        self.log(f"Proceso finalizado. Archivos guardados en: {output_folder}")

    def delete_selected(self, files):
        if not files: return
        for p_str in files:
            p = Path(p_str)
            if p.exists():
                try:
                    p.unlink()
                    self._update_file_status(p_str, "Eliminado")
                    self.log(f"Eliminado: {p_str}")
                except Exception as e:
                    self._update_file_status(p_str, "Error")
                    self.log(f"Error eliminando {p_str}: {e}")
            else:
                self._update_file_status(p_str, "No encontrado")
        self._window.evaluate_js(f"ui.updateHarvestTree({json.dumps(self.found_files)});")

    def move_selected(self, files):
        if not files or not self._window: return
        res = self._window.create_file_dialog(webview.FOLDER_DIALOG)
        dest = res[0] if res and len(res) > 0 else None
        if not dest: return
        threading.Thread(target=self._run_move_copy, args=(files, dest, "move"), daemon=True).start()

    def copy_selected(self, files):
        if not files or not self._window: return
        res = self._window.create_file_dialog(webview.FOLDER_DIALOG)
        dest = res[0] if res and len(res) > 0 else None
        if not dest: return
        threading.Thread(target=self._run_move_copy, args=(files, dest, "copy"), daemon=True).start()

    def _run_move_copy(self, files, dest_folder, action):
        dest_root = Path(dest_folder)
        base_dir = Path(self.config_data.get("dir_scan", "."))
        total = len(files)

        self._window.evaluate_js("ui.setHarvestButtonsState(false);")

        for i, path_str in enumerate(files):
            p = Path(path_str)
            if p.exists():
                try:
                    rel = p.relative_to(base_dir) if p.is_relative_to(base_dir) else p.name
                    target = dest_root / rel
                    target.parent.mkdir(parents=True, exist_ok=True)

                    if action == "move":
                        shutil.move(str(p), str(target))
                        self._update_file_status(path_str, "Movido")
                        self.log(f"Movido: {target}")
                    else:
                        shutil.copy2(str(p), str(target))
                        self._update_file_status(path_str, "Copiado")
                        self.log(f"Copiado: {target}")
                except Exception as e:
                    self._update_file_status(path_str, "Error")
                    self.log(f"Error en {path_str}: {e}")
            else:
                self._update_file_status(path_str, "No encontrado")

            prog = ((i + 1) / total) * 100
            self._window.evaluate_js(f"ui.setProgress({prog}, '{'Moviendo' if action == 'move' else 'Copiando'}...');")

        self._window.evaluate_js(f"ui.updateHarvestTree({json.dumps(self.found_files)});")
        self._window.evaluate_js("ui.setHarvestButtonsState(true);")

    def _update_file_status(self, path_str, new_status):
        for f in self.found_files:
            if f['path'] == path_str:
                f['status'] = new_status
                break

    # ==========================================
    # DUPLIMINAR ENGINE
    # ==========================================
    def start_dupliminar(self, dir_a, dir_b):
        if self.is_processing: return
        if not dir_a or not dir_b:
            self.log("Selecciona ambos directorios para Dupliminar.")
            return

        self.config_data["dupli_a"] = dir_a
        self.config_data["dupli_b"] = dir_b
        self.save_config()

        self.is_processing = True
        self._window.evaluate_js("ui.clearDupliTrees(); ui.setDupliButtonsState(false);")
        self._window.evaluate_js("ui.setIndeterminate(true, 'Buscando duplicados...');")

        threading.Thread(target=self._run_dupliminar, args=(dir_a, dir_b), daemon=True).start()

    def _run_dupliminar(self, dir_a, dir_b):
        path_a = Path(dir_a)
        path_b = Path(dir_b)

        self.log(f"Buscando coincidencias relativas entre A ({dir_a}) y B ({dir_b})...")

        count_a = 0
        matches = 0
        batch = []

        for p_a in path_a.rglob("*"):
            if not self.is_processing: break
            if p_a.is_file():
                count_a += 1
                try:
                    rel = p_a.relative_to(path_a)
                    p_b = path_b / rel
                    is_dup = p_b.exists() and p_b.is_file()

                    if is_dup:
                        matches += 1

                    batch.append({
                        "a": str(p_a),
                        "b": str(p_b) if is_dup else "--- No encontrado ---",
                        "is_dup": is_dup
                    })

                    if len(batch) >= 20:
                        self._window.evaluate_js(f"ui.appendDupliRows({json.dumps(batch)});")
                        batch.clear()
                        time.sleep(0.01)
                except Exception as e:
                    self.log(f"Error procesando {p_a.name}: {e}")

        if batch:
            self._window.evaluate_js(f"ui.appendDupliRows({json.dumps(batch)});")

        self.log(f"Dupliminar finalizado. Leídos en A: {count_a} | Duplicados en B: {matches}")
        self.is_processing = False
        self._window.evaluate_js("ui.setIndeterminate(false, 'Dupliminar completado'); ui.setProgress(100);")
        self._window.evaluate_js(f"ui.setDupliButtonsState({'true' if matches > 0 else 'false'});")

    def dupli_action(self, action):
        dir_a = self.config_data.get("dupli_a", "")
        dir_b = self.config_data.get("dupli_b", "")
        if not dir_a or not dir_b: return

        self.is_processing = True
        self._window.evaluate_js("ui.setDupliButtonsState(false);")
        self._window.evaluate_js(f"ui.setIndeterminate(true, '{action.upper()} duplicados...');")

        def _run():
            path_a = Path(dir_a)
            path_b = Path(dir_b)

            dest_folder = None
            if action != "delete":
                if self._window:
                    res = self._window.create_file_dialog(webview.FOLDER_DIALOG)
                    dest_folder = res[0] if res and len(res) > 0 else None
                if not dest_folder:
                    self.is_processing = False
                    self._window.evaluate_js("ui.setIndeterminate(false, 'Cancelado');")
                    self._window.evaluate_js("ui.setDupliButtonsState(true);")
                    return

            duplis = []
            for p_a in path_a.rglob("*"):
                if p_a.is_file():
                    try:
                        rel = p_a.relative_to(path_a)
                        p_b = path_b / rel
                        if p_b.exists() and p_b.is_file():
                            duplis.append(p_a)
                    except Exception:
                        pass

            total = len(duplis)
            for i, p in enumerate(duplis):
                try:
                    if action == "delete":
                        p.unlink()
                        self.log(f"Eliminado de A: {p}")
                    else:
                        target = Path(dest_folder) / p.name
                        if action == "move":
                            shutil.move(str(p), str(target))
                            self.log(f"Movido de A a: {target}")
                        else:
                            shutil.copy2(str(p), str(target))
                            self.log(f"Copiado de A a: {target}")
                except Exception as e:
                    self.log(f"Error operando {p}: {e}")

                prog = ((i + 1) / total) * 100
                self._window.evaluate_js(f"ui.setProgress({prog}, '{action.capitalize()}...');")

            self.is_processing = False
            self.start_dupliminar(dir_a, dir_b)

        threading.Thread(target=_run, daemon=True).start()


# ==========================================
# INICIALIZACIÓN DE LA APLICACIÓN
# ==========================================
def main():
    api = ZarpadoSaneadoAPI()
    win_w = 650
    win_h = 730
    try:
        user32 = ctypes.windll.user32
        sw = user32.GetSystemMetrics(0)
        sh = user32.GetSystemMetrics(1)
        center_x = max(0, (sw - win_w) // 2)
        center_y = max(0, (sh - win_h) // 2)
    except Exception:
        center_x = 100
        center_y = 100

    PROFILE_DIR = os.path.join(os.environ.get('APPDATA', os.getcwd()), "ZarpadoSaneado", "WebProfile")
    os.makedirs(PROFILE_DIR, exist_ok=True)

    window = webview.create_window(
        title="ZarpadoSaneado",
        url=UI_HTML_PATH,
        js_api=api,
        frameless=True,
        easy_drag=False,
        transparent=False,
        resizable=True,
        x=center_x,
        y=center_y,
        width=win_w,
        height=win_h,
        min_size=(560, 600),
        background_color="#0051ee"
    )
    def _on_closed():
        api.save_config()
        os._exit(0)

    window.events.closed += _on_closed
    api.set_window(window)
    USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
    webview.start(api.on_loaded, debug=False, private_mode=False, storage_path=PROFILE_DIR, user_agent=USER_AGENT)
    os._exit(0)

if __name__ == "__main__":
    main()
