"""Stands in for QIDI Studio's command-line slicer in the tests.

Accepts `--slice 1 --export-3mf NAME --outputdir DIR PROJECT` and writes DIR/NAME:
the project plus a small synthetic Metadata/plate_1.gcode in QIDI Studio's
style (relative extrusion, a wipe and a retraction before every travel, and
an un-retraction afterwards), using the project's retraction length.
"""
import hashlib
import json
import os
import sys
import zipfile


def gcode(retraction, height, layer=0.2, extra=0.0, nozzle="210"):
    lines = ["; HEADER_BLOCK_START", "; total layer number: %d" % round(height / layer), "; HEADER_BLOCK_END",
             "M83", "G1 E5 F80 ; prime in the start G-code, must stay untouched",
             "; MACHINE_START_GCODE_END"]
    z = layer
    while z <= height + 1e-6:
        lines += ["; CHANGE_LAYER", "; Z_HEIGHT: %g" % round(z, 4), "; LAYER_HEIGHT: %g" % layer,
                  "G1 X10 Y10 E1.2", "G1 X20 Y10 E1.2",
                  "; WIPE_START", "G1 X18 Y10 E-%s" % round(retraction * 0.95, 5), "; WIPE_END",
                  "G1 E-%s F1800" % round(retraction * 0.05, 5),
                  "G1 X60 Y10 F30000",
                  "G1 E%s F1800" % round(retraction + extra, 5),
                  "G1 X70 Y10 E1.2"]
        z += layer
    lines += ["; MACHINE_END_GCODE_START", "G1 E-3 F1800 ; end G-code retraction, must stay untouched",
              "; CONFIG_BLOCK_START", "; nozzle_temperature = %s" % nozzle,
              "; retraction_length = %s" % retraction, "; CONFIG_BLOCK_END", ""]
    return "\n".join(lines)


def tiny_png(w=4, h=3):
    """A small grey PNG, standing in for the plate picture QIDI Studio renders."""
    import struct
    import zlib

    def chunk(kind, data):
        return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data))
    raw = b"".join(b"\x00" + b"\x80" * w for _ in range(h))
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 0, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(raw)) + chunk(b"IEND", b""))


def main(argv):
    out_name = argv[argv.index("--export-3mf") + 1]
    out_dir = argv[argv.index("--outputdir") + 1]
    project = argv[-1]
    with zipfile.ZipFile(project) as z:
        cfg = json.loads(z.read("Metadata/project_settings.config"))
        entries = {n: z.read(n) for n in z.namelist()}
    retraction = float(cfg["filament_retraction_length"][0])
    height = float(os.environ.get("FAKE_SLICER_HEIGHT", "11"))
    extra = float(os.environ.get("FAKE_SLICER_EXTRA", "0"))
    code = gcode(retraction, height, extra=extra, nozzle=cfg.get("nozzle_temperature", ["210"])[0]).encode()
    entries["Metadata/plate_1.gcode"] = code
    entries["Metadata/plate_1.gcode.md5"] = hashlib.md5(code).hexdigest().upper().encode()
    entries["Metadata/plate_1.png"] = tiny_png()
    with zipfile.ZipFile(os.path.join(out_dir, out_name), "w") as z:
        for n, data in entries.items():
            z.writestr(n, data)
    with open(os.path.join(out_dir, "result.json"), "w") as f:
        json.dump({"return_code": 0, "error_string": "Success."}, f)


if __name__ == "__main__":
    main(sys.argv[1:])
