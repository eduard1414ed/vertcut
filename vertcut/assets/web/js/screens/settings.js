// Экран 10 · Настройки. Блок ключа — первый, как в дизайне.
//
// Дизайн рисует шесть разделов. Здесь пять, и шестой не нарисован
// не потому, что не успели: **«Формат и качество»** — такой настройки
// в сервисе нет вовсе. Кадр вертикалки 1080×1920 это геометрия
// площадки, а не вкус, а кодек и битрейт замерены. Поле, которое
// ни на что не влияет, обещает управление, которого нет.
//
// **Ключ — не галочка в конце списка, а первый блок с ясным
// договором:** где лежит, куда уходит, кто платит, сколько ушло.
// Это правило дизайна, и оно же правило спеки: не прятать цену.
//
// **Списка моделей нет.** Адрес, протокол и имя модели — обычные поля
// с разумным значением по умолчанию, поэтому новая модель работает
// в тот день, когда её выпустили, а не когда мы обновим сервис.
//
// Одно расхождение с дизайном названо вслух прямо на экране: он пишет
// «где лежит — в этом браузере», а здесь показан путь к файлу. Ключ
// в браузере не виден команде в терминале, пропадает от чистки
// браузера и заводится заново в каждом браузере на машине.

import {
  нарисовать, лого, блок, эл, моно, метка, растяжка, галка, стрелка,
  сказать, сказать_беду, убрать_полосы,
} from '../shell.js';
import * as связь from '../api.js';
import * as слова from '../words.js';
import * as адрес from '../route.js';

const РАЗДЕЛЫ = [
  ['ai', 'AI and API key'],
  ['my-style', 'My style and fonts'],
  ['folders', 'Folders and disk space'],
  ['samples', 'Your samples'],
  ['shortcuts', 'Keyboard shortcuts'],
];

let это = null;
let ai = null;
let раздел = 'ai';
// Список моделей от поставщика. Спрашивается по кнопке, а не сам:
// это обращение к сети, а сервис обязан работать и без неё.
let список_моделей = null;
let свои_имена = false;
// Раскрыт ли список моделей. Экран перерисовывается целиком после
// каждой правки — раскрытое иначе схлопывалось бы само.
let список_раскрыт = false;
// Само поле ключа. Помнится ради одного случая: человек вставил ключ
// и сразу нажал «Проверить». Поле записывается, когда из него уходят,
// а «уходят» и «нажали» случаются почти одновременно — и проверка
// успела бы уйти со СТАРЫМ ключом. Проверка дописывает его сама.
let поле_ключа = null;
// Раскрыт ли договор. Экран перерисовывается целиком после каждой
// правки, и `<details>` каждый раз рождался бы закрытым: человек
// раскрыл, поправил число — и объяснение схлопнулось само. Помнить
// это негде, кроме как здесь: оно про эту вкладку и про эту минуту.
let договор_раскрыт = false;

export async function показать([какой]) {
  if (какой && РАЗДЕЛЫ.some(([имя]) => имя === какой)) раздел = какой;
  это = await связь.взять('настройки');
  ai = await связь.взять('ai');
  await взять_список();
  рисовать();
}

// Список моделей берётся СРАЗУ, а не по кнопке: базово поле «Модель»
// и есть список, а набор имени руками — дорога для тех, кому список
// не подошёл.
//
// **Молча, и молча же не получается.** Это единственное обращение
// к сети, которое сервис делает сам, без нажатия: оно бесплатное
// (список моделей денег не стоит) и без него поле не станет списком.
// Не ответил поставщик — остаётся поле для имени, и внизу стоит
// ссылка «спросить список у поставщика»: тогда отказ будет показан
// словами, потому что человек его попросил.
async function взять_список() {
  if (!ai.подключён || список_моделей) return;
  try {
    список_моделей = await связь.взять('ai-модели');
  } catch (_) {
    список_моделей = null;
  }
}

// Разделы стоят в КОЛОНКЕ СЕРВИСА, а не в своей второй колонке.
//
// Расхождение с макетом, и оно названо вслух. Макет рисует экран 10
// отдельно стоящим: у него сверху своя полоса «← назад · Настройки»,
// а слева своя навигация на 236 пикселей. В живом сервисе колонка
// слева есть ВСЕГДА, и настройки получали два меню разом — пустую
// колонку сервиса и свою рядом с ней. Автор увидел это первым же
// взглядом.
//
// Правило проекта тут прямое: колонка — это то, чем человек ходит
// по сервису. В четвёртой сессии из неё уже выселяли отчёт, вернувший
// на её место навигацию; второе меню — та же беда с другой стороны.
function рисовать() {
  нарисовать({
    колонка: [
      лого(),
      блок('settings', РАЗДЕЛЫ.map(([имя, зовут]) => эл('button', {
        класс: 'в-раздел', текст: зовут,
        'aria-current': имя === раздел ? 'true' : 'false',
        на: { click: () => { раздел = имя; рисовать(); } },
      }))),
      растяжка(),
      эл('button', {
        класс: 'vc-link vc-link--muted', текст: '← all videos',
        на: { click: () => { адрес.идти('videos'); } },
      }),
    ],
    заголовок: эл('h1', { класс: 'vc-h1' }, ['Settings']),
    лид: 'Everything stays on this computer: no account, no cloud. ' +
         'The API key too — and only three buttons need it.',
    мета: [моно(РАЗДЕЛЫ.find(([имя]) => имя === раздел)[1])],
    тело: содержимое(),
  });
}

function содержимое() {
  if (раздел === 'folders') return папка();
  if (раздел === 'shortcuts') return клавиши();
  if (раздел === 'my-style') return субтитры();
  if (раздел === 'samples') return эталоны();
  return ключ();
}

// ── My style and fonts ────────────────────────────────────────────────

// Своей карточкой, а не строкой «моего стиля»: это не про то, как
// выглядят субтитры, и «Save as my style» её не трогает. Действует
// на видео, разобранные после неё (`ingest.принять`).
function субтитры_новых() {
  const галочка = эл('input', { type: 'checkbox',
                                checked: это.новые_без_субтитров });
  галочка.addEventListener('change', async () => {
    убрать_полосы();
    try {
      это = await связь.послать('новые-без-субтитров',
                                { вкл: галочка.checked });
    } catch (беда) { сказать_беду(беда); }
    рисовать();
  });
  return эл('div', { класс: 'vc-card' }, [
    эл('div', { класс: 'в-ряд' }, [
      эл('b', { класс: 'vc-card__title', текст: 'Subtitles in new videos' }),
    ]),
    эл('label', { класс: 'в-выключатель' }, [
      галочка, эл('span', { текст: 'export new videos without subtitles' }),
    ]),
    эл('p', {
      класс: 'в-подпись', стиль: { margin: '0' },
      текст: 'Clips of videos you analyze from now on export without ' +
             'subtitles. You can still turn subtitles on for any clip. ' +
             'Videos you have already analyzed don\'t change.',
    }),
  ]);
}

function субтитры() {
  const л = это.личный_стиль;
  return [
    эл('div', { класс: 'vc-card' }, [
      эл('div', { класс: 'в-ряд' }, [
        эл('b', { класс: 'vc-card__title', текст: 'My style' }),
        растяжка(),
        // Старый образец — своей меткой: «saved» про файл, который
        // эта версия не читает, было бы неправдой наполовину.
        л.беда ? метка('older version', 'warn')
          : л.есть ? метка('saved', 'good') : метка('not saved yet', 'off'),
      ]),
      эл('p', {
        класс: 'в-подпись', стиль: { margin: '0' },
        текст: 'Subtitle style comes in four layers: the default style, ' +
               'my style, this video\'s style and — if you made one — ' +
               'a clip\'s own style. Every video gets its own copy when ' +
               'it\'s analyzed, so changing my style never makes clips of ' +
               'videos you already analyzed out of date.',
      }),
      моно(л.путь, 'в-подпись'),
      старый_личный(л),
      л.есть
        ? эл('div', { класс: 'в-ряд' }, [
            эл('button', {
              класс: 'vc-btn vc-btn--sm', текст: 'Remove my style',
              на: { click: убрать_личный },
            }),
            эл('span', {
              класс: 'в-подпись',
              текст: 'new videos will start with the default style; ' +
                     'videos you already analyzed won\'t change',
            }),
          ])
        : эл('p', {
            класс: 'в-подпись', стиль: { margin: '0' },
            текст: 'It appears when you click Save as my style in the ' +
                   'subtitle editor of any clip.',
          }),
    ]),
    л.числа ? числа_стиля(л.числа) : null,
    субтитры_новых(),
    эл('div', { класс: 'vc-card' }, [
      эл('div', { класс: 'в-ряд' }, [
        эл('b', { класс: 'vc-card__title', текст: 'Fonts' }),
        растяжка(),
        // Кнопка здесь, а не только в редакторе субтитров. В редакторе
        // она значит «этой вертикалке — вот такой шрифт», и без
        // открытой вертикалки её нет вовсе; а человек, который просто
        // хочет добавить свой шрифт, приходит сюда, где шрифты
        // перечислены. Ставит она в тот же набор и той же работой.
        это.диалог_умеем ? эл('button', {
          класс: 'vc-btn vc-btn--sm', текст: 'Add font file…',
          на: { click: добавить_шрифт },
        }) : null,
      ]),
      эл('p', {
        класс: 'в-подпись', стиль: { margin: '0' },
        текст: `${слова.счёт(это.шрифты.length, 'font comes', 'fonts come')} ` +
               'with Vertcut, each with its license file next to it. Your ' +
               'own font is copied into Vertcut\'s settings folder: a path ' +
               'to your desktop may lead nowhere a month later, and the ' +
               'clip would export without letters. .ttf, .otf and .ttc work.',
      }),
      // Диалога на этой машине нет — говорим, куда положить файл
      // руками. Мёртвой кнопки вместо этого не рисуется.
      это.диалог_умеем ? null : эл('p', {
        класс: 'в-подпись', стиль: { margin: '0' },
        текст: 'Vertcut can\'t open a file picker on this computer — put ' +
               'the font file into the “fonts” folder inside the settings ' +
               'folder yourself. The settings path is under Folders and ' +
               'disk space.',
      }),
      // Не «в-числа»: там правая колонка моноширинная и прижата
      // вправо — это для чисел. Здесь справа фраза, и прижимать её
      // некуда, а моноширинной она читается как код.
      эл('div', { класс: 'в-список-пар' }, [
        ...это.шрифты.map((ш) => пара(ш.файл, ш.какой)),
        ...это.свои_шрифты.map((имя) => пара(имя, 'yours')),
      ]),
    ]),
  ];
}

// Личный стиль, сохранённый старой версией (до английских ключей).
//
// **Двадцатая сессия оставила его немым:** экран не падал, но и
// не говорил, что файл не читается, — метка «есть» стояла над файлом,
// которым сервис пользоваться не может. Отказ приезжает полем
// `беда` и говорит, чей файл; что с ним делать — здесь, рядом
// с кнопкой, которая это делает.
function старый_личный(л) {
  if (!л.беда) return null;
  return эл('div', { класс: 'vc-bar vc-bar--warn' }, [
    эл('div', { класс: 'vc-bar__what' }, [
      эл('b', { текст: 'My style was saved by an older version of ' +
                       'Vertcut, and this version can\'t read it.' }),
      эл('span', { текст: 'New videos start with the default style ' +
                          'until you fix it. Open any clip\'s ' +
                          'subtitles, set the style up and click Save as ' +
                          'my style — that replaces the old file. Or ' +
                          'remove it below.' }),
    ]),
  ]);
}

function числа_стиля(числа) {
  return эл('div', { класс: 'vc-card' }, [
    эл('b', { класс: 'vc-card__title', текст: 'What my style sets' }),
    эл('div', { класс: 'в-числа' }, Object.entries(числа).map(([ключ, з]) =>
      эл('div', {}, [эл('span', { текст: ключ }),
                     эл('b', { текст: String(з) })]))),
  ]);
}

async function убрать_личный() {
  убрать_полосы();
  сказать({
    вид: 'ask',
    что: 'Remove my style?',
    делать: 'Videos you already analyzed keep their own copy of the ' +
            'style. New videos will start with the default style.',
    действия: [
      эл('button', {
        класс: 'vc-btn vc-btn--sm vc-btn--danger', текст: 'Remove',
        на: { click: async () => {
          убрать_полосы();
          try {
            это = await связь.послать('убрать-личный-стиль');
            рисовать();
          } catch (беда) { сказать_беду(беда); }
        } },
      }),
      эл('button', {
        класс: 'vc-btn vc-btn--sm', текст: 'Cancel', на: { click: убрать_полосы },
      }),
    ],
  });
}

// ── Folders and disk space ────────────────────────────────────────────

function папка() {
  return [
    эл('div', { класс: 'в-факты' }, [
      факт('used by analyses', слова.гигабайт(это.занято)),
      факт('free on disk', слова.гигабайт(это.свободно)),
      факт(слова.форма(это.разборы.length, 'analyzed video', 'analyzed videos'),
           String(это.разборы.length)),
      факт('in Inbox', String(это.входящих.length)),
    ]),
    эл('div', { класс: 'vc-card' }, [
      эл('b', { класс: 'vc-card__title', текст: 'Where things are' }),
      // Сеткой, а не рядом. Ряд ставит путь сразу за подписью,
      // а подписи разной длины — и три пути начинались в трёх
      // разных местах. Читают тут именно пути, и глазу не за что
      // зацепиться, когда их левый край пляшет.
      эл('div', { класс: 'в-пути' },
         [['analyses', это.корень, 'корень'],  // какую папку — для сервера, не для человека
          ['Inbox', это.входящие, 'входящие'],  // для сервера, не для человека
          ['settings and my fonts', это.настройки, 'настройки']]  // для сервера, не для человека
        .map(([зовут, путь, какую]) => эл('div', { класс: 'в-пути__ряд' }, [
          эл('span', { класс: 'в-подпись', текст: зовут }),
          моно(путь, 'в-подпись'),
          эл('button', {
            класс: 'vc-btn vc-btn--xs', текст: 'Show in folder',
            на: { click: () => открыть(какую) },
          }),
        ]))),
      эл('p', {
        класс: 'в-подпись', стиль: { margin: '0' },
        текст: 'Settings live NEXT TO the analyses, not inside them: ' +
               'you may clean up analyses by hand, and you shouldn\'t lose ' +
               'your style and fonts when you do.',
      }),
    ]),
    эл('div', { класс: 'vc-card' }, [
      эл('b', { класс: 'vc-card__title', текст: 'What takes the space' }),
      // Было «папку разбора можно удалить, видео не пропадёт» — правда
      // про исходник, но молчание про вертикалки, которые лежат в той
      // же папке. Теперь — дорога, которая спросит и скажет, что уйдёт.
      эл('p', {
        класс: 'в-подпись', стиль: { margin: '0' },
        текст: 'Each analysis keeps an audio track, a smaller copy of the ' +
               'video and a frame for every shot. To free space, delete ' +
               'a video in the list of videos — it says what goes with it ' +
               'before anything is deleted.',
      }),
      эл('div', { класс: 'в-числа' }, это.разборы.map((р) => эл('div', {}, [
        эл('span', { текст: р.журнал ? р.источник : р.слаг }),
        эл('b', { текст: слова.гигабайт(р.занято) }),
      ]))),
    ]),
  ];
}

// Плитка факта: крупное число сверху, чему оно — снизу.
//
// Третья строка необязательная и заведена блоком ключа: там факт
// сам по себе ничего не значит («куда уходит — только на этот адрес»
// без самого адреса это обещание, а не факт).
function факт(зовут, значение, подпись) {
  return эл('div', {}, [
    эл('b', { текст: значение }),
    эл('span', { текст: зовут }),
    подпись ? эл('span', { класс: 'в-подпись', текст: подпись }) : null,
  ]);
}

// Свой шрифт. Системный диалог открывает САМ СЕРВИС — браузер пути
// к файлу не отдаёт, только содержимое, и копия шрифта через окно
// браузера была бы вторым способом делать то же самое.
async function добавить_шрифт() {
  убрать_полосы();
  try {
    const ответ = await связь.послать('поставить-шрифт', {});
    // Отмена — не отказ: человек нажал «Отмена» ровно потому, что
    // передумал, и красная полоса тут ругала бы его за это.
    if (ответ.передумал) return;
    это = ответ;
    рисовать();
    сказать({ вид: 'good', что: `Font added: ${ответ.поставлен}`,
              делать: 'It\'s in the list now — pick it in the subtitle ' +
                      'editor of any clip.' });
  } catch (беда) { сказать_беду(беда); }
}

async function открыть(какую) {
  убрать_полосы();
  try {
    await связь.послать('показать-папку', { какую });
  } catch (беда) { сказать_беду(беда); }
}

// ── Клавиши ───────────────────────────────────────────────────────────

function клавиши() {
  const все = [
    ['Shift', 'hold on the first click on a phrase — add it as a second ' +
     'part of the clip', 'Segments'],
    ['←  →', 'move between the clip\'s shots', 'Clip'],
    // Пробел делает две работы сразу, и обе названы: на кадре он
    // ПЕРЕКЛЮЧАЕТ на просмотр и играет, на просмотре — играет
    // и останавливает. Своим пробелом плеер слушается только
    // с фокусом на себе, поэтому его ловит сам экран.
    ['Space', 'play and pause; on Frame — switch to Preview', 'Clip'],
    ['Mouse', 'drag the crop on the large shot frame', 'Clip'],
    ['Mouse', 'drag the subtitle right on the frame', 'Subtitles'],
  ];
  return [
    эл('div', { класс: 'vc-card' }, [
      эл('b', { класс: 'vc-card__title', текст: 'Keyboard and mouse' }),
      эл('div', { класс: 'в-клавиши' }, все.map(([клавиша, что, где]) =>
        эл('div', {}, [
          эл('span', { класс: 'в-клавиша', текст: клавиша }),
          эл('span', { текст: что }),
          растяжка(),
          моно(где, 'в-подпись'),
        ]))),
    ]),
  ];
}

// ── AI и ключ ─────────────────────────────────────────────────────────
//
// Блок первый и с ясным договором. Порядок частей взят из дизайна:
// ключ и адрес, ряд фактов, инструкция для фрагментов, расходы.

function ключ() {
  return [
    эл('div', { класс: 'vc-card' }, [
      эл('p', {
        класс: 'vc-lede', стиль: { margin: '0' },
        текст: 'It\'s needed for exactly three things: AI suggestions for ' +
               'segments, AI descriptions and checking subtitles with AI. ' +
               'Everything else — ' +
               'transcribing, shots, crop, subtitles, export — works ' +
               'without it and without internet.',
      }),
      договор(),
    ]),
    поля_ключа(),
    инструкция('фрагменты', 'Prompt for segments',  // какая — для сервера, не для человека
               'AI gets this prompt, the whole transcript and the ' +
               'shortest allowed length. It answers with segments as ' +
               'phrase numbers — Vertcut sets the answer format itself, ' +
               'so you don\'t need to describe it here.'),
    инструкция('описания', 'Prompt for descriptions',  // какая — для сервера, не для человека
               'Vertcut adds your samples to it, if you have any — they ' +
               'matter more than the prompt.'),
    инструкция('вычитка', 'Prompt for checking subtitles',  // какая — для сервера, не для человека
               'AI gets this prompt, the clip\'s subtitle lines, a few ' +
               'phrases around the clip and how the video begins. It ' +
               'answers with fixes; nothing changes until you accept one.'),
    расходы(),
  ];
}

// Свёрнутый блок с договором — правило спеки, и порядок первых двух
// строк назван спекой дословно: сперва «это не подписка Claude»,
// следом «без ключа сервис работает». Люди вводят пароль от claude.ai
// и злятся; сказать об этом надо ДО того, как они попробуют.
//
// **Дальше идёт то, чего тут раньше не было: что делать.** Блок
// отвечал на вопрос «что это такое» и не отвечал на «как мне его
// завести», а человек, который слышит про API впервые, приходит
// сюда со вторым вопросом. Рассказ про то, где ключ лежит и куда
// уходит, остался на месте — он ниже, отдельной раскрывашкой,
// и читают его один раз.
//
// **Шаги набраны той же раскрывашкой, что и страница помощи.** Её
// `ul` уже описан в `screen.css` и заведён ровно под это — «у каждой
// беды по три-четыре шага»; второй такой же разошёлся бы с первым.
//
// **Протокол ставится ПЕРВЫМ, и в шагах это сказано.** Ключи лежат
// по одному на поставщика (`config.имя_ключа`), и вставленный при
// чужом переключателе ляжет под чужим именем — отказ придёт «ключ
// не принят», то есть укажет ровно не туда, где беда. Та же ловушка,
// из-за которой полей ключа в файле два, а не одно.
function договор() {
  return эл('details', { класс: 'в-раскрывашка' }, [
    эл('summary', { текст: 'What an API key is and how to get one' }),
    эл('div', { класс: 'в-поля-столбиком' }, [
      эл('p', {
        стиль: { margin: '0' },
        текст: 'This is NOT a Claude subscription. A claude.ai ' +
               'subscription and an API key are different things, paid ' +
               'for separately: your claude.ai password won\'t work here — ' +
               'you need a separate sign-up and money on that account.',
      }),
      эл('p', {
        стиль: { margin: '0' },
        текст: 'Vertcut works fully without a key. No step disappears ' +
               'or gets locked: you mark segments by phrases and write ' +
               'descriptions yourself.',
      }),
      эл('p', {
        стиль: { margin: '0' },
        текст: 'In short: AI models can answer not only a person in a ' +
               'chat window but also other programs. That entrance for ' +
               'programs is called an API, and the key is its password. ' +
               'The key tells the provider the request is yours, and they ' +
               'charge your account for it. You set this up once; it ' +
               'takes a few minutes.',
      }),
      эл('ul', {}, [
        эл('li', {}, [
          'Sign up with one of two providers — either is fine. It\'s ' +
          'a separate account for programs, not the one you use for ' +
          'chat: ',
          внешняя('https://console.anthropic.com', 'console.anthropic.com'),
          ' is Claude by Anthropic, ',
          внешняя('https://platform.openai.com', 'platform.openai.com'),
          ' is GPT by OpenAI.',
        ]),
        эл('li', {
          текст: 'Add money to the account. You pay in advance, like ' +
                 'a prepaid phone, and you decide how much: Vertcut needs ' +
                 'only a small amount.',
        }),
        эл('li', {
          текст: 'Create a key there. It\'s a long line starting with ' +
                 '“sk-”. You see it in full only once, so copy it right ' +
                 'away.',
        }),
        эл('li', {
          текст: 'Come back here and FIRST set API type to your ' +
                 'provider: Vertcut keeps one key per provider, and a key ' +
                 'pasted under the wrong one will be rejected. The API ' +
                 'address fills in by itself.',
        }),
        эл('li', {
          текст: 'Now paste the key into the field below and choose ' +
                 'a model from the list — the provider sends the list as ' +
                 'soon as the key is accepted. That\'s it.',
        }),
      ]),
      эл('p', {
        стиль: { margin: '0' },
        текст: 'There\'s no subscription and no monthly fee: you pay only ' +
               'for work done. Click Ask AI or Write missing descriptions ' +
               '— you pay for that one request; don\'t click — you pay ' +
               'nothing. What you\'ve spent is shown below under Spending, ' +
               'and that\'s where you set a daily limit.',
      }),
      эл('p', {
        стиль: { margin: '0' },
        текст: 'Any other address that speaks the OpenAI API type works ' +
               'too — a proxy, or a model running right on this computer. ' +
               'A local model needs no key at all: leave the key empty ' +
               'and enter its address.',
      }),
    ]),
  ]);
}

// Ссылка наружу — первая и пока единственная на экране.
//
// Своего класса ей не заведено: правило пакета `a { color: accent }`
// красит её само, и заводить поверх него своё имя значило бы завести
// расхождение с дизайном там, где его нет.
//
// `rel` — не украшение: без него открытая вкладка получает ссылку
// на нашу страницу через `window.opener`.
function внешняя(куда, текст) {
  return эл('a', {
    href: куда, target: '_blank', rel: 'noopener noreferrer', текст,
  });
}

// Поля ключа. Все ростом 44 — как в макете: поле, кнопка
// и переключатель стоят в один ряд, и разнобой высот виден сразу.
//
// **Кнопки «Сохранить» нет, и это по макету.** Там её и не было:
// поле само есть настройка. Правка ложится на диск, когда человек
// уходит из поля, — то же правило «правится там же, где читается»,
// по которому устроены описания и строки субтитров.
function поля_ключа() {
  поле_ключа = эл('input', {
    класс: 'vc-input vc-input--mono', type: 'password',
    placeholder: ai.ключ_есть ? `key ${ai.хвост_ключа} — paste a new one`
                              : 'paste your API key',
  });
  const ключ_ = поле_ключа;
  сохранять(ключ_, () => ключ_.value.trim()
    ? { ключ: ключ_.value.trim() } : null);

  const адрес_ = эл('input', {
    класс: 'vc-input vc-input--mono', type: 'text',
    свойства: { value: ai.адрес },
  });
  сохранять(адрес_, () => адрес_.value.trim() === ai.адрес
    ? null : { адрес: адрес_.value.trim() });

  return эл('div', { класс: 'vc-card' }, [
    эл('div', { класс: 'в-ряд' }, [
      эл('b', { класс: 'vc-card__title', текст: 'API key and address' }),
      // «key saved», а не «connected»: метка знает только, что ключ
      // записан, а принят ли он — говорит кнопка Test.
      ai.подключён ? метка('key saved', 'good') : метка('no API key', 'off'),
      растяжка(),
      ai.проверено ? моно(`last answered ${слова.когда(ai.проверено)}`,
                          'в-подпись')
                   : null,
    ]),
    // Ряд ключа: поле во всю ширину, кнопки прижаты к нему справа.
    // Так в макете, и высота у всех одна — 44, как у поля.
    эл('div', { класс: 'в-поля' }, [
      поле('API key', ключ_),
      ai.подключён ? эл('button', {
        класс: 'vc-btn', текст: 'Test',
        на: { click: проверить },
      }) : null,
      ai.ключ_есть ? эл('button', {
        класс: 'vc-btn vc-btn--danger', текст: 'Remove',
        на: { click: () => настроить({ ключ: '' }) },
      }) : null,
    ]),
    эл('div', { класс: 'в-поля' }, [
      поле('API address', адрес_),
      поле('API type', протокол_переключатель()),
      поле('Model', выбор_модели()),
    ]),
    // Ссылка прижата вправо — то есть встаёт ровно под поле «Модель»:
    // оно последнее в ряду и тянется до правого края. Строкой по центру
    // она относилась бы ко всему ряду сразу, а относится к одному полю.
    эл('div', { класс: 'в-поля__ниже' }, [ссылка_на_список()]),
    эл('p', {
      класс: 'в-подпись', стиль: { margin: '0' },
      текст: ai.подключён
        ? 'The list comes from the provider itself — Vertcut doesn\'t ' +
          'keep one, because a built-in list would go stale. If your ' +
          'model isn\'t listed, or the provider sends no list, type the ' +
          'name exactly as in the provider\'s documentation.'
        : 'Vertcut gets the list of models from the provider once there ' +
          'is one — via a key or an address. Until then, type the name ' +
          'exactly as in your provider\'s documentation.',
    }),
    договор_ключа(),
  ]);
}

// Поле само себе кнопка «Сохранить»: ушли из него — записалось.
//
// Пишем ТОЛЬКО когда значение изменилось. Иначе каждый щелчок мимо
// поля слал бы просьбу и клал полосу «Записано» — и человек перестал
// бы её замечать ровно к тому моменту, когда она что-то значит.
function сохранять(поле_, что) {
  поле_.addEventListener('change', () => {
    const это_ = что();
    if (это_) настроить(это_);
  });
}

// Модель — списком от поставщика, а не полем для набора вслепую.
//
// Расхождение с дизайном, и оно в сторону человека: он рисует
// текстовое поле. Требование спеки — не вшивать СПИСОК — при этом
// соблюдено буквально: списка в сервисе нет, он приезжает
// от поставщика по его же адресу и потому не может устареть.
//
// Поле никуда не делось: посредник может списка не отдавать вовсе,
// и тогда имя вписывается руками, как в дизайне.
// Модель выбирается СПИСКОМ, и список этот свой, а не браузерный.
//
// Родной `<select>` на macOS открывается ПОВЕРХ поля и рисует свою
// стрелку системным шрифтом — ни то ни другое не настраивается.
// Автор увидел и то и другое сразу.
//
// Свой список открывается ВНИЗ и В ПОТОКЕ: он раздвигает карточку,
// а не наезжает на неё. Это ещё и правило пакета: всплывающих слоёв
// в этом дизайне нет вовсе — «тень допустима только под всплывающим
// слоем; в этом дизайне таких слоёв нет».
//
// Стрелка и галочка нарисованы линиями: этих знаков нет ни в одном
// из трёх шрифтов экрана.
function выбор_модели() {
  if (свои_имена || !список_моделей) return поле_модели();

  const свои = список_моделей.модели.some((м) => м.имя === ai.модель);
  const все = [...список_моделей.модели];
  if (!свои) все.unshift({ имя: ai.модель, зовут: 'typed by hand' });

  return эл('div', { класс: 'в-список' }, [
    эл('button', {
      класс: 'в-список__поле' + (список_раскрыт ? ' в-список__поле--открыт' : ''),
      'aria-expanded': список_раскрыт ? 'true' : 'false',
      на: { click: () => { список_раскрыт = !список_раскрыт; рисовать(); } },
    }, [
      эл('span', { класс: 'в-список__имя', текст: ai.модель }),
      растяжка(),
      стрелка(),
    ]),
    список_раскрыт
      ? эл('div', { класс: 'в-список__ряд' }, все.map(строка_модели))
      : null,
  ]);
}

function строка_модели(м) {
  const эта = м.имя === ai.модель;
  return эл('button', {
    класс: 'в-список__строка' + (эта ? ' в-список__строка--эта' : ''),
    на: { click: () => {
      список_раскрыт = false;
      if (эта) return рисовать();
      настроить({ модель: м.имя });
    } },
  }, [
    эта ? галка() : эл('span', { класс: 'в-список__пусто' }),
    эл('span', { класс: 'в-список__имя', текст: м.имя }),
    м.зовут ? эл('span', { класс: 'в-подпись', текст: м.зовут }) : null,
  ]);
}

function поле_модели() {
  const поле_ = эл('input', {
    класс: 'vc-input vc-input--mono', type: 'text',
    свойства: { value: ai.модель },
  });
  сохранять(поле_, () => поле_.value.trim() === ai.модель
    ? null : { модель: поле_.value.trim() });
  return поле_;
}

// Под полем — мелкая ссылка для тех, кому список не подходит.
// Дорога туда и обратно: у поставщика может не быть нужной модели
// в списке, а может не быть и самого списка.
function ссылка_на_список() {
  if (!ai.подключён) return null;
  if (список_моделей && !свои_имена) {
    return эл('button', {
      класс: 'vc-link vc-link--muted', текст: 'type the name',
      на: { click: () => { свои_имена = true; список_раскрыт = false;
                           рисовать(); } },
    });
  }
  if (список_моделей) {
    return эл('button', {
      класс: 'vc-link vc-link--muted', текст: 'choose from the list',
      на: { click: () => { свои_имена = false; рисовать(); } },
    });
  }
  // Списка нет вовсе: поставщик его не отдал. Это не поломка —
  // часть посредников такого адреса не держит.
  return эл('button', {
    класс: 'vc-link vc-link--muted', текст: 'get the list from the provider',
    на: { click: спросить_модели },
  });
}

async function спросить_модели() {
  убрать_полосы();
  try {
    список_моделей = await связь.взять('ai-модели');
    свои_имена = false;
    рисовать();
    if (список_моделей.ещё_есть) {
      сказать({ вид: 'ask',
                что: `Not all models are shown: the provider sent ` +
                     `${список_моделей.модели.length} and said there are more.`,
                делать: 'If yours isn\'t listed, type the name.' });
    }
  } catch (беда) { сказать_беду(беда); }
}

function поле(зовут, что) {
  return эл('label', { класс: 'vc-field' }, [
    эл('span', { класс: 'vc-field__label', текст: зовут }), что,
  ]);
}

function протокол_переключатель() {
  return эл('div', { класс: 'vc-seg' }, [
    ['anthropic', 'Anthropic'], ['openai', 'OpenAI'],
  ].map(([имя, зовут]) => эл('button', {
    текст: зовут,
    'aria-pressed': ai.протокол === имя ? 'true' : 'false',
    на: { click: () => настроить({ протокол: имя }) },
  })));
}

// Договор ключа: где лежит, куда уходит, кто платит.
//
// **Сложен, и это по слову автора.** Договор читают ОДИН РАЗ — когда
// решают, вставлять ли сюда ключ. Дальше он висит четырьмя плитками
// над каждой правкой числа и вытесняет то, ради чего на экран зашли.
//
// Живое число — сколько ушло за сегодня — из договора убрано вовсе
// и стоит в «Расходах», рядом с порогом и стопом. Там его место:
// это не договор, а счётчик, и смотрят на него не однажды, а всякий
// раз.
//
// **Подпись сверху, значение снизу** — как в макете, и это не вкус.
// Плитка с крупным числом наверху годится там, где число и есть суть
// («занято 3.4 ГБ»). Здесь наоборот: «в файле на этой машине»
// не значит ничего, пока не сказано, о чём это.
function договор_ключа() {
  const узел = эл('details', {
    класс: 'в-раскрывашка', open: договор_раскрыт,
  }, [
    эл('summary', { текст: 'More: where the key is kept, where it goes ' +
                           'and who pays' }),
    эл('div', { класс: 'в-договор' }, [
      факт_договора('kept', 'in a file on this computer', ai.где_лежит),
      факт_договора('sent', 'only to this address', ai.адрес),
      факт_договора('paid by', 'you, at your own rates',
                    ai.ключ_есть ? `key ${ai.хвост_ключа}` : 'no API key'),
    ]),
    эл('div', { класс: 'в-поля-столбиком' }, [
      эл('p', {
        стиль: { margin: '0' },
        текст: 'The key is kept in a plain file with your settings — not ' +
               'in the app folder and not in the browser: you may ' +
               'reinstall the app or clear the browser one day, and a key ' +
               'is something you set up once. Only your user account can ' +
               'read that file.',
      }),
      эл('p', {
        стиль: { margin: '0' },
        текст: 'It goes only to the address in the field above: there\'s ' +
               'one single place in Vertcut\'s code that goes online at ' +
               'all, and a test guards that. Everything else — ' +
               'transcribing, frames, subtitles, export — runs on your ' +
               'computer, without internet.',
      }),
      эл('p', {
        стиль: { margin: '0' },
        текст: 'The screen and reports show only the key\'s last four ' +
               'characters. The key never goes into the log or an ' +
               'analysis folder — those are what people send when they ' +
               'ask for help.',
      }),
      эл('p', {
        стиль: { margin: '0' },
        текст: 'You pay the provider directly, at your own rates. Vertcut ' +
               'has no account, no subscription and no middleman: it only ' +
               'counts what was spent — and takes that number from the ' +
               'provider\'s answer, not from a guess.',
      }),
    ]),
  ]);
  узел.addEventListener('toggle', () => { договор_раскрыт = узел.open; });
  return узел;
}

function факт_договора(зовут, значение, подпись) {
  return эл('div', {}, [
    эл('span', { класс: 'в-договор__что', текст: зовут }),
    эл('b', { текст: значение }),
    подпись ? эл('span', { класс: 'в-договор__ещё', текст: подпись }) : null,
  ]);
}

// Инструкция правится как текст, а не как поле формы. «Вернуть
// базовую» — это просто стереть свою: пустое поле и отсутствующий
// файл должны значить одно и то же.
function инструкция(какая, зовут, объяснение) {
  const это_ = ai.инструкции[какая];
  const поле_ = эл('textarea', {
    класс: 'vc-textarea vc-textarea--prompt', rows: '9',
    свойства: { value: это_.текст },
  });
  return эл('div', { класс: 'vc-card' }, [
    эл('div', { класс: 'в-ряд' }, [
      эл('b', { класс: 'vc-card__title', текст: зовут }),
      растяжка(),
      это_.своя ? метка('yours', 'good') : метка('default', 'off'),
    ]),
    эл('p', { класс: 'в-подпись', стиль: { margin: '0' },
              текст: объяснение }),
    поле_,
    эл('div', { класс: 'в-ряд' }, [
      эл('button', {
        класс: 'vc-btn vc-btn--sm', текст: 'Save',
        на: { click: () => положить_инструкцию(какая, поле_.value) },
      }),
      эл('span', { класс: 'в-подпись',
                   текст: 'applies from the next request' }),
      растяжка(),
      это_.своя ? эл('button', {
        класс: 'vc-link vc-link--muted', текст: 'Reset to default prompt',
        на: { click: () => положить_инструкцию(какая, '') },
      }) : null,
    ]),
  ]);
}

// Расходы. Порог и стоп — из дизайна, оба настройка.
//
// **Про суточный стоп сказана правда, которую легко было бы скрыть:**
// он считает деньги, а деньги считаются по цене модели. Модель
// не из прейскуранта — стоп не работает, и человек должен узнать это
// здесь, а не тогда, когда он не сработает.
function расходы() {
  const порог_ = эл('input', {
    класс: 'vc-input vc-input--mono', type: 'number', step: '0.05',
    min: '0', свойства: { value: String(ai.порог) },
  });
  const стоп_ = эл('input', {
    класс: 'vc-input vc-input--mono', type: 'number', step: '0.5',
    min: '0', свойства: { value: String(ai.стоп) },
  });
  const ц = ai.цена_модели;
  const п = ai.за_сегодня;
  return эл('div', { класс: 'vc-card' }, [
    эл('div', { класс: 'в-ряд' }, [
      эл('b', { класс: 'vc-card__title', текст: 'Spending' }),
      растяжка(),
      // Живое число стоит здесь, а не в договоре: договор читают
      // один раз, а на счётчик смотрят всякий раз.
      моно(`today $${п.деньги.toFixed(2)} · ` +
           слова.счёт(п.запросов, 'request', 'requests')),
    ]),
    эл('p', {
      класс: 'в-подпись', стиль: { margin: '0' },
      текст: ц
        ? `Vertcut takes the token counts from the provider's answer ` +
          `instead of counting them itself, and turns them into money at ` +
          `this model's price — $${ц[0]} and $${ц[1]} per million input / ` +
          `output tokens, checked ${ai.цены_сверены}. Your rates may differ.`
        : 'Vertcut doesn\'t know this model\'s price: it shows request ' +
          'size in tokens, not in money. A made-up price is worse than ' +
          'none — people click “≈$0.02” without thinking.',
    }),
    эл('div', { класс: 'в-поля' }, [
      поле('Ask above, $', порог_),
      поле('Daily limit, $', стоп_),
    ]),
    эл('div', { класс: 'в-ряд' }, [
      эл('button', {
        класс: 'vc-btn vc-btn--sm', текст: 'Save',
        на: { click: () => настроить({ порог: Number(порог_.value),
                                       стоп: Number(стоп_.value) }) },
      }),
      ai.цена_модели ? null : эл('span', {
        класс: 'в-подпись',
        текст: 'neither works with this model: treating an unknown price ' +
               'as zero would promise protection that isn\'t there',
      }),
    ]),
    ai.замер ? эл('div', { класс: 'в-числа' }, [
      строка_числа('answers so far', String(ai.замер.ответов)),
      строка_числа('average answer',
                   `${ai.замер.вышло_в_среднем.toFixed(0)} tokens`),
      строка_числа('average time', слова.длина(ai.замер.секунд_в_среднем)),
      строка_числа('tokens today (in + out)',
                   `${ai.за_сегодня.вошло} + ${ai.за_сегодня.вышло}`),
    ]) : null,
  ]);
}

function строка_числа(зовут, значение) {
  return эл('div', {}, [эл('span', { текст: зовут }),
                        эл('b', { текст: значение })]);
}

// ── Your samples ──────────────────────────────────────────────────────

function эталоны() {
  const поле_ = эл('textarea', {
    класс: 'vc-textarea vc-textarea--prompt', rows: '12',
    placeholder: 'one description per line',
    свойства: { value: ai.эталоны.join('\n') },
  });
  return [
    эл('div', { класс: 'vc-card' }, [
      эл('div', { класс: 'в-ряд' }, [
        эл('b', { класс: 'vc-card__title', текст: 'Your samples' }),
        растяжка(),
        ai.эталоны.length
          ? метка(слова.счёт(ai.эталоны.length, 'sample', 'samples'), 'good')
          : метка('none', 'off'),
      ]),
      эл('p', {
        класс: 'в-подпись', стиль: { margin: '0' },
        текст: 'Ten or so real descriptions from your own posts — and AI ' +
               'writes in your voice instead of from scratch. This beats ' +
               'any prompt: showing an example is shorter than explaining. ' +
               'AI takes the manner from them, not the language.',
      }),
      поле_,
      эл('div', { класс: 'в-ряд' }, [
        эл('button', {
          класс: 'vc-btn vc-btn--sm', текст: 'Save',
          на: { click: () => положить_эталоны(поле_.value) },
        }),
        эл('span', {
          класс: 'в-подпись',
          текст: 'samples are optional — without them AI writes from ' +
                 'the prompt alone, and that\'s fine',
        }),
      ]),
    ]),
  ];
}

// ── Дела ──────────────────────────────────────────────────────────────

async function настроить(что) {
  убрать_полосы();
  try {
    const было_моделью = ai.модель;
    ai = await связь.послать('ai-настроить', что);
    // Список моделей у нового поставщика свой — старый показывать
    // нельзя: он от прежнего и просто неверен.
    if ('протокол' in что) { список_моделей = null; свои_имена = false; }  // ключ json, не для человека
    рисовать();
    if ('протокол' in что) сказано_про_протокол(было_моделью);  // ключ json, не для человека
    else сказать({ вид: 'good', что: 'Saved.' });
  } catch (беда) { сказать_беду(беда); }
}

// Переключили протокол — сказать, что поехало ВМЕСТЕ с ним.
//
// **Адрес меняется сам, и это правильно**: адреса у поставщиков
// разные, и оставить прежний значило бы отправить ключ Anthropic
// на `api.openai.com`. Свой вписанный адрес при этом не трогается —
// человек его для того и вписывал.
//
// **А имя модели не меняется, и это тоже правильно.** Подставить
// его сервис не может: держать список названий ему запрещено —
// вшитый устареет молча. Но молчать об этом нельзя: имя от прежнего
// поставщика у нового не работает, и отказ придёт «нет такой
// модели» — то есть уже после того, как человек нажал платную
// кнопку. Поэтому про модель говорится ЗДЕСЬ и её имя называется.
function сказано_про_протокол(было_моделью) {
  сказать({
    вид: 'ask',
    что: `API type: ${ai.протокол === 'anthropic' ? 'Anthropic' : 'OpenAI'}. ` +
         `The address is now ${ai.адрес}.`,
    делать: `Each provider has its own keys and models. Vertcut keeps ` +
            `one key per provider and switches it for you, but the ` +
            `model name stayed the same — “${было_моделью}”. Check that ` +
            `it's a model of the new provider: its list arrives as soon ` +
            `as it answers.`,
  });
}

async function положить_инструкцию(какая, текст) {
  убрать_полосы();
  try {
    ai = await связь.послать('ai-инструкция', { какая, текст });
    рисовать();
    сказать({ вид: 'good',
              что: текст.trim() ? 'Prompt saved.'
                                : 'Back to the default prompt.' });
  } catch (беда) { сказать_беду(беда); }
}

async function положить_эталоны(текст) {
  убрать_полосы();
  try {
    ai = await связь.послать('ai-эталоны', { текст });
    рисовать();
    сказать({ вид: 'good', что: 'Saved.' });
  } catch (беда) { сказать_беду(беда); }
}

// Проверка ключа — одно дешёвое обращение, и оно тоже стоит денег.
// Поэтому сервис говорит, СКОЛЬКО оно стоило: это первое место, где
// человек видит, что кнопки здесь платные.
async function проверить() {
  убрать_полосы();
  // Сперва дописать то, что человек только что вставил в поле,
  // — иначе проверка уйдёт со старым ключом.
  const вставлен = поле_ключа && поле_ключа.value.trim();
  if (вставлен) {
    try { ai = await связь.послать('ai-настроить', { ключ: вставлен }); }
    catch (беда) { return сказать_беду(беда); }
  }
  сказать({ вид: 'ask', что: 'Asking…',
            делать: 'one short request to the model' });
  try {
    const ответ = await связь.послать('ai-проверить');
    убрать_полосы();
    ai = ответ;
    рисовать();
    const п = ответ.проверка;
    сказать({
      вид: 'good',
      что: `It answers: ${п.модель}, in ${слова.длина(п.секунд)}`,
      делать: п.стоило === null || п.стоило === undefined
        ? 'Vertcut doesn\'t know what this cost: it has no price for ' +
          'this model'
        : `cost: ${слова.деньги(п.стоило)}`,
    });
  } catch (беда) {
    // Полоса «Asking…» уходит и при отказе: иначе она висела рядом
    // с ним, будто проверка ещё идёт. Найдено на снимке 21-й сессии.
    убрать_полосы();
    сказать_беду(беда);
  }
}


// Пара «слева имя, справа словами». Своя раскладка, потому что
// «в-числа» — про числа: там правая колонка моноширинная и прижата
// вправо. Фраза, прижатая вправо и набранная моноширинным, читается
// как код и переносится посреди себя.
function пара(слева, справа) {
  return эл('div', {}, [
    моно(слева), эл('span', { текст: справа }),
  ]);
}


