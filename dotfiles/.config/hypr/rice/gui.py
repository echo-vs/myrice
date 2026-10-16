#!/usr/bin/env python3
# hyprEcho · окно настроек для людей (GTK4). Всё, что меняется здесь, записывает rice.py,
# так что конфиги руками трогать не нужно.
#   gui.py          — все настройки        (Super + I, ПКМ по 茶 в waybar)
#   gui.py themes   — быстрый выбор темы   (Super + T)
#   gui.py lang     — язык и раскладка     (Super + Shift + Space, ПКМ по EN/RU в waybar)

import hashlib, json, math, os, shutil, subprocess, sys, threading

sys.path.insert(0, os.path.dirname(os.path.realpath(__file__)))
import rice  # noqa: E402

import gi  # noqa: E402
gi.require_version('Gtk', '4.0')
gi.require_version('Gdk', '4.0')
gi.require_version('GdkPixbuf', '2.0')
from gi.repository import Gdk, GdkPixbuf, Gio, GLib, Gtk  # noqa: E402

MODE = sys.argv[1] if len(sys.argv) > 1 and sys.argv[1] in ('themes', 'lang') else 'settings'
THUMBS = os.path.expanduser('~/.cache/wallpapers/thumbs')
SCRIPTS = os.path.expanduser('~/.config/hypr/scripts')
LANG = rice.load()['lang']


def T(ru, en):
    return en if LANG == 'en' else ru


V, H = Gtk.Orientation.VERTICAL, Gtk.Orientation.HORIZONTAL
CENTER = Gtk.Align.CENTER

LAYOUTS = [('us', 'Английская (US)', 'English (US)'), ('ru', 'Русская', 'Russian'),
           ('ua', 'Украинская', 'Ukrainian'), ('by', 'Белорусская', 'Belarusian'),
           ('kz', 'Казахская', 'Kazakh'), ('gb', 'Английская (UK)', 'English (UK)'),
           ('de', 'Немецкая', 'German'), ('fr', 'Французская', 'French'),
           ('es', 'Испанская', 'Spanish'), ('pl', 'Польская', 'Polish')]
SHORT = {'us': 'EN', 'gb': 'EN', 'ru': 'RU', 'ua': 'UA', 'by': 'BY', 'kz': 'KZ', 'de': 'DE', 'fr': 'FR', 'es': 'ES', 'pl': 'PL'}
# Super + Space не предлагаем: на нём лаунчер
TOGGLES = [('grp:alt_shift_toggle', 'Alt + Shift'), ('grp:ctrl_shift_toggle', 'Ctrl + Shift'),
           ('grp:alt_space_toggle', 'Alt + Space'), ('grp:caps_toggle', 'Caps Lock'),
           ('grp:lalt_lshift_toggle', 'Левые Alt + Shift / Left Alt + Shift')]
ACCENTS_EN = {'yellow': 'yellow', 'orange': 'orange', 'red': 'red', 'green': 'green', 'cyan': 'teal',
              'blue': 'blue', 'magenta': 'magenta'}
ANCHORS_EN = {'top-right': 'top right', 'top-center': 'top center', 'bottom-right': 'bottom right',
              'bottom-center': 'bottom center'}
MODULES_EN = {'mpris': 'Player', 'pulseaudio': 'Volume', 'network': 'Network', 'cpu': 'CPU',
              'memory': 'Memory', 'hyprland/language': 'Keyboard layout', 'tray': 'Tray',
              'custom/dnd': 'Do not disturb', 'custom/power': 'Power'}
APPS = {
    'terminal': ['kitty', 'alacritty', 'foot', 'wezterm', 'ghostty', 'konsole', 'xterm'],
    'browser': ['firefox-bin', 'firefox', 'librewolf', 'chromium', 'google-chrome-stable', 'brave-browser', 'vivaldi'],
    'files': ['dolphin', 'thunar', 'nautilus', 'nemo', 'pcmanfm-qt', 'pcmanfm'],
}


# ── мелочи ────────────────────────────────────
def rgbf(h, a=1.0):
    r, g, b = rice.rgb(h)
    return r / 255, g / 255, b / 255, a


def lum(h):
    r, g, b = rice.rgb(h)
    return (0.2126 * r + 0.7152 * g + 0.0722 * b) / 255


def sh(*cmd):
    return subprocess.run(cmd, capture_output=True, text=True).stdout


def spawn(*cmd):
    subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)


def thumb(path, size=(480, 270)):
    path = os.path.expanduser(path or '')
    if not os.path.isfile(path):
        return None
    key = hashlib.md5(f'{path}:{os.path.getmtime(path)}:{size}'.encode()).hexdigest()
    out = os.path.join(THUMBS, key + '.png')
    if not os.path.exists(out):
        # Через GdkPixbuf, а не PIL: он и так нужен GTK и есть всегда. Обрезка по центру, как COVER.
        w, h = size
        try:
            _fmt, iw, ih = GdkPixbuf.Pixbuf.get_file_info(path)
            k = max(w / iw, h / ih)
            pb = GdkPixbuf.Pixbuf.new_from_file_at_scale(path, max(w, round(iw * k)), max(h, round(ih * k)), False)
            pb = pb.new_subpixbuf((pb.get_width() - w) // 2, (pb.get_height() - h) // 2, w, h)
            os.makedirs(THUMBS, exist_ok=True)
            pb.savev(out, 'png', [], [])
        except (GLib.Error, TypeError, ZeroDivisionError):
            return None
    return out


def rrect(cr, x, y, w, h, r):
    r = max(0, min(r, w / 2, h / 2))
    if r < 0.5:
        cr.rectangle(x, y, w, h)
        return
    cr.new_sub_path()
    cr.arc(x + w - r, y + r, r, -math.pi / 2, 0)
    cr.arc(x + w - r, y + h - r, r, 0, math.pi / 2)
    cr.arc(x + r, y + h - r, r, math.pi / 2, math.pi)
    cr.arc(x + r, y + r, r, math.pi, 3 * math.pi / 2)
    cr.close_path()


def lbl(text, *cls, **kw):
    kw.setdefault('xalign', 0)
    kw.setdefault('wrap', True)
    return Gtk.Label(label=text, css_classes=list(cls), **kw)


def row(title, sub=None, w=None):
    b = Gtk.Box(spacing=16, css_classes=['row'])
    t = Gtk.Box(orientation=V, spacing=2, hexpand=True, valign=CENTER)
    t.append(lbl(title, 'title'))
    if sub:
        t.append(lbl(sub, 'dim'))
    b.append(t)
    if w:
        w.set_valign(CENTER)
        b.append(w)
    return b


def group(title, *rows):
    box = Gtk.Box(orientation=V, spacing=8)
    if title:
        box.append(lbl(title, 'h2'))
    card = Gtk.Box(orientation=V, css_classes=['card'])
    for i, r in enumerate(rows):
        if i:
            card.append(Gtk.Separator(css_classes=['sep']))
        card.append(r)
    box.append(card)
    return box


def page(title, sub, *parts):
    inner = Gtk.Box(orientation=V, spacing=22, margin_top=28, margin_bottom=32, margin_start=32, margin_end=32)
    head = Gtk.Box(orientation=V, spacing=4)
    head.append(lbl(title, 'h1'))
    if sub:
        head.append(lbl(sub, 'dim'))
    inner.append(head)
    for p in parts:
        inner.append(p)
    return Gtk.ScrolledWindow(child=inner, hscrollbar_policy=Gtk.PolicyType.NEVER, vexpand=True, hexpand=True)


# ── фоновое применение: окно не подвисает, пока rice.py пересобирает конфиги ──
def APPLY():
    rice.apply(rice.load())


class Worker:
    def __init__(self, done):
        self.q, self.busy, self.done = [], False, done
        self.lock = threading.Lock()

    def submit(self, job):
        with self.lock:
            if job is APPLY and APPLY in self.q:
                return
            self.q.append(job)
            if self.busy:
                return
            self.busy = True
        threading.Thread(target=self.loop).start()  # не daemon: закрытие окна дождётся применения

    def loop(self):
        while True:
            with self.lock:
                if not self.q:
                    self.busy = False
                    break
                job = self.q.pop(0)
            try:
                job()
            except Exception as e:  # покажем, но окно не роняем
                GLib.idle_add(rice.notify, T('Не получилось применить', 'Could not apply'), str(e))
        GLib.idle_add(self.done)


# ── приложение ────────────────────────────────
class App(Gtk.Application):
    def __init__(self):
        super().__init__(application_id=f'rice.{MODE}')
        self.worker = Worker(self.applied)
        self.css = Gtk.CssProvider()
        self.win = None
        self.st = rice.load()
        self.pixbufs = {}
        self.page_name = 'themes'
        self.after = []  # что обновить, когда rice.py закончит

    # состояние
    def set(self, **kv):
        self.st.update(kv)
        st = rice.load()
        st.update(kv)
        rice.save(st)
        self.worker.submit(APPLY)

    def applied(self):
        self.st = rice.load()
        self.restyle()
        for fn in self.after:
            fn()
        self.after = []

    # окно
    def do_activate(self):
        if self.win:
            return self.win.present()
        Gtk.StyleContext.add_provider_for_display(Gdk.Display.get_default(), self.css, Gtk.STYLE_PROVIDER_PRIORITY_USER)
        self.win = Gtk.ApplicationWindow(application=self, decorated=False, css_classes=['rice'])
        if MODE == 'settings':
            self.win.set_default_size(1040, 720)
        keys = Gtk.EventControllerKey()
        keys.connect('key-pressed', lambda _c, k, *_: k == Gdk.KEY_Escape and (self.win.close() or True))
        self.win.add_controller(keys)
        self.restyle()
        self.rebuild()
        self.win.present()

    def rebuild(self):
        global LANG
        LANG = self.st['lang']
        self.win.set_title({'settings': T('Настройки', 'Settings'), 'themes': T('Темы', 'Themes'),
                            'lang': T('Язык и раскладка', 'Language & keyboard')}[MODE])
        self.win.set_child({'settings': self.build_settings, 'themes': self.build_themes_popup,
                            'lang': self.build_lang_popup}[MODE]())

    def restyle(self):
        st = self.st
        c, _, _ = rice.colors(st)
        retro = st['ui_style'] == 'retro'
        r = 0 if retro else 10
        ink = '#ffffff' if retro else c['bg']
        gs = Gtk.Settings.get_default()
        gs.props.gtk_theme_name = 'Adwaita'  # системная Adwaita-dark красит светлые палитры белым текстом
        gs.props.gtk_application_prefer_dark_theme = lum(c['bg']) < 0.5
        if self.win:
            (self.win.add_css_class if retro else self.win.remove_css_class)('retro')
        bevel = f"border: 2px solid; border-color: #ffffff {c['bg_dark']} {c['bg_dark']} #ffffff;"
        self.css.load_from_string(f"""
window.rice {{ background: {c['bg']}; color: {c['fg']}; font-family: "{'Nimbus Sans' if retro else 'Noto Sans'}"; font-size: 14px; }}
window.rice.retro {{ border: 3px solid {c['tea']}; }}
.rice .sidebar {{ background: {c['bg_dark']}; padding: 16px 0; }}
.rice .sidebar .brand {{ font-size: 18px; font-weight: 800; color: {c['tea']}; margin: 4px 22px 14px; }}
.rice stacksidebar, .rice stacksidebar list {{ background: transparent; border: none; }}
.rice stacksidebar row {{ padding: 5px 14px; margin: 1px 10px; min-height: 30px; border-radius: {r}px; color: {c['fg']}; }}
.rice stacksidebar row:hover {{ background: alpha({c['surface']}, 0.7); }}
.rice stacksidebar row:selected {{ background: {c['tea']}; color: {ink}; }}
.rice .card {{ background: {c['surface']}; border-radius: {r}px; border: 1px solid {c['overlay']}; }}
.rice .row {{ padding: 12px 16px; min-height: 36px; }}
.rice .sep {{ background: alpha({c['overlay']}, 0.6); min-height: 1px; }}
.rice .h1 {{ font-size: 24px; font-weight: 800; color: {c['paper']}; }}
.rice .h2 {{ font-size: 13px; font-weight: 700; color: {c['muted']}; margin-left: 4px; }}
.rice .title {{ font-weight: 600; }}
.rice .dim {{ color: {c['muted']}; font-size: 12.5px; }}
.rice button, .rice dropdown > button {{ background: {c['bg']}; color: {c['fg']}; }}
.rice button:hover, .rice dropdown > button:hover {{ background: alpha({c['overlay']}, 0.6); }}
.rice button.flat {{ background: transparent; }}
.rice entry {{ background: {c['bg']}; color: {c['fg']}; }}
.rice popover > contents {{ background: {c['surface']}; color: {c['fg']}; }}
.rice checkbutton check {{ background: {c['bg']}; border: 1px solid {c['overlay']}; }}
.rice switch:checked {{ background: {c['tea']}; }}
.rice scale highlight {{ background: {c['tea']}; }}
.rice checkbutton check:checked {{ background: {c['tea']}; color: {ink}; }}
.rice button.accent {{ background: {c['tea']}; color: {ink}; font-weight: 700; }}
.rice .theme-card {{ padding: 8px; border-radius: {r + 4 if r else 0}px; background: {c['surface']}; border: 2px solid {c['overlay']}; }}
.rice .theme-card:hover {{ border-color: alpha({c['tea']}, 0.6); }}
.rice .theme-card.active {{ border-color: {c['tea']}; }}
.rice .badge {{ background: {c['tea']}; color: {ink}; border-radius: {r}px; padding: 1px 8px; font-size: 12px; font-weight: 700; }}
.rice .big {{ font-size: 16px; font-weight: 700; padding: 16px 22px; border-radius: {r}px; }}
.rice .big.on {{ background: {c['tea']}; color: {ink}; }}
.rice .wall {{ padding: 3px; border-radius: {r}px; border: 3px solid transparent; background: transparent; }}
.rice .wall.on {{ border-color: {c['tea']}; }}
.rice .kbd {{ background: {c['bg']}; border: 1px solid {c['overlay']}; border-radius: 5px; padding: 1px 8px; font-family: monospace; font-size: 12.5px; }}
.rice .note {{ background: alpha({c['tea']}, 0.14); border-radius: {r}px; padding: 10px 14px; }}
.rice .close {{ padding: 2px 10px; border-radius: {r}px; }}
.rice.retro button, .rice.retro dropdown > button, .rice.retro entry {{ border-radius: 0; box-shadow: none; {bevel} background-image: none; }}
.rice.retro button.accent, .rice.retro .big.on {{ border-color: {c['bg_dark']} #ffffff #ffffff {c['bg_dark']}; }}
.rice.retro .card {{ {bevel} }}
""")

    # ── контролы, сразу пишущие в rice ───────
    def sw(self, key, **kw):
        s = Gtk.Switch(active=bool(self.st[key]), **kw)
        s.connect('notify::active', lambda w, _: self.set(**{key: w.get_active()}))
        return s

    def dd(self, key, opts):
        vals = [v for v, _ in opts]
        d = Gtk.DropDown.new_from_strings([l for _, l in opts])
        if self.st[key] in vals:
            d.set_selected(vals.index(self.st[key]))
        d.connect('notify::selected', lambda w, _: self.set(**{key: vals[w.get_selected()]}))
        return d

    def scale(self, key, lo, hi, step, digits=0, fmt=None, conv=float):
        s = Gtk.Scale.new_with_range(H, lo, hi, step)
        s.set_value(self.st[key])
        s.set_digits(digits)
        s.set_draw_value(True)
        s.set_value_pos(Gtk.PositionType.LEFT)
        s.set_size_request(260, -1)
        if fmt:
            s.set_format_value_func(lambda _s, v: fmt(v))
        pending = [0]

        def fire():
            pending[0] = 0
            self.set(**{key: conv(round(s.get_value(), digits))})
            return False

        def changed(_w):
            if pending[0]:
                GLib.source_remove(pending[0])
            pending[0] = GLib.timeout_add(450, fire)  # не дёргаем hyprctl reload на каждый пиксель

        s.connect('value-changed', changed)
        return s

    def close_btn(self):
        b = Gtk.Button(label='✕', css_classes=['flat', 'close'], valign=Gtk.Align.START, tooltip_text='Esc')
        b.connect('clicked', lambda *_: self.win.close())
        return b

    # ── главное окно ──────────────────────────
    def build_settings(self):
        pages = [
            ('themes', T('Темы', 'Themes'), self.page_themes),
            ('look', T('Оформление', 'Appearance'), self.page_look),
            ('bar', T('Панель', 'Panel'), self.page_bar),
            ('wall', T('Обои', 'Wallpaper'), self.page_wall),
            ('lang', T('Язык и клавиатура', 'Language & keyboard'), self.page_lang),
            ('mouse', T('Мышь', 'Mouse'), self.page_mouse),
            ('screen', T('Экран', 'Display'), self.page_screen),
            ('apps', T('Программы', 'Apps'), self.page_apps),
            ('notify', T('Уведомления', 'Notifications'), self.page_notify),
            ('keys', T('Горячие клавиши', 'Shortcuts'), self.page_keys),
            ('system', T('Сброс и справка', 'Reset & help'), self.page_system),
        ]
        stack = Gtk.Stack(transition_type=Gtk.StackTransitionType.CROSSFADE, transition_duration=120, hexpand=True)
        builders = {}
        for name, title, fn in pages:
            stack.add_titled(Gtk.Box(orientation=V), name, title)
            builders[name] = fn

        def ensure(*_):
            # страницы строятся при первом открытии: так окно появляется быстрее
            name = stack.get_visible_child_name()
            self.page_name = name
            if name in builders:
                stack.get_child_by_name(name).append(builders.pop(name)())

        stack.connect('notify::visible-child-name', ensure)
        side = Gtk.Box(orientation=V, css_classes=['sidebar'], width_request=230)
        side.append(lbl('茶  hyprEcho', 'brand'))
        side.append(Gtk.StackSidebar(stack=stack, vexpand=True))
        side.append(lbl(T('Esc — закрыть\nВсё применяется сразу', 'Esc to close\nChanges apply instantly'),
                        'dim', margin_start=24, margin_bottom=6))
        box = Gtk.Box()
        box.append(side)
        box.append(stack)
        stack.set_visible_child_name(self.page_name)
        ensure()
        return box

    # ── темы ──────────────────────────────────
    def wall_pixbuf(self, t, w, h):
        path = os.path.expanduser(t.get('wallpaper') or '')
        if t.get('generate') and not os.path.exists(path):
            rice.generate_wallpaper(t)
        key = (path, w, h)
        if key not in self.pixbufs:
            th = thumb(path)
            self.pixbufs[key] = GdkPixbuf.Pixbuf.new_from_file_at_scale(th, w, h, False) if th else None
        return self.pixbufs[key]

    def draw_preview(self, _area, cr, w, h, t):
        """Мини-рабочий стол: обои, панель и два окна так, как их нарисует тема."""
        st = {**rice.DEFAULT, **self.st, **t['set']}
        c, _, ansi = rice.colors(st, t.get('palette_data'))
        retro = st['ui_style'] == 'retro'
        rrect(cr, 0, 0, w, h, 0 if retro else 8)
        cr.clip()
        pb = self.wall_pixbuf(t, w, h)
        if pb:
            Gdk.cairo_set_source_pixbuf(cr, pb, 0, 0)
        else:
            cr.set_source_rgba(*rgbf(c['bg_dark']))
        cr.paint()
        k = 0.42
        gi, go = (g * k for g in rice.GAPS[st['gaps']][:2])
        # панель
        island = st['bar_style'] == 'island'
        bh = max(9, st['bar_height'] * 0.3)
        m = 5 if island else 0
        by = m if st['bar_position'] == 'top' else h - bh - m
        bar_a = 1 if retro else max(0.35, float(st.get('bar_opacity', 0.92)))
        if st.get('bar_layout') == 'modules' and not retro:
            pm = 0 if island else 3
            for px, pw in ((m + pm, w * 0.3), (w / 2 - w * 0.07, w * 0.14), (w - m - pm - w * 0.3, w * 0.3)):
                rrect(cr, px, by + (0 if island else 1), pw, bh - (0 if island else 2), 4)
                cr.set_source_rgba(*rgbf(c['bg'], bar_a))
                cr.fill()
        else:
            rrect(cr, m, by, w - 2 * m, bh, 0 if retro or not island else 4)
            cr.set_source_rgba(*rgbf(c['bg'], bar_a))
            cr.fill()
        for i in range(4):
            cr.set_source_rgba(*rgbf(c['tea'] if i == 0 else c['muted']))
            rrect(cr, m + 8 + i * 9, by + bh / 2 - 2.5, 6, 5, 0 if retro else 2)
            cr.fill()
        # окна
        top = (by + bh if st['bar_position'] == 'top' else 0) + go + (0 if st['bar_position'] == 'top' else 0)
        bottom = (h if st['bar_position'] == 'top' else by) - go
        if st['bar_position'] == 'bottom':
            top = go
        left, right = go, w - go
        ww = (right - left - gi) / 2
        rad = st['rounding'] * k * 0.8
        bs = max(1, st['border_size'] * 0.6)
        for i, x in enumerate((left, left + ww + gi)):
            active = i == 0
            y, wh = top, bottom - top
            rrect(cr, x, y, ww, wh, rad)
            cr.set_source_rgba(*rgbf(c['tea'] if active else c['overlay']))
            cr.fill()
            ix, iy, iw, ih = x + bs, y + bs, ww - 2 * bs, wh - 2 * bs
            rrect(cr, ix, iy, iw, ih, max(0, rad - bs))
            cr.set_source_rgba(*rgbf(c['bg']))
            cr.fill()
            if st['titlebars']:
                tb = 9
                cr.rectangle(ix, iy, iw, tb)
                cr.set_source_rgba(*rgbf(c['tea'] if retro else c['surface']))
                cr.fill()
                for j in range(3):
                    cr.rectangle(ix + iw - 8 - j * 8, iy + 2, 6, 5)
                    cr.set_source_rgba(*rgbf(c['bg'] if retro else c['overlay']))
                    cr.fill()
                iy += tb
                ih -= tb
            # «текст» в терминале
            for j in range(int((ih - 10) // 8)):
                col = ansi[[2, 7, 4, 3, 7, 5, 7][j % 7]] if active else c['muted']
                cr.set_source_rgba(*rgbf(col, 0.9))
                cr.rectangle(ix + 6, iy + 7 + j * 8, (iw - 12) * (0.35 + 0.5 * ((j * 37 + i * 11) % 7) / 7), 3)
                cr.fill()

    def theme_cards(self, cols):
        flow = Gtk.FlowBox(selection_mode=Gtk.SelectionMode.NONE, homogeneous=True, max_children_per_line=cols,
                           min_children_per_line=min(cols, 2), column_spacing=14, row_spacing=14, valign=Gtk.Align.START)
        active = rice.active_theme(self.st)
        for tid, t in rice.themes().items():
            card = Gtk.Box(orientation=V, spacing=8)
            area = Gtk.DrawingArea(content_width=280, content_height=158)
            area.set_draw_func(self.draw_preview, t)
            card.append(area)
            head = Gtk.Box(spacing=8)
            head.append(lbl(t['name'], 'title', hexpand=True))
            if tid == active:
                head.append(Gtk.Label(label=T('сейчас', 'current'), css_classes=['badge']))
            card.append(head)
            desc = t.get('desc_en' if LANG == 'en' else 'desc', t.get('desc', ''))
            card.append(lbl(desc, 'dim', max_width_chars=34))
            btn = Gtk.Button(child=card, css_classes=['theme-card'] + (['active'] if tid == active else []))
            btn.connect('clicked', lambda _b, tid=tid: self.pick_theme(tid))
            outer = Gtk.Box(orientation=V, spacing=4)
            outer.append(btn)
            acts = Gtk.Box(spacing=4, halign=Gtk.Align.END)
            if t.get('builtin'):
                ed = Gtk.Button(label=T('Сделать на её основе', 'Make one from this'), css_classes=['flat'])
            else:
                ed = Gtk.Button(label=T('Изменить', 'Edit'), css_classes=['flat'])
                rm = Gtk.Button(label=T('Удалить', 'Delete'), css_classes=['flat'])
                rm.connect('clicked', lambda _b, tid=tid: (rice.delete_theme(tid), self.rebuild()))
                acts.append(rm)
            ed.connect('clicked', lambda _b, tid=tid: ThemeEditor(self, tid))
            acts.prepend(ed)
            outer.append(acts)
            flow.append(outer)
        return flow

    def pick_theme(self, tid):
        self.worker.submit(lambda: rice.apply_theme(tid))
        self.after.append(self.rebuild)

    def save_theme_row(self):
        e = Gtk.Entry(placeholder_text=T('Название, например «Моя тёмная»', 'Name, e.g. “My dark”'), hexpand=True)
        b = Gtk.Button(label=T('Сохранить', 'Save'), css_classes=['accent'])

        def save(*_):
            name = e.get_text().strip()
            if name:
                rice.save_current_theme(name)
                self.rebuild()

        b.connect('clicked', save)
        e.connect('activate', save)
        box = Gtk.Box(spacing=10, css_classes=['row'])
        box.append(e)
        box.append(b)
        return group(T('Сохранить текущее оформление как тему', 'Save the current look as a theme'), box)

    def page_themes(self):
        return page(T('Темы', 'Themes'),
                    T('Одно нажатие — и меняется всё: цвета, окна, панель, меню, терминал и обои. Быстрый вызов: Super + T.',
                      'One click changes everything: colors, windows, panel, menus, terminal and wallpaper. Shortcut: Super + T.'),
                    self.create_theme_row(), self.theme_cards(3), self.save_theme_row())

    def create_theme_row(self):
        b = Gtk.Button(label=T('Создать свою тему', 'Create a theme'), css_classes=['accent'])
        b.connect('clicked', lambda *_: ThemeEditor(self))
        return group(None, row(T('Своя тема', 'Your own theme'),
                               T('Свои цвета, обои, панель и окна — с живым превью. Начнёт с того, что у тебя сейчас.',
                                 'Your own colors, wallpaper, panel and windows, with a live preview. Starts from your current look.'), b))

    def build_themes_popup(self):
        box = Gtk.Box(orientation=V, spacing=16, margin_top=20, margin_bottom=20, margin_start=22, margin_end=22)
        head = Gtk.Box()
        t = Gtk.Box(orientation=V, spacing=2, hexpand=True)
        t.append(lbl(T('Темы', 'Themes'), 'h1'))
        t.append(lbl(T('Кликни по теме, чтобы применить. Esc — закрыть.', 'Click a theme to apply it. Esc to close.'), 'dim'))
        head.append(t)
        head.append(self.close_btn())
        box.append(head)
        n = len(rice.themes())
        box.append(self.theme_cards(min(max(n, 2), 3)))
        return box

    # ── оформление ────────────────────────────
    def page_look(self):
        pal = [(k, p['name']) for k, p in rice.PALETTES.items()]
        acc = [(a, ACCENTS_EN[a] if LANG == 'en' else n) for a, n in rice.ACCENTS]
        fonts = rice.installed_fonts()
        if self.st['font'] not in fonts:
            fonts.append(self.st['font'])
        gaps = [(g, {'none': 'none', 'compact': 'tight', 'normal': 'normal', 'wide': 'roomy'}[g] if LANG == 'en' else v[2])
                for g, v in rice.GAPS.items()]
        pct = lambda v: f'{round(v * 100)}%'
        bars = self.sw('titlebars', sensitive=os.path.exists(rice.HYPRBARS))
        return page(
            T('Оформление', 'Appearance'), T('Меняй по одному пункту — всё применяется сразу.', 'Change anything, it applies right away.'),
            group(T('Цвета', 'Colors'),
                  row(T('Палитра', 'Palette'), T('Цвета окон, панели, меню, терминала и уведомлений', 'Colors of windows, panel, menus, terminal and notifications'), self.dd('palette', pal)),
                  row(T('Акцент', 'Accent'), T('Рамка активного окна, выделение, текущий стол', 'Active window border, selection, current workspace'), self.dd('accent', acc)),
                  row(T('Стиль панели и меню', 'Panel and menu style'), T('Ретро — объёмные серые кнопки, как в старых X11', 'Retro: beveled grey buttons, like old X11'),
                      self.dd('ui_style', [('modern', T('современный', 'modern')), ('retro', T('ретро', 'retro'))]))),
            group(T('Окна', 'Windows'),
                  row(T('Скругление углов', 'Corner rounding'), None, self.scale('rounding', 0, 20, 1, conv=int, fmt=lambda v: f'{int(v)} px')),
                  row(T('Отступы между окнами', 'Gaps between windows'), None, self.dd('gaps', gaps)),
                  row(T('Толщина рамки', 'Border width'), None, self.scale('border_size', 0, 6, 1, conv=int, fmt=lambda v: f'{int(v)} px')),
                  row(T('Рамка', 'Border'), None, self.dd('border_style', [('gradient', T('градиент', 'gradient')), ('solid', T('один цвет', 'solid'))])),
                  row(T('Прозрачность неактивных окон', 'Inactive window opacity'), None, self.scale('inactive_opacity', 0.7, 1, 0.01, 2, pct)),
                  row(T('Заголовки окон с кнопками', 'Title bars with buttons'),
                      T('Закрыть, развернуть, сделать плавающим. Двойной клик — развернуть', 'Close, maximize, float. Double-click maximizes')
                      if os.path.exists(rice.HYPRBARS) else T('Нет плагина hyprbars', 'hyprbars plugin not found'), bars)),
            group(T('Эффекты', 'Effects'),
                  row(T('Размытие', 'Blur'), T('Под полупрозрачными окнами и панелью', 'Behind translucent windows and the panel'), self.sw('blur')),
                  row(T('Сила размытия', 'Blur strength'), None, self.scale('blur_strength', 1, 10, 1, conv=int, fmt=lambda v: f'{int(v)}')),
                  row(T('Тени', 'Shadows'), None, self.sw('shadow')),
                  row(T('Анимации', 'Animations'), None, self.sw('animations'))),
            group(T('Терминал и шрифт', 'Terminal and font'),
                  row(T('Шрифт', 'Font'), T('Терминал, панель, меню, уведомления, экран блокировки', 'Terminal, panel, menus, notifications, lock screen'), self.dd('font', [(f, f) for f in fonts])),
                  row(T('Непрозрачность терминала', 'Terminal opacity'), T('Для новых окон kitty', 'For new kitty windows'), self.scale('term_opacity', 0.3, 1, 0.05, 2, pct)),
                  row(T('Размытие под терминалом', 'Blur behind the terminal'), T('Выключи, чтобы сквозь терминал были видны чёткие обои и окна', 'Turn off to see sharp wallpaper and windows through the terminal'), self.sw('term_blur'))),
        )

    # ── панель ────────────────────────────────
    def page_bar(self):
        mods = []
        for m, n in rice.MODULES:
            s = Gtk.Switch(active=self.st['bar_modules'].get(m, True))
            s.connect('notify::active', lambda w, _, m=m: self.set(bar_modules={**self.st['bar_modules'], m: w.get_active()}))
            mods.append(row(MODULES_EN[m] if LANG == 'en' else n, None, s))
        return page(
            T('Панель', 'Panel'), T('Waybar — полоска со столами, часами и значками.', 'Waybar: the strip with workspaces, clock and icons.'),
            group(None,
                  row(T('Где', 'Position'), None, self.dd('bar_position', [('top', T('сверху', 'top')), ('bottom', T('снизу', 'bottom'))])),
                  row(T('Вид', 'Style'), T('Остров — парит с отступами; полоса — во всю ширину', 'Island floats with margins; strip spans the full width'),
                      self.dd('bar_style', [('island', T('остров', 'island')), ('strip', T('полоса', 'strip'))])),
                  row(T('Высота', 'Height'), None, self.scale('bar_height', 24, 48, 1, conv=int, fmt=lambda v: f'{int(v)} px')),
                  row(T('Заголовок активного окна', 'Active window title'), None, self.sw('bar_window_title'))),
            group(T('Фон и размытие', 'Background and blur'),
                  row(T('Фон', 'Background'), T('Одна сплошная плашка или отдельные: слева, по центру и справа', 'One solid bar, or separate pills left, center and right'),
                      self.dd('bar_layout', [('solid', T('одна сплошная', 'solid')), ('modules', T('отдельные модули', 'modules'))])),
                  row(T('Непрозрачность', 'Opacity'), T('Чем прозрачнее, тем заметнее размытие', 'The more transparent, the more the blur shows'),
                      self.scale('bar_opacity', 0.2, 1, 0.01, 2, lambda v: f'{round(v * 100)}%')),
                  row(T('Размытие под панелью', 'Blur behind the panel'),
                      T('Нужно включённое размытие в «Оформлении»', 'Needs blur enabled under Appearance'), self.sw('bar_blur')),
                  row(T('Сила размытия', 'Blur strength'), T('Общая для панели и окон: так устроен Hyprland', 'Shared by panel and windows: Hyprland has one setting'),
                      self.scale('blur_strength', 1, 10, 1, conv=int, fmt=lambda v: f'{int(v)}'))),
            group(T('Что показывать справа', 'What to show on the right'), *mods),
        )

    # ── обои ──────────────────────────────────
    def page_wall(self):
        holder = Gtk.Box(orientation=V)

        def fill():
            while holder.get_first_child():
                holder.remove(holder.get_first_child())
            cur = rice.current_wallpaper()
            flow = Gtk.FlowBox(selection_mode=Gtk.SelectionMode.NONE, max_children_per_line=3, min_children_per_line=2,
                               homogeneous=True, column_spacing=10, row_spacing=10)
            files = sorted(f for f in os.listdir(rice.WALL_DIR) if f.lower().endswith(('.png', '.jpg', '.jpeg', '.webp'))) \
                if os.path.isdir(rice.WALL_DIR) else []
            for f in files:
                path = os.path.join(rice.WALL_DIR, f)
                th = thumb(path)
                if not th:
                    continue
                pic = Gtk.Picture.new_for_filename(th)
                pic.set_content_fit(Gtk.ContentFit.COVER)
                pic.set_size_request(230, 130)
                b = Gtk.Button(child=pic, css_classes=['wall'] + (['on'] if os.path.realpath(path) == cur else []), tooltip_text=f)
                b.connect('clicked', lambda _b, p=path: (spawn(rice.WALLPAPER, p), GLib.timeout_add(700, lambda: fill() and False)))
                flow.append(b)
            holder.append(flow)

        def add(*_):
            dlg = Gtk.FileDialog(title=T('Выбери картинку', 'Pick an image'))
            flt = Gtk.FileFilter(name=T('Картинки', 'Images'))
            flt.add_mime_type('image/*')
            store = Gio.ListStore.new(Gtk.FileFilter)
            store.append(flt)
            dlg.set_filters(store)

            def done(d, res):
                try:
                    f = d.open_finish(res)
                except GLib.Error:
                    return
                os.makedirs(rice.WALL_DIR, exist_ok=True)
                dst = os.path.join(rice.WALL_DIR, os.path.basename(f.get_path()))
                if os.path.realpath(f.get_path()) != os.path.realpath(dst):
                    shutil.copy2(f.get_path(), dst)
                spawn(rice.WALLPAPER, dst)
                GLib.timeout_add(700, lambda: fill() and False)

            dlg.open(self.win, None, done)

        fill()
        btn = Gtk.Button(label=T('Добавить картинку…', 'Add an image…'), css_classes=['accent'], halign=Gtk.Align.START)
        btn.connect('clicked', add)
        return page(T('Обои', 'Wallpaper'),
                    T('Клик по картинке — поставить. Новые картинки копируются в ~/Pictures/wallpapers.',
                      'Click a picture to set it. Added images are copied to ~/Pictures/wallpapers.'),
                    btn, holder)

    # ── язык и раскладка ──────────────────────
    def lang_parts(self):
        st = self.st
        layouts = [l for l in st['kb_layouts'].split(',') if l]
        names = {c: (en if LANG == 'en' else ru) for c, ru, en in LAYOUTS}

        # раскладка прямо сейчас
        now = Gtk.Box(spacing=10, homogeneous=True, css_classes=['row'])

        def fill_now():
            while now.get_first_child():
                now.remove(now.get_first_child())
            try:
                kb = next(k for k in json.loads(sh('hyprctl', 'devices', '-j'))['keyboards'] if k['main'])
                cur = kb['active_layout_index']
            except (StopIteration, ValueError, KeyError):
                cur = -1
            for i, l in enumerate(layouts):
                b = Gtk.Button(css_classes=['big'] + (['on'] if i == cur else []))
                b.set_child(lbl(f"{SHORT.get(l, l.upper())}  ·  {names.get(l, l)}", xalign=0.5))
                b.connect('clicked', lambda _b, i=i: (sh('hyprctl', 'switchxkblayout', 'all', str(i)), fill_now()))
                now.append(b)

        fill_now()

        # язык системы
        sys_box = Gtk.Box(spacing=10, homogeneous=True, css_classes=['row'])
        for code, title in (('ru', 'Русский'), ('en', 'English')):
            b = Gtk.Button(css_classes=['big'] + (['on'] if st['lang'] == code else []))
            b.set_child(lbl(title, xalign=0.5))
            b.connect('clicked', lambda _b, code=code: code != self.st['lang'] and self.set_lang(code))
            sys_box.append(b)
        note = lbl(T('Сразу меняются: это окно, панель и все программы, которые ты откроешь дальше. Уже открытые программы '
                     'переключатся после перезапуска, а всё целиком — после выхода из сеанса и входа обратно.',
                     'Changes right away: this window, the panel and every app you open next. Apps that are already open '
                     'switch after a restart, everything else after you log out and back in.'), 'note', 'dim')

        # список раскладок
        checks = []

        def toggled(w, code):
            chosen = [c for c, cb in checks if cb.get_active()]
            if not chosen:  # хотя бы одна раскладка должна остаться
                w.set_active(True)
                return
            order = [l for l in layouts if l in chosen] + [c for c in chosen if c not in layouts]
            layouts[:] = order
            self.set(kb_layouts=','.join(order))
            self.after.append(fill_now)

        grid = Gtk.FlowBox(selection_mode=Gtk.SelectionMode.NONE, max_children_per_line=2, min_children_per_line=2,
                           homogeneous=True, css_classes=['row'])
        for code, ru, en in LAYOUTS:
            cb = Gtk.CheckButton(label=en if LANG == 'en' else ru, active=code in layouts)
            cb.connect('toggled', toggled, code)
            checks.append((code, cb))
            grid.append(cb)

        return (
            group(T('Раскладка сейчас', 'Current keyboard layout'), now),
            group(T('Язык системы', 'System language'), sys_box, note),
            group(T('Раскладки клавиатуры', 'Keyboard layouts'), grid,
                  row(T('Переключение раскладки', 'Switch layouts with'), None, self.dd('kb_toggle', TOGGLES))),
            group(T('Клавиатура', 'Keyboard'),
                  row(T('Задержка перед повтором', 'Repeat delay'), T('Сколько держать клавишу, пока она не начнёт повторяться', 'How long to hold a key before it repeats'),
                      self.scale('repeat_delay', 150, 800, 10, conv=int, fmt=lambda v: f'{int(v)} ms')),
                  row(T('Скорость повтора', 'Repeat rate'), None, self.scale('repeat_rate', 10, 80, 1, conv=int, fmt=lambda v: f'{int(v)}/s'))),
        )

    def set_lang(self, code):
        self.set(lang=code)
        self.after.append(self.rebuild)

    def page_lang(self):
        return page(T('Язык и клавиатура', 'Language & keyboard'),
                    T('Отдельное окно: Super + Shift + Space или правый клик по EN/RU на панели.',
                      'Quick window: Super + Shift + Space or right-click EN/RU on the panel.'),
                    *self.lang_parts())

    def build_lang_popup(self):
        box = Gtk.Box(orientation=V, spacing=18, margin_top=20, margin_bottom=22, margin_start=22, margin_end=22, width_request=620)
        head = Gtk.Box()
        head.append(lbl(T('Язык и раскладка', 'Language & keyboard'), 'h1', hexpand=True))
        head.append(self.close_btn())
        box.append(head)
        parts = self.lang_parts()
        box.append(parts[0])
        box.append(parts[1])
        box.append(parts[2])
        return box

    # ── мышь ──────────────────────────────────
    def page_mouse(self):
        return page(
            T('Мышь', 'Mouse'), None,
            group(None,
                  row(T('Скорость указателя', 'Pointer speed'), None, self.scale('sensitivity', -1, 1, 0.05, 2)),
                  row(T('Без ускорения', 'No acceleration'), T('Указатель двигается ровно — удобно в играх', 'Pointer moves linearly, handy for games'), self.sw('accel_flat')),
                  row(T('Обратная прокрутка', 'Natural scrolling'), T('Как на телефоне: колесо тянет страницу', 'Like a phone: the wheel drags the page'), self.sw('natural_scroll')),
                  row(T('Фокус окна', 'Window focus'), None,
                      self.dd('follow_mouse', [(1, T('где мышь, там и фокус', 'follows the mouse')),
                                               (0, T('только по клику', 'click to focus')),
                                               (2, T('клавиатура по клику, колесо под мышью', 'keyboard on click, scroll under mouse'))]))),
        )

    # ── экран ─────────────────────────────────
    def page_screen(self):
        groups = []
        try:
            mons = json.loads(sh('hyprctl', 'monitors', '-j'))
        except ValueError:
            mons = []
        for m in mons:
            modes = list(dict.fromkeys(x.removesuffix('Hz') for x in m['availableModes']))
            cur = f"{m['width']}x{m['height']}@{m['refreshRate']:.2f}"
            best = min(range(len(modes)), key=lambda i: (modes[i].split('@')[0] != cur.split('@')[0],
                                                        abs(float(modes[i].split('@')[1]) - m['refreshRate']))) if modes else 0
            md = Gtk.DropDown.new_from_strings([x.replace('@', '  ·  ') + ' Hz' for x in modes])
            md.set_selected(best)
            scales = [1.0, 1.25, 1.5, 1.6, 1.75, 2.0]
            sc = Gtk.DropDown.new_from_strings([f'{int(s * 100)}%' for s in scales])
            sc.set_selected(min(range(len(scales)), key=lambda i: abs(scales[i] - m['scale'])))
            btn = Gtk.Button(label=T('Применить', 'Apply'), css_classes=['accent'], halign=Gtk.Align.END)
            old = f"{cur},{m['x']}x{m['y']},{m['scale']:g}"
            btn.connect('clicked', lambda _b, m=m, md=md, sc=sc, modes=modes, old=old: self.try_monitor(
                m['name'], f"{modes[md.get_selected()]},{m['x']}x{m['y']},{scales[sc.get_selected()]:g}", old))
            groups.append(group(f"{m['name']} · {m['description']}",
                                row(T('Разрешение и частота', 'Resolution and refresh rate'), None, md),
                                row(T('Масштаб', 'Scale'), T('Больше — крупнее текст и окна', 'Bigger means larger text and windows'), sc),
                                row('', None, btn)))
        return page(T('Экран', 'Display'),
                    T('Если картинка пропадёт — ничего не трогай, через 15 секунд вернётся как было.',
                      'If the screen goes blank, just wait: it reverts in 15 seconds.'), *groups)

    def try_monitor(self, name, rule, old):
        sh('hyprctl', 'keyword', 'monitor', f'{name},{rule}')
        dlg = Gtk.Window(transient_for=self.win, modal=True, decorated=False, css_classes=['rice'])
        box = Gtk.Box(orientation=V, spacing=14, margin_top=20, margin_bottom=20, margin_start=24, margin_end=24)
        msg = lbl('', 'title')
        box.append(msg)
        btns = Gtk.Box(spacing=10, halign=Gtk.Align.END)
        back = Gtk.Button(label=T('Вернуть', 'Revert'))
        keep = Gtk.Button(label=T('Оставить', 'Keep'), css_classes=['accent'])
        btns.append(back)
        btns.append(keep)
        box.append(btns)
        dlg.set_child(box)
        left = [15]
        timer = [0]

        def finish(ok):
            if timer[0]:
                GLib.source_remove(timer[0])
                timer[0] = 0
            dlg.close()
            if ok:
                self.set(monitors={**self.st['monitors'], name: rule})
            else:
                sh('hyprctl', 'keyword', 'monitor', f'{name},{old}')

        def tick():
            left[0] -= 1
            if left[0] <= 0:
                timer[0] = 0
                finish(False)
                return False
            msg.set_label(T(f'Оставить эти настройки? Вернётся само через {left[0]} с.',
                            f'Keep these settings? Reverting in {left[0]} s.'))
            return True

        back.connect('clicked', lambda *_: finish(False))
        keep.connect('clicked', lambda *_: finish(True))
        left[0] += 1
        tick()
        timer[0] = GLib.timeout_add_seconds(1, tick)
        dlg.present()

    # ── программы ─────────────────────────────
    def page_apps(self):
        def opts(key):
            found = [a for a in APPS[key] if shutil.which(a)]
            if self.st[key] not in found:
                found.insert(0, self.st[key])
            return [(a, a) for a in found]

        return page(
            T('Программы по умолчанию', 'Default apps'), T('Что открывают горячие клавиши. Показаны только установленные.',
                                                          'What the shortcuts open. Only installed apps are listed.'),
            group(None,
                  row(T('Терминал', 'Terminal'), 'Super + Enter', self.dd('terminal', opts('terminal'))),
                  row(T('Браузер', 'Browser'), 'Super + B', self.dd('browser', opts('browser'))),
                  row(T('Файлы', 'Files'), 'Super + E', self.dd('files', opts('files')))),
        )

    # ── уведомления ───────────────────────────
    def page_notify(self):
        anchors = [(a, ANCHORS_EN[a] if LANG == 'en' else n) for a, n in rice.ANCHORS]
        dnd = Gtk.Switch(active='do-not-disturb' in sh('makoctl', 'mode'))
        dnd.connect('notify::active', lambda *_: spawn(os.path.join(SCRIPTS, 'dnd.sh'), 'toggle'))
        test = Gtk.Button(label=T('Показать пример', 'Show a sample'))
        test.connect('clicked', lambda *_: spawn('notify-send', T('Привет!', 'Hello!'), T('Так выглядят уведомления', 'This is what notifications look like')))
        return page(
            T('Уведомления', 'Notifications'), None,
            group(None,
                  row(T('Где появляются', 'Position'), None, self.dd('mako_anchor', anchors)),
                  row(T('Не беспокоить', 'Do not disturb'), T('Прячет уведомления. Также Super + N', 'Hides notifications. Also Super + N'), dnd),
                  row(T('Проверить', 'Try it'), None, test)),
        )

    # ── горячие клавиши ───────────────────────
    def page_keys(self):
        mods = {64: 'Super', 1: 'Shift', 4: 'Ctrl', 8: 'Alt'}
        keys = {'Return': 'Enter', 'slash': '/', 'SUPER_L': '(Super)', 'mouse_down': T('Колесо', 'Wheel'),
                'mouse:272': T('ЛКМ', 'LMB'), 'mouse:273': T('ПКМ', 'RMB'), 'Print': 'PrtSc', 'Escape': 'Esc'}
        rows = []
        try:
            binds = json.loads(sh('hyprctl', 'binds', '-j'))
        except ValueError:
            binds = []
        for b in binds:
            if not b.get('has_description'):
                continue
            combo = [n for bit, n in mods.items() if b['modmask'] & bit]
            if b['key'] != 'SUPER_L':
                combo.append(keys.get(b['key'], b['key']))
            kb = Gtk.Box(spacing=4)
            for i, part in enumerate(combo):
                if i:
                    kb.append(lbl('+', 'dim'))
                kb.append(Gtk.Label(label=part, css_classes=['kbd']))
            rows.append(row(b['description'], None, kb))
        return page(T('Горячие клавиши', 'Shortcuts'),
                    T('Шпаргалка всегда под рукой: Super + /', 'Cheat sheet anytime: Super + /'), group(None, *rows))

    # ── сброс и справка ───────────────────────
    def page_system(self):
        reset = Gtk.Button(label=T('Вернуть hyprEcho', 'Restore hyprEcho'), css_classes=['accent'])
        reset.connect('clicked', lambda *_: self.pick_theme('hyprecho'))
        folder = Gtk.Button(label=T('Открыть папку', 'Open folder'))
        folder.connect('clicked', lambda *_: spawn('xdg-open', os.path.expanduser('~/.config/hypr')))
        menu = Gtk.Button(label=T('Открыть', 'Open'))
        menu.connect('clicked', lambda *_: spawn(rice.ME, 'menu'))
        plug = T('установлен', 'installed') if os.path.exists(rice.HYPRBARS) else T('не найден', 'not found')
        return page(
            T('Сброс и справка', 'Reset & help'), None,
            group(None,
                  row(T('Вернуть оформление hyprEcho', 'Restore the hyprEcho look'),
                      T('Язык, раскладки, мышь, экран и программы останутся как есть', 'Language, keyboard, mouse, display and apps stay as they are'), reset),
                  row(T('Быстрое меню в rofi', 'Quick rofi menu'), 'Super + Shift + I', menu),
                  row(T('Конфиги', 'Config files'),
                      T('Для тех, кто хочет руками. Файл rice.conf пишет это окно — его не правь.',
                        'For tinkerers. rice.conf is written by this window, don’t edit it.'), folder),
                  row(T('Плагин заголовков окон', 'Title bar plugin'), f'hyprbars: {plug} · {rice.HYPRBARS}')),
        )


# ── редактор тем ──────────────────────────────
COLOR_GROUPS = [
    (('Фон', 'Background'), [('bg', 'Фон окон и панели', 'Window and panel background'),
                             ('bg_dark', 'Самый тёмный фон', 'Darkest background'),
                             ('surface', 'Плашки и карточки', 'Cards and pills'),
                             ('overlay', 'Рамки', 'Borders'),
                             ('selection', 'Выделение текста', 'Text selection')]),
    (('Текст', 'Text'), [('fg', 'Текст', 'Text'), ('muted', 'Приглушённый текст', 'Muted text'),
                         ('bright', 'Яркий текст', 'Bright text')]),
    (('Цвета', 'Colors'), [('yellow', 'Жёлтый', 'Yellow'), ('orange', 'Оранжевый', 'Orange'), ('red', 'Красный', 'Red'),
                           ('green', 'Зелёный', 'Green'), ('cyan', 'Бирюзовый', 'Teal'), ('blue', 'Синий', 'Blue'),
                           ('magenta', 'Пурпурный', 'Magenta')]),
]
IMG_EXT = ('.png', '.jpg', '.jpeg', '.webp')


def contrast(a, b):
    def L(h):
        ch = [x / 255 for x in rice.rgb(h)]
        ch = [x / 12.92 if x <= 0.03928 else ((x + 0.055) / 1.055) ** 2.4 for x in ch]
        return 0.2126 * ch[0] + 0.7152 * ch[1] + 0.0722 * ch[2]
    la, lb = sorted((L(a), L(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)


def to_hex(rgba):
    return '#%02x%02x%02x' % tuple(round(max(0, min(1, v)) * 255) for v in (rgba.red, rgba.green, rgba.blue))


def to_rgba(h):
    c = Gdk.RGBA()
    c.parse(h)
    return c


class ThemeEditor:
    """Отдельное окно: черновик темы живёт здесь, система не меняется, пока не нажмёшь «Применить»."""

    def __init__(self, app, tid=None):
        self.app = app
        themes = rice.themes()
        src = themes.get(tid) if tid else None
        self.tid = tid if src and not src.get('builtin') else None
        st = {**rice.DEFAULT, **app.st, **(src['set'] if src else {})}
        self.set = {k: st[k] for k in rice.THEME_KEYS if k in st}
        self.pal = rice.full_palette(rice.PALETTES.get(st['palette']) or rice.PALETTES[rice.DEFAULT['palette']])
        if src and not self.tid:
            name = src['name'] + T(' (моя)', ' (mine)')
        else:
            name = src['name'] if src else T('Моя тема', 'My theme')
        self.generate = src.get('generate') if src else None
        self.wall = (src.get('wallpaper') if src else '') or rice.current_wallpaper()
        self.color_btns = {}

        self.win = Gtk.Window(application=app, decorated=False, css_classes=['rice'] + (['retro'] if app.st['ui_style'] == 'retro' else []))
        self.win.set_default_size(1040, 720)
        keys = Gtk.EventControllerKey()
        keys.connect('key-pressed', lambda _c, k, *_: k == Gdk.KEY_Escape and (self.win.close() or True))
        self.win.add_controller(keys)

        # слева — настройки
        left = Gtk.Box(orientation=V, spacing=22, margin_top=24, margin_bottom=28, margin_start=28, margin_end=20)
        head = Gtk.Box(orientation=V, spacing=4)
        head.append(lbl(T('Редактор темы', 'Theme editor') if not self.tid else T('Изменить тему', 'Edit theme'), 'h1'))
        head.append(lbl(T('Меняй что хочешь — превью справа обновляется сразу. Система не меняется, пока не нажмёшь «Применить».',
                          'Change anything; the preview on the right updates live. Nothing changes until you press Apply.'), 'dim'))
        left.append(head)

        self.name = Gtk.Entry(text=name, hexpand=True)
        self.desc = Gtk.Entry(text=(src.get('desc', '') if src and self.tid else ''), hexpand=True,
                              placeholder_text=T('Например: «тёплая, для вечера»', 'e.g. “warm, for evenings”'))
        left.append(group(None, row(T('Название', 'Name'), None, self.name), row(T('Описание', 'Description'), None, self.desc)))

        # основа палитры
        keys_p = list(rice.PALETTES)
        base = Gtk.DropDown.new_from_strings([rice.PALETTES[k]['name'] for k in keys_p])
        if st['palette'] in keys_p:
            base.set_selected(keys_p.index(st['palette']))
        base.connect('notify::selected', lambda w, _: self.load_palette(keys_p[w.get_selected()]))
        acc = [a for a, _ in rice.ACCENTS]
        accent = Gtk.DropDown.new_from_strings([ACCENTS_EN[a] if LANG == 'en' else n for a, n in rice.ACCENTS])
        if self.set['accent'] in acc:
            accent.set_selected(acc.index(self.set['accent']))
        accent.connect('notify::selected', lambda w, _: self.put(accent=acc[w.get_selected()]))
        left.append(group(T('Цвета', 'Colors'),
                          row(T('Взять цвета из палитры', 'Start from a palette'),
                              T('Заменит все цвета ниже — потом подправь нужные', 'Replaces all colors below; then tweak what you like'), base),
                          row(T('Акцент', 'Accent'), T('Рамка активного окна, текущий стол, выделение', 'Active border, current workspace, selection'), accent)))
        for (gru, gen), items in COLOR_GROUPS:
            flow = Gtk.FlowBox(selection_mode=Gtk.SelectionMode.NONE, max_children_per_line=3, min_children_per_line=2,
                               column_spacing=10, row_spacing=6, homogeneous=True, margin_top=10, margin_bottom=10,
                               margin_start=12, margin_end=12)
            for key, ru, en in items:
                flow.append(self.color_item(key, en if LANG == 'en' else ru))
            card = Gtk.Box(orientation=V, css_classes=['card'])
            card.append(flow)
            g = Gtk.Box(orientation=V, spacing=8)
            g.append(lbl(T(gru, gen), 'h2'))
            g.append(card)
            left.append(g)

        # обои
        left.append(self.wall_group())

        # окна и панель
        gaps = [(g, {'none': 'none', 'compact': 'tight', 'normal': 'normal', 'wide': 'roomy'}[g] if LANG == 'en' else v[2])
                for g, v in rice.GAPS.items()]
        fonts = rice.installed_fonts()
        if self.set['font'] not in fonts:
            fonts.append(self.set['font'])
        pct = lambda v: f'{round(v * 100)}%'
        left.append(group(T('Окна', 'Windows'),
                          row(T('Стиль', 'Style'), T('Ретро — объёмные серые кнопки, как в старых X11', 'Retro: beveled buttons like old X11'),
                              self.dd('ui_style', [('modern', T('современный', 'modern')), ('retro', T('ретро', 'retro'))])),
                          row(T('Скругление углов', 'Corner rounding'), None, self.scale('rounding', 0, 20, 1, int, lambda v: f'{int(v)} px')),
                          row(T('Отступы', 'Gaps'), None, self.dd('gaps', gaps)),
                          row(T('Толщина рамки', 'Border width'), None, self.scale('border_size', 0, 6, 1, int, lambda v: f'{int(v)} px')),
                          row(T('Рамка', 'Border'), None, self.dd('border_style', [('gradient', T('градиент', 'gradient')), ('solid', T('один цвет', 'solid'))])),
                          row(T('Прозрачность неактивных окон', 'Inactive window opacity'), None, self.scale('inactive_opacity', 0.7, 1, 0.01, float, pct, 2)),
                          row(T('Непрозрачность терминала', 'Terminal opacity'), None, self.scale('term_opacity', 0.3, 1, 0.05, float, pct, 2)),
                          row(T('Шрифт', 'Font'), None, self.dd('font', [(f, f) for f in fonts]))))
        left.append(group(T('Эффекты', 'Effects'),
                          row(T('Размытие', 'Blur'), None, self.sw('blur')),
                          row(T('Сила размытия', 'Blur strength'), None, self.scale('blur_strength', 1, 10, 1, int, lambda v: f'{int(v)}')),
                          row(T('Тени', 'Shadows'), None, self.sw('shadow')),
                          row(T('Анимации', 'Animations'), None, self.sw('animations'))))
        left.append(group(T('Панель', 'Panel'),
                          row(T('Где', 'Position'), None, self.dd('bar_position', [('top', T('сверху', 'top')), ('bottom', T('снизу', 'bottom'))])),
                          row(T('Вид', 'Style'), None, self.dd('bar_style', [('island', T('остров', 'island')), ('strip', T('полоса', 'strip'))])),
                          row(T('Фон', 'Background'), None, self.dd('bar_layout', [('solid', T('одна сплошная', 'solid')), ('modules', T('отдельные модули', 'modules'))])),
                          row(T('Непрозрачность', 'Opacity'), None, self.scale('bar_opacity', 0.2, 1, 0.01, float, pct, 2)),
                          row(T('Размытие под панелью', 'Blur behind the panel'), None, self.sw('bar_blur')),
                          row(T('Высота', 'Height'), None, self.scale('bar_height', 24, 48, 1, int, lambda v: f'{int(v)} px')),
                          row(T('Заголовок активного окна', 'Active window title'), None, self.sw('bar_window_title'))))
        scroll = Gtk.ScrolledWindow(child=left, hscrollbar_policy=Gtk.PolicyType.NEVER, vexpand=True, hexpand=True)

        # справа — превью и кнопки
        right = Gtk.Box(orientation=V, spacing=14, margin_top=24, margin_bottom=24, margin_start=8, margin_end=24, width_request=440)
        top = Gtk.Box()
        top.append(lbl(T('Превью', 'Preview'), 'h2', hexpand=True))
        close = Gtk.Button(label='✕', css_classes=['flat', 'close'], tooltip_text='Esc')
        close.connect('clicked', lambda *_: self.win.close())
        top.append(close)
        right.append(top)
        self.preview = Gtk.DrawingArea(content_width=430, content_height=242)
        self.preview.set_draw_func(lambda a, cr, w, h: app.draw_preview(a, cr, w, h, self.as_theme()))
        right.append(self.preview)
        self.swatches = Gtk.DrawingArea(content_width=430, content_height=26)
        self.swatches.set_draw_func(self.draw_swatches)
        right.append(self.swatches)
        self.note = lbl('', 'note')
        right.append(self.note)
        right.append(Gtk.Box(vexpand=True))
        btns = Gtk.Box(spacing=8, halign=Gtk.Align.END)
        cancel = Gtk.Button(label=T('Отмена', 'Cancel'))
        cancel.connect('clicked', lambda *_: self.win.close())
        save = Gtk.Button(label=T('Сохранить', 'Save'))
        save.connect('clicked', lambda *_: self.save(False))
        apply = Gtk.Button(label=T('Сохранить и применить', 'Save and apply'), css_classes=['accent'])
        apply.connect('clicked', lambda *_: self.save(True))
        for b in (cancel, save, apply):
            btns.append(b)
        right.append(btns)

        box = Gtk.Box()
        box.append(scroll)
        box.append(right)
        self.win.set_child(box)
        self.check()
        self.win.present()

    # черновик
    def as_theme(self):
        return {'set': self.set, 'wallpaper': self.wall, 'generate': self.generate, 'palette_data': self.pal}

    def put(self, **kv):
        self.set.update(kv)
        self.redraw()

    def redraw(self):
        self.preview.queue_draw()
        self.swatches.queue_draw()
        self.check()

    def check(self):
        bg, fg, muted = self.pal['bg'], self.pal['fg'], self.pal['muted']
        acc = self.pal.get(self.set['accent'], self.pal['yellow'])
        cr, cm, ca = contrast(fg, bg), contrast(muted, bg), contrast(acc, bg)
        warn = []
        if cr < 4.5:
            warn.append(T(f'Текст плохо читается на фоне (контраст {cr:.1f}, лучше от 4.5)', f'Text is hard to read on the background (contrast {cr:.1f}, aim for 4.5+)'))
        if cm < 2.5:
            warn.append(T(f'Приглушённый текст почти сливается с фоном ({cm:.1f})', f'Muted text almost blends into the background ({cm:.1f})'))
        if ca < 2:
            warn.append(T(f'Акцент плохо виден на фоне ({ca:.1f})', f'Accent is hard to see on the background ({ca:.1f})'))
        self.note.set_label('\n'.join(warn) if warn else T(f'Контраст текста {cr:.1f} — читается хорошо', f'Text contrast {cr:.1f}: easy to read'))

    def draw_swatches(self, _a, cr, w, h):
        keys = ['bg_dark', 'bg', 'surface', 'overlay', 'muted', 'fg', 'red', 'orange', 'yellow', 'green', 'cyan', 'blue', 'magenta']
        sw = w / len(keys)
        for i, k in enumerate(keys):
            cr.set_source_rgba(*rgbf(self.pal[k]))
            rrect(cr, i * sw + 1, 0, sw - 2, h, 4)
            cr.fill()
        acc = self.set['accent'] if self.set['accent'] in self.pal else 'yellow'
        i = keys.index(acc)
        cr.set_source_rgba(*rgbf(self.pal['fg']))
        cr.set_line_width(2)
        rrect(cr, i * sw + 2, 1, sw - 4, h - 2, 4)
        cr.stroke()

    def load_palette(self, pid):
        self.pal = rice.full_palette(rice.PALETTES[pid])
        for k, b in self.color_btns.items():
            b.set_rgba(to_rgba(self.pal[k]))
        self.redraw()

    # контролы черновика
    def color_item(self, key, title):
        dlg = Gtk.ColorDialog(with_alpha=False, title=title)
        b = Gtk.ColorDialogButton(dialog=dlg, rgba=to_rgba(self.pal[key]), valign=CENTER)

        def changed(w, _):
            h = to_hex(w.get_rgba())
            if h != self.pal.get(key):
                self.pal[key] = h
                self.redraw()

        b.connect('notify::rgba', changed)
        self.color_btns[key] = b
        box = Gtk.Box(spacing=8)
        box.append(b)
        box.append(lbl(title, valign=CENTER, hexpand=True))
        return box

    def sw(self, key):
        s = Gtk.Switch(active=bool(self.set[key]), valign=CENTER)
        s.connect('notify::active', lambda w, _: self.put(**{key: w.get_active()}))
        return s

    def dd(self, key, opts):
        vals = [v for v, _ in opts]
        d = Gtk.DropDown.new_from_strings([l for _, l in opts])
        if self.set[key] in vals:
            d.set_selected(vals.index(self.set[key]))
        d.connect('notify::selected', lambda w, _: self.put(**{key: vals[w.get_selected()]}))
        return d

    def scale(self, key, lo, hi, step, conv, fmt, digits=0):
        s = Gtk.Scale.new_with_range(H, lo, hi, step)
        s.set_value(self.set[key])
        s.set_digits(digits)
        s.set_draw_value(True)
        s.set_value_pos(Gtk.PositionType.LEFT)
        s.set_size_request(240, -1)
        s.set_format_value_func(lambda _s, v: fmt(v))
        s.connect('value-changed', lambda w: self.put(**{key: conv(round(w.get_value(), digits))}))
        return s

    # обои
    def wall_group(self):
        self.wall_flow = Gtk.FlowBox(selection_mode=Gtk.SelectionMode.NONE, max_children_per_line=4, min_children_per_line=2,
                                     column_spacing=6, row_spacing=6, homogeneous=True, margin_top=10, margin_start=10, margin_end=10)
        self.fill_walls()
        pick = Gtk.Button(label=T('Другой файл…', 'Other file…'))
        pick.connect('clicked', self.pick_file)
        foot = Gtk.Box(spacing=10, css_classes=['row'])
        self.wall_lbl = lbl(os.path.basename(self.wall) or T('не выбраны', 'none'), 'dim', hexpand=True, wrap=False, ellipsize=3)
        foot.append(self.wall_lbl)
        foot.append(pick)
        card = Gtk.Box(orientation=V, css_classes=['card'])
        card.append(self.wall_flow)
        card.append(foot)
        g = Gtk.Box(orientation=V, spacing=8)
        g.append(lbl(T('Обои', 'Wallpaper'), 'h2'))
        g.append(card)
        return g

    def fill_walls(self):
        while (c := self.wall_flow.get_first_child()):
            self.wall_flow.remove(c)
        files = sorted(os.path.join(rice.WALL_DIR, f) for f in os.listdir(rice.WALL_DIR)
                       if f.lower().endswith(IMG_EXT)) if os.path.isdir(rice.WALL_DIR) else []
        cur = os.path.realpath(os.path.expanduser(self.wall)) if self.wall else ''
        if cur and cur not in [os.path.realpath(f) for f in files] and os.path.isfile(cur):
            files.insert(0, cur)
        for f in files:
            th = thumb(f)
            if not th:
                continue
            pic = Gtk.Picture.new_for_filename(th)
            pic.set_can_shrink(True)
            pic.set_size_request(110, 62)
            b = Gtk.Button(child=pic, css_classes=['wall'] + (['on'] if os.path.realpath(f) == cur else []), tooltip_text=os.path.basename(f))
            b.connect('clicked', lambda _b, f=f: self.set_wall(f))
            self.wall_flow.append(b)

    def set_wall(self, f):
        self.wall = f
        self.generate = None
        self.wall_lbl.set_label(os.path.basename(f))
        self.fill_walls()
        self.redraw()

    def pick_file(self, *_):
        dlg = Gtk.FileDialog(title=T('Выбери обои', 'Choose a wallpaper'))
        flt = Gtk.FileFilter(name=T('Картинки', 'Images'))
        for e in IMG_EXT:
            flt.add_suffix(e.lstrip('.'))
        store = Gio.ListStore.new(Gtk.FileFilter)
        store.append(flt)
        dlg.set_filters(store)

        def done(d, res):
            try:
                f = d.open_finish(res)
            except GLib.Error:
                return
            if f and f.get_path():
                self.set_wall(f.get_path())

        dlg.open(self.win, None, done)

    # сохранение
    def save(self, apply):
        name = self.name.get_text().strip()
        if not name:
            self.note.set_label(T('Дай теме название — без него не сохранить', 'Give the theme a name first'))
            self.name.grab_focus()
            return
        tid = rice.save_custom_theme(name, self.desc.get_text().strip(), self.pal, self.set, self.wall, self.tid)
        self.tid = tid
        app = self.app
        if apply:
            app.worker.submit(lambda: rice.apply_theme(tid))
            app.after.append(app.rebuild)
        elif app.win:
            app.rebuild()
        self.win.close()


if __name__ == '__main__':
    sys.exit(App().run([sys.argv[0]]))
