import time
import random
import sys
from evdev import UInput, ecodes as e

from click_sounds import ClickSoundPlayer

class HighResSleeper:
    def __init__(self, spin_cap_sec=0.00025, drift_sec=0.00002):
        self.spin_cap = float(spin_cap_sec)
        self.drift = float(drift_sec)

    def sleep_until(self, target_time):
        clock_drift = random.uniform(-self.drift, self.drift)
        target = target_time + clock_drift

        while True:
            now = time.perf_counter()
            rem = target - now
            if rem <= 0:
                break
            if rem > self.spin_cap:
                time.sleep(rem - self.spin_cap)

class ClickerChannel:
    def __init__(self, default_btn):
        self.active = False
        self.target_btn = default_btn
        self.next_tick = 0.0

        self.state = "cruising"
        self.state_end_time = 0.0
        self.current_variance = 0.0

        self.cps = 12.0
        self.jitter_enabled = False
        self.jitter_strength = 2.0
        self.human_lvl = 1

    def reset(self):
        self.next_tick = time.perf_counter()
        self.state = "cruising"
        self.state_end_time = time.perf_counter()
        self.current_variance = 0.0

    def get_next_delay(self):
        now = time.perf_counter()

        if now >= self.state_end_time:
            rand = random.random()

            if rand < 0.70:
                self.state = "cruising"
                self.state_end_time = now + random.uniform(0.4, 1.2)
                self.current_variance = random.uniform(-1.5, 1.5)
            elif rand < 0.85:
                self.state = "burst"
                self.state_end_time = now + random.uniform(0.2, 0.4)
                self.current_variance = random.uniform(4.0, 7.0)
            else:
                self.state = "tired"
                self.state_end_time = now + random.uniform(0.3, 0.6)
                self.current_variance = random.uniform(-6.0, -3.0)

        target_cps = self.cps + self.current_variance
        roughness = random.gauss(0, 1.5)
        final_cps = max(6.0, min(22.0, target_cps + roughness))
        return 1.0 / final_cps

class GhostEngine:
    def __init__(self):
        mouse_buttons = [e.BTN_LEFT, e.BTN_RIGHT, e.BTN_MIDDLE, e.BTN_SIDE, e.BTN_EXTRA]

        try:
            self.ui = UInput(
                {
                    e.EV_KEY: mouse_buttons,
                    e.EV_REL: [e.REL_X, e.REL_Y, e.REL_WHEEL],
                },
                name="Moonlight HID",
                vendor=0x1234,
                product=0x5678,
                version=0x1
            )
        except PermissionError:
            print("ROOT REQUIRED: run with sudo")
            sys.exit(1)

        self.left = ClickerChannel(e.BTN_LEFT)
        self.left.jitter_enabled = True
        self.right = ClickerChannel(e.BTN_RIGHT)

        self.paused = False
        self.drift_x = 0.0
        self.drift_y = 0.0
        self.sounds = ClickSoundPlayer()

    def cleanup(self):
        try:
            self.ui.write(e.EV_KEY, e.BTN_LEFT, 0)
            self.ui.write(e.EV_KEY, e.BTN_RIGHT, 0)
            self.ui.syn()
            self.ui.close()
        except Exception:
            pass

    def apply_jitter(self, strength, human_lvl):
        if strength <= 0:
            return
        if random.random() < 0.50:
            multiplier = 1.0 if human_lvl == 1 else 2.2
            intensity = strength * multiplier
            dx = random.gauss(0, intensity)
            dy = random.gauss(0, intensity)

            self.drift_x += random.uniform(-0.2, 0.2)
            self.drift_y += random.uniform(-0.2, 0.2)
            self.drift_x = max(-2.5, min(2.5, self.drift_x))
            self.drift_y = max(-2.5, min(2.5, self.drift_y))

            final_x = int(dx + self.drift_x)
            final_y = int(dy + self.drift_y)

            if final_x != 0 or final_y != 0:
                self.ui.write(e.EV_REL, e.REL_X, final_x)
                self.ui.write(e.EV_REL, e.REL_Y, final_y)

    def _apply_config(self, cfg):
        if 'cps_left' in cfg:
            self.left.cps = float(cfg['cps_left'])
        if 'cps_right' in cfg:
            self.right.cps = float(cfg['cps_right'])
        if 'jitter' in cfg:
            self.left.jitter_strength = float(cfg['jitter'])
        if 'rand' in cfg:
            self.left.human_lvl = int(cfg['rand'])
            self.right.human_lvl = int(cfg['rand'])

        sound_cfg = {}
        if 'click_sounds' in cfg:
            sound_cfg['enabled'] = bool(cfg['click_sounds'])
        if 'click_sound_volume' in cfg:
            sound_cfg['volume'] = float(cfg['click_sound_volume'])
        if 'click_sound_pack' in cfg:
            sound_cfg['pack'] = cfg['click_sound_pack']
        if sound_cfg:
            self.sounds.configure(**sound_cfg)

    def _click_button(self, btn):
        self.ui.write(e.EV_KEY, btn, 1)
        self.ui.syn()
        self.sounds.play()

    def _release_button(self, btn):
        self.ui.write(e.EV_KEY, btn, 0)
        self.ui.syn()

    def run(self, state_q, config_q):
        sleeper = HighResSleeper()

        try:
            while True:
                while not config_q.empty():
                    self._apply_config(config_q.get())

                while not state_q.empty():
                    msg = state_q.get()
                    if msg == "STOP":
                        return
                    if msg == "PAUSE":
                        self.paused = True
                    if msg == "RESUME":
                        self.paused = False

                    if msg == "ENABLE_LEFT":
                        if not self.left.active:
                            self.left.active = True
                            self.left.reset()
                            self.drift_x = 0.0
                            self.drift_y = 0.0
                    elif msg == "DISABLE_LEFT":
                        self.left.active = False

                    if msg == "ENABLE_RIGHT":
                        if not self.right.active:
                            self.right.active = True
                            self.right.reset()
                    elif msg == "DISABLE_RIGHT":
                        self.right.active = False

                if self.paused:
                    time.sleep(0.05)
                    continue

                now = time.perf_counter()
                if not self.left.active and not self.right.active:
                    time.sleep(0.01)
                    continue

                processed_something = False

                if self.left.active and now >= self.left.next_tick:
                    if self.left.jitter_enabled:
                        self.apply_jitter(self.left.jitter_strength, self.left.human_lvl)

                    self._click_button(self.left.target_btn)

                    hold = max(0.022, min(0.15, random.lognormvariate(-3.2, 0.25)))
                    full_delay = self.left.get_next_delay()
                    self.left.next_tick = now + full_delay

                    sleeper.sleep_until(now + hold)
                    self._release_button(self.left.target_btn)
                    processed_something = True

                now = time.perf_counter()
                if self.right.active and now >= self.right.next_tick:
                    self._click_button(self.right.target_btn)

                    hold = max(0.022, min(0.15, random.lognormvariate(-3.2, 0.25)))
                    full_delay = self.right.get_next_delay()
                    self.right.next_tick = now + full_delay

                    sleeper.sleep_until(now + hold)
                    self._release_button(self.right.target_btn)
                    processed_something = True

                if not processed_something:
                    next_event = 9999999999.0
                    if self.left.active:
                        next_event = min(next_event, self.left.next_tick)
                    if self.right.active:
                        next_event = min(next_event, self.right.next_tick)
                    rem = next_event - time.perf_counter()
                    if rem > 0.001:
                        time.sleep(min(rem, 0.05))

        except KeyboardInterrupt:
            pass
        except Exception as err:
            print(f"Engine Error: {err}")
        finally:
            self.cleanup()
