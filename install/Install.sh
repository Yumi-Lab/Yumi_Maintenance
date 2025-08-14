#!/bin/bash
set -e

echo "[Yumi_Maintenance] Installation..."

# Chemins de destination
KS_WIDGETS="/home/pi/KlipperScreen/ks_includes/widgets"
KLIPPER_EXTRAS="/home/pi/klipper/klippy/extras"
CONFIG_DIR="/home/pi/printer_data/config"
MAINTENANCE_STYLE="/home/pi/KlipperScreen/styles/maintenance"

# Copier prompts.py
install -Dm644 ../scripts/prompts.py "$KS_WIDGETS/prompts.py"

# Copier yumi_maintenance.py
install -Dm644 ../scripts/yumi_maintenance.py "$KLIPPER_EXTRAS/yumi_maintenance.py"

# Copier config Yumi_Maintenance.cfg si absent
if [ ! -f "$CONFIG_DIR/Yumi_Maintenance.cfg" ]; then
    install -Dm644 ../config/Yumi_Maintenance.cfg "$CONFIG_DIR/Yumi_Maintenance.cfg"
fi

# Copier images
mkdir -p "$MAINTENANCE_STYLE"
cp ../img/*.png "$MAINTENANCE_STYLE/"

# Permissions sécurisées
chmod 755 "$MAINTENANCE_STYLE"
chmod 644 "$MAINTENANCE_STYLE"/*.png
chown -R pi:pi "$MAINTENANCE_STYLE"

# Copier script check_maintenance.py
install -Dm755 ../scripts/check_maintenance.py /home/pi/Yumi_Maintenance/scripts/check_maintenance.py

# Installer service et timer
sudo install -Dm644 ../service/yumi_maintenance.service /etc/systemd/system/yumi_maintenance.service
sudo install -Dm644 ../service/yumi_maintenance.timer /etc/systemd/system/yumi_maintenance.timer

# Activer le timer
sudo systemctl daemon-reload
sudo systemctl enable --now yumi_maintenance.timer

echo "[Yumi_Maintenance] Installation terminée."
