#!/usr/bin/env bash
# Шпаргалка: берёт описания из bindd в hyprland.conf
hyprctl binds -j | python3 -c '
import json, sys
mods = {64:"Super", 1:"Shift", 4:"Ctrl", 8:"Alt"}
keys = {"Return":"Enter", "slash":"/", "SUPER_L":"(Super)", "mouse_down":"Колесо"}
for b in json.load(sys.stdin):
    if not b.get("has_description"): continue
    m = " + ".join(n for bit, n in mods.items() if b["modmask"] & bit)
    k = keys.get(b["key"], b["key"])
    combo = f"{m} + {k}" if m else k
    d = b["description"]
    print(f"{combo:<24} {d}")
' | rofi -dmenu -i -p "󰌌 " -theme-str 'window {width: 640px;} listview {lines: 14;}' >/dev/null
