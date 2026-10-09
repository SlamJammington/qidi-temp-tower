"""QIDI Studio temperature tower generator (GUI, or command line with --help)."""
import argparse
import os
import re
import shutil
import subprocess
import sys
import traceback

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import qidi_profiles as qp  # noqa: E402
import temp_tower as tt  # noqa: E402
from tower_geometry import HERE as DATA_DIR  # noqa: E402

__version__ = "1.0.0"
APP_NAME = "QIDI Studio Temperature Tower"

def _windows_install_dirs():
    dirs = [os.path.join(os.environ.get(v, d), "QIDIStudio")
            for v, d in (("ProgramFiles", r"C:\Program Files"), ("ProgramFiles(x86)", r"C:\Program Files (x86)"))]
    try:  # the installer records its folder in the uninstall key
        import winreg
        for hive in (winreg.HKEY_LOCAL_MACHINE, winreg.HKEY_CURRENT_USER):
            try:
                base = winreg.OpenKey(hive, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall")
            except OSError:
                continue
            for i in range(winreg.QueryInfoKey(base)[0]):
                try:
                    sub = winreg.OpenKey(base, winreg.EnumKey(base, i))
                    if "qidistudio" in str(winreg.QueryValueEx(sub, "DisplayName")[0]).lower().replace(" ", ""):
                        dirs.append(winreg.QueryValueEx(sub, "InstallLocation")[0])
                except OSError:
                    pass
    except ImportError:
        pass
    return dirs


def studio_command():
    """Command prefix that opens a file in QIDI Studio, or None if it isn't installed."""
    if sys.platform == "win32":
        for d in _windows_install_dirs():
            exe = os.path.join(d, "qidi-studio.exe")
            if d and os.path.isfile(exe):
                return [exe]
    elif sys.platform == "darwin":
        for app in ("/Applications/QIDIStudio.app", os.path.expanduser("~/Applications/QIDIStudio.app")):
            if os.path.isdir(app):
                return ["open", "-a", app]
    for name in ("qidi-studio", "QIDIStudio", "qidistudio"):
        exe = shutil.which(name)
        if exe:
            return [exe]
    return None


def open_in_studio(path):
    cmd = studio_command()
    if not cmd:
        raise FileNotFoundError("QIDI Studio was not found; open the 3MF yourself")
    subprocess.Popen(cmd + [path])


def filament_defaults(store, filament):
    """(start, end, step) suggested from the filament's recommended range, hottest at the bottom."""
    f = store.resolve("filament", filament)
    lo = int(qp.as_float(f.get("nozzle_temperature_range_low"), 0))
    hi = int(qp.as_float(f.get("nozzle_temperature_range_high"), 0))
    nominal = int(qp.as_float(f.get("nozzle_temperature"), 210))
    if not lo or not hi or hi <= lo:
        lo, hi = nominal - 20, nominal + 20
    step = 5
    lo -= (lo % step)
    hi -= (hi % step)
    return hi, lo, step


def safe_filename(s):
    return re.sub(r'[<>:"/\\|?*]+', "_", s).strip() or "temp_tower"


def default_output_dir(store):
    app = store.app_config.get("app", {}) if store and isinstance(store.app_config, dict) else {}
    for d in (app.get("last_export_path"), app.get("download_path"),
              os.path.join(os.path.expanduser("~"), "Downloads")):
        if d and os.path.isdir(d):
            return d
    return os.path.expanduser("~")


def default_output(store, filament, temps):
    short = filament.split("@")[0].strip()
    return os.path.join(default_output_dir(store),
                        safe_filename("Temp Tower %s %d-%d" % (short, temps[0], temps[-1])) + ".3mf")


# ---------------------------------------------------------------------- CLI
def run_cli(argv):
    for stream in (sys.stdout, sys.stderr):
        try:  # a preset name the console's code page can't show shouldn't crash the listing
            stream.reconfigure(errors="replace")
        except (AttributeError, ValueError):
            pass
    ap = argparse.ArgumentParser(prog="qidi_temp_tower", description=__doc__)
    ap.add_argument("--version", action="version", version="%(prog)s " + __version__)
    ap.add_argument("--qidi-dir", help="QIDI Studio data folder (default: %s)" % qp.default_root().replace("%", "%%"))
    ap.add_argument("--printer", help="printer preset (default: the one selected in QIDI Studio)")
    ap.add_argument("--process", help="process preset (default: the one selected in QIDI Studio)")
    ap.add_argument("--filament", help="filament preset (default: the one selected in QIDI Studio)")
    ap.add_argument("--start", type=int, help="bottom floor temperature (default: filament max)")
    ap.add_argument("--end", type=int, help="top floor temperature (default: filament min)")
    ap.add_argument("--step", type=int, default=5)
    ap.add_argument("--wait", action="store_true", help="use M109 (wait) instead of M104")
    ap.add_argument("--no-settings", action="store_true",
                    help="don't embed presets; QIDI Studio keeps whatever is selected")
    ap.add_argument("--list", choices=["printer", "process", "filament"], help="list presets and exit")
    ap.add_argument("--open", action="store_true", help="open the result in QIDI Studio")
    ap.add_argument("-o", "--output", help="output .3mf path")
    ap.add_argument("--cli", action="store_true", help=argparse.SUPPRESS)
    a = ap.parse_args(argv)

    store = qp.PresetStore(a.qidi_dir)
    sel_m, sel_p, sel_f = store.selected()
    machine = a.printer or sel_m
    if a.list:
        kind = {"printer": "machine"}.get(a.list, a.list)
        for n in store.names(kind):
            if kind == "machine" or not machine or store.compatible(kind, n, machine):
                print(n)
        return 0
    process = a.process or sel_p
    filament = a.filament or (sel_f[0] if sel_f else None)
    for kind, name in (("machine", machine), ("process", process), ("filament", filament)):
        if not name or not store.get(kind, name):
            sys.exit(f"{kind} preset not found: {name!r} (use --list)")
    d_start, d_end, _ = filament_defaults(store, filament)
    temps = tt.temperatures(a.start if a.start is not None else d_start,
                            a.end if a.end is not None else d_end, a.step)
    out = a.output or default_output(store, filament, temps)
    r = tt.write_3mf(out, temps, store=store, machine=machine, process=process, filament=filament,
                     wait=a.wait, embed_settings=not a.no_settings)
    print("Wrote %s\n  %d floors, %g mm tall, %s at z = %s" % (
        r["path"], r["floors"], r["height"], r["command"],
        ", ".join("%g (%d°C)" % c for c in r["changes"])))
    if a.open:
        open_in_studio(out)
    return 0


# ---------------------------------------------------------------------- GUI
def run_gui():
    import tkinter as tk
    from tkinter import ttk, filedialog, messagebox

    try:  # crisp text on high-DPI Windows displays
        import ctypes
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except (AttributeError, OSError):
        pass
    root = tk.Tk()
    root.title("%s %s" % (APP_NAME, __version__))
    try:
        root.iconphoto(True, tk.PhotoImage(file=os.path.join(DATA_DIR, "assets", "icon.png")))
    except tk.TclError:
        pass
    root.minsize(560, 0)

    state = {"store": None}
    v = {k: tk.StringVar() for k in ("dir", "printer", "process", "filament", "start", "end",
                                     "step", "info", "summary", "output")}
    v_wait = tk.BooleanVar(value=False)
    v_embed = tk.BooleanVar(value=True)
    v_all = tk.BooleanVar(value=False)
    v["dir"].set(qp.default_root())
    v["step"].set("5")

    frm = ttk.Frame(root, padding=12)
    frm.grid(sticky="nsew")
    root.columnconfigure(0, weight=1)
    frm.columnconfigure(1, weight=1)
    row = 0

    def label(text, r, **kw):
        ttk.Label(frm, text=text).grid(row=r, column=0, sticky="w", padx=(0, 8), pady=3, **kw)

    label("QIDI Studio folder", row)
    ttk.Entry(frm, textvariable=v["dir"]).grid(row=row, column=1, sticky="ew", pady=3)
    ttk.Button(frm, text="Browse…", command=lambda: browse_dir()).grid(row=row, column=2, padx=(6, 0))
    row += 1

    combos = {}
    for key, text in (("printer", "Printer"), ("process", "Process"), ("filament", "Filament")):
        label(text, row)
        cb = ttk.Combobox(frm, textvariable=v[key], state="readonly", height=25)
        cb.grid(row=row, column=1, columnspan=2, sticky="ew", pady=3)
        combos[key] = cb
        row += 1
    ttk.Checkbutton(frm, text="Show presets for other printers too", variable=v_all,
                    command=lambda: refresh_lists()).grid(row=row, column=1, columnspan=2, sticky="w")
    row += 1
    ttk.Label(frm, textvariable=v["info"], foreground="#555").grid(row=row, column=1, columnspan=2,
                                                                    sticky="w", pady=(2, 8))
    row += 1

    temps_frm = ttk.Frame(frm)
    temps_frm.grid(row=row, column=1, columnspan=2, sticky="w")
    label("Temperatures", row)
    for i, (key, text) in enumerate((("start", "Bottom"), ("end", "Top"), ("step", "Step"))):
        ttk.Label(temps_frm, text=text).grid(row=0, column=2 * i, padx=(0 if i == 0 else 12, 4))
        sp = ttk.Spinbox(temps_frm, textvariable=v[key], from_=1 if key == "step" else 100,
                         to=50 if key == "step" else 500, increment=1 if key == "step" else 5, width=6,
                         command=lambda: update_summary())
        sp.grid(row=0, column=2 * i + 1)
        sp.bind("<KeyRelease>", lambda e: update_summary())
    ttk.Label(temps_frm, text="°C").grid(row=0, column=6, padx=(4, 0))
    ttk.Button(temps_frm, text="Use filament range", command=lambda: apply_filament_range()).grid(
        row=0, column=7, padx=(12, 0))
    row += 1
    ttk.Label(frm, textvariable=v["summary"], foreground="#555").grid(row=row, column=1, columnspan=2,
                                                                       sticky="w", pady=(2, 8))
    row += 1

    label("Options", row)
    ttk.Checkbutton(frm, text="Wait for each temperature (M109) instead of changing on the fly (M104)",
                    variable=v_wait).grid(row=row, column=1, columnspan=2, sticky="w")
    row += 1
    ttk.Checkbutton(frm, text="Embed the printer / process / filament presets in the 3MF",
                    variable=v_embed).grid(row=row, column=1, columnspan=2, sticky="w")
    row += 1

    label("Save as", row)
    ttk.Entry(frm, textvariable=v["output"]).grid(row=row, column=1, sticky="ew", pady=(10, 3))
    ttk.Button(frm, text="Browse…", command=lambda: browse_out()).grid(row=row, column=2, padx=(6, 0),
                                                                     pady=(10, 3))
    row += 1

    btns = ttk.Frame(frm)
    btns.grid(row=row, column=0, columnspan=3, sticky="e", pady=(10, 0))
    ttk.Button(btns, text="Generate", command=lambda: generate(False)).grid(row=0, column=0, padx=4)
    open_btn = ttk.Button(btns, text="Generate & open in QIDI Studio", command=lambda: generate(True))
    open_btn.grid(row=0, column=1, padx=4)
    if not studio_command():
        open_btn.state(["disabled"])
    row += 1
    status = tk.StringVar()
    ttk.Label(frm, textvariable=status, wraplength=620, justify="left").grid(
        row=row, column=0, columnspan=3, sticky="w", pady=(10, 0))

    out_auto = {"value": ""}

    def store():
        return state["store"]

    def load_store():
        try:
            state["store"] = qp.PresetStore(v["dir"].get().strip() or None)
        except Exception as e:  # noqa: BLE001
            state["store"] = None
            status.set("Could not read QIDI Studio presets: %s" % e)
            for cb in combos.values():
                cb["values"] = []
            return
        st = state["store"]
        sel_m, sel_p, sel_f = st.selected()
        machines = st.names("machine")
        combos["printer"]["values"] = machines
        v["printer"].set(sel_m if sel_m in machines else (machines[0] if machines else ""))
        refresh_lists(prefer_process=sel_p, prefer_filament=sel_f[0] if sel_f else None)
        status.set("Loaded %d printer, %d process and %d filament presets from %s" % (
            len(machines), len(st.names("process")), len(st.names("filament")), st.root))

    def refresh_lists(prefer_process=None, prefer_filament=None):
        st = store()
        if not st:
            return
        m = v["printer"].get()
        for key, kind, prefer in (("process", "process", prefer_process),
                                  ("filament", "filament", prefer_filament)):
            names = [n for n in st.names(kind) if v_all.get() or not m or st.compatible(kind, n, m)]
            # User presets first, they're the ones people tune.
            names.sort(key=lambda n: (st.get(kind, n).system, n.lower()))
            combos[key]["values"] = names
            cur = prefer or v[key].get()
            if cur not in names:
                cur = names[0] if names else ""
            v[key].set(cur)
        on_filament()

    def on_filament(_e=None):
        st = store()
        f = v["filament"].get()
        if not st or not f:
            v["info"].set("")
            return
        cfg = st.resolve("filament", f)
        v["info"].set("%s · recommended %s–%s °C · preset nozzle temp %s °C" % (
            qp.first(cfg.get("filament_type"), "?"), qp.first(cfg.get("nozzle_temperature_range_low"), "?"),
            qp.first(cfg.get("nozzle_temperature_range_high"), "?"), qp.first(cfg.get("nozzle_temperature"), "?")))
        apply_filament_range()

    def apply_filament_range():
        st = store()
        if not st or not v["filament"].get():
            return
        s, e, step = filament_defaults(st, v["filament"].get())
        v["start"].set(str(s))
        v["end"].set(str(e))
        v["step"].set(str(step))
        update_summary()

    def current_temps():
        return tt.temperatures(int(v["start"].get()), int(v["end"].get()), int(v["step"].get()))

    def update_summary():
        try:
            nums = [int(v[k].get()) for k in ("start", "end", "step")]
        except ValueError:
            v["summary"].set("Enter whole numbers")
            return
        try:
            temps = tt.temperatures(*nums)
        except ValueError as e:
            v["summary"].set(str(e))
            return
        h = tt.tower_height(len(temps))
        msg = "%d floors, %g mm tall: %s" % (len(temps), h, " → ".join(map(str, temps)))
        st = store()
        if st and v["printer"].get():
            max_h = qp.as_float(st.resolve("machine", v["printer"].get()).get("printable_height"), 0)
            if max_h and h > max_h:
                msg += "   ⚠ taller than the printer's %g mm" % max_h
        v["summary"].set(msg)
        if st and v["filament"].get() and (not v["output"].get() or v["output"].get() == out_auto["value"]):
            out_auto["value"] = default_output(st, v["filament"].get(), temps)
            v["output"].set(out_auto["value"])

    def browse_dir():
        d = filedialog.askdirectory(initialdir=v["dir"].get() or None, title="QIDI Studio data folder")
        if d:
            v["dir"].set(os.path.normpath(d))
            load_store()

    def browse_out():
        cur = v["output"].get()
        p = filedialog.asksaveasfilename(defaultextension=".3mf", filetypes=[("3MF project", "*.3mf")],
                                         initialdir=os.path.dirname(cur) or None,
                                         initialfile=os.path.basename(cur) or None)
        if p:
            v["output"].set(os.path.normpath(p))

    def generate(open_after):
        st = store()
        if not st:
            messagebox.showerror("Temperature tower", "QIDI Studio presets are not loaded.")
            return
        try:
            temps = current_temps()
            out = v["output"].get().strip() or default_output(st, v["filament"].get(), temps)
            if not out.lower().endswith(".3mf"):
                out += ".3mf"
            r = tt.write_3mf(out, temps, store=st, machine=v["printer"].get(), process=v["process"].get(),
                             filament=v["filament"].get(), wait=v_wait.get(), embed_settings=v_embed.get())
        except Exception as e:  # noqa: BLE001
            traceback.print_exc()
            messagebox.showerror("Temperature tower", str(e))
            return
        status.set("Saved %s\n%d floors, %g mm tall. Temperature changes (%s) at z = %s." % (
            r["path"], r["floors"], r["height"], r["command"],
            ", ".join("%g→%d°C" % c for c in r["changes"])))
        if open_after:
            try:
                open_in_studio(out)
            except OSError as e:
                messagebox.showerror("Temperature tower", str(e))

    combos["printer"].bind("<<ComboboxSelected>>", lambda e: refresh_lists())
    combos["filament"].bind("<<ComboboxSelected>>", on_filament)
    combos["process"].bind("<<ComboboxSelected>>", lambda e: update_summary())
    load_store()
    root.mainloop()


def _parent_pid(pid):
    """Parent process id on Windows (None if unknown)."""
    import ctypes
    from ctypes import wintypes

    class PROCESSENTRY32W(ctypes.Structure):
        _fields_ = [("dwSize", wintypes.DWORD), ("cntUsage", wintypes.DWORD),
                    ("th32ProcessID", wintypes.DWORD), ("th32DefaultHeapID", ctypes.c_size_t),
                    ("th32ModuleID", wintypes.DWORD), ("cntThreads", wintypes.DWORD),
                    ("th32ParentProcessID", wintypes.DWORD), ("pcPriClassBase", wintypes.LONG),
                    ("dwFlags", wintypes.DWORD), ("szExeFile", wintypes.WCHAR * 260)]

    k32 = ctypes.windll.kernel32
    k32.CreateToolhelp32Snapshot.restype = ctypes.c_void_p
    snap = k32.CreateToolhelp32Snapshot(2, 0)  # TH32CS_SNAPPROCESS
    if not snap or snap == ctypes.c_void_p(-1).value:
        return None
    try:
        entry = PROCESSENTRY32W()
        entry.dwSize = ctypes.sizeof(entry)
        ok = k32.Process32FirstW(ctypes.c_void_p(snap), ctypes.byref(entry))
        while ok:
            if entry.th32ProcessID == pid:
                return entry.th32ParentProcessID
            ok = k32.Process32NextW(ctypes.c_void_p(snap), ctypes.byref(entry))
    finally:
        k32.CloseHandle(ctypes.c_void_p(snap))
    return None


def attach_console():
    """Let the windowed Windows build print when it's run from a terminal.

    The one-file build runs as two processes (a small unpacker, then this
    one), so the terminal is our grandparent rather than our parent.
    """
    if sys.platform != "win32" or not getattr(sys, "frozen", False):
        return
    import ctypes
    k32 = ctypes.windll.kernel32
    k32.GetStdHandle.restype = ctypes.c_void_p
    handle = k32.GetStdHandle(-11)  # STD_OUTPUT_HANDLE
    if handle and handle != ctypes.c_void_p(-1).value and k32.GetFileType(ctypes.c_void_p(handle)) in (1, 3):
        return  # FILE_TYPE_DISK / FILE_TYPE_PIPE: output is redirected, leave it there
    attached = k32.AttachConsole(-1)  # the parent's console
    if not attached:
        grandparent = _parent_pid(os.getppid())
        attached = bool(grandparent) and k32.AttachConsole(grandparent)
    if attached:
        sys.stdout = open("CONOUT$", "w", encoding="utf-8")
        sys.stderr = sys.stdout
        print()  # the shell has already printed its prompt


if __name__ == "__main__":
    if len(sys.argv) > 1:
        attach_console()
        sys.exit(run_cli(sys.argv[1:]))
    run_gui()
