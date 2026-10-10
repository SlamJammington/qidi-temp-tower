# Dev-time builder for assets/digits.json: the digits and a decimal point used
# for engraved labels (end users don't need it). Run with FreeCAD's
# interpreter, which bundles DejaVu Sans Bold through matplotlib:
#   "C:\Program Files\FreeCAD 1.0\bin\freecadcmd.exe" tools/build_digits.py
# Set TT_FONT to use a different TrueType font.
#
# Each digit becomes a prism standing on the tower's front face (x right,
# z up, baseline at z=0), reaching TEXT_DEPTH into the tower (+y) and
# TEXT_OVERSHOOT out of it so the engraving never shares a face with the tower.
import base64
import json
import os
import struct
import sys

import FreeCAD as App
import MeshPart
import Part

HERE = os.path.dirname(os.path.abspath(__file__)) if "__file__" in globals() else os.getcwd()
OUT = os.path.join(os.path.dirname(HERE), "assets", "digits.json")

TEXT_DEPTH = 1.0
TEXT_OVERSHOOT = 0.6
DIGIT_H = 7.0  # height of a digit's ink


def find_font():
    if os.environ.get("TT_FONT"):
        return os.environ["TT_FONT"]
    try:
        import matplotlib
        p = os.path.join(os.path.dirname(matplotlib.__file__), "mpl-data", "fonts", "ttf", "DejaVuSans-Bold.ttf")
        if os.path.isfile(p):
            return p
    except ImportError:
        pass
    sys.exit("DejaVuSans-Bold.ttf not found; set TT_FONT to a .ttf file")


def pack(shape):
    m = MeshPart.meshFromShape(Shape=shape, LinearDeflection=0.005, AngularDeflection=0.1, Relative=False)
    pts, tris = m.Topology
    v = struct.pack("<%df" % (3 * len(pts)), *[c for p in pts for c in (p.x, p.y, p.z)])
    t = struct.pack("<%dI" % (3 * len(tris)), *[i for f in tris for i in f])
    return {"vertices": base64.b64encode(v).decode(), "triangles": base64.b64encode(t).decode(),
            "vcount": len(pts), "tcount": len(tris)}


def main():
    fontdir, fontfile = os.path.split(find_font())
    fontdir += os.sep
    probe = Part.makeWireString("0", fontdir, fontfile, 10.0, 0)
    size = 10.0 * DIGIT_H / Part.Compound([w for c in probe for w in c]).BoundBox.YLength
    pair = Part.makeWireString("00", fontdir, fontfile, size, 0)
    advance = Part.Compound(pair[1]).BoundBox.XMin - Part.Compound(pair[0]).BoundBox.XMin
    zero_left = Part.Compound(Part.makeWireString("0", fontdir, fontfile, size, 0)[0]).BoundBox.XMin

    def advance_of(ch):
        """Pen advance after `ch`: where a following "0" starts, less the 0's own left bearing."""
        wires = Part.makeWireString(ch + "0", fontdir, fontfile, size, 0)
        return Part.Compound(wires[1]).BoundBox.XMin - zero_left

    # Rotation about X: (u, v, w) -> (u, -w, v), so the glyph stands on the
    # front face and w in [-depth, overshoot] becomes y in [-overshoot, depth].
    rot = App.Matrix(1, 0, 0, 0,
                     0, 0, -1, 0,
                     0, 1, 0, 0,
                     0, 0, 0, 1)
    glyphs = {}
    for ch in "0123456789.":
        face = Part.makeFace(Part.makeWireString(ch, fontdir, fontfile, size, 0)[0], "Part::FaceMakerBullseye")
        prism = face.extrude(App.Vector(0, 0, -(TEXT_DEPTH + TEXT_OVERSHOOT)))
        prism.translate(App.Vector(0, 0, TEXT_OVERSHOOT))
        prism = prism.transformGeometry(rot)
        bb = prism.optimalBoundingBox()
        glyphs[ch] = dict(pack(prism), xmin=bb.XMin, xmax=bb.XMax, zmin=bb.ZMin, zmax=bb.ZMax,
                          advance=advance_of(ch))
        print(f"{ch}: {glyphs[ch]['tcount']} triangles, x {bb.XMin:.2f}..{bb.XMax:.2f}, advance {glyphs[ch]['advance']:.2f}")
    data = {"font": fontfile, "digit_height": DIGIT_H, "depth": TEXT_DEPTH, "overshoot": TEXT_OVERSHOOT,
            "advance": advance, "glyphs": glyphs}
    with open(OUT, "w") as f:
        json.dump(data, f)
    print("wrote", OUT, os.path.getsize(OUT), "bytes")


if not getattr(App, "_tt_digits_built", False):  # freecadcmd may execute the file twice
    App._tt_digits_built = True
    main()
