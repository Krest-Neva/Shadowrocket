#!/bin/sh
clear

echo "[*] Настройка DNS..."
echo "nameserver 8.8.8.8" > /etc/resolv.conf
echo "nameserver 8.8.4.4" >> /etc/resolv.conf
echo "nameserver 94.140.14.14" >> /etc/resolv.conf
echo "nameserver 94.140.15.15" >> /etc/resolv.conf
echo "nameserver 1.1.1.1" >> /etc/resolv.conf

echo "[*] Проверка соединения с интернетом..."
while ! ping -c 3 google.com > /dev/null 2>&1; do
    echo "[!] ОШИБКА: Нет подключения к интернету!"
    echo "[*] Повторная проверка через 5 секунд..."
    sleep 5
done
echo "[+] Интернет доступен."

echo "[*] Обновление системы и установка зависимостей..."
apk update
apk upgrade
apk add --no-cache python3 py3-pip curl wget bash

echo "[*] Создание папок..."
mkdir -p ~/SRLog
mkdir -p ~/SpyLog

echo "[*] Удаление старых файлов..."
rm -f ~/Spylog.py

cat << 'EOF' > ~/Spylog.py
import json
import re
import sys
from pathlib import Path
from datetime import datetime
from collections import defaultdict

ROOT = Path.home()
INPUT_DIR = ROOT / "SRLog"
OUTPUT_DIR = ROOT / "SpyLog"
ANSI_RE = re.compile(r"\x1b\[[0-9;]*[A-Za-z]")
SPY_TAG = "[Spylog]"
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
    if not files:
        die(f"В папке {INPUT_DIR} нет файлов")
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

def ask_files(files, compare=False):
    print_files(files)
    if compare:
        while True:
            choice = input("\n[?] Выбери 2 файла для сравнения, например 1,2: ").strip()
            try:
                indices = parse_selection(choice, len(files))
                if len(indices) != 2:
                    print("[!] Нужно выбрать ровно 2 файла")
                    continue
                if indices[0] == indices[1]:
                    print("[!] Файлы должны быть разными")
                    continue
                return [files[indices[0] - 1], files[indices[1] - 1]]
            except Exception:
                print("[!] Неверный выбор")
    while True:
        choice = input("\n[?] Выбери один или несколько файлов, например 1,3-4 или all: ").strip()
        try:
            indices = parse_selection(choice, len(files))
            return [files[i - 1] for i in indices]
        except Exception:
            print("[!] Неверный выбор")

def extract_spy_blocks(text):
    lines = text.split("\n")
    blocks = []
    current = []
    active = False
    for line in lines:
        if not active:
            if SPY_TAG in line:
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

def dedupe_exact(blocks):
    seen = set()
    out = []
    for block in blocks:
        key = block.replace("\r\n", "\n").strip("\n")
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
        return json.loads(s)
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

def parse_record(block, source_name):
    method, url = parse_header(block)
    request_body = extract_request_body(block)
    response_body = extract_response_body(block)
    return {
        "source": source_name,
        "raw": block,
        "method": method or "",
        "url": url or "",
        "signature": f"{method or 'ANY'} {url or 'UNKNOWN'}",
        "request_body": request_body,
        "response_body": response_body,
        "request_json": parse_json_maybe(request_body),
        "response_json": parse_json_maybe(response_body),
    }

def build_records(path):
    text = load_log(path)
    blocks = extract_spy_blocks(text)
    blocks = dedupe_exact(blocks)
    records = [parse_record(block, path.name) for block in blocks]
    return records, blocks

def extract_mode(selected_files):
    all_blocks = []
    per_file_counts = []
    total_found = 0
    for path in selected_files:
        _, blocks = build_records(path)
        total_found += len(blocks)
        per_file_counts.append((path.name, len(blocks)))
        all_blocks.extend(blocks)
    all_blocks = dedupe_exact(all_blocks)
    stamp = now_stamp()
    out_path = OUTPUT_DIR / f"Spylog_extract_{stamp}.txt"
    header = [f"Source files: {', '.join(p.name for p in selected_files)}", f"Blocks before dedupe: {total_found}", f"Blocks after dedupe: {len(all_blocks)}", ""]
    for name, count in per_file_counts:
        header.append(f"{name}: {count}")
    header.append("")
    content = "\n\n".join(all_blocks)
    save_text(out_path, "\n".join(header) + "\n" + content + "\n")
    print(f"[+] Готово: {out_path}")
    print(f"[+] Блоков: {len(all_blocks)}")

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
    if a["request_json"] is not None and b["request_json"] is not None:
        req_diffs = compare_values(a["request_json"], b["request_json"], "", [], 500)
        if req_diffs:
            lines.append("Request JSON changes:")
            lines.append(summarize_diff(req_diffs))
    else:
        left = sanitize_for_compare(a["request_body"])
        right = sanitize_for_compare(b["request_body"])
        if left != right:
            lines.append("Request body changed:")
            lines.append(f"- left: {left[:2000]}")
            lines.append(f"- right: {right[:2000]}")
    if a["response_json"] is not None and b["response_json"] is not None:
        res_diffs = compare_values(a["response_json"], b["response_json"], "", [], 500)
        if res_diffs:
            lines.append("Response JSON changes:")
            lines.append(summarize_diff(res_diffs))
    else:
        left = sanitize_for_compare(a["response_body"])
        right = sanitize_for_compare(b["response_body"])
        if left != right:
            lines.append("Response body changed:")
            lines.append(f"- left: {left[:2000]}")
            lines.append(f"- right: {right[:2000]}")
    return lines

def compare_record(a, b):
    lines = record_diff_lines(a, b)
    if not lines:
        return ""
    out = [f"Signature: {a['signature']}"]
    out.extend(lines)
    return "\n".join(out)

def compare_mode(file_a, file_b):
    rec_a, _ = build_records(file_a)
    rec_b, _ = build_records(file_b)
    map_a = group_by_signature(rec_a)
    map_b = group_by_signature(rec_b)
    keys = sorted(set(map_a.keys()) | set(map_b.keys()))
    lines = []
    lines.append(f"File A: {file_a.name}")
    lines.append(f"File B: {file_b.name}")
    lines.append(f"Spylog blocks A: {len(rec_a)}")
    lines.append(f"Spylog blocks B: {len(rec_b)}")
    lines.append("")
    shared = 0
    only_a = 0
    only_b = 0
    for key in keys:
        la = map_a.get(key, [])
        lb = map_b.get(key, [])
        shared += min(len(la), len(lb))
        if len(la) > len(lb):
            only_a += len(la) - len(lb)
        elif len(lb) > len(la):
            only_b += len(lb) - len(la)
    lines.append(f"Matched occurrences: {shared}")
    lines.append(f"Unmatched in A: {only_a}")
    lines.append(f"Unmatched in B: {only_b}")
    lines.append("")
    diff_blocks = 0
    for key in keys:
        la = map_a.get(key, [])
        lb = map_b.get(key, [])
        pair_count = min(len(la), len(lb))
        for i in range(pair_count):
            section = compare_record(la[i], lb[i])
            if section:
                diff_blocks += 1
                lines.append(f"=== {key} #{i + 1} ===")
                lines.append(section)
                lines.append("")
    if diff_blocks == 0:
        lines.append("Различий не найдено")
    else:
        lines.append(f"Blocks with differences: {diff_blocks}")
    stamp = now_stamp()
    out_path = OUTPUT_DIR / f"Spylog_compare_{file_a.stem}_VS_{file_b.stem}_{stamp}.txt"
    save_text(out_path, "\n".join(lines).rstrip() + "\n")
    print(f"[+] Готово: {out_path}")
    print(f"[+] Сопоставлено: {shared}")
    print(f"[+] Блоков с отличиями: {diff_blocks}")

def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    files = list_input_files()
    print("[1] Extract")
    print("[2] Compare")
    while True:
        mode = input("\n[?] Выбери режим 1 или 2: ").strip()
        if mode in {"1", "2"}:
            break
        print("[!] Неверный выбор")
    if mode == "1":
        selected = ask_files(files, compare=False)
        extract_mode(selected)
    else:
        selected = ask_files(files, compare=True)
        compare_mode(selected[0], selected[1])

if __name__ == "__main__":
    main()
EOF

echo "[*] Настройка DNS перед запуском..."
echo "nameserver 8.8.8.8" > /etc/resolv.conf
echo "nameserver 8.8.4.4" >> /etc/resolv.conf
echo "nameserver 94.140.14.14" >> /etc/resolv.conf
echo "nameserver 94.140.15.15" >> /etc/resolv.conf
echo "nameserver 1.1.1.1" >> /etc/resolv.conf

echo "[*] Повторная проверка интернета..."
while ! ping -c 3 google.com > /dev/null 2>&1; do
    echo "[!] ОШИБКА: Соединение потеряно."
    echo "[*] Повторная проверка через 5 секунд..."
    sleep 5
done

echo "[*] Запуск Spylog Analyzer..."
python3 ~/Spylog.py
