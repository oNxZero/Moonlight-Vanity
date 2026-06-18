import gi
import os
import tempfile
import time
import subprocess
import sys
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Gtk, Adw, GLib, Gdk

from click_sounds import list_sound_packs, ClickSoundPlayer

MOON_SVG_TEMPLATE = """<?xml version="1.0" encoding="UTF-8"?>
<svg width="64px" height="64px" viewBox="0 0 24 24" version="1.1" xmlns="http://www.w3.org/2000/svg">
    <path d="M12.0000002,2.0000002 C12.2855146,2.0000002 12.5649479,2.02237834 12.8373396,2.06546059 C8.97157672,2.67699175 6.00000016,6.02897621 6.00000016,10 C6.00000016,14.4182782 9.58172216,18.0000002 14.0000002,18.0000002 C17.9710241,18.0000002 21.3230086,15.0284236 21.9345398,11.1626607 C21.9776221,11.4350524 22.0000002,11.7144857 22.0000002,12.0000002 C22.0000002,17.5228477 17.5228477,22.0000002 12.0000002,22.0000002 C6.47715266,22.0000002 2.00000016,17.5228477 2.00000016,12.0000002 C2.00000016,6.47715266 6.47715266,2.0000002 12.0000002,2.0000002 Z" fill="{0}" stroke="none"></path>
</svg>
"""

class MainWindow(Adw.ApplicationWindow):
    def __init__(self, app, backend_toggle, backend_config, backend_suspend, listener, initial_config, preset_manager, theme_cb, preset_cb):
        super().__init__(application=app, title="Moonlight")

        self.set_default_size(780, 720)
        self.set_resizable(False)

        self.backend_toggle = backend_toggle
        self._backend_config_func = backend_config
        self.backend_suspend = backend_suspend
        self.listener = listener
        self.preset_mgr = preset_manager
        self.theme_cb = theme_cb
        self.preset_cb = preset_cb

        loaded_default = self.preset_mgr.load_preset("Default")
        self.cfg = loaded_default if loaded_default else initial_config

        self.active_preset_name = "Default"
        self.color_buttons = {}

        self.sliders_map = {}
        self.sound_preview = ClickSoundPlayer()
        self._updating_sound_pack = False
        self.last_focus_time = 0
        self.is_binding = False
        self.last_bind_time = 0

        self.connect("notify::is-active", self.on_window_focus_change)

        self.mouse_blocker = Gtk.GestureClick()
        self.mouse_blocker.set_button(0)
        self.mouse_blocker.set_propagation_phase(Gtk.PropagationPhase.CAPTURE)
        self.mouse_blocker.connect("pressed", self.on_mouse_block_press)
        self.mouse_blocker.connect("released", self.on_mouse_block_release)
        self.add_controller(self.mouse_blocker)

        root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.set_content(root)

        self.header = Adw.HeaderBar()
        self.header.set_show_end_title_buttons(False)
        self.header.set_show_start_title_buttons(False)

        self.box_header_left = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)

        self.btn_menu = Gtk.Button(icon_name="emblem-system-symbolic")
        self.btn_menu.set_css_classes(["win-ctrl"])
        self.btn_menu.connect("clicked", lambda x: self.navigate_to("settings"))

        self.btn_back = Gtk.Button(icon_name="go-previous-symbolic")
        self.btn_back.set_css_classes(["win-ctrl"])
        self.btn_back.set_visible(False)
        self.btn_back.connect("clicked", lambda x: self.navigate_to("home"))

        self.box_header_left.append(self.btn_back)
        self.box_header_left.append(self.btn_menu)
        self.header.pack_start(self.box_header_left)

        self.lbl_title = Gtk.Label(label="Moonlight")
        self.lbl_title.set_css_classes(["title-label"])
        self.header.set_title_widget(self.lbl_title)

        box_win_ctrl = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
        btn_min = Gtk.Button(icon_name="window-minimize-symbolic")
        btn_min.set_css_classes(["win-ctrl"])
        btn_min.set_focusable(False)
        btn_min.connect("clicked", lambda x: self.minimize())

        btn_close = Gtk.Button(icon_name="window-close-symbolic")
        btn_close.set_css_classes(["win-ctrl", "close"])
        btn_close.set_focusable(False)
        btn_close.connect("clicked", lambda x: app.quit())

        box_win_ctrl.append(btn_min)
        box_win_ctrl.append(btn_close)
        self.header.pack_end(box_win_ctrl)
        root.append(self.header)

        self.stack = Gtk.Stack()
        self.stack.set_transition_type(Gtk.StackTransitionType.SLIDE_LEFT_RIGHT)
        self.stack.set_transition_duration(300)

        self.page_home = self.build_home_page()
        self.stack.add_named(self.page_home, "home")

        self.page_settings = self.build_settings_page()
        self.stack.add_named(self.page_settings, "settings")

        root.append(self.stack)

        self.update_ui_from_config(self.cfg)

        base_theme = self.preset_mgr.active_theme_name
        self.theme_cb(base_theme, is_custom=False)

        for key, val in self.preset_mgr.custom_overrides.items():
            self.theme_cb(key, is_custom=True, color_val=val)

        self.refresh_color_pickers()
        self.update_logo_visuals()

    def update_config(self, new_data):
        self.cfg.update(new_data)
        self._backend_config_func(new_data)
        if self.stack.get_visible_child_name() == "settings":
            self.refresh_presets()

    def navigate_to(self, page):
        if page == "settings":
            self.refresh_presets()
            self.refresh_color_pickers()

        self.stack.set_visible_child_name(page)

        if page == "home":
            self.btn_back.set_visible(False)
            self.btn_menu.set_visible(True)
            self.lbl_title.set_label("Moonlight")
        else:
            self.btn_menu.set_visible(False)
            self.btn_back.set_visible(True)
            self.lbl_title.set_label("Settings")

    def build_home_page(self):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)

        hero = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=24)
        hero.set_css_classes(["card", "hero-card"])

        self.tmp_icon = tempfile.NamedTemporaryFile(suffix=".svg", delete=False)
        self.tmp_icon.close()

        self.icon_status = Gtk.Image()
        self.icon_status.set_pixel_size(64)
        self.icon_status.set_css_classes(["icon-pulse"])
        hero.append(self.icon_status)

        vbox_st = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        vbox_st.set_valign(Gtk.Align.CENTER)
        self.lbl_status = Gtk.Label(label="DISABLED", xalign=0)
        self.lbl_status.set_css_classes(["h1"])
        self.lbl_sub = Gtk.Label(label="Waiting for input...", xalign=0)
        self.lbl_sub.set_css_classes(["dim"])
        vbox_st.append(self.lbl_status)
        vbox_st.append(self.lbl_sub)
        hero.append(vbox_st)

        self.box_master = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
        self.box_master.set_valign(Gtk.Align.CENTER)
        self.box_master.set_halign(Gtk.Align.END)
        self.box_master.set_hexpand(True)
        self.box_master.set_css_classes(["segmented-box", "master-box", "pos-left"])
        self.box_master.set_homogeneous(True)
        self.btn_master_off = Gtk.ToggleButton(label="OFF")
        self.btn_master_off.set_css_classes(["segment-btn"])
        self.btn_master_off.set_active(True)
        self.btn_master_off.set_focusable(False)
        self.btn_master_off.connect("toggled", self.on_master_toggled)
        self.btn_master_on = Gtk.ToggleButton(label="ON")
        self.btn_master_on.set_css_classes(["segment-btn"])
        self.btn_master_on.set_group(self.btn_master_off)
        self.btn_master_on.set_focusable(False)
        self.box_master.append(self.btn_master_off)
        self.box_master.append(self.btn_master_on)
        self.sw_shield = Gtk.GestureClick()
        self.sw_shield.set_propagation_phase(Gtk.PropagationPhase.CAPTURE)
        self.sw_shield.connect("pressed", self.on_switch_click_attempt)
        self.box_master.add_controller(self.sw_shield)
        hero.append(self.box_master)
        box.append(hero)

        card_act = self.create_card("ACTIVATION")

        self.seg_trig = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
        self.seg_trig.set_css_classes(["segmented-box", "pos-left"])
        self.seg_trig.set_homogeneous(True)
        self.btn_trig_tog = Gtk.ToggleButton(label="Toggle")
        self.btn_trig_tog.set_css_classes(["segment-btn"])

        if self.cfg.get('trigger_mode') == 'hold':
            self.btn_trig_tog.set_active(False)
            self.seg_trig.add_css_class("pos-right")
            self.seg_trig.remove_css_class("pos-left")
        else:
            self.btn_trig_tog.set_active(True)
            self.seg_trig.add_css_class("pos-left")
            self.seg_trig.remove_css_class("pos-right")

        self.btn_trig_tog.set_focusable(False)
        self.btn_trig_tog.connect("toggled", self.on_trig_mode_changed)
        self.btn_trig_hold = Gtk.ToggleButton(label="Hold")
        self.btn_trig_hold.set_css_classes(["segment-btn"])
        self.btn_trig_hold.set_group(self.btn_trig_tog)
        self.btn_trig_hold.set_focusable(False)
        self.seg_trig.append(self.btn_trig_tog)
        self.seg_trig.append(self.btn_trig_hold)
        card_act.append(self.create_control_row("Trigger Type", self.seg_trig))
        card_act.append(self.create_sep())

        self.row_bind_left = self.create_bind_row("Left Click Trigger", "trigger_left", self.cfg.get('trigger_left', 64))
        card_act.append(self.row_bind_left)

        self.row_bind_right = self.create_bind_row("Right Click Trigger", "trigger_right", self.cfg.get('trigger_right', 65))
        card_act.append(self.row_bind_right)
        box.append(card_act)

        self.card_conf = self.create_card("CONFIGURATION")

        cps_grid = Gtk.Grid(column_spacing=24, row_spacing=0)
        cps_grid.set_column_homogeneous(True)
        self.box_cps_left, self.lbl_cps_left = self.add_slider(cps_grid, "Left Click CPS", 1.0, 20.0, self.cfg.get('cps_left', 12.0), 0.5, lambda v: self.update_config({'cps_left': v}), 'cps_left')
        self.box_cps_right, self.lbl_cps_right = self.add_slider(cps_grid, "Right Click CPS", 1.0, 20.0, self.cfg.get('cps_right', 12.0), 0.5, lambda v: self.update_config({'cps_right': v}), 'cps_right')
        self.box_cps_left.set_hexpand(True)
        self.box_cps_right.set_hexpand(True)
        cps_grid.attach(self.box_cps_left, 0, 0, 1, 1)
        cps_grid.attach(self.box_cps_right, 1, 0, 1, 1)
        self.card_conf.append(cps_grid)
        self.card_conf.append(self.create_sep())

        self.sep_jitter = self.create_sep()
        self.box_jitter, _ = self.add_slider(self.card_conf, "Jitter Strength", 0.0, 10.0, self.cfg.get('jitter', 2.0), 0.5, lambda v: self.update_config({'jitter': v}), 'jitter')
        self.card_conf.append(self.sep_jitter)

        self.seg_rand = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
        self.seg_rand.set_css_classes(["segmented-box", "pos-left"])
        self.seg_rand.set_homogeneous(True)
        self.btn_legit = Gtk.ToggleButton(label="Legit")
        self.btn_legit.set_css_classes(["segment-btn"])

        if self.cfg.get('rand') == 2:
            self.btn_legit.set_active(False)
            self.seg_rand.add_css_class("pos-right")
            self.seg_rand.remove_css_class("pos-left")
        else:
            self.btn_legit.set_active(True)
            self.seg_rand.add_css_class("pos-left")
            self.seg_rand.remove_css_class("pos-right")

        self.btn_legit.set_focusable(False)
        self.btn_legit.connect("toggled", self.on_human_toggled)
        self.btn_blatant = Gtk.ToggleButton(label="Blatant")
        self.btn_blatant.set_css_classes(["segment-btn"])
        self.btn_blatant.set_group(self.btn_legit)
        self.btn_blatant.set_focusable(False)
        self.seg_rand.append(self.btn_legit)
        self.seg_rand.append(self.btn_blatant)
        self.card_conf.append(self.create_control_row("Humanization", self.seg_rand))
        self.card_conf.append(self.create_sep())

        self.sw_sounds = Gtk.Switch()
        self.sw_sounds.set_active(self.cfg.get('click_sounds', True))
        self.sw_sounds.set_valign(Gtk.Align.CENTER)
        self.sw_sounds.connect("notify::active", lambda w, p: self._sync_sound_config(preview=True))
        self.card_conf.append(self.create_control_row("Click Sounds", self.sw_sounds, control_width=0))

        self.sound_packs = list_sound_packs()
        pack_model = Gtk.StringList()
        for pack_name in self.sound_packs:
            pack_model.append(pack_name)
        self.dd_sound_pack = Gtk.DropDown(model=pack_model)
        self.dd_sound_pack.set_valign(Gtk.Align.CENTER)
        saved_pack = self.cfg.get('click_sound_pack', self.sound_packs[0])
        if saved_pack in self.sound_packs:
            self._updating_sound_pack = True
            self.dd_sound_pack.set_selected(self.sound_packs.index(saved_pack))
            self._updating_sound_pack = False
        self.dd_sound_pack.connect("notify::selected", self.on_sound_pack_changed)
        self.card_conf.append(self.create_control_row("Sound Pack", self.dd_sound_pack))

        self.add_slider(self.card_conf, "Sound Volume %", 0, 100, self.cfg.get('click_sound_volume', 80.0), 5, lambda v: self._sync_sound_config(), 'click_sound_volume')
        self.card_conf.append(self.create_sep())

        self.row_hide = self.create_bind_row("Hide Window Key", "hide", self.cfg.get('hide_key', 54))
        self.btn_hide = self.row_hide.get_last_child()
        self.card_conf.append(self.row_hide)
        self.card_conf.set_margin_bottom(8)
        box.append(self.card_conf)
        return box

    def build_settings_page(self):
        scroll = Gtk.ScrolledWindow()
        scroll.set_vexpand(True)

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=20)
        box.set_margin_top(24)
        box.set_margin_bottom(24)
        box.set_margin_start(36)
        box.set_margin_end(36)

        hbox_cfg_h = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        lbl_cfg = Gtk.Label(label="CONFIGURATIONS", xalign=0)
        lbl_cfg.set_css_classes(["h2"])

        btn_open_cfg = Gtk.Button(icon_name="folder-open-symbolic")
        btn_open_cfg.set_css_classes(["icon-btn"])
        btn_open_cfg.set_tooltip_text("Open Config Folder")
        btn_open_cfg.connect("clicked", lambda x: self.on_open_folder(self.preset_mgr.preset_dir))

        hbox_cfg_h.append(lbl_cfg)
        hbox_cfg_h.append(btn_open_cfg)
        box.append(hbox_cfg_h)

        input_card = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        input_card.set_css_classes(["create-config-box", "anim-enter"])

        self.entry_preset = Gtk.Entry(placeholder_text="Create new config...")
        self.entry_preset.set_hexpand(True)
        btn_save = Gtk.Button(label="Create")
        btn_save.set_css_classes(["trigger-btn", "zoom-in-anim"])
        btn_save.connect("clicked", self.on_preset_save)

        input_card.append(self.entry_preset)
        input_card.append(btn_save)
        box.append(input_card)

        self.list_frame = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.list_frame.set_css_classes(["card", "nopad", "anim-enter-delay"])

        self.list_presets = Gtk.ListBox()
        self.list_presets.set_selection_mode(Gtk.SelectionMode.NONE)
        self.list_presets.set_css_classes(["boxed-list"])
        self.refresh_presets()

        self.list_frame.append(self.list_presets)
        box.append(self.list_frame)

        box.append(self.create_sep())

        hbox_th_h = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        lbl_th = Gtk.Label(label="THEME GALLERY", xalign=0)
        lbl_th.set_css_classes(["h2"])

        btn_open_th = Gtk.Button(icon_name="folder-open-symbolic")
        btn_open_th.set_css_classes(["icon-btn"])
        btn_open_th.set_tooltip_text("Open Theme Folder")
        btn_open_th.connect("clicked", lambda x: self.on_open_folder(self.preset_mgr.theme_dir))

        hbox_th_h.append(lbl_th)
        hbox_th_h.append(btn_open_th)
        box.append(hbox_th_h)

        theme_card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16)
        theme_card.set_css_classes(["card", "anim-enter-delay-2"])

        grid = Gtk.FlowBox()
        grid.set_valign(Gtk.Align.START)
        grid.set_max_children_per_line(3)
        grid.set_selection_mode(Gtk.SelectionMode.NONE)
        grid.set_column_spacing(10)
        grid.set_row_spacing(10)

        available_themes = self.preset_mgr.get_available_themes()
        for filename, display_name in available_themes:
            btn = Gtk.Button(label=display_name)
            btn.set_css_classes(["trigger-btn"])
            btn.connect("clicked", lambda b, n=filename: self.on_theme_preset_clicked(n))
            grid.append(btn)

        theme_card.append(grid)
        box.append(theme_card)

        lbl_c = Gtk.Label(label="VISUAL OVERRIDES", xalign=0)
        lbl_c.set_css_classes(["h2"])
        box.append(lbl_c)

        override_card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16)
        override_card.set_css_classes(["card", "anim-enter-delay-2"])

        cols = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=24)
        cols.set_homogeneous(True)

        col1 = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        col1.append(self.create_color_row("Base", "base"))
        col1.append(self.create_color_row("Mantle", "mantle"))
        col1.append(self.create_color_row("Crust", "crust"))
        col1.append(self.create_color_row("Logo", "logo"))
        col1.append(self.create_color_row("Switch", "switch_bg"))

        col2 = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        col2.append(self.create_color_row("Surface 1", "surface0"))
        col2.append(self.create_color_row("Surface 2", "surface1"))
        col2.append(self.create_color_row("Text", "text"))
        col2.append(self.create_color_row("Title", "title"))
        col2.append(self.create_color_row("Subtext", "subtext"))

        col3 = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        col3.append(self.create_color_row("Accent", "blue"))
        col3.append(self.create_color_row("Slider", "slider"))
        col3.append(self.create_color_row("Handle", "handle"))
        col3.append(self.create_color_row("Outline", "outline"))
        col3.append(self.create_color_row("Shadow", "shadow"))

        cols.append(col1)
        cols.append(col2)
        cols.append(col3)
        override_card.append(cols)

        box.append(override_card)
        scroll.set_child(box)

        self.refresh_color_pickers()

        return scroll

    def on_open_folder(self, path):
        try:
            if sys.platform == 'win32':
                os.startfile(path)
            else:
                subprocess.Popen(['xdg-open', path])
        except Exception as e:
            print(f"Failed to open folder: {e}")

    def on_theme_preset_clicked(self, name):
        self.theme_cb(name, is_custom=False)
        self.refresh_color_pickers()
        self.update_logo_visuals()
        self.refresh_presets()

    def create_color_row(self, title, key):
        row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        lbl = Gtk.Label(label=title, xalign=0, hexpand=True)
        lbl.add_css_class("dim")

        btn = Gtk.ColorButton()
        btn.set_css_classes(["zoom-in-anim", "color-override-btn"])
        btn.connect("color-set", lambda b: self.on_color_set(b, key))

        self.color_buttons[key] = btn

        row.append(lbl)
        row.append(btn)
        return row

    def refresh_color_pickers(self):
        theme = self.preset_mgr.get_active_theme()
        if not theme: return

        for key, btn in self.color_buttons.items():
            if key in theme:
                c_str = theme[key]
                if not c_str: continue
                if not c_str.startswith("#"): c_str = "#" + c_str

                c = Gdk.RGBA()
                if c.parse(c_str):
                    btn.set_rgba(c)
                else:
                    fallback = Gdk.RGBA()
                    fallback.parse("#FFFFFF")
                    btn.set_rgba(fallback)

    def update_logo_visuals(self):
        theme = self.preset_mgr.get_active_theme()
        logo_color = theme.get('logo', '#8caaee')

        try:
            with open(self.tmp_icon.name, 'w') as f:
                f.write(MOON_SVG_TEMPLATE.format(logo_color))

            self.icon_status.set_from_file(self.tmp_icon.name)
        except Exception as e:
            print(f"Error updating logo: {e}")

    def on_color_set(self, btn, key):
        rgba = btn.get_rgba()
        r, g, b = int(rgba.red*255), int(rgba.green*255), int(rgba.blue*255)
        hex_val = f"#{r:02x}{g:02x}{b:02x}"
        self.theme_cb(key, is_custom=True, color_val=hex_val)
        self.refresh_presets()
        if key == 'logo':
            self.update_logo_visuals()

    def refresh_presets(self):
        while child := self.list_presets.get_first_child():
            self.list_presets.remove(child)

        presets = self.preset_mgr.get_presets()
        for p in presets:
            row = Gtk.ListBoxRow()
            row.set_css_classes(["boxed-row"])

            if p == self.active_preset_name:
                row.add_css_class("selected-row")

            hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
            hbox.set_margin_top(8)
            hbox.set_margin_bottom(8)
            hbox.set_margin_start(12)
            hbox.set_margin_end(12)

            lbl = Gtk.Label(label=p, xalign=0, hexpand=True)
            lbl.set_css_classes(["h2-text"])

            btn_save = Gtk.Button(icon_name="document-save-symbolic")
            btn_save.set_css_classes(["icon-btn", "zoom-in-anim"])

            is_modified = self.preset_mgr.check_modification(p, self.cfg)
            if not is_modified:
                btn_save.set_sensitive(False)
                btn_save.set_opacity(0.3)
            else:
                btn_save.connect("clicked", lambda b, n=p: self.on_preset_save_existing(n))

            btn_load = Gtk.Button(icon_name="media-playback-start-symbolic")
            btn_load.set_css_classes(["icon-btn", "zoom-in-anim"])

            if p == self.active_preset_name:
                btn_load.set_sensitive(False)
                btn_load.set_opacity(0.3)
            else:
                btn_load.connect("clicked", lambda b, n=p: self.on_preset_load(n))

            if p == "Default":
                btn_reset = Gtk.Button(icon_name="view-refresh-symbolic")
                btn_reset.set_css_classes(["icon-btn", "zoom-in-anim"])

                is_def_mod = self.preset_mgr.is_default_modified(self.cfg)
                if not is_def_mod:
                    btn_reset.set_sensitive(False)
                    btn_reset.set_opacity(0.3)
                else:
                    btn_reset.connect("clicked", self.on_preset_reset)

                hbox.append(lbl)
                hbox.append(btn_save)
                hbox.append(btn_load)
                hbox.append(btn_reset)
            else:
                btn_del = Gtk.Button(icon_name="user-trash-symbolic")
                btn_del.set_css_classes(["icon-btn", "destructive", "zoom-in-anim"])
                btn_del.connect("clicked", lambda b, n=p: self.on_preset_delete(n))
                hbox.append(lbl)
                hbox.append(btn_save)
                hbox.append(btn_load)
                hbox.append(btn_del)

            row.set_child(hbox)
            self.list_presets.append(row)

    def on_preset_save(self, btn):
        name = self.entry_preset.get_text()
        status = self.preset_mgr.save_preset(name, self.cfg, check_exists=True)

        if status == "success":
            self.entry_preset.set_text("")
            self.entry_preset.set_placeholder_text("Create new config...")
            self.entry_preset.remove_css_class("error")
            self.active_preset_name = name
            self.refresh_presets()
        elif status == "empty":
            self.trigger_error("Name cannot be empty!")
        elif status == "duplicate":
            self.trigger_error("Name already exists!")

    def trigger_error(self, msg):
        self.entry_preset.set_text("")
        self.entry_preset.set_placeholder_text(msg)
        self.entry_preset.add_css_class("error")
        self.entry_preset.add_css_class("shake-anim")

        GLib.timeout_add(500, lambda: self.entry_preset.remove_css_class("shake-anim"))
        GLib.timeout_add(1000, lambda: self.entry_preset.remove_css_class("error"))
        GLib.timeout_add(1000, lambda: self.entry_preset.set_placeholder_text("Create new config..."))

    def on_preset_save_existing(self, name):
        if self.preset_mgr.save_preset(name, self.cfg, check_exists=False) == "success":
            if name == "Default":
                # Persist the full active runtime config when Default is overwritten.
                clean_cfg = {k: v for k, v in self.cfg.items() if k != '_theme_config'}
                self.update_config(clean_cfg)
            self.active_preset_name = name
            self.refresh_presets()

    def on_preset_load(self, name):
        cfg = self.preset_cb("load", name)
        if cfg:
            self.active_preset_name = name
            self.update_ui_from_config(cfg)
            self.refresh_presets()
            self.refresh_color_pickers()
            self.update_logo_visuals()

    def on_preset_reset(self, btn):
        self.preset_mgr.reset_preset("Default")
        self.on_preset_load("Default")

    def on_preset_delete(self, name):
        self.preset_cb("delete", name)
        if self.active_preset_name == name:
            self.on_preset_load("Default")
        else:
            self.refresh_presets()

    def _get_selected_sound_pack(self):
        item = self.dd_sound_pack.get_selected_item()
        if item is not None:
            return item.get_string()
        idx = self.dd_sound_pack.get_selected()
        if idx != Gtk.INVALID_LIST_POSITION and idx < len(self.sound_packs):
            return self.sound_packs[idx]
        return self.sound_packs[0]

    def _sync_sound_config(self, preview=False):
        payload = {
            'click_sounds': self.sw_sounds.get_active(),
            'click_sound_volume': self.sliders_map['click_sound_volume'].get_value(),
            'click_sound_pack': self._get_selected_sound_pack(),
        }
        self.update_config(payload)
        if preview and payload['click_sounds']:
            self.sound_preview.configure(
                enabled=True,
                volume=payload['click_sound_volume'],
                pack=payload['click_sound_pack'],
            )
            self.sound_preview.play()

    def on_sound_pack_changed(self, dropdown, _prop):
        if self._updating_sound_pack:
            return
        pack = self._get_selected_sound_pack()
        if pack == self.cfg.get('click_sound_pack'):
            return
        self._sync_sound_config(preview=True)

    def create_control_row(self, title, widget, control_width=200):
        row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        row.set_css_classes(["control-row"])
        lbl = Gtk.Label(label=title, xalign=0, hexpand=True)
        lbl.set_css_classes(["row-label"])
        widget.set_valign(Gtk.Align.CENTER)
        widget.set_halign(Gtk.Align.END)
        if control_width:
            widget.set_size_request(control_width, -1)
        row.append(lbl)
        row.append(widget)
        return row

    def create_card(self, title):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        box.set_css_classes(["card"])
        lbl = Gtk.Label(label=title, xalign=0)
        lbl.set_css_classes(["h2"])
        box.append(lbl)
        return box

    def create_sep(self):
        sep = Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL)
        sep.set_css_classes(["white-sep"])
        sep.set_margin_top(4)
        sep.set_margin_bottom(4)
        return sep

    def add_slider(self, parent, title, min_v, max_v, def_v, step, callback, cfg_key=None):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=3)
        head = Gtk.Box()
        t = Gtk.Label(label=title, xalign=0, hexpand=True)
        v = Gtk.Label(label=f"{def_v:.1f}")
        v.set_css_classes(["accent"])
        head.append(t)
        head.append(v)
        box.append(head)
        adj = Gtk.Adjustment(value=def_v, lower=min_v, upper=max_v, step_increment=step, page_increment=step)
        scale = Gtk.Scale(orientation=Gtk.Orientation.HORIZONTAL, adjustment=adj)
        scale.set_digits(1)
        scale.set_round_digits(1)
        def _cb(s):
            raw = s.get_value()
            snapped = round(raw / step) * step
            if abs(raw - snapped) > 0.01: s.set_value(snapped)
            v.set_label(f"{snapped:.1f}")
            callback(snapped)
        scale.connect("value-changed", _cb)
        box.append(scale)
        parent.append(box)
        if cfg_key: self.sliders_map[cfg_key] = scale
        return box, t

    def create_bind_row(self, title, mode, code):
        row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        row.set_css_classes(["control-row"])
        lbl = Gtk.Label(label=title, xalign=0, hexpand=True)
        lbl.set_css_classes(["row-label"])

        name = self.listener.get_nice_name(code)
        btn = Gtk.Button(label=name)
        btn.set_css_classes(["trigger-btn"])
        btn.set_halign(Gtk.Align.END)
        btn.set_size_request(200, -1)
        btn.connect("clicked", lambda x: self.on_bind_click(mode))

        if mode == "trigger_left":
            self.lbl_bind_left = lbl
            self.btn_bind_left = btn
        elif mode == "trigger_right":
            self.lbl_bind_right = lbl
            self.btn_bind_right = btn

        row.append(lbl)
        row.append(btn)
        return row

    def update_ui_from_config(self, cfg):
        self.cfg.update(cfg)
        for key, scale in self.sliders_map.items():
            if key in cfg: scale.set_value(float(cfg[key]))

        if 'click_sounds' in cfg:
            self.sw_sounds.set_active(cfg['click_sounds'])
        if 'click_sound_pack' in cfg and cfg['click_sound_pack'] in self.sound_packs:
            self._updating_sound_pack = True
            self.dd_sound_pack.set_selected(self.sound_packs.index(cfg['click_sound_pack']))
            self._updating_sound_pack = False

        if 'trigger_left' in cfg:
            self.listener.trigger_left = cfg['trigger_left']
            self.btn_bind_left.set_label(self.listener.get_nice_name(cfg['trigger_left']))
        if 'trigger_right' in cfg:
            self.listener.trigger_right = cfg['trigger_right']
            self.btn_bind_right.set_label(self.listener.get_nice_name(cfg['trigger_right']))
        if 'hide_key' in cfg:
            self.listener.hide_key = cfg['hide_key']
            self.btn_hide.set_label(self.listener.get_nice_name(cfg['hide_key']))

        if 'rand' in cfg:
            is_legit = (cfg['rand'] == 1)
            self.btn_legit.set_active(is_legit)
            self.btn_blatant.set_active(not is_legit)

        if 'trigger_mode' in cfg:
            is_tog = (cfg['trigger_mode'] == 'toggle')
            self.listener.set_trigger_mode(cfg['trigger_mode'])
            self.btn_trig_tog.set_active(is_tog)
            self.btn_trig_hold.set_active(not is_tog)

        clean_cfg = {k: v for k, v in cfg.items() if k != '_theme_config'}
        self.update_config(clean_cfg)

    def on_window_focus_change(self, win, _):
        is_focused = win.get_property("is-active")
        if is_focused: self.last_focus_time = time.time()
        self.listener.set_paused(is_focused)
        self.backend_suspend(is_focused)

    def on_switch_click_attempt(self, gesture, n_press, x, y):
        if time.time() - self.last_focus_time < 0.2:
            gesture.set_state(Gtk.EventSequenceState.CLAIMED)

    def on_mouse_block_press(self, gesture, n_press, x, y):
        btn = gesture.get_current_button()
        if btn > 3:
            gesture.set_state(Gtk.EventSequenceState.CLAIMED)
            return True

    def on_mouse_block_release(self, gesture, n_press, x, y):
        btn = gesture.get_current_button()
        if btn > 3:
            gesture.set_state(Gtk.EventSequenceState.CLAIMED)
            return True

    def on_master_toggled(self, btn):
        is_on = not self.btn_master_off.get_active()
        self.update_master_visuals(is_on)
        self.backend_toggle(is_on, 'left')
        if not is_on: self.backend_toggle(False, 'right')

    def update_master_visuals(self, active):
        if active:
            self.box_master.add_css_class("pos-right")
            self.box_master.remove_css_class("pos-left")
            self.lbl_status.set_label("ENABLED")
            self.lbl_status.add_css_class("status-active")
            self.icon_status.add_css_class("active")
            self.lbl_sub.set_label("Injecting input stream...")
            if not self.btn_master_on.get_active(): self.btn_master_on.set_active(True)
        else:
            self.box_master.add_css_class("pos-left")
            self.box_master.remove_css_class("pos-right")
            self.lbl_status.set_label("DISABLED")
            self.lbl_status.remove_css_class("status-active")
            self.icon_status.remove_css_class("active")
            self.lbl_sub.set_label("Waiting for input...")
            if not self.btn_master_off.get_active(): self.btn_master_off.set_active(True)

    def set_active_visuals(self, active_left, active_right):
        self.btn_master_off.handler_block_by_func(self.on_master_toggled)
        self.update_master_visuals(active_left or active_right)
        self.btn_master_off.handler_unblock_by_func(self.on_master_toggled)

    def on_trig_mode_changed(self, btn):
        mode = "toggle" if self.btn_trig_tog.get_active() else "hold"
        self.listener.set_trigger_mode(mode)
        self.update_config({'trigger_mode': mode})

        if mode == "toggle":
            self.seg_trig.add_css_class("pos-left")
            self.seg_trig.remove_css_class("pos-right")
        else:
            self.seg_trig.add_css_class("pos-right")
            self.seg_trig.remove_css_class("pos-left")

    def on_human_toggled(self, btn):
        lvl = 1 if self.btn_legit.get_active() else 2
        self.update_config({'rand': lvl})

        if lvl == 1:
            self.seg_rand.add_css_class("pos-left")
            self.seg_rand.remove_css_class("pos-right")
        else:
            self.seg_rand.add_css_class("pos-right")
            self.seg_rand.remove_css_class("pos-left")

    def on_bind_click(self, mode):
        if self.is_binding: return
        if time.time() - self.last_bind_time < 0.5: return
        self.is_binding = True
        btn = None
        if mode == "trigger_left": btn = self.btn_bind_left
        elif mode == "trigger_right": btn = self.btn_bind_right
        elif mode == "hide": btn = self.btn_hide
        if btn: btn.set_label("Press Button / Key")
        self.listener.start_rebind(mode)

    def update_bind_label(self, label, code, mode):
        self.is_binding = False
        self.last_bind_time = time.time()
        btn = None
        if mode == "trigger_left":
            btn = self.btn_bind_left
            self.cfg['trigger_left'] = code
        elif mode == "trigger_right":
            btn = self.btn_bind_right
            self.cfg['trigger_right'] = code
        elif mode == "hide":
            btn = self.btn_hide
            self.cfg['hide_key'] = code
        if btn: btn.set_label(label)
        self.refresh_presets()
