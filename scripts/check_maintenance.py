#!/usr/bin/env python3
import os

CFG_PATH = "/home/pi/printer_data/config/Yumi_Maintenance.cfg"
PRINTER_CFG = "/home/pi/printer_data/config/printer.cfg"
MARKER = "[yumi_maintenance]"
INSERT_AFTER = "filename: ~/printer_data/config/variables.cfg"

def read_enable_flag():
    if not os.path.exists(CFG_PATH):
        return False
    with open(CFG_PATH, "r") as f:
        for line in f:
            if line.strip().startswith("enable_maintenance"):
                return line.strip().split("=")[1].strip().lower() == "true"
    return False

def printer_cfg_contains_marker():
    if not os.path.exists(PRINTER_CFG):
        return False
    with open(PRINTER_CFG, "r") as f:
        return MARKER in f.read()

def add_marker():
    lines = []
    with open(PRINTER_CFG, "r") as f:
        lines = f.readlines()
    new_lines = []
    inserted = False
    for line in lines:
        new_lines.append(line)
        if INSERT_AFTER in line and not inserted:
            new_lines.append(MARKER + "\n")
            inserted = True
    if inserted:
        with open(PRINTER_CFG, "w") as f:
            f.writelines(new_lines)

def remove_marker():
    with open(PRINTER_CFG, "r") as f:
        lines = f.readlines()
    new_lines = [l for l in lines if MARKER not in l]
    with open(PRINTER_CFG, "w") as f:
        f.writelines(new_lines)

def main():
    enable = read_enable_flag()
    has_marker = printer_cfg_contains_marker()
    if enable and not has_marker:
        add_marker()
    elif not enable and has_marker:
        remove_marker()

if __name__ == "__main__":
    main()
