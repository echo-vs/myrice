#!/usr/bin/env bash
# Обои: Super + W — выбор из ~/Pictures/wallpapers
#   wallpaper.sh <файл>  — поставить конкретную картинку
#   wallpaper.sh restore — вернуть последние (автозапуск)
dir=~/Pictures/wallpapers
state=~/.cache/wallpaper
default=$dir/tea-house.png
cache=~/.cache/wallpapers

# swaybg собран без gdk-pixbuf и читает только PNG — остальное конвертим в кеш
to_png() {
    local src png
    src=$(realpath "$1")
    case "${src,,}" in *.png) echo "$src"; return ;; esac
    png=$cache/$(basename "${src%.*}").png
    if [ ! -s "$png" ] || [ "$src" -nt "$png" ]; then
        mkdir -p "$cache"
        ffmpeg -loglevel error -y -i "$src" -frames:v 1 "$png" || return 1
    fi
    echo "$png"
}

set_wall() {
    local old img pid
    img=$(to_png "$1") || { notify-send "Обои" "Не удалось открыть: $1"; return 1; }
    old=$(pgrep -x swaybg)
    swaybg -m fill -i "$img" >/dev/null 2>&1 & pid=$!
    disown
    # старый swaybg гасим после запуска нового, чтобы не мигало
    sleep 0.3
    kill -0 "$pid" 2>/dev/null || { notify-send "Обои" "swaybg не смог загрузить: $1"; return 1; }
    [ -n "$old" ] && kill $old
    ln -sf "$(realpath "$1")" "$state"
}

case "$1" in
    restore)
        [ -e "$state" ] && set_wall "$state" || set_wall "$default" ;;
    "")
        current=$(readlink "$state")
        choice=$(find "$dir" -maxdepth 1 -type f \
                    \( -iname '*.png' -o -iname '*.jpg' -o -iname '*.jpeg' -o -iname '*.webp' \) \
                    -printf '%f\n' | sort |
            while read -r f; do
                printf '%s\0icon\x1f%s\n' "$f" "$dir/$f"
            done |
            rofi -dmenu -i -show-icons -p "󰸉 " \
                -select "$(basename "$current")" \
                -theme-str 'window {width: 720px;} listview {lines: 6;} element-icon {size: 96px;}')
        [ -n "$choice" ] && set_wall "$dir/$choice" ;;
    *)
        [ -f "$1" ] || { notify-send "Обои" "Нет такого файла: $1"; exit 1; }
        set_wall "$1" ;;
esac
