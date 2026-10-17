"""Сборка без субтитров: решение у вертикалки и у видео, не в стиле."""

from __future__ import annotations

import json

from vertcut import config, ingest, layout, pick, render, subs, verify

from tests.test_ingest import видео, только_дорожка  # noqa: F401 — заготовки
from tests.test_render import _видео_с_роликами


def ролик(песочница):
    project, _ = _видео_с_роликами(1)
    return project, pick.listing(project)[0]


def пометить_видео(project, без: bool) -> None:
    meta = json.loads(layout.meta(project).read_text(encoding="utf-8"))
    meta[subs.БЕЗ_СУБТИТРОВ] = без
    layout.meta(project).write_text(json.dumps(meta, ensure_ascii=False),
                                    encoding="utf-8")


# ─── где лежит решение ───────────────────────────────────────────────

def test_по_умолчанию_субтитры_есть(песочница):
    project, cut = ролик(песочница)
    assert subs.в_файле(project, cut)


def test_видео_без_субтитров_решает_за_ролики(песочница):
    project, cut = ролик(песочница)
    пометить_видео(project, True)
    assert not subs.в_файле(project, cut)


def test_ролик_решает_сам_поверх_видео(песочница):
    project, cut = ролик(песочница)
    пометить_видео(project, True)
    subs.задать_в_файле(project, cut, True)
    assert subs.в_файле(project, cut)
    assert cut[subs.СУБТИТРЫ_В_ФАЙЛЕ] is True


def test_решение_как_у_видео_не_лежит_в_ролике(песочница):
    """Совпало с видео — ключа нет: ролик снова идёт за видео."""
    project, cut = ролик(песочница)
    subs.задать_в_файле(project, cut, False)
    assert cut[subs.СУБТИТРЫ_В_ФАЙЛЕ] is False
    subs.задать_в_файле(project, cut, True)
    assert subs.СУБТИТРЫ_В_ФАЙЛЕ not in cut


def test_выключить_субтитры_не_заводит_своего_стиля(песочница):
    """Ради этого решение и не лежит в профиле: «only this clip uses it»
    из-за выключенных субтитров было бы неправдой."""
    project, cut = ролик(песочница)
    subs.задать_в_файле(project, cut, False)
    pick.update(project, cut)
    assert not layout.cut_subs(project, cut["id"]).exists()


# ─── галочка настроек — только новым видео ───────────────────────────

def test_галочка_снятая_не_лежит_в_настройках(песочница):
    config.задать_новые_без_субтитров(True)
    assert config.новые_без_субтитров()
    config.задать_новые_без_субтитров(False)
    assert config.НОВЫЕ_БЕЗ_СУБТИТРОВ not in config.read()


def test_новое_видео_запоминает_галочку(видео):
    config.задать_новые_без_субтитров(True)
    project, meta = ingest.принять(видео, говорить=lambda *_: None)
    assert meta[subs.БЕЗ_СУБТИТРОВ] is True
    assert not subs.у_видео(project)


def test_разобранное_видео_галочка_не_трогает(видео):
    """Поставили галочку после разбора — старое видео не меняется."""
    project, _ = ingest.принять(видео, говорить=lambda *_: None)
    config.задать_новые_без_субтитров(True)
    project, meta = ingest.принять(видео, говорить=lambda *_: None)
    assert subs.БЕЗ_СУБТИТРОВ not in meta
    assert subs.у_видео(project)


def test_разбор_заново_решения_видео_не_теряет(видео):
    config.задать_новые_без_субтитров(True)
    ingest.принять(видео, говорить=lambda *_: None)
    config.задать_новые_без_субтитров(False)
    _, meta = ingest.принять(видео, заново=True, говорить=lambda *_: None)
    assert meta[subs.БЕЗ_СУБТИТРОВ] is True


# ─── штамп и заслоны ─────────────────────────────────────────────────

def собранный(project, cut, субтитры=None):
    """Ролик со штампом и файлом: устареть ему не от чего, кроме того,
    что проверяется."""
    штамп = {"куски": pick.ranges(cut), "montage": {"hand": {}},
             "subs": {"профиль": subs.отпечаток(project=project,
                                                  ident=cut["id"])}}
    if субтитры is not None:
        штамп["субтитры"] = субтитры
    cut["render"] = штамп
    cut["файл"] = "ролик.mp4"
    layout.out(project, cut).parent.mkdir(parents=True, exist_ok=True)
    layout.out(project, cut).write_text("не пусто", encoding="utf-8")
    return cut


def test_выключили_у_собранного_устарел_с_причиной(песочница):
    project, cut = ролик(песочница)
    собранный(project, cut, субтитры=True)
    subs.задать_в_файле(project, cut, False)
    assert render.почему_устарел(project, cut) == render.СУБТИТРЫ_ВЫКЛЮЧЕНЫ


def test_включили_у_собранного_без_них_устарел(песочница):
    project, cut = ролик(песочница)
    subs.задать_в_файле(project, cut, False)
    собранный(project, cut, субтитры=False)
    subs.задать_в_файле(project, cut, True)
    assert render.почему_устарел(project, cut) == render.СУБТИТРЫ_ВКЛЮЧЕНЫ


def test_старый_штамп_без_ключа_значит_были(песочница):
    """Ролики, собранные до этой возможности, не устаревают от неё."""
    project, cut = ролик(песочница)
    собранный(project, cut)
    причина = render.почему_устарел(project, cut)
    assert причина not in (render.СУБТИТРЫ_ВКЛЮЧЕНЫ,
                           render.СУБТИТРЫ_ВЫКЛЮЧЕНЫ)


def test_без_субтитров_текст_и_стиль_не_устаревают(песочница):
    """Их в файле нет — и правка текста файлу ничем не грозит."""
    project, cut = ролик(песочница)
    subs.задать_в_файле(project, cut, False)
    собранный(project, cut, субтитры=False)
    cut["render"]["subs"]["профиль"] = "другой"
    assert render.почему_устарел(project, cut) is None


def test_проверка_субтитров_пропущена_а_не_провалена():
    итоги = verify.итоги({"duration": 10.0, "субтитры": False,
                          "сверка": {"сошлось": True, "худшая": 0.99,
                                     "точек": 3, "порог": 0.9}})
    субтитры = next(и for и in итоги if и["имя"] == "Subtitles")
    assert субтитры["как"] == "skipped"
    assert "off" in субтитры["подробно"]


def test_без_субтитров_цепочка_без_слоя():
    from vertcut import chain

    from tests.test_render import ряды

    цепь = chain.video(ряды((1, 0.0, 10.0, 0.5)), 1920, 1080,
                       вход_субтитров=None, fps=25.0)
    assert "overlay" not in цепь and "[subs]" not in цепь


def test_экран_сборки_знает_про_ролик_без_субтитров(песочница):
    from vertcut import queue

    project, cut = ролик(песочница)
    subs.задать_в_файле(project, cut, False)
    pick.update(project, cut)
    обзор = queue.обзор(project, json.loads(
        layout.meta(project).read_text(encoding="utf-8")))
    assert обзор["ждут"][0]["без_субтитров"] is True


def test_у_собранного_строка_говорит_про_лежащий_файл(песочница):
    """Сняли галочку после сборки — у файла субтитры есть, и строка
    собранного не имеет права сказать «without subtitles»."""
    from vertcut import queue, works

    project, cut = ролик(песочница)
    собранный(project, cut, субтитры=True)
    subs.задать_в_файле(project, cut, False)
    assert queue._без_субтитров(project, cut, works.ГОТОВ) is False
    assert queue._без_субтитров(project, cut, works.ЖДЁТ) is True
