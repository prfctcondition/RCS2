from typing import Optional

from core.services.recoil_service import RecoilService


class WeaponDetectionService:
    def __init__(self, recoil_service: RecoilService):
        self.recoil_service = recoil_service
        self.enabled = False
        self._was_active = False

    def enable(self) -> bool:
        self.enabled = True
        return True

    def disable(self) -> bool:
        self.enabled = False
        return True

    def process_player_state(self, weapon_name: Optional[str]) -> None:
        if not self.enabled:
            return
        if not weapon_name:
            if self.recoil_service.active:
                self._was_active = True
                self.recoil_service.stop_compensation()
            self.recoil_service.set_weapon(None)
            return
        current = self.recoil_service.current_weapon
        if current != weapon_name:
            prev_active = self.recoil_service.active
            if prev_active:
                self.recoil_service.stop_compensation()
            self.recoil_service.set_weapon(weapon_name)
            if prev_active or self._was_active:
                self.recoil_service.start_compensation()
                self._was_active = False
