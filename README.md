# Tea House · Hyprland rice 茶

Hyprland + waybar + rofi + kitty + mako + hyprlock/hypridle, настройщики `rice.py` (меню) и `gui.py` (окно GTK4), две темы: **Tea House** (Gruvbox Material) и **X11 Classic** (заголовки окон через hyprbars).

## Установка

```bash
git clone <этот репозиторий> ~/Projects/tea-house
cd ~/Projects/tea-house
./install.sh
```

Откроется меню компонентов (↑↓ — ходить, пробел — вкл/выкл, Enter — поехали):

| Компонент  | Что делает |
|------------|------------|
| `packages` | Gentoo (hyproverlay + guru) или Arch (pacman / yay / paru) |
| `configs`  | `~/.config/{hypr,waybar,rofi,kitty,mako,swappy,fastfetch,cava}`; старые уезжают в бэкап |
| `assets`   | обои в `~/Pictures/wallpapers`, курсоры Nordic, тёмная GTK-схема |
| `plugin`   | собирает hyprbars под установленную версию Hyprland |
| `extras`   | «Настройки райса» / «Темы» / «Язык» в лаунчере, команда `rice` |
| `apply`    | генерирует цвета, бар, rofi, kitty, mako под выбранную тему |

Без вопросов: `./install.sh -y --theme tea-house`. Посмотреть план: `./install.sh --dry-run`.

При установке копиями конфиг сам подгоняется под машину: без NVIDIA комментируются её env-переменные, находится нужный polkit-агент, убирается `gentoo-pipewire-launcher`, если его нет. Строку `monitor = DP-1, 2560x1440@240` поправь под свой монитор.

## Другие команды

```bash
./install.sh --link       # симлинки на репозиторий: правки в Super+I сразу попадают в git
./install.sh collect      # забрать текущий райс из $HOME в dotfiles/
./install.sh doctor       # проверить программы, шрифты, плагин, конфиги
./install.sh restore      # вернуть последний бэкап (или restore 20260926-214807)
./install.sh uninstall    # убрать райс и вернуть бэкап
```

Бэкапы и логи лежат в `~/.local/share/tea-house/`.

## Главные бинды

| Клавиши | Что делают |
|---------|------------|
| `Super + /` | шпаргалка по всем биндам |
| `Super + I` / `Super + Shift + I` | окно настроек / быстрое меню |
| `Super + T` | темы |
| `Super + Space` или просто `Super` | лаунчер |
| `Super + Enter` · `Super + Q` | терминал · закрыть окно |
| `Super + hjkl` · `+ Shift` · `+ Ctrl` | фокус · переместить · размер |
| `Super + W` · `Super + V` | обои · история буфера обмена |
| `Print` / `Shift+Print` / `Ctrl+Print` | скриншот области / экрана / в редактор |
| `Super + Esc` · `Super + Shift + E` | блокировка · меню питания |
