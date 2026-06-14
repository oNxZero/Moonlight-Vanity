import sys
import os
import multiprocessing
import signal
import ctypes
import json
import gi

gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Gtk, Adw, Gdk, GLib

from ui_builder import MainWindow
from ghost_core import GhostEngine
from input_listener import GlobalListener
from managers import PresetManager

CONFIG_DIR = os.path.expanduser("~/.config/Moonlight")
CONFIG_FILE = os.path.join(CONFIG_DIR, "config.json")

DEFAULT_CONFIG = {
    'cps_left': 12.0,
    'cps_right': 12.0,
    'jitter': 2.0,
    'rand': 1,
    'mode': 'mouse',
    'target_btn': -1,
    'trigger_mode': 'toggle',
    'trigger_left': 64,
    'trigger_right': 65,
    'hide_key': 54,
    'assist_wtap': False,
    'assist_wtap_chance': 5.0,
    'assist_blockhit': False,
    'assist_blockhit_chance': 5.0
}

def mask_process():
    try:
        libc = ctypes.cdll.LoadLibrary('libc.so.6')
        name = b"kworker/u12:0"
        libc.prctl(15, name, 0, 0, 0)
    except Exception:
        pass

def install_app_icon():
    try:
        icon_dir = os.path.expanduser("~/.local/share/icons/hicolor/scalable/apps")
        os.makedirs(icon_dir, exist_ok=True)

        dest_path = os.path.join(icon_dir, "com.moonlight.final.svg")
        source_path = os.path.join(os.path.dirname(__file__), "icon.svg")

        if os.path.exists(source_path):
            with open(source_path, "r") as src:
                icon_content = src.read()
            with open(dest_path, "w") as dest:
                dest.write(icon_content)

            os.system("gtk4-update-icon-cache -f -t " + os.path.expanduser("~/.local/share/icons/hicolor/"))
        else:
            print("Warning: icon.svg not found. Taskbar icon may be missing.")

    except Exception as e:
        print(f"Icon installation warning: {e}")

def backend_proc(state_q, config_q):
    mask_process()
    signal.signal(signal.SIGINT, signal.SIG_IGN)
    eng = GhostEngine()
    eng.run(state_q, config_q)

class MoonlightApp(Adw.Application):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        install_app_icon()

        self.connect('activate', self.on_activate)
        self.connect('shutdown', self.on_shutdown)

        self.state_q = multiprocessing.Queue()
        self.config_q = multiprocessing.Queue()

        self.proc = multiprocessing.Process(target=backend_proc, args=(self.state_q, self.config_q))
        self.proc.daemon = True
        self.proc.start()

        self.active_left = False
        self.active_right = False

        self.config = self.load_config()
        self.preset_mgr = PresetManager(CONFIG_DIR, DEFAULT_CONFIG)

        self.theme_provider = Gtk.CssProvider()
        Gtk.StyleContext.add_provider_for_display(
            Gdk.Display.get_default(),
            self.theme_provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION + 10
        )

        mask_process()

    def load_config(self):
        if not os.path.exists(CONFIG_DIR):
            os.makedirs(CONFIG_DIR, exist_ok=True)

        cfg = DEFAULT_CONFIG.copy()
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, 'r') as f:
                    saved = json.load(f)
                    cfg.update(saved)
            except Exception as e:
                print(f"Failed to load config: {e}")
        cfg['assist_wtap'] = False
        cfg['assist_blockhit'] = False
        return cfg

    def save_config(self):
        try:
            with open(CONFIG_FILE, 'w') as f:
                json.dump(self.config, f, indent=4)
        except Exception as e:
            print(f"Failed to save config: {e}")

    def on_activate(self, app):
        self.hold()

        css = Gtk.CssProvider()
        css_path = os.path.join(os.path.dirname(__file__), 'style.css')
        if os.path.exists(css_path):
            css.load_from_path(css_path)
            Gtk.StyleContext.add_provider_for_display(
                Gdk.Display.get_default(),
                css,
                Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
            )

        self.refresh_dynamic_theme()

        self.listener = GlobalListener(
            toggle_cb=self.trigger_toggle,
            start_cb=self.trigger_start,
            stop_cb=self.trigger_stop,
            rebind_cb=self.update_bind_label,
            toggle_gui_cb=self.toggle_gui,
            initial_keys={
                'left': self.config.get('trigger_left', 64),
                'right': self.config.get('trigger_right', 65),
                'hide': self.config.get('hide_key', 54)
            },
            initial_mode=self.config.get('trigger_mode', 'toggle'),
            initial_app_mode=self.config.get('mode', 'mouse')
        )
        self.listener.start()

        self.config_q.put(self.config)

        self.win = MainWindow(
            app,
            self.ui_toggle_request,
            self.handle_config_change,
            self.send_suspend,
            self.listener,
            self.config,
            self.preset_mgr,
            self.handle_theme_change,
            self.handle_preset_action
        )
        self.win.present()

    def handle_theme_change(self, key, is_custom=False, color_val=None):
        if is_custom:
            self.preset_mgr.update_custom_color(key, color_val)
        else:
            self.preset_mgr.set_base_theme(key)
        self.refresh_dynamic_theme()

    def refresh_dynamic_theme(self):
        data = self.preset_mgr.get_active_theme()
        css_str = ""
        for key, val in data.items():
            css_str += f"@define-color {key} {val};\n"
        self.theme_provider.load_from_string(css_str)

    def handle_preset_action(self, action, name):
        if action == "save":
            return self.preset_mgr.save_preset(name, self.config)
        elif action == "delete":
            self.preset_mgr.delete_preset(name)
        elif action == "load":
            cfg = self.preset_mgr.load_preset(name)
            if cfg:
                clean_cfg = {k:v for k,v in cfg.items() if k != '_theme_config'}
                clean_cfg['assist_wtap'] = False
                clean_cfg['assist_blockhit'] = False
                self.config.update(clean_cfg)
                self.save_config()
                self.config_q.put(clean_cfg)
                self.refresh_dynamic_theme()
                return cfg
        return None

    def ui_toggle_request(self, active, channel):
        if channel == 'left':
            self.active_left = active
            self.send_state("ENABLE_LEFT" if active else "DISABLE_LEFT")

    def trigger_toggle(self, channel):
        if channel == 'left':
            self.active_left = not self.active_left
            self.send_state("ENABLE_LEFT" if self.active_left else "DISABLE_LEFT")
        elif channel == 'right':
            self.active_right = not self.active_right
            self.send_state("ENABLE_RIGHT" if self.active_right else "DISABLE_RIGHT")
        self.update_visuals()

    def trigger_start(self, channel):
        if channel == 'left':
            self.active_left = True
            self.send_state("ENABLE_LEFT")
        elif channel == 'right':
            self.active_right = True
            self.send_state("ENABLE_RIGHT")
        self.update_visuals()

    def trigger_stop(self, channel):
        if channel == 'left':
            self.active_left = False
            self.send_state("DISABLE_LEFT")
        elif channel == 'right':
            self.active_right = False
            self.send_state("DISABLE_RIGHT")
        self.update_visuals()

    def update_visuals(self):
        if hasattr(self, 'win'):
            GLib.idle_add(self.win.set_active_visuals, self.active_left, self.active_right)

    def update_bind_label(self, nice_name, code, mode):
        if mode == 'trigger_left': self.config['trigger_left'] = code
        elif mode == 'trigger_right': self.config['trigger_right'] = code
        elif mode == 'hide': self.config['hide_key'] = code
        elif mode == 'target': self.config['target_btn'] = code
        self.save_config()

        if hasattr(self, 'win'):
            GLib.idle_add(self.win.update_bind_label, nice_name, code, mode)

    def toggle_gui(self, visible: bool):
        def _do():
            self.win.set_visible(visible)
        GLib.idle_add(_do)

    def send_state(self, msg):
        self.state_q.put(msg)

    def handle_config_change(self, cfg: dict):
        cfg['assist_wtap'] = False
        cfg['assist_blockhit'] = False
        self.config.update(cfg)
        self.save_config()
        self.config_q.put(cfg)

    def send_suspend(self, suspend: bool):
        self.state_q.put("PAUSE" if suspend else "RESUME")

    def on_shutdown(self, app):
        try: self.state_q.put("STOP")
        except: pass
        try: self.listener.stop()
        except: pass
        if self.proc.is_alive():
            self.proc.terminate()

if __name__ == "__main__":
    sys.path.append(os.path.abspath(os.path.dirname(__file__)))
    app = MoonlightApp(application_id="com.moonlight.final")
    try:
        app.run(sys.argv)
    except KeyboardInterrupt:
        pass
