#!/bin/sh
clear
echo "[*] Настройка DNS..."
echo "nameserver 8.8.8.8" > /etc/resolv.conf
echo "nameserver 8.8.4.4" >> /etc/resolv.conf
echo "nameserver 94.140.14.14" >> /etc/resolv.conf
echo "nameserver 94.140.15.15" >> /etc/resolv.conf
echo "nameserver 1.1.1.1" >> /etc/resolv.conf
echo "[*] Обновление системы и установка зависимостей..."
apk update
apk upgrade
apk add --no-cache python3 sqlite curl wget bash
echo "[*] Создание папок..."
mkdir -p ~/DBLog
mkdir -p ~/TextLog

cat << 'EOF' > ~/SQLiteTXT.py
#!/usr/bin/env python3
import os
import sys
import re
import sqlite3
import csv
import shutil
from pathlib import Path
from datetime import datetime
from collections import defaultdict

ROOT = Path.home()
INPUT_DIR = ROOT / "DBLog"
OUTPUT_DIR = ROOT / "TextLog"
CONFIG_FILE = ROOT / ".sqlitetxt_config"
SEPARATOR = "\t"
SEP_NAME = "tab"

def load_config():
    global SEPARATOR, SEP_NAME
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, 'r') as f:
                data = f.read().strip()
                if data in ("tab", "comma", "semicolon"):
                    SEP_NAME = data
                    if data == "tab":
                        SEPARATOR = "\t"
                    elif data == "comma":
                        SEPARATOR = ","
                    elif data == "semicolon":
                        SEPARATOR = ";"
        except:
            pass

def save_config():
    with open(CONFIG_FILE, 'w') as f:
        f.write(SEP_NAME)

load_config()

def sanitize_filename(name):
    if not name:
        return name
    allowed = re.compile(r'[^a-zA-Z0-9_.\-]')
    clean = allowed.sub('_', name)
    clean = clean.strip('_')
    if not clean:
        clean = 'file'
    return clean

def clean_str(s):
    if not s:
        return s
    return ''.join(ch for ch in s if ord(ch) >= 32 or ch in '\n\r\t')

def now_stamp():
    return datetime.now().strftime("%Y%m%d_%H%M%S")

def die(message):
    print(f"[!] {message}")
    sys.exit(1)

def list_input_files():
    if not INPUT_DIR.exists():
        die(f"Папка {INPUT_DIR} не найдена")
    files = [p for p in INPUT_DIR.iterdir() if p.is_file() and not p.name.startswith(".") and p.suffix.lower() == ".db"]
    files.sort(key=lambda p: p.name.lower())
    return files

def print_files(files, title="[+] Найденные .db файлы:"):
    print(f"\n{title}")
    for i, path in enumerate(files, 1):
        size_mb = path.stat().st_size / 1024 / 1024
        print(f"{i}. {path.name} ({size_mb:.2f} MB)")

def parse_selection(text, max_index):
    text = text.strip().lower()
    if text in {"all", "a"}:
        return list(range(1, max_index + 1))
    result = []
    parts = [p.strip() for p in text.split(",") if p.strip()]
    for part in parts:
        if "-" in part:
            left, right = part.split("-", 1)
            if not left.isdigit() or not right.isdigit():
                raise ValueError
            a = int(left)
            b = int(right)
            if a > b:
                a, b = b, a
            for n in range(a, b + 1):
                if 1 <= n <= max_index and n not in result:
                    result.append(n)
        else:
            if not part.isdigit():
                raise ValueError
            n = int(part)
            if 1 <= n <= max_index and n not in result:
                result.append(n)
    if not result:
        raise ValueError
    return result

def select_files(files, allow_multiple=True, prompt="Выберите файлы"):
    while True:
        print_files(files)
        if allow_multiple:
            print(f"\n[?] {prompt} (можно несколько, например 1,3-4 или all)")
        else:
            print(f"\n[?] {prompt} (введите номер)")
        choice = input("[?] Ваш выбор: ").strip()
        if choice.lower() in ("b", "back"):
            return None
        try:
            indices = parse_selection(choice, len(files))
            if not allow_multiple and len(indices) != 1:
                print("[!] Выберите ровно один файл")
                continue
            selected = [files[i-1] for i in indices]
            return selected
        except:
            print("[!] Неверный выбор")

def get_user_tables(conn):
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
    all_tables = [row[0] for row in cursor.fetchall()]
    skip = ('logging_segments', 'logging_segdir', 'logging_content')
    tables = [t for t in all_tables if t not in skip]
    return tables

def get_table_info(conn, table):
    cursor = conn.cursor()
    cursor.execute(f"PRAGMA table_info({table})")
    columns = [row[1] for row in cursor.fetchall()]
    cursor.execute(f"SELECT COUNT(*) FROM {table}")
    count = cursor.fetchone()[0]
    return columns, count

def row_matches_filter(row, columns, keywords):
    if not keywords:
        return True
    url_idx = columns.index('url') if 'url' in columns else None
    if url_idx is not None:
        val = str(row[url_idx]) if row[url_idx] is not None else ""
        for kw in keywords:
            if kw.lower() in val.lower():
                return True
        return False
    else:
        for col, val in zip(columns, row):
            if val is not None:
                s = str(val)
                for kw in keywords:
                    if kw.lower() in s.lower():
                        return True
        return False

def export_table_human(conn, table, out_file, dedupe=False, sort_by_policy=False, keywords=None):
    if keywords is None:
        keywords = []
    cursor = conn.cursor()
    cursor.execute(f"PRAGMA table_info({table})")
    columns = [row[1] for row in cursor.fetchall()]
    if not columns:
        return 0
    cursor.execute(f"SELECT * FROM {table}")
    rows = cursor.fetchall()

    if keywords:
        rows = [r for r in rows if row_matches_filter(r, columns, keywords)]

    if not rows:
        out_file.write("\n(нет записей, соответствующих фильтру)\n")
        return 0

    if sort_by_policy and table == "logging":
        type_idx = columns.index('type') if 'type' in columns else None
        if type_idx is not None:
            policy_order = {'DIRECT': 0, 'PROXY': 1, 'REJECT': 2}
            rows.sort(key=lambda r: policy_order.get(r[type_idx] if type_idx < len(r) else '', 3))

    if dedupe and table == "logging":
        url_idx = columns.index('url') if 'url' in columns else None
        if url_idx is not None:
            groups = defaultdict(list)
            for row in rows:
                groups[row[url_idx]].append(row)
            grouped_rows = []
            for url, group in groups.items():
                first = group[0]
                count = len(group)
                row_list = list(first)
                row_list.append(count)
                grouped_rows.append(row_list)
            columns = columns + ['count']
            rows = grouped_rows
        else:
            dedupe = False

    if sort_by_policy and table == "logging" and 'type' in columns:
        type_idx = columns.index('type')
        policy_groups = {'DIRECT': [], 'PROXY': [], 'REJECT': []}
        other = []
        for row in rows:
            val = row[type_idx] if type_idx < len(row) else ''
            if val in policy_groups:
                policy_groups[val].append(row)
            else:
                other.append(row)
        total_written = 0
        for policy in ('DIRECT', 'PROXY', 'REJECT'):
            if policy_groups[policy]:
                out_file.write(f"\n--- {policy} ---\n")
                for row in policy_groups[policy]:
                    out_file.write("\n")
                    for col, val in zip(columns, row):
                        if val is not None:
                            out_file.write(f"{col}: {val}\n")
                        else:
                            out_file.write(f"{col}: (null)\n")
                    total_written += 1
        if other:
            out_file.write("\n--- OTHER ---\n")
            for row in other:
                out_file.write("\n")
                for col, val in zip(columns, row):
                    if val is not None:
                        out_file.write(f"{col}: {val}\n")
                    else:
                        out_file.write(f"{col}: (null)\n")
                total_written += 1
        return total_written
    else:
        for row in rows:
            out_file.write("\n")
            for col, val in zip(columns, row):
                if val is not None:
                    out_file.write(f"{col}: {val}\n")
                else:
                    out_file.write(f"{col}: (null)\n")
        return len(rows)

def extract_mode(selected_files, show_schema, show_stats, keywords, dedupe, sort_by_policy):
    total_files = len(selected_files)
    created = []
    for idx, db_path in enumerate(selected_files, 1):
        print(f"\r[*] Обработка {idx}/{total_files}: {db_path.name}          ", end="")
        base_name = db_path.stem
        timestamp = now_stamp()
        out_path = OUTPUT_DIR / f"{base_name}_{timestamp}.txt"
        try:
            conn = sqlite3.connect(str(db_path))
            tables = get_user_tables(conn)
            if not tables:
                with open(out_path, 'w', encoding='utf-8') as f:
                    f.write(f"База данных {db_path.name} не содержит таблиц.\n")
                conn.close()
                created.append(out_path)
                continue
            with open(out_path, 'w', encoding='utf-8') as f:
                if show_schema:
                    f.write(f"=== Схема базы данных: {db_path.name} ===\n")
                    for table in tables:
                        columns, total_count = get_table_info(conn, table)
                        f.write(f"\nТаблица: {table}\n")
                        f.write(f"Колонки: {', '.join(columns)}\n")
                        if show_stats:
                            f.write(f"Общее количество записей: {total_count}\n")
                    f.write("\n" + "="*40 + "\n\n")
                total_exported = 0
                for table in tables:
                    f.write(f"\n=== Таблица: {table} ===\n")
                    if keywords:
                        f.write(f"Фильтр по ключевым словам: {', '.join(keywords)}\n")
                    if dedupe:
                        f.write("Дедупликация по URL включена (группировка с подсчётом)\n")
                    if sort_by_policy:
                        f.write("Сортировка по политике: DIRECT → PROXY → REJECT\n")
                    count = export_table_human(conn, table, f, dedupe, sort_by_policy, keywords)
                    total_exported += count
                if show_stats:
                    f.write(f"\n--- Итого записей после фильтрации/дедупликации: {total_exported} ---\n")
            conn.close()
            created.append(out_path)
            print(f"\r[+] Обработана {db_path.name} -> {out_path.name} (таблиц: {len(tables)})          ")
        except sqlite3.Error as e:
            print(f"\r[!] Ошибка при обработке {db_path.name}: {e}          ")
    return created

def ask_options_extract():
    print("\n=== Настройки экспорта (введите строку из 0/1 длиной 5, Enter = 11000) ===")
    print("1. Показывать схему таблиц (колонки)")
    print("2. Показывать количество записей (общее и итоговое)")
    print("3. Фильтровать записи по ключевым словам (в поле URL) (если 1, затем введите слова)")
    print("4. Удалять дубликаты по URL (группировать, показывать количество)")
    print("5. Сортировать по политике: DIRECT → PROXY → REJECT")
    default = "11000"
    while True:
        s = input("[?] Ваш выбор: ").strip()
        if s == "":
            s = default
        if len(s) != len(default):
            print(f"[!] Ожидается {len(default)} символов")
            continue
        if not all(c in "01" for c in s):
            print("[!] Используйте только 0 и 1")
            continue
        bits = [c == "1" for c in s]
        keywords = []
        if bits[2]:
            kw = input("[?] Введите ключевые слова для фильтрации (через запятую): ").strip()
            if kw:
                keywords = [x.strip() for x in kw.split(",") if x.strip()]
        return bits, keywords

def rename_mode(files):
    while True:
        print_files(files)
        print("\n[?] Переименовать один файл (1) или группу с общим префиксом (2)? [1]: ", end="")
        choice = input().strip()
        if choice == "":
            choice = "1"
        if choice == "1":
            selected = select_files(files, allow_multiple=False, prompt="Выберите файл для переименования")
            if selected is None:
                continue
            path = selected[0]
            while True:
                new_name = input(f"[?] Новое имя для {path.name}: ").strip()
                new_name = clean_str(new_name)
                new_name = sanitize_filename(new_name)
                if not new_name:
                    print("[!] Имя не может быть пустым")
                    continue
                if new_name.lower() in ("b", "back"):
                    break
                if not new_name.endswith(".db"):
                    new_name += ".db"
                new_path = path.parent / new_name
                if new_path.exists():
                    print("[!] Файл с таким именем уже существует")
                    continue
                confirm = input(f"[?] Переименовать {path.name} в {new_name}? (y/n/back) [n]: ").strip().lower()
                if confirm == "":
                    confirm = "n"
                if confirm == "y":
                    path.rename(new_path)
                    print(f"[+] Переименован в {new_name}")
                    files = list_input_files()
                    print_files(files)
                    break
                elif confirm == "back":
                    break
                else:
                    print("[!] Введите y, n или back")
        elif choice == "2":
            prefix = input("[?] Введите префикс для группы: ").strip()
            prefix = clean_str(prefix)
            prefix = sanitize_filename(prefix)
            if not prefix:
                print("[!] Префикс не может быть пустым")
                continue
            apply_all = input("[?] Применить ко всем файлам? (y/n) [y]: ").strip().lower()
            if apply_all == "":
                apply_all = "y"
            if apply_all == "y":
                selected_files = files
            else:
                selected_files = select_files(files, allow_multiple=True, prompt="Выберите файлы для переименования")
                if selected_files is None:
                    continue
            if not selected_files:
                print("[!] Нет файлов для переименования")
                continue
            selected_files_sorted = sorted(selected_files, key=lambda p: p.name)
            conflicts = []
            for i, path in enumerate(selected_files_sorted, 1):
                ext = path.suffix
                new_name = f"{prefix}-{i}{ext}"
                new_path = path.parent / new_name
                if new_path.exists() and new_path != path:
                    conflicts.append((path, new_path))
            if conflicts:
                print("[!] Следующие файлы будут перезаписаны:")
                for old, new in conflicts:
                    print(f"  {old.name} -> {new.name}")
                confirm = input("[?] Продолжить? (y/n) [n]: ").strip().lower()
                if confirm != "y":
                    print("[!] Отменено")
                    continue
            for i, path in enumerate(selected_files_sorted, 1):
                ext = path.suffix
                new_name = f"{prefix}-{i}{ext}"
                new_path = path.parent / new_name
                path.rename(new_path)
                print(f"[+] {path.name} -> {new_name}")
            files = list_input_files()
            print_files(files)
        else:
            print("[!] Неверный выбор")
            continue
        cont = input("[?] Продолжить переименование? (y/n) [n]: ").strip().lower()
        if cont != "y":
            break

def rename_single_output_file(file_path):
    while True:
        new_name = input(f"[?] Новое имя для {file_path.name}: ").strip()
        new_name = clean_str(new_name)
        new_name = sanitize_filename(new_name)
        if not new_name:
            print("[!] Имя не может быть пустым")
            continue
        if new_name.lower() in ("b", "back"):
            return None
        if not new_name.endswith(".txt"):
            new_name += ".txt"
        new_path = file_path.parent / new_name
        if new_path.exists():
            print("[!] Файл с таким именем уже существует")
            continue
        confirm = input(f"[?] Переименовать {file_path.name} в {new_name}? (y/n) [n]: ").strip().lower()
        if confirm == "":
            confirm = "n"
        if confirm == "y":
            file_path.rename(new_path)
            print(f"[+] Переименован в {new_name}")
            return new_path
        elif confirm == "back":
            return None
        else:
            print("[!] Введите y, n или back")

def change_separator():
    global SEPARATOR, SEP_NAME
    print(f"\n[+] Текущий разделитель: '{SEP_NAME}'")
    print("[1] tab")
    print("[2] comma (,)")
    print("[3] semicolon (;)")
    choice = input("[?] Выберите номер [1]: ").strip()
    if choice == "":
        choice = "1"
    if choice == "1":
        SEP_NAME = "tab"
        SEPARATOR = "\t"
    elif choice == "2":
        SEP_NAME = "comma"
        SEPARATOR = ","
    elif choice == "3":
        SEP_NAME = "semicolon"
        SEPARATOR = ";"
    else:
        print("[!] Неверный выбор")
        return
    save_config()
    print(f"[+] Разделитель изменён на '{SEP_NAME}'")

def clean_broken_files():
    print("\n=== Очистка повреждённых файлов ===")
    print("[1] Проверить все .db файлы и удалить битые")
    print("[2] Очистить папку DBLog (удалить все файлы)")
    print("[3] Очистить папку TextLog (удалить все файлы)")
    print("[4] Очистить обе папки")
    print("[5] Назад")
    choice = input("[?] Ваш выбор [5]: ").strip()
    if choice == "":
        choice = "5"
    if choice == "5":
        return
    if choice == "1":
        files = list_input_files()
        if not files:
            print("[!] Нет .db файлов для проверки")
            return
        print("[*] Проверка целостности баз данных...")
        for path in files:
            try:
                conn = sqlite3.connect(str(path))
                cursor = conn.cursor()
                cursor.execute("SELECT 1")
                conn.close()
                print(f"[+] {path.name} - OK")
            except sqlite3.Error:
                print(f"[!] {path.name} - повреждён, удаляем...")
                try:
                    path.unlink()
                except Exception as e:
                    print(f"[!] Не удалось удалить {path.name}: {e}")
        print("[+] Проверка завершена")
        return
    dirs = []
    if choice in ("2", "4"):
        dirs.append(INPUT_DIR)
    if choice in ("3", "4"):
        dirs.append(OUTPUT_DIR)
    for d in dirs:
        if not d.exists():
            print(f"[!] Папка {d} не существует")
            continue
        print(f"[?] Удалить всё содержимое {d}? (y/n) [n]: ", end="")
        ans = input().strip().lower()
        if ans == "":
            ans = "n"
        if ans == "y":
            for item in d.iterdir():
                try:
                    if item.is_dir():
                        shutil.rmtree(item)
                    else:
                        item.unlink()
                except Exception as e:
                    print(f"[!] Ошибка удаления {item}: {e}")
            print(f"[+] Папка {d} очищена")
        else:
            print(f"[!] Пропущено {d}")

def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    while True:
        files = list_input_files()
        while not files:
            print("\n[!] В папке ~/DBLog нет .db файлов.")
            print("[*] Поместите файлы в ~/DBLog и нажмите Enter для продолжения")
            print("[*] Или введите 'exit' для выхода")
            cmd = input().strip().lower()
            if cmd == "exit":
                print("[+] Выход.")
                return
            files = list_input_files()
        print("\n[1] Export")
        print("[2] Rename input files")
        print("[3] Change output separator")
        print("[4] Clean broken files")
        print("[5] Exit")
        mode = input("\n[?] Выберите режим (1/2/3/4/5) [1]: ").strip()
        if mode == "":
            mode = "1"
        if mode == "5":
            print("[+] Выход.")
            break
        if mode == "4":
            clean_broken_files()
            continue
        if mode == "3":
            change_separator()
            continue
        if mode == "2":
            rename_mode(files)
            continue
        if mode == "1":
            selected = select_files(files, allow_multiple=True, prompt="Выберите файлы для экспорта")
            if selected is None:
                continue
            opts, keywords = ask_options_extract()
            show_schema, show_stats, _, dedupe, sort_by_policy = opts
            created = extract_mode(selected, show_schema, show_stats, keywords, dedupe, sort_by_policy)
            print("\n[+] Экспорт завершён. Файлы сохранены в ~/TextLog")
            if len(created) == 1:
                ans = input("[?] Переименовать созданный файл? (y/n) [n]: ").strip().lower()
                if ans == "y":
                    rename_single_output_file(created[0])
        else:
            print("[!] Неверный выбор")
            continue
        print("\n[+] Готово! Можете продолжить или выйти.")
        input("[*] Нажмите Enter для продолжения...")

if __name__ == "__main__":
    main()
EOF

echo "[*] Запуск SQLiteTXT.py..."
python3 ~/SQLiteTXT.py
echo "[*] Готово! Текстовые файлы находятся в ~/TextLog"
