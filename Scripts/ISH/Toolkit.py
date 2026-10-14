#!/bin/sh

# ========================================
#  Shadowrocket Toolkit (iSH)
# ========================================

# --- Инициализация ---
clear
BASE="$HOME/Shadowrocket"
LANG_FILE="$HOME/.sr_toolkit_lang"
TK_VERSION="3"
VERSION_FILE="$BASE/.toolkit_version"

# --- Выбор языка (только при первом запуске или если LANG_FILE отсутствует) ---
if [ ! -f "$LANG_FILE" ]; then
    echo "========================================"
    echo "  Language / Язык"
    echo "========================================"
    echo "  1 - Русский [по умолчанию]"
    echo "  2 - English"
    printf '%s' "Выбор / Choice [1]: "
    IFS= read -r LC
    if [ "$LC" = "2" ]; then LANG_SEL="en"; else LANG_SEL="ru"; fi
    echo "$LANG_SEL" > "$LANG_FILE"
else
    LANG_SEL="$(cat "$LANG_FILE" 2>/dev/null)"
    if [ "$LANG_SEL" != "en" ] && [ "$LANG_SEL" != "ru" ]; then LANG_SEL="ru"; fi
fi
export LANG_SEL

# --- Функция перевода ---
T() {
    if [ "$LANG_SEL" = "en" ]; then
        case "$1" in
            update_sys) echo "Update system and install dependencies?" ;;
            update_script) echo "Update Toolkit script from GitHub?" ;;
            delete_files) echo "Delete all Toolkit data folders?" ;;
            dl_script) echo "[*] Downloading script..." ;;
            script_ok) echo "[+] Script updated. Re-running..." ;;
            dns) echo "[*] Setting DNS..." ;;
            net_check) echo "[*] Checking connection..." ;;
            net_retry) echo "[!] No connection. Retry in 5 sec..." ;;
            net_ok) echo "[+] Internet available." ;;
            sys_upd) echo "[*] Updating system..." ;;
            deps) echo "[*] Installing dependencies..." ;;
            mkdirs) echo "[*] Preparing folders..." ;;
            mk_scripts) echo "[*] Creating scripts..." ;;
            m_title) echo "Shadowrocket Toolkit (iSH)" ;;
            m_ad) echo "  1 - AdBlock           Ad/tracker blocklist generator" ;;
            m_sql) echo "  2 - SQLiteTXT         SQLite to text viewer" ;;
            m_spy) echo "  3 - SpyLog            Shadowrocket log analyzer" ;;
            m_sub) echo "  4 - SubManager        Subscriptions and JSON Xray" ;;
            m_rx)  echo "  5 - RegexBuilder      Interactive regex constructor" ;;
            m_def) echo "  6 - GetDefaultConfig  Download default configuration" ;;
            m_q) echo "  q - Quit" ;;
            choice) echo "Choice" ;;
            bad) echo "Invalid choice." ;;
            press) echo "Press Enter to return to menu..." ;;
            fail) echo "Download failed." ;;
            dl_try) echo "[*] Trying download method" ;;
            dl_ok) echo "[+] Downloaded successfully" ;;
            net_timeout) echo "[!] Network unavailable. Continuing offline." ;;
        esac
    else
        case "$1" in
            update_sys) echo "Обновить систему и установить зависимости?" ;;
            update_script) echo "Обновить сам скрипт Toolkit из GitHub?" ;;
            delete_files) echo "Удалить все папки с данными Toolkit?" ;;
            dl_script) echo "[*] Скачивание скрипта..." ;;
            script_ok) echo "[+] Скрипт обновлён. Перезапуск..." ;;
            dns) echo "[*] Настройка DNS..." ;;
            net_check) echo "[*] Проверка соединения..." ;;
            net_retry) echo "[!] Нет подключения. Повтор через 5 сек..." ;;
            net_ok) echo "[+] Интернет доступен." ;;
            sys_upd) echo "[*] Обновление системы..." ;;
            deps) echo "[*] Установка зависимостей..." ;;
            mkdirs) echo "[*] Подготовка папок..." ;;
            mk_scripts) echo "[*] Создание скриптов..." ;;
            m_title) echo "Shadowrocket Toolkit (iSH)" ;;
            m_ad) echo "  1 - AdBlock           Генератор блок-листов" ;;
            m_sql) echo "  2 - SQLiteTXT         Просмотр SQLite в тексте" ;;
            m_spy) echo "  3 - SpyLog            Анализ журналов Shadowrocket" ;;
            m_sub) echo "  4 - SubManager        Подписки и JSON Xray" ;;
            m_rx)  echo "  5 - RegexBuilder      Конструктор регулярных выражений" ;;
            m_def) echo "  6 - GetDefaultConfig  Скачать дефолтную конфигурацию" ;;
            m_q) echo "  q - Выход" ;;
            choice) echo "Ваш выбор" ;;
            bad) echo "Неверный выбор." ;;
            press) echo "Нажмите Enter для возврата в меню..." ;;
            fail) echo "Не удалось скачать." ;;
            dl_try) echo "[*] Попытка метода" ;;
            dl_ok) echo "[+] Успешно скачано" ;;
            net_timeout) echo "[!] Сеть недоступна. Продолжаем без сети." ;;
        esac
    fi
}

# --- Фоновая привязка геолокации iSH ---
if [ -e /dev/location ]; then
    ( cat /dev/location > /dev/null 2>&1 ) &
fi

# ========================================
#  Утилиты: DNS, скачивание несколькими способами
# ========================================

# --- Настройка DNS ---
setup_dns() {
    cat > /etc/resolv.conf << 'DNS_EOF'
nameserver 8.8.8.8
nameserver 8.8.4.4
nameserver 94.140.14.14
nameserver 94.140.15.15
nameserver 1.1.1.1
DNS_EOF
}

# --- Универсальное скачивание: curl -> wget -> aria2c -> python3 urllib ---
try_download() {
    _url="$1"
    _out="$2"
    rm -f "$_out"

    if command -v curl >/dev/null 2>&1; then
        echo "$(T dl_try): curl"
        curl -fsSL --connect-timeout 15 --max-time 60 -A "Mozilla/5.0" "$_url" -o "$_out" 2>/dev/null
        if [ -s "$_out" ]; then echo "$(T dl_ok): curl"; return 0; fi
    fi

    if command -v wget >/dev/null 2>&1; then
        echo "$(T dl_try): wget"
        wget -q --no-check-certificate -U "Mozilla/5.0" -O "$_out" "$_url" 2>/dev/null
        if [ -s "$_out" ]; then echo "$(T dl_ok): wget"; return 0; fi
    fi

    if command -v aria2c >/dev/null 2>&1; then
        echo "$(T dl_try): aria2c"
        aria2c -q --check-certificate=false -U "Mozilla/5.0" \
            -d "$(dirname "$_out")" -o "$(basename "$_out")" "$_url" 2>/dev/null
        if [ -s "$_out" ]; then echo "$(T dl_ok): aria2c"; return 0; fi
    fi

    if command -v python3 >/dev/null 2>&1; then
        echo "$(T dl_try): python3"
        python3 - "$_url" "$_out" << 'PYEOF' 2>/dev/null
import sys, urllib.request, ssl
url, out = sys.argv[1], sys.argv[2]
ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE
req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
with urllib.request.urlopen(req, context=ctx, timeout=30) as r, open(out, 'wb') as f:
    f.write(r.read())
PYEOF
        if [ -s "$_out" ]; then echo "$(T dl_ok): python3"; return 0; fi
    fi

    return 1
}

# ========================================
#  Вопросы: обновление системы / скрипта
# ========================================

echo ""
echo "========================================"
echo "  $(T update_sys)"
echo "========================================"
printf '%s' "[y/N]: "
IFS= read -r U1
case "$U1" in y|Y|yes|Yes|YES) DO_UPDATE=1 ;; *) DO_UPDATE=0 ;; esac

echo ""
echo "========================================"
echo "  $(T update_script)"
echo "========================================"
printf '%s' "[y/N]: "
IFS= read -r U2
case "$U2" in y|Y|yes|Yes|YES) DO_SCRIPT=1 ;; *) DO_SCRIPT=0 ;; esac

# ========================================
#  Обновление самого скрипта Toolkit
# ========================================

if [ "$DO_SCRIPT" = "1" ]; then
    echo ""
    echo "========================================"
    echo "  $(T delete_files)"
    echo "========================================"
    printf '%s' "[y/N]: "
    IFS= read -r U3
    case "$U3" in y|Y|yes|Yes|YES) rm -rf "$BASE" ;; esac

    # --- Настройка DNS перед скачиванием (иначе iSH не резолвит github) ---
    echo "$(T dns)"
    setup_dns

    # --- Скачивание новой версии скрипта несколькими способами ---
    echo "$(T dl_script)"
    SCRIPT_URL="https://raw.githubusercontent.com/Krest-Neva/Shadowrocket/refs/heads/main/Scripts/ISH/Toolkit.py"
    NEW_SCRIPT="$HOME/Toolkit.sh"
    DL_OK=0
    for attempt in 1 2 3; do
        if try_download "$SCRIPT_URL" "$NEW_SCRIPT"; then
            DL_OK=1
            break
        fi
        echo "$(T net_retry) [$attempt/3]"
        sleep 3
    done

    # --- Проверка содержимого: это shell-скрипт, не HTML-ошибка ---
    if [ "$DL_OK" = "1" ] && head -c 20 "$NEW_SCRIPT" | grep -q '^#!'; then
        echo "$(T script_ok)"
        exec sh "$NEW_SCRIPT"
    else
        echo "$(T fail)"
    fi
fi

# ========================================
#  Обновление системы и установка зависимостей
# ========================================

if [ "$DO_UPDATE" = "1" ]; then
    echo "$(T dns)"
    setup_dns

    echo "$(T net_check)"
    tries=0
    while ! ping -c 3 1.1.1.1 > /dev/null 2>&1; do
        tries=$((tries + 1))
        if [ "$tries" -ge 12 ]; then
            echo "$(T net_timeout)"
            break
        fi
        echo "$(T net_retry) [$tries/12]"
        sleep 5
    done
    echo "$(T net_ok)"

    echo "$(T sys_upd)"
    apk update
    apk upgrade

    echo "$(T deps)"
    apk add --no-cache \
        python3 py3-pip curl wget aria2 openssl ca-certificates \
        bind-tools bash sqlite git py3-chardet || echo "[!] Some dependencies failed"
fi

# ========================================
#  Создание структуры папок
# ========================================

echo "$(T mkdirs)"
mkdir -p "$BASE" \
    "$BASE/AdBlock" \
    "$BASE/SQLiteTXT/Input" "$BASE/SQLiteTXT/Output" \
    "$BASE/SpyLog/Input" "$BASE/SpyLog/Output" \
    "$BASE/SubManager/Input" "$BASE/SubManager/Output" \
    "$BASE/SubManager/Backups" "$BASE/SubManager/Routing" \
    "$BASE/RegexBuilder/Output" "$BASE/RegexBuilder/Backups" \
    "$BASE/Configurations"

# --- Проверка версии для перегенерации python-скриптов ---
REGEN_PY=0
if [ ! -f "$VERSION_FILE" ] || [ "$(cat "$VERSION_FILE" 2>/dev/null)" != "$TK_VERSION" ]; then
    REGEN_PY=1
fi

echo "$(T mk_scripts)"

# ========================================
#  Скрипт 1/5: AdBlock.py
# ========================================
if [ "$REGEN_PY" = "1" ] || [ ! -s "$BASE/AdBlock.py" ]; then
cat << 'ADBLOCK_END' > "$BASE/AdBlock.py"
# ========================================
#  AdBlock: генератор блок-листов
# ========================================

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

os.umask(0o077)

# --- Загрузка языка ---
LANG = os.environ.get("LANG_SEL", "").strip()
if not LANG:
    try:
        with open(os.path.expanduser("~/.sr_toolkit_lang")) as _f:
            LANG = _f.read().strip()
    except Exception:
        LANG = "ru"
if LANG not in ("ru", "en"):
    LANG = "ru"

# --- Словарь переводов ---
_T = {
"ru": {
 "exit": "Выход.",
 "mode_hdr": "ADBLOCK: выбор режима",
 "mode_1": "1 - По умолчанию",
 "mode_2": "2 - Custom",
 "choice": "Ваш выбор",
 "oid_hdr": "Настройка списков OISD",
 "oid_1": "1 - Обычные",
 "oid_2": "2 - Короткие",
 "oid_3": "3 - Скачать все",
 "chosen": "Выбрано",
 "confirm": "Подтвердить? (y/n)",
 "custom_wd": "CUSTOM: белые домены",
 "custom_ws": "CUSTOM: белые суффиксы",
 "custom_bd": "CUSTOM: чёрные домены",
 "custom_bs": "CUSTOM: чёрные суффиксы",
 "custom_list_hint": "Введите значения через запятую (Enter — пропустить):",
 "custom_val": "Значение",
 "custom_black_urls": "CUSTOM: чёрные списки (URL)",
 "custom_white_urls": "CUSTOM: белые списки (URL)",
 "custom_name": "Имя списка",
 "custom_name_end": "пустое имя — конец ввода",
 "custom_url": "URL",
 "custom_url_end": "пустой ввод — конец списка URL",
 "custom_clean": "Очищать белыми списками? (y/n)",
 "custom_no_bl": "Ни одного чёрного списка не задано.",
 "split_hdr": "Разбивать итоговые списки по 100000 строк?",
 "split_1": "1 - Да",
 "split_2": "2 - Нет (целые списки)",
 "split_on": "Разбиение включено",
 "split_off": "Целые списки",
 "e1w": "ЭТАП 1: ЗАГРУЗКА БЕЛЫХ СПИСКОВ",
 "e1b": "ЭТАП 1: ЗАГРУЗКА ЧЁРНЫХ СПИСКОВ",
 "e2": "ЭТАП 2: ПОВТОРНАЯ ЗАГРУЗКА ОШИБОК",
 "e3": "ЭТАП 3: ОБРАБОТКА БЕЛЫХ СПИСКОВ",
 "e4": "ЭТАП 4: ОБРАБОТКА ЧЁРНЫХ СПИСКОВ",
 "e5": "ЭТАП 5: ОЧИСТКА И ФОРМИРОВАНИЕ RULE-SET",
 "dl": "Скачивание",
 "dl_ok": "Успешно загружено строк",
 "dl_attempt": "попытка не удалась, повтор через",
 "dl_err": "Ошибка: не удалось скачать",
 "dl_err_any": "ни одним из способов",
 "net_setup": "Настройка DNS",
 "net_ok": "Интернет доступен",
 "net_fail": "Ping не прошёл",
 "net_err": "Ошибка проверки сети",
 "need_retry": "ВНИМАНИЕ: некоторые списки не удалось скачать",
 "wlist": "Белый",
 "blist": "Черный",
 "retry_q": "Хотите попытаться скачать снова?",
 "retry_1": "1 - Да",
 "retry_2": "2 - Нет",
 "retry_3": "3 - Вручную",
 "retry_manual": "Введите полную ссылку",
 "retry_ok": "Успешно скачано. Файл добавлен в очередь",
 "retry_fail": "Загрузка снова не удалась",
 "parsing": "Парсинг",
 "extracted": "Извлечено доменов",
 "opt_std": "Оптимизация стандартного списка",
 "opt_plus": "Оптимизация расширенного списка",
 "opt_sm": "Оптимизация малого списка",
 "opt_plus_sm": "Оптимизация малого расширенного списка",
 "writing": "Формирование и запись файлов",
 "done": "ГОТОВО! Файлы успешно сохранены",
 "u_std": "Уникальных доменов (Std/Plus)",
 "u_sm": "Уникальных доменов (Sm/PlusSm)",
 "u_ip": "Уникальных IP-адресов",
 "rm_kw": "Удалено по ключевым словам",
 "junk": "Отсеяно ошибочно добавленных",
 "prot_e": "Защищено (exact)",
 "prot_s": "Защищено (suffix)",
 "r_std": "ПРАВИЛ В ФАЙЛАХ STD",
 "r_plus": "ПРАВИЛ В ФАЙЛАХ PLUS",
 "r_sm": "ПРАВИЛ В ФАЙЛАХ STD SMALL",
 "r_plus_sm": "ПРАВИЛ В ФАЙЛАХ PLUS SMALL",
 "total_drop": "ВСЕГО ОТБРОШЕНО СТРОК",
 "total_time": "ОБЩЕЕ ВРЕМЯ ВЫПОЛНЕНИЯ",
 "sec": "сек",
 "sum_bl": "Download summary (blacklists)",
 "sum_wl": "Download summary (whitelists)",
 "skipped": "Some lists were skipped intentionally.",
 "all_ok": "All lists processed successfully.",
 "y_or_n": "y/n"
},
"en": {
 "exit": "Exit.",
 "mode_hdr": "ADBLOCK: choose mode",
 "mode_1": "1 - Default",
 "mode_2": "2 - Custom",
 "choice": "Your choice",
 "oid_hdr": "OISD list configuration",
 "oid_1": "1 - Normal",
 "oid_2": "2 - Small",
 "oid_3": "3 - Download all",
 "chosen": "Chosen",
 "confirm": "Confirm? (y/n)",
 "custom_wd": "CUSTOM: white domains",
 "custom_ws": "CUSTOM: white suffixes",
 "custom_bd": "CUSTOM: black domains",
 "custom_bs": "CUSTOM: black suffixes",
 "custom_list_hint": "Enter comma-separated (Enter — skip):",
 "custom_val": "Value",
 "custom_black_urls": "CUSTOM: black lists (URLs)",
 "custom_white_urls": "CUSTOM: white lists (URLs)",
 "custom_name": "List name",
 "custom_name_end": "empty name — finish",
 "custom_url": "URL",
 "custom_url_end": "empty input — finish URL list",
 "custom_clean": "Clean with whitelists? (y/n)",
 "custom_no_bl": "No black lists provided.",
 "split_hdr": "Split output lists by 100000 lines?",
 "split_1": "1 - Yes",
 "split_2": "2 - No (whole lists)",
 "split_on": "Splitting enabled",
 "split_off": "Whole lists",
 "e1w": "STAGE 1: WHITELIST DOWNLOAD",
 "e1b": "STAGE 1: BLACKLIST DOWNLOAD",
 "e2": "STAGE 2: RETRY FAILED DOWNLOADS",
 "e3": "STAGE 3: PROCESSING WHITELISTS",
 "e4": "STAGE 4: PROCESSING BLACKLISTS",
 "e5": "STAGE 5: SUBDOMAIN CLEANUP AND RULE-SET BUILD",
 "dl": "Downloading",
 "dl_ok": "Successfully downloaded lines",
 "dl_attempt": "attempt failed, retry in",
 "dl_err": "Error: failed to download",
 "dl_err_any": "by any method",
 "net_setup": "Setting DNS",
 "net_ok": "Internet available",
 "net_fail": "Ping failed",
 "net_err": "Network check error",
 "need_retry": "WARNING: some lists failed to download",
 "wlist": "White",
 "blist": "Black",
 "retry_q": "Try to download again?",
 "retry_1": "1 - Yes",
 "retry_2": "2 - No",
 "retry_3": "3 - Manually",
 "retry_manual": "Enter full URL",
 "retry_ok": "Successfully downloaded. Added to queue",
 "retry_fail": "Download failed again",
 "parsing": "Parsing",
 "extracted": "Extracted domains",
 "opt_std": "Optimizing standard list",
 "opt_plus": "Optimizing extended list",
 "opt_sm": "Optimizing small list",
 "opt_plus_sm": "Optimizing small extended list",
 "writing": "Building and writing files",
 "done": "DONE! Files successfully saved",
 "u_std": "Unique domains (Std/Plus)",
 "u_sm": "Unique domains (Sm/PlusSm)",
 "u_ip": "Unique IP addresses",
 "rm_kw": "Removed by keywords",
 "junk": "Filtered invalid entries",
 "prot_e": "Protected (exact)",
 "prot_s": "Protected (suffix)",
 "r_std": "RULES IN STD FILES",
 "r_plus": "RULES IN PLUS FILES",
 "r_sm": "RULES IN STD SMALL FILES",
 "r_plus_sm": "RULES IN PLUS SMALL FILES",
 "total_drop": "TOTAL DROPPED LINES",
 "total_time": "TOTAL EXECUTION TIME",
 "sec": "sec",
 "sum_bl": "Download summary (blacklists)",
 "sum_wl": "Download summary (whitelists)",
 "skipped": "Some lists were skipped intentionally.",
 "all_ok": "All lists processed successfully.",
 "y_or_n": "y/n"
}}

def tr(k):
    return _T.get(LANG, _T["ru"]).get(k, _T["ru"].get(k, k))

# --- Безопасный ввод с поддержкой q/exit ---
def _input(prompt=""):
    try:
        v = input(prompt)
    except (EOFError, KeyboardInterrupt):
        print()
        sys.exit(0)
    if v.strip().lower() in ("q", "quit", "exit"):
        print("[+] " + tr("exit"))
        sys.exit(0)
    return v

def _inp_allow_empty(prompt=""):
    try:
        v = input(prompt)
    except (EOFError, KeyboardInterrupt):
        print()
        sys.exit(0)
    if v.strip().lower() in ("q", "quit", "exit"):
        print("[+] " + tr("exit"))
        sys.exit(0)
    return v

# --- Выбор режима ---
def choose_mode():
    print("\n" + "="*40)
    print(tr("mode_hdr"))
    print("  " + tr("mode_1"))
    print("  " + tr("mode_2"))
    v = _input(f"{tr('choice')} [1]: ").strip()
    return "custom" if v == "2" else "default"

MODE = choose_mode()

# --- Выбор OISD ---
oisd_choice = '3'
if MODE == "default":
    while True:
        print("\n" + "="*40)
        print(tr("oid_hdr"))
        print(tr("oid_1"))
        print(tr("oid_2"))
        print(tr("oid_3"))
        v = _input(f"{tr('choice')} [3]: ").strip()
        oisd_choice = v if v in ('1', '2', '3') else '3'
        label = {'1': tr("oid_1")[4:], '2': tr("oid_2")[4:], '3': tr("oid_3")[4:]}[oisd_choice]
        print(f" -> {tr('chosen')}: {label}")
        c = _input(f"{tr('confirm')} [y]: ").strip().lower()
        if c in ('y', 'yes', ''):
            break

# --- URL-ы списков ---
oisd_main_url = "https://dl.oisd.nl/oisd_big_surge.list"
oisd_nsfw_url = "https://dl.oisd.nl/oisd_nsfw_surge.list"
oisd_small_url = "https://dl.oisd.nl/oisd_small_surge.list"
oisd_nsfw_small_url = "https://dl.oisd.nl/oisd_nsfw_small_surge.list"
print("="*40 + "\n")

SCRIPT_START_TIME = time.time()

urls = {}
white_urls = {}
whitelist_clean = {}

protected_suffixes = set()
protected_domains = set()
forced_block_suffixes = set()
forced_block_domains = set()

# --- Настройка: режим по умолчанию ---
if MODE == "default":
    urls = {
        "1) Loyalsoldier": [
            "https://raw.githubusercontent.com/Loyalsoldier/surge-rules/release/ruleset/reject.txt",
            "https://cdn.jsdelivr.net/gh/Loyalsoldier/surge-rules@release/ruleset/reject.txt",
            "https://raw.githubusercontent.com/Loyalsoldier/surge-rules/release/reject.txt",
            "https://cdn.jsdelivr.net/gh/Loyalsoldier/surge-rules@release/reject.txt"
        ],
        "2) AdGuard (Base)": "https://filters.adtidy.org/ios/filters/15_optimized.txt",
        "3) AdGuard 1": "https://filters.adtidy.org/ios/filters/2_optimized.txt",
        "4) AdGuard 2": "https://filters.adtidy.org/ios/filters/3_optimized.txt",
        "5) AdGuard 3.1": "https://pgl.yoyo.org/adservers/serverlist.php?hostformat=adblockplus&showintro=0&mimetype=plaintext",
        "6) Mobile ads": "https://filters.adtidy.org/ios/filters/11_optimized.txt",
        "7) RU filter": "https://filters.adtidy.org/ios/filters/1_optimized.txt",
        "8) Trackers": [
            "https://easylist-downloads.adblockplus.org/cntblock.txt",
            "https://raw.githubusercontent.com/easylist/easylist/master/easyprivacy/easyprivacy_trackers.txt"
        ],
        "9) Anti-phishing": "https://malware-filter.gitlab.io/malware-filter/phishing-filter-ag.txt"
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
        "Direct": [
            "https://raw.githubusercontent.com/Loyalsoldier/surge-rules/release/ruleset/direct.txt",
            "https://cdn.jsdelivr.net/gh/Loyalsoldier/surge-rules@release/ruleset/direct.txt"
        ],
        "Proxy": [
            "https://raw.githubusercontent.com/Loyalsoldier/surge-rules/release/ruleset/proxy.txt",
            "https://cdn.jsdelivr.net/gh/Loyalsoldier/surge-rules@release/ruleset/proxy.txt"
        ],
        "Apple": [
            "https://raw.githubusercontent.com/Loyalsoldier/surge-rules/release/ruleset/apple.txt",
            "https://cdn.jsdelivr.net/gh/Loyalsoldier/surge-rules@release/ruleset/apple.txt"
        ],
        "iCloud": [
            "https://raw.githubusercontent.com/Loyalsoldier/surge-rules/release/ruleset/icloud.txt",
            "https://cdn.jsdelivr.net/gh/Loyalsoldier/surge-rules@release/ruleset/icloud.txt"
        ],
        "AnudeepND": [
            "https://raw.githubusercontent.com/anudeepND/whitelist/master/domains/whitelist.txt",
            "https://cdn.jsdelivr.net/gh/anudeepND/whitelist@master/domains/whitelist.txt"
        ],
        "RU mobile": [
            "https://cdn.jsdelivr.net/gh/hxehex/russia-mobile-internet-whitelist@main/whitelist.txt",
            "https://raw.githubusercontent.com/hxehex/russia-mobile-internet-whitelist/main/whitelist.txt"
        ],
        "Other 1": "https://raw.githubusercontent.com/chebur-net/russia-mobile-whitelist/refs/heads/main/moscow-tele2/domains.txt",
        "Other 2": "https://raw.githubusercontent.com/chebur-net/russia-mobile-whitelist/refs/heads/main/spb-tele2/domains.txt"
    }
    protected_suffixes = {
        "apple-pki.com","icloud.com","icloud-content.com","mzstatic.com","push.apple.com","appleid.apple.com",
        "simplex.im","simplexonflux.com","telegram.org","t.me","telegram.me","telegra.ph","tg.dev","cdn.telegram-cdn.org",
        "whatsapp.com","whatsapp.net","wa.me","youtube.com","youtu.be","ytimg.com","googlevideo.com",
        "youtube.googleapis.com","ls-apple.com.akadns.net","ess-apple.com.akadns.net"
    }
    protected_domains = {
        "raw.githubusercontent.com","cdn-apple.com","apple-dns.net","ls.apple.com","facetime.apple.com","stun.apple.com",
        "apple.com","aaplimg.com","github.com","githubusercontent.com","githubassets.com","google.com","gstatic.com",
        "ggpht.com","firebase.google.com","googleapis.com","firebaseio.com","openai.com","chatgpt.com","oaistatic.com",
        "oaiusercontent.com","microsoft.com","windows.com","windowsupdate.com","msftconnecttest.com","msftncsi.com",
        "azure.com","azureedge.net","azurefd.net","amazon.com","amazonaws.com","aws.amazon.com","cloudfront.net",
        "cloudflare.com","fastly.net","cdn.jsdelivr.net","unpkg.com","akamaiedge.net","akamaized.net","akamai.net",
        "auth0.com","okta.com","login.microsoftonline.com","accounts.google.com","hcaptcha.com","challenges.cloudflare.com",
        "recaptcha.net","facebook.com","fb.com","fbcdn.net","graph.instagram.com","graph.facebook.com","instagram.com",
        "cdninstagram.com","discord.com","discordapp.com","duckduckgo.com","ddg.co","giphy.com","habr.com","yandex.ru",
        "yandex.com","yandex.by","yandex.kz","mail.yandex.ru","passport.yandex.ru","api.yandex.ru","mail.ru","e.mail.ru",
        "vk.com","api.vk.com","ozon.ru","wildberries.ru","avito.ru","avito.st","hh.ru","sberbank.ru","online.sberbank.ru",
        "alfabank.ru","alfa.ru","tbank.ru","tinkoff.ru","vtb.ru","finam.ru","63.ru","aif.ru","amic.ru","angliya.com",
        "ap22.ru","asiaplustj.info","avesta.tj","azerisport.com","belta.by","championat.com","chita.ru","citilink.ru",
        "civil.ge","click-or-die.ru","dni.ru","e1.ru","echo.az","echo.msk.ru","fedpress.ru","f1news.ru","fontanka.ru",
        "gazeta.ru","gazetanovgorod.ru","golosarmenii.am","government.ru","gundogar-news.com","hronikatm.com",
        "infoabad.com","inosmi.ru","interfax.ru","itogi.ru","izvestia.ru","kp.ru","kremlin.ru","lenta.ru","matchtv.ru",
        "meduza.io","mn.ru","ng.ru","novayagazeta.ru","newsvl.ru","og.ru","ok.ru","politikus.info","ppt.ru",
        "pressball.by","progorodsamara.ru","radiomayak.ru","rbc.ru","rg.ru","ria.ru","rskrf.ru","rutube.ru","sovsport.ru",
        "sport-express.ru","sport24.ru","sportbox.ru","sports.ru","tass.ru","trud.ru","utro.ru","ytro.ru","zr.ru",
        "one.one.one.one","dns.google","quad9.net","npmjs.org","pypi.org","gitlab.com","bitbucket.org","android.com",
        "yastatic.net","dft.ru","afisha.ru","gosuslugi.ru","yandex.ru","aviasales.ru","kinopoisk.ru"
    }
    forced_block_suffixes = {
        "bit.ly","tinyurl.com","t.co","reurl.cc","is.gd","ow.ly","linktr.ee","about.me","campaign-archive.com",
        "vk.link","app.link","mradx.net","adjust.com","static.rutubelist.ru","static.kuper.ru","static-origin.kuper.ru",
        "max.ru","zztfly.com","sub.scroogethebest.com","apmplus.volces.com","googleadservices.com","doubleclick.net",
        "googlesyndication.com","google-analytics.com","googletagmanager.com","app-measurement.com","crashlytics.com",
        "branch.io","amplitude.com","mixpanel.com","hotjar.com","yandexmetrica.ru","mc.yandex.ru","metrika.yandex.ru",
        "top.mail.ru","adriver.ru","adfox.ru","pixel.facebook.com","analytics.facebook.com","connect.facebook.net",
        "tr.facebook.com","firebaselogging-pa.googleapis.com"
    }
    for name in urls:
        whitelist_clean[name] = not ("OISD" in name)
else:
    # --- Настройка: custom-режим ---
    def ask_csv(key):
        print("\n=== " + tr(key) + " ===")
        print(tr("custom_list_hint"))
        v = _inp_allow_empty(f"{tr('custom_val')}: ").strip()
        if not v:
            return []
        return [x.strip() for x in v.split(",") if x.strip()]

    for d in ask_csv("custom_wd"):
        protected_domains.add(d.lower().strip("."))
    for d in ask_csv("custom_ws"):
        protected_suffixes.add(d.lower().lstrip(".").strip("."))
    for d in ask_csv("custom_bd"):
        forced_block_domains.add(d.lower().strip("."))
    for d in ask_csv("custom_bs"):
        forced_block_suffixes.add(d.lower().lstrip(".").strip("."))

    print("\n=== " + tr("custom_black_urls") + " ===")
    idx = 1
    while True:
        name = _inp_allow_empty(f"  {tr('custom_name')} #{idx} ({tr('custom_name_end')}): ").strip()
        if not name:
            break
        lst = []
        print(f"    {tr('custom_url')}: ({tr('custom_url_end')})")
        while True:
            u = _inp_allow_empty(f"    {tr('custom_url')} #{len(lst)+1}: ").strip()
            if not u:
                break
            lst.append(u)
        if not lst:
            continue
        urls[name] = lst
        cl = _input(f"    {tr('custom_clean')} [n]: ").strip().lower()
        whitelist_clean[name] = cl in ("y", "yes")
        idx += 1

    print("\n=== " + tr("custom_white_urls") + " ===")
    idx = 1
    while True:
        name = _inp_allow_empty(f"  {tr('custom_name')} #{idx} ({tr('custom_name_end')}): ").strip()
        if not name:
            break
        lst = []
        print(f"    {tr('custom_url')}: ({tr('custom_url_end')})")
        while True:
            u = _inp_allow_empty(f"    {tr('custom_url')} #{len(lst)+1}: ").strip()
            if not u:
                break
            lst.append(u)
        if not lst:
            continue
        white_urls[name] = lst
        idx += 1

    if not urls:
        print("\n[!] " + tr("custom_no_bl"))
        sys.exit(1)

# --- Опция разбиения ---
print("\n" + "="*40)
print(tr("split_hdr"))
print("  " + tr("split_1"))
print("  " + tr("split_2"))
_v = _input(f"{tr('choice')} [2]: ").strip()
SPLIT_LISTS = (_v == "1")
print(" -> " + (tr("split_on") if SPLIT_LISTS else tr("split_off")))
print("="*40)

# --- Константы-фильтры ---
exclude_keywords = [
    "ads","analytics","tracker","tracking","tracer","metrics","metrica","metrika","telemetry","pixel","beacon",
    "adserver","doubleclick","adjust","appsflyer","app-measurement","log-upload","crash-report","messenger.yandex","vetmanager"
]
exclude_pattern = re.compile('|'.join(re.escape(kw) for kw in exclude_keywords))
INVALID_CHARS = set('?|=*(),&:[]/\\%#_')

protected_ips = {
    "1.1.1.1","1.0.0.1","8.8.8.8","8.8.4.4","9.9.9.9","149.112.112.112","94.140.14.14","94.140.15.15",
    "94.140.14.15","94.140.14.1","76.76.2.0","76.76.10.0","208.67.222.222","208.67.220.220",
    "212.13.114.252","212.111.75.55","195.230.90.26","194.247.146.200","195.2.83.118",
    "195.133.107.200","195.146.64.44","195.230.90.32","194.67.20.14"
}
forced_block_ips = {"178.248.232.0/21","82.148.11.0/24","185.15.56.0/22","91.223.116.0/22"}
plus_forced_block_suffixes = {"yabuchka.net","xcelebs.ru"}
dangerous_tlds = {"com","net","org","ru","site","info","xyz","bid","club","shop","html","xml","gif","js","php","top"}
AGGREGATE_THRESHOLD = 0

headers = {'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1'}
errors_output_file = "LogsAdBlockScript"

# --- Состояние ---
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
DNS_SERVERS = ["8.8.8.8","8.8.4.4","94.140.14.14","94.140.15.15","1.1.1.1"]
_progress_state = {}

# --- Хелпер: определять, чистить ли список белыми ---
def should_filter_with_whitelist(name):
    if MODE == "default":
        return not ("OISD" in name)
    return whitelist_clean.get(name, True)

# ========================================
#  Блок: сетевые функции
# ========================================

def setup_dns_and_test():
    while True:
        sys.stdout.write(f"\r    [net] {tr('net_setup')}...\033[K")
        sys.stdout.flush()
        try:
            with open("/etc/resolv.conf", "w") as f:
                for dns in DNS_SERVERS:
                    f.write(f"nameserver {dns}\n")
            result = subprocess.run(
                ["ping", "-c", "3", "google.com"],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=5
            )
            if result.returncode == 0:
                sys.stdout.write(f"\r    [net] {tr('net_ok')}\033[K")
                sys.stdout.flush()
                return True
            sys.stdout.write(f"\r    [net] {tr('net_fail')}\033[K")
            sys.stdout.flush()
        except Exception as e:
            sys.stdout.write(f"\r    [net] {tr('net_err')}: {e}\033[K")
            sys.stdout.flush()
        time.sleep(5)

def full_network_diagnostics():
    print("    [diag] network diagnostics...")
    try:
        subprocess.run(["ping", "-c", "3", "8.8.8.8"])
        subprocess.run(["ping", "-c", "3", "google.com"])
        subprocess.run(["cat", "/etc/resolv.conf"])
    except Exception:
        pass

# ========================================
#  Блок: прогресс-бар
# ========================================

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
        elapsed = f" | {int(time.time() - start_time)}s"
    sys.stdout.write(f"\r\033[2K{prefix} [{bar}] {current}/{total} ({pct:.1f}%){elapsed}")
    sys.stdout.flush()
    if current == total:
        sys.stdout.write("\n")
        sys.stdout.flush()
    if "[dl]" in prefix:
        _progress_state[prefix] = {"time": now, "current": current}

# ========================================
#  Блок: скачивание списков (несколькими методами)
# ========================================

def download_with_urllib(url, headers, timeout=30):
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        cl = resp.getheader('Content-Length')
        try:
            total = int(cl) if cl else None
        except Exception:
            total = None
        out = bytearray()
        read = 0
        start = time.time()
        last_unk = 0.0
        while True:
            chunk = resp.read(8192)
            if not chunk:
                break
            out.extend(chunk)
            read += len(chunk)
            if total:
                print_progress("  [dl] urllib", min(read, total), total, start_time=start)
            else:
                now = time.time()
                if now - last_unk >= 0.25:
                    sys.stdout.write(f"\r\033[2K  [dl] urllib {read // 1024} KB")
                    sys.stdout.flush()
                    last_unk = now
        if total and read < total * 0.95:
            raise Exception("Incomplete download")
        if not total:
            sys.stdout.write("\n")
        return out.decode('utf-8', errors='ignore').splitlines(), "urllib"

def download_with_curl_to_file(url, headers, timeout=15, curl_args=None):
    tmp = tempfile.NamedTemporaryFile(delete=False)
    tmp.close()
    base = ['curl', '-s', '-L', '--fail', '--show-error', '-A', headers['User-Agent']]
    cmd = base + (curl_args or []) + ['-o', tmp.name, url]
    try:
        proc = subprocess.run(cmd, timeout=timeout)
        if proc.returncode == 0:
            with open(tmp.name, 'rb') as f:
                data = f.read().decode('utf-8', errors='ignore').splitlines()
            return data, "curl"
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
    variants.append((curl_common + [url], False, "curl"))
    variants.append((curl_common + ['--http1.1', url], False, "curl-h1"))
    variants.append((curl_common + ['--compressed', url], False, "curl-gz"))
    if shutil.which('wget'):
        variants.append((['wget', '--no-check-certificate', '-q', '-O', '-', url], False, "wget"))
    if shutil.which('aria2c'):
        variants.append((['aria2c', '-q', '-x', '4', '-o', 'aria_tmp_dl', url], True, "aria2c"))
    for cmd, is_file_writer, descr in variants:
        if not shutil.which(cmd[0]):
            continue
        try:
            if not is_file_writer:
                tmp = tempfile.NamedTemporaryFile(delete=False)
                tmp.close()
                try:
                    proc = subprocess.run(cmd, stdout=open(tmp.name, 'wb'), stderr=subprocess.DEVNULL, timeout=15)
                    if proc.returncode == 0:
                        with open(tmp.name, 'rb') as f:
                            return f.read().decode('utf-8', errors='ignore').splitlines(), descr
                except Exception:
                    pass
                finally:
                    try:
                        os.unlink(tmp.name)
                    except Exception:
                        pass
            else:
                proc = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=15)
                if proc.returncode == 0 and cmd[0] == 'aria2c':
                    try:
                        with open('aria_tmp_dl', 'rb') as f:
                            return f.read().decode('utf-8', errors='ignore').splitlines(), "aria2c"
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

def download_data(name, url_or_urls):
    print(f"\n  [*] {tr('dl')}: {name}...")
    setup_dns_and_test()
    urls_to_try = url_or_urls if isinstance(url_or_urls, list) else [url_or_urls]
    for url in urls_to_try:
        for attempt in range(1, 4):
            for fn in (download_with_urllib, download_with_curl_to_file):
                try:
                    if fn is download_with_urllib:
                        lines, method = fn(url, headers, timeout=30)
                    else:
                        lines, method = fn(url, headers, timeout=15)
                    if lines and len(lines) > 10 and not any("<html" in str(l).lower() for l in lines[:15]):
                        print(f"\r  [+] {tr('dl_ok')}: {len(lines)} ({method})\033[K")
                        return lines, method
                except Exception:
                    pass
            try:
                lines, method = try_command_variants(url)
                if lines and len(lines) > 10 and not any("<html" in str(l).lower() for l in lines[:15]):
                    print(f"\r  [+] {tr('dl_ok')}: {len(lines)} ({method})\033[K")
                    return lines, method
            except Exception:
                pass
            sys.stdout.write(f"\r    [!] {tr('dl_attempt')} {int(1 + attempt * 0.5)}s...\033[K")
            sys.stdout.flush()
            time.sleep(1 + attempt * 0.5)
        full_network_diagnostics()
    print(f"\r  [!] {tr('dl_err')}: {name} {tr('dl_err_any')}.\033[K")
    return [], None

# ========================================
#  Блок: валидация домена / IP / защиты
# ========================================

def is_protected_full(domain):
    if domain in protected_domains:
        return True, "exact"
    parts = domain.split('.')
    for i in range(len(parts)):
        if '.'.join(parts[i:]) in protected_suffixes:
            return True, "suffix"
    return False, None

def is_valid_domain(d):
    if not d or len(d) < 4:
        return False
    if not d.isascii():
        return False
    if d.startswith('.') or d.startswith('-') or d.endswith('.') or d.endswith('-'):
        return False
    if '.' not in d:
        return False
    if not INVALID_CHARS.isdisjoint(d):
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

def normalize_line_for_parser(raw_line):
    s = raw_line.strip()
    if not s:
        return raw_line
    m = re.match(r'^address=/([^/]+)/', s, re.IGNORECASE)
    if m:
        return m.group(1).lower().strip('.')
    m = re.match(r'^server=/([^/]+)/', s, re.IGNORECASE)
    if m:
        return m.group(1).lower().strip('.')
    m = re.match(r'^local-zone:\s*"([^"]+)"', s, re.IGNORECASE)
    if m:
        return m.group(1).lower().strip('.')
    if s.startswith('/') and s.endswith('/') and len(s) > 2:
        return "#__PIHOLE_REGEX_SKIP__"
    return raw_line

# ========================================
#  Блок: логи
# ========================================

def save_logs(total_time_val=None):
    try:
        with open(errors_output_file, 'w', encoding='utf-8') as ef:
            ef.write(f"Log generated at: {time.ctime()}\n")
            ef.write("=" * 40 + "\n")
            ef.write("DOWNLOAD REPORT (blacklists)\n")
            for name, info in download_report.items():
                ef.write(f"{name}\t{info['status']}\t{info.get('method','N/A')}\t{info.get('lines',0)}\n")
            ef.write("\nDOWNLOAD REPORT (whitelists)\n")
            for name, info in white_download_report.items():
                ef.write(f"{name}\t{info['status']}\t{info.get('method','N/A')}\t{info.get('lines',0)}\n")
            ef.write(f"\nTotal errors/exclusions: {len(errors)}\n")
    except Exception as e:
        sys.stdout.write(f"\n[!] Log write failed: {e}\n")

# ========================================
#  Блок: оптимизация доменов (убираем поддомены, если есть родитель)
# ========================================

def optimize_domain_set(source_domains, log_prefix):
    sorted_raw = sorted(list(source_domains), key=lambda x: x.count('.'))
    opt_set = set()
    total = len(sorted_raw)
    start = time.time()
    for idx, d in enumerate(sorted_raw, start=1):
        if idx % 1000 == 0 or idx == total:
            print_progress(f"  [{log_prefix}]", idx, total, start_time=start)
        parts = d.split('.')
        redundant = False
        for i in range(1, len(parts) - 1):
            if ".".join(parts[i:]) in opt_set:
                redundant = True
                break
        if not redundant:
            opt_set.add(d)
    return opt_set

# ========================================
#  Блок: запись итоговых списков
# ========================================

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
        with open(f"{base_name}.list", 'w', encoding='utf-8') as f:
            for line in combined:
                f.write(line + "\n")
        if not SPLIT_LISTS:
            return total
        chunk_size = 100000
        chunks = math.ceil(total / chunk_size)
        for i in range(chunks):
            chunk_data = combined[i * chunk_size : (i + 1) * chunk_size]
            out_name = f"{base_name}_{i+1}.list"
            with open(out_name, 'w', encoding='utf-8') as f:
                written = 0
                for line in chunk_data:
                    f.write(line + "\n")
                    written += 1
                    if written % 1000 == 0 or written == len(chunk_data):
                        print_progress(f"  [{log_prefix} {i+1}/{chunks}]", written, len(chunk_data), start_time=time.time())
        return total

    total_rules = 0
    if MODE == "custom" or oisd_choice in ('1', '3'):
        print("[*] " + tr("opt_std"))
        optimized_domains = optimize_domain_set(all_domains | oisd_domains, "opt std")
        print("[*] " + tr("opt_plus"))
        optimized_domains_plus = optimize_domain_set(all_domains | oisd_domains | nsfw_domains, "opt plus")
        print("[*] " + tr("writing"))
        final_list_len = write_chunks("REJECT_RULES", optimized_domains, all_ips | oisd_ips, "write std")
        final_list_plus_len = write_chunks("REJECT_RULES_PLUS", optimized_domains_plus, all_ips | oisd_ips | nsfw_ips, "write plus", is_plus=True)
        total_rules += final_list_len + final_list_plus_len
    if MODE == "default" and oisd_choice in ('2', '3'):
        print("[*] " + tr("opt_sm"))
        optimized_domains_sm = optimize_domain_set(all_domains | oisd_small_domains, "opt sm")
        print("[*] " + tr("opt_plus_sm"))
        optimized_domains_plus_sm = optimize_domain_set(all_domains | oisd_small_domains | nsfw_small_domains, "opt plus sm")
        print("[*] " + tr("writing"))
        final_list_sm_len = write_chunks("REJECT_RULES_SMALL", optimized_domains_sm, all_ips | oisd_small_ips, "write sm")
        final_list_plus_sm_len = write_chunks("REJECT_RULES_PLUS_SMALL", optimized_domains_plus_sm, all_ips | oisd_small_ips | nsfw_small_ips, "write plus sm", is_plus=True)
        total_rules += final_list_sm_len + final_list_plus_sm_len
    return total_rules

# ========================================
#  ЭТАП 1: загрузка белых списков
# ========================================

print("\n=== " + tr("e1w") + " ===")
for name, url in white_urls.items():
    lines, method = download_data(name, url)
    if lines and method:
        white_raw_data[name] = {"lines": lines, "method": method, "url": url}
        white_download_report[name] = {"status": "ok", "method": method, "lines": len(lines)}
    else:
        white_download_report[name] = {"status": "failed", "method": None, "lines": 0}
        failed_white_lists.append(name)

# ========================================
#  ЭТАП 1: загрузка чёрных списков
# ========================================

print("\n=== " + tr("e1b") + " ===")
for name, url in urls.items():
    lines, method = download_data(name, url)
    if lines and method:
        black_raw_data[name] = {"lines": lines, "method": method, "url": url}
        download_report[name] = {"status": "ok", "method": method, "lines": len(lines)}
    else:
        download_report[name] = {"status": "failed", "method": None, "lines": 0}
        failed_lists.append(name)

# ========================================
#  ЭТАП 2: повторная загрузка ошибок
# ========================================

print("\n=== " + tr("e2") + " ===")
while failed_lists or failed_white_lists:
    print("\n" + "=" * 40)
    print(tr("need_retry") + ":")
    for w in failed_white_lists:
        print(f"  [{tr('wlist')}]  - {w}")
    for b in failed_lists:
        print(f"  [{tr('blist')}] - {b}")
    print("=" * 40)
    target = failed_white_lists[0] if failed_white_lists else failed_lists[0]
    is_white = target in failed_white_lists
    print(f"\n[?] {tr('retry_q')} '{target}'")
    print("  " + tr("retry_1"))
    print("  " + tr("retry_2"))
    print("  " + tr("retry_3"))
    ans = _input(f"{tr('choice')} (1/2/3): ").strip()
    if ans == '2':
        (failed_white_lists if is_white else failed_lists).remove(target)
        continue
    if ans in ('1', '3'):
        setup_dns_and_test()
        url_to_try = _input(tr("retry_manual") + ": ").strip() if ans == '3' else (white_urls[target] if is_white else urls[target])
        lines, method = download_data(target, url_to_try)
        if not lines:
            print("  [!] " + tr("retry_fail"))
            continue
        print(f"  [+] {tr('retry_ok')}")
        if is_white:
            white_raw_data[target] = {"lines": lines, "method": method, "url": url_to_try}
            failed_white_lists.remove(target)
        else:
            black_raw_data[target] = {"lines": lines, "method": method, "url": url_to_try}
            failed_lists.remove(target)

# ========================================
#  ЭТАП 3: обработка белых списков
# ========================================

print("\n=== " + tr("e3") + " ===")
for name, data_dict in white_raw_data.items():
    lines = data_dict["lines"]
    total_lines = len(lines)
    print(f"\n  [*] {tr('parsing')}: {name}...")
    for idx, raw_line in enumerate(lines, start=1):
        if idx % 200 == 0 or idx == total_lines:
            print_progress("  [w-parse]", idx, total_lines)
        line = raw_line.strip()
        if not line or line.startswith(('#', '!')):
            continue
        if line.startswith('.'):
            d = line.lstrip('.').lower()
            if is_valid_domain(d):
                protected_suffixes.add(d)
            continue
        if ',' in line:
            parts = line.split(',', 1)
            if len(parts) == 2:
                key = parts[0].lower()
                val = parts[1].strip().lower().split('#')[0].strip()
                if key.startswith('domain-suffix'):
                    if is_valid_domain(val):
                        protected_suffixes.add(val)
                elif key.startswith('domain'):
                    if is_valid_domain(val):
                        protected_domains.add(val)
            continue
        if is_valid_domain(line.lower()):
            protected_domains.add(line.lower())

for d in list(protected_domains):
    if (d.endswith(".apple.com") or d.startswith("apple-") or d.startswith("icloud")) and d != "apple.com":
        protected_domains.discard(d)
        protected_suffixes.add(d)

# ========================================
#  ЭТАП 4: обработка чёрных списков
# ========================================

print("\n=== " + tr("e4") + " ===")
for name, data_dict in black_raw_data.items():
    lines = data_dict["lines"]
    total_lines = len(lines)
    local_domain_count = 0
    local_ip_count = 0
    print(f"\n  [*] {tr('parsing')}: {name}...")
    is_oisd_nsfw = MODE == "default" and "10.2) OISD NSFW" in name
    is_oisd_main = MODE == "default" and "10.1) OISD" in name
    is_oisd_nsfw_sm = MODE == "default" and "10.4) OISD NSFW Small" in name
    is_oisd_sm = MODE == "default" and "10.3) OISD Small" in name
    use_whitelist = should_filter_with_whitelist(name)

    for idx, raw_line in enumerate(lines, start=1):
        if idx % 200 == 0 or idx == total_lines:
            print_progress("  [b-parse]", idx, total_lines)
        normalized = normalize_line_for_parser(raw_line)
        if normalized == "#__PIHOLE_REGEX_SKIP__":
            stats["junk"] += 1
            continue
        raw_line = normalized
        line = raw_line.strip().lower()
        if not line or line.startswith(('!', '[', '@@')) or '##' in line or '#@#' in line or line.startswith('#'):
            continue
        if exclude_pattern.search(line):
            stats["excluded"] += 1
            if len(errors) < 500:
                errors.append(("excluded_keyword", name, raw_line))
            continue

        if "," in line and not line.startswith("||"):
            parts = [p.strip() for p in line.split(',', 2)]
            if len(parts) >= 2:
                rule_type = parts[0]
                val = parts[1].split('#')[0].strip()
                if "ip-cidr" in rule_type:
                    v = validate_ip(val)
                    if v:
                        pure_ip = v.split('/')[0]
                        if use_whitelist and pure_ip in protected_ips:
                            stats["protected_exact"] += 1
                        else:
                            (nsfw_ips if is_oisd_nsfw else oisd_ips if is_oisd_main else
                             nsfw_small_ips if is_oisd_nsfw_sm else oisd_small_ips if is_oisd_sm
                             else all_ips).add(v)
                            local_ip_count += 1
                    else:
                        stats["junk"] += 1
                elif "domain" in rule_type:
                    if is_valid_domain(val):
                        protected, reason = is_protected_full(val) if use_whitelist else (False, None)
                        if protected:
                            if reason == "exact":
                                stats["protected_exact"] += 1
                            else:
                                stats["protected_suffix"] += 1
                        else:
                            (nsfw_domains if is_oisd_nsfw else oisd_domains if is_oisd_main else
                             nsfw_small_domains if is_oisd_nsfw_sm else oisd_small_domains if is_oisd_sm
                             else all_domains).add(val)
                            local_domain_count += 1
                    else:
                        stats["junk"] += 1
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
            continue
        clean = clean.split('^')[0].split('$')[0].split(':')[0].split('*')[0].strip().strip('.')
        if not clean:
            stats["junk"] += 1
            continue

        validated_ip = validate_ip(clean)
        if validated_ip:
            pure_ip = validated_ip.split('/')[0]
            if use_whitelist and pure_ip in protected_ips:
                stats["protected_exact"] += 1
            else:
                (nsfw_ips if is_oisd_nsfw else oisd_ips if is_oisd_main else
                 nsfw_small_ips if is_oisd_nsfw_sm else oisd_small_ips if is_oisd_sm
                 else all_ips).add(validated_ip)
                local_ip_count += 1
        elif is_valid_domain(clean):
            protected, reason = is_protected_full(clean) if use_whitelist else (False, None)
            if protected:
                if reason == "exact":
                    stats["protected_exact"] += 1
                else:
                    stats["protected_suffix"] += 1
            else:
                (nsfw_domains if is_oisd_nsfw else oisd_domains if is_oisd_main else
                 nsfw_small_domains if is_oisd_nsfw_sm else oisd_small_domains if is_oisd_sm
                 else all_domains).add(clean)
                local_domain_count += 1
        else:
            stats["junk"] += 1

    download_report[name]["extracted_domains"] = local_domain_count
    download_report[name]["extracted_ips"] = local_ip_count
    print(f"  -> {tr('extracted')}: {local_domain_count} | IP: {local_ip_count}")

for suffix in forced_block_suffixes:
    if is_valid_domain(suffix):
        all_domains.add(suffix)
for domain in forced_block_domains:
    if is_valid_domain(domain):
        all_domains.add(domain)
for ip in forced_block_ips:
    v = validate_ip(ip)
    if v:
        all_ips.add(v)

# ========================================
#  ЭТАП 5: формирование и запись файлов
# ========================================

print("\n=== " + tr("e5") + " ===")
build_and_write()

TOTAL_TIME = round(time.time() - SCRIPT_START_TIME, 2)

# ========================================
#  Итоговая сводка
# ========================================

print("\n" + "=" * 40)
print(tr("done"))
print("-" * 40)
if MODE == "custom" or oisd_choice in ('1', '3'):
    print(f"{tr('u_std')}: {len(optimized_domains)} / {len(optimized_domains_plus)}")
if MODE == "default" and oisd_choice in ('2', '3'):
    print(f"{tr('u_sm')}: {len(optimized_domains_sm)} / {len(optimized_domains_plus_sm)}")
print(f"{tr('u_ip')}: {len(all_ips)}")
print(f"{tr('rm_kw')}: {stats['excluded']}")
print(f"{tr('junk')}: {stats['junk']}")
print(f"{tr('prot_e')}: {stats['protected_exact']}")
print(f"{tr('prot_s')}: {stats['protected_suffix']}")
print("-" * 40)
if MODE == "custom" or oisd_choice in ('1', '3'):
    print(f"{tr('r_std')}: {final_list_len}")
    print(f"{tr('r_plus')}: {final_list_plus_len}")
if MODE == "default" and oisd_choice in ('2', '3'):
    print(f"{tr('r_sm')}: {final_list_sm_len}")
    print(f"{tr('r_plus_sm')}: {final_list_plus_sm_len}")
print(f"{tr('total_drop')}: {stats['excluded']}")
print(f"{tr('total_time')}: {TOTAL_TIME} {tr('sec')}.")
print("-" * 40)
print(tr("sum_bl") + ":")
for name, info in download_report.items():
    print(f"  - {name}: {info['status']} ({info.get('method','N/A')}, {info.get('lines',0)})")
print("\n" + tr("sum_wl") + ":")
for name, info in white_download_report.items():
    print(f"  - {name}: {info['status']} ({info.get('method','N/A')}, {info.get('lines',0)})")
save_logs(TOTAL_TIME)
print("\n" + (tr("all_ok") if not (failed_lists or failed_white_lists) else tr("skipped")))
print("=" * 40)
ADBLOCK_END
fi

# ========================================
#  Скрипт 2/5: SQLiteTXT.py
# ========================================
if [ "$REGEN_PY" = "1" ] || [ ! -s "$BASE/SQLiteTXT.py" ]; then
cat << 'SQLITE_END' > "$BASE/SQLiteTXT.py"
# ========================================
#  SQLiteTXT: конвертер SQLite баз в текстовый вид
# ========================================

import os
import sys
import re
import sqlite3
import shutil
from pathlib import Path
from datetime import datetime
from collections import defaultdict

os.umask(0o077)

# --- Загрузка языка ---
LANG = os.environ.get("LANG_SEL", "").strip()
if not LANG:
    try:
        with open(os.path.expanduser("~/.sr_toolkit_lang")) as _f:
            LANG = _f.read().strip()
    except Exception:
        LANG = "ru"
if LANG not in ("ru", "en"):
    LANG = "ru"

# --- Словарь переводов ---
_T = {
"ru": {
 "exit": "Выход.",
 "folder_missing": "Папка не найдена",
 "found_files": "Найденные .db файлы",
 "choose_files": "Выберите файлы",
 "choose_file": "Выберите файл",
 "multi_hint": "можно несколько, например 1,3-4 или all",
 "enter_number": "введите номер",
 "choice": "Ваш выбор",
 "bad": "Неверный выбор",
 "one_file": "Выберите ровно один файл",
 "m_export": "1 - Экспорт",
 "m_rename": "2 - Переименование входных файлов",
 "m_sep": "3 - Разделитель вывода",
 "m_clean": "4 - Очистка повреждённых файлов",
 "m_q": "q - Выход",
 "menu": "Выберите режим",
 "no_db": "В папке Input нет .db файлов",
 "place": "Поместите файлы в",
 "press": "и нажмите Enter для продолжения",
 "type_q": "Или введите q для выхода",
 "export_done": "Экспорт завершён. Файлы сохранены в Output",
 "rename_created": "Переименовать созданный файл? (y/n)",
 "done": "Готово! Можете продолжить или выйти.",
 "processing": "Обработка",
 "processed": "Обработана",
 "tables": "таблиц",
 "err_proc": "Ошибка при обработке",
 "exp_settings": "Настройки экспорта",
 "opt_schema": "1. Показывать схему таблиц",
 "opt_stats": "2. Показывать количество записей",
 "opt_kw": "3. Фильтровать записи по ключевым словам",
 "opt_dedupe": "4. Удалять дубликаты по URL",
 "opt_sort": "5. Сортировать по политике",
 "enter_kw": "Введите ключевые слова для фильтрации",
 "exp_len": "Ожидается символов",
 "use_01": "Используйте только 0 и 1",
 "new_name": "Новое имя для",
 "new_prefix": "Введите префикс для группы",
 "apply_all": "Применить ко всем файлам? (y/n)",
 "no_files": "Нет файлов для переименования",
 "will_over": "Следующие файлы будут перезаписаны",
 "cont_q": "Продолжить? (y/n)",
 "cancel": "Отменено",
 "renamed": "Переименован в",
 "cont_rename": "Продолжить переименование? (y/n)",
 "rename_q": "Переименовать один файл (1) или группу (2)?",
 "name_empty": "Имя не может быть пустым",
 "file_exists": "Файл с таким именем уже существует",
 "prefix_empty": "Префикс не может быть пустым",
 "cur_sep": "Текущий разделитель",
 "sep_1": "1 - tab",
 "sep_2": "2 - comma (,)",
 "sep_3": "3 - semicolon (;)",
 "choose_num": "Выберите номер",
 "sep_changed": "Разделитель изменён на",
 "clean_hdr": "Очистка повреждённых файлов",
 "clean_1": "1 - Проверить все .db и удалить повреждённые",
 "clean_2": "2 - Очистить папку Input",
 "clean_3": "3 - Очистить папку Output",
 "clean_4": "4 - Очистить обе папки",
 "clean_5": "5 - Назад",
 "no_db_check": "Нет .db файлов для проверки",
 "checking": "Проверка целостности баз данных",
 "corrupted": "повреждён, удаляем",
 "del_all": "Удалить всё содержимое",
 "folder_ok": "Папка очищена",
 "skipped": "Пропущено",
 "no_tables": "не содержит таблиц",
 "schema": "Схема базы данных",
 "table": "Таблица",
 "columns": "Колонки",
 "records": "Общее количество записей",
 "kw_filter": "Фильтр по ключевым словам",
 "dedupe_on": "Дедупликация по URL включена",
 "sort_on": "Сортировка по политике",
 "filter_empty": "нет записей, соответствующих фильтру",
 "total_after": "Итого записей после фильтрации/дедупликации",
 "y_or_n": "y/n",
 "back_hint": "b - назад",
 "back": "Назад"
},
"en": {
 "exit": "Exit.",
 "folder_missing": "Folder not found",
 "found_files": "Found .db files",
 "choose_files": "Choose files",
 "choose_file": "Choose a file",
 "multi_hint": "you can choose several, e.g. 1,3-4 or all",
 "enter_number": "enter number",
 "choice": "Your choice",
 "bad": "Invalid choice",
 "one_file": "Choose exactly one file",
 "m_export": "1 - Export",
 "m_rename": "2 - Rename input files",
 "m_sep": "3 - Output separator",
 "m_clean": "4 - Clean corrupted files",
 "m_q": "q - Quit",
 "menu": "Choose mode",
 "no_db": "No .db files in Input folder",
 "place": "Put files into",
 "press": "and press Enter to continue",
 "type_q": "Or type q to exit",
 "export_done": "Export complete. Files saved to Output",
 "rename_created": "Rename created file? (y/n)",
 "done": "Done! You can continue or exit.",
 "processing": "Processing",
 "processed": "Processed",
 "tables": "tables",
 "err_proc": "Error processing",
 "exp_settings": "Export settings",
 "opt_schema": "1. Show table schema",
 "opt_stats": "2. Show record count",
 "opt_kw": "3. Filter by keywords",
 "opt_dedupe": "4. Deduplicate by URL",
 "opt_sort": "5. Sort by policy",
 "enter_kw": "Enter comma-separated keywords",
 "exp_len": "Expected length",
 "use_01": "Use only 0 and 1",
 "new_name": "New name for",
 "new_prefix": "Enter group prefix",
 "apply_all": "Apply to all files? (y/n)",
 "no_files": "No files to rename",
 "will_over": "The following files will be overwritten",
 "cont_q": "Continue? (y/n)",
 "cancel": "Cancelled",
 "renamed": "Renamed to",
 "cont_rename": "Continue renaming? (y/n)",
 "rename_q": "Rename one file (1) or group (2)?",
 "name_empty": "Name cannot be empty",
 "file_exists": "File with this name already exists",
 "prefix_empty": "Prefix cannot be empty",
 "cur_sep": "Current separator",
 "sep_1": "1 - tab",
 "sep_2": "2 - comma (,)",
 "sep_3": "3 - semicolon (;)",
 "choose_num": "Choose number",
 "sep_changed": "Separator changed to",
 "clean_hdr": "Clean corrupted files",
 "clean_1": "1 - Check all .db and delete corrupted",
 "clean_2": "2 - Clean Input folder",
 "clean_3": "3 - Clean Output folder",
 "clean_4": "4 - Clean both folders",
 "clean_5": "5 - Back",
 "no_db_check": "No .db files to check",
 "checking": "Checking databases integrity",
 "corrupted": "corrupted, deleting",
 "del_all": "Delete all contents of",
 "folder_ok": "Folder cleaned",
 "skipped": "Skipped",
 "no_tables": "contains no tables",
 "schema": "Database schema",
 "table": "Table",
 "columns": "Columns",
 "records": "Total records",
 "kw_filter": "Keyword filter",
 "dedupe_on": "URL deduplication enabled",
 "sort_on": "Sort by policy",
 "filter_empty": "no matching records",
 "total_after": "Total after filter/dedupe",
 "y_or_n": "y/n",
 "back_hint": "b - back",
 "back": "Back"
}}

def tr(k):
    return _T.get(LANG, _T["ru"]).get(k, _T["ru"].get(k, k))

# --- Безопасный ввод ---
def _input(prompt=""):
    try:
        v = input(prompt)
    except (EOFError, KeyboardInterrupt):
        print()
        sys.exit(0)
    if v.strip().lower() in ("q", "quit", "exit"):
        print("[+] " + tr("exit"))
        sys.exit(0)
    return v

def _inp_allow_empty(prompt=""):
    try:
        v = input(prompt)
    except (EOFError, KeyboardInterrupt):
        print()
        sys.exit(0)
    if v.strip().lower() in ("q", "quit", "exit"):
        print("[+] " + tr("exit"))
        sys.exit(0)
    return v

def _inp_allow_back(prompt=""):
    try:
        v = input(prompt)
    except (EOFError, KeyboardInterrupt):
        print()
        sys.exit(0)
    if v.strip().lower() in ("q", "quit", "exit"):
        print("[+] " + tr("exit"))
        sys.exit(0)
    return v

# --- Пути ---
ROOT = Path.home()
INPUT_DIR = ROOT / "Shadowrocket" / "SQLiteTXT" / "Input"
OUTPUT_DIR = ROOT / "Shadowrocket" / "SQLiteTXT" / "Output"
CONFIG_FILE = ROOT / ".sqlitetxt_config"
SEPARATOR = "\t"
SEP_NAME = "tab"

# --- Конфиг разделителя ---
def load_config():
    global SEPARATOR, SEP_NAME
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, "r") as f:
                data = f.read().strip()
                if data in ("tab", "comma", "semicolon"):
                    SEP_NAME = data
                    SEPARATOR = {"tab": "\t", "comma": ",", "semicolon": ";"}[data]
        except Exception:
            pass

def save_config():
    with open(CONFIG_FILE, "w") as f:
        f.write(SEP_NAME)

load_config()

# --- Хелперы ---
def sanitize_filename(name):
    if not name:
        return name
    clean = re.sub(r'[^a-zA-Z0-9_.\-]', '_', name).strip('_')
    return clean or 'file'

def clean_str(s):
    if not s:
        return s
    return ''.join(ch for ch in s if ord(ch) >= 32 or ch in '\n\r\t')

def now_stamp():
    return datetime.now().strftime("%Y%m%d_%H%M%S")

def die(message):
    print(f"[!] {message}")
    sys.exit(1)

# ========================================
#  Блок: работа со списком файлов
# ========================================

def list_input_files():
    if not INPUT_DIR.exists():
        die(f"{tr('folder_missing')}: {INPUT_DIR}")
    files = [p for p in INPUT_DIR.iterdir() if p.is_file() and not p.name.startswith(".") and p.suffix.lower() == ".db"]
    files.sort(key=lambda p: p.name.lower())
    return files

def print_files(files, title=None):
    if title is None:
        title = f"[+] {tr('found_files')}:"
    print(f"\n{title}")
    for i, path in enumerate(files, 1):
        size_mb = path.stat().st_size / 1024 / 1024
        print(f"{i}. {path.name} ({size_mb:.2f} MB)")

def parse_selection(text, max_index):
    text = text.strip().lower()
    if text in {"all", "a"}:
        return list(range(1, max_index + 1))
    result = []
    for part in [p.strip() for p in text.split(",") if p.strip()]:
        if "-" in part:
            left, right = part.split("-", 1)
            if not left.isdigit() or not right.isdigit():
                raise ValueError
            a, b = int(left), int(right)
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

def select_files(files, allow_multiple=True, prompt=None):
    if prompt is None:
        prompt = tr("choose_files")
    while True:
        print_files(files)
        if allow_multiple:
            print(f"\n[?] {prompt} ({tr('multi_hint')})")
        else:
            print(f"\n[?] {prompt} ({tr('enter_number')})")
        choice = _inp_allow_back(f"[?] {tr('choice')}: ").strip()
        if choice.lower() in ("b", "back"):
            return None
        try:
            indices = parse_selection(choice, len(files))
            if not allow_multiple and len(indices) != 1:
                print(f"[!] {tr('one_file')}")
                continue
            return [files[i - 1] for i in indices]
        except Exception:
            print(f"[!] {tr('bad')}")

# ========================================
#  Блок: работа с SQLite
# ========================================

def get_user_tables(conn):
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
    skip = ('logging_segments', 'logging_segdir', 'logging_content')
    return [row[0] for row in cursor.fetchall() if row[0] not in skip]

def get_table_info(conn, table):
    cursor = conn.cursor()
    cursor.execute(f"PRAGMA table_info({table})")
    columns = [row[1] for row in cursor.fetchall()]
    cursor.execute(f"SELECT COUNT(*) FROM {table}")
    return columns, cursor.fetchone()[0]

def row_matches_filter(row, columns, keywords):
    if not keywords:
        return True
    url_idx = columns.index('url') if 'url' in columns else None
    if url_idx is not None:
        val = str(row[url_idx]) if row[url_idx] is not None else ""
        return any(kw.lower() in val.lower() for kw in keywords)
    for col, val in zip(columns, row):
        if val is not None:
            s = str(val)
            if any(kw.lower() in s.lower() for kw in keywords):
                return True
    return False

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
        out_file.write(f"\n({tr('filter_empty')})\n")
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
                        out_file.write(f"{col}: {val if val is not None else '(null)'}\n")
                    total_written += 1
        if other:
            out_file.write("\n--- OTHER ---\n")
            for row in other:
                out_file.write("\n")
                for col, val in zip(columns, row):
                    out_file.write(f"{col}: {val if val is not None else '(null)'}\n")
                total_written += 1
        return total_written
    else:
        for row in rows:
            out_file.write("\n")
            for col, val in zip(columns, row):
                out_file.write(f"{col}: {val if val is not None else '(null)'}\n")
        return len(rows)

# ========================================
#  Блок: режим экспорта
# ========================================

def extract_mode(selected_files, show_schema, show_stats, keywords, dedupe, sort_by_policy):
    total_files = len(selected_files)
    created = []
    for idx, db_path in enumerate(selected_files, 1):
        print(f"\r[*] {tr('processing')} {idx}/{total_files}: {db_path.name}          ", end="")
        base_name = db_path.stem
        out_path = OUTPUT_DIR / f"{base_name}_{now_stamp()}.txt"
        try:
            conn = sqlite3.connect(str(db_path))
            tables = get_user_tables(conn)
            if not tables:
                with open(out_path, 'w', encoding='utf-8') as f:
                    f.write(f"{db_path.name} {tr('no_tables')}.\n")
                conn.close()
                created.append(out_path)
                continue
            with open(out_path, 'w', encoding='utf-8') as f:
                if show_schema:
                    f.write(f"=== {tr('schema')}: {db_path.name} ===\n")
                    for table in tables:
                        columns, total_count = get_table_info(conn, table)
                        f.write(f"\n{tr('table')}: {table}\n")
                        f.write(f"{tr('columns')}: {', '.join(columns)}\n")
                        if show_stats:
                            f.write(f"{tr('records')}: {total_count}\n")
                    f.write("\n" + "=" * 40 + "\n\n")
                total_exported = 0
                for table in tables:
                    f.write(f"\n=== {tr('table')}: {table} ===\n")
                    if keywords:
                        f.write(f"{tr('kw_filter')}: {', '.join(keywords)}\n")
                    if dedupe:
                        f.write(tr("dedupe_on") + "\n")
                    if sort_by_policy:
                        f.write(tr("sort_on") + ": DIRECT -> PROXY -> REJECT\n")
                    count = export_table_human(conn, table, f, dedupe, sort_by_policy, keywords)
                    total_exported += count
                if show_stats:
                    f.write(f"\n--- {tr('total_after')}: {total_exported} ---\n")
            conn.close()
            created.append(out_path)
            print(f"\r[+] {tr('processed')} {db_path.name} -> {out_path.name} ({tr('tables')}: {len(tables)})          ")
        except sqlite3.Error as e:
            print(f"\r[!] {tr('err_proc')} {db_path.name}: {e}          ")
    return created

# --- Настройки экспорта ---
def ask_options_extract():
    print(f"\n=== {tr('exp_settings')} (5 bits, Enter = 11000) ===")
    print(tr("opt_schema"))
    print(tr("opt_stats"))
    print(tr("opt_kw"))
    print(tr("opt_dedupe"))
    print(tr("opt_sort"))
    default = "11000"
    while True:
        s = _input(f"[?] {tr('choice')}: ").strip() or default
        if len(s) != len(default):
            print(f"[!] {tr('exp_len')} {len(default)}")
            continue
        if not all(c in "01" for c in s):
            print(f"[!] {tr('use_01')}")
            continue
        bits = [c == "1" for c in s]
        keywords = []
        if bits[2]:
            kw = _inp_allow_empty(f"[?] {tr('enter_kw')}: ").strip()
            if kw:
                keywords = [x.strip() for x in kw.split(",") if x.strip()]
        return bits, keywords

# ========================================
#  Блок: переименование
# ========================================

def rename_mode(files):
    while True:
        print_files(files)
        print(f"\n[?] {tr('rename_q')} [1]: ", end="")
        choice = _inp_allow_back().strip() or "1"
        if choice.lower() in ("b", "back"):
            return
        if choice == "1":
            selected = select_files(files, allow_multiple=False, prompt=tr("choose_file"))
            if selected is None:
                continue
            path = selected[0]
            new_name = _inp_allow_back(f"[?] {tr('new_name')} {path.name}: ").strip()
            if new_name.lower() in ("b", "back"):
                continue
            new_name = sanitize_filename(clean_str(new_name))
            if not new_name:
                print(f"[!] {tr('name_empty')}")
                continue
            if not new_name.endswith(".db"):
                new_name += ".db"
            new_path = path.parent / new_name
            if new_path.exists():
                print(f"[!] {tr('file_exists')}")
                continue
            if _input(f"[?] {tr('cont_q')} [n]: ").strip().lower() == "y":
                path.rename(new_path)
                print(f"[+] {tr('renamed')} {new_name}")
                files = list_input_files()
        elif choice == "2":
            prefix = sanitize_filename(clean_str(_inp_allow_back(f"[?] {tr('new_prefix')}: ").strip()))
            if not prefix:
                print(f"[!] {tr('prefix_empty')}")
                continue
            for i, path in enumerate(sorted(files, key=lambda p: p.name), 1):
                new_path = path.parent / f"{prefix}-{i}{path.suffix}"
                path.rename(new_path)
            files = list_input_files()
        else:
            print(f"[!] {tr('bad')}")
            continue
        if _input(f"[?] {tr('cont_rename')} [n]: ").strip().lower() != "y":
            break

def rename_single_output_file(file_path):
    new_name = _inp_allow_back(f"[?] {tr('new_name')} {file_path.name}: ").strip()
    if new_name.lower() in ("b", "back"):
        return None
    new_name = sanitize_filename(clean_str(new_name))
    if not new_name:
        print(f"[!] {tr('name_empty')}")
        return None
    if not new_name.endswith(".txt"):
        new_name += ".txt"
    new_path = file_path.parent / new_name
    if new_path.exists():
        print(f"[!] {tr('file_exists')}")
        return None
    file_path.rename(new_path)
    print(f"[+] {tr('renamed')} {new_name}")
    return new_path

# ========================================
#  Блок: разделитель
# ========================================

def change_separator():
    global SEPARATOR, SEP_NAME
    print(f"\n[+] {tr('cur_sep')}: '{SEP_NAME}'")
    print(tr("sep_1"))
    print(tr("sep_2"))
    print(tr("sep_3"))
    choice = _input(f"[?] {tr('choose_num')} [1]: ").strip() or "1"
    mapping = {"1": ("tab", "\t"), "2": ("comma", ","), "3": ("semicolon", ";")}
    if choice in mapping:
        SEP_NAME, SEPARATOR = mapping[choice]
        save_config()
        print(f"[+] {tr('sep_changed')} '{SEP_NAME}'")
    else:
        print(f"[!] {tr('bad')}")

# ========================================
#  Блок: очистка
# ========================================

def clean_broken_files():
    print(f"\n=== {tr('clean_hdr')} ===")
    print(tr("clean_1"))
    print(tr("clean_2"))
    print(tr("clean_3"))
    print(tr("clean_4"))
    print(tr("clean_5"))
    choice = _input(f"[?] {tr('choice')} [5]: ").strip() or "5"
    if choice == "5":
        return
    if choice == "1":
        files = list_input_files()
        if not files:
            print(f"[!] {tr('no_db_check')}")
            return
        print(f"[*] {tr('checking')}...")
        for path in files:
            try:
                conn = sqlite3.connect(str(path))
                conn.cursor().execute("SELECT 1")
                conn.close()
                print(f"[+] {path.name} - OK")
            except sqlite3.Error:
                print(f"[!] {path.name} - {tr('corrupted')}...")
                try:
                    path.unlink()
                except Exception as e:
                    print(f"[!] {path.name}: {e}")
        print("[+] " + tr("folder_ok"))
        return
    dirs = []
    if choice in ("2", "4"):
        dirs.append(INPUT_DIR)
    if choice in ("3", "4"):
        dirs.append(OUTPUT_DIR)
    for d in dirs:
        if not d.exists():
            print(f"[!] {tr('folder_missing')}: {d}")
            continue
        if _input(f"[?] {tr('del_all')} {d}? ({tr('y_or_n')}) [n]: ").strip().lower() == "y":
            for item in d.iterdir():
                try:
                    if item.is_dir():
                        shutil.rmtree(item)
                    else:
                        item.unlink()
                except Exception as e:
                    print(f"[!] {item}: {e}")
            print(f"[+] {tr('folder_ok')}: {d}")
        else:
            print(f"[!] {tr('skipped')}: {d}")

# ========================================
#  Блок: главное меню
# ========================================

def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    while True:
        files = list_input_files()
        while not files:
            print(f"\n[!] {tr('no_db')}.")
            print(f"[*] {tr('place')} {INPUT_DIR} {tr('press')}")
            print(f"[*] {tr('type_q')}")
            cmd = _inp_allow_empty().strip().lower()
            if cmd in ("q", "quit", "exit"):
                print("[+] " + tr("exit"))
                return
            files = list_input_files()
        print(f"\n{tr('m_export')}")
        print(tr("m_rename"))
        print(tr("m_sep"))
        print(tr("m_clean"))
        print(tr("m_q"))
        mode = _input(f"\n[?] {tr('menu')} (1/2/3/4/q) [1]: ").strip() or "1"
        if mode in ("q", "quit", "exit"):
            print("[+] " + tr("exit"))
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
            selected = select_files(files, allow_multiple=True, prompt=tr("choose_files"))
            if selected is None:
                continue
            opts, keywords = ask_options_extract()
            show_schema, show_stats, _, dedupe, sort_by_policy = opts
            created = extract_mode(selected, show_schema, show_stats, keywords, dedupe, sort_by_policy)
            print(f"\n[+] {tr('export_done')}")
            if len(created) == 1:
                if _input(f"[?] {tr('rename_created')} [n]: ").strip().lower() == "y":
                    rename_single_output_file(created[0])
        else:
            print(f"[!] {tr('bad')}")
            continue
        print(f"\n[+] {tr('done')}")
        _inp_allow_empty(f"[*] {tr('press')}")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n[+] " + tr("exit"))
        sys.exit(0)
SQLITE_END
fi

# ========================================
#  Скрипт 3/5: SpyLog.py
# ========================================
if [ "$REGEN_PY" = "1" ] || [ ! -s "$BASE/SpyLog.py" ]; then
cat << 'SPYLOG_END' > "$BASE/SpyLog.py"
# ========================================
#  SpyLog: анализатор логов Shadowrocket
# ========================================

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

os.umask(0o077)

# --- Загрузка языка ---
LANG = os.environ.get("LANG_SEL", "").strip()
if not LANG:
    try:
        with open(os.path.expanduser("~/.sr_toolkit_lang")) as _f:
            LANG = _f.read().strip()
    except Exception:
        LANG = "ru"
if LANG not in ("ru", "en"):
    LANG = "ru"

# --- Словарь переводов ---
_T = {
"ru": {
 "exit": "Выход.",
 "found_files": "Найденные файлы",
 "empty_hdr": "В папке Input нет файлов",
 "empty_hint": "Поместите файлы в",
 "empty_enter": "и нажмите Enter для продолжения",
 "empty_or": "Или введите q для выхода",
 "empty_or_module": "Или введите m — получить Spy.module",
 "m_1": "1 - Extract (извлечение блоков)",
 "m_2": "2 - Compare (сравнение)",
 "m_3": "3 - Rename (переименование входных файлов)",
 "m_4": "4 - Change search pattern",
 "m_5": "5 - Clean broken files",
 "m_6": "6 - Get Spy.module",
 "m_q": "q - Выход",
 "menu": "Выберите режим",
 "choice": "Ваш выбор",
 "bad": "Неверный выбор",
 "multi_hint": "можно несколько, например 1,3-4 или all",
 "enter_number": "введите номер",
 "one_file": "Выберите ровно один файл",
 "choose_files": "Выберите файлы",
 "choose_one": "Выберите файл",
 "cmp_min": "минимум 2 файла",
 "opts_extract": "Настройки вывода (5 бит, Enter = 11110)",
 "opts_compare": "Настройки вывода (6 бит, Enter = 111100)",
 "o_urls": "1. Показывать список уникальных URL",
 "o_decode": "2. Декодировать закодированные строки в телах",
 "o_counts": "3. Показывать количество блоков по каждому файлу",
 "o_kw": "4. Отделить логи с ключевыми словами",
 "o_dup": "5. Показывать дубликаты (0 - удалять, 1 - оставлять)",
 "oc_stats": "1. Показывать статистику URL",
 "oc_decode": "2. Декодировать строки в телах перед сравнением",
 "oc_diffs": "3. Показывать детальные различия полей",
 "oc_blocks": "4. Включать полные блоки в отчёт",
 "oc_kw": "5. Отделить логи с ключевыми словами",
 "oc_dup": "6. Показывать дубликаты (0 - удалять, 1 - оставлять)",
 "sig_hdr": "Как сравнивать сигнатуры (метод + URL)?",
 "sig_1": "1 - полный URL",
 "sig_2": "2 - путь без параметров",
 "sig_3": "3 - только метод + путь",
 "sig_4": "4 - только метод",
 "enter_kw": "Введите ключевые слова (через запятую)",
 "exp_len": "Ожидается символов",
 "use_01": "Используйте только 0 и 1",
 "groups_q": "Сколько групп создать? (минимум 2)",
 "group": "Группа",
 "group_files": "Выберите файлы для группы",
 "cmp_type": "Сравнивать файлы (1) или группы (2)?",
 "extract_done": "Готово",
 "blocks": "Блоков",
 "processing": "Обработка файла",
 "reading": "Чтение файла",
 "reading_grp": "Обработка группы",
 "dedupe": "Дедупликация",
 "saving": "Сохранение",
 "kw_blocks": "Блоки с ключевыми словами (перемещены вверх)",
 "unique_urls": "Уникальные URL",
 "per_file": "Количество блоков по файлам",
 "extracted_hdr": "Извлечённые блоки",
 "rename_q": "Переименовать один файл (1) или группу (2)?",
 "new_name": "Новое имя для",
 "new_prefix": "Введите префикс для группы",
 "apply_all": "Применить ко всем файлам? (y/n)",
 "no_files_rename": "Нет файлов для переименования",
 "will_over": "Следующие файлы будут перезаписаны",
 "cont_q": "Продолжить? (y/n)",
 "cancel": "Отменено",
 "renamed": "Переименован в",
 "cont_rename": "Продолжить переименование? (y/n)",
 "name_empty": "Имя не может быть пустым",
 "file_exists": "Файл с таким именем уже существует",
 "prefix_empty": "Префикс не может быть пустым",
 "pattern_cur": "Текущий паттерн",
 "pattern_new": "Введите новый паттерн (пусто — отмена)",
 "pattern_ok": "Паттерн изменён на",
 "pattern_cancel": "Отмена",
 "clean_hdr": "Очистка",
 "clean_1": "1 - Очистить папку Input",
 "clean_2": "2 - Очистить папку Output",
 "clean_3": "3 - Очистить обе папки",
 "clean_4": "4 - Найти файлы с проблемными именами",
 "clean_5": "5 - Назад",
 "del_all": "Удалить всё содержимое",
 "folder_ok": "Папка очищена",
 "skipped": "Пропущено",
 "folder_missing": "Папка не существует",
 "no_bad": "Подозрительных файлов не найдено",
 "bad_found": "Найдено файлов с проблемными именами",
 "del_all_bad": "Удалить все проблемные файлы? (y/n)",
 "delete_one": "Удалять по одному? (y/n)",
 "delete_q": "Удалить",
 "deleted": "Удалён",
 "deleted_all": "Все проблемные файлы удалены",
 "rename_out": "Переименовать выходной файл",
 "new_name_short": "Новое имя",
 "module_hdr": "Получение Spy.module",
 "module_dl": "Загрузка Spy.module",
 "module_err": "Не удалось загрузить",
 "module_saved": "Сохранено",
 "rename_created": "Переименовать созданный файл? (y/n)",
 "done_continue": "Готово! Можете продолжить или выйти.",
 "press": "Нажмите Enter для продолжения",
 "y_or_n": "y/n",
 "no_input": "нет файлов",
 "no_input_after_module": "После получения модуля добавьте файлы логов в папку Input",
 "how_get_logs": "Как собрать логи: включите Spy.module в Shadowrocket, поработайте, затем выгрузите лог в папку",
 "ask_get_module": "Получить Spy.module сейчас?"
},
"en": {
 "exit": "Exit.",
 "found_files": "Found files",
 "empty_hdr": "No files in Input folder",
 "empty_hint": "Put files into",
 "empty_enter": "and press Enter to continue",
 "empty_or": "Or type q to exit",
 "empty_or_module": "Or type m to fetch Spy.module",
 "m_1": "1 - Extract (extract blocks)",
 "m_2": "2 - Compare",
 "m_3": "3 - Rename (input files)",
 "m_4": "4 - Change search pattern",
 "m_5": "5 - Clean broken files",
 "m_6": "6 - Get Spy.module",
 "m_q": "q - Quit",
 "menu": "Choose mode",
 "choice": "Your choice",
 "bad": "Invalid choice",
 "multi_hint": "you can choose several, e.g. 1,3-4 or all",
 "enter_number": "enter number",
 "one_file": "Choose exactly one file",
 "choose_files": "Choose files",
 "choose_one": "Choose a file",
 "cmp_min": "at least 2 files",
 "opts_extract": "Output options (5 bits, Enter = 11110)",
 "opts_compare": "Output options (6 bits, Enter = 111100)",
 "o_urls": "1. Show unique URLs",
 "o_decode": "2. Decode encoded strings in bodies",
 "o_counts": "3. Show per-file block counts",
 "o_kw": "4. Separate blocks with keywords",
 "o_dup": "5. Show duplicates (0 - drop, 1 - keep)",
 "oc_stats": "1. Show URL statistics",
 "oc_decode": "2. Decode bodies before comparison",
 "oc_diffs": "3. Show detailed field differences",
 "oc_blocks": "4. Include full blocks in report",
 "oc_kw": "5. Separate blocks with keywords",
 "oc_dup": "6. Show duplicates (0 - drop, 1 - keep)",
 "sig_hdr": "How to compare signatures (method + URL)?",
 "sig_1": "1 - full URL",
 "sig_2": "2 - path without params",
 "sig_3": "3 - method + path only",
 "sig_4": "4 - method only",
 "enter_kw": "Enter comma-separated keywords",
 "exp_len": "Expected length",
 "use_01": "Use only 0 and 1",
 "groups_q": "How many groups? (min 2)",
 "group": "Group",
 "group_files": "Choose files for group",
 "cmp_type": "Compare files (1) or groups (2)?",
 "extract_done": "Done",
 "blocks": "Blocks",
 "processing": "Processing file",
 "reading": "Reading file",
 "reading_grp": "Processing group",
 "dedupe": "Deduplicating",
 "saving": "Saving",
 "kw_blocks": "Blocks with keywords (moved to top)",
 "unique_urls": "Unique URLs",
 "per_file": "Per-file block counts",
 "extracted_hdr": "Extracted blocks",
 "rename_q": "Rename one file (1) or group (2)?",
 "new_name": "New name for",
 "new_prefix": "Enter group prefix",
 "apply_all": "Apply to all files? (y/n)",
 "no_files_rename": "No files to rename",
 "will_over": "The following files will be overwritten",
 "cont_q": "Continue? (y/n)",
 "cancel": "Cancelled",
 "renamed": "Renamed to",
 "cont_rename": "Continue renaming? (y/n)",
 "name_empty": "Name cannot be empty",
 "file_exists": "File with this name already exists",
 "prefix_empty": "Prefix cannot be empty",
 "pattern_cur": "Current pattern",
 "pattern_new": "Enter new pattern (empty — cancel)",
 "pattern_ok": "Pattern changed to",
 "pattern_cancel": "Cancelled",
 "clean_hdr": "Cleanup",
 "clean_1": "1 - Clean Input folder",
 "clean_2": "2 - Clean Output folder",
 "clean_3": "3 - Clean both folders",
 "clean_4": "4 - Find files with bad names",
 "clean_5": "5 - Back",
 "del_all": "Delete all contents of",
 "folder_ok": "Folder cleaned",
 "skipped": "Skipped",
 "folder_missing": "Folder does not exist",
 "no_bad": "No suspicious files found",
 "bad_found": "Found files with bad names",
 "del_all_bad": "Delete all bad files? (y/n)",
 "delete_one": "Delete one by one? (y/n)",
 "delete_q": "Delete",
 "deleted": "Deleted",
 "deleted_all": "All bad files deleted",
 "rename_out": "Rename output file",
 "new_name_short": "New name",
 "module_hdr": "Fetching Spy.module",
 "module_dl": "Downloading Spy.module",
 "module_err": "Failed to load",
 "module_saved": "Saved",
 "rename_created": "Rename created file? (y/n)",
 "done_continue": "Done! You can continue or exit.",
 "press": "Press Enter to continue",
 "y_or_n": "y/n",
 "no_input": "no files",
 "no_input_after_module": "After fetching module, put log files into Input folder",
 "how_get_logs": "How to collect logs: enable Spy.module in Shadowrocket, use the app, then export the log into folder",
 "ask_get_module": "Fetch Spy.module now?"
}}

def tr(k):
    return _T.get(LANG, _T["ru"]).get(k, _T["ru"].get(k, k))

# --- Безопасный ввод ---
def _input(prompt=""):
    try:
        v = input(prompt)
    except (EOFError, KeyboardInterrupt):
        print()
        sys.exit(0)
    if v.strip().lower() in ("q", "quit", "exit"):
        print("[+] " + tr("exit"))
        sys.exit(0)
    return v

def _inp_allow_back(prompt=""):
    try:
        v = input(prompt)
    except (EOFError, KeyboardInterrupt):
        print()
        sys.exit(0)
    if v.strip().lower() in ("q", "quit", "exit"):
        print("[+] " + tr("exit"))
        sys.exit(0)
    return v

# --- Пути и константы ---
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

# --- Конфиг паттерна ---
def load_config():
    global SPY_PATTERN
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, 'rb') as f:
                SPY_PATTERN = f.read().strip()
        except Exception:
            pass

def save_config():
    with open(CONFIG_FILE, 'w') as f:
        f.write(SPY_PATTERN.decode('utf-8', errors='ignore'))

load_config()

# ========================================
#  Блок: загрузка Spy.module
# ========================================

def fetch_spy_module():
    print(f"[*] {tr('module_dl')}...")
    try:
        req = urllib.request.Request(SPY_MODULE_URL, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=30) as r:
            data = r.read().decode('utf-8', errors='ignore')
    except Exception as e:
        print(f"[!] {tr('module_err')}: {e}")
        return None
    print("\n" + "=" * 40)
    print(data)
    print("=" * 40)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    out = OUTPUT_DIR / "Spy.module"
    with open(out, 'w', encoding='utf-8') as f:
        f.write(data)
    print(f"[+] {tr('module_saved')}: {out}")
    return data

# ========================================
#  Блок: хелперы
# ========================================

def sanitize_filename(name):
    if not name:
        return name
    clean = re.sub(r'[^a-zA-Z0-9_.\-]', '_', name).strip('_')
    return clean or 'file'

def clean_str(s):
    if not s:
        return s
    return ''.join(ch for ch in s if ord(ch) >= 32 or ch in '\n\r\t')

def now_stamp():
    return datetime.now().strftime("%Y%m%d_%H%M%S")

def die(message):
    print(f"[!] {message}")
    sys.exit(1)

def strip_ansi_bytes(data):
    return ANSI_RE.sub(b"", data)

# ========================================
#  Блок: декодирование
# ========================================

def detect_and_decode(data):
    try:
        detected = chardet.detect(data)
        if detected and detected['encoding'] and detected['confidence'] > 0.5:
            return data.decode(detected['encoding'], errors='replace')
    except Exception:
        pass
    encodings = ['utf-8', 'cp1251', 'koi8-r', 'cp866', 'mac-cyrillic', 'iso-8859-5', 'latin-1']
    best_text = None
    best_score = -1
    for enc in encodings:
        try:
            text = data.decode(enc)
        except Exception:
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
    except Exception:
        return text

def universal_decode_text(text):
    if not text:
        return text
    text = html.unescape(text)
    text = decode_percent(text)
    text = decode_unicode_escapes(text)
    try:
        text = codecs.decode(text, 'quopri')
    except Exception:
        pass
    return text

# ========================================
#  Блок: извлечение и парсинг блоков
# ========================================

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

# ========================================
#  Блок: список файлов и выбор
# ========================================

def list_input_files():
    if not INPUT_DIR.exists():
        return []
    files = [p for p in INPUT_DIR.iterdir() if p.is_file() and not p.name.startswith(".")]
    files.sort(key=lambda p: p.name.lower())
    return files

def print_files(files):
    print(f"\n[+] {tr('found_files')}:")
    for i, path in enumerate(files, 1):
        size_mb = path.stat().st_size / 1024 / 1024
        print(f"{i}. {path.name} ({size_mb:.2f} MB)")

def parse_selection(text, max_index):
    text = text.strip().lower()
    if text in {"all", "a"}:
        return list(range(1, max_index + 1))
    result = []
    for part in [p.strip() for p in text.split(",") if p.strip()]:
        if "-" in part:
            left, right = part.split("-", 1)
            if not left.isdigit() or not right.isdigit():
                raise ValueError
            a, b = int(left), int(right)
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

def select_files(files, allow_multiple=True, prompt=None):
    if prompt is None:
        prompt = tr("choose_files")
    while True:
        if allow_multiple:
            print(f"\n[?] {prompt} ({tr('multi_hint')})")
        else:
            print(f"\n[?] {prompt} ({tr('enter_number')})")
        choice = _inp_allow_back(f"[?] {tr('choice')}: ").strip()
        if choice.lower() in ("b", "back"):
            return None
        try:
            indices = parse_selection(choice, len(files))
            if not allow_multiple and len(indices) != 1:
                print(f"[!] {tr('one_file')}")
                continue
            return [files[i - 1] for i in indices]
        except Exception:
            print(f"[!] {tr('bad')}")

def ask_files(files, compare=False):
    while True:
        print_files(files)
        if compare:
            selected = select_files(files, allow_multiple=True, prompt=f"{tr('choose_files')} ({tr('cmp_min')})")
        else:
            selected = select_files(files, allow_multiple=True, prompt=tr("choose_files"))
        if selected is None:
            return None
        return selected

def ask_groups(files):
    while True:
        try:
            n_str = _input(f"\n[?] {tr('groups_q')}: ").strip()
            n = int(n_str)
            if n >= 2:
                break
            print(f"[!] >= 2")
        except Exception:
            print(f"[!] {tr('enter_number')}")
    groups = []
    for g in range(1, n + 1):
        print(f"\n=== {tr('group')} {g} ===")
        print_files(files)
        selected = select_files(files, allow_multiple=True, prompt=f"{tr('group_files')} {g}")
        if selected is None:
            return None
        groups.append(selected)
    return groups

# ========================================
#  Блок: утилиты обработки блоков
# ========================================

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

# ========================================
#  Блок: диалоги настроек
# ========================================

def ask_options(mode):
    if mode == "extract":
        print(f"\n=== {tr('opts_extract')} ===")
        print(tr("o_urls"))
        print(tr("o_decode"))
        print(tr("o_counts"))
        print(tr("o_kw"))
        print(tr("o_dup"))
        default = "11110"
        while True:
            s = _input(f"[?] {tr('choice')}: ").strip() or default
            if len(s) != len(default):
                print(f"[!] {tr('exp_len')} {len(default)}")
                continue
            if not all(c in "01" for c in s):
                print(f"[!] {tr('use_01')}")
                continue
            bits = [c == "1" for c in s]
            keywords = []
            if bits[3]:
                kw = _inp_allow_back(f"[?] {tr('enter_kw')}: ").strip()
                if kw:
                    keywords = [x.strip() for x in kw.split(",") if x.strip()]
            return bits, keywords
    else:
        print(f"\n=== {tr('opts_compare')} ===")
        print(tr("oc_stats"))
        print(tr("oc_decode"))
        print(tr("oc_diffs"))
        print(tr("oc_blocks"))
        print(tr("oc_kw"))
        print(tr("oc_dup"))
        default = "111100"
        while True:
            s = _input(f"[?] {tr('choice')}: ").strip() or default
            if len(s) != len(default):
                print(f"[!] {tr('exp_len')} {len(default)}")
                continue
            if not all(c in "01" for c in s):
                print(f"[!] {tr('use_01')}")
                continue
            bits = [c == "1" for c in s]
            keywords = []
            if bits[4]:
                kw = _inp_allow_back(f"[?] {tr('enter_kw')}: ").strip()
                if kw:
                    keywords = [x.strip() for x in kw.split(",") if x.strip()]
            print("\n[?] " + tr("sig_hdr"))
            print(tr("sig_1"))
            print(tr("sig_2"))
            print(tr("sig_3"))
            print(tr("sig_4"))
            sig_choice = _input(f"[?] {tr('choice')} [1]: ").strip()
            if sig_choice not in ("1", "2", "3", "4"):
                sig_choice = "1"
            return bits, keywords, int(sig_choice)

def build_records_from_blocks(blocks, source_name, decode=False, sig_level=1):
    records = []
    for block in blocks:
        rec = parse_record_from_text(block, source_name, decode, sig_level)
        records.append(rec)
    return records

# ========================================
#  Блок: режим Extract
# ========================================

def extract_mode(selected_files, show_urls, decode, show_stats, keywords, keep_duplicates):
    all_blocks = []
    per_file_counts = []
    total_found = 0
    total_files = len(selected_files)
    for idx, path in enumerate(selected_files, 1):
        print(f"\r[*] {tr('processing')} {idx}/{total_files}: {path.name}          ", end="")
        blocks = load_log_and_extract_blocks(path)
        if decode:
            blocks = [universal_decode_text(b) for b in blocks]
        total_found += len(blocks)
        per_file_counts.append((path.name, len(blocks)))
        all_blocks.extend(blocks)
    print(f"\r[*] {tr('dedupe')}...          ", end="")
    all_blocks = dedupe_exact(all_blocks, keep_duplicates)
    all_blocks = move_keyword_blocks(all_blocks, keywords)
    print(f"\r[+] {tr('saving')}...          ")
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
        lines.append(f"=== {tr('unique_urls')} ===")
        lines.extend(sorted(urls))
        lines.append("")
    if show_stats:
        lines.append(f"=== {tr('per_file')} ===")
        for name, count in per_file_counts:
            lines.append(f"{name}: {count}")
        lines.append("")
    if keywords:
        lines.append(f"=== {tr('kw_blocks')} ===")
        lines.append(f"Keywords: {', '.join(keywords)}")
        lines.append("")
    lines.append(f"=== {tr('extracted_hdr')} ===")
    lines.append("")
    content = "\n\n".join(all_blocks)
    full_text = "\n".join(lines) + "\n" + content + "\n"
    save_text(out_path, full_text)
    print(f"[+] {tr('extract_done')}: {out_path}")
    print(f"[+] {tr('blocks')}: {len(all_blocks)}")
    return out_path

# ========================================
#  Блок: режим Compare (файлы)
# ========================================

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

def compare_mode(selected_files, show_urls, decode, show_diffs, include_blocks, keywords, keep_duplicates, sig_level):
    base = selected_files[0]
    others = selected_files[1:]
    recs = []
    total = len(selected_files)
    for idx, path in enumerate(selected_files, 1):
        print(f"\r[*] {tr('reading')} {idx}/{total}: {path.name}          ", end="")
        blocks = load_log_and_extract_blocks(path)
        if decode:
            blocks = [universal_decode_text(b) for b in blocks]
        records = build_records_from_blocks(blocks, path.name, decode, sig_level)
        recs.append((path.name, records))
    print(f"\r[+] {tr('reading')} OK          ")
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
    print(f"[+] {tr('extract_done')}: {out_path}")
    return out_path

# ========================================
#  Блок: режим Compare (группы)
# ========================================

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

def compare_groups(groups, show_urls, decode, show_diffs, include_blocks, keywords, keep_duplicates, sig_level):
    group_names = []
    group_records = []
    for idx, group in enumerate(groups, 1):
        name = f"Group_{idx}"
        print(f"\r[*] {tr('reading_grp')} {idx}/{len(groups)}...          ", end="")
        rec, _ = build_group_records(group, name, decode, keep_duplicates, sig_level)
        group_names.append(name)
        group_records.append(rec)
    print(f"\r[+] {tr('reading_grp')} OK          ")
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
    print(f"[+] {tr('extract_done')}: {out_path}")
    return out_path

# ========================================
#  Блок: переименование выходного файла
# ========================================

def rename_output_file(path):
    while True:
        ans = _input(f"\n[?] {tr('rename_out')} {path.name}? (y/n) [n]: ").strip().lower() or "n"
        if ans in ("n", "no"):
            return path
        if ans in ("y", "yes"):
            break
        print(f"[!] y/n")
    while True:
        new_name = _inp_allow_back(f"[?] {tr('new_name_short')}: ").strip()
        new_name = sanitize_filename(clean_str(new_name))
        if not new_name:
            print(f"[!] {tr('name_empty')}")
            continue
        new_path = path.parent / new_name
        if new_path.exists():
            print(f"[!] {tr('file_exists')}")
            continue
        break
    while True:
        confirm = _input(f"[?] {tr('rename_out')} {path.name} -> {new_name}? (y/n) [n]: ").strip().lower() or "n"
        if confirm == "y":
            path.rename(new_path)
            print(f"[+] {tr('renamed')} {new_name}")
            return new_path
        elif confirm == "n":
            return path
        else:
            print(f"[!] y/n")

# ========================================
#  Блок: переименование входных файлов
# ========================================

def rename_mode(files):
    while True:
        print_files(files)
        print(f"\n[?] {tr('rename_q')} [1]: ", end="")
        choice = _inp_allow_back().strip() or "1"
        if choice.lower() in ("b", "back"):
            return
        if choice == "1":
            selected = select_files(files, allow_multiple=False, prompt=tr("choose_one"))
            if selected is None:
                continue
            path = selected[0]
            while True:
                new_name = _inp_allow_back(f"[?] {tr('new_name')} {path.name}: ").strip()
                if new_name.lower() in ("b", "back"):
                    break
                new_name = sanitize_filename(clean_str(new_name))
                if not new_name:
                    print(f"[!] {tr('name_empty')}")
                    continue
                new_path = path.parent / new_name
                if new_path.exists():
                    print(f"[!] {tr('file_exists')}")
                    continue
                confirm = _input(f"[?] {tr('rename_out')} {path.name} -> {new_name}? (y/n) [n]: ").strip().lower() or "n"
                if confirm == "y":
                    path.rename(new_path)
                    print(f"[+] {tr('renamed')} {new_name}")
                    files = list_input_files()
                    break
                elif confirm == "n":
                    break
                else:
                    print(f"[!] y/n")
        elif choice == "2":
            prefix = sanitize_filename(clean_str(_inp_allow_back(f"[?] {tr('new_prefix')}: ").strip()))
            if not prefix:
                print(f"[!] {tr('prefix_empty')}")
                continue
            apply_all = _input(f"[?] {tr('apply_all')} [y]: ").strip().lower() or "y"
            if apply_all == "y":
                selected_files = files
            else:
                selected_files = select_files(files, allow_multiple=True, prompt=tr("choose_files"))
                if selected_files is None:
                    continue
            if not selected_files:
                print(f"[!] {tr('no_files_rename')}")
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
                print(f"[!] {tr('will_over')}:")
                for old, new in conflicts:
                    print(f"  {old.name} -> {new.name}")
                confirm = _input(f"[?] {tr('cont_q')} [n]: ").strip().lower()
                if confirm != "y":
                    print(f"[!] {tr('cancel')}")
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
            print(f"[!] {tr('bad')}")
            continue
        if _input(f"[?] {tr('cont_rename')} [n]: ").strip().lower() != "y":
            break

# ========================================
#  Блок: смена паттерна
# ========================================

def change_pattern():
    global SPY_PATTERN
    print(f"\n[+] {tr('pattern_cur')}: '{SPY_PATTERN.decode('utf-8', errors='ignore')}'")
    new = _inp_allow_back(f"[?] {tr('pattern_new')}: ").strip()
    if new:
        SPY_PATTERN = new.encode('utf-8')
        save_config()
        print(f"[+] {tr('pattern_ok')} '{new}'")
    else:
        print(f"[!] {tr('pattern_cancel')}")

# ========================================
#  Блок: очистка папок
# ========================================

def clean_broken_files():
    print(f"\n=== {tr('clean_hdr')} ===")
    print(tr("clean_1"))
    print(tr("clean_2"))
    print(tr("clean_3"))
    print(tr("clean_4"))
    print(tr("clean_5"))
    choice = _input(f"[?] {tr('choice')} [5]: ").strip() or "5"
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
                print(f"[!] {tr('folder_missing')}: {d}")
                continue
            if _input(f"[?] {tr('del_all')} {d}? ({tr('y_or_n')}) [n]: ").strip().lower() == "y":
                for item in d.iterdir():
                    try:
                        if item.is_dir():
                            shutil.rmtree(item)
                        else:
                            item.unlink()
                    except Exception as e:
                        print(f"[!] {item}: {e}")
                print(f"[+] {tr('folder_ok')}: {d}")
            else:
                print(f"[!] {tr('skipped')}: {d}")
        return
    if choice == "4":
        print(f"\n[+] {tr('bad_found')}...")
        bad_files = []
        for d in [INPUT_DIR, OUTPUT_DIR]:
            if not d.exists():
                continue
            for item in d.iterdir():
                name = item.name
                if re.search(r'[^a-zA-Z0-9_.\-]', name):
                    bad_files.append(item)
        if not bad_files:
            print(f"[+] {tr('no_bad')}")
            return
        print(f"[+] {tr('bad_found')}: {len(bad_files)}")
        for i, p in enumerate(bad_files, 1):
            size = p.stat().st_size if p.is_file() else 0
            print(f"{i}. {p.name} ({size} bytes)")
        if _input(f"\n[?] {tr('del_all_bad')} [n]: ").strip().lower() == "y":
            for p in bad_files:
                try:
                    if p.is_dir():
                        shutil.rmtree(p)
                    else:
                        p.unlink()
                    print(f"[+] {tr('deleted')}: {p.name}")
                except Exception as e:
                    print(f"[!] {p.name}: {e}")
            print(f"[+] {tr('deleted_all')}")
        return
    print(f"[!] {tr('bad')}")

# ========================================
#  Блок: обработка пустой папки
# ========================================

def handle_empty_input():
    print(f"\n[!] {tr('empty_hdr')}.")
    print(f"[*] {tr('how_get_logs')} {INPUT_DIR}")
    print(f"[*] {tr('press')}")
    print(f"[*] {tr('empty_or')}")
    print(f"[*] {tr('empty_or_module')}")
    cmd = _inp_allow_back().strip().lower()
    if cmd == "m":
        fetch_spy_module()
        print(f"\n[*] {tr('no_input_after_module')}: {INPUT_DIR}")
        _inp_allow_back(f"[*] {tr('press')}")
        return "module"
    if cmd in ("q", "quit", "exit"):
        print("[+] " + tr("exit"))
        sys.exit(0)
    return "retry"

# ========================================
#  Блок: главное меню
# ========================================

def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    while True:
        files = list_input_files()
        while not files:
            result = handle_empty_input()
            if result == "module":
                files = list_input_files()
                if not files:
                    continue
            files = list_input_files()
        print(f"\n{tr('m_1')}")
        print(tr("m_2"))
        print(tr("m_3"))
        print(tr("m_4"))
        print(tr("m_5"))
        print(tr("m_6"))
        print(tr("m_q"))
        mode = _input(f"\n[?] {tr('menu')} (1/2/3/4/5/6/q) [1]: ").strip() or "1"
        if mode in ("q", "quit", "exit"):
            print("[+] " + tr("exit"))
            break
        if mode == "6":
            fetch_spy_module()
            _inp_allow_back("\n" + tr("press"))
            continue
        if mode == "5":
            clean_broken_files()
            continue
        if mode == "4":
            change_pattern()
            continue
        if mode == "3":
            rename_mode(files)
            continue
        if mode not in ("1", "2"):
            print(f"[!] {tr('bad')}")
            continue
        if mode == "1":
            opts, keywords = ask_options("extract")
            selected = ask_files(files, compare=False)
            if selected is None:
                continue
            out_path = extract_mode(selected, opts[0], opts[1], opts[2], keywords, opts[4])
            rename_output_file(out_path)
        else:
            print(f"\n[?] {tr('cmp_type')} [1]: ", end="")
            cmp_type = _inp_allow_back().strip() or "1"
            if cmp_type == "1":
                selected = ask_files(files, compare=True)
                if selected is None or len(selected) < 2:
                    print(f"[!] {tr('cmp_min')}")
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
                print(f"[!] {tr('bad')}")
                continue
        print(f"\n[+] {tr('done_continue')}")
        _inp_allow_back(f"[*] {tr('press')}")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n[+] " + tr("exit"))
        sys.exit(0)
SPYLOG_END
fi

# ========================================
#  Скрипт 4/5: SubManager.py
# ========================================
if [ "$REGEN_PY" = "1" ] || [ ! -s "$BASE/SubManager.py" ]; then
cat << 'SUBMGR_END' > "$BASE/SubManager.py"
# ========================================
#  SubManager: подписки + генерация Xray JSON
# ========================================

import os, sys, re, json, base64, urllib.request, ssl, subprocess, shutil, time, random, copy, ipaddress
from urllib.parse import urlparse, parse_qs, urlencode, unquote, quote
from pathlib import Path

os.umask(0o077)

# --- Загрузка языка ---
LANG = os.environ.get("LANG_SEL", "").strip()
if not LANG:
    try:
        with open(os.path.expanduser("~/.sr_toolkit_lang")) as _f:
            LANG = _f.read().strip()
    except Exception:
        LANG = "ru"
if LANG not in ("ru", "en"):
    LANG = "ru"

# --- Словарь переводов ---
_T = {
"ru": {
"exit":"Выход.",
"allowed":"Допустимо","number":"Введите число","fmt_all":"Формат: 1,3-5 или all",
"empty":"Пусто",
"load_src":"ЗАГРУЗКА ИСХОДНИКОВ","load_1":"1 - Локальный файл","load_2":"2 - По ссылке (URL)","load_3":"3 - Несколько ссылок подряд",
"q_back":"q - Назад","choice":"Ваш выбор","folder_empty":"Папка пуста","put_file":"Поместите файл в",
"file_n":"Номер файла","url_sub":"URL подписки","dl_fail":"Не удалось загрузить",
"enter_urls":"Вводите URL по одному. q - завершить.","url_q":"URL (q - конец)","added":"Добавлено. Всего частей",
"merged":"Объединено частей",
"xray_detected":"Обнаружен Xray JSON конфиг. Извлечено outbounds",
"singbox_detected":"Обнаружены sing-box-объекты",
"links_found":"Найдено ссылок","parsed":"распарсено",
"parse_fail":"Не удалось распарсить данные.",
"dedupe_hdr":"ДЕДУПЛИКАЦИЯ","d_full":"1 - Полное сходство","d_name":"2 - По имени","d_addr":"3 - По адресу",
"d_user":"4 - По адресу и пользователю","d_proto":"5 - По протоколу + адрес + порт","dedupe_removed":"Удалено дубликатов","dedupe_none":"Дубликатов нет.",
"del_hdr":"УДАЛЕНИЕ СЕРВЕРОВ","del_1":"1 - По имени","del_2":"2 - По протоколу","del_3":"3 - По транспорту",
"del_4":"4 - По security","del_5":"5 - По домену","del_6":"6 - По номерам","del_7":"7 - Инвертировать",
"words_csv":"Слова через запятую","proto_l":"Протокол","transport":"Транспорт","security":"Security","domain":"Домен",
"numbers":"Номера","kw_inv":"Ключевые слова для ИНВЕРТА","not_found":"Ничего не найдено.","found":"Найдено",
"delete_q":"Удалить? (y/n)","deleted_n":"Удалено",
"sort_hdr":"СОРТИРОВКА","s_az":"1 - По имени (A-Z)","s_za":"2 - По имени (Z-A)","s_proto":"3 - По протоколу",
"s_host":"4 - По хосту","s_port":"5 - По порту","s_rand":"6 - Случайно","sorted":"Отсортировано.",
"move_n":"Номер сервера для перемещения","direction":"Направление (u=вверх / d=вниз)","moved_up":"Перемещён вверх.",
"moved_dn":"Перемещён вниз.","no_move":"Некуда двигать.",
"dup_n":"Номера для дублирования","dup_created":"Создано дубликатов","edit_q":"Отредактировать? (y/n)",
"edit_grp":"РЕДАКТИРОВАНИЕ ГРУППЫ","sel_servers":"Выбрано серверов",
"edit_hdr":"РЕДАКТИРОВАНИЕ СЕРВЕРОВ","e1":"1 - Имена","e2":"2 - Параметры (группа)","e3":"3 - Удалить по номерам",
"e4":"4 - Удалить по фильтру","e5":"5 - Добавить сервер вручную","e6":"6 - Удалить дубликаты","e7":"7 - Сортировка",
"e8":"8 - Переместить сервер","e9":"9 - Создать дубликаты","e10":"10 - Поиск по ключевому слову",
"e11":"11 - Показать параметры сервера","eq":"q - Готово",
"names_q":"1-Все с суффиксами / 2-Группу / 3-По одному / 4-Добавить префикс / q-назад",
"base_name":"Базовое имя","prefix":"Префикс","skip_q":"(q-пропустить)","updated":"Обновлено.",
"del_q":"Номера для удаления","del_n":"Удалить сервер(ов)","link_q":"Ссылка","added_ok":"Добавлен.","parse_err":"Не удалось распарсить.",
"kw_q":"Ключевое слово","params_of":"Параметры сервера","u_scheme":"Scheme","u_host":"Host","u_port":"Port",
"u_cred":"ID/Pass/Method","u_params":"Params",
"change":"ИЗМЕНЕНИЕ","compat":"Совместимых","will_change":"Будут изменены","incompat":"Несовместимых",
"default_val":"Значение по умолчанию","enter_default":"Enter = применить значение по умолчанию",
"minus_del":"'-' = удалить параметр","q_cancel":"q = отмена","new_val":"Новое значение",
"list_empty":"Список пуст.","no_servers":"Нет серверов.",
"missing_unsupported":"Пропущены неподдерживаемые Xray протоколы",
"exp_gt":"больше числа серверов. Установлено",
"norm_hdr":"НОРМАЛИЗАЦИЯ СУЩЕСТВУЮЩЕГО КОНФИГА","n_from_out":"1 - Из папки Output","n_from_in":"2 - Из папки Input",
"n_manual":"3 - Ввести путь вручную","no_json_out":"В Output нет JSON файлов.","no_json_in":"В Input нет JSON файлов.",
"path_q":"Путь к файлу","file_not_found":"Файл не найден","read_err":"Ошибка чтения JSON",
"norm_nochange":"Конфиг уже корректен, изменений не требуется.","norm_found":"Найдено исправлений",
"norm_save":"Сохранить исправленный файл? (y/n)","norm_saved":"Сохранено",
"n_serv_hdr":"НОРМАЛИЗАЦИЯ БЭКАПА СЕРВЕРОВ","n1":"1 - Из папки Backups","n2":"2 - Из папки Output",
"n3":"3 - Из папки Input","n4":"4 - Ввести путь вручную","no_files":"Нет файлов.",
"serv_parsed":"Распарсено серверов","serv_valid":"Валидных","serv_dropped":"Отброшено некорректных",
"serv_save_norm":"Сохранить нормализованный список? (y/n)",
"imp_hdr":"ИМПОРТ ПРАВИЛ МАРШРУТИЗАЦИИ","imp_1":"1 - Shadowrocket / Clash / Surge","imp_2":"2 - AdGuard",
"imp_3":"3 - Blocklist без политики","imp_src_1":"1 - Из локального файла","imp_src_2":"2 - По ссылке",
"imp_rules":"Найдено правил","imp_add":"Добавить правил","imp_added":"Добавлено. Всего",
"rt_hdr":"РОУТИНГ ДЛЯ КЛИЕНТОВ","rt_direct":"Direct домены","rt_block":"Block домены","rt_dip":"Direct IP","rt_bip":"Block IP",
"rt_cr":"Custom rules","rt_order":"Порядок","rt_global":"Глобальный",
"rt_1":"1 - Импорт правил","rt_2":"2 - Просмотр/очистка custom rules","rt_3":"3 - Настроить DNS для роутинга",
"rt_4":"4 - Настроить порядок правил","rt_5":"5 - Настроить глобальный прокси","rt_6":"6 - Сгенерировать happ ссылку",
"rt_7":"7 - Сгенерировать v2raytun ссылку","rt_8":"8 - Сохранить JSON роутинга",
"cr_empty":"Нет custom rules.","clear_all":"Очистить все","del_by_n":"Удалить по номерам",
"clear_q":"Точно удалить все? (y/n)","cleared":"Очищено.",
"dns_remote":"Remote DNS domain","dns_local":"Domestic DNS domain",
"order_q":"Порядок (block,direct,proxy)","saved":"Сохранено.","need_all_three":"Нужно указать все три.",
"global_q":"Глобальный прокси",
"happ_saved":"Happ routing","v2r_saved":"v2RayTun routing","rt_json":"JSON роутинга",
"cfg_hdr":"НАСТРОЙКИ ГЕНЕРАЦИИ","cfg_jname":"JSON имя файла","cfg_jrem":"JSON примечание",
"cfg_dns":"DNS","cfg_dns_strat":"DNS стратегия","cfg_probe":"Probe URL","cfg_int":"Interval","cfg_to":"Timeout",
"cfg_bal":"Balancer","cfg_ports":"Порты","cfg_mux":"Mux","cfg_global":"Глобальный","cfg_sniff":"Sniffing",
"cfg_order":"Порядок правил","cfg_cr":"Custom rules",
"cfg_1":"1 - DNS (серверы и стратегия)","cfg_2":"2 - Обсерватория","cfg_3":"3 - Балансировщик",
"cfg_4":"4 - Порты SOCKS/HTTP","cfg_5":"5 - Direct домены","cfg_6":"6 - Block домены","cfg_7":"7 - Direct/Block IP",
"cfg_8":"8 - Block протоколы","cfg_9":"9 - Порядок применения правил","cfg_10":"10 - Импорт правил",
"cfg_11":"11 - Просмотр/очистка custom rules","cfg_12":"12 - Глобальный прокси","cfg_13":"13 - Mux / XUDP",
"cfg_14":"14 - Sniffing","cfg_15":"15 - Имя JSON файла","cfg_16":"16 - Примечание JSON-сервера",
"cfg_17":"17 - Сбросить к дефолту",
"dns_csv":"DNS через запятую","strategy":"Стратегия","dns_url":"URL","interval":"Интервал","timeout":"Таймаут",
"maxrtt":"MaxRTT","tolerance":"Tolerance","baselines":"Baselines","expected":"Expected",
"socks":"SOCKS","http":"HTTP","cur":"Текущие","hints":"Подсказки","direct_d":"Direct домены (через запятую, пусто=очистить, q=отмена)",
"block_d":"Block домены (через запятую, пусто=очистить, q=отмена)","direct_ip":"Direct IP","block_ip":"Block IP",
"protos":"Протоколы (через запятую, пусто=очистить, q=отмена)",
"mux_on":"Включить Mux? (y/n/q)","concurrency":"Concurrency","xudp_c":"XUDP concurrency","xudp_p":"XUDP proxyUDP443",
"dest_over":"DestOverride","route_only":"RouteOnly",
"jname_q":"Имя JSON файла","jrem_q":"Новое примечание","as_fname":"Использовать как имя файла? (y/n)",
"reset_q":"Сбросить все настройки? (y/n)","reset_done":"Сброшено.",
"exp_sel_hdr":"ЭКСПОРТ ВЫБРАННЫХ СЕРВЕРОВ","exp_1":"1 - Экспорт ссылок (txt + base64)","exp_2":"2 - Экспорт JSON Xray",
"exp_sel_n":"Номера серверов для экспорта (1,3-5,all)","exp_name":"Имя файла (без расширения)",
"exp_json_name":"Имя JSON","exp_rem":"Примечание сервера",
"links_saved":"Ссылки","b64_saved":"Base64","str_count":"Строк",
"jname_cfg":"Настройка имени JSON-сервера","jname_cur":"Текущее имя файла","jrem_cur":"Текущее примечание",
"jenter_keep":"(Enter - оставить текущие, q - отмена)","jchange_q":"Изменить имя/примечание? (y/n)",
"jrem_new":"Примечание сервера","jname_auto":"Использовать примечание как имя файла (транслитом)? (y/n)",
"jname_will":"Имя файла будет","jname_noext":"Имя файла (без .json)",
"backup_ok":"Backup","stat_hdr":"СТАТИСТИКА","no_serv":"Серверов нет.","total_serv":"Всего серверов",
"by_proto":"По протоколу","by_transp":"По транспорту","by_sec":"По security",
"uje_hdr":"УНИВЕРСАЛЬНЫЙ РЕДАКТОР JSON","uje_1":"1 - Открыть из Input","uje_2":"2 - Открыть из Output",
"uje_3":"3 - Ввести путь вручную","uje_4":"4 - Создать новый JSON",
"uje_field_hdr":"ДОБАВЛЕНИЕ ПОЛЯ","uje_sugg":"Рекомендуемые поля (отсутствующие)",
"uje_pick_sugg":"1 - Выбрать из рекомендаций","uje_pick_own":"2 - Ввести своё имя",
"uje_field_name":"Имя поля","uje_exists":"Поле уже существует",
"uje_type_q":"Тип поля: 1-строка, 2-список, 3-объект, 4-true/false","uje_type":"Тип",
"uje_val":"Значение","uje_elem":"Элемент (Enter - конец)","uje_key":"Ключ (Enter - конец)","uje_key_n":"Ключ","uje_val_n":"Значение",
"uje_added":"Добавлено поле",
"uje_editor_hdr":"УНИВЕРСАЛЬНЫЙ РЕДАКТОР JSON","uje_file":"Файл",
"uje_a":"a - Добавить новое поле","uje_s":"s - Сохранить","uje_b":"b - Создать бэкап",
"uje_v":"v - Показать JSON полностью","uje_o":"o - Сохранить как","uje_q":"q - Выход",
"uje_saved":"Сохранено","uje_backup":"Бэкап","uje_exp":"Экспортировано",
"uje_list_hdr":"СПИСОК","uje_dict_hdr":"ОБЪЕКТ","uje_elems":"Элементов","uje_keys":"Записей",
"uje_l1":"1 - Добавить элемент","uje_l2":"2 - Удалить по номеру","uje_l3":"3 - Удалить несколько",
"uje_l4":"4 - Очистить всё","uje_l5":"5 - Заменить значение по номеру","uje_l6":"6 - Удалить поле полностью",
"uje_d1":"1 - Добавить запись","uje_d2":"2 - Изменить запись","uje_d3":"3 - Удалить запись",
"uje_d4":"4 - Удалить поле полностью","uje_back":"q - Назад",
"uje_del_n":"Номер","uje_del_multi":"Номера (например 1,3-5)","uje_del_range":"Удалено",
"uje_del_all_q":"Очистить всё? (y/n)","uje_del_all":"Очищено","uje_rep_n":"Номер для замены",
"uje_del_field_q":"Удалить поле полностью? (y/n)","uje_del_field":"Поле удалено","uje_deleted":"Удалено",
"uje_new_val":"Новое значение","uje_cur_val":"Текущее значение","uje_updated":"Обновлено","uje_replaced":"Заменено",
"uje_cur":"Текущее","uje_edit_hint":"(Enter=оставить, '-'=удалить, q=отмена)","uje_nochange":"Без изменений",
"uje_parse_err":"Ошибка разбора",
"uje_all_have":"Все рекомендуемые поля уже есть.",
"uje_file_in":"В Input нет JSON.","uje_file_out":"В Output нет JSON.",
"uje_root_not_obj":"Корень JSON не является объектом.",
"gname_hdr":"ГЛАВНОЕ МЕНЮ","g_serv":"Серверов","g_json":"Загружен JSON шаблон",
"g1":"1 - Загрузить исходники","g2":"2 - Редактировать серверы","g3":"3 - Показать список серверов",
"g4":"4 - Статистика","g5":"5 - JSON: настройки и редактор","g6":"6 - Сгенерировать JSON Xray",
"g7":"7 - Роутинг для клиентов","g8":"8 - Экспорт выбранных серверов",
"g9":"9 - Сохранить ссылки (txt + base64)","g10":"10 - Сохранить Clash YAML","g11":"11 - Сделать бэкап",
"g12":"12 - Нормализовать существующий конфиг","g13":"13 - Нормализовать бэкап серверов",
"g14":"14 - Очистить автосохранение","gq":"q - Выход",
"backup_before":"Сделать бэкап перед выходом? (y/n)","autosave":"Автосохранение",
"list_hdr":"СПИСОК СЕРВЕРОВ","total":"Всего",
"load_ok":"Загружено. Всего","no_servers_list":"Список пуст.","parse_data":"Не удалось распарсить данные.",
"autoload":"Автозагрузка прошлой сессии",
"json_menu_hdr":"JSON: НАСТРОЙКИ И РЕДАКТОР",
"json_m1":"1 - Настройки генерации","json_m2":"2 - Универсальный редактор JSON",
"json_m3":"3 - Быстрый просмотр активного config.json",
"cur_auto":"Автосохранения нет.","del_auto":"Удалить автосохранение? (y/n)"
},
"en": {
"exit":"Exit.",
"allowed":"Allowed","number":"Enter a number","fmt_all":"Format: 1,3-5 or all",
"empty":"Empty",
"load_src":"LOAD SOURCES","load_1":"1 - Local file","load_2":"2 - By URL","load_3":"3 - Multiple URLs",
"q_back":"q - Back","choice":"Choice","folder_empty":"Folder is empty","put_file":"Put file into",
"file_n":"File number","url_sub":"Subscription URL","dl_fail":"Failed to load",
"enter_urls":"Enter URLs one by one. q - finish.","url_q":"URL (q - end)","added":"Added. Total parts",
"merged":"Merged parts",
"xray_detected":"Xray JSON detected. Outbounds extracted",
"singbox_detected":"sing-box objects detected",
"links_found":"Links found","parsed":"parsed",
"parse_fail":"Failed to parse data.",
"dedupe_hdr":"DEDUPLICATION","d_full":"1 - Full match","d_name":"2 - By name","d_addr":"3 - By address",
"d_user":"4 - By address and user","d_proto":"5 - By protocol + address + port","dedupe_removed":"Duplicates removed","dedupe_none":"No duplicates.",
"del_hdr":"DELETE SERVERS","del_1":"1 - By name","del_2":"2 - By protocol","del_3":"3 - By transport",
"del_4":"4 - By security","del_5":"5 - By domain","del_6":"6 - By numbers","del_7":"7 - Invert",
"words_csv":"Comma-separated words","proto_l":"Protocol","transport":"Transport","security":"Security","domain":"Domain",
"numbers":"Numbers","kw_inv":"Keywords to INVERT","not_found":"Nothing found.","found":"Found",
"delete_q":"Delete? (y/n)","deleted_n":"Deleted",
"sort_hdr":"SORT","s_az":"1 - By name (A-Z)","s_za":"2 - By name (Z-A)","s_proto":"3 - By protocol",
"s_host":"4 - By host","s_port":"5 - By port","s_rand":"6 - Random","sorted":"Sorted.",
"move_n":"Server number to move","direction":"Direction (u=up / d=down)","moved_up":"Moved up.",
"moved_dn":"Moved down.","no_move":"Nothing to move.",
"dup_n":"Numbers to duplicate","dup_created":"Created duplicates","edit_q":"Edit? (y/n)",
"edit_grp":"EDIT GROUP","sel_servers":"Servers selected",
"edit_hdr":"EDIT SERVERS","e1":"1 - Names","e2":"2 - Parameters (group)","e3":"3 - Delete by numbers",
"e4":"4 - Delete by filter","e5":"5 - Add server manually","e6":"6 - Remove duplicates","e7":"7 - Sort",
"e8":"8 - Move server","e9":"9 - Duplicate","e10":"10 - Search by keyword",
"e11":"11 - Show server parameters","eq":"q - Done",
"names_q":"1-All with suffixes / 2-Group / 3-One by one / 4-Add prefix / q-back",
"base_name":"Base name","prefix":"Prefix","skip_q":"(q-skip)","updated":"Updated.",
"del_q":"Numbers to delete","del_n":"Delete server(s)","link_q":"Link","added_ok":"Added.","parse_err":"Failed to parse.",
"kw_q":"Keyword","params_of":"Server parameters","u_scheme":"Scheme","u_host":"Host","u_port":"Port",
"u_cred":"ID/Pass/Method","u_params":"Params",
"change":"CHANGE","compat":"Compatible","will_change":"Will change","incompat":"Incompatible",
"default_val":"Default value","enter_default":"Enter = apply default",
"minus_del":"'-' = remove parameter","q_cancel":"q = cancel","new_val":"New value",
"list_empty":"List empty.","no_servers":"No servers.",
"missing_unsupported":"Unsupported Xray protocols skipped",
"exp_gt":"greater than server count. Set to",
"norm_hdr":"NORMALIZE EXISTING CONFIG","n_from_out":"1 - From Output","n_from_in":"2 - From Input",
"n_manual":"3 - Enter path manually","no_json_out":"No JSON files in Output.","no_json_in":"No JSON files in Input.",
"path_q":"Path to file","file_not_found":"File not found","read_err":"Error reading JSON",
"norm_nochange":"Config already correct, no changes needed.","norm_found":"Fixes found",
"norm_save":"Save fixed file? (y/n)","norm_saved":"Saved",
"n_serv_hdr":"NORMALIZE SERVERS BACKUP","n1":"1 - From Backups","n2":"2 - From Output",
"n3":"3 - From Input","n4":"4 - Enter path manually","no_files":"No files.",
"serv_parsed":"Servers parsed","serv_valid":"Valid","serv_dropped":"Invalid dropped",
"serv_save_norm":"Save normalized list? (y/n)",
"imp_hdr":"IMPORT ROUTING RULES","imp_1":"1 - Shadowrocket / Clash / Surge","imp_2":"2 - AdGuard",
"imp_3":"3 - Blocklist without policy","imp_src_1":"1 - From local file","imp_src_2":"2 - By URL",
"imp_rules":"Rules found","imp_add":"Add rules","imp_added":"Added. Total",
"rt_hdr":"CLIENT ROUTING","rt_direct":"Direct domains","rt_block":"Block domains","rt_dip":"Direct IP","rt_bip":"Block IP",
"rt_cr":"Custom rules","rt_order":"Order","rt_global":"Global",
"rt_1":"1 - Import rules","rt_2":"2 - View/clear custom rules","rt_3":"3 - Configure routing DNS",
"rt_4":"4 - Configure rule order","rt_5":"5 - Configure global proxy","rt_6":"6 - Generate happ link",
"rt_7":"7 - Generate v2raytun link","rt_8":"8 - Save routing JSON",
"cr_empty":"No custom rules.","clear_all":"Clear all","del_by_n":"Delete by numbers",
"clear_q":"Really clear all? (y/n)","cleared":"Cleared.",
"dns_remote":"Remote DNS domain","dns_local":"Domestic DNS domain",
"order_q":"Order (block,direct,proxy)","saved":"Saved.","need_all_three":"All three required.",
"global_q":"Global proxy",
"happ_saved":"Happ routing","v2r_saved":"v2RayTun routing","rt_json":"Routing JSON",
"cfg_hdr":"GENERATION SETTINGS","cfg_jname":"JSON file name","cfg_jrem":"JSON remark",
"cfg_dns":"DNS","cfg_dns_strat":"DNS strategy","cfg_probe":"Probe URL","cfg_int":"Interval","cfg_to":"Timeout",
"cfg_bal":"Balancer","cfg_ports":"Ports","cfg_mux":"Mux","cfg_global":"Global","cfg_sniff":"Sniffing",
"cfg_order":"Rule order","cfg_cr":"Custom rules",
"cfg_1":"1 - DNS (servers and strategy)","cfg_2":"2 - Observatory","cfg_3":"3 - Balancer",
"cfg_4":"4 - SOCKS/HTTP ports","cfg_5":"5 - Direct domains","cfg_6":"6 - Block domains","cfg_7":"7 - Direct/Block IP",
"cfg_8":"8 - Block protocols","cfg_9":"9 - Rule application order","cfg_10":"10 - Import rules",
"cfg_11":"11 - View/clear custom rules","cfg_12":"12 - Global proxy","cfg_13":"13 - Mux / XUDP",
"cfg_14":"14 - Sniffing","cfg_15":"15 - JSON file name","cfg_16":"16 - JSON server remark",
"cfg_17":"17 - Reset to default",
"dns_csv":"DNS comma-separated","strategy":"Strategy","dns_url":"URL","interval":"Interval","timeout":"Timeout",
"maxrtt":"MaxRTT","tolerance":"Tolerance","baselines":"Baselines","expected":"Expected",
"socks":"SOCKS","http":"HTTP","cur":"Current","hints":"Hints","direct_d":"Direct domains (comma, empty=clear, q=cancel)",
"block_d":"Block domains (comma, empty=clear, q=cancel)","direct_ip":"Direct IP","block_ip":"Block IP",
"protos":"Protocols (comma, empty=clear, q=cancel)",
"mux_on":"Enable Mux? (y/n/q)","concurrency":"Concurrency","xudp_c":"XUDP concurrency","xudp_p":"XUDP proxyUDP443",
"dest_over":"DestOverride","route_only":"RouteOnly",
"jname_q":"JSON file name","jrem_q":"New remark","as_fname":"Use as file name? (y/n)",
"reset_q":"Reset all settings? (y/n)","reset_done":"Reset.",
"exp_sel_hdr":"EXPORT SELECTED SERVERS","exp_1":"1 - Export links (txt + base64)","exp_2":"2 - Export JSON Xray",
"exp_sel_n":"Server numbers to export (1,3-5,all)","exp_name":"File name (no extension)",
"exp_json_name":"JSON name","exp_rem":"Server remark",
"links_saved":"Links","b64_saved":"Base64","str_count":"Lines",
"jname_cfg":"JSON server name setup","jname_cur":"Current file name","jrem_cur":"Current remark",
"jenter_keep":"(Enter - keep current, q - cancel)","jchange_q":"Change name/remark? (y/n)",
"jrem_new":"Server remark","jname_auto":"Use remark as file name (transliterated)? (y/n)",
"jname_will":"File name will be","jname_noext":"File name (without .json)",
"backup_ok":"Backup","stat_hdr":"STATISTICS","no_serv":"No servers.","total_serv":"Total servers",
"by_proto":"By protocol","by_transp":"By transport","by_sec":"By security",
"uje_hdr":"UNIVERSAL JSON EDITOR","uje_1":"1 - Open from Input","uje_2":"2 - Open from Output",
"uje_3":"3 - Enter path manually","uje_4":"4 - Create new JSON",
"uje_field_hdr":"ADD FIELD","uje_sugg":"Suggested fields (missing)",
"uje_pick_sugg":"1 - Choose from suggestions","uje_pick_own":"2 - Enter custom name",
"uje_field_name":"Field name","uje_exists":"Field already exists",
"uje_type_q":"Field type: 1-string, 2-list, 3-object, 4-true/false","uje_type":"Type",
"uje_val":"Value","uje_elem":"Element (Enter - finish)","uje_key":"Key (Enter - finish)","uje_key_n":"Key","uje_val_n":"Value",
"uje_added":"Field added",
"uje_editor_hdr":"UNIVERSAL JSON EDITOR","uje_file":"File",
"uje_a":"a - Add new field","uje_s":"s - Save","uje_b":"b - Create backup",
"uje_v":"v - Show full JSON","uje_o":"o - Save as","uje_q":"q - Exit",
"uje_saved":"Saved","uje_backup":"Backup","uje_exp":"Exported",
"uje_list_hdr":"LIST","uje_dict_hdr":"OBJECT","uje_elems":"Elements","uje_keys":"Entries",
"uje_l1":"1 - Add element","uje_l2":"2 - Delete by number","uje_l3":"3 - Delete several",
"uje_l4":"4 - Clear all","uje_l5":"5 - Replace value by number","uje_l6":"6 - Delete field entirely",
"uje_d1":"1 - Add entry","uje_d2":"2 - Edit entry","uje_d3":"3 - Delete entry",
"uje_d4":"4 - Delete field entirely","uje_back":"q - Back",
"uje_del_n":"Number","uje_del_multi":"Numbers (e.g. 1,3-5)","uje_del_range":"Deleted",
"uje_del_all_q":"Clear all? (y/n)","uje_del_all":"Cleared","uje_rep_n":"Number to replace",
"uje_del_field_q":"Delete field entirely? (y/n)","uje_del_field":"Field deleted","uje_deleted":"Deleted",
"uje_new_val":"New value","uje_cur_val":"Current value","uje_updated":"Updated","uje_replaced":"Replaced",
"uje_cur":"Current","uje_edit_hint":"(Enter=keep, '-'=delete, q=cancel)","uje_nochange":"No change",
"uje_parse_err":"Parse error",
"uje_all_have":"All suggested fields already present.",
"uje_file_in":"No JSON in Input.","uje_file_out":"No JSON in Output.",
"uje_root_not_obj":"JSON root is not an object.",
"gname_hdr":"MAIN MENU","g_serv":"Servers","g_json":"JSON template loaded",
"g1":"1 - Load sources","g2":"2 - Edit servers","g3":"3 - Show server list",
"g4":"4 - Statistics","g5":"5 - JSON: settings and editor","g6":"6 - Generate JSON Xray",
"g7":"7 - Client routing","g8":"8 - Export selected servers",
"g9":"9 - Save links (txt + base64)","g10":"10 - Save Clash YAML","g11":"11 - Make backup",
"g12":"12 - Normalize existing config","g13":"13 - Normalize servers backup",
"g14":"14 - Clear autosave","gq":"q - Quit",
"backup_before":"Make backup before exit? (y/n)","autosave":"Autosave",
"list_hdr":"SERVER LIST","total":"Total",
"load_ok":"Loaded. Total","no_servers_list":"List empty.","parse_data":"Failed to parse data.",
"autoload":"Autoload from previous session",
"json_menu_hdr":"JSON: SETTINGS AND EDITOR",
"json_m1":"1 - Generation settings","json_m2":"2 - Universal JSON editor",
"json_m3":"3 - Quick view of active config.json",
"cur_auto":"No autosave.","del_auto":"Delete autosave? (y/n)"
}}

def tr(k):
    return _T.get(LANG, _T["ru"]).get(k, _T["ru"].get(k, k))

EXIT = "__EXIT__"

# --- Безопасный ввод ---
def _in(prompt="", default=None, allow_exit=True):
    while True:
        try:
            v = input(prompt).strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return EXIT if allow_exit else default
        if allow_exit and v.lower() in ("q", "quit", "exit"):
            return EXIT
        if not v and default is not None:
            return default
        return v

def _in_int(prompt, default=None, mn=None, mx=None):
    while True:
        v = _in(prompt, default)
        if v == EXIT:
            return EXIT
        try:
            n = int(v)
            if mn is not None and n < mn:
                print(f"[!] >= {mn}"); continue
            if mx is not None and n > mx:
                print(f"[!] <= {mx}"); continue
            return n
        except ValueError:
            print(f"[!] {tr('number')}")

def _in_multi(prompt, mn, mx):
    while True:
        v = _in(prompt)
        if v == EXIT:
            return EXIT
        if not v:
            return None
        if v.lower() in ("all", "a", "*"):
            return list(range(mn, mx + 1))
        try:
            out = []
            for p in v.split(','):
                p = p.strip()
                if '-' in p:
                    a, b = p.split('-', 1)
                    a, b = int(a), int(b)
                    if a > b: a, b = b, a
                    for x in range(a, b + 1):
                        if mn <= x <= mx and x not in out: out.append(x)
                else:
                    x = int(p)
                    if mn <= x <= mx and x not in out: out.append(x)
            if out: return out
            print(f"[!] {tr('empty')}")
        except Exception:
            print(f"[!] {tr('fmt_all')}")

def _in_choice(prompt, choices):
    while True:
        v = _in(prompt)
        if v == EXIT:
            return EXIT
        if v.lower() in [c.lower() for c in choices]:
            return v
        print(f"[!] {tr('allowed')}: {', '.join(choices)}")

# --- Пути ---
HOME = Path.home()
BASE = HOME / "Shadowrocket" / "SubManager"
INPUT_DIR = BASE / "Input"
OUTPUT_DIR = BASE / "Output"
BACKUP_DIR = BASE / "Backups"
ROUTING_DIR = BASE / "Routing"
CFG_FILE = BASE / "config.json"
AUTOSAVE_FILE = BACKUP_DIR / "autosave_servers.txt"
UA = "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1"
W = 40
DNS_SERVERS = ["8.8.8.8","8.8.4.4","1.1.1.1","94.140.14.14","94.140.15.15"]

# --- Утилиты нормализации ---
DURATION_RE = re.compile(r'^(\d+(?:\.\d+)?)(ms|s|m|h|d)?$')
DURATION_UNITS = {'ms','s','m','h','d'}
BALANCER_TYPES = {"leastload":"leastLoad","leastping":"leastPing","random":"random","roundrobin":"roundRobin"}
TLD_ONLY = {'ru','su','by','kz','xn--p1ai','рф'}

PARAM_DEFAULTS = {
"scheme":"vless","type":"tcp","security":"reality","flow":"xtls-rprx-vision","path":"/","host":"","sni":"","pbk":"","sid":"","fp":"chrome",
"serviceName":"","authority":"","mode":"auto","port":"443","host_addr":"","alpn":"h2","obfs":"salamander","obfs-password":"","id":"","password":"",
"method":"aes-256-gcm","concurrency":"4","spiderX":"/","headerType":"none","heartbeatPeriod":"0","alterId":"0","encryption":"auto",
"allowedIPs":"0.0.0.0/0","mtu":"1420","dns":"1.1.1.1","presharedKey":"","keepalive":"0","up":"","down":"","congestion_control":"cubic",
"pinned_certchain_sha256":"","verify_peer_cert_by_name":"",
"jc":"4","jmin":"40","jmax":"70","s1":"30","s2":"30","h1":"1","h2":"2","h3":"3","h4":"4"}

GEOSITE_SUGG = ["geosite:private","geosite:category-ads-all","geosite:category-ru","geosite:category-porn","geosite:google","geosite:youtube",
"geosite:telegram","geosite:twitter","geosite:facebook","geosite:instagram","geosite:openai","geosite:geolocation-cn",
"geosite:cn","geosite:apple","geosite:icloud","geosite:microsoft","geosite:github","geosite:netflix","geosite:spotify","geosite:discord",
"geosite:tiktok","geosite:category-games","geosite:category-media-ru","geosite:category-communication"]
GEOIP_SUGG = ["geoip:private","geoip:ru","geoip:by","geoip:kz","geoip:cn","geoip:us","geoip:eu","geoip:telegram"]

# ========================================
#  Блок: нормализация
# ========================================

def norm_dur(val, default_unit='s'):
    if val is None: return f"1{default_unit}"
    v = str(val).strip().lower()
    if not v: return f"1{default_unit}"
    m = DURATION_RE.match(v)
    if not m: return f"1{default_unit}"
    num, unit = m.group(1), m.group(2)
    if unit is None: unit = default_unit
    if unit not in DURATION_UNITS: unit = default_unit
    try: float(num)
    except ValueError: return f"1{default_unit}"
    return f"{num}{unit}"

def norm_bal(val):
    if not val: return "leastLoad"
    return BALANCER_TYPES.get(re.sub(r'[^a-z]','',str(val).lower()), "leastLoad")

def norm_int(val, default=0, mn=None, mx=None):
    try: n = int(val)
    except (ValueError, TypeError): return default
    if mn is not None and n < mn: n = mn
    if mx is not None and n > mx: n = mx
    return n

def norm_float(val, default=0.0):
    try: return float(val)
    except (ValueError, TypeError): return default

def process_domain_list(domains):
    dom_only, kw_set, re_set, other = [], set(), set(), []
    for d in domains:
        if not isinstance(d, str): continue
        if d.startswith("domain:"):
            base = d[7:]
            if '.' not in base and base.lower() in TLD_ONLY: kw_set.add(f"keyword:.{base.lower()}")
            else: dom_only.append(base)
        elif d.startswith("keyword:"): kw_set.add(d)
        elif d.startswith("regexp:"): re_set.add(d)
        else: other.append(d)
    dom_only.sort(key=lambda x: x.count('.'))
    keep = set()
    for d in dom_only:
        parts = d.split('.')
        is_child = False
        for i in range(1, len(parts)):
            if '.'.join(parts[i:]) in keep: is_child = True; break
        if not is_child: keep.add(d)
    result = [f"domain:{d}" for d in sorted(keep)]
    result.extend(sorted(kw_set)); result.extend(sorted(re_set)); result.extend(sorted(set(other)))
    return result

# --- Утилиты UI ---
def clr(): os.system('clear')
def hdr(t): print("=" * W); print(f" {t}"); print("=" * W)
def ln(): print("-" * W)

def fmt_size(b):
    if b < 1024: return f"{b} B"
    if b < 1024 * 1024: return f"{b/1024:.1f} KB"
    return f"{b/1024/1024:.2f} MB"

# ========================================
#  Блок: скачивание URL (несколькими способами)
# ========================================

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

def dl_urllib(url, show=True):
    ctx = ssl.create_default_context(); ctx.check_hostname = False; ctx.verify_mode = ssl.CERT_NONE
    req = urllib.request.Request(url, headers={'User-Agent': UA})
    with urllib.request.urlopen(req, context=ctx, timeout=30) as r:
        total = None
        cl = r.getheader('Content-Length')
        if cl:
            try: total = int(cl)
            except Exception: pass
        data = bytearray(); start = time.time()
        while True:
            chunk = r.read(8192)
            if not chunk: break
            data.extend(chunk)
            if show: progress_bar(len(data), total, prefix="  [urllib]", elapsed=time.time()-start)
        if show: sys.stdout.write("\n"); sys.stdout.flush()
        return bytes(data)

def dl_curl(url, show=True):
    tmp = "/tmp/sub_dl_curl.txt"
    cmd = ['curl','-sL','--insecure','-A',UA,'--max-time','60','-o',tmp,url]
    if show: print("  [curl] dl...")
    r = subprocess.run(cmd, capture_output=True)
    if r.returncode == 0 and os.path.exists(tmp):
        with open(tmp,'rb') as f: data = f.read()
        os.unlink(tmp)
        if show: print(f"  [curl] OK: {fmt_size(len(data))}")
        return data
    return None

def dl_wget(url, show=True):
    if not shutil.which('wget'): return None
    tmp = "/tmp/sub_dl_wget.txt"
    cmd = ['wget','-q','--no-check-certificate','-U',UA,'-O',tmp,url]
    if show: print("  [wget] dl...")
    r = subprocess.run(cmd, capture_output=True)
    if r.returncode == 0 and os.path.exists(tmp):
        with open(tmp,'rb') as f: data = f.read()
        os.unlink(tmp)
        if show: print(f"  [wget] OK: {fmt_size(len(data))}")
        return data
    return None

def dl_aria2(url, show=True):
    if not shutil.which('aria2c'): return None
    tmp_dir = "/tmp/sub_aria"; os.makedirs(tmp_dir, exist_ok=True)
    cmd = ['aria2c','-q','--check-certificate=false','-U',UA,'-x','4','-d',tmp_dir,'-o','sub.txt',url]
    if show: print("  [aria2] dl...")
    r = subprocess.run(cmd, capture_output=True)
    out = os.path.join(tmp_dir,'sub.txt')
    if r.returncode == 0 and os.path.exists(out):
        with open(out,'rb') as f: data = f.read()
        os.unlink(out)
        if show: print(f"  [aria2] OK: {fmt_size(len(data))}")
        return data
    return None

def dl_url(url, method='auto', show=True):
    print(f"[*] URL: {url}")
    methods = ['urllib','curl','wget','aria2'] if method == 'auto' else [method]
    for m in methods:
        try:
            if m == 'urllib': data = dl_urllib(url, show)
            elif m == 'curl': data = dl_curl(url, show)
            elif m == 'wget': data = dl_wget(url, show)
            elif m == 'aria2': data = dl_aria2(url, show)
            else: data = None
            if data:
                for enc in ['utf-8','cp1251','latin-1']:
                    try: return data.decode(enc)
                    except Exception: continue
        except Exception as e:
            print(f"[!] {m}: {e}"); continue
    return None

# ========================================
#  Блок: парсинг ссылок / JSON
# ========================================

def try_b64(raw):
    s = raw.strip().replace('\n','').replace('\r','').replace(' ','')
    if len(s) < 16 or not re.fullmatch(r'[A-Za-z0-9+/=_\-]+', s): return None
    for enc in ['urlsafe_b64','b64']:
        try:
            pad = 4 - len(s) % 4
            padded = s + ('=' * pad if pad != 4 else '')
            decoded = (base64.urlsafe_b64decode(padded) if enc == 'urlsafe_b64' else base64.b64decode(padded)).decode('utf-8', errors='ignore')
            if '://' in decoded or decoded.strip().startswith('{') or 'proxies:' in decoded: return decoded
        except Exception: continue
    return None

def auto_decode(raw):
    if not raw: return raw
    st = raw.strip()
    if st.startswith('{') or st.startswith('['): return raw
    if '://' in raw[:500] or 'proxies:' in raw[:200]: return raw
    dec = try_b64(raw)
    if dec: print("[+] Base64 decoded."); return dec
    return raw

def _safe_parsed_port(p):
    try:
        return p.port
    except ValueError:
        return None

def parse_uri(uri):
    uri = uri.strip()
    if not uri or '://' not in uri: return None
    scheme = uri.split('://')[0].lower()
    frag = ''
    if '#' in uri: uri, frag = uri.split('#', 1)
    r = {'scheme':scheme, 'raw':uri+('#'+frag if frag else ''), 'name':unquote(frag) if frag else '', 'params':{},
         'host':'','port':'','id':'','password':'','method':''}
    try:
        if scheme in ('vless','vmess','trojan'):
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
                            if len(cand) >= 8: r['id'] = cand
                except Exception: pass
            pport = _safe_parsed_port(p)
            r['host'] = p.hostname or ''; r['port'] = str(pport) if pport else ''
            for k,v in parse_qs(p.query).items(): r['params'][k] = v[0] if len(v) == 1 else v
        elif scheme in ('hysteria2','hy2','hysteria','hy'):
            p = urlparse(uri)
            r['password'] = unquote(p.username or '')
            pport = _safe_parsed_port(p)
            r['host'] = p.hostname or ''; r['port'] = str(pport) if pport else ''
            for k,v in parse_qs(p.query).items(): r['params'][k] = v[0] if len(v) == 1 else v
        elif scheme == 'ss':
            body = uri[5:]
            if '@' in body:
                ui, hp = body.rsplit('@', 1)
                try:
                    pad = 4 - len(ui) % 4
                    ui_pad = ui + '=' * pad if pad != 4 else ui
                    dec = base64.b64decode(ui_pad).decode('utf-8', errors='ignore')
                    if ':' in dec: r['method'], r['password'] = dec.split(':', 1)
                    else: r['method'] = dec
                except Exception:
                    if ':' in ui: r['method'], r['password'] = ui.split(':', 1)
                    else: r['method'] = ui
                if ':' in hp: r['host'], r['port'] = hp.rsplit(':', 1)
                else: r['host'] = hp
            else:
                try:
                    pad = 4 - len(body) % 4
                    padded = body + ('=' * pad if pad != 4 else '')
                    dec = base64.b64decode(padded).decode('utf-8', errors='ignore')
                    if '@' in dec:
                        ui, hp = dec.rsplit('@', 1)
                        if ':' in ui: r['method'], r['password'] = ui.split(':', 1)
                        if ':' in hp: r['host'], r['port'] = hp.rsplit(':', 1)
                except Exception: pass
            if '?' in uri:
                for k,v in parse_qs(uri.split('?',1)[1]).items(): r['params'][k] = v[0] if len(v) == 1 else v
        elif scheme in ('socks5','http','tuic','juicity','wireguard','amneziawg','awg','mieru','sudoku','openconnect'):
            p = urlparse(uri)
            r['id'] = unquote(p.username or '')
            r['password'] = unquote(p.password or '')
            pport = _safe_parsed_port(p)
            r['host'] = p.hostname or ''; r['port'] = str(pport) if pport else ''
            for k,v in parse_qs(p.query).items(): r['params'][k] = v[0] if len(v) == 1 else v
        else: return None
    except Exception: return None
    return r

def extract_links(text):
    out = []
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith('#'): continue
        if any(line.startswith(s + '://') for s in ['vless','vmess','trojan','ss','hysteria2','hy2','hysteria','hy','socks5','http','tuic','juicity','wireguard','amneziawg','awg','mieru','sudoku','openconnect']):
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
        if not vnext: return None
        vn = vnext[0]; users = vn.get('users', [{}]); user = users[0] if users else {}
        s = {'scheme':'vless','name':tag or 'vless','host':vn.get('address',''),'port':str(vn.get('port','443')),
             'id':user.get('id',''),'password':'','method':'','params':{'type':net,'security':sec}}
        if user.get('flow'): s['params']['flow'] = user['flow']
        if sec == 'reality':
            rs = ss.get('realitySettings', {}) or {}
            for src, dst in [('serverName','sni'),('publicKey','pbk'),('shortId','sid'),('fingerprint','fp'),('spiderX','spiderX')]:
                if rs.get(src): s['params'][dst] = str(rs[src])
        elif sec == 'tls':
            ts = ss.get('tlsSettings', {}) or {}
            if ts.get('serverName'): s['params']['sni'] = ts['serverName']
            if ts.get('fingerprint'): s['params']['fp'] = ts['fingerprint']
            if ts.get('alpn'): s['params']['alpn'] = ','.join(ts['alpn'])
        if net == 'ws':
            w = ss.get('wsSettings', {}) or {}
            s['params']['path'] = w.get('path', '/')
            headers = w.get('headers', {}) or {}
            if headers.get('Host'): s['params']['host'] = headers['Host']
            if w.get('heartbeatPeriod'): s['params']['heartbeatPeriod'] = str(w['heartbeatPeriod'])
        elif net == 'grpc':
            g = ss.get('grpcSettings', {}) or {}
            if g.get('serviceName'): s['params']['serviceName'] = g['serviceName']
            if g.get('authority'): s['params']['authority'] = g['authority']
            s['params']['mode'] = 'multi' if g.get('multiMode') else 'auto'
        elif net == 'tcp':
            th = (ss.get('tcpSettings', {}) or {}).get('header', {}) or {}
            s['params']['headerType'] = th.get('type', 'none')
        elif net in ('xhttp','splithttp'):
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
        if not vnext: return None
        vn = vnext[0]; users = vn.get('users', [{}]); user = users[0] if users else {}
        s = {'scheme':'vmess','name':tag or 'vmess','host':vn.get('address',''),'port':str(vn.get('port','443')),
             'id':user.get('id',''),'password':'','method':'','params':{'type':net,'security':sec}}
        if user.get('alterId'): s['params']['alterId'] = str(user['alterId'])
        if user.get('security'): s['params']['encryption'] = user['security']
        if sec == 'tls':
            ts = ss.get('tlsSettings', {}) or {}
            if ts.get('serverName'): s['params']['sni'] = ts['serverName']
        return s

    elif proto in ('shadowsocks','ss'):
        servers = (ob.get('settings', {}) or {}).get('servers', [{}])
        if not servers: return None
        srv = servers[0]
        return {'scheme':'ss','name':tag or 'ss','host':srv.get('address',''),'port':str(srv.get('port','443')),
                'id':'','password':srv.get('password',''),'method':srv.get('method','aes-256-gcm'),'params':{}}

    elif proto == 'hysteria2':
        st = ob.get('settings', {}) or {}
        s = {'scheme':'hysteria2','name':tag or 'hysteria2','host':st.get('address',''),'port':str(st.get('port','443')),
             'id':'','password':st.get('password',''),'method':'','params':{'type':'hysteria2','security':'tls'}}
        if st.get('obfs'):
            s['params']['obfs'] = st['obfs']
            if st.get('obfsPassword'): s['params']['obfs-password'] = st['obfsPassword']
        ts = ss.get('tlsSettings', {}) or {}
        if ts.get('serverName'): s['params']['sni'] = ts['serverName']
        if ts.get('alpn'): s['params']['alpn'] = ','.join(ts['alpn'])
        return s

    elif proto == 'hysteria':
        st = ob.get('settings', {}) or {}
        s = {'scheme':'hysteria','name':tag or 'hysteria','host':st.get('address',''),'port':str(st.get('port','443')),
             'id':'','password':st.get('auth',''),'method':'','params':{'type':'hysteria','security':'tls'}}
        if st.get('up'): s['params']['up'] = str(st['up'])
        if st.get('down'): s['params']['down'] = str(st['down'])
        return s

    elif proto == 'trojan':
        servers = (ob.get('settings', {}) or {}).get('servers', [{}])
        if not servers: return None
        srv = servers[0]
        s = {'scheme':'trojan','name':tag or 'trojan','host':srv.get('address',''),'port':str(srv.get('port','443')),
             'id':'','password':srv.get('password',''),'method':'','params':{'type':net,'security':sec if sec != 'none' else 'tls'}}
        if sec == 'tls':
            ts = ss.get('tlsSettings', {}) or {}
            if ts.get('serverName'): s['params']['sni'] = ts['serverName']
        return s

    elif proto == 'socks':
        servers = (ob.get('settings', {}) or {}).get('servers', [{}])
        if not servers: return None
        srv = servers[0]
        return {'scheme':'socks5','name':tag or 'socks5','host':srv.get('address',''),'port':str(srv.get('port','1080')),
                'id':srv.get('user',''),'password':srv.get('pass',''),'method':'','params':{}}

    elif proto == 'http':
        servers = (ob.get('settings', {}) or {}).get('servers', [{}])
        if not servers: return None
        srv = servers[0]
        return {'scheme':'http','name':tag or 'http','host':srv.get('address',''),'port':str(srv.get('port','8080')),
                'id':srv.get('user',''),'password':srv.get('pass',''),'method':'','params':{}}

    elif proto == 'wireguard':
        st = ob.get('settings', {}) or {}
        peers = st.get('peers', [{}]); peer = peers[0] if peers else {}
        ep = peer.get('endpoint', '')
        return {'scheme':'wireguard','name':tag or 'wireguard',
                'host':ep.split(':')[0] if ep else '','port':ep.split(':')[1] if ep and ':' in ep else '51820',
                'id':st.get('secretKey',''),'password':peer.get('publicKey',''),'method':'',
                'params':{'allowedIPs':','.join(peer.get('allowedIPs',['0.0.0.0/0'])),'mtu':str(st.get('mtu',1420)),
                          'dns':st.get('dns',''),'presharedKey':peer.get('preSharedKey',''),
                          'keepalive':str(peer.get('persistentKeepalive',0))}}
    return None

def singbox_obj_to_server(obj):
    if not isinstance(obj, dict): return None
    t = (obj.get('type') or obj.get('protocol') or '').upper()
    host = obj.get('host') or obj.get('server') or obj.get('address') or ''
    port = obj.get('port')
    if port is None: return None
    port = str(port)
    if not host or not port: return None
    name = obj.get('title') or obj.get('remarks') or obj.get('name') or obj.get('tag') or ''
    alpn = obj.get('alpn') or ''
    peer = obj.get('peer') or obj.get('sni') or obj.get('serverName') or ''
    if t in ('HYSTERIA2','HY2'):
        s = {'scheme':'hysteria2','name':name,'host':host,'port':port,'id':'',
             'password':obj.get('password') or obj.get('auth') or '','method':'',
             'params':{'type':'hysteria2','security':'tls'}}
        if peer: s['params']['sni'] = peer
        if alpn: s['params']['alpn'] = alpn
        obfs = obj.get('obfs')
        if obfs and obfs.lower() not in ('none',''):
            s['params']['obfs'] = obfs
            if obj.get('obfsParam'): s['params']['obfs-password'] = obj['obfsParam']
        return s
    if t == 'VLESS':
        s = {'scheme':'vless','name':name,'host':host,'port':port,'id':obj.get('uuid') or obj.get('id') or '',
             'password':'','method':'','params':{'type':'tcp','security':'none'}}
        if obj.get('tls') or obj.get('publicKey') or peer:
            s['params']['security'] = 'reality' if obj.get('publicKey') else 'tls'
            s['params']['type'] = 'tcp'
        if peer: s['params']['sni'] = peer
        if obj.get('publicKey'): s['params']['pbk'] = obj['publicKey']
        if obj.get('shortId'): s['params']['sid'] = obj['shortId']
        if obj.get('tlsProfile'): s['params']['fp'] = obj['tlsProfile']
        if obj.get('fingerprint'): s['params']['fp'] = obj['fingerprint']
        if obj.get('xtls') in (2,'2',True): s['params']['flow'] = 'xtls-rprx-vision'
        if alpn: s['params']['alpn'] = alpn
        return s
    if t == 'TROJAN':
        s = {'scheme':'trojan','name':name,'host':host,'port':port,'id':'',
             'password':obj.get('password') or '','method':'','params':{'type':'tcp','security':'tls'}}
        if peer: s['params']['sni'] = peer
        if alpn: s['params']['alpn'] = alpn
        return s
    if t in ('SHADOWSOCKS','SS'):
        return {'scheme':'ss','name':name,'host':host,'port':port,'id':'',
                'password':obj.get('password') or '','method':obj.get('method') or 'aes-256-gcm','params':{}}
    return None

def extract_servers_from_json(text):
    try: data = json.loads(text)
    except Exception: return [], None
    if not isinstance(data, dict): return [], None
    outbounds = data.get('outbounds', [])
    servers = []
    for ob in outbounds:
        if not isinstance(ob, dict): continue
        proto = (ob.get('protocol') or '').lower()
        if proto in ('vless','vmess','trojan','ss','shadowsocks','hysteria2','hysteria','socks','http','wireguard'):
            s = parse_xray_outbound(ob)
            if s: servers.append(s)
    return servers, data

def parse_singbox_multi(text):
    servers = []
    for line in text.splitlines():
        line = line.strip().rstrip(',')
        if not line.startswith('{'): continue
        try: obj = json.loads(line)
        except Exception: continue
        srv = singbox_obj_to_server(obj)
        if srv: servers.append(srv)
    return servers

# ========================================
#  Блок: построение URI
# ========================================

def build_uri(s):
    scheme = s['scheme']; host = s['host']; port = s['port']
    params = dict(s['params']); name = s.get('name','')
    if scheme in ('vless','vmess','trojan'): uri = f"{scheme}://{quote(s.get('id',''))}@{host}:{port}"
    elif scheme in ('hysteria2','hy2','hysteria','hy'): uri = f"{scheme}://{quote(s.get('password',''))}@{host}:{port}"
    elif scheme == 'ss':
        ui = f"{s.get('method','')}:{s.get('password','')}"
        uri = f"ss://{base64.b64encode(ui.encode()).decode().rstrip('=')}@{host}:{port}"
    elif scheme == 'socks5':
        auth = f"{quote(s.get('id',''))}:{quote(s.get('password',''))}@" if (s.get('id') or s.get('password')) else ''
        uri = f"socks5://{auth}{host}:{port}"
    elif scheme == 'http':
        auth = f"{quote(s.get('id',''))}:{quote(s.get('password',''))}@" if (s.get('id') or s.get('password')) else ''
        uri = f"http://{auth}{host}:{port}"
    elif scheme == 'tuic': uri = f"tuic://{quote(s.get('id',''))}:{quote(s.get('password',''))}@{host}:{port}"
    elif scheme == 'juicity': uri = f"juicity://{quote(s.get('id',''))}:{quote(s.get('password',''))}@{host}:{port}"
    elif scheme == 'wireguard': uri = f"wireguard://{quote(s.get('id',''))}@{host}:{port}"
    elif scheme in ('amneziawg','awg'): uri = f"{scheme}://{quote(s.get('id',''))}@{host}:{port}"
    elif scheme == 'mieru': uri = f"mieru://{quote(s.get('id',''))}:{quote(s.get('password',''))}@{host}:{port}"
    elif scheme == 'sudoku': uri = f"sudoku://{quote(s.get('id',''))}:{quote(s.get('password',''))}@{host}:{port}"
    elif scheme == 'openconnect': uri = f"openconnect://{quote(s.get('id',''))}@{host}:{port}"
    else: return s.get('raw', '')
    if params: uri += '?' + urlencode(params, doseq=True)
    if name: uri += '#' + quote(name)
    return uri

# ========================================
#  Блок: список серверов
# ========================================

def show_servers_list(servers, show_params=False):
    if not servers:
        print(f"[!] {tr('list_empty')}"); return
    print(f"\n{'#':>3} {'Protocol':12} {'Name':28} {'Address':30} {'Transport':10} {'Sec':8}")
    ln()
    for i, s in enumerate(servers, 1):
        name = (s.get('name','') or '(no name)')[:28]
        addr = f"{s['host']}:{s['port']}"[:30]
        t = s['params'].get('type','tcp')
        sec = s['params'].get('security','none')
        print(f"{i:>3} {s['scheme']:12} {name:28} {addr:30} {t:10} {sec:8}")
        if show_params:
            extra = []
            for k in ('flow','path','host','sni','pbk','sid','fp','serviceName','mode','concurrency','alpn','obfs','method','alterId','encryption','allowedIPs','mtu','dns','keepalive'):
                if k in s['params'] and s['params'][k]:
                    val = str(s['params'][k])
                    if len(val) > 40: val = val[:37] + "..."
                    extra.append(f"{k}={val}")
            if extra: print(f"      {', '.join(extra)}")

# ========================================
#  Блок: конфиг (дефолт / загрузка / сохранение)
# ========================================

def cfg_default():
    return {"dns_servers":DNS_SERVERS,"dns_query_strategy":"UseIP","observatory_url":"https://www.google.com/generate_204",
        "observatory_interval":"1m","observatory_timeout":"3s","balancer_strategy":"leastLoad","balancer_expected":3,
        "balancer_max_rtt":"2s","balancer_tolerance":0,"balancer_baselines":["2s"],"proxy_ports":[10808,10809],
        "mux_enabled":False,"mux_concurrency":8,"mux_xudp_concurrency":0,"mux_xudp_proxy_udp443":"reject",
        "global_proxy":"proxy","sniffing_enabled":True,"sniffing_dest_override":["http","tls","quic"],"sniffing_route_only":True,
        "json_name":"xray_config","json_remarks":"SubManager Auto","json_use_remarks_as_name":False,
        "routing_order":["block","direct","proxy"],
        "routing":{"direct_domains":[],"block_domains":[],"direct_ips":[],"block_ips":[],"block_protocols":[],
                   "direct_ports":[],"block_ports":[],"custom_rules":[]}}

def norm_cfg(cfg):
    d = cfg_default()
    for k, v in cfg.items():
        if isinstance(v, dict) and k in d and isinstance(d[k], dict):
            m = dict(d[k]); m.update(v); cfg[k] = m
        else: d[k] = v
    cfg = d
    cfg['observatory_interval'] = norm_dur(cfg.get('observatory_interval','1m'), 'm')
    cfg['observatory_timeout'] = norm_dur(cfg.get('observatory_timeout','3s'), 's')
    cfg['balancer_max_rtt'] = norm_dur(cfg.get('balancer_max_rtt','2s'), 's')
    cfg['balancer_strategy'] = norm_bal(cfg.get('balancer_strategy','leastLoad'))
    cfg['balancer_expected'] = norm_int(cfg.get('balancer_expected',3), 3, 1, 999)
    cfg['balancer_tolerance'] = norm_float(cfg.get('balancer_tolerance',0), 0.0)
    bl = cfg.get('balancer_baselines',['2s'])
    if not isinstance(bl, list): bl = ['2s']
    cfg['balancer_baselines'] = [norm_dur(b,'s') for b in bl]
    pp = cfg.get('proxy_ports',[10808,10809])
    if not isinstance(pp, list) or len(pp) != 2: pp = [10808,10809]
    cfg['proxy_ports'] = [norm_int(pp[0],10808,1,65535), norm_int(pp[1],10809,1,65535)]
    cfg['mux_concurrency'] = norm_int(cfg.get('mux_concurrency',8),8,1,128)
    cfg['mux_xudp_concurrency'] = norm_int(cfg.get('mux_xudp_concurrency',0),0,0,1024)
    if cfg.get('mux_xudp_proxy_udp443') not in ('reject','skip','allow'): cfg['mux_xudp_proxy_udp443'] = 'reject'
    if cfg.get('global_proxy') not in ('proxy','direct','block'): cfg['global_proxy'] = 'proxy'
    if cfg.get('dns_query_strategy') not in ('UseIP','UseIPv4','UseIPv6','AsIs'): cfg['dns_query_strategy'] = 'UseIP'
    ds = cfg.get('dns_servers', DNS_SERVERS)
    if not isinstance(ds, list) or not ds: cfg['dns_servers'] = DNS_SERVERS
    so = cfg.get('sniffing_dest_override',["http","tls","quic"])
    if not isinstance(so, list): so = ["http","tls","quic"]
    cfg['sniffing_dest_override'] = so
    ro = cfg.get('routing_order',["block","direct","proxy"])
    if not isinstance(ro, list) or set(ro) != {'block','direct','proxy'}: ro = ["block","direct","proxy"]
    cfg['routing_order'] = ro
    return cfg

def cfg_load():
    if CFG_FILE.exists():
        try:
            with open(CFG_FILE, 'r', encoding='utf-8') as f: return norm_cfg(json.load(f))
        except Exception: pass
    return cfg_default()

def cfg_save(cfg):
    cfg = norm_cfg(cfg)
    CFG_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(CFG_FILE, 'w', encoding='utf-8') as f: json.dump(cfg, f, ensure_ascii=False, indent=2)

# ========================================
#  Блок: утилиты файлов и имён
# ========================================

def ensure_dirs():
    for d in [INPUT_DIR, OUTPUT_DIR, BACKUP_DIR, ROUTING_DIR]:
        if not d.exists(): d.mkdir(parents=True, exist_ok=True)

def sanitize_fn(name):
    name = re.sub(r'[\\/:*?"<>|]', '_', name).strip().strip('.')
    return name or "xray_config"

def transliterate(name):
    mp = {'а':'a','б':'b','в':'v','г':'g','д':'d','е':'e','ё':'e','ж':'zh','з':'z','и':'i','й':'y','к':'k','л':'l','м':'m','н':'n','о':'o','п':'p','р':'r','с':'s','т':'t','у':'u','ф':'f','х':'h','ц':'ts','ч':'ch','ш':'sh','щ':'sch','ъ':'','ы':'y','ь':'','э':'e','ю':'yu','я':'ya',
          'А':'A','Б':'B','В':'V','Г':'G','Д':'D','Е':'E','Ё':'E','Ж':'Zh','З':'Z','И':'I','Й':'Y','К':'K','Л':'L','М':'M','Н':'N','О':'O','П':'P','Р':'R','С':'S','Т':'T','У':'U','Ф':'F','Х':'H','Ц':'Ts','Ч':'Ch','Ш':'Sh','Щ':'Sch','Ъ':'','Ы':'Y','Ь':'','Э':'E','Ю':'Yu','Я':'Ya',' ':'_'}
    return ''.join(mp.get(ch, ch) for ch in name)

def autosave(servers):
    if not servers: return
    with open(AUTOSAVE_FILE, 'w', encoding='utf-8') as f: f.write('\n'.join(build_uri(s) for s in servers))

def autoload():
    if not AUTOSAVE_FILE.exists(): return []
    try: raw = AUTOSAVE_FILE.read_text(encoding='utf-8', errors='ignore')
    except Exception: return []
    srv, _ = parse_input(raw); return srv

# ========================================
#  Блок: парсинг входных данных
# ========================================

def parse_input(raw):
    if not raw: return [], None
    st = raw.strip()
    if st.startswith('{'):
        servers, jd = extract_servers_from_json(st)
        if servers:
            print(f"[+] {tr('xray_detected')}: {len(servers)}")
            return servers, jd
    servers = []
    if '{' in raw and '"type"' in raw.upper():
        sb = parse_singbox_multi(raw)
        if sb:
            print(f"[+] {tr('singbox_detected')}: {len(sb)}"); servers.extend(sb)
    links = extract_links(raw)
    if links:
        cnt = 0
        for l in links:
            p = parse_uri(l)
            if p: servers.append(p); cnt += 1
        print(f"[+] {tr('links_found')}: {len(links)}, {tr('parsed')}: {cnt}")
    if servers: return servers, None
    print(f"[!] {tr('parse_data')}")
    return [], None

# ========================================
#  Блок: загрузка источников
# ========================================

def load_source():
    hdr(tr("load_src"))
    print("  " + tr("load_1")); print("  " + tr("load_2")); print("  " + tr("load_3")); print("  " + tr("q_back"))
    ch = _in_choice(f"{tr('choice')} [1]: ", ["1","2","3"]) or "1"
    if ch == EXIT: return None
    if ch == "1":
        files = sorted([p for p in INPUT_DIR.glob("*") if p.is_file()])
        if not files:
            print(f"[!] {tr('folder_empty')}: {INPUT_DIR}")
            print(f"    {tr('put_file')} {INPUT_DIR}")
            _in("\n" + tr("q_back") + ": ", allow_exit=False)
            return None
        print(f"\n[+] Files:")
        for i, f in enumerate(files, 1): print(f"  {i}. {f.name} ({fmt_size(f.stat().st_size)})")
        idx = _in_int(f"{tr('file_n')} ({tr('q_back')}): ", mn=1, mx=len(files))
        if idx == EXIT or idx is None: return None
        raw = files[idx-1].read_text(encoding='utf-8', errors='ignore')
    elif ch == "2":
        url = _in(f"{tr('url_sub')} ({tr('q_back')}): ")
        if url == EXIT or not url: return None
        raw = dl_url(url)
        if not raw:
            print(f"[!] {tr('dl_fail')}")
            _in("\n" + tr("q_back") + ": ", allow_exit=False)
            return None
    else:
        print(f"[?] {tr('enter_urls')}")
        parts = []
        while True:
            u = _in(f"{tr('url_q')}: ")
            if u == EXIT or not u: break
            t = dl_url(u)
            if t:
                parts.append(auto_decode(t))
                print(f"  [+] {tr('added')}: {len(parts)}")
            else: print(f"  [!] {tr('dl_fail')}: {u}")
        if not parts:
            _in("\n" + tr("q_back") + ": ", allow_exit=False); return None
        raw = "\n".join(parts)
        print(f"[+] {tr('merged')}: {len(parts)}")
        return raw
    return auto_decode(raw)

# ========================================
#  Блок: дедупликация
# ========================================

def dedupe_servers(servers, mode='full'):
    seen = set(); out = []
    for s in servers:
        if mode == 'full': key = (s['scheme'],s['host'],s['port'],s.get('id','') or s.get('password','') or s.get('method',''))
        elif mode == 'name': key = s.get('name','')
        elif mode == 'addr': key = (s['host'],s['port'])
        elif mode == 'user': key = (s['host'],s['port'],s.get('id','') or s.get('password',''))
        else: key = (s['scheme'],s['host'],s['port'])
        if key not in seen: seen.add(key); out.append(s)
    removed = len(servers) - len(out)
    print(f"[+] {tr('dedupe_removed')}: {removed}" if removed else f"[+] {tr('dedupe_none')}")
    return out

def dedupe_menu(servers):
    hdr(tr("dedupe_hdr"))
    print("  " + tr("d_full")); print("  " + tr("d_name")); print("  " + tr("d_addr")); print("  " + tr("d_user"))
    print("  " + tr("d_proto")); print("  " + tr("q_back"))
    ch = _in_choice(f"{tr('choice')}: ", ["1","2","3","4","5"])
    if ch == EXIT: return servers
    mm = {"1":"full","2":"name","3":"addr","4":"user","5":"proto"}
    return dedupe_servers(servers, mm[ch])

# ========================================
#  Блок: удаление серверов
# ========================================

def delete_by_keyword(servers):
    hdr(tr("del_hdr"))
    print("  " + tr("del_1")); print("  " + tr("del_2")); print("  " + tr("del_3")); print("  " + tr("del_4"))
    print("  " + tr("del_5")); print("  " + tr("del_6")); print("  " + tr("del_7")); print("  " + tr("q_back"))
    ch = _in_choice(f"{tr('choice')}: ", ["1","2","3","4","5","6","7"])
    if ch == EXIT: return servers
    idxs = None
    if ch == "1":
        kw = _in(f"{tr('words_csv')}: ")
        if kw == EXIT: return servers
        kws = [k.strip().lower() for k in kw.split(',') if k.strip()]
        if not kws: return servers
        idxs = [i for i,s in enumerate(servers) if any(k in s.get('name','').lower() for k in kws)]
    elif ch == "2":
        proto = _in(f"{tr('proto_l')}: ").lower()
        if proto == EXIT: return servers
        idxs = [i for i,s in enumerate(servers) if s['scheme'] == proto]
    elif ch == "3":
        t = _in(f"{tr('transport')}: ").lower()
        if t == EXIT: return servers
        idxs = [i for i,s in enumerate(servers) if s['params'].get('type','tcp') == t]
    elif ch == "4":
        sec = _in(f"{tr('security')}: ").lower()
        if sec == EXIT: return servers
        idxs = [i for i,s in enumerate(servers) if s['params'].get('security','none') == sec]
    elif ch == "5":
        dom = _in(f"{tr('domain')}: ").lower()
        if dom == EXIT: return servers
        idxs = [i for i,s in enumerate(servers) if dom in s['host'].lower()]
    elif ch == "6":
        show_servers_list(servers)
        sel = _in_multi(f"{tr('numbers')}: ", 1, len(servers))
        if sel == EXIT or not sel: return servers
        idxs = [i-1 for i in sel]
    elif ch == "7":
        kw = _in(f"{tr('kw_inv')}: ")
        if kw == EXIT: return servers
        kws = [k.strip().lower() for k in kw.split(',') if k.strip()]
        if not kws: return servers
        idxs = [i for i,s in enumerate(servers) if not any(k in s.get('name','').lower() for k in kws)]
    if not idxs:
        print(f"[!] {tr('not_found')}")
        _in("\n" + tr("q_back") + ": ", allow_exit=False); return servers
    print(f"\n[+] {tr('found')}: {len(idxs)}")
    for i in idxs[:20]: print(f"   - {servers[i].get('name','')} ({servers[i]['scheme']}://{servers[i]['host']})")
    if len(idxs) > 20: print(f"   ... +{len(idxs)-20}")
    ans = _in(f"{tr('delete_q')} [n]: ", default="n")
    if ans and ans.lower() == 'y':
        for i in sorted(idxs, reverse=True): servers.pop(i)
        print(f"[+] {tr('deleted_n')}: {len(idxs)}")
    return servers

# ========================================
#  Блок: сортировка / перемещение / дубликаты
# ========================================

def sort_servers(servers):
    hdr(tr("sort_hdr"))
    print("  " + tr("s_az")); print("  " + tr("s_za")); print("  " + tr("s_proto")); print("  " + tr("s_host"))
    print("  " + tr("s_port")); print("  " + tr("s_rand")); print("  " + tr("q_back"))
    ch = _in_choice(f"{tr('choice')}: ", ["1","2","3","4","5","6"])
    if ch == EXIT: return servers
    if ch == "1": servers.sort(key=lambda x: x.get('name','').lower())
    elif ch == "2": servers.sort(key=lambda x: x.get('name','').lower(), reverse=True)
    elif ch == "3": servers.sort(key=lambda x: x['scheme'])
    elif ch == "4": servers.sort(key=lambda x: x['host'].lower())
    elif ch == "5": servers.sort(key=lambda x: int(x['port']) if str(x['port']).isdigit() else 0)
    elif ch == "6": random.shuffle(servers)
    print(f"[+] {tr('sorted')}"); return servers

def move_server(servers):
    show_servers_list(servers)
    idx = _in_int(f"{tr('move_n')} ({tr('q_back')}): ", mn=1, mx=len(servers))
    if idx == EXIT or idx is None: return servers
    d = _in_choice(f"{tr('direction')}: ", ["u","d"])
    if d == EXIT: return servers
    i = idx - 1
    if d == "u" and i > 0: servers[i], servers[i-1] = servers[i-1], servers[i]; print(f"[+] {tr('moved_up')}")
    elif d == "d" and i < len(servers) - 1: servers[i], servers[i+1] = servers[i+1], servers[i]; print(f"[+] {tr('moved_dn')}")
    else: print(f"[!] {tr('no_move')}")
    return servers

def duplicate_servers(servers):
    show_servers_list(servers)
    sel = _in_multi(f"{tr('dup_n')}: ", 1, len(servers))
    if sel == EXIT or not sel: return servers
    new = []
    for idx in sel:
        s = copy.deepcopy(servers[idx-1])
        s['name'] = f"{s.get('name','')} (copy)"
        new.append(s)
    servers.extend(new)
    print(f"[+] {tr('dup_created')}: {len(new)}")
    ans = _in(f"{tr('edit_q')} [n]: ", default="n")
    if ans and ans.lower() == 'y':
        edit_params_for_group(servers, list(range(len(servers)-len(new), len(servers))))
    return servers

# ========================================
#  Блок: параметры серверов (редактирование группы)
# ========================================

PARAM_LIST = [
("scheme","Protocol"),("type","Transport"),("security","Security"),("flow","Flow"),("path","Path"),("host","Host"),
("sni","SNI"),("pbk","PublicKey"),("sid","ShortId"),("fp","Fingerprint"),("serviceName","ServiceName"),("authority","Authority"),
("mode","Mode"),("port","Port"),("host_addr","Address"),("alpn","ALPN"),("obfs","Obfs"),("obfs-password","Obfs-password"),
("id","UUID/Login"),("password","Password"),("method","SS Method"),("concurrency","Concurrency"),("spiderX","SpiderX"),
("headerType","Header Type"),("heartbeatPeriod","HeartbeatPeriod"),("alterId","AlterID"),("encryption","Encryption"),
("allowedIPs","AllowedIPs"),("mtu","MTU"),("dns","DNS"),("presharedKey","PresharedKey"),("keepalive","Keepalive"),
("up","Up"),("down","Down"),("congestion_control","Congestion Control"),("pinned_certchain_sha256","PinnedCertHash"),
("verify_peer_cert_by_name","VerifyPeerCertByName"),("jc","Jc"),("jmin","Jmin"),("jmax","Jmax"),
("s1","S1"),("s2","S2"),("h1","H1"),("h2","H2"),("h3","H3"),("h4","H4")]

CHOICES = {
"scheme":["vless","vmess","trojan","hysteria2","hysteria","ss","socks5","http","tuic","juicity","wireguard","amneziawg","mieru","sudoku","openconnect"],
"type":["tcp","ws","grpc","xhttp","splithttp","httpupgrade","h2","kcp","quic"],
"security":["none","tls","reality"],"flow":["xtls-rprx-vision",""],
"fp":["chrome","firefox","safari","ios","android","edge","360","qq","random","randomized"],
"mode":["auto","packet-up","stream-up","stream-one","multi"],"headerType":["none","http"],
"alpn":["h3","h2","http/1.1","h3,h2","h2,http/1.1"],"congestion_control":["cubic","new_reno","bbr"],
"encryption":["auto","none","zero"]}

COMPAT = {
"flow":lambda s: s['scheme']=='vless' and s['params'].get('type','tcp')=='tcp' and s['params'].get('security')=='reality',
"pbk":lambda s: s['scheme']=='vless' and s['params'].get('security')=='reality',
"sid":lambda s: s['scheme']=='vless' and s['params'].get('security')=='reality',
"sni":lambda s: s['scheme'] in ('vless','hysteria2','trojan','tuic','juicity','vmess'),
"fp":lambda s: s['scheme'] in ('vless','trojan','vmess'),
"serviceName":lambda s: s['scheme'] in ('vless','vmess') and s['params'].get('type')=='grpc',
"authority":lambda s: s['scheme'] in ('vless','vmess') and s['params'].get('type')=='grpc',
"path":lambda s: s['scheme'] in ('vless','vmess') and s['params'].get('type') in ('ws','xhttp','splithttp','httpupgrade'),
"host":lambda s: s['scheme'] in ('vless','vmess') and s['params'].get('type') in ('ws','xhttp','splithttp','httpupgrade'),
"mode":lambda s: s['scheme'] in ('vless','vmess') and s['params'].get('type') in ('grpc','xhttp','splithttp'),
"concurrency":lambda s: s['scheme'] in ('vless','vmess') and s['params'].get('type') in ('xhttp','splithttp'),
"obfs":lambda s: s['scheme']=='hysteria2',"obfs-password":lambda s: s['scheme']=='hysteria2',
"alpn":lambda s: s['params'].get('security')=='tls' or s['scheme'] in ('hysteria2','tuic','juicity'),
"method":lambda s: s['scheme']=='ss',
"id":lambda s: s['scheme'] in ('vless','vmess','trojan','tuic','juicity','wireguard','amneziawg','mieru','sudoku','openconnect'),
"password":lambda s: s['scheme'] in ('hysteria2','hysteria','ss','trojan','tuic','juicity','mieru','sudoku'),
"spiderX":lambda s: s['scheme']=='vless' and s['params'].get('security')=='reality',
"headerType":lambda s: s['scheme'] in ('vless','vmess') and s['params'].get('type')=='tcp' and s['params'].get('security')!='reality',
"heartbeatPeriod":lambda s: s['scheme'] in ('vless','vmess') and s['params'].get('type')=='ws',
"alterId":lambda s: s['scheme']=='vmess',"encryption":lambda s: s['scheme']=='vmess',
"allowedIPs":lambda s: s['scheme']=='wireguard',"mtu":lambda s: s['scheme'] in ('wireguard','amneziawg'),
"dns":lambda s: s['scheme'] in ('wireguard','amneziawg'),"presharedKey":lambda s: s['scheme']=='wireguard',
"keepalive":lambda s: s['scheme']=='wireguard',"up":lambda s: s['scheme']=='hysteria',"down":lambda s: s['scheme']=='hysteria',
"congestion_control":lambda s: s['scheme'] in ('tuic','juicity'),
"pinned_certchain_sha256":lambda s: s['params'].get('security')=='tls',
"verify_peer_cert_by_name":lambda s: s['params'].get('security')=='tls',
"jc":lambda s: s['scheme'] in ('amneziawg','awg'),"jmin":lambda s: s['scheme'] in ('amneziawg','awg'),
"jmax":lambda s: s['scheme'] in ('amneziawg','awg'),"s1":lambda s: s['scheme'] in ('amneziawg','awg'),
"s2":lambda s: s['scheme'] in ('amneziawg','awg'),"h1":lambda s: s['scheme'] in ('amneziawg','awg'),
"h2":lambda s: s['scheme'] in ('amneziawg','awg'),"h3":lambda s: s['scheme'] in ('amneziawg','awg'),
"h4":lambda s: s['scheme'] in ('amneziawg','awg')}

SS_METHODS = ["aes-128-gcm","aes-256-gcm","chacha20-poly1305","chacha20-ietf-poly1305","xchacha20-poly1305",
"xchacha20-ietf-poly1305","2022-blake3-aes-128-gcm","2022-blake3-aes-256-gcm","2022-blake3-chacha20-poly1305","none"]

def get_param_current(s, pkey):
    if pkey == 'port': return s.get('port','')
    if pkey == 'host_addr': return s.get('host','')
    if pkey == 'scheme': return s.get('scheme','')
    if pkey in ('id','password','method'): return s.get(pkey,'')
    return s['params'].get(pkey,'')

def edit_params_for_group(servers, indices):
    if not indices: return
    while True:
        clr(); hdr(tr("edit_grp"))
        print(f"  {tr('sel_servers')}: {len(indices)}")
        for i in indices[:25]:
            s = servers[i]
            print(f"    {i+1}. {s.get('name','')[:32]} [{s['scheme']}] {s['host']}:{s['port']}")
        if len(indices) > 25: print(f"    ... +{len(indices)-25}")
        ln()
        for idx, (k, desc) in enumerate(PARAM_LIST, 1):
            print(f"  {idx:2}. {desc}")
        print(f"   {tr('q_back')}")
        ch = _in(f"{tr('choice')}: ")
        if ch == EXIT or ch == "0": break
        try: pi = int(ch) - 1
        except Exception: continue
        if pi < 0 or pi >= len(PARAM_LIST): continue
        pkey, pname = PARAM_LIST[pi]
        compat_fn = COMPAT.get(pkey)
        compatible = [i for i in indices if compat_fn is None or compat_fn(servers[i])]
        if not compatible:
            print(f"[!] {tr('no_servers')}")
            _in("\n" + tr("q_back") + ": ", allow_exit=False); continue
        clr(); hdr(f"{tr('change')}: {pname}")
        print(f"  {tr('compat')}: {len(compatible)}/{len(indices)}")
        print(f"  {tr('will_change')}: {len(compatible)}")
        if len(indices) - len(compatible) > 0: print(f"  {tr('incompat')}: {len(indices)-len(compatible)}")
        print()
        for i in compatible[:15]:
            s = servers[i]
            print(f"    {i+1}. {s.get('name','')[:28]} -> {get_param_current(s, pkey)}")
        if len(compatible) > 15: print(f"    ... +{len(compatible)-15}")
        cur_default = ''
        for i in compatible:
            v = get_param_current(servers[i], pkey)
            if v: cur_default = str(v); break
        if not cur_default: cur_default = PARAM_DEFAULTS.get(pkey, '')
        ln()
        if pkey == "scheme": print(f"  {', '.join(CHOICES['scheme'])}")
        elif pkey in CHOICES: print(f"  {', '.join(CHOICES[pkey])}")
        elif pkey == "method": print(f"  {', '.join(SS_METHODS)}")
        print(f"  {tr('default_val')}: {cur_default}")
        print(f"  {tr('enter_default')}"); print(f"  {tr('minus_del')}"); print(f"  {tr('q_cancel')}")
        try: raw = input(f"{tr('new_val')} [{cur_default}]: ").strip()
        except (EOFError, KeyboardInterrupt): continue
        if raw.lower() in ("q","quit","exit"): continue
        if raw == '-': nv = ''
        elif raw == '': nv = cur_default
        else: nv = raw
        for i in compatible:
            s = servers[i]
            if pkey == "scheme": s['scheme'] = nv
            elif pkey == "port": s['port'] = nv
            elif pkey == "host_addr": s['host'] = nv
            elif pkey in ("id","password","method"): s[pkey] = nv
            else:
                if nv == "": s['params'].pop(pkey, None)
                else: s['params'][pkey] = nv
        print(f"\n[+] {tr('updated')}: {len(compatible)}")

# ========================================
#  Блок: редактирование серверов
# ========================================

def edit_servers(servers):
    while True:
        clr(); hdr(tr("edit_hdr"))
        show_servers_list(servers)
        print(f"\n  {tr('total')}: {len(servers)}")
        ln()
        print("  " + tr("e1")); print("  " + tr("e2")); print("  " + tr("e3")); print("  " + tr("e4"))
        print("  " + tr("e5")); print("  " + tr("e6")); print("  " + tr("e7")); print("  " + tr("e8"))
        print("  " + tr("e9")); print("  " + tr("e10")); print("  " + tr("e11")); print("  " + tr("eq"))
        ch = _in_choice(f"{tr('choice')}: ", [str(i) for i in range(1, 12)])
        if ch == EXIT or ch == "0": break
        if ch == "1":
            sub = _in_choice(f"{tr('names_q')}: ", ["1","2","3","4"])
            if sub == EXIT: continue
            if sub == "1":
                base = _in(f"{tr('base_name')}: ")
                if base == EXIT or not base: continue
                for i, s in enumerate(servers): s['name'] = f"{base}-{i+1}"
                print(f"[+] {tr('updated')}")
            elif sub == "2":
                sel = _in_multi(f"{tr('numbers')}: ", 1, len(servers))
                if sel == EXIT or not sel: continue
                base = _in(f"{tr('base_name')}: ")
                if base == EXIT or not base: continue
                for idx in sel: servers[idx-1]['name'] = f"{base}-{idx}"
                print(f"[+] {tr('updated')}")
            elif sub == "3":
                sel = _in_multi(f"{tr('numbers')}: ", 1, len(servers))
                if sel == EXIT or not sel: continue
                for idx in sel:
                    nn = _in(f"  {idx}. '{servers[idx-1].get('name','')}' {tr('skip_q')}: ")
                    if nn == EXIT or not nn: continue
                    servers[idx-1]['name'] = nn
                print(f"[+] {tr('updated')}")
            elif sub == "4":
                pre = _in(f"{tr('prefix')}: ")
                if pre == EXIT or not pre: continue
                for s in servers: s['name'] = f"{pre}{s.get('name','')}"
                print(f"[+] {tr('updated')}")
        elif ch == "2":
            sel = _in_multi(f"{tr('numbers')}: ", 1, len(servers))
            if sel == EXIT or not sel: continue
            edit_params_for_group(servers, [i-1 for i in sel])
        elif ch == "3":
            sel = _in_multi(f"{tr('del_q')}: ", 1, len(servers))
            if sel == EXIT or not sel: continue
            ans = _in(f"{tr('del_n')} {len(sel)}? (y/n) [n]: ", default="n")
            if ans and ans.lower() == 'y':
                for i in sorted(sel, reverse=True): servers.pop(i-1)
                print(f"[+] {tr('deleted_n')}: {len(sel)}")
        elif ch == "4":
            servers = delete_by_keyword(servers)
        elif ch == "5":
            uri = _in(f"{tr('link_q')}: ")
            if uri == EXIT or not uri: continue
            p = parse_uri(uri)
            if p: servers.append(p); print(f"[+] {tr('added_ok')}")
            else: print(f"[!] {tr('parse_err')}")
        elif ch == "6": servers = dedupe_menu(servers)
        elif ch == "7": servers = sort_servers(servers)
        elif ch == "8": servers = move_server(servers)
        elif ch == "9": servers = duplicate_servers(servers)
        elif ch == "10":
            kw = _in(f"{tr('kw_q')}: ").lower()
            if kw == EXIT: continue
            found = [(i+1, s) for i, s in enumerate(servers)
                     if kw in s.get('name','').lower() or kw in s['host'].lower() or kw in s['scheme']]
            if found:
                print(f"\n[+] {tr('found')}: {len(found)}")
                for n, s in found: print(f"   {n}. {s.get('name','')} [{s['scheme']}://{s['host']}:{s['port']}]")
            else: print(f"[!] {tr('not_found')}")
            _in("\n" + tr("q_back") + ": ", allow_exit=False)
        elif ch == "11":
            idx = _in_int(f"{tr('file_n')}: ", mn=1, mx=len(servers))
            if idx == EXIT or idx is None: continue
            s = servers[idx-1]
            print(f"\n  URI: {build_uri(s)}")
            print(f"  {tr('u_scheme')}: {s['scheme']}")
            print(f"  {tr('u_host')}: {s['host']}")
            print(f"  {tr('u_port')}: {s['port']}")
            print(f"  {tr('u_cred')}: {s.get('id') or s.get('password') or s.get('method')}")
            print(f"  {tr('u_params')}: {json.dumps(s['params'], ensure_ascii=False, indent=4)}")
            _in("\n" + tr("q_back") + ": ", allow_exit=False)
    return servers

# ========================================
#  Блок: генерация outbound / config
# ========================================

def gen_outbound(s, tag, cfg):
    scheme = s['scheme']; host = s['host']
    try: port = int(s['port']) if str(s['port']).isdigit() else 443
    except Exception: port = 443
    out = {}
    if scheme == 'vless':
        out = {"protocol":"vless",
            "settings":{"vnext":[{"address":host,"port":port,
                "users":[{"id":s.get('id',''),"encryption":"none","flow":s['params'].get('flow','')}]}]},
            "streamSettings":{"network":s['params'].get('type','tcp'),"security":s['params'].get('security','none')},
            "tag":tag}
        sec = out["streamSettings"]["security"]
        if sec == 'reality':
            rs = {"serverName":s['params'].get('sni',''),"fingerprint":s['params'].get('fp','chrome'),
                  "publicKey":s['params'].get('pbk',''),"shortId":s['params'].get('sid','')}
            if 'spiderX' in s['params']: rs["spiderX"] = s['params']['spiderX']
            out["streamSettings"]["realitySettings"] = rs
        elif sec == 'tls':
            tls = {"serverName":s['params'].get('sni', host)}
            if 'alpn' in s['params']: tls["alpn"] = [a.strip() for a in str(s['params']['alpn']).split(',') if a.strip()]
            if 'fp' in s['params']: tls["fingerprint"] = s['params']['fp']
            if 'pinned_certchain_sha256' in s['params']: tls["pinnedPeerCertSha256"] = s['params']['pinned_certchain_sha256']
            if 'verify_peer_cert_by_name' in s['params']: tls["verifyPeerCertByName"] = s['params']['verify_peer_cert_by_name']
            out["streamSettings"]["tlsSettings"] = tls
        net = out["streamSettings"]["network"]
        if net == 'ws':
            ws = {"path":s['params'].get('path','/'), "headers":{"Host":s['params'].get('host', host)}}
            if 'heartbeatPeriod' in s['params']:
                try: ws["heartbeatPeriod"] = int(s['params']['heartbeatPeriod'])
                except Exception: pass
            out["streamSettings"]["wsSettings"] = ws
        elif net == 'grpc':
            gs = {"serviceName":s['params'].get('serviceName',''), "multiMode":s['params'].get('mode','') == 'multi'}
            if 'authority' in s['params']: gs["authority"] = s['params']['authority']
            out["streamSettings"]["grpcSettings"] = gs
        elif net == 'tcp':
            out["streamSettings"]["tcpSettings"] = {"header":{"type":s['params'].get('headerType','none')}}
        elif net in ('xhttp','splithttp'):
            xh = {"path":s['params'].get('path','/'), "host":s['params'].get('host', host), "mode":s['params'].get('mode','auto')}
            if 'concurrency' in s['params']:
                try: xh["concurrency"] = int(s['params']['concurrency'])
                except Exception: pass
            out["streamSettings"]["xhttpSettings"] = xh
        elif net == 'httpupgrade':
            out["streamSettings"]["httpupgradeSettings"] = {"path":s['params'].get('path','/'), "host":s['params'].get('host', host)}
    elif scheme == 'vmess':
        out = {"protocol":"vmess",
            "settings":{"vnext":[{"address":host,"port":port,
                "users":[{"id":s.get('id',''), "alterId":int(s['params'].get('alterId',0)) if str(s['params'].get('alterId','0')).isdigit() else 0,
                          "security":s['params'].get('encryption','auto')}]}]},
            "streamSettings":{"network":s['params'].get('type','tcp'),"security":s['params'].get('security','none')},
            "tag":tag}
        sec = out["streamSettings"]["security"]
        if sec == 'tls':
            tls = {"serverName":s['params'].get('sni', host)}
            if 'alpn' in s['params']: tls["alpn"] = [a.strip() for a in str(s['params']['alpn']).split(',') if a.strip()]
            out["streamSettings"]["tlsSettings"] = tls
        net = out["streamSettings"]["network"]
        if net == 'ws':
            out["streamSettings"]["wsSettings"] = {"path":s['params'].get('path','/'), "headers":{"Host":s['params'].get('host', host)}}
        elif net == 'grpc':
            out["streamSettings"]["grpcSettings"] = {"serviceName":s['params'].get('serviceName',''), "multiMode":s['params'].get('mode','') == 'multi'}
        elif net == 'tcp':
            out["streamSettings"]["tcpSettings"] = {"header":{"type":s['params'].get('headerType','none')}}
    elif scheme in ('hysteria2','hy2'):
        out = {"protocol":"hysteria2",
            "settings":{"address":host,"port":port,"password":s.get('password','')},
            "streamSettings":{"network":"hysteria2","security":"tls",
                "tlsSettings":{"serverName":s['params'].get('sni', host),
                               "alpn":[a.strip() for a in str(s['params'].get('alpn','h3')).split(',') if a.strip()]}},
            "tag":tag}
        if 'obfs' in s['params']:
            out["settings"]["obfs"] = s['params']['obfs']
            if 'obfs-password' in s['params']: out["settings"]["obfsPassword"] = s['params']['obfs-password']
    elif scheme == 'hysteria':
        out = {"protocol":"hysteria",
            "settings":{"address":host,"port":port,"auth":s.get('password','')},
            "streamSettings":{"network":"hysteria","security":"tls",
                "tlsSettings":{"serverName":s['params'].get('sni', host),
                               "alpn":[a.strip() for a in str(s['params'].get('alpn','h3')).split(',') if a.strip()]}},
            "tag":tag}
        if 'up' in s['params']: out["settings"]["up"] = s['params']['up']
        if 'down' in s['params']: out["settings"]["down"] = s['params']['down']
    elif scheme == 'ss':
        out = {"protocol":"shadowsocks",
            "settings":{"servers":[{"address":host,"port":port,"method":s.get('method','aes-256-gcm'),
                                    "password":s.get('password','')}]},
            "tag":tag}
    elif scheme == 'trojan':
        out = {"protocol":"trojan",
            "settings":{"servers":[{"address":host,"port":port,"password":s.get('password','')}]},
            "streamSettings":{"network":s['params'].get('type','tcp'),"security":s['params'].get('security','tls')},
            "tag":tag}
        ts = {"serverName":s['params'].get('sni', host)}
        if 'alpn' in s['params']: ts["alpn"] = [a.strip() for a in str(s['params']['alpn']).split(',') if a.strip()]
        if 'pinned_certchain_sha256' in s['params']: ts["pinnedPeerCertSha256"] = s['params']['pinned_certchain_sha256']
        if 'verify_peer_cert_by_name' in s['params']: ts["verifyPeerCertByName"] = s['params']['verify_peer_cert_by_name']
        out["streamSettings"]["tlsSettings"] = ts
    elif scheme == 'socks5':
        out = {"protocol":"socks","settings":{"servers":[{"address":host,"port":port,"user":s.get('id',''),"pass":s.get('password','')}]},"tag":tag}
    elif scheme == 'http':
        out = {"protocol":"http","settings":{"servers":[{"address":host,"port":port,"user":s.get('id',''),"pass":s.get('password','')}]},"tag":tag}
    elif scheme == 'wireguard':
        peer = {"endpoint":f"{host}:{port}", "publicKey":s.get('password',''),
                "allowedIPs":[x.strip() for x in str(s['params'].get('allowedIPs','0.0.0.0/0')).split(',')]}
        if s['params'].get('presharedKey'): peer["preSharedKey"] = s['params']['presharedKey']
        if s['params'].get('keepalive'):
            try: peer["persistentKeepalive"] = int(s['params']['keepalive'])
            except Exception: pass
        out = {"protocol":"wireguard",
            "settings":{"secretKey":s.get('id',''),"dns":s['params'].get('dns','1.1.1.1'),
                        "mtu":int(s['params'].get('mtu',1420)) if str(s['params'].get('mtu','1420')).isdigit() else 1420,
                        "peers":[peer]},
            "tag":tag}
    else: return None
    if cfg.get('mux_enabled'):
        mux = {"enabled":True, "concurrency":cfg.get('mux_concurrency',8)}
        xc = cfg.get('mux_xudp_concurrency',0)
        if xc != 0:
            mux["xudpConcurrency"] = xc
            mux["xudpProxyUDP443"] = cfg.get('mux_xudp_proxy_udp443','reject')
        out["mux"] = mux
    return out

def merge_group_rules(rules, outbound_type):
    domains = []; others = []
    for r in rules:
        if not isinstance(r, dict): continue
        keys = set(r.keys()) - {'outboundTag', 'balancerTag'}
        if r.get('type') == 'field' and keys == {'type', 'domain'}:
            for d in r.get('domain', []):
                if isinstance(d, str): domains.append(d)
        else: others.append(r)
    result = []
    if domains:
        deduped = process_domain_list(domains)
        rule = {'type':'field', 'domain':deduped}
        if outbound_type == 'proxy': rule['balancerTag'] = 'balancer'
        else: rule['outboundTag'] = outbound_type
        result.append(rule)
    result.extend(others)
    return result

def gen_config(servers, cfg):
    outbounds = []; tags = []; unsupported = []
    for i, s in enumerate(servers):
        base_tag = re.sub(r'[^a-zA-Z0-9_\-]', '_', s.get('name', f"proxy-{i+1}")) or f"proxy-{i+1}"
        tag = base_tag; c = 1
        while tag in tags: tag = f"{base_tag}_{c}"; c += 1
        out = gen_outbound(s, tag, cfg)
        if out: tags.append(tag); outbounds.append(out)
        else: unsupported.append(s.get('name', s['scheme']))
    if unsupported: print(f"[!] {tr('missing_unsupported')}: {', '.join(unsupported)}")
    outbounds.append({"protocol":"freedom","tag":"direct"})
    outbounds.append({"protocol":"blackhole","tag":"block"})

    rt = cfg.get('routing', {})
    order = cfg.get('routing_order', ["block","direct","proxy"])
    groups = {'block':[], 'direct':[], 'proxy':[]}
    if rt.get('block_protocols'): groups['block'].append({"type":"field","protocol":rt['block_protocols'],"outboundTag":"block"})
    if rt.get('block_ips'): groups['block'].append({"type":"field","ip":rt['block_ips'],"outboundTag":"block"})
    if rt.get('block_ports'): groups['block'].append({"type":"field","port":rt['block_ports'],"outboundTag":"block"})
    if rt.get('block_domains'): groups['block'].append({"type":"field","domain":rt['block_domains'],"outboundTag":"block"})
    if rt.get('direct_ips'): groups['direct'].append({"type":"field","ip":rt['direct_ips'],"outboundTag":"direct"})
    if rt.get('direct_ports'): groups['direct'].append({"type":"field","port":rt['direct_ports'],"outboundTag":"direct"})
    if rt.get('direct_domains'): groups['direct'].append({"type":"field","domain":rt['direct_domains'],"outboundTag":"direct"})
    for r in rt.get('custom_rules', []):
        if not isinstance(r, dict): continue
        tag = r.get('outboundTag') or r.get('balancerTag', '')
        if tag == 'block': groups['block'].append(r)
        elif tag == 'direct': groups['direct'].append(r)
        else:
            r2 = dict(r); r2.pop('outboundTag', None); r2['balancerTag'] = 'balancer'; groups['proxy'].append(r2)

    rules = []
    for name in order: rules.extend(merge_group_rules(groups.get(name, []), name))

    gp = cfg.get('global_proxy', 'proxy')
    if gp == 'direct': rules.append({"type":"field","network":"tcp,udp","outboundTag":"direct"})
    elif gp == 'block': rules.append({"type":"field","network":"tcp,udp","outboundTag":"block"})
    else: rules.append({"type":"field","network":"tcp,udp","balancerTag":"balancer"})

    expected = norm_int(cfg.get('balancer_expected',3), 3, 1, 999)
    if len(tags) > 0 and expected > len(tags):
        print(f"[!] expected={expected} {tr('exp_gt')} {len(tags)}.")
        expected = len(tags)

    balancer = {"tag":"balancer", "selector":tags,
        "strategy":{"type":norm_bal(cfg.get('balancer_strategy','leastLoad')),
                    "settings":{"expected":expected,
                                "maxRTT":norm_dur(cfg.get('balancer_max_rtt','2s'),'s'),
                                "tolerance":norm_float(cfg.get('balancer_tolerance',0), 0.0),
                                "baselines":[norm_dur(b,'s') for b in cfg.get('balancer_baselines',['2s'])]}}}
    if tags: balancer["fallbackTag"] = tags[0]
    observatory = {"subjectSelector":tags,
        "probeUrl":cfg.get('observatory_url','https://www.google.com/generate_204'),
        "probeInterval":norm_dur(cfg.get('observatory_interval','1m'),'m'),
        "probeTimeout":norm_dur(cfg.get('observatory_timeout','3s'),'s'),
        "enableConcurrency":True}
    dns = {"servers":cfg.get('dns_servers', DNS_SERVERS), "queryStrategy":cfg.get('dns_query_strategy','UseIP')}
    p_socks, p_http = cfg.get('proxy_ports', [10808,10809])
    sniffing = {"enabled":cfg.get('sniffing_enabled',True),
                "destOverride":cfg.get('sniffing_dest_override', ["http","tls","quic"]),
                "routeOnly":cfg.get('sniffing_route_only', True)}
    inbounds = [
        {"listen":"127.0.0.1","port":p_socks,"protocol":"socks","settings":{"auth":"noauth","udp":True},"sniffing":sniffing,"tag":"socks"},
        {"listen":"127.0.0.1","port":p_http,"protocol":"http","settings":{"allowTransparent":False},"sniffing":sniffing,"tag":"http"}
    ]
    return {"remarks":cfg.get('json_remarks','SubManager Auto'),"log":{"loglevel":"warning"},
            "dns":dns,"inbounds":inbounds,"outbounds":outbounds,
            "routing":{"domainStrategy":"IPIfNonMatch","rules":rules,"balancers":[balancer]},
            "observatory":observatory}

# ========================================
#  Блок: нормализация существующего конфига
# ========================================

def normalize_existing_config_file(path):
    hdr(tr("norm_hdr"))
    if not path.exists():
        print(f"[!] {tr('file_not_found')}: {path}"); return None
    try:
        with open(path, 'r', encoding='utf-8') as f: data = json.load(f)
    except Exception as e:
        print(f"[!] {tr('read_err')}: {e}"); return None
    changes = []
    if 'observatory' in data and isinstance(data['observatory'], dict):
        obs = data['observatory']
        for k, unit in (('probeInterval','m'), ('probeTimeout','s')):
            if k in obs:
                old = obs[k]; new = norm_dur(old, unit)
                if old != new: changes.append(f"observatory.{k}: '{old}' -> '{new}'"); obs[k] = new
    if 'routing' in data and isinstance(data['routing'], dict):
        rt = data['routing']
        bals = rt.get('balancers', [])
        if isinstance(bals, list):
            for bi, b in enumerate(bals):
                if not isinstance(b, dict): continue
                st = b.get('strategy', {})
                if not isinstance(st, dict): continue
                old = st.get('type',''); new = norm_bal(old)
                if old != new: changes.append(f"balancers[{bi}].strategy.type: '{old}' -> '{new}'"); st['type'] = new
                settings = st.get('settings', {})
                if isinstance(settings, dict):
                    if 'maxRTT' in settings:
                        old = settings['maxRTT']; new = norm_dur(old,'s')
                        if old != new: changes.append(f"balancers[{bi}].strategy.settings.maxRTT: '{old}' -> '{new}'"); settings['maxRTT'] = new
                    if 'baselines' in settings and isinstance(settings['baselines'], list):
                        new_bl = []
                        for bv in settings['baselines']:
                            new_v = norm_dur(bv,'s')
                            new_bl.append(new_v)
                            if bv != new_v: changes.append(f"balancers[{bi}].baselines[]: '{bv}' -> '{new_v}'")
                        settings['baselines'] = new_bl
                    if 'expected' in settings:
                        try: e = int(settings['expected'])
                        except Exception: e = 1
                        if e < 1: changes.append(f"balancers[{bi}].expected -> '1'"); settings['expected'] = 1
                    if 'tolerance' in settings:
                        try: t = float(settings['tolerance'])
                        except Exception:
                            t = 0.0; changes.append(f"balancers[{bi}].tolerance -> '0'"); settings['tolerance'] = t
        rules = rt.get('rules', [])
        if isinstance(rules, list):
            for ri, r in enumerate(rules):
                if not isinstance(r, dict): continue
                if r.get('outboundTag') == 'proxy':
                    changes.append(f"rules[{ri}]: outboundTag 'proxy' -> balancerTag 'balancer'")
                    del r['outboundTag']; r['balancerTag'] = 'balancer'
                if 'domain' in r and isinstance(r['domain'], list):
                    old_domains = list(r['domain']); new_domains = process_domain_list(old_domains)
                    if new_domains != old_domains:
                        diff = len(old_domains) - len(new_domains)
                        changes.append(f"rules[{ri}]: domains {len(old_domains)} -> {len(new_domains)} (removed {diff})")
                        r['domain'] = new_domains
    if 'outbounds' in data and isinstance(data['outbounds'], list):
        for oi, ob in enumerate(data['outbounds']):
            if not isinstance(ob, dict): continue
            ss = ob.get('streamSettings', {})
            if not isinstance(ss, dict): continue
            if ss.get('security') == 'tls':
                ts = ss.get('tlsSettings', {})
                if isinstance(ts, dict):
                    if 'allowInsecure' in ts:
                        changes.append(f"outbounds[{oi}].tlsSettings.allowInsecure: removed"); del ts['allowInsecure']
                    if 'verifyPeerCertInNames' in ts:
                        changes.append(f"outbounds[{oi}].verifyPeerCertInNames -> verifyPeerCertByName"); ts['verifyPeerCertByName'] = ts.pop('verifyPeerCertInNames')
                    if 'pinnedPeerCertificateChainSha256' in ts:
                        changes.append(f"outbounds[{oi}].pinnedPeerCertificateChainSha256 -> pinnedPeerCertSha256")
                        ts['pinnedPeerCertSha256'] = ts.pop('pinnedPeerCertificateChainSha256')
    if not changes:
        print(f"[+] {tr('norm_nochange')}"); return data
    print(f"[+] {tr('norm_found')}: {len(changes)}")
    for c in changes: print(f"    - {c}")
    ans = _in(f"\n{tr('norm_save')} [y]: ", default="y")
    if ans and ans.lower() == 'y':
        p = path.parent / (path.stem + "_fixed.json")
        with open(p, 'w', encoding='utf-8') as f: json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"[+] {tr('norm_saved')}: {p}")
        return data
    return data

def normalize_existing_config_menu():
    hdr(tr("norm_hdr"))
    print("  " + tr("n_from_out")); print("  " + tr("n_from_in")); print("  " + tr("n_manual")); print("  " + tr("q_back"))
    ch = _in_choice(f"{tr('choice')}: ", ["1","2","3"])
    if ch == EXIT: return
    path = None
    if ch == "1":
        files = sorted([p for p in OUTPUT_DIR.glob("*.json") if p.is_file()])
        if not files:
            print(f"[!] {tr('no_json_out')}"); _in("\n" + tr("q_back") + ": ", allow_exit=False); return
        for i, f in enumerate(files, 1): print(f"  {i}. {f.name} ({fmt_size(f.stat().st_size)})")
        idx = _in_int(f"{tr('file_n')}: ", mn=1, mx=len(files))
        if idx == EXIT or idx is None: return
        path = files[idx-1]
    elif ch == "2":
        files = sorted([p for p in INPUT_DIR.glob("*.json") if p.is_file()])
        if not files:
            print(f"[!] {tr('no_json_in')}"); _in("\n" + tr("q_back") + ": ", allow_exit=False); return
        for i, f in enumerate(files, 1): print(f"  {i}. {f.name} ({fmt_size(f.stat().st_size)})")
        idx = _in_int(f"{tr('file_n')}: ", mn=1, mx=len(files))
        if idx == EXIT or idx is None: return
        path = files[idx-1]
    elif ch == "3":
        p = _in(f"{tr('path_q')}: ")
        if p == EXIT or not p: return
        path = Path(p)
    if path:
        normalize_existing_config_file(path)
        _in("\n" + tr("q_back") + ": ", allow_exit=False)

def normalize_existing_servers_menu():
    hdr(tr("n_serv_hdr"))
    print("  " + tr("n1")); print("  " + tr("n2")); print("  " + tr("n3")); print("  " + tr("n4")); print("  " + tr("q_back"))
    ch = _in_choice(f"{tr('choice')}: ", ["1","2","3","4"])
    if ch == EXIT: return
    path = None; files = None
    if ch == "1": files = sorted([p for p in BACKUP_DIR.glob("*") if p.is_file()])
    elif ch == "2": files = sorted([p for p in OUTPUT_DIR.glob("*.txt") if p.is_file()])
    elif ch == "3": files = sorted([p for p in INPUT_DIR.glob("*") if p.is_file()])
    elif ch == "4":
        p = _in(f"{tr('path_q')}: ")
        if p == EXIT or not p: return
        path = Path(p)
    if files is not None:
        if not files:
            print(f"[!] {tr('no_files')}"); _in("\n" + tr("q_back") + ": ", allow_exit=False); return
        for i, f in enumerate(files, 1): print(f"  {i}. {f.name} ({fmt_size(f.stat().st_size)})")
        idx = _in_int(f"{tr('file_n')}: ", mn=1, mx=len(files))
        if idx == EXIT or idx is None: return
        path = files[idx-1]
    if path:
        try: raw = path.read_text(encoding='utf-8', errors='ignore')
        except Exception as e:
            print(f"[!] {tr('read_err')}: {e}"); _in("\n" + tr("q_back") + ": ", allow_exit=False); return
        servers, _ = parse_input(auto_decode(raw))
        if not servers:
            print(f"[!] {tr('parse_data')}"); _in("\n" + tr("q_back") + ": ", allow_exit=False); return
        print(f"[+] {tr('serv_parsed')}: {len(servers)}")
        valid = []
        for s in servers:
            if not s.get('host') or not str(s.get('port','')).isdigit(): continue
            s['port'] = str(s['port']); valid.append(s)
        print(f"[+] {tr('serv_valid')}: {len(valid)}")
        if len(valid) != len(servers): print(f"[!] {tr('serv_dropped')}: {len(servers)-len(valid)}")
        ans = _in(f"{tr('serv_save_norm')} [y]: ", default="y")
        if ans and ans.lower() == 'y':
            ts = time.strftime("%Y%m%d_%H%M%S")
            out = BACKUP_DIR / f"normalized_{ts}.txt"
            with open(out, 'w', encoding='utf-8') as f: f.write('\n'.join(build_uri(s) for s in valid))
            print(f"[+] {tr('norm_saved')}: {out}")
        _in("\n" + tr("q_back") + ": ", allow_exit=False)

# ========================================
#  Блок: импорт правил маршрутизации
# ========================================

def parse_shadowrocket_rules(text):
    rules = []
    proxy_kw = ["PROXY","SPEEDPROXY","BESTPROXY","AIPROXY","METAPROXY","TGPROXY","SPOTIFYPROXY"]
    block_kw = ["REJECT","REJECT-DROP","REJECT-200","REJECT-DICT","REJECT-TINYGIF","REJECT-NO-DROP"]
    for raw in text.splitlines():
        s = raw.strip()
        if not s or s.startswith(('#',';','//','[','!')): continue
        if 'URL-REGEX' in s or s.startswith(('RULE-SET','DOMAIN-WILDCARD','AND,','OR,','NOT,')): continue
        parts = [p.strip() for p in s.split(',')]
        if len(parts) < 3: continue
        rt = parts[0].upper(); val = parts[1]; pol = parts[2].upper()
        if pol == 'DIRECT': out = 'direct'
        elif pol in block_kw: out = 'block'
        elif any(p in pol for p in proxy_kw): out = 'proxy'
        else: continue
        rule = None
        if rt == 'DOMAIN-SUFFIX': rule = {"type":"field","domain":[f"domain:{val}"],"outboundTag":out}
        elif rt == 'DOMAIN': rule = {"type":"field","domain":[val],"outboundTag":out}
        elif rt == 'DOMAIN-KEYWORD': rule = {"type":"field","domain":[f"keyword:{val}"],"outboundTag":out}
        elif rt in ('IP-CIDR','IP-CIDR6'): rule = {"type":"field","ip":[val],"outboundTag":out}
        elif rt == 'GEOIP': rule = {"type":"field","ip":[f"geoip:{val.lower()}"],"outboundTag":out}
        elif rt == 'DST-PORT': rule = {"type":"field","port":val,"outboundTag":out}
        elif rt == 'PROTOCOL': rule = {"type":"field","protocol":[val.lower()],"outboundTag":out}
        if rule: rules.append(rule)
    return rules, {}

def parse_adguard_rules(text):
    rules = []
    for raw in text.splitlines():
        s = raw.strip()
        if not s or s.startswith(('!','#','@@')): continue
        if s.startswith(('||','|')):
            d = s.lstrip('|').rstrip('^').strip()
            if d: rules.append({"type":"field","domain":[f"domain:{d}"],"outboundTag":"block"})
    return rules, {}

def parse_blocklist_rules(text):
    rules = []
    for raw in text.splitlines():
        s = raw.strip()
        if not s or s.startswith(('!','#',';','[','//','@@')): continue
        if s.startswith('||'):
            d = s[2:].rstrip('^').strip()
            if d and '.' in d: rules.append({"type":"field","domain":[f"domain:{d}"],"outboundTag":"block"})
            continue
        if ',' in s:
            parts = [p.strip() for p in s.split(',')]
            rt = parts[0].upper(); val = parts[1] if len(parts) > 1 else ''
            if not val: continue
            if rt in ('DOMAIN-SUFFIX','DOMAIN'): rules.append({"type":"field","domain":[f"domain:{val}"],"outboundTag":"block"})
            elif rt == 'DOMAIN-KEYWORD': rules.append({"type":"field","domain":[f"keyword:{val}"],"outboundTag":"block"})
            elif rt in ('IP-CIDR','IP-CIDR6'): rules.append({"type":"field","ip":[val],"outboundTag":"block"})
            elif rt == 'GEOIP': rules.append({"type":"field","ip":[f"geoip:{val.lower()}"],"outboundTag":"block"})
            continue
        if re.fullmatch(r'[A-Za-z0-9._\-]+', s) and '.' in s and not re.fullmatch(r'[\d.]+', s):
            rules.append({"type":"field","domain":[f"domain:{s}"],"outboundTag":"block"})
        elif re.fullmatch(r'[\d.]{7,}', s) or re.fullmatch(r'[0-9a-fA-F:]+/\d+', s):
            rules.append({"type":"field","ip":[s],"outboundTag":"block"})
    return rules, {}

def import_routing_rules(cfg):
    hdr(tr("imp_hdr"))
    print("  " + tr("imp_1")); print("  " + tr("imp_2")); print("  " + tr("imp_3")); print("  " + tr("q_back"))
    ch = _in_choice(f"{tr('choice')}: ", ["1","2","3"])
    if ch == EXIT: return cfg
    parser = {"1":parse_shadowrocket_rules, "2":parse_adguard_rules, "3":parse_blocklist_rules}[ch]
    print("  " + tr("imp_src_1")); print("  " + tr("imp_src_2"))
    ch2 = _in_choice(f"{tr('choice')}: ", ["1","2"])
    if ch2 == EXIT: return cfg
    raw = ""
    if ch2 == "1":
        files = sorted([p for p in ROUTING_DIR.glob("*") if p.is_file()])
        if not files:
            print(f"[!] {tr('folder_empty')}: {ROUTING_DIR}"); _in("\n" + tr("q_back") + ": ", allow_exit=False); return cfg
        for i, f in enumerate(files, 1): print(f"  {i}. {f.name} ({fmt_size(f.stat().st_size)})")
        idx = _in_int(f"{tr('file_n')}: ", mn=1, mx=len(files))
        if idx == EXIT or idx is None: return cfg
        raw = files[idx-1].read_text(encoding='utf-8', errors='ignore')
    else:
        url = _in(f"URL: ")
        if url == EXIT or not url: return cfg
        raw = dl_url(url)
        if not raw:
            print(f"[!] {tr('dl_fail')}"); _in("\n" + tr("q_back") + ": ", allow_exit=False); return cfg
    rules, _ = parser(raw)
    if not rules:
        print(f"[!] {tr('not_found')}"); _in("\n" + tr("q_back") + ": ", allow_exit=False); return cfg
    print(f"\n[+] {tr('imp_rules')}: {len(rules)}")
    ans = _in(f"\n{tr('imp_add')} {len(rules)}? (y/n) [y]: ", default="y")
    if ans and ans.lower() == 'y':
        rt = cfg.get('routing', {}); ex = rt.get('custom_rules', []); ex.extend(rules)
        rt['custom_rules'] = ex; cfg['routing'] = rt; cfg_save(cfg)
        print(f"[+] {tr('imp_added')}: {len(ex)}")
    _in("\n" + tr("q_back") + ": ", allow_exit=False)
    return cfg

# ========================================
#  Блок: роутинг для клиентов
# ========================================

def gen_happ_routing(cfg):
    rt = cfg.get('routing', {})
    profile = {"Name":"SubManager Routing","GlobalProxy":cfg.get('global_proxy') == 'proxy',
        "RemoteDNSDomain":"https://cloudflare-dns.com/dns-query","RemoteDNSType":"DoH",
        "DomesticDNSDomain":"https://dns.comss.one/dns-query","DomesticDNSType":"DoH",
        "GeositeUrl":"https://github.com/v2fly/domain-list-community/releases/latest/download/dlc.dat",
        "GeoipUrl":"https://github.com/v2fly/geoip/releases/download/202501090053/geoip.dat",
        "ProxySites":[], "DirectSites":rt.get('direct_domains', []), "BlockSites":rt.get('block_domains', []),
        "DirectIp":rt.get('direct_ips', []), "BlockIp":rt.get('block_ips', []), "ProxyIp":[],
        "DomainStrategy":cfg.get('dns_query_strategy','IPIfNonMatch'),
        "RouteOrder":"-".join(cfg.get('routing_order',['block','proxy','direct'])),
        "DnsHosts":{}, "UseChunkFiles":False, "LastUpdated":0,
        "RemoteDNSIp":"1.1.1.1","DomesticDNSIp":"83.220.169.155"}
    for r in rt.get('custom_rules', []):
        tag = r.get('outboundTag',''); doms = r.get('domain', []); ips = r.get('ip', [])
        if tag == 'proxy':
            for d in doms: profile["ProxySites"].append(d)
        elif tag == 'direct':
            for d in doms: profile["DirectSites"].append(d)
            for ip in ips: profile["DirectIp"].append(ip)
        elif tag == 'block':
            for d in doms: profile["BlockSites"].append(d)
            for ip in ips: profile["BlockIp"].append(ip)
    return profile

def gen_v2raytun_routing(cfg):
    rt = cfg.get('routing', {})
    rules = list(rt.get('custom_rules', []))
    if rt.get('block_domains'): rules.append({"type":"field","domain":rt['block_domains'],"outboundTag":"block"})
    if rt.get('block_ips'): rules.append({"type":"field","ip":rt['block_ips'],"outboundTag":"block"})
    if rt.get('direct_domains'): rules.append({"type":"field","domain":rt['direct_domains'],"outboundTag":"direct"})
    if rt.get('direct_ips'): rules.append({"type":"field","ip":rt['direct_ips'],"outboundTag":"direct"})
    return {"name":"SubManager","domainStrategy":cfg.get('dns_query_strategy','AsIs'),"domainMatcher":"hybrid","rules":rules}

def routing_menu(cfg):
    while True:
        clr(); hdr(tr("rt_hdr"))
        rt = cfg.get('routing', {})
        print(f"  {tr('rt_direct')}: {len(rt.get('direct_domains', []))}")
        print(f"  {tr('rt_block')}:  {len(rt.get('block_domains', []))}")
        print(f"  {tr('rt_dip')}:     {len(rt.get('direct_ips', []))}")
        print(f"  {tr('rt_bip')}:     {len(rt.get('block_ips', []))}")
        print(f"  {tr('rt_cr')}:  {len(rt.get('custom_rules', []))}")
        print(f"  {tr('rt_order')}:       {' -> '.join(cfg.get('routing_order', []))}")
        print(f"  {tr('rt_global')}:    {cfg.get('global_proxy')}")
        ln()
        for k in ("rt_1","rt_2","rt_3","rt_4","rt_5","rt_6","rt_7","rt_8"): print("  " + tr(k))
        print("  " + tr("q_back"))
        ch = _in_choice(f"{tr('choice')}: ", [str(i) for i in range(1, 9)])
        if ch == EXIT: break
        if ch == "1": cfg = import_routing_rules(cfg)
        elif ch == "2":
            cr = rt.get('custom_rules', [])
            if not cr:
                print(f"[!] {tr('cr_empty')}"); _in("\n" + tr("q_back") + ": ", allow_exit=False); continue
            print(f"  {tr('total')}: {len(cr)}")
            for i, r in enumerate(cr[:30], 1): print(f"  {i:3}. {json.dumps(r, ensure_ascii=False)[:100]}")
            if len(cr) > 30: print(f"  ... +{len(cr)-30}")
            ln()
            print("  1 - " + tr("clear_all")); print("  2 - " + tr("del_by_n")); print("  " + tr("q_back"))
            s = _in_choice(f"{tr('choice')}: ", ["1","2"])
            if s == "1":
                a = _in(f"{tr('clear_q')} [n]: ", default="n")
                if a and a.lower() == 'y':
                    cfg['routing']['custom_rules'] = []; cfg_save(cfg); print(f"[+] {tr('cleared')}")
            elif s == "2":
                sel = _in_multi(f"{tr('del_q')}: ", 1, len(cr))
                if sel and sel != EXIT:
                    for i in sorted(sel, reverse=True): cr.pop(i-1)
                    cfg['routing']['custom_rules'] = cr; cfg_save(cfg)
                    print(f"[+] {tr('deleted_n')}: {len(sel)}")
        elif ch == "3":
            v = _in(f"{tr('dns_remote')} [https://cloudflare-dns.com/dns-query]: ")
            if v != EXIT and v: cfg['routing_remote_dns'] = v
            v = _in(f"{tr('dns_local')} [https://dns.comss.one/dns-query]: ")
            if v != EXIT and v: cfg['routing_domestic_dns'] = v
            cfg_save(cfg)
        elif ch == "4":
            print(f"  {tr('cur')}: {' -> '.join(cfg.get('routing_order', []))}")
            v = _in(f"{tr('order_q')}: ")
            if v == EXIT: continue
            parts = [p.strip().lower() for p in v.split(',') if p.strip()]
            if all(p in ('block','direct','proxy') for p in parts) and len(set(parts)) == 3:
                cfg['routing_order'] = parts; cfg_save(cfg); print(f"[+] {tr('saved')}")
            else: print(f"[!] {tr('need_all_three')}")
        elif ch == "5":
            gp = _in_choice(f"{tr('global_q')} [{cfg.get('global_proxy')}]: ", ['proxy','direct','block'])
            if gp != EXIT: cfg['global_proxy'] = gp; cfg_save(cfg)
        elif ch == "6":
            profile = gen_happ_routing(cfg)
            b = base64.b64encode(json.dumps(profile, ensure_ascii=False).encode('utf-8')).decode('ascii')
            p = OUTPUT_DIR / "happ_routing.txt"
            with open(p, 'w', encoding='utf-8') as f: f.write(f"happ://routing/add/{b}")
            print(f"[+] {tr('happ_saved')}: {p}")
            _in("\n" + tr("q_back") + ": ", allow_exit=False)
        elif ch == "7":
            profile = gen_v2raytun_routing(cfg)
            b = base64.b64encode(json.dumps(profile, ensure_ascii=False).encode('utf-8')).decode('ascii')
            p = OUTPUT_DIR / "v2raytun_routing.txt"
            with open(p, 'w', encoding='utf-8') as f: f.write(f"v2rayTun://import_route/{b}")
            print(f"[+] {tr('v2r_saved')}: {p}")
            _in("\n" + tr("q_back") + ": ", allow_exit=False)
        elif ch == "8":
            profile = gen_happ_routing(cfg)
            p = OUTPUT_DIR / "routing_profile.json"
            with open(p, 'w', encoding='utf-8') as f: f.write(json.dumps(profile, ensure_ascii=False, indent=2))
            print(f"[+] {tr('rt_json')}: {p}")
            _in("\n" + tr("q_back") + ": ", allow_exit=False)
    return cfg

# ========================================
#  Блок: меню настроек генерации
# ========================================

def config_menu(servers, cfg):
    while True:
        clr(); hdr(tr("cfg_hdr"))
        rt = cfg.get('routing', {})
        print(f"  {tr('cfg_jname')}: {cfg.get('json_name')}.json")
        print(f"  {tr('cfg_jrem')}:  {cfg.get('json_remarks')}")
        print(f"  {tr('cfg_dns')}:            {', '.join(cfg.get('dns_servers', [])[:3])}...")
        print(f"  {tr('cfg_dns_strat')}:  {cfg.get('dns_query_strategy')}")
        print(f"  {tr('cfg_probe')}:      {cfg.get('observatory_url')}")
        print(f"  {tr('cfg_int')}:       {cfg.get('observatory_interval')}")
        print(f"  {tr('cfg_to')}:        {cfg.get('observatory_timeout')}")
        print(f"  {tr('cfg_bal')}:       {cfg.get('balancer_strategy')} (exp={cfg.get('balancer_expected')}, maxRTT={cfg.get('balancer_max_rtt')})")
        print(f"  {tr('cfg_ports')}:          SOCKS {cfg.get('proxy_ports',[10808,10809])[0]}, HTTP {cfg.get('proxy_ports',[10808,10809])[1]}")
        print(f"  {tr('cfg_mux')}:            {'ON' if cfg.get('mux_enabled') else 'OFF'}")
        print(f"  {tr('cfg_global')}:     {cfg.get('global_proxy')}")
        print(f"  {tr('cfg_sniff')}:       {'ON' if cfg.get('sniffing_enabled') else 'OFF'}")
        print(f"  {tr('cfg_order')}: {' -> '.join(cfg.get('routing_order', []))}")
        print(f"  {tr('cfg_cr')}:   {len(rt.get('custom_rules', []))}")
        ln()
        for k in ("cfg_1","cfg_2","cfg_3","cfg_4","cfg_5","cfg_6","cfg_7","cfg_8","cfg_9","cfg_10","cfg_11","cfg_12","cfg_13","cfg_14","cfg_15","cfg_16","cfg_17"):
            print("  " + tr(k))
        print("  " + tr("q_back"))
        ch = _in_choice(f"{tr('choice')}: ", [str(i) for i in range(1, 18)])
        if ch == EXIT: break
        if ch == "1":
            v = _in(f"{tr('dns_csv')} [{','.join(cfg.get('dns_servers', []))}]: ")
            if v == EXIT: continue
            if v: cfg['dns_servers'] = [x.strip() for x in v.split(',') if x.strip()]
            st = _in_choice(f"{tr('strategy')} [{cfg.get('dns_query_strategy')}]: ", ['UseIP','UseIPv4','UseIPv6','AsIs'])
            if st != EXIT: cfg['dns_query_strategy'] = st
            cfg_save(cfg)
        elif ch == "2":
            u = _in(f"{tr('dns_url')} [{cfg.get('observatory_url')}]: ")
            if u == EXIT: continue
            if u: cfg['observatory_url'] = u
            i = _in(f"{tr('interval')} [{cfg.get('observatory_interval')}]: ")
            if i != EXIT and i: cfg['observatory_interval'] = norm_dur(i, 'm')
            t = _in(f"{tr('timeout')} [{cfg.get('observatory_timeout')}]: ")
            if t != EXIT and t: cfg['observatory_timeout'] = norm_dur(t, 's')
            cfg_save(cfg)
        elif ch == "3":
            st = _in_choice(f"{tr('strategy')} [{cfg.get('balancer_strategy')}]: ", ['leastLoad','leastPing','random','roundRobin'])
            if st != EXIT: cfg['balancer_strategy'] = norm_bal(st)
            e = _in_int(f"{tr('expected')} [{cfg.get('balancer_expected')}]: ", default=cfg.get('balancer_expected'))
            if e != EXIT and e is not None: cfg['balancer_expected'] = e
            m = _in(f"{tr('maxrtt')} [{cfg.get('balancer_max_rtt')}]: ")
            if m != EXIT and m: cfg['balancer_max_rtt'] = norm_dur(m, 's')
            tol = _in(f"{tr('tolerance')} [{cfg.get('balancer_tolerance')}]: ")
            if tol != EXIT and tol: cfg['balancer_tolerance'] = norm_float(tol, 0.0)
            bl = _in(f"{tr('baselines')} [{','.join(cfg.get('balancer_baselines', ['2s']))}]: ")
            if bl != EXIT and bl: cfg['balancer_baselines'] = [norm_dur(x, 's') for x in bl.split(',') if x.strip()]
            cfg_save(cfg)
        elif ch == "4":
            ps = _in_int(f"SOCKS [{cfg.get('proxy_ports', [10808,10809])[0]}]: ", default=cfg.get('proxy_ports', [10808,10809])[0])
            if ps == EXIT: continue
            ph = _in_int(f"HTTP [{cfg.get('proxy_ports', [10808,10809])[1]}]: ", default=cfg.get('proxy_ports', [10808,10809])[1])
            if ph == EXIT: continue
            cfg['proxy_ports'] = [ps, ph]; cfg_save(cfg)
        elif ch == "5":
            print(f"  {tr('cur')}: {rt.get('direct_domains', [])}")
            print(f"  {tr('hints')}: {', '.join(GEOSITE_SUGG[:10])}")
            v = _in(f"{tr('direct_d')}: ")
            if v == EXIT: continue
            cfg['routing']['direct_domains'] = [x.strip() for x in v.split(',') if x.strip()] if v else []
            cfg_save(cfg)
        elif ch == "6":
            print(f"  {tr('cur')}: {rt.get('block_domains', [])}")
            print(f"  {tr('hints')}: {', '.join(GEOSITE_SUGG[:10])}")
            v = _in(f"{tr('block_d')}: ")
            if v == EXIT: continue
            cfg['routing']['block_domains'] = [x.strip() for x in v.split(',') if x.strip()] if v else []
            cfg_save(cfg)
        elif ch == "7":
            print(f"  Direct IP: {rt.get('direct_ips', [])}")
            print(f"  {tr('hints')}: {', '.join(GEOIP_SUGG)}")
            v = _in(f"{tr('direct_ip')}: ")
            if v != EXIT: cfg['routing']['direct_ips'] = [x.strip() for x in v.split(',') if x.strip()] if v else []
            print(f"  Block IP: {rt.get('block_ips', [])}")
            v = _in(f"{tr('block_ip')}: ")
            if v != EXIT: cfg['routing']['block_ips'] = [x.strip() for x in v.split(',') if x.strip()] if v else []
            cfg_save(cfg)
        elif ch == "8":
            print(f"  {tr('cur')}: {rt.get('block_protocols', [])}")
            v = _in(f"{tr('protos')}: ")
            if v == EXIT: continue
            cfg['routing']['block_protocols'] = [x.strip() for x in v.split(',') if x.strip()] if v else []
            cfg_save(cfg)
        elif ch == "9":
            print(f"  {tr('cur')}: {' -> '.join(cfg.get('routing_order', []))}")
            v = _in(f"{tr('order_q')}: ")
            if v == EXIT: continue
            parts = [p.strip().lower() for p in v.split(',') if p.strip()]
            if all(p in ('block','direct','proxy') for p in parts) and len(set(parts)) == 3:
                cfg['routing_order'] = parts; cfg_save(cfg); print(f"[+] {tr('saved')}")
            else: print(f"[!] {tr('need_all_three')}")
            _in("\n" + tr("q_back") + ": ", allow_exit=False)
        elif ch == "10": cfg = import_routing_rules(cfg)
        elif ch == "11":
            cr = rt.get('custom_rules', [])
            if not cr:
                print(f"[!] {tr('cr_empty')}"); _in("\n" + tr("q_back") + ": ", allow_exit=False); continue
            print(f"  {tr('total')}: {len(cr)}")
            for i, r in enumerate(cr[:30], 1): print(f"  {i:3}. {json.dumps(r, ensure_ascii=False)[:100]}")
            if len(cr) > 30: print(f"  ... +{len(cr)-30}")
            ln()
            print("  1 - " + tr("clear_all")); print("  2 - " + tr("del_by_n")); print("  " + tr("q_back"))
            s = _in_choice(f"{tr('choice')}: ", ["1","2"])
            if s == "1":
                a = _in(f"{tr('clear_q')} [n]: ", default="n")
                if a and a.lower() == 'y':
                    cfg['routing']['custom_rules'] = []; cfg_save(cfg); print(f"[+] {tr('cleared')}")
            elif s == "2":
                sel = _in_multi(f"{tr('del_q')}: ", 1, len(cr))
                if sel and sel != EXIT:
                    for i in sorted(sel, reverse=True): cr.pop(i-1)
                    cfg['routing']['custom_rules'] = cr; cfg_save(cfg)
                    print(f"[+] {tr('deleted_n')}: {len(sel)}")
        elif ch == "12":
            gp = _in_choice(f"{tr('global_q')} [{cfg.get('global_proxy')}]: ", ['proxy','direct','block'])
            if gp != EXIT: cfg['global_proxy'] = gp; cfg_save(cfg)
        elif ch == "13":
            print(f"  Mux: {'ON' if cfg.get('mux_enabled') else 'OFF'}")
            en = _in(f"{tr('mux_on')}: ")
            if en == EXIT: continue
            if en: cfg['mux_enabled'] = en.lower() == 'y'
            if cfg.get('mux_enabled'):
                c = _in_int(f"{tr('concurrency')} [{cfg.get('mux_concurrency')}]: ", default=cfg.get('mux_concurrency'))
                if c != EXIT and c is not None: cfg['mux_concurrency'] = c
                xc = _in_int(f"{tr('xudp_c')} [{cfg.get('mux_xudp_concurrency')}]: ", default=cfg.get('mux_xudp_concurrency'))
                if xc != EXIT and xc is not None: cfg['mux_xudp_concurrency'] = xc
                xp = _in_choice(f"{tr('xudp_p')} [{cfg.get('mux_xudp_proxy_udp443')}]: ", ['reject','skip','allow'])
                if xp != EXIT: cfg['mux_xudp_proxy_udp443'] = xp
            cfg_save(cfg)
        elif ch == "14":
            en = _in_choice(f"Sniffing [{cfg.get('sniffing_enabled')}]: ", ['y','n'])
            if en != EXIT: cfg['sniffing_enabled'] = en.lower() == 'y'
            if cfg.get('sniffing_enabled'):
                v = _in(f"{tr('dest_over')} [{','.join(cfg.get('sniffing_dest_override', []))}]: ")
                if v != EXIT and v: cfg['sniffing_dest_override'] = [x.strip() for x in v.split(',') if x.strip()]
                ro = _in_choice(f"{tr('route_only')} [{cfg.get('sniffing_route_only')}]: ", ['y','n'])
                if ro != EXIT: cfg['sniffing_route_only'] = ro.lower() == 'y'
            cfg_save(cfg)
        elif ch == "15":
            n = _in(f"{tr('jname_q')} [{cfg.get('json_name')}]: ")
            if n != EXIT and n: cfg['json_name'] = n; cfg_save(cfg)
        elif ch == "16":
            print(f"  {tr('jrem_cur')}: {cfg.get('json_remarks')}")
            n = _in(f"{tr('jrem_q')} [{cfg.get('json_remarks')}]: ")
            if n == EXIT: continue
            if n:
                cfg['json_remarks'] = n
                auto = _in(f"{tr('jname_auto')} [n]: ", default="n")
                if auto == EXIT: continue
                if auto.lower() == 'y':
                    cfg['json_name'] = sanitize_fn(transliterate(n)); cfg['json_use_remarks_as_name'] = True
                else: cfg['json_use_remarks_as_name'] = False
                cfg_save(cfg)
        elif ch == "17":
            a = _in(f"{tr('reset_q')} [n]: ", default="n")
            if a and a.lower() == 'y':
                cfg = cfg_default(); cfg_save(cfg); print(f"[+] {tr('reset_done')}")
    return cfg

# ========================================
#  Блок: экспорт / сохранение
# ========================================

def save_base64(servers, name="servers"):
    lines = [build_uri(s) for s in servers]
    raw = '\n'.join(lines)
    p1 = OUTPUT_DIR / f"{name}.txt"; p2 = OUTPUT_DIR / f"{name}_base64.txt"
    with open(p1, 'w', encoding='utf-8') as f: f.write(raw)
    with open(p2, 'w', encoding='utf-8') as f: f.write(base64.b64encode(raw.encode('utf-8')).decode('ascii'))
    print(f"[+] {tr('links_saved')}: {p1}")
    print(f"[+] {tr('b64_saved')}: {p2}")
    print(f"[+] {tr('str_count')}: {len(lines)}")

def save_json(config, cfg, name_override=None, remarks_override=None):
    name = name_override or cfg.get('json_name', 'xray_config')
    if not name.endswith('.json'): name += '.json'
    if remarks_override is not None: config['remarks'] = remarks_override
    p = OUTPUT_DIR / name
    with open(p, 'w', encoding='utf-8') as f: json.dump(config, f, ensure_ascii=False, indent=2)
    print(f"[+] JSON: {p}")
    return p

def ask_json_name_and_remarks(cfg):
    dn = cfg.get('json_name', 'xray_config'); dr = cfg.get('json_remarks', 'SubManager Auto')
    print(f"\n[?] {tr('jname_cfg')}")
    print(f"    {tr('jname_cur')}:    {dn}.json")
    print(f"    {tr('jrem_cur')}:   {dr}")
    print(f"    {tr('jenter_keep')}")
    use = _in(f"{tr('jchange_q')} [n]: ", default="n")
    if use == EXIT: return None, None
    if use.lower() != 'y': return dn, dr
    rem = _in(f"{tr('jrem_new')} [{dr}]: ", default=dr)
    if rem == EXIT: return None, None
    cfg['json_remarks'] = rem
    auto = _in(f"{tr('jname_auto')} [n]: ", default="n")
    if auto == EXIT: return None, None
    if auto.lower() == 'y':
        fn = sanitize_fn(transliterate(rem)); cfg['json_use_remarks_as_name'] = True
        cfg_save(cfg); print(f"    {tr('jname_will')}: {fn}.json")
        return fn, rem
    else:
        nm = _in(f"{tr('jname_noext')} [{dn}]: ", default=dn)
        if nm == EXIT: return None, None
        cfg['json_name'] = nm; cfg_save(cfg); return nm, rem

def export_menu(servers, cfg):
    while True:
        clr(); hdr(tr("exp_sel_hdr"))
        show_servers_list(servers)
        print(f"\n  {tr('total')}: {len(servers)}")
        ln()
        print("  " + tr("exp_1")); print("  " + tr("exp_2")); print("  " + tr("q_back"))
        ch = _in_choice(f"{tr('choice')}: ", ["1","2"])
        if ch == EXIT: break
        sel = _in_multi(f"{tr('exp_sel_n')}: ", 1, len(servers))
        if sel == EXIT or not sel: continue
        subset = [servers[i-1] for i in sel]
        if ch == "1":
            name = _in(f"{tr('exp_name')} [servers]: ", default="servers")
            if name == EXIT: name = "servers"
            save_base64(subset, name)
        elif ch == "2":
            name = _in(f"{tr('exp_json_name')} [selected_config]: ", default="selected_config")
            if name == EXIT: name = "selected_config"
            remarks = _in(f"{tr('exp_rem')} [{cfg.get('json_remarks','SubManager')}]: ", default=cfg.get('json_remarks','SubManager'))
            if remarks == EXIT: remarks = cfg.get('json_remarks','SubManager')
            cfg2 = copy.deepcopy(cfg); cfg2['json_name'] = name
            save_json(gen_config(subset, cfg2), cfg2, name, remarks)
        _in("\n" + tr("q_back") + ": ", allow_exit=False)

def backup_servers(servers, name="backup"):
    ts = time.strftime("%Y%m%d_%H%M%S")
    p = BACKUP_DIR / f"{name}_{ts}.txt"
    with open(p, 'w', encoding='utf-8') as f: f.write('\n'.join(build_uri(s) for s in servers))
    print(f"[+] {tr('backup_ok')}: {p}")

def stats(servers):
    clr(); hdr(tr("stat_hdr"))
    if not servers:
        print(f"  {tr('no_serv')}"); _in("\n" + tr("q_back") + ": ", allow_exit=False); return
    print(f"  {tr('total_serv')}: {len(servers)}")
    by_p, by_t, by_s = {}, {}, {}
    for s in servers:
        by_p[s['scheme']] = by_p.get(s['scheme'], 0) + 1
        t = s['params'].get('type','tcp'); by_t[t] = by_t.get(t, 0) + 1
        sec = s['params'].get('security','none'); by_s[sec] = by_s.get(sec, 0) + 1
    print(f"\n  {tr('by_proto')}:")
    for k, v in sorted(by_p.items()): print(f"    {k:15} : {v}")
    print(f"\n  {tr('by_transp')}:")
    for k, v in sorted(by_t.items()): print(f"    {k:15} : {v}")
    print(f"\n  {tr('by_sec')}:")
    for k, v in sorted(by_s.items()): print(f"    {k:15} : {v}")
    _in("\n" + tr("q_back") + ": ", allow_exit=False)

def save_yaml_clash(servers, name="clash_proxies.yaml"):
    lines = ["proxies:"]
    for s in servers:
        n = s.get('name', 'proxy')
        if s['scheme'] == 'vless':
            lines.append(f"  - name: \"{n}\""); lines.append(f"    type: vless")
            lines.append(f"    server: {s['host']}"); lines.append(f"    port: {s['port']}")
            lines.append(f"    uuid: {s.get('id', '')}"); lines.append(f"    network: {s['params'].get('type', 'tcp')}")
            lines.append(f"    tls: {str(s['params'].get('security') == 'tls').lower()}")
            if s['params'].get('security') == 'reality':
                lines.append(f"    reality-opts:")
                lines.append(f"      public-key: {s['params'].get('pbk', '')}")
                lines.append(f"      short-id: {s['params'].get('sid', '')}")
                lines.append(f"    servername: {s['params'].get('sni', '')}")
            if s['params'].get('flow'): lines.append(f"    flow: {s['params']['flow']}")
        elif s['scheme'] == 'ss':
            lines.append(f"  - name: \"{n}\""); lines.append(f"    type: ss")
            lines.append(f"    server: {s['host']}"); lines.append(f"    port: {s['port']}")
            lines.append(f"    cipher: {s.get('method', '')}"); lines.append(f"    password: \"{s.get('password', '')}\"")
        elif s['scheme'] in ('hysteria2','hy2','hysteria'):
            lines.append(f"  - name: \"{n}\""); lines.append(f"    type: hysteria2")
            lines.append(f"    server: {s['host']}"); lines.append(f"    port: {s['port']}")
            lines.append(f"    password: \"{s.get('password', '')}\"")
            if 'sni' in s['params']: lines.append(f"    sni: {s['params']['sni']}")
        elif s['scheme'] == 'trojan':
            lines.append(f"  - name: \"{n}\""); lines.append(f"    type: trojan")
            lines.append(f"    server: {s['host']}"); lines.append(f"    port: {s['port']}")
            lines.append(f"    password: \"{s.get('password', '')}\"")
            if 'sni' in s['params']: lines.append(f"    sni: {s['params']['sni']}")
    p = OUTPUT_DIR / name
    with open(p, 'w', encoding='utf-8') as f: f.write('\n'.join(lines))
    print(f"[+] Clash YAML: {p}")

# ========================================
#  Блок: универсальный редактор JSON
# ========================================

FIELD_HINTS = {"Name":"Name","GlobalProxy":"GlobalProxy true/false","UseChunkFiles":"UseChunkFiles true/false",
"RemoteDns":"RemoteDns IP","DomesticDns":"DomesticDns IP","RemoteDNSType":"RemoteDNSType","RemoteDNSDomain":"RemoteDNSDomain URL",
"RemoteDNSIP":"RemoteDNSIP","DomesticDNSType":"DomesticDNSType","DomesticDNSDomain":"DomesticDNSDomain URL",
"DomesticDNSIP":"DomesticDNSIP","Geoipurl":"GeoIP URL","Geositeurl":"GeoSite URL","LastUpdated":"LastUpdated unix",
"RouteOrder":"RouteOrder","DomainStrategy":"DomainStrategy","FakeDNS":"FakeDNS true/false",
"DnsHosts":"DnsHosts object","DirectSites":"DirectSites list","DirectIp":"DirectIp list","ProxySites":"ProxySites list",
"ProxyIp":"ProxyIp list","BlockSites":"BlockSites list","BlockIp":"BlockIp list"}
PREF_ORDER = ["Name","GlobalProxy","UseChunkFiles","RemoteDns","DomesticDns","RemoteDNSType","RemoteDNSDomain",
"RemoteDNSIP","DomesticDNSType","DomesticDNSDomain","DomesticDNSIP","Geoipurl","Geositeurl","LastUpdated","DnsHosts",
"RouteOrder","DirectSites","DirectIp","ProxySites","ProxyIp","BlockSites","BlockIp","DomainStrategy","FakeDNS"]

def uje_ordered_keys(cfg):
    keys = list(cfg.keys())
    ordered = [k for k in PREF_ORDER if k in keys]
    extra = [k for k in keys if k not in ordered]
    return ordered + sorted(extra)

def uje_load(path):
    try:
        with open(path, 'r', encoding='utf-8') as f: return json.load(f)
    except Exception as e:
        print(f"[!] {tr('read_err')}: {e}"); return None

def uje_save(path, data):
    try:
        with open(path, 'w', encoding='utf-8') as f: json.dump(data, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        print(f"[!] {e}"); return False

def uje_edit_string(cfg, key):
    cur = str(cfg.get(key, ''))
    print(f"  {tr('uje_cur')}: {cur}")
    v = _in(f"  {tr('uje_new_val')} {tr('uje_edit_hint')}: ")
    if v == EXIT: return False
    if v == '-':
        cfg.pop(key, None); print(f"[+] {tr('uje_deleted')}"); return True
    if v == '':
        print(f"[*] {tr('uje_nochange')}"); return False
    cfg[key] = v
    print(f"[+] {tr('uje_updated')}: {key} = {v}"); return True

def uje_edit_list(cfg, key):
    cur = cfg.get(key, [])
    if not isinstance(cur, list): cur = []
    while True:
        clr(); hdr(f"{tr('uje_list_hdr')}: {key}")
        print(f"  {tr('uje_elems')}: {len(cur)}")
        for i, v in enumerate(cur[:40], 1): print(f"    {i:3}. {v}")
        if len(cur) > 40: print(f"    ... +{len(cur)-40}")
        ln()
        for k in ("uje_l1","uje_l2","uje_l3","uje_l4","uje_l5","uje_l6"): print("  " + tr(k))
        print("  " + tr("uje_back"))
        ch = _in_choice(f"  {tr('choice')}: ", ["1","2","3","4","5","6"])
        if ch == EXIT: return
        if ch == "1":
            while True:
                v = input(f"  {tr('uje_elem')}: ").strip()
                if v.lower() in ("q","quit","exit") or not v: break
                cur.append(v); print(f"  [+] {v}")
            cfg[key] = cur
        elif ch == "2":
            if not cur: continue
            idx = _in_int(f"  {tr('uje_del_n')}: ", mn=1, mx=len(cur))
            if idx == EXIT or idx is None: continue
            cur.pop(idx-1); cfg[key] = cur; print(f"[+] {tr('uje_deleted')}")
        elif ch == "3":
            if not cur: continue
            sel = _in(f"  {tr('uje_del_multi')}: ")
            if sel == EXIT or not sel: continue
            idxs = []
            try:
                for p in sel.split(','):
                    p = p.strip()
                    if '-' in p:
                        a, b = p.split('-', 1)
                        for x in range(int(a), int(b)+1):
                            if 1 <= x <= len(cur) and (x-1) not in idxs: idxs.append(x-1)
                    else:
                        x = int(p)
                        if 1 <= x <= len(cur) and (x-1) not in idxs: idxs.append(x-1)
                for i in sorted(idxs, reverse=True): cur.pop(i)
                cfg[key] = cur; print(f"[+] {tr('uje_del_range')}: {len(idxs)}")
            except Exception: print(f"[!] {tr('uje_parse_err')}")
        elif ch == "4":
            a = _in(f"  {tr('uje_del_all_q')} [n]: ", default="n")
            if a and a.lower() == 'y': cfg[key] = []; print(f"[+] {tr('uje_del_all')}")
        elif ch == "5":
            if not cur: continue
            idx = _in_int(f"  {tr('uje_rep_n')}: ", mn=1, mx=len(cur))
            if idx == EXIT or idx is None: continue
            print(f"  {tr('uje_cur_val')}: {cur[idx-1]}")
            v = _in(f"  {tr('uje_new_val')}: ")
            if v == EXIT or not v: continue
            cur[idx-1] = v; cfg[key] = cur; print(f"[+] {tr('uje_replaced')}")
        elif ch == "6":
            a = _in(f"  {tr('uje_del_field_q')} [n]: ", default="n")
            if a and a.lower() == 'y':
                cfg.pop(key, None); print(f"[+] {tr('uje_del_field')}"); return
        if ch in ("1","2","3","4","5"): _in("\n" + tr("q_back") + ": ", allow_exit=False)

def uje_edit_dict(cfg, key):
    cur = cfg.get(key, {})
    if not isinstance(cur, dict): cur = {}
    while True:
        clr(); hdr(f"{tr('uje_dict_hdr')}: {key}")
        print(f"  {tr('uje_keys')}: {len(cur)}")
        keys_list = list(cur.keys())
        for i, k in enumerate(keys_list, 1):
            v = str(cur[k])
            if len(v) > 40: v = v[:37] + "..."
            print(f"    {i:3}. {k} = {v}")
        ln()
        for k in ("uje_d1","uje_d2","uje_d3","uje_d4"): print("  " + tr(k))
        print("  " + tr("uje_back"))
        ch = _in_choice(f"  {tr('choice')}: ", ["1","2","3","4"])
        if ch == EXIT: return
        if ch == "1":
            k = _in(f"  {tr('uje_key_n')}: ")
            if k == EXIT or not k: continue
            v = _in(f"  {tr('uje_val_n')}: ")
            if v == EXIT: continue
            cur[k] = v; cfg[key] = cur; print("[+]")
        elif ch == "2":
            if not cur: continue
            idx = _in_int(f"  {tr('uje_del_n')}: ", mn=1, mx=len(cur))
            if idx == EXIT or idx is None: continue
            k = keys_list[idx-1]
            print(f"  {tr('uje_cur_val')}: {cur[k]}")
            v = _in(f"  {tr('uje_new_val')}: ")
            if v == EXIT or not v: continue
            cur[k] = v; cfg[key] = cur; print(f"[+] {tr('uje_updated')}")
        elif ch == "3":
            if not cur: continue
            idx = _in_int(f"  {tr('uje_del_n')}: ", mn=1, mx=len(cur))
            if idx == EXIT or idx is None: continue
            cur.pop(keys_list[idx-1]); cfg[key] = cur; print(f"[+] {tr('uje_deleted')}")
        elif ch == "4":
            a = _in(f"  {tr('uje_del_field_q')} [n]: ", default="n")
            if a and a.lower() == 'y':
                cfg.pop(key, None); print(f"[+] {tr('uje_del_field')}"); return
        if ch in ("1","2","3"): _in("\n" + tr("q_back") + ": ", allow_exit=False)

def uje_add_field(cfg):
    clr(); hdr(tr("uje_field_hdr"))
    sugg = [k for k in FIELD_HINTS if k not in cfg]
    if sugg:
        print(f"  {tr('uje_sugg')}:")
        for i, k in enumerate(sugg, 1): print(f"    {i}. {k}")
        ln()
    print("  " + tr("uje_pick_sugg")); print("  " + tr("uje_pick_own")); print("  " + tr("uje_back"))
    s = _in_choice(f"  {tr('choice')}: ", ["1","2"])
    if s == EXIT: return
    if s == "1":
        if not sugg:
            print(f"[!] {tr('uje_all_have')}"); _in("\n" + tr("q_back") + ": ", allow_exit=False); return
        idx = _in_int(f"  {tr('uje_del_n')}: ", mn=1, mx=len(sugg))
        if idx == EXIT or idx is None: return
        new_key = sugg[idx-1]
    else:
        new_key = _in(f"  {tr('uje_field_name')}: ")
        if new_key == EXIT or not new_key: return
    if new_key in cfg:
        print(f"[!] {tr('uje_exists')}: {new_key}"); _in("\n" + tr("q_back") + ": ", allow_exit=False); return
    print(f"\n  {tr('uje_type_q')}")
    t = _in_choice(f"  {tr('uje_type')} [1]: ", ["1","2","3","4"]) or "1"
    if t == EXIT: return
    if t == "1":
        v = _in(f"  {tr('uje_val')}: ")
        if v == EXIT: return
        cfg[new_key] = v
    elif t == "2":
        cfg[new_key] = []
        while True:
            v = input(f"  {tr('uje_elem')}: ").strip()
            if v.lower() in ("q","quit","exit") or not v: break
            cfg[new_key].append(v)
    elif t == "3":
        cfg[new_key] = {}
        while True:
            k = input(f"  {tr('uje_key')}: ").strip()
            if k.lower() in ("q","quit","exit") or not k: break
            val = _in(f"  {tr('uje_val')}: ")
            if val == EXIT: break
            cfg[new_key][k] = val
    elif t == "4":
        v = _in_choice(f"  true/false: ", ["true","false"])
        if v == EXIT: return
        cfg[new_key] = v
    print(f"[+] {tr('uje_added')}: {new_key}")
    _in("\n" + tr("q_back") + ": ", allow_exit=False)

def uje_editor(cfg, path):
    while True:
        clr(); hdr(tr("uje_editor_hdr"))
        print(f"  {tr('uje_file')}: {path.name}")
        ln()
        keys = uje_ordered_keys(cfg)
        for i, k in enumerate(keys, 1):
            v = cfg[k]
            if isinstance(v, list): disp = f"[{len(v)}]"
            elif isinstance(v, dict): disp = f"{{...}} ({len(v)})"
            else:
                disp = str(v)
                if len(disp) > 45: disp = disp[:42] + "..."
            print(f"  {i:3}. {k:24} = {disp}")
        ln()
        print("  " + tr("uje_a")); print("  " + tr("uje_s")); print("  " + tr("uje_b"))
        print("  " + tr("uje_v")); print("  " + tr("uje_o")); print("  " + tr("uje_q"))
        ch = _in(f"  {tr('choice')}: ")
        if ch == EXIT: return cfg
        if ch == 'a': uje_add_field(cfg); continue
        if ch == 's':
            if uje_save(path, cfg): print(f"[+] {tr('uje_saved')}: {path}"); _in("\n" + tr("q_back") + ": ", allow_exit=False)
            continue
        if ch == 'b':
            ts = time.strftime("%Y%m%d_%H%M%S")
            bp = BACKUP_DIR / f"{path.stem}_{ts}.json"
            if uje_save(bp, cfg): print(f"[+] {tr('uje_backup')}: {bp}")
            _in("\n" + tr("q_back") + ": ", allow_exit=False); continue
        if ch == 'v':
            clr(); print(json.dumps(cfg, ensure_ascii=False, indent=2))
            _in("\n" + tr("q_back") + ": ", allow_exit=False); continue
        if ch == 'o':
            nm = _in(f"  {tr('uje_file')}: ")
            if nm == EXIT or not nm: continue
            if not nm.endswith('.json'): nm += '.json'
            op = OUTPUT_DIR / nm
            if uje_save(op, cfg): print(f"[+] {tr('uje_exp')}: {op}")
            _in("\n" + tr("q_back") + ": ", allow_exit=False); continue
        if ch == 'q': return cfg
        try: idx = int(ch)
        except Exception: continue
        if 1 <= idx <= len(keys):
            key = keys[idx-1]; val = cfg.get(key)
            if isinstance(val, list): uje_edit_list(cfg, key)
            elif isinstance(val, dict): uje_edit_dict(cfg, key)
            else:
                uje_edit_string(cfg, key)
                _in("\n" + tr("q_back") + ": ", allow_exit=False)

def uje_menu():
    hdr(tr("uje_hdr"))
    print("  " + tr("uje_1")); print("  " + tr("uje_2")); print("  " + tr("uje_3")); print("  " + tr("uje_4"))
    print("  " + tr("q_back"))
    ch = _in_choice(f"{tr('choice')}: ", ["1","2","3","4"])
    if ch == EXIT: return
    if ch == "4":
        name = _in(f"  {tr('jname_noext')}: ")
        if name == EXIT or not name: return
        if not name.endswith('.json'): name += '.json'
        path = OUTPUT_DIR / name
        template = {"Name": name.replace('.json','')}
        if uje_save(path, template):
            print(f"[+] {tr('uje_saved')}: {path}")
            uje_editor(template, path)
        return
    path = None
    if ch == "1":
        files = sorted([p for p in INPUT_DIR.glob("*.json") if p.is_file()])
        if not files:
            print(f"[!] {tr('uje_file_in')}"); _in("\n" + tr("q_back") + ": ", allow_exit=False); return
        for i, f in enumerate(files, 1): print(f"  {i}. {f.name} ({fmt_size(f.stat().st_size)})")
        idx = _in_int(f"{tr('file_n')}: ", mn=1, mx=len(files))
        if idx == EXIT or idx is None: return
        path = files[idx-1]
    elif ch == "2":
        files = sorted([p for p in OUTPUT_DIR.glob("*.json") if p.is_file()])
        if not files:
            print(f"[!] {tr('uje_file_out')}"); _in("\n" + tr("q_back") + ": ", allow_exit=False); return
        for i, f in enumerate(files, 1): print(f"  {i}. {f.name} ({fmt_size(f.stat().st_size)})")
        idx = _in_int(f"{tr('file_n')}: ", mn=1, mx=len(files))
        if idx == EXIT or idx is None: return
        path = files[idx-1]
    elif ch == "3":
        p = _in(f"{tr('path_q')}: ")
        if p == EXIT or not p: return
        path = Path(p)
    if path:
        cfg = uje_load(path)
        if cfg is None:
            _in("\n" + tr("q_back") + ": ", allow_exit=False); return
        if not isinstance(cfg, dict):
            print(f"[!] {tr('uje_root_not_obj')}"); _in("\n" + tr("q_back") + ": ", allow_exit=False); return
        uje_editor(cfg, path)

def json_menu(servers, cfg):
    while True:
        clr(); hdr(tr("json_menu_hdr"))
        ln()
        print("  " + tr("json_m1")); print("  " + tr("json_m2"))
        print("  " + tr("json_m3")); print("  " + tr("q_back"))
        ch = _in_choice(f"{tr('choice')}: ", ["1","2","3"])
        if ch == EXIT: return cfg
        if ch == "1": cfg = config_menu(servers, cfg)
        elif ch == "2": uje_menu()
        elif ch == "3":
            if CFG_FILE.exists():
                try:
                    with open(CFG_FILE, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    clr(); print(json.dumps(data, ensure_ascii=False, indent=2))
                    _in("\n" + tr("q_back") + ": ", allow_exit=False)
                except Exception as e:
                    print(f"[!] {e}"); _in("\n" + tr("q_back") + ": ", allow_exit=False)
            else:
                print(f"[!] {tr('no_files')}"); _in("\n" + tr("q_back") + ": ", allow_exit=False)
    return cfg

# ========================================
#  Блок: главное меню
# ========================================

def main():
    ensure_dirs()
    cfg = cfg_load(); cfg_save(cfg)
    clr(); hdr("SubManager")
    print(f"  Input:   {INPUT_DIR}")
    print(f"  Output:  {OUTPUT_DIR}")
    print(f"  Backups: {BACKUP_DIR}")
    print("=" * W)
    servers = autoload()
    if servers:
        print(f"[+] {tr('autoload')}: {len(servers)}")
        time.sleep(1)
    json_template = None
    while True:
        clr(); hdr(tr("gname_hdr"))
        print(f"  {tr('g_serv')}: {len(servers)}")
        if json_template: print(f"  {tr('g_json')}")
        ln()
        for k in ("g1","g2","g3","g4","g5","g6","g7","g8","g9","g10","g11","g12","g13","g14"):
            print("  " + tr(k))
        print("  " + tr("gq"))
        ch = _in_choice(f"{tr('choice')}: ", [str(i) for i in range(1, 15)])
        if ch == EXIT:
            if servers:
                a = _in(f"{tr('backup_before')} [n]: ", default="n")
                if a != EXIT and a.lower() == 'y': backup_servers(servers)
                autosave(servers)
                print(f"[+] {tr('autosave')}: {AUTOSAVE_FILE}")
            print("[+] " + tr("exit"))
            break
        if ch == "1":
            raw = load_source()
            if raw:
                ns, jd = parse_input(raw)
                if ns:
                    servers.extend(ns)
                    if jd: json_template = jd
                    print(f"[+] {tr('load_ok')}: {len(servers)}")
                else: print(f"[!] {tr('parse_data')}")
            _in("\n" + tr("q_back") + ": ", allow_exit=False)
        elif ch == "2":
            if not servers:
                print(f"[!] {tr('no_servers_list')}"); _in("\n" + tr("q_back") + ": ", allow_exit=False); continue
            servers = edit_servers(servers)
        elif ch == "3":
            clr(); hdr(tr("list_hdr"))
            show_servers_list(servers, show_params=True)
            print(f"\n  {tr('total')}: {len(servers)}")
            _in("\n" + tr("q_back") + ": ", allow_exit=False)
        elif ch == "4": stats(servers)
        elif ch == "5": cfg = json_menu(servers, cfg)
        elif ch == "6":
            if not servers:
                print(f"[!] {tr('no_servers')}"); _in("\n" + tr("q_back") + ": ", allow_exit=False); continue
            nm, rem = ask_json_name_and_remarks(cfg)
            if nm is None:
                _in("\n" + tr("q_back") + ": ", allow_exit=False); continue
            save_json(gen_config(servers, cfg), cfg, nm, rem)
            _in("\n" + tr("q_back") + ": ", allow_exit=False)
        elif ch == "7": cfg = routing_menu(cfg)
        elif ch == "8":
            if not servers:
                print(f"[!] {tr('no_servers')}"); _in("\n" + tr("q_back") + ": ", allow_exit=False); continue
            export_menu(servers, cfg)
        elif ch == "9":
            if not servers:
                print(f"[!] {tr('no_servers')}"); _in("\n" + tr("q_back") + ": ", allow_exit=False); continue
            save_base64(servers); _in("\n" + tr("q_back") + ": ", allow_exit=False)
        elif ch == "10":
            if not servers:
                print(f"[!] {tr('no_servers')}"); _in("\n" + tr("q_back") + ": ", allow_exit=False); continue
            save_yaml_clash(servers); _in("\n" + tr("q_back") + ": ", allow_exit=False)
        elif ch == "11":
            if not servers:
                print(f"[!] {tr('no_servers')}"); _in("\n" + tr("q_back") + ": ", allow_exit=False); continue
            backup_servers(servers); _in("\n" + tr("q_back") + ": ", allow_exit=False)
        elif ch == "12": normalize_existing_config_menu()
        elif ch == "13": normalize_existing_servers_menu()
        elif ch == "14":
            if AUTOSAVE_FILE.exists():
                a = _in(f"{tr('del_auto')} [n]: ", default="n")
                if a and a.lower() == 'y':
                    AUTOSAVE_FILE.unlink(); print(f"[+] {tr('uje_deleted')}")
            else: print(f"[!] {tr('cur_auto')}")
            _in("\n" + tr("q_back") + ": ", allow_exit=False)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n[+] " + tr("exit"))
        sys.exit(0)
SUBMGR_END
fi

# ========================================
#  Скрипт 5/5: RegexBuilder.py
# ========================================
if [ "$REGEN_PY" = "1" ] || [ ! -s "$BASE/RegexBuilder.py" ]; then
cat << 'REGEX_END' > "$BASE/RegexBuilder.py"
# ========================================
#  RegexBuilder: конструктор регулярных выражений
# ========================================

import os
import sys
import re
import time
import json
from pathlib import Path
from datetime import datetime

os.umask(0o077)

# --- Загрузка языка ---
LANG = os.environ.get("LANG_SEL", "").strip()
if not LANG:
    try:
        with open(os.path.expanduser("~/.sr_toolkit_lang")) as _f:
            LANG = _f.read().strip()
    except Exception:
        LANG = "ru"
if LANG not in ("ru", "en"):
    LANG = "ru"

# --- Словарь переводов ---
_T = {
"ru": {
"exit": "Выход.",
"menu_hdr": "REGEXBUILDER: ГЛАВНОЕ МЕНЮ",
"m1": "1 - Создать regex (мастер)",
"m2": "2 - Объяснить regex",
"m3": "3 - Протестировать regex",
"m4": "4 - Быстрые шаблоны",
"m5": "5 - Расширенный конструктор",
"m6": "6 - История",
"m_q": "q - Выход",
"choice": "Ваш выбор",
"bad": "Неверный выбор",
"press": "Нажмите Enter для продолжения",
"step1_hdr": "ШАГ 1: Что ДОЛЖНО совпадать?",
"step1_hint": "Введите примеры по одному. Пустая строка — конец ввода.",
"example_n": "Пример",
"added_n": "Добавлено. Всего",
"need_one": "Нужен хотя бы 1 пример.",
"step2_hdr": "ШАГ 2: Что НЕ ДОЛЖНО совпадать?",
"step2_hint": "Введите примеры по одному. Пустая строка — конец ввода.",
"step3_hdr": "ШАГ 3: Где искать?",
"step3_1": "1 - Везде по тексту",
"step3_2": "2 - Только целое слово",
"step3_3": "3 - Только начало строки",
"step3_4": "4 - Только конец строки",
"step3_5": "5 - Только вся строка целиком",
"step4_hdr": "ШАГ 4: Флаги",
"step4_case": "Учитывать регистр?",
"step4_multiline": "Многострочный режим?",
"step4_dotall": "Точка захватывает перевод строки?",
"step5_hdr": "ШАГ 5: Группа захвата",
"step5_q": "Добавить группу захвата? (y/n)",
"step5_name": "Имя группы (латиница)",
"step6_hdr": "ШАГ 6: Фильтры",
"step6_q": "Добавить фильтры включения/исключения? (y/n)",
"step6_include": "ВКЛЮЧИТЬ если содержит",
"step6_exclude": "ИСКЛЮЧИТЬ если содержит",
"step6_kw": "Ключевое слово",
"building": "Сборка...",
"result_hdr": "РЕЗУЛЬТАТ",
"regex_lbl": "Регулярное выражение",
"flags_lbl": "Флаги",
"testing": "Проверка на примерах",
"match_ok": "СОВПАДАЕТ",
"match_no": "НЕ СОВПАДАЕТ",
"all_ok": "Все примеры проверены.",
"some_fail": "Некоторые примеры не прошли.",
"save_q": "Сохранить? (y/n)",
"save_name": "Имя файла (без расширения)",
"save_ok": "Сохранено",
"explain_hdr": "ОБЪЯСНЕНИЕ REGEX",
"explain_q": "Введите регулярное выражение",
"empty": "Пустое выражение.",
"err_lbl": "Ошибка",
"test_hdr": "ТЕСТИРОВАНИЕ",
"test_hint": "Введите текст. Пустая строка — конец.",
"matches": "Найдено совпадений",
"groups_lbl": "Группы",
"preset_hdr": "БЫСТРЫЕ ШАБЛОНЫ",
"preset_1": "1 - Email",
"preset_2": "2 - URL",
"preset_3": "3 - IPv4",
"preset_4": "4 - Дата YYYY-MM-DD",
"preset_5": "5 - Время HH:MM:SS",
"preset_6": "6 - Телефон +7...",
"preset_7": "7 - HEX-цвет #RRGGBB",
"preset_8": "8 - UUID",
"preset_9": "9 - MAC-адрес",
"preset_back": "b - Назад",
"preset_applied": "Шаблон применён",
"adv_hdr": "РАСШИРЕННЫЙ КОНСТРУКТОР",
"adv_1": "1 - Добавить ПОЗИТИВНЫЙ LOOKAHEAD  (?=...)",
"adv_2": "2 - Добавить НЕГАТИВНЫЙ LOOKAHEAD  (?!...)",
"adv_3": "3 - Добавить ПОЗИТИВНЫЙ LOOKBEHIND (?<=...)",
"adv_4": "4 - Добавить НЕГАТИВНЫЙ LOOKBEHIND (?<!...)",
"adv_5": "5 - Добавить УСЛОВНЫЙ БЛОК  (?(N)yes|no)",
"adv_6": "6 - Добавить BACKREFERENCE \\1 \\2",
"adv_7": "7 - Добавить АТОМАРНУЮ ГРУППУ (?>...)",
"adv_8": "8 - Добавить ИМЕНОВАННУЮ ГРУППУ (?P<name>...)",
"adv_9": "9 - Показать текущий шаблон",
"adv_10": "10 - Протестировать и сохранить",
"adv_11": "11 - Очистить",
"adv_q": "q - Выход",
"adv_current": "Текущий шаблон",
"adv_insert": "Куда вставить?",
"adv_pos_1": "1 - В начало",
"adv_pos_2": "2 - В конец",
"adv_pos_3": "3 - Заменить всё",
"adv_inner": "Содержимое",
"adv_group_n": "Номер группы (1-9)",
"adv_group_name": "Имя группы (латиница)",
"adv_added": "Добавлено",
"adv_empty": "Пустой шаблон.",
"adv_cleared": "Очищено.",
"hist_hdr": "ИСТОРИЯ",
"hist_empty": "История пуста.",
"back": "b - Назад",
"q_back": "q - Назад",
"path_q": "Путь к файлу",
"file_n": "Номер файла"
},
"en": {
"exit": "Exit.",
"menu_hdr": "REGEXBUILDER: MAIN MENU",
"m1": "1 - Build a regex (wizard)",
"m2": "2 - Explain regex",
"m3": "3 - Test a regex",
"m4": "4 - Quick templates",
"m5": "5 - Advanced builder",
"m6": "6 - History",
"m_q": "q - Quit",
"choice": "Your choice",
"bad": "Invalid choice",
"press": "Press Enter to continue",
"step1_hdr": "STEP 1: What SHOULD match?",
"step1_hint": "Enter examples one per line. Empty line — end.",
"example_n": "Example",
"added_n": "Added. Total",
"need_one": "At least 1 example needed.",
"step2_hdr": "STEP 2: What should NOT match?",
"step2_hint": "Enter examples one per line. Empty line — end.",
"step3_hdr": "STEP 3: Where to search?",
"step3_1": "1 - Anywhere in text",
"step3_2": "2 - Whole word only",
"step3_3": "3 - Start of line",
"step3_4": "4 - End of line",
"step3_5": "5 - Whole line only",
"step4_hdr": "STEP 4: Flags",
"step4_case": "Case sensitive?",
"step4_multiline": "Multiline mode?",
"step4_dotall": "Dot matches newlines?",
"step5_hdr": "STEP 5: Capture group",
"step5_q": "Add capture group? (y/n)",
"step5_name": "Group name (latin)",
"step6_hdr": "STEP 6: Filters",
"step6_q": "Add include/exclude filters? (y/n)",
"step6_include": "INCLUDE if contains",
"step6_exclude": "EXCLUDE if contains",
"step6_kw": "Keyword",
"building": "Building...",
"result_hdr": "RESULT",
"regex_lbl": "Regular expression",
"flags_lbl": "Flags",
"testing": "Testing examples",
"match_ok": "MATCH",
"match_no": "NO MATCH",
"all_ok": "All examples passed.",
"some_fail": "Some examples failed.",
"save_q": "Save? (y/n)",
"save_name": "File name (without extension)",
"save_ok": "Saved",
"explain_hdr": "REGEX EXPLANATION",
"explain_q": "Enter regular expression",
"empty": "Empty expression.",
"err_lbl": "Error",
"test_hdr": "TESTING",
"test_hint": "Enter text. Empty line — end.",
"matches": "Matches found",
"groups_lbl": "Groups",
"preset_hdr": "QUICK TEMPLATES",
"preset_1": "1 - Email",
"preset_2": "2 - URL",
"preset_3": "3 - IPv4",
"preset_4": "4 - Date YYYY-MM-DD",
"preset_5": "5 - Time HH:MM:SS",
"preset_6": "6 - Phone +7...",
"preset_7": "7 - HEX color #RRGGBB",
"preset_8": "8 - UUID",
"preset_9": "9 - MAC address",
"preset_back": "b - Back",
"preset_applied": "Template applied",
"adv_hdr": "ADVANCED BUILDER",
"adv_1": "1 - Add POSITIVE LOOKAHEAD  (?=...)",
"adv_2": "2 - Add NEGATIVE LOOKAHEAD  (?!...)",
"adv_3": "3 - Add POSITIVE LOOKBEHIND (?<=...)",
"adv_4": "4 - Add NEGATIVE LOOKBEHIND (?<!...)",
"adv_5": "5 - Add CONDITIONAL BLOCK  (?(N)yes|no)",
"adv_6": "6 - Add BACKREFERENCE \\1 \\2",
"adv_7": "7 - Add ATOMIC GROUP (?>...)",
"adv_8": "8 - Add NAMED GROUP (?P<name>...)",
"adv_9": "9 - Show current pattern",
"adv_10": "10 - Test and save",
"adv_11": "11 - Clear",
"adv_q": "q - Exit",
"adv_current": "Current pattern",
"adv_insert": "Where to insert?",
"adv_pos_1": "1 - At start",
"adv_pos_2": "2 - At end",
"adv_pos_3": "3 - Replace all",
"adv_inner": "Content",
"adv_group_n": "Group number (1-9)",
"adv_group_name": "Group name (latin)",
"adv_added": "Added",
"adv_empty": "Empty pattern.",
"adv_cleared": "Cleared.",
"hist_hdr": "HISTORY",
"hist_empty": "History is empty.",
"back": "b - Back",
"q_back": "q - Back",
"path_q": "Path to file",
"file_n": "File number"
}}

def tr(k):
    return _T.get(LANG, _T["ru"]).get(k, _T["ru"].get(k, k))

# --- Очистка ввода от ANSI-последовательностей и управляющих символов ---
def _clean(s):
    if s is None:
        return ""
    s = re.sub(r'\x1b\[[0-9;?]*[A-Za-z]', '', s)
    s = ''.join(ch for ch in s if ch == '\t' or ord(ch) >= 32)
    return s

# --- Безопасный ввод. Возвращает None если пользователь ввёл q ---
def _input(prompt="", allow_empty=False):
    try:
        v = input(prompt)
    except (EOFError, KeyboardInterrupt):
        print()
        return None
    v = _clean(v)
    stripped = v.strip()
    if stripped.lower() in ("q", "quit", "exit"):
        return None
    if not allow_empty and not stripped:
        return ""
    return v

# --- Утилиты UI ---
def clr():
    os.system('clear')

def hdr(t):
    print("=" * 40)
    print(f" {t}")
    print("=" * 40)

def ln():
    print("-" * 40)

# --- Пути ---
ROOT = Path.home()
BASE = ROOT / "Shadowrocket" / "RegexBuilder"
OUTPUT_DIR = BASE / "Output"
BACKUP_DIR = BASE / "Backups"
HISTORY_FILE = BASE / "history.json"

def ensure_dirs():
    for d in [BASE, OUTPUT_DIR, BACKUP_DIR]:
        if not d.exists():
            d.mkdir(parents=True, exist_ok=True)

# ========================================
#  Блок: классификация строк и генерация pattern
# ========================================

def classify(s):
    if re.fullmatch(r'\d{1,3}(\.\d{1,3}){3}', s): return 'ipv4'
    if re.fullmatch(r'[\w.+-]+@[\w-]+\.[\w.]+', s): return 'email'
    if re.fullmatch(r'https?://\S+', s): return 'url'
    if re.fullmatch(r'\d{4}-\d{2}-\d{2}', s): return 'date'
    if re.fullmatch(r'\d{2}:\d{2}:\d{2}', s): return 'time'
    if re.fullmatch(r'#[0-9a-fA-F]{6}', s): return 'hexcolor'
    if re.fullmatch(r'[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}', s): return 'uuid'
    if re.fullmatch(r'\+?\d[\d\s\-()]{6,}', s): return 'phone'
    if re.fullmatch(r'([0-9A-Fa-f]{2}[:-]){5}[0-9A-Fa-f]{2}', s): return 'mac'
    if re.fullmatch(r'\d+', s): return 'number'
    if re.fullmatch(r'[a-zA-Z]+', s): return 'word'
    if re.fullmatch(r'[a-zA-Z][a-zA-Z0-9_]*', s): return 'identifier'
    return 'literal'

def build_pattern_from_examples(examples):
    if not examples:
        return None
    tokens = []
    for ex in examples:
        t = classify(ex)
        if t == 'ipv4': tokens.append(r'\d{1,3}(?:\.\d{1,3}){3}')
        elif t == 'email': tokens.append(r'[\w.+-]+@[\w-]+\.[\w.]+')
        elif t == 'url': tokens.append(r'https?://[^\s]+')
        elif t == 'date': tokens.append(r'\d{4}-\d{2}-\d{2}')
        elif t == 'time': tokens.append(r'\d{2}:\d{2}:\d{2}')
        elif t == 'hexcolor': tokens.append(r'#[0-9a-fA-F]{6}')
        elif t == 'uuid': tokens.append(r'[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}')
        elif t == 'phone': tokens.append(r'\+?\d[\d\s\-()]{6,}')
        elif t == 'mac': tokens.append(r'(?:[0-9A-Fa-f]{2}[:-]){5}[0-9A-Fa-f]{2}')
        elif t == 'number': tokens.append(r'\d+')
        elif t == 'word': tokens.append(r'[a-zA-Z]+')
        elif t == 'identifier': tokens.append(r'[a-zA-Z][a-zA-Z0-9_]*')
        else: tokens.append(re.escape(ex))
    unique = []
    for t in tokens:
        if t not in unique:
            unique.append(t)
    if len(unique) == 1:
        return unique[0]
    return '(?:' + '|'.join(unique) + ')'

# ========================================
#  Блок: объяснение regex по токенам
# ========================================

def explain_regex(pattern):
    out = []
    i = 0
    n = len(pattern)
    while i < n:
        c = pattern[i]
        if c == '^':
            out.append(("^", "Начало строки" if LANG == "ru" else "Start of line"))
        elif c == '$':
            out.append(("$", "Конец строки" if LANG == "ru" else "End of line"))
        elif c == '.':
            out.append((".", "Любой символ" if LANG == "ru" else "Any character"))
        elif c == '*':
            out.append(("*", "0 или более раз" if LANG == "ru" else "0 or more"))
        elif c == '+':
            out.append(("+", "1 или более раз" if LANG == "ru" else "1 or more"))
        elif c == '?':
            out.append(("?", "0 или 1 раз" if LANG == "ru" else "0 or 1"))
        elif c == '\\' and i + 1 < n:
            nxt = pattern[i + 1]
            d = {'d': 'Цифра', 'D': 'Не цифра', 'w': 'Слово', 'W': 'Не слово',
                 's': 'Пробел', 'S': 'Не пробел', 'b': 'Граница слова', 'B': 'Не граница слова'}
            if nxt.isdigit():
                out.append((f"\\{nxt}", f"Backreference на группу {nxt}"))
            else:
                out.append((f"\\{nxt}", d.get(nxt, f"Спецсимвол \\{nxt}")))
            i += 1
        elif c == '(':
            if i + 2 < n and pattern[i + 1] == '?':
                if pattern[i + 2] == ':':
                    out.append(("(?:", "Незахватывающая группа"))
                elif pattern[i + 2] == '=':
                    out.append(("(?=", "Позитивный lookahead"))
                elif pattern[i + 2] == '!':
                    out.append(("(?!", "Негативный lookahead"))
                elif pattern[i + 2] == '<':
                    if i + 3 < n and pattern[i + 3] in ('=', '!'):
                        sign = pattern[i + 3]
                        out.append((f"(?<{sign}", "Позитивный lookbehind" if sign == '=' else "Негативный lookbehind"))
                    else:
                        out.append(("(?<", "Именованная группа (old-style)"))
                elif pattern[i + 2] == 'P':
                    out.append(("(?P", "Именованная группа / backreference"))
                elif pattern[i + 2] == '>':
                    out.append(("(?>", "Атомарная группа"))
                elif pattern[i + 2] == '(':
                    out.append(("(?(", "Условный блок"))
                else:
                    out.append(("(?", "Inline-модификатор"))
            else:
                out.append(("(", "Начало группы"))
        elif c == ')':
            out.append((")", "Конец группы"))
        elif c == '|':
            out.append(("|", "ИЛИ" if LANG == "ru" else "OR"))
        elif c == '[':
            j = pattern.find(']', i)
            if j > i:
                content = pattern[i:j + 1]
                out.append((content, f"Набор символов: {content[1:-1]}"))
                i = j
            else:
                out.append(("[", "Набор символов"))
        elif c == '{':
            j = pattern.find('}', i)
            if j > i:
                content = pattern[i:j + 1]
                out.append((content, f"Количество: {content[1:-1]}"))
                i = j
            else:
                out.append(("{", "Квантор"))
        else:
            out.append((c, f"Литерал '{c}'"))
        i += 1
    return out

# ========================================
#  Блок: пресеты
# ========================================

PRESETS = {
    "1": ("Email", r'[\w.+-]+@[\w-]+\.[\w.]+', "test@example.com"),
    "2": ("URL", r'https?://[^\s]+', "https://example.com/path?x=1"),
    "3": ("IPv4", r'\d{1,3}(?:\.\d{1,3}){3}', "192.168.1.1"),
    "4": ("Date", r'\d{4}-\d{2}-\d{2}', "2025-01-15"),
    "5": ("Time", r'\d{2}:\d{2}:\d{2}', "14:30:00"),
    "6": ("Phone", r'\+?\d[\d\s\-()]{6,}', "+7 999 123-45-67"),
    "7": ("HEX", r'#[0-9a-fA-F]{6}', "#FF5733"),
    "8": ("UUID", r'[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}', "550e8400-e29b-41d4-a716-446655440000"),
    "9": ("MAC", r'(?:[0-9A-Fa-f]{2}[:-]){5}[0-9A-Fa-f]{2}', "AA:BB:CC:DD:EE:FF"),
}

# ========================================
#  Блок: история
# ========================================

def load_history():
    if not HISTORY_FILE.exists():
        return []
    try:
        data = json.loads(HISTORY_FILE.read_text(encoding='utf-8'))
        return data if isinstance(data, list) else []
    except Exception:
        return []

def save_history(pattern, flags_desc, examples):
    try:
        hist = load_history()
        hist.append({
            "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "pattern": pattern,
            "flags": flags_desc,
            "examples": examples[:5],
        })
        hist = hist[-50:]
        HISTORY_FILE.write_text(json.dumps(hist, ensure_ascii=False, indent=2), encoding='utf-8')
    except Exception:
        pass

# ========================================
#  Блок: тестирование
# ========================================

def test_pattern(pattern, flags, match_examples, no_match_examples):
    try:
        compiled = re.compile(pattern, flags)
    except re.error as e:
        print(f"[!] {tr('err_lbl')}: {e}")
        return None, None
    results = {"ok": True, "missed": [], "unexpected": []}
    print(f"\n  {tr('testing')}:")
    ln()
    for ex in match_examples:
        m = compiled.search(ex)
        if m:
            print(f"    [+] {tr('match_ok')}:  {ex}")
            print(f"        -> '{m.group()}' @ {m.start()}-{m.end()}")
        else:
            print(f"    [-] {tr('match_no')}: {ex}")
            results["missed"].append(ex)
            results["ok"] = False
    for ex in no_match_examples:
        m = compiled.search(ex)
        if not m:
            print(f"    [+] {tr('match_no')}: {ex}")
        else:
            print(f"    [!] {tr('match_ok')}:  {ex}")
            results["unexpected"].append(ex)
            results["ok"] = False
    return compiled, results

# ========================================
#  Блок: сохранение результата
# ========================================

def save_result(pattern, flags, flag_names, match_examples, no_match_examples):
    if _input(f"\n  {tr('save_q')} [y]: ", allow_empty=True) is None:
        return
    v = input(f"  {tr('save_name')} [regex_output]: ").strip()
    v = _clean(v)
    if not v:
        v = "regex_output"
    out = OUTPUT_DIR / f"{v}.py"
    with open(out, 'w', encoding='utf-8') as f:
        f.write("# Auto-generated by RegexBuilder\n")
        f.write(f"# Generated: {datetime.now().isoformat()}\n")
        f.write(f"# Flags: {', '.join(flag_names) if flag_names else 'none'}\n\n")
        f.write("import re\n\n")
        f.write(f"pattern = r'''{pattern}'''\n")
        if flag_names:
            f.write("flags = " + " | ".join(f"re.{fn}" for fn in flag_names) + "\n")
        else:
            f.write("flags = 0\n")
        f.write("\nregex = re.compile(pattern, flags)\n\n")
        if match_examples:
            f.write("# Test examples (SHOULD match):\n")
            for ex in match_examples:
                f.write(f"#   {ex}\n")
        if no_match_examples:
            f.write("\n# Test examples (SHOULD NOT match):\n")
            for ex in no_match_examples:
                f.write(f"#   {ex}\n")
    print(f"  [+] {tr('save_ok')}: {out}")

# ========================================
#  Блок: режим "Мастер"
# ========================================

def mode_wizard():
    clr()
    hdr(tr("step1_hdr"))
    print(tr("step1_hint"))

    match_examples = []
    idx = 1
    while True:
        s = _input(f"  {tr('example_n')} #{idx}: ", allow_empty=True)
        if s is None:
            return
        if not s:
            break
        match_examples.append(s)
        idx += 1
        print(f"  [+] {tr('added_n')}: {len(match_examples)}")

    if not match_examples:
        print(f"[!] {tr('need_one')}")
        input(f"\n{tr('press')}: ")
        return

    print("\n" + "=" * 40)
    print(f"  {tr('step2_hdr')}")
    print("=" * 40)
    print(tr("step2_hint"))
    no_match_examples = []
    idx = 1
    while True:
        s = _input(f"  {tr('example_n')} #{idx}: ", allow_empty=True)
        if s is None:
            return
        if not s:
            break
        no_match_examples.append(s)
        idx += 1

    print("\n" + "=" * 40)
    print(f"  {tr('step3_hdr')}")
    print("=" * 40)
    print("  " + tr("step3_1"))
    print("  " + tr("step3_2"))
    print("  " + tr("step3_3"))
    print("  " + tr("step3_4"))
    print("  " + tr("step3_5"))
    sc = _input(f"{tr('choice')} [1]: ", allow_empty=True)
    if sc is None: return
    sc = sc.strip() or "1"
    if sc not in ("1", "2", "3", "4", "5"):
        sc = "1"

    print("\n" + "=" * 40)
    print(f"  {tr('step4_hdr')}")
    print("=" * 40)
    v = _input(f"  {tr('step4_case')} (y/n) [n]: ", allow_empty=True)
    if v is None: return
    case_sensitive = v.strip().lower() == "y"
    v = _input(f"  {tr('step4_multiline')} (y/n) [n]: ", allow_empty=True)
    if v is None: return
    multiline = v.strip().lower() == "y"
    v = _input(f"  {tr('step4_dotall')} (y/n) [n]: ", allow_empty=True)
    if v is None: return
    dotall = v.strip().lower() == "y"

    print("\n" + "=" * 40)
    print(f"  {tr('step5_hdr')}")
    print("=" * 40)
    v = _input(f"  {tr('step5_q')} [n]: ", allow_empty=True)
    if v is None: return
    use_group = v.strip().lower() == "y"
    group_name = ""
    if use_group:
        v = _input(f"  {tr('step5_name')} (Enter — без имени): ", allow_empty=True)
        if v is None: return
        group_name = v.strip()

    print("\n" + "=" * 40)
    print(f"  {tr('step6_hdr')}")
    print("=" * 40)
    v = _input(f"  {tr('step6_q')} [n]: ", allow_empty=True)
    if v is None: return
    use_filters = v.strip().lower() == "y"
    include_kw = []
    exclude_kw = []
    if use_filters:
        print(f"\n  {tr('step6_include')}:")
        while True:
            kw = _input(f"    {tr('step6_kw')} (Enter — конец): ", allow_empty=True)
            if kw is None: return
            if not kw.strip(): break
            include_kw.append(kw.strip())
        print(f"\n  {tr('step6_exclude')}:")
        while True:
            kw = _input(f"    {tr('step6_kw')} (Enter — конец): ", allow_empty=True)
            if kw is None: return
            if not kw.strip(): break
            exclude_kw.append(kw.strip())

    print("\n" + tr("building"))
    time.sleep(0.2)

    pattern = build_pattern_from_examples(match_examples) or re.escape(match_examples[0])

    if use_group:
        if group_name and re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]*', group_name):
            pattern = f"(?P<{group_name}>{pattern})"
        else:
            pattern = f"({pattern})"

    if sc == "2":
        pattern = r'\b' + pattern + r'\b'
    elif sc == "3":
        pattern = '^' + pattern
    elif sc == "4":
        pattern = pattern + '$'
    elif sc == "5":
        pattern = '^' + pattern + '$'

    for kw in exclude_kw:
        pattern = f"(?!.*{re.escape(kw)})" + pattern
    for kw in include_kw:
        pattern = f"(?=.*{re.escape(kw)})" + pattern

    flags = 0
    flag_names = []
    if not case_sensitive:
        flags |= re.IGNORECASE
        flag_names.append("IGNORECASE")
    if multiline:
        flags |= re.MULTILINE
        flag_names.append("MULTILINE")
    if dotall:
        flags |= re.DOTALL
        flag_names.append("DOTALL")

    clr()
    hdr(tr("result_hdr"))
    print(f"  {tr('regex_lbl')}:")
    print(f"    {pattern}")
    if flag_names:
        print(f"  {tr('flags_lbl')}: {', '.join(flag_names)}")

    compiled, results = test_pattern(pattern, flags, match_examples, no_match_examples)
    if compiled is None:
        input(f"\n{tr('press')}: ")
        return

    ln()
    if results["ok"]:
        print(f"  [+] {tr('all_ok')}")
    else:
        print(f"  [!] {tr('some_fail')}")

    save_history(pattern, "|".join(flag_names), match_examples)
    save_result(pattern, flags, flag_names, match_examples, no_match_examples)
    input(f"\n{tr('press')}: ")

# ========================================
#  Блок: режим "Объяснить"
# ========================================

def mode_explain():
    clr()
    hdr(tr("explain_hdr"))
    pattern = _input(f"\n{tr('explain_q')}: ", allow_empty=True)
    if pattern is None: return
    pattern = pattern.strip()
    if not pattern:
        print(f"[!] {tr('empty')}")
        input(f"\n{tr('press')}: ")
        return
    try:
        re.compile(pattern)
    except re.error as e:
        print(f"[!] {tr('err_lbl')}: {e}")
        input(f"\n{tr('press')}: ")
        return
    print(f"\n  {tr('regex_lbl')}: {pattern}\n")
    ln()
    for tok, desc in explain_regex(pattern):
        print(f"    {tok:<22} {desc}")
    ln()
    input(f"\n{tr('press')}: ")

# ========================================
#  Блок: режим "Тест"
# ========================================

def mode_test():
    clr()
    hdr(tr("test_hdr"))
    pattern = _input(f"\n{tr('explain_q')}: ", allow_empty=True)
    if pattern is None: return
    pattern = pattern.strip()
    if not pattern:
        print(f"[!] {tr('empty')}")
        input(f"\n{tr('press')}: ")
        return
    try:
        compiled = re.compile(pattern)
    except re.error as e:
        print(f"[!] {tr('err_lbl')}: {e}")
        input(f"\n{tr('press')}: ")
        return
    print(f"\n{tr('test_hint')}")
    lines = []
    while True:
        s = input("  > ")
        s = _clean(s)
        if not s: break
        lines.append(s)
    if not lines:
        input(f"\n{tr('press')}: ")
        return
    text = "\n".join(lines)
    matches = list(compiled.finditer(text))
    print(f"\n  {tr('matches')}: {len(matches)}")
    ln()
    for i, m in enumerate(matches, 1):
        print(f"  [{i}] '{m.group()}' @ {m.start()}-{m.end()}")
        for gi, g in enumerate(m.groups(), 1):
            print(f"       {tr('groups_lbl')} #{gi}: {g!r}")
        for ng, val in (m.groupdict() or {}).items():
            print(f"       {tr('groups_lbl')} '{ng}': {val!r}")
    input(f"\n{tr('press')}: ")

# ========================================
#  Блок: режим "Пресеты"
# ========================================

def mode_presets():
    while True:
        clr()
        hdr(tr("preset_hdr"))
        for k, (name, pat, example) in PRESETS.items():
            print(f"  {k:>2}. {name:<16} {pat}")
        ln()
        print(f"  {tr('preset_back')}")
        ch = _input(f"{tr('choice')} [1]: ", allow_empty=True)
        if ch is None: return
        ch = ch.strip()
        if ch.lower() in ("b", "back"):
            return
        if ch not in PRESETS:
            continue
        name, pat, example = PRESETS[ch]
        print(f"\n  {name}: {pat}")
        print(f"  Пример: {example}")
        try:
            compiled = re.compile(pat)
        except re.error as e:
            print(f"[!] {tr('err_lbl')}: {e}")
            input(f"\n{tr('press')}: ")
            continue
        m = compiled.search(example)
        if m:
            print(f"  [+] {tr('match_ok')}: '{m.group()}'")
        else:
            print(f"  [!] {tr('match_no')}")
        if _input(f"\n  {tr('save_q')} [y]: ", allow_empty=True) is not None:
            fname = _input(f"  {tr('save_name')} [{name.lower().replace(' ', '_')}]: ", allow_empty=True)
            if fname is None:
                continue
            fname = fname.strip() or name.lower().replace(' ', '_')
            out = OUTPUT_DIR / f"{fname}.py"
            with open(out, 'w', encoding='utf-8') as f:
                f.write(f"# {name}\nimport re\n\npattern = r'''{pat}'''\nflags = 0\nregex = re.compile(pattern, flags)\n")
            print(f"  [+] {tr('save_ok')}: {out}")
        input(f"\n{tr('press')}: ")

# ========================================
#  Блок: режим "Расширенный"
# ========================================

def mode_advanced():
    pattern = ""

    def insert_component(comp):
        nonlocal pattern
        print(f"\n  {tr('adv_current')}: {pattern if pattern else '(пусто)'}")
        print(f"\n  {tr('adv_insert')}:")
        print("    " + tr("adv_pos_1"))
        print("    " + tr("adv_pos_2"))
        print("    " + tr("adv_pos_3"))
        pos = _input(f"  {tr('choice')} [1]: ", allow_empty=True)
        if pos is None: return
        pos = pos.strip() or "1"
        if pos == "1":
            pattern = comp + pattern
        elif pos == "2":
            pattern = pattern + comp
        elif pos == "3":
            pattern = comp
        print(f"  [+] {tr('adv_added')}: {comp}")

    while True:
        clr()
        hdr(tr("adv_hdr"))
        print("  " + tr("adv_1"))
        print("  " + tr("adv_2"))
        print("  " + tr("adv_3"))
        print("  " + tr("adv_4"))
        print("  " + tr("adv_5"))
        print("  " + tr("adv_6"))
        print("  " + tr("adv_7"))
        print("  " + tr("adv_8"))
        print("  " + tr("adv_9"))
        print("  " + tr("adv_10"))
        print("  " + tr("adv_11"))
        print("  " + tr("adv_q"))
        ln()
        print(f"  {tr('adv_current')}: {pattern if pattern else '(пусто)'}")
        ln()

        ch = _input(f"{tr('choice')}: ", allow_empty=True)
        if ch is None:
            return
        ch = ch.strip().lower()

        if ch == "1":
            inner = _input(f"  {tr('adv_inner')} (?= ... ): ", allow_empty=True)
            if inner is None: continue
            inner = inner.strip()
            if inner: insert_component(f"(?={inner})")

        elif ch == "2":
            inner = _input(f"  {tr('adv_inner')} (?! ... ): ", allow_empty=True)
            if inner is None: continue
            inner = inner.strip()
            if inner: insert_component(f"(?!{inner})")

        elif ch == "3":
            inner = _input(f"  {tr('adv_inner')} (?<= ... ): ", allow_empty=True)
            if inner is None: continue
            inner = inner.strip()
            if inner: insert_component(f"(?<={inner})")

        elif ch == "4":
            inner = _input(f"  {tr('adv_inner')} (?<! ... ): ", allow_empty=True)
            if inner is None: continue
            inner = inner.strip()
            if inner: insert_component(f"(?<!{inner})")

        elif ch == "5":
            v = _input(f"  {tr('adv_group_n')} [1]: ", allow_empty=True)
            if v is None: continue
            n = v.strip() or "1"
            if not n.isdigit(): n = "1"
            yes_pat = _input("  Паттерн если сработала (yes): ", allow_empty=True)
            if yes_pat is None: continue
            no_pat = _input("  Паттерн если НЕ сработала (no): ", allow_empty=True)
            if no_pat is None: continue
            insert_component(f"(?({n}){yes_pat.strip()}|{no_pat.strip()})")

        elif ch == "6":
            v = _input(f"  {tr('adv_group_n')} [1]: ", allow_empty=True)
            if v is None: continue
            n = v.strip() or "1"
            if not n.isdigit(): n = "1"
            insert_component(f"\\{n}")

        elif ch == "7":
            inner = _input(f"  {tr('adv_inner')} (?> ... ): ", allow_empty=True)
            if inner is None: continue
            inner = inner.strip()
            if inner: insert_component(f"(?>{inner})")

        elif ch == "8":
            name_g = _input(f"  {tr('adv_group_name')}: ", allow_empty=True)
            if name_g is None: continue
            name_g = name_g.strip()
            if not name_g or not re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]*', name_g):
                print("[!] Имя должно начинаться с буквы или подчёркивания")
                continue
            inner = _input(f"  {tr('adv_inner')}: ", allow_empty=True)
            if inner is None: continue
            inner = inner.strip() or ".*?"
            insert_component(f"(?P<{name_g}>{inner})")

        elif ch == "9":
            print(f"\n  {tr('adv_current')}: {pattern if pattern else '(пусто)'}")
            input(f"\n{tr('press')}: ")

        elif ch == "10":
            if not pattern:
                print(f"[!] {tr('adv_empty')}")
                input(f"\n{tr('press')}: ")
                continue
            try:
                compiled = re.compile(pattern)
            except re.error as e:
                print(f"[!] {tr('err_lbl')}: {e}")
                input(f"\n{tr('press')}: ")
                continue
            print(f"\n  {tr('regex_lbl')}: {pattern}")
            print(f"\n  {tr('test_hint')}")
            lines = []
            while True:
                s = input("  > ")
                s = _clean(s)
                if not s: break
                lines.append(s)
            text = "\n".join(lines)
            matches = list(compiled.finditer(text)) if text else []
            print(f"\n  {tr('matches')}: {len(matches)}")
            for i, m in enumerate(matches[:20], 1):
                print(f"  [{i}] '{m.group()}' @ {m.start()}-{m.end()}")
            if len(matches) > 20:
                print(f"  ... ещё {len(matches)-20}")
            if _input(f"\n  {tr('save_q')} [y]: ", allow_empty=True) is not None:
                fname = _input(f"  {tr('save_name')} [advanced]: ", allow_empty=True)
                if fname is None: continue
                fname = fname.strip() or "advanced"
                out = OUTPUT_DIR / f"{fname}.py"
                with open(out, 'w', encoding='utf-8') as f:
                    f.write(f"import re\n\npattern = r'''{pattern}'''\nflags = 0\nregex = re.compile(pattern, flags)\n")
                print(f"  [+] {tr('save_ok')}: {out}")
                save_history(pattern, "advanced", lines or [pattern])
            input(f"\n{tr('press')}: ")

        elif ch == "11":
            pattern = ""
            print(f"[+] {tr('adv_cleared')}")
            time.sleep(0.5)

# ========================================
#  Блок: режим "История"
# ========================================

def mode_history():
    clr()
    hdr(tr("hist_hdr"))
    hist = load_history()
    if not hist:
        print(f"  [!] {tr('hist_empty')}")
        input(f"\n{tr('press')}: ")
        return
    for i, item in enumerate(reversed(hist[-20:]), 1):
        print(f"  {i:3}. [{item.get('time','')}] {item.get('pattern','')}")
        if item.get('flags'):
            print(f"       flags: {item.get('flags')}")
    input(f"\n{tr('press')}: ")

# ========================================
#  Блок: главное меню
# ========================================

def main():
    ensure_dirs()
    while True:
        clr()
        hdr(tr("menu_hdr"))
        print("  " + tr("m1"))
        print("  " + tr("m2"))
        print("  " + tr("m3"))
        print("  " + tr("m4"))
        print("  " + tr("m5"))
        print("  " + tr("m6"))
        print("  " + tr("m_q"))
        ln()
        ch = _input(f"{tr('choice')} [1]: ", allow_empty=True)
        if ch is None:
            return
        ch = ch.strip() or "1"
        if ch == "1":
            mode_wizard()
        elif ch == "2":
            mode_explain()
        elif ch == "3":
            mode_test()
        elif ch == "4":
            mode_presets()
        elif ch == "5":
            mode_advanced()
        elif ch == "6":
            mode_history()
        else:
            print(f"[!] {tr('bad')}")
            time.sleep(1)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n[+] " + tr("exit"))
        sys.exit(0)
REGEX_END
fi

# --- Обновление маркера версии ---
echo "$TK_VERSION" > "$VERSION_FILE"

echo "[+] All scripts created."
sleep 1

# ========================================
#  Главное меню
# ========================================

while true; do
    clear
    echo "========================================"
    echo "        $(T m_title)"
    echo "========================================"
    echo "$(T m_ad)"
    echo "$(T m_sql)"
    echo "$(T m_spy)"
    echo "$(T m_sub)"
    echo "$(T m_rx)"
    echo "$(T m_def)"
    echo "$(T m_q)"
    echo "========================================"
    printf '%s: ' "$(T choice)"
    IFS= read -r CH
    case "$CH" in
        1) cd "$BASE/AdBlock"; python3 "$BASE/AdBlock.py"; cd "$HOME" ;;
        2) python3 "$BASE/SQLiteTXT.py" ;;
        3) python3 "$BASE/SpyLog.py" ;;
        4) python3 "$BASE/SubManager.py" ;;
        5) python3 "$BASE/RegexBuilder.py" ;;
        6)
            OUT="$BASE/Configurations/Default_configuration_by_Krest-Neva.module"
            if try_download "https://raw.githubusercontent.com/Krest-Neva/Shadowrocket/refs/heads/main/Configurations/Default_configuration_by_Krest-Neva.module" "$OUT"; then
                echo "[+] $OUT"
                echo "----"
                cat "$OUT"
                echo "----"
            else
                echo "$(T fail)"
            fi
            ;;
        q|Q) echo "$(T m_q)"; exit 0 ;;
        *) echo "$(T bad)"; sleep 1; continue ;;
    esac
    echo ""
    printf '%s' "$(T press)"
    IFS= read -r DUMMY
done
