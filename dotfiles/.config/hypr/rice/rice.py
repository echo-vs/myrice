#!/usr/bin/env python3
# hyprEcho · настройки райса
#   rice.py menu          — меню (Super + I, или ПКМ по 茶 в waybar)
#   rice.py apply         — пересобрать все конфиги из state.json
#   rice.py set KEY VALUE — поменять одну настройку, например: rice.py set palette nord
#   rice.py theme ID      — применить тему из themes.json, например: rice.py theme x11-classic
#
# Окно настроек для людей: gui.py (Super + I), темы: gui.py themes (Super + T),
# язык и раскладка: gui.py lang (Super + Shift + Space).
#
# Палитры лежат в palettes.json: добавь свою по образцу, и она появится в меню.
# Цвета генерируются в: hypr/colors.conf, waybar/colors.css, rofi/colors.rasi,
# kitty/hyprecho.conf, mako/config. Окна Hyprland: hypr/rice.conf.

import html, json, os, re, shutil, subprocess, sys, time

CFG = os.path.expanduser('~/.config')
HERE = os.path.join(CFG, 'hypr', 'rice')
STATE = os.path.join(HERE, 'state.json')
PALETTES = json.load(open(os.path.join(HERE, 'palettes.json')))

P = lambda *a: os.path.join(CFG, *a)
HYPR, HYPR_COLORS, HYPR_RICE, HYPRLOCK = P('hypr/hyprland.conf'), P('hypr/colors.conf'), P('hypr/rice.conf'), P('hypr/hyprlock.conf')
WB_CONF, WB_CSS, WB_COLORS = P('waybar/config.jsonc'), P('waybar/style.css'), P('waybar/colors.css')
ROFI_THEME, ROFI_COLORS = P('rofi/hyprecho.rasi'), P('rofi/colors.rasi')
KITTY_CONF, KITTY_COLORS = P('kitty/kitty.conf'), P('kitty/hyprecho.conf')
MAKO = P('mako/config')
PLASMA_LOCALE = P('plasma-localerc')
WALLPAPER = P('hypr/scripts/wallpaper.sh')
WALL_DIR = os.path.expanduser('~/Pictures/wallpapers')
WALL_STATE = os.path.expanduser('~/.cache/wallpaper')
THEMES = os.path.join(HERE, 'themes.json')
HYPRBARS = os.path.expanduser('~/.local/share/hypr-rice/hyprbars.so')
ME = os.path.join(HERE, 'rice.py')
GUI = os.path.join(HERE, 'gui.py')

MODULES = [  # правая часть waybar, в этом порядке
    ('mpris', 'Плеер'), ('pulseaudio', 'Громкость'), ('network', 'Сеть'), ('cpu', 'Процессор'),
    ('memory', 'Память'), ('hyprland/language', 'Раскладка'), ('tray', 'Трей'),
    ('custom/dnd', 'Не беспокоить'), ('custom/power', 'Питание'),
]
ACCENTS = [('yellow', 'жёлтый'), ('orange', 'оранжевый'), ('red', 'красный'), ('green', 'зелёный'),
           ('cyan', 'бирюзовый'), ('blue', 'синий'), ('magenta', 'пурпурный')]
ACCENT2 = {'yellow': 'orange', 'orange': 'red', 'red': 'orange', 'green': 'cyan',
           'cyan': 'blue', 'blue': 'magenta', 'magenta': 'blue'}
GAPS = {'none': (0, 0, 'без отступов'), 'compact': (3, 6, 'плотные'), 'normal': (6, 14, 'обычные'),
        'wide': (10, 24, 'просторные')}
ANCHORS = [('top-right', 'справа сверху'), ('top-center', 'по центру сверху'),
           ('bottom-right', 'справа снизу'), ('bottom-center', 'по центру снизу')]
FONTS = ['Iosevka', 'JetBrains Mono', 'Fira Code', 'Cascadia Code', 'Maple Mono', 'Hack',
         'Noto Sans Mono', 'Liberation Mono', 'Nimbus Mono PS']
LANGS = {'ru': ('ru_RU.UTF-8', 'ru'), 'en': ('en_US.UTF-8', 'en_US:en')}

DEFAULT = {
    'palette': 'kanagawa-dragon', 'accent': 'yellow', 'font': 'Iosevka',
    'bar_position': 'top', 'bar_style': 'island', 'bar_height': 36, 'bar_window_title': True,
    'bar_modules': {m: True for m, _ in MODULES},
    'bar_layout': 'solid', 'bar_opacity': 0.92, 'bar_blur': True,
    'rounding': 10, 'gaps': 'normal', 'border_size': 2, 'border_style': 'gradient',
    'blur': True, 'blur_strength': 4, 'term_blur': True, 'shadow': True, 'animations': True, 'inactive_opacity': 0.97,
    'term_opacity': 0.6, 'titlebars': False, 'ui_style': 'modern',
    'mako_anchor': 'top-right',
    # система
    'lang': 'en', 'kb_layouts': 'us,ru', 'kb_toggle': 'grp:alt_shift_toggle',
    'repeat_rate': 40, 'repeat_delay': 280,
    'sensitivity': 0.0, 'accel_flat': False, 'natural_scroll': False, 'follow_mouse': 1,
    'terminal': 'kitty', 'browser': 'firefox-bin', 'files': 'dolphin',
    'monitors': {},
}
# Что входит в тему (остальное — личные настройки системы, темы их не трогают)
THEME_KEYS = ['palette', 'accent', 'font', 'bar_position', 'bar_style', 'bar_height', 'bar_window_title',
              'bar_layout', 'bar_opacity', 'bar_blur',
              'rounding', 'gaps', 'border_size', 'border_style', 'blur', 'blur_strength', 'shadow', 'animations',
              'inactive_opacity', 'term_opacity', 'titlebars', 'ui_style', 'mako_anchor']


# ── состояние ─────────────────────────────────
def load():
    st = json.loads(json.dumps(DEFAULT))
    try:
        saved = json.load(open(STATE))
        st.update({k: v for k, v in saved.items() if k in DEFAULT})
        st['bar_modules'] = {**DEFAULT['bar_modules'], **saved.get('bar_modules', {})}
    except (OSError, ValueError):
        pass
    if st['palette'] not in PALETTES:
        st['palette'] = DEFAULT['palette']
    return st


def save(st):
    tmp = STATE + '.tmp'
    json.dump(st, open(tmp, 'w'), ensure_ascii=False, indent=2)
    os.replace(tmp, STATE)


# ── цвета ─────────────────────────────────────
def rgb(h):
    h = h.lstrip('#')
    return [int(h[i:i + 2], 16) for i in (0, 2, 4)]


def blend(a, b, t):
    return '#' + ''.join(f'{round(x + (y - x) * t):02x}' for x, y in zip(rgb(a), rgb(b)))


def colors(st, pal=None):
    p = pal or PALETTES[st['palette']]
    acc = st['accent'] if st['accent'] in p else 'yellow'
    c = {
        'bg': p['bg'], 'bg_dark': p['bg_dark'], 'surface': p['surface'], 'overlay': p['overlay'],
        'muted': p['muted'], 'fg': p['fg'], 'paper': p['bright'],
        'tea': p[acc], 'amber': p[ACCENT2[acc]],
        'sage': p['green'], 'clay': p['red'], 'mist': p['blue'],
    }
    ansi = p.get('ansi') or [
        p['bg_dark'], p['red'], p['green'], p['yellow'], p['blue'], p['magenta'], p['cyan'], p['bright'],
        blend(p['muted'], p['fg'], .35), *(blend(p[k], '#ffffff', .12) for k in
                                           ('red', 'green', 'yellow', 'blue', 'magenta', 'cyan')), p['fg']]
    return c, p, ansi


# ── файлы ─────────────────────────────────────
def read(f):
    return open(f, encoding='utf-8').read()


def write(f, text):
    try:
        if read(f) == text:
            return False
    except OSError:
        pass
    tmp = f + '.rice-tmp'
    open(tmp, 'w', encoding='utf-8').write(text)
    os.replace(tmp, f)
    return True


def sub1(pattern, repl, text, flags=re.M):
    return re.sub(pattern, repl, text, count=1, flags=flags)


def ensure_setup():
    """Один раз переводит конфиги на общие файлы цветов. Повторный запуск ничего не меняет."""
    css = read(WB_CSS)
    if '@import "colors.css"' not in css:
        css = re.sub(r'^@define-color[^\n]*\n', '', css, flags=re.M)
        css = sub1(r'^(/\*.*?\*/\n)?', lambda m: (m.group(0) or '') + '@import "colors.css";\n', css)
        write(WB_CSS, css)
    rasi = read(ROFI_THEME)
    if '@import "colors.rasi"' not in rasi:
        rasi = re.sub(r'^\s*(bg|surface|overlay|muted|fg|tea|ink):\s*#[0-9a-fA-F]+;\n', '', rasi, flags=re.M)
        rasi = sub1(r'^(/\*.*?\*/\n)?', lambda m: (m.group(0) or '') + '@import "colors.rasi"\n', rasi)
        write(ROFI_THEME, rasi)
    hy = read(HYPR)
    if 'rice/rice.py menu' not in hy:
        bind = 'bindd  = $mod, I, Настройки райса, exec, ~/.config/hypr/rice/rice.py menu'
        if 'Сменить обои' in hy:
            hy = sub1(r'^(bindd\s*=.*Сменить обои.*)$', lambda m: m.group(1) + '\n' + bind, hy)
        else:
            hy += '\n' + bind + '\n'
    if 'rice/gui.py' not in hy:
        gui = ('bindd  = $mod, I, Настройки (окно), exec, ~/.config/hypr/rice/gui.py\n'
               'bindd  = $mod SHIFT, I, Настройки (быстрое меню), exec, ~/.config/hypr/rice/rice.py menu\n'
               'bindd  = $mod, T, Темы, exec, ~/.config/hypr/rice/gui.py themes\n'
               'bindd  = $mod SHIFT, Space, Язык и раскладка, exec, ~/.config/hypr/rice/gui.py lang')
        hy = sub1(r'^bindd\s*=\s*\$mod, I,.*rice\.py menu$', lambda m: gui, hy)
    if 'source = ~/.config/hypr/rice.conf' not in hy:
        hy = hy.rstrip('\n') + '\n\n# Настройки из меню Super + I (генерирует rice.py). Идёт последним, чтобы перекрывать.\nsource = ~/.config/hypr/rice.conf\n'
    write(HYPR, hy)
    wb = read(WB_CONF)
    if 'rice.py menu' not in wb and 'rice/gui.py"' not in wb:
        wb = sub1(r'("on-click": "rofi -show drun")',
                  r'\1,\n    "on-click-right": "~/.config/hypr/rice/gui.py"', wb)
        wb = wb.replace('"tooltip-format": "Лаунчер"', '"tooltip-format": "ЛКМ: лаунчер · ПКМ: настройки"')
    wb = wb.replace('"on-click-right": "~/.config/hypr/rice/rice.py menu"', '"on-click-right": "~/.config/hypr/rice/gui.py"')
    if 'gui.py lang' not in wb:
        wb = sub1(r'("on-click": "hyprctl switchxkblayout all next")',
                  r'\1,\n    "on-click-right": "~/.config/hypr/rice/gui.py lang"', wb)
    write(WB_CONF, wb)


def gen_colors(st):
    c, p, ansi = colors(st)
    hx = lambda k: c[k].lstrip('#')
    changed = set()

    names = {'bg': 'фон', 'bg_dark': 'самый тёмный фон', 'surface': 'плашки', 'overlay': 'рамки',
             'muted': 'приглушённый текст', 'fg': 'текст', 'paper': 'яркий текст', 'tea': 'основной акцент',
             'amber': 'второй акцент', 'sage': 'зелёный', 'clay': 'красный', 'mist': 'синий'}
    body = '\n'.join(f'${k:<8} = rgb({hx(k)})   # {names[k]}' for k in c)
    if write(HYPR_COLORS, f'# {p["name"]} · сгенерировано rice.py\n# Менять через меню Super + I (или ~/.config/hypr/rice/palettes.json)\n{body}\n'):
        changed.add('hypr')

    body = '\n'.join(f'@define-color {k:<8} {v};' for k, v in c.items())
    if write(WB_COLORS, f'/* {p["name"]} · сгенерировано rice.py */\n{body}\n'):
        changed.add('waybar')

    body = '\n'.join(f'    {k + ":":<9} {v};' for k, v in
                     [('bg', c['bg'] + 'f0'), ('surface', c['surface']), ('overlay', c['overlay']),
                      ('muted', c['muted']), ('fg', c['fg']), ('tea', c['tea']), ('ink', c['bg'])])
    write(ROFI_COLORS, f'/* {p["name"]} · сгенерировано rice.py */\n* {{\n{body}\n}}\n')

    sel = p.get('selection') or blend(c['bg'], c['mist'], .35)
    kitty = f"""# {p['name']} для kitty · сгенерировано rice.py
background            {c['bg']}
foreground            {c['fg']}
selection_background  {sel}
selection_foreground  {c['paper']}
cursor                {c['tea']}
cursor_text_color     {c['bg']}
url_color             {c['mist']}
active_border_color   {c['tea']}
inactive_border_color {c['overlay']}
active_tab_background   {c['tea']}
active_tab_foreground   {c['bg']}
inactive_tab_background {c['surface']}
inactive_tab_foreground {c['muted']}
tab_bar_background      {c['bg_dark']}

# чёрный / красный / зелёный / жёлтый / синий / пурпурный / циан / белый
""" + '\n'.join(f'color{i:<2} {ansi[i]}\ncolor{i + 8:<2} {ansi[i + 8]}' for i in range(8)) + '\n'
    if write(KITTY_COLORS, kitty):
        changed.add('kitty')

    lock = sub1(r'^(\s*inner_color\s*=\s*)rgba\([0-9a-fA-F]{8}\)', lambda m: f"{m.group(1)}rgba({hx('bg')}e0)", read(HYPRLOCK))
    lock = sub1(r'(placeholder_text\s*=.*foreground="##)[0-9a-fA-F]{6}', lambda m: m.group(1) + hx('muted'), lock)
    write(HYPRLOCK, lock)

    wb = read(WB_CONF)
    wb = sub1(r'("months":\s*"<span color=\')#[0-9a-fA-F]{6}', r'\g<1>' + c['tea'], wb)
    wb = sub1(r'("weekdays":\s*"<span color=\')#[0-9a-fA-F]{6}', r'\g<1>' + c['muted'], wb)
    wb = sub1(r'("today":\s*"<span color=\')#[0-9a-fA-F]{6}(\' background=\')#[0-9a-fA-F]{6}',
              r'\g<1>' + c['bg'] + r'\g<2>' + c['tea'], wb)
    if write(WB_CONF, wb):
        changed.add('waybar')
    return changed


def gen_waybar(st):
    wb = read(WB_CONF)
    edge = st['bar_position']
    island = st['bar_style'] == 'island'
    wb = sub1(r'("position":\s*)"[a-z]+"', rf'\1"{edge}"', wb)
    wb = sub1(r'("height":\s*)\d+', rf'\g<1>{int(st["bar_height"])}', wb)
    wb = sub1(r'"margin-(top|bottom)":\s*\d+', f'"margin-{edge}": {10 if island else 0}', wb)
    wb = sub1(r'("margin-left":\s*)\d+', rf'\g<1>{14 if island else 0}', wb)
    wb = sub1(r'("margin-right":\s*)\d+', rf'\g<1>{14 if island else 0}', wb)
    left = ['custom/logo', 'hyprland/workspaces'] + (['hyprland/window'] if st['bar_window_title'] else [])
    right = [m for m, _ in MODULES if st['bar_modules'].get(m, True)]
    wb = sub1(r'("modules-left":\s*)\[[^\]]*\]', lambda m: m.group(1) + json.dumps(left, ensure_ascii=False).replace('","', '", "'), wb)
    wb = sub1(r'("modules-right":\s*)\[[^\]]*\]', lambda m: m.group(1) + json.dumps(right, ensure_ascii=False).replace('","', '", "'), wb)
    changed = write(WB_CONF, wb)

    css = read(WB_CSS)
    css = sub1(r'(window#waybar\s*\{[^}]*?border-radius:\s*)\d+px', rf'\g<1>{12 if island else 0}px', css, flags=re.S)
    css = sub1(r'(window#waybar\s*\{[^}]*?border:\s*)[^;]+', r'\g<1>' + ('1px solid alpha(@overlay, 0.9)' if island else '0'), css, flags=re.S)
    css = put_block(css, bar_css(st), BAR_BEGIN, BAR_END)
    return changed | write(WB_CSS, css)


BAR_BEGIN, BAR_END = '/* rice:bar — генерирует rice.py, не править */', '/* rice:bar end */'


def bar_css(st):
    """Фон панели: одна сплошная плашка или отдельные плашки слева, по центру и справа."""
    op = f"{min(1.0, max(0.0, float(st['bar_opacity']))):.2f}"
    if st['bar_layout'] != 'modules':
        return f'window#waybar {{ background: alpha(@bg, {op}); }}'
    island = st['bar_style'] == 'island'
    return f"""
window#waybar {{ background: transparent; border: none; }}
.modules-left, .modules-center, .modules-right {{
  background: alpha(@bg, {op});
  border: 1px solid alpha(@overlay, 0.9);
  border-radius: 12px;
  padding: 0 6px;
}}
.modules-left {{ margin-left: {0 if island else 6}px; }}
.modules-right {{ margin-right: {0 if island else 6}px; }}
""" + ('' if island else '.modules-left, .modules-center, .modules-right { margin-top: 3px; margin-bottom: 3px; }\n')


def gen_hypr(st):
    c, _, _ = colors(st)
    gi, go, _ = GAPS[st['gaps']]
    border = '$tea $amber 45deg' if st['border_style'] == 'gradient' else '$tea'
    dark = c['bg_dark'].lstrip('#')
    text = f"""# Сгенерировано rice.py (меню Super + I). Правки руками перезапишутся.
general {{
    gaps_in  = {gi}
    gaps_out = {go}
    border_size = {int(st['border_size'])}
    col.active_border   = {border}
    col.inactive_border = $overlay
}}

decoration {{
    rounding = {int(st['rounding'])}
    inactive_opacity = {st['inactive_opacity']}

    blur {{
        enabled = {onoff(st['blur'])}
        size = {blur_size(st)}
        passes = {blur_passes(st)}
    }}

    shadow {{
        enabled = {onoff(st['shadow'])}
        color = rgba({dark}b0)
        color_inactive = rgba({dark}60)
    }}
}}

animations {{
    enabled = {onoff(st['animations'])}
}}

# Клавиатура и мышь
input {{
    kb_layout  = {st['kb_layouts']}
    kb_options = {st['kb_toggle']}
    repeat_rate  = {int(st['repeat_rate'])}
    repeat_delay = {int(st['repeat_delay'])}
    sensitivity  = {float(st['sensitivity']):.2f}
    accel_profile = {'flat' if st['accel_flat'] else 'adaptive'}
    natural_scroll = {onoff(st['natural_scroll'])}
    follow_mouse = {int(st['follow_mouse'])}
}}

# Язык интерфейса
env = LANG,{LANGS[st['lang']][0]}
env = LANGUAGE,{LANGS[st['lang']][1]}
""" + ''.join(f'monitor = {name},{rule}\n' for name, rule in st['monitors'].items()) + """
# Окна настроек
windowrule {
    name = rice-settings
    match:class = ^(rice\\.settings)$
    float = on
    size = 1040 720
    center = on
}
windowrule {
    name = rice-popups
    match:class = ^(rice\\.(themes|lang))$
    float = on
    center = on
}
""" + term_rule(st) + bar_rule(st) + bars_block(st)
    return write(HYPR_RICE, text)


def onoff(b):
    return str(bool(b)).lower()


def blur_level(st):
    return min(10, max(1, int(st['blur_strength'])))


def blur_size(st):
    return blur_level(st) + 2  # 3…12


def blur_passes(st):
    lv = blur_level(st)
    return 1 + (lv > 3) + (lv > 7)  # 1…3


def term_rule(st):
    """Без размытия под терминалом: сквозь него видно окна и обои как есть."""
    if st['term_blur']:
        return ''
    cls = re.escape(os.path.basename(st['terminal']))
    return f"""
# Терминал без размытия
windowrule {{
    name = rice-term-noblur
    match:class = ^({cls})$
    no_blur = on
}}
"""


def bar_rule(st):
    """Размытие под waybar: правило для слоя. ignore_alpha — не размывать прозрачные промежутки между плашками."""
    if not (st['blur'] and st['bar_blur']):
        return ''
    return """
# Размытие под панелью
layerrule {
    name = rice-bar-blur
    match:namespace = ^(waybar)$
    blur = on
    ignore_alpha = 0.1
}
"""


UI_BEGIN, UI_END = '/* rice:ui — генерирует rice.py, не править */', '/* rice:ui end */'


def put_block(text, block, begin=UI_BEGIN, end=UI_END):
    text = re.sub(re.escape(begin) + r'.*?' + re.escape(end) + r'\n?', '', text, flags=re.S).rstrip('\n') + '\n'
    return text + (f'\n{begin}\n{block.strip()}\n{end}\n' if block.strip() else '')


def gen_ui(st):
    """Ретро-стиль панели, меню, уведомлений и прозрачность терминала."""
    retro = st['ui_style'] == 'retro'
    ch = set()
    bevel = 'border: 2px solid; border-color: #ffffff @bg_dark @bg_dark #ffffff;'
    sunken = 'border: 2px solid; border-color: @bg_dark #ffffff #ffffff @bg_dark;'
    css = f"""
window#waybar {{ background: @bg; border-radius: 0; {bevel} }}
tooltip {{ border-radius: 0; background: @surface; }}
#workspaces button {{ border-radius: 0; margin: 0 2px; {bevel} }}
#workspaces button.active {{ color: #ffffff; {sunken} }}
#workspaces button.empty {{ color: @muted; }}
#mpris, #pulseaudio, #network, #cpu, #memory, #language, #tray, #custom-dnd, #custom-power {{
  border-radius: 0; background: @surface; {sunken}
}}
""" if retro else ''
    if write(WB_CSS, put_block(read(WB_CSS), css)):
        ch.add('waybar')
    rasi = """
window { border-radius: 0; border: 3px; border-color: @tea; background-color: @bg; }
inputbar { border-radius: 0; border: 2px; border-color: @overlay; }
element { border-radius: 0; }
element selected.normal { text-color: #ffffff; }
message { border-radius: 0; }
""" if retro else ''
    write(ROFI_THEME, put_block(read(ROFI_THEME), rasi))
    kc = sub1(r'^(background_opacity\s+).*$', lambda m: m.group(1) + f"{float(st['term_opacity']):g}", read(KITTY_CONF))
    if write(KITTY_CONF, kc):
        ch.add('kitty')
    return ch


APP_VARS = {'terminal': '$term', 'browser': '$browser', 'files': '$files'}


def gen_apps(st):
    hy = read(HYPR)
    for key, var in APP_VARS.items():
        hy = sub1(r'^(' + re.escape(var) + r'\s*=\s*).*$', lambda m: m.group(1) + st[key], hy)
    return write(HYPR, hy)


def gen_lang(st):
    lang, language = LANGS[st['lang']]
    ch = set()
    rc = read(PLASMA_LOCALE) if os.path.exists(PLASMA_LOCALE) else ''
    rc = re.sub(r'\[(Formats|Translations)\][^\[]*', '', rc).strip()
    rc = (rc + '\n\n' if rc else '') + f'[Formats]\nLANG={lang}\n\n[Translations]\nLANGUAGE={language.replace("_US:en", "_US")}\n'
    write(PLASMA_LOCALE, rc)
    if write(WB_CONF, sub1(r'("locale":\s*)"[^"]*"', rf'\1"{lang}"', read(WB_CONF))):
        ch.add('waybar')
    if os.environ.get('LANG') != lang or os.environ.get('LANGUAGE') != language:
        os.environ.update(LANG=lang, LANGUAGE=language)
        run('hyprctl', '--batch', f'keyword env LANG,{lang} ; keyword env LANGUAGE,{language}')
        run('dbus-update-activation-environment', 'LANG', 'LANGUAGE')
        ch.add('waybar')
    return ch


# ── заголовки окон (hyprbars) ─────────────────
def notify(title, body=''):
    run('notify-send', '-a', 'Настройки', title, body)


def bars_block(st):
    """Заголовки окон: Hyprland сам грузит плагин по строке plugin = и выгружает, когда её нет."""
    if not (st['titlebars'] and os.path.exists(HYPRBARS)):
        return ''
    c, _, _ = colors(st)
    retro = st['ui_style'] == 'retro'
    h = lambda k: 'rgb(' + c[k].lstrip('#') + ')'
    bar, text, btn, icon = (h('tea'), 'rgb(ffffff)', h('bg'), 'rgb(000000)') if retro else \
                           (h('surface'), h('fg'), h('overlay'), h('fg'))
    kw = {
        'bar_color': bar, 'col.text': text, 'bar_height': 22 if retro else 26,
        'bar_text_font': 'Nimbus Sans' if retro else st['font'], 'bar_text_size': 10,
        'bar_text_weight': 'bold' if retro else 'medium', 'bar_text_align': 'center' if retro else 'left',
        'bar_precedence_over_border': 'true' if retro else 'false', 'bar_part_of_window': 'true',
        'bar_padding': 4 if retro else 10, 'bar_button_padding': 4 if retro else 8,
        'on_double_click': 'hyprctl dispatch fullscreen 1',
    }
    lines = [f'        {k} = {v}' for k, v in kw.items()]
    size = 16 if retro else 12
    # кнопки справа налево: закрыть, развернуть, плавающее
    for ic, action in [('󰖭', 'hyprctl dispatch killactive'), ('󰖯', 'hyprctl dispatch fullscreen 1'),
                       ('󰕮', 'hyprctl dispatch togglefloating')]:
        lines.append(f'        hyprbars-button = {btn}, {size}, {ic}, {action}, {icon}')
    body = '\n'.join(lines)
    return f"""
# Заголовки окон (hyprbars)
plugin = {HYPRBARS}
plugin {{
    hyprbars {{
{body}
    }}
}}
"""


# ── темы ──────────────────────────────────────
def themes():
    try:
        return json.load(open(THEMES, encoding='utf-8'))
    except (OSError, ValueError):
        return {}


def save_themes(t):
    tmp = THEMES + '.tmp'
    json.dump(t, open(tmp, 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
    os.replace(tmp, THEMES)


def current_wallpaper():
    try:
        return os.path.realpath(WALL_STATE)
    except OSError:
        return ''


def active_theme(st=None):
    st = st or load()
    for tid, t in themes().items():
        if all(st.get(k) == v for k, v in t['set'].items()):
            return tid
    return None


def apply_theme(tid):
    t = themes()[tid]
    wall = os.path.expanduser(t.get('wallpaper') or '')
    generate_wallpaper(t)
    st = change(**{k: v for k, v in t['set'].items() if k in DEFAULT})
    if wall and os.path.exists(wall) and wall != current_wallpaper():
        subprocess.Popen([WALLPAPER, wall], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
    return st


def save_current_theme(name):
    st = load()
    t = themes()
    tid = re.sub(r'[^\w-]+', '-', name.lower()).strip('-') or 'theme'
    while tid in t and t[tid].get('builtin'):
        tid += '-2'
    t[tid] = {'name': name, 'desc': PALETTES[st['palette']]['name'], 'wallpaper': current_wallpaper(),
              'set': {k: st[k] for k in THEME_KEYS}}
    save_themes(t)
    return tid


def delete_theme(tid):
    t = themes()
    if tid in t and not t[tid].get('builtin'):
        pid = t[tid]['set'].get('palette', '')
        del t[tid]
        save_themes(t)
        # своя палитра темы больше никому не нужна — убираем, если она не включена сейчас
        if PALETTES.get(pid, {}).get('custom') and load()['palette'] != pid \
                and not any(x['set'].get('palette') == pid for x in t.values()):
            del PALETTES[pid]
            save_palettes()


# ── свои темы (редактор в gui.py) ─────────────
PALETTE_KEYS = ['bg', 'bg_dark', 'surface', 'overlay', 'selection', 'muted', 'fg', 'bright',
                'yellow', 'orange', 'red', 'green', 'cyan', 'blue', 'magenta']


def save_palettes():
    path = os.path.join(HERE, 'palettes.json')
    tmp = path + '.tmp'
    json.dump(PALETTES, open(tmp, 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
    os.replace(tmp, path)


def full_palette(p):
    """Палитра со всеми ключами, которые нужны редактору (selection бывает не у всех)."""
    p = dict(p)
    p.setdefault('selection', blend(p['bg'], p['blue'], .35))
    return p


def save_custom_theme(name, desc, pal, settings, wallpaper, tid=None):
    """Сохраняет тему вместе с её собственной палитрой. tid — своя тема, которую правим; иначе создаётся новая."""
    t = themes()
    if not tid or tid not in t or t[tid].get('builtin'):
        tid = re.sub(r'[^\w-]+', '-', name.lower()).strip('-') or 'theme'
        while tid in t:
            tid += '-2'
    pid = 'custom-' + tid
    PALETTES[pid] = {'name': name, 'custom': True, **{k: pal[k] for k in PALETTE_KEYS if k in pal}}
    save_palettes()
    sets = {k: settings[k] for k in THEME_KEYS if k in settings}
    sets['palette'] = pid
    t[tid] = {'name': name, 'desc': desc or '', 'wallpaper': wallpaper or '', 'set': sets}
    save_themes(t)
    return tid


def write_png(path, w, h, rgb_bytes):
    """Простой RGB-PNG без PIL."""
    import struct, zlib
    raw = b''.join(b'\0' + bytes(rgb_bytes[y * w * 3:(y + 1) * w * 3]) for y in range(h))
    chunk = lambda tag, data: struct.pack('>I', len(data)) + tag + data + struct.pack('>I', zlib.crc32(tag + data))
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'wb') as f:
        f.write(b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB', w, h, 8, 2, 0, 0, 0))
                + chunk(b'IDAT', zlib.compress(raw, 6)) + chunk(b'IEND', b''))


def make_x11_weave(path):
    """Классический фон X11 (root weave) — тот самый серый «ковёр» при старте голого X."""
    if os.path.exists(path):
        return
    bits = [0x88, 0x22, 0x44, 0x11]
    k = 2  # пиксель узора = 2×2, иначе на 1440p сливается в серое
    w, h = 2560, 1440
    rows = [b''.join((b'\0\0\0' if b >> x & 1 else b'\xff\xff\xff') * k for x in range(4)) * (w // (4 * k))
            for b in bits]
    write_png(path, w, h, b''.join(rows[(y // k) % 4] for y in range(h)))


def make_sakura_hearts(path):
    """Пастельные сердечки и точки на сливочно-сливовом градиенте. Без PIL: PNG пишем сами."""
    if os.path.exists(path):
        return
    import random
    w, h = 2560, 1440
    top, bottom = rgb('#47294d'), rgb('#22182a')
    img = bytearray()
    for y in range(h):
        t = y / (h - 1)
        img += bytes(round(a + (b - a) * t) for a, b in zip(top, bottom)) * w

    def heart(s):  # маска сердечка s×s со сглаживанием 3×3
        m = []
        for y in range(s):
            row = []
            for x in range(s):
                hit = 0
                for sy in range(3):
                    for sx in range(3):
                        u = ((x + (sx + .5) / 3) / s - .5) * 2.6
                        v = -(((y + (sy + .5) / 3) / s - .5) * 2.6 - .2)
                        hit += (u * u + v * v - 1) ** 3 - u * u * v ** 3 <= 0
                row.append(hit / 9)
            m.append(row)
        return m

    def dot(s):
        r = s / 2
        return [[max(0., min(1., r - ((x + .5 - r) ** 2 + (y + .5 - r) ** 2) ** .5)) for x in range(s)] for y in range(s)]

    def stamp(mask, x0, y0, col, alpha):
        for y, row in enumerate(mask):
            yy = y0 + y
            if not 0 <= yy < h:
                continue
            for x, m in enumerate(row):
                xx = x0 + x
                if m and 0 <= xx < w:
                    a, i = m * alpha, (yy * w + xx) * 3
                    for k in range(3):
                        img[i + k] = round(img[i + k] + (col[k] - img[i + k]) * a)

    rnd = random.Random(14)
    pinks = [rgb(c) for c in ('#f7a8d8', '#ff8fab', '#ffb4c8', '#c3b4ff', '#fff0f7')]
    hearts = {s: heart(s) for s in (22, 34, 50, 72)}
    dots = {s: dot(s) for s in (5, 8, 12)}
    cell = 150
    for gy in range(-1, h // cell + 1):
        for gx in range(-1, w // cell + 1):
            x, y = gx * cell + rnd.randrange(cell), gy * cell + rnd.randrange(cell)
            if rnd.random() < .5:
                s = rnd.choice(list(hearts))
                stamp(hearts[s], x, y, rnd.choice(pinks), rnd.uniform(.14, .38))
            for _ in range(rnd.randrange(3)):
                s = rnd.choice(list(dots))
                stamp(dots[s], x + rnd.randrange(-60, 60), y + rnd.randrange(-60, 60), rnd.choice(pinks), rnd.uniform(.2, .5))

    write_png(path, w, h, img)


GENERATORS = {'x11-weave': make_x11_weave, 'sakura-hearts': make_sakura_hearts}


def generate_wallpaper(t):
    """Темам с "generate" обои рисуются при первом выборе."""
    gen = GENERATORS.get(t.get('generate'))
    if gen and t.get('wallpaper'):
        gen(os.path.expanduser(t['wallpaper']))


def gen_mako(st):
    c, _, ansi = colors(st)
    out, sec = [], None
    for line in read(MAKO).split('\n'):
        if line.startswith('['):
            sec = line.strip()
        key = line.split('=', 1)[0] if '=' in line and not line.startswith('#') else None
        val = None
        if sec is None:
            val = {'background-color': c['bg'] + 'f0', 'text-color': c['fg'], 'border-color': c['overlay'],
                   'progress-color': f"over {c['tea']}55", 'anchor': st['mako_anchor'],
                   'border-radius': '0' if st['ui_style'] == 'retro' else '12',
                   'border-size': '2' if st['ui_style'] == 'retro' else '1',
                   'font': f"{st['font']} {line.rsplit(' ', 1)[-1] if key == 'font' else ''}"}.get(key)
        elif sec == '[urgency=low]' and key == 'text-color':
            val = ansi[8]
        elif sec == '[urgency=high]' and key == 'border-color':
            val = c['clay']
        elif sec.startswith('[app-name=') and key == 'border-color':
            val = c['sage']
        out.append(f'{key}={val}' if val else line)
    return write(MAKO, '\n'.join(out))


def gen_fonts(st):
    f = st['font']
    ch = set()
    if write(KITTY_CONF, sub1(r'^(font_family\s+).*$', lambda m: m.group(1) + f, read(KITTY_CONF))):
        ch.add('kitty')
    if write(WB_CSS, sub1(r'(font-family:\s*)"[^"]+"', lambda m: f'{m.group(1)}"{f}"', read(WB_CSS))):
        ch.add('waybar')
    write(ROFI_THEME, sub1(r'(font:\s*")[^"]*?(\s\d+(?:\.\d+)?")', lambda m: m.group(1) + f + m.group(2), read(ROFI_THEME)))
    write(HYPRLOCK, re.sub(r'^(\s*font_family\s*=\s*).*?(\s+Bold)?$', lambda m: m.group(1) + f + (m.group(2) or ''), read(HYPRLOCK), flags=re.M))
    return ch


def run(*cmd):
    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def apply(st):
    ensure_setup()
    ch = gen_colors(st)
    if gen_waybar(st):
        ch.add('waybar')
    gen_hypr(st)
    gen_apps(st)
    ch |= gen_fonts(st)
    ch |= gen_ui(st)
    ch |= gen_lang(st)
    gen_mako(st)
    run('hyprctl', 'reload')
    if not bars_block(st) and 'hyprbars' in subprocess.run(['hyprctl', 'plugin', 'list'], capture_output=True, text=True).stdout:
        run('hyprctl', 'plugin', 'unload', HYPRBARS)  # сам Hyprland плагин не выгружает, даже без строки plugin =
    run('makoctl', 'reload')
    if 'kitty' in ch:
        run('pkill', '-USR1', '-x', 'kitty')
    if 'waybar' in ch:
        run('pkill', '-x', 'waybar')
        time.sleep(0.25)
        run('hyprctl', 'dispatch', 'exec', 'waybar')


def change(**kv):
    st = load()
    st.update(kv)
    save(st)
    apply(st)
    return st


# ── меню ──────────────────────────────────────
ICON = {'palette': '\U000F03D8', 'accent': '\U000F020A', 'bar': '\U000F0379', 'win': '\U000F05AF',
        'font': '\U000F06D6', 'wall': '\U000F0976', 'bell': '\U000F009A', 'reset': '\U000F0453',
        'on': '\U000F0135', 'off': '\U000F0131', 'check': '\U000F012C'}


def rofi(prompt, rows, selected=0, mesg=None):
    args = ['rofi', '-dmenu', '-i', '-no-custom', '-markup-rows', '-format', 'i', '-p', prompt,
            '-selected-row', str(max(0, selected)),
            '-theme-str', f'window {{width: 560px;}} listview {{lines: {min(len(rows), 11)};}} entry {{placeholder: "";}}']
    if mesg:
        args += ['-mesg', mesg]
    r = subprocess.run(args, input='\n'.join(rows), capture_output=True, text=True)
    out = r.stdout.strip()
    return int(out) if r.returncode == 0 and out.isdigit() else None


def row(icon, label, value='', muted='#737c73'):
    v = f"<span foreground='{muted}'>{html.escape(str(value))}</span>" if value != '' else ''
    return f'{icon}  {html.escape(label).ljust(24)}{v}'


def swatch(p, keys=('bg', 'surface', 'yellow', 'orange', 'green', 'red', 'blue', 'magenta')):
    return ''.join(f"<span foreground='{p[k]}'>●</span>" for k in keys)


def menu_palette():
    sel = None
    while True:
        st = load()
        keys = list(PALETTES)
        if sel is None:
            sel = keys.index(st['palette'])
        rows = [f"{swatch(PALETTES[k])}  {html.escape(PALETTES[k]['name'])}" + (f"  <span foreground='{colors(st)[0]['tea']}'>{ICON['check']}</span>" if k == st['palette'] else '')
                for k in keys]
        i = rofi('палитра', rows, sel, 'Применяется сразу ко всему: окна, waybar, rofi, kitty, уведомления, экран блокировки')
        if i is None:
            return
        sel = i
        change(palette=keys[i])


def menu_accent():
    sel = None
    while True:
        st = load()
        p = PALETTES[st['palette']]
        if sel is None:
            sel = [a for a, _ in ACCENTS].index(st['accent']) if st['accent'] in dict(ACCENTS) else 0
        rows = [f"<span foreground='{p[a]}'>●●●</span>  {n}" + (f"  {ICON['check']}" if a == st['accent'] else '')
                for a, n in ACCENTS]
        i = rofi('акцент', rows, sel, 'Цвет бордера активного окна, рабочего стола в waybar, выделения в rofi и курсора в kitty')
        if i is None:
            return
        sel = i
        change(accent=ACCENTS[i][0])


def menu_waybar():
    sel = 0
    while True:
        st = load()
        mc = colors(st)[0]['muted']
        on = lambda b: f"{ICON['on']} вкл" if b else f"{ICON['off']} выкл"
        items = [
            ('pos', row(ICON['bar'], 'Положение', 'сверху' if st['bar_position'] == 'top' else 'снизу', mc)),
            ('style', row(ICON['bar'], 'Вид', 'остров' if st['bar_style'] == 'island' else 'полоса во всю ширину', mc)),
            ('layout', row(ICON['bar'], 'Фон', 'отдельные модули' if st['bar_layout'] == 'modules' else 'одна сплошная', mc)),
            ('opacity', row(ICON['bar'], 'Непрозрачность', f"{round(st['bar_opacity'] * 100)}%", mc)),
            ('bblur', row(ICON['bar'], 'Размытие под панелью', on(st['bar_blur']), mc)),
            ('height', row(ICON['bar'], 'Высота', f"{st['bar_height']} px", mc)),
            ('title', row(ICON['bar'], 'Заголовок окна', on(st['bar_window_title']), mc)),
        ] + [(m, row(ICON['bar'], n, on(st['bar_modules'].get(m, True)), mc)) for m, n in MODULES]
        i = rofi('waybar', [r for _, r in items], sel, 'Enter переключает. Esc: назад')
        if i is None:
            return
        sel, k = i, items[i][0]
        if k == 'pos':
            change(bar_position='bottom' if st['bar_position'] == 'top' else 'top')
        elif k == 'style':
            change(bar_style='strip' if st['bar_style'] == 'island' else 'island')
        elif k == 'layout':
            change(bar_layout='solid' if st['bar_layout'] == 'modules' else 'modules')
        elif k == 'opacity':
            change(bar_opacity=cycle([1.0, 0.92, 0.75, 0.55, 0.35], st['bar_opacity']))
        elif k == 'bblur':
            change(bar_blur=not st['bar_blur'])
        elif k == 'height':
            hs = [30, 36, 42]
            change(bar_height=hs[(hs.index(st['bar_height']) + 1) % 3 if st['bar_height'] in hs else 1])
        elif k == 'title':
            change(bar_window_title=not st['bar_window_title'])
        else:
            mods = dict(st['bar_modules'])
            mods[k] = not mods.get(k, True)
            change(bar_modules=mods)


def cycle(options, cur):
    return options[(options.index(cur) + 1) % len(options)] if cur in options else options[0]


def menu_windows():
    sel = 0
    while True:
        st = load()
        mc = colors(st)[0]['muted']
        on = lambda b: f"{ICON['on']} вкл" if b else f"{ICON['off']} выкл"
        items = [
            ('rounding', row(ICON['win'], 'Скругление углов', f"{st['rounding']} px", mc)),
            ('gaps', row(ICON['win'], 'Отступы', GAPS[st['gaps']][2], mc)),
            ('border_size', row(ICON['win'], 'Толщина рамки', f"{st['border_size']} px", mc)),
            ('border_style', row(ICON['win'], 'Рамка', 'градиент' if st['border_style'] == 'gradient' else 'один цвет', mc)),
            ('inactive_opacity', row(ICON['win'], 'Неактивные окна', 'непрозрачные' if st['inactive_opacity'] >= 1 else f"прозрачность {round((1 - st['inactive_opacity']) * 100)}%", mc)),
            ('blur', row(ICON['win'], 'Размытие', on(st['blur']), mc)),
            ('blur_strength', row(ICON['win'], 'Сила размытия', f"{st['blur_strength']} из 10", mc)),
            ('term_blur', row(ICON['win'], 'Размытие под терминалом', on(st['term_blur']), mc)),
            ('animations', row(ICON['win'], 'Анимации', on(st['animations']), mc)),
        ]
        i = rofi('окна', [r for _, r in items], sel, 'Enter переключает по кругу. Esc: назад')
        if i is None:
            return
        sel, k = i, items[i][0]
        nxt = {
            'rounding': lambda: cycle([0, 6, 10, 16], st['rounding']),
            'gaps': lambda: cycle(list(GAPS), st['gaps']),
            'border_size': lambda: cycle([1, 2, 3], st['border_size']),
            'border_style': lambda: 'solid' if st['border_style'] == 'gradient' else 'gradient',
            'inactive_opacity': lambda: cycle([1.0, 0.97, 0.9, 0.85], st['inactive_opacity']),
            'blur': lambda: not st['blur'],
            'blur_strength': lambda: cycle([2, 4, 6, 8, 10], st['blur_strength']),
            'term_blur': lambda: not st['term_blur'],
            'animations': lambda: not st['animations'],
        }[k]()
        change(**{k: nxt})


def installed_fonts():
    try:
        fams = subprocess.run(['fc-list', ':', 'family'], capture_output=True, text=True).stdout
    except OSError:
        return FONTS[:1]
    have = {f.strip() for line in fams.splitlines() for f in line.split(',')}
    return [f for f in FONTS if f in have] or FONTS[:1]


def menu_font():
    fonts = installed_fonts()
    st = load()
    rows = [f"<span font_family='{html.escape(f)}'>{html.escape(f)}</span>" + (f"  {ICON['check']}" if f == st['font'] else '') for f in fonts]
    i = rofi('шрифт', rows, fonts.index(st['font']) if st['font'] in fonts else 0,
             'Для kitty, waybar, rofi, уведомлений и экрана блокировки. Показаны только установленные')
    if i is not None:
        change(font=fonts[i])


def menu_notify():
    st = load()
    rows = [n + (f"  {ICON['check']}" if a == st['mako_anchor'] else '') for a, n in ANCHORS]
    i = rofi('уведомления', rows, [a for a, _ in ANCHORS].index(st['mako_anchor']) if st['mako_anchor'] in dict(ANCHORS) else 0)
    if i is not None:
        change(mako_anchor=ANCHORS[i][0])
        run('notify-send', 'Уведомления', 'Теперь они появляются здесь')


def menu_reset():
    i = rofi('сброс', ['Да, вернуть всё как было в hyprEcho', 'Нет'], 1, 'Палитра, waybar, окна, шрифт и уведомления вернутся к исходным')
    if i == 0:
        save(json.loads(json.dumps(DEFAULT)))
        apply(load())


def menu():
    if subprocess.run(['pgrep', '-f', 'rofi -dmenu -i -no-custom -markup-rows'], capture_output=True).returncode == 0:
        return
    sel = 0
    while True:
        st = load()
        mc = colors(st)[0]['muted']
        items = [
            ('palette', row(ICON['palette'], 'Палитра', PALETTES[st['palette']]['name'], mc)),
            ('accent', row(ICON['accent'], 'Акцент', dict(ACCENTS).get(st['accent'], ''), mc)),
            ('waybar', row(ICON['bar'], 'Waybar', f"{'сверху' if st['bar_position'] == 'top' else 'снизу'} · {'остров' if st['bar_style'] == 'island' else 'полоса'}", mc)),
            ('windows', row(ICON['win'], 'Окна', f"углы {st['rounding']} · отступы {GAPS[st['gaps']][2]}", mc)),
            ('font', row(ICON['font'], 'Шрифт', st['font'], mc)),
            ('wall', row(ICON['wall'], 'Обои', '', mc)),
            ('notify', row(ICON['bell'], 'Уведомления', dict(ANCHORS).get(st['mako_anchor'], ''), mc)),
            ('reset', row(ICON['reset'], 'Сбросить к hyprEcho', '', mc)),
        ]
        i = rofi('茶 настройки', [r for _, r in items], sel)
        if i is None:
            return
        sel, k = i, items[i][0]
        if k == 'wall':
            subprocess.run([WALLPAPER])
            continue
        {'palette': menu_palette, 'accent': menu_accent, 'waybar': menu_waybar, 'windows': menu_windows,
         'font': menu_font, 'notify': menu_notify, 'reset': menu_reset}[k]()


def main():
    a = sys.argv[1:]
    if not a or a[0] == 'menu':
        return menu()
    if a[0] == 'apply':
        return apply(load())
    if a[0] == 'theme' and len(a) == 2:
        if a[1] not in themes():
            sys.exit('Нет такой темы. Есть: ' + ', '.join(themes()))
        return apply_theme(a[1])
    if a[0] == 'get':
        return print(json.dumps(load(), ensure_ascii=False, indent=2))
    if a[0] == 'set' and len(a) == 3:
        k, v = a[1], a[2]
        if k not in DEFAULT or isinstance(DEFAULT[k], dict):
            sys.exit(f'Нет такой настройки: {k}. Список: rice.py get')
        d = DEFAULT[k]
        v = (v in ('1', 'true', 'on', 'yes')) if isinstance(d, bool) else type(d)(v)
        return change(**{k: v})
    print(__doc__ or open(ME).read().split('\n\n')[0])


if __name__ == '__main__':
    main()
