"""Small DualSense to Xbox 360 bridge for Windows."""

import os
import queue
import threading
import time
import tkinter as tk
from tkinter import ttk
import webbrowser

os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")

import pygame
import hid
from pygame._sdl2 import controller as sdl_controller


DRIVER_URL = "https://github.com/nefarius/ViGEmBus/releases/tag/v1.22.0"
BUTTONS = (
    (pygame.CONTROLLER_BUTTON_A, "XUSB_GAMEPAD_A"),
    (pygame.CONTROLLER_BUTTON_B, "XUSB_GAMEPAD_B"),
    (pygame.CONTROLLER_BUTTON_X, "XUSB_GAMEPAD_X"),
    (pygame.CONTROLLER_BUTTON_Y, "XUSB_GAMEPAD_Y"),
    (pygame.CONTROLLER_BUTTON_BACK, "XUSB_GAMEPAD_BACK"),
    (pygame.CONTROLLER_BUTTON_START, "XUSB_GAMEPAD_START"),
    (pygame.CONTROLLER_BUTTON_LEFTSHOULDER, "XUSB_GAMEPAD_LEFT_SHOULDER"),
    (pygame.CONTROLLER_BUTTON_RIGHTSHOULDER, "XUSB_GAMEPAD_RIGHT_SHOULDER"),
    (pygame.CONTROLLER_BUTTON_LEFTSTICK, "XUSB_GAMEPAD_LEFT_THUMB"),
    (pygame.CONTROLLER_BUTTON_RIGHTSTICK, "XUSB_GAMEPAD_RIGHT_THUMB"),
    (pygame.CONTROLLER_BUTTON_DPAD_UP, "XUSB_GAMEPAD_DPAD_UP"),
    (pygame.CONTROLLER_BUTTON_DPAD_DOWN, "XUSB_GAMEPAD_DPAD_DOWN"),
    (pygame.CONTROLLER_BUTTON_DPAD_LEFT, "XUSB_GAMEPAD_DPAD_LEFT"),
    (pygame.CONTROLLER_BUTTON_DPAD_RIGHT, "XUSB_GAMEPAD_DPAD_RIGHT"),
)


class UsbDualSense:
    """Read the active USB interface when SDL selects an idle Bluetooth twin."""

    def __init__(self, info):
        self.path = info["path"]
        self.name = info.get("product_string") or "DualSense (USB)"
        self.device = hid.device()
        self.device.open_path(self.path)
        self.device.set_nonblocking(1)
        self.report = [1, 128, 128, 128, 128, 0, 0, 0, 8, 0, 0]
        self.connected = True

    def poll(self):
        try:
            for _ in range(32):
                report = self.device.read(64)
                if not report:
                    break
                if len(report) >= 11 and report[0] == 1:
                    self.report = report
        except OSError:
            self.connected = False

    def attached(self):
        return self.connected

    def get_button(self, button):
        face = self.report[8]
        shoulder = self.report[9]
        direction = face & 0x0F
        masks = {
            pygame.CONTROLLER_BUTTON_A: bool(face & 0x20),  # Cross
            pygame.CONTROLLER_BUTTON_B: bool(face & 0x40),  # Circle
            pygame.CONTROLLER_BUTTON_X: bool(face & 0x10),  # Square
            pygame.CONTROLLER_BUTTON_Y: bool(face & 0x80),  # Triangle
            pygame.CONTROLLER_BUTTON_BACK: bool(shoulder & 0x10),
            pygame.CONTROLLER_BUTTON_START: bool(shoulder & 0x20),
            pygame.CONTROLLER_BUTTON_LEFTSHOULDER: bool(shoulder & 0x01),
            pygame.CONTROLLER_BUTTON_RIGHTSHOULDER: bool(shoulder & 0x02),
            pygame.CONTROLLER_BUTTON_LEFTSTICK: bool(shoulder & 0x40),
            pygame.CONTROLLER_BUTTON_RIGHTSTICK: bool(shoulder & 0x80),
            pygame.CONTROLLER_BUTTON_DPAD_UP: direction in (0, 1, 7),
            pygame.CONTROLLER_BUTTON_DPAD_RIGHT: direction in (1, 2, 3),
            pygame.CONTROLLER_BUTTON_DPAD_DOWN: direction in (3, 4, 5),
            pygame.CONTROLLER_BUTTON_DPAD_LEFT: direction in (5, 6, 7),
        }
        return masks.get(button, False)

    def get_axis(self, axis):
        indices = {
            pygame.CONTROLLER_AXIS_LEFTX: 1,
            pygame.CONTROLLER_AXIS_LEFTY: 2,
            pygame.CONTROLLER_AXIS_RIGHTX: 3,
            pygame.CONTROLLER_AXIS_RIGHTY: 4,
        }
        if axis in indices:
            value = self.report[indices[axis]]
            return max(-32768, min(32767, round((value - 128) * 32767 / 127)))
        if axis == pygame.CONTROLLER_AXIS_TRIGGERLEFT:
            return round(self.report[5] * 32767 / 255)
        if axis == pygame.CONTROLLER_AXIS_TRIGGERRIGHT:
            return round(self.report[6] * 32767 / 255)
        return 0

    def quit(self):
        self.device.close()


def find_usb_dualsense():
    for info in hid.enumerate(0x054C):
        name = (info.get("product_string") or "").lower()
        if info.get("interface_number", -1) >= 0 and "dualsense" in name:
            return UsbDualSense(info)
    return None


def axis_stick(value):
    """Convert SDL's signed 16-bit stick value to vgamepad's float range."""
    return max(-1.0, min(1.0, value / (32768.0 if value < 0 else 32767.0)))


def axis_trigger(value):
    return max(0.0, min(1.0, value / 32767.0))


def send_report(source, target, xbox_buttons):
    target.reset()
    active_inputs = []
    for source_button, xbox_button in xbox_buttons:
        if source.get_button(source_button):
            target.press_button(button=xbox_button)
            active_inputs.append(xbox_button.name.replace("XUSB_GAMEPAD_", ""))
    lx = axis_stick(source.get_axis(pygame.CONTROLLER_AXIS_LEFTX))
    ly = axis_stick(source.get_axis(pygame.CONTROLLER_AXIS_LEFTY))
    rx = axis_stick(source.get_axis(pygame.CONTROLLER_AXIS_RIGHTX))
    ry = axis_stick(source.get_axis(pygame.CONTROLLER_AXIS_RIGHTY))
    lt = axis_trigger(source.get_axis(pygame.CONTROLLER_AXIS_TRIGGERLEFT))
    rt = axis_trigger(source.get_axis(pygame.CONTROLLER_AXIS_TRIGGERRIGHT))
    target.left_joystick_float(
        x_value_float=lx,
        y_value_float=-ly,
    )
    target.right_joystick_float(
        x_value_float=rx,
        y_value_float=-ry,
    )
    target.left_trigger_float(lt)
    target.right_trigger_float(rt)
    target.update()
    if max(abs(lx), abs(ly)) > 0.3:
        active_inputs.append("LEFT STICK")
    if max(abs(rx), abs(ry)) > 0.3:
        active_inputs.append("RIGHT STICK")
    if lt > 0.3:
        active_inputs.append("L2")
    if rt > 0.3:
        active_inputs.append("R2")
    return ", ".join(active_inputs) if active_inputs else "None"


class Bridge:
    def __init__(self):
        self.commands = queue.Queue()
        self.events = queue.Queue()
        self.latest_input = "Press a button after starting"
        self.thread = threading.Thread(target=self.run, daemon=True)
        self.thread.start()

    def post(self, status, active=False):
        self.events.put((status, active))

    def run(self):
        source = None
        target = None
        enabled = False
        source_name = None
        vg = None
        xbox_buttons = None
        try:
            pygame.display.init()
            pygame.display.set_mode((1, 1), pygame.HIDDEN)
            pygame.joystick.init()
            sdl_controller.init()
            self.post("Connect your DualSense by USB or Bluetooth.")
            while True:
                try:
                    while True:
                        command = self.commands.get_nowait()
                        if command == "quit":
                            return
                        enabled = command == "start"
                        if not enabled and target is not None:
                            target.reset()
                            target.update()
                            target = None
                            self.latest_input = "Press a button after starting"
                            self.post("Stopped. The virtual Xbox controller is disconnected.")
                except queue.Empty:
                    pass

                pygame.event.pump()
                if source is not None and hasattr(source, "poll"):
                    source.poll()
                if source is not None and not source.attached():
                    source.quit()
                    source = None
                    source_name = None
                    if target is not None:
                        target.reset()
                        target.update()
                        target = None
                    self.post("DualSense disconnected. Reconnect it to continue.")

                if source is None:
                    try:
                        source = find_usb_dualsense()
                    except OSError:
                        source = None
                    if source is not None:
                        source_name = f"{source.name} (USB)"
                        self.post(f"Found {source_name}. Press Start.")
                    else:
                        for index in range(sdl_controller.get_count()):
                            if not sdl_controller.is_controller(index):
                                continue
                            joystick = pygame.joystick.Joystick(index)
                            name = joystick.get_name() or ""
                            joystick.quit()
                            if (
                                "dualsense" in name.lower()
                                or "wireless controller" in name.lower()
                                or "sony" in name.lower()
                                or "ps5 controller" in name.lower()
                            ):
                                source = sdl_controller.Controller(index)
                                source_name = name
                                self.post(f"Found {name}. Press Start.")
                                break

                if enabled and source is not None:
                    if target is None:
                        try:
                            if vg is None:
                                import vgamepad as vg
                                xbox_buttons = [(button, getattr(vg.XUSB_BUTTON, name)) for button, name in BUTTONS]
                            target = vg.VX360Gamepad()
                            self.post(f"Running: {source_name} → Xbox 360 controller", True)
                        except Exception as exc:
                            enabled = False
                            self.post("Virtual controller unavailable. Install ViGEmBus and restart this app. "
                                      f"({type(exc).__name__})")
                    if target is not None:
                        self.latest_input = send_report(source, target, xbox_buttons)
                elif enabled and source is None:
                    self.post("Waiting for DualSense connection…")

                time.sleep(1 / 120)
        except Exception as exc:
            self.post(f"Error: {exc}")
        finally:
            if target is not None:
                target.reset()
                target.update()
            if source is not None:
                source.quit()
            sdl_controller.quit()
            pygame.joystick.quit()
            pygame.display.quit()


class App:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("DualSense → Xbox")
        self.root.geometry("430x250")
        self.root.resizable(False, False)
        self.bridge = Bridge()
        self.active = False

        frame = ttk.Frame(self.root, padding=22)
        frame.pack(fill="both", expand=True)
        ttk.Label(frame, text="DualSense → Xbox", font=("Segoe UI", 17, "bold")).pack(anchor="w")
        ttk.Label(frame, text="Use your PS5 controller in Xbox-only PC games.").pack(anchor="w", pady=(4, 15))
        self.status = tk.StringVar(value="Looking for controller…")
        ttk.Label(frame, textvariable=self.status, wraplength=380).pack(anchor="w", pady=(0, 14))
        self.input_status = tk.StringVar(value="Physical input: press a button after starting")
        ttk.Label(frame, textvariable=self.input_status, wraplength=380).pack(anchor="w", pady=(0, 10))
        self.button = ttk.Button(frame, text="Start", command=self.toggle)
        self.button.pack(anchor="w")
        ttk.Button(frame, text="Get required ViGEmBus driver", command=lambda: webbrowser.open(DRIVER_URL)).pack(
            anchor="w", pady=(12, 0)
        )
        self.root.protocol("WM_DELETE_WINDOW", self.close)
        self.root.after(100, self.poll)

    def toggle(self):
        self.bridge.commands.put("stop" if self.active else "start")
        self.active = not self.active
        self.button.configure(text="Stop" if self.active else "Start")

    def poll(self):
        try:
            while True:
                message, running = self.bridge.events.get_nowait()
                self.status.set(message)
                if message.startswith("Error:") or "unavailable" in message:
                    self.active = False
                    self.button.configure(text="Start")
        except queue.Empty:
            pass
        self.input_status.set(f"Physical input: {self.bridge.latest_input}")
        self.root.after(100, self.poll)

    def close(self):
        self.bridge.commands.put("quit")
        self.bridge.thread.join(timeout=1)
        self.root.destroy()

    def run(self):
        self.root.mainloop()


if __name__ == "__main__":
    App().run()
