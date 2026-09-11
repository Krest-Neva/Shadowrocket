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

echo "[*] Создание рабочей папки /root/RedirectGen..."
mkdir -p /root/RedirectGen

echo "[*] Очистка старых файлов..."
rm -f /root/RedirectGen/URL_REWRITE.list
rm -f /root/RedirectGen/MITM.list
rm -f /root/RedirectGen/Shadowrocket.conf
rm -f /root/RedirectGen/LogsRedirectScript
rm -f /root/RedirectGen/aria_tmp_dl
rm -f /root/RedirectGen/REJECT_RULES_STD.list

cat << 'ADBLOCK_EOF' > "/root/RedirectGen/update_reject.sh"
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
apk add python3 curl wget aria2 openssl ca-certificates bind-tools bash py3-pip git

echo "[*] Принудительное удаление старых файлов перед сборкой..."
rm -f REJECT_RULES*.list
rm -f "LogsAdBlockScript"

cat << 'EOF' > "REJECT_RULES.py"
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

while True:
    print("\n" + "="*45)
    print("Настройка списков OISD")
    print("1 - Обычные (Big/Full)")
    print("2 - Короткие (Small)")
    print("3 - Скачать все (Обычные + Короткие)")
    
    raw_oisd = input("Ваш выбор (1/2/3) [по умолчанию 3]: ").strip()
    oisd_choice = raw_oisd if raw_oisd in ('1', '2', '3') else '3'
    
    mapping = {
        '1': 'Обычные (Big/Full)', 
        '2': 'Короткие (Small)', 
        '3': 'Скачать все (Обычные + Короткие)'
    }
    choice_str = mapping[oisd_choice]
    
    print(f" -> Выбрано: {choice_str}")
    confirm = input(f"Подтвердить выбор? (y/n) [по умолчанию y]: ").strip().lower()
    
    if confirm in ('y', 'yes'):
        break
    else:
        print("Повторите ввод...")

oisd_main_url = "https://dl.oisd.nl/oisd_big_surge.list"
oisd_nsfw_url = "https://dl.oisd.nl/oisd_nsfw_surge.list"
oisd_small_url = "https://dl.oisd.nl/oisd_small_surge.list"
oisd_nsfw_small_url = "https://dl.oisd.nl/oisd_nsfw_small_surge.list"
print("="*45 + "\n")

SCRIPT_START_TIME = time.time()

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

exclude_keywords = [
    "ads", "analytics", "tracker", "tracking", "tracer", "metrics", "metrica", "metrika", "telemetry", "pixel", "beacon", "adserver", "doubleclick", "adjust", "appsflyer", "app-measurement", "log-upload", "crash-report", "messenger.yandex", "vetmanager"
]

exclude_pattern = re.compile('|'.join(re.escape(kw) for kw in exclude_keywords))

INVALID_CHARS = set('?|=*(),&:[]/\\%#_')

protected_suffixes = {
   "apple-pki.com", "icloud.com", "icloud-content.com", "mzstatic.com", "push.apple.com", "appleid.apple.com",
    "simplex.im", "simplexonflux.com", "telegram.org", "t.me", "telegram.me", "telegra.ph", "tg.dev", "cdn.telegram-cdn.org",
    "whatsapp.com", "whatsapp.net", "wa.me", "youtube.com", "youtu.be", "ytimg.com", "googlevideo.com", "youtube.googleapis.com", "ls-apple.com.akadns.net", "ess-apple.com.akadns.net"
}

protected_domains = {
    "raw.githubusercontent.com", "cdn-apple.com", "apple-dns.net", "ls.apple.com", "facetime.apple.com", "stun.apple.com", "apple.com", "aaplimg.com", "github.com", "githubusercontent.com", "githubassets.com", "google.com", "gstatic.com", "ggpht.com", "firebase.google.com", "googleapis.com", "firebaseio.com", "openai.com", "chatgpt.com", "oaistatic.com", "oaiusercontent.com", "microsoft.com", "windows.com", "windowsupdate.com", "msftconnecttest.com", "msftncsi.com", "azure.com", "azureedge.net", "azurefd.net", "amazon.com", "amazonaws.com", "aws.amazon.com", "cloudfront.net", "cloudflare.com", "fastly.net", "cdn.jsdelivr.net", "unpkg.com", "akamaiedge.net", "akamaized.net", "akamai.net", "auth0.com", "okta.com", "login.microsoftonline.com", "accounts.google.com", "hcaptcha.com", "challenges.cloudflare.com", "recaptcha.net", "facebook.com", "fb.com", "fbcdn.net", "graph.instagram.com", "graph.facebook.com", "instagram.com", "cdninstagram.com", "discord.com", "discordapp.com", "duckduckgo.com", "ddg.co", "giphy.com", "habr.com", "yandex.ru", "yandex.com", "yandex.by", "yandex.kz", "mail.yandex.ru", "passport.yandex.ru", "api.yandex.ru", "mail.ru", "e.mail.ru", "vk.com", "api.vk.com", "ozon.ru", "wildberries.ru", "avito.ru", "avito.st", "hh.ru", "sberbank.ru", "online.sberbank.ru", "alfabank.ru", "alfa.ru", "tbank.ru", "tinkoff.ru", "vtb.ru", "finam.ru", "63.ru", "aif.ru", "amic.ru", "angliya.com", "ap22.ru", "asiaplustj.info", "avesta.tj", "azerisport.com", "belta.by", "championat.com", "chita.ru", "citilink.ru", "civil.ge", "click-or-die.ru", "dni.ru", "e1.ru", "echo.az", "echo.msk.ru", "fedpress.ru", "f1news.ru", "fontanka.ru", "gazeta.ru", "gazetanovgorod.ru", "golosarmenii.am", "government.ru", "gundogar-news.com", "hronikatm.com", "infoabad.com", "inosmi.ru", "interfax.ru", "itogi.ru", "izvestia.ru", "kp.ru", "kremlin.ru", "lenta.ru", "matchtv.ru", "meduza.io", "mn.ru", "ng.ru", "novayagazeta.ru", "newsvl.ru", "og.ru", "ok.ru", "politikus.info", "ppt.ru", "pressball.by", "progorodsamara.ru", "radiomayak.ru", "rbc.ru", "rg.ru", "ria.ru", "rskrf.ru", "rutube.ru", "sovsport.ru", "sport-express.ru", "sport24.ru", "sportbox.ru", "sports.ru", "tass.ru", "trud.ru", "utro.ru", "ytro.ru", "zr.ru", "one.one.one.one", "dns.google", "quad9.net", "npmjs.org", "pypi.org", "gitlab.com", "bitbucket.org", "android.com", "yastatic.net", "dft.ru", "afisha.ru", "gosuslugi.ru", "yandex.ru", "aviasales.ru", "kinopoisk.ru", 
}

manual_protected_domains = protected_domains.copy()
manual_protected_suffixes = protected_suffixes.copy()

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

def full_network_diagnostics():
    print("    [diag] Выполняется полная диагностика сети (ошибка скачивания)...")
    try:
        print("      - Ping 8.8.8.8:")
        subprocess.run(["ping", "-c", "3", "8.8.8.8"])
        print("      - Ping google.com:")
        subprocess.run(["ping", "-c", "3", "google.com"])
        print("      - Текущий resolv.conf:")
        subprocess.run(["cat", "/etc/resolv.conf"])
    except Exception as e:
        print(f"      [!] Ошибка при диагностике: {e}")

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

def validate_ip(ip_str):
    try:
        net = ipaddress.ip_network(ip_str, strict=False)
        addr = str(net.network_address)
        if addr.startswith(('0.', '127.', '255.')):
            return None
        return str(net)
    except ValueError:
        return None

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
            ef.write("PROTECTED SUFFIXES (whitelisted, suffix match)\n")
            for s in sorted(protected_suffixes):
                ef.write(f"{s}\n")
            ef.write("\nPROTECTED DOMAINS (whitelisted, exact match)\n")
            for d in sorted(protected_domains):
                ef.write(f"{d}\n")

            ef.write("\n" + "="*60 + "\n")
            ef.write("EXCLUDED BY KEYWORDS\n")
            excluded = [(r,s,o) for r,s,o in errors if r == "excluded_keyword"]
            for reason, src, orig in excluded:
                ef.write(f"{src}\t{orig}\n")

            ef.write("\nJUNK / INVALID LINES (или пропущенные пути)\n")
            junk = [(r,s,o) for r,s,o in errors if r.startswith("junk") or r == "skipped_path_rule"]
            for reason, src, orig in junk:
                ef.write(f"{reason}\t{src}\t{orig}\n")

            ef.write("\nPROTECTED ENTRIES (skipped during parsing)\n")
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
        print("[*] Оптимизация расширенного списка (PLUS)...")
        optimized_domains_plus = optimize_domain_set(all_domains | oisd_domains | nsfw_domains, "opt plus")
        
        print("[*] Формирование и запись файлов STD и PLUS...")
        final_list_len = write_chunks("REJECT_RULES", optimized_domains, all_ips | oisd_ips, "write std")
        final_list_plus_len = write_chunks("REJECT_RULES_PLUS", optimized_domains_plus, all_ips | oisd_ips | nsfw_ips, "write plus", is_plus=True)
        total_rules += final_list_len + final_list_plus_len

    if oisd_choice in ('2', '3'):
        print("[*] Оптимизация малого списка (SMALL)...")
        optimized_domains_sm = optimize_domain_set(all_domains | oisd_small_domains, "opt sm")
        print("[*] Оптимизация малого расширенного списка (PLUS SMALL)...")
        optimized_domains_plus_sm = optimize_domain_set(all_domains | oisd_small_domains | nsfw_small_domains, "opt plus sm")
        
        print("[*] Формирование и запись файлов SMALL и PLUS SMALL...")
        final_list_sm_len = write_chunks("REJECT_RULES_SMALL", optimized_domains_sm, all_ips | oisd_small_ips, "write sm")
        final_list_plus_sm_len = write_chunks("REJECT_RULES_PLUS_SMALL", optimized_domains_plus_sm, all_ips | oisd_small_ips | nsfw_small_ips, "write plus sm", is_plus=True)
        total_rules += final_list_sm_len + final_list_plus_sm_len

    return total_rules

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
    print("  1 - Да (попробовать стандартные ссылки)")
    print("  2 - Нет (пропустить этот список)")
    print("  3 - Вручную (я введу новую рабочую ссылку)")
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
            url_to_try = input("Введите полную ссылку (https://...): ").strip()
        else:
            url_to_try = white_urls[target] if is_white else urls[target]

        lines, method = download_data(target, url_to_try)

        if not lines:
            print("  [!] Загрузка снова не удалась или получена страница с ошибкой (HTML).")
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

    for idx, raw_line in enumerate(lines, start=1):
        if idx % 100 == 0 or idx == total_lines:
            print_progress("  [b-parse]", idx, total_lines, start_time=start_parse)

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
                        is_protected_ip = False if is_any_oisd else (pure_ip in protected_ips)
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
                        protected, reason = (False, None) if is_any_oisd else is_protected_full(val)
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
            is_protected_ip = False if is_any_oisd else (pure_ip in protected_ips)
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
            protected, reason = (False, None) if is_any_oisd else is_protected_full(clean)
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

print("\n=== ЭТАП 5: ОЧИСТКА ПОДДОМЕНОВ И ФОРМИРОВАНИЕ RULE-SET ===")
build_and_write()

TOTAL_TIME = round(time.time() - SCRIPT_START_TIME, 2)

print("\n" + "="*45)
print(f"ГОТОВО! Файлы успешно разделены и сохранены.")
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
EOF

echo "[*] Настройка DNS перед запуском парсера..."
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

echo "[*] Запуск скрипта генерации правил..."
python3 "REJECT_RULES.py"
ADBLOCK_EOF

chmod +x "/root/RedirectGen/update_reject.sh"

cat << 'GEN_EOF' > "/root/RedirectGen/GEN_REDIRECT.py"
import sys
import os
import re
import time
import shutil
import tempfile
import subprocess
import urllib.request
from collections import defaultdict

WORK_DIR = os.path.dirname(os.path.abspath(__file__))
ADBLOCK_SCRIPT = os.path.join(WORK_DIR, "update_reject.sh")
ADBLOCK_LOCAL_LIST = os.path.join(WORK_DIR, "REJECT_RULES.list")

SOURCE_URL = "https://dl.oisd.nl/oisd_nsfw_surge.list"
REDIRECT_URL = "https://raw.githubusercontent.com/Krest-Neva/Shadowrocket/refs/heads/main/Other/Redirect"
REJECT_STD_GITHUB = "https://raw.githubusercontent.com/Krest-Neva/Shadowrocket/refs/heads/main/REJECT_RULES/REJECT_RULES_STD.list"

OUT_URL = os.path.join(WORK_DIR, "URL_REWRITE.list")
OUT_MITM = os.path.join(WORK_DIR, "MITM.list")
OUT_COMBINED = os.path.join(WORK_DIR, "Shadowrocket.conf")
OUT_REJECT_STD = os.path.join(WORK_DIR, "REJECT_RULES_STD.list")
LOG_FILE = os.path.join(WORK_DIR, "LogsRedirectScript")

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
    "tele2_spb": "https://raw.githubusercontent.com/chebur-net/russia-mobile-whitelist/refs/heads/main/spb-tele2/domains.txt"
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

def ask_reject_std_mode():
    while True:
        print("\n" + "=" * 45)
        print("Источник списка REJECT_RULES_STD")
        print("1 - Скачать готовый с GitHub")
        print("2 - Собрать заново (запуск полного обновления)")
        raw = input("Ваш выбор (1/2) [по умолчанию 1]: ").strip()
        choice = raw if raw in ('1', '2') else '1'
        mapping = {
            '1': 'Скачать готовый с GitHub',
            '2': 'Собрать заново (займёт много времени)'
        }
        print(" -> Выбрано: " + mapping[choice])
        confirm = input("Подтвердить выбор? (y/n) [по умолчанию y]: ").strip().lower()
        if confirm in ('y', 'yes', ''):
            return choice
        print("Повторите ввод...")

def run_adblock_build():
    print("[*] Запуск полной сборки REJECT_RULES_STD...")
    print("[*] Скрипт update_reject.sh будет запущен с параметрами: OISD = Big/Full")
    if not os.path.exists(ADBLOCK_SCRIPT):
        print("[!] Не найден " + ADBLOCK_SCRIPT)
        return None
    try:
        proc = subprocess.run(
            ['sh', ADBLOCK_SCRIPT],
            cwd=WORK_DIR,
            input="1\ny\n",
            text=True,
            timeout=7200
        )
        if proc.returncode != 0:
            print("[!] Скрипт завершился с кодом " + str(proc.returncode))
    except subprocess.TimeoutExpired:
        print("[!] Скрипт не завершился за 2 часа")
        return None
    except Exception as e:
        print("[!] Ошибка запуска: " + str(e))
        return None

    if not os.path.exists(ADBLOCK_LOCAL_LIST):
        print("[!] Не найден результат: " + ADBLOCK_LOCAL_LIST)
        return None

    print("[+] Локальная сборка завершена: " + ADBLOCK_LOCAL_LIST)
    try:
        shutil.copyfile(ADBLOCK_LOCAL_LIST, OUT_REJECT_STD)
        print("[+] Сохранено как: " + OUT_REJECT_STD)
    except Exception as e:
        print("[!] Не удалось скопировать: " + str(e))

    with open(ADBLOCK_LOCAL_LIST, 'r', encoding='utf-8', errors='ignore') as f:
        return f.read().splitlines()

def download_reject_std():
    print("[*] Скачивание REJECT_RULES_STD с GitHub...")
    lines = download(REJECT_STD_GITHUB, "rej_std")
    if not lines:
        return None
    try:
        with open(OUT_REJECT_STD, 'w', encoding='utf-8') as f:
            for l in lines:
                f.write(l + "\n")
        print("[+] Сохранено как: " + OUT_REJECT_STD)
    except Exception as e:
        print("[!] Не удалось сохранить: " + str(e))
    return lines

def load_reject_std(mode):
    if mode == '2':
        lines = run_adblock_build()
        if lines:
            return lines
        print("[!] Локальная сборка не удалась, откат к GitHub...")
    return download_reject_std() or []

def download_all_whitelists():
    print("\n[*] ФАЗА 1/3: Загрузка белых списков...")
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
    print("\n[*] ФАЗА 1/3: Загрузка основного списка...")
    lines = download(SOURCE_URL, "oisd_nsfw")
    return lines

def parse_whitelists(raw, reject_std_lines):
    print("\n[*] ФАЗА 2/3: Парсинг белых списков...")
    whitelist_suffixes = set(PROTECTED_SUFFIXES)
    whitelist_exact = set(PROTECTED_DOMAINS)

    all_whitelists = dict(raw)
    if reject_std_lines:
        all_whitelists["rej_std"] = reject_std_lines

    for name, lines in all_whitelists.items():
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
    sorted_list = sorted(s)
    total = len(sorted_list)
    for i, d in enumerate(sorted_list, 1):
        if i % STEP == 0 or i == total:
            progress_bar("  [redundant]", i, total)
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
    tld_items = list(groups.items())
    total = len(tld_items)
    for i, (tld, doms) in enumerate(tld_items, 1):
        if i % 50 == 0 or i == total:
            progress_bar("  [regex-build]", i, total)
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
    print("[*] Рабочая папка: " + WORK_DIR)
    print("[*] Настройка DNS...")
    setup_dns()
    print("[*] Проверка интернета...")
    if not check_internet():
        print("[!] Нет соединения с интернетом")
        sys.exit(1)
    print("[+] Интернет доступен.")

    mode = ask_reject_std_mode()

    reject_std_lines = load_reject_std(mode)
    if not reject_std_lines:
        print("[!] REJECT_RULES_STD пуст — продолжаем без него.")

    white_raw, failed_white = download_all_whitelists()
    if failed_white:
        print("[!] Пропущены белые списки: " + ", ".join(failed_white))
    if not white_raw and not reject_std_lines:
        print("[!] Ни один белый список не скачался. Продолжаем со встроенным защищённым списком.")

    black_lines = download_blacklist()
    if not black_lines:
        print("[!] Не удалось скачать основной список")
        sys.exit(1)

    print("\n[*] Все списки загружены. Начинаем обработку.")
    print("=" * 60)

    whitelist_suffixes, whitelist_exact = parse_whitelists(white_raw, reject_std_lines)
    white_count = len(whitelist_suffixes) + len(whitelist_exact)
    print("[*] Всего в белых списках: " + str(white_count))

    print("[*] Парсинг основного списка...")
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
    print("[*] Удаление избыточных доменов...")
    domains = remove_redundant(domains)
    print("[*] После удаления избыточных: " + str(len(domains)))

    domains = sorted(domains)
    print("\n[*] ФАЗА 3/3: Генерация регулярки и MITM...")
    regex = build_regex(domains)
    if regex is None:
        print("[!] ОШИБКА: регулярка вырождается в голый TLD.")
        write_log(total, valid_count, len(domains), len(domains), 0, skipped, white_count, excluded, "FAILED: TLD-only regex")
        sys.exit(1)

    pattern = r'^https?:\/\/(?:[^\/.]+\.)*' + regex + r'(?::\d+)?(?:\/.*)?$'
    print("[*] Длина regex: " + str(len(pattern)))

    with open(OUT_URL, 'w', encoding='utf-8') as f:
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

    with open(OUT_COMBINED, 'w', encoding='utf-8') as f:
        f.write("[URL Rewrite]\n")
        f.write(pattern + " " + REDIRECT_URL + " 302\n")
        f.write("\n[MITM]\n")
        f.write("hostname = %APPEND% " + ", ".join(mitm_sorted) + "\n")
    print("[+] Записано: " + OUT_COMBINED)

    write_log(total, valid_count, len(domains), len(domains), len(pattern), skipped, white_count, excluded, "OK")
    print("[+] Лог: " + LOG_FILE)

if __name__ == '__main__':
    main()
GEN_EOF

cd /root/RedirectGen
python3 GEN_REDIRECT.py

echo ""
echo "[*] Готово. Все файлы в /root/RedirectGen/"
ls -la /root/RedirectGen/
