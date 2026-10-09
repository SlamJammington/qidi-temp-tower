# QIDI Studio Temperature Tower Generator

QIDI Studio doesn't have a temperature tower calibration, so this app makes one. Pick your printer, process and filament from your QIDI Studio presets and choose a temperature range. It writes a ready-to-slice `.3mf` where each floor prints at a different temperature, with that temperature engraved on the front.

![Generator window](docs/generator.png)

![The tower sliced in QIDI Studio, with a temperature change marker for each floor](docs/qidi-preview.png)

## Download

Get the latest version from the [Releases page](https://github.com/SlamJammington/qidi-temp-tower/releases/latest):

| System | File | How to start it |
|---|---|---|
| Windows 10/11 | `QidiTempTower-windows.exe` | Double-click it. Nothing to install. |
| macOS (Apple silicon) | `QidiTempTower-macos.zip` | Unzip, then right-click **QidiTempTower** → **Open** the first time. |
| Linux (x86-64) | `QidiTempTower-linux.tar.gz` | Extract, then run `./QidiTempTower`. |

The apps aren't code-signed, so your system will warn you the first time. On Windows, click **More info → Run anyway**. On macOS, right-click → **Open**.

## Reading the tower

Each 10 mm floor has a 45° and a 35° overhang, a bridge, two stringing cones and a couple of holes. Pick the floor that looks best overall. Hotter usually means stronger layers and more stringing. Cooler usually means cleaner overhangs and bridges.

## Running from source

You need [Python 3.8+](https://www.python.org/downloads/) with Tkinter, which the python.org installers include. On Linux you may need your distro's `python3-tk` package.

Download this repository (**Code → Download ZIP**, or `git clone`). Then run:

```bash
python3 qidi_temp_tower.py
```

On Windows you can double-click `Temp Tower.bat` instead.

## Building the app yourself

```bash
pip install pyinstaller
pyinstaller qidi_temp_tower.spec
```

The app is created in the `dist` folder.

## License

[MIT](LICENSE). The engraved digits come from DejaVu Sans Bold, whose license is in [assets/LICENSE-DejaVu-font.txt](assets/LICENSE-DejaVu-font.txt).

QIDI and QIDI Studio are trademarks of QIDI Technology. This project isn't affiliated with them.

---

*This app was generated with [Claude](https://claude.ai), Anthropic's AI assistant.*
