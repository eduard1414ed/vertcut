"""Раздача: что человек получает и что с ним происходит при щелчке.

**Всё здесь проверено ещё и прогоном чистой машины** — подменённый дом,
распакованный архив, настоящая установка. Числа и что она нашла —
в `private/docs/sessions.md`. Эти проверки стерегут то, что прогон показал
один раз: повторить его на каждый коммит нельзя, он идёт минуты
и качает сотни мегабайт.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

import pytest

КОРЕНЬ = Path(__file__).resolve().parent.parent
УСТАНОВКА = КОРЕНЬ / "install"

sys.path.insert(0, str(УСТАНОВКА))
import installer as установщик  # noqa: E402


# ─── иконка на Рабочем столе ─────────────────────────────────────────

def подставная_иконка(куда: Path) -> Path:
    приложение = куда / "Vertcut.app"
    (приложение / "Contents" / "MacOS").mkdir(parents=True)
    (приложение / "Contents" / "Resources").mkdir(parents=True)
    пуск = приложение / "Contents" / "MacOS" / "Vertcut"
    пуск.write_text("#!/bin/bash\n", encoding="utf-8")
    пуск.chmod(0o755)
    (приложение / "Contents" / "Resources" / "install").mkdir()
    (приложение / "Contents" / "MacOS" / "install").symlink_to(
        "../Resources/install")
    (приложение / "Contents" / "Info.plist").write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" '
        '"http://www.apple.com/DTDs/PropertyList-1.0.dtd">\n'
        '<plist version="1.0"><dict>'
        '<key>CFBundleIdentifier</key><string>net.vertcut.проба</string>'
        '<key>CFBundleExecutable</key><string>Vertcut</string>'
        '</dict></plist>\n', encoding="utf-8")
    return приложение


@pytest.mark.skipif(sys.platform != "darwin",
                    reason="свёрток и его исполняемый бит бывают тут")
def test_иконка_ложится_на_рабочий_стол(tmp_path, monkeypatch):
    """Иначе её придётся искать — а искать человек не станет."""
    дом = tmp_path / "дом"
    (дом / "Desktop").mkdir(parents=True)
    monkeypatch.setattr(Path, "home", staticmethod(lambda: дом))
    иконка = подставная_иконка(tmp_path / "Загрузки")

    вышло = установщик.put_icon_on_desktop(иконка)

    assert вышло == дом / "Desktop" / "Vertcut.app"
    пуск = вышло / "Contents" / "MacOS" / "Vertcut"
    assert пуск.exists() and пуск.stat().st_mode & 0o111, (
        "исполняемый бит не уцелел — система скажет, что приложение "
        "повреждено")
    ссылка = вышло / "Contents" / "MacOS" / "install"
    assert ссылка.is_symlink() and ссылка.exists(), (
        "ссылка на установку не уцелела — ставить будет нечем")


def test_чужое_на_столе_не_перетирается(tmp_path, monkeypatch):
    """Перезаписать чужое молча хуже, чем не положить своё."""
    дом = tmp_path / "дом"
    стол = дом / "Desktop"
    стол.mkdir(parents=True)
    чужое = стол / "Vertcut.app"
    чужое.mkdir()
    (чужое / "это не наше.txt").write_text("привет", encoding="utf-8")
    monkeypatch.setattr(Path, "home", staticmethod(lambda: дом))

    установщик.put_icon_on_desktop(подставная_иконка(tmp_path / "Загрузки"))

    assert (чужое / "это не наше.txt").exists()


def test_запуск_со_стола_не_копирует_сам_себя(tmp_path, monkeypatch):
    дом = tmp_path / "дом"
    стол = дом / "Desktop"
    стол.mkdir(parents=True)
    monkeypatch.setattr(Path, "home", staticmethod(lambda: дом))
    иконка = подставная_иконка(стол)

    вышло = установщик.put_icon_on_desktop(иконка)

    assert вышло == иконка
    assert list(стол.iterdir()) == [иконка]


def test_без_рабочего_стола_не_падаем(tmp_path, monkeypatch):
    """Стола может не быть вовсе — это не повод рушить установку."""
    дом = tmp_path / "дом"
    дом.mkdir()
    monkeypatch.setattr(Path, "home", staticmethod(lambda: дом))
    assert установщик.put_icon_on_desktop(
        подставная_иконка(tmp_path / "Загрузки")) is None


# ─── второй щелчок ───────────────────────────────────────────────────

def test_честный_уход_сервиса_не_считается_падением():
    """Ноль — это не падение, и различать это обязательно.

    Сервис уже работал: второй экземпляр нашёл хозяина, открыл его
    вкладку и ушёл. Пока ярлык считал это поломкой, человек, нажавший
    иконку второй раз, получал ДВЕ вкладки — свой работающий сервис
    и страницу «Vertcut не запустился» поверх него. Поймано прогоном
    чистой машины, ни один прежний тест этого не видел.
    """
    sh = (УСТАНОВКА / "launcher.sh").read_text(encoding="utf-8")
    ps = (УСТАНОВКА / "launcher.ps1").read_text(encoding="utf-8")
    assert 'if [ "$CODE" -eq 0 ]; then' in sh
    assert "$Server.ExitCode -eq 0" in ps
    for текст in (sh, ps):
        assert "already running" in текст


def test_ярлык_не_ставит_второй_раз():
    """Установка идёт, только если поставленного ещё нет."""
    sh = (УСТАНОВКА / "launcher.sh").read_text(encoding="utf-8")
    assert 'if [ ! -f "$PROGRAM/version.json" ]; then' in sh


# ─── сборщик раздачи ─────────────────────────────────────────────────

def test_исходного_кода_в_раздаче_нет():
    """Он уехал на GitHub, и это правка после живой беды.

    Человек на Windows распаковал архив и увидел россыпь `.py` и `.sh`
    — он прочитал это как «мне прислали исходники» и был прав:
    запускать ему было нечего. А копия кода в архиве ещё и устаревала
    бы молча: собранная сегодня раздача несла бы вчерашний код.
    """
    модуль = сборщик_раздачи()
    исходник = Path(модуль.__file__).read_text(encoding="utf-8")
    # Слова, а не прозу: почему код уехал, написано в самом файле,
    # и искать его объяснение как поломку значило бы краснеть на нём.
    assert not hasattr(модуль, "КОД"), "список копируемого кода вернулся"
    assert "copytree" not in исходник, (
        "раздача снова копирует папки репозитория")
    for мёртвое in ('"Техническое"', '"Исходный код"'):
        assert мёртвое not in исходник, (
            f"исходный код снова уезжает в раздачу: {мёртвое}")
    for система in ("darwin", "windows"):
        страница = модуль.страница(система)
        assert модуль.АДРЕС_ПРОЕКТА in страница, (
            "человеку не сказано, где взять код")
    assert "github.com" in (КОРЕНЬ / "README.md").read_text(encoding="utf-8")


def test_лицензии_едут_с_раздачей():
    """Это обязательство, а не вежливость: MIT велит носить с собой
    имя и отказ от гарантий."""
    модуль = сборщик_раздачи()
    for имя in модуль.ЛИЦЕНЗИИ:
        assert (КОРЕНЬ / имя).exists(), f"в раздачу зовут то, чего нет: {имя}"


def test_человеку_сказано_про_стол_и_про_второй_запуск():
    модуль = сборщик_раздачи()
    for система in ("darwin", "windows"):
        страница = модуль.страница(система)
        assert "appears on your Desktop" in страница, (
            f"{система}: не сказано, что значок появится на столе")
        assert "it just opens Vertcut" in страница, (
            f"{система}: не сказано, что второй раз он не ставится")


@pytest.mark.skipif(sys.platform != "darwin", reason="ditto есть на macOS")
def test_в_архиве_нет_имён_вне_латиницы():
    """Главная беда четырнадцатой сессии, и вот её замер.

    `ditto` пишет имена буквами utf-8, но отметку «здесь utf-8»
    не ставит — и чужая машина читает их своей привычкой. Каждая
    русская буква превращается в два знака, и человек получает список
    файлов, в котором нельзя прочесть ни одного имени.

    Поэтому в раздаче латиница, а проверка смотрит на имена так,
    как их УВИДИТ получатель, а не так, как мы их записали.
    """
    модуль = сборщик_раздачи()
    import tempfile

    врем = Path(tempfile.mkdtemp(prefix="vertcut-имена-"))
    try:
        папка = врем / "Vertcut"
        папка.mkdir()
        (папка / "ЛИЦЕНЗИИ.md").write_text("проба", encoding="utf-8")
        архив = врем / "проба.zip"
        subprocess.run(["ditto", "-c", "-k", "--sequesterRsrc",
                        "--keepParent", str(папка), str(архив)], check=True)
        имена = модуль.имена_в_архиве(архив)
        рассыпалось = [и for и in имена if any(ord(з) > 127 for з in и)]
        assert рассыпалось, (
            "имя доехало целым — значит отметка utf-8 теперь ставится, "
            "и заслон надо перемерить, а не удалять")
        assert "ЛИЦЕНЗИИ.md" not in "".join(имена), (
            "имя прочиталось верно там, где прочитаться не могло")
    finally:
        shutil.rmtree(врем, ignore_errors=True)


def test_командный_файл_windows_только_латиницей():
    """`cmd.exe` читает его кодировкой времён DOS: русский путь внутри
    не находится никогда, а метка utf-8 в начале выполняется как
    команда — окно мигает, и не запускается ничего."""
    сборщик = сборщик_иконки_модуль()
    cmd = сборщик.WINDOWS_CMD
    assert cmd.isascii(), "в Vertcut.cmd русские буквы"
    assert not cmd.startswith("\ufeff")
    исходник = Path(сборщик.__file__).read_text(encoding="utf-8")
    assert 'encoding="ascii"' in исходник, (
        "Vertcut.cmd снова пишется с меткой utf-8")


def test_powershell_с_меткой_utf8():
    """Обратное правило, и потому оно стоит рядом. Windows PowerShell
    без метки читает файл старой кодировкой — и все русские слова
    человеку приезжают мусором."""
    for имя in ("install.ps1", "launcher.ps1"):
        начало = (УСТАНОВКА / имя).read_bytes()[:3]
        assert начало == b"\xef\xbb\xbf", (
            f"{имя} без метки utf-8: человек прочтёт мусор")


def test_обвес_не_везёт_чужой_половины():
    """`install.sh` в виндовой папке читается ровно так, как прочёл
    первый получатель: «мне прислали исходники»."""
    сборщик = сборщик_иконки_модуль()
    windows = сборщик.СВОЁ_УСТАНОВКИ["windows"]
    darwin = сборщик.СВОЁ_УСТАНОВКИ["darwin"]
    assert not [и for и in windows if и.endswith(".sh")]
    assert not [и for и in darwin if и.endswith(".ps1")]


def test_виндовая_раздача_проверяется_без_запуска(tmp_path):
    """Запустить её здесь нечем, и потому проверяется то, что
    проверяется без запуска. Проверка обязана краснеть."""
    модуль = сборщик_раздачи()
    корень = tmp_path / "Vertcut"
    (корень / "install").mkdir(parents=True)
    (корень / "install" / "Vertcut.cmd").write_bytes(
        "\ufeff@echo off\r\nrem путь\r\n".encode("utf-8-sig"))
    беды = " ".join(модуль.виндовые_беды(корень))
    assert "no Vertcut.exe" in беды, "раздача без exe прошла молча"
    assert "utf-8 mark" in беды, "метка utf-8 в cmd прошла молча"
    assert "non-Latin" in беды, "русский путь в cmd прошёл молча"
    assert "installer.py" in беды, "пропажа установщика прошла молча"

    (корень / "Vertcut.exe").write_bytes(b"<html>not found</html>")
    беды = " ".join(модуль.виндовые_беды(корень))
    assert "isn't a program" in беды, "exe, который не программа, прошёл молча"


def test_exe_зовёт_ту_же_запускалку_что_и_cmd():
    """Второй правды о том, как поднимается сервис, exe не заводит:
    он зовёт тот же `launcher.ps1` теми же словами, что `.cmd`."""
    сборщик = сборщик_иконки_модуль()
    исходник = (УСТАНОВКА / "launcher.cs").read_text(encoding="utf-8-sig")
    слова = "-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File"
    assert слова in исходник
    assert слова in сборщик.WINDOWS_CMD
    assert '"launcher.ps1"' in исходник
    assert "launcher.cs" not in сборщик.ОБЩЕЕ_УСТАНОВКИ + \
        сборщик.СВОЁ_УСТАНОВКИ["windows"], "исходник exe уезжает к человеку"


def test_русские_слова_exe_не_рассыпаются():
    """В окне «переложите меня в папку» русские слова. Компилятор
    берёт кодировку системы, если ему не сказать иначе, — и человек
    получил бы окно с мусором. Сказано дважды: меткой и флагом."""
    сборщик_текст = (УСТАНОВКА / "build-launcher.py").read_text(encoding="utf-8")
    assert (УСТАНОВКА / "launcher.cs").read_bytes()[:3] == b"\xef\xbb\xbf"
    assert "/codepage:65001" in сборщик_текст
    assert "/target:winexe" in сборщик_текст, (
        "exe без winexe показывает чёрное окно консоли")
    код = "\n".join(с.split("//")[0] for с in
                    (УСТАНОВКА / "launcher.cs").read_text(
                        encoding="utf-8-sig").splitlines())
    import re
    имена = re.sub(r'"[^"]*"', "", код)
    assert имена.isascii(), "в коде exe имена не латиницей"


# ─── подпись ─────────────────────────────────────────────────────────

def сборщик_иконки_модуль():
    import importlib.util

    спец = importlib.util.spec_from_file_location(
        "ярлык", УСТАНОВКА / "build-launcher.py")
    модуль = importlib.util.module_from_spec(спец)
    спец.loader.exec_module(модуль)
    return модуль


def сборщик_раздачи():
    import importlib.util

    спец = importlib.util.spec_from_file_location(
        "раздача", УСТАНОВКА / "build-release.py")
    модуль = importlib.util.module_from_spec(спец)
    спец.loader.exec_module(модуль)
    return модуль


def test_иконка_подписывается_своей_подписью():
    """Без подписи чужая машина говорит не «неизвестный разработчик»,
    а «программа повреждена», и разрешить это нельзя ничем, кроме
    терминала. Живьём это и случилось: архив уехал на чужой макбук,
    и человек не смог открыть его вовсе.

    Своя подпись бесплатна и ставится одной командой — так собирает
    всякий, у кого нет сертификата. Подпись автора (с 31-й сессии)
    ставится только с «укреплённым запуском» и отметкой времени:
    без них Apple заверять отказывает.
    """
    текст = (УСТАНОВКА / "build-launcher.py").read_text(encoding="utf-8")
    assert '"codesign", "--force", "--sign", "-"' in текст, (
        "свёрток собирается без своей подписи — чужая машина скажет, "
        "что он повреждён")
    assert '"--options", "runtime", "--timestamp"' in текст, (
        "подпись автора без укреплённого запуска — Apple не заверит")
    assert "подписать(приложение, автор)" in текст, "подпись не зовётся из сборки"
    # Последним делом: подпись запечатывает всё, что внутри, и всякая
    # правка после неё ломает её молча.
    сборка = текст[текст.index("def маковский"):текст.index("# Каким сертификатом")]
    assert сборка.rstrip().endswith("return приложение")
    assert сборка.index("подписать(приложение") > сборка.index("symlink_to")


def test_сертификат_автора_один_или_отказ(monkeypatch):
    """Чужим сертификатом не подписываем: его имя увидит в окне каждый,
    кто откроет программу. Сертификат для своей машины («Apple
    Development») не годится — Apple с ним не заверит."""
    модуль = сборщик_иконки_модуль()

    def связка(*строки):
        вывод = "".join(f'  {н}) ABC "{с}"\n' for н, с in enumerate(строки, 1))
        monkeypatch.setattr(модуль.subprocess, "run", lambda *а, **к:
                            subprocess.CompletedProcess(а, 0, вывод, ""))

    связка("Apple Development: a@b.c (X)",
           "Developer ID Application: Автор (TEAM)")
    assert модуль.сертификат_автора() == "Developer ID Application: Автор (TEAM)"

    связка("Apple Development: a@b.c (X)")
    with pytest.raises(SystemExit, match="No \"Developer ID Application\""):
        модуль.сертификат_автора()

    связка("Developer ID Application: Один (A)",
           "Developer ID Application: Другой (B)")
    with pytest.raises(SystemExit, match="Several"):
        модуль.сертификат_автора()


def test_отказ_apple_останавливает_сборку(tmp_path, monkeypatch):
    """Не заверили — сборка встаёт с объяснением Apple, а не уезжает
    раздачей, которая выглядит заверенной и пускает в настройки."""
    модуль = сборщик_раздачи()
    приложение = tmp_path / "Vertcut.app"
    приложение.mkdir()
    позвали = []

    def запуск(команда, *а, **к):
        позвали.append(команда[:3])
        if команда[:3] == ["xcrun", "notarytool", "submit"]:
            return subprocess.CompletedProcess(
                команда, 1, '{"id": "42", "status": "Invalid", '
                '"message": "Processing complete"}', "")
        if команда[:3] == ["xcrun", "notarytool", "log"]:
            return subprocess.CompletedProcess(
                команда, 0, "The signature does not include a secure timestamp.", "")
        return subprocess.CompletedProcess(команда, 0, "", "")

    monkeypatch.setattr(модуль.subprocess, "run", запуск)
    with pytest.raises(SystemExit, match="secure timestamp"):
        модуль.заверить_у_apple(приложение)
    assert ["xcrun", "stapler", "staple"] not in позвали, (
        "отметку вложили в незаверенное")
    assert not list(tmp_path.glob("vertcut-notary-*")), "времянка осталась"


@pytest.mark.skipif(sys.platform != "darwin", reason="codesign есть на macOS")
def test_подпись_переживает_копию_на_рабочий_стол(tmp_path, monkeypatch):
    """`shutil.copy` не носит меток файла — и это нарочно, из-за
    карантина. Подпись при этом уцелеть ОБЯЗАНА: она лежит файлами
    внутри свёртка, а не меткой, и сломанная подпись для системы
    то же самое, что её отсутствие."""
    дом = tmp_path / "дом"
    (дом / "Desktop").mkdir(parents=True)
    monkeypatch.setattr(Path, "home", staticmethod(lambda: дом))
    иконка = подставная_иконка(tmp_path / "Загрузки")
    subprocess.run(["codesign", "--force", "--sign", "-", str(иконка)],
                   check=True, capture_output=True)

    вышло = установщик.put_icon_on_desktop(иконка)

    проверка = subprocess.run(
        ["codesign", "--verify", "--deep", "--strict", str(вышло)],
        capture_output=True, text=True)
    assert проверка.returncode == 0, (
        "копия на столе потеряла подпись: " + проверка.stderr)


@pytest.mark.skipif(sys.platform != "darwin", reason="ditto есть на macOS")
def test_проверка_раздачи_краснеет_без_подписи(tmp_path):
    """Сборка обязана поймать это у себя, а не человек — у себя."""
    модуль = сборщик_раздачи()
    раздача = tmp_path / "Vertcut"
    приложение = подставная_иконка(раздача)
    (раздача / "README.html").write_text("<h1>", encoding="utf-8")
    (приложение / "Contents" / "Resources"
     / "vertcut-0.0.0-py3-none-any.whl").write_text("", encoding="utf-8")
    for имя in ("installer.py", "constraints.txt"):
        (приложение / "Contents" / "Resources" / "install"
         / имя).write_text("", encoding="utf-8")
    лицензии = раздача / "Licenses"
    лицензии.mkdir()
    for имя in модуль.ЛИЦЕНЗИИ:
        (лицензии / имя).write_text("", encoding="utf-8")

    архив = модуль.упаковать(раздача, "darwin")
    беды = модуль.проверить(архив, "darwin")
    assert any("damaged" in беда for беда in беды), беды

    subprocess.run(["codesign", "--force", "--sign", "-", str(приложение)],
                   check=True, capture_output=True)
    архив.unlink()
    архив = модуль.упаковать(раздача, "darwin")
    assert модуль.проверить(архив, "darwin") == []


# ─── маковский выпуск у автора ───────────────────────────────────────

def test_суммы_с_маком_не_трогают_виндовую(tmp_path):
    """Маковский архив кладёт в черновик автор (`release-mac.py`), а сумму
    виндового считал GitHub: её строка обязана остаться как была,
    а старая маковская — уйти, а не задвоиться."""
    import hashlib
    import importlib.util

    спец = importlib.util.spec_from_file_location(
        "выпуск_мака", УСТАНОВКА / "release-mac.py")
    модуль = importlib.util.module_from_spec(спец)
    спец.loader.exec_module(модуль)

    архив = tmp_path / "Vertcut-mac.zip"
    архив.write_bytes(b"mac")
    старые = "aaaa  Vertcut-windows.zip\n"
    вышло = модуль.суммы_с_маком(старые, архив)
    сумма = hashlib.sha256(b"mac").hexdigest()
    assert вышло == f"{сумма}  Vertcut-mac.zip\naaaa  Vertcut-windows.zip\n"
    # Второй прогон той же метки: строка мака заменяется, не дописывается.
    assert модуль.суммы_с_маком("bbbb  Vertcut-mac.zip\n" + старые, архив) == вышло


def test_github_не_кладёт_маковский_архив_в_черновик():
    """Архив со своей подписью в черновике выглядит ровно как заверенный
    и уехал бы к людям с заходом в настройки. Его место пустует, пока
    автор не положит заверенный."""
    текст = (КОРЕНЬ / ".github" / "workflows" / "release.yml").read_text(
        encoding="utf-8")
    кладёт = текст[текст.index("name: Положить в черновик"):]
    кладёт = кладёт[:кладёт.index("\n\n")]
    assert "Vertcut-mac.zip" not in кладёт
    assert "Vertcut-windows.zip" in кладёт
