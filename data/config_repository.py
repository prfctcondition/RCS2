import json, sys, os
from typing import Dict, List, Any
from pathlib import Path

from core.models.recoil_data import RecoilData


class ConfigRepository:
    def __init__(self, config_file: str = "config.json"):
        self.config_file = config_file
        self._ensure_config()

    def _ensure_config(self):
        path = Path(self.config_file)
        if path.exists():
            return
        mp = getattr(sys, '_MEIPASS', None)
        if mp:
            src = Path(mp) / self.config_file
            if src.exists():
                import shutil
                shutil.copy2(str(src), str(path))

    def load_config(self) -> Dict[str, Any]:
        path = Path(self.config_file)
        if not path.exists():
            return {}
        with open(str(path), 'r', encoding='utf-8') as f:
            return json.load(f)

    def save_config(self, config: Dict[str, Any]) -> bool:
        with open(self.config_file, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=4, ensure_ascii=False)
        return True


class CSVRepository:
    SENSITIVITY_MULTIPLIER = 2.45

    def __init__(self, patterns_folder: str = "patterns"):
        self.patterns_folder = Path(patterns_folder)
        if not self.patterns_folder.exists():
            mp = getattr(sys, '_MEIPASS', None)
            if mp:
                alt = Path(mp) / patterns_folder
                if alt.exists():
                    self.patterns_folder = alt

    def load_weapon_pattern(self, filename: str, game_sensitivity: float = 1.0) -> List[RecoilData]:
        file_path = self.patterns_folder / filename
        if not file_path.exists():
            return []
        pattern = []
        with open(str(file_path), 'r', encoding='utf-8-sig') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                parts = line.split(',')
                if len(parts) >= 3:
                    dx = float(parts[0]) * self.SENSITIVITY_MULTIPLIER / game_sensitivity
                    dy = float(parts[1]) * self.SENSITIVITY_MULTIPLIER / game_sensitivity
                    delay = round(float(parts[2]), 1)
                    pattern.append(RecoilData(dx=dx, dy=dy, delay=delay))
        return pattern
