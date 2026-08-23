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
apk add --no-cache python3 py3-pip curl wget bash

echo "[*] Создание папок..."
mkdir -p ~/SRLog
mkdir -p ~/SpyLog

cat << 'EOF' > ~/Spylog.py
import json
import re
import sys
import os
import shutil
from pathlib import Path
from datetime import datetime
from collections import defaultdict
from urllib.parse import unquote, urlparse
import base64
import html
import codecs

ROOT = Path.home()
INPUT_DIR = ROOT / "SRLog"
OUTPUT_DIR = ROOT / "SpyLog"
ANSI_RE = re.compile(rb"\x1b\[[0-9;]*[A-Za-z]")
SPY_PATTERN = b"[Spylog]"
KNOWN_SECTION_PREFIXES = (
    "| < Заголовки ответа:",
    "| TYPE:",
    "| SIZE ",
    "| < Body:",
    "| URL:",
    "| [REQ/RES]",
    "| [REQ]",
    "| [RES]",
)
METHODS = {"GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS", "TRACE", "CONNECT"}
CONFIG_FILE = ROOT / ".spylog_config"

def load_config():
    global SPY_PATTERN
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, 'rb') as f:
                SPY_PATTERN = f.read().strip()
        except:
            pass

def save_config():
    with open(CONFIG_FILE, 'w') as f:
        f.write(SPY_PATTERN.decode('utf-8', errors='ignore'))

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

def strip_ansi_bytes(data):
    return ANSI_RE.sub(b"", data)

def best_decode_block(data):
    encodings = ['utf-8', 'cp1251', 'koi8-r', 'cp866', 'mac-cyrillic', 'iso-8859-5', 'latin-1']
    best_text = None
    best_score = -1
    for enc in encodings:
        try:
            text = data.decode(enc)
        except:
            continue
        score = 0
        cyrillic = sum(1 for c in text if 0x0400 <= ord(c) <= 0x04FF)
        score += cyrillic * 5
        rep = text.count('\ufffd')
        score -= rep * 10
        if cyrillic > 0 and score > best_score:
            best_score = score
            best_text = text
    if best_text is None:
        best_text = data.decode('utf-8', errors='replace')
    return best_text

def decode_unicode_escapes(text):
    def repl(m):
        return chr(int(m.group(1), 16))
    return re.sub(r'\\u([0-9a-fA-F]{4})', repl, text)

def decode_percent(text):
    try:
        return unquote(text, encoding='utf-8', errors='replace')
    except:
        return text

def universal_decode_text(text):
    text = html.unescape(text)
    text = decode_percent(text)
    text = decode_unicode_escapes(text)
    try:
        text = codecs.decode(text, 'quopri')
    except:
        pass
    return text

def extract_spy_blocks_bytes(raw):
    lines = raw.split(b'\n')
    blocks = []
    current = []
    active = False
    for line in lines:
        if not active:
            if SPY_PATTERN in line:
                active = True
                current = [line]
            continue
        current.append(line)
        if line.strip() == b"+---":
            blocks.append(b"\n".join(current))
            current = []
            active = False
    if active and current:
        blocks.append(b"\n".join(current))
    return blocks

def parse_header(block_text):
    first_line = block_text.split("\n", 1)[0]
    m = re.search(r"\[Spylog\].*?\[([A-Z]+)\]\s+([A-Z]+)\s+(https?://\S+)", first_line)
    if m:
        method = m.group(2)
        url = m.group(3).rstrip("]")
        return method, url
    m = re.search(r"(GET|POST|PUT|DELETE|PATCH|HEAD|OPTIONS|TRACE|CONNECT)\s+(https?://\S+)", block_text)
    if m:
        return m.group(1), m.group(2).rstrip("]")
    return None, None

def collect_section(lines, marker, stop_on_pipe_section):
    idx = -1
    for i, line in enumerate(lines):
        if marker in line:
            idx = i
            break
    if idx < 0:
        return ""
    first = lines[idx].split(marker, 1)[1]
    collected = [first]
    for line in lines[idx + 1:]:
        if line.strip() == "+---":
            break
        if stop_on_pipe_section and line.startswith("|") and any(line.startswith(prefix) for prefix in KNOWN_SECTION_PREFIXES):
            break
        collected.append(line)
    return "\n".join(collected).strip("\n")

def parse_record_from_text(block_text, source_name, decode=False, sig_level=1):
    if decode:
        block_text = universal_decode_text(block_text)
    method, url = parse_header(block_text)
    lines = block_text.split('\n')
    request_body = collect_section(lines, "| > Body:", True)
    response_body = collect_section(lines, "| < Body:", False)
    if decode:
        request_body = universal_decode_text(request_body)
        response_body = universal_decode_text(response_body)
    norm_url = url if url else "UNKNOWN"
    if sig_level == 2:
        parsed = urlparse(norm_url)
        norm_url = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
    elif sig_level == 3:
        parsed = urlparse(norm_url)
        norm_url = parsed.path if parsed.path else "/"
    elif sig_level == 4:
        norm_url = ""
    sig = f"{method or 'ANY'} {norm_url}"
    return {
        "source": source_name,
        "raw": block_text,
        "method": method or "",
        "url": url or "",
        "signature": sig,
        "request_body": request_body,
        "response_body": response_body,
        "request_json": None,
        "response_json": None,
    }

def load_log_and_extract_blocks(path):
    raw = path.read_bytes()
    raw = strip_ansi_bytes(raw)
    blocks_bytes = extract_spy_blocks_bytes(raw)
    blocks_text = []
    for bb in blocks_bytes:
        text = best_decode_block(bb)
        blocks_text.append(text)
    return blocks_text

def list_input_files():
    if not INPUT_DIR.exists():
        die(f"Папка {INPUT_DIR} не найдена")
    files = [p for p in INPUT_DIR.iterdir() if p.is_file() and not p.name.startswith(".")]
    files.sort(key=lambda p: p.name.lower())
    return files

def print_files(files):
    print("\n[+] Найденные файлы:")
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

def ask_files(files, compare=False):
    while True:
        print_files(files)
        if compare:
            selected = select_files(files, allow_multiple=True, prompt="Выберите файлы для сравнения (минимум 2)")
        else:
            selected = select_files(files, allow_multiple=True, prompt="Выберите один или несколько файлов")
        if selected is None:
            return None
        return selected

def ask_groups(files):
    while True:
        print("\n[?] Сколько групп создать? (минимум 2): ", end="")
        try:
            num = int(input().strip())
            if num >= 2:
                break
            print("[!] Должно быть не меньше 2")
        except:
            print("[!] Введите число")
    groups = []
    for g in range(1, num+1):
        print(f"\n=== Группа {g} ===")
        print_files(files)
        selected = select_files(files, allow_multiple=True, prompt=f"Выберите файлы для группы {g}")
        if selected is None:
            return None
        groups.append(selected)
    return groups

def dedupe_exact(blocks, keep_duplicates):
    if keep_duplicates:
        return blocks
    seen = set()
    out = []
    for block in blocks:
        lines = block.split("\n")
        if len(lines) >= 2 and lines[-1].strip() == "+---":
            body = "\n".join(lines[1:-1])
        else:
            body = "\n".join(lines[1:]) if len(lines) > 1 else ""
        key = body.replace("\r\n", "\n").strip("\n")
        if key not in seen:
            seen.add(key)
            out.append(block)
    return out

def save_text(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")

def move_keyword_blocks(blocks, keywords):
    if not keywords:
        return blocks
    matched = []
    other = []
    for block in blocks:
        lower = block.lower()
        if any(kw.lower() in lower for kw in keywords):
            matched.append(block)
        else:
            other.append(block)
    return matched + other

def ask_options(mode):
    if mode == "extract":
        print("\n=== Настройки вывода (введите строку из 0/1 длиной 5, Enter = 11110) ===")
        print("1. Показывать список уникальных URL")
        print("2. Декодировать закодированные строки в телах")
        print("3. Показывать количество блоков по каждому файлу")
        print("4. Отделить логи с ключевыми словами (если 1, затем введите слова)")
        print("5. Показывать дубликаты (0 - удалять, 1 - оставлять)")
        default = "11110"
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
            if bits[3]:
                kw = input("[?] Введите ключевые слова (через запятую): ").strip()
                if kw:
                    keywords = [x.strip() for x in kw.split(",") if x.strip()]
            return bits, keywords
    else:
        print("\n=== Настройки вывода (введите строку из 0/1 длиной 6, Enter = 111100) ===")
        print("1. Показывать статистику URL")
        print("2. Декодировать строки в телах перед сравнением")
        print("3. Показывать детальные различия полей")
        print("4. Включать полные блоки в отчёт")
        print("5. Отделить логи с ключевыми словами (если 1, затем введите слова)")
        print("6. Показывать дубликаты (0 - удалять, 1 - оставлять)")
        default = "111100"
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
            if bits[4]:
                kw = input("[?] Введите ключевые слова (через запятую): ").strip()
                if kw:
                    keywords = [x.strip() for x in kw.split(",") if x.strip()]
            print("\n[?] Как сравнивать сигнатуры (метод+URL)?")
            print("1 - полный URL (включая параметры)")
            print("2 - путь без параметров (схема+хост+путь)")
            print("3 - только метод + путь (без хоста)")
            print("4 - только метод")
            sig_choice = input("[?] Ваш выбор [1]: ").strip()
            if sig_choice not in ("1","2","3","4"):
                sig_choice = "1"
            return bits, keywords, int(sig_choice)

def build_records_from_blocks(blocks, source_name, decode=False, sig_level=1):
    records = []
    for block in blocks:
        rec = parse_record_from_text(block, source_name, decode, sig_level)
        records.append(rec)
    return records

def extract_mode(selected_files, show_urls, decode, show_stats, keywords, keep_duplicates):
    all_blocks = []
    per_file_counts = []
    total_found = 0
    total_files = len(selected_files)
    for idx, path in enumerate(selected_files, 1):
        print(f"\r[*] Обработка файла {idx}/{total_files}: {path.name}          ", end="")
        blocks = load_log_and_extract_blocks(path)
        if decode:
            blocks = [universal_decode_text(b) for b in blocks]
        total_found += len(blocks)
        per_file_counts.append((path.name, len(blocks)))
        all_blocks.extend(blocks)
    print("\r[*] Дедупликация (по содержимому)...          ", end="")
    all_blocks = dedupe_exact(all_blocks, keep_duplicates)
    all_blocks = move_keyword_blocks(all_blocks, keywords)
    print("\r[+] Готово, сохраняем...          ")
    stamp = now_stamp()
    out_path = OUTPUT_DIR / f"Spylog_extract_{stamp}.txt"
    lines = []
    lines.append(f"Source files: {', '.join(p.name for p in selected_files)}")
    lines.append(f"Blocks before dedupe: {total_found}")
    lines.append(f"Blocks after dedupe: {len(all_blocks)}")
    lines.append("")
    if show_urls:
        urls = set()
        for block in all_blocks:
            method, url = parse_header(block)
            if url:
                urls.add(url)
        lines.append("=== Unique URLs found ===")
        lines.extend(sorted(urls))
        lines.append("")
    if show_stats:
        lines.append("=== Per-file block counts ===")
        for name, count in per_file_counts:
            lines.append(f"{name}: {count}")
        lines.append("")
    if keywords:
        lines.append("=== Blocks with keywords (moved to top) ===")
        lines.append(f"Keywords: {', '.join(keywords)}")
        lines.append("")
    lines.append("=== Extracted blocks ===")
    lines.append("")
    content = "\n\n".join(all_blocks)
    full_text = "\n".join(lines) + "\n" + content + "\n"
    save_text(out_path, full_text)
    print(f"[+] Готово: {out_path}")
    print(f"[+] Блоков: {len(all_blocks)}")
    return out_path

def group_by_signature(records):
    grouped = defaultdict(list)
    for rec in records:
        grouped[rec["signature"]].append(rec)
    return grouped

def compare_record(a, b):
    lines = []
    if a["method"] != b["method"]:
        lines.append(f"Method: {a['method']} -> {b['method']}")
    if a["url"] != b["url"]:
        lines.append(f"URL: {a['url']} -> {b['url']}")
    if a["request_body"] != b["request_body"]:
        lines.append("--- Request body (A) ---")
        lines.append(a["request_body"])
        lines.append("--- Request body (B) ---")
        lines.append(b["request_body"])
    if a["response_body"] != b["response_body"]:
        lines.append("--- Response body (A) ---")
        lines.append(a["response_body"])
        lines.append("--- Response body (B) ---")
        lines.append(b["response_body"])
    if lines:
        return f"Signature: {a['signature']}\n" + "\n".join(lines)
    return ""

def compare_mode(selected_files, show_urls, decode, show_diffs, include_blocks, keywords, keep_duplicates, sig_level):
    base = selected_files[0]
    others = selected_files[1:]
    recs = []
    total = len(selected_files)
    for idx, path in enumerate(selected_files, 1):
        print(f"\r[*] Чтение файла {idx}/{total}: {path.name}          ", end="")
        blocks = load_log_and_extract_blocks(path)
        if decode:
            blocks = [universal_decode_text(b) for b in blocks]
        records = build_records_from_blocks(blocks, path.name, decode, sig_level)
        recs.append((path.name, records))
    print("\r[+] Чтение завершено          ")
    base_name, base_recs = recs[0]
    lines = []
    lines.append(f"=== COMPARE REPORT ===")
    lines.append(f"Base file: {base_name}")
    lines.append(f"Compared against: {', '.join(name for name, _ in recs[1:])}")
    lines.append(f"Signature level: {sig_level} (1=full URL, 2=path no params, 3=path only, 4=method only)")
    lines.append("")
    if keywords:
        lines.append(f"Keywords (blocks moved to top): {', '.join(keywords)}")
        lines.append("")
    all_urls = {}
    if show_urls:
        for name, rec_list in recs:
            urls = set()
            for r in rec_list:
                if r["url"]:
                    urls.add(r["url"])
            all_urls[name] = urls
        common = set.intersection(*[all_urls[name] for name, _ in recs]) if recs else set()
        lines.append("=== URL STATISTICS ===")
        for name, url_set in all_urls.items():
            unique = url_set - common
            lines.append(f"{name}: total {len(url_set)}, unique {len(unique)}")
        lines.append(f"Common URLs across all files: {len(common)}")
        if common:
            lines.append("  " + "\n  ".join(sorted(common)))
        lines.append("")
    sigs = {}
    for name, rec_list in recs:
        sig_set = set(r["signature"] for r in rec_list)
        sigs[name] = sig_set
        lines.append(f"[{name}] Total blocks: {len(rec_list)}, unique signatures: {len(sig_set)}")
    lines.append("")
    for name, rec_list in recs:
        sample = [r["signature"] for r in rec_list[:10]]
        lines.append(f"Sample signatures from {name} (first 10):")
        for s in sample:
            lines.append(f"  {s}")
        lines.append("")
    common_sigs = set.intersection(*[sigs[name] for name, _ in recs]) if recs else set()
    if not common_sigs:
        lines.append("!!! WARNING: No common signatures found between files !!!")
        lines.append("")
    else:
        lines.append(f"Common signatures: {len(common_sigs)}")
        lines.append("")
    for idx, (other_name, other_recs) in enumerate(recs[1:], 1):
        lines.append(f"=== Comparison with {other_name} (vs {base_name}) ===")
        map_base = group_by_signature(base_recs)
        map_other = group_by_signature(other_recs)
        keys = sorted(set(map_base.keys()) | set(map_other.keys()))
        shared = 0
        only_base = 0
        only_other = 0
        for key in keys:
            lb = map_base.get(key, [])
            lo = map_other.get(key, [])
            shared += min(len(lb), len(lo))
            if len(lb) > len(lo):
                only_base += len(lb) - len(lo)
            elif len(lo) > len(lb):
                only_other += len(lo) - len(lb)
        lines.append(f"Shared signatures: {shared}")
        lines.append(f"Only in {base_name}: {only_base}")
        lines.append(f"Only in {other_name}: {only_other}")
        lines.append("")
        if show_diffs:
            diff_blocks = 0
            for key in keys:
                lb = map_base.get(key, [])
                lo = map_other.get(key, [])
                pair_count = min(len(lb), len(lo))
                for i in range(pair_count):
                    section = compare_record(lb[i], lo[i])
                    if section:
                        diff_blocks += 1
                        lines.append(f"--- {key} #{i+1} ---")
                        lines.append(section)
                        lines.append("")
            if diff_blocks == 0:
                lines.append("No differences found for this pair.")
            else:
                lines.append(f"Blocks with differences: {diff_blocks}")
            lines.append("")
        if include_blocks:
            lines.append("--- Full blocks (base vs other) ---")
            for key in keys:
                lb = map_base.get(key, [])
                lo = map_other.get(key, [])
                pair_count = min(len(lb), len(lo))
                for i in range(pair_count):
                    lines.append(f"=== {key} #{i+1} (base) ===")
                    lines.append(lb[i]["raw"])
                    lines.append(f"=== {key} #{i+1} (other) ===")
                    lines.append(lo[i]["raw"])
                    lines.append("")
    stamp = now_stamp()
    out_path = OUTPUT_DIR / f"Spylog_compare_{base_name}_VS_{len(others)}files_{stamp}.txt"
    save_text(out_path, "\n".join(lines).rstrip() + "\n")
    print(f"[+] Готово: {out_path}")
    return out_path

def build_group_records(group_files, group_name, decode, keep_duplicates, sig_level):
    all_blocks = []
    for path in group_files:
        blocks = load_log_and_extract_blocks(path)
        if decode:
            blocks = [universal_decode_text(b) for b in blocks]
        all_blocks.extend(blocks)
    all_blocks = dedupe_exact(all_blocks, keep_duplicates)
    records = build_records_from_blocks(all_blocks, group_name, decode, sig_level)
    return records, all_blocks

def compare_groups(groups, show_urls, decode, show_diffs, include_blocks, keywords, keep_duplicates, sig_level):
    group_names = []
    group_records = []
    for idx, group in enumerate(groups, 1):
        name = f"Group_{idx}"
        print(f"\r[*] Обработка группы {idx} из {len(groups)}...          ", end="")
        rec, _ = build_group_records(group, name, decode, keep_duplicates, sig_level)
        group_names.append(name)
        group_records.append(rec)
    print("\r[+] Все группы обработаны          ")
    base_name = group_names[0]
    base_recs = group_records[0]
    lines = []
    lines.append("=== GROUP COMPARE REPORT ===")
    lines.append(f"Base group: {base_name} (files: {', '.join(p.name for p in groups[0])})")
    lines.append(f"Compared against: {', '.join(group_names[1:])}")
    lines.append(f"Signature level: {sig_level} (1=full URL, 2=path no params, 3=path only, 4=method only)")
    lines.append("")
    if keywords:
        lines.append(f"Keywords (blocks moved to top): {', '.join(keywords)}")
        lines.append("")
    all_urls = {}
    if show_urls:
        for idx, (name, rec_list) in enumerate(zip(group_names, group_records)):
            urls = set()
            for r in rec_list:
                if r["url"]:
                    urls.add(r["url"])
            all_urls[name] = urls
        common = set.intersection(*[all_urls[name] for name in group_names]) if group_names else set()
        lines.append("=== URL STATISTICS ===")
        for name, url_set in all_urls.items():
            unique = url_set - common
            lines.append(f"{name}: total {len(url_set)}, unique {len(unique)}")
        lines.append(f"Common URLs across all groups: {len(common)}")
        if common:
            lines.append("  " + "\n  ".join(sorted(common)))
        lines.append("")
    sigs = {}
    for name, rec_list in zip(group_names, group_records):
        sig_set = set(r["signature"] for r in rec_list)
        sigs[name] = sig_set
        lines.append(f"[{name}] Total blocks: {len(rec_list)}, unique signatures: {len(sig_set)}")
    lines.append("")
    for name, rec_list in zip(group_names, group_records):
        sample = [r["signature"] for r in rec_list[:10]]
        lines.append(f"Sample signatures from {name} (first 10):")
        for s in sample:
            lines.append(f"  {s}")
        lines.append("")
    common_sigs = set.intersection(*[sigs[name] for name in group_names]) if group_names else set()
    if not common_sigs:
        lines.append("!!! WARNING: No common signatures found between groups !!!")
        lines.append("")
    else:
        lines.append(f"Common signatures: {len(common_sigs)}")
        lines.append("")
    for idx in range(1, len(group_names)):
        other_name = group_names[idx]
        other_recs = group_records[idx]
        lines.append(f"=== Comparison with {other_name} (vs {base_name}) ===")
        map_base = group_by_signature(base_recs)
        map_other = group_by_signature(other_recs)
        keys = sorted(set(map_base.keys()) | set(map_other.keys()))
        shared = 0
        only_base = 0
        only_other = 0
        for key in keys:
            lb = map_base.get(key, [])
            lo = map_other.get(key, [])
            shared += min(len(lb), len(lo))
            if len(lb) > len(lo):
                only_base += len(lb) - len(lo)
            elif len(lo) > len(lb):
                only_other += len(lo) - len(lb)
        lines.append(f"Shared signatures: {shared}")
        lines.append(f"Only in {base_name}: {only_base}")
        lines.append(f"Only in {other_name}: {only_other}")
        lines.append("")
        if show_diffs:
            diff_blocks = 0
            for key in keys:
                lb = map_base.get(key, [])
                lo = map_other.get(key, [])
                pair_count = min(len(lb), len(lo))
                for i in range(pair_count):
                    section = compare_record(lb[i], lo[i])
                    if section:
                        diff_blocks += 1
                        lines.append(f"--- {key} #{i+1} ---")
                        lines.append(section)
                        lines.append("")
            if diff_blocks == 0:
                lines.append("No differences found for this pair.")
            else:
                lines.append(f"Blocks with differences: {diff_blocks}")
            lines.append("")
        if include_blocks:
            lines.append("--- Full blocks (base vs other) ---")
            for key in keys:
                lb = map_base.get(key, [])
                lo = map_other.get(key, [])
                pair_count = min(len(lb), len(lo))
                for i in range(pair_count):
                    lines.append(f"=== {key} #{i+1} (base) ===")
                    lines.append(lb[i]["raw"])
                    lines.append(f"=== {key} #{i+1} (other) ===")
                    lines.append(lo[i]["raw"])
                    lines.append("")
    stamp = now_stamp()
    out_path = OUTPUT_DIR / f"Spylog_compare_groups_{stamp}.txt"
    save_text(out_path, "\n".join(lines).rstrip() + "\n")
    print(f"[+] Готово: {out_path}")
    return out_path

def rename_output_file(path):
    while True:
        print(f"\n[?] Переименовать выходной файл {path.name}? (y/n/back) [n]: ", end="")
        ans = input().strip().lower()
        if ans == "":
            ans = "n"
        if ans in ("n", "no"):
            return path
        if ans in ("b", "back"):
            return path
        if ans in ("y", "yes"):
            break
        print("[!] Введите y, n или back")
    while True:
        new_name = input(f"[?] Новое имя (без пути): ").strip()
        new_name = clean_str(new_name)
        new_name = sanitize_filename(new_name)
        if not new_name:
            print("[!] Имя не может быть пустым")
            continue
        if new_name.lower() in ("b", "back"):
            return path
        new_path = path.parent / new_name
        if new_path.exists():
            print("[!] Файл уже существует")
            continue
        break
    while True:
        confirm = input(f"[?] Переименовать {path.name} в {new_name}? (y/n/back) [n]: ").strip().lower()
        if confirm == "":
            confirm = "n"
        if confirm == "y":
            path.rename(new_path)
            print(f"[+] Переименован в {new_name}")
            return new_path
        elif confirm == "n":
            return path
        elif confirm == "back":
            return path
        else:
            print("[!] Введите y, n или back")

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
            new_paths = []
            for i, path in enumerate(selected_files_sorted, 1):
                ext = path.suffix
                new_name = f"{prefix}-{i}{ext}"
                new_path = path.parent / new_name
                if new_path.exists() and new_path != path:
                    conflicts.append((path, new_path))
                new_paths.append(new_path)
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

def change_pattern():
    global SPY_PATTERN
    print(f"\n[+] Текущий паттерн: '{SPY_PATTERN.decode('utf-8', errors='ignore')}'")
    new = input("[?] Введите новый паттерн (пусто - отмена): ").strip()
    if new:
        SPY_PATTERN = new.encode('utf-8')
        save_config()
        print(f"[+] Паттерн изменён на '{new}'")
    else:
        print("[!] Отмена")

def clean_broken_files():
    print("\n=== Очистка повреждённых файлов ===")
    print("[1] Очистить папку SRLog (удалить все файлы)")
    print("[2] Очистить папку SpyLog (удалить все файлы)")
    print("[3] Очистить обе папки")
    print("[4] Показать файлы с подозрительными именами и удалить выборочно")
    print("[5] Назад")
    choice = input("[?] Ваш выбор [5]: ").strip()
    if choice == "":
        choice = "5"
    if choice == "5":
        return
    if choice in ("1", "2", "3"):
        dirs = []
        if choice in ("1", "3"):
            dirs.append(INPUT_DIR)
        if choice in ("2", "3"):
            dirs.append(OUTPUT_DIR)
        for d in dirs:
            if not d.exists():
                print(f"[!] Папка {d} не существует")
                continue
            print(f"[?] Удалить всё содержимое {d}? (y/n) [n]: ", end="")
            ans = input().strip().lower()
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
        return
    if choice == "4":
        print("\n[+] Поиск файлов с недопустимыми символами в именах...")
        bad_files = []
        for d in [INPUT_DIR, OUTPUT_DIR]:
            if not d.exists():
                continue
            for item in d.iterdir():
                name = item.name
                if re.search(r'[^a-zA-Z0-9_.\-]', name):
                    bad_files.append(item)
        if not bad_files:
            print("[+] Подозрительных файлов не найдено")
            return
        print(f"[+] Найдено {len(bad_files)} файлов с проблемными именами:")
        for i, p in enumerate(bad_files, 1):
            size = p.stat().st_size if p.is_file() else 0
            print(f"{i}. {p.name} ({size} bytes)")
        print("\n[?] Удалить все проблемные файлы? (y/n) [n]: ", end="")
        ans = input().strip().lower()
        if ans == "y":
            for p in bad_files:
                try:
                    if p.is_dir():
                        shutil.rmtree(p)
                    else:
                        p.unlink()
                    print(f"[+] Удалён: {p.name}")
                except Exception as e:
                    print(f"[!] Ошибка удаления {p.name}: {e}")
            print("[+] Все проблемные файлы удалены")
        else:
            print("[?] Удалять по одному? (y/n) [n]: ", end="")
            ans2 = input().strip().lower()
            if ans2 == "y":
                for p in bad_files:
                    print(f"\n[?] Удалить {p.name}? (y/n) [n]: ", end="")
                    ans3 = input().strip().lower()
                    if ans3 == "y":
                        try:
                            if p.is_dir():
                                shutil.rmtree(p)
                            else:
                                p.unlink()
                            print(f"[+] Удалён: {p.name}")
                        except Exception as e:
                            print(f"[!] Ошибка: {e}")
        return
    print("[!] Неверный выбор")

def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    while True:
        files = list_input_files()
        while not files:
            print("\n[!] В папке ~/SRLog нет файлов.")
            print("[*] Поместите файлы в ~/SRLog и нажмите Enter для продолжения")
            print("[*] Или введите 'exit' для выхода")
            cmd = input().strip().lower()
            if cmd == "exit":
                print("[+] Выход.")
                return
            files = list_input_files()
        print("\n[1] Extract")
        print("[2] Compare")
        print("[3] Rename files")
        print("[4] Change search pattern")
        print("[5] Exit")
        print("[6] Clean broken files")
        mode = input("\n[?] Выберите режим (1/2/3/4/5/6) [1]: ").strip()
        if mode == "":
            mode = "1"
        if mode == "5":
            print("[+] Выход.")
            break
        if mode == "6":
            clean_broken_files()
            continue
        if mode == "4":
            change_pattern()
            continue
        if mode == "3":
            rename_mode(files)
            continue
        if mode not in ("1", "2"):
            print("[!] Неверный выбор")
            continue
        if mode == "1":
            opts, keywords = ask_options("extract")
            selected = ask_files(files, compare=False)
            if selected is None:
                continue
            out_path = extract_mode(selected, opts[0], opts[1], opts[2], keywords, opts[4])
            rename_output_file(out_path)
        else:
            print("\n[?] Сравнивать файлы (1) или группы (2)? [1]: ", end="")
            cmp_type = input().strip()
            if cmp_type == "":
                cmp_type = "1"
            if cmp_type == "1":
                selected = ask_files(files, compare=True)
                if selected is None or len(selected) < 2:
                    print("[!] Нужно минимум 2 файла")
                    continue
                opts, keywords, sig_level = ask_options("compare")
                out_path = compare_mode(selected, opts[0], opts[1], opts[2], opts[3], keywords, opts[5], sig_level)
                rename_output_file(out_path)
            elif cmp_type == "2":
                groups = ask_groups(files)
                if groups is None:
                    continue
                opts, keywords, sig_level = ask_options("compare")
                out_path = compare_groups(groups, opts[0], opts[1], opts[2], opts[3], keywords, opts[5], sig_level)
                rename_output_file(out_path)
            else:
                print("[!] Неверный выбор")
                continue
        print("\n[+] Готово! Можете продолжить или выйти.")
        input("[*] Нажмите Enter для продолжения...")

if __name__ == "__main__":
    main()
EOF

echo "[*] Запуск Spylog Analyzer..."
python3 ~/Spylog.py
