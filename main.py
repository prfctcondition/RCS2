import sys, time, os, json
import win32api, win32con
from PyQt5.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout,
                             QLabel, QDoubleSpinBox, QPushButton, QDialog,
                             QTableWidget, QTableWidgetItem, QHeaderView)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal, QObject
from pynput import mouse

from data.config_repository import ConfigRepository, CSVRepository
from core.services.config_service import ConfigService
from core.services.input_service import InputService
from core.services.recoil_service import RecoilService
from core.services.gsi_service import GSIService
from core.services.weapon_detection_service import WeaponDetectionService
from core.services.autostop_service import AutoStopService


KEYBINDS_FILE = "keybinds.json"
TOGGLE_RCS_KEY = "__toggle_rcs__"


class KeybindSignalEmitter(QObject):
    weapon_selected = pyqtSignal(str)
    toggle_rcs_triggered = pyqtSignal()


class KeybindManager:
    def __init__(self, weapon_callback, toggle_rcs_callback):
        self.keybinds = {}
        self.reverse_keybinds = {}
        self.mouse_listener = None
        self.emitter = KeybindSignalEmitter()
        self.emitter.weapon_selected.connect(weapon_callback)
        self.emitter.toggle_rcs_triggered.connect(toggle_rcs_callback)

        self.poll_timer = QTimer()
        self.poll_timer.timeout.connect(self._poll_keyboard)
        self._pressed_keys = set()

        self.load_keybinds()

    def load_keybinds(self):
        if os.path.exists(KEYBINDS_FILE):
            try:
                with open(KEYBINDS_FILE, "r", encoding="utf-8") as f:
                    self.keybinds = json.load(f)
            except Exception as e:
                print(f"Failed to load keybinds: {e}")
                self.keybinds = {}
        else:
            self.keybinds = {}
        self._update_reverse_map()

    def save_keybinds(self):
        try:
            with open(KEYBINDS_FILE, "w", encoding="utf-8") as f:
                json.dump(self.keybinds, f, indent=4, ensure_ascii=False)
        except Exception as e:
            print(f"Failed to save keybinds: {e}")

    def set_keybind(self, item_key, key_str):
        if key_str:
            self.keybinds[item_key] = key_str.lower()
        else:
            self.keybinds.pop(item_key, None)
        self._update_reverse_map()
        self.save_keybinds()

    def _update_reverse_map(self):
        self.reverse_keybinds = {v.lower(): k for k, v in self.keybinds.items() if v}

    def start_listeners(self):
        if not self.poll_timer.isActive():
            self.poll_timer.start(15)

        if self.mouse_listener is None:
            self.mouse_listener = mouse.Listener(
                on_click=self._on_mouse_click,
                on_scroll=self._on_mouse_scroll
            )
            self.mouse_listener.daemon = True
            self.mouse_listener.start()

    def _trigger_action(self, k_str):
        if k_str in self.reverse_keybinds:
            target = self.reverse_keybinds[k_str]
            if target == TOGGLE_RCS_KEY:
                self.emitter.toggle_rcs_triggered.emit()
            else:
                self.emitter.weapon_selected.emit(target)

    def _poll_keyboard(self):
        # Опрос цифр (0-9) и букв (A-Z)
        for vk in range(0x30, 0x5B):
            state = win32api.GetAsyncKeyState(vk)
            key_char = chr(vk).lower()
            if state & 0x8000:
                if key_char not in self._pressed_keys:
                    self._pressed_keys.add(key_char)
                    self._trigger_action(key_char)
            else:
                self._pressed_keys.discard(key_char)

        # Опрос клавиш F1-F12
        for vk in range(0x70, 0x7C):
            state = win32api.GetAsyncKeyState(vk)
            f_key = f"f{vk - 0x6F}"
            if state & 0x8000:
                if f_key not in self._pressed_keys:
                    self._pressed_keys.add(f_key)
                    self._trigger_action(f_key)
            else:
                self._pressed_keys.discard(f_key)

    def _on_mouse_click(self, x, y, button, pressed):
        if pressed:
            if button == mouse.Button.x1:
                self._trigger_action("mouse4")
            elif button == mouse.Button.x2:
                self._trigger_action("mouse5")
            elif button == mouse.Button.middle:
                self._trigger_action("mouse3")

    def _on_mouse_scroll(self, x, y, dx, dy):
        if dy > 0:
            self._trigger_action("mwheelup")
        elif dy < 0:
            self._trigger_action("mwheeldown")


class KeybindDialog(QDialog):
    def __init__(self, parent, config_service, keybind_manager):
        super().__init__(parent)
        self.config_service = config_service
        self.keybind_manager = keybind_manager
        self.setWindowTitle("Weapon & Function Keybinds")
        self.setFixedSize(380, 450)
        self.setStyleSheet("background-color: #111; color: #fff;")
        self.listening_row = -1

        self.mouse_timer = QTimer(self)
        self.mouse_timer.timeout.connect(self._check_mouse_buttons)

        self.scroll_listener = None
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout()
        
        self.table = QTableWidget()
        self.table.setColumnCount(2)
        self.table.setHorizontalHeaderLabels(["Action / Weapon", "Keybind"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setStyleSheet("""
            QTableWidget { background: #181818; color: #fff; gridline-color: #333; }
            QHeaderView::section { background: #222; color: #fff; padding: 4px; border: 1px solid #333; }
        """)

        items = [("Toggle Recoil Control", TOGGLE_RCS_KEY)]
        for w_name in self.config_service.weapon_profiles.keys():
            disp_name = self.config_service.get_weapon_display_name(w_name) or w_name
            items.append((disp_name, w_name))

        self.table.setRowCount(len(items))

        for row, (disp_name, key_id) in enumerate(items):
            item_label = QTableWidgetItem(disp_name)
            if key_id == TOGGLE_RCS_KEY:
                item_label.setForeground(Qt.cyan)
            item_label.setFlags(Qt.ItemIsEnabled)
            item_label.setData(Qt.UserRole, key_id)
            self.table.setItem(row, 0, item_label)

            k_val = self.keybind_manager.keybinds.get(key_id, "None")
            btn = QPushButton(k_val.upper() if k_val else "None")
            btn.setStyleSheet("background: #222; border: 1px solid #4488ff; color: #fff;")
            btn.clicked.connect(lambda _, r=row: self._start_capture(r))
            self.table.setCellWidget(row, 1, btn)

        layout.addWidget(self.table)

        close_btn = QPushButton("Done")
        close_btn.setStyleSheet("background: #222; border: 1px solid #4488ff; color: #fff; padding: 6px;")
        close_btn.clicked.connect(self._close_dialog)
        layout.addWidget(close_btn)

        self.setLayout(layout)

    def _start_capture(self, row):
        self.listening_row = row
        btn = self.table.cellWidget(row, 1)
        btn.setText("Press Key, Mouse4/5 or Scroll...")
        btn.setStyleSheet("background: #442222; border: 1px solid #ff4444; color: #fff;")
        
        self.mouse_timer.start(20)

        if self.scroll_listener is None:
            self.scroll_listener = mouse.Listener(on_scroll=self._on_capture_scroll)
            self.scroll_listener.daemon = True
            self.scroll_listener.start()

    def _on_capture_scroll(self, x, y, dx, dy):
        if self.listening_row != -1:
            if dy > 0:
                QTimer.singleShot(0, lambda: self._apply_bind("mwheelup"))
            elif dy < 0:
                QTimer.singleShot(0, lambda: self._apply_bind("mwheeldown"))

    def _check_mouse_buttons(self):
        if self.listening_row == -1:
            self.mouse_timer.stop()
            return

        if win32api.GetAsyncKeyState(0x05) & 0x8000:
            self._apply_bind("mouse4")
        elif win32api.GetAsyncKeyState(0x06) & 0x8000:
            self._apply_bind("mouse5")
        elif win32api.GetAsyncKeyState(0x04) & 0x8000:
            self._apply_bind("mouse3")

    def _stop_listeners(self):
        self.mouse_timer.stop()
        if self.scroll_listener:
            self.scroll_listener.stop()
            self.scroll_listener = None

    def _apply_bind(self, k_str):
        if self.listening_row == -1:
            return
        
        self._stop_listeners()

        item = self.table.item(self.listening_row, 0)
        key_id = item.data(Qt.UserRole)

        self.keybind_manager.set_keybind(key_id, k_str)
        btn = self.table.cellWidget(self.listening_row, 1)
        btn.setText(k_str.upper() if k_str else "None")
        btn.setStyleSheet("background: #222; border: 1px solid #4488ff; color: #fff;")

        self.listening_row = -1

    def keyPressEvent(self, event):
        if self.listening_row != -1:
            key = event.key()
            if key == Qt.Key_Escape:
                k_str = ""
            else:
                k_str = event.text().lower()
                if not k_str:
                    k_str = Qt.Key(key).name.replace("Key_", "").lower()

            self._apply_bind(k_str)
        else:
            super().keyPressEvent(event)

    def _close_dialog(self):
        self._stop_listeners()
        self.listening_row = -1
        self.accept()


class RCSMenu(QWidget):
    def __init__(self, config_service, recoil_service, gsi_service,
                 weapon_detection_service, autostop_service, keybind_manager):
        super().__init__()
        self.config_service = config_service
        self.recoil_service = recoil_service
        self.gsi_service = gsi_service
        self.weapon_detection_service = weapon_detection_service
        self.autostop_service = autostop_service
        self.keybind_manager = keybind_manager
        self.rcs_enabled = False
        self._insert_prev = False
        self._setup_ui()
        self._setup_timers()
        self.setWindowTitle("RCS")
        self.setWindowFlags(Qt.Widget)
        self.setFixedSize(290, 310)
        self.setAttribute(Qt.WA_TranslucentBackground, False)
        self.setStyleSheet("background-color: #000; color: #fff; border: 2px solid #4488ff;")

    def _setup_ui(self):
        layout = QVBoxLayout()
        layout.setSpacing(6)
        title = QLabel("Recoil Control")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("font-size: 14px; font-weight: bold; color: #66aaff;")
        layout.addWidget(title)
        self.weapon_label = QLabel("Weapon: --")
        layout.addWidget(self.weapon_label)
        self.status_label = QLabel("Recoil: OFF")
        self.status_label.setStyleSheet("color: red;")
        layout.addWidget(self.status_label)
        sens_layout = QHBoxLayout()
        sens_layout.addWidget(QLabel("Sensitivity:"))
        self.sens_input = QDoubleSpinBox()
        self.sens_input.setRange(0.1, 10.0)
        self.sens_input.setSingleStep(0.01)
        self.sens_input.setDecimals(2)
        self.sens_input.setValue(self.config_service.config.get("game_sensitivity", 1.0))
        self.sens_input.valueChanged.connect(self._on_sensitivity_changed)
        sens_layout.addWidget(self.sens_input)
        layout.addLayout(sens_layout)
        self.toggle_btn = QPushButton("Enable Recoil Control")
        self.toggle_btn.clicked.connect(self._toggle_rcs)
        layout.addWidget(self.toggle_btn)
        self.gsi_label = QLabel("GSI: Waiting for connection...")
        self.gsi_label.setStyleSheet("color: #888;")
        layout.addWidget(self.gsi_label)
        self.autostop_btn = QPushButton("Enable Auto-Stop")
        self.autostop_btn.clicked.connect(self._toggle_autostop)
        layout.addWidget(self.autostop_btn)

        binds_btn = QPushButton("Configure Keybinds")
        binds_btn.clicked.connect(self._open_keybinds)
        layout.addWidget(binds_btn)

        btn_layout = QHBoxLayout()
        save_btn = QPushButton("Save Config")
        save_btn.clicked.connect(self._save_config)
        btn_layout.addWidget(save_btn)
        exit_btn = QPushButton("Safe Exit")
        exit_btn.setStyleSheet("QPushButton { background: #5a1a1a; border: 1px solid #a33; color: #fff; }")
        exit_btn.clicked.connect(self._safe_exit)
        btn_layout.addWidget(exit_btn)
        layout.addLayout(btn_layout)
        self.setLayout(layout)

    def _setup_timers(self):
        self._ins = QTimer(self)
        self._ins.timeout.connect(self._check_insert)
        self._ins.start(50)
        self._upd = QTimer(self)
        self._upd.timeout.connect(self._update_ui)
        self._upd.start(200)

    def _check_insert(self):
        p = bool(win32api.GetAsyncKeyState(win32con.VK_INSERT) & 0x8000)
        if p and not self._insert_prev:
            self.setVisible(not self.isVisible())
        self._insert_prev = p

    def _update_ui(self):
        w = self.recoil_service.current_weapon
        d = self.config_service.get_weapon_display_name(w) if w else "--"
        kb = self.keybind_manager.keybinds.get(w, "").upper()
        kb_str = f" [{kb}]" if kb else ""
        self.weapon_label.setText(f"Weapon: {d}{kb_str}")

        s = "ON" if self.recoil_service.active else "OFF"
        self.status_label.setText(f"Recoil: {s}")
        self.status_label.setStyleSheet("color: green;" if self.recoil_service.active else "color: red;")
        now = time.time()
        el = now - self.gsi_service.last_seen if self.gsi_service.last_seen else -1
        if self.weapon_detection_service.enabled and el >= 0 and el < 5:
            lw = self.config_service.get_weapon_display_name(self.gsi_service.last_weapon) or self.gsi_service.last_weapon
            self.gsi_label.setText(f"GSI: Connected [{lw}]")
            self.gsi_label.setStyleSheet("color: #4c4;")
        elif self.weapon_detection_service.enabled and el >= 5:
            self.gsi_label.setText(f"GSI: Disconnected ({int(el)}s)")
            self.gsi_label.setStyleSheet("color: #c44;")
        elif self.weapon_detection_service.enabled:
            self.gsi_label.setText("GSI: Waiting for connection...")
            self.gsi_label.setStyleSheet("color: #888;")
        else:
            self.gsi_label.setText("GSI: Stopped")
            self.gsi_label.setStyleSheet("color: #888;")
        self.autostop_btn.setText("Disable Auto-Stop" if self.autostop_service.enabled else "Enable Auto-Stop")

    def _open_keybinds(self):
        dlg = KeybindDialog(self, self.config_service, self.keybind_manager)
        dlg.exec_()

    def _on_sensitivity_changed(self, value):
        wa = self.recoil_service.active
        if wa:
            self.recoil_service.stop_compensation()
        wn = self.recoil_service.current_weapon
        self.config_service.update_global_sensitivity(value)
        if wn:
            self.recoil_service.set_weapon(wn)
        if wa:
            self.recoil_service.start_compensation()

    def _toggle_autostop(self):
        if self.autostop_service.enabled:
            self.autostop_service.stop()
            self.autostop_btn.setText("Enable Auto-Stop")
        else:
            self.autostop_service.start()
            self.autostop_btn.setText("Disable Auto-Stop")
        self.config_service.config.setdefault("autostop", {})["enabled"] = self.autostop_service.enabled
        self.config_service.config_repository.save_config(self.config_service.config)

    def _toggle_rcs(self):
        if self.rcs_enabled:
            self.recoil_service.stop_compensation()
            self.rcs_enabled = False
            self.weapon_detection_service._was_active = False
            self.toggle_btn.setText("Enable Recoil Control")
        else:
            self.weapon_detection_service._was_active = True
            if not self.recoil_service.current_weapon:
                f = next(iter(self.config_service.weapon_profiles.keys()), None)
                if f:
                    self.recoil_service.set_weapon(f)
            if self.recoil_service.current_weapon:
                self.recoil_service.start_compensation()
                self.rcs_enabled = True
                self.toggle_btn.setText("Disable Recoil Control")

    def _save_config(self):
        weapons = []
        for n, p in self.config_service.weapon_profiles.items():
            weapons.append({
                "name": n, "display_name": p.display_name,
                "length": p.length, "multiple": p.multiple,
                "sleep_divider": p.sleep_divider, "sleep_suber": p.sleep_suber,
            })
        data = {
            "game_sensitivity": self.config_service.config.get("game_sensitivity", 1.0),
            "gsi": self.config_service.gsi_config,
            "weapons": weapons,
        }
        self.config_service.config_repository.save_config(data)
        self.keybind_manager.save_keybinds()

    def _safe_exit(self):
        self.recoil_service.stop_compensation()
        self.autostop_service.stop()
        self.weapon_detection_service.disable()
        self.gsi_service.stop_server()
        self._save_config()
        QApplication.quit()


def main():
    app = QApplication(sys.argv)
    app.setStyleSheet("""
        QWidget { background: #000; color: #fff; font-size: 12px; }
        QLabel { color: #fff; }
        QDoubleSpinBox { background: #111; color: #fff; border: 1px solid #4488ff;
                         padding: 2px 4px; border-radius: 2px; }
        QPushButton { background: #111; border: 1px solid #4488ff; color: #fff;
                      padding: 4px; border-radius: 3px; }
        QPushButton:hover { background: #222; border: 1px solid #66aaff; }
    """)

    cr = ConfigRepository()
    cvs = CSVRepository()
    cs = ConfigService(cr, cvs)
    inp = InputService()
    rs = RecoilService(cs, inp)

    w_ref = []

    def on_bind_weapon_select(weapon_name):
        def _apply():
            rs.set_weapon(weapon_name)
            if w_ref and w_ref[0].rcs_enabled:
                rs.stop_compensation()
                rs.start_compensation()
        QTimer.singleShot(0, _apply)

    def on_bind_toggle_rcs():
        if w_ref:
            QTimer.singleShot(0, w_ref[0]._toggle_rcs)

    km = KeybindManager(on_bind_weapon_select, on_bind_toggle_rcs)
    km.start_listeners()

    gc = cs.gsi_config
    gs = GSIService(host=gc.get("server_host", "127.0.0.1"), port=gc.get("server_port", 59873))
    wd = WeaponDetectionService(rs)
    rs.set_weapon_detection_service(wd)
    gs.register_callback("weapon_detection", wd.process_player_state)
    if gc.get("enabled", True):
        gs.start_server()
        wd.enable()

    asv = AutoStopService()
    import sys as _sys
    _def_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json") if not hasattr(_sys, '_MEIPASS') else os.path.join(_sys._MEIPASS, "config.json")
    asv.load_defaults(_def_path)
    if "autostop" not in cs.config:
        cs.config["autostop"] = {"enabled": False}
        for k in ("keyboard", "min_stop_trigger_ms", "peek_window_ms", "stop_duration_ms",
                  "stop_scaling_ratio", "max_stop_hold_ms", "peek_delay_ms",
                  "press_delay_ms", "space_timer", "stop_on_multi_keys"):
            cs.config["autostop"][k] = getattr(asv, k)
        cs.config_repository.save_config(cs.config)
    asv.load_config(cs.config)
    if cs.config["autostop"].get("enabled", False):
        asv.start()

    first = next(iter(cs.weapon_profiles.keys()), None)
    if first:
        rs.set_weapon(first)

    w = RCSMenu(cs, rs, gs, wd, asv, km)
    w_ref.append(w)
    w.show()

    t = QTimer(app)
    t.timeout.connect(lambda: None)
    t.start(100)
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()