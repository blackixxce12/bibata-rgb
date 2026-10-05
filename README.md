# Bibata-RGB

![Курсоры Bibata-RGB](docs/cursors.gif)

Анимированный радужный курсор на основе [Bibata Modern Ice](https://github.com/ful1e5/Bibata_Cursor)
для Hyprland (hyprcursor + XCursor) и вращающиеся радужные рамки окон. Одна команда
включает всё, другая возвращает исходную тему и прежние цвета рамок.

- Белое тело всех 56 курсоров (145 имён с алиасами) заменено радугой, которая плавно течёт
  вдоль формы; один цикл — 2,16 с. Чёрный контур, бейджи и размер остаются как у Bibata.
- Рамки окон — радужный градиент, который вращается: один оборот за 5 с.
  Неактивные окна — та же радуга, приглушённая.

![Вращающаяся рамка (иллюстрация)](docs/borders.gif)

*English summary at the end.*

## Установка

Рассчитано на Hyprland с конфигом на Lua (проверено на 0.56.2) и сессию через uwsm — как в
CachyOS Hyprland (noctalia). Подойдёт и свежая система.

```bash
shelly install standard --needed python-gobject python-cairo librsvg hyprcursor
git clone https://github.com/blackixxce12/bibata-rgb.git
cd bibata-rgb
./install.sh
~/.local/bin/rgb-theme on
```

Полный путь нужен только в первый раз: на свежей системе папки `~/.local/bin` ещё нет, и fish
добавит её в PATH только в новых терминалах. Дальше достаточно `rgb-theme ...`.

`install.sh` собирает тему (несколько секунд), ставит её в `~/.local/share/icons/Bibata-RGB`,
модуль рамок в `~/.config/hypr/config/rgb.lua` и переключатель `rgb-theme` в
`~/.local/bin`. Если в системе нет Bibata-Modern-Ice, он ставит оригинал из `vendor/`. Сам
`install.sh` ничего не включает. При переустановке выбранные скорости, режим `spin` и
вариант XCursor сохраняются; если RGB-курсор уже включён, `rgb-theme on` перечитает тему.

XCursor-часть (для XWayland и GTK3) бывает двух вариантов:

| | Размеры | На диске |
|---|---|---|
| `./install.sh --lite` (по умолчанию) | 24, 32, 40, 48, 64 px | ~54 МБ |
| `./install.sh --full` | 16–96 px, как у оригинала | ~235 МБ |

Hyprland и программы грузят только нужный размер, так что вариант влияет лишь на место на
диске и на то, найдётся ли точный размер для необычных масштабов.

Для сборки нужны `python-gobject`, `python-cairo`, `librsvg` и `hyprcursor` (первая строка
выше; `--needed` пропускает уже установленные). На свежей CachyOS обычно не хватает
`python-cairo`. Если чего-то нет, `install.sh` скажет об этом и ничего не тронет. Если
`generate.py` или `vendor/` новее сборки (например, после `git pull`), `install.sh` соберёт
тему заново.

**Без сборки:** скачайте `Bibata-RGB.tar.xz` (или `Bibata-RGB-full.tar.xz`) со страницы
[Releases](https://github.com/blackixxce12/bibata-rgb/releases), распакуйте его в `build/`
и запустите `./install.sh` (для full-архива — `./install.sh --full`). Сборка тогда
пропускается. Ключ `-m` важен: файлы получают время распаковки, иначе `install.sh` сочтёт
сборку старше исходников и пересоберёт её.

```bash
mkdir -p build && tar -xJmf Bibata-RGB.tar.xz -C build
```

## Управление

```bash
rgb-theme status              # что сейчас включено и что вернёт off
rgb-theme on                  # RGB-курсор и RGB-рамки
rgb-theme off                 # вернуть всё как было до on
rgb-theme off cursor          # только курсор назад (рамки остаются RGB)
rgb-theme off borders         # только рамки назад
rgb-theme toggle [cursor|borders]
rgb-theme spin loop           # рамки вращаются всё время (по умолчанию)
rgb-theme spin focus          # один оборот при фокусе окна, потом покой (экономнее)
rgb-theme spin off            # радуга стоит
rgb-theme speed               # текущие скорости
rgb-theme speed cursor 1      # курсор: секунд на цикл радуги (0,3–20; по умолчанию 2,16)
                              # (спиннер ожидания крутится быстрее или медленнее вместе с ней)
rgb-theme speed borders 3     # рамки: секунд на оборот (0,3–10; по умолчанию 5)
rgb-theme speed cursor default
rgb-theme version
```

### Что вернёт off

Первый `on` сохраняет то, что собирается изменить, в `~/.local/state/bibata-rgb/`: копии
файлов, а для отсутствующих — сам факт, что их не было; значение gsettings (и было ли оно
вообще задано); переменные `XCURSOR_THEME`/`HYPRCURSOR_THEME` окружения systemd. `off`
возвращает ровно это и удаляет снимок. Если до `on` стояла, например, `MyCustomCursor`,
после `off` снова будет `MyCustomCursor` — во всех файлах, в gsettings, в окружении и в
самом Hyprland (темы `XCURSOR` и `HYPRCURSOR` восстанавливаются каждая своя).

- Файл, который после `on` правили вручную, сохраняет эти правки; в нём возвращается только
  строка темы курсора (для `hyprland.lua` — убирается только строка `require("config.rgb")`).
  gsettings и переменные окружения возвращаются, только если там всё ещё `Bibata-RGB`.
- Файл, которого до `on` не было, `off` не удаляет; если в нём стоит `Bibata-RGB`, эта
  строка меняется на прежнюю тему.
- Повторный `on` снимок не перезаписывает. Если же RGB уже убрали другим способом, снимок
  считается устаревшим: `off` его просто удаляет, а следующий `on` делает новый.
- Если `on` прервался на полпути, его снимок сохраняется: повторный `on` доделает работу, а
  `off` вернёт состояние до него. Два одновременных запуска (например, двойное нажатие на
  бинд с `toggle`) выполняются по очереди.
- Переменную, которой до `on` не было в окружении D-Bus, убрать оттуда нельзя: она
  останется до перезахода (это касается только программ, запускаемых через D-Bus).
- Если RGB включили версией 1.0 (снимков тогда не было), `off` переключает на
  Bibata-Modern-Ice, как раньше; следующий `on` уже сохранит снимок.

Перед правками скрипт проверяет, что тема установлена, `hyprland.lua` и `rgb.lua` на
месте, а папки с изменяемыми файлами доступны для записи; иначе он ничего не трогает. Если
Hyprland недоступен, файлы всё равно переключаются, и изменения вступят в силу при
следующем входе.

Курсор меняется сразу. Уже запущенные приложения и курсор XWayland по умолчанию
переключаются после перезахода в сессию. Окна, открытые, пока рамки не двигались (рамки
выключены или `spin off`), вращаются непрерывно только после переоткрытия: Hyprland
включает зацикливание при открытии окна. До этого они делают один оборот при каждом
фокусе. После `off` → `on` рамки снова начинают вращаться, когда окно получит фокус.

### Что меняет rgb-theme

| Где | Что |
|---|---|
| `~/.config/uwsm/env` | `HYPRCURSOR_THEME`, `XCURSOR_THEME` |
| `~/.config/gtk-3.0/settings.ini` | `gtk-cursor-theme-name` |
| `~/.config/xsettingsd/xsettingsd.conf` | `Gtk/CursorThemeName` |
| `~/.icons/default/index.theme` | `Inherits=` |
| gsettings | `org.gnome.desktop.interface cursor-theme` |
| окружение systemd/dbus и Hyprland | `XCURSOR_THEME`, `HYPRCURSOR_THEME` (на лету) |
| `~/.config/hypr/hyprland.lua` | строка `require("config.rgb")` после `require("config.workspaces")` |
| `~/.local/state/bibata-rgb/` | снимок состояния до `on` (удаляется при `off`) |

Отсутствующие файлы пропускаются; если в `~/.config/uwsm/env` нет строки
`export HYPRCURSOR_THEME=...`, скрипт предупредит, что после перезахода тема не сохранится.
Размер курсора не меняется.

## Настройка

Скорость меняется командой `rgb-theme speed` (см. выше). Для курсора она переписывает
задержки кадров в установленной теме и сразу перечитывает её; кадры те же, поэтому
переливание остаётся таким же плавным, только быстрее или медленнее. Спиннер ожидания
крутится вместе с радугой. Чем короче цикл, тем чаще Hyprland меняет кадр курсора: при
0,3 с это ~120 раз в секунду (у спиннера ~180) вместо ~17 при 2,16 с.

Цвета и прозрачность неактивных рамок (`"66"`) задаются в `hypr/rgb.lua`; после правки
запустите `./install.sh`. Правки, внесённые прямо в установленный
`~/.config/hypr/config/rgb.lua`, `install.sh` сохраняет в `rgb.lua.bak-<дата>` и заменяет
файл; `SPIN` и `TURN` (режим и скорость) переносятся.

У заблокированных групп окон тёплая радуга. Полоски вкладок групп Hyprland рисует одним
цветом: фиолетовый, у заблокированных — оранжевый.

Курсор: палитра (`RAINBOW`) и число кадров — константы в начале `generate.py`. После
правки: `python3 generate.py && ./install.sh`, затем `rgb-theme on`, чтобы Hyprland
перечитал тему. Для уже установленной темы скорость задаёт `rgb-theme speed cursor`, а
размеры XCursor — `./install.sh --lite|--full`; опции `generate.py --cycle-ms` и
`--xcursor` нужны для первой установки или для своих архивов (`install.sh` сохраняет
установленную скорость, только если сборка сделана со скоростью по умолчанию).

## Удаление

```bash
rgb-theme off
rm ~/.config/hypr/config/rgb.lua ~/.local/bin/rgb-theme
rm -r ~/.local/share/icons/Bibata-RGB ~/.local/state/bibata-rgb
```

## Как это устроено

- `generate.py` написан под конкретный исходник — Bibata-Modern-Ice v2.0.6 из `vendor/`:
  его правила перекраски опираются на разметку именно этих SVG. Перед сборкой он проверяет
  имя и версию в `manifest.hl`, контрольную сумму дерева `vendor/Bibata-Modern-Ice` (пути,
  содержимое, симлинки) и число форм и имён (56 и 145); затем — что у каждой формы есть файл
  XCursor, все алиасы XCursor указывают на файлы, в каждом кадре срабатывают все правила для
  этой формы, а у спиннеров — все 4 лопасти. При любом расхождении сборка останавливается с
  перечнем проблем, а не выдаёт тихо неперекрашенную тему. `--no-verify` позволяет собрать из
  другого исходника: он пропускает проверки имени, версии, контрольной суммы и числа форм,
  остальные выполняются.
- Затем `generate.py` берёт SVG-исходники Bibata-Modern-Ice из `vendor/` и заменяет белый цвет
  тела повторяющимся радужным градиентом, который в каждом кадре сдвигается на долю
  периода. Направление градиента выбирается по оси формы: у карандаша и диагональных стрелок
  радуга идёт вдоль них. Особые формы:
  - у X_cursor и wayland-cursor радужный светлый контур;
  - у «запрещено» (crossed_circle) тонкое радужное кольцо внутри чёрного края;
  - у угловых курсоров изменения размера сектор окрашен радугой со сдвигом на полпериода,
    чтобы уголок-указатель выделялся;
  - лопасти спиннера ожидания — чередующиеся светлые и тёмные полупрозрачные.
- hyprcursor: SVG-кадры, 36 кадров на цикл (у спиннеров 54); при скорости по умолчанию это
  60 и 40 мс на кадр. SVG рисуются ровно в том
  размере, который просит Hyprland (24 × наибольший масштаб мониторов), поэтому курсор
  корректен при любом масштабе. Проверено на 20–72 px против оригинала: покрытие и хотспоты
  совпадают у всех 145 имён.
- XCursor (для XWayland и GTK3): 24 кадра на цикл (спиннеры 54); размеры — по варианту lite
  или full (см. «Установка»). В lite запросы за пределами 24–64 получат ближайший размер.
- В теме лежит `BUILD-INFO`: версия, исходник, вариант XCursor и текущая длина цикла.

### Цена

Замеры на ноутбуке с RTX 3060 и экраном 165 Гц, масштаб 1,6:

- Каждая загрузка темы рисует все ~2050 кадров: ~0,5 с, и Hyprland в это время стоит.
  Загрузка бывает при старте, при `rgb-theme on` и дважды при каждой смене раскладки мониторов
  (пробуждение, переключение VT, подключение монитора) — около 1 с. `rgb-theme off` грузит
  исходную тему за ~0,04 с.
- Память Hyprland: +~25 МБ, после перезахода ещё ~+30 МБ (его XCursor-менеджер грузит все
  145 анимированных файлов). Программы, которые сами грузят всю XCursor-тему
  (libwayland-cursor, GTK3), тратят на курсоры примерно в 7 раз больше памяти, чем с
  оригиналом (~34 МБ против ~5 МБ при 48 px). Современные приложения просят курсор у
  Hyprland по протоколу cursor-shape и этого не платят.
- `spin loop`: пока на экране есть вращающаяся рамка, Hyprland перерисовывает экран на
  частоте обновления вместо простоя, а его таймер анимаций просыпается ~1000 раз/с (и тикает,
  даже если окно скрыто). Это ~4–6 % ядра, и видеокарта всё время рисует кадры. На батарее
  экономнее `rgb-theme spin focus`.
- PNG-вариант (`python3 generate.py --hypr-format png`) грузится мгновенно, но libhyprcursor
  0.1.13 обрезает PNG-кадры, которые приходится заметно уменьшать (при масштабе 1, 1,25 и
  1,75 курсор был бы срезан). Поэтому по умолчанию SVG.

## Инструменты

Для превью нужен Pillow: `shelly install standard --needed python-pillow`.

- `python3 preview.py` — `build/preview.png`: все курсоры, 4 фазы, на светлом и тёмном фоне.
- `python3 tools/make_previews.py` — GIF-превью в `docs/`.
- `tools/hctest.cpp` — загрузка темы через libhyprcursor: время, память, кадры, хотспоты и
  покрытие по формам.

  ```bash
  bash -c 'g++ -O2 -std=c++20 tools/hctest.cpp -o tools/hctest $(pkg-config --cflags --libs hyprcursor cairo)'
  tools/hctest Bibata-RGB 38 left_ptr wait text
  ```

## Лицензия

GPL-3.0 (см. `LICENSE`). Bibata Cursor — автор Abdulkaiz Khatri (ful1e5),
<https://github.com/ful1e5/Bibata_Cursor>, GPL-3.0. Неизменённая копия Bibata-Modern-Ice
лежит в `vendor/` (подробнее — `vendor/README.md`).

---

## English summary

An animated rainbow version of the Bibata Modern Ice cursor for Hyprland (hyprcursor and
XCursor), plus rainbow window borders that keep turning, with a switch that puts everything
back.

```bash
sudo pacman -S --needed python-gobject python-cairo librsvg hyprcursor
git clone https://github.com/blackixxce12/bibata-rgb.git && cd bibata-rgb
./install.sh                 # builds the theme, installs theme + border module + rgb-theme
~/.local/bin/rgb-theme on    # later just: rgb-theme off / on / status
rgb-theme spin focus         # borders turn once on focus instead of all the time (cheaper)
```

`rgb-theme off` restores exactly what was there before the first `on` (files, whether they
existed, gsettings, the session environment), saved in `~/.local/state/bibata-rgb`; files
edited by hand in between keep those edits. `rgb-theme speed cursor <s>` and
`rgb-theme speed borders <s>` set the animation speeds; `./install.sh --full` adds the
16–96 px XCursor sizes (~235 MB instead of ~54 MB). The generator checks that
`vendor/Bibata-Modern-Ice` is exactly Bibata-Modern-Ice v2.0.6 (name, version, tree checksum)
and that every recolouring rule matches before it builds.

Needs Hyprland with a Lua config (tested on 0.56.2) and a uwsm session (the CachyOS Hyprland
layout); building needs python-gobject, python-cairo, librsvg and hyprcursor. Prebuilt themes
(Bibata-RGB.tar.xz, Bibata-RGB-full.tar.xz; unpack with `tar -xJmf ... -C build`) are attached
to the releases. The theme is generated from the GPL-3.0 Bibata sources
kept in `vendor/`. The turning borders keep Hyprland redrawing at the monitor's refresh rate
(about 4–6 % of a CPU core in the author's measurements), and loading the animated theme
takes about 0.5 s.
