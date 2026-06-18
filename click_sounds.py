import os
import threading

SOUNDS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sounds")

CLICK_CANDIDATES = (
    "click.wav",
    "click.mp3",
    "left-down.wav",
    "left-down.mp3",
    "primary_down.wav",
    "primary_down.mp3",
)


def _find_click_file(directory):
    for name in CLICK_CANDIDATES:
        path = os.path.join(directory, name)
        if os.path.isfile(path):
            return path
    return None


def list_sound_packs():
    packs = []
    if not os.path.isdir(SOUNDS_DIR):
        return ["Default"]

    if _find_click_file(SOUNDS_DIR):
        packs.append("Default")

    for name in sorted(os.listdir(SOUNDS_DIR)):
        pack_dir = os.path.join(SOUNDS_DIR, name)
        if os.path.isdir(pack_dir) and _find_click_file(pack_dir):
            packs.append(name)

    return packs or ["Default"]


def resolve_sound_path(pack_name):
    if pack_name == "Default":
        return _find_click_file(SOUNDS_DIR)

    return _find_click_file(os.path.join(SOUNDS_DIR, pack_name))


class ClickSoundPlayer:
    def __init__(self):
        self.enabled = True
        self.volume = 0.8
        self.pack = list_sound_packs()[0]
        self._sound = None
        self._loaded_path = None
        self._lock = threading.Lock()
        self._ready = False
        self._init_mixer()

    def _init_mixer(self):
        try:
            import pygame
            if not pygame.mixer.get_init():
                pygame.mixer.pre_init(frequency=44100, size=-16, channels=2, buffer=256)
                pygame.mixer.init()
            pygame.mixer.set_num_channels(48)
            self._ready = True
        except Exception as err:
            print(f"Click sounds unavailable: {err}")

    def _load(self):
        if not self._ready:
            return

        path = resolve_sound_path(self.pack)
        if not path:
            self._sound = None
            self._loaded_path = None
            return

        if path == self._loaded_path and self._sound is not None:
            self._sound.set_volume(self.volume)
            return

        try:
            import pygame
            self._sound = pygame.mixer.Sound(path)
            self._sound.set_volume(self.volume)
            self._loaded_path = path
        except Exception as err:
            print(f"Failed to load click sound '{self.pack}' from '{path}': {err}")
            self._sound = None
            self._loaded_path = None

    def configure(self, enabled=None, volume=None, pack=None):
        with self._lock:
            if enabled is not None:
                self.enabled = bool(enabled)
            if volume is not None:
                self.volume = max(0.0, min(1.0, float(volume) / 100.0))
            if pack is not None:
                self.pack = pack
                self._sound = None
                self._loaded_path = None
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
