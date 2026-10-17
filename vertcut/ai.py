"""Одна функция: дать текст — получить текст.

## Правило спеки, и оно определяет всё остальное

**Внутри этой функции нет ничего, что знает про конкретного
поставщика; снаружи — тем более.** Модель делает здесь мало: две
стадии, оба раза текст на входе и текст на выходе, без картинок,
инструментов и длинного разговора. Значит поставщика можно менять
в одном месте — но только если обращения не расползлись по коду.

Правило дешёвое сейчас и дорогое потом.

## Две дороги, и почему именно эти

Не «Claude или OpenAI», а **Claude или протокол OpenAI**. По второму
говорят и сами OpenAI, и посредники, и модели, работающие прямо
на машине человека, — последним ключ не нужен вовсе. Работы столько же,
покрытие шире.

## Ни одной новой зависимости

Обе дороги идут обычным HTTP из стандартной библиотеки — тем же
способом, каким сервис поднимает свой экран.

Причина не в экономии места. Официальная библиотека Anthropic
не говорит по протоколу OpenAI, то есть одну из двух дорог пришлось бы
писать руками в любом случае, — а функция, у которой внутри две разные
библиотеки, это уже не одна функция. Тело запроса тут крошечное: имя
модели, потолок ответа, инструкция и текст.

## Общий знаменатель, а не всё, что умеет каждый

Отправляется самое простое тело, которое понимают оба. Ни глубины
думанья, ни жёсткой формы ответа, ни подсчёта токенов чужой ручкой —
всё это есть у одного и может отсутствовать у другого, и стоило бы
завести это здесь, как дороги разошлись бы: у одного поставщика
работает так, у другого иначе, и понять почему было бы неоткуда.

## Отказы говорят РАЗНЫМИ словами

Человек должен понять, ждать ему, платить или исправлять. «Не получилось
обратиться к модели» на все случаи — это отказ, после которого чинят
наугад:

  · нет ключа            — исправлять, и сказано где;
  · нет связи            — ждать, и сказано с каким адресом;
  · ключ не принят       — исправлять ключ;
  · слишком часто        — ждать, и сколько именно, если сказали;
  · у поставщика беда    — ждать;
  · просьба не понравилась — исправлять, и приведено, что ответил сам
    поставщик (обычно там имя модели, которой у него нет);
  · не дождались         — ждать или уменьшить запрос.

## Сеть только здесь

Четвёртая сессия завела правило «сервис обязан работать без сети»
и раздаёт шрифты со своего диска. Эта сессия впервые вводит сеть,
и заслон на это правило нужен: автотесты в сеть не ходят вовсе,
и молчаливое обращение к сети из середины разбора не поймал бы никто.

**Ни один файл главной дороги — разбор, фразы, кадр, субтитры,
сборка — этого модуля не знает.** Есть автотест, который падает,
если такой импорт появится, и второй — который следит, что наружу
ходят только отсюда.
"""

from __future__ import annotations

import json
import socket
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import datetime

from . import config, layout, spend, tuning
from .errors import VertcutError


@dataclass
class Ответ:
    """Что вернулось. Текст и правда про деньги, ничего больше."""

    текст: str
    модель: str
    вошло: int          # токенов на входе — со слов поставщика
    вышло: int          # токенов на выходе — со слов поставщика
    деньги: float | None
    секунд: float
    оборвался: bool     # упёрся в потолок ответа
    посчитал_сам: bool  # поставщик промолчал про токены, считали мы


def спросить(инструкция: str, текст: str, *, потолок: int,
             разрешено_дорого: bool = False,
             задача: str = spend.КАНДИДАТЫ) -> Ответ:
    """Дать текст — получить текст. Единственная дорога к модели.

    `инструкция` — что делать; `текст` — с чем. Разделены потому, что
    оба протокола разделяют их сами, а не потому, что нам так удобнее.

    Деньги проверяются ДО отправки и записываются СРАЗУ после ответа —
    до того, как ответ начнут разбирать. Разбор может не удаться,
    а деньги уже потрачены.
    """
    if not config.подключён():
        raise VertcutError(
            "No API key — there is nobody to ask",
            hint="add one in Settings → “AI and API key”, or set the "
                 f"{config.MODEL_ENV} environment variable. Everything else "
                 "works without a key: you choose segments by phrase and "
                 "write descriptions yourself",
        )

    # И на отправке тоже: ключ мог приехать из переменной окружения,
    # а её никто не проверял.
    config.проверить_ключ(config.model_key() or "")

    оценка = spend.оценить(инструкция + текст, потолок, задача)
    spend.проверить_порог(оценка["деньги"], разрешено_дорого)
    spend.проверить_стоп(оценка["деньги"])

    протокол = config.протокол()
    адрес, заголовки, тело = (
        _просьба_anthropic if протокол == config.ANTHROPIC
        else _просьба_openai
    )(инструкция, текст, потолок)

    начали = time.monotonic()
    сырое = _сходить(адрес, заголовки, тело)
    секунд = round(time.monotonic() - начали, 2)

    разбор = (_ответ_anthropic if протокол == config.ANTHROPIC
              else _ответ_openai)(сырое)

    # Поставщик может и промолчать про токены — так делают некоторые
    # посредники и часть местных моделей. Тогда считаем сами и говорим,
    # что считали сами: число со слов поставщика и своя прикидка —
    # разные вещи, и путать их нельзя.
    посчитал_сам = разбор["вошло"] is None or разбор["вышло"] is None
    вошло = разбор["вошло"] if разбор["вошло"] is not None \
        else spend.токенов(инструкция + текст)
    вышло = разбор["вышло"] if разбор["вышло"] is not None \
        else spend.токенов(разбор["текст"])

    цена = config.цена(разбор["модель"] or config.модель())
    деньги = None
    if цена:
        деньги = round(вошло / 1e6 * цена[0] + вышло / 1e6 * цена[1], 6)
    spend.записать(разбор["модель"] or config.модель(), вошло, вышло,
                   деньги, секунд,
                   знаков_ушло=len(инструкция) + len(текст),
                   азбука_=spend.азбукой(текст), задача=задача)

    if разбор["отказ"]:
        raise VertcutError(
            f"The model refused to answer: {разбор['отказ']}",
            hint="this is the provider's decision, not Vertcut's. "
                 "Try a different segment or a different model",
        )
    if not разбор["текст"].strip():
        # **Пустой ответ и ОБОРВАННЫЙ ответ — разные беды**, и валить
        # их в одну значило бы винить модель в том, что сделал сервис.
        #
        # Нынешние модели сначала думают, думанье считается в тот же
        # потолок, и при тесном потолке текста не остаётся вовсе.
        # Поймано на ПЕРВОМ ЖЕ живом обращении пятой сессии: проверка
        # ключа возвращала «модель ответила пустотой» на совершенно
        # исправном ключе, потому что все её шестнадцать токенов
        # уходили в думанье.
        if разбор["оборвался"]:
            raise VertcutError(
                f"No answer left: all {вышло} tokens went to thinking, "
                "and the limit ran out before the answer",
                hint="your key is fine. Current models think before they "
                     "answer, and the thinking counts toward the same "
                     "limit. Pick a simpler model — or tell the Vertcut "
                     "author: the limits live in tuning.py",
            )
        raise VertcutError(
            "The model sent an empty answer",
            hint="the request is paid for, but there is no answer in it. "
                 "Try again or pick another model in Settings",
        )
    return Ответ(текст=разбор["текст"], модель=разбор["модель"] or config.модель(),
                 вошло=вошло, вышло=вышло, деньги=деньги, секунд=секунд,
                 оборвался=разбор["оборвался"], посчитал_сам=посчитал_сам)


def проверить() -> dict:
    """Отвечает ли ключ. Одно дешёвое обращение, а не «наверное, да».

    Потолок ответа в пару токенов: проверка обязана стоить столько,
    чтобы её не жалко было нажать. Просить «ответь одним словом» и
    смотреть, что вернулось, незачем — нам нужен сам факт, что адрес
    ответил, ключ принят и модель у поставщика есть.
    """
    начали = time.monotonic()
    ответ = спросить("Reply with one word: ready.", "ready?",
                     потолок=tuning.ПОТОЛОК_ПРОВЕРКИ,
                     разрешено_дорого=True, задача="проверка")
    # Когда ключ отвечал в последний раз. Макет показывает это строкой
    # в шапке блока, и она стоит того: человек, у которого перестало
    # работать, первым делом смотрит именно сюда.
    config.put(config.ПРОВЕРЕНО,
               datetime.now().astimezone().isoformat(timespec="minutes"))
    return {
        "отвечает": True,
        "модель": ответ.модель,
        "секунд": round(time.monotonic() - начали, 2),
        "хвост_ключа": config.model_key_tail(),
        "адрес": config.адрес(),
        "протокол": config.протокол(),
        "стоило": ответ.деньги,
    }


# ─────────────────────────────────────────────────────────────────────
# Дорога Anthropic
# ─────────────────────────────────────────────────────────────────────

# Версия протокола. Заголовок обязателен, и значение у него своё
# у каждого поставщика — здесь оно к дороге и привязано.
ВЕРСИЯ_ANTHROPIC = "2023-06-01"


def _просьба_anthropic(инструкция: str, текст: str, потолок: int):
    заголовки = {
        "content-type": "application/json",
        "anthropic-version": ВЕРСИЯ_ANTHROPIC,
    }
    ключ = config.model_key()
    if ключ:
        заголовки["x-api-key"] = ключ
    тело = {
        "model": config.модель(),
        "max_tokens": потолок,
        "system": инструкция,
        "messages": [{"role": "user", "content": текст}],
    }
    return f"{config.адрес()}/messages", заголовки, тело


def _ответ_anthropic(это: dict) -> dict:
    куски = это.get("content") or []
    текст = "".join(к.get("text") or "" for к in куски
                    if isinstance(к, dict) and к.get("type") == "text")
    расход = это.get("usage") or {}
    почему = это.get("stop_reason")
    отказ = None
    if почему == "refusal":
        подробно = (это.get("stop_details") or {}).get("explanation")
        отказ = подробно or "the provider gave no reason"
    return {
        "текст": текст,
        "модель": это.get("model") or "",
        "вошло": _цел(расход.get("input_tokens")),
        "вышло": _цел(расход.get("output_tokens")),
        "оборвался": почему == "max_tokens",
        "отказ": отказ,
    }


# ─────────────────────────────────────────────────────────────────────
# Дорога протокола OpenAI
# ─────────────────────────────────────────────────────────────────────

def _просьба_openai(инструкция: str, текст: str, потолок: int):
    заголовки = {"content-type": "application/json"}
    ключ = config.model_key()
    if ключ:
        # Ключа может не быть вовсе, и это законный случай: модель
        # на машине человека его не спрашивает. Заголовок тогда
        # не ставится — пустой «Bearer » часть серверов отвергает.
        заголовки["authorization"] = f"Bearer {ключ}"
    тело = {
        "model": config.модель(),
        "max_tokens": потолок,
        "messages": [{"role": "system", "content": инструкция},
                     {"role": "user", "content": текст}],
    }
    return f"{config.адрес()}/chat/completions", заголовки, тело


def _ответ_openai(это: dict) -> dict:
    выборы = это.get("choices") or []
    первый = выборы[0] if выборы else {}
    сообщение = первый.get("message") or {}
    текст = сообщение.get("content") or ""
    расход = это.get("usage") or {}
    почему = первый.get("finish_reason")
    return {
        "текст": текст if isinstance(текст, str) else "",
        "модель": это.get("model") or "",
        "вошло": _цел(расход.get("prompt_tokens")),
        "вышло": _цел(расход.get("completion_tokens")),
        "оборвался": почему == "length",
        "отказ": сообщение.get("refusal") or None,
    }


def _цел(значение) -> int | None:
    try:
        return int(значение)
    except (TypeError, ValueError):
        return None


# ─────────────────────────────────────────────────────────────────────
# Сеть: единственное место во всём сервисе, откуда он выходит наружу
# ─────────────────────────────────────────────────────────────────────

# Часть серверов протокола OpenAI отвергает `max_tokens` и требует
# `max_completion_tokens` — так сделали у себя сами OpenAI на новых
# моделях. Отличить одно от другого заранее нельзя: адрес произвольный.
#
# Поэтому одна повторная попытка, и только на этот случай: если отказ
# назвал новое имя поля, просьба уходит ещё раз с ним. Не «пробуем оба
# наугад» — переименование делается по слову самого поставщика.
ПОЛЕ_ПОТОЛКА = "max_completion_tokens"


def _сходить(адрес: str, заголовки: dict, тело: dict) -> dict:
    try:
        return _послать(адрес, заголовки, тело)
    except VertcutError as беда:
        подсказал = getattr(беда, "сказал_поставщик", "") or ""
        if ПОЛЕ_ПОТОЛКА in подсказал and "max_tokens" in тело:
            ещё = dict(тело)
            ещё[ПОЛЕ_ПОТОЛКА] = ещё.pop("max_tokens")
            return _послать(адрес, заголовки, ещё)
        raise


def _послать(адрес: str, заголовки: dict, тело: dict) -> dict:
    просьба = urllib.request.Request(
        адрес, method="POST",
        data=json.dumps(тело, ensure_ascii=False).encode("utf-8"),
        headers=заголовки)
    try:
        # Открывалка берётся своя и БЕЗ обработчиков окружения: иначе
        # питон подхватил бы системный прокси, и запрос с ключом ушёл бы
        # не туда, куда обещано человеку на экране («куда уходит —
        # только на этот адрес»).
        открывалка = urllib.request.build_opener(
            urllib.request.HTTPSHandler(), urllib.request.HTTPHandler())
        with открывалка.open(просьба, timeout=tuning.ЖДЁМ_ОТВЕТА) as ответ:
            сырое = ответ.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as беда:
        raise _отказ_поставщика(беда) from None
    except socket.timeout:
        raise VertcutError(
            f"No answer within {tuning.ЖДЁМ_ОТВЕТА:.0f} s",
            hint="nothing is broken: a long transcript takes a while. "
                 "Try again or pick a faster model",
        ) from None
    except urllib.error.URLError as беда:
        причина = getattr(беда, "reason", беда)
        if isinstance(причина, socket.timeout):
            raise VertcutError(
                f"No answer within {tuning.ЖДЁМ_ОТВЕТА:.0f} s",
                hint="try again or pick a faster model",
            ) from None
        raise VertcutError(
            f"Cannot reach {адрес}: {причина}",
            hint="check your internet connection and the API address "
                 "in Settings. Everything else in Vertcut "
                 "works offline — analysis, crop, subtitles, export",
        ) from None

    try:
        это = json.loads(сырое)
    except json.JSONDecodeError:
        raise VertcutError(
            f"{адрес} sent back something unexpected",
            hint=f"it started with: {сырое[:200]!r}. The address probably "
                 "does not lead to a model — check it in Settings",
        ) from None
    if not isinstance(это, dict):
        raise VertcutError(
            f"{адрес} sent an answer in an unknown format",
            hint="check the API address and API type in Settings")
    return это


# Слова, по которым поставщик называет пустой счёт. Смотрим на ПОРОДУ
# отказа (`type`/`code`), а не на текст сообщения: сообщение пишется
# людям и меняется, когда поставщику вздумается. Текст остаётся
# запасным способом — у некоторых посредников поля породы нет вовсе.
ПРО_ДЕНЬГИ = ("quota", "credit", "billing", "balance", "payment", "funds")


def _деньги_кончились(порода: str, сказал: str) -> bool:
    низом = порода.lower()
    if any(с in низом for с in ПРО_ДЕНЬГИ):
        return True
    return any(с in сказал.lower() for с in ПРО_ДЕНЬГИ)


def _отказ_поставщика(беда: urllib.error.HTTPError) -> VertcutError:
    """Разные коды — разные слова. Ждать, платить или исправлять."""
    код = беда.code
    сказал, порода = "", ""
    try:
        тело = json.loads(беда.read().decode("utf-8", errors="replace"))
        ошибка = тело.get("error") or {}
        сказал = str(ошибка.get("message") or тело.get("message") or "")
        # Порода отказа — СЛОВОМ поставщика, а не разбором его текста.
        # Оба протокола кладут её отдельным полем, и это единственное,
        # на что тут можно опереться: сообщение они пишут людям
        # и меняют, когда захотят.
        порода = f"{ошибка.get('type') or ''} {ошибка.get('code') or ''}"
    except Exception:                      # noqa: BLE001
        # Отказ на отказе — не повод потерять сам отказ. Код у нас
        # уже есть, и он говорит главное.
        сказал = ""

    if код in (401, 403):
        свой = VertcutError(
            f"API key not accepted ({код}): {сказал or 'the provider gave no reason'}",
            hint=f"the key used is {config.model_key_tail()} — "
                 f"{config.откуда_ключ()}. Check that it has not expired "
                 "and still has money on it")
    elif код == 429 and _деньги_кончились(порода, сказал):
        # **429 у поставщика значит две РАЗНЫЕ вещи**, и совет у них
        # противоположный. «Слишком часто» — подождите. «Кончились
        # деньги на счету» — ждать бесполезно, надо положить денег.
        #
        # Найдено на живом ключе OpenAI: сервис советовал подождать
        # минуту там, где ждать можно было вечно.
        свой = VertcutError(
            f"Your provider account is out of money ({код}): "
            f"{сказал or 'no reason given'}",
            hint="waiting will not help — this is your balance with the "
                 "provider. Add money or use another key. Vertcut's daily "
                 "limit has nothing to do with it: that counts your "
                 "spending, this is your balance")
    elif код == 429:
        когда = беда.headers.get("retry-after") if беда.headers else None
        свой = VertcutError(
            f"Too many requests ({код}): {сказал or 'the provider gave no reason'}",
            hint=(f"just wait: the provider asks to come back in {когда} s"
                  if когда else
                  "just wait: try again in a minute. Refusals are "
                  "not charged"))
    elif код == 404:
        свой = VertcutError(
            f"Nothing at this address ({код}): "
            f"{сказал or 'the provider gave no reason'}",
            hint=f"the address is {config.адрес()} — check it and the "
                 "API type in Settings")
    elif код >= 500:
        свой = VertcutError(
            f"The provider has a problem ({код}): {сказал or 'no reason given'}",
            hint="nothing to fix here, just wait: try again in a few "
                 "minutes. Refusals are not charged")
    else:
        свой = VertcutError(
            f"The provider rejected the request ({код}): "
            f"{сказал or 'no reason given'}",
            hint=f"most often it is the model name: “{config.модель()}” — "
                 "it must be written exactly as in your provider's docs. "
                 "Change it in Settings")
    # Слова поставщика оставляем на объекте: по ним выше решается,
    # не переименовать ли поле потолка. В сообщение они уже вошли.
    свой.сказал_поставщик = сказал
    return свой


# ─────────────────────────────────────────────────────────────────────
# Что показать человеку про ключ и деньги
# ─────────────────────────────────────────────────────────────────────
#
# Живёт ЗДЕСЬ, а не в веб-слое, по правилу проекта: у ручки ровно три
# работы — взять слова из просьбы, позвать функцию, отдать её ответ.
# Собери этот словарь в ручке, и в ней окажется знание о том, какая
# цена откуда берётся, — то есть логика.

def как_дела() -> dict:
    """Ключ, адрес, деньги и инструкции — одним ответом.

    **Ключ сюда не попадает, только хвост.** Ни в один ответ сервиса
    он не уезжает: страницу человек показывает на записи экрана, когда
    просит помощи.
    """
    from . import prompts

    модель_ = config.модель()
    прошло = spend.день()
    было = spend.замер(модель_)
    return {
        "подключён": config.подключён(),
        "протокол": config.протокол(),
        "адрес": config.адрес(),
        "модель": модель_,
        "хвост_ключа": config.model_key_tail(),
        "откуда_ключ": config.откуда_ключ(),
        "ключ_есть": bool(config.model_key()),
        # «Где лежит» — расхождение с дизайном, названное вслух:
        # он говорит «в этом браузере», спека — «в настройках снаружи
        # репозитория». Человеку показывается путь, а не обещание.
        "где_лежит": str(layout.config_file()),
        "проверено": config.read().get(config.ПРОВЕРЕНО),
        "цена_модели": config.цена(модель_),
        "цены_сверены": tuning.ЦЕНЫ_СВЕРЕНЫ,
        "порог": config.порог(),
        "стоп": config.стоп(),
        "за_сегодня": прошло,
        "замер": было,
        "по_умолчанию": {
            "модель": tuning.МОДЕЛЬ_ПО_УМОЛЧАНИЮ,
            "адрес_anthropic": tuning.АДРЕС_ANTHROPIC,
            "адрес_openai": tuning.АДРЕС_OPENAI,
        },
        "инструкции": {
            какая: {"текст": prompts.прочитать(какая),
                    "своя": prompts.своя_ли(какая),
                    "поставляемая": prompts.поставляемая(какая)}
            for какая in prompts.ВСЕ
        },
        "эталоны": prompts.эталоны(),
    }


def настроить(что: dict) -> dict:
    """Поправить поля ключа. Что пришло, то и правится.

    **Ключ кладётся в поле, отвечающее протоколу, и протокол меняется
    ПЕРВЫМ.** Иначе ключ, присланный вместе с новым протоколом, лёг бы
    в поле старого — и молча не заработал.

    **Смена протокола тянет за собой адрес**, если человек его
    не трогал: адреса у поставщиков разные, и оставить старый значит
    отправить ключ Anthropic на `api.openai.com`. Свой адрес при этом
    не трогается — человек его для того и вписывал.
    """
    if "протокол" in что:
        новый = str(что["протокол"]).strip().lower()
        if новый not in (config.ANTHROPIC, config.OPENAI):
            raise VertcutError(
                f"Unknown API type: {новый}",
                hint="there are two: anthropic and openai")
        был_адрес = config.адрес()
        config.put(config.ПРОТОКОЛ, новый)
        if "адрес" not in что and был_адрес == _адрес_по_умолчанию(
                config.ANTHROPIC if новый == config.OPENAI else config.OPENAI):
            config.выбросить(config.АДРЕС)

    if "ключ" in что:
        # Проверяется В МОМЕНТ ЗАПИСИ, а не только при обращении:
        # человек должен узнать про негодный ключ тогда, когда он его
        # вставил, а не через минуту, нажав другую кнопку.
        ключ = config.проверить_ключ(что["ключ"])
        if ключ:
            config.put(config.ключ_поле(), ключ)
        else:
            config.выбросить(config.ключ_поле())
    if "адрес" in что:
        адрес = str(что["адрес"] or "").strip()
        if адрес and not адрес.startswith(("http://", "https://")):
            raise VertcutError(
                f"The API address must start with http:// or https://: "
                f"{адрес}",
                hint="for example, https://api.anthropic.com/v1")
        config.put(config.АДРЕС, адрес) if адрес \
            else config.выбросить(config.АДРЕС)
    if "модель" in что:
        имя = str(что["модель"] or "").strip()
        if not имя:
            raise VertcutError(
                "The model name is empty",
                hint="type it exactly as your provider's documentation "
                     "spells it, or choose it from the provider's list")
        config.put(config.МОДЕЛЬ, имя)
    for имя, куда, зовут in (("порог", config.ПОРОГ, "Ask above"),
                             ("стоп", config.СТОП, "Daily limit")):
        if имя in что:
            config.put(куда, _деньгами(что[имя], зовут))
    if "цена" in что:
        config.put(config.ЦЕНЫ, {**(config.read().get(config.ЦЕНЫ) or {}),
                                 config.модель(): _пара_цен(что["цена"])})
    return как_дела()


def _адрес_по_умолчанию(протокол: str) -> str:
    return (tuning.АДРЕС_ANTHROPIC if протокол == config.ANTHROPIC
            else tuning.АДРЕС_OPENAI)


def _деньгами(значение, имя: str) -> float:
    try:
        число = float(значение)
    except (TypeError, ValueError):
        raise VertcutError(f"“{имя}” must be a number, got: "
                           f"{значение!r}") from None
    if число < 0:
        raise VertcutError(f"“{имя}” can't be less than zero")
    return число


def _пара_цен(значение) -> list[float]:
    try:
        вход, выход = float(значение[0]), float(значение[1])
    except (TypeError, ValueError, IndexError, KeyError):
        raise VertcutError(
            "A price is two numbers: dollars per million input "
            "and output tokens") from None
    return [вход, выход]


# ─────────────────────────────────────────────────────────────────────
# Какие модели есть у поставщика
# ─────────────────────────────────────────────────────────────────────
#
# **Список не вшивается — он спрашивается.** Спека запрещает держать
# в сервисе список названий моделей, и правильно: вшитый устареет
# молча. Но голое поле, в которое надо вписать `claude-opus-5` знак
# в знак, — это не «мы честны», это «разбирайтесь сами».
#
# Выход в том, что список есть у самого поставщика. Обе дороги
# отдают его по ОДНОМУ И ТОМУ ЖЕ адресу `/models` и в одном и том же
# виде — `data[].id`, — так что спрашивать его можно, не зная,
# с кем говоришь. Такой список не устареет: он приезжает в тот день,
# когда модель выпустили.
#
# Поле при этом никуда не девается. Посредник может `/models`
# не отдавать вовсе, и тогда имя вписывается руками — как в дизайне.
# Это расхождение с дизайном в сторону человека, и оно названо вслух.

def модели() -> dict:
    """Что есть у поставщика по его собственным словам.

    Не отвечает — это не поломка: часть посредников такого адреса
    не держит. Тогда так и говорится, и остаётся поле для имени.
    """
    заголовки = {"content-type": "application/json"}
    ключ = config.model_key()
    if config.протокол() == config.ANTHROPIC:
        заголовки["anthropic-version"] = ВЕРСИЯ_ANTHROPIC
        if ключ:
            заголовки["x-api-key"] = ключ
    elif ключ:
        заголовки["authorization"] = f"Bearer {ключ}"

    это = _взять(f"{config.адрес()}/models", заголовки)
    ряд = это.get("data") if isinstance(это, dict) else None
    if not isinstance(ряд, list):
        raise VertcutError(
            f"The provider at {config.адрес()} did not send a list "
            "of models",
            hint="nothing is broken: some proxies don't offer one. Type "
                 "the model name yourself — it's in your provider's "
                 "documentation")
    вышло = []
    for это_ in ряд:
        if not isinstance(это_, dict):
            continue
        имя = str(это_.get("id") or "").strip()
        if имя:
            вышло.append({"имя": имя,
                          "зовут": str(это_.get("display_name") or "").strip()})
    return {"модели": вышло, "ещё_есть": bool(это.get("has_more")),
            "адрес": config.адрес()}


def _взять(адрес: str, заголовки: dict) -> dict:
    """GET. Отдельно от POST нарочно: тело у него другое, а отказы
    те же самые — их разбирает одно место."""
    просьба = urllib.request.Request(адрес, method="GET", headers=заголовки)
    try:
        открывалка = urllib.request.build_opener(
            urllib.request.HTTPSHandler(), urllib.request.HTTPHandler())
        with открывалка.open(просьба, timeout=tuning.ЖДЁМ_ОТВЕТА) as ответ:
            сырое = ответ.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as беда:
        raise _отказ_поставщика(беда) from None
    except (socket.timeout, urllib.error.URLError) as беда:
        причина = getattr(беда, "reason", беда)
        raise VertcutError(
            f"Cannot reach {адрес}: {причина}",
            hint="check your internet connection and the API address "
                 "in Settings") from None
    try:
        return json.loads(сырое)
    except json.JSONDecodeError:
        raise VertcutError(
            f"{адрес} sent back something unexpected",
            hint="the address probably does not lead to a model — "
                 "check it in Settings") from None
