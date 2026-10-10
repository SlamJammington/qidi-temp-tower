import base64
import os
import re
import sys
import tempfile
import unittest
from unittest import mock

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TESTS = os.path.join(ROOT, "tests")
sys.path.insert(0, ROOT)
sys.path.insert(0, TESTS)
import fake_slicer  # noqa: E402
import qidi_profiles as qp  # noqa: E402
import retraction_test as rt  # noqa: E402

FIXTURE = os.path.join(TESTS, "fixtures", "QIDIStudio")
PRESETS = dict(machine="My Printer", process="0.20mm Standard @Test", filament="My PLA")


def retractions_by_band(gcode):
    """{band value: (wipe E, retract E, unretract E)} from the first layer of each band."""
    found, band, body = {}, None, False
    for line in gcode.split("\n"):
        if line.startswith(rt.START_MARK):
            body = True
        if line.startswith(rt.END_MARK):
            body = False
        m = re.match(r"; RETRACTION_TEST band \d+: ([\d.]+) mm", line)
        if m:
            band = m.group(1)
            found[band] = []
        elif body and band and len(found[band]) < 3:
            e = re.search(r"\bE(-?[\d.]+)", line)
            if e and (float(e.group(1)) < 0 or line.startswith("G1 E")):
                found[band].append(float(e.group(1)))
    return found


class LengthTests(unittest.TestCase):
    def test_lengths(self):
        self.assertEqual(rt.lengths(0, 1, 0.2), [0.0, 0.2, 0.4, 0.6, 0.8, 1.0])
        self.assertEqual(rt.lengths(2, 1, 0.5), [2.0, 1.5, 1.0])
        with self.assertRaises(ValueError):
            rt.lengths(0, 1, 0.3)
        with self.assertRaises(ValueError):
            rt.lengths(-1, 1, 0.5)

    def test_fmt(self):
        self.assertEqual([rt.fmt(x) for x in (0, 0.2, 1, 1.25, 2.5)], ["0.0", "0.2", "1.0", "1.25", "2.5"])

    def test_defaults_and_preset_value(self):
        store = qp.PresetStore(FIXTURE)
        self.assertEqual(rt.defaults(store, "My Printer"), (0.0, 2.0, 0.2))  # direct drive
        self.assertEqual(rt.preset_retraction(store, "My Printer", "My PLA"), 0.8)


class RewriteTests(unittest.TestCase):
    def test_each_band_gets_its_length(self):
        values = [0.0, 0.5, 1.0, 2.0]
        src = fake_slicer.gcode(retraction=2.0, height=1 + 4 * 2.0)
        new, counts = rt.rewrite_retractions(src, values, band_h=2.0, reference=2.0)
        bands = retractions_by_band(new)
        self.assertEqual(sorted(bands), ["0.0", "0.5", "1.0", "2.0"])
        for value, (wipe, retract, unretract) in bands.items():
            v = float(value)
            self.assertAlmostEqual(wipe, -0.95 * v, places=4)
            self.assertAlmostEqual(retract, -0.05 * v, places=4)
            self.assertAlmostEqual(unretract, v, places=4)
        self.assertTrue(all(counts))

    def test_extrusion_is_unchanged_and_start_end_gcode_untouched(self):
        src = fake_slicer.gcode(retraction=1.0, height=11, extra=0.1)
        new, _ = rt.rewrite_retractions(src, [0.2, 0.6], band_h=5.0, reference=1.0)
        self.assertAlmostEqual(rt.body_extrusion(new), rt.body_extrusion(src), places=6)
        self.assertIn("G1 E5 F80 ; prime", new)
        self.assertIn("G1 E-3 F1800 ; end G-code", new)
        # "Extra length on restart" (0.1) is kept on top of the scaled retraction.
        self.assertEqual(retractions_by_band(new)["0.6"][2], 0.7)


class TestPieceTests(unittest.TestCase):
    def test_parts(self):
        parts = rt.build_parts([0.0, 0.2, 1.25], band_h=5.0)
        self.assertEqual([p[1] for p in parts], ["normal_part"] * 3 + ["negative_part"])
        solid = [v for _, sub, m in parts if sub == "normal_part" for v in m.verts]
        xs, ys = [v[0] for v in solid], [v[1] for v in solid]
        self.assertAlmostEqual(min(xs) + max(xs), 0, places=6)
        self.assertAlmostEqual(min(ys) + max(ys), 0, places=6)
        self.assertAlmostEqual(max(v[2] for v in solid), rt.test_height(3, 5.0))
        labels = parts[-1][2]
        left_edge = -(2 * rt.TOWER_W + rt.GAP) / 2
        self.assertTrue(all(left_edge < v[0] < left_edge + rt.TOWER_W for v in labels.verts))


class GenerateTests(unittest.TestCase):
    def test_end_to_end_with_fake_slicer(self):
        store = qp.PresetStore(FIXTURE)
        values = rt.lengths(0, 1, 0.5)
        fake = [sys.executable, os.path.join(TESTS, "fake_slicer.py")]
        with tempfile.TemporaryDirectory() as d, \
                mock.patch("studio.cli_command", return_value=fake), \
                mock.patch.dict(os.environ, {"FAKE_SLICER_HEIGHT": str(rt.test_height(3, 5.0))}):
            out = os.path.join(d, "test.gcode")
            r = rt.generate(out, values, store=store, band_h=5.0, nozzle_temp=215, **PRESETS)
            self.assertEqual(r["bands"], 3)
            with open(out, encoding="utf-8") as f:
                gcode = f.read()
        # Sliced with the chosen temperature and the largest length as the reference.
        self.assertIn("; nozzle_temperature = 215", gcode)
        self.assertIn("; retraction_length = 1.0", gcode)
        self.assertIn("; RETRACTION_TEST: 0.0 -> 1.0 mm", gcode)
        self.assertEqual([round(b[2], 4) for b in retractions_by_band(gcode).values()], [0.0, 0.5, 1.0])
        # The plate picture rides along as a thumbnail the printer can show.
        m = re.search(r"; thumbnail begin 4x3 (\d+)\n((?:; .*\n)+?); thumbnail end", gcode)
        self.assertIsNotNone(m)
        data = "".join(line[2:] for line in m.group(2).splitlines())
        self.assertEqual(len(data), int(m.group(1)))
        self.assertEqual(base64.b64decode(data), fake_slicer.tiny_png())

    def test_needs_qidi_studio(self):
        store = qp.PresetStore(FIXTURE)
        with tempfile.TemporaryDirectory() as d, mock.patch("studio.cli_command", return_value=None):
            with self.assertRaises(FileNotFoundError):
                rt.generate(os.path.join(d, "x.gcode"), [0.0, 1.0], store=store, **PRESETS)


if __name__ == "__main__":
    unittest.main()
