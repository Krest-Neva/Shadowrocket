#!/bin/sh
# ==========================================================================
#  MediaForge — универсальный загрузчик/медиа-инструмент (iSH/Alpine, Termux, Debian, macOS)
#  Запуск:  sh MediaForge.sh
#  Оболочка: язык → фиктивная геолокация (3 с) → Alpine/Python 3.10+ → пакеты → pip-инструменты
#  → запуск встроенного Python-ядра. Ядро: загрузка видео/аудио/фото (yt-dlp, gallery-dl, прямые
#  ссылки, разбор страниц), очередь с автозагрузкой, конвертер, коллажи, метаданные, сеть, настройки.
# ==========================================================================
MF_BUILD="202610250001"
MF_UPDATE_URL=""

HOME="${HOME:-/root}"; export HOME
BASE="$HOME/MediaForge"; CONF="$BASE/.config"; CORE="$BASE/.core"
mkdir -p "$CONF" "$CORE" 2>/dev/null
case "$0" in /*) MF_SELF="$0" ;; *) MF_SELF="$(pwd)/$0" ;; esac
[ -f "$MF_SELF" ] && echo "$MF_SELF" > "$CONF/self_path"

if [ -t 1 ]; then
  C_OK='\033[38;5;84m'; C_ER='\033[38;5;203m'; C_WN='\033[38;5;220m'; C_IN='\033[38;5;51m'; C_AC='\033[38;5;45m'; C_RS='\033[0m'
else
  C_OK=''; C_ER=''; C_WN=''; C_IN=''; C_AC=''; C_RS=''
fi
say_ok() { printf '%b[+] %s%b\n' "$C_OK" "$*" "$C_RS"; }
say_er() { printf '%b[!] %s%b\n' "$C_ER" "$*" "$C_RS"; }
say_wn() { printf '%b[!] %s%b\n' "$C_WN" "$*" "$C_RS"; }
say_in() { printf '%b[*] %s%b\n' "$C_IN" "$*" "$C_RS"; }
T() { if [ "$MF_LANG" = "en" ]; then printf '%s' "$2"; else printf '%s' "$1"; fi; }

# ---------- 1. выбор языка (в самом начале) ----------
MF_LANG="ru"
if [ -f "$CONF/lang" ]; then
  MF_LANG="$(cat "$CONF/lang" 2>/dev/null)"; [ "$MF_LANG" = "en" ] || MF_LANG="ru"
elif [ -t 0 ]; then
  printf '%b========================================\n  Language / Язык\n========================================%b\n' "$C_WN" "$C_RS"
  printf '  1 - Русский [по умолчанию]\n  2 - English\nВыбор / Choice [1]: '
  IFS= read -r _lc
  [ "$_lc" = "2" ] && MF_LANG="en"
  echo "$MF_LANG" > "$CONF/lang"
fi

# ---------- 2. фиктивная геолокация (iSH в фоне), предупреждение за 3 секунды ----------
loc_keepalive() {
  [ -e /dev/location ] || { say_in "$(T '/dev/location не найден — геолокация не нужна.' '/dev/location not found — geolocation not needed.')"; return; }
  [ -f "$CONF/noloc" ] && { say_in "$(T 'Фоновая геолокация отключена в настройках.' 'Background location is disabled in settings.')"; return; }
  say_wn "$(T 'Через 3 секунды будет сделан фиктивный запрос геолокации (чтобы iSH не засыпал в фоне). Данные отбрасываются и никуда не отправляются.' 'A dummy geolocation request will be made in 3 seconds (keeps iSH alive in background). Data is discarded and never sent anywhere.')"
  _n=3
  while [ "$_n" -gt 0 ]; do printf '\r  %b%s%b ' "$C_WN" "$_n" "$C_RS"; sleep 1; _n=$((_n - 1)); done
  printf '\r\033[K'
  [ -f "$CONF/loc.pid" ] && kill "$(cat "$CONF/loc.pid")" 2>/dev/null
  ( cat /dev/location >/dev/null 2>&1 ) &
  echo $! > "$CONF/loc.pid"
  say_ok "$(T "Геолокация запрошена (PID $!)." "Geolocation requested (PID $!).")"
}
loc_keepalive

# ---------- среда ----------
detect_env() {
  _u="$(uname -a 2>/dev/null | tr 'A-Z' 'a-z')"
  case "$_u" in *darwin*) MF_ENV=macos; return ;; esac
  case "${PREFIX:-}" in *com.termux*) MF_ENV=termux; return ;; esac
  case "$_u" in *ish*) MF_ENV=ish; return ;; esac
  if [ -f /etc/alpine-release ]; then MF_ENV=alpine
  elif command -v apt-get >/dev/null 2>&1; then MF_ENV=debian
  else MF_ENV=linux; fi
}
detect_env
export MF_ENV MF_BUILD PYTHONUTF8=1 PYTHONIOENCODING=utf-8
is_apk() { case "$MF_ENV" in ish|alpine) command -v apk >/dev/null 2>&1 ;; *) return 1 ;; esac; }
stty erase '^?' 2>/dev/null

run_spin() {
  _msg="$1"; shift
  if [ ! -t 1 ]; then say_in "$_msg..."; "$@" >/tmp/mf_spin.log 2>&1; return $?; fi
  ( "$@" ) >/tmp/mf_spin.log 2>&1 &
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

fix_dns() {
  if [ -w /etc/resolv.conf ] || [ ! -e /etc/resolv.conf ]; then
    grep -q nameserver /etc/resolv.conf 2>/dev/null || printf 'nameserver 1.1.1.1\nnameserver 8.8.8.8\nnameserver 9.9.9.9\n' > /etc/resolv.conf 2>/dev/null
  fi
}

# ---------- Alpine: репозитории и подбор версии (нужен Python 3.10+) ----------
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
python_ok() {
  command -v python3 >/dev/null 2>&1 && python3 -c 'import sys; sys.exit(0 if sys.version_info >= (3,10) else 1)' >/dev/null 2>&1
}
alpine_try() {
  _v="$1"
  set_repos "$_v" || return 1
  [ "$(alp_cur)" = "$_v" ] || apk upgrade --available --no-cache >/dev/null 2>&1
  apk add --no-cache --upgrade python3 py3-pip curl ca-certificates >/dev/null 2>&1 || return 1
  python_ok
}
# -1 = Python упал (Bad system call), иначе число проваленных обязательных компонентов
score_env() {
  python_ok || { echo -1; return; }
  python3 "$CORE/mediaforge.py" --selftest >/tmp/mf_self.out 2>&1; _rc=$?
  [ "$_rc" -ge 128 ] && { echo -1; return; }
  _n="$(grep -c '^FAIL' /tmp/mf_self.out 2>/dev/null)"; echo "${_n:-0}"
}
find_alpine() {
  is_apk || return 1
  _good="$(cat "$CONF/good_alpine" 2>/dev/null)"
  _tried=" "; _n=0
  for _v in $_good 3.19 3.20 3.18 3.21 3.17; do
    [ -n "$_v" ] || continue
    case "$_tried" in *" $_v "*) continue ;; esac
    _tried="$_tried$_v "; _n=$((_n + 1)); [ "$_n" -gt 5 ] && break
    say_in "$(T "Пробую Alpine $_v ..." "Trying Alpine $_v ...")"
    run_spin "Alpine $_v" alpine_try "$_v" || { say_wn "Alpine $_v: $(T 'не подошла' 'failed')"; continue; }
    _sc="$(score_env)"
    if [ "$_sc" = "0" ]; then echo "$_v" > "$CONF/good_alpine"; say_ok "Alpine $_v + Python $(python3 -V 2>&1 | cut -d' ' -f2)"; return 0; fi
    [ "$_sc" = "-1" ] && say_wn "Alpine $_v: SIGSYS"
  done
  return 1
}

# ---------- пакеты ----------
install_packages() {
  case "$MF_ENV" in
    ish|alpine)
      for _p in ffmpeg nodejs exiftool imagemagick jpegoptim mediainfo; do
        apk info -e "$_p" >/dev/null 2>&1 || run_spin "apk add $_p" apk add --no-cache "$_p" || say_wn "$_p: $(T 'не установился (не критично)' 'not installed (non-critical)')"
      done ;;
    termux) run_spin "pkg" pkg install -y python ffmpeg nodejs exiftool imagemagick curl ;;
    debian) run_spin "apt" apt-get install -y python3 python3-pip ffmpeg nodejs libimage-exiftool-perl imagemagick curl ;;
    macos) run_spin "brew" brew install python ffmpeg node exiftool imagemagick ;;
  esac
}
pip_install() {
  python3 -m pip install -U --break-system-packages "$@" >/tmp/mf_pip.log 2>&1 && return 0
  python3 -m pip install -U "$@" >>/tmp/mf_pip.log 2>&1 && return 0
  sleep 2; fix_dns
  python3 -m pip install -U --break-system-packages "$@" >>/tmp/mf_pip.log 2>&1
}
ensure_pytools() {
  python3 -c 'import yt_dlp' >/dev/null 2>&1 || run_spin "pip yt-dlp" pip_install yt-dlp || say_er "yt-dlp: $(T 'не установился (см. /tmp/mf_pip.log)' 'failed (see /tmp/mf_pip.log)')"
  python3 -c 'import gallery_dl, requests, urllib3, certifi, idna, charset_normalizer' >/dev/null 2>&1 || run_spin "pip gallery-dl" pip_install gallery-dl requests urllib3 certifi idna charset-normalizer || say_wn "gallery-dl: $(T 'не установился' 'failed')"
  python3 -c 'import mutagen' >/dev/null 2>&1 || run_spin "pip mutagen" pip_install mutagen || true
  python3 -c 'import yt_dlp_ejs' >/dev/null 2>&1 || run_spin "pip yt-dlp-ejs" pip_install yt-dlp-ejs || true
}
tools_ok() {
  python_ok && python3 -c 'import yt_dlp, gallery_dl' >/dev/null 2>&1 && command -v ffmpeg >/dev/null 2>&1
}
ensure_env() {
  fix_dns
  if tools_ok && [ "$(score_env)" = "0" ]; then return 0; fi
  if ! python_ok; then
    say_wn "$(T 'Нужен Python 3.10+ (для yt-dlp). Обновляю репозитории Alpine...' 'Python 3.10+ is required (yt-dlp). Updating Alpine repositories...')"
    if is_apk; then find_alpine || true
    else
      case "$MF_ENV" in termux) pkg install -y python ;; debian) apt-get update && apt-get install -y python3 python3-pip ;; macos) brew install python ;; esac
    fi
  fi
  python_ok || { say_er "$(T 'Python 3.10+ недоступен. Установите вручную и запустите снова.' 'Python 3.10+ unavailable. Install it manually and re-run.')"; exit 1; }
  install_packages
  ensure_pytools
  if [ "$(score_env)" = "-1" ] && is_apk; then say_wn "$(T 'Окружение нестабильно — подбираю Alpine...' 'Environment unstable — picking Alpine...')"; find_alpine || true; fi
}
update_pkgs() {
  case "$MF_ENV" in
    ish|alpine) run_spin "apk update" apk update; run_spin "apk upgrade" apk upgrade ;;
    termux) run_spin "pkg upgrade" pkg upgrade -y ;;
    debian) run_spin "apt upgrade" sh -c 'apt-get update && apt-get upgrade -y' ;;
  esac
  say_ok "$(T 'Пакеты обновлены.' 'Packages updated.')"
}
apply_update() {
  _new="$CONF/MediaForge.new"
  if [ -f "$_new" ] && head -1 "$_new" | grep -q '^#!/bin/sh' && grep -q 'MF_BUILD=' "$_new"; then
    _dst="$MF_SELF"; [ -f "$_dst" ] || _dst="$HOME/MediaForge.sh"
    cp "$_new" "$_dst" && chmod 700 "$_dst" && rm -f "$_new" && echo "$_dst" > "$CONF/self_path"
    say_ok "$(T "Обновлено: $_dst — перезапуск..." "Updated: $_dst — restarting...")"
    exec sh "$_dst"
  fi
  say_er "$(T 'Файл обновления повреждён.' 'Update file is damaged.')"
}

# ==========================================================================
#  ВСТРОЕННОЕ PYTHON-ЯДРО
# ==========================================================================
if [ "${MF_FORCE:-0}" = "1" ] || [ ! -f "$CORE/mediaforge.py" ] || [ "$(cat "$CORE/.ver" 2>/dev/null)" != "$MF_BUILD" ]; then
cat > "$CORE/mediaforge.py" << 'PYEOF'
# -*- coding: utf-8 -*-
import os, sys, re, json, time, shutil, socket, ssl, random, subprocess, threading, hashlib, traceback, html, builtins
from pathlib import Path
import urllib.request, urllib.error
from urllib.parse import urlparse, urljoin, quote, unquote

# --- iSH: fork+exec наследует tty → SIGSYS. Всегда захватываем вывод и закрываем stdin ---
_orig_run = subprocess.run
def _safe_run(*a, **k):
    if not any(x in k for x in ("capture_output", "stdout", "stderr")):
        k["capture_output"] = True
    k.setdefault("stdin", subprocess.DEVNULL)
    return _orig_run(*a, **k)
subprocess.run = _safe_run

try:
    import readline
    HAVE_RL = True
except Exception:
    HAVE_RL = False

HOME = Path(os.environ.get("HOME") or "/root")
BASE = HOME / "MediaForge"
CONF, CORE = BASE / ".config", BASE / ".core"
DIRS = ("videos", "audio", "photos", "tmp", "reports", "cookies", "collages")
UA_IOS = "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1"
UA_DESK = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
os.umask(0o022)

# ==========================================================================
#  НАСТРОЙКИ (схема → автоматическое меню). (группа, ключ, умолч., тип, варианты, RU, EN)
# ==========================================================================
SCHEMA = [
 ("design", "theme", "ocean", "choice", ("ocean", "sunset", "neon", "matrix", "candy", "aurora", "fire", "mono"), "Цветовая тема", "Color theme"),
 ("design", "anim", True, "bool", None, "Анимации", "Animations"),
 ("design", "anim_speed", 100, "int", (30, 300), "Скорость анимации, %", "Animation speed, %"),
 ("design", "banner_anim", True, "bool", None, "Анимированный баннер и ракета", "Animated banner & rocket"),
 ("design", "spinner", "braille", "choice", ("braille", "dots", "line", "arc", "pulse", "bounce"), "Стиль спиннера", "Spinner style"),
 ("design", "bar_style", "smooth", "choice", ("smooth", "blocks", "bars", "dots", "arrows", "ascii"), "Стиль прогресс-бара", "Progress bar style"),
 ("design", "bar_width", 0, "int", (0, 60), "Длина бара (0 — авто)", "Bar width (0 = auto)"),
 ("design", "bar_gradient", True, "bool", None, "Градиент в баре", "Bar gradient"),
 ("design", "bar_speed", True, "bool", None, "Показывать скорость", "Show speed"),
 ("design", "bar_eta", True, "bool", None, "Показывать ETA", "Show ETA"),
 ("design", "unicode", True, "bool", None, "Юникод-символы (иначе ASCII)", "Unicode glyphs (else ASCII)"),
 ("design", "color", "256", "choice", ("256", "off"), "Цвет", "Color"),
 ("design", "clear", True, "bool", None, "Очищать экран между меню", "Clear screen between menus"),
 ("design", "max_width", 0, "int", (0, 200), "Макс. ширина текста (0 — авто)", "Max text width (0 = auto)"),
 ("design", "lang", "ru", "choice", ("ru", "en"), "Язык / Language", "Language / Язык"),
 ("download", "quality", "best", "choice", ("best", "2160", "1440", "1080", "720", "480", "360"), "Макс. качество видео (высота)", "Max video quality (height)"),
 ("download", "container", "mp4", "choice", ("mp4", "mkv", "webm"), "Контейнер видео", "Video container"),
 ("download", "prefer_h264", True, "bool", None, "Предпочитать H.264 (совместимость с iPhone)", "Prefer H.264 (iPhone compatible)"),
 ("download", "audio_format", "m4a", "choice", ("m4a", "mp3", "opus", "flac", "best"), "Формат аудио", "Audio format"),
 ("download", "audio_quality", "192", "choice", ("320", "256", "192", "128"), "Битрейт аудио (mp3/m4a), кбит/с", "Audio bitrate, kbps"),
 ("download", "subs", False, "bool", None, "Скачивать субтитры", "Download subtitles"),
 ("download", "sub_langs", "ru,en", "str", None, "Языки субтитров", "Subtitle languages"),
 ("download", "embed_thumb", True, "bool", None, "Встраивать обложку", "Embed thumbnail"),
 ("download", "embed_meta", True, "bool", None, "Встраивать метаданные и главы", "Embed metadata & chapters"),
 ("download", "info_json", False, "bool", None, "Сохранять .info.json", "Save .info.json"),
 ("download", "organize", "flat", "choice", ("flat", "site", "date", "uploader"), "Раскладка по папкам", "Folder layout"),
 ("download", "fname", "title_id", "choice", ("title_id", "title", "id", "date_title"), "Шаблон имени файла", "File name template"),
 ("download", "out_dir", "", "str", None, "Своя папка вывода (пусто — по умолчанию)", "Custom output folder (empty = default)"),
 ("download", "playlist_limit", 0, "int", (0, 500), "Лимит элементов плейлиста (0 — без)", "Playlist item limit (0 = none)"),
 ("download", "max_filesize_mb", 0, "int", (0, 100000), "Макс. размер файла, МБ (0 — без)", "Max file size, MB (0 = none)"),
 ("behavior", "ask_selection", "ask", "choice", ("ask", "all", "first"), "Если на странице несколько медиа: спросить / все / первое", "Several media on a page: ask / all / first"),
 ("behavior", "skip_history", True, "bool", None, "Пропускать уже скачанное", "Skip already downloaded"),
 ("behavior", "retry_rounds", 2, "int", (1, 10), "Кругов повтора для неудачных", "Retry rounds for failed"),
 ("behavior", "sleep_between", 2, "int", (0, 600), "Пауза между загрузками, с", "Pause between downloads, s"),
 ("behavior", "sleep_slow", 20, "int", (0, 300), "Доп. пауза для Instagram/TikTok/X, с", "Extra pause for Instagram/TikTok/X, s"),
 ("behavior", "tls_fallback", "ask", "choice", ("ask", "auto", "never"), "Ошибка TLS: спросить / без проверки / никогда", "TLS error: ask / insecure / never"),
 ("behavior", "min_free_mb", 300, "int", (0, 100000), "Остановка при свободном месте меньше, МБ", "Stop if free space below, MB"),
 ("behavior", "bell", True, "bool", None, "Сигнал по окончании", "Bell when finished"),
 ("network", "proxy", "", "str", None, "Прокси (http/socks5)", "Proxy (http/socks5)"),
 ("network", "dns_mode", "auto", "choice", ("auto", "system", "doh"), "DNS: авто / системный / DoH", "DNS: auto / system / DoH"),
 ("network", "doh_url", "https://1.1.1.1/dns-query", "str", None, "DoH-сервер", "DoH server"),
 ("network", "ip_version", "auto", "choice", ("auto", "ipv4", "ipv6"), "IP-версия", "IP version"),
 ("network", "cookies_file", "", "str", None, "Файл cookies (Netscape); иначе cookies/<домен>.txt", "Cookies file (Netscape); else cookies/<domain>.txt"),
 ("network", "socket_timeout", 30, "int", (5, 300), "Таймаут сокета, с", "Socket timeout, s"),
 ("network", "retries", 8, "int", (0, 30), "Повторы запросов", "Request retries"),
 ("network", "fragments", 4, "int", (1, 16), "Параллельные фрагменты", "Concurrent fragments"),
 ("network", "rate_limit", "", "str", None, "Лимит скорости (напр. 2M)", "Rate limit (e.g. 2M)"),
 ("network", "ua", "ios", "choice", ("ios", "desktop"), "User-Agent для страниц", "User-Agent for pages"),
 ("network", "extra_args", "", "str", None, "Доп. аргументы yt-dlp (для запуска как процесс)", "Extra yt-dlp args (process mode)"),
 ("network", "update_url", "", "str", None, "URL обновления скрипта", "Script update URL"),
]
GROUPS = [("design", "Оформление", "Design"), ("download", "Загрузка и качество", "Download & quality"), ("behavior", "Поведение и автозагрузка", "Behavior & auto-download"), ("network", "Сеть и cookies", "Network & cookies")]
SCH = {s[1]: s for s in SCHEMA}
PROXY_T = ["", "http://127.0.0.1:1082", "http://127.0.0.1:8080", "http://127.0.0.1:3128", "socks5://127.0.0.1:1080", "socks5h://127.0.0.1:1080", "socks5://127.0.0.1:10808", "socks5h://127.0.0.1:9050"]
SETTINGS_FILE = CONF / "settings.json"


class Store:
    def __init__(self):
        self.d = {}
        try:
            self.d = json.loads(SETTINGS_FILE.read_text("utf-8"))
        except Exception:
            self.d = {}
        if not isinstance(self.d, dict):
            self.d = {}
        if "lang" not in self.d:
            try:
                v = (CONF / "lang").read_text().strip()
                if v in ("ru", "en"):
                    self.d["lang"] = v
            except Exception:
                pass

    def g(self, k):
        s = SCH[k]
        v = self.d.get(k, s[2])
        if type(v) is not type(s[2]):
            return s[2]
        if s[3] == "choice" and v not in s[4]:
            return s[2]
        if s[3] == "int":
            return max(s[4][0], min(s[4][1], v))
        return v

    def set(self, k, v):
        self.d[k] = v
        try:
            CONF.mkdir(parents=True, exist_ok=True)
            t = SETTINGS_FILE.with_suffix(".tmp")
            t.write_text(json.dumps(self.d, ensure_ascii=False, indent=1), "utf-8")
            os.replace(str(t), str(SETTINGS_FILE))
        except Exception:
            pass

    def mem(self, k, d=None):
        return self.d.get("_mem", {}).get(k, d)

    def setmem(self, k, v):
        self.d.setdefault("_mem", {})[k] = v
        self.set("_mem_touch", time.time())


ST = Store()


def L(ru, en):
    return ru if ST.g("lang") == "ru" else en


# ==========================================================================
#  ОФОРМЛЕНИЕ: цвета, градиенты, рамки, спиннер, прогресс-бар
# ==========================================================================
RESET, BOLD, DIM = "\033[0m", "\033[1m", "\033[2m"
PALETTES = {"ocean": [27, 33, 39, 45, 51, 50, 49, 48, 84, 120], "sunset": [196, 202, 208, 214, 220, 226, 190, 154], "neon": [201, 165, 129, 93, 57, 27, 33, 39, 45, 51],
            "matrix": [22, 28, 34, 40, 46, 82, 118, 154, 190], "candy": [213, 207, 201, 165, 171, 177, 183, 189, 195], "aurora": [53, 90, 127, 164, 135, 99, 63, 33, 39, 49],
            "fire": [52, 88, 124, 160, 196, 202, 208, 214, 220], "mono": [244, 247, 250, 253, 255, 253, 250, 247]}
OK_C, ERR_C, WARN_C, INFO_C, ASK_C = 84, 203, 220, 51, 213
ANSI_RE = re.compile(r"\x1b(?:\[[0-9;?]*[ -/]*[@-~]|[@-Z\\-_])")


def cmode():
    return "off" if (not sys.stdout.isatty() or os.environ.get("NO_COLOR")) else ST.g("color")


def fg(n):
    return "" if cmode() == "off" else "\033[38;5;%dm" % n


def pal():
    return PALETTES.get(ST.g("theme"), PALETTES["ocean"])


def accent():
    p = pal()
    return p[len(p) // 2]


def c(t, n, b=False):
    return str(t) if cmode() == "off" else (BOLD if b else "") + fg(n) + str(t) + RESET


def dim(t):
    return str(t) if cmode() == "off" else DIM + str(t) + RESET


def bold(t):
    return str(t) if cmode() == "off" else BOLD + str(t) + RESET


def grad(text, shift=0, b=False):
    if cmode() == "off":
        return str(text)
    p, n, out = pal(), max(1, len(text) - 1), []
    for i, ch in enumerate(str(text)):
        if ch == " ":
            out.append(ch)
            continue
        out.append((BOLD if b else "") + fg(p[(int(round(i / n * (len(p) - 1))) + shift) % len(p)]) + ch)
    return "".join(out) + RESET


def vlen(s):
    n = 0
    for ch in ANSI_RE.sub("", str(s)):
        o = ord(ch)
        n += 2 if (o >= 0x1F000 or 0x2600 <= o <= 0x27BF and ch not in "✔✘✓✗✦✧★☆▶●○◆◇") else (0 if o in (0x200B, 0xFE0F) else 1)
    return n


def term_w(lo=30, hi=78):
    try:
        w = shutil.get_terminal_size((44, 24)).columns
    except Exception:
        w = 44
    r = max(lo, min(hi, w - 1))
    mw = ST.g("max_width")
    return max(lo, min(r, mw)) if mw else r


def U(a, b):
    return a if ST.g("unicode") else b


def clear_screen():
    if sys.stdout.isatty() and ST.g("clear"):
        sys.stdout.write("\033[2J\033[3J\033[H")
        sys.stdout.flush()


_OUT = threading.RLock()
_TAG = re.compile(r"^(\s*)(\[[+!*?x]\])(\s?)(.*)$", re.S)
_MENU = re.compile(r"^(\s*)(\d{1,3}|[a-zA-Z])(\s*[-.)]\s+)(.*)$")
_ERRW = re.compile(r"(ошибк|error|fail|не удалось|не найден|traceback|denied|refused)", re.I)


def paint_line(s):
    if cmode() == "off" or "\033" in s or not s.strip():
        return s
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


print = tprint


def box(lines, title=None, w=None):
    w = w or term_w()
    tl, tr, bl, br, h, v = U("╭", "+"), U("╮", "+"), U("╰", "+"), U("╯", "+"), U("─", "-"), U("│", "|")
    inner = w - 2
    top = h * inner
    if title:
        t = " " + title + " "
        top = h + t + h * max(0, inner - vlen(t) - 1)
    out = [grad(tl + top + tr, 0)]
    for x in lines:
        out.append(c(v, pal()[0]) + " " + x + " " * max(0, inner - vlen(x) - 1) + c(v, pal()[-1]))
    out.append(grad(bl + h * inner + br, 3))
    return "\n".join(out)


def hdr(title, sub=None):
    lines = [grad(U("✦ ", "* ") + str(title), 0, True)]
    if sub:
        lines.append(dim(str(sub)))
    print("\n" + box(lines))


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


def table(rows, heads=None):
    allr = ([heads] if heads else []) + rows
    if not allr:
        return
    cols = len(allr[0])
    widths = [max(vlen(r[i]) for r in allr) for i in range(cols)]
    mx = term_w()
    if sum(widths) + 2 * cols > mx:
        k = (mx - 2 * cols) / float(sum(widths))
        widths = [max(4, int(w * k)) for w in widths]
    def fmt(r, hd=False):
        s = "  ".join(trunc(x, widths[i]) + " " * (widths[i] - vlen(trunc(x, widths[i]))) for i, x in enumerate(r))
        return c(s, accent(), True) if hd else s
    if heads:
        print(fmt(heads, True))
        print(grad(U("─", "-") * min(mx, sum(widths) + 2 * cols)))
    for r in rows:
        print(fmt(r))


SPIN = {"braille": "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏", "dots": "⣾⣽⣻⢿⡿⣟⣯⣷", "line": "|/-\\", "arc": "◜◠◝◞◡◟", "pulse": "▏▎▍▌▋▊▉█▉▊▋▌▍▎", "bounce": "⠁⠂⠄⡀⢀⠠⠐⠈"}


class Spin:
    def __init__(self, msg, quiet=False):
        self.msg, self.t0, self._stop, self.th, self.quiet = msg, time.time(), False, None, quiet
        self.live = sys.stdout.isatty() and ST.g("anim")
        self.final = None
        self.ok = True

    def update(self, m):
        self.msg = m

    def _run(self):
        fr = SPIN.get(ST.g("spinner"), SPIN["braille"]) if ST.g("unicode") else "|/-\\"
        i, p = 0, pal()
        while not self._stop:
            line = "\r\033[K %s %s %s" % (c(fr[i % len(fr)], p[i % len(p)], True), trunc(self.msg, term_w() - 12), dim("%.0fs" % (time.time() - self.t0)))
            with _OUT:
                sys.stdout.write(line)
                sys.stdout.flush()
            i += 1
            time.sleep(0.08 / max(0.3, ST.g("anim_speed") / 100.0))

    def __enter__(self):
        if self.live:
            self.th = threading.Thread(target=self._run, daemon=True)
            self.th.start()
        elif not self.quiet:
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
        if not self.quiet and et is None:
            print("[+] %s %s" % (self.final or self.msg, dim("(%.1fs)" % (time.time() - self.t0))))
        return False


def spin(m, **k):
    return Spin(m, **k)


BAR_STYLES = {"blocks": ("█", "░"), "bars": ("▰", "▱"), "dots": ("●", "○"), "arrows": ("▶", "·"), "ascii": ("#", "-")}
PARTIAL = " ▏▎▍▌▋▊▉"


class Bar:
    def __init__(self, total=None, label="", unit=""):
        self.total, self.label, self.unit = total, label, unit
        self.cur, self.t0, self.last, self.speed, self.lc, self.lt = 0, time.time(), 0.0, 0.0, 0, time.time()
        self.live = sys.stdout.isatty() and ST.g("anim")
        self.nl, self.closed = -1, False

    def _f(self, v):
        return fmt_size(v) if self.unit == "B" else fmt_dur(v) if self.unit == "s" else "%d" % v

    def update(self, cur=None, add=None, total=None):
        if total is not None:
            self.total = total
        self.cur = cur if cur is not None else self.cur + (add or 0)
        now = time.time()
        if now - self.lt >= 0.25:
            inst = (self.cur - self.lc) / (now - self.lt)
            self.speed = inst if self.speed == 0 else self.speed * 0.6 + inst * 0.4
            self.lc, self.lt = self.cur, now
        if now - self.last >= 0.1 or (self.total and self.cur >= self.total):
            self.last = now
            self.render()

    def _cells(self, w, frac):
        st = ST.g("bar_style") if ST.g("unicode") else "ascii"
        p = pal()
        if self.total is None:
            pos = int((time.time() * 8) % (w * 2 - 2))
            pos = pos if pos < w else 2 * w - 2 - pos
            return "".join(c(U("█", "#"), p[(i * len(p)) // w]) if abs(i - pos) < 3 else dim(U("░", "-")) for i in range(w))
        if st == "smooth":
            full = int(frac * w)
            rem = int((frac * w - full) * 8)
            cells = ["█" if i < full else (PARTIAL[rem] if i == full and rem > 0 else "░") for i in range(w)]
        else:
            on, off = BAR_STYLES.get(st, BAR_STYLES["blocks"])
            full = int(round(frac * w))
            cells = [on if i < full else off for i in range(w)]
        out = []
        for i, ch in enumerate(cells):
            if ch in "░·▱○-":
                out.append(dim(ch))
            elif ST.g("bar_gradient"):
                out.append(c(ch, p[min(len(p) - 1, int(i / max(1, w - 1) * (len(p) - 1)))]))
            else:
                out.append(c(ch, accent()))
        return "".join(out)

    def render(self, final=False):
        frac = 1.0 if final else (min(1.0, self.cur / float(self.total)) if self.total else 0.0)
        parts = []
        if self.total:
            parts.append(c("%5.1f%%" % (frac * 100), accent(), True))
        parts.append("%s/%s" % (self._f(self.cur), self._f(self.total)) if self.total else self._f(self.cur))
        if ST.g("bar_speed") and self.unit == "B" and self.speed > 0:
            parts.append(c(fmt_size(self.speed) + "/s", INFO_C))
        if ST.g("bar_eta") and self.total and self.speed > 0 and not final and self.unit == "B":
            parts.append(dim("ETA " + fmt_dur((self.total - self.cur) / self.speed)))
        if final:
            parts.append(dim(fmt_dur(time.time() - self.t0)))
        lab = trunc(self.label, 12) + " " if self.label else ""
        while True:
            tail = " ".join(parts)
            avail = term_w(24, 100) - vlen(lab) - vlen(tail) - 4
            if avail >= 10 or len(parts) <= 1:
                break
            parts.pop(-2 if final and len(parts) > 2 else -1)
        w = ST.g("bar_width") or max(8, min(40, avail))
        w = max(6, min(w, max(6, avail)))
        line = "%s%s%s%s %s" % (lab, U("▕", "["), self._cells(w, frac), U("▏", "]"), tail)
        if self.live:
            with _OUT:
                sys.stdout.write("\r\033[K " + line)
                sys.stdout.flush()
        else:
            step = int(frac * 10)
            if step > self.nl or final:
                self.nl = step
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


def track(it, label=""):
    it = list(it)
    b = Bar(len(it), label)
    for i, x in enumerate(it, 1):
        yield x
        b.update(i)
    b.close()


# ==========================================================================
#  ВВОД И МЕНЮ
# ==========================================================================
class Quit(Exception):
    pass


def fix_tty():
    try:
        import termios
        a = termios.tcgetattr(sys.stdin.fileno())
        a[6][termios.VERASE] = b"\x7f"
        termios.tcsetattr(sys.stdin.fileno(), termios.TCSANOW, a)
    except Exception:
        pass
    if HAVE_RL:
        try:
            readline.parse_and_bind("set enable-bracketed-paste off")
        except Exception:
            pass


def clean_line(s):
    out = []
    for ch in ANSI_RE.sub("", s or ""):
        if ch in ("\x7f", "\x08"):
            if out:
                out.pop()
        elif ch in "\r\n":
            continue
        elif ch == "\t" or ord(ch) >= 32:
            out.append(ch)
    return "".join(out).strip()


def _rl(s):
    return re.sub(r"(\x1b\[[0-9;]*m)", "\x01\\1\x02", s) if HAVE_RL else s


def ask(label, default="", quit_ok=True, hint=None):
    d = (" " + dim("[%s]" % default)) if default not in ("", None) else ""
    prompt = "%s %s%s%s%s " % (c(U("❯", ">"), accent(), True), label, (" " + dim(hint)) if hint else "", d, c(":", accent()))
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


UNATT = [False]


def confirm(q, default=False):
    if UNATT[0]:
        return default
    return ask("%s %s" % (q, dim("(y/n)")), "y" if default else "n", quit_ok=False).lower() in ("y", "yes", "д", "да", "1")


def pause(msg=None):
    try:
        input(_rl(dim(msg or L("Enter — продолжить...", "Press Enter..."))) + " ")
    except (EOFError, KeyboardInterrupt):
        print()


def parse_multi(text, n):
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
            if 1 <= int(part) <= n and int(part) not in res:
                res.append(int(part))
    if not res:
        raise ValueError(text)
    return res


def ask_multi(label, n, default=""):
    while True:
        v = ask(label, default, hint="1,3-5 / all / b")
        if v.lower() in ("b", "back"):
            return None
        try:
            return parse_multi(v, n)
        except ValueError:
            print("[!] " + L("Неверный ввод. Пример: 1,3-5 или all", "Bad input. Example: 1,3-5 or all"))


def menu(title, items, sub=None, back=None, show=True):
    if show:
        clear_screen()
        hdr(title, sub)
    for k, lab, desc in items:
        if k == "--":
            print("\n " + c(U("━━ ", "-- ") + lab + " " + U("━" * max(2, term_w() - vlen(lab) - 8), "-" * 6), accent(), True))
            continue
        row = " %s %s %s" % (c("%2s" % k, accent(), True), c(U("┃", "|"), pal()[0]), bold(lab))
        if desc:
            row += "  " + dim(trunc(desc, max(8, term_w() - vlen(lab) - 9)))
        print(row)
    print(" %s %s %s" % (c(" q", ERR_C, True), c(U("┃", "|"), pal()[0]), dim(back or L("Назад / выход", "Back / exit"))))
    keys = [str(k).lower() for k, _, _ in items if k != "--"]
    while True:
        try:
            v = ask(L("Выбор", "Choice"), "", quit_ok=False).lower()
        except Quit:
            return "q"
        if v in ("q", "quit", "exit", "b", "back"):
            return "q"
        if v in keys:
            return v
        print("[!] " + L("Неверный выбор", "Invalid choice"))


def pick_one(title, options, current=None):
    print("\n" + c(title, accent(), True))
    for i, o in enumerate(options, 1):
        print("  %s %s%s" % (c("%2d" % i, accent(), True), o if o != "" else dim(L("(пусто)", "(empty)")), c(" ◄", OK_C) if o == current else ""))
    v = ask(L("Номер", "Number"), "", quit_ok=False)
    return options[int(v) - 1] if v.isdigit() and 1 <= int(v) <= len(options) else None


# ==========================================================================
#  СЕТЬ: DNS (system/DoH), прокси, HTTP, TLS-политика
# ==========================================================================
_orig_gai = socket.getaddrinfo
_tl = threading.local()
DNS_CACHE = {}
INSECURE = set()


def is_ip(h):
    for fam in (socket.AF_INET, socket.AF_INET6):
        try:
            socket.inet_pton(fam, h)
            return True
        except (OSError, ValueError):
            pass
    return False


def doh_resolve(host):
    ips = []
    for qt in ("A", "AAAA") if ST.g("ip_version") == "auto" else (("A",) if ST.g("ip_version") == "ipv4" else ("AAAA",)):
        try:
            req = urllib.request.Request("%s?name=%s&type=%s" % (ST.g("doh_url"), host, qt), headers={"accept": "application/dns-json", "user-agent": UA_DESK})
            op = urllib.request.build_opener(urllib.request.ProxyHandler({}), urllib.request.HTTPSHandler(context=ssl.create_default_context()))
            with op.open(req, timeout=8) as r:
                d = json.loads(r.read().decode("utf-8", "replace"))
            ips += [a["data"] for a in d.get("Answer", []) if a.get("type") in (1, 28)]
        except Exception:
            pass
    return list(dict.fromkeys(ips))


def patched_gai(host, port, family=0, type=0, proto=0, flags=0):
    mode = ST.g("dns_mode")
    if mode == "system" or not isinstance(host, str) or not host or host == "localhost" or is_ip(host) or getattr(_tl, "busy", False):
        return _orig_gai(host, port, family, type, proto, flags)
    if mode == "auto":
        try:
            r = _orig_gai(host, port, family, type, proto, flags)
            if r:
                return r
        except OSError:
            pass
    v = DNS_CACHE.get(host)
    ips = v[0] if v and time.time() - v[1] < 120 else None
    if not ips:
        _tl.busy = True
        try:
            ips = doh_resolve(host)
        finally:
            _tl.busy = False
        if ips:
            DNS_CACHE[host] = (ips, time.time())
    if not ips:
        raise socket.gaierror(socket.EAI_NONAME, "Name does not resolve")
    p = int(port) if port and str(port).isdigit() else 0
    return [(socket.AF_INET6 if ":" in ip else socket.AF_INET, type or socket.SOCK_STREAM, proto or 0, "", (ip, p)) for ip in ips]


socket.getaddrinfo = patched_gai


def ua():
    return UA_IOS if ST.g("ua") == "ios" else UA_DESK


def tls_policy(host):
    if host in INSECURE:
        return True
    pol = ST.g("tls_fallback")
    if pol == "auto" or (pol == "ask" and not UNATT[0] and confirm(L("Ошибка TLS-сертификата для %s. Продолжить БЕЗ проверки?" % host, "TLS certificate error for %s. Continue WITHOUT verification?" % host))):
        INSECURE.add(host)
        print("[!] " + L("Проверка TLS отключена для ", "TLS verification disabled for ") + host)
        return True
    return False


def opener(verify=True):
    p = ST.g("proxy").strip()
    hs = [urllib.request.ProxyHandler({"http": p, "https": p} if p and not p.lower().startswith("socks") else {})]
    hs.append(urllib.request.HTTPSHandler(context=ssl.create_default_context() if verify else ssl._create_unverified_context()))
    return urllib.request.build_opener(*hs)


def http_get(url, headers=None, timeout=None, retries=2):
    timeout = timeout or ST.g("socket_timeout")
    host = urlparse(url).hostname or ""
    hd = dict({"User-Agent": ua(), "Accept": "*/*", "Accept-Language": "en-US,en;q=0.8,ru;q=0.6"}, **(headers or {}))
    last = None
    for att in range(retries + 1):
        try:
            if ST.g("proxy").lower().startswith("socks") and shutil.which("curl"):
                r = subprocess.run(["curl", "-sSL", "--fail", "--max-time", str(timeout), "-x", ST.g("proxy"), "-A", hd["User-Agent"]] + ([] if host not in INSECURE else ["-k"]) + [url], timeout=timeout + 5)
                if r.returncode == 0:
                    return r.stdout
                raise IOError(r.stderr.decode("utf-8", "replace")[:150])
            with opener(host not in INSECURE).open(urllib.request.Request(url, headers=hd), timeout=timeout) as r:
                return r.read()
        except Exception as e:
            last = e
            if "CERTIFICATE" in str(e).upper() and host not in INSECURE:
                if tls_policy(host):
                    continue
                break
            if isinstance(e, urllib.error.HTTPError) and e.code in (401, 403, 404, 410):
                break
            DNS_CACHE.pop(host, None)
            time.sleep(1 + att)
    raise IOError(str(last))


# ==========================================================================
#  ПУТИ, ИСТОРИЯ, ОЧЕРЕДЬ
# ==========================================================================
def ensure_dirs():
    for d in DIRS:
        (BASE / d).mkdir(parents=True, exist_ok=True)
    CONF.mkdir(parents=True, exist_ok=True)


def outdir(kind):
    root = Path(ST.g("out_dir")).expanduser() if ST.g("out_dir") else BASE
    d = root / {"video": "videos", "audio": "audio", "photo": "photos"}.get(kind, "videos")
    d.mkdir(parents=True, exist_ok=True)
    return d


def jload(p, default):
    try:
        return json.loads(Path(p).read_text("utf-8"))
    except Exception:
        return default


def jsave(p, data):
    try:
        t = Path(p).with_suffix(".tmp")
        t.write_text(json.dumps(data, ensure_ascii=False, indent=1), "utf-8")
        os.replace(str(t), str(p))
    except Exception:
        pass


HIST, QUEUE = CONF / "history.json", CONF / "queue.json"


def hist_done(url):
    e = jload(HIST, {}).get(url)
    return bool(e and e.get("status") == "ok" and e.get("path") and Path(e["path"]).exists())


def hist_add(url, title, path, status):
    h = jload(HIST, {})
    h[url] = {"title": title, "path": str(path or ""), "status": status, "ts": time.strftime("%Y-%m-%d %H:%M")}
    jsave(HIST, h)


def sanitize(name):
    s = re.sub(r"[^\w.\-]", "_", clean_line(name), flags=re.U).strip("._")
    return s or "file"


def uniq(p):
    p = Path(p)
    if not p.exists():
        return p
    for i in range(1, 1000):
        q = p.with_name("%s_%d%s" % (p.stem, i, p.suffix))
        if not q.exists():
            return q
    return p


def cookies_for(host):
    f = ST.g("cookies_file")
    if f and Path(f).expanduser().exists():
        return str(Path(f).expanduser())
    h = host.lower().split(":")[0]
    parts = h.split(".")
    for i in range(len(parts) - 1):
        p = BASE / "cookies" / (".".join(parts[i:]) + ".txt")
        if p.exists():
            return str(p)
    return None


def list_files(d, exts=None):
    out = []
    try:
        for e in os.scandir(str(d)):
            if e.is_file() and not e.name.startswith(".") and not e.name.endswith(".part") and (not exts or Path(e.name).suffix.lower() in exts):
                out.append(Path(e.path))
    except OSError:
        pass
    return sorted(out, key=lambda p: p.name.lower())


def pick_files(d, exts=None, multi=True, title=None):
    d = Path(d)
    d.mkdir(parents=True, exist_ok=True)
    while True:
        fs = list_files(d, exts)
        if not fs:
            print("[!] " + L("Папка пуста: ", "Folder is empty: ") + str(d))
            return None
        print("\n" + c(title or L("Файлы", "Files"), accent(), True) + dim("  " + str(d)))
        for i, f in enumerate(fs, 1):
            try:
                inf = "%s  %s" % (fmt_size(f.stat().st_size), time.strftime("%m-%d %H:%M", time.localtime(f.stat().st_mtime)))
            except OSError:
                inf = "?"
            print("  %s %s  %s" % (c("%2d" % i, accent(), True), trunc(f.name, term_w() - 28), dim(inf)))
        v = ask(L("Номера", "Numbers") if multi else L("Номер", "Number"), "", hint="1,3-5 / all / b")
        if v.lower() in ("b", "back", ""):
            return None
        try:
            nums = parse_multi(v, len(fs))
        except ValueError:
            continue
        return [fs[i - 1] for i in (nums if multi else nums[:1])]


# ==========================================================================
#  МЕДИА: типы, поиск медиа на страницах, прямое скачивание
# ==========================================================================
VEXT = {".mp4", ".mkv", ".webm", ".mov", ".m4v", ".avi", ".flv", ".ts", ".m3u8"}
AEXT = {".mp3", ".m4a", ".aac", ".opus", ".ogg", ".flac", ".wav"}
IEXT = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".bmp", ".heic", ".avif"}
ICON = {"video": "🎬", "audio": "🎵", "photo": "🖼"}
CT_EXT = {"image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".webp", "image/gif": ".gif", "video/mp4": ".mp4", "video/webm": ".webm", "audio/mpeg": ".mp3", "audio/mp4": ".m4a", "audio/ogg": ".ogg"}
SLOW_HOSTS = ("instagram.com", "tiktok.com", "twitter.com", "x.com", "facebook.com")


def ext_of(u):
    return Path(urlparse(u).path).suffix.lower()


def type_of_ext(e):
    return "video" if e in VEXT else "audio" if e in AEXT else "photo" if e in IEXT else None


def scrape_media(url, html_text=None):
    """Найти медиа на странице: og/twitter-теги, <video>/<audio>/<source>, <img>, ссылки, JSON-LD, embed Instagram."""
    if html_text is None:
        html_text = http_get(url, {"Referer": url}).decode("utf-8", "replace")
    t = html_text.replace("\\/", "/").replace("\\u0026", "&").replace("&amp;", "&")
    items, seen = [], set()

    def add(u, typ, title=""):
        u = urljoin(url, html.unescape(u.strip()))
        if not u.startswith("http") or u in seen or re.search(r"(sprite|favicon|pixel|blank|1x1|logo|\.svg)", u, re.I):
            return
        seen.add(u)
        items.append({"type": typ, "url": u, "title": title or (unquote(Path(urlparse(u).path).name) or u[-40:])})

    for m in re.finditer(r'<meta[^>]+?(?:property|name)=["\']([\w:]+)["\'][^>]*?content=["\']([^"\']+)', t, re.I):
        k, v = m.group(1).lower(), m.group(2)
        if k.startswith(("og:video", "twitter:player:stream")):
            add(v, "video")
        elif k.startswith("og:audio"):
            add(v, "audio")
        elif k in ("og:image", "og:image:url", "og:image:secure_url", "twitter:image"):
            add(v, "photo")
    for m in re.finditer(r'<meta[^>]+?content=["\']([^"\']+)["\'][^>]*?(?:property|name)=["\']([\w:]+)', t, re.I):
        k = m.group(2).lower()
        if k.startswith("og:video"):
            add(m.group(1), "video")
        elif k in ("og:image", "twitter:image"):
            add(m.group(1), "photo")
    for m in re.finditer(r'<(video|audio|source)\b[^>]*?\bsrc=["\']([^"\']+)', t, re.I):
        e = ext_of(m.group(2))
        add(m.group(2), type_of_ext(e) or ("audio" if m.group(1).lower() == "audio" else "video"))
    for m in re.finditer(r'<img\b[^>]*?\b(?:data-src|data-original|data-lazy-src|src)=["\']([^"\']+)', t, re.I):
        u = m.group(1)
        if not u.startswith("data:") and (ext_of(u) in IEXT or re.search(r"(image|photo|img|media|cdn)", u, re.I)):
            add(u, "photo")
    for m in re.finditer(r'href=["\']([^"\']+)["\']', t, re.I):
        e = ext_of(m.group(1).split("?")[0])
        if type_of_ext(e):
            add(m.group(1), type_of_ext(e))
    for m in re.finditer(r'https?://[^\s"\'<>\\]+?\.(?:m3u8|mp4|webm|mp3|m4a)(?:\?[^\s"\'<>\\]*)?', t, re.I):
        add(m.group(0), type_of_ext(ext_of(m.group(0).split("?")[0])) or "video")
    for m in re.finditer(r'"(?:contentUrl|video_url|display_url)"\s*:\s*"([^"]+)"', t):
        add(m.group(1), "video" if "video" in m.group(0) or ext_of(m.group(1).split("?")[0]) in VEXT else "photo")
    return items


def wayback_url(url):
    try:
        d = json.loads(http_get("https://archive.org/wayback/available?url=" + quote(url, safe=""), retries=1).decode())
        return d.get("archived_snapshots", {}).get("closest", {}).get("url")
    except Exception:
        return None


def dl_direct(url, dest_dir, referer=None, label=""):
    """Прямое скачивание с докачкой (.part), прогресс-баром, TLS-политикой. Возвращает Path."""
    p = urlparse(url)
    hd = {"User-Agent": ua(), "Referer": referer or "%s://%s/" % (p.scheme, p.netloc), "Accept": "*/*"}
    name = sanitize(unquote(Path(p.path).name)) or "file"
    dest_dir = Path(dest_dir)
    dest_dir.mkdir(parents=True, exist_ok=True)
    part = dest_dir / (name + ".part")
    host = p.hostname or ""
    for attempt in range(ST.g("retries") // 2 + 2):
        have = part.stat().st_size if part.exists() else 0
        h2 = dict(hd)
        if have:
            h2["Range"] = "bytes=%d-" % have
        try:
            with opener(host not in INSECURE).open(urllib.request.Request(url, headers=h2), timeout=ST.g("socket_timeout")) as r:
                if have and r.status != 206:
                    have = 0
                    part.unlink()
                cl = int(r.headers.get("Content-Length") or 0)
                total = cl + have if cl else None
                cdn = re.search(r'filename\*?=(?:UTF-8\'\')?"?([^";]+)', r.headers.get("Content-Disposition", ""))
                if cdn:
                    name = sanitize(unquote(cdn.group(1)))
                if not Path(name).suffix:
                    name += CT_EXT.get((r.headers.get("Content-Type") or "").split(";")[0].strip(), "")
                bar = Bar(total, label or trunc(name, 12), "B")
                bar.cur = have
                with open(str(part), "ab" if have else "wb") as f:
                    while True:
                        ch = r.read(65536)
                        if not ch:
                            break
                        f.write(ch)
                        bar.update(bar.cur + len(ch))
                bar.close()
            final = uniq(dest_dir / name)
            os.replace(str(part), str(final))
            return final
        except urllib.error.HTTPError as e:
            if e.code == 416 and part.exists():
                final = uniq(dest_dir / name)
                os.replace(str(part), str(final))
                return final
            if e.code in (401, 403, 404, 410):
                raise IOError("HTTP %d" % e.code)
            time.sleep(1 + attempt)
        except Exception as e:
            if "CERTIFICATE" in str(e).upper() and host not in INSECURE and tls_policy(host):
                continue
            DNS_CACHE.pop(host, None)
            time.sleep(1 + attempt)
    raise IOError(L("не удалось скачать", "download failed"))


def probe_duration(path):
    if not shutil.which("ffprobe"):
        return None
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=nw=1:nk=1", str(path)], timeout=60)
    try:
        return float(r.stdout.decode().strip())
    except Exception:
        return None


def ff_run(args, label="ffmpeg", duration=None):
    ff = shutil.which("ffmpeg")
    if not ff:
        print("[!] ffmpeg " + L("не установлен", "is not installed"))
        return 1
    cmd = [ff, "-y", "-hide_banner", "-nostats", "-loglevel", "error", "-progress", "pipe:1"] + [str(a) for a in args]
    p = subprocess.Popen(cmd, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    err = []
    th = threading.Thread(target=lambda: err.append(p.stderr.read()), daemon=True)
    th.start()
    bar = Bar(duration, label, "s")
    try:
        for line in p.stdout:
            if line.startswith("out_time_ms="):
                try:
                    bar.update(int(line.split("=")[1]) / 1e6)
                except ValueError:
                    pass
        p.wait()
    except KeyboardInterrupt:
        p.kill()
        bar.close(False)
        raise
    th.join(2)
    bar.close(p.returncode == 0)
    if p.returncode != 0:
        print("[!] " + trunc((err[0] if err else "").strip().splitlines()[-1] if err and err[0].strip() else "ffmpeg error", term_w() - 6))
    return p.returncode


def hls_download(url, kind, referer=None):
    d = outdir(kind)
    out = uniq(d / (sanitize(Path(urlparse(url).path).stem or "stream") + (".m4a" if kind == "audio" else ".mp4")))
    hd = "User-Agent: %s\r\nReferer: %s\r\n" % (ua(), referer or url)
    args = ["-headers", hd, "-i", url] + (["-vn", "-c:a", "copy"] if kind == "audio" else ["-c", "copy", "-bsf:a", "aac_adtstoasc"]) + [str(out)]
    if ff_run(args, "hls") == 0 and out.exists():
        return out
    raise IOError("ffmpeg/hls failed")


# ==========================================================================
#  yt-dlp: опции, цепочка fallback, процесс-режим
# ==========================================================================
YT_CLIENTS = ["tv", "android_vr", "web_safari", "mweb", "ios", "android"]
FATAL = ("private video", "video unavailable", "been removed", "copyright", "not available in your country", "members-only", "this video is not available", "account has been terminated", "age", "sign in to confirm")


class QLog:
    def debug(self, m): pass
    def info(self, m): pass
    def warning(self, m): pass
    def error(self, m): pass


def have_ffmpeg():
    return bool(shutil.which("ffmpeg"))


def outtmpl(kind):
    d = outdir(kind)
    sub = {"flat": "", "site": "%(extractor_key)s/", "date": "%(upload_date>%Y-%m)s/", "uploader": "%(uploader|unknown).60B/"}[ST.g("organize")]
    nm = {"title_id": "%(title).150B [%(id)s]", "title": "%(title).180B", "id": "%(id)s", "date_title": "%(upload_date)s - %(title).150B"}[ST.g("fname")]
    return str(d / (sub + nm + ".%(ext)s"))


def vformat(q=None):
    q = q or ST.g("quality")
    h = "" if q == "best" else "[height<=%s]" % q
    c_ = []
    if ST.g("prefer_h264"):
        c_.append("bv*%s[vcodec^=avc1]+ba[ext=m4a]" % h)
    c_ += ["bv*%s+ba" % h, "b%s" % h, "bv*+ba", "b", "w"]
    return "/".join(c_)


def aformat():
    return "ba[ext=m4a]/ba/b" if ST.g("audio_format") in ("m4a", "best") else "ba/b"


def ydl_opts(kind, client=None, generic=False, q=None):
    o = {"quiet": True, "no_warnings": True, "noprogress": True, "logger": QLog(), "socket_timeout": ST.g("socket_timeout"), "retries": ST.g("retries"),
         "fragment_retries": ST.g("retries"), "concurrent_fragment_downloads": ST.g("fragments"), "continuedl": True, "noplaylist": True,
         "outtmpl": outtmpl(kind), "windowsfilenames": True, "http_headers": {"User-Agent": ua()}, "overwrites": False, "trim_file_name": 200}
    if ST.g("proxy"):
        o["proxy"] = ST.g("proxy")
    if ST.g("ip_version") != "auto":
        o["source_address"] = "0.0.0.0" if ST.g("ip_version") == "ipv4" else "::"
    if ST.g("rate_limit"):
        try:
            import yt_dlp.utils as yu
            o["ratelimit"] = yu.parse_bytes(ST.g("rate_limit"))
        except Exception:
            pass
    if ST.g("max_filesize_mb"):
        o["max_filesize"] = ST.g("max_filesize_mb") * 1048576
    if client:
        o["extractor_args"] = {"youtube": {"player_client": [client]}}
    if generic:
        o["allowed_extractors"] = ["generic"]
    if shutil.which("node") or shutil.which("qjs"):
        o["js_runtimes"] = {"node": {}} if shutil.which("node") else {"quickjs": {}}
    pp = []
    ff = have_ffmpeg()
    if kind == "audio":
        o["format"] = aformat()
        af = ST.g("audio_format")
        if ff and af != "best":
            pp.append({"key": "FFmpegExtractAudio", "preferredcodec": af, "preferredquality": ST.g("audio_quality") if af in ("mp3", "m4a") else None})
    else:
        o["format"] = vformat(q)
        o["merge_output_format"] = ST.g("container") if ST.g("container") != "webm" else "webm"
        if ST.g("subs"):
            o.update(writesubtitles=True, writeautomaticsub=True, subtitleslangs=[x.strip() for x in ST.g("sub_langs").split(",") if x.strip()])
            if ff and ST.g("container") in ("mp4", "mkv"):
                pp.append({"key": "FFmpegEmbedSubtitle"})
    if ff and ST.g("embed_meta"):
        pp.append({"key": "FFmpegMetadata", "add_metadata": True, "add_chapters": True})
    if ff and ST.g("embed_thumb") and not (kind == "audio" and ST.g("audio_format") in ("opus", "flac", "best")):
        o["writethumbnail"] = True
        pp.insert(0, {"key": "FFmpegThumbnailsConvertor", "format": "jpg", "when": "before_dl"})
        pp.append({"key": "EmbedThumbnail"})
    if ST.g("info_json"):
        o["writeinfojson"] = True
    o["postprocessors"] = pp
    ck = cookies_for(urlparse(o.get("_url", "")).netloc) if False else None
    return o


def run_api(url, o):
    import yt_dlp
    host = urlparse(url).netloc
    ck = cookies_for(host)
    if ck:
        o["cookiefile"] = ck
    if (urlparse(url).hostname or "") in INSECURE:
        o["nocheckcertificate"] = True
    bar = [None]

    def hook(d):
        if d.get("status") == "downloading":
            tot = d.get("total_bytes") or d.get("total_bytes_estimate")
            if bar[0] is None:
                bar[0] = Bar(tot, "dl", "B")
            if tot:
                bar[0].total = tot
            bar[0].update(d.get("downloaded_bytes") or 0)
        elif d.get("status") == "finished" and bar[0]:
            bar[0].close()
            bar[0] = None
    o["progress_hooks"] = [hook]
    try:
        with yt_dlp.YoutubeDL(o) as y:
            info = y.extract_info(url, download=True)
            if info and info.get("entries"):
                info = [e for e in info["entries"] if e][0]
            rd = (info or {}).get("requested_downloads") or []
            path = rd[0].get("filepath") if rd else y.prepare_filename(info)
        if bar[0]:
            bar[0].close()
        return True, path
    except Exception as e:
        if bar[0]:
            bar[0].close(False)
        return False, ANSI_RE.sub("", str(e)).strip()[:300]


def run_bin(url, kind, client=None, generic=False, impersonate=False):
    cmd = [sys.executable, "-m", "yt_dlp", "--no-playlist", "--newline", "--no-warnings", "-o", outtmpl(kind), "--print", "after_move:filepath", "--no-simulate",
           "--retries", str(ST.g("retries")), "--socket-timeout", str(ST.g("socket_timeout")), "-N", str(ST.g("fragments")), "--user-agent", ua()]
    if kind == "audio":
        cmd += ["-f", aformat()]
        if have_ffmpeg() and ST.g("audio_format") != "best":
            cmd += ["-x", "--audio-format", ST.g("audio_format"), "--audio-quality", ST.g("audio_quality") + "K"]
    else:
        cmd += ["-f", vformat(), "--merge-output-format", ST.g("container")]
    if have_ffmpeg() and ST.g("embed_meta"):
        cmd += ["--embed-metadata", "--embed-chapters"]
    if ST.g("proxy"):
        cmd += ["--proxy", ST.g("proxy")]
    ck = cookies_for(urlparse(url).netloc)
    if ck:
        cmd += ["--cookies", ck]
    if client:
        cmd += ["--extractor-args", "youtube:player_client=" + client]
    if generic:
        cmd += ["--use-extractors", "generic"]
    if impersonate:
        cmd += ["--impersonate", "chrome"]
    if (urlparse(url).hostname or "") in INSECURE:
        cmd.append("--no-check-certificate")
    if ST.g("extra_args"):
        cmd += ST.g("extra_args").split()
    with Spin(L("yt-dlp (процесс)", "yt-dlp (process)"), quiet=True):
        r = subprocess.run(cmd + [url], timeout=3 * 3600)
    out = r.stdout.decode("utf-8", "replace").strip().splitlines()
    if r.returncode == 0 and out:
        return True, out[-1]
    return False, ANSI_RE.sub("", r.stderr.decode("utf-8", "replace")).strip().splitlines()[-1][:300] if r.stderr.strip() else "exit %d" % r.returncode


def has_impersonate():
    try:
        import curl_cffi  # noqa
        return True
    except Exception:
        return False


def ytdlp_chain(url, kind, q=None):
    host = (urlparse(url).hostname or "").lower()
    yt = "youtube.com" in host or "youtu.be" in host
    steps = [("api", cl) for cl in ([None] + (YT_CLIENTS if yt else []))] + [("bin", None), ("gen", None)]
    if has_impersonate():
        steps.append(("imp", None))
    last, tried_tls, i = "", False, 0
    while i < len(steps):
        st, cl = steps[i]
        i += 1
        try:
            if st == "api":
                ok, res = run_api(url, ydl_opts(kind, cl, q=q))
            elif st == "gen":
                ok, res = run_api(url, ydl_opts(kind, None, True, q=q))
            else:
                ok, res = run_bin(url, kind, cl, impersonate=(st == "imp"))
        except Exception as e:
            ok, res = False, str(e)[:300]
        if ok and res and Path(res).exists():
            return True, res
        last = str(res)
        low = last.lower()
        if "certificate" in low and not tried_tls and tls_policy(host):
            tried_tls = True
            i -= 1
            continue
        if "unsupported url" in low:
            steps = [s for s in steps[i:] if s[0] in ("gen",)]
            i = 0
            if not steps:
                break
            continue
        if any(w in low for w in FATAL) or "login" in low or "log in" in low or "cookies" in low:
            if not cookies_for(host) and ("login" in low or "log in" in low or "sign in" in low or "cookies" in low):
                last += " | " + L("нужны cookies: положите cookies/%s.txt" % host.replace("www.", ""), "cookies needed: put cookies/%s.txt" % host.replace("www.", ""))
            break
    return False, last


# ==========================================================================
#  gallery-dl и фото
# ==========================================================================
def pip_install(pk):
    for extra in (["--break-system-packages"], []):
        r = subprocess.run([sys.executable, "-m", "pip", "install", "-U"] + extra + pk, timeout=900)
        if r.returncode == 0:
            return True
    return False


GDL_DEPS = ["requests", "urllib3", "certifi", "idna", "charset-normalizer"]


def gdl(args, host=""):
    cmd = [sys.executable, "-m", "gallery_dl"] + args
    if ST.g("proxy"):
        cmd += ["--proxy", ST.g("proxy")]
    ck = cookies_for(host)
    if ck:
        cmd += ["--cookies", ck]
    if any(h in host for h in SLOW_HOSTS):
        cmd += ["--sleep-request", "3-8"]
    for att in range(2):
        r = subprocess.run(cmd, timeout=3600)
        err = r.stderr.decode("utf-8", "replace")
        if "ModuleNotFoundError" in err or "No module named" in err:
            with Spin(L("Доустанавливаю зависимости gallery-dl", "Installing gallery-dl dependencies"), quiet=True):
                pip_install(GDL_DEPS + ["gallery-dl"])
            continue
        return r.returncode, r.stdout.decode("utf-8", "replace"), err
    return 1, "", "gallery-dl unavailable"


def gallery_list(url):
    host = urlparse(url).netloc.lower()
    rc, out, err = gdl(["-g", url], host)
    urls = [l.strip() for l in out.splitlines() if re.match(r"^https?://", l.strip())]
    return urls, err


def gallery_whole(url):
    d = outdir("photo")
    before = {p for p in d.rglob("*") if p.is_file()}
    rc, out, err = gdl(["-d", str(d), url], urlparse(url).netloc.lower())
    new = [p for p in d.rglob("*") if p.is_file() and p not in before]
    if new:
        return True, str(new[0].parent) + " (%d)" % len(new)
    return False, (err.strip().splitlines() or ["gallery-dl: nothing downloaded"])[-1][:200]


# ==========================================================================
#  ПЛАНИРОВАНИЕ (вопросы только здесь) → ЗАГРУЗКА БЕЗ ВОПРОСОВ
# ==========================================================================
def mkjob(url, kind, title="", src="ytdlp", typ=None, referer=None, dur=None):
    return {"url": url, "kind": kind, "title": title or url, "src": src, "type": typ or kind, "referer": referer, "dur": dur}


def select_items(items, what):
    """Показать найденные медиа и дать выбрать. Режим 'all'/'first' из настроек — без вопросов."""
    if len(items) <= 1:
        return items
    cnt = {t: sum(1 for i in items if i["type"] == t) for t in ("video", "audio", "photo")}
    print("[*] %s: %s" % (L("Найдено на странице", "Found on the page"), ", ".join("%s %d" % ({"video": L("видео", "video"), "audio": L("аудио", "audio"), "photo": L("фото", "photo")}[t], n) for t, n in cnt.items() if n)))
    mode = ST.g("ask_selection")
    if mode == "all" or (UNATT[0] and mode != "first"):
        print("[+] " + L("Беру все (%d)" % len(items), "Taking all (%d)" % len(items)))
        return items
    if mode == "first":
        print("[+] " + L("Беру первое", "Taking the first"))
        return items[:1]
    shown = items[:200]
    for i, it in enumerate(shown, 1):
        extra = fmt_dur(it["dur"]) if it.get("dur") else ""
        print("  %s %s %s %s" % (c("%3d" % i, accent(), True), ICON.get(it["type"], "•"), trunc(it["title"], term_w() - 22), dim(extra)))
    if len(items) > 200:
        print(dim("... +%d" % (len(items) - 200)))
    while True:
        v = ask(L("Что скачать: номера 1,3-5 / all / v видео / a аудио / p фото / Enter = все", "Pick: numbers 1,3-5 / all / v video / a audio / p photo / Enter = all"), "all", quit_ok=False).lower()
        flt = {"v": "video", "a": "audio", "p": "photo"}.get(v)
        if flt:
            sel = [i for i in shown if i["type"] == flt]
            if sel:
                return sel
            print("[!] " + L("Такого типа нет", "No such type"))
            continue
        try:
            return [shown[i - 1] for i in parse_multi(v, len(shown))]
        except ValueError:
            print("[!] " + L("Неверный ввод", "Bad input"))


def probe_ytdlp(url):
    import yt_dlp
    o = {"quiet": True, "no_warnings": True, "logger": QLog(), "extract_flat": "in_playlist", "skip_download": True, "socket_timeout": ST.g("socket_timeout"), "http_headers": {"User-Agent": ua()}}
    if ST.g("proxy"):
        o["proxy"] = ST.g("proxy")
    ck = cookies_for(urlparse(url).netloc)
    if ck:
        o["cookiefile"] = ck
    if ST.g("playlist_limit"):
        o["playlistend"] = ST.g("playlist_limit")
    if (urlparse(url).hostname or "") in INSECURE:
        o["nocheckcertificate"] = True
    with yt_dlp.YoutubeDL(o) as y:
        return y.extract_info(url, download=False)


def plan_url(url, kind):
    """Анализ одной ссылки → список заданий (с вопросом о выборе, если медиа несколько)."""
    host = (urlparse(url).hostname or "").lower()
    e = ext_of(url.split("?")[0])
    if type_of_ext(e):
        t = type_of_ext(e)
        return [mkjob(url, t if kind == "auto" else kind, Path(urlparse(url).path).name, "direct", t)]
    items, err = [], ""
    if kind in ("video", "audio", "auto"):
        try:
            with Spin(L("Анализ: ", "Analyzing: ") + trunc(url, 40), quiet=True):
                info = probe_ytdlp(url)
            ents = [x for x in (info.get("entries") or []) if x] if info else []
            if info and (info.get("entries") is not None) and ents:
                for x in ents:
                    u = x.get("webpage_url") or x.get("url") or ""
                    if not u.startswith("http") and x.get("id") and "youtube" in str(x.get("ie_key", "")).lower():
                        u = "https://www.youtube.com/watch?v=" + x["id"]
                    if u.startswith("http"):
                        items.append(mkjob(u, "audio" if kind == "audio" else "video", x.get("title") or u, "ytdlp", "audio" if kind == "audio" else "video", dur=x.get("duration")))
                if len(items) > 1:
                    print("[+] %s: %s" % (L("Плейлист/канал", "Playlist/channel"), trunc(info.get("title") or url, 40)))
            elif info:
                items = [mkjob(url, "audio" if kind == "audio" else "video", info.get("title") or url, "ytdlp", "audio" if kind == "audio" else "video", dur=info.get("duration"))]
        except Exception as ex:
            err = ANSI_RE.sub("", str(ex))[:200]
            if any(w in err.lower() for w in FATAL) and "age" not in err.lower():
                print("[!] " + trunc(err, term_w() - 6))
                return []
            if "youtube" in host or "youtu.be" in host:
                items = [mkjob(url, "audio" if kind == "audio" else "video", url, "ytdlp")]
        if items:
            return select_items(items, kind)
    # фото/галереи и страницы с несколькими медиа
    media = []
    if kind in ("photo", "auto") and not any(x in host for x in ("youtube.com", "youtu.be")):
        with Spin(L("gallery-dl: список медиа", "gallery-dl: listing media"), quiet=True):
            try:
                urls, gerr = gallery_list(url)
            except Exception:
                urls, gerr = [], ""
        for u in urls:
            ee = ext_of(u.split("?")[0])
            media.append({"type": type_of_ext(ee) or "photo", "url": u, "title": unquote(Path(urlparse(u).path).name) or u[-30:]})
        if not media and gerr and ("login" in gerr.lower() or "401" in gerr or "403" in gerr) and not cookies_for(host):
            print("[!] " + L("Сайт требует вход: положите cookies/%s.txt" % host.replace("www.", ""), "Login required: put cookies/%s.txt" % host.replace("www.", "")))
    if not media:
        pages = [url]
        if "instagram.com" in host:
            m = re.search(r"/(p|reel|tv)/([\w-]+)", url)
            if m:
                pages.insert(0, "https://www.instagram.com/%s/%s/embed/captioned/" % (m.group(1), m.group(2)))
        for pg in pages:
            try:
                with Spin(L("Разбор страницы", "Parsing page"), quiet=True):
                    media = scrape_media(pg)
            except Exception as ex:
                err = str(ex)
                media = []
            if media:
                break
        if not media:
            wb = wayback_url(url)
            if wb:
                try:
                    media = scrape_media(wb)
                    if media:
                        print("[*] " + L("Страница взята из Wayback Machine", "Page taken from Wayback Machine"))
                except Exception:
                    pass
    if kind in ("video", "audio"):
        media = [m for m in media if m["type"] == kind] or [m for m in media if m["type"] in ("video", "audio")]
    if media:
        sel = select_items(media, kind)
        return [mkjob(m["url"], m["type"], m["title"], "direct" if not m["url"].endswith(".m3u8") else "direct", m["type"], referer=url) for m in sel]
    if kind == "photo":
        return [mkjob(url, "photo", url, "gallery")]
    print("[!] %s %s" % (L("Медиа не найдено:", "No media found:"), trunc(err or url, term_w() - 24)))
    return []


def do_job(job):
    src, url = job["src"], job["url"]
    if src == "ytdlp":
        return ytdlp_chain(url, "audio" if job["kind"] == "audio" else "video", job.get("q"))
    if src == "gallery":
        return gallery_whole(url)
    typ = job.get("type") or "video"
    if ext_of(url.split("?")[0]) == ".m3u8":
        return True, str(hls_download(url, "audio" if typ == "audio" else "video", job.get("referer")))
    return True, str(dl_direct(url, outdir(typ), job.get("referer")))


def free_mb():
    try:
        return shutil.disk_usage(str(BASE)).free // 1048576
    except Exception:
        return 10 ** 9


def run_jobs(jobs, resume=False):
    """Загрузка без вопросов: очередь сохраняется, неудачные повторяются, итоговая сводка."""
    if not jobs:
        return
    UNATT[0] = True
    jsave(QUEUE, {"jobs": jobs})
    results, pending = [], list(jobs)
    t0 = time.time()
    try:
        for rnd in range(ST.g("retry_rounds")):
            failed = []
            for i, j in enumerate(pending, 1):
                if free_mb() < ST.g("min_free_mb"):
                    print("[!] " + L("Мало места (%d МБ) — остановка. Очередь сохранена." % free_mb(), "Low disk space (%d MB) — stopped. Queue saved." % free_mb()))
                    failed += pending[i - 1:]
                    break
                print("\n" + c("[%d/%d]" % (i, len(pending)), accent(), True) + " " + ICON.get(j["type"], "") + " " + trunc(j["title"], term_w() - 14) + (dim("  (%s %d)" % (L("круг", "round"), rnd + 1)) if rnd else ""))
                if ST.g("skip_history") and hist_done(j["url"]):
                    print("[*] " + L("Уже скачано — пропуск", "Already downloaded — skipped"))
                    results.append((j, "skip", ""))
                    continue
                try:
                    ok, res = do_job(j)
                except KeyboardInterrupt:
                    raise
                except Exception as ex:
                    ok, res = False, str(ex)[:200]
                if ok:
                    print("[+] %s %s" % (L("Готово:", "Done:"), trunc(res, term_w() - 14)))
                    hist_add(j["url"], j["title"], res, "ok")
                    results.append((j, "ok", res))
                else:
                    print("[!] " + trunc(res, term_w() - 6))
                    failed.append(j)
                    if rnd == ST.g("retry_rounds") - 1:
                        hist_add(j["url"], j["title"], "", "fail")
                        results.append((j, "fail", res))
                rest = [x for x in jobs if x not in [r[0] for r in results] ]
                jsave(QUEUE, {"jobs": rest})
                slow = any(h in j["url"] for h in SLOW_HOSTS)
                if i < len(pending):
                    time.sleep(ST.g("sleep_between") + (random.uniform(0.5, 1.5) * ST.g("sleep_slow") if slow else 0))
            pending = failed
            if not pending:
                break
            print("\n[*] " + L("Повтор неудачных (%d) через %d с..." % (len(pending), 5 * (rnd + 1)), "Retrying failed (%d) in %d s..." % (len(pending), 5 * (rnd + 1))))
            time.sleep(5 * (rnd + 1))
    except KeyboardInterrupt:
        print("\n[!] " + L("Прервано. Очередь сохранена (пункт «Очередь»).", "Interrupted. Queue saved ('Queue' item)."))
        UNATT[0] = False
        return
    UNATT[0] = False
    rest = [j for j in jobs if j in pending]
    jsave(QUEUE, {"jobs": rest})
    ok_n, sk_n, fl_n = (sum(1 for r in results if r[1] == s) for s in ("ok", "skip", "fail"))
    print("\n" + box([grad(L("Итог", "Summary"), 0, True),
                      "%s %d   %s %d   %s %d   %s" % (c(L("успешно", "ok"), OK_C, True), ok_n, c(L("пропущено", "skipped"), WARN_C), sk_n, c(L("ошибок", "failed"), ERR_C, True), fl_n, dim(fmt_dur(time.time() - t0)))]))
    for j, st, res in results:
        if st == "fail":
            print("  " + c("✗ ", ERR_C) + trunc(j["title"], 30) + dim(" — " + trunc(res, term_w() - 40)))
    jsave(BASE / "reports" / ("report_%s.json" % now_stamp()), [{"url": j["url"], "title": j["title"], "status": s, "result": r} for j, s, r in results])
    if ST.g("bell"):
        sys.stdout.write("\a")
        sys.stdout.flush()


# ==========================================================================
#  МЕНЮ: ЗАГРУЗКА, ОЧЕРЕДЬ, ПОИСК
# ==========================================================================
URL_RE = re.compile(r"https?://[^\s\"'<>]+")


def read_clipboard():
    try:
        return open("/dev/clipboard", "rb").read().decode("utf-8", "replace")
    except Exception:
        return ""


def read_urls():
    print(dim(L("Вставляйте ссылки по одной (пустая строка — старт). Можно: путь к .txt, 'clip' — из буфера iOS.", "Paste URLs one per line (blank = start). Also: .txt path, 'clip' = iOS clipboard.")))
    urls = []
    while True:
        v = ask(L("Ссылка", "URL") + " #%d" % (len(urls) + 1), "", quit_ok=True)
        if not v:
            break
        if v.lower() in ("clip", "c"):
            found = URL_RE.findall(read_clipboard())
            print("[+] " + L("Из буфера: %d" % len(found), "From clipboard: %d" % len(found)))
            urls += found
        elif v.startswith(("/", "~")) and Path(v).expanduser().is_file():
            found = URL_RE.findall(Path(v).expanduser().read_text("utf-8", "replace"))
            print("[+] " + L("Из файла: %d" % len(found), "From file: %d" % len(found)))
            urls += found
        else:
            urls += URL_RE.findall(v) or ([("https://" + v)] if "." in v and " " not in v else [])
    return list(dict.fromkeys(urls))


def download_menu(kind):
    clear_screen()
    hdr({"video": L("Скачать видео", "Download video"), "audio": L("Скачать аудио", "Download audio"), "photo": L("Скачать фото / галереи", "Download photos / galleries"), "auto": L("Умная загрузка", "Smart download")}[kind],
        L("Все вопросы — сразу после ввода ссылок, затем загрузка идёт сама", "All questions come right after the links, then it runs on its own"))
    if kind in ("video", "auto"):
        print(dim("%s: %s, %s, H.264=%s" % (L("Профиль", "Profile"), ST.g("quality"), ST.g("container"), ST.g("prefer_h264"))))
        q = ask(L("Качество (best/2160/1440/1080/720/480/360)", "Quality (best/2160/1440/1080/720/480/360)"), ST.g("quality"), quit_ok=True)
        if q in SCH["quality"][4]:
            ST.set("quality", q)
    elif kind == "audio":
        f = ask(L("Формат (m4a/mp3/opus/flac/best)", "Format (m4a/mp3/opus/flac/best)"), ST.g("audio_format"))
        if f in SCH["audio_format"][4]:
            ST.set("audio_format", f)
    urls = read_urls()
    if not urls:
        return
    if free_mb() < 500:
        print("[!] " + L("Свободно всего %d МБ" % free_mb(), "Only %d MB free" % free_mb()))
    jobs = []
    for n, u in enumerate(urls, 1):
        print("\n" + c("%s %d/%d" % (L("Анализ", "Analysis"), n, len(urls)), accent(), True) + " " + dim(trunc(u, term_w() - 16)))
        try:
            jobs += plan_url(u, kind)
        except Quit:
            raise
        except Exception as ex:
            print("[!] %s" % trunc(str(ex), term_w() - 6))
    jobs = [j for i, j in enumerate(jobs) if j["url"] not in [x["url"] for x in jobs[:i]]]
    if not jobs:
        print("[!] " + L("Нечего скачивать", "Nothing to download"))
        return
    print("\n[+] " + L("К загрузке: %d. Дальше без вопросов (Ctrl+C — пауза)." % len(jobs), "To download: %d. No more questions (Ctrl+C = pause)." % len(jobs)))
    when = ask(L("Старт: Enter — сразу, число — через N минут", "Start: Enter = now, number = in N minutes"), "", quit_ok=False)
    if when.isdigit() and int(when) > 0:
        wait_minutes(int(when))
    run_jobs(jobs)


def wait_minutes(m):
    end = time.time() + m * 60
    try:
        with Spin(L("Ожидание старта", "Waiting to start"), quiet=True) as s:
            while time.time() < end:
                s.update(L("Старт через %s (Ctrl+C — отмена)" % fmt_dur(end - time.time()), "Starting in %s (Ctrl+C to cancel)" % fmt_dur(end - time.time())))
                time.sleep(1)
    except KeyboardInterrupt:
        raise Quit()


def queue_menu():
    while True:
        q = jload(QUEUE, {}).get("jobs", [])
        k = menu(L("Очередь (%d)" % len(q), "Queue (%d)" % len(q)), [
            ("1", L("Запустить / продолжить очередь", "Run / resume queue"), ""), ("2", L("Показать", "Show"), ""), ("3", L("Добавить ссылки из буфера iOS", "Add links from iOS clipboard"), ""),
            ("4", L("Добавить ссылки из .txt файла", "Add links from .txt file"), ""), ("5", L("Очистить очередь", "Clear queue"), ""), ("6", L("Запуск по таймеру", "Start on a timer"), "")])
        if k == "q":
            return
        if k in ("1", "6"):
            if not q:
                print("[!] " + L("Очередь пуста", "Queue is empty"))
            else:
                if k == "6":
                    m = ask(L("Через сколько минут", "In how many minutes"), "30", quit_ok=False)
                    if m.isdigit():
                        wait_minutes(int(m))
                run_jobs(q)
        elif k == "2":
            for i, j in enumerate(q, 1):
                print("  %s %s %s" % (c("%3d" % i, accent(), True), ICON.get(j["type"], ""), trunc(j["title"], term_w() - 10)))
        elif k in ("3", "4"):
            txt = read_clipboard() if k == "3" else (Path(ask(L("Путь к .txt", ".txt path"), "", quit_ok=False)).expanduser().read_text("utf-8", "replace") if True else "")
            urls = list(dict.fromkeys(URL_RE.findall(txt)))
            kind = ask(L("Тип: auto/video/audio/photo", "Type: auto/video/audio/photo"), "auto", quit_ok=False)
            kind = kind if kind in ("auto", "video", "audio", "photo") else "auto"
            jobs = []
            for u in urls:
                jobs += plan_url(u, kind)
            jsave(QUEUE, {"jobs": q + jobs})
            print("[+] " + L("Добавлено: %d" % len(jobs), "Added: %d" % len(jobs)))
        elif k == "5" and confirm(L("Очистить?", "Clear?")):
            jsave(QUEUE, {"jobs": []})
        if k != "q":
            pause()


def search_menu():
    k = menu(L("Поиск", "Search"), [("1", "YouTube", ""), ("2", "SoundCloud", ""), ("3", "RuTube", ""), ("4", L("Страница другого сайта (список видео)", "Another site page (video list)"), "")])
    if k == "q":
        return
    if k == "4":
        u = ask("URL", "", quit_ok=False)
        jobs = plan_url(u, "auto") if u else []
        if jobs and confirm(L("Скачать выбранное?", "Download selected?"), True):
            run_jobs(jobs)
        return
    qy = ask(L("Запрос", "Query"), "", quit_ok=False)
    if not qy:
        return
    items = []
    with Spin(L("Ищу", "Searching"), quiet=True):
        try:
            if k == "3":
                d = json.loads(http_get("https://rutube.ru/api/search/video/?query=%s" % quote(qy)).decode())
                items = [mkjob(r["video_url"], "video", r.get("title", ""), "ytdlp", "video", dur=r.get("duration")) for r in d.get("results", [])[:10]]
            else:
                import yt_dlp
                pre = "ytsearch10:" if k == "1" else "scsearch10:"
                with yt_dlp.YoutubeDL({"quiet": True, "extract_flat": True, "logger": QLog(), "proxy": ST.g("proxy") or None}) as y:
                    info = y.extract_info(pre + qy, download=False)
                for e in info.get("entries", []):
                    u = e.get("url") or ""
                    if not u.startswith("http") and e.get("id"):
                        u = "https://www.youtube.com/watch?v=" + e["id"]
                    items.append(mkjob(u, "audio" if k == "2" else "video", e.get("title") or u, "ytdlp", "audio" if k == "2" else "video", dur=e.get("duration")))
        except Exception as ex:
            print("[!] %s" % trunc(str(ex), term_w() - 6))
    if not items:
        return
    for i, it in enumerate(items, 1):
        print("  %s %s %s" % (c("%2d" % i, accent(), True), trunc(it["title"], term_w() - 16), dim(fmt_dur(it["dur"]) if it.get("dur") else "")))
    sel = ask_multi(L("Скачать (номера/all)", "Download (numbers/all)"), len(items))
    if sel:
        kind = ask(L("Как: video или audio", "As: video or audio"), "audio" if k == "2" else "video", quit_ok=False)
        for i in sel:
            items[i - 1]["kind"] = "audio" if kind == "audio" else "video"
            items[i - 1]["type"] = items[i - 1]["kind"]
        run_jobs([items[i - 1] for i in sel])


# ==========================================================================
#  КОНВЕРТЕР И МЕДИА-ИНСТРУМЕНТЫ
# ==========================================================================
VPROF = {"h264 (iPhone/Android)": ("libx264", ["-crf", "23", "-preset", "fast", "-pix_fmt", "yuv420p", "-profile:v", "high"], "mp4"),
         "h264 baseline (старые)": ("libx264", ["-crf", "24", "-preset", "fast", "-pix_fmt", "yuv420p", "-profile:v", "baseline", "-level", "3.0"], "mp4"),
         "h265/HEVC": ("libx265", ["-crf", "28", "-preset", "fast", "-tag:v", "hvc1"], "mp4"), "vp9": ("libvpx-vp9", ["-crf", "32", "-b:v", "0"], "webm"), "av1": ("libsvtav1", ["-crf", "35"], "mkv")}
APROF = {"aac/m4a": ("aac", ["-b:a", "192k"], "m4a"), "mp3": ("libmp3lame", ["-b:a", "192k"], "mp3"), "opus": ("libopus", ["-b:a", "160k"], "opus"), "flac": ("flac", [], "flac"), "ac3": ("ac3", ["-b:a", "192k"], "ac3")}


def pick_media(multi=True):
    k = menu(L("Папка", "Folder"), [("1", "videos", ""), ("2", "audio", ""), ("3", "photos", ""), ("4", "collages", ""), ("5", "tmp", "")], show=False)
    if k == "q":
        return None
    d = BASE / {"1": "videos", "2": "audio", "3": "photos", "4": "collages", "5": "tmp"}[k]
    return pick_files(d, None, multi)


def convert_menu():
    fs = pick_media()
    if not fs:
        return
    isaud = all(f.suffix.lower() in AEXT for f in fs)
    pr = APROF if isaud else dict(VPROF, **{"только аудио → " + k: v for k, v in APROF.items()})
    name = pick_one(L("Целевой формат", "Target format"), list(pr))
    if not name:
        return
    enc, opts, ext = pr[name]
    audio_only = name in APROF or name.startswith("только")
    UNATT[0] = True
    ok = 0
    for f in fs:
        out = uniq(f.with_name("%s_conv.%s" % (f.stem, ext)))
        dur = probe_duration(f)
        args = ["-i", f] + (["-vn", "-c:a", enc] + opts if audio_only else ["-c:v", enc] + opts + ["-c:a", "aac", "-b:a", "160k", "-movflags", "+faststart"]) + [out]
        print("[*] " + f.name)
        if ff_run(args, "conv", dur) == 0:
            ok += 1
            print("[+] " + out.name)
    UNATT[0] = False
    print("[+] %d/%d" % (ok, len(fs)))


def tools_menu():
    k = menu(L("Медиа-инструменты", "Media tools"), [("1", L("Конвертер (кодеки)", "Converter (codecs)"), ""), ("2", L("Извлечь аудио из видео", "Extract audio from video"), ""), ("3", L("Видео → GIF", "Video → GIF"), ""),
                                                     ("4", L("Кадр-превью", "Thumbnail frame"), ""), ("5", L("Сжать видео (CRF)", "Compress video (CRF)"), ""), ("6", L("Склеить видео", "Concat videos"), ""),
                                                     ("7", L("Нарезать на части", "Split into segments"), ""), ("8", L("Нормализовать громкость", "Normalize loudness"), ""), ("9", L("Заменить аудиодорожку", "Replace audio track"), ""),
                                                     ("10", L("Вшить/достать субтитры", "Embed / extract subtitles"), ""), ("11", L("Обрезать по времени", "Trim by time"), "")])
    if k == "q":
        return
    if k == "1":
        return convert_menu()
    fs = pick_media(multi=k in ("2", "3", "4", "5", "8", "6"))
    if not fs:
        return
    UNATT[0] = True
    try:
        if k == "6":
            lst = BASE / "tmp" / "concat.txt"
            lst.write_text("\n".join("file '%s'" % str(f).replace("'", "'\\''") for f in fs))
            ff_run(["-f", "concat", "-safe", "0", "-i", lst, "-c", "copy", uniq(fs[0].with_name("merged" + fs[0].suffix))], "concat")
            return
        extra = {}
        if k == "7":
            extra["n"] = ask(L("Длина части, сек", "Segment length, s"), "600", quit_ok=False)
        if k == "11":
            extra["ss"] = ask(L("Начало (00:01:30)", "Start (00:01:30)"), "00:00:00", quit_ok=False)
            extra["to"] = ask(L("Конец (00:02:30)", "End (00:02:30)"), "", quit_ok=False)
        if k == "5":
            extra["crf"] = ask("CRF (18-32)", "28", quit_ok=False)
        if k == "9":
            af = pick_files(BASE / "audio", None, False, L("Новое аудио", "New audio"))
            if not af:
                return
            f = fs[0]
            ff_run(["-i", f, "-i", af[0], "-map", "0:v:0", "-map", "1:a:0", "-c:v", "copy", "-c:a", "aac", "-shortest", uniq(f.with_name(f.stem + "_newaudio.mp4"))], "merge")
            return
        if k == "10":
            f = fs[0]
            sub = ask(L("Файл .srt для вшивания (Enter — достать из видео)", "Path to .srt to embed (Enter = extract)"), "", quit_ok=False)
            if sub:
                ff_run(["-i", f, "-i", sub, "-c", "copy", "-c:s", "mov_text", uniq(f.with_name(f.stem + "_subs.mp4"))], "subs")
            else:
                ff_run(["-i", f, "-map", "0:s:0", uniq(f.with_name(f.stem + ".srt"))], "subs")
            return
        for f in fs:
            d = probe_duration(f)
            o = f.with_name
            if k == "2":
                ff_run(["-i", f, "-vn", "-c:a", "aac", "-b:a", "192k", uniq(BASE / "audio" / (f.stem + ".m4a"))], "audio", d)
            elif k == "3":
                ff_run(["-i", f, "-vf", "fps=10,scale=480:-1:flags=lanczos", "-loop", "0", uniq(f.with_name(f.stem + ".gif"))], "gif", d)
            elif k == "4":
                ff_run(["-ss", "00:00:01", "-i", f, "-frames:v", "1", uniq(BASE / "photos" / (f.stem + "_thumb.jpg"))], "thumb")
            elif k == "5":
                ff_run(["-i", f, "-c:v", "libx264", "-crf", extra["crf"], "-preset", "fast", "-c:a", "aac", "-b:a", "128k", "-movflags", "+faststart", uniq(f.with_name(f.stem + "_small.mp4"))], "compress", d)
            elif k == "7":
                ff_run(["-i", f, "-c", "copy", "-map", "0", "-f", "segment", "-segment_time", extra["n"], "-reset_timestamps", "1", str(f.with_name(f.stem + "_part%03d" + f.suffix))], "split", d)
            elif k == "8":
                ff_run(["-i", f, "-af", "loudnorm=I=-16:TP=-1.5:LRA=11", "-c:v", "copy", uniq(f.with_name(f.stem + "_norm" + f.suffix))], "loudnorm", d)
            elif k == "11":
                ff_run(["-ss", extra["ss"]] + (["-to", extra["to"]] if extra["to"] else []) + ["-i", f, "-c", "copy", uniq(f.with_name(f.stem + "_cut" + f.suffix))], "trim")
    finally:
        UNATT[0] = False


# ==========================================================================
#  ФОТО: коллаж / панорама / лента, правка, метаданные
# ==========================================================================
def im_prefix():
    return ["magick"] if shutil.which("magick") else (["convert"] if shutil.which("convert") else None)


def collage_menu():
    pre = im_prefix()
    if not pre:
        print("[!] " + L("ImageMagick не установлен (apk add imagemagick)", "ImageMagick is not installed (apk add imagemagick)"))
        return
    k = menu(L("Коллаж / сшивание", "Collage / stitching"), [("1", L("Сетка (коллаж)", "Grid (collage)"), "montage"), ("2", L("Панорама (горизонтально)", "Panorama (horizontal)"), "+append"), ("3", L("Лента (вертикально, скриншоты)", "Strip (vertical, screenshots)"), "-append")])
    if k == "q":
        return
    fs = pick_files(BASE / "photos", {".jpg", ".jpeg", ".png", ".webp"}, True, L("Фото для сшивания", "Photos to stitch"))
    if not fs:
        return
    if len(fs) > 30:
        print("[!] " + L("Для iSH беру первые 30", "Taking first 30 for iSH"))
        fs = fs[:30]
    if len(fs) > 12:
        print("[*] " + L("Это может занять 1–2 минуты на iSH", "This may take 1–2 minutes on iSH"))
    tmp = BASE / "tmp"
    out = uniq(BASE / "collages" / ("%s_%s.jpg" % ({"1": "collage", "2": "panorama", "3": "strip"}[k], now_stamp())))
    UNATT[0] = True
    try:
        if k == "1":
            cols = int(ask(L("Колонок", "Columns"), "3", quit_ok=False) or 3)
            cell = ask(L("Размер ячейки (300x300)", "Cell size (300x300)"), "300x300", quit_ok=False)
            gap = int(ask(L("Отступ", "Gap"), "5", quit_ok=False) or 5)
            bg = ask(L("Фон (#336699 / black)", "Background (#336699 / black)"), "#1e1e2e", quit_ok=False)
            labels = confirm(L("Подписывать имена?", "Label file names?"))
            tmps = []
            for i, f in enumerate(track(fs, L("Подготовка", "Preparing")), 1):
                t = tmp / ("c_%03d.jpg" % i)
                subprocess.run(pre + [str(f) + "[0]", "-auto-orient", "-resize", cell + "^", "-gravity", "center", "-extent", cell, "-quality", "88", str(t)], timeout=300)
                if t.exists():
                    tmps.append((t, f.stem))
            mont = ["montage"] if shutil.which("montage") else (["magick", "montage"] if shutil.which("magick") else None)
            if not mont or not tmps:
                print("[!] montage ?")
                return
            args = mont + ([] if not labels else []) + [str(t) for t, _ in tmps] + ["-tile", "%dx" % cols, "-geometry", "%s+%d+%d" % (cell, gap, gap), "-background", bg, "-quality", "90", str(out)]
            with Spin(L("Собираю коллаж", "Building collage"), quiet=True):
                r = subprocess.run(args, timeout=1200)
            for t, _ in tmps:
                t.unlink(missing_ok=True)
        else:
            hgt = ask(L("Выровнять высоту/ширину до (px, 0 — не менять)", "Normalize height/width to (px, 0 = keep)"), "1080", quit_ok=False)
            tmps = []
            for i, f in enumerate(track(fs, L("Подготовка", "Preparing")), 1):
                t = tmp / ("s_%03d.jpg" % i)
                rs = ["-resize", ("x%s" % hgt) if k == "2" else ("%sx" % hgt)] if hgt != "0" else []
                subprocess.run(pre + [str(f) + "[0]", "-auto-orient"] + rs + ["-quality", "88", str(t)], timeout=300)
                tmps.append(t)
            with Spin(L("Сшиваю", "Stitching"), quiet=True):
                r = subprocess.run(pre + [str(t) for t in tmps if t.exists()] + ["+append" if k == "2" else "-append", "-quality", "90", str(out)], timeout=1200)
            for t in tmps:
                t.unlink(missing_ok=True)
        print(("[+] " + str(out)) if out.exists() else "[!] " + (r.stderr.decode("utf-8", "replace")[:150] or "error"))
    finally:
        UNATT[0] = False


def photo_menu():
    pre = im_prefix()
    k = menu(L("Фото: правка и оптимизация", "Photos: edit & optimize"), [("1", L("Уменьшить (800x600 / 50%)", "Resize (800x600 / 50%)"), ""), ("2", L("Повернуть", "Rotate"), ""), ("3", L("Авто-поворот по EXIF", "Auto-orient by EXIF"), ""),
                                                                      ("4", L("Конвертировать (jpg/png/webp)", "Convert (jpg/png/webp)"), ""), ("5", L("Сжать JPEG (jpegoptim)", "Compress JPEG (jpegoptim)"), ""), ("6", L("Обрезать (100x100+10+10)", "Crop (100x100+10+10)"), "")])
    if k == "q":
        return
    if not pre:
        print("[!] ImageMagick?")
        return
    fs = pick_files(BASE / "photos", None, True)
    if not fs:
        return
    arg = {"1": lambda: ask(L("Размер", "Size"), "1280x1280", quit_ok=False), "2": lambda: ask(L("Градусы (90/180/-90)", "Degrees (90/180/-90)"), "90", quit_ok=False),
           "4": lambda: ask("jpg/png/webp", "jpg", quit_ok=False), "6": lambda: ask(L("Геометрия", "Geometry"), "100x100+10+10", quit_ok=False)}.get(k, lambda: "")()
    for f in track(fs, "photo"):
        if k == "5":
            if shutil.which("jpegoptim"):
                subprocess.run(["jpegoptim", "-m85", "--strip-all", str(f)], timeout=300)
            continue
        o = uniq(f.with_name("%s_edit.%s" % (f.stem, arg if k == "4" else f.suffix.lstrip("."))))
        op = {"1": ["-resize", arg], "2": ["-rotate", arg], "3": ["-auto-orient"], "4": [], "6": ["-crop", arg, "+repage"]}[k]
        subprocess.run(pre + [str(f)] + op + [str(o)], timeout=300)
    print("[+] OK")


def meta_menu():
    k = menu(L("Метаданные и приватность", "Metadata & privacy"), [("1", L("Просмотр тегов", "View tags"), ""), ("2", L("Удалить ВСЕ метаданные", "Strip ALL metadata"), ""), ("3", L("Удалить только GPS", "Strip GPS only"), ""),
                                                                 ("4", L("Показать GPS + ссылка на карту", "Show GPS + map link"), ""), ("5", L("Переименовать в случайные имена", "Rename to random names"), ""), ("6", L("Поиск дубликатов (SHA-256)", "Find duplicates (SHA-256)"), "")])
    if k == "q":
        return
    fs = pick_media()
    if not fs:
        return
    ex = shutil.which("exiftool")
    for f in fs:
        if k == "1":
            r = subprocess.run([ex or "mediainfo", str(f)], timeout=60)
            print(c(f.name, accent(), True))
            print(r.stdout.decode("utf-8", "replace")[:1800])
        elif k in ("2", "3"):
            if ex:
                r = subprocess.run([ex, "-overwrite_original"] + (["-all="] if k == "2" else ["-gps:all="]) + [str(f)], timeout=120)
                print(("[+] " if r.returncode == 0 else "[!] ") + f.name)
            elif k == "2" and have_ffmpeg() and f.suffix.lower() in VEXT | AEXT:
                o = f.with_name(f.stem + "_clean" + f.suffix)
                print(("[+] " if ff_run(["-i", f, "-map_metadata", "-1", "-c", "copy", o]) == 0 else "[!] ") + f.name)
            else:
                print("[!] exiftool?")
        elif k == "4" and ex:
            r = subprocess.run([ex, "-n", "-gpslatitude", "-gpslongitude", "-s3", str(f)], timeout=60).stdout.decode().split()
            print("%s: %s" % (f.name, ("https://www.openstreetmap.org/?mlat=%s&mlon=%s#map=16/%s/%s" % (r[0], r[1], r[0], r[1])) if len(r) >= 2 else L("GPS нет", "no GPS")))
        elif k == "5":
            n = f.with_name(hashlib.sha1(os.urandom(16)).hexdigest()[:16] + f.suffix)
            f.rename(n)
            print("[+] %s → %s" % (f.name, n.name))
    if k == "6":
        seen = {}
        for f in track(fs, "sha256"):
            h = hashlib.sha256(f.read_bytes() if f.stat().st_size < 200 * 1048576 else b"big" + str(f.stat().st_size).encode()).hexdigest()
            seen.setdefault(h, []).append(f)
        dups = [v for v in seen.values() if len(v) > 1]
        for g in dups:
            print(c(L("Дубликаты:", "Duplicates:"), WARN_C) + " " + ", ".join(x.name for x in g))
        if dups and confirm(L("Удалить копии (оставить первый)?", "Delete copies (keep first)?")):
            for g in dups:
                for x in g[1:]:
                    x.unlink()
        if not dups:
            print("[+] " + L("Дубликатов нет", "No duplicates"))


# ==========================================================================
#  ФАЙЛЫ, ИСТОРИЯ
# ==========================================================================
def files_menu():
    while True:
        k = menu(L("Файлы", "Files"), [("1", L("Просмотр папок и размеры", "Browse folders & sizes"), ""), ("2", L("Удалить файлы", "Delete files"), ""), ("3", L("Переименовать", "Rename"), ""),
                                       ("4", L("Очистить tmp и недокачанные .part", "Clean tmp and partial .part"), ""), ("5", L("Показать путь для iOS «Файлы»", "Show path for iOS Files"), "")])
        if k == "q":
            return
        if k == "1":
            rows = []
            for d in DIRS:
                n = s = 0
                for r, _, fs in os.walk(str(BASE / d)):
                    for f in fs:
                        try:
                            s += os.lstat(os.path.join(r, f)).st_size
                            n += 1
                        except OSError:
                            pass
                rows.append([d, str(n), fmt_size(s)])
            table(rows, [L("Папка", "Folder"), L("файлов", "files"), L("размер", "size")])
            print("[*] %s: %d MB" % (L("Свободно", "Free"), free_mb()))
        elif k == "2":
            fs = pick_media()
            if fs and confirm(L("Удалить %d файл(ов)?" % len(fs), "Delete %d file(s)?" % len(fs))):
                for f in fs:
                    try:
                        f.unlink()
                    except OSError as e:
                        print("[!] %s" % e)
        elif k == "3":
            fs = pick_media(False)
            if fs:
                nn = ask(L("Новое имя", "New name"), fs[0].name, quit_ok=False)
                if nn and not (fs[0].parent / nn).exists():
                    fs[0].rename(fs[0].parent / sanitize(nn) if "." in nn else fs[0].parent / (sanitize(nn) + fs[0].suffix))
        elif k == "4":
            n = 0
            for p in list((BASE / "tmp").glob("*")) + [x for d in ("videos", "audio", "photos") for x in (BASE / d).rglob("*.part")]:
                try:
                    p.unlink()
                    n += 1
                except OSError:
                    pass
            print("[+] " + L("Удалено: %d" % n, "Removed: %d" % n))
        elif k == "5":
            print(str(BASE) + "\n" + dim(L("В iSH: mount -t ios . /mnt/files, затем cp -r %s/videos /mnt/files/" % BASE, "In iSH: mount -t ios . /mnt/files, then cp -r %s/videos /mnt/files/" % BASE)))
        pause()


def history_menu():
    h = jload(HIST, {})
    items = sorted(h.items(), key=lambda x: x[1].get("ts", ""), reverse=True)
    if not items:
        print("[!] " + L("История пуста", "History is empty"))
        return
    for i, (u, e) in enumerate(items[:30], 1):
        print("  %s %s %s %s" % (c("%2d" % i, accent(), True), c("✓" if e["status"] == "ok" else "✗", OK_C if e["status"] == "ok" else ERR_C), trunc(e.get("title") or u, term_w() - 28), dim(e.get("ts", ""))))
    k = ask(L("r — повторить неудачные, c — очистить, Enter — назад", "r = retry failed, c = clear, Enter = back"), "", quit_ok=False).lower()
    if k == "c" and confirm(L("Очистить?", "Clear?")):
        jsave(HIST, {})
    elif k == "r":
        jobs = [mkjob(u, "video", e.get("title", u), "ytdlp") for u, e in items if e["status"] != "ok"]
        run_jobs(jobs)


# ==========================================================================
#  СЕТЬ, НАСТРОЙКИ, СРЕДА
# ==========================================================================
def net_menu():
    while True:
        k = menu(L("Сеть и диагностика", "Network & diagnostics"), [("1", L("Проверка доступности сервисов", "Service reachability test"), ""), ("2", L("Прокси (шаблоны)", "Proxy (templates)"), ST.g("proxy") or "-"),
                                                                    ("3", L("Режим DNS", "DNS mode"), ST.g("dns_mode")), ("4", L("Внешний IP", "External IP"), ""), ("5", L("Тест скорости", "Speed test"), ""),
                                                                    ("6", L("Записать DNS в /etc/resolv.conf", "Write DNS to /etc/resolv.conf"), ""), ("7", L("Cookies: папка и подсказки", "Cookies: folder & hints"), "")])
        if k == "q":
            return
        if k == "1":
            hosts = ["www.youtube.com", "i.ytimg.com", "redirector.googlevideo.com", "www.instagram.com", "rutube.ru", "soundcloud.com", "github.com", "pypi.org", "dl-cdn.alpinelinux.org"]
            rows = []
            for h in track(hosts, "net"):
                t = time.time()
                try:
                    ip = patched_gai(h, 443)[0][4][0]
                    d1 = int((time.time() - t) * 1000)
                    t = time.time()
                    s = socket.create_connection((ip, 443), 5)
                    s = ssl.create_default_context().wrap_socket(s, server_hostname=h)
                    s.close()
                    rows.append([h, c("OK", OK_C), "%dms" % d1, "%dms" % int((time.time() - t) * 1000), ip])
                except Exception as e:
                    rows.append([h, c("FAIL", ERR_C), "-", "-", trunc(str(e), 24)])
            table(rows, ["host", "", "DNS", "TCP+TLS", "info"])
        elif k == "2":
            v = pick_one(L("Прокси", "Proxy"), PROXY_T, ST.g("proxy"))
            v = v if v is not None else ask(L("Свой прокси (пусто — выкл)", "Custom proxy (empty = off)"), ST.g("proxy"), quit_ok=False)
            ST.set("proxy", v)
        elif k == "3":
            ST.set("dns_mode", {"auto": "doh", "doh": "system", "system": "auto"}[ST.g("dns_mode")])
            DNS_CACHE.clear()
            print("[+] " + ST.g("dns_mode"))
        elif k == "4":
            for u in ("https://api.ipify.org", "https://icanhazip.com"):
                try:
                    print("[+] " + http_get(u, retries=0, timeout=8).decode().strip())
                    break
                except Exception as e:
                    print("[!] %s" % trunc(str(e), 60))
        elif k == "5":
            t = time.time()
            try:
                d = http_get("https://speed.cloudflare.com/__down?bytes=5000000", timeout=30)
                print("[+] %s/s (%.1f Mbit/s)" % (fmt_size(len(d) / (time.time() - t)), len(d) * 8 / 1e6 / (time.time() - t)))
            except Exception as e:
                print("[!] %s" % e)
        elif k == "6":
            try:
                open("/etc/resolv.conf", "w").write("nameserver 1.1.1.1\nnameserver 8.8.8.8\nnameserver 9.9.9.9\n")
                print("[+] OK")
            except OSError as e:
                print("[!] %s" % e)
        elif k == "7":
            print(str(BASE / "cookies") + "\n" + dim(L("Положите cookies в формате Netscape как cookies/instagram.com.txt, cookies/youtube.com.txt — подхватятся автоматически по домену. Экспорт: расширение «Get cookies.txt» в браузере.", "Put Netscape-format cookies as cookies/instagram.com.txt, cookies/youtube.com.txt — picked up automatically by domain. Export with a 'Get cookies.txt' browser extension.")))
        pause()


def preview():
    print()
    b = Bar(100, L("Образец", "Sample"), "")
    for i in range(0, 101, 5):
        b.cur, b.speed = i, 1
        b.render()
        time.sleep(0.02)
    b.close()
    with Spin(L("Образец спиннера", "Spinner sample"), quiet=True):
        time.sleep(0.8)


def edit_setting(s):
    grp, key, dv, kind, opts, ru, en = s
    cur = ST.g(key)
    if kind == "bool":
        ST.set(key, not cur)
    elif kind == "choice":
        v = pick_one(L(ru, en), list(opts), cur)
        if v:
            ST.set(key, v)
    elif kind == "int":
        v = ask("%s (%s–%s)" % (L(ru, en), opts[0], opts[1]), str(cur), quit_ok=False)
        if re.fullmatch(r"-?\d+", v):
            ST.set(key, max(opts[0], min(opts[1], int(v))))
    else:
        if key == "proxy":
            t = pick_one(L(ru, en), PROXY_T, cur)
            if t is not None:
                ST.set(key, t)
                return
        v = ask(L(ru, en), cur, quit_ok=False, hint=L("'-' очистить", "'-' clear"))
        ST.set(key, "" if v == "-" else v)
    DNS_CACHE.clear()


def settings_menu():
    while True:
        k = menu(L("Настройки", "Settings"), [(str(i), L(ru, en), "") for i, (g, ru, en) in enumerate(GROUPS, 1)] + [("9", L("Сбросить все настройки", "Reset all settings"), ""), ("10", L("Фоновая геолокация (iSH)", "Background location (iSH)"), "off" if (CONF / "noloc").exists() else "on")])
        if k == "q":
            return
        if k == "9":
            if confirm(L("Сбросить?", "Reset?")):
                ST.d = {"lang": ST.g("lang")}
                ST.set("lang", ST.g("lang"))
            continue
        if k == "10":
            p = CONF / "noloc"
            p.unlink() if p.exists() else p.write_text("1")
            continue
        grp = GROUPS[int(k) - 1][0]
        items = [s for s in SCHEMA if s[0] == grp]
        while True:
            clear_screen()
            hdr(L(GROUPS[int(k) - 1][1], GROUPS[int(k) - 1][2]))
            for i, s in enumerate(items, 1):
                v = ST.g(s[1])
                vs = (c("on", OK_C) if v else c("off", ERR_C)) if s[3] == "bool" else c(trunc(str(v) if v != "" else "-", 24), INFO_C)
                print(" %s %s  %s" % (c("%2d" % i, accent(), True), trunc(L(s[5], s[6]), term_w() - 36), vs))
            v = ask(L("Номер параметра (q — назад)", "Parameter # (q = back)"), "", quit_ok=False)
            if v.lower() in ("q", "b", ""):
                break
            if v.isdigit() and 1 <= int(v) <= len(items):
                edit_setting(items[int(v) - 1])
                if grp == "design":
                    preview()


def write_action(a):
    try:
        (CONF / "action").write_text(a)
    except Exception:
        pass


def versions():
    rows = [["python", sys.version.split()[0]]]
    try:
        import yt_dlp.version as yv
        rows.append(["yt-dlp", yv.__version__])
    except Exception:
        rows.append(["yt-dlp", c("нет/missing", ERR_C)])
    try:
        import gallery_dl.version as gv
        rows.append(["gallery-dl", gv.__version__])
    except Exception:
        rows.append(["gallery-dl", c("нет/missing", ERR_C)])
    try:
        import yt_dlp_ejs  # noqa
        rows.append(["yt-dlp-ejs", "ok"])
    except Exception:
        rows.append(["yt-dlp-ejs", "-"])
    for name, cmd in (("ffmpeg", ["ffmpeg", "-version"]), ("ffprobe", ["ffprobe", "-version"]), ("exiftool", ["exiftool", "-ver"]), ("node", ["node", "-v"]), ("imagemagick", ["magick", "-version"]), ("jpegoptim", ["jpegoptim", "--version"]), ("mediainfo", ["mediainfo", "--Version"])):
        if shutil.which(cmd[0]):
            r = subprocess.run(cmd, timeout=20)
            rows.append([name, (r.stdout.decode("utf-8", "replace").strip().splitlines() or ["ok"])[0][:40]])
        else:
            rows.append([name, c("нет/missing", WARN_C)])
    return rows


def env_menu():
    while True:
        k = menu(L("Среда, обновление, отладка", "Environment, update, debug"), [("1", L("Версии и состояние", "Versions & status"), ""), ("2", L("Обновить yt-dlp / gallery-dl / ejs", "Update yt-dlp / gallery-dl / ejs"), ""), ("3", L("yt-dlp Nightly", "yt-dlp Nightly"), ""),
                                                                              ("4", L("Обновить пакеты системы (apk)", "Update system packages (apk)"), ""), ("5", L("Починить окружение / сменить Alpine", "Repair environment / switch Alpine"), ""),
                                                                              ("6", L("Обновить скрипт по URL", "Update script from URL"), ""), ("7", L("Все настройки и пути", "All settings & paths"), ""), ("8", L("Журнал ошибок", "Error log"), "")])
        if k == "q":
            return
        if k == "1":
            table(versions(), [L("Компонент", "Component"), L("Версия", "Version")])
            e = os.environ
            print(dim("ENV=%s  LANG=%s  Alpine=%s  free=%dMB" % (e.get("MF_ENV"), ST.g("lang"), (Path("/etc/alpine-release").read_text().strip() if Path("/etc/alpine-release").exists() else "-"), free_mb())))
        elif k == "2":
            write_action("upgrade_tools"); raise SystemExit(0)
        elif k == "3":
            write_action("nightly"); raise SystemExit(0)
        elif k == "4":
            write_action("pkgupdate"); raise SystemExit(0)
        elif k == "5":
            write_action("repair"); raise SystemExit(0)
        elif k == "6":
            url = ST.g("update_url") or ask(L("URL нового MediaForge.sh", "URL of the new MediaForge.sh"), "", quit_ok=False)
            if not url:
                continue
            ST.set("update_url", url)
            try:
                txt = http_get(url).decode("utf-8", "replace")
            except Exception as e:
                print("[!] %s" % e)
                pause()
                continue
            if not txt.startswith("#!/bin/sh") or "MF_BUILD=" not in txt[:3000]:
                print("[!] " + L("Это не MediaForge — отмена", "Not a MediaForge file — cancelled"))
            elif confirm(L("Установить (sha256 %s)?" % hashlib.sha256(txt.encode()).hexdigest()[:12], "Install (sha256 %s)?" % hashlib.sha256(txt.encode()).hexdigest()[:12]), True):
                (CONF / "MediaForge.new").write_text(txt)
                write_action("applyupdate"); raise SystemExit(0)
        elif k == "7":
            for s in SCHEMA:
                print("  %-16s = %s" % (s[1], ST.g(s[1])))
            print(dim(str(BASE)))
        elif k == "8":
            try:
                print((CONF / "crash.log").read_text()[-2500:])
            except Exception:
                print("[*] " + L("Журнал пуст", "Log is empty"))
        pause()


# ==========================================================================
#  ЗАПУСК
# ==========================================================================
def banner():
    w = term_w(30, 56)
    title, sub = "M E D I A   F O R G E", "D O W N L O A D · C O N V E R T"
    anim = ST.g("banner_anim") and sys.stdout.isatty() and ST.g("anim")
    sp = max(0.3, ST.g("anim_speed") / 100.0)
    for f in range(16 if anim else 1):
        stars = "".join(random.choice(["  ", " ✦", " ·", "  ", " ✧"]) if ST.g("unicode") else random.choice(["  ", " *", " ."]) for _ in range(w // 2 - 1))
        lines = [" " * max(0, (w - 4 - vlen(title)) // 2) + grad(title, f, True), " " * max(0, (w - 4 - vlen(sub)) // 2) + grad(sub, -f), dim(stars[:w - 4])]
        if anim and f > 0:
            sys.stdout.write("\033[%dA" % (len(lines) + 2))
        sys.stdout.write(box(lines, None, w) + "\n")
        sys.stdout.flush()
        if anim:
            time.sleep(0.05 / sp)


def rocket():
    if not (sys.stdout.isatty() and ST.g("anim") and ST.g("banner_anim") and ST.g("unicode")):
        return
    w, p = term_w(30, 50), pal()
    for i in range(0, w - 4, 2):
        trail = "".join(c("~", p[(j + i) % len(p)]) for j in range(max(0, min(i, 8))))
        sys.stdout.write("\r\033[K" + " " * max(0, i - 8) + trail + "🚀")
        sys.stdout.flush()
        time.sleep(0.02 / max(0.3, ST.g("anim_speed") / 100.0))
    sys.stdout.write("\r\033[K")


def status_line():
    q = len(jload(QUEUE, {}).get("jobs", []))
    return "%s py %s · %s · %s%s%s" % (c(U("◆", "*"), accent()), sys.version.split()[0], ST.g("lang").upper(), "%dMB free" % free_mb(), (" · " + c("proxy", WARN_C)) if ST.g("proxy") else "", (" · " + c(L("очередь: %d" % q, "queue: %d" % q), WARN_C)) if q else "")


def guarded(fn):
    try:
        fn()
    except (Quit, KeyboardInterrupt):
        print("\n[+] " + L("Отмена / возврат в меню.", "Cancelled / back to menu."))
    except SystemExit:
        raise
    except Exception:
        tb = traceback.format_exc()
        print("\n[!] " + L("Ошибка: ", "Error: ") + tb.strip().splitlines()[-1])
        try:
            with open(str(CONF / "crash.log"), "a") as f:
                f.write("== %s\n%s\n" % (time.ctime(), tb))
        except Exception:
            pass
    UNATT[0] = False
    pause()


def main():
    ensure_dirs()
    fix_tty()
    clear_screen()
    rocket()
    banner()
    while True:
        items = [("--", L("Загрузка", "Download"), ""), ("1", L("Умная загрузка", "Smart download"), L("авто: видео/аудио/фото", "auto: video/audio/photo")), ("2", L("Видео", "Video"), ""), ("3", L("Аудио", "Audio"), ""),
                 ("4", L("Фото / галереи", "Photos / galleries"), ""), ("5", L("Очередь и таймер", "Queue & timer"), ""), ("6", L("Поиск", "Search"), "YouTube, SoundCloud, RuTube"),
                 ("--", L("Обработка", "Processing"), ""), ("7", L("Конвертер и медиа-инструменты", "Converter & media tools"), ""), ("8", L("Коллаж / сшивание фото", "Photo collage / stitching"), ""),
                 ("9", L("Правка фото", "Photo editing"), ""), ("10", L("Метаданные и приватность", "Metadata & privacy"), ""),
                 ("--", L("Система", "System"), ""), ("11", L("Файлы", "Files"), ""), ("12", L("История", "History"), ""), ("13", L("Сеть и диагностика", "Network & diagnostics"), ""),
                 ("14", L("Настройки", "Settings"), L("дизайн, качество, автозагрузка", "design, quality, auto-download")), ("15", L("Среда / обновление / отладка", "Environment / update / debug"), "")]
        clear_screen()
        print(status_line())
        k = menu(L("Главное меню", "Main menu"), items, back=L("Выход", "Quit"), show=False if False else True)
        if k == "q":
            print("[+] " + L("До встречи!", "See you!"))
            return
        fn = {"1": lambda: download_menu("auto"), "2": lambda: download_menu("video"), "3": lambda: download_menu("audio"), "4": lambda: download_menu("photo"), "5": queue_menu, "6": search_menu,
              "7": tools_menu, "8": collage_menu, "9": photo_menu, "10": meta_menu, "11": files_menu, "12": history_menu, "13": net_menu, "14": settings_menu, "15": env_menu}.get(k)
        if fn:
            if k in ("14", "15", "13", "11", "5"):
                try:
                    fn()
                except (Quit, KeyboardInterrupt):
                    pass
            else:
                guarded(fn)


def selftest():
    import importlib
    for mod, req in (("json", 1), ("ssl", 1), ("socket", 1), ("select", 1), ("zlib", 1), ("hashlib", 1), ("threading", 1), ("sqlite3", 0), ("readline", 0), ("termios", 0)):
        try:
            importlib.import_module(mod)
            print("OK %s" % mod)
        except Exception as e:
            print("%s %s %s" % ("FAIL" if req else "WARN", mod, str(e)[:50].replace(" ", "_")))
    try:
        import select
        select.select([], [], [], 0.01)
        socket.socket(socket.AF_INET, socket.SOCK_DGRAM).close()
        ssl.create_default_context()
        print("OK runtime")
    except Exception as e:
        print("FAIL runtime %s" % str(e)[:50].replace(" ", "_"))
    for mod in ("yt_dlp", "gallery_dl"):
        try:
            importlib.import_module(mod)
            print("OK " + mod)
        except Exception:
            print("WARN " + mod)
    print("PY %d.%d.%d" % sys.version_info[:3])
    return 0


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        sys.exit(selftest())
    try:
        main()
    except (Quit, KeyboardInterrupt):
        print("\n[+] " + L("Выход.", "Bye."))
PYEOF
echo "$MF_BUILD" > "$CORE/.ver"
fi
chmod 700 "$CORE"/*.py 2>/dev/null

# ==========================================================================
#  ЗАПУСК: окружение → главный цикл с «действиями», которые запрашивает меню
# ==========================================================================
printf '%b  ★ MediaForge  (%s)%b\n' "$C_AC" "$MF_ENV" "$C_RS"
cleanup() { [ -f "$CONF/loc.pid" ] && kill "$(cat "$CONF/loc.pid")" 2>/dev/null; rm -f "$CONF/loc.pid"; }
trap cleanup EXIT INT TERM

ensure_env

tries=0; crashes=0; sigsys=0
while [ "$tries" -lt 20 ]; do
  tries=$((tries + 1))
  rm -f "$CONF/action"
  python3 "$CORE/mediaforge.py"; rc=$?
  act=""
  if [ -f "$CONF/action" ]; then act="$(cat "$CONF/action")"; rm -f "$CONF/action"; fi
  case "$act" in
    repair)        find_alpine; install_packages; ensure_pytools; continue ;;
    upgrade_tools) run_spin "pip -U yt-dlp gallery-dl" pip_install yt-dlp gallery-dl yt-dlp-ejs; say_ok "$(T 'Инструменты обновлены.' 'Tools updated.')"; continue ;;
    nightly)       run_spin "yt-dlp nightly" pip_install --pre yt-dlp; say_ok "yt-dlp nightly"; continue ;;
    pkgupdate)     update_pkgs; continue ;;
    applyupdate)   apply_update; continue ;;
  esac
  if [ "$rc" -eq 159 ]; then
    # SIGSYS (iSH): менять Alpine бесполезно — просто перезапускаем ядро
    sigsys=$((sigsys + 1))
    say_wn "$(T 'SIGSYS (особенность iSH) — перезапуск ядра.' 'SIGSYS (iSH quirk) — restarting core.')"
    [ "$sigsys" -ge 3 ] && { say_er "$(T 'Повторные SIGSYS. Меню «Среда» → починить окружение.' 'Repeated SIGSYS.')"; exit 159; }
    continue
  fi
  if [ "$rc" -ge 128 ]; then
    crashes=$((crashes + 1))
    say_er "$(T "Python завершился аварийно (код $rc)." "Python crashed (code $rc).")"
    [ "$crashes" -ge 3 ] && { say_er "$(T 'Слишком много сбоев.' 'Too many crashes.')"; exit "$rc"; }
    find_alpine || true
    continue
  fi
  is_apk && alp_cur > "$CONF/good_alpine" 2>/dev/null
  exit "$rc"
done
say_er "$(T 'Превышено число попыток.' 'Max retries reached.')"
exit 1
