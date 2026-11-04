# Installing Vertcut — instructions for an AI agent

You're an AI agent (Claude Code or similar), and a person asked you to
install Vertcut on their computer. Follow these steps in order. Each
step has the commands to run and a check that tells you it worked.
Don't skip a check. Stop when you reach "Tell the person" at the end.

Vertcut cuts long videos into vertical clips with subtitles. It runs
locally: a small web server on `127.0.0.1` that the person opens in
their browser.

If you're a person reading this yourself: the same steps, with the same
commands, are in the [README](README.md#2-install-it-yourself-in-a-terminal).

## Rules

1. **Talk to the person in their language, in plain words.** They may
   not be a programmer. Say what you're about to do and why before
   anything that takes long or downloads a lot.
2. **Ask before installing anything outside the Vertcut folder** —
   Homebrew, winget, apt, a Python installer, Xcode Command Line
   Tools, anything system-wide. Show the exact command and wait for a
   yes. If they say no, explain what won't work and stop.
3. **Never use `sudo`.** If something needs it, give the person the
   command to run themselves.
4. **Don't touch the system Python** — no `pip install` outside the
   virtual environment, no `--user`, no `--break-system-packages`.
   Everything Python goes into `.venv` inside the Vertcut folder.
5. **Install into `~/vertcut-app`** (Windows: `%USERPROFILE%\vertcut-app`),
   unless the person asked for another place. **Never into `~/vertcut`:**
   that's where Vertcut keeps the person's videos and clips.
6. **Don't open the person's browser or any app without asking.**
7. **Don't promise what you didn't check.** If a step fails and the
   fix isn't in this file, tell the person what failed, show the error,
   and point them to
   [Issues](https://github.com/eduard1414ed/vertcut/issues).

## What works where

| System | Status |
|---|---|
| macOS 14 or newer on Apple Silicon (M1 and later) | tested; older macOS has no builds of the speech and face libraries Vertcut uses |
| Windows 10/11, 64-bit Intel/AMD | tested up to `vertcut check` on a clean Windows build machine; not tested on a real person's PC |
| Linux, 64-bit Intel/AMD | tested up to `vertcut check` on a clean Ubuntu build machine; not used for real work yet |
| macOS on Intel | not tested — should work with Python 3.11–3.13 (3.14 has no face-detector build for Intel Macs), tell the person |
| Windows on ARM, Linux on ARM | not tested — tell the person before you start |

## Step 1. Look at what's already there

Find out the system and check each requirement. Use the commands for
the person's system.

**macOS / Linux:**

```
uname -sm
sw_vers -productVersion
git --version
python3 --version
ffmpeg -version
ffprobe -version
df -h ~
brew --version
```

`sw_vers` and `brew --version` matter only on macOS. `sw_vers` gives
the macOS version: an Apple Silicon Mac needs 14 or newer — below that,
stop and tell the person. `brew --version` tells you which way to offer
in Step 2 if something is missing.

On macOS, check `xcode-select -p` **before** `git --version`: if it
fails, Command Line Tools aren't installed, and `git --version` would
pop up an install window on the person's screen. Treat that as
"git is missing" (Step 2).

**Windows (PowerShell):**

```
git --version
py --version
python --version
ffmpeg -version
ffprobe -version
Get-PSDrive -Name ($HOME.Substring(0,1))
```

On Windows, `python` may be a Microsoft Store shortcut that prints
nothing or opens the Store — that doesn't count as Python. `py` is the
Python launcher; prefer it.

**What's needed:**

| | Needed | Check passes when |
|---|---|---|
| git | any version | `git --version` prints a version |
| Python | **3.11, 3.12, 3.13 or 3.14** | the version printed is in that range |
| ffmpeg and ffprobe | any recent version, on PATH | both print a version |
| Disk space | about **1 GB** for Vertcut, plus room for videos (20 minutes of video ≈ 400 MB of work files) | at least 2 GB free in the home folder |
| Internet | for installing (~250 MB of Python libraries) and for the speech model (~490 MB, downloaded on the first video) | — |

If `python3` (or `py`) is outside 3.11–3.14, look for another Python
already installed: `python3.14`, `python3.13`, `python3.12`,
`python3.11` (Windows: `py -0` lists them). If one fits, use it in
place of `python3` (Windows: `py -3.13` etc. in place of `py`) in
Step 4.

Everything there → go to Step 3.

## Step 2. If something is missing — ask, then install

Tell the person what's missing, show the command, and ask. Run it only
after a yes.

| Missing | macOS (with Homebrew) | Windows | Linux (Debian/Ubuntu) |
|---|---|---|---|
| Python | `brew install python` | `winget install Python.Python.3.13` | `sudo apt install python3 python3-venv` — the person runs it |
| ffmpeg | `brew install ffmpeg` | `winget install Gyan.FFmpeg` | `sudo apt install ffmpeg` — the person runs it |
| git | `xcode-select --install` (opens a system window) | `winget install Git.Git` | `sudo apt install git` — the person runs it |

- **macOS without Homebrew** (`brew --version` fails): don't install
  Homebrew yourself — it asks for the person's password. Offer two
  ways and let them choose: they install Homebrew from
  [brew.sh](https://brew.sh) themselves, or they use the ready-made
  installer instead (README, way 3, "Download the installer"), which
  brings its own Python and ffmpeg — into its own program folder,
  outside `~/vertcut-app`.
- **Windows:** after `winget install`, PATH changes only in **new**
  terminals. Open a new one (or ask the person to) before checking
  again.
- **Linux, other distributions:** find the package names for that
  distribution and ask the same way.

Check: run the Step 1 commands again. Everything must pass now.

**If the person says no:** Vertcut can't work without Python 3.11–3.14
and ffmpeg, and there's no way to get them that stays inside the
Vertcut folder. Don't go on with Step 4. Tell them what's missing, that
nothing else was changed, and how to continue later (ask you again
after installing it themselves, or use the installer); leave the clone
in place unless they ask you to delete it. Stop there.

## Step 3. Get the code

**macOS / Linux:**

<!-- commands:clone-unix -->
```
git clone https://github.com/eduard1414ed/vertcut.git ~/vertcut-app
```

**Windows (PowerShell):**

<!-- commands:clone-windows -->
```
git clone https://github.com/eduard1414ed/vertcut.git "$HOME\vertcut-app"
```

If you already cloned it to read this file, skip the clone — just
make sure it's in `~/vertcut-app`. If the folder existed before you
started and is a Vertcut clone, this is an update — go to "Updating"
below instead.

Check: the folder `vertcut-app` exists and has `INSTALL.md` and
`pyproject.toml` in it.

## Step 4. Install Vertcut into its own environment

Run these exactly. If Step 1 found a different Python (`python3.13`,
`py -3.13`…), use it in the `venv` line — only there.

**macOS / Linux:**

<!-- commands:install-unix -->
```
cd ~/vertcut-app
python3 -m venv .venv
.venv/bin/python -m pip install . -c constraints.txt
.venv/bin/vertcut check
```

**Windows (PowerShell):**

<!-- commands:install-windows -->
```
cd "$HOME\vertcut-app"
py -m venv .venv
.venv\Scripts\python -m pip install . -c constraints.txt
.venv\Scripts\vertcut check
```

The `pip install` line downloads about 250 MB and takes a minute or
two. You don't need to upgrade pip or setuptools first; if pip prints
a notice that a new release of pip is available, ignore it.

Check: the last line of `vertcut check` is **"Everything is in place."**
and the command exits with code 0. If it says "Something is missing",
the lines above it say what. Fix that (Step 2) and run `vertcut check`
again.

A line saying the speech model **"DOWNLOADS on the first analysis"**
is normal: the ~490 MB model arrives when the person analyzes their
first video. That isn't something missing.

Common failures:

- `python3 -m venv` says `ensurepip is not available` (Debian/Ubuntu):
  `python3-venv` is missing — Step 2.
- `pip` says `requires a different Python`: the Python is outside
  3.11–3.14. Delete `.venv` and redo Step 4 with a fitting Python.
- `ffmpeg … NOT FOUND` in `vertcut check`: ffmpeg isn't on PATH in this
  terminal. On Windows, open a new terminal after installing it.

## Step 5. Check that it starts

Start it without opening a browser, check that it answers, stop it.

**macOS / Linux:**

```
~/vertcut-app/.venv/bin/vertcut screen --no-browser
```

**Windows (PowerShell):**

```
& "$HOME\vertcut-app\.venv\Scripts\vertcut" screen --no-browser
```

It keeps running until stopped, so run it in the background (or in a
second terminal).

Check: within a few seconds it prints
`Vertcut is running. Open it in the browser:` and an address like
`http://127.0.0.1:PORT/?pass=…`. Then stop it:

macOS / Linux: `~/vertcut-app/.venv/bin/vertcut stop`

Windows (PowerShell): `& "$HOME\vertcut-app\.venv\Scripts\vertcut" stop`

Check: it prints `Vertcut has stopped.`, and the process you started
has ended. (Ctrl+C works only in a terminal where Vertcut runs in the
foreground — a process started in the background ignores it.) The
address is new on every start, so there's no point in saving it.

## Step 6. macOS only: an icon on the Desktop (ask first)

Ask the person if they want a Vertcut icon on their Desktop, so they
can start it with a double-click instead of a terminal. If yes:

```
cd ~/vertcut-app
.venv/bin/python install/build-dev-launcher.py --plain
```

Check: it prints `built: …/Desktop/Vertcut.app`. If it says the icon
already exists and "isn't an icon built here", the person has Vertcut
from the ready-made installer too — ask whether to move that one to
the Trash or to build this one elsewhere with `--out <folder>`.

The icon is made on this Mac, not downloaded, so macOS doesn't ask
anything about it. It starts Vertcut
from `~/vertcut-app` and never installs anything. A double-click opens
a tab in the browser; if Vertcut is already running, it opens the same
tab.

There's no icon for Windows or Linux: there, Vertcut starts from a
terminal.

## Step 7. Open it for the person (ask first)

Ask: "Vertcut is installed. Shall I open it in your browser now?"
Only on a yes:

- **macOS with the icon:** `open ~/Desktop/Vertcut.app`
- **Otherwise:** don't start it from your own session — it would stop
  when you finish. Give the person the command to paste into their own
  terminal, and tell them to keep that window open while they use
  Vertcut:

  macOS / Linux: `~/vertcut-app/.venv/bin/vertcut screen`

  Windows (PowerShell): `& "$HOME\vertcut-app\.venv\Scripts\vertcut" screen`

  It opens a tab in their default browser.

## Tell the person

Say this in your own words, in their language:

- Vertcut is installed in `~/vertcut-app` (Windows:
  `%USERPROFILE%\vertcut-app`).
- **How to start it:** the Desktop icon (macOS, if built), or the
  command from Step 7 in a terminal. It opens in the browser; clicking
  the icon again while it runs just opens the same tab.
- **How to stop it:** **Quit Vertcut**, the last line of the left
  column. Or `vertcut stop` in a terminal, or Ctrl+C in the terminal
  it was started from. An analysis or export that's running keeps going
  on its own; Vertcut says so before quitting, and opening it again
  shows how it's doing.
- **If they move the `vertcut-app` folder**, the Desktop icon stops
  working; build it again (Step 6) from the new place.
- **Their work** — videos and finished clips — goes to `~/vertcut`
  (Windows: `%USERPROFILE%\vertcut`). Settings, their subtitle style
  and logs go to `~/.vertcut`.
- **The first video takes longer:** Vertcut downloads its speech model
  (~490 MB) once. Analysis takes about 9 minutes per 20 minutes of
  video on an Apple Silicon Mac (other computers: not measured);
  cutting clips after that takes seconds each.
- **AI is optional.** Two buttons can ask an AI model to suggest clips
  and write descriptions. They need the person's own API key — from
  Anthropic (Claude), or from a service that speaks the OpenAI API —
  paid separately, not a chat subscription. They send the transcript
  text to that provider. Everything else works without a key and without the
  internet.
- **If something breaks:** in Vertcut, **Not working?** at the bottom
  of the left column; or
  [Issues](https://github.com/eduard1414ed/vertcut/issues).

## Updating

When the person asks to update Vertcut:

**macOS / Linux:**

<!-- commands:update-unix -->
```
cd ~/vertcut-app
.venv/bin/vertcut stop
git pull
.venv/bin/python -m pip install . -c constraints.txt
.venv/bin/vertcut check
```

**Windows (PowerShell):**

<!-- commands:update-windows -->
```
cd "$HOME\vertcut-app"
.venv\Scripts\vertcut stop
git pull
.venv\Scripts\python -m pip install . -c constraints.txt
.venv\Scripts\vertcut check
```

The first line stops Vertcut if it's running (if it isn't, it just
says so). The icon doesn't need rebuilding. The person's videos, clips and settings aren't touched.

Check: `git pull` succeeded and `vertcut check` ends with
"Everything is in place."

If `git pull` complains about local changes, don't discard them —
show the person and ask.

## Removing Vertcut

Ask the person which of these to remove, then remove only that:

| What | macOS / Linux | Windows |
|---|---|---|
| The program | `~/vertcut-app` | `%USERPROFILE%\vertcut-app` |
| The Desktop icon (macOS) | `~/Desktop/Vertcut.app` | — |
| The speech model (~490 MB) | `~/.cache/huggingface/hub/models--Systran--faster-whisper-small` | `%USERPROFILE%\.cache\huggingface\hub\models--Systran--faster-whisper-small` |
| Settings, subtitle style, API key, logs | `~/.vertcut` | `%USERPROFILE%\.vertcut` |
| pip's download cache (~60 MB, shared with other Python projects) | macOS: `~/Library/Caches/pip`, Linux: `~/.cache/pip` | `%LOCALAPPDATA%\pip\Cache` |
| **Their work: videos and clips** | `~/vertcut` | `%USERPROFILE%\vertcut` |

Stop Vertcut first (`vertcut stop`). **Never remove `~/vertcut` unless
the person explicitly says so** — it's their work, and nothing else has a copy.
The model folder and pip's cache are shared with other Python
projects: remove only what's listed, and the pip cache only if the
person agrees.

Nothing else is installed: no services, no login items, no changes to
the system Python.
