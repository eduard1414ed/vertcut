"""First launch: install everything this computer doesn't have yet.

## What it does, in order

1. checks that there's enough disk space;
2. installs the libraries into a self-contained Python, which has
   already been unpacked by this point (`install.sh` / `install.ps1`
   fetch it);
3. gets ffmpeg — or finds one that's already installed;
4. downloads the speech recognition model;
5. and only then, in one move, puts everything into place.

## The three rules it's built on

**An interrupted install leaves nothing half-built behind.** Everything
is put together in a folder next to the real one, and that folder is
moved into place with a single rename — the very last action. Close
the laptop halfway through, and what's left on disk is an unfinished
temporary folder that the next launch throws away before starting
over. Nothing that LOOKS installed exists, not even for a second.

**The network is mentioned before, not during.** How much will be
downloaded and how long it takes is on the very first screen. The
internet is needed only here: after this Vertcut works offline,
except for the two AI buttons.

**Progress is visible from the first second.** As a page in the
browser, which this file rewrites on disk — it needs no server and no
network. A rule of the project: anything that takes longer than half
a second says what it's doing.

## What it does NOT do

**It installs nothing into the system.** Not into `/usr/local`, not
into the registry, not into the system Python. Everything lives in one
folder, and removing Vertcut means removing that folder.

**It doesn't touch `~/.vertcut`.** That's where your AI key, your
spending log and your own subtitle style live: they survive a
reinstall. That's a separate rule, and there's a test that guards it.
"""

from __future__ import annotations

import argparse
import codecs
import hashlib
import json
import os
import platform
import shutil
import subprocess
import sys
import tarfile
import tempfile
import time
import urllib.error
import urllib.request
import zipfile
from pathlib import Path

# No bytecode cache next to these files. On macOS they live INSIDE the
# signed Vertcut.app, and Python's habit of writing
# `__pycache__/progress.cpython-313.pyc` next to an imported file added a
# file to the app after it was signed: the signature broke, and the copy
# on the Desktop carried the broken signature along (found in the trial
# release, session 27). An app with a broken signature still opens on the
# Mac it was installed on, but sent to another Mac it would be called
# "damaged". This must come before the import below.
sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
import progress  # noqa: E402

HERE = Path(__file__).resolve().parent

# How long to wait for the network to answer. Not "longer, just in
# case": someone whose internet just dropped should find out within half
# a minute, not stare at a page that doesn't move.
NETWORK_TIMEOUT = 30

# Each step says what it actually does: the first one only checks disk
# space (the network gets checked by the first download, and an existing
# ffmpeg by the third step).
STEPS = [
    ("Checking disk space", "takes a second"),
    ("Installing libraries", "speech recognition, drawing subtitles, math"),
    ("Getting ffmpeg", "the tool that cuts and exports video"),
    ("Downloading the speech recognition model",
     "it's what hears the speech; 486 MB, only once"),
    ("Finishing up", "moving everything into place"),
]


# ─── reading the list of sources ─────────────────────────────────────

def sources() -> list[list[str]]:
    """The same list the shell script reads. Two readers, one list."""
    rows = []
    for line in (HERE / "sources.txt").read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            rows.append(line.split())
    return rows


def this_machine() -> tuple[str, str]:
    """What this system and this hardware are called in `sources.txt`.

    **The hardware is asked of the MACHINE, not of this process.**
    `platform.machine()` answers about this process, and under Rosetta
    it honestly says "x86_64" on a machine that is really arm64 (Apple
    Silicon). A program started with a double-click can end up running
    under Rosetta — both Vertcut and its icon have been caught by this.
    Then Intel builds would be downloaded onto an Apple Silicon Mac:
    they'd work, but through translation, and slower.

    What's asked is not a flag but an attempt: `arch -arm64` runs a tiny
    program. If it exits with zero, the machine can run arm64.
    """
    system = "windows" if sys.platform.startswith("win") else (
        "darwin" if sys.platform == "darwin" else "linux")
    hardware = platform.machine().lower()
    if hardware in ("amd64", "x86_64"):
        hardware = "x86_64"
    elif hardware in ("arm64", "aarch64"):
        hardware = "arm64"
    if system == "darwin" and hardware != "arm64" and _can_run_arm64():
        hardware = "arm64"
    return system, hardware


def _can_run_arm64() -> bool:
    """Can THIS MACHINE run arm64. Checked by trying, not by a flag."""
    try:
        result = subprocess.run(["/usr/bin/arch", "-arm64", "/usr/bin/true"],
                                stdout=subprocess.DEVNULL,
                                stderr=subprocess.DEVNULL, timeout=10)
    except (OSError, subprocess.SubprocessError):
        return False
    return result.returncode == 0


def sizes() -> dict[str, int]:
    return {row[1]: int(row[2]) for row in sources() if row[0] == "size"}


# ─── network ──────────────────────────────────────────────────────────

class InstallProblem(Exception):
    """The install stopped: `what` is what happened, `hint` is what to do."""

    def __init__(self, what: str, hint: str = ""):
        super().__init__(what)
        self.what = what
        self.hint = hint


def download(url: str, dest: Path, sha256: str = "",
             on_progress=None) -> Path:
    """Download a file and check its checksum.

    **It's downloaded into a TEMPORARY file and renamed at the end.**
    Otherwise a broken download leaves a stub under the real name, and
    the next launch would take it for the whole file.
    """
    dest.parent.mkdir(parents=True, exist_ok=True)
    partial = dest.with_suffix(dest.suffix + ".partial")
    digest = hashlib.sha256()
    attempts = 3
    for attempt in range(1, attempts + 1):
        try:
            # The name we send with the request is plain Latin on purpose:
            # an HTTP header value must be ASCII, and with any other
            # letters Python doesn't refuse politely — it crashes.
            request = urllib.request.Request(
                url, headers={"User-Agent": "vertcut-installer"})
            with urllib.request.urlopen(request, timeout=NETWORK_TIMEOUT) as response:
                total = int(response.headers.get("Content-Length") or 0)
                digest = hashlib.sha256()
                received = 0
                with partial.open("wb") as file:
                    while True:
                        chunk = response.read(1 << 20)
                        if not chunk:
                            break
                        file.write(chunk)
                        digest.update(chunk)
                        received += len(chunk)
                        if on_progress:
                            on_progress(received, total)
            break
        except (urllib.error.URLError, TimeoutError, OSError) as error:
            partial.unlink(missing_ok=True)
            if attempt == attempts:
                # The server ANSWERED — so the internet works, but there's
                # no file at that address. "Wait for the internet" would
                # be untrue here, and would keep the person waiting
                # forever: an ffmpeg download address has died before.
                if isinstance(error, urllib.error.HTTPError):
                    raise InstallProblem(
                        f"Couldn't download: {url}\n{error}",
                        "The internet works, but the server didn't give us "
                        "the file — it may be down for a while, or the file "
                        "has moved. Nothing is broken: try again later, get "
                        "a newer Vertcut, or install ffmpeg yourself — then "
                        "nothing needs to be downloaded.") from None
                raise InstallProblem(
                    f"Couldn't download: {url}\n{error}",
                    "Looks like the internet connection dropped. Nothing "
                    "is broken — open Vertcut again when you're back "
                    "online.") from None
            time.sleep(2 * attempt)

    if sha256:
        got = digest.hexdigest()
        if got != sha256:
            partial.unlink(missing_ok=True)
            raise InstallProblem(
                f"This download isn't the file we expected.\n\n"
                f"  {url}\n  expected: {sha256}\n  got:      {got}",
                "Maybe whoever builds it released an update, maybe it was "
                "tampered with. There's no way to tell which, so the "
                "installer stopped and installed nothing. Get a newer "
                "Vertcut — or install ffmpeg yourself, and nothing will "
                "need to be downloaded.")
    partial.replace(dest)
    return dest


# ─── steps ────────────────────────────────────────────────────────────

def free_mb(path: Path) -> int:
    """Free megabytes. Asked of the nearest folder that exists."""
    probe = path
    while not probe.exists() and probe != probe.parent:
        probe = probe.parent
    return shutil.disk_usage(probe).free // (1024 * 1024)


def installed_ffmpeg() -> tuple[str, str] | None:
    """An ffmpeg that's already installed, if there is one and it works.

    ffprobe is checked too: they come as a pair, and one is useless
    without the other. It's checked by RUNNING it, not by the file being
    there: PATH sometimes holds a leftover from an old install.
    """
    ff = shutil.which("ffmpeg")
    fp = shutil.which("ffprobe")
    if not (ff and fp):
        return None
    try:
        result = subprocess.run([ff, "-version"], capture_output=True,
                                text=True, timeout=20)
        if result.returncode != 0:
            return None
        version = result.stdout.splitlines()[0].split(" version ")[-1].split()[0]
    except (OSError, subprocess.SubprocessError, IndexError):
        return None
    return ff, version


def install_libraries(python: Path, wheel: Path,
                      shown: progress.Progress) -> None:
    """`pip install` into the self-contained Python.

    pip's output is read as it comes, and the line on the page follows
    it: four silent minutes look like a hang. There's no progress bar —
    pip doesn't know in advance how much it will download, and drawing
    a bar would be a lie.

    **The versions are exact, from `constraints.txt` next to this file.**
    Without it pip takes the newest of everything, and on 29 September
    2026 the newest `av` broke reading sound for every fresh install —
    this installer included — while nothing in Vertcut had changed.
    """
    constraints = HERE / "constraints.txt"
    if not constraints.exists():
        raise InstallProblem(f"Couldn't find {constraints.name} next to "
                             "the installer.",
                             "Something is missing from the download. "
                             "Download Vertcut again.")
    command = [str(python), "-m", "pip", "install", "--no-input",
               "--disable-pip-version-check", "-c", str(constraints),
               str(wheel)]
    process = subprocess.Popen(command, stdout=subprocess.PIPE,
                               stderr=subprocess.STDOUT, text=True,
                               encoding="utf-8", errors="replace")
    last_lines = []
    for line in process.stdout:
        line = line.strip()
        last_lines.append(line)
        del last_lines[:-40]
        if line.startswith(("Collecting ", "Downloading ", "Installing ")):
            shown.update(1, line[:80])
    process.wait()
    if process.returncode != 0:
        raise InstallProblem("The libraries didn't install.\n\n"
                             + "\n".join(last_lines[-15:]),
                             "Most often this means the internet connection "
                             "dropped. Nothing is broken — open Vertcut again.")


def get_ffmpeg(dest: Path, shown: progress.Progress) -> str:
    """A copy of ffmpeg just for Vertcut — or the one already installed.

    **First we look whether the computer already has it.** People with
    Homebrew usually do, and a second copy next to it would mean 45 MB
    for nothing plus the question "which of the two is being used".
    """
    existing = installed_ffmpeg()
    if existing:
        path, version = existing
        shown.done(2, f"already installed: {path} (version {version}) — "
                      "no download needed")
        return "found"

    system, hardware = this_machine()
    rows = [row for row in sources()
            if row[0] == "ffmpeg" and row[1] == system and row[2] == hardware]
    if not rows:
        raise InstallProblem(
            f"There's no ready-made ffmpeg for {system}/{hardware}.",
            "Install ffmpeg yourself — Vertcut will find it and won't "
            "download anything. On macOS that's `brew install ffmpeg`, "
            "on Linux — your system's package.")

    dest.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        for _, _, _, what, url, sha256 in rows:
            # Windows has a single row, an archive with both files inside,
            # and the word "archive" would mean nothing to the person.
            label = "ffmpeg" if what == "archive" else what
            def report(received, total, label=label):
                shown.update(2, f"{label}: {received / 1e6:.0f} of "
                                f"{total / 1e6:.0f} MB",
                             fraction=(received / total if total else None))
            # THE ARCHIVE'S CHECKSUM IS CHECKED HERE. Further down, the
            # UNPACKED files are checked by name — that's right for the
            # Mac builds, whose checksums are taken from the program files
            # themselves. But Windows has a single row called "archive":
            # no file by that name exists after unpacking, so that later
            # check would quietly find nothing to check. This line is
            # what makes "everything downloaded gets checked" true on
            # Windows too.
            archive = download(url, tmp / f"{what}.zip",
                               sha256=(sha256 if what == "archive" else ""),
                               on_progress=report)
            with zipfile.ZipFile(archive) as z:
                for name in z.namelist():
                    bare = name.rsplit("/", 1)[-1]
                    # "LICENSE" with no extension is what the license text
                    # is called in the Windows build; without it nothing
                    # about the GPL would be left next to the program.
                    if bare in ("ffmpeg", "ffprobe", "ffmpeg.exe",
                                "ffprobe.exe", "LICENSE", "LICENSE.txt",
                                "COPYING.GPLv3"):
                        with z.open(name) as src, (dest / bare).open("wb") as out:
                            shutil.copyfileobj(src, out)
        # The Mac builds' checksums are of the program files, not the
        # archive: those are what the builder publishes, and those are
        # what actually runs.
        for _, _, _, what, _, sha256 in rows:
            file = dest / what
            if file.exists() and sha256:
                got = hashlib.sha256(file.read_bytes()).hexdigest()
                if got != sha256:
                    shutil.rmtree(dest, ignore_errors=True)
                    raise InstallProblem(
                        f"The downloaded {what} isn't the file we expected.\n"
                        f"  expected: {sha256}\n  got:      {got}",
                        # Same advice as for the archive: `sources.txt`
                        # promises it, and the Mac builds keep the same file
                        # name across updates — so this is exactly where
                        # the checksum stops matching.
                        "Maybe whoever builds it released an update, maybe "
                        "it was tampered with. There's no way to tell which, "
                        "so the installer stopped and installed nothing. Get "
                        "a newer Vertcut — or install ffmpeg yourself, and "
                        "nothing will need to be downloaded.")
    for file in dest.iterdir():
        if file.suffix.lower() not in (".txt", ".md", ".exe"):
            file.chmod(0o755)

    # Where it came from and under what license — in a file next to it,
    # the same habit as for the fonts and the face detector. The Mac
    # builds come as a bare program file with no license text in the
    # archive, so it's on us to write this down.
    origin = [row for row in sources()
              if row[0] == "ffmpeg" and row[1] == system and row[2] == hardware]
    (dest / "ORIGIN.md").write_text(
        "# ffmpeg\n\n"
        "This computer downloaded it the first time Vertcut was opened —\n"
        "Vertcut does NOT distribute it.\n\n"
        + "".join(f"- `{row[3]}` — {row[4]}\n" for row in origin)
        + "\nThis build is under the GPL: it includes the x264 encoder.\n"
        "The source code and the license text are on the website of\n"
        "whoever built it, at the addresses above.\n\n"
        "You can delete these files at any time: if ffmpeg is installed\n"
        "on the system, Vertcut will use that one.\n",
        encoding="utf-8")
    return "downloaded"


def download_model(python: Path, shown: progress.Progress) -> None:
    """The speech recognition model — fetched the same way analysis
    will load it.

    **There's deliberately no download code of our own here.** The
    speech recognition library downloads the model into its own folder,
    its own way; if we wrote a second way, the project would have two
    truths about where the model lives, and they'd drift apart quietly.

    Interrupted halfway? No harm: the library can resume, and the next
    launch continues where it stopped instead of starting over.
    """
    script = (
        "import faster_whisper, sys\n"
        "faster_whisper.WhisperModel('small', device='cpu', compute_type='int8')\n"
        "print('model is in place')\n"
    )
    # ORT_DISABLE_TELEMETRY: the speech library loads onnxruntime, and
    # onnxruntime on macOS otherwise reports to Microsoft (device model,
    # system version, network type, a device ID) the moment it's
    # imported. Vertcut promises that nothing but the model download and
    # the AI buttons goes over the internet, so it's switched off here,
    # before the import — switching it off afterwards is too late.
    # Vertcut itself does the same in `vertcut/__init__.py`.
    # HF_HUB_DISABLE_TELEMETRY: the same for the library that downloads
    # the model — it otherwise reports to Hugging Face once a day.
    environment = dict(os.environ, ORT_DISABLE_TELEMETRY="1",
                       HF_HUB_DISABLE_TELEMETRY="1")
    process = subprocess.Popen([str(python), "-c", script], env=environment,
                               stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                               text=True, encoding="utf-8", errors="replace")
    last_lines = []
    for line in process.stdout:
        line = line.strip()
        if line:
            last_lines.append(line)
            del last_lines[:-40]
    process.wait()
    if process.returncode != 0:
        raise InstallProblem("The speech recognition model didn't download.\n\n"
                             + "\n".join(last_lines[-10:]),
                             "Most often this means the internet connection "
                             "dropped. Nothing is broken — open Vertcut again, "
                             "and the download will pick up where it stopped.")


# ─── all together ─────────────────────────────────────────────────────

def desktop_folder() -> Path | None:
    """Where this person's Desktop is.

    **Asked of the system, not just assumed to be `~/Desktop`.** On
    Windows the Desktop is often moved into OneDrive, and there may be
    no `Desktop` folder in the home folder at all; on Linux its name
    comes from the user's settings and may be translated.
    """
    home = Path.home()
    if sys.platform == "win32":
        candidates = [home / "OneDrive" / "Desktop", home / "Desktop"]
    elif sys.platform == "darwin":
        # On macOS the folder is ALWAYS called Desktop on disk, however
        # Finder shows it: a translated name is only Finder's display.
        candidates = [home / "Desktop"]
    else:
        candidates = []
        settings = home / ".config" / "user-dirs.dirs"
        try:
            for line in settings.read_text(encoding="utf-8").splitlines():
                if line.startswith("XDG_DESKTOP_DIR"):
                    path = line.split("=", 1)[1].strip().strip('"')
                    candidates.append(
                        Path(path.replace("$HOME", str(home))))
        except OSError:
            pass
        candidates.append(home / "Desktop")
    for place in candidates:
        if place.is_dir():
            return place
    return None


def put_icon_on_desktop(icon: Path | None) -> Path | None:
    """A copy of the icon on the Desktop — so nobody has to look for it.

    **A copy, not a shortcut.** Someone unzips the archive into Downloads,
    installs Vertcut and a week later throws the unzipped folder away —
    a shortcut would then lead nowhere, a copy still works. The icon holds
    only the installer and the Vertcut package, about three megabytes:
    no Python, no ffmpeg, no model — those are already installed.

    **File marks are not copied, and that matters.** macOS marks
    downloaded files with a "quarantine" flag, and a copy carrying that
    flag would ask for permission again — from someone who has just given
    it. The copy is made here and now by the program they've already
    allowed to run.

    **We don't touch what isn't ours.** If something with the same name
    is already on the Desktop, we leave it as it is: silently
    overwriting someone's file is worse than not placing ours.
    """
    if icon is None or not icon.exists():
        return None
    desktop = desktop_folder()
    if desktop is None:
        return None
    # Started right from the Desktop — nowhere to copy and no need to.
    try:
        if icon.resolve().parent == desktop.resolve():
            return icon
    except OSError:
        pass
    target = desktop / icon.name
    if target.exists():
        return target
    try:
        if icon.is_dir():
            shutil.copytree(icon, target, symlinks=True,
                            copy_function=shutil.copy)
        else:
            shutil.copy(icon, target)
    except OSError:
        return None
    return target


def install(stage: Path, target: Path, wheel: Path, page_dir: Path,
            icon: Path | None = None) -> int:
    """Put everything together in `stage`, then move it to `target`.
    Returns the exit code."""
    # Live: Python is already here (the shell script fetched it), so there's
    # something to show progress with, without reloading the window.
    shown = progress.Progress(page_dir, STEPS, live=True)
    shown.render()
    number = 0
    try:
        # ── 1. disk space ───────────────────────────────────────────────
        shown.start(0)
        needed = sizes()["disk"]
        free = free_mb(target.parent)
        if free < needed:
            raise InstallProblem(
                f"Only {free} MB free on the disk, and about {needed} MB "
                "is needed.",
                "Free up some space and open Vertcut again. The biggest "
                "part is the speech recognition model — 486 MB.")
        shown.done(0, f"{free} MB free, about {needed} MB needed")

        # ── 2. libraries ────────────────────────────────────────────────
        number = 1
        python = stage / "python" / ("python.exe" if sys.platform.startswith("win")
                                     else "bin/python3")
        if not python.exists():
            raise InstallProblem(f"Couldn't find Python: {python}",
                                 "Looks like the installer was started the "
                                 "wrong way. Download Vertcut again.")
        shown.start(1, "usually 2–4 minutes")
        install_libraries(python, wheel, shown)
        # Not pip's last line: cut at 80 characters, ending in a comma,
        # it used to hang under the finished step.
        shown.done(1, "installed")

        # ── 3. ffmpeg ───────────────────────────────────────────────────
        number = 2
        shown.start(2, "usually half a minute")
        how = get_ffmpeg(stage / "ffmpeg", shown)
        if how == "downloaded":
            shown.done(2, "downloaded a copy just for Vertcut")

        # ── 4. model ────────────────────────────────────────────────────
        number = 3
        shown.start(3, "486 MB — the longest part")
        download_model(python, shown)
        shown.done(3, "downloaded")

        # ── 5. move into place ──────────────────────────────────────────
        # IN ONE MOVE AND AS THE LAST ACTION. Until this line there's
        # nothing on disk that looks installed.
        number = 4
        shown.start(4)
        # The launcher checks only that this file exists; the contents
        # are for whoever opens it.
        (stage / "version.json").write_text(json.dumps({
            "installed": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "python": ".".join(str(x) for x in sys.version_info[:3]),
            "ffmpeg": how,
            "system": "/".join(this_machine()),
        }, ensure_ascii=False, indent=1), encoding="utf-8")
        previous = target.with_name(target.name + ".previous")
        shutil.rmtree(previous, ignore_errors=True)
        if target.exists():
            target.replace(previous)
        target.parent.mkdir(parents=True, exist_ok=True)
        try:
            stage.replace(target)
        except OSError:
            # A rename doesn't work across disks. The launcher puts the
            # stage folder next to the target, so this shouldn't happen —
            # but if someone moved folders around by hand, moving slowly
            # is better than failing.
            shutil.move(str(stage), str(target))
        shutil.rmtree(previous, ignore_errors=True)
        # The Desktop icon comes last and only after the move: until then
        # nothing is installed, and an icon that leads nowhere mustn't be
        # handed to anyone.
        shown.done(4, "the Vertcut icon is on your Desktop"
                   if put_icon_on_desktop(icon) else "")
        shown.finish()
        shown.wait_for_page()
        return 0

    except InstallProblem as problem:
        shown.fail(number, problem.what, problem.hint)
        shown.wait_for_page()
        print(f"installation stopped: {problem.what}", file=sys.stderr, flush=True)
        return 1
    except KeyboardInterrupt:
        shown.fail(number, "The installation was stopped.",
                   "Nothing was installed and nothing is broken: open "
                   "Vertcut again, and it will start over.")
        shown.wait_for_page()
        return 130
    except Exception:  # noqa: BLE001
        import traceback
        shown.fail(number, traceback.format_exc(),
                   "This is a bug in Vertcut, not something you did. "
                   "Please report it with the lines above.")
        shown.wait_for_page()
        return 1


def utf8_output() -> None:
    """Same as the copy in Vertcut itself (`vertcut/report.py`), and a
    copy on purpose: the installer runs before the package exists, so
    there's nothing to import. When output goes to a log or a pipe
    instead of a console, Python uses the system's encoding — and on
    Windows that encoding often can't write non-English letters (in file
    and folder names, say), so printing would crash. In that case we
    switch the output to UTF-8.
    """
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is None:
            continue
        # Anything but UTF-8 is switched: a code page that knows
        # Cyrillic (cp1251) still can't write "\u00d7" or "\u2192".
        try:
            current = codecs.lookup(stream.encoding or "ascii").name
        except LookupError:
            current = ""
        if current != "utf-8":
            reconfigure(encoding="utf-8", errors="replace")


def main(args=None) -> int:
    utf8_output()
    parser = argparse.ArgumentParser(description="Vertcut's first launch: install")
    parser.add_argument("--stage", dest="stage", required=True, type=Path,
                        help="folder where everything is put together")
    parser.add_argument("--target", dest="target", required=True, type=Path,
                        help="where to move it once it is ready")
    parser.add_argument("--wheel", dest="wheel", required=True, type=Path,
                        help="the Vertcut package (.whl)")
    parser.add_argument("--page-dir", dest="page_dir", required=True, type=Path,
                        help="where to write the progress page")
    parser.add_argument("--icon", dest="icon", type=Path, default=None,
                        help="what to put on the Desktop")
    a = parser.parse_args(args)
    return install(a.stage, a.target, a.wheel, a.page_dir, a.icon)


if __name__ == "__main__":
    sys.exit(main())
