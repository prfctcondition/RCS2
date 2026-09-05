# CS2 Recoil Control System (RCS) & Auto-Stop Macro

A lightweight, high-performance Recoil Control System (RCS) and movement utility for **Counter-Strike 2**, featuring automatic weapon detection, low-level input simulation, and fully customizable keybinds.

---

## ✨ Features

* **Advanced Recoil Control**: Smooth and precise compensation tailored for all CS2 spray patterns.
* **Game State Integration (GSI)**: Automatic weapon detection in real-time via CS2's built-in GSI server.
* **Auto-Stop Assistant**: Intelligent counter-strafe simulation for instant accuracy upon shooting.
* **Global & Hybrid Keybind Manager**: 
  * Low-level Windows API keyboard polling (GetAsyncKeyState) for 100% reliable trigger detection in any game/layout.
  * Native support for Mouse4, Mouse5, Middle Mouse, Mouse Wheel Scroll UP/DOWN, and standard keyboard keys (A-Z, 0-9, F1-F12).
* **Minimalist Dark UI**: Overlay-friendly GUI built with PyQt5 for quick sensitivity tuning and profile management.
* **Per-Weapon Fine-Tuning**: Configurable sleep timers, pattern multipliers, and sensitivity scaling.

---

## 🛠️ Requirements

* **OS**: Windows 10 / 11
* **Python**: 3.9 or higher

---

## 🚀 Installation & Quick Start

### 1. Install Dependencies
Run the following command in your terminal to install all required libraries:

pip install PyQt5 pynput pywin32 requests

Alternatively, if you have a requirements.txt file:

pip install -r requirements.txt

### 2. Launching the App
Simply double-click start.bat or run it from your command prompt:

start.bat

---

## 🎮 Hotkeys & Controls

| Key / Control | Function |
| :--- | :--- |
| **Insert** | Toggle UI Overlay Visibility (Show / Hide) |
| **Configure Keybinds** | Open in-app dialog to set custom hotkeys for weapons & RCS |

---

## 📄 License & Disclaimer

Educational purposes only. Use at your own risk.
