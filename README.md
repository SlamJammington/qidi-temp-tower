# QIDI Studio Temperature Tower & Retraction Test

QIDI Studio doesn't have temperature tower or retraction test calibrations, so this app makes them. Pick your printer, process and filament from your QIDI Studio presets and choose a range:

- **Temperature tower:** a ready-to-slice `.3mf` where each floor prints at a different temperature, with that temperature engraved on the front.
- **Retraction test:** two towers whose bands print with different retraction lengths, each labelled. QIDI Studio can't vary retraction by height, so the app slices this one for you with QIDI Studio and saves ready-to-print G-code. QIDI Studio can preview that file but can't send it, so the app can upload it to the network printer you set up in QIDI Studio. You can also copy it to the printer yourself.

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

The retraction test needs QIDI Studio installed on the same computer, because the app uses it to slice the test.

## Reading the results

**Temperature tower:** each 10 mm floor has a 45° and a 35° overhang, a bridge, two stringing cones and a couple of holes. Pick the floor that looks best overall. Hotter usually means stronger layers and more stringing. Cooler usually means cleaner overhangs and bridges.

**Retraction test:** print it at the temperature you picked from the tower. Look at the strings between the two towers and find the lowest band without strings or blobs. Use that band's length (engraved on the left tower) as your retraction length. Going much higher than needed can cause under-extrusion and wear on the filament.

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
