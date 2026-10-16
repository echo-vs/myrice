#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────
#  hyprEcho · установщик райса (Hyprland + waybar + rofi + kitty + mako
#  + настройщики rice.py / gui.py)
#
#  ./install.sh                 интерактивная установка (меню компонентов)
#  ./install.sh -y              всё по умолчанию, без вопросов
#  ./install.sh --link          симлинки на репозиторий вместо копий
#  ./install.sh --theme ID      какую тему применить (hyprecho, x11-classic)
#  ./install.sh --only a,b      только эти компоненты (packages,configs,assets,plugin,extras,apply)
#  ./install.sh --skip a,b      всё, кроме этих
#  ./install.sh --dry-run       показать, что будет сделано, ничего не трогая
#
#  ./install.sh collect         забрать текущие конфиги из $HOME в репозиторий
#  ./install.sh restore [DATE]  вернуть конфиги из бэкапа (по умолчанию последний)
#  ./install.sh doctor          проверить, всё ли на месте
#  ./install.sh uninstall       убрать райс и вернуть последний бэкап
# ─────────────────────────────────────────────────────────────
set -euo pipefail

REPO=$(cd "$(dirname "$(realpath "${BASH_SOURCE[0]}")")" && pwd)
DOT=$REPO/dotfiles
DATA=${XDG_DATA_HOME:-$HOME/.local/share}/hyprecho
BACKUPS=$DATA/backups
STAMP=$(date +%Y%m%d-%H%M%S)
LOG=$DATA/install-$STAMP.log

CONFIG_DIRS=(hypr waybar rofi kitty mako swappy fastfetch cava)
HOME_ITEMS=(Pictures/wallpapers .icons/Nordic-cursors)
EXCLUDES=('rice/backup-*' '__pycache__' '*.pyc' '*.save' '*.bak' '*.bak-*' '*.tmp')

COMP_IDS=(packages configs assets plugin extras apply)
COMP_NAMES=(
    "Пакеты         Hyprland, waybar, rofi, kitty, mako, шрифты, GTK4 для GUI"
    "Конфиги        окна, бинды, бар, терминал, уведомления, настройщик Super+I"
    "Оформление     обои, курсоры Nordic, тёмная GTK-тема"
    "hyprbars       плагин заголовков окон (нужен для темы X11 Classic)"
    "Ярлыки         «Настройки райса» в лаунчере, команда rice в ~/.local/bin"
    "Применить      сгенерировать цвета/бар/rofi под выбранную тему"
)
COMP_ON=(1 1 1 1 1 1)

YES=0 DRY=0 LINK=0 THEME=""

# ── вид ──────────────────────────────────────────────────────
if [[ -t 1 ]]; then
    R=$'\e[0m' B=$'\e[1m' D=$'\e[2m'
    TEA=$'\e[38;2;216;166;87m' AMB=$'\e[38;2;231;138;78m' SAGE=$'\e[38;2;169;182;101m'
    CLAY=$'\e[38;2;234;105;98m' MIST=$'\e[38;2;125;174;163m' FG=$'\e[38;2;212;190;152m'
else
    R= B= D= TEA= AMB= SAGE= CLAY= MIST= FG=
fi

banner() {
    printf '%s' "$TEA"
    cat <<'EOF'

        ( (        _____              _   _
         ) )      |_   _|__  __ _    | | | | ___  _   _ ___  ___
      .______.      | |/ _ \/ _` |   | |_| |/ _ \| | | / __|/ _ \
      |      |]     | |  __/ (_| |   |  _  | (_) | |_| \__ \  __/
      \      /      |_|\___|\__,_|   |_| |_|\___/ \__,_|___/\___|
       `----'
EOF
    printf '%s      Hyprland rice · 茶 · установщик%s\n\n' "$D$FG" "$R"
}

STEP=0 STEPS=0
step()  { STEP=$((STEP + 1)); printf '\n%s%s[%d/%d]%s %s%s%s\n' "$B" "$AMB" "$STEP" "$STEPS" "$R" "$B$FG" "$*" "$R"; }
info()  { printf '  %s•%s %s\n' "$MIST" "$R" "$*"; }
ok()    { printf '  %s✓%s %s\n' "$SAGE" "$R" "$*"; }
warn()  { printf '  %s!%s %s\n' "$TEA" "$R" "$*"; }
err()   { printf '  %s✗%s %s\n' "$CLAY" "$R" "$*" >&2; }
die()   { err "$*"; exit 1; }
have()  { command -v "$1" >/dev/null 2>&1; }

ask() {  # ask "Вопрос" [y|n] → 0 = да
    local def=${2:-y} a hint
    [[ $def == y ]] && hint="[Y/n]" || hint="[y/N]"
    if ((YES)) || [[ ! -t 0 ]]; then [[ $def == y ]]; return; fi
    printf '  %s?%s %s %s%s%s ' "$TEA" "$R" "$1" "$D" "$hint" "$R"
    read -r a || a=""
    a=${a:-$def}
    [[ ${a,,} == y* || ${a,,} == д* ]]
}

run() {  # run cmd... — с учётом --dry-run
    if ((DRY)); then printf '  %s$ %s%s\n' "$D" "$*" "$R"; return 0; fi
    "$@"
}

spin() {  # spin "Текст" cmd... — фоновая команда с крутилкой, вывод в лог
    local msg=$1; shift
    if ((DRY)); then printf '  %s$ %s%s\n' "$D" "$*" "$R"; return 0; fi
    mkdir -p "$DATA"
    "$@" >>"$LOG" 2>&1 &
    local pid=$! i=0 frames='⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏'
    if [[ -t 1 ]]; then
        while kill -0 "$pid" 2>/dev/null; do
            printf '\r  %s%s%s %s' "$TEA" "${frames:i++%${#frames}:1}" "$R" "$msg"
            sleep 0.08
        done
        printf '\r\e[K'
    fi
    if wait "$pid"; then ok "$msg"; else err "$msg — не вышло, подробности в $LOG"; return 1; fi
}

cleanup() { [[ -t 1 ]] && printf '\e[?25h' || true; }
trap cleanup EXIT
trap 'echo; err "Прервано"; exit 130' INT

# ── меню компонентов ─────────────────────────────────────────
choose_components() {
    local n=${#COMP_IDS[@]} cur=0 key i mark
    printf '  %sЧто ставим?%s %s↑↓/jk — ходить, пробел — вкл/выкл, a — всё, Enter — поехали%s\n\n' "$B" "$R" "$D" "$R"
    printf '\e[?25l'
    while true; do
        for ((i = 0; i < n; i++)); do
            ((COMP_ON[i])) && mark="$SAGE[✓]$R" || mark="$D[ ]$R"
            if ((i == cur)); then
                printf '\e[K  %s❯%s %s %s%s%s\n' "$TEA" "$R" "$mark" "$B" "${COMP_NAMES[i]}" "$R"
            else
                printf '\e[K    %s %s\n' "$mark" "${COMP_NAMES[i]}"
            fi
        done
        IFS= read -rsn1 key
        case $key in
            $'\e') read -rsn2 -t 0.01 key || key=""
                   case $key in '[A') cur=$(((cur - 1 + n) % n)) ;; '[B') cur=$(((cur + 1) % n)) ;; esac ;;
            k) cur=$(((cur - 1 + n) % n)) ;;
            j) cur=$(((cur + 1) % n)) ;;
            ' ') COMP_ON[cur]=$((1 - COMP_ON[cur])) ;;
            a) local all=1; for ((i = 0; i < n; i++)); do ((COMP_ON[i])) || all=0; done
               for ((i = 0; i < n; i++)); do COMP_ON[i]=$((1 - all)); done ;;
            '') break ;;
        esac
        printf '\e[%dA' "$n"
    done
    printf '\e[?25h'
}

enabled() { local i; for i in "${!COMP_IDS[@]}"; do [[ ${COMP_IDS[i]} == "$1" ]] && return $((1 - COMP_ON[i])); done; return 1; }

set_components() {  # set_components only|skip "a,b"
    local mode=$1 list=",$2," i
    for i in "${!COMP_IDS[@]}"; do
        if [[ $list == *",${COMP_IDS[i]},"* ]]; then
            COMP_ON[i]=$([[ $mode == only ]] && echo 1 || echo 0)
        elif [[ $mode == only ]]; then
            COMP_ON[i]=0
        fi
    done
}

# ── система ──────────────────────────────────────────────────
detect_distro() {
    if have emerge; then echo gentoo
    elif have pacman; then echo arch
    else echo other; fi
}

SUDO=""
need_root() {
    ((EUID == 0)) && return
    if have sudo; then SUDO=sudo; elif have doas; then SUDO=doas
    else die "Нужны права root для пакетов, а нет ни sudo, ни doas"; fi
}

GENTOO_PKGS=(
    gui-wm/hyprland gui-apps/hyprlock gui-apps/hypridle gui-apps/hyprpicker
    gui-libs/xdg-desktop-portal-hyprland
    gui-apps/waybar x11-misc/rofi gui-apps/mako gui-apps/swaybg x11-terms/kitty
    gui-apps/grim gui-apps/slurp gui-apps/wl-clipboard gui-apps/swappy app-misc/cliphist
    media-sound/playerctl media-sound/pavucontrol x11-libs/libnotify
    sys-process/btop app-misc/fastfetch media-sound/cava media-video/ffmpeg
    dev-python/pygobject gui-libs/gtk
    x11-themes/papirus-icon-theme
    media-fonts/iosevka media-fonts/symbols-nerd-font media-fonts/noto-cjk
    dev-vcs/git
)
ARCH_PKGS=(
    hyprland hyprlock hypridle hyprpicker xdg-desktop-portal-hyprland
    waybar rofi mako swaybg kitty
    grim slurp wl-clipboard swappy cliphist
    playerctl pavucontrol libnotify btop fastfetch cava ffmpeg
    python-gobject gtk4 papirus-icon-theme
    ttc-iosevka ttf-nerd-fonts-symbols noto-fonts-cjk
    polkit-kde-agent git base-devel cmake
)

install_gentoo() {
    info "Оверлеи hyproverlay и guru"
    have eselect && run $SUDO eselect repository enable hyproverlay guru >/dev/null 2>&1 || true
    run $SUDO emaint sync -r hyproverlay || warn "не удалось синхронизировать hyproverlay"
    run $SUDO emaint sync -r guru || warn "не удалось синхронизировать guru"

    info "package.accept_keywords / package.use → hyprecho"
    local kw use
    kw=$(cat <<'KW'
*/*::hyproverlay ~amd64
app-misc/cliphist::guru ~amd64
media-fonts/symbols-nerd-font::guru ~amd64
dev-cpp/sdbus-c++ ~amd64
KW
)
    use=$(cat <<'USE'
gui-apps/waybar mpris network pulseaudio tray
x11-misc/rofi wayland
dev-python/pygobject cairo
USE
)
    if ((DRY)); then
        printf '  %s$ write /etc/portage/package.{accept_keywords,use}/hyprecho%s\n' "$D" "$R"
    else
        $SUDO mkdir -p /etc/portage/package.accept_keywords /etc/portage/package.use
        printf '%s\n' "$kw" | $SUDO tee /etc/portage/package.accept_keywords/hyprecho >/dev/null
        printf '%s\n' "$use" | $SUDO tee /etc/portage/package.use/hyprecho >/dev/null
    fi

    info "emerge (${#GENTOO_PKGS[@]} пакетов, уже стоящие пропустятся)"
    local ask_flag=--ask; ((YES)) && ask_flag=""
    run $SUDO emerge $ask_flag --verbose --noreplace --autounmask-continue "${GENTOO_PKGS[@]}"
}

install_arch() {
    local helper=""
    have paru && helper=paru
    have yay && helper=yay
    local confirm=""; ((YES)) && confirm=--noconfirm
    if [[ -n $helper ]]; then
        info "$helper (${#ARCH_PKGS[@]} пакетов)"
        run "$helper" -S --needed $confirm "${ARCH_PKGS[@]}"
    else
        info "pacman (${#ARCH_PKGS[@]} пакетов)"
        run $SUDO pacman -S --needed $confirm "${ARCH_PKGS[@]}"
    fi
}

do_packages() {
    step "Пакеты"
    local distro; distro=$(detect_distro)
    case $distro in
        gentoo) need_root; install_gentoo ;;
        arch)   need_root; install_arch ;;
        *) warn "Дистрибутив не узнал. Поставь руками аналоги:"
           printf '    %s%s%s\n' "$D" "${ARCH_PKGS[*]}" "$R"
           return 0 ;;
    esac
    ok "Пакеты на месте"
}

# ── конфиги ──────────────────────────────────────────────────
BACKUP_DIR=$BACKUPS/$STAMP
backup() {  # backup <путь относительно $HOME>
    local rel=$1 src=$HOME/$1
    [[ -e $src || -L $src ]] || return 0
    # наш же симлинк на репозиторий — бэкапить нечего
    [[ -L $src && $(realpath "$src") == "$DOT"/* ]] && { run rm "$src"; return 0; }
    run mkdir -p "$(dirname "$BACKUP_DIR/$rel")"
    run mv "$src" "$BACKUP_DIR/$rel"
    BACKED_UP=$((BACKED_UP + 1))
}

place() {  # place <путь относительно $HOME> — копия или симлинк из dotfiles/
    local rel=$1 src=$DOT/$1 dst=$HOME/$1
    [[ -e $src ]] || { warn "нет в репозитории: $rel"; return 0; }
    backup "$rel"
    run mkdir -p "$(dirname "$dst")"
    if ((LINK)); then run ln -s "$src" "$dst"
    else run cp -a "$src" "$dst"; fi
}

adapt_system() {  # подгоняем конфиг под машину (только в режиме копий, чтобы не трогать репозиторий)
    ((LINK)) && return 0
    local conf=$HOME/.config/hypr/hyprland.conf
    [[ -f $conf ]] || return 0
    if [[ ! -d /proc/driver/nvidia ]] && grep -qE '^env = (LIBVA_DRIVER_NAME,nvidia|__GLX_VENDOR|NVD_BACKEND)' "$conf"; then
        run sed -i -E 's/^(env = (LIBVA_DRIVER_NAME,nvidia|__GLX_VENDOR_LIBRARY_NAME|NVD_BACKEND).*)/# \1  # не NVIDIA/' "$conf"
        info "NVIDIA не найдена — env-переменные NVIDIA закомментированы"
    fi
    if ! have gentoo-pipewire-launcher && grep -q '^exec-once = gentoo-pipewire-launcher' "$conf"; then
        run sed -i 's/^exec-once = gentoo-pipewire-launcher/# &  # pipewire запускает systemd/' "$conf"
        info "gentoo-pipewire-launcher не найден — строка закомментирована"
    fi
    local polkit
    for polkit in /usr/libexec/polkit-kde-authentication-agent-1 /usr/lib/polkit-kde-authentication-agent-1 \
                  /usr/lib/polkit-gnome/polkit-gnome-authentication-agent-1 /usr/libexec/polkit-gnome-authentication-agent-1; do
        [[ -x $polkit ]] || continue
        if ! grep -qF "exec-once = $polkit" "$conf"; then
            run sed -i -E "s|^exec-once = /usr/[^ ]*polkit[^ ]*|exec-once = $polkit|" "$conf"
            info "polkit-агент → $polkit"
        fi
        break
    done
}

do_configs() {
    step "Конфиги $( ((LINK)) && echo '(симлинки)' || echo '(копии)')"
    BACKED_UP=0
    local d
    for d in "${CONFIG_DIRS[@]}"; do
        place ".config/$d"
        ok "$(printf '%-10s' "$d") → ~/.config/$d"
    done
    run chmod +x "$HOME"/.config/hypr/scripts/*.sh "$HOME"/.config/hypr/rice/{rice,gui}.py 2>/dev/null || true
    adapt_system
    ((BACKED_UP)) && info "Старые конфиги ($BACKED_UP шт.) → ${BACKUP_DIR/#$HOME/\~}"
    return 0
}

do_assets() {
    step "Оформление"
    local wdir=$HOME/Pictures/wallpapers f n=0
    run mkdir -p "$wdir" "$HOME/Pictures/Screenshots"
    # обои не бэкапим и не удаляем — только докладываем свои
    for f in "$DOT"/Pictures/wallpapers/*; do
        [[ -e $f ]] || continue
        [[ -e $wdir/$(basename "$f") ]] && continue
        run cp -a "$f" "$wdir/"; n=$((n + 1))
    done
    ok "Обои: +$n в ~/Pictures/wallpapers"

    place .icons/Nordic-cursors
    ok "Курсоры Nordic-cursors"

    if have gsettings; then
        run gsettings set org.gnome.desktop.interface color-scheme prefer-dark 2>/dev/null || true
        run gsettings set org.gnome.desktop.interface icon-theme Papirus-Dark 2>/dev/null || true
        run gsettings set org.gnome.desktop.interface cursor-theme Nordic-cursors 2>/dev/null || true
        ok "GTK: тёмная схема, Papirus-Dark"
    fi

    if have fc-list; then
        fc-list : family | grep -i 'Iosevka' >/dev/null || warn "Шрифт Iosevka не найден (поставится с пакетами)"
        fc-list : family | grep -i 'Symbols Nerd Font' >/dev/null || warn "Symbols Nerd Font не найден — иконки в баре будут квадратиками"
        run fc-cache -f >/dev/null 2>&1 || true
    fi
}

# ── hyprbars ─────────────────────────────────────────────────
build_hyprbars() {
    local src=$1 out=$2 hver
    rm -rf "$src"
    git clone --quiet https://github.com/hyprwm/hyprland-plugins "$src"
    # hyprpm.toml хранит пары «коммит Hyprland → коммит плагинов» — берём совместимый
    hver=$(Hyprland --version 2>/dev/null | grep -oE 'commit [0-9a-f]{7,}' | head -1 | cut -d' ' -f2 || true)
    if [[ -n $hver ]]; then
        local pin
        pin=$(grep -oE "\[\"$hver[0-9a-f]*\", *\"[0-9a-f]+\"\]" "$src/hyprpm.toml" | grep -oE '"[0-9a-f]+"\]' | tr -d '"]' | head -1 || true)
        [[ -n $pin ]] && git -C "$src" checkout --quiet "$pin"
    fi
    make -C "$src/hyprbars" all
    mkdir -p "$(dirname "$out")"
    cp "$src/hyprbars/hyprbars.so" "$out"
}

do_plugin() {
    step "Плагин hyprbars"
    local out=$HOME/.local/share/hypr-rice/hyprbars.so
    if ! have Hyprland; then warn "Hyprland ещё не установлен — пропускаю (потом: ./install.sh --only plugin)"; return 0; fi
    if [[ -f $out ]] && ! ask "hyprbars.so уже есть. Пересобрать под текущий Hyprland?" n; then
        ok "Оставил как есть"; return 0
    fi
    for t in git make g++ pkg-config; do have $t || { warn "Нет $t — пропускаю сборку"; return 0; }; done
    pkg-config --exists hyprland 2>/dev/null || { warn "Нет заголовков Hyprland (pkg-config hyprland) — пропускаю"; return 0; }
    spin "Сборка hyprbars (пару минут)" build_hyprbars "$DATA/src/hyprland-plugins" "$out" || return 0
}

# ── ярлыки ───────────────────────────────────────────────────
desktop_entry() {  # desktop_entry file name comment exec icon
    local file=$HOME/.local/share/applications/$1
    if ((DRY)); then printf '  %s$ write %s%s\n' "$D" "$file" "$R"; return; fi
    mkdir -p "$(dirname "$file")"
    cat >"$file" <<EOF
[Desktop Entry]
Type=Application
Name=$2
Comment=$3
Exec=$4
Icon=$5
Terminal=false
Categories=Settings;DesktopSettings;
EOF
}

do_extras() {
    step "Ярлыки и команды"
    local rice=$HOME/.config/hypr/rice
    desktop_entry hyprecho-settings.desktop "Настройки райса" "hyprEcho: цвета, бар, окна, шрифты" "$rice/gui.py" preferences-desktop-theme
    desktop_entry hyprecho-themes.desktop "Темы райса" "hyprEcho: быстрый выбор темы" "$rice/gui.py themes" preferences-desktop-color
    desktop_entry hyprecho-lang.desktop "Язык и раскладка" "hyprEcho: язык интерфейса и раскладки" "$rice/gui.py lang" preferences-desktop-locale
    ok "Лаунчер: «Настройки райса», «Темы райса», «Язык и раскладка»"

    run mkdir -p "$HOME/.local/bin"
    run ln -sf "$rice/rice.py" "$HOME/.local/bin/rice"
    ok "Команда rice → rice.py  (rice get · rice set rounding 12 · rice theme x11-classic)"
    [[ :$PATH: == *":$HOME/.local/bin:"* ]] || warn "~/.local/bin нет в PATH — добавь в ~/.bashrc"
}

# ── применить тему ───────────────────────────────────────────
pick_theme() {
    [[ -n $THEME ]] && return
    local tf=$DOT/.config/hypr/rice/themes.json
    local -a ids names
    mapfile -t ids < <(python3 -c 'import json,sys; [print(k) for k in json.load(open(sys.argv[1]))]' "$tf" 2>/dev/null)
    mapfile -t names < <(python3 -c 'import json,sys; [print(v["name"]+" — "+v.get("desc","")) for v in json.load(open(sys.argv[1])).values()]' "$tf" 2>/dev/null)
    THEME=${ids[0]:-hyprecho}
    ((YES)) || [[ ! -t 0 ]] || ((${#ids[@]} < 2)) && return
    printf '\n  %sТема:%s\n' "$B" "$R"
    local i
    for i in "${!ids[@]}"; do printf '    %s%d%s) %s\n' "$TEA" $((i + 1)) "$R" "${names[i]}"; done
    printf '  %s?%s номер %s[1]%s ' "$TEA" "$R" "$D" "$R"
    read -r i || i=1
    [[ $i =~ ^[0-9]+$ ]] && ((i >= 1 && i <= ${#ids[@]})) && THEME=${ids[i - 1]}
}

do_apply() {
    step "Применяю тему «$THEME»"
    local rice=$HOME/.config/hypr/rice/rice.py
    [[ -f $rice ]] || { warn "rice.py не найден — сначала поставь конфиги"; return 0; }
    have python3 || { warn "Нет python3"; return 0; }

    if [[ -n ${HYPRLAND_INSTANCE_SIGNATURE:-} ]]; then
        spin "rice.py theme $THEME" python3 "$rice" theme "$THEME" || return 0
        run pkill -x waybar 2>/dev/null || true
        ((DRY)) || (setsid waybar >/dev/null 2>&1 &)
        ok "Hyprland перечитал конфиг, waybar перезапущен"
    else
        # не в сессии: генерируем файлы и сами запоминаем обои (swaybg без Wayland не запустится)
        spin "rice.py theme $THEME" env -u WAYLAND_DISPLAY python3 "$rice" theme "$THEME" || return 0
        local wall
        wall=$(python3 -c 'import json,os,sys; print(os.path.expanduser(json.load(open(sys.argv[1]))[sys.argv[2]].get("wallpaper","")))' \
               "$HOME/.config/hypr/rice/themes.json" "$THEME" 2>/dev/null || true)
        [[ -f $wall ]] && run ln -sf "$wall" "$HOME/.cache/wallpaper" && ok "Обои: $(basename "$wall")"
    fi
}

# ── подкоманды ───────────────────────────────────────────────
cmd_collect() {
    banner
    have rsync || die "Для collect нужен rsync"
    printf '  %sЗабираю райс из %s в %s%s\n' "$B" "$HOME" "${DOT/#$HOME/\~}" "$R"
    local ex=() e d
    for e in "${EXCLUDES[@]}"; do ex+=(--exclude "$e"); done
    for d in "${CONFIG_DIRS[@]}"; do
        [[ -L $HOME/.config/$d ]] && { info "$d — симлинк на репозиторий, пропускаю"; continue; }
        [[ -d $HOME/.config/$d ]] || { warn "нет ~/.config/$d"; continue; }
        mkdir -p "$DOT/.config"
        rsync -a --delete "${ex[@]}" "$HOME/.config/$d/" "$DOT/.config/$d/"
        ok ".config/$d"
    done
    for d in "${HOME_ITEMS[@]}"; do
        [[ -d $HOME/$d && ! -L $HOME/$d ]] || continue
        mkdir -p "$DOT/$d"
        rsync -a --delete "$HOME/$d/" "$DOT/$d/"
        ok "$d"
    done
    # машинное состояние: мониторы у всех свои
    python3 - "$DOT/.config/hypr/rice/state.json" <<'PY' 2>/dev/null || true
import json, sys
p = sys.argv[1]; s = json.load(open(p)); s['monitors'] = {}
json.dump(s, open(p, 'w'), ensure_ascii=False, indent=2)
PY
    printf '\n  %sГотово.%s %sgit -C %s status%s — посмотреть, что поменялось\n' "$SAGE" "$R" "$D" "${REPO/#$HOME/\~}" "$R"
}

cmd_restore() {
    banner
    local which=${1:-}
    [[ -d $BACKUPS ]] || die "Бэкапов нет ($BACKUPS)"
    [[ -z $which ]] && which=$(ls -1 "$BACKUPS" | sort | tail -1)
    local dir=$BACKUPS/$which
    [[ -d $dir ]] || die "Нет бэкапа $which. Есть: $(ls -1 "$BACKUPS" | tr '\n' ' ')"
    printf '  %sВозвращаю бэкап %s%s\n' "$B" "$which" "$R"
    local rel
    while IFS= read -r rel; do
        rel=${rel#./}
        if [[ -e $HOME/$rel || -L $HOME/$rel ]]; then run rm -rf "${HOME:?}/$rel"; fi
        run mkdir -p "$(dirname "$HOME/$rel")"
        run cp -a "$dir/$rel" "$HOME/$rel"
        ok "$rel"
    done < <(cd "$dir" && find . -mindepth 2 -maxdepth 2 \( -path './.config/*' -o -path './.icons/*' \) | sort)
    [[ -n ${HYPRLAND_INSTANCE_SIGNATURE:-} ]] && run hyprctl reload >/dev/null
    printf '\n  %sВернул.%s\n' "$SAGE" "$R"
}

cmd_uninstall() {
    banner
    ask "Убрать конфиги hyprEcho и вернуть последний бэкап?" n || exit 0
    local d
    for d in "${CONFIG_DIRS[@]}"; do run rm -rf "${HOME:?}/.config/$d"; done
    run rm -f "$HOME"/.local/share/applications/hyprecho-*.desktop "$HOME/.local/bin/rice"
    ok "Конфиги и ярлыки убраны (пакеты, обои и курсоры оставил)"
    if [[ -d $BACKUPS ]] && ls "$BACKUPS" | grep -q .; then cmd_restore; fi
}

cmd_doctor() {
    banner
    local bad=0 c
    check() { if eval "$2" >/dev/null 2>&1; then ok "$1"; else err "$1"; bad=$((bad + 1)); fi; }
    printf '  %sПрограммы%s\n' "$B" "$R"
    for c in Hyprland hyprlock hypridle hyprpicker waybar rofi mako swaybg kitty grim slurp wl-copy \
             swappy cliphist playerctl notify-send btop ffmpeg python3; do
        check "$c" "have $c"
    done
    printf '\n  %sGUI-настройщик%s\n' "$B" "$R"
    check "python3-gobject + GTK4" "python3 -c 'import gi; gi.require_version(\"Gtk\", \"4.0\"); from gi.repository import Gtk'"
    check "rice.py" "[[ -x $HOME/.config/hypr/rice/rice.py ]]"
    check "gui.py" "[[ -x $HOME/.config/hypr/rice/gui.py ]]"
    check "hyprbars.so (заголовки окон)" "[[ -f $HOME/.local/share/hypr-rice/hyprbars.so ]]"
    printf '\n  %sШрифты и оформление%s\n' "$B" "$R"
    check "Iosevka" "fc-list : family | grep -i iosevka"
    check "Symbols Nerd Font" "fc-list : family | grep -i 'Symbols Nerd Font'"
    check "Noto CJK (для 茶)" "fc-list : family | grep -i 'Noto Sans CJK'"
    check "Курсоры Nordic" "[[ -d $HOME/.icons/Nordic-cursors ]]"
    check "Обои" "ls $HOME/Pictures/wallpapers/* "
    printf '\n  %sКонфиги%s\n' "$B" "$R"
    for c in "${CONFIG_DIRS[@]}"; do
        if [[ -L $HOME/.config/$c ]]; then ok "$c (симлинк → репозиторий)"
        else check "$c" "[[ -d $HOME/.config/$c ]]"; fi
    done
    echo
    ((bad)) && { warn "Проблем: $bad. Починить: ./install.sh"; return 1; }
    printf '  %sВсё на месте ☕%s\n' "$SAGE" "$R"
}

usage() { awk 'NR > 2 && /^# ───/ { exit } NR > 2 { sub(/^# ?/, ""); print }' "${BASH_SOURCE[0]}"; }

# ── main ─────────────────────────────────────────────────────
main() {
    local cmd=install
    case ${1:-} in
        collect|restore|doctor|uninstall) cmd=$1; shift ;;
        help|-h|--help) usage; exit 0 ;;
    esac
    local only="" skip=""
    while (($#)); do
        case $1 in
            -y|--yes) YES=1 ;;
            -n|--dry-run) DRY=1 ;;
            -l|--link) LINK=1 ;;
            -t|--theme) THEME=${2:?нужно имя темы}; shift ;;
            --only) only=${2:?}; shift ;;
            --skip) skip=${2:?}; shift ;;
            *) [[ $cmd == restore && $1 != -* ]] && { RESTORE_ARG=$1; shift; continue; }
               die "Не понял аргумент: $1 (см. ./install.sh --help)" ;;
        esac
        shift
    done

    case $cmd in
        collect) cmd_collect; return ;;
        restore) cmd_restore "${RESTORE_ARG:-}"; return ;;
        doctor) cmd_doctor; return ;;
        uninstall) cmd_uninstall; return ;;
    esac

    ((EUID == 0)) && die "Запускай от своего пользователя, не от root — sudo попрошу сам, когда нужно"
    [[ -d $DOT/.config/hypr ]] || die "Нет $DOT — сначала ./install.sh collect на машине с райсом"

    banner
    [[ -n $only ]] && set_components only "$only"
    [[ -n $skip ]] && set_components skip "$skip"
    if [[ -z $only && -z $skip ]] && ((!YES)) && [[ -t 0 && -t 1 ]]; then choose_components; fi

    enabled apply && pick_theme
    local c
    for c in "${COMP_IDS[@]}"; do enabled "$c" && STEPS=$((STEPS + 1)); done
    ((STEPS)) || { info "Ничего не выбрано"; exit 0; }
    ((DRY)) && warn "Пробный прогон: ничего не меняю, только показываю"
    mkdir -p "$DATA"

    enabled packages && do_packages
    enabled configs  && do_configs
    enabled assets   && do_assets
    enabled plugin   && do_plugin
    enabled extras   && do_extras
    enabled apply    && do_apply

    printf '\n%s  ☕ Готово!%s\n\n' "$B$SAGE" "$R"
    cat <<EOF
  ${TEA}Super + /${R}          шпаргалка по всем биндам
  ${TEA}Super + I${R}          окно настроек (цвета, бар, окна, шрифты)
  ${TEA}Super + T${R}          темы
  ${TEA}Super + Space${R}      лаунчер        ${TEA}Super + W${R}  обои
  ${TEA}Super + Enter${R}      терминал       ${TEA}Super + Q${R}  закрыть окно

EOF
    if [[ -z ${HYPRLAND_INSTANCE_SIGNATURE:-} ]]; then
        info "Выйди из текущей сессии и выбери ${B}Hyprland${R} в менеджере входа"
    fi
    info "Проверить установку: ${D}./install.sh doctor${R}"
    [[ -f $LOG ]] && info "Лог: ${LOG/#$HOME/\~}"
    return 0
}

main "$@"
