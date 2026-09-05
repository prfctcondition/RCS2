from typing import Dict, Optional

from core.models.weapon import WeaponProfile
from data.config_repository import ConfigRepository, CSVRepository


class ConfigService:
    def __init__(self, config_repository: ConfigRepository, csv_repository: CSVRepository):
        self.config_repository = config_repository
        self.csv_repository = csv_repository
        self.config = {}
        self.weapon_profiles: Dict[str, WeaponProfile] = {}
        self.hotkeys = {}
        self.gsi_config = {}
        self.load_config()

    def load_config(self) -> bool:
        self.config = self.config_repository.load_config()
        if not self.config:
            return False
        self._parse_config()
        return True

    def _parse_config(self) -> None:
        game_sensitivity = self.config.get("game_sensitivity", 1.0)
        weapons_config = self.config.get("weapons", [])
        self.gsi_config = self.config.get("gsi", {})
        self.weapon_profiles = {}
        for wc in weapons_config:
            name = wc.get("name")
            if not name:
                continue
            csv_file = f"{name}.csv"
            recoil_data = self.csv_repository.load_weapon_pattern(csv_file, game_sensitivity)
            if not recoil_data:
                continue
            profile = WeaponProfile(
                name=name,
                display_name=wc.get("display_name", name),
                recoil_pattern=recoil_data,
                length=wc.get("length", 30),
                multiple=wc.get("multiple", 6),
                sleep_divider=wc.get("sleep_divider", 6.0),
                sleep_suber=wc.get("sleep_suber", 0.0),
                game_sensitivity=game_sensitivity
            )
            self.weapon_profiles[name] = profile
        self.hotkeys = self.config.get("hotkeys", {})

    def get_weapon_profile(self, name: str) -> Optional[WeaponProfile]:
        return self.weapon_profiles.get(name)

    def get_weapon_display_name(self, internal_name: str) -> Optional[str]:
        if not internal_name:
            return None
        profile = self.weapon_profiles.get(internal_name)
        if profile:
            return profile.display_name
        for wc in self.config.get("weapons", []):
            if wc.get("name") == internal_name:
                return wc.get("display_name", internal_name)
        return internal_name

    def update_global_sensitivity(self, new_sensitivity: float) -> None:
        self.config["game_sensitivity"] = new_sensitivity
        self._parse_config()
