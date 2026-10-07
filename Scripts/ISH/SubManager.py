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
    echo "[!] Нет подключения. Повтор через 5 сек..."
    sleep 5
done
echo "[+] Интернет доступен."

echo "[*] Обновление и установка зависимостей..."
apk update
apk upgrade
apk add python3 curl wget aria2 openssl ca-certificates bind-tools bash py3-pip git

echo "[*] Создание папок..."
mkdir -p ~/SubManager/Input
mkdir -p ~/SubManager/Output
mkdir -p ~/SubManager/Backups
mkdir -p ~/SubManager/Routing

cat << 'PYEOF' > ~/SubManager/SubManager.py
#!/usr/bin/env python3
import os, sys, re, json, base64, urllib.request, ssl, subprocess, shutil, time, random, copy, ipaddress
from urllib.parse import urlparse, parse_qs, urlencode, unquote, quote
from pathlib import Path

HOME = Path.home()
BASE = HOME / "SubManager"
INPUT_DIR = BASE / "Input"
OUTPUT_DIR = BASE / "Output"
BACKUP_DIR = BASE / "Backups"
ROUTING_DIR = BASE / "Routing"
CFG_FILE = BASE / "config.json"
UA = "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1"
W = 52
EXIT = "__EXIT__"
DNS_SERVERS = ["8.8.8.8", "8.8.4.4", "1.1.1.1", "94.140.14.14", "94.140.15.15"]

DURATION_RE = re.compile(r'^(\d+(?:\.\d+)?)(ms|s|m|h|d)?$')
DURATION_UNITS = {'ms', 's', 'm', 'h', 'd'}
BALANCER_TYPES = {"leastload": "leastLoad", "leastping": "leastPing", "random": "random", "roundrobin": "roundRobin"}
TLD_ONLY = {'ru', 'su', 'by', 'kz', 'xn--p1ai', 'рф'}

PARAM_DEFAULTS = {
    "scheme": "vless",
    "type": "tcp",
    "security": "reality",
    "flow": "xtls-rprx-vision",
    "path": "/",
    "host": "",
    "sni": "",
    "pbk": "",
    "sid": "",
    "fp": "chrome",
    "serviceName": "",
    "authority": "",
    "mode": "auto",
    "port": "443",
    "host_addr": "",
    "alpn": "h2",
    "obfs": "salamander",
    "obfs-password": "",
    "id": "",
    "password": "",
    "method": "aes-256-gcm",
    "concurrency": "4",
    "spiderX": "/",
    "headerType": "none",
    "heartbeatPeriod": "0",
    "alterId": "0",
    "encryption": "auto",
    "allowedIPs": "0.0.0.0/0",
    "mtu": "1420",
    "dns": "1.1.1.1",
    "presharedKey": "",
    "keepalive": "0",
    "up": "",
    "down": "",
    "congestion_control": "cubic",
    "pinned_certchain_sha256": "",
    "verify_peer_cert_by_name": "",
    "jc": "4",
    "jmin": "40",
    "jmax": "70",
    "s1": "30",
    "s2": "30",
    "h1": "1",
    "h2": "2",
    "h3": "3",
    "h4": "4",
}

GEOSITE_SUGGESTIONS = [
    "geosite:private",
    "geosite:category-ads-all",
    "geosite:category-ru",
    "geosite:category-porn",
    "geosite:google",
    "geosite:youtube",
    "geosite:telegram",
    "geosite:twitter",
    "geosite:facebook",
    "geosite:instagram",
    "geosite:openai",
    "geosite:geolocation-cn",
    "geosite:cn",
    "geosite:apple",
    "geosite:icloud",
    "geosite:microsoft",
    "geosite:github",
    "geosite:netflix",
    "geosite:spotify",
    "geosite:discord",
    "geosite:tiktok",
    "geosite:category-games",
    "geosite:category-media-ru",
    "geosite:category-communication",
]

GEOIP_SUGGESTIONS = [
    "geoip:private",
    "geoip:ru",
    "geoip:by",
    "geoip:kz",
    "geoip:cn",
    "geoip:us",
    "geoip:eu",
    "geoip:telegram",
]


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
    dom_only = []
    kw_set = set()
    re_set = set()
    other = []
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
        elif scheme == 'socks5':
            p = urlparse(uri)
            r['id'] = unquote(p.username or '')
            r['password'] = unquote(p.password or '')
            r['host'] = p.hostname or ''
            r['port'] = str(p.port) if p.port else ''
            for k, v in parse_qs(p.query).items():
                r['params'][k] = v[0] if len(v) == 1 else v
        elif scheme == 'http':
            p = urlparse(uri)
            r['id'] = unquote(p.username or '')
            r['password'] = unquote(p.password or '')
            r['host'] = p.hostname or ''
            r['port'] = str(p.port) if p.port else ''
            for k, v in parse_qs(p.query).items():
                r['params'][k] = v[0] if len(v) == 1 else v
        elif scheme == 'tuic':
            p = urlparse(uri)
            r['id'] = unquote(p.username or '')
            r['password'] = unquote(p.password or '')
            r['host'] = p.hostname or ''
            r['port'] = str(p.port) if p.port else ''
            for k, v in parse_qs(p.query).items():
                r['params'][k] = v[0] if len(v) == 1 else v
        elif scheme == 'juicity':
            p = urlparse(uri)
            r['id'] = unquote(p.username or '')
            r['password'] = unquote(p.password or '')
            r['host'] = p.hostname or ''
            r['port'] = str(p.port) if p.port else ''
            for k, v in parse_qs(p.query).items():
                r['params'][k] = v[0] if len(v) == 1 else v
        elif scheme == 'wireguard':
            p = urlparse(uri)
            r['id'] = unquote(p.username or '')
            r['host'] = p.hostname or ''
            r['port'] = str(p.port) if p.port else ''
            for k, v in parse_qs(p.query).items():
                r['params'][k] = v[0] if len(v) == 1 else v
        elif scheme in ('amneziawg', 'awg'):
            p = urlparse(uri)
            r['id'] = unquote(p.username or '')
            r['host'] = p.hostname or ''
            r['port'] = str(p.port) if p.port else ''
            for k, v in parse_qs(p.query).items():
                r['params'][k] = v[0] if len(v) == 1 else v
        elif scheme == 'mieru':
            p = urlparse(uri)
            r['id'] = unquote(p.username or '')
            r['password'] = unquote(p.password or '')
            r['host'] = p.hostname or ''
            r['port'] = str(p.port) if p.port else ''
            for k, v in parse_qs(p.query).items():
                r['params'][k] = v[0] if len(v) == 1 else v
        elif scheme == 'sudoku':
            p = urlparse(uri)
            r['id'] = unquote(p.username or '')
            r['password'] = unquote(p.password or '')
            r['host'] = p.hostname or ''
            r['port'] = str(p.port) if p.port else ''
            for k, v in parse_qs(p.query).items():
                r['params'][k] = v[0] if len(v) == 1 else v
        elif scheme == 'openconnect':
            p = urlparse(uri)
            r['id'] = unquote(p.username or '')
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
                             ('shortId', 'sid'), ('fingerprint', 'fp'),
                             ('spiderX', 'spiderX')]:
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
            "direct_domains": [],
            "block_domains": [],
            "direct_ips": [],
            "block_ips": [],
            "block_protocols": [],
            "direct_ports": [],
            "block_ports": [],
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
        'Ъ':'','Ы':'Y','Ь':'','Э':'E','Ю':'Yu','Я':'Ya',
        ' ':'_'
    }
    out = []
    for ch in name:
        out.append(mapping.get(ch, ch))
    return ''.join(out)


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
            print(f"[+] Обнаружен JSON конфиг. Извлечено outbounds: {len(servers)}")
            return servers, json_data
        else:
            print("[!] JSON найден, но прокси outbounds не обнаружены.")
    links = extract_links(raw)
    if links:
        servers = []
        for l in links:
            p = parse_uri(l)
            if p:
                servers.append(p)
        print(f"[+] Найдено ссылок: {len(links)}, успешно распарсено: {len(servers)}")
        return servers, None
    return [], None


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
    print("  1 - Полное сходство (scheme+host+port+id/password)")
    print("  2 - По имени")
    print("  3 - По адресу (host+port)")
    print("  4 - По адресу и пользователю")
    print("  5 - По протоколу + адрес + порт")
    print("  q - Отмена")
    ch = ask("Выбор: ", choices=["1", "2", "3", "4", "5"])
    if ch == EXIT:
        return servers
    mode_map = {"1": "full", "2": "name", "3": "addr", "4": "user", "5": "proto"}
    return dedupe_servers(servers, mode_map[ch])


def delete_by_keyword(servers):
    hdr("УДАЛЕНИЕ СЕРВЕРОВ")
    print("  1 - По ключевым словам в имени")
    print("  2 - По протоколу")
    print("  3 - По транспорту")
    print("  4 - По security")
    print("  5 - По домену")
    print("  6 - По номерам")
    print("  7 - Инвертировать (оставить только совпадающие)")
    print("  q - Отмена")
    ch = ask("Выбор: ", choices=["1", "2", "3", "4", "5", "6", "7"])
    if ch == EXIT:
        return servers
    idxs = None
    if ch == "1":
        kw = ask("Ключевые слова через запятую (q - отмена): ")
        if kw == EXIT:
            return servers
        kws = [k.strip().lower() for k in kw.split(',') if k.strip()]
        if not kws:
            return servers
        idxs = [i for i, s in enumerate(servers) if any(k in s.get('name', '').lower() for k in kws)]
    elif ch == "2":
        proto = ask("Протокол (vless/ss/hysteria2/trojan/vmess/wireguard): ").lower()
        if proto == EXIT:
            return servers
        idxs = [i for i, s in enumerate(servers) if s['scheme'] == proto]
    elif ch == "3":
        t = ask("Транспорт (tcp/ws/grpc/xhttp/httpupgrade): ").lower()
        if t == EXIT:
            return servers
        idxs = [i for i, s in enumerate(servers) if s['params'].get('type', 'tcp') == t]
    elif ch == "4":
        sec = ask("Security (none/tls/reality): ").lower()
        if sec == EXIT:
            return servers
        idxs = [i for i, s in enumerate(servers) if s['params'].get('security', 'none') == sec]
    elif ch == "5":
        dom = ask("Домен (часть): ").lower()
        if dom == EXIT:
            return servers
        idxs = [i for i, s in enumerate(servers) if dom in s['host'].lower()]
    elif ch == "6":
        show_servers_list(servers)
        sel = ask_multi("Номера (q - отмена): ", 1, len(servers))
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
    sel = ask_multi("Номера для дублирования (1,3-5,all): ", 1, len(servers))
    if sel == EXIT or not sel:
        return servers
    new = []
    for idx in sel:
        s = copy.deepcopy(servers[idx - 1])
        s['name'] = f"{s.get('name', '')} (copy)"
        new.append(s)
    servers.extend(new)
    print(f"[+] Создано дубликатов: {len(new)}")
    ans = ask("Отредактировать дубликаты сейчас? (y/n) [n]: ", default="n")
    if ans.lower() == 'y':
        new_indices = list(range(len(servers) - len(new), len(servers)))
        edit_params_for_group(servers, new_indices)
    return servers


PARAM_LIST = [
    ("scheme", "Протокол"),
    ("type", "Транспорт"),
    ("security", "Безопасность"),
    ("flow", "Flow"),
    ("path", "Path"),
    ("host", "Host (заголовок)"),
    ("sni", "SNI"),
    ("pbk", "PublicKey (pbk)"),
    ("sid", "ShortId (sid)"),
    ("fp", "Fingerprint (fp)"),
    ("serviceName", "ServiceName (gRPC)"),
    ("authority", "Authority (gRPC)"),
    ("mode", "Mode"),
    ("port", "Порт"),
    ("host_addr", "Адрес сервера"),
    ("alpn", "ALPN"),
    ("obfs", "Obfs"),
    ("obfs-password", "Obfs-password"),
    ("id", "UUID / логин"),
    ("password", "Пароль"),
    ("method", "Метод шифрования"),
    ("concurrency", "Concurrency (xhttp)"),
    ("spiderX", "SpiderX (reality)"),
    ("headerType", "Header Type (tcp)"),
    ("heartbeatPeriod", "HeartbeatPeriod (ws)"),
    ("alterId", "AlterID (vmess)"),
    ("encryption", "Шифрование (vmess)"),
    ("allowedIPs", "AllowedIPs (wg)"),
    ("mtu", "MTU (wg)"),
    ("dns", "DNS (wg)"),
    ("presharedKey", "PresharedKey (wg)"),
    ("keepalive", "Keepalive (wg)"),
    ("up", "Up (hysteria)"),
    ("down", "Down (hysteria)"),
    ("congestion_control", "Congestion Control"),
    ("pinned_certchain_sha256", "PinnedCertHash (hex)"),
    ("verify_peer_cert_by_name", "VerifyPeerCertByName"),
    ("jc", "Jc (AWG)"),
    ("jmin", "Jmin (AWG)"),
    ("jmax", "Jmax (AWG)"),
    ("s1", "S1 (AWG)"),
    ("s2", "S2 (AWG)"),
    ("h1", "H1 (AWG)"),
    ("h2", "H2 (AWG)"),
    ("h3", "H3 (AWG)"),
    ("h4", "H4 (AWG)"),
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
    "allow_insecure": ["0", "1"],
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
    "obfs": lambda s: s['scheme'] in ('hysteria2',),
    "obfs-password": lambda s: s['scheme'] in ('hysteria2',),
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
            print(f"  Несовместимых (пропустятся): {len(indices) - len(compatible)}")
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


def edit_servers(servers):
    while True:
        clr()
        hdr("РЕДАКТИРОВАНИЕ СЕРВЕРОВ")
        show_servers_list(servers)
        print(f"\n  Всего: {len(servers)}")
        ln()
        print("  1 - Имена")
        print("  2 - Параметры (выбрать группу)")
        print("  3 - Удалить сервер(ы) по номерам")
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
            sel = ask_multi("Номера серверов для редактирования (q - отмена): ", 1, len(servers))
            if sel == EXIT or not sel:
                continue
            edit_params_for_group(servers, [i - 1 for i in sel])
        elif ch == "3":
            sel = ask_multi("Номера для удаления (q - отмена): ", 1, len(servers))
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
            if 'pinned_certchain_sha256' in s['params']:
                tls["pinnedPeerCertSha256"] = s['params']['pinned_certchain_sha256']
            if 'verify_peer_cert_by_name' in s['params']:
                tls["verifyPeerCertByName"] = s['params']['verify_peer_cert_by_name']
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
        "tag": "balancer",
        "selector": tags,
        "strategy": {
            "type": normalize_balancer_type(cfg.get('balancer_strategy', 'leastLoad')),
            "settings": {
                "expected": expected,
                "maxRTT": normalize_duration(cfg.get('balancer_max_rtt', '2s'), 's'),
                "tolerance": normalize_float(cfg.get('balancer_tolerance', 0), 0.0),
                "baselines": [normalize_duration(b, 's') for b in cfg.get('balancer_baselines', ['2s'])]
            }
        }
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
                        changes.append(f"outbounds[{oi}].streamSettings.tlsSettings.allowInsecure: удалён")
                        del ts['allowInsecure']
                    if 'verifyPeerCertInNames' in ts:
                        changes.append(f"outbounds[{oi}].streamSettings.tlsSettings.verifyPeerCertInNames -> verifyPeerCertByName")
                        ts['verifyPeerCertByName'] = ts.pop('verifyPeerCertInNames')
                    if 'pinnedPeerCertificateChainSha256' in ts:
                        changes.append(f"outbounds[{oi}].streamSettings.tlsSettings.pinnedPeerCertificateChainSha256 -> pinnedPeerCertSha256")
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
    stats = {"direct": 0, "proxy": 0, "block": 0, "skipped": 0}
    for raw in text.splitlines():
        s = raw.strip()
        if not s:
            continue
        if s.startswith('!') or s.startswith('#'):
            continue
        if s.startswith('@@'):
            continue
        if s.startswith('||') or s.startswith('|'):
            domain = s.lstrip('|').rstrip('^').strip()
            if domain:
                rules.append({"type": "field", "domain": [f"domain:{domain}"], "outboundTag": "block"})
                stats["block"] += 1
    return rules, stats


def import_routing_rules(cfg, target='xray'):
    hdr("ИМПОРТ ПРАВИЛ МАРШРУТИЗАЦИИ")
    print("  1 - Shadowrocket / Clash / Surge")
    print("  2 - AdGuard")
    print("  q - Отмена")
    ch = ask("Выбор: ", choices=["1", "2"])
    if ch == EXIT:
        return cfg
    parser = parse_shadowrocket_rules if ch == "1" else parse_adguard_rules

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
        print("  1 - Импорт правил (Shadowrocket/Clash/AdGuard)")
        print("  2 - Просмотр/очистка custom rules")
        print("  3 - Настроить DNS для роутинга")
        print("  4 - Настроить порядок правил")
        print("  5 - Настроить глобальный прокси")
        print("  6 - Сгенерировать happ:// ссылку")
        print("  7 - Сгенерировать v2raytun:// ссылку")
        print("  8 - Сохранить JSON роутинга (raw)")
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
            print("  DNS настройки для роутинга")
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
                print("[!] Нужно указать все три в любом порядке.")
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
            print(f"    {link[:120]}...")
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
            print(f"    {link[:120]}...")
            input("Enter...")
        elif ch == "8":
            profile = gen_happ_routing(cfg)
            j = json.dumps(profile, ensure_ascii=False, indent=2)
            p = OUTPUT_DIR / "routing_profile.json"
            with open(p, 'w', encoding='utf-8') as f:
                f.write(j)
            print(f"[+] JSON роутинга: {p}")
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
        print(" 10 - Импорт правил маршрутизации")
        print(" 11 - Просмотр/очистка custom rules")
        print(" 12 - Глобальный прокси")
        print(" 13 - Mux / XUDP")
        print(" 14 - Sniffing")
        print(" 15 - Имя JSON файла")
        print(" 16 - Примечание JSON-сервера (для Happ)")
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
            i = ask(f"Интервал [{cfg.get('observatory_interval')}] (например 30s, 1m, 2m): ", default="")
            if i != EXIT and i:
                cfg['observatory_interval'] = normalize_duration(i, 'm')
                print(f"    -> {cfg['observatory_interval']}")
            t = ask(f"Таймаут [{cfg.get('observatory_timeout')}] (например 2s, 5s): ", default="")
            if t != EXIT and t:
                cfg['observatory_timeout'] = normalize_duration(t, 's')
                print(f"    -> {cfg['observatory_timeout']}")
            cfg_save(cfg)
        elif ch == "3":
            print(f"  Стратегии: leastLoad — топ-серверы по задержке и стабильности;")
            print(f"             leastPing — топ-серверы по чистому пингу;")
            print(f"             random — случайный сервер;")
            print(f"             roundRobin — по кругу.")
            print(f"  expected — сколько 'лучших' серверов использовать (1=только лучший, 3-5=пул).")
            st = ask(f"Стратегия [{cfg.get('balancer_strategy')}]: ", choices=['leastLoad', 'leastPing', 'random', 'roundRobin'])
            if st != EXIT:
                cfg['balancer_strategy'] = normalize_balancer_type(st)
            e = ask_int(f"Expected [{cfg.get('balancer_expected')}] (1=только лучший; 3=пул 3 серверов; 5+ баланс): ", default=cfg.get('balancer_expected'))
            if e != EXIT and e is not None:
                cfg['balancer_expected'] = e
            m = ask(f"MaxRTT [{cfg.get('balancer_max_rtt')}] (1s/2s/3s) - сервера с большим пингом не рассматриваются: ", default="")
            if m != EXIT and m:
                cfg['balancer_max_rtt'] = normalize_duration(m, 's')
                print(f"    -> {cfg['balancer_max_rtt']}")
            tol = ask(f"Tolerance [{cfg.get('balancer_tolerance')}] - допустимое отклонение от лучшего: ", default="")
            if tol != EXIT and tol:
                cfg['balancer_tolerance'] = normalize_float(tol, 0.0)
            bl = ask(f"Baselines через запятую [{','.join(cfg.get('balancer_baselines', ['2s']))}]: ", default="")
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
            print(f"  Подсказки geosite: {', '.join(GEOSITE_SUGGESTIONS[:10])}")
            print(f"  Всего geosite-вариантов: {len(GEOSITE_SUGGESTIONS)}")
            print(f"  Формат: geosite:category-ru, domain:example.com, keyword:.ru, regexp:.*\\.google\\.com$")
            v = ask("Direct домены (через запятую, пусто=очистить, q=отмена): ")
            if v == EXIT:
                continue
            cfg['routing']['direct_domains'] = [x.strip() for x in v.split(',') if x.strip()] if v else []
            cfg_save(cfg)
        elif ch == "6":
            print(f"  Текущие: {rt.get('block_domains', [])}")
            print(f"  Подсказки geosite: {', '.join(GEOSITE_SUGGESTIONS[:10])}")
            print(f"  Всего geosite-вариантов: {len(GEOSITE_SUGGESTIONS)}")
            print(f"  Формат: geosite:category-ads-all, domain:ads.example.com, keyword:ads, regexp:.*\\.ads\\.com$")
            v = ask("Block домены (через запятую, пусто=очистить, q=отмена): ")
            if v == EXIT:
                continue
            cfg['routing']['block_domains'] = [x.strip() for x in v.split(',') if x.strip()] if v else []
            cfg_save(cfg)
        elif ch == "7":
            print(f"  Direct IP: {rt.get('direct_ips', [])}")
            print(f"  Подсказки geoip: {', '.join(GEOIP_SUGGESTIONS)}")
            print(f"  Формат: geoip:ru, geoip:private, 1.1.1.1, 192.168.0.0/16")
            v = ask("Direct IP: ")
            if v != EXIT:
                cfg['routing']['direct_ips'] = [x.strip() for x in v.split(',') if x.strip()] if v else []
            print(f"  Block IP: {rt.get('block_ips', [])}")
            print(f"  Подсказки geoip: {', '.join(GEOIP_SUGGESTIONS)}")
            v = ask("Block IP: ")
            if v != EXIT:
                cfg['routing']['block_ips'] = [x.strip() for x in v.split(',') if x.strip()] if v else []
            cfg_save(cfg)
        elif ch == "8":
            print(f"  Текущие: {rt.get('block_protocols', [])}")
            print(f"  Примеры: bittorrent, quic, http")
            v = ask("Протоколы (через запятую, пусто=очистить, q=отмена): ")
            if v == EXIT:
                continue
            cfg['routing']['block_protocols'] = [x.strip() for x in v.split(',') if x.strip()] if v else []
            cfg_save(cfg)
        elif ch == "9":
            print(f"  Текущий: {' -> '.join(cfg.get('routing_order', []))}")
            print(f"  Доступные: block, direct, proxy")
            v = ask("Порядок (block,direct,proxy): ")
            if v == EXIT:
                continue
            parts = [p.strip().lower() for p in v.split(',') if p.strip()]
            if all(p in ('block', 'direct', 'proxy') for p in parts) and len(set(parts)) == 3:
                cfg['routing_order'] = parts
                cfg_save(cfg)
                print("[+] Сохранено.")
            else:
                print("[!] Нужно указать все три в любом порядке.")
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
            print(f"  proxy — через балансировщик; direct — напрямую; block — блокировать всё")
            gp = ask(f"Глобальный прокси [{cfg.get('global_proxy')}]: ", choices=['proxy', 'direct', 'block'])
            if gp != EXIT:
                cfg['global_proxy'] = gp
            cfg_save(cfg)
        elif ch == "13":
            print(f"  Mux: {'ON' if cfg.get('mux_enabled') else 'OFF'}")
            print(f"  Concurrency: {cfg.get('mux_concurrency')}")
            print(f"  XUDP concurrency: {cfg.get('mux_xudp_concurrency')}")
            print(f"  XUDP proxyUDP443: {cfg.get('mux_xudp_proxy_udp443')}")
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
                auto = ask("Использовать как имя файла (транслитом)? (y/n) [n]: ", default="n")
                if auto == EXIT:
                    continue
                if auto.lower() == 'y':
                    tr = transliterate(n)
                    cfg['json_name'] = sanitize_filename(tr)
                    cfg['json_use_remarks_as_name'] = True
                    print(f"    Имя файла: {cfg['json_name']}.json")
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
        print("  3 - Экспорт Clash YAML")
        print("  q - Назад")
        ch = ask("Выбор: ", choices=["1", "2", "3"])
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
        elif ch == "3":
            name = ask("Имя YAML [selected_clash.yaml]: ", default="selected_clash.yaml")
            if name == EXIT:
                name = "selected_clash.yaml"
            save_yaml_clash(subset, name)
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
    remarks = ask(f"Примечание сервера в Happ/клиенте [{default_remarks}]: ", default=default_remarks)
    if remarks == EXIT:
        return None, None
    cfg['json_remarks'] = remarks
    auto = ask("Использовать примечание как имя файла (транслитом)? (y/n) [n]: ", default="n")
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
    servers = []
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
        print("  7 - Роутинг для клиентов (happ/v2raytun)")
        print("  8 - Экспорт выбранных серверов")
        print("  9 - Сохранить ссылки (txt + base64)")
        print(" 10 - Сохранить Clash YAML")
        print(" 11 - Сделать бэкап")
        print(" 12 - Нормализовать существующий конфиг")
        print(" 13 - Нормализовать бэкап серверов")
        print("  q - Выход")
        ch = ask("Выбор: ", choices=[str(i) for i in range(1, 14)])
        if ch == EXIT:
            if servers:
                a = ask("Сделать бэкап перед выходом? (y/n) [n]: ", default="n")
                if a != EXIT and a.lower() == 'y':
                    backup_servers(servers)
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
    echo "[!] Соединение потеряно. Повтор через 5 сек..."
    sleep 5
done

echo "[*] Запуск SubManager..."
python3 ~/SubManager/SubManager.py
