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

echo "[*] Создание рабочих папок..."
mkdir -p ~/SubManager/Input
mkdir -p ~/SubManager/Output
mkdir -p ~/SubManager/Backups
mkdir -p ~/SubManager/Routing

cat << 'PYEOF' > ~/SubManager/SubManager.py
#!/usr/bin/env python3
import os, sys, re, json, base64, urllib.request, urllib.error, ssl, subprocess, shutil, time, ipaddress, random
from urllib.parse import urlparse, parse_qs, urlencode, unquote, quote
from pathlib import Path

HOME = Path.home()
BASE_DIR = HOME / "SubManager"
INPUT_DIR = BASE_DIR / "Input"
OUTPUT_DIR = BASE_DIR / "Output"
BACKUP_DIR = BASE_DIR / "Backups"
ROUTING_DIR = BASE_DIR / "Routing"
CONFIG_FILE = BASE_DIR / "config.json"
UA = "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1"

DNS_SERVERS = ["8.8.8.8", "8.8.4.4", "1.1.1.1", "94.140.14.14", "94.140.15.15"]
W = 50


def clr():
    os.system('clear')


def hdr(title):
    print("=" * W)
    print(f" {title}")
    print("=" * W)


def line():
    print("-" * W)


def cfg_default():
    return {
        "dns_servers": DNS_SERVERS,
        "dns_query_strategy": "UseIP",
        "observatory_url": "https://www.google.com/generate_204",
        "observatory_interval": "1m",
        "observatory_timeout": "3s",
        "observatory_probing_url": "https://cp.cloudflare.com/generate_204",
        "balancer_strategy": "leastLoad",
        "balancer_expected": 1,
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
        "routing": {
            "direct_domains": ["geosite:private", "geosite:category-ru"],
            "block_domains": ["geosite:category-ads-all"],
            "direct_ips": [],
            "block_ips": [],
            "block_protocols": ["bittorrent"],
            "direct_ports": [],
            "block_ports": [],
            "block_networks": [],
            "rules": []
        },
        "json_name": "xray_config"
    }


def cfg_load():
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                saved = json.load(f)
            base = cfg_default()
            for k, v in saved.items():
                if isinstance(v, dict) and k in base:
                    base[k].update(v)
                else:
                    base[k] = v
            return base
        except Exception:
            pass
    return cfg_default()


def cfg_save(cfg):
    CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)


def ensure_dirs():
    for d in [INPUT_DIR, OUTPUT_DIR, BACKUP_DIR, ROUTING_DIR]:
        d.mkdir(parents=True, exist_ok=True)


def ask(prompt, default=None, choices=None):
    while True:
        try:
            v = input(prompt).strip()
        except EOFError:
            return default
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
            print("[!] Введите число.")
        except EOFError:
            return default


def ask_multi(prompt, mn, mx):
    while True:
        try:
            v = input(prompt).strip()
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
            print("[!] Формат: 1,3-5 или all")


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


def decode_base64_if_needed(raw):
    cl = raw.strip().replace('\n', '').replace('\r', '').replace(' ', '')
    if len(cl) > 20 and re.fullmatch(r'[A-Za-z0-9+/=_\-]+', cl):
        try:
            pad = 4 - len(cl) % 4
            padded = cl + ('=' * pad if pad != 4 else '')
            decoded = base64.b64decode(padded).decode('utf-8', errors='ignore')
            if '://' in decoded and ('vless://' in decoded or 'vmess://' in decoded or 'ss://' in decoded or 'trojan://' in decoded or 'hysteria2://' in decoded or 'hy2://' in decoded):
                return decoded, True
        except Exception:
            pass
    return raw, False


def load_source():
    hdr("ЗАГРУЗКА ИСХОДНИКОВ")
    print("  1 - Локальный файл")
    print("  2 - По ссылке (URL)")
    print("  3 - Несколько ссылок подряд")
    ch = ask("Выбор [1]: ", default="1", choices=["1", "2", "3"])
    raw = ""
    if ch == "1":
        files = sorted([p for p in INPUT_DIR.glob("*") if p.is_file()])
        if not files:
            print(f"[!] Папка {INPUT_DIR} пуста.")
            return None
        for i, f in enumerate(files, 1):
            print(f"  {i}. {f.name} ({fmt_size(f.stat().st_size)})")
        idx = ask_int("Номер файла: ", mn=1, mx=len(files))
        if idx is None:
            return None
        raw = files[idx - 1].read_text(encoding='utf-8', errors='ignore')
    elif ch == "2":
        url = ask("URL подписки: ")
        if not url:
            return None
        raw = dl_url(url)
        if not raw:
            print("[!] Не удалось загрузить.")
            return None
    else:
        print("[?] Вводите URL по одному. Пустая строка - завершить.")
        parts = []
        while True:
            u = ask("URL: ")
            if not u:
                break
            t = dl_url(u)
            if t:
                parts.append(t)
        if not parts:
            return None
        raw = "\n".join(parts)
    raw, was_b64 = decode_base64_if_needed(raw)
    if was_b64:
        print("[+] Base64 декодирован.")
    return raw


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
            r['host'] = p.hostname or ''
            r['port'] = str(p.port) if p.port else ''
            for k, v in parse_qs(p.query).items():
                r['params'][k] = v[0] if len(v) == 1 else v
        elif scheme in ('hysteria2', 'hy2'):
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
        else:
            return None
    except Exception:
        return None
    return r


def extract_links(text):
    out = []
    for ln in text.splitlines():
        ln = ln.strip()
        if not ln or ln.startswith('#'):
            continue
        if any(ln.startswith(s) for s in ['vless://', 'vmess://', 'trojan://', 'ss://', 'hysteria2://', 'hy2://']):
            out.append(ln)
    return out


def build_uri(info):
    scheme = info['scheme']
    host = info['host']
    port = info['port']
    params = info['params']
    name = info.get('name', '')
    if scheme in ('vless', 'vmess', 'trojan'):
        uri = f"{scheme}://{quote(info.get('id', ''))}@{host}:{port}"
    elif scheme in ('hysteria2', 'hy2'):
        uri = f"{scheme}://{quote(info.get('password', ''))}@{host}:{port}"
    elif scheme == 'ss':
        ui = f"{info.get('method', '')}:{info.get('password', '')}"
        b = base64.b64encode(ui.encode()).decode().rstrip('=')
        uri = f"ss://{b}@{host}:{port}"
    else:
        return info['raw']
    if params:
        uri += '?' + urlencode(params, doseq=True)
    if name:
        uri += '#' + quote(name)
    return uri


def show_servers_list(servers, show_params=False):
    if not servers:
        print("[!] Список пуст.")
        return
    for i, s in enumerate(servers, 1):
        name = s.get('name', '') or '(без имени)'
        t = s['params'].get('type', 'tcp')
        sec = s['params'].get('security', 'none')
        print(f"  {i:3}. [{s['scheme']:9}] {name[:28]:28} {s['host']}:{s['port']}")
        if show_params:
            print(f"        type={t} sec={sec} flow={s['params'].get('flow','')}")
            print(f"        path={s['params'].get('path','')} sni={s['params'].get('sni','')}")


def get_uri_info(uri):
    return parse_uri(uri)


def delete_by_keyword(servers):
    hdr("УДАЛЕНИЕ СЕРВЕРОВ")
    print("  1 - По ключевым словам в имени")
    print("  2 - По протоколу")
    print("  3 - По транспорту")
    print("  4 - По security")
    print("  5 - По домену")
    print("  6 - Инвертировать (оставить только совпадающие)")
    print("  7 - По номерам (1,3-5)")
    print("  0 - Отмена")
    ch = ask("Выбор: ", choices=["0", "1", "2", "3", "4", "5", "6", "7"])
    if ch == "0":
        return servers
    idxs = None
    if ch == "1":
        kw = ask("Ключевые слова (через запятую): ")
        kws = [k.strip().lower() for k in kw.split(',') if k.strip()]
        if not kws:
            return servers
        idxs = [i for i, s in enumerate(servers) if any(k in s.get('name', '').lower() for k in kws)]
    elif ch == "2":
        proto = ask("Протокол (vless/hysteria2/ss): ").lower()
        idxs = [i for i, s in enumerate(servers) if s['scheme'] == proto]
    elif ch == "3":
        t = ask("Транспорт (tcp/ws/grpc/xhttp): ").lower()
        idxs = [i for i, s in enumerate(servers) if s['params'].get('type', 'tcp') == t]
    elif ch == "4":
        sec = ask("Security (none/tls/reality): ").lower()
        idxs = [i for i, s in enumerate(servers) if s['params'].get('security', 'none') == sec]
    elif ch == "5":
        dom = ask("Домен (часть): ").lower()
        idxs = [i for i, s in enumerate(servers) if dom in s['host'].lower()]
    elif ch == "6":
        kw = ask("Ключевые слова для ИНВЕРТИРОВАНИЯ: ")
        kws = [k.strip().lower() for k in kw.split(',') if k.strip()]
        if not kws:
            return servers
        idxs = [i for i, s in enumerate(servers) if not any(k in s.get('name', '').lower() for k in kws)]
    elif ch == "7":
        show_servers_list(servers)
        sel = ask_multi("Номера для удаления: ", 1, len(servers))
        if not sel:
            return servers
        idxs = [i - 1 for i in sel]
    if not idxs:
        print("[!] Ничего не найдено.")
        return servers
    print(f"\n[+] Найдено: {len(idxs)}")
    for i in idxs[:15]:
        print(f"   - {servers[i].get('name', '')} ({servers[i]['scheme']}://{servers[i]['host']})")
    if len(idxs) > 15:
        print(f"   ... и ещё {len(idxs) - 15}")
    ans = ask("Удалить? (y/n) [n]: ", default="n")
    if ans.lower() == 'y':
        for i in sorted(idxs, reverse=True):
            servers.pop(i)
        print(f"[+] Удалено: {len(idxs)}")
    return servers


def dedupe_servers(servers):
    seen = set()
    out = []
    for s in servers:
        key = (s['scheme'], s['host'], s['port'], s.get('id', '') or s.get('password', '') or s.get('method', ''))
        if key not in seen:
            seen.add(key)
            out.append(s)
    removed = len(servers) - len(out)
    print(f"[+] Удалено дубликатов: {removed}" if removed else "[+] Дубликатов не найдено.")
    return out


def sort_servers(servers):
    hdr("СОРТИРОВКА")
    print("  1 - По имени (A-Z)")
    print("  2 - По имени (Z-A)")
    print("  3 - По протоколу")
    print("  4 - По хосту")
    print("  5 - Случайно")
    print("  0 - Отмена")
    ch = ask("Выбор: ", choices=["0", "1", "2", "3", "4", "5"])
    if ch == "1":
        servers.sort(key=lambda x: x.get('name', '').lower())
    elif ch == "2":
        servers.sort(key=lambda x: x.get('name', '').lower(), reverse=True)
    elif ch == "3":
        servers.sort(key=lambda x: x['scheme'])
    elif ch == "4":
        servers.sort(key=lambda x: x['host'].lower())
    elif ch == "5":
        random.shuffle(servers)
    else:
        return servers
    print("[+] Отсортировано.")
    return servers


PARAM_LIST = [
    ("scheme", "Протокол (vless/hysteria2/ss)"),
    ("type", "Транспорт (tcp/ws/grpc/xhttp)"),
    ("security", "Безопасность (none/tls/reality)"),
    ("flow", "Flow (xtls-rprx-vision)"),
    ("path", "Path"),
    ("host", "Host"),
    ("sni", "SNI"),
    ("pbk", "PublicKey (pbk)"),
    ("sid", "ShortId (sid)"),
    ("fp", "Fingerprint (fp)"),
    ("serviceName", "ServiceName (gRPC)"),
    ("mode", "Mode"),
    ("port", "Порт"),
    ("host_addr", "Адрес"),
    ("alpn", "ALPN"),
    ("obfs", "Obfs (hysteria2)"),
    ("obfs-password", "Obfs-password"),
    ("id", "UUID (id)"),
    ("password", "Пароль"),
    ("method", "Метод шифрования (ss)"),
    ("authority", "Authority (gRPC)"),
    ("concurrency", "concurrency (xhttp)"),
    ("spiderX", "SpiderX"),
    ("headerType", "Header Type (tcp)"),
    ("heartbeatPeriod", "Heartbeat Period (ws)"),
]

CHOICES_MAP = {
    "scheme": ["vless", "vmess", "trojan", "hysteria2", "hy2", "ss"],
    "type": ["tcp", "ws", "grpc", "xhttp", "splithttp", "httpupgrade", "h2", "kcp", "quic"],
    "security": ["none", "tls", "reality"],
    "flow": ["xtls-rprx-vision", ""],
    "fp": ["chrome", "firefox", "safari", "ios", "android", "edge", "360", "qq", "random", "randomized"],
    "mode": ["auto", "packet-up", "stream-up", "stream-one", "multi"],
    "headerType": ["none", "http"],
    "alpn": ["h3", "h2", "http/1.1", "h3,h2", "h2,http/1.1"],
    "spiderX": ["/", ""],
}

COMPAT = {
    "flow": lambda s: s['scheme'] == 'vless' and s['params'].get('type', 'tcp') == 'tcp' and s['params'].get('security') == 'reality',
    "pbk": lambda s: s['scheme'] == 'vless' and s['params'].get('security') == 'reality',
    "sid": lambda s: s['scheme'] == 'vless' and s['params'].get('security') == 'reality',
    "sni": lambda s: s['scheme'] in ('vless', 'hysteria2', 'hy2', 'trojan'),
    "fp": lambda s: s['scheme'] in ('vless', 'trojan'),
    "serviceName": lambda s: s['scheme'] == 'vless' and s['params'].get('type') == 'grpc',
    "authority": lambda s: s['scheme'] == 'vless' and s['params'].get('type') == 'grpc',
    "path": lambda s: s['scheme'] == 'vless' and s['params'].get('type') in ('ws', 'xhttp', 'splithttp', 'httpupgrade'),
    "host": lambda s: s['scheme'] == 'vless' and s['params'].get('type') in ('ws', 'xhttp', 'splithttp', 'httpupgrade'),
    "mode": lambda s: s['scheme'] == 'vless' and s['params'].get('type') in ('grpc', 'xhttp', 'splithttp'),
    "concurrency": lambda s: s['scheme'] == 'vless' and s['params'].get('type') in ('xhttp', 'splithttp'),
    "obfs": lambda s: s['scheme'] in ('hysteria2', 'hy2'),
    "obfs-password": lambda s: s['scheme'] in ('hysteria2', 'hy2'),
    "alpn": lambda s: s['params'].get('security') == 'tls' or s['scheme'] in ('hysteria2', 'hy2'),
    "method": lambda s: s['scheme'] == 'ss',
    "id": lambda s: s['scheme'] in ('vless', 'vmess', 'trojan'),
    "password": lambda s: s['scheme'] in ('hysteria2', 'hy2', 'ss', 'trojan'),
    "spiderX": lambda s: s['scheme'] == 'vless' and s['params'].get('security') == 'reality',
    "headerType": lambda s: s['scheme'] == 'vless' and s['params'].get('type') == 'tcp' and s['params'].get('security') != 'reality',
    "heartbeatPeriod": lambda s: s['scheme'] == 'vless' and s['params'].get('type') == 'ws',
}

SS_METHODS = [
    "aes-128-gcm", "aes-256-gcm", "chacha20-poly1305", "chacha20-ietf-poly1305",
    "xchacha20-poly1305", "xchacha20-ietf-poly1305", "2022-blake3-aes-128-gcm",
    "2022-blake3-aes-256-gcm", "2022-blake3-chacha20-poly1305", "none"
]


def edit_params_for_group(servers, indices):
    if not indices:
        return
    while True:
        clr()
        hdr("РЕДАКТИРОВАНИЕ ВЫБРАННОЙ ГРУППЫ")
        print(f"  Выбрано серверов: {len(indices)}")
        for i in indices[:20]:
            s = servers[i]
            print(f"    {i+1}. {s.get('name', '')[:30]} [{s['scheme']}] {s['host']}:{s['port']}")
        if len(indices) > 20:
            print(f"    ... и ещё {len(indices) - 20}")
        line()
        for idx, (k, desc) in enumerate(PARAM_LIST, 1):
            print(f"  {idx:2}. {desc}")
        print("   0. Назад")
        ch = ask("Выбор: ", choices=[str(i) for i in range(0, len(PARAM_LIST)+1)] + ["0"])
        if ch == "0":
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
        print(f"\n[?] '{pname}'")
        print(f"    Совместимых: {len(compatible)}, несовместимых: {len(indices) - len(compatible)}")
        if pkey == "scheme":
            print(f"    Варианты: {', '.join(CHOICES_MAP['scheme'])}")
        elif pkey in CHOICES_MAP:
            print(f"    Варианты: {', '.join(CHOICES_MAP[pkey])}")
        elif pkey == "method":
            print(f"    Варианты: {', '.join(SS_METHODS)}")
        nv = ask("Новое значение (пусто = удалить): ")
        for i in compatible:
            s = servers[i]
            if pkey == "scheme":
                s['scheme'] = nv
            elif pkey == "port":
                s['port'] = nv
            elif pkey == "host_addr":
                s['host'] = nv
            elif pkey == "id":
                s['id'] = nv
            elif pkey == "password":
                s['password'] = nv
            elif pkey == "method":
                s['method'] = nv
            else:
                if nv == "":
                    s['params'].pop(pkey, None)
                else:
                    s['params'][pkey] = nv
        print(f"[+] Обновлено: {len(compatible)}")


def edit_servers(servers):
    while True:
        clr()
        hdr("РЕДАКТИРОВАНИЕ СЕРВЕРОВ")
        show_servers_list(servers)
        print(f"\n  Всего: {len(servers)}")
        line()
        print("  1 - Имена (все / группа / по одному)")
        print("  2 - Параметры (выбрать группу)")
        print("  3 - Удалить сервер(ы)")
        print("  4 - Удалить по ключевым словам/фильтру")
        print("  5 - Добавить сервер вручную")
        print("  6 - Удалить дубликаты")
        print("  7 - Сортировка")
        print("  8 - Фильтр (показать подходящие)")
        print("  9 - Показать параметры сервера")
        print("  0 - Готово")
        ch = ask("Выбор: ", choices=[str(i) for i in range(0, 10)])
        if ch == "0":
            break
        if ch == "1":
            print("\n  1 - Все сразу (суффиксы -1, -2, ...)")
            print("  2 - Выбрать группу (номера)")
            print("  3 - По одному")
            print("  4 - Добавить префикс")
            sub = ask("Выбор [1]: ", default="1", choices=["1", "2", "3", "4"])
            if sub == "1":
                base = ask("Базовое имя: ")
                if base:
                    for i, s in enumerate(servers):
                        s['name'] = f"{base}-{i + 1}"
                    print("[+] Обновлено.")
            elif sub == "2":
                show_servers_list(servers)
                sel = ask_multi("Номера: ", 1, len(servers))
                if sel:
                    base = ask("Базовое имя: ")
                    if base:
                        for idx in sel:
                            servers[idx - 1]['name'] = f"{base}-{idx}"
                        print("[+] Обновлено.")
            elif sub == "3":
                sel = ask_multi("Номера: ", 1, len(servers))
                if sel:
                    for idx in sel:
                        if 1 <= idx <= len(servers):
                            cur = servers[idx - 1].get('name', '')
                            nn = ask(f"  {idx}. '{cur}' -> ")
                            if nn:
                                servers[idx - 1]['name'] = nn
                    print("[+] Обновлено.")
            else:
                pre = ask("Префикс: ")
                if pre:
                    for s in servers:
                        s['name'] = f"{pre}{s.get('name', '')}"
                    print("[+] Обновлено.")
        elif ch == "2":
            show_servers_list(servers)
            sel = ask_multi("Номера серверов для редактирования (1,3-5,all): ", 1, len(servers))
            if sel:
                edit_params_for_group(servers, [i - 1 for i in sel])
        elif ch == "3":
            show_servers_list(servers)
            sel = ask_multi("Номера для удаления: ", 1, len(servers))
            if sel:
                ans = ask(f"Удалить {len(sel)} сервер(ов)? (y/n) [n]: ", default="n")
                if ans.lower() == 'y':
                    for i in sorted(sel, reverse=True):
                        servers.pop(i - 1)
                    print(f"[+] Удалено: {len(sel)}")
        elif ch == "4":
            servers = delete_by_keyword(servers)
        elif ch == "5":
            uri = ask("Ссылка: ")
            if uri:
                p = parse_uri(uri)
                if p:
                    servers.append(p)
                    print("[+] Добавлен.")
                else:
                    print("[!] Не удалось распарсить.")
        elif ch == "6":
            servers = dedupe_servers(servers)
        elif ch == "7":
            servers = sort_servers(servers)
        elif ch == "8":
            show_servers_list(servers)
            kw = ask("Ключевое слово для поиска: ").lower()
            found = [(i+1, s) for i, s in enumerate(servers) if kw in s.get('name', '').lower() or kw in s['host'].lower() or kw in s['scheme']]
            if found:
                print(f"\n[+] Найдено: {len(found)}")
                for n, s in found:
                    print(f"   {n}. {s.get('name', '')} [{s['scheme']}://{s['host']}]")
            else:
                print("[!] Ничего не найдено.")
            input("Enter...")
        elif ch == "9":
            show_servers_list(servers)
            idx = ask_int("Номер: ", mn=1, mx=len(servers))
            if idx:
                s = servers[idx - 1]
                print(f"\n  URI: {build_uri(s)}")
                print(f"  Scheme: {s['scheme']}")
                print(f"  Host: {s['host']}")
                print(f"  Port: {s['port']}")
                print(f"  ID/Pass/Method: {s.get('id') or s.get('password') or s.get('method')}")
                print(f"  Params: {json.dumps(s['params'], ensure_ascii=False, indent=4)}")
                input("Enter...")
    return servers


def gen_outbound(s, tag, cfg):
    scheme = s['scheme']
    host = s['host']
    try:
        port = int(s['port']) if s['port'].isdigit() else 443
    except Exception:
        port = 443
    out = {}
    if scheme == 'vless':
        out = {
            "protocol": "vless",
            "settings": {"vnext": [{"address": host, "port": port, "users": [{"id": s.get('id', ''), "encryption": "none", "flow": s['params'].get('flow', '')}]}]},
            "streamSettings": {"network": s['params'].get('type', 'tcp'), "security": s['params'].get('security', 'none')},
            "tag": tag
        }
        sec = out["streamSettings"]["security"]
        if sec == 'reality':
            rs = {
                "serverName": s['params'].get('sni', ''),
                "fingerprint": s['params'].get('fp', 'chrome'),
                "publicKey": s['params'].get('pbk', ''),
                "shortId": s['params'].get('sid', '')
            }
            if 'spiderX' in s['params']:
                rs["spiderX"] = s['params']['spiderX']
            out["streamSettings"]["realitySettings"] = rs
        elif sec == 'tls':
            tls = {"serverName": s['params'].get('sni', host), "allowInsecure": True}
            if 'alpn' in s['params']:
                tls["alpn"] = [a.strip() for a in str(s['params']['alpn']).split(',') if a.strip()]
            if 'fp' in s['params']:
                tls["fingerprint"] = s['params']['fp']
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
            gs = {"serviceName": s['params'].get('serviceName', ''), "multiMode": s['params'].get('mode', '') == 'multi'}
            if 'authority' in s['params']:
                gs["authority"] = s['params']['authority']
            out["streamSettings"]["grpcSettings"] = gs
        elif net == 'tcp':
            ht = s['params'].get('headerType', 'none')
            out["streamSettings"]["tcpSettings"] = {"header": {"type": ht}}
        elif net in ('xhttp', 'splithttp'):
            xh = {
                "path": s['params'].get('path', '/'),
                "host": s['params'].get('host', host),
                "mode": s['params'].get('mode', 'auto')
            }
            if 'concurrency' in s['params']:
                try:
                    xh["concurrency"] = int(s['params']['concurrency'])
                except Exception:
                    pass
            out["streamSettings"]["xhttpSettings"] = xh
        elif net == 'httpupgrade':
            out["streamSettings"]["httpupgradeSettings"] = {
                "path": s['params'].get('path', '/'),
                "host": s['params'].get('host', host)
            }
    elif scheme in ('hysteria2', 'hy2'):
        out = {
            "protocol": "hysteria2",
            "settings": {"address": host, "port": port, "password": s.get('password', '')},
            "streamSettings": {"network": "hysteria2", "security": "tls",
                               "tlsSettings": {"serverName": s['params'].get('sni', host), "allowInsecure": True,
                                               "alpn": [a.strip() for a in str(s['params'].get('alpn', 'h3')).split(',') if a.strip()]}},
            "tag": tag
        }
        if 'obfs' in s['params']:
            out["settings"]["obfs"] = s['params']['obfs']
            if 'obfs-password' in s['params']:
                out["settings"]["obfsPassword"] = s['params']['obfs-password']
    elif scheme == 'ss':
        out = {
            "protocol": "shadowsocks",
            "settings": {"servers": [{"address": host, "port": port, "method": s.get('method', 'aes-256-gcm'), "password": s.get('password', '')}]},
            "tag": tag
        }
        if s['params'].get('udp_over_tcp') == 'true':
            out["settings"]["udpOverTcp"] = True
    if cfg.get('mux_enabled'):
        mux = {"enabled": True, "concurrency": cfg.get('mux_concurrency', 8)}
        xudp = cfg.get('mux_xudp_concurrency', 0)
        if xudp != 0:
            mux["xudpConcurrency"] = xudp
            mux["xudpProxyUDP443"] = cfg.get('mux_xudp_proxy_udp443', 'reject')
        out["mux"] = mux
    return out


def gen_config(servers, cfg):
    outbounds = []
    tags = []
    for i, s in enumerate(servers):
        base_tag = re.sub(r'[^a-zA-Z0-9_\-]', '_', s.get('name', f"proxy-{i + 1}")) or f"proxy-{i + 1}"
        tag = base_tag
        c = 1
        while tag in tags:
            tag = f"{base_tag}_{c}"
            c += 1
        tags.append(tag)
        out = gen_outbound(s, tag, cfg)
        if out:
            outbounds.append(out)
    outbounds.append({"protocol": "freedom", "tag": "direct"})
    outbounds.append({"protocol": "blackhole", "tag": "block"})

    rt = cfg.get('routing', {})
    rules = []

    if rt.get('block_protocols'):
        rules.append({"type": "field", "protocol": rt['block_protocols'], "outboundTag": "block"})
    if rt.get('block_networks'):
        rules.append({"type": "field", "network": rt['block_networks'], "outboundTag": "block"})
    if rt.get('block_ips'):
        rules.append({"type": "field", "ip": rt['block_ips'], "outboundTag": "block"})
    if rt.get('block_ports'):
        rules.append({"type": "field", "port": rt['block_ports'], "outboundTag": "block"})
    if rt.get('block_domains'):
        rules.append({"type": "field", "domain": rt['block_domains'], "outboundTag": "block"})
    if rt.get('direct_ips'):
        rules.append({"type": "field", "ip": rt['direct_ips'], "outboundTag": "direct"})
    if rt.get('direct_ports'):
        rules.append({"type": "field", "port": rt['direct_ports'], "outboundTag": "direct"})
    if rt.get('direct_domains'):
        rules.append({"type": "field", "domain": rt['direct_domains'], "outboundTag": "direct"})
    for r in rt.get('rules', []):
        rules.append(r)

    gp = cfg.get('global_proxy', 'proxy')
    if gp == 'direct':
        rules.append({"type": "field", "network": "tcp,udp", "outboundTag": "direct"})
    elif gp == 'block':
        rules.append({"type": "field", "network": "tcp,udp", "outboundTag": "block"})
    else:
        rules.append({"type": "field", "network": "tcp,udp", "balancerTag": "balancer"})

    balancer = {
        "tag": "balancer",
        "selector": tags,
        "strategy": {
            "type": cfg.get('balancer_strategy', 'leastLoad'),
            "settings": {
                "expected": cfg.get('balancer_expected', 1),
                "maxRTT": cfg.get('balancer_max_rtt', '2s'),
                "tolerance": cfg.get('balancer_tolerance', 0),
                "baselines": cfg.get('balancer_baselines', ['2s'])
            }
        }
    }
    observatory = {
        "subjectSelector": tags,
        "probeUrl": cfg.get('observatory_url', 'https://www.google.com/generate_204'),
        "probeInterval": cfg.get('observatory_interval', '1m'),
        "probeTimeout": cfg.get('observatory_timeout', '3s'),
        "enableConcurrency": True
    }
    dns = {"servers": cfg.get('dns_servers', DNS_SERVERS), "queryStrategy": cfg.get('dns_query_strategy', 'UseIP')}
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
        "log": {"loglevel": "warning"},
        "dns": dns,
        "inbounds": inbounds,
        "outbounds": outbounds,
        "routing": {"domainStrategy": "IPIfNonMatch", "rules": rules, "balancers": [balancer]},
        "observatory": observatory
    }


def save_json(config, cfg):
    name = cfg.get('json_name', 'xray_config')
    if not name.endswith('.json'):
        name += '.json'
    p = OUTPUT_DIR / name
    with open(p, 'w', encoding='utf-8') as f:
        json.dump(config, f, ensure_ascii=False, indent=2)
    print(f"[+] JSON: {p}")
    return p


def import_routing_rules(cfg):
    hdr("ИМПОРТ ПРАВИЛ МАРШРУТИЗАЦИИ")
    print("  1 - Из локального файла")
    print("  2 - По ссылке")
    print("  0 - Отмена")
    ch = ask("Выбор: ", choices=["0", "1", "2"])
    if ch == "0":
        return cfg

    raw = ""
    if ch == "1":
        files = sorted([p for p in ROUTING_DIR.glob("*") if p.is_file()])
        if not files:
            print(f"[!] Папка {ROUTING_DIR} пуста. Поместите туда файл с правилами.")
            return cfg
        for i, f in enumerate(files, 1):
            print(f"  {i}. {f.name} ({fmt_size(f.stat().st_size)})")
        idx = ask_int("Номер файла: ", mn=1, mx=len(files))
        if idx is None:
            return cfg
        raw = files[idx - 1].read_text(encoding='utf-8', errors='ignore')
    else:
        url = ask("URL с правилами: ")
        if not url:
            return cfg
        raw = dl_url(url)
        if not raw:
            print("[!] Не удалось загрузить.")
            return cfg

    rules_parsed, stats = parse_shadowrocket_rules(raw)
    if not rules_parsed:
        print("[!] Правила не найдены.")
        print(f"    Пропущено строк: {stats.get('skipped', 0)}")
        return cfg

    print(f"\n[+] Найдено правил: {len(rules_parsed)}")
    print(f"    Direct: {stats.get('direct', 0)}")
    print(f"    Proxy: {stats.get('proxy', 0)}")
    print(f"    Block: {stats.get('block', 0)}")
    print(f"    Пропущено (комментарии): {stats.get('commented', 0)}")
    print(f"    Пропущено (URL-REGEX/MITM): {stats.get('url_regex', 0)}")
    print(f"    Пропущено (неизвестные): {stats.get('skipped', 0)}")

    print("\n[?] Примеры (первые 15):")
    for r in rules_parsed[:15]:
        print(f"    {json.dumps(r, ensure_ascii=False)}")

    ans = ask(f"\nДобавить {len(rules_parsed)} правил в routing? (y/n) [y]: ", default="y")
    if ans.lower() == 'y':
        rt = cfg.get('routing', {})
        existing = rt.get('rules', [])
        existing.extend(rules_parsed)
        rt['rules'] = existing
        cfg['routing'] = rt
        cfg_save(cfg)
        print(f"[+] Добавлено правил: {len(rules_parsed)}")
        print(f"[+] Всего правил в routing: {len(existing)}")
    return cfg


def parse_shadowrocket_rules(text):
    rules = []
    stats = {"direct": 0, "proxy": 0, "block": 0, "commented": 0, "url_regex": 0, "skipped": 0}
    proxy_keywords = ["PROXY", "SPEEDPROXY", "BESTPROXY", "AIPROXY", "METAPROXY", "TGPROXY", "SPOTIFYPROXY", "PROXY_GROUP"]
    block_keywords = ["REJECT", "REJECT-DROP", "REJECT-200", "REJECT-DICT", "REJECT-TINYGIF", "REJECT-NO-DROP"]

    for raw_line in text.splitlines():
        ln = raw_line.strip()
        if not ln:
            continue
        if ln.startswith('#') or ln.startswith(';') or ln.startswith('//'):
            stats["commented"] += 1
            continue
        if ln.startswith('[') and ln.endswith(']'):
            continue
        if ln.startswith('!'):
            continue
        if 'URL-REGEX' in ln or 'URL-REGEX-JQ' in ln:
            stats["url_regex"] += 1
            continue
        if ln.startswith('RULE-SET') or ln.startswith('DOMAIN-WILDCARD'):
            stats["skipped"] += 1
            continue

        parts = [p.strip() for p in ln.split(',')]
        if len(parts) < 3:
            stats["skipped"] += 1
            continue

        rule_type = parts[0].upper().strip()
        rule_value = parts[1].strip()
        policy = parts[2].strip().upper()

        outbound = None
        if policy == 'DIRECT':
            outbound = 'direct'
        elif policy in block_keywords:
            outbound = 'block'
        elif any(p in policy for p in proxy_keywords):
            outbound = 'proxy'
        else:
            stats["skipped"] += 1
            continue

        rule = None
        if rule_type == 'DOMAIN-SUFFIX':
            rule = {"type": "field", "domain": [f"domain:{rule_value}"], "outboundTag": outbound}
        elif rule_type == 'DOMAIN':
            rule = {"type": "field", "domain": [rule_value], "outboundTag": outbound}
        elif rule_type == 'DOMAIN-KEYWORD':
            rule = {"type": "field", "domain": [f"keyword:{rule_value}"], "outboundTag": outbound}
        elif rule_type in ('IP-CIDR', 'IP-CIDR6'):
            rule = {"type": "field", "ip": [rule_value], "outboundTag": outbound}
        elif rule_type == 'GEOIP':
            rule = {"type": "field", "ip": [f"geoip:{rule_value.lower()}"], "outboundTag": outbound}
        elif rule_type == 'DST-PORT':
            rule = {"type": "field", "port": rule_value, "outboundTag": outbound}
        elif rule_type == 'PROTOCOL':
            rule = {"type": "field", "protocol": [rule_value.lower()], "outboundTag": outbound}
        elif rule_type == 'PROCESS-NAME':
            rule = {"type": "field", "process": [rule_value], "outboundTag": outbound}
        elif rule_type == 'AND' or rule_type == 'OR' or rule_type == 'NOT':
            stats["skipped"] += 1
            continue

        if rule:
            rules.append(rule)
            if outbound == 'direct':
                stats["direct"] += 1
            elif outbound == 'proxy':
                stats["proxy"] += 1
            elif outbound == 'block':
                stats["block"] += 1
        else:
            stats["skipped"] += 1

    return rules, stats


def config_menu(servers, cfg):
    while True:
        clr()
        hdr("НАСТРОЙКИ ГЕНЕРАЦИИ")
        rt = cfg.get('routing', {})
        print(f"  JSON имя:       {cfg.get('json_name', 'xray_config')}")
        print(f"  DNS:            {', '.join(cfg.get('dns_servers', [])[:3])}...")
        print(f"  DNS strategy:   {cfg.get('dns_query_strategy', 'UseIP')}")
        print(f"  Probe URL:      {cfg.get('observatory_url')}")
        print(f"  Interval:       {cfg.get('observatory_interval')}")
        print(f"  Timeout:        {cfg.get('observatory_timeout')}")
        print(f"  Strategy:       {cfg.get('balancer_strategy')}")
        print(f"  Expected:       {cfg.get('balancer_expected')}")
        print(f"  MaxRTT:         {cfg.get('balancer_max_rtt')}")
        print(f"  Tolerance:      {cfg.get('balancer_tolerance')}")
        print(f"  Ports:          SOCKS {cfg.get('proxy_ports', [10808, 10809])[0]}, HTTP {cfg.get('proxy_ports', [10808, 10809])[1]}")
        print(f"  Mux:            {'ON' if cfg.get('mux_enabled') else 'OFF'} (conc={cfg.get('mux_concurrency')})")
        print(f"  Global proxy:   {cfg.get('global_proxy')}")
        print(f"  Sniffing:       {'ON' if cfg.get('sniffing_enabled') else 'OFF'}")
        print(f"  Direct домены:  {len(rt.get('direct_domains', []))}")
        print(f"  Block домены:   {len(rt.get('block_domains', []))}")
        print(f"  Direct IP:      {len(rt.get('direct_ips', []))}")
        print(f"  Block IP:       {len(rt.get('block_ips', []))}")
        print(f"  Block проток.:  {rt.get('block_protocols', [])}")
        print(f"  Routing rules:  {len(rt.get('rules', []))}")
        line()
        print("  1 - DNS (серверы и стратегия)")
        print("  2 - Обсерватория (URL, интервал, таймаут)")
        print("  3 - Балансировщик (стратегия, expected, maxRTT)")
        print("  4 - Порты SOCKS/HTTP")
        print("  5 - Routing: direct домены")
        print("  6 - Routing: block домены")
        print("  7 - Routing: direct/block IP")
        print("  8 - Routing: block протоколы")
        print("  9 - Импорт правил маршрутизации")
        print(" 10 - Глобальный прокси (direct/proxy/block)")
        print(" 11 - Mux / XUDP")
        print(" 12 - Sniffing")
        print(" 13 - Имя JSON файла")
        print(" 14 - Сбросить к настройкам по умолчанию")
        print("  0 - Назад")
        ch = ask("Выбор: ", choices=[str(i) for i in range(0, 15)])
        if ch == "0":
            break
        if ch == "1":
            v = ask(f"DNS через запятую [{','.join(cfg.get('dns_servers', []))}]: ")
            if v:
                cfg['dns_servers'] = [x.strip() for x in v.split(',') if x.strip()]
            st = ask(f"Стратегия [{cfg.get('dns_query_strategy')}]: ", default=cfg.get('dns_query_strategy'), choices=['UseIP', 'UseIPv4', 'UseIPv6', 'UseIP4', 'AsIs'])
            cfg['dns_query_strategy'] = st
            cfg_save(cfg)
        elif ch == "2":
            u = ask(f"URL [{cfg.get('observatory_url')}]: ")
            if u:
                cfg['observatory_url'] = u
            i = ask(f"Интервал [{cfg.get('observatory_interval')}]: ")
            if i:
                cfg['observatory_interval'] = i
            t = ask(f"Таймаут [{cfg.get('observatory_timeout')}]: ")
            if t:
                cfg['observatory_timeout'] = t
            cfg_save(cfg)
        elif ch == "3":
            st = ask(f"Стратегия [{cfg.get('balancer_strategy')}]: ", default=cfg.get('balancer_strategy'), choices=['leastLoad', 'leastPing', 'random', 'roundRobin'])
            cfg['balancer_strategy'] = st
            e = ask_int(f"Expected [{cfg.get('balancer_expected')}]: ", default=cfg.get('balancer_expected'))
            if e is not None:
                cfg['balancer_expected'] = e
            m = ask(f"MaxRTT [{cfg.get('balancer_max_rtt')}]: ", default=cfg.get('balancer_max_rtt'))
            if m:
                cfg['balancer_max_rtt'] = m
            t = ask(f"Tolerance [{cfg.get('balancer_tolerance')}]: ", default=str(cfg.get('balancer_tolerance')))
            try:
                cfg['balancer_tolerance'] = float(t)
            except Exception:
                pass
            cfg_save(cfg)
        elif ch == "4":
            p_socks = ask_int(f"SOCKS [{cfg.get('proxy_ports', [10808, 10809])[0]}]: ", default=cfg.get('proxy_ports', [10808, 10809])[0])
            p_http = ask_int(f"HTTP [{cfg.get('proxy_ports', [10808, 10809])[1]}]: ", default=cfg.get('proxy_ports', [10808, 10809])[1])
            cfg['proxy_ports'] = [p_socks, p_http]
            cfg_save(cfg)
        elif ch == "5":
            print(f"  Текущие: {rt.get('direct_domains', [])}")
            v = ask("Direct домены (через запятую, пусто=оставить): ")
            if v:
                cfg['routing']['direct_domains'] = [x.strip() for x in v.split(',') if x.strip()]
            cfg_save(cfg)
        elif ch == "6":
            print(f"  Текущие: {rt.get('block_domains', [])}")
            v = ask("Block домены (через запятую, пусто=оставить): ")
            if v:
                cfg['routing']['block_domains'] = [x.strip() for x in v.split(',') if x.strip()]
            cfg_save(cfg)
        elif ch == "7":
            print(f"  Direct IP: {rt.get('direct_ips', [])}")
            v = ask("Direct IP (через запятую): ")
            if v:
                cfg['routing']['direct_ips'] = [x.strip() for x in v.split(',') if x.strip()]
            print(f"  Block IP: {rt.get('block_ips', [])}")
            v = ask("Block IP (через запятую): ")
            if v:
                cfg['routing']['block_ips'] = [x.strip() for x in v.split(',') if x.strip()]
            cfg_save(cfg)
        elif ch == "8":
            print(f"  Текущие: {rt.get('block_protocols', [])}")
            v = ask("Протоколы (через запятую, пусто=очистить): ")
            cfg['routing']['block_protocols'] = [x.strip() for x in v.split(',') if x.strip()] if v else []
            cfg_save(cfg)
        elif ch == "9":
            cfg = import_routing_rules(cfg)
            input("Enter...")
        elif ch == "10":
            gp = ask(f"Глобальный прокси [{cfg.get('global_proxy')}]: ", default=cfg.get('global_proxy'), choices=['proxy', 'direct', 'block'])
            cfg['global_proxy'] = gp
            cfg_save(cfg)
        elif ch == "11":
            print(f"  Mux: {'ON' if cfg.get('mux_enabled') else 'OFF'}")
            print(f"  Concurrency: {cfg.get('mux_concurrency')}")
            print(f"  XUDP concurrency: {cfg.get('mux_xudp_concurrency')}")
            print(f"  XUDP proxyUDP443: {cfg.get('mux_xudp_proxy_udp443')}")
            en = ask("Включить Mux? (y/n) [n]: ", default="n")
            cfg['mux_enabled'] = en.lower() == 'y'
            if cfg['mux_enabled']:
                c = ask_int(f"Concurrency [{cfg.get('mux_concurrency')}]: ", default=cfg.get('mux_concurrency'))
                if c is not None:
                    cfg['mux_concurrency'] = c
                xc = ask_int(f"XUDP concurrency [{cfg.get('mux_xudp_concurrency')}]: ", default=cfg.get('mux_xudp_concurrency'))
                if xc is not None:
                    cfg['mux_xudp_concurrency'] = xc
                xp = ask(f"XUDP proxyUDP443 [{cfg.get('mux_xudp_proxy_udp443')}]: ", default=cfg.get('mux_xudp_proxy_udp443'), choices=['reject', 'skip', 'allow'])
                cfg['mux_xudp_proxy_udp443'] = xp
            cfg_save(cfg)
        elif ch == "12":
            en = ask(f"Sniffing [{cfg.get('sniffing_enabled')}] (y/n): ", default="y" if cfg.get('sniffing_enabled') else "n")
            cfg['sniffing_enabled'] = en.lower() == 'y'
            if cfg['sniffing_enabled']:
                v = ask(f"DestOverride через запятую [{','.join(cfg.get('sniffing_dest_override', []))}]: ")
                if v:
                    cfg['sniffing_dest_override'] = [x.strip() for x in v.split(',') if x.strip()]
                ro = ask(f"RouteOnly [{cfg.get('sniffing_route_only')}] (y/n): ", default="y" if cfg.get('sniffing_route_only') else "n")
                cfg['sniffing_route_only'] = ro.lower() == 'y'
            cfg_save(cfg)
        elif ch == "13":
            n = ask(f"Имя JSON файла [{cfg.get('json_name')}]: ", default=cfg.get('json_name'))
            cfg['json_name'] = n
            cfg_save(cfg)
        elif ch == "14":
            cfg = cfg_default()
            cfg_save(cfg)
            print("[+] Сброшено.")
    return cfg


def save_base64(servers):
    lines = [build_uri(s) for s in servers]
    raw = '\n'.join(lines)
    b64 = base64.b64encode(raw.encode('utf-8')).decode('ascii')
    p1 = OUTPUT_DIR / "servers.txt"
    p2 = OUTPUT_DIR / "servers_base64.txt"
    with open(p1, 'w', encoding='utf-8') as f:
        f.write(raw)
    with open(p2, 'w', encoding='utf-8') as f:
        f.write(b64)
    print(f"[+] Ссылки: {p1}")
    print(f"[+] Base64: {p2}")
    print(f"[+] Строк: {len(lines)}")
    return p1, p2


def save_yaml_clash(servers):
    lines = ["proxies:"]
    for s in servers:
        name = s.get('name', 'proxy')
        if s['scheme'] == 'vless':
            lines.append(f"  - name: \"{name}\"")
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
            lines.append(f"  - name: \"{name}\"")
            lines.append(f"    type: ss")
            lines.append(f"    server: {s['host']}")
            lines.append(f"    port: {s['port']}")
            lines.append(f"    cipher: {s.get('method', '')}")
            lines.append(f"    password: \"{s.get('password', '')}\"")
        elif s['scheme'] in ('hysteria2', 'hy2'):
            lines.append(f"  - name: \"{name}\"")
            lines.append(f"    type: hysteria2")
            lines.append(f"    server: {s['host']}")
            lines.append(f"    port: {s['port']}")
            lines.append(f"    password: \"{s.get('password', '')}\"")
            if 'sni' in s['params']:
                lines.append(f"    sni: {s['params']['sni']}")
    p = OUTPUT_DIR / "clash_proxies.yaml"
    with open(p, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))
    print(f"[+] Clash YAML: {p}")


def backup_servers(servers, name="backup"):
    ts = time.strftime("%Y%m%d_%H%M%S")
    p = BACKUP_DIR / f"{name}_{ts}.txt"
    lines = [build_uri(s) for s in servers]
    with open(p, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))
    print(f"[+] Backup: {p}")
    return p


def stats(servers):
    clr()
    hdr("СТАТИСТИКА")
    print(f"  Всего серверов: {len(servers)}")
    by_proto = {}
    by_type = {}
    by_sec = {}
    for s in servers:
        by_proto[s['scheme']] = by_proto.get(s['scheme'], 0) + 1
        t = s['params'].get('type', 'tcp')
        by_type[t] = by_type.get(t, 0) + 1
        sec = s['params'].get('security', 'none')
        by_sec[sec] = by_sec.get(sec, 0) + 1
    print("\n  По протоколу:")
    for k, v in sorted(by_proto.items()):
        print(f"    {k}: {v}")
    print("\n  По транспорту:")
    for k, v in sorted(by_type.items()):
        print(f"    {k}: {v}")
    print("\n  По security:")
    for k, v in sorted(by_sec.items()):
        print(f"    {k}: {v}")
    input("\nEnter...")


def main():
    ensure_dirs()
    cfg = cfg_load()
    clr()
    hdr("SubManager - Менеджер прокси-подписок для iSH")
    print(f"  Input:  {INPUT_DIR}")
    print(f"  Output: {OUTPUT_DIR}")
    print(f"  Routing: {ROUTING_DIR}")
    print("=" * W)
    servers = []
    while True:
        clr()
        hdr("ГЛАВНОЕ МЕНЮ")
        print(f"  Серверов: {len(servers)}")
        line()
        print("  1 - Загрузить исходники")
        print("  2 - Редактировать серверы")
        print("  3 - Показать список серверов")
        print("  4 - Статистика")
        print("  5 - Сгенерировать JSON Xray")
        print("  6 - Настройки генерации")
        print("  7 - Сохранить ссылки (txt + base64)")
        print("  8 - Сохранить Clash YAML")
        print("  9 - Сделать бэкап")
        print("  0 - Выход")
        ch = ask("Выбор: ", choices=[str(i) for i in range(0, 10)])
        if ch == "0":
            if servers:
                ans = ask("Сделать бэкап перед выходом? (y/n) [n]: ", default="n")
                if ans.lower() == 'y':
                    backup_servers(servers)
            print("[+] Выход.")
            break
        if ch == "1":
            raw = load_source()
            if raw:
                links = extract_links(raw)
                if not links:
                    print("[!] Ссылки не найдены.")
                else:
                    new = []
                    for ln in links:
                        p = parse_uri(ln)
                        if p:
                            new.append(p)
                    if new:
                        servers.extend(new)
                        print(f"[+] Загружено: {len(new)}. Всего: {len(servers)}")
                    else:
                        print("[!] Парсинг не удался.")
            input("\nEnter...")
        elif ch == "2":
            if not servers:
                print("[!] Список пуст.")
                input("Enter...")
                continue
            servers = edit_servers(servers)
        elif ch == "3":
            show_servers_list(servers, show_params=True)
            input("\nEnter...")
        elif ch == "4":
            stats(servers)
        elif ch == "5":
            if not servers:
                print("[!] Нет серверов.")
                input("Enter...")
                continue
            cfg_json = gen_config(servers, cfg)
            save_json(cfg_json, cfg)
            input("\nEnter...")
        elif ch == "6":
            cfg = config_menu(servers, cfg)
        elif ch == "7":
            if not servers:
                print("[!] Нет серверов.")
                input("Enter...")
                continue
            save_base64(servers)
            input("\nEnter...")
        elif ch == "8":
            if not servers:
                print("[!] Нет серверов.")
                input("Enter...")
                continue
            save_yaml_clash(servers)
            input("\nEnter...")
        elif ch == "9":
            if not servers:
                print("[!] Нет серверов.")
                input("Enter...")
                continue
            backup_servers(servers)
            input("\nEnter...")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n[!] Прервано.")
    except Exception as e:
        print(f"\n[!] Ошибка: {e}")
        import traceback
        traceback.print_exc()
PYEOF

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

echo "[*] Запуск SubManager..."
python3 ~/SubManager/SubManager.py
