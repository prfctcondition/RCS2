import threading
from typing import Optional

import win32con

from core.services.input_service import InputService
from core.services.config_service import ConfigService
from core.services.timing_service import TimingService


class RecoilService:
    def __init__(self, config_service: ConfigService, input_service: InputService):
        self.config_service = config_service
        self.input_service = input_service
        self.timing_service = TimingService()
        self.active = False
        self.current_weapon = None
        self.running_thread = None
        self.stop_event = threading.Event()
        self.weapon_detection_service = None
        self.accumulated_x = 0.0
        self.accumulated_y = 0.0

    def set_weapon_detection_service(self, service) -> None:
        self.weapon_detection_service = service

    def set_weapon(self, weapon_name: str) -> bool:
        if not weapon_name:
            if self.active:
                self.stop_compensation()
            self.current_weapon = None
            return True
        if weapon_name not in self.config_service.weapon_profiles:
            return False
        self.current_weapon = weapon_name
        return True

    def get_current_weapon(self):
        if not self.current_weapon:
            return None
        return self.config_service.get_weapon_profile(self.current_weapon)

    def start_compensation(self, key_trigger: int = win32con.VK_LBUTTON) -> bool:
        if self.active or not self.current_weapon:
            return False
        self.active = True
        self.stop_event.clear()
        self.running_thread = threading.Thread(
            target=self._compensation_loop,
            args=(key_trigger,),
            daemon=True
        )
        self.running_thread.start()
        return True

    def stop_compensation(self) -> bool:
        if not self.active:
            return True
        self.stop_event.set()
        if self.running_thread and self.running_thread.is_alive():
            self.running_thread.join(timeout=1.0)
        self.active = False
        return True

    def _compensation_loop(self, key_trigger: int) -> None:
        while not self.stop_event.is_set():
            try:
                weapon = self.get_current_weapon()
                if not weapon:
                    self.timing_service.combined_sleep_2(10)
                    continue
                pattern = weapon.calculated_pattern
                if not pattern:
                    self.timing_service.combined_sleep_2(10)
                    continue
                if self.input_service.is_key_pressed(key_trigger):
                    self._execute_compensation_sequence(weapon, pattern, key_trigger)
                    if self.stop_event.is_set():
                        break
                    while (self.input_service.is_key_pressed(key_trigger) and
                           not self.stop_event.is_set()):
                        self.timing_service.combined_sleep_2(1)
                self.timing_service.combined_sleep_2(1)
            except Exception:
                self.timing_service.combined_sleep_2(10)

    def _execute_compensation_sequence(self, weapon, pattern, key_trigger) -> bool:
        begin_time = self.timing_service.system_time()
        accumulated_time = 0.0
        self.accumulated_x = 0.0
        self.accumulated_y = 0.0
        sum_x = 0.0
        sum_y = 0.0

        for i, point in enumerate(pattern):
            if (not self.input_service.is_key_pressed(key_trigger) or
                    self.stop_event.is_set()):
                return False
            if i == 0:
                delay = point.delay / weapon.sleep_divider - weapon.sleep_suber
                accumulated_time = delay
                self.timing_service.combined_sleep(accumulated_time, begin_time)
                continue
            dx_float = point.dx
            dy_float = -point.dy
            sum_x += dx_float
            sum_y += dy_float
            dx_int = int(sum_x)
            dy_int = int(sum_y)
            sum_x -= dx_int
            sum_y -= dy_int
            if dx_int != 0 or dy_int != 0:
                self.input_service.mouse_move(dx_int, dy_int)
                self.accumulated_x += dx_int
                self.accumulated_y += dy_int
            if i < len(pattern) - 1:
                if i <= weapon.multiple:
                    intermediate_sleep = (
                        point.delay / weapon.sleep_divider - weapon.sleep_suber) / 2
                else:
                    intermediate_sleep = (
                        point.delay / weapon.sleep_divider - weapon.sleep_suber) * 2 / 3
                self.timing_service.combined_sleep_2(intermediate_sleep)
                accumulated_time += point.delay / weapon.sleep_divider - weapon.sleep_suber
                self.timing_service.combined_sleep(accumulated_time, begin_time)
        return True
