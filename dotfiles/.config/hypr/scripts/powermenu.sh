#!/usr/bin/env bash
choice=$(printf '%s\n' \
    "󰌾  Заблокировать" \
    "󰤄  Сон" \
    "󰍃  Выйти" \
    "󰜉  Перезагрузка" \
    "󰐥  Выключение" \
  | rofi -dmenu -i -p "" -theme-str 'window {width: 300px;} listview {lines: 5;} inputbar {enabled: false;}')
case "$choice" in
    *Заблокировать) loginctl lock-session ;;
    *Сон)           loginctl suspend ;;
    *Выйти)         hyprctl dispatch exit ;;
    *Перезагрузка)  loginctl reboot ;;
    *Выключение)    loginctl poweroff ;;
esac
