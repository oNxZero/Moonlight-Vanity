import evdev
import select
import threading
import time

class GlobalListener:
    def __init__(
        self,
        toggle_cb,
        start_cb,
        stop_cb,
        rebind_cb,
        toggle_gui_cb,
        initial_keys=None,
        initial_mode="toggle",
        initial_app_mode="mouse"
    ):
        if initial_keys is None: initial_keys = {}
        self.trigger_left = initial_keys.get('left', 64)
        self.trigger_right = initial_keys.get('right', 65)
        self.hide_key = initial_keys.get('hide', 54)

        self.mode_app = initial_app_mode
        self.mode_trigger = initial_mode

        self.holding_left = False
        self.holding_right = False
        self.pending_left_mouse = False
        self.pending_right_mouse = False
        self.is_paused = False

        self.gui_visible = True

        self.toggle_cb = toggle_cb
        self.start_cb = start_cb
        self.stop_cb = stop_cb
        self.rebind_cb = rebind_cb
        self.toggle_gui_cb = toggle_gui_cb

        self.stop_event = threading.Event()
        self.rebind_mode = None
        self.devices = []

    def get_nice_name(self, code: int) -> str:
        if code == evdev.ecodes.BTN_LEFT: return "Left Click"
        if code == evdev.ecodes.BTN_RIGHT: return "Right Click"
        if code == evdev.ecodes.BTN_MIDDLE: return "Middle Click"
        if code == evdev.ecodes.KEY_RIGHTSHIFT: return "Right Shift"
        if code == evdev.ecodes.KEY_LEFTSHIFT: return "Left Shift"
        if code == -1: return "Select Key..."

        try:
            name = evdev.ecodes.keys.get(code, f"KEY_{code}")
            if isinstance(name, list): name = name[0]
            return str(name).replace("KEY_", "").replace("BTN_", "").replace("_", " ").title()
        except:
            return "Unknown"

    def set_app_mode(self, mode):
        self.mode_app = mode
        self.stop_all()

    def set_trigger_mode(self, mode):
        self.mode_trigger = mode
        self.stop_all()

    def set_paused(self, paused: bool):
        self.is_paused = paused
        if paused: self.stop_all()

    def stop_all(self):
        if self.holding_left:
            self.stop_cb('left')
            self.holding_left = False
        if self.holding_right:
            self.stop_cb('right')
            self.holding_right = False
        self.pending_left_mouse = False
        self.pending_right_mouse = False

    def start_rebind(self, mode):
        self.rebind_mode = mode

    def start(self):
        t = threading.Thread(target=self._loop, daemon=True)
        t.start()

    def stop(self):
        self.stop_event.set()

    def _loop(self):
        while not self.stop_event.is_set():
            if not self.devices:
                self.devices = [d for d in [evdev.InputDevice(path) for path in evdev.list_devices()] if "Moonlight HID" not in d.name]
                if not self.devices:
                    time.sleep(0.5)
                    continue

            try:
                r, _, _ = select.select(self.devices, [], [], 0.5)
                for dev in r:
                    for event in dev.read():
                        if event.type != evdev.ecodes.EV_KEY: continue
                        val, code = event.value, event.code

                        if self.rebind_mode and val == 1:

                            if code == evdev.ecodes.KEY_ESC:
                                old_code = -1
                                old_name = "Select Key..."

                                if self.rebind_mode == 'trigger_left': old_code = self.trigger_left
                                elif self.rebind_mode == 'trigger_right': old_code = self.trigger_right
                                elif self.rebind_mode == 'hide': old_code = self.hide_key

                                if old_code != -1: old_name = self.get_nice_name(old_code)

                                self.rebind_cb(old_name, old_code, self.rebind_mode)
                                self.rebind_mode = None
                                continue

                            if self.rebind_mode in ['hide', 'trigger_left', 'trigger_right'] and code in [evdev.ecodes.BTN_LEFT, evdev.ecodes.BTN_RIGHT]:
                                continue

                            if self.rebind_mode in ['trigger_left', 'trigger_right'] and code == self.hide_key:
                                continue

                            if self.rebind_mode == 'hide' and (code == self.trigger_left or code == self.trigger_right):
                                continue

                            nice = self.get_nice_name(code)

                            if self.rebind_mode == 'trigger_left':
                                self.trigger_left = code
                                self.rebind_cb(nice, code, 'trigger_left')
                            elif self.rebind_mode == 'trigger_right':
                                self.trigger_right = code
                                self.rebind_cb(nice, code, 'trigger_right')
                            elif self.rebind_mode == 'target':
                                self.rebind_cb(nice, code, 'target')
                            elif self.rebind_mode == 'hide':
                                self.hide_key = code
                                self.rebind_cb(nice, code, 'hide')

                            self.rebind_mode = None
                            continue

                        if code == self.hide_key and val == 1:
                            self.gui_visible = not self.gui_visible
                            self.toggle_gui_cb(self.gui_visible)
                            continue

                        if self.is_paused: continue

                        def process_trigger(t_code, channel):
                            if self.mode_app == 'keyboard' and channel == 'right':
                                return

                            if code == t_code:
                                is_mouse_phys = (code in [evdev.ecodes.BTN_LEFT, evdev.ecodes.BTN_RIGHT])

                                if self.mode_trigger == 'toggle':
                                    if val == 1: self.toggle_cb(channel)

                                elif self.mode_trigger == 'hold':
                                    if val == 1:
                                        if channel == 'left' and not self.holding_left:
                                            self.holding_left = True
                                            if is_mouse_phys: self.pending_left_mouse = True
                                            else: self.start_cb('left')
                                        if channel == 'right' and not self.holding_right:
                                            self.holding_right = True
                                            if is_mouse_phys: self.pending_right_mouse = True
                                            else: self.start_cb('right')

                                    elif val == 0:
                                        if channel == 'left' and self.holding_left:
                                            self.holding_left = False
                                            if self.pending_left_mouse: self.pending_left_mouse = False
                                            else: self.stop_cb('left')
                                        if channel == 'right' and self.holding_right:
                                            self.holding_right = False
                                            if self.pending_right_mouse: self.pending_right_mouse = False
                                            else: self.stop_cb('right')

                                    if val == 0:
                                        if channel == 'left' and self.pending_left_mouse:
                                            self.pending_left_mouse = False
                                            self.start_cb('left')

                        process_trigger(self.trigger_left, 'left')
                        process_trigger(self.trigger_right, 'right')

            except Exception:
                self.devices = []
