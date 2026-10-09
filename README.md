# QIDI Studio Temperature Tower Generator

QIDI Studio doesn't have a temperature tower calibration. This tool makes one: it reads your printers, filaments and process presets from QIDI Studio and writes a ready-to-slice `.3mf` project. Each floor of the tower prints at a different nozzle temperature, with the temperature engraved on the front.

![Generator window](docs/generator.png)

![The tower sliced in QIDI Studio, with a temperature change marker for each floor](docs/qidi-preview.png)

## Features

- **Uses your own presets.** It lists the printers, processes and filaments you have in QIDI Studio, including your custom ones, and only shows presets that work with the chosen printer.
- **Sensible defaults.** The temperature range comes from the filament's recommended range, hottest at the bottom, in 5 °C steps. It warns you if the tower won't fit under your printer's height limit.
- **Opens ready to slice.** The selected presets are embedded in the project, so QIDI Studio opens it with that printer, process and filament selected. Supports are turned off for the tower.
- **Temperature changes you can see.** Each change is a custom G-code marker on QIDI Studio's layer slider (`M104 S…`, or `M109` if you'd rather the printer wait at each change).
- **No dependencies.** It's plain Python 3 with Tkinter. There's a window and a command line.

## The tower

The base is 1 mm thick, and there's one 10 mm floor per temperature. Each floor tests:

| Feature | What to look for |
|---|---|
| Engraved temperature on the front block | Which floor you're looking at |
| 45° overhang (left) and 35° overhang (right) | Drooping or curling on the underside |
| 30 mm bridge | Sagging strands |
| Two cones between the pillars | Stringing and blobs from travel moves |
| Vertical 3 mm hole and horizontal 4 mm hole | Round, clean holes |

Pick the floor that looks best overall. Hotter usually means better layer bonding, glossier walls and more stringing. Cooler means cleaner overhangs and bridges.

The geometry is generated in code (`tower_geometry.py`). It's an original design in the spirit of the classic "all-in-one" temperature towers.

## Install

You need [Python 3.8+](https://www.python.org/downloads/) with Tkinter, which the python.org installers include. On Linux you may need your distro's `python3-tk` package.

Download this repository (**Code → Download ZIP**, or `git clone`) and unzip it anywhere.

## Use

**Windows:** double-click `Temp Tower.bat`.

**macOS / Linux:**

```bash
python3 qidi_temp_tower.py
```

Pick a printer, process and filament, check the temperatures, then click **Generate** or **Generate & open in QIDI Studio**.

### Command line

```bash
python3 qidi_temp_tower.py --list filament
python3 qidi_temp_tower.py --filament "Generic PLA @Qidi X-Max 4 0.4 nozzle" --start 230 --end 190 --step 5 --open
python3 qidi_temp_tower.py --help
```

Any preset you don't specify defaults to the one currently selected in QIDI Studio.

### Where it looks for QIDI Studio

| OS | Presets folder |
|---|---|
| Windows | `%APPDATA%\QIDIStudio` |
| macOS | `~/Library/Application Support/QIDIStudio` |
| Linux | `~/.config/QIDIStudio` (or the Flatpak config folder) |

If yours is elsewhere, use **Browse…** in the window or `--qidi-dir` on the command line.

## Notes

- The temperature changes on the first layer of each floor. The base prints at the filament preset's own temperatures.
- The markers use the layer heights of the process you picked. If you change the layer height in QIDI Studio afterwards, each change still lands within a layer of the start of its floor.
- The engraved numbers and holes are negative volumes ("Label 230", "Holes") in QIDI Studio's object list. You can delete them there.
- Tested with QIDI Studio 2.07 on Windows with an X-Max 4. The macOS and Linux paths follow QIDI Studio's standard locations but haven't been tested on real installs. Reports are welcome.

## Development

Run the tests (they use a small fake preset folder in `tests/fixtures`, so QIDI Studio isn't needed):

```bash
python3 -m unittest discover -s tests -v
```

| File | Purpose |
|---|---|
| `qidi_temp_tower.py` | Window and command line |
| `qidi_profiles.py` | Finds QIDI Studio's presets and resolves their `inherits` chains |
| `temp_tower.py` | Writes the 3MF: parts, per-layer G-code, embedded project settings |
| `tower_geometry.py` | The tower, built from simple solids |
| `tools/build_digits.py` | Rebuilds `assets/digits.json`, the engraving glyphs (needs FreeCAD) |

To make a quick check against the real slicer, slice the output with QIDI Studio's command line and look for the `; temp tower floor` lines in the G-code:

```bash
qidi-studio --slice 1 --outputdir out tower.3mf
```

## License

The code is under the [MIT License](LICENSE). The digit shapes in `assets/digits.json` are made from DejaVu Sans Bold. Their license is in [assets/LICENSE-DejaVu-font.txt](assets/LICENSE-DejaVu-font.txt).

QIDI and QIDI Studio are trademarks of QIDI Technology. This project isn't affiliated with them.
