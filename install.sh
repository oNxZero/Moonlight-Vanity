#!/bin/bash
set -e

GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

if [ "${EUID:-$(id -u)}" -eq 0 ]; then
    echo -e "${RED}Error: Do NOT run this script as root.${NC}"
    echo "It installs files into your home directory."
    exit 1
fi

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
TARGET_DIR="$HOME/Moonlight"

echo -e "${BLUE}=========================================${NC}"
echo -e "${BLUE}       Moonlight Setup Assistant         ${NC}"
echo -e "${BLUE}=========================================${NC}"

if [ "${1:-}" != "--no-copy" ] && [ "$SCRIPT_DIR" != "$TARGET_DIR" ]; then
    echo -e "${YELLOW}Installing to $TARGET_DIR...${NC}"
    mkdir -p "$TARGET_DIR"
    cp -a "$SCRIPT_DIR"/. "$TARGET_DIR"/
    chmod +x "$TARGET_DIR/install.sh"
    cd "$TARGET_DIR"
    exec ./install.sh --no-copy
fi

echo -e "${GREEN}Cleaning up repository artifacts...${NC}"

rm -rf "$TARGET_DIR/.git"        2>/dev/null || true
rm -rf "$TARGET_DIR/assets"      2>/dev/null || true
rm -f  "$TARGET_DIR/README.md"   2>/dev/null || true
rm -f  "$TARGET_DIR/LICENSE"     2>/dev/null || true

echo -e "${GREEN}[1/5] Installing system dependencies...${NC}"

if command -v dnf >/dev/null; then
    sudo dnf install -y \
        python3-pip python3-gobject gtk4 libadwaita \
        python3-devel gcc pkgconf-pkg-config gobject-introspection-devel
elif command -v apt-get >/dev/null; then
    sudo apt-get update
    sudo apt-get install -y \
        python3-pip python3-gi gir1.2-gtk-4.0 gir1.2-adw-1 \
        python3-dev gcc pkg-config gobject-introspection
elif command -v pacman >/dev/null; then
    sudo pacman -S --noconfirm \
        python-pip python-gobject gtk4 libadwaita \
        python gcc make pkgconf gobject-introspection
else
    echo -e "${RED}Unsupported distro.${NC}"
    exit 1
fi

echo -e "${GREEN}[2/5] Installing Python dependencies...${NC}"
python3 -m pip install --user -r requirements.txt

rm -f "$TARGET_DIR/requirements.txt" 2>/dev/null || true

echo -e "${GREEN}[3/5] Configuring input permissions...${NC}"
sudo groupadd -f input
sudo usermod -aG input "$USER"

sudo tee /etc/udev/rules.d/99-moonlight.rules >/dev/null <<EOF
SUBSYSTEM=="misc", KERNEL=="uinput", GROUP="input", MODE="0660", OPTIONS+="static_node=uinput"
SUBSYSTEM=="input", KERNEL=="event*", GROUP="input", MODE="0660"
EOF

sudo udevadm control --reload-rules
sudo udevadm trigger

echo -e "${GREEN}[4/5] Preparing launcher...${NC}"

cat > start.sh <<EOF
#!/bin/bash
cd "$TARGET_DIR"
exec /usr/bin/python3 main.py
EOF
chmod +x start.sh

echo -e "${GREEN}[5/5] Registering application...${NC}"
APP_DIR="$HOME/.local/share/applications"
mkdir -p "$APP_DIR"

cat > "$APP_DIR/Moonlight.desktop" <<EOF
[Desktop Entry]
Name=Moonlight
Comment=Auto Clicker
Exec=$TARGET_DIR/start.sh
Icon=$TARGET_DIR/icon.svg
Terminal=false
Type=Application
Categories=Utility;Accessibility;
StartupNotify=true
EOF

chmod +x "$APP_DIR/Moonlight.desktop"
command -v update-desktop-database >/dev/null && update-desktop-database "$APP_DIR" || true

echo -e "${GREEN}INSTALLATION COMPLETE${NC}"
echo "Log out and log back in to apply input permissions."
