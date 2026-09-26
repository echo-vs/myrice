#!/usr/bin/env bash
# area | screen | edit
dir="$HOME/Pictures/Screenshots"; mkdir -p "$dir"
file="$dir/$(date +%Y-%m-%d_%H-%M-%S).png"
case "$1" in
    area)   geom=$(slurp -b 18161688 -c c4b28aff -w 2) || exit 0; grim -g "$geom" "$file" ;;
    screen) grim "$file" ;;
    edit)   geom=$(slurp -b 18161688 -c c4b28aff -w 2) || exit 0; grim -g "$geom" - | swappy -f - ; exit 0 ;;
esac
wl-copy < "$file"
notify-send -a Скриншот -i "$file" "Скриншот скопирован" "$(basename "$file")"
