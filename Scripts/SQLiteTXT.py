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

cat << 'EOF' > ~/db_to_text.py
#!/usr/bin/env python3
import os
import sqlite3
import csv
import sys
from pathlib import Path

HOME = Path.home()
INPUT_DIR = HOME / "DBLog"
OUTPUT_DIR = HOME / "TextLog"

def ensure_dirs():
    INPUT_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

def get_db_files():
    return [f for f in INPUT_DIR.glob("*.db") if f.is_file()]

def export_table_to_text(conn, table_name, out_file):
    cursor = conn.cursor()
    cursor.execute(f"PRAGMA table_info({table_name})")
    columns = [row[1] for row in cursor.fetchall()]
    if not columns:
        return
    cursor.execute(f"SELECT * FROM {table_name}")
    writer = csv.writer(out_file, delimiter='\t', quoting=csv.QUOTE_MINIMAL)
    writer.writerow(columns)
    for row in cursor.fetchall():
        writer.writerow(row)

def export_database(db_path, output_dir):
    base_name = db_path.stem
    out_path = output_dir / f"{base_name}.txt"
    try:
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
        tables = [row[0] for row in cursor.fetchall()]
        if not tables:
            with open(out_path, 'w', encoding='utf-8') as f:
                f.write(f"База данных {db_path.name} не содержит пользовательских таблиц.\n")
            return
        with open(out_path, 'w', encoding='utf-8', newline='') as f:
            for table in tables:
                f.write(f"\n=== Таблица: {table} ===\n")
                export_table_to_text(conn, table, f)
        print(f"[+] Обработана {db_path.name} -> {out_path.name} (таблиц: {len(tables)})")
        conn.close()
    except sqlite3.Error as e:
        print(f"[!] Ошибка при обработке {db_path.name}: {e}")

def main():
    ensure_dirs()
    db_files = get_db_files()
    if not db_files:
        print("[!] В папке ~/DBLog нет .db файлов.")
        print("[*] Поместите туда ваши базы данных и запустите скрипт снова.")
        sys.exit(1)
    print(f"[*] Найдено файлов: {len(db_files)}")
    for db_file in db_files:
        export_database(db_file, OUTPUT_DIR)
    print("[+] Все базы данных обработаны. Результаты в ~/TextLog")

if __name__ == "__main__":
    main()
EOF

echo "[*] Запуск конвертера SQLite -> текст..."
python3 ~/db_to_text.py

echo "[*] Готово! Текстовые файлы находятся в ~/TextLog"
