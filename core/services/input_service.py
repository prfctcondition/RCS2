import ctypes
import win32api
from ctypes import wintypes


class MOUSEINPUT(ctypes.Structure):
    _fields_ = [
        ("dx", wintypes.LONG),
        ("dy", wintypes.LONG),
        ("mouseData", wintypes.DWORD),
        ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ctypes.POINTER(ctypes.c_ulong))
    ]


class INPUT_UNION(ctypes.Union):
    _fields_ = [("mi", MOUSEINPUT)]


class INPUT(ctypes.Structure):
    _fields_ = [
        ("type", wintypes.DWORD),
        ("union", INPUT_UNION)
    ]


class InputService:
    MOUSEEVENTF_MOVE = 0x0001

    def __init__(self):
        self._user32 = ctypes.WinDLL('user32')
        self._user32.SendInput.argtypes = (
            wintypes.UINT,
            ctypes.POINTER(INPUT),
            ctypes.c_int
        )
        self._user32.SendInput.restype = wintypes.UINT

    def mouse_move(self, dx: int, dy: int) -> None:
        if dx == 0 and dy == 0:
            return
        mouse_input = MOUSEINPUT(
            dx=dx, dy=dy, mouseData=0,
            dwFlags=self.MOUSEEVENTF_MOVE,
            time=0, dwExtraInfo=None
        )
        input_obj = INPUT(
            type=0,
            union=INPUT_UNION(mi=mouse_input)
        )
        self._user32.SendInput(
            1, ctypes.byref(input_obj), ctypes.sizeof(INPUT))

    def is_key_pressed(self, vk_code: int) -> bool:
        return bool(win32api.GetAsyncKeyState(vk_code) & 0x8000)
