// Экран «Если не работает».
//
// **Её читают в ту минуту, когда всё сломалось, и это определяет всё.**
// Человек здесь не изучает сервис — он застрял и раздражён. Значит:
//
// - никаких рассказов о том, как хорошо всё устроено;
// - каждая строка начинается с ТОГО, ЧТО ОН ВИДИТ, а не с причины;
// - путь к файлу написан целиком и рядом с кнопкой «показать в папке»,
//   а не словами «найдите в настройках»;
// - сперва то, что случается часто, потом редкое.
//
// **И здесь стоят факты про ЭТУ машину, а не инструкция вообще.**
// Инструкция говорит «посмотрите в журнал»; тут написан путь к нему
// и лежат последние строки последнего запуска. Человек, у которого
// что-то сломалось, не должен ещё и искать, где смотреть.

import {
  нарисовать, лого, блок, эл, моно, метка, растяжка,
  сказать_беду, подвал,
} from '../shell.js';
import * as связь from '../api.js';
import * as адрес from '../route.js';
import * as слова from '../words.js';

let это = null;
let окружение = null;

export async function показать() {
  это = await связь.взять('помощь');
  окружение = null;
  рисовать();
  // Окружение приезжает отдельно и потом: оно поднимает каждую
  // библиотеку по имени, а страница помощи обязана открыться сразу.
  // Ждать её появления, глядя в пустоту, — ровно то, из-за чего сюда
  // и пришли.
  try {
    окружение = await связь.взять('окружение');
    if (адрес.части()[0] === 'help') рисовать();
  } catch (беда) { сказать_беду(беда); }
}

function рисовать() {
  нарисовать({
    колонка: колонка(),
    заголовок: эл('h1', { класс: 'vc-h1' }, ['Not working?']),
    лид: 'The most common problems first. ' +
         'Below that — what is on your computer right now.',
    тело: [
      беды(),
      где_что_лежит(),
      что_сейчас(),
      журнал(),
      напоследок(),
    ],
  });
}

function колонка() {
  return [
    лого(),
    блок('', [
      эл('button', {
        класс: 'в-подвал', на: { click: () => адрес.идти('videos') },
      }, [эл('span', { текст: '← all videos' })]),
    ]),
    растяжка(),
    подвал((куда) => адрес.идти(куда)),
  ];
}

// ── что случается чаще всего ─────────────────────────────────────────
//
// Порядок не алфавитный и не по разделам сервиса, а ПО ЧАСТОТЕ.
// Человек читает сверху вниз и должен найти своё в первых двух-трёх.
const БЕДЫ = [
  {
    вижу: 'I clicked the icon and nothing opened',
    делать: [
      'Wait half a minute: the first time, Vertcut needs a moment to start.',
      'Click the icon again — a second click doesn\'t start a second ' +
      'Vertcut, it opens the same tab.',
      'Still nothing — look at the last lines of the log at the bottom ' +
      'of this page.',
    ],
  },
  {
    вижу: 'The first time, the system said the app is damaged',
    делать: [
      // Не «куплено у Apple», а подпись: система говорит так про всё,
      // что не подписано платным ключом разработчика.
      'It isn\'t. The system says this about any app that isn\'t signed ' +
      'with a paid Apple developer account ($99 a year).',
      'macOS: System Settings → Privacy & Security → at the bottom, ' +
      '“Open Anyway”.',
      'Windows: “More info” → “Run anyway”.',
      'You only do this once.',
    ],
  },
  {
    вижу: 'Analysis takes very long',
    делать: [
      // «Два часа — около часа» — пересчёт, а не замер: длинное видео
      // не мерялось (TODO.md, «Всё мерялось на коротких видео»).
      'A 20-minute video takes about 9 minutes; a two-hour video should ' +
      'take about an hour. That\'s by design: a video is analyzed once, ' +
      'and you can cut as many clips from it as you like.',
      'The longest stage is transcribing. Its progress is honest: how ' +
      'many seconds of audio have been heard so far, out of how many.',
      'You can close the tab, but don\'t let the computer sleep: the work ' +
      'runs on its own and survives a closed tab, but not sleep.',
    ],
  },
  {
    вижу: 'Subtitles change page in the middle of a phrase',
    делать: [
      'That\'s not a bug: a long phrase is shown in pages.',
      'If you want it otherwise, split the phrase in the subtitle editor ' +
      'or shorten its text.',
      'Or pick a narrower preset: each preset says what share of phrases ' +
      'will need two pages.',
    ],
  },
  {
    вижу: 'A clip doesn\'t play in the browser',
    делать: [
      'Download it with the button next to it and open it in your own ' +
      'player — the file is fine, browsers are just picky.',
      'Preview shows the original and doesn\'t draw subtitles: export ' +
      'draws them with the real font.',
    ],
  },
  {
    вижу: 'Vertcut says the API key was not accepted',
    делать: [
      'Check that the API type in Settings matches the provider the key ' +
      'is from: an Anthropic key doesn\'t work on an OpenAI address.',
      // Набрать ключ «заново» нельзя — он длинный, а поставщик
      // показывает его один раз. Честный совет — скопировать или
      // завести новый.
      'Some Cyrillic letters look exactly like Latin ones. If the key ' +
      'went through a chat or a document, copy it again from where you ' +
      'saved it — or create a new key at your provider.',
      'Without a key, everything works except three buttons: AI ' +
      'suggestions for segments, AI descriptions and Check with AI ' +
      'for subtitles.',
    ],
  },
  {
    вижу: 'Everything is gone after reinstalling',
    делать: [
      'Nothing is gone. Reinstalling only touches the app itself.',
      'Your analyses, clips, API key, spending history and my style ' +
      'are kept separately — the paths are below.',
    ],
  },
];

function беды() {
  // Стопка раскрывашек, и просвет между ними задан ЗДЕСЬ.
  //
  // Раскрывашка держит черту сверху и отступ под неё, а снизу
  // не держит ничего — снизу её отделяет просвет контейнера. Пока
  // контейнер был обычным `div`, просвета не было вовсе: над словами
  // стояло шестнадцать пикселей, под ними — ноль, и каждая строка
  // висела прижатой к своей черте. Автор увидел это первым же
  // взглядом.
  //
  // Просвет равен отступу сверху, а не взят на глаз: тогда слова
  // стоят ровно посередине между двумя чертами, и это видно.
  return эл('div', { класс: 'в-стопка' }, БЕДЫ.map((б) => эл('details', { класс: 'в-раскрывашка' }, [
    эл('summary', { текст: б.вижу }),
    эл('ul', {}, б.делать.map((с) => эл('li', { текст: с }))),
  ])));
}

// ── где что лежит ────────────────────────────────────────────────────

function где_что_лежит() {
  const ряд = (зовут, путь, зачем) => эл('div', { класс: 'в-ряд' }, [
    эл('div', {}, [
      эл('div', { текст: зовут }),
      эл('div', { класс: 'vc-meta', текст: зачем }),
    ]),
    растяжка(),
    моно(путь || '—'),
  ]);
  // **Свёрнуто.** Пять путей в моноширинном шрифте — это пять
  // длинных строк посреди страницы, на которую человек пришёл
  // с бедой. Пути нужны, но не всем и не сразу: их ищут, когда
  // уже прочли, что делать. Раскрывашка — то же правило, по
  // которому свёрнуты сами беды выше.
  return раскрыть('Where things are', [
    ряд('Analyses and exported clips', это.пути.разборы,
        'your work; updates never touch it'),
    ряд('Inbox', это.пути.входящие,
        'videos dropped into the browser window'),
    ряд('Settings', это.пути.настройки,
        'API key, spending history, my style'),
    ряд('Log', это.пути.журнал,
        'what Vertcut said when started from the icon'),
    ряд('The app itself', это.пути.программа,
        'you can delete it entirely — everything else stays'),
  ]);
}

// ── что сейчас на машине ─────────────────────────────────────────────

function что_сейчас() {
  if (!окружение) {
    return блок('On this computer right now', [
      эл('div', { класс: 'vc-meta', текст: 'checking…' }),
    ]);
  }
  // Полосой здесь сказать нельзя, и это не мелочь: `сказать` кладёт
  // полосу в свою область наверху страницы и её же возвращает.
  // Вставь её ещё и сюда — узел уедет из одного места в другое,
  // потому что один и тот же узел не лежит в двух местах сразу.
  return блок('On this computer right now', [
    окружение.всё_на_месте ? null
      : эл('div', { класс: 'в-ряд' }, [
          эл('span', { текст: 'Something is missing — the lines below ' +
                              'say what.' }),
          растяжка(),
          метка('incomplete', 'bad'),
        ]),
    эл('pre', { класс: 'в-хвост', текст: окружение.строки.join('\n') }),
  ].filter(Boolean));
}

// ── журнал ───────────────────────────────────────────────────────────

function журнал() {
  if (!это.лог.файл) {
    return блок('Log', [
      эл('div', { класс: 'vc-meta',
                  текст: 'Empty so far: Vertcut has never been started ' +
                         'from the icon. From the terminal it prints ' +
                         'straight into the window.' }),
    ]);
  }
  return блок('Last launch', [
    эл('div', { класс: 'в-ряд' }, [
      моно(это.лог.файл),
      растяжка(),
      метка(слова.счёт(это.лог.сколько, 'launch logged', 'launches logged'),
            ''),
    ]),
    эл('pre', { класс: 'в-хвост', текст: это.лог.строки.join('\n') }),
    эл('div', { класс: 'vc-meta',
                текст: 'There is no API key in this file — only its last ' +
                       'four characters. It does show your folder and ' +
                       'file names.' }),
  ]);
}

// Раздел, свёрнутый в раскрывашку. Тот же узел, что у бед выше:
// второй такой же разошёлся бы с первым — правило, по которому
// в проекте вообще заведена одна раскрывашка на всё.
function раскрыть(зовут, дети) {
  return эл('details', { класс: 'в-раскрывашка' }, [
    эл('summary', { текст: зовут }),
    эл('div', { класс: 'в-поля-столбиком' }, дети),
  ]);
}

function напоследок() {
  return блок('If none of this helped', [
    эл('ul', {}, [
      эл('li', { текст: 'Quit Vertcut (the last line of the left column) ' +
                        'and open it again: nothing is lost, everything ' +
                        'is on disk.' }),
      эл('li', { текст: 'Delete the app folder (path above) and click the ' +
                        'icon — it installs again. Your analyses, API key ' +
                        'and settings stay.' }),
    ]),
    // Живой адрес последней строкой, и это конец дороги: всё, что
    // человек мог сделать сам, стоит выше.
    //
    // **Адрес публичный, и это меняет совет.** Письмо читал один автор;
    // задачу на GitHub читают все. Поэтому про журнал сказано не только
    // «ключа там нет», но и что в нём видны имена папок и файлов.
    эл('p', { класс: 'в-подпись', стиль: { margin: '0' } }, [
      'Nothing helped — tell us at ',
      эл('a', { href: КУДА_ПИСАТЬ, target: '_blank',
                rel: 'noopener noreferrer', текст: КУДА_ПИСАТЬ }),
      '. Add the last lines of the log. Issues there are public: the log ' +
      'has no API key, but it does show your folder and file names — ' +
      'look through it before posting.',
    ]),
  ]);
}

// Куда писать, когда не помогло ничего. Одно место: адрес меняется
// вместе с тем, кто сервис раздаёт, и второй такой же в разметке
// разъехался бы с этим молча.
const КУДА_ПИСАТЬ = 'https://github.com/eduard1414ed/vertcut/issues';
