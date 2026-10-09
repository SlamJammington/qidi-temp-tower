"""Read QIDI Studio's printer / filament / process presets from its AppData folder.

QIDI Studio (a Bambu Studio fork) keeps vendor ("system") presets in
%APPDATA%/QIDIStudio/system/<vendor>.json + <vendor>/{machine,filament,process}/,
and the user's own presets in %APPDATA%/QIDIStudio/user/<id>/{machine,filament,process}/.
Presets only store what differs from the preset named in "inherits", so every
preset is resolved by walking that chain.
"""
import json
import sys
import os

KINDS = ("machine", "filament", "process")

# Bookkeeping keys that describe a preset file rather than a setting.
META_KEYS = {
    "name", "inherits", "from", "instantiation", "setting_id", "type", "version",
    "base_id", "user_id", "updated_time", "is_custom_defined", "description",
    "renamed_from", "filament_id", "box_id", "alias",
}


def candidate_roots():
    """Where QIDI Studio keeps its data on each platform."""
    home = os.path.expanduser("~")
    if sys.platform == "win32":
        return [os.path.join(os.environ.get("APPDATA", os.path.join(home, "AppData", "Roaming")), "QIDIStudio")]
    if sys.platform == "darwin":
        return [os.path.join(home, "Library", "Application Support", "QIDIStudio")]
    xdg = os.environ.get("XDG_CONFIG_HOME") or os.path.join(home, ".config")
    return [os.path.join(xdg, "QIDIStudio"),
            os.path.join(home, ".var", "app", "com.qidi3d.QIDIStudio", "config", "QIDIStudio")]  # Flatpak


def default_root():
    roots = candidate_roots()
    for r in roots:
        if os.path.isdir(r):
            return r
    return roots[0]


def read_json(path):
    with open(path, encoding="utf-8") as f:
        text = f.read()
    # QIDIStudio.conf has a trailing "# MD5 checksum" line after the JSON.
    obj, _ = json.JSONDecoder().raw_decode(text.lstrip("﻿"))
    return obj


class Preset:
    def __init__(self, kind, data, path, system):
        self.kind = kind
        self.data = data
        self.path = path
        self.system = system
        self.name = data.get("name") or os.path.splitext(os.path.basename(path))[0]

    @property
    def visible(self):
        # System presets marked instantiation=false are abstract parents.
        return not self.system or str(self.data.get("instantiation", "true")).lower() == "true"

    def __repr__(self):
        return f"Preset({self.kind!r}, {self.name!r}, system={self.system})"


class PresetStore:
    def __init__(self, root=None):
        self.root = root or default_root()
        self.presets = {k: {} for k in KINDS}
        self.app_config = {}
        self._cache = {}
        if not os.path.isdir(self.root):
            raise FileNotFoundError(f"QIDI Studio folder not found: {self.root}")
        self._load_system()
        self._load_user()
        conf = os.path.join(self.root, "QIDIStudio.conf")
        if os.path.isfile(conf):
            try:
                self.app_config = read_json(conf)
            except (OSError, ValueError):
                self.app_config = {}

    # ---------------------------------------------------------------- loading
    def _add(self, kind, path, system):
        try:
            data = read_json(path)
        except (OSError, ValueError):
            return
        if not isinstance(data, dict):
            return
        p = Preset(kind, data, path, system)
        # User presets win over a system preset of the same name.
        if p.name in self.presets[kind] and system and not self.presets[kind][p.name].system:
            return
        self.presets[kind][p.name] = p

    def _load_system(self):
        sysdir = os.path.join(self.root, "system")
        if not os.path.isdir(sysdir):
            return
        for fn in sorted(os.listdir(sysdir)):
            index = os.path.join(sysdir, fn)
            vendor_dir = os.path.join(sysdir, os.path.splitext(fn)[0])
            if not fn.endswith(".json") or not os.path.isdir(vendor_dir):
                continue
            try:
                idx = read_json(index)
            except (OSError, ValueError):
                continue
            for kind, key in (("machine", "machine_list"), ("filament", "filament_list"),
                              ("process", "process_list")):
                for entry in idx.get(key, []):
                    sub = entry.get("sub_path")
                    if sub:
                        self._add(kind, os.path.join(vendor_dir, sub), True)

    def _load_user(self):
        userdir = os.path.join(self.root, "user")
        if not os.path.isdir(userdir):
            return
        for uid in sorted(os.listdir(userdir)):
            for kind in KINDS:
                d = os.path.join(userdir, uid, kind)
                for sub in (d, os.path.join(d, "base")):
                    if not os.path.isdir(sub):
                        continue
                    for fn in sorted(os.listdir(sub)):
                        if fn.endswith(".json"):
                            self._add(kind, os.path.join(sub, fn), False)

    # ------------------------------------------------------------- resolving
    def get(self, kind, name):
        return self.presets[kind].get(name)

    def resolve(self, kind, name, _seen=None):
        """Full settings of a preset with its inheritance chain applied."""
        key = (kind, name)
        if key in self._cache:
            return dict(self._cache[key])
        p = self.get(kind, name)
        if p is None:
            raise KeyError(f"{kind} preset not found: {name}")
        seen = _seen or set()
        if name in seen:
            raise ValueError(f"inheritance loop at {kind} preset {name}")
        seen.add(name)
        parent = p.data.get("inherits") or ""
        out = self.resolve(kind, parent, seen) if parent and self.get(kind, parent) else {}
        out.update(p.data)
        self._cache[key] = dict(out)
        return out

    def system_parent(self, kind, name):
        """Nearest system preset in the chain (the preset itself if it is one)."""
        seen = set()
        while name and name not in seen:
            seen.add(name)
            p = self.get(kind, name)
            if p is None:
                return None
            if p.system:
                return p.name
            name = p.data.get("inherits") or ""
        return None

    # --------------------------------------------------------------- listing
    def names(self, kind):
        return sorted((p.name for p in self.presets[kind].values() if p.visible), key=str.lower)

    def compatible(self, kind, name, machine):
        """Whether a filament/process preset lists the machine (or its system parent)."""
        cfg = self.resolve(kind, name)
        allowed = cfg.get("compatible_printers") or []
        if isinstance(allowed, str):
            allowed = [allowed] if allowed else []
        if not allowed:
            return True
        targets = {machine, self.system_parent("machine", machine)}
        return any(t in allowed for t in targets if t)

    def selected(self):
        """Presets currently selected in QIDI Studio: (machine, process, [filaments])."""
        pr = self.app_config.get("presets", {}) if isinstance(self.app_config, dict) else {}
        fil = pr.get("filaments") or []
        if isinstance(fil, str):
            fil = [fil]
        return pr.get("machine"), pr.get("process"), fil

    def app_version(self):
        app = self.app_config.get("app", {}) if isinstance(self.app_config, dict) else {}
        return app.get("version") or "02.07.02.60"


def first(v, default=None):
    """First element of a preset value (most settings are per-extruder lists)."""
    if isinstance(v, list):
        return v[0] if v else default
    return default if v is None else v


def as_float(v, default=0.0):
    try:
        return float(first(v, default))
    except (TypeError, ValueError):
        return default


def bed_shape(machine_cfg):
    """(min_x, min_y, max_x, max_y) of printable_area."""
    pts = []
    area = machine_cfg.get("printable_area") or ["0x0", "200x0", "200x200", "0x200"]
    if isinstance(area, str):
        area = area.split(",")
    for p in area:
        try:
            x, y = p.strip().split("x")
            pts.append((float(x), float(y)))
        except ValueError:
            pass
    if not pts:
        return 0.0, 0.0, 200.0, 200.0
    xs, ys = zip(*pts)
    return min(xs), min(ys), max(xs), max(ys)
