import json
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from typing import Callable, Dict, Optional


_WEAPON_MAP = {
    "weapon_ak47": "ak47",
    "weapon_m4a1": "m4a4",
    "weapon_m4a1_silencer": "m4a1",
    "weapon_galilar": "galil",
    "weapon_famas": "famas",
    "weapon_sg556": "sg553",
    "weapon_aug": "aug",
    "weapon_p90": "p90",
    "weapon_bizon": "bizon",
    "weapon_ump45": "ump45",
    "weapon_mac10": "mac10",
    "weapon_mp5sd": "mp5sd",
    "weapon_mp7": "mp7",
    "weapon_mp9": "mp9",
    "weapon_m249": "m249",
    "weapon_cz75a": "cz75",
}


class GSIHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length)
        data = json.loads(body.decode("utf-8"))
        if self.server.callback:
            self.server.callback(data)
        self.send_response(200)
        self.end_headers()

    def log_message(self, fmt, *args):
        pass


class GSIService:
    def __init__(self, host: str = "127.0.0.1", port: int = 59873):
        self.host = host
        self.port = port
        self._server: Optional[HTTPServer] = None
        self._thread: Optional[threading.Thread] = None
        self.callbacks: Dict[str, Callable] = {}
        self.last_seen = 0.0
        self.last_weapon = ""

    def register_callback(self, name: str, callback: Callable) -> None:
        self.callbacks[name] = callback

    def start_server(self) -> bool:
        try:
            self._server = HTTPServer((self.host, self.port), GSIHandler)
            self._server.callback = self._on_gsi_data
            self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)
            self._thread.start()
            return True
        except Exception:
            return False

    def stop_server(self) -> None:
        if self._server:
            self._server.shutdown()

    def _on_gsi_data(self, data: dict) -> None:
        import time
        self.last_seen = time.time()
        weapon = self._detect_weapon(data)
        self.last_weapon = weapon or self.last_weapon
        for cb in self.callbacks.values():
            cb(weapon)

    def _detect_weapon(self, data: dict) -> Optional[str]:
        try:
            weapons = data.get("player", {}).get("weapons", {})
            for w in weapons.values():
                if w.get("state") == "active":
                    cs2_name = w.get("name", "")
                    return _WEAPON_MAP.get(cs2_name)
        except Exception:
            pass
        return None
