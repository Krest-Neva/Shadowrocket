#!/bin/sh
clear

echo "[*] Настройка DNS..."
echo "nameserver 8.8.8.8" > /etc/resolv.conf
echo "nameserver 8.8.4.4" >> /etc/resolv.conf
echo "nameserver 94.140.14.14" >> /etc/resolv.conf
echo "nameserver 94.140.15.15" >> /etc/resolv.conf
echo "nameserver 1.1.1.1" >> /etc/resolv.conf

echo "[*] Проверка соединения..."
TRIES=0
while ! ping -c 3 1.1.1.1 > /dev/null 2>&1; do
    TRIES=$((TRIES+1))
    if [ "$TRIES" -ge 12 ]; then
        echo "[!] Сеть недоступна. Продолжаем без сети."
        break
    fi
    echo "[!] Нет подключения. Повтор через 5 сек... [$TRIES/12]"
    sleep 5
done
echo "[+] Соединение в порядке."

echo "[*] Обновление и установка зависимостей..."
apk update
apk upgrade
apk add --no-cache python3 curl wget aria2 openssl ca-certificates bind-tools bash py3-pip git || echo "[!] Некоторые пакеты не установились"

echo "[*] Проверка папок..."
mkdir -p ~/RegexBuilder/Output
mkdir -p ~/RegexBuilder/Backups

cat << 'PYEOF' > ~/RegexBuilder/RegexBuilder.py
#!/usr/bin/env python3
# ============================================================
#  RegexBuilder — интерактивный конструктор регулярных выражений
#  Поддержка: lookaround, backreferences, conditionals,
#             atomic groups, named groups, inline flags
# ============================================================

import os
import sys
import re
import time
import json
from pathlib import Path
from datetime import datetime

os.umask(0o077)

# ============================================================
#  Язык интерфейса
# ============================================================
LANG = os.environ.get("LANG_SEL", "").strip()
if not LANG:
    try:
        with open(os.path.expanduser("~/.sr_toolkit_lang")) as _f:
            LANG = _f.read().strip()
    except Exception:
        LANG = "ru"
if LANG not in ("ru", "en"):
    LANG = "ru"

# ============================================================
#  Пути
# ============================================================
ROOT = Path.home()
BASE = ROOT / "RegexBuilder"
OUTPUT_DIR = BASE / "Output"
BACKUP_DIR = BASE / "Backups"
HISTORY_FILE = BASE / "history.json"

# ============================================================
#  Словарь переводов
# ============================================================
_T = {
"ru": {
"menu": "ГЛАВНОЕ МЕНЮ",
"m1": "1 - Создать regex (мастер)",
"m2": "2 - Объяснить regex",
"m3": "3 - Протестировать regex",
"m4": "4 - Быстрые шаблоны",
"m5": "5 - Расширенный конструктор (lookaround/backref/conditional)",
"m6": "6 - История",
"m7": "7 - Загрузить из файла",
"mq": "q - Выход",
"choice": "Ваш выбор",
"bad": "Неверный выбор",
"press": "Нажмите Enter для продолжения",
"exit": "Выход.",
"step1": "ШАГ 1: Что ДОЛЖНО совпадать?",
"step1_q": "Введите примеры строк по одному. Пустая строка — конец.",
"step1_added": "Добавлено. Всего",
"step1_need": "Нужен хотя бы 1 пример.",
"step2": "ШАГ 2: Что НЕ ДОЛЖНО совпадать?",
"step2_q": "Введите примеры. Пустая строка — конец.",
"step2_skip": "(Enter — пропустить)",
"step3": "ШАГ 3: Где искать?",
"step3_1": "1 - Везде по тексту",
"step3_2": "2 - Только целое слово",
"step3_3": "3 - Только начало строки",
"step3_4": "4 - Только конец строки",
"step3_5": "5 - Только вся строка целиком",
"step4": "ШАГ 4: Флаги",
"step4_case": "Учитывать регистр?",
"step4_multiline": "Многострочный режим (^ и $ для каждой строки)?",
"step4_dotall": "Точка захватывает перевод строки?",
"step4_verbose": "Разрешить пробелы и # комментарии в шаблоне?",
"step5": "ШАГ 5: Группы захвата",
"step5_q": "Сколько групп захвата? (0 — без групп)",
"step5_name": "Имя группы",
"step6": "ШАГ 6: Дополнительно",
"step6_q": "Добавить фильтры-условия? (y/n)",
"step6_include": "ВКЛЮЧИТЬ если содержит",
"step6_exclude": "ИСКЛЮЧИТЬ если содержит",
"step6_kw": "Ключевое слово",
"step6_done": "Фильтры добавлены",
"build": "Сборка...",
"result": "РЕЗУЛЬТАТ",
"regex": "Регулярное выражение",
"flags": "Флаги",
"groups": "Группы",
"testing": "Проверка на примерах",
"match_ok": "СОВПАДАЕТ",
"match_no": "НЕ СОВПАДАЕТ",
"all_ok": "Все примеры проверены.",
"some_fail": "Некоторые примеры не прошли.",
"save": "Сохранить? (y/n)",
"save_name": "Имя файла (без расширения)",
"save_ok": "Сохранено",
"explain_q": "Введите регулярное выражение",
"explain_empty": "Пустое выражение.",
"explain_err": "Ошибка",
"test_q": "Введите текст. Пустая строка — конец.",
"test_match": "Найдено совпадений",
"test_groups": "Группы",
"hist_hdr": "ИСТОРИЯ",
"hist_empty": "История пуста.",
"hist_hint": "Введите номер для повтора или b для выхода",
"preset_hdr": "БЫСТРЫЕ ШАБЛОНЫ",
"advanced_hdr": "РАСШИРЕННЫЙ КОНСТРУКТОР",
"adv_1": "1 - Добавить ПОЗИТИВНЫЙ LOOKAHEAD  (?=...)",
"adv_2": "2 - Добавить НЕГАТИВНЫЙ LOOKAHEAD  (?!...)",
"adv_3": "3 - Добавить ПОЗИТИВНЫЙ LOOKBEHIND (?<=...)",
"adv_4": "4 - Добавить НЕГАТИВНЫЙ LOOKBEHIND (?<!...)",
"adv_5": "5 - Добавить УСЛОВНЫЙ БЛОК  (?(1)yes|no)",
"adv_6": "6 - Добавить BACKREFERENCE  \\1 \\2 \\3",
"adv_7": "7 - Добавить ИМЕНОВАННЫЙ BACKREF  (?P=name)",
"adv_8": "8 - Добавить АТОМАРНУЮ ГРУППУ  (?>...)",
"adv_9": "9 - Добавить ИМЕНОВАННУЮ ГРУППУ  (?P<name>...)",
"adv_10": "10 - Показать текущий шаблон",
"adv_11": "11 - Протестировать и сохранить",
"adv_12": "12 - Очистить и начать заново",
"adv_q": "q - Готово",
"adv_current": "Текущий шаблон",
"adv_component": "Компонент регулярки",
"adv_pos": "Куда вставить?",
"adv_pos_1": "1 - В начало (префикс)",
"adv_pos_2": "2 - В конец (суффикс)",
"adv_pos_3": "3 - Заменить весь шаблон",
"adv_added": "Добавлено",
"adv_empty": "Пустой шаблон.",
"adv_group_n": "Номер группы (1-9)",
"adv_group_name": "Имя группы (латиница)",
"adv_example_hint": "Пример текста, который должен совпасть",
"y_or_n": "y/n"
},
"en": {
"menu": "MAIN MENU",
"m1": "1 - Build a regex (wizard)",
"m2": "2 - Explain regex",
"m3": "3 - Test a regex",
"m4": "4 - Quick templates",
"m5": "5 - Advanced builder (lookaround/backref/conditional)",
"m6": "6 - History",
"m7": "7 - Load from file",
"mq": "q - Quit",
"choice": "Your choice",
"bad": "Invalid choice",
"press": "Press Enter to continue",
"exit": "Exit.",
"step1": "STEP 1: What SHOULD match?",
"step1_q": "Enter examples one per line. Empty line — end.",
"step1_added": "Added. Total",
"step1_need": "At least 1 example needed.",
"step2": "STEP 2: What should NOT match?",
"step2_q": "Enter examples. Empty line — end.",
"step2_skip": "(Enter — skip)",
"step3": "STEP 3: Where to search?",
"step3_1": "1 - Anywhere in text",
"step3_2": "2 - Whole word only",
"step3_3": "3 - Start of line",
"step3_4": "4 - End of line",
"step3_5": "5 - Whole line only",
"step4": "STEP 4: Flags",
"step4_case": "Case sensitive?",
"step4_multiline": "Multiline mode (^ and $ per line)?",
"step4_dotall": "Dot matches newlines?",
"step4_verbose": "Allow whitespace and # comments?",
"step5": "STEP 5: Capture groups",
"step5_q": "How many capture groups? (0 — none)",
"step5_name": "Group name",
"step6": "STEP 6: Additional",
"step6_q": "Add include/exclude filters? (y/n)",
"step6_include": "INCLUDE if contains",
"step6_exclude": "EXCLUDE if contains",
"step6_kw": "Keyword",
"step6_done": "Filters added",
"build": "Building...",
"result": "RESULT",
"regex": "Regular expression",
"flags": "Flags",
"groups": "Groups",
"testing": "Testing examples",
"match_ok": "MATCH",
"match_no": "NO MATCH",
"all_ok": "All examples tested.",
"some_fail": "Some examples failed.",
"save": "Save? (y/n)",
"save_name": "File name (without extension)",
"save_ok": "Saved",
"explain_q": "Enter regular expression",
"explain_empty": "Empty expression.",
"explain_err": "Error",
"test_q": "Enter test text. Empty line — end.",
"test_match": "Matches found",
"test_groups": "Groups",
"hist_hdr": "HISTORY",
"hist_empty": "History is empty.",
"hist_hint": "Enter number to repeat or b to exit",
"preset_hdr": "QUICK TEMPLATES",
"advanced_hdr": "ADVANCED BUILDER",
"adv_1": "1 - Add POSITIVE LOOKAHEAD  (?=...)",
"adv_2": "2 - Add NEGATIVE LOOKAHEAD  (?!...)",
"adv_3": "3 - Add POSITIVE LOOKBEHIND (?<=...)",
"adv_4": "4 - Add NEGATIVE LOOKBEHIND (?<!...)",
"adv_5": "5 - Add CONDITIONAL BLOCK  (?(1)yes|no)",
"adv_6": "6 - Add BACKREFERENCE  \\1 \\2 \\3",
"adv_7": "7 - Add NAMED BACKREF  (?P=name)",
"adv_8": "8 - Add ATOMIC GROUP  (?>...)",
"adv_9": "9 - Add NAMED GROUP  (?P<name>...)",
"adv_10": "10 - Show current pattern",
"adv_11": "11 - Test and save",
"adv_12": "12 - Clear and start over",
"adv_q": "q - Done",
"adv_current": "Current pattern",
"adv_component": "Regex component",
"adv_pos": "Where to insert?",
"adv_pos_1": "1 - At start (prefix)",
"adv_pos_2": "2 - At end (suffix)",
"adv_pos_3": "3 - Replace whole pattern",
"adv_added": "Added",
"adv_empty": "Empty pattern.",
"adv_group_n": "Group number (1-9)",
"adv_group_name": "Group name (latin)",
"adv_example_hint": "Example text that should match",
"y_or_n": "y/n"
}
}


def tr(k):
    return _T.get(LANG, _T["ru"]).get(k, _T["ru"].get(k, k))


# ============================================================
#  Ввод
# ============================================================
def _input(prompt=""):
    try:
        v = input(prompt)
    except (EOFError, KeyboardInterrupt):
        print()
        sys.exit(0)
    if v.strip().lower() in ("q", "quit", "exit"):
        print("[+] " + tr("exit"))
        sys.exit(0)
    return v


def _inp_allow_back(prompt=""):
    try:
        v = input(prompt)
    except (EOFError, KeyboardInterrupt):
        print()
        sys.exit(0)
    if v.strip().lower() in ("q", "quit", "exit"):
        print("[+] " + tr("exit"))
        sys.exit(0)
    return v


def _inp_allow_empty(prompt=""):
    try:
        v = input(prompt)
    except (EOFError, KeyboardInterrupt):
        print()
        sys.exit(0)
    if v.strip().lower() in ("q", "quit", "exit"):
        print("[+] " + tr("exit"))
        sys.exit(0)
    return v


# ============================================================
#  UI
# ============================================================
def clr():
    os.system('clear')


def hdr(t):
    print("=" * 64)
    print(f"  {t}")
    print("=" * 64)


def ln():
    print("-" * 64)


def ensure_dirs():
    for d in [BASE, OUTPUT_DIR, BACKUP_DIR]:
        if not d.exists():
            d.mkdir(parents=True, exist_ok=True)


# ============================================================
#  Классификатор строк
# ============================================================
def classify(s):
    if re.fullmatch(r'\d{1,3}(\.\d{1,3}){3}', s): return 'ipv4'
    if re.fullmatch(r'[\w.+-]+@[\w-]+\.[\w.]+', s): return 'email'
    if re.fullmatch(r'https?://\S+', s): return 'url'
    if re.fullmatch(r'\d{4}-\d{2}-\d{2}', s): return 'date'
    if re.fullmatch(r'\d{2}:\d{2}:\d{2}', s): return 'time'
    if re.fullmatch(r'#[0-9a-fA-F]{6}', s): return 'hexcolor'
    if re.fullmatch(r'[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}', s): return 'uuid'
    if re.fullmatch(r'\+?\d[\d\s\-()]{6,}', s): return 'phone'
    if re.fullmatch(r'([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})', s): return 'mac'
    if re.fullmatch(r'\d+', s): return 'number'
    if re.fullmatch(r'[a-zA-Z]+', s): return 'word'
    if re.fullmatch(r'[a-zA-Z][a-zA-Z0-9_]*', s): return 'identifier'
    return 'literal'


# ============================================================
#  Генератор общего шаблона из примеров
# ============================================================
def build_pattern_from_examples(examples):
    if not examples:
        return None
    tokens = []
    for ex in examples:
        t = classify(ex)
        if t == 'ipv4': tokens.append(r'\d{1,3}(?:\.\d{1,3}){3}')
        elif t == 'email': tokens.append(r'[\w.+-]+@[\w-]+\.[\w.]+')
        elif t == 'url': tokens.append(r'https?://[^\s]+')
        elif t == 'date': tokens.append(r'\d{4}-\d{2}-\d{2}')
        elif t == 'time': tokens.append(r'\d{2}:\d{2}:\d{2}')
        elif t == 'hexcolor': tokens.append(r'#[0-9a-fA-F]{6}')
        elif t == 'uuid': tokens.append(r'[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}')
        elif t == 'phone': tokens.append(r'\+?\d[\d\s\-()]{6,}')
        elif t == 'mac': tokens.append(r'(?:[0-9A-Fa-f]{2}[:-]){5}[0-9A-Fa-f]{2}')
        elif t == 'number': tokens.append(r'\d+')
        elif t == 'word': tokens.append(r'[a-zA-Z]+')
        elif t == 'identifier': tokens.append(r'[a-zA-Z][a-zA-Z0-9_]*')
        else: tokens.append(re.escape(ex))
    unique = []
    for t in tokens:
        if t not in unique:
            unique.append(t)
    if len(unique) == 1:
        return unique[0]
    return '(?:' + '|'.join(unique) + ')'


# ============================================================
#  Объяснение regex по токенам
# ============================================================
def explain_regex(pattern):
    out = []
    i = 0
    n = len(pattern)
    while i < n:
        c = pattern[i]
        if c == '^':
            out.append(("^", "Начало строки" if LANG == "ru" else "Start of line"))
        elif c == '$':
            out.append(("$", "Конец строки" if LANG == "ru" else "End of line"))
        elif c == '.':
            out.append((".", "Любой символ" if LANG == "ru" else "Any character"))
        elif c == '*':
            out.append(("*", "0 или более раз" if LANG == "ru" else "0 or more"))
        elif c == '+':
            out.append(("+", "1 или более раз" if LANG == "ru" else "1 or more"))
        elif c == '?':
            out.append(("?", "0 или 1 раз" if LANG == "ru" else "0 or 1"))
        elif c == '\\' and i + 1 < n:
            nxt = pattern[i + 1]
            d = {'d': 'Цифра', 'D': 'Не цифра', 'w': 'Слово', 'W': 'Не слово',
                 's': 'Пробел', 'S': 'Не пробел', 'b': 'Граница слова', 'B': 'Не граница слова'}
            out.append((f"\\{nxt}", d.get(nxt, f"Спецсимвол \\{nxt}")))
            i += 1
        elif c == '(':
            if i + 2 < n and pattern[i + 1] == '?':
                if pattern[i + 2] == ':':
                    out.append(("(?:", "Незахватывающая группа"))
                elif pattern[i + 2] == '=':
                    out.append(("(?=", "Позитивный lookahead"))
                elif pattern[i + 2] == '!':
                    out.append(("(?!", "Негативный lookahead"))
                elif pattern[i + 2] == '<':
                    if i + 3 < n and pattern[i + 3] in ('=', '!'):
                        sign = pattern[i + 3]
                        out.append((f"(?<{sign}", "Позитивный lookbehind" if sign == '=' else "Негативный lookbehind"))
                    else:
                        out.append(("(?<", "Именованная группа"))
                elif pattern[i + 2] == 'P':
                    out.append(("(?P", "Именованная группа / backreference"))
                elif pattern[i + 2] == '>':
                    out.append(("(?>", "Атомарная группа"))
                elif pattern[i + 2] == '(':
                    out.append(("(?(", "Условный блок"))
                else:
                    out.append(("(?", "Inline-модификатор"))
            else:
                out.append(("(", "Начало группы"))
        elif c == ')':
            out.append((")", "Конец группы"))
        elif c == '|':
            out.append(("|", "ИЛИ"))
        elif c == '[':
            j = pattern.find(']', i)
            if j > i:
                content = pattern[i:j + 1]
                out.append((content, f"Набор символов: {content[1:-1]}"))
                i = j
            else:
                out.append(("[", "Набор символов"))
        elif c == '{':
            j = pattern.find('}', i)
            if j > i:
                content = pattern[i:j + 1]
                out.append((content, f"Количество: {content[1:-1]}"))
                i = j
            else:
                out.append(("{", "Квантор"))
        elif c in '0123456789' and i > 0 and pattern[i - 1] == '\\':
            out.append((f"\\{c}", f"Backreference на группу {c}"))
        else:
            out.append((c, f"Литерал '{c}'"))
        i += 1
    return out


# ============================================================
#  Быстрые шаблоны
# ============================================================
PRESETS = {
    "1": ("Email", r'[\w.+-]+@[\w-]+\.[\w.]+', "test@example.com"),
    "2": ("URL", r'https?://[^\s]+', "https://example.com/path?x=1"),
    "3": ("IPv4", r'\d{1,3}(?:\.\d{1,3}){3}', "192.168.1.1"),
    "4": ("Date", r'\d{4}-\d{2}-\d{2}', "2025-01-15"),
    "5": ("Time", r'\d{2}:\d{2}:\d{2}', "14:30:00"),
    "6": ("Phone", r'\+?\d[\d\s\-()]{6,}', "+7 999 123-45-67"),
    "7": ("HEX", r'#[0-9a-fA-F]{6}', "#FF5733"),
    "8": ("UUID", r'[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}', "550e8400-e29b-41d4-a716-446655440000"),
    "9": ("MAC", r'(?:[0-9A-Fa-f]{2}[:-]){5}[0-9A-Fa-f]{2}', "AA:BB:CC:DD:EE:FF"),
    "10": ("Base64", r'[A-Za-z0-9+/]{20,}={0,2}', "SGVsbG8gV29ybGQ="),
    "11": ("JWT", r'[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+', "eyJhbGc.eyJzdWI.SflKxwRJ"),
    "12": ("Russian phone", r'\+7\s?\(?\d{3}\)?\s?\d{3}[-\s]?\d{2}[-\s]?\d{2}', "+7 (999) 123-45-67"),
}


# ============================================================
#  Сохранение / история
# ============================================================
def load_history():
    if not HISTORY_FILE.exists():
        return []
    try:
        data = json.loads(HISTORY_FILE.read_text(encoding='utf-8'))
        return data if isinstance(data, list) else []
    except Exception:
        return []


def save_history(pattern, flags_desc, examples):
    try:
        hist = load_history()
        hist.append({
            "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "pattern": pattern,
            "flags": flags_desc,
            "examples": examples[:5],
        })
        hist = hist[-50:]
        HISTORY_FILE.write_text(json.dumps(hist, ensure_ascii=False, indent=2), encoding='utf-8')
    except Exception:
        pass


# ============================================================
#  Демонстрация совпадений
# ============================================================
def test_pattern(pattern, flags, match_examples, no_match_examples):
    try:
        compiled = re.compile(pattern, flags)
    except re.error as e:
        print(f"[!] {tr('explain_err')}: {e}")
        return None, None
    results = {"ok": True, "found": [], "missed": [], "unexpected": []}
    print(f"\n  {tr('testing')}:")
    ln()
    for ex in match_examples:
        m = compiled.search(ex)
        if m:
            print(f"    [+] {tr('match_ok')}:  {ex}")
            print(f"        -> '{m.group()}' @ {m.start()}-{m.end()}")
            results["found"].append(ex)
        else:
            print(f"    [-] {tr('match_no')}: {ex}")
            results["missed"].append(ex)
            results["ok"] = False
    for ex in no_match_examples:
        m = compiled.search(ex)
        if not m:
            print(f"    [+] {tr('match_no')}: {ex}")
        else:
            print(f"    [!] {tr('match_ok')}:  {ex}  (не должно совпадать!)")
            results["unexpected"].append(ex)
            results["ok"] = False
    return compiled, results


# ============================================================
#  Сохранение результата
# ============================================================
def save_result(pattern, flags, flag_names, match_examples, no_match_examples, groups_info):
    if _input(f"\n  {tr('save')} [y]: ").strip().lower() == "n":
        return
    name = _inp_allow_empty(f"  {tr('save_name')} [regex_output]: ").strip() or "regex_output"
    out = OUTPUT_DIR / f"{name}.py"
    with open(out, 'w', encoding='utf-8') as f:
        f.write("# Auto-generated by RegexBuilder\n")
        f.write(f"# Generated: {datetime.now().isoformat()}\n")
        f.write(f"# Flags: {', '.join(flag_names) if flag_names else 'none'}\n\n")
        f.write("import re\n\n")
        f.write(f"pattern = r'''{pattern}'''\n")
        if flag_names:
            f.write("flags = " + " | ".join(f"re.{fn}" for fn in flag_names) + "\n")
        else:
            f.write("flags = 0\n")
        f.write("\nregex = re.compile(pattern, flags)\n\n")
        if groups_info:
            f.write("# Capture groups:\n")
            for name_g, idx in groups_info:
                f.write(f"#   #{idx}" + (f" ({name_g})" if name_g else "") + "\n")
            f.write("\n")
        f.write("# Test examples (SHOULD match):\n")
        for ex in match_examples:
            f.write(f"#   {ex}\n")
        if no_match_examples:
            f.write("\n# Test examples (SHOULD NOT match):\n")
            for ex in no_match_examples:
                f.write(f"#   {ex}\n")
    print(f"  [+] {tr('save_ok')}: {out}")


# ============================================================
#  РЕЖИМ 1: Мастер создания
# ============================================================
def mode_wizard():
    clr()
    hdr(tr("step1"))
    print(tr("step1_q"))

    match_examples = []
    idx = 1
    while True:
        s = _inp_allow_back(f"  #{idx}: ").strip()
        if not s:
            break
        match_examples.append(s)
        idx += 1
        print(f"  [+] {tr('step1_added')}: {len(match_examples)}")

    if not match_examples:
        print(f"[!] {tr('step1_need')}")
        _input(f"\n{tr('press')}: ")
        return

    # --- Шаг 2: исключения ---
    print("\n" + "=" * 64)
    print(f"  {tr('step2')}")
    print("=" * 64)
    print(tr("step2_q"))
    no_match_examples = []
    idx = 1
    while True:
        s = _inp_allow_back(f"  #{idx} {tr('step2_skip')}: ").strip()
        if not s:
            break
        no_match_examples.append(s)
        idx += 1
    if no_match_examples:
        print(f"  [+] {tr('step1_added')}: {len(no_match_examples)}")

    # --- Шаг 3: режим поиска ---
    print("\n" + "=" * 64)
    print(f"  {tr('step3')}")
    print("=" * 64)
    print("  " + tr("step3_1"))
    print("  " + tr("step3_2"))
    print("  " + tr("step3_3"))
    print("  " + tr("step3_4"))
    print("  " + tr("step3_5"))
    sc = _input(f"{tr('choice')} [1]: ").strip() or "1"
    if sc not in ("1", "2", "3", "4", "5"):
        sc = "1"

    # --- Шаг 4: флаги ---
    print("\n" + "=" * 64)
    print(f"  {tr('step4')}")
    print("=" * 64)
    case_sensitive = _input(f"  {tr('step4_case')} (y/n) [n]: ").strip().lower() == "y"
    multiline = _input(f"  {tr('step4_multiline')} (y/n) [n]: ").strip().lower() == "y"
    dotall = _input(f"  {tr('step4_dotall')} (y/n) [n]: ").strip().lower() == "y"
    verbose = _input(f"  {tr('step4_verbose')} (y/n) [n]: ").strip().lower() == "y"

    # --- Шаг 5: группы ---
    print("\n" + "=" * 64)
    print(f"  {tr('step5')}")
    print("=" * 64)
    n_groups = 0
    try:
        ng = _input(f"  {tr('step5_q')} [0]: ").strip() or "0"
        n_groups = int(ng) if ng.isdigit() else 0
    except Exception:
        n_groups = 0
    group_names = []
    for g in range(n_groups):
        gname = _inp_allow_empty(f"  {tr('step5_name')} #{g+1} (Enter — без имени): ").strip()
        group_names.append(gname)

    # --- Шаг 6: фильтры ---
    print("\n" + "=" * 64)
    print(f"  {tr('step6')}")
    print("=" * 64)
    use_filters = _input(f"  {tr('step6_q')} [n]: ").strip().lower() == "y"
    include_kw = []
    exclude_kw = []
    if use_filters:
        print(f"\n  {tr('step6_include')}:")
        while True:
            kw = _inp_allow_empty(f"    {tr('step6_kw')} (Enter — конец): ").strip()
            if not kw:
                break
            include_kw.append(kw)
        print(f"\n  {tr('step6_exclude')}:")
        while True:
            kw = _inp_allow_empty(f"    {tr('step6_kw')} (Enter — конец): ").strip()
            if not kw:
                break
            exclude_kw.append(kw)
        print(f"  [+] {tr('step6_done')}")

    # --- Сборка ---
    print("\n" + tr("build"))
    time.sleep(0.2)

    pattern = build_pattern_from_examples(match_examples) or re.escape(match_examples[0])

    # Обёртка групп
    groups_info = []
    if n_groups > 0:
        gname0 = group_names[0] if group_names else ""
        if gname0 and re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]*', gname0):
            pattern = f"(?P<{gname0}>{pattern})"
            groups_info.append((gname0, 1))
        else:
            pattern = f"({pattern})"
            groups_info.append(("", 1))

    # Режим поиска
    if sc == "2":
        pattern = r'\b' + pattern + r'\b'
    elif sc == "3":
        pattern = '^' + pattern
    elif sc == "4":
        pattern = pattern + '$'
    elif sc == "5":
        pattern = '^' + pattern + '$'

    # Исключения через negative lookahead
    for kw in exclude_kw:
        pattern = f"(?!.*{re.escape(kw)})" + pattern
    # Включения
    for kw in include_kw:
        pattern = f"(?=.*{re.escape(kw)})" + pattern

    # Флаги
    flags = 0
    flag_names = []
    if not case_sensitive:
        flags |= re.IGNORECASE
        flag_names.append("IGNORECASE")
    if multiline:
        flags |= re.MULTILINE
        flag_names.append("MULTILINE")
    if dotall:
        flags |= re.DOTALL
        flag_names.append("DOTALL")
    if verbose:
        flags |= re.VERBOSE
        flag_names.append("VERBOSE")

    # --- Результат ---
    clr()
    hdr(tr("result"))
    print(f"  {tr('regex')}:")
    print(f"    {pattern}")
    if flag_names:
        print(f"  {tr('flags')}: {', '.join(flag_names)}")
    if groups_info:
        print(f"  {tr('groups')}: {len(groups_info)}")

    compiled, results = test_pattern(pattern, flags, match_examples, no_match_examples)
    if compiled is None:
        _input(f"\n{tr('press')}: ")
        return

    ln()
    if results["ok"]:
        print(f"  [+] {tr('all_ok')}")
    else:
        print(f"  [!] {tr('some_fail')}")
        if results["missed"]:
            print(f"      Missed: {results['missed']}")
        if results["unexpected"]:
            print(f"      Unexpected: {results['unexpected']}")

    save_history(pattern, "|".join(flag_names), match_examples)
    save_result(pattern, flags, flag_names, match_examples, no_match_examples, groups_info)
    _input(f"\n{tr('press')}: ")


# ============================================================
#  РЕЖИМ 2: Объяснить
# ============================================================
def mode_explain():
    clr()
    hdr(tr("explain_q"))
    pattern = _inp_allow_empty(f"\n{tr('explain_q')}: ").strip()
    if not pattern:
        print(f"[!] {tr('explain_empty')}")
        _input(f"\n{tr('press')}: ")
        return
    try:
        re.compile(pattern)
    except re.error as e:
        print(f"[!] {tr('explain_err')}: {e}")
        _input(f"\n{tr('press')}: ")
        return
    print(f"\n  {tr('regex')}: {pattern}\n")
    ln()
    for tok, desc in explain_regex(pattern):
        print(f"    {tok:<22} {desc}")
    ln()
    _input(f"\n{tr('press')}: ")


# ============================================================
#  РЕЖИМ 3: Тест
# ============================================================
def mode_test():
    clr()
    hdr(tr("test_q"))
    pattern = _inp_allow_empty(f"\n{tr('explain_q')}: ").strip()
    if not pattern:
        print(f"[!] {tr('explain_empty')}")
        _input(f"\n{tr('press')}: ")
        return
    try:
        compiled = re.compile(pattern)
    except re.error as e:
        print(f"[!] {tr('explain_err')}: {e}")
        _input(f"\n{tr('press')}: ")
        return
    print(f"\n{tr('test_q')}")
    lines = []
    while True:
        s = _inp_allow_empty("  > ").strip()
        if not s:
            break
        lines.append(s)
    if not lines:
        _input(f"\n{tr('press')}: ")
        return
    text = "\n".join(lines)
    matches = list(compiled.finditer(text))
    print(f"\n  {tr('test_match')}: {len(matches)}")
    ln()
    for i, m in enumerate(matches, 1):
        print(f"  [{i}] '{m.group()}' @ {m.start()}-{m.end()}")
        for gi, g in enumerate(m.groups(), 1):
            print(f"       {tr('test_groups')} #{gi}: {g!r}")
        for name_g, val in (m.groupdict() or {}).items():
            print(f"       {tr('test_groups')} '{name_g}': {val!r}")
    _input(f"\n{tr('press')}: ")


# ============================================================
#  РЕЖИМ 4: Пресеты
# ============================================================
def mode_presets():
    clr()
    hdr(tr("preset_hdr"))
    for k, (name, pat, example) in PRESETS.items():
        print(f"  {k:>2}. {name:<16} {pat}")
    ln()
    ch = _input(f"{tr('choice')} [1]: ").strip() or "1"
    if ch not in PRESETS:
        print(f"[!] {tr('bad')}")
        _input(f"\n{tr('press')}: ")
        return
    name, pat, example = PRESETS[ch]
    print(f"\n  {name}: {pat}")
    print(f"  Пример: {example}")
    try:
        compiled = re.compile(pat)
    except re.error as e:
        print(f"[!] {tr('explain_err')}: {e}")
        _input(f"\n{tr('press')}: ")
        return
    m = compiled.search(example)
    if m:
        print(f"  [+] Совпадает: '{m.group()}'")
    else:
        print(f"  [!] Не совпадает с примером")
    if _input(f"\n  {tr('save')} [y]: ").strip().lower() != "n":
        fname = _inp_allow_empty(f"  {tr('save_name')} [{name.lower().replace(' ', '_')}]: ").strip() or name.lower().replace(' ', '_')
        out = OUTPUT_DIR / f"{fname}.py"
        with open(out, 'w', encoding='utf-8') as f:
            f.write(f"# {name}\nimport re\n\npattern = r'''{pat}'''\nflags = 0\nregex = re.compile(pattern, flags)\n")
        print(f"  [+] {tr('save_ok')}: {out}")
    _input(f"\n{tr('press')}: ")


# ============================================================
#  РЕЖИМ 5: Расширенный конструктор
# ============================================================
def mode_advanced():
    pattern = ""
    test_examples = []

    def show_pattern():
        print(f"\n  {tr('adv_current')}:")
        print(f"    {pattern if pattern else '(пусто)'}")

    def insert_component(comp):
        nonlocal pattern
        show_pattern()
        print(f"\n  {tr('adv_pos')}:")
        print("    " + tr("adv_pos_1"))
        print("    " + tr("adv_pos_2"))
        print("    " + tr("adv_pos_3"))
        pos = _input(f"  {tr('choice')} [1]: ").strip() or "1"
        if pos == "1":
            pattern = comp + pattern
        elif pos == "2":
            pattern = pattern + comp
        elif pos == "3":
            pattern = comp
        print(f"  [+] {tr('adv_added')}: {comp}")

    while True:
        clr()
        hdr(tr("advanced_hdr"))
        print("  " + tr("adv_1"))
        print("  " + tr("adv_2"))
        print("  " + tr("adv_3"))
        print("  " + tr("adv_4"))
        print("  " + tr("adv_5"))
        print("  " + tr("adv_6"))
        print("  " + tr("adv_7"))
        print("  " + tr("adv_8"))
        print("  " + tr("adv_9"))
        print("  " + tr("adv_10"))
        print("  " + tr("adv_11"))
        print("  " + tr("adv_12"))
        print("  " + tr("adv_q"))
        ln()
        print(f"  {tr('adv_current')}:")
        print(f"    {pattern if pattern else '(пусто)'}")
        ln()

        ch = _input(f"{tr('choice')}: ").strip().lower()
        if ch in ("q", "quit", "exit"):
            break

        if ch == "1":
            inner = _inp_allow_back("  (?= ... ) содержимое: ").strip()
            if inner:
                insert_component(f"(?={inner})")

        elif ch == "2":
            inner = _inp_allow_back("  (?! ... ) содержимое: ").strip()
            if inner:
                insert_component(f"(?!{inner})")

        elif ch == "3":
            inner = _inp_allow_back("  (?<= ... ) содержимое (должно быть фиксированной длины!): ").strip()
            if inner:
                insert_component(f"(?<={inner})")

        elif ch == "4":
            inner = _inp_allow_back("  (?<! ... ) содержимое (фиксированная длина!): ").strip()
            if inner:
                insert_component(f"(?<!{inner})")

        elif ch == "5":
            n = _inp_allow_back(f"  {tr('adv_group_n')} [1]: ").strip() or "1"
            yes_pat = _inp_allow_back("  Паттерн если группа сработала: ").strip()
            no_pat = _inp_allow_back("  Паттерн если НЕ сработала (Enter — пусто): ").strip()
            insert_component(f"(?({n}){yes_pat}|{no_pat})")

        elif ch == "6":
            n = _inp_allow_back(f"  {tr('adv_group_n')} [1]: ").strip() or "1"
            insert_component(f"\\{n}")

        elif ch == "7":
            name_g = _inp_allow_back(f"  {tr('adv_group_name')}: ").strip()
            if name_g and re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]*', name_g):
                insert_component(f"(?P={name_g})")
            else:
                print("[!] Имя должно начинаться с буквы/подчёркивания.")

        elif ch == "8":
            inner = _inp_allow_back("  (?> ... ) содержимое (без возврата назад): ").strip()
            if inner:
                insert_component(f"(?>")
                pattern = pattern  # placeholder
                # Просто вставляем целиком
                pattern = f"(?>{inner})" if not pattern else pattern

        elif ch == "9":
            name_g = _inp_allow_back(f"  {tr('adv_group_name')}: ").strip()
            inner = _inp_allow_back("  Содержимое группы: ").strip()
            if not inner:
                inner = ".*?"
            if name_g and re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]*', name_g):
                insert_component(f"(?P<{name_g}>{inner})")
            else:
                insert_component(f"({inner})")

        elif ch == "10":
            show_pattern()
            _input(f"\n{tr('press')}: ")

        elif ch == "11":
            if not pattern:
                print(f"[!] {tr('adv_empty')}")
                _input(f"\n{tr('press')}: ")
                continue
            try:
                compiled = re.compile(pattern)
            except re.error as e:
                print(f"[!] {tr('explain_err')}: {e}")
                _input(f"\n{tr('press')}: ")
                continue
            print(f"\n  {tr('regex')}: {pattern}")
            print(f"\n  {tr('test_q')}")
            lines = []
            while True:
                s = _inp_allow_empty("  > ").strip()
                if not s:
                    break
                lines.append(s)
            text = "\n".join(lines) if lines else " ".join(test_examples)
            matches = list(compiled.finditer(text)) if text else []
            print(f"\n  {tr('test_match')}: {len(matches)}")
            for i, m in enumerate(matches[:20], 1):
                print(f"  [{i}] '{m.group()}' @ {m.start()}-{m.end()}")
            if len(matches) > 20:
                print(f"  ... ещё {len(matches)-20}")
            if _input(f"\n  {tr('save')} [y]: ").strip().lower() != "n":
                fname = _inp_allow_empty(f"  {tr('save_name')} [advanced]: ").strip() or "advanced"
                out = OUTPUT_DIR / f"{fname}.py"
                with open(out, 'w', encoding='utf-8') as f:
                    f.write(f"import re\n\npattern = r'''{pattern}'''\nflags = 0\nregex = re.compile(pattern, flags)\n")
                print(f"  [+] {tr('save_ok')}: {out}")
                save_history(pattern, "advanced", lines or [pattern])
            _input(f"\n{tr('press')}: ")

        elif ch == "12":
            pattern = ""
            print("[+] Очищено.")
            time.sleep(0.5)

        else:
            print(f"[!] {tr('bad')}")
            time.sleep(0.7)


# ============================================================
#  РЕЖИМ 6: История
# ============================================================
def mode_history():
    clr()
    hdr(tr("hist_hdr"))
    hist = load_history()
    if not hist:
        print(f"  [!] {tr('hist_empty')}")
        _input(f"\n{tr('press')}: ")
        return
    for i, item in enumerate(reversed(hist[-20:]), 1):
        print(f"  {i:3}. [{item.get('time','')}] {item.get('pattern','')}")
        if item.get('flags'):
            print(f"       flags: {item.get('flags')}")
    print(f"\n  {tr('hist_hint')}")
    _input(f"\n{tr('press')}: ")


# ============================================================
#  РЕЖИМ 7: Из файла
# ============================================================
def mode_from_file():
    clr()
    hdr("Загрузка из файла")
    files = sorted([p for p in OUTPUT_DIR.glob("*.py") if p.is_file()])
    if not files:
        print("[!] В Output нет файлов.")
        _input(f"\n{tr('press')}: ")
        return
    for i, f in enumerate(files, 1):
        print(f"  {i}. {f.name}")
    try:
        idx = int(_input(f"{tr('choice')}: ").strip())
        if 1 <= idx <= len(files):
            content = files[idx - 1].read_text(encoding='utf-8')
            m = re.search(r"pattern\s*=\s*r?'''(.+?)'''", content, re.DOTALL)
            if m:
                pat = m.group(1)
                print(f"\n  {tr('regex')}: {pat}")
                try:
                    compiled = re.compile(pat)
                    print("  [+] Валиден.")
                except re.error as e:
                    print(f"  [!] {e}")
    except Exception:
        pass
    _input(f"\n{tr('press')}: ")


# ============================================================
#  Главное меню
# ============================================================
def main():
    ensure_dirs()
    while True:
        clr()
        hdr("RegexBuilder")
        print("  " + tr("m1"))
        print("  " + tr("m2"))
        print("  " + tr("m3"))
        print("  " + tr("m4"))
        print("  " + tr("m5"))
        print("  " + tr("m6"))
        print("  " + tr("m7"))
        print("  " + tr("mq"))
        ln()
        ch = _input(f"{tr('choice')} [1]: ").strip() or "1"
        if ch in ("q", "quit", "exit"):
            print("[+] " + tr("exit"))
            break
        if ch == "1":
            mode_wizard()
        elif ch == "2":
            mode_explain()
        elif ch == "3":
            mode_test()
        elif ch == "4":
            mode_presets()
        elif ch == "5":
            mode_advanced()
        elif ch == "6":
            mode_history()
        elif ch == "7":
            mode_from_file()
        else:
            print(f"[!] {tr('bad')}")
            time.sleep(1)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n[+] " + tr("exit"))
        sys.exit(0)
PYEOF

echo "[*] Настройка DNS перед запуском..."
echo "nameserver 8.8.8.8" > /etc/resolv.conf
echo "nameserver 8.8.4.4" >> /etc/resolv.conf
echo "nameserver 94.140.14.14" >> /etc/resolv.conf
echo "nameserver 94.140.15.15" >> /etc/resolv.conf
echo "nameserver 1.1.1.1" >> /etc/resolv.conf

echo "[*] Запуск RegexBuilder..."
python3 ~/RegexBuilder/RegexBuilder.py
