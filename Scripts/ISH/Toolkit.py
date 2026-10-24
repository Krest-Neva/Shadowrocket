#!/bin/sh
# ==========================================================================
#  Toolkit — единый файл (оболочка + Python-модули): сеть, прокси, анализ трафика, скрипты, конфиги
#  Запуск:  sh Toolkit.sh      (работает в iSH/Alpine, Termux, Debian/Ubuntu, macOS, Linux)
#  Архитектура: этот sh-файл распаковывает модули в ~/Shadowrocket/.core,
#  готовит окружение (пакеты, подбор версии Alpine с откатом на стабильную),
#  запускает launcher.py и выполняет «действия» (ремонт, обновление), которые
#  запрашивает меню. Все циклы ограничены по числу попыток.
#  Модули: tkcore tkcodec rules routing launcher netcenter netdiag filemgr guide decoder listlab adblock
#          sqlitetxt spylog scriptforge configforge subman regexb vault ghapi qr
# ==========================================================================
TK_BUILD="202610241652"
TK_UPDATE_URL="https://raw.githubusercontent.com/Krest-Neva/Shadowrocket/refs/heads/main/Scripts/ISH/Toolkit.py"

HOME="${HOME:-/root}"; export HOME
BASE="$HOME/Shadowrocket"; CONF="$BASE/.config"; CORE="$BASE/.core"
mkdir -p "$CONF" "$CORE" 2>/dev/null
case "$0" in /*) TK_SELF="$0" ;; *) TK_SELF="$(pwd)/$0" ;; esac
[ -f "$TK_SELF" ] && echo "$TK_SELF" > "$CONF/self_path"

# ---------- цвета (только в терминале) ----------
if [ -t 1 ]; then
  C_OK='\033[38;5;84m'; C_ER='\033[38;5;203m'; C_WN='\033[38;5;220m'; C_IN='\033[38;5;51m'; C_AC='\033[38;5;45m'; C_RS='\033[0m'
else
  C_OK=''; C_ER=''; C_WN=''; C_IN=''; C_AC=''; C_RS=''
fi
say_ok()  { printf '%b[+] %s%b\n' "$C_OK" "$*" "$C_RS"; }
say_er()  { printf '%b[!] %s%b\n' "$C_ER" "$*" "$C_RS"; }
say_wn()  { printf '%b[!] %s%b\n' "$C_WN" "$*" "$C_RS"; }
say_in()  { printf '%b[*] %s%b\n' "$C_IN" "$*" "$C_RS"; }
# T "ру" "en" — сообщение на выбранном языке
T() { if [ "$TK_LANG" = "en" ]; then printf '%s' "$2"; else printf '%s' "$1"; fi; }

# ---------- выбор языка при первом запуске ----------
TK_LANG="ru"
if [ -f "$CONF/lang" ]; then
  TK_LANG="$(cat "$CONF/lang" 2>/dev/null)"
  [ "$TK_LANG" = "en" ] || TK_LANG="ru"
elif [ -t 0 ]; then
  printf '%b========================================\n  Language / Язык\n========================================%b\n' "$C_WN" "$C_RS"
  printf '  1 - Русский [по умолчанию]\n  2 - English\nВыбор / Choice [1]: '
  IFS= read -r _lc
  [ "$_lc" = "2" ] && TK_LANG="en"
  echo "$TK_LANG" > "$CONF/lang"
fi

# ---------- определение среды ----------
detect_env() {
  _u="$(uname -a 2>/dev/null | tr 'A-Z' 'a-z')"
  case "$_u" in *darwin*) TK_ENV=macos; return ;; esac
  case "${PREFIX:-}" in *com.termux*) TK_ENV=termux; return ;; esac
  case "$_u" in *ish*) TK_ENV=ish; return ;; esac
  if [ -f /etc/alpine-release ]; then TK_ENV=alpine
  elif command -v apt-get >/dev/null 2>&1; then TK_ENV=debian
  elif command -v dnf >/dev/null 2>&1; then TK_ENV=fedora
  else TK_ENV=linux; fi
}
detect_env
export TK_ENV TK_BUILD PYTHONUTF8=1 PYTHONIOENCODING=utf-8
is_apk() { case "$TK_ENV" in ish|alpine) command -v apk >/dev/null 2>&1 ;; *) return 1 ;; esac; }
stty erase '^?' 2>/dev/null   # Backspace в iSH шлёт DEL

# ---------- спиннер для долгих операций ----------
run_spin() {
  _msg="$1"; shift
  if [ ! -t 1 ]; then say_in "$_msg..."; "$@" >/tmp/tk_spin.log 2>&1; return $?; fi
  ( "$@" ) >/tmp/tk_spin.log 2>&1 &
  _pid=$!; _i=0
  while kill -0 "$_pid" 2>/dev/null; do
    case $((_i % 4)) in 0) _f='|' ;; 1) _f='/' ;; 2) _f='-' ;; *) _f='\' ;; esac
    printf '\r%b %s%b %s ' "$C_AC" "$_f" "$C_RS" "$_msg" >&2
    _i=$((_i + 1)); sleep 1
  done
  wait "$_pid" 2>/dev/null; _rc=$?
  printf '\r\033[K' >&2
  return $_rc
}

# ---------- геолокация для работы iSH в фоне (с предупреждением и паузой 3 с) ----------
loc_keepalive() {
  if [ ! -e /dev/location ]; then
    say_in "$(T '/dev/location не найден — фиктивный запрос геолокации не нужен/пропущен.' '/dev/location not found — dummy geolocation request skipped.')"
    return
  fi
  if [ -f "$CONF/noloc" ]; then
    say_in "$(T 'Фоновый запрос геолокации отключён в настройках.' 'Background location request is disabled in settings.')"
    return
  fi
  say_wn "$(T 'Сейчас будет запрошена геолокация (фиктивно, чтобы iSH стабильнее работал в фоне). Данные отбрасываются и никуда не отправляются.' 'A dummy geolocation request is about to be made (keeps iSH running in the background). Data is discarded and never sent anywhere.')"
  _n=3
  while [ "$_n" -gt 0 ]; do printf '\r  %b%s%b ' "$C_WN" "$_n" "$C_RS"; sleep 1; _n=$((_n - 1)); done
  printf '\r\033[K'
  [ -f "$CONF/loc.pid" ] && kill "$(cat "$CONF/loc.pid")" 2>/dev/null
  ( cat /dev/location >/dev/null 2>&1 ) &
  echo $! > "$CONF/loc.pid"
  say_ok "$(T "Геолокация запрошена (PID $!)." "Geolocation requested (PID $!).")"
}

# ---------- менеджер пакетов (по среде) ----------
pm_update() {
  case "$TK_ENV" in ish|alpine) apk update ;; termux) pkg update -y ;; debian) apt-get update ;; *) return 0 ;; esac
}
pm_base_pkgs() {
  case "$TK_ENV" in
    ish|alpine) echo "python3 py3-pip curl wget ca-certificates py3-chardet" ;;
    termux) echo "python curl wget" ;;
    debian) echo "python3 python3-pip curl wget ca-certificates python3-chardet" ;;
    fedora) echo "python3 curl wget" ;;
    macos) echo "python3 curl" ;;
    *) echo "" ;;
  esac
}
pm_add() {
  case "$TK_ENV" in
    ish|alpine) apk add --no-cache "$@" ;;
    termux) pkg install -y "$@" ;;
    debian) apt-get install -y "$@" ;;
    fedora) dnf install -y "$@" ;;
    macos) brew install "$@" ;;
    *) return 1 ;;
  esac
}

# ---------- Alpine: репозитории, версии, откат ----------
alp_cur() { cut -d. -f1,2 /etc/alpine-release 2>/dev/null; }
set_repos() {
  _v="$1"
  printf 'https://dl-cdn.alpinelinux.org/alpine/v%s/main\nhttps://dl-cdn.alpinelinux.org/alpine/v%s/community\n' "$_v" "$_v" > /etc/apk/repositories
  apk update >/dev/null 2>&1 && return 0
  for _m in mirror.yandex.ru/mirrors/alpine mirrors.ustc.edu.cn/alpine mirror.leaseweb.com/alpine; do
    printf 'https://%s/v%s/main\nhttps://%s/v%s/community\n' "$_m" "$_v" "$_m" "$_v" > /etc/apk/repositories
    apk update >/dev/null 2>&1 && return 0
  done
  return 1
}
alpine_try() { set_repos "$1" && apk add --no-cache --upgrade python3 py3-pip curl wget ca-certificates py3-chardet >/dev/null 2>&1; }

python_ok() {
  command -v python3 >/dev/null 2>&1 && python3 -c 'import sys; sys.exit(0 if sys.version_info >= (3,8) else 1)' >/dev/null 2>&1
}
# Балл окружения: -1 = Python упал (Bad system call), иначе число проваленных обязательных компонентов
score_env() {
  python_ok || { echo -1; return; }
  python3 "$CORE/tkcore.py" --selftest >/tmp/tk_self.out 2>&1; _rc=$?
  if [ "$_rc" -ge 128 ]; then echo -1; return; fi
  _n="$(grep -c '^FAIL' /tmp/tk_self.out 2>/dev/null)"; echo "${_n:-0}"
}

# Подбор рабочей версии Alpine: стабильная → соседние; запоминаем лучшую; не более 6 попыток
find_alpine() {
  is_apk || { say_wn "$(T 'Смена версии доступна только в Alpine/iSH.' 'Version switching is available only on Alpine/iSH.')"; return 1; }
  _good="$(cat "$CONF/good_alpine" 2>/dev/null)"; _cur="$(alp_cur)"
  _best=""; _bsc=999; _tried=" "; _n=0
  for _v in $_good $_cur 3.18 3.19 3.17 3.20 3.21 3.16; do
    [ -n "$_v" ] || continue
    case "$_tried" in *" $_v "*) continue ;; esac
    _tried="$_tried$_v "; _n=$((_n + 1)); [ "$_n" -gt 6 ] && break
    say_in "$(T "Пробую Alpine $_v ..." "Trying Alpine $_v ...")"
    run_spin "Alpine $_v" alpine_try "$_v" || { say_wn "Alpine $_v: $(T 'не удалось установить' 'install failed')"; continue; }
    _sc="$(score_env)"
    if [ "$_sc" = "0" ]; then
      echo "$_v" > "$CONF/good_alpine"; say_ok "$(T "Alpine $_v работает — всё в порядке." "Alpine $_v works — all good.")"; return 0
    fi
    say_wn "Alpine $_v: $(T 'проблемные компоненты' 'problem components') = $_sc"
    [ "$_sc" -ge 0 ] 2>/dev/null && [ "$_sc" -lt "$_bsc" ] && { _best="$_v"; _bsc="$_sc"; }
  done
  if [ -n "$_best" ]; then
    say_wn "$(T "Идеальной версии нет — выбираю лучшую: $_best" "No perfect version — picking the best: $_best")"
    run_spin "Alpine $_best" alpine_try "$_best"
    grep '^FAIL' /tmp/tk_self.out 2>/dev/null | while read -r _l; do say_wn "$_l"; done
    return 0
  fi
  say_er "$(T 'Не найдено рабочей версии Alpine.' 'No working Alpine version found.')"; return 1
}

# Подготовка окружения: пакеты → самотест → при проблемах подбор Alpine (один раз)
ensure_env() {
  if python_ok; then [ "$(score_env)" = "0" ] && return 0; fi
  _pk="$(pm_base_pkgs)"
  if [ -n "$_pk" ]; then
    say_in "$(T 'Устанавливаю зависимости...' 'Installing dependencies...')"
    run_spin "$(T 'Обновление индекса пакетов' 'Updating package index')" pm_update
    run_spin "$(T 'Установка пакетов' 'Installing packages')" pm_add $_pk || say_wn "$(T 'Часть пакетов не установилась.' 'Some packages failed to install.')"
  fi
  python_ok && [ "$(score_env)" = "0" ] && return 0
  say_wn "$(T 'Окружение нестабильно (Python/компоненты).' 'Environment is unstable (Python/components).')"
  find_alpine || true
  python_ok || { say_er "$(T 'Python недоступен. Установите python3 вручную и запустите снова.' 'Python is unavailable. Install python3 manually and run again.')"; exit 1; }
}

update_pkgs() {
  run_spin "$(T 'Обновление индекса' 'Updating index')" pm_update
  case "$TK_ENV" in
    ish|alpine) run_spin "apk upgrade" apk upgrade ;;
    termux) run_spin "pkg upgrade" pkg upgrade -y ;;
    debian) run_spin "apt upgrade" apt-get upgrade -y ;;
  esac
  say_ok "$(T 'Пакеты обновлены.' 'Packages updated.')"
}

apply_update() {
  _new="$CONF/Toolkit.new"
  if [ -f "$_new" ] && head -1 "$_new" | grep -q '^#!/bin/sh' && grep -q 'TK_BUILD=' "$_new"; then
    _dst="$TK_SELF"; [ -f "$_dst" ] || _dst="$HOME/Toolkit.sh"
    cp "$_new" "$_dst" && chmod 700 "$_dst" && rm -f "$_new" && echo "$_dst" > "$CONF/self_path"
    say_ok "$(T "Обновлено: $_dst — перезапуск..." "Updated: $_dst — restarting...")"
    exec sh "$_dst"
  fi
  say_er "$(T 'Файл обновления повреждён — отмена.' 'Update file is damaged — cancelled.')"
}

# ==========================================================================
#  РАСПАКОВКА МОДУЛЕЙ (пропускается, если версия уже установлена)
# ==========================================================================
SKIP=0
if [ "${TK_FORCE:-0}" != "1" ] && [ -f "$CORE/launcher.py" ] && [ "$(cat "$CORE/.ver" 2>/dev/null)" = "$TK_BUILD" ]; then SKIP=1; fi
tk_put() { if [ "$SKIP" = "1" ]; then cat >/dev/null; else cat > "$CORE/$1"; fi; }

tk_put tkcore.py << 'TKEOF_tkcore'
# -*- coding: utf-8 -*-
# ==========================================================================
#  tkcore — общее ядро Toolkit (iSH, Termux, Linux, macOS)
#  Содержит: настройки + память, цвета/градиенты, рамки, спиннеры, прогресс-бары,
#  безопасный ввод (Backspace!), меню, выбор файлов, сеть (DNS/DoH/прокси/IP),
#  загрузка с fallback-ами, проверка связи, самотест окружения.
#  Совместимость: Python 3.8+ (iSH / Alpine), только stdlib.
# ==========================================================================
import os, sys, re, json, time, shutil, socket, ssl, struct, random, subprocess
import threading, math, builtins, base64, traceback, hashlib
from pathlib import Path
import urllib.request, urllib.error
from urllib.parse import urlparse, quote, unquote

try:
    import readline          # даёт нормальное редактирование строки (Backspace, стрелки)
    HAVE_RL = True
except Exception:
    HAVE_RL = False

TK_VERSION = ""   # версия не показывается; идентификатор сборки задаёт оболочка
HOME = Path(os.environ.get("HOME") or "/root")
BASE = HOME / "Shadowrocket"
CONF = BASE / ".config"
CORE = BASE / ".core"
SETTINGS_FILE = CONF / "settings.json"
CRASH_LOG = CONF / "crash.log"
UA = ("Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 "
      "(KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1")
os.umask(0o077)

# ==========================================================================
#  НАСТРОЙКИ И ПАМЯТЬ (глобальные + по каждому инструменту)
# ==========================================================================
DEFAULTS = {
    "lang": "ru", "theme": "ocean", "anim": True, "anim_speed": 1.0, "spinner": "braille",
    "bar_style": "smooth", "bar_width": 0, "bar_gradient": True, "bar_pct": True,
    "bar_size": True, "bar_speed": True, "bar_eta": True, "color": "256", "unicode": True,
    "confirm_delete": True, "loc_keepalive": True, "launch_anim": True,
    "verbose": False, "max_width": 0, "clear": True, "update_url": "https://raw.githubusercontent.com/Krest-Neva/Shadowrocket/refs/heads/main/Scripts/ISH/Toolkit.py",
}
NET_DEFAULTS = {
    "proxy": "", "dns_mode": "auto", "dns_servers": "1.1.1.1,8.8.8.8,94.140.14.14,9.9.9.9",
    "doh_url": "", "doh_fallback": True, "ip_version": "auto", "verify_tls": True,
    "tls_fallback": "ask", "extra_ca": "", "timeout": 20, "retries": 2, "preflight": True,
}
CHOICES = {"theme": ("ocean", "sunset", "neon", "matrix", "candy", "mono"),
           "spinner": ("braille", "dots", "line", "arc", "pulse", "bounce"),
           "bar_style": ("smooth", "blocks", "bars", "dots", "arrows", "ascii"),
           "color": ("256", "16", "off"), "lang": ("ru", "en"),
           "dns_mode": ("auto", "system", "udp", "doh"), "ip_version": ("auto", "ipv4", "ipv6"),
           "tls_fallback": ("ask", "auto", "never")}


class Store:
    """JSON-хранилище настроек. Запись атомарная, значения проверяются по типу."""
    def __init__(self):
        self.d = {}
        self.load()

    def load(self):
        try:
            self.d = json.loads(SETTINGS_FILE.read_text("utf-8"))
        except Exception:
            self.d = {}
        if not isinstance(self.d, dict):
            self.d = {}
        if "lang" not in self.d:                      # язык, выбранный оболочкой при первом запуске
            try:
                v = (CONF / "lang").read_text().strip()
                if v in ("ru", "en"):
                    self.d["lang"] = v
            except Exception:
                pass

    def save(self):
        try:
            CONF.mkdir(parents=True, exist_ok=True)
            tmp = SETTINGS_FILE.with_suffix(".tmp")
            tmp.write_text(json.dumps(self.d, ensure_ascii=False, indent=1), "utf-8")
            os.replace(str(tmp), str(SETTINGS_FILE))
        except Exception:
            pass

    @staticmethod
    def _ok(v, dv, key=None):
        if type(v) is not type(dv) and not (isinstance(dv, float) and isinstance(v, int)):
            return False
        return not (key in CHOICES and v not in CHOICES[key])

    def g(self, k):
        v = self.d.get(k, DEFAULTS[k])
        return v if self._ok(v, DEFAULTS[k], k) else DEFAULTS[k]

    def set(self, k, v):
        self.d[k] = v
        self.save()

    def net(self, k):
        v = self.d.get("net", {}).get(k, NET_DEFAULTS[k])
        return v if self._ok(v, NET_DEFAULTS[k], k) else NET_DEFAULTS[k]

    def setnet(self, k, v):
        self.d.setdefault("net", {})[k] = v
        self.save()

    def mem(self, tool, k, default=None):
        return self.d.get("mem", {}).get(tool, {}).get(k, default)

    def setmem(self, tool, k, v):
        self.d.setdefault("mem", {}).setdefault(tool, {})[k] = v
        self.save()

    def clear_mem(self, tool=None):
        if tool:
            self.d.get("mem", {}).pop(tool, None)
        else:
            self.d["mem"] = {}
        self.save()


ST = Store()


def L(ru, en):
    """Мини-локализация: возвращает строку на выбранном языке."""
    return ru if ST.g("lang") == "ru" else en


# ==========================================================================
#  ЦВЕТА, ГРАДИЕНТЫ, ПАЛИТРЫ
# ==========================================================================
RESET, BOLD, DIM = "\033[0m", "\033[1m", "\033[2m"
PALETTES = {
    "ocean": [27, 33, 39, 45, 51, 50, 49, 48, 84, 120],
    "sunset": [196, 202, 208, 214, 220, 226, 190, 154],
    "neon": [201, 165, 129, 93, 57, 27, 33, 39, 45, 51],
    "matrix": [22, 28, 34, 40, 46, 82, 118, 154, 190],
    "candy": [213, 207, 201, 165, 171, 177, 183, 189, 195],
    "mono": [244, 247, 250, 253, 255, 253, 250, 247],
}
OK_C, ERR_C, WARN_C, INFO_C, ASK_C = 84, 203, 220, 51, 213


def color_mode():
    if not sys.stdout.isatty() and not os.environ.get("TK_FORCE_COLOR"):
        return "off"
    if os.environ.get("NO_COLOR"):
        return "off"
    return ST.g("color")


def fg(n):
    m = color_mode()
    if m == "off":
        return ""
    if m == "256":
        return "\033[38;5;%dm" % n
    if n < 16:
        return "\033[%dm" % (30 + n if n < 8 else 82 + n)
    n -= 16
    r, g, b = n // 36, n % 36 // 6, n % 6
    code = (1 if r > 2 else 0) | (2 if g > 2 else 0) | (4 if b > 2 else 0)
    return "\033[%dm" % (90 + code if max(r, g, b) > 3 else 30 + code)


def pal():
    return PALETTES.get(ST.g("theme"), PALETTES["ocean"])


def accent():
    p = pal()
    return p[len(p) // 2]


def c(text, n, bold=False):
    """Окрасить текст цветом n (0-255)."""
    if color_mode() == "off":
        return str(text)
    return (BOLD if bold else "") + fg(n) + str(text) + RESET


def dim(text):
    return str(text) if color_mode() == "off" else DIM + str(text) + RESET


def bold(text):
    return str(text) if color_mode() == "off" else BOLD + str(text) + RESET


def grad(text, shift=0, bold_=False):
    """Градиент по палитре темы. shift — сдвиг для анимации (блик)."""
    if color_mode() == "off":
        return str(text)
    p, n, out = pal(), max(1, len(text) - 1), []
    for i, ch in enumerate(str(text)):
        if ch == " ":
            out.append(ch)
            continue
        idx = (int(round(i / n * (len(p) - 1))) + shift) % len(p)
        out.append((BOLD if bold_ else "") + fg(p[idx]) + ch)
    return "".join(out) + RESET


ANSI_RE = re.compile(r"\x1b(?:\[[0-9;?]*[ -/]*[@-~]|[@-Z\\-_]|O[A-Za-z])")


def vlen(s):
    """Видимая длина строки (без ANSI, эмодзи считаются как 2)."""
    s = ANSI_RE.sub("", str(s))
    n = 0
    for ch in s:
        o = ord(ch)
        if o >= 0x1F000 or 0x2600 <= o <= 0x27BF and ch not in "✔✘✓✗✦✧★☆▶▷●○◆◇":
            n += 2
        elif o in (0x200B, 0xFE0F):
            continue
        else:
            n += 1
    return n


def term_w(lo=30, hi=78):
    """Ширина вывода: ширина терминала, ограниченная настройкой max_width (0 = авто)."""
    try:
        w = shutil.get_terminal_size((44, 24)).columns
    except Exception:
        w = 44
    r = max(lo, min(hi, w - 1))
    mw = ST.g("max_width")
    return max(lo, min(r, mw)) if mw else r


def clear_screen():
    """Очистить экран (настройка clear) — аккуратный вывод без «мусора»."""
    if sys.stdout.isatty() and ST.g("clear"):
        sys.stdout.write("\033[2J\033[3J\033[H")
        sys.stdout.flush()


def U(a, b):
    """Юникод-символ или ASCII-замена (настройка unicode)."""
    return a if ST.g("unicode") else b


# ==========================================================================
#  ВЫВОД: раскрашивающий print, рамки, заголовки, таблицы
# ==========================================================================
_OUT = threading.RLock()
_TAG = re.compile(r"^(\s*)(\[[+!*?x]\])(\s?)(.*)$", re.S)
_MENU = re.compile(r"^(\s*)(\d{1,3}|[a-zA-Z])(\s*[-.)]\s+)(.*)$")
_RULE = re.compile(r"^[\s=\-─━_*~·.]{6,}$")
_ERRW = re.compile(r"(ошибк|error|fail|не удалось|не найден|traceback|invalid|неверн|denied|refused)", re.I)


def paint_line(s):
    """Автоматическая раскраска строки по её виду ([+] [!] [*] [?], меню, разделители)."""
    if color_mode() == "off" or "\033" in s:
        return s
    st = s.strip()
    if not st:
        return s
    if _RULE.match(st):
        return grad(s)
    if st.startswith("===") and st.rstrip().endswith("==="):
        return c(s, accent(), True)
    m = _TAG.match(s)
    if m:
        ind, tag, sp, rest = m.groups()
        col = {"+": OK_C, "*": INFO_C, "?": ASK_C, "x": ERR_C}.get(tag[1])
        if tag == "[!]":
            col = ERR_C if _ERRW.search(rest) else WARN_C
        return ind + c(tag, col, True) + sp + c(rest, col)
    m = _MENU.match(s)
    if m:
        ind, num, sep, rest = m.groups()
        return ind + c(num, accent(), True) + dim(sep) + rest
    return s


def tprint(*args, sep=" ", end="\n", file=None, flush=False):
    if file is not None and file is not sys.stdout:
        return builtins.print(*args, sep=sep, end=end, file=file, flush=flush)
    text = sep.join(str(a) for a in args)
    with _OUT:
        sys.stdout.write("\n".join(paint_line(x) for x in text.split("\n")) + end)
        if flush or end == "":
            sys.stdout.flush()


print = tprint   # экспортируется всем инструментам (from tkcore import *)


def box(lines, title=None, w=None, col=None):
    """Рамка со скруглёнными углами и градиентной окантовкой."""
    w = w or term_w()
    tl, tr_, bl, br, h, v = (U("╭", "+"), U("╮", "+"), U("╰", "+"), U("╯", "+"), U("─", "-"), U("│", "|"))
    inner = w - 2
    top = h * inner
    if title:
        t = " " + title + " "
        top = h + t + h * max(0, inner - vlen(t) - 1)
    out = [grad(tl + top + tr_, 0)]
    for ln_ in lines:
        pad = max(0, inner - vlen(ln_) - 1)
        out.append(c(v, pal()[0]) + " " + ln_ + " " * pad + c(v, pal()[-1]))
    out.append(grad(bl + h * inner + br, 3))
    return "\n".join(out)


def hdr(title, sub=None):
    """Заголовок раздела: рамка + градиентный текст."""
    w = term_w()
    star = U("✦ ", "* ")
    lines = [grad(star + str(title), 0, True)]
    if sub:
        lines.append(dim(str(sub)))
    print("\n" + box(lines, None, w))


def ln(ch=None):
    print(grad((ch or U("─", "-")) * term_w()))


def trunc(s, n):
    s = str(s)
    return s if vlen(s) <= n else s[:max(1, n - 1)] + U("…", ".")


def fmt_size(n):
    try:
        n = float(n)
    except Exception:
        return "?"
    for u in ("B", "KiB", "MiB", "GiB", "TiB"):
        if n < 1024 or u == "TiB":
            return ("%d %s" % (n, u)) if u == "B" else ("%.1f %s" % (n, u))
        n /= 1024.0


def fmt_dur(sec):
    try:
        sec = int(sec)
    except Exception:
        return "--:--"
    h, r = divmod(max(0, sec), 3600)
    m, s = divmod(r, 60)
    return "%d:%02d:%02d" % (h, m, s) if h else "%d:%02d" % (m, s)


def now_stamp():
    return time.strftime("%Y%m%d_%H%M%S")


def table(rows, heads=None, widths=None):
    """Простая таблица с цветной шапкой. rows — список списков строк."""
    allr = ([heads] if heads else []) + rows
    cols = len(allr[0]) if allr else 0
    if not widths:
        widths = [max(vlen(r[i]) for r in allr) for i in range(cols)]
    total = sum(widths) + 2 * cols
    mx = term_w()
    if total > mx:
        k = (mx - 2 * cols) / float(sum(widths))
        widths = [max(4, int(w * k)) for w in widths]
    def fmt(r, hd=False):
        cells = []
        for i, x in enumerate(r):
            x = trunc(x, widths[i])
            cells.append(x + " " * (widths[i] - vlen(x)))
        s = "  ".join(cells)
        return c(s, accent(), True) if hd else s
    if heads:
        print(fmt(heads, True))
        ln()
    for r in rows:
        print(fmt(r))


# ==========================================================================
#  СПИННЕРЫ (анимация, когда нет прогресс-бара)
# ==========================================================================
SPIN = {"braille": "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏", "dots": "⣾⣽⣻⢿⡿⣟⣯⣷", "line": "|/-\\", "arc": "◜◠◝◞◡◟",
        "pulse": "▏▎▍▌▋▊▉█▉▊▋▌▍▎", "bounce": "⠁⠂⠄⡀⢀⠠⠐⠈"}


class Spin:
    """Спиннер в отдельном потоке: Spin('Загрузка') как контекстный менеджер."""
    def __init__(self, msg, quiet_ok=False):
        self.msg, self.t0, self._stop, self.th, self.quiet_ok = msg, time.time(), False, None, quiet_ok
        self.live = sys.stdout.isatty() and ST.g("anim")
        self.ok, self.final = True, None

    def update(self, msg):
        self.msg = msg

    def _run(self):
        frames = SPIN.get(ST.g("spinner"), SPIN["braille"]) if ST.g("unicode") else "|/-\\"
        i, p = 0, pal()
        while not self._stop:
            el = time.time() - self.t0
            line = "\r\033[K %s %s %s" % (c(frames[i % len(frames)], p[i % len(p)], True), self.msg, dim("%.0fs" % el))
            with _OUT:
                sys.stdout.write(trunc_vis(line, term_w() + 12))
                sys.stdout.flush()
            i += 1
            time.sleep(0.08 / max(0.3, float(ST.g("anim_speed"))))

    def __enter__(self):
        if self.live:
            self.th = threading.Thread(target=self._run, daemon=True)
            self.th.start()
        else:
            print("[*] %s..." % self.msg)
        return self

    def __exit__(self, et, ev, tb):
        self._stop = True
        if self.th:
            self.th.join(0.5)
            with _OUT:
                sys.stdout.write("\r\033[K")
        if et is not None:
            self.ok = False
        if self.final is not False and not self.quiet_ok:
            el = time.time() - self.t0
            if self.ok:
                print("[+] %s %s" % (self.final or self.msg, dim("(%.1fs)" % el)))
            else:
                print("[!] %s %s" % (self.final or self.msg, dim("(%.1fs)" % el)))
        return False


def trunc_vis(s, n):
    return s


def spin(msg, **kw):
    return Spin(msg, **kw)


# ==========================================================================
#  ПРОГРЕСС-БАР (проценты, объём, скорость, ETA; стиль и длина настраиваются)
# ==========================================================================
BAR_STYLES = {"smooth": None, "blocks": ("█", "░"), "bars": ("▰", "▱"), "dots": ("●", "○"),
              "arrows": ("▶", "·"), "ascii": ("#", "-")}
PARTIAL = " ▏▎▍▌▋▊▉"


class Bar:
    """Прогресс-бар. total=None — неопределённый режим. unit: 'B' (байты), '' (штуки), 's' (секунды)."""
    def __init__(self, total=None, label="", unit="", width=None):
        self.total, self.label, self.unit = total, label, unit
        self.cur, self.t0, self.last, self.speed, self.lc, self.lt = 0, time.time(), 0.0, 0.0, 0, time.time()
        self.width_cfg = width
        self.live = sys.stdout.isatty() and ST.g("anim")
        self.nl_step = 0
        self.closed = False

    def _fmt(self, v):
        if self.unit == "B":
            return fmt_size(v)
        if self.unit == "s":
            return fmt_dur(v)
        return "%d" % v

    def update(self, cur=None, add=None, total=None):
        if total is not None:
            self.total = total
        self.cur = cur if cur is not None else self.cur + (add or 0)
        now = time.time()
        dt = now - self.lt
        if dt >= 0.25:                                    # сглаженная скорость (EMA)
            inst = (self.cur - self.lc) / dt
            self.speed = inst if self.speed == 0 else self.speed * 0.6 + inst * 0.4
            self.lc, self.lt = self.cur, now
        if now - self.last >= 0.08 or (self.total and self.cur >= self.total):
            self.last = now
            self.render()

    def _cells(self, w, frac):
        st = ST.g("bar_style")
        if self.total is None:                            # неопределённый режим: бегущий блок
            pos = int((time.time() * 8) % (w * 2 - 2))
            pos = pos if pos < w else 2 * w - 2 - pos
            return "".join(c(U("█", "#"), pal()[(i * len(pal())) // w], False) if abs(i - pos) < 3 else dim(U("░", "-")) for i in range(w))
        if not ST.g("unicode"):
            st = "ascii"
        if st == "smooth":
            full = int(frac * w)
            rem = int((frac * w - full) * 8)
            cells = []
            for i in range(w):
                if i < full:
                    cells.append("█")
                elif i == full and rem > 0:
                    cells.append(PARTIAL[rem])
                else:
                    cells.append("░")
        else:
            on, off = BAR_STYLES.get(st, BAR_STYLES["blocks"])
            full = int(round(frac * w))
            cells = [on if i < full else off for i in range(w)]
        p, out = pal(), []
        for i, ch in enumerate(cells):
            if ch in ("░", "·", "▱", "○", "-"):
                out.append(dim(ch))
            elif ST.g("bar_gradient"):
                out.append(c(ch, p[min(len(p) - 1, int(i / max(1, w - 1) * (len(p) - 1)))]))
            else:
                out.append(c(ch, accent()))
        return "".join(out)

    def render(self, final=False):
        frac = 1.0 if final else (min(1.0, self.cur / float(self.total)) if self.total else 0.0)
        parts = []
        if ST.g("bar_pct") and self.total:
            parts.append(c("%5.1f%%" % (frac * 100), accent(), True))
        if ST.g("bar_size"):
            parts.append("%s/%s" % (self._fmt(self.cur), self._fmt(self.total)) if self.total else self._fmt(self.cur))
        if ST.g("bar_speed") and self.unit == "B" and self.speed > 0:
            parts.append(c(fmt_size(self.speed) + "/s", INFO_C))
        if ST.g("bar_eta") and self.total and self.speed > 0 and not final:
            parts.append(dim("ETA " + fmt_dur((self.total - self.cur) / self.speed)))
        if final:
            parts.append(dim(fmt_dur(time.time() - self.t0)))
        lab = trunc(self.label, 14) + " " if self.label else ""
        while True:                                       # на узком экране отбрасываем ETA → скорость → ...
            tail = " ".join(parts)
            avail = term_w(24, 100) - vlen(lab) - vlen(tail) - 4
            if avail >= 10 or len(parts) <= 1:
                break
            parts.pop(-2 if final and len(parts) > 2 else -1)
        w = self.width_cfg or ST.g("bar_width") or max(8, min(40, avail))
        w = max(6, min(w, max(6, avail))) if avail >= 6 else 6
        caps = (U("▕", "["), U("▏", "]"))
        line = "%s%s%s%s %s" % (lab, caps[0], self._cells(w, frac), caps[1], tail)
        if self.live:
            with _OUT:
                sys.stdout.write("\r\033[K " + line)
                sys.stdout.flush()
        else:
            pct = int(frac * 10)
            if pct > self.nl_step or final:
                self.nl_step = pct
                print(" " + ANSI_RE.sub("", line))

    def close(self, ok=True):
        if self.closed:
            return
        self.closed = True
        if self.total and self.cur < self.total and ok:
            self.cur = self.total
        self.render(final=True)
        if self.live:
            sys.stdout.write("\n")
            sys.stdout.flush()


def track(it, total=None, label="", unit=""):
    """for x in track(items, label='...'): — итерация с прогресс-баром."""
    try:
        total = total if total is not None else len(it)
    except Exception:
        total = None
    b = Bar(total, label, unit)
    for i, x in enumerate(it, 1):
        yield x
        b.update(i)
    b.close()


# ==========================================================================
#  ВВОД: безопасный (Backspace/стрелки/ANSI), подтверждения, мульти-выбор
# ==========================================================================
class Quit(Exception):
    """Выход из инструмента (пользователь ввёл q / Ctrl+C / EOF)."""


def fix_tty():
    """Сделать ERASE = 0x7f (iSH шлёт DEL при Backspace) и отключить bracketed paste."""
    try:
        import termios
        fd = sys.stdin.fileno()
        a = termios.tcgetattr(fd)
        a[6][termios.VERASE] = b"\x7f"
        termios.tcsetattr(fd, termios.TCSANOW, a)
    except Exception:
        pass
    if HAVE_RL:
        try:
            readline.parse_and_bind("set enable-bracketed-paste off")
        except Exception:
            pass


def clean_line(s):
    """Корректно применить Backspace (\\x7f, \\x08), убрать ANSI/управляющие символы."""
    if s is None:
        return ""
    s = ANSI_RE.sub("", s)
    out = []
    for ch in s:
        if ch in ("\x7f", "\x08"):
            if out:
                out.pop()
        elif ch in ("\r", "\n"):
            continue
        elif ch == "\t" or ord(ch) >= 32:
            out.append(ch)
    return "".join(out).strip()


def _rl(s):
    """Обернуть ANSI-последовательности в \\001..\\002, чтобы readline считал ширину верно."""
    return re.sub(r"(\x1b\[[0-9;]*m)", "\x01\\1\x02", s) if HAVE_RL else s


def ask(label, default="", quit_ok=True, hint=None):
    """Запрос строки. 'q' → Quit (если quit_ok). Enter → default."""
    d = (" " + dim("[%s]" % default)) if default not in ("", None) else ""
    h = (" " + dim(hint)) if hint else ""
    prompt = "%s %s%s%s%s " % (c(U("❯", ">"), accent(), True), label, h, d, c(":", accent()))
    try:
        sys.stdout.flush()
        v = clean_line(input(_rl(prompt)))
    except EOFError:
        raise Quit()
    except KeyboardInterrupt:
        print()
        raise Quit()
    if quit_ok and v.lower() in ("q", "quit", "exit"):
        raise Quit()
    return v if v != "" else (default if default is not None else "")


def confirm(q, default=False):
    v = ask("%s %s" % (q, dim("(y/n)")), "y" if default else "n", quit_ok=False).lower()
    return v in ("y", "yes", "д", "да", "1")


def pause(msg=None):
    try:
        input(_rl(dim(msg or L("Enter — продолжить...", "Press Enter to continue..."))) + " ")
    except (EOFError, KeyboardInterrupt):
        print()


def parse_multi(text, n):
    """'1,3-5' / 'all' / 'a' → список номеров 1..n. Бросает ValueError при мусоре."""
    t = (text or "").strip().lower()
    if t in ("all", "a", "*", "все"):
        return list(range(1, n + 1))
    res = []
    for part in [p.strip() for p in t.split(",") if p.strip()]:
        if "-" in part:
            a, b = part.split("-", 1)
            if not (a.strip().isdigit() and b.strip().isdigit()):
                raise ValueError(part)
            a, b = sorted((int(a), int(b)))
            res += [x for x in range(a, b + 1) if 1 <= x <= n and x not in res]
        else:
            if not part.isdigit():
                raise ValueError(part)
            x = int(part)
            if 1 <= x <= n and x not in res:
                res.append(x)
    if not res:
        raise ValueError(text)
    return res


def ask_multi(label, n, default=""):
    while True:
        v = ask(label, default, quit_ok=True, hint="1,3-5 / all")
        if v.lower() in ("b", "back", "") and default == "":
            return None
        try:
            return parse_multi(v, n)
        except ValueError:
            print("[!] " + L("Неверный ввод. Пример: 1,3-5 или all", "Bad input. Example: 1,3-5 or all"))


def menu(title, items, tool=None, sub=None, back_label=None, show=True, clear_ok=True):
    """Цветное меню. items: [(key,label,desc)]. Возвращает ключ ('q' при выходе)."""
    if show:
        if clear_ok:
            clear_screen()
        hdr(title, sub)
    for k, lab, desc in items:
        if k == "--":                                           # заголовок группы
            print("\n " + c(U("━━ ", "-- ") + lab + " " + U("━" * max(2, term_w() - vlen(lab) - 8), "-" * 6), pal()[len(pal()) // 2], True))
            continue
        row = " %s %s %s" % (c("%2s" % k, accent(), True), c(U("┃", "|"), pal()[0]), bold(lab))
        if desc:
            row += "  " + dim(trunc(desc, max(8, term_w() - vlen(lab) - 9)))
        print(row)
    print(" %s %s %s" % (c(" q", ERR_C, True), c(U("┃", "|"), pal()[0]), dim(back_label or L("Назад / выход", "Back / exit"))))
    keys = [str(k).lower() for k, _, _ in items if k != "--"]
    last = ST.mem(tool, "_menu_" + title) if tool else None
    while True:
        try:
            v = ask(L("Выбор", "Choice"), "", quit_ok=False, hint=("(last: %s)" % last) if last else None).lower()
        except Quit:
            return "q"
        if v in ("q", "quit", "exit", "b", "back", "0") and "0" not in keys:
            return "q"
        if v in keys:
            if tool:
                ST.setmem(tool, "_menu_" + title, v)
            return v
        print("[!] " + L("Неверный выбор", "Invalid choice"))


# ==========================================================================
#  АНИМАЦИИ: запуск, баннер, фейерверк
# ==========================================================================
def banner(animate=True):
    w = term_w(30, 56)
    title = "T O O L K I T"
    sub = "N E T   &   T R A F F I C   L A B"
    anim = animate and sys.stdout.isatty() and ST.g("anim")
    frames = 16 if anim else 1
    sp = max(0.3, float(ST.g("anim_speed")))
    for f in range(frames):
        lines = [" " * max(0, (w - 4 - vlen(title)) // 2) + grad(title, f, True),
                 " " * max(0, (w - 4 - vlen(sub)) // 2) + grad(sub, -f)]
        stars = "".join(random.choice(["  ", " ✦", " ·", "  ", " ✧"]) if ST.g("unicode") else random.choice(["  ", " *", " ."]) for _ in range(w // 2 - 1))
        lines.append(dim(stars[:w - 4]))
        out = box(lines, None, w)
        if anim and f > 0:
            sys.stdout.write("\033[%dA" % (len(lines) + 2))
        sys.stdout.write(out + "\n")
        sys.stdout.flush()
        if anim:
            time.sleep(0.05 / sp)


def rocket_launch():
    if not (sys.stdout.isatty() and ST.g("anim") and ST.g("launch_anim") and ST.g("unicode")):
        return
    w = term_w(30, 50)
    sp = max(0.3, float(ST.g("anim_speed")))
    p = pal()
    for i in range(0, w - 4, 2):
        trail = "".join(c("~", p[(j + i) % len(p)]) for j in range(max(0, min(i, 8))))
        sys.stdout.write("\r\033[K" + " " * max(0, i - 8) + trail + "🚀")
        sys.stdout.flush()
        time.sleep(0.02 / sp)
    sys.stdout.write("\r\033[K")
    sys.stdout.flush()


# ==========================================================================
#  ФАЙЛЫ: безопасные операции, выбор файлов, переименование/очистка
# ==========================================================================
def atomic_write(path, data, mode="w"):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    if "b" in mode:
        tmp.write_bytes(data)
    else:
        tmp.write_text(data, "utf-8")
    os.replace(str(tmp), str(path))


def sanitize_filename(name):
    s = re.sub(r"[^\w.\-]", "_", clean_line(name), flags=re.U).strip("._")
    return s or "file"


def list_files(d, exts=None):
    """Файлы каталога (без скрытых). Устойчиво к «битым» именам."""
    out = []
    try:
        for e in os.scandir(str(d)):
            try:
                if e.is_file() and not e.name.startswith("."):
                    if not exts or Path(e.name).suffix.lower() in exts:
                        out.append(Path(e.path))
            except OSError:
                continue
    except OSError:
        return []
    return sorted(out, key=lambda p: p.name.lower())


def show_files(files):
    for i, f in enumerate(files, 1):
        try:
            st = f.stat()
            info = "%s  %s" % (fmt_size(st.st_size), time.strftime("%m-%d %H:%M", time.localtime(st.st_mtime)))
        except OSError:
            info = "?"
        print("  %s %s  %s" % (c("%2d" % i, accent(), True), trunc(f.name, term_w() - 28), dim(info)))


def pick_files(d, exts=None, multi=True, title=None, tool=None):
    """Выбор файлов из каталога. Возвращает список Path или None (назад)."""
    d = Path(d)
    d.mkdir(parents=True, exist_ok=True)
    while True:
        files = list_files(d, exts)
        if not files:
            print("[!] " + L("Папка пуста: ", "Folder is empty: ") + str(d))
            print("[*] " + L("Положите файлы в неё и нажмите Enter (b — назад).", "Put files there and press Enter (b = back)."))
            if ask("", "", quit_ok=True).lower() in ("b", "back"):
                return None
            continue
        print("\n" + c(title or L("Файлы", "Files"), accent(), True) + dim("  " + str(d)))
        show_files(files)
        last = ST.mem(tool, "last_pick_" + d.name, "") if tool else ""
        v = ask(L("Номера", "Numbers") if multi else L("Номер", "Number"), "", hint="1,3-5 / all / b" if multi else "b")
        if v.lower() in ("b", "back"):
            return None
        if v.lower() == "r" or not v:
            continue
        try:
            nums = parse_multi(v, len(files))
        except ValueError:
            print("[!] " + L("Неверный ввод", "Bad input"))
            continue
        if not multi:
            nums = nums[:1]
        return [files[i - 1] for i in nums]


def rm_tree(p):
    """Надёжное удаление файла/папки (в т.ч. с битыми правами/именами)."""
    p = str(p)
    try:
        if os.path.islink(p) or os.path.isfile(p):
            os.unlink(p)
        else:
            shutil.rmtree(p)
        return True
    except Exception:
        pass
    try:
        subprocess.run(["chmod", "-R", "u+rwx", p], capture_output=True, timeout=60)
        subprocess.run(["rm", "-rf", "--", p], capture_output=True, timeout=300)
        return not os.path.lexists(p)
    except Exception:
        return False


def files_menu(tool, input_dir, output_dir, exts=None):
    """Общее меню: переименование файлов Input, очистка папок, поиск «битых» имён."""
    while True:
        k = menu(L("Файлы и очистка", "Files & cleanup"), [
            ("1", L("Переименовать файл", "Rename a file"), ""), ("2", L("Переименовать группой (префикс-N)", "Bulk rename (prefix-N)"), ""),
            ("3", L("Очистить Input", "Clean Input"), ""), ("4", L("Очистить Output", "Clean Output"), ""),
            ("5", L("Найти файлы с «битыми» именами", "Find files with bad names"), ""),
            ("6", L("Открыть файловый менеджер здесь", "Open file manager here"), "")], tool=tool)
        if k == "q":
            return
        if k in ("1", "2"):
            fs = pick_files(input_dir, exts, multi=(k == "2"), title=L("Что переименовать", "What to rename"))
            if not fs:
                continue
            if k == "1":
                nn = ask(L("Новое имя", "New name"), fs[0].name, quit_ok=False)
                nn = sanitize_filename(nn) if nn else ""
                if nn and not Path(nn).suffix:
                    nn += fs[0].suffix
                if nn and not (fs[0].parent / nn).exists():
                    fs[0].rename(fs[0].parent / nn)
                    print("[+] " + L("Переименовано: ", "Renamed: ") + nn)
                else:
                    print("[!] " + L("Имя пустое или занято", "Name empty or taken"))
            else:
                pre = sanitize_filename(ask(L("Префикс", "Prefix"), "", quit_ok=False))
                for i, f in enumerate(fs, 1):
                    nf = f.parent / ("%s-%d%s" % (pre, i, f.suffix))
                    if not nf.exists():
                        f.rename(nf)
                        print("[+] %s -> %s" % (f.name, nf.name))
        elif k in ("3", "4"):
            d = Path(input_dir if k == "3" else output_dir)
            if confirm(L("Удалить всё содержимое %s?" % d, "Delete everything in %s?" % d)):
                n = 0
                for e in list(os.scandir(str(d))):
                    n += 1 if rm_tree(e.path) else 0
                print("[+] " + L("Удалено объектов: %d" % n, "Objects removed: %d" % n))
        elif k == "5":
            bad = []
            for d in (input_dir, output_dir):
                for e in os.scandir(str(d)):
                    if re.search(r"[^\w.\-]", e.name, re.U) and not re.fullmatch(r"[\w.\- ]+", e.name, re.U):
                        bad.append(Path(e.path))
            if not bad:
                print("[+] " + L("Подозрительных имён нет", "No suspicious names"))
            for i, p in enumerate(bad, 1):
                print("  %d. %s" % (i, repr(p.name)))
            if bad and confirm(L("Удалить их все?", "Delete all of them?")):
                print("[+] %d" % sum(1 for p in bad if rm_tree(p)))
        elif k == "6":
            run_sibling("filemgr.py", [str(input_dir)])


def run_sibling(script, args=()):
    """Запустить другой модуль toolkit в том же интерпретаторе (как отдельный процесс)."""
    try:
        subprocess.call([sys.executable, str(CORE / script)] + list(args))
    except Exception as e:
        print("[!] %s" % e)


def clip_copy(text):
    """Скопировать в буфер iOS через /dev/clipboard (если доступно в iSH)."""
    try:
        if os.path.exists("/dev/clipboard"):
            with open("/dev/clipboard", "w") as f:
                f.write(text)
            return True
    except Exception:
        pass
    return False


def smart_read(path):
    """Прочитать текстовый файл с подбором кодировки (utf-8/cp1251/koi8-r...)."""
    raw = Path(path).read_bytes()
    for enc in ("utf-8-sig", "utf-8", "cp1251", "koi8-r", "cp866", "latin-1"):
        try:
            return raw.decode(enc)
        except Exception:
            continue
    return raw.decode("utf-8", "replace")


# ==========================================================================
#  СЕТЬ: DNS (system/udp/DoH), IP-версия, прокси, TLS
# ==========================================================================
DNS_CACHE = {}
DNS_TTL = 90
_orig_gai = socket.getaddrinfo


def is_ip(h):
    for fam in (socket.AF_INET, socket.AF_INET6):
        try:
            socket.inet_pton(fam, h)
            return True
        except (OSError, ValueError):
            pass
    return False


def dns_servers():
    return [s.strip() for s in ST.net("dns_servers").split(",") if s.strip()]


DOH_FALLBACK = ["https://1.1.1.1/dns-query", "https://8.8.8.8/dns-query", "https://9.9.9.9/dns-query",
                "https://dns.quad9.net/dns-query", "https://cloudflare-dns.com/dns-query"]


def doh_urls():
    urls = [u.strip() for u in ST.net("doh_url").split(",") if u.strip()]
    if ST.net("doh_fallback"):
        urls += DOH_FALLBACK
    return list(dict.fromkeys(urls))


def qtypes():
    return {"ipv4": [1], "ipv6": [28]}.get(ST.net("ip_version"), [1, 28])


def build_query(host, qt=1):
    tid = random.randint(0, 65535)
    name = b"".join(bytes([len(p)]) + p.encode("idna") for p in host.rstrip(".").split("."))
    return tid, struct.pack(">HHHHHH", tid, 0x0100, 1, 0, 0, 0) + name + b"\x00" + struct.pack(">HH", qt, 1)


def parse_response(data, tid, qt=1):
    if len(data) < 12:
        return []
    rid, flags, qd, an = struct.unpack(">HHHH", data[:8])
    if rid != tid or flags & 0x000F:
        return []

    def skip(p):
        while True:
            if p >= len(data):
                raise ValueError("trunc")
            n = data[p]
            if n == 0:
                return p + 1
            if n & 0xC0 == 0xC0:
                return p + 2
            p += n + 1
    pos, ips = 12, []
    try:
        for _ in range(qd):
            pos = skip(pos) + 4
        for _ in range(an):
            pos = skip(pos)
            rt, rc, ttl, rl = struct.unpack(">HHIH", data[pos:pos + 10])
            pos += 10
            if qt == 1 and rt == 1 and rl == 4:
                ips.append(socket.inet_ntoa(data[pos:pos + 4]))
            elif qt == 28 and rt == 28 and rl == 16:
                ips.append(socket.inet_ntop(socket.AF_INET6, data[pos:pos + 16]))
            pos += rl
    except Exception:
        pass
    return ips


def udp_query(server, host, qt=1, timeout=3):
    """DNS по UDP/53. Возвращает (ips, ошибка)."""
    try:
        tid, pkt = build_query(host, qt)
        s = socket.socket(socket.AF_INET6 if ":" in server else socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(timeout)
        try:
            s.sendto(pkt, (server, 53))
            data, _ = s.recvfrom(4096)
            return parse_response(data, tid, qt), ""
        finally:
            s.close()
    except Exception as e:
        return [], "%s: %s" % (type(e).__name__, e)


def doh_query(url, host, qt=1, timeout=8):
    """DNS-over-HTTPS (JSON API). Исключение при ошибке."""
    op = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    sep = "&" if "?" in url else "?"
    req = urllib.request.Request("%s%sname=%s&type=%s" % (url, sep, host, "A" if qt == 1 else "AAAA"),
                                 headers={"accept": "application/dns-json", "user-agent": UA})
    with op.open(req, timeout=timeout) as r:
        d = json.loads(r.read().decode("utf-8", "replace"))
    return [a["data"] for a in d.get("Answer", []) if a.get("type") == (1 if qt == 1 else 28)]


def resolve(host, mode):
    """Разрешить имя выбранным способом: system / udp / doh."""
    fam = {"ipv4": socket.AF_INET, "ipv6": socket.AF_INET6}.get(ST.net("ip_version"), 0)
    if mode == "system":
        try:
            return list(dict.fromkeys(r[4][0] for r in _orig_gai(host, 443, fam, socket.SOCK_STREAM)))
        except Exception:
            return []
    res = []
    if mode == "udp":
        for srv in dns_servers():
            for qt in qtypes():
                res += udp_query(srv, host, qt)[0]
            if res:
                break
    elif mode == "doh":
        for u in doh_urls():
            for qt in qtypes():
                try:
                    res += doh_query(u, host, qt)
                except Exception:
                    pass
            if res:
                break
    return list(dict.fromkeys(res))


def dns_order():
    return {"auto": ["system", "udp", "doh"], "system": ["system"],
            "udp": ["udp", "doh", "system"], "doh": ["doh", "udp", "system"]}[ST.net("dns_mode")]


_in_doh = threading.local()


def patched_gai(host, port, family=0, type=0, proto=0, flags=0):
    """Подменённый getaddrinfo: несколько способов DNS + выбор IPv4/IPv6."""
    if (not isinstance(host, str) or not host or host == "localhost" or is_ip(host)
            or (ST.net("dns_mode") == "system" and ST.net("ip_version") == "auto")
            or getattr(_in_doh, "busy", False)):
        return _orig_gai(host, port, family, type, proto, flags)
    ipv = ST.net("ip_version")
    fam = {"ipv4": socket.AF_INET, "ipv6": socket.AF_INET6}.get(ipv, family)
    ips = cache_get(host)
    if not ips:
        for m in dns_order():
            if m == "system":
                try:
                    r = _orig_gai(host, port, fam, type, proto, flags)
                    if r:
                        return r
                except Exception:
                    pass
                continue
            _in_doh.busy = True
            try:
                ips = resolve(host, m)
            finally:
                _in_doh.busy = False
            if ips:
                DNS_CACHE[host] = (ips, time.time())
                break
    if not ips:
        raise socket.gaierror(socket.EAI_NONAME, "Name does not resolve")
    p = int(port) if port and str(port).isdigit() else 0
    return [(socket.AF_INET6 if ":" in ip else socket.AF_INET, type or socket.SOCK_STREAM, proto or 0, "", (ip, p)) for ip in ips]


socket.getaddrinfo = patched_gai


def dns_reset():
    DNS_CACHE.clear()


def cache_get(host):
    """IP из кэша DNS (живёт 90 с — устойчиво к смене Wi-Fi/мобильной сети и VPN)."""
    v = DNS_CACHE.get(host)
    if v and time.time() - v[1] < DNS_TTL:
        return v[0]
    DNS_CACHE.pop(host, None)
    return None


# ---- шаблоны (как в примере: выбор 1,2,3 / 1-3 / all) ----
PROXY_T = ["http://127.0.0.1:1082", "http://127.0.0.1:8080", "http://127.0.0.1:8081", "http://127.0.0.1:3128",
           "http://127.0.0.1:9098", "http://198.18.0.3:8080", "socks5://127.0.0.1:1080", "socks5h://127.0.0.1:1080",
           "socks5://127.0.0.1:10808", "socks5h://127.0.0.1:10808", "socks5://127.0.0.1:1081", "socks5h://127.0.0.1:1086",
           "socks5h://127.0.0.1:9050", ""]
DNS_T = ["1.1.1.1,8.8.8.8,94.140.14.14,9.9.9.9", "1.1.1.1,1.0.0.1", "8.8.8.8,8.8.4.4", "94.140.14.14,94.140.15.15",
         "9.9.9.9,149.112.112.112", "208.67.222.222,208.67.220.220", "76.76.2.0,76.76.10.0", "77.88.8.8,77.88.8.1",
         "223.5.5.5,223.6.6.6", "185.222.222.222,185.184.222.222",
         "1.1.1.1,1.0.0.1,8.8.8.8,8.8.4.4,9.9.9.9,149.112.112.112,94.140.14.14,94.140.15.15"]
DOH_T = ["", "https://cloudflare-dns.com/dns-query", "https://dns.google/dns-query", "https://dns.quad9.net/dns-query",
         "https://dns.adguard-dns.com/dns-query", "https://unfiltered.adguard-dns.com/dns-query",
         "https://dns.comss.one/dns-query", "https://dns.sb/dns-query", "https://dns.alidns.com/dns-query",
         "https://1.1.1.1/dns-query", "https://8.8.8.8/dns-query", "https://9.9.9.9/dns-query", "https://94.140.14.14/dns-query"]
PROXY_RE = re.compile(r"^(https?|socks4a?|socks5h?)://\S+$", re.I)


def pick_templates(title, items, current, multi=True, merge="ips"):
    """Выбор шаблонов: номер, 1,2,3, 1-3, all; 0 — ввести вручную; Enter — оставить. Возвращает строку или None."""
    print("\n" + c(title, accent(), True))
    for i, t in enumerate(items, 1):
        mark = c(" ◄", OK_C) if t == current else ""
        print("  %s %s%s" % (c("%2d" % i, accent(), True), t if t else dim(L("(пусто / выключено)", "(empty / off)")), mark))
    print("  %s %s" % (c(" 0", WARN_C, True), L("ввести вручную", "enter manually")))
    if multi:
        print(dim("  " + L("можно: 2   1,3,5   1-3   all", "allowed: 2   1,3,5   1-3   all")))
    v = ask(L("Выбор", "Choice"), "", quit_ok=False)
    if not v:
        return None
    if v == "0":
        r = ask(L("Значение ('-' = очистить)", "Value ('-' = clear)"), "", quit_ok=False)
        return None if not r else ("" if r == "-" else r)
    try:
        nums = parse_multi(v, len(items)) if multi else [int(v)]
        sel = [items[i - 1] for i in nums]
    except Exception:
        print("[!] " + L("Неверный ввод", "Bad input"))
        return None
    if not multi or len(sel) == 1:
        return sel[0]
    if merge == "ips":
        parts = []
        for s in sel:
            for x in s.split(","):
                if x.strip() and x.strip() not in parts:
                    parts.append(x.strip())
        return ",".join(parts)
    return ",".join(s for s in sel if s)


def set_proxy_ui():
    v = pick_templates(L("Прокси (http/https/socks5/socks5h)", "Proxy (http/https/socks5/socks5h)"), PROXY_T, ST.net("proxy"), multi=False)
    if v is None:
        return False
    if v and not PROXY_RE.match(v):
        print("[!] " + L("Неверный формат прокси", "Invalid proxy format"))
        return False
    ST.setnet("proxy", v)
    dns_reset()
    print("[+] " + L("Прокси сохранён: ", "Proxy saved: ") + (v or L("выключен", "off")))
    return True


def set_dns_ui():
    v = pick_templates(L("DNS-серверы (UDP/53)", "DNS servers (UDP/53)"), DNS_T, ST.net("dns_servers"))
    if v is None:
        return False
    ST.setnet("dns_servers", v)
    if ST.net("dns_mode") == "system":
        ST.setnet("dns_mode", "auto")
    dns_reset()
    print("[+] DNS: " + v)
    return True


def set_doh_ui():
    v = pick_templates(L("DoH-серверы (DNS-over-HTTPS)", "DoH servers (DNS-over-HTTPS)"), DOH_T, ST.net("doh_url"), merge="join")
    if v is None:
        return False
    ST.setnet("doh_url", v)
    dns_reset()
    print("[+] DoH: " + (v or L("пусто", "empty")))
    return True


def wait_network(maxwait=15):
    """Дождаться появления сети (переключение Wi-Fi ↔ LTE, смена VPN). Ограничено по времени."""
    t0, shown = time.time(), False
    while time.time() - t0 < maxwait:
        for host, port in (("1.1.1.1", 443), ("8.8.8.8", 443), ("9.9.9.9", 443), ("77.88.8.8", 443)):
            try:
                socket.create_connection((host, port), 2).close()
                return True
            except Exception:
                pass
        if not shown:
            print("[*] " + L("Сеть недоступна — жду переключения сети (до %d с)..." % maxwait, "Network down — waiting for network switch (up to %d s)..." % maxwait))
            shown = True
        dns_reset()
        time.sleep(1.5)
    return False


# ---- HTTP-загрузка с несколькими способами и починкой ----
LAST_ERR = [""]
INSECURE_OK = set()


def classify(err):
    t = str(err).lower()
    for key, name in (("certificate", "tls"), ("ssl", "tls"), ("handshake", "tls"), ("name or service", "dns"),
                      ("name does not resolve", "dns"), ("resolution", "dns"), ("timed out", "timeout"),
                      ("timeout", "timeout"), ("refused", "refused"), ("reset", "reset"), ("unreachable", "net"),
                      ("404", "http"), ("403", "http"), ("5", "")):
        if key in t and name:
            return name
    return "other"


def make_ctx(verify=True):
    """SSL-контекст: системные сертификаты + дополнительный CA (например, Минцифры) из настроек."""
    if not verify:
        return ssl._create_unverified_context()
    ctx = ssl.create_default_context()
    ca = ST.net("extra_ca")
    if ca and os.path.exists(ca):
        try:
            ctx.load_verify_locations(cafile=ca)
        except Exception:
            pass
    return ctx


def _opener(verify):
    p = ST.net("proxy").strip()
    h = [urllib.request.ProxyHandler({"http": p, "https": p} if p and p.lower().startswith("http") else {})]
    h.append(urllib.request.HTTPSHandler(context=make_ctx(verify)))
    return urllib.request.build_opener(*h)


def _get_urllib(url, timeout, headers, label, show, verify):
    req = urllib.request.Request(url, headers=dict({"User-Agent": UA}, **(headers or {})))
    with _opener(verify).open(req, timeout=timeout) as r:
        total = int(r.headers.get("Content-Length") or 0) or None
        buf = bytearray()
        bar = Bar(total, label or urlparse(url).netloc, "B") if show else None
        while True:
            ch = r.read(16384)
            if not ch:
                break
            buf += ch
            if bar:
                bar.update(len(buf))
        if bar:
            bar.close()
        if total and len(buf) < total * 0.98:
            raise IOError("incomplete download")
        return bytes(buf)


def _get_cli(tool, url, timeout, headers, verify):
    if not shutil.which(tool):
        raise FileNotFoundError(tool)
    p = ST.net("proxy").strip()
    ipv = ST.net("ip_version")
    env = dict(os.environ)
    if tool == "curl":
        cmd = ["curl", "-sSL", "--fail", "--connect-timeout", str(timeout), "--max-time", str(timeout * 4), "-A", UA]
        if p:
            cmd += ["-x", p]
        if not verify:
            cmd.append("-k")
        if ipv != "auto":
            cmd.append("-4" if ipv == "ipv4" else "-6")
        host = urlparse(url).hostname
        if host and not p and not is_ip(host) and not (ST.net("dns_mode") == "system"):
            ips = cache_get(host) or resolve(host, "udp") or resolve(host, "doh")
            if ips:
                cmd += ["--resolve", "%s:%d:%s" % (host, 443 if url.startswith("https") else 80, ips[0])]
        for k, v in (headers or {}).items():
            cmd += ["-H", "%s: %s" % (k, v)]
        cmd += ["-o", "-", url]
    else:
        cmd = ["wget", "-q", "-O", "-", "-T", str(timeout), "-U", UA] + ([] if verify else ["--no-check-certificate"]) + [url]
        if p:
            env["http_proxy"] = env["https_proxy"] = p
    r = subprocess.run(cmd, capture_output=True, timeout=timeout * 5, env=env)
    if r.returncode != 0:
        raise IOError((r.stderr or b"").decode("utf-8", "replace").strip() or "exit %d" % r.returncode)
    return r.stdout


def fetch(url, timeout=None, headers=None, label="", show=True, interactive=True, retries=None, minlen=1, quiet=False):
    """Скачать URL: urllib → curl → wget, повторы, TLS-fallback (с вопросом), меню починки сети."""
    timeout = timeout or ST.net("timeout")
    retries = retries or ST.net("retries")
    host = urlparse(url).hostname or ""
    for rnd in range(3):
        verify = ST.net("verify_tls") and host not in INSECURE_OK
        last = None
        for att in range(1, retries + 1):
            socks = ST.net("proxy").lower().startswith("socks")
            for m in (["curl", "wget"] if socks else ["urllib", "curl", "wget"]):
                try:
                    data = (_get_urllib(url, timeout, headers, label, show, verify) if m == "urllib"
                            else _get_cli(m, url, timeout, headers, verify))
                    if data is not None and len(data) >= minlen:
                        return data
                except Exception as e:
                    last = e
                    LAST_ERR[0] = "%s: %s" % (m, e)
                    if ST.g("verbose"):
                        print("[!] %s %s → %s" % (m, trunc(url, 40), trunc(str(e), term_w() - 20)))
                    if classify(e) in ("dns", "net", "timeout", "reset", "refused"):
                        dns_reset()
                    if classify(e) == "tls" and verify:
                        break
            if last is not None and classify(last) == "tls" and verify:
                break
            if att < retries:
                if last is not None and classify(last) in ("dns", "net", "timeout", "reset"):
                    wait_network(6)
                time.sleep(min(1.5 * att, 4))
        kind = classify(last) if last else "other"
        if kind == "tls" and verify and ST.net("tls_fallback") != "never":
            if ST.net("tls_fallback") == "auto" or (interactive and confirm(
                    L("Ошибка TLS-сертификата для %s. Повторить БЕЗ проверки сертификата?" % host,
                      "TLS certificate error for %s. Retry WITHOUT verification?" % host))):
                INSECURE_OK.add(host)
                print("[!] " + L("Проверка TLS отключена для ", "TLS verification disabled for ") + host)
                continue
        if not quiet:
            print("[!] %s: %s" % (L("Не удалось скачать", "Download failed"), trunc(url, 60)))
            print("[!] %s (%s)" % (trunc(LAST_ERR[0], term_w() - 12), kind))
        if not (interactive and sys.stdin.isatty()) or rnd == 2:
            return None
        if net_trouble(url) == "skip":
            return None
    return None


def fetch_text(url, **kw):
    d = fetch(url, **kw)
    return None if d is None else d.decode("utf-8", "replace")


def fetch_lines(url_or_list, label="", **kw):
    """Скачать список (str или [зеркала]) → (lines, источник). Пустой список при неудаче."""
    for u in ([url_or_list] if isinstance(url_or_list, str) else url_or_list):
        t = fetch_text(u, label=label, **kw)
        if t and len(t.splitlines()) > 5 and "<html" not in t[:400].lower():
            return t.splitlines(), u
    return [], None


def net_trouble(url=None):
    """Меню починки сети при ошибке скачивания. Возвращает 'retry' или 'skip'."""
    while True:
        k = menu(L("Проблема с сетью — что сделать?", "Network problem — what to do?"), [
            ("1", L("Повторить", "Retry"), ""), ("2", L("Сменить прокси", "Change proxy"), ST.net("proxy") or "-"),
            ("3", L("Сменить DNS (UDP)", "Change DNS (UDP)"), ST.net("dns_servers")[:24]),
            ("4", L("Сменить DoH", "Change DoH"), ST.net("doh_url")[:24] or "-"),
            ("5", L("Режим DNS: ", "DNS mode: ") + ST.net("dns_mode"), ""),
            ("6", L("IPv4/IPv6: ", "IPv4/IPv6: ") + ST.net("ip_version"), ""),
            ("7", L("Проверить связь (много сервисов)", "Connectivity test (many services)"), ""),
            ("8", L("Полный центр сети", "Full network center"), ""), ("9", L("Пропустить", "Skip"), "")], show=True)
        if k in ("q", "9"):
            return "skip"
        if k == "1":
            return "retry"
        if k == "2" and set_proxy_ui():
            return "retry"
        if k == "3" and set_dns_ui():
            return "retry"
        if k == "4" and set_doh_ui():
            return "retry"
        if k == "5":
            opts = CHOICES["dns_mode"]
            ST.setnet("dns_mode", opts[(opts.index(ST.net("dns_mode")) + 1) % len(opts)])
            dns_reset()
        if k == "6":
            opts = CHOICES["ip_version"]
            ST.setnet("ip_version", opts[(opts.index(ST.net("ip_version")) + 1) % len(opts)])
            dns_reset()
        if k == "7":
            conn_report(True)
        if k == "8":
            run_sibling("netcenter.py")
            return "retry"


# ---- проверка соединения по многим сервисам (не только Google) ----
SERVICES = [("Google", "www.google.com", "/generate_204"), ("Cloudflare", "one.one.one.one", "/"),
            ("Apple", "captive.apple.com", "/"), ("GitHub", "raw.githubusercontent.com", "/"),
            ("Yandex", "ya.ru", "/"), ("Microsoft", "www.msftconnecttest.com", "/connecttest.txt"),
            ("Telegram", "api.telegram.org", "/"), ("YouTube", "www.youtube.com", "/generate_204"),
            ("Quad9", "dns.quad9.net", "/"), ("jsDelivr", "cdn.jsdelivr.net", "/")]


def probe(name, host, path, timeout=6):
    """Проверка одного сервиса по этапам: DNS → TCP → TLS → HTTP. Возвращает dict."""
    r = {"name": name, "host": host, "dns": None, "tcp": None, "tls": None, "http": None, "err": "", "ip": ""}
    proxy = ST.net("proxy").strip()
    t = time.time()
    try:
        if proxy:                                           # через прокси: один запрос целиком
            if proxy.lower().startswith("socks"):
                out = subprocess.run(["curl", "-sS", "-o", "/dev/null", "-w", "%{http_code}", "-x", proxy, "--max-time", str(timeout),
                                      "https://%s%s" % (host, path)], capture_output=True, timeout=timeout + 3)
                code = int((out.stdout or b"0").decode() or 0)
            else:
                with _opener(ST.net("verify_tls")).open(urllib.request.Request("https://%s%s" % (host, path), headers={"User-Agent": UA}), timeout=timeout) as rr:
                    code = rr.status
            r["http"] = round((time.time() - t) * 1000)
            r["err"] = "" if 0 < code < 500 else "HTTP %s" % code
            return r
        ips = []
        for m in dns_order():
            ips = resolve(host, m)
            if ips:
                r["dns"] = round((time.time() - t) * 1000)
                break
        if not ips:
            r["err"] = "dns"
            return r
        r["ip"] = ips[0]
        t = time.time()
        s = socket.create_connection((ips[0], 443), timeout)
        r["tcp"] = round((time.time() - t) * 1000)
        t = time.time()
        ctx = make_ctx(ST.net("verify_tls"))
        ss = ctx.wrap_socket(s, server_hostname=host)
        r["tls"] = round((time.time() - t) * 1000)
        t = time.time()
        ss.settimeout(timeout)
        ss.sendall(("HEAD %s HTTP/1.1\r\nHost: %s\r\nUser-Agent: tk\r\nConnection: close\r\n\r\n" % (path, host)).encode())
        line = ss.recv(64).split(b"\r\n")[0].decode("latin-1")
        r["http"] = round((time.time() - t) * 1000)
        r["err"] = "" if re.search(r" [1-4]\d\d", line) else line[:30]
        ss.close()
    except Exception as e:
        r["err"] = "%s" % (str(e)[:40] or type(e).__name__)
    return r


def conn_check(services=None, stop_after=None, timeout=6):
    """Параллельная проверка нескольких сервисов. stop_after=N — выйти, когда N успешны."""
    res, lock = [], threading.Lock()
    ok_count = [0]

    def work(sv):
        r = probe(sv[0], sv[1], sv[2], timeout)
        with lock:
            res.append(r)
            if r["http"] is not None and not r["err"]:
                ok_count[0] += 1
    ths = [threading.Thread(target=work, args=(s,), daemon=True) for s in (services or SERVICES)]
    for t in ths:
        t.start()
    t0 = time.time()
    while any(t.is_alive() for t in ths) and time.time() - t0 < timeout + 4:
        if stop_after and ok_count[0] >= stop_after:
            break
        time.sleep(0.1)
    return list(res)


def conn_report(show_table=True):
    """Запустить проверку и красиво показать. Возвращает True, если сеть работает."""
    with spin(L("Проверяю связь с несколькими сервисами", "Checking connectivity to several services")):
        res = conn_check()
    ok = [r for r in res if r["http"] is not None and not r["err"]]
    if show_table:
        rows = []
        for r in sorted(res, key=lambda x: x["name"]):
            good = r["http"] is not None and not r["err"]
            f = lambda v: ("%dms" % v) if v is not None else dim("-")
            rows.append([c(U("● ", "+ "), OK_C if good else ERR_C) + r["name"], f(r["dns"]), f(r["tcp"]), f(r["tls"]), f(r["http"]),
                         dim(r["err"][:18]) if r["err"] else c("OK", OK_C)])
        table(rows, ["Service", "DNS", "TCP", "TLS", "HTTP", ""])
    print(("[+] " if ok else "[!] ") + L("Доступно сервисов: %d из %d" % (len(ok), len(res)), "Services reachable: %d of %d" % (len(ok), len(res))))
    return bool(ok)


def preflight_net():
    """Быстрая проверка перед загрузкой (2 успешных сервиса — достаточно)."""
    if not ST.net("preflight"):
        return True
    with spin(L("Проверка сети", "Network check"), quiet_ok=True):
        res = conn_check(stop_after=2, timeout=5)
    ok = any(r["http"] is not None and not r["err"] for r in res)
    if not ok:
        print("[!] " + L("Нет связи ни с одним тестовым сервисом", "No test service is reachable"))
        return net_trouble() == "retry" and conn_report(False)
    return True


# ==========================================================================
#  ЧЕКЛИСТ: переключаемые опции с памятью (вместо ввода «11010»)
# ==========================================================================
def checklist(tool, title, items):
    """items: [(key, label, default_bool)] → dict key→bool. Состояние запоминается в настройках."""
    state = {k: ST.mem(tool, "opt_" + k, d) for k, _, d in items}
    while True:
        print("\n" + c(title, accent(), True))
        for i, (k, lab, _) in enumerate(items, 1):
            mark = c(U("◉", "[x]"), OK_C, True) if state[k] else c(U("○", "[ ]"), ERR_C)
            print("  %s %s %s" % (c("%2d" % i, accent(), True), mark, lab))
        v = ask(L("Переключить номера (Enter — готово)", "Toggle numbers (Enter = done)"), "", quit_ok=False, hint="1,3-4 / all")
        if not v:
            break
        try:
            for n in parse_multi(v, len(items)):
                state[items[n - 1][0]] = not state[items[n - 1][0]]
        except ValueError:
            print("[!] " + L("Неверный ввод", "Bad input"))
    for k, val in state.items():
        ST.setmem(tool, "opt_" + k, val)
    return state


def mem_ask(tool, key, label, default="", **kw):
    """ask() с памятью: подставляет прошлое значение и запоминает новое."""
    v = ask(label, ST.mem(tool, key, default), **kw)
    ST.setmem(tool, key, v)
    return v


# ==========================================================================
#  ДЕКОДИРОВАНИЕ СКАЧАННОГО И ИНФОРМАЦИЯ О СРЕДЕ
# ==========================================================================
def decode_download(data, want="text"):
    """Распознать закодированный файл (base64/gzip/percent/hex...). Возвращает (text, chain) либо (None, причина)."""
    import tkcodec
    if not data:
        return None, L("пустой файл", "empty file")
    try:
        obj, chain, enc = tkcodec.smart_decode(data)
    except Exception as e:
        return None, L("файл повреждён или формат не поддерживается: %s" % e, "file is damaged or format unsupported: %s" % e)
    if isinstance(obj, (dict, list)):
        return json.dumps(obj, ensure_ascii=False, indent=1), chain
    txt = obj if isinstance(obj, str) else str(obj)
    if txt.count("\ufffd") > max(5, len(txt) // 20) or "\x00" in txt[:2000]:
        return None, L("файл повреждён или имеет несовместимый (бинарный) формат", "file is damaged or has an incompatible (binary) format")
    return txt, chain


def env_info():
    """Сведения о среде выполнения (iSH / Termux / Alpine / Debian / macOS ...)."""
    e = os.environ.get("TK_ENV", "")
    if not e:
        try:
            u = subprocess.run(["uname", "-a"], capture_output=True, text=True, timeout=5).stdout.lower()
        except Exception:
            u = ""
        e = "ish" if "ish" in u else "macos" if "darwin" in u else "termux" if "com.termux" in os.environ.get("PREFIX", "") else \
            "alpine" if os.path.exists("/etc/alpine-release") else "linux"
    alp = ""
    try:
        alp = open("/etc/alpine-release").read().strip()
    except Exception:
        pass
    return {"env": e, "alpine": alp, "python": "%d.%d.%d" % sys.version_info[:3], "ish": e == "ish", "loc": os.path.exists("/dev/location")}


# ==========================================================================
#  ЗАПУСК ИНСТРУМЕНТОВ, САМОТЕСТ ОКРУЖЕНИЯ
# ==========================================================================
def ensure_dirs(*names):
    for n in names:
        (BASE / n).mkdir(parents=True, exist_ok=True)


def run_tool(name, fn):
    """Обёртка main инструмента: Quit/Ctrl+C — штатный выход, ошибки — в лог без падения."""
    fix_tty()
    try:
        fn()
    except (Quit, KeyboardInterrupt):
        print("\n[+] " + L("Выход из %s." % name, "Leaving %s." % name))
    except Exception:
        tb = traceback.format_exc()
        print("\n[!] " + L("Ошибка в %s: " % name, "Error in %s: " % name) + tb.strip().splitlines()[-1])
        try:
            CONF.mkdir(parents=True, exist_ok=True)
            with open(str(CRASH_LOG), "a") as f:
                f.write("== %s %s\n%s\n" % (time.ctime(), name, tb))
            print("[*] " + L("Подробности: ", "Details: ") + str(CRASH_LOG))
        except Exception:
            pass
        pause()


def selftest():
    """Проверка компонентов окружения (используется оболочкой для выбора версии Alpine)."""
    import importlib
    for mod, req in (("json", 1), ("sqlite3", 1), ("ssl", 1), ("socket", 1), ("select", 1), ("threading", 1), ("zlib", 1),
                     ("hashlib", 1), ("readline", 0), ("termios", 0), ("ctypes", 0), ("chardet", 0)):
        try:
            importlib.import_module(mod)
            print("OK %s" % mod)
        except Exception as e:
            print("%s %s %s" % ("FAIL" if req else "WARN", mod, str(e)[:60].replace(" ", "_")))
    try:
        ssl.create_default_context()
        socket.socket(socket.AF_INET, socket.SOCK_DGRAM).close()
        subprocess.run(["true"], timeout=10)
        print("OK runtime")
    except Exception as e:
        print("FAIL runtime %s" % str(e)[:60].replace(" ", "_"))
    for b in ("curl", "wget", "node", "qjs"):
        print("%s %s" % ("OK" if shutil.which(b) else "WARN", b))
    print("PY %d.%d.%d" % sys.version_info[:3])


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        selftest()
TKEOF_tkcore

tk_put tkcodec.py << 'TKEOF_tkcodec'
# -*- coding: utf-8 -*-
# ==========================================================================
#  tkcodec — кодировки тела (base64/gzip/percent/hex/JSON-в-строке) без «кракозябр»,
#  обратное кодирование, JSON-пути (get/set/delete), diff, обобщение путей.
# ==========================================================================
import re, json, base64, zlib, gzip, binascii
from urllib.parse import quote, unquote_to_bytes

TEXT_ENCS = ("utf-8", "utf-8-sig", "utf-16", "cp1251", "koi8-r", "cp866", "latin-1")
_B64 = re.compile(r"^[A-Za-z0-9+/\-_]{16,}={0,2}$")
_HEX = re.compile(r"^(?:[0-9a-fA-F]{2}){8,}$")


def decode_bytes(raw):
    """bytes → (str, encoding). Подбор кодировки с проверкой на «кракозябры»."""
    best = None
    for enc in TEXT_ENCS:
        try:
            t = raw.decode(enc)
        except Exception:
            continue
        bad = t.count("\ufffd") + sum(1 for ch in t if ord(ch) < 9 or 13 < ord(ch) < 32)
        if bad == 0:
            return t, enc
        if best is None or bad < best[2]:
            best = (t, enc, bad)
    return (best[0], best[1]) if best else (raw.decode("utf-8", "replace"), "utf-8")


def _b64d(s):
    s = re.sub(r"\s+", "", s)
    pad = "=" * (-len(s) % 4)
    for fn in (base64.b64decode, base64.urlsafe_b64decode):
        try:
            return fn(s + pad), ("b64url" if fn is base64.urlsafe_b64decode and ("-" in s or "_" in s) else "b64")
        except Exception:
            continue
    return None, None


def smart_decode(data, max_depth=5):
    """Распознать слои кодирования. Возвращает (obj, chain, enc): obj — dict/list/str; chain — ['b64','gzip','json'...]."""
    chain, enc = [], "utf-8"
    cur = data if isinstance(data, bytes) else data.encode("utf-8", "surrogateescape")
    for _ in range(max_depth):
        if cur[:2] == b"\x1f\x8b":
            try:
                cur = gzip.decompress(cur); chain.append("gzip"); continue
            except Exception:
                pass
        if cur[:1] in (b"\x78",) and len(cur) > 6:
            try:
                cur = zlib.decompress(cur); chain.append("zlib"); continue
            except Exception:
                pass
        txt, enc = decode_bytes(cur)
        st = txt.strip()
        if st[:1] in "{[" and st[-1:] in "}]":
            try:
                return json.loads(st), chain + ["json"], enc
            except Exception:
                pass
        if st[:1] == '"' and st[-1:] == '"':                      # JSON-строка, внутри которой JSON
            try:
                inner = json.loads(st)
                if isinstance(inner, str):
                    chain.append("jsonstr"); cur = inner.encode("utf-8"); continue
            except Exception:
                pass
        if "%" in st and re.search(r"%[0-9A-Fa-f]{2}", st) and " " not in st[:80]:
            try:
                cur = unquote_to_bytes(st); chain.append("percent"); continue
            except Exception:
                pass
        if _HEX.match(st):
            try:
                cur = binascii.unhexlify(st); chain.append("hex"); continue
            except Exception:
                pass
        if _B64.match(re.sub(r"\s+", "", st)):
            raw, kind = _b64d(st)
            if raw:
                t2, _ = decode_bytes(raw)
                ok = raw[:2] == b"\x1f\x8b" or raw[:1] == b"\x78" or t2.strip()[:1] in "{[\"<" or t2.isprintable() or "\n" in t2
                if ok and len(raw) > 4:
                    cur = raw; chain.append(kind); continue
        return txt, chain + ["text"], enc
    return decode_bytes(cur)[0], chain + ["text"], enc


def smart_encode(obj, chain, enc="utf-8", compact=True):
    """Обратная операция к smart_decode: упаковать obj по той же цепочке."""
    out = None
    for step in reversed(chain):
        if step == "json":
            out = json.dumps(obj, ensure_ascii=False, separators=(",", ":") if compact else None).encode(enc if enc != "utf-8-sig" else "utf-8")
        elif step == "text":
            out = (obj if isinstance(obj, str) else str(obj)).encode(enc if enc != "utf-8-sig" else "utf-8", "replace")
        elif step == "jsonstr":
            out = json.dumps(out.decode("utf-8", "replace"), ensure_ascii=False).encode("utf-8")
        elif step in ("b64", "b64url"):
            out = (base64.urlsafe_b64encode(out) if step == "b64url" else base64.b64encode(out))
        elif step == "gzip":
            out = gzip.compress(out)
        elif step == "zlib":
            out = zlib.compress(out)
        elif step == "percent":
            out = quote(out, safe="").encode()
        elif step == "hex":
            out = binascii.hexlify(out)
    return out


# ---- JSON-пути: a.b[0].c, wildcard a[*].b ----
_TOK = re.compile(r"\[(\*|\d+)\]|([^.\[\]]+)")


def tokens(path):
    return [(int(m.group(1)) if m.group(1) and m.group(1) != "*" else ("*" if m.group(1) else m.group(2))) for m in _TOK.finditer(path)]


def flatten(obj, prefix="", out=None, limit=4000):
    """Список (path, value) для всех листьев JSON."""
    out = [] if out is None else out
    if len(out) >= limit:
        return out
    if isinstance(obj, dict):
        for k, v in obj.items():
            flatten(v, "%s.%s" % (prefix, k) if prefix else str(k), out, limit)
        if not obj:
            out.append((prefix, obj))
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            flatten(v, "%s[%d]" % (prefix, i), out, limit)
        if not obj:
            out.append((prefix, obj))
    else:
        out.append((prefix, obj))
    return out


def get_path(obj, path):
    """Значения по пути (с wildcard) → список (конкретный_путь, значение)."""
    res = [("", obj)]
    for t in tokens(path):
        nxt = []
        for p, v in res:
            if t == "*" and isinstance(v, list):
                nxt += [("%s[%d]" % (p, i), x) for i, x in enumerate(v)]
            elif isinstance(t, int) and isinstance(v, list) and t < len(v):
                nxt.append(("%s[%d]" % (p, t), v[t]))
            elif isinstance(t, str) and isinstance(v, dict) and t in v:
                nxt.append((p + "." + t if p else t, v[t]))
        res = nxt
    return res


def generalize(path):
    return re.sub(r"\[\d+\]", "[*]", path)


def walk_type(v):
    return "null" if v is None else "bool" if isinstance(v, bool) else "number" if isinstance(v, (int, float)) else "string" if isinstance(v, str) else "array" if isinstance(v, list) else "object"


def diff(a, b, prefix="", out=None, limit=2000):
    """Структурный diff: [(path, kind, old, new)] kind ∈ changed/added/removed/type."""
    out = [] if out is None else out
    if len(out) >= limit:
        return out
    if isinstance(a, dict) and isinstance(b, dict):
        for k in a:
            p = "%s.%s" % (prefix, k) if prefix else str(k)
            if k not in b:
                out.append((p, "removed", a[k], None))
            else:
                diff(a[k], b[k], p, out, limit)
        for k in b:
            if k not in a:
                out.append(("%s.%s" % (prefix, k) if prefix else str(k), "added", None, b[k]))
    elif isinstance(a, list) and isinstance(b, list):
        for i in range(max(len(a), len(b))):
            p = "%s[%d]" % (prefix, i)
            if i >= len(a):
                out.append((p, "added", None, b[i]))
            elif i >= len(b):
                out.append((p, "removed", a[i], None))
            else:
                diff(a[i], b[i], p, out, limit)
    elif walk_type(a) != walk_type(b):
        out.append((prefix, "type", a, b))
    elif a != b:
        out.append((prefix, "changed", a, b))
    return out


_VOL = re.compile(r"(time|date|stamp|nonce|token|sign|expire|uuid|guid|session|rand|trace|request_?id|etag|cursor)", re.I)


def volatile(path, old=None, new=None):
    """Эвристика «шумного» поля (время/случайные значения)."""
    if _VOL.search(path):
        return True
    for v in (old, new):
        if isinstance(v, (int, float)) and not isinstance(v, bool) and (v > 1e9 or v < -1e9):
            return True
        if isinstance(v, str) and (re.fullmatch(r"[0-9a-fA-F-]{32,40}", v) or re.fullmatch(r"\d{4}-\d\d-\d\dT[\d:.]+Z?", v)):
            return True
    return False


def set_path(obj, path, value):
    n = 0
    for p, _ in get_path(obj, path):
        toks = tokens(p)
        cur = obj
        for t in toks[:-1]:
            cur = cur[t]
        if toks:
            cur[toks[-1]] = value; n += 1
    return n


def del_path(obj, path):
    n = 0
    for p, _ in sorted(get_path(obj, path), key=lambda x: x[0], reverse=True):
        toks = tokens(p)
        cur = obj
        for t in toks[:-1]:
            cur = cur[t]
        if toks:
            del cur[toks[-1]]; n += 1
    return n


def short(v, n=60):
    s = json.dumps(v, ensure_ascii=False) if not isinstance(v, str) else v
    return s if len(s) <= n else s[:n - 1] + "…"


def url_to_pattern(url, keep_query=False):
    """URL → безопасный regex для Shadowrocket (id/uuid/числа в пути → [^/]+)."""
    from urllib.parse import urlparse
    p = urlparse(url)
    segs = []
    for s in p.path.split("/"):
        if re.fullmatch(r"\d{3,}|[0-9a-fA-F-]{24,}|[A-Za-z0-9_-]{20,}", s):
            segs.append("[^/]+")
        else:
            segs.append(re.escape(s).replace("\\-", "-"))
    path = "/".join(segs)
    host = re.escape(p.netloc).replace("\\-", "-")
    return "^https?:\\/\\/%s%s%s$" % (host, path.replace("/", "\\/"), "(\\?.*)?" if not keep_query else "")
TKEOF_tkcodec

tk_put rules.py << 'TKEOF_rules'
# -*- coding: utf-8 -*-
# ==========================================================================
#  rules — движок правил: разбор строк, определение вида текста, переписывание
#  политик, распаковка rule-set в правила, упаковка правил в rule-set с СОХРАНЕНИЕМ
#  приоритета (минимальное число наборов), конвертация в другие форматы.
# ==========================================================================
import re, json, ipaddress, fnmatch
from collections import OrderedDict

RULE_TYPES = ["DOMAIN-SUFFIX", "DOMAIN-KEYWORD", "DOMAIN-WILDCARD", "DOMAIN", "USER-AGENT", "URL-REGEX", "IP-CIDR", "IP-CIDR6", "IP-ASN",
              "RULE-SET", "DOMAIN-SET", "SCRIPT", "DST-PORT", "SRC-PORT", "GEOIP", "PROTOCOL", "PROCESS-NAME", "AND", "OR", "NOT", "FINAL"]
POLICIES = ["PROXY", "DIRECT", "TAILSCALE", "REJECT", "REJECT-DICT", "REJECT-ARRAY", "REJECT-200", "REJECT-IMG", "REJECT-TINYGIF",
            "REJECT-DROP", "REJECT-NO-DROP", "REJECT-VIDEO"]
POLICY_HELP = {"REJECT": "HTTP 404, пусто / 404 empty", "REJECT-DICT": "200 + {}", "REJECT-ARRAY": "200 + []", "REJECT-200": "200 empty",
               "REJECT-IMG": "200 + 1px image", "REJECT-TINYGIF": "200 + 1px gif", "REJECT-DROP": "drop IP packet",
               "REJECT-NO-DROP": "ICMP port unreachable", "REJECT-VIDEO": "200 + empty video", "DIRECT": "direct", "PROXY": "proxy", "TAILSCALE": "tailscale"}
_SIMPLE = {"DOMAIN-SUFFIX", "DOMAIN-KEYWORD", "DOMAIN-WILDCARD", "DOMAIN", "USER-AGENT", "URL-REGEX", "IP-CIDR", "IP-CIDR6", "IP-ASN",
           "RULE-SET", "DOMAIN-SET", "SCRIPT", "DST-PORT", "SRC-PORT", "GEOIP", "PROTOCOL", "PROCESS-NAME"}


def parse_line(line):
    """Строка → dict(kind: rule|comment|blank|other, type, val, policy, opts)."""
    s = line.strip()
    if not s:
        return {"kind": "blank", "raw": line}
    if s.startswith(("#", ";", "//")):
        return {"kind": "comment", "raw": line}
    p = s.split(",")
    t = p[0].strip().upper()
    if t in ("AND", "OR", "NOT"):
        m = re.match(r"^(AND|OR|NOT)\s*,\s*(\(.*\))\s*,\s*([^,()]+)(?:,(.*))?$", s, re.I)
        if m:
            return {"kind": "rule", "type": m.group(1).upper(), "val": m.group(2), "policy": m.group(3).strip(), "opts": [x.strip() for x in (m.group(4) or "").split(",") if x.strip()], "raw": line}
    if t == "FINAL" and len(p) >= 2:
        return {"kind": "rule", "type": "FINAL", "val": "", "policy": p[1].strip(), "opts": [x.strip() for x in p[2:]], "raw": line}
    if t in _SIMPLE and len(p) >= 2:
        pol = p[2].strip() if len(p) >= 3 else ""
        if pol.lower() in ("no-resolve", "pre-matching", "extended-matching"):
            pol, opts = "", [x.strip() for x in p[2:]]
        else:
            opts = [x.strip() for x in p[3:]]
        return {"kind": "rule", "type": t, "val": p[1].strip(), "policy": pol, "opts": [o for o in opts if o], "raw": line}
    return {"kind": "other", "raw": line}


def fmt_rule(r, policy=None):
    pol = r["policy"] if policy is None else policy
    parts = [r["type"]] + ([r["val"]] if r["type"] != "FINAL" else []) + ([pol] if pol else []) + list(r.get("opts", []))
    return ",".join(parts)


def detect_kind(text):
    """Определить вид текста: config / ruleset / vpn-links / json / base64 / clash-yaml / js / hosts / domains / text."""
    head = text[:200000]
    st = head.lstrip()
    lines = [l_.strip() for l_ in head.splitlines() if l_.strip() and not l_.strip().startswith(("#", ";", "//"))][:400]
    if re.search(r"^\[(General|Rule|Proxy Group|Script|MITM)\]", head, re.M | re.I):
        return "config"
    if st[:1] in "{[":
        try:
            json.loads(text if len(text) < 5_000_000 else head)
            return "json"
        except Exception:
            pass
    if re.search(r"^(proxies|rules|proxy-groups|rule-providers)\s*:", head, re.M):
        return "clash-yaml"
    if lines:
        n = len(lines)
        if sum(1 for l_ in lines if re.match(r"^(vless|vmess|trojan|ss|ssr|hysteria2?|hy2|tuic|wireguard|socks5?|http|naive\+https?|anytls|snell|juicity|mieru|ssh|sudoku)://", l_, re.I)) > n * 0.3:
            return "vpn-links"
        if sum(1 for l_ in lines if parse_line(l_)["kind"] == "rule") > n * 0.5:
            return "ruleset"
        if sum(1 for l_ in lines if re.match(r"^(\d{1,3}(\.\d{1,3}){3}|::1?)\s+\S+", l_)) > n * 0.5:
            return "hosts"
        if sum(1 for l_ in lines if re.match(r"^[\w*+.\-]+\.[a-z]{2,}$", l_, re.I)) > n * 0.6:
            return "domains"
        if sum(1 for l_ in lines if re.match(r"^(\s*(function|var|let|const|\$done|if|for)\b|.*=>)", l_)) > n * 0.2:
            return "js"
    if re.fullmatch(r"[A-Za-z0-9+/=_\-\s]{40,}", head.strip()):
        return "base64"
    return "text"


def rewrite_policy(lines, mapping, only_types=None, contains=None, regex=None):
    """Заменить политики в строках. mapping: {старая|'*': новая}. Возвращает (новые строки, число изменений)."""
    out, n = [], 0
    rx = re.compile(regex) if regex else None
    for l_ in lines:
        r = parse_line(l_)
        if r["kind"] != "rule" or not r["policy"] or r["type"] == "FINAL" and False:
            out.append(l_); continue
        if only_types and r["type"] not in only_types:
            out.append(l_); continue
        if contains and contains.lower() not in l_.lower():
            out.append(l_); continue
        if rx and not rx.search(l_):
            out.append(l_); continue
        new = mapping.get(r["policy"], mapping.get("*"))
        if new and new != r["policy"]:
            out.append(fmt_rule(r, new)); n += 1
        else:
            out.append(l_)
    return out, n


def ruleset_to_rules(lines, policy, default_type="DOMAIN-SUFFIX"):
    """Строки rule-set (без политики) → правила с политикой. Голые домены получают default_type."""
    out = []
    for l_ in lines:
        s = l_.strip()
        if not s or s.startswith(("#", ";", "//")):
            continue
        r = parse_line(s)
        if r["kind"] == "rule":
            out.append(fmt_rule(r, policy))
        elif re.fullmatch(r"\+?\.?[\w*\-.]+\.[a-z]{2,}", s, re.I):
            out.append("DOMAIN-SUFFIX,%s,%s" % (s.lstrip("+."), policy) if default_type == "DOMAIN-SUFFIX" else "DOMAIN,%s,%s" % (s, policy))
        elif re.fullmatch(r"[0-9a-fA-F:.]+/\d+", s):
            out.append("IP-CIDR%s,%s,%s,no-resolve" % ("6" if ":" in s else "", s, policy))
    return out


# ---- упаковка в rule-set с сохранением приоритета ----
class _Set:
    def __init__(self, policy):
        self.policy, self.rules = policy, []
        self.suff, self.parents, self.exact, self.kw, self.wild, self.nets = set(), set(), set(), [], [], []
        self.opaque, self.ip_resolving = False, False

    def add(self, r):
        self.rules.append(r)
        t, v = r["type"], r["val"].lower()
        if t == "DOMAIN-SUFFIX":
            self.suff.add(v)
            parts = v.split(".")
            for i in range(1, len(parts)):
                self.parents.add(".".join(parts[i:]))
        elif t == "DOMAIN":
            self.exact.add(v)
        elif t == "DOMAIN-KEYWORD":
            self.kw.append(v)
        elif t == "DOMAIN-WILDCARD":
            self.wild.append(v)
        elif t in ("IP-CIDR", "IP-CIDR6"):
            try:
                self.nets.append(ipaddress.ip_network(v, strict=False))
            except ValueError:
                self.opaque = True
            if "no-resolve" not in [o.lower() for o in r.get("opts", [])]:
                self.ip_resolving = True
        else:
            self.opaque = True


def _anc(x, S):
    parts = x.split(".")
    return any(".".join(parts[i:]) in S for i in range(len(parts)))


def conflicts(r, T):
    """Может ли один запрос совпасть и с правилом r, и с набором T (тогда порядок важен)."""
    if T.opaque or r["type"] not in ("DOMAIN-SUFFIX", "DOMAIN", "DOMAIN-KEYWORD", "DOMAIN-WILDCARD", "IP-CIDR", "IP-CIDR6"):
        return True
    t, v = r["type"], r["val"].lower()
    domainish = bool(T.suff or T.exact or T.kw or T.wild)
    if t in ("IP-CIDR", "IP-CIDR6"):
        noresolve = "no-resolve" in [o.lower() for o in r.get("opts", [])]
        if not noresolve and domainish:
            return True
        if T.ip_resolving and domainish is False and False:
            return True
        try:
            n = ipaddress.ip_network(v, strict=False)
            return any(n.version == m.version and n.overlaps(m) for m in T.nets)
        except ValueError:
            return True
    if T.nets and T.ip_resolving:
        return True
    if t == "DOMAIN-SUFFIX":
        return (_anc(v, T.suff) or v in T.parents or bool(T.kw) or bool(T.wild)
                or any(e == v or e.endswith("." + v) for e in T.exact))
    if t == "DOMAIN":
        return (_anc(v, T.suff) or v in T.exact or any(k in v for k in T.kw) or any(fnmatch.fnmatch(v, w) for w in T.wild))
    if t == "DOMAIN-KEYWORD":
        return bool(T.suff or T.kw or T.wild) or any(v in e for e in T.exact)
    return domainish


def pack_rulesets(lines, split_final=True):
    """Правила (с политикой) → упорядоченные наборы. Возвращает (sets, rest), sets=[(policy,[rule-lines без политики])],
    rest — строки, которые остаются в конфиге (FINAL, pre-matching, RULE-SET и т.п.)."""
    sets, rest = [], []
    for l_ in lines:
        r = parse_line(l_)
        if r["kind"] != "rule" or not r["policy"]:
            continue
        if r["type"] in ("FINAL", "RULE-SET", "DOMAIN-SET") or "pre-matching" in [o.lower() for o in r.get("opts", [])]:
            rest.append(l_.strip()); continue
        placed = None
        for i in range(len(sets) - 1, -1, -1):
            S = sets[i]
            if S.policy == r["policy"]:
                placed = i
            elif conflicts(r, S):
                break
        if placed is None:
            sets.append(_Set(r["policy"])); placed = len(sets) - 1
        sets[placed].add(r)
    out = []
    for S in sets:
        body = []
        for r in S.rules:
            body.append(",".join([r["type"], r["val"]] + list(r.get("opts", []))))
        out.append((S.policy, body))
    return out, rest


def build_ruleset_files(sets, prefix="RULES", base_url=""):
    """Имена файлов и строки RULE-SET для конфига в нужном порядке."""
    files, cfg = [], []
    for i, (pol, body) in enumerate(sets, 1):
        name = "%s_%02d_%s.list" % (prefix, i, re.sub(r"[^\w\-]", "_", pol))
        files.append((name, "\n".join(body) + "\n"))
        cfg.append("RULE-SET,%s%s,%s" % ((base_url.rstrip("/") + "/") if base_url else "", name, pol))
    return files, cfg


# ---- конвертации ----
def to_clash_rules(lines):
    out = []
    for l_ in lines:
        r = parse_line(l_)
        if r["kind"] == "rule" and r["type"] not in ("USER-AGENT", "SCRIPT", "URL-REGEX", "DOMAIN-WILDCARD"):
            pol = {"REJECT-DROP": "REJECT-DROP", "REJECT-200": "REJECT"}.get(r["policy"], r["policy"] if not r["policy"].startswith("REJECT") else "REJECT")
            out.append("  - " + fmt_rule(r, pol))
    return "rules:\n" + "\n".join(out) + "\n"


def to_domain_list(lines):
    """Только домены/суффиксы → список для geosite/domain-set ('+.example.com')."""
    out = []
    for l_ in lines:
        r = parse_line(l_)
        if r["kind"] == "rule" and r["type"] == "DOMAIN-SUFFIX":
            out.append("+." + r["val"])
        elif r["kind"] == "rule" and r["type"] == "DOMAIN":
            out.append(r["val"])
    return out


def to_singbox_ruleset(lines):
    """Правила → sing-box rule-set (source format JSON)."""
    d = {"domain": [], "domain_suffix": [], "domain_keyword": [], "ip_cidr": [], "domain_regex": []}
    for l_ in lines:
        r = parse_line(l_)
        if r["kind"] != "rule":
            continue
        t, v = r["type"], r["val"]
        if t == "DOMAIN": d["domain"].append(v)
        elif t == "DOMAIN-SUFFIX": d["domain_suffix"].append(v)
        elif t == "DOMAIN-KEYWORD": d["domain_keyword"].append(v)
        elif t in ("IP-CIDR", "IP-CIDR6"): d["ip_cidr"].append(v)
    return json.dumps({"version": 2, "rules": [{k: v for k, v in d.items() if v}]}, ensure_ascii=False, indent=1)


def to_xray_rules(lines, balancer="balancer"):
    """Правила (политика → тег: DIRECT=direct, REJECT*=block, прочее=balancer/proxy)."""
    buckets = OrderedDict()
    for l_ in lines:
        r = parse_line(l_)
        if r["kind"] != "rule":
            continue
        tag = "direct" if r["policy"] == "DIRECT" else "block" if r["policy"].startswith("REJECT") else "proxy"
        key = (tag, "ip" if r["type"] in ("IP-CIDR", "IP-CIDR6", "GEOIP") else "domain" if r["type"].startswith("DOMAIN") else None)
        if not key[1]:
            continue
        v = {"DOMAIN-SUFFIX": "domain:" + r["val"], "DOMAIN": "full:" + r["val"], "DOMAIN-KEYWORD": "keyword:" + r["val"],
             "IP-CIDR": r["val"], "IP-CIDR6": r["val"], "GEOIP": "geoip:" + r["val"].lower(), "DOMAIN-WILDCARD": "regexp:" + fnmatch.translate(r["val"])}.get(r["type"])
        if v:
            buckets.setdefault(key, []).append(v)
    rules = []
    for (tag, kind), vals in buckets.items():
        rule = {"type": "field", kind: vals}
        if tag == "proxy":
            rule["balancerTag"] = balancer
        else:
            rule["outboundTag"] = tag
        rules.append(rule)
    return rules
TKEOF_rules

tk_put routing.py << 'TKEOF_routing'
# -*- coding: utf-8 -*-
# ==========================================================================
#  routing — клиенты прокси: схемы URL для импорта подписок/роутинга/конфигов,
#  профили роутинга (Happ, v2RayTun, Xray, sing-box, Clash, Shadowrocket-подобные),
#  каталоги гео-ресурсов (geoip/geosite/ASN) и публичных DNS (IP, DoH, DoT, DoQ).
# ==========================================================================
import json, base64, re
from urllib.parse import quote

# клиент → (описание, {вид: шаблон})   {u}=URL, {q}=URL-encoded, {b}=base64(URL), {n}=name, {p}=base64(payload)
# «?» в названии — схема менее надёжна, проверьте в документации клиента
CLIENTS = {
    "Shadowrocket": {"sub": ["sub://{b}", "shadowrocket://add/sub://{b}?remarks={n}"], "config": ["shadowrocket://config/add/{u}"]},
    "Happ / Happ Plus": {"sub": ["happ://add/{u}"], "routing": ["happ://routing/add/{p}", "happ://routing/onadd/{p}"]},
    "v2RayTun": {"sub": ["v2raytun://import/{u}"], "routing": ["v2raytun://import_route/{p}"]},
    "Hiddify": {"sub": ["hiddify://import/{u}#{n}"]},
    "Streisand": {"sub": ["streisand://import/{u}"]},
    "Karing": {"sub": ["karing://install-config?url={q}&name={n}"]},
    "Clash / Mihomo / Clash Verge / FlClash": {"sub": ["clash://install-config?url={q}&name={n}"]},
    "Stash": {"sub": ["stash://install-config?url={q}"]},
    "sing-box (SFI/SFA)": {"sub": ["sing-box://import-remote-profile?url={q}#{n}"]},
    "Surge": {"sub": ["surge:///install-config?url={q}"]},
    "Loon": {"sub": ["loon://import?sub={q}"]},
    "V2Box (?)": {"sub": ["v2box://install-sub?url={q}&name={n}"]},
    "NekoBox / Nekoray (?)": {"sub": ["sn://subscription?url={q}&name={n}"]},
    "Incy (?)": {"sub": ["incy://import/{u}"]},
    "v2rayN / v2rayNG": {"sub": ["{u}   (добавить URL подписки вручную / paste the subscription URL)"]},
}


def client_links(name, kind, url="", payload="", title="toolkit"):
    """Ссылки импорта для клиента. payload — строка (JSON) для routing."""
    t = CLIENTS.get(name, {}).get(kind, [])
    p = base64.b64encode(payload.encode("utf-8")).decode("ascii") if payload else ""
    b = base64.b64encode(url.encode("utf-8")).decode("ascii") if url else ""
    return [x.format(u=url, q=quote(url, safe=""), b=b, n=quote(title), p=p) for x in t]


# ---- гео-ресурсы ----
GEO = [
    ("Loyalsoldier v2ray-rules-dat", "geoip.dat / geosite.dat", "https://github.com/Loyalsoldier/v2ray-rules-dat/releases/latest/download/geoip.dat", "https://github.com/Loyalsoldier/v2ray-rules-dat/releases/latest/download/geosite.dat"),
    ("v2fly (domain-list-community)", "geosite.dat (dlc.dat)", "", "https://github.com/v2fly/domain-list-community/releases/latest/download/dlc.dat"),
    ("v2fly geoip", "geoip.dat", "https://github.com/v2fly/geoip/releases/latest/download/geoip.dat", ""),
    ("Loyalsoldier geoip (mmdb)", "Country.mmdb / GeoLite2-ASN.mmdb", "https://github.com/Loyalsoldier/geoip/raw/release/Country.mmdb", "https://github.com/Loyalsoldier/geoip/raw/release/GeoLite2-ASN.mmdb"),
    ("Loyalsoldier surge-rules", "ruleset/*.txt (direct, proxy, reject, apple, icloud, telegramcidr...)", "https://raw.githubusercontent.com/Loyalsoldier/surge-rules/release/ruleset/", ""),
    ("MetaCubeX meta-rules-dat", "geoip.dat / geosite.dat / mmdb (mihomo)", "https://github.com/MetaCubeX/meta-rules-dat/releases/latest/download/geoip.dat", "https://github.com/MetaCubeX/meta-rules-dat/releases/latest/download/geosite.dat"),
    ("runetfreedom (RU-блокировки)", "geoip.dat / geosite.dat (ru-blocked, antifilter)", "https://github.com/runetfreedom/russia-v2ray-rules-dat/releases/latest/download/geoip.dat", "https://github.com/runetfreedom/russia-v2ray-rules-dat/releases/latest/download/geosite.dat"),
    ("hydraponique roscomvpn-geoip/geosite", "RU geo (roscomvpn)", "https://github.com/hydraponique/roscomvpn-geoip/releases/latest/download/geoip.dat", "https://github.com/hydraponique/roscomvpn-geosite/releases/latest/download/geosite.dat"),
    ("antifilter.download", "ipresolve/community/allyouneed lists", "https://antifilter.download/list/allyouneed.lst", "https://antifilter.download/list/domains.lst"),
    ("itdoginfo allow-domains", "RU services lists (inside/outside)", "https://github.com/itdoginfo/allow-domains/raw/main/Russia/inside-raw.lst", "https://github.com/itdoginfo/allow-domains/raw/main/Russia/outside-raw.lst"),
    ("blackmatrix7 ios_rule_script", "Shadowrocket/Surge/Clash rules per service", "https://github.com/blackmatrix7/ios_rule_script/tree/master/rule/Shadowrocket", ""),
    ("ACL4SSR", "Clash/SSR rule lists", "https://github.com/ACL4SSR/ACL4SSR/tree/master/Clash", ""),
    ("sing-geoip / sing-geosite (SagerNet)", "sing-box rule-set .srs", "https://github.com/SagerNet/sing-geoip/releases/latest/download/geoip.db", "https://github.com/SagerNet/sing-geosite/releases/latest/download/geosite.db"),
    ("HaGeZi DNS blocklists", "adblock/hosts/domains/rpz", "https://github.com/hagezi/dns-blocklists", ""),
    ("OISD", "big/small/nsfw (surge, domains, hosts)", "https://oisd.nl", ""),
    ("ipverse / ASN ranges", "IP ranges per ASN", "https://github.com/ipverse/asn-ip", ""),
    ("RIPEstat API (ASN/prefix)", "https://stat.ripe.net/data/announced-prefixes/data.json?resource=AS13335", "", ""),
]

# name, region, plain IPs, DoH, DoT, DoQ
DNS_CATALOG = [
    ("Cloudflare", "Global", "1.1.1.1,1.0.0.1,2606:4700:4700::1111", "https://cloudflare-dns.com/dns-query", "one.one.one.one", ""),
    ("Cloudflare Malware", "Global", "1.1.1.2,1.0.0.2", "https://security.cloudflare-dns.com/dns-query", "security.cloudflare-dns.com", ""),
    ("Cloudflare Family", "Global", "1.1.1.3,1.0.0.3", "https://family.cloudflare-dns.com/dns-query", "family.cloudflare-dns.com", ""),
    ("Google", "Global", "8.8.8.8,8.8.4.4,2001:4860:4860::8888", "https://dns.google/dns-query", "dns.google", ""),
    ("Quad9", "Global/CH", "9.9.9.9,149.112.112.112,2620:fe::fe", "https://dns.quad9.net/dns-query", "dns.quad9.net", ""),
    ("Quad9 unfiltered", "Global/CH", "9.9.9.10,149.112.112.10", "https://dns10.quad9.net/dns-query", "dns10.quad9.net", ""),
    ("AdGuard", "Global/CY", "94.140.14.14,94.140.15.15", "https://dns.adguard-dns.com/dns-query", "dns.adguard-dns.com", "quic://dns.adguard-dns.com"),
    ("AdGuard unfiltered", "Global/CY", "94.140.14.140,94.140.14.141", "https://unfiltered.adguard-dns.com/dns-query", "unfiltered.adguard-dns.com", "quic://unfiltered.adguard-dns.com"),
    ("AdGuard family", "Global/CY", "94.140.14.15,94.140.15.16", "https://family.adguard-dns.com/dns-query", "family.adguard-dns.com", "quic://family.adguard-dns.com"),
    ("Yandex basic", "RU", "77.88.8.8,77.88.8.1", "https://common.dot.dns.yandex.net/dns-query", "common.dot.dns.yandex.net", ""),
    ("Yandex safe", "RU", "77.88.8.88,77.88.8.2", "https://safe.dot.dns.yandex.net/dns-query", "safe.dot.dns.yandex.net", ""),
    ("Yandex family", "RU", "77.88.8.7,77.88.8.3", "https://family.dot.dns.yandex.net/dns-query", "family.dot.dns.yandex.net", ""),
    ("SkyDNS", "RU", "193.58.251.251", "", "", ""),
    ("Comss.one DNS", "RU/EU", "83.220.169.155,212.109.195.93", "https://dns.comss.one/dns-query", "dns.comss.one", ""),
    ("Mullvad", "SE", "194.242.2.2,194.242.2.3", "https://dns.mullvad.net/dns-query", "dns.mullvad.net", ""),
    ("Mullvad adblock", "SE", "194.242.2.3", "https://adblock.dns.mullvad.net/dns-query", "adblock.dns.mullvad.net", ""),
    ("NextDNS", "Global", "45.90.28.0,45.90.30.0", "https://dns.nextdns.io/<id>", "<id>.dns.nextdns.io", "quic://dns.nextdns.io"),
    ("ControlD free", "Global", "76.76.2.0,76.76.10.0", "https://freedns.controld.com/p0", "p0.freedns.controld.com", "quic://p0.freedns.controld.com"),
    ("ControlD ads+trackers", "Global", "76.76.2.2,76.76.10.2", "https://freedns.controld.com/p2", "p2.freedns.controld.com", "quic://p2.freedns.controld.com"),
    ("OpenDNS", "US", "208.67.222.222,208.67.220.220", "https://doh.opendns.com/dns-query", "dns.opendns.com", ""),
    ("OpenDNS FamilyShield", "US", "208.67.222.123,208.67.220.123", "https://doh.familyshield.opendns.com/dns-query", "", ""),
    ("CleanBrowsing security", "US", "185.228.168.9,185.228.169.9", "https://doh.cleanbrowsing.org/doh/security-filter/", "security-filter-dns.cleanbrowsing.org", ""),
    ("DNS.SB", "DE/Global", "185.222.222.222,45.11.45.11", "https://doh.dns.sb/dns-query", "dot.sb", ""),
    ("DNS0.eu", "EU", "193.110.81.0,185.253.5.0", "https://dns0.eu", "dns0.eu", "quic://dns0.eu"),
    ("LibreDNS", "DE", "116.202.176.26", "https://doh.libredns.gr/dns-query", "dot.libredns.gr", ""),
    ("Digitale Gesellschaft", "CH", "185.95.218.42,185.95.218.43", "https://dns.digitale-gesellschaft.ch/dns-query", "dns.digitale-gesellschaft.ch", ""),
    ("Switch.ch", "CH", "130.59.31.248,130.59.31.251", "https://dns.switch.ch/dns-query", "dns.switch.ch", ""),
    ("Applied Privacy", "AT", "", "https://doh.applied-privacy.net/query", "dot1.applied-privacy.net", ""),
    ("DNSForge", "DE", "176.9.93.198,176.9.1.117", "https://dnsforge.de/dns-query", "dnsforge.de", ""),
    ("Hurricane Electric", "US", "74.82.42.42", "", "", ""),
    ("Verisign", "US", "64.6.64.6,64.6.65.6", "", "", ""),
    ("Level3 / Lumen", "US", "4.2.2.1,4.2.2.2", "", "", ""),
    ("AliDNS", "CN", "223.5.5.5,223.6.6.6", "https://dns.alidns.com/dns-query", "dns.alidns.com", "quic://dns.alidns.com:853"),
    ("DNSPod (Tencent)", "CN", "119.29.29.29,119.28.28.28", "https://doh.pub/dns-query", "dot.pub", ""),
    ("360 DNS", "CN", "101.226.4.6,218.30.118.6", "https://doh.360.cn/dns-query", "dot.360.cn", ""),
    ("TWNIC Quad101", "TW", "101.101.101.101,101.102.103.104", "https://dns.twnic.tw/dns-query", "101.101.101.101", ""),
    ("Cloudflare (Tor-friendly)", "Global", "", "https://dns4torpnlfs2ifuz2s2yf3fc7rdmsbhm6rw75euj35pac6ap25zgqad.onion/dns-query", "", ""),
]
TKEOF_routing

tk_put launcher.py << 'TKEOF_launcher'
# -*- coding: utf-8 -*-
# ==========================================================================
#  Launcher — главное меню: инструменты сгруппированы по назначению (анализ / конструкторы / сеть /
#  данные / система), запуск отдельными процессами, настройки по разделам, статистика,
#  среда/ремонт/обновление, гид. Выход из инструмента возвращает сюда, а не закрывает программу.
# ==========================================================================
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from tkcore import *

# (ключ, файл, RU, EN, описание RU, описание EN) ; ("--", None, заголовок...) — раздел
TOOLS = [
    ("--", None, "Анализ", "Analysis", "", ""),
    ("1", "spylog.py", "SpyLog", "SpyLog", "логи трафика, различия полей", "traffic logs, field diffs"),
    ("2", "sqlitetxt.py", "SQLiteTXT", "SQLiteTXT", "DNS/прокси-логи, логи клиентов", "DNS/proxy logs, client logs"),
    ("3", "listlab.py", "ListLab", "ListLab", "большие тексты, rule-set, политики", "big texts, rule-sets, policies"),
    ("4", "decoder.py", "Decoder", "Decoder", "декодер base64/gzip/…", "base64/gzip/… decoder"),
    ("--", None, "Конструкторы", "Builders", "", ""),
    ("5", "scriptforge.py", "ScriptForge", "ScriptForge", "JS-скрипты req/res", "req/res JS scripts"),
    ("6", "configforge.py", "ConfigForge", "ConfigForge", "конфиги и модули", "configs and modules"),
    ("7", "subman.py", "SubManager", "SubManager", "серверы, подписки, Xray/sing-box/Clash", "servers, subs, Xray/sing-box/Clash"),
    ("8", "adblock.py", "AdBlock", "AdBlock", "блок-листы и rule-set", "blocklists and rule-sets"),
    ("9", "regexb.py", "RegexBuilder", "RegexBuilder", "regex для URL и доменов", "regex for URLs and domains"),
    ("--", None, "Сеть", "Network", "", ""),
    ("10", "netcenter.py", "Сеть", "Network", "прокси, DNS, TLS, диагностика", "proxy, DNS, TLS, diagnostics"),
    ("11", "netdiag.py", "Тест сервисов", "Service test", "ТСПУ, SNI, 16 КБ, история", "DPI, SNI, 16KB, history"),
    ("--", None, "Данные", "Data", "", ""),
    ("12", "filemgr.py", "Файлы", "Files", "файловый менеджер", "file manager"),
    ("13", "vault.py", "Vault", "Vault", "шифрование файлов", "file encryption"),
    ("14", "ghapi.py", "GitHub", "GitHub", "репозиторий из консоли", "repository from the console"),
    ("15", "qr.py", "QR", "QR", "QR для подписок и ссылок", "QR for subscriptions & links"),
]
CRASHES = {}


def status_line():
    e = env_info()
    px = ST.net("proxy")
    return "%s %s · py %s%s · %s · DNS:%s%s" % (c(U("◆", "*"), accent()), e["env"], e["python"], (" · alpine " + e["alpine"]) if e["alpine"] else "", ST.g("lang").upper(), ST.net("dns_mode"), (" · " + c("proxy", WARN_C)) if px else "")


def net_dot():
    for h in ("1.1.1.1", "8.8.8.8", "77.88.8.8"):
        try:
            socket.create_connection((h, 443), 1.5).close()
            return c(U("● ", "+ "), OK_C) + L("сеть: онлайн", "network: online")
        except Exception:
            pass
    return c(U("● ", "x "), ERR_C) + L("сеть: нет связи (пункт 10)", "network: offline (item 10)")


def write_action(a):
    try:
        CONF.mkdir(parents=True, exist_ok=True)
        (CONF / "action").write_text(a)
    except Exception:
        pass


def run_proc(script, args=()):
    path = CORE / script
    if not path.exists():
        print("[!] " + L("Модуль не установлен: %s (обновите Toolkit)" % script, "Module not installed: %s (update the Toolkit)" % script))
        pause(); return
    for attempt in range(1, 3):
        t0 = time.time()
        rc = subprocess.call([sys.executable, str(path)] + list(args))
        n = ST.mem("stats", script + ":n", 0) + 1
        ST.setmem("stats", script + ":n", n); ST.setmem("stats", script + ":t", round(ST.mem("stats", script + ":t", 0) + time.time() - t0))
        if 0 <= rc < 128:
            return
        print("\n[!] " + L("Инструмент упал (код %s) — возможно, нестабильная версия Alpine/библиотеки." % rc, "Tool crashed (code %s) — possibly an unstable Alpine/library version." % rc))
        k = menu(L("Что сделать?", "What now?"), [("1", L("Повторить", "Retry"), ""), ("2", L("Починить окружение", "Repair environment"), ""), ("3", L("Пропустить", "Skip"), "")], show=False)
        if k == "1" and attempt < 2:
            continue
        if k == "2":
            write_action("repair"); raise SystemExit(0)
        return
    print("[!] " + L("Повторные попытки исчерпаны.", "Retries exhausted."))


DEFAULT_CFG_URL = "https://raw.githubusercontent.com/Krest-Neva/Shadowrocket/refs/heads/main/Configurations/Default_configuration_by_Krest-Neva.module"


def get_default_config():
    clear_screen(); hdr(L("Готовая конфигурация", "Ready-made configuration"))
    d = fetch(DEFAULT_CFG_URL, label="config")
    if not d:
        print("[!] " + L("Не удалось скачать.", "Download failed.")); pause(); return
    txt, why = decode_download(d)
    if txt is None:
        print("[!] " + why); pause(); return
    out = BASE / "Configurations" / "Default_configuration.module"
    atomic_write(out, txt)
    print("[+] %s (%s, %d %s)" % (out, fmt_size(len(txt)), len(txt.splitlines()), L("строк", "lines")))
    if clip_copy(txt):
        print("[+] " + L("Скопировано в буфер iOS", "Copied to iOS clipboard"))
    if confirm(L("Открыть в ConfigForge?", "Open in ConfigForge?")):
        run_proc("configforge.py", [str(out)])


# ---- настройки по разделам ----
def preview():
    print()
    b = Bar(100, L("Образец", "Sample"), "")
    for i in range(0, 101, 5):
        b.cur, b.speed = i, 1
        b.render(); time.sleep(0.02)
    b.close()
    with spin(L("Образец спиннера", "Spinner sample"), quiet_ok=True):
        time.sleep(0.8)


def cycle(key, opts):
    cur = ST.g(key)
    ST.set(key, opts[(opts.index(cur) + 1) % len(opts)] if cur in opts else opts[0])


def num(key, label, lo, hi, cast=int):
    v = ask("%s (%s–%s)" % (label, lo, hi), str(ST.g(key)), quit_ok=False)
    try:
        ST.set(key, max(lo, min(hi, cast(v))))
    except ValueError:
        pass


def onoff(k):
    return "on" if ST.g(k) else "off"


def settings_menu():
    while True:
        g = ST.g
        k = menu(L("Настройки", "Settings"), [
            ("1", L("Язык и вывод", "Language & output"), "%s · w=%s" % (g("lang"), g("max_width") or "auto")), ("2", L("Оформление и цвета", "Look & colors"), "%s · %s" % (g("theme"), g("color"))),
            ("3", L("Анимации и спиннеры", "Animations & spinners"), onoff("anim")), ("4", L("Прогресс-бары", "Progress bars"), g("bar_style")),
            ("5", L("Поведение", "Behavior"), ""), ("6", L("Данные и память", "Data & memory"), ""), ("7", L("Обновление", "Update"), "")], tool="launcher", clear_ok=True)
        if k == "q":
            return
        if k == "1":
            while True:
                s = menu(L("Язык и вывод", "Language & output"), [("1", L("Язык / Language", "Language / Язык"), g("lang")), ("2", L("Макс. ширина текста (0 — авто)", "Max text width (0 = auto)"), str(g("max_width"))),
                                                               ("3", L("Очищать экран при смене меню", "Clear screen between menus"), onoff("clear")), ("4", L("Юникод-символы (иначе ASCII)", "Unicode glyphs (else ASCII)"), onoff("unicode")),
                                                               ("5", L("Подробные сообщения об ошибках", "Verbose error messages"), onoff("verbose"))], show=True)
                if s == "q": break
                if s == "1": cycle("lang", ["ru", "en"])
                elif s == "2": num("max_width", L("Ширина", "Width"), 0, 200)
                elif s == "3": ST.set("clear", not g("clear"))
                elif s == "4": ST.set("unicode", not g("unicode"))
                elif s == "5": ST.set("verbose", not g("verbose"))
        elif k == "2":
            while True:
                s = menu(L("Оформление и цвета", "Look & colors"), [("1", L("Тема", "Theme"), g("theme")), ("2", L("Режим цвета", "Color mode"), g("color"))], show=True)
                if s == "q": break
                cycle("theme" if s == "1" else "color", list(CHOICES["theme" if s == "1" else "color"]))
                preview()
        elif k == "3":
            while True:
                s = menu(L("Анимации и спиннеры", "Animations & spinners"), [("1", L("Анимации", "Animations"), onoff("anim")), ("2", L("Скорость анимации", "Animation speed"), str(g("anim_speed"))),
                                                                          ("3", L("Анимация запуска (ракета)", "Launch animation"), onoff("launch_anim")), ("4", L("Стиль спиннера", "Spinner style"), g("spinner"))], show=True)
                if s == "q": break
                if s == "1": ST.set("anim", not g("anim"))
                elif s == "2": num("anim_speed", L("Скорость", "Speed"), 0.3, 3.0, float)
                elif s == "3": ST.set("launch_anim", not g("launch_anim"))
                elif s == "4": cycle("spinner", list(CHOICES["spinner"]))
                preview()
        elif k == "4":
            while True:
                s = menu(L("Прогресс-бары", "Progress bars"), [("1", L("Стиль", "Style"), g("bar_style")), ("2", L("Длина (0 — авто)", "Width (0 = auto)"), str(g("bar_width"))), ("3", L("Градиент", "Gradient"), onoff("bar_gradient")),
                                                             ("4", L("Что показывать: % / объём / скорость / ETA", "Show: % / size / speed / ETA"), "".join("+" if g(x) else "-" for x in ("bar_pct", "bar_size", "bar_speed", "bar_eta")))], show=True)
                if s == "q": break
                if s == "1": cycle("bar_style", list(CHOICES["bar_style"]))
                elif s == "2": num("bar_width", L("Длина", "Width"), 0, 60)
                elif s == "3": ST.set("bar_gradient", not g("bar_gradient"))
                elif s == "4":
                    st = checklist("launcher", L("Показывать", "Show"), [("bar_pct", "%", g("bar_pct")), ("bar_size", L("Объём", "Size"), g("bar_size")), ("bar_speed", L("Скорость", "Speed"), g("bar_speed")), ("bar_eta", "ETA", g("bar_eta"))])
                    for kk, vv in st.items(): ST.set(kk, vv)
                preview()
        elif k == "5":
            noloc = (CONF / "noloc").exists()
            while True:
                noloc = (CONF / "noloc").exists()
                s = menu(L("Поведение", "Behavior"), [("1", L("Подтверждать удаление", "Confirm deletions"), onoff("confirm_delete")), ("2", L("Фоновая геолокация (iSH)", "Background location (iSH)"), "off" if noloc else "on")], show=True)
                if s == "q": break
                if s == "1": ST.set("confirm_delete", not g("confirm_delete"))
                elif s == "2":
                    try:
                        (CONF / "noloc").unlink() if noloc else (CONF / "noloc").write_text("1")
                    except Exception:
                        pass
        elif k == "6":
            s = menu(L("Данные и память", "Data & memory"), [("1", L("Сбросить память инструментов (последние выборы)", "Reset tool memory (last choices)"), ""), ("2", L("Сбросить ВСЕ настройки (кроме сети)", "Reset ALL settings (except network)"), ""),
                                                           ("3", L("Сбросить сетевые настройки", "Reset network settings"), ""), ("4", L("Экспорт настроек в файл", "Export settings to a file"), ""), ("5", L("Импорт настроек из файла", "Import settings from a file"), "")], show=True)
            if s == "1" and confirm(L("Сбросить память?", "Reset memory?")): ST.clear_mem()
            elif s == "2" and confirm(L("Сбросить настройки?", "Reset settings?")):
                net = ST.d.get("net", {}); ST.d = {"net": net}; ST.save()
            elif s == "3" and confirm(L("Сбросить сеть?", "Reset network?")):
                ST.d["net"] = {}; ST.save(); dns_reset()
            elif s == "4":
                p = BASE / "Configurations" / "toolkit_settings.json"; atomic_write(p, json.dumps(ST.d, ensure_ascii=False, indent=1)); print("[+] " + str(p)); pause()
            elif s == "5":
                fs = pick_files(BASE / "Configurations", {".json"}, False)
                if fs:
                    try:
                        ST.d = json.loads(fs[0].read_text("utf-8")); ST.save(); print("[+] OK")
                    except Exception as e:
                        print("[!] %s" % e)
                    pause()
        elif k == "7":
            s = menu(L("Обновление", "Update"), [("1", L("Обновить Toolkit с GitHub", "Update Toolkit from GitHub"), ""), ("2", L("URL обновления", "Update URL"), g("update_url")[-30:])], show=True)
            if s == "1": self_update()
            elif s == "2":
                v = ask("URL", g("update_url"), quit_ok=False)
                if v.startswith("http"): ST.set("update_url", v)


def stats_screen():
    clear_screen(); hdr(L("Статистика", "Statistics"))
    rows = []
    for key, f, ru, en, *_ in TOOLS:
        if f:
            n, t = ST.mem("stats", f + ":n", 0), ST.mem("stats", f + ":t", 0)
            if n:
                rows.append([ru if ST.g("lang") == "ru" else en, str(n), fmt_dur(t)])
    table(rows, [L("Инструмент", "Tool"), L("запусков", "runs"), L("время", "time")]) if rows else print(dim(L("Пока нет данных", "No data yet")))
    print(c(L("Данные", "Data"), accent(), True))
    tot = 0
    drows = []
    for d in sorted(p for p in BASE.iterdir() if p.is_dir() and not p.name.startswith(".")):
        sz, cnt = 0, 0
        for r, _, fs in os.walk(str(d)):
            for f in fs:
                try:
                    sz += os.lstat(os.path.join(r, f)).st_size; cnt += 1
                except OSError:
                    pass
        tot += sz
        drows.append([d.name, str(cnt), fmt_size(sz)])
    table(drows, [L("Папка", "Folder"), L("файлов", "files"), L("размер", "size")])
    print("[*] %s: %s" % (L("Всего данных", "Total data"), fmt_size(tot)))
    h = []
    try:
        h = json.loads((BASE / "NetDiag" / "history.json").read_text())
    except Exception:
        pass
    print("[*] %s: %d | %s: %s | proxy: %s | DNS: %s" % (L("Тестов сети в истории", "Net tests in history"), len(h), L("лог ошибок", "error log"), fmt_size(CRASH_LOG.stat().st_size) if CRASH_LOG.exists() else "0", ST.net("proxy") or "-", ST.net("dns_mode")))
    pause()


ALPINE_VERS = ["3.18", "3.19", "3.17", "3.20", "3.21", "3.16", "3.22"]


def env_menu():
    while True:
        e = env_info()
        k = menu(L("Среда, обновление и ремонт", "Environment, update & repair"), [
            ("1", L("Самотест компонентов", "Component self-test"), "py %s" % e["python"]), ("2", L("Починить окружение (автоподбор версии Alpine)", "Repair environment (auto-pick Alpine)"), ""),
            ("3", L("Выбрать версию Alpine вручную", "Pick Alpine version manually"), e["alpine"]), ("4", L("Обновить пакеты системы", "Update system packages"), ""),
            ("5", L("Обновить Toolkit с GitHub", "Update Toolkit from GitHub"), ""), ("6", L("Переустановить модули", "Reinstall modules"), ""), ("7", L("Журнал ошибок", "Error log"), ""),
            ("8", L("Установить опциональное (nodejs, quickjs, qrencode)", "Install optional (nodejs, quickjs, qrencode)"), "")], tool="launcher")
        if k == "q":
            return
        if k == "1":
            r = subprocess.run([sys.executable, str(CORE / "tkcore.py"), "--selftest"], capture_output=True, text=True)
            for l_ in r.stdout.splitlines():
                print(c(l_, OK_C if l_.startswith("OK") else ERR_C if l_.startswith("FAIL") else WARN_C))
            pause()
        elif k == "2":
            write_action("repair"); raise SystemExit(0)
        elif k == "3":
            for i, v in enumerate(ALPINE_VERS, 1):
                print("  %s v%s" % (c("%2d" % i, accent(), True), v))
            n = ask(L("Номер версии", "Version number"), "", quit_ok=False)
            if n.isdigit() and 1 <= int(n) <= len(ALPINE_VERS):
                write_action("alpine:" + ALPINE_VERS[int(n) - 1]); raise SystemExit(0)
        elif k == "4":
            write_action("pkgupdate"); raise SystemExit(0)
        elif k == "5":
            self_update()
        elif k == "6":
            write_action("rewrite"); raise SystemExit(0)
        elif k == "7":
            try:
                print(CRASH_LOG.read_text()[-3000:])
            except Exception:
                print("[*] " + L("Журнал пуст", "Log is empty"))
            pause()
        elif k == "8":
            write_action("optional"); raise SystemExit(0)


def self_update():
    d = fetch(ST.g("update_url"), label="update")
    if not d:
        return
    txt, why = decode_download(d)
    if not txt or not txt.startswith("#!/bin/sh") or "TK_BUILD=" not in txt[:4000]:
        print("[!] " + L("Файл повреждён или это не Toolkit — обновление отменено.", "File is damaged or not a Toolkit — update cancelled.")); pause(); return
    new = re.search(r'TK_BUILD="([^"]+)"', txt)
    cur = os.environ.get("TK_BUILD", "")
    if new and new.group(1) == cur:
        print("[+] " + L("Уже установлена актуальная сборка.", "You already have the latest build.")); pause(); return
    print("[*] sha256: " + hashlib.sha256(txt.encode("utf-8")).hexdigest()[:16])
    if confirm(L("Установить обновление?", "Install the update?"), True):
        atomic_write(CONF / "Toolkit.new", txt)
        write_action("applyupdate"); raise SystemExit(0)


def first_run_lang():
    if (CONF / "lang").exists() or "lang" in ST.d:
        return
    print("\n" + c("  Language / Язык", accent(), True))
    print("  1 - Русский [по умолчанию]\n  2 - English")
    v = input("Выбор / Choice [1]: ").strip() if sys.stdin.isatty() else "1"
    ST.set("lang", "en" if v == "2" else "ru")
    try:
        (CONF / "lang").write_text(ST.g("lang"))
    except Exception:
        pass


def main():
    CONF.mkdir(parents=True, exist_ok=True)
    fix_tty()
    first_run_lang()
    ensure_dirs("AdBlock", "SQLiteTXT/Input", "SQLiteTXT/Output", "SpyLog/Input", "SpyLog/Output", "SubManager/Input", "SubManager/Output", "SubManager/Backups", "SubManager/Routing",
                "RegexBuilder/Output", "Configurations", "ScriptForge/Input", "ScriptForge/Output", "ScriptForge/Scripts", "ScriptForge/Findings", "ConfigForge/Input", "ConfigForge/Output",
                "Decoder/Input", "Decoder/Output", "ListLab/Input", "ListLab/Output", "NetDiag", "QR")
    clear_screen(); rocket_launch(); banner()
    while True:
        ru = ST.g("lang") == "ru"
        items = [(k, ru_ if ru else en, d_ru if ru else d_en) if k != "--" else ("--", ru_ if ru else en, "") for k, f, ru_, en, d_ru, d_en in TOOLS]
        items += [("--", L("Система", "System"), ""), ("16", L("Готовая конфигурация", "Ready-made config"), L("скачать и открыть", "download & open")), ("17", L("Настройки", "Settings"), L("оформление, бары, язык", "style, bars, language")),
                  ("18", L("Среда / обновление / ремонт", "Environment / update / repair"), ""), ("19", L("Статистика", "Statistics"), ""), ("20", L("Гид и инструкция", "Guide & help"), L("подробно", "detailed"))]
        clear_screen()
        print(status_line()); print(net_dot())
        k = menu(L("Главное меню", "Main menu"), items, tool="launcher", back_label=L("Выход", "Quit"), clear_ok=False)
        if k == "q":
            print("[+] " + L("До встречи!", "See you!")); return
        for key, f, *_ in TOOLS:
            if key == k and f:
                run_proc(f)
        if k == "16": get_default_config()
        elif k == "17": settings_menu()
        elif k == "18": env_menu()
        elif k == "19": stats_screen()
        elif k == "20": run_proc("guide.py")


if __name__ == "__main__":
    try:
        main()
    except (Quit, KeyboardInterrupt):
        print("\n[+] " + L("Выход.", "Bye."))
TKEOF_launcher

tk_put netcenter.py << 'TKEOF_netcenter'
# -*- coding: utf-8 -*-
# ==========================================================================
#  NetCenter — центр сети: прокси, DNS (UDP/DoH/system), IPv4/IPv6, TLS,
#  проверка связи по многим сервисам и полная диагностика.
# ==========================================================================
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from tkcore import *

TOOL = "netcenter"


# ---- показать текущие настройки сети ----
def show_current():
    n = ST.net
    rows = [[L("Прокси", "Proxy"), n("proxy") or L("выключен", "off")], ["DNS mode", n("dns_mode")],
            ["DNS UDP", n("dns_servers")], ["DoH", n("doh_url") or "-"], ["DoH fallback", str(n("doh_fallback"))],
            ["IP", n("ip_version")], ["TLS verify", str(n("verify_tls"))], ["TLS fallback", n("tls_fallback")],
            [L("Таймаут/повторы", "Timeout/retries"), "%s / %s" % (n("timeout"), n("retries"))],
            [L("Предпроверка", "Preflight"), str(n("preflight"))]]
    table(rows, [L("Параметр", "Option"), L("Значение", "Value")], [16, 40])


# ---- публичный IP по нескольким сервисам ----
def public_ip():
    for u in ("https://api.ipify.org", "https://icanhazip.com", "https://ifconfig.me/ip", "https://ipinfo.io/ip"):
        t = fetch_text(u, show=False, interactive=False, retries=1, timeout=6, quiet=True)
        if t and re.fullmatch(r"[0-9a-fA-F:.]{3,45}", t.strip()):
            return t.strip(), u
    return None, None


# ---- TCP-пинг с джиттером ----
def tcp_ping(host, port=443, n=5):
    res = []
    for _ in range(n):
        t = time.time()
        try:
            socket.create_connection((host, port), 4).close()
            res.append((time.time() - t) * 1000)
        except Exception:
            res.append(None)
        time.sleep(0.15)
    ok = [x for x in res if x is not None]
    if not ok:
        return None
    avg = sum(ok) / len(ok)
    return {"min": min(ok), "avg": avg, "max": max(ok), "loss": 100 - 100 * len(ok) // n,
            "jit": (sum(abs(x - avg) for x in ok) / len(ok))}


# ---- информация о сертификате ----
def cert_info(host):
    try:
        ctx = ssl.create_default_context()
        s = ctx.wrap_socket(socket.create_connection((host, 443), 6), server_hostname=host)
        cert = s.getpeercert()
        s.close()
        issuer = dict(x[0] for x in cert.get("issuer", ()))
        return "%s | %s" % (issuer.get("organizationName", "?"), cert.get("notAfter", "?"))
    except Exception as e:
        return "ERR " + str(e)[:50]


# ---- сравнение DNS-ответов (поиск подмены/блокировки) ----
def dns_compare(host):
    ans = {}
    ans["system"] = resolve(host, "system")
    for srv in dns_servers()[:4]:
        ans["udp " + srv] = udp_query(srv, host, 1)[0]
    for u in doh_urls()[:2]:
        try:
            ans["doh " + u.split("/")[2]] = doh_query(u, host, 1)
        except Exception:
            ans["doh " + u.split("/")[2]] = []
    return ans


# ---- полная диагностика ----
def full_diag():
    hdr(L("Полная диагностика сети", "Full network diagnostics"))
    print(c(L("1) Окружение", "1) Environment"), accent(), True))
    show_current()
    try:
        print(dim("resolv.conf: " + ", ".join(re.findall(r"nameserver\s+(\S+)", open("/etc/resolv.conf").read())) ))
    except Exception:
        pass
    for cmd in (["ip", "-brief", "addr"], ["ifconfig"]):
        if shutil.which(cmd[0]):
            try:
                out = subprocess.run(cmd, capture_output=True, text=True, timeout=8).stdout.strip().splitlines()[:6]
                print(dim("\n".join(out)))
                break
            except Exception:
                pass
    print("\n" + c(L("2) Связь с сервисами", "2) Service connectivity"), accent(), True))
    conn_report(True)
    print("\n" + c(L("3) Публичный IP", "3) Public IP"), accent(), True))
    with spin(L("Определяю IP", "Detecting IP"), quiet_ok=True):
        ip, src = public_ip()
    print(("[+] %s  %s" % (ip, dim(src))) if ip else "[!] " + L("не удалось определить", "could not detect"))
    print("\n" + c(L("4) DNS: сравнение ответов (подмена/блокировка)", "4) DNS answer comparison (spoof/block)"), accent(), True))
    for host in ("www.youtube.com", "raw.githubusercontent.com", "api.telegram.org"):
        with spin(host, quiet_ok=True):
            ans = dns_compare(host)
        sets = {tuple(sorted(v)) for v in ans.values() if v}
        print(c(host, accent(), True))
        for k, v in ans.items():
            print("   %-22s %s" % (k, ", ".join(v[:3]) if v else dim(L("нет ответа", "no answer"))))
        if len(sets) > 1:
            print("[!] " + L("ответы различаются — возможна подмена DNS", "answers differ — DNS spoofing possible"))
    print("\n" + c(L("5) TCP-пинг (потери/джиттер)", "5) TCP ping (loss/jitter)"), accent(), True))
    rows = []
    for host in ("1.1.1.1", "8.8.8.8", "9.9.9.9", "94.140.14.14"):
        with spin(host, quiet_ok=True):
            r = tcp_ping(host, 443, 5)
        rows.append([host] + (["%.0f" % r["min"], "%.0f" % r["avg"], "%.0f" % r["max"], "%.0f" % r["jit"], "%d%%" % r["loss"]] if r else ["-"] * 4 + ["100%"]))
    table(rows, ["Host", "min", "avg", "max", "jit", "loss"])
    print("\n" + c(L("6) TLS-сертификаты (признак MITM/DPI)", "6) TLS certificates (MITM/DPI hint)"), accent(), True))
    for host in ("www.google.com", "github.com", "www.youtube.com"):
        print("  %-18s %s" % (host, cert_info(host)))
    print("\n" + c(L("7) IPv6", "7) IPv6"), accent(), True))
    try:
        socket.create_connection(("2606:4700:4700::1111", 443), 4).close()
        print("[+] IPv6 OK")
    except Exception as e:
        print("[!] IPv6: " + str(e)[:50])
    print("\n" + c("8) Speed", accent(), True))
    speed_test()
    pause()


# ---- тест скорости (поток с Cloudflare, с прогресс-баром) ----
def speed_test(size=5_000_000):
    t = time.time()
    d = fetch("https://speed.cloudflare.com/__down?bytes=%d" % size, label="speed", interactive=False, retries=1, timeout=15)
    if d:
        sp = len(d) / max(0.01, time.time() - t)
        print("[+] %s: %s/s (%.1f Mbit/s)" % (L("Скорость", "Speed"), fmt_size(sp), sp * 8 / 1e6))
    else:
        print("[!] " + L("тест скорости не прошёл", "speed test failed"))


# ---- применить DNS в /etc/resolv.conf (системно для iSH) ----
def apply_resolv():
    srv = dns_servers()
    if not srv:
        print("[!] " + L("DNS-список пуст", "DNS list is empty"))
        return
    try:
        with open("/etc/resolv.conf", "w") as f:
            for s in srv:
                f.write("nameserver %s\n" % s)
        print("[+] /etc/resolv.conf: " + ", ".join(srv))
    except Exception as e:
        print("[!] %s" % e)


def toggle(key, vals):
    cur = ST.net(key)
    ST.setnet(key, vals[(vals.index(cur) + 1) % len(vals)] if cur in vals else vals[0])
    dns_reset()
    print("[+] %s = %s" % (key, ST.net(key)))


def quick_fix(url=None):
    net_trouble(url)


def main():
    ensure_dirs("Configurations")
    while True:
        n = ST.net
        k = menu(L("Центр сети", "Network center"), [
            ("1", L("Проверить связь (много сервисов)", "Connectivity test (many services)"), ""),
            ("2", L("Полная диагностика", "Full diagnostics"), ""),
            ("3", L("Прокси", "Proxy"), n("proxy") or L("выкл", "off")),
            ("4", L("DNS-серверы (шаблоны)", "DNS servers (templates)"), n("dns_servers")[:22]),
            ("5", L("DoH (шаблоны)", "DoH (templates)"), n("doh_url")[:22] or "-"),
            ("6", L("Режим DNS", "DNS mode"), n("dns_mode")), ("7", L("IPv4 / IPv6", "IPv4 / IPv6"), n("ip_version")),
            ("8", L("Проверка TLS", "TLS verify"), "on" if n("verify_tls") else "off"),
            ("9", L("Политика TLS-fallback", "TLS fallback policy"), n("tls_fallback")),
            ("10", L("Таймаут / повторы", "Timeout / retries"), "%s/%s" % (n("timeout"), n("retries"))),
            ("11", L("Предпроверка сети", "Preflight check"), "on" if n("preflight") else "off"),
            ("12", L("Записать DNS в /etc/resolv.conf", "Write DNS to /etc/resolv.conf"), ""),
            ("13", L("Тест скорости", "Speed test"), ""), ("14", L("Текущие настройки", "Current settings"), ""),
            ("15", L("Сбросить сетевые настройки", "Reset network settings"), "")], tool=TOOL)
        if k == "q":
            return
        if k == "1":
            conn_report(True); pause()
        elif k == "2":
            full_diag()
        elif k == "3":
            set_proxy_ui()
        elif k == "4":
            set_dns_ui()
        elif k == "5":
            set_doh_ui()
        elif k == "6":
            toggle("dns_mode", list(CHOICES["dns_mode"]))
        elif k == "7":
            toggle("ip_version", list(CHOICES["ip_version"]))
        elif k == "8":
            ST.setnet("verify_tls", not n("verify_tls")); print("[+] verify_tls = %s" % ST.net("verify_tls"))
        elif k == "9":
            toggle("tls_fallback", list(CHOICES["tls_fallback"]))
        elif k == "10":
            t = ask(L("Таймаут, сек", "Timeout, sec"), str(n("timeout")), quit_ok=False)
            r = ask(L("Повторов", "Retries"), str(n("retries")), quit_ok=False)
            if t.isdigit() and r.isdigit():
                ST.setnet("timeout", max(3, min(120, int(t)))); ST.setnet("retries", max(1, min(10, int(r))))
        elif k == "11":
            ST.setnet("preflight", not n("preflight"))
        elif k == "12":
            apply_resolv()
        elif k == "13":
            speed_test(); pause()
        elif k == "14":
            show_current(); pause()
        elif k == "15" and confirm(L("Сбросить?", "Reset?")):
            ST.d["net"] = {}; ST.save(); dns_reset(); print("[+] OK")


if __name__ == "__main__":
    run_tool("NetCenter", main)
TKEOF_netcenter

tk_put netdiag.py << 'TKEOF_netdiag'
# -*- coding: utf-8 -*-
# ==========================================================================
#  NetDiag — глубокая проверка доступности сервисов: много DNS (system/UDP/DoH/DoT), TCP, TLS,
#  SNI-блокировка, обрыв после ~16 КБ (ТСПУ), с прокси и без, IPv4/IPv6; внешний IP/ASN;
#  история прогонов с подписью и сравнение сетей; тест публичных DNS; IP/ASN/хост-информация;
#  сертификаты Минцифры.
# ==========================================================================
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from tkcore import *
import routing as RT
from concurrent.futures import ThreadPoolExecutor

TOOL = "netdiag"
HIST = BASE / "NetDiag" / "history.json"
# категория → [(название, хост, путь)]
SERVICES = {
    "messengers": [("Telegram", "web.telegram.org", "/"), ("Telegram API", "api.telegram.org", "/"), ("WhatsApp", "web.whatsapp.com", "/"), ("Signal", "chat.signal.org", "/"), ("Viber", "www.viber.com", "/"),
                   ("Discord", "discord.com", "/"), ("Skype", "www.skype.com", "/"), ("Zoom", "zoom.us", "/"), ("MS Teams", "teams.microsoft.com", "/"), ("Slack", "slack.com", "/"), ("Max", "max.ru", "/"),
                   ("Threema", "threema.ch", "/"), ("Element/Matrix", "matrix.org", "/"), ("Google Meet", "meet.google.com", "/")],
    "social": [("Instagram", "www.instagram.com", "/"), ("Facebook", "www.facebook.com", "/"), ("X / Twitter", "x.com", "/"), ("TikTok", "www.tiktok.com", "/"), ("Reddit", "www.reddit.com", "/"),
               ("LinkedIn", "www.linkedin.com", "/"), ("Pinterest", "www.pinterest.com", "/"), ("Threads", "www.threads.net", "/"), ("Snapchat", "www.snapchat.com", "/"), ("VK", "vk.com", "/"), ("OK.ru", "ok.ru", "/"),
               ("Twitch", "www.twitch.tv", "/"), ("Medium", "medium.com", "/"), ("Quora", "www.quora.com", "/")],
    "video": [("YouTube", "www.youtube.com", "/generate_204"), ("YouTube img", "i.ytimg.com", "/"), ("googlevideo", "redirector.googlevideo.com", "/"), ("Netflix", "www.netflix.com", "/"), ("Rutube", "rutube.ru", "/"),
              ("Vimeo", "vimeo.com", "/"), ("Kinopoisk", "www.kinopoisk.ru", "/"), ("Okko", "okko.tv", "/"), ("IVI", "www.ivi.ru", "/"), ("Wink", "wink.ru", "/"), ("Kion", "kion.ru", "/"), ("Disney+", "www.disneyplus.com", "/"),
              ("Prime Video", "www.primevideo.com", "/"), ("Dzen", "dzen.ru", "/"), ("Dailymotion", "www.dailymotion.com", "/"), ("Kick", "kick.com", "/")],
    "music": [("Spotify", "open.spotify.com", "/"), ("Spotify API", "api.spotify.com", "/"), ("SoundCloud", "soundcloud.com", "/"), ("Apple Music", "music.apple.com", "/"), ("Yandex Music", "music.yandex.ru", "/"),
              ("Deezer", "www.deezer.com", "/"), ("Tidal", "tidal.com", "/"), ("Zvuk", "zvuk.com", "/"), ("VK Music", "vk.com", "/audio"), ("Last.fm", "www.last.fm", "/"), ("Bandcamp", "bandcamp.com", "/")],
    "photo": [("Google Photos", "photos.google.com", "/"), ("iCloud", "www.icloud.com", "/"), ("Imgur", "imgur.com", "/"), ("Flickr", "www.flickr.com", "/"), ("Unsplash", "unsplash.com", "/"),
              ("Yandex Disk", "disk.yandex.ru", "/"), ("Dropbox", "www.dropbox.com", "/"), ("Google Drive", "drive.google.com", "/"), ("OneDrive", "onedrive.live.com", "/"), ("Mega", "mega.nz", "/")],
    "stores": [("App Store", "apps.apple.com", "/"), ("Apple servers", "gsa.apple.com", "/"), ("Google Play", "play.google.com", "/"), ("Steam", "store.steampowered.com", "/"), ("Epic Games", "store.epicgames.com", "/"),
               ("GOG", "www.gog.com", "/"), ("MS Store", "www.microsoft.com", "/"), ("Ozon", "www.ozon.ru", "/"), ("Wildberries", "www.wildberries.ru", "/"), ("AliExpress", "www.aliexpress.com", "/"), ("Amazon", "www.amazon.com", "/"),
               ("Avito", "www.avito.ru", "/"), ("RuStore", "www.rustore.ru", "/"), ("Yandex Market", "market.yandex.ru", "/")],
    "ai_search": [("Google", "www.google.com", "/generate_204"), ("Bing", "www.bing.com", "/"), ("Yandex", "ya.ru", "/"), ("DuckDuckGo", "duckduckgo.com", "/"), ("ChatGPT", "chatgpt.com", "/"), ("OpenAI API", "api.openai.com", "/"),
                  ("Claude", "claude.ai", "/"), ("Anthropic API", "api.anthropic.com", "/"), ("Gemini", "gemini.google.com", "/"), ("Perplexity", "www.perplexity.ai", "/"), ("DeepSeek", "chat.deepseek.com", "/"),
                  ("Hugging Face", "huggingface.co", "/"), ("Copilot", "copilot.microsoft.com", "/")],
    "dev": [("GitHub", "github.com", "/"), ("GitHub raw", "raw.githubusercontent.com", "/"), ("GitLab", "gitlab.com", "/"), ("npm", "registry.npmjs.org", "/"), ("PyPI", "pypi.org", "/"), ("Docker Hub", "hub.docker.com", "/"),
            ("jsDelivr", "cdn.jsdelivr.net", "/"), ("Cloudflare", "www.cloudflare.com", "/"), ("Alpine mirror", "dl-cdn.alpinelinux.org", "/"), ("StackOverflow", "stackoverflow.com", "/"), ("Wikipedia", "www.wikipedia.org", "/")],
    "ru_services": [("Gosuslugi", "www.gosuslugi.ru", "/"), ("Nalog.ru", "www.nalog.gov.ru", "/"), ("Mos.ru", "www.mos.ru", "/"), ("Sber", "www.sberbank.ru", "/"), ("T-Bank", "www.tbank.ru", "/"), ("Alfa-Bank", "alfabank.ru", "/"),
                    ("VTB", "www.vtb.ru", "/"), ("Yandex", "yandex.ru", "/"), ("Mail.ru", "mail.ru", "/"), ("2GIS", "2gis.ru", "/"), ("HH.ru", "hh.ru", "/"), ("RBC", "www.rbc.ru", "/"), ("Lenta", "lenta.ru", "/"),
                    ("Rostelecom", "www.company.rt.ru", "/"), ("MTS", "mts.ru", "/"), ("Tele2/T2", "t2.ru", "/"), ("Megafon", "www.megafon.ru", "/")],
    "news": [("BBC", "www.bbc.com", "/"), ("Meduza", "meduza.io", "/"), ("Reuters", "www.reuters.com", "/"), ("DW", "www.dw.com", "/"), ("Novaya Gazeta", "novayagazeta.eu", "/"), ("The Insider", "theins.ru", "/"),
             ("RFE/RL", "www.svoboda.org", "/"), ("CNN", "edition.cnn.com", "/"), ("NYTimes", "www.nytimes.com", "/")],
    "vpn_infra": [("Cloudflare 1.1.1.1", "one.one.one.one", "/"), ("Google DNS", "dns.google", "/"), ("Quad9", "dns.quad9.net", "/"), ("AdGuard DNS", "dns.adguard-dns.com", "/"), ("Comss DNS", "dns.comss.one", "/"),
                  ("Speedtest", "www.speedtest.net", "/"), ("Fast.com", "fast.com", "/"), ("ipify", "api.ipify.org", "/"), ("ifconfig.me", "ifconfig.me", "/")],
}
RESOLVERS = {"system": ("system", None), "yandex": ("udp", "77.88.8.8"), "cloudflare": ("udp", "1.1.1.1"), "google": ("udp", "8.8.8.8"), "adguard": ("udp", "94.140.14.14"),
             "doh-cf": ("doh", "https://cloudflare-dns.com/dns-query"), "doh-google": ("doh", "https://dns.google/dns-query"), "doh-comss": ("doh", "https://dns.comss.one/dns-query"), "dot-cf": ("dot", "1.1.1.1"), "dot-quad9": ("dot", "9.9.9.9")}
PROFILES = {"quick": ["system"], "standard": ["system", "yandex", "doh-cf"], "deep": ["system", "yandex", "google", "doh-cf", "doh-comss", "dot-cf"]}
OK, WARN, BAD = "✓", "~", "✗"


def dot_query(server, host, qt=1, timeout=5):
    """DNS-over-TLS (порт 853)."""
    tid, pkt = build_query(host, qt)
    s = socket.create_connection((server, 853), timeout)
    try:
        ss = ssl._create_unverified_context().wrap_socket(s, server_hostname=server)
        ss.sendall(struct.pack(">H", len(pkt)) + pkt)
        ln_ = struct.unpack(">H", ss.recv(2))[0]
        data = b""
        while len(data) < ln_:
            ch = ss.recv(ln_ - len(data))
            if not ch:
                break
            data += ch
        return parse_response(data, tid, qt)
    finally:
        s.close()


def res_one(host, rname):
    mode, arg = RESOLVERS[rname]
    t = time.time()
    try:
        if mode == "system":
            ips = resolve(host, "system")
        elif mode == "udp":
            ips = udp_query(arg, host, 1, 3)[0]
        elif mode == "doh":
            ips = doh_query(arg, host, 1, 6)
        else:
            ips = dot_query(arg, host, 1, 5)
    except Exception:
        ips = []
    return ips, round((time.time() - t) * 1000)


def deep_conn(host, ip, path="/", sni=True, kb=24, pad_kb=0, timeout=6):
    """TCP→TLS→HTTP; читает до kb КБ ответа и (опц.) отправляет pad_kb КБ заголовков. Возвращает (код, детали)."""
    t0 = time.time()
    try:
        s = socket.create_connection((ip, 443), timeout)
    except socket.timeout:
        return "tcp-tmo", ""
    except Exception as e:
        return "tcp", str(e)[:30]
    try:
        try:
            ss = ssl._create_unverified_context().wrap_socket(s, server_hostname=host if sni else None)
        except Exception as e:
            return ("tls" if sni else "tls-nosni"), str(e)[:30]
        req = "GET %s HTTP/1.1\r\nHost: %s\r\nUser-Agent: Mozilla/5.0\r\nAccept: */*\r\nAccept-Encoding: identity\r\n%sConnection: close\r\n\r\n" % (
            path, host, ("X-Pad: " + "A" * (pad_kb * 1024) + "\r\n") if pad_kb else "")
        try:
            ss.sendall(req.encode())
        except Exception as e:
            return "cut-up", str(e)[:30]
        ss.settimeout(timeout)
        got, status = 0, ""
        try:
            while got < kb * 1024:
                ch = ss.recv(8192)
                if not ch:
                    break
                if not status:
                    m = re.match(rb"HTTP/\d\.?\d? (\d{3})", ch)
                    status = m.group(1).decode() if m else "?"
                got += len(ch)
        except socket.timeout:
            return ("cut-stall" if got >= 8000 else "http-tmo"), "%dB" % got
        except (ConnectionResetError, ssl.SSLError, OSError) as e:
            return ("cut-reset" if got >= 8000 else "reset"), "%dB" % got
        return ("ok" if status and status[0] in "123" else "http" + status if status else "noresp"), "%s %dB %dms" % (status, got, (time.time() - t0) * 1000)
    finally:
        s.close()


def test_service(svc, resolvers, deep, via_proxy):
    name, host, path = svc
    out = {}
    first_ip = None
    for r in resolvers:
        ips, ms = res_one(host, r)
        out["dns:" + r] = "ok" if ips else "dns"
        first_ip = first_ip or (ips[0] if ips and ":" not in ips[0] else None)
    if not first_ip:
        return out
    out["tls"], _ = deep_conn(host, first_ip, path, True, 2)
    if deep:
        fake, _ = deep_conn(host, first_ip, path, False, 2) if out["tls"] != "ok" else ("-", "")
        if out["tls"] in ("tls", "reset", "tcp-tmo") and fake == "ok":
            out["tls"] = "sni-block"
        out["down24k"], _ = deep_conn(host, first_ip, path, True, 24)
        out["up20k"], _ = deep_conn(host, first_ip, path, True, 2, 20)
    return out


def fmt_res(v):
    if v in ("ok", "-"):
        return c(OK, OK_C)
    if v.startswith("http") and v[4:5].isdigit():
        return c(WARN + v[4:], WARN_C)
    if v in ("sni-block", "cut-stall", "cut-reset", "cut-up"):
        return c(v, ERR_C, True)
    return c(BAD + v[:5], ERR_C)


def ext_ip():
    """Внешний IP/страна/ASN по нескольким сервисам."""
    for u in ("http://ip-api.com/json/?fields=status,query,country,countryCode,as,org,isp", "https://ipinfo.io/json", "https://api.ipify.org?format=json"):
        t = fetch_text(u, show=False, interactive=False, retries=1, timeout=6, quiet=True)
        try:
            d = json.loads(t)
            return {"ip": d.get("query") or d.get("ip"), "country": d.get("countryCode") or d.get("country"), "asn": d.get("as") or d.get("org"), "isp": d.get("isp") or d.get("org")}
        except Exception:
            continue
    return {}


def run_matrix():
    cats = list(SERVICES)
    for i, k in enumerate(cats, 1):
        print("  %s %-12s %d" % (c("%2d" % i, accent(), True), k, len(SERVICES[k])))
    sel = ask_multi(L("Категории (1,3 / all)", "Categories (1,3 / all)"), len(cats), ST.mem(TOOL, "cats", "all"))
    if not sel:
        return
    ST.setmem(TOOL, "cats", ",".join(map(str, sel)))
    prof = ask(L("Профиль: quick / standard / deep", "Profile: quick / standard / deep"), ST.mem(TOOL, "profile", "standard"), quit_ok=False)
    prof = prof if prof in PROFILES else "standard"
    ST.setmem(TOOL, "profile", prof)
    svcs = [s for i in sel for s in SERVICES[cats[i - 1]]]
    res_list, deep = PROFILES[prof], prof == "deep"
    px = ST.net("proxy")
    modes = [("direct", "")] + ([("proxy", px)] if px and deep else [])
    results, total = {}, len(svcs) * len(modes)
    bar = Bar(total, "net-test", "")
    saved_proxy = px
    done = 0
    try:
        for mname, mpx in modes:
            ST.d.setdefault("net", {})["proxy"] = "" if mname == "direct" else mpx           # временно (не сохраняется)
            with ThreadPoolExecutor(max_workers=6) as ex:
                futs = {ex.submit(test_service, s, res_list, deep, mname == "proxy"): s for s in svcs}
                for f, s in futs.items():
                    try:
                        results.setdefault(s[0], {})[mname] = f.result()
                    except Exception as e:
                        results.setdefault(s[0], {})[mname] = {"tls": "err"}
                    done += 1; bar.update(done)
    finally:
        ST.d.setdefault("net", {})["proxy"] = saved_proxy
    bar.close()
    heads = ["Service"] + [r[:5] for r in res_list] + ["TLS"] + (["24k", "up20"] if deep else [])
    rows = []
    for s in svcs:
        d = results.get(s[0], {}).get("direct", {})
        rows.append([s[0]] + [fmt_res(d.get("dns:" + r, "dns")) for r in res_list] + [fmt_res(d.get("tls", "dns"))] + ([fmt_res(d.get("down24k", "dns")), fmt_res(d.get("up20k", "dns"))] if deep else []))
    table(rows, heads)
    if len(modes) > 1:
        print(c(L("Через прокси:", "Via proxy:"), accent(), True))
        table([[s[0], fmt_res(results[s[0]]["proxy"].get("tls", "-")), fmt_res(results[s[0]]["proxy"].get("down24k", "-"))] for s in svcs], ["Service", "TLS", "24k"])
    bad = [s[0] for s in svcs if results.get(s[0], {}).get("direct", {}).get("tls", "dns") != "ok"]
    print(("[!] " if bad else "[+] ") + L("Недоступно/ограничено: %d из %d" % (len(bad), len(svcs)), "Unavailable/limited: %d of %d" % (len(bad), len(svcs))) + (": " + ", ".join(bad[:12]) if bad else ""))
    with spin(L("Определяю внешний IP", "Detecting external IP"), quiet_ok=True):
        ip = ext_ip()
    print("[*] %s: %s" % (L("Внешний IP", "External IP"), ", ".join("%s=%s" % kv for kv in ip.items() if kv[1])))
    if confirm(L("Подписать и сохранить результат в историю?", "Label and save this run to history?"), True):
        label = ask(L("Подпись (например: Wi-Fi дом / МТС LTE / VPN вкл)", "Label (e.g. Home Wi-Fi / LTE / VPN on)"), "", quit_ok=False) or now_stamp()
        h = load_hist()
        h.append({"label": label, "ts": time.strftime("%Y-%m-%d %H:%M"), "profile": prof, "ip": ip, "proxy": saved_proxy, "dns_mode": ST.net("dns_mode"),
                  "res": {n: v.get("direct", {}) for n, v in results.items()}})
        save_hist(h); print("[+] " + L("Сохранено", "Saved"))


def load_hist():
    try:
        return json.loads(HIST.read_text("utf-8"))
    except Exception:
        return []


def save_hist(h):
    atomic_write(HIST, json.dumps(h, ensure_ascii=False, indent=1))


def history_menu():
    h = load_hist()
    if not h:
        print("[!] " + L("История пуста", "History is empty")); return
    for i, x in enumerate(h, 1):
        bad = sum(1 for v in x["res"].values() if v.get("tls") not in ("ok", None))
        print("  %s %-24s %s  IP:%s  %s" % (c("%2d" % i, accent(), True), trunc(x["label"], 24), dim(x["ts"]), (x.get("ip") or {}).get("ip", "?"), c(L("проблем: %d" % bad, "issues: %d" % bad), ERR_C if bad else OK_C)))
    k = ask(L("Номер для просмотра / два номера через запятую для сравнения / d — удалить", "# to view / two numbers to compare / d = delete"), "", quit_ok=False)
    if k.lower() == "d":
        n = ask(L("Номер", "Number"), "", quit_ok=False)
        if n.isdigit() and 1 <= int(n) <= len(h):
            h.pop(int(n) - 1); save_hist(h)
        return
    try:
        nums = [int(x) for x in k.split(",") if x.strip()]
    except ValueError:
        return
    if len(nums) == 1 and 1 <= nums[0] <= len(h):
        x = h[nums[0] - 1]
        table([[n, fmt_res(v.get("tls", "-")), fmt_res(v.get("down24k", "-")), fmt_res(v.get("up20k", "-"))] for n, v in x["res"].items()], ["Service", "TLS", "24k", "up20"])
    elif len(nums) == 2 and all(1 <= n <= len(h) for n in nums):
        a, b = h[nums[0] - 1], h[nums[1] - 1]
        print(c("%s  ⇄  %s" % (a["label"], b["label"]), accent(), True))
        rows = []
        for n in sorted(set(a["res"]) | set(b["res"])):
            ta, tb = a["res"].get(n, {}).get("tls", "-"), b["res"].get(n, {}).get("tls", "-")
            if ta != tb:
                rows.append([n, fmt_res(ta), fmt_res(tb)])
        table(rows, ["Service", a["label"][:10], b["label"][:10]]) if rows else print("[+] " + L("Различий нет", "No differences"))


def dns_catalog_test():
    host = ask(L("Домен для проверки", "Domain to test"), "www.youtube.com", quit_ok=False)
    kinds = ask(L("Что проверять: u UDP, h DoH, t DoT (например uht)", "Check: u UDP, h DoH, t DoT (e.g. uht)"), "uh", quit_ok=False)
    rows, jobs = [], []
    def work(e):
        name, reg, ips, doh, dot, doq = e
        r = [name, reg]
        ip1 = ips.split(",")[0] if ips else ""
        for kind, arg, fn in (("u", ip1, lambda a: udp_query(a, host, 1, 3)[0]), ("h", doh, lambda a: doh_query(a, host, 1, 6)), ("t", dot, lambda a: dot_query(a, host, 1, 5))):
            if kind not in kinds:
                continue
            if not arg or arg.startswith("<") or "<id>" in arg:
                r.append("-"); continue
            t = time.time()
            try:
                a = fn(arg)
                r.append("%dms" % ((time.time() - t) * 1000) if a else "empty")
            except Exception:
                r.append("fail")
        return r + ["quic" if doq else ""]
    bar = Bar(len(RT.DNS_CATALOG), "dns", "")
    with ThreadPoolExecutor(max_workers=6) as ex:
        for i, r in enumerate(ex.map(work, RT.DNS_CATALOG), 1):
            rows.append(r); bar.update(i)
    bar.close()
    heads = ["DNS", "reg"] + [{"u": "UDP", "h": "DoH", "t": "DoT"}[k] for k in "uht" if k in kinds] + ["DoQ"]
    table([[x if not (isinstance(x, str) and x in ("fail", "empty")) else c(x, ERR_C) for x in r] for r in rows], heads)
    print(dim(L("DoQ (QUIC) показан каталогом: проверку выполняйте клиентом, поддерживающим QUIC.", "DoQ (QUIC) is catalog-only: test it with a QUIC-capable client.")))
    if confirm(L("Показать полный каталог адресов?", "Show the full address catalog?")):
        for e in RT.DNS_CATALOG:
            print(c(e[0], accent(), True) + dim(" [%s]" % e[1]))
            for lab, v in (("IP", e[2]), ("DoH", e[3]), ("DoT", e[4]), ("DoQ", e[5])):
                if v:
                    print("   %-4s %s" % (lab, v))


def ip_tools():
    k = menu(L("IP / ASN / хост", "IP / ASN / host"), [("1", L("Информация об IP (подсеть, ASN, страна)", "IP info (prefix, ASN, country)"), ""), ("2", L("Хост → все IP (разные DNS) + ASN", "Host → all IPs (many DNS) + ASN"), ""),
                                                    ("3", L("ASN → список префиксов (для правил)", "ASN → prefix list (for rules)"), ""), ("4", L("Строки [Host] для домена", "[Host] lines for a domain"), "")], show=False)
    if k == "1":
        ip = ask("IP", "", quit_ok=False)
        t = fetch_text("https://stat.ripe.net/data/prefix-overview/data.json?resource=%s" % ip, show=False, interactive=False, retries=1, quiet=True)
        try:
            d = json.loads(t)["data"]
            print("[+] %s  ASN: %s  %s" % (d.get("resource"), ",".join("AS%s" % a["asn"] for a in d.get("asns", [])), ", ".join(a.get("holder", "") for a in d.get("asns", []))[:60]))
        except Exception:
            pass
        t2 = fetch_text("http://ip-api.com/json/%s?fields=status,country,regionName,city,isp,org,as,reverse,proxy,hosting" % ip, show=False, interactive=False, retries=1)
        try:
            for kk, v in json.loads(t2).items():
                print("  %-10s %s" % (kk, v))
        except Exception:
            print("[!] " + L("нет данных", "no data"))
    elif k == "2":
        h = ask(L("Хост", "Host"), "", quit_ok=False)
        allips = {}
        for r in RESOLVERS:
            ips, ms = res_one(h, r)
            for ip in ips:
                allips.setdefault(ip, []).append(r)
        for ip, rs in allips.items():
            print("  %-16s %s" % (ip, dim(",".join(rs))))
        if len({tuple(sorted(v)) for v in allips.values()}) > 1 and len(allips) > 1:
            print("[*] " + L("Разные резолверы вернули разные IP (нормально для CDN; подозрительно, если один даёт 0.0.0.0/частный IP).", "Different resolvers returned different IPs (normal for CDNs; suspicious if one returns 0.0.0.0/private)."))
    elif k == "3":
        a = ask("ASN (AS13335 / 13335)", "", quit_ok=False).upper().replace("AS", "")
        t = fetch_text("https://stat.ripe.net/data/announced-prefixes/data.json?resource=AS%s" % a, interactive=False, retries=1)
        try:
            pf = [p["prefix"] for p in json.loads(t)["data"]["prefixes"]]
        except Exception:
            print("[!] " + L("нет данных", "no data")); return
        pol = ask(L("Политика для правил", "Policy for rules"), "PROXY", quit_ok=False)
        txt = "IP-ASN,%s,%s,no-resolve\n" % (a, pol) + "\n".join("IP-CIDR%s,%s,%s,no-resolve" % ("6" if ":" in p else "", p, pol) for p in pf)
        p_ = BASE / "NetDiag" / ("AS%s_rules.list" % a); atomic_write(p_, txt + "\n"); print("[+] %s (%d %s)" % (p_, len(pf), L("префиксов", "prefixes")))
    elif k == "4":
        h = ask(L("Домен", "Domain"), "", quit_ok=False)
        ips, _ = res_one(h, "doh-cf")
        ips = ips or res_one(h, "system")[0]
        print("\n".join("%s = %s" % (h, ip) for ip in ips[:3]))


def mincifra():
    urls = [("root", "https://gu-st.ru/content/lending/russian_trusted_root_ca_pem.crt"), ("sub", "https://gu-st.ru/content/lending/russian_trusted_sub_ca_pem.crt")]
    d = BASE / ".config" / "certs"; d.mkdir(parents=True, exist_ok=True)
    k = menu(L("Сертификаты Минцифры (Russian Trusted CA)", "Russian Trusted CA (Mincifra) certificates"), [("1", L("Скачать и проверить", "Download & verify"), ""), ("2", L("Включить для Toolkit (доп. CA)", "Enable for Toolkit (extra CA)"), ""),
                                                                                                             ("3", L("Установить в систему (Alpine/Debian)", "Install into system store (Alpine/Debian)"), ""), ("4", L("Выключить доп. CA", "Disable extra CA"), "")], show=True)
    if k == "1":
        pem = ""
        for nm, u in urls:
            raw = fetch(u, label=nm, interactive=True)
            if raw and b"BEGIN CERTIFICATE" in raw:
                (d / ("russian_%s.crt" % nm)).write_bytes(raw); pem += raw.decode() + "\n"
                der = base64.b64decode(re.sub(r"-----.*?-----|\s", "", raw.decode(), flags=re.S).encode()[:100000] + b"==") if False else b""
                print("[+] %s  sha256(file)=%s" % (nm, hashlib.sha256(raw).hexdigest()[:32]))
            else:
                print("[!] %s: %s" % (nm, L("повреждён или не PEM", "damaged or not PEM")))
        if pem:
            atomic_write(d / "russian_bundle.pem", pem); print("[*] " + L("Сверьте отпечатки с официальным сайтом (gosuslugi.ru/crt) перед установкой.", "Compare fingerprints with the official site (gosuslugi.ru/crt) before installing."))
    elif k == "2":
        if (d / "russian_bundle.pem").exists():
            ST.setnet("extra_ca", str(d / "russian_bundle.pem")); print("[+] " + L("Включено", "Enabled"))
        else:
            print("[!] " + L("Сначала скачайте (пункт 1)", "Download first (item 1)"))
    elif k == "3":
        try:
            for f in d.glob("russian_*.crt"):
                shutil.copy(str(f), "/usr/local/share/ca-certificates/%s" % f.name) if os.path.isdir("/usr/local/share/ca-certificates") else (os.makedirs("/usr/local/share/ca-certificates", exist_ok=True), shutil.copy(str(f), "/usr/local/share/ca-certificates/%s" % f.name))
            r = subprocess.run(["update-ca-certificates"], capture_output=True, text=True)
            print("[+] " + (r.stdout.strip().splitlines() or ["OK"])[-1] if r.returncode == 0 else "[!] " + r.stderr[:100])
        except Exception as e:
            print("[!] %s" % e)
    elif k == "4":
        ST.setnet("extra_ca", ""); print("[+] OK")


def main():
    ensure_dirs("NetDiag")
    while True:
        k = menu(L("Диагностика сервисов", "Service diagnostics"), [
            ("1", L("Тест доступности сервисов (матрица)", "Service availability test (matrix)"), L("много DNS, SNI, 16 КБ, прокси", "many DNS, SNI, 16KB, proxy")),
            ("2", L("История и сравнение сетей", "History & network comparison"), ""), ("3", L("Тест публичных DNS (UDP/DoH/DoT) и каталог", "Public DNS test (UDP/DoH/DoT) & catalog"), ""),
            ("4", L("IP / ASN / хост", "IP / ASN / host"), ""), ("5", L("Свой список сайтов", "Custom site list"), ""), ("6", L("Сертификаты Минцифры", "Mincifra certificates"), ""),
            ("7", L("Георесурсы (geoip/geosite/ASN) — ссылки", "Geo resources (geoip/geosite/ASN) links"), ""), ("8", L("Ссылки импорта для клиентов", "Client import links"), "")], tool=TOOL)
        if k == "q":
            return
        try:
            if k == "1": run_matrix()
            elif k == "2": history_menu()
            elif k == "3": dns_catalog_test()
            elif k == "4": ip_tools()
            elif k == "5":
                hs = [x.strip() for x in ask(L("Хосты через запятую", "Hosts, comma"), "", quit_ok=False).split(",") if x.strip()]
                SERVICES["custom"] = [(h, h, "/") for h in hs]; run_matrix() if hs else None
            elif k == "6": mincifra()
            elif k == "7":
                for n, d_, a, b in RT.GEO:
                    print(c(n, accent(), True) + " " + dim(d_))
                    for u in (a, b):
                        if u:
                            print("   " + u)
            elif k == "8":
                names = list(RT.CLIENTS)
                for i, n in enumerate(names, 1):
                    print("  %s %s" % (c("%2d" % i, accent(), True), n))
                n = ask(L("Клиент №", "Client #"), "", quit_ok=False)
                if n.isdigit() and 1 <= int(n) <= len(names):
                    url = ask(L("URL подписки/конфига", "Subscription/config URL"), "", quit_ok=False)
                    for kind in RT.CLIENTS[names[int(n) - 1]]:
                        for lnk in RT.client_links(names[int(n) - 1], kind, url, "", "toolkit"):
                            print("  [%s] %s" % (kind, lnk))
                    print(dim(L("QR: используйте пункт QR в меню данных.", "QR: use the QR item in the data menu.")))
        except KeyboardInterrupt:
            print("\n[*] " + L("Отменено", "Cancelled"))
        pause()


if __name__ == "__main__":
    run_tool("NetDiag", main)
TKEOF_netdiag

tk_put filemgr.py << 'TKEOF_filemgr'
# -*- coding: utf-8 -*-
# ==========================================================================
#  FileManager — просмотр и правка папок/файлов, в том числе «битых»:
#  удаление с исправлением прав, нечитаемые имена, просмотр текста/hex, поиск,
#  копирование/перемещение, права, размеры папок, создание каталогов.
# ==========================================================================
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from tkcore import *

TOOL = "filemgr"


# ---- безопасное имя для показа (битые байты → ?) ----
def shown(name):
    return os.fsencode(name).decode("utf-8", "replace") if isinstance(name, str) else name.decode("utf-8", "replace")


# ---- размер каталога (рекурсивно, устойчиво к ошибкам) ----
def dir_size(p, limit=200000):
    tot, cnt = 0, 0
    for root, dirs, files in os.walk(p, onerror=lambda e: None):
        for f in files:
            cnt += 1
            try:
                tot += os.lstat(os.path.join(root, f)).st_size
            except OSError:
                pass
            if cnt > limit:
                return tot, cnt
    return tot, cnt


# ---- содержимое каталога ----
def entries(path):
    out = []
    try:
        with os.scandir(path) as it:
            for e in it:
                try:
                    isd = e.is_dir(follow_symlinks=False)
                    st = e.stat(follow_symlinks=False)
                    out.append((e.name, isd, st.st_size, st.st_mtime, e.is_symlink(), oct(st.st_mode)[-3:]))
                except OSError:
                    out.append((e.name, False, -1, 0, False, "???"))
    except OSError as ex:
        print("[!] %s" % ex)
    return sorted(out, key=lambda x: (not x[1], x[0].lower()))


def show(path, items, page, per):
    hdr(L("Файловый менеджер", "File manager"), str(path))
    chunk = items[page * per:(page + 1) * per]
    for i, (n, isd, sz, mt, sl, mode) in enumerate(chunk, page * per + 1):
        icon = c(U("📁", "D"), WARN_C) if isd else c(U("📄", "F"), INFO_C)
        if sl:
            icon = c(U("🔗", "L"), ASK_C)
        meta = dim("%s %s" % (mode, "" if isd else fmt_size(sz) if sz >= 0 else "ERR"))
        print(" %s %s %s %s" % (c("%3d" % i, accent(), True), icon, trunc(shown(n), term_w() - 20), meta))
    pages = max(1, (len(items) + per - 1) // per)
    print(dim(L("страница %d/%d, объектов: %d", "page %d/%d, items: %d") % (page + 1, pages, len(items))))


# ---- просмотр файла: текст или hex ----
def view_file(p, hexmode=False):
    try:
        raw = open(p, "rb").read(65536)
    except Exception as e:
        print("[!] %s" % e)
        return
    if hexmode or b"\x00" in raw[:2000]:
        for off in range(0, min(len(raw), 2048), 16):
            ch = raw[off:off + 16]
            print("%06x  %-47s  %s" % (off, " ".join("%02x" % b for b in ch), "".join(chr(b) if 32 <= b < 127 else "." for b in ch)))
    else:
        txt = raw.decode("utf-8", "replace").splitlines()
        for i, l in enumerate(txt[:80], 1):
            print(c("%4d " % i, accent()) + trunc(l, term_w() - 6))
        if len(txt) > 80:
            print(dim("... +%d" % (len(txt) - 80)))
    pause()


# ---- копирование / перемещение ----
def transfer(src, dst_dir, move):
    dst = os.path.join(dst_dir, os.path.basename(src))
    if os.path.exists(dst):
        print("[!] " + L("Назначение существует", "Destination exists"))
        return
    try:
        (shutil.move if move else (shutil.copytree if os.path.isdir(src) else shutil.copy2))(src, dst)
        print("[+] OK")
    except Exception as e:
        print("[!] %s" % e)


# ---- поиск по имени ----
def find(path, pat):
    n = 0
    for root, dirs, files in os.walk(path, onerror=lambda e: None):
        for nm in dirs + files:
            if pat.lower() in nm.lower():
                print("  " + os.path.join(root, nm))
                n += 1
                if n >= 200:
                    print(dim("..."))
                    return


def main():
    start = sys.argv[1] if len(sys.argv) > 1 and os.path.isdir(sys.argv[1]) else str(BASE)
    path, page, per = os.path.abspath(start), 0, 15
    while True:
        items = entries(path)
        show(path, items, page, per)
        print(dim(L("номер — открыть | u — вверх | n/p — стр. | c — перейти по пути | r — домой", "number — open | u — up | n/p — page | c — goto path | r — home")))
        print(dim(L("d — удалить | m — переименовать | v — просмотр | x — hex | k — mkdir | cp/mv — копировать/переместить", "d — delete | m — rename | v — view | x — hex | k — mkdir | cp/mv — copy/move")))
        print(dim(L("s — размеры | f — поиск | h — права (chmod) | o — открыть Input/Output тулкита", "s — sizes | f — find | h — chmod | o — toolkit folders")))
        try:
            cmd = ask(L("Команда", "Command"), "", quit_ok=True).strip()
        except Quit:
            return
        low = cmd.lower()
        if low.isdigit() and 1 <= int(low) <= len(items):
            n, isd = items[int(low) - 1][0], items[int(low) - 1][1]
            full = os.path.join(path, n)
            if isd:
                path, page = full, 0
            else:
                view_file(full)
        elif low == "u":
            path, page = os.path.dirname(path) or "/", 0
        elif low == "n":
            page = min(page + 1, max(0, (len(items) - 1) // per))
        elif low == "p":
            page = max(0, page - 1)
        elif low == "r":
            path, page = str(HOME), 0
        elif low == "c":
            t = ask(L("Путь", "Path"), "", quit_ok=False)
            if t and os.path.isdir(t):
                path, page = os.path.abspath(t), 0
        elif low == "o":
            sub = ask(L("Папка (AdBlock/SQLiteTXT/SpyLog/SubManager/ScriptForge/RegexBuilder)", "Folder"), "SpyLog", quit_ok=False)
            t = str(BASE / sub)
            if os.path.isdir(t):
                path, page = t, 0
        elif low == "k":
            nm = ask(L("Имя папки", "Folder name"), "", quit_ok=False)
            if nm:
                os.makedirs(os.path.join(path, nm), exist_ok=True)
        elif low == "f":
            f = ask(L("Что искать", "Search for"), "", quit_ok=False)
            if f:
                find(path, f)
                pause()
        elif low == "s":
            rows = []
            for n, isd, sz, *_ in items[:60]:
                if isd:
                    s, cnt = dir_size(os.path.join(path, n))
                    rows.append([shown(n) + "/", fmt_size(s), str(cnt)])
                else:
                    rows.append([shown(n), fmt_size(sz), "1"])
            table(rows, [L("Имя", "Name"), L("Размер", "Size"), L("Файлов", "Files")])
            pause()
        elif low in ("d", "m", "v", "x", "cp", "mv", "h"):
            sel = ask_multi(L("Номера объектов", "Item numbers"), len(items)) if low in ("d", "cp", "mv") else None
            if low in ("m", "v", "x", "h"):
                v = ask(L("Номер объекта", "Item number"), "", quit_ok=False)
                if not v.isdigit() or not 1 <= int(v) <= len(items):
                    continue
                sel = [int(v)]
            if not sel:
                continue
            targets = [os.path.join(path, items[i - 1][0]) for i in sel]
            if low == "d":
                names = ", ".join(shown(os.path.basename(t)) for t in targets[:5])
                if not ST.g("confirm_delete") or confirm(L("Удалить: %s ?" % names, "Delete: %s ?" % names)):
                    for t in targets:
                        print(("[+] " if rm_tree(t) else "[!] ") + shown(os.path.basename(t)))
            elif low == "m":
                nn = ask(L("Новое имя", "New name"), "", quit_ok=False)
                if nn:
                    try:
                        os.rename(targets[0], os.path.join(path, nn))
                        print("[+] OK")
                    except Exception as e:
                        print("[!] %s" % e)
            elif low in ("v", "x"):
                if os.path.isfile(targets[0]):
                    view_file(targets[0], low == "x")
            elif low in ("cp", "mv"):
                dst = ask(L("Куда (путь)", "Destination path"), "", quit_ok=False)
                if dst and os.path.isdir(dst):
                    for t in targets:
                        transfer(t, dst, low == "mv")
            elif low == "h":
                md = ask(L("Права (например 755, 644, u+rwx)", "Mode (e.g. 755, 644, u+rwx)"), "755", quit_ok=False)
                r = subprocess.run(["chmod", md, targets[0]], capture_output=True, text=True)
                print("[+] OK" if r.returncode == 0 else "[!] " + r.stderr.strip())


if __name__ == "__main__":
    run_tool("FileManager", main)
TKEOF_filemgr

tk_put guide.py << 'TKEOF_guide'
# -*- coding: utf-8 -*-
# ==========================================================================
#  Guide — подробная инструкция для новичков (RU/EN) с постраничным просмотром.
# ==========================================================================
import sys, os, textwrap
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from tkcore import *

# (заголовок RU, заголовок EN, текст RU, текст EN)
PAGES = [
("Быстрый старт", "Quick start",
 "Toolkit — набор инструментов для сетей, прокси и анализа трафика: блок-листы, анализ логов, конструктор JS-скриптов и конфигов, подписки, регулярки.\n"
 "Всё управляется цифрами: введите номер пункта и нажмите Enter. 'q' — шаг назад / выход в главное меню (скрипт не закрывается). Ctrl+C — отмена.\n"
 "Множественный выбор: 2 | 1,3,5 | 1-3 | all. Если в поле показано [значение] — Enter оставит его. Все ваши выборы запоминаются.\n"
 "Данные лежат в папке ~/Shadowrocket (каждый инструмент — своя подпапка Input/Output).",
 "Toolkit is a set of tools for networking, proxies and traffic analysis: blocklists, log analysis, JS script and config builders, subscriptions, regexes.\n"
 "Everything is driven by numbers: type the item number and press Enter. 'q' goes back / to the main menu (the script stays open). Ctrl+C cancels.\n"
 "Multi-select: 2 | 1,3,5 | 1-3 | all. A [value] in a prompt means Enter keeps it. Your choices are remembered.\n"
 "Data lives in ~/Shadowrocket (each tool has its own Input/Output subfolder)."),
("iSH и файлы iPhone", "iSH and iPhone files",
 "iSH — эмулятор Linux (Alpine) на iPhone. Чтобы работать с файлами из «Файлов» iOS: в iSH выполните  mount -t ios . /mnt/files  и выберите папку в системном окне.\n"
 "Дальше копируйте: cp /mnt/files/log.txt ~/Shadowrocket/SpyLog/Input/  — или используйте пункт «Файлы» (файловый менеджер) прямо в Toolkit.\n"
 "Результаты (Output) копируйте обратно: cp ~/Shadowrocket/AdBlock/*.list /mnt/files/. Для iSH работает буфер обмена: результат можно скопировать в iOS-буфер (/dev/clipboard).\n"
 "Чтобы iSH не засыпал в фоне, Toolkit делает фиктивный запрос геолокации (отключается в Настройках).",
 "iSH is a Linux (Alpine) emulator for iPhone. To access iOS Files run  mount -t ios . /mnt/files  and pick a folder in the system dialog.\n"
 "Then copy: cp /mnt/files/log.txt ~/Shadowrocket/SpyLog/Input/  — or use the built-in File manager item.\n"
 "Copy results (Output) back: cp ~/Shadowrocket/AdBlock/*.list /mnt/files/. In iSH the iOS clipboard works: results can be copied there (/dev/clipboard).\n"
 "To keep iSH alive in the background Toolkit makes a dummy geolocation request (can be disabled in Settings)."),
("Управление и ввод", "Controls and input",
 "Backspace исправлен: Toolkit использует readline и приводит ввод в порядок. Если вдруг появились символы ^? или ^H — Toolkit сам их применит как удаление.\n"
 "В меню: цифра = пункт, q = назад. В запросах: Enter = значение по умолчанию. Пустой ввод в большинстве запросов = отмена.\n"
 "Оформление: Настройки → тема, стиль и длина прогресс-баров, спиннеры, анимации, ASCII-режим для простых терминалов.",
 "Backspace is fixed: Toolkit uses readline and sanitises input. Stray ^? or ^H are applied as deletions.\n"
 "In menus: number = item, q = back. In prompts: Enter = default. Empty input usually cancels.\n"
 "Look & feel: Settings → theme, progress-bar style/width, spinners, animations, ASCII mode for plain terminals."),
("AdBlock", "AdBlock",
 "Скачивает популярные блок-листы (AdGuard, OISD, HaGeZi, StevenBlock и др.), чистит их белыми списками, убирает поддомены и собирает RULE-SET для Shadowrocket (.list).\n"
 "Режимы: По умолчанию (готовый набор) и Custom (свои URL, свои белые/чёрные домены). Результат: AdBlock/REJECT_RULES*.list. Кэш ускоряет повторные запуски (ETag).\n"
 "Если список не скачался — можно повторить, сменить прокси/DNS, ввести ссылку вручную или пропустить.",
 "Downloads popular blocklists (AdGuard, OISD, HaGeZi, StevenBlack...), cleans them with whitelists, removes subdomains and builds a Shadowrocket RULE-SET (.list).\n"
 "Modes: Default (ready set) and Custom (your URLs, your white/black domains). Output: AdBlock/REJECT_RULES*.list. A cache speeds up reruns (ETag).\n"
 "If a list fails: retry, change proxy/DNS, enter a URL manually or skip."),
("SQLiteTXT", "SQLiteTXT",
 "Превращает базы SQLite (например журнал Shadowrocket) в читаемый текст, CSV или JSONL. Положите .db в SQLiteTXT/Input. Есть фильтр по ключевым словам, дедупликация по URL, сортировка по политике DIRECT/PROXY/REJECT и статистика по доменам.",
 "Converts SQLite databases (e.g. the Shadowrocket log) into readable text, CSV or JSONL. Put .db files into SQLiteTXT/Input. Includes keyword filter, URL dedupe, policy sorting (DIRECT/PROXY/REJECT) and domain statistics."),
("SpyLog — анализ трафика", "SpyLog — traffic analysis",
 "Читает логи модуля Spy (блоки [Spylog] ... +---). Умеет: извлекать блоки, сравнивать файлы/группы, искать различия В ПОЛЯХ JSON (с расшифровкой base64/gzip/percent), искать значение по всем ответам, считать статистику, маскировать токены перед публикацией.\n"
 "Найденные различия сохраняются как «находки» и одним нажатием передаются в ScriptForge.",
 "Reads Spy module logs (blocks [Spylog] ... +---). It can extract blocks, compare files/groups, find JSON FIELD differences (decoding base64/gzip/percent), search a value across responses, compute stats and mask tokens before sharing.\n"
 "Findings are saved and can be sent to ScriptForge in one tap."),
("ScriptForge — JS-скрипты", "ScriptForge — JS scripts",
 "Конструктор скриптов Shadowrocket: типы http-request, http-response, cron, event, dns, rule, generic; движки auto/jsc/webview.\n"
 "Порядок: 1) загрузите образец (лог, файл, вставка) — Toolkit сам раскодирует base64/gzip и т.п.; 2) в «Поля» выберите, что менять; 3) добавьте операции (установить, удалить, regex, заголовки, статус, mock, редирект); 4) сгенерируйте JS — он сам перекодирует тело обратно; 5) получите готовые блоки [Script] и [MITM]; 6) проверьте в node/qjs.\n"
 "Шаблоны универсальны (заголовки, JSON-патч, mock, редирект, блок, cron, event). Пишите скрипты только для своего трафика и в рамках правил сервисов.",
 "Shadowrocket script builder: http-request, http-response, cron, event, dns, rule, generic; engines auto/jsc/webview.\n"
 "Flow: 1) load a sample (log, file, paste) — Toolkit decodes base64/gzip etc.; 2) pick fields to change in 'Fields'; 3) add operations (set, delete, regex, headers, status, mock, redirect); 4) generate JS — it re-encodes the body back; 5) get ready [Script] and [MITM] blocks; 6) test in node/qjs.\n"
 "Templates are generic (headers, JSON patch, mock, redirect, block, cron, event). Write scripts only for your own traffic and within service terms."),
("ConfigForge — конфиги", "ConfigForge — configs",
 "Конструктор конфигураций/модулей Shadowrocket: [General], [Proxy Group], [Rule], [Host], [URL Rewrite], [Header Rewrite], [Body Rewrite], [Map Local], [Script], [MITM]. Можно импортировать готовый файл, добавлять правила мастером, строить группы с regex-фильтрами, брать шаблоны, проверять (линтер) и экспортировать .module/.conf. Роутинг можно выгрузить для других клиентов (Xray/Happ).",
 "Builder for Shadowrocket configs/modules: [General], [Proxy Group], [Rule], [Host], [URL Rewrite], [Header Rewrite], [Body Rewrite], [Map Local], [Script], [MITM]. Import an existing file, add rules via wizard, build groups with regex filters, use templates, lint and export .module/.conf. Routing can be exported for other clients (Xray/Happ)."),
("SubManager", "SubManager",
 "Загружает подписки (файл/URL/несколько), понимает vless/vmess/trojan/ss/hysteria2/tuic/wireguard/naive и др., правит и сортирует серверы, убирает дубли, экспортирует ссылки, base64, Clash YAML и Xray JSON с балансировщиком и роутингом.",
 "Loads subscriptions (file/URL/several), understands vless/vmess/trojan/ss/hysteria2/tuic/wireguard/naive etc., edits and sorts servers, removes duplicates, exports links, base64, Clash YAML and Xray JSON with balancer and routing."),
("RegexBuilder и Decoder", "RegexBuilder and Decoder",
 "RegexBuilder: мастер по примерам, объяснение, тест, шаблоны, генератор URL-паттернов для Shadowrocket.\nDecoder: принимает файл, ссылку, вставку или буфер — распознаёт base64/gzip/percent/hex/JSON-в-строке, показывает читаемый текст; если файл повреждён или формат несовместим — скажет об этом.",
 "RegexBuilder: example-based wizard, explainer, tester, templates, Shadowrocket URL-pattern generator.\nDecoder: takes a file, URL, paste or clipboard — recognises base64/gzip/percent/hex/JSON-in-string and shows readable text; says so if the file is damaged or the format is incompatible."),
("ListLab — большие тексты", "ListLab — big texts",
 "Комбайн для больших текстов (конфиги, списки правил на миллионы строк, VPN-ссылки, JSON, base64, код). Определяет вид текста, ищет, удаляет, заменяет, вставляет строки, анализирует.\n"
 "Политики: можно массово заменить, например, BESTPROXY → SPEEDPROXY или DIRECT (с фильтром по типу/словам).\n"
 "Конвертация: правила → набор rule-set (с сохранением порядка/приоритета, минимум файлов), rule-set → правила с политикой, правила → Clash/sing-box/Xray. Файлы rule-set нужно опубликовать (пункт GitHub) и вставить блок RULE-SET в конфиг.",
 "A combine for big texts (configs, rule lists with millions of lines, VPN links, JSON, base64, code). It detects the kind of text and can search, delete, replace, insert and analyse.\n"
 "Policies: bulk-replace e.g. BESTPROXY → SPEEDPROXY or DIRECT (filter by type/words).\n"
 "Convert: rules → rule-set files (order/priority preserved, fewest files), rule-set → rules with a policy, rules → Clash/sing-box/Xray. Publish the rule-set files (GitHub item) and paste the RULE-SET block into the config."),
("Тест сервисов (NetDiag)", "Service test (NetDiag)",
 "Проверяет доступность десятков сервисов (мессенджеры, соцсети, видео, музыка, магазины, ИИ, РФ-сервисы…) разными способами: несколько DNS (system, Яндекс, Cloudflare, Google, DoH, DoT), TCP, TLS, подмена SNI, обрыв после ~16 КБ (ТСПУ), с прокси и без. Результаты можно подписать (Wi-Fi дом / LTE / VPN вкл) и позже сравнить. Есть тест публичных DNS, информация об IP/ASN, сертификаты Минцифры, каталог георесурсов и ссылки импорта для клиентов.",
 "Checks dozens of services (messengers, social, video, music, stores, AI, RU services…) in several ways: many DNS (system, Yandex, Cloudflare, Google, DoH, DoT), TCP, TLS, SNI swap, cut-after-~16KB (DPI), with and without proxy. Label runs (Home Wi-Fi / LTE / VPN on) and compare them later. Also: public DNS test, IP/ASN info, Russian Trusted CA certificates, geo-resource catalog and client import links."),
("Vault, GitHub, QR", "Vault, GitHub, QR",
 "Vault шифрует выбранные или все файлы Toolkit (ключ-файл или пароль) и расшифровывает их по ключу даже после перезапуска. СОХРАНИТЕ ключ отдельно! GitHub: токен (PAT) → просмотр/правка/загрузка файлов репозитория и публикация rule-set и скриптов с готовыми raw-ссылками. QR: коды для подписок и ссылок импорта (нужен qrencode: Среда → установить опциональное).",
 "Vault encrypts selected or all Toolkit files (key file or password) and decrypts them with the key even after a restart. BACK UP the key separately! GitHub: token (PAT) → browse/edit/upload repo files and publish rule-sets and scripts with ready raw links. QR: codes for subscriptions and import links (needs qrencode: Environment → install optional)."),
("Сеть: прокси, DNS, ТСПУ", "Network: proxy, DNS, DPI",
 "Пункт «Сеть»: прокси (http/socks5), DNS по UDP, DoH, режим DNS, IPv4/IPv6, проверка TLS, шаблоны (1,2,3 / 1-3 / all), проверка связи по десяткам сервисов, полная диагностика.\n"
 "ВАЖНО: если в Shadowrocket включён перехват DNS (hijack-dns = *:53), обычные UDP-запросы на порт 53 из iSH могут не работать — используйте режим DoH. Диагностика это подскажет.\n"
 "Toolkit переживает смену Wi-Fi ↔ LTE и смену адреса VPN: кэш DNS живёт 90 с, при сбое сеть ждётся и запрос повторяется. Если всё не удалось — выбор: повторить или пропустить.",
 "'Network' item: proxy (http/socks5), UDP DNS, DoH, DNS mode, IPv4/IPv6, TLS verify, templates (1,2,3 / 1-3 / all), connectivity test against many services, full diagnostics.\n"
 "IMPORTANT: if Shadowrocket hijacks DNS (hijack-dns = *:53), plain UDP/53 queries from iSH may fail — use DoH mode. Diagnostics will hint at this.\n"
 "Toolkit survives Wi-Fi ↔ LTE switches and VPN address changes: DNS cache lives 90 s, on failure it waits for the network and retries. If everything fails you choose: retry or skip."),
("Если что-то сломалось", "Troubleshooting",
 "• «Bad system call» / падение Python: Меню 13 → «Починить окружение». Toolkit перебирает версии Alpine (3.18, 3.19, ...), проверяет каждую самотестом и откатывается на стабильную.\n"
 "• Не скачивается: пункт «Сеть» → прокси/DNS/DoH; включите «Подробные ошибки» в Настройках.\n"
 "• Папку не открыть в «Файлах»: пункт «Файлы» — удаляет/переименовывает «битые» файлы и папки.\n"
 "• Журнал ошибок: Меню 13 → «Журнал ошибок». Обновление: Меню 13 → «Обновить Toolkit».",
 "• 'Bad system call' / Python crash: Menu 13 → 'Repair environment'. Toolkit tries Alpine versions (3.18, 3.19, ...), self-tests each and rolls back to a stable one.\n"
 "• Download fails: 'Network' item → proxy/DNS/DoH; enable 'Verbose errors' in Settings.\n"
 "• Folder won't open in Files: use the 'Files' item — it deletes/renames broken files and folders.\n"
 "• Error log: Menu 13 → 'Error log'. Update: Menu 13 → 'Update Toolkit'."),
("Другие платформы и безопасность", "Other platforms & safety",
 "Toolkit работает не только в iSH: Alpine, Termux (Android), Debian/Ubuntu, macOS, Linux — нужен Python 3.8+ (оболочка поставит его сама).\n"
 "Логи трафика содержат токены и cookie: перед публикацией используйте «Маскировать» в SpyLog. Расшифровка HTTPS (MITM) нужна только для ваших собственных устройств и трафика.",
 "Toolkit works beyond iSH: Alpine, Termux (Android), Debian/Ubuntu, macOS, Linux — Python 3.8+ is required (the shell installs it).\n"
 "Traffic logs contain tokens and cookies: use 'Mask' in SpyLog before sharing. HTTPS decryption (MITM) is for your own devices and traffic only."),
]


def pager(title, text):
    hdr(title)
    w = term_w() - 2
    lines = []
    for para in text.split("\n"):
        lines += textwrap.wrap(para, w) or [""]
        lines.append("")
    page = max(8, (shutil.get_terminal_size((40, 24)).lines or 24) - 6)
    for i in range(0, len(lines), page):
        for l_ in lines[i:i + page]:
            print(l_)
        if i + page < len(lines):
            v = ask(L("Enter — дальше, q — стоп", "Enter = more, q = stop"), "", quit_ok=False)
            if v.lower() == "q":
                return


def main():
    while True:
        items = [(str(i), p[0] if ST.g("lang") == "ru" else p[1], "") for i, p in enumerate(PAGES, 1)]
        items.append(("a", L("Читать всё подряд", "Read everything"), ""))
        k = menu(L("Гид и инструкция", "Guide & help"), items, tool="guide")
        if k == "q":
            return
        idx = range(len(PAGES)) if k == "a" else [int(k) - 1]
        for i in idx:
            p = PAGES[i]
            pager(p[0] if ST.g("lang") == "ru" else p[1], p[2] if ST.g("lang") == "ru" else p[3])
        pause()


if __name__ == "__main__":
    run_tool("Guide", main)
TKEOF_guide

tk_put decoder.py << 'TKEOF_decoder'
# -*- coding: utf-8 -*-
# ==========================================================================
#  Decoder — универсальный «комбайн» для данных: файл / URL / вставка / буфер iOS.
#  Распознаёт слои (base64, gzip, percent, hex, JSON-в-строке), показывает читаемый
#  вид, ищет по полям, извлекает URL/домены, перекодирует обратно и сохраняет.
#  Если файл повреждён/несовместим — честно сообщает.
# ==========================================================================
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from tkcore import *
import tkcodec as K

TOOL = "decoder"
OUT = BASE / "Decoder" / "Output"


def read_clip():
    try:
        return open("/dev/clipboard", "rb").read()
    except Exception:
        return None


def load():
    k = menu(L("Источник данных", "Data source"), [("1", L("Файл (Decoder/Input)", "File (Decoder/Input)"), ""), ("2", L("URL", "URL"), ""),
                                                 ("3", L("Вставить текст", "Paste text"), ""), ("4", L("Буфер обмена iOS", "iOS clipboard"), "")], tool=TOOL)
    if k == "q":
        return None, ""
    if k == "1":
        fs = pick_files(BASE / "Decoder" / "Input", multi=False, tool=TOOL)
        return (fs[0].read_bytes(), fs[0].name) if fs else (None, "")
    if k == "2":
        u = ask("URL", "", quit_ok=False)
        d = fetch(u, label="data") if u else None
        return d, u
    if k == "3":
        print(dim(L("Вставьте текст. Пустая строка — конец.", "Paste text. Empty line = end.")))
        lines = []
        while True:
            l_ = input("")
            if not l_.strip():
                break
            lines.append(l_)
        return "\n".join(lines).encode("utf-8"), "paste"
    d = read_clip()
    if not d:
        print("[!] " + L("Буфер недоступен (только iSH с /dev/clipboard)", "Clipboard unavailable (iSH with /dev/clipboard only)"))
    return d, "clipboard"


def show(obj, chain, enc, name, raw):
    print("\n" + c(L("Результат анализа", "Analysis result"), accent(), True))
    table([[L("Источник", "Source"), trunc(name, 30)], [L("Размер", "Size"), fmt_size(len(raw))],
           [L("Слои", "Layers"), " → ".join(chain)], [L("Кодировка", "Encoding"), enc]], None, [12, 30])
    if isinstance(obj, (dict, list)):
        fl = K.flatten(obj)
        print(dim(L("JSON-полей: %d" % len(fl), "JSON fields: %d" % len(fl))))
        for p, v in fl[:25]:
            print("  %s = %s" % (c(trunc(p, 28), INFO_C), trunc(K.short(v, 40), term_w() - 34)))
        if len(fl) > 25:
            print(dim("  ... +%d" % (len(fl) - 25)))
    else:
        for l_ in str(obj).splitlines()[:25]:
            print("  " + trunc(l_, term_w() - 4))


def extract(text):
    urls = sorted(set(re.findall(r"https?://[^\s\"'<>\\]+", text)))
    doms = sorted(set(re.findall(r"\b(?:[a-z0-9-]+\.)+[a-z]{2,}\b", text.lower())))
    mails = sorted(set(re.findall(r"[\w.+-]+@[\w-]+\.[\w.]+", text)))
    return urls, doms, mails


def main():
    ensure_dirs("Decoder/Input", "Decoder/Output")
    while True:
        raw, name = load()
        if not raw:
            return
        try:
            obj, chain, enc = K.smart_decode(raw)
        except Exception as e:
            print("[!] " + L("Файл повреждён или имеет несовместимый формат: %s" % e, "File is damaged or has an incompatible format: %s" % e))
            continue
        txt, why = decode_download(raw)
        if txt is None:
            print("[!] " + why)
            if confirm(L("Показать hex-дамп?", "Show hex dump?")):
                for off in range(0, min(len(raw), 512), 16):
                    ch = raw[off:off + 16]
                    print("%04x  %-47s  %s" % (off, " ".join("%02x" % b for b in ch), "".join(chr(b) if 32 <= b < 127 else "." for b in ch)))
            continue
        show(obj, chain, enc, name, raw)
        while True:
            k = menu(L("Действия", "Actions"), [("1", L("Сохранить расшифрованное", "Save decoded"), ""), ("2", L("Скопировать в буфер", "Copy to clipboard"), ""),
                                              ("3", L("Поиск по значениям/ключам", "Search values/keys"), ""), ("4", L("Извлечь URL / домены / e-mail", "Extract URLs / domains / e-mails"), ""),
                                              ("5", L("Перекодировать обратно (цепочка слоёв)", "Re-encode back (layer chain)"), ""), ("6", L("Другие данные", "Other data"), "")], show=False, tool=TOOL)
            if k == "q" or k == "6":
                break
            if k == "1":
                p = OUT / ("decoded_%s.%s" % (now_stamp(), "json" if isinstance(obj, (dict, list)) else "txt"))
                atomic_write(p, txt)
                print("[+] " + str(p))
            elif k == "2":
                print("[+] OK" if clip_copy(txt) else "[!] " + L("буфер недоступен", "clipboard unavailable"))
            elif k == "3":
                q = ask(L("Что искать", "Search for"), "", quit_ok=False).lower()
                hits = [(p, v) for p, v in (K.flatten(obj) if isinstance(obj, (dict, list)) else enumerate(str(obj).splitlines(), 1))
                        if q and (q in str(p).lower() or q in str(v).lower())]
                for p, v in hits[:40]:
                    print("  %s = %s" % (c(p, INFO_C), trunc(K.short(v), term_w() - 30)))
                print(dim(L("найдено: %d" % len(hits), "found: %d" % len(hits))))
            elif k == "4":
                u, d, m = extract(txt)
                for t, lst in (("URL", u), ("Domains", d), ("E-mails", m)):
                    print(c("%s (%d)" % (t, len(lst)), accent(), True))
                    for x in lst[:30]:
                        print("  " + x)
            elif k == "5":
                ch = ask(L("Цепочка слоёв через запятую (напр. b64,json)", "Layer chain (e.g. b64,json)"), ",".join(chain), quit_ok=False)
                try:
                    out = K.smart_encode(obj, [x.strip() for x in ch.split(",") if x.strip()], enc)
                    p = OUT / ("encoded_%s.txt" % now_stamp())
                    atomic_write(p, out, "wb")
                    print("[+] %s (%s)" % (p, fmt_size(len(out))))
                except Exception as e:
                    print("[!] %s" % e)


if __name__ == "__main__":
    run_tool("Decoder", main)
TKEOF_decoder

tk_put listlab.py << 'TKEOF_listlab'
# -*- coding: utf-8 -*-
# ==========================================================================
#  ListLab — комбайн для больших текстов (конфиги, списки правил, rule-set на миллион
#  строк, VPN-ссылки, JSON, base64, код): поиск, удаление, замена, вставка, анализ,
#  переписывание политик, распаковка rule-set в правила, упаковка правил в rule-set
#  с сохранением приоритета, дедупликация, сортировка. Один шаг отмены (undo).
# ==========================================================================
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from tkcore import *
import tkcodec as K
import rules as R
from collections import Counter

TOOL = "listlab"
IN, OUT = BASE / "ListLab" / "Input", BASE / "ListLab" / "Output"


class Doc:
    def __init__(self, lines, name):
        self.lines, self.name, self.undo, self.dirty = lines, name, None, False

    def snap(self):
        self.undo = list(self.lines)
        self.dirty = True


def load():
    k = menu(L("Источник текста", "Text source"), [("1", L("Файл (ListLab/Input)", "File (ListLab/Input)"), ""), ("2", "URL", ""),
                                                  ("3", L("Вставить текст", "Paste text"), ""), ("4", L("Буфер iOS", "iOS clipboard"), "")], tool=TOOL)
    if k == "q":
        return None
    raw, name = None, "text"
    if k == "1":
        fs = pick_files(IN, None, False, tool=TOOL)
        if fs:
            raw, name = fs[0].read_bytes(), fs[0].name
    elif k == "2":
        u = ask("URL", "", quit_ok=False)
        raw, name = (fetch(u, label="list") if u else None), (u.rsplit("/", 1)[-1] or "list.txt")
    elif k == "3":
        print(dim(L("Вставьте текст. Две пустые строки подряд — конец.", "Paste text. Two blank lines = end.")))
        buf, blank = [], 0
        while blank < 2:
            l_ = input("")
            blank = blank + 1 if not l_.strip() else 0
            buf.append(l_)
        raw, name = "\n".join(buf).encode(), "paste.txt"
    else:
        try:
            raw, name = open("/dev/clipboard", "rb").read(), "clipboard.txt"
        except Exception:
            print("[!] " + L("буфер недоступен", "clipboard unavailable"))
    if not raw:
        return None
    txt, why = decode_download(raw)
    if txt is None:
        print("[!] " + why)
        return None
    kind = R.detect_kind(txt)
    lines = txt.splitlines()
    print("[+] %s: %s | %s | %s" % (L("Загружено", "Loaded"), trunc(name, 24), c(kind, accent(), True), L("строк: %d" % len(lines), "lines: %d" % len(lines))))
    if len(lines) > 1_500_000:
        print("[!] " + L("Очень большой файл — возможна нехватка памяти.", "Very large file — memory may run out."))
    return Doc(lines, name)


def show_range(d, a, b):
    for i in range(max(0, a), min(len(d.lines), b)):
        print("%s %s" % (c("%7d" % (i + 1), accent()), trunc(d.lines[i], term_w() - 9)))


def matcher():
    q = ask(L("Что искать (текст или regex)", "Find (text or regex)"), "", quit_ok=False)
    if not q:
        return None
    isre = confirm(L("Это регулярное выражение?", "Is it a regex?"))
    cs = confirm(L("Учитывать регистр?", "Case sensitive?"))
    if isre:
        try:
            rx = re.compile(q, 0 if cs else re.I)
        except re.error as e:
            print("[!] %s" % e)
            return None
        return lambda s: bool(rx.search(s)), q
    ql = q if cs else q.lower()
    return (lambda s: ql in (s if cs else s.lower())), q


def op_find(d):
    m = matcher()
    if not m:
        return
    fn = m[0]
    hits = [i for i, l_ in enumerate(d.lines) if fn(l_)]
    print("[+] " + L("Найдено строк: %d" % len(hits), "Matching lines: %d" % len(hits)))
    for i in hits[:60]:
        print("%s %s" % (c("%7d" % (i + 1), accent()), trunc(d.lines[i], term_w() - 9)))
    if len(hits) > 60:
        print(dim("... +%d" % (len(hits) - 60)))
    return hits


def op_delete(d):
    k = menu(L("Удалить строки", "Delete lines"), [("1", L("по совпадению", "matching"), ""), ("2", L("диапазон номеров", "line range"), ""), ("3", L("дубликаты", "duplicates"), ""),
                                               ("4", L("пустые строки", "blank lines"), ""), ("5", L("комментарии (#, ;, //)", "comments (#, ;, //)"), ""),
                                               ("6", L("все КРОМЕ совпадающих", "all EXCEPT matching"), "")], show=False)
    if k == "q":
        return
    new = None
    if k in ("1", "6"):
        m = matcher()
        if m:
            new = [l_ for l_ in d.lines if (not m[0](l_) if k == "1" else m[0](l_))]
    elif k == "2":
        a, b = ask(L("С строки", "From line"), "1", quit_ok=False), ask(L("По строку", "To line"), "1", quit_ok=False)
        if a.isdigit() and b.isdigit():
            new = d.lines[:int(a) - 1] + d.lines[int(b):]
    elif k == "3":
        seen, new = set(), []
        for l_ in d.lines:
            key = l_.strip()
            if key.startswith(("#", ";", "//")) or not key or key not in seen:
                new.append(l_); seen.add(key)
    elif k == "4":
        new = [l_ for l_ in d.lines if l_.strip()]
    elif k == "5":
        new = [l_ for l_ in d.lines if not l_.strip().startswith(("#", ";", "//"))]
    if new is not None:
        print("[*] %s: %d → %d" % (L("Строк", "Lines"), len(d.lines), len(new)))
        if confirm(L("Применить?", "Apply?"), True):
            d.snap(); d.lines = new


def op_replace(d):
    q = ask(L("Что заменить (текст/regex)", "Replace what (text/regex)"), "", quit_ok=False)
    if not q:
        return
    rep = ask(L("Чем заменить", "Replace with"), "", quit_ok=False)
    isre = confirm(L("regex?", "regex?"))
    try:
        rx = re.compile(q if isre else re.escape(q))
    except re.error as e:
        print("[!] %s" % e); return
    new, n = [], 0
    for l_ in d.lines:
        s, k = rx.subn(rep, l_)
        new.append(s); n += k
    print("[*] " + L("Замен: %d" % n, "Replacements: %d" % n))
    if n and confirm(L("Применить?", "Apply?"), True):
        d.snap(); d.lines = new


def op_insert(d):
    k = menu(L("Куда вставить", "Insert where"), [("1", L("в начало", "at start"), ""), ("2", L("в конец", "at end"), ""), ("3", L("перед строкой N", "before line N"), ""),
                                                 ("4", L("после каждой строки, где есть совпадение", "after each matching line"), "")], show=False)
    if k == "q":
        return
    print(dim(L("Вводите строки. Пустая строка — конец.", "Enter lines. Empty line = end.")))
    add = []
    while True:
        l_ = input("")
        if not l_:
            break
        add.append(l_)
    if not add:
        return
    d.snap()
    if k == "1":
        d.lines = add + d.lines
    elif k == "2":
        d.lines += add
    elif k == "3":
        n = ask(L("Номер строки", "Line number"), "1", quit_ok=False)
        n = int(n) - 1 if n.isdigit() else 0
        d.lines = d.lines[:n] + add + d.lines[n:]
    else:
        m = matcher()
        if m:
            new = []
            for l_ in d.lines:
                new.append(l_)
                if m[0](l_):
                    new += add
            d.lines = new


def op_policy(d):
    rules = [R.parse_line(l_) for l_ in d.lines]
    pols = Counter(r["policy"] for r in rules if r["kind"] == "rule" and r["policy"])
    if not pols:
        print("[!] " + L("Правила с политикой не найдены.", "No rules with policy found."))
        return
    print(c(L("Политики в тексте:", "Policies in text:"), accent(), True))
    for p, n in pols.most_common():
        print("  %-22s %d" % (p, n))
    print(dim(L("Стандартные: ", "Standard: ") + ", ".join(R.POLICIES)))
    old = ask(L("Какую политику менять (* — любую)", "Which policy to replace (* = any)"), "*", quit_ok=False)
    new = ask(L("На какую", "Replace with"), "DIRECT", quit_ok=False)
    types = ask(L("Только типы правил (через запятую, Enter — все)", "Only rule types (comma, Enter = all)"), "", quit_ok=False)
    cont = ask(L("Только строки, содержащие (Enter — все)", "Only lines containing (Enter = all)"), "", quit_ok=False)
    out, n = R.rewrite_policy(d.lines, {old: new}, [t.strip().upper() for t in types.split(",") if t.strip()] or None, cont or None)
    print("[*] " + L("Будет изменено: %d" % n, "Will change: %d" % n))
    if n and confirm(L("Применить?", "Apply?"), True):
        d.snap(); d.lines = out


def op_convert(d):
    k = menu(L("Конвертация", "Convert"), [("1", L("Правила → набор rule-set (с сохранением приоритета)", "Rules → rule-sets (priority preserved)"), ""),
                                          ("2", L("Rule-set → правила с политикой", "Rule-set → rules with policy"), ""), ("3", L("Правила → Clash rules (yaml)", "Rules → Clash rules (yaml)"), ""),
                                          ("4", L("Правила → sing-box rule-set (json)", "Rules → sing-box rule-set (json)"), ""), ("5", L("Правила → Xray routing (json)", "Rules → Xray routing (json)"), ""),
                                          ("6", L("Правила → список доменов (+.domain)", "Rules → domain list (+.domain)"), "")], show=False)
    if k == "q":
        return
    stamp = now_stamp()
    if k == "1":
        sets, rest = R.pack_rulesets(d.lines)
        base = mem_ask(TOOL, "base_url", L("Базовый URL, где вы опубликуете файлы (Enter — пусто)", "Base URL where you will publish the files (Enter = none)"), "", quit_ok=False)
        pre = sanitize_filename(mem_ask(TOOL, "prefix", L("Префикс имён файлов", "File name prefix"), "RULES", quit_ok=False))
        files, cfg = R.build_ruleset_files(sets, pre, base)
        OUT.mkdir(parents=True, exist_ok=True)
        for name, body in files:
            atomic_write(OUT / name, body)
            print("[+] %s  (%d)" % (name, body.count("\n")))
        block = "\n".join(cfg + rest)
        atomic_write(OUT / ("config_block_%s.txt" % stamp), block + "\n")
        print("\n" + c(L("Вставьте в [Rule] сверху вниз (порядок важен):", "Paste into [Rule] top to bottom (order matters):"), accent(), True))
        print(block)
        print(dim(L("Файлы нужно опубликовать (GitHub raw и т.п.) — используйте пункт GitHub в меню.", "Publish the files (GitHub raw etc.) — use the GitHub item in the menu.")))
        if clip_copy(block):
            print("[+] " + L("Блок скопирован в буфер", "Block copied to clipboard"))
    elif k == "2":
        pol = ask(L("Политика", "Policy"), "PROXY", quit_ok=False)
        new = R.ruleset_to_rules(d.lines, pol)
        print("[*] %d → %d" % (len(d.lines), len(new)))
        if confirm(L("Заменить текст результатом?", "Replace the text with the result?"), True):
            d.snap(); d.lines = new
    else:
        txt = {"3": lambda: R.to_clash_rules(d.lines), "4": lambda: R.to_singbox_ruleset(d.lines), "5": lambda: json.dumps({"routing": {"rules": R.to_xray_rules(d.lines)}}, indent=1, ensure_ascii=False),
               "6": lambda: "\n".join(R.to_domain_list(d.lines))}[k]()
        ext = {"3": "yaml", "4": "json", "5": "json", "6": "txt"}[k]
        p = OUT / ("converted_%s.%s" % (stamp, ext))
        atomic_write(p, txt)
        print("[+] %s (%s)" % (p, fmt_size(len(txt))))


def op_analyze(d):
    txt = "\n".join(d.lines[:300000])
    kind = R.detect_kind(txt)
    rules = [R.parse_line(l_) for l_ in d.lines]
    print(c(L("Анализ", "Analysis"), accent(), True))
    table([[L("Вид", "Kind"), kind], [L("Строк", "Lines"), str(len(d.lines))], [L("Правил", "Rules"), str(sum(1 for r in rules if r["kind"] == "rule"))],
           [L("Комментариев", "Comments"), str(sum(1 for r in rules if r["kind"] == "comment"))], [L("Пустых", "Blank"), str(sum(1 for r in rules if r["kind"] == "blank"))],
           [L("Дубликатов", "Duplicates"), str(len(d.lines) - len(set(l_.strip() for l_ in d.lines)))], [L("Размер", "Size"), fmt_size(sum(len(l_) + 1 for l_ in d.lines))]], None, [16, 30])
    for title, ctr in ((L("Типы правил", "Rule types"), Counter(r["type"] for r in rules if r["kind"] == "rule")), (L("Политики", "Policies"), Counter(r["policy"] or "-" for r in rules if r["kind"] == "rule")),
                       (L("Топ зон (TLD)", "Top TLDs"), Counter(r["val"].rsplit(".", 1)[-1] for r in rules if r["kind"] == "rule" and r["type"].startswith("DOMAIN") and "." in r["val"]))):
        if ctr:
            print(c(title, INFO_C, True))
            for k, n in ctr.most_common(10):
                print("  %-24s %d" % (trunc(k, 24), n))
    if kind == "vpn-links":
        print(c(L("Протоколы", "Protocols"), INFO_C, True))
        for k, n in Counter(l_.split("://")[0].lower() for l_ in d.lines if "://" in l_).most_common():
            print("  %-12s %d" % (k, n))


def op_normalize(d):
    k = menu(L("Упорядочить", "Tidy up"), [("1", L("сортировать правила (тип, значение)", "sort rules (type, value)"), ""), ("2", L("дедупликация + нижний регистр доменов", "dedupe + lowercase domains"), ""),
                                          ("3", L("убрать поддомены, покрытые родителем (DOMAIN-SUFFIX)", "drop subdomains covered by parent (DOMAIN-SUFFIX)"), ""), ("4", L("обрезать пробелы", "trim whitespace"), "")], show=False)
    d.snap()
    if k == "1":
        d.lines.sort(key=lambda s: (R.parse_line(s).get("type", "~"), R.parse_line(s).get("val", s).lower()))
    elif k == "2":
        seen, out = set(), []
        for l_ in d.lines:
            r = R.parse_line(l_)
            if r["kind"] == "rule" and r["type"].startswith("DOMAIN"):
                r["val"] = r["val"].lower(); l_ = R.fmt_rule(r)
            if l_.strip() and l_ in seen:
                continue
            seen.add(l_); out.append(l_)
        d.lines = out
    elif k == "3":
        suff = {R.parse_line(l_)["val"].lower() for l_ in d.lines if R.parse_line(l_).get("type") == "DOMAIN-SUFFIX"}
        out = []
        for l_ in d.lines:
            r = R.parse_line(l_)
            if r["kind"] == "rule" and r["type"] in ("DOMAIN-SUFFIX", "DOMAIN"):
                parts = r["val"].lower().split(".")
                if any(".".join(parts[i:]) in suff for i in range(1, len(parts))):
                    continue
            out.append(l_)
        d.lines = out
    elif k == "4":
        d.lines = [l_.strip() for l_ in d.lines]
    print("[+] OK")


def op_save(d):
    OUT.mkdir(parents=True, exist_ok=True)
    nm = sanitize_filename(ask(L("Имя файла", "File name"), "edited_" + d.name, quit_ok=False))
    p = OUT / nm
    with open(str(p), "w", encoding="utf-8") as f:
        f.write("\n".join(d.lines) + "\n")
    d.dirty = False
    print("[+] %s (%s)" % (p, fmt_size(p.stat().st_size)))
    if confirm(L("Скопировать в буфер iOS?", "Copy to iOS clipboard?")) and len(d.lines) < 200000:
        print("[+] OK" if clip_copy("\n".join(d.lines)) else "[!] n/a")


def main():
    ensure_dirs("ListLab/Input", "ListLab/Output")
    d = load()
    if not d:
        return
    while True:
        k = menu(L("Текст: %s (%d строк)" % (trunc(d.name, 20), len(d.lines)), "Text: %s (%d lines)" % (trunc(d.name, 20), len(d.lines))), [
            ("1", L("Поиск", "Find"), ""), ("2", L("Удалить строки", "Delete lines"), ""), ("3", L("Заменить", "Replace"), ""), ("4", L("Вставить строки", "Insert lines"), ""),
            ("5", L("Политики правил", "Rule policies"), L("переписать BESTPROXY → SPEEDPROXY…", "rewrite BESTPROXY → SPEEDPROXY…")),
            ("6", L("Конвертация / rule-set", "Convert / rule-sets"), ""), ("7", L("Анализ", "Analyze"), ""), ("8", L("Упорядочить", "Tidy up"), ""),
            ("9", L("Показать строки", "View lines"), ""), ("10", L("Отменить последнее", "Undo last"), ""), ("11", L("Сохранить", "Save"), ""),
            ("12", L("Загрузить другой текст", "Load another text"), "")], tool=TOOL)
        if k == "q":
            if d.dirty and not confirm(L("Есть несохранённые правки. Выйти?", "Unsaved changes. Leave?")):
                continue
            return
        try:
            if k == "1": op_find(d)
            elif k == "2": op_delete(d)
            elif k == "3": op_replace(d)
            elif k == "4": op_insert(d)
            elif k == "5": op_policy(d)
            elif k == "6": op_convert(d)
            elif k == "7": op_analyze(d)
            elif k == "8": op_normalize(d)
            elif k == "9":
                a = ask(L("С какой строки", "From line"), "1", quit_ok=False)
                a = int(a) - 1 if a.isdigit() else 0
                show_range(d, a, a + 40)
            elif k == "10":
                if d.undo is not None:
                    d.lines, d.undo = d.undo, None; print("[+] OK")
                else:
                    print("[!] " + L("нечего отменять", "nothing to undo"))
            elif k == "11": op_save(d)
            elif k == "12":
                nd = load()
                if nd: d = nd
        except KeyboardInterrupt:
            print("\n[*] " + L("Отменено", "Cancelled"))
        if k in "123456789" or k in ("11",):
            pause()


if __name__ == "__main__":
    run_tool("ListLab", main)
TKEOF_listlab

tk_put adblock.py << 'TKEOF_adblock'
# -*- coding: utf-8 -*-
# ==========================================================================
#  AdBlock — генератор блок-листов (RU/EN): скачивание с кэшем и откатом на кэш, белые списки,
#  защита доменов, убирание поддоменов, RULE-SET (.list), а также domain-list / Clash / sing-box.
# ==========================================================================
import sys, os, ipaddress
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from tkcore import *

TOOL = "adblock"
AB = BASE / "AdBlock"
CACHE = AB / ".cache"
GH = "https://raw.githubusercontent.com/"
URLS = {
    "Loyalsoldier": [GH + "Loyalsoldier/surge-rules/release/ruleset/reject.txt", "https://cdn.jsdelivr.net/gh/Loyalsoldier/surge-rules@release/ruleset/reject.txt"],
    "AdGuard Base": ["https://filters.adtidy.org/ios/filters/15_optimized.txt"], "AdGuard 1": ["https://filters.adtidy.org/ios/filters/2_optimized.txt"],
    "AdGuard 2": ["https://filters.adtidy.org/ios/filters/3_optimized.txt"], "Yoyo": ["https://pgl.yoyo.org/adservers/serverlist.php?hostformat=adblockplus&showintro=0&mimetype=plaintext"],
    "Mobile ads": ["https://filters.adtidy.org/ios/filters/11_optimized.txt"], "RU filter": ["https://filters.adtidy.org/ios/filters/1_optimized.txt"],
    "Trackers": ["https://easylist-downloads.adblockplus.org/cntblock.txt", GH + "easylist/easylist/master/easyprivacy/easyprivacy_trackers.txt"],
    "Anti-phishing": ["https://malware-filter.gitlab.io/malware-filter/phishing-filter-ag.txt"],
    "HaGeZi Pro": [GH + "hagezi/dns-blocklists/main/adblock/pro.txt", "https://cdn.jsdelivr.net/gh/hagezi/dns-blocklists@main/adblock/pro.txt"],
    "StevenBlack": [GH + "StevenBlack/hosts/master/hosts", "https://cdn.jsdelivr.net/gh/StevenBlack/hosts@master/hosts"]}
OISD = {"big": ("OISD", "https://dl.oisd.nl/oisd_big_surge.list"), "nsfw": ("OISD NSFW", "https://dl.oisd.nl/oisd_nsfw_surge.list"), "small": ("OISD Small", "https://dl.oisd.nl/oisd_small_surge.list"), "nsfw_small": ("OISD NSFW Small", "https://dl.oisd.nl/oisd_nsfw_small_surge.list")}
WHITE = {"Direct": [GH + "Loyalsoldier/surge-rules/release/ruleset/direct.txt"], "Proxy": [GH + "Loyalsoldier/surge-rules/release/ruleset/proxy.txt"], "Apple": [GH + "Loyalsoldier/surge-rules/release/ruleset/apple.txt"],
         "iCloud": [GH + "Loyalsoldier/surge-rules/release/ruleset/icloud.txt"], "AnudeepND": [GH + "anudeepND/whitelist/master/domains/whitelist.txt"],
         "RU mobile": ["https://cdn.jsdelivr.net/gh/hxehex/russia-mobile-internet-whitelist@main/whitelist.txt", GH + "hxehex/russia-mobile-internet-whitelist/main/whitelist.txt"]}
PROT_SUF = set("apple-pki.com icloud.com icloud-content.com mzstatic.com push.apple.com appleid.apple.com simplex.im simplexonflux.com telegram.org t.me telegram.me telegra.ph tg.dev whatsapp.com whatsapp.net wa.me youtube.com youtu.be ytimg.com googlevideo.com youtube.googleapis.com".split())
PROT_DOM = set("""raw.githubusercontent.com apple.com aaplimg.com github.com githubusercontent.com githubassets.com google.com gstatic.com ggpht.com googleapis.com firebaseio.com openai.com chatgpt.com oaistatic.com microsoft.com windows.com windowsupdate.com
azure.com amazon.com amazonaws.com cloudfront.net cloudflare.com fastly.net cdn.jsdelivr.net unpkg.com akamaiedge.net akamaized.net auth0.com okta.com hcaptcha.com recaptcha.net facebook.com fbcdn.net instagram.com discord.com discordapp.com duckduckgo.com
yandex.ru yandex.com mail.ru vk.com ozon.ru wildberries.ru avito.ru hh.ru sberbank.ru alfabank.ru tbank.ru tinkoff.ru vtb.ru gosuslugi.ru kinopoisk.ru rutube.ru lenta.ru rbc.ru dns.google quad9.net npmjs.org pypi.org gitlab.com android.com""".split())
FORCE_SUF = set("bit.ly tinyurl.com t.co is.gd ow.ly linktr.ee adjust.com googleadservices.com doubleclick.net googlesyndication.com google-analytics.com googletagmanager.com app-measurement.com crashlytics.com branch.io amplitude.com mixpanel.com hotjar.com yandexmetrica.ru mc.yandex.ru metrika.yandex.ru top.mail.ru adriver.ru adfox.ru pixel.facebook.com analytics.facebook.com connect.facebook.net".split())
KW = ["ads", "analytics", "tracker", "tracking", "tracer", "metrics", "metrica", "metrika", "telemetry", "pixel", "beacon", "adserver", "doubleclick", "adjust", "appsflyer", "app-measurement", "log-upload", "crash-report"]
SUBSTR_KW = {"doubleclick", "appsflyer", "app-measurement", "adserver", "telemetry", "analytics", "metrika", "metrica"}
PROT_IP = set("1.1.1.1 1.0.0.1 8.8.8.8 8.8.4.4 9.9.9.9 149.112.112.112 94.140.14.14 94.140.15.15 208.67.222.222 208.67.220.220".split())
INVALID = set("?|=*(),&:[]/\\%#")


def cached(name, urls):
    """Скачать список (зеркала по очереди); при неудаче — взять копию из кэша (с пометкой)."""
    CACHE.mkdir(parents=True, exist_ok=True)
    f = CACHE / (hashlib.sha1(urls[0].encode()).hexdigest()[:16] + ".txt")
    ttl = ST.mem(TOOL, "cache_hours", 0)
    if ttl and f.exists() and time.time() - f.stat().st_mtime < ttl * 3600:
        print("[+] %s: %s" % (name, L("из кэша (свежий)", "from cache (fresh)")))
        return f.read_text("utf-8", "replace").splitlines(), "cache"
    for u in urls:
        d = fetch(u, label=name, interactive=False, retries=2)
        if d:
            txt, chain = decode_download(d)
            if txt and len(txt.splitlines()) > 5 and "<html" not in txt[:300].lower():
                atomic_write(f, txt)
                return txt.splitlines(), u
            print("[!] %s: %s" % (name, chain if txt is None else L("получен не список (HTML?)", "not a list (HTML?)")))
    if f.exists():
        print("[!] %s: %s" % (name, L("сеть недоступна — использую КЭШ", "network failed — using CACHE")))
        return f.read_text("utf-8", "replace").splitlines(), "cache"
    return [], None


def kw_hit(dom, mode):
    if mode == "off":
        return False
    toks = set(re.split(r"[.\-_]", dom))
    return any((k in dom) if (mode == "substr" or k in SUBSTR_KW) else (k in toks) for k in KW)


def valid_dom(d, allow_us):
    bad = INVALID - ({"_"} if allow_us else set())
    return bool(d) and len(d) >= 4 and d.isascii() and "." in d and not (d[0] in ".-" or d[-1] in ".-") and bad.isdisjoint(d)


def valid_ip(s):
    try:
        n = ipaddress.ip_network(s, strict=False)
        return None if str(n.network_address).startswith(("0.", "127.", "255.")) else str(n)
    except ValueError:
        return None


def parse_line(raw):
    s = raw.strip().lower()
    m = re.match(r"^(?:address|server)=/([^/]+)/", s) or re.match(r'^local-zone:\s*"([^"]+)"', s)
    if m:
        return ("d", m.group(1).strip("."))
    if not s or s.startswith(("!", "[", "@@", "#", "/")) or "##" in s or "#@#" in s:
        return None
    if "," in s and not s.startswith("||"):
        p = [x.strip() for x in s.split(",", 2)]
        v = p[1].split("#")[0].strip() if len(p) > 1 else ""
        if "ip-cidr" in p[0]:
            return ("i", v)
        return ("d", v) if "domain" in p[0] else None
    s = s.split("#")[0].strip()
    if s.startswith(("0.0.0.0 ", "127.0.0.1 ")):
        s = s.split(" ", 1)[1].strip()
    s = re.sub(r"^[|\s]*\|\|?", "", s)
    s = re.sub(r"^https?://", "", s); s = re.sub(r"^www\.", "", s)
    if "/" in s.split("^")[0].split("$")[0]:
        return None
    s = s.split("^")[0].split("$")[0].split(":")[0].split("*")[0].strip().strip(".")
    return ("i", s) if valid_ip(s) else ("d", s) if s else None


def optimize(doms, label):
    srt = sorted(doms, key=lambda x: x.count("."))
    keep, bar = set(), Bar(len(srt), label, "")
    for i, d in enumerate(srt, 1):
        p = d.split(".")
        if not any(".".join(p[j:]) in keep for j in range(1, len(p) - 1)):
            keep.add(d)
        if i % 5000 == 0:
            bar.update(i)
    bar.update(len(srt)); bar.close()
    return keep


def protected(d, dom_set, suf_set):
    if d in dom_set:
        return True
    p = d.split(".")
    return any(".".join(p[i:]) in suf_set for i in range(len(p)))


def main():
    ensure_dirs("AdBlock")
    mode = menu(L("AdBlock: режим", "AdBlock: mode"), [("1", L("По умолчанию (готовый набор)", "Default (ready set)"), ""), ("2", "Custom", L("свои списки и домены", "your lists and domains"))], tool=TOOL)
    if mode == "q":
        return
    opts = checklist(TOOL, L("Параметры", "Options"), [("split", L("Разбивать по 100000 строк", "Split by 100000 lines"), False), ("clist", L("Домены-список (txt)", "Plain domain list (txt)"), False),
                                                      ("clash", "Clash (yaml payload)", False), ("sing", "sing-box rule-set", False), ("us", L("Разрешать «_» в доменах", "Allow '_' in domains"), True),
                                                      ("child", L("Не блокировать родителей белых доменов", "Don't block parents of whitelisted domains"), False)])
    kwm = {"1": "token", "2": "substr", "3": "off"}[ask(L("Фильтр ключевых слов: 1 по частям имени, 2 по подстроке, 3 выкл", "Keyword filter: 1 by name parts, 2 substring, 3 off"), "1", quit_ok=False) if True else "1"]
    ST.setmem(TOOL, "cache_hours", int(ask(L("Считать кэш свежим, часов (0 — всегда качать)", "Treat cache as fresh for hours (0 = always download)"), str(ST.mem(TOOL, "cache_hours", 0)), quit_ok=False) or 0))
    urls = dict(URLS)
    white = dict(WHITE)
    psuf, pdom, fsuf, fdom = set(PROT_SUF), set(PROT_DOM), set(FORCE_SUF), set()
    oi = "3"
    if mode == "1":
        oi = ask(L("OISD: 1 обычные, 2 малые, 3 все", "OISD: 1 normal, 2 small, 3 both"), ST.mem(TOOL, "oisd", "3"), quit_ok=False)
        ST.setmem(TOOL, "oisd", oi)
    else:
        urls, white = {}, {}
        csv = lambda t: [x.strip().lower().strip(".") for x in ask(t, "", quit_ok=False).split(",") if x.strip()]
        pdom |= set(csv(L("Белые домены (через запятую)", "White domains (comma)"))); psuf |= set(csv(L("Белые суффиксы", "White suffixes")))
        fdom |= set(csv(L("Чёрные домены", "Black domains"))); fsuf |= set(csv(L("Чёрные суффиксы", "Black suffixes")))
        for tgt, ttl in ((urls, L("чёрный", "black")), (white, L("белый", "white"))):
            while True:
                nm = ask(L("Имя %s списка (Enter — конец)" % ttl, "%s list name (Enter = end)" % ttl), "", quit_ok=False)
                if not nm:
                    break
                lst = []
                while True:
                    u = ask("  URL #%d (Enter — конец)" % (len(lst) + 1), "", quit_ok=False)
                    if not u:
                        break
                    lst.append(u)
                if lst:
                    tgt[nm] = lst
        if not urls:
            print("[!] " + L("Чёрные списки не заданы", "No blacklists given")); return
    groups = {"std": ["main"], "std_nsfw": ["main", "nsfw"]}
    buckets = {k: (set(), set()) for k in ("base", "big", "nsfw", "small", "nsfw_small")}
    t0 = time.time()
    hdr(L("Этап 1: белые списки", "Stage 1: whitelists"))
    for nm, us in white.items():
        lines, src = cached(nm, us)
        for raw in lines:
            r = parse_line(raw)
            if r and r[0] == "d" and valid_dom(r[1], True):
                (psuf if raw.strip().startswith(".") or raw.lower().startswith("domain-suffix") else pdom).add(r[1])
    for d in [x for x in pdom if (x.endswith(".apple.com") or x.startswith(("apple-", "icloud"))) and x != "apple.com"]:
        pdom.discard(d); psuf.add(d)
    hdr(L("Этап 2: чёрные списки", "Stage 2: blacklists"))
    stats, failed = Counter(), []
    todo = [(nm, us, "base") for nm, us in urls.items()]
    if mode == "1":
        if oi in ("1", "3"):
            todo += [(OISD["big"][0], [OISD["big"][1]], "big"), (OISD["nsfw"][0], [OISD["nsfw"][1]], "nsfw")]
        if oi in ("2", "3"):
            todo += [(OISD["small"][0], [OISD["small"][1]], "small"), (OISD["nsfw_small"][0], [OISD["nsfw_small"][1]], "nsfw_small")]
    for nm, us, b in todo:
        lines, src = cached(nm, us)
        while not lines:
            a = ask(L("«%s» не скачан: 1 повторить, 2 пропустить, 3 ввести ссылку, 4 сеть (прокси/DNS)" % nm, "'%s' failed: 1 retry, 2 skip, 3 enter URL, 4 network (proxy/DNS)" % nm), "1", quit_ok=False)
            if a == "2":
                failed.append(nm); break
            if a == "3":
                us = [ask("URL", "", quit_ok=False)]
            if a == "4":
                net_trouble()
            lines, src = cached(nm, us)
        if not lines:
            continue
        D, I = buckets[b]
        use_wl = "OISD" not in nm if mode == "1" else True
        bar = Bar(len(lines), "parse", "")
        for i, raw in enumerate(lines, 1):
            r = parse_line(raw)
            if r is None:
                continue
            kind, v = r
            if kind == "d":
                if not valid_dom(v, opts["us"]):
                    stats["junk"] += 1; continue
                if kw_hit(v, kwm):
                    stats["kw"] += 1; continue
                if use_wl and protected(v, pdom, psuf):
                    stats["prot"] += 1; continue
                D.add(v)
            else:
                n = valid_ip(v)
                if n and not (use_wl and n.split("/")[0] in PROT_IP):
                    I.add(n)
            if i % 4000 == 0:
                bar.update(i)
        bar.update(len(lines)); bar.close()
    for s in fsuf | fdom:
        if valid_dom(s, True):
            buckets["base"][0].add(s)
    if opts["child"]:
        par = set()
        for p in pdom | psuf:
            parts = p.split(".")
            par |= {".".join(parts[i:]) for i in range(1, len(parts) - 1)}
        for k_, (D, I) in buckets.items():
            D.difference_update(par - fsuf - fdom)
    hdr(L("Этап 3: оптимизация и запись", "Stage 3: optimize & write"))
    base_d, base_i = buckets["base"]
    sets = [("REJECT_RULES", ["big"], False), ("REJECT_RULES_PLUS", ["big", "nsfw"], True), ("REJECT_RULES_SMALL", ["small"], False), ("REJECT_RULES_PLUS_SMALL", ["small", "nsfw_small"], True)] if mode == "1" else [("REJECT_RULES", [], False)]
    sets = [s for s in sets if mode != "1" or (("big" in s[1] and oi in ("1", "3")) or ("small" in s[1] and oi in ("2", "3")))]
    summary = []
    for name, parts, plus in sets:
        D, I = set(base_d), set(base_i)
        for p in parts:
            D |= buckets[p][0]; I |= buckets[p][1]
        if plus:
            D |= {"yabuchka.net", "xcelebs.ru"}
        opt = optimize(D, name)
        lines = ["DOMAIN-SUFFIX,%s" % d for d in sorted(opt)] + ["IP-CIDR,%s" % i for i in sorted(I)]
        if not lines:
            continue
        chunks = [lines] if not opts["split"] else [lines[i:i + 100000] for i in range(0, len(lines), 100000)]
        atomic_write(AB / (name + ".list"), "\n".join(lines) + "\n")
        for i, ch in enumerate(chunks if opts["split"] else [], 1):
            atomic_write(AB / ("%s_%d.list" % (name, i)), "\n".join(ch) + "\n")
        if opts["clist"]:
            atomic_write(AB / (name + ".txt"), "\n".join(sorted(opt)) + "\n")
        if opts["clash"]:
            atomic_write(AB / (name + ".yaml"), "payload:\n" + "\n".join("  - '+.%s'" % d for d in sorted(opt)) + "\n")
        if opts["sing"]:
            atomic_write(AB / (name + ".json"), json.dumps({"version": 2, "rules": [{"domain_suffix": sorted(opt), "ip_cidr": sorted(I)}]}))
        summary.append([name, str(len(opt)), str(len(I)), str(len(lines))])
    table(summary, [L("Файл", "File"), "domains", "IP", L("строк", "lines")])
    print("[+] %s: %s | %s: %d | %s: %d | %s: %d" % (L("Папка", "Folder"), AB, L("ключ.слова", "keywords"), stats["kw"], L("защищено", "protected"), stats["prot"], L("мусор", "junk"), stats["junk"]))
    if failed:
        print("[!] " + L("Не скачаны: ", "Failed: ") + ", ".join(failed))
    print(dim("%s %.0f s" % (L("Время:", "Time:"), time.time() - t0)))
    if confirm(L("Опубликовать на GitHub сейчас?", "Publish to GitHub now?")):
        run_sibling("ghapi.py")


from collections import Counter

if __name__ == "__main__":
    run_tool("AdBlock", main)
TKEOF_adblock

tk_put sqlitetxt.py << 'TKEOF_sqlitetxt'
# -*- coding: utf-8 -*-
# ==========================================================================
#  SQLiteTXT — логи в SQLite (прокси-журнал и DNS-журнал клиента) → текст/CSV/JSONL,
#  анализ DNS (серверы, задержки, пустые ответы), статистика по политикам и доменам,
#  генерация правил/[Host] из журнала. Плюс разбор текстовых логов Xray/sing-box/Clash.
# ==========================================================================
import sys, os, sqlite3, csv
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from tkcore import *
from collections import Counter, defaultdict

TOOL = "sqlitetxt"
IN, OUT = BASE / "SQLiteTXT" / "Input", BASE / "SQLiteTXT" / "Output"
SKIP = ("logging_segments", "logging_segdir", "logging_content", "logging_docsize", "logging_stat")
DNS_TYPES = {"1": "A", "28": "AAAA", "5": "CNAME", "15": "MX", "16": "TXT", "65": "HTTPS", "12": "PTR", "2": "NS"}


def q(name):
    return '"%s"' % name.replace('"', '""')


def open_db(path):
    try:
        return sqlite3.connect("file:%s?mode=ro" % quote(str(path)), uri=True)
    except Exception:
        return sqlite3.connect(str(path))


def tables(conn):
    return [r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type IN ('table') AND name NOT LIKE 'sqlite_%'") if r[0] not in SKIP]


def columns(conn, t):
    return [r[1] for r in conn.execute("PRAGMA table_info(%s)" % q(t))]


def kind_of(cols):
    s = set(c_.lower() for c_ in cols)
    if {"host", "result", "server"} <= s:
        return "dns"
    if "url" in s or ("host" in s and "type" in s):
        return "proxy"
    return "generic"


def rows(conn, t, where="", params=()):
    cur = conn.execute("SELECT * FROM %s %s" % (q(t), where), params)
    while True:
        chunk = cur.fetchmany(5000)
        if not chunk:
            return
        for r in chunk:
            yield r


def info(conn, t):
    cols = columns(conn, t)
    n = conn.execute("SELECT COUNT(*) FROM %s" % q(t)).fetchone()[0]
    return cols, n, kind_of(cols)


# ---- экспорт ----
def do_export(conn, t, cols):
    fmt = menu(L("Формат", "Format"), [("1", L("Читаемый текст", "Readable text"), ""), ("2", "CSV", ""), ("3", "TSV", ""), ("4", "JSONL", "")], show=False)
    if fmt == "q":
        return
    kw = [x.strip().lower() for x in mem_ask(TOOL, "kw", L("Фильтр по словам (через запятую, Enter — все)", "Keyword filter (comma, Enter = all)"), "", quit_ok=False).split(",") if x.strip()]
    total = conn.execute("SELECT COUNT(*) FROM %s" % q(t)).fetchone()[0]
    p = OUT / ("%s_%s.%s" % (sanitize_filename(t), now_stamp(), {"1": "txt", "2": "csv", "3": "tsv", "4": "jsonl"}[fmt]))
    bar, n, w = Bar(total, "export", ""), 0, None
    with open(str(p), "w", encoding="utf-8", newline="") as f:
        if fmt in ("2", "3"):
            w = csv.writer(f, delimiter="," if fmt == "2" else "\t"); w.writerow(cols)
        for i, r in enumerate(rows(conn, t), 1):
            if kw and not any(k in " ".join(str(x) for x in r).lower() for k in kw):
                continue
            n += 1
            if fmt == "1":
                f.write("\n" + "\n".join("%s: %s" % (c_, "(null)" if v is None else v) for c_, v in zip(cols, r)) + "\n")
            elif w:
                w.writerow(["" if v is None else v for v in r])
            else:
                f.write(json.dumps(dict(zip(cols, r)), ensure_ascii=False) + "\n")
            if i % 2000 == 0:
                bar.update(i)
    bar.update(total); bar.close()
    print("[+] %s (%d %s)" % (p, n, L("строк", "rows")))


# ---- DNS-анализ ----
def dns_analyze(conn, t):
    recs = list(rows(conn, t))
    cols = [c_.lower() for c_ in columns(conn, t)]
    ix = {k: cols.index(k) for k in ("host", "result", "server", "type", "elapsed", "created") if k in cols}
    g = lambda r, k: r[ix[k]] if k in ix else None
    print(c(L("Всего запросов: %d" % len(recs), "Total queries: %d" % len(recs)), accent(), True))
    srv = defaultdict(list)
    for r in recs:
        srv[g(r, "server")].append(r)
    rows_ = []
    for s, lst in sorted(srv.items(), key=lambda x: -len(x[1])):
        el = [g(r, "elapsed") for r in lst if isinstance(g(r, "elapsed"), (int, float))]
        empty = sum(1 for r in lst if not g(r, "result"))
        rows_.append([trunc(str(s), 30), str(len(lst)), "%.0f" % (sum(el) / len(el)) if el else "-", str(max(el)) if el else "-", str(empty)])
    table(rows_, [L("Сервер", "Server"), "n", "avg ms", "max", L("пусто", "empty")])
    print(c(L("Типы записей", "Record types"), INFO_C, True))
    for k, n in Counter(DNS_TYPES.get(str(g(r, "type")), str(g(r, "type"))) for r in recs).most_common():
        print("  %-8s %d" % (k, n))
    print(c(L("Топ доменов", "Top hosts"), INFO_C, True))
    for h, n in Counter(g(r, "host") for r in recs).most_common(15):
        print("  %-36s %d" % (trunc(h, 36), n))
    slow = sorted((r for r in recs if isinstance(g(r, "elapsed"), (int, float))), key=lambda r: -g(r, "elapsed"))[:8]
    print(c(L("Самые медленные", "Slowest"), INFO_C, True))
    for r in slow:
        print("  %5d ms  %s  %s" % (g(r, "elapsed"), trunc(g(r, "host"), 28), dim(trunc(str(g(r, "server")), 24))))
    empties = Counter(g(r, "host") for r in recs if not g(r, "result"))
    if empties:
        print(c(L("Без ответа (блок/сбой)", "No answer (blocked/failed)"), WARN_C, True))
        for h, n in empties.most_common(10):
            print("  %-36s %d" % (trunc(h, 36), n))
    return recs, ix


def dns_outputs(recs, ix):
    k = menu(L("Результат из DNS-журнала", "Output from the DNS log"), [("1", L("Строки [Host] (домен = IP)", "[Host] lines (domain = IP)"), ""), ("2", L("Список доменов (DOMAIN-SUFFIX) с политикой", "Domain list (DOMAIN-SUFFIX) with policy"), ""),
                                                                    ("3", L("Список IP из ответов", "IP list from answers"), "")], show=False)
    if k == "q":
        return
    h, r_ = ix["host"], ix["result"]
    seen = OrderedDict() if False else {}
    for r in recs:
        if r[h] and r[r_]:
            seen.setdefault(r[h], str(r[r_]).split(",")[0].strip())
    if k == "1":
        txt = "\n".join("%s = %s" % (a, b) for a, b in seen.items())
    elif k == "2":
        pol = ask(L("Политика", "Policy"), "DIRECT", quit_ok=False)
        txt = "\n".join("DOMAIN-SUFFIX,%s,%s" % (a, pol) for a in seen)
    else:
        txt = "\n".join(sorted(set(seen.values())))
    p = OUT / ("dns_out_%s.txt" % now_stamp()); atomic_write(p, txt + "\n")
    print("[+] %s (%d)" % (p, len(txt.splitlines())))


def proxy_analyze(conn, t, cols):
    low = [c_.lower() for c_ in cols]
    recs = list(rows(conn, t))
    print(c(L("Записей: %d" % len(recs), "Rows: %d" % len(recs)), accent(), True))
    ti = low.index("type") if "type" in low else None
    ui = low.index("url") if "url" in low else (low.index("host") if "host" in low else None)
    if ti is not None:
        for k, n in Counter(r[ti] for r in recs).most_common():
            print("  %-10s %d" % (k, n))
    if ui is not None:
        def dom(u):
            m = re.match(r"^(?:\w+://)?([^/:]+)", str(u))
            return m.group(1) if m else str(u)
        for pol in ([None] if ti is None else sorted({r[ti] for r in recs if r[ti]})):
            c_ = Counter(dom(r[ui]) for r in recs if pol is None or r[ti] == pol)
            print(c("%s — %s" % (L("Топ доменов", "Top hosts"), pol or "*"), INFO_C, True))
            for h, n in c_.most_common(8):
                print("  %-38s %d" % (trunc(h, 38), n))
        if confirm(L("Сформировать правила (DOMAIN-SUFFIX) из журнала?", "Build rules (DOMAIN-SUFFIX) from the log?")):
            out = []
            for r in recs:
                d = dom(r[ui]); p = r[ti] if ti is not None and r[ti] in ("DIRECT", "PROXY", "REJECT") else ask(L("Политика для %s" % d, "Policy for %s" % d), "PROXY", quit_ok=False) if False else (r[ti] if ti is not None else "PROXY")
                out.append("DOMAIN-SUFFIX,%s,%s" % (d, p))
            out = list(dict.fromkeys(out))
            pth = OUT / ("rules_from_log_%s.list" % now_stamp()); atomic_write(pth, "\n".join(out) + "\n")
            print("[+] %s (%d)" % (pth, len(out)))


# ---- текстовые логи других клиентов (Xray / sing-box / Clash / Happ / v2RayTun) ----
XRAY_ACC = re.compile(r"(?P<ts>\d{4}[/-]\d\d[/-]\d\d \d\d:\d\d:\d\d)\S*\s+(?:from\s+(?:tcp:|udp:)?(?P<src>\S+)\s+)?accepted\s+(?P<net>tcp|udp):(?P<dst>[^\s\[]+)(?:\s+\[(?P<route>[^\]]+)\])?")
SB_LINE = re.compile(r"(?:outbound|inbound)/(?P<ob>\w+)\[(?P<tag>[^\]]*)\]:\s*(?P<msg>.*)")
CL_LINE = re.compile(r"\[(?:TCP|UDP)\]\s+(?P<src>\S+)\s+-->\s+(?P<dst>\S+)\s+match\s+(?P<rule>.+?)\s+using\s+(?P<pol>.+)$")


def text_logs():
    fs = pick_files(IN, {".log", ".txt"}, True, L("Текстовые логи клиентов", "Client text logs"), TOOL)
    if not fs:
        return
    hosts, routes, errs, kinds = Counter(), Counter(), Counter(), Counter()
    for f in fs:
        bar = Bar(max(1, f.stat().st_size), trunc(f.name, 12), "B"); done = 0
        with open(str(f), "rb") as fh:
            for i, raw in enumerate(fh):
                done += len(raw)
                ln_ = raw.decode("utf-8", "replace")
                m = XRAY_ACC.search(ln_)
                if m:
                    kinds["xray"] += 1; hosts[m.group("dst").rsplit(":", 1)[0]] += 1; routes[m.group("route") or "-"] += 1; continue
                m = CL_LINE.search(ln_)
                if m:
                    kinds["clash"] += 1; hosts[m.group("dst").rsplit(":", 1)[0]] += 1; routes[m.group("pol").strip()] += 1; continue
                m = SB_LINE.search(ln_)
                if m:
                    kinds["sing-box"] += 1; routes[m.group("tag") or m.group("ob")] += 1
                if re.search(r"(?i)error|failed|refused|timeout|reset|denied", ln_):
                    errs[re.sub(r"\d+(\.\d+){3}(:\d+)?|\b[0-9a-f]{8,}\b", "*", ln_.strip())[:90]] += 1
                if i % 500 == 0:
                    bar.update(done)
        bar.update(bar.total); bar.close()
    print(c(L("Форматы: ", "Formats: ") + ", ".join("%s=%d" % kv for kv in kinds.items()), accent(), True))
    for title, ctr in ((L("Топ назначений", "Top destinations"), hosts), (L("Маршруты/политики", "Routes/policies"), routes), (L("Частые ошибки", "Frequent errors"), errs)):
        if ctr:
            print(c(title, INFO_C, True))
            for k, n in ctr.most_common(12):
                print("  %-60s %d" % (trunc(k, 60), n))


def main():
    ensure_dirs("SQLiteTXT/Input", "SQLiteTXT/Output")
    while True:
        k = menu("SQLiteTXT", [("1", L("База SQLite: экспорт и анализ", "SQLite DB: export & analysis"), L("прокси- и DNS-журналы", "proxy & DNS logs")), ("2", L("Текстовые логи клиентов (Xray, sing-box, Clash…)", "Client text logs (Xray, sing-box, Clash…)"), ""),
                               ("3", L("Файлы и очистка", "Files & cleanup"), "")], tool=TOOL)
        if k == "q":
            return
        if k == "3":
            files_menu(TOOL, IN, OUT, {".db", ".sqlite", ".sqlite3", ".log", ".txt"}); continue
        if k == "2":
            text_logs(); pause(); continue
        fs = pick_files(IN, {".db", ".sqlite", ".sqlite3"}, False, L("Выберите базу", "Choose a database"), TOOL)
        if not fs:
            continue
        try:
            conn = open_db(fs[0])
            tl = tables(conn)
        except sqlite3.Error as e:
            print("[!] " + L("Файл повреждён или это не SQLite: %s" % e, "File is damaged or not SQLite: %s" % e)); continue
        if not tl:
            print("[!] " + L("В базе нет таблиц", "No tables in the database")); continue
        for t in tl:
            cols, n, kd = info(conn, t)
            print("  %s %-14s %-8s %d %s: %s" % (c("•", accent()), t, c(kd, INFO_C), n, L("строк", "rows"), trunc(", ".join(cols), term_w() - 36)))
        t = tl[0] if len(tl) == 1 else ask(L("Таблица", "Table"), tl[0], quit_ok=False)
        if t not in tl:
            continue
        cols, n, kd = info(conn, t)
        while True:
            k2 = menu("%s: %s (%s)" % (fs[0].name[:18], t, kd), [("1", L("Экспорт (текст/CSV/TSV/JSONL)", "Export (text/CSV/TSV/JSONL)"), ""), ("2", L("Анализ и статистика", "Analysis & stats"), ""),
                                                           ("3", L("Результат: [Host]/правила/IP (для DNS)", "Output: [Host]/rules/IPs (DNS)"), "")], show=True)
            if k2 == "q":
                break
            try:
                if k2 == "1": do_export(conn, t, cols)
                elif k2 == "2":
                    if kd == "dns": dns_analyze(conn, t)
                    else: proxy_analyze(conn, t, cols)
                elif k2 == "3" and kd == "dns":
                    recs, ix = dns_analyze(conn, t) if False else (list(rows(conn, t)), {c_.lower(): i for i, c_ in enumerate(cols)})
                    dns_outputs(recs, ix)
            except KeyboardInterrupt:
                print("\n[*] " + L("Отменено", "Cancelled"))
            pause()


if __name__ == "__main__":
    run_tool("SQLiteTXT", main)
TKEOF_sqlitetxt

tk_put spylog.py << 'TKEOF_spylog'
# -*- coding: utf-8 -*-
# ==========================================================================
#  SpyLog — анализатор логов Shadowrocket (модуль Spy): блоки [Spylog] … +---
#  Extract / Compare (файлы и группы) с различиями ПО ПОЛЯМ JSON / Explore / Search /
#  Stats / Mask / «Находки» → ScriptForge.  Тела раскодируются (base64/gzip/percent…).
# ==========================================================================
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from tkcore import *
import tkcodec as K
from collections import defaultdict, Counter
from urllib.parse import urlparse

TOOL = "spylog"
IN, OUT = BASE / "SpyLog" / "Input", BASE / "SpyLog" / "Output"
FIND = BASE / "ScriptForge" / "Findings"
SPY_URL = "https://raw.githubusercontent.com/Krest-Neva/Shadowrocket/main/Configurations/Spy.module"
ANSI_B = re.compile(rb"\x1b\[[0-9;]*[A-Za-z]")
PREFIXES = ("| < Заголовки ответа:", "| TYPE:", "| SIZE ", "| < Body:", "| URL:", "| [REQ/RES]", "| [REQ]", "| [RES]")


# ---- чтение блоков из файла потоково (с прогресс-баром) ----
def read_blocks(path, pattern):
    pat = pattern.encode()
    size = max(1, path.stat().st_size)
    bar = Bar(size, trunc(path.name, 14), "B")
    blocks, cur, done = [], None, 0
    with open(str(path), "rb") as f:
        for i, line in enumerate(f):
            done += len(line)
            line = ANSI_B.sub(b"", line.rstrip(b"\r\n"))
            if cur is None:
                if pat in line:
                    cur = [line]
            else:
                cur.append(line)
                if line.strip() == b"+---":
                    blocks.append(b"\n".join(cur)); cur = None
            if i % 400 == 0:
                bar.update(done)
    if cur:
        blocks.append(b"\n".join(cur))
    bar.update(size); bar.close()
    return [K.decode_bytes(b)[0] for b in blocks]


def parse_header(t):
    first = t.split("\n", 1)[0]
    m = re.search(r"\[Spylog\].*?\[([A-Z/]+)\]\s+([A-Z]+)\s+(https?://\S+)", first) or re.search(r"(GET|POST|PUT|DELETE|PATCH|HEAD|OPTIONS)\s+(https?://\S+)", t)
    if not m:
        return None, None
    return (m.group(2), m.group(3).rstrip("]")) if m.lastindex == 3 else (m.group(1), m.group(2).rstrip("]"))


def section(lines, marker, stop_pipe):
    idx = next((i for i, l_ in enumerate(lines) if marker in l_), -1)
    if idx < 0:
        return ""
    col = [lines[idx].split(marker, 1)[1]]
    for l_ in lines[idx + 1:]:
        if l_.strip() == "+---" or (stop_pipe and l_.startswith("|") and l_.startswith(PREFIXES)):
            break
        col.append(l_)
    return "\n".join(col).strip("\n")


def parse_rec(text, src, sig_level=1):
    m, u = parse_header(text)
    lines = text.split("\n")
    nu = u or "UNKNOWN"
    p = urlparse(nu)
    nu = {2: "%s://%s%s" % (p.scheme, p.netloc, p.path), 3: p.path or "/", 4: ""}.get(sig_level, nu)
    return {"source": src, "raw": text, "method": m or "", "url": u or "", "host": p.netloc, "sig": "%s %s" % (m or "ANY", nu),
            "req": section(lines, "| > Body:", True), "res": section(lines, "| < Body:", False), "_c": {}}


def decoded(rec, side):
    """Раскодированное тело записи: (obj, chain, enc) с кэшем."""
    if side not in rec["_c"]:
        body = rec[side]
        try:
            rec["_c"][side] = K.smart_decode(body.encode("utf-8", "surrogateescape")) if body.strip() else ("", ["text"], "utf-8")
        except Exception:
            rec["_c"][side] = (body, ["text"], "utf-8")
    return rec["_c"][side]


def load_records(files, pattern, sig_level=1, dedupe=True):
    recs = []
    for f in files:
        for b in read_blocks(f, pattern):
            recs.append(parse_rec(b, f.name, sig_level))
    if dedupe:
        seen, out = set(), []
        for r in recs:
            k = (r["method"], r["url"], r["req"], r["res"])
            if k not in seen:
                seen.add(k); out.append(r)
        recs = out
    return recs


def pick(multi=True, title=None):
    return pick_files(IN, None, multi, title or L("Выберите файлы логов", "Choose log files"), TOOL)


# ---- маскирование секретов ----
MASKS = [(re.compile(r"(?i)(authorization|cookie|set-cookie|x-api-key|x-auth-token)(\s*[:=]\s*)([^\n\r]+)"), r"\1\2<masked>"),
         (re.compile(r"(?i)(\"?(?:access_?token|refresh_?token|id_?token|password|passwd|secret|api_?key|session_?id|sign)\"?\s*[:=]\s*\"?)([^\",&\s]{6,})"), r"\1<masked>"),
         (re.compile(r"(?i)bearer\s+[A-Za-z0-9._\-]{10,}"), "Bearer <masked>"),
         (re.compile(r"[\w.+-]+@[\w-]+\.[\w.]{2,}"), "<email>"), (re.compile(r"\beyJ[A-Za-z0-9_\-]{10,}\.[A-Za-z0-9_\-]{10,}\.[A-Za-z0-9_\-]*"), "<jwt>")]


def mask(text):
    for rx, rep in MASKS:
        text = rx.sub(rep, text)
    return text


# ---- Extract ----
def do_extract(pattern):
    fs = pick()
    if not fs:
        return
    o = checklist(TOOL, L("Опции вывода", "Output options"), [("urls", L("Список уникальных URL", "Unique URL list"), True),
                  ("decode", L("Показывать расшифрованные тела", "Show decoded bodies"), True), ("counts", L("Количество блоков по файлам", "Per-file block counts"), True),
                  ("dedupe", L("Удалять дубликаты", "Drop duplicates"), True), ("mask", L("Маскировать секреты", "Mask secrets"), False)])
    kw = [x.strip().lower() for x in mem_ask(TOOL, "kw", L("Ключевые слова (через запятую, пусто — все)", "Keywords (comma, empty = all)"), "", quit_ok=False).split(",") if x.strip()]
    recs = load_records(fs, pattern, 1, o["dedupe"])
    if kw:
        recs = sorted(recs, key=lambda r: 0 if any(k in r["raw"].lower() for k in kw) else 1)
    lines = ["Files: " + ", ".join(f.name for f in fs), "Blocks: %d" % len(recs), ""]
    if o["urls"]:
        lines += ["=== URLs ==="] + sorted({r["url"] for r in recs if r["url"]}) + [""]
    if o["counts"]:
        cnt = Counter(r["source"] for r in recs)
        lines += ["=== Per file ==="] + ["%s: %d" % kv for kv in cnt.items()] + [""]
    lines.append("=== Blocks ===")
    for r in recs:
        txt = r["raw"]
        if o["decode"]:
            for side in ("req", "res"):
                if r[side].strip():
                    obj, ch, enc = decoded(r, side)
                    shown = json.dumps(obj, ensure_ascii=False, indent=1) if isinstance(obj, (dict, list)) else str(obj)
                    txt += "\n[decoded %s | %s]\n%s" % (side, "→".join(ch), shown)
        lines.append(txt + "\n")
    text = "\n".join(lines)
    if o["mask"]:
        text = mask(text)
    p = OUT / ("Spylog_extract_%s.txt" % now_stamp())
    atomic_write(p, text)
    print("[+] %s  (%d %s)" % (p, len(recs), L("блоков", "blocks")))


# ---- Compare: различия по полям ----
def group_sig(recs):
    g = defaultdict(list)
    for r in recs:
        g[r["sig"]].append(r)
    return g


def compare(base, other, sides, noise):
    """Найти различия полей между двумя наборами записей → список находок (агрегировано)."""
    gb, go = group_sig(base), group_sig(other)
    agg = {}
    for sig in sorted(set(gb) & set(go)):
        for a, b in zip(gb[sig], go[sig]):
            for side in sides:
                (oa, ca, ea), (ob, cb, eb) = decoded(a, side), decoded(b, side)
                if isinstance(oa, (dict, list)) and isinstance(ob, (dict, list)):
                    diffs = K.diff(oa, ob)
                elif oa != ob:
                    diffs = [("$text", "changed", str(oa)[:200], str(ob)[:200])]
                else:
                    diffs = []
                for path, kind, old, new in diffs:
                    gp = K.generalize(path)
                    if noise and K.volatile(path, old, new):
                        continue
                    key = (sig, side, gp, kind)
                    f = agg.get(key)
                    if f:
                        f["count"] += 1
                    else:
                        agg[key] = {"sig": sig, "method": a["method"], "url": a["url"], "pattern": K.url_to_pattern(a["url"]) if a["url"] else "",
                                    "side": "response" if side == "res" else "request", "path": gp, "example_path": path, "kind": kind,
                                    "old": old, "new": new, "count": 1, "chain": ca, "enc": ea}
    return sorted(agg.values(), key=lambda f: (-f["count"], f["sig"], f["path"]))


def do_compare(pattern):
    k = menu(L("Что сравнивать", "What to compare"), [("1", L("Файлы (первый — базовый)", "Files (first = base)"), ""), ("2", L("Группы файлов", "File groups"), "")], tool=TOOL)
    if k == "q":
        return
    sets = []
    if k == "1":
        fs = pick(True, L("Выберите минимум 2 файла", "Choose at least 2 files"))
        if not fs or len(fs) < 2:
            print("[!] " + L("Нужно минимум 2 файла", "Need at least 2 files")); return
        sets = [[f] for f in fs]
    else:
        n = ask(L("Сколько групп (мин. 2)", "How many groups (min 2)"), "2", quit_ok=False)
        n = int(n) if n.isdigit() and int(n) >= 2 else 2
        for i in range(1, n + 1):
            fs = pick(True, L("Группа %d" % i, "Group %d" % i))
            if not fs:
                return
            sets.append(fs)
    o = checklist(TOOL, L("Параметры сравнения", "Compare options"), [("res", L("Тела ответов", "Response bodies"), True), ("req", L("Тела запросов", "Request bodies"), False),
                  ("noise", L("Скрывать «шумные» поля (время, id, токены)", "Hide noisy fields (time, ids, tokens)"), True), ("dedupe", L("Удалять дубликаты блоков", "Drop duplicate blocks"), True)])
    sig = menu(L("Сигнатура запроса", "Request signature"), [("1", L("Метод + полный URL", "Method + full URL"), ""), ("2", L("Метод + путь без параметров", "Method + path w/o query"), ""),
                                                           ("3", L("Метод + только путь", "Method + path only"), ""), ("4", L("Только метод", "Method only"), "")], tool=TOOL, show=True)
    sig = int(sig) if sig.isdigit() else 2
    sides = [s for s, on in (("res", o["res"]), ("req", o["req"])) if on] or ["res"]
    recsets = [load_records(s, pattern, sig, o["dedupe"]) for s in sets]
    allf = []
    for i in range(1, len(recsets)):
        with spin(L("Сравниваю набор 1 и %d" % (i + 1), "Comparing set 1 and %d" % (i + 1))):
            allf += compare(recsets[0], recsets[i], sides, o["noise"])
    if not allf:
        print("[!] " + L("Различий в полях не найдено (или нет общих сигнатур — попробуйте другой тип сигнатуры).", "No field differences (or no common signatures — try another signature type)."))
        return
    rows = [[str(i), trunc(f["sig"].split(" ", 1)[-1][-24:], 24), trunc(f["path"], 22), f["kind"][:4], trunc(K.short(f["old"], 14) + "→" + K.short(f["new"], 14), 26), str(f["count"])]
            for i, f in enumerate(allf[:40], 1)]
    table(rows, ["#", "URL", L("Поле", "Field"), "kind", "old→new", "n"])
    FIND.mkdir(parents=True, exist_ok=True)
    fp = FIND / ("findings_%s.json" % now_stamp())
    atomic_write(fp, json.dumps(allf, ensure_ascii=False, indent=1))
    rp = OUT / ("Spylog_compare_%s.txt" % now_stamp())
    atomic_write(rp, "\n".join("%s | %s | %s | %s: %s -> %s (x%d)" % (f["sig"], f["side"], f["path"], f["kind"], K.short(f["old"], 80), K.short(f["new"], 80), f["count"]) for f in allf))
    print("[+] %s\n[+] %s  (%d)" % (rp, fp, len(allf)))
    if confirm(L("Отправить находки в ScriptForge?", "Send findings to ScriptForge?"), True):
        run_sibling("scriptforge.py", ["--findings", str(fp)])


# ---- Explore: просмотр записей, поля, образец → ScriptForge ----
def do_explore(pattern):
    fs = pick()
    if not fs:
        return
    recs = load_records(fs, pattern, 1, True)
    if not recs:
        print("[!] " + L("Блоки [Spylog] не найдены — проверьте паттерн (пункт 8).", "No [Spylog] blocks found — check the pattern (item 8)."))
        return
    flt = ""
    while True:
        view = [r for r in recs if flt.lower() in r["url"].lower()] if flt else recs
        rows = [[str(i), r["method"][:4], trunc(r["host"], 18), trunc(urlparse(r["url"]).path, 22), "→".join(decoded(r, "res")[1])[:12]] for i, r in enumerate(view[:50], 1)]
        table(rows, ["#", "", "host", "path", "body"])
        v = ask(L("Номер записи / текст для фильтра URL / b — назад", "Record # / text to filter URL / b = back"), "", quit_ok=False)
        if v.lower() in ("b", "back", ""):
            return
        if not v.isdigit():
            flt = v
            continue
        if not 1 <= int(v) <= len(view[:50]):
            continue
        r = view[int(v) - 1]
        print("\n" + c("%s %s" % (r["method"], r["url"]), accent(), True))
        for side, lab in (("req", L("Запрос", "Request")), ("res", L("Ответ", "Response"))):
            if r[side].strip():
                obj, ch, enc = decoded(r, side)
                print(c("%s: %s, %s" % (lab, "→".join(ch), fmt_size(len(r[side]))), INFO_C))
                if isinstance(obj, (dict, list)):
                    for p, val in K.flatten(obj)[:30]:
                        print("   %s = %s" % (trunc(p, 30), trunc(K.short(val, 40), term_w() - 38)))
                else:
                    print("   " + trunc(str(obj).replace("\n", " "), term_w() - 6))
        if confirm(L("Отправить ответ как образец в ScriptForge?", "Send the response as a sample to ScriptForge?")):
            obj, ch, enc = decoded(r, "res")
            FIND.mkdir(parents=True, exist_ok=True)
            sp = FIND / ("sample_%s.json" % now_stamp())
            atomic_write(sp, json.dumps({"url": r["url"], "method": r["method"], "side": "response", "chain": ch, "enc": enc, "body": obj, "pattern": K.url_to_pattern(r["url"])}, ensure_ascii=False))
            run_sibling("scriptforge.py", ["--sample", str(sp)])


# ---- Search по значениям/ключам во всех ответах ----
def do_search(pattern):
    fs = pick()
    if not fs:
        return
    q = ask(L("Что искать (значение или ключ)", "What to find (value or key)"), "", quit_ok=False).lower()
    if not q:
        return
    n = 0
    for r in track(load_records(fs, pattern, 1, True), label=L("Поиск", "Search")):
        for side in ("req", "res"):
            if not r[side].strip():
                continue
            obj = decoded(r, side)[0]
            hits = [(p, v) for p, v in K.flatten(obj) if q in p.lower() or q in str(v).lower()] if isinstance(obj, (dict, list)) else ([("$text", obj)] if q in str(obj).lower() else [])
            for p, v in hits[:5]:
                n += 1
                if n <= 60:
                    print("  %s %s  %s = %s" % (c(r["method"], WARN_C), trunc(urlparse(r["url"]).path, 24), c(trunc(p, 26), INFO_C), trunc(K.short(v, 30), 24)))
    print(dim(L("совпадений: %d" % n, "matches: %d" % n)))


# ---- Stats ----
def do_stats(pattern):
    fs = pick()
    if not fs:
        return
    recs = load_records(fs, pattern, 1, False)
    print("[+] %s: %d" % (L("Всего блоков", "Total blocks"), len(recs)))
    for title, ctr in ((L("Хосты", "Hosts"), Counter(r["host"] for r in recs)), (L("Методы", "Methods"), Counter(r["method"] for r in recs)),
                       (L("Типы тел ответа", "Response body types"), Counter("→".join(decoded(r, "res")[1]) for r in recs if r["res"].strip()))):
        print(c(title, accent(), True))
        for k_, v in ctr.most_common(12):
            print("  %-34s %s" % (trunc(k_, 34), c(str(v), INFO_C)))


# ---- Mask ----
def do_mask():
    fs = pick(True, L("Какие файлы замаскировать", "Which files to mask"))
    for f in fs or []:
        p = OUT / ("masked_" + f.name)
        atomic_write(p, mask(smart_read(f)))
        print("[+] " + str(p))


def do_module():
    t = fetch_text(SPY_URL, label="Spy.module")
    if t:
        p = OUT / "Spy.module"
        atomic_write(p, t)
        print("[+] %s  (%d %s)" % (p, len(t.splitlines()), L("строк", "lines")))
        if clip_copy(t):
            print("[+] " + L("Скопировано в буфер iOS", "Copied to iOS clipboard"))
        print(dim(L("Включите модуль в Shadowrocket, поработайте с приложением, выгрузите лог в SpyLog/Input.", "Enable the module in Shadowrocket, use the app, export the log into SpyLog/Input.")))


def main():
    ensure_dirs("SpyLog/Input", "SpyLog/Output", "ScriptForge/Findings")
    pattern = ST.mem(TOOL, "pattern", "[Spylog]")
    while True:
        k = menu("SpyLog", [("1", L("Extract — извлечь блоки", "Extract blocks"), ""), ("2", L("Compare — различия по полям", "Compare — field differences"), ""),
                            ("3", L("Explore — просмотр записей и полей", "Explore records and fields"), ""), ("4", L("Search — поиск значения/ключа", "Search a value/key"), ""),
                            ("5", L("Stats — статистика", "Statistics"), ""), ("6", L("Mask — скрыть токены/cookie", "Mask tokens/cookies"), ""),
                            ("7", L("Паттерн поиска: ", "Search pattern: ") + pattern, ""), ("8", L("Получить Spy.module", "Get Spy.module"), ""),
                            ("9", L("Файлы и очистка", "Files & cleanup"), "")], tool=TOOL)
        if k == "q":
            return
        try:
            {"1": lambda: do_extract(pattern), "2": lambda: do_compare(pattern), "3": lambda: do_explore(pattern), "4": lambda: do_search(pattern),
             "5": lambda: do_stats(pattern), "6": do_mask, "8": do_module, "9": lambda: files_menu(TOOL, IN, OUT)}.get(k, lambda: None)()
        except KeyboardInterrupt:
            print("\n[*] " + L("Отменено", "Cancelled"))
        if k == "7":
            v = ask(L("Новый паттерн (пусто — отмена)", "New pattern (empty = cancel)"), "", quit_ok=False)
            if v:
                pattern = v
                ST.setmem(TOOL, "pattern", v)
        if k in "1234568":
            pause()


if __name__ == "__main__":
    run_tool("SpyLog", main)
TKEOF_spylog

tk_put scriptforge.py << 'TKEOF_scriptforge'
# -*- coding: utf-8 -*-
# ==========================================================================
#  ScriptForge — конструктор JS-скриптов Shadowrocket (http-request/response, cron,
#  event, dns, rule, generic; engine auto/jsc/webview).
#  Находит поля в образце (с раскодированием base64/gzip/percent/hex), предлагает
#  изменения, генерирует JS с обратным кодированием тела, блоки [Script]/[MITM],
#  модуль, тест в node/qjs и локальный сервер скриптов.
#  Шаблоны универсальные (без привязки к конкретным приложениям).
# ==========================================================================
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from tkcore import *
import tkcodec as K

TOOL = "scriptforge"
SF = BASE / "ScriptForge"
WS_FILE = SF / "workspace.json"
TYPES = ["http-response", "http-request", "cron", "event", "dns", "rule", "generic"]
DEF_BASE = "https://raw.githubusercontent.com/Krest-Neva/Shadowrocket/refs/heads/main/Scripts/"


# ==========================================================================
#  МОДЕЛЬ ПРОЕКТА
# ==========================================================================
def new_proj(name="script"):
    return {"name": name, "type": "http-response", "pattern": "", "requires_body": True, "max_size": -1, "binary": False, "timeout": 30,
            "engine": "auto", "argument": "", "debug": False, "ops": [], "hops": [], "urlops": [], "status": None, "redirect": "", "mock": None,
            "chain": ["json"], "enc": "utf-8", "sample": None, "sample_url": "", "cronexp": "0 8 * * *", "event": "network-changed",
            "interval": 0, "tpl": "", "desc": ""}


def load_ws():
    try:
        d = json.loads(WS_FILE.read_text("utf-8"))
        return d if isinstance(d, dict) and isinstance(d.get("scripts"), list) else {"scripts": []}
    except Exception:
        return {"scripts": []}


def save_ws(ws):
    s = json.dumps(ws, ensure_ascii=False)
    if len(s) > 4_000_000:                                    # слишком большие образцы не храним
        for p in ws["scripts"]:
            if len(json.dumps(p.get("sample"))) > 200000:
                p["sample"] = None
    atomic_write(WS_FILE, json.dumps(ws, ensure_ascii=False, indent=1))


# ==========================================================================
#  ГЕНЕРАТОР JS: вспомогательные функции (включаются только если нужны)
# ==========================================================================
JS_UTF8 = r"""
function utf8d(b){var s="",i=0,c;while(i<b.length){c=b[i++];if(c<128)s+=String.fromCharCode(c);else if(c>191&&c<224)s+=String.fromCharCode((c&31)<<6|b[i++]&63);else if(c>239){var u=((c&7)<<18|(b[i++]&63)<<12|(b[i++]&63)<<6|b[i++]&63)-65536;s+=String.fromCharCode(55296+(u>>10),56320+(u&1023));}else s+=String.fromCharCode((c&15)<<12|(b[i++]&63)<<6|b[i++]&63);}return s;}
function utf8e(s){var o=[];for(var i=0;i<s.length;i++){var c=s.charCodeAt(i);if(c<128)o.push(c);else if(c<2048)o.push(192|c>>6,128|c&63);else if(c>=55296&&c<56320){var d=s.charCodeAt(++i);c=65536+((c&1023)<<10|d&1023);o.push(240|c>>18,128|c>>12&63,128|c>>6&63,128|c&63);}else o.push(224|c>>12,128|c>>6&63,128|c&63);}return new Uint8Array(o);}
function toStr(b){return typeof b==="string"?b:(b instanceof ArrayBuffer?utf8d(new Uint8Array(b)):utf8d(b));}
"""
JS_B64 = r"""
var B64="ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/";
function b64d(s){s=s.replace(/-/g,"+").replace(/_/g,"/").replace(/[^A-Za-z0-9+\/]/g,"");var o=[],buf=0,bits=0;for(var i=0;i<s.length;i++){buf=buf<<6|B64.indexOf(s[i]);bits+=6;if(bits>=8){bits-=8;o.push(buf>>bits&255);}}return new Uint8Array(o);}
function b64e(b,url){var s="",i=0;for(;i+2<b.length;i+=3){var n=b[i]<<16|b[i+1]<<8|b[i+2];s+=B64[n>>18&63]+B64[n>>12&63]+B64[n>>6&63]+B64[n&63];}if(i<b.length){var n2=b[i]<<16|(i+1<b.length?b[i+1]<<8:0);s+=B64[n2>>18&63]+B64[n2>>12&63]+(i+1<b.length?B64[n2>>6&63]:"=")+"=";}if(url)s=s.replace(/\+/g,"-").replace(/\//g,"_").replace(/=+$/,"");return s;}
"""
JS_PATH = r"""
function walk(o,p,fn){if(!p.length||o===null||typeof o!=="object")return;var k=p[0],last=p.length===1;if(k==="*"){if(Array.isArray(o))for(var i=o.length-1;i>=0;i--){if(last)fn(o,i);else walk(o[i],p.slice(1),fn);}return;}if(k in o){if(last)fn(o,k);else walk(o[k],p.slice(1),fn);}}
function setDeep(o,p,v){for(var i=0;i<p.length-1;i++){if(o[p[i]]===undefined||o[p[i]]===null||typeof o[p[i]]!=="object")o[p[i]]={};o=o[p[i]];}o[p[p.length-1]]=v;}
function getOne(o,p){for(var i=0;i<p.length&&o!==undefined&&o!==null;i++)o=o[p[i]];return o;}
function deepDel(o,test){if(Array.isArray(o)){for(var i=0;i<o.length;i++)deepDel(o[i],test);}else if(o&&typeof o==="object"){Object.keys(o).forEach(function(k){if(test(k))delete o[k];else deepDel(o[k],test);});}}
"""
JS_HDR = r"""
function hfind(h,n){n=n.toLowerCase();for(var k in h)if(k.toLowerCase()===n)return k;return null;}
function hset(h,n,v){var k=hfind(h,n);h[k===null?n:k]=v;}
function hdel(h,n){var k=hfind(h,n);if(k!==null)delete h[k];}
"""


def ptoks(path):
    return json.dumps(K.tokens(path), ensure_ascii=False)


def js_ops(ops, var="obj"):
    """Операции над JSON → строки JS."""
    out = []
    for i, o in enumerate(ops, 1):
        t, ind = o.get("op"), "  "
        body = []
        if t == "set":
            v = json.dumps(o.get("value"), ensure_ascii=False)
            body.append("setDeep(%s,%s,%s);" % (var, ptoks(o["path"]), v) if o.get("create") and "*" not in o["path"]
                        else "walk(%s,%s,function(o,k){o[k]=%s;});" % (var, ptoks(o["path"]), v))
        elif t == "delete":
            body.append("walk(%s,%s,function(o,k){if(Array.isArray(o))o.splice(k,1);else delete o[k];});" % (var, ptoks(o["path"])))
        elif t == "regex":
            body.append("walk(%s,%s,function(o,k){if(typeof o[k]==='string')o[k]=o[k].replace(new RegExp(%s,%s),%s);});" % (
                var, ptoks(o["path"]), json.dumps(o["re"]), json.dumps(o.get("flags", "g")), json.dumps(o.get("repl", ""))))
        elif t == "push":
            body.append("walk(%s,%s,function(o,k){if(Array.isArray(o[k]))o[k].push(%s);});" % (var, ptoks(o["path"]), json.dumps(o.get("value"), ensure_ascii=False)))
        elif t == "filter":
            cmp_ = "x&&x[%s]===%s" % (json.dumps(o["key"]), json.dumps(o.get("eq"), ensure_ascii=False))
            body.append("walk(%s,%s,function(o,k){if(Array.isArray(o[k]))o[k]=o[k].filter(function(x){return %s(%s);});});" % (
                var, ptoks(o["path"]), "" if o.get("keep") else "!", cmp_))
        elif t == "deepdel":
            names = json.dumps(o.get("names", []))
            mode = o.get("mode", "prefix")
            test = {"prefix": "function(k){return %s.some(function(n){return k.indexOf(n)===0;});}" % names,
                    "exact": "function(k){return %s.indexOf(k)>=0;}" % names,
                    "regex": "function(k){return new RegExp(%s).test(k);}" % json.dumps(o.get("names", [""])[0])}[mode]
            body.append("deepDel(%s,%s);" % (var, test))
        elif t == "rename":
            body.append("walk(%s,%s,function(o,k){o[%s]=o[k];delete o[k];});" % (var, ptoks(o["path"]), json.dumps(o["to"])))
        elif t == "expr":
            body.append(o.get("code", ""))
        if o.get("when") and body:
            w = o["when"]
            body = ["if(JSON.stringify(getOne(%s,%s))===%s){" % (var, ptoks(w["path"]), json.dumps(json.dumps(w.get("eq"), ensure_ascii=False))), *["  " + b for b in body], "}"]
        out.append(ind + "// %d. %s %s" % (i, t, o.get("path", "")))
        out += [ind + b for b in body]
    return "\n".join(out)


def decode_steps(chain):
    """Строки JS: s (string) → obj согласно цепочке слоёв."""
    lines, needs_b64, ok = [], False, True
    for st in chain[:-1]:
        if st in ("b64", "b64url"):
            lines.append("s=utf8d(b64d(s));"); needs_b64 = True
        elif st == "percent":
            lines.append("s=decodeURIComponent(s);")
        elif st == "jsonstr":
            lines.append("s=JSON.parse(s);")
        elif st == "hex":
            lines.append("s=utf8d(new Uint8Array(s.match(/../g).map(function(h){return parseInt(h,16);})));")
        else:                                                      # gzip/zlib в JS недоступны
            lines.append("throw new Error('layer %s is not supported in JS');" % st); ok = False
    lines.append("obj=JSON.parse(s);" if chain[-1] == "json" else "obj=s;")
    return lines, needs_b64, ok


def encode_steps(chain):
    lines = ["s=JSON.stringify(obj);" if chain[-1] == "json" else "s=String(obj);"]
    for st in reversed(chain[:-1]):
        if st in ("b64", "b64url"):
            lines.append("s=b64e(utf8e(s),%s);" % ("true" if st == "b64url" else "false"))
        elif st == "percent":
            lines.append("s=encodeURIComponent(s);")
        elif st == "jsonstr":
            lines.append("s=JSON.stringify(s);")
        elif st == "hex":
            lines.append("s=Array.prototype.map.call(utf8e(s),function(b){return ('0'+b.toString(16)).slice(-2);}).join('');")
    return lines


ARG_JS = ("var ARG=(function(){try{if(typeof $argument==='string'&&$argument){try{return JSON.parse($argument);}catch(e){var r={};$argument.split('&').forEach(function(p){var kv=p.split('=');"
          "if(kv[0])r[kv[0]]=decodeURIComponent(kv.slice(1).join('='));});return r;}}return (typeof $argument==='object'&&$argument)||{};}catch(e){return {};}})();")

SKEL = {
    "cron": "// Периодическая задача: запрос + уведомление\n$httpClient.get({url: ARG.url || 'https://example.com', timeout: 10}, function(err, resp, data){\n  if (err) { console.log('error: ' + err); $done(); return; }\n  console.log('status ' + resp.status + ', ' + (data||'').length + ' bytes');\n  // $notification.post('Cron', 'status ' + resp.status, '');\n  $done();\n});",
    "event": "// Событие (network-changed / notification): $event, $network\nvar net = (typeof $network !== 'undefined' && $network) || {};\nvar ssid = net.wifi && net.wifi.ssid;\nconsole.log('event: ' + JSON.stringify($event || {}) + ', ssid=' + ssid);\n// $notification.post('Network', ssid ? 'Wi-Fi: ' + ssid : 'Cellular', '');\n$done();",
    "dns": "// DNS-скрипт: $domain — запрошенное имя; ответ: адрес (проверьте формат в документации клиента)\nvar map = ARG.map || {};\nif (typeof $domain !== 'undefined' && map[$domain]) { $done({address: map[$domain], ttl: 60}); } else { $done({}); }",
    "rule": "// Rule-скрипт (SCRIPT,имя,политика): решает, подходит ли запрос\nvar url = (typeof $request !== 'undefined' && $request.url) || '';\nvar matched = /example\\.com/.test(url);   // TODO: ваше условие\n$done({matched: matched});",
    "generic": "// Generic: произвольная логика\nconsole.log('generic script started');\n$done();",
}


def gen_js(P):
    """Собрать JS-код проекта."""
    t = P["type"]
    head = "/*\n * %s — %s\n * Generated by Shadowrocket Toolkit / ScriptForge. Type: %s\n%s */\n" % (
        P["name"], P.get("desc") or "script", t, (" * Pattern: %s\n" % P["pattern"]) if P.get("pattern") else "")
    code = [head, ARG_JS]
    if t in ("cron", "event", "dns", "rule", "generic"):
        code.append(P.get("body_js") or SKEL[t])
        return "\n".join(code) + "\n"
    chain = P.get("chain") or ["json"]
    ops, hops, uops = P.get("ops", []), P.get("hops", []), P.get("urlops", [])
    is_res = t == "http-response"
    objname = "$response" if is_res else "$request"
    dec, need_b64, dec_ok = decode_steps(chain)
    helpers = [JS_UTF8]
    if need_b64 or any(s in ("b64", "b64url") for s in chain):
        helpers.append(JS_B64)
    if ops:
        helpers.append(JS_PATH)
    if hops:
        helpers.append(JS_HDR)
    code += helpers
    # короткие ответы без чтения тела: mock / redirect / reject
    if not is_res and (P.get("mock") is not None or P.get("redirect")):
        if P.get("redirect"):
            code.append("$done({response:{status:%d,headers:{Location:%s}}});" % (P.get("status") or 302, json.dumps(P["redirect"])))
        else:
            m = P["mock"]
            code.append("$done({response:{status:%d,headers:{'Content-Type':%s},body:%s}});" % (
                P.get("status") or 200, json.dumps(m.get("ctype", "application/json")), json.dumps(m["body"] if isinstance(m["body"], str) else json.dumps(m["body"], ensure_ascii=False))))
        return "\n".join(code) + "\n"
    main = ["(function main(){", "  var hdrs = Object.assign({}, %s.headers || {});" % objname]
    for h in hops:
        if h["side"] == ("res" if is_res else "req"):
            fn = {"set": "hset(hdrs,%s,%s);" % (json.dumps(h["name"]), json.dumps(h.get("value", ""))), "del": "hdel(hdrs,%s);" % json.dumps(h["name"]),
                  "append": "hset(hdrs,%s,(hdrs[hfind(hdrs,%s)||%s]?hdrs[hfind(hdrs,%s)]+', ':'')+%s);" % tuple(
                      [json.dumps(h["name"])] * 2 + [json.dumps(h["name"])] * 1 + [json.dumps(h["name"]), json.dumps(h.get("value", ""))])}[h["action"]]
            main.append("  " + fn)
    if not is_res:
        main.append("  var url = $request.url;")
        for u in uops:
            main.append("  url = url.replace(new RegExp(%s,%s),%s);" % (json.dumps(u["re"]), json.dumps(u.get("flags", "")), json.dumps(u.get("repl", ""))))
    if ops or P.get("body_edit"):
        main += ["  var raw = %s.body;" % objname, "  if (raw === undefined || raw === null || raw === '') { $done({%s}); return; }" % ("headers:hdrs" if hops else ""),
                 "  var wasBytes = typeof raw !== 'string';", "  var s = toStr(raw), obj;", "  try {"]
        main += ["    " + l_ for l_ in dec]
        main += ["  } catch (e) { console.log('[%s] decode failed: ' + e); $done({}); return; }" % P["name"], "  // ---- операции ----", js_ops(ops)]
        main += ["  // ---- обратное кодирование (слои: %s) ----" % "→".join(chain)] + ["  " + l_ for l_ in encode_steps(chain)]
        main.append("  var out = wasBytes ? utf8e(s) : s;")
    done = []
    if ops:
        done.append("body: out")
    if hops:
        done.append("headers: hdrs")
    if is_res and P.get("status"):
        done.append("status: %d" % P["status"])
    if not is_res:
        if uops:
            done.append("url: url")
    main.append("  $done({%s});" % ", ".join(done))
    main.append("})();")
    code += main
    return "\n".join(code) + "\n"


# ==========================================================================
#  БЛОКИ [Script] / [MITM] / модуль
# ==========================================================================
def hosts_from_pattern(p):
    """Хосты из regex-паттерна (best-effort). Возвращает (список, предупреждения)."""
    m = re.search(r"(?:https?:?\??|https\?)?:?(?:\\?/){2}([^\\/]+(?:\\.[^\\/]+)*?)(?:\\?/|$)", p.replace("^", "")) or re.search(r"//([^/]+)", p)
    if not m:
        return [], [L("не удалось выделить хост", "could not extract host")]
    seg = m.group(1).replace("\\.", ".")
    seg = re.sub(r"\(:443\)\??", "", seg)
    alts = [seg]
    g = re.search(r"\(([^()]+)\)", seg)
    if g and "|" in g.group(1):
        alts = [seg[:g.start()] + a + seg[g.end():] for a in g.group(1).split("|")]
    out, warn = [], []
    for a in alts:
        a = re.sub(r"\(\?:?", "", a).replace(".*", "*").replace("[\\w-]+", "*").replace("[^.]+", "*").replace("[\\w.-]+", "*").replace(")?", "")
        if re.search(r"[\[\]()?+\\^$|]", a):
            warn.append(L("хост «%s» сложный — проверьте вручную" % a, "host '%s' is complex — check manually" % a))
        out.append(a)
    return out, warn


def script_line(P, base):
    t = P["type"]
    parts = ["type=" + t]
    if t in ("http-request", "http-response"):
        parts.append("pattern=" + (P["pattern"] or "^https:\\/\\/example\\.com\\/"))
        parts.append("requires-body=%d" % (1 if P["requires_body"] else 0))
        if P.get("max_size") not in (None, ""):
            parts.append("max-size=%s" % P["max_size"])
        if P["binary"]:
            parts.append("binary-body-mode=1")
    elif t == "cron":
        parts.append('cronexp="%s"' % P["cronexp"])
    elif t == "event":
        parts.append("event-name=" + P["event"])
    parts.append("script-path=" + (base.rstrip("/") + "/" if base else "") + P["name"] + ".js")
    if P.get("argument"):
        parts.append("argument=" + P["argument"])
    if P["engine"] != "auto":
        parts.append("engine=" + P["engine"])
    parts.append("timeout=%d" % P["timeout"])
    if P.get("interval"):
        parts.append("script-update-interval=%d" % P["interval"])
    if P["debug"]:
        parts.append("debug=1")
    return "%s = %s" % (P["name"], ",".join(parts))


def build_blocks(projs, base):
    lines = ["[Script]"] + [script_line(p, base) for p in projs]
    hosts, warns = [], []
    for p in projs:
        if p["type"] in ("http-request", "http-response") and p.get("pattern"):
            h, w = hosts_from_pattern(p["pattern"])
            hosts += [x for x in h if x not in hosts]
            warns += w
    if hosts:
        lines += ["", "[MITM]", "hostname = %APPEND% " + ",".join(hosts)]
    return "\n".join(lines), warns


def build_module(projs, base, name, desc):
    blocks, warns = build_blocks(projs, base)
    return "#!name=%s\n#!desc=%s\n\n%s\n" % (name, desc, blocks), warns


def parse_script_lines(text):
    """Разобрать существующие строки [Script] (в т.ч. из вашего конфига) → список проектов."""
    res = []
    for raw in text.splitlines():
        m = re.match(r"^\s*([^#=\s][^=]*?)\s*=\s*(type=.*)$", raw)
        if not m:
            continue
        name, rest = m.group(1).strip(), m.group(2)
        kv = {}
        for part in re.findall(r'(?:[^,"{]|"[^"]*"|\{[^}]*\})+', rest):
            if "=" in part:
                k, v = part.split("=", 1)
                kv[k.strip()] = v.strip()
        P = new_proj(re.sub(r"[^\w\-]", "_", name))
        P["type"] = kv.get("type", "http-response") if kv.get("type") in TYPES else "http-response"
        P["pattern"] = kv.get("pattern", "")
        P["requires_body"] = kv.get("requires-body", "0") in ("1", "true")
        P["max_size"] = int(kv["max-size"]) if re.fullmatch(r"-?\d+", kv.get("max-size", "")) else P["max_size"]
        P["binary"] = kv.get("binary-body-mode", "0") in ("1", "true")
        P["timeout"] = int(kv["timeout"]) if kv.get("timeout", "").isdigit() else 30
        P["engine"] = kv.get("engine", "auto") if kv.get("engine") in ("auto", "jsc", "webview") else "auto"
        P["argument"] = kv.get("argument", "")
        P["cronexp"] = kv.get("cronexp", "").strip('"') or P["cronexp"]
        P["event"] = kv.get("event-name", P["event"])
        P["sample_url"] = kv.get("script-path", "")
        res.append(P)
    return res


# ==========================================================================
#  ИНТЕРФЕЙС
# ==========================================================================
def sugg_values(v):
    t = K.walk_type(v)
    return {"bool": [(not v, L("инвертировать", "invert"))], "number": [(0, "0"), (-1, "-1"), (999999, "999999"), (v + 1 if isinstance(v, (int, float)) else 1, "+1")],
            "string": [("", L("пустая строка", "empty string"))], "null": [({}, "{}"), ([], "[]"), ("", '""')], "array": [([], L("очистить []", "clear []"))], "object": [({}, L("пустой {}", "empty {}"))]}[t]


def json_in(label, default=""):
    v = ask(label, default, quit_ok=False)
    try:
        return json.loads(v)
    except Exception:
        return v                                              # не JSON → строка


def op_wizard(P, path, cur=None):
    """Мастер операции для поля path (cur — текущее значение из образца)."""
    items = [("1", L("Установить значение", "Set value"), ""), ("2", L("Удалить поле", "Delete field"), ""), ("3", L("Заменить в строке (regex)", "Regex replace in string"), ""),
             ("4", L("Добавить элемент в массив", "Push into array"), ""), ("5", L("Оставить/убрать элементы массива по полю", "Filter array items by field"), ""), ("6", L("Переименовать ключ", "Rename key"), "")]
    k = menu(L("Операция над: ", "Operation on: ") + path, items, show=True)
    if k == "q":
        return
    op = None
    if k == "1":
        sg = sugg_values(cur) if cur is not None else []
        for i, (v, lab) in enumerate(sg, 1):
            print("  %s %s  %s" % (c(str(i), accent(), True), K.short(v, 30), dim(lab)))
        v = ask(L("Номер подсказки или своё значение (JSON: true, 5, \"текст\", {})", "Hint # or your value (JSON: true, 5, \"text\", {})"), "1" if sg else "", quit_ok=False)
        val = sg[int(v) - 1][0] if v.isdigit() and sg and 1 <= int(v) <= len(sg) else (json.loads(v) if re.match(r"^(true|false|null|-?\d+(\.\d+)?|\"|\[|\{)", v) else v)
        op = {"op": "set", "path": path, "value": val, "create": confirm(L("Создать поле, если его нет?", "Create the field if missing?"))}
    elif k == "2":
        op = {"op": "delete", "path": path}
    elif k == "3":
        re_ = ask("regex", "", quit_ok=False)
        op = {"op": "regex", "path": path, "re": re_, "flags": "g", "repl": ask(L("Замена", "Replacement"), "", quit_ok=False)}
    elif k == "4":
        op = {"op": "push", "path": path, "value": json_in(L("Значение (JSON)", "Value (JSON)"))}
    elif k == "5":
        op = {"op": "filter", "path": path, "key": ask(L("Поле элемента", "Item field"), "", quit_ok=False), "eq": json_in(L("Значение (JSON)", "Value (JSON)")),
              "keep": confirm(L("Оставить только совпадающие? (нет — удалить совпадающие)", "Keep only matching? (no = remove matching)"))}
    elif k == "6":
        op = {"op": "rename", "path": path, "to": ask(L("Новое имя", "New name"), "", quit_ok=False)}
    if op:
        w = ask(L("Условие 'путь=значение' (Enter — без условия)", "Condition 'path=value' (Enter = none)"), "", quit_ok=False)
        if "=" in w:
            wp, wv = w.split("=", 1)
            try:
                wv = json.loads(wv)
            except Exception:
                pass
            op["when"] = {"path": wp.strip(), "eq": wv}
        P["ops"].append(op)
        print("[+] " + L("Операция добавлена", "Operation added"))


def explorer(P):
    s = P.get("sample")
    if not isinstance(s, (dict, list)):
        print("[!] " + L("Сначала загрузите образец JSON (пункт «Образец»).", "Load a JSON sample first ('Sample' item).")); return
    flt = ""
    while True:
        seen, rows = {}, []
        for p, v in K.flatten(s):
            g = K.generalize(p)
            if g not in seen:
                seen[g] = v; rows.append((g, v))
        view = [(g, v) for g, v in rows if flt.lower() in g.lower() or flt.lower() in str(v).lower()][:60]
        for i, (g, v) in enumerate(view, 1):
            print("%s %-3s %s = %s" % (c("%3d" % i, accent(), True), dim(K.walk_type(v)[:3]), c(trunc(g, 28), INFO_C), trunc(K.short(v, 30), term_w() - 42)))
        n = ask(L("Номер поля / текст для фильтра / Enter — назад", "Field # / filter text / Enter = back"), "", quit_ok=False)
        if not n:
            return
        if n.isdigit() and 1 <= int(n) <= len(view):
            op_wizard(P, view[int(n) - 1][0], view[int(n) - 1][1])
        else:
            flt = n


def load_sample(P):
    k = menu(L("Образец", "Sample"), [("1", L("Файл JSON/текст", "JSON/text file"), ""), ("2", L("Вставить текст", "Paste text"), ""), ("3", L("Файл из SpyLog/Findings", "File from SpyLog/Findings"), ""), ("4", L("Буфер iOS", "iOS clipboard"), "")], show=False)
    raw = None
    if k == "1":
        fs = pick_files(SF / "Input", None, False, tool=TOOL)
        raw = fs[0].read_bytes() if fs else None
    elif k == "2":
        buf, blank = [], 0
        while blank < 2:
            l_ = input(""); blank = blank + 1 if not l_.strip() else 0; buf.append(l_)
        raw = "\n".join(buf).encode()
    elif k == "3":
        fs = pick_files(SF / "Findings", {".json"}, False, tool=TOOL)
        if fs:
            d = json.loads(fs[0].read_text("utf-8"))
            if isinstance(d, dict) and "body" in d:
                P.update(sample=d["body"], chain=d.get("chain", ["json"]), enc=d.get("enc", "utf-8"), pattern=d.get("pattern") or P["pattern"], sample_url=d.get("url", ""))
                print("[+] " + L("Образец загружен: ", "Sample loaded: ") + "→".join(P["chain"])); return
    elif k == "4":
        try:
            raw = open("/dev/clipboard", "rb").read()
        except Exception:
            print("[!] n/a")
    if raw:
        try:
            obj, ch, enc = K.smart_decode(raw)
        except Exception as e:
            print("[!] " + L("Файл повреждён или формат не поддерживается: %s" % e, "Damaged or unsupported: %s" % e)); return
        P.update(sample=obj, chain=ch, enc=enc)
        print("[+] %s: %s | %s" % (L("Образец", "Sample"), "→".join(ch), L("JSON-поля: %d" % len(K.flatten(obj)), "JSON fields: %d" % len(K.flatten(obj))) if isinstance(obj, (dict, list)) else L("текст", "text")))


def import_findings(P, path):
    try:
        fs = json.loads(open(path, encoding="utf-8").read())
    except Exception as e:
        print("[!] %s" % e); return
    rows = [[str(i), f["side"][:3], trunc(f["path"], 24), f["kind"][:4], trunc(K.short(f["old"], 12) + "→" + K.short(f["new"], 12), 24), str(f["count"])] for i, f in enumerate(fs[:60], 1)]
    table(rows, ["#", "", L("Поле", "Field"), "kind", "old→new", "n"])
    sel = ask_multi(L("Какие различия превратить в операции", "Which differences become operations"), len(fs))
    if not sel:
        return
    mode = ask(L("Режим: 1 — привести к НОВЫМ значениям, 2 — к СТАРЫМ", "Mode: 1 = apply NEW values, 2 = apply OLD values"), "1", quit_ok=False)
    for i in sel:
        f = fs[i - 1]
        new_is_target = mode != "2"
        tgt = f["new"] if new_is_target else f["old"]
        kind = f["kind"]
        gone = (kind == "removed" and new_is_target) or (kind == "added" and not new_is_target)
        if f["path"].endswith("[*]"):
            if not gone:
                P["ops"].append({"op": "push", "path": f["path"][:-3], "value": tgt})
            continue
        P["ops"].append({"op": "delete", "path": f["path"]} if gone else {"op": "set", "path": f["path"], "value": tgt, "create": kind in ("added", "removed")})
    f0 = fs[sel[0] - 1]
    P.update(type="http-response" if f0["side"] == "response" else "http-request", pattern=P["pattern"] or f0.get("pattern", ""), chain=f0.get("chain", ["json"]), enc=f0.get("enc", "utf-8"))
    print("[+] " + L("Добавлено операций: %d" % len(sel), "Operations added: %d" % len(sel)))


def edit_ops(P):
    while True:
        for i, o in enumerate(P["ops"], 1):
            print("%s %-8s %-28s %s" % (c("%2d" % i, accent(), True), o["op"], trunc(o.get("path", o.get("names", "")), 28), dim(trunc(K.short(o.get("value", o.get("repl", "")), 20), 20))))
        k = menu(L("Операции", "Operations"), [("1", L("Добавить вручную (путь)", "Add by path"), ""), ("2", L("Удалить ключи по имени везде (deepdel)", "Delete keys by name everywhere"), ""), ("3", L("Удалить операцию", "Remove operation"), ""),
                                              ("4", L("Своё JS-выражение (obj)", "Custom JS (obj)"), ""), ("5", L("Очистить все", "Clear all"), "")], show=False)
        if k == "q":
            return
        if k == "1":
            op_wizard(P, ask(L("Путь (a.b[*].c)", "Path (a.b[*].c)"), "", quit_ok=False))
        elif k == "2":
            nm = [x.strip() for x in ask(L("Имена/префиксы через запятую", "Names/prefixes, comma"), "", quit_ok=False).split(",") if x.strip()]
            P["ops"].append({"op": "deepdel", "names": nm, "mode": {"1": "prefix", "2": "exact", "3": "regex"}.get(ask("1 prefix, 2 exact, 3 regex", "1", quit_ok=False), "prefix")})
        elif k == "3":
            for i in sorted(ask_multi(L("Номера", "Numbers"), len(P["ops"])) or [], reverse=True):
                P["ops"].pop(i - 1)
        elif k == "4":
            P["ops"].append({"op": "expr", "code": ask("JS", "", quit_ok=False)})
        elif k == "5" and confirm(L("Очистить?", "Clear?")):
            P["ops"] = []


def edit_headers(P):
    k = menu(L("Заголовки / статус / mock / редирект", "Headers / status / mock / redirect"), [("1", L("Заголовок: установить/удалить/добавить", "Header: set/delete/append"), ""), ("2", L("Статус ответа", "Response status"), ""),
                                                                                              ("3", L("Mock-ответ (запрос → готовый ответ)", "Mock response (request → ready reply)"), ""), ("4", L("Редирект (302/307)", "Redirect (302/307)"), ""),
                                                                                              ("5", L("Переписать URL запроса (regex)", "Rewrite request URL (regex)"), ""), ("6", L("Сбросить это всё", "Reset all of these"), "")], show=False)
    if k == "1":
        P["hops"].append({"side": "res" if P["type"] == "http-response" else "req", "action": {"1": "set", "2": "del", "3": "append"}.get(ask("1 set, 2 del, 3 append", "1", quit_ok=False), "set"),
                          "name": ask(L("Имя заголовка", "Header name"), "", quit_ok=False), "value": ask(L("Значение", "Value"), "", quit_ok=False)})
    elif k == "2":
        s = ask(L("Код (Enter — не менять)", "Code (Enter = keep)"), "", quit_ok=False)
        P["status"] = int(s) if s.isdigit() else None
    elif k == "3":
        P["type"] = "http-request"
        P["mock"] = {"ctype": ask("Content-Type", "application/json", quit_ok=False), "body": json_in(L("Тело (JSON или текст)", "Body (JSON or text)"), "{}")}
        P["redirect"] = ""
    elif k == "4":
        P["type"] = "http-request"; P["redirect"] = ask("Location", "", quit_ok=False); P["status"] = 302; P["mock"] = None
    elif k == "5":
        P["urlops"].append({"re": ask("regex", "", quit_ok=False), "repl": ask(L("Замена ($1…)", "Replacement ($1…)"), "", quit_ok=False)})
    elif k == "6":
        P.update(hops=[], urlops=[], status=None, mock=None, redirect="")


def settings_menu(P):
    while True:
        k = menu(L("Параметры [Script]", "[Script] options"), [
            ("1", L("Имя", "Name"), P["name"]), ("2", L("Тип", "Type"), P["type"]), ("3", L("Паттерн URL (regex)", "URL pattern (regex)"), trunc(P["pattern"], 22)),
            ("4", "requires-body", str(P["requires_body"])), ("5", "max-size", str(P["max_size"])), ("6", "binary-body-mode", str(P["binary"])), ("7", "timeout", str(P["timeout"])),
            ("8", "engine", P["engine"]), ("9", "argument", trunc(P["argument"], 22)), ("10", "cronexp / event-name", "%s / %s" % (P["cronexp"], P["event"])), ("11", "script-update-interval", str(P["interval"])),
            ("12", "debug", str(P["debug"])), ("13", L("Описание", "Description"), trunc(P["desc"], 20))], show=False)
        if k == "q":
            return
        if k == "1":
            P["name"] = sanitize_filename(ask(L("Имя", "Name"), P["name"], quit_ok=False))
        elif k == "2":
            P["type"] = TYPES[int(ask(" ".join("%d=%s" % (i, t) for i, t in enumerate(TYPES, 1)), "1", quit_ok=False)) - 1]
        elif k == "3":
            how = ask(L("1 — ввести regex, 2 — из примера ссылки, 3 — открыть RegexBuilder", "1 type regex, 2 from sample URL, 3 open RegexBuilder"), "2", quit_ok=False)
            if how == "3":
                run_sibling("regexb.py")
                P["pattern"] = ask(L("Вставьте готовый regex", "Paste the regex"), P["pattern"], quit_ok=False)
            else:
                v = ask(L("Ссылка-пример" if how == "2" else "Regex", "Sample URL" if how == "2" else "Regex"), P["sample_url"], quit_ok=False)
                P["pattern"] = K.url_to_pattern(v) if how == "2" and v.startswith("http") else v
            try:
                re.compile(P["pattern"]); print("[+] " + P["pattern"])
            except re.error as e:
                print("[!] regex: %s" % e)
        elif k in ("4", "6", "12"):
            key = {"4": "requires_body", "6": "binary", "12": "debug"}[k]; P[key] = not P[key]
        elif k in ("5", "7", "11"):
            key = {"5": "max_size", "7": "timeout", "11": "interval"}[k]; v = ask(key, str(P[key]), quit_ok=False)
            P[key] = int(v) if re.fullmatch(r"-?\d+", v) else P[key]
        elif k == "8":
            P["engine"] = {"auto": "jsc", "jsc": "webview"}.get(P["engine"], "auto")
        elif k == "9":
            P["argument"] = ask("argument", P["argument"], quit_ok=False)
        elif k == "10":
            P["cronexp"] = ask("cronexp", P["cronexp"], quit_ok=False); P["event"] = ask("event-name", P["event"], quit_ok=False)
        elif k == "13":
            P["desc"] = ask(L("Описание", "Description"), P["desc"], quit_ok=False)


def run_test(P, js):
    rt = shutil.which("node") or shutil.which("qjs")
    if not rt:
        print("[!] " + L("Нет node/qjs. Меню «Среда» → установить опциональное (nodejs/quickjs).", "No node/qjs. 'Environment' menu → install optional (nodejs/quickjs).")); return
    chain = P.get("chain") or ["json"]
    body = K.smart_encode(P["sample"], chain, P.get("enc", "utf-8")).decode("utf-8", "replace") if P.get("sample") is not None else ""
    harness = ("var $argument=%s;var $request={url:%s,method:'GET',headers:{},body:%s};var $response={status:200,headers:{'Content-Type':'application/json'},body:%s};"
               "var $persistentStore={read:function(){return null;},write:function(){return true;}};var $notification={post:function(){}};var $network={};var $event={};"
               "var $httpClient={get:function(o,cb){cb(null,{status:200,headers:{}},'{}');},post:function(o,cb){cb(null,{status:200,headers:{}},'{}');}};"
               "function $done(o){console.log('__DONE__'+JSON.stringify(o===undefined?null:o));}\n%s\n") % (
        json.dumps(P["argument"]), json.dumps(P.get("sample_url") or "https://example.com/"), json.dumps(body if P["type"] == "http-request" else ""), json.dumps(body), js)
    p = SF / "Output" / "_harness.js"
    atomic_write(p, harness)
    try:
        r = subprocess.run([rt, str(p)], capture_output=True, text=True, timeout=30)
    except Exception as e:
        print("[!] %s" % e); return
    out = r.stdout + r.stderr
    m = re.search(r"__DONE__(.*)", out)
    print(dim(trunc(out.replace("__DONE__", "").strip(), 300)))
    if not m:
        print("[!] " + L("$done не вызван", "$done not called")); return
    res = json.loads(m.group(1) or "null") or {}
    nb = res.get("body")
    if nb is not None and P.get("sample") is not None:
        try:
            obj, ch2, _ = K.smart_decode(nb if isinstance(nb, str) else bytes(nb.values() if isinstance(nb, dict) else nb))
            ds = K.diff(P["sample"], obj) if isinstance(obj, (dict, list)) else []
            print("[+] %s: %d" % (L("Изменений в теле", "Body changes"), len(ds)))
            for p_, kd, o, n in ds[:25]:
                print("  %s %s: %s → %s" % (c(kd[:4], WARN_C), p_, K.short(o, 20), K.short(n, 20)))
        except Exception as e:
            print("[!] " + L("Результат не раскодирован: %s" % e, "Result not decodable: %s" % e))
    else:
        print("[+] " + json.dumps(res, ensure_ascii=False)[:300])


def serve_scripts():
    import http.server, socketserver, threading
    port = int(ask("port", "8765", quit_ok=False) or 8765)
    d = str(SF / "Scripts")
    class H(http.server.SimpleHTTPRequestHandler):
        def __init__(s, *a, **k): super().__init__(*a, directory=d, **k)
        def log_message(s, *a): pass
    srv = socketserver.TCPServer(("127.0.0.1", port), H)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    print("[+] http://127.0.0.1:%d/  (%s)" % (port, d))
    print(dim(L("Работает, пока открыт этот экран. iSH должен быть активен. Enter — остановить.", "Runs while this screen is open. iSH must stay active. Enter = stop.")))
    pause("")
    srv.shutdown()


def project_menu(ws):
    while True:
        for i, p in enumerate(ws["scripts"], 1):
            print("%s %-22s %-14s ops:%d" % (c("%2d" % i, accent(), True), trunc(p["name"], 22), p["type"], len(p["ops"])))
        k = menu(L("Проекты скриптов", "Script projects"), [("1", L("Новый", "New"), ""), ("2", L("Открыть №", "Open #"), ""), ("3", L("Дублировать №", "Duplicate #"), ""), ("4", L("Удалить №", "Delete #"), ""),
                                                          ("5", L("Импорт строк [Script] (из конфига)", "Import [Script] lines (from config)"), "")], show=False)
        if k == "q":
            return None
        if k == "1":
            ws["scripts"].append(new_proj(sanitize_filename(ask(L("Имя", "Name"), "script%d" % (len(ws["scripts"]) + 1), quit_ok=False)))); save_ws(ws)
            return ws["scripts"][-1]
        n = ask(L("Номер", "Number"), "", quit_ok=False) if k in "234" else ""
        if k == "2" and n.isdigit() and 1 <= int(n) <= len(ws["scripts"]):
            return ws["scripts"][int(n) - 1]
        if k == "3" and n.isdigit() and 1 <= int(n) <= len(ws["scripts"]):
            import copy
            q = copy.deepcopy(ws["scripts"][int(n) - 1]); q["name"] += "_copy"; ws["scripts"].append(q); save_ws(ws)
        if k == "4" and n.isdigit() and 1 <= int(n) <= len(ws["scripts"]) and confirm(L("Удалить?", "Delete?")):
            ws["scripts"].pop(int(n) - 1); save_ws(ws)
        if k == "5":
            buf, blank = [], 0
            print(dim(L("Вставьте строки [Script], две пустые — конец.", "Paste [Script] lines, two blank = end.")))
            while blank < 2:
                l_ = input(""); blank = blank + 1 if not l_.strip() else 0; buf.append(l_)
            ps = parse_script_lines("\n".join(buf))
            ws["scripts"] += ps; save_ws(ws)
            print("[+] " + L("Импортировано: %d" % len(ps), "Imported: %d" % len(ps)))


def main():
    ensure_dirs("ScriptForge/Input", "ScriptForge/Output", "ScriptForge/Scripts", "ScriptForge/Findings")
    ws = load_ws()
    P = None
    args = sys.argv[1:]
    if args:
        P = new_proj("script%d" % (len(ws["scripts"]) + 1)); ws["scripts"].append(P)
        if args[0] == "--findings" and len(args) > 1:
            import_findings(P, args[1])
        elif args[0] == "--sample" and len(args) > 1:
            d = json.loads(open(args[1], encoding="utf-8").read())
            P.update(sample=d["body"], chain=d.get("chain", ["json"]), enc=d.get("enc", "utf-8"), pattern=d.get("pattern", ""), sample_url=d.get("url", ""))
        save_ws(ws)
    while True:
        if P is None:
            P = project_menu(ws)
            if P is None:
                return
        k = menu(L("ScriptForge: %s [%s]" % (P["name"], P["type"]), "ScriptForge: %s [%s]" % (P["name"], P["type"])), [
            ("1", L("Образец ответа/запроса", "Response/request sample"), "→".join(P["chain"]) if P.get("sample") is not None else L("нет", "none")),
            ("2", L("Поля образца → операции", "Sample fields → operations"), ""), ("3", L("Операции", "Operations"), str(len(P["ops"]))),
            ("4", L("Заголовки, статус, mock, редирект", "Headers, status, mock, redirect"), ""), ("5", L("Параметры [Script] и паттерн", "[Script] options & pattern"), trunc(P["pattern"], 18)),
            ("6", L("Импорт находок SpyLog", "Import SpyLog findings"), ""), ("7", L("Шаблоны (cron/event/dns/rule/generic)", "Templates (cron/event/dns/rule/generic)"), ""),
            ("8", L("Сгенерировать и сохранить JS", "Generate & save JS"), ""), ("9", L("Блоки [Script]/[MITM] и модуль", "[Script]/[MITM] blocks & module"), ""),
            ("10", L("Тест в node/qjs", "Test in node/qjs"), ""), ("11", L("Локальный сервер скриптов", "Local script server"), ""), ("12", L("Другой проект", "Another project"), "")], tool=TOOL)
        if k == "q":
            save_ws(ws); return
        try:
            if k == "1": load_sample(P)
            elif k == "2": explorer(P)
            elif k == "3": edit_ops(P)
            elif k == "4": edit_headers(P)
            elif k == "5": settings_menu(P)
            elif k == "6":
                fs = pick_files(SF / "Findings", {".json"}, False, tool=TOOL)
                if fs: import_findings(P, str(fs[0]))
            elif k == "7":
                t = ask(L("Тип: ", "Type: ") + " ".join("%d=%s" % (i, t) for i, t in enumerate(TYPES[2:], 1)), "1", quit_ok=False)
                if t.isdigit() and 1 <= int(t) <= len(TYPES) - 2:
                    P["type"] = TYPES[int(t) + 1]; P["body_js"] = SKEL[P["type"]]; P["engine"] = "webview" if confirm(L("Движок webview?", "webview engine?")) else "auto"
                    print("[+] " + P["type"])
            elif k == "8":
                js = gen_js(P)
                p = SF / "Scripts" / (P["name"] + ".js"); atomic_write(p, js)
                print(dim("\n".join(js.splitlines()[:40]))); print("[+] %s (%s)" % (p, fmt_size(len(js))))
                if clip_copy(js): print("[+] " + L("Скопировано в буфер iOS", "Copied to iOS clipboard"))
            elif k == "9":
                base = mem_ask(TOOL, "base_url", L("Базовый URL скриптов (где опубликуете .js)", "Scripts base URL (where you publish .js)"), DEF_BASE, quit_ok=False)
                allp = confirm(L("Включить ВСЕ проекты в модуль?", "Include ALL projects in the module?"))
                projs = ws["scripts"] if allp else [P]
                txt, warns = build_module(projs, base, P["name"], P.get("desc") or "ScriptForge module")
                p = SF / "Output" / (P["name"] + ".module"); atomic_write(p, txt)
                print(txt); [print("[!] " + w) for w in warns]; print("[+] " + str(p))
                if clip_copy(txt): print("[+] " + L("Скопировано в буфер iOS", "Copied to iOS clipboard"))
            elif k == "10": run_test(P, gen_js(P))
            elif k == "11": serve_scripts()
            elif k == "12": P = None
        except (KeyboardInterrupt, ValueError, IndexError) as e:
            print("\n[*] %s" % (L("Отменено", "Cancelled") if isinstance(e, KeyboardInterrupt) else L("Неверный ввод", "Bad input")))
        save_ws(ws)
        if k in ("8", "9", "10"):
            pause()


if __name__ == "__main__":
    run_tool("ScriptForge", main)
TKEOF_scriptforge

tk_put configforge.py << 'TKEOF_configforge'
# -*- coding: utf-8 -*-
# ==========================================================================
#  ConfigForge — конструктор конфигураций и модулей (формат Shadowrocket/Surge-подобный):
#  [General] [Proxy Group] [Rule] [Host] [URL Rewrite] [Header Rewrite] [Body Rewrite]
#  [Map Local] [Script] [MITM]. Импорт, мастера, шаблоны, линтер, rule-set, экспорт,
#  выгрузка роутинга для других клиентов.
# ==========================================================================
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from tkcore import *
import tkcodec as K
import rules as R
import routing as RT
from collections import OrderedDict, Counter

TOOL = "configforge"
OUT = BASE / "ConfigForge" / "Output"
SECTIONS = ["General", "Proxy Group", "Rule", "Host", "URL Rewrite", "Header Rewrite", "Body Rewrite", "Map Local", "Script", "MITM"]
SEC_RU = {"General": "Общее", "Proxy Group": "Группы прокси", "Rule": "Правила", "Host": "Хосты", "URL Rewrite": "Переписать URL", "Header Rewrite": "Заголовки",
          "Body Rewrite": "Тело", "Map Local": "Локальная карта", "Script": "Скрипты", "MITM": "Расшифровка HTTPS"}
# ключи [General]: (описание RU, EN, подсказка значений)
GENERAL = {"ipv6": ("Использовать IPv6", "Use IPv6", "true/false"), "prefer-ipv6": ("Предпочитать IPv6", "Prefer IPv6", "true/false"),
           "dns-server": ("DNS-серверы (DoH/UDP/DoT)", "DNS servers", "https://dns.comss.one/dns-query,223.5.5.5"), "fallback-dns-server": ("Резервные DNS", "Fallback DNS", ""),
           "hijack-dns": ("Перехват DNS", "DNS hijack", "*:53"), "dns-over-https": ("DNS через HTTPS", "DoH", "true/false"), "block-quic": ("Блокировка QUIC", "Block QUIC", "true/false/all"),
           "skip-proxy": ("Исключить из проксирования", "Skip proxy", "*.local,localhost,..."), "tun-excluded-routes": ("Исключённые маршруты", "Excluded routes", "10.0.0.0/8,..."),
           "always-real-ip": ("Реальные IP", "Always real IP", ""), "bypass-system": ("Обход системы", "Bypass system", "true/false"), "udp-policy-not-supported-behaviour": ("Если UDP не поддерживается", "UDP unsupported", "REJECT/DIRECT"),
           "loglevel": ("Уровень логов", "Log level", "error/warning/info/debug"), "all-hybrid": ("Гибридный режим", "All hybrid", "true/false"), "icmp-auto-reply": ("Ответ на ICMP", "ICMP auto reply", "true/false"),
           "private-ip-answer": ("Ответ для частных IP", "Private IP answer", "true/false"), "stun-response-ip": ("Ответ STUN (IPv4)", "STUN IPv4", "0.0.0.0"), "stun-response-ipv6": ("Ответ STUN (IPv6)", "STUN IPv6", "::1"),
           "geoip-maxmind-url": ("URL GeoIP", "GeoIP URL", "https://.../Country.mmdb"), "wifi-assist": ("Помощник Wi-Fi", "Wi-Fi assist", "true/false"), "exclude-simple-hostnames": ("Простые имена мимо прокси", "Exclude simple hostnames", "true/false"),
           "proxy-test-url": ("URL теста прокси", "Proxy test URL", "https://www.gstatic.com/generate_204"), "internet-test-url": ("URL теста интернета", "Internet test URL", ""), "test-timeout": ("Таймаут теста", "Test timeout", "5"),
           "show-error-page-for-reject": ("Страница ошибки при блокировке", "Show error page on reject", "true/false"), "dns-direct-system": ("Системный DNS для DIRECT", "System DNS for DIRECT", "true/false"),
           "dns-fallback-system": ("Системный DNS как резерв", "System DNS fallback", "true/false"), "doh-skip-cert-verification": ("DoH без проверки сертификата", "DoH skip cert verify", "true/false"),
           "allow-wifi-access": ("Доступ к прокси по Wi-Fi", "Allow Wi-Fi access", "true/false"), "wifi-access-http-port": ("HTTP-порт доступа", "HTTP access port", "1082"), "hide-vpn-icon": ("Скрыть значок VPN", "Hide VPN icon", "true/false")}
STD_POL = ["DIRECT", "PROXY", "REJECT", "REJECT-DICT", "REJECT-ARRAY", "REJECT-200", "REJECT-IMG", "REJECT-TINYGIF", "REJECT-DROP", "REJECT-NO-DROP", "REJECT-VIDEO", "TAILSCALE"]
URL_ACT = ["302", "307", "header", "reject", "reject-200", "reject-dict", "reject-array", "reject-img", "reject-tinygif"]
COUNTRIES = [("🇷🇺", "россия|russia|ru"), ("🇨🇳", "китай|china"), ("🇭🇰", "гонконг|hong\\s*kong"), ("🇮🇷", "иран|iran"), ("🇧🇾", "беларусь|belarus"), ("🇺🇸", "сша|usa|united\\s*states"),
             ("🇩🇪", "германия|germany"), ("🇳🇱", "нидерланды|netherlands"), ("🇫🇮", "финляндия|finland"), ("🇹🇷", "турция|turkey"), ("🇯🇵", "япония|japan"), ("🇸🇬", "сингапур|singapore")]


class Cfg:
    def __init__(self):
        self.pre, self.sec, self.name = [], OrderedDict((s, []) for s in SECTIONS), "config"

    def parse(self, text):
        cur, self.pre = None, []
        for l_ in text.splitlines():
            m = re.match(r"^\[([^\]]+)\]\s*$", l_.strip())
            if m:
                nm = next((s for s in SECTIONS if s.lower() == m.group(1).lower()), m.group(1))
                cur = self.sec.setdefault(nm, [])
            elif cur is None:
                self.pre.append(l_)
            else:
                cur.append(l_)
        for k in self.sec:                                       # убрать хвостовые пустые строки
            while self.sec[k] and not self.sec[k][-1].strip():
                self.sec[k].pop()

    def render(self, header=None):
        out = list(header if header is not None else self.pre)
        for k, v in self.sec.items():
            if v:
                out += ["", "[%s]" % k] + v
        return "\n".join(out).strip("\n") + "\n"

    def groups(self):
        return [l_.split("=", 1)[0].strip() for l_ in self.sec["Proxy Group"] if "=" in l_ and not l_.strip().startswith("#")]

    def rule_count(self):
        return sum(1 for l_ in self.sec["Rule"] if R.parse_line(l_)["kind"] == "rule")


def policy_pick(cfg, default="DIRECT"):
    opts = cfg.groups() + STD_POL
    print(c(L("Политика:", "Policy:"), accent(), True))
    for i, p in enumerate(opts, 1):
        extra = dim(R.POLICY_HELP.get(p, "")) if p in R.POLICY_HELP else (dim(L("группа", "group")) if p in cfg.groups() else "")
        print("  %s %-16s %s" % (c("%2d" % i, accent(), True), p, extra))
    v = ask(L("Номер или своё имя", "Number or custom name"), default, quit_ok=False)
    return opts[int(v) - 1] if v.isdigit() and 1 <= int(v) <= len(opts) else v


def list_section(cfg, name, page=0, per=25):
    lines = cfg.sec[name]
    n = len(lines)
    for i in range(page * per, min(n, (page + 1) * per)):
        print("%s %s" % (c("%4d" % (i + 1), accent()), trunc(lines[i], term_w() - 6)))
    print(dim(L("%d строк, стр. %d/%d" % (n, page + 1, max(1, (n + per - 1) // per)), "%d lines, page %d/%d" % (n, page + 1, max(1, (n + per - 1) // per)))))


# ---- универсальный редактор строк раздела ----
def edit_lines(cfg, name, adder):
    page = 0
    while True:
        list_section(cfg, name, page)
        k = menu(L("Раздел: ", "Section: ") + (SEC_RU.get(name, name) if ST.g("lang") == "ru" else name), [
            ("1", L("Добавить (мастер)", "Add (wizard)"), ""), ("2", L("Добавить строки вручную", "Add raw lines"), ""), ("3", L("Удалить по номерам", "Delete by numbers"), ""),
            ("4", L("Изменить строку", "Edit a line"), ""), ("5", L("Переместить", "Move"), ""), ("6", L("Поиск", "Search"), ""), ("7", L("След. страница", "Next page"), ""),
            ("8", L("Пред. страница", "Prev page"), ""), ("9", L("Очистить раздел", "Clear section"), "")], show=False)
        L_ = cfg.sec[name]
        if k == "q":
            return
        if k == "1":
            adder(cfg)
        elif k == "2":
            print(dim(L("Вводите строки, пустая — конец.", "Enter lines, blank = end.")))
            while True:
                x = input("")
                if not x.strip():
                    break
                L_.append(x)
        elif k == "3":
            sel = ask_multi(L("Номера", "Numbers"), len(L_))
            for i in sorted(sel or [], reverse=True):
                L_.pop(i - 1)
        elif k == "4":
            n = ask(L("Номер строки", "Line number"), "", quit_ok=False)
            if n.isdigit() and 1 <= int(n) <= len(L_):
                print(dim(L_[int(n) - 1]))
                v = ask(L("Новая строка (Enter — оставить)", "New line (Enter = keep)"), "", quit_ok=False)
                if v:
                    L_[int(n) - 1] = v
        elif k == "5":
            a, b = ask(L("Номер строки", "Line #"), "", quit_ok=False), ask(L("Переместить на позицию", "Move to position"), "", quit_ok=False)
            if a.isdigit() and b.isdigit() and 1 <= int(a) <= len(L_):
                L_.insert(max(0, min(len(L_), int(b) - 1)), L_.pop(int(a) - 1))
        elif k == "6":
            q = ask(L("Что искать", "Search"), "", quit_ok=False).lower()
            for i, l_ in enumerate(L_, 1):
                if q and q in l_.lower():
                    print("%s %s" % (c("%4d" % i, accent()), trunc(l_, term_w() - 6)))
            pause()
        elif k == "7":
            page = min(page + 1, max(0, (len(L_) - 1) // 25))
        elif k == "8":
            page = max(0, page - 1)
        elif k == "9" and confirm(L("Очистить раздел?", "Clear section?")):
            L_.clear()


# ---- мастера ----
def add_rule(cfg):
    types = [t for t in R.RULE_TYPES]
    for i, t in enumerate(types, 1):
        print("  %s %s" % (c("%2d" % i, accent(), True), t))
    v = ask(L("Тип правила (номер)", "Rule type (number)"), "1", quit_ok=False)
    t = types[int(v) - 1] if v.isdigit() and 1 <= int(v) <= len(types) else "DOMAIN-SUFFIX"
    if t == "FINAL":
        cfg.sec["Rule"].append("FINAL," + policy_pick(cfg, "PROXY")); return
    val = ask(L("Значение (домен/маска/regex/CIDR/ASN/URL)", "Value (domain/pattern/regex/CIDR/ASN/URL)"), "", quit_ok=False)
    if not val:
        return
    if t == "URL-REGEX" and val.startswith("http"):
        val = K.url_to_pattern(val)
        print("[*] " + L("Сгенерирован паттерн: ", "Generated pattern: ") + val)
    pol = policy_pick(cfg)
    opts = []
    if t.startswith("IP-") and confirm(L("no-resolve?", "no-resolve?"), True):
        opts.append("no-resolve")
    if confirm(L("pre-matching (до DNS)?", "pre-matching?")):
        opts.append("pre-matching")
    ln_ = ",".join([t, val, pol] + opts)
    pos = ask(L("Позиция (Enter — в конец)", "Position (Enter = end)"), "", quit_ok=False)
    if pos.isdigit():
        cfg.sec["Rule"].insert(int(pos) - 1, ln_)
    else:
        cfg.sec["Rule"].append(ln_)
    print("[+] " + ln_)


def add_group(cfg):
    name = ask(L("Имя группы", "Group name"), "", quit_ok=False)
    if not name:
        return
    tp = ask(L("Тип: 1 select, 2 url-test, 3 fallback, 4 load-balance", "Type: 1 select, 2 url-test, 3 fallback, 4 load-balance"), "2", quit_ok=False)
    tp = {"1": "select", "2": "url-test", "3": "fallback", "4": "load-balance"}.get(tp, "url-test")
    parts = [tp]
    if tp != "select":
        parts.append("interval=" + ask(L("Интервал проверки, сек", "Check interval, sec"), "200", quit_ok=False))
        parts.append("timeout=" + ask(L("Таймаут, сек", "Timeout, sec"), "2", quit_ok=False))
        if tp == "url-test":
            parts.append("tolerance=" + ask("tolerance, ms", "50", quit_ok=False))
        parts.append("url=" + ask(L("URL проверки", "Test URL"), "https://cp.cloudflare.com/generate_204", quit_ok=False))
    k = ask(L("Источник серверов: 1 фильтр regex, 2 список политик", "Servers: 1 regex filter, 2 policy list"), "1", quit_ok=False)
    if k == "2":
        parts.append("policies=" + ask(L("Политики через запятую", "Policies, comma"), "DIRECT", quit_ok=False))
    else:
        excl = ask(L("Исключить слова (через запятую)", "Exclude words (comma)"), "подписка,subscribe,истекла,support", quit_ok=False)
        print(dim(L("Страны для исключения (номера через запятую, Enter — нет):", "Countries to exclude (numbers, Enter = none):")))
        for i, (fl, rx) in enumerate(COUNTRIES, 1):
            print("  %2d %s %s" % (i, fl, rx.split("|")[0]))
        cs = ask(L("Номера", "Numbers"), "", quit_ok=False)
        bad = [x.strip() for x in excl.split(",") if x.strip()]
        try:
            for n in parse_multi(cs, len(COUNTRIES)) if cs else []:
                bad += [COUNTRIES[n - 1][0]] + COUNTRIES[n - 1][1].split("|")
        except ValueError:
            pass
        inc = ask(L("Оставить только (слова через запятую, Enter — все)", "Only keep (words, Enter = all)"), "", quit_ok=False)
        rx = "(?i)^(?!.*(?:%s))" % "|".join(re.escape(b) if "\\" not in b else b for b in bad) if bad else "(?i)^"
        rx += (".*(?:%s).*$" % "|".join(re.escape(x.strip()) for x in inc.split(",") if x.strip())) if inc.strip() else ".*$"
        try:
            re.compile(rx)
        except re.error as e:
            print("[!] regex: %s" % e); return
        parts.append("policy-regex-filter=" + rx)
    cfg.sec["Proxy Group"].append("%s = %s" % (name, ",".join(parts)))
    print("[+] " + cfg.sec["Proxy Group"][-1][:80])


def pattern_ask():
    p = ask(L("Паттерн URL (regex) или пример ссылки", "URL pattern (regex) or sample URL"), "", quit_ok=False)
    return K.url_to_pattern(p) if p.startswith("http") else p


def add_urlrw(cfg):
    p = pattern_ask()
    if not p:
        return
    for i, a in enumerate(URL_ACT, 1):
        print("  %s %s" % (c("%2d" % i, accent(), True), a))
    a = URL_ACT[int(ask(L("Действие", "Action"), "1", quit_ok=False)) - 1] if True else "302"
    cfg.sec["URL Rewrite"].append("%s %s %s" % (p, (ask(L("Новый URL/замена ($1...)", "New URL / replacement ($1...)"), "", quit_ok=False) if a in ("302", "307", "header") else "_"), a))


def add_hdr(cfg):
    p = pattern_ask()
    if not p:
        return
    act = ask("1 header-add, 2 header-del, 3 header-replace, 4 header-replace-regex", "2", quit_ok=False)
    act = {"1": "header-add", "2": "header-del", "3": "header-replace", "4": "header-replace-regex"}.get(act, "header-del")
    nm = ask(L("Имя заголовка", "Header name"), "", quit_ok=False)
    val = ask(L("Значение", "Value"), "", quit_ok=False) if act != "header-del" else ""
    cfg.sec["Header Rewrite"].append(("%s %s %s %s" % (p, act, nm, val)).strip())


def add_body(cfg):
    side = ask("1 http-response, 2 http-request, 3 http-response-jq, 4 http-request-jq", "1", quit_ok=False)
    side = {"1": "http-response", "2": "http-request", "3": "http-response-jq", "4": "http-request-jq"}.get(side, "http-response")
    p = pattern_ask()
    if side.endswith("jq"):
        cfg.sec["Body Rewrite"].append("%s %s '%s'" % (side, p, ask(L("Выражение jq", "jq expression"), ".", quit_ok=False)))
    else:
        cfg.sec["Body Rewrite"].append("%s %s %s %s" % (side, p, ask(L("Что найти (regex)", "Find (regex)"), "", quit_ok=False), ask(L("Чем заменить", "Replace with"), "", quit_ok=False)))


def add_map(cfg):
    p = pattern_ask()
    dt = ask("1 text, 2 json, 3 file, 4 base64", "1", quit_ok=False)
    dt = {"1": "text", "2": "json", "3": "file", "4": "base64"}.get(dt, "text")
    data = ask(L("Содержимое (или путь для file)", "Content (or path for file)"), "", quit_ok=False)
    st = ask("status-code", "200", quit_ok=False)
    cfg.sec["Map Local"].append('%s data-type=%s %s="%s" status-code=%s' % (p, dt, "data-path" if dt == "file" else "data", data, st))


def add_host(cfg):
    h = ask(L("Домен", "Domain"), "", quit_ok=False)
    if not h:
        return
    v = ask(L("IP / домен / server:DNS (Enter — определить через DNS)", "IP / domain / server:DNS (Enter = resolve via DNS)"), "", quit_ok=False)
    if not v:
        with spin(L("Определяю IP", "Resolving IP")):
            ips = resolve(h, "doh") or resolve(h, "udp") or resolve(h, "system")
        if not ips:
            print("[!] " + L("не определён", "not resolved")); return
        v = ips[0]
    cfg.sec["Host"].append("%s = %s" % (h, v))


def mitm_edit(cfg):
    L_ = cfg.sec["MITM"]
    def get(k):
        for l_ in L_:
            if re.match(r"^\s*%s\s*=" % k, l_):
                return l_.split("=", 1)[1].strip()
        return ""
    def put(k, v):
        for i, l_ in enumerate(L_):
            if re.match(r"^\s*%s\s*=" % k, l_):
                L_[i] = "%s = %s" % (k, v); return
        L_.append("%s = %s" % (k, v))
    while True:
        print("enable = %s | h2 = %s" % (get("enable") or "-", get("h2") or "-"))
        hosts = [x.strip() for x in get("hostname").replace("%APPEND%", "").split(",") if x.strip()]
        print(dim(trunc(", ".join(hosts), term_w() * 3)))
        k = menu(L("Расшифровка HTTPS", "HTTPS decryption"), [("1", "enable", get("enable")), ("2", "h2", get("h2")), ("3", L("Добавить хосты", "Add hosts"), ""), ("4", L("Удалить хосты", "Remove hosts"), ""),
                                                             ("5", L("Хосты из паттернов [Script]/[URL Rewrite]/…", "Hosts from [Script]/[URL Rewrite]/… patterns"), ""), ("6", L("Исключить хост (-host)", "Exclude host (-host)"), "")], show=False)
        if k == "q":
            return
        if k in ("1", "2"):
            key = "enable" if k == "1" else "h2"
            put(key, "false" if get(key) == "true" else "true")
        elif k == "3":
            add = [x.strip() for x in ask(L("Хосты через запятую", "Hosts, comma"), "", quit_ok=False).split(",") if x.strip()]
            put("hostname", "%APPEND% " + ",".join(dict.fromkeys(hosts + add)))
        elif k == "4":
            rm = [x.strip() for x in ask(L("Какие убрать", "Which to remove"), "", quit_ok=False).split(",")]
            put("hostname", "%APPEND% " + ",".join(h for h in hosts if h not in rm))
        elif k == "6":
            put("hostname", "%APPEND% " + ",".join(hosts + ["-" + ask(L("Хост", "Host"), "", quit_ok=False)]))
        elif k == "5":
            import scriptforge as SF
            found = []
            for sec in ("Script", "URL Rewrite", "Header Rewrite", "Body Rewrite", "Map Local"):
                for l_ in cfg.sec[sec]:
                    m = re.search(r"pattern=([^,]+)", l_) if sec == "Script" else re.match(r"^(?:http-\w+(?:-jq)?\s+)?(\S+)", l_.strip())
                    if m and not l_.strip().startswith("#"):
                        found += SF.hosts_from_pattern(m.group(1))[0]
            found = [h for h in dict.fromkeys(found) if h and h not in hosts]
            print("[*] " + L("Найдено: ", "Found: ") + ", ".join(found))
            if found and confirm(L("Добавить?", "Add?"), True):
                put("hostname", "%APPEND% " + ",".join(hosts + found))


def script_edit(cfg):
    import scriptforge as SF
    def add(cfg_):
        ws = SF.load_ws()["scripts"]
        if ws:
            for i, p in enumerate(ws, 1):
                print("  %2d %s [%s]" % (i, p["name"], p["type"]))
            n = ask(L("Номера проектов ScriptForge (1,3 / all)", "ScriptForge projects (1,3 / all)"), "", quit_ok=False)
            try:
                base = mem_ask(TOOL, "script_base", L("Базовый URL скриптов", "Scripts base URL"), SF.DEF_BASE, quit_ok=False)
                for i in parse_multi(n, len(ws)):
                    cfg_.sec["Script"].append(SF.script_line(ws[i - 1], base))
            except ValueError:
                pass
        else:
            print("[*] " + L("В ScriptForge нет проектов. Вставьте строки вручную (пункт 2).", "No ScriptForge projects. Paste raw lines (item 2)."))
    edit_lines(cfg, "Script", add)


def template_menu(cfg):
    T_ = [
        ("ru", L("РФ напрямую, остальное через прокси", "RU direct, rest via proxy"), ["DOMAIN-SUFFIX,ru,DIRECT", "DOMAIN-SUFFIX,su,DIRECT", "DOMAIN-SUFFIX,xn--p1ai,DIRECT", "GEOIP,RU,DIRECT", "FINAL,{PROXY}"]),
        ("lan", L("Локальные сети напрямую", "Private networks direct"), ["GEOIP,PRIVATE,DIRECT", "IP-CIDR,192.168.0.0/16,DIRECT,no-resolve", "IP-CIDR,10.0.0.0/8,DIRECT,no-resolve", "IP-CIDR,172.16.0.0/12,DIRECT,no-resolve"]),
        ("ads", L("Базовая блокировка рекламы/трекеров", "Basic ad/tracker blocking"), ["DOMAIN-KEYWORD,adserver,REJECT-200,pre-matching", "DOMAIN-KEYWORD,doubleclick,REJECT-DICT,pre-matching", "DOMAIN-KEYWORD,telemetry,REJECT-DICT,pre-matching",
                                                                              "DOMAIN-SUFFIX,googlesyndication.com,REJECT", "DOMAIN-SUFFIX,google-analytics.com,REJECT"]),
        ("tg", L("Telegram через группу", "Telegram via a group"), ["IP-CIDR,91.108.4.0/22,{PROXY},no-resolve", "IP-CIDR,91.108.56.0/22,{PROXY},no-resolve", "IP-CIDR,149.154.160.0/20,{PROXY},no-resolve", "DOMAIN-SUFFIX,telegram.org,{PROXY}", "DOMAIN-SUFFIX,t.me,{PROXY}"]),
        ("quic", L("Блок QUIC (UDP 443)", "Block QUIC (UDP 443)"), ["AND,((DST-PORT,443), (PROTOCOL,UDP)),REJECT"]),
    ]
    G_ = {"dns": ("DoH-DNS и перехват", ["dns-over-https = true", "hijack-dns = *:53", "dns-server = https://dns.comss.one/dns-query,https://1.1.1.1/dns-query", "fallback-dns-server = https://8.8.8.8/dns-query,https://9.9.9.9/dns-query"]),
          "leak": ("Защита от утечек WebRTC/QUIC", ["block-quic = true", "stun-response-ip = 0.0.0.0", "stun-response-ipv6 = ::1"]),
          "base": ("Базовые параметры", ["ipv6 = false", "loglevel = error", "bypass-system = true", "exclude-simple-hostnames = true", "private-ip-answer = true", "udp-policy-not-supported-behaviour = REJECT"])}
    for i, (_, lab, _) in enumerate(T_, 1):
        print("  %s %s" % (c("%2d" % i, accent(), True), lab))
    for j, (k, (lab, _)) in enumerate(G_.items(), len(T_) + 1):
        print("  %s [General] %s" % (c("%2d" % j, accent(), True), lab))
    sel = ask_multi(L("Шаблоны (1,3 / all)", "Templates (1,3 / all)"), len(T_) + len(G_))
    for n in sel or []:
        if n <= len(T_):
            pol = policy_pick(cfg, "PROXY") if any("{PROXY}" in x for x in T_[n - 1][2]) else ""
            for x in T_[n - 1][2]:
                cfg.sec["Rule"].append(x.replace("{PROXY}", pol))
        else:
            for x in list(G_.values())[n - len(T_) - 1][1]:
                key = x.split("=")[0].strip()
                cfg.sec["General"] = [l_ for l_ in cfg.sec["General"] if not re.match(r"^\s*%s\s*=" % re.escape(key), l_)] + [x]
    print("[+] OK")


def general_edit(cfg):
    while True:
        keys = sorted(GENERAL)
        cur = {l_.split("=", 1)[0].strip(): l_.split("=", 1)[1].strip() for l_ in cfg.sec["General"] if "=" in l_ and not l_.strip().startswith("#")}
        for i, k in enumerate(keys, 1):
            d = GENERAL[k]
            print("%s %-30s %s" % (c("%3d" % i, accent()), k, c(trunc(cur[k], 18), OK_C) if k in cur else dim(L(d[0], d[1])[:18])))
        v = ask(L("Номер параметра / 'x' — свой ключ / Enter — назад", "Parameter # / 'x' custom key / Enter = back"), "", quit_ok=False)
        if not v:
            return
        key = ask(L("Ключ", "Key"), "", quit_ok=False) if v == "x" else (keys[int(v) - 1] if v.isdigit() and 1 <= int(v) <= len(keys) else None)
        if not key:
            continue
        hint = GENERAL.get(key, ("", "", ""))[2]
        nv = ask("%s [%s]" % (key, hint), cur.get(key, ""), quit_ok=False, hint=L("'-' — удалить", "'-' = delete"))
        cfg.sec["General"] = [l_ for l_ in cfg.sec["General"] if not re.match(r"^\s*#?\s*%s\s*=" % re.escape(key), l_)]
        if nv != "-" and nv != "":
            cfg.sec["General"].append("%s = %s" % (key, nv))


def lint(cfg):
    msgs, groups = [], set(cfg.groups())
    pols = groups | set(STD_POL)
    rules = [R.parse_line(l_) for l_ in cfg.sec["Rule"]]
    rr = [r for r in rules if r["kind"] == "rule"]
    if not any(r["type"] == "FINAL" for r in rr):
        msgs.append(("!", L("Нет правила FINAL", "No FINAL rule")))
    fi = next((i for i, r in enumerate(rr) if r["type"] == "FINAL"), None)
    if fi is not None and fi < len(rr) - 1:
        msgs.append(("!", L("Есть правила после FINAL (не сработают)", "Rules after FINAL (never match)")))
    for r in rr:
        if r["policy"] and r["policy"] not in pols:
            msgs.append(("!", L("Неизвестная политика/группа: ", "Unknown policy/group: ") + r["policy"])); break
        if r["type"] == "URL-REGEX":
            try:
                re.compile(r["val"])
            except re.error:
                msgs.append(("!", "URL-REGEX: " + r["val"][:40]))
    seen, dup = set(), 0
    for r in rr:
        k = (r["type"], r["val"].lower())
        dup += k in seen; seen.add(k)
    if dup:
        msgs.append(("*", L("Повторяющихся правил: %d" % dup, "Duplicate rules: %d" % dup)))
    for sec in ("Script", "URL Rewrite", "Header Rewrite", "Body Rewrite", "Map Local"):
        for l_ in cfg.sec[sec]:
            s = l_.strip()
            if s and not s.startswith("#"):
                m = re.search(r"pattern=([^,]+)", s) if sec == "Script" else re.match(r"^(?:http-\w+(?:-jq)?\s+)?(\S+)", s)
                if m:
                    try:
                        re.compile(m.group(1))
                    except re.error as e:
                        msgs.append(("!", "%s: bad regex %s" % (sec, m.group(1)[:30])))
    for l_ in cfg.sec["Proxy Group"]:
        m = re.search(r"policy-regex-filter=(.*)$", l_)
        if m:
            try:
                re.compile(m.group(1).split(",url=")[0])
            except re.error:
                msgs.append(("!", L("Некорректный regex в группе: ", "Bad group regex: ") + l_.split("=")[0]))
    if (cfg.sec["Script"] or cfg.sec["Body Rewrite"] or cfg.sec["Map Local"]) and not any("hostname" in l_ for l_ in cfg.sec["MITM"]):
        msgs.append(("!", L("Есть скрипты/перезаписи, но не задан hostname в [MITM]", "Scripts/rewrites present but no [MITM] hostname")))
    for sec in ("Rule",):
        for r in rr:
            if r["type"] == "RULE-SET" and not r["val"].startswith("http"):
                msgs.append(("*", "RULE-SET: " + r["val"][:40]))
    if not msgs:
        print("[+] " + L("Проблем не найдено", "No problems found"))
    for lv, m in msgs:
        print(("[!] " if lv == "!" else "[*] ") + m)


def rules_tools(cfg):
    while True:
        print(dim(L("правил: %d" % cfg.rule_count(), "rules: %d" % cfg.rule_count())))
        k = menu(L("Инструменты правил", "Rule tools"), [
            ("1", L("Развернуть RULE-SET в правила (с выбранной политикой)", "Inline a RULE-SET as rules (with chosen policy)"), ""),
            ("2", L("Свернуть правила в rule-set (с сохранением приоритета)", "Pack rules into rule-sets (priority preserved)"), ""),
            ("3", L("Переписать политику", "Rewrite policy"), ""), ("4", L("Открыть правила в ListLab", "Open rules in ListLab"), "")], show=False)
        if k == "q":
            return
        if k == "1":
            rs = [(i, R.parse_line(l_)) for i, l_ in enumerate(cfg.sec["Rule"]) if R.parse_line(l_).get("type") == "RULE-SET"]
            for n, (i, r) in enumerate(rs, 1):
                print("  %s %s -> %s" % (c("%2d" % n, accent(), True), trunc(r["val"], 44), r["policy"]))
            u = ask(L("Номер RULE-SET или URL списка", "RULE-SET number or list URL"), "", quit_ok=False)
            idx = None
            if u.isdigit() and 1 <= int(u) <= len(rs):
                idx, r = rs[int(u) - 1]; url, pol = r["val"], r["policy"]
            elif u.startswith("http"):
                url, pol = u, policy_pick(cfg)
            else:
                continue
            lines, _ = fetch_lines(url, label="rule-set")
            new = R.ruleset_to_rules(lines, pol)
            print("[+] " + L("Правил: %d" % len(new), "Rules: %d" % len(new)))
            if new and confirm(L("Вставить?", "Insert?"), True):
                if idx is not None:
                    cfg.sec["Rule"][idx:idx + 1] = new
                else:
                    cfg.sec["Rule"] += new
        elif k == "2":
            sets, rest = R.pack_rulesets(cfg.sec["Rule"])
            base = mem_ask(TOOL, "base_url", L("Базовый URL публикации", "Publish base URL"), "", quit_ok=False)
            files, blk = R.build_ruleset_files(sets, sanitize_filename(ask(L("Префикс", "Prefix"), "RULES", quit_ok=False)), base)
            for nm, body in files:
                atomic_write(OUT / nm, body); print("[+] %s (%d)" % (nm, body.count("\n")))
            print(c(L("Новый блок [Rule]:", "New [Rule] block:"), accent(), True)); print("\n".join(blk + rest))
            if confirm(L("Заменить [Rule] этим блоком?", "Replace [Rule] with this block?")):
                cfg.sec["Rule"] = blk + rest
        elif k == "3":
            old = ask(L("Какую политику менять (* — любую)", "Policy to replace (* = any)"), "*", quit_ok=False)
            new = policy_pick(cfg)
            cfg.sec["Rule"], n = R.rewrite_policy(cfg.sec["Rule"], {old: new})
            print("[+] " + L("Изменено: %d" % n, "Changed: %d" % n))
        elif k == "4":
            p = OUT / "rules_for_listlab.txt"
            atomic_write(p, "\n".join(cfg.sec["Rule"]))
            run_sibling("listlab.py")


def export_menu(cfg):
    OUT.mkdir(parents=True, exist_ok=True)
    k = menu(L("Экспорт", "Export"), [("1", L("Полный конфиг (.conf)", "Full config (.conf)"), ""), ("2", L("Модуль (.module) с заголовком", "Module (.module) with header"), ""),
                                    ("3", L("Только [Rule] как список", "Only [Rule] as list"), ""), ("4", L("Роутинг для других клиентов (Xray/Clash/sing-box/Happ…)", "Routing for other clients (Xray/Clash/sing-box/Happ…)"), ""),
                                    ("5", L("Скопировать в буфер iOS", "Copy to iOS clipboard"), "")], show=False)
    if k == "q":
        return
    stamp = now_stamp()
    if k == "1":
        p = OUT / ("config_%s.conf" % stamp); atomic_write(p, cfg.render()); print("[+] " + str(p))
    elif k == "2":
        nm = ask(L("Название модуля", "Module name"), cfg.name, quit_ok=False)
        ds = ask(L("Описание", "Description"), "", quit_ok=False)
        url = ask(L("URL обновления (#!url, Enter — нет)", "Update URL (#!url, Enter = none)"), "", quit_ok=False)
        hd = (["#!url=" + url] if url else []) + ["#!name=" + nm, "#!desc=" + ds, ""]
        p = OUT / ("%s.module" % sanitize_filename(nm)); atomic_write(p, cfg.render(hd)); print("[+] " + str(p))
    elif k == "3":
        p = OUT / ("rules_%s.list" % stamp); atomic_write(p, "\n".join(cfg.sec["Rule"]) + "\n"); print("[+] " + str(p))
    elif k == "4":
        kk = menu(L("Формат", "Format"), [("1", "Xray routing JSON", ""), ("2", "Clash rules (yaml)", ""), ("3", "sing-box rule-set", ""), ("4", L("Ссылка Happ / v2RayTun (routing)", "Happ / v2RayTun routing link"), ""),
                                           ("5", L("Shadowrocket-подобный (Incy и др.) .conf", "Shadowrocket-like (Incy etc.) .conf"), "")], show=False)
        rl = cfg.sec["Rule"]
        if kk == "1":
            p = OUT / ("xray_routing_%s.json" % stamp); atomic_write(p, json.dumps({"routing": {"domainStrategy": "IPIfNonMatch", "rules": R.to_xray_rules(rl)}}, indent=1, ensure_ascii=False))
        elif kk == "2":
            p = OUT / ("clash_rules_%s.yaml" % stamp); atomic_write(p, R.to_clash_rules(rl))
        elif kk == "3":
            p = OUT / ("singbox_ruleset_%s.json" % stamp); atomic_write(p, R.to_singbox_ruleset(rl))
        elif kk == "4":
            prof = {"Name": cfg.name, "GlobalProxy": True, "DirectSites": [], "BlockSites": [], "ProxySites": [], "DirectIp": [], "BlockIp": [], "ProxyIp": [], "DomainStrategy": "IPIfNonMatch", "RouteOrder": "block-direct-proxy"}
            for l_ in rl:
                r = R.parse_line(l_)
                if r["kind"] != "rule":
                    continue
                tag = "Direct" if r["policy"] == "DIRECT" else "Block" if r["policy"].startswith("REJECT") else "Proxy"
                if r["type"] == "DOMAIN-SUFFIX": prof[tag + "Sites"].append("domain:" + r["val"])
                elif r["type"] == "DOMAIN": prof[tag + "Sites"].append("full:" + r["val"])
                elif r["type"] == "DOMAIN-KEYWORD": prof[tag + "Sites"].append("keyword:" + r["val"])
                elif r["type"] in ("IP-CIDR", "IP-CIDR6"): prof[tag + "Ip"].append(r["val"])
            js = json.dumps(prof, ensure_ascii=False)
            p = OUT / ("routing_links_%s.txt" % stamp)
            atomic_write(p, "\n".join(RT.client_links("Happ / Happ Plus", "routing", payload=js) + RT.client_links("v2RayTun", "routing", payload=js)))
            print(p.read_text()[:600])
        else:
            p = OUT / ("rules_srlike_%s.conf" % stamp); atomic_write(p, "[Rule]\n" + "\n".join(rl) + "\n")
        print("[+] " + str(p))
    elif k == "5":
        print("[+] OK" if clip_copy(cfg.render()) else "[!] n/a")


def load_cfg():
    k = menu(L("Открыть", "Open"), [("1", L("Новый пустой", "New empty"), ""), ("2", L("Файл (ConfigForge/Output или Input)", "File (ConfigForge/Output or Input)"), ""), ("3", "URL", ""),
                                  ("4", L("Вставить текст", "Paste text"), ""), ("5", L("Дефолтная конфигурация автора", "Author's default config"), "")], tool=TOOL)
    cfg = Cfg()
    if k == "q":
        return None
    raw = None
    if k == "2":
        fs = pick_files(BASE / "ConfigForge" / "Input", None, False, tool=TOOL) or pick_files(OUT, None, False, tool=TOOL)
        raw = fs[0].read_bytes() if fs else None
        cfg.name = fs[0].stem if fs else "config"
    elif k == "3":
        raw = fetch(ask("URL", "", quit_ok=False), label="config")
    elif k == "4":
        buf, blank = [], 0
        print(dim(L("Вставьте текст, две пустые строки — конец.", "Paste text, two blank lines = end.")))
        while blank < 2:
            l_ = input(""); blank = blank + 1 if not l_.strip() else 0; buf.append(l_)
        raw = "\n".join(buf).encode()
    elif k == "5":
        raw = fetch("https://raw.githubusercontent.com/Krest-Neva/Shadowrocket/refs/heads/main/Configurations/Default_configuration_by_Krest-Neva.module", label="config")
    if raw:
        txt, why = decode_download(raw)
        if txt is None:
            print("[!] " + why); return None
        cfg.parse(txt)
    return cfg


def main():
    ensure_dirs("ConfigForge/Input", "ConfigForge/Output")
    cfg = load_cfg()
    if cfg is None:
        return
    if len(sys.argv) > 1 and os.path.isfile(sys.argv[1]):
        cfg.parse(smart_read(sys.argv[1]))
    while True:
        items = [(str(i), (SEC_RU[s] if ST.g("lang") == "ru" else s), "%d" % len(cfg.sec[s])) for i, s in enumerate(SECTIONS, 1)]
        items += [("t", L("Шаблоны", "Templates"), ""), ("r", L("Инструменты правил (rule-set, политики)", "Rule tools (rule-sets, policies)"), ""), ("l", L("Проверка (линтер)", "Lint"), ""),
                  ("e", L("Экспорт", "Export"), ""), ("o", L("Открыть другой", "Open another"), ""), ("v", L("Предпросмотр", "Preview"), "")]
        k = menu(L("ConfigForge: %s" % cfg.name, "ConfigForge: %s" % cfg.name), items, tool=TOOL)
        if k == "q":
            return
        try:
            if k.isdigit() and 1 <= int(k) <= len(SECTIONS):
                s = SECTIONS[int(k) - 1]
                {"General": lambda: general_edit(cfg), "Proxy Group": lambda: edit_lines(cfg, s, add_group), "Rule": lambda: edit_lines(cfg, s, add_rule), "Host": lambda: edit_lines(cfg, s, add_host),
                 "URL Rewrite": lambda: edit_lines(cfg, s, add_urlrw), "Header Rewrite": lambda: edit_lines(cfg, s, add_hdr), "Body Rewrite": lambda: edit_lines(cfg, s, add_body),
                 "Map Local": lambda: edit_lines(cfg, s, add_map), "Script": lambda: script_edit(cfg), "MITM": lambda: mitm_edit(cfg)}[s]()
            elif k == "t": template_menu(cfg)
            elif k == "r": rules_tools(cfg)
            elif k == "l": lint(cfg); pause()
            elif k == "e": export_menu(cfg); pause()
            elif k == "o":
                n = load_cfg()
                cfg = n or cfg
            elif k == "v":
                for l_ in cfg.render().splitlines()[:60]:
                    print(trunc(l_, term_w()))
                pause()
        except (KeyboardInterrupt, ValueError, IndexError) as e:
            print("\n[*] %s" % (L("Отменено", "Cancelled") if isinstance(e, KeyboardInterrupt) else L("Неверный ввод", "Bad input")))


if __name__ == "__main__":
    run_tool("ConfigForge", main)
TKEOF_configforge

tk_put subman.py << 'TKEOF_subman'
# -*- coding: utf-8 -*-
# ==========================================================================
#  SubManager — подписки и серверы любых прокси-протоколов, транспорты (tcp/http/h2/ws/mkcp/grpc/quic/
#  httpupgrade/xhttp со всеми параметрами), TLS/REALITY, фрагментация и шумы; экспорт: ссылки, base64,
#  Clash/Mihomo YAML, Xray JSON (балансировщик + роутинг), sing-box JSON; ссылки импорта для клиентов.
# ==========================================================================
import sys, os, copy, random
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from tkcore import *
import tkcodec as K
import rules as R
import routing as RT
from urllib.parse import urlparse, parse_qs, urlencode

TOOL = "subman"
SM = BASE / "SubManager"
IN, OUT, BK = SM / "Input", SM / "Output", SM / "Backups"
AUTOSAVE = BK / "autosave_servers.txt"
GENERIC = ["vless", "trojan", "hysteria2", "hy2", "hysteria", "tuic", "anytls", "socks5", "socks", "socks5+tls", "http", "https", "naive+https", "naive+quic", "snell", "ssh", "juicity", "mieru", "sudoku",
           "trusttunnel", "masque", "brook", "openconnect", "relay", "lua", "wireguard", "amneziawg", "awg", "shadowtls", "ssr"]
SCHEMES = ["vmess", "ss"] + GENERIC
TRANSPORTS = ["tcp", "http", "h2", "ws", "kcp", "grpc", "quic", "httpupgrade", "xhttp"]
# поля транспортов: (ключ, RU, EN, тип) ; тип: s строка, i число, b bool, j JSON
TF = {
    "tcp": [("headerType", "Тип заголовка (none/http)", "Header type (none/http)", "s"), ("host", "Host (для http)", "Host (http)", "s"), ("path", "Path (для http)", "Path (http)", "s")],
    "http": [("host", "Host (через запятую)", "Hosts (comma)", "s"), ("path", "Path", "Path", "s"), ("method", "Метод", "Method", "s"), ("read_idle_timeout", "read_idle_timeout", "read_idle_timeout", "i"), ("health_check_timeout", "health_check_timeout", "health_check_timeout", "i")],
    "ws": [("path", "Path", "Path", "s"), ("host", "Host", "Host", "s"), ("heartbeatPeriod", "heartbeatPeriod", "heartbeatPeriod", "i"), ("ed", "maxEarlyData", "maxEarlyData", "i"), ("eh", "earlyDataHeaderName", "earlyDataHeaderName", "s")],
    "kcp": [("headerType", "Маскировка (none/srtp/utp/wechat-video/dtls/wireguard)", "Header (none/srtp/utp/wechat-video/dtls/wireguard)", "s"), ("seed", "seed", "seed", "s"), ("mtu", "mtu", "mtu", "i"), ("tti", "tti", "tti", "i"),
            ("uplinkCapacity", "uplinkCapacity", "uplinkCapacity", "i"), ("downlinkCapacity", "downlinkCapacity", "downlinkCapacity", "i"), ("congestion", "congestion", "congestion", "b"),
            ("readBufferSize", "readBufferSize", "readBufferSize", "i"), ("writeBufferSize", "writeBufferSize", "writeBufferSize", "i")],
    "grpc": [("serviceName", "serviceName", "serviceName", "s"), ("authority", "authority", "authority", "s"), ("mode", "mode (gun/multi)", "mode (gun/multi)", "s"), ("idle_timeout", "idle_timeout", "idle_timeout", "i"),
             ("health_check_timeout", "health_check_timeout", "health_check_timeout", "i"), ("permit_without_stream", "permit_without_stream", "permit_without_stream", "b"), ("initial_windows_size", "initial_windows_size", "initial_windows_size", "i"), ("user_agent", "user_agent", "user_agent", "s")],
    "quic": [("quicSecurity", "security", "security", "s"), ("key", "key", "key", "s"), ("headerType", "header", "header", "s")],
    "httpupgrade": [("path", "Path", "Path", "s"), ("host", "Host", "Host", "s")],
    "xhttp": [("path", "Path", "Path", "s"), ("host", "Host", "Host", "s"), ("mode", "Режим (auto/packet-up/stream-up/stream-one)", "Mode (auto/packet-up/stream-up/stream-one)", "s")]}
# XHTTP extra: dotted keys
XEXTRA = ["noGRPCHeader", "noSSEHeader", "xPaddingBytes", "xPaddingObfsMode", "xPaddingKey", "xPaddingHeader", "xPaddingPlacement", "xPaddingMethod", "uplinkHTTPMethod", "sessionPlacement", "sessionKey", "sessionTable", "sessionLength",
          "seqPlacement", "seqKey", "uplinkDataPlacement", "uplinkDataKey", "uplinkChunkSize", "scMaxEachPostBytes", "scMinPostsIntervalMs", "scMaxBufferedPosts", "scStreamUpServerSecs", "headers",
          "xmux.maxConcurrency", "xmux.maxConnections", "xmux.cMaxReuseTimes", "xmux.hMaxRequestTimes", "xmux.hMaxReusableSecs", "xmux.hKeepAlivePeriod",
          "downloadSettings.address", "downloadSettings.port", "downloadSettings.network", "downloadSettings.security", "downloadSettings.tlsSettings.serverName", "downloadSettings.xhttpSettings.host",
          "downloadSettings.xhttpSettings.path", "downloadSettings.xhttpSettings.mode"]
TLS_F = [("sni", "SNI", "s"), ("fp", "fingerprint (chrome/firefox/safari/ios/android/edge/random...)", "s"), ("alpn", "ALPN (h2,http/1.1,h3)", "s"), ("insecure", "allowInsecure", "b"), ("pcs", "pinnedPeerCertSha256", "s"),
         ("vcn", "verifyPeerCertByName", "s"), ("ech", "ECH config", "s"), ("minVersion", "minVersion", "s"), ("maxVersion", "maxVersion", "s"), ("pbk", "REALITY publicKey", "s"), ("sid", "REALITY shortId", "s"), ("spx", "REALITY spiderX", "s"), ("pqv", "REALITY mldsa65Verify", "s")]
OTHER_F = [("flow", "flow", "s"), ("encryption", "encryption (vless/vmess)", "s"), ("alterId", "alterId", "i"), ("obfs", "obfs", "s"), ("obfs-password", "obfs-password", "s"), ("mport", "port hopping (mport)", "s"), ("congestion_control", "congestion_control", "s"),
           ("udp_relay_mode", "udp_relay_mode", "s"), ("plugin", "ss plugin", "s"), ("up", "up", "s"), ("down", "down", "s"), ("allowedIPs", "WG allowedIPs", "s"), ("mtu", "WG mtu", "i"), ("reserved", "WG reserved", "s"), ("publickey", "WG public key", "s"), ("address", "WG address", "s")]


# ==========================================================================
#  РАЗБОР И СБОРКА ССЫЛОК
# ==========================================================================
def b64d(s):
    s = re.sub(r"\s+", "", s)
    for fn in (base64.b64decode, base64.urlsafe_b64decode):
        try:
            return fn(s + "=" * (-len(s) % 4)).decode("utf-8", "replace")
        except Exception:
            continue
    return ""


def parse_uri(uri):
    uri = uri.strip()
    if "://" not in uri:
        return None
    scheme = uri.split("://")[0].lower()
    s = {"scheme": scheme, "name": "", "host": "", "port": "", "id": "", "password": "", "method": "", "params": {}}
    body, frag = (uri.split("#", 1) + [""])[:2]
    s["name"] = unquote(frag)
    try:
        if scheme == "vmess":
            raw = body[8:]
            j = json.loads(b64d(raw)) if not "@" in raw else None
            if j:
                s.update(name=j.get("ps", s["name"]), host=j.get("add", ""), port=str(j.get("port", "")), id=j.get("id", ""))
                p = s["params"]
                p.update(type=j.get("net", "tcp"), alterId=str(j.get("aid", 0)), encryption=j.get("scy", "auto"), security="tls" if j.get("tls") in ("tls", True) else "none")
                for a, b in (("host", "host"), ("path", "path"), ("sni", "sni"), ("alpn", "alpn"), ("fp", "fp"), ("headerType", "type")):
                    if j.get(b):
                        p[a] = str(j[b])
                if p["type"] in ("h2",):
                    p["type"] = "http"
                return s
        if scheme == "ss":
            b = body[5:]
            q = ""
            if "?" in b:
                b, q = b.split("?", 1)
            b = b.rstrip("/")
            if "@" in b:
                ui, hp = b.rsplit("@", 1)
                dec = b64d(ui) if ":" not in ui else unquote(ui)
                s["method"], s["password"] = (dec.split(":", 1) + [""])[:2]
            else:
                dec = b64d(b)
                ui, hp = dec.rsplit("@", 1)
                s["method"], s["password"] = ui.split(":", 1)
            s["host"], s["port"] = hp.rsplit(":", 1)
            s["params"] = {k: v[0] for k, v in parse_qs(q).items()}
            return s
        if scheme == "ssr":
            dec = b64d(body[6:])
            main, _, q = dec.partition("/?")
            h, p, proto, method, obfs, pw = (main.split(":") + [""] * 6)[:6]
            s.update(host=h, port=p, method=method, password=b64d(pw))
            s["params"] = {"protocol": proto, "obfs": obfs, **{k: b64d(v[0]) for k, v in parse_qs(q).items()}}
            s["name"] = s["params"].get("remarks", s["name"])
            return s
        u = urlparse(body)
        s["id"] = unquote(u.username or "")
        s["password"] = unquote(u.password or "")
        s["host"] = u.hostname or ""
        s["port"] = str(u.port or "")
        s["params"] = {k: v[0] for k, v in parse_qs(u.query, keep_blank_values=True).items()}
        if scheme in ("hysteria2", "hy2", "hysteria", "anytls", "trojan", "snell") and not s["password"]:
            s["password"], s["id"] = s["id"], ""
        if scheme == "hy2":
            s["scheme"] = "hysteria2"
        if scheme == "vless" and s["params"].get("type") == "splithttp":
            s["params"]["type"] = "xhttp"
        return s if s["host"] else None
    except Exception:
        return None


def build_uri(s):
    sc, p, name = s["scheme"], dict(s["params"]), s.get("name", "")
    tail = ("#" + quote(name)) if name else ""
    if sc == "vmess":
        j = {"v": "2", "ps": name, "add": s["host"], "port": s["port"], "id": s["id"], "aid": p.get("alterId", "0"), "scy": p.get("encryption", "auto"), "net": p.get("type", "tcp"), "type": p.get("headerType", "none"),
             "host": p.get("host", ""), "path": p.get("path", ""), "tls": "tls" if p.get("security") == "tls" else "", "sni": p.get("sni", ""), "alpn": p.get("alpn", ""), "fp": p.get("fp", "")}
        return "vmess://" + base64.b64encode(json.dumps(j, ensure_ascii=False).encode()).decode()
    if sc == "ss":
        ui = base64.urlsafe_b64encode(("%s:%s" % (s["method"], s["password"])).encode()).decode().rstrip("=")
        return "ss://%s@%s:%s%s%s" % (ui, s["host"], s["port"], ("/?" + urlencode(p)) if p else "", tail)
    if sc == "ssr":
        pw = base64.urlsafe_b64encode(s["password"].encode()).decode().rstrip("=")
        q = urlencode({k: base64.urlsafe_b64encode(str(v).encode()).decode().rstrip("=") for k, v in {"remarks": name}.items()})
        main = "%s:%s:%s:%s:%s:%s/?%s" % (s["host"], s["port"], p.get("protocol", "origin"), s["method"], p.get("obfs", "plain"), pw, q)
        return "ssr://" + base64.urlsafe_b64encode(main.encode()).decode().rstrip("=")
    cred = quote(s["id"], safe="") if s["id"] else ""
    if s["password"]:
        cred = (cred + ":" if cred else "") + quote(s["password"], safe="")
    host = "[%s]" % s["host"] if ":" in s["host"] else s["host"]
    return "%s://%s%s:%s%s%s" % (sc, (cred + "@") if cred else "", host, s["port"], ("?" + urlencode(p)) if p else "", tail)


def extract_servers(text):
    text = text.strip()
    kind = R.detect_kind(text)
    out = []
    if kind == "base64":
        d = b64d(text)
        if "://" in d:
            text = d
    if text[:1] in "{[":
        try:
            return parse_json_cfg(json.loads(text))
        except Exception:
            pass
    for l_ in text.splitlines():
        l_ = l_.strip()
        if re.match(r"^[a-z0-9+]+://", l_, re.I):
            s = parse_uri(l_)
            if s and s["host"]:
                out.append(s)
    return out


def parse_json_cfg(d):
    """Xray/sing-box JSON → серверы (основные протоколы)."""
    out = []
    for ob in (d.get("outbounds") or []) if isinstance(d, dict) else []:
        proto = (ob.get("protocol") or ob.get("type") or "").lower()
        st = ob.get("settings") or {}
        ss = ob.get("streamSettings") or {}
        try:
            if proto in ("vless", "vmess"):
                vn = st["vnext"][0]; u = vn["users"][0]
                s = {"scheme": proto, "name": ob.get("tag", ""), "host": vn["address"], "port": str(vn["port"]), "id": u.get("id", ""), "password": "", "method": "", "params": {"type": ss.get("network", "tcp"), "security": ss.get("security", "none")}}
                if u.get("flow"): s["params"]["flow"] = u["flow"]
                rs = ss.get("realitySettings") or {}
                for a, b in (("serverName", "sni"), ("publicKey", "pbk"), ("shortId", "sid"), ("fingerprint", "fp"), ("spiderX", "spx")):
                    if rs.get(a): s["params"][b] = rs[a]
                ts = ss.get("tlsSettings") or {}
                if ts.get("serverName"): s["params"]["sni"] = ts["serverName"]
                out.append(s)
            elif proto in ("trojan", "shadowsocks"):
                sv = st["servers"][0]
                out.append({"scheme": "trojan" if proto == "trojan" else "ss", "name": ob.get("tag", ""), "host": sv["address"], "port": str(sv["port"]), "id": "", "password": sv.get("password", ""), "method": sv.get("method", ""), "params": {}})
        except Exception:
            continue
    return out


# ==========================================================================
#  ГЕНЕРАТОРЫ: Xray JSON, sing-box JSON, Clash YAML
# ==========================================================================
def tbool(v):
    return str(v).lower() in ("1", "true", "yes", "on")


def nested_set(d, dotted, v):
    ks = dotted.split(".")
    for k in ks[:-1]:
        d = d.setdefault(k, {})
    d[ks[-1]] = v


def xhttp_extra(p):
    ex = {}
    if p.get("extra"):
        try:
            ex = json.loads(p["extra"])
        except Exception:
            ex = {}
    for k, v in p.items():
        if k.startswith("x."):
            try:
                nested_set(ex, k[2:], json.loads(v))
            except Exception:
                nested_set(ex, k[2:], v)
    return ex


def conv(v, kind):
    return int(v) if kind == "i" and str(v).lstrip("-").isdigit() else tbool(v) if kind == "b" else v


def xray_stream(s, cfg):
    p = s["params"]
    net = p.get("type", "tcp")
    net = {"h2": "http", "mkcp": "kcp", "splithttp": "xhttp"}.get(net, net)
    sec = p.get("security", "none")
    ss = {"network": net, "security": sec}
    if sec == "tls":
        t = {"serverName": p.get("sni") or p.get("host") or s["host"]}
        if p.get("alpn"): t["alpn"] = [a for a in p["alpn"].split(",") if a]
        if p.get("fp"): t["fingerprint"] = p["fp"]
        if p.get("insecure") and tbool(p["insecure"]): t["allowInsecure"] = True
        for a, b in (("pcs", "pinnedPeerCertSha256"), ("vcn", "verifyPeerCertByName"), ("ech", "echConfigList"), ("minVersion", "minVersion"), ("maxVersion", "maxVersion")):
            if p.get(a): t[b] = p[a]
        ss["tlsSettings"] = t
    elif sec == "reality":
        r = {"serverName": p.get("sni", ""), "fingerprint": p.get("fp", "chrome"), "publicKey": p.get("pbk", ""), "shortId": p.get("sid", ""), "spiderX": p.get("spx", "")}
        if p.get("pqv"): r["mldsa65Verify"] = p["pqv"]
        ss["realitySettings"] = r
    g = lambda k, d=None: p.get(k, d)
    if net == "ws":
        w = {"path": g("path", "/")}
        if g("host"): w["headers"] = {"Host": p["host"]}
        if g("heartbeatPeriod"): w["heartbeatPeriod"] = int(p["heartbeatPeriod"])
        if g("ed"): w["maxEarlyData"] = int(p["ed"])
        if g("eh"): w["earlyDataHeaderName"] = p["eh"]
        ss["wsSettings"] = w
    elif net == "grpc":
        gs = {"serviceName": g("serviceName", ""), "multiMode": g("mode") == "multi"}
        for k, kind in (("authority", "s"), ("idle_timeout", "i"), ("health_check_timeout", "i"), ("permit_without_stream", "b"), ("initial_windows_size", "i"), ("user_agent", "s")):
            if g(k): gs[k] = conv(p[k], kind)
        ss["grpcSettings"] = gs
    elif net == "kcp":
        ks = {"header": {"type": g("headerType", "none")}}
        for k, kind in (("seed", "s"), ("mtu", "i"), ("tti", "i"), ("uplinkCapacity", "i"), ("downlinkCapacity", "i"), ("congestion", "b"), ("readBufferSize", "i"), ("writeBufferSize", "i")):
            if g(k): ks[k] = conv(p[k], kind)
        ss["kcpSettings"] = ks
    elif net == "http":
        hs = {"path": g("path", "/")}
        if g("host"): hs["host"] = [h for h in p["host"].split(",") if h]
        if g("method"): hs["method"] = p["method"]
        for k in ("read_idle_timeout", "health_check_timeout"):
            if g(k): hs[k] = int(p[k])
        ss["httpSettings"] = hs
    elif net == "quic":
        ss["quicSettings"] = {"security": g("quicSecurity", "none"), "key": g("key", ""), "header": {"type": g("headerType", "none")}}
    elif net == "httpupgrade":
        hu = {"path": g("path", "/")}
        if g("host"): hu["host"] = p["host"]
        ss["httpupgradeSettings"] = hu
    elif net == "xhttp":
        xs = {"path": g("path", "/"), "mode": g("mode", "auto")}
        if g("host"): xs["host"] = p["host"]
        ex = xhttp_extra(p)
        if ex: xs["extra"] = ex
        ss["xhttpSettings"] = xs
    elif net == "tcp" and g("headerType") == "http":
        ss["tcpSettings"] = {"header": {"type": "http", "request": {"path": [g("path", "/")], "headers": {"Host": [h for h in g("host", "").split(",") if h]}}}}
    fr = cfg.get("fragment", {})
    if fr.get("enabled") or cfg.get("noises"):
        ss["sockopt"] = {"dialerProxy": fr.get("tag", "fragment")}
    return ss


def xray_outbound(s, tag, cfg):
    sc, p = s["scheme"], s["params"]
    try:
        port = int(s["port"])
    except ValueError:
        port = 443
    if sc == "vless":
        u = {"id": s["id"], "encryption": p.get("encryption", "none")}
        if p.get("flow"): u["flow"] = p["flow"]
        o = {"protocol": "vless", "settings": {"vnext": [{"address": s["host"], "port": port, "users": [u]}]}}
    elif sc == "vmess":
        o = {"protocol": "vmess", "settings": {"vnext": [{"address": s["host"], "port": port, "users": [{"id": s["id"], "alterId": int(p.get("alterId", 0) or 0), "security": p.get("encryption", "auto")}]}]}}
    elif sc == "trojan":
        o = {"protocol": "trojan", "settings": {"servers": [{"address": s["host"], "port": port, "password": s["password"]}]}}
    elif sc == "ss":
        o = {"protocol": "shadowsocks", "settings": {"servers": [{"address": s["host"], "port": port, "method": s["method"], "password": s["password"]}]}}
    elif sc in ("socks5", "socks"):
        o = {"protocol": "socks", "settings": {"servers": [{"address": s["host"], "port": port, "users": [{"user": s["id"], "pass": s["password"]}] if s["id"] else []}]}}
    elif sc == "http":
        o = {"protocol": "http", "settings": {"servers": [{"address": s["host"], "port": port, "users": [{"user": s["id"], "pass": s["password"]}] if s["id"] else []}]}}
    elif sc == "hysteria2":
        o = {"protocol": "hysteria", "settings": {"version": 2, "address": s["host"], "port": port},
             "streamSettings": {"network": "hysteria", "security": "tls", "tlsSettings": {"serverName": p.get("sni", s["host"]), "alpn": ["h3"]}, "hysteriaSettings": {"version": 2, "auth": s["password"]}}}
        if p.get("obfs"): o["streamSettings"]["finalmask"] = {"udp": [{"type": "salamander", "settings": {"password": p.get("obfs-password", "")}}]}
        o["tag"] = tag
        return o
    elif sc == "wireguard":
        o = {"protocol": "wireguard", "settings": {"secretKey": s["id"], "address": [x for x in p.get("address", "").split(",") if x], "peers": [{"publicKey": p.get("publickey", ""), "endpoint": "%s:%d" % (s["host"], port), "allowedIPs": (p.get("allowedIPs") or "0.0.0.0/0,::/0").split(",")}], "mtu": int(p.get("mtu", 1420) or 1420)}}
        o["tag"] = tag
        return o
    else:
        return None
    if sc in ("vless", "vmess", "trojan", "ss"):
        o["streamSettings"] = xray_stream(s, cfg)
    if cfg.get("mux") and sc in ("vless", "vmess", "trojan"):
        o["mux"] = {"enabled": True, "concurrency": cfg.get("mux_n", 8)}
    o["tag"] = tag
    return o


def tag_of(s, i, used):
    t = re.sub(r"[^\w\-]", "_", transliterate(s.get("name") or "proxy-%d" % i)) or "proxy-%d" % i
    base, n = t, 1
    while t in used:
        t = "%s_%d" % (base, n); n += 1
    used.add(t)
    return t


RU = dict(zip("абвгдеёжзийклмнопрстуфхцчшщъыьэюя", "a b v g d e e zh z i y k l m n o p r s t u f h ts ch sh sch _ y _ e yu ya".split()))


def transliterate(n):
    return "".join(RU.get(ch.lower(), ch) if ch.lower() in RU else ch for ch in n).replace(" ", "_")


def gen_xray(servers, cfg):
    outs, tags, used, bad = [], [], set(), []
    for i, s in enumerate(servers, 1):
        t = tag_of(s, i, used)
        o = xray_outbound(s, t, cfg)
        if o:
            outs.append(o); tags.append(t)
        else:
            bad.append("%s(%s)" % (s.get("name", "?"), s["scheme"]))
    outs += [{"protocol": "freedom", "tag": "direct"}, {"protocol": "blackhole", "tag": "block"}]
    fr = cfg.get("fragment", {})
    if fr.get("enabled") or cfg.get("noises"):
        st = {"domainStrategy": "AsIs"}
        if fr.get("enabled"):
            st["fragment"] = {k: v for k, v in (("packets", fr.get("packets", "tlshello")), ("length", fr.get("length", "100-200")), ("interval", fr.get("interval", "10-20")), ("maxSplit", fr.get("maxSplit"))) if v}
        if cfg.get("noises"):
            st["noises"] = cfg["noises"]
        outs.append({"protocol": "freedom", "tag": fr.get("tag", "fragment"), "settings": st, "streamSettings": {"sockopt": {"tcpNoDelay": True}}})
    rules = R.to_xray_rules(cfg.get("rules", [])) if cfg.get("rules") else []
    rules.append({"type": "field", "network": "tcp,udp", "balancerTag": "balancer"})
    bal = {"tag": "balancer", "selector": tags, "strategy": {"type": cfg.get("bal", "leastLoad"), "settings": {"expected": min(3, max(1, len(tags))), "maxRTT": "2s", "tolerance": 0.01, "baselines": ["2s"]}}}
    if tags:
        bal["fallbackTag"] = tags[0]
    ps = cfg.get("ports", [10808, 10809])
    sn = {"enabled": True, "destOverride": ["http", "tls", "quic"], "routeOnly": True}
    d = {"remarks": cfg.get("remarks", "SubManager"), "log": {"loglevel": "warning"}, "dns": {"servers": cfg.get("dns", ["1.1.1.1", "8.8.8.8"]), "queryStrategy": "UseIP"},
         "inbounds": [{"listen": "127.0.0.1", "port": ps[0], "protocol": "socks", "settings": {"auth": "noauth", "udp": True}, "sniffing": sn, "tag": "socks"},
                      {"listen": "127.0.0.1", "port": ps[1], "protocol": "http", "settings": {}, "sniffing": sn, "tag": "http"}],
         "outbounds": outs, "routing": {"domainStrategy": "IPIfNonMatch", "rules": rules, "balancers": [bal]},
         "observatory": {"subjectSelector": tags, "probeUrl": "https://www.google.com/generate_204", "probeInterval": "1m", "enableConcurrency": True}}
    return d, bad


def gen_singbox(servers, cfg):
    outs, tags, used, bad = [], [], set(), []
    for i, s in enumerate(servers, 1):
        t, p, sc = tag_of(s, i, used), s["params"], s["scheme"]
        o = {"tag": t, "server": s["host"], "server_port": int(s["port"] or 443)}
        tls = None
        if p.get("security") in ("tls", "reality") or sc in ("trojan", "hysteria2", "tuic", "anytls", "naive+https", "https"):
            tls = {"enabled": True, "server_name": p.get("sni") or s["host"], "insecure": tbool(p.get("insecure", "0"))}
            if p.get("alpn"): tls["alpn"] = p["alpn"].split(",")
            if p.get("fp"): tls["utls"] = {"enabled": True, "fingerprint": p["fp"]}
            if p.get("security") == "reality": tls["reality"] = {"enabled": True, "public_key": p.get("pbk", ""), "short_id": p.get("sid", "")}
            fr = cfg.get("fragment", {})
            if fr.get("enabled"): tls["fragment"] = True
        net = {"h2": "http", "mkcp": "kcp"}.get(p.get("type", "tcp"), p.get("type", "tcp"))
        tr = None
        if net == "ws": tr = {"type": "ws", "path": p.get("path", "/"), "headers": {"Host": p["host"]} if p.get("host") else {}}
        elif net == "grpc": tr = {"type": "grpc", "service_name": p.get("serviceName", "")}
        elif net == "http": tr = {"type": "http", "path": p.get("path", "/"), "host": [h for h in p.get("host", "").split(",") if h]}
        elif net == "httpupgrade": tr = {"type": "httpupgrade", "path": p.get("path", "/"), "host": p.get("host", "")}
        elif net == "quic": tr = {"type": "quic"}
        if sc == "vless": o.update(type="vless", uuid=s["id"], flow=p.get("flow", ""))
        elif sc == "vmess": o.update(type="vmess", uuid=s["id"], alter_id=int(p.get("alterId", 0) or 0), security=p.get("encryption", "auto"))
        elif sc == "trojan": o.update(type="trojan", password=s["password"])
        elif sc == "ss": o.update(type="shadowsocks", method=s["method"], password=s["password"])
        elif sc == "hysteria2":
            o.update(type="hysteria2", password=s["password"])
            if p.get("obfs"): o["obfs"] = {"type": "salamander", "password": p.get("obfs-password", "")}
        elif sc == "tuic": o.update(type="tuic", uuid=s["id"], password=s["password"], congestion_control=p.get("congestion_control", "bbr"))
        elif sc == "anytls": o.update(type="anytls", password=s["password"])
        elif sc in ("naive+https", "naive+quic"): o.update(type="naive", username=s["id"], password=s["password"])
        elif sc in ("socks5", "socks"): o.update(type="socks", username=s["id"], password=s["password"])
        elif sc in ("http", "https"): o.update(type="http", username=s["id"], password=s["password"])
        elif sc == "ssh": o.update(type="ssh", user=s["id"], password=s["password"])
        else:
            bad.append("%s(%s)" % (s.get("name", "?"), sc)); continue
        if tls: o["tls"] = tls
        if tr and o["type"] in ("vless", "vmess", "trojan"): o["transport"] = tr
        outs.append(o); tags.append(t)
    outs += [{"type": "selector", "tag": "proxy", "outbounds": ["auto"] + tags}, {"type": "urltest", "tag": "auto", "outbounds": tags}, {"type": "direct", "tag": "direct"}]
    return {"log": {"level": "warn"}, "outbounds": outs, "route": {"final": "proxy", "auto_detect_interface": True}}, bad


def yaml_dump(o, ind=0):
    pad = "  " * ind
    if isinstance(o, dict):
        out = []
        for k, v in o.items():
            if isinstance(v, (dict, list)) and v:
                out.append("%s%s:\n%s" % (pad, k, yaml_dump(v, ind + 1)))
            else:
                out.append("%s%s: %s" % (pad, k, json.dumps(v, ensure_ascii=False) if v != {} and v != [] else ("{}" if v == {} else "[]")))
        return "\n".join(out)
    out = []
    for it in o:
        if isinstance(it, (dict, list)):
            sub = yaml_dump(it, ind + 1).split("\n")
            out.append("%s- %s" % (pad, sub[0].lstrip()) + ("\n" + "\n".join(sub[1:]) if len(sub) > 1 else ""))
        else:
            out.append("%s- %s" % (pad, json.dumps(it, ensure_ascii=False)))
    return "\n".join(out)


def gen_clash(servers, cfg):
    px, names, used, bad = [], [], set(), []
    for i, s in enumerate(servers, 1):
        p, sc = s["params"], s["scheme"]
        n = s.get("name") or "proxy-%d" % i
        while n in used:
            n += "_"
        used.add(n)
        o = {"name": n, "server": s["host"], "port": int(s["port"] or 443)}
        net = {"h2": "h2", "mkcp": "kcp"}.get(p.get("type", "tcp"), p.get("type", "tcp"))
        tlsb = p.get("security") in ("tls", "reality")
        if sc in ("vless", "vmess", "trojan"):
            o.update(type=sc, udp=True)
            o["uuid" if sc != "trojan" else "password"] = s["id"] if sc != "trojan" else s["password"]
            if sc == "vmess": o.update(alterId=int(p.get("alterId", 0) or 0), cipher=p.get("encryption", "auto"))
            if tlsb or sc == "trojan": o["tls"] = True
            if p.get("sni"): o["servername" if sc != "trojan" else "sni"] = p["sni"]
            if p.get("fp"): o["client-fingerprint"] = p["fp"]
            if p.get("alpn"): o["alpn"] = p["alpn"].split(",")
            if p.get("flow"): o["flow"] = p["flow"]
            if p.get("security") == "reality": o["reality-opts"] = {"public-key": p.get("pbk", ""), "short-id": p.get("sid", "")}
            if net != "tcp":
                o["network"] = net
                if net == "ws": o["ws-opts"] = {"path": p.get("path", "/"), "headers": {"Host": p["host"]} if p.get("host") else {}}
                elif net == "grpc": o["grpc-opts"] = {"grpc-service-name": p.get("serviceName", "")}
                elif net == "h2": o["h2-opts"] = {"path": p.get("path", "/"), "host": [h for h in p.get("host", "").split(",") if h]}
                elif net == "http": o["network"] = "http"; o["http-opts"] = {"path": [p.get("path", "/")], "method": p.get("method", "GET")}
                elif net == "xhttp":
                    o["network"] = "xhttp"; o["xhttp-opts"] = {"path": p.get("path", "/"), "host": p.get("host", ""), "mode": p.get("mode", "auto")}
        elif sc == "ss": o.update(type="ss", cipher=s["method"], password=s["password"], udp=True)
        elif sc == "hysteria2":
            o.update(type="hysteria2", password=s["password"], sni=p.get("sni", s["host"]))
            if p.get("obfs"): o.update(obfs=p["obfs"], **{"obfs-password": p.get("obfs-password", "")})
        elif sc == "tuic": o.update(type="tuic", uuid=s["id"], password=s["password"], **{"congestion-controller": p.get("congestion_control", "bbr")})
        elif sc == "anytls": o.update(type="anytls", password=s["password"], sni=p.get("sni", s["host"]))
        elif sc in ("socks5", "socks"): o.update(type="socks5", username=s["id"], password=s["password"])
        elif sc == "http": o.update(type="http", username=s["id"], password=s["password"])
        elif sc == "ssh": o.update(type="ssh", username=s["id"], password=s["password"])
        elif sc == "snell": o.update(type="snell", psk=s["password"], version=int(p.get("version", 3) or 3))
        elif sc == "wireguard": o.update(type="wireguard", **{"private-key": s["id"], "public-key": p.get("publickey", ""), "ip": (p.get("address", "").split(",") or [""])[0]})
        else:
            bad.append("%s(%s)" % (n, sc)); continue
        px.append(o); names.append(n)
    d = {"mixed-port": 7890, "mode": "rule", "proxies": px, "proxy-groups": [{"name": "PROXY", "type": "select", "proxies": ["AUTO"] + names + ["DIRECT"]},
                                                                           {"name": "AUTO", "type": "url-test", "proxies": names, "url": "https://www.gstatic.com/generate_204", "interval": 300}],
         "rules": (["  - " + x for x in []]) or ["MATCH,PROXY"]}
    return yaml_dump(d), bad


# ==========================================================================
#  ИНТЕРФЕЙС
# ==========================================================================
def cfg_get():
    d = {"remarks": "toolkit", "dns": ["1.1.1.1", "8.8.8.8"], "ports": [10808, 10809], "bal": "leastLoad", "mux": False, "mux_n": 8,
         "fragment": {"enabled": False, "packets": "tlshello", "length": "100-200", "interval": "10-20", "maxSplit": "", "tag": "fragment"}, "noises": [], "rules": []}
    d.update(ST.mem(TOOL, "cfg", {}) or {})
    return d


def cfg_save(c_):
    ST.setmem(TOOL, "cfg", {k: v for k, v in c_.items()})


def show_list(sv, params=False):
    if not sv:
        print("[!] " + L("Список пуст", "List is empty")); return
    rows = [[str(i), s["scheme"][:9], trunc(s.get("name") or "-", 18), trunc("%s:%s" % (s["host"], s["port"]), 22), s["params"].get("type", "tcp")[:6], s["params"].get("security", "-")[:7]] for i, s in enumerate(sv, 1)]
    table(rows, ["#", "proto", L("имя", "name"), "addr", "net", "sec"])


def load_sources(sv):
    k = menu(L("Загрузка", "Load"), [("1", L("Файл (SubManager/Input)", "File (SubManager/Input)"), ""), ("2", L("URL подписки", "Subscription URL"), ""), ("3", L("Несколько URL", "Several URLs"), ""),
                                    ("4", L("Вставить ссылки", "Paste links"), ""), ("5", L("Буфер iOS", "iOS clipboard"), "")], tool=TOOL)
    raws = []
    if k == "1":
        for f in pick_files(IN, None, True, tool=TOOL) or []:
            raws.append(f.read_bytes())
    elif k in ("2", "3"):
        while True:
            u = ask("URL%s" % ("" if k == "2" else L(" (Enter — конец)", " (Enter = end)")), "", quit_ok=False)
            if not u:
                break
            d = fetch(u, label="sub")
            if d:
                raws.append(d)
            if k == "2":
                break
    elif k == "4":
        buf, blank = [], 0
        while blank < 2:
            l_ = input(""); blank = blank + 1 if not l_.strip() else 0; buf.append(l_)
        raws.append("\n".join(buf).encode())
    elif k == "5":
        try:
            raws.append(open("/dev/clipboard", "rb").read())
        except Exception:
            print("[!] n/a")
    added = 0
    for r in raws:
        txt, why = decode_download(r)
        if txt is None:
            print("[!] " + why); continue
        ns = extract_servers(txt)
        sv.extend(ns); added += len(ns)
    print(("[+] " if added else "[!] ") + L("Добавлено серверов: %d (всего %d)" % (added, len(sv)), "Servers added: %d (total %d)" % (added, len(sv))))


def param_editor(sv, idxs):
    s0 = sv[idxs[0]]
    cat = menu(L("Что менять у %d сервер(ов)" % len(idxs), "What to change on %d server(s)" % len(idxs)), [
        ("1", L("Основное (имя, хост, порт, id, пароль, метод)", "Basics (name, host, port, id, password, method)"), ""), ("2", L("Транспорт и его параметры", "Transport & its options"), s0["params"].get("type", "tcp")),
        ("3", L("XHTTP: расширенные параметры (extra)", "XHTTP: advanced options (extra)"), ""), ("4", L("TLS / REALITY", "TLS / REALITY"), s0["params"].get("security", "none")),
        ("5", L("Прочее (flow, obfs, hysteria/tuic/wg…)", "Other (flow, obfs, hysteria/tuic/wg…)"), ""), ("6", L("Любой свой параметр (ключ=значение)", "Any custom param (key=value)"), "")], show=True)
    if cat == "q":
        return
    def setp(k, v):
        for i in idxs:
            if v in ("", None):
                sv[i]["params"].pop(k, None)
            else:
                sv[i]["params"][k] = v
    if cat == "1":
        for key in ("name", "host", "port", "id", "password", "method"):
            v = ask(key + L(" ('-' очистить, Enter пропустить)", " ('-' clear, Enter skip)"), "", quit_ok=False)
            if v:
                for i in idxs:
                    sv[i][key] = "" if v == "-" else v
    elif cat == "2":
        for j, t in enumerate(TRANSPORTS, 1):
            print("  %s %s" % (c(str(j), accent(), True), t))
        v = ask(L("Транспорт (номер, Enter — оставить)", "Transport (number, Enter = keep)"), "", quit_ok=False)
        if v.isdigit() and 1 <= int(v) <= len(TRANSPORTS):
            setp("type", TRANSPORTS[int(v) - 1])
        net = {"h2": "http", "mkcp": "kcp"}.get(sv[idxs[0]]["params"].get("type", "tcp"), sv[idxs[0]]["params"].get("type", "tcp"))
        for key, ru, en, kind in TF.get(net, []):
            cur = sv[idxs[0]]["params"].get(key, "")
            v = ask("%s" % L(ru, en), str(cur), quit_ok=False, hint=L("'-' очистить", "'-' clear"))
            if v != str(cur):
                setp(key, "" if v == "-" else v)
    elif cat == "3":
        ex = xhttp_extra(sv[idxs[0]]["params"])
        while True:
            for i, k in enumerate(XEXTRA, 1):
                cur = ex
                for part in k.split("."):
                    cur = cur.get(part) if isinstance(cur, dict) else None
                print("%s %-44s %s" % (c("%2d" % i, accent()), k, c(K.short(cur, 24), OK_C) if cur is not None else ""))
            v = ask(L("№ параметра / 'x' свой ключ / Enter — готово", "Param # / 'x' custom key / Enter = done"), "", quit_ok=False)
            if not v:
                break
            key = ask(L("Ключ (a.b.c)", "Key (a.b.c)"), "", quit_ok=False) if v == "x" else (XEXTRA[int(v) - 1] if v.isdigit() and 1 <= int(v) <= len(XEXTRA) else None)
            if not key:
                continue
            val = ask("%s = (JSON/текст, '-' удалить)" % key, "", quit_ok=False)
            if val == "-":
                d_ = ex
                ks = key.split(".")
                for kk in ks[:-1]:
                    d_ = d_.get(kk, {})
                d_.pop(ks[-1], None)
            elif val:
                try:
                    val = json.loads(val)
                except Exception:
                    pass
                nested_set(ex, key, val)
        for i in idxs:
            sv[i]["params"] = {k: v for k, v in sv[i]["params"].items() if not k.startswith("x.") and k != "extra"}
            if ex:
                sv[i]["params"]["extra"] = json.dumps(ex, ensure_ascii=False, separators=(",", ":"))
            sv[i]["params"]["type"] = "xhttp"
    elif cat in ("4", "5"):
        fl = TLS_F if cat == "4" else OTHER_F
        if cat == "4":
            v = ask(L("security: 1 none, 2 tls, 3 reality, Enter — оставить", "security: 1 none, 2 tls, 3 reality, Enter = keep"), "", quit_ok=False)
            if v in ("1", "2", "3"):
                setp("security", {"1": "none", "2": "tls", "3": "reality"}[v])
        for key, desc, kind in fl:
            cur = sv[idxs[0]]["params"].get(key, "")
            v = ask(desc, str(cur), quit_ok=False, hint="'-'")
            if v != str(cur):
                setp(key, "" if v == "-" else v)
    elif cat == "6":
        kv = ask("key=value", "", quit_ok=False)
        if "=" in kv:
            setp(*kv.split("=", 1))


def edit_menu(sv):
    while True:
        show_list(sv)
        k = menu(L("Редактирование", "Editing"), [("1", L("Изменить параметры выбранных", "Edit parameters of selected"), ""), ("2", L("Переименовать (шаблон)", "Rename (pattern)"), ""), ("3", L("Удалить по номерам", "Delete by numbers"), ""),
                                                ("4", L("Удалить по фильтру (имя/протокол/транспорт)", "Delete by filter (name/protocol/transport)"), ""), ("5", L("Убрать дубликаты", "Remove duplicates"), ""),
                                                ("6", L("Сортировка", "Sort"), ""), ("7", L("Дублировать", "Duplicate"), ""), ("8", L("Добавить ссылку вручную", "Add a link manually"), ""), ("9", L("Показать ссылку/детали", "Show link/details"), "")], show=False)
        if k == "q":
            return
        try:
            if k == "1":
                sel = ask_multi(L("Какие серверы", "Which servers"), len(sv))
                if sel: param_editor(sv, [i - 1 for i in sel])
            elif k == "2":
                sel = ask_multi(L("Какие серверы", "Which servers"), len(sv))
                pat = ask(L("Шаблон: {n} номер, {p} протокол, {h} хост, {t} транспорт", "Pattern: {n} number, {p} proto, {h} host, {t} transport"), "{p}-{n}", quit_ok=False)
                for i in sel or []:
                    sv[i - 1]["name"] = pat.format(n=i, p=sv[i - 1]["scheme"], h=sv[i - 1]["host"], t=sv[i - 1]["params"].get("type", "tcp"))
            elif k == "3":
                for i in sorted(ask_multi(L("Номера", "Numbers"), len(sv)) or [], reverse=True):
                    sv.pop(i - 1)
            elif k == "4":
                w = ask(L("Что содержит имя/протокол/транспорт/хост (слова через запятую)", "Contains in name/proto/transport/host (comma words)"), "", quit_ok=False).lower().split(",")
                w = [x.strip() for x in w if x.strip()]
                hits = [i for i, s in enumerate(sv) if any(x in (s["name"] + " " + s["scheme"] + " " + s["params"].get("type", "") + " " + s["host"]).lower() for x in w)]
                print("[*] " + L("Найдено: %d" % len(hits), "Found: %d" % len(hits)))
                if hits and confirm(L("Удалить?", "Delete?")):
                    for i in reversed(hits): sv.pop(i)
            elif k == "5":
                seen, out = set(), []
                for s in sv:
                    key = (s["scheme"], s["host"], s["port"], s["id"] or s["password"])
                    if key not in seen: seen.add(key); out.append(s)
                print("[+] " + L("Удалено: %d" % (len(sv) - len(out)), "Removed: %d" % (len(sv) - len(out)))); sv[:] = out
            elif k == "6":
                o = ask(L("1 имя, 2 протокол, 3 хост, 4 случайно, 5 транспорт", "1 name, 2 proto, 3 host, 4 random, 5 transport"), "1", quit_ok=False)
                if o == "4": random.shuffle(sv)
                else: sv.sort(key=lambda s: {"1": s["name"].lower(), "2": s["scheme"], "3": s["host"], "5": s["params"].get("type", "")}.get(o, s["name"]))
            elif k == "7":
                for i in ask_multi(L("Какие", "Which"), len(sv)) or []:
                    q = copy.deepcopy(sv[i - 1]); q["name"] += " (copy)"; sv.append(q)
            elif k == "8":
                s = parse_uri(ask(L("Ссылка", "Link"), "", quit_ok=False))
                sv.append(s) if s else print("[!] " + L("не разобрана", "could not parse"))
            elif k == "9":
                n = ask("№", "", quit_ok=False)
                if n.isdigit() and 1 <= int(n) <= len(sv):
                    print(build_uri(sv[int(n) - 1])); print(json.dumps(sv[int(n) - 1]["params"], ensure_ascii=False, indent=1)); pause()
        except (ValueError, IndexError, KeyError) as e:
            print("[!] %s" % e)
        autosave(sv)


def autosave(sv):
    if sv:
        try:
            atomic_write(AUTOSAVE, "\n".join(build_uri(s) for s in sv))
        except Exception:
            pass


def settings_cfg(cfg):
    while True:
        fr = cfg["fragment"]
        k = menu(L("Настройки генерации (Xray/sing-box)", "Generation settings (Xray/sing-box)"), [
            ("1", L("Фрагментация TLS", "TLS fragmentation"), "on" if fr["enabled"] else "off"), ("2", L("Шумы (noises)", "Noises"), str(len(cfg["noises"]))), ("3", "DNS", ",".join(cfg["dns"])[:20]),
            ("4", L("Порты SOCKS/HTTP", "SOCKS/HTTP ports"), "%s/%s" % tuple(cfg["ports"])), ("5", L("Балансировщик", "Balancer"), cfg["bal"]), ("6", "Mux", "on" if cfg["mux"] else "off"),
            ("7", L("Правила роутинга из файла (ListLab/ConfigForge)", "Routing rules from a file (ListLab/ConfigForge)"), str(len(cfg["rules"]))), ("8", L("Название (remarks)", "Title (remarks)"), cfg["remarks"])], show=True)
        if k == "q":
            cfg_save(cfg); return
        if k == "1":
            fr["enabled"] = confirm(L("Включить фрагментацию?", "Enable fragmentation?"), fr["enabled"])
            if fr["enabled"]:
                fr["packets"] = ask(L("packets (tlshello / 1-3 / 1-1)", "packets (tlshello / 1-3 / 1-1)"), fr["packets"], quit_ok=False)
                fr["length"] = ask(L("length — длина фрагментов, байт (100-200)", "length — fragment size, bytes (100-200)"), fr["length"], quit_ok=False)
                fr["interval"] = ask(L("interval — задержка, мс (10-20)", "interval — delay, ms (10-20)"), fr["interval"], quit_ok=False)
                fr["maxSplit"] = ask(L("maxSplit — макс. число частей (напр. 100-200, Enter — нет)", "maxSplit — max parts (e.g. 100-200, Enter = none)"), fr.get("maxSplit", ""), quit_ok=False)
        elif k == "2":
            while True:
                for i, n in enumerate(cfg["noises"], 1):
                    print("  %d. %s" % (i, json.dumps(n)))
                a = ask(L("a добавить | d удалить № | Enter готово", "a add | d delete # | Enter done"), "", quit_ok=False)
                if a == "a":
                    cfg["noises"].append({"type": ask("type (rand/str/base64/hex)", "rand", quit_ok=False), "packet": ask(L("packet (размер или данные, напр. 10-20)", "packet (size or data, e.g. 10-20)"), "10-20", quit_ok=False),
                                          "delay": ask(L("delay, мс", "delay, ms"), "10-16", quit_ok=False), "applyTo": ask("applyTo (ip/ipv4/ipv6)", "ip", quit_ok=False)})
                elif a.startswith("d") and a[1:].strip().isdigit() and 0 < int(a[1:]) <= len(cfg["noises"]):
                    cfg["noises"].pop(int(a[1:]) - 1)
                elif not a:
                    break
        elif k == "3":
            cfg["dns"] = [x.strip() for x in ask("DNS", ",".join(cfg["dns"]), quit_ok=False).split(",") if x.strip()]
        elif k == "4":
            a, b = ask("SOCKS", str(cfg["ports"][0]), quit_ok=False), ask("HTTP", str(cfg["ports"][1]), quit_ok=False)
            if a.isdigit() and b.isdigit(): cfg["ports"] = [int(a), int(b)]
        elif k == "5":
            cfg["bal"] = {"1": "leastLoad", "2": "leastPing", "3": "random", "4": "roundRobin"}.get(ask("1 leastLoad, 2 leastPing, 3 random, 4 roundRobin", "1", quit_ok=False), "leastLoad")
        elif k == "6":
            cfg["mux"] = not cfg["mux"]
        elif k == "7":
            fs = pick_files(BASE / "ListLab" / "Output", None, False, tool=TOOL) or pick_files(BASE / "ConfigForge" / "Output", None, False, tool=TOOL)
            if fs:
                cfg["rules"] = [l_ for l_ in smart_read(fs[0]).splitlines() if R.parse_line(l_)["kind"] == "rule"]
        elif k == "8":
            cfg["remarks"] = ask(L("Название", "Title"), cfg["remarks"], quit_ok=False)


def export_menu(sv, cfg):
    if not sv:
        print("[!] " + L("Нет серверов", "No servers")); return
    show_list(sv)
    sel = ask_multi(L("Какие серверы экспортировать (all — все)", "Which servers to export (all)"), len(sv), "all") or list(range(1, len(sv) + 1))
    sub = [sv[i - 1] for i in sel]
    k = menu(L("Экспорт", "Export"), [("1", L("Ссылки + base64 (подписка)", "Links + base64 (subscription)"), ""), ("2", "Xray JSON", L("балансировщик, роутинг, фрагментация", "balancer, routing, fragmentation")), ("3", "sing-box JSON", ""),
                                    ("4", "Clash / Mihomo YAML", ""), ("5", L("Ссылки импорта для клиентов (+QR)", "Client import links (+QR)"), "")], show=False)
    nm = sanitize_filename(ask(L("Имя файла", "File name"), ST.mem(TOOL, "fname", "servers"), quit_ok=False)); ST.setmem(TOOL, "fname", nm)
    OUT.mkdir(parents=True, exist_ok=True)
    if k == "1":
        raw = "\n".join(build_uri(s) for s in sub)
        atomic_write(OUT / (nm + ".txt"), raw); atomic_write(OUT / (nm + "_base64.txt"), base64.b64encode(raw.encode()).decode())
        print("[+] %s (%d)" % (OUT / (nm + ".txt"), len(sub)))
    elif k in ("2", "3", "4"):
        if k == "2": d, bad = gen_xray(sub, cfg); out, ext = json.dumps(d, ensure_ascii=False, indent=1), "json"
        elif k == "3": d, bad = gen_singbox(sub, cfg); out, ext = json.dumps(d, ensure_ascii=False, indent=1), "singbox.json"
        else: out, bad = gen_clash(sub, cfg); ext = "yaml"
        atomic_write(OUT / ("%s.%s" % (nm, ext)), out)
        print("[+] %s" % (OUT / ("%s.%s" % (nm, ext))))
        if bad:
            print("[!] " + L("Этот формат не поддерживает (пропущены): ", "Not supported by this format (skipped): ") + ", ".join(bad[:10]))
    elif k == "5":
        url = ask(L("URL, где опубликована подписка (GitHub raw и т.п.)", "URL where the subscription is published (GitHub raw etc.)"), "", quit_ok=False)
        names = list(RT.CLIENTS)
        for i, n in enumerate(names, 1):
            print("  %s %s" % (c("%2d" % i, accent(), True), n))
        for i in ask_multi(L("Клиенты", "Clients"), len(names), "all") or []:
            for kind in RT.CLIENTS[names[i - 1]]:
                for lnk in RT.client_links(names[i - 1], kind, url, "", nm):
                    print("  %s [%s] %s" % (c(names[i - 1][:14], accent()), kind, lnk))
        if confirm(L("Показать QR для первой ссылки?", "Show QR for the first link?")):
            import qr
            qr.show_qr(url)


def health(sv):
    from concurrent.futures import ThreadPoolExecutor
    res = {}
    def one(i):
        t = time.time()
        try:
            socket.create_connection((sv[i]["host"], int(sv[i]["port"] or 443)), 4).close()
            return i, round((time.time() - t) * 1000)
        except Exception:
            return i, None
    bar = Bar(len(sv), "tcp-ping", "")
    with ThreadPoolExecutor(max_workers=8) as ex:
        for n, (i, ms) in enumerate(ex.map(one, range(len(sv))), 1):
            res[i] = ms; bar.update(n)
    bar.close()
    rows = [[str(i + 1), trunc(sv[i]["name"], 20), trunc(sv[i]["host"], 22), (c("%d ms" % ms, OK_C) if ms is not None else c("fail", ERR_C))] for i, ms in sorted(res.items(), key=lambda x: (x[1] is None, x[1] or 0))]
    table(rows, ["#", L("имя", "name"), "host", "tcp"])
    dead = [i for i, ms in res.items() if ms is None]
    if dead and confirm(L("Удалить недоступные (%d)?" % len(dead), "Remove unreachable (%d)?" % len(dead))):
        for i in sorted(dead, reverse=True): sv.pop(i)


def main():
    ensure_dirs("SubManager/Input", "SubManager/Output", "SubManager/Backups", "SubManager/Routing")
    sv = []
    try:
        sv = extract_servers(AUTOSAVE.read_text("utf-8")) if AUTOSAVE.exists() else []
        if sv:
            print("[+] " + L("Автозагрузка прошлой сессии: %d" % len(sv), "Restored previous session: %d" % len(sv)))
    except Exception:
        pass
    cfg = cfg_get()
    while True:
        k = menu("SubManager (%d)" % len(sv), [("1", L("Загрузить подписки/ссылки", "Load subscriptions/links"), ""), ("2", L("Список и статистика", "List & stats"), ""), ("3", L("Редактирование и параметры", "Editing & parameters"), L("транспорты, XHTTP, TLS…", "transports, XHTTP, TLS…")),
                                              ("4", L("Экспорт (ссылки, Xray, sing-box, Clash, клиенты)", "Export (links, Xray, sing-box, Clash, clients)"), ""), ("5", L("Настройки генерации (фрагмент, шумы, DNS, роутинг)", "Generation settings (fragment, noises, DNS, routing)"), ""),
                                              ("6", L("Проверка доступности серверов (TCP)", "Server reachability check (TCP)"), ""), ("7", L("Бэкап / очистить автосохранение", "Backup / clear autosave"), ""), ("8", L("Файлы и очистка", "Files & cleanup"), "")], tool=TOOL)
        if k == "q":
            autosave(sv); return
        try:
            if k == "1": load_sources(sv)
            elif k == "2":
                show_list(sv)
                if sv:
                    for title, key in ((L("Протоколы", "Protocols"), lambda s: s["scheme"]), (L("Транспорты", "Transports"), lambda s: s["params"].get("type", "tcp")), ("Security", lambda s: s["params"].get("security", "none"))):
                        print(c(title, accent(), True) + ": " + ", ".join("%s=%d" % kv for kv in Counter(key(s) for s in sv).most_common()))
            elif k == "3": edit_menu(sv)
            elif k == "4": export_menu(sv, cfg)
            elif k == "5": settings_cfg(cfg)
            elif k == "6": health(sv) if sv else print("[!] " + L("Нет серверов", "No servers"))
            elif k == "7":
                if sv:
                    p = BK / ("backup_%s.txt" % now_stamp()); atomic_write(p, "\n".join(build_uri(s) for s in sv)); print("[+] " + str(p))
                if confirm(L("Очистить автосохранение?", "Clear autosave?")) and AUTOSAVE.exists():
                    AUTOSAVE.unlink()
            elif k == "8": files_menu(TOOL, IN, OUT)
        except KeyboardInterrupt:
            print("\n[*] " + L("Отменено", "Cancelled"))
        autosave(sv)
        if k in "2467":
            pause()


from collections import Counter

if __name__ == "__main__":
    run_tool("SubManager", main)
TKEOF_subman

tk_put regexb.py << 'TKEOF_regexb'
# -*- coding: utf-8 -*-
# ==========================================================================
#  RegexBuilder — понятный помощник для регулярных выражений под сетевые задачи:
#  паттерны URL для скриптов/правил, regex из списка доменов, пошаговый конструктор,
#  проверка на примерах с подсветкой, объяснение, шпаргалка, сетевые шаблоны.
# ==========================================================================
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from tkcore import *
import tkcodec as K

TOOL = "regexb"
PRESETS = [("IPv4", r"\b(?:\d{1,3}\.){3}\d{1,3}\b"), ("IPv6", r"\b(?:[0-9a-fA-F]{1,4}:){2,7}[0-9a-fA-F]{1,4}\b"), ("CIDR", r"\b(?:\d{1,3}\.){3}\d{1,3}/\d{1,2}\b"),
           ("Домен/Domain", r"\b(?:[a-z0-9-]+\.)+[a-z]{2,}\b"), ("URL", r"https?:\/\/[^\s\"'<>]+"), ("Порт/Port", r":(\d{2,5})\b"), ("UUID", r"\b[0-9a-fA-F]{8}-(?:[0-9a-fA-F]{4}-){3}[0-9a-fA-F]{12}\b"),
           ("MAC", r"\b(?:[0-9A-Fa-f]{2}[:-]){5}[0-9A-Fa-f]{2}\b"), ("ASN", r"\bAS\d{1,10}\b"), ("VPN-ссылка/link", r"\b(?:vless|vmess|trojan|ss|hysteria2?|tuic|wireguard)://[^\s]+")]


def hist_add(rx):
    h = ST.mem(TOOL, "history", [])
    h = [rx] + [x for x in h if x != rx]
    ST.setmem(TOOL, "history", h[:20])


def result(rx, what=""):
    print("\n" + c(L("Готовый regex:", "Your regex:"), accent(), True))
    print(c(rx, OK_C, True))
    hist_add(rx)
    if clip_copy(rx):
        print(dim(L("(скопирован в буфер iOS)", "(copied to the iOS clipboard)")))
    for w in dialect_warnings(rx):
        print("[*] " + w)


def dialect_warnings(rx):
    w = []
    if re.search(r"\(\?P<", rx):
        w.append(L("(?P<имя>…) — синтаксис Python; в JS/ICU используйте (?<имя>…)", "(?P<name>…) is Python syntax; use (?<name>…) in JS/ICU"))
    if re.search(r"\(\?[<]?[=!]", rx) and "(?<" in rx:
        w.append(L("lookbehind поддерживается не везде — проверьте на устройстве", "lookbehind isn't supported everywhere — verify on the device"))
    if re.search(r"(?<!\\)/", rx) and not rx.startswith("^"):
        w.append(L("слэши в URL лучше экранировать: \\/ (как в модулях)", "escape slashes in URLs as \\/ (as in modules)"))
    return w


def url_wizard():
    print(dim(L("Вставьте 1–5 примеров ссылок (пустая строка — конец). Если ссылок несколько — найду общую часть.", "Paste 1–5 sample URLs (blank = end). With several, I'll find the common part.")))
    urls = []
    while len(urls) < 8:
        u = ask(L("Ссылка", "URL"), "", quit_ok=False)
        if not u:
            break
        urls.append(u)
    if not urls:
        return
    if len(urls) == 1:
        rx = K.url_to_pattern(urls[0], keep_query=confirm(L("Учитывать параметры запроса (?a=b)?", "Match the query string (?a=b)?")))
    else:
        from urllib.parse import urlparse
        ps = [urlparse(u) for u in urls]
        hosts = sorted({p.netloc for p in ps})
        segs = [p.path.strip("/").split("/") for p in ps]
        n = min(len(s) for s in segs)
        common = []
        for i in range(n):
            col = {s[i] for s in segs}
            common.append(re.escape(col.pop()) if len(col) == 1 else "[^/]+")
        hrx = re.escape(hosts[0]) if len(hosts) == 1 else "(" + "|".join(re.escape(h) for h in hosts) + ")"
        rx = "^https?:\\/\\/%s\\/%s" % (hrx.replace(".", "\\.") if len(hosts) == 1 else hrx, "\\/".join(common)) + ("(\\/.*)?" if len({len(s) for s in segs}) > 1 else "") + "(\\?.*)?$"
        rx = rx.replace("\\\\.", "\\.")
    print("\n" + c(L("Проверка на ваших ссылках:", "Check on your URLs:"), INFO_C, True))
    for u in urls:
        print("  %s %s" % (c(OK if re.search(rx, u) else BAD, OK_C if re.search(rx, u) else ERR_C, True), trunc(u, term_w() - 6)))
    result(rx)


OK, BAD = "✓", "✗"


def domains_wizard():
    print(dim(L("Вставьте домены (по одному, пустая строка — конец).", "Paste domains (one per line, blank = end).")))
    ds = []
    while True:
        d = ask(L("Домен", "Domain"), "", quit_ok=False).lower().lstrip("*.")
        if not d:
            break
        ds.append(d)
    if not ds:
        return
    sub = confirm(L("Включать поддомены (*.домен)?", "Include subdomains (*.domain)?"), True)
    body = "|".join(re.escape(d) for d in sorted(set(ds)))
    rx = "^%s(?:%s)$" % ("(?:[^.]+\\.)*" if sub else "", body)
    result(rx)
    if confirm(L("Сделать паттерн для URL (https://…/)?", "Make a URL pattern (https://…/)?")):
        result("^https?:\\/\\/%s(?:%s)(?::\\d+)?\\/" % ("(?:[^\\/.]+\\.)*" if sub else "", body.replace("/", "\\/")))


def builder():
    sch = ask(L("Схема: 1 https, 2 http+https, 3 любая", "Scheme: 1 https, 2 http+https, 3 any"), "2", quit_ok=False)
    rx = "^" + {"1": "https:", "2": "https?:", "3": "[a-z]+:"}.get(sch, "https?:") + "\\/\\/"
    h = ask(L("Хост (api.site.com | *.site.com | a.com,b.com)", "Host (api.site.com | *.site.com | a.com,b.com)"), "", quit_ok=False)
    hs = [x.strip() for x in h.split(",") if x.strip()]
    parts = [("(?:[^\\/.]+\\.)+" + re.escape(x[2:])) if x.startswith("*.") else re.escape(x) for x in hs]
    rx += parts[0] if len(parts) == 1 else "(?:" + "|".join(parts) + ")"
    if confirm(L("Порт может быть указан (:443)?", "Optional port (:443)?")):
        rx += "(?::\\d+)?"
    p = ask(L("Путь (/v1/user/{id}/info — {id} любой сегмент; * — любое окончание)", "Path (/v1/user/{id}/info — {id} any segment; * any tail)"), "/", quit_ok=False)
    tail = ""
    if p.endswith("*"):
        p, tail = p[:-1], ".*"
    seg = [("[^\\/]+" if re.fullmatch(r"\{.*\}", s) else re.escape(s)) for s in p.strip("/").split("/") if s != ""]
    rx += "\\/" + "\\/".join(seg) + (("\\/" if p.endswith("/") and seg else "") + tail)
    if confirm(L("Допускать параметры запроса (?…)?", "Allow a query string (?…)?"), True):
        rx += "(?:\\?.*)?"
    rx += "$" if not tail else ""
    try:
        re.compile(rx)
    except re.error as e:
        print("[!] %s" % e); return
    result(rx)


def tester():
    rx = ask(L("Regex", "Regex"), (ST.mem(TOOL, "history", [""]) or [""])[0], quit_ok=False)
    try:
        cr = re.compile(rx)
    except re.error as e:
        print("[!] %s" % e); return
    for w in dialect_warnings(rx):
        print("[*] " + w)
    print(dim(L("Вводите строки для проверки; пустая — конец.", "Enter test strings; blank = end.")))
    while True:
        s = ask(L("Строка", "String"), "", quit_ok=False)
        if not s:
            return
        ms = list(cr.finditer(s))
        if not ms:
            print("  " + c(BAD + " " + L("не совпало", "no match"), ERR_C)); continue
        out, last = "", 0
        for m in ms:
            out += s[last:m.start()] + c(s[m.start():m.end()], OK_C, True); last = m.end()
        print("  %s %s  %s" % (c(OK, OK_C, True), out + s[last:], dim("x%d" % len(ms))))
        for m in ms[:3]:
            if m.groups():
                print(dim("     groups: " + " | ".join(str(g) for g in m.groups())))


def explain():
    rx = ask("Regex", "", quit_ok=False)
    try:
        re.compile(rx)
    except re.error as e:
        print("[!] %s" % e); return
    tok = [(r"\\d", L("цифра", "digit")), (r"\\w", L("буква/цифра/_", "word char")), (r"\\s", L("пробел", "whitespace")), (r"\\\.", L("точка", "literal dot")), (r"\\/", L("слэш", "slash")), (r"\.\*", L("любые символы", "anything")),
           (r"\[\^[^\]]+\]\+?", L("символы, кроме указанных", "chars except these")), (r"\(\?:", L("группа без захвата", "non-capturing group")), (r"\(\?[=!]", L("проверка вперёд", "lookahead")), (r"\(\?<[=!]", L("проверка назад", "lookbehind")),
           (r"\^", L("начало", "start")), (r"\$", L("конец", "end")), (r"\|", L("или", "or")), (r"\?", L("0 или 1 раз", "0 or 1 time")), (r"\+", L("1+ раз", "1+ times")), (r"\*", L("0+ раз", "0+ times")), (r"\{\d+(,\d*)?\}", L("повторов", "repeats")), (r"\(", L("группа", "group")), (r"\)", L("конец группы", "end group"))]
    i = 0
    while i < len(rx):
        for pat, desc in tok:
            m = re.match(pat, rx[i:])
            if m:
                print("  %-22s %s" % (c(m.group(0), accent(), True), desc)); i += len(m.group(0)); break
        else:
            j = i
            while j < len(rx) and not re.match(r"[\\\[\](){}|?*+^$.]", rx[j]):
                j += 1
            print("  %-22s %s" % (c(rx[i:max(j, i + 1)], INFO_C), L("текст как есть", "literal text"))); i = max(j, i + 1)


def cheat():
    print(L("""Шпаргалка (Shadowrocket/JS/ICU):
 ^ $      начало/конец          .  любой символ      \\.  настоящая точка
 \\/       слэш (в модулях экранируют)   [^\\/]+  один сегмент пути
 (a|b)    или                    (?:…)  группа без захвата   $1 $2  подстановки в URL Rewrite
 ?        0 или 1 раз            +  1 и более        *  любое число
 (\\?.*)?  необязательные параметры запроса
 URL-REGEX / pattern= — регулярное выражение по ПОЛНОЙ ссылке.
 Совет: сначала тест на 2–3 реальных ссылках (пункт «Проверить»).""", """Cheat sheet (Shadowrocket/JS/ICU):
 ^ $      start/end             .  any char          \\.  literal dot
 \\/       slash (escaped in modules)   [^\\/]+  one path segment
 (a|b)    or                     (?:…)  non-capturing group   $1 $2  substitutions in URL Rewrite
 ?        0 or 1                 +  1 or more        *  any count
 (\\?.*)?  optional query string
 URL-REGEX / pattern= match the FULL URL.
 Tip: test on 2–3 real URLs first ('Test' item)."""))


def main():
    while True:
        k = menu("RegexBuilder", [("1", L("Ссылка(и) → готовый паттерн", "URL(s) → ready pattern"), L("для скриптов, URL-REGEX, rewrite", "for scripts, URL-REGEX, rewrite")), ("2", L("Список доменов → regex", "Domain list → regex"), ""),
                                  ("3", L("Пошаговый конструктор (схема/хост/путь)", "Step-by-step builder (scheme/host/path)"), ""), ("4", L("Проверить regex на строках", "Test a regex on strings"), ""), ("5", L("Объяснить regex", "Explain a regex"), ""),
                                  ("6", L("Сетевые шаблоны (IP, CIDR, домен, UUID…)", "Network presets (IP, CIDR, domain, UUID…)"), ""), ("7", L("История", "History"), ""), ("8", L("Шпаргалка", "Cheat sheet"), "")], tool=TOOL)
        if k == "q":
            return
        try:
            if k == "1": url_wizard()
            elif k == "2": domains_wizard()
            elif k == "3": builder()
            elif k == "4": tester()
            elif k == "5": explain()
            elif k == "6":
                for i, (n, p) in enumerate(PRESETS, 1):
                    print("  %s %-16s %s" % (c("%2d" % i, accent(), True), n, dim(p)))
                n = ask("№", "", quit_ok=False)
                if n.isdigit() and 1 <= int(n) <= len(PRESETS):
                    result(PRESETS[int(n) - 1][1])
            elif k == "7":
                for i, x in enumerate(ST.mem(TOOL, "history", []), 1):
                    print("  %s %s" % (c("%2d" % i, accent(), True), x))
            elif k == "8": cheat()
        except KeyboardInterrupt:
            print("\n[*] " + L("Отменено", "Cancelled"))
        pause()


if __name__ == "__main__":
    run_tool("RegexBuilder", main)
TKEOF_regexb

tk_put vault.py << 'TKEOF_vault'
# -*- coding: utf-8 -*-
# ==========================================================================
#  Vault — шифрование файлов Toolkit (все или выбранные) и расшифровка по ключу.
#  Схема (только stdlib): ключ → HKDF(HMAC-SHA256) → enc_key/mac_key; поток = BLAKE2b(key, nonce‖counter);
#  целостность: HMAC-SHA256 (encrypt-then-MAC). Формат файла: TKV1 | salt | nonce | ciphertext | tag.
#  Ключ: файл-ключ (base64) либо пароль (PBKDF2/scrypt). Без ключа/пароля расшифровать нельзя.
# ==========================================================================
import sys, os, hmac
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from tkcore import *

TOOL = "vault"
KEYFILE = CONF / "vault.key"
MAGIC = b"TKV1"
ROOTS = ["AdBlock", "SQLiteTXT", "SpyLog", "SubManager", "ScriptForge", "ConfigForge", "ListLab", "Decoder", "RegexBuilder", "NetDiag", "Configurations"]


def hk(master, label):
    return hmac.new(master, label, hashlib.sha256).digest()


def derive(secret, salt, kind):
    if kind == 0:                                              # ключ-файл (32 байта)
        return secret
    try:
        return hashlib.scrypt(secret, salt=salt, n=2 ** 14, r=8, p=1, dklen=32)
    except Exception:
        return hashlib.pbkdf2_hmac("sha256", secret, salt, 200000, 32)


def keystream_xor(data, key, nonce):
    out, ctr, pos = bytearray(len(data)), 0, 0
    while pos < len(data):
        chunk = data[pos:pos + 65536]
        ks = b"".join(hashlib.blake2b(nonce + struct.pack(">Q", ctr + i), key=key, digest_size=64).digest() for i in range((len(chunk) + 63) // 64))
        ctr += (len(chunk) + 63) // 64
        n = len(chunk)
        out[pos:pos + n] = (int.from_bytes(chunk, "big") ^ int.from_bytes(ks[:n], "big")).to_bytes(n, "big")
        pos += n
    return bytes(out)


def encrypt(data, secret, kind):
    salt, nonce = os.urandom(16), os.urandom(16)
    master = derive(secret, salt, kind)
    ek, mk = hk(master, b"enc"), hk(master, b"mac")
    ct = keystream_xor(data, ek, nonce)
    head = MAGIC + bytes([kind]) + salt + nonce
    return head + ct + hmac.new(mk, head + ct, hashlib.sha256).digest()


def decrypt(blob, secret_fn):
    if blob[:4] != MAGIC or len(blob) < 4 + 1 + 32 + 32:
        raise ValueError(L("не файл Vault или повреждён", "not a Vault file or damaged"))
    kind, salt, nonce = blob[4], blob[5:21], blob[21:37]
    master = derive(secret_fn(kind), salt, kind)
    ek, mk = hk(master, b"enc"), hk(master, b"mac")
    ct, tag = blob[37:-32], blob[-32:]
    if not hmac.compare_digest(tag, hmac.new(mk, blob[:-32], hashlib.sha256).digest()):
        raise ValueError(L("неверный ключ/пароль или файл повреждён", "wrong key/password or file damaged"))
    return keystream_xor(ct, ek, nonce)


def get_key():
    if KEYFILE.exists():
        return base64.b64decode(KEYFILE.read_text().strip())
    return None


def make_key():
    k = os.urandom(32)
    CONF.mkdir(parents=True, exist_ok=True)
    KEYFILE.write_text(base64.b64encode(k).decode()); os.chmod(str(KEYFILE), 0o600)
    return k


_pw = [None]


def secret_for(kind):
    if kind == 0:
        k = get_key()
        if not k:
            t = ask(L("Ключ не найден. Вставьте ключ (base64)", "Key not found. Paste the key (base64)"), "", quit_ok=False)
            k = base64.b64decode(t.strip()) if t else None
            if not k:
                raise ValueError(L("нет ключа", "no key"))
        return k
    if _pw[0] is None:
        _pw[0] = ask(L("Пароль", "Password"), "", quit_ok=False).encode()
    return _pw[0]


def pick_targets():
    k = menu(L("Что обработать", "What to process"), [("1", L("Выбрать файлы в папке инструмента", "Pick files in a tool folder"), ""), ("2", L("Все данные Toolkit (все подпапки)", "All Toolkit data (all subfolders)"), ""),
                                                    ("3", L("Свой путь (файл или папка)", "Custom path (file or folder)"), "")], show=False)
    if k == "q":
        return []
    if k == "1":
        for i, r in enumerate(ROOTS, 1):
            print("  %s %s" % (c("%2d" % i, accent(), True), r))
        n = ask(L("Папка №", "Folder #"), "", quit_ok=False)
        if not (n.isdigit() and 1 <= int(n) <= len(ROOTS)):
            return []
        base = BASE / ROOTS[int(n) - 1]
        allf = [Path(r) / f for r, _, fs in os.walk(str(base)) for f in fs]
        for i, f in enumerate(allf[:80], 1):
            print("  %s %s" % (c("%2d" % i, accent(), True), trunc(str(f.relative_to(base)), term_w() - 8)))
        sel = ask_multi(L("Файлы", "Files"), len(allf[:80]))
        return [allf[i - 1] for i in sel or []]
    if k == "2":
        return [Path(r) / f for root in ROOTS for r, _, fs in os.walk(str(BASE / root)) for f in fs]
    p = Path(ask(L("Путь", "Path"), "", quit_ok=False))
    return [p] if p.is_file() else [Path(r) / f for r, _, fs in os.walk(str(p)) for f in fs] if p.is_dir() else []


def main():
    while True:
        k = menu(L("Шифрование файлов", "File encryption"), [("1", L("Зашифровать", "Encrypt"), ""), ("2", L("Расшифровать (.tkv)", "Decrypt (.tkv)"), ""), ("3", L("Ключ: создать / показать / импортировать", "Key: create / show / import"), L("есть" if KEYFILE.exists() else "нет", "yes" if KEYFILE.exists() else "no")),
                                                         ("4", L("Забыть пароль в памяти", "Forget password in memory"), "")], tool=TOOL)
        if k == "q":
            return
        try:
            if k in ("1", "2"):
                fl = [f for f in pick_targets() if (f.suffix == ".tkv") == (k == "2")]
                if not fl:
                    print("[!] " + L("Нет подходящих файлов", "No suitable files")); continue
                kind = 0
                if k == "1":
                    kind = 0 if get_key() and confirm(L("Использовать файл-ключ? (нет — пароль)", "Use key file? (no = password)"), True) else 1
                    if kind == 0 and not get_key():
                        make_key(); print("[+] " + L("Создан ключ. СОХРАНИТЕ его (пункт 3 → показать)!", "Key created. BACK IT UP (item 3 → show)!"))
                    if kind == 1 and _pw[0] is None:
                        _pw[0] = ask(L("Новый пароль", "New password"), "", quit_ok=False).encode()
                rm = confirm(L("Удалять исходные файлы после операции?", "Delete source files afterwards?"))
                ok = bad = 0
                for f in track(fl, label="vault"):
                    try:
                        data = f.read_bytes()
                        if k == "1":
                            out = encrypt(data, secret_for(kind) if kind == 0 else _pw[0], kind); dst = f.with_name(f.name + ".tkv")
                        else:
                            out = decrypt(data, secret_for); dst = f.with_name(f.name[:-4])
                        dst.write_bytes(out)
                        if rm:
                            f.write_bytes(os.urandom(min(len(data), 1 << 20))) if k == "1" and len(data) <= 1 << 20 else None
                            f.unlink()
                        ok += 1
                    except Exception as e:
                        bad += 1; print("[!] %s: %s" % (f.name, e))
                print("[+] %s: %d, %s: %d" % (L("Готово", "Done"), ok, L("ошибок", "errors"), bad))
            elif k == "3":
                s = menu(L("Ключ", "Key"), [("1", L("Создать новый (старый будет потерян!)", "Create new (old one is lost!)"), ""), ("2", L("Показать (для резервной копии)", "Show (for backup)"), ""), ("3", L("Импортировать из текста", "Import from text"), "")], show=False)
                if s == "1" and (not KEYFILE.exists() or confirm(L("Старый ключ перестанет работать. Продолжить?", "Old key will stop working. Continue?"))):
                    make_key(); print("[+] OK")
                elif s == "2" and KEYFILE.exists():
                    t = KEYFILE.read_text().strip(); print(c(t, WARN_C, True)); print("[+] OK" if clip_copy(t) else ""); print(dim(L("Храните отдельно от данных!", "Store it apart from the data!")))
                elif s == "3":
                    t = ask(L("Ключ base64", "Key base64"), "", quit_ok=False)
                    try:
                        assert len(base64.b64decode(t)) == 32
                        KEYFILE.write_text(t.strip()); os.chmod(str(KEYFILE), 0o600); print("[+] OK")
                    except Exception:
                        print("[!] " + L("неверный ключ", "bad key"))
            elif k == "4":
                _pw[0] = None; print("[+] OK")
        except KeyboardInterrupt:
            print("\n[*] " + L("Отменено", "Cancelled"))
        pause()


if __name__ == "__main__":
    run_tool("Vault", main)
TKEOF_vault

tk_put ghapi.py << 'TKEOF_ghapi'
# -*- coding: utf-8 -*-
# ==========================================================================
#  GitHub — работа с репозиторием через API прямо из консоли: обзор папок, просмотр/правка/загрузка/
#  удаление файлов, коммиты, публикация rule-set и скриптов с готовыми raw-ссылками.
#  Токен (PAT) хранится локально в ~/Shadowrocket/.config/github.json (права 600).
# ==========================================================================
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from tkcore import *

TOOL = "github"
CFG = CONF / "github.json"


def cfg():
    try:
        return json.loads(CFG.read_text())
    except Exception:
        return {}


def save(c_):
    CONF.mkdir(parents=True, exist_ok=True)
    CFG.write_text(json.dumps(c_)); os.chmod(str(CFG), 0o600)


def api(method, path, body=None):
    c_ = cfg()
    url = path if path.startswith("http") else "https://api.github.com" + path
    req = urllib.request.Request(url, method=method, data=json.dumps(body).encode() if body is not None else None,
                                 headers={"Authorization": "Bearer " + c_.get("token", ""), "Accept": "application/vnd.github+json", "User-Agent": "toolkit", "X-GitHub-Api-Version": "2022-11-28"})
    last = None
    for att in range(2):
        try:
            with _opener(ST.net("verify_tls")).open(req, timeout=ST.net("timeout")) as r:
                raw = r.read()
                return json.loads(raw) if raw else {}
        except urllib.error.HTTPError as e:
            msg = e.read().decode("utf-8", "replace")[:200]
            raise RuntimeError("HTTP %s: %s" % (e.code, msg))
        except Exception as e:
            last = e; dns_reset(); wait_network(5)
    raise RuntimeError(str(last))


def repo_path(p=""):
    c_ = cfg()
    return "/repos/%s/contents/%s" % (c_["repo"], quote(p.strip("/"))) + ("?ref=" + c_["branch"] if c_.get("branch") else "")


def raw_url(p):
    c_ = cfg()
    return "https://raw.githubusercontent.com/%s/refs/heads/%s/%s" % (c_["repo"], c_.get("branch", "main"), quote(p.strip("/")))


def put_file(p, data, msg):
    c_, sha = cfg(), None
    try:
        sha = api("GET", repo_path(p)).get("sha")
    except RuntimeError:
        pass
    body = {"message": msg, "content": base64.b64encode(data).decode(), "branch": c_.get("branch", "main")}
    if sha:
        body["sha"] = sha
    return api("PUT", "/repos/%s/contents/%s" % (c_["repo"], quote(p.strip("/"))), body)


def setup():
    c_ = cfg()
    c_["token"] = ask(L("Токен GitHub (PAT, repo scope)", "GitHub token (PAT, repo scope)"), c_.get("token", ""), quit_ok=False)
    c_["repo"] = ask(L("Репозиторий owner/name", "Repository owner/name"), c_.get("repo", "Krest-Neva/Shadowrocket"), quit_ok=False)
    c_["branch"] = ask(L("Ветка", "Branch"), c_.get("branch", "main"), quit_ok=False)
    save(c_)
    try:
        r = api("GET", "/repos/" + c_["repo"]); print("[+] %s (%s)" % (r.get("full_name"), L("доступ есть", "access ok")))
    except Exception as e:
        print("[!] %s" % e)


def browse():
    path = ask(L("Путь в репозитории", "Repo path"), ST.mem(TOOL, "path", ""), quit_ok=False).strip("/")
    while True:
        ST.setmem(TOOL, "path", path)
        try:
            items = api("GET", repo_path(path))
        except Exception as e:
            print("[!] %s" % e); return
        if isinstance(items, dict):
            items = [items]
        items.sort(key=lambda x: (x["type"] != "dir", x["name"].lower()))
        print(c("/" + path, accent(), True))
        for i, it in enumerate(items, 1):
            print("  %s %s %s %s" % (c("%2d" % i, accent(), True), c("D" if it["type"] == "dir" else "F", WARN_C if it["type"] == "dir" else INFO_C), trunc(it["name"], term_w() - 22), dim(fmt_size(it.get("size", 0)) if it["type"] == "file" else "")))
        v = ask(L("№ открыть | u вверх | d удалить | n новая папка | b назад", "# open | u up | d delete | n new folder | b back"), "", quit_ok=False).lower()
        if v in ("b", ""):
            return
        if v == "u":
            path = "/".join(path.split("/")[:-1])
        elif v.isdigit() and 1 <= int(v) <= len(items):
            it = items[int(v) - 1]
            if it["type"] == "dir":
                path = it["path"]
            else:
                file_menu(it)
        elif v == "d":
            n = ask(L("Номер файла", "File number"), "", quit_ok=False)
            if n.isdigit() and 1 <= int(n) <= len(items) and items[int(n) - 1]["type"] == "file" and confirm(L("Удалить файл в репозитории?", "Delete the file in the repo?")):
                it = items[int(n) - 1]
                api("DELETE", "/repos/%s/contents/%s" % (cfg()["repo"], quote(it["path"])), {"message": "delete " + it["name"], "sha": it["sha"], "branch": cfg().get("branch", "main")}); print("[+] OK")
        elif v == "n":
            nm = ask(L("Имя папки", "Folder name"), "", quit_ok=False)
            if nm:
                put_file((path + "/" + nm + "/.gitkeep").strip("/"), b"", "mkdir " + nm); print("[+] OK")


def file_menu(it):
    k = menu(it["name"], [("1", L("Просмотр", "View"), ""), ("2", L("Скачать в ListLab/Input для правки", "Download to ListLab/Input to edit"), ""), ("3", L("Raw-ссылка (скопировать)", "Raw link (copy)"), ""), ("4", L("Загрузить новую версию из файла", "Upload new version from file"), "")], show=False)
    if k == "1" or k == "2":
        d = fetch(raw_url(it["path"]), label=it["name"]) or base64.b64decode(api("GET", repo_path(it["path"]))["content"])
        if k == "1":
            for l_ in d.decode("utf-8", "replace").splitlines()[:60]:
                print(trunc(l_, term_w()))
        else:
            p = BASE / "ListLab" / "Input" / it["name"]; atomic_write(p, d, "wb"); print("[+] " + str(p))
    elif k == "3":
        u = raw_url(it["path"]); print(u); clip_copy(u)
    elif k == "4":
        fs = pick_files(BASE / "ListLab" / "Output", None, False, tool=TOOL)
        if fs:
            put_file(it["path"], fs[0].read_bytes(), ask(L("Сообщение коммита", "Commit message"), "update " + it["name"], quit_ok=False)); print("[+] OK")


def publish():
    srcs = {"1": BASE / "ListLab" / "Output", "2": BASE / "ScriptForge" / "Scripts", "3": BASE / "AdBlock", "4": BASE / "ConfigForge" / "Output", "5": BASE / "SubManager" / "Output"}
    k = menu(L("Откуда публиковать", "Publish from"), [("1", "ListLab/Output (rule-set)", ""), ("2", "ScriptForge/Scripts (.js)", ""), ("3", "AdBlock (.list)", ""), ("4", "ConfigForge/Output", ""), ("5", "SubManager/Output", "")], show=False)
    if k not in srcs:
        return
    fs = pick_files(srcs[k], None, True, tool=TOOL)
    if not fs:
        return
    dst = ask(L("Папка в репозитории", "Repo folder"), ST.mem(TOOL, "dst", "Rules"), quit_ok=False).strip("/")
    ST.setmem(TOOL, "dst", dst)
    msg = ask(L("Сообщение коммита", "Commit message"), "update via toolkit", quit_ok=False)
    urls = []
    for f in track(fs, label="upload"):
        try:
            put_file("%s/%s" % (dst, f.name), f.read_bytes(), msg); urls.append(raw_url("%s/%s" % (dst, f.name)))
        except Exception as e:
            print("[!] %s: %s" % (f.name, e))
    print("\n".join(urls))
    if urls and clip_copy("\n".join(urls)):
        print("[+] " + L("Ссылки скопированы", "Links copied"))


def main():
    while True:
        c_ = cfg()
        k = menu("GitHub", [("1", L("Настройка (токен, репозиторий)", "Setup (token, repo)"), c_.get("repo", "-")), ("2", L("Обзор репозитория", "Browse repository"), ""), ("3", L("Опубликовать файлы Toolkit", "Publish Toolkit files"), ""),
                             ("4", L("Последние коммиты", "Recent commits"), "")], tool=TOOL)
        if k == "q":
            return
        try:
            if k == "1": setup()
            elif not c_.get("token") or not c_.get("repo"):
                print("[!] " + L("Сначала настройка (пункт 1)", "Do the setup first (item 1)"))
            elif k == "2": browse()
            elif k == "3": publish()
            elif k == "4":
                for cm in api("GET", "/repos/%s/commits?per_page=10" % c_["repo"]):
                    print("  %s %s  %s" % (c(cm["sha"][:7], accent()), trunc(cm["commit"]["message"].splitlines()[0], term_w() - 14), dim(cm["commit"]["author"]["date"][:10])))
        except KeyboardInterrupt:
            print("\n[*] " + L("Отменено", "Cancelled"))
        except Exception as e:
            print("[!] %s" % e)
        pause()


if __name__ == "__main__":
    run_tool("GitHub", main)
TKEOF_ghapi

tk_put qr.py << 'TKEOF_qr'
# -*- coding: utf-8 -*-
# ==========================================================================
#  QR — QR-коды для подписок, ссылок импорта и текста (через qrencode; при отсутствии — установка).
# ==========================================================================
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from tkcore import *

TOOL = "qr"


def show_qr(text):
    q = shutil.which("qrencode")
    if not q:
        print("[!] " + L("qrencode не установлен. Меню «Среда» → «Установить опциональное», либо: apk add libqrencode-tools", "qrencode is not installed. 'Environment' menu → install optional, or: apk add libqrencode-tools"))
        return False
    r = subprocess.run([q, "-t", "ANSIUTF8", "-m", "1", text], capture_output=True, text=True)
    if r.returncode != 0:
        print("[!] " + (r.stderr or "qrencode error")[:120]); return False
    print(r.stdout)
    return True


def main():
    ensure_dirs("QR")
    while True:
        k = menu("QR", [("1", L("QR из текста / ссылки", "QR from text / link"), ""), ("2", L("QR ссылки импорта для клиента", "QR of a client import link"), ""), ("3", L("Сохранить QR как PNG", "Save QR as PNG"), "")], tool=TOOL)
        if k == "q":
            return
        if k == "1":
            t = ask(L("Текст/ссылка", "Text/link"), "", quit_ok=False)
            if t:
                if len(t) > 1200:
                    print("[!] " + L("Слишком длинно для QR (>1200 символов)", "Too long for a QR (>1200 chars)"))
                else:
                    show_qr(t)
        elif k == "2":
            import routing as RT
            names = list(RT.CLIENTS)
            for i, n in enumerate(names, 1):
                print("  %s %s" % (c("%2d" % i, accent(), True), n))
            n = ask(L("Клиент №", "Client #"), "", quit_ok=False)
            if n.isdigit() and 1 <= int(n) <= len(names):
                url = ask(L("URL подписки", "Subscription URL"), "", quit_ok=False)
                links = [l_ for kind in RT.CLIENTS[names[int(n) - 1]] for l_ in RT.client_links(names[int(n) - 1], kind, url, "", "toolkit")]
                for l_ in links[:2]:
                    print(c(l_, accent(), True)); show_qr(l_)
        elif k == "3":
            t = ask(L("Текст/ссылка", "Text/link"), "", quit_ok=False)
            if t and shutil.which("qrencode"):
                p = BASE / "QR" / ("qr_%s.png" % now_stamp())
                subprocess.run(["qrencode", "-o", str(p), "-s", "8", t]); print("[+] " + str(p))
            else:
                print("[!] qrencode?")
        pause()


if __name__ == "__main__":
    run_tool("QR", main)
TKEOF_qr

[ "$SKIP" = "1" ] || echo "$TK_BUILD" > "$CORE/.ver"
chmod 700 "$CORE"/*.py 2>/dev/null

# ==========================================================================
#  ЗАПУСК: геолокация (фон) → окружение → главный цикл с «действиями» меню
# ==========================================================================
printf '%b  ★ Toolkit  (%s)%b\n' "$C_AC" "$TK_ENV" "$C_RS"
loc_keepalive
cleanup() { [ -f "$CONF/loc.pid" ] && kill "$(cat "$CONF/loc.pid")" 2>/dev/null; rm -f "$CONF/loc.pid"; }
trap cleanup EXIT INT TERM

# DNS по умолчанию — только если файл пуст/отсутствует и есть права
if [ -w /etc/resolv.conf ] || [ ! -e /etc/resolv.conf ]; then
  grep -q nameserver /etc/resolv.conf 2>/dev/null || printf 'nameserver 1.1.1.1\nnameserver 8.8.8.8\nnameserver 94.140.14.14\nnameserver 9.9.9.9\n' > /etc/resolv.conf 2>/dev/null
fi

ensure_env

tries=0; crashes=0
while [ "$tries" -lt 14 ]; do
  tries=$((tries + 1))
  rm -f "$CONF/action"
  python3 "$CORE/launcher.py"; rc=$?
  act=""
  if [ -f "$CONF/action" ]; then act="$(cat "$CONF/action")"; rm -f "$CONF/action"; fi
  case "$act" in
    repair)       find_alpine; continue ;;
    alpine:*)     _v="${act#alpine:}"; run_spin "Alpine $_v" alpine_try "$_v" && say_ok "Alpine $_v" || say_er "Alpine $_v: $(T 'не удалось' 'failed')"; continue ;;
    pkgupdate)    update_pkgs; continue ;;
    optional)     case "$TK_ENV" in ish|alpine) run_spin "nodejs quickjs" apk add --no-cache nodejs quickjs ;; termux) run_spin nodejs pkg install -y nodejs ;; debian) run_spin nodejs apt-get install -y nodejs ;; esac; continue ;;
    rewrite)      if [ -f "$TK_SELF" ]; then TK_FORCE=1 exec sh "$TK_SELF"; else say_wn "$(T 'Перезапустите скрипт с TK_FORCE=1.' 'Re-run the script with TK_FORCE=1.')"; fi; continue ;;
    applyupdate)  apply_update; continue ;;
  esac
  if [ "$rc" -ge 128 ]; then
    crashes=$((crashes + 1))
    say_er "$(T "Python завершился аварийно (код $rc)." "Python crashed (code $rc).")"
    if [ "$crashes" -ge 3 ]; then say_er "$(T 'Слишком много сбоев — остановка. Меню «Среда» → ремонт.' 'Too many crashes — stopping.')"; exit "$rc"; fi
    find_alpine || true
    continue
  fi
  # штатный выход: запомнить текущую версию Alpine как стабильную
  is_apk && alp_cur > "$CONF/good_alpine" 2>/dev/null
  exit "$rc"
done
say_er "$(T 'Превышено число попыток.' 'Max retries reached.')"
exit 1
