"""Команда `vertcut`: разбор слов и печать. Логики здесь нет.

Правило перенесено вместе с причиной: всё, что делает команда, делают
функции стадий, и их же позовёт будущий экран. Иначе экран и терминал
соберут разное, и увидит это зритель.

**Разбор аргументов — стандартный argparse, а не click.** Click хорош,
но это ещё одна зависимость в списке, который человек ставит руками
на своей машине. Работа команды в том числе — рассказать, что окружение
не собралось; инструмент, который сам для этого нужен, для такой работы
не годится.

**Отказ печатается по одному правилу**: первая строка — что случилось,
дальше подсказка после пустой строки. Отказ, у которого подсказка
утонула в потоке слов, читается как поломка, и человек начинает чинить
не то.
"""

from __future__ import annotations

import argparse
import signal
import sys
from pathlib import Path

from . import report, tuning
from .errors import VertcutError


def _остановка(*_) -> None:
    """SIGTERM — это «остановите», а не «умрите молча».

    Заведено ради экрана: он гасит долгую работу сигналом, а не
    флажком в файле (флажок стадия увидела бы только между шагами,
    а распознавание идёт минутами внутри чужой библиотеки). Без этого
    обработчика процесс умирает, не выполнив ни одного `finally`, —
    то есть оставляет работу занятой мёртвым хозяином, и кнопка потом
    твердит «уже идёт», когда никто не идёт.

    Превращается в то же самое, чем человек останавливает работу
    в терминале: Ctrl+C. Дорога у остановки одна, и обрабатывается
    она в одном месте.
    """
    raise KeyboardInterrupt


def main(argv: list[str] | None = None) -> int:
    # Первым делом, до единого напечатанного слова: на Windows вывод
    # в журнал роняет питона на первой же русской букве.
    report.по_русски()
    signal.signal(signal.SIGTERM, _остановка)

    parser = парсер()
    args = parser.parse_args(argv)
    if not getattr(args, "дело", None):
        parser.print_help()
        return 1

    try:
        # Дело может вернуть свой код выхода — пока это делает одна
        # `check`; остальные возвращают None, и это ноль.
        код = args.дело(args)
    except VertcutError as exc:
        report.беда(exc.message, exc.hint)
        return 1
    except BrokenPipeError:
        # Человек оборвал вывод — `vertcut phrases … | head`. Это
        # не поломка, и трассировкой отвечать на неё нельзя: она
        # выглядит как отказ там, где всё в порядке.
        import os
        os.dup2(os.open(os.devnull, os.O_WRONLY), sys.stdout.fileno())
        return 0
    except KeyboardInterrupt:
        print("\nStopped.", file=sys.stderr)
        return 130
    return код or 0


def парсер() -> argparse.ArgumentParser:
    """Все команды и их ключи. Отдельно от `main` — ради проверки:
    она сверяет ключи, названные в подсказках по всему проекту,
    с тем, что команда принимает на самом деле."""
    parser = argparse.ArgumentParser(
        prog="vertcut",
        description="Cuts long videos into vertical clips with subtitles",
    )
    слова = parser.add_subparsers(dest="слово", metavar="COMMAND")

    # Ключи — английские, по словарю `docs/glossary.md`: одно слово
    # словаря — одно имя ключа. Имена внутри (`dest`) остаются русскими,
    # как и весь код: их видит только тот, кто читает этот файл.

    p = слова.add_parser("check", help="what is missing to work")
    p.set_defaults(дело=_check)

    p = слова.add_parser("ingest",
                         help="analyze a video (slow, done once per video)")
    p.add_argument("файл", type=Path, metavar="VIDEO",
                   help="path to the video file")
    p.add_argument("--script", type=Path, default=None, metavar="FILE",
                   help="the script, .docx or .txt; without it the text "
                        "is the transcript")
    p.add_argument("--again", dest="заново", action="store_true",
                   help="don't skip finished stages, redo everything")
    p.set_defaults(дело=_ingest)

    p = слова.add_parser("phrases", help="the phrases with their times")
    p.add_argument("слаг", metavar="VIDEO_ID",
                   help="video id (see vertcut videos)")
    p.add_argument("--from", type=int, default=None, dest="с", metavar="N",
                   help="first phrase to show")
    p.add_argument("--to", type=int, default=None, dest="по", metavar="N",
                   help="last phrase to show")
    p.set_defaults(дело=_phrases)

    p = слова.add_parser("videos", help="videos analyzed so far")
    p.set_defaults(дело=_videos)

    p = слова.add_parser(
        "crop", help="measure the crop for shots again (slow: ~0.4 s a shot)")
    p.add_argument("слаг", metavar="VIDEO_ID", help="video id")
    p.add_argument("--shots", dest="планы", default=None, metavar="N-M",
                   help="which shots, for example 1-50 or 7 (default: all)")
    p.add_argument("--sheet", dest="лист", action="store_true",
                   help="draw a contact sheet with the crops")
    p.set_defaults(дело=_crop)

    p = слова.add_parser("pick", help="pick a segment of the video for a clip")
    p.add_argument("слаг", metavar="VIDEO_ID", help="video id")
    p.add_argument("--text", default=None,
                   help="a pasted part of the script (or - to read it "
                        "from the terminal)")
    p.add_argument("--range", dest="диапазон", default=None, metavar="N-M",
                   help="phrase numbers: 13-31 or 21-22,25-30")
    p.add_argument("--start", default=None, metavar="TIME",
                   help="start time, 1:25.0")
    p.add_argument("--end", default=None, metavar="TIME", help="end time")
    p.add_argument("--which", type=int, default=None, metavar="N",
                   help="which match to take when the text fits "
                        "in several places")
    p.add_argument("--again", dest="заново", action="store_true",
                   help="overwrite the clip with the same id")
    p.set_defaults(дело=_pick)

    p = слова.add_parser("cuts", help="clips picked and exported")
    p.add_argument("слаг", metavar="VIDEO_ID", help="video id")
    p.set_defaults(дело=_cuts)

    p = слова.add_parser("title", help="the clip's title")
    p.add_argument("слаг", metavar="VIDEO_ID")
    p.add_argument("ключ", metavar="CLIP_ID")
    p.add_argument("--title", dest="название", default=None, metavar="TITLE",
                   help="your own title; empty — back to the one Vertcut "
                        "made")
    p.set_defaults(дело=_title)

    p = слова.add_parser("frame", help="set a shot's crop by hand")
    p.add_argument("слаг", metavar="VIDEO_ID")
    p.add_argument("ключ", metavar="CLIP_ID")
    p.add_argument("--shot", dest="план", type=int, required=True,
                   metavar="N", help="shot number")
    p.add_argument("--crop", dest="рамка", type=float, default=None,
                   metavar="FRACTION",
                   help="center of the crop as a fraction of the width: "
                        "0.5 is the middle")
    p.add_argument("--mode", dest="режим", default=None,
                   choices=["crop", "full"],
                   help="crop, or full frame with blurred sides")
    p.add_argument("--reset", dest="сбросить", action="store_true",
                   help="back to the crop Vertcut suggested")
    p.set_defaults(дело=_frame)

    p = слова.add_parser("plans", help="the clip's shots and their crops")
    p.add_argument("слаг", metavar="VIDEO_ID")
    p.add_argument("ключ", metavar="CLIP_ID")
    p.add_argument("--sheet", dest="лист", action="store_true",
                   help="draw a contact sheet of this clip's shots")
    p.set_defaults(дело=_plans)

    p = слова.add_parser(
        "text", help="edit the clip's phrases: split, merge, text")
    p.add_argument("слаг", metavar="VIDEO_ID")
    p.add_argument("ключ", metavar="CLIP_ID")
    p.add_argument("--phrase", dest="фраза", type=int, default=None,
                   metavar="N",
                   help="phrase number from the video's list "
                        "(vertcut phrases)")
    p.add_argument("--text", dest="текст", default=None, metavar="TEXT",
                   help="new text for this phrase")
    p.add_argument("--split", dest="разделить", type=int, default=None,
                   metavar="N",
                   help="split after word N of the phrase (counting from 1)")
    p.add_argument("--merge", dest="склеить", action="store_true",
                   help="merge this phrase with the next one")
    p.add_argument("--reset", dest="сбросить", action="store_true",
                   help="remove the edits: of this phrase, or all of them "
                        "without --phrase")
    p.set_defaults(дело=_text)

    p = слова.add_parser("subs", help="the clip's subtitles in numbers")
    p.add_argument("слаг", metavar="VIDEO_ID")
    p.add_argument("ключ", metavar="CLIP_ID")
    p.add_argument("--sheet", dest="лист", action="store_true",
                   help="draw a sheet of the subtitle layout")
    вкл = p.add_mutually_exclusive_group()
    вкл.add_argument("--on", dest="в_файле", action="store_const", const=True,
                     default=None, help="show subtitles in the exported clip")
    вкл.add_argument("--off", dest="в_файле", action="store_const",
                     const=False, help="export the clip without subtitles")
    p.set_defaults(дело=_subs)

    p = слова.add_parser(
        "fonts", help="fonts that come with Vertcut, and yours")
    p.set_defaults(дело=_fonts)

    p = слова.add_parser(
        "looks", help="subtitle presets: what there is and how they differ")
    p.add_argument("слаг", nargs="?", default=None, metavar="VIDEO_ID",
                   help="measure the presets again on this video")
    p.set_defaults(дело=_looks)

    p = слова.add_parser(
        "style", help="subtitle style: whose it is, what it is, how it looks")
    p.add_argument("слаг", metavar="VIDEO_ID", help="video id")
    p.add_argument("ключ", nargs="?", default=None, metavar="CLIP_ID",
                   help="clip id: with it, only this clip's style changes")
    p.add_argument("--set", dest="задать", action="append", default=None,
                   metavar="KEY=VALUE",
                   help="change one setting of the style, for example "
                        "size=0.05")
    p.add_argument("--font", dest="шрифт", default=None,
                   metavar="FILE_OR_NAME",
                   help="use a font: a name from the list (vertcut fonts) "
                        "or your .ttf/.otf file — it is copied to "
                        "~/.vertcut/fonts")
    p.add_argument("--case", dest="регистр", default=None,
                   choices=["as_typed", "all_caps", "small_caps"],
                   help="case of the subtitle text")
    p.add_argument("--background", dest="подложка", default=None,
                   choices=["box", "outline", "shadow", "none"],
                   help="what sets the subtitle apart from the picture")
    p.add_argument("--karaoke", dest="подсветка", default=None,
                   choices=["none", "word", "line"],
                   help="what is highlighted as it is spoken")
    p.add_argument("--karaoke-by", dest="чем", default=None,
                   choices=["color", "box", "size"],
                   help="how it is highlighted")
    p.add_argument("--from-bottom", dest="от_низа", default=None,
                   metavar="FRACTION",
                   help="where the bottom of the subtitle is, as a fraction "
                        "of the frame height (0.22 — low, 0.48 — middle)")
    p.add_argument("--side-margins", dest="поля", default=None,
                   metavar="FRACTION",
                   help="margin on the left and right, as a fraction "
                        "of the frame width")
    p.add_argument("--safe-zones", dest="беречь", default=None,
                   choices=["on", "off"],
                   help="keep the subtitle out from under the platforms' "
                        "buttons")
    p.add_argument("--preset", dest="вид", default=None, metavar="NAME",
                   help="use a whole preset: it goes on top of the default "
                        "style (to see them: vertcut looks)")
    p.add_argument("--sheet", dest="лист", action="store_true",
                   help="draw a sheet on real frames: before and after")
    p.add_argument("--show-zones", dest="зоны", action="store_true",
                   help="show the platforms' safe zones on the sheet")
    p.add_argument("--my-style", dest="мой", action="store_true",
                   help="use my style: it is copied into this video")
    p.add_argument("--save-as-my-style", dest="сделать_моим",
                   action="store_true",
                   help="save this video's style as my style")
    p.add_argument("--apply-to-all", dest="всем", action="store_true",
                   help="give this clip's style to all the other clips "
                        "of this video")
    p.add_argument("--default-style", dest="поставляемый",
                   action="store_true",
                   help="put the default style back into this video")
    p.set_defaults(дело=_style)

    p = слова.add_parser(
        "plate", help="end card: thumbnail, background image, text")
    p.add_argument("слаг", metavar="VIDEO_ID", help="video id")
    p.add_argument("ключ", nargs="?", default=None, metavar="CLIP_ID",
                   help="clip id; without it, the first clip picked")
    p.add_argument("--thumbnail", dest="обложка", default=None,
                   metavar="FILE",
                   help="add the thumbnail: one per video, every clip "
                        "of it uses the same")
    p.add_argument("--remove-thumbnail", dest="снять_обложку",
                   action="store_true", help="remove the thumbnail")
    p.add_argument("--background-image", dest="фон", default=None,
                   metavar="FILE",
                   help="copy your background image to "
                        "~/.vertcut/backgrounds and use it")
    p.add_argument("--text", dest="текст", default=None, metavar="TEXT",
                   help="this clip's own end card text; --text \"\" goes "
                        "back to the default text from the style")
    p.set_defaults(дело=_plate)

    p = слова.add_parser("render", help="export clips")
    p.add_argument("слаг", metavar="VIDEO_ID")
    p.add_argument("ключ", nargs="?", default=None, metavar="CLIP_ID",
                   help="without it — every clip not exported yet")
    p.add_argument("--again", dest="заново", action="store_true",
                   help="export again even if up to date")
    p.set_defaults(дело=_render)

    p = слова.add_parser(
        "proof", help="compare the screen with the exported file")
    p.add_argument("слаг", metavar="VIDEO_ID")
    p.add_argument("ключ", metavar="CLIP_ID")
    p.set_defaults(дело=_proof)

    p = слова.add_parser(
        "ai", help="API key, API type, model, spending; --test")
    p.add_argument("--api-key", dest="ключ", metavar="KEY",
                   help="save the API key (in your settings, not in the "
                        "Vertcut folder)")
    p.add_argument("--remove-api-key", dest="убрать_ключ",
                   action="store_true", help="forget the API key")
    p.add_argument("--api-type", dest="протокол",
                   choices=["anthropic", "openai"],
                   help="how to talk to the provider: Anthropic or the "
                        "OpenAI protocol")
    p.add_argument("--api-address", dest="адрес", metavar="URL",
                   help="API address")
    p.add_argument("--model", dest="модель", metavar="NAME",
                   help="model name, as in the provider's documentation")
    p.add_argument("--ask-above", dest="порог", type=float, metavar="DOLLARS",
                   help="ask before a request that costs more")
    p.add_argument("--daily-limit", dest="стоп", type=float,
                   metavar="DOLLARS", help="daily limit")
    p.add_argument("--test", dest="проверить", action="store_true",
                   help="one cheap request: does it answer")
    p.set_defaults(дело=_ai)

    p = слова.add_parser(
        "suggest", help="ask AI to suggest segments (costs money)")
    p.add_argument("слаг", metavar="VIDEO_ID")
    p.add_argument("--again", dest="заново", action="store_true",
                   help="ask again even if there are suggestions already")
    p.add_argument("--yes", dest="да", action="store_true",
                   help="agree to a request above the ask-above price")
    p.set_defaults(дело=_suggest)

    p = слова.add_parser(
        "describe", help="ask AI to write descriptions (costs money)")
    p.add_argument("слаг", metavar="VIDEO_ID")
    p.add_argument("ключ", nargs="?", default=None, metavar="CLIP_ID",
                   help="without it — every clip with no description")
    p.add_argument("--rewrite-all", dest="всем", action="store_true",
                   help="rewrite all, including the written ones")
    p.add_argument("--yes", dest="да", action="store_true",
                   help="agree to a request above the ask-above price")
    p.set_defaults(дело=_describe)

    p = слова.add_parser(
        "proofread",
        help="ask AI to check a clip's subtitles for recognition mistakes "
             "(costs money)")
    p.add_argument("слаг", metavar="VIDEO_ID")
    p.add_argument("ключ", metavar="CLIP_ID")
    p.add_argument("--again", dest="заново", action="store_true",
                   help="ask again even if there are AI fixes already")
    p.add_argument("--accept", dest="принять", metavar="N|all",
                   help="accept an AI fix by its number in the list, or all")
    p.add_argument("--dismiss", dest="отклонить", metavar="N|all",
                   help="dismiss an AI fix by its number in the list, or all")
    p.add_argument("--yes", dest="да", action="store_true",
                   help="agree to a request above the ask-above price")
    p.set_defaults(дело=_proofread)

    p = слова.add_parser("screen", help="open Vertcut in the browser")
    p.add_argument("--port", dest="порт", type=int, default=None,
                   metavar="PORT",
                   help="port to listen on (default 7864, or the first "
                        "free one after it)")
    p.add_argument("--no-browser", dest="не_открывать",
                   action="store_true",
                   help="don't open the browser, only print the address")
    p.add_argument("--exit-with-icon", dest="уйти_с_ярлыком",
                   action="store_true",
                   help="exit when the process that started it exits "
                        "(this is how the icon starts Vertcut)")
    p.add_argument("--print-address", dest="адрес", action="store_true",
                   help="print the address of the running screen and exit")
    p.set_defaults(дело=_screen)

    p = слова.add_parser(
        "stop", help="stop the running Vertcut screen (analysis and export "
                     "keep going)")
    p.set_defaults(дело=_stop)

    p = слова.add_parser("queue", help="the export queue")
    p.add_argument("слаг", metavar="VIDEO_ID")
    p.add_argument("--export", dest="собрать", action="store_true",
                   help="start exporting")
    p.add_argument("--again", dest="заново", action="store_true",
                   help="build the queue again, dropping the unfinished one")
    p.add_argument("--only", dest="только", action="append", default=None,
                   metavar="CLIP_ID",
                   help="export just this clip; the others in the queue "
                        "keep waiting")
    p.set_defaults(дело=_queue)

    return parser


def _proof(args) -> None:
    """Пятая сверка: то, что человек видел на экране, — в файле ли оно.

    **Четыре заслона сверяют файл с МОНТАЖОМ, а не с экраном.** Пока
    браузер не набирает субтитр сам, правда одна — но «одна» это
    утверждение, а не измерение. Здесь оно становится измерением,
    и повторить его можно одной командой: число, которое нельзя
    перемерить, через полгода становится преданием.
    """
    from . import layout, pick, render, verify

    папка, meta, _ = _открыть(args.слаг)
    всё = render.открыть_ролик(папка, meta, args.ключ)
    cut = всё["cut"]
    файл = layout.out(папка, cut)

    report.скажи(f"\n{pick.зовут(cut)}   {файл.name}")
    report.скажи("comparing the screen with the file…")
    итог = verify.экран_против_файла(папка, meta, cut, всё["ряды"],
                                     всё["раскл"], всё["prof"], всё["шрифт"],
                                     файл)
    report.скажи("")
    report.скажи("    second    match    control   margin")
    for точка in итог["точки"]:
        report.скажи(f"  {точка['при']:>8.2f}  {точка['связь']:>7.4f}  "
                     f"{точка['контроль']:>9.4f}  "
                     f"{точка['связь'] - точка['контроль']:>+8.4f}")
    report.скажи("")
    report.скажи(
        "  It is never exactly 1, and it can't be: the preview is drawn by\n"
        "  Pillow and the file is cut by ffmpeg, so the edges of the letters\n"
        "  always differ by a level or two of brightness. What matters is\n"
        "  that the number is measured, recorded and repeatable with this\n"
        "  command.")
    report.скажи(
        f"  Control is the same frame with the subtitle moved by "
        f"{итог['сдвиг_контроля']:.0%} of the height. The margin shows\n"
        "  that the check doesn't just agree with anything.")


def _ai(args) -> None:
    """Ключ, адрес, протокол, модель и деньги — одной командой.

    **Без слов «AI не настроен» и без пустого экрана.** Команда всегда
    печатает, что сейчас взято и откуда: у человека ключ может лежать
    и в оболочке, и в файле, и понять, который из них работает,
    неоткуда, если сервис об этом не говорит.
    """
    from . import ai, config, spend, tuning

    # Правка — той же функцией, что у экрана, и с её проверками: ключ
    # с русской буквой, адрес не на http, отрицательные деньги. До 24-й
    # сессии команда писала в настройки сама и пропускала всё это —
    # найдено прочёсом (`tools/cyrillic-sweep.py`).
    что: dict = {}
    if args.убрать_ключ:
        что["ключ"] = ""
    if args.ключ:
        что["ключ"] = args.ключ
    for имя in ("протокол", "адрес", "модель", "порог", "стоп"):
        значение = getattr(args, имя, None)
        if значение is not None and значение != "":
            что[имя] = значение
    if что:
        ai.настроить(что)
        report.скажи("Saved.\n")

    модель = config.модель()
    цена = config.цена(модель)
    report.скажи("AI — two buttons; everything else works without them\n")
    report.скажи(f"  API type     {config.протокол()}")
    report.скажи(f"  API address  {config.адрес()}")
    report.скажи(f"  model        {модель}")
    report.скажи(f"  API key      {config.model_key_tail()}  "
                 f"({config.откуда_ключ()})")
    if цена:
        report.скажи(f"  price        ${цена[0]:g} per million input / "
                     f"${цена[1]:g} per million output tokens — prices "
                     f"checked {tuning.ЦЕНЫ_СВЕРЕНЫ}")
    else:
        report.скажи("  price        UNKNOWN — Vertcut won't show money, "
                     "only the size of the request")
    report.скажи(f"  ask above    ${config.порог():.2f}")
    report.скажи(f"  daily limit  ${config.стоп():.2f}")

    прошло = spend.день()
    report.скажи(f"\n  today        ${прошло['деньги']:.4f} · "
                 f"{report.счёт(прошло['запросов'], 'request', 'requests')} · "
                 f"{прошло['вошло']} + {прошло['вышло']} tokens")
    if прошло["без_цены"]:
        report.скажи("               and "
                     f"{report.счёт(прошло['без_цены'], 'request', 'requests')}"
                     " with an unknown price — they don't count toward the "
                     "daily limit")
    было = spend.замер(модель)
    if было:
        report.скажи(f"  measured     this model answers with "
                     f"{было['вышло_в_среднем']:.0f} tokens in "
                     f"{было['секунд_в_среднем']:.1f} s on average "
                     f"({report.счёт(было['ответов'], 'request', 'requests')})")

    if not config.подключён():
        report.скажи("\nNo API key — and that's fine: all of Vertcut works "
                     "except these two buttons.")
        return
    if not args.проверить:
        report.скажи("\nTest it with one cheap request: "
                     "vertcut ai --test")
        return

    report.скажи("\nAsking…")
    вышло = ai.проверить()
    стоило = ("free or price unknown" if вышло["стоило"] is None
              else f"${вышло['стоило']:.5f}")
    report.скажи(f"It answers: {вышло['модель']} in {вышло['секунд']:.1f} s, "
                 f"{стоило}")


def _suggest(args) -> None:
    """Кандидаты во фрагменты. Печатает и годные, и негодные.

    **Негодные не прячутся** — правило дизайна: причина часто
    интереснее самого предложения. «Короче порога на три секунды»
    говорит про материал больше, чем ещё один годный кусок.
    """
    from . import ingest, layout, spend, suggest

    project, meta, laid = ingest.открыть(args.слаг)
    было = suggest.прочитать(project)
    if было and not args.заново:
        свежо = suggest.свежие_ли(project, laid, было)
        report.скажи(f"There are AI suggestions already, asked "
                     f"{было['когда'][:16]}."
                     + ("" if свежо else
                        "\n  THE PHRASES HAVE BEEN SPLIT AGAIN SINCE — the "
                        "numbers now point to other places in the video."))
        _напечатать_предложения(было)
        report.скажи("\nAsk again: vertcut suggest "
                     f"{args.слаг} --again")
        return

    текст = suggest._что_показать_модели(laid, meta)
    оценка = spend.оценить(текст, tuning.ПОТОЛОК_КАНДИДАТОВ)
    report.скажи(_цена_словами(оценка) + "\n")

    это = suggest.спросить(project, laid, meta,
                           разрешено_дорого=args.да,
                           на_ходу=report.скажи)
    report.скажи(
        f"\n{это['модель']} answered in {это['секунд']:.1f} s: "
        f"{это['вошло']} + {это['вышло']} tokens"
        + (f", ${это['деньги']:.4f}" if это["деньги"] is not None
           else ", price of this model unknown"))
    _про_прикидку(оценка, это)
    if это["оборвался"]:
        report.скажи("  THE ANSWER WAS CUT OFF at the token limit — the last "
                     "suggestion may be incomplete.")
    if это["язык_разошёлся"]:
        report.скажи("  WRONG LANGUAGE: the video is in one language, the "
                     "answer in another. Say so in the prompt.")
    _напечатать_предложения(это)
    report.скажи(f"\n  the whole AI answer: {layout.suggestions_raw(project)}")


def _цена_словами(оценка: dict) -> str:
    """Цена ДО нажатия. Правило спеки: не прятать цену обращения."""
    размер = (f"{оценка['знаков']} characters ≈ {оценка['вошло']} input "
              f"tokens, the answer about {оценка['выйдет']} "
              f"({оценка['откуда_оценка']})")
    if оценка["деньги"] is None:
        return (f"Asking {оценка['модель']}: {размер}.\n"
                "  Vertcut doesn't know this model's price, so it can't "
                "say what this will cost.")
    return (f"Asking {оценка['модель']}: {размер}.\n"
            f"  That's about ${оценка['деньги']:.4f}. "
            f"Spent today: ${оценка['за_сегодня']['деньги']:.2f} "
            f"of ${оценка['стоп']:.2f}.")


def _про_прикидку(оценка: dict, это: dict) -> None:
    """Насколько своя прикидка размера разошлась с фактом.

    Печатается всегда, а не только при большом расхождении: это
    единственное место, где число `ЗНАКОВ_НА_ТОКЕН` вообще
    проверяется, и молчащая проверка — не проверка.
    """
    было, стало = оценка["вошло"], это["вошло"]
    if not стало:
        return
    доля = (стало - было) / стало * 100
    report.скажи(f"  input estimate: {было}, actual {стало} "
                 f"({доля:+.0f}%)")


def _напечатать_предложения(это: dict) -> None:
    from . import slug as _slug           # noqa: F401  (для симметрии имён)

    все = это["предложения"]
    report.скажи(f"\n{это['годных']} of {len(все)} usable\n")
    for э in все:
        где = (f"phrases {э['с']}–{э['по']}" if э["с"] else "no phrases given")
        сколько = f" · {э['duration']:.0f} s" if э["duration"] else ""
        метка = ("clip exists" if э["есть_ключ"] else
                 "" if э["годен"] else "NOT USABLE")
        report.скажи(f"  #{э['н']:<3} {э['название'] or '(no title)'}"
                     + (f"   [{метка}]" if метка else ""))
        report.скажи(f"       {где}{сколько}")
        if э["о_чём"]:
            report.скажи(f"       {э['о_чём']}")
        if э["почему"]:
            report.скажи(f"       not usable: {э['почему']}")
        if э["есть_ключ"]:
            report.скажи(f"       clip exists: {э['есть_ключ']}")


def _describe(args) -> None:
    """Описания моделью. То же поле, что и у написанных рукой."""
    from . import describe, ingest, layout, notes, pick

    project, _, _ = ingest.открыть(args.слаг)
    if args.ключ:
        ключи = [args.ключ]
    elif args.всем:
        ключи = describe.все_ключи(project)
    else:
        ключи = describe.без_описания(project)
    if not describe.все_ключи(project):
        # «Описания есть у всех» про видео без единой вертикалки —
        # неправда, и звучит она успокаивающе. Пустота и полнота
        # выглядели одинаково.
        report.скажи("This video has no clips — there is nothing "
                     "to describe.")
        report.скажи(f"  pick a segment: vertcut pick {args.слаг} --range 1-12")
        return
    if not ключи:
        report.скажи("Every clip has a description. Rewrite all: "
                     f"vertcut describe {args.слаг} --rewrite-all")
        return

    оценка = describe.оценить(project, ключи)
    report.скажи("Writing descriptions for "
                 + report.счёт(len(ключи), "clip", "clips") + ".")
    report.скажи(_цена_словами(оценка) + "\n")

    это = describe.написать(project, ключи, разрешено_дорого=args.да,
                            на_ходу=report.скажи)
    report.скажи(
        f"\n{это['модель']} answered in {это['секунд']:.1f} s: "
        f"{это['вошло']} + {это['вышло']} tokens"
        + (f", ${это['деньги']:.4f}" if это["деньги"] is not None
           else ", price of this model unknown"))
    _про_прикидку(оценка, это)
    if это["язык_разошёлся"]:
        report.скажи("  WRONG LANGUAGE: the video is in one language, the "
                     "descriptions in another. Say so in the prompt.")
    if это["не_ответила"]:
        report.скажи("  NO ANSWER for: "
                     + ", ".join(это["не_ответила"]))
    if это["чужие_ключи"]:
        report.скажи("  answered for clip ids nobody asked about: "
                     + ", ".join(это["чужие_ключи"]))

    report.скажи("")
    for ключ in это["записано"]:
        текст = notes.прочитать(pick.load(project, ключ))["текст"]
        report.скажи(f"  {ключ}  {текст}")
    for пара in это["одинаковые"]:
        report.скажи(f"\n  THESE DESCRIPTIONS START THE SAME WAY "
                     f"“{пара['начало']}…”: {пара['один']} and "
                     f"{пара['другой']}")
    report.скажи(f"\n  the whole AI answer: {layout.notes_raw(project)}")


def _proofread(args) -> None:
    """Вычитка субтитров моделью. Правки предлагаются, а не ложатся сами."""
    from . import ingest, layout, pick, proofread

    project, _, _ = ingest.открыть(args.слаг)
    cut = pick.load(project, args.ключ)
    if args.принять or args.отклонить:
        _решить_правки(project, cut, args)
        return

    было = proofread.свежие(project, cut)
    if было and not args.заново:
        report.скажи("There are AI fixes already:")
        _напечатать_правки(было, args)
        return

    оценка = proofread.оценить(project, cut)
    report.скажи(_цена_словами(оценка) + "\n")
    это = proofread.спросить(project, args.ключ, разрешено_дорого=args.да,
                             на_ходу=report.скажи)
    report.скажи(
        f"\n{это['модель']} answered in {это['секунд']:.1f} s: "
        f"{это['вошло']} + {это['вышло']} tokens"
        + (f", ${это['деньги']:.4f}" if это["деньги"] is not None
           else ", price of this model unknown"))
    _про_прикидку(оценка, это)
    if это["оборвался"]:
        report.скажи("  THE ANSWER WAS CUT OFF at the token limit — the last "
                     "fix may be missing.")
    if это["не_та_азбука"]:
        report.скажи("  WRONG LANGUAGE: "
                     + report.счёт(это["не_та_азбука"], "fix", "fixes")
                     + " came in another alphabet and were left out.")
    if это["чужие_строки"]:
        report.скажи("  fixes for lines that aren't in this clip were left "
                     "out: " + ", ".join(это["чужие_строки"]))
    if not это["правки"]:
        report.скажи("\nAI found nothing to fix.")
    else:
        report.скажи(f"\nAI suggested "
                     + report.счёт(len(это["правки"]), "fix", "fixes") + ":")
        _напечатать_правки(это["правки"], args)
    report.скажи(f"\n  the whole AI answer: "
                 f"{layout.proofread_raw(project, args.ключ)}")


def _напечатать_правки(правки: list[dict], args) -> None:
    for н, п in enumerate(правки, 1):
        report.скажи(f"\n  #{н}  {п['было']}")
        report.скажи(f"   →  {п['стало']}")
        if п["почему"]:
            report.скажи(f"      {п['почему']}")
    report.скажи(f"\nAccept: vertcut proofread {args.слаг} {args.ключ} "
                 "--accept 1 (or --accept all); dismiss: --dismiss 1. "
                 "To change a fix first, edit the phrase in the subtitle "
                 "editor.")


def _решить_правки(project, cut: dict, args) -> None:
    """Принять или отклонить по номеру в списке — или все разом."""
    from . import pick, proofread

    живые = proofread.свежие(project, cut)
    что = args.принять or args.отклонить
    if что == "all":
        с = по = None
    else:
        try:
            п = живые[int(что) - 1]
        except (ValueError, IndexError):
            raise VertcutError(
                f"No AI fix number {что}",
                hint=f"see the list: vertcut proofread {args.слаг} "
                     f"{args.ключ}") from None
        с, по = п["с"], п["по"]
    if args.принять:
        сколько = proofread.принять(project, cut, с, по)
        pick.update(project, cut)
        report.скажи("Accepted " + report.счёт(сколько, "AI fix", "AI fixes")
                     + ". The clip is out of date — export again.")
    else:
        сколько = proofread.отклонить(project, cut, с, по)
        report.скажи("Dismissed " + report.счёт(сколько, "AI fix", "AI fixes")
                     + ".")


def _screen(args) -> None:
    """Экран. Вся работа сервиса — та же самая, только мышью."""
    from .web import server

    if args.адрес:
        # Адрес собирается ОДНИМ местом. Иконка после установки уводит
        # свою страницу хода на сервис, и собирать этот адрес второй
        # раз, в оболочке, значило бы завести вторую правду о том, как
        # он выглядит.
        живой = server.живой_хозяин()
        if not живой:
            raise VertcutError("Vertcut isn't running right now",
                               hint="start it: vertcut screen")
        report.скажи(server.адрес_хозяина(живой))
        return

    server.run(порт=args.порт, открывать=not args.не_открывать,
               уйти_с_ярлыком=args.уйти_с_ярлыком)


def _stop(args) -> None:
    """Погасить экран — тот же путь, что у кнопки «Quit Vertcut»."""
    from .web import server

    server.остановить_работающий()


def _check(args) -> int:
    """Код выхода — ответ, а не только слова.

    До 26-й сессии `check` выходил с нулём и тогда, когда ffmpeg
    не находился: сборочная машина проверяла код выхода — и не могла
    покраснеть никогда. Теперь на него опираются и она, и агент,
    который ставит сервис по `INSTALL.md`. Модель распознавания в счёт
    не идёт (`deps.всё_на_месте`).
    """
    from . import deps
    print("vertcut — environment check\n")
    for строка in deps.отчёт():
        print(строка)
    print()
    if deps.всё_на_месте():
        print("Everything is in place.")
        return 0
    print("Something is missing — the lines above say what.")
    return 1


def _ingest(args) -> None:
    from . import ingest
    ingest.run(args.файл, script_path=args.script, заново=args.заново)




def _phrases(args) -> None:
    """Список фраз — то, чем человек выбирает кусок руками.

    **Надёжность печатается числом, а не флажком.** Замер: из 72
    прикидочных границ 64 стоят в одном слове от опоры, промах в сотые
    доли. Одинаковый флажок утопил бы в шуме те четыре, которые правда
    опасны.

    **Столбец надёжности один, а смысл у него два — по тому, откуда
    взялся текст.** Со сценарием сомнение во времени: слово известно.
    Без сценария наоборот: время измерено, а слово под вопросом. Два
    столбца сразу показали бы человеку две надёжности и не сказали,
    какая из них про его беду.
    """
    from . import layout, speech

    папка = layout.project(args.слаг)
    if not папка.exists():
        raise VertcutError(f"No such video: {args.слаг}",
                           hint="to see your videos, run: vertcut videos")
    это = speech.список_фраз(speech.read(папка))
    фразы = это["фразы"]
    по_слуху = это["надёжность"] == "слух"

    с = max(args.с or 1, 1)
    по = min(args.по or len(фразы), len(фразы))
    if с > по:
        raise VertcutError(f"Nothing to show: from {с} to {по}",
                           hint=f"this video has phrases 1 to {len(фразы)}")

    print(f"Video: {args.слаг}   phrases: {len(фразы)}   shown {с}–{по}\n")
    print("  " + это["про"] + "\n")
    print(f"    #     time   length  {'heard' if по_слуху else 'edge '}"
          "       text")
    for фраза in фразы[с - 1:по]:
        if по_слуху:
            надёжность = f"{фраза['слух']:.2f}"
        else:
            слева = "" if фраза["слева"] == 0 else f"‹{фраза['слева']}"
            справа = "" if фраза["справа"] == 0 else f"{фраза['справа']}›"
            надёжность = f"{слева:>3} {справа}"
        print(f"  {фраза['idx']:>3}   {speech.show_time(фраза['start'])}  "
              f"{фраза['duration']:4.1f} s  "
              f"{надёжность:<9}  {фраза['text']}")


def _videos(args) -> None:
    """Список разборов. Считает его `ingest.список`, здесь только печать."""
    from . import ingest, layout

    разборы = ingest.список()
    if not разборы:
        print(f"No videos analyzed yet. They will be in {layout.root()}")
        return
    for это in разборы:
        if not это["журнал"]:
            беда = это.get("беда", "no analysis data")
            print(f"{это['слаг']}  — the folder is there, {беда}")
            continue
        длина = это["duration"]
        сделано = ", ".join(это["стадии"]) if это["стадии"] else "nothing"
        print(f"{это['слаг']}")
        print(f"    {это['источник']}")
        print(f"    {int(длина // 60)} min {int(длина % 60):02d} s · "
              f"{это['width']}×{это['height']} · done: {сделано}")


def _crop(args) -> None:
    """Рамка кадра планам видео.

    **Считается по подмножеству, а не всегда по всему видео.** Это самая
    дорогая работа в сервисе, а в один ролик попадают десятки планов
    из сотен. Кому рамка не нужна — тому она и не считается; кому нужна,
    тот её и оплачивает.
    """
    from . import crop, ingest, layout, shots as планы

    папка = layout.project(args.слаг)
    if not папка.exists():
        raise VertcutError(f"No such video: {args.слаг}",
                           hint="to see your videos, run: vertcut videos")
    meta = ingest.read_meta(папка)
    найдено = планы.read(папка)

    только = None
    if args.планы:
        кусок = args.планы.split("-")
        начало = int(кусок[0])
        конец = int(кусок[-1])
        только = {n for n in range(начало, конец + 1)}
        есть = {s["idx"] for s in найдено}
        если_нет = только - есть
        if если_нет:
            нет = sorted(если_нет)
            raise VertcutError(
                "No such shots: " + ", ".join(map(str, нет[:5]))
                + (f" and {len(нет) - 5} more" if len(нет) > 5 else ""),
                hint=f"this video has shots 1 to {max(есть)}")

    итог = crop.посчитать(Path(meta["source"]), папка, только)
    найдено = планы.read(папка)
    report.скажи(f"\nshots measured: {итог['shots']}")
    ingest.сказать_о_рамках(итог, report.скажи)

    if args.лист:
        считанные = [s for s in найдено if s.get("crop_cx") is not None]
        страницы = планы.sheets(считанные, папка, рисовать_рамку=True)
        report.скажи(f"  contact sheet with crops: {страницы[0].parent}")


def _открыть(слаг: str):
    """Папка разбора, её журнал и уложенный текст — одним движением.

    Считает `ingest.открыть`: тот же отказ с той же подсказкой обязан
    приходить и человеку в терминале, и человеку на экране.
    """
    from . import ingest

    return ingest.открыть(слаг)


def _pick(args) -> None:
    """Выбор куска: три дороги к одной паре номеров слов."""
    import sys

    from . import pick, plate

    папка, meta, laid = _открыть(args.слаг)
    дороги = [bool(args.text), bool(args.диапазон),
              bool(args.start or args.end)]
    if sum(дороги) != 1:
        raise VertcutError(
            "Give ONE way to pick: --text, --range or --start/--end",
            hint="Vertcut won't decide for you which one wins")

    duration = float(meta["duration"])
    if args.диапазон:
        куски = pick.by_ranges(laid, pick.parse_ranges(args.диапазон))
        как = f"phrases {args.диапазон}"
    elif args.text:
        текст = sys.stdin.read() if args.text == "-" else args.text
        раскладки = pick.by_text(laid, текст)
        if len(раскладки) > 1 and args.which is None:
            report.скажи(f"The text fits the script in {len(раскладки)} "
                         f"places — choose one: --which N\n")
            for n, раскладка in enumerate(раскладки, 1):
                где = ", ".join(
                    f"{pick.show_time(laid['words'][a]['s'])}"
                    f"–{pick.show_time(laid['words'][b]['e'])}"
                    for a, b in раскладка)
                report.скажи(f"  {n}. "
                             f"{report.счёт(len(раскладка), 'segment', 'segments')}"
                             f": {где}")
            return
        куски = раскладки[(args.which or 1) - 1]
        как = "pasted text"
    else:
        if not (args.start and args.end):
            raise VertcutError("Only one end of the segment is given",
                               hint="give both: --start and --end")
        первое = pick.snap(laid, pick.parse_time(args.start), "start")
        последнее = pick.snap(laid, pick.parse_time(args.end), "end")
        куски = [(первое, последнее)]
        как = f"time {args.start}–{args.end}"

    описание = pick.describe(laid, куски, как, duration)
    # Порог длины растёт вместе с плашкой в конце: она замещает
    # последние секунды картинки, и от пятнадцатисекундного ролика
    # три секунды плашки — это плашка с предисловием.
    pick.check_length(описание, plate.секунд_у(папка))
    pick.save(папка, описание, заново=args.заново)
    свежий = pick.load(папка, описание["id"])

    report.скажи(f"\n{pick.зовут(свежий)}")
    report.скажи(f"  clip id {свежий['id']}   file {свежий.get('файл', '—')}")
    report.скажи(f"  {свежий['duration']:.1f} s of speech, "
                 f"{report.счёт(len(pick.pieces(свежий)), 'segment', 'segments')}, "
                 f"{report.счёт(свежий['phrases']['count'], 'phrase', 'phrases')}")
    для_края = свежий["edges"]
    for имя, край in (("start", для_края["start"]), ("end", для_края["end"])):
        как_стоит = ("on a heard word" if край["measured"]
                     else "estimated, the nearest heard word is "
                          f"{report.счёт(край['far'], 'word', 'words')} away")
        report.скажи(f"  {имя}: phrase {край['phrase']}, "
                     f"{pick.show_time(край['at'])} — {как_стоит}")
    if not свежий["edges"]["start"]["measured"]:
        report.скажи("  the start is estimated — listen to it before you "
                     "publish")
    целая = pick.pieces(свежий)[0]
    if целая["words"]["first"] != 0 and not _с_начала_фразы(laid, целая):
        report.скажи("  the clip starts in the MIDDLE of a phrase — that's "
                     "allowed, but the first word comes mid-thought")


def _с_начала_фразы(laid: dict, кусок: dict) -> bool:
    from . import speech
    return speech.с_начала_фразы(laid, кусок["words"]["first"])


def _cuts(args) -> None:
    """Что выбрано и что собрано. Читает голый json."""
    from . import layout, pick, render

    папка = layout.project(args.слаг)
    if not папка.exists():
        raise VertcutError(f"No such video: {args.слаг}",
                           hint="to see your videos, run: vertcut videos")
    ролики = pick.listing(папка)
    if not ролики:
        report.скажи("No clips picked yet.")
        report.скажи(f"Pick one: vertcut pick {args.слаг} --range 12-16")
        return
    for cut in ролики:
        # Стиль вертикалки не читается (испорчен или старого образца) —
        # список выбранного всё равно нужен: это ровно та минута, когда
        # человек смотрит, что у него есть. Отказ встаёт на место
        # причины, а не роняет весь список.
        try:
            причина = render.почему_устарел(папка, cut)
        except VertcutError as беда:
            причина = беда.message.splitlines()[0]
        report.скажи(f"\n{pick.зовут(cut)}")
        куски = pick.pieces(cut)
        фразы = " + ".join(f"{к['phrases']['first']}–{к['phrases']['last']}"
                           for к in куски)
        report.скажи(f"  {cut['duration']:.1f} s · phrases {фразы} · "
                     f"clip id {cut['id']}")
        report.скажи(f"  file: {cut.get('файл', '—')}"
                     + ("" if причина is None else f"   ({причина})"))


def _title(args) -> None:
    from . import layout, pick, rename

    папка = layout.project(args.слаг)
    было = pick.зовут(pick.load(папка, args.ключ))
    стало = rename.set_title(папка, args.ключ, args.название)
    report.скажи(f"was:  {было}")
    report.скажи(f"now:  {pick.зовут(стало)}")
    report.скажи(f"file: {стало.get('файл')}")


def _frame(args) -> None:
    """Рамка рукой. Машина предлагает, рука сильнее."""
    from . import pick, plans, shots as планы

    папка, meta, _ = _открыть(args.слаг)
    cut = pick.load(папка, args.ключ)
    стало = plans.поставить_рамку(
        cut, args.план, cx=args.рамка,
        режим=plans.РЕЖИМ_ПО_СЛОВУ[args.режим] if args.режим else None,
        сбросить=args.сбросить, планов=len(планы.read(папка)))
    if args.сбросить:
        report.скажи(f"shot {args.план}: back to the crop Vertcut "
                     "suggested")
    else:
        # Словами, а не словарём питона: до 24-й сессии печаталось
        # «shot 1: {'cx': 0.3}».
        части = []
        if "mode" in стало:
            части.append(plans.ИМЯ_РЕЖИМА[стало["mode"]])
        if "cx" in стало:
            части.append(f"crop center at {стало['cx']:.2f} of the width")
        report.скажи(f"shot {args.план}: {', '.join(части)}, by hand")
    pick.update(папка, cut)
    report.скажи("the exported file is now out of date — export again: "
                 f"vertcut render {args.слаг} {args.ключ}")


def _plans(args) -> None:
    from . import pick, plans, shots as планы

    папка, meta, _ = _открыть(args.слаг)
    cut = pick.load(папка, args.ключ)
    найдено = планы.read(папка)
    ряды = plans.montage(папка, meta, cut, найдено)
    планы.write(найдено, папка)

    report.скажи(f"\n{pick.зовут(cut)}   "
                 f"{report.счёт(len(ряды), 'shot', 'shots')}")
    report.скажи("   shot      at       length  frame        crop")
    for ряд in ряды:
        чья = "by hand" if ряд.get("hand") else (ряд.get("by") or "—")
        report.скажи(f"  {ряд['idx']:>5}   {ряд['at']:>6.2f} s  "
                     f"{ряд['duration']:>5.2f} s  "
                     f"{plans.ИМЯ_РЕЖИМА[ряд['mode']]:<12} "
                     f"{ряд['cx']:.4f} ({чья})")
    огрызки = plans.stubs(ряды)
    if огрызки:
        report.скажи("")
        for ряд in огрызки:
            report.скажи(f"  partial shot: shot {ряд['idx']} is on screen "
                         f"for {ряд['duration']:.2f} s — viewers see the end "
                         "of a scene without its beginning")
    if args.лист:
        свои = [{**s, "crop_cx": r["cx"], "crop_by": ("hand" if r.get("hand")
                                                      else s.get("crop_by"))}
                for r in ряды
                for s in найдено if s["idx"] == r["idx"]]
        страницы = планы.sheets(
            свои, папка,
            namer=lambda p, n: __import__("vertcut.layout", fromlist=["x"])
            .cut_sheet(p, cut["id"], n),
            рисовать_рамку=True)
        report.скажи(f"  sheet: {страницы[0]}")


def _text(args) -> None:
    """Правка фраз рукой: разделить, склеить, поправить текст.

    **Человек называет номер фразы, а на диск ложатся номера слов.**
    Та же дорога, что у выбора куска: номера фраз переезжают при
    перенарезке, номера слов — нет. Перевод делается здесь, один раз,
    в момент записи.
    """
    from . import edits, pick, speech

    папка, meta, laid = _открыть(args.слаг)
    cut = pick.load(папка, args.ключ)
    правки = edits.список(cut)

    if args.сбросить:
        если = (None, None) if args.фраза is None else _слова_фразы(
            laid, args.фраза)
        снято = edits.снять(cut, *если)
        pick.update(папка, cut)
        report.скажи(f"edits removed: {снято}")
        _показать_правки(cut)
        return

    сколько = sum(x is not None and x is not False
                  for x in (args.текст, args.разделить,
                            args.склеить or None))
    if сколько == 0:
        _показать_правки(cut)
        return
    if сколько > 1:
        raise VertcutError(
            "One edit at a time: text, split or merge",
            hint="run the command once for each")
    if args.фраза is None:
        raise VertcutError("Which phrase? Give --phrase N",
                           hint="the phrase numbers: "
                                f"vertcut phrases {args.слаг}")

    с, по = _слова_фразы(laid, args.фраза)
    if args.текст is not None:
        правка = edits.поправить_текст(cut, с, по, args.текст)
    elif args.разделить is not None:
        если = args.разделить
        if если < 1 or с + если - 1 >= по:
            raise VertcutError(
                f"Phrase {args.фраза} has {по - с + 1} words, and the split "
                f"is asked after word {если}.",
                hint="counting starts at 1, and there is nothing to split "
                     "after the last word")
        правка = edits.разделить_после(cut, с + если - 1)
    else:
        правка = edits.склеить_после(cut, по)
    pick.update(папка, cut)
    report.скажи(f"saved: {edits.описать(правка)}")
    report.скажи("  the transcript is untouched — the edit changes only "
                 "this clip's subtitles")
    _показать_правки(cut)


def _слова_фразы(laid: dict, номер: int) -> tuple[int, int]:
    from . import speech
    return speech.слова_фразы(laid, номер)


def _показать_правки(cut) -> None:
    from . import edits

    правки = edits.список(cut)
    if not правки:
        report.скажи("no phrase edits")
        return
    report.скажи(f"phrase edits: {len(правки)}")
    for правка in правки:
        report.скажи(f"  {edits.описать(правка)}")


def _subs(args) -> None:
    from . import (phrases as segmentation, pick, plans,
                   shots as планы, subs)

    from . import render

    папка, meta, laid = _открыть(args.слаг)
    if args.в_файле is not None:
        cut = pick.load(папка, args.ключ)
        subs.задать_в_файле(папка, cut, args.в_файле)
        pick.update(папка, cut)
        причина = render.почему_устарел(папка, cut)
        report.скажи(("Subtitles are on" if args.в_файле else
                      "This clip now exports without subtitles")
                     + (f". Out of date — export again ({причина})."
                        if причина and cut.get("render") else "."))
        return
    всё = render.открыть_ролик(папка, meta, args.ключ)
    cut, prof, шрифт, раскл = (всё["cut"], всё["prof"], всё["шрифт"],
                               всё["раскл"])
    if not subs.в_файле(папка, cut):
        report.скажи("\nSUBTITLES ARE OFF for this clip: it exports without "
                     f"them. Turn them on: vertcut subs {args.слаг} "
                     f"{args.ключ} --on")

    report.скажи(f"\n{pick.зовут(cut)}   "
                 f"{report.счёт(len(раскл['фразы']), 'phrase', 'phrases')}, "
                 f"{report.счёт(len(раскл['показы']), 'state', 'states')}")
    # Где стоит фраза — слово раскладки, русское; человеку — словами.
    где_словом = {subs.ЦЕНТР: "middle", subs.НИЗ: "bottom"}
    for ф in раскл["фразы"]:
        # Текст печатается ЗДЕСЬ, а не только числа: это тот список,
        # по которому человек правит субтитры руками, и править их
        # вслепую нельзя.
        текст = segmentation.join_words(w["w"] for w in ф["words"])
        # «Не влезает» — не поломка, а сведение: длинную фразу субтитр
        # показывает страницами. Сказано это ЗДЕСЬ, а не в списке фраз
        # видео: только здесь известен стиль, а без стиля ответить
        # на вопрос «влезает ли» нечем.
        метки = []
        if not ф["влезает"]:
            метки.append(report.счёт(len(ф['страницы']), 'page', 'pages'))
        if ф.get("правлено"):
            метки.append("edited")
        хвост = ("   ← " + ", ".join(метки)) if метки else ""
        report.скажи(f"  phrase {ф['idx']:>3}  {ф['at']:>6.2f}–{ф['till']:>6.2f} s"
                     f"  {где_словом.get(ф['где'], ф['где']):<6} "
                     f"lines {len(ф['страницы'])}×"
                     f"{[len(с) for с in ф['страницы']]}  {текст}{хвост}")
    for строка in раскл["подрезано"]:
        report.скажи(f"  {строка}")
    if раскл["частями"]:
        report.скажи(f"  {раскл['частями']}")
    for жалоба in раскл["жалобы"]:
        report.скажи(f"  ! {жалоба}")
    if args.лист:
        from . import layout
        путь = subs.лист(раскл, prof, шрифт,
                         layout.cut_subs_sheet(папка, cut["id"]))
        report.скажи(f"  sheet: {путь}")


def _plate(args) -> None:
    """Плашка в конце: поставить обложку и фон, собрать, показать числами.

    **Настройка, которую нельзя показать кадром, не сделана** — правило
    проекта. «Кегль 0.0954» не значит ничего, пока не видно, что из
    этого выйдет; поэтому команда не только печатает числа, но и кладёт
    собранную картинку рядом с роликом.
    """
    from . import layout, pick, plate, render, subs

    папка, meta, _ = _открыть(args.слаг)

    if args.снять_обложку:
        было = plate.убрать_обложку(папка)
        report.скажи("thumbnail removed" if было
                     else "there was no thumbnail")
    if args.обложка:
        сделано = plate.поставить_обложку(папка, Path(args.обложка))
        было = сделано["было"]
        report.скажи(
            f"thumbnail: {сделано['размер'][0]}×{сделано['размер'][1]}, "
            f"{сделано['мегабайт']} MB → {сделано['файл']}"
            + (f"\n  replaced (was {было['размер'][0]}×{было['размер'][1]})"
               if было else ""))
    if args.фон:
        куда = plate.поставить_фон(Path(args.фон))
        report.скажи(f"background image copied: {куда}")
        # Файл стиля — тот, что читает сказанная вертикалка: свой, если
        # он у неё есть. Раньше фон всегда ложился в стиль видео, и у
        # вертикалки со своим стилем он молча оставался «none».
        стиль = subs.файл(папка, args.ключ)
        subs.задать(стиль, {"end_card.image": куда.name})
        report.скажи(f"  and used: end_card.image = {куда.name} in {стиль}")

    ролики = pick.listing(папка)
    if not ролики:
        report.скажи("\nno clips yet — there is nothing to show the end "
                     "card on")
        return
    ключ = args.ключ or ролики[0]["id"]

    if args.текст is not None:
        cut = pick.load(папка, ключ)
        plate.задать_текст(cut, args.текст)
        pick.update(папка, cut)
        report.скажи(f"end card text of {pick.зовут(cut)}: "
                     + (repr(args.текст) if args.текст.strip()
                        else "its own is gone, the default is used"))

    всё = render.открыть_ролик(папка, meta, ключ)
    это = plate.сырые(папка, ключ)
    if not plate.включена(это):
        report.скажи("\nthe end card is OFF — clips are exported "
                     "without it.")
        report.скажи(f"  turn it on: vertcut style {args.слаг} "
                     "--set end_card.show=true")
        return

    сделано = plate.собрать_у(папка, всё["cut"], всё["prof"])
    ш, в = сделано["кадр"]["w"], сделано["кадр"]["h"]
    report.скажи(f"\n{pick.зовут(всё['cut'])}   frame {ш}×{в}")
    report.скажи(f"  end card: the last {plate.секунды(это)} s of the file")
    report.скажи(f"  background image: {сделано['фон']}")
    if сделано["обложка"]:
        о = сделано["обложка"]
        report.скажи(f"  thumbnail: {о['w']}×{о['h']} at ({о['x']}, {о['y']}), "
                     f"from {о['размер'][0]}×{о['размер'][1]}")
    н = сделано["надпись"]
    report.скажи(f"  end card text: size {н['кегль']}"
                 + ("" if н["кегль"] == н["просили"]
                    else f" (asked for {н['просили']} — it didn't fit)")
                 + f", lines {н['верх']}…{н['низ']}")
    for строка in н["строки"]:
        report.скажи(f"    {строка['лев']:>4}…{строка['прав']:<4} "
                     f"baseline {строка['базовая']}  {строка['текст']}")
    полоса = сделано["полоса"]
    report.скажи(f"  subtitle area: {полоса['верх']}…{полоса['низ']} "
                 f"({report.счёт(полоса['строк'], 'line', 'lines')}) — "
                 "set by the style")
    if сделано["просвет"] is not None:
        report.скажи(f"  between the thumbnail and the text: "
                     f"{сделано['просвет']} px")
    # Имена зазоров — ключи словаря плашки, русские; человеку — словами.
    что_это = {"надпись": "end card text", "обложка": "thumbnail"}
    сторона = {"слева": "left", "справа": "right", "сверху": "top",
               "снизу": "bottom", "до_полосы": "to the subtitle area"}
    for имя, зазор in сделано["зазоры"].items():
        report.скажи(f"  gaps around the {что_это.get(имя, имя)}: "
                     + ", ".join(f"{сторона.get(к, к)} {з}"
                                 for к, з in зазор.items()))
    for жалоба in сделано["жалобы"]:
        report.скажи(f"  ! {жалоба}")
    report.скажи(f"  picture: {сделано['файл']}")


def _fonts(args) -> None:
    """Какие шрифты есть: в поставке, свои и что они умеют.

    Печатает и то, сколько знаков шрифт знает: чужой шрифт может
    не знать кириллицы, и узнать об этом надо ДО того, как он встанет
    в ролик квадратиками.
    """
    from . import fonts, layout

    report.скажи("come with Vertcut:")
    for шрифт in fonts.набор():
        if not шрифт["есть"]:
            report.скажи(f"  {шрифт['файл']:<18} — the file is missing!")
            continue
        св = fonts.сведения(шрифт["путь"])
        оси = ", ".join(св["оси"]) or "no axes"
        report.скажи(f"  {шрифт['файл']:<18} {шрифт['какой']}")
        report.скажи(f"  {'':<18} {св['знаков']} characters, {оси}, "
                     f"license {шрифт['лицензия']}")

    своя = layout.my_fonts()
    свои = sorted(своя.glob("*.[to]t[tfc]")) if своя.exists() else []
    report.скажи(f"\nyours ({своя}):")
    if not свои:
        report.скажи("  none — add one: "
                     "vertcut style VIDEO_ID --font /path/to/file.ttf")
        return
    for путь in свои:
        try:
            св = fonts.сведения(путь)
            report.скажи(f"  {путь.name:<18} {св['знаков']} characters, "
                         f"{св['гарнитура']}")
        except VertcutError as беда:
            report.скажи(f"  {путь.name:<18} — can't be read: {беда.message}")


def _looks(args) -> None:
    """Готовые виды: какие есть, чем отличаются и чего стоят.

    **Цена вида названа числом.** Крупные буквы значат, что в строку
    влезает меньше, и часть фраз начинает перелистываться посреди себя.
    Узнать это человек должен здесь, а не на своём первом видео.
    """
    from . import layout, subs

    if args.слаг:
        _замерить_виды(args.слаг)
        return

    личный = layout.my_subs()
    if личный.exists():
        report.скажи(f"{'my style':<14}— the style you saved as yours\n"
                     f"{'':14}  {личный}\n"
                     f"{'':14}  use it: vertcut style VIDEO_ID --my-style\n")

    for имя, вид in subs.виды().items():
        числа = ", ".join(f"{к} {з}" for к, з in вид["числа"].items())
        report.скажи(f"{имя:<14}— {вид['зачем']}")
        if числа:
            report.скажи(f"{'':14}  {числа}")
        цена = ", ".join(f"{к} {з:.0%}" for к, з in вид["цена"].items())
        report.скажи(f"{'':14}  phrases that need two pages: {цена}")
    report.скажи("\nuse one: vertcut style VIDEO_ID --preset large")
    report.скажи("save as yours: vertcut style VIDEO_ID --save-as-my-style")
    report.скажи("measure them on your video: vertcut looks VIDEO_ID")


def _замерить_виды(слаг: str) -> None:
    """Перемерить цену каждого вида на настоящем видео.

    **Замер живёт в сервисе, а не в черновом скрипте.** Второй раз
    подряд записанное однажды число не сошлось с пересчётом — сперва
    у предка, потом у нас. Число, которое нельзя перемерить одной
    командой, через полгода становится преданием.
    """
    from . import layout, speech, subs

    папка = layout.project(слаг)
    if not папка.exists():
        raise VertcutError(f"No such video: {слаг}",
                           hint="to see your videos, run: vertcut videos")
    laid = speech.read(папка)
    основа = subs.образец()
    report.скажи(f"phrases that need two pages on “{слаг}”:\n")
    не_влезает = "don't fit"
    report.скажи(f"  {'preset':<14}{не_влезает:>12}   recorded")
    for имя, вид in subs.виды().items():
        числа = {**основа}
        for ключ, значение in вид["числа"].items():
            где, части = числа, ключ.split(".")
            for часть in части[:-1]:
                где[часть] = dict(где[часть])
                где = где[часть]
            где[части[-1]] = значение
        prof = subs.к_пикселям(числа)
        итог = subs.перелистывания(laid, prof, subs.font_of(prof))
        было = ", ".join(f"{к} {з:.0%}" for к, з in вид["цена"].items())
        report.скажи(f"  {имя:<14}{итог['не_влезли']:>4} of "
                     f"{итог['фраз']:<4}{итог['доля']:>4.0%}   {было}")
    report.скажи("\nif it differs from what is recorded, the preset's "
                 "numbers changed and its cost wasn't measured again: fix "
                 "it in assets/looks.yaml")


def _style(args) -> None:
    """Стиль субтитров: чей он у этого видео, какой он и как выглядит.

    Три уровня — поставляемый, личный, копия в видео, — две кнопки
    из спеки («взять мой стиль» и «сделать этот стиль моим»), правка
    чисел и лист на настоящем кадре.

    **Лист рисуется ДО и ПОСЛЕ одной картинкой.** Настройка, которую
    нельзя показать кадром, не настроена: «кегль 0.05» не значит
    ничего, пока не видно, что из этого выйдет на кадре видео.
    """
    import shutil
    from copy import deepcopy

    from . import layout, subs

    папка = layout.project(args.слаг)
    if not папка.exists():
        raise VertcutError(f"No such video: {args.слаг}",
                           hint="to see your videos, run: vertcut videos")

    дороги = [args.мой, args.сделать_моим, args.поставляемый,
              bool(args.задать) or bool(args.шрифт)
              or bool(args.регистр) or bool(args.подложка)
              or bool(args.подсветка) or bool(args.чем)
              or bool(args.от_низа) or bool(args.поля) or bool(args.беречь)
              or bool(args.вид)]
    if sum(дороги) > 1:
        raise VertcutError(
            "Give ONE: --my-style, --save-as-my-style, --default-style "
            "or a change such as --set",
            hint="Vertcut won't decide for you which one wins")

    subs.завести(папка)
    # Сказан ключ ролика — правится стиль ЭТОЙ вертикалки, а не всего
    # видео. Уровней стиля четыре, и четвёртый заводится первой же
    # правкой; команда и экран делают тут одно и то же, иначе они
    # разошлись бы в том, чей стиль человек только что поменял.
    if args.всем:
        if not args.ключ:
            raise VertcutError(
                "Which clip's style? Give its clip id",
                hint=f"vertcut style {args.слаг} CLIP_ID --apply-to-all")
        убрано = subs.применить_ко_всем(папка, args.ключ)
        report.скажи(f"the style of clip {args.ключ} is now this video's "
                     "style")
        report.скажи(f"  other clips' own styles removed: {убрано}")
        report.скажи("  exported clips whose style changed will show as "
                     "out of date")
        _стиль_показать(папка)
        return

    правим = args.ключ if (args.ключ and _правит_стиль(args)) else None
    куда = (subs.завести_свой(папка, правим) if правим
            else layout.project_subs(папка))
    # Читаем «как было» мягко: испорченный профиль не должен мешать
    # его же и починить — иначе человек с одной опечаткой в файле
    # остаётся без команды, которой он эту опечатку убирает.
    #
    # Читается стиль сказанной вертикалки, а не стиль видео, даже когда
    # команда только показывает: раньше `style {слаг} {ключ} --sheet`
    # рисовал вертикалке со своим стилем стиль видео — чужие числа
    # под её ключом.
    было = deepcopy(_числа_как_есть(папка, args.ключ))

    if args.сделать_моим:
        _стиль_сделать_моим(папка)
    elif args.мой:
        _стиль_взять_мой(папка, было, куда, правим)
    elif args.поставляемый:
        _стиль_вернуть_поставляемый(папка, было, куда, правим)
    elif (args.задать or args.шрифт or args.регистр or args.подложка
          or args.подсветка or args.чем or args.от_низа or args.поля
          or args.беречь or args.вид):
        правки = {}
        if args.вид:
            # Вид кладётся поверх ПОСТАВЛЯЕМОГО, а не поверх нынешнего.
            #
            # Иначе «взять готовый вид» значило бы разное в зависимости
            # от того, что человек трогал раньше: вид «обычный» (он же
            # поставляемый, и чисел в нём нет вовсе) не менял бы ничего,
            # а «крупный» оставлял бы чужой шрифт от прошлой правки.
            # Готовый вид должен давать ровно то, что показано.
            числа = subs.взять_вид(args.вид)
            shutil.copy2(layout.subs_yaml(), куда)
            subs.сбросить_кэш()
            правки.update(числа)
        правки.update(_разобрать_правки(args.задать or []))
        if args.шрифт:
            правки["font"] = _подключить_шрифт(args.шрифт)
        if args.регистр:
            правки["case"] = args.регистр
        if args.подложка:
            правки["background"] = args.подложка
        if args.подсветка:
            правки["karaoke.mode"] = args.подсветка
        if args.чем:
            правки["karaoke.by"] = args.чем
        if args.от_низа:
            правки["position.from_bottom"] = args.от_низа
        if args.поля:
            правки["safe_zones.side"] = args.поля
        if args.беречь:
            правки["safe_zones.enabled"] = ("true" if args.беречь == "on"
                                            else "false")
        сказано = subs.задать(куда, правки)
        if args.вид:
            report.скажи(f"preset “{args.вид}” used — it goes on top of "
                         "the default style, not on top of the old one")
        subs.сбросить_кэш()
        _сказать_разницу(было, subs.settings(папка, правим),
                         "changed" if not args.вид else "now")

    subs.сбросить_кэш()
    стало = subs.settings(папка, args.ключ)
    _стиль_показать(папка, args.ключ)
    if правим:
        report.скажи(f"  changed the style of CLIP {правим}, not of the "
                     "whole video\n  give it to the other clips: "
                     f"vertcut style {args.слаг} {правим} --apply-to-all")

    if args.лист or args.зоны:
        _стиль_лист(папка, args.ключ, было, стало, args.зоны)


def _правит_стиль(args) -> bool:
    """Правит ли эта команда стиль, или только показывает его.

    Ключ ролика у `style` значит две разные вещи: для листа — какой
    ролик рисовать, для правки — чей стиль менять. Показ ничего
    не меняет, и заводить вертикалке свой стиль на нём нельзя: человек
    попросил посмотреть, а не отделиться.
    """
    return bool(args.задать or args.шрифт or args.регистр or args.подложка
                or args.подсветка or args.чем or args.от_низа or args.поля
                or args.беречь or args.вид or args.мой or args.поставляемый)


def _разобрать_правки(куски: list[str]) -> dict:
    """`--set size=0.05` → {«size»: «0.05»}.

    Знак равенства, а не пробел: `--set box.color #E8E5E9`
    оболочка съела бы вместе с решёткой, приняв её за примечание.
    """
    правки = {}
    for кусок in куски:
        if "=" not in кусок:
            raise VertcutError(
                f"A change is written with an equals sign, but got: {кусок}",
                hint="for example: --set size=0.05")
        ключ, значение = кусок.split("=", 1)
        правки[ключ.strip()] = значение
    return правки


def _подключить_шрифт(что: str) -> str:
    """Имя шрифта для профиля. Свой файл по дороге ложится к себе.

    **Копируется, а не запоминается путём.** Путь на рабочий стол
    через месяц ведёт в пустоту, и ролик соберётся без букв.
    """
    from pathlib import Path

    from . import fonts

    как_есть = Path(что).expanduser()
    if len(как_есть.parts) > 1 or как_есть.suffix.lower() in (
            ".ttf", ".otf", ".ttc"):
        if как_есть.exists():
            куда = fonts.поставить(как_есть)
            if куда != как_есть:
                report.скажи(f"font copied to your fonts: {куда}")
            return куда.name
    # Голое имя — пусть его ищет тот, кто умеет искать во всех трёх
    # местах. Здесь только проверка, что он найдётся.
    fonts.найти(что)
    return что


def _стиль_показать(папка, ключ=None) -> None:
    from . import layout, pick, render, subs

    путь, откуда = subs.завести(папка)
    если = subs.чей(папка)
    # Сказан ключ и у вертикалки свой стиль — показывается ЕЁ стиль,
    # а не стиль видео. Показать чужие числа под правильным заголовком
    # хуже, чем не показать никаких.
    свой_у_ролика = bool(ключ) and subs.свой_ли(папка, ключ)
    if свой_у_ролика:
        путь = layout.cut_subs(папка, ключ)
    report.скажи(f"\nsubtitle style: {путь}")
    if свой_у_ролика:
        report.скажи(f"  this is the style of CLIP {ключ}, not of the whole "
                     "video")
    if откуда != subs.СВОЙ:
        report.скажи(f"  copied just now from: {откуда}")
    if свой_у_ролика:
        pass          # про совпадения ниже сказано про видео, а тут ролик
    elif если["как_поставляемый"]:
        report.скажи("  same as the default style")
    elif если["как_личный"]:
        report.скажи("  same as my style")
    elif если["личный_есть"]:
        report.скажи("  differs from both the default style and my style")
    else:
        report.скажи("  differs from the default style; my style isn't "
                     "saved yet")
    report.скажи(f"  my style: {layout.my_subs()}"
                 f"{'' if если['личный_есть'] else '  — not saved yet'}")

    prof = subs.profile(папка, ident=ключ)
    про = subs.про_шрифт(prof)
    report.скажи(f"\nnumbers for a {prof['width']}×{prof['height']} frame:")
    report.скажи(f"  font            {prof['шрифт'].name} "
                 f"({про['гарнитура']}), {про['знаков']} characters")
    if про["вес_выставлен"]:
        report.скажи(f"  weight          {prof['вес']}")
    else:
        # Молчать нельзя: человек будет двигать число и не понимать,
        # почему ничего не меняется.
        report.скажи(f"  weight          {prof['вес']} — NOT SET: this font "
                     "has no weight setting, the file itself decides")
    report.скажи(f"  case            {prof['регистр']}")
    report.скажи(f"  size            {prof['кегль']} px")
    report.скажи(f"  line spacing    {prof['шаг']} px, "
                 f"at most {report.счёт(prof['максимум_строк'], 'line', 'lines')}")
    report.скажи(f"  background      {prof['подложка']}")
    if prof["подложка"] == subs.ПЛАШКА:
        report.скажи(f"  box             height {prof['высота_плашки']}, "
                     f"side padding {prof['поле_сбоку']}, color {prof['цвет']}")
    elif prof["подложка"] == subs.ОБВОДКА:
        report.скажи(f"  outline         {prof['обводка_толщина']} px, "
                     f"color {prof['обводка_цвет']}")
    elif prof["подложка"] == subs.ТЕНЬ:
        report.скажи(f"  shadow          offset {prof['тень_сдвиг']} px "
                     f"right and down, color {prof['тень_цвет']}")
    report.скажи(f"  text color      spoken {prof['сказанное']}, "
                 f"upcoming {prof['несказанное']}")
    if prof["подсветка"] == subs.НЕТ_ПОДСВЕТКИ:
        report.скажи("  karaoke         none")
    else:
        крупнее = (f", {prof['подсветка_крупнее']} times larger"
                   if prof["подсветка_чем"] == subs.КЕГЛЕМ else "")
        report.скажи(f"  karaoke         {prof['подсветка']}, "
                     f"by {prof['подсветка_чем']} {prof['подсветка_цвет']}"
                     f"{крупнее}")
    беда = subs.жалоба_на_контраст(prof)
    if беда:
        report.скажи(f"  ! {беда}")
    report.скажи(f"  line width      at most {prof['предел_плашки']} px, "
                 f"{prof['предел_текста']} px for the letters")
    если = "on" if prof["беречь_зоны"] else "OFF"
    report.скажи(f"  safe zones      {если}: side {prof['зона_сбоку']}, "
                 f"bottom {prof['зона_снизу']}, top {prof['зона_сверху']}")
    от_низа = prof["height"] - prof["низ_центра"]
    report.скажи(f"  subtitle        bottom at {от_низа} from the bottom of "
                 f"the frame (row {prof['низ_центра']} from the top)")
    if prof["упёрся_вниз"] or prof["упёрся_вверх"]:
        куда = "bottom" if prof["упёрся_вниз"] else "top"
        report.скажи(f"  ! stopped at the {куда} safe zone: asked for "
                     f"{prof['height'] - prof['низ_хотели']} from the bottom")
    report.скажи(f"  under the shot  gap {prof['отступ_от_плана']}, "
                 f"never lower than {prof['предел_низа']}")

    # Что теперь надо пересобрать. Отпечаток профиля входит в штамп
    # сборки, и человек обязан видеть цену правки стиля СРАЗУ, а не
    # обнаружить её очередью на двадцать роликов.
    ролики = pick.listing(папка)
    устарели = [c for c in ролики
                if render.почему_устарел(папка, c) == render.ПРОФИЛЬ_ПОМЕНЯЛСЯ]
    if устарели:
        report.скажи(f"\nout of date because of the style: "
                     f"{len(устарели)} of "
                     f"{report.счёт(len(ролики), 'clip', 'clips')}")
        for cut in устарели:
            report.скажи(f"  {pick.зовут(cut)}")
        report.скажи(f"export again: vertcut queue {папка.name} --export")


def _стиль_лист(папка, ключ, было, стало: dict,
                показать_зоны: bool = False) -> None:
    """Лист на настоящих кадрах: что было и что стало.

    Кадры берутся из самого видео и кадрируются тем же монтажом,
    каким их вырежет сборка. Серый лист (`vertcut subs --sheet`)
    отвечает на вопрос «как разложился текст»; этот — на вопрос
    «как это выглядит».
    """
    from . import (ingest, layout, pick, plans, preview, render,
                   shots as планы, speech, subs)

    if ключ is None:
        raise VertcutError(
            "The sheet is drawn for a clip — give its clip id",
            hint=f"your clips: vertcut cuts {папка.name}")
    meta = ingest.read_meta(папка)
    laid = speech.read(папка)
    cut = pick.load(папка, ключ)
    ряды = plans.montage(папка, meta, cut, планы.read(папка))
    источник = render.проверить_исходник(meta)

    # Один столбец, если ничего не менялось: «до и после» на одинаковых
    # картинках — это не ответ, а два одинаковых кадра рядом.
    # Подписи столбцов рисуются НА КАРТИНКЕ, а её видно на экране
    # редактора — поэтому они английские раньше остальной команды.
    пары = ([("before", было), ("after", стало)] if было != стало
            else [("now", стало)])
    столбцы = []
    for имя, числа in пары:
        # Тот же сборщик, что у сборки и у экрана, — только профиль
        # подсунут снаружи: второго на диске нет, он ещё только
        # обдумывается человеком.
        всё = render.открыть_ролик(папка, meta, cut, ряды=ряды, laid=laid,
                                   prof=subs.к_пикселям(числа))
        столбцы.append({
            "имя": имя, "prof": всё["prof"], "шрифт": всё["шрифт"],
            "зоны": показать_зоны, "раскл": всё["раскл"],
        })

    куда = layout.cut_style_sheet(папка, cut["id"])
    preview.лист(папка, meta, cut, ряды, источник, куда, столбцы)
    report.скажи(f"\nsheet: {куда}")


def _стиль_взять_мой(папка, было, куда, ключ=None) -> None:
    """«Взять мой стиль»: личный образец ложится копией в это видео —
    или в стиль сказанной вертикалки (`куда`)."""
    import shutil

    from . import layout, subs

    личный = layout.my_subs()
    if not личный.exists():
        raise VertcutError(
            "My style isn't saved yet — there is nothing to use.",
            hint="save this video's style as yours: "
                 f"vertcut style {папка.name} --save-as-my-style")
    # Старый образец (до английских ключей) не копируется: копия
    # не читалась бы, и отказ назвал бы не тот файл.
    subs.из_файла(личный)
    shutil.copy2(личный, куда)
    subs.сбросить_кэш()
    стало = subs.settings(папка, ключ)
    _сказать_разницу(было, стало, "my style used")


def _стиль_сделать_моим(папка) -> None:
    """«Сделать этот стиль моим»: копия видео ложится личным образцом.

    **Правка личного образца не устаревает ничего**, и это не побочный
    эффект, а то, ради чего уровней три: у каждого видео своя копия,
    и до неё чужая правка не дотягивается.
    """
    import shutil

    from . import layout, subs

    откуда, _ = subs.завести(папка)
    личный = layout.my_subs()
    было = subs.из_файла(личный) if личный.exists() else None
    личный.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(откуда, личный)
    subs.сбросить_кэш()
    стало = subs.из_файла(личный)
    if было is None:
        report.скажи(f"my style saved: {личный}")
    else:
        _сказать_разницу(было, стало, f"my style rewritten: {личный}")
    report.скажи("  exported clips are still up to date: every video keeps "
                 "its own copy of the style")


def _стиль_вернуть_поставляемый(папка, было, куда, ключ=None) -> None:
    """Вернуть поставляемый образец в это видео — или в стиль
    сказанной вертикалки (`куда`)."""
    import shutil

    from . import layout, subs

    shutil.copy2(layout.subs_yaml(), куда)
    subs.сбросить_кэш()
    стало = subs.settings(папка, ключ)
    _сказать_разницу(было, стало, "back to the default style")


def _числа_как_есть(папка, ключ=None):
    """Числа профиля — или None, если он испорчен.

    **Испорченный профиль не должен мешать его починить.** Обе кнопки,
    которые кладут в видео другой профиль, читают старый только затем,
    чтобы сказать, что поменялось. Ронять на этом чтении команду,
    которой человек как раз и чинит файл, — способ загнать его в угол.
    """
    from . import subs

    try:
        return subs.settings(папка, ключ)
    except VertcutError as беда:
        первая = беда.message.splitlines()[0]
        report.скажи(f"the old style can't be read ({первая})")
        return None


def _сказать_разницу(было, стало: dict, заголовок: str) -> None:
    from . import subs

    if было is None:
        report.скажи(f"{заголовок}")
        return
    строки = subs.разница(было, стало)
    if not строки:
        report.скажи(f"{заголовок}: the numbers are the same, nothing "
                     "to change")
        return
    report.скажи(f"{заголовок}, "
                 f"{report.счёт(len(строки), 'change', 'changes')}:")
    for строка in строки:
        report.скажи(f"  {строка}")


def _render(args) -> None:
    from . import render

    папка, meta, _ = _открыть(args.слаг)
    вышло = render.run_all(папка, meta, args.ключ, заново=args.заново)
    report.скажи(f"\nexported: {report.счёт(len(вышло), 'clip', 'clips')}")


def _queue(args) -> None:
    from . import pick, queue, works

    папка, meta, _ = _открыть(args.слаг)
    for ключ in args.только or []:
        pick.load(папка, ключ)              # нет такой — отказ словами
    if args.собрать:
        состояние = queue.сложить(папка, meta, заново=args.заново)
        if not состояние.get("дела"):
            report.скажи("nothing to export — everything is up to date")
            return
        queue.записать(папка, состояние)
        queue.run(папка, meta, только=args.только)
        return

    очередь = queue.сложить(папка, meta, заново=args.заново)
    queue.записать(папка, очередь)
    дела = очередь.get("дела", [])
    if not дела:
        report.скажи("nothing to export — everything is up to date")
        return
    report.скажи(f"in the queue: {len(дела)}")
    for дело in дела:
        report.скажи(f"  {works.СОСТОЯНИЕ_СЛОВОМ[дело['состояние']]:<10} "
                     f"{дело['зовут']}  — {дело['почему']}")
    report.скажи(f"\nexport: vertcut queue {args.слаг} --export")
