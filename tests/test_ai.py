"""Ключ, деньги и сеть.

**Ни один тест отсюда в сеть не ходит.** Это и есть главная беда этой
сессии: автотесты сети не видят вовсе, и обращение к ней, заползшее
в середину разбора, не поймал бы никто. Поэтому здесь два заслона
на само правило — «наружу ходят только из одного файла» и «главная
дорога про этот файл не знает», — а всё остальное проверяется
на поддельном ответе поставщика.
"""

from __future__ import annotations

import io
import json
import urllib.error
from pathlib import Path

import pytest

from vertcut import ai, config, layout, spend, tuning
from vertcut.errors import VertcutError


# ─── сеть живёт в одном файле ────────────────────────────────────────

def test_наружу_ходят_только_из_одного_файла():
    """Правило четвёртой сессии: сервис обязан работать без сети.

    Эта сессия впервые вводит сеть. Если обращение к ней появится
    в разборе, в сборке или в веб-слое, человек без интернета получит
    отказ там, где его быть не должно, — а поймать это нечем: тесты
    в сеть не ходят.

    `web/server.py` считается своим: он не ходит наружу, а слушает
    у себя, и это разные вещи.
    """
    корень = Path(layout.__file__).parent
    свои = {"ai.py", "server.py"}
    виноватые = []
    for файл in корень.rglob("*.py"):
        if файл.name in свои:
            continue
        текст = файл.read_text(encoding="utf-8")
        for номер, строка in enumerate(текст.splitlines(), 1):
            голая = строка.strip()
            if голая.startswith("#") or голая.startswith('"'):
                continue
            for чужое in ("urllib.request", "http.client", "import requests",
                          "urlopen", "socket.create_connection"):
                if чужое in голая:
                    виноватые.append(f"{файл.name}:{номер}  {голая}")
    assert not виноватые, виноватые


def test_главная_дорога_не_знает_про_модель():
    """Разбор, кадр, субтитры и сборка не должны звать модель.

    Иначе «без ключа работает всё остальное» перестало бы быть правдой
    молча: человек без ключа узнал бы об этом посреди девятиминутного
    разбора.
    """
    корень = Path(layout.__file__).parent
    главная = ["ingest.py", "align.py", "phrases.py", "speech.py", "shots.py",
               "crop.py", "faces.py", "plans.py", "subs.py", "chain.py",
               "render.py", "verify.py", "queue.py", "preview.py", "pick.py",
               "edits.py", "layer.py", "media.py", "fonts.py"]
    виноватые = []
    for имя in главная:
        текст = (корень / имя).read_text(encoding="utf-8")
        for номер, строка in enumerate(текст.splitlines(), 1):
            голая = строка.strip()
            if голая.startswith("#") or голая.startswith('"'):
                continue
            if "import ai" in голая or "from .ai" in голая:
                виноватые.append(f"{имя}:{номер}  {голая}")
    assert not виноватые, виноватые


# ─── ключ ────────────────────────────────────────────────────────────

def test_ключ_не_печатается_целиком(песочница):
    config.write({config.MODEL_KEY: "sk-ant-sekret-tselikom-1234"})
    assert config.model_key_tail() == "…1234"
    assert "sekret" not in config.model_key_tail()
    assert "sekret" not in config.откуда_ключ()


def test_ключ_лежит_снаружи_репозитория(песочница):
    """Спека против дизайна, и взята спека.

    Ключ в браузере не виден команде в терминале, пропадает от чистки
    браузера и заводится заново в каждом браузере на машине.
    """
    config.put(config.MODEL_KEY, "sk-ant-что-то")
    где = layout.config_file()
    репозиторий = Path(layout.__file__).parent.parent
    assert репозиторий not in где.parents


def test_ключ_берётся_по_протоколу(песочница, monkeypatch):
    """У кого заведены обе переменные, ключ Anthropic не уедет к OpenAI.

    И в файле их два по той же причине: сперва поле было одно, и смена
    протокола отправляла ключ Anthropic на адрес OpenAI. Отказ приходил
    «ключ не принят» — то есть указывал ровно не туда, где беда.
    """
    config.write({config.MODEL_KEY: "sk-ant-v-fajle",
                  config.OPENAI_KEY: "sk-oai-v-fajle"})
    config.put(config.ПРОТОКОЛ, config.ANTHROPIC)
    assert config.model_key() == "sk-ant-v-fajle"
    config.put(config.ПРОТОКОЛ, config.OPENAI)
    assert config.model_key() == "sk-oai-v-fajle"

    monkeypatch.setenv(config.MODEL_ENV, "sk-ant-0004")
    monkeypatch.setenv(config.OPENAI_ENV, "sk-oai-0005")
    config.put(config.ПРОТОКОЛ, config.ANTHROPIC)
    assert config.model_key() == "sk-ant-0004"
    config.put(config.ПРОТОКОЛ, config.OPENAI)
    assert config.model_key() == "sk-oai-0005"


def test_без_ключа_но_со_своим_адресом_это_законно(песочница):
    """Модель на машине человека ключа не спрашивает вовсе.

    Требовать его значило бы закрыть единственный способ пользоваться
    двумя кнопками бесплатно.
    """
    assert not config.подключён()
    config.write({config.ПРОТОКОЛ: config.OPENAI,
                  config.АДРЕС: "http://127.0.0.1:11434/v1"})
    assert config.подключён()


def test_без_ключа_отказ_говорит_что_остальное_работает(песочница):
    with pytest.raises(VertcutError) as беда:
        ai.спросить("что-то", "текст", потолок=100)
    вместе = беда.value.message + (беда.value.hint or "")
    # Сказано, что ключа нет, где его завести, и что без него работает
    # всё остальное.
    assert "No API key" in беда.value.message
    assert "Settings" in вместе
    assert "Everything else works without a key" in вместе


# ─── деньги ──────────────────────────────────────────────────────────

def test_цена_неизвестной_модели_не_выдумывается(песочница):
    """Соврать про цену хуже, чем её не знать."""
    config.put(config.МОДЕЛЬ, "ollama/своя-модель")
    assert config.цена("ollama/своя-модель") is None
    оценка = spend.оценить("текст" * 100, 1000)
    assert оценка["деньги"] is None
    assert оценка["вошло"] > 0        # размер всё равно назван


def test_своя_цена_перебивает_поставляемую(песочница):
    config.put(config.ЦЕНЫ, {"claude-opus-5": [1.0, 2.0]})
    assert config.цена("claude-opus-5") == [1.0, 2.0]


def test_суточный_стоп_останавливает(песочница):
    config.put(config.СТОП, 1.0)
    spend.записать("claude-opus-5", 100000, 40000, 1.5, 3.0)
    with pytest.raises(VertcutError) as беда:
        spend.проверить_стоп(0.01)
    # Названо, что сработал суточный стоп, и сколько ушло.
    assert "Daily limit" in беда.value.message
    assert "$1.50" in беда.value.message
    assert "raise the daily limit" in беда.value.hint


def test_суточный_стоп_ловит_и_то_что_ещё_не_потрачено(песочница):
    config.put(config.СТОП, 1.0)
    spend.записать("claude-opus-5", 1000, 100, 0.9, 1.0)
    with pytest.raises(VertcutError):
        spend.проверить_стоп(0.5)
    spend.проверить_стоп(0.05)        # а это влезает


def test_запрос_без_известной_цены_в_стоп_не_входит(песочница):
    """И об этом сказано вслух, а не считается нулём молча."""
    spend.записать("своя-модель", 1000, 100, None, 1.0)
    прошло = spend.день()
    assert прошло["деньги"] == 0.0
    assert прошло["без_цены"] == 1


def test_порог_спрашивает_а_не_отказывает(песочница):
    config.put(config.ПОРОГ, 0.10)
    with pytest.raises(spend.ДорогоError) as беда:
        spend.проверить_порог(0.30, разрешено=False)
    assert беда.value.сколько == 0.30
    spend.проверить_порог(0.30, разрешено=True)      # согласился — молчим


def test_дорого_это_вопрос_а_не_беда():
    """Экран показывает это полосой с кнопкой, а не красным отказом.

    Отличить одно от другого по тексту сообщения нельзя — по типу можно.
    """
    assert issubclass(spend.ДорогоError, VertcutError)


def test_оценка_считается_по_замеру_а_не_по_потолку(песочница):
    """Потолок — предел, а не ожидание.

    Считать по нему значило бы пугать человека суммой впятеро больше
    настоящей.
    """
    сперва = spend.оценить("текст" * 500, 8000)
    assert сперва["выйдет"] < 8000
    # Оценка честно говорит, что опереться не на что.
    assert "no requests to this model yet" in сперва["откуда_оценка"]

    for _ in range(3):
        spend.записать(config.модель(), 5000, 700, 0.02, 4.0)
    потом = spend.оценить("текст" * 500, 8000)
    assert потом["выйдет"] == 700
    # Сказано, на скольких прошлых ответах стоит оценка.
    assert "3 past requests" in потом["откуда_оценка"]


def test_дневник_не_растёт_бесконечно(песочница):
    """Дневник нужен суточному стопу, а не бухгалтерии."""
    import json as _json
    spend.записать("claude-opus-5", 10, 10, 0.01, 1.0)
    файл = layout.spend_file()
    это = _json.loads(файл.read_text(encoding="utf-8"))
    это["дни"] = {f"2020-01-{д:02d}": {"запросов": 1} for д in range(1, 29)}
    это["дни"].update({f"2020-02-{д:02d}": {"запросов": 1}
                       for д in range(1, 29)})
    это["дни"].update({f"2020-03-{д:02d}": {"запросов": 1}
                       for д in range(1, 29)})
    файл.write_text(_json.dumps(это), encoding="utf-8")
    spend.записать("claude-opus-5", 10, 10, 0.01, 1.0)
    после = _json.loads(файл.read_text(encoding="utf-8"))
    assert len(после["дни"]) <= tuning.ДНЕЙ_РАСХОДОВ


# ─── разбор ответа: обе дороги ───────────────────────────────────────

def _ответил(тело: dict, monkeypatch, код: int = 200):
    """Подделать поставщика, не выходя в сеть."""
    сырое = json.dumps(тело).encode("utf-8")

    class Открывалка:
        def open(self, просьба, timeout=None):
            Открывалка.видел = просьба
            if код != 200:
                raise urllib.error.HTTPError(
                    просьба.full_url, код, "нет", {}, io.BytesIO(сырое))

            class Ответ:
                def read(self_):
                    return сырое

                def __enter__(self_):
                    return self_

                def __exit__(self_, *_):
                    return False
            return Ответ()

    monkeypatch.setattr(ai.urllib.request, "build_opener",
                        lambda *_: Открывалка())
    return Открывалка


ANTHROPIC_ОТВЕТ = {
    "model": "claude-opus-5",
    "content": [{"type": "text", "text": "вот ответ"}],
    "usage": {"input_tokens": 1200, "output_tokens": 300},
    "stop_reason": "end_turn",
}

OPENAI_ОТВЕТ = {
    "model": "gpt-что-то",
    "choices": [{"message": {"content": "вот ответ"},
                 "finish_reason": "stop"}],
    "usage": {"prompt_tokens": 1200, "completion_tokens": 300},
}


def test_обе_дороги_дают_один_и_тот_же_ответ(песочница, monkeypatch):
    """Одна функция — значит снаружи разницы нет вовсе."""
    config.write({config.MODEL_KEY: "sk-test-0001"})
    _ответил(ANTHROPIC_ОТВЕТ, monkeypatch)
    один = ai.спросить("инструкция", "текст", потолок=1000)

    config.write({config.OPENAI_KEY: "sk-test-0002", config.ПРОТОКОЛ: config.OPENAI})
    _ответил(OPENAI_ОТВЕТ, monkeypatch)
    другой = ai.спросить("инструкция", "текст", потолок=1000)

    assert один.текст == другой.текст == "вот ответ"
    assert один.вошло == другой.вошло == 1200
    assert один.вышло == другой.вышло == 300


def test_ключ_уходит_нужным_заголовком(песочница, monkeypatch):
    """У протоколов они разные, и перепутать их значит получить 401."""
    config.write({config.MODEL_KEY: "sk-sekretnyj-0003"})
    видел = _ответил(ANTHROPIC_ОТВЕТ, monkeypatch)
    ai.спросить("и", "т", потолок=10)
    заголовки = видел.видел.headers
    assert заголовки.get("X-api-key") == "sk-sekretnyj-0003"
    assert "Authorization" not in заголовки

    config.write({config.OPENAI_KEY: "sk-sekretnyj-0003",
                  config.ПРОТОКОЛ: config.OPENAI})
    видел = _ответил(OPENAI_ОТВЕТ, monkeypatch)
    ai.спросить("и", "т", потолок=10)
    assert видел.видел.headers.get("Authorization") == "Bearer sk-sekretnyj-0003"


def test_без_ключа_заголовка_нет_вовсе(песочница, monkeypatch):
    """Пустой «Bearer » часть серверов отвергает."""
    config.write({config.ПРОТОКОЛ: config.OPENAI,
                  config.АДРЕС: "http://127.0.0.1:11434/v1"})
    видел = _ответил(OPENAI_ОТВЕТ, monkeypatch)
    ai.спросить("и", "т", потолок=10)
    assert "Authorization" not in видел.видел.headers


def test_деньги_записываются_даже_если_ответ_не_разобрался(песочница,
                                                           monkeypatch):
    """Разбор может не удаться, а деньги уже потрачены."""
    config.write({config.MODEL_KEY: "sk-test-0001"})
    пустой = {**ANTHROPIC_ОТВЕТ, "content": []}
    _ответил(пустой, monkeypatch)
    with pytest.raises(VertcutError):
        ai.спросить("и", "т", потолок=10)
    assert spend.день()["запросов"] == 1


def test_поставщик_промолчал_про_токены_считаем_сами(песочница, monkeypatch):
    config.write({config.MODEL_KEY: "sk-test-0001"})
    без = {k: v for k, v in ANTHROPIC_ОТВЕТ.items() if k != "usage"}
    _ответил(без, monkeypatch)
    вышло = ai.спросить("инструкция", "текст", потолок=10)
    assert вышло.посчитал_сам
    assert вышло.вошло > 0


def test_обрыв_по_потолку_виден(песочница, monkeypatch):
    config.write({config.MODEL_KEY: "sk-test-0001"})
    _ответил({**ANTHROPIC_ОТВЕТ, "stop_reason": "max_tokens"}, monkeypatch)
    assert ai.спросить("и", "т", потолок=10).оборвался


def test_отказ_модели_это_не_пустота(песочница, monkeypatch):
    config.write({config.MODEL_KEY: "sk-test-0001"})
    _ответил({**ANTHROPIC_ОТВЕТ, "content": [], "stop_reason": "refusal",
              "stop_details": {"explanation": "не хочу"}}, monkeypatch)
    with pytest.raises(VertcutError) as беда:
        ai.спросить("и", "т", потолок=10)
    # Названо, что отказала МОДЕЛЬ, и её же словами.
    assert "refused" in беда.value.message
    assert "не хочу" in беда.value.message


# ─── отказы говорят разными словами ──────────────────────────────────

@pytest.mark.parametrize("код,слово,что_делать", [
    # Что случилось — и что делать: проверить ключ, ждать, проверить
    # адрес, ждать, поправить имя модели.
    (401, "not accepted", "expired"),
    (429, "Too many requests", "wait"),
    (404, "Nothing at this address", "address"),
    (500, "provider has a problem", "wait"),
    (400, "rejected the request", "model name"),
])
def test_отказы_разными_словами(песочница, monkeypatch, код, слово,
                                что_делать):
    """Человек должен понять: ждать ему, платить или исправлять."""
    config.write({config.MODEL_KEY: "sk-test-0001"})
    _ответил({"error": {"message": "поставщик так сказал"}}, monkeypatch,
             код=код)
    with pytest.raises(VertcutError) as беда:
        ai.спросить("и", "т", потолок=10)
    вместе = (беда.value.message + " " + (беда.value.hint or "")).lower()
    assert слово.lower() in вместе
    assert что_делать.lower() in вместе


def test_нет_связи_говорит_что_остальное_работает(песочница, monkeypatch):
    config.write({config.MODEL_KEY: "sk-test-0001"})

    class Открывалка:
        def open(self, *_, **__):
            raise urllib.error.URLError("имя не разрешается")

    monkeypatch.setattr(ai.urllib.request, "build_opener",
                        lambda *_: Открывалка())
    with pytest.raises(VertcutError) as беда:
        ai.спросить("и", "т", потолок=10)
    вместе = беда.value.message + (беда.value.hint or "")
    # Названо, что нет связи, и что остальное работает без сети.
    assert "Cannot reach" in вместе
    assert "works offline" in вместе


def test_не_json_в_ответе_говорит_про_адрес(песочница, monkeypatch):
    """Чаще всего это адрес, ведущий не к модели, а на чью-то страницу."""
    config.write({config.MODEL_KEY: "sk-test-0001"})

    class Открывалка:
        def open(self, просьба, timeout=None):
            class Ответ:
                def read(self_):
                    return b"<html>Not Found</html>"

                def __enter__(self_):
                    return self_

                def __exit__(self_, *_):
                    return False
            return Ответ()

    monkeypatch.setattr(ai.urllib.request, "build_opener",
                        lambda *_: Открывалка())
    with pytest.raises(VertcutError) as беда:
        ai.спросить("и", "т", потолок=10)
    assert "does not lead to a model" in (беда.value.hint or "")


def test_потолок_переименовывается_по_слову_поставщика(песочница,
                                                       monkeypatch):
    """Часть серверов протокола OpenAI требует другого имени поля.

    Отличить их заранее нельзя: адрес произвольный. Переименование
    делается по слову самого поставщика, а не наугад.
    """
    config.write({config.OPENAI_KEY: "sk-test-0002", config.ПРОТОКОЛ: config.OPENAI})
    сказано = []

    class Открывалка:
        def open(self, просьба, timeout=None):
            тело = json.loads(просьба.data.decode("utf-8"))
            сказано.append(тело)
            if "max_tokens" in тело:
                ошибка = json.dumps({"error": {"message":
                    "Unsupported parameter: 'max_tokens'. Use "
                    "'max_completion_tokens' instead."}}).encode()
                raise urllib.error.HTTPError(просьба.full_url, 400, "нет",
                                             {}, io.BytesIO(ошибка))

            class Ответ:
                def read(self_):
                    return json.dumps(OPENAI_ОТВЕТ).encode()

                def __enter__(self_):
                    return self_

                def __exit__(self_, *_):
                    return False
            return Ответ()

    monkeypatch.setattr(ai.urllib.request, "build_opener",
                        lambda *_: Открывалка())
    вышло = ai.спросить("и", "т", потолок=777)
    assert вышло.текст == "вот ответ"
    assert len(сказано) == 2
    assert сказано[1]["max_completion_tokens"] == 777


def test_прокси_не_подхватывается_из_окружения(песочница, monkeypatch):
    """«Куда уходит — только на этот адрес» — это обещание экрана.

    Питон по умолчанию берёт прокси из окружения, и запрос с ключом
    ушёл бы не туда, куда обещано.
    """
    исходник = Path(ai.__file__).read_text(encoding="utf-8")
    assert "build_opener" in исходник
    assert "ProxyHandler" not in исходник


# ─── инструкции ──────────────────────────────────────────────────────

def test_форма_ответа_не_правится(песочница):
    """Человек правит, ЧТО просить; сервис задаёт, КАК отвечать.

    Пусти форму в правку — и первая же вольность («пиши просто
    списком») превратилась бы в «сервис перестал понимать модель»,
    а виноватым выглядел бы сервис.
    """
    from vertcut import prompts

    prompts.записать(prompts.ФРАГМЕНТЫ, "делай что хочешь")
    целиком = prompts.собрать(prompts.ФРАГМЕНТЫ)
    assert "делай что хочешь" in целиком
    assert '"фрагменты"' in целиком          # форма на месте


def test_пустая_инструкция_это_вернуть_базовую(песочница):
    from vertcut import prompts

    prompts.записать(prompts.ОПИСАНИЯ, "своя")
    assert prompts.своя_ли(prompts.ОПИСАНИЯ)
    prompts.записать(prompts.ОПИСАНИЯ, "   ")
    assert not prompts.своя_ли(prompts.ОПИСАНИЯ)
    assert prompts.прочитать(prompts.ОПИСАНИЯ) == \
        prompts.поставляемая(prompts.ОПИСАНИЯ)


def test_эталонов_может_не_быть_вовсе(песочница):
    """У чужого человека их нет, и это не недостача."""
    from vertcut import prompts

    assert prompts.эталоны() == []
    целиком = prompts.собрать(prompts.ОПИСАНИЯ, prompts.эталоны())
    assert "HOW THE CREATOR WRITES" not in целиком
    prompts.записать_эталоны("Первая подпись\n\nВторая подпись")
    assert prompts.эталоны() == ["Первая подпись", "Вторая подпись"]
    с_эталонами = prompts.собрать(prompts.ОПИСАНИЯ, prompts.эталоны())
    assert "HOW THE CREATOR WRITES" in с_эталонами
    # Манеру, а не язык: русские образцы не должны тянуть на русский
    # описания английского видео (21-я сессия).
    assert "the manner, not the language" in " ".join(с_эталонами.split())


def test_правило_языка_стоит_в_конце_просьбы_и_сказано_дважды(песочница):
    """ЗАМЕР пятой сессии опроверг первый заход.

    Сперва правило стояло в инструкции, по-русски и один раз.
    На английском видео модель ответила ПО-РУССКИ — все двенадцать
    предложений: инструкция целиком русская, и она перетянула.

    Теперь оно в конце самой просьбы (последнее весит больше)
    и на двух языках: назвать язык сервис не может — он его
    не определяет и не должен.

    С 21-й сессии инструкция английская, и опасной стала обратная
    сторона: русское видео. Правило называет обе стороны примером.
    """
    from vertcut import prompts

    for какая in prompts.ВСЕ:
        assert "ANSWER LANGUAGE" not in prompts.ФОРМА[какая], \
            "правило вернулось в форму"
    assert "ЯЗЫК ОТВЕТА" in prompts.ПРО_ЯЗЫК
    assert "ANSWER LANGUAGE" in prompts.ПРО_ЯЗЫК
    for сторона in ("Russian transcript → write in Russian",
                    "English transcript → write in English",
                    "русский текст —", "английский — по-английски"):
        assert сторона in " ".join(prompts.ПРО_ЯЗЫК.split()), сторона


def test_инструкции_модели_английские_а_ключи_договора_прежние():
    """21-я сессия: инструкции по-английски, ключи ответа — нет.

    Ключи json — договор с сервисом: по ним читаются и новые ответы,
    и старые, уже лежащие на диске. Форма прямо говорит модели, что
    ключи русские, а значения — на языке видео.
    """
    from vertcut import layout, prompts
    from vertcut.text import азбука

    for какая in prompts.ВСЕ:
        assert азбука(prompts.поставляемая(какая)) == "латиница", какая
        assert "in Russian letters" in prompts.ФОРМА[какая]
    for ключ in ('"фрагменты"', '"с"', '"по"', '"название"', '"о_чём"'):
        assert ключ in prompts.ФОРМА[prompts.ФРАГМЕНТЫ], ключ
    for ключ in ('"описания"', '"ключ"', '"текст"'):
        assert ключ in prompts.ФОРМА[prompts.ОПИСАНИЯ], ключ
    for ключ in ('"правки"', '"строка"', '"стало"', '"почему"'):
        assert ключ in prompts.ФОРМА[prompts.ВЫЧИТКА], ключ


@pytest.mark.parametrize("текст,ждём", [
    ("Как жить, когда мир катится", "кириллица"),
    ("What every beginner gets wrong", "латиница"),
    ("Привет, это Vertcut", "обе"),
    ("Смотрите новое видео про Kubernetes", "кириллица"),   # имя не в счёт
    ("2026 · 19:31", None),
])
def test_азбука_считает_а_не_судит(текст, ждём):
    """Отличить кириллицу от латиницы можно счётом; язык — нельзя.

    Имя или название на другом языке есть почти в любом тексте, и
    жаловаться на них значило бы жаловаться всегда.
    """
    from vertcut.text import азбука

    assert азбука(текст) == ждём


# ─── список моделей спрашивается, а не вшивается ─────────────────────

def test_список_моделей_нигде_не_вшит():
    """Спека запрещает вшивать список названий моделей.

    Но голое поле, в которое надо вписать имя знак в знак, — это
    не честность, а «разбирайтесь сами». Выход в том, что список есть
    у самого поставщика: обе дороги отдают его по одному и тому же
    адресу и в одном и том же виде.

    Прейскурант — не список моделей: там цены, и у него своя работа.
    Он же единственное место, где имена моделей вообще написаны.
    """
    корень = Path(layout.__file__).parent
    экран = layout.web() / "js"
    имена = ("claude-sonnet-5", "claude-haiku", "gpt-4", "gpt-5", "o1-")
    виноватые = []
    for файл in list(корень.rglob("*.py")) + list(экран.rglob("*.js")):
        if файл.name == "tuning.py":
            continue           # прейскурант, и у него дата
        текст = файл.read_text(encoding="utf-8")
        for имя in имена:
            if имя in текст:
                виноватые.append(f"{файл.name}: {имя}")
    assert not виноватые, виноватые


def test_модели_приезжают_обеими_дорогами(песочница, monkeypatch):
    """У обеих один адрес `/models` и одно поле `data[].id`.

    Поэтому спрашивать список можно, не зная, с кем говоришь.
    """
    config.write({config.MODEL_KEY: "sk-test-0001"})
    _ответил({"data": [{"id": "claude-opus-5", "display_name": "Opus 5"},
                       {"id": "claude-sonnet-5"}]}, monkeypatch)
    вышло = ai.модели()
    assert [м["имя"] for м in вышло["модели"]] == ["claude-opus-5",
                                                   "claude-sonnet-5"]
    assert вышло["модели"][0]["зовут"] == "Opus 5"

    config.write({config.OPENAI_KEY: "sk-test-0002", config.ПРОТОКОЛ: config.OPENAI})
    видел = _ответил({"data": [{"id": "gpt-нечто", "object": "model"}]},
                     monkeypatch)
    вышло = ai.модели()
    assert [м["имя"] for м in вышло["модели"]] == ["gpt-нечто"]
    assert видел.видел.full_url.endswith("/models")
    assert видел.видел.get_method() == "GET"


def test_поставщик_без_списка_это_не_поломка(песочница, monkeypatch):
    """Часть посредников такого адреса не держит вовсе.

    Тогда остаётся поле для имени — как в дизайне, — и сказано это
    словами, а не отказом «сломалось».
    """
    config.write({config.MODEL_KEY: "sk-test-0001"})
    _ответил({"что-то": "другое"}, monkeypatch)
    with pytest.raises(VertcutError) as беда:
        ai.модели()
    assert "did not send a list" in беда.value.message
    assert "Type the model name" in (беда.value.hint or "")


def test_список_моделей_не_стоит_денег(песочница, monkeypatch):
    """Он не идёт через `спросить`, значит в дневник не пишется."""
    config.write({config.MODEL_KEY: "sk-test-0001"})
    _ответил({"data": [{"id": "какая-то"}]}, monkeypatch)
    ai.модели()
    assert spend.день()["запросов"] == 0


def test_ключ_с_русскими_буквами_это_отказ_а_не_поломка(песочница):
    """Пятое место в проекте, где русские буквы не проходят.

    Значение заголовка HTTP обязано быть латиницей — так велит
    стандарт, — и питон на кириллице не отказывает, а ПАДАЕТ. Человек
    видел «сервис сломался», а сломался не сервис.

    Найдено автором на живом экране. Случай не выдуманный: русская «с»
    неотличима от латинской `c`, и ключ, поправленный не в той
    раскладке, выглядит совершенно правильным.
    """
    with pytest.raises(VertcutError) as беда:
        config.проверить_ключ("sk-ant-api03-плохой")
    assert "can't be in a key" in беда.value.message
    assert "Cyrillic letter" in (беда.value.hint or "")


def test_ключ_с_переводом_строки_это_отказ(песочница):
    """Ключ копируют из файла вместе с концом строки."""
    with pytest.raises(VertcutError) as беда:
        config.проверить_ключ("sk-ant-api03-abc\ndef")
    assert "line break" in беда.value.message


def test_негодный_ключ_не_записывается(песочница):
    """Человек узнаёт про негодный ключ тогда, когда вставил его,
    а не через минуту, нажав другую кнопку."""
    with pytest.raises(VertcutError):
        ai.настроить({"ключ": "sk-ant-api03-плохой"})
    assert config.model_key() is None


def test_негодный_ключ_из_окружения_тоже_не_проходит(песочница, monkeypatch):
    """Переменную окружения никто не проверял."""
    monkeypatch.setenv(config.MODEL_ENV, "sk-ant-плохой")
    with pytest.raises(VertcutError) as беда:
        ai.спросить("и", "т", потолок=10)
    assert "can't be in a key" in беда.value.message


def test_оборванный_ответ_и_пустой_ответ_разные_беды(песочница, monkeypatch):
    """Найдено на ПЕРВОМ ЖЕ живом обращении пятой сессии.

    Нынешние модели сначала думают, думанье считается в тот же потолок,
    и при тесном потолке текста не остаётся вовсе. Сервис говорил
    «модель ответила пустотой» на совершенно исправном ключе — то есть
    винил модель в том, что сделал сам.
    """
    config.write({config.MODEL_KEY: "sk-test-0001"})
    _ответил({**ANTHROPIC_ОТВЕТ, "content": [], "stop_reason": "max_tokens"},
             monkeypatch)
    with pytest.raises(VertcutError) as беда:
        ai.спросить("и", "т", потолок=10)
    # Сказано, куда ушли токены, и что ключ тут ни при чём.
    assert "went to thinking" in беда.value.message
    assert "your key is fine" in (беда.value.hint or "")

    # А пустота без обрыва остаётся пустотой.
    _ответил({**ANTHROPIC_ОТВЕТ, "content": []}, monkeypatch)
    with pytest.raises(VertcutError) as беда:
        ai.спросить("и", "т", потолок=10)
    assert "empty answer" in беда.value.message


def test_потолок_проверки_переживает_думанье():
    """Замер: на вопрос «готов?» claude-opus-5 тратит 46–66 токенов
    на думанье и 6 на ответ. При потолке 16 текста не оставалось."""
    assert tuning.ПОТОЛОК_ПРОВЕРКИ >= 256


def test_знаков_на_токен_считается_по_азбуке(песочница):
    """ЗАМЕР пятой сессии: у кириллицы токен вдвое короче.

    Одно число на оба языка занижало цену русского запроса на сорок
    процентов, а занизить цену — худшая из двух ошибок.
    """
    от_кириллицы = spend.токенов("это русский текст про кино" * 40)
    от_латиницы = spend.токенов("this is english text about films" * 40)
    # На тексте примерно одной длины кириллица даёт заметно больше
    # токенов — так и есть на самом деле.
    assert от_кириллицы > от_латиницы


def test_замер_двигает_оценку_только_в_осторожную_сторону(песочница):
    """Замер честнее поставляемого числа, но не всегда безопаснее.

    У двух РУССКИХ текстов отношение вышло разным — 1.51 у списка фраз
    и 2.15 у прозы. Замер, снятый на одном виде просьбы, занизил бы
    цену другому.
    """
    русский = "это русский текст про кино " * 40
    было = spend.знаков_на_токен(русский, "какая-то")

    # Поставщик оказался «щедрее» — знаков на токон больше, токенов
    # меньше, цена ниже. Такой замер не берётся.
    spend.записать("какая-то", 100, 10, 0.01, 1.0,
                   знаков_ушло=1000, азбука_="кир")
    assert spend.знаков_на_токен(русский, "какая-то") == было

    # А замер в осторожную сторону берётся.
    spend.записать("иная", 1000, 10, 0.01, 1.0,
                   знаков_ушло=800, азбука_="кир")
    assert spend.знаков_на_токен(русский, "иная") < было



def test_кончились_деньги_и_слишком_часто_разные_беды(песочница, monkeypatch):
    """429 у поставщика значит две РАЗНЫЕ вещи, и совет у них
    противоположный.

    Найдено на живом ключе OpenAI: сервис советовал подождать минуту
    там, где ждать можно было вечно — на счету не было денег.
    """
    config.write({config.MODEL_KEY: "sk-test-0001"})

    _ответил({"error": {"message": "You have no credits remaining.",
                        "type": "insufficient_quota",
                        "code": "credit_balance_exhausted"}},
             monkeypatch, код=429)
    with pytest.raises(VertcutError) as беда:
        ai.спросить("и", "т", потолок=10)
    # Пустой счёт: ждать бесполезно — это говорится прямо.
    assert "out of money" in беда.value.message
    assert "waiting will not help" in (беда.value.hint or "")

    _ответил({"error": {"message": "Rate limit reached",
                        "type": "rate_limit_error"}}, monkeypatch, код=429)
    with pytest.raises(VertcutError) as беда:
        ai.спросить("и", "т", потолок=10)
    # «Слишком часто»: здесь, наоборот, надо подождать.
    assert "Too many requests" in беда.value.message
    assert "just wait" in (беда.value.hint or "")


def test_порода_отказа_читается_полем_а_не_текстом(песочница, monkeypatch):
    """Сообщение поставщик пишет людям и меняет, когда захочет;
    `type` и `code` — договор.

    Текст остаётся запасным способом: у части посредников полей
    породы нет вовсе.
    """
    config.write({config.MODEL_KEY: "sk-test-0001"})
    _ответил({"error": {"message": "странные слова", "type": "quota_thing"}},
             monkeypatch, код=429)
    with pytest.raises(VertcutError) as беда:
        ai.спросить("и", "т", потолок=10)
    assert "out of money" in беда.value.message


def test_замер_ведётся_по_задаче_а_не_по_модели(песочница):
    """ЗАМЕР пятой сессии, и он поймал дыру в суточном стопе.

    Кандидаты и описания отвечают совершенно по-разному — 4765 и 2802
    токена против 305 и 212. Среднее по модели занижало оценку
    кандидатов впятеро, и стоп, поставленный на пять центов, пропустил
    запрос на шесть. То есть страховка не срабатывала бы ровно тогда,
    когда она нужна.
    """
    spend.записать("м", 100, 3000, 0.05, 30.0, задача=spend.КАНДИДАТЫ)
    spend.записать("м", 100, 200, 0.01, 5.0, задача=spend.ОПИСАНИЯ)

    кандидаты = spend.замер("м", spend.КАНДИДАТЫ)
    описания = spend.замер("м", spend.ОПИСАНИЯ)
    assert кандидаты["вышло_в_среднем"] == 3000
    assert описания["вышло_в_среднем"] == 200


def test_оценка_кандидатов_не_берёт_замер_описаний(песочница):
    """Та же дыра с другой стороны: оценка спрашивает свою задачу."""
    config.put(config.МОДЕЛЬ, "claude-opus-5")
    spend.записать("claude-opus-5", 100, 200, 0.01, 5.0,
                   задача=spend.ОПИСАНИЯ)
    оценка = spend.оценить("текст" * 100, 8000, spend.КАНДИДАТЫ)
    assert "no requests to this model yet" in оценка["откуда_оценка"]


def test_команда_ai_проверяет_то_же_что_экран():
    """До 24-й сессии `vertcut ai` писал в настройки сам и пропускал
    ключ с русской буквой, адрес `ftp://` и отрицательный стоп."""
    from vertcut import cli, config

    было = config.адрес()
    assert cli.main(["ai", "--api-address", "ftp://nope"]) == 1
    assert cli.main(["ai", "--api-key", "sk-аnt-1"]) == 1
    assert cli.main(["ai", "--daily-limit", "-3"]) == 1
    assert config.адрес() == было
    assert not config.model_key()
