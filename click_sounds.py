import os
import threading

SOUNDS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sounds")


def list_sound_packs():
    packs = []
    if not os.path.isdir(SOUNDS_DIR):
        return ["Default"]

    if os.path.isfile(os.path.join(SOUNDS_DIR, "click.mp3")):
        packs.append("Default")

    for name in sorted(os.listdir(SOUNDS_DIR)):
        pack_dir = os.path.join(SOUNDS_DIR, name)
        if os.path.isdir(pack_dir) and os.path.isfile(os.path.join(pack_dir, "click.mp3")):
            packs.append(name)

    return packs or ["Default"]


def resolve_sound_path(pack_name):
    if pack_name == "Default":
        path = os.path.join(SOUNDS_DIR, "click.mp3")
    else:
        path = os.path.join(SOUNDS_DIR, pack_name, "click.mp3")

    if os.path.isfile(path):
        return path

    fallback = os.path.join(SOUNDS_DIR, "click.mp3")
    if os.path.isfile(fallback):
        return fallback

    for name in os.listdir(SOUNDS_DIR) if os.path.isdir(SOUNDS_DIR) else []:
        candidate = os.path.join(SOUNDS_DIR, name, "click.mp3")
        if os.path.isfile(candidate):
            return candidate

    return None


class ClickSoundPlayer:
    def __init__(self):
        self.enabled = True
        self.volume = 0.8
        self.pack = list_sound_packs()[0]
        self._sound = None
        self._loaded_pack = None
        self._lock = threading.Lock()
        self._ready = False
        self._init_mixer()

    def _init_mixer(self):
        try:
            import pygame
            pygame.mixer.pre_init(frequency=44100, size=-16, channels=2, buffer=256)
            pygame.mixer.init()
            pygame.mixer.set_num_channels(48)
            self._ready = True
        except Exception as err:
            print(f"Click sounds unavailable: {err}")

    def _load(self):
        if not self._ready:
            return

        if self._loaded_pack == self.pack and self._sound is not None:
            return

        path = resolve_sound_path(self.pack)
        if not path:
            self._sound = None
            self._loaded_pack = None
            return

        try:
            import pygame
            self._sound = pygame.mixer.Sound(path)
            self._sound.set_volume(self.volume)
            self._loaded_pack = self.pack
        except Exception as err:
            print(f"Failed to load click sound '{self.pack}': {err}")
            self._sound = None
            self._loaded_pack = None

    def configure(self, enabled=None, volume=None, pack=None):
        with self._lock:
            if enabled is not None:
                self.enabled = bool(enabled)
            if volume is not None:
                self.volume = max(0.0, min(1.0, float(volume) / 100.0))
                if self._sound is not None:
                    self._sound.set_volume(self.volume)
            if pack is not None and pack != self.pack:
                self.pack = pack
                self._loaded_pack = None
            self._load()

    def play(self):
        if not self.enabled or not self._ready:
            return

        with self._lock:
            if self._sound is None:
                self._load()
            if self._sound is None:
                return
            try:
                self._sound.play()
            except Exception:
                pass
