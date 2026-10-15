"""Собрать то, что отдают человеку: архив с README и иконкой.

    python install/build-release.py                 — под эту систему
    python install/build-release.py --system windows
    python install/build-release.py --out ...

## Чем это отличается от `build-launcher.py`

Тот собирает ИКОНКУ — три мегабайта, которые человек запускает.
Этот собирает РАЗДАЧУ: иконку плюс то, без чего чужой человек
не поймёт, что ему прислали.

    Vertcut/                     macOS            Windows
      README.html                что это и как запустить
      Vertcut.app / Vertcut.exe  то, что нажимают
      If-Vertcut-does-not-open.sh  запасная дорога  —
      install/                   —                установка и поставка
      Licenses/                  лицензии: своя и чужие

**Наверху то, что читать, и то, что нажимать.** Кнопка, которую
человек не знает зачем нажимать, хуже её отсутствия.

## Почему исходного кода здесь больше НЕТ

Он лежал папкой «Техническое/Исходный код» — весь репозиторий копией.
Это уехало на Windows и обернулось бедой, которой не ждали: человек
распаковал архив и увидел россыпь `.py` и `.sh` с мусором вместо
имён. Он прочитал это как «мне прислали исходники» — и был прав,
потому что запускать ему было нечего.

Теперь код раздаётся с GitHub, одной ссылкой, и она стоит в README.
Копия кода в архиве устаревала бы молча: собранная сегодня раздача
несла бы вчерашний код, и разошлись бы они без единого слова.

**Лицензии при этом остаются, и это обязательство, а не вежливость.**
MIT велит носить с собой имя и отказ от гарантий; шрифты под OFL
несут свои файлы внутри поставки.

## Почему архив собирается КОДОМ, а не мышью в Finder

Старый формат архива хранит имена в кодировке времён DOS, а отметку
«здесь utf-8» Finder не ставит. Чужая машина читает такие имена
своей привычкой — и каждая русская буква превращается в два знака.
Ровно это и случилось: человек на Windows получил список файлов,
в котором нельзя прочесть ни одного имени.

**Отсюда два заслона, а не один.** Архив собирается кодом — и в нём
нет ни одного имени вне латиницы: проверка распаковкой читает имена
и краснеет на первом же русском. Второй заслон нужен потому, что
первый чинит только НАШ архив, а пересылать его будут чем угодно.

## Почему macOS пакуется `ditto`, а Windows — `zipfile`

Иконка на macOS — это папка `Vertcut.app`, а внутри неё исполняемый
файл, две ссылки и подпись. Питоновский `zipfile` не хранит ни прав,
ни ссылок: распакованное им приложение не запускается вовсе, Finder
говорит, что оно повреждено.

На Windows ссылок нет, прав нет, подписи нет — и `ditto` там нет тоже.
Виндовая раздача собирается на виндовой машине, и собирать её нечем,
кроме стандартной библиотеки. Она же ставит отметку «utf-8» сама.

**Проверка распаковкой входит в сборку.** Архив, который никто
не распаковал, — это обещание, а не раздача.

**Подпись проверяется именно у РАСПАКОВАННОГО.** Своя подпись стоит
на свёртке (зачем она — в `build-launcher.py`), но вопрос здесь
другой: доехала ли она до чужого человека. Ломается она молча — от
лишнего файла внутри, от упаковщика, который не хранит прав и ссылок,
— а сломанная подпись для системы то же самое, что её отсутствие:
«программа повреждена» и Корзина.
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import codecs
import sys
import tempfile
import zipfile
from pathlib import Path

ЗДЕСЬ = Path(__file__).resolve().parent
КОРЕНЬ = ЗДЕСЬ.parent
sys.path.insert(0, str(ЗДЕСЬ))

# Где лежит код. Одним местом: этот адрес печатает README раздачи,
# README репозитория и страница помощи — разъедутся, и человек пойдёт
# искать то, чего нет.
АДРЕС_ПРОЕКТА = "https://github.com/eduard1414ed/vertcut"

# Как файл спасения зовётся в раздаче.
#
# **Словами беды, а не работы**: человек ищет файл именно ими. До 23-й
# сессии это были русские слова латиницей (`Esli-ne-otkryvaetsya.sh`) —
# русское имя не переживает чужого распаковщика. Теперь слова английские,
# как всё, что видит человек, и латиница у них своя. Без апострофа
# («won't»): кавычка в имени файла ломает его перетаскивание в Терминал
# у тех, кто потом допишет что-то руками.
СПАСЕНИЕ = "If-Vertcut-does-not-open.sh"

# Лицензии. Своя — MIT, чужие — списком с версиями.
ЛИЦЕНЗИИ = ["LICENSE", "LICENSES.md"]


def версия() -> str:
    for строка in (КОРЕНЬ / "pyproject.toml").read_text(
            encoding="utf-8").splitlines():
        if строка.startswith("version"):
            return строка.split("=")[1].strip().strip('"')
    return "0.0.0"


def сборщик_иконки():
    """Иконку собирает тот же файл, что и всегда. Второго способа
    собрать её не заводится."""
    import importlib.util

    спец = importlib.util.spec_from_file_location(
        "ярлык_сборщик", ЗДЕСЬ / "build-launcher.py")
    модуль = importlib.util.module_from_spec(спец)
    спец.loader.exec_module(модуль)
    return модуль


def собрать(куда: Path, система: str) -> Path:
    """Папка раздачи. Возвращает её путь."""
    сборщик = сборщик_иконки()
    раздача = куда / "Vertcut"
    shutil.rmtree(раздача, ignore_errors=True)

    if система == "windows":
        # Виндовая «иконка» — это папка с `Vertcut.exe` внутри, и она
        # же корень раздачи: класть папку в папку с тем же именем
        # значило бы заставить человека войти дважды.
        раздача = сборщик.виндовый(куда)
    else:
        раздача.mkdir(parents=True)
        сборщик.маковский(раздача)
        # Запасная дорога — только на macOS: она снимает метку
        # «скачано из интернета», а такой метки в Windows нет вовсе.
        спасение = раздача / СПАСЕНИЕ
        shutil.copy2(ЗДЕСЬ / "unquarantine.sh", спасение)
        спасение.chmod(0o755)

    (раздача / "README.html").write_text(страница(система), encoding="utf-8")

    лицензии = раздача / "Licenses"
    лицензии.mkdir()
    for имя in ЛИЦЕНЗИИ:
        shutil.copy2(КОРЕНЬ / имя, лицензии / имя)
    return раздача


def упаковать(раздача: Path, система: str) -> Path:
    """Архив рядом с папкой."""
    архив = раздача.parent / f"Vertcut-{'windows' if система == 'windows' else 'mac'}.zip"
    архив.unlink(missing_ok=True)
    if система == "windows":
        # Стандартная библиотека: ссылок и прав здесь нет, а собирается
        # это на виндовой машине, где `ditto` не существует.
        with zipfile.ZipFile(архив, "w", zipfile.ZIP_DEFLATED) as z:
            for файл in sorted(раздача.rglob("*")):
                if файл.is_file():
                    z.write(файл, Path("Vertcut") / файл.relative_to(раздача))
    else:
        subprocess.run(["ditto", "-c", "-k", "--sequesterRsrc", "--keepParent",
                        str(раздача), str(архив)], check=True)
    return архив


def имена_в_архиве(архив: Path) -> list[str]:
    """Имена так, как их прочтёт чужая машина.

    Когда отметки «utf-8» нет, читатель разбирает имя своей привычкой
    — и русские буквы рассыпаются. Здесь этот же разбор и делается:
    смотреть надо на то, что УВИДИТ человек, а не на то, что мы
    записали.
    """
    with zipfile.ZipFile(архив) as z:
        return [и.orig_filename for и in z.infolist()]


def проверить(архив: Path, система: str) -> list[str]:
    """Распаковать и посмотреть, живо ли то, что нельзя потерять."""
    беды = []

    # ── имена ────────────────────────────────────────────────────────
    #
    # Первое, что видит человек, открыв архив. Мусор вместо имён
    # читается как «мне прислали сломанное», и дальше он не пойдёт.
    for имя in имена_в_архиве(архив):
        if any(ord(з) > 127 for з in имя):
            беды.append(
                f"a name in the archive isn't plain Latin — another "
                f"computer will show it as garbage: {имя!r}")
            break

    врем = Path(tempfile.mkdtemp(prefix="vertcut-probe-"))
    try:
        if система == "windows":
            with zipfile.ZipFile(архив) as z:
                z.extractall(врем)
        else:
            subprocess.run(["ditto", "-x", "-k", str(архив), str(врем)],
                           check=True)
        корень = врем / "Vertcut"
        if not (корень / "README.html").exists():
            беды.append("no README.html")
        for имя in ЛИЦЕНЗИИ:
            if not (корень / "Licenses" / имя).exists():
                беды.append(f"missing license: {имя}")

        if система == "windows":
            беды += виндовые_беды(корень)
        else:
            беды += маковские_беды(корень)
    finally:
        shutil.rmtree(врем, ignore_errors=True)
    return беды


def маковские_беды(корень: Path) -> list[str]:
    беды = []
    пуск = корень / "Vertcut.app" / "Contents" / "MacOS" / "Vertcut"
    ссылка = корень / "Vertcut.app" / "Contents" / "MacOS" / "install"
    if not пуск.exists():
        беды.append("the app has no executable")
    elif not пуск.stat().st_mode & 0o111:
        беды.append("the app's executable isn't executable — macOS "
                    "will say the app is damaged")
    if not ссылка.is_symlink():
        беды.append("the link to the installer didn't survive")
    elif not (ссылка / "installer.py").exists():
        беды.append("the link to the installer leads nowhere")
    elif not (ссылка / "constraints.txt").exists():
        беды.append("no constraints.txt — the installer wouldn't know "
                    "which library versions to install")
    if not list((корень / "Vertcut.app" / "Contents"
                 / "Resources").glob("*.whl")):
        беды.append("no Vertcut package — nothing to install")
    спасение = корень / СПАСЕНИЕ
    if not спасение.exists():
        беды.append("no backup way — someone macOS won't let in has "
                    "nothing to help themselves with")
    elif not спасение.stat().st_mode & 0o111:
        беды.append("the backup way isn't executable")
    приложение = корень / "Vertcut.app"
    if приложение.exists():
        подпись = subprocess.run(
            ["codesign", "--verify", "--deep", "--strict", str(приложение)],
            capture_output=True, text=True)
        if подпись.returncode != 0:
            беды.append(
                "the signature didn't survive the archive — macOS will "
                f"say the app is damaged: {подпись.stderr.strip()}")
    return беды


def виндовые_беды(корень: Path) -> list[str]:
    """Что проверяется у виндовой раздачи, и почему именно это.

    Запустить её здесь нельзя — Windows-машины у сессии нет. Поэтому
    проверяется то, что проверяется без запуска, и каждая строка
    стоит за настоящей бедой, а не за красотой.
    """
    беды = []
    # **Нажимают exe, и он обязан быть настоящей программой.** Первые
    # два байта всякой программы Windows — «MZ»; пустой файл или
    # страница с отказом, скачанная вместо него, этой проверки
    # не пройдут.
    exe = корень / "Vertcut.exe"
    if not exe.exists():
        беды.append("no Vertcut.exe — nothing to double-click")
    elif exe.read_bytes()[:2] != b"MZ":
        беды.append("Vertcut.exe isn't a program — Windows won't run it")

    # Запасная дорога — на случай, когда exe не пустит антивирус.
    пуск = корень / "install" / "Vertcut.cmd"
    if not пуск.exists():
        беды.append("no install/Vertcut.cmd — no backup way")
    else:
        беды += беды_командного_файла(пуск.read_bytes())

    обвес = корень / "install"
    for имя in ("installer.py", "install.ps1", "launcher.ps1",
                "sources.txt", "progress.py", "constraints.txt"):
        if not (обвес / имя).exists():
            беды.append(f"no {имя} — nothing to install with")
    if not list(обвес.glob("*.whl")):
        беды.append("no Vertcut package — nothing to install")

    # **Метка utf-8 у скриптов PowerShell — наоборот, обязательна.**
    # Windows PowerShell (тот, что стоит на всякой машине) без неё
    # читает файл старой кодировкой. Русских слов для человека там
    # с 23-й сессии нет, но остались тире и стрелки в тексте страницы
    # и примечания — а путь к дому человека бывает русским всегда.
    for имя in ("install.ps1", "launcher.ps1"):
        файл = обвес / имя
        if файл.exists() and файл.read_bytes()[:3] != b"\xef\xbb\xbf":
            беды.append(f"{имя} has no utf-8 mark — PowerShell will "
                        "read anything beyond plain Latin as garbage")
    return беды


def беды_командного_файла(байты: bytes) -> list[str]:
    беды = []
    # **Метка utf-8 в начале.** `cmd.exe` её не понимает и пытается
    # выполнить как команду: окно мигает, не запускается ничего.
    if байты[:3] == b"\xef\xbb\xbf":
        беды.append("Vertcut.cmd starts with a utf-8 mark — cmd.exe "
                    "reads it as a command and runs nothing")
    # **Только латиница.** Командный файл читается в кодировке времён
    # DOS, и русский путь внутри него не находится никогда.
    if any(б > 127 for б in байты):
        беды.append("Vertcut.cmd has non-Latin characters — cmd.exe "
                    "reads it in an old encoding and won't find the path")
    if b"\r\n" not in байты:
        беды.append("Vertcut.cmd has no Windows line endings")
    return беды


def страница(система: str) -> str:
    """README раздачи. Он отвечает на вопрос «я скачал архив, что мне
    делать», а не «что это за проект» — на второй отвечает README.md.

    Цвета записаны числами по той же причине, по которой они записаны
    числами на странице хода: показывается она ДО того, как поставка
    появилась, и брать их из `tokens.css` неоткуда.

    **Подстановки и классы — латиницей.** Это страница целиком для
    человека, её открывают и в редакторе; русских имён в ней нет вовсе,
    и храповик английского это сторожит без исключений.
    """
    окна = система == "windows"
    return (ЧИТАТЬ.replace("@STEPS@", ШАГИ_WINDOWS if окна else ШАГИ_MAC)
                  .replace("@RESCUE_BLOCK@", "" if окна else СПАСЕНИЕ_БЛОК)
                  .replace("@ADD@", ДОБАВИТЬ_WINDOWS if окна else ДОБАВИТЬ_MAC)
                  .replace("@INSIDE@", ВНУТРИ_WINDOWS if окна else ВНУТРИ_MAC)
                  .replace("@PLACES@", МЕСТА_WINDOWS if окна else МЕСТА_MAC)
                  .replace("@RESCUE@", СПАСЕНИЕ)
                  .replace("@ADDRESS@", АДРЕС_ПРОЕКТА)
                  .replace("@VERSION@", версия()))


# Названия кнопок и разделов системы — слово в слово, как их видит
# человек с английской системой (`docs/glossary.md`, «Установка, ярлык,
# раздача»). Что из этого проверено глазами, а что нет, — в
# `private/docs/sessions.md`, сессия 23.
#
# **«Так она говорит про всё, что не куплено у неё за деньги» — это
# было неточно.** Платят не за программу, а за проверку: Apple берёт
# 99 долларов в год за участие в программе разработчиков, Windows
# узнаёт издателя по купленному сертификату. Сказано теперь так.
#
# **Launchpad в macOS 26 нет**, и путь «Launchpad → Другие → Терминал»
# вёл в никуда. Терминал открывается поиском — так он находится
# на любой версии.
#
# **Кнопка «Open Anyway» живёт около часа** после попытки открыть
# программу — так пишет Apple. Человек, который открыл настройки
# назавтра, кнопки не найдёт; поэтому сказано «сразу после».
ШАГИ_MAC = """
<div class="step"><div class="n">1</div><div>
  <b>Unzip the archive</b> — anywhere, Downloads is fine.
</div></div>

<div class="step"><div class="n">2</div><div>
  <b>Double-click <code>Vertcut</code></b> in the unzipped folder.
</div></div>

<div class="step"><div class="n">3</div><div>
  <b>The first time, macOS won't open it.</b> It says
  <b>"Vertcut" Not Opened</b>: Apple couldn't check it for malware.
  macOS says this about every app whose developer hasn't paid Apple
  for that check — it isn't about a virus. Click <b>Done</b>.
  Right after that, open <b>System Settings → Privacy &amp; Security</b>
  and scroll down: there's a line about Vertcut and an
  <b>Open Anyway</b> button. Click it and confirm with your password
  or Touch ID. You only do this once.
  <p class="quiet" style="margin:6px 0 0">The button stays there for
  about an hour after you tried to open Vertcut — if it's gone,
  double-click <code>Vertcut</code> again first. Still no button? Download the archive again and unzip
  it with a double-click, not with another app. If that doesn't help
  either, there's a backup way below.</p>
</div></div>

<div class="step"><div class="n">4</div><div>
  <b>A page opens showing the install progress.</b> Vertcut needs to
  download what you don't have yet: Python, ffmpeg and the speech
  recognition model. That's about 800 MB and a few minutes. After
  that it works offline — only the AI buttons need the internet.
</div></div>

<div class="step"><div class="n">5</div><div>
  <b>When it's done, the same page opens Vertcut</b>, and a
  <code>Vertcut</code> icon appears on your Desktop — use that one
  from now on. You can delete the unzipped folder.
</div></div>

<div class="card">
<b>The second time and every time after, it just opens Vertcut.</b>
Nothing is installed again: a double-click on the icon starts Vertcut
and opens a tab in your browser.
</div>
"""

# **Windows: «Unblock» — дорога без вопросов вовсе.** Отметку «скачано
# из интернета» Windows ставит архиву, а «Извлечь все» переносит её на
# каждый файл; сняв её с архива до распаковки, человек не увидит окна
# SmartScreen совсем. Это необязательно и сказано мелко.
#
# **«Защитник» убрал exe — запасная дорога `install\Vertcut.cmd`**: она
# зовёт тот же `launcher.ps1`, что и exe, и второго способа поднять
# сервис не заводит. Спросит ли Windows и про неё — не проверено;
# сказано осторожно: «если спросит — тем же способом».
ШАГИ_WINDOWS = """
<div class="step"><div class="n">1</div><div>
  <b>Unzip the archive</b> — anywhere, Downloads is fine:
  right-click it → <b>Extract All</b>.
</div></div>

<div class="step"><div class="n">2</div><div>
  <b>Open the <code>Vertcut</code> folder and double-click
  <code>Vertcut</code></b> inside it — that's the app,
  <code>Vertcut.exe</code>. Don't move it out of the folder: it only
  works next to the <code>install</code> folder.
</div></div>

<div class="step"><div class="n">3</div><div>
  <b>The first time, Windows says it protected your PC</b> — a blue
  window, <b>Windows protected your PC</b>. Windows says this about
  every app that isn't signed with a paid certificate — it isn't about
  a virus. Click <b>More info</b>, then <b>Run anyway</b>. You only do
  this once.
  <p class="quiet" style="margin:6px 0 0">You can skip this window
  altogether: before unzipping, right-click the archive →
  <b>Properties</b> → tick <b>Unblock</b> → <b>OK</b>.</p>
  <p class="quiet" style="margin:6px 0 0">If <code>Vertcut</code>
  doesn't start at all, or Microsoft Defender removed it, open the
  <code>install</code> folder: there's <code>Vertcut.cmd</code> in it.
  It does exactly the same thing — double-click it too. If Windows
  asks about it, answer the same way: <b>More info</b> →
  <b>Run anyway</b>.</p>
</div></div>

<div class="step"><div class="n">4</div><div>
  <b>A page opens showing the install progress.</b> Vertcut needs to
  download what you don't have yet: Python, ffmpeg and the speech
  recognition model. That's about 800 MB and a few minutes. After
  that it works offline — only the AI buttons need the internet.
</div></div>

<div class="step"><div class="n">5</div><div>
  <b>When it's done, the same page opens Vertcut</b>, and a
  <code>Vertcut</code> folder appears on your Desktop — start Vertcut
  from there from now on (<code>Vertcut.exe</code> inside). You can
  delete the unzipped one.
</div></div>

<div class="card">
<b>The second time and every time after, it just opens Vertcut.</b>
Nothing is installed again: a double-click starts Vertcut and opens
a tab in your browser.
</div>
"""

# Терминал открывается поиском, а не через Launchpad: в macOS 26 его нет.
# Клавиша на маковской клавиатуре подписана «return», а не «Enter».
СПАСЕНИЕ_БЛОК = """
<h2>The backup way, if macOS still won't open it</h2>

<p>Next to this page there's a file called <code>@RESCUE@</code>.
It removes the "downloaded from the internet" mark from Vertcut — the
mark that makes macOS ask for permission. It does nothing else: it
doesn't install or download anything.</p>

<div class="card">
<p style="margin:0 0 8px"><b>What to do:</b></p>
<ol style="margin:0; padding-left:20px">
  <li>Open <b>Terminal</b>: press <b>⌘ Space</b>, type
      <code>Terminal</code> and press <b>Return</b>.</li>
  <li>Type <code>bash</code> and a space after it.</li>
  <li><b>Drag</b> the file <code>@RESCUE@</code> into the Terminal
      window — its path is filled in for you.</li>
  <li>Press <b>Return</b>. It answers "Done."</li>
</ol>
<p class="quiet" style="margin:12px 0 0">Then close Terminal and open
<code>Vertcut</code> with a double-click, as usual. You won't need
this file again.</p>
</div>

<p class="quiet">This file doesn't run with a double-click, and that's
not an oversight: macOS checks everything you open from Finder before
it can take its first step. It only works when you run it yourself,
from Terminal.</p>
"""

# «Choose file» есть только на macOS: на Windows системного диалога
# выбора нет (TODO.md), и обещать его там нельзя.
ДОБАВИТЬ_MAC = """<b>Add a video</b> — drag the file into the browser
      window, or click <b>Choose file</b>."""

ДОБАВИТЬ_WINDOWS = """<b>Add a video</b> — drag the file into the browser
      window."""

ВНУТРИ_MAC = """<ul>
  <li><code>Vertcut</code> — the app you open.</li>
  <li><code>@RESCUE@</code> — the backup way described above. Most
      people won't need it.</li>
  <li><code>Licenses/</code> — the license of Vertcut and of everything
      it's built from.</li>
</ul>"""

ВНУТРИ_WINDOWS = """<ul>
  <li><code>Vertcut</code> — the app you open.</li>
  <li><code>install/</code> — what installs it, and Vertcut itself.
      No need to touch it. <code>Vertcut.cmd</code> is in there too —
      the backup way if <code>Vertcut</code> doesn't start.</li>
  <li><code>Licenses/</code> — the license of Vertcut and of everything
      it's built from.</li>
</ul>"""

МЕСТА_MAC = """<p class="path">~/vertcut/</p>
<p class="quiet" style="margin:0 0 12px">Your work: analyzed videos
and exported clips. Nothing ever touches them.</p>
<p class="path">~/.vertcut/</p>
<p class="quiet" style="margin:0 0 12px">Settings: subtitle style,
API key, logs. They survive a reinstall.</p>
<p class="path">~/Library/Application Support/vertcut/</p>
<p class="quiet" style="margin:0">The app itself. Delete this folder
and the icon, and Vertcut is gone — nothing else.</p>"""

МЕСТА_WINDOWS = """<p class="path">%USERPROFILE%\\vertcut\\</p>
<p class="quiet" style="margin:0 0 12px">Your work: analyzed videos
and exported clips. Nothing ever touches them.</p>
<p class="path">%USERPROFILE%\\.vertcut\\</p>
<p class="quiet" style="margin:0 0 12px">Settings: subtitle style,
API key, logs. They survive a reinstall.</p>
<p class="path">%LOCALAPPDATA%\\vertcut\\</p>
<p class="quiet" style="margin:0">The app itself. Delete this folder
and the Vertcut folder on your Desktop, and Vertcut is gone — nothing
else.</p>"""


# Страница «читать первым». Своя, а не README.md, переложенный
# в разметку: тот отвечает на вопрос «что это за проект», а этот —
# на вопрос «я скачал архив, что мне делать».
#
# Что русский текст обещал неверно и как сказано теперь:
# - «ничего никуда не отправляет» — а две кнопки с моделью отправляют
#   расшифровку поставщику; сказано, что уходит только с ними;
# - «ролики режутся мгновенно» — сборка идёт 10–50 с; сказано «быстро»;
# - «девять минут на двадцать минут видео» — замер на маке автора;
#   так и сказано;
# - «ничего личного в журнале нет» — в нём видны имена папок и файлов
#   (решение 21-й сессии, экран помощи говорит то же самое).
ЧИТАТЬ = """<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Vertcut — what it is and how to start</title>
<style>
  :root { color-scheme: light dark; }
  body { margin:0; background:#FBFBFA; color:#191919; padding:48px 24px;
         font:16px/1.6 -apple-system, system-ui, "Segoe UI", sans-serif; }
  @media (prefers-color-scheme: dark) {
    body { background:#1A1A18; color:#F0EFEC; }
    .step b { color:#F0EFEC; }
    code, .path { color:#B9B9B4; }
    .card { background:#232320; }
  }
  .sheet { max-width:640px; margin:0 auto; }
  h1 { font-size:32px; line-height:1.2; margin:0 0 8px; }
  h2 { font-size:20px; margin:36px 0 10px; }
  p, li { margin:0 0 12px; }
  ul { padding-left:20px; }
  .lead { font-size:18px; color:#6B6B6B; margin-bottom:28px; }
  @media (prefers-color-scheme: dark) { .lead { color:#A5A59F; } }
  .step { display:flex; gap:14px; margin:0 0 18px; }
  .step .n { flex:none; width:26px; height:26px; border-radius:50%;
             background:#191919; color:#FBFBFA; font-size:14px;
             display:flex; align-items:center; justify-content:center; }
  @media (prefers-color-scheme: dark) {
    .step .n { background:#F0EFEC; color:#1A1A18; } }
  .card { background:#F2F1EE; border-radius:12px; padding:16px 18px;
          margin:18px 0; }
  code, .path { font:14px ui-monospace, Menlo, Consolas, monospace;
                color:#6B6B6B; }
  .quiet { color:#6B6B6B; font-size:14px; }
  @media (prefers-color-scheme: dark) { .quiet { color:#A5A59F; } }
  a { color:inherit; }
</style></head><body><div class="sheet">

<h1>Vertcut</h1>
<p class="lead">Cuts long videos into vertical clips with subtitles.
It runs on your computer, needs no account and costs nothing. Nothing
leaves your computer unless you use the optional AI buttons.</p>

<p>Add a podcast, an interview or a lecture, pick a segment, and get
a finished 1080×1920 clip with subtitles, ready to upload. You don't
need a script: Vertcut transcribes the speech into words and phrases,
finds the cuts and frames each shot around the speaker's face.</p>

<h2>How to start</h2>
@STEPS@
@RESCUE_BLOCK@
<h2>Then, in Vertcut</h2>
<ul>
  <li>@ADD@</li>
  <li><b>Wait for the analysis.</b> This is the longest part: about
      nine minutes for twenty minutes of video on a recent Mac. It
      happens once per video; after that, making clips is quick.</li>
  <li><b>Pick a segment</b> — click the phrase where it starts and the
      phrase where it ends.</li>
  <li><b>Adjust it if you like:</b> the crop, the subtitle text, the
      style.</li>
  <li><b>Export</b> — and take the finished file.</li>
</ul>

<h2>If something doesn't work</h2>
<p>In Vertcut, at the bottom of the left column, there's a
<b>Not working?</b> page. It says what to do about each problem and
has the log of the last launch — a file you can send along with your
question. It has no API key in it, but it does show your folder and
file names.</p>

<h2>Where things are</h2>
<div class="card">
@PLACES@
</div>

<h2>AI and money</h2>
<p>Two things in Vertcut can ask an AI model: suggesting segments and
writing descriptions. They need an API key, and it's paid — it isn't
a Claude or ChatGPT subscription, it's a separate thing.
<b>Without a key, everything else in Vertcut works</b>; those two just
stay off. Vertcut's settings, under <b>AI and API key</b>, explain how
to get one.</p>

<h2>What's in the archive</h2>
@INSIDE@

<h2>Source code</h2>
<p>All of it is open, here:
<a href="@ADDRESS@">@ADDRESS@</a>. It also explains how to build
Vertcut yourself — <b>a copy you build yourself opens without any
warnings</b>: the "downloaded from the internet" mark isn't set by the
system, but by the app that downloaded the file.</p>

<p class="quiet">Version @VERSION@. MIT license: do whatever you like
with it. Everything it's built from is free and open; the list with
licenses is in <code>Licenses/</code>.</p>

</div></body></html>
"""


def по_русски() -> None:
    """То же самое, что `vertcut/report.py:по_русски`, и КОПИЕЙ нарочно:
    установка работает до того, как пакет появился, и импортировать ей
    нечего. Одиннадцатое место, где не проходят русские буквы: вывод
    не в консоль, а в журнал или в трубу, берёт кодировку системы —
    а на Windows она русских букв не знает и роняет печать.
    """
    for поток in (sys.stdout, sys.stderr):
        менять = getattr(поток, "reconfigure", None)
        if менять is None:
            continue
        try:
            своя = codecs.lookup(поток.encoding or "ascii").name
        except LookupError:
            своя = ""
        if своя != "utf-8":
            менять(encoding="utf-8", errors="replace")


def main(аргументы=None) -> int:
    по_русски()
    разбор = argparse.ArgumentParser(description="Build the Vertcut release archive")
    разбор.add_argument("--out", dest="куда", type=Path, default=None,
                        help="where to put the archive; the Desktop by default")
    разбор.add_argument("--system", dest="система", choices=["darwin", "windows"],
                        default=None, help="this system by default")
    это = разбор.parse_args(аргументы)

    своя = "windows" if sys.platform.startswith("win") else (
        "darwin" if sys.platform == "darwin" else None)
    система = это.система or своя
    if система is None:
        raise SystemExit(
            "The release is built for macOS and Windows. On Linux, install "
            "Vertcut from the repository — the README says how.")
    if система != своя:
        print("WARNING: building for another system. It can't be run and\n"
              "checked here — and a release nobody has run is worse than\n"
              "no release at all.", file=sys.stderr)

    куда = это.куда or (Path.home() / "Desktop")
    куда.mkdir(parents=True, exist_ok=True)

    раздача = собрать(куда, система)
    архив = упаковать(раздача, система)
    беды = проверить(архив, система)
    # Папка была нужна, чтобы собрать архив; человеку едет архив.
    shutil.rmtree(раздача, ignore_errors=True)

    вес = архив.stat().st_size / 1e6
    print(f"built: {архив}")
    print(f"size: {вес:.1f} MB")
    if беды:
        print("\nUNZIP CHECK FAILED:")
        for беда in беды:
            print(f"  · {беда}")
        return 1
    print(f"unzip check: names are plain Latin, everything is in place"
          f"{', signature intact' if система == 'darwin' else ''}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
