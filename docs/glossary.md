# Словарь: русское слово → слово на экране

Всё, что видит человек, — по-английски. Один термин — одно слово
везде: на экране, в сообщениях, в команде, в установке. Нашёл понятие,
которого здесь нет, — сперва впиши его сюда, потом пиши текст.

Английский — простой, разговорный, короткий. Без жаргона монтажёра
и программиста там, где есть обычное слово.

## Главные понятия

| русское | на экране | пояснение |
|---|---|---|
| видео (исходное) | **video** | *source video* — только там, где без него непонятно |
| ролик, вертикалка | **clip** | |
| кусок, фрагмент | **segment** | шаг маршрута — **Segments** |
| разбор, разобрать | **analysis**, **Analyze** | идёт — *Analyzing…*; готов — *Analyzed* |
| сборка, собрать | **export**, **Export** | идёт — *Exporting…*; готов — *Exported* |
| фраза | **phrase** | |
| строка субтитра | **line** | |
| страница субтитра (что видно разом) | **page** | |
| план | **shot** | |
| склейка | **cut** | граница между планами |
| кадр | **frame** | |
| рамка | **crop** | не *frame*: кадр уже *frame* |
| вид (готовый, `looks.yaml`) | **preset** | |
| стиль, профиль субтитров | **subtitle style** | «профиль» человек не видит |
| поставляемый стиль | **default style** | |
| мой стиль, личный образец | **my style** | |
| стиль видео / вертикалки | **this video's style / this clip's style** | |
| раздать всем | **Apply to all clips** | |
| подложка (без / плашка / обводка) | **background** | значения: *none / box / outline* |
| плашка под текстом субтитра | **box** | не путать с плашкой в конце |
| плашка в конце, хвост | **end card** | |
| надпись на плашке | **end card text** | |
| обложка выпуска | **thumbnail** | |
| заслон, сверка | **check** | «5 checks» |
| штамп | — | слова нет; человек видит **up to date / out of date** |
| устарел | **out of date — export again** | |
| очередь | **queue** | |
| описание | **description** | не *caption*: так по-английски зовут и субтитры |
| предложения модели | **AI suggestions** | |
| эталонные описания, «ваши настоящие подписи» | **your samples** | |
| инструкция модели | **prompt** | |
| сценарий | **script** | |
| расшифровка | **transcript** | |
| распознавание | **transcribing** | в ходе работы — *Transcribing…* |
| укладка | **syncing text to speech** | |
| стадия разбора | **stage** | не *step*: step — шаг маршрута слева |
| шаг маршрута (колонка слева) | **step** | блок зовётся **steps**: Analyze → Segments → Descriptions → Export |
| состояние стадии: сделана / идёт / ждёт / не доделан | **done / running / waiting / unfinished** | у дела в очереди «идёт» — *exporting*, см. «Вертикалка и сборка» |
| нарезка фраз | **splitting phrases** | в имени стадии |
| годен / негоден (предложение AI) | **usable / not usable** | |
| «вертикалка есть» (по этому предложению) | **clip exists** | метка на карточке |
| прикидка (время края не измерено) | **estimated** | «start is estimated» |
| услышанное слово | **heard word** | |
| обвес (файлы внутри пакета) | **bundled files** | в `vertcut check` |

## На экране и в сообщениях

| русское | на экране | пояснение |
|---|---|---|
| Входящие | **Inbox** | папка, куда ложатся брошенные в окно видео |
| принять видео (из Inbox) | **Add** | кнопка; общее действие — **Add video** |
| бросить в окно | **drop** | «Drop a video here» |
| выбрать на диске | **Choose file** | кнопка и её упоминания в тексте |
| системный диалог выбора | **file picker** | |
| журнал разбора (`meta.json`) | **analysis data** | не *log*: log — это `logs/` |
| разобрано / не разобрано / в процессе | **analyzed / not analyzed / in progress** | метка видео |
| отпечаток файла | **fingerprint** | |
| папка сервиса | **the Vertcut folder** | |
| «Если не работает» | **Not working?** | строка в колонке и экран помощи |
| журнал | **log** | |
| ключ (AI) | **API key** | |
| поставщик | **provider** | |
| протокол (Anthropic / OpenAI) | **API type** | |
| адрес API | **API address** | |
| модель | **model** | |
| расходы | **spending** | |
| «спрашивать, если дороже» | **ask above $…** | |
| суточный стоп | **daily limit** | |
| кегль | **size** | |
| межстрочное расстояние | **line spacing** | |
| обводка, тень | **outline, shadow** | |
| подсветка по словам | **karaoke** | цветом / плашкой / кеглем — *color / box / size* |
| регистр: как есть / прописные / капитель | **case: as typed / ALL CAPS / Small Caps** | |
| безопасные зоны | **safe zones** | |
| от низа, поля по бокам | **from bottom, side margins** | |
| черновик (просмотр без сборки) | **preview** | |
| исходник | **original** | |
| разделить / склеить фразу | **Split / Merge** | |
| убрать (из списка, из настроек) | **Remove** | файлы на диске остаются |
| удалить (с диска) | **Delete** | необратимо; кнопка подтверждения — **Delete permanently** |
| вернуть (стиль, рамку, инструкцию) | **Reset** | |
| отмена | **Cancel** | |
| слаг (имя разбора в команде) | **video id** | в справке команды — `VIDEO_ID` |
| ключ вертикалки (`0202-0363`) | **clip id** | в справке команды — `CLIP_ID` |
| сервис | **Vertcut** | по имени, а не «the service» |
| программа | **app** | |
| Поддержать | **Support** | |
| AI | **AI** | |
| раздел «AI и ключ» в настройках | **AI and API key** | |
| дальше, к шагу | **Next: …** | «Next: segments» |
| создать вертикалку | **Create clip** | |
| свой текст (вставить кусок сценария) | **Your text** | ссылка — **paste your own text** |
| кусок сценария (вставленный текст) | **part of the script** | не *piece* и не *segment*: segment — кусок ВИДЕО |
| найти в видео | **Find in video** | |
| снять выбор | **clear** | |
| слушать / хватит | **Listen / Stop** | |
| ← ко всем видео | **← all videos** | |
| спросить AI / спросить заново | **Ask AI / Ask again** | |
| подключить ключ | **Add API key** | |
| остановить разбор | **stop analysis** | |
| разобрать / продолжить / разобрать заново | **Analyze / Continue analysis / analyze again** | |
| токен | **token** | |
| страница прислала неполную просьбу | **The page sent an incomplete request** | поломка самой страницы; имени поля человек не видит — оно русское, договор страницы с сервером |
| перезагрузить страницу | **reload the page** | |

## Вертикалка и сборка

| русское | на экране | пояснение |
|---|---|---|
| собрана (свежая) | **exported** | |
| устарела | **out of date** | подсказка — *export again* |
| не собрана | **not exported** | |
| дело в очереди: ждёт / идёт / упало / отменено / удалено | **waiting / exporting / failed / canceled / deleted** | *canceled* — с одной *l* |
| надо собрать, но в очередь не поставлена | **not queued** | |
| собрать (одну, в строке очереди) | **Export** | |
| собрать вертикалку (главная кнопка) | **Export clip** | |
| собрать заново | **Export again** | |
| собрать всё | **Export all** | |
| повторить (упавшую) | **Try again** | |
| остановить сборку | **stop export** | как *stop analysis* |
| скачать | **Download** | |
| показать в папке | **Show in folder** | и для всей папки, и для одного файла |
| пять заслонов по именам | **Length, Picture, Cuts, Subtitles, End card** | *Cuts* — кадры у склеек, где меняется рамка или режим; это тот же *cut*, что «склейка» |
| итог заслонов | **all 5 checks passed** | пропущенная проверка не считается прошедшей: *all 3 checks passed · skipped: Cuts, End card*; не прошла — *failed: Picture · passed: Length, Subtitles*; числа сверки — подсказкой при наведении |
| проверка пропущена (проверять нечего) | **skipped** | без плашки; у стыков, где рамка не меняется |
| время сборки в строке готового | **export took 6.1 s** | не *exported in*: рядом длина ролика, и путались |
| не прошёл заслон | **failed a check** | «Exported, but failed a check: …» |
| ход сборки: считаю планы | **Laying out shots** | шаги хода — с большой буквы, в строке «Exporting · …» |
| раскладываю субтитры | **Laying out subtitles** | |
| рисую субтитры (по состояниям) | **Drawing subtitles** | единица — *images* |
| склеиваю слой субтитров | **Preparing subtitles** | единица — *frames* |
| собираю плашку | **Making the end card** | |
| кодирую | **Encoding** | единица — `s`: «12 of 31 s» |
| сверяю кадры / плашку / субтитры | **Checking picture and cuts / Checking end card / Checking subtitles** | картинка и стыки сверяются одним проходом; единица — *frames* (точка сверки — это кадр) |
| играть / пауза | **Play / Pause** | плеер чернового просмотра |
| в начало | **Rewind** | |
| без звука / со звуком | **Mute / Unmute** | |
| кроп / полный кадр (режим плана) | **Crop / Full frame** | |
| полный кадр с размытыми полями | **full frame, blurred sides** | |
| рамка по лицу / рукой / по центру | **crop follows the face / crop set by hand / no face found — centered** | |
| огрызок (план, от которого попал хвост) | **partial shot** | |
| переключатель «кадр / просмотр» | **Frame / Preview** | готовый файл в окне называется *the exported file* |
| отметка файла: файл поменяли, пока правили | **changed while you were editing** | |

## Редактор субтитров, профиль и виды

Ключи и слова-значения `subtitles.yaml` и `looks.yaml` — английские,
строчные, через подчёркивание, теми же словами, что на экране.
Таблица «старое имя → новое» одна: `private/tools/rename-style-keys.py`.

| русское | на экране | в профиле |
|---|---|---|
| шрифт / вес шрифта | **font / weight** | `font`, `weight` |
| свой шрифт, свой фон (в списке) | **yours** | «Oswald.ttf — yours» |
| вес не выставился | **this font has no weight setting** | |
| регистр: как есть / прописные / капитель | **case: As typed / ALL CAPS / Small Caps** | `case: as_typed / all_caps / small_caps` |
| кегль | **size** | `size` |
| межстрочное расстояние | **line spacing** | `lines.spacing` |
| подложка: плашка / обводка / тень / без | **background: Box / Outline / Shadow / None** | `background: box / outline / shadow / none` |
| толщина обводки | **outline width** («9 % of size») | `outline.width` |
| краска сказанного / ещё не сказанного | **spoken color / upcoming** | `text_color.spoken / upcoming` |
| подсветка: ничего / слово / строка | **Karaoke: None / Word / Line** | `karaoke.mode: none / word / line` |
| чем подсвечивать: цветом / плашкой / кеглем | **by: Color / Box / Size** | `karaoke.by: color / box / size` |
| место в кадре; быстрые места верх / середина / низ | **Position; quick positions Top / Middle / Bottom** | `position.from_bottom` |
| беречь зоны (галочка) | **Stay inside safe zones** | `safe_zones.enabled: true/false` |
| поля по бокам | **side margins** | `safe_zones.side` |
| плашка в конце: показывать | **show an end card over the last seconds** | `end_card.show: true/false` |
| фон плашки / без фона | **background image / none — solid color** | `end_card.image` (имя файла или `none`) |
| надпись плашки: своя / базовая | **end card text — this clip's own / the default** | `end_card.text.content` |
| сделать надпись базовой | **Make default** | |
| сохранить надпись этой вертикалке | **Save for this clip** | |
| полоса под субтитр на плашке | **subtitle area** | |
| показать плашку / вернуться к кадру | **Show the end card / Back to the video** | |
| субтитры в файле ролика: есть / нет | **show subtitles in the clip**; выключены — метка **off**, в строке сборки **without subtitles** | в команде — `vertcut subs … --on\|--off` |
| причина устаревания: субтитры выключили / включили | **subtitles turned off / subtitles turned on** | |
| галочка «новые видео — без субтитров» | карточка **Subtitles in new videos**, галочка **export new videos without subtitles** | действует на видео, разобранные после неё |
| заменить… (обложку) | **Replace…** | |
| свой файл шрифта / фона | **Add font file… / Add image…** | |
| готовые виды | **Presets** | `looks.yaml`: `name`, `about`, `cost`, `settings` |
| виды: обычный / крупный / на обводке / узкий | **Standard / Large / Outline / Narrow** | `standard / large / outline / narrow` |
| цена вида (фраза не влезает в одну страницу) | **8–23% of phrases need two pages** | `cost: {essay, interview, english}` |
| фраза в несколько страниц (у фразы) | **2 pages**; у выбранной — **Shown on 2 pages, one after another** | не *doesn't fit*: жёлтое «не влезает» читали как «обрежется» |
| сколько фраз перелистывается (у вертикалки) | **5 of 21 phrases take more than one page … No words are lost** | серым, не жалобой |
| правлено рукой (текст фразы) | **edited** | |
| строк · знаков (счётчик у фразы) | **2 lines · 14 and 16 characters** | |
| список фраз ролика в редакторе | **Phrases** | не *lines*: в списке фразы, а строки — внутри |
| снять правки текста и швов | **Reset text edits**; в вопросе — «splits and merges» | слова «шов» на экране нет |
| вычитать субтитры моделью | **Check with AI / Check again**; идёт — *Checking…* | в команде — `vertcut proofread` (`check` уже занят окружением) |
| правка модели (у фразы) | **AI fix**; счёт — *6 AI fixes* | не *suggestion*: suggestions — кандидаты во фрагменты |
| принять / поправить / отклонить правку модели | **Accept / Edit / Dismiss**; все — **Accept all (6) / Dismiss all** | в команде — `--accept N\|all`, `--dismiss N\|all` |
| модель ничего не нашла | **AI found nothing to fix** | |
| дорогая проверка (сбоку от кнопки) | **≈ $0.12 · over limit** | цена пишется только дорогая |
| сделать этот стиль моим | **Save as my style** | |
| взять мой стиль | **My style** (вид), **Use my style** (кнопка) | |
| вернуть поставляемый | **Reset to default style** | |
| вернуть стиль видео (снять свой у вертикалки) | **Use this video's style** | |
| чей стиль стоит сейчас | **now: the default style / my style / this clip's own style / this video's style, changed** | |
| стиль видео / вертикалки в заголовке | **this video's style — shared by all its clips / this clip's style — only this clip uses it** | |
| починить стиль (отказ «не читается») | **Fix the style** | кнопка под отказом и карточка в редакторе |
| профиль старого образца | **saved by an older version of Vertcut** | файл без `version` |

## Описания, настройки, помощь

| русское | на экране | пояснение |
|---|---|---|
| автор (в инструкции модели) | **creator** | на экране человек — *you* |
| площадка (YouTube, TikTok…) | **platform** | «the platform's form» |
| метка у описания: моделью / ваше / правится | **AI / yours / editing** | |
| скопировать / скопировано | **Copy / Copied** | |
| написать самому | **Write it yourself** | |
| попросить AI (у одной вертикалки) | **Ask AI** | |
| переписать через AI | **Rewrite with AI** | |
| написать тем, у кого нет | **Write missing descriptions** | |
| переписать все | **Rewrite all** | |
| описания нет | **no description** | |
| описания начинаются одинаково | **these descriptions start the same way** | |
| знаков (счётчик) | **characters** | |
| запрос (к модели) | **request** | |
| ответ модели | **AI answer** | |
| проверить ключ | **Test** | |
| ключ записан / ключа нет | **key saved / no API key** | не *connected*: принят ли ключ, говорит только **Test** |
| отвечал (дата проверки) | **last answered Sep 2** | |
| вписать имя руками / выбрать из списка / спросить список | **type the name / choose from the list / get the list from the provider** | |
| цена за миллион токенов на вход / выход | **per million input / output tokens** | |
| дневник расходов | **spending history** | не *log*: log — это `logs/` |
| инструкция: своя / базовая | **yours / default** | |
| вернуть базовую инструкцию | **Reset to default prompt** | |
| раздел «Субтитры по умолчанию» | **My style and fonts** | не *default*: default style — поставляемый |
| раздел «Папка и место на диске» | **Folders and disk space** | |
| раздел «Клавиши» | **Keyboard shortcuts** | |
| мой стиль есть / ещё нет | **saved / not saved yet** | |
| убрать мой стиль | **Remove my style** | |
| добавить свой шрифт | **Add font file…** | одна кнопка в настройках и в редакторе |
| где что лежит | **Where things are** | |
| машина (компьютер человека) | **computer** | |
| иконка, вкладка | **icon, tab** | |
| что сейчас на этой машине | **On this computer right now** | экран помощи |
| последний запуск | **Last launch** | экран помощи, хвост журнала |
| подписи листа стиля: было / стало / сейчас | **before / after / now** | `vertcut style --sheet` |

## Команда `vertcut`, адреса экранов, имена на диске

Ключ команды — то же слово словаря, через дефис: одно слово — одно
имя ключа на все подкоманды («заново» везде `--again`, «лист» везде
`--sheet`). Таблица ключей — `vertcut <команда> --help` и CLAUDE.md;
что подсказки называют только настоящие ключи, сторожит проверка.

| русское | на экране / в команде | пояснение |
|---|---|---|
| лист (контактный лист, лист раскладки, лист стиля) | **sheet** | `--sheet`; файл `subtitles-sheet.jpg`, `style-sheet.jpg` |
| название ролика | **title** | `vertcut title … --title` |
| заново | **again** | `--again` у `ingest`, `pick`, `render`, `queue`, `suggest`, `proofread` |
| да (согласиться на дорогой запрос) | **yes** | `--yes` |
| ярлык (кто поднял сервис по иконке) | **icon** | `screen --exit-with-icon` |
| кроп / полный кадр в команде | **crop / full** | `frame --mode crop\|full` |
| беречь зоны: да / нет в команде | **on / off** | `style --safe-zones on\|off` |
| место фразы: под планом / внизу | **middle / bottom** | в печати `vertcut subs` |
| край фразы (столбец) / слух (столбец) | **edge / heard** | `vertcut phrases` |
| пропуск в адресе | **pass** | `?pass=`, как заголовок `X-Vertcut-Pass` |

Экраны в адресе: `videos`, `analysis`, `segments`, `clip`, `subtitles`,
`descriptions`, `export`, `settings`, `help`. Разделы настроек: `ai`,
`my-style`, `folders`, `samples`, `shortcuts`.

Имена на диске — словами экрана: `Inbox`, `logs/launch-…log`,
`backgrounds/`, `spending.json`, `samples.txt`, `install/progress.html`,
`analysis-job.json`, `ai-job.json`, `suggestions.json`,
`suggestions.answer.txt`, `descriptions.answer.txt`, `proofread.json`,
`proofread.answer.txt`, `thumbnail.jpg`,
`cover.jpg` (кадр для списков — не *preview*: preview занят черновым
просмотром), `end-card.png`, `analysis.log`, `export.log`; у программы
`python/` и `version.json`. Полная таблица «старое → новое» —
`private/tools/rename-disk-names.py`.

## Установка, ярлык, раздача

Названия кнопок и разделов системы — так, как их видит человек
с английской системой, слово в слово; в кавычках не пишутся, выделяются
жирным.

| русское | на экране | пояснение |
|---|---|---|
| установка, ставится | **install, installing** | заголовок страницы хода — *Installing Vertcut* |
| установщик | **installer** | «The installer stopped and installed nothing» |
| установка не доделалась | **Installation didn't finish** | заголовок страницы хода при отказе |
| Vertcut не поставился (оболочка, до питона) | **Vertcut didn't install** | |
| Vertcut не запустился (ярлык, после установки) | **Vertcut didn't start** | |
| это делается один раз | **This happens only once.** | |
| Готово (в конце установки) | **Done** | |
| переносимый питон | **Python** | человеку — просто *Python* |
| библиотеки | **libraries** | |
| модель распознавания | **speech recognition model** | |
| добыть ffmpeg | **Getting ffmpeg** | уже стоит — *already installed* |
| пропал интернет / сеть вернётся | **the internet connection dropped / when you're back online** | |
| сумма не сошлась | **isn't the file we expected** | слова *checksum* человек не видит; в подробностях — *expected / got* |
| подмена | **tampered with** | |
| ничего не сломано | **Nothing is broken** | после любого отказа установки |
| запустить ещё раз | **open Vertcut again** | не *run the installer*: установщика человек не видит |
| значок на Рабочем столе | **the Vertcut icon on your Desktop** | *Desktop* — с большой буквы, как в системе |
| Загрузки | **Downloads** | |
| распакованная папка | **the unzipped folder** | |
| файл поставки (`.whl`) | **Vertcut package** | только в журнале |
| запасная дорога на macOS | **If-Vertcut-does-not-open.sh** | имя файла в раздаче; в README и в его примечаниях — *the backup way*; файл английский целиком, с примечаниями |
| опись лицензий (`LICENSES.md`) | **What Vertcut is made of, and under which licenses** | заголовок файла в папке `Licenses/`; *copyleft* — «заразная», *weak copyleft* — «слабо заразная» |
| раздавать (ffmpeg) | **hand out** | «we do NOT hand it out» |
| метка «скачано из интернета» | **the "downloaded from the internet" mark** | |
| Терминал | **Terminal** | открывается **⌘ Space** → *Terminal* → **Return**: Launchpad в macOS 26 нет |
| macOS: Системные настройки → Конфиденциальность и безопасность → Всё равно открыть | **System Settings → Privacy & Security → Open Anyway** | macOS 12 и старше: **System Preferences → Security & Privacy → General → Open Anyway** |
| macOS: окно отказа | **"Vertcut" Not Opened**, кнопки **Done / Move to Trash** | macOS 15 и новее |
| Windows: окно SmartScreen | **Windows protected your PC**, **More info → Run anyway** | |
| Windows: Извлечь все | **Extract All** | |
| Windows: снять блокировку архива | **Properties → Unblock** | |
| Защитник | **Microsoft Defender** | |
| Windows: Журнал защиты | **Windows Security → Virus & threat protection → Protection history** | |
| выйти из сервиса (кнопка) | **Quit Vertcut** | последней строкой подвала колонки; на первом входе — в верхней полосе. Вопрос — **Quit Vertcut?**, кнопки **Quit / Cancel**; после — **Vertcut has stopped.** |
| погасить экран из терминала | **vertcut stop** | |
| идёт дальше сам (после выхода) | **keeps going on its own / Still running on its own** | разбор и сборка; *open Vertcut again to see how it’s doing* |
| ИИ-помощник, который ставит сервис | **AI agent** | README, INSTALL.md: *Ask your AI agent to install it* |
| три пути установки | **ways**: *1. Ask your AI agent… 2. Install it yourself in a terminal 3. Download the installer* | путь — *way*, не *method/option* |
| готовые архивы на GitHub | **the Releases page** | |
| папка с кодом при установке из исходников | **`~/vertcut-app`** | не `~/vertcut`: там работа человека |
| окружение `.venv` | **Python environment (.venv)** | в окне значка из исходников |
| значок из исходников (`build-dev-launcher.py --plain`) | **Vertcut** | для правки — **Vertcut (dev)** |
| не проверено (на системе) | **not tested** | *tested* — только то, что гонялось |

## Числа, время, единицы

| что | как пишется | пример |
|---|---|---|
| длина меньше минуты | десятые через точку, `s` | `42.5 s` |
| длина от минуты | `min` и `s` | `3 min 05 s` |
| длина видео крупно | только минуты | `19 min` |
| время внутри видео | минуты:секунды.десятые | `1:19.5` |
| размер | `MB`, `GB`, десятые через точку | `3.4 GB` |
| дата | день, месяц тремя буквами, время | `Sep 2, 17:40` |
| счёт | две формы: одна и много | `1 clip`, `0 clips`, `5 clips` |
| деньги | доллары, два знака | `$0.42` |
| деньги мельче цента / ноль / неизвестно | словами | `less than a cent`, `free`, `price unknown` |
| частота кадров | `fps` | `25 fps` |
| «столько-то из стольких» | `of` | `3 of 5 usable`, `120 of 300 seconds of audio` |

Даты, числа и деньги пишутся своими функциями (`words.js`: `длина`,
`минут`, `гигабайт`, `когда`, `счёт`, `деньги`; `report.py`: `счёт`),
а не системными: системные на разных машинах отдают разное.
