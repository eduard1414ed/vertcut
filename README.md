# Vertcut

Vertcut cuts long videos into vertical clips with subtitles.

Give it a podcast, an interview or a lecture, pick a segment, and get a
finished 1080×1920 clip with subtitles, ready to upload. You don't need
a script: Vertcut listens to the speech, splits it into words and
phrases, finds the cuts and frames each shot around the speaker's face.

It runs on your own computer, in your browser. No account, no
subscription, nothing to pay.

![Picking a segment: the list of phrases with their timings](docs/images/screen-segments.jpg)

![A clip: the vertical frame follows the speaker's face](docs/images/screen-clip.jpg)

![Subtitles: text, font and style, tried on a real frame of the video](docs/images/screen-subtitles.jpg)

<sub>Demo footage: ["Jasmin Moghbeli Interview Resource Reel"](https://images.nasa.gov/details/jsc2023m000156_NASAs_SpaceX_Crew-7_Jasmin_Moghbeli_Interview_Resource_Reel_230824-MP4-4K),
NASA/JSC, public domain. NASA doesn't endorse Vertcut.</sub>

## What it does

1. **Add a video.** Drag it into the browser window, or click
   **Choose file** (macOS).
2. **Let Vertcut analyze it.** This is the long part: about 9 minutes
   for 20 minutes of video on an Apple Silicon Mac. It happens once per
   video. You can close the tab meanwhile.
3. **Pick a segment.** Click the phrase where it starts and the phrase
   where it ends. Or paste a piece of text, and Vertcut finds it in the
   video.
4. **Fix the frame if you like.** Vertcut finds the face and places the
   vertical frame; drag it if you disagree. Each shot gets its own.
5. **Style the subtitles.** Font, size, background, position, on a real
   frame of your video. Save the style as yours, and your next videos
   start from it.
6. **Export.** 10–50 seconds per clip. Each file is named after the
   first words the viewer hears, so twenty clips don't turn into a pile
   of `out.mp4`.

It also works without a script (the text comes from the speech, and you
can correct any phrase), keeps subtitles clear of the buttons that
TikTok, Reels and Shorts draw on top, and can finish a clip with an
end card (your background, an episode cover, a line of text). The end
card is off unless you turn it on. A clip can also be exported without
subtitles: untick **show subtitles in the clip**, or in Settings make new
videos export without them.

What it doesn't do: download videos from links (only files from your
disk), upload clips anywhere, or run on a phone.

## Install

There are three ways. The first is the easiest if you have an AI agent;
the third needs no terminal at all, but your system will warn you about
it.

### 1. Ask your AI agent to install it

If you use Claude Code or another AI agent that can run commands on
your computer, copy this sentence and send it to the agent:

```
Install Vertcut on my computer: clone https://github.com/eduard1414ed/vertcut into ~/vertcut-app and follow INSTALL.md in it. Ask me before installing anything outside that folder.
```

The agent follows [INSTALL.md](INSTALL.md): it checks what you already
have, asks before installing anything system-wide (like Python or
ffmpeg), sets Vertcut up in its own folder, checks that it works and
tells you how to start it. On a Mac it can also put a Vertcut icon on
your Desktop. An icon built on your own Mac opens without the security
warnings that a downloaded app gets.

### 2. Install it yourself in a terminal

These are the same steps the agent follows, with the same commands.

**You need:** git, Python 3.11–3.14, ffmpeg, and about 1 GB of free
space (plus room for your videos); on a Mac, macOS 14 or newer. Check in a terminal:

```
git --version
python3 --version
ffmpeg -version
```

On Windows, use PowerShell, and `py --version` instead of
`python3 --version`.

Something missing? On a Mac with [Homebrew](https://brew.sh):
`brew install python ffmpeg`. On Windows:
`winget install Python.Python.3.13` and `winget install Gyan.FFmpeg`,
then open a new terminal. On Debian or Ubuntu:
`sudo apt install python3 python3-venv ffmpeg git`.

**Install, on macOS or Linux:**

<!-- commands:clone-unix -->
```
git clone https://github.com/eduard1414ed/vertcut.git ~/vertcut-app
```

<!-- commands:install-unix -->
```
cd ~/vertcut-app
python3 -m venv .venv
.venv/bin/python -m pip install . -c constraints.txt
.venv/bin/vertcut check
```

**Install, on Windows (PowerShell):**

<!-- commands:clone-windows -->
```
git clone https://github.com/eduard1414ed/vertcut.git "$HOME\vertcut-app"
```

<!-- commands:install-windows -->
```
cd "$HOME\vertcut-app"
py -m venv .venv
.venv\Scripts\python -m pip install . -c constraints.txt
.venv\Scripts\vertcut check
```

pip may suggest updating itself; you don't need to.
`vertcut check` should end with **"Everything is in place."** If it
says something is missing, the lines above that say what. A line saying
the speech model "DOWNLOADS on the first analysis" is fine: the model
(about 490 MB) arrives with your first video.

**Start it:**

```
~/vertcut-app/.venv/bin/vertcut screen
```

On Windows: `& "$HOME\vertcut-app\.venv\Scripts\vertcut" screen`.
It opens a tab in your browser. Keep the terminal open while you use
Vertcut. To stop it, click **Quit Vertcut** at the bottom of the left
column, or press Ctrl+C in that terminal.

**On a Mac, a Desktop icon** saves you the terminal next time:

```
cd ~/vertcut-app
.venv/bin/python install/build-dev-launcher.py --plain
```

Updating and removing are described [below](#updating).

### 3. Download the installer

Ready-made installers for macOS and Windows are on the
[Releases page](https://github.com/eduard1414ed/vertcut/releases/latest):
`Vertcut-mac.zip` and `Vertcut-windows.zip`. Unzip, double-click
`Vertcut`. The first start downloads what Vertcut needs (Python, ffmpeg
and the speech model, about 800 MB in all) and shows the progress in
your browser. When it's done, a Vertcut icon appears on your Desktop
(on Windows, a Vertcut folder with the app in it).

**Honestly: Vertcut isn't signed, and your system will warn you the
first time.** Signing costs money every year (Apple charges $99 a year;
Windows needs a paid certificate), and Vertcut is free. The warning
says the system couldn't check who made the app. It doesn't mean a
virus was found. You confirm once, and after that it opens like any
other app.

**On macOS:**

1. Double-click `Vertcut`. macOS says **"Vertcut" Not Opened**: Apple
   couldn't check it for malware. Click **Done**.
2. Right away, open **System Settings → Privacy & Security** and scroll
   down. There's a line about Vertcut with an **Open Anyway** button.
   Click it and confirm with your password or Touch ID.
3. The button stays there for about an hour after you tried to open
   Vertcut. If it's gone, double-click `Vertcut` again first. On macOS
   12 and older it's **System Preferences → Security & Privacy →
   General**.
4. Still no button? Download the archive again and unzip it with a
   double-click, not with another app. If that doesn't help either,
   the archive has a backup way: a file called
   `If-Vertcut-does-not-open.sh` that removes the "downloaded from the
   internet" mark from Vertcut and does nothing else. The `README.html`
   next to it says how to run it.

**On Windows:**

1. Right-click the archive → **Extract All**.
2. Open the `Vertcut` folder and double-click `Vertcut` (that's
   `Vertcut.exe`). Keep it in that folder: it needs the `install`
   folder next to it.
3. Windows shows a blue window, **Windows protected your PC**. Click
   **More info**, then **Run anyway**.
4. You can skip that window entirely: before unzipping, right-click the
   archive → **Properties** → tick **Unblock** → **OK**.
5. If `Vertcut` doesn't start at all, or Microsoft Defender removed it,
   there's `Vertcut.cmd` in the `install` folder. It does the same
   thing.

Each archive has a `README.html` with these steps and pictures of what
you'll see.

## What works where

| | 1. Agent | 2. Terminal | 3. Installer |
|---|---|---|---|
| **macOS 14 or newer, Apple Silicon** | tested | tested | tested |
| **macOS, Intel** (Python 3.11–3.13) | not tested | not tested | not tested |
| **Windows 10/11, 64-bit** | not tested | tested on a clean build machine, up to `vertcut check` | tested on a clean build machine |
| **Linux, 64-bit** | not tested | tested on a clean Ubuntu build machine, up to `vertcut check` | no installer |

"Not tested" means nobody has run it there yet. It may well work. If you
try it, please say how it went in
[Issues](https://github.com/eduard1414ed/vertcut/issues).

Real videos have only been analyzed on a Mac. On Windows the build
machine runs everything on short test clips, so a full 20-minute video
there hasn't been tried. Two things are known to be missing on Windows:
there's no **Choose file** button (drag the file into the browser
window instead), and the button that stops an analysis halfway probably
doesn't work.

## AI is optional

Three things in Vertcut can ask an AI model for help: **AI suggestions**
(it reads the transcript and suggests segments), **descriptions**
for your clips, and **Check with AI** in the subtitle editor (it
suggests fixes for misheard words, word endings and names; nothing
changes until you accept a fix). They need your own API key from
Anthropic (Claude) or from a service that speaks the OpenAI API. That's
a separate paid account, not a Claude or ChatGPT subscription. The
money is yours. For suggestions and descriptions Vertcut shows what the
request will cost before you click, whenever it knows the price.
Checking one clip's subtitles costs a few cents, so its price is shown
only when it's above your "ask first" limit.

**Without a key, everything else works.** Those three just stay
off. The Claude path is tested with a real key; the OpenAI-style path
isn't yet.

## What goes over the internet

- **While installing:** Python libraries (from PyPI), and with the
  installer also Python itself and ffmpeg, from the sites that build
  them.
- **On your first video:** the speech recognition model, about 490 MB,
  from Hugging Face. Once: after that, analysis doesn't go online.
- **When you click an AI button:** text goes to the AI provider whose
  key you entered: the transcript of your video (or of the clips you're
  describing or checking), its length, and for descriptions and
  subtitle checks also the video's file name and how the video begins;
  for descriptions also your samples (descriptions you wrote yourself,
  in the settings), if any.
  Never the video or the audio.

That's all. Vertcut doesn't send analytics, has no account and doesn't
check for updates. Two of the libraries it uses would report on their
own: onnxruntime to Microsoft (your computer model, system version and
a device ID) and huggingface_hub to Hugging Face (which AI agent, if
any, started Vertcut). Vertcut switches both off before loading them;
we checked by watching every connection during a full analysis and
export. The video, the audio and everything you make stay on your
computer. Vertcut's server listens only on your own computer
(`127.0.0.1`), not on your network.

## Where things are

| | macOS / Linux | Windows |
|---|---|---|
| Your work: videos and finished clips | `~/vertcut/` | `%USERPROFILE%\vertcut\` |
| Settings, your subtitle style, API key, logs | `~/.vertcut/` | `%USERPROFILE%\.vertcut\` |
| Vertcut itself, ways 1 and 2 | `~/vertcut-app/` | `%USERPROFILE%\vertcut-app\` |
| Vertcut itself, way 3 | `~/Library/Application Support/vertcut/` (macOS) | `%LOCALAPPDATA%\vertcut\` |
| The speech model, ways 1 and 2 | `~/.cache/huggingface/hub/models--Systran--faster-whisper-small` | `%USERPROFILE%\.cache\huggingface\hub\models--Systran--faster-whisper-small` |

Vertcut never deletes your work by itself, and reinstalling doesn't
touch your work or your settings.

## Updating

**Ways 1 and 2:** ask your agent to update Vertcut, or run (the first
line stops Vertcut if it's running):

<!-- commands:update-unix -->
```
cd ~/vertcut-app
.venv/bin/vertcut stop
git pull
.venv/bin/python -m pip install . -c constraints.txt
.venv/bin/vertcut check
```

On Windows (PowerShell):

<!-- commands:update-windows -->
```
cd "$HOME\vertcut-app"
.venv\Scripts\vertcut stop
git pull
.venv\Scripts\python -m pip install . -c constraints.txt
.venv\Scripts\vertcut check
```

**Way 3:** download the new archive and start it the same way. Your
work and settings stay.

## Removing Vertcut

Delete the folder with Vertcut itself (see [Where things
are](#where-things-are)) and the Desktop icon. For ways 1 and 2, also
delete the speech model folder if you want the 490 MB back, and pip's
download cache (about 60 MB: `~/Library/Caches/pip` on a Mac,
`~/.cache/pip` on Linux, `%LOCALAPPDATA%\pip\Cache` on Windows) if
you don't use Python for anything else. Nothing else is installed: no
background services, no login items.

Your work (`~/vertcut`) and settings (`~/.vertcut`) stay until you
delete them yourself.

## Something broken? An idea?

First look at **Not working?** at the bottom of the left column in
Vertcut: it says what to do about common problems and shows what
Vertcut sees on your computer.

Then [open an issue](https://github.com/eduard1414ed/vertcut/issues/new/choose).
For a problem, the form asks for your system, how you installed
Vertcut, the output of `vertcut check` and the last lines of the log.
Issues are public. The log has no API key in it, but it does show your
folder and file names, so look before you paste.

Found a security problem? See [SECURITY.md](SECURITY.md).

## Support Vertcut

Vertcut is free. If it saves you time, you can buy me a coffee on
[Ko-fi](https://ko-fi.com/tsarionov).

## License

Vertcut is under the [MIT license](LICENSE). What it's built from, and
under which licenses, is in [LICENSES.md](LICENSES.md). ffmpeg is GPL
and isn't part of Vertcut: you install it yourself, or the installer
downloads it from the people who build it.
