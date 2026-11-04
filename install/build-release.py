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

## Заверение у Apple: `--notarize`

    python install/build-release.py --notarize

С 31-й сессии у автора есть сертификат «Developer ID Application»,
и маковская раздача может уехать ЗАВЕРЕННОЙ: человек дважды щёлкает,
система спрашивает «Открыть?» — и всё, без захода в настройки. Без
ключа сборка та же, что прежде, со своей подписью: так собирают
сборочная машина и всякий, у кого сертификата нет.

Порядок, и каждый шаг в нём не переставляется:

1. иконка подписывается сертификатом автора (`build-launcher.py`);
2. ОДНА иконка уезжает в Apple (`notarytool submit --wait`), и ответ
   ждётся тут же — пара минут;
3. отметка о заверении вкладывается в иконку (`stapler staple`).
   Без неё система спросила бы Apple по сети при первом запуске,
   а без сети — отказала бы. Отметка подписи не ломает: она для того
   и придумана;
4. только ПОТОМ собирается архив раздачи — иначе в архиве иконка
   без отметки.

**Пароль для отправки в Apple не лежит ни в проекте, ни в команде.**
Он в связке ключей под именем `vertcut-notary` (заводится один раз:
`xcrun notarytool store-credentials vertcut-notary …`), и сборка
называет только это имя.

**Проверка распаковкой с `--notarize` строже:** у распакованного
спрашиваются `stapler validate` и `spctl` — система должна сказать
«Notarized Developer ID». Заверили, но не доехало — сборка красная.
"""

from __future__ import annotations

import argparse
import codecs
import shutil
import subprocess
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


def собрать(куда: Path, система: str, заверить: bool = False) -> Path:
    """Папка раздачи. Возвращает её путь.

    `заверить` — подписать иконку сертификатом автора и заверить
    у Apple (только macOS); порядок — наверху этого файла."""
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
        if заверить:
            приложение = сборщик.маковский(раздача, сборщик.сертификат_автора())
            заверить_у_apple(приложение)
        else:
            сборщик.маковский(раздача)

    (раздача / "README.html").write_text(страница(система), encoding="utf-8")

    лицензии = раздача / "Licenses"
    лицензии.mkdir()
    for имя in ЛИЦЕНЗИИ:
        shutil.copy2(КОРЕНЬ / имя, лицензии / имя)
    return раздача


# Под каким именем в связке ключей лежит пароль для отправки в Apple.
# Одним местом: его называют сборка и подсказка, как его завести.
ПРОФИЛЬ_ЗАВЕРЕНИЯ = "vertcut-notary"


def заверить_у_apple(приложение: Path) -> None:
    """Отправить иконку в Apple, дождаться ответа, вложить отметку.

    Apple принимает архив, а не папку, — поэтому иконка пакуется
    отдельно, во времянку рядом с собой, и времянка потом уходит.
    **Отказ Apple — отказ сборки, с их же объяснением:** без него
    не понять, что чинить, а раздача без заверения выглядела бы ровно
    как заверенная.
    """
    import json

    врем = Path(tempfile.mkdtemp(prefix="vertcut-notary-",
                                 dir=приложение.parent))
    try:
        посылка = врем / "Vertcut.zip"
        subprocess.run(["ditto", "-c", "-k", "--sequesterRsrc", "--keepParent",
                        str(приложение), str(посылка)], check=True)
        print("notarizing: sent to Apple, waiting for the answer "
              "(usually a few minutes)…", flush=True)
        вышло = subprocess.run(
            ["xcrun", "notarytool", "submit", str(посылка),
             "--keychain-profile", ПРОФИЛЬ_ЗАВЕРЕНИЯ, "--wait",
             "--output-format", "json"],
            capture_output=True, text=True)
    finally:
        shutil.rmtree(врем, ignore_errors=True)
    try:
        ответ = json.loads(вышло.stdout)
    except ValueError:
        ответ = {}
    if ответ.get("status") != "Accepted":
        if not ответ:
            raise SystemExit(
                "Apple's notary service couldn't be asked:\n"
                + (вышло.stderr or вышло.stdout).strip()
                + f"\nIf the password isn't stored yet: xcrun notarytool "
                f"store-credentials {ПРОФИЛЬ_ЗАВЕРЕНИЯ} --apple-id <email> "
                "--team-id <team id>")
        журнал = subprocess.run(
            ["xcrun", "notarytool", "log", ответ.get("id", ""),
             "--keychain-profile", ПРОФИЛЬ_ЗАВЕРЕНИЯ],
            capture_output=True, text=True)
        raise SystemExit(
            f"Apple didn't notarize the app: {ответ.get('status')} — "
            f"{ответ.get('message', '')}\n{журнал.stdout.strip()}")
    print(f"notarizing: accepted ({ответ.get('id')})", flush=True)
    отметка = subprocess.run(["xcrun", "stapler", "staple", str(приложение)],
                             capture_output=True, text=True)
    if отметка.returncode != 0:
        raise SystemExit(
            "Apple notarized the app, but the ticket couldn't be attached "
            "— without it a Mac offline would refuse to open it:\n"
            + (отметка.stderr or отметка.stdout).strip())


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


def проверить(архив: Path, система: str, заверено: bool = False) -> list[str]:
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
            if заверено:
                беды += беды_заверения(корень / "Vertcut.app")
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


def беды_заверения(приложение: Path) -> list[str]:
    """Доехало ли заверение до распакованного — глазами самой системы.

    `spctl` отвечает ровно на тот вопрос, который система задаёт при
    двойном щелчке; `stapler validate` — на месте ли отметка, без
    которой машина вне сети откажет.
    """
    беды = []
    отметка = subprocess.run(["xcrun", "stapler", "validate", str(приложение)],
                             capture_output=True, text=True)
    if отметка.returncode != 0:
        беды.append("the notarization ticket didn't survive the archive — "
                    "a Mac offline won't open the app")
    допуск = subprocess.run(["spctl", "-a", "-t", "exec", "-vv", str(приложение)],
                            capture_output=True, text=True)
    ответ = (допуск.stdout + допуск.stderr).strip()
    if допуск.returncode != 0 or "Notarized Developer ID" not in ответ:
        беды.append(f"macOS doesn't see the app as notarized: {ответ}")
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
                  .replace("@ADD@", ДОБАВИТЬ_WINDOWS if окна else ДОБАВИТЬ_MAC)
                  .replace("@INSIDE@", ВНУТРИ_WINDOWS if окна else ВНУТРИ_MAC)
                  .replace("@PLACES@", МЕСТА_WINDOWS if окна else МЕСТА_MAC)
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
# **С 31-й сессии маковская раздача заверена Apple**, и шаг 3 — один
# вопрос «Открыть?», а не заход в настройки. Строка мелким — для
# архива, собранного без заверения (своими руками, `build-release.py`
# без `--notarize`): там система по-прежнему отказывает, и человеку
# надо знать, куда идти. **Кнопка «Open Anyway» живёт около часа**
# после попытки открыть — так пишет Apple; поэтому «сразу после».
ШАГИ_MAC = """
<div class="step"><div class="n">1</div><div>
  <b>Unzip the archive</b> — anywhere, Downloads is fine.
</div></div>

<div class="step"><div class="n">2</div><div>
  <b>Double-click <code>Vertcut</code></b> in the unzipped folder.
</div></div>

<div class="step"><div class="n">3</div><div>
  <b>The first time, macOS asks if you want to open it</b> — an app
  downloaded from the internet. Click <b>Open</b>. Vertcut is checked
  by Apple, and macOS only asks this once.
  <p class="quiet" style="margin:6px 0 0">If instead macOS says
  <b>"Vertcut" Not Opened</b> (a copy that wasn't checked by Apple
  says that), click <b>Done</b>, then right away open <b>System
  Settings → Privacy &amp; Security</b>, scroll down and click
  <b>Open Anyway</b> next to the line about Vertcut.</p>
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

# «Choose file» есть только на macOS: на Windows системного диалога
# выбора нет (TODO.md), и обещать его там нельзя.
ДОБАВИТЬ_MAC = """<b>Add a video</b> — drag the file into the browser
      window, or click <b>Choose file</b>."""

ДОБАВИТЬ_WINDOWS = """<b>Add a video</b> — drag the file into the browser
      window."""

ВНУТРИ_MAC = """<ul>
  <li><code>Vertcut</code> — the app you open.</li>
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
    разбор.add_argument("--notarize", dest="заверить", action="store_true",
                        help="macOS: sign with the Developer ID certificate "
                        "and have Apple notarize the app")
    это = разбор.parse_args(аргументы)

    своя = "windows" if sys.platform.startswith("win") else (
        "darwin" if sys.platform == "darwin" else None)
    система = это.система or своя
    if система is None:
        raise SystemExit(
            "The release is built for macOS and Windows. On Linux, install "
            "Vertcut from the repository — the README says how.")
    if это.заверить and (система != "darwin" or своя != "darwin"):
        raise SystemExit("--notarize is for the Mac release, built on a Mac.")
    if система != своя:
        print("WARNING: building for another system. It can't be run and\n"
              "checked here — and a release nobody has run is worse than\n"
              "no release at all.", file=sys.stderr)

    куда = это.куда or (Path.home() / "Desktop")
    куда.mkdir(parents=True, exist_ok=True)

    раздача = собрать(куда, система, это.заверить)
    архив = упаковать(раздача, система)
    беды = проверить(архив, система, это.заверить)
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
          f"{', signature intact' if система == 'darwin' else ''}"
          f"{', notarized' if это.заверить else ''}")
    if система == "darwin" and not это.заверить:
        print("NOT NOTARIZED: macOS will send people to Settings to allow it. "
              "For a release: --notarize")
    return 0


if __name__ == "__main__":
    sys.exit(main())
