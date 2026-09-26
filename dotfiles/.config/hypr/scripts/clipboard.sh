#!/usr/bin/env bash
if ! command -v cliphist >/dev/null; then
    notify-send "Буфер обмена" "cliphist не установлен"; exit 1
fi
cliphist list | rofi -dmenu -p "󰅍 " -display-columns 2 | cliphist decode | wl-copy
