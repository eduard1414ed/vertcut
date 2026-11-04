# Vertcut @VERSION@

Vertcut cuts long videos into vertical clips with subtitles, on your
own computer, in your browser.

## What's new in @VERSION@

- **Check with AI** on the Subtitles screen. Speech recognition gets
  names, titles and word endings wrong; the AI reads the subtitles of
  one clip and suggests fixes as a list. You accept, edit or dismiss
  each one yourself — nothing changes until you do. Needs an API key;
  the price is shown only when a check would cost more than your limit.
- **Clips without subtitles.** Each clip has a "show subtitles in the
  clip" switch on its Subtitles screen. In Settings you can make new
  videos export without subtitles by default; videos you have already
  analyzed don't change.

## How to install

There are three ways, described in the
[README](https://github.com/eduard1414ed/vertcut#install):

1. Ask your AI agent to install it (easiest if you have one).
2. Install it yourself in a terminal.
3. Download an installer below — no terminal needed.

| File | For |
|---|---|
| `Vertcut-mac.zip` | macOS 14 or later |
| `Vertcut-windows.zip` | Windows 10 or 11, 64-bit |
| `SHA256SUMS.txt` | checksums of both archives |

The first start downloads what Vertcut needs (Python, ffmpeg and the
speech model, about 800 MB) and shows the progress in your browser.

## Signed on macOS, not on Windows

**macOS:** Vertcut is signed with its author's Apple Developer ID and
notarized by Apple. The first time, macOS only asks whether to open an
app downloaded from the internet — click **Open**.

**Windows:** Vertcut isn't signed — a Windows certificate costs money
every year, and Vertcut is free. So the first time, Windows says it
protected your PC. That doesn't mean a virus was found — it means
Windows can't confirm who made the app.
[What to click](https://github.com/eduard1414ed/vertcut#3-download-the-installer).

The Windows archive was built by GitHub's build machines from the
source code at this release's tag, and the build logs are public. The
macOS archive was built from the same tag on the author's Mac, because
that's where the signing certificate lives, and then checked by Apple.
To check that your download is exactly what was uploaded:

    macOS:    shasum -a 256 -c SHA256SUMS.txt --ignore-missing
    Windows:  Get-FileHash Vertcut-windows.zip   (compare with SHA256SUMS.txt)

## What's tested

| | Agent | Terminal | Installer |
|---|---|---|---|
| macOS 14 or newer, Apple Silicon | tested | tested | tested |
| macOS, Intel (Python 3.11–3.13) | not tested | not tested | not tested |
| Windows 10/11, 64-bit | not tested | tested on a clean build machine | tested on a clean build machine |
| Linux, 64-bit | not tested | tested on a clean build machine | no installer |

Real videos have only been analyzed on a Mac. Nobody has run Vertcut
on a home Windows PC yet. Known gaps on Windows: no "Choose file"
button (drag the file in), and stopping an analysis halfway probably
doesn't work.

"Not tested" means nobody has tried it yet — it may work fine. If you
try it, please tell us how it went in
[Issues](https://github.com/eduard1414ed/vertcut/issues).
