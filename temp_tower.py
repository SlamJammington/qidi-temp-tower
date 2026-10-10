"""Build a temperature tower 3MF for QIDI Studio.

The tower (see tower_geometry.py) is a base plate plus one 10 mm floor per
temperature, each with overhangs, a bridge, stringing cones and holes. Each
floor gets its temperature engraved on the front (negative volumes, so QIDI
Studio does the boolean), and the temperature changes are stored as per-layer
custom G-code, which QIDI Studio shows as markers on the layer slider.
"""
import project3mf
import tower_geometry as geo
from project3mf import layer_print_z, project_config  # noqa: F401  (re-exported)
from tower_geometry import build_parts, label_mesh, tower_height  # noqa: F401  (re-exported)

LABEL_MAX_WIDTH = geo.LABEL_MAX_WIDTH


def temperatures(start, end, step):
    """Floor temperatures from the bottom up, e.g. (230, 190, 5) -> 230, 225, ... 190."""
    start, end, step = int(round(start)), int(round(end)), abs(int(round(step)))
    if step <= 0:
        raise ValueError("Step must be at least 1 °C")
    sign = -1 if end < start else 1
    temps = list(range(start, end + sign, sign * step))
    if temps[-1] != end:
        raise ValueError(f"{start}→{end} is not a whole number of {step} °C steps")
    return temps


def write_3mf(path, temps, *, store=None, machine=None, process=None, filament=None,
              wait=False, embed_settings=True):
    """Write the tower. Returns a dict describing what was written."""
    printer = project3mf.Printer(store, machine, process)
    height = tower_height(len(temps))
    printer.check_height(height)
    cmd = "M109" if wait else "M104"
    changes = [(layer_print_z(printer.first_layer, printer.layer, geo.floor_bottom(k)), t)
               for k, t in enumerate(temps)]
    gcodes = [(z, "%s S%d ; temp tower floor %d" % (cmd, t, k + 1)) for k, (z, t) in enumerate(changes)]
    project3mf.write_project(
        path, build_parts(temps), center=printer.center, store=store, machine=machine, process=process,
        filament=filament, embed_settings=embed_settings, layer_gcodes=gcodes,
        description="Temperature tower %d-%d °C" % (temps[0], temps[-1]))
    return {"path": path, "floors": len(temps), "height": height, "changes": changes,
            "center": printer.center, "command": cmd}
