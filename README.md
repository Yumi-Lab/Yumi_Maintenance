# Yumi_Maintenance

Yumi_Maintenance provides scripts and configuration files to easily enable or disable a maintenance mode for Klipper and KlipperScreen.

When maintenance mode is enabled, a [yumi_maintenance] section is automatically inserted into your printer.cfg to activate specific maintenance features.
When disabled, the section is removed — no manual editing needed.

<a href="https://github.com/Yumi-Lab/Yumi_Maintenance/blob/main/img_readme/">
    <img src="https://github.com/Yumi-Lab/Yumi_Maintenance/blob/main/img_readme/screen_maintenance-example.png?raw=true" alt="Translation status" />
</a>

---

# Features
- Automatic config management — no need to manually edit printer.cfg
- Systemd timer service — checks every 10 minutes for maintenance mode changes
- Custom scripts for Klipper and KlipperScreen integration
- Optional icons/images for a dedicated maintenance theme
- Safe file handling — preserves your existing printer configuration

---

# Requirements
- Raspberry Pi running Klipper + KlipperScreen
- git and python3 installed
- Access to /home/pi user directory
- systemd available for service/timer setup

---

# Installation
Clone the repository and run the installer:

```bash
git clone https://github.com/Yumi-Lab/Yumi_Maintenance.git
cd Yumi_Maintenance/install
./install.sh
```

## The installer will:
- Copy prompts.py into the KlipperScreen widgets folder
- Copy yumi_maintenance.py into the Klipper extras folder
- Install Yumi_Maintenance.cfg into your Klipper config folder
- Copy PNG images to the KlipperScreen maintenance style folder and set permissions
- Install and enable the yumi_maintenance systemd service and timer

---

# Configuration
Edit /home/pi/printer_data/config/Yumi_Maintenance.cfg:

enable_maintenance=True

- True → Adds [yumi_maintenance] to printer.cfg
- False → Removes [yumi_maintenance] from printer.cfg

---

# How It Works
1. Every 10 minutes, the systemd timer runs check_maintenance.py
2. The script reads enable_maintenance in Yumi_Maintenance.cfg
3. If True:
   - Checks if [yumi_maintenance] exists in printer.cfg
   - If not, inserts it after the line:
     filename: ~/printer_data/config/variables.cfg
4. If False:
   - Checks if [yumi_maintenance] exists in printer.cfg
   - If yes, removes that line

---

# Uninstallation

```bash
sudo systemctl disable --now yumi_maintenance.timer
sudo rm /etc/systemd/system/yumi_maintenance.service
sudo rm /etc/systemd/system/yumi_maintenance.timer
sudo systemctl daemon-reload

rm -f /home/pi/KlipperScreen/ks_includes/widgets/prompts.py
rm -f /home/pi/klipper/klippy/extras/yumi_maintenance.py
rm -f /home/pi/printer_data/config/Yumi_Maintenance.cfg
rm -rf /home/pi/KlipperScreen/styles/maintenance/
rm -rf /home/pi/Yumi_Maintenance
```

If [yumi_maintenance] is still present in your printer.cfg and you want it removed, delete the line manually or set enable_maintenance=False before uninstalling.

---

Notes
- [yumi_maintenance] section content can be customized for your printer’s hardware pins
- Works with any Klipper-based setup where the header format in printer.cfg remains consistent
- Backup your printer.cfg before installation
- Use caution — modifies config files

---

# License
MIT License



