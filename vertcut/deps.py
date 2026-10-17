"""Что должно быть на месте, чтобы сервис работал, и как это проверить.

Работа этого файла — рассказать человеку, чего не хватает, СВОИМИ
словами и до того, как он потратит девять минут на разбор.

**Проверка ничего не чинит и ничего не ставит.** Правило перенесено
из Нарезатора вместе с причиной: зависимость, поставленная молча
посреди работы, однажды поставится не та и не туда, а человек узнает
об этом через три стадии.

**Библиотеки спрашиваются по одной и по имени.** Не «попробуем
импортировать всё разом»: одна отсутствующая тогда прячет остальные,
и человек ставит их по очереди, каждый раз узнавая о следующей.
"""

from __future__ import annotations

import importlib
import importlib.metadata as md
import os
import sys

from . import layout, tuning
from .run import FFMPEG, FFPROBE, run, where
from pathlib import Path

# Вилка версий питона. Держится не капризом: под самый свежий питон
# колёса библиотек подъезжают последними, и человек, у которого стоит
# только он, получил бы сборку из исходников вместо установки.
#
# Нижняя граница 3.11 — от Нарезатора, где она стояла из-за движка
# распознавания. Сегодня движок умеет и 3.12, и 3.13 (проверено
# 1 сентября 2026 года), так что снизу её держит только то, что ниже
# никто не проверял. Верхняя — 3.14 с 26-й сессии; замер в `pyproject.toml`,
# и обе границы должны совпадать с ним.
PYTHON_MIN = (3, 11)
PYTHON_MAX = (3, 14)

# Что нужно и зачем. Пара «как импортируется» / «как называется
# в установке»: у половины библиотек эти имена разные, и путать их
# значит сказать человеку «поставьте cv2», чего он поставить не сможет.
# Сколько весит поставленное окружение.
#
# ЗАМЕР 3 сентября 2026 года: 243 МБ. До шестой сессии было 364 —
# уход от opencv снял 121. Самое тяжёлое теперь: движок детектора лиц
# 80 МБ, разбор видео 44, числа 34, рисование 14.
ВЕС_БИБЛИОТЕК_МБ = 243

LIBS = [
    ("faster_whisper", "faster-whisper", "transcribing speech"),
    ("ctranslate2", "ctranslate2", "engine under transcribing"),
    ("numpy", "numpy", "numbers: timings, metrics, frames"),
    ("onnxruntime", "onnxruntime", "face detector engine"),
    ("PIL", "pillow", "drawing subtitles"),
    ("yaml", "pyyaml", "styles: numbers as parts of the frame"),
]


# Что обязано приехать вместе с кодом.
#
# **Список нужен потому, что поставка однажды уехала неполной.** Шестая
# сессия собрала её и посмотрела внутрь: там был только код — 51 файл,
# и ни одного шрифта, профиля, веса детектора или файла страницы.
# У автора это не всплывало, потому что у него сервис поставлен «на
# месте», где обвес лежит рядом.
#
# Список ОДИН на проверку окружения и на автотест: второй такой же
# разошёлся бы с первым молча, и разошёлся бы ровно в ту сторону,
# в которую никто не смотрит.
#
# Здесь только то, без чего сервис не работает. Лицензии и «ОТКУДА»
# проверяет свой заслон, у него другая причина: их отсутствие ломает
# не работу, а право раздавать.
ПОСТАВКА = [
    ("subtitles.yaml", "default subtitle style"),
    ("looks.yaml", "presets"),
    ("prompt-suggest.txt", "prompt for segments"),
    ("prompt-notes.txt", "prompt for descriptions"),
    ("prompt-proofread.txt", "prompt for checking subtitles"),
    ("fonts/InterTight.ttf", "subtitle font"),
    ("fonts/GolosText.ttf", "subtitle font"),
    ("fonts/Oswald.ttf", "subtitle font"),
    ("fonts/Literata.ttf", "subtitle font"),
    ("models/yunet.onnx", "face detector weights"),
    ("web/index.html", "screen page"),
    ("web/tokens.css", "colors and scale from the design kit"),
    ("web/components.css", "screen parts from the design kit"),
    ("web/screen.css", "our own styles on top of the kit"),
    ("web/js/shell.js", "page frame"),
    ("web/js/route.js", "page address, in one place"),
    ("web/js/api.js", "talking to Vertcut"),
    ("web/js/words.js", "counts and labels"),
    ("web/js/draw.js", "markup from data"),
    ("web/js/app.js", "routing between screens"),
    ("web/js/intake.js", "adding a file"),
    ("web/js/screens/videos.js", "screen: videos"),
    ("web/js/screens/ingest.js", "screen: analysis"),
    ("web/js/screens/picks.js", "screen: segments"),
    ("web/js/screens/cut.js", "screen: clip"),
    ("web/js/screens/subs.js", "screen: subtitle editor"),
    ("web/js/screens/render.js", "screen: export"),
    ("web/js/screens/notes.js", "screen: descriptions"),
    ("web/js/screens/settings.js", "screen: settings"),
    ("web/fonts/JetBrainsMono.ttf", "interface font"),
    ("web/fonts/LiterataItalic.ttf", "interface font"),
]


def обвес() -> list[dict]:
    """Всё ли на месте в поставке. Пусто — значит всё."""
    корень = layout.assets()
    out = []
    for имя, зачем in ПОСТАВКА:
        out.append({"имя": имя, "зачем": зачем,
                    "есть": (корень / имя).exists()})
    return out


def кэш_моделей() -> Path:
    """Куда движок распознавания кладёт скачанную модель.

    Считается по тем же правилам, что и у него самого, но СВОИМИ
    руками: `check` обязан отвечать на машине, где библиотек ещё нет
    вовсе — иначе он не сможет сказать, чего именно не хватает.
    """
    if os.environ.get("HF_HUB_CACHE"):
        return Path(os.environ["HF_HUB_CACHE"]).expanduser()
    if os.environ.get("HF_HOME"):
        return Path(os.environ["HF_HOME"]).expanduser() / "hub"
    if os.environ.get("XDG_CACHE_HOME"):
        return Path(os.environ["XDG_CACHE_HOME"]).expanduser() / "huggingface" / "hub"
    return Path.home() / ".cache" / "huggingface" / "hub"


def модель_распознавания() -> dict:
    """Скачана ли модель распознавания и сколько она весит.

    **Про неё не знал никто, и это была дыра ровно там, где больно.**
    Модель весит около 460 МБ и качается при первом разборе; человек,
    у которого её ещё нет, узнавал об этом на девятой минуте работы,
    а без сети — не узнавал вовсе, потому что разбор просто падал.
    """
    имя = tuning.WHISPER_MODEL
    папка = кэш_моделей() / f"models--Systran--faster-whisper-{имя}"
    return {"имя": имя, "есть": папка.exists() and вес_папки(папка) > 0,
            "где": папка, "вес_мб": round(вес_папки(папка) / 1e6)}


def вес_папки(папка: Path) -> int:
    """Сколько весят файлы папки, если идти по ссылкам, — каждый
    настоящий файл один раз.

    **Ссылки не пропускаются, а разворачиваются**, и это замер 27-й
    сессии. До неё ссылки пропускались: на маке кэш устроен так, что
    в `snapshots/` лежат ссылки, а сами файлы — в `blobs/` той же папки,
    и счёт сходился. На сборочной машине Windows (huggingface_hub 2.x,
    хранилище xet) `blobs/<хэш>` модели САМ оказался ссылкой — на общий
    склад `hub/blobs/42/…` ВНЕ папки модели, — и `check` писал «3 MB»
    вместо 486: настоящий `model.bin` не попадал в счёт вовсе.
    Поэтому файл берётся по месту, куда ведёт ссылка, и складывается
    по настоящему пути один раз — сколько бы ссылок на него ни вело.
    """
    if not папка.exists():
        return 0
    настоящие: dict[str, int] = {}
    for файл in папка.rglob("*"):
        try:
            if not файл.is_file():
                continue
            куда = str(файл.resolve())
            настоящие.setdefault(куда, os.stat(куда).st_size)
        except OSError:
            continue        # битая ссылка: файла нет — нечего и считать
    return sum(настоящие.values())


def python_ok() -> bool:
    return PYTHON_MIN <= sys.version_info[:2] <= PYTHON_MAX


def python_line() -> str:
    v = ".".join(str(x) for x in sys.version_info[:3])
    нужно = (f"{PYTHON_MIN[0]}.{PYTHON_MIN[1]}–"
             f"{PYTHON_MAX[0]}.{PYTHON_MAX[1]}")
    return f"{v} — {'OK' if python_ok() else 'NOT OK'} (needs {нужно})"


def libs() -> list[dict]:
    """Каждая библиотека: стоит ли, какой версии, зачем нужна.

    **«Не поставлено» и «поставлено, но не загружается» — РАЗНЫЕ беды,
    и это замер, а не аккуратность.** Библиотека проверяется импортом,
    а импорт падает не только от отсутствия. Автор увидел на экране
    «НЕТ numpy 2.5.2 — ставятся, около 243 МБ» у себя на машине, где
    numpy стояла и работала: сервис был запущен иконкой, а та подняла
    питон под Rosetta — и arm64-библиотеки в него не грузились вовсе.
    Совет «поставьте» в этом случае не просто бесполезен: человек
    полчаса ставит то, что у него есть.

    Отличается это надёжно: версия читается из МЕТАДАННЫХ, а они лежат
    файлом рядом с библиотекой. Есть версия, а импорт упал — значит
    она поставлена, и беда в том, ЧЕМ её поднимают. Причина тогда
    называется словами: первая строка ошибки импорта.
    """
    out = []
    for имя, пакет, зачем in LIBS:
        беда = None
        try:
            importlib.import_module(имя)
            стоит = True
        except Exception as е:
            стоит = False
            беда = str(е).strip().splitlines()[0] if str(е).strip() else \
                type(е).__name__
        try:
            версия = md.version(пакет)
        except md.PackageNotFoundError:
            версия = ""
        out.append({"имя": имя, "пакет": пакет, "зачем": зачем,
                    "стоит": стоит, "версия": версия,
                    # Поставлена, но не поднимается. Проверяется
                    # по метаданным, а не по тексту ошибки: текст пишут
                    # библиотеки и меняют, когда захотят.
                    "лежит_но_не_грузится": bool(версия) and not стоит,
                    "почему": беда})
    return out


# Где ffmpeg лежит у людей, когда его нет в PATH.
#
# **Список нужен НЕ для запуска.** Запускается по-прежнему то, что
# нашлось в PATH: правило «ffmpeg ищется в PATH, а не пишется путём»
# в силе, и обходить его здесь нельзя — иначе сервис начнёт работать
# на машине, где PATH урезан, и урезанный PATH никто никогда
# не заметит.
#
# Список нужен, чтобы СКАЗАТЬ ПРАВДУ. «ffmpeg НЕТ — ставится, около
# 80 МБ» человеку, у которого он стоит через Homebrew, — это не совет,
# а посылка ставить второй раз то, что уже есть. Так и случилось:
# сервис, запущенный иконкой, получил launchd-овский PATH
# (`/usr/bin:/bin:/usr/sbin:/sbin`), и `/opt/homebrew/bin/ffmpeg`
# в него не попал.
ОБЫЧНЫЕ_МЕСТА = ("/opt/homebrew/bin", "/usr/local/bin", "/opt/local/bin")


def лежит_но_не_в_пути(имя: str) -> str | None:
    """Есть ли программа в обычном месте, когда в PATH её нет."""
    for место in ОБЫЧНЫЕ_МЕСТА:
        рядом = Path(место) / имя
        if рядом.exists() and os.access(рядом, os.X_OK):
            return str(рядом)
    return None


def ffmpeg() -> dict:
    """Где лежит ffmpeg и какой он версии.

    Версия печатается не для красоты: у ffmpeg порядок слов в команде
    — часть смысла, и когда однажды что-то соберётся не так, первым
    вопросом будет «а какой у вас ffmpeg».
    """
    путь = where(FFMPEG)
    версия = ""
    if путь:
        try:
            строка = run([FFMPEG, "-version"]).splitlines()[0]
            версия = строка.split(" version ")[-1].split()[0]
        except Exception:
            версия = "could not read"
    return {"путь": путь, "версия": версия, "probe": where(FFPROBE),
            # Не нашли в PATH — смотрим, не лежит ли он рядом. Это
            # не запуск, а честность: см. примечание у списка.
            "мимо_пути": None if путь else лежит_но_не_в_пути(FFMPEG)}


def всё_на_месте() -> bool:
    """Можно ли работать прямо сейчас.

    Модель распознавания сюда НЕ входит, и это решение: её отсутствие
    — не поломка окружения, а первая минута первого разбора. Сказать
    «чего-то не хватает» человеку, у которого всё поставлено и просто
    ещё не было ни одного видео, значит соврать.
    """
    м = ffmpeg()
    return (python_ok() and bool(м["путь"]) and bool(м["probe"])
            and all(x["стоит"] for x in libs())
            and all(x["есть"] for x in обвес()))


def _где_взять_ffmpeg() -> str:
    """Откуда придёт ffmpeg — зависит от того, как поставлен сервис.

    Установщик из архива приносит его сам, и человеку там правда
    «ставится». Поставленному из клона (`INSTALL.md`) его не принесёт
    никто — найдено в 26-й сессии агентом, который ставил сервис
    на машину без ffmpeg: прежняя строка обещала установку, которой
    не будет.
    """
    if layout.программа() is not None:
        return "it gets installed, about 80 MB: open Vertcut again"
    return ("install it so that `ffmpeg` works in a terminal "
            "(INSTALL.md, step 2)")


def чего_не_хватает() -> list[str]:
    """Чего не хватает — по одной строке на беду, словами.

    **Считается ЗДЕСЬ, а не на экране, и это починка.** Полоса
    на экране собиралась так: взять весь отчёт и оставить строки,
    в которых есть буквы «НЕ». Пока «НЕ» стояло в каждой беде, это
    работало; стоило беде назваться иначе — «ЕСТЬ, но сервис его
    не видит», «ПОСТАВЛЕНА, но не загружается», — и она пропала бы
    из полосы молча. Экран не должен решать, что важно, разглядывая
    буквы в чужом тексте.
    """
    беды = []
    if not python_ok():
        беды.append(f"Python {python_line()}")
    м = ffmpeg()
    if not м["путь"] and м["мимо_пути"]:
        беды.append(f"ffmpeg is installed ({м['мимо_пути']}), but this "
                    "process was started with a short PATH and cannot see it")
    elif not м["путь"]:
        беды.append(f"ffmpeg is MISSING — {_где_взять_ffmpeg()}; "
                    "nothing works without it")
    elif not м["probe"]:
        беды.append("ffprobe is MISSING — it comes with ffmpeg")
    for x in libs():
        if x["стоит"]:
            continue
        if x["лежит_но_не_грузится"]:
            беды.append(f"{x['пакет']} {x['версия']} is installed but "
                        f"does not load — no need to reinstall it: "
                        f"{x['почему']}")
        else:
            беды.append(f"{x['пакет']} is NOT installed — {x['зачем']}")
    нет = [x for x in обвес() if not x["есть"]]
    if нет:
        беды.append(f"bundled files are incomplete: {len(нет)} of "
                    f"{len(ПОСТАВКА)} missing — the package was built wrong")
    return беды


def отчёт() -> list[str]:
    """Строки для печати. Печатает их команда, а не этот файл.

    **У каждой строки сказано, откуда оно берётся:** лежит в поставке,
    скачается само или ставится руками. Список «чего нет» без этого
    — это список поводов для паники: человек видит десять «нет»
    и не знает, что девять из них появятся сами через минуту.
    """
    строки = [f"Python     {python_line()}"]

    м = ffmpeg()
    if м["путь"]:
        строки.append(f"ffmpeg     {м['путь']}"
                      + (f" (version {м['версия']})" if м["версия"] else ""))
    elif м["мимо_пути"]:
        строки.append(f"ffmpeg     INSTALLED, but Vertcut cannot see it: "
                      f"{м['мимо_пути']}")
        строки.append("           this process was started with a short PATH — "
                      "no need to reinstall ffmpeg")
    else:
        строки.append(f"ffmpeg     MISSING — {_где_взять_ffmpeg()}. "
                      "Nothing works without it")
    if not м["probe"] and м["путь"]:
        строки.append("ffprobe    MISSING — it comes with ffmpeg")

    строки.append("")
    строки.append(f"Libraries (installed, about {ВЕС_БИБЛИОТЕК_МБ} MB on disk):")
    for x in libs():
        знак = "✓" if x["стоит"] else "NO"
        верс = x["версия"] or "—"
        строки.append(f"  {знак:>3}  {x['пакет']:<23} {верс:<10} {x['зачем']}")
        # Поставлена, но не поднимается — это не «поставьте её».
        if x["лежит_но_не_грузится"]:
            строки.append(f"       it IS installed but does not load — "
                          f"no need to reinstall it:")
            строки.append(f"       {x['почему']}")

    строки.append("")
    м2 = модель_распознавания()
    if м2["есть"]:
        строки.append(f"Transcribing model “{м2['имя']}”: in place, "
                      f"{м2['вес_мб']} MB")
        строки.append(f"  {м2['где']}")
    else:
        строки.append(f"Transcribing model “{м2['имя']}”: DOWNLOADS "
                      f"on the first analysis, about "
                      f"{tuning.ВЕС_МОДЕЛИ_МБ} MB")
        строки.append("  This is the only time Vertcut needs the internet, "
                      "apart from the AI buttons.")
        строки.append(f"  It will go here: {м2['где']}")

    строки.append("")
    нет = [x for x in обвес() if not x["есть"]]
    if нет:
        строки.append(f"Bundled files: INCOMPLETE — {len(нет)} of "
                      f"{len(ПОСТАВКА)} missing. The package was built wrong:")
        for x in нет:
            строки.append(f"  no   {x['имя']:<32} {x['зачем']}")
    else:
        строки.append(f"Bundled files: all {len(ПОСТАВКА)} in place — fonts, "
                      f"style, face detector weights, screen page")

    строки.append("")
    строки.append("Folders:")
    корень = layout.root()
    строки.append(f"  videos     {корень}"
                  + ("" if корень.exists() else "  (created on the first analysis)"))
    строки.append(f"  settings   {layout.settings_dir()}"
                  + ("" if layout.settings_dir().exists() else "  (created on its own)"))
    строки.append(f"  bundled    {layout.assets()}")
    return строки
