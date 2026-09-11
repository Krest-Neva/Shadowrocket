#!/bin/sh
clear

echo "[*] Настройка DNS..."
echo "nameserver 8.8.8.8" > /etc/resolv.conf
echo "nameserver 8.8.4.4" >> /etc/resolv.conf
echo "nameserver 94.140.14.14" >> /etc/resolv.conf
echo "nameserver 94.140.15.15" >> /etc/resolv.conf
echo "nameserver 1.1.1.1" >> /etc/resolv.conf

echo "[*] Проверка соединения..."
while ! ping -c 3 google.com > /dev/null 2>&1; do
    echo "[!] ОШИБКА: Нет подключения к интернету!"
    echo "[*] Повторная проверка через 5 секунд..."
    sleep 5
done
echo "[+] Интернет доступен."

echo "[*] Установка зависимостей..."
apk update
apk add python3 curl bind-tools ca-certificates

echo "[*] Очистка старых файлов..."
rm -f URL_REWRITE.list
rm -f MITM.list
rm -f "LogsRedirectScript"

cat << 'EOF' > "GEN_REDIRECT.py"
import sys
import os
import re
import time
import tempfile
import subprocess
import urllib.request
from collections import defaultdict

SOURCE_URL = "https://dl.oisd.nl/oisd_nsfw_surge.list"
REDIRECT_URL = "https://raw.githubusercontent.com/Krest-Neva/Shadowrocket/refs/heads/main/Other/Redirect"
OUT_URL = "URL_REWRITE.list"
OUT_MITM = "MITM.list"
LOG_FILE = "LogsRedirectScript"

DNS_SERVERS = ["8.8.8.8", "8.8.4.4", "94.140.14.14", "94.140.15.15", "1.1.1.1"]
HEADERS = {'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1'}

INVALID_CHARS = set('?|=*(),&:[]/\\%#_')
DANGEROUS_TLDS = {"html", "xml", "gif", "js", "php", "css", "png", "jpg"}

def setup_dns():
    with open("/etc/resolv.conf", "w") as f:
        for dns in DNS_SERVERS:
            f.write("nameserver " + dns + "\n")

def check_internet():
    for _ in range(60):
        r = subprocess.run(["ping", "-c", "3", "google.com"],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if r.returncode == 0:
            return True
        time.sleep(5)
    return False

def is_valid_domain(d):
    if not d or len(d) < 4:
        return False
    if not d.isascii():
        return False
    if d.startswith('.') or d.startswith('-'):
        return False
    if d.endswith('.') or d.endswith('-'):
        return False
    if '.' not in d:
        return False
    if not INVALID_CHARS.isdisjoint(d):
        return False
    parts = d.split('.')
    if len(parts) < 2:
        return False
    if parts[-1].lower() in DANGEROUS_TLDS and len(parts) == 2:
        return False
    if any((not p) or len(p) > 63 for p in parts):
        return False
    return True

def parse_line(line):
    line = line.strip()
    if not line or line.startswith(('#', '!', ';', '//', '[')):
        return None
    if '##' in line or '#@#' in line or line.startswith('@@'):
        return None
    if '#' in line:
        line = line.split('#', 1)[0].strip()
    if not line:
        return None
    if ',' in line and not line.startswith('||'):
        parts = line.split(',', 1)
        key = parts[0].strip().upper()
        if 'DOMAIN' not in key:
            return None
        val = parts[1].strip().split()[0] if parts[1].strip() else ''
        val = val.lstrip('*.').lower().rstrip('.')
        return val or None
    if line.startswith(('0.0.0.0', '127.0.0.1', '::1')):
        tokens = line.split()
        if len(tokens) >= 2:
            return tokens[1].lstrip('*.').lower().rstrip('.') or None
        return None
    clean = re.sub(r'^[|\s]*\|\|', '', line)
    clean = re.sub(r'^\|', '', clean)
    clean = re.sub(r'^https?://', '', clean)
    clean = clean.split('^')[0].split('$')[0].split('/')[0].split(':')[0].split('*')[0].strip().strip('.')
    return clean.lower() if clean else None

def download(url):
    for attempt in range(3):
        try:
            req = urllib.request.Request(url, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = resp.read().decode('utf-8', errors='ignore')
                if len(data) > 100 and '<html' not in data[:300].lower():
                    return data.splitlines()
        except Exception:
            pass
        try:
            tmp = tempfile.NamedTemporaryFile(delete=False)
            tmp.close()
            r = subprocess.run(['curl', '-s', '-L', '-k', '-A', HEADERS['User-Agent'], '-o', tmp.name, url], timeout=30)
            if r.returncode == 0:
                with open(tmp.name, 'rb') as f:
                    data = f.read().decode('utf-8', errors='ignore')
                try:
                    os.unlink(tmp.name)
                except Exception:
                    pass
                if len(data) > 100 and '<html' not in data[:300].lower():
                    return data.splitlines()
            try:
                os.unlink(tmp.name)
            except Exception:
                pass
        except Exception:
            pass
        time.sleep(2 + attempt)
    return []

def remove_redundant(domains):
    s = set(domains)
    result = set()
    for d in s:
        parts = d.split('.')
        if any('.'.join(parts[i:]) in s for i in range(1, len(parts))):
            continue
        result.add(d)
    return result

class TrieNode:
    __slots__ = ('children', 'is_end')
    def __init__(self):
        self.children = {}
        self.is_end = False

def build_trie(strings):
    root = TrieNode()
    for s in strings:
        node = root
        for ch in s:
            if ch not in node.children:
                node.children[ch] = TrieNode()
            node = node.children[ch]
        node.is_end = True
    return root

def escape_in_class(ch):
    return '\\' + ch if ch in '\\^-]' else ch

def char_class(chars):
    chars = sorted(set(chars))
    if len(chars) == 1:
        return re.escape(chars[0])
    ranges = []
    start = end = chars[0]
    for c in chars[1:]:
        if ord(c) == ord(end) + 1:
            end = c
        else:
            ranges.append((start, end))
            start = end = c
    ranges.append((start, end))
    parts = []
    for s, e in ranges:
        if s == e:
            parts.append(escape_in_class(s))
        elif ord(e) == ord(s) + 1:
            parts.append(escape_in_class(s) + escape_in_class(e))
        else:
            parts.append(escape_in_class(s) + '-' + escape_in_class(e))
    return '[' + ''.join(parts) + ']'

def trie_to_regex(node):
    if not node.children:
        return ''
    parts = []
    if node.is_end:
        parts.append('')
    leaves = []
    branches = []
    for ch, child in node.children.items():
        if (not child.children) and child.is_end:
            leaves.append(ch)
        else:
            branches.append((ch, trie_to_regex(child)))
    if leaves:
        parts.append(char_class(leaves))
    for ch, sub in branches:
        parts.append(re.escape(ch) + sub)
    if not parts:
        return ''
    if len(parts) == 1:
        return parts[0]
    return '(?:' + '|'.join(parts) + ')'

def build_regex(domains):
    groups = defaultdict(set)
    for d in domains:
        groups[d.rsplit('.', 1)[-1]].add(d)
    alts = []
    for tld, doms in groups.items():
        suffix = '.' + tld
        bases = set()
        for d in doms:
            if d.endswith(suffix):
                bases.add(d[:-len(suffix)])
        if not bases:
            continue
        alts.append(trie_to_regex(build_trie(bases)) + re.escape(suffix))
    if not alts:
        return ''
    if len(alts) == 1:
        return alts[0]
    return '(?:' + '|'.join(alts) + ')'

def write_log(total_lines, valid, redundant, final, regex_len, skipped):
    try:
        with open(LOG_FILE, 'w', encoding='utf-8') as f:
            f.write("Log generated at: " + time.ctime() + "\n")
            f.write("=" * 60 + "\n")
            f.write("Source: " + SOURCE_URL + "\n")
            f.write("-" * 60 + "\n")
            f.write("Downloaded lines:       " + str(total_lines) + "\n")
            f.write("Valid domains:          " + str(valid) + "\n")
            f.write("Skipped (invalid):      " + str(skipped) + "\n")
            f.write("After dedup redundant:  " + str(redundant) + "\n")
            f.write("Unique final domains:   " + str(final) + "\n")
            f.write("Regex length (chars):   " + str(regex_len) + "\n")
            f.write("=" * 60 + "\n")
    except Exception as e:
        sys.stdout.write("[!] Log write failed: " + str(e) + "\n")

def main():
    print("[*] Настройка DNS...")
    setup_dns()
    print("[*] Проверка интернета...")
    if not check_internet():
        print("[!] Нет соединения с интернетом")
        sys.exit(1)
    print("[+] Интернет доступен.")

    print("[*] Скачивание: " + SOURCE_URL)
    lines = download(SOURCE_URL)
    if not lines:
        print("[!] Не удалось скачать список")
        sys.exit(1)
    print("[+] Получено строк: " + str(len(lines)))

    domains = set()
    skipped = 0
    total = len(lines)
    for i, raw in enumerate(lines, 1):
        if i % 2000 == 0 or i == total:
            sys.stdout.write("\r  [parse] " + str(i) + "/" + str(total))
            sys.stdout.flush()
        d = parse_line(raw)
        if not d:
            continue
        if not is_valid_domain(d):
            skipped += 1
            continue
        domains.add(d)
    sys.stdout.write("\n")
    print("[*] Валидных доменов: " + str(len(domains)) + " | отброшено: " + str(skipped))

    valid_count = len(domains)
    domains = remove_redundant(domains)
    print("[*] После удаления избыточных: " + str(len(domains)))

    domains = sorted(domains)
    regex = build_regex(domains)
    pattern = r'^https?:\/\/(?:[^\/.]+\.)*' + regex + r'(?::\d+)?(?:\/.*)?$'
    print("[*] Длина regex: " + str(len(pattern)))

    with open(OUT_URL, 'w', encoding='utf-8') as f:
        f.write("#GDEBENZ/REDIRECT\n")
        f.write(pattern + " " + REDIRECT_URL + " 302\n")
    print("[+] Записано: " + OUT_URL)

    mitm_entries = set()
    for d in domains:
        mitm_entries.add(d)
        mitm_entries.add('*.' + d)
    mitm_sorted = sorted(mitm_entries)
    with open(OUT_MITM, 'w', encoding='utf-8') as f:
        f.write("hostname = " + ", ".join(mitm_sorted) + "\n")
    print("[+] Записано: " + OUT_MITM + " (записей: " + str(len(mitm_sorted)) + ")")

    write_log(total, valid_count, len(domains), len(domains), len(pattern), skipped)
    print("[+] Лог: " + LOG_FILE)

if __name__ == '__main__':
    main()
EOF

echo "[*] Запуск генератора..."
python3 "GEN_REDIRECT.py"

echo ""
echo "[*] Результат — содержимое URL_REWRITE.list:"
echo "============================================================"
cat URL_REWRITE.list
echo "============================================================"
echo ""
echo "[*] MITM.list сохранён отдельно (может быть длинным)."
echo "[*] Готово."
