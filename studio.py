"""Find QIDI Studio's installation, to open files in it and to use its command-line slicer."""
import os
import shutil
import subprocess
import sys


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


def cli_command():
    """Command prefix for QIDI Studio's command-line slicer, or None."""
    cmd = studio_command()
    if not cmd:
        return None
    if cmd[0] == "open":  # macOS: run the binary inside the app bundle directly
        macos = os.path.join(cmd[-1], "Contents", "MacOS")
        bins = sorted(b for b in os.listdir(macos) if not b.startswith(".")) if os.path.isdir(macos) else []
        return [os.path.join(macos, bins[0])] if bins else None
    return cmd
