"""Прочёс перед выпуском: нет ли кириллицы там, где её ВИДИТ человек.

    python tools/cyrillic-sweep.py              — всё, ~4 минуты
    python tools/cyrillic-sweep.py --keep       — и не стирать песочницу
    python tools/cyrillic-sweep.py --only screen,api

Части: `cli` (команда), `screen` (экран в невидимом Chrome), `api`
(отказы ручек), `disk` (имена и содержимое файлов, которые сервис
пишет человеку), `install` (страница хода, README,
окно Vertcut.exe, имена в архивах). Ноль находок — выход 0.

**Чем это отличается от `tests/test_english.py`.** Тот смотрит на
строки в КОДЕ и по признакам решает, видит ли их человек. Этот
смотрит на то, что человек ДЕЙСТВИТЕЛЬНО получил: вывод команды,
текст запущенной страницы, файлы на диске. Слово, которое уходит
к человеку через переменную или с диска, видно только так.

**Приём: песочница целиком английская.** Английское видео (речь
`say`), английские имена файлов, английский сценарий, свой шрифт
и фон с английскими именами, английские ответы модели. Тогда любая
кириллица на выходе — находка, и разбираться, чья она, не надо.
Исключения — явным списком (`ПОСАЖЕНО`, `маска`): то, что «человек»
нарочно ввёл русскими буквами (испорченный ключ, незнакомый ключ
стиля), и пути, в которых лежат сам репозиторий и песочница.

**Ничего живого не трогает.** Свой `VERTCUT_HOME` во временной папке,
свой профиль Chrome, Chrome невидимый (`--headless`). Модель — своя
заглушка на 127.0.0.1: денег не тратит, отвечает по-английски и умеет
отказывать, как поставщик. Ручки, которые открывают окна на столе
человека (системный диалог, Finder), страница звать может, но ответ
им подменяет прочёс: окна не открываются.

Нужны: macOS (`say`), Google Chrome, ffmpeg, окружение сервиса
(`.venv` в репозитории). Нового не ставит ничего.
"""

from __future__ import annotations

import argparse
import base64
import http.client
import json
import os
import re
import shutil
import signal
import socket
import struct
import subprocess
import sys
import tempfile
import threading
import time
import unicodedata
import urllib.parse
import zipfile
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

РЕПО = Path(__file__).resolve().parent.parent
ПИТОН = РЕПО / ".venv" / "bin" / "python"
CHROME = Path("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome")
РУССКОЕ = re.compile(r"[А-Яа-яЁё]")
СЛАГ = "morning-walk"

# То, что «человек» нарочно ввёл русскими буквами. Строка с этим —
# не находка: это его же слово, вернувшееся к нему.
ПОСАЖЕНО = ["sk-аnt-кириллица", "…лица", "размер", "“а”"]

СЦЕНАРИЙ = """\
Every morning I walk along the river before work. The air is cold and the city is still quiet.

I count the bridges as I pass them. There are seven, and each one has its own sound under my feet.

Some days I stop at the bakery near the third bridge. The owner always asks how the walk went, and I always say it was fine.

By the time I reach the old market, the streets are full of people. That is when I turn around and head home.

It takes about forty minutes. It is the best part of my day, and I would not trade it for anything.
"""
# Чужой сценарий: укладка на чужую речь обязана упасть словами.
ЧУЖОЙ = "Tomatoes need full sun and a lot of water in July.\n"


class Находки:
    def __init__(self, маски: list[str]):
        # Пути на macOS приходят то в составной форме юникода, то
        # в разложенной («й» — две точки кода): маска ищет обе.
        self.маски = sorted({ф(м) for м in маски for ф in (
            lambda с: unicodedata.normalize("NFC", с),
            lambda с: unicodedata.normalize("NFD", с))}, key=len, reverse=True)
        self.всё: dict[tuple[str, str], str] = {}
        self.журнал = None          # всё просмотренное — для разбора глазами
        self.известное: set[str] = set()   # файлы с русскими ключами json

    def чисто(self, текст: str) -> str:
        for м in self.маски:
            текст = текст.replace(м, "<PATH>")
        return текст

    def смотреть(self, где: str, текст: str, откуда: str = "") -> None:
        текст = self.чисто(текст)
        if self.журнал:
            self.журнал.write(json.dumps({"где": где, "откуда": откуда, "текст": текст},
                                         ensure_ascii=False) + "\n")
        # Трассировка питона — не слова, а падение: русские в ней имена
        # кода. Находка одна — «упало», с последней строкой.
        for след in re.finditer(r"Traceback \(most recent call last\):\n(?:[ \t].*\n)*(.+)",
                                текст):
            self.отметить(где, f"ПАДЕНИЕ: {след.group(1)[:160]}", откуда)
        текст = re.sub(r"Traceback \(most recent call last\):\n(?:[ \t].*\n)*.*", "", текст)
        for строка in текст.splitlines():
            if not РУССКОЕ.search(строка):
                continue
            if any(п in строка for п in ПОСАЖЕНО):
                continue
            self.всё.setdefault((где, строка.strip()[:200]), откуда)

    def отметить(self, где: str, строка: str, откуда: str = "") -> None:
        """Находка не про буквы: поломка, которую прочёс увидел по дороге."""
        self.всё.setdefault((где, строка[:200]), откуда)

    def печать(self) -> int:
        if self.известное:
            print(f"\nрусские ключи и значения-жетоны json (решение автора, 22-я "
                  "сессия, — не находка): "
                  f"{len(self.известное)} файлов, например "
                  + ", ".join(sorted(self.известное)[:6]))
        if not self.всё:
            print("\nкириллицы, которую видит человек: 0")
            return 0
        print(f"\nНАЙДЕНО {len(self.всё)}:")
        for (где, строка), откуда in sorted(self.всё.items()):
            print(f"  [{где}] {строка}" + (f"   ← {откуда}" if откуда else ""))
        return 1


# ─────────────────────────────────────────────────────────────────────
# Песочница
# ─────────────────────────────────────────────────────────────────────

def ffmpeg() -> str:
    return shutil.which("ffmpeg") or "ffmpeg"


def песочница(корень: Path) -> dict:
    src = корень / "src"
    src.mkdir(parents=True)
    (src / "Morning-Walk-script.txt").write_text(СЦЕНАРИЙ)
    (src / "Garden-Notes-script.txt").write_text(ЧУЖОЙ)
    subprocess.run(["say", "-v", "Samantha", "-r", "130", "-f",
                    src / "Morning-Walk-script.txt", "-o", src / "voice.aiff"],
                   check=True)
    куски = ["testsrc2", "smptehdbars", "mandelbrot",
             "life=mold=10:ratio=0.1:death_color=#202060:life_color=#e0c040",
             "cellauto=rule=110"]
    входы, цепь = [], []
    for н, к in enumerate(куски):
        имя, _, доводы = к.partition("=")
        доводы = ("s=1920x1080:r=25" + (":" + доводы if доводы else ""))
        входы += ["-f", "lavfi", "-i", f"{имя}={доводы}"]
        цепь.append(f"[{н}]trim=0:10,setpts=PTS-STARTPTS,format=yuv420p[в{н}]")
    цепь.append("".join(f"[в{н}]" for н in range(len(куски)))
                + f"concat=n={len(куски)}:v=1:a=0[v]")
    subprocess.run([ffmpeg(), "-v", "error", "-y", *входы, "-i", src / "voice.aiff",
                    "-filter_complex", ";".join(цепь), "-map", "[v]",
                    "-map", f"{len(куски)}:a", "-c:v", "libx264", "-preset",
                    "veryfast", "-crf", "28", "-c:a", "aac", "-shortest",
                    src / "Morning-Walk.mp4"], check=True)
    # Второе видео — для «разбор упал»: та же речь, чужой сценарий.
    shutil.copy(src / "Morning-Walk.mp4", src / "Garden-Notes.mp4")
    # Третье — длинное, чтобы застать разбор идущим.
    subprocess.run([ffmpeg(), "-v", "error", "-y", "-stream_loop", "5", "-i",
                    src / "Morning-Walk.mp4", "-c", "copy", src / "Long-Talk.mp4"],
                   check=True)
    subprocess.run([ffmpeg(), "-v", "error", "-y", "-f", "lavfi", "-i",
                    "gradients=s=1080x1920:d=1", "-frames:v", "1",
                    src / "Sunset-Background.png"], check=True)
    subprocess.run([ffmpeg(), "-v", "error", "-y", "-f", "lavfi", "-i",
                    "testsrc2=s=1280x720:d=1", "-frames:v", "1",
                    src / "Episode-Thumbnail.jpg"], check=True)
    for шрифт in ("/System/Library/Fonts/Supplemental/Courier New Bold.ttf",
                  "/System/Library/Fonts/Supplemental/Arial Bold.ttf"):
        if Path(шрифт).exists():
            shutil.copy(шрифт, src / "Courier-Bold.ttf")
            break
    return {"src": src, "заглушки": заглушки(корень, src)}


def заглушки(корень: Path, src: Path) -> Path:
    """`osascript` и `open` своими файлами впереди PATH сервиса.

    **Без них прочёс открывал окна на столе человека** — так и было
    на первом прогоне: ручки шрифта, обложки и фона зовут системный
    диалог сами, и три окна «Choose…» встали поверх всего. Заглушка
    «выбирает» файл из песочницы (или «нажимает Отмену», если рядом
    лежит файл `cancel`) и записывает, какое окно открылось бы.
    """
    папка = корень / "fake-bin"
    папка.mkdir()
    журнал = папка / "calls.log"
    (папка / "osascript").write_text(f"""#!/bin/sh
echo "osascript $*" >> '{журнал}'
if [ -e '{папка}/cancel' ]; then echo "execution error: User canceled. (-128)" >&2; exit 1; fi
case "$*" in
  *font*) echo '{src}/Courier-Bold.ttf' ;;
  *thumbnail*) echo '{src}/Episode-Thumbnail.jpg' ;;
  *image*) echo '{src}/Sunset-Background.png' ;;
  *) echo '{src}/Morning-Walk.mp4' ;;
esac
""")
    (папка / "open").write_text(f"#!/bin/sh\necho \"open $*\" >> '{журнал}'\n")
    for имя in ("osascript", "open"):
        (папка / имя).chmod(0o755)
    return папка


# ─────────────────────────────────────────────────────────────────────
# Заглушка модели: отвечает как Anthropic, по-английски, бесплатно
# ─────────────────────────────────────────────────────────────────────

class Модель:
    """Режим меняется на ходу: `модель.режим = "401"`."""

    ОТКАЗЫ = {
        "401": (401, "authentication_error", "invalid x-api-key"),
        "429": (429, "rate_limit_error", "Number of requests has exceeded your rate limit"),
        "429money": (429, "insufficient_quota", "You exceeded your current quota"),
        "500": (500, "api_error", "Internal server error"),
        "404": (404, "not_found_error", "model: nope"),
        "400": (400, "invalid_request_error", "model: unknown model"),
    }

    def __init__(self):
        self.режим = "ok"
        модель = self

        class Ручка(BaseHTTPRequestHandler):
            def log_message(self, *_):
                pass

            def _отдать(self, код, тело):
                сырое = json.dumps(тело).encode()
                self.send_response(код)
                self.send_header("content-type", "application/json")
                self.send_header("content-length", str(len(сырое)))
                self.end_headers()
                self.wfile.write(сырое)

            def _отказ(self) -> bool:
                if модель.режим not in модель.ОТКАЗЫ:
                    return False
                код, порода, что = модель.ОТКАЗЫ[модель.режим]
                self._отдать(код, {"type": "error",
                                   "error": {"type": порода, "message": что}})
                return True

            def do_GET(self):
                if not self._отказ():
                    self._отдать(200, {"data": [
                        {"id": "claude-fable-5-1", "display_name": "Fable 5.1"},
                        {"id": "claude-haiku-5-5", "display_name": "Haiku 5.5"}]})

            def do_POST(self):
                тело = json.loads(self.rfile.read(int(self.headers["content-length"])))
                if self._отказ():
                    return
                система = тело.get("system") or ""
                текст = тело["messages"][-1]["content"]
                # Ключи ответа — договор сервиса с моделью (`prompts.ФОРМА`):
                # не для человека: так их пишет модель
                фр, оп = "фрагменты", "описания"
                if модель.режим == "empty":
                    ответ = ""
                elif модель.режим == "garbage":
                    ответ = "Here are some thoughts about the video, no list."
                elif фр in система:
                    ответ = json.dumps({фр: [
                        {"с": 1, "по": 6, "название": "The river walk",  # не для человека
                         "о_чём": "Why the morning walk matters"},  # не для человека
                        {"с": 6, "по": 13, "название": "Seven bridges",  # не для человека
                         "о_чём": "Counting bridges on the way"},  # не для человека
                        {"с": 5, "по": 9, "название": "Overlapping one",  # не для человека
                         "о_чём": "This one overlaps another"},  # не для человека
                        {"с": 9, "по": 99, "название": "Out of range",  # не для человека
                         "о_чём": "Phrases that do not exist"},  # не для человека
                        {"с": 8, "по": 8, "название": "Too short",  # не для человека
                         "о_чём": "A single short phrase"},  # не для человека
                    ]})
                elif оп in система:
                    ключи = re.findall(r"KEY (\S+)", текст)
                    ответ = json.dumps({оп: [
                        {"ключ": к, "текст": f"What do {н + 2} bridges sound like?"}  # не для человека
                        for н, к in enumerate(ключи)]})
                else:
                    ответ = "OK"
                self._отдать(200, {
                    "id": "msg_sweep", "type": "message", "role": "assistant",
                    "model": тело.get("model") or "claude-fable-5-1",
                    "content": [{"type": "text", "text": ответ}],
                    "stop_reason": "end_turn",
                    "usage": {"input_tokens": 1200, "output_tokens": 300}})

        self.сервер = ThreadingHTTPServer(("127.0.0.1", 0), Ручка)
        self.адрес = f"http://127.0.0.1:{self.сервер.server_address[1]}/v1"
        threading.Thread(target=self.сервер.serve_forever, daemon=True).start()


# ─────────────────────────────────────────────────────────────────────
# Команда
# ─────────────────────────────────────────────────────────────────────

def окружение(дом: Path, заглушки: Path) -> dict:
    """Своё окружение сервиса: свой дом, без ключей, заглушки окон впереди."""
    вышло = {к: з for к, з in os.environ.items()
             if к not in ("ANTHROPIC_API_KEY", "OPENAI_API_KEY")}
    вышло["VERTCUT_HOME"] = str(дом)
    вышло["PATH"] = f"{заглушки}:{вышло.get('PATH', '')}"
    # Предохранитель: окно на столе человека — хуже, чем непройденный прочёс.
    for имя in ("osascript", "open"):
        if Path(shutil.which(имя, path=вышло["PATH"]) or "").parent != заглушки:
            raise SystemExit(f"{имя} в окружении сервиса — не заглушка; прочёс не идёт")
    return вышло


class Команда:
    def __init__(self, дом: Path, находки: Находки, журнал: Path, заглушки: Path):
        self.окружение = окружение(дом, заглушки)
        self.заглушки = заглушки
        self.дом = дом
        self.находки = находки
        self.журнал = журнал.open("a")

    def __call__(self, *доводы, вход: str | None = None, смотреть: bool = True):
        доводы = [str(д) for д in доводы]
        вышло = subprocess.run([ПИТОН, "-m", "vertcut", *доводы], cwd=РЕПО,
                               env=self.окружение, capture_output=True, text=True,
                               input=вход, timeout=900)
        текст = вышло.stdout + вышло.stderr
        self.журнал.write(f"\n$ vertcut {' '.join(доводы)}   [{вышло.returncode}]\n{текст}")
        self.журнал.flush()
        if смотреть:
            self.находки.смотреть("cli", текст, "vertcut " + " ".join(доводы[:3]))
        return вышло

    def ключи(self) -> list[str]:
        return sorted(п.name for п in (self.дом / СЛАГ / "cuts").iterdir() if п.is_dir())


def часть_cli(v: Команда, src: Path, модель: Модель) -> dict:
    """Все подкоманды: --help, обычный вывод, отказы. Попутно строит
    состояния, которые потом покажет экран."""
    v("--help")
    for подкоманда in ("check", "ingest", "phrases", "videos", "crop", "pick",
                       "cuts", "title", "frame", "plans", "text", "subs",
                       "fonts", "looks", "style", "plate", "render", "proof",
                       "ai", "suggest", "describe", "screen", "queue"):
        v(подкоманда, "--help")
    v("check")
    v("videos")
    v("ingest", src / "Morning-Walk.mp4", "--script", src / "Morning-Walk-script.txt")
    v("ingest", src / "Morning-Walk.mp4")          # уже разобрано
    v("videos"); v("phrases", СЛАГ); v("phrases", СЛАГ, "--from", 2, "--to", 5)
    v("cuts", СЛАГ)
    v("pick", СЛАГ, "--range", "1-6")
    v("pick", СЛАГ, "--range", "6-13")
    v("pick", СЛАГ, "--range", "1-3,8-13")
    v("pick", СЛАГ, "--start", "0:02", "--end", "0:19")
    v("pick", СЛАГ, "--text", "-", вход=" ".join(СЦЕНАРИЙ.split(". ")[2:7]))
    v("pick", СЛАГ, "--text", "I count the bridges")          # коротко
    к = v.ключи()
    к1, к2 = к[1], к[2]
    v("cuts", СЛАГ)
    v("title", СЛАГ, к1); v("title", СЛАГ, к1, "--title", "Seven Bridges")
    v("plans", СЛАГ, к1); v("plans", СЛАГ, к1, "--sheet")
    v("frame", СЛАГ, к1, "--shot", 1, "--crop", 0.3)
    v("frame", СЛАГ, к1, "--shot", 2, "--mode", "full")
    v("frame", СЛАГ, к1, "--shot", 1, "--reset")
    v("text", СЛАГ, к2); v("text", СЛАГ, к2, "--phrase", 5, "--split", 3)
    v("text", СЛАГ, к2, "--phrase", 5, "--merge")
    v("text", СЛАГ, к2, "--phrase", 6, "--text", "I count every bridge.")
    v("subs", СЛАГ, к1); v("subs", СЛАГ, к1, "--sheet")
    v("fonts"); v("looks"); v("looks", СЛАГ)
    v("crop", СЛАГ, "--shots", "1-2", "--sheet")
    v("style", СЛАГ); v("style", СЛАГ, "--sheet", "--show-zones")
    v("style", СЛАГ, "--set", "size=0.05"); v("style", СЛАГ, "--case", "all_caps")
    v("style", СЛАГ, "--font", src / "Courier-Bold.ttf"); v("fonts")
    v("style", СЛАГ, "--karaoke", "word", "--karaoke-by", "box")
    v("style", СЛАГ, "--background", "box"); v("style", СЛАГ, "--safe-zones", "on")
    v("style", СЛАГ, "--save-as-my-style"); v("style", СЛАГ, "--default-style")
    v("style", СЛАГ, "--my-style")
    v("style", СЛАГ, к1); v("style", СЛАГ, к1, "--set", "size=0.06")
    v("style", СЛАГ, к1, "--apply-to-all"); v("style", СЛАГ, к1, "--sheet")
    v("plate", СЛАГ); v("plate", СЛАГ, к1)
    v("plate", СЛАГ, к1, "--background-image", src / "Sunset-Background.png")
    v("plate", СЛАГ, к1, "--thumbnail", src / "Episode-Thumbnail.jpg")
    v("plate", СЛАГ, к1, "--text", "Thanks for watching")
    v("render", СЛАГ, к1); v("cuts", СЛАГ)
    v("render", СЛАГ)
    v("proof", СЛАГ, к1)
    v("text", СЛАГ, к1, "--phrase", 2, "--text", "The air is cold and quiet.")
    v("cuts", СЛАГ)                                  # устарел
    v("queue", СЛАГ); v("queue", СЛАГ, "--again")
    # AI без ключа, потом с заглушкой
    v("ai"); v("suggest", СЛАГ); v("describe", СЛАГ)
    v("ai", "--api-address", модель.адрес)
    v("ai", "--api-key", "sk-ant-sweep-0000000000")
    v("ai", "--model", "claude-fable-5-1"); v("ai", "--ask-above", "0.5")
    v("ai", "--daily-limit", "2"); v("ai"); v("ai", "--test")
    v("suggest", СЛАГ, "--yes"); v("suggest", СЛАГ)
    v("describe", СЛАГ, "--yes"); v("describe", СЛАГ, к1, "--rewrite-all", "--yes")
    for режим in ("401", "429", "429money", "500", "404", "400", "empty", "garbage"):
        модель.режим = режим
        v("ai", "--test"); v("suggest", СЛАГ, "--again", "--yes")
        v("describe", СЛАГ, к1, "--rewrite-all", "--yes")
    модель.режим = "ok"
    v("suggest", СЛАГ, "--again", "--yes")           # годный ответ на диск
    v("ai", "--api-type", "openai"); v("ai"); v("ai", "--api-type", "anthropic")
    v("ai", "--api-address", модель.адрес)
    v("ai", "--model", "claude-opus-5")              # цена известна
    v("ai", "--ask-above", "0.000001"); v("suggest", СЛАГ, "--again")
    v("ai", "--ask-above", "0.5"); v("ai", "--daily-limit", "0.000001")
    v("suggest", СЛАГ, "--again", "--yes")
    v("ai", "--daily-limit", "2"); v("ai", "--model", "claude-fable-5-1")
    v("ai", "--ask-above", "abc"); v("ai", "--daily-limit", "-3")
    v("ai", "--api-address", "ftp://nope"); v("ai", "--api-key", ПОСАЖЕНО[0])
    v("ai", "--api-key", "sk-ant-sweep-0000000000")
    v("ai", "--api-address", "http://127.0.0.1:9/v1"); v("ai", "--test")
    v("ai", "--api-address", модель.адрес)
    # отказы
    v("phrases", "no-such-video"); v("cuts", "no-such-video")
    v("pick", "no-such-video", "--range", "1-2")
    v("pick", СЛАГ, "--range", "99-120"); v("pick", СЛАГ, "--range", "abc")
    v("pick", СЛАГ, "--text", "words that are not there at all")
    v("pick", СЛАГ, "--start", "9:00", "--end", "9:10")
    v("pick", СЛАГ, "--start", "0:10"); v("pick", СЛАГ)
    v("title", СЛАГ, "0000-0001"); v("plans", СЛАГ, "9999-9999")
    v("render", СЛАГ, "9999-9999")
    v("frame", СЛАГ, к1, "--shot", 99, "--crop", 0.5)
    v("frame", СЛАГ, к1, "--shot", 1, "--crop", 7)
    v("text", СЛАГ, к1, "--phrase", 999, "--text", "x")
    v("text", СЛАГ, к1, "--phrase", 2, "--split", 99)
    v("style", СЛАГ, "--set", "bogus=1"); v("style", СЛАГ, "--set", "size=abc")
    v("style", СЛАГ, "--set", "size"); v("style", СЛАГ, "--preset", "nope")
    v("style", СЛАГ, "--font", "No Such Font")
    v("style", СЛАГ, "--font", src / "Morning-Walk-script.txt")
    v("ingest", src / "missing.mp4"); v("ingest", src / "Morning-Walk-script.txt")
    v("ingest", src / "Morning-Walk.mp4", "--script", src / "missing.txt")
    v("plate", СЛАГ, к1, "--thumbnail", src / "missing.png")
    v("plate", СЛАГ, к1, "--background-image", src / "Morning-Walk-script.txt")
    v("proof", СЛАГ, к2); v("queue", СЛАГ, "--only", "9999-9999")
    v("crop", СЛАГ, "--shots", "50-60"); v("looks", "no-such-video")
    v("describe", СЛАГ, "9999-9999", "--yes")
    v("nosuchcommand"); v("pick", СЛАГ, "--nosuchflag")
    стиль = v.дом / СЛАГ / "subtitles.yaml"
    целый = стиль.read_text()
    стиль.write_text(целый + "\n  : : [broken\n")
    v("style", СЛАГ); v("render", СЛАГ, к1, "--again"); v("subs", СЛАГ, к1)
    стиль.write_text(re.sub(r"(?m)^version:.*\n", "", целый))
    v("style", СЛАГ); v("subs", СЛАГ, к1)
    стиль.write_text(целый.replace("size:", ПОСАЖЕНО[2] + ":", 1)); v("style", СЛАГ)
    стиль.write_text(целый)
    # Разбор, который падает словами: чужой сценарий.
    v("ingest", src / "Garden-Notes.mp4", "--script", src / "Garden-Notes-script.txt")
    return {"ключи": v.ключи()}


# ─────────────────────────────────────────────────────────────────────
# Протокол отладки Chrome: свой маленький клиент на стандартной библиотеке
# ─────────────────────────────────────────────────────────────────────

class Сокет:
    """WebSocket ровно настолько, насколько он нужен для Chrome на 127.0.0.1."""

    def __init__(self, адрес: str):
        у = urllib.parse.urlparse(адрес)
        self.с = socket.create_connection((у.hostname, у.port), timeout=120)
        ключ = base64.b64encode(os.urandom(16)).decode()
        self.с.sendall((f"GET {у.path} HTTP/1.1\r\nHost: {у.hostname}:{у.port}\r\n"
                        "Upgrade: websocket\r\nConnection: Upgrade\r\n"
                        f"Sec-WebSocket-Key: {ключ}\r\nSec-WebSocket-Version: 13\r\n\r\n")
                       .encode())
        шапка = b""
        while b"\r\n\r\n" not in шапка:
            шапка += self.с.recv(1)
        if b" 101 " not in шапка.split(b"\r\n")[0]:
            raise RuntimeError(шапка.decode(errors="replace"))

    def послать(self, текст: str) -> None:
        тело = текст.encode()
        маска = os.urandom(4)
        н = len(тело)
        шапка = bytes([0x81])
        if н < 126:
            шапка += bytes([0x80 | н])
        elif н < 65536:
            шапка += bytes([0x80 | 126]) + struct.pack(">H", н)
        else:
            шапка += bytes([0x80 | 127]) + struct.pack(">Q", н)
        self.с.sendall(шапка + маска + bytes(б ^ маска[и % 4] for и, б in enumerate(тело)))

    def _ровно(self, н: int) -> bytes:
        куски = b""
        while len(куски) < н:
            к = self.с.recv(н - len(куски))
            if not к:
                raise ConnectionError("Chrome closed the connection")
            куски += к
        return куски

    def принять(self) -> str:
        собрано = b""
        while True:
            б1, б2 = self._ровно(2)
            н = б2 & 0x7F
            if н == 126:
                н = struct.unpack(">H", self._ровно(2))[0]
            elif н == 127:
                н = struct.unpack(">Q", self._ровно(8))[0]
            тело = self._ровно(н)
            код = б1 & 0x0F
            if код == 8:
                raise ConnectionError("Chrome closed the connection")
            if код in (9, 10):
                continue
            собрано += тело
            if б1 & 0x80:
                return собрано.decode()


class Chrome:
    def __init__(self, профиль: Path, загрузки: Path):
        self.профиль = профиль
        self.процесс = subprocess.Popen(
            [str(CHROME), "--headless=new", "--remote-debugging-port=0",
             f"--user-data-dir={профиль}", "--no-first-run",
             "--no-default-browser-check", "--disable-extensions",
             "--window-size=1440,1000", "about:blank"],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        порт_файл = профиль / "DevToolsActivePort"
        for _ in range(100):
            if порт_файл.exists() and порт_файл.read_text().strip():
                break
            time.sleep(0.1)
        порт = порт_файл.read_text().split()[0]
        связь = http.client.HTTPConnection("127.0.0.1", int(порт))
        связь.request("GET", "/json/list")
        страница = next(ц for ц in json.loads(связь.getresponse().read())
                        if ц["type"] == "page")
        self.ws = Сокет(страница["webSocketDebuggerUrl"])
        self.н = 0
        self.события: list[dict] = []
        self("Page.enable"); self("Runtime.enable")
        self("Page.setDownloadBehavior", behavior="allow", downloadPath=str(загрузки))

    def __call__(self, метод: str, **доводы):
        self.н += 1
        свой = self.н
        self.ws.послать(json.dumps({"id": свой, "method": метод, "params": доводы}))
        while True:
            это = json.loads(self.ws.принять())
            if это.get("id") == свой:
                if "error" in это:
                    raise RuntimeError(f"{метод}: {это['error']}")
                return это.get("result", {})
            self.события.append(это)
            self._событие(это)

    def _событие(self, это: dict) -> None:
        if getattr(self, "на_событие", None):
            self.на_событие(это)

    def js(self, выражение: str):
        ответ = self("Runtime.evaluate", expression=выражение,
                     awaitPromise=True, returnByValue=True)
        if "exceptionDetails" in ответ:
            raise RuntimeError(json.dumps(ответ["exceptionDetails"])[:400])
        return ответ["result"].get("value")

    def снимок(self, куда: Path) -> None:
        куда.write_bytes(base64.b64decode(
            self("Page.captureScreenshot", format="png")["data"]))

    def закрыть(self) -> None:
        self.процесс.terminate()
        try:
            self.процесс.wait(10)
        except subprocess.TimeoutExpired:
            self.процесс.kill()


# Что слушает страница: каждый текст и каждую подпись, которые хоть раз
# появились в документе, — в том числе полосу, которая исчезает через
# секунду. Классы, `data-…`, id и содержимое <script>/<style> — нет:
# их человек не видит.
СЛУШАТЬ = r"""
(() => {
  const ПОДПИСИ = ['title', 'placeholder', 'aria-label', 'alt', 'download',
                   'aria-description', 'aria-valuetext', 'label'];
  window.__слова = window.__слова || new Map();
  const взять = (с, как) => {
    с = (с || '').replace(/\s+/g, ' ').trim();
    if (с) window.__слова.set(как + '\u0001' + с, location.hash);
  };
  const обойти = (у) => {
    if (!у) return;
    if (у.nodeType === 3) {
      const р = у.parentElement;
      if (р && /^(SCRIPT|STYLE|NOSCRIPT)$/.test(р.tagName)) return;
      взять(у.data, 'text');
      return;
    }
    if (у.nodeType !== 1) return;
    for (const п of ПОДПИСИ) if (у.hasAttribute(п)) взять(у.getAttribute(п), '@' + п);
    if (у.tagName === 'INPUT' && /^(button|submit|reset)$/i.test(у.type)) взять(у.value, '@value');
    if (у.tagName === 'TITLE') взять(у.textContent, 'title');
    for (const д of у.childNodes) обойти(д);
  };
  new MutationObserver((все) => {
    for (const м of все) {
      if (м.type === 'childList') м.addedNodes.forEach(обойти);
      else if (м.type === 'characterData') обойти(м.target);
      else if (м.type === 'attributes') взять(м.target.getAttribute(м.attributeName), '@' + м.attributeName);
    }
  }).observe(document, { subtree: true, childList: true, characterData: true,
                          attributes: true, attributeFilter: ПОДПИСИ });
  document.addEventListener('DOMContentLoaded', () => обойти(document.documentElement));
})();
"""

# Найти, по чему ещё не щёлкали. Подпись кнопки — её текст, подпись
# и место: экран перерисовывается целиком, и сам узел каждый раз новый.
КНОПКИ = r"""
(() => {
  const видно = (э) => { const р = э.getBoundingClientRect();
    return р.width > 0 && р.height > 0 && getComputedStyle(э).visibility !== 'hidden'; };
  const все = [...document.querySelectorAll(
    'button, [role=button], [role=tab], summary, a[href], label, ' +
    'input[type=checkbox], input[type=radio], [tabindex="0"], select')];
  return все.filter((э) => видно(э) && !э.disabled).map((э, н) => {
    const путь = []; let у = э;
    while (у && у !== document.body && путь.length < 4) {
      путь.unshift(у.tagName + '.' + [...у.classList].slice(0, 2).join('.'));
      у = у.parentElement;
    }
    э.dataset.sweep = String(н);
    return { н, подпись: [э.tagName, (э.innerText || э.value || '').slice(0, 60),
             э.getAttribute('title') || '', э.getAttribute('aria-label') || '',
             э.getAttribute('href') || '', путь.join('>')].join('|') };
  });
})()
"""

# Чем страница на столе человека открыла бы окно или стёрла бы то,
# что нужно следующим экранам. Ответ подменяется отказом словами —
# английскими, — и экран показывает свою полосу «не вышло».
ПОДМЕНИТЬ: tuple[str, ...] = ()


ПОДМЕНА = r"""
(() => {
  // Сколько просьб в пути: по нулю прочёс понимает, что экран дорисован.
  window.__летит = 0;
  const свой = window.fetch.bind(window);
  const ЗАКРЫТЫ = %s.map((и) => encodeURI('/апи/' + и));
  window.fetch = async (адрес, ...доводы) => {
    const а = String(адрес);
    if (ЗАКРЫТЫ.some((з) => а.includes(з + '?') || а.endsWith(з))) {
      return new Response(JSON.stringify({ беда: 'Sweep: a window would open on the desktop here',
        подсказка: 'the sweep answers instead of the service' }),
        { status: 400, headers: { 'content-type': 'application/json' } });
    }
    window.__летит++;
    try { return await свой(адрес, ...доводы); } finally { window.__летит--; }
  };
  // Наружу не ходим: ссылка на GitHub и пожертвования записывается, а не открывается.
  window.__наружу = [];
  document.addEventListener('click', (е) => {
    const а = е.target.closest && е.target.closest('a[href]');
    if (а && /^https?:/.test(а.href) && !а.href.startsWith(location.origin)) {
      е.preventDefault(); window.__наружу.push(а.href);
    }
  }, true);
})();
""" % json.dumps(list(ПОДМЕНИТЬ), ensure_ascii=False)

# Поля: что «человек» туда вводит. Английское — значит, кириллица
# в ответе на это не его.
ВВОД = r"""
(() => {
  const видно = (э) => { const р = э.getBoundingClientRect(); return р.width > 0 && р.height > 0; };
  const поля = [...document.querySelectorAll('input, textarea, select')].filter(
    (э) => видно(э) && !э.disabled && !/^(file|checkbox|radio|button|submit|hidden)$/i.test(э.type));
  поля.forEach((э, н) => { э.dataset.sweepField = String(н); });
  return поля.map((э, н) => ({ н, тип: э.tagName === 'SELECT' ? 'select' : (э.type || 'text') }));
})()
"""


class Экран:
    """`vertcut screen` на своём порту, со своим домом."""

    def __init__(self, дом: Path, журнал: Path, находки: Находки, заглушки: Path):
        with socket.socket() as с:
            с.bind(("127.0.0.1", 0))
            self.порт = с.getsockname()[1]
        self.журнал = журнал
        self.находки = находки
        self.процесс = subprocess.Popen(
            [ПИТОН, "-m", "vertcut", "screen", "--no-browser", "--port", str(self.порт)],
            cwd=РЕПО, env=окружение(дом, заглушки), stdout=журнал.open("w"),
            stderr=subprocess.STDOUT)
        for _ in range(200):
            м = re.search(r"(http://127\.0\.0\.1:\d+/\S*pass=(\S+))", журнал.read_text())
            if м:
                self.адрес, self.пропуск = м.group(1), м.group(2)
                return
            time.sleep(0.1)
        raise RuntimeError("vertcut screen did not start:\n" + журнал.read_text())

    def ручка(self, способ: str, имя: str, тело: dict | None = None,
              запрос: dict | None = None) -> tuple[int, dict | str, dict]:
        путь = urllib.parse.quote(f"/апи/{имя}")
        if запрос:
            путь += "?" + urllib.parse.urlencode(запрос)
        связь = http.client.HTTPConnection("127.0.0.1", self.порт, timeout=300)
        связь.request(способ, путь,
                      body=json.dumps(тело or {}).encode() if способ == "POST" else None,
                      headers={"X-Vertcut-Pass": self.пропуск,
                               "Content-Type": "application/json"})
        ответ = связь.getresponse()
        сырое = ответ.read()
        шапки = dict(ответ.getheaders())
        if "json" in шапки.get("Content-Type", ""):
            return ответ.status, json.loads(сырое), шапки
        return ответ.status, сырое[:400].decode("utf-8", "replace") \
            if шапки.get("Content-Type", "").startswith("text/") else "", шапки

    def остановить(self) -> None:
        self.процесс.send_signal(signal.SIGINT)
        try:
            self.процесс.wait(15)
        except subprocess.TimeoutExpired:
            self.процесс.kill()
        self.находки.смотреть("screen-terminal", self.журнал.read_text(),
                              "vertcut screen: вывод в терминал и журнал запуска")


# «Quit» в полосе-вопросе гасит сам сервис (27-я сессия) — щёлкнутая
# посреди обхода, она оставила бы остальным экранам мёртвую страницу.
# «Quit Vertcut» щёлкается как всё: её полоса — тоже слова для человека.
# Сам выход проходится ОДИН раз, последним. Подпись кнопки здесь —
# «ТЕГ|текст|…» (см. `КНОПКИ`), отсюда вид образца.
НЕ_ЩЁЛКАТЬ_НИКОГДА = r"^BUTTON\|Quit\|"


class Обход:
    def __init__(self, хром: Chrome, экран: Экран, находки: Находки, снимки: Path):
        self.хром, self.экран, self.находки, self.снимки = хром, экран, находки, снимки
        self.н = len(list(снимки.glob("*.png")))
        хром("Page.addScriptToEvaluateOnNewDocument", source=ПОДМЕНА + СЛУШАТЬ)
        хром("Page.navigate", url=экран.адрес)
        self.тишина()

    def тишина(self, предел: float = 30) -> None:
        """Ждать, пока страница не перестанет спрашивать сервер."""
        time.sleep(0.4)
        конец, тихо = time.time() + предел, 0
        while time.time() < конец:
            try:
                летит = self.хром.js("window.__летит || 0")
            except RuntimeError:
                летит = 1
            тихо = тихо + 1 if not летит else 0
            if тихо >= 3:
                return
            time.sleep(0.15)

    def собрать(self) -> None:
        слова = self.хром.js("[...(window.__слова || new Map()).entries()]") or []
        for ключ, хэш in слова:
            как, _, текст = ключ.partition("\u0001")
            self.находки.смотреть("screen", текст, f"{хэш or '#'} {как}")
        self.хром.js("window.__слова && window.__слова.clear()")

    def побывать(self, хэш: str, щёлкать: bool = True, вводить: bool = True,
                 нельзя: str = r"\bdelete\b", предел: int = 150) -> None:
        self.хром.js(f"location.hash = {json.dumps(хэш)}")
        self.тишина()
        self.н += 1
        self.хром.снимок(self.снимки / f"{self.н:03d}-{re.sub(r'[^a-z0-9]+', '-', хэш)}.png")
        if щёлкать:
            self.щёлкать_всё(хэш, нельзя, предел)
        if вводить:
            self.вводить_всё(хэш)
        self.собрать()

    def вернуться(self, хэш: str) -> None:
        if self.хром.js("location.hash") != хэш:
            self.хром.js(f"location.hash = {json.dumps(хэш)}")
            self.тишина()

    def щёлкать_всё(self, хэш: str, нельзя: str, предел: int) -> None:
        сделано: set[str] = set()
        for _ in range(предел):
            кнопки = self.хром.js(КНОПКИ) or []
            новые = [к for к in кнопки if к["подпись"] not in сделано
                     and not re.search(нельзя, к["подпись"], re.I)
                     and not re.search(НЕ_ЩЁЛКАТЬ_НИКОГДА, к["подпись"], re.I)]
            if not новые:
                return
            к = новые[0]
            сделано.add(к["подпись"])
            self.хром.js(f"document.querySelector('[data-sweep=\"{к['н']}\"]')?.click()")
            self.тишина()
            self.вернуться(хэш)

    def щёлкнуть(self, подпись: str) -> bool:
        """Щёлкнуть по первой видимой кнопке, в подписи которой есть это."""
        for к in self.хром.js(КНОПКИ) or []:
            if re.search(подпись, к["подпись"], re.I):
                self.хром.js(f"document.querySelector('[data-sweep=\"{к['н']}\"]')?.click()")
                self.тишина()
                return True
        return False

    def вводить_всё(self, хэш: str) -> None:
        for поле in self.хром.js(ВВОД) or []:
            где = f"document.querySelector('[data-sweep-field=\"{поле['н']}\"]')"
            if поле["тип"] == "select":
                дело = (f"(() => {{ const э = {где}; if (!э) return; "
                        "э.selectedIndex = (э.selectedIndex + 1) % э.options.length; "
                        "э.dispatchEvent(new Event('change', { bubbles: true })); })()")
            elif поле["тип"] == "range":
                дело = (f"(() => {{ const э = {где}; if (!э) return; э.value = э.max; "
                        "э.dispatchEvent(new Event('input', { bubbles: true })); "
                        "э.dispatchEvent(new Event('change', { bubbles: true })); })()")
            else:
                значение = "999" if поле["тип"] == "number" else "abc"
                дело = (f"(() => {{ const э = {где}; if (!э) return; э.focus(); "
                        f"э.value = {json.dumps(значение)}; "
                        "э.dispatchEvent(new Event('input', { bubbles: true })); "
                        "э.dispatchEvent(new Event('change', { bubbles: true })); "
                        "э.dispatchEvent(new KeyboardEvent('keydown', { key: 'Enter', bubbles: true })); "
                        "э.blur(); })()")
            self.хром.js(дело)
            self.тишина()
            self.вернуться(хэш)


def ждать_разбора(экран: Экран, слаг: str, предел: float = 300) -> dict:
    конец = time.time() + предел
    while time.time() < конец:
        _, это, _ = экран.ручка("GET", "разбор", запрос={"слаг": слаг})
        if isinstance(это, dict) and not (это.get("работа") or {}).get("идёт"):
            return это
        time.sleep(1)
    return {}


def часть_screen(дом: Path, папка: Path, находки: Находки, модель: Модель,
                 v: Команда, src: Path, ключи: list[str], части: set) -> None:
    снимки = папка / "shots"
    снимки.mkdir()
    загрузки = папка / "downloads"
    загрузки.mkdir()

    # ── Пустой дом: ни видео, ни ключа.
    пусто = папка / "empty-home"
    экран = Экран(пусто, папка / "screen-empty.log", находки, v.заглушки)
    хром = Chrome(папка / "chrome-profile", загрузки)
    try:
        о = Обход(хром, экран, находки, снимки)
        о.побывать("#videos")
        for раздел in ("ai", "folders", "shortcuts", "my-style", "samples"):
            о.побывать(f"#settings/{раздел}")
        о.побывать("#help")
        for плохой in ("#analysis/no-such-video", "#segments/no-such-video",
                       "#clip/no-such-video/0000-0001", "#subtitles/no-such-video/0000-0001",
                       "#export/no-such-video", "#descriptions/no-such-video",
                       "#analysis", "#clip", "#nonsense"):
            о.побывать(плохой, щёлкать=False, вводить=False)
    finally:
        экран.остановить()

    # ── Дом с разборами. Журнал запуска для помощи — настоящий вывод экрана.
    логи = дом / ".settings" / "logs"
    логи.mkdir(parents=True, exist_ok=True)
    экран = Экран(дом, логи / time.strftime("launch-%Y-%m-%d-%H%M%S.log"), находки,
                  v.заглушки)
    try:
        if "api" in части:
            print("· отказы ручек", flush=True)
            (v.заглушки / "cancel").touch()
            часть_api(экран, находки, src, ключи)
            (v.заглушки / "cancel").unlink()
        о = Обход(хром, экран, находки, снимки)
        # Разбор идёт: длинное видео, брошенное как с экрана.
        _, это, _ = экран.ручка("POST", "принять-путь", {"путь": str(src / "Long-Talk.mp4")})
        длинный = это["слаг"]
        экран.ручка("POST", "разобрать", {"слаг": длинный})
        о.побывать(f"#analysis/{длинный}", щёлкать=False, вводить=False)
        time.sleep(4)
        о.побывать(f"#analysis/{длинный}", щёлкать=False, вводить=False)
        о.побывать("#videos", щёлкать=False, вводить=False)
        о.побывать(f"#analysis/{длинный}", нельзя=r"\bdelete\b")   # «Stop» — тоже состояние
        экран.ручка("POST", "разобрать", {"слаг": длинный})
        ждать_разбора(экран, длинный)
        о.побывать(f"#analysis/{длинный}")
        о.побывать("#analysis/garden-notes")
        о.побывать(f"#analysis/{СЛАГ}")
        о.побывать("#videos")

        # Фрагменты: без ключа, с ключом, ответ модели, отказы поставщика.
        экран.ручка("POST", "ai-настроить", {"ключ": ""})
        о.побывать(f"#segments/{длинный}")
        экран.ручка("POST", "ai-настроить", {"ключ": "sk-ant-sweep-0000000000"})
        о.побывать(f"#segments/{длинный}")
        for режим in ("401", "429money", "500", "empty", "garbage"):
            модель.режим = режим
            о.побывать(f"#segments/{длинный}", щёлкать=False, вводить=False)
            о.щёлкнуть(r"ask ai|suggest|ask again")
            о.собрать()
        модель.режим = "ok"
        о.побывать(f"#segments/{СЛАГ}")

        # Вертикалки: собранная, устаревшая, несобранная, новая.
        v("pick", СЛАГ, "--range", "2-8")
        # Щёлкается всё у одной вертикалки каждого состояния: устаревшая,
        # собранная, разрывная, новая. Остальные — только смотрятся:
        # экран у них тот же, а обход стоит минуты.
        полно = {ключи[1], ключи[2], ключи[0]} | (set(v.ключи()) - set(ключи))
        for ключ in v.ключи():
            о.побывать(f"#clip/{СЛАГ}/{ключ}", щёлкать=ключ in полно,
                       вводить=ключ in полно)
        о.побывать(f"#subtitles/{СЛАГ}/{ключи[1]}")
        о.побывать(f"#subtitles/{СЛАГ}/{ключи[2]}")

        # Сборка: очередь ждёт, идёт, готова, упала.
        v("queue", СЛАГ, "--again")
        о.побывать(f"#export/{СЛАГ}", щёлкать=False, вводить=False)
        экран.ручка("POST", "собрать-всё", {"слаг": СЛАГ, "заново": "1"})
        о.побывать(f"#export/{СЛАГ}", щёлкать=False, вводить=False)
        time.sleep(3)
        о.побывать(f"#export/{СЛАГ}")
        стиль = дом / СЛАГ / "subtitles.yaml"
        целый = стиль.read_text()
        стиль.write_text(целый + "\n  : : [broken\n")
        экран.ручка("POST", "собрать-всё", {"слаг": СЛАГ, "заново": "1"})
        time.sleep(3)
        о.побывать(f"#export/{СЛАГ}", щёлкать=False, вводить=False)
        о.побывать(f"#clip/{СЛАГ}/{ключи[1]}", щёлкать=False, вводить=False)
        о.побывать(f"#subtitles/{СЛАГ}/{ключи[1]}", щёлкать=False, вводить=False)
        стиль.write_text(re.sub(r"(?m)^version:.*\n", "", целый))
        о.побывать(f"#subtitles/{СЛАГ}/{ключи[1]}", щёлкать=False, вводить=False)
        стиль.write_text(целый)
        о.побывать(f"#export/{СЛАГ}")

        о.побывать(f"#descriptions/{СЛАГ}")
        о.побывать(f"#descriptions/{длинный}")
        for раздел in ("ai", "folders", "shortcuts", "my-style", "samples"):
            о.побывать(f"#settings/{раздел}")
        о.побывать("#help")

        # Удаление — последним: вертикалка, потом видео целиком.
        о.побывать(f"#clip/{СЛАГ}/{ключи[0]}", нельзя=r"^$")
        о.побывать("#videos", нельзя=r"^$")

        # Выход — самым последним: после него сервиса нет. Слова
        # последнего экрана («Vertcut has stopped.») — тоже человеку.
        о.побывать("#videos", щёлкать=False, вводить=False)
        о.щёлкнуть(r"^BUTTON\|Quit Vertcut\|")
        о.щёлкнуть(r"^BUTTON\|Quit\|")
        time.sleep(1.5)
        о.собрать()
        if "Vertcut has stopped." not in (хром.js("document.body.innerText") or ""):
            находки.отметить("screen", "ПОСЛЕ «Quit» НЕТ ЭКРАНА «Vertcut has stopped.»",
                             "#videos → Quit Vertcut → Quit")
        наружу = хром.js("window.__наружу || []")
        print(f"  ссылки наружу (не открывались): {len(наружу)}")
    finally:
        экран.остановить()
        хром.закрыть()
    for файл in загрузки.iterdir():
        находки.смотреть("download", файл.name, "имя скачанного файла")


# Каждая ручка с плохими данными: её отказ человек видит полосой.
def часть_api(экран: Экран, находки: Находки, src: Path, ключи: list[str]) -> None:
    sys.path.insert(0, str(РЕПО))
    from vertcut.web import api  # noqa: E402 — список ручек, не логика
    к = ключи[1]
    плохие = [
        {},
        {"слаг": "no-such-video"},
        {"слаг": СЛАГ, "ключ": "9999-9999"},
        {"слаг": СЛАГ, "ключ": к, "план": "99", "н": "999", "фраза": "999",
         "номер": "abc", "секунда": "abc", "при": "abc", "отметка": "1:stale"},
        {"слаг": СЛАГ, "ключ": к, "путь": str(src / "missing.mp4"),
         "файл": str(src / "Morning-Walk-script.txt"), "текст": "",
         "что": {"bogus": 1}, "вид": "nope", "откуда": "nope", "имя": "nope",
         "с": "abc", "по": "abc", "куски": "abc", "отметка": "0"},
    ]
    for (способ, имя) in sorted(api.РУЧКИ):
        # «выключить» гасит сам сервис (27-я сессия): проходится одна,
        # последней, в части screen.
        if имя in ("удалить-видео", "выключить"):
            continue
        for тело in плохие:
            if имя.startswith("удалить") and тело.get("ключ") == к:
                continue
            запрос = {к_: (json.dumps(з) if isinstance(з, dict) else з)
                      for к_, з in тело.items()} if способ == "GET" else None
            try:
                код, это, шапки = экран.ручка(способ, имя, тело if способ == "POST" else None,
                                              запрос)
            except Exception as беда:          # noqa: BLE001
                находки.отметить("api", f"прочёс не дождался ответа: {беда!r}", f"{способ} {имя}")
                continue
            if isinstance(это, dict) and "беда" in это:
                находки.смотреть("api", f"{это.get('беда')}\n{это.get('подсказка') or ''}",
                                 f"{способ} /апи/{имя} {sorted(тело)}")
            elif isinstance(это, str) and код >= 400:
                находки.смотреть("api", это, f"{способ} /апи/{имя} [{код}]")
            скачать = шапки.get("Content-Disposition", "")
            if скачать:
                находки.смотреть("api", urllib.parse.unquote(скачать),
                                 f"{способ} /апи/{имя}: имя файла для скачивания")


# ─────────────────────────────────────────────────────────────────────
# Диск: что сервис написал человеку
# ─────────────────────────────────────────────────────────────────────

ТЕКСТОВЫЕ = {".json", ".txt", ".log", ".yaml", ".yml", ".md", ".srt", ".html",
             ".csv", ".err", ".sh", ".cmd"}
КАРТИНКИ = {".jpg", ".jpeg", ".png"}
# Буквы, у которых нет латинского двойника. Распознавание читает
# английское «cop» с русским словарём как «сор»; слово без этих букв
# находкой на картинке не считается.
НЕ_ДВОЙНИКИ = re.compile(r"[бвгдёжзийлмнптфцчшщъыьэюяБГДЁЖЗИЙЛПФЦЧШЩЪЫЬЭЮЯ]")

РАСПОЗНАТЬ = r"""
import Foundation
import Vision
import AppKit
for path in CommandLine.arguments.dropFirst() {
    guard let img = NSImage(contentsOfFile: path),
          let cg = img.cgImage(forProposedRect: nil, context: nil, hints: nil) else { continue }
    let req = VNRecognizeTextRequest()
    req.recognitionLevel = .accurate
    req.recognitionLanguages = ["ru-RU", "en-US"]
    req.usesLanguageCorrection = false
    try? VNImageRequestHandler(cgImage: cg).perform([req])
    for o in req.results ?? [] {
        if let t = o.topCandidates(1).first?.string { print("\(path)\t\(t)") }
    }
}
"""


def _json_насквозь(это, путь=""):
    """(где, ключ или значение, текст) для каждой строки внутри json."""
    if isinstance(это, dict):
        for к, з in это.items():
            yield путь, "key", str(к)
            yield from _json_насквозь(з, f"{путь}.{к}")
    elif isinstance(это, list):
        for з in это:
            yield from _json_насквозь(з, f"{путь}[]")
    elif isinstance(это, str):
        yield путь, "value", это


def часть_disk(корни: list[Path], находки: Находки, папка: Path) -> None:
    картинки = []
    for корень in корни:
        if not корень.exists():
            continue
        for файл in sorted(корень.rglob("*")):
            имя = файл.relative_to(корень).as_posix()
            находки.смотреть("disk-name", имя, f"имя на диске в {корень.name}/")
            if not файл.is_file():
                continue
            if файл.suffix.lower() in КАРТИНКИ:
                # Кадры планов — картинка из видео; подписи только на листах.
                if "sheet" in файл.name or файл.parent.name != "frames" or \
                        файл.name.startswith("sheet"):
                    картинки.append(файл)
                continue
            if файл.suffix.lower() not in ТЕКСТОВЫЕ or файл.stat().st_size > 4_000_000:
                continue
            текст = файл.read_text(encoding="utf-8", errors="replace")
            # Ответ модели — json по договору (`prompts.ФОРМА`), с теми же
            # русскими ключами; смотрится так же, как json.
            сырое = re.sub(r"^```(?:json)?\s*|\s*```$", "", текст.strip())
            if файл.suffix == ".json" or файл.name.endswith(".answer.txt"):
                try:
                    это = json.loads(сырое)
                except json.JSONDecodeError:
                    находки.смотреть("disk-text", текст, имя)
                    continue
                for где, как, строка in _json_насквозь(это):
                    if как == "key":
                        # Решение автора (22-я сессия): ключи json
                        # не переводятся — договор кода с кодом.
                        if РУССКОЕ.search(строка):
                            находки.известное.add(имя)
                        continue
                    # Значение-жетон (`упал`, `сценарий`, отпечаток
                    # `1:0.5:full:рука`) — тот же договор кода с кодом,
                    # что и ключ: строчные слова без знаков фразы.
                    if all(re.fullmatch(r"[а-яёa-z0-9_.:+\-]+", с) for с in строка.split()):
                        if РУССКОЕ.search(строка):
                            находки.известное.add(имя)
                        continue
                    находки.смотреть("disk-json-value", строка, f"{имя} {где}")
            else:
                находки.смотреть("disk-text", текст, имя)
    распознать(картинки, находки, папка)


def распознать(картинки: list[Path], находки: Находки, папка: Path) -> None:
    """Подписи на листах — встроенным распознаванием текста macOS."""
    if not картинки:
        return
    исходник = папка / "ocr.swift"
    исходник.write_text(РАСПОЗНАТЬ)
    программа = папка / "ocr"
    if subprocess.run(["swiftc", "-O", "-o", программа, исходник],
                      capture_output=True).returncode != 0:
        находки.отметить("disk-image", "не собралось распознавание текста — "
                         "листы надо смотреть глазами", "swiftc")
        return
    print(f"  распознаю подписи на {len(картинки)} картинках", flush=True)
    вышло = subprocess.run([программа, *map(str, картинки)], capture_output=True,
                           text=True, timeout=1800).stdout
    for строка in вышло.splitlines():
        путь, _, текст = строка.partition("\t")
        if any(НЕ_ДВОЙНИКИ.search(слово) and len(РУССКОЕ.findall(слово)) >= 2
               for слово in текст.split()):
            находки.смотреть("disk-image", текст, Path(путь).name)


# ─────────────────────────────────────────────────────────────────────
# Установка и раздача
# ─────────────────────────────────────────────────────────────────────

def _модуль(путь: Path, имя: str):
    import importlib.util
    спец = importlib.util.spec_from_file_location(имя, путь)
    модуль = importlib.util.module_from_spec(спец)
    sys.modules[имя] = модуль
    спец.loader.exec_module(модуль)
    return модуль


def _страница_в_хроме(хром: Chrome, адрес: str, находки: Находки, где: str,
                      ждать: float = 1.0) -> None:
    хром("Page.navigate", url=адрес)
    time.sleep(ждать)
    for ключ, _ in хром.js("[...(window.__слова || new Map()).entries()]") or []:
        как, _, текст = ключ.partition("\u0001")
        находки.смотреть(где, текст, как)


def часть_install(папка: Path, находки: Находки) -> None:
    установка = РЕПО / "install"
    sys.path.insert(0, str(установка))
    ход = _модуль(установка / "progress.py", "progress")
    ставит = _модуль(установка / "installer.py", "installer")
    сборщик = _модуль(установка / "build-release.py", "build_release")
    показ = папка / "install-pages"
    показ.mkdir()
    хром = Chrome(папка / "chrome-install", папка)
    хром("Page.addScriptToEvaluateOnNewDocument", source=СЛУШАТЬ)
    try:
        # Страница хода — живая, как у человека: свой сервер, опрос
        # состояния, каждый шаг по очереди, отказ, «готово».
        шаги = ставит.STEPS
        живая = ход.Progress(показ, шаги, live=True)
        хром("Page.navigate", url=живая.address())
        time.sleep(1.5)
        for н in range(len(шаги)):
            живая.start(н, "usually half a minute")
            живая.update(н, "ffmpeg: 6 of 23 MB", fraction=0.25)
            time.sleep(1.2)
            живая.done(н, "done")
        # Отказы установщика — настоящими словами `download`.
        беды = []
        сервер = ThreadingHTTPServer(("127.0.0.1", 0), type("Р", (BaseHTTPRequestHandler,), {
            "log_message": lambda *_: None,
            "do_GET": lambda с: (с.send_response(200 if с.path == "/file" else 404),
                                 с.send_header("Content-Length", "5" if с.path == "/file" else "0"),
                                 с.end_headers(), с.path == "/file" and с.wfile.write(b"hello"))}))
        threading.Thread(target=сервер.serve_forever, daemon=True).start()
        порт = сервер.server_address[1]
        for адрес, сумма in ((f"http://127.0.0.1:{порт}/gone", ""),
                             (f"http://127.0.0.1:{порт}/file", "0" * 64),
                             ("http://127.0.0.1:9/nothing", "")):
            try:
                ставит.download(адрес, показ / "dl.bin", сумма)
            except ставит.InstallProblem as б:
                беды.append(б)
        сервер.shutdown()
        for б in беды:
            живая.fail(2, б.what, б.hint)
            time.sleep(1.2)
            _страница_в_хроме(хром, живая.address(), находки, "install-page")
        живая.finish()
        time.sleep(1.5)
        _страница_в_хроме(хром, живая.address(), находки, "install-page")
        # Установщик замолчал: через сорок промахов страница говорит своё.
        живая2 = ход.Progress(показ, шаги, live=True)
        живая2.start(1)
        хром("Page.navigate", url=живая2.address())
        time.sleep(1.5)
        живая2.server.shutdown()
        живая2.server.server_close()
        time.sleep(40)
        _страница_в_хроме(хром, "about:blank", находки, "install-page", ждать=0.2)
        # «Vertcut didn't start» и «Done» — как их зовёт ярлык.
        журнал = показ / "launch-test.log"
        журнал.write_text("Starting Vertcut\nTraceback: ValueError: bad thing\n")
        for доводы in (["--title", "Vertcut didn't start", "--hint", "Below are the last lines of the log.",
                        "--problem", "exit code 1", "--log-tail", str(журнал), "--wait", "0"],
                       ["--go-to", "http://127.0.0.1:9/", "--wait", "0"]):
            subprocess.run([sys.executable, установка / "progress.py", "--page-dir", показ, *доводы],
                           capture_output=True, timeout=60)
            текст = (показ / "progress.html").read_text()
            if "--go-to" in доводы:
                текст = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", текст, flags=re.S)
                находки.смотреть("install-page", re.sub(r"<[^>]+>", " ", текст), "progress.py --go-to")
            else:
                _страница_в_хроме(хром, (показ / "progress.html").as_uri(), находки,
                                  "install-page")
        # README.html обеих систем.
        for система in ("darwin", "windows"):
            файл = показ / f"README-{система}.html"
            файл.write_text(сборщик.страница(система), encoding="utf-8")
            _страница_в_хроме(хром, файл.as_uri(), находки, f"readme-{система}")
    finally:
        хром.закрыть()

    # Окно Vertcut.exe: показать его здесь нечем, строки — из исходника.
    for м in re.finditer(r'@?"((?:[^"\\]|\\.)*)"', (установка / "launcher.cs").read_text()):
        находки.смотреть("launcher.exe", м.group(1), "строка в launcher.cs")

    # Архивы: имена — как их прочтёт чужая машина; содержимое того,
    # что лежит на виду и написано для человека.
    сборщик_иконки = сборщик.сборщик_иконки()
    сборщик.сборщик_иконки = lambda: сборщик_иконки
    for система in ("darwin", "windows"):
        куда = папка / f"release-{система}"
        куда.mkdir()
        if система == "windows":
            # Компилятора C# здесь нет — exe подменяется пустышкой, всё
            # остальное собирается тем же кодом, что на сборочной машине.
            сборщик_иконки.собрать_exe = lambda путь: путь.write_bytes(b"MZ")
        раздача = сборщик.собрать(куда, система)
        архив = сборщик.упаковать(раздача, система)
        for имя in сборщик.имена_в_архиве(архив):
            находки.смотреть(f"archive-{система}", имя, "имя в архиве")
            if any(ord(з) > 127 for з in имя):
                находки.отметить(f"archive-{система}", f"не латиница: {имя!r}", "имя в архиве")
        with zipfile.ZipFile(архив) as z:
            for имя in z.namelist():
                путь = Path(имя)
                на_виду = (len(путь.parts) <= 2 or путь.parts[1] == "Licenses"
                           or путь.name == "Vertcut.cmd")
                if на_виду and путь.suffix.lower() in ТЕКСТОВЫЕ | {""} \
                        and not имя.endswith("/"):
                    текст = z.read(имя).decode("utf-8", "replace")
                    if путь.suffix == ".html":
                        текст = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", текст, flags=re.S)
                        текст = re.sub(r"<[^>]+>", " ", текст)
                    находки.смотреть(f"archive-{система}", текст, имя)


def main() -> int:
    разбор = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    разбор.add_argument("--keep", action="store_true")
    разбор.add_argument("--only", default="cli,screen,api,disk,install")
    доводы = разбор.parse_args()
    части = set(доводы.only.split(","))

    корень = Path(tempfile.mkdtemp(prefix="vertcut-sweep-"))
    дом = корень / "home"
    находки = Находки([str(РЕПО), str(корень), str(корень.resolve()),
                       str(Path.home())])
    находки.журнал = (корень / "seen.jsonl").open("w")
    print(f"песочница: {корень}", flush=True)
    модель = Модель()
    начали = time.time()
    try:
        if части & {"cli", "screen", "api", "disk"}:
            п = песочница(корень)
            v = Команда(дом, находки, корень / "cli.txt", п["заглушки"])
            # Команда идёт всегда, когда нужен дом: она же строит
            # состояния, которые потом покажут экран и диск.
            print("· команда", flush=True)
            ключи = часть_cli(v, п["src"], модель)["ключи"]
            if части & {"screen", "api"}:
                print("· экран", flush=True)
                часть_screen(дом, корень, находки, модель, v, п["src"], ключи, части)
            if "disk" in части:
                print("· диск", flush=True)
                часть_disk([дом, корень / "empty-home", корень / "downloads"],
                           находки, корень)
            окна = (п["заглушки"] / "calls.log")
            if окна.exists():
                print(f"  окон на столе открылось бы: {len(окна.read_text().splitlines())}"
                      " — их открыли заглушки, а не система", flush=True)
        if "install" in части:
            print("· установка и раздача", flush=True)
            часть_install(корень, находки)
    finally:
        модель.сервер.shutdown()
        if not доводы.keep:
            shutil.rmtree(корень, ignore_errors=True)
    print(f"\nпрочёс шёл {(time.time() - начали) / 60:.0f} мин", flush=True)
    return находки.печать()


if __name__ == "__main__":
    sys.exit(main())
