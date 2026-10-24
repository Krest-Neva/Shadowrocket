#!/bin/sh
# ==========================================================
#  MediaForge for iSH - Unified Media Toolkit
#  Полная версия: сохранён весь оригинальный функционал
#  + новые модули: фото, текст, код, метаданные, отчёты.
# ==========================================================

set -u

# --- Цвета для shell-части ---
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; BLUE='\033[0;34m'; CYAN='\033[0;36m'; MAGENTA='\033[0;35m'; NC='\033[0m'
say() { printf '%b\n' "$1"; }

# --- Стабильный DNS при старте ---
printf 'nameserver 1.1.1.1\nnameserver 8.8.8.8\nnameserver 94.140.14.14\nnameserver 9.9.9.9\n' > /etc/resolv.conf 2>/dev/null

# --- Пути и переменные окружения ---
if [ -f "$0" ]; then
    SCRIPT_DIR="$(cd "$(dirname "$0")" 2>/dev/null && pwd)"
    SCRIPT_NAME="$(basename "$0")"
    export VD_SCRIPT_PATH="$SCRIPT_DIR/$SCRIPT_NAME"
else
    export VD_SCRIPT_PATH=""
fi
export VD_UPDATE_URL="https://raw.githubusercontent.com/Krest-Neva/Shadowrocket/refs/heads/main/Scripts/ISH/VideoDownloader.py"

LANG_FILE="$HOME/.mediaforge_lang"
ALPINE_VERSION_FILE="$HOME/.mediaforge_alpine"
FAILED_ALPINES="/tmp/mf_failed_alpines"
ALPINE_DIAG="/tmp/mf_alpine_diag"
PY_FILE="/tmp/mediaforge.py"
CURRENT_ALPINE="?"

# --- Очистка временных сигнальных файлов ---
rm -f /tmp/mf_pip_cmd /tmp/mf_update_all /tmp/mf_reinstall_py /tmp/mf_self_update "$FAILED_ALPINES"
: > "$ALPINE_DIAG"

# --- Выбор языка ---
if [ -f "$LANG_FILE" ]; then
    VD_LANG=$(cat "$LANG_FILE" 2>/dev/null)
    if [ "$VD_LANG" != "en" ] && [ "$VD_LANG" != "ru" ]; then VD_LANG="ru"; fi
else
    say "${YELLOW}========================================${NC}"
    say "${YELLOW}  Language / Язык${NC}"
    say "${YELLOW}========================================${NC}"
    say "  1 - Русский [по умолчанию]"
    say "  2 - English"
    printf '%s' "Выбор / Choice [1]: "
    IFS= read -r VD_CHOICE
    if [ "$VD_CHOICE" = "2" ]; then VD_LANG="en"; else VD_LANG="ru"; fi
    echo "$VD_LANG" > "$LANG_FILE"
fi

# --- Цветной вывод по языку ---
REP() {
    case "$VD_LANG:$1" in
        en:ok)  shift; say "${GREEN}[+] $*${NC}" ;;
        en:err) shift; say "${RED}[!] $*${NC}" ;;
        en:inf) shift; say "${BLUE}[*] $*${NC}" ;;
        en:wrn) shift; say "${YELLOW}[!] $*${NC}" ;;
        ru:ok)  shift; say "${GREEN}[+] $*${NC}" ;;
        ru:err) shift; say "${RED}[!] $*${NC}" ;;
        ru:inf) shift; say "${BLUE}[*] $*${NC}" ;;
        ru:wrn) shift; say "${YELLOW}[!] $*${NC}" ;;
    esac
}
tr_msg() { if [ "$VD_LANG" = "en" ]; then echo "$2"; else echo "$1"; fi; }

# --- Фиктивный запрос геолокации (для фоновой работы iSH) ---
if [ -e /dev/location ]; then
    say "${MAGENTA}[*] $(tr_msg 'Фиктивный запрос геолокации для работы в фоне — данные не используются.' 'Dummy geolocation request for background stability — data not used.')${NC}"
    ( cat /dev/location > /dev/null 2>&1 ) &
fi

# --- Заголовок ---
say "${YELLOW}========================================${NC}"
if [ "$VD_LANG" = "en" ]; then
    say "${YELLOW}  === MediaForge for iSH ===${NC}"
    say "${YELLOW}  Unified Media Toolkit${NC}"
else
    say "${YELLOW}  === MediaForge for iSH ===${NC}"
    say "${YELLOW}  Универсальный медиа-инструмент${NC}"
fi
say "${YELLOW}========================================${NC}"

# ==========================================================
#  СПИННЕР ДЛЯ SHELL-ОПЕРАЦИЙ
# ==========================================================
run_with_spinner() {
    msg="$1"; shift
    ("$@") >/tmp/mf_spin_out 2>/tmp/mf_spin_err &
    pid=$!
    frames='|/-\'; i=0
    while kill -0 "$pid" 2>/dev/null; do
        frame=$(printf '%s' "$frames" | cut -c$(( (i % 4) + 1 )))
        printf '\r\033[0;36m%s\033[0m %s... ' "$frame" "$msg" >&2
        i=$((i + 1)); sleep 0.15
    done
    wait "$pid" 2>/dev/null; rc=$?
    printf '\r\033[K' >&2
    return $rc
}

# ==========================================================
#  РЕПОЗИТОРИИ ALPINE
# ==========================================================
set_repos() {
    ver=$1
    printf 'https://dl-cdn.alpinelinux.org/alpine/v%s/main\nhttps://dl-cdn.alpinelinux.org/alpine/v%s/community\n' "$ver" "$ver" > /etc/apk/repositories
    if ! apk update >/dev/null 2>&1; then
        # Fallback: зеркало Yandex
        printf 'https://mirror.yandex.ru/mirrors/alpine/v%s/main\nhttps://mirror.yandex.ru/mirrors/alpine/v%s/community\n' "$ver" "$ver" > /etc/apk/repositories
        if ! apk update >/dev/null 2>&1; then
            return 1
        fi
    fi
    return 0
}

python_ok() {
    command -v python3 >/dev/null 2>&1 || return 1
    python3 -c 'import sys; sys.exit(0 if sys.version_info >= (3,10) else 1)' >/dev/null 2>&1
}

# ==========================================================
#  УСТАНОВКА PYTHON (3 ВАРИАНТА С ПОЛНОЙ ПЕРЕУСТАНОВКОЙ)
# ==========================================================
_apk_python() {
    ver=$1
    if ! set_repos "$ver"; then
        echo "Alpine $ver: repos failed" >> "$ALPINE_DIAG"
        return 1
    fi
    if ! apk update >/dev/null 2>&1; then
        echo "Alpine $ver: apk update failed" >> "$ALPINE_DIAG"
        return 1
    fi

    # Уже подходящая версия?
    if python_ok; then
        return 0
    fi

    # ВАЖНО: перед сменой версии полностью удаляем старые пакеты
    # чтобы избежать конфликтов версий musl/python
    apk del python3 py3-pip >/dev/null 2>&1 || true

    # Вариант 1: установка python3
    apk add --no-cache python3 py3-pip >/dev/null 2>&1 || true
    if python_ok; then
        return 0
    fi

    # Вариант 2: полное обновление системы (musl и т.п.)
    apk upgrade --available --no-cache >/dev/null 2>&1 || true
    if python_ok; then
        return 0
    fi

    # Вариант 3: повторная попытка после upgrade
    apk del python3 py3-pip >/dev/null 2>&1 || true
    apk add --no-cache python3 py3-pip >/dev/null 2>&1 || {
        echo "Alpine $ver: apk add failed" >> "$ALPINE_DIAG"
        return 1
    }
    if python_ok; then
        return 0
    fi

    pyv=$(python3 --version 2>&1 | awk '{print $2}')
    echo "Alpine $ver: got Python $pyv (need 3.10+)" >> "$ALPINE_DIAG"
    return 1
}

pick_alpine() {
    saved=$(cat "$ALPINE_VERSION_FILE" 2>/dev/null || echo "")
    # 3.18 — самая стабильная для iSH по отчётам сообщества
    for ver in $saved 3.18 3.19 3.20 3.17 3.21 3.16 3.15 3.14; do
        [ -n "$ver" ] || continue
        if grep -qx "$ver" "$FAILED_ALPINES" 2>/dev/null; then
            continue
        fi
        REP inf "$(tr_msg "Пробую Alpine $ver..." "Trying Alpine $ver...")"
        if run_with_spinner "Alpine $ver" _apk_python "$ver"; then
            echo "$ver" > "$ALPINE_VERSION_FILE"
            CURRENT_ALPINE="$ver"
            return 0
        fi
        echo "$ver" >> "$FAILED_ALPINES"
    done
    return 1
}

# ==========================================================
#  FFMPEG LD_PRELOAD ХАК (ОБХОД BAD SYSTEM CALL)
# ==========================================================
ff_works() { ( "$1" -version ) >/dev/null 2>&1; }

fix_ffmpeg() {
    if command -v ffmpeg >/dev/null 2>&1 && ff_works ffmpeg; then
        return 0
    fi
    REAL_FF=/usr/bin/ffmpeg
    [ -x "$REAL_FF" ] || REAL_FF=$(command -v ffmpeg 2>/dev/null)
    if [ -z "$REAL_FF" ] || [ "$REAL_FF" = "/usr/local/bin/ffmpeg" ]; then
        return 1
    fi
    REP wrn "$(tr_msg 'ffmpeg сломан (Bad system call), готовлю LD_PRELOAD хак...' 'ffmpeg broken, preparing LD_PRELOAD hack...')"
    HACK_C="/tmp/ffmpeg-hack.c"
    HACK_SO="/usr/local/lib/ffmpeg-hack.so"
    mkdir -p /usr/local/lib /usr/local/bin
    if [ ! -s "$HACK_SO" ]; then
        apk add --no-cache gcc musl-dev >/dev/null 2>&1 || true
        curl -fsSL "https://raw.githubusercontent.com/tjcaul/iSH-LD_PRELOAD-Hack/main/ffmpeg-hack.c" -o "$HACK_C" 2>/dev/null || true
        if [ ! -s "$HACK_C" ]; then
            REP err "Could not download ffmpeg-hack.c"; return 1
        fi
        if ! gcc -O2 -shared -fPIC -o "$HACK_SO" "$HACK_C" -ldl >/dev/null 2>&1; then
            REP err "Could not compile ffmpeg-hack.so"; return 1
        fi
    fi
    cat > /usr/local/bin/ffmpeg << WRAP_EOF
#!/bin/sh
exec env LD_PRELOAD="$HACK_SO" "$REAL_FF" "\$@"
WRAP_EOF
    chmod +x /usr/local/bin/ffmpeg
    REAL_FP=/usr/bin/ffprobe
    [ -x "$REAL_FP" ] || REAL_FP=""
    if [ -n "$REAL_FP" ]; then
        cat > /usr/local/bin/ffprobe << WRAP_FP_EOF
#!/bin/sh
exec env LD_PRELOAD="$HACK_SO" "$REAL_FP" "\$@"
WRAP_FP_EOF
        chmod +x /usr/local/bin/ffprobe
    fi
    if ff_works ffmpeg; then
        REP ok "ffmpeg LD_PRELOAD OK"
        return 0
    fi
    REP err "ffmpeg still broken"; return 1
}

# ==========================================================
#  УСТАНОВКА ПАКЕТОВ (РАСШИРЕННЫЙ НАБОР)
# ==========================================================
install_packages() {
    run_with_spinner "apk update" apk update >/dev/null 2>&1 || true
    # Медиа, метаданные, текст, код, анализ
    for pkg in python3 py3-pip curl wget ca-certificates nodejs ffmpeg ffprobe \
               exiftool imagemagick imagemagick-jpeg imagemagick-webp imagemagick-tiff \
               aspell aspell-ru aspell-en shellcheck \
               sox mediainfo gpac opus-tools flac lame; do
        if apk info -e "$pkg" >/dev/null 2>&1; then
            REP ok "$pkg $(tr_msg 'уже установлен' 'already installed')"
            continue
        fi
        if run_with_spinner "Installing $pkg" apk add --no-cache "$pkg"; then
            REP ok "$pkg $(tr_msg 'установлен' 'installed')"
        else
            REP wrn "$pkg $(tr_msg 'не установился (не критично)' 'failed (non-critical)')"
        fi
    done
}

pip_install() {
    python3 -m pip install -U --no-deps --break-system-packages "$@" >/tmp/mf_pip.log 2>&1 \
        || python3 -m pip install -U --no-deps "$@" >>/tmp/mf_pip.log 2>&1
}

ensure_python_tools() {
    # yt-dlp, tqdm, yt-dlp-ejs, gallery-dl, rich, ruff (замена black/flake8/isort)
    if ! python3 -c 'import yt_dlp, tqdm' >/dev/null 2>&1; then
        run_with_spinner "pip: yt-dlp" pip_install yt-dlp tqdm
    fi
    if ! python3 -c 'import yt_dlp_ejs' >/dev/null 2>&1; then
        run_with_spinner "pip: yt-dlp-ejs" python3 -m pip install -U --break-system-packages yt-dlp-ejs >/dev/null 2>&1 \
            || python3 -m pip install -U yt-dlp-ejs >/dev/null 2>&1 || true
    fi
    if ! python3 -c 'import gallery_dl' >/dev/null 2>&1; then
        run_with_spinner "pip: gallery-dl" pip_install gallery-dl
    fi
    if ! python3 -c 'import rich' >/dev/null 2>&1; then
        run_with_spinner "pip: rich" pip_install rich
    fi
    if ! python3 -c 'import ruff' >/dev/null 2>&1; then
        run_with_spinner "pip: ruff" pip_install ruff
    fi
    # Итоговый отчёт по версиям
    YTV=$(python3 -c 'import yt_dlp; print(yt_dlp.version.__version__)' 2>/dev/null || echo "?")
    REP ok "yt-dlp $YTV"
    if python3 -c 'import yt_dlp_ejs' >/dev/null 2>&1; then REP ok "yt-dlp-ejs"; fi
    if python3 -c 'import gallery_dl' >/dev/null 2>&1; then REP ok "gallery-dl"; fi
    if python3 -c 'import rich' >/dev/null 2>&1; then REP ok "rich"; fi
    if python3 -c 'import ruff' >/dev/null 2>&1; then REP ok "ruff"; fi
}

show_versions() {
    PYV=$(python3 --version 2>&1 | awk '{print $2}')
    REP ok "python3 $PYV (Alpine $CURRENT_ALPINE)"
    if command -v ffmpeg >/dev/null 2>&1 && ff_works ffmpeg; then
        FFV=$(ffmpeg -version 2>/dev/null | head -1 | awk '{print $3}')
        REP ok "ffmpeg $FFV"
    else
        REP wrn "$(tr_msg 'ffmpeg не работает — только комбинированные форматы' 'ffmpeg not functional — combined formats only')"
    fi
    if command -v exiftool >/dev/null 2>&1; then
        EXV=$(exiftool -ver 2>/dev/null)
        REP ok "exiftool $EXV"
    fi
    if command -v convert >/dev/null 2>&1; then
        IMV=$(convert -version 2>/dev/null | head -1 | awk '{print $3}')
        REP ok "imagemagick $IMV"
    fi
    if command -v aspell >/dev/null 2>&1; then
        REP ok "aspell $(aspell --version 2>/dev/null | head -1 | awk '{print $2}')"
    fi
}

setup_environment() {
    install_packages
    fix_ffmpeg || true
    ensure_python_tools
    show_versions
}

switch_env() {
    [ -n "$CURRENT_ALPINE" ] && [ "$CURRENT_ALPINE" != "?" ] && echo "$CURRENT_ALPINE" >> "$FAILED_ALPINES"
    if ! pick_alpine; then return 1; fi
    setup_environment
    return 0
}

# ==========================================================
#  ПЕРВИЧНЫЙ ВЫБОР ALPINE
# ==========================================================
if ! python_ok; then
    REP inf "$(tr_msg 'Поиск рабочей версии Alpine с Python 3.10+...' 'Finding working Alpine with Python 3.10+...')"
    if ! pick_alpine; then
        REP err "$(tr_msg 'Не найдено рабочей версии Alpine' 'No working Alpine version found')"
        if [ -s "$ALPINE_DIAG" ]; then
            REP inf "$(tr_msg 'Диагностика:' 'Diagnostics:')"
            sed 's/^/    /' "$ALPINE_DIAG"
        fi
        REP inf "$(tr_msg 'Ручной фикс:' 'Manual fix:')"
        say "    printf 'https://dl-cdn.alpinelinux.org/alpine/v3.18/main\\nhttps://dl-cdn.alpinelinux.org/alpine/v3.18/community\\n' > /etc/apk/repositories"
        say "    apk update && apk upgrade --available"
        say "    apk del python3 py3-pip && apk add --no-cache python3 py3-pip"
        say "    python3 --version   # должно быть 3.11.x"
        exit 1
    fi
    REP ok "$(tr_msg "Alpine $CURRENT_ALPINE работает" "Alpine $CURRENT_ALPINE works")"
else
    CURRENT_ALPINE=$(cat "$ALPINE_VERSION_FILE" 2>/dev/null || echo "?")
fi

setup_environment

command -v python3 >/dev/null 2>&1 || { REP err "python3 missing"; exit 1; }
python_ok || {
    REP err "$(tr_msg 'Python установлен, но версия < 3.10 — запустите скрипт ещё раз' 'Python installed but < 3.10 — rerun the script')"
    exit 1
}

export PYTHONUTF8=1
export PYTHONIOENCODING=utf-8
export PYTHONHASHSEED=0

# ==========================================================
#  ВСТРОЕННЫЙ PYTHON-СКРИПТ (ЧАСТЬ 2/2)
#  См. следующее сообщение — вставьте содержимое между
#  маркерами << 'PYEOF' и PYEOF сюда, сохранив их.
# ==========================================================

cat > "$PY_FILE" << 'PYEOF'
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# MediaForge for iSH — Full Python Core (Part 2A)
import sys, os, re, json, time, ssl, socket, struct, random, shutil, subprocess, importlib.util, csv, hashlib, uuid, glob
import urllib.request, urllib.error
from pathlib import Path
from urllib.parse import urlparse, quote

# Опциональные модули
try: import yt_dlp
except ImportError: yt_dlp = None
try: from tqdm import tqdm
except ImportError: tqdm = None
try:
    from rich.console import Console
    from rich.progress import Progress as RProgress, BarColumn, TextColumn, TimeRemainingColumn, DownloadColumn, TransferSpeedColumn
    HAS_RICH = True
except ImportError:
    HAS_RICH = False

HOME = Path.home()
LANG_FILE = HOME / ".mediaforge_lang"
SETTINGS_FILE = HOME / ".mediaforge_settings.json"
SCRIPT_PATH = os.environ.get("VD_SCRIPT_PATH", "")
UPDATE_URL = os.environ.get("VD_UPDATE_URL", "")
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
RED, GREEN, YELLOW, BLUE, CYAN, MAGENTA, NC = "\033[0;31m","\033[0;32m","\033[1;33m","\033[0;34m","\033[0;36m","\033[0;35m","\033[0m"
ACTION_PIP_FILE = "/tmp/mf_pip_cmd"
ACTION_UPDATE_ALL_FILE = "/tmp/mf_update_all"
ACTION_REINSTALL_PY_FILE = "/tmp/mf_reinstall_py"
ACTION_SELF_UPDATE_FILE = "/tmp/mf_self_update"

# Глобальные константы
DIRECT = ("youtube.com/","youtu.be/","rutube.ru/video/","rutube.ru/play/",".mp4",".m3u8")
SEEN_ERRORS = set()
OUT_TMPL = "%(title).150B [%(id)s].%(ext)s"
JS_BIN = {"deno":"deno","node":"node","bun":"bun","quickjs":"qjs"}
YT_CLIENT_SEQ = [[],["tv"],["android_vr"],["web_safari"],["mweb"],["ios"],["android"]]
VIDEO_EXTS = (".mp4",".mkv",".webm",".mov",".m4v",".avi",".flv",".ts")
AUDIO_EXTS = (".mp3",".m4a",".opus",".flac",".ac3",".aac",".ogg",".wav",".weba")
PHOTO_EXTS = (".jpg",".jpeg",".png",".webp",".heic",".tiff",".bmp",".gif")
TEXT_EXTS = (".txt",".md",".log",".csv",".json",".xml",".html")
CODE_EXTS = (".py",".sh",".js",".html",".css",".c",".cpp",".go",".rs",".rb",".php",".ts")
_encoders_cache = None
OP = {"active": False}
INPUT_STATE = {"timeout": False}
PP = {"timed_out": False}
LAST_PRIO = {"video": "mp4", "audio": "m4a"}
ANSI_RE = re.compile(r'\x1b(?:\[[0-9;?]*[A-Za-z~]|O[A-Za-z])')
CTRL_RE = re.compile(r'[\x00-\x08\x0b-\x1f\x7f]')

# Базовые функции очистки и печати
def clean_input(s):
    if s is None: return None
    s = ANSI_RE.sub('', str(s)); s = CTRL_RE.sub('', s); return s.replace('\r','').replace('\n',' ').strip()
def c(t, col): return f"{col}{t}{NC}"
def info_line(m): print(c("[*] " + str(m), BLUE))
def ok_line(m): print(c("[+] " + str(m), GREEN))
def warn_line(m): print(c("[!] " + str(m), YELLOW))
def err_line(m): print(c("[!] " + str(m), RED))
def mag_line(m): print(c("[*] " + str(m), MAGENTA))
def err_unique(m):
    msg = str(m).strip()
    if not msg or msg in SEEN_ERRORS: return
    SEEN_ERRORS.add(msg); err_line(msg)
def show_msgs(text):
    for raw in str(text or "").splitlines():
        line = ANSI_RE.sub("", raw).strip()
        if not line or "Deprecated Feature" in line or "Support for Python version" in line: continue
        is_warn = line.startswith("WARNING"); norm = re.sub(r"^(ERROR|WARNING):\s*", "", line).strip()
        if not norm or norm in SEEN_ERRORS: continue
        SEEN_ERRORS.add(norm); (warn_line if is_warn else err_line)(norm)
def header(title):
    print(c("="*40, YELLOW)); print(c("  " + str(title), YELLOW)); print(c("="*40, YELLOW))
def banner(title, sub=""):
    print(c("╔" + "═"*42 + "╗", CYAN)); print(c("║  " + title.ljust(40) + "║", CYAN))
    if sub: print(c("║  " + sub.ljust(40) + "║", CYAN))
    print(c("╚" + "═"*42 + "╝", CYAN))
def signal_action(path, data=None):
    try:
        p = Path(path)
        if data is not None: p.write_text(data, encoding="utf-8")
        else: p.touch()
        return True
    except Exception as e: err_line(f"signal_action: {e}"); return False

# Загрузка языка
if LANG_FILE.exists():
    try:
        _l = LANG_FILE.read_text(encoding="utf-8").strip(); LANG = _l if _l in ("ru","en") else "ru"
    except Exception: LANG = "ru"
else: LANG = "ru"

# Обнаружение ffmpeg/ffprobe
def _detect_bin(name):
    cands = []
    w = shutil.which(name)
    if w: cands.append(w)
    for p in (f"/usr/local/bin/{name}", f"/usr/bin/{name}", f"/bin/{name}"):
        if p not in cands and os.path.exists(p): cands.append(p)
    for p in cands:
        if os.path.exists(p) and os.access(p, os.X_OK):
            try:
                r = subprocess.run([p, "-version"], capture_output=True, timeout=30)
                if r.returncode == 0 and (name + " version").encode() in r.stdout: return p
            except Exception: pass
    return None
FFMPEG_BIN = _detect_bin("ffmpeg"); FFPROBE_BIN = _detect_bin("ffprobe"); HAS_FFMPEG = FFMPEG_BIN is not None
def refresh_ffmpeg():
    global FFMPEG_BIN, FFPROBE_BIN, HAS_FFMPEG, _encoders_cache
    nf = _detect_bin("ffmpeg"); np_ = _detect_bin("ffprobe")
    if nf != FFMPEG_BIN:
        FFMPEG_BIN, FFPROBE_BIN, HAS_FFMPEG = nf, np_, nf is not None
        _encoders_cache = None
        if HAS_FFMPEG: ok_line(f"ffmpeg: {nf}")

# ============ TEXTS: ПОЛНЫЕ ПЕРЕВОДЫ RU+EN ============
TEXTS = {
"ru": {
    "app_title":"MediaForge — универсальный медиа-инструмент",
    "menu_download_video":"Скачать видео","menu_download_audio":"Скачать аудио",
    "menu_download_photo":"Скачать фото / галерею","menu_search":"Поиск видео",
    "menu_reencode":"Перекодировать готовые файлы","menu_files":"Управление файлами",
    "menu_settings":"Настройки","menu_diag":"Диагностика сети","menu_update":"Обновить инструменты",
    "menu_selfupdate":"Обновить скрипт с GitHub","menu_debug":"Отладка (все версии и настройки)",
    "menu_photo_edit":"Редактировать фото","menu_photo_meta":"Метаданные фото",
    "menu_text":"Работа с текстом","menu_code":"Работа с кодом",
    "menu_metadata":"Метаданные (видео/аудио/фото)","menu_advanced":"Расширенные медиа-инструменты",
    "menu_privacy":"Приватность (шифрование/хэши/дубликаты)","menu_reports":"Отчёты и аудит",
    "menu_profiles":"Профили / пресеты","menu_batch":"Пакетный режим (без вопросов)",
    "menu_exit":"Выход (q)","choice":"Ваш выбор","invalid_choice":"Неверный выбор",
    "videos_dir":"Видео","audio_dir":"Аудио","photos_dir":"Фото","text_dir":"Текст","code_dir":"Код",
    "enter_urls":"Введите ссылки (по одной на строку).",
    "enter_urls_hint":"Пустая строка — начать. 'q' — меню.",
    "cancel_hint":"Ctrl+C — отменить и вернуться в главное меню",
    "interrupted":"Операция отменена, возврат в главное меню","kept_files":"Уже скачанные файлы сохранены",
    "input_timeout":"Время ожидания ответа истекло","pp_skip_hint":"Нет ответа — остальные вопросы пропущены",
    "post_process":"Завершение: конвертация, переименование, fix","available_formats":"Доступные форматы видео",
    "select_video":"Номер видеоформата (Enter — лучший)","select_audio_track":"Номер аудиодорожки (Enter — лучшая)",
    "invalid_default":"Неверный выбор, формат по умолчанию",
    "prio_video_title":"Приоритетный формат видео (при неудаче будут перебраны остальные)",
    "prio_audio_title":"Приоритетный формат аудио (при неудаче будут перебраны остальные)",
    "prio_v_mp4":"MP4 / H.264 + AAC (самый совместимый)","prio_v_vp9":"VP9 + Opus (в MKV)",
    "prio_v_av1":"AV1 (в MKV)","prio_v_any":"Любой лучший формат","prio_v_manual":"Выбрать вручную из списка",
    "prio_a_m4a":"M4A / AAC","prio_a_opus":"Opus / WebM","prio_a_mp3":"MP3","prio_a_any":"Любой лучший",
    "selector":"Селектор","strategy":"Способ","trying_generic":"Пробую generic-экстрактор...",
    "trying_binary":"Пробую yt-dlp отдельным процессом...","trying_external":"Прямая загрузка...",
    "trying_rutube":"RuTube API напрямую...","retry_tls":"Повторить без проверки TLS?",
    "all_exhausted":"Все попытки исчерпаны","fail_hint":"Что попробовать: меню 8, прокси, cookies, клиенты YouTube, другой приоритет.",
    "failed_summary":"Не удалось скачать","file_not_found":"Скачанный файл не найден",
    "info_failed":"Не удалось получить информацию, пробую напрямую","network_unavailable":"Сеть недоступна",
    "scanning":"Сканирование страницы","found_videos":"Найдено видео","no_videos":"Видео не найдены",
    "multiple_videos":"Найдено несколько видео","number_or_all":"Номера (1,3-5 или all)",
    "invalid_url":"Некорректная ссылка","stopped":"Работа остановлена","extracting":"Извлечение информации",
    "downloading":"Начинаю скачивание","download_done":"Скачано",
    "no_ffmpeg_warn":"ffmpeg не работает — только комбинированные форматы",
    "search_where":"Где искать?","search_other":"Другой сайт (ссылка на страницу)",
    "search_query":"Введите поисковый запрос","search_results":"Результаты поиска",
    "search_select":"Номера (1,3-5 или all; Enter — отмена)","search_searching":"Ищу",
    "search_empty":"Ничего не найдено","search_failed":"Поиск не удался",
    "search_url":"Ссылка на страницу со списком видео","search_kind":"1 — видео, 2 — аудио [1]",
    "fm_title":"Управление файлами","fm_choose_dir":"Выберите папку",
    "fm_videos":"videos","fm_audio":"audio","fm_photos":"photos","fm_text":"text","fm_code":"code","fm_fix":"fix",
    "fm_back":"Назад","fm_empty":"Папка пуста","fm_delete":"Удалить","fm_delete_multi":"Удалить несколько",
    "fm_delete_all":"Удалить все","fm_rename":"Переименовать","fm_move_to_fix":"В fix",
    "fm_restore":"Вернуть из fix","fm_deleted":"Удалено","fm_failed":"Ошибка","fm_numbers":"Номера",
    "fm_new_name":"Новое имя","fm_renamed":"Переименовано","fm_moved":"Перемещено",
    "fm_file_index":"Номер файла","fm_exists":"Файл уже существует",
    "settings_title":"Настройки","grp_media":"Видео и аудио","grp_network":"Сеть и YouTube",
    "grp_interface":"Интерфейс и папки","grp_new":"Новые модули (фото/текст/код)",
    "set_reset":"Сбросить настройки","set_saved":"Сохранено",
    "set_enter_value":"Новое значение (Enter — оставить, '-' — очистить)","set_bad_value":"Недопустимое значение",
    "set_video_codec":"Видеокодек","set_audio_codec":"Аудиокодек",
    "set_max_height":"Макс. высота (0 — без ограничения)","set_auto_convert":"Конвертация несовместимых",
    "set_concurrent_fragments":"Параллельных фрагментов","set_cookies_file":"Файл cookies",
    "set_proxy":"Прокси","set_dns_mode":"Режим DNS","set_dns_servers":"DNS-серверы",
    "set_doh_url":"DoH-адрес","set_doh_fallback":"DoH fallback","set_ip_version":"Предпочтение IP",
    "set_verify_tls":"Проверка TLS","set_preflight":"Предпроверка сети","set_socket_timeout":"Таймаут, сек",
    "set_retries":"Повторов","set_yt_clients":"Клиенты YouTube","set_js_runtime":"JS-движок",
    "set_remote_ejs":"EJS с GitHub","set_progress_width":"Ширина прогресса",
    "set_ask_rename":"Спрашивать переименование","set_ask_fix":"Спрашивать перенос в fix",
    "set_prompt_timeout":"Таймаут ответа, сек","set_base_dir":"Основная папка","set_language":"Язык",
    "set_unattended":"Автономный режим (без подтверждений)","set_photo_max_width":"Макс. ширина фото (0 — без)",
    "set_photo_quality":"Качество JPEG (1-100)","set_code_auto_fix":"Авто-исправление кода",
    "set_spell_lang":"Язык орфографии (ru/en/both)","set_metadata_template":"Шаблон метаданных",
    "opt_auto":"авто","opt_system":"system","opt_udp":"udp","opt_doh":"doh","opt_none":"нет",
    "opt_ask":"спрашивать","opt_always":"всегда","opt_never":"никогда","opt_deno":"deno","opt_node":"node",
    "opt_bun":"bun","opt_quickjs":"quickjs","opt_ipv4":"IPv4","opt_ipv6":"IPv6",
    "on":"вкл","off":"выкл","unlimited":"без ограничения","empty":"не задано",
    "preset_iphone":"iPhone (H.264 + AAC)","preset_android":"Android (H.264 + AAC)",
    "preset_universal":"Универсальный (H.264 Baseline)","preset_h265":"H.265 / HEVC",
    "preset_vp9":"VP9","preset_av1":"AV1","preset_original":"Оригинал",
    "audio_aac":"AAC 128k","audio_ac3":"AC3 192k","audio_mp3":"MP3 192k","audio_opus":"Opus 160k",
    "audio_flac":"FLAC","audio_original":"Оригинал","lang_ru":"Русский","lang_en":"English",
    "video_ready":"Видео готово","audio_ready":"Аудио готово","file":"Файл","size":"Размер",
    "rename_prompt":"Переименовать?","move_fix_prompt":"В fix (если не открывается)?",
    "converting":"Конвертация","convert_prompt":"Конвертировать?","convert_done":"Конвертация завершена",
    "convert_failed":"Ошибка конвертации","convert_cancelled":"Отменено",
    "ffmpeg_missing":"ffmpeg не найден","compat_warning":"Формат может быть несовместим",
    "encoder_missing":"Кодек не поддерживается","reenc_keep":"Оставить оригинал?",
    "reenc_done":"Перекодировано","reenc_skipped":"Перекодирование не требуется",
    "preflight_title":"Проверка сети","preflight_ok":"Сеть ОК, DNS",
    "preflight_fail":"TLS не удалось","preflight_blocked":"Похоже на DPI. Нужен прокси/VPN.",
    "preflight_continue":"Попробовать всё равно?","net_help":"Сетевые ошибки. Задайте прокси или Enter.",
    "proxy_prompt":"Прокси","proxy_invalid":"Неверный формат","proxy_set":"Прокси сохранён",
    "diag_title":"Диагностика сети","diag_system":"система","diag_fail":"нет ответа",
    "diag_mismatch":"DNS-ответы различаются","diag_tls_ok":"TLS ОК","diag_tls_fail":"TLS провал",
    "diag_proxy":"Проверка прокси","diag_proxy_socks":"SOCKS проверяется при загрузке",
    "diag_press":"Enter — продолжить","diag_what":"Какую диагностику провести?",
    "diag_quick":"Быстрая (все хосты, system DNS)","diag_dns_full":"Полная DNS (все серверы + DoH)",
    "diag_tls_only":"Только TLS (все хосты)","diag_proxy_only":"Только прокси",
    "diag_custom":"Свой список хостов","diag_all":"Все тесты",
    "upd_title":"Обновление инструментов","upd_stable":"yt-dlp стабильная","upd_nightly":"yt-dlp Nightly",
    "upd_ejs":"Только yt-dlp-ejs","upd_all_tools":"Обновить ВСЁ (apk upgrade + pip)",
    "upd_reinstall_python":"Переустановить Python (подобрать Alpine)",
    "js_none":"JS-движок не найден","rutube_no_m3u8":"RuTube: нет m3u8","ytdlp_missing":"yt-dlp нет","dl_dest":"Сохранено в",
    "selfupd_title":"Обновление скрипта","selfupd_checking":"Проверка GitHub",
    "selfupd_uptodate":"Уже последняя версия","selfupd_check_failed":"Не удалось проверить",
    "selfupd_prompt":"Скачать и обновить скрипт?","selfupd_done":"Скрипт обновлён, перезапуск",
    "selfupd_invalid":"Неверный формат файла","selfupd_no_path":"Не удалось определить путь",
    "selfupd_downloading":"Скачивание новой версии",
    "templates_custom":"Ввести вручную","templates_multi_hint":"Можно: 2 или 1,3,5 или 1-3 или all",
    "debug_title":"Отладочная информация","debug_press":"Enter — продолжить",
    "debug_versions":"Версии инструментов","debug_py_pkgs":"Python-пакеты","debug_settings":"Все настройки",
    "debug_dirs":"Папки","debug_binaries":"Бинарники","debug_env":"Окружение",
    "photo_download_ok":"Фото скачаны в","photo_edit_menu":"Редактирование фото",
    "photo_resize":"Изменить размер","photo_crop":"Обрезать","photo_rotate":"Повернуть",
    "photo_convert":"Сменить формат","photo_auto_orient":"Повернуть по EXIF",
    "photo_enter_size":"Размер (например 800x600 или 50%)","photo_enter_crop":"Геометрия (100x100+10+10)",
    "photo_enter_angle":"Угол (90, 180, -90)","photo_enter_ext":"Новый формат (jpg/png/webp)",
    "photo_src_local":"Локальный файл","photo_src_download":"Скачать по ссылке",
    "photo_created":"Создан","photo_applied":"Применено",
    "text_title":"Работа с текстом","text_download":"Скачать текст по ссылке",
    "text_local":"Открыть локальный файл","text_spell":"Проверить орфографию",
    "text_search":"Поиск по тексту","text_edit":"Простое редактирование",
    "text_lang":"Язык (ru/en/both) [ru]:","text_enter_url":"URL текстового файла",
    "text_enter_path":"Путь к файлу","text_enter_query":"Строка для поиска",
    "text_spell_ok":"Ошибок не найдено","text_spell_found":"Найдены возможные ошибки",
    "text_search_found":"Найдено совпадений","text_search_none":"Не найдено",
    "text_saved":"Файл сохранён","text_downloaded":"Текст скачан",
    "code_title":"Работа с кодом","code_fix":"Авто-исправление (ruff/shellcheck)",
    "code_scan":"Только анализ (без правки)","code_enter_path":"Путь к файлу кода",
    "code_lang_unknown":"Нет инструмента для этого языка","code_fixed":"Код исправлен",
    "code_errors":"Найдены ошибки","code_clean":"Ошибок нет",
    "meta_title":"Метаданные","meta_view":"Просмотреть метаданные",
    "meta_strip_all":"Удалить ВСЕ метаданные","meta_strip_selective":"Удалить выборочные теги",
    "meta_set_template":"Применить шаблон","meta_verify":"Проверить после очистки",
    "meta_deep_clean":"Глубокая очистка (XMP/IPTC/ICC/thumbnails)",
    "meta_gps_preview":"Предпросмотр GPS (OpenStreetMap)","meta_dir_or_file":"Путь к папке или файлу",
    "meta_tags_select":"Номера тегов для удаления","meta_template_select":"Шаблон",
    "meta_done":"Обработано файлов","meta_strip_ok":"Метаданные удалены",
    "meta_strip_fail":"Не удалось удалить метаданные","meta_not_found":"Метаданные не найдены",
    "meta_tpl_anon":"Полная анонимность","meta_tpl_camera":"Только камера","meta_tpl_date":"Дата и время",
    "meta_tpl_author":"Авторское право","meta_tpl_software":"ПО","meta_tpl_gps":"Геолокация (очистить)",
    "adv_title":"Расширенные медиа-инструменты","adv_extract_audio":"Извлечь аудио из видео",
    "adv_make_gif":"Создать GIF из видео","adv_thumbnail":"Извлечь кадр-превью",
    "adv_concat":"Склеить видео","adv_split":"Разбить видео","adv_loudnorm":"Нормализовать громкость",
    "adv_compress":"Сжать медиа","adv_enter_src":"Исходный файл","adv_enter_out":"Выходной файл",
    "adv_enter_time":"Время (HH:MM:SS)","adv_enter_duration":"Длительность сегмента, сек",
    "adv_enter_paths":"Пути через запятую (для склейки)","adv_done":"Готово",
    "priv_title":"Приватность","priv_uuid":"Переименовать в UUID","priv_encrypt":"Шифровать (gpg/openssl)",
    "priv_shred":"Безопасно удалить (затереть)","priv_sha256":"SHA-256 хэши",
    "priv_dups":"Найти дубликаты","priv_enter_path":"Путь к файлу/папке",
    "priv_warn":"ВНИМАНИЕ: необратимая операция","priv_confirm":"Продолжить?",
    "priv_renamed":"Переименовано","priv_encrypted":"Зашифровано","priv_shredded":"Затёрто",
    "priv_hashed":"Хэши","priv_dups_found":"Найдено групп дубликатов",
    "rep_title":"Отчёты и аудит","rep_csv":"CSV-отчёт по папке","rep_json":"JSON-отчёт",
    "rep_prescan":"Пред-скан папки (сводка)","rep_enter_dir":"Путь к папке",
    "rep_saved":"Отчёт сохранён","rep_summary":"Сводка",
    "prof_title":"Профили / пресеты","prof_apply":"Применить профиль","prof_save":"Сохранить текущие как профиль",
    "prof_default":"Обычный","prof_social":"Соцсети (без GPS/мета, resize 1920)",
    "prof_paranoid":"Параноик (полная очистка + UUID + шифрование)",
    "prof_archive":"Архив (оригиналы)","prof_applied":"Профиль применён",
    "batch_title":"Пакетный режим","batch_enter_urls":"URL по одному на строку (или путь к файлу .txt)",
    "batch_hint":"Всё будет скачано и обработано без вопросов. Авто-выбор лучшего формата.",
    "batch_kind":"1 — видео, 2 — аудио, 3 — фото [1]","batch_done":"Пакетная обработка завершена",
    "batch_summary":"Итог пакетной обработки","batch_ok":"Успешно","batch_fail":"С ошибками",
    "unattended_on":"Автономный режим: ВКЛ (без вопросов)","unattended_off":"Автономный режим: ВЫКЛ",
},
"en": {
    "app_title":"MediaForge — Unified Media Toolkit",
    "menu_download_video":"Download video","menu_download_audio":"Download audio",
    "menu_download_photo":"Download photos / gallery","menu_search":"Search video",
    "menu_reencode":"Reencode ready files","menu_files":"File manager",
    "menu_settings":"Settings","menu_diag":"Network diagnostics","menu_update":"Update tools",
    "menu_selfupdate":"Update script from GitHub","menu_debug":"Debug (all versions and settings)",
    "menu_photo_edit":"Edit photos","menu_photo_meta":"Photo metadata",
    "menu_text":"Text tools","menu_code":"Code tools",
    "menu_metadata":"Metadata (video/audio/photo)","menu_advanced":"Advanced media tools",
    "menu_privacy":"Privacy (encrypt/hash/dedup)","menu_reports":"Reports & audit",
    "menu_profiles":"Profiles / presets","menu_batch":"Batch mode (no prompts)",
    "menu_exit":"Exit (q)","choice":"Choice","invalid_choice":"Invalid choice",
    "videos_dir":"Videos","audio_dir":"Audio","photos_dir":"Photos","text_dir":"Text","code_dir":"Code",
    "enter_urls":"Enter URLs (one per line).","enter_urls_hint":"Empty line — start. 'q' — menu.",
    "cancel_hint":"Ctrl+C — cancel and return to menu","interrupted":"Cancelled","kept_files":"Kept files",
    "input_timeout":"Answer timeout","pp_skip_hint":"No answer — skipped",
    "post_process":"Finishing","available_formats":"Available formats",
    "select_video":"Format number (Enter = best)","select_audio_track":"Audio track number (Enter = best)",
    "invalid_default":"Invalid choice","prio_video_title":"Priority video format (others tried if fail)",
    "prio_audio_title":"Priority audio format (others tried if fail)",
    "prio_v_mp4":"MP4 / H.264 + AAC","prio_v_vp9":"VP9 + Opus (MKV)","prio_v_av1":"AV1 (MKV)",
    "prio_v_any":"Any best","prio_v_manual":"Manual selection",
    "prio_a_m4a":"M4A / AAC","prio_a_opus":"Opus","prio_a_mp3":"MP3","prio_a_any":"Any best",
    "selector":"Selector","strategy":"Method","trying_generic":"Trying generic...",
    "trying_binary":"Trying yt-dlp binary...","trying_external":"Direct download...",
    "trying_rutube":"RuTube API...","retry_tls":"Retry without TLS?","all_exhausted":"All attempts exhausted",
    "fail_hint":"Try: menu 8, proxy, cookies, YouTube clients, different priority.",
    "failed_summary":"Failed","file_not_found":"File not found",
    "info_failed":"Info failed, trying direct download","network_unavailable":"Network unavailable",
    "scanning":"Scanning","found_videos":"Found","no_videos":"No videos",
    "multiple_videos":"Multiple videos","number_or_all":"Numbers (1,3-5 or all)",
    "invalid_url":"Invalid URL","stopped":"Stopped","extracting":"Extracting","downloading":"Downloading",
    "download_done":"Downloaded","no_ffmpeg_warn":"ffmpeg not working — combined formats only",
    "search_where":"Where?","search_other":"Other site","search_query":"Query",
    "search_results":"Results","search_select":"Numbers (1,3-5 or all; Enter — cancel)",
    "search_searching":"Searching","search_empty":"Nothing found","search_failed":"Search failed",
    "search_url":"Page URL","search_kind":"1 — video, 2 — audio [1]",
    "fm_title":"File manager","fm_choose_dir":"Choose dir","fm_videos":"videos","fm_audio":"audio",
    "fm_photos":"photos","fm_text":"text","fm_code":"code","fm_fix":"fix","fm_back":"Back",
    "fm_empty":"Empty","fm_delete":"Delete","fm_delete_multi":"Delete many","fm_delete_all":"Delete all",
    "fm_rename":"Rename","fm_move_to_fix":"Move to fix","fm_restore":"Restore",
    "fm_deleted":"Deleted","fm_failed":"Error","fm_numbers":"Numbers","fm_new_name":"New name",
    "fm_renamed":"Renamed","fm_moved":"Moved","fm_file_index":"File number","fm_exists":"Exists",
    "settings_title":"Settings","grp_media":"Media","grp_network":"Network","grp_interface":"Interface",
    "grp_new":"New modules (photo/text/code)","set_reset":"Reset","set_saved":"Saved",
    "set_enter_value":"New value (Enter keep, '-' clear)","set_bad_value":"Invalid value",
    "set_video_codec":"Video codec","set_audio_codec":"Audio codec",
    "set_max_height":"Max height (0 = unlimited)","set_auto_convert":"Auto convert",
    "set_concurrent_fragments":"Parallel fragments","set_cookies_file":"Cookies file",
    "set_proxy":"Proxy","set_dns_mode":"DNS mode","set_dns_servers":"DNS servers",
    "set_doh_url":"DoH URL","set_doh_fallback":"DoH fallback","set_ip_version":"IP preference",
    "set_verify_tls":"Verify TLS","set_preflight":"Preflight","set_socket_timeout":"Timeout (s)",
    "set_retries":"Retries","set_yt_clients":"YouTube clients","set_js_runtime":"JS runtime",
    "set_remote_ejs":"Remote EJS","set_progress_width":"Progress width",
    "set_ask_rename":"Ask rename","set_ask_fix":"Ask move to fix","set_prompt_timeout":"Prompt timeout (s)",
    "set_base_dir":"Base dir","set_language":"Language",
    "set_unattended":"Unattended (no prompts)","set_photo_max_width":"Max photo width (0 = unlimited)",
    "set_photo_quality":"JPEG quality (1-100)","set_code_auto_fix":"Code auto-fix",
    "set_spell_lang":"Spell lang (ru/en/both)","set_metadata_template":"Metadata template",
    "opt_auto":"auto","opt_system":"system","opt_udp":"udp","opt_doh":"doh","opt_none":"none",
    "opt_ask":"ask","opt_always":"always","opt_never":"never","opt_deno":"deno","opt_node":"node",
    "opt_bun":"bun","opt_quickjs":"quickjs","opt_ipv4":"IPv4","opt_ipv6":"IPv6",
    "on":"on","off":"off","unlimited":"unlimited","empty":"not set",
    "preset_iphone":"iPhone (H.264 + AAC)","preset_android":"Android (H.264 + AAC)",
    "preset_universal":"Universal (H.264 Baseline)","preset_h265":"H.265 / HEVC",
    "preset_vp9":"VP9","preset_av1":"AV1","preset_original":"Original",
    "audio_aac":"AAC 128k","audio_ac3":"AC3 192k","audio_mp3":"MP3 192k","audio_opus":"Opus 160k",
    "audio_flac":"FLAC","audio_original":"Original","lang_ru":"Русский","lang_en":"English",
    "video_ready":"Video ready","audio_ready":"Audio ready","file":"File","size":"Size",
    "rename_prompt":"Rename?","move_fix_prompt":"Move to fix?",
    "converting":"Converting","convert_prompt":"Convert?","convert_done":"Done",
    "convert_failed":"Failed","convert_cancelled":"Cancelled","ffmpeg_missing":"ffmpeg missing",
    "compat_warning":"May be incompatible","encoder_missing":"Encoder missing",
    "reenc_keep":"Keep original?","reenc_done":"Reencoded","reenc_skipped":"No reencoding needed",
    "preflight_title":"Network check","preflight_ok":"OK, DNS","preflight_fail":"TLS failed",
    "preflight_blocked":"Looks like DPI","preflight_continue":"Try anyway?",
    "net_help":"Network errors. Set proxy or Enter.","proxy_prompt":"Proxy","proxy_invalid":"Invalid",
    "proxy_set":"Proxy saved","diag_title":"Diagnostics","diag_system":"system","diag_fail":"no answer",
    "diag_mismatch":"DNS answers differ","diag_tls_ok":"TLS OK","diag_tls_fail":"TLS failed",
    "diag_proxy":"Proxy check","diag_proxy_socks":"SOCKS checked on download","diag_press":"Enter — continue",
    "diag_what":"What to diagnose?","diag_quick":"Quick (all hosts, system DNS)",
    "diag_dns_full":"Full DNS (all servers + DoH)","diag_tls_only":"TLS only (all hosts)",
    "diag_proxy_only":"Proxy only","diag_custom":"Custom host list","diag_all":"All tests",
    "upd_title":"Update","upd_stable":"yt-dlp stable","upd_nightly":"yt-dlp Nightly","upd_ejs":"yt-dlp-ejs only",
    "upd_all_tools":"Update ALL (apk upgrade + pip)","upd_reinstall_python":"Reinstall Python (re-pick Alpine)",
    "js_none":"No JS","rutube_no_m3u8":"RuTube: no m3u8","ytdlp_missing":"yt-dlp missing","dl_dest":"Saved to",
    "selfupd_title":"Update script","selfupd_checking":"Checking GitHub","selfupd_uptodate":"Already latest",
    "selfupd_check_failed":"Check failed","selfupd_prompt":"Download and update?","selfupd_done":"Updated, restarting",
    "selfupd_invalid":"Invalid file","selfupd_no_path":"Cannot determine path","selfupd_downloading":"Downloading",
    "templates_custom":"Custom","templates_multi_hint":"Allowed: 2 or 1,3,5 or 1-3 or all",
    "debug_title":"Debug","debug_press":"Enter — continue","debug_versions":"Tool versions",
    "debug_py_pkgs":"Python packages","debug_settings":"All settings","debug_dirs":"Folders",
    "debug_binaries":"Binaries","debug_env":"Environment",
    "photo_download_ok":"Photos saved to","photo_edit_menu":"Photo editing",
    "photo_resize":"Resize","photo_crop":"Crop","photo_rotate":"Rotate","photo_convert":"Convert",
    "photo_auto_orient":"Auto-orient (EXIF)","photo_enter_size":"Size (e.g. 800x600 or 50%)",
    "photo_enter_crop":"Geometry (100x100+10+10)","photo_enter_angle":"Angle (90, 180, -90)",
    "photo_enter_ext":"New format (jpg/png/webp)","photo_src_local":"Local file",
    "photo_src_download":"Download by URL","photo_created":"Created","photo_applied":"Applied",
    "text_title":"Text tools","text_download":"Download text by URL","text_local":"Open local file",
    "text_spell":"Spell check","text_search":"Search in text","text_edit":"Simple edit",
    "text_lang":"Language (ru/en/both) [ru]:","text_enter_url":"Text URL","text_enter_path":"File path",
    "text_enter_query":"Search string","text_spell_ok":"No errors","text_spell_found":"Possible errors",
    "text_search_found":"Matches","text_search_none":"Not found","text_saved":"Saved","text_downloaded":"Downloaded",
    "code_title":"Code tools","code_fix":"Auto-fix (ruff/shellcheck)","code_scan":"Scan only (no fix)",
    "code_enter_path":"Code file path","code_lang_unknown":"No tool for this language",
    "code_fixed":"Code fixed","code_errors":"Errors found","code_clean":"No errors",
    "meta_title":"Metadata","meta_view":"View metadata","meta_strip_all":"Strip ALL metadata",
    "meta_strip_selective":"Strip selected tags","meta_set_template":"Apply template",
    "meta_verify":"Verify after cleaning","meta_deep_clean":"Deep clean (XMP/IPTC/ICC/thumbnails)",
    "meta_gps_preview":"GPS preview (OpenStreetMap)","meta_dir_or_file":"Path to folder or file",
    "meta_tags_select":"Tag numbers to remove","meta_template_select":"Template",
    "meta_done":"Processed","meta_strip_ok":"Metadata removed","meta_strip_fail":"Failed to strip metadata",
    "meta_not_found":"Metadata not found","meta_tpl_anon":"Full anonymity","meta_tpl_camera":"Camera only",
    "meta_tpl_date":"Date & time","meta_tpl_author":"Copyright","meta_tpl_software":"Software",
    "meta_tpl_gps":"GPS (clear)",
    "adv_title":"Advanced media","adv_extract_audio":"Extract audio from video","adv_make_gif":"Make GIF from video",
    "adv_thumbnail":"Extract thumbnail frame","adv_concat":"Concat videos","adv_split":"Split video",
    "adv_loudnorm":"Loudness normalize","adv_compress":"Compress media",
    "adv_enter_src":"Source file","adv_enter_out":"Output file","adv_enter_time":"Time (HH:MM:SS)",
    "adv_enter_duration":"Segment duration (s)","adv_enter_paths":"Paths comma-separated (concat)",
    "adv_done":"Done",
    "priv_title":"Privacy","priv_uuid":"Rename to UUID","priv_encrypt":"Encrypt (gpg/openssl)",
    "priv_shred":"Secure erase (overwrite)","priv_sha256":"SHA-256 hashes","priv_dups":"Find duplicates",
    "priv_enter_path":"Path to file/folder","priv_warn":"WARNING: irreversible operation",
    "priv_confirm":"Continue?","priv_renamed":"Renamed","priv_encrypted":"Encrypted","priv_shredded":"Overwritten",
    "priv_hashed":"Hashes","priv_dups_found":"Duplicate groups found",
    "rep_title":"Reports & audit","rep_csv":"CSV report for folder","rep_json":"JSON report",
    "rep_prescan":"Pre-scan folder (summary)","rep_enter_dir":"Folder path",
    "rep_saved":"Report saved","rep_summary":"Summary",
    "prof_title":"Profiles / presets","prof_apply":"Apply profile","prof_save":"Save current as profile",
    "prof_default":"Default","prof_social":"Social (no GPS/meta, resize 1920)",
    "prof_paranoid":"Paranoid (full clean + UUID + encrypt)","prof_archive":"Archive (originals)",
    "prof_applied":"Profile applied",
    "batch_title":"Batch mode","batch_enter_urls":"URLs one per line (or .txt file path)",
    "batch_hint":"All downloaded and processed without prompts. Auto best format.",
    "batch_kind":"1 — video, 2 — audio, 3 — photo [1]","batch_done":"Batch finished",
    "batch_summary":"Batch summary","batch_ok":"Success","batch_fail":"Failed",
    "unattended_on":"Unattended mode: ON (no prompts)","unattended_off":"Unattended mode: OFF",
}
}
def T(key): return TEXTS.get(LANG, TEXTS["ru"]).get(key, key)

# Ввод
def save_lang(nl):
    global LANG; LANG = nl
    try: LANG_FILE.write_text(nl, encoding="utf-8")
    except Exception: pass
def flush_stdin():
    try:
        import termios; termios.tcflush(sys.stdin, termios.TCIFLUSH)
    except Exception: pass
def _ask_timeout(prompt, timeout, default):
    import select
    sys.stdout.write(prompt); sys.stdout.flush()
    try:
        r, _, _ = select.select([sys.stdin], [], [], timeout)
    except (OSError, ValueError, TypeError): return clean_input(input())
    if not r:
        INPUT_STATE["timeout"] = True; print(); warn_line(T("input_timeout")); return default
    line = sys.stdin.readline()
    return default if line == "" else clean_input(line)
def ask_input(prompt, default=None, timeout=None):
    INPUT_STATE["timeout"] = False; flush_stdin()
    try:
        sys.stdout.flush()
        if timeout and timeout > 0: return _ask_timeout(prompt, timeout, default)
        return clean_input(input(prompt))
    except EOFError: return default
    except KeyboardInterrupt:
        if OP["active"]: print(); raise
        return default
def PT(): return SETTINGS.get("prompt_timeout", 60)
def is_unattended(): return bool(SETTINGS.get("unattended", False))
def parse_multi(text, n):
    if not text: return []
    text = text.strip().lower()
    if text in ("all","a","*"): return list(range(1, n + 1))
    result = []
    for part in text.split(","):
        part = part.strip()
        if not part: continue
        if "-" in part:
            try:
                a,b = part.split("-",1); a,b = int(a), int(b)
                if a > b: a,b = b,a
                for i in range(a, b+1):
                    if 1 <= i <= n and i not in result: result.append(i)
            except ValueError: continue
        elif part.isdigit():
            i = int(part)
            if 1 <= i <= n and i not in result: result.append(i)
    return result
def fix_url(u):
    if not u: return u
    u = str(u).strip()
    if not u or "://" in u: return u
    if re.match(r'^[a-zA-Z0-9][a-zA-Z0-9.-]*\.[a-zA-Z]{2,}(?:[/:?#]|$)', u): return "https://" + u
    return u

# Шаблоны
PROXY_TEMPLATES = ["http://127.0.0.1:1082","http://127.0.0.1:8080","http://127.0.0.1:8081","http://127.0.0.1:3128",
    "http://127.0.0.1:9098","http://198.18.0.3:8080","http://198.18.0.3:1082",
    "socks5://127.0.0.1:1080","socks5h://127.0.0.1:1080","socks5://127.0.0.1:10808","socks5h://127.0.0.1:10808",
    "socks5://127.0.0.1:1081","socks5h://127.0.0.1:1081","socks5://127.0.0.1:1086","socks5h://127.0.0.1:1086",
    "socks5://127.0.0.1:9050","socks5h://127.0.0.1:9050",""]
DNS_TEMPLATES = ["1.1.1.1,8.8.8.8,94.140.14.14,9.9.9.9","1.1.1.1,1.0.0.1","8.8.8.8,8.8.4.4",
    "94.140.14.14,94.140.15.15","9.9.9.9,149.112.112.112","208.67.222.222,208.67.220.220",
    "76.76.2.0,76.76.10.0","77.88.8.8,77.88.8.1","223.5.5.5,223.6.6.6","185.222.222.222,185.184.222.222",
    "1.1.1.1,1.0.0.1,8.8.8.8,8.8.4.4,9.9.9.9,149.112.112.112,94.140.14.14,94.140.15.15"]
DOH_TEMPLATES = ["","https://cloudflare-dns.com/dns-query","https://dns.google/dns-query",
    "https://dns.quad9.net/dns-query","https://dns.adguard-dns.com/dns-query",
    "https://unfiltered.adguard-dns.com/dns-query","https://dns.comss.one/dns-query",
    "https://dns.sb/dns-query","https://doh.libredns.gr/dns-query","https://dns.alidns.com/dns-query",
    "https://1.1.1.1/dns-query","https://8.8.8.8/dns-query","https://9.9.9.9/dns-query",
    "https://94.140.14.14/dns-query","https://doh.angry.im/dns-query"]
DOH_FALLBACK = ["https://1.1.1.1/dns-query","https://1.0.0.1/dns-query","https://8.8.8.8/dns-query",
    "https://8.8.4.4/dns-query","https://9.9.9.9/dns-query","https://dns.quad9.net/dns-query",
    "https://cloudflare-dns.com/dns-query"]
YT_CLIENTS_TEMPLATES = ["","tv,mweb","tv,ios","tv,android_vr","tv,web_safari,mweb,android_vr,ios",
    "android_vr,web_safari","ios,android","web_safari","all"]

# Настройки
DEFAULT_SETTINGS = {
    "video_codec":"iphone","audio_codec":"aac","max_height":0,"auto_convert":"ask",
    "concurrent_fragments":1,"cookies_file":"","proxy":"","dns_mode":"auto",
    "dns_servers":"1.1.1.1,8.8.8.8,94.140.14.14,9.9.9.9","doh_url":"","doh_fallback":True,
    "ip_version":"auto","verify_tls":True,"preflight":True,"socket_timeout":30,"retries":10,
    "yt_clients":"","js_runtime":"auto","remote_ejs":False,"progress_width":36,
    "ask_rename":True,"ask_fix":True,"prompt_timeout":60,"base_dir":"/root/MediaForge",
    "unattended":False,"photo_max_width":0,"photo_quality":85,"code_auto_fix":True,
    "spell_lang":"ru","metadata_template":"anon",
}
CHOICES = {"dns_mode":("auto","system","udp","doh"),"auto_convert":("ask","always","never"),
    "js_runtime":("auto","none","deno","node","bun","quickjs"),"ip_version":("auto","ipv4","ipv6"),
    "spell_lang":("ru","en","both")}
INT_LIMITS = {"max_height":(0,8640),"concurrent_fragments":(1,16),"socket_timeout":(5,600),
    "retries":(0,50),"progress_width":(10,80),"prompt_timeout":(5,3600),
    "photo_max_width":(0,8192),"photo_quality":(1,100)}
GROUPS = [
    ("grp_media",["video_codec","audio_codec","max_height","auto_convert","concurrent_fragments","cookies_file"]),
    ("grp_network",["proxy","dns_mode","dns_servers","doh_url","doh_fallback","ip_version","verify_tls",
                    "preflight","socket_timeout","retries","yt_clients","js_runtime","remote_ejs"]),
    ("grp_new",["photo_max_width","photo_quality","code_auto_fix","spell_lang","metadata_template","unattended"]),
    ("grp_interface",["language","progress_width","ask_rename","ask_fix","prompt_timeout","base_dir"]),
]
def load_settings():
    data = {}
    if SETTINGS_FILE.exists():
        try:
            raw = json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
            if isinstance(raw, dict): data = raw
        except Exception: data = {}
    result = {}
    for k, dv in DEFAULT_SETTINGS.items():
        v = data.get(k, dv)
        if type(v) is not type(dv): v = dv
        if k in CHOICES and v not in CHOICES[k]: v = dv
        if k in INT_LIMITS:
            lo,hi = INT_LIMITS[k]
            try: v = max(lo, min(hi, int(v)))
            except (TypeError, ValueError): v = dv
        result[k] = v
    return result
def save_settings(s):
    try: SETTINGS_FILE.write_text(json.dumps(s, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception: pass
SETTINGS = load_settings()
BASE_DIR = Path(SETTINGS["base_dir"]); VIDEOS_DIR = BASE_DIR/"videos"; AUDIO_DIR = BASE_DIR/"audio"
PHOTOS_DIR = BASE_DIR/"photos"; TEXT_DIR = BASE_DIR/"text"; CODE_DIR = BASE_DIR/"code"
FIX_DIR = BASE_DIR/"fix"; TMP_DIR = BASE_DIR/"tmp"; REPORTS_DIR = BASE_DIR/"reports"
def apply_dirs():
    global BASE_DIR, VIDEOS_DIR, AUDIO_DIR, PHOTOS_DIR, TEXT_DIR, CODE_DIR, FIX_DIR, TMP_DIR, REPORTS_DIR
    BASE_DIR = Path(SETTINGS["base_dir"]).expanduser()
    VIDEOS_DIR = BASE_DIR/"videos"; AUDIO_DIR = BASE_DIR/"audio"; PHOTOS_DIR = BASE_DIR/"photos"
    TEXT_DIR = BASE_DIR/"text"; CODE_DIR = BASE_DIR/"code"; FIX_DIR = BASE_DIR/"fix"
    TMP_DIR = BASE_DIR/"tmp"; REPORTS_DIR = BASE_DIR/"reports"
def ensure_dir():
    apply_dirs()
    try:
        for d in (VIDEOS_DIR, AUDIO_DIR, PHOTOS_DIR, TEXT_DIR, CODE_DIR, FIX_DIR, TMP_DIR, REPORTS_DIR):
            d.mkdir(parents=True, exist_ok=True)
    except OSError as e:
        err_line(f"{BASE_DIR}: {e}")
        SETTINGS["base_dir"] = str(HOME / "MediaForge"); save_settings(SETTINGS); apply_dirs()
        for d in (VIDEOS_DIR, AUDIO_DIR, PHOTOS_DIR, TEXT_DIR, CODE_DIR, FIX_DIR, TMP_DIR, REPORTS_DIR):
            d.mkdir(parents=True, exist_ok=True)

# DNS
DNS_CACHE = {}; DNS_STATE = {"order": None, "busy": False}; PREFLIGHT_OK = set(); QUICK = {"on": False}
_orig_gai = socket.getaddrinfo
def is_ip(h):
    for fam in (socket.AF_INET, socket.AF_INET6):
        try: socket.inet_pton(fam, h); return True
        except (OSError, ValueError): pass
    return False
def dns_servers(): return [s.strip() for s in SETTINGS["dns_servers"].split(",") if s.strip()]
def doh_urls():
    urls = []
    if SETTINGS["doh_url"]:
        for u in SETTINGS["doh_url"].split(","):
            u = u.strip()
            if u: urls.append(u)
    if SETTINGS["doh_fallback"]: urls += DOH_FALLBACK
    return list(dict.fromkeys(urls))
def dns_order():
    if DNS_STATE["order"]: return DNS_STATE["order"]
    table = {"auto":["system","udp","doh"],"system":["system"],"udp":["udp","doh","system"],"doh":["doh","udp","system"]}
    return table.get(SETTINGS["dns_mode"], table["auto"])
def build_query(host, qtype=1):
    tid = random.randint(0, 65535)
    h = struct.pack(">HHHHHH", tid, 0x0100, 1, 0, 0, 0)
    name = b"".join(bytes([len(p)]) + p.encode("ascii") for p in host.rstrip(".").split("."))
    return tid, h + name + b"\x00" + struct.pack(">HH", qtype, 1)
def parse_response(data, tid, qtype=1):
    if len(data) < 12: return []
    rid, flags, qd, an, ns, ar = struct.unpack(">HHHHHH", data[:12])
    if rid != tid or (flags & 0x000F): return []
    def skip(p):
        while True:
            if p >= len(data): raise ValueError("truncated")
            n = data[p]
            if n == 0: return p+1
            if n & 0xC0 == 0xC0: return p+2
            p += n + 1
    pos = 12
    for _ in range(qd): pos = skip(pos) + 4
    ips = []
    for _ in range(an):
        pos = skip(pos)
        rt, rc, ttl, rd = struct.unpack(">HHIH", data[pos:pos+10]); pos += 10
        if qtype == 1 and rt == 1 and rd == 4: ips.append(socket.inet_ntoa(data[pos:pos+4]))
        elif qtype == 28 and rt == 28 and rd == 16: ips.append(socket.inet_ntop(socket.AF_INET6, data[pos:pos+16]))
        pos += rd
    return ips
def udp_query(server, host, qtype=1, timeout=4):
    try: tid, pkt = build_query(host, qtype)
    except Exception as e: return [], str(e)
    fam = socket.AF_INET6 if ":" in server else socket.AF_INET
    s = socket.socket(fam, socket.SOCK_DGRAM); s.settimeout(timeout)
    try:
        s.sendto(pkt, (server, 53)); data, _ = s.recvfrom(4096)
        return parse_response(data, tid, qtype), ""
    except Exception as e: return [], f"{type(e).__name__}: {e}"
    finally: s.close()
def doh_query(url, host, qtype=1, timeout=10):
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    sep = "&" if "?" in url else "?"; t = "A" if qtype == 1 else "AAAA"
    req = urllib.request.Request(f"{url}{sep}name={host}&type={t}", headers={"accept":"application/dns-json","user-agent":UA})
    with opener.open(req, timeout=timeout) as r: data = json.loads(r.read().decode("utf-8","replace"))
    rt = 1 if qtype == 1 else 28
    return [a["data"] for a in data.get("Answer",[]) if a.get("type") == rt]
def qtypes():
    ipv = SETTINGS["ip_version"]
    if ipv == "ipv4": return [1]
    if ipv == "ipv6": return [28]
    return [1, 28]
def resolve_with(mode, host):
    qs = qtypes()
    if mode == "system":
        try:
            fam = socket.AF_INET6 if SETTINGS["ip_version"]=="ipv6" else (socket.AF_INET if SETTINGS["ip_version"]=="ipv4" else 0)
            res = _orig_gai(host, 443, fam, socket.SOCK_STREAM)
            return list(dict.fromkeys(r[4][0] for r in res))
        except Exception: return []
    results = []
    if mode == "udp":
        for srv in dns_servers():
            for qt in qs:
                ips, _ = udp_query(srv, host, qt)
                if ips: results.extend(ips)
            if results: return list(dict.fromkeys(results))
        return []
    if mode == "doh":
        DNS_STATE["busy"] = True
        try:
            for u in doh_urls():
                for qt in qs:
                    try:
                        ips = doh_query(u, host, qt)
                        if ips: results.extend(ips)
                    except Exception: continue
                if results: return list(dict.fromkeys(results))
        finally: DNS_STATE["busy"] = False
        return []
    return []
def patched_gai(host, port, family=0, type=0, proto=0, flags=0):
    if not isinstance(host, str) or not host or host == "localhost" or is_ip(host): return _orig_gai(host, port, family, type, proto, flags)
    if port is not None and not isinstance(port, int) and not str(port).isdigit(): return _orig_gai(host, port, family, type, proto, flags)
    p = int(port) if port else 0
    ips = DNS_CACHE.get(host)
    if not ips:
        for m in dns_order():
            if m == "doh" and DNS_STATE["busy"]: continue
            if m == "system":
                try:
                    fam = socket.AF_INET6 if SETTINGS["ip_version"]=="ipv6" else (socket.AF_INET if SETTINGS["ip_version"]=="ipv4" else family)
                    res = _orig_gai(host, port, fam, type, proto, flags)
                    if res: return res
                except Exception: pass
                continue
            ips = resolve_with(m, host)
            if ips: DNS_CACHE[host] = ips; break
    if not ips: raise socket.gaierror(socket.EAI_NONAME, "Name does not resolve")
    st = type or socket.SOCK_STREAM
    return [(socket.AF_INET6 if ":" in ip else socket.AF_INET, st, proto or 0, "", (ip, p)) for ip in ips]
socket.getaddrinfo = patched_gai
def reset_dns(): DNS_STATE["order"] = None; DNS_CACHE.clear(); PREFLIGHT_OK.clear()

# Предпроверка
def tls_probe(host, ip, timeout=15):
    ctx = ssl.create_default_context() if SETTINGS["verify_tls"] else ssl._create_unverified_context()
    sock = None
    try:
        sock = socket.create_connection((ip, 443), timeout); wrapped = ctx.wrap_socket(sock, server_hostname=host); wrapped.close(); return True, ""
    except Exception as e:
        if sock:
            try: sock.close()
            except Exception: pass
        return False, f"{type(e).__name__}: {e}"
def preflight(url):
    host = urlparse(url).hostname
    if not host or SETTINGS["proxy"] or not SETTINGS["preflight"] or host in PREFLIGHT_OK: return True
    info_line(f"{T('preflight_title')} {host}")
    order = []
    for m in dns_order() + ["system","udp","doh"]:
        if m not in order: order.append(m)
    for m in order:
        ips = resolve_with(m, host)
        if not ips: warn_line(f"{m}: {T('diag_fail')}"); continue
        for ip in ips[:2]:
            ok, err = tls_probe(host, ip)
            if ok:
                DNS_STATE["order"] = [m] + [x for x in order if x != m]
                DNS_CACHE.clear(); PREFLIGHT_OK.add(host)
                ok_line(f"{T('preflight_ok')}: {m} ({ip})"); return True
            warn_line(f"{m} {ip}: {err}")
    err_line(T("preflight_fail")); warn_line(T("preflight_blocked")); return False

# Утилиты
NET_PATTERNS = ("name does not resolve","name or service not known","temporary failure in name resolution",
    "try again","handshake","timed out","timeout","connection refused","connection reset","connection aborted",
    "network is unreachable","no route to host","transporterror","errno -2","errno -3","errno 110","errno 111","errno 113","eof occurred")
def is_net_error(t):
    t = str(t).lower(); return any(p in t for p in NET_PATTERNS)
def is_format_error(t):
    t = str(t).lower()
    return ("requested format is not available" in t or "no video formats" in t or "merging of multiple formats" in t or "ffmpeg is not installed" in t)
def trunc(s, n):
    s = str(s); return s if len(s) <= n else s[:n-3] + "..."
def fmt_size(n):
    if n < 1024: return f"{n} B"
    if n < 1024*1024: return f"{n/1024:.1f} KiB"
    if n < 1024*1024*1024: return f"{n/1048576:.1f} MiB"
    return f"{n/1073741824:.2f} GiB"
def fmt_dur(sec):
    try: sec = int(sec)
    except (TypeError, ValueError): return ""
    h, r = divmod(sec, 3600); m, s = divmod(r, 60)
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"
def confirm(prompt, default=False, timeout=None):
    if is_unattended(): return default
    suffix = " [Y/n]: " if default else " [y/N]: "
    ans = ask_input(c(prompt + suffix, YELLOW), None, timeout)
    if ans is None: return default if INPUT_STATE["timeout"] else False
    ans = ans.strip().lower()
    if not ans: return default
    return ans in ("y","yes","д","да")
def valid_url(u):
    try:
        p = urlparse(u); return p.scheme in ("http","https") and bool(p.netloc)
    except (ValueError, TypeError): return False
def is_youtube(url):
    try: host = (urlparse(url).hostname or "").lower()
    except Exception: return False
    return host.endswith(("youtube.com","youtu.be","youtube-nocookie.com"))
def safe_name(s, limit=150):
    s = re.sub(r'[\\/:*?"<>|%\n\r\t]+', "_", str(s)).strip(); return s[:limit] or "file"
def _rm(p):
    try:
        if p and Path(p).exists(): Path(p).unlink()
    except OSError: pass

# Кодеки
VIDEO_CODECS = {
    "iphone":{"label_key":"preset_iphone","encoder":"libx264","profile":"high","level":"4.0","crf":"23","pix_fmt":"yuv420p","preset":"medium","audio_codec":"aac","audio_bitrate":"128k","movflags":"+faststart","compat":("h264","avc1")},
    "android":{"label_key":"preset_android","encoder":"libx264","profile":"high","level":"4.0","crf":"23","pix_fmt":"yuv420p","preset":"medium","audio_codec":"aac","audio_bitrate":"128k","movflags":"+faststart","compat":("h264","avc1")},
    "universal":{"label_key":"preset_universal","encoder":"libx264","profile":"baseline","level":"3.0","crf":"23","pix_fmt":"yuv420p","preset":"medium","audio_codec":"aac","audio_bitrate":"128k","movflags":"+faststart","compat":("h264","avc1")},
    "h265":{"label_key":"preset_h265","encoder":"libx265","crf":"28","preset":"fast","pix_fmt":"yuv420p","audio_codec":"aac","audio_bitrate":"128k","movflags":"+faststart","compat":("hevc","h265")},
    "vp9":{"label_key":"preset_vp9","encoder":"libvpx-vp9","crf":"32","speed":"6","row_mt":"1","pix_fmt":"yuv420p","audio_codec":"opus","audio_bitrate":"128k","container":"webm","compat":("vp9",)},
    "av1":{"label_key":"preset_av1","encoder":"libsvtav1","crf":"35","preset":"10","pix_fmt":"yuv420p","audio_codec":"opus","audio_bitrate":"128k","container":"mkv","compat":("av1",)},
    "original":{"label_key":"preset_original","encoder":"copy","audio_codec":"copy"},
}
AUDIO_CODECS = {
    "aac":{"label_key":"audio_aac","encoder":"aac","bitrate":"128k","ext":"m4a","probe":"aac"},
    "ac3":{"label_key":"audio_ac3","encoder":"ac3","bitrate":"192k","ext":"ac3","probe":"ac3"},
    "mp3":{"label_key":"audio_mp3","encoder":"libmp3lame","bitrate":"192k","ext":"mp3","probe":"mp3"},
    "opus":{"label_key":"audio_opus","encoder":"libopus","bitrate":"160k","ext":"opus","probe":"opus"},
    "flac":{"label_key":"audio_flac","encoder":"flac","bitrate":None,"ext":"flac","probe":"flac"},
    "original":{"label_key":"audio_original","encoder":"copy","bitrate":None,"ext":None,"probe":None},
}
A_COMPAT = {"aac":("aac","mp4a"), "opus":("opus",)}
def available_encoders():
    global _encoders_cache
    if _encoders_cache is not None: return _encoders_cache
    _encoders_cache = set()
    if not HAS_FFMPEG: return _encoders_cache
    try:
        r = subprocess.run([FFMPEG_BIN,"-hide_banner","-encoders"], capture_output=True, text=True, timeout=60)
        for line in r.stdout.splitlines():
            m = re.match(r"^ [A-Z.]{6} (\S+)", line)
            if m: _encoders_cache.add(m.group(1))
    except Exception: pass
    return _encoders_cache
def encoder_ok(n): return n == "copy" or n in available_encoders()
def js_runtime():
    rt = SETTINGS["js_runtime"]
    if rt == "none": return None
    if rt == "auto":
        for name, binary in JS_BIN.items():
            if shutil.which(binary): return name
        return None
    return rt if shutil.which(JS_BIN[rt]) else None
def has_ejs():
    try: return importlib.util.find_spec("yt_dlp_ejs") is not None
    except Exception: return False
def height_filter():
    h = SETTINGS["max_height"]; return f"[height<={h}]" if h else ""
def default_selector():
    h = height_filter()
    if not HAS_FFMPEG: return f"b[ext=mp4]{h}/b{h}"
    return f"bv*[vcodec^=avc1]{h}+ba[ext=m4a]/b[ext=mp4]{h}/bv*{h}+ba/b{h}"
def selector_chain(chosen):
    h = height_filter()
    if not HAS_FFMPEG: return [f"b[ext=mp4]{h}", "b"]
    return list(dict.fromkeys([i for i in [chosen, default_selector(), f"bv*{h}+ba/b{h}", f"b[ext=mp4]{h}/b{h}", "b/w"] if i]))
def video_selectors(prio, chosen=None):
    h = height_filter(); items = []
    if chosen: items.append((chosen, "mp4" if HAS_FFMPEG else None))
    if not HAS_FFMPEG:
        items += [(f"b[ext=mp4]{h}", None),(f"b{h}", None),("b", None),("w", None)]
        return list(dict.fromkeys(items))
    groups = {
        "mp4":[(f"bv*[vcodec^=avc1]{h}+ba[ext=m4a]/b[ext=mp4]{h}", "mp4")],
        "vp9":[(f"bv*[vcodec~='^(vp9|vp09)']{h}+ba/b[vcodec~='^(vp9|vp09)']{h}", "mkv")],
        "av1":[(f"bv*[vcodec~='^(av01|av1)']{h}+ba/b[vcodec~='^(av01|av1)']{h}", "mkv")],
        "any":[(f"bv*{h}+ba/b{h}", "mkv")],
    }
    first = prio if prio in groups else "mp4"
    order = [first] + [k for k in ("mp4","vp9","av1","any") if k != first]
    for k in order: items += groups[k]
    items += [(default_selector(),"mp4"),(f"bv*{h}+ba/b{h}","mp4"),(f"b[ext=mp4]{h}/b{h}","mp4"),("bv*+ba/b","mkv"),("b/w",None)]
    return list(dict.fromkeys(items))
def audio_selectors(prio):
    groups = {"m4a":[("ba[ext=m4a]",None)],"opus":[("ba[acodec=opus]/ba[ext=webm]",None)],
              "mp3":[("ba[ext=mp3]",None)],"any":[("bestaudio/best",None)]}
    first = prio if prio in groups else "m4a"
    order = [first] + [k for k in ("m4a","opus","mp3","any") if k != first]
    items = []
    for k in order: items += groups[k]
    items += [("bestaudio/best",None),("b",None),("b/w",None)]
    return list(dict.fromkeys(items))

# Log + Progress
class Log:
    def __init__(self): self.msgs = []; self.summary = []
    def debug(self, m): pass
    def info(self, m): pass
    def warning(self, m):
        m = str(m)
        if "Deprecated Feature" in m or "Support for Python version" in m: return
        if "PO Token" in m or "SABR" in m or "n challenge" in m:
            key = "PO token required" if "PO Token" in m else ("SABR streaming" if "SABR" in m else "challenge failed")
            if key not in self.summary: self.summary.append(key)
            return
        self.msgs.append("WARNING: " + m)
    def error(self, m):
        m = str(m)
        if "Deprecated Feature" in m or "Support for Python version" in m: return
        self.msgs.append(m if m.startswith("ERROR") else "ERROR: " + m)
    def text(self): return "\n".join(self.msgs)
def report(e, lg): return lg.text() + "\n" + str(e).strip()
class Progress:
    def __init__(self): self.bar = None
    def __call__(self, d):
        if tqdm is None: return
        st = d.get("status")
        if st == "downloading":
            total = d.get("total_bytes") or d.get("total_bytes_estimate")
            if self.bar is None:
                self.bar = tqdm(total=total, unit="B", unit_scale=True, leave=False, ncols=SETTINGS["progress_width"], desc="dl",
                    bar_format="{l_bar}{bar}| {n_fmt}/{total_fmt} [{rate_fmt}, ETA {remaining}]")
            elif total: self.bar.total = total
            dl = d.get("downloaded_bytes") or 0
            self.bar.update(max(0, dl - self.bar.n))
        elif st in ("finished","error"): self.close()
    def close(self):
        if self.bar is not None:
            self.bar.close(); self.bar = None; sys.stdout.write("\n"); sys.stdout.flush()

# yt-dlp обёртки
def parse_clients(text):
    groups = []
    for part in text.split(","):
        part = part.strip()
        if part: groups.append([x.strip() for x in part.split("+") if x.strip()])
    return groups
def build_strategies(url, win=None):
    out = []
    if is_youtube(url):
        seq = parse_clients(SETTINGS["yt_clients"]) or YT_CLIENT_SEQ
        for cl in seq: out.append({"clients":cl, "name":"+".join(cl) or "default"})
    else: out.append({"clients":[], "name":"default"})
    if win: out.sort(key=lambda s: 0 if s["name"] == win else 1)
    return out
def base_opts(strategy=None, **extra):
    s = SETTINGS; quick = QUICK["on"]
    o = {"quiet":True, "noplaylist":True, "logger":Log(),
         "socket_timeout":15 if quick else s["socket_timeout"], "retries":1 if quick else s["retries"],
         "fragment_retries":1 if quick else s["retries"], "extractor_retries":1 if quick else 3,
         "nocheckcertificate":not s["verify_tls"],
         "concurrent_fragment_downloads":max(1, s["concurrent_fragments"])}
    if s["ip_version"] == "ipv4": o["source_address"] = "0.0.0.0"
    if s["proxy"]: o["proxy"] = s["proxy"]
    if s["cookies_file"] and Path(s["cookies_file"]).expanduser().exists(): o["cookiefile"] = str(Path(s["cookies_file"]).expanduser())
    if strategy and strategy.get("clients"): o["extractor_args"] = {"youtube":{"player_client":list(strategy["clients"])}}
    rt = js_runtime()
    if rt:
        try: o["js_runtimes"] = {rt: {}}
        except Exception: pass
    if s["remote_ejs"] or rt: o["remote_components"] = ["ejs:github"]
    o.update(extra); return o
def first_entry(info):
    if isinstance(info, dict) and info.get("entries") is not None:
        return next((e for e in info["entries"] if isinstance(e, dict) and e.get("formats")), None)
    return info
def get_info(url, strategy):
    if yt_dlp is None: return None, ""
    o = base_opts(strategy, url=url); lg = o["logger"]
    try:
        with yt_dlp.YoutubeDL(o) as ydl: info = first_entry(ydl.extract_info(url, download=False))
        return info, lg.text()
    except Exception as e: return None, report(e, lg)
def extract_info_smart(url):
    info_line(f"{T('extracting')}: {trunc(url, 60)}")
    net_fail = 0
    for st in build_strategies(url):
        if net_fail >= 2: break
        info, err = get_info(url, st)
        if isinstance(info, dict) and (info.get("formats") or info.get("url")): return info, st["name"]
        show_msgs(err)
        if is_net_error(err): net_fail += 1
        if not is_youtube(url): break
    return None, None
def run_module(url, selector, strategy, job, extra=None, outtmpl=None):
    if yt_dlp is None: return False, ""
    o = base_opts(strategy, url=url); lg = o["logger"]
    o.update(format=selector, outtmpl=str(outtmpl or (job["dir"] / OUT_TMPL)), continuedl=True, overwrites=False)
    mf = job.get("merge_fmt", "mp4") if job["merge"] else None
    if mf: o["merge_output_format"] = mf
    if extra: o.update(extra)
    pg = Progress(); o["progress_hooks"] = [pg]
    try:
        with yt_dlp.YoutubeDL(o) as ydl: code = ydl.download([url])
        return code in (None, 0), lg.text()
    except Exception as e: return False, report(e, lg)
    finally: pg.close()
def run_binary(url, selector, strategy, job, extra_flags=(), outtmpl=None):
    if not shutil.which("yt-dlp") and yt_dlp is None: return False, ""
    s = SETTINGS; base = ["yt-dlp"] if shutil.which("yt-dlp") else [sys.executable, "-m", "yt_dlp"]
    cmd = base + ["-f", selector, "--no-playlist", "--newline", "--no-warnings",
                  "-o", str(outtmpl or (job["dir"] / OUT_TMPL)),
                  "--socket-timeout", str(15 if QUICK["on"] else s["socket_timeout"]),
                  "--retries", str(1 if QUICK["on"] else s["retries"]),
                  "--fragment-retries", str(1 if QUICK["on"] else s["retries"]),
                  "-N", str(max(1, s["concurrent_fragments"]))]
    mf = job.get("merge_fmt", "mp4") if job["merge"] else None
    if mf: cmd += ["--merge-output-format", mf]
    if s["ip_version"] == "ipv4": cmd.append("--force-ipv4")
    elif s["ip_version"] == "ipv6": cmd.append("--force-ipv6")
    if s["proxy"]: cmd += ["--proxy", s["proxy"]]
    if not s["verify_tls"]: cmd.append("--no-check-certificate")
    if s["cookies_file"] and Path(s["cookies_file"]).expanduser().exists(): cmd += ["--cookies", str(Path(s["cookies_file"]).expanduser())]
    if strategy and strategy.get("clients"): cmd += ["--extractor-args", "youtube:player_client=" + ",".join(strategy["clients"])]
    rt = js_runtime()
    if rt:
        try: help_out = subprocess.run(base + ["--help"], capture_output=True, text=True, timeout=10).stdout or ""
        except Exception: help_out = ""
        if "--js-runtimes" in help_out: cmd += ["--js-runtimes", rt]
    if s["remote_ejs"]: cmd += ["--remote-components", "ejs:github"]
    cmd += list(extra_flags) + [url]
    env = dict(os.environ, VD_DNS_ORDER=",".join(dns_order()), PYTHONUTF8="1")
    err = []; proc = None
    try: proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1, env=env)
    except Exception as e: return False, str(e)
    try:
        for line in proc.stdout:
            line = line.rstrip("\r\n")
            if not line: continue
            if "[download]" in line and "%" in line:
                sys.stdout.write("\r\033[K" + line[:SETTINGS["progress_width"] + 20]); sys.stdout.flush(); continue
            if "Deprecated Feature" in line or "Support for Python version" in line: continue
            if "PO Token" in line or "SABR" in line or "n challenge" in line: continue
            if line.startswith(("ERROR","WARNING")): err.append(line)
        try: proc.wait(timeout=7200)
        except Exception: proc.kill()
    except KeyboardInterrupt:
        try: proc.kill()
        except Exception: pass
        raise
    finally:
        sys.stdout.write("\n"); sys.stdout.flush()
        if proc.poll() is None:
            try: proc.terminate(); proc.wait(timeout=5)
            except Exception:
                try: proc.kill()
                except Exception: pass
    return proc.returncode == 0, "\n".join(err)
def run_any(url, selector, strategy, job, extra=None, flags=(), outtmpl=None):
    errors = []
    if yt_dlp is not None:
        ok, err = run_module(url, selector, strategy, job, extra, outtmpl)
        if ok: return True, err
        if err: errors.append(err)
        if not shutil.which("yt-dlp"): return False, "\n".join(errors)
    ok, err = run_binary(url, selector, strategy, job, flags, outtmpl)
    if ok: return True, err
    if err: errors.append(err)
    return False, "\n".join(errors)

# Снимки и очистка
def snapshot(d):
    result = {}
    try:
        for f in d.iterdir():
            if f.is_file():
                try: result[f.name] = f.stat().st_mtime
                except OSError: pass
    except OSError: pass
    return result
def newest_changed(d, before, exts=None):
    best, mt_best = None, 0
    try:
        for f in d.iterdir():
            if not f.is_file() or f.suffix in (".part",".ytdl") or f.name.startswith("."): continue
            if exts and f.suffix.lower() not in exts: continue
            try: mt = f.stat().st_mtime
            except OSError: continue
            if mt > before.get(f.name, 0) and mt > mt_best: best, mt_best = f, mt
    except OSError: pass
    return best
def find_by_id(d, info, exts=None):
    vid = info.get("id") if isinstance(info, dict) else None
    if not vid: return None
    best, mt_best = None, 0
    try:
        for f in d.iterdir():
            if not f.is_file() or f.suffix in (".part",".ytdl"): continue
            if f"[{vid}]" not in f.name or (exts and f.suffix.lower() not in exts): continue
            mt = f.stat().st_mtime
            if mt > mt_best: best, mt_best = f, mt
    except OSError: pass
    return best
def cleanup_junk(aggressive=False):
    removed = []; now = time.time()
    for d in (VIDEOS_DIR, AUDIO_DIR, PHOTOS_DIR):
        try:
            for f in d.iterdir():
                if not f.is_file(): continue
                try: age = now - f.stat().st_mtime
                except OSError: continue
                is_part = f.suffix in (".part",".ytdl") or ".temp." in f.name or ".vdtmp." in f.name
                is_frag = bool(re.search(r"\.f\d+$", f.stem)) and f.suffix.lower() in (".mp4",".m4a",".webm",".mkv")
                if (is_part and age > 120) or (is_frag and aggressive and age > 3600):
                    try: f.unlink(); removed.append(f.name)
                    except OSError: pass
        except OSError: pass
    try:
        for d in TMP_DIR.iterdir():
            try: age = now - d.stat().st_mtime
            except OSError: age = 0
            if age > 600:
                try:
                    if d.is_dir(): shutil.rmtree(d, ignore_errors=True)
                    else: d.unlink()
                    removed.append(d.name)
                except OSError: pass
    except OSError: pass
    return removed

# FFmpeg работа
def get_duration(path):
    if not HAS_FFMPEG or not FFPROBE_BIN: return None
    try:
        r = subprocess.run([FFPROBE_BIN,"-v","error","-show_entries","format=duration","-of","default=noprint_wrappers=1:nokey=1",str(path)], capture_output=True, text=True, timeout=60)
        return float(r.stdout.strip())
    except Exception: return None
def probe_codec(path, stream):
    if not HAS_FFMPEG or not FFPROBE_BIN: return ""
    try:
        r = subprocess.run([FFPROBE_BIN,"-v","error","-select_streams",stream,"-show_entries","stream=codec_name","-of","default=nw=1:nk=1",str(path)], capture_output=True, text=True, timeout=60)
        return r.stdout.strip().lower()
    except Exception: return ""
def run_ffmpeg_with_progress(cmd, duration, desc):
    if tqdm is None:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=14400)
        if r.returncode != 0 and r.stderr: err_line(r.stderr.strip()[-1500:])
        return r.returncode == 0
    full = cmd[:1] + ["-nostats","-hide_banner","-loglevel","error","-progress","pipe:1"] + cmd[1:]
    try: proc = subprocess.Popen(full, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    except Exception as e: err_line(f"ffmpeg: {e}"); return False
    pbar = tqdm(total=duration or 0, unit="s", desc=desc, leave=False, ncols=SETTINGS["progress_width"],
                bar_format="{l_bar}{bar}| {n_fmt}/{total_fmt} [{rate_fmt}, ETA {remaining}]")
    last = 0; errtext = ""; interrupted = False
    try:
        for line in proc.stdout:
            line = line.strip()
            if line.startswith("out_time_ms="):
                try:
                    secs = int(line.split("=",1)[1]) / 1000000.0
                    if secs > last: pbar.update(secs - last); last = secs
                except ValueError: pass
            elif line.startswith("progress=") and line.endswith("end"): break
    except KeyboardInterrupt:
        interrupted = True
        try: proc.kill()
        except Exception: pass
    except Exception: pass
    finally:
        try: _, errtext = proc.communicate(timeout=120)
        except Exception: proc.kill(); errtext = ""
        if duration and last < duration and not interrupted: pbar.update(duration - last)
        pbar.close(); sys.stdout.write("\n"); sys.stdout.flush()
    if interrupted: raise KeyboardInterrupt
    if proc.returncode != 0 and errtext: err_line(errtext.strip()[-1500:])
    return proc.returncode == 0
def check_compat(path, vkey):
    if not path or not path.exists(): return True
    v = VIDEO_CODECS.get(vkey, VIDEO_CODECS["iphone"])
    if v.get("encoder") == "copy" or not HAS_FFMPEG: return True
    vc = probe_codec(path, "v:0"); ac = probe_codec(path, "a:0")
    acompat = A_COMPAT.get(v.get("audio_codec"))
    if vc and vc not in v.get("compat", ()): return False
    if ac and acompat and ac not in acompat: return False
    return True
def build_ffmpeg_cmd(src, dst, vkey):
    v = VIDEO_CODECS.get(vkey, VIDEO_CODECS["iphone"])
    cmd = [FFMPEG_BIN, "-y", "-i", str(src)]
    if v.get("encoder") == "copy": cmd += ["-c:v", "copy"]
    else:
        cmd += ["-c:v", v["encoder"]]
        if v.get("preset"): cmd += ["-preset", v["preset"]]
        if v["encoder"] == "libvpx-vp9": cmd += ["-crf", v["crf"], "-b:v", "0"]
        elif v.get("crf"): cmd += ["-crf", v["crf"]]
        if v.get("profile"): cmd += ["-profile:v", v["profile"]]
        if v.get("level"): cmd += ["-level", v["level"]]
        if v.get("pix_fmt"): cmd += ["-pix_fmt", v["pix_fmt"]]
        if v.get("speed"): cmd += ["-speed", v["speed"]]
        if v.get("row_mt"): cmd += ["-row-mt", v["row_mt"]]
    vac = v.get("audio_codec", "copy")
    if vac == "aac": cmd += ["-c:a", "aac", "-b:a", v.get("audio_bitrate", "128k")]
    elif vac == "opus": cmd += ["-c:a", "libopus", "-b:a", v.get("audio_bitrate", "128k")]
    else: cmd += ["-c:a", "copy"]
    if v.get("movflags"): cmd += ["-movflags", v["movflags"]]
    cmd.append(str(dst)); return cmd
def convert_file(src, vkey, keep=False):
    v = VIDEO_CODECS.get(vkey, VIDEO_CODECS["iphone"])
    if not HAS_FFMPEG: err_line(T("ffmpeg_missing")); return src, False
    aenc = {"aac":"aac","opus":"libopus"}.get(v.get("audio_codec"), "copy")
    if not encoder_ok(v.get("encoder","copy")) or not encoder_ok(aenc): warn_line(T("encoder_missing")); return src, False
    container = v.get("container", "mp4")
    if keep: same = False; dst = src.with_name(f"{src.stem} [{vkey}].{container}")
    else: same = src.suffix.lower() == "." + container; dst = src.with_name(src.stem + ".vdtmp." + container) if same else src.with_suffix("." + container)
    cmd = build_ffmpeg_cmd(src, dst, vkey)
    info_line(f"{T('converting')}: {src.name}")
    try: ok = run_ffmpeg_with_progress(cmd, get_duration(src), T("converting"))
    except KeyboardInterrupt: _rm(dst); raise
    if ok and dst.exists() and dst.stat().st_size > 0:
        if keep: return dst, True
        try:
            src.unlink()
            if same: dst.rename(src); return src, True
            return dst, True
        except OSError as e: err_line(str(e)); return dst, True
    err_line(T("convert_failed")); _rm(dst); return src, False
def convert_audio(src, akey, keep=False, force=False):
    a = AUDIO_CODECS.get(akey, AUDIO_CODECS["aac"])
    if a["encoder"] == "copy" or not src or not src.exists(): return src, None
    if not force and probe_codec(src, "a:0") == a["probe"]: return src, None
    if not HAS_FFMPEG: err_line(T("ffmpeg_missing")); return src, False
    if not encoder_ok(a["encoder"]): warn_line(T("encoder_missing")); return src, False
    if keep: dst = src.with_name(f"{src.stem} [{akey}].{a['ext']}")
    else:
        dst = src.with_suffix("." + a["ext"])
        if dst == src: dst = src.with_name(src.stem + ".vdtmp." + a["ext"])
    cmd = [FFMPEG_BIN,"-y","-i",str(src),"-vn","-c:a",a["encoder"]]
    if a["bitrate"]: cmd += ["-b:a", a["bitrate"]]
    cmd.append(str(dst))
    info_line(f"{T('converting')}: {src.name}")
    try: ok = run_ffmpeg_with_progress(cmd, get_duration(src), T("converting"))
    except KeyboardInterrupt: _rm(dst); raise
    if ok and dst.exists() and dst.stat().st_size > 0:
        if keep: return dst, True
        try: src.unlink()
        except OSError: pass
        final = dst
        if ".vdtmp." in dst.name:
            final = src.with_suffix("." + a["ext"])
            try: dst.rename(final)
            except OSError: final = dst
        return final, True
    err_line(T("convert_failed")); _rm(dst); return src, False
def select_format(info):
    if not isinstance(info, dict): return None
    formats = info.get("formats") or []
    videos = [f for f in formats if isinstance(f, dict) and f.get("format_id") and f.get("vcodec") not in (None, "none")]
    audios = [f for f in formats if isinstance(f, dict) and f.get("format_id") and f.get("vcodec") == "none" and f.get("acodec") not in (None, "none")]
    if not videos: return None
    uniq = {}
    for f in videos: uniq[(f.get("height"),f.get("ext"),f.get("fps"),f.get("vcodec"),f.get("acodec"))] = f
    vlist = sorted(uniq.values(), key=lambda x: (x.get("height") or 0, x.get("fps") or 0))
    print(c(f"\n{T('available_formats')}:", CYAN))
    for i, f in enumerate(vlist, 1):
        size = f.get("filesize") or f.get("filesize_approx")
        size_t = f", {size/1048576:.0f}M" if isinstance(size, (int, float)) else ""
        fps_t = f", {f['fps']}fps" if f.get("fps") else ""
        aud = "+" if f.get("acodec") not in (None, "none") else "-"
        print(f"  {i}. {f.get('height') or '?'}p {f.get('ext') or '?'} {aud}{fps_t}{size_t}")
    sys.stdout.flush()
    ch = ask_input(c(f"{T('select_video')}: ", YELLOW), timeout=PT())
    if not ch: return None
    try: sel = vlist[int(ch) - 1]
    except (ValueError, IndexError): warn_line(T("invalid_default")); return None
    vid = str(sel["format_id"])
    if sel.get("acodec") not in (None, "none"): return vid
    if not audios or not HAS_FFMPEG:
        if not HAS_FFMPEG and audios: warn_line(T("no_ffmpeg_warn"))
        return vid if not audios else None
    print(c(f"\n{T('select_audio_track')}:", CYAN))
    for i, f in enumerate(audios, 1):
        abr = f.get("abr"); abr_t = f", {abr:g}kbps" if isinstance(abr, (int, float)) else ""
        print(f"  {i}. {f.get('language') or 'unknown'}, {f.get('ext') or '?'}{abr_t}")
    sys.stdout.flush()
    a = ask_input(c(f"{T('select_audio_track')}: ", YELLOW), timeout=PT())
    if not a: return f"{vid}+ba/b"
    try: return f"{vid}+{audios[int(a) - 1]['format_id']}"
    except (ValueError, IndexError): return f"{vid}+ba/b"

# HTTP helpers
def make_opener():
    handlers = []
    px = SETTINGS["proxy"]
    if px and px.split("://")[0].lower() in ("http","https"): handlers.append(urllib.request.ProxyHandler({"http":px,"https":px}))
    if not SETTINGS["verify_tls"]: handlers.append(urllib.request.HTTPSHandler(context=ssl._create_unverified_context()))
    return urllib.request.build_opener(*handlers)
def http_json(url, referer="https://rutube.ru/"):
    req = urllib.request.Request(url, headers={"User-Agent":UA,"Referer":referer,"Accept":"application/json"})
    with make_opener().open(req, timeout=SETTINGS["socket_timeout"]) as r: return json.loads(r.read().decode("utf-8","replace"))
def rutube_download(url, job):
    m = re.search(r"rutube\.ru/(?:video|play/embed|video/private)/([0-9a-f]{32})", url)
    if not m: return False
    vid = m.group(1); p = re.search(r"[?&]p=([\w-]+)", url); private = f"&p={p.group(1)}" if p else ""
    info_line(T("trying_rutube")); title = vid
    try: title = http_json(f"https://rutube.ru/api/video/{vid}/?format=json").get("title") or vid
    except Exception as e: err_unique(f"{type(e).__name__}: {e}")
    title = safe_name(title); ref = "https%3A%2F%2Frutube.ru"
    variants = [
        f"https://rutube.ru/api/play/options/{vid}/?no_404=true&referer={ref}&pver=v2&client=wdp{private}",
        f"https://rutube.ru/api/play/options/{vid}/?no_404=true&referer={ref}&pver=v2{private}",
        f"https://rutube.ru/api/play/options/{vid}/?no_404=true&referer={ref}{private}",
        f"https://rutube.ru/api/play/options/{vid}/?format=json{private}",
    ]
    m3u8 = None
    for u in variants:
        try:
            data = http_json(u); vb = data.get("video_balancer") or {}
            m3u8 = (vb.get("m3u8") or vb.get("default")) if isinstance(vb, dict) else None
            if m3u8: break
        except Exception as e: err_unique(f"{type(e).__name__}: {e}")
    if not m3u8: err_line(T("rutube_no_m3u8")); return False
    hdrs = {"User-Agent":UA,"Referer":"https://rutube.ru/","Origin":"https://rutube.ru"}
    out_tmpl = job["dir"] / f"{title} [{vid}].%(ext)s"; job["merge_fmt"] = "mp4" if job["merge"] else None
    for sel in (default_selector(), "bv*+ba/b", "b"):
        ok, err = run_any(m3u8, sel, None, job, extra={"http_headers":hdrs}, outtmpl=out_tmpl)
        if ok: return True
        show_msgs(err)
    if HAS_FFMPEG:
        out = job["dir"] / f"{title} [{vid}].mp4"
        hs = "".join(f"{k}: {v}\r\n" for k, v in hdrs.items())
        cmd = [FFMPEG_BIN,"-y","-headers",hs,"-i",m3u8,"-c","copy","-bsf:a","aac_adtstoasc",str(out)]
        try:
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=7200)
            if r.returncode == 0 and out.exists() and out.stat().st_size > 0: return True
        except Exception: pass
    return False
def external_download(url, info, job):
    if not isinstance(info, dict): return False
    audio = job["kind"] == "audio"
    fm = [f for f in info.get("formats") or [] if isinstance(f, dict) and f.get("url")]
    title = safe_name(info.get("title") or "media"); vid = info.get("id") or "id"
    mh = SETTINGS["max_height"]; prog = [f for f in fm if f.get("protocol") in ("https","http")]
    if audio:
        cands = [f for f in prog if f.get("vcodec") in (None,"none") and f.get("acodec") not in (None,"none")]
        cands.sort(key=lambda f: f.get("abr") or 0, reverse=True)
    else:
        cands = [f for f in prog if f.get("vcodec") not in (None,"none") and f.get("acodec") not in (None,"none")]
        if mh: cands = [f for f in cands if (f.get("height") or 0) <= mh] or cands
        cands.sort(key=lambda f: f.get("height") or 0, reverse=True)
    s = SETTINGS
    for f in cands[:3]:
        ext = f.get("ext") or "mp4"; out = job["dir"] / f"{title} [{vid}].{ext}"
        furl = f["url"]; headers = f.get("http_headers") or {}
        host = urlparse(furl).hostname or ""; port = 443 if furl.startswith("https") else 80
        ips = (resolve_with("udp", host) or resolve_with("doh", host)) if host else []
        tools = []
        if shutil.which("curl"):
            cmd = ["curl","-L","--fail","--retry","3","--connect-timeout",str(s["socket_timeout"]),"-#"]
            if s["ip_version"] == "ipv4": cmd.append("--ipv4")
            elif s["ip_version"] == "ipv6": cmd.append("--ipv6")
            if s["proxy"]: cmd += ["-x", s["proxy"]]
            if not s["verify_tls"]: cmd.append("-k")
            if ips and not s["proxy"]: cmd += ["--resolve", f"{host}:{port}:{ips[0]}"]
            for k, v in headers.items(): cmd += ["-H", f"{k}: {v}"]
            tools.append(("curl", cmd + ["-o", str(out), furl]))
        if shutil.which("wget") and not s["proxy"]:
            cmd = ["wget","--tries=3","-O",str(out)]
            if not s["verify_tls"]: cmd.append("--no-check-certificate")
            for k, v in headers.items(): cmd.append(f"--header={k}: {v}")
            tools.append(("wget", cmd + [furl]))
        for name, cmd in tools:
            info_line(name)
            try:
                r = subprocess.run(cmd, timeout=7200)
                if r.returncode == 0 and out.exists() and out.stat().st_size > 0: return True
            except Exception as e: err_unique(f"{name}: {type(e).__name__}: {e}")
            _rm(out)
    if not audio and HAS_FFMPEG:
        hls = [f for f in fm if f.get("protocol") in ("m3u8","m3u8_native")]
        hls.sort(key=lambda f: f.get("height") or 0, reverse=True)
        if mh: hls = [f for f in hls if (f.get("height") or 0) <= mh] or hls
        for f in hls[:2]:
            out = job["dir"] / f"{title} [{vid}].mp4"
            headers = f.get("http_headers") or {}
            hs = "".join(f"{k}: {v}\r\n" for k, v in headers.items())
            cmd = [FFMPEG_BIN,"-y"]
            if hs: cmd += ["-headers", hs]
            cmd += ["-i", f["url"], "-c", "copy", "-bsf:a", "aac_adtstoasc", str(out)]
            try:
                r = subprocess.run(cmd, capture_output=True, text=True, timeout=7200)
                if r.returncode == 0 and out.exists() and out.stat().st_size > 0: return True
            except Exception as e: err_unique(f"ffmpeg: {type(e).__name__}: {e}")
    return False
def prompt_proxy():
    if is_unattended(): return False
    warn_line(T("net_help")); print(c(f"\n{T('set_proxy')}:", CYAN))
    for i, t in enumerate(PROXY_TEMPLATES, 1):
        disp = t if t else T("empty"); cur = " [*]" if t == SETTINGS.get("proxy", "") else ""
        print(f"  {i}. {disp}{cur}")
    print(f"  0. {T('templates_custom')}")
    ch = ask_input(c(f"{T('choice')} [0]: ", YELLOW), timeout=PT())
    if ch is None: return False
    v = ""
    if ch.isdigit() and 1 <= int(ch) <= len(PROXY_TEMPLATES): v = PROXY_TEMPLATES[int(ch) - 1]
    else:
        raw = ask_input(c(T("proxy_prompt") + ": ", YELLOW), timeout=PT())
        if raw is None: return False
        v = raw
    if not v: return False
    if not re.match(r"^(https?|socks4a?|socks5h?)://\S+$", v, re.I): err_line(T("proxy_invalid")); return False
    SETTINGS["proxy"] = v; save_settings(SETTINGS); reset_dns(); QUICK["on"] = False
    info_line(T("proxy_set")); return True
def prepare_network(url):
    QUICK["on"] = False
    if preflight(url): return True
    if prompt_proxy(): return True
    if confirm(T("preflight_continue"), default=True, timeout=PT()): QUICK["on"] = True; return True
    return False
def download_chain(url, job, info, win, allow_proxy=True):
    selectors = list(job["selectors"]); strategies = build_strategies(url, win); net_fail = 0
    for st in strategies:
        if net_fail >= 2: break
        for sel, mf in selectors:
            job["merge_fmt"] = mf
            info_line(f"{T('strategy')}: {st['name']} | {T('selector')}: {trunc(sel, 45)}")
            ok, err = run_any(url, sel, st, job)
            if ok: return True
            show_msgs(err)
            if is_net_error(err): net_fail += 1; break
            if not is_format_error(err): break
    if net_fail >= 2: QUICK["on"] = True
    first = strategies[0]
    if shutil.which("yt-dlp"):
        info_line(T("trying_binary"))
        for sel, mf in selectors:
            job["merge_fmt"] = mf
            ok, err = run_binary(url, sel, first, job)
            if ok: return True
            show_msgs(err)
            if not is_format_error(err) and not is_net_error(err): break
    if job["kind"] == "video" and "rutube.ru" in url:
        if rutube_download(url, job): return True
    info_line(T("trying_generic"))
    for sel, mf in selectors:
        job["merge_fmt"] = mf
        ok, err = run_any(url, sel, None, job, extra={"force_generic_extractor":True}, flags=("--force-generic-extractor",))
        if ok: return True
        show_msgs(err)
        if not is_format_error(err) and not is_net_error(err): break
    if info:
        info_line(T("trying_external"))
        if external_download(url, info, job): return True
    if net_fail and allow_proxy and prompt_proxy(): return download_chain(url, job, info, win, allow_proxy=False)
    if SETTINGS["verify_tls"] and confirm(T("retry_tls"), timeout=PT()):
        for sel, mf in selectors:
            job["merge_fmt"] = mf
            ok, err = run_any(url, sel, first, job, extra={"nocheckcertificate":True}, flags=("--no-check-certificate",))
            if ok: return True
            show_msgs(err)
    return False

# Задания на скачивание
def make_job(kind):
    if kind == "audio": return {"kind":"audio","dir":AUDIO_DIR,"merge":False,"merge_fmt":None,"selectors":[]}
    if kind == "photo": return {"kind":"photo","dir":PHOTOS_DIR,"merge":False,"merge_fmt":None,"selectors":[]}
    return {"kind":"video","dir":VIDEOS_DIR,"merge":HAS_FFMPEG,"merge_fmt":"mp4" if HAS_FFMPEG else None,"selectors":[]}
def attempt_download_video(url, prio="mp4"):
    if not valid_url(url): err_line(f"{T('invalid_url')}: {url}"); return False, None
    if yt_dlp is None: err_line(T("ytdlp_missing")); return False, None
    SEEN_ERRORS.clear(); refresh_ffmpeg()
    if not prepare_network(url): err_line(T("network_unavailable")); return False, None
    if not HAS_FFMPEG: warn_line(T("no_ffmpeg_warn"))
    job = make_job("video"); before = snapshot(VIDEOS_DIR)
    info, win = extract_info_smart(url)
    if not isinstance(info, dict): warn_line(T("info_failed"))
    title = (info.get("title") if isinstance(info, dict) else None) or trunc(url, 40)
    info_line(f"{T('downloading')}: {trunc(title, 50)}")
    chosen = select_format(info) if prio == "manual" and not is_unattended() else None
    job["selectors"] = video_selectors(prio, chosen)
    info_line(f"{T('selector')}: {trunc(job['selectors'][0][0], 60)}")
    if not download_chain(url, job, info, win): err_line(T("all_exhausted")); warn_line(T("fail_hint")); return False, None
    f = newest_changed(VIDEOS_DIR, before, VIDEO_EXTS) or find_by_id(VIDEOS_DIR, info, VIDEO_EXTS)
    if f is None: err_line(T("file_not_found")); return False, None
    ok_line(f"{T('download_done')}: {f.name}"); return True, f
def attempt_download_audio(url, prio="m4a"):
    if not valid_url(url): err_line(f"{T('invalid_url')}: {url}"); return False, None
    if yt_dlp is None: err_line(T("ytdlp_missing")); return False, None
    SEEN_ERRORS.clear(); refresh_ffmpeg()
    if not prepare_network(url): err_line(T("network_unavailable")); return False, None
    job = make_job("audio"); before = snapshot(AUDIO_DIR)
    info, win = extract_info_smart(url)
    if not isinstance(info, dict): warn_line(T("info_failed"))
    title = (info.get("title") if isinstance(info, dict) else None) or trunc(url, 40)
    info_line(f"{T('downloading')}: {trunc(title, 50)}")
    job["selectors"] = audio_selectors(prio)
    info_line(f"{T('selector')}: {trunc(job['selectors'][0][0], 60)}")
    if not download_chain(url, job, info, win): err_line(T("all_exhausted")); warn_line(T("fail_hint")); return False, None
    f = newest_changed(AUDIO_DIR, before) or find_by_id(AUDIO_DIR, info)
    if f is None: err_line(T("file_not_found")); return False, None
    ok_line(f"{T('download_done')}: {f.name}"); return True, f

# Файловые операции
def move_to_fix(path):
    if not path or not path.exists(): return False
    dest = FIX_DIR / path.name; n = 1
    while dest.exists(): dest = FIX_DIR / f"{path.stem}_{n}{path.suffix}"; n += 1
    try: path.rename(dest); ok_line(f"{T('fm_moved')}: {dest.name}"); return True
    except OSError as e: err_line(f"{T('fm_failed')}: {e}"); return False
def rename_file(path, new_name):
    if not new_name.endswith(path.suffix): new_name += path.suffix
    new_name = re.sub(r'[\\/:*?"<>|]', "_", new_name); new_path = path.parent / new_name
    if new_path.exists() and new_path != path: err_line(f"{T('fm_failed')}: {T('fm_exists')}"); return path
    try: path.rename(new_path); ok_line(f"{T('fm_renamed')}: {new_name}"); return new_path
    except OSError as e: err_line(f"{T('fm_failed')}: {e}"); return path
def show_ready(path, is_audio=False):
    try: size = path.stat().st_size
    except OSError: size = 0
    print(); print(c("="*40, GREEN))
    print(c("  " + T("audio_ready" if is_audio else "video_ready"), GREEN))
    print(c("="*40, GREEN))
    print(c(f"  {T('file')}: {path.name}", CYAN))
    print(c(f"  {T('size')}: {fmt_size(size)}", CYAN))
    print(c(f"  {T('dl_dest')}: {path.parent}", CYAN)); print()
def pp_confirm(prompt, default=False):
    if is_unattended(): return False
    if PP["timed_out"]: return False
    r = confirm(prompt, default, timeout=PT())
    if INPUT_STATE["timeout"]: PP["timed_out"] = True; info_line(T("pp_skip_hint")); return False
    return r
def maybe_convert_video(f):
    vkey = SETTINGS["video_codec"]; mode = SETTINGS["auto_convert"]
    if mode == "never" or not HAS_FFMPEG or check_compat(f, vkey): return f
    warn_line(f"{T('compat_warning')}: {trunc(f.name, 40)}")
    if mode == "always" or pp_confirm(T("convert_prompt")):
        nf, st = convert_file(f, vkey)
        if st: ok_line(f"{T('convert_done')}: {nf.name}")
        return nf
    info_line(T("convert_cancelled")); return f
def post_process_files(items):
    items = [it for it in items if it and it.get("path") and Path(it["path"]).exists()]
    if not items: return []
    PP["timed_out"] = False
    print(); header(T("post_process"))
    stage = []
    for it in items:
        f = it["path"]
        if it["audio"]:
            nf, st = convert_audio(f, SETTINGS["audio_codec"])
            if st: ok_line(f"{T('convert_done')}: {nf.name}")
            f = nf
        else: f = maybe_convert_video(f)
        stage.append({"path":f,"audio":it["audio"]})
    result = []
    for it in stage:
        f = it["path"]; audio = it["audio"]
        if not f.exists(): continue
        show_ready(f, audio)
        if SETTINGS["ask_rename"] and pp_confirm(f"{T('rename_prompt')} '{trunc(f.name, 40)}'"):
            new_name = ask_input(c(f"{T('fm_new_name')}: ", YELLOW), timeout=PT())
            if INPUT_STATE["timeout"]: PP["timed_out"] = True; info_line(T("pp_skip_hint"))
            elif new_name: f = rename_file(f, new_name)
        if not audio and SETTINGS["ask_fix"] and pp_confirm(f"{T('move_fix_prompt')} '{trunc(f.name, 40)}'"):
            move_to_fix(f)
        result.append(f)
    return result
def finish_session(items, failed):
    if failed:
        print(); err_line(f"{T('failed_summary')}: {len(failed)}")
        for u in failed: print("  - " + trunc(u, 70))
    if items: post_process_files(items)

# Поиск / приоритет
def find_videos_on_page(page_url):
    info_line(f"{T('scanning')}: {trunc(page_url, 60)}")
    if yt_dlp is None: return []
    o = base_opts(extract_flat=True, noplaylist=False); lg = o["logger"]
    try:
        with yt_dlp.YoutubeDL(o) as ydl: info = ydl.extract_info(page_url, download=False)
    except Exception as e: show_msgs(report(e, lg)); return []
    if not isinstance(info, dict): return []
    if info.get("entries") is not None:
        urls = []
        for e in info["entries"]:
            if isinstance(e, dict):
                u = e.get("webpage_url") or e.get("url")
                if isinstance(u, str) and u.startswith(("http://","https://")): urls.append(u)
        urls = list(dict.fromkeys(urls)); ok_line(f"{T('found_videos')}: {len(urls)}"); return urls
    u = info.get("webpage_url") or info.get("original_url") or info.get("url")
    return [u] if isinstance(u, str) and valid_url(u) else []
def ask_priority(audio_only):
    kind = "audio" if audio_only else "video"
    if is_unattended(): return LAST_PRIO[kind]
    if audio_only: title = T("prio_audio_title"); opts = [("m4a","prio_a_m4a"),("opus","prio_a_opus"),("mp3","prio_a_mp3"),("any","prio_a_any")]
    else: title = T("prio_video_title"); opts = [("mp4","prio_v_mp4"),("vp9","prio_v_vp9"),("av1","prio_v_av1"),("any","prio_v_any"),("manual","prio_v_manual")]
    default = LAST_PRIO[kind]; keys = [k for k,_ in opts]; dindex = keys.index(default) + 1 if default in keys else 1
    print(c(f"\n{title}:", CYAN))
    for i, (k, lk) in enumerate(opts, 1): print(f"  {i}. {T(lk)}{' [*]' if i == dindex else ''}")
    ch = ask_input(c(f"{T('choice')} [{dindex}]: ", YELLOW))
    if not ch: return keys[dindex-1]
    if ch.isdigit() and 1 <= int(ch) <= len(keys): LAST_PRIO[kind] = keys[int(ch)-1]; return keys[int(ch)-1]
    warn_line(T("invalid_default")); return keys[dindex-1]
def download_one(url, audio_only, prio, items, failed):
    if audio_only: ok, fp = attempt_download_audio(url, prio)
    else: ok, fp = attempt_download_video(url, prio)
    if ok and fp: items.append({"path":fp,"audio":audio_only}); return True
    failed.append(url); return False
def process_links(links, audio_only, prio, items, failed):
    for raw_url in links:
        url = fix_url(raw_url)
        if not valid_url(url): err_line(f"{T('invalid_url')}: {raw_url}"); failed.append(raw_url); continue
        if audio_only or any(m in url.lower() for m in DIRECT): download_one(url, audio_only, prio, items, failed); continue
        found = find_videos_on_page(url)
        if not found: warn_line(f"{T('no_videos')}: {url}"); failed.append(url); continue
        if len(found) == 1: download_one(found[0], False, prio, items, failed); continue
        if is_unattended():
            for u in found: download_one(u, False, prio, items, failed)
            continue
        print(c(f"\n{T('multiple_videos')}:", CYAN))
        for i, u in enumerate(found, 1): print(f"  {i}. {trunc(u, 60)}")
        ch = ask_input(c(f"{T('number_or_all')}: ", YELLOW), timeout=PT())
        if not ch: continue
        nums = parse_multi(ch, len(found))
        if not nums: err_line(T("invalid_choice")); continue
        for n in nums: download_one(found[n-1], False, prio, items, failed)
def download_session(audio_only):
    links = []; info_line(T("enter_urls")); info_line(T("enter_urls_hint"))
    while True:
        line = ask_input(c("> ", GREEN))
        if line is None or not line or line.lower() == "q": break
        links.append(line)
    if not links: return
    prio = ask_priority(audio_only); info_line(T("cancel_hint"))
    items, failed = [], []
    try: process_links(links, audio_only, prio, items, failed)
    except KeyboardInterrupt:
        if items: info_line(f"{T('kept_files')}: {len(items)}")
        raise
    finish_session(items, failed); print()

    # ==========================================================
#  ПОИСК (YouTube / RuTube / SoundCloud / произвольная страница)
# ==========================================================
def flat_entries(target, limit=10):
    """Плоский список видео с поисковой страницы или URL."""
    if yt_dlp is None: err_line(T("ytdlp_missing")); return []
    o = base_opts(None, extract_flat="in_playlist", noplaylist=False, playlistend=limit)
    lg = o["logger"]
    try:
        with yt_dlp.YoutubeDL(o) as ydl: info = ydl.extract_info(target, download=False)
    except Exception as e: show_msgs(report(e, lg)); err_line(T("search_failed")); return []
    if not isinstance(info, dict): return []
    out = []; raw = info.get("entries")
    if raw is None:
        u = info.get("webpage_url") or info.get("original_url") or target
        if valid_url(u): out.append({"title": info.get("title") or u, "url": u, "duration": info.get("duration")})
        return out
    try:
        for e in raw:
            if not isinstance(e, dict): continue
            u = e.get("webpage_url") or e.get("url")
            if not (isinstance(u, str) and u.startswith(("http://","https://"))):
                vid = e.get("id")
                if vid and str(e.get("ie_key","")).lower() == "youtube":
                    u = f"https://www.youtube.com/watch?v={vid}"
                else: continue
            out.append({"title": e.get("title") or u, "url": u, "duration": e.get("duration")})
            if len(out) >= limit: break
    except Exception as e: show_msgs(report(e, lg))
    return out

def search_rutube(query, limit=10):
    """Поиск на RuTube через публичное API."""
    from urllib.parse import quote as _q
    api = "https://rutube.ru/api/search/video/?query=" + _q(query, safe="") + "&format=json"
    try: data = http_json(api)
    except Exception as e: err_line(f"{T('search_failed')}: {type(e).__name__}: {e}"); return []
    res = data.get("results") if isinstance(data, dict) else None
    out = []
    for r in res or []:
        if not isinstance(r, dict): continue
        u = r.get("video_url") or ""
        if not u and r.get("id"): u = f"https://rutube.ru/video/{r['id']}/"
        if not valid_url(u): continue
        out.append({"title": r.get("title") or u, "url": u, "duration": r.get("duration")})
        if len(out) >= limit: break
    return out

def search_videos():
    """Меню поиска: YouTube/RuTube/SoundCloud/любой сайт."""
    header(T("menu_search"))
    if yt_dlp is None: err_line(T("ytdlp_missing")); return
    print(c(f"{T('search_where')}", CYAN))
    print(f"  1. YouTube\n  2. RuTube\n  3. SoundCloud\n  4. {T('search_other')}\n  0. {T('fm_back')}")
    ch = ask_input(c(f"{T('choice')}: ", GREEN))
    if not ch or ch in ("0","q"): return
    entries = []; audio_only = False
    if ch in ("1","2","3"):
        q = ask_input(c(f"{T('search_query')}: ", YELLOW))
        if not q: return
        host_url = {"1":"https://www.youtube.com/","2":"https://rutube.ru/","3":"https://soundcloud.com/"}[ch]
        SEEN_ERRORS.clear()
        if not prepare_network(host_url):
            err_line(T("network_unavailable")); return
        info_line(f"{T('search_searching')}: {trunc(q, 60)}")
        if ch == "1": entries = flat_entries("ytsearch10:" + q, 10)
        elif ch == "2": entries = search_rutube(q, 10)
        else: entries = flat_entries("scsearch10:" + q, 10); audio_only = True
    elif ch == "4":
        u = ask_input(c(f"{T('search_url')}: ", YELLOW)); u = fix_url(u)
        if not u or not valid_url(u): err_line(f"{T('invalid_url')}: {u or ''}"); return
        SEEN_ERRORS.clear()
        if not prepare_network(u): err_line(T("network_unavailable")); return
        info_line(f"{T('scanning')}: {trunc(u, 60)}")
        entries = flat_entries(u, 30)
    else: err_line(T("invalid_choice")); return
    if not entries: warn_line(T("search_empty")); return
    print(c(f"\n{T('search_results')}:", CYAN))
    for i, e in enumerate(entries, 1):
        d = fmt_dur(e.get("duration"))
        print(f"  {i}. {trunc(e['title'], 58)}{' [' + d + ']' if d else ''}")
    sel = ask_input(c(f"{T('search_select')}: ", YELLOW))
    if not sel: return
    nums = parse_multi(sel, len(entries))
    if not nums: err_line(T("invalid_choice")); return
    if not audio_only:
        k = ask_input(c(f"{T('search_kind')}: ", YELLOW))
        audio_only = (k == "2")
    prio = ask_priority(audio_only); info_line(T("cancel_hint"))
    items, failed = [], []
    try:
        for n in nums: download_one(entries[n-1]["url"], audio_only, prio, items, failed)
    except KeyboardInterrupt:
        if items: info_line(f"{T('kept_files')}: {len(items)}")
        raise
    finish_session(items, failed)

# ==========================================================
#  ПЕРЕКОДИРОВАНИЕ ГОТОВЫХ ФАЙЛОВ
# ==========================================================
def reencode_menu():
    """Пакетное перекодирование видео/аудио в выбранных папках."""
    header(T("menu_reencode")); ensure_dir()
    if not HAS_FFMPEG: err_line(T("ffmpeg_missing")); return
    d = file_manager_choose_dir()
    if d is None: return
    files = list_files(d)
    if not files: warn_line(T("fm_empty")); return
    print_files(files)
    nums = ask_numbers(f"{T('fm_numbers')} (1-{len(files)}, all): ", len(files))
    if not nums: return
    targets = [files[n-1] for n in nums]
    vids = [t for t in targets if t.suffix.lower() not in AUDIO_EXTS]
    auds = [t for t in targets if t.suffix.lower() in AUDIO_EXTS]
    keep = confirm(T("reenc_keep"), default=True)
    info_line(T("cancel_hint"))
    if vids:
        keys = list(VIDEO_CODECS.keys())
        cur = keys.index(SETTINGS["video_codec"]) if SETTINGS["video_codec"] in keys else 0
        idx = pick_from(T("set_video_codec"), [T(VIDEO_CODECS[k]["label_key"]) for k in keys], cur)
        if idx is None: err_line(T("invalid_choice"))
        else:
            for t in vids:
                nf, st = convert_file(t, keys[idx], keep)
                if st: ok_line(f"{T('reenc_done')}: {nf.name}")
    if auds:
        keys = list(AUDIO_CODECS.keys())
        cur = keys.index(SETTINGS["audio_codec"]) if SETTINGS["audio_codec"] in keys else 0
        idx = pick_from(T("set_audio_codec"), [T(AUDIO_CODECS[k]["label_key"]) for k in keys], cur)
        if idx is None: err_line(T("invalid_choice"))
        else:
            for t in auds:
                nf, st = convert_audio(t, keys[idx], keep, force=True)
                if st: ok_line(f"{T('reenc_done')}: {nf.name}")
                elif st is None: info_line(T("reenc_skipped"))

# ==========================================================
#  ЭТО ВСЁ ЕЩЁ PART 2A — ниже начинается PART 2B
# ==========================================================

# ============================================================
#  ПРОДОЛЖЕНИЕ В PART 2B: новые модули (фото, текст, код,
#  метаданные, advanced, privacy, reports, profiles, batch),
#  обновлённые диагностика/отладка, main_menu, main.
#  Не закрывайте PYEOF пока не получите 2B.
# ============================================================
# === PART 2B CONTINUES IN NEXT REPLY ===
# ==========================================================
#  ФОТО: скачивание и редактирование (ImageMagick)
# ==========================================================
def download_photos(url):
    """Скачивает фото/галерею через gallery-dl → прямое → yt-dlp-thumbnail."""
    ensure_dir()
    if not valid_url(url):
        err_line(f"{T('invalid_url')}: {url}"); return False
    info_line(f"Photos: {trunc(url, 60)}")
    # Вариант 1: gallery-dl (лучший для галерей)
    if shutil.which("gallery-dl"):
        try:
            r = subprocess.run(["gallery-dl", "-D", str(PHOTOS_DIR), url], timeout=1800, capture_output=True, text=True)
            if r.returncode == 0:
                count = sum(1 for f in PHOTOS_DIR.iterdir() if f.is_file())
                ok_line(f"{T('photo_download_ok')}: {PHOTOS_DIR} ({count})"); return True
            show_msgs(r.stderr)
        except Exception as e: warn_line(f"gallery-dl: {e}")
    # Вариант 2: прямое скачивание, если URL ведёт на файл-картинку
    try:
        clean = url.lower().split("?")[0]
        if any(clean.endswith(ext) for ext in PHOTO_EXTS):
            name = Path(urlparse(url).path).name or "photo.jpg"
            out = PHOTOS_DIR / safe_name(name)
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with make_opener().open(req, timeout=60) as r: out.write_bytes(r.read())
            if out.exists() and out.stat().st_size > 0:
                ok_line(f"{T('photo_download_ok')}: {out.name}"); return True
    except Exception as e: warn_line(f"direct: {e}")
    # Вариант 3: yt-dlp thumbnail (обложка видео)
    if yt_dlp is not None:
        try:
            o = base_opts(None, skip_download=True, writethumbnail=True, outtmpl=str(PHOTOS_DIR / "%(title).150B.%(ext)s"))
            with yt_dlp.YoutubeDL(o) as ydl: ydl.download([url])
            if any(PHOTOS_DIR.iterdir()): ok_line(f"{T('photo_download_ok')}: {PHOTOS_DIR}"); return True
        except Exception: pass
    err_line(T("failed_summary")); return False

def photo_apply_op(src_path, op, value=None):
    """Применяет ImageMagick-операцию, сохраняет в *_edited (кроме convert)."""
    if not shutil.which("convert"): err_line("ImageMagick convert не найден"); return False
    src = Path(src_path)
    if not src.exists(): err_line(f"Нет файла: {src_path}"); return False
    if op == "convert" and value: out = src.with_suffix("." + value.lstrip(".").lower())
    else: out = src.with_name(src.stem + "_edited" + src.suffix)
    cmd = ["convert", str(src)]
    if op == "resize": cmd += ["-resize", value]
    elif op == "crop": cmd += ["-crop", value]
    elif op == "rotate": cmd += ["-rotate", value]
    elif op == "auto_orient": cmd += ["-auto-orient"]
    elif op != "convert": return False
    if SETTINGS.get("photo_quality") and out.suffix.lower() in (".jpg",".jpeg"):
        cmd += ["-quality", str(SETTINGS["photo_quality"])]
    cmd.append(str(out))
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        if r.returncode == 0 and out.exists() and out.stat().st_size > 0:
            ok_line(f"{T('photo_created')}: {out.name}"); return True
        if r.stderr: err_line(r.stderr.strip()[:300])
    except Exception as e: err_line(f"convert: {e}")
    return False

def photo_edit_menu():
    header(T("photo_edit_menu"))
    print(f"  1. {T('photo_src_local')}\n  2. {T('photo_src_download')}\n  0. {T('fm_back')}")
    ch = ask_input(c(f"{T('choice')}: ", GREEN))
    if ch is None or ch in ("0","q"): return
    path = None
    if ch == "1":
        p = ask_input(c("Путь: ", YELLOW))
        if p:
            pp = Path(p).expanduser()
            if pp.exists(): path = pp
            else: err_line(f"Не найдено: {p}"); return
    elif ch == "2":
        u = ask_input(c("URL: ", YELLOW))
        if not u or not download_photos(u): return
        files = sorted([f for f in PHOTOS_DIR.iterdir() if f.is_file()], key=lambda x: x.stat().st_mtime, reverse=True)[:20]
        if not files: return
        print_files(files)
        nums = ask_numbers(f"Номер (1-{len(files)}): ", len(files))
        if nums: path = files[nums[0]-1]
    else: return
    if not path: return
    while True:
        header(f"{T('photo_edit_menu')} — {path.name}")
        print(f"  1. {T('photo_resize')}\n  2. {T('photo_crop')}\n  3. {T('photo_rotate')}")
        print(f"  4. {T('photo_convert')}\n  5. {T('photo_auto_orient')}\n  0. {T('fm_back')}")
        op = ask_input(c(f"{T('choice')}: ", GREEN))
        if op is None or op in ("0","q"): return
        if op == "1":
            v = ask_input(c(f"{T('photo_enter_size')}: ", YELLOW))
            if v: photo_apply_op(path, "resize", v)
        elif op == "2":
            v = ask_input(c(f"{T('photo_enter_crop')}: ", YELLOW))
            if v: photo_apply_op(path, "crop", v)
        elif op == "3":
            v = ask_input(c(f"{T('photo_enter_angle')}: ", YELLOW))
            if v: photo_apply_op(path, "rotate", v)
        elif op == "4":
            v = ask_input(c(f"{T('photo_enter_ext')}: ", YELLOW))
            if v: photo_apply_op(path, "convert", v)
        elif op == "5": photo_apply_op(path, "auto_orient")

# ==========================================================
#  МЕТАДАННЫЕ (exiftool): view / strip / templates / deep / verify / GPS
# ==========================================================
META_TEMPLATES = {
    "anon": {"Artist":"Anonymous","Copyright":"Public Domain","Make":"Unknown","Model":"Unknown","Software":"MediaForge","LensModel":"","SerialNumber":"","DateTimeOriginal":"1970:01:01 00:00:00"},
    "camera": {"Make":"Unknown","Model":"Unknown","LensModel":"","SerialNumber":""},
    "date": {"DateTimeOriginal":"1970:01:01 00:00:00","CreateDate":"1970:01:01 00:00:00","ModifyDate":"1970:01:01 00:00:00"},
    "author": {"Artist":"Anonymous","Copyright":"Public Domain"},
    "software": {"Software":"MediaForge"},
    "gps": {"GPS:all":""},
}
COMMON_TAGS = ["Artist","Copyright","Make","Model","Software","LensModel","SerialNumber",
               "DateTimeOriginal","CreateDate","ModifyDate","GPS:all","GPSLatitude","GPSLongitude","Orientation"]

def exiftool_available(): return shutil.which("exiftool") is not None
def get_metadata(path):
    if not exiftool_available(): return {}
    try:
        r = subprocess.run(["exiftool","-json","-G","-s",str(path)], capture_output=True, text=True, timeout=60)
        if r.returncode == 0:
            data = json.loads(r.stdout)
            if isinstance(data, list) and data: return data[0]
    except Exception as e: warn_line(f"exiftool: {e}")
    return {}
def meta_strip_all(path):
    """Удаляет все метаданные; для видео fallback на ffmpeg -map_metadata -1."""
    if not exiftool_available(): err_line("exiftool не установлен"); return False
    try:
        r = subprocess.run(["exiftool","-overwrite_original","-all=",str(path)], capture_output=True, text=True, timeout=180)
        if r.returncode == 0: return True
    except Exception: pass
    if HAS_FFMPEG and Path(path).suffix.lower() in VIDEO_EXTS:
        temp = str(path) + ".vdtmp" + Path(path).suffix
        try:
            subprocess.run([FFMPEG_BIN,"-y","-i",str(path),"-map_metadata","-1","-c","copy",temp], check=True, capture_output=True, timeout=7200)
            os.replace(temp, path); return True
        except Exception:
            _rm(temp)
    return False
def meta_strip_selective(path, tags):
    if not exiftool_available(): return False
    args = ["exiftool","-overwrite_original"] + [f"-{t}=" for t in tags] + [str(path)]
    try:
        r = subprocess.run(args, capture_output=True, text=True, timeout=180); return r.returncode == 0
    except Exception: return False
def meta_set_template(path, tpl_key):
    if not exiftool_available(): return False
    tpl = META_TEMPLATES.get(tpl_key)
    if not tpl: return False
    args = ["exiftool","-overwrite_original"]
    for k, v in tpl.items():
        args.append(f"-{k}={v}")
    args.append(str(path))
    try:
        r = subprocess.run(args, capture_output=True, text=True, timeout=180); return r.returncode == 0
    except Exception: return False
def meta_deep_clean(path):
    """-all= + явно удаляем XMP/IPTC/ICC/thumbnail-блоки."""
    if not exiftool_available(): return False
    args = ["exiftool","-overwrite_original","-all=","-XMP:all=","-IPTC:all=","-ICC_Profile:all=",
            "-ThumbnailImage=","-Photoshop:all=","-JFIF:all=","-EXIF:all=",str(path)]
    try:
        r = subprocess.run(args, capture_output=True, text=True, timeout=180); return r.returncode == 0
    except Exception: return False
def meta_verify(path):
    md = get_metadata(path)
    risky = [k for k in md if any(t in k for t in ("GPS","Serial","Artist","Copyright","Make","Model","Software"))]
    if risky:
        warn_line(f"{T('code_errors')}: {', '.join(risky[:10])}"); return False
    ok_line(f"{T('code_clean')}: {Path(path).name}"); return True
def meta_gps_preview(path):
    md = get_metadata(path)
    lat = md.get("Composite:GPSLatitude") or md.get("EXIF:GPSLatitude")
    lon = md.get("Composite:GPSLongitude") or md.get("EXIF:GPSLongitude")
    if lat and lon:
        info_line(f"GPS: {lat}, {lon}")
        print(c(f"  https://www.openstreetmap.org/?mlat={lat}&mlon={lon}", CYAN))
    else: warn_line("GPS не найден")

def _iter_media_files(target):
    p = Path(target)
    if p.is_file(): yield p
    elif p.is_dir():
        for f in p.rglob("*"):
            if f.is_file() and f.suffix.lower() in (VIDEO_EXTS + AUDIO_EXTS + PHOTO_EXTS): yield f

def metadata_menu():
    if not exiftool_available():
        err_line("exiftool не установлен. Установите: apk add exiftool"); return
    header(T("meta_title"))
    print(f"  1. {T('meta_view')}\n  2. {T('meta_strip_all')}\n  3. {T('meta_strip_selective')}")
    print(f"  4. {T('meta_set_template')}\n  5. {T('meta_verify')}\n  6. {T('meta_deep_clean')}")
    print(f"  7. {T('meta_gps_preview')}\n  0. {T('fm_back')}")
    ch = ask_input(c(f"{T('choice')}: ", GREEN))
    if ch is None or ch in ("0","q"): return
    tgt = ask_input(c(f"{T('meta_dir_or_file')}: ", YELLOW))
    if not tgt: return
    path = Path(tgt).expanduser()
    if not path.exists(): err_line(f"Не найдено: {tgt}"); return
    files = list(_iter_media_files(path))
    if not files: warn_line("Файлов не найдено"); return
    info_line(f"Файлов: {len(files)}")
    count_ok = 0
    if ch == "1":
        for f in files:
            md = get_metadata(f)
            print(c(f"\n{f.name}", CYAN))
            for k, v in md.items():
                if v not in (None, "", []): print(f"  {k}: {v}")
        return
    if ch == "2":
        if not confirm(f"{T('meta_strip_all')} ({len(files)})?"): return
        for f in files:
            if meta_strip_all(f): count_ok += 1; ok_line(f.stem)
    elif ch == "3":
        print(c(f"\n{','.join(f'[{i}]{t}' for i,t in enumerate(COMMON_TAGS,1))}", CYAN))
        sel = ask_input(c(f"{T('meta_tags_select')}: ", YELLOW))
        nums = parse_multi(sel or "", len(COMMON_TAGS))
        if not nums: return
        tags = [COMMON_TAGS[i-1] for i in nums]
        for f in files:
            if meta_strip_selective(f, tags): count_ok += 1
    elif ch == "4":
        print("  1. anon\n  2. camera\n  3. date\n  4. author\n  5. software\n  6. gps")
        t = ask_input(c(f"{T('meta_template_select')}: ", YELLOW))
        keys = {"1":"anon","2":"camera","3":"date","4":"author","5":"software","6":"gps"}
        if t not in keys: return
        for f in files:
            if meta_set_template(f, keys[t]): count_ok += 1
    elif ch == "5":
        for f in files:
            if meta_verify(f): count_ok += 1
        return
    elif ch == "6":
        if not confirm(f"{T('meta_deep_clean')} ({len(files)})?"): return
        for f in files:
            if meta_deep_clean(f): count_ok += 1
    elif ch == "7":
        for f in files: meta_gps_preview(f)
        return
    ok_line(f"{T('meta_done')}: {count_ok}/{len(files)}")

# ==========================================================
#  ТЕКСТ: скачивание, aspell, поиск, редактирование
# ==========================================================
def text_download(url):
    ensure_dir()
    if not valid_url(url): err_line(f"{T('invalid_url')}: {url}"); return None
    try:
        req = urllib.request.Request(url, headers={"User-Agent": UA})
        with make_opener().open(req, timeout=60) as r:
            data = r.read()
        name = safe_name(Path(urlparse(url).path).name or "text.txt")
        out = TEXT_DIR / name
        out.write_bytes(data)
        ok_line(f"{T('text_downloaded')}: {out}"); return out
    except Exception as e: err_line(f"{T('text_download')}: {e}"); return None
def spell_check(path, lang="ru"):
    if not shutil.which("aspell"): err_line("aspell не установлен"); return
    langs = ["ru","en"] if lang == "both" else [lang]
    for lg in langs:
        try:
            txt = Path(path).read_text(encoding="utf-8", errors="ignore")
            r = subprocess.run(["aspell","list",f"--lang={lg}","--encoding=utf-8"], input=txt, capture_output=True, text=True, timeout=120)
            words = sorted(set(r.stdout.strip().splitlines()))
            if words:
                warn_line(f"[{lg}] {T('text_spell_found')}: {len(words)}")
                for w in words[:25]: print(f"  - {w}")
                if len(words) > 25: print(f"  ... +{len(words)-25}")
            else: ok_line(f"[{lg}] {T('text_spell_ok')}")
        except Exception as e: err_line(f"aspell {lg}: {e}")
def text_search(path, query):
    try:
        lines = Path(path).read_text(encoding="utf-8", errors="ignore").splitlines()
        matches = [(i+1, ln) for i, ln in enumerate(lines) if query.lower() in ln.lower()]
        if matches:
            ok_line(f"{T('text_search_found')}: {len(matches)}")
            for n, ln in matches[:30]: print(f"  {n}: {trunc(ln.strip(), 80)}")
        else: warn_line(T("text_search_none"))
    except Exception as e: err_line(f"{e}")
def text_tools_menu():
    header(T("text_title"))
    print(f"  1. {T('text_download')}\n  2. {T('text_local')}\n  3. {T('text_spell')}")
    print(f"  4. {T('text_search')}\n  0. {T('fm_back')}")
    ch = ask_input(c(f"{T('choice')}: ", GREEN))
    if ch is None or ch in ("0","q"): return
    path = None
    if ch == "1":
        u = ask_input(c(f"{T('text_enter_url')}: ", YELLOW))
        if u: path = text_download(u)
    else:
        p = ask_input(c(f"{T('text_enter_path')}: ", YELLOW))
        if p:
            pp = Path(p).expanduser()
            if pp.exists(): path = pp
    if not path or not Path(path).exists(): return
    if ch == "3":
        lg = ask_input(c(f"{T('text_lang')} ", YELLOW)) or SETTINGS.get("spell_lang","ru")
        if lg not in ("ru","en","both"): lg = "ru"
        spell_check(path, lg)
    elif ch == "4":
        q = ask_input(c(f"{T('text_enter_query')}: ", YELLOW))
        if q: text_search(path, q)

# ==========================================================
#  КОД: ruff (python) / shellcheck (shell)
# ==========================================================
def code_check(path, fix=False):
    p = Path(path)
    ext = p.suffix.lower()
    if ext == ".py":
        if not shutil.which("ruff") and not shutil.which("python3"): err_line("ruff/python3 нет"); return False
        cmd = ["ruff","check"] + (["--fix"] if fix else []) + [str(p)]
        try:
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            if r.stdout: print(r.stdout[:2000])
            if fix and r.returncode == 0: ok_line(f"{T('code_fixed')}: {p.name}"); return True
            if r.returncode != 0: warn_line(f"{T('code_errors')}: {p.name}")
            else: ok_line(f"{T('code_clean')}: {p.name}")
            return True
        except Exception as e: err_line(f"ruff: {e}"); return False
    if ext == ".sh" or ext == ".bash":
        if not shutil.which("shellcheck"): err_line("shellcheck не установлен"); return False
        try:
            r = subprocess.run(["shellcheck", str(p)], capture_output=True, text=True, timeout=120)
            if r.stdout: print(r.stdout[:3000])
            if r.returncode == 0: ok_line(f"{T('code_clean')}: {p.name}")
            else: warn_line(f"{T('code_errors')}: {p.name}"); return True
        except Exception as e: err_line(f"shellcheck: {e}")
        return False
    warn_line(T("code_lang_unknown")); return False
def code_tools_menu():
    header(T("code_title"))
    print(f"  1. {T('code_fix')}\n  2. {T('code_scan')}\n  0. {T('fm_back')}")
    ch = ask_input(c(f"{T('choice')}: ", GREEN))
    if ch is None or ch in ("0","q"): return
    p = ask_input(c(f"{T('code_enter_path')}: ", YELLOW))
    if not p: return
    path = Path(p).expanduser()
    if not path.exists(): err_line(f"Не найдено: {p}"); return
    if path.is_dir():
        files = [f for f in path.rglob("*") if f.is_file() and f.suffix.lower() in CODE_EXTS]
    else: files = [path]
    for f in files: code_check(f, fix=(ch == "1"))

# ==========================================================
#  РАСШИРЕННЫЕ МЕДИА-ИНСТРУМЕНТЫ
# ==========================================================
def _run_ff(args, desc="processing", timeout=14400):
    if not HAS_FFMPEG: err_line(T("ffmpeg_missing")); return False
    try:
        r = subprocess.run([FFMPEG_BIN,"-y"] + args, capture_output=True, text=True, timeout=timeout)
        if r.returncode == 0: ok_line(f"{T('adv_done')}: {desc}"); return True
        if r.stderr: err_line(r.stderr.strip()[-500:])
    except Exception as e: err_line(f"ffmpeg: {e}")
    return False
def advanced_menu():
    header(T("adv_title"))
    print(f"  1. {T('adv_extract_audio')}\n  2. {T('adv_make_gif')}\n  3. {T('adv_thumbnail')}")
    print(f"  4. {T('adv_concat')}\n  5. {T('adv_split')}\n  6. {T('adv_loudnorm')}")
    print(f"  7. {T('adv_compress')}\n  0. {T('fm_back')}")
    ch = ask_input(c(f"{T('choice')}: ", GREEN))
    if ch is None or ch in ("0","q"): return
    if ch == "1":
        src = ask_input(c(f"{T('adv_enter_src')}: ", YELLOW))
        if not src or not Path(src).exists(): return
        out = AUDIO_DIR / (Path(src).stem + ".m4a")
        _run_ff(["-i",src,"-vn","-c:a","aac","-b:a","192k",str(out)], "extract audio")
    elif ch == "2":
        src = ask_input(c(f"{T('adv_enter_src')}: ", YELLOW))
        if not src or not Path(src).exists(): return
        out = Path(src).with_suffix(".gif")
        _run_ff(["-i",src,"-vf","fps=10,scale=480:-1:flags=lanczos","-loop","0",str(out)], "gif")
    elif ch == "3":
        src = ask_input(c(f"{T('adv_enter_src')}: ", YELLOW))
        if not src or not Path(src).exists(): return
        out = Path(src).with_name(Path(src).stem + "_thumb.jpg")
        _run_ff(["-i",src,"-ss","00:00:01","-frames:v","1","-q:v","2",str(out)], "thumbnail")
    elif ch == "4":
        lst = ask_input(c(f"{T('adv_enter_paths')}: ", YELLOW))
        if not lst: return
        paths = [Path(x.strip()).expanduser() for x in lst.split(",") if x.strip()]
        if len(paths) < 2: return
        list_file = TMP_DIR / "concat.txt"
        with open(list_file, "w", encoding="utf-8") as fh:
            for p in paths:
                if p.exists(): fh.write(f"file '{p}'\n")
        out = VIDEOS_DIR / "concatenated.mp4"
        _run_ff(["-f","concat","-safe","0","-i",str(list_file),"-c","copy",str(out)], "concat")
    elif ch == "5":
        src = ask_input(c(f"{T('adv_enter_src')}: ", YELLOW))
        if not src or not Path(src).exists(): return
        dur = ask_input(c(f"{T('adv_enter_duration')}: ", YELLOW)) or "60"
        try: d = int(dur)
        except ValueError: d = 60
        total = get_duration(src) or 0
        segs = max(1, int(total // d) + 1) if total else 1
        for i in range(segs):
            out = VIDEOS_DIR / f"{Path(src).stem}_part{i+1:02d}{Path(src).suffix}"
            _run_ff(["-ss",str(i*d),"-i",src,"-t",str(d),"-c","copy",str(out)], f"split part {i+1}", timeout=3600)
    elif ch == "6":
        src = ask_input(c(f"{T('adv_enter_src')}: ", YELLOW))
        if not src or not Path(src).exists(): return
        out = Path(src).with_name(Path(src).stem + "_norm" + Path(src).suffix)
        _run_ff(["-i",src,"-af","loudnorm=I=-16:TP=-1.5:LRA=11","-c:v","copy",str(out)], "loudnorm")
    elif ch == "7":
        src = ask_input(c(f"{T('adv_enter_src')}: ", YELLOW))
        if not src or not Path(src).exists(): return
        out = Path(src).with_name(Path(src).stem + "_small" + Path(src).suffix)
        _run_ff(["-i",src,"-vcodec","libx264","-crf","28","-preset","fast","-acodec","aac","-b:a","128k",str(out)], "compress")

# ==========================================================
#  ПРИВАТНОСТЬ: uuid / encrypt / shred / sha256 / dedup
# ==========================================================
def priv_uuid(path):
    p = Path(path)
    if not p.exists(): return
    new = p.with_name(str(uuid.uuid4()) + p.suffix)
    try: p.rename(new); ok_line(f"{T('priv_renamed')}: {new.name}")
    except OSError as e: err_line(str(e))
def priv_encrypt(path):
    p = Path(path)
    if not p.exists(): return
    if shutil.which("gpg"):
        try:
            subprocess.run(["gpg","--symmetric","--cipher-algo","AES256","-o",str(p)+".gpg",str(p)], check=True, timeout=1800)
            ok_line(f"{T('priv_encrypted')}: {p.name}.gpg"); return
        except Exception as e: err_line(f"gpg: {e}")
    if shutil.which("openssl"):
        try:
            subprocess.run(["openssl","enc","-aes-256-cbc","-salt","-in",str(p),"-out",str(p)+".enc"], check=True, timeout=1800)
            ok_line(f"{T('priv_encrypted')}: {p.name}.enc"); return
        except Exception as e: err_line(f"openssl: {e}")
    err_line("gpg/openssl не найдены")
def priv_shred(path):
    p = Path(path)
    if not p.exists(): return
    if shutil.which("shred"):
        try: subprocess.run(["shred","-uzf",str(p)], check=True, timeout=300); ok_line(f"{T('priv_shredded')}: {p.name}"); return
        except Exception as e: err_line(f"shred: {e}")
    try:
        size = p.stat().st_size
        with open(p, "r+b") as fh:
            fh.write(os.urandom(size)); fh.flush(); os.fsync(fh.fileno())
        p.unlink(); ok_line(f"{T('priv_shredded')}: {p.name}")
    except Exception as e: err_line(f"{e}")
def priv_sha256(target):
    out = []
    for f in _iter_media_files(target):
        try:
            h = hashlib.sha256()
            with open(f, "rb") as fh:
                for chunk in iter(lambda: fh.read(65536), b""): h.update(chunk)
            out.append((f, h.hexdigest())); print(f"  {h.hexdigest()[:16]}…  {f.name}")
        except Exception: pass
    if out: ok_line(f"{T('priv_hashed')}: {len(out)}")
    return out
def priv_dups(target):
    groups = {}
    for f, h in priv_sha256(target): groups.setdefault(h, []).append(f)
    dups = {h:fs for h,fs in groups.items() if len(fs) > 1}
    if dups:
        ok_line(f"{T('priv_dups_found')}: {len(dups)}")
        for h, fs in dups.items():
            print(c(f"\n[{h[:12]}]", CYAN))
            for f in fs: print(f"  {f}")
    else: ok_line("Дубликаты не найдены")
def privacy_menu():
    header(T("priv_title"))
    print(f"  1. {T('priv_uuid')}\n  2. {T('priv_encrypt')}\n  3. {T('priv_shred')}")
    print(f"  4. {T('priv_sha256')}\n  5. {T('priv_dups')}\n  0. {T('fm_back')}")
    ch = ask_input(c(f"{T('choice')}: ", GREEN))
    if ch is None or ch in ("0","q"): return
    if ch in ("3",):
        warn_line(T("priv_warn"))
        if not confirm(T("priv_confirm")): return
    p = ask_input(c(f"{T('priv_enter_path')}: ", YELLOW))
    if not p: return
    path = Path(p).expanduser()
    if not path.exists(): err_line(f"Не найдено: {p}"); return
    if ch in ("1","2","3"):
        if path.is_dir():
            for f in _iter_media_files(path):
                {"1":priv_uuid,"2":priv_encrypt,"3":priv_shred}[ch](f)
        else: {"1":priv_uuid,"2":priv_encrypt,"3":priv_shred}[ch](path)
    elif ch == "4": priv_sha256(path)
    elif ch == "5": priv_dups(path)

# ==========================================================
#  ОТЧЁТЫ: CSV / JSON / pre-scan
# ==========================================================
def _collect_report(target):
    rows = []
    for f in _iter_media_files(target):
        md = get_metadata(f) if exiftool_available() else {}
        rows.append({
            "path": str(f), "name": f.name, "size": f.stat().st_size,
            "ext": f.suffix.lower(),
            "mtime": time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime(f.stat().st_mtime)),
            "has_gps": bool(md.get("Composite:GPSLatitude") or md.get("EXIF:GPSLatitude")),
            "make": md.get("EXIF:Make") or md.get("Make") or "",
            "model": md.get("EXIF:Model") or md.get("Model") or "",
        })
    return rows
def reports_menu():
    ensure_dir()
    header(T("rep_title"))
    print(f"  1. {T('rep_csv')}\n  2. {T('rep_json')}\n  3. {T('rep_prescan')}\n  0. {T('fm_back')}")
    ch = ask_input(c(f"{T('choice')}: ", GREEN))
    if ch is None or ch in ("0","q"): return
    d = ask_input(c(f"{T('rep_enter_dir')}: ", YELLOW))
    if not d: return
    path = Path(d).expanduser()
    if not path.exists(): err_line(f"Не найдено: {d}"); return
    rows = _collect_report(path)
    if not rows: warn_line("Нет медиа-файлов"); return
    ts = time.strftime("%Y%m%d_%H%M%S")
    if ch == "1":
        out = REPORTS_DIR / f"report_{ts}.csv"
        with open(out, "w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)
        ok_line(f"{T('rep_saved')}: {out}")
    elif ch == "2":
        out = REPORTS_DIR / f"report_{ts}.json"
        out.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
        ok_line(f"{T('rep_saved')}: {out}")
    elif ch == "3":
        total = len(rows); with_gps = sum(1 for r in rows if r["has_gps"])
        cameras = {}
        for r in rows:
            k = f"{r['make']} {r['model']}".strip() or "unknown"; cameras[k] = cameras.get(k, 0) + 1
        print(c(f"\n{T('rep_summary')}:", CYAN))
        print(f"  Всего: {total}\n  С GPS: {with_gps}\n  Камеры:")
        for k, n in sorted(cameras.items(), key=lambda x: -x[1])[:10]: print(f"    {k}: {n}")

# ==========================================================
#  ПРОФИЛИ / ПРЕСЕТЫ
# ==========================================================
PROFILES = {
    "default": {},
    "social": {"photo_max_width": 1920, "metadata_template": "social", "auto_convert": "never", "ask_rename": False, "ask_fix": False},
    "paranoid": {"metadata_template": "anon", "photo_max_width": 1280, "ask_rename": False, "ask_fix": False, "unattended": True},
    "archive": {"auto_convert": "never", "ask_rename": False, "ask_fix": False},
}
def apply_profile(name):
    p = PROFILES.get(name, {})
    for k, v in p.items():
        if k in DEFAULT_SETTINGS:
            SETTINGS[k] = v
    save_settings(SETTINGS); ok_line(f"{T('prof_applied')}: {name}")
def profiles_menu():
    header(T("prof_title"))
    print(f"  1. {T('prof_default')}\n  2. {T('prof_social')}\n  3. {T('prof_paranoid')}")
    print(f"  4. {T('prof_archive')}\n  5. {T('prof_save')}\n  0. {T('fm_back')}")
    ch = ask_input(c(f"{T('choice')}: ", GREEN))
    if ch is None or ch in ("0","q"): return
    keys = {"1":"default","2":"social","3":"paranoid","4":"archive"}
    if ch in keys: apply_profile(keys[ch])
    elif ch == "5":
        name = ask_input(c("Имя профиля: ", YELLOW))
        if name:
            PROFILES[name] = {k: SETTINGS[k] for k in DEFAULT_SETTINGS}
            ok_line(f"Сохранён: {name}")

# ==========================================================
#  ПАКЕТНЫЙ РЕЖИМ (без вопросов)
# ==========================================================
def batch_menu():
    header(T("batch_title")); info_line(T("batch_hint"))
    k = ask_input(c(f"{T('batch_kind')}: ", YELLOW)) or "1"
    kind = {"1":"video","2":"audio","3":"photo"}.get(k, "video")
    src = ask_input(c(f"{T('batch_enter_urls')}: ", YELLOW))
    if not src: return
    urls = []
    p = Path(src).expanduser()
    if p.exists() and p.is_file():
        urls = [ln.strip() for ln in p.read_text(encoding="utf-8").splitlines() if ln.strip() and not ln.startswith("#")]
    else:
        urls = [u.strip() for u in src.splitlines() if u.strip()]
    if not urls: warn_line("Нет URL"); return
    ok_count = 0; fail_count = 0
    for i, u in enumerate(urls, 1):
        info_line(f"[{i}/{len(urls)}] {trunc(u, 60)}")
        try:
            if kind == "video": ok, _ = attempt_download_video(fix_url(u), LAST_PRIO["video"])
            elif kind == "audio": ok, _ = attempt_download_audio(fix_url(u), LAST_PRIO["audio"])
            else: ok = download_photos(fix_url(u))
            if ok: ok_count += 1
            else: fail_count += 1
        except KeyboardInterrupt: raise
        except Exception as e: err_line(f"{type(e).__name__}: {e}"); fail_count += 1
    print(); header(T("batch_summary"))
    ok_line(f"{T('batch_ok')}: {ok_count}")
    if fail_count: err_line(f"{T('batch_fail')}: {fail_count}")

# ==========================================================
#  ОБНОВЛЁННЫЕ ДИАГНОСТИКА И ОТЛАДКА
# ==========================================================
DIAG_DEFAULT_HOSTS = ["rutube.ru","www.youtube.com","i.ytimg.com","redirector.googlevideo.com","www.google.com"]

def diagnostics():
    header(T("diag_title"))
    print(f"  1. {T('diag_quick')}\n  2. {T('diag_dns_full')}\n  3. {T('diag_tls_only')}")
    print(f"  4. {T('diag_proxy_only')}\n  5. {T('diag_custom')}\n  6. {T('diag_all')}\n  0. {T('fm_back')}")
    ch = ask_input(c(f"{T('diag_what')}: ", GREEN))
    if ch is None or ch in ("0","q"): return
    hosts = list(DIAG_DEFAULT_HOSTS)
    if ch == "5":
        raw = ask_input(c("Хосты через запятую: ", YELLOW))
        if not raw: return
        hosts = [h.strip() for h in raw.split(",") if h.strip()]
    do_dns = ch in ("1","2","6"); do_full_dns = ch in ("2","6")
    do_tls = ch in ("1","3","6"); do_proxy = ch in ("4","6")
    for host in hosts:
        print(c(f"\n{host}", CYAN))
        answers = {}
        if do_dns:
            ips = resolve_with("system", host); answers["system"] = ips
            print(f"  {T('diag_system')}: {', '.join(ips) if ips else T('diag_fail')}")
            if do_full_dns:
                for srv in dns_servers():
                    ips, err = udp_query(srv, host); answers["udp " + srv] = ips
                    print(f"  udp {srv}: {', '.join(ips) if ips else (err or T('diag_fail'))}")
                for u in doh_urls()[:3]:
                    try: ips = doh_query(u, host); err = ""
                    except Exception as e: ips, err = [], f"{type(e).__name__}"
                    answers["doh " + u] = ips
                    print(f"  doh {u}: {', '.join(ips) if ips else (err or T('diag_fail'))}")
            if len({tuple(sorted(v)) for v in answers.values() if v}) > 1: warn_line(T("diag_mismatch"))
        if do_tls:
            cands = [ip for v in answers.values() for ip in v] or resolve_with("system", host)
            if cands:
                ok, err = tls_probe(host, cands[0], timeout=10)
                if ok: ok_line(f"{T('diag_tls_ok')} ({cands[0]})")
                else: err_line(f"{T('diag_tls_fail')} ({cands[0]}): {err}")
    if do_proxy:
        px = SETTINGS["proxy"]
        if px:
            print(c(f"\n{T('diag_proxy')}: {px}", CYAN))
            if px.split("://")[0].lower() in ("http","https"):
                try:
                    req = urllib.request.Request("https://www.youtube.com/generate_204", headers={"User-Agent":UA})
                    with make_opener().open(req, timeout=20) as r: ok_line(f"HTTP {r.status}")
                except Exception as e: err_line(f"{type(e).__name__}: {e}")
            else: warn_line(T("diag_proxy_socks"))
        else: warn_line(T("empty"))
    ask_input(c(f"\n{T('diag_press')}", YELLOW))

def _pkg_version(py_mod):
    try:
        m = importlib.import_module(py_mod)
        return getattr(m, "__version__", "?")
    except Exception: return "?"

def debug_menu():
    header(T("debug_title"))
    print(c(f"── {T('debug_versions')} ──", MAGENTA))
    print(f"  Python: {sys.version.split()[0]}")
    print(f"  yt-dlp: {getattr(getattr(yt_dlp, 'version', None), '__version__', '?')}")
    print(f"  yt-dlp-ejs: {'ON' if has_ejs() else 'OFF'}")
    if HAS_FFMPEG:
        try:
            r = subprocess.run([FFMPEG_BIN,"-version"], capture_output=True, text=True, timeout=10)
            line = r.stdout.splitlines()[0] if r.stdout else "?"
            print(f"  ffmpeg: {line[:80]}")
        except Exception: print(f"  ffmpeg: {FFMPEG_BIN} (version read failed)")
    else: print("  ffmpeg: MISSING")
    print(f"  ffprobe: {FFPROBE_BIN or 'MISSING'}")
    for name in ("exiftool","convert","aspell","shellcheck","yt-dlp","gallery-dl","gpg","openssl","shred","mediainfo","mp4box","sox"):
        w = shutil.which(name)
        print(f"  {name}: {w or 'not found'}")
    print(c(f"\n── {T('debug_py_pkgs')} ──", MAGENTA))
    for mod in ("yt_dlp","gallery_dl","rich","tqdm","ruff","yt_dlp_ejs"):
        v = _pkg_version(mod)
        print(f"  {mod}: {v}")
    print(c(f"\n── {T('debug_settings')} ──", MAGENTA))
    for k in DEFAULT_SETTINGS:
        print(f"  {k} = {SETTINGS.get(k)}")
    print(c(f"\n── {T('debug_dirs')} ──", MAGENTA))
    for label, d in (("BASE", BASE_DIR), ("videos", VIDEOS_DIR), ("audio", AUDIO_DIR),
                     ("photos", PHOTOS_DIR), ("text", TEXT_DIR), ("code", CODE_DIR),
                     ("fix", FIX_DIR), ("reports", REPORTS_DIR)):
        print(f"  {label}: {d}")
    print(c(f"\n── {T('debug_env')} ──", MAGENTA))
    print(f"  LANG={LANG}  Python UTF8={os.environ.get('PYTHONUTF8','-')}")
    print(f"  Alpine: {os.environ.get('CURRENT_ALPINE','?')}")
    print(f"  Unattended: {SETTINGS.get('unattended')}")
    ask_input(c(f"\n{T('debug_press')}", YELLOW))

# ==========================================================
#  УТИЛИТЫ
# ==========================================================
def list_files(directory):
    try: files = sorted(directory.iterdir(), key=lambda p: p.name.lower())
    except OSError: return []
    return [f for f in files if f.is_file() and not f.name.startswith(".")]
def parse_numbers(text, max_index):
    if not text: raise ValueError
    text = text.strip().lower()
    if text in ("all","a"): return list(range(1, max_index + 1))
    result = []
    for part in [p.strip() for p in text.split(",") if p.strip()]:
        if "-" in part:
            left, right = part.split("-",1)
            if not left.isdigit() or not right.isdigit(): raise ValueError
            a,b = sorted((int(left), int(right)))
            for n in range(a, b+1):
                if 1 <= n <= max_index and n not in result: result.append(n)
        else:
            if not part.isdigit(): raise ValueError
            n = int(part)
            if 1 <= n <= max_index and n not in result: result.append(n)
    if not result: raise ValueError
    return result
def ask_numbers(prompt, count):
    v = ask_input(c(prompt, YELLOW))
    if not v: err_line(T("invalid_choice")); return None
    try: return parse_numbers(v, count)
    except ValueError: err_line(T("invalid_choice")); return None
def print_files(files):
    for i, f in enumerate(files, 1):
        try: size = f.stat().st_size
        except OSError: size = 0
        print(f"  {i}. {trunc(f.name, 60)} ({fmt_size(size)})")

def file_manager_choose_dir():
    while True:
        header(T("fm_choose_dir"))
        print(f"  1. {T('fm_videos')}\n  2. {T('fm_audio')}\n  3. {T('fm_photos')}")
        print(f"  4. {T('fm_text')}\n  5. {T('fm_code')}\n  6. {T('fm_fix')}\n  0. {T('fm_back')}")
        ch = ask_input(c(f"{T('choice')}: ", GREEN))
        if ch is None: return None
        if ch in ("0","q",""): return None
        m = {"1":VIDEOS_DIR,"2":AUDIO_DIR,"3":PHOTOS_DIR,"4":TEXT_DIR,"5":CODE_DIR,"6":FIX_DIR}
        if ch in m: return m[ch]
        err_line(T("invalid_choice"))

def file_manager():
    ensure_dir(); current = file_manager_choose_dir()
    if current is None: return
    while True:
        files = list_files(current); header(T("fm_title"))
        print(c(f"{current} ({len(files)})", CYAN)); print("-" * 40)
        if files: print_files(files)
        else: warn_line(T("fm_empty"))
        print("-" * 40)
        print(f"  1. {T('fm_delete')}\n  2. {T('fm_delete_multi')}\n  3. {T('fm_delete_all')}")
        print(f"  4. {T('fm_rename')}\n  5. {T('fm_move_to_fix')}\n  6. {T('fm_restore')}")
        print(f"  7. {T('fm_choose_dir')}\n  0. {T('fm_back')}")
        ch = ask_input(c(f"{T('choice')}: ", GREEN))
        if ch is None or ch in ("0","q"): return
        if ch == "7":
            nd = file_manager_choose_dir()
            if nd: current = nd
            continue
        if ch not in ("1","2","3","4","5","6"): err_line(T("invalid_choice")); continue
        if ch == "6":
            fix_files = list_files(FIX_DIR)
            if not fix_files: warn_line(T("fm_empty")); continue
            print_files(fix_files)
            nums = ask_numbers(f"Номер (1-{len(fix_files)}): ", len(fix_files))
            if not nums: continue
            tgt = fix_files[nums[0]-1]
            dest = PHOTOS_DIR if tgt.suffix.lower() in PHOTO_EXTS else (AUDIO_DIR if tgt.suffix.lower() in AUDIO_EXTS else VIDEOS_DIR)
            try: tgt.rename(dest / tgt.name); ok_line(f"{T('fm_moved')}: {tgt.name}")
            except OSError as e: err_line(f"{e}")
            continue
        if not files: continue
        if ch == "3":
            if confirm(f"{T('fm_delete_all')} ({len(files)})?"):
                cnt = 0
                for f in files:
                    try: f.unlink(); cnt += 1
                    except OSError: pass
                ok_line(f"{T('fm_deleted')}: {cnt}")
            continue
        nums = ask_numbers(f"Номер (1-{len(files)}): ", len(files))
        if not nums: continue
        if ch in ("1","2"):
            targets = [files[n-1] for n in (nums[:1] if ch == "1" else nums)]
            if confirm(f"{T('fm_delete')}?"):
                for t in targets:
                    try: t.unlink(); ok_line(f"{T('fm_deleted')}: {t.name}")
                    except OSError: pass
        elif ch == "4":
            tgt = files[nums[0]-1]
            new = ask_input(c(f"{T('fm_new_name')}: ", YELLOW))
            if new: rename_file(tgt, new)
        elif ch == "5":
            move_to_fix(files[nums[0]-1])

def language_menu():
    while True:
        header(T("set_language"))
        print(f"  1. {T('lang_ru')}\n  2. {T('lang_en')}\n  0. {T('fm_back')}")
        ch = ask_input(c(f"{T('choice')}: ", GREEN))
        if ch is None or ch in ("0","q"): return
        if ch in ("1","2"):
            save_lang("ru" if ch == "1" else "en"); ok_line(T("set_saved")); return

def setting_display(key):
    if key == "language": return T("lang_ru" if LANG == "ru" else "lang_en")
    v = SETTINGS[key]
    if key == "video_codec": return T(VIDEO_CODECS[v]["label_key"])
    if key == "audio_codec": return T(AUDIO_CODECS[v]["label_key"])
    if isinstance(v, bool): return T("on" if v else "off")
    if key in CHOICES: return T("opt_" + v)
    if key == "max_height" and v == 0: return T("unlimited")
    if isinstance(v, str) and not v: return T("empty")
    return str(v)

def pick_from(title, labels, current_index):
    print(c(f"\n{title}:", CYAN))
    for i, lb in enumerate(labels, 1):
        print(f"  {i}. {lb}{' [*]' if i-1 == current_index else ''}")
    ch = ask_input(c(f"{T('choice')}: ", YELLOW))
    if not ch or not ch.isdigit(): return None
    idx = int(ch) - 1
    return idx if 0 <= idx < len(labels) else None

def edit_with_templates(key, templates, current_value, on_set=None, multi=False):
    print(c(f"\n{T('set_' + key)}:", CYAN))
    for i, t in enumerate(templates, 1):
        disp = t if t else T("empty"); cur = " [*]" if t == current_value else ""
        print(f"  {i}. {disp}{cur}")
    print(f"  0. {T('templates_custom')}")
    if multi: print(f"  {T('templates_multi_hint')}")
    ch = ask_input(c(f"{T('choice')} [0]: ", YELLOW))
    if ch is None: return False
    new_val = None
    if not ch or ch == "0":
        raw = ask_input(c(f"{T('set_' + key)} [{current_value or T('empty')}]\n{T('set_enter_value')}: ", YELLOW))
        if not raw: return False
        new_val = raw if raw != "-" else ""
    elif ch.isdigit() and 1 <= int(ch) <= len(templates): new_val = templates[int(ch)-1]
    elif multi:
        nums = parse_multi(ch, len(templates))
        if not nums: err_line(T("invalid_choice")); return False
        selected = [templates[i-1] for i in nums]
        if key in ("dns_servers","yt_clients"):
            parts = []
            for s in selected:
                for ip in s.split(","):
                    ip = ip.strip()
                    if ip and ip not in parts: parts.append(ip)
            new_val = ",".join(parts)
        elif key == "doh_url": new_val = ",".join([s for s in selected if s])
        else: new_val = selected[0] if selected else ""
    else: new_val = ch
    if new_val is None: return False
    if on_set and not on_set(new_val): err_line(T("set_bad_value")); return False
    SETTINGS[key] = new_val; save_settings(SETTINGS)
    if key in ("proxy","dns_servers","doh_url","doh_fallback","ip_version","verify_tls"): reset_dns()
    ok_line(T("set_saved")); return True

def edit_setting(key):
    if key == "language": language_menu(); return
    title = T("set_" + key); v = SETTINGS[key]
    if key == "proxy":
        edit_with_templates("proxy", PROXY_TEMPLATES, v,
            on_set=lambda nv: (not nv) or bool(re.match(r"^(https?|socks4a?|socks5h?)://\S+$", nv, re.I))); return
    if key == "dns_servers": edit_with_templates("dns_servers", DNS_TEMPLATES, v, multi=True); return
    if key == "doh_url": edit_with_templates("doh_url", DOH_TEMPLATES, v, multi=True); return
    if key == "yt_clients": edit_with_templates("yt_clients", YT_CLIENTS_TEMPLATES, v, multi=True); return
    if key in ("video_codec","audio_codec"):
        table = VIDEO_CODECS if key == "video_codec" else AUDIO_CODECS
        keys = list(table.keys())
        idx = pick_from(title, [T(table[k]["label_key"]) for k in keys], keys.index(v))
        if idx is None: return
        enc = table[keys[idx]].get("encoder")
        if not encoder_ok(enc): err_line(T("encoder_missing")); return
        SETTINGS[key] = keys[idx]
    elif isinstance(v, bool): SETTINGS[key] = not v
    elif key in CHOICES:
        keys = list(CHOICES[key]); idx = pick_from(title, [T("opt_" + k) for k in keys], keys.index(v))
        if idx is None: return
        SETTINGS[key] = keys[idx]
    elif isinstance(v, int):
        raw = ask_input(c(f"{title} [{v}]: ", YELLOW))
        if not raw: return
        lo, hi = INT_LIMITS.get(key, (0, 10**9))
        if not raw.isdigit() or not lo <= int(raw) <= hi:
            err_line(f"{T('set_bad_value')} ({lo}-{hi})"); return
        SETTINGS[key] = int(raw)
    else:
        raw = ask_input(c(f"{title} [{v or T('empty')}]\n{T('set_enter_value')}: ", YELLOW))
        if not raw: return
        SETTINGS[key] = raw if raw != "-" else ""
    save_settings(SETTINGS)
    if key == "base_dir": ensure_dir()
    if key in ("dns_mode","doh_fallback","ip_version","verify_tls"): reset_dns()
    ok_line(T("set_saved"))

def settings_group_menu(group_key, keys):
    while True:
        header(T(group_key))
        for i, k in enumerate(keys, 1): print(f"  {i}. {T('set_' + k)}: {setting_display(k)}")
        print(f"  0. {T('fm_back')}")
        ch = ask_input(c(f"{T('choice')}: ", GREEN))
        if ch is None or ch in ("0","q"): return
        if ch.isdigit() and 1 <= int(ch) <= len(keys): edit_setting(keys[int(ch)-1])
        else: err_line(T("invalid_choice"))

def settings_menu():
    while True:
        header(T("settings_title"))
        for i, (gk, _) in enumerate(GROUPS, 1): print(f"  {i}. {T(gk)}")
        print(f"  {len(GROUPS)+1}. {T('set_reset')}\n  0. {T('fm_back')}")
        ch = ask_input(c(f"{T('choice')}: ", GREEN))
        if ch is None or ch in ("0","q"): return
        if ch.isdigit() and 1 <= int(ch) <= len(GROUPS):
            gk, keys = GROUPS[int(ch)-1]; settings_group_menu(gk, keys)
        elif ch == str(len(GROUPS) + 1):
            SETTINGS.clear(); SETTINGS.update(DEFAULT_SETTINGS)
            save_settings(SETTINGS); reset_dns(); ensure_dir(); ok_line(T("set_saved"))
        else: err_line(T("invalid_choice"))

def update_menu():
    header(T("upd_title"))
    print(f"  1. {T('upd_stable')}\n  2. {T('upd_nightly')}\n  3. {T('upd_ejs')}")
    print(f"  4. {T('upd_all_tools')}\n  5. {T('upd_reinstall_python')}\n  0. {T('fm_back')}")
    ch = ask_input(c(f"{T('choice')}: ", GREEN))
    if ch == "1": return signal_action(ACTION_PIP_FILE, "yt-dlp tqdm gallery-dl rich ruff")
    if ch == "2": return signal_action(ACTION_PIP_FILE, "--pre yt-dlp tqdm")
    if ch == "3": return signal_action(ACTION_PIP_FILE, "yt-dlp-ejs")
    if ch == "4": return signal_action(ACTION_UPDATE_ALL_FILE)
    if ch == "5": return signal_action(ACTION_REINSTALL_PY_FILE)
    return False

def check_remote_version():
    if not UPDATE_URL: return None
    try:
        req = urllib.request.Request(UPDATE_URL, headers={"User-Agent":UA})
        with urllib.request.urlopen(req, timeout=30) as r: return r.read().decode("utf-8","replace")
    except Exception as e: err_line(f"{type(e).__name__}: {e}"); return None

def self_update_menu():
    header(T("selfupd_title")); info_line(T("selfupd_checking"))
    content = check_remote_version()
    if content is None: err_line(T("selfupd_check_failed")); return False
    if not content.startswith("#!/bin/sh"): err_line(T("selfupd_invalid")); return False
    shell_path = SCRIPT_PATH
    if not shell_path or not Path(shell_path).exists(): err_line(T("selfupd_no_path")); return False
    try:
        old = Path(shell_path).read_text(encoding="utf-8")
        if old == content: info_line(T("selfupd_uptodate")); return False
    except Exception: pass
    if not confirm(T("selfupd_prompt"), timeout=PT()): return False
    info_line(T("selfupd_downloading"))
    try:
        new_path = shell_path + ".new"
        Path(new_path).write_text(content, encoding="utf-8"); os.chmod(new_path, 0o755)
        os.replace(new_path, shell_path); ok_line(T("selfupd_done")); return True
    except Exception as e: err_line(f"{type(e).__name__}: {e}"); return False

# ==========================================================
#  ЗАЩИЩЁННЫЙ ЗАПУСК И SELF-TEST
# ==========================================================
def run_guarded(fn, *args):
    OP["active"] = True
    try: return fn(*args)
    except KeyboardInterrupt:
        print(); warn_line(T("interrupted")); return None
    finally: OP["active"] = False; QUICK["on"] = False

def selftest():
    try:
        import select; select.select([], [], [], 0.01)
        subprocess.run(["true"], timeout=10)
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM); s.close()
        ssl.create_default_context()
        if yt_dlp is None:
            print("selftest: yt_dlp not importable"); return 2
        with yt_dlp.YoutubeDL({"quiet":True, "logger":Log()}): pass
        return 0
    except Exception as e:
        print(f"selftest: {type(e).__name__}: {e}"); return 1

# ==========================================================
#  ГЛАВНОЕ МЕНЮ
# ==========================================================
def main_menu():
    ensure_dir(); cleanup_junk(aggressive=True); refresh_ffmpeg()
    if not HAS_FFMPEG: warn_line(T("no_ffmpeg_warn"))
    if not exiftool_available(): warn_line("exiftool не найден — метаданные недоступны")
    while True:
        SEEN_ERRORS.clear()
        print(c("╔" + "═"*44 + "╗", CYAN))
        print(c("║  " + T("app_title").ljust(42)[:42] + "║", CYAN))
        print(c("╚" + "═"*44 + "╝", CYAN))
        print(c(f"  videos: {VIDEOS_DIR}", CYAN))
        print(c(f"  audio:  {AUDIO_DIR}", CYAN))
        print(c(f"  photos: {PHOTOS_DIR}", CYAN))
        print("-" * 46)
        items = [
            ("1", "menu_download_video", lambda: download_session(False)),
            ("2", "menu_download_audio", lambda: download_session(True)),
            ("3", "menu_download_photo", None),  # special: prompt URL
            ("4", "menu_search", search_videos),
            ("5", "menu_reencode", reencode_menu),
            ("6", "menu_photo_edit", photo_edit_menu),
            ("7", "menu_metadata", metadata_menu),
            ("8", "menu_text", text_tools_menu),
            ("9", "menu_code", code_tools_menu),
            ("10", "menu_advanced", advanced_menu),
            ("11", "menu_privacy", privacy_menu),
            ("12", "menu_reports", reports_menu),
            ("13", "menu_profiles", profiles_menu),
            ("14", "menu_batch", batch_menu),
            ("15", "menu_files", file_manager),
            ("16", "menu_settings", settings_menu),
            ("17", "menu_diag", diagnostics),
            ("18", "menu_update", update_menu),
            ("19", "menu_selfupdate", self_update_menu),
            ("20", "menu_debug", debug_menu),
        ]
        for num, key, _ in items: print(f"  {num.rjust(2)}. {T(key)}")
        print(f"   0. {T('menu_exit')}   [unattended: {'ON' if is_unattended() else 'OFF'}]")
        ch = ask_input(c(f"{T('choice')}: ", GREEN))
        if ch is None: print(c(f"\n[+] {T('stopped')}", GREEN)); break
        ch = ch.lower()
        if ch in ("0","q","quit","exit"): ok_line(T("menu_exit")); break
        handler = None
        for num, key, fn in items:
            if num == ch: handler = (key, fn); break
        if not handler: err_line(T("invalid_choice")); continue
        key, fn = handler
        if key == "menu_download_photo":
            u = ask_input(c("URL: ", YELLOW))
            if u: run_guarded(download_photos, fix_url(u))
        elif key == "menu_update":
            if run_guarded(update_menu): return
        elif key == "menu_selfupdate":
            if run_guarded(self_update_menu):
                signal_action(ACTION_SELF_UPDATE_FILE); return
        elif fn: run_guarded(fn)

def main():
    if "--selftest" in sys.argv[1:]: sys.exit(selftest())
    if "--batch" in sys.argv[1:]:
        SETTINGS["unattended"] = True
        ensure_dir(); batch_menu(); sys.exit(0)
    order = os.environ.get("VD_DNS_ORDER")
    if order:
        parsed = [x for x in order.split(",") if x in ("system","udp","doh")]
        DNS_STATE["order"] = parsed or None
    ensure_dir()
    try: main_menu()
    except KeyboardInterrupt: print(c(f"\n[+] {T('stopped')}", GREEN))

if __name__ == "__main__":
    try: main()
    except KeyboardInterrupt: print(c(f"\n[+] {T('stopped')}", GREEN))
PYEOF

chmod 700 "$PY_FILE"

# --- Проверка синтаксиса Python ---
if ! python3 -c 'compile(open("'"$PY_FILE"'", encoding="utf-8").read(), "mf", "exec")' >/dev/null 2>&1; then
    REP err "$(tr_msg 'Синтаксическая ошибка в Python-части' 'Syntax error in Python part')"
    python3 -c 'compile(open("'"$PY_FILE"'", encoding="utf-8").read(), "mf", "exec")' 2>&1 | tail -6
    exit 1
fi

# ==========================================================
#  ГЛАВНЫЙ ЦИКЛ (с обработкой сбоев Python)
# ==========================================================
tries=0
repaired=0
while [ "$tries" -lt 10 ]; do
    tries=$((tries + 1))

    # Самотест
    python3 "$PY_FILE" --selftest
    st=$?
    if [ "$st" -ge 128 ]; then
        REP err "$(tr_msg "Python упал при самотесте (код $st) — меняю Alpine..." "Python crashed in self-test (code $st) — switching Alpine...")"
        if ! switch_env; then
            REP err "$(tr_msg 'Не удалось подобрать Alpine' 'Could not pick Alpine')"; exit 1
        fi
        continue
    elif [ "$st" -ne 0 ]; then
        if [ "$repaired" -ge 2 ]; then
            REP err "$(tr_msg 'Самотест не проходит — проверьте сеть' 'Self-test keeps failing — check network')"; exit 1
        fi
        repaired=$((repaired + 1))
        REP wrn "$(tr_msg 'Самотест не пройден, переустанавливаю yt-dlp...' 'Self-test failed, reinstalling yt-dlp...')"
        run_with_spinner "pip: yt-dlp" pip_install yt-dlp tqdm
        continue
    fi

    # Основной запуск
    python3 "$PY_FILE"
    code=$?

    # Сигналы от Python
    if [ -f /tmp/mf_pip_cmd ]; then
        PIPE_ARGS=$(cat /tmp/mf_pip_cmd); rm -f /tmp/mf_pip_cmd
        REP inf "pip install $PIPE_ARGS"
        if run_with_spinner "pip install" pip_install $PIPE_ARGS; then REP ok "pip install OK"
        else REP err "pip install failed"; tail -3 /tmp/mf_pip.log 2>/dev/null; fi
        continue
    fi

    if [ -f /tmp/mf_update_all ]; then
        rm -f /tmp/mf_update_all
        REP inf "$(tr_msg 'Обновляю всё...' 'Updating everything...')"
        run_with_spinner "apk update" apk update >/dev/null 2>&1 || true
        run_with_spinner "apk upgrade" apk upgrade >/dev/null 2>&1 || true
        run_with_spinner "pip: yt-dlp" pip_install yt-dlp tqdm gallery-dl rich ruff || true
        ensure_python_tools
        fix_ffmpeg || true
        show_versions
        continue
    fi

    if [ -f /tmp/mf_reinstall_py ]; then
        rm -f /tmp/mf_reinstall_py
        REP inf "$(tr_msg 'Переустановка Python...' 'Reinstalling Python...')"
        rm -f "$ALPINE_VERSION_FILE" "$FAILED_ALPINES"
        if ! pick_alpine; then
            REP err "$(tr_msg 'Не удалось найти Alpine' 'Could not find Alpine')"; exit 1
        fi
        setup_environment
        continue
    fi

    if [ -f /tmp/mf_self_update ]; then
        rm -f /tmp/mf_self_update
        REP ok "$(tr_msg 'Перезапуск...' 'Restarting...')"
        exec sh "$0"
    fi

    if [ "$code" -ge 128 ]; then
        REP err "$(tr_msg "Python упал (код $code). Пробую пересобрать окружение..." "Python crashed (code $code). Rebuilding environment...")"
        if ! switch_env; then
            REP err "$(tr_msg 'Окружение не собралось' 'Environment rebuild failed')"; exit 1
        fi
        continue
    fi
    exit "$code"
done

REP err "$(tr_msg 'Превышено число попыток' 'Max retries reached')"
exit 1
