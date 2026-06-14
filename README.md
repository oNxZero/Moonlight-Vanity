# Moonlight-Vanity

> **A stripped-down, kernel-level auto clicker for Linux — left and right click only.**

![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg)
![License](https://img.shields.io/badge/License-MIT-green.svg)
![Platform](https://img.shields.io/badge/Platform-Linux%20(Wayland%20%7C%20X11)-lightgrey)

**Moonlight-Vanity** is a fork of [Moonlight](https://github.com/oNxZero/Moonlight) built for simple mouse auto-clicking. It keeps the same kernel-level input engine, humanized timing, and clean UI — but removes PvP assist features entirely.

This build supports **left click** and **right click** only. W-Tap, S-Tap, and Blockhit are disabled in both the UI and backend, so they cannot be enabled or used.

It should work out of the box on both Wayland (Hyprland, GNOME, KDE) and X11.

---

## Demo

<p align="center">
  <img src="./assets/demo.gif" alt="Moonlight-Vanity UI Demo" width="600">
</p>

---

## Features

* **Kernel-Level Input:** Creates a virtual device via `/dev/uinput`. To the OS and games, it looks like a real physical mouse.
* **Left & Right Click:** Dedicated triggers, CPS sliders, and toggle/hold modes for both mouse buttons.
* **Process Cloaking:** The background daemon renames itself to `kworker/u12:0` so it blends into `htop` and task managers.
* **Biological Timing:** Gaussian timing with cruising, burst, and tired states to mimic human click patterns.
* **Asynchronous Architecture:** The click engine runs in a separate process from the UI, so the click rate never stutters when you move the window.

### What is disabled

The **ASSIST** panel (W-Tap and Blockhit) is grayed out and hard-disabled. This is intentional — Vanity is meant to stay a plain auto clicker.

---

## Installation

```bash
# Clone this repository
git clone https://github.com/oNxZero/Moonlight-Vanity.git

# Enter the directory
cd Moonlight-Vanity

# Make the installer executable
chmod +x install.sh

# Run the universal installer and wait for it to finish
./install.sh
```

**Note:** You must **log out** after installing. The script creates a hardware permission rule so you do not need to run the app as root.

---

## Uninstallation

```bash
cd Moonlight-Vanity
chmod +x uninstall.sh
./uninstall.sh
cd ..
```

---

## Usage

Once installed, search for **Moonlight** in your application menu.

### Dashboard

* **Master Switch:** Global safety toggle. Must be **ON** for any clicks to register.
* **Target Mode:**
    * **Mouse:** Auto-click left and right mouse buttons.
    * **Keyboard:** Spam a specific key (e.g. `Space`, `F`) instead of clicking.
* **Trigger Mode:**
    * **Toggle:** Press once to start, again to stop.
    * **Hold:** Clicks only while the key is held down.
* **Humanization:**
    * **Legit:** Realistic jitter and timing drift.
    * **Blatant:** Strict timing with minimal variance.

---

## Keybinds

Rebind these in the app by clicking the button and pressing a new key.

| Key | Action | Description |
| :--- | :--- | :--- |
| **F6** | Left Click | Toggles the left mouse clicker. |
| **F7** | Right Click | Toggles the right mouse clicker. |
| **R-Shift** | Panic Mode | Instantly hides or shows the window. |

---

## Configuration

Presets and themes are managed from the in-app settings menu.

### Presets

* **Create:** Save your current settings as a new preset.
* **Load:** Apply a saved preset to your session.
* **Update:** Overwrite an existing preset with current settings.

### Themes

Choose a built-in theme or override individual colors from the settings panel.

### File location

Config and presets are stored in:

`~/.config/Moonlight/`

---

## Upstream

Based on [oNxZero/Moonlight](https://github.com/oNxZero/Moonlight). Moonlight-Vanity tracks that project but keeps assist features permanently off.

---

## License

Distributed under the MIT License. See [LICENSE](LICENSE) for more information.
