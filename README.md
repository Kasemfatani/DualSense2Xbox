# DualSense → Xbox

A small Windows app that reads a PS5 DualSense controller and creates a virtual Xbox 360 controller for games that only accept XInput.

## Use

1. Install the [ViGEmBus driver](https://github.com/nefarius/ViGEmBus/releases/tag/v1.22.0) once, then restart Windows if its installer asks.
2. Connect the DualSense by USB or Bluetooth.
3. Run `dist\DualSenseXbox-USB.exe`, click **Start**, then launch the game.
4. Click **Stop** or close the app when done.

The app maps sticks, triggers, face buttons, shoulders, D-pad, stick clicks, Create/Share, and Options. The PS button is left unmapped because the Xbox Guide button can open Windows Game Bar. The touchpad, motion sensors, adaptive triggers, and advanced haptics are not mapped.

When both USB and Bluetooth connections are present, the app reads the active USB input directly. This avoids an SDL issue where an idle Bluetooth connection can appear as the only controller and show no button presses.

If a game does not respond, press `Win+R`, run `joy.cpl`, select **Xbox 360 Controller**, and check **Properties** while pressing DualSense buttons. If the test responds, fully close the game, start this app, and then reopen the game. If the game reacts twice to one input, it is seeing both the real DualSense and the virtual Xbox controller; hide the physical controller from that game using HidHide or disable the game's native PlayStation input.

If Windows shows an `ms-gamebar` link popup as soon as the virtual Xbox controller connects, turn off **Open Xbox Game Bar using this button on a controller** under **Settings → Gaming → Game Bar**. The popup is a Windows Game Bar shortcut issue and does not mean the virtual controller failed.

## Build from source

Run `powershell -ExecutionPolicy Bypass -File .\build.ps1`. Python 3.14 or a compatible version is required. The build skips vgamepad's automatic driver installer; install the driver separately using the link above.
