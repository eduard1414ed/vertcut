"""Остановить сервис без выхода из системы (27-я сессия).

Кнопка «Quit Vertcut» и `vertcut stop` зовут одну функцию —
`server.выключить` внутри самого сервера; команда стучится к нему той
же ручкой, что и страница. Внешний значок в строке меню по-прежнему
гасит сервис сигналом по номеру из `app.json` — это сторожится здесь же.

Сервер поднимается НАСТОЯЩИМ процессом, а не нитью: проверяется
то, что увидит человек, — ушёл ли процесс, с каким кодом и что
осталось в `app.json`.
"""

from __future__ import annotations

import json
import os
import signal
import signal
import socket
import subprocess
import sys
import time

import pytest

from vertcut import cli, layout, works
from vertcut.web import server

from test_screen import экран, спросить     # noqa: F401  (фикстура)


def _свободный_порт() -> int:
    with socket.socket() as гнездо:
        гнездо.bind(("127.0.0.1", 0))
        return гнездо.getsockname()[1]


@pytest.fixture
def живой_экран(песочница):
    """`vertcut screen --no-browser` отдельным процессом в песочнице."""
    layout.root().mkdir(parents=True, exist_ok=True)
    процесс = subprocess.Popen(
        [sys.executable, "-X", "faulthandler", "-m", "vertcut", "screen",
         "--no-browser", "--port", str(_свободный_порт())],
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        env=dict(os.environ, PYTHONUTF8="1"))
    срок = time.monotonic() + 30
    while server.живой_хозяин() is None:
        if процесс.poll() is not None or time.monotonic() > срок:
            # Живого сперва гасим: читать вывод работающего — значит
            # ждать вечно. На машине macOS так зависало до предела в
            # 45 минут, и журнал не называл ни одной проверки. SIGABRT —
            # чтобы питон напечатал, на какой строке стоял.
            if процесс.poll() is None:
                if os.name == "posix":
                    процесс.send_signal(signal.SIGABRT)
                else:
                    процесс.kill()
                процесс.wait(timeout=10)
            вывод = процесс.stdout.read().decode("utf-8", "replace")
            pytest.fail(f"экран не поднялся:\n{вывод}")
        time.sleep(0.1)
    try:
        yield процесс
    finally:
        if процесс.poll() is None:
            процесс.kill()
        процесс.wait(timeout=10)


def _ушёл(процесс, сколько: float = 10) -> int:
    процесс.wait(timeout=сколько)
    return процесс.returncode


def test_stop_гасит_экран_и_отпускает_хозяина(живой_экран, capsys):
    assert cli.main(["stop"]) == 0
    assert "Vertcut has stopped." in capsys.readouterr().out
    # Код ноль: ярлык считает это обычным концом, а не «didn't start».
    assert _ушёл(живой_экран) == 0
    вывод = живой_экран.stdout.read().decode("utf-8", "replace")
    assert "Stopped." in вывод
    состояние = works.прочитать(layout.экран_хозяин())
    assert "хозяин" not in состояние
    assert server.живой_хозяин() is None


def test_stop_без_работающего_не_отказ(песочница, capsys):
    """Не работает — уже исполнено: код ноль, а не отказ. На этом
    держится «остановить на всякий случай» перед обновлением."""
    assert cli.main(["stop"]) == 0
    assert "Vertcut isn't running." in capsys.readouterr().out


def test_stop_гасит_сигналом_если_сервер_не_ответил(живой_экран, monkeypatch,
                                                     capsys):
    """Запасной путь: просьба не дошла — процесс гасится сигналом.
    На Windows это `TerminateProcess`, и код выхода там другой; здесь
    проверяется одно: процесса больше нет."""
    monkeypatch.setattr(server, "_попросить_уйти", lambda состояние: False)
    assert cli.main(["stop"]) == 0
    assert "Vertcut has stopped." in capsys.readouterr().out
    _ушёл(живой_экран)
    assert server.живой_хозяин() is None


@pytest.mark.skipif(sys.platform.startswith("win"),
                    reason="на Windows SIGTERM — это TerminateProcess")
def test_значок_в_строке_меню_гасит_по_номеру_как_раньше(живой_экран):
    """Внешний значок (программа вне репозитория) берёт номер процесса
    из `app.json` и шлёт SIGTERM. Формат `app.json` и этот путь
    не меняются: сервер уходит с нулём и отпускает хозяина."""
    состояние = json.loads(layout.экран_хозяин().read_text(encoding="utf-8"))
    assert set(состояние) >= {"хозяин", "порт", "пропуск"}
    assert состояние["хозяин"]["pid"] == живой_экран.pid
    os.kill(состояние["хозяин"]["pid"], signal.SIGTERM)
    assert _ушёл(живой_экран) == 0
    assert "хозяин" not in works.прочитать(layout.экран_хозяин())


def test_ручка_выключить_только_с_пропуском(экран):  # noqa: F811
    """Погасить сервис — та же просьба, что и все: чужая страница
    пропуска не знает."""
    код, _ = спросить(экран, "/апи/выключить", ключ=None, тело={})
    assert код == 403
    код, _ = спросить(экран, "/апи/что-идёт", ключ=None)
    assert код == 403
    assert "выключить" not in server.БЕЗ_ПРОПУСКА


def test_что_идёт_называет_долгую_работу(экран):  # noqa: F811
    """Страница спрашивает это ДО «Quit»: человек узнаёт, что разбор
    пойдёт дальше сам, заранее, а не после."""
    код, тело = спросить(экран, "/апи/что-идёт")
    assert код == 200
    assert json.loads(тело) == {"идёт": []}

    папка = layout.root() / "long-talk"
    папка.mkdir(parents=True)
    works.взять(layout.work(папка), "analysis")      # хозяин — этот процесс
    код, тело = спросить(экран, "/апи/что-идёт")
    assert json.loads(тело)["идёт"] == ["analysis of “long-talk”"]


def test_ручка_выключить_гасит_этот_сервер(песочница):
    """Ответ уходит странице ДО того, как сервер гаснет: иначе кнопка
    получила бы обрыв и показала «Vertcut is not responding»."""
    import threading

    layout.root().mkdir(parents=True, exist_ok=True)
    сервер = server.завести(порт=0)
    поток = threading.Thread(target=сервер.serve_forever, daemon=True)
    поток.start()
    try:
        код, тело = спросить(сервер, "/апи/выключить", тело={})
        assert код == 200, тело
        assert json.loads(тело) == {"остановлен": True, "идёт": []}
        поток.join(timeout=5)
        assert not поток.is_alive(), "сервер не ушёл после «выключить»"
    finally:
        сервер.server_close()
