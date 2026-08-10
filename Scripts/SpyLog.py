#!/bin/sh
clear

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

def ask_rename_file(files, mode="input"):
    while True:
        print("\n[?] Хотите переименовать файл? (y/n/back)")
        ans = input().strip().lower()
        if ans in ("n", "no"):
            return None
        if ans in ("b", "back"):
            return "back"
        if ans in ("y", "yes"):
            break
        print("[!] Введите y, n или back")
    print_files(files)
    while True:
        choice = input("\n[?] Выберите номер файла для переименования: ").strip()
        if choice.lower() in ("b", "back"):
            return "back"
        try:
            idx = int(choice) - 1
            if 0 <= idx < len(files):
                break
            print("[!] Неверный номер")
        except:
            print("[!] Введите число")
    path = files[idx]
    while True:
        new_name = input(f"[?] Новое имя для {path.name}: ").strip()
        if not new_name:
            print("[!] Имя не может быть пустым")
            continue
        if new_name.lower() in ("b", "back"):
            return "back"
        new_path = path.parent / new_name
        if new_path.exists():
            print("[!] Файл с таким именем уже существует")
            continue
        break
    while True:
        confirm = input(f"[?] Переименовать {path.name} в {new_name}? (y/n/back): ").strip().lower()
        if confirm == "y":
            path.rename(new_path)
            print(f"[+] Переименован в {new_name}")
            return new_path
        elif confirm == "n":
            return None
        elif confirm == "back":
            return "back"
        else:
            print("[!] Введите y, n или back")

def ask_files(files, compare=False):
    while True:
        while True:
            renamed = ask_rename_file(files)
            if renamed == "back":
                return None
            if renamed is not None:
                files = list_input_files()
                print_files(files)
            break
        if compare:
            print("\n[?] Выберите файлы для сравнения (минимум 2), например 1,2,3 или all")
            choice = input("[?] Ваш выбор: ").strip()
            if choice.lower() in ("b", "back"):
                return None
            try:
                indices = parse_selection(choice, len(files))
                if len(indices) < 2:
                    print("[!] Нужно выбрать минимум 2 файла")
                    continue
                selected = [files[i-1] for i in indices]
                return selected
            except:
                print("[!] Неверный выбор")
        else:
            print("\n[?] Выберите один или несколько файлов, например 1,3-4 или all (или 'back' для возврата)")
            choice = input("[?] Ваш выбор: ").strip()
            if choice.lower() in ("b", "back"):
                return None
            try:
                indices = parse_selection(choice, len(files))
                selected = [files[i-1] for i in indices]
                return selected
            except:
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

def build_records(path, progress_callback=None):
    text = load_log(path)
    blocks = extract_spy_blocks(text)
    if progress_callback:
        progress_callback(len(blocks), "extract")
    blocks = dedupe_exact(blocks)
    records = [parse_record(block, path.name) for block in blocks]
    return records, blocks

def extract_mode(selected_files):
    all_blocks = []
    per_file_counts = []
    total_found = 0
    total_files = len(selected_files)
    for idx, path in enumerate(selected_files, 1):
        print(f"\r[*] Обработка файла {idx}/{total_files}: {path.name}          ", end="")
        _, blocks = build_records(path)
        total_found += len(blocks)
        per_file_counts.append((path.name, len(blocks)))
        all_blocks.extend(blocks)
    print("\r[*] Дедупликация блоков...          ", end="")
    all_blocks = dedupe_exact(all_blocks)
    print("\r[+] Готово, сохраняем...          ")
    stamp = now_stamp()
    out_path = OUTPUT_DIR / f"Spylog_extract_{stamp}.txt"
    urls = set()
    for block in all_blocks:
        method, url = parse_header(block)
        if url:
            urls.add(url)
    header = [
        f"Source files: {', '.join(p.name for p in selected_files)}",
        f"Blocks before dedupe: {total_found}",
        f"Blocks after dedupe: {len(all_blocks)}",
        "",
        "=== Unique URLs found ===",
        *sorted(urls),
        "",
        "=== Per-file block counts ===",
    ]
    for name, count in per_file_counts:
        header.append(f"{name}: {count}")
    header.append("")
    header.append("=== Extracted blocks ===")
    header.append("")
    content = "\n\n".join(all_blocks)
    full_text = "\n".join(header) + "\n" + content + "\n"
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

def compare_mode(selected_files):
    base = selected_files[0]
    others = selected_files[1:]
    recs = []
    total = len(selected_files)
    for idx, path in enumerate(selected_files, 1):
        print(f"\r[*] Чтение файла {idx}/{total}: {path.name}          ", end="")
        rec, _ = build_records(path)
        recs.append((path.name, rec))
    print("\r[+] Чтение завершено          ")
    base_name, base_recs = recs[0]
    lines = []
    lines.append(f"=== COMPARE REPORT ===")
    lines.append(f"Base file: {base_name}")
    lines.append(f"Compared against: {', '.join(name for name, _ in recs[1:])}")
    lines.append("")
    all_urls = {}
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
    stamp = now_stamp()
    out_path = OUTPUT_DIR / f"Spylog_compare_{base_name}_VS_{len(others)}files_{stamp}.txt"
    save_text(out_path, "\n".join(lines).rstrip() + "\n")
    print(f"[+] Готово: {out_path}")
    return out_path

def rename_output_file(path):
    while True:
        print(f"\n[?] Переименовать выходной файл {path.name}? (y/n/back)")
        ans = input().strip().lower()
        if ans in ("n", "no"):
            return path
        if ans in ("b", "back"):
            return path
        if ans in ("y", "yes"):
            break
        print("[!] Введите y, n или back")
    while True:
        new_name = input(f"[?] Новое имя (без пути): ").strip()
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
        confirm = input(f"[?] Переименовать {path.name} в {new_name}? (y/n/back): ").strip().lower()
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

def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    while True:
        files = list_input_files()
        print("\n[1] Extract")
        print("[2] Compare")
        print("[3] Exit")
        mode = input("\n[?] Выберите режим (1/2/3): ").strip()
        if mode == "3":
            print("[+] Выход.")
            break
        if mode not in ("1", "2"):
            print("[!] Неверный выбор")
            continue
        selected = ask_files(files, compare=(mode == "2"))
        if selected is None:
            continue
        if mode == "1":
            out_path = extract_mode(selected)
        else:
            out_path = compare_mode(selected)
        rename_output_file(out_path)
        print("\n[+] Готово! Можете продолжить или выйти.")
        input("[*] Нажмите Enter для продолжения...")

if __name__ == "__main__":
    main()
EOF

echo "[*] Запуск Spylog Analyzer..."
python3 ~/Spylog.py
