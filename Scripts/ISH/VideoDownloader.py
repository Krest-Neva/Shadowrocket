#!/bin/sh

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; BLUE='\033[0;34m'; NC='\033[0m'
say() { printf '%b\n' "$1"; }

LANG_FILE="$HOME/.video_downloader_lang"
KA_PID=""

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

T() {
    if [ "$VD_LANG" = "en" ]; then
        case "$1" in
            apk_update) echo "[*] apk update..." ;;
            apk_fail) echo "[!] apk update failed, continuing" ;;
            apk_skip) echo "[!] apk package not installed" ;;
            pip_install) echo "[*] pip: installing yt-dlp..." ;;
            pip_fail) echo "[!] pip install failed" ;;
            setup_header) echo "=== Video Downloader ===" ;;
            installing) echo "[*] yt-dlp not found — installing" ;;
            not_imported) echo "[!] yt-dlp/tqdm not importable, fallbacks will be tried" ;;
            no_python) echo "[!] python3 not found" ;;
            *) echo "$1" ;;
        esac
    else
        case "$1" in
            apk_update) echo "[*] Обновление apk..." ;;
            apk_fail) echo "[!] apk update не удался, продолжаем" ;;
            apk_skip) echo "[!] apk-пакет не установлен" ;;
            pip_install) echo "[*] pip: установка yt-dlp..." ;;
            pip_fail) echo "[!] pip install не удался" ;;
            setup_header) echo "=== Универсальный загрузчик видео ===" ;;
            installing) echo "[*] yt-dlp не найден — устанавливаю" ;;
            not_imported) echo "[!] yt-dlp/tqdm не импортируются, будут использованы запасные методы" ;;
            no_python) echo "[!] python3 не найден" ;;
            *) echo "$1" ;;
        esac
    fi
}

setup_dns() {
    cat > /etc/resolv.conf << 'EOF'
nameserver 1.1.1.1
nameserver 8.8.8.8
nameserver 94.140.14.14
EOF
}

keep_alive() {
    if [ -e /dev/location ]; then
        ( cat /dev/location > /dev/null 2>&1 ) &
        KA_PID=$!
    fi
}

have_ytdlp() {
    python3 - << 'EOF' >/dev/null 2>&1
import yt_dlp, tqdm
EOF
}

install_packages() {
    say "${BLUE}$(T apk_update)${NC}"
    apk update || say "${YELLOW}$(T apk_fail)${NC}"
    for p in python3 py3-pip ffmpeg ca-certificates curl \
             py3-brotli py3-pycryptodomex py3-mutagen py3-websockets; do
        apk add --no-cache "$p" >/dev/null 2>&1 || say "${YELLOW}$(T apk_skip): $p${NC}"
    done
    apk add --no-cache quickjs >/dev/null 2>&1 || true

    say "${BLUE}$(T pip_install)${NC}"
    pip3 install -U --no-deps --disable-pip-version-check yt-dlp tqdm \
      || pip3 install -U --no-deps --break-system-packages yt-dlp tqdm \
      || say "${RED}$(T pip_fail)${NC}"
}

say "${YELLOW}========================================${NC}"
say "${YELLOW}  $(T setup_header)${NC}"
say "${YELLOW}========================================${NC}"
setup_dns
keep_alive

if ! have_ytdlp; then
    say "${YELLOW}$(T installing)${NC}"
    install_packages
elif [ "${1:-}" = "--update" ]; then
    install_packages
fi

have_ytdlp || say "${RED}$(T not_imported)${NC}"

command -v python3 >/dev/null 2>&1 || { say "${RED}$(T no_python)${NC}"; exit 1; }

export PYTHONUTF8=1
export PYTHONIOENCODING=utf-8

cat > /tmp/video_downloader.py << 'PYEOF'
import sys
import os
import re
import json
import time
import ssl
import socket
import struct
import random
import shutil
import subprocess
import importlib
import importlib.util
import importlib.metadata
import urllib.request
import urllib.error
from pathlib import Path
from urllib.parse import urlparse

try:
    import yt_dlp
except ImportError:
    yt_dlp = None
try:
    from tqdm import tqdm
except ImportError:
    tqdm = None

HOME = Path.home()
LANG_FILE = HOME / ".video_downloader_lang"
SETTINGS_FILE = HOME / ".video_downloader_settings.json"
EJS_MARK = HOME / ".video_downloader_ejs_tried"
SCRIPT_PATH = os.path.abspath(sys.argv[0])
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"

RED, GREEN, YELLOW, BLUE, CYAN, NC = ("\033[0;31m", "\033[0;32m", "\033[1;33m",
                                      "\033[0;34m", "\033[0;36m", "\033[0m")

def c(t, col):
    return f"{col}{t}{NC}"

def info_line(m):
    print(c("[*] " + str(m), BLUE))

def ok_line(m):
    print(c("[+] " + str(m), GREEN))

def warn_line(m):
    print(c("[!] " + str(m), YELLOW))

def err_line(m):
    print(c("[!] " + str(m), RED))

def header(title):
    line = "=" * 40
    print(c(line, YELLOW))
    print(c("  " + str(title), YELLOW))
    print(c(line, YELLOW))

if LANG_FILE.exists():
    try:
        _l = LANG_FILE.read_text(encoding="utf-8").strip()
        LANG = _l if _l in ("ru", "en") else "ru"
    except Exception:
        LANG = "ru"
else:
    LANG = "ru"

TEXTS = {
    "ru": {
        "app_title": "Универсальный загрузчик видео",
        "menu_download_video": "Скачать видео",
        "menu_download_audio": "Скачать аудио",
        "menu_files": "Управление файлами",
        "menu_settings": "Настройки",
        "menu_diag": "Диагностика сети",
        "menu_update": "Обновить yt-dlp",
        "menu_exit": "Выход (q)",
        "choice": "Ваш выбор",
        "invalid_choice": "Неверный выбор",
        "videos_dir": "Видео сохраняются в",
        "audio_dir": "Аудио сохраняются в",
        "enter_urls": "Введите ссылки (по одной на строку).",
        "enter_urls_hint": "Пустая строка — начать. 'q' — меню.",
        "available_formats": "Доступные форматы видео",
        "select_video": "Номер видеоформата (Enter — лучший совместимый)",
        "select_audio_track": "Номер аудиодорожки (Enter — лучшая)",
        "invalid_default": "Неверный выбор, используется формат по умолчанию",
        "selector": "Селектор",
        "strategy": "Способ",
        "trying": "Пробую",
        "trying_generic": "Пробую generic-экстрактор...",
        "trying_binary": "Пробую yt-dlp отдельным процессом...",
        "trying_manual": "Пробую скачать видео и аудио отдельно и склеить через ffmpeg...",
        "trying_external": "Пробую прямую загрузку через curl/wget/aria2c/ffmpeg...",
        "trying_rutube": "Пробую RuTube API напрямую...",
        "retry_tls": "Повторить без проверки TLS?",
        "all_exhausted": "Все попытки исчерпаны",
        "scanning": "Сканирование страницы",
        "found_videos": "Найдено видео",
        "no_videos": "Видео не найдены",
        "multiple_videos": "Найдено несколько видео",
        "number_or_all": "Номер или 'all'",
        "invalid_url": "Некорректная ссылка",
        "stopped": "Работа остановлена",
        "finished": "Загрузка завершена",
        "fm_title": "Управление файлами",
        "fm_choose_dir": "Выберите папку",
        "fm_videos": "videos",
        "fm_audio": "audio",
        "fm_fix": "fix",
        "fm_back": "Назад",
        "fm_empty": "Папка пуста",
        "fm_delete": "Удалить файл",
        "fm_delete_multi": "Удалить несколько (1,3-5)",
        "fm_delete_all": "Удалить все",
        "fm_rename": "Переименовать",
        "fm_move_to_fix": "Переместить в fix",
        "fm_restore": "Вернуть из fix",
        "fm_deleted": "Удалено",
        "fm_failed": "Ошибка",
        "fm_numbers": "Номера",
        "fm_new_name": "Новое имя",
        "fm_renamed": "Переименовано",
        "fm_moved": "Перемещено",
        "fm_file_index": "Номер файла",
        "fm_exists": "Файл уже существует",
        "settings_title": "Настройки",
        "grp_media": "Видео и аудио",
        "grp_network": "Сеть и YouTube",
        "grp_interface": "Интерфейс и папки",
        "set_reset": "Сбросить все настройки",
        "set_saved": "Настройки сохранены",
        "set_enter_value": "Новое значение (Enter — оставить, '-' — очистить)",
        "set_bad_value": "Недопустимое значение",
        "set_video_codec": "Видеокодек",
        "set_audio_codec": "Аудиокодек",
        "set_max_height": "Макс. высота видео (0 — без ограничения)",
        "set_auto_convert": "Конвертация несовместимых",
        "set_concurrent_fragments": "Параллельных фрагментов",
        "set_cookies_file": "Файл cookies (cookies.txt)",
        "set_proxy": "Прокси (http/https/socks5)",
        "set_dns_mode": "Режим DNS",
        "set_dns_servers": "DNS-серверы (через запятую)",
        "set_doh_url": "Свой DoH-адрес",
        "set_ipv4_only": "Только IPv4",
        "set_verify_tls": "Проверка TLS-сертификатов",
        "set_preflight": "Предпроверка сети",
        "set_socket_timeout": "Таймаут сокета, сек",
        "set_retries": "Число повторов",
        "set_yt_clients": "Клиенты YouTube (tv,ios+web,...)",
        "set_js_runtime": "JS-движок для YouTube",
        "set_remote_ejs": "Загружать EJS-компоненты с GitHub",
        "set_progress_width": "Ширина прогресс-бара",
        "set_ask_rename": "Спрашивать о переименовании",
        "set_ask_fix": "Спрашивать о переносе в fix",
        "set_base_dir": "Основная папка",
        "set_language": "Язык",
        "opt_auto": "авто",
        "opt_system": "только системный",
        "opt_udp": "UDP-DNS в приоритете",
        "opt_doh": "DoH в приоритете",
        "opt_none": "нет",
        "opt_ask": "спрашивать",
        "opt_always": "всегда",
        "opt_never": "никогда",
        "opt_deno": "deno",
        "opt_node": "node",
        "opt_bun": "bun",
        "opt_quickjs": "quickjs",
        "on": "вкл",
        "off": "выкл",
        "unlimited": "без ограничения",
        "empty": "не задано",
        "preset_iphone": "iPhone (H.264 + AAC)",
        "preset_android": "Android (H.264 + AAC)",
        "preset_universal": "Универсальный (H.264 Baseline + AAC)",
        "preset_h265": "H.265 / HEVC (меньше размер, медленно на iSH)",
        "preset_vp9": "VP9 (Web, медленно на iSH)",
        "preset_av1": "AV1 (макс. сжатие, очень медленно на iSH)",
        "preset_original": "Оригинал (без перекодирования)",
        "audio_aac": "AAC 128 kbps (iPhone)",
        "audio_ac3": "AC3 192 kbps (не для Quick Look)",
        "audio_mp3": "MP3 192 kbps",
        "audio_opus": "Opus 160 kbps",
        "audio_flac": "FLAC (lossless, большой)",
        "audio_original": "Оригинал (без конвертации)",
        "lang_ru": "Русский",
        "lang_en": "English",
        "video_ready": "Видео готово",
        "audio_ready": "Аудио готово",
        "file": "Файл",
        "size": "Размер",
        "rename_prompt": "Переименовать?",
        "move_fix_prompt": "Переместить в fix (если не открывается)?",
        "converting": "Конвертация",
        "convert_prompt": "Формат несовместим. Конвертировать?",
        "convert_done": "Конвертация завершена",
        "convert_failed": "Ошибка конвертации",
        "convert_cancelled": "Конвертация отменена",
        "ffmpeg_missing": "ffmpeg не найден",
        "compat_warning": "Формат может быть несовместим с выбранным устройством.",
        "junk_cleaned": "Очищено временных файлов",
        "encoder_missing": "Кодек не поддерживается этой сборкой ffmpeg. Выберите другой.",
        "preflight_title": "Проверка сети для",
        "preflight_ok": "Сеть доступна, DNS-режим",
        "preflight_fail": "Не удалось установить TLS-соединение ни одним способом",
        "preflight_blocked": "Похоже на блокировку или подмену DNS у провайдера (DPI). Обычно помогает только прокси/VPN.",
        "preflight_continue": "Всё равно попробовать (быстрые попытки)?",
        "net_help": "Сетевые ошибки. Задайте прокси (http://host:port, socks5://host:port) или Enter — пропустить.",
        "proxy_prompt": "Прокси",
        "proxy_invalid": "Неверный формат прокси",
        "proxy_set": "Прокси сохранён, повторяю",
        "diag_title": "Диагностика сети",
        "diag_system": "система",
        "diag_fail": "нет ответа",
        "diag_mismatch": "Ответы DNS различаются — возможна подмена DNS",
        "diag_tls_ok": "TLS-соединение установлено",
        "diag_tls_fail": "TLS-соединение не удалось",
        "diag_proxy": "Проверка прокси",
        "diag_proxy_socks": "SOCKS-прокси проверяется только при загрузке",
        "diag_env": "Окружение",
        "diag_press": "Enter — продолжить",
        "upd_title": "Обновление yt-dlp",
        "upd_stable": "Стабильная версия",
        "upd_nightly": "Nightly (свежие исправления YouTube)",
        "upd_ejs": "Только компонент yt-dlp-ejs",
        "upd_done": "Обновление завершено, перезапуск",
        "upd_failed": "Обновление не удалось",
        "ejs_installing": "Устанавливаю yt-dlp-ejs (нужен для YouTube)",
        "ejs_failed": "Не удалось установить yt-dlp-ejs",
        "js_none": "JS-движок не найден: YouTube может отдавать не все форматы",
        "rutube_no_m3u8": "RuTube: ссылка на поток не получена",
        "ytdlp_missing": "yt-dlp не установлен",
        "dl_dest": "Сохранено в",
    },
    "en": {
        "app_title": "Universal Video Downloader",
        "menu_download_video": "Download video",
        "menu_download_audio": "Download audio",
        "menu_files": "File manager",
        "menu_settings": "Settings",
        "menu_diag": "Network diagnostics",
        "menu_update": "Update yt-dlp",
        "menu_exit": "Exit (q)",
        "choice": "Choice",
        "invalid_choice": "Invalid choice",
        "videos_dir": "Videos saved to",
        "audio_dir": "Audio saved to",
        "enter_urls": "Enter URLs (one per line).",
        "enter_urls_hint": "Empty line — start. 'q' — menu.",
        "available_formats": "Available video formats",
        "select_video": "Video format number (Enter = best compatible)",
        "select_audio_track": "Audio track number (Enter = best)",
        "invalid_default": "Invalid choice, using default",
        "selector": "Selector",
        "strategy": "Method",
        "trying": "Trying",
        "trying_generic": "Trying generic extractor...",
        "trying_binary": "Trying yt-dlp as a separate process...",
        "trying_manual": "Trying separate video and audio download with ffmpeg merge...",
        "trying_external": "Trying direct download via curl/wget/aria2c/ffmpeg...",
        "trying_rutube": "Trying RuTube API directly...",
        "retry_tls": "Retry without TLS verification?",
        "all_exhausted": "All attempts exhausted",
        "scanning": "Scanning page",
        "found_videos": "Videos found",
        "no_videos": "No videos found",
        "multiple_videos": "Multiple videos found",
        "number_or_all": "Number or 'all'",
        "invalid_url": "Invalid URL",
        "stopped": "Stopped",
        "finished": "Download finished",
        "fm_title": "File manager",
        "fm_choose_dir": "Choose directory",
        "fm_videos": "videos",
        "fm_audio": "audio",
        "fm_fix": "fix",
        "fm_back": "Back",
        "fm_empty": "Directory is empty",
        "fm_delete": "Delete file",
        "fm_delete_multi": "Delete multiple (1,3-5)",
        "fm_delete_all": "Delete all",
        "fm_rename": "Rename",
        "fm_move_to_fix": "Move to fix",
        "fm_restore": "Restore from fix",
        "fm_deleted": "Deleted",
        "fm_failed": "Failed",
        "fm_numbers": "Numbers",
        "fm_new_name": "New name",
        "fm_renamed": "Renamed",
        "fm_moved": "Moved",
        "fm_file_index": "File number",
        "fm_exists": "File already exists",
        "settings_title": "Settings",
        "grp_media": "Video and audio",
        "grp_network": "Network and YouTube",
        "grp_interface": "Interface and folders",
        "set_reset": "Reset all settings",
        "set_saved": "Settings saved",
        "set_enter_value": "New value (Enter = keep, '-' = clear)",
        "set_bad_value": "Invalid value",
        "set_video_codec": "Video codec",
        "set_audio_codec": "Audio codec",
        "set_max_height": "Max video height (0 = unlimited)",
        "set_auto_convert": "Convert incompatible files",
        "set_concurrent_fragments": "Parallel fragments",
        "set_cookies_file": "Cookies file (cookies.txt)",
        "set_proxy": "Proxy (http/https/socks5)",
        "set_dns_mode": "DNS mode",
        "set_dns_servers": "DNS servers (comma separated)",
        "set_doh_url": "Custom DoH URL",
        "set_ipv4_only": "IPv4 only",
        "set_verify_tls": "Verify TLS certificates",
        "set_preflight": "Network preflight check",
        "set_socket_timeout": "Socket timeout, sec",
        "set_retries": "Retries",
        "set_yt_clients": "YouTube clients (tv,ios+web,...)",
        "set_js_runtime": "JS runtime for YouTube",
        "set_remote_ejs": "Fetch EJS components from GitHub",
        "set_progress_width": "Progress bar width",
        "set_ask_rename": "Ask to rename",
        "set_ask_fix": "Ask to move to fix",
        "set_base_dir": "Base folder",
        "set_language": "Language",
        "opt_auto": "auto",
        "opt_system": "system only",
        "opt_udp": "UDP DNS first",
        "opt_doh": "DoH first",
        "opt_none": "none",
        "opt_ask": "ask",
        "opt_always": "always",
        "opt_never": "never",
        "opt_deno": "deno",
        "opt_node": "node",
        "opt_bun": "bun",
        "opt_quickjs": "quickjs",
        "on": "on",
        "off": "off",
        "unlimited": "unlimited",
        "empty": "not set",
        "preset_iphone": "iPhone (H.264 + AAC)",
        "preset_android": "Android (H.264 + AAC)",
        "preset_universal": "Universal (H.264 Baseline + AAC)",
        "preset_h265": "H.265 / HEVC (smaller, slow on iSH)",
        "preset_vp9": "VP9 (Web, slow on iSH)",
        "preset_av1": "AV1 (max compression, very slow on iSH)",
        "preset_original": "Original (no re-encode)",
        "audio_aac": "AAC 128 kbps (iPhone)",
        "audio_ac3": "AC3 192 kbps (not for Quick Look)",
        "audio_mp3": "MP3 192 kbps",
        "audio_opus": "Opus 160 kbps",
        "audio_flac": "FLAC (lossless, large)",
        "audio_original": "Original (no conversion)",
        "lang_ru": "Русский",
        "lang_en": "English",
        "video_ready": "Video ready",
        "audio_ready": "Audio ready",
        "file": "File",
        "size": "Size",
        "rename_prompt": "Rename?",
        "move_fix_prompt": "Move to fix (if it won't open)?",
        "converting": "Converting",
        "convert_prompt": "Format is incompatible. Convert?",
        "convert_done": "Conversion done",
        "convert_failed": "Conversion failed",
        "convert_cancelled": "Conversion cancelled",
        "ffmpeg_missing": "ffmpeg not found",
        "compat_warning": "Format may be incompatible with selected device.",
        "junk_cleaned": "Cleaned temp files",
        "encoder_missing": "Codec not supported by this ffmpeg build. Choose another.",
        "preflight_title": "Network check for",
        "preflight_ok": "Network reachable, DNS mode",
        "preflight_fail": "TLS connection failed with every method",
        "preflight_blocked": "Looks like ISP blocking or DNS spoofing (DPI). Usually only a proxy/VPN helps.",
        "preflight_continue": "Try anyway (quick attempts)?",
        "net_help": "Network errors. Set a proxy (http://host:port, socks5://host:port) or press Enter to skip.",
        "proxy_prompt": "Proxy",
        "proxy_invalid": "Invalid proxy format",
        "proxy_set": "Proxy saved, retrying",
        "diag_title": "Network diagnostics",
        "diag_system": "system",
        "diag_fail": "no answer",
        "diag_mismatch": "DNS answers differ — DNS spoofing is possible",
        "diag_tls_ok": "TLS connection established",
        "diag_tls_fail": "TLS connection failed",
        "diag_proxy": "Proxy check",
        "diag_proxy_socks": "SOCKS proxy is only checked during download",
        "diag_env": "Environment",
        "diag_press": "Enter — continue",
        "upd_title": "Update yt-dlp",
        "upd_stable": "Stable release",
        "upd_nightly": "Nightly (latest YouTube fixes)",
        "upd_ejs": "yt-dlp-ejs component only",
        "upd_done": "Update finished, restarting",
        "upd_failed": "Update failed",
        "ejs_installing": "Installing yt-dlp-ejs (required for YouTube)",
        "ejs_failed": "Could not install yt-dlp-ejs",
        "js_none": "No JS runtime found: YouTube may return incomplete formats",
        "rutube_no_m3u8": "RuTube: stream link not received",
        "ytdlp_missing": "yt-dlp is not installed",
        "dl_dest": "Saved to",
    },
}

def T(key):
    return TEXTS.get(LANG, TEXTS["ru"]).get(key, key)

def save_lang(new_lang):
    global LANG
    LANG = new_lang
    try:
        LANG_FILE.write_text(new_lang, encoding="utf-8")
    except Exception:
        pass

DEFAULT_SETTINGS = {
    "video_codec": "iphone",
    "audio_codec": "aac",
    "max_height": 0,
    "auto_convert": "ask",
    "concurrent_fragments": 1,
    "cookies_file": "",
    "proxy": "",
    "dns_mode": "auto",
    "dns_servers": "1.1.1.1,8.8.8.8,94.140.14.14",
    "doh_url": "",
    "ipv4_only": True,
    "verify_tls": True,
    "preflight": True,
    "socket_timeout": 30,
    "retries": 10,
    "yt_clients": "",
    "js_runtime": "auto",
    "remote_ejs": False,
    "progress_width": 36,
    "ask_rename": True,
    "ask_fix": True,
    "base_dir": "/root/VideoDownloader",
}

CHOICES = {
    "dns_mode": ("auto", "system", "udp", "doh"),
    "auto_convert": ("ask", "always", "never"),
    "js_runtime": ("auto", "none", "deno", "node", "bun", "quickjs"),
}

INT_LIMITS = {
    "max_height": (0, 8640),
    "concurrent_fragments": (1, 16),
    "socket_timeout": (5, 600),
    "retries": (0, 50),
    "progress_width": (10, 80),
}

GROUPS = [
    ("grp_media", ["video_codec", "audio_codec", "max_height", "auto_convert", "concurrent_fragments", "cookies_file"]),
    ("grp_network", ["proxy", "dns_mode", "dns_servers", "doh_url", "ipv4_only", "verify_tls", "preflight",
                     "socket_timeout", "retries", "yt_clients", "js_runtime", "remote_ejs"]),
    ("grp_interface", ["language", "progress_width", "ask_rename", "ask_fix", "base_dir"]),
]

def load_settings():
    data = {}
    if SETTINGS_FILE.exists():
        try:
            raw = json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
            if isinstance(raw, dict):
                data = raw
        except Exception:
            data = {}
    result = {}
    for k, dv in DEFAULT_SETTINGS.items():
        v = data.get(k, dv)
        if type(v) is not type(dv):
            v = dv
        if k in CHOICES and v not in CHOICES[k]:
            v = dv
        if k in INT_LIMITS:
            lo, hi = INT_LIMITS[k]
            v = max(lo, min(hi, v))
        result[k] = v
    return result

def save_settings(s):
    try:
        SETTINGS_FILE.write_text(json.dumps(s, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception:
        pass

SETTINGS = load_settings()

BASE_DIR = Path(SETTINGS["base_dir"])
VIDEOS_DIR = BASE_DIR / "videos"
AUDIO_DIR = BASE_DIR / "audio"
FIX_DIR = BASE_DIR / "fix"
TMP_DIR = BASE_DIR / "tmp"

def apply_dirs():
    global BASE_DIR, VIDEOS_DIR, AUDIO_DIR, FIX_DIR, TMP_DIR
    BASE_DIR = Path(SETTINGS["base_dir"]).expanduser()
    VIDEOS_DIR = BASE_DIR / "videos"
    AUDIO_DIR = BASE_DIR / "audio"
    FIX_DIR = BASE_DIR / "fix"
    TMP_DIR = BASE_DIR / "tmp"

def ensure_dir():
    apply_dirs()
    try:
        for d in (VIDEOS_DIR, AUDIO_DIR, FIX_DIR, TMP_DIR):
            d.mkdir(parents=True, exist_ok=True)
    except OSError as e:
        err_line(f"{BASE_DIR}: {e}")
        SETTINGS["base_dir"] = str(HOME / "VideoDownloader")
        save_settings(SETTINGS)
        apply_dirs()
        for d in (VIDEOS_DIR, AUDIO_DIR, FIX_DIR, TMP_DIR):
            d.mkdir(parents=True, exist_ok=True)

DNS_CACHE = {}
DNS_STATE = {"order": None, "busy": False}
PREFLIGHT_OK = set()
QUICK = {"on": False}
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
    return [s.strip() for s in SETTINGS["dns_servers"].split(",") if s.strip()]

def doh_urls():
    urls = []
    if SETTINGS["doh_url"]:
        urls.append(SETTINGS["doh_url"])
    urls += ["https://1.1.1.1/dns-query", "https://8.8.8.8/resolve"]
    return urls

def dns_order():
    if DNS_STATE["order"]:
        return DNS_STATE["order"]
    table = {
        "auto": ["system", "udp", "doh"],
        "system": ["system"],
        "udp": ["udp", "doh", "system"],
        "doh": ["doh", "udp", "system"],
    }
    return table.get(SETTINGS["dns_mode"], table["auto"])

def build_query(host):
    tid = random.randint(0, 65535)
    header_bytes = struct.pack(">HHHHHH", tid, 0x0100, 1, 0, 0, 0)
    name = b"".join(bytes([len(p)]) + p.encode("ascii") for p in host.rstrip(".").split("."))
    return tid, header_bytes + name + b"\x00" + struct.pack(">HH", 1, 1)

def parse_response(data, tid):
    if len(data) < 12:
        return []
    rid, flags, qd, an, ns, ar = struct.unpack(">HHHHHH", data[:12])
    if rid != tid or (flags & 0x000F):
        return []

    def skip_name(p):
        while True:
            if p >= len(data):
                raise ValueError("truncated")
            n = data[p]
            if n == 0:
                return p + 1
            if n & 0xC0 == 0xC0:
                return p + 2
            p += n + 1

    pos = 12
    for _ in range(qd):
        pos = skip_name(pos) + 4
    ips = []
    for _ in range(an):
        pos = skip_name(pos)
        rtype, rclass, ttl, rdlen = struct.unpack(">HHIH", data[pos:pos + 10])
        pos += 10
        if rtype == 1 and rdlen == 4:
            ips.append(socket.inet_ntoa(data[pos:pos + 4]))
        pos += rdlen
    return ips

def udp_query(server, host, timeout=4):
    try:
        tid, pkt = build_query(host)
    except Exception as e:
        return [], str(e)
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.settimeout(timeout)
    try:
        s.sendto(pkt, (server, 53))
        data, _ = s.recvfrom(2048)
        return parse_response(data, tid), ""
    except Exception as e:
        return [], f"{type(e).__name__}: {e}"
    finally:
        s.close()

def doh_query(url, host, timeout=10):
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    sep = "&" if "?" in url else "?"
    req = urllib.request.Request(f"{url}{sep}name={host}&type=A",
                                 headers={"accept": "application/dns-json", "user-agent": UA})
    with opener.open(req, timeout=timeout) as r:
        data = json.loads(r.read().decode("utf-8", "replace"))
    return [a["data"] for a in data.get("Answer", []) if a.get("type") == 1 and a.get("data")]

def resolve_with(mode, host):
    if mode == "system":
        try:
            res = _orig_gai(host, 443, socket.AF_INET, socket.SOCK_STREAM)
            return list(dict.fromkeys(r[4][0] for r in res))
        except Exception:
            return []
    if mode == "udp":
        for srv in dns_servers():
            ips, _ = udp_query(srv, host)
            if ips:
                return ips
        return []
    if mode == "doh":
        DNS_STATE["busy"] = True
        try:
            for u in doh_urls():
                try:
                    ips = doh_query(u, host)
                    if ips:
                        return ips
                except Exception:
                    continue
        finally:
            DNS_STATE["busy"] = False
        return []
    return []

def patched_gai(host, port, family=0, type=0, proto=0, flags=0):
    if not isinstance(host, str) or not host or host == "localhost" or is_ip(host):
        return _orig_gai(host, port, family, type, proto, flags)
    if port is not None and not isinstance(port, int) and not str(port).isdigit():
        return _orig_gai(host, port, family, type, proto, flags)
    p = int(port) if port else 0
    ips = DNS_CACHE.get(host)
    if not ips:
        for m in dns_order():
            if m == "doh" and DNS_STATE["busy"]:
                continue
            if m == "system":
                try:
                    fam = socket.AF_INET if SETTINGS["ipv4_only"] else family
                    res = _orig_gai(host, port, fam, type, proto, flags)
                    if res:
                        return res
                except Exception:
                    pass
                continue
            ips = resolve_with(m, host)
            if ips:
                DNS_CACHE[host] = ips
                break
    if not ips:
        raise socket.gaierror(socket.EAI_NONAME, "Name does not resolve")
    st = type or socket.SOCK_STREAM
    return [(socket.AF_INET, st, proto or 0, "", (ip, p)) for ip in ips]

socket.getaddrinfo = patched_gai

def reset_dns():
    DNS_STATE["order"] = None
    DNS_CACHE.clear()
    PREFLIGHT_OK.clear()

def tls_probe(host, ip, timeout=15):
    ctx = ssl.create_default_context() if SETTINGS["verify_tls"] else ssl._create_unverified_context()
    sock = None
    try:
        sock = socket.create_connection((ip, 443), timeout)
        wrapped = ctx.wrap_socket(sock, server_hostname=host)
        wrapped.close()
        return True, ""
    except Exception as e:
        if sock is not None:
            try:
                sock.close()
            except Exception:
                pass
        return False, f"{type(e).__name__}: {e}"

def preflight(url):
    host = urlparse(url).hostname
    if not host or SETTINGS["proxy"] or not SETTINGS["preflight"] or host in PREFLIGHT_OK:
        return True
    info_line(f"{T('preflight_title')} {host}")
    order = []
    for m in dns_order() + ["system", "udp", "doh"]:
        if m not in order:
            order.append(m)
    for m in order:
        ips = resolve_with(m, host)
        if not ips:
            warn_line(f"{m}: {T('diag_fail')}")
            continue
        for ip in ips[:2]:
            ok, err = tls_probe(host, ip)
            if ok:
                DNS_STATE["order"] = [m] + [x for x in order if x != m]
                DNS_CACHE.clear()
                PREFLIGHT_OK.add(host)
                ok_line(f"{T('preflight_ok')}: {m} ({ip})")
                return True
            warn_line(f"{m} {ip}: {err}")
    err_line(T("preflight_fail"))
    warn_line(T("preflight_blocked"))
    return False

NET_PATTERNS = (
    "name does not resolve", "name or service not known", "temporary failure in name resolution",
    "try again", "handshake", "timed out", "timeout", "connection refused", "connection reset",
    "connection aborted", "network is unreachable", "no route to host", "transporterror",
    "errno -2", "errno -3", "errno 110", "errno 111", "errno 113", "eof occurred", "ssl",
)

def is_net_error(text):
    t = str(text).lower()
    return any(p in t for p in NET_PATTERNS)

def is_format_error(text):
    t = str(text).lower()
    return "requested format is not available" in t or "no video formats" in t

def trunc(s, n):
    s = str(s)
    return s if len(s) <= n else s[:n - 3] + "..."

def fmt_size(n):
    if n < 1024:
        return f"{n} B"
    if n < 1024 * 1024:
        return f"{n / 1024:.1f} KiB"
    if n < 1024 * 1024 * 1024:
        return f"{n / 1048576:.1f} MiB"
    return f"{n / 1073741824:.2f} GiB"

def confirm(prompt, default=False):
    suffix = " [Y/n]: " if default else " [y/N]: "
    try:
        ans = input(c(prompt + suffix, YELLOW)).strip().lower()
    except (EOFError, KeyboardInterrupt):
        return False
    if not ans:
        return default
    return ans in ("y", "yes", "д", "да")

def valid_url(u):
    try:
        p = urlparse(u)
        return p.scheme in ("http", "https") and bool(p.netloc)
    except (ValueError, TypeError):
        return False

def is_youtube(url):
    host = (urlparse(url).hostname or "").lower()
    return host.endswith(("youtube.com", "youtu.be", "youtube-nocookie.com"))

def safe_name(s, limit=150):
    s = re.sub(r'[\\/:*?"<>|%\n\r\t]+', "_", str(s)).strip()
    return s[:limit] or "video"

VIDEO_CODECS = {
    "iphone": {
        "label_key": "preset_iphone", "encoder": "libx264",
        "profile": "high", "level": "4.0", "crf": "23", "pix_fmt": "yuv420p", "preset": "medium",
        "audio_codec": "aac", "audio_bitrate": "128k", "movflags": "+faststart",
        "compat": ("h264", "avc1"),
    },
    "android": {
        "label_key": "preset_android", "encoder": "libx264",
        "profile": "high", "level": "4.0", "crf": "23", "pix_fmt": "yuv420p", "preset": "medium",
        "audio_codec": "aac", "audio_bitrate": "128k", "movflags": "+faststart",
        "compat": ("h264", "avc1"),
    },
    "universal": {
        "label_key": "preset_universal", "encoder": "libx264",
        "profile": "baseline", "level": "3.0", "crf": "23", "pix_fmt": "yuv420p", "preset": "medium",
        "audio_codec": "aac", "audio_bitrate": "128k", "movflags": "+faststart",
        "compat": ("h264", "avc1"),
    },
    "h265": {
        "label_key": "preset_h265", "encoder": "libx265",
        "crf": "28", "preset": "fast", "pix_fmt": "yuv420p",
        "audio_codec": "aac", "audio_bitrate": "128k", "movflags": "+faststart",
        "compat": ("hevc", "h265"),
    },
    "vp9": {
        "label_key": "preset_vp9", "encoder": "libvpx-vp9",
        "crf": "32", "speed": "6", "row_mt": "1", "pix_fmt": "yuv420p",
        "audio_codec": "opus", "audio_bitrate": "128k", "container": "webm",
        "compat": ("vp9",),
    },
    "av1": {
        "label_key": "preset_av1", "encoder": "libsvtav1",
        "crf": "35", "preset": "10", "pix_fmt": "yuv420p",
        "audio_codec": "opus", "audio_bitrate": "128k", "container": "mkv",
        "compat": ("av1",),
    },
    "original": {
        "label_key": "preset_original", "encoder": "copy", "audio_codec": "copy",
    },
}

AUDIO_CODECS = {
    "aac": {"label_key": "audio_aac", "encoder": "aac", "bitrate": "128k", "ext": "m4a", "probe": "aac"},
    "ac3": {"label_key": "audio_ac3", "encoder": "ac3", "bitrate": "192k", "ext": "ac3", "probe": "ac3"},
    "mp3": {"label_key": "audio_mp3", "encoder": "libmp3lame", "bitrate": "192k", "ext": "mp3", "probe": "mp3"},
    "opus": {"label_key": "audio_opus", "encoder": "libopus", "bitrate": "160k", "ext": "opus", "probe": "opus"},
    "flac": {"label_key": "audio_flac", "encoder": "flac", "bitrate": None, "ext": "flac", "probe": "flac"},
    "original": {"label_key": "audio_original", "encoder": "copy", "bitrate": None, "ext": None, "probe": None},
}

A_COMPAT = {"aac": ("aac", "mp4a"), "opus": ("opus",)}
VIDEO_EXTS = (".mp4", ".mkv", ".webm", ".mov", ".m4v", ".avi", ".flv", ".ts")
OUT_TMPL = "%(title).150B [%(id)s].%(ext)s"
JS_BIN = {"deno": "deno", "node": "node", "bun": "bun", "quickjs": "qjs"}
YT_CLIENT_SEQ = [[], ["tv"], ["android_vr"], ["web_safari"], ["mweb"], ["ios"], ["android"]]
SEEN_WARNINGS = set()
_encoders_cache = None

def available_encoders():
    global _encoders_cache
    if _encoders_cache is not None:
        return _encoders_cache
    _encoders_cache = set()
    if not shutil.which("ffmpeg"):
        return _encoders_cache
    try:
        r = subprocess.run(["ffmpeg", "-hide_banner", "-encoders"], capture_output=True, text=True, timeout=30)
        for line in r.stdout.splitlines():
            m = re.match(r"^ [A-Z.]{6} (\S+)", line)
            if m:
                _encoders_cache.add(m.group(1))
    except Exception:
        pass
    return _encoders_cache

def encoder_ok(name):
    return name == "copy" or name in available_encoders()

def js_runtime():
    rt = SETTINGS["js_runtime"]
    if rt == "none":
        return None
    if rt == "auto":
        for name, binary in JS_BIN.items():
            if shutil.which(binary):
                return name
        return None
    return rt if shutil.which(JS_BIN[rt]) else None

def has_ejs():
    try:
        return importlib.util.find_spec("yt_dlp_ejs") is not None
    except Exception:
        return False

def height_filter():
    h = SETTINGS["max_height"]
    return f"[height<={h}]" if h else ""

def default_selector():
    h = height_filter()
    return f"bv*[vcodec^=avc1]{h}+ba[ext=m4a]/b[ext=mp4]{h}/bv*{h}+ba/b{h}"

def selector_chain(chosen):
    h = height_filter()
    items = [chosen, default_selector(), f"bv*{h}+ba/b{h}", "b/w"]
    return list(dict.fromkeys(items))

class Log:
    def __init__(self):
        self.msgs = []

    def debug(self, m):
        pass

    def info(self, m):
        pass

    def warning(self, m):
        m = str(m)
        self.msgs.append(m)
        if m not in SEEN_WARNINGS:
            SEEN_WARNINGS.add(m)
            warn_line(m)

    def error(self, m):
        m = str(m)
        self.msgs.append(m)
        err_line(m)

    def text(self):
        return "\n".join(self.msgs)

def report(e, lg):
    msg = str(e).strip()
    if msg and not any(msg in m or m.strip() in msg for m in lg.msgs):
        err_line(f"{type(e).__name__}: {msg}")
    return lg.text() + "\n" + msg

class Progress:
    def __init__(self):
        self.bar = None

    def __call__(self, d):
        if tqdm is None:
            return
        st = d.get("status")
        if st == "downloading":
            total = d.get("total_bytes") or d.get("total_bytes_estimate")
            if self.bar is None:
                self.bar = tqdm(total=total, unit="B", unit_scale=True, leave=False,
                                ncols=SETTINGS["progress_width"], desc="dl")
            elif total:
                self.bar.total = total
            dl = d.get("downloaded_bytes") or 0
            self.bar.update(max(0, dl - self.bar.n))
        elif st in ("finished", "error"):
            self.close()

    def close(self):
        if self.bar is not None:
            self.bar.close()
            self.bar = None
            sys.stdout.write("\n")
            sys.stdout.flush()

def parse_clients(text):
    groups = []
    for part in text.split(","):
        part = part.strip()
        if part:
            groups.append([x.strip() for x in part.split("+") if x.strip()])
    return groups

def build_strategies(url, win=None):
    out = []
    if is_youtube(url):
        seq = parse_clients(SETTINGS["yt_clients"]) or YT_CLIENT_SEQ
        for cl in seq:
            out.append({"clients": cl, "name": "+".join(cl) or "default"})
    else:
        out.append({"clients": [], "name": "default"})
    if win:
        out.sort(key=lambda s: 0 if s["name"] == win else 1)
    return out

def base_opts(strategy=None, **extra):
    s = SETTINGS
    quick = QUICK["on"]
    o = {
        "quiet": True,
        "noplaylist": True,
        "logger": Log(),
        "socket_timeout": 15 if quick else s["socket_timeout"],
        "retries": 1 if quick else s["retries"],
        "fragment_retries": 1 if quick else s["retries"],
        "extractor_retries": 1 if quick else 3,
        "nocheckcertificate": not s["verify_tls"],
        "concurrent_fragment_downloads": max(1, s["concurrent_fragments"]),
    }
    if s["ipv4_only"]:
        o["source_address"] = "0.0.0.0"
    if s["proxy"]:
        o["proxy"] = s["proxy"]
    if s["cookies_file"] and Path(s["cookies_file"]).expanduser().exists():
        o["cookiefile"] = str(Path(s["cookies_file"]).expanduser())
    if strategy and strategy.get("clients"):
        o["extractor_args"] = {"youtube": {"player_client": list(strategy["clients"])}}
    rt = js_runtime()
    if rt:
        o["js_runtimes"] = {rt: {}}
    if s["remote_ejs"]:
        o["remote_components"] = ["ejs:github"]
    o.update(extra)
    return o

def first_entry(info):
    if isinstance(info, dict) and info.get("entries") is not None:
        return next((e for e in info["entries"] if isinstance(e, dict) and e.get("formats")), None)
    return info

def get_info(url, strategy):
    if yt_dlp is None:
        return None, ""
    o = base_opts(strategy)
    lg = o["logger"]
    try:
        with yt_dlp.YoutubeDL(o) as ydl:
            info = first_entry(ydl.extract_info(url, download=False))
        return info, lg.text()
    except Exception as e:
        return None, report(e, lg)

def extract_info_smart(url):
    net_fail = 0
    for st in build_strategies(url):
        if net_fail >= 2:
            break
        info, err = get_info(url, st)
        if isinstance(info, dict) and (info.get("formats") or info.get("url")):
            return info, st["name"]
        if is_net_error(err):
            net_fail += 1
        if not is_youtube(url):
            break
    return None, None

def ytdlp_cmd():
    if yt_dlp is not None:
        return [sys.executable, SCRIPT_PATH, "--ytdlp"]
    b = shutil.which("yt-dlp")
    return [b] if b else None

def run_module(url, selector, strategy, job, extra=None, outtmpl=None):
    if yt_dlp is None:
        return False, ""
    o = base_opts(strategy)
    lg = o["logger"]
    o.update(format=selector, outtmpl=str(outtmpl or (job["dir"] / OUT_TMPL)), continuedl=True, overwrites=False)
    if job["merge"]:
        o["merge_output_format"] = "mp4"
    if extra:
        o.update(extra)
    pg = Progress()
    o["progress_hooks"] = [pg]
    try:
        with yt_dlp.YoutubeDL(o) as ydl:
            code = ydl.download([url])
        return code in (None, 0), lg.text()
    except Exception as e:
        return False, report(e, lg)
    finally:
        pg.close()

def run_binary(url, selector, strategy, job, extra_flags=(), outtmpl=None):
    cmd0 = ytdlp_cmd()
    if not cmd0:
        return False, ""
    s = SETTINGS
    cmd = cmd0 + ["-f", selector, "--no-playlist", "--quiet", "--no-progress",
                  "-o", str(outtmpl or (job["dir"] / OUT_TMPL)),
                  "--socket-timeout", str(15 if QUICK["on"] else s["socket_timeout"]),
                  "--retries", str(1 if QUICK["on"] else s["retries"]),
                  "--fragment-retries", str(1 if QUICK["on"] else s["retries"]),
                  "-N", str(max(1, s["concurrent_fragments"]))]
    if job["merge"]:
        cmd += ["--merge-output-format", "mp4"]
    if s["ipv4_only"]:
        cmd.append("--force-ipv4")
    if s["proxy"]:
        cmd += ["--proxy", s["proxy"]]
    if not s["verify_tls"]:
        cmd.append("--no-check-certificate")
    if s["cookies_file"] and Path(s["cookies_file"]).expanduser().exists():
        cmd += ["--cookies", str(Path(s["cookies_file"]).expanduser())]
    if strategy and strategy.get("clients"):
        cmd += ["--extractor-args", "youtube:player_client=" + ",".join(strategy["clients"])]
    rt = js_runtime()
    if rt:
        cmd += ["--js-runtimes", rt]
    if s["remote_ejs"]:
        cmd += ["--remote-components", "ejs:github"]
    cmd += list(extra_flags) + [url]
    env = dict(os.environ, VD_DNS_ORDER=",".join(dns_order()), PYTHONUTF8="1")
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=7200, env=env)
    except Exception as e:
        err_line(f"{type(e).__name__}: {e}")
        return False, str(e)
    text = (r.stderr or "").strip()
    if text:
        for line in text.splitlines():
            (err_line if r.returncode else warn_line)(line)
    return r.returncode == 0, text

def run_any(url, selector, strategy, job, extra=None, flags=(), outtmpl=None):
    if yt_dlp is not None:
        return run_module(url, selector, strategy, job, extra, outtmpl)
    return run_binary(url, selector, strategy, job, flags, outtmpl)

def snapshot(d):
    result = {}
    try:
        for f in d.iterdir():
            if f.is_file():
                try:
                    result[f.name] = f.stat().st_mtime
                except OSError:
                    pass
    except OSError:
        pass
    return result

def newest_changed(d, before, exts=None):
    best, best_mt = None, 0
    try:
        for f in d.iterdir():
            if not f.is_file() or f.suffix in (".part", ".ytdl") or f.name.startswith("."):
                continue
            if exts and f.suffix.lower() not in exts:
                continue
            try:
                mt = f.stat().st_mtime
            except OSError:
                continue
            if mt > before.get(f.name, 0) and mt > best_mt:
                best, best_mt = f, mt
    except OSError:
        pass
    return best

def cleanup_junk():
    removed = []
    for d in (VIDEOS_DIR, AUDIO_DIR):
        try:
            for f in d.iterdir():
                if not f.is_file():
                    continue
                junk = f.suffix in (".part", ".ytdl") or ".temp." in f.name
                if not junk and re.search(r"\.f\d+$", f.stem) and f.suffix.lower() in (".mp4", ".m4a", ".webm", ".mkv"):
                    junk = True
                if junk:
                    try:
                        f.unlink()
                        removed.append(f.name)
                    except OSError:
                        pass
        except OSError:
            pass
    try:
        for d in TMP_DIR.iterdir():
            shutil.rmtree(d, ignore_errors=True) if d.is_dir() else d.unlink()
            removed.append(d.name)
    except OSError:
        pass
    if removed:
        info_line(f"{T('junk_cleaned')}: {len(removed)}")
    return removed

def get_duration(path):
    if not shutil.which("ffprobe"):
        return None
    try:
        r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                            "-of", "default=noprint_wrappers=1:nokey=1", str(path)],
                           capture_output=True, text=True, timeout=30)
        return float(r.stdout.strip())
    except Exception:
        return None

def probe_codec(path, stream):
    if not shutil.which("ffprobe"):
        return ""
    try:
        r = subprocess.run(["ffprobe", "-v", "error", "-select_streams", stream,
                            "-show_entries", "stream=codec_name", "-of", "default=nw=1:nk=1", str(path)],
                           capture_output=True, text=True, timeout=30)
        return r.stdout.strip().lower()
    except Exception:
        return ""

def run_ffmpeg_with_progress(cmd, duration, desc):
    if tqdm is None:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=14400)
        if r.returncode != 0 and r.stderr:
            err_line(r.stderr.strip()[-1500:])
        return r.returncode == 0
    full = cmd[:1] + ["-nostats", "-progress", "pipe:1"] + cmd[1:]
    try:
        proc = subprocess.Popen(full, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    except Exception as e:
        err_line(f"ffmpeg: {e}")
        return False
    pbar = tqdm(total=duration or 0, unit="s", desc=desc, leave=False, ncols=SETTINGS["progress_width"])
    last = 0
    try:
        for line in proc.stdout:
            line = line.strip()
            if line.startswith("out_time_ms="):
                try:
                    secs = int(line.split("=", 1)[1]) / 1000000.0
                    if secs > last:
                        pbar.update(secs - last)
                        last = secs
                except ValueError:
                    pass
            elif line.startswith("progress=") and line.endswith("end"):
                break
    except Exception:
        pass
    finally:
        try:
            _, errtext = proc.communicate(timeout=120)
        except Exception:
            proc.kill()
            errtext = ""
        if duration and last < duration:
            pbar.update(duration - last)
        pbar.close()
        sys.stdout.write("\n")
        sys.stdout.flush()
    if proc.returncode != 0 and errtext:
        err_line(errtext.strip()[-1500:])
    return proc.returncode == 0

def check_compat(path, vkey):
    if not path or not path.exists():
        return True
    v = VIDEO_CODECS.get(vkey, VIDEO_CODECS["iphone"])
    if v.get("encoder") == "copy" or not shutil.which("ffprobe"):
        return True
    vcodec = probe_codec(path, "v:0")
    acodec = probe_codec(path, "a:0")
    acompat = A_COMPAT.get(v.get("audio_codec"))
    if vcodec and vcodec not in v.get("compat", ()):
        return False
    if acodec and acompat and acodec not in acompat:
        return False
    return True

def build_ffmpeg_cmd(src, dst, vkey):
    v = VIDEO_CODECS.get(vkey, VIDEO_CODECS["iphone"])
    cmd = ["ffmpeg", "-y", "-i", str(src)]
    if v.get("encoder") == "copy":
        cmd += ["-c:v", "copy"]
    else:
        cmd += ["-c:v", v["encoder"]]
        if v.get("preset"):
            cmd += ["-preset", v["preset"]]
        if v["encoder"] == "libvpx-vp9":
            cmd += ["-crf", v["crf"], "-b:v", "0"]
        elif v.get("crf"):
            cmd += ["-crf", v["crf"]]
        if v.get("profile"):
            cmd += ["-profile:v", v["profile"]]
        if v.get("level"):
            cmd += ["-level", v["level"]]
        if v.get("pix_fmt"):
            cmd += ["-pix_fmt", v["pix_fmt"]]
        if v.get("speed"):
            cmd += ["-speed", v["speed"]]
        if v.get("row_mt"):
            cmd += ["-row-mt", v["row_mt"]]
    vac = v.get("audio_codec", "copy")
    if vac == "aac":
        cmd += ["-c:a", "aac", "-b:a", v.get("audio_bitrate", "128k")]
    elif vac == "opus":
        cmd += ["-c:a", "libopus", "-b:a", v.get("audio_bitrate", "128k")]
    else:
        cmd += ["-c:a", "copy"]
    if v.get("movflags"):
        cmd += ["-movflags", v["movflags"]]
    cmd.append(str(dst))
    return cmd

def convert_file(src, vkey):
    v = VIDEO_CODECS.get(vkey, VIDEO_CODECS["iphone"])
    if not shutil.which("ffmpeg"):
        err_line(T("ffmpeg_missing"))
        return src
    aenc = {"aac": "aac", "opus": "libopus"}.get(v.get("audio_codec"), "copy")
    if not encoder_ok(v.get("encoder", "copy")) or not encoder_ok(aenc):
        warn_line(T("encoder_missing"))
        return src
    container = v.get("container", "mp4")
    same = src.suffix.lower() == "." + container
    dst = src.with_name(src.stem + ".vdtmp." + container) if same else src.with_suffix("." + container)
    cmd = build_ffmpeg_cmd(src, dst, vkey)
    info_line(f"{T('converting')}: {src.name}")
    ok = run_ffmpeg_with_progress(cmd, get_duration(src), T("converting"))
    if ok and dst.exists() and dst.stat().st_size > 0:
        try:
            src.unlink()
            final = src if same else dst
            if same:
                dst.rename(final)
            return final
        except OSError as e:
            err_line(str(e))
            return dst
    err_line(T("convert_failed"))
    try:
        if dst.exists():
            dst.unlink()
    except OSError:
        pass
    return src

def convert_audio(src, akey):
    a = AUDIO_CODECS.get(akey, AUDIO_CODECS["aac"])
    if a["encoder"] == "copy" or not src or not src.exists():
        return src
    if probe_codec(src, "a:0") == a["probe"]:
        return src
    if not shutil.which("ffmpeg"):
        err_line(T("ffmpeg_missing"))
        return src
    if not encoder_ok(a["encoder"]):
        warn_line(T("encoder_missing"))
        return src
    dst = src.with_suffix("." + a["ext"])
    if dst == src:
        dst = src.with_name(src.stem + ".vdtmp." + a["ext"])
    cmd = ["ffmpeg", "-y", "-i", str(src), "-vn", "-c:a", a["encoder"]]
    if a["bitrate"]:
        cmd += ["-b:a", a["bitrate"]]
    cmd.append(str(dst))
    info_line(f"{T('converting')}: {src.name}")
    ok = run_ffmpeg_with_progress(cmd, get_duration(src), T("converting"))
    if ok and dst.exists() and dst.stat().st_size > 0:
        try:
            src.unlink()
        except OSError:
            pass
        final = dst
        if ".vdtmp." in dst.name:
            final = src.with_suffix("." + a["ext"])
            try:
                dst.rename(final)
            except OSError:
                final = dst
        return final
    err_line(T("convert_failed"))
    return src

def select_format(info):
    default = default_selector()
    if not isinstance(info, dict):
        return default
    formats = info.get("formats") or []
    videos = [f for f in formats if isinstance(f, dict) and f.get("format_id") and f.get("vcodec") not in (None, "none")]
    audios = [f for f in formats if isinstance(f, dict) and f.get("format_id") and f.get("vcodec") == "none" and f.get("acodec") not in (None, "none")]
    if not videos:
        return default
    uniq = {}
    for f in videos:
        uniq[(f.get("height"), f.get("ext"), f.get("fps"), f.get("vcodec"), f.get("acodec"))] = f
    vlist = sorted(uniq.values(), key=lambda x: (x.get("height") or 0, x.get("fps") or 0))
    print(c(f"\n{T('available_formats')}:", CYAN))
    for i, f in enumerate(vlist, 1):
        size = f.get("filesize") or f.get("filesize_approx")
        size_t = f", {size / 1048576:.0f}M" if isinstance(size, (int, float)) else ""
        fps_t = f", {f['fps']}fps" if f.get("fps") else ""
        aud = "+" if f.get("acodec") not in (None, "none") else "-"
        print(f"  {i}. {f.get('height') or '?'}p {f.get('ext') or '?'} {aud}{fps_t}{size_t}")
    try:
        ch = input(c(f"\n{T('select_video')}: ", YELLOW)).strip()
    except (EOFError, KeyboardInterrupt):
        return default
    if not ch:
        return default
    try:
        sel = vlist[int(ch) - 1]
    except (ValueError, IndexError):
        warn_line(T("invalid_default"))
        return default
    vid = str(sel["format_id"])
    if sel.get("acodec") not in (None, "none"):
        return vid
    if not audios:
        return f"{vid}+ba/b"
    print(c(f"\n{T('select_audio_track')}:", CYAN))
    for i, f in enumerate(audios, 1):
        abr = f.get("abr")
        abr_t = f", {abr:g}kbps" if isinstance(abr, (int, float)) else ""
        print(f"  {i}. {f.get('language') or 'unknown'}, {f.get('ext') or '?'}{abr_t}")
    try:
        a = input(c(f"{T('select_audio_track')}: ", YELLOW)).strip()
        if not a:
            return f"{vid}+ba/b"
        return f"{vid}+{audios[int(a) - 1]['format_id']}"
    except (ValueError, IndexError, EOFError, KeyboardInterrupt):
        return f"{vid}+ba/b"

def make_opener():
    handlers = []
    px = SETTINGS["proxy"]
    if px and px.split("://")[0].lower() in ("http", "https"):
        handlers.append(urllib.request.ProxyHandler({"http": px, "https": px}))
    if not SETTINGS["verify_tls"]:
        handlers.append(urllib.request.HTTPSHandler(context=ssl._create_unverified_context()))
    return urllib.request.build_opener(*handlers)

def http_json(url, referer="https://rutube.ru/"):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Referer": referer, "Accept": "application/json"})
    with make_opener().open(req, timeout=SETTINGS["socket_timeout"]) as r:
        return json.loads(r.read().decode("utf-8", "replace"))

def rutube_download(url, job):
    m = re.search(r"rutube\.ru/(?:video|play/embed|video/private)/([0-9a-f]{32})", url)
    if not m:
        return False
    vid = m.group(1)
    p = re.search(r"[?&]p=([\w-]+)", url)
    private = f"&p={p.group(1)}" if p else ""
    info_line(T("trying_rutube"))
    title = vid
    try:
        title = http_json(f"https://rutube.ru/api/video/{vid}/?format=json").get("title") or vid
    except Exception as e:
        warn_line(f"{type(e).__name__}: {e}")
    title = safe_name(title)
    ref = "https%3A%2F%2Frutube.ru"
    variants = [
        f"https://rutube.ru/api/play/options/{vid}/?no_404=true&referer={ref}&pver=v2&client=wdp{private}",
        f"https://rutube.ru/api/play/options/{vid}/?no_404=true&referer={ref}&pver=v2{private}",
        f"https://rutube.ru/api/play/options/{vid}/?no_404=true&referer={ref}{private}",
        f"https://rutube.ru/api/play/options/{vid}/?format=json{private}",
        f"https://rutube.ru/api/play/options/{vid}/?no_404=true&referer=https%3A%2F%2Frutube.ru%2Fplay%2Fembed%2F{vid}&pver=v2",
    ]
    m3u8 = None
    for u in variants:
        try:
            data = http_json(u)
            vb = data.get("video_balancer") or {}
            m3u8 = (vb.get("m3u8") or vb.get("default")) if isinstance(vb, dict) else None
            if m3u8:
                break
        except Exception as e:
            warn_line(f"{type(e).__name__}: {e}")
    if not m3u8:
        err_line(T("rutube_no_m3u8"))
        return False
    hdrs = {"User-Agent": UA, "Referer": "https://rutube.ru/", "Origin": "https://rutube.ru"}
    out_tmpl = job["dir"] / f"{title} [{vid}].%(ext)s"
    for sel in (default_selector(), "bv*+ba/b", "b"):
        ok, _ = run_any(m3u8, sel, None, job, extra={"http_headers": hdrs}, outtmpl=out_tmpl)
        if ok:
            return True
    if shutil.which("ffmpeg"):
        out = job["dir"] / f"{title} [{vid}].mp4"
        hs = "".join(f"{k}: {v}\r\n" for k, v in hdrs.items())
        cmd = ["ffmpeg", "-y", "-headers", hs, "-i", m3u8, "-c", "copy", "-bsf:a", "aac_adtstoasc", str(out)]
        try:
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=7200)
            if r.returncode == 0 and out.exists() and out.stat().st_size > 0:
                return True
            if r.stderr:
                err_line(r.stderr.strip()[-1500:])
        except Exception as e:
            err_line(f"{type(e).__name__}: {e}")
    return False

def ffmpeg_merge(vfile, afile, out):
    attempts = (
        ["ffmpeg", "-y", "-i", str(vfile), "-i", str(afile), "-c", "copy", str(out)],
        ["ffmpeg", "-y", "-i", str(vfile), "-i", str(afile), "-c:v", "copy", "-c:a", "aac", "-b:a", "128k", str(out)],
    )
    for cmd in attempts:
        try:
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=7200)
        except Exception as e:
            err_line(f"{type(e).__name__}: {e}")
            return False
        if r.returncode == 0 and out.exists() and out.stat().st_size > 0:
            return True
        if r.stderr:
            err_line(r.stderr.strip()[-1500:])
    return False

def manual_merge(url, strategy, info, job):
    if not shutil.which("ffmpeg"):
        err_line(T("ffmpeg_missing"))
        return False
    info = info if isinstance(info, dict) else {}
    stamp = str(int(time.time()))
    tdir = TMP_DIR / stamp
    tdir.mkdir(parents=True, exist_ok=True)
    h = height_filter()
    try:
        run_any(url, f"bv*[vcodec^=avc1]{h}/bv*{h}", strategy, job, extra={"merge_output_format": None},
                flags=(), outtmpl=tdir / "video.%(ext)s")
        run_any(url, "ba[ext=m4a]/ba/b", strategy, job, extra={"merge_output_format": None},
                outtmpl=tdir / "audio.%(ext)s")
        vf = next(iter(sorted(tdir.glob("video.*"))), None)
        af = next(iter(sorted(tdir.glob("audio.*"))), None)
        name = f"{safe_name(info.get('title') or 'video_' + stamp)} [{info.get('id') or stamp}].mp4"
        out = job["dir"] / name
        if vf and af:
            return ffmpeg_merge(vf, af, out)
        if vf:
            shutil.move(str(vf), str(out.with_suffix(vf.suffix)))
            return True
        return False
    finally:
        shutil.rmtree(tdir, ignore_errors=True)

def external_download(url, info, job):
    if not isinstance(info, dict):
        return False
    audio = job["kind"] == "audio"
    fm = [f for f in info.get("formats") or [] if isinstance(f, dict) and f.get("url")]
    title = safe_name(info.get("title") or "video")
    vid = info.get("id") or "id"
    mh = SETTINGS["max_height"]
    prog = [f for f in fm if f.get("protocol") in ("https", "http")]
    if audio:
        cands = [f for f in prog if f.get("vcodec") in (None, "none") and f.get("acodec") not in (None, "none")]
        cands.sort(key=lambda f: f.get("abr") or 0, reverse=True)
    else:
        cands = [f for f in prog if f.get("vcodec") not in (None, "none") and f.get("acodec") not in (None, "none")]
        if mh:
            cands = [f for f in cands if (f.get("height") or 0) <= mh] or cands
        cands.sort(key=lambda f: f.get("height") or 0, reverse=True)
    s = SETTINGS
    for f in cands[:3]:
        ext = f.get("ext") or "mp4"
        out = job["dir"] / f"{title} [{vid}].{ext}"
        furl = f["url"]
        headers = f.get("http_headers") or {}
        host = urlparse(furl).hostname or ""
        port = 443 if furl.startswith("https") else 80
        ips = resolve_with("udp", host) or resolve_with("doh", host) if host else []
        tools = []
        if shutil.which("curl"):
            cmd = ["curl", "-L", "--fail", "--retry", "3", "--connect-timeout", str(s["socket_timeout"]), "-#"]
            if s["ipv4_only"]:
                cmd.append("--ipv4")
            if s["proxy"]:
                cmd += ["-x", s["proxy"]]
            if not s["verify_tls"]:
                cmd.append("-k")
            if ips and not s["proxy"]:
                cmd += ["--resolve", f"{host}:{port}:{ips[0]}"]
            for k, v in headers.items():
                cmd += ["-H", f"{k}: {v}"]
            tools.append(("curl", cmd + ["-o", str(out), furl]))
        if shutil.which("wget") and not s["proxy"]:
            cmd = ["wget", "--tries=3", "-O", str(out)]
            if not s["verify_tls"]:
                cmd.append("--no-check-certificate")
            for k, v in headers.items():
                cmd.append(f"--header={k}: {v}")
            tools.append(("wget", cmd + [furl]))
        if shutil.which("aria2c"):
            cmd = ["aria2c", "-x", "4", "-d", str(job["dir"]), "-o", out.name]
            if s["proxy"]:
                cmd.append(f"--all-proxy={s['proxy']}")
            if not s["verify_tls"]:
                cmd.append("--check-certificate=false")
            for k, v in headers.items():
                cmd.append(f"--header={k}: {v}")
            tools.append(("aria2c", cmd + [furl]))
        for name, cmd in tools:
            info_line(name)
            try:
                r = subprocess.run(cmd, timeout=7200)
                if r.returncode == 0 and out.exists() and out.stat().st_size > 0:
                    return True
            except Exception as e:
                err_line(f"{name}: {type(e).__name__}: {e}")
            try:
                if out.exists():
                    out.unlink()
            except OSError:
                pass
    if not audio and shutil.which("ffmpeg"):
        hls = [f for f in fm if f.get("protocol") in ("m3u8", "m3u8_native")]
        hls.sort(key=lambda f: f.get("height") or 0, reverse=True)
        if mh:
            hls = [f for f in hls if (f.get("height") or 0) <= mh] or hls
        for f in hls[:2]:
            out = job["dir"] / f"{title} [{vid}].mp4"
            headers = f.get("http_headers") or {}
            hs = "".join(f"{k}: {v}\r\n" for k, v in headers.items())
            cmd = ["ffmpeg", "-y"]
            if hs:
                cmd += ["-headers", hs]
            cmd += ["-i", f["url"], "-c", "copy", "-bsf:a", "aac_adtstoasc", str(out)]
            try:
                r = subprocess.run(cmd, capture_output=True, text=True, timeout=7200)
                if r.returncode == 0 and out.exists() and out.stat().st_size > 0:
                    return True
                if r.stderr:
                    err_line(r.stderr.strip()[-1500:])
            except Exception as e:
                err_line(f"{type(e).__name__}: {e}")
    return False

def prompt_proxy():
    warn_line(T("net_help"))
    try:
        v = input(c(T("proxy_prompt") + ": ", YELLOW)).strip()
    except (EOFError, KeyboardInterrupt):
        return False
    if not v:
        return False
    if not re.match(r"^(https?|socks4a?|socks5h?)://\S+$", v, re.I):
        err_line(T("proxy_invalid"))
        return False
    SETTINGS["proxy"] = v
    save_settings(SETTINGS)
    reset_dns()
    QUICK["on"] = False
    info_line(T("proxy_set"))
    return True

def prepare_network(url):
    QUICK["on"] = False
    if preflight(url):
        return True
    if prompt_proxy():
        return True
    if confirm(T("preflight_continue"), default=True):
        QUICK["on"] = True
        return True
    return False

def download_chain(url, job, chosen, info, win, allow_proxy=True):
    selectors = job["selectors"] or selector_chain(chosen)
    strategies = build_strategies(url, win)
    net_fail = 0
    for st in strategies:
        if net_fail >= 2:
            break
        for sel in selectors:
            info_line(f"{T('strategy')}: {st['name']} | {T('selector')}: {sel}")
            ok, err = run_any(url, sel, st, job)
            if ok:
                return True
            if is_net_error(err):
                net_fail += 1
                break
            if not is_format_error(err):
                break
    if net_fail >= 2:
        QUICK["on"] = True
    first = strategies[0]
    if yt_dlp is not None and ytdlp_cmd():
        info_line(T("trying_binary"))
        ok, err = run_binary(url, selectors[0], first, job)
        if ok:
            return True
        if is_net_error(err):
            net_fail += 1
    if job["kind"] == "video" and "rutube.ru" in url:
        if rutube_download(url, job):
            return True
    info_line(T("trying_generic"))
    ok, err = run_any(url, selectors[-1], None, job, extra={"force_generic_extractor": True},
                      flags=("--force-generic-extractor",))
    if ok:
        return True
    if job["kind"] == "video" and info:
        info_line(T("trying_manual"))
        if manual_merge(url, first, info, job):
            return True
    if info:
        info_line(T("trying_external"))
        if external_download(url, info, job):
            return True
    if net_fail and allow_proxy and prompt_proxy():
        return download_chain(url, job, chosen, info, win, allow_proxy=False)
    if SETTINGS["verify_tls"] and confirm(T("retry_tls")):
        ok, err = run_any(url, selectors[-1], first, job, extra={"nocheckcertificate": True},
                          flags=("--no-check-certificate",))
        if ok:
            return True
    return False

def make_job(kind):
    if kind == "audio":
        return {"kind": "audio", "dir": AUDIO_DIR, "merge": False, "selectors": ["bestaudio/best", "b"]}
    return {"kind": "video", "dir": VIDEOS_DIR, "merge": True, "selectors": None}

def attempt_download_video(url):
    if not valid_url(url):
        err_line(f"{T('invalid_url')}: {url}")
        return False, None
    if not prepare_network(url):
        return False, None
    job = make_job("video")
    before = snapshot(VIDEOS_DIR)
    info, win = extract_info_smart(url)
    chosen = select_format(info)
    info_line(f"{T('selector')}: {chosen}")
    if not download_chain(url, job, chosen, info, win):
        err_line(T("all_exhausted"))
        return False, None
    cleanup_junk()
    f = newest_changed(VIDEOS_DIR, before, VIDEO_EXTS)
    if f is None:
        return True, None
    vkey = SETTINGS["video_codec"]
    mode = SETTINGS["auto_convert"]
    if mode != "never" and not check_compat(f, vkey):
        warn_line(T("compat_warning"))
        if mode == "always" or confirm(T("convert_prompt")):
            f = convert_file(f, vkey)
            ok_line(f"{T('convert_done')}: {f.name}")
        else:
            info_line(T("convert_cancelled"))
    return True, f

def attempt_download_audio(url):
    if not valid_url(url):
        err_line(f"{T('invalid_url')}: {url}")
        return False, None
    if not prepare_network(url):
        return False, None
    job = make_job("audio")
    before = snapshot(AUDIO_DIR)
    info, win = extract_info_smart(url)
    if not download_chain(url, job, "bestaudio/best", info, win):
        err_line(T("all_exhausted"))
        return False, None
    cleanup_junk()
    f = newest_changed(AUDIO_DIR, before)
    if f is not None:
        f = convert_audio(f, SETTINGS["audio_codec"])
    return True, f

def move_to_fix(path):
    if not path or not path.exists():
        return False
    dest = FIX_DIR / path.name
    n = 1
    while dest.exists():
        dest = FIX_DIR / f"{path.stem}_{n}{path.suffix}"
        n += 1
    try:
        path.rename(dest)
        ok_line(f"{T('fm_moved')}: {dest.name}")
        return True
    except OSError as e:
        err_line(f"{T('fm_failed')}: {e}")
        return False

def rename_file(path, new_name):
    if not new_name.endswith(path.suffix):
        new_name += path.suffix
    new_name = re.sub(r'[\\/:*?"<>|]', "_", new_name)
    new_path = path.parent / new_name
    if new_path.exists() and new_path != path:
        err_line(f"{T('fm_failed')}: {T('fm_exists')}")
        return path
    try:
        path.rename(new_path)
        ok_line(f"{T('fm_renamed')}: {new_name}")
        return new_path
    except OSError as e:
        err_line(f"{T('fm_failed')}: {e}")
        return path

def show_ready_and_rename(path, is_audio=False):
    if not path or not path.exists():
        return path
    try:
        size = path.stat().st_size
    except OSError:
        size = 0
    print()
    print(c("=" * 40, GREEN))
    print(c("  " + T("audio_ready" if is_audio else "video_ready"), GREEN))
    print(c("=" * 40, GREEN))
    print(c(f"  {T('file')}: {path.name}", CYAN))
    print(c(f"  {T('size')}: {fmt_size(size)}", CYAN))
    print(c(f"  {T('dl_dest')}: {path.parent}", CYAN))
    print()
    if SETTINGS["ask_rename"] and confirm(T("rename_prompt")):
        try:
            new_name = input(c(f"{T('fm_new_name')}: ", YELLOW)).strip()
        except (EOFError, KeyboardInterrupt):
            new_name = ""
        if new_name:
            path = rename_file(path, new_name)
    if not is_audio and SETTINGS["ask_fix"] and confirm(T("move_fix_prompt")):
        move_to_fix(path)
    return path

def find_videos_on_page(page_url):
    info_line(f"{T('scanning')}: {page_url}")
    if yt_dlp is None:
        return []
    o = base_opts(extract_flat=True, noplaylist=False)
    lg = o["logger"]
    try:
        with yt_dlp.YoutubeDL(o) as ydl:
            info = ydl.extract_info(page_url, download=False)
    except Exception as e:
        report(e, lg)
        return []
    if not isinstance(info, dict):
        return []
    if info.get("entries") is not None:
        urls = []
        for e in info["entries"]:
            if isinstance(e, dict):
                u = e.get("webpage_url") or e.get("url")
                if isinstance(u, str) and u.startswith(("http://", "https://")):
                    urls.append(u)
        urls = list(dict.fromkeys(urls))
        ok_line(f"{T('found_videos')}: {len(urls)}")
        return urls
    u = info.get("webpage_url") or info.get("original_url") or info.get("url")
    return [u] if isinstance(u, str) and valid_url(u) else []

DIRECT = ("youtube.com/", "youtu.be/", "rutube.ru/video/", "rutube.ru/play/", ".mp4", ".m3u8")

def download_one(url, audio_only):
    if audio_only:
        ok, fp = attempt_download_audio(url)
    else:
        ok, fp = attempt_download_video(url)
    if ok and fp:
        show_ready_and_rename(fp, is_audio=audio_only)

def process_links(links, audio_only=False):
    for url in links:
        if not valid_url(url):
            err_line(f"{T('invalid_url')}: {url}")
            continue
        if audio_only or any(m in url.lower() for m in DIRECT):
            download_one(url, audio_only)
            continue
        found = find_videos_on_page(url)
        if not found:
            warn_line(f"{T('no_videos')}: {url}")
            continue
        if len(found) == 1:
            download_one(found[0], False)
            continue
        print(c(f"\n{T('multiple_videos')}:", CYAN))
        for i, u in enumerate(found, 1):
            print(f"  {i}. {u}")
        try:
            ch = input(c(f"{T('number_or_all')}: ", YELLOW)).strip().lower()
            if ch == "all":
                for u in found:
                    download_one(u, False)
            else:
                download_one(found[int(ch) - 1], False)
        except (ValueError, IndexError, EOFError, KeyboardInterrupt):
            err_line(T("invalid_choice"))

def list_files(directory):
    try:
        files = sorted(directory.iterdir(), key=lambda p: p.name.lower())
    except OSError:
        return []
    return [f for f in files if f.is_file() and not f.name.startswith(".")]

def parse_numbers(text, max_index):
    text = text.strip().lower()
    if text in ("all", "a"):
        return list(range(1, max_index + 1))
    result = []
    for part in [p.strip() for p in text.split(",") if p.strip()]:
        if "-" in part:
            left, right = part.split("-", 1)
            if not left.isdigit() or not right.isdigit():
                raise ValueError
            a, b = sorted((int(left), int(right)))
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

def ask_numbers(prompt, count):
    try:
        return parse_numbers(input(c(prompt, YELLOW)).strip(), count)
    except (ValueError, EOFError, KeyboardInterrupt):
        err_line(T("invalid_choice"))
        return None

def print_files(files):
    for i, f in enumerate(files, 1):
        try:
            size = f.stat().st_size
        except OSError:
            size = 0
        print(f"  {i}. {f.name} ({fmt_size(size)})")

def file_manager_choose_dir():
    while True:
        header(T("fm_choose_dir"))
        print(f"  1. {T('fm_videos')}\n  2. {T('fm_audio')}\n  3. {T('fm_fix')}\n  0. {T('fm_back')}")
        try:
            ch = input(c(f"{T('choice')}: ", GREEN)).strip().lower()
        except (EOFError, KeyboardInterrupt):
            return None
        if ch in ("0", "q"):
            return None
        if ch in ("1", "2", "3"):
            return {"1": VIDEOS_DIR, "2": AUDIO_DIR, "3": FIX_DIR}[ch]
        err_line(T("invalid_choice"))

def file_manager():
    ensure_dir()
    current = file_manager_choose_dir()
    if current is None:
        return
    while True:
        files = list_files(current)
        header(T("fm_title"))
        print(c(f"{current} ({len(files)})", CYAN))
        print("-" * 40)
        if files:
            print_files(files)
        else:
            warn_line(T("fm_empty"))
        print("-" * 40)
        print(f"  1. {T('fm_delete')}\n  2. {T('fm_delete_multi')}\n  3. {T('fm_delete_all')}")
        print(f"  4. {T('fm_rename')}\n  5. {T('fm_move_to_fix')}\n  6. {T('fm_restore')}")
        print(f"  7. {T('fm_choose_dir')}\n  0. {T('fm_back')}")
        try:
            ch = input(c(f"{T('choice')}: ", GREEN)).strip().lower()
        except (EOFError, KeyboardInterrupt):
            return
        if ch in ("0", "q"):
            return
        if ch == "7":
            nd = file_manager_choose_dir()
            if nd:
                current = nd
            continue
        if ch not in ("1", "2", "3", "4", "5", "6"):
            err_line(T("invalid_choice"))
            continue
        if ch == "6":
            fix_files = list_files(FIX_DIR)
            if not fix_files:
                warn_line(T("fm_empty"))
                continue
            header(T("fm_restore"))
            print_files(fix_files)
            nums = ask_numbers(f"{T('fm_file_index')} (1-{len(fix_files)}): ", len(fix_files))
            if not nums:
                continue
            target = fix_files[nums[0] - 1]
            dest = AUDIO_DIR if target.suffix.lower() in (".mp3", ".m4a", ".opus", ".flac", ".ac3") else VIDEOS_DIR
            try:
                target.rename(dest / target.name)
                ok_line(f"{T('fm_moved')}: {target.name}")
            except OSError as e:
                err_line(f"{T('fm_failed')}: {e}")
            continue
        if not files:
            continue
        if ch == "3":
            if confirm(f"{T('fm_delete_all')} ({len(files)})?"):
                count = 0
                for f in files:
                    try:
                        f.unlink()
                        count += 1
                    except OSError as e:
                        err_line(f"{T('fm_failed')}: {e}")
                ok_line(f"{T('fm_deleted')}: {count}")
            continue
        nums = ask_numbers(f"{T('fm_numbers')} (1-{len(files)}): ", len(files))
        if not nums:
            continue
        if ch in ("1", "2"):
            targets = [files[n - 1] for n in (nums[:1] if ch == "1" else nums)]
            if confirm(f"{T('fm_delete')}: {', '.join(t.name for t in targets)}?"):
                for t in targets:
                    try:
                        t.unlink()
                        ok_line(f"{T('fm_deleted')}: {t.name}")
                    except OSError as e:
                        err_line(f"{T('fm_failed')}: {e}")
        elif ch == "4":
            target = files[nums[0] - 1]
            try:
                new_name = input(c(f"{T('fm_new_name')}: ", YELLOW)).strip()
            except (EOFError, KeyboardInterrupt):
                continue
            if new_name:
                rename_file(target, new_name)
        elif ch == "5":
            move_to_fix(files[nums[0] - 1])

def language_menu():
    while True:
        header(T("set_language"))
        print(f"  1. {T('lang_ru')}\n  2. {T('lang_en')}\n  0. {T('fm_back')}")
        try:
            ch = input(c(f"{T('choice')}: ", GREEN)).strip().lower()
        except (EOFError, KeyboardInterrupt):
            return
        if ch in ("0", "q"):
            return
        if ch in ("1", "2"):
            save_lang("ru" if ch == "1" else "en")
            ok_line(T("set_saved"))
            return

def setting_display(key):
    if key == "language":
        return T("lang_ru" if LANG == "ru" else "lang_en")
    v = SETTINGS[key]
    if key == "video_codec":
        return T(VIDEO_CODECS[v]["label_key"])
    if key == "audio_codec":
        return T(AUDIO_CODECS[v]["label_key"])
    if isinstance(v, bool):
        return T("on" if v else "off")
    if key in CHOICES:
        return T("opt_" + v)
    if key == "max_height" and v == 0:
        return T("unlimited")
    if isinstance(v, str) and not v:
        return T("empty")
    return str(v)

def pick_from(title, labels, current_index):
    print(c(f"\n{title}:", CYAN))
    for i, lb in enumerate(labels, 1):
        print(f"  {i}. {lb}{' [*]' if i - 1 == current_index else ''}")
    try:
        idx = int(input(c(f"{T('choice')}: ", YELLOW)).strip()) - 1
    except (ValueError, EOFError, KeyboardInterrupt):
        return None
    return idx if 0 <= idx < len(labels) else None

def edit_setting(key):
    if key == "language":
        language_menu()
        return
    title = T("set_" + key)
    v = SETTINGS[key]
    if key in ("video_codec", "audio_codec"):
        table = VIDEO_CODECS if key == "video_codec" else AUDIO_CODECS
        keys = list(table.keys())
        idx = pick_from(title, [T(table[k]["label_key"]) for k in keys], keys.index(v))
        if idx is None:
            return
        enc = table[keys[idx]].get("encoder")
        if not encoder_ok(enc):
            err_line(T("encoder_missing"))
            return
        SETTINGS[key] = keys[idx]
    elif isinstance(v, bool):
        SETTINGS[key] = not v
    elif key in CHOICES:
        keys = list(CHOICES[key])
        idx = pick_from(title, [T("opt_" + k) for k in keys], keys.index(v))
        if idx is None:
            return
        SETTINGS[key] = keys[idx]
    elif isinstance(v, int):
        try:
            raw = input(c(f"{title} [{v}]: ", YELLOW)).strip()
        except (EOFError, KeyboardInterrupt):
            return
        if not raw:
            return
        lo, hi = INT_LIMITS.get(key, (0, 10 ** 9))
        if not raw.isdigit() or not lo <= int(raw) <= hi:
            err_line(f"{T('set_bad_value')} ({lo}-{hi})")
            return
        SETTINGS[key] = int(raw)
    else:
        try:
            raw = input(c(f"{title} [{v or T('empty')}]\n{T('set_enter_value')}: ", YELLOW)).strip()
        except (EOFError, KeyboardInterrupt):
            return
        if not raw:
            return
        if raw == "-":
            raw = ""
        if key == "proxy" and raw and not re.match(r"^(https?|socks4a?|socks5h?)://\S+$", raw, re.I):
            err_line(T("proxy_invalid"))
            return
        SETTINGS[key] = raw
    save_settings(SETTINGS)
    if key == "base_dir":
        ensure_dir()
    if key in ("proxy", "dns_mode", "dns_servers", "doh_url", "ipv4_only", "verify_tls"):
        reset_dns()
    ok_line(T("set_saved"))

def settings_group_menu(group_key, keys):
    while True:
        header(T(group_key))
        for i, k in enumerate(keys, 1):
            print(f"  {i}. {T('set_' + k)}: {setting_display(k)}")
        print(f"  0. {T('fm_back')}")
        try:
            ch = input(c(f"{T('choice')}: ", GREEN)).strip().lower()
        except (EOFError, KeyboardInterrupt):
            return
        if ch in ("0", "q"):
            return
        if ch.isdigit() and 1 <= int(ch) <= len(keys):
            edit_setting(keys[int(ch) - 1])
        else:
            err_line(T("invalid_choice"))

def settings_menu():
    global SETTINGS
    while True:
        header(T("settings_title"))
        for i, (gk, _) in enumerate(GROUPS, 1):
            print(f"  {i}. {T(gk)}")
        print(f"  {len(GROUPS) + 1}. {T('set_reset')}\n  0. {T('fm_back')}")
        try:
            ch = input(c(f"{T('choice')}: ", GREEN)).strip().lower()
        except (EOFError, KeyboardInterrupt):
            return
        if ch in ("0", "q"):
            return
        if ch.isdigit() and 1 <= int(ch) <= len(GROUPS):
            gk, keys = GROUPS[int(ch) - 1]
            settings_group_menu(gk, keys)
        elif ch == str(len(GROUPS) + 1):
            SETTINGS.clear()
            SETTINGS.update(DEFAULT_SETTINGS)
            save_settings(SETTINGS)
            reset_dns()
            ensure_dir()
            ok_line(T("set_saved"))
        else:
            err_line(T("invalid_choice"))

def pip_run(args):
    cmd = [sys.executable, SCRIPT_PATH, "--pip"] + args
    env = dict(os.environ, VD_DNS_ORDER=",".join(dns_order()), PYTHONUTF8="1")
    base = ["install", "-U", "--no-deps", "--disable-pip-version-check"]
    for extra in ([], ["--break-system-packages"]):
        try:
            r = subprocess.run(cmd[:3] + base + extra + args, env=env)
        except Exception as e:
            err_line(f"{type(e).__name__}: {e}")
            return False
        if r.returncode == 0:
            return True
    return False

def install_ejs():
    spec = "yt-dlp-ejs"
    try:
        r = subprocess.run([sys.executable, "-c",
                            "import importlib.metadata as m;print(chr(10).join(m.requires('yt-dlp') or []))"],
                           capture_output=True, text=True, timeout=60)
        for line in r.stdout.splitlines():
            if line.strip().startswith("yt-dlp-ejs"):
                spec = line.split(";")[0].strip()
                break
    except Exception as e:
        warn_line(f"{type(e).__name__}: {e}")
    return pip_run([spec])

def ensure_ejs():
    if yt_dlp is None or has_ejs() or EJS_MARK.exists():
        return
    info_line(T("ejs_installing"))
    ok = install_ejs()
    try:
        EJS_MARK.write_text("1")
    except OSError:
        pass
    if not ok:
        warn_line(T("ejs_failed"))

def restart():
    os.execv(sys.executable, [sys.executable, SCRIPT_PATH])

def update_menu():
    header(T("upd_title"))
    print(f"  1. {T('upd_stable')}\n  2. {T('upd_nightly')}\n  3. {T('upd_ejs')}\n  0. {T('fm_back')}")
    try:
        ch = input(c(f"{T('choice')}: ", GREEN)).strip().lower()
    except (EOFError, KeyboardInterrupt):
        return
    if ch not in ("1", "2", "3"):
        return
    ok = True
    if ch in ("1", "2"):
        ok = pip_run((["--pre"] if ch == "2" else []) + ["yt-dlp", "tqdm"])
    if ok:
        try:
            EJS_MARK.unlink()
        except OSError:
            pass
        ok = install_ejs()
    if ok:
        ok_line(T("upd_done"))
        restart()
    else:
        err_line(T("upd_failed"))

def diag_hosts():
    return ["rutube.ru", "www.youtube.com", "i.ytimg.com", "redirector.googlevideo.com", "www.google.com"]

def diagnostics():
    header(T("diag_title"))
    print(c(T("diag_env"), CYAN))
    print(f"  python {sys.version.split()[0]}")
    print(f"  yt-dlp {getattr(getattr(yt_dlp, 'version', None), '__version__', T('ytdlp_missing'))}")
    print(f"  yt-dlp-ejs: {T('on') if has_ejs() else T('off')}")
    print(f"  ffmpeg: {shutil.which('ffmpeg') or T('ffmpeg_missing')}")
    print(f"  JS: {js_runtime() or T('js_none')}")
    print(f"  proxy: {SETTINGS['proxy'] or T('empty')}")
    print(f"  DNS: {','.join(dns_order())}")
    for host in diag_hosts():
        print(c(f"\n{host}", CYAN))
        answers = {}
        ips = resolve_with("system", host)
        answers["system"] = ips
        print(f"  {T('diag_system')}: {', '.join(ips) if ips else T('diag_fail')}")
        for srv in dns_servers():
            ips, err = udp_query(srv, host)
            answers["udp " + srv] = ips
            print(f"  udp {srv}: {', '.join(ips) if ips else (err or T('diag_fail'))}")
        DNS_STATE["busy"] = True
        try:
            for u in doh_urls():
                try:
                    ips = doh_query(u, host)
                    err = ""
                except Exception as e:
                    ips, err = [], f"{type(e).__name__}: {e}"
                answers["doh " + u] = ips
                print(f"  doh {u}: {', '.join(ips) if ips else (err or T('diag_fail'))}")
        finally:
            DNS_STATE["busy"] = False
        sets = {tuple(sorted(v)) for v in answers.values() if v}
        if len(sets) > 1:
            warn_line(T("diag_mismatch"))
        candidates = [ip for v in answers.values() for ip in v]
        if candidates:
            ok, err = tls_probe(host, candidates[0], timeout=10)
            if ok:
                ok_line(f"{T('diag_tls_ok')} ({candidates[0]})")
            else:
                err_line(f"{T('diag_tls_fail')} ({candidates[0]}): {err}")
    px = SETTINGS["proxy"]
    if px:
        print(c(f"\n{T('diag_proxy')}: {px}", CYAN))
        if px.split("://")[0].lower() in ("http", "https"):
            try:
                req = urllib.request.Request("https://www.youtube.com/generate_204", headers={"User-Agent": UA})
                with make_opener().open(req, timeout=20) as r:
                    ok_line(f"HTTP {r.status}")
            except Exception as e:
                err_line(f"{type(e).__name__}: {e}")
        else:
            warn_line(T("diag_proxy_socks"))
    try:
        input(c(f"\n{T('diag_press')}", YELLOW))
    except (EOFError, KeyboardInterrupt):
        pass

def main_menu():
    ensure_dir()
    while True:
        cleanup_junk()
        header(T("app_title"))
        print(c(f"{T('videos_dir')}: {VIDEOS_DIR}", CYAN))
        print(c(f"{T('audio_dir')}: {AUDIO_DIR}", CYAN))
        print("-" * 40)
        print(f"  1. {T('menu_download_video')}\n  2. {T('menu_download_audio')}\n  3. {T('menu_files')}")
        print(f"  4. {T('menu_settings')}\n  5. {T('menu_diag')}\n  6. {T('menu_update')}\n  0. {T('menu_exit')}")
        try:
            ch = input(c(f"{T('choice')}: ", GREEN)).strip().lower()
        except (EOFError, KeyboardInterrupt):
            print(c(f"\n[+] {T('stopped')}", GREEN))
            break
        if ch in ("0", "q", "quit", "exit"):
            ok_line(T("menu_exit"))
            break
        if ch == "3":
            file_manager()
        elif ch == "4":
            settings_menu()
        elif ch == "5":
            diagnostics()
        elif ch == "6":
            update_menu()
        elif ch in ("1", "2"):
            links = []
            info_line(T("enter_urls"))
            info_line(T("enter_urls_hint"))
            while True:
                try:
                    line = input(c("> ", GREEN)).strip()
                except (EOFError, KeyboardInterrupt):
                    break
                if not line or line.lower() == "q":
                    break
                links.append(line)
            if links:
                process_links(links, audio_only=(ch == "2"))
                print()
        else:
            err_line(T("invalid_choice"))

def main():
    argv = sys.argv[1:]
    order = os.environ.get("VD_DNS_ORDER")
    if order:
        parsed = [x for x in order.split(",") if x in ("system", "udp", "doh")]
        DNS_STATE["order"] = parsed or None
    if argv and argv[0] == "--ytdlp":
        if yt_dlp is None:
            sys.exit(1)
        yt_dlp.main(argv[1:])
        return
    if argv and argv[0] == "--pip":
        import runpy
        sys.argv = ["pip"] + argv[1:]
        runpy.run_module("pip", run_name="__main__", alter_sys=True)
        return
    ensure_dir()
    ensure_ejs()
    main_menu()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(c(f"\n[+] {T('stopped')}", GREEN))
PYEOF

chmod 700 /tmp/video_downloader.py
python3 /tmp/video_downloader.py
CODE=$?
if [ -n "$KA_PID" ]; then kill "$KA_PID" 2>/dev/null; fi
exit $CODE
