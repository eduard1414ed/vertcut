"""Настройки: один файл, переменная окружения перебивает.

Пока настроек мало, но файл заведён словарём, а не строкой: следующая
приедет, и менять тогда формат файла, который уже лежит у человека
на диске, — работа на ровном месте.

**Ключ к модели живёт ЗДЕСЬ, а не в папке проекта.** Папка проекта под
присмотром git, и ключ, однажды туда попавший, оттуда уже не вынуть.

**И не в браузере, хотя дизайн говорит «в этом браузере».** Расхождение
названо вслух, потому что спека говорит другое — «ложится в настройки
снаружи репозитория», — и потому, что у браузера три беды сразу: ключ
не виден команде в терминале, пропадает от чистки браузера и заводится
заново в каждом браузере на машине. Экран об этом так и говорит: «в
файле настроек на этой машине», с путём.

**Ключ не печатается целиком никогда** — ни в лог, ни на экран, ни
в файл разбора. И лог, и разбор человек пришлёт в письме, когда что-то
не заработает. Наружу уходит хвост из четырёх знаков.
"""

from __future__ import annotations

import json
import os

from . import layout, tuning
from .errors import VertcutError

# Ключи в файле настроек. Литералы в одном месте: опечатка в таком
# литерале — это молча пустая настройка, а такую ошибку видно только
# через три шага.
MODEL_KEY = "anthropic_api_key"
OPENAI_KEY = "openai_api_key"
АДРЕС = "ai_адрес"
ПРОТОКОЛ = "ai_протокол"
МОДЕЛЬ = "ai_модель"
ПОРОГ = "ai_порог"
СТОП = "ai_стоп"
ЦЕНЫ = "ai_цены"
ПРОВЕРЕНО = "ai_проверено"
# Галочка «новые видео — без субтитров». Читается один раз, при разборе
# нового видео (`ingest.принять`), и запоминается в его `meta.json`:
# уже разобранные видео от неё не меняются.
НОВЫЕ_БЕЗ_СУБТИТРОВ = "новые_без_субтитров"

# Два протокола, и ровно два. Не «Claude или OpenAI», а «Claude или
# протокол OpenAI»: по второму говорят и сами OpenAI, и посредники,
# и модели, работающие прямо на машине человека, — последним ключ
# не нужен вовсе. Работы столько же, покрытие шире.
ANTHROPIC, OPENAI = "anthropic", "openai"

# Переменные окружения. У кого ключ уже заведён в оболочке, у того
# всё заработает само; имена взяты общепринятые, а не свои.
#
# Их две, потому что протокола два, и человек, у которого заведены
# оба, не должен выбирать. Берётся та, что отвечает выбранному
# протоколу: иначе ключ Anthropic уехал бы на чужой адрес.
#
# **По той же причине и в файле их два.** Сперва поле было одно —
# и переключение протокола отправляло ключ Anthropic на адрес OpenAI:
# отказ приходил «ключ не принят», то есть указывал ровно не туда,
# где беда. Ключ привязан к поставщику, а не к сервису.
MODEL_ENV = "ANTHROPIC_API_KEY"
OPENAI_ENV = "OPENAI_API_KEY"

# Что кладётся в файл при первой правке — чтобы поля на экране
# не были пустыми. Значения по умолчанию живут в `tuning.py` вместе
# с их происхождением; здесь только имена.
ПО_УМОЛЧАНИЮ = {
    ПРОТОКОЛ: ANTHROPIC,
    АДРЕС: tuning.АДРЕС_ANTHROPIC,
    МОДЕЛЬ: tuning.МОДЕЛЬ_ПО_УМОЛЧАНИЮ,
    ПОРОГ: tuning.ПОРОГ_СПРОСИТЬ,
    СТОП: tuning.СУТОЧНЫЙ_СТОП,
}


def read() -> dict:
    """Настройки с диска. Нет файла — пустой словарь, это не ошибка."""
    файл = layout.config_file()
    if not файл.exists():
        return {}
    try:
        data = json.loads(файл.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise VertcutError(
            f"The settings file is damaged: {файл}\n  {exc}",
            hint="delete it — Vertcut will make a new one",
        ) from None
    if not isinstance(data, dict):
        raise VertcutError(
            f"The settings file is damaged: {файл} — expected an object",
            hint="delete it — Vertcut will make a new one",
        )
    return data


def write(data: dict) -> None:
    файл = layout.config_file()
    файл.parent.mkdir(parents=True, exist_ok=True)
    файл.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n",
                    encoding="utf-8")
    # Ключ лежит в этом файле, и читать его должен только хозяин
    # машины. У Нарезатора это не проверялось; здесь сервис раздаётся,
    # и на общей машине разница настоящая.
    try:
        файл.chmod(0o600)
    except OSError:
        # Файловая система без прав (сетевой диск, чужая система) —
        # не повод падать: ключ уже записан, и это важнее.
        pass


def put(ключ: str, значение) -> None:
    data = read()
    data[ключ] = значение
    write(data)


def выбросить(ключ: str) -> None:
    data = read()
    if data.pop(ключ, None) is not None:
        write(data)


# ─────────────────────────────────────────────────────────────────────
# Ключ
# ─────────────────────────────────────────────────────────────────────

def протокол() -> str:
    какой = str(read().get(ПРОТОКОЛ) or ANTHROPIC).strip().lower()
    return какой if какой in (ANTHROPIC, OPENAI) else ANTHROPIC


def model_key() -> str | None:
    """Ключ к модели: сначала переменная окружения, потом файл.

    Переменная берётся ТА, что отвечает выбранному протоколу. У кого
    заведены обе, ключ Anthropic не уедет на адрес OpenAI — и наоборот.
    """
    свой = протокол() == ANTHROPIC
    из_среды = os.environ.get(MODEL_ENV if свой else OPENAI_ENV)
    if из_среды:
        return из_среды.strip()
    лежит = read().get(MODEL_KEY if свой else OPENAI_KEY)
    return str(лежит).strip() if лежит else None


def model_key_tail() -> str:
    """Хвост ключа для отчётов. Сам ключ не печатается никогда —
    ни в лог, ни на экран, ни в файл разбора."""
    ключ = model_key()
    return f"…{ключ[-4:]}" if ключ else "not set"


def откуда_ключ() -> str:
    """Где сервис его взял. Ключ при этом не называется.

    Нужно человеку, у которого ключ заведён и в оболочке, и в файле:
    без этой строки он правит один, а работает другой, и понять это
    неоткуда.
    """
    свой = протокол() == ANTHROPIC
    имя = MODEL_ENV if свой else OPENAI_ENV
    if os.environ.get(имя):
        return f"environment variable {имя}"
    if read().get(MODEL_KEY if свой else OPENAI_KEY):
        return f"file {layout.config_file()}"
    return "not set anywhere"


def адрес() -> str:
    свой = str(read().get(АДРЕС) or "").strip().rstrip("/")
    if свой:
        return свой
    return (tuning.АДРЕС_ANTHROPIC if протокол() == ANTHROPIC
            else tuning.АДРЕС_OPENAI)


def модель() -> str:
    return str(read().get(МОДЕЛЬ) or tuning.МОДЕЛЬ_ПО_УМОЛЧАНИЮ).strip()


def порог() -> float:
    return _число(ПОРОГ, tuning.ПОРОГ_СПРОСИТЬ)


def стоп() -> float:
    return _число(СТОП, tuning.СУТОЧНЫЙ_СТОП)


def новые_без_субтитров() -> bool:
    return bool(read().get(НОВЫЕ_БЕЗ_СУБТИТРОВ))


def задать_новые_без_субтитров(да: bool) -> None:
    """Галочка снята — ключа нет вовсе: пустой и снятый значат одно."""
    if да:
        put(НОВЫЕ_БЕЗ_СУБТИТРОВ, True)
    else:
        выбросить(НОВЫЕ_БЕЗ_СУБТИТРОВ)


def _число(ключ: str, если_нет: float) -> float:
    лежит = read().get(ключ)
    if лежит is None:
        return если_нет
    try:
        return float(лежит)
    except (TypeError, ValueError):
        raise VertcutError(
            f"Setting “{ключ}” is not a number: {лежит!r}",
            hint=f"fix {layout.config_file()} or set it again",
        ) from None


def цена(модель_: str) -> list[float] | None:
    """Цена за миллион токенов: [вход, выход]. Не знаем — None.

    **Не знаем — так и говорим.** Выдуманная цена хуже отсутствующей:
    человек, увидевший «≈$0.02», нажмёт не думая. Своя цена человека
    перебивает поставляемую: прейскурант у посредника свой, а у модели
    на его же машине цены нет вовсе.
    """
    свои = read().get(ЦЕНЫ) or {}
    пара = свои.get(модель_, tuning.ЦЕНЫ.get(модель_))
    if not пара:
        return None
    try:
        вход, выход = float(пара[0]), float(пара[1])
    except (TypeError, ValueError, IndexError):
        raise VertcutError(
            f"The price of model “{модель_}” is not a pair of numbers: {пара!r}",
            hint="it needs two numbers: dollars per million tokens in "
                 "and out",
        ) from None
    return [вход, выход]


def подключён() -> bool:
    """Можно ли вообще спрашивать модель.

    **Ключ нужен не всегда, и в этом весь смысл второй дороги.**
    Модель, запущенная прямо на машине человека, говорит по протоколу
    OpenAI и ключа не спрашивает вовсе — требовать его значило бы
    закрыть единственный способ пользоваться сервисом бесплатно.
    """
    if model_key():
        return True
    return протокол() == OPENAI and bool(str(read().get(АДРЕС) or "").strip())


def ключ_поле() -> str:
    """Под каким именем ключ лежит в файле — по нынешнему протоколу.

    Нужно тем, кто ключ КЛАДЁТ: команда и экран. Спрашивать это
    у них самих значило бы завести второе место, знающее про связь
    протокола и поля, — а разъехавшись, оно молча положило бы ключ
    не в то поле.
    """
    return MODEL_KEY if протокол() == ANTHROPIC else OPENAI_KEY


def проверить_ключ(ключ: str) -> str:
    """Годится ли эта строка в ключ. Не годится — отказ словами.

    **Пятое место в проекте, где русские буквы не проходят там, где
    их ждёшь.** Значение заголовка HTTP обязано быть латиницей — так
    велит стандарт, — и питон на кириллице не отказывает, а ПАДАЕТ:
    человек видит «сервис сломался», а сломался не сервис.

    Случай не выдуманный. Русская «с» неотличима от латинской `c`,
    и ключ, набранный или поправленный не в той раскладке, выглядит
    совершенно правильным. Найдено на живом экране: поддельный ключ
    с русскими буквами уронил обращение пятисотой.

    Перевод строки сюда попадает не реже: ключ копируют из файла
    вместе с концом строки.
    """
    чистый = str(ключ or "").strip()
    if not чистый:
        return чистый
    for знак in чистый:
        if ord(знак) > 127:
            raise VertcutError(
                f"The API key has a character that can't be in a key: "
                f"“{знак}”",
                hint="keys are Latin letters, digits and dashes. Most "
                     "often it's a Cyrillic letter typed instead of a "
                     "Latin one that looks the same: c, e, a, o, p, x. "
                     "Copy the key again, all of it")
        if знак.isspace() or ord(знак) < 32:
            raise VertcutError(
                "The API key has a space or a line break in it",
                hint="copy only the key itself, without the lines "
                     "around it")
    return чистый
