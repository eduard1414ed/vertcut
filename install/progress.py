"""How the installer shows its progress before Vertcut itself exists.

## Why it's a browser page and not a window

Vertcut has no windows at all, on purpose: a window library would be
one more dependency to ship. The person has no terminal open either —
the whole point of the installer is that they never need one. But it
can't stay silent: installing takes minutes, and a program that says
nothing for that long looks frozen.

That leaves the browser. But there's nothing to run a web server with
yet: the machine may have no Python at all.

**So the first page is a plain file on disk** that the browser reloads
by itself. No server, no Python, no dependencies: it works even when
the machine has nothing installed yet.

**It only lives like that until Python shows up, and that was learned
the hard way.** Reloading the page reloads the WHOLE window: a white
flash, a jumpy address bar, a jump back to the top. Once a second, for
the several minutes the install takes. The very first look at it made
it obvious that this reads as broken — a page that keeps twitching
looks broken, whatever it says.

As soon as Python is in place (the first thing the installer does),
a tiny local server starts, and from then on **only the contents of
the card change, not the window**. No flash, no jump, no jumpy address.

**The markup is still drawn by Python, not by the browser.** The page
asks for `/state` and swaps in the ready-made piece of markup it gets
back. If the browser built the markup itself, there would be two
versions of the truth about what the progress looks like — the same
reason the browser never draws subtitles in Vertcut.

## Why it looks like Vertcut

It uses the same colors and spacing as Vertcut's design files — but
NOT the files themselves: `tokens.css` ships inside the Vertcut
package, and the package isn't installed yet at this point. This is
the only place in the project where colors are written out as numbers,
and this is why.

## What it shows

The steps as a list, and for the current one what exactly is
happening. **A progress bar is drawn only where the fraction is
really known** — a design rule, and plain honesty. There's exactly
one such step here: downloads, where we know how many bytes out of
how many. The other steps say "usually takes this long" instead.
"""

from __future__ import annotations

import codecs
import html
import json
import os
import sys
import tempfile
import threading
import time
from datetime import datetime
from pathlib import Path

# Colors and spacing — from Vertcut's design, but as plain numbers.
#
# This is NOT carelessness: `tokens.css` lives inside the Vertcut
# package, and this page is shown BEFORE the package exists. The numbers
# were checked against `tokens.css` by eye; if they ever drift apart,
# anyone who opens the installer and Vertcut side by side will see it.
_STYLE = """
:root{--bg:#FBFBFA;--fg:#191919;--muted:#6B6B6B;--line:#E3E2DF;
--accent:#C96442;--good:#2E7D5B;--bad:#B3261E;--card:#FFFFFF}
@media (prefers-color-scheme:dark){:root{--bg:#1A1A18;--fg:#F0EFEC;
--muted:#9B9A96;--line:#2E2E2B;--card:#232320}}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--fg);
font:15px/1.5 -apple-system,BlinkMacSystemFont,"Segoe UI",system-ui,sans-serif;
padding:40px 24px}
.sheet{max-width:560px;margin:0 auto}
h1{font-size:24px;line-height:1.25;margin:0 0 8px;letter-spacing:-.01em}
.sub{color:var(--muted);margin:0 0 24px}
.card{background:var(--card);border:1px solid var(--line);
border-radius:12px;padding:20px 24px}
.step{display:flex;gap:12px;align-items:flex-start;padding:10px 0;
border-top:1px solid var(--line)}
.step:first-child{border-top:0}
.mark{width:18px;flex:0 0 18px;text-align:center;color:var(--muted)}
.running .mark{color:var(--accent)}
.done .mark{color:var(--good)}
.name{font-weight:500}
.running .name{color:var(--accent)}
.waiting{color:var(--muted)}
.small{color:var(--muted);font-size:13px;margin-top:2px}
.bar{height:6px;border-radius:3px;background:var(--line);
margin-top:8px;overflow:hidden}
.bar i{display:block;height:100%;background:var(--accent)}
.problem{border-color:var(--bad)}
.problem h1{color:var(--bad)}
.code{font:12px/1.5 ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;
white-space:pre-wrap;color:var(--muted);margin-top:12px}
"""

WAITING, RUNNING, DONE, FAILED = "waiting", "running", "done", "failed"


def _mark(state: str) -> str:
    """No system font is guaranteed to have a check mark, so it's drawn
    with lines. Same problem and same fix as in Vertcut itself."""
    if state == DONE:
        return ('<svg class="mark" width="14" height="14" viewBox="0 0 14 14" '
                'fill="none" stroke="currentColor" stroke-width="2">'
                '<path d="M2 7.5 L5.5 11 L12 3.5"/></svg>')
    if state == RUNNING:
        return '<span class="mark">→</span>'
    if state == FAILED:
        return '<span class="mark">✕</span>'
    return '<span class="mark">·</span>'


def card(steps: list[dict], problem: str = "", log_tail: str = "") -> str:
    """The markup of the ONE card — the part that changes as things go.

    It's separate from the page so the live update replaces exactly
    this and not a line more. It's drawn here, in Python: if the browser
    built it, there'd be two versions of the truth about the progress.
    """
    rows = _steps(steps)
    problem_html = f'<div class="code">{html.escape(problem)}</div>' if problem else ""
    tail_html = f'<div class="code">{html.escape(log_tail)}</div>' if log_tail else ""
    return "".join(rows) + problem_html + tail_html


def _steps(steps: list[dict]) -> list[str]:
    rows = []
    for step in steps:
        state = step.get("state", WAITING)
        classes = {WAITING: "waiting", RUNNING: "running", DONE: "done",
                   FAILED: "problem"}[state]
        parts = [f'<div class="step {classes}">', _mark(state),
                 '<div style="flex:1">',
                 f'<div class="name">{html.escape(step["name"])}</div>']
        detail = step.get("detail", "")
        if detail:
            parts.append(f'<div class="small">{html.escape(detail)}</div>')
        fraction = step.get("fraction")
        # The bar is drawn ONLY where the fraction is really known. A design
        # rule, and also honesty: a bar crawling along a made-up number
        # lies exactly when someone is looking at it.
        if state == RUNNING and fraction is not None:
            parts.append(f'<div class="bar"><i style="width:'
                         f'{max(0, min(100, round(fraction * 100)))}%"></i></div>')
        parts.append("</div></div>")
        rows.append("".join(parts))
    return rows


def page(steps: list[dict], title: str, subtitle: str,
         problem: str = "", go_to: str = "", log_tail: str = "",
         reload_every: int = 1, live: str = "") -> str:
    """The whole page. The data comes in ready; nothing to compute here."""

    # The page reloads itself ONLY while there's no other way. That reloads
    # the whole window, with a flash and a jump; where there is a server,
    # only the contents of the card change instead.
    refresh = ""
    if go_to:
        refresh = f'<meta http-equiv="refresh" content="0; url={go_to}">'
    elif not problem and reload_every:
        refresh = f'<meta http-equiv="refresh" content="{reload_every}">'

    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
{refresh}<title>{html.escape(title)}</title>
<style>{_STYLE}</style></head>
<body><div class="sheet">
<h1 id="title">{html.escape(title)}</h1>
<p class="sub" id="sub">{html.escape(subtitle)}</p>
<div class="card{' problem' if problem else ''}" id="card">
{card(steps, problem=problem, log_tail=log_tail)}
</div></div>{live}</body></html>
"""


# Live update: the CONTENTS of the card change, not the window.
#
# A few lines of logic and not a single line of markup: Python draws
# the markup and sends it ready-made. If the browser built it, there'd
# be two versions of the truth about what the progress looks like.
#
# **When the server goes quiet, the page does NOT switch to the file —
# it waits.** It used to switch: `location.replace('file://…')`. Browsers
# silently forbid going from an `http://` page to a `file://` one — no
# error, no window, just nothing. The page froze on the last step it had
# seen, and on someone else's Mac it kept saying "Downloading the model"
# long after the install had finished. Now it keeps asking the same
# address, and the launcher, once Vertcut is up, takes over that port
# for a few minutes and answers "go there" (`_tell_live_page`). Going
# from `http://` to `http://` is allowed.
#
# If it's quiet for too long, it says what to do — in words Python sent
# in advance: the browser has no words of its own here.
_LIVE = """<script>
(function () {
  var misses = 0, silentHint = '';
  function tick() {
    fetch('state', { cache: 'no-store' })
      .then(function (r) { return r.json(); })
      .then(function (s) {
        misses = 0;
        silentHint = s.silent_hint || silentHint;
        if (s.go_to) { location.replace(s.go_to); return; }
        document.getElementById('title').textContent = s.title;
        document.getElementById('sub').textContent = s.sub;
        var box = document.getElementById('card');
        box.innerHTML = s.card;
        box.className = 'card' + (s.problem ? ' problem' : '');
        document.title = s.title;
        setTimeout(tick, 900);
      })
      .catch(function () {
        if (++misses === 40 && silentHint) {
          document.getElementById('sub').textContent = silentHint;
        }
        setTimeout(tick, 900);
      });
  }
  tick();
})();
</script>"""

# What to say if the page has had no answers for a long time. The usual
# gap between the end of the install and Vertcut starting is about five
# seconds; forty misses is half a minute, and Vertcut would surely be up
# by then.
#
# **The Desktop icon may not exist yet.** The last install step puts it
# there, and the installer also goes quiet when it was interrupted
# halfway (the Mac was shut down). So the text doesn't only point at
# the icon — there may be no icon to point at.
_SILENT_HINT = ("The installer stopped responding. If nothing changes, open "
                "Vertcut again — from the icon on your Desktop, or from the "
                "unzipped folder if the icon isn't there yet.")

# Where the live page's port number is kept: after the install the
# launcher takes over that port to send the page on to Vertcut.
PORT_FILE = "port.txt"


def write_file(path: Path, text: str) -> None:
    """Writes through a temporary file and a rename.

    Not just tidiness: the browser reloads the file once a second and
    will sooner or later hit the exact moment of writing. A half-written
    page is a blank screen for someone who is waiting and doesn't know
    what's going on.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    f = tempfile.NamedTemporaryFile("w", encoding="utf-8", delete=False,
                                    dir=path.parent, suffix=".tmp")
    try:
        f.write(text)
        f.flush()
        os.fsync(f.fileno())
        f.close()
        os.replace(f.name, path)
    except BaseException:
        Path(f.name).unlink(missing_ok=True)
        raise


def _start_server(progress, port: int = 0):
    """A tiny server that exists only while the install runs.

    **It appears exactly when Python appears** — that is, at the very
    first install step — and dies with the installer. It does nothing
    else: one page and one state.

    It listens on `127.0.0.1` only (nothing outside this computer can
    reach it) and takes any free port. A fixed port isn't needed: the
    address lives for two minutes, nobody bookmarks it, and a taken
    port would be a failure for no reason.

    **The only address inside is plain Latin (`/state`), on purpose.**
    Non-Latin letters in a request path arrive percent-encoded, and the
    main Vertcut server has extra code to put the bytes back together.
    Doing that a second time here, for an address no person ever sees,
    costs more than simply not having the problem.
    """
    import http.server
    import threading

    class Handler(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            path = self.path.split("?")[0]
            if path in ("/", "/index.html"):
                body = page(progress.steps, progress.title, progress.subtitle,
                            problem=progress.problem, log_tail=progress.log_tail,
                            go_to=progress.go_to, reload_every=0,
                            live="" if progress.go_to else _LIVE
                            ).encode("utf-8")
                kind = "text/html; charset=utf-8"
            elif path == "/state":
                body = json.dumps({
                    "title": progress.title,
                    "sub": progress.subtitle,
                    "card": card(progress.steps, problem=progress.problem,
                                 log_tail=progress.log_tail),
                    "problem": bool(progress.problem),
                    "go_to": progress.go_to,
                    "silent_hint": _SILENT_HINT,
                }, ensure_ascii=False).encode("utf-8")
                # The last word has reached the page — whoever is waiting
                # for that can go now.
                if progress.finished:
                    progress.delivered.set()
                kind = "application/json; charset=utf-8"
            else:
                self.send_response(404)
                self.end_headers()
                return
            self.send_response(200)
            self.send_header("Content-Type", kind)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *_):
            """Quiet. The installer talks to the person through the page,
            and the log gets what happened; a line per request would
            drown both."""

    server = http.server.ThreadingHTTPServer(("127.0.0.1", port), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server


class Progress:
    """The install's state: kept on disk, not only in memory.

    On disk for the same reason Vertcut keeps the progress of its long
    jobs there: tabs get closed, pages get reloaded, but the work goes on
    in its own process and must be able to tell whoever comes later how
    it's doing.
    """

    def __init__(self, folder: Path, steps: list[tuple[str, str]],
                 title: str = "Installing Vertcut", live: bool = False):
        self.page_file = folder / "progress.html"
        self.state_file = folder / "state.json"
        self.title = title
        self.steps = [{"name": name, "detail": detail, "state": WAITING}
                      for name, detail in steps]
        self.subtitle = "This happens only once."
        self.started = datetime.now()
        self.problem = ""
        self.log_tail = ""
        self.go_to = ""
        self.finished = False
        self.delivered = threading.Event()
        self.server = _start_server(self) if live else None
        port_file = folder / PORT_FILE
        port_file.unlink(missing_ok=True)
        if self.server:
            write_file(port_file, str(self.server.server_address[1]))
            # The file on disk turns into a single redirect: a browser
            # looking at it moves to the live page and never reloads again.
            write_file(self.page_file,
                       page([], "Installing Vertcut", "This happens only once.",
                            go_to=self.address()))

    def address(self) -> str:
        port = self.server.server_address[1]
        return f"http://127.0.0.1:{port}/"

    # ── what's happening ────────────────────────────────────────────────

    def start(self, number: int, detail: str = "") -> None:
        for i, step in enumerate(self.steps):
            if i < number:
                step["state"] = DONE
        self.steps[number]["state"] = RUNNING
        if detail:
            self.steps[number]["detail"] = detail
        self.steps[number].pop("fraction", None)
        self.render()

    def update(self, number: int, detail: str = "",
               fraction: float | None = None) -> None:
        if detail:
            self.steps[number]["detail"] = detail
        if fraction is None:
            self.steps[number].pop("fraction", None)
        else:
            self.steps[number]["fraction"] = fraction
        self.render()

    def done(self, number: int, detail: str = "") -> None:
        self.steps[number]["state"] = DONE
        if detail:
            self.steps[number]["detail"] = detail
        self.steps[number].pop("fraction", None)
        self.render()

    def fail(self, number: int, problem: str, hint: str = "") -> None:
        self.steps[number]["state"] = FAILED
        self.title = "Installation didn't finish"
        self.subtitle = hint or "Here's what went wrong."
        self.render(problem=problem)

    def finish(self, go_to: str = "") -> None:
        for step in self.steps:
            step["state"] = DONE
        seconds = (datetime.now() - self.started).total_seconds()
        # "Took 0 min" is untrue about work that took half a minute.
        # Seconds are said as seconds.
        took = (f"{seconds:.0f} s" if seconds < 90
                else f"{seconds / 60:.0f} min")
        self.title = "Done"
        # Not "works offline" across the board: the two AI buttons do go
        # online, and promising otherwise would be untrue.
        self.subtitle = (f"Took {took}. From now on Vertcut works "
                         "offline — only the AI buttons need the internet.")
        self.render(go_to=go_to)

    # ── to disk ─────────────────────────────────────────────────────────

    def render(self, problem: str = "", go_to: str = "") -> None:
        self.problem = problem
        self.go_to = go_to
        # The state always goes to disk: both the person and whoever comes
        # to investigate later look at it. The page file is rewritten only
        # when there's no live server: the server shows the same thing,
        # without reloading the window.
        write_file(self.state_file, json.dumps(
            {"title": self.title, "steps": self.steps,
             "problem": problem, "when": datetime.now().isoformat(timespec="seconds")},
            ensure_ascii=False, indent=1))
        if self.server is None:
            write_file(self.page_file,
                       page(self.steps, self.title, self.subtitle,
                            problem=problem, go_to=go_to))

    def wait_for_page(self) -> None:
        """The installer's last job: let the page read the ending.

        **The page must not be sent to the file** — browsers don't allow
        going from `http://` to `file://` and say nothing about it. That's
        how it was done at first, and on someone else's Mac the page froze
        on "Downloading the model" after the install had finished. So the
        server waits until the page has picked up the final state: "Done",
        or the whole problem.

        After "Done" there's no point waiting long: within seconds the
        launcher takes the same port and sends the page on to Vertcut
        (`_tell_live_page`), and the page keeps asking patiently all that
        time. After a problem — longer: nothing but the page will show
        that problem to the person, and the tab may be in the background,
        where the browser asks less often.
        """
        if self.server is None:
            return
        # The file is rewritten too, in case someone is looking at it.
        write_file(self.page_file,
                   page(self.steps, self.title, self.subtitle,
                        problem=self.problem, reload_every=0))
        self.finished = True
        self.delivered.wait(120 if self.problem else 5)
        self.server.shutdown()
        # The port is released right away, not when the process exits:
        # the launcher takes it over to send the page on to Vertcut.
        self.server.server_close()


class _LastWord:
    """The launcher's last word to the live page, after the install.

    Like `Progress` for the server, but without steps: one title and
    either Vertcut's address or a problem."""

    def __init__(self, title: str, subtitle: str, go_to: str = "",
                 problem: str = "", log_tail: str = ""):
        self.steps: list[dict] = []
        self.title, self.subtitle = title, subtitle
        self.go_to, self.problem, self.log_tail = go_to, problem, log_tail
        self.finished = True
        self.delivered = threading.Event()


def _tell_live_page(page_dir: Path, last_word: _LastWord, seconds: float) -> bool:
    """Take over the progress page's port and give it the last word.

    After the installer's server has gone, the page keeps asking the same
    address. Whoever takes the port first is who it listens to — here
    that's the launcher, with Vertcut's address. The browser allows going
    from `http://` to `http://`; to `file://` it doesn't, which is why
    this isn't a file.

    Waits for the page to ask, but no longer than `seconds`: the tab may
    have been closed. A background tab asks less often — the browser
    saves effort — so "go to Vertcut" waits a long time.

    Returns whether the word reached the page.
    """
    port_file = page_dir / PORT_FILE
    try:
        port = int(port_file.read_text(encoding="utf-8").strip())
    except (OSError, ValueError):
        return False
    try:
        server = _start_server(last_word, port)
    except OSError:
        # Someone else took the port — no way to talk to the page.
        port_file.unlink(missing_ok=True)
        return False
    try:
        reached = last_word.delivered.wait(seconds)
        time.sleep(0.3)   # let the answer go out completely
        return reached
    finally:
        server.shutdown()
        server.server_close()
        port_file.unlink(missing_ok=True)


# ─── how to call this from outside ────────────────────────────────────

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
    """Show a problem on the page — for the launcher, which has no words
    of its own.

    The launcher is a shell script, and it shouldn't write markup: the
    same page written in two places would drift apart at the first edit.
    So the launcher calls this.
    """
    utf8_output()
    import argparse
    parser = argparse.ArgumentParser(
        description="Show the last word on the install progress page")
    parser.add_argument("--page-dir", dest="page_dir", required=True, type=Path)
    parser.add_argument("--title", dest="title", default="Vertcut didn't start")
    parser.add_argument("--hint", dest="hint", default="")
    parser.add_argument("--problem", dest="problem", default="")
    parser.add_argument("--log-tail", dest="log_tail", default="",
                        help="a log file whose last lines to show")
    parser.add_argument("--go-to", dest="go_to", default="",
                        help="an address to send the page to")
    parser.add_argument("--wait", dest="wait", type=float, default=10,
                        help="how many seconds to wait for the live progress page")
    a = parser.parse_args(args)
    log_tail = ""
    if a.log_tail and Path(a.log_tail).exists():
        lines = Path(a.log_tail).read_text(encoding="utf-8",
                                           errors="replace").splitlines()
        log_tail = "\n".join(lines[-25:])
    if a.go_to:
        # The person is looking at the progress page and waiting. Opening
        # Vertcut in a SECOND tab would leave them with two, one of them
        # dead. Better to turn the one they're looking at into Vertcut.
        write_file(a.page_dir / "progress.html",
                   page([], "Done", "Opening Vertcut…", go_to=a.go_to))
        last_word = _LastWord("Done", "Opening Vertcut…", go_to=a.go_to)
    else:
        write_file(a.page_dir / "progress.html",
                   page([], a.title, a.hint,
                        problem=a.problem, log_tail=log_tail))
        last_word = _LastWord(a.title, a.hint,
                              problem=a.problem, log_tail=log_tail)
    # 0: the word reached the live page, nothing needs opening.
    # 3: it didn't — there's no page, and the launcher opens the file itself.
    return 0 if _tell_live_page(a.page_dir, last_word, a.wait) else 3


if __name__ == "__main__":
    sys.exit(main())
