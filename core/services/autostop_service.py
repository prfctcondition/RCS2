import threading, time, os, json
from concurrent.futures import ThreadPoolExecutor
from pynput.keyboard import Controller, Listener, Key, KeyCode
from pynput import keyboard


def _log(msg: str):
    pass

_VK_TO_NAME = {
    0x57: "w", 0x41: "a", 0x53: "s", 0x44: "d",
}

def _key_to_str(key):
    try:
        return key.char
    except AttributeError:
        s = str(key)
        return s.replace("Key.", "") if s.startswith("Key.") else s


class AutoStopService:
    def __init__(self):
        self.enabled = False
        self.active = True
        self._listener: Listener = None
        self._stop_event = threading.Event()
        self._lock = threading.Lock()
        self._executor = ThreadPoolExecutor(max_workers=4)

        # state
        self.press_timer = {}
        self.physical_keys = set()
        self.simulated_press_count = {}
        self.simulated_release_count = {}
        self.key_press_history = {}
        self.space_flag = False
        self.disable_flag = False
        self.suppressed_keys = set()
        self.last_press_ts = 0.0
        self.last_press_key = None

        self.keyboard = {"w": "s", "s": "w", "a": "d", "d": "a"}
        self.min_stop_trigger_ms = 150
        self.peek_window_ms = 150
        self.stop_duration_ms = 70
        self.stop_scaling_ratio = 0.25
        self.max_stop_hold_ms = 2300
        self.peek_delay_ms = 15
        self.press_delay_ms = 5
        self.space_timer = 0.85
        self.stop_on_multi_keys = False
        self.auto_window_detection = False
        self.target_window = "Counter-Strike 2"

        self._controller = Controller()

    def load_defaults(self, path: str):
        if not os.path.exists(path):
            return
        try:
            with open(path, 'r', encoding='utf-8') as f:
                d = json.load(f)
            self.keyboard = d.get("方向键急停映射", self.keyboard)
            self.min_stop_trigger_ms = d.get("最小触发急停的按键时长_毫秒", self.min_stop_trigger_ms)
            self.peek_window_ms = d.get("快速Peek检测窗口_毫秒", self.peek_window_ms)
            self.stop_duration_ms = d.get("急停按键最大持续时长_毫秒", self.stop_duration_ms)
            self.stop_scaling_ratio = d.get("急停时长缩放比例", self.stop_scaling_ratio)
            self.max_stop_hold_ms = d.get("最大有效急停按键时长_毫秒", self.max_stop_hold_ms)
            self.peek_delay_ms = d.get("急停触发预留延迟_毫秒", self.peek_delay_ms)
            self.space_timer = d.get("跳跃后禁用急停时长_秒", self.space_timer)
            self.press_delay_ms = d.get("双键快速冲突延迟_毫秒", self.press_delay_ms)
            self.stop_on_multi_keys = d.get("多键同时按下时是否触发急停", self.stop_on_multi_keys)
            _log(f"Defaults loaded from {path}")
        except Exception as e:
            _log(f"load_defaults error: {e}")

    def load_config(self, config: dict):
        ac = config.get("autostop", {})
        self.keyboard = ac.get("keyboard", self.keyboard)
        self.min_stop_trigger_ms = ac.get("min_stop_trigger_ms", self.min_stop_trigger_ms)
        self.peek_window_ms = ac.get("peek_window_ms", self.peek_window_ms)
        self.stop_duration_ms = ac.get("stop_duration_ms", self.stop_duration_ms)
        self.stop_scaling_ratio = ac.get("stop_scaling_ratio", self.stop_scaling_ratio)
        self.max_stop_hold_ms = ac.get("max_stop_hold_ms", self.max_stop_hold_ms)
        self.peek_delay_ms = ac.get("peek_delay_ms", self.peek_delay_ms)
        self.space_timer = ac.get("space_timer", self.space_timer)
        self.press_delay_ms = ac.get("press_delay_ms", self.press_delay_ms)
        self.stop_on_multi_keys = ac.get("stop_on_multi_keys", self.stop_on_multi_keys)

    def start(self):
        if self.enabled:
            return
        self.enabled = True
        self.active = True
        self._stop_event.clear()
        self._reset_state()
        _log("AutoStop start() called, creating listener...")
        self._listener = Listener(on_press=self._on_press, on_release=self._on_release)
        self._listener.start()
        _log(f"AutoStop started (listener alive={self._listener.running})")

    def stop(self):
        if not self.enabled:
            return
        self.enabled = False
        self.active = False
        self._stop_event.set()
        if self._listener:
            self._listener.stop()
            self._listener = None
        self._reset_state()
        _log("AutoStop stopped")

    def _reset_state(self):
        with self._lock:
            self.press_timer.clear()
            self.physical_keys.clear()
            self.simulated_press_count.clear()
            self.simulated_release_count.clear()
            self.key_press_history.clear()
            self.suppressed_keys.clear()
            self.space_flag = False
            self.disable_flag = False
            self.last_press_ts = 0.0
            self.last_press_key = None

    def _on_press(self, key):
        try:
            ks = _key_to_str(key)

            # jump / disable key handled before everything else
            if ks in ("space", " "):
                _log(f"JUMP detected, disabling for {self.space_timer}s")
                self._executor.submit(self._handle_jump_delay)
                return
            if ks == "shift":
                _log("SHIFT disable on")
                self.disable_flag = True
                return

            if ks in self.keyboard:
                with self._lock:
                    if self.simulated_press_count.get(ks, 0) > 0:
                        self.simulated_press_count[ks] -= 1
                        return
                    self.physical_keys.add(ks)
                    self.key_press_history[ks] = time.time()
                    opp = self.keyboard[ks]
                    if ks not in self.press_timer and opp not in self.physical_keys:
                        self.press_timer[ks] = time.time()
                        _log(f"PRESS {ks.upper()} (start timer)")
                    else:
                        _log(f"PRESS {ks.upper()} (no timer - opp held or already timed)")

            if not self.active or self.space_flag:
                return

            if ks in self.keyboard:
                now = time.time()
                if (now - self.last_press_ts) * 1000 < self.press_delay_ms:
                    is_movement = ks in self.keyboard
                    is_same = self.last_press_key == key
                    if not is_movement or is_same:
                        with self._lock:
                            self.suppressed_keys.add(ks)
                            if self.last_press_key:
                                lk = _key_to_str(self.last_press_key)
                                if lk: self.suppressed_keys.add(lk)
                self.last_press_ts = now
                self.last_press_key = key

        except Exception as e:
            _log(f"_on_press error: {e}")

    def _on_release(self, key):
        try:
            ks = _key_to_str(key)
            if not ks:
                return

            if ks == "shift":
                _log("SHIFT disable off")
                self.disable_flag = False
                return

            with self._lock:
                if self.simulated_release_count.get(ks, 0) > 0:
                    self.simulated_release_count[ks] -= 1
                    _log(f"FILTER simulated release: {ks.upper()}")
                    return
                if ks in self.physical_keys:
                    self.physical_keys.discard(ks)

            if not self.active:
                return

            if ks in self.keyboard:
                with self._lock:
                    if ks in self.suppressed_keys:
                        self.suppressed_keys.discard(ks)
                        self.press_timer.pop(ks, None)
                        _log(f"SUPPRESSED release: {ks.upper()}")
                        return
                    if ks not in self.press_timer:
                        return
                    start_ts = self.press_timer.pop(ks)
                    duration = time.time() - start_ts

                if self.disable_flag or self.space_flag:
                    _log(f"SKIP release {ks.upper()} (disabled/space)")
                    return

                if duration * 1000 > self.max_stop_hold_ms:
                    _log(f"SKIP release {ks.upper()} (too long: {duration*1000:.0f}ms)")
                    return
                if duration * 1000 < self.min_stop_trigger_ms:
                    _log(f"SKIP release {ks.upper()} (too short: {duration*1000:.0f}ms)")
                    return

                opp = self.keyboard.get(ks)
                if not opp:
                    return
                with self._lock:
                    last_opp = self.key_press_history.get(opp, 0)
                multi = len([k for k in self.press_timer if k in self.keyboard]) > 0
                if not multi:
                    if (time.time() - last_opp) * 1000 < self.peek_window_ms:
                        _log(f"SKIP release {ks.upper()} (peek window)")
                        return

                _log(f"TRIGGER stop: {ks.upper()} -> {opp.upper()} ({duration*1000:.0f}ms)")
                self._executor.submit(self._do_stop, ks, duration)

        except Exception as e:
            _log(f"_on_release error: {e}")

    def _do_stop(self, key_str, pressed_time):
        try:
            if self.peek_delay_ms > 0:
                time.sleep(self.peek_delay_ms / 1000.0)
            opp = self.keyboard[key_str]
            with self._lock:
                if opp in self.physical_keys:
                    _log(f"DO_STOP abort: {opp.upper()} physically pressed")
                    return
                self.simulated_press_count[opp] = self.simulated_press_count.get(opp, 0) + 1

            hold = min(self.stop_duration_ms / 1000.0, pressed_time * self.stop_scaling_ratio)
            try:
                self._controller.press(opp)
                _log(f"SIMULATE press {opp.upper()} ({hold*1000:.0f}ms)")
                time.sleep(hold)
                with self._lock:
                    if opp not in self.physical_keys:
                        self.simulated_release_count[opp] = self.simulated_release_count.get(opp, 0) + 1
                        self._controller.release(opp)
                        _log(f"SIMULATE release {opp.upper()}")
            except Exception as e:
                _log(f"DO_STOP key error: {e}")
        except Exception as e:
            _log(f"_do_stop error: {e}")

    def _handle_jump_delay(self):
        with self._lock:
            self.press_timer.clear()
            self.space_flag = True
        time.sleep(self.space_timer)
        with self._lock:
            self.space_flag = False
