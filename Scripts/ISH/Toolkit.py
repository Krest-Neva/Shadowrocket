#!/bin/sh
# ============================================================
# SHADOWROCKET TOOLKIT
# Единый скрипт для iSH: AdBlock, SQLiteTXT, SpyLog, SubManager
# ============================================================

clear

# ============================================================
# Настройка DNS
# ============================================================
echo "[*] Настройка DNS..."
echo "nameserver 8.8.8.8" > /etc/resolv.conf
echo "nameserver 8.8.4.4" >> /etc/resolv.conf
echo "nameserver 94.140.14.14" >> /etc/resolv.conf
echo "nameserver 94.140.15.15" >> /etc/resolv.conf
echo "nameserver 1.1.1.1" >> /etc/resolv.conf

# ============================================================
# Проверка соединения
# ============================================================
echo "[*] Проверка соединения..."
while ! ping -c 3 google.com > /dev/null 2>&1; do
    echo "[!] Нет подключения. Повтор через 5 сек..."
    sleep 5
done
echo "[+] Интернет доступен."

# ============================================================
# Обновление системы
# ============================================================
echo "[*] Обновление системы..."
apk update
apk upgrade

# ============================================================
# Установка всех зависимостей одним блоком
# ============================================================
echo "[*] Установка всех зависимостей..."
apk add --no-cache \
    python3 py3-pip curl wget aria2 openssl ca-certificates \
    bind-tools bash sqlite git py3-chardet

# ============================================================
# Создание структуры папок
# ============================================================
echo "[*] Настройка папок..."
BASE=$HOME/Shadowrocket
mkdir -p $BASE/AdBlock
mkdir -p $BASE/SQLiteTXT/Input $BASE/SQLiteTXT/Output
mkdir -p $BASE/SpyLog/Input $BASE/SpyLog/Output
mkdir -p $BASE/SubManager/Input $BASE/SubManager/Output $BASE/SubManager/Backups $BASE/SubManager/Routing

# ============================================================
# Создание AdBlock.py
# ============================================================
cat << 'ADBLOCK_END' > $BASE/AdBlock.py
# ============================================================
# ADBLOCK SCRIPT
# Формирует REJECT_RULES для Shadowrocket.
# Поддерживает режимы default и custom.
# Нормализатор понимает Adblock Plus, hosts, dnsmasq, unbound,
# Pi-hole, domain-only, Surge.
# ============================================================

import urllib.request
import subprocess
import re
import time
import os
import sys
import tempfile
import math
import shutil
import ipaddress

# Блок выбора режима
def choose_mode():
    print("\n" + "="*50)
    print("ADBLOCK: выбор режима")
    print("  1 - По умолчанию")
    print("  2 - Custom")
    ch = input("Ваш выбор [1]: ").strip()
    return "custom" if ch == "2" else "default"

MODE = choose_mode()

# Блок выбора списков OISD
oisd_choice = '3'
if MODE == "default":
    while True:
        print("\n" + "="*45)
        print("Настройка списков OISD")
        print("1 - Обычные")
        print("2 - Короткие")
        print("3 - Скачать все")
        raw_oisd = input("Ваш выбор [3]: ").strip()
        oisd_choice = raw_oisd if raw_oisd in ('1', '2', '3') else '3'
        mapping = {'1': 'Обычные', '2': 'Короткие', '3': 'Скачать все'}
        print(f" -> Выбрано: {mapping[oisd_choice]}")
        confirm = input("Подтвердить? (y/n) [y]: ").strip().lower()
        if confirm in ('y', 'yes', ''):
            break

# Блок URL списков
oisd_main_url = "https://dl.oisd.nl/oisd_big_surge.list"
oisd_nsfw_url = "https://dl.oisd.nl/oisd_nsfw_surge.list"
oisd_small_url = "https://dl.oisd.nl/oisd_small_surge.list"
oisd_nsfw_small_url = "https://dl.oisd.nl/oisd_nsfw_small_surge.list"
print("="*45 + "\n")

SCRIPT_START_TIME = time.time()

# Стандартные чёрные списки
urls = {}
white_urls = {}
whitelist_clean = {}

if MODE == "default":
    urls = {
        "1) Loyalsoldier": [
            "https://raw.githubusercontent.com/Loyalsoldier/surge-rules/release/ruleset/reject.txt",
            "https://cdn.jsdelivr.net/gh/Loyalsoldier/surge-rules@release/ruleset/reject.txt",
            "https://raw.githubusercontent.com/Loyalsoldier/surge-rules/release/reject.txt",
            "https://cdn.jsdelivr.net/gh/Loyalsoldier/surge-rules@release/reject.txt"
        ],
        "2) AdGuard (Base)": "https://filters.adtidy.org/ios/filters/15_optimized.txt",
        "3) Дополнение к AdGuard 1": "https://filters.adtidy.org/ios/filters/2_optimized.txt",
        "4) Дополнение к AdGuard 2": "https://filters.adtidy.org/ios/filters/3_optimized.txt",
        "5) Дополнение к AdGuard 3.1": "https://pgl.yoyo.org/adservers/serverlist.php?hostformat=adblockplus&showintro=0&mimetype=plaintext",
        "6) Фильтр мобильной рекламы": "https://filters.adtidy.org/ios/filters/11_optimized.txt",
        "7) Дополнительный фильтр (RU)": "https://filters.adtidy.org/ios/filters/1_optimized.txt",
        "8) Дополнительный фильтр для блокировки трекеров": [
            "https://easylist-downloads.adblockplus.org/cntblock.txt",
            "https://raw.githubusercontent.com/easylist/easylist/master/easyprivacy/easyprivacy_trackers.txt"
        ],
        "9) Анти фишинг": "https://malware-filter.gitlab.io/malware-filter/phishing-filter-ag.txt"
    }

    if oisd_choice in ('1', '3'):
        urls["10.1) OISD"] = [oisd_main_url]
        urls["10.2) OISD NSFW"] = [oisd_nsfw_url]
    if oisd_choice in ('2', '3'):
        urls["10.3) OISD Small"] = [oisd_small_url]
        urls["10.4) OISD NSFW Small"] = [oisd_nsfw_small_url]

    urls["11) HaGeZi Pro"] = [
        "https://raw.githubusercontent.com/hagezi/dns-blocklists/main/adblock/pro.txt",
        "https://cdn.jsdelivr.net/gh/hagezi/dns-blocklists@main/adblock/pro.txt"
    ]
    urls["12) StevenBlack Hosts"] = [
        "https://raw.githubusercontent.com/StevenBlack/hosts/master/hosts",
        "https://cdn.jsdelivr.net/gh/StevenBlack/hosts@master/hosts"
    ]

    white_urls = {
        "Белый список 1 (Direct)": [
            "https://raw.githubusercontent.com/Loyalsoldier/surge-rules/release/ruleset/direct.txt",
            "https://cdn.jsdelivr.net/gh/Loyalsoldier/surge-rules@release/ruleset/direct.txt",
            "https://raw.githubusercontent.com/Loyalsoldier/surge-rules/release/direct.txt",
            "https://cdn.jsdelivr.net/gh/Loyalsoldier/surge-rules@release/direct.txt"
        ],
        "Белый список 2 (Proxy)": [
            "https://raw.githubusercontent.com/Loyalsoldier/surge-rules/release/ruleset/proxy.txt",
            "https://cdn.jsdelivr.net/gh/Loyalsoldier/surge-rules@release/ruleset/proxy.txt",
            "https://raw.githubusercontent.com/Loyalsoldier/surge-rules/release/proxy.txt",
            "https://cdn.jsdelivr.net/gh/Loyalsoldier/surge-rules@release/proxy.txt"
        ],
        "Белый список Apple": [
            "https://raw.githubusercontent.com/Loyalsoldier/surge-rules/release/ruleset/apple.txt",
            "https://cdn.jsdelivr.net/gh/Loyalsoldier/surge-rules@release/ruleset/apple.txt",
            "https://raw.githubusercontent.com/Loyalsoldier/surge-rules/release/apple.txt",
            "https://cdn.jsdelivr.net/gh/Loyalsoldier/surge-rules@release/apple.txt"
        ],
        "Белый список iCloud": [
            "https://raw.githubusercontent.com/Loyalsoldier/surge-rules/release/ruleset/icloud.txt",
            "https://cdn.jsdelivr.net/gh/Loyalsoldier/surge-rules@release/ruleset/icloud.txt",
            "https://raw.githubusercontent.com/Loyalsoldier/surge-rules/release/icloud.txt",
            "https://cdn.jsdelivr.net/gh/Loyalsoldier/surge-rules@release/icloud.txt"
        ],
        "Белый список AnudeepND (Global)": [
            "https://raw.githubusercontent.com/anudeepND/whitelist/master/domains/whitelist.txt",
            "https://cdn.jsdelivr.net/gh/anudeepND/whitelist@master/domains/whitelist.txt"
        ],
        "РФ БС для моб.": [
            "https://cdn.jsdelivr.net/gh/hxehex/russia-mobile-internet-whitelist@main/whitelist.txt",
            "https://raw.githubusercontent.com/hxehex/russia-mobile-internet-whitelist/main/whitelist.txt"
        ],
        "Прочие 1": "https://raw.githubusercontent.com/chebur-net/russia-mobile-whitelist/refs/heads/main/moscow-tele2/domains.txt",
        "Прочие 2": "https://raw.githubusercontent.com/chebur-net/russia-mobile-whitelist/refs/heads/main/spb-tele2/domains.txt"
    }

    # OISD по умолчанию не фильтруется белыми списками
    for name in urls:
        whitelist_clean[name] = not ("OISD" in name)

else:
    # Режим custom: пользователь вводит свои списки
    print("\n=== CUSTOM: ввод чёрных списков ===")
    print("Вводите по одному. Пустое имя — конец ввода.")
    idx = 1
    while True:
        name = input(f"  Имя чёрного списка #{idx} (Enter — конец): ").strip()
        if not name:
            break
        link = input("    URL(ы) через ';': ").strip()
        if not link:
            continue
        parts = [p.strip() for p in link.split(';') if p.strip()]
        urls[name] = parts
        cl = input("    Очищать белыми списками? (y/n) [n]: ").strip().lower()
        whitelist_clean[name] = cl in ('y', 'yes')
        idx += 1

    print("\n=== CUSTOM: ввод белых списков ===")
    idx = 1
    while True:
        name = input(f"  Имя белого списка #{idx} (Enter — конец): ").strip()
        if not name:
            break
        link = input("    URL(ы) через ';': ").strip()
        if not link:
            continue
        parts = [p.strip() for p in link.split(';') if p.strip()]
        white_urls[name] = parts
        idx += 1

# Блок ключевых слов-исключений
exclude_keywords = [
    "ads", "analytics", "tracker", "tracking", "tracer", "metrics", "metrica", "metrika", "telemetry", "pixel", "beacon", "adserver", "doubleclick", "adjust", "appsflyer", "app-measurement", "log-upload", "crash-report", "messenger.yandex", "vetmanager"
]
exclude_pattern = re.compile('|'.join(re.escape(kw) for kw in exclude_keywords))

INVALID_CHARS = set('?|=*(),&:[]/\\%#_')

# Блок защищённых суффиксов
protected_suffixes = {
   "apple-pki.com", "icloud.com", "icloud-content.com", "mzstatic.com", "push.apple.com", "appleid.apple.com",
    "simplex.im", "simplexonflux.com", "telegram.org", "t.me", "telegram.me", "telegra.ph", "tg.dev", "cdn.telegram-cdn.org",
    "whatsapp.com", "whatsapp.net", "wa.me", "youtube.com", "youtu.be", "ytimg.com", "googlevideo.com", "youtube.googleapis.com", "ls-apple.com.akadns.net", "ess-apple.com.akadns.net"
}

# Блок защищённых доменов
protected_domains = {
    "raw.githubusercontent.com", "cdn-apple.com", "apple-dns.net", "ls.apple.com", "facetime.apple.com", "stun.apple.com", "apple.com", "aaplimg.com", "github.com", "githubusercontent.com", "githubassets.com", "google.com", "gstatic.com", "ggpht.com", "firebase.google.com", "googleapis.com", "firebaseio.com", "openai.com", "chatgpt.com", "oaistatic.com", "oaiusercontent.com", "microsoft.com", "windows.com", "windowsupdate.com", "msftconnecttest.com", "msftncsi.com", "azure.com", "azureedge.net", "azurefd.net", "amazon.com", "amazonaws.com", "aws.amazon.com", "cloudfront.net", "cloudflare.com", "fastly.net", "cdn.jsdelivr.net", "unpkg.com", "akamaiedge.net", "akamaized.net", "akamai.net", "auth0.com", "okta.com", "login.microsoftonline.com", "accounts.google.com", "hcaptcha.com", "challenges.cloudflare.com", "recaptcha.net", "facebook.com", "fb.com", "fbcdn.net", "graph.instagram.com", "graph.facebook.com", "instagram.com", "cdninstagram.com", "discord.com", "discordapp.com", "duckduckgo.com", "ddg.co", "giphy.com", "habr.com", "yandex.ru", "yandex.com", "yandex.by", "yandex.kz", "mail.yandex.ru", "passport.yandex.ru", "api.yandex.ru", "mail.ru", "e.mail.ru", "vk.com", "api.vk.com", "ozon.ru", "wildberries.ru", "avito.ru", "avito.st", "hh.ru", "sberbank.ru", "online.sberbank.ru", "alfabank.ru", "alfa.ru", "tbank.ru", "tinkoff.ru", "vtb.ru", "finam.ru", "63.ru", "aif.ru", "amic.ru", "angliya.com", "ap22.ru", "asiaplustj.info", "avesta.tj", "azerisport.com", "belta.by", "championat.com", "chita.ru", "citilink.ru", "civil.ge", "click-or-die.ru", "dni.ru", "e1.ru", "echo.az", "echo.msk.ru", "fedpress.ru", "f1news.ru", "fontanka.ru", "gazeta.ru", "gazetanovgorod.ru", "golosarmenii.am", "government.ru", "gundogar-news.com", "hronikatm.com", "infoabad.com", "inosmi.ru", "interfax.ru", "itogi.ru", "izvestia.ru", "kp.ru", "kremlin.ru", "lenta.ru", "matchtv.ru", "meduza.io", "mn.ru", "ng.ru", "novayagazeta.ru", "newsvl.ru", "og.ru", "ok.ru", "politikus.info", "ppt.ru", "pressball.by", "progorodsamara.ru", "radiomayak.ru", "rbc.ru", "rg.ru", "ria.ru", "rskrf.ru", "rutube.ru", "sovsport.ru", "sport-express.ru", "sport24.ru", "sportbox.ru", "sports.ru", "tass.ru", "trud.ru", "utro.ru", "ytro.ru", "zr.ru", "one.one.one.one", "dns.google", "quad9.net", "npmjs.org", "pypi.org", "gitlab.com", "bitbucket.org", "android.com", "yastatic.net", "dft.ru", "afisha.ru", "gosuslugi.ru", "yandex.ru", "aviasales.ru", "kinopoisk.ru",
}

manual_protected_domains = protected_domains.copy()
manual_protected_suffixes = protected_suffixes.copy()

# Блок принудительно блокируемых суффиксов
forced_block_suffixes = {
    "bit.ly", "tinyurl.com", "t.co", "reurl.cc", "is.gd", "ow.ly", "linktr.ee", "about.me", "campaign-archive.com", "vk.link", "app.link", "mradx.net", "adjust.com", "static.rutubelist.ru", "static.kuper.ru", "static-origin.kuper.ru", "max.ru", "zztfly.com", "sub.scroogethebest.com", "apmplus.volces.com", "googleadservices.com", "doubleclick.net", "googlesyndication.com", "google-analytics.com", "googletagmanager.com", "app-measurement.com", "crashlytics.com", "branch.io", "amplitude.com", "mixpanel.com", "hotjar.com", "yandexmetrica.ru", "mc.yandex.ru", "metrika.yandex.ru", "top.mail.ru", "adriver.ru", "adfox.ru", "pixel.facebook.com", "analytics.facebook.com", "connect.facebook.net", "tr.facebook.com", "firebaselogging-pa.googleapis.com"
}
forced_block_domains = set()

plus_forced_block_suffixes = {"yabuchka.net", "xcelebs.ru"}

protected_ips = {
    "1.1.1.1", "1.0.0.1", "8.8.8.8", "8.8.4.4", "9.9.9.9", "149.112.112.112", "94.140.14.14", "94.140.15.15", "94.140.14.15", "94.140.14.1", "76.76.2.0", "76.76.10.0", "208.67.222.222", "208.67.220.220", "212.13.114.252", "212.111.75.55", "195.230.90.26", "194.247.146.200", "195.2.83.118", "195.133.107.200", "195.146.64.44", "195.230.90.32", "194.67.20.14"
}

forced_block_ips = {
    "178.248.232.0/21", "82.148.11.0/24", "185.15.56.0/22", "91.223.116.0/22"
}

dangerous_tlds = {"com", "net", "org", "ru", "site", "info", "xyz", "bid", "club", "shop", "html", "xml", "gif", "js", "php", "top"}

AGGREGATE_THRESHOLD = 0

headers = {'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1'}
ip_regex = re.compile(r'^(\d{1,3}(?:\.\d{1,3}){3})(?:/\d{1,2})?$')

errors_output_file = "LogsAdBlockScript"
download_report = {}
failed_lists = []
white_download_report = {}
failed_white_lists = []

white_raw_data = {}
black_raw_data = {}

all_domains = set()
all_ips = set()
oisd_domains = set()
oisd_ips = set()
nsfw_domains = set()
nsfw_ips = set()
oisd_small_domains = set()
oisd_small_ips = set()
nsfw_small_domains = set()
nsfw_small_ips = set()

optimized_domains = set()
optimized_domains_plus = set()
optimized_domains_sm = set()
optimized_domains_plus_sm = set()
final_list_len = 0
final_list_plus_len = 0
final_list_sm_len = 0
final_list_plus_sm_len = 0

stats = {"excluded": 0, "junk": 0, "protected_exact": 0, "protected_suffix": 0}
errors = []

DNS_SERVERS = [
    "8.8.8.8",
    "8.8.4.4",
    "94.140.14.14",
    "94.140.15.15",
    "1.1.1.1"
]

_progress_state = {}

# Блок определения режима фильтрации белыми
def should_filter_with_whitelist(name):
    if MODE == "default":
        return not ("OISD" in name)
    return whitelist_clean.get(name, True)

# Блок настройки DNS и проверки сети
def setup_dns_and_test():
    while True:
        sys.stdout.write("\r    [net] Настройка DNS...\033[K")
        sys.stdout.flush()
        try:
            with open("/etc/resolv.conf", "w") as f:
                for dns in DNS_SERVERS:
                    f.write(f"nameserver {dns}\n")
            result = subprocess.run(
                ["ping", "-c", "3", "google.com"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=5
            )
            if result.returncode == 0:
                sys.stdout.write("\r    [net] Интернет доступен\033[K")
                sys.stdout.flush()
                return True
            sys.stdout.write("\r    [net] Ping не прошёл\033[K")
            sys.stdout.flush()
        except Exception as e:
            sys.stdout.write(f"\r    [net] Ошибка проверки сети: {e}\033[K")
            sys.stdout.flush()
        time.sleep(5)

# Блок полной диагностики сети
def full_network_diagnostics():
    print("    [diag] Выполняется полная диагностика сети...")
    try:
        print("      - Ping 8.8.8.8:")
        subprocess.run(["ping", "-c", "3", "8.8.8.8"])
        print("      - Ping google.com:")
        subprocess.run(["ping", "-c", "3", "google.com"])
        print("      - Текущий resolv.conf:")
        subprocess.run(["cat", "/etc/resolv.conf"])
    except Exception as e:
        print(f"      [!] Ошибка при диагностике: {e}")

# Блок отрисовки прогресс-бара
def print_progress(prefix, current, total, bar_len=5, start_time=None):
    if total <= 0:
        return
    now = time.time()
    if "[dl]" in prefix:
        state = _progress_state.get(prefix)
        if state is not None and current != total and now - state["time"] < 0.25:
            return
    frac = current / float(total)
    filled = int(round(bar_len * frac))
    bar = '=' * filled + '-' * (bar_len - filled)
    pct = frac * 100.0
    elapsed = ''
    if start_time:
        sec = time.time() - start_time
        elapsed = f" | {int(sec)}s"
    sys.stdout.write(f"\r\033[2K{prefix} [{bar}] {current}/{total} ({pct:.1f}%){elapsed}")
    sys.stdout.flush()
    if current == total:
        sys.stdout.write("\n")
        sys.stdout.flush()
    if "[dl]" in prefix:
        _progress_state[prefix] = {"time": now, "current": current}

# Блок скачивания через urllib
def download_with_urllib(url, headers, timeout=30):
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        content_length = resp.getheader('Content-Length')
        try:
            total = int(content_length) if content_length else None
        except Exception:
            total = None
        out = bytearray()
        chunk_size = 8192
        read = 0
        start = time.time()
        last_unknown_report = 0.0
        while True:
            chunk = resp.read(chunk_size)
            if not chunk:
                break
            out.extend(chunk)
            read += len(chunk)
            if total:
                print_progress("  [dl] urllib", min(read, total), total, start_time=start)
            else:
                now = time.time()
                if now - last_unknown_report >= 0.25:
                    kb = read // 1024
                    sys.stdout.write(f"\r\033[2K  [dl] urllib {kb} KB")
                    sys.stdout.flush()
                    last_unknown_report = now
        if total and read < total * 0.95:
            raise Exception(f"Incomplete download: {read}/{total} bytes")
        if not total:
            sys.stdout.write("\n")
        return out.decode('utf-8', errors='ignore').splitlines(), "urllib"

# Блок скачивания через curl в файл
def download_with_curl_to_file(url, headers, timeout=15, curl_args=None):
    tmp = tempfile.NamedTemporaryFile(delete=False)
    tmp.close()
    base = ['curl', '-s', '-L', '--fail', '--show-error', '-A', headers['User-Agent']]
    if curl_args:
        cmd = base + curl_args + ['-o', tmp.name, url]
    else:
        cmd = base + ['-o', tmp.name, url]
    sys.stdout.write(f"\r    [dl] curl: {url[:50]}...\033[K")
    sys.stdout.flush()
    try:
        proc = subprocess.run(cmd, timeout=timeout)
        if proc.returncode == 0:
            with open(tmp.name, 'rb') as f:
                data = f.read().decode('utf-8', errors='ignore').splitlines()
            return data, "curl " + (" ".join(curl_args) if curl_args else "default")
        else:
            return [], None
    except Exception:
        return [], None
    finally:
        try:
            os.unlink(tmp.name)
        except Exception:
            pass

# Блок перебора вариантов команд скачивания
def try_command_variants(url):
    ua = headers['User-Agent']
    variants = []
    curl_common = ['curl', '-s', '-L', '-k', '-A', ua]
    variants.append((curl_common + [url], False, "curl default"))
    variants.append((curl_common + ['--http1.1', url], False, "curl http1.1"))
    variants.append((curl_common + ['--http2', url], False, "curl http2"))
    variants.append((curl_common + ['--compressed', url], False, "curl compressed"))
    variants.append((curl_common + ['--ipv4', url], False, "curl ipv4"))
    variants.append((curl_common + ['--ipv6', url], False, "curl ipv6"))
    variants.append((['curl', '-s', '-L', '-k', '-A', 'Wget/1.20', url], False, "curl ua=Wget"))

    if shutil.which('wget'):
        variants.append((['wget', '-q', '--show-progress', '-O', '-', url], False, "wget stdout"))
        variants.append((['wget', '--no-check-certificate', '-q', '--show-progress', '-O', '-', url], False, "wget no-check"))

    if shutil.which('aria2c'):
        variants.append((['aria2c', '-q', '--summary-interval=1', '-x', '4', '-o', 'aria_tmp_dl', url], True, "aria2c"))

    for cmd, is_file_writer, descr in variants:
        if not shutil.which(cmd[0]):
            continue
        try:
            sys.stdout.write(f"\r    [attempt] running: {cmd[0]}... ({descr})\033[K")
            sys.stdout.flush()
            if not is_file_writer:
                tmp = tempfile.NamedTemporaryFile(delete=False)
                tmp.close()
                try:
                    proc = subprocess.run(cmd, stdout=open(tmp.name, 'wb'), stderr=subprocess.DEVNULL, timeout=15)
                    if proc.returncode == 0:
                        with open(tmp.name, 'rb') as f:
                            data = f.read().decode('utf-8', errors='ignore').splitlines()
                        return data, descr
                except Exception:
                    pass
                finally:
                    try:
                        os.unlink(tmp.name)
                    except Exception:
                        pass
            else:
                proc = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=15)
                if proc.returncode == 0:
                    if cmd[0] == 'aria2c':
                        try:
                            with open('aria_tmp_dl', 'rb') as f:
                                data = f.read().decode('utf-8', errors='ignore').splitlines()
                            return data, descr
                        except Exception:
                            pass
                        finally:
                            try:
                                os.unlink('aria_tmp_dl')
                            except Exception:
                                pass
        except Exception:
            continue
    return [], None

# Блок проверки защищённости
def is_protected_full(domain):
    if domain in protected_domains:
        return True, "exact"
    parts = domain.split('.')
    for i in range(len(parts)):
        suffix = '.'.join(parts[i:])
        if suffix in protected_suffixes:
            return True, "suffix"
    return False, None

def is_protected_manual(domain):
    if domain in manual_protected_domains:
        return True, "exact"
    parts = domain.split('.')
    for i in range(len(parts)):
        suffix = '.'.join(parts[i:])
        if suffix in manual_protected_suffixes:
            return True, "suffix"
    return False, None

# Блок валидации домена
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
    if len(parts) == 1:
        return False
    if parts[-1].lower() in dangerous_tlds and len(parts) == 1:
        return False
    return True

# Блок валидации IP
def validate_ip(ip_str):
    try:
        net = ipaddress.ip_network(ip_str, strict=False)
        addr = str(net.network_address)
        if addr.startswith(('0.', '127.', '255.')):
            return None
        return str(net)
    except ValueError:
        return None

# Блок нормализации строк из разных форматов блокировщиков
def normalize_line_for_parser(raw_line):
    s = raw_line.strip()
    if not s:
        return raw_line

    # dnsmasq address=/domain/0.0.0.0
    m = re.match(r'^address=/([^/]+)/', s, re.IGNORECASE)
    if m:
        d = m.group(1).lower().strip('.')
        return d

    # dnsmasq server=/domain/x.x.x.x
    m = re.match(r'^server=/([^/]+)/', s, re.IGNORECASE)
    if m:
        d = m.group(1).lower().strip('.')
        return d

    # unbound local-zone: "domain" always_null
    m = re.match(r'^local-zone:\s*"([^"]+)"', s, re.IGNORECASE)
    if m:
        d = m.group(1).lower().strip('.')
        return d

    # Pi-hole regex /regex/ — пропускаем
    if s.startswith('/') and s.endswith('/') and len(s) > 2:
        return "#__PIHOLE_REGEX_SKIP__"

    return raw_line

# Блок скачивания списка
def download_data(name, url_or_urls):
    print(f"\n  [*] Скачивание: {name}...")
    setup_dns_and_test()
    urls_to_try = url_or_urls if isinstance(url_or_urls, list) else [url_or_urls]

    for url in urls_to_try:
        for attempt in range(1, 4):
            try:
                lines, method = download_with_urllib(url, headers, timeout=30)
                if lines and len(lines) > 10 and not any("<html" in str(l).lower() for l in lines[:15]):
                    print(f"\r  [+] Успешно загружено строк: {len(lines)} (method: {method})\033[K")
                    return lines, method
            except Exception:
                pass

            try:
                lines, method = download_with_curl_to_file(url, headers, timeout=15)
                if lines and len(lines) > 10 and not any("<html" in str(l).lower() for l in lines[:15]):
                    print(f"\r  [+] Успешно загружено строк: {len(lines)} (method: {method})\033[K")
                    return lines, method
            except Exception:
                pass

            try:
                lines, method = try_command_variants(url)
                if lines and len(lines) > 10 and not any("<html" in str(l).lower() for l in lines[:15]):
                    print(f"\r  [+] Успешно загружено строк: {len(lines)} (method: {method})\033[K")
                    return lines, method
            except Exception:
                pass

            sys.stdout.write(f"\r    [!] попытка {attempt} не удалась, повтор через {int(1 + attempt*0.5)}s...\033[K")
            sys.stdout.flush()
            time.sleep(1 + attempt * 0.5)

        full_network_diagnostics()

    print(f"\r  [!] Ошибка: Не удалось скачать {name} ни одним из способов.\033[K")
    return [], None

# Блок записи логов
def save_logs(total_time_val=None):
    try:
        with open(errors_output_file, 'w', encoding='utf-8') as ef:
            ef.write(f"Log generated at: {time.ctime()}\n")
            ef.write("="*60 + "\n")
            ef.write("DOWNLOAD & PARSE REPORT (blacklists)\n")
            ef.write("Source\tStatus\tMethod\tDL Lines\tExtracted (D/IP)\n")
            for name, info in download_report.items():
                ext = f"{info.get('extracted_domains',0)}/{info.get('extracted_ips',0)}"
                ef.write(f"{name}\t{info['status']}\t{info.get('method','N/A')}\t{info.get('lines',0)}\t{ext}\n")

            ef.write("\nDOWNLOAD & PARSE REPORT (whitelists)\n")
            ef.write("Source\tStatus\tMethod\tDL Lines\tExtracted\n")
            for name, info in white_download_report.items():
                ef.write(f"{name}\t{info['status']}\t{info.get('method','N/A')}\t{info.get('lines',0)}\t{info.get('extracted', 0)}\n")

            ef.write("\n" + "="*60 + "\n")
            ef.write("PROTECTED SUFFIXES\n")
            for s in sorted(protected_suffixes):
                ef.write(f"{s}\n")
            ef.write("\nPROTECTED DOMAINS\n")
            for d in sorted(protected_domains):
                ef.write(f"{d}\n")

            ef.write("\n" + "="*60 + "\n")
            ef.write("EXCLUDED BY KEYWORDS\n")
            excluded = [(r,s,o) for r,s,o in errors if r == "excluded_keyword"]
            for reason, src, orig in excluded:
                ef.write(f"{src}\t{orig}\n")

            ef.write("\nJUNK / INVALID LINES\n")
            junk = [(r,s,o) for r,s,o in errors if r.startswith("junk") or r == "skipped_path_rule"]
            for reason, src, orig in junk:
                ef.write(f"{reason}\t{src}\t{orig}\n")

            ef.write("\nPROTECTED ENTRIES\n")
            prot = [(r,s,o) for r,s,o in errors if r.startswith("protected")]
            for reason, src, orig in prot:
                ef.write(f"{reason}\t{src}\t{orig}\n")

            if total_time_val is not None:
                ef.write("\n" + "="*60 + "\n")
                ef.write("ФИНАЛЬНАЯ СТАТИСТИКА\n")
                ef.write("-" * 45 + "\n")
                if oisd_choice in ('1', '3'):
                    ef.write(f"Уникальных доменов (Std/Plus): {len(optimized_domains)} / {len(optimized_domains_plus)}\n")
                if oisd_choice in ('2', '3'):
                    ef.write(f"Уникальных доменов (Sm/PlusSm):{len(optimized_domains_sm)} / {len(optimized_domains_plus_sm)}\n")
                ef.write(f"Уникальных IP-адресов:         {len(all_ips)}\n")
                ef.write(f"Удалено по ключевым словам:    {stats['excluded']}\n")
                ef.write(f"Отсеяно ошибочно добавленных:  {stats['junk']}\n")
                ef.write(f"Защищено (exact):              {stats['protected_exact']}\n")
                ef.write(f"Защищено (suffix):             {stats['protected_suffix']}\n")
                ef.write("-" * 45 + "\n")
                if oisd_choice in ('1', '3'):
                    ef.write(f"ПРАВИЛ В ФАЙЛАХ STD:       {final_list_len}\n")
                    ef.write(f"ПРАВИЛ В ФАЙЛАХ PLUS:      {final_list_plus_len}\n")
                if oisd_choice in ('2', '3'):
                    ef.write(f"ПРАВИЛ В ФАЙЛАХ STD SMALL: {final_list_sm_len}\n")
                    ef.write(f"ПРАВИЛ В ФАЙЛАХ PLUS SMALL:{final_list_plus_sm_len}\n")
                ef.write(f"ВСЕГО ОТБРОШЕНО СТРОК:     {len(errors)}\n")
                ef.write(f"ОБЩЕЕ ВРЕМЯ ВЫПОЛНЕНИЯ:    {total_time_val} сек.\n")
                ef.write("-" * 45 + "\n")

            ef.write(f"\nTotal errors/exclusions: {len(errors)}\n")
    except Exception as e:
        sys.stdout.write(f"\n[!] Не удалось записать {errors_output_file}: {e}\n")

# Блок оптимизации набора доменов
def optimize_domain_set(source_domains, log_prefix):
    sorted_raw = sorted(list(source_domains), key=lambda x: x.count('.'))
    opt_set = set()
    total_to_check = len(sorted_raw)
    start_opt = time.time()

    if AGGREGATE_THRESHOLD and AGGREGATE_THRESHOLD > 1:
        parent_groups = {}
        for idx, d in enumerate(sorted_raw, start=1):
            if idx % 1000 == 0 or idx == total_to_check:
                print_progress(f"  [{log_prefix} group]", idx, total_to_check, start_time=start_opt)
            p = '.'.join(d.split('.')[-2:])
            parent_groups.setdefault(p, []).append(d)
        pg_items = list(parent_groups.items())
        total_pg = len(pg_items)
        start_replace = time.time()
        for i, (parent, members) in enumerate(pg_items, start=1):
            if i % 1000 == 0 or i == total_pg:
                print_progress(f"  [{log_prefix} aggr]", i, total_pg, start_time=start_replace)
            if len(members) >= AGGREGATE_THRESHOLD and not is_protected_full(parent)[0]:
                opt_set.add(parent)
            else:
                for m in members:
                    opt_set.add(m)
    else:
        for idx, d in enumerate(sorted_raw, start=1):
            if idx % 1000 == 0 or idx == total_to_check:
                print_progress(f"  [{log_prefix}]", idx, total_to_check, start_time=start_opt)
            parts = d.split('.')
            is_redundant = False
            for i in range(1, len(parts) - 1):
                if ".".join(parts[i:]) in opt_set:
                    is_redundant = True
                    break
            if not is_redundant:
                opt_set.add(d)
    return opt_set

# Блок сборки и записи файлов
def build_and_write():
    global optimized_domains, optimized_domains_plus, optimized_domains_sm, optimized_domains_plus_sm
    global final_list_len, final_list_plus_len, final_list_sm_len, final_list_plus_sm_len

    def write_chunks(base_name, domains_set, ips_set, log_prefix, is_plus=False):
        final_list = sorted([f"DOMAIN-SUFFIX,{d}" for d in domains_set])
        if is_plus:
            for sfx in plus_forced_block_suffixes:
                if f"DOMAIN-SUFFIX,{sfx}" not in final_list:
                    final_list.append(f"DOMAIN-SUFFIX,{sfx}")
            final_list.sort()

        final_ips = sorted([f"IP-CIDR,{ip}" for ip in ips_set])
        combined = final_list + final_ips
        total = len(combined)
        if total == 0:
            return 0

        with open(f"{base_name}.list", 'w', encoding='utf-8') as full_f:
            for line in combined:
                full_f.write(line + "\n")

        chunk_size = 100000
        chunks = math.ceil(total / chunk_size)
        for i in range(chunks):
            chunk_data = combined[i*chunk_size : (i+1)*chunk_size]
            out_name = f"{base_name}_{i+1}.list"
            start_write = time.time()
            with open(out_name, 'w', encoding='utf-8') as f:
                written = 0
                for line in chunk_data:
                    f.write(line + "\n")
                    written += 1
                    if written % 1000 == 0 or written == len(chunk_data):
                        print_progress(f"  [{log_prefix} {i+1}/{chunks}]", written, len(chunk_data), start_time=start_write)
        return total

    total_rules = 0
    if oisd_choice in ('1', '3'):
        print("[*] Оптимизация стандартного списка...")
        optimized_domains = optimize_domain_set(all_domains | oisd_domains, "opt std")
        print("[*] Оптимизация расширенного списка...")
        optimized_domains_plus = optimize_domain_set(all_domains | oisd_domains | nsfw_domains, "opt plus")

        print("[*] Формирование и запись файлов STD и PLUS...")
        final_list_len = write_chunks("REJECT_RULES", optimized_domains, all_ips | oisd_ips, "write std")
        final_list_plus_len = write_chunks("REJECT_RULES_PLUS", optimized_domains_plus, all_ips | oisd_ips | nsfw_ips, "write plus", is_plus=True)
        total_rules += final_list_len + final_list_plus_len

    if oisd_choice in ('2', '3'):
        print("[*] Оптимизация малого списка...")
        optimized_domains_sm = optimize_domain_set(all_domains | oisd_small_domains, "opt sm")
        print("[*] Оптимизация малого расширенного списка...")
        optimized_domains_plus_sm = optimize_domain_set(all_domains | oisd_small_domains | nsfw_small_domains, "opt plus sm")

        print("[*] Формирование и запись файлов SMALL и PLUS SMALL...")
        final_list_sm_len = write_chunks("REJECT_RULES_SMALL", optimized_domains_sm, all_ips | oisd_small_ips, "write sm")
        final_list_plus_sm_len = write_chunks("REJECT_RULES_PLUS_SMALL", optimized_domains_plus_sm, all_ips | oisd_small_ips | nsfw_small_ips, "write plus sm", is_plus=True)
        total_rules += final_list_sm_len + final_list_plus_sm_len

    return total_rules

# Этап загрузки белых списков
print("\n=== ЭТАП 1: ЗАГРУЗКА БЕЛЫХ СПИСКОВ ===")
for name, url in white_urls.items():
    lines, method = download_data(name, url)
    if lines and method:
        white_raw_data[name] = {"lines": lines, "method": method, "url": url}
        white_download_report[name] = {"status": "ok", "method": method, "lines": len(lines)}
    else:
        white_download_report[name] = {"status": "failed", "method": None, "lines": 0}
        failed_white_lists.append(name)
        sys.stdout.write(f"\r[!] Не удалось скачать белый список: {name}\033[K\n")
        sys.stdout.flush()

# Этап загрузки чёрных списков
print("\n=== ЭТАП 1: ЗАГРУЗКА ЧЁРНЫХ СПИСКОВ ===")
for name, url in urls.items():
    lines, method = download_data(name, url)
    if lines and method:
        black_raw_data[name] = {"lines": lines, "method": method, "url": url}
        download_report[name] = {"status": "ok", "method": method, "lines": len(lines)}
    else:
        download_report[name] = {"status": "failed", "method": None, "lines": 0}
        failed_lists.append(name)
        sys.stdout.write(f"\r[!] Не удалось скачать список: {name}\033[K\n")
        sys.stdout.flush()

# Этап повторной загрузки ошибок
print("\n=== ЭТАП 2: ПОВТОРНАЯ ЗАГРУЗКА ОШИБОК ===")
while failed_lists or failed_white_lists:
    print("\n" + "="*45)
    print("ВНИМАНИЕ: Некоторые списки не удалось скачать:")
    for w in failed_white_lists:
        print(f"  [Белый]  - {w}")
    for b in failed_lists:
        print(f"  [Черный] - {b}")
    print("="*45)

    target = failed_white_lists[0] if failed_white_lists else failed_lists[0]
    is_white = target in failed_white_lists

    print(f"\n[?] Хотите попытаться скачать '{target}' ещё раз?")
    print("  1 - Да")
    print("  2 - Нет")
    print("  3 - Вручную")
    ans = input("Ваш выбор (1/2/3): ").strip()

    if ans == '2':
        if is_white:
            failed_white_lists.remove(target)
        else:
            failed_lists.remove(target)
        continue
    elif ans in ('1', '3'):
        setup_dns_and_test()
        url_to_try = ""
        if ans == '3':
            url_to_try = input("Введите полную ссылку: ").strip()
        else:
            url_to_try = white_urls[target] if is_white else urls[target]

        lines, method = download_data(target, url_to_try)

        if not lines:
            print("  [!] Загрузка снова не удалась.")
            continue

        print(f"  [+] Успешно скачано ({method}). Файл добавлен в очередь.")
        if is_white:
            white_raw_data[target] = {"lines": lines, "method": method, "url": url_to_try}
            failed_white_lists.remove(target)
            white_download_report[target] = {"status": "ok (retry)", "method": method, "lines": len(lines)}
        else:
            black_raw_data[target] = {"lines": lines, "method": method, "url": url_to_try}
            failed_lists.remove(target)
            download_report[target] = {"status": "ok (retry)", "method": method, "lines": len(lines)}
    else:
        print("  [!] Неверный ввод.")

# Этап обработки белых списков
print("\n=== ЭТАП 3: ОБРАБОТКА БЕЛЫХ СПИСКОВ ===")
for name, data_dict in white_raw_data.items():
    lines = data_dict["lines"]
    total_lines = len(lines)
    local_white_count = 0
    start_parse = time.time()
    print(f"\n  [*] Парсинг: {name}...")

    for idx, raw_line in enumerate(lines, start=1):
        if idx % 100 == 0 or idx == total_lines:
            print_progress("  [w-parse]", idx, total_lines, start_time=start_parse)

        line = raw_line.strip()
        if not line or line.startswith(('#', '!')):
            continue

        if line.startswith('.'):
            domain = line.lstrip('.').lower()
            if is_valid_domain(domain):
                protected_suffixes.add(domain)
                local_white_count += 1
            continue

        if ',' in line:
            parts = line.split(',', 1)
            if len(parts) == 2:
                key = parts[0].lower()
                val = parts[1].strip().lower().split('#')[0].strip()
                if key.startswith('domain-suffix'):
                    if is_valid_domain(val):
                        protected_suffixes.add(val)
                        local_white_count += 1
                elif key.startswith('domain'):
                    if is_valid_domain(val):
                        protected_domains.add(val)
                        local_white_count += 1
                else:
                    if is_valid_domain(val):
                        protected_domains.add(val)
                        local_white_count += 1
            continue

        if is_valid_domain(line.lower()):
            protected_domains.add(line.lower())
            local_white_count += 1

    white_download_report[name]["extracted"] = local_white_count
    print(f"  -> Извлечено доменов: {local_white_count}")

apple_keys = [d for d in list(protected_domains) if (d.endswith(".apple.com") or d.startswith("apple-") or d.startswith("icloud")) and d != "apple.com"]
for a in apple_keys:
    protected_domains.discard(a)
    protected_suffixes.add(a)

# Этап обработки чёрных списков
print("\n=== ЭТАП 4: ОБРАБОТКА ЧЁРНЫХ СПИСКОВ ===")
for name, data_dict in black_raw_data.items():
    lines = data_dict["lines"]
    total_lines = len(lines)
    local_domain_count = 0
    local_ip_count = 0
    start_parse = time.time()
    print(f"\n  [*] Парсинг: {name}...")

    is_oisd_nsfw = "10.2) OISD NSFW" in name
    is_oisd_main = "10.1) OISD" in name
    is_oisd_nsfw_sm = "10.4) OISD NSFW Small" in name
    is_oisd_sm = "10.3) OISD Small" in name
    is_any_oisd = "OISD" in name
    use_whitelist = should_filter_with_whitelist(name)

    for idx, raw_line in enumerate(lines, start=1):
        if idx % 100 == 0 or idx == total_lines:
            print_progress("  [b-parse]", idx, total_lines, start_time=start_parse)

        # Предобработка для новых форматов
        normalized = normalize_line_for_parser(raw_line)
        if normalized == "#__PIHOLE_REGEX_SKIP__":
            stats["junk"] += 1
            errors.append(("junk_pihole_regex", name, raw_line))
            continue
        raw_line = normalized

        line = raw_line.strip().lower()

        if not line or line.startswith(('!', '[', '@@')) or '##' in line or '#@#' in line or line.startswith('#'):
            continue

        if exclude_pattern.search(line):
            stats["excluded"] += 1
            errors.append(("excluded_keyword", name, raw_line))
            continue

        if "," in line and not line.startswith("||"):
            parts = [p.strip() for p in line.split(',', 2)]
            if len(parts) >= 2:
                rule_type = parts[0]
                val = parts[1].split('#')[0].strip()
                if "ip-cidr" in rule_type:
                    validated = validate_ip(val)
                    if validated:
                        pure_ip = validated.split('/')[0]
                        is_protected_ip = (pure_ip in protected_ips) if use_whitelist else False
                        if is_protected_ip:
                            stats["protected_exact"] += 1
                            errors.append(("protected_ip", name, val))
                        else:
                            if is_oisd_nsfw:
                                nsfw_ips.add(validated)
                            elif is_oisd_main:
                                oisd_ips.add(validated)
                            elif is_oisd_nsfw_sm:
                                nsfw_small_ips.add(validated)
                            elif is_oisd_sm:
                                oisd_small_ips.add(validated)
                            else:
                                all_ips.add(validated)
                            local_ip_count += 1
                    else:
                        stats["junk"] += 1
                        errors.append(("junk_invalid_ip", name, val))
                elif "domain" in rule_type:
                    if is_valid_domain(val):
                        if use_whitelist:
                            protected, reason = is_protected_full(val)
                        else:
                            protected, reason = False, None
                        if protected:
                            if reason == "exact":
                                stats["protected_exact"] += 1
                            else:
                                stats["protected_suffix"] += 1
                            errors.append((f"protected_{reason}", name, val))
                        else:
                            if is_oisd_nsfw:
                                nsfw_domains.add(val)
                            elif is_oisd_main:
                                oisd_domains.add(val)
                            elif is_oisd_nsfw_sm:
                                nsfw_small_domains.add(val)
                            elif is_oisd_sm:
                                oisd_small_domains.add(val)
                            else:
                                all_domains.add(val)
                            local_domain_count += 1
                    else:
                        stats["junk"] += 1
                        errors.append(("junk_invalid_domain", name, val))
            continue

        clean = line.split('#')[0].strip()
        if clean.startswith(('0.0.0.0 ', '127.0.0.1 ')):
            clean = clean.split(' ', 1)[1].strip()

        clean = re.sub(r'^[|\s]*\|\|', '', clean)
        clean = re.sub(r'^\|', '', clean)
        clean = re.sub(r'^https?://', '', clean)
        clean = re.sub(r'^www\.', '', clean)

        if '/' in clean.split('^')[0].split('$')[0]:
            stats["junk"] += 1
            errors.append(("skipped_path_rule", name, raw_line))
            continue

        clean = clean.split('^')[0].split('$')[0].split(':')[0].split('*')[0].strip()
        clean = clean.strip('.').strip()

        if not clean:
            stats["junk"] += 1
            errors.append(("junk_empty_after_clean", name, raw_line))
            continue

        validated_ip = validate_ip(clean)
        if validated_ip:
            pure_ip = validated_ip.split('/')[0]
            is_protected_ip = (pure_ip in protected_ips) if use_whitelist else False
            if is_protected_ip:
                stats["protected_exact"] += 1
                errors.append(("protected_ip", name, clean))
            else:
                if is_oisd_nsfw:
                    nsfw_ips.add(validated_ip)
                elif is_oisd_main:
                    oisd_ips.add(validated_ip)
                elif is_oisd_nsfw_sm:
                    nsfw_small_ips.add(validated_ip)
                elif is_oisd_sm:
                    oisd_small_ips.add(validated_ip)
                else:
                    all_ips.add(validated_ip)
                local_ip_count += 1
        elif is_valid_domain(clean):
            if use_whitelist:
                protected, reason = is_protected_full(clean)
            else:
                protected, reason = False, None
            if protected:
                if reason == "exact":
                    stats["protected_exact"] += 1
                else:
                    stats["protected_suffix"] += 1
                errors.append((f"protected_{reason}", name, clean))
            else:
                if is_oisd_nsfw:
                    nsfw_domains.add(clean)
                elif is_oisd_main:
                    oisd_domains.add(clean)
                elif is_oisd_nsfw_sm:
                    nsfw_small_domains.add(clean)
                elif is_oisd_sm:
                    oisd_small_domains.add(clean)
                else:
                    all_domains.add(clean)
                local_domain_count += 1
        else:
            stats["junk"] += 1
            errors.append(("junk_invalid_line", name, raw_line))

    download_report[name]["extracted_domains"] = local_domain_count
    download_report[name]["extracted_ips"] = local_ip_count
    print(f"  -> Извлечено доменов: {local_domain_count} | IP: {local_ip_count}")

for suffix in forced_block_suffixes:
    if is_valid_domain(suffix):
        all_domains.add(suffix)
for domain in forced_block_domains:
    if is_valid_domain(domain):
        all_domains.add(domain)

for ip in forced_block_ips:
    validated = validate_ip(ip)
    if validated:
        all_ips.add(validated)

# Этап формирования Rule-Set
print("\n=== ЭТАП 5: ОЧИСТКА ПОДДОМЕНОВ И ФОРМИРОВАНИЕ RULE-SET ===")
build_and_write()

TOTAL_TIME = round(time.time() - SCRIPT_START_TIME, 2)

print("\n" + "="*45)
print("ГОТОВО! Файлы успешно разделены и сохранены.")
print("-" * 45)
if oisd_choice in ('1', '3'):
    print(f"Уникальных доменов (Std/Plus): {len(optimized_domains)} / {len(optimized_domains_plus)}")
if oisd_choice in ('2', '3'):
    print(f"Уникальных доменов (Sm/PlusSm):{len(optimized_domains_sm)} / {len(optimized_domains_plus_sm)}")
print(f"Уникальных IP-адресов:         {len(all_ips)}")
print(f"Удалено по ключевым словам:    {stats['excluded']}")
print(f"Отсеяно ошибочно добавленных:  {stats['junk']}")
print(f"Защищено (exact):              {stats['protected_exact']}")
print(f"Защищено (suffix):             {stats['protected_suffix']}")
print("-" * 45)
if oisd_choice in ('1', '3'):
    print(f"ПРАВИЛ В ФАЙЛАХ STD:       {final_list_len}")
    print(f"ПРАВИЛ В ФАЙЛАХ PLUS:      {final_list_plus_len}")
if oisd_choice in ('2', '3'):
    print(f"ПРАВИЛ В ФАЙЛАХ STD SMALL: {final_list_sm_len}")
    print(f"ПРАВИЛ В ФАЙЛАХ PLUS SMALL:{final_list_plus_sm_len}")
print(f"ВСЕГО ОТБРОШЕНО СТРОК:     {len(errors)}")
print(f"ОБЩЕЕ ВРЕМЯ ВЫПОЛНЕНИЯ:    {TOTAL_TIME} сек.")
print("-" * 45)

print("Download summary (blacklists):")
for name, info in download_report.items():
    print(f"  - {name}: {info['status']} (method: {info.get('method','N/A')}, lines: {info.get('lines',0)})")
print("\nDownload summary (whitelists):")
for name, info in white_download_report.items():
    print(f"  - {name}: {info['status']} (method: {info.get('method','N/A')}, lines: {info.get('lines',0)})")

save_logs(TOTAL_TIME)

if failed_lists or failed_white_lists:
    print("\nSome lists were skipped intentionally.")
else:
    print("\nAll lists processed successfully.")
print("="*45)
ADBLOCK_END

# ============================================================
# Создание SQLiteTXT.py
# ============================================================
cat << 'SQLITE_END' > $BASE/SQLiteTXT.py
# ============================================================
# SQLITETXT SCRIPT
# Просмотр SQLite баз Shadowrocket в текстовом виде.
# ============================================================

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
INPUT_DIR = ROOT / "Shadowrocket" / "SQLiteTXT" / "Input"
OUTPUT_DIR = ROOT / "Shadowrocket" / "SQLiteTXT" / "Output"
CONFIG_FILE = ROOT / ".sqlitetxt_config"
SEPARATOR = "\t"
SEP_NAME = "tab"

# Блок загрузки конфигурации
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

# Блок утилит
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

# Блок работы с файлами
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

# Блок парсинга выбора
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

# Блок работы с таблицами
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

# Блок экспорта таблицы
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

# Блок режима экспорта
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
                        f.write("Дедупликация по URL включена\n")
                    if sort_by_policy:
                        f.write("Сортировка по политике: DIRECT, PROXY, REJECT\n")
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

# Блок настроек экспорта
def ask_options_extract():
    print("\n=== Настройки экспорта (строка из 0/1 длиной 5, Enter = 11000) ===")
    print("1. Показывать схему таблиц")
    print("2. Показывать количество записей")
    print("3. Фильтровать записи по ключевым словам в поле URL")
    print("4. Удалять дубликаты по URL")
    print("5. Сортировать по политике DIRECT PROXY REJECT")
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
            kw = input("[?] Введите ключевые слова для фильтрации: ").strip()
            if kw:
                keywords = [x.strip() for x in kw.split(",") if x.strip()]
        return bits, keywords

# Блок переименования
def rename_mode(files):
    while True:
        print_files(files)
        print("\n[?] Переименовать один файл (1) или группу (2)? [1]: ", end="")
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

# Блок смены разделителя
def change_separator():
    global SEPARATOR, SEP_NAME
    print(f"\n[+] Текущий разделитель: '{SEP_NAME}'")
    print("[1] tab")
    print("[2] comma")
    print("[3] semicolon")
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

# Блок очистки
def clean_broken_files():
    print("\n=== Очистка повреждённых файлов ===")
    print("[1] Проверить все .db файлы и удалить битые")
    print("[2] Очистить папку Input")
    print("[3] Очистить папку Output")
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

# Главное меню
def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    while True:
        files = list_input_files()
        while not files:
            print("\n[!] В папке Input нет .db файлов.")
            print(f"[*] Поместите файлы в {INPUT_DIR} и нажмите Enter для продолжения")
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
            print("\n[+] Экспорт завершён. Файлы сохранены в Output")
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
SQLITE_END

# ============================================================
# Создание SpyLog.py
# ============================================================
cat << 'SPYLOG_END' > $BASE/SpyLog.py
# ============================================================
# SPYLOG SCRIPT
# Анализ журналов Shadowrocket и получение Spy.module.
# ============================================================

import json
import re
import sys
import os
import shutil
import urllib.request
from pathlib import Path
from datetime import datetime
from collections import defaultdict
from urllib.parse import unquote, urlparse
import base64
import html
import codecs
import chardet

ROOT = Path.home()
INPUT_DIR = ROOT / "Shadowrocket" / "SpyLog" / "Input"
OUTPUT_DIR = ROOT / "Shadowrocket" / "SpyLog" / "Output"
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
SPY_MODULE_URL = "https://raw.githubusercontent.com/Krest-Neva/Shadowrocket/main/Configurations/Spy.module"

# Блок загрузки конфигурации
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

# Блок получения модуля
def fetch_spy_module():
    print("[*] Загрузка Spy.module...")
    try:
        req = urllib.request.Request(SPY_MODULE_URL, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=30) as r:
            data = r.read().decode('utf-8', errors='ignore')
    except Exception as e:
        print(f"[!] Не удалось загрузить: {e}")
        return None
    print("\n" + "="*70)
    print(data)
    print("="*70)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    out = OUTPUT_DIR / "Spy.module"
    with open(out, 'w', encoding='utf-8') as f:
        f.write(data)
    print(f"[+] Сохранено: {out}")
    return data

# Блок утилит
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

# Блок декодирования
def strip_ansi_bytes(data):
    return ANSI_RE.sub(b"", data)

def detect_and_decode(data):
    try:
        detected = chardet.detect(data)
        if detected and detected['encoding'] and detected['confidence'] > 0.5:
            return data.decode(detected['encoding'], errors='replace')
    except:
        pass
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
    if not text:
        return text
    text = html.unescape(text)
    text = decode_percent(text)
    text = decode_unicode_escapes(text)
    try:
        text = codecs.decode(text, 'quopri')
    except:
        pass
    return text

# Блок извлечения блоков
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
        text = detect_and_decode(bb)
        blocks_text.append(text)
    return blocks_text

# Блок работы с файлами
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

# Блок дедупликации и сохранения
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

# Блок настроек
def ask_options(mode):
    if mode == "extract":
        print("\n=== Настройки вывода (строка из 0/1 длиной 5, Enter = 11110) ===")
        print("1. Показывать список уникальных URL")
        print("2. Декодировать закодированные строки в телах")
        print("3. Показывать количество блоков по каждому файлу")
        print("4. Отделить логи с ключевыми словами")
        print("5. Показывать дубликаты (0 удалять, 1 оставлять)")
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
                kw = input("[?] Введите ключевые слова: ").strip()
                if kw:
                    keywords = [x.strip() for x in kw.split(",") if x.strip()]
            return bits, keywords
    else:
        print("\n=== Настройки вывода (строка из 0/1 длиной 6, Enter = 111100) ===")
        print("1. Показывать статистику URL")
        print("2. Декодировать строки в телах перед сравнением")
        print("3. Показывать детальные различия полей")
        print("4. Включать полные блоки в отчёт")
        print("5. Отделить логи с ключевыми словами")
        print("6. Показывать дубликаты (0 удалять, 1 оставлять)")
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
                kw = input("[?] Введите ключевые слова: ").strip()
                if kw:
                    keywords = [x.strip() for x in kw.split(",") if x.strip()]
            print("\n[?] Как сравнивать сигнатуры?")
            print("1 - полный URL")
            print("2 - путь без параметров")
            print("3 - только метод и путь")
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

# Блок режима Extract
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
    print("\r[*] Дедупликация...          ", end="")
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
        lines.append("=== Blocks with keywords ===")
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

# Блок режима Compare
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
    lines.append("=== COMPARE REPORT ===")
    lines.append(f"Base file: {base_name}")
    lines.append(f"Compared against: {', '.join(name for name, _ in recs[1:])}")
    lines.append(f"Signature level: {sig_level}")
    lines.append("")
    if keywords:
        lines.append(f"Keywords: {', '.join(keywords)}")
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
        lines.append(f"Sample signatures from {name}:")
        for s in sample:
            lines.append(f"  {s}")
        lines.append("")
    common_sigs = set.intersection(*[sigs[name] for name, _ in recs]) if recs else set()
    if not common_sigs:
        lines.append("WARNING: No common signatures found between files")
        lines.append("")
    else:
        lines.append(f"Common signatures: {len(common_sigs)}")
        lines.append("")
    for idx, (other_name, other_recs) in enumerate(recs[1:], 1):
        lines.append(f"=== Comparison with {other_name} ===")
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

# Блок группового сравнения
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
    lines.append(f"Base group: {base_name}")
    lines.append(f"Compared against: {', '.join(group_names[1:])}")
    lines.append(f"Signature level: {sig_level}")
    lines.append("")
    if keywords:
        lines.append(f"Keywords: {', '.join(keywords)}")
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
        lines.append(f"Sample signatures from {name}:")
        for s in sample:
            lines.append(f"  {s}")
        lines.append("")
    common_sigs = set.intersection(*[sigs[name] for name in group_names]) if group_names else set()
    if not common_sigs:
        lines.append("WARNING: No common signatures found between groups")
        lines.append("")
    else:
        lines.append(f"Common signatures: {len(common_sigs)}")
        lines.append("")
    for idx in range(1, len(group_names)):
        other_name = group_names[idx]
        other_recs = group_records[idx]
        lines.append(f"=== Comparison with {other_name} ===")
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

# Блок переименования выходных файлов
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
        new_name = input("[?] Новое имя: ").strip()
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
        print("\n[?] Переименовать один файл (1) или группу (2)? [1]: ", end="")
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

# Блок очистки
def clean_broken_files():
    print("\n=== Очистка ===")
    print("[1] Очистить папку Input")
    print("[2] Очистить папку Output")
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
        print("\n[+] Поиск файлов с недопустимыми символами...")
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
        return
    print("[!] Неверный выбор")

# Главное меню
def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    while True:
        files = list_input_files()
        while not files:
            print("\n[!] В папке Input нет файлов.")
            print(f"[*] Поместите файлы в {INPUT_DIR} и нажмите Enter для продолжения")
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
        print("[7] Get Spy.module")
        mode = input("\n[?] Выберите режим (1/2/3/4/5/6/7) [1]: ").strip()
        if mode == "":
            mode = "1"
        if mode == "5":
            print("[+] Выход.")
            break
        if mode == "7":
            fetch_spy_module()
            input("\nEnter...")
            continue
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
SPYLOG_END

# ============================================================
# Создание SubManager.py
# ============================================================
cat << 'SUBMGR_END' > $BASE/SubManager.py
# ============================================================
# SUBMANAGER SCRIPT
# Работа с подписками, генерация JSON Xray, универсальный
# редактор JSON-конфигов с любыми полями.
# ============================================================

import os, sys, re, json, base64, urllib.request, ssl, subprocess, shutil, time, random, copy, ipaddress
from urllib.parse import urlparse, parse_qs, urlencode, unquote, quote
from pathlib import Path

HOME = Path.home()
BASE = HOME / "Shadowrocket" / "SubManager"
INPUT_DIR = BASE / "Input"
OUTPUT_DIR = BASE / "Output"
BACKUP_DIR = BASE / "Backups"
ROUTING_DIR = BASE / "Routing"
CFG_FILE = BASE / "config.json"
AUTOSAVE_FILE = BACKUP_DIR / "autosave_servers.txt"
UA = "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1"
W = 52
EXIT = "__EXIT__"
DNS_SERVERS = ["8.8.8.8", "8.8.4.4", "1.1.1.1", "94.140.14.14", "94.140.15.15"]

DURATION_RE = re.compile(r'^(\d+(?:\.\d+)?)(ms|s|m|h|d)?$')
DURATION_UNITS = {'ms', 's', 'm', 'h', 'd'}
BALANCER_TYPES = {"leastload": "leastLoad", "leastping": "leastPing", "random": "random", "roundrobin": "roundRobin"}
TLD_ONLY = {'ru', 'su', 'by', 'kz', 'xn--p1ai', 'рф'}

PARAM_DEFAULTS = {
    "scheme": "vless", "type": "tcp", "security": "reality", "flow": "xtls-rprx-vision",
    "path": "/", "host": "", "sni": "", "pbk": "", "sid": "", "fp": "chrome",
    "serviceName": "", "authority": "", "mode": "auto", "port": "443", "host_addr": "",
    "alpn": "h2", "obfs": "salamander", "obfs-password": "", "id": "", "password": "",
    "method": "aes-256-gcm", "concurrency": "4", "spiderX": "/", "headerType": "none",
    "heartbeatPeriod": "0", "alterId": "0", "encryption": "auto",
    "allowedIPs": "0.0.0.0/0", "mtu": "1420", "dns": "1.1.1.1", "presharedKey": "",
    "keepalive": "0", "up": "", "down": "", "congestion_control": "cubic",
    "pinned_certchain_sha256": "", "verify_peer_cert_by_name": "",
    "jc": "4", "jmin": "40", "jmax": "70", "s1": "30", "s2": "30",
    "h1": "1", "h2": "2", "h3": "3", "h4": "4",
}

GEOSITE_SUGGESTIONS = [
    "geosite:private", "geosite:category-ads-all", "geosite:category-ru",
    "geosite:category-porn", "geosite:google", "geosite:youtube",
    "geosite:telegram", "geosite:twitter", "geosite:facebook",
    "geosite:instagram", "geosite:openai", "geosite:geolocation-cn",
    "geosite:cn", "geosite:apple", "geosite:icloud", "geosite:microsoft",
    "geosite:github", "geosite:netflix", "geosite:spotify", "geosite:discord",
    "geosite:tiktok", "geosite:category-games", "geosite:category-media-ru",
    "geosite:category-communication",
]
GEOIP_SUGGESTIONS = [
    "geoip:private", "geoip:ru", "geoip:by", "geoip:kz",
    "geoip:cn", "geoip:us", "geoip:eu", "geoip:telegram",
]

# Блок нормализации
def normalize_duration(val, default_unit='s'):
    if val is None:
        return f"1{default_unit}"
    v = str(val).strip().lower()
    if not v:
        return f"1{default_unit}"
    m = DURATION_RE.match(v)
    if not m:
        return f"1{default_unit}"
    num, unit = m.group(1), m.group(2)
    if unit is None:
        unit = default_unit
    if unit not in DURATION_UNITS:
        unit = default_unit
    try:
        float(num)
    except ValueError:
        return f"1{default_unit}"
    return f"{num}{unit}"

def normalize_balancer_type(val):
    if not val:
        return "leastLoad"
    key = re.sub(r'[^a-z]', '', str(val).lower())
    return BALANCER_TYPES.get(key, "leastLoad")

def normalize_int(val, default=0, mn=None, mx=None):
    try:
        n = int(val)
    except (ValueError, TypeError):
        return default
    if mn is not None and n < mn:
        n = mn
    if mx is not None and n > mx:
        n = mx
    return n

def normalize_float(val, default=0.0):
    try:
        return float(val)
    except (ValueError, TypeError):
        return default

def process_domain_list(domains):
    dom_only, kw_set, re_set, other = [], set(), set(), []
    for d in domains:
        if not isinstance(d, str):
            continue
        if d.startswith("domain:"):
            base = d[7:]
            if '.' not in base and base.lower() in TLD_ONLY:
                kw_set.add(f"keyword:.{base.lower()}")
            else:
                dom_only.append(base)
        elif d.startswith("keyword:"):
            kw_set.add(d)
        elif d.startswith("regexp:"):
            re_set.add(d)
        else:
            other.append(d)
    dom_only.sort(key=lambda x: x.count('.'))
    keep = set()
    for d in dom_only:
        parts = d.split('.')
        is_child = False
        for i in range(1, len(parts)):
            if '.'.join(parts[i:]) in keep:
                is_child = True
                break
        if not is_child:
            keep.add(d)
    result = [f"domain:{d}" for d in sorted(keep)]
    result.extend(sorted(kw_set))
    result.extend(sorted(re_set))
    result.extend(sorted(set(other)))
    return result

# Блок утилит интерфейса
def clr():
    os.system('clear')

def hdr(t):
    print("=" * W)
    print(f" {t}")
    print("=" * W)

def ln():
    print("-" * W)

def ask(prompt, default=None, choices=None, allow_exit=True):
    while True:
        try:
            v = input(prompt).strip()
        except (EOFError, KeyboardInterrupt):
            return EXIT if allow_exit else default
        if allow_exit and v.lower() in ('q', 'exit', 'back', 'назад'):
            return EXIT
        if not v and default is not None:
            return default
        if choices:
            if v.lower() in [c.lower() for c in choices]:
                return v
            print(f"[!] Допустимо: {', '.join(choices)}")
        else:
            return v

def ask_int(prompt, default=None, mn=None, mx=None):
    while True:
        try:
            v = input(prompt).strip()
            if v.lower() in ('q', 'exit', 'back', 'назад'):
                return EXIT
            if not v and default is not None:
                return default
            n = int(v)
            if mn is not None and n < mn:
                print(f"[!] >= {mn}")
                continue
            if mx is not None and n > mx:
                print(f"[!] <= {mx}")
                continue
            return n
        except ValueError:
            print("[!] Введите число или 'q' для выхода.")
        except (EOFError, KeyboardInterrupt):
            return EXIT

def ask_multi(prompt, mn, mx):
    while True:
        try:
            v = input(prompt).strip()
            if v.lower() in ('q', 'exit', 'back', 'назад'):
                return EXIT
            if not v:
                return None
            if v.lower() in ('all', 'a', '*'):
                return list(range(mn, mx + 1))
            result = []
            for part in v.split(','):
                part = part.strip()
                if '-' in part:
                    a, b = part.split('-', 1)
                    a, b = int(a), int(b)
                    if a > b:
                        a, b = b, a
                    for x in range(a, b + 1):
                        if mn <= x <= mx and x not in result:
                            result.append(x)
                else:
                    x = int(part)
                    if mn <= x <= mx and x not in result:
                        result.append(x)
            if result:
                return result
            print("[!] Пусто.")
        except Exception:
            print("[!] Формат: 1,3-5 или all (или q)")

def fmt_size(b):
    if b < 1024:
        return f"{b} B"
    if b < 1024 * 1024:
        return f"{b / 1024:.1f} KB"
    return f"{b / 1024 / 1024:.2f} MB"

def progress_bar(current, total, prefix="", width=25, elapsed=None):
    if total and total > 0:
        frac = current / total
        filled = int(width * frac)
        bar = "#" * filled + "-" * (width - filled)
        pct = frac * 100
        tail = ""
        if elapsed and frac > 0:
            eta = elapsed / frac * (1 - frac)
            tail = f" ETA {int(eta)}s"
        sys.stdout.write(f"\r{prefix} [{bar}] {pct:5.1f}%{tail}   ")
        sys.stdout.flush()
    else:
        sys.stdout.write(f"\r{prefix} {fmt_size(current)}   ")
        sys.stdout.flush()

# Блок загрузки
def dl_urllib(url, show_progress=True):
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    req = urllib.request.Request(url, headers={'User-Agent': UA})
    with urllib.request.urlopen(req, context=ctx, timeout=30) as r:
        total = None
        cl = r.getheader('Content-Length')
        if cl:
            try:
                total = int(cl)
            except Exception:
                total = None
        data = bytearray()
        start = time.time()
        while True:
            chunk = r.read(8192)
            if not chunk:
                break
            data.extend(chunk)
            if show_progress:
                progress_bar(len(data), total, prefix="  [urllib]", elapsed=time.time() - start)
        if show_progress:
            sys.stdout.write("\n")
            sys.stdout.flush()
        return bytes(data)

def dl_curl(url, show_progress=True):
    tmp = "/tmp/sub_dl_curl.txt"
    cmd = ['curl', '-sL', '--insecure', '-A', UA, '--max-time', '60', '-o', tmp, url]
    if show_progress:
        print("  [curl] загрузка...")
    r = subprocess.run(cmd, capture_output=True)
    if r.returncode == 0 and os.path.exists(tmp):
        with open(tmp, 'rb') as f:
            data = f.read()
        os.unlink(tmp)
        if show_progress:
            print(f"  [curl] OK: {fmt_size(len(data))}")
        return data
    return None

def dl_wget(url, show_progress=True):
    if not shutil.which('wget'):
        return None
    tmp = "/tmp/sub_dl_wget.txt"
    cmd = ['wget', '-q', '--no-check-certificate', '-U', UA, '-O', tmp, url]
    if show_progress:
        print("  [wget] загрузка...")
    r = subprocess.run(cmd, capture_output=True)
    if r.returncode == 0 and os.path.exists(tmp):
        with open(tmp, 'rb') as f:
            data = f.read()
        os.unlink(tmp)
        if show_progress:
            print(f"  [wget] OK: {fmt_size(len(data))}")
        return data
    return None

def dl_aria2(url, show_progress=True):
    if not shutil.which('aria2c'):
        return None
    tmp_dir = "/tmp/sub_aria"
    os.makedirs(tmp_dir, exist_ok=True)
    cmd = ['aria2c', '-q', '--check-certificate=false', '-U', UA, '-x', '4', '-d', tmp_dir, '-o', 'sub.txt', url]
    if show_progress:
        print("  [aria2] загрузка...")
    r = subprocess.run(cmd, capture_output=True)
    out = os.path.join(tmp_dir, 'sub.txt')
    if r.returncode == 0 and os.path.exists(out):
        with open(out, 'rb') as f:
            data = f.read()
        os.unlink(out)
        if show_progress:
            print(f"  [aria2] OK: {fmt_size(len(data))}")
        return data
    return None

def dl_url(url, method='auto', show_progress=True):
    print(f"[*] URL: {url}")
    methods = ['urllib', 'curl', 'wget', 'aria2'] if method == 'auto' else [method]
    for m in methods:
        try:
            if m == 'urllib':
                data = dl_urllib(url, show_progress)
            elif m == 'curl':
                data = dl_curl(url, show_progress)
            elif m == 'wget':
                data = dl_wget(url, show_progress)
            elif m == 'aria2':
                data = dl_aria2(url, show_progress)
            else:
                data = None
            if data:
                for enc in ['utf-8', 'cp1251', 'latin-1']:
                    try:
                        return data.decode(enc)
                    except Exception:
                        continue
        except Exception as e:
            print(f"[!] {m}: {e}")
            continue
    return None

def try_decode_base64(raw):
    s = raw.strip().replace('\n', '').replace('\r', '').replace(' ', '')
    if len(s) < 16 or not re.fullmatch(r'[A-Za-z0-9+/=_\-]+', s):
        return None
    for enc in ['urlsafe_b64', 'b64']:
        try:
            pad = 4 - len(s) % 4
            padded = s + ('=' * pad if pad != 4 else '')
            if enc == 'urlsafe_b64':
                decoded = base64.urlsafe_b64decode(padded).decode('utf-8', errors='ignore')
            else:
                decoded = base64.b64decode(padded).decode('utf-8', errors='ignore')
            if '://' in decoded or decoded.strip().startswith('{') or 'proxies:' in decoded:
                return decoded
        except Exception:
            continue
    return None

def auto_decode(raw):
    if not raw:
        return raw
    stripped = raw.strip()
    if stripped.startswith('{') or stripped.startswith('['):
        return raw
    if '://' in raw[:500] or 'proxies:' in raw[:200]:
        return raw
    dec = try_decode_base64(raw)
    if dec:
        print("[+] Base64 декодирован.")
        return dec
    return raw

# Блок парсинга URI
def parse_uri(uri):
    uri = uri.strip()
    if not uri or '://' not in uri:
        return None
    scheme = uri.split('://')[0].lower()
    frag = ''
    if '#' in uri:
        uri, frag = uri.split('#', 1)
    r = {'scheme': scheme, 'raw': uri + ('#' + frag if frag else ''),
         'name': unquote(frag) if frag else '', 'params': {},
         'host': '', 'port': '', 'id': '', 'password': '', 'method': ''}
    try:
        if scheme in ('vless', 'vmess', 'trojan'):
            p = urlparse(uri)
            r['id'] = unquote(p.username or '')
            if scheme == 'vless' and not re.fullmatch(r'[0-9a-fA-F\-]{20,}', r['id']):
                try:
                    pad = 4 - len(r['id']) % 4
                    padded = r['id'] + ('=' * pad if pad != 4 else '')
                    if re.fullmatch(r'[A-Za-z0-9+/=_\-]+', r['id']) and len(r['id']) >= 16:
                        dec = base64.urlsafe_b64decode(padded).decode('utf-8', errors='ignore')
                        if ':' in dec:
                            cand = dec.split(':', 1)[1].strip()
                            if len(cand) >= 8:
                                r['id'] = cand
                except Exception:
                    pass
            r['host'] = p.hostname or ''
            r['port'] = str(p.port) if p.port else ''
            for k, v in parse_qs(p.query).items():
                r['params'][k] = v[0] if len(v) == 1 else v
        elif scheme in ('hysteria2', 'hy2', 'hysteria', 'hy'):
            p = urlparse(uri)
            r['password'] = unquote(p.username or '')
            r['host'] = p.hostname or ''
            r['port'] = str(p.port) if p.port else ''
            for k, v in parse_qs(p.query).items():
                r['params'][k] = v[0] if len(v) == 1 else v
        elif scheme == 'ss':
            body = uri[5:]
            if '@' in body:
                ui, hp = body.rsplit('@', 1)
                try:
                    pad = 4 - len(ui) % 4
                    ui_pad = ui + '=' * pad if pad != 4 else ui
                    dec = base64.b64decode(ui_pad).decode('utf-8', errors='ignore')
                    if ':' in dec:
                        r['method'], r['password'] = dec.split(':', 1)
                    else:
                        r['method'] = dec
                except Exception:
                    if ':' in ui:
                        r['method'], r['password'] = ui.split(':', 1)
                    else:
                        r['method'] = ui
                if ':' in hp:
                    h, p = hp.rsplit(':', 1)
                    r['host'] = h
                    r['port'] = p
                else:
                    r['host'] = hp
            else:
                try:
                    pad = 4 - len(body) % 4
                    padded = body + ('=' * pad if pad != 4 else '')
                    dec = base64.b64decode(padded).decode('utf-8', errors='ignore')
                    if '@' in dec:
                        ui, hp = dec.rsplit('@', 1)
                        if ':' in ui:
                            r['method'], r['password'] = ui.split(':', 1)
                        if ':' in hp:
                            r['host'], r['port'] = hp.rsplit(':', 1)
                except Exception:
                    pass
            if '?' in uri:
                for k, v in parse_qs(uri.split('?', 1)[1]).items():
                    r['params'][k] = v[0] if len(v) == 1 else v
        elif scheme in ('socks5', 'http', 'tuic', 'juicity', 'wireguard', 'amneziawg', 'awg', 'mieru', 'sudoku', 'openconnect'):
            p = urlparse(uri)
            r['id'] = unquote(p.username or '')
            r['password'] = unquote(p.password or '')
            r['host'] = p.hostname or ''
            r['port'] = str(p.port) if p.port else ''
            for k, v in parse_qs(p.query).items():
                r['params'][k] = v[0] if len(v) == 1 else v
        else:
            return None
    except Exception:
        return None
    return r

def extract_links(text):
    out = []
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        if any(line.startswith(s + '://') for s in ['vless', 'vmess', 'trojan', 'ss', 'hysteria2', 'hy2', 'hysteria', 'hy', 'socks5', 'http', 'tuic', 'juicity', 'wireguard', 'amneziawg', 'awg', 'mieru', 'sudoku', 'openconnect']):
            out.append(line)
    return out

# Блок парсинга Xray outbounds
def parse_xray_outbound(ob):
    proto = (ob.get('protocol') or '').lower()
    tag = ob.get('tag', '')
    ss = ob.get('streamSettings', {}) or {}
    net = ss.get('network', 'tcp')
    sec = ss.get('security', 'none')

    if proto == 'vless':
        vnext = (ob.get('settings', {}) or {}).get('vnext', [{}])
        if not vnext:
            return None
        vn = vnext[0]
        users = vn.get('users', [{}])
        user = users[0] if users else {}
        s = {
            'scheme': 'vless', 'name': tag or 'vless',
            'host': vn.get('address', ''), 'port': str(vn.get('port', '443')),
            'id': user.get('id', ''), 'password': '', 'method': '',
            'params': {'type': net, 'security': sec}
        }
        if user.get('flow'):
            s['params']['flow'] = user['flow']
        if sec == 'reality':
            rs = ss.get('realitySettings', {}) or {}
            for src, dst in [('serverName', 'sni'), ('publicKey', 'pbk'),
                             ('shortId', 'sid'), ('fingerprint', 'fp'), ('spiderX', 'spiderX')]:
                if rs.get(src):
                    s['params'][dst] = str(rs[src])
        elif sec == 'tls':
            ts = ss.get('tlsSettings', {}) or {}
            if ts.get('serverName'):
                s['params']['sni'] = ts['serverName']
            if ts.get('fingerprint'):
                s['params']['fp'] = ts['fingerprint']
            if ts.get('alpn'):
                s['params']['alpn'] = ','.join(ts['alpn'])
        if net == 'ws':
            w = ss.get('wsSettings', {}) or {}
            s['params']['path'] = w.get('path', '/')
            headers = w.get('headers', {}) or {}
            if headers.get('Host'):
                s['params']['host'] = headers['Host']
            if w.get('heartbeatPeriod'):
                s['params']['heartbeatPeriod'] = str(w['heartbeatPeriod'])
        elif net == 'grpc':
            g = ss.get('grpcSettings', {}) or {}
            if g.get('serviceName'):
                s['params']['serviceName'] = g['serviceName']
            if g.get('authority'):
                s['params']['authority'] = g['authority']
            s['params']['mode'] = 'multi' if g.get('multiMode') else 'auto'
        elif net == 'tcp':
            th = (ss.get('tcpSettings', {}) or {}).get('header', {}) or {}
            s['params']['headerType'] = th.get('type', 'none')
        elif net in ('xhttp', 'splithttp'):
            x = ss.get('xhttpSettings', {}) or {}
            if x.get('path'): s['params']['path'] = x['path']
            if x.get('host'): s['params']['host'] = x['host']
            if x.get('mode'): s['params']['mode'] = x['mode']
            if x.get('concurrency'): s['params']['concurrency'] = str(x['concurrency'])
        elif net == 'httpupgrade':
            h = ss.get('httpupgradeSettings', {}) or {}
            if h.get('path'): s['params']['path'] = h['path']
            if h.get('host'): s['params']['host'] = h['host']
        return s

    elif proto == 'vmess':
        vnext = (ob.get('settings', {}) or {}).get('vnext', [{}])
        if not vnext:
            return None
        vn = vnext[0]
        users = vn.get('users', [{}])
        user = users[0] if users else {}
        s = {
            'scheme': 'vmess', 'name': tag or 'vmess',
            'host': vn.get('address', ''), 'port': str(vn.get('port', '443')),
            'id': user.get('id', ''), 'password': '', 'method': '',
            'params': {'type': net, 'security': sec}
        }
        if user.get('alterId'):
            s['params']['alterId'] = str(user['alterId'])
        if user.get('security'):
            s['params']['encryption'] = user['security']
        if sec == 'tls':
            ts = ss.get('tlsSettings', {}) or {}
            if ts.get('serverName'):
                s['params']['sni'] = ts['serverName']
        return s

    elif proto in ('shadowsocks', 'ss'):
        servers = (ob.get('settings', {}) or {}).get('servers', [{}])
        if not servers:
            return None
        srv = servers[0]
        return {
            'scheme': 'ss', 'name': tag or 'ss',
            'host': srv.get('address', ''), 'port': str(srv.get('port', '443')),
            'id': '', 'password': srv.get('password', ''),
            'method': srv.get('method', 'aes-256-gcm'), 'params': {}
        }

    elif proto == 'hysteria2':
        st = ob.get('settings', {}) or {}
        s = {
            'scheme': 'hysteria2', 'name': tag or 'hysteria2',
            'host': st.get('address', ''), 'port': str(st.get('port', '443')),
            'id': '', 'password': st.get('password', ''), 'method': '',
            'params': {'type': 'hysteria2', 'security': 'tls'}
        }
        if st.get('obfs'):
            s['params']['obfs'] = st['obfs']
            if st.get('obfsPassword'):
                s['params']['obfs-password'] = st['obfsPassword']
        ts = ss.get('tlsSettings', {}) or {}
        if ts.get('serverName'):
            s['params']['sni'] = ts['serverName']
        if ts.get('alpn'):
            s['params']['alpn'] = ','.join(ts['alpn'])
        return s

    elif proto == 'hysteria':
        st = ob.get('settings', {}) or {}
        s = {
            'scheme': 'hysteria', 'name': tag or 'hysteria',
            'host': st.get('address', ''), 'port': str(st.get('port', '443')),
            'id': '', 'password': st.get('auth', ''), 'method': '',
            'params': {'type': 'hysteria', 'security': 'tls'}
        }
        if st.get('up'):
            s['params']['up'] = str(st['up'])
        if st.get('down'):
            s['params']['down'] = str(st['down'])
        return s

    elif proto == 'trojan':
        servers = (ob.get('settings', {}) or {}).get('servers', [{}])
        if not servers:
            return None
        srv = servers[0]
        s = {
            'scheme': 'trojan', 'name': tag or 'trojan',
            'host': srv.get('address', ''), 'port': str(srv.get('port', '443')),
            'id': '', 'password': srv.get('password', ''), 'method': '',
            'params': {'type': net, 'security': sec if sec != 'none' else 'tls'}
        }
        if sec == 'tls':
            ts = ss.get('tlsSettings', {}) or {}
            if ts.get('serverName'):
                s['params']['sni'] = ts['serverName']
        return s

    elif proto == 'socks':
        servers = (ob.get('settings', {}) or {}).get('servers', [{}])
        if not servers:
            return None
        srv = servers[0]
        return {
            'scheme': 'socks5', 'name': tag or 'socks5',
            'host': srv.get('address', ''), 'port': str(srv.get('port', '1080')),
            'id': srv.get('user', ''), 'password': srv.get('pass', ''), 'method': '',
            'params': {}
        }

    elif proto == 'http':
        servers = (ob.get('settings', {}) or {}).get('servers', [{}])
        if not servers:
            return None
        srv = servers[0]
        return {
            'scheme': 'http', 'name': tag or 'http',
            'host': srv.get('address', ''), 'port': str(srv.get('port', '8080')),
            'id': srv.get('user', ''), 'password': srv.get('pass', ''), 'method': '',
            'params': {}
        }

    elif proto == 'wireguard':
        st = ob.get('settings', {}) or {}
        peers = st.get('peers', [{}])
        peer = peers[0] if peers else {}
        return {
            'scheme': 'wireguard', 'name': tag or 'wireguard',
            'host': peer.get('endpoint', '').split(':')[0] if peer.get('endpoint') else '',
            'port': peer.get('endpoint', '').split(':')[1] if peer.get('endpoint') and ':' in peer.get('endpoint') else '51820',
            'id': st.get('secretKey', ''), 'password': peer.get('publicKey', ''), 'method': '',
            'params': {
                'allowedIPs': ','.join(peer.get('allowedIPs', ['0.0.0.0/0'])),
                'mtu': str(st.get('mtu', 1420)),
                'dns': st.get('dns', ''),
                'presharedKey': peer.get('preSharedKey', ''),
                'keepalive': str(peer.get('persistentKeepalive', 0))
            }
        }
    return None

def singbox_obj_to_server(obj):
    if not isinstance(obj, dict):
        return None
    t = (obj.get('type') or obj.get('protocol') or '').upper()
    host = obj.get('host') or obj.get('server') or obj.get('address') or ''
    port = obj.get('port')
    if port is None:
        return None
    port = str(port)
    if not host or not port:
        return None
    name = obj.get('title') or obj.get('remarks') or obj.get('name') or obj.get('tag') or ''
    alpn = obj.get('alpn') or ''
    peer = obj.get('peer') or obj.get('sni') or obj.get('serverName') or ''
    if t in ('HYSTERIA2', 'HY2'):
        s = {'scheme': 'hysteria2', 'name': name, 'host': host, 'port': port,
             'id': '', 'password': obj.get('password') or obj.get('auth') or '',
             'method': '', 'params': {'type': 'hysteria2', 'security': 'tls'}}
        if peer:
            s['params']['sni'] = peer
        if alpn:
            s['params']['alpn'] = alpn
        obfs = obj.get('obfs')
        if obfs and obfs.lower() not in ('none', ''):
            s['params']['obfs'] = obfs
            if obj.get('obfsParam'):
                s['params']['obfs-password'] = obj['obfsParam']
        return s
    if t == 'VLESS':
        s = {'scheme': 'vless', 'name': name, 'host': host, 'port': port,
             'id': obj.get('uuid') or obj.get('id') or '',
             'password': '', 'method': '', 'params': {'type': 'tcp', 'security': 'none'}}
        if obj.get('tls') or obj.get('publicKey') or peer:
            s['params']['security'] = 'reality' if obj.get('publicKey') else 'tls'
            s['params']['type'] = 'tcp'
        if peer:
            s['params']['sni'] = peer
        if obj.get('publicKey'):
            s['params']['pbk'] = obj['publicKey']
        if obj.get('shortId'):
            s['params']['sid'] = obj['shortId']
        if obj.get('tlsProfile'):
            s['params']['fp'] = obj['tlsProfile']
        if obj.get('fingerprint'):
            s['params']['fp'] = obj['fingerprint']
        xtls = obj.get('xtls')
        if xtls in (2, '2', True):
            s['params']['flow'] = 'xtls-rprx-vision'
        if alpn:
            s['params']['alpn'] = alpn
        return s
    if t == 'TROJAN':
        s = {'scheme': 'trojan', 'name': name, 'host': host, 'port': port,
             'id': '', 'password': obj.get('password') or '',
             'method': '', 'params': {'type': 'tcp', 'security': 'tls'}}
        if peer:
            s['params']['sni'] = peer
        if alpn:
            s['params']['alpn'] = alpn
        return s
    if t in ('SHADOWSOCKS', 'SS'):
        return {'scheme': 'ss', 'name': name, 'host': host, 'port': port,
                'id': '', 'password': obj.get('password') or '',
                'method': obj.get('method') or 'aes-256-gcm', 'params': {}}
    return None

def extract_servers_from_json(text):
    try:
        data = json.loads(text)
    except Exception:
        return [], None
    if not isinstance(data, dict):
        return [], None
    outbounds = data.get('outbounds', [])
    servers = []
    for ob in outbounds:
        if not isinstance(ob, dict):
            continue
        proto = (ob.get('protocol') or '').lower()
        if proto in ('vless', 'vmess', 'trojan', 'ss', 'shadowsocks', 'hysteria2', 'hysteria', 'socks', 'http', 'wireguard'):
            s = parse_xray_outbound(ob)
            if s:
                servers.append(s)
    return servers, data

def parse_singbox_multi(text):
    servers = []
    for line in text.splitlines():
        line = line.strip().rstrip(',')
        if not line.startswith('{'):
            continue
        try:
            obj = json.loads(line)
        except Exception:
            continue
        srv = singbox_obj_to_server(obj)
        if srv:
            servers.append(srv)
    return servers

# Блок сборки URI
def build_uri(s):
    scheme = s['scheme']
    host = s['host']
    port = s['port']
    params = dict(s['params'])
    name = s.get('name', '')
    if scheme in ('vless', 'vmess', 'trojan'):
        uri = f"{scheme}://{quote(s.get('id', ''))}@{host}:{port}"
    elif scheme in ('hysteria2', 'hy2', 'hysteria', 'hy'):
        uri = f"{scheme}://{quote(s.get('password', ''))}@{host}:{port}"
    elif scheme == 'ss':
        ui = f"{s.get('method', '')}:{s.get('password', '')}"
        b = base64.b64encode(ui.encode()).decode().rstrip('=')
        uri = f"ss://{b}@{host}:{port}"
    elif scheme == 'socks5':
        auth = ''
        if s.get('id') or s.get('password'):
            auth = f"{quote(s.get('id', ''))}:{quote(s.get('password', ''))}@"
        uri = f"socks5://{auth}{host}:{port}"
    elif scheme == 'http':
        auth = ''
        if s.get('id') or s.get('password'):
            auth = f"{quote(s.get('id', ''))}:{quote(s.get('password', ''))}@"
        uri = f"http://{auth}{host}:{port}"
    elif scheme == 'tuic':
        uri = f"tuic://{quote(s.get('id', ''))}:{quote(s.get('password', ''))}@{host}:{port}"
    elif scheme == 'juicity':
        uri = f"juicity://{quote(s.get('id', ''))}:{quote(s.get('password', ''))}@{host}:{port}"
    elif scheme == 'wireguard':
        uri = f"wireguard://{quote(s.get('id', ''))}@{host}:{port}"
    elif scheme in ('amneziawg', 'awg'):
        uri = f"{scheme}://{quote(s.get('id', ''))}@{host}:{port}"
    elif scheme == 'mieru':
        uri = f"mieru://{quote(s.get('id', ''))}:{quote(s.get('password', ''))}@{host}:{port}"
    elif scheme == 'sudoku':
        uri = f"sudoku://{quote(s.get('id', ''))}:{quote(s.get('password', ''))}@{host}:{port}"
    elif scheme == 'openconnect':
        uri = f"openconnect://{quote(s.get('id', ''))}@{host}:{port}"
    else:
        return s.get('raw', '')
    if params:
        uri += '?' + urlencode(params, doseq=True)
    if name:
        uri += '#' + quote(name)
    return uri

def show_servers_list(servers, show_params=False):
    if not servers:
        print("[!] Список пуст.")
        return
    print(f"\n{'#':>3} {'Протокол':12} {'Имя':28} {'Адрес':30} {'Транспорт':8} {'Sec':8}")
    ln()
    for i, s in enumerate(servers, 1):
        name = (s.get('name', '') or '(без имени)')[:28]
        addr = f"{s['host']}:{s['port']}"[:30]
        t = s['params'].get('type', 'tcp')
        sec = s['params'].get('security', 'none')
        print(f"{i:>3} {s['scheme']:12} {name:28} {addr:30} {t:8} {sec:8}")
        if show_params:
            extra = []
            for k in ('flow', 'path', 'host', 'sni', 'pbk', 'sid', 'fp', 'serviceName', 'mode', 'concurrency', 'alpn', 'obfs', 'method', 'alterId', 'encryption', 'allowedIPs', 'mtu', 'dns', 'keepalive'):
                if k in s['params'] and s['params'][k]:
                    val = str(s['params'][k])
                    if len(val) > 40:
                        val = val[:37] + "..."
                    extra.append(f"{k}={val}")
            if extra:
                print(f"      {', '.join(extra)}")

# Блок конфигурации по умолчанию
def cfg_default():
    return {
        "dns_servers": DNS_SERVERS,
        "dns_query_strategy": "UseIP",
        "observatory_url": "https://www.google.com/generate_204",
        "observatory_interval": "1m",
        "observatory_timeout": "3s",
        "balancer_strategy": "leastLoad",
        "balancer_expected": 3,
        "balancer_max_rtt": "2s",
        "balancer_tolerance": 0,
        "balancer_baselines": ["2s"],
        "proxy_ports": [10808, 10809],
        "mux_enabled": False,
        "mux_concurrency": 8,
        "mux_xudp_concurrency": 0,
        "mux_xudp_proxy_udp443": "reject",
        "global_proxy": "proxy",
        "sniffing_enabled": True,
        "sniffing_dest_override": ["http", "tls", "quic"],
        "sniffing_route_only": True,
        "json_name": "xray_config",
        "json_remarks": "SubManager Auto",
        "json_use_remarks_as_name": False,
        "routing_order": ["block", "direct", "proxy"],
        "routing": {
            "direct_domains": [], "block_domains": [],
            "direct_ips": [], "block_ips": [],
            "block_protocols": [], "direct_ports": [], "block_ports": [],
            "custom_rules": []
        }
    }

def normalize_cfg(cfg):
    d = cfg_default()
    for k, v in cfg.items():
        if isinstance(v, dict) and k in d and isinstance(d[k], dict):
            merged = dict(d[k])
            merged.update(v)
            cfg[k] = merged
        else:
            d[k] = v
    cfg = d
    cfg['observatory_interval'] = normalize_duration(cfg.get('observatory_interval', '1m'), 'm')
    cfg['observatory_timeout'] = normalize_duration(cfg.get('observatory_timeout', '3s'), 's')
    cfg['balancer_max_rtt'] = normalize_duration(cfg.get('balancer_max_rtt', '2s'), 's')
    cfg['balancer_strategy'] = normalize_balancer_type(cfg.get('balancer_strategy', 'leastLoad'))
    cfg['balancer_expected'] = normalize_int(cfg.get('balancer_expected', 3), 3, 1, 999)
    cfg['balancer_tolerance'] = normalize_float(cfg.get('balancer_tolerance', 0), 0.0)
    bl = cfg.get('balancer_baselines', ['2s'])
    if not isinstance(bl, list):
        bl = ['2s']
    cfg['balancer_baselines'] = [normalize_duration(b, 's') for b in bl]
    pp = cfg.get('proxy_ports', [10808, 10809])
    if not isinstance(pp, list) or len(pp) != 2:
        pp = [10808, 10809]
    cfg['proxy_ports'] = [normalize_int(pp[0], 10808, 1, 65535), normalize_int(pp[1], 10809, 1, 65535)]
    cfg['mux_concurrency'] = normalize_int(cfg.get('mux_concurrency', 8), 8, 1, 128)
    cfg['mux_xudp_concurrency'] = normalize_int(cfg.get('mux_xudp_concurrency', 0), 0, 0, 1024)
    if cfg.get('mux_xudp_proxy_udp443') not in ('reject', 'skip', 'allow'):
        cfg['mux_xudp_proxy_udp443'] = 'reject'
    if cfg.get('global_proxy') not in ('proxy', 'direct', 'block'):
        cfg['global_proxy'] = 'proxy'
    if cfg.get('dns_query_strategy') not in ('UseIP', 'UseIPv4', 'UseIPv6', 'AsIs'):
        cfg['dns_query_strategy'] = 'UseIP'
    ds = cfg.get('dns_servers', DNS_SERVERS)
    if not isinstance(ds, list) or not ds:
        cfg['dns_servers'] = DNS_SERVERS
    so = cfg.get('sniffing_dest_override', ["http", "tls", "quic"])
    if not isinstance(so, list):
        so = ["http", "tls", "quic"]
    cfg['sniffing_dest_override'] = so
    ro = cfg.get('routing_order', ["block", "direct", "proxy"])
    if not isinstance(ro, list) or set(ro) != {'block', 'direct', 'proxy'}:
        ro = ["block", "direct", "proxy"]
    cfg['routing_order'] = ro
    return cfg

def cfg_load():
    if CFG_FILE.exists():
        try:
            with open(CFG_FILE, 'r', encoding='utf-8') as f:
                saved = json.load(f)
            return normalize_cfg(saved)
        except Exception:
            pass
    return cfg_default()

def cfg_save(cfg):
    cfg = normalize_cfg(cfg)
    CFG_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(CFG_FILE, 'w', encoding='utf-8') as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)

def ensure_dirs():
    for d in [INPUT_DIR, OUTPUT_DIR, BACKUP_DIR, ROUTING_DIR]:
        if not d.exists():
            d.mkdir(parents=True, exist_ok=True)

def sanitize_filename(name):
    name = re.sub(r'[\\/:*?"<>|]', '_', name)
    name = name.strip().strip('.')
    return name or "xray_config"

def transliterate(name):
    mapping = {
        'а':'a','б':'b','в':'v','г':'g','д':'d','е':'e','ё':'e','ж':'zh','з':'z',
        'и':'i','й':'y','к':'k','л':'l','м':'m','н':'n','о':'o','п':'p','р':'r',
        'с':'s','т':'t','у':'u','ф':'f','х':'h','ц':'ts','ч':'ch','ш':'sh','щ':'sch',
        'ъ':'','ы':'y','ь':'','э':'e','ю':'yu','я':'ya',
        'А':'A','Б':'B','В':'V','Г':'G','Д':'D','Е':'E','Ё':'E','Ж':'Zh','З':'Z',
        'И':'I','Й':'Y','К':'K','Л':'L','М':'M','Н':'N','О':'O','П':'P','Р':'R',
        'С':'S','Т':'T','У':'U','Ф':'F','Х':'H','Ц':'Ts','Ч':'Ch','Ш':'Sh','Щ':'Sch',
        'Ъ':'','Ы':'Y','Ь':'','Э':'E','Ю':'Yu','Я':'Ya',' ':'_'
    }
    out = []
    for ch in name:
        out.append(mapping.get(ch, ch))
    return ''.join(out)

def autosave_servers(servers):
    if not servers:
        return
    lines = [build_uri(s) for s in servers]
    with open(AUTOSAVE_FILE, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))

def autoload_servers():
    if not AUTOSAVE_FILE.exists():
        return []
    try:
        raw = AUTOSAVE_FILE.read_text(encoding='utf-8', errors='ignore')
    except Exception:
        return []
    srv, _ = parse_input(raw)
    return srv

# Блок загрузки источников
def load_source():
    hdr("ЗАГРУЗКА ИСХОДНИКОВ")
    print("  1 - Локальный файл")
    print("  2 - По ссылке (URL)")
    print("  3 - Несколько ссылок подряд")
    print("  q - Назад")
    ch = ask("Выбор [1]: ", default="1", choices=["1", "2", "3"])
    if ch == EXIT:
        return None
    if ch == "1":
        files = sorted([p for p in INPUT_DIR.glob("*") if p.is_file()])
        if not files:
            print(f"[!] Папка {INPUT_DIR} пуста.")
            print(f"    Поместите файл (ссылки, base64 или JSON) в {INPUT_DIR}")
            input("Enter...")
            return None
        print("\n[+] Доступные файлы:")
        for i, f in enumerate(files, 1):
            print(f"  {i}. {f.name} ({fmt_size(f.stat().st_size)})")
        idx = ask_int("Номер файла (q - назад): ", mn=1, mx=len(files))
        if idx == EXIT or idx is None:
            return None
        raw = files[idx - 1].read_text(encoding='utf-8', errors='ignore')
    elif ch == "2":
        url = ask("URL подписки (q - назад): ")
        if url == EXIT or not url:
            return None
        raw = dl_url(url)
        if not raw:
            print("[!] Не удалось загрузить.")
            input("Enter...")
            return None
    else:
        print("[?] Вводите URL по одному. 'q' - завершить.")
        parts = []
        while True:
            u = ask("URL (q - конец): ")
            if u == EXIT or not u:
                break
            t = dl_url(u)
            if t:
                t2 = auto_decode(t)
                parts.append(t2)
                print(f"  [+] Добавлено. Всего частей: {len(parts)}")
            else:
                print(f"  [!] Не удалось загрузить: {u}")
        if not parts:
            input("Enter...")
            return None
        raw = "\n".join(parts)
        print(f"[+] Объединено частей: {len(parts)}")
        return raw
    return auto_decode(raw)

def parse_input(raw):
    if not raw:
        return [], None
    stripped = raw.strip()
    if stripped.startswith('{'):
        servers, json_data = extract_servers_from_json(stripped)
        if servers:
            print(f"[+] Обнаружен Xray JSON конфиг. Извлечено outbounds: {len(servers)}")
            return servers, json_data
    servers = []
    if '{' in raw and '"type"' in raw.upper():
        sb = parse_singbox_multi(raw)
        if sb:
            print(f"[+] Обнаружены sing-box-объекты: {len(sb)}")
            servers.extend(sb)
    links = extract_links(raw)
    if links:
        cnt = 0
        for l in links:
            p = parse_uri(l)
            if p:
                servers.append(p)
                cnt += 1
        print(f"[+] Найдено ссылок: {len(links)}, распарсено: {cnt}")
    if servers:
        return servers, None
    print("[!] Не удалось распарсить данные.")
    return [], None

# Блок дедупликации
def dedupe_servers(servers, mode='full'):
    seen = set()
    out = []
    for s in servers:
        if mode == 'full':
            key = (s['scheme'], s['host'], s['port'], s.get('id', '') or s.get('password', '') or s.get('method', ''))
        elif mode == 'name':
            key = s.get('name', '')
        elif mode == 'addr':
            key = (s['host'], s['port'])
        elif mode == 'user':
            key = (s['host'], s['port'], s.get('id', '') or s.get('password', ''))
        else:
            key = (s['scheme'], s['host'], s['port'])
        if key not in seen:
            seen.add(key)
            out.append(s)
    removed = len(servers) - len(out)
    print(f"[+] Удалено дубликатов: {removed}" if removed else "[+] Дубликатов нет.")
    return out

def dedupe_menu(servers):
    hdr("ДЕДУПЛИКАЦИЯ")
    print("  1 - Полное сходство")
    print("  2 - По имени")
    print("  3 - По адресу")
    print("  4 - По адресу и пользователю")
    print("  5 - По протоколу + адрес + порт")
    print("  q - Отмена")
    ch = ask("Выбор: ", choices=["1", "2", "3", "4", "5"])
    if ch == EXIT:
        return servers
    mode_map = {"1": "full", "2": "name", "3": "addr", "4": "user", "5": "proto"}
    return dedupe_servers(servers, mode_map[ch])

# Блок удаления
def delete_by_keyword(servers):
    hdr("УДАЛЕНИЕ СЕРВЕРОВ")
    print("  1 - По имени")
    print("  2 - По протоколу")
    print("  3 - По транспорту")
    print("  4 - По security")
    print("  5 - По домену")
    print("  6 - По номерам")
    print("  7 - Инвертировать")
    print("  q - Отмена")
    ch = ask("Выбор: ", choices=["1", "2", "3", "4", "5", "6", "7"])
    if ch == EXIT:
        return servers
    idxs = None
    if ch == "1":
        kw = ask("Слова через запятую: ")
        if kw == EXIT:
            return servers
        kws = [k.strip().lower() for k in kw.split(',') if k.strip()]
        if not kws:
            return servers
        idxs = [i for i, s in enumerate(servers) if any(k in s.get('name', '').lower() for k in kws)]
    elif ch == "2":
        proto = ask("Протокол: ").lower()
        if proto == EXIT:
            return servers
        idxs = [i for i, s in enumerate(servers) if s['scheme'] == proto]
    elif ch == "3":
        t = ask("Транспорт: ").lower()
        if t == EXIT:
            return servers
        idxs = [i for i, s in enumerate(servers) if s['params'].get('type', 'tcp') == t]
    elif ch == "4":
        sec = ask("Security: ").lower()
        if sec == EXIT:
            return servers
        idxs = [i for i, s in enumerate(servers) if s['params'].get('security', 'none') == sec]
    elif ch == "5":
        dom = ask("Домен: ").lower()
        if dom == EXIT:
            return servers
        idxs = [i for i, s in enumerate(servers) if dom in s['host'].lower()]
    elif ch == "6":
        show_servers_list(servers)
        sel = ask_multi("Номера: ", 1, len(servers))
        if sel == EXIT or not sel:
            return servers
        idxs = [i - 1 for i in sel]
    elif ch == "7":
        kw = ask("Ключевые слова для ИНВЕРТА: ")
        if kw == EXIT:
            return servers
        kws = [k.strip().lower() for k in kw.split(',') if k.strip()]
        if not kws:
            return servers
        idxs = [i for i, s in enumerate(servers) if not any(k in s.get('name', '').lower() for k in kws)]
    if not idxs:
        print("[!] Ничего не найдено.")
        input("Enter...")
        return servers
    print(f"\n[+] Найдено: {len(idxs)}")
    for i in idxs[:20]:
        print(f"   - {servers[i].get('name', '')} ({servers[i]['scheme']}://{servers[i]['host']})")
    if len(idxs) > 20:
        print(f"   ... и ещё {len(idxs) - 20}")
    ans = ask("Удалить? (y/n) [n]: ", default="n")
    if ans.lower() == 'y':
        for i in sorted(idxs, reverse=True):
            servers.pop(i)
        print(f"[+] Удалено: {len(idxs)}")
    return servers

# Блок сортировки
def sort_servers(servers):
    hdr("СОРТИРОВКА")
    print("  1 - По имени (A-Z)")
    print("  2 - По имени (Z-A)")
    print("  3 - По протоколу")
    print("  4 - По хосту")
    print("  5 - По порту")
    print("  6 - Случайно")
    print("  q - Отмена")
    ch = ask("Выбор: ", choices=["1", "2", "3", "4", "5", "6"])
    if ch == EXIT:
        return servers
    if ch == "1":
        servers.sort(key=lambda x: x.get('name', '').lower())
    elif ch == "2":
        servers.sort(key=lambda x: x.get('name', '').lower(), reverse=True)
    elif ch == "3":
        servers.sort(key=lambda x: x['scheme'])
    elif ch == "4":
        servers.sort(key=lambda x: x['host'].lower())
    elif ch == "5":
        servers.sort(key=lambda x: int(x['port']) if str(x['port']).isdigit() else 0)
    elif ch == "6":
        random.shuffle(servers)
    else:
        return servers
    print("[+] Отсортировано.")
    return servers

def move_server(servers):
    show_servers_list(servers)
    idx = ask_int("Номер сервера для перемещения (q - отмена): ", mn=1, mx=len(servers))
    if idx == EXIT or idx is None:
        return servers
    direction = ask("Направление (u=вверх / d=вниз): ", choices=["u", "d"])
    if direction == EXIT:
        return servers
    i = idx - 1
    if direction == "u" and i > 0:
        servers[i], servers[i - 1] = servers[i - 1], servers[i]
        print("[+] Перемещён вверх.")
    elif direction == "d" and i < len(servers) - 1:
        servers[i], servers[i + 1] = servers[i + 1], servers[i]
        print("[+] Перемещён вниз.")
    else:
        print("[!] Некуда двигать.")
    return servers

def duplicate_servers(servers):
    show_servers_list(servers)
    sel = ask_multi("Номера для дублирования: ", 1, len(servers))
    if sel == EXIT or not sel:
        return servers
    new = []
    for idx in sel:
        s = copy.deepcopy(servers[idx - 1])
        s['name'] = f"{s.get('name', '')} (copy)"
        new.append(s)
    servers.extend(new)
    print(f"[+] Создано дубликатов: {len(new)}")
    ans = ask("Отредактировать? (y/n) [n]: ", default="n")
    if ans.lower() == 'y':
        new_indices = list(range(len(servers) - len(new), len(servers)))
        edit_params_for_group(servers, new_indices)
    return servers

# Список редактируемых параметров
PARAM_LIST = [
    ("scheme", "Протокол"), ("type", "Транспорт"), ("security", "Безопасность"),
    ("flow", "Flow"), ("path", "Path"), ("host", "Host"), ("sni", "SNI"),
    ("pbk", "PublicKey"), ("sid", "ShortId"), ("fp", "Fingerprint"),
    ("serviceName", "ServiceName"), ("authority", "Authority"), ("mode", "Mode"),
    ("port", "Порт"), ("host_addr", "Адрес"), ("alpn", "ALPN"),
    ("obfs", "Obfs"), ("obfs-password", "Obfs-password"),
    ("id", "UUID / логин"), ("password", "Пароль"), ("method", "Метод SS"),
    ("concurrency", "Concurrency"), ("spiderX", "SpiderX"), ("headerType", "Header Type"),
    ("heartbeatPeriod", "HeartbeatPeriod"), ("alterId", "AlterID"), ("encryption", "Шифрование"),
    ("allowedIPs", "AllowedIPs"), ("mtu", "MTU"), ("dns", "DNS"),
    ("presharedKey", "PresharedKey"), ("keepalive", "Keepalive"),
    ("up", "Up"), ("down", "Down"), ("congestion_control", "Congestion Control"),
    ("pinned_certchain_sha256", "PinnedCertHash"), ("verify_peer_cert_by_name", "VerifyPeerCertByName"),
    ("jc", "Jc"), ("jmin", "Jmin"), ("jmax", "Jmax"),
    ("s1", "S1"), ("s2", "S2"), ("h1", "H1"), ("h2", "H2"), ("h3", "H3"), ("h4", "H4"),
]

CHOICES_MAP = {
    "scheme": ["vless", "vmess", "trojan", "hysteria2", "hysteria", "ss", "socks5", "http", "tuic", "juicity", "wireguard", "amneziawg", "mieru", "sudoku", "openconnect"],
    "type": ["tcp", "ws", "grpc", "xhttp", "splithttp", "httpupgrade", "h2", "kcp", "quic"],
    "security": ["none", "tls", "reality"],
    "flow": ["xtls-rprx-vision", ""],
    "fp": ["chrome", "firefox", "safari", "ios", "android", "edge", "360", "qq", "random", "randomized"],
    "mode": ["auto", "packet-up", "stream-up", "stream-one", "multi"],
    "headerType": ["none", "http"],
    "alpn": ["h3", "h2", "http/1.1", "h3,h2", "h2,http/1.1"],
    "congestion_control": ["cubic", "new_reno", "bbr"],
    "encryption": ["auto", "none", "zero"],
}

COMPAT = {
    "flow": lambda s: s['scheme'] == 'vless' and s['params'].get('type', 'tcp') == 'tcp' and s['params'].get('security') == 'reality',
    "pbk": lambda s: s['scheme'] == 'vless' and s['params'].get('security') == 'reality',
    "sid": lambda s: s['scheme'] == 'vless' and s['params'].get('security') == 'reality',
    "sni": lambda s: s['scheme'] in ('vless', 'hysteria2', 'trojan', 'tuic', 'juicity', 'vmess'),
    "fp": lambda s: s['scheme'] in ('vless', 'trojan', 'vmess'),
    "serviceName": lambda s: s['scheme'] in ('vless', 'vmess') and s['params'].get('type') == 'grpc',
    "authority": lambda s: s['scheme'] in ('vless', 'vmess') and s['params'].get('type') == 'grpc',
    "path": lambda s: s['scheme'] in ('vless', 'vmess') and s['params'].get('type') in ('ws', 'xhttp', 'splithttp', 'httpupgrade'),
    "host": lambda s: s['scheme'] in ('vless', 'vmess') and s['params'].get('type') in ('ws', 'xhttp', 'splithttp', 'httpupgrade'),
    "mode": lambda s: s['scheme'] in ('vless', 'vmess') and s['params'].get('type') in ('grpc', 'xhttp', 'splithttp'),
    "concurrency": lambda s: s['scheme'] in ('vless', 'vmess') and s['params'].get('type') in ('xhttp', 'splithttp'),
    "obfs": lambda s: s['scheme'] == 'hysteria2',
    "obfs-password": lambda s: s['scheme'] == 'hysteria2',
    "alpn": lambda s: s['params'].get('security') == 'tls' or s['scheme'] in ('hysteria2', 'tuic', 'juicity'),
    "method": lambda s: s['scheme'] == 'ss',
    "id": lambda s: s['scheme'] in ('vless', 'vmess', 'trojan', 'tuic', 'juicity', 'wireguard', 'amneziawg', 'mieru', 'sudoku', 'openconnect'),
    "password": lambda s: s['scheme'] in ('hysteria2', 'hysteria', 'ss', 'trojan', 'tuic', 'juicity', 'mieru', 'sudoku'),
    "spiderX": lambda s: s['scheme'] == 'vless' and s['params'].get('security') == 'reality',
    "headerType": lambda s: s['scheme'] in ('vless', 'vmess') and s['params'].get('type') == 'tcp' and s['params'].get('security') != 'reality',
    "heartbeatPeriod": lambda s: s['scheme'] in ('vless', 'vmess') and s['params'].get('type') == 'ws',
    "alterId": lambda s: s['scheme'] == 'vmess',
    "encryption": lambda s: s['scheme'] == 'vmess',
    "allowedIPs": lambda s: s['scheme'] == 'wireguard',
    "mtu": lambda s: s['scheme'] in ('wireguard', 'amneziawg'),
    "dns": lambda s: s['scheme'] in ('wireguard', 'amneziawg'),
    "presharedKey": lambda s: s['scheme'] == 'wireguard',
    "keepalive": lambda s: s['scheme'] == 'wireguard',
    "up": lambda s: s['scheme'] == 'hysteria',
    "down": lambda s: s['scheme'] == 'hysteria',
    "congestion_control": lambda s: s['scheme'] in ('tuic', 'juicity'),
    "pinned_certchain_sha256": lambda s: s['params'].get('security') == 'tls',
    "verify_peer_cert_by_name": lambda s: s['params'].get('security') == 'tls',
    "jc": lambda s: s['scheme'] in ('amneziawg', 'awg'),
    "jmin": lambda s: s['scheme'] in ('amneziawg', 'awg'),
    "jmax": lambda s: s['scheme'] in ('amneziawg', 'awg'),
    "s1": lambda s: s['scheme'] in ('amneziawg', 'awg'),
    "s2": lambda s: s['scheme'] in ('amneziawg', 'awg'),
    "h1": lambda s: s['scheme'] in ('amneziawg', 'awg'),
    "h2": lambda s: s['scheme'] in ('amneziawg', 'awg'),
    "h3": lambda s: s['scheme'] in ('amneziawg', 'awg'),
    "h4": lambda s: s['scheme'] in ('amneziawg', 'awg'),
}

SS_METHODS = [
    "aes-128-gcm", "aes-256-gcm", "chacha20-poly1305", "chacha20-ietf-poly1305",
    "xchacha20-poly1305", "xchacha20-ietf-poly1305", "2022-blake3-aes-128-gcm",
    "2022-blake3-aes-256-gcm", "2022-blake3-chacha20-poly1305", "none"
]

def get_param_current(s, pkey):
    if pkey == 'port':
        return s.get('port', '')
    if pkey == 'host_addr':
        return s.get('host', '')
    if pkey == 'scheme':
        return s.get('scheme', '')
    if pkey in ('id', 'password', 'method'):
        return s.get(pkey, '')
    return s['params'].get(pkey, '')

# Блок редактирования параметров группы
def edit_params_for_group(servers, indices):
    if not indices:
        return
    while True:
        clr()
        hdr("РЕДАКТИРОВАНИЕ ГРУППЫ")
        print(f"  Выбрано серверов: {len(indices)}")
        for i in indices[:25]:
            s = servers[i]
            print(f"    {i+1}. {s.get('name', '')[:32]} [{s['scheme']}] {s['host']}:{s['port']}")
        if len(indices) > 25:
            print(f"    ... и ещё {len(indices) - 25}")
        ln()
        for idx, (k, desc) in enumerate(PARAM_LIST, 1):
            print(f"  {idx:2}. {desc}")
        print("   q. Назад")
        ch = ask("Выбор: ")
        if ch == EXIT or ch == "0":
            break
        try:
            pi = int(ch) - 1
        except Exception:
            continue
        if pi < 0 or pi >= len(PARAM_LIST):
            continue
        pkey, pname = PARAM_LIST[pi]
        compat_fn = COMPAT.get(pkey)
        compatible = [i for i in indices if compat_fn is None or compat_fn(servers[i])]
        if not compatible:
            print("[!] Нет совместимых серверов в выборке.")
            input("Enter...")
            continue
        clr()
        hdr(f"ИЗМЕНЕНИЕ: {pname}")
        print(f"  Совместимых: {len(compatible)} / всего в выборке: {len(indices)}")
        print(f"  Будут изменены: {len(compatible)}")
        if len(indices) - len(compatible) > 0:
            print(f"  Несовместимых: {len(indices) - len(compatible)}")
        print()
        for i in compatible[:15]:
            s = servers[i]
            cur = get_param_current(s, pkey)
            print(f"    {i+1}. {s.get('name', '')[:28]} -> {cur}")
        if len(compatible) > 15:
            print(f"    ... и ещё {len(compatible) - 15}")
        cur_default = ''
        for i in compatible:
            v = get_param_current(servers[i], pkey)
            if v:
                cur_default = str(v)
                break
        if not cur_default:
            cur_default = PARAM_DEFAULTS.get(pkey, '')
        ln()
        if pkey == "scheme":
            print(f"  Варианты: {', '.join(CHOICES_MAP['scheme'])}")
        elif pkey in CHOICES_MAP:
            print(f"  Варианты: {', '.join(CHOICES_MAP[pkey])}")
        elif pkey == "method":
            print(f"  Варианты: {', '.join(SS_METHODS)}")
        print(f"  Значение по умолчанию: {cur_default}")
        print("  Enter = применить значение по умолчанию")
        print("  '-'   = удалить параметр")
        print("  q     = отмена")
        try:
            raw = input(f"Новое значение [{cur_default}]: ").strip()
        except (EOFError, KeyboardInterrupt):
            continue
        if raw.lower() in ('q', 'exit', 'back', 'назад'):
            continue
        if raw == '-':
            nv = ''
        elif raw == '':
            nv = cur_default
        else:
            nv = raw
        for i in compatible:
            s = servers[i]
            if pkey == "scheme":
                s['scheme'] = nv
            elif pkey == "port":
                s['port'] = nv
            elif pkey == "host_addr":
                s['host'] = nv
            elif pkey in ("id", "password", "method"):
                s[pkey] = nv
            else:
                if nv == "":
                    s['params'].pop(pkey, None)
                else:
                    s['params'][pkey] = nv
        print(f"\n[+] Обновлено: {len(compatible)}")

# Блок редактирования серверов
def edit_servers(servers):
    while True:
        clr()
        hdr("РЕДАКТИРОВАНИЕ СЕРВЕРОВ")
        show_servers_list(servers)
        print(f"\n  Всего: {len(servers)}")
        ln()
        print("  1 - Имена")
        print("  2 - Параметры (группа)")
        print("  3 - Удалить по номерам")
        print("  4 - Удалить по фильтру")
        print("  5 - Добавить сервер вручную")
        print("  6 - Удалить дубликаты")
        print("  7 - Сортировка")
        print("  8 - Переместить сервер")
        print("  9 - Создать дубликаты")
        print(" 10 - Поиск по ключевому слову")
        print(" 11 - Показать параметры сервера")
        print("  q - Готово")
        ch = ask("Выбор: ", choices=[str(i) for i in range(1, 12)])
        if ch == EXIT or ch == "0":
            break
        if ch == "1":
            sub = ask("1-Все с суффиксами / 2-Группу / 3-По одному / 4-Добавить префикс / q-назад: ", choices=["1", "2", "3", "4"])
            if sub == EXIT:
                continue
            if sub == "1":
                base = ask("Базовое имя (q - отмена): ")
                if base == EXIT or not base:
                    continue
                for i, s in enumerate(servers):
                    s['name'] = f"{base}-{i + 1}"
                print("[+] Обновлено.")
            elif sub == "2":
                sel = ask_multi("Номера (q - отмена): ", 1, len(servers))
                if sel == EXIT or not sel:
                    continue
                base = ask("Базовое имя: ")
                if base == EXIT or not base:
                    continue
                for idx in sel:
                    servers[idx - 1]['name'] = f"{base}-{idx}"
                print("[+] Обновлено.")
            elif sub == "3":
                sel = ask_multi("Номера (q - отмена): ", 1, len(servers))
                if sel == EXIT or not sel:
                    continue
                for idx in sel:
                    cur = servers[idx - 1].get('name', '')
                    nn = ask(f"  {idx}. '{cur}' -> (q-пропустить): ")
                    if nn == EXIT or not nn:
                        continue
                    servers[idx - 1]['name'] = nn
                print("[+] Обновлено.")
            elif sub == "4":
                pre = ask("Префикс (q - отмена): ")
                if pre == EXIT or not pre:
                    continue
                for s in servers:
                    s['name'] = f"{pre}{s.get('name', '')}"
                print("[+] Обновлено.")
        elif ch == "2":
            sel = ask_multi("Номера серверов для редактирования: ", 1, len(servers))
            if sel == EXIT or not sel:
                continue
            edit_params_for_group(servers, [i - 1 for i in sel])
        elif ch == "3":
            sel = ask_multi("Номера для удаления: ", 1, len(servers))
            if sel == EXIT or not sel:
                continue
            ans = ask(f"Удалить {len(sel)} сервер(ов)? (y/n) [n]: ", default="n")
            if ans.lower() == 'y':
                for i in sorted(sel, reverse=True):
                    servers.pop(i - 1)
                print(f"[+] Удалено: {len(sel)}")
        elif ch == "4":
            servers = delete_by_keyword(servers)
        elif ch == "5":
            uri = ask("Ссылка (q - отмена): ")
            if uri == EXIT or not uri:
                continue
            p = parse_uri(uri)
            if p:
                servers.append(p)
                print("[+] Добавлен.")
            else:
                print("[!] Не удалось распарсить.")
        elif ch == "6":
            servers = dedupe_menu(servers)
        elif ch == "7":
            servers = sort_servers(servers)
        elif ch == "8":
            servers = move_server(servers)
        elif ch == "9":
            servers = duplicate_servers(servers)
        elif ch == "10":
            kw = ask("Ключевое слово (q - отмена): ").lower()
            if kw == EXIT:
                continue
            found = [(i + 1, s) for i, s in enumerate(servers)
                     if kw in s.get('name', '').lower() or kw in s['host'].lower() or kw in s['scheme']]
            if found:
                print(f"\n[+] Найдено: {len(found)}")
                for n, s in found:
                    print(f"   {n}. {s.get('name', '')} [{s['scheme']}://{s['host']}:{s['port']}]")
            else:
                print("[!] Ничего не найдено.")
            input("Enter...")
        elif ch == "11":
            idx = ask_int("Номер сервера (q - отмена): ", mn=1, mx=len(servers))
            if idx == EXIT or idx is None:
                continue
            s = servers[idx - 1]
            print(f"\n  URI: {build_uri(s)}")
            print(f"  Scheme: {s['scheme']}")
            print(f"  Host: {s['host']}")
            print(f"  Port: {s['port']}")
            print(f"  ID/Pass/Method: {s.get('id') or s.get('password') or s.get('method')}")
            print(f"  Params: {json.dumps(s['params'], ensure_ascii=False, indent=4)}")
            input("Enter...")
    return servers

# Блок генерации outbound
def gen_outbound(s, tag, cfg):
    scheme = s['scheme']
    host = s['host']
    try:
        port = int(s['port']) if str(s['port']).isdigit() else 443
    except Exception:
        port = 443
    out = {}
    if scheme == 'vless':
        out = {
            "protocol": "vless",
            "settings": {"vnext": [{"address": host, "port": port,
                                    "users": [{"id": s.get('id', ''), "encryption": "none", "flow": s['params'].get('flow', '')}]}]},
            "streamSettings": {"network": s['params'].get('type', 'tcp'), "security": s['params'].get('security', 'none')},
            "tag": tag
        }
        sec = out["streamSettings"]["security"]
        if sec == 'reality':
            rs = {"serverName": s['params'].get('sni', ''),
                  "fingerprint": s['params'].get('fp', 'chrome'),
                  "publicKey": s['params'].get('pbk', ''),
                  "shortId": s['params'].get('sid', '')}
            if 'spiderX' in s['params']:
                rs["spiderX"] = s['params']['spiderX']
            out["streamSettings"]["realitySettings"] = rs
        elif sec == 'tls':
            tls = {"serverName": s['params'].get('sni', host)}
            if 'alpn' in s['params']:
                tls["alpn"] = [a.strip() for a in str(s['params']['alpn']).split(',') if a.strip()]
            if 'fp' in s['params']:
                tls["fingerprint"] = s['params']['fp']
            if 'pinned_certchain_sha256' in s['params']:
                tls["pinnedPeerCertSha256"] = s['params']['pinned_certchain_sha256']
            if 'verify_peer_cert_by_name' in s['params']:
                tls["verifyPeerCertByName"] = s['params']['verify_peer_cert_by_name']
            out["streamSettings"]["tlsSettings"] = tls
        net = out["streamSettings"]["network"]
        if net == 'ws':
            ws = {"path": s['params'].get('path', '/'), "headers": {"Host": s['params'].get('host', host)}}
            if 'heartbeatPeriod' in s['params']:
                try:
                    ws["heartbeatPeriod"] = int(s['params']['heartbeatPeriod'])
                except Exception:
                    pass
            out["streamSettings"]["wsSettings"] = ws
        elif net == 'grpc':
            gs = {"serviceName": s['params'].get('serviceName', ''),
                  "multiMode": s['params'].get('mode', '') == 'multi'}
            if 'authority' in s['params']:
                gs["authority"] = s['params']['authority']
            out["streamSettings"]["grpcSettings"] = gs
        elif net == 'tcp':
            out["streamSettings"]["tcpSettings"] = {"header": {"type": s['params'].get('headerType', 'none')}}
        elif net in ('xhttp', 'splithttp'):
            xh = {"path": s['params'].get('path', '/'),
                  "host": s['params'].get('host', host),
                  "mode": s['params'].get('mode', 'auto')}
            if 'concurrency' in s['params']:
                try:
                    xh["concurrency"] = int(s['params']['concurrency'])
                except Exception:
                    pass
            out["streamSettings"]["xhttpSettings"] = xh
        elif net == 'httpupgrade':
            out["streamSettings"]["httpupgradeSettings"] = {
                "path": s['params'].get('path', '/'),
                "host": s['params'].get('host', host)}
    elif scheme == 'vmess':
        out = {
            "protocol": "vmess",
            "settings": {"vnext": [{"address": host, "port": port,
                                    "users": [{"id": s.get('id', ''), "alterId": int(s['params'].get('alterId', 0)) if str(s['params'].get('alterId', '0')).isdigit() else 0,
                                               "security": s['params'].get('encryption', 'auto')}]}]},
            "streamSettings": {"network": s['params'].get('type', 'tcp'), "security": s['params'].get('security', 'none')},
            "tag": tag
        }
        sec = out["streamSettings"]["security"]
        if sec == 'tls':
            tls = {"serverName": s['params'].get('sni', host)}
            if 'alpn' in s['params']:
                tls["alpn"] = [a.strip() for a in str(s['params']['alpn']).split(',') if a.strip()]
            out["streamSettings"]["tlsSettings"] = tls
        net = out["streamSettings"]["network"]
        if net == 'ws':
            out["streamSettings"]["wsSettings"] = {
                "path": s['params'].get('path', '/'),
                "headers": {"Host": s['params'].get('host', host)}}
        elif net == 'grpc':
            out["streamSettings"]["grpcSettings"] = {
                "serviceName": s['params'].get('serviceName', ''),
                "multiMode": s['params'].get('mode', '') == 'multi'}
        elif net == 'tcp':
            out["streamSettings"]["tcpSettings"] = {"header": {"type": s['params'].get('headerType', 'none')}}
    elif scheme in ('hysteria2', 'hy2'):
        out = {
            "protocol": "hysteria2",
            "settings": {"address": host, "port": port, "password": s.get('password', '')},
            "streamSettings": {"network": "hysteria2", "security": "tls",
                               "tlsSettings": {"serverName": s['params'].get('sni', host),
                                               "alpn": [a.strip() for a in str(s['params'].get('alpn', 'h3')).split(',') if a.strip()]}},
            "tag": tag
        }
        if 'obfs' in s['params']:
            out["settings"]["obfs"] = s['params']['obfs']
            if 'obfs-password' in s['params']:
                out["settings"]["obfsPassword"] = s['params']['obfs-password']
    elif scheme == 'hysteria':
        out = {
            "protocol": "hysteria",
            "settings": {"address": host, "port": port, "auth": s.get('password', '')},
            "streamSettings": {"network": "hysteria", "security": "tls",
                               "tlsSettings": {"serverName": s['params'].get('sni', host),
                                               "alpn": [a.strip() for a in str(s['params'].get('alpn', 'h3')).split(',') if a.strip()]}},
            "tag": tag
        }
        if 'up' in s['params']:
            out["settings"]["up"] = s['params']['up']
        if 'down' in s['params']:
            out["settings"]["down"] = s['params']['down']
    elif scheme == 'ss':
        out = {
            "protocol": "shadowsocks",
            "settings": {"servers": [{"address": host, "port": port,
                                      "method": s.get('method', 'aes-256-gcm'),
                                      "password": s.get('password', '')}]},
            "tag": tag
        }
    elif scheme == 'trojan':
        out = {
            "protocol": "trojan",
            "settings": {"servers": [{"address": host, "port": port, "password": s.get('password', '')}]},
            "streamSettings": {"network": s['params'].get('type', 'tcp'), "security": s['params'].get('security', 'tls')},
            "tag": tag
        }
        ts = {"serverName": s['params'].get('sni', host)}
        if 'alpn' in s['params']:
            ts["alpn"] = [a.strip() for a in str(s['params']['alpn']).split(',') if a.strip()]
        if 'pinned_certchain_sha256' in s['params']:
            ts["pinnedPeerCertSha256"] = s['params']['pinned_certchain_sha256']
        if 'verify_peer_cert_by_name' in s['params']:
            ts["verifyPeerCertByName"] = s['params']['verify_peer_cert_by_name']
        out["streamSettings"]["tlsSettings"] = ts
    elif scheme == 'socks5':
        out = {
            "protocol": "socks",
            "settings": {"servers": [{"address": host, "port": port,
                                      "user": s.get('id', ''), "pass": s.get('password', '')}]},
            "tag": tag
        }
    elif scheme == 'http':
        out = {
            "protocol": "http",
            "settings": {"servers": [{"address": host, "port": port,
                                      "user": s.get('id', ''), "pass": s.get('password', '')}]},
            "tag": tag
        }
    elif scheme == 'wireguard':
        peer = {
            "endpoint": f"{host}:{port}",
            "publicKey": s.get('password', ''),
            "allowedIPs": [x.strip() for x in str(s['params'].get('allowedIPs', '0.0.0.0/0')).split(',')],
        }
        if s['params'].get('presharedKey'):
            peer["preSharedKey"] = s['params']['presharedKey']
        if s['params'].get('keepalive'):
            try:
                peer["persistentKeepalive"] = int(s['params']['keepalive'])
            except Exception:
                pass
        out = {
            "protocol": "wireguard",
            "settings": {
                "secretKey": s.get('id', ''),
                "dns": s['params'].get('dns', '1.1.1.1'),
                "mtu": int(s['params'].get('mtu', 1420)) if str(s['params'].get('mtu', '1420')).isdigit() else 1420,
                "peers": [peer]
            },
            "tag": tag
        }
    else:
        return None
    if cfg.get('mux_enabled'):
        mux = {"enabled": True, "concurrency": cfg.get('mux_concurrency', 8)}
        xc = cfg.get('mux_xudp_concurrency', 0)
        if xc != 0:
            mux["xudpConcurrency"] = xc
            mux["xudpProxyUDP443"] = cfg.get('mux_xudp_proxy_udp443', 'reject')
        out["mux"] = mux
    return out

def merge_group_rules(rules, outbound_type):
    domains = []
    others = []
    for r in rules:
        if not isinstance(r, dict):
            continue
        keys = set(r.keys()) - {'outboundTag', 'balancerTag'}
        if r.get('type') == 'field' and keys == {'type', 'domain'}:
            for d in r.get('domain', []):
                if isinstance(d, str):
                    domains.append(d)
        else:
            others.append(r)
    result = []
    if domains:
        deduped = process_domain_list(domains)
        rule = {'type': 'field', 'domain': deduped}
        if outbound_type == 'proxy':
            rule['balancerTag'] = 'balancer'
        else:
            rule['outboundTag'] = outbound_type
        result.append(rule)
    result.extend(others)
    return result

# Блок генерации конфига
def gen_config(servers, cfg):
    outbounds = []
    tags = []
    unsupported = []
    for i, s in enumerate(servers):
        base_tag = re.sub(r'[^a-zA-Z0-9_\-]', '_', s.get('name', f"proxy-{i + 1}")) or f"proxy-{i + 1}"
        tag = base_tag
        c = 1
        while tag in tags:
            tag = f"{base_tag}_{c}"
            c += 1
        out = gen_outbound(s, tag, cfg)
        if out:
            tags.append(tag)
            outbounds.append(out)
        else:
            unsupported.append(s.get('name', s['scheme']))
    if unsupported:
        print(f"[!] Пропущены неподдерживаемые Xray протоколы: {', '.join(unsupported)}")
    outbounds.append({"protocol": "freedom", "tag": "direct"})
    outbounds.append({"protocol": "blackhole", "tag": "block"})

    rt = cfg.get('routing', {})
    order = cfg.get('routing_order', ["block", "direct", "proxy"])
    groups = {'block': [], 'direct': [], 'proxy': []}

    if rt.get('block_protocols'):
        groups['block'].append({"type": "field", "protocol": rt['block_protocols'], "outboundTag": "block"})
    if rt.get('block_ips'):
        groups['block'].append({"type": "field", "ip": rt['block_ips'], "outboundTag": "block"})
    if rt.get('block_ports'):
        groups['block'].append({"type": "field", "port": rt['block_ports'], "outboundTag": "block"})
    if rt.get('block_domains'):
        groups['block'].append({"type": "field", "domain": rt['block_domains'], "outboundTag": "block"})

    if rt.get('direct_ips'):
        groups['direct'].append({"type": "field", "ip": rt['direct_ips'], "outboundTag": "direct"})
    if rt.get('direct_ports'):
        groups['direct'].append({"type": "field", "port": rt['direct_ports'], "outboundTag": "direct"})
    if rt.get('direct_domains'):
        groups['direct'].append({"type": "field", "domain": rt['direct_domains'], "outboundTag": "direct"})

    for r in rt.get('custom_rules', []):
        if not isinstance(r, dict):
            continue
        tag = r.get('outboundTag') or r.get('balancerTag', '')
        if tag == 'block':
            groups['block'].append(r)
        elif tag == 'direct':
            groups['direct'].append(r)
        else:
            r2 = dict(r)
            r2.pop('outboundTag', None)
            r2['balancerTag'] = 'balancer'
            groups['proxy'].append(r2)

    rules = []
    for name in order:
        rules.extend(merge_group_rules(groups.get(name, []), name))

    gp = cfg.get('global_proxy', 'proxy')
    if gp == 'direct':
        rules.append({"type": "field", "network": "tcp,udp", "outboundTag": "direct"})
    elif gp == 'block':
        rules.append({"type": "field", "network": "tcp,udp", "outboundTag": "block"})
    else:
        rules.append({"type": "field", "network": "tcp,udp", "balancerTag": "balancer"})

    expected = normalize_int(cfg.get('balancer_expected', 3), 3, 1, 999)
    if len(tags) > 0 and expected > len(tags):
        print(f"[!] expected={expected} больше числа серверов ({len(tags)}). Установлено {len(tags)}.")
        expected = len(tags)

    balancer = {
        "tag": "balancer", "selector": tags,
        "strategy": {"type": normalize_balancer_type(cfg.get('balancer_strategy', 'leastLoad')),
                     "settings": {"expected": expected,
                                  "maxRTT": normalize_duration(cfg.get('balancer_max_rtt', '2s'), 's'),
                                  "tolerance": normalize_float(cfg.get('balancer_tolerance', 0), 0.0),
                                  "baselines": [normalize_duration(b, 's') for b in cfg.get('balancer_baselines', ['2s'])]}}
    }
    if tags:
        balancer["fallbackTag"] = tags[0]
    observatory = {
        "subjectSelector": tags,
        "probeUrl": cfg.get('observatory_url', 'https://www.google.com/generate_204'),
        "probeInterval": normalize_duration(cfg.get('observatory_interval', '1m'), 'm'),
        "probeTimeout": normalize_duration(cfg.get('observatory_timeout', '3s'), 's'),
        "enableConcurrency": True
    }
    dns = {"servers": cfg.get('dns_servers', DNS_SERVERS),
           "queryStrategy": cfg.get('dns_query_strategy', 'UseIP')}
    p_socks, p_http = cfg.get('proxy_ports', [10808, 10809])
    sniffing = {
        "enabled": cfg.get('sniffing_enabled', True),
        "destOverride": cfg.get('sniffing_dest_override', ["http", "tls", "quic"]),
        "routeOnly": cfg.get('sniffing_route_only', True)
    }
    inbounds = [
        {"listen": "127.0.0.1", "port": p_socks, "protocol": "socks",
         "settings": {"auth": "noauth", "udp": True}, "sniffing": sniffing, "tag": "socks"},
        {"listen": "127.0.0.1", "port": p_http, "protocol": "http",
         "settings": {"allowTransparent": False}, "sniffing": sniffing, "tag": "http"}
    ]
    return {
        "remarks": cfg.get('json_remarks', 'SubManager Auto'),
        "log": {"loglevel": "warning"},
        "dns": dns,
        "inbounds": inbounds,
        "outbounds": outbounds,
        "routing": {"domainStrategy": "IPIfNonMatch", "rules": rules, "balancers": [balancer]},
        "observatory": observatory
    }

# Блок нормализации конфига
def normalize_existing_config_file(path):
    hdr("НОРМАЛИЗАЦИЯ СУЩЕСТВУЮЩЕГО КОНФИГА")
    if not path.exists():
        print(f"[!] Файл не найден: {path}")
        return None
    try:
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception as e:
        print(f"[!] Ошибка чтения JSON: {e}")
        return None
    changes = []
    if 'observatory' in data and isinstance(data['observatory'], dict):
        obs = data['observatory']
        if 'probeInterval' in obs:
            old = obs['probeInterval']
            new = normalize_duration(old, 'm')
            if old != new:
                changes.append(f"observatory.probeInterval: '{old}' -> '{new}'")
                obs['probeInterval'] = new
        if 'probeTimeout' in obs:
            old = obs['probeTimeout']
            new = normalize_duration(old, 's')
            if old != new:
                changes.append(f"observatory.probeTimeout: '{old}' -> '{new}'")
                obs['probeTimeout'] = new
    if 'routing' in data and isinstance(data['routing'], dict):
        rt = data['routing']
        bals = rt.get('balancers', [])
        if isinstance(bals, list):
            for bi, b in enumerate(bals):
                if not isinstance(b, dict):
                    continue
                st = b.get('strategy', {})
                if not isinstance(st, dict):
                    continue
                old_type = st.get('type', '')
                new_type = normalize_balancer_type(old_type)
                if old_type != new_type:
                    changes.append(f"balancers[{bi}].strategy.type: '{old_type}' -> '{new_type}'")
                    st['type'] = new_type
                settings = st.get('settings', {})
                if isinstance(settings, dict):
                    if 'maxRTT' in settings:
                        old = settings['maxRTT']
                        new = normalize_duration(old, 's')
                        if old != new:
                            changes.append(f"balancers[{bi}].strategy.settings.maxRTT: '{old}' -> '{new}'")
                            settings['maxRTT'] = new
                    if 'baselines' in settings and isinstance(settings['baselines'], list):
                        new_bl = []
                        for bval in settings['baselines']:
                            old = bval
                            new = normalize_duration(old, 's')
                            new_bl.append(new)
                            if old != new:
                                changes.append(f"balancers[{bi}].strategy.settings.baselines[]: '{old}' -> '{new}'")
                        settings['baselines'] = new_bl
                    if 'expected' in settings:
                        try:
                            e = int(settings['expected'])
                        except Exception:
                            e = 1
                        if e < 1:
                            changes.append(f"balancers[{bi}].strategy.settings.expected: '{settings['expected']}' -> '1'")
                            settings['expected'] = 1
                    if 'tolerance' in settings:
                        try:
                            t = float(settings['tolerance'])
                        except Exception:
                            t = 0.0
                            changes.append(f"balancers[{bi}].strategy.settings.tolerance: '{settings.get('tolerance')}' -> '0'")
                            settings['tolerance'] = t
        rules = rt.get('rules', [])
        if isinstance(rules, list):
            for ri, r in enumerate(rules):
                if not isinstance(r, dict):
                    continue
                if r.get('outboundTag') == 'proxy':
                    changes.append(f"rules[{ri}]: outboundTag 'proxy' -> balancerTag 'balancer'")
                    del r['outboundTag']
                    r['balancerTag'] = 'balancer'
                if 'domain' in r and isinstance(r['domain'], list):
                    old_domains = list(r['domain'])
                    new_domains = process_domain_list(old_domains)
                    if new_domains != old_domains:
                        diff = len(old_domains) - len(new_domains)
                        changes.append(f"rules[{ri}]: доменов было {len(old_domains)}, стало {len(new_domains)} (TLD->keyword, убрано дочерних: {diff})")
                        r['domain'] = new_domains
    if 'outbounds' in data and isinstance(data['outbounds'], list):
        for oi, ob in enumerate(data['outbounds']):
            if not isinstance(ob, dict):
                continue
            ss = ob.get('streamSettings', {})
            if not isinstance(ss, dict):
                continue
            sec = ss.get('security', 'none')
            if sec == 'tls':
                ts = ss.get('tlsSettings', {})
                if isinstance(ts, dict):
                    if 'allowInsecure' in ts:
                        changes.append(f"outbounds[{oi}].tlsSettings.allowInsecure: удалён")
                        del ts['allowInsecure']
                    if 'verifyPeerCertInNames' in ts:
                        changes.append(f"outbounds[{oi}].tlsSettings.verifyPeerCertInNames -> verifyPeerCertByName")
                        ts['verifyPeerCertByName'] = ts.pop('verifyPeerCertInNames')
                    if 'pinnedPeerCertificateChainSha256' in ts:
                        changes.append(f"outbounds[{oi}].tlsSettings.pinnedPeerCertificateChainSha256 -> pinnedPeerCertSha256")
                        ts['pinnedPeerCertSha256'] = ts.pop('pinnedPeerCertificateChainSha256')
    if not changes:
        print("[+] Конфиг уже корректен, изменений не требуется.")
        return data
    print(f"[+] Найдено исправлений: {len(changes)}")
    for c in changes:
        print(f"    - {c}")
    ans = ask("\nСохранить исправленный файл? (y/n) [y]: ", default="y")
    if ans.lower() == 'y':
        p = path.parent / (path.stem + "_fixed.json")
        with open(p, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"[+] Сохранено: {p}")
        return data
    return data

def normalize_existing_config_menu():
    hdr("НОРМАЛИЗАЦИЯ СУЩЕСТВУЮЩЕГО КОНФИГА")
    print("  1 - Из папки Output")
    print("  2 - Из папки Input")
    print("  3 - Ввести путь вручную")
    print("  q - Отмена")
    ch = ask("Выбор: ", choices=["1", "2", "3"])
    if ch == EXIT:
        return
    path = None
    if ch == "1":
        files = sorted([p for p in OUTPUT_DIR.glob("*.json") if p.is_file()])
        if not files:
            print("[!] В Output нет JSON файлов.")
            input("Enter...")
            return
        for i, f in enumerate(files, 1):
            print(f"  {i}. {f.name} ({fmt_size(f.stat().st_size)})")
        idx = ask_int("Номер файла: ", mn=1, mx=len(files))
        if idx == EXIT or idx is None:
            return
        path = files[idx - 1]
    elif ch == "2":
        files = sorted([p for p in INPUT_DIR.glob("*.json") if p.is_file()])
        if not files:
            print("[!] В Input нет JSON файлов.")
            input("Enter...")
            return
        for i, f in enumerate(files, 1):
            print(f"  {i}. {f.name} ({fmt_size(f.stat().st_size)})")
        idx = ask_int("Номер файла: ", mn=1, mx=len(files))
        if idx == EXIT or idx is None:
            return
        path = files[idx - 1]
    elif ch == "3":
        p = ask("Путь к файлу (q - отмена): ")
        if p == EXIT or not p:
            return
        path = Path(p)
    if path:
        normalize_existing_config_file(path)
        input("Enter...")

def normalize_existing_servers_menu():
    hdr("НОРМАЛИЗАЦИЯ БЭКАПА СЕРВЕРОВ")
    print("  1 - Из папки Backups")
    print("  2 - Из папки Output")
    print("  3 - Из папки Input")
    print("  4 - Ввести путь вручную")
    print("  q - Отмена")
    ch = ask("Выбор: ", choices=["1", "2", "3", "4"])
    if ch == EXIT:
        return
    path = None
    if ch == "1":
        files = sorted([p for p in BACKUP_DIR.glob("*") if p.is_file()])
    elif ch == "2":
        files = sorted([p for p in OUTPUT_DIR.glob("*.txt") if p.is_file()])
    elif ch == "3":
        files = sorted([p for p in INPUT_DIR.glob("*") if p.is_file()])
    elif ch == "4":
        p = ask("Путь к файлу (q - отмена): ")
        if p == EXIT or not p:
            return
        path = Path(p)
        files = None
    else:
        return
    if files is not None:
        if not files:
            print("[!] Нет файлов.")
            input("Enter...")
            return
        for i, f in enumerate(files, 1):
            print(f"  {i}. {f.name} ({fmt_size(f.stat().st_size)})")
        idx = ask_int("Номер файла: ", mn=1, mx=len(files))
        if idx == EXIT or idx is None:
            return
        path = files[idx - 1]
    if path:
        try:
            raw = path.read_text(encoding='utf-8', errors='ignore')
        except Exception as e:
            print(f"[!] Ошибка чтения: {e}")
            input("Enter...")
            return
        raw2 = auto_decode(raw)
        servers, _ = parse_input(raw2)
        if not servers:
            print("[!] Не удалось распарсить серверы.")
            input("Enter...")
            return
        print(f"[+] Распарсено серверов: {len(servers)}")
        valid = []
        for s in servers:
            if not s.get('host'):
                continue
            if not str(s.get('port', '')).isdigit():
                continue
            s['port'] = str(s['port'])
            valid.append(s)
        print(f"[+] Валидных: {len(valid)}")
        if len(valid) != len(servers):
            print(f"[!] Отброшено некорректных: {len(servers) - len(valid)}")
        ans = ask("Сохранить нормализованный список? (y/n) [y]: ", default="y")
        if ans.lower() == 'y':
            ts = time.strftime("%Y%m%d_%H%M%S")
            out = BACKUP_DIR / f"normalized_{ts}.txt"
            lines = [build_uri(s) for s in valid]
            with open(out, 'w', encoding='utf-8') as f:
                f.write('\n'.join(lines))
            print(f"[+] Сохранено: {out}")
        input("Enter...")

# Блок парсеров правил
def parse_shadowrocket_rules(text):
    rules = []
    stats = {"direct": 0, "proxy": 0, "block": 0, "commented": 0, "url_regex": 0, "skipped": 0}
    proxy_kw = ["PROXY", "SPEEDPROXY", "BESTPROXY", "AIPROXY", "METAPROXY", "TGPROXY", "SPOTIFYPROXY"]
    block_kw = ["REJECT", "REJECT-DROP", "REJECT-200", "REJECT-DICT", "REJECT-TINYGIF", "REJECT-NO-DROP"]
    for raw in text.splitlines():
        s = raw.strip()
        if not s:
            continue
        if s.startswith('#') or s.startswith(';') or s.startswith('//'):
            stats["commented"] += 1
            continue
        if s.startswith('[') and s.endswith(']'):
            continue
        if s.startswith('!'):
            continue
        if 'URL-REGEX' in s:
            stats["url_regex"] += 1
            continue
        if s.startswith('RULE-SET') or s.startswith('DOMAIN-WILDCARD') or s.startswith('AND,') or s.startswith('OR,') or s.startswith('NOT,'):
            stats["skipped"] += 1
            continue
        parts = [p.strip() for p in s.split(',')]
        if len(parts) < 3:
            stats["skipped"] += 1
            continue
        rule_type = parts[0].upper()
        val = parts[1]
        policy = parts[2].upper()
        out = None
        if policy == 'DIRECT':
            out = 'direct'
        elif policy in block_kw:
            out = 'block'
        elif any(p in policy for p in proxy_kw):
            out = 'proxy'
        else:
            stats["skipped"] += 1
            continue
        rule = None
        if rule_type == 'DOMAIN-SUFFIX':
            rule = {"type": "field", "domain": [f"domain:{val}"], "outboundTag": out}
        elif rule_type == 'DOMAIN':
            rule = {"type": "field", "domain": [val], "outboundTag": out}
        elif rule_type == 'DOMAIN-KEYWORD':
            rule = {"type": "field", "domain": [f"keyword:{val}"], "outboundTag": out}
        elif rule_type in ('IP-CIDR', 'IP-CIDR6'):
            rule = {"type": "field", "ip": [val], "outboundTag": out}
        elif rule_type == 'GEOIP':
            rule = {"type": "field", "ip": [f"geoip:{val.lower()}"], "outboundTag": out}
        elif rule_type == 'DST-PORT':
            rule = {"type": "field", "port": val, "outboundTag": out}
        elif rule_type == 'PROTOCOL':
            rule = {"type": "field", "protocol": [val.lower()], "outboundTag": out}
        if rule:
            rules.append(rule)
            stats[out] += 1
        else:
            stats["skipped"] += 1
    return rules, stats

def parse_adguard_rules(text):
    rules = []
    stats = {"block": 0, "skipped": 0}
    for raw in text.splitlines():
        s = raw.strip()
        if not s or s.startswith(('!', '#', '@@')):
            continue
        if s.startswith(('||', '|')):
            d = s.lstrip('|').rstrip('^').strip()
            if d:
                rules.append({"type": "field", "domain": [f"domain:{d}"], "outboundTag": "block"})
                stats["block"] += 1
    return rules, stats

def parse_blocklist_rules(text):
    rules = []
    stats = {"domain": 0, "ip": 0, "keyword": 0, "skipped": 0}
    for raw in text.splitlines():
        s = raw.strip()
        if not s or s.startswith(('!', '#', ';', '[', '//')):
            continue
        if s.startswith('@@'):
            continue
        if s.startswith('||'):
            d = s[2:].rstrip('^').strip()
            if d and '.' in d:
                rules.append({"type": "field", "domain": [f"domain:{d}"], "outboundTag": "block"})
                stats["domain"] += 1
            else:
                stats["skipped"] += 1
            continue
        if ',' in s:
            parts = [p.strip() for p in s.split(',')]
            rt = parts[0].upper()
            val = parts[1] if len(parts) > 1 else ''
            if not val:
                stats["skipped"] += 1
                continue
            if rt in ('DOMAIN-SUFFIX', 'DOMAIN'):
                rules.append({"type": "field", "domain": [f"domain:{val}"], "outboundTag": "block"})
                stats["domain"] += 1
            elif rt == 'DOMAIN-KEYWORD':
                rules.append({"type": "field", "domain": [f"keyword:{val}"], "outboundTag": "block"})
                stats["keyword"] += 1
            elif rt in ('IP-CIDR', 'IP-CIDR6'):
                rules.append({"type": "field", "ip": [val], "outboundTag": "block"})
                stats["ip"] += 1
            elif rt == 'GEOIP':
                rules.append({"type": "field", "ip": [f"geoip:{val.lower()}"], "outboundTag": "block"})
                stats["ip"] += 1
            else:
                if '.' in val and re.fullmatch(r'[A-Za-z0-9._\-]+', val):
                    rules.append({"type": "field", "domain": [f"domain:{val}"], "outboundTag": "block"})
                    stats["domain"] += 1
                else:
                    stats["skipped"] += 1
            continue
        if re.fullmatch(r'[A-Za-z0-9._\-]+', s) and '.' in s and not re.fullmatch(r'[\d.]+', s):
            rules.append({"type": "field", "domain": [f"domain:{s}"], "outboundTag": "block"})
            stats["domain"] += 1
        elif re.fullmatch(r'[\d.]{7,}', s) or re.fullmatch(r'[0-9a-fA-F:]+/\d+', s):
            rules.append({"type": "field", "ip": [s], "outboundTag": "block"})
            stats["ip"] += 1
        else:
            stats["skipped"] += 1
    return rules, stats

def import_routing_rules(cfg):
    hdr("ИМПОРТ ПРАВИЛ МАРШРУТИЗАЦИИ")
    print("  1 - Shadowrocket / Clash / Surge")
    print("  2 - AdGuard")
    print("  3 - Blocklist без политики")
    print("  q - Отмена")
    ch = ask("Выбор: ", choices=["1", "2", "3"])
    if ch == EXIT:
        return cfg
    parser = {"1": parse_shadowrocket_rules, "2": parse_adguard_rules, "3": parse_blocklist_rules}[ch]

    print("  1 - Из локального файла")
    print("  2 - По ссылке")
    ch2 = ask("Выбор: ", choices=["1", "2"])
    if ch2 == EXIT:
        return cfg
    raw = ""
    if ch2 == "1":
        files = sorted([p for p in ROUTING_DIR.glob("*") if p.is_file()])
        if not files:
            print(f"[!] Папка {ROUTING_DIR} пуста.")
            input("Enter...")
            return cfg
        for i, f in enumerate(files, 1):
            print(f"  {i}. {f.name} ({fmt_size(f.stat().st_size)})")
        idx = ask_int("Номер файла (q - отмена): ", mn=1, mx=len(files))
        if idx == EXIT or idx is None:
            return cfg
        raw = files[idx - 1].read_text(encoding='utf-8', errors='ignore')
    else:
        url = ask("URL (q - отмена): ")
        if url == EXIT or not url:
            return cfg
        raw = dl_url(url)
        if not raw:
            print("[!] Не удалось загрузить.")
            input("Enter...")
            return cfg

    rules, stats = parser(raw)
    if not rules:
        print("[!] Правила не найдены.")
        input("Enter...")
        return cfg

    print(f"\n[+] Найдено правил: {len(rules)}")
    for k, v in stats.items():
        if v:
            print(f"    {k}: {v}")

    ans = ask(f"\nДобавить {len(rules)} правил? (y/n) [y]: ", default="y")
    if ans.lower() == 'y':
        rt = cfg.get('routing', {})
        existing = rt.get('custom_rules', [])
        existing.extend(rules)
        rt['custom_rules'] = existing
        cfg['routing'] = rt
        cfg_save(cfg)
        print(f"[+] Добавлено: {len(rules)}. Всего: {len(existing)}")
    input("Enter...")
    return cfg

# Блок генерации маршрутов
def gen_happ_routing(cfg):
    rt = cfg.get('routing', {})
    profile = {
        "Name": "SubManager Routing",
        "GlobalProxy": cfg.get('global_proxy') == 'proxy',
        "RemoteDNSDomain": "https://cloudflare-dns.com/dns-query",
        "RemoteDNSType": "DoH",
        "DomesticDNSDomain": "https://dns.comss.one/dns-query",
        "DomesticDNSType": "DoH",
        "GeositeUrl": "https://github.com/v2fly/domain-list-community/releases/latest/download/dlc.dat",
        "GeoipUrl": "https://github.com/v2fly/geoip/releases/download/202501090053/geoip.dat",
        "ProxySites": [],
        "DirectSites": rt.get('direct_domains', []),
        "BlockSites": rt.get('block_domains', []),
        "DirectIp": rt.get('direct_ips', []),
        "BlockIp": rt.get('block_ips', []),
        "ProxyIp": [],
        "DomainStrategy": cfg.get('dns_query_strategy', 'IPIfNonMatch'),
        "RouteOrder": "-".join(cfg.get('routing_order', ['block', 'proxy', 'direct'])),
        "DnsHosts": {},
        "UseChunkFiles": False,
        "LastUpdated": 0,
        "RemoteDNSIp": "1.1.1.1",
        "DomesticDNSIp": "83.220.169.155"
    }
    for r in rt.get('custom_rules', []):
        tag = r.get('outboundTag', '')
        domains = r.get('domain', [])
        ips = r.get('ip', [])
        if tag == 'proxy':
            for d in domains:
                profile["ProxySites"].append(d)
        elif tag == 'direct':
            for d in domains:
                profile["DirectSites"].append(d)
            for ip in ips:
                profile["DirectIp"].append(ip)
        elif tag == 'block':
            for d in domains:
                profile["BlockSites"].append(d)
            for ip in ips:
                profile["BlockIp"].append(ip)
    return profile

def gen_v2raytun_routing(cfg):
    rt = cfg.get('routing', {})
    rules = []
    for r in rt.get('custom_rules', []):
        rules.append(r)
    if rt.get('block_domains'):
        rules.append({"type": "field", "domain": rt['block_domains'], "outboundTag": "block"})
    if rt.get('block_ips'):
        rules.append({"type": "field", "ip": rt['block_ips'], "outboundTag": "block"})
    if rt.get('direct_domains'):
        rules.append({"type": "field", "domain": rt['direct_domains'], "outboundTag": "direct"})
    if rt.get('direct_ips'):
        rules.append({"type": "field", "ip": rt['direct_ips'], "outboundTag": "direct"})
    return {
        "name": "SubManager",
        "domainStrategy": cfg.get('dns_query_strategy', 'AsIs'),
        "domainMatcher": "hybrid",
        "rules": rules
    }

def routing_menu(cfg):
    while True:
        clr()
        hdr("РОУТИНГ ДЛЯ КЛИЕНТОВ")
        rt = cfg.get('routing', {})
        print(f"  Direct домены: {len(rt.get('direct_domains', []))}")
        print(f"  Block домены:  {len(rt.get('block_domains', []))}")
        print(f"  Direct IP:     {len(rt.get('direct_ips', []))}")
        print(f"  Block IP:      {len(rt.get('block_ips', []))}")
        print(f"  Custom rules:  {len(rt.get('custom_rules', []))}")
        print(f"  Порядок:       {' -> '.join(cfg.get('routing_order', []))}")
        print(f"  Глобальный:    {cfg.get('global_proxy')}")
        ln()
        print("  1 - Импорт правил")
        print("  2 - Просмотр/очистка custom rules")
        print("  3 - Настроить DNS для роутинга")
        print("  4 - Настроить порядок правил")
        print("  5 - Настроить глобальный прокси")
        print("  6 - Сгенерировать happ ссылку")
        print("  7 - Сгенерировать v2raytun ссылку")
        print("  8 - Сохранить JSON роутинга")
        print("  q - Назад")
        ch = ask("Выбор: ", choices=[str(i) for i in range(1, 9)])
        if ch == EXIT:
            break
        if ch == "1":
            cfg = import_routing_rules(cfg)
        elif ch == "2":
            cr = rt.get('custom_rules', [])
            if not cr:
                print("[!] Нет custom rules.")
                input("Enter...")
                continue
            print(f"  Всего: {len(cr)}")
            for i, r in enumerate(cr[:30], 1):
                print(f"  {i:3}. {json.dumps(r, ensure_ascii=False)[:100]}")
            if len(cr) > 30:
                print(f"  ... и ещё {len(cr) - 30}")
            ln()
            print("  1 - Очистить все")
            print("  2 - Удалить по номерам")
            print("  q - Назад")
            s = ask("Выбор: ", choices=["1", "2"])
            if s == "1":
                a = ask("Точно удалить все? (y/n): ", default="n")
                if a.lower() == 'y':
                    cfg['routing']['custom_rules'] = []
                    cfg_save(cfg)
                    print("[+] Очищено.")
            elif s == "2":
                sel = ask_multi("Номера для удаления: ", 1, len(cr))
                if sel and sel != EXIT:
                    for i in sorted(sel, reverse=True):
                        cr.pop(i - 1)
                    cfg['routing']['custom_rules'] = cr
                    cfg_save(cfg)
                    print(f"[+] Удалено: {len(sel)}")
        elif ch == "3":
            v = ask(f"Remote DNS domain [https://cloudflare-dns.com/dns-query]: ", default="")
            if v != EXIT and v:
                cfg['routing_remote_dns'] = v
            v = ask(f"Domestic DNS domain [https://dns.comss.one/dns-query]: ", default="")
            if v != EXIT and v:
                cfg['routing_domestic_dns'] = v
            cfg_save(cfg)
        elif ch == "4":
            print(f"  Текущий: {' -> '.join(cfg.get('routing_order', []))}")
            v = ask("Порядок (block,direct,proxy): ")
            if v == EXIT:
                continue
            parts = [p.strip().lower() for p in v.split(',') if p.strip()]
            if all(p in ('block', 'direct', 'proxy') for p in parts) and len(set(parts)) == 3:
                cfg['routing_order'] = parts
                cfg_save(cfg)
                print("[+] Сохранено.")
            else:
                print("[!] Нужно указать все три.")
        elif ch == "5":
            gp = ask(f"Глобальный прокси [{cfg.get('global_proxy')}]: ", choices=['proxy', 'direct', 'block'])
            if gp != EXIT:
                cfg['global_proxy'] = gp
                cfg_save(cfg)
        elif ch == "6":
            profile = gen_happ_routing(cfg)
            j = json.dumps(profile, ensure_ascii=False)
            b = base64.b64encode(j.encode('utf-8')).decode('ascii')
            link = f"happ://routing/add/{b}"
            p = OUTPUT_DIR / "happ_routing.txt"
            with open(p, 'w', encoding='utf-8') as f:
                f.write(link)
            print(f"[+] Happ routing: {p}")
            input("Enter...")
        elif ch == "7":
            profile = gen_v2raytun_routing(cfg)
            j = json.dumps(profile, ensure_ascii=False)
            b = base64.b64encode(j.encode('utf-8')).decode('ascii')
            link = f"v2rayTun://import_route/{b}"
            p = OUTPUT_DIR / "v2raytun_routing.txt"
            with open(p, 'w', encoding='utf-8') as f:
                f.write(link)
            print(f"[+] v2rayTun routing: {p}")
            input("Enter...")
        elif ch == "8":
            profile = gen_happ_routing(cfg)
            p = OUTPUT_DIR / "routing_profile.json"
            with open(p, 'w', encoding='utf-8') as f:
                f.write(json.dumps(profile, ensure_ascii=False, indent=2))
            print(f"[+] JSON: {p}")
            input("Enter...")
    return cfg

def config_menu(servers, cfg):
    while True:
        clr()
        hdr("НАСТРОЙКИ ГЕНЕРАЦИИ")
        rt = cfg.get('routing', {})
        print(f"  JSON имя файла:  {cfg.get('json_name')}.json")
        print(f"  JSON примечание: {cfg.get('json_remarks')}")
        print(f"  DNS:            {', '.join(cfg.get('dns_servers', [])[:3])}...")
        print(f"  DNS стратегия:  {cfg.get('dns_query_strategy')}")
        print(f"  Probe URL:      {cfg.get('observatory_url')}")
        print(f"  Interval:       {cfg.get('observatory_interval')}")
        print(f"  Timeout:        {cfg.get('observatory_timeout')}")
        print(f"  Balancer:       {cfg.get('balancer_strategy')} (expected={cfg.get('balancer_expected')}, maxRTT={cfg.get('balancer_max_rtt')})")
        print(f"  Порты:          SOCKS {cfg.get('proxy_ports', [10808, 10809])[0]}, HTTP {cfg.get('proxy_ports', [10808, 10809])[1]}")
        print(f"  Mux:            {'ON' if cfg.get('mux_enabled') else 'OFF'}")
        print(f"  Глобальный:     {cfg.get('global_proxy')}")
        print(f"  Sniffing:       {'ON' if cfg.get('sniffing_enabled') else 'OFF'}")
        print(f"  Порядок правил: {' -> '.join(cfg.get('routing_order', []))}")
        print(f"  Custom rules:   {len(rt.get('custom_rules', []))}")
        ln()
        print("  1 - DNS (серверы и стратегия)")
        print("  2 - Обсерватория")
        print("  3 - Балансировщик")
        print("  4 - Порты SOCKS/HTTP")
        print("  5 - Direct домены")
        print("  6 - Block домены")
        print("  7 - Direct/Block IP")
        print("  8 - Block протоколы")
        print("  9 - Порядок применения правил")
        print(" 10 - Импорт правил")
        print(" 11 - Просмотр/очистка custom rules")
        print(" 12 - Глобальный прокси")
        print(" 13 - Mux / XUDP")
        print(" 14 - Sniffing")
        print(" 15 - Имя JSON файла")
        print(" 16 - Примечание JSON-сервера")
        print(" 17 - Сбросить к дефолту")
        print("  q - Назад")
        ch = ask("Выбор: ", choices=[str(i) for i in range(1, 18)])
        if ch == EXIT:
            break
        if ch == "1":
            v = ask(f"DNS через запятую [{','.join(cfg.get('dns_servers', []))}]: ", default="")
            if v == EXIT:
                continue
            if v:
                cfg['dns_servers'] = [x.strip() for x in v.split(',') if x.strip()]
            st = ask(f"Стратегия [{cfg.get('dns_query_strategy')}]: ", choices=['UseIP', 'UseIPv4', 'UseIPv6', 'AsIs'])
            if st != EXIT:
                cfg['dns_query_strategy'] = st
            cfg_save(cfg)
        elif ch == "2":
            u = ask(f"URL [{cfg.get('observatory_url')}]: ", default="")
            if u == EXIT:
                continue
            if u:
                cfg['observatory_url'] = u
            i = ask(f"Интервал [{cfg.get('observatory_interval')}]: ", default="")
            if i != EXIT and i:
                cfg['observatory_interval'] = normalize_duration(i, 'm')
            t = ask(f"Таймаут [{cfg.get('observatory_timeout')}]: ", default="")
            if t != EXIT and t:
                cfg['observatory_timeout'] = normalize_duration(t, 's')
            cfg_save(cfg)
        elif ch == "3":
            st = ask(f"Стратегия [{cfg.get('balancer_strategy')}]: ", choices=['leastLoad', 'leastPing', 'random', 'roundRobin'])
            if st != EXIT:
                cfg['balancer_strategy'] = normalize_balancer_type(st)
            e = ask_int(f"Expected [{cfg.get('balancer_expected')}]: ", default=cfg.get('balancer_expected'))
            if e != EXIT and e is not None:
                cfg['balancer_expected'] = e
            m = ask(f"MaxRTT [{cfg.get('balancer_max_rtt')}]: ", default="")
            if m != EXIT and m:
                cfg['balancer_max_rtt'] = normalize_duration(m, 's')
            tol = ask(f"Tolerance [{cfg.get('balancer_tolerance')}]: ", default="")
            if tol != EXIT and tol:
                cfg['balancer_tolerance'] = normalize_float(tol, 0.0)
            bl = ask(f"Baselines [{','.join(cfg.get('balancer_baselines', ['2s']))}]: ", default="")
            if bl != EXIT and bl:
                cfg['balancer_baselines'] = [normalize_duration(x, 's') for x in bl.split(',') if x.strip()]
            cfg_save(cfg)
        elif ch == "4":
            ps = ask_int(f"SOCKS [{cfg.get('proxy_ports', [10808, 10809])[0]}]: ", default=cfg.get('proxy_ports', [10808, 10809])[0])
            if ps == EXIT:
                continue
            ph = ask_int(f"HTTP [{cfg.get('proxy_ports', [10808, 10809])[1]}]: ", default=cfg.get('proxy_ports', [10808, 10809])[1])
            if ph == EXIT:
                continue
            cfg['proxy_ports'] = [ps, ph]
            cfg_save(cfg)
        elif ch == "5":
            print(f"  Текущие: {rt.get('direct_domains', [])}")
            print(f"  Подсказки: {', '.join(GEOSITE_SUGGESTIONS[:10])}")
            v = ask("Direct домены (через запятую, пусто=очистить, q=отмена): ")
            if v == EXIT:
                continue
            cfg['routing']['direct_domains'] = [x.strip() for x in v.split(',') if x.strip()] if v else []
            cfg_save(cfg)
        elif ch == "6":
            print(f"  Текущие: {rt.get('block_domains', [])}")
            print(f"  Подсказки: {', '.join(GEOSITE_SUGGESTIONS[:10])}")
            v = ask("Block домены (через запятую, пусто=очистить, q=отмена): ")
            if v == EXIT:
                continue
            cfg['routing']['block_domains'] = [x.strip() for x in v.split(',') if x.strip()] if v else []
            cfg_save(cfg)
        elif ch == "7":
            print(f"  Direct IP: {rt.get('direct_ips', [])}")
            print(f"  Подсказки: {', '.join(GEOIP_SUGGESTIONS)}")
            v = ask("Direct IP: ")
            if v != EXIT:
                cfg['routing']['direct_ips'] = [x.strip() for x in v.split(',') if x.strip()] if v else []
            print(f"  Block IP: {rt.get('block_ips', [])}")
            v = ask("Block IP: ")
            if v != EXIT:
                cfg['routing']['block_ips'] = [x.strip() for x in v.split(',') if x.strip()] if v else []
            cfg_save(cfg)
        elif ch == "8":
            print(f"  Текущие: {rt.get('block_protocols', [])}")
            v = ask("Протоколы (через запятую, пусто=очистить, q=отмена): ")
            if v == EXIT:
                continue
            cfg['routing']['block_protocols'] = [x.strip() for x in v.split(',') if x.strip()] if v else []
            cfg_save(cfg)
        elif ch == "9":
            print(f"  Текущий: {' -> '.join(cfg.get('routing_order', []))}")
            v = ask("Порядок (block,direct,proxy): ")
            if v == EXIT:
                continue
            parts = [p.strip().lower() for p in v.split(',') if p.strip()]
            if all(p in ('block', 'direct', 'proxy') for p in parts) and len(set(parts)) == 3:
                cfg['routing_order'] = parts
                cfg_save(cfg)
                print("[+] Сохранено.")
            else:
                print("[!] Нужно указать все три.")
            input("Enter...")
        elif ch == "10":
            cfg = import_routing_rules(cfg)
        elif ch == "11":
            cr = rt.get('custom_rules', [])
            if not cr:
                print("[!] Нет custom rules.")
                input("Enter...")
                continue
            print(f"  Всего: {len(cr)}")
            for i, r in enumerate(cr[:30], 1):
                print(f"  {i:3}. {json.dumps(r, ensure_ascii=False)[:100]}")
            if len(cr) > 30:
                print(f"  ... и ещё {len(cr) - 30}")
            ln()
            print("  1 - Очистить все")
            print("  2 - Удалить по номерам")
            print("  q - Назад")
            s = ask("Выбор: ", choices=["1", "2"])
            if s == "1":
                a = ask("Точно удалить все? (y/n): ", default="n")
                if a.lower() == 'y':
                    cfg['routing']['custom_rules'] = []
                    cfg_save(cfg)
                    print("[+] Очищено.")
            elif s == "2":
                sel = ask_multi("Номера для удаления: ", 1, len(cr))
                if sel and sel != EXIT:
                    for i in sorted(sel, reverse=True):
                        cr.pop(i - 1)
                    cfg['routing']['custom_rules'] = cr
                    cfg_save(cfg)
                    print(f"[+] Удалено: {len(sel)}")
        elif ch == "12":
            gp = ask(f"Глобальный прокси [{cfg.get('global_proxy')}]: ", choices=['proxy', 'direct', 'block'])
            if gp != EXIT:
                cfg['global_proxy'] = gp
            cfg_save(cfg)
        elif ch == "13":
            print(f"  Mux: {'ON' if cfg.get('mux_enabled') else 'OFF'}")
            en = ask("Включить Mux? (y/n/q): ", default="")
            if en == EXIT:
                continue
            if en:
                cfg['mux_enabled'] = en.lower() == 'y'
            if cfg.get('mux_enabled'):
                c = ask_int(f"Concurrency [{cfg.get('mux_concurrency')}]: ", default=cfg.get('mux_concurrency'))
                if c != EXIT and c is not None:
                    cfg['mux_concurrency'] = c
                xc = ask_int(f"XUDP concurrency [{cfg.get('mux_xudp_concurrency')}]: ", default=cfg.get('mux_xudp_concurrency'))
                if xc != EXIT and xc is not None:
                    cfg['mux_xudp_concurrency'] = xc
                xp = ask(f"XUDP proxyUDP443 [{cfg.get('mux_xudp_proxy_udp443')}]: ", choices=['reject', 'skip', 'allow'])
                if xp != EXIT:
                    cfg['mux_xudp_proxy_udp443'] = xp
            cfg_save(cfg)
        elif ch == "14":
            en = ask(f"Sniffing [{cfg.get('sniffing_enabled')}]: ", choices=['y', 'n'])
            if en != EXIT:
                cfg['sniffing_enabled'] = en.lower() == 'y'
            if cfg.get('sniffing_enabled'):
                v = ask(f"DestOverride [{','.join(cfg.get('sniffing_dest_override', []))}]: ", default="")
                if v != EXIT and v:
                    cfg['sniffing_dest_override'] = [x.strip() for x in v.split(',') if x.strip()]
                ro = ask(f"RouteOnly [{cfg.get('sniffing_route_only')}]: ", choices=['y', 'n'])
                if ro != EXIT:
                    cfg['sniffing_route_only'] = ro.lower() == 'y'
            cfg_save(cfg)
        elif ch == "15":
            n = ask(f"Имя JSON файла [{cfg.get('json_name')}]: ", default="")
            if n != EXIT and n:
                cfg['json_name'] = n
                cfg_save(cfg)
        elif ch == "16":
            print(f"  Текущее: {cfg.get('json_remarks')}")
            n = ask(f"Новое примечание [{cfg.get('json_remarks')}]: ", default="")
            if n == EXIT:
                continue
            if n:
                cfg['json_remarks'] = n
                auto = ask("Использовать как имя файла? (y/n) [n]: ", default="n")
                if auto == EXIT:
                    continue
                if auto.lower() == 'y':
                    tr = transliterate(n)
                    cfg['json_name'] = sanitize_filename(tr)
                    cfg['json_use_remarks_as_name'] = True
                else:
                    cfg['json_use_remarks_as_name'] = False
                cfg_save(cfg)
        elif ch == "17":
            a = ask("Сбросить все настройки? (y/n): ", default="n")
            if a.lower() == 'y':
                cfg = cfg_default()
                cfg_save(cfg)
                print("[+] Сброшено.")
    return cfg

def save_base64(servers, name="servers"):
    lines = [build_uri(s) for s in servers]
    raw = '\n'.join(lines)
    b64 = base64.b64encode(raw.encode('utf-8')).decode('ascii')
    p1 = OUTPUT_DIR / f"{name}.txt"
    p2 = OUTPUT_DIR / f"{name}_base64.txt"
    with open(p1, 'w', encoding='utf-8') as f:
        f.write(raw)
    with open(p2, 'w', encoding='utf-8') as f:
        f.write(b64)
    print(f"[+] Ссылки: {p1}")
    print(f"[+] Base64: {p2}")
    print(f"[+] Строк: {len(lines)}")

def export_menu(servers, cfg):
    while True:
        clr()
        hdr("ЭКСПОРТ ВЫБРАННЫХ СЕРВЕРОВ")
        show_servers_list(servers)
        print(f"\n  Всего: {len(servers)}")
        ln()
        print("  1 - Экспорт ссылок (txt + base64)")
        print("  2 - Экспорт JSON Xray")
        print("  q - Назад")
        ch = ask("Выбор: ", choices=["1", "2"])
        if ch == EXIT:
            break
        sel = ask_multi("Номера серверов для экспорта (1,3-5,all): ", 1, len(servers))
        if sel == EXIT or not sel:
            continue
        subset = [servers[i - 1] for i in sel]
        if ch == "1":
            name = ask("Имя файла (без расширения) [servers]: ", default="servers")
            if name == EXIT:
                name = "servers"
            save_base64(subset, name)
        elif ch == "2":
            name = ask("Имя JSON [selected_config]: ", default="selected_config")
            if name == EXIT:
                name = "selected_config"
            remarks = ask(f"Примечание сервера [{cfg.get('json_remarks', 'SubManager')}]: ", default=cfg.get('json_remarks', 'SubManager'))
            if remarks == EXIT:
                remarks = cfg.get('json_remarks', 'SubManager')
            cfg2 = copy.deepcopy(cfg)
            cfg2['json_name'] = name
            save_json(gen_config(subset, cfg2), cfg2, name, remarks)
        input("Enter...")

def save_json(config, cfg, name_override=None, remarks_override=None):
    name = name_override or cfg.get('json_name', 'xray_config')
    if not name.endswith('.json'):
        name += '.json'
    if remarks_override is not None:
        config['remarks'] = remarks_override
    p = OUTPUT_DIR / name
    with open(p, 'w', encoding='utf-8') as f:
        json.dump(config, f, ensure_ascii=False, indent=2)
    print(f"[+] JSON: {p}")
    if 'remarks' in config:
        print(f"    Примечание сервера: {config['remarks']}")
    return p

def ask_json_name_and_remarks(cfg, default_name=None):
    default_name = default_name or cfg.get('json_name', 'xray_config')
    default_remarks = cfg.get('json_remarks', 'SubManager Auto')
    print("\n[?] Настройка имени JSON-сервера")
    print(f"    Текущее имя файла:    {default_name}.json")
    print(f"    Текущее примечание:   {default_remarks}")
    print("    (Enter - оставить текущие, q - отмена)")
    use = ask("Изменить имя/примечание? (y/n) [n]: ", default="n")
    if use == EXIT:
        return None, None
    if use.lower() != 'y':
        return default_name, default_remarks
    remarks = ask(f"Примечание сервера [{default_remarks}]: ", default=default_remarks)
    if remarks == EXIT:
        return None, None
    cfg['json_remarks'] = remarks
    auto = ask("Использовать примечание как имя файла? (y/n) [n]: ", default="n")
    if auto == EXIT:
        return None, None
    if auto.lower() == 'y':
        tr = transliterate(remarks)
        fname = sanitize_filename(tr)
        cfg['json_use_remarks_as_name'] = True
        cfg_save(cfg)
        print(f"    Имя файла будет: {fname}.json")
        return fname, remarks
    else:
        name = ask(f"Имя файла (без .json) [{default_name}]: ", default=default_name)
        if name == EXIT:
            return None, None
        cfg['json_name'] = name
        cfg_save(cfg)
        return name, remarks

def backup_servers(servers, name="backup"):
    ts = time.strftime("%Y%m%d_%H%M%S")
    p = BACKUP_DIR / f"{name}_{ts}.txt"
    lines = [build_uri(s) for s in servers]
    with open(p, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))
    print(f"[+] Backup: {p}")

def stats(servers):
    clr()
    hdr("СТАТИСТИКА")
    if not servers:
        print("  Серверов нет.")
        input("Enter...")
        return
    print(f"  Всего серверов: {len(servers)}")
    by_proto, by_type, by_sec = {}, {}, {}
    for s in servers:
        by_proto[s['scheme']] = by_proto.get(s['scheme'], 0) + 1
        t = s['params'].get('type', 'tcp')
        by_type[t] = by_type.get(t, 0) + 1
        sec = s['params'].get('security', 'none')
        by_sec[sec] = by_sec.get(sec, 0) + 1
    print("\n  По протоколу:")
    for k, v in sorted(by_proto.items()):
        print(f"    {k:15} : {v}")
    print("\n  По транспорту:")
    for k, v in sorted(by_type.items()):
        print(f"    {k:15} : {v}")
    print("\n  По security:")
    for k, v in sorted(by_sec.items()):
        print(f"    {k:15} : {v}")
    input("\nEnter...")

def save_yaml_clash(servers, name="clash_proxies.yaml"):
    lines = ["proxies:"]
    for s in servers:
        n = s.get('name', 'proxy')
        if s['scheme'] == 'vless':
            lines.append(f"  - name: \"{n}\"")
            lines.append(f"    type: vless")
            lines.append(f"    server: {s['host']}")
            lines.append(f"    port: {s['port']}")
            lines.append(f"    uuid: {s.get('id', '')}")
            lines.append(f"    network: {s['params'].get('type', 'tcp')}")
            lines.append(f"    tls: {str(s['params'].get('security') == 'tls').lower()}")
            if s['params'].get('security') == 'reality':
                lines.append(f"    reality-opts:")
                lines.append(f"      public-key: {s['params'].get('pbk', '')}")
                lines.append(f"      short-id: {s['params'].get('sid', '')}")
                lines.append(f"    servername: {s['params'].get('sni', '')}")
            if s['params'].get('flow'):
                lines.append(f"    flow: {s['params']['flow']}")
        elif s['scheme'] == 'ss':
            lines.append(f"  - name: \"{n}\"")
            lines.append(f"    type: ss")
            lines.append(f"    server: {s['host']}")
            lines.append(f"    port: {s['port']}")
            lines.append(f"    cipher: {s.get('method', '')}")
            lines.append(f"    password: \"{s.get('password', '')}\"")
        elif s['scheme'] in ('hysteria2', 'hy2', 'hysteria'):
            lines.append(f"  - name: \"{n}\"")
            lines.append(f"    type: hysteria2")
            lines.append(f"    server: {s['host']}")
            lines.append(f"    port: {s['port']}")
            lines.append(f"    password: \"{s.get('password', '')}\"")
            if 'sni' in s['params']:
                lines.append(f"    sni: {s['params']['sni']}")
        elif s['scheme'] == 'trojan':
            lines.append(f"  - name: \"{n}\"")
            lines.append(f"    type: trojan")
            lines.append(f"    server: {s['host']}")
            lines.append(f"    port: {s['port']}")
            lines.append(f"    password: \"{s.get('password', '')}\"")
            if 'sni' in s['params']:
                lines.append(f"    sni: {s['params']['sni']}")
    p = OUTPUT_DIR / name
    with open(p, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))
    print(f"[+] Clash YAML: {p}")

# ============================================================
# Блок универсального редактора JSON
# ============================================================

FIELD_INFO_HINTS = {
    "Name": "Название конфига",
    "GlobalProxy": "Глобальный прокси true/false",
    "UseChunkFiles": "Использовать чанки true/false",
    "RemoteDns": "Удалённый DNS IP",
    "DomesticDns": "Локальный DNS IP",
    "RemoteDNSType": "Тип удалённого DNS",
    "RemoteDNSDomain": "URL удалённого DNS",
    "RemoteDNSIP": "IP удалённого DNS",
    "DomesticDNSType": "Тип локального DNS",
    "DomesticDNSDomain": "URL локального DNS",
    "DomesticDNSIP": "IP локального DNS",
    "Geoipurl": "URL GeoIP",
    "Geositeurl": "URL GeoSite",
    "LastUpdated": "Время обновления unix",
    "RouteOrder": "Порядок маршрутов",
    "DomainStrategy": "Стратегия домена",
    "FakeDNS": "FakeDNS true/false",
    "DnsHosts": "Объект DNS хостов",
    "DirectSites": "Список прямых сайтов",
    "DirectIp": "Список прямых IP",
    "ProxySites": "Список проксируемых сайтов",
    "ProxyIp": "Список проксируемых IP",
    "BlockSites": "Список блокируемых сайтов",
    "BlockIp": "Список блокируемых IP",
}

PREFERRED_ORDER_HINTS = ["Name","GlobalProxy","UseChunkFiles","RemoteDns","DomesticDns",
                   "RemoteDNSType","RemoteDNSDomain","RemoteDNSIP",
                   "DomesticDNSType","DomesticDNSDomain","DomesticDNSIP",
                   "Geoipurl","Geositeurl","LastUpdated","DnsHosts","RouteOrder",
                   "DirectSites","DirectIp","ProxySites","ProxyIp","BlockSites","BlockIp",
                   "DomainStrategy","FakeDNS"]

def ordered_keys_hint(cfg):
    keys = list(cfg.keys())
    ordered = [k for k in PREFERRED_ORDER_HINTS if k in keys]
    extra = [k for k in keys if k not in ordered]
    return ordered + sorted(extra)

def uje_load_json(path):
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"[!] Ошибка чтения: {e}")
        return None

def uje_save_json(path, data):
    try:
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        print(f"[!] Ошибка записи: {e}")
        return False

def uje_edit_string(cfg, key):
    cur = str(cfg.get(key, ''))
    print(f"  Текущее: {cur}")
    v = ask("  Новое значение (Enter=оставить, '-'=удалить, q=отмена): ")
    if v == EXIT:
        return False
    if v == '-':
        cfg.pop(key, None)
        print("[+] Удалено")
        return True
    if v == '':
        print("[*] Без изменений")
        return False
    cfg[key] = v
    print(f"[+] Обновлено: {key} = {v}")
    return True

def uje_edit_list(cfg, key):
    cur = cfg.get(key, [])
    if not isinstance(cur, list):
        cur = []
    while True:
        clr()
        hdr(f"СПИСОК: {key}")
        print(f"  Элементов: {len(cur)}")
        for i, v in enumerate(cur[:40], 1):
            print(f"    {i:3}. {v}")
        if len(cur) > 40:
            print(f"    ... и ещё {len(cur) - 40}")
        ln()
        print("  1 - Добавить элемент")
        print("  2 - Удалить по номеру")
        print("  3 - Удалить несколько")
        print("  4 - Очистить всё")
        print("  5 - Заменить значение по номеру")
        print("  6 - Удалить поле полностью")
        print("  q - Назад")
        ch = ask("  Выбор: ", choices=["1","2","3","4","5","6"])
        if ch == EXIT:
            return
        if ch == "1":
            while True:
                v = ask("  Значение (Enter = конец): ", default="")
                if v == EXIT or not v:
                    break
                cur.append(v)
                print(f"  [+] Добавлено: {v}")
            cfg[key] = cur
        elif ch == "2":
            if not cur:
                continue
            idx = ask_int("  Номер: ", mn=1, mx=len(cur))
            if idx == EXIT or idx is None:
                continue
            cur.pop(idx-1)
            cfg[key] = cur
            print("[+] Удалено")
        elif ch == "3":
            if not cur:
                continue
            sel = ask("  Номера (например 1,3-5): ")
            if sel == EXIT or not sel:
                continue
            idxs = []
            try:
                for p in sel.split(','):
                    p = p.strip()
                    if '-' in p:
                        a, b = p.split('-', 1)
                        for x in range(int(a), int(b)+1):
                            if 1 <= x <= len(cur) and (x-1) not in idxs:
                                idxs.append(x-1)
                    else:
                        x = int(p)
                        if 1 <= x <= len(cur) and (x-1) not in idxs:
                            idxs.append(x-1)
                for i in sorted(idxs, reverse=True):
                    cur.pop(i)
                cfg[key] = cur
                print(f"[+] Удалено: {len(idxs)}")
            except Exception:
                print("[!] Ошибка разбора")
        elif ch == "4":
            a = ask("  Очистить всё? (y/n) [n]: ", default="n")
            if a.lower() == 'y':
                cfg[key] = []
                print("[+] Очищено")
        elif ch == "5":
            if not cur:
                continue
            idx = ask_int("  Номер для замены: ", mn=1, mx=len(cur))
            if idx == EXIT or idx is None:
                continue
            print(f"  Текущее: {cur[idx-1]}")
            v = ask("  Новое значение: ")
            if v == EXIT or not v:
                continue
            cur[idx-1] = v
            cfg[key] = cur
            print("[+] Заменено")
        elif ch == "6":
            a = ask("  Удалить поле полностью? (y/n) [n]: ", default="n")
            if a.lower() == 'y':
                cfg.pop(key, None)
                print("[+] Поле удалено")
                return
        if ch in ("1", "2", "3", "4", "5"):
            input("Enter...")

def uje_edit_dict(cfg, key):
    cur = cfg.get(key, {})
    if not isinstance(cur, dict):
        cur = {}
    while True:
        clr()
        hdr(f"ОБЪЕКТ: {key}")
        print(f"  Записей: {len(cur)}")
        keys_list = list(cur.keys())
        for i, k in enumerate(keys_list, 1):
            v = str(cur[k])
            if len(v) > 40:
                v = v[:37] + "..."
            print(f"    {i:3}. {k} = {v}")
        ln()
        print("  1 - Добавить запись")
        print("  2 - Изменить запись")
        print("  3 - Удалить запись")
        print("  4 - Удалить поле полностью")
        print("  q - Назад")
        ch = ask("  Выбор: ", choices=["1","2","3","4"])
        if ch == EXIT:
            return
        if ch == "1":
            k = ask("  Ключ: ")
            if k == EXIT or not k:
                continue
            v = ask("  Значение: ")
            if v == EXIT:
                continue
            cur[k] = v
            cfg[key] = cur
            print("[+] Добавлено")
        elif ch == "2":
            if not cur:
                continue
            idx = ask_int("  Номер: ", mn=1, mx=len(cur))
            if idx == EXIT or idx is None:
                continue
            k = keys_list[idx-1]
            print(f"  Текущее значение: {cur[k]}")
            v = ask("  Новое значение: ")
            if v == EXIT or not v:
                continue
            cur[k] = v
            cfg[key] = cur
            print("[+] Обновлено")
        elif ch == "3":
            if not cur:
                continue
            idx = ask_int("  Номер: ", mn=1, mx=len(cur))
            if idx == EXIT or idx is None:
                continue
            k = keys_list[idx-1]
            cur.pop(k)
            cfg[key] = cur
            print("[+] Удалено")
        elif ch == "4":
            a = ask("  Удалить поле полностью? (y/n) [n]: ", default="n")
            if a.lower() == 'y':
                cfg.pop(key, None)
                print("[+] Поле удалено")
                return
        if ch in ("1", "2", "3"):
            input("Enter...")

def uje_add_field(cfg):
    clr()
    hdr("ДОБАВЛЕНИЕ ПОЛЯ")
    sugg = [k for k in FIELD_INFO_HINTS if k not in cfg]
    if sugg:
        print("  Рекомендуемые поля (отсутствующие):")
        for i, k in enumerate(sugg, 1):
            print(f"    {i}. {k} - {FIELD_INFO_HINTS[k]}")
        ln()
    print("  1 - Выбрать из рекомендаций")
    print("  2 - Ввести своё имя")
    print("  q - Назад")
    s = ask("  Выбор: ", choices=["1","2"])
    if s == EXIT:
        return
    new_key = None
    if s == "1":
        if not sugg:
            print("[!] Все рекомендуемые поля уже есть.")
            input("Enter...")
            return
        idx = ask_int("  Номер: ", mn=1, mx=len(sugg))
        if idx == EXIT or idx is None:
            return
        new_key = sugg[idx-1]
    else:
        new_key = ask("  Имя поля: ")
        if new_key == EXIT or not new_key:
            return
    if new_key in cfg:
        print(f"[!] Поле уже существует: {new_key}")
        input("Enter...")
        return
    print(f"\n  Тип поля: 1-строка, 2-список, 3-объект, 4-true/false")
    t = ask("  Тип [1]: ", default="1", choices=["1","2","3","4"])
    if t == EXIT:
        return
    if t == "1":
        v = ask("  Значение: ")
        if v == EXIT:
            return
        cfg[new_key] = v
    elif t == "2":
        cfg[new_key] = []
        while True:
            v = ask("  Элемент (Enter - конец): ", default="")
            if v == EXIT or not v:
                break
            cfg[new_key].append(v)
    elif t == "3":
        cfg[new_key] = {}
        while True:
            k = ask("  Ключ (Enter - конец): ", default="")
            if k == EXIT or not k:
                break
            val = ask("  Значение: ")
            if val == EXIT:
                break
            cfg[new_key][k] = val
    elif t == "4":
        v = ask("  true/false: ", choices=["true","false"])
        if v == EXIT:
            return
        cfg[new_key] = v
    print(f"[+] Добавлено поле: {new_key}")
    input("Enter...")

def uje_editor(cfg, path):
    while True:
        clr()
        hdr("УНИВЕРСАЛЬНЫЙ РЕДАКТОР JSON")
        print(f"  Файл: {path.name}")
        ln()
        keys = ordered_keys_hint(cfg)
        for i, k in enumerate(keys, 1):
            v = cfg[k]
            if isinstance(v, list):
                disp = f"[{len(v)} элем.]"
            elif isinstance(v, dict):
                disp = f"{{...}} ({len(v)})"
            else:
                disp = str(v)
                if len(disp) > 45:
                    disp = disp[:42] + "..."
            print(f"  {i:3}. {k:24} = {disp}")
        ln()
        print("  a - Добавить новое поле")
        print("  s - Сохранить")
        print("  b - Создать бэкап")
        print("  v - Показать JSON полностью")
        print("  o - Сохранить как")
        print("  q - Выход")
        ch = ask("  Выбор: ")
        if ch == EXIT:
            return cfg
        if ch == 'a':
            uje_add_field(cfg)
            continue
        if ch == 's':
            if uje_save_json(path, cfg):
                print(f"[+] Сохранено: {path}")
                input("Enter...")
            continue
        if ch == 'b':
            ts = time.strftime("%Y%m%d_%H%M%S")
            bpath = BACKUP_DIR / f"{path.stem}_{ts}.json"
            if uje_save_json(bpath, cfg):
                print(f"[+] Бэкап: {bpath}")
            input("Enter...")
            continue
        if ch == 'v':
            clr()
            print(json.dumps(cfg, ensure_ascii=False, indent=2))
            input("\nEnter...")
            continue
        if ch == 'o':
            nm = ask("  Имя файла: ")
            if nm == EXIT or not nm:
                continue
            if not nm.endswith('.json'):
                nm += '.json'
            opath = OUTPUT_DIR / nm
            if uje_save_json(opath, cfg):
                print(f"[+] Экспортировано: {opath}")
            input("Enter...")
            continue
        if ch == 'q':
            return cfg
        try:
            idx = int(ch)
        except Exception:
            continue
        if 1 <= idx <= len(keys):
            key = keys[idx-1]
            val = cfg.get(key)
            if isinstance(val, list):
                uje_edit_list(cfg, key)
            elif isinstance(val, dict):
                uje_edit_dict(cfg, key)
            else:
                uje_edit_string(cfg, key)
                input("Enter...")

def uje_menu():
    hdr("УНИВЕРСАЛЬНЫЙ РЕДАКТОР JSON")
    print("  1 - Открыть из Input")
    print("  2 - Открыть из Output")
    print("  3 - Ввести путь вручную")
    print("  4 - Создать новый JSON")
    print("  q - Отмена")
    ch = ask("Выбор: ", choices=["1","2","3","4"])
    if ch == EXIT:
        return
    if ch == "4":
        name = ask("  Имя файла (без .json): ")
        if name == EXIT or not name:
            return
        if not name.endswith('.json'):
            name += '.json'
        path = OUTPUT_DIR / name
        template = {"Name": name.replace('.json','')}
        if uje_save_json(path, template):
            print(f"[+] Создан: {path}")
            uje_editor(template, path)
        return
    path = None
    if ch == "1":
        files = sorted([p for p in INPUT_DIR.glob("*.json") if p.is_file()])
        if not files:
            print("[!] В Input нет JSON.")
            input("Enter...")
            return
        for i, f in enumerate(files, 1):
            print(f"  {i}. {f.name} ({fmt_size(f.stat().st_size)})")
        idx = ask_int("Номер файла: ", mn=1, mx=len(files))
        if idx == EXIT or idx is None:
            return
        path = files[idx-1]
    elif ch == "2":
        files = sorted([p for p in OUTPUT_DIR.glob("*.json") if p.is_file()])
        if not files:
            print("[!] В Output нет JSON.")
            input("Enter...")
            return
        for i, f in enumerate(files, 1):
            print(f"  {i}. {f.name} ({fmt_size(f.stat().st_size)})")
        idx = ask_int("Номер файла: ", mn=1, mx=len(files))
        if idx == EXIT or idx is None:
            return
        path = files[idx-1]
    elif ch == "3":
        p = ask("Путь к файлу: ")
        if p == EXIT or not p:
            return
        path = Path(p)
    if path:
        cfg = uje_load_json(path)
        if cfg is None:
            input("Enter...")
            return
        if not isinstance(cfg, dict):
            print("[!] Корень JSON не является объектом.")
            input("Enter...")
            return
        uje_editor(cfg, path)

# Главное меню SubManager
def main():
    ensure_dirs()
    cfg = cfg_load()
    cfg_save(cfg)
    clr()
    hdr("SubManager")
    print(f"  Input:   {INPUT_DIR}")
    print(f"  Output:  {OUTPUT_DIR}")
    print(f"  Backups: {BACKUP_DIR}")
    print("=" * W)
    servers = autoload_servers()
    if servers:
        print(f"[+] Автозагрузка прошлой сессии: {len(servers)} серверов")
        time.sleep(1)
    json_template = None
    while True:
        clr()
        hdr("ГЛАВНОЕ МЕНЮ")
        print(f"  Серверов: {len(servers)}")
        if json_template:
            print(f"  Загружен JSON шаблон")
        ln()
        print("  1 - Загрузить исходники")
        print("  2 - Редактировать серверы")
        print("  3 - Показать список серверов")
        print("  4 - Статистика")
        print("  5 - Сгенерировать JSON Xray")
        print("  6 - Настройки генерации")
        print("  7 - Роутинг для клиентов")
        print("  8 - Экспорт выбранных серверов")
        print("  9 - Сохранить ссылки (txt + base64)")
        print(" 10 - Сохранить Clash YAML")
        print(" 11 - Сделать бэкап")
        print(" 12 - Нормализовать существующий конфиг")
        print(" 13 - Нормализовать бэкап серверов")
        print(" 14 - Очистить автосохранение")
        print(" 15 - Универсальный редактор JSON")
        print("  q - Выход")
        ch = ask("Выбор: ", choices=[str(i) for i in range(1, 16)])
        if ch == EXIT:
            if servers:
                a = ask("Сделать бэкап перед выходом? (y/n) [n]: ", default="n")
                if a != EXIT and a.lower() == 'y':
                    backup_servers(servers)
                autosave_servers(servers)
                print(f"[+] Автосохранение: {AUTOSAVE_FILE}")
            print("[+] Выход.")
            break
        if ch == "1":
            raw = load_source()
            if raw:
                new_servers, json_data = parse_input(raw)
                if new_servers:
                    servers.extend(new_servers)
                    if json_data:
                        json_template = json_data
                    print(f"[+] Загружено: {len(new_servers)}. Всего: {len(servers)}")
                else:
                    print("[!] Не удалось распарсить данные.")
            input("\nEnter...")
        elif ch == "2":
            if not servers:
                print("[!] Список пуст.")
                input("Enter...")
                continue
            servers = edit_servers(servers)
        elif ch == "3":
            clr()
            hdr("СПИСОК СЕРВЕРОВ")
            show_servers_list(servers, show_params=True)
            print(f"\n  Всего: {len(servers)}")
            input("\nEnter...")
        elif ch == "4":
            stats(servers)
        elif ch == "5":
            if not servers:
                print("[!] Нет серверов.")
                input("Enter...")
                continue
            nm, rem = ask_json_name_and_remarks(cfg)
            if nm is None:
                input("Enter...")
                continue
            cfg_json = gen_config(servers, cfg)
            save_json(cfg_json, cfg, nm, rem)
            input("\nEnter...")
        elif ch == "6":
            cfg = config_menu(servers, cfg)
        elif ch == "7":
            cfg = routing_menu(cfg)
        elif ch == "8":
            if not servers:
                print("[!] Нет серверов.")
                input("Enter...")
                continue
            export_menu(servers, cfg)
        elif ch == "9":
            if not servers:
                print("[!] Нет серверов.")
                input("Enter...")
                continue
            save_base64(servers)
            input("\nEnter...")
        elif ch == "10":
            if not servers:
                print("[!] Нет серверов.")
                input("Enter...")
                continue
            save_yaml_clash(servers)
            input("\nEnter...")
        elif ch == "11":
            if not servers:
                print("[!] Нет серверов.")
                input("Enter...")
                continue
            backup_servers(servers)
            input("\nEnter...")
        elif ch == "12":
            normalize_existing_config_menu()
        elif ch == "13":
            normalize_existing_servers_menu()
        elif ch == "14":
            if AUTOSAVE_FILE.exists():
                a = ask("Удалить автосохранение? (y/n): ", default="n")
                if a.lower() == 'y':
                    AUTOSAVE_FILE.unlink()
                    print("[+] Удалено.")
            else:
                print("[!] Автосохранения нет.")
            input("Enter...")
        elif ch == "15":
            uje_menu()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n[!] Прервано.")
    except Exception as e:
        print(f"\n[!] Ошибка: {e}")
        import traceback
        traceback.print_exc()
SUBMGR_END

echo "[+] Все скрипты созданы."
sleep 1

# ============================================================
# Главное меню
# ============================================================
while true; do
    clear
    echo "===================================================="
    echo "        Shadowrocket Toolkit (iSH)"
    echo "===================================================="
    echo "  1 - AdBlock           Формирование блокировщика"
    echo "  2 - SQLiteTXT         Просмотр SQLite в тексте"
    echo "  3 - SpyLog            Анализ журналов Shadowrocket"
    echo "  4 - SubManager        Подписки и JSON Xray"
    echo "  5 - GetDefaultConfig  Скачать дефолтную конфигурацию"
    echo "  q - Выход"
    echo "===================================================="
    printf "Ваш выбор: "
    read CH
    case "$CH" in
        1)
            cd $BASE/AdBlock
            python3 $BASE/AdBlock.py
            cd $HOME
            ;;
        2)
            python3 $BASE/SQLiteTXT.py
            ;;
        3)
            python3 $BASE/SpyLog.py
            ;;
        4)
            python3 $BASE/SubManager.py
            ;;
        5)
            echo "[*] Скачивание дефолтной конфигурации..."
            mkdir -p $BASE/Configurations
            OUT=$BASE/Configurations/Default_configuration_by_Krest-Neva.module
            curl -sL "https://raw.githubusercontent.com/Krest-Neva/Shadowrocket/refs/heads/main/Configurations/Default_configuration_by_Krest-Neva.module" -o "$OUT"
            if [ -s "$OUT" ]; then
                echo "[+] Сохранено: $OUT"
                echo ""
                echo "---- Содержимое ----"
                cat "$OUT"
                echo ""
                echo "---- Конец ----"
            else
                echo "[!] Не удалось скачать."
            fi
            ;;
        q|Q)
            echo "Выход."
            exit 0
            ;;
        *)
            echo "Неверный выбор."
            sleep 1
            continue
            ;;
    esac
    echo ""
    printf "Нажмите Enter для возврата в меню..."
    read DUMMY
done
