"""Собрать то, что человек скачивает и дважды щёлкает.

    python install/build-launcher.py            — под свою систему
    python install/build-launcher.py --out ...

## Что внутри и чего внутри НЕТ

Внутри: ярлык, установка, поставка сервиса. Всего около трёх мегабайт.

**Внутри НЕТ ни питона, ни ffmpeg, ни модели** — их приносит первый
запуск. Сложи их сюда, и скачиваемое стало бы под гигабайт, а собирать
пришлось бы отдельно под каждую систему и каждое железо. Так же
поступает почти всякая программа, которая просит интернет при первом
запуске, — и по той же причине.

## Про подпись, и это надо знать до раздачи

**Приложение подписано СВОЕЙ подписью и не заверено Apple.** Своя
подпись («adhoc») не стоит денег и не требует у Apple ничего: её
ставит `codesign --sign -`, и делает это последним делом сборка.
Заверение (нотаризация) — другое дело, оно требует платного участия
в программе Apple, 99 долларов в год; решение это авторское, и пока
не платим.

**Разница между «нет подписи» и «есть своя подпись» — это разница
между бедой, которую человек не разрешит ничем, кроме терминала,
и обычным вопросом системы, на который отвечают двумя щелчками.**
Так система смотрит на то и другое (`syspolicy_check distribution`):

| что в свёртке | что говорит система | что может человек |
|---|---|---|
| подписи нет вовсе | «File is not signed at all» | «Программа повреждена. Переместите её в Корзину» |
| своя подпись | «Notary Ticket Missing» | «Не удалось проверить на вредоносное ПО» → в настройках «Всё равно открыть» |

Первое и случилось живьём: архив уехал на чужой макбук, и человек
не смог открыть его вовсе — README обещал заход в настройки, а система
предлагала Корзину.

**Подпись ставится ПОСЛЕДНИМ делом.** Она запечатывает всё, что лежит
внутри свёртка; положи туда что-нибудь после — и подпись сломается,
а сломанная подпись для системы то же самое, что её отсутствие.

На Windows то же самое и тем же порядком: «Защитник» скажет, что
издатель неизвестен, и надо будет нажать «подробнее» и «выполнить
в любом случае».

## Чего этот сборщик не делает

**Не собирает под чужую систему.** Windows-ярлык собирается на Windows,
маковский — на macOS. Причина простая: собранное надо проверять,
а проверить чужую систему отсюда нельзя. Собрать-то можно — и тем
опаснее: получилась бы раздача, которую никто не запускал.
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import codecs
import sys
from pathlib import Path

ЗДЕСЬ = Path(__file__).resolve().parent
КОРЕНЬ = ЗДЕСЬ.parent

# Что кладётся рядом с ярлыком. Список поимённый, а не «всё из папки»:
# поиск однажды подберёт черновик и увезёт его к чужому человеку.
# Что кладётся рядом с ярлыком, и РАЗНОЕ у разных систем.
#
# Общее — таблица источников, установщик и страница хода: они одни
# на обе системы, в этом всё решение установки. Своя у каждой только
# оболочка, которая добывает питон, да виндовый ярлык.
#
# **Чужую половину не кладём, и это не экономия двадцати килобайт.**
# Виндовая папка у человека на виду, и `install.sh` в ней читается
# ровно так, как прочёл её первый получатель: «мне прислали
# исходники». Файл, который человеку нечем открыть, — это мусор
# в папке, а не запас.
ОБЩЕЕ_УСТАНОВКИ = ["sources.txt", "installer.py", "progress.py"]
# Файл точных версий библиотек (28-я сессия) лежит в КОРНЕ репозитория:
# им же ставят командами README и сборочные машины, и копии у него нет.
# В раздачу он едет рядом с установщиком — тот ставит библиотеки по нему.
ИЗ_КОРНЯ_УСТАНОВКИ = ["constraints.txt"]
СВОЁ_УСТАНОВКИ = {"darwin": ["install.sh"],
                  "windows": ["install.ps1", "launcher.ps1"]}

INFO_PLIST = """<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
 "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
  <key>CFBundleName</key><string>Vertcut</string>
  <key>CFBundleDisplayName</key><string>Vertcut</string>
  <key>CFBundleIdentifier</key><string>net.vertcut.app</string>
  <key>CFBundleVersion</key><string>{version}</string>
  <key>CFBundleShortVersionString</key><string>{version}</string>
  <key>CFBundleExecutable</key><string>Vertcut</string>
  <key>CFBundlePackageType</key><string>APPL</string>
  <!-- The app has no windows: it starts Vertcut and opens a browser tab.
       That's why it stays out of the app switcher and the Dock. -->
  <key>LSUIElement</key><true/>
  <!-- macOS 14: below it the speech and face libraries in
       constraints.txt have no builds for Apple Silicon. With this line
       an older Mac hears it from macOS itself, before anything is
       downloaded, instead of a failed install halfway through. -->
  <key>LSMinimumSystemVersion</key><string>14.0</string>
  <key>NSHighResolutionCapable</key><true/>
</dict></plist>
"""

# Что написано в `Vertcut.cmd`, и почему там нет ни одного русского
# слова и ни одного примечания.
#
# **С пятнадцатой сессии он ЗАПАСНАЯ дорога и лежит в `install\`.**
# Нажимают теперь `Vertcut.exe` (о нём ниже). Командный файл остался
# на случай, когда exe не пустит антивирус: делают они одно и то же,
# и второго способа поднять сервис этим не заводится.
#
# **`cmd.exe` читает командный файл СТАРОЙ кодировкой** — той, что
# досталась Windows от DOS. Русские буквы в нём рассыпаются, и путь
# `install\ярлык.ps1` не находится никогда. Это касается и примечаний:
# объяснять работу надо здесь, где объяснение прочтёт человек, а не
# внутри файла, который читает разборщик с чужой привычкой.
#
# **И метки utf-8 в начале быть не должно.** `cmd.exe` её не понимает
# и пытается выполнить как команду: окно мигает, не запускается ничего.
# Поэтому файл пишется без неё — `encoding="ascii"`, а не
# `"utf-8-sig"`, как было до четырнадцатой сессии.
#
# Работа у него одна: позвать PowerShell и скрыться. Окна консоли
# человек видеть не должен — вся работа с иконкой про то, чтобы
# терминала не было вовсе; мелькнёт оно на долю секунды, и это плата
# за то, что своего окна у сервиса нет.
#
# ЭТОТ ФАЙЛ НЕ ПРОВЕРЕН НА ЖИВОЙ WINDOWS НИ РАЗУ.
# **И переноса строки здесь нет.** Батник переносит строку значком `^`,
# и это работает — но файл этот не запускался ни разу, а каждая
# особенность разбора в непроверенном файле это лишний способ
# не запуститься. Длинная строка ничего не стоит.
WINDOWS_CMD = """@echo off
start "" powershell -NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File "%~dp0launcher.ps1"
"""

# `Vertcut.exe` — то, по чему щёлкают на Windows. Исходник рядом,
# `launcher.cs`, и там же написано, зачем он.
#
# **Собирается компилятором, который уже лежит на всякой Windows**
# вместе с .NET Framework, — тем же, что стоит и на сборочной машине.
# Ни новой зависимости, ни скачивания: то же правило, по которому
# сервер экрана написан на стандартной библиотеке.
#
# **`/target:winexe` — программа без окна консоли.** С обычным
# `exe` человек видел бы чёрное окно на всё время жизни ярлыка.
#
# **`/codepage:65001` — чтение исходника как utf-8.** Без него
# компилятор берёт кодировку системы, и русские слова в окне
# «переложите меня в папку» приехали бы мусором.
КОМПИЛЯТОРЫ = [r"Microsoft.NET\Framework64\v4.0.30319\csc.exe",
               r"Microsoft.NET\Framework\v4.0.30319\csc.exe"]


def версия() -> str:
    текст = (КОРЕНЬ / "pyproject.toml").read_text(encoding="utf-8")
    for строка in текст.splitlines():
        if строка.startswith("version"):
            return строка.split("=")[1].strip().strip('"')
    return "0.0.0"


def собрать_поставку(куда: Path) -> Path:
    """Файл поставки самого сервиса. Собирается тем же способом, каким
    его собрал бы всякий, — своего второго способа тут нет."""
    куда.mkdir(parents=True, exist_ok=True)
    for старое in куда.glob("*.whl"):
        старое.unlink()
    subprocess.run([sys.executable, "-m", "pip", "wheel", str(КОРЕНЬ),
                    "--no-deps", "-w", str(куда), "-q"], check=True)
    колёса = list(куда.glob("*.whl"))
    if not колёса:
        raise SystemExit("the Vertcut package (.whl) wasn't built")
    return колёса[0]


def положить_установку(куда: Path, система: str) -> None:
    куда.mkdir(parents=True, exist_ok=True)
    for имя in ОБЩЕЕ_УСТАНОВКИ + СВОЁ_УСТАНОВКИ[система]:
        shutil.copy2(ЗДЕСЬ / имя, куда / имя)
    for имя in ИЗ_КОРНЯ_УСТАНОВКИ:
        shutil.copy2(КОРЕНЬ / имя, куда / имя)


def маковский(куда: Path) -> Path:
    """`Vertcut.app` — обычная папка, которую система показывает иконкой."""
    приложение = куда / "Vertcut.app"
    shutil.rmtree(приложение, ignore_errors=True)
    внутри = приложение / "Contents"
    (внутри / "MacOS").mkdir(parents=True)
    (внутри / "Resources").mkdir(parents=True)

    (внутри / "Info.plist").write_text(
        INFO_PLIST.format(version=версия()), encoding="utf-8")

    пуск = внутри / "MacOS" / "Vertcut"
    shutil.copy2(ЗДЕСЬ / "launcher.sh", пуск)
    пуск.chmod(0o755)

    ресурсы = внутри / "Resources"
    положить_установку(ресурсы / "install", "darwin")
    колесо = собрать_поставку(ресурсы)
    # Ярлык ищет установку и поставку РЯДОМ С СОБОЙ. Внутри свёртка
    # исполняемый файл лежит в MacOS/, а обвес в Resources/ — так велит
    # система, и ссылка связывает одно с другим.
    (внутри / "MacOS" / "install").symlink_to("../Resources/install")
    (внутри / "MacOS" / колесо.name).symlink_to(f"../Resources/{колесо.name}")
    подписать(приложение)
    return приложение


def подписать(приложение: Path) -> None:
    """Своя подпись — последним делом, и её же сразу проверяем.

    Зачем она нужна и чем «нет подписи» отличается от «своя подпись»,
    написано наверху этого файла таблицей. Здесь важно другое:

    **Проверяем тут же, а не надеемся.** Подпись ломается от всякой
    правки внутри свёртка, а сломанная для системы то же самое, что
    её отсутствие, — то есть «повреждено» у чужого человека. Увидеть
    это должен тот, кто собирает, а не тот, кому собранное отдали.

    **Не подписалось — сборка ВСТАЁТ.** Раздача без подписи выглядит
    как раздача и не открывается ни у кого.
    """
    try:
        subprocess.run(["codesign", "--force", "--sign", "-", str(приложение)],
                       check=True)
    except FileNotFoundError:
        raise SystemExit(
            "no `codesign` — the Mac app is built on macOS. Without "
            "a signature it can't be handed out: another Mac will say "
            "the app is damaged.")
    проверка = subprocess.run(
        ["codesign", "--verify", "--deep", "--strict", str(приложение)],
        capture_output=True, text=True)
    if проверка.returncode != 0:
        raise SystemExit(
            "the signature doesn't verify — another Mac will say the "
            f"app is damaged:\n{проверка.stderr.strip()}")


def виндовый(куда: Path) -> Path:
    """Папка с `Vertcut.exe` внутри. Свёртков в Windows нет."""
    папка = куда / "Vertcut"
    shutil.rmtree(папка, ignore_errors=True)
    папка.mkdir(parents=True)
    положить_установку(папка / "install", "windows")
    (папка / "install" / "Vertcut.cmd").write_text(
        WINDOWS_CMD, encoding="ascii", newline="\r\n")
    собрать_поставку(папка / "install")
    собрать_exe(папка / "Vertcut.exe")
    return папка


def собрать_exe(куда: Path) -> None:
    """`Vertcut.exe` из `launcher.cs`.

    **Нет компилятора — сборка ВСТАЁТ**, а не кладёт один `.cmd`.
    Раздача без exe выглядит как раздача, а человеку в ней снова
    нажимать шестерёнку; тот же выбор, что с подписью на macOS.
    """
    система = Path(os.environ.get("WINDIR", r"C:\Windows"))
    компилятор = next((система / к for к in КОМПИЛЯТОРЫ
                       if (система / к).exists()), None)
    if компилятор is None:
        raise SystemExit(
            "no C# compiler from .NET Framework — Vertcut.exe is built "
            "on Windows. Looked for:\n  "
            + "\n  ".join(str(система / к) for к in КОМПИЛЯТОРЫ))
    вышло = subprocess.run(
        [str(компилятор), "/nologo", "/target:winexe", "/optimize+",
         "/codepage:65001", "/r:System.Windows.Forms.dll",
         f"/out:{куда}", str(ЗДЕСЬ / "launcher.cs")],
        capture_output=True, text=True, errors="replace")
    if вышло.returncode != 0 or not куда.exists():
        raise SystemExit("Vertcut.exe didn't build:\n"
                         + (вышло.stdout + вышло.stderr).strip())


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
    разбор = argparse.ArgumentParser(description="Build the Vertcut app icon")
    разбор.add_argument("--out", dest="куда", type=Path, default=КОРЕНЬ / "dist",
                        help="where to put the result")
    разбор.add_argument("--system", dest="система", choices=["darwin", "windows"],
                        default=None, help="this system by default")
    это = разбор.parse_args(аргументы)
    система = это.система or ("windows" if sys.platform.startswith("win")
                              else "darwin" if sys.platform == "darwin"
                              else None)
    if система is None:
        raise SystemExit(
            "The app is built for macOS and Windows. On Linux, install "
            "Vertcut from the repository — the README says how.")
    if система != ("windows" if sys.platform.startswith("win") else "darwin"):
        print("WARNING: building for another system. It can't be run and\n"
              "checked here — and a release nobody has run is worse than\n"
              "no release at all.", file=sys.stderr)
    вышло = (виндовый if система == "windows" else маковский)(это.куда)
    вес = sum(ф.stat().st_size for ф in вышло.rglob("*")
              if ф.is_file() and not ф.is_symlink())
    print(f"built: {вышло}")
    print(f"size: {вес / 1e6:.1f} MB")
    if система == "darwin":
        print("signature: ad-hoc, verified")
    print("\nThere's no Python, ffmpeg or model inside — the first launch\n"
          "downloads them. The signature and first steps are in the README.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
