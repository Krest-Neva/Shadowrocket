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
from urllib.parse import unquote, urlparse, parse_qs

ROOT = Path.home()
INPUT_DIR = ROOT / "SRLog"
OUTPUT_DIR = ROOT / "SpyLog"
ANSI_RE = re.compile(r"\x1b\[[0-9;]*[A-Za-z]")
SPY_PATTERN = "[Spylog]"
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
            with open(CONFIG_FILE, 'r') as f:
                SPY_PATTERN = f.read().strip()
        except:
            pass

def save_config():
    with open(CONFIG_FILE, 'w') as f:
        f.write(SPY_PATTERN)

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

def read_text_auto(path):
    raw = path.read_bytes()
    for enc in ("utf-8-sig", "utf-8", "cp1251", "latin-1"):
        try:
            return raw.decode(enc)
        except Exception:
            pass
    return raw.decode("utf-8", "replace")

def strip_ansi(text):
    return ANSI_RE.sub("", text)

def clean_text(text):
    return strip_ansi(text).replace("\r\n", "\n").replace("\r", "\n")

def maybe_repair_mojibake(text):
    if not any(ch in text for ch in ("Ð", "Ñ", "Ã", "Â")):
        return text
    try:
        return text.encode("latin1").decode("utf-8")
    except Exception:
        return text

def fix_mojibake_in_data(data):
    if isinstance(data, dict):
        return {k: fix_mojibake_in_data(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [fix_mojibake_in_data(v) for v in data]
    elif isinstance(data, str):
        return maybe_repair_mojibake(data)
    else:
        return data

def load_log(path):
    text = read_text_auto(path)
    text = clean_text(text)
    text = maybe_repair_mojibake(text)
    return text

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

def extract_spy_blocks(text):
    lines = text.split("\n")
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
        if line.strip() == "+---":
            blocks.append("\n".join(current).strip("\n"))
            current = []
            active = False
    if active and current:
        blocks.append("\n".join(current).strip("\n"))
    return blocks

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

def sanitize_for_compare(text):
    text = strip_ansi(text)
    text = text.replace(">>>", "").replace("<<<", "")
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    return text.strip()

def parse_header(block):
    first_line = block.split("\n", 1)[0]
    m = re.search(r"\[Spylog\].*?\[([A-Z]+)\]\s+([A-Z]+)\s+(https?://\S+)", first_line)
    if m:
        method = m.group(2)
        url = m.group(3).rstrip("]")
        return method, url
    m = re.search(r"(GET|POST|PUT|DELETE|PATCH|HEAD|OPTIONS|TRACE|CONNECT)\s+(https?://\S+)", block)
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

def parse_json_maybe(text):
    s = sanitize_for_compare(text)
    if not s:
        return None
    s = s.replace(">>>", "").replace("<<<", "")
    if not s.startswith("{") and not s.startswith("["):
        return None
    try:
        obj = json.loads(s)
        return fix_mojibake_in_data(obj)
    except Exception:
        return None

def extract_request_body(block):
    return collect_section(block.split("\n"), "| > Body:", True)

def extract_response_body(block):
    return collect_section(block.split("\n"), "| < Body:", False)

def compare_values(a, b, path="", out=None, limit=500):
    if out is None:
        out = []
    if len(out) >= limit:
        return out
    if type(a) != type(b):
        out.append((path or "$", a, b))
        return out
    if isinstance(a, dict):
        keys = sorted(set(a.keys()) | set(b.keys()), key=lambda x: str(x))
        for key in keys:
            if len(out) >= limit:
                break
            p = f"{path}.{key}" if path else str(key)
            if key not in a:
                out.append((p, None, b[key]))
            elif key not in b:
                out.append((p, a[key], None))
            else:
                compare_values(a[key], b[key], p, out, limit)
        return out
    if isinstance(a, list):
        if len(a) != len(b):
            out.append((path or "$", f"list[{len(a)}]", f"list[{len(b)}]"))
            if len(out) >= limit:
                return out
        for i in range(min(len(a), len(b))):
            if len(out) >= limit:
                break
            p = f"{path}[{i}]" if path else f"[{i}]"
            compare_values(a[i], b[i], p, out, limit)
        return out
    if a != b:
        out.append((path or "$", a, b))
    return out

def format_value(value):
    try:
        return json.dumps(value, ensure_ascii=False)
    except Exception:
        return repr(value)

def summarize_diff(diffs, limit=60):
    lines = []
    for i, (path, left, right) in enumerate(diffs):
        if i >= limit:
            lines.append(f"... и ещё {len(diffs) - limit} изменений")
            break
        lines.append(f"- {path}: {format_value(left)} -> {format_value(right)}")
    return "\n".join(lines)

def decode_all_strings(text):
    try:
        decoded = unquote(text)
        decoded = maybe_repair_mojibake(decoded)
        return decoded
    except Exception:
        return text

def normalize_url(url, level):
    if not url:
        return url
    parsed = urlparse(url)
    if level == 1:
        return url
    elif level == 2:
        return f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
    elif level == 3:
        return f"{parsed.path}" if parsed.path else "/"
    elif level == 4:
        return ""
    return url

def parse_record(block, source_name, decode=False, sig_level=1):
    method, url = parse_header(block)
    request_body = extract_request_body(block)
    response_body = extract_response_body(block)
    if decode:
        request_body = decode_all_strings(request_body)
        response_body = decode_all_strings(response_body)
    norm_url = normalize_url(url, sig_level) if url else "UNKNOWN"
    sig = f"{method or 'ANY'} {norm_url}"
    return {
        "source": source_name,
        "raw": block,
        "method": method or "",
        "url": url or "",
        "signature": sig,
        "request_body": request_body,
        "response_body": response_body,
        "request_json": parse_json_maybe(request_body),
        "response_json": parse_json_maybe(response_body),
    }

def build_records(path, decode=False, keep_duplicates=False, sig_level=1):
    text = load_log(path)
    blocks = extract_spy_blocks(text)
    blocks = dedupe_exact(blocks, keep_duplicates)
    records = [parse_record(block, path.name, decode, sig_level) for block in blocks]
    return records, blocks

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

def extract_mode(selected_files, show_urls, decode, show_stats, keywords, keep_duplicates):
    all_blocks = []
    per_file_counts = []
    total_found = 0
    total_files = len(selected_files)
    for idx, path in enumerate(selected_files, 1):
        print(f"\r[*] Обработка файла {idx}/{total_files}: {path.name}          ", end="")
        _, blocks = build_records(path, decode, keep_duplicates)
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

def record_diff_lines(a, b):
    lines = []
    if a["method"] != b["method"]:
        lines.append(f"Method: {a['method']} -> {b['method']}")
    if a["url"] != b["url"]:
        lines.append(f"URL: {a['url']} -> {b['url']}")
    req_body_a = a["request_body"]
    req_body_b = b["request_body"]
    resp_body_a = a["response_body"]
    resp_body_b = b["response_body"]
    if req_body_a or req_body_b:
        lines.append("--- Request body (A) ---")
        lines.append(req_body_a if req_body_a else "(empty)")
        lines.append("--- Request body (B) ---")
        lines.append(req_body_b if req_body_b else "(empty)")
    if resp_body_a or resp_body_b:
        lines.append("--- Response body (A) ---")
        lines.append(resp_body_a if resp_body_a else "(empty)")
        lines.append("--- Response body (B) ---")
        lines.append(resp_body_b if resp_body_b else "(empty)")
    if a["request_json"] is not None and b["request_json"] is not None:
        req_diffs = compare_values(a["request_json"], b["request_json"], "", [], 500)
        if req_diffs:
            lines.append("Request JSON changes:")
            lines.append(summarize_diff(req_diffs))
    elif req_body_a != req_body_b:
        left = sanitize_for_compare(req_body_a)
        right = sanitize_for_compare(req_body_b)
        if left != right:
            lines.append("Request body raw diff:")
            lines.append(f"- left: {left[:500]}")
            lines.append(f"- right: {right[:500]}")
    if a["response_json"] is not None and b["response_json"] is not None:
        res_diffs = compare_values(a["response_json"], b["response_json"], "", [], 500)
        if res_diffs:
            lines.append("Response JSON changes:")
            lines.append(summarize_diff(res_diffs))
    elif resp_body_a != resp_body_b:
        left = sanitize_for_compare(resp_body_a)
        right = sanitize_for_compare(resp_body_b)
        if left != right:
            lines.append("Response body raw diff:")
            lines.append(f"- left: {left[:500]}")
            lines.append(f"- right: {right[:500]}")
    return lines

def compare_record(a, b):
    lines = record_diff_lines(a, b)
    if not lines:
        return ""
    out = [f"Signature: {a['signature']}"]
    out.extend(lines)
    return "\n".join(out)

def compare_mode(selected_files, show_urls, decode, show_diffs, include_blocks, keywords, keep_duplicates, sig_level):
    base = selected_files[0]
    others = selected_files[1:]
    recs = []
    total = len(selected_files)
    for idx, path in enumerate(selected_files, 1):
        print(f"\r[*] Чтение файла {idx}/{total}: {path.name}          ", end="")
        rec, _ = build_records(path, decode, keep_duplicates, sig_level)
        recs.append((path.name, rec))
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
        lines.append("This means that none of the requests match by method+URL (with current signature level).")
        lines.append("Possible reasons: different domains, paths, or the files contain completely different logs.")
        lines.append("Check the sample signatures above to see the differences.")
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
        _, blocks = build_records(path, decode, keep_duplicates, sig_level)
        all_blocks.extend(blocks)
    all_blocks = dedupe_exact(all_blocks, keep_duplicates)
    records = [parse_record(block, group_name, decode, sig_level) for block in all_blocks]
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
    print(f"\n[+] Текущий паттерн: '{SPY_PATTERN}'")
    new = input("[?] Введите новый паттерн (пусто - отмена): ").strip()
    if new:
        SPY_PATTERN = new
        save_config()
        print(f"[+] Паттерн изменён на '{SPY_PATTERN}'")
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
