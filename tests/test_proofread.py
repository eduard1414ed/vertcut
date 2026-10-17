"""Вычитка субтитров моделью: модель предлагает, человек решает.

**Ни один тест отсюда в сеть не ходит.** Поставщик подделывается;
проверяется то, что сервис делает с его ответом.
"""

from __future__ import annotations

import json
import os

import pytest

from vertcut import edits, layout, pick, proofread, speech, subs
from vertcut.errors import VertcutError

from tests.test_notes_ai import видео, поставщик


def ролик(песочница):
    """Видео с одной вертикалкой: фразы 1–12, по четыре слова."""
    project, laid = видео(песочница, 1)
    return project, laid, pick.listing(project)[0]["id"]


def строки(project, ключ) -> list[dict]:
    return proofread._фразы(speech.read(project), pick.load(project, ключ))


def ответ_про(*правки) -> str:
    return json.dumps({"правки": [
        {"строка": с, "стало": стало, "почему": "ослышка"}
        for с, стало in правки]}, ensure_ascii=False)


# ─── что уезжает ─────────────────────────────────────────────────────

def test_модели_уезжают_строки_ролика_с_номерами(песочница, monkeypatch):
    """Номер строки — её слова; по нему правка и вернётся."""
    project, _, ключ = ролик(песочница)
    видел = поставщик(monkeypatch, ответ_про())
    proofread.спросить(project, ключ)
    текст = json.loads(видел.видел.data.decode("utf-8"))["messages"][0]["content"]
    for ф in строки(project, ключ):
        assert f'[{ф["строка"]}] {ф["текст"]}' in текст


def test_модель_видит_текст_с_правками_рукой(песочница, monkeypatch):
    """Вычитывается то, что стоит в кадре, а не то, что услышала машина."""
    project, _, ключ = ролик(песочница)
    cut = pick.load(project, ключ)
    первая = строки(project, ключ)[0]
    edits.поправить_текст(cut, первая["с"], первая["по"], "уже поправлено мной")
    pick.update(project, cut)
    видел = поставщик(monkeypatch, ответ_про())
    proofread.спросить(project, ключ)
    текст = json.loads(видел.видел.data.decode("utf-8"))["messages"][0]["content"]
    assert "уже поправлено мной" in текст


def test_контекст_вокруг_уезжает_но_не_правится(песочница, monkeypatch):
    """Фразы до и после ролика — для смысла; правка на них не ложится."""
    project, _ = видео(песочница, 0)
    laid = speech.read(project)
    pick.save(project, pick.describe(laid, pick.by_ranges(laid, [(10, 15)]),
                                     "фразы", 180.0))
    ключ = pick.listing(project)[0]["id"]
    видел = поставщик(monkeypatch, ответ_про(("1-4", "чужая строка")))
    вышло = proofread.спросить(project, ключ)
    текст = json.loads(видел.видел.data.decode("utf-8"))["messages"][0]["content"]
    assert "фраза номер 9" in текст and "фраза номер 16" in текст
    assert вышло["правки"] == [] and вышло["чужие_строки"] == ["1-4"]


# ─── что приезжает ───────────────────────────────────────────────────

def test_было_пишет_сервис_а_не_модель(песочница, monkeypatch):
    """Модель называет строку и присылает, какой ей стать; что в строке
    сейчас — сервис знает сам."""
    project, _, ключ = ролик(песочница)
    ф = строки(project, ключ)[1]
    поставщик(monkeypatch, json.dumps({"правки": [
        {"строка": ф["строка"], "стало": "фраза номер два", "почему": "цифры",
         "было": "выдумка модели"}]}, ensure_ascii=False))
    вышло = proofread.спросить(project, ключ)
    assert вышло["правки"][0]["было"] == ф["текст"]
    assert вышло["правки"][0]["стало"] == "фраза номер два"


def test_ответ_ложится_файлом_до_разбора(песочница, monkeypatch):
    """Разбор может не удаться, а деньги уже заплачены."""
    project, _, ключ = ролик(песочница)
    поставщик(monkeypatch, "это не json")
    with pytest.raises(VertcutError) as беда:
        proofread.спросить(project, ключ)
    assert layout.proofread_raw(project, ключ).read_text(encoding="utf-8") \
        == "это не json"
    assert "proofread.answer.txt" in беда.value.hint


def test_номер_строки_с_тире_и_скобками_узнаётся(песочница, monkeypatch):
    """Модель любит типографское тире — правку из-за него не теряем."""
    project, _, ключ = ролик(песочница)
    ф = строки(project, ключ)[0]
    с, по = ф["строка"].split("-")
    поставщик(monkeypatch, ответ_про((f"[{с}–{по}]", "Фраза номер один")))
    assert len(proofread.спросить(project, ключ)["правки"]) == 1


def test_перевод_вместо_правки_отброшен(песочница, monkeypatch):
    """Русская строка, ставшая латиницей, — перевод, а не ослышка."""
    project, _, ключ = ролик(песочница)
    ф = строки(project, ключ)[0]
    поставщик(monkeypatch, ответ_про((ф["строка"], "phrase number one")))
    вышло = proofread.спросить(project, ключ)
    assert вышло["правки"] == [] and вышло["не_та_азбука"] == 1


def test_правка_без_изменений_не_правка(песочница, monkeypatch):
    project, _, ключ = ролик(песочница)
    ф = строки(project, ключ)[0]
    поставщик(monkeypatch, ответ_про((ф["строка"], ф["текст"])))
    assert proofread.спросить(project, ключ)["правки"] == []


# ─── решает человек ──────────────────────────────────────────────────

def спрошено(project, ключ, monkeypatch, сколько=2):
    фразы = строки(project, ключ)[:сколько]
    поставщик(monkeypatch, ответ_про(
        *[(ф["строка"], ф["текст"] + " исправлено") for ф in фразы]))
    proofread.спросить(project, ключ)
    return фразы


def test_правка_не_ложится_сама(песочница, monkeypatch):
    """Ответ модели — список, а не правка субтитра."""
    project, _, ключ = ролик(песочница)
    спрошено(project, ключ, monkeypatch)
    assert edits.список(pick.load(project, ключ)) == []


def test_принятая_правка_это_правка_рукой(песочница, monkeypatch):
    """Та же метка, тот же «Reset text edits», тот же штамп сборки."""
    project, _, ключ = ролик(песочница)
    ф = спрошено(project, ключ, monkeypatch)[0]
    cut = pick.load(project, ключ)
    до = subs.отпечаток_фраз(speech.read(project), pick.ranges(cut),
                             edits.список(cut))
    assert proofread.принять(project, cut, ф["с"], ф["по"]) == 1
    pick.update(project, cut)
    cut = pick.load(project, ключ)
    assert edits.список(cut) == [{"что": edits.ТЕКСТ, "с": ф["с"],
                                  "по": ф["по"],
                                  "текст": ф["текст"] + " исправлено"}]
    после = subs.отпечаток_фраз(speech.read(project), pick.ranges(cut),
                                edits.список(cut))
    assert до != после, "ролик не устарел от принятой правки"
    assert len(proofread.свежие(project, cut)) == 1


def test_свой_текст_вместо_текста_модели(песочница, monkeypatch):
    """Edit: человек поправил правку модели — ложится его текст."""
    project, _, ключ = ролик(песочница)
    ф = спрошено(project, ключ, monkeypatch)[0]
    cut = pick.load(project, ключ)
    proofread.принять(project, cut, ф["с"], ф["по"], "мой вариант")
    assert edits.список(cut)[0]["текст"] == "мой вариант"


def test_принять_все(песочница, monkeypatch):
    project, _, ключ = ролик(песочница)
    спрошено(project, ключ, monkeypatch, 3)
    cut = pick.load(project, ключ)
    assert proofread.принять(project, cut) == 3
    assert len(edits.список(cut)) == 3
    assert proofread.свежие(project, cut) == []


def test_отклонённая_не_трогает_субтитр(песочница, monkeypatch):
    project, _, ключ = ролик(песочница)
    ф = спрошено(project, ключ, monkeypatch)[0]
    cut = pick.load(project, ключ)
    assert proofread.отклонить(project, cut, ф["с"], ф["по"]) == 1
    assert edits.список(cut) == []
    assert [п["с"] for п in proofread.свежие(project, cut)] != [ф["с"]]
    assert len(proofread.свежие(project, cut)) == 1


def test_правка_пропадает_когда_фразу_поправили_рукой(песочница, monkeypatch):
    """Свежесть — по тексту: «было» больше не стоит в кадре, и правку
    показывать не к чему."""
    project, _, ключ = ролик(песочница)
    ф = спрошено(project, ключ, monkeypatch, 1)[0]
    cut = pick.load(project, ключ)
    edits.поправить_текст(cut, ф["с"], ф["по"], "своё")
    pick.update(project, cut)
    assert proofread.свежие(project, pick.load(project, ключ)) == []


def test_правка_пропадает_когда_фразу_разделили(песочница, monkeypatch):
    project, _, ключ = ролик(песочница)
    ф = спрошено(project, ключ, monkeypatch, 1)[0]
    cut = pick.load(project, ключ)
    edits.разделить_после(cut, ф["с"])
    pick.update(project, cut)
    assert proofread.свежие(project, pick.load(project, ключ)) == []


def test_принять_ушедшую_правку_отказ_словами(песочница, monkeypatch):
    project, _, ключ = ролик(песочница)
    ф = спрошено(project, ключ, monkeypatch, 1)[0]
    cut = pick.load(project, ключ)
    proofread.отклонить(project, cut, ф["с"], ф["по"])
    with pytest.raises(VertcutError) as беда:
        proofread.принять(project, cut, ф["с"], ф["по"])
    assert "no longer there" in беда.value.message


def test_разница_по_словам_считается_сервисом():
    """Экран только рисует: что зачеркнуть и что подсветить, приезжает."""
    вышло = proofread.разница("антология истории связанных",
                              "антология историй связанных")
    assert вышло["было"] == [["антология", False], ["истории", True],
                             ["связанных", False]]
    assert вышло["стало"][1] == ["историй", True]


# ─── деньги ──────────────────────────────────────────────────────────

def test_у_обращения_есть_хозяин(песочница, monkeypatch):
    """Двойное нажатие не оплачивается дважды."""
    from vertcut import works

    project, _, ключ = ролик(песочница)
    works.записать(layout.ai_work(project),
                   {"хозяин": {"pid": os.getpid(), "что": "вычитка",
                               "когда": "сейчас"}})
    with pytest.raises(VertcutError) as беда:
        proofread.спросить(project, ключ)
    assert "Already running" in беда.value.message


def test_хозяин_отпущен_и_после_неразобранного_ответа(песочница, monkeypatch):
    project, _, ключ = ролик(песочница)
    поставщик(monkeypatch, "мусор")
    with pytest.raises(VertcutError):
        proofread.спросить(project, ключ)
    assert not layout.ai_work(project).exists() or \
        "хозяин" not in json.loads(layout.ai_work(project).read_text("utf-8"))


def test_расход_записан_своей_задачей(песочница, monkeypatch):
    """У вычитки свой замер размера ответа: короче кандидатов, длиннее
    описаний."""
    from vertcut import spend

    project, _, ключ = ролик(песочница)
    поставщик(monkeypatch, ответ_про())
    proofread.спросить(project, ключ)
    assert spend.замер("какая-то", spend.ВЫЧИТКА)


def test_без_ключа_экран_знает_и_цены_нет(песочница):
    project, _, ключ = ролик(песочница)
    экран = proofread.для_экрана(project, pick.load(project, ключ))
    assert экран["подключён"] is False and экран["оценка"] is None
    assert экран["правки"] == [] and экран["спрошено"] is False

