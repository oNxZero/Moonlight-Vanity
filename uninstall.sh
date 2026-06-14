#!/bin/bash

GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

TARGET_DIR="$HOME/Moonlight"
CONFIG_DIR="$HOME/.config/Moonlight"
DESKTOP_FILE="$HOME/.local/share/applications/Moonlight.desktop"
ICON_FILE="$HOME/.local/share/icons/hicolor/scalable/apps/com.moonlight.final.svg"
RULE_FILE="/etc/udev/rules.d/99-moonlight.rules"

echo -e "${BLUE}=========================================${NC}"
echo -e "${BLUE}       Moonlight Uninstaller             ${NC}"
echo -e "${BLUE}=========================================${NC}"

echo -e "${GREEN}[1/5] Removing Desktop Shortcut...${NC}"
if [ -f "$DESKTOP_FILE" ]; then
    rm -f "$DESKTOP_FILE"
    echo "Removed Moonlight.desktop"
else
    echo -e "${YELLOW}No desktop entry found (Skipping).${NC}"
fi

echo -e "${GREEN}[2/5] Removing App Icon...${NC}"
if [ -f "$ICON_FILE" ]; then
    rm -f "$ICON_FILE"
    echo "Removed com.moonlight.final.svg"
    if command -v gtk4-update-icon-cache >/dev/null; then
        gtk4-update-icon-cache -f -t "$HOME/.local/share/icons/hicolor/"
    fi
else
    echo -e "${YELLOW}No icon found (Skipping).${NC}"
fi

echo -e "${GREEN}[3/5] Removing System Permissions...${NC}"
if [ -f "$RULE_FILE" ]; then
    echo -e "${YELLOW}Admin access required to remove udev rules.${NC}"
    if sudo rm -f "$RULE_FILE"; then
        sudo udevadm control --reload-rules
        sudo udevadm trigger
        echo "udev rules removed and reloaded."
    else
        echo -e "${RED}Failed to remove udev rules. Manual removal may be required.${NC}"
    fi
else
    echo -e "${YELLOW}No udev rules found (Skipping).${NC}"
fi

echo -e "${GREEN}[4/5] Removing Installation Files...${NC}"
if [ -d "$TARGET_DIR" ]; then
    rm -rf "$TARGET_DIR"
    echo "Removed $TARGET_DIR"
else
    echo -e "${YELLOW}Install directory not found (Skipping).${NC}"
fi

echo -e "${GREEN}[5/5] Removing Configuration...${NC}"
if [ -d "$CONFIG_DIR" ]; then
    rm -rf "$CONFIG_DIR"
    echo "Removed $CONFIG_DIR"
else
    echo -e "${YELLOW}Config directory not found (Skipping).${NC}"
fi

echo -e "${GREEN}[Final] Final Notes...${NC}"
echo "Your user remains in the 'input' group."
echo "If you added it only for Moonlight and want to remove it manually:"
echo "  sudo gpasswd -d $USER input"
echo "Then log out and log back in."

echo -e "${BLUE}=========================================${NC}"
echo -e "${GREEN}        UNINSTALLATION COMPLETE          ${NC}"
echo -e "${BLUE}=========================================${NC}"
