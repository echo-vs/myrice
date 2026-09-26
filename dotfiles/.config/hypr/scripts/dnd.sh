#!/usr/bin/env bash
# Режим «не беспокоить» для mako + статус для waybar
if [ "$1" = toggle ]; then
    makoctl mode -t do-not-disturb >/dev/null
    pkill -RTMIN+8 waybar
    exit 0
fi
if makoctl mode 2>/dev/null | grep -q do-not-disturb; then
    echo '{"text":"󰂛","tooltip":"Не беспокоить: вкл","class":"dnd"}'
else
    echo '{"text":"󰂚","tooltip":"Уведомления включены","class":"normal"}'
fi
