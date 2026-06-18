# 🌙 Moonlight-Vanity

> **A stripped-down, kernel-level auto clicker for Linux — left and right click only.**

![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg)
![License](https://img.shields.io/badge/License-MIT-green.svg)
![Platform](https://img.shields.io/badge/Platform-Linux%20(Wayland%20%7C%20X11)-lightgrey)

**Moonlight-Vanity** is a fork of [Moonlight](https://github.com/oNxZero/Moonlight) built for simple mouse auto-clicking. It keeps the same kernel-level input engine, humanized timing, and clean UI — but strips out keyboard mode, W-Tap, and Blockhit entirely.

It **should** work out of the box on both Wayland (Hyprland, GNOME, KDE) and X11. It also features built-in **click sounds** with swappable mouse sound packs.

---

## 📸 Demo

<p align="center">
  <img src="./assets/demo.gif" alt="Moonlight-Vanity UI Demo" width="600">
</p>

---

## 🔥 Features

* **Kernel-Level Input:** Instead of sending software signals, Moonlight-Vanity creates a virtual device in `/dev/uinput`. To the OS and games, it looks identical to a real physical mouse.
* **Left & Right Click:** Dedicated triggers, CPS sliders, and toggle/hold modes for both mouse buttons.
* **Click Sounds:** Plays a mouse click sound on every auto-click. Choose from multiple sound packs and adjust volume in the UI.
* **Process Cloaking:** The background daemon actively renames itself to `kworker/u12:0` (a common kernel thread) so it blends into `htop` and task managers.
* **Biological Timing:** It doesn't just use random numbers. The engine cycles through "cruising", "burst", and "tired" states using Gaussian distribution to mimic actual human muscle fatigue and reaction speeds.
* **Asynchronous Architecture:** The click engine runs in a completely separate process from the UI. You can drag the window around or minimize it, and the click rate will never stutter.

---

## 🚀 Installation

Moonlight-Vanity comes with a smart installer that handles system dependencies, creates the necessary permissions, and adds the app to your desktop menu.

```bash
# Clone the repository
git clone https://github.com/oNxZero/Moonlight-Vanity.git

# Enter the directory
cd Moonlight-Vanity

# Make the installer executable
chmod +x install.sh

# Run the universal installer and wait for it to finish
./install.sh
```

**Note:** You must **Log Out** after installing. The script creates a new hardware permission rule so you don't have to run the app as root.

---

## 🗑️ Uninstallation

If you want to remove Moonlight-Vanity, the included script will remove the desktop shortcut, config files, and system permissions for you.

```bash
# Enter the directory (if not already there)
cd Moonlight-Vanity

# Make the uninstaller executable
chmod +x uninstall.sh

# Run the uninstaller
./uninstall.sh

# Finally, leave the deleted directory
cd ..
```

---

## 📖 Usage

Once installed, simply search for **Moonlight** in your application menu.

### 🟢 The Dashboard
The interface is split into simple controls:

* **Master Switch:** The global safety. This must be **ON** for any clicks to register.
* **Trigger Mode:**
    * **Toggle:** Press key to start clicking, press again to stop.
    * **Hold:** Clicks only while you physically hold the key down.
* **Humanization:**
    * **Legit:** Adds realistic jitter and timing drift (recommended for gaming).
    * **Blatant:** Strict timing with little variance (maximum efficiency).
* **Click Sounds:**
    * **Toggle:** Enable or disable click sounds.
    * **Sound Pack:** Pick a mouse sound profile from the dropdown.
    * **Volume:** Adjust how loud the click sounds play.

---

## 🔊 Sound Packs

Sound packs live in the `./sounds/` directory. Each pack is a folder containing a `click.wav` or `click.mp3` file.

To add your own pack:

```bash
mkdir -p sounds/MyCustomPack
cp /path/to/your/click.wav sounds/MyCustomPack/click.wav
```

Restart the app and your new pack will appear in the dropdown.

Bundled mouse sounds are sourced from [Keyboard Sounds Pro](https://github.com/keyboard-sounds/keyboardsounds-pro) (MIT License). See `sounds/ATTRIBUTION.md` for details.

---

## ⌨️ Keybinds
You can rebind these directly in the app by clicking the button and pressing a new key.

| Key | Action | Description |
| :--- | :--- | :--- |
| **[F6]** | **Left Click** | Toggles the left mouse clicker. |
| **[F7]** | **Right Click** | Toggles the right mouse clicker. |
| **[R-Shift]** | **Panic Mode** | Instantly hides or shows the window. |

---

## ⚙️ Configuration & Customization

The settings menu allows you to manage profiles and themes without editing files.

### 📁 Presets
Presets are **snapshots** of your configuration.
* **Create:** Type a name and click "Create" to save your current settings as a new preset.
* **Load:** Click the **Play** button (▶) to apply a preset's settings to your current session.
* **Update:** Click the **Save** button (💾) to overwrite an existing preset with your current settings.
* **Note:** The app remembers your *current* active settings automatically on exit, but Presets must be updated manually.

### 🎨 Themes
* **Gallery:** Click any theme name (like **Dracula** or **Obsidian**) to instantly apply that color scheme.
* **Overrides:** Use the color pickers to change specific elements like the Accent color or Background.

### 🔧 File Location
All configurations and presets are stored in:
`~/.config/Moonlight/`

---

## 📜 License

Distributed under the MIT License. See `LICENSE` for more information.
