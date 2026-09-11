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
apk add python3 curl wget aria2 bind-tools ca-certificates openssl

echo "[*] Очистка старых файлов..."
rm -f URL_REWRITE.list
rm -f MITM.list
rm -f "LogsRedirectScript"
rm -f aria_tmp_dl

cat << 'EOF' > "GEN_REDIRECT.py"
import sys
import os
import re
import time
import shutil
import tempfile
import subprocess
import urllib.request
from collections import defaultdict

SOURCE_URL = "https://dl.oisd.nl/oisd_nsfw_surge.list"
REDIRECT_URL = "https://raw.githubusercontent.com/Krest-Neva/Shadowrocket/refs/heads/main/Other/Redirect"
OUT_URL = "URL_REWRITE.list"
OUT_MITM = "MITM.list"
LOG_FILE = "LogsRedirectScript"

STEP = 100

WHITE_URLS = {
    "direct": [
        "https://raw.githubusercontent.com/Loyalsoldier/surge-rules/release/ruleset/direct.txt",
        "https://cdn.jsdelivr.net/gh/Loyalsoldier/surge-rules@release/ruleset/direct.txt",
        "https://raw.githubusercontent.com/Loyalsoldier/surge-rules/release/direct.txt",
        "https://cdn.jsdelivr.net/gh/Loyalsoldier/surge-rules@release/direct.txt"
    ],
    "proxy": [
        "https://raw.githubusercontent.com/Loyalsoldier/surge-rules/release/ruleset/proxy.txt",
        "https://cdn.jsdelivr.net/gh/Loyalsoldier/surge-rules@release/ruleset/proxy.txt",
        "https://raw.githubusercontent.com/Loyalsoldier/surge-rules/release/proxy.txt",
        "https://cdn.jsdelivr.net/gh/Loyalsoldier/surge-rules@release/proxy.txt"
    ],
    "apple": [
        "https://raw.githubusercontent.com/Loyalsoldier/surge-rules/release/ruleset/apple.txt",
        "https://cdn.jsdelivr.net/gh/Loyalsoldier/surge-rules@release/ruleset/apple.txt",
        "https://raw.githubusercontent.com/Loyalsoldier/surge-rules/release/apple.txt",
        "https://cdn.jsdelivr.net/gh/Loyalsoldier/surge-rules@release/apple.txt"
    ],
    "icloud": [
        "https://raw.githubusercontent.com/Loyalsoldier/surge-rules/release/ruleset/icloud.txt",
        "https://cdn.jsdelivr.net/gh/Loyalsoldier/surge-rules@release/ruleset/icloud.txt",
        "https://raw.githubusercontent.com/Loyalsoldier/surge-rules/release/icloud.txt",
        "https://cdn.jsdelivr.net/gh/Loyalsoldier/surge-rules@release/icloud.txt"
    ],
    "anudeepND": [
        "https://raw.githubusercontent.com/anudeepND/whitelist/master/domains/whitelist.txt",
        "https://cdn.jsdelivr.net/gh/anudeepND/whitelist@master/domains/whitelist.txt"
    ],
    "ru_mobile": [
        "https://cdn.jsdelivr.net/gh/hxehex/russia-mobile-internet-whitelist@main/whitelist.txt",
        "https://raw.githubusercontent.com/hxehex/russia-mobile-internet-whitelist/main/whitelist.txt"
    ],
    "tele2_msk": "https://raw.githubusercontent.com/chebur-net/russia-mobile-whitelist/refs/heads/main/moscow-tele2/domains.txt",
    "tele2_spb": "https://raw.githubusercontent.com/chebur-net/russia-mobile-whitelist/refs/heads/main/spb-tele2/domains.txt",
    "rej_std": "https://raw.githubusercontent.com/Krest-Neva/Shadowrocket/refs/heads/main/REJECT_RULES/REJECT_RULES_STD.list"
}

EXCLUDE_KEYWORDS = [
    "ads", "analytics", "tracker", "tracking", "tracer", "metrics",
    "metrica", "metrika", "telemetry", "pixel", "beacon", "adserver",
    "doubleclick", "adjust", "appsflyer", "app-measurement",
    "log-upload", "crash-report", "messenger.yandex", "vetmanager"
]

EXCLUDE_PATTERN = re.compile('|'.join(re.escape(kw) for kw in EXCLUDE_KEYWORDS))

PROTECTED_SUFFIXES = {
    "apple-pki.com", "icloud.com", "icloud-content.com", "mzstatic.com",
    "push.apple.com", "appleid.apple.com", "simplex.im", "simplexonflux.com",
    "telegram.org", "t.me", "telegram.me", "telegra.ph", "tg.dev",
    "cdn.telegram-cdn.org", "whatsapp.com", "whatsapp.net", "wa.me",
    "youtube.com", "youtu.be", "ytimg.com", "googlevideo.com",
    "youtube.googleapis.com", "ls-apple.com.akadns.net", "ess-apple.com.akadns.net"
}

PROTECTED_DOMAINS = {
    "raw.githubusercontent.com", "cdn-apple.com", "apple-dns.net", "ls.apple.com",
    "facetime.apple.com", "stun.apple.com", "apple.com", "aaplimg.com",
    "github.com", "githubusercontent.com", "githubassets.com", "google.com",
    "gstatic.com", "ggpht.com", "firebase.google.com", "googleapis.com",
    "firebaseio.com", "openai.com", "chatgpt.com", "oaistatic.com",
    "oaiusercontent.com", "microsoft.com", "windows.com", "windowsupdate.com",
    "msftconnecttest.com", "msftncsi.com", "azure.com", "azureedge.net",
    "azurefd.net", "amazon.com", "amazonaws.com", "aws.amazon.com",
    "cloudfront.net", "cloudflare.com", "fastly.net", "cdn.jsdelivr.net",
    "unpkg.com", "akamaiedge.net", "akamaized.net", "akamai.net", "auth0.com",
    "okta.com", "login.microsoftonline.com", "accounts.google.com",
    "hcaptcha.com", "challenges.cloudflare.com", "recaptcha.net",
    "facebook.com", "fb.com", "fbcdn.net", "graph.instagram.com",
    "graph.facebook.com", "instagram.com", "cdninstagram.com", "discord.com",
    "discordapp.com", "duckduckgo.com", "ddg.co", "giphy.com", "habr.com",
    "yandex.ru", "yandex.com", "yandex.by", "yandex.kz", "mail.yandex.ru",
    "passport.yandex.ru", "api.yandex.ru", "mail.ru", "e.mail.ru", "vk.com",
    "api.vk.com", "ozon.ru", "wildberries.ru", "avito.ru", "avito.st",
    "hh.ru", "sberbank.ru", "online.sberbank.ru", "alfabank.ru", "alfa.ru",
    "tbank.ru", "tinkoff.ru", "vtb.ru", "finam.ru", "63.ru", "aif.ru",
    "amic.ru", "angliya.com", "ap22.ru", "asiaplustj.info", "avesta.tj",
    "azerisport.com", "belta.by", "championat.com", "chita.ru", "citilink.ru",
    "civil.ge", "click-or-die.ru", "dni.ru", "e1.ru", "echo.az",
    "echo.msk.ru", "fedpress.ru", "f1news.ru", "fontanka.ru", "gazeta.ru",
    "gazetanovgorod.ru", "golosarmenii.am", "government.ru",
    "gundogar-news.com", "hronikatm.com", "infoabad.com", "inosmi.ru",
    "interfax.ru", "itogi.ru", "izvestia.ru", "kp.ru", "kremlin.ru",
    "lenta.ru", "matchtv.ru", "meduza.io", "mn.ru", "ng.ru",
    "novayagazeta.ru", "newsvl.ru", "og.ru", "ok.ru", "politikus.info",
    "ppt.ru", "pressball.by", "progorodsamara.ru", "radiomayak.ru",
    "rbc.ru", "rg.ru", "ria.ru", "rskrf.ru", "rutube.ru", "sovsport.ru",
    "sport-express.ru", "sport24.ru", "sportbox.ru", "sports.ru",
    "tass.ru", "trud.ru", "utro.ru", "ytro.ru", "zr.ru", "one.one.one.one",
    "dns.google", "quad9.net", "npmjs.org", "pypi.org", "gitlab.com",
    "bitbucket.org", "android.com", "yastatic.net", "dft.ru", "afisha.ru",
    "gosuslugi.ru", "aviasales.ru", "kinopoisk.ru"
}

DNS_SERVERS = ["8.8.8.8", "8.8.4.4", "94.140.14.14", "94.140.15.15", "1.1.1.1"]
HEADERS = {'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1'}

INVALID_CHARS = set('?|=*(),&:[]/\\%#_')
DANGEROUS_TLDS = {"html", "xml", "gif", "js", "php", "css", "png", "jpg"}

_progress_state = {}

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

def progress_bar(prefix, current, total, width=8):
    if total <= 0:
        return
    now = time.time()
    if "[dl]" in prefix:
        state = _progress_state.get(prefix)
        if state is not None and current != total and now - state < 0.25:
            return
    frac = current / float(total)
    filled = int(round(width * frac))
    bar = '=' * filled + '-' * (width - filled)
    pct = round(frac * 100.0, 1)
    sys.stdout.write("\r" + prefix + " [" + bar + "] " + str(current) + "/" + str(total) + " (" + str(pct) + "%)")
    sys.stdout.flush()
    if current == total:
        sys.stdout.write("\n")
        sys.stdout.flush()
    if "[dl]" in prefix:
        _progress_state[prefix] = now

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

def parse_whitelist_line(line):
    line = line.strip()
    if not line or line.startswith(('#', '!', ';', '//', '[')):
        return None
    if '#' in line:
        line = line.split('#', 1)[0].strip()
    if not line:
        return None
    if line.startswith('.'):
        return line.lstrip('.').lower().rstrip('.') or None
    if ',' in line:
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
    clean = re.sub(r'^https?://', '', line)
    clean = clean.split('/')[0].split(':')[0].split('*')[0].strip().strip('.')
    return clean.lower() if clean else None

def _validate_content(data):
    if len(data) <= 100:
        return False
    if '<html' in data[:300].lower():
        return False
    return True

def download_urllib(url, label, timeout=30):
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        content_length = resp.getheader('Content-Length')
        try:
            total = int(content_length) if content_length else None
        except Exception:
            total = None
        out = bytearray()
        read = 0
        last_report = 0.0
        while True:
            chunk = resp.read(8192)
            if not chunk:
                break
            out.extend(chunk)
            read += len(chunk)
            if total:
                progress_bar("  [dl] " + label, min(read, total), total)
            else:
                now = time.time()
                if now - last_report >= 0.25:
                    sys.stdout.write("\r  [dl] " + label + " " + str(read // 1024) + " KB\033[K")
                    sys.stdout.flush()
                    last_report = now
        if total and read < total * 0.95:
            raise Exception("Incomplete: " + str(read) + "/" + str(total))
        if not total:
            sys.stdout.write("\n")
        data = out.decode('utf-8', errors='ignore')
        if _validate_content(data):
            return data.splitlines(), "urllib"
    return [], None

def download_curl_file(url, timeout=15, extra_args=None):
    tmp = tempfile.NamedTemporaryFile(delete=False)
    tmp.close()
    cmd = ['curl', '-s', '-L', '--fail', '--show-error', '-k', '-A', HEADERS['User-Agent']]
    if extra_args:
        cmd += extra_args
    cmd += ['-o', tmp.name, url]
    try:
        proc = subprocess.run(cmd, timeout=timeout)
        if proc.returncode == 0:
            with open(tmp.name, 'rb') as f:
                data = f.read().decode('utf-8', errors='ignore')
            if _validate_content(data):
                return data.splitlines(), "curl " + (" ".join(extra_args) if extra_args else "default")
    except Exception:
        pass
    finally:
        try:
            os.unlink(tmp.name)
        except Exception:
            pass
    return [], None

def download_variants(url):
    ua = HEADERS['User-Agent']
    variants = [
        (['curl', '-s', '-L', '-k', '-A', ua, url], False, "curl default"),
        (['curl', '-s', '-L', '-k', '--http1.1', '-A', ua, url], False, "curl http1.1"),
        (['curl', '-s', '-L', '-k', '--http2', '-A', ua, url], False, "curl http2"),
        (['curl', '-s', '-L', '-k', '--compressed', '-A', ua, url], False, "curl compressed"),
        (['curl', '-s', '-L', '-k', '--ipv4', '-A', ua, url], False, "curl ipv4"),
        (['curl', '-s', '-L', '-k', '--ipv6', '-A', ua, url], False, "curl ipv6"),
        (['curl', '-s', '-L', '-k', '-A', 'Wget/1.20', url], False, "curl UA=Wget"),
    ]
    if shutil.which('wget'):
        variants.append((['wget', '-q', '--no-check-certificate', '-O', '-', url], False, "wget"))
    if shutil.which('aria2c'):
        variants.append((['aria2c', '-q', '--summary-interval=1', '-x', '4', '-o', 'aria_tmp_dl', url], True, "aria2c"))

    for cmd, is_file_writer, descr in variants:
        if not shutil.which(cmd[0]):
            continue
        try:
            sys.stdout.write("\r    [try] " + descr + "...\033[K")
            sys.stdout.flush()
            if not is_file_writer:
                tmp = tempfile.NamedTemporaryFile(delete=False)
                tmp.close()
                try:
                    with open(tmp.name, 'wb') as f:
                        proc = subprocess.run(cmd, stdout=f, stderr=subprocess.DEVNULL, timeout=20)
                    if proc.returncode == 0:
                        with open(tmp.name, 'rb') as f:
                            data = f.read().decode('utf-8', errors='ignore')
                        if _validate_content(data):
                            return data.splitlines(), descr
                finally:
                    try:
                        os.unlink(tmp.name)
                    except Exception:
                        pass
            else:
                proc = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=20)
                if proc.returncode == 0:
                    try:
                        with open('aria_tmp_dl', 'rb') as f:
                            data = f.read().decode('utf-8', errors='ignore')
                        if _validate_content(data):
                            return data.splitlines(), descr
                    finally:
                        try:
                            os.unlink('aria_tmp_dl')
                        except Exception:
                            pass
        except Exception:
            continue
    return [], None

def download(url, label):
    for attempt in range(1, 4):
        for fn, args in [
            (download_urllib, (url, label)),
            (download_curl_file, (url,)),
        ]:
            try:
                lines, method = fn(*args)
                if lines:
                    print("  [+] " + label + ": " + str(len(lines)) + " строк (" + method + ")")
                    return lines
            except Exception:
                pass
        try:
            lines, method = download_variants(url)
            if lines:
                print("  [+] " + label + ": " + str(len(lines)) + " строк (" + method + ")")
                return lines
        except Exception:
            pass
        sys.stdout.write("\r    [!] попытка " + str(attempt) + " не удалась, повтор...\033[K\n")
        sys.stdout.flush()
        time.sleep(1 + attempt * 1.5)
    print("  [!] Не удалось скачать: " + label)
    return []

def download_all_whitelists():
    print("[*] ФАЗА 1/3: Загрузка белых списков...")
    raw = {}
    failed = []
    for name, urls in WHITE_URLS.items():
        url_list = urls if isinstance(urls, list) else [urls]
        lines = []
        for u in url_list:
            lines = download(u, name)
            if lines:
                break
        if lines:
            raw[name] = lines
        else:
            failed.append(name)
    return raw, failed

def download_blacklist():
    print("[*] ФАЗА 2/3: Загрузка основного списка...")
    lines = download(SOURCE_URL, "oisd_nsfw")
    return lines

def parse_whitelists(raw):
    print("[*] ФАЗА 3/3: Парсинг и генерация...")
    print("  [*] Парсинг белых списков...")
    whitelist_suffixes = set(PROTECTED_SUFFIXES)
    whitelist_exact = set(PROTECTED_DOMAINS)

    for name, lines in raw.items():
        count = 0
        total = len(lines)
        for i, raw_line in enumerate(lines, 1):
            if i % STEP == 0 or i == total:
                progress_bar("  [wl] " + name, i, total)
            d = parse_whitelist_line(raw_line)
            if not d or not is_valid_domain(d):
                continue
            whitelist_suffixes.add(d)
            count += 1
        print("  -> " + name + ": " + str(count) + " доменов")

    print("  -> Встроенный защищённый список: " + str(len(PROTECTED_SUFFIXES) + len(PROTECTED_DOMAINS)) + " записей")
    return whitelist_suffixes, whitelist_exact

def remove_redundant(domains):
    s = set(domains)
    result = set()
    for d in s:
        parts = d.split('.')
        if any('.'.join(parts[i:]) in s for i in range(1, len(parts))):
            continue
        result.add(d)
    return result

def is_covered_by_whitelist(domain, whitelist_suffixes, whitelist_exact):
    if domain in whitelist_exact:
        return True
    parts = domain.split('.')
    for i in range(len(parts)):
        if '.'.join(parts[i:]) in whitelist_suffixes:
            return True
    return False

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
        if len(bases) == 1 and len(next(iter(bases))) == 0:
            return None
        alts.append(trie_to_regex(build_trie(bases)) + re.escape(suffix))
    if not alts:
        return ''
    if len(alts) == 1:
        return alts[0]
    return '(?:' + '|'.join(alts) + ')'

def write_log(total_lines, valid, redundant, final, regex_len, skipped, white_count, excluded_count, status):
    try:
        with open(LOG_FILE, 'w', encoding='utf-8') as f:
            f.write("Log generated at: " + time.ctime() + "\n")
            f.write("=" * 60 + "\n")
            f.write("Source: " + SOURCE_URL + "\n")
            f.write("-" * 60 + "\n")
            f.write("Downloaded lines:       " + str(total_lines) + "\n")
            f.write("Valid domains:          " + str(valid) + "\n")
            f.write("Skipped (invalid):      " + str(skipped) + "\n")
            f.write("Excluded by keywords:   " + str(excluded_count) + "\n")
            f.write("Whitelist domains:      " + str(white_count) + "\n")
            f.write("After all filters:      " + str(redundant) + "\n")
            f.write("Unique final domains:   " + str(final) + "\n")
            f.write("Regex length (chars):   " + str(regex_len) + "\n")
            f.write("Status:                 " + status + "\n")
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

    white_raw, failed_white = download_all_whitelists()
    if failed_white:
        print("[!] Пропущены белые списки: " + ", ".join(failed_white))
    if not white_raw:
        print("[!] Ни один белый список не скачался. Продолжаем с встроенным защищённым списком.")

    black_lines = download_blacklist()
    if not black_lines:
        print("[!] Не удалось скачать основной список")
        sys.exit(1)

    print("[*] Все списки загружены. Начинаем обработку.")
    print("=" * 60)

    whitelist_suffixes, whitelist_exact = parse_whitelists(white_raw)
    white_count = len(whitelist_suffixes) + len(whitelist_exact)
    print("[*] Всего в белых списках: " + str(white_count))

    domains = set()
    skipped = 0
    excluded = 0
    total = len(black_lines)
    for i, raw_line in enumerate(black_lines, 1):
        if i % STEP == 0 or i == total:
            progress_bar("  [parse]", i, total)
        d = parse_line(raw_line)
        if not d:
            continue
        if not is_valid_domain(d):
            skipped += 1
            continue
        if EXCLUDE_PATTERN.search(d):
            excluded += 1
            continue
        if is_covered_by_whitelist(d, whitelist_suffixes, whitelist_exact):
            continue
        domains.add(d)

    print("[*] Валидных доменов: " + str(len(domains)) + " | отброшено: " + str(skipped) + " | исключено по ключам: " + str(excluded))

    valid_count = len(domains)
    domains = remove_redundant(domains)
    print("[*] После удаления избыточных: " + str(len(domains)))

    domains = sorted(domains)
    regex = build_regex(domains)
    if regex is None:
        print("[!] ОШИБКА: регулярка вырождается в голый TLD.")
        write_log(total, valid_count, len(domains), len(domains), 0, skipped, white_count, excluded, "FAILED: TLD-only regex")
        sys.exit(1)

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

    write_log(total, valid_count, len(domains), len(domains), len(pattern), skipped, white_count, excluded, "OK")
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
echo "[*] MITM.list сохранён отдельно."
echo "[*] Готово."
