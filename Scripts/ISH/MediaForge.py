#!/bin/sh
# ==========================================================================
#  MediaForge — универсальный загрузчик/медиа-инструмент (iSH/Alpine, Termux, Debian, macOS)
#  Запуск:  sh MediaForge.sh            (отладка: sh MediaForge.sh --debug  или  MF_DEBUG=1)
#  Оболочка: язык → проверка целостности → фиктивная геолокация (3 с) → репозитории Alpine 3.19
#  → Python 3.10+ → пакеты → pip-инструменты → запуск встроенного Python-ядра.
#  Ядро: загрузка видео/аудио/фото/истории/аватарки (yt-dlp, gallery-dl, API соцсетей, Telegram),
#  очередь, планировщик, конвертер, коллажи, метаданные, сеть (LAN-прокси, MITM, пинг), профили.
#  ВАЖНО: Alpine НЕ переключается без реальной необходимости (падение самого Python).
#  SIGSYS (код 159) — особенность iSH: просто перезапуск ядра, версия Alpine не меняется.
# ==========================================================================
MF_BUILD="202610260001"
MF_UPDATE_URL="https://raw.githubusercontent.com/Krest-Neva/Shadowrocket/refs/heads/main/Scripts/ISH/MediaForge.py"

HOME="${HOME:-/root}"; export HOME
BASE="$HOME/MediaForge"; CONF="$BASE/.config"; CORE="$BASE/.core"
# починка папок на уровне shell (если Python не стартует): файл вместо папки, права, битые JSON, ядро распакуется заново
repair_core() {
  for _d in "$BASE" "$CONF" "$CORE"; do
    [ -e "$_d" ] && [ ! -d "$_d" ] && mv -f "$_d" "$_d.bad_$(date +%s)" 2>/dev/null
    mkdir -p "$_d" 2>/dev/null
  done
  chmod -R u+rwX "$BASE" 2>/dev/null
  rm -f "$CORE/.ver" "$CORE/mediaforge.py" 2>/dev/null
  if command -v python3 >/dev/null 2>&1; then
    for _j in settings history queue hashes stats schedule profiles links; do
      _f="$CONF/$_j.json"
      if [ -f "$_f" ] && ! python3 -c "import json,sys; json.load(open(sys.argv[1]))" "$_f" 2>/dev/null; then
        mkdir -p "$CONF/corrupt"; mv -f "$_f" "$CONF/corrupt/$_j.json.$(date +%s)"; echo "[+] repaired $_j.json"
      fi
    done
  fi
  echo "[+] folders repaired / папки исправлены"
}
for _a in "$@"; do case "$_a" in --repair) repair_core ;; esac; done
mkdir -p "$CONF" "$CORE" 2>/dev/null
{ [ -d "$CONF" ] && [ -d "$CORE" ] && [ -w "$CONF" ]; } || repair_core
case "$0" in /*) MF_SELF="$0" ;; *) MF_SELF="$(pwd)/$0" ;; esac
[ -f "$MF_SELF" ] && echo "$MF_SELF" > "$CONF/self_path"
MF_DEBUG="${MF_DEBUG:-0}"
for _a in "$@"; do case "$_a" in --debug|-d) MF_DEBUG=1 ;; esac; done
export MF_DEBUG
SPINLOG="/tmp/mf_spin.log"

# ---------- цвета (только в терминале) ----------
if [ -t 1 ]; then
  C_OK='\033[38;5;84m'; C_ER='\033[38;5;203m'; C_WN='\033[38;5;220m'; C_IN='\033[38;5;51m'; C_AC='\033[38;5;45m'; C_DM='\033[2m'; C_RS='\033[0m'
else
  C_OK=''; C_ER=''; C_WN=''; C_IN=''; C_AC=''; C_DM=''; C_RS=''
fi
say_ok() { printf '%b[+] %s%b\n' "$C_OK" "$*" "$C_RS"; }
say_er() { printf '%b[!] %s%b\n' "$C_ER" "$*" "$C_RS"; }
say_wn() { printf '%b[!] %s%b\n' "$C_WN" "$*" "$C_RS"; }
say_in() { printf '%b[*] %s%b\n' "$C_IN" "$*" "$C_RS"; }
# отладочное сообщение (только при --debug), дублируется в журнал
dbg() { [ "$MF_DEBUG" = "1" ] && printf '%b[dbg] %s%b\n' "$C_DM" "$*" "$C_RS" >&2; [ "$MF_DEBUG" = "1" ] && echo "$(date '+%H:%M:%S' 2>/dev/null) sh $*" >> "$CONF/debug.log" 2>/dev/null; return 0; }
T() { if [ "$MF_LANG" = "en" ]; then printf '%s' "$2"; else printf '%s' "$1"; fi; }

# ---------- градиент для shell (ASCII): sh_grad "текст" сдвиг ----------
sh_col() { # ping-pong по палитре ocean: индекс → цвет 256
  _p=$(( $1 % 18 )); [ "$_p" -ge 10 ] && _p=$((18 - _p))
  case "$_p" in 0) echo 27 ;; 1) echo 33 ;; 2) echo 39 ;; 3) echo 45 ;; 4) echo 51 ;; 5) echo 50 ;; 6) echo 49 ;; 7) echo 48 ;; 8) echo 84 ;; *) echo 120 ;; esac
}
sh_grad() {
  _t="$1"; _sh="${2:-0}"; _k=0
  if [ ! -t 1 ]; then printf '%s' "$_t"; return; fi
  while [ -n "$_t" ]; do
    _r="${_t#?}"; _ch="${_t%"$_r"}"; _t="$_r"
    printf '\033[1;38;5;%sm%s' "$(sh_col $((_k + _sh)))" "$_ch"
    _k=$((_k + 1))
  done
  printf '\033[0m'
}
# анимированная шапка при старте (бегущий градиент)
sh_banner() {
  [ -t 1 ] || { echo "== MediaForge =="; return; }
  _f=0
  while [ "$_f" -lt 14 ]; do
    printf '\r  '; sh_grad '=== M E D I A F O R G E ===' "$_f"
    sleep 0.04 2>/dev/null || true
    _f=$((_f + 1))
  done
  printf '  %b(%s)%b\n' "$C_DM" "$MF_BUILD" "$C_RS"
}

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

# ---------- журнал аудита (цепочка хэшей, ротация) ----------
AUDIT="$CONF/audit.log"
# audit действие детали — запись с хэшем предыдущей строки (tamper-detection)
audit() {
  _pv="$(tail -n 1 "$AUDIT" 2>/dev/null | sha256sum 2>/dev/null | cut -d' ' -f1)"
  printf '%s | %s | %s | %s | %s\n' "$(date '+%Y-%m-%d %H:%M:%S' 2>/dev/null)" "$(id -un 2>/dev/null || echo user)" "$1" "$2" "${_pv:-0}" >> "$AUDIT" 2>/dev/null
  _sz="$(wc -c < "$AUDIT" 2>/dev/null || echo 0)"
  if [ "${_sz:-0}" -gt 1048576 ]; then mv -f "$AUDIT" "$AUDIT.1" 2>/dev/null; : > "$AUDIT"; fi
  if [ -f "$AUDIT.1" ] && [ "$(wc -c < "$AUDIT.1" 2>/dev/null || echo 0)" -gt 10485760 ]; then rm -f "$AUDIT.1"; fi
}

# ---------- проверка целостности скрипта ----------
check_signature() {
  [ -f "$MF_SELF" ] || return 0
  command -v sha256sum >/dev/null 2>&1 || return 0
  _cur="$(sha256sum "$MF_SELF" 2>/dev/null | cut -d' ' -f1)"
  _sf="$CONF/signature"
  if [ -f "$_sf" ]; then
    _sb="$(cut -d' ' -f1 "$_sf" 2>/dev/null)"; _ss="$(cut -d' ' -f2 "$_sf" 2>/dev/null)"
    if [ "$_sb" = "$MF_BUILD" ] && [ "$_ss" != "$_cur" ]; then
      say_wn "$(T 'Файл скрипта изменён без смены версии (build). Если это не вы — остановитесь.' 'Script file changed without a build bump. If it was not you — stop.')"
      audit signature-mismatch "build=$MF_BUILD"
      if [ -t 0 ]; then
        printf '%s [y/N]: ' "$(T 'Продолжить?' 'Continue?')"; IFS= read -r _a
        case "$_a" in y|Y|д|Д|yes|да) ;; *) exit 1 ;; esac
      fi
    fi
  fi
  echo "$MF_BUILD $_cur" > "$_sf" 2>/dev/null
}

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

# ---------- спиннер с градиентом: run_spin "текст" команда... ----------
run_spin() {
  _msg="$1"; shift
  _t0="$(date +%s 2>/dev/null || echo 0)"
  if [ ! -t 1 ]; then say_in "$_msg..."; "$@" >"$SPINLOG" 2>&1; return $?; fi
  ( "$@" ) >"$SPINLOG" 2>&1 &
  _pid=$!; _i=0
  while kill -0 "$_pid" 2>/dev/null; do
    case $((_i % 10)) in 0) _f='⠋' ;; 1) _f='⠙' ;; 2) _f='⠹' ;; 3) _f='⠸' ;; 4) _f='⠼' ;; 5) _f='⠴' ;; 6) _f='⠦' ;; 7) _f='⠧' ;; 8) _f='⠇' ;; *) _f='⠏' ;; esac
    _el=$(( $(date +%s 2>/dev/null || echo 0) - _t0 ))
    printf '\r\033[K \033[1;38;5;%sm%s\033[0m %b%s%b %b%ss%b' "$(sh_col $((_i / 2)))" "$_f" "$C_AC" "$_msg" "$C_RS" "$C_DM" "$_el" "$C_RS" >&2
    _i=$((_i + 1)); sleep 0.1 2>/dev/null || sleep 1
  done
  wait "$_pid" 2>/dev/null; _rc=$?
  _el=$(( $(date +%s 2>/dev/null || echo 0) - _t0 ))
  if [ "$_rc" -eq 0 ]; then printf '\r\033[K %b✓%b %s %b(%ss)%b\n' "$C_OK" "$C_RS" "$_msg" "$C_DM" "$_el" "$C_RS" >&2
  else printf '\r\033[K %b✗%b %s %b(%ss, rc=%s)%b\n' "$C_WN" "$C_RS" "$_msg" "$C_DM" "$_el" "$_rc" "$C_RS" >&2; fi
  dbg "spin '$_msg' rc=$_rc"
  return $_rc
}

# DNS: принудительная перезапись (iSH DNS иногда «не просыпается» с первого запроса)
force_dns() {
  if [ -w /etc/resolv.conf ] || [ ! -e /etc/resolv.conf ]; then
    printf 'nameserver 1.1.1.1\nnameserver 8.8.8.8\nnameserver 9.9.9.9\n' > /etc/resolv.conf 2>/dev/null
  fi
}

# ---------- Alpine: репозитории, версии, без лишних обновлений ----------
SAFE_ALPINE="3.19 3.20 3.18 3.17 3.21"
valid_alpine() { case "$1" in 3.17|3.18|3.19|3.20|3.21) return 0 ;; esac; return 1; }
alp_cur() { cut -d. -f1,2 /etc/alpine-release 2>/dev/null; }
repo_ver() { sed -n 's#.*alpine/v\(3\.[0-9]*\)/.*#\1#p' /etc/apk/repositories 2>/dev/null | head -n 1; }
# apk update с повтором: первый запрос в iSH часто падает (SSL eof / Errno -3)
apk_update_retry() {
  _i=0
  while [ "$_i" -lt 3 ]; do
    _i=$((_i + 1))
    apk update >/tmp/mf_apkupd.log 2>&1
    if grep -q '^OK:' /tmp/mf_apkupd.log 2>/dev/null; then return 0; fi
    dbg "apk update try $_i: $(tail -n 1 /tmp/mf_apkupd.log 2>/dev/null)"
    sleep 3; force_dns
  done
  return 1
}
set_repos() {
  _v="$1"
  printf 'https://dl-cdn.alpinelinux.org/alpine/v%s/main\nhttps://dl-cdn.alpinelinux.org/alpine/v%s/community\n' "$_v" "$_v" > /etc/apk/repositories
  apk_update_retry && return 0
  for _m in mirror.yandex.ru/mirrors/alpine mirrors.ustc.edu.cn/alpine mirror.leaseweb.com/alpine alpine.global.ssl.fastly.net/alpine ftp.halifax.rwth-aachen.de/alpine; do
    printf 'https://%s/v%s/main\nhttps://%s/v%s/community\n' "$_m" "$_v" "$_m" "$_v" > /etc/apk/repositories
    apk_update_retry && return 0
  done
  return 1
}
# в начале: чистим /ish (иначе репозитории сбрасываются) и ставим CDN-репозитории только если они «чужие»
fix_repos_start() {
  is_apk || return 0
  [ "$MF_ENV" = "ish" ] && rm -rf /ish 2>/dev/null
  _good="$(cat "$CONF/good_alpine" 2>/dev/null)"; valid_alpine "$_good" || _good=""
  if ! grep -Eq 'alpine/v3\.(17|18|19|20|21)/(main|community)' /etc/apk/repositories 2>/dev/null; then
    _want="${_good:-3.19}"
    say_in "$(T "Репозитории Alpine → v$_want (старые адреса iSH недоступны)" "Alpine repositories → v$_want (old iSH URLs are dead)")"
    printf 'https://dl-cdn.alpinelinux.org/alpine/v%s/main\nhttps://dl-cdn.alpinelinux.org/alpine/v%s/community\n' "$_want" "$_want" > /etc/apk/repositories
    audit repos "v$_want"
  fi
  return 0
}
# один раз выравниваем систему под версию репозиториев (musl и др.); glib.trigger=159 безвреден
sync_alpine() {
  is_apk || return 0
  _rv="$(repo_ver)"; [ -n "$_rv" ] || return 0
  [ "$_rv" = "$(alp_cur)" ] && return 0
  [ -f "$CONF/synced_$_rv" ] && return 0
  apk_update_retry || say_wn "$(T 'apk update не удался — работаю с тем, что есть' 'apk update failed — continuing as is')"
  run_spin "$(T "Выравниваю Alpine → v$_rv (один раз)" "Aligning Alpine → v$_rv (once)")" apk upgrade --available
  touch "$CONF/synced_$_rv" 2>/dev/null
  audit apk-upgrade "v$_rv"
}
python_ok() {
  command -v python3 >/dev/null 2>&1 && python3 -c 'import sys; sys.exit(0 if sys.version_info >= (3,10) else 1)' >/dev/null 2>&1
}
# Python реально запускается (не падает с SIGSYS) и базовые модули импортируются
py_smoke() { python3 -c 'import sys, os, json, ssl, socket; print("ok")' >/dev/null 2>&1; }
# оценка окружения: -1 = сам Python падает; иначе число проваленных ОБЯЗАТЕЛЬНЫХ модулей (проверка каждого модуля отдельным процессом)
score_env() {
  python_ok || { echo -1; return; }
  py_smoke || { echo -1; return; }
  _n=0; : > "$CONF/env_probe.log"
  for _m in json ssl socket select zlib hashlib threading; do
    python3 -c "import $_m" >/dev/null 2>&1; _rc=$?
    if [ "$_rc" -ne 0 ]; then _n=$((_n + 1)); echo "FAIL $_m rc=$_rc" >> "$CONF/env_probe.log"; fi
  done
  for _m in sqlite3 yt_dlp gallery_dl; do
    python3 -c "import $_m" >/dev/null 2>&1; _rc=$?
    [ "$_rc" -ne 0 ] && echo "WARN $_m rc=$_rc" >> "$CONF/env_probe.log"
  done
  echo "$_n"
}
# переустановка Python под версию Alpine (только когда нужен)
alpine_try() {
  _v="$1"
  set_repos "$_v" || return 1
  if [ "$(alp_cur)" = "$_v" ] && python_ok && py_smoke; then return 0; fi
  [ "$(alp_cur)" = "$_v" ] || apk upgrade --available >/dev/null 2>&1 || true
  apk del python3 py3-pip >/dev/null 2>&1 || true
  apk add --no-cache python3 py3-pip curl ca-certificates >/dev/null 2>&1 || true
  python_ok && py_smoke
}
# подбор версии: ТОЛЬКО если Python не работает. find_alpine [force]
find_alpine() {
  is_apk || return 1
  if [ "$1" != "force" ] && valid_alpine "$(alp_cur)" && python_ok && py_smoke; then
    echo "$(alp_cur)" > "$CONF/good_alpine"
    say_ok "$(T "Alpine $(alp_cur) и Python в порядке — менять ничего не нужно." "Alpine $(alp_cur) and Python are fine — nothing to change.")"
    return 0
  fi
  _good="$(cat "$CONF/good_alpine" 2>/dev/null)"; valid_alpine "$_good" || _good=""
  _vers="$SAFE_ALPINE"; [ -n "$_good" ] && _vers="$_good $SAFE_ALPINE"
  _tried=" "; _n=0
  for _v in $_vers; do
    case "$_tried" in *" $_v "*) continue ;; esac
    _tried="$_tried$_v "; _n=$((_n + 1)); [ "$_n" -gt 4 ] && break
    say_in "$(T "Пробую Alpine $_v ..." "Trying Alpine $_v ...")"
    run_spin "Alpine $_v" alpine_try "$_v" || { say_wn "Alpine $_v: $(T 'не подошла' 'did not work')"; continue; }
    if [ "$(score_env)" = "0" ]; then echo "$_v" > "$CONF/good_alpine"; audit alpine "v$_v"; say_ok "Alpine $_v + Python $(python3 -V 2>&1 | cut -d' ' -f2)"; return 0; fi
    say_wn "Alpine $_v: $(T 'проверка модулей не пройдена' 'module check failed')"
  done
  return 1
}

# ---------- пакеты ----------
# apk add с проверкой результата: ошибка триггера glib (159) игнорируется, если пакеты на месте
apk_add_verify() {
  apk add --no-cache "$@" >/tmp/mf_apkadd.log 2>&1
  for _p in "$@"; do apk info -e "$_p" >/dev/null 2>&1 || return 1; done
  return 0
}
install_packages() {
  case "$MF_ENV" in
    ish|alpine)
      _im="imagemagick"
      case "$(alp_cur)" in 3.14|3.15|3.16|3.17|3.18) ;; *) _im="imagemagick imagemagick-jpeg imagemagick-webp imagemagick-tiff" ;; esac
      _need=""
      for _p in ffmpeg nodejs exiftool $_im jpegoptim mediainfo; do apk info -e "$_p" >/dev/null 2>&1 || _need="$_need $_p"; done
      [ -z "$_need" ] && return 0
      apk_update_retry || say_wn "$(T 'apk update не удался — пробую установить из кэша' 'apk update failed — trying from cache')"
      for _p in $_need; do
        run_spin "apk add $_p" apk_add_verify "$_p" || say_wn "$_p: $(T 'не установился (не критично)' 'not installed (non-critical)')"
      done ;;
    termux) run_spin "pkg" pkg install -y python ffmpeg nodejs exiftool imagemagick curl ;;
    debian) run_spin "apt" apt-get install -y python3 python3-pip ffmpeg nodejs libimage-exiftool-perl imagemagick curl ;;
    macos) run_spin "brew" brew install python ffmpeg node exiftool imagemagick ;;
  esac
  return 0
}
# ffmpeg в iSH иногда падает с SIGSYS: LD_PRELOAD-обход (источник: tjcaul/iSH-LD_PRELOAD-Hack), best-effort
ffmpeg_hack() {
  is_apk || return 1
  _src="$CONF/ffmpeg-hack.c"
  if [ ! -s "$_src" ]; then
    for _u in https://raw.githubusercontent.com/tjcaul/iSH-LD_PRELOAD-Hack/main/ffmpeg-hack.c https://raw.githubusercontent.com/tjcaul/iSH-LD_PRELOAD-Hack/master/ffmpeg-hack.c; do
      curl -fsSL "$_u" -o "$_src" 2>/dev/null && [ -s "$_src" ] && break
      rm -f "$_src"
    done
  fi
  [ -s "$_src" ] || return 1
  apk_add_verify gcc musl-dev || return 1
  mkdir -p /usr/local/lib /usr/local/bin
  gcc -O2 -shared -fPIC -o /usr/local/lib/ffmpeg-hack.so "$_src" -ldl 2>/dev/null || return 1
  for _b in ffmpeg ffprobe; do
    printf '#!/bin/sh\nexec env LD_PRELOAD=/usr/local/lib/ffmpeg-hack.so /usr/bin/%s "$@"\n' "$_b" > "/usr/local/bin/$_b"
    chmod 755 "/usr/local/bin/$_b"
  done
  audit ffmpeg-hack ok
  ffmpeg -version >/dev/null 2>&1
}
ffmpeg_check() {
  command -v ffmpeg >/dev/null 2>&1 || return 0
  ffmpeg -version >/dev/null 2>&1; _rc=$?
  [ "$_rc" -lt 128 ] && return 0
  say_wn "$(T "ffmpeg падает (код $_rc) — пробую LD_PRELOAD-обход" "ffmpeg crashes (rc $_rc) — trying LD_PRELOAD hack")"
  if run_spin "ffmpeg LD_PRELOAD" ffmpeg_hack; then say_ok "ffmpeg OK"; else say_wn "$(T 'Обход не удался: конвертация недоступна, загрузка работает.' 'Hack failed: conversion unavailable, downloads still work.')"; fi
}

# pip: цепочка — обычная установка → повтор после DNS → зеркала → --user → --no-deps
PIP_MIRRORS="https://mirrors.aliyun.com/pypi/simple https://pypi.tuna.tsinghua.edu.cn/simple https://mirrors.cloud.tencent.com/pypi/simple"
pip_install() {
  : > /tmp/mf_pip.log
  for _try in 1 2; do
    python3 -m pip install -U --break-system-packages "$@" >>/tmp/mf_pip.log 2>&1 && return 0
    python3 -m pip install -U "$@" >>/tmp/mf_pip.log 2>&1 && return 0
    sleep 2; force_dns
  done
  for _m in $PIP_MIRRORS; do
    python3 -m pip install -U --break-system-packages -i "$_m" "$@" >>/tmp/mf_pip.log 2>&1 && return 0
  done
  python3 -m pip install -U --user --break-system-packages "$@" >>/tmp/mf_pip.log 2>&1 && return 0
  python3 -m pip install -U --no-deps --break-system-packages "$@" >>/tmp/mf_pip.log 2>&1
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
# подготовка окружения: Alpine меняется ТОЛЬКО если Python не запускается
ensure_env() {
  force_dns
  fix_repos_start
  if ! python_ok || ! py_smoke; then
    say_wn "$(T 'Python 3.10+ недоступен или падает — настраиваю Alpine...' 'Python 3.10+ is unavailable or crashes — configuring Alpine...')"
    if is_apk; then sync_alpine; find_alpine force || true
    else
      case "$MF_ENV" in termux) pkg install -y python ;; debian) apt-get update && apt-get install -y python3 python3-pip ;; macos) brew install python ;; esac
    fi
  fi
  python_ok && py_smoke || { say_er "$(T 'Python 3.10+ недоступен. Установите вручную и запустите снова.' 'Python 3.10+ unavailable. Install it manually and re-run.')"; exit 1; }
  if ! tools_ok; then
    is_apk && sync_alpine
    install_packages
    ensure_pytools
  fi
  _sc="$(score_env)"
  case "$_sc" in
    0) ;;
    -1) say_er "$(T 'Сам Python падает — подбираю Alpine.' 'Python itself crashes — picking Alpine.')"; is_apk && find_alpine force ;;
    *) say_wn "$(T "Не импортируются модули: $(grep '^FAIL' "$CONF/env_probe.log" 2>/dev/null | tr '\n' ' ') — Alpine не трогаю." "Modules fail to import: $(grep '^FAIL' "$CONF/env_probe.log" 2>/dev/null | tr '\n' ' ') — leaving Alpine alone.")" ;;
  esac
  ffmpeg_check
  return 0
}
update_pkgs() {
  case "$MF_ENV" in
    ish|alpine) apk_update_retry; run_spin "apk upgrade" apk upgrade --available ;;
    termux) run_spin "pkg upgrade" pkg upgrade -y ;;
    debian) run_spin "apt upgrade" sh -c 'apt-get update && apt-get upgrade -y' ;;
  esac
  audit pkgupdate "$MF_ENV"
  say_ok "$(T 'Пакеты обновлены.' 'Packages updated.')"
}
apply_update() {
  _new="$CONF/MediaForge.new"
  if [ -f "$_new" ] && head -1 "$_new" | grep -q '^#!/bin/sh' && grep -q 'MF_BUILD=' "$_new"; then
    _dst="$MF_SELF"; [ -f "$_dst" ] || _dst="$HOME/MediaForge.sh"
    cp "$_new" "$_dst" && chmod 700 "$_dst" && rm -f "$_new" && echo "$_dst" > "$CONF/self_path"
    audit update "$_dst"
    say_ok "$(T "Обновлено: $_dst — перезапуск..." "Updated: $_dst — restarting...")"
    exec sh "$_dst"
  fi
  say_er "$(T 'Файл обновления повреждён.' 'Update file is damaged.')"
}

# ==========================================================================
#  ВСТРОЕННОЕ PYTHON-ЯДРО
# ==========================================================================
check_signature
sh_banner
if [ "${MF_FORCE:-0}" = "1" ] || [ ! -f "$CORE/mediaforge.py" ] || [ "$(cat "$CORE/.ver" 2>/dev/null)" != "$MF_BUILD" ]; then
cat > "$CORE/mediaforge.py" << 'PYEOF'
# -*- coding: utf-8 -*-
# ==========================================================================
#  MediaForge core. Один файл, только stdlib (+ yt-dlp, gallery-dl, mutagen; telethon — по желанию).
# ==========================================================================
import os, sys, re, json, time, shutil, socket, ssl, random, subprocess, threading, hashlib, traceback, html, builtins
import atexit, base64, struct, collections
from pathlib import Path
import urllib.request, urllib.error
from urllib.parse import urlparse, urljoin, quote, unquote, urlencode

# --- iSH: fork+exec наследует tty → SIGSYS. Всегда захватываем вывод и закрываем stdin (кроме input=) ---
_orig_run = subprocess.run
def _safe_run(*a, **k):
    # subprocess.run без захвата вывода на iSH убивает Python (SIGSYS 159)
    if not any(x in k for x in ("capture_output", "stdout", "stderr")):
        k["capture_output"] = True
    if "input" not in k and "stdin" not in k:
        k["stdin"] = subprocess.DEVNULL
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
DIRS = ("videos", "audio", "photos", "texts", "files", "tmp", "reports", "cookies", "collages", "certs")
UA_IOS = "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1"
UA_DESK = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
MF_DEBUG = os.environ.get("MF_DEBUG") == "1"
os.umask(0o022)

# ==========================================================================
#  НАСТРОЙКИ (схема → автоматическое меню). (группа, ключ, умолч., тип, варианты, RU, EN)
# ==========================================================================
SCHEMA = [
 ("design", "theme", "ocean", "choice", ("ocean", "sunset", "neon", "matrix", "candy", "aurora", "fire", "mono"), "Цветовая тема", "Color theme"),
 ("design", "anim", True, "bool", None, "Анимации", "Animations"),
 ("design", "anim_speed", 100, "int", (30, 300), "Скорость анимации, %", "Animation speed, %"),
 ("design", "banner_anim", True, "bool", None, "Анимированный баннер и ракета", "Animated banner & rocket"),
 ("design", "menu_anim", True, "bool", None, "Переливающийся градиент в заголовках меню", "Shimmering gradient in menu headers"),
 ("design", "ascii_art", True, "bool", None, "Крупный логотип в баннере", "Big logo in banner"),
 ("design", "spinner", "braille", "choice", ("braille", "dots", "line", "arc", "pulse", "bounce"), "Стиль спиннера", "Spinner style"),
 ("design", "bar_style", "smooth", "choice", ("smooth", "blocks", "bars", "dots", "arrows", "ascii"), "Стиль прогресс-бара", "Progress bar style"),
 ("design", "bar_width", 0, "int", (0, 60), "Длина бара (0 — авто)", "Bar width (0 = auto)"),
 ("design", "bar_gradient", True, "bool", None, "Градиент в баре", "Bar gradient"),
 ("design", "bar_flow", True, "bool", None, "Бегущий градиент в баре", "Flowing bar gradient"),
 ("design", "bar_speed", True, "bool", None, "Показывать скорость", "Show speed"),
 ("design", "bar_eta", True, "bool", None, "Показывать ETA", "Show ETA"),
 ("design", "unicode", True, "bool", None, "Юникод-символы (иначе ASCII)", "Unicode glyphs (else ASCII)"),
 ("design", "color", "256", "choice", ("256", "16", "off"), "Цвет: 256 / 16 / выкл", "Color: 256 / 16 / off"),
 ("design", "clear", True, "bool", None, "Очищать экран между меню", "Clear screen between menus"),
 ("design", "max_width", 0, "int", (0, 200), "Макс. ширина текста (0 — авто)", "Max text width (0 = auto)"),
 ("design", "lang", "ru", "choice", ("ru", "en"), "Язык / Language", "Language / Язык"),
 ("design", "hints", True, "bool", None, "Показывать подсказки (описания пунктов и форматы ввода)", "Show hints (item descriptions and input formats)"),
 ("download", "quality", "best", "choice", ("best", "2160", "1440", "1080", "720", "480", "360"), "Макс. качество видео (высота)", "Max video quality (height)"),
 ("download", "device", "generic", "choice", ("generic", "iphone", "ipad", "android", "appletv", "chromecast"), "Устройство (кодеки/контейнер подбираются сами)", "Target device (codecs/container auto)"),
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
 ("download", "auto_dedupe", True, "bool", None, "Удалять дубликаты после загрузки (SHA-256)", "Delete duplicates after download (SHA-256)"),
 ("download", "strip_meta", False, "bool", None, "Стирать метаданные (GPS и т.п.) после загрузки", "Strip metadata (GPS etc.) after download"),
 ("download", "sort_content", False, "bool", None, "Раскладывать по содержимому (shorts/long, артист/альбом)", "Sort by content (shorts/long, artist/album)"),
 ("download", "summary", False, "bool", None, "Создавать .summary.txt и сетку кадров", "Create .summary.txt and frame grid"),
 ("download", "library_html", False, "bool", None, "Обновлять index.html медиатеки", "Update library index.html"),
 ("download", "contact_sheet", True, "bool", None, "Contact sheet 3×3 (_contact.jpg) для каждого видео", "Contact sheet 3×3 (_contact.jpg) for every video"),
 ("download", "verify_after_download", True, "bool", None, "Проверять целостность файла после загрузки (ffprobe)", "Verify file integrity after download (ffprobe)"),
 ("download", "original_quality", True, "bool", None, "Искать оригиналы вместо миниатюр на страницах", "Look for originals instead of thumbnails on pages"),
 ("download", "crawl_pages", 30, "int", (1, 500), "Обход сайта: максимум страниц", "Site crawl: max pages"),
 ("download", "crawl_depth", 2, "int", (0, 6), "Обход сайта: глубина ссылок", "Site crawl: link depth"),
 ("download", "tg_text", "all", "choice", ("all", "html", "md", "txt"), "Текст из Telegram: форматы сохранения", "Telegram text: save formats"),
 ("behavior", "ask_selection", "ask", "choice", ("ask", "all", "first"), "Если на странице несколько медиа: спросить / все / первое", "Several media on a page: ask / all / first"),
 ("behavior", "skip_history", True, "bool", None, "Пропускать уже скачанное", "Skip already downloaded"),
 ("behavior", "retry_rounds", 2, "int", (1, 10), "Кругов повтора для неудачных", "Retry rounds for failed"),
 ("behavior", "sleep_between", 2, "int", (0, 600), "Пауза между загрузками, с", "Pause between downloads, s"),
 ("behavior", "sleep_slow", 20, "int", (0, 300), "Доп. пауза для Instagram/TikTok/X, с", "Extra pause for Instagram/TikTok/X, s"),
 ("behavior", "tls_fallback", "ask", "choice", ("ask", "auto", "never"), "Ошибка TLS: спросить / без проверки / никогда", "TLS error: ask / insecure / never"),
 ("behavior", "min_free_mb", 300, "int", (0, 100000), "Остановка при свободном месте меньше, МБ", "Stop if free space below, MB"),
 ("behavior", "bell", True, "bool", None, "Сигнал по окончании", "Bell when finished"),
 ("behavior", "audit", True, "bool", None, "Журнал аудита (цепочка хэшей)", "Audit log (hash chain)"),
 ("behavior", "verbose", False, "bool", None, "Подробный вывод + запись в debug.log", "Verbose output + write debug.log"),
 ("behavior", "health_start", True, "bool", None, "Быстрая проверка окружения при старте", "Quick environment check at start"),
 ("behavior", "trash", True, "bool", None, "Удалять через корзину (можно восстановить)", "Delete via trash (restorable)"),
 ("behavior", "trash_ttl_days", 7, "int", (1, 90), "Хранить корзину, дней", "Keep trash, days"),
 ("behavior", "auto_backup", True, "bool", None, "Ежедневный бэкап настроек и списков", "Daily backup of settings and lists"),
 ("behavior", "enable_plugins", True, "bool", None, "Плагины из папки plugins/", "Plugins from the plugins/ folder"),
 ("behavior", "enable_hooks", False, "bool", None, "Хуки hooks/<событие>.sh (выполняют команды!)", "Hooks hooks/<event>.sh (run commands!)"),
 ("behavior", "notify_telegram", False, "bool", None, "Уведомления в Telegram", "Telegram notifications"),
 ("behavior", "telegram_bot_token", "", "str", None, "Токен Telegram-бота для уведомлений", "Telegram bot token for notifications"),
 ("behavior", "telegram_chat_id", "", "str", None, "Chat ID для уведомлений", "Chat ID for notifications"),
 ("behavior", "remedy", True, "bool", None, "После пакета ошибок предлагать способы починки", "Offer fixes after a batch with failures"),
 ("network", "proxy", "", "str", None, "Прокси (http/socks5, можно user:pass@host:port)", "Proxy (http/socks5, user:pass@host:port ok)"),
 ("network", "proxy_allow_lan", False, "bool", None, "Показывать LAN-шаблоны прокси (общий доступ)", "Show LAN proxy templates (shared access)"),
 ("network", "dns_mode", "auto", "choice", ("auto", "system", "doh", "udp"), "DNS: авто / системный / DoH / UDP", "DNS: auto / system / DoH / UDP"),
 ("network", "doh_url", "https://1.1.1.1/dns-query", "str", None, "DoH-сервер (основной)", "DoH server (primary)"),
 ("network", "dns_servers", "1.1.1.1", "str", None, "UDP-DNS сервер(ы) через запятую", "UDP DNS server(s), comma separated"),
 ("network", "ip_version", "auto", "choice", ("auto", "ipv4", "ipv6"), "IP-версия", "IP version"),
 ("network", "https_upgrade", True, "bool", None, "Поднимать http:// до https:// (с откатом)", "Upgrade http:// to https:// (with fallback)"),
 ("network", "rate_per_min", 60, "int", (0, 600), "Лимит запросов на домен в минуту (0 — без)", "Requests per domain per minute (0 = off)"),
 ("network", "mitm_policy", "ask", "choice", ("ask", "allow", "reject"), "MITM без доверенного CA: спросить / разрешить / запретить", "MITM without trusted CA: ask / allow / reject"),
 ("network", "mitm_warn_on_start", True, "bool", None, "Предупреждать о MITM при старте", "Warn about MITM at start"),
 ("network", "extra_ca", "", "str", None, "Доп. CA-файл (PEM): сертификат прокси-клиента и т.п.", "Extra CA file (PEM): proxy-client cert etc."),
 ("network", "impersonate", True, "bool", None, "Подмена TLS-отпечатка браузера (curl_cffi, если установлен)", "Browser TLS fingerprint (curl_cffi, if installed)"),
 ("network", "captcha_service", "none", "choice", ("none", "flaresolverr", "capsolver"), "Обход Cloudflare-челленджа: сервис", "Cloudflare challenge solver service"),
 ("network", "flaresolverr_url", "http://127.0.0.1:8191/v1", "str", None, "Адрес FlareSolverr", "FlareSolverr URL"),
 ("network", "capsolver_key", "", "str", None, "Ключ CapSolver", "CapSolver API key"),
 ("network", "use_tor", False, "bool", None, "Направлять запросы через Tor (если запущен)", "Route requests through Tor (if running)"),
 ("network", "bridges_url", "https://raw.githubusercontent.com/scriptzteam/Tor-Bridges-Collector/main/bridges-obfs4,https://raw.githubusercontent.com/scriptzteam/Tor-Bridges-Collector/main/bridges-webtunnel", "str", None, "Публичные списки мостов Tor (через запятую)", "Public Tor bridge lists (comma separated)"),
 ("network", "vk_token", "", "str", None, "Токен VK для музыки", "VK token for music"),
 ("network", "ping_enabled", True, "bool", None, "Проверять интернет перед сетевыми операциями", "Check internet before network operations"),
 ("network", "ping_cache_sec", 30, "int", (0, 600), "Кэш результата пинга, с", "Ping result cache, s"),
 ("network", "ping_timeout", 3, "int", (1, 30), "Таймаут пинга, с", "Ping timeout, s"),
 ("network", "verbose_ping", False, "bool", None, "Показывать успешный пинг", "Show successful ping"),
 ("network", "cookies_file", "", "str", None, "Файл cookies (Netscape); иначе cookies/<домен>.txt", "Cookies file (Netscape); else cookies/<domain>.txt"),
 ("network", "encrypt_cookies", False, "bool", None, "Хранить cookies зашифрованными (Vault)", "Keep cookies encrypted (Vault)"),
 ("network", "socket_timeout", 30, "int", (5, 300), "Таймаут сокета, с", "Socket timeout, s"),
 ("network", "retries", 8, "int", (0, 30), "Повторы запросов", "Request retries"),
 ("network", "fragments", 4, "int", (1, 16), "Параллельные фрагменты", "Concurrent fragments"),
 ("network", "rate_limit", "", "str", None, "Лимит скорости (напр. 2M)", "Rate limit (e.g. 2M)"),
 ("network", "ua", "ios", "choice", ("ios", "desktop", "random"), "User-Agent для страниц (random — случайный браузер)", "User-Agent for pages (random = random browser)"),
 ("network", "antibot", True, "bool", None, "Антибот: случайные заголовки (Accept-Language, DNT…)", "Anti-bot: randomized headers (Accept-Language, DNT…)"),
 ("network", "antibot_delay", False, "bool", None, "Антибот: случайная пауза 1–3 с между запросами", "Anti-bot: random 1–3 s pause between requests"),
 ("network", "proxy_pool", "", "str", None, "Пул прокси через запятую (случайный при пустом «proxy»)", "Proxy pool, comma separated (random when 'proxy' is empty)"),
 ("network", "extra_args", "", "str", None, "Доп. аргументы yt-dlp (для запуска как процесс)", "Extra yt-dlp args (process mode)"),
 ("network", "update_url", "", "str", None, "URL обновления скрипта", "Script update URL"),
]
GROUPS = [("design", "Оформление", "Design"), ("download", "Загрузка и качество", "Download & quality"), ("behavior", "Поведение и автозагрузка", "Behavior & auto-download"), ("network", "Сеть, прокси и cookies", "Network, proxy & cookies")]
SCH = {s[1]: s for s in SCHEMA}
PROXY_T = ["", "http://127.0.0.1:1082", "http://127.0.0.1:8080", "http://127.0.0.1:3128", "socks5://127.0.0.1:1080", "socks5h://127.0.0.1:1080", "socks5://127.0.0.1:10808", "socks5h://127.0.0.1:9050"]
SETTINGS_FILE = CONF / "settings.json"
PROFILES_FILE = CONF / "profiles.json"
# встроенные профили настроек (применяются поверх текущих; ключи проверяются по схеме)
BUILTIN_PROFILES = {
    "paranoid": {"dns_mode": "doh", "tls_fallback": "never", "mitm_policy": "reject", "strip_meta": True, "encrypt_cookies": True, "audit": True, "https_upgrade": True, "rate_per_min": 30, "embed_meta": False, "ask_selection": "ask"},
    "social": {"ask_selection": "all", "strip_meta": False, "quality": "1080", "prefer_h264": True, "device": "iphone", "sleep_between": 3, "sort_content": True, "auto_dedupe": True},
    "archive": {"ask_selection": "all", "embed_meta": True, "embed_thumb": True, "info_json": True, "subs": True, "container": "mkv", "quality": "best", "auto_dedupe": True, "summary": True, "library_html": True},
    "minimal": {"anim": False, "menu_anim": False, "banner_anim": False, "ascii_art": False, "bar_flow": False, "ping_enabled": False, "unicode": False, "clear": False, "audit": False},
}


class Store:
    # JSON-хранилище настроек с проверкой типов и временными переопределениями (ov)
    def __init__(self):
        self.ov = {}
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

    def valid(self, k, v):
        s = SCH.get(k)
        if not s or type(v) is not type(s[2]):
            return False
        if s[3] == "choice" and v not in s[4]:
            return False
        return True

    def g(self, k):
        if k in self.ov:
            return self.ov[k]
        s = SCH[k]
        v = self.d.get(k, s[2])
        if type(v) is not type(s[2]):
            return s[2]
        if s[3] == "choice" and v not in s[4]:
            return s[2]
        if s[3] == "int":
            return max(s[4][0], min(s[4][1], v))
        return v

    def save(self):
        try:
            CONF.mkdir(parents=True, exist_ok=True)
            t = SETTINGS_FILE.with_suffix(".tmp")
            t.write_text(json.dumps(self.d, ensure_ascii=False, indent=1), "utf-8")
            os.replace(str(t), str(SETTINGS_FILE))
        except Exception:
            pass

    def set(self, k, v):
        self.d[k] = v
        self.save()

    def mem(self, k, d=None):
        return self.d.get("_mem", {}).get(k, d)

    def setmem(self, k, v):
        self.d.setdefault("_mem", {})[k] = v
        self.save()


ST = Store()


def L(ru, en):
    return ru if ST.g("lang") == "ru" else en


# ==========================================================================
#  ОФОРМЛЕНИЕ: цвета, градиенты (бегущие), рамки, спиннер, прогресс-бар
# ==========================================================================
RESET, BOLD, DIM = "\033[0m", "\033[1m", "\033[2m"
PALETTES = {"ocean": [27, 33, 39, 45, 51, 50, 49, 48, 84, 120], "sunset": [196, 202, 208, 214, 220, 226, 190, 154], "neon": [201, 165, 129, 93, 57, 27, 33, 39, 45, 51],
            "matrix": [22, 28, 34, 40, 46, 82, 118, 154, 190], "candy": [213, 207, 201, 165, 171, 177, 183, 189, 195], "aurora": [53, 90, 127, 164, 135, 99, 63, 33, 39, 49],
            "fire": [52, 88, 124, 160, 196, 202, 208, 214, 220], "mono": [244, 247, 250, 253, 255, 253, 250, 247]}
OK_C, ERR_C, WARN_C, INFO_C, ASK_C = 84, 203, 220, 51, 213
ANSI_RE = re.compile(r"\x1b(?:\[[0-9;?]*[ -/]*[@-~]|[@-Z\\-_])")
_OUT = threading.RLock()


def cmode():
    # режим цвета: off для не-терминала и NO_COLOR
    if not sys.stdout.isatty() or os.environ.get("NO_COLOR"):
        return "off"
    return ST.g("color")


def fg(n):
    m = cmode()
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


def pp(i, n):
    # «пинг-понг» индекс: плавное движение градиента без скачка на стыке палитры
    if n <= 1:
        return 0
    m = i % (2 * (n - 1))
    return m if m < n else 2 * (n - 1) - m


def c(t, n, b=False):
    return str(t) if cmode() == "off" else (BOLD if b else "") + fg(n) + str(t) + RESET


def dim(t):
    return str(t) if cmode() == "off" else DIM + str(t) + RESET


def bold(t):
    return str(t) if cmode() == "off" else BOLD + str(t) + RESET


def grad(text, shift=0, b=False):
    # градиент по палитре темы; shift двигает «блик» (анимация)
    if cmode() == "off":
        return str(text)
    p, n, out = pal(), max(1, len(text) - 1), []
    for i, ch in enumerate(str(text)):
        if ch == " ":
            out.append(ch)
            continue
        idx = pp(int(round(i / n * (len(p) - 1))) + shift, len(p))
        out.append((BOLD if b else "") + fg(p[idx]) + ch)
    return "".join(out) + RESET


def vlen(s):
    # видимая длина строки (без ANSI, эмодзи = 2)
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


def speed_k():
    return max(0.3, ST.g("anim_speed") / 100.0)


def animating():
    return sys.stdout.isatty() and ST.g("anim")


# ---------- вывод: раскрашивающий print + журнал отладки ----------
DEBUG_LOG = CONF / "debug.log"
_TAG = re.compile(r"^(\s*)(\[[+!*?x]\])(\s?)(.*)$", re.S)
_MENU = re.compile(r"^(\s*)(\d{1,3}|[a-zA-Z])(\s*[-.)]\s+)(.*)$")
_ERRW = re.compile(r"(ошибк|error|fail|не удалось|не найден|traceback|denied|refused)", re.I)


def dlog(msg, level="DEBUG"):
    # запись в debug.log (при verbose или --debug); токены и пароли маскируются
    if not (MF_DEBUG or ST.g("verbose")):
        return
    try:
        CONF.mkdir(parents=True, exist_ok=True)
        if DEBUG_LOG.exists() and DEBUG_LOG.stat().st_size > 2 * 1048576:
            os.replace(str(DEBUG_LOG), str(DEBUG_LOG) + ".1")
        with open(str(DEBUG_LOG), "a", encoding="utf-8") as f:
            f.write("%s %-5s %s\n" % (time.strftime("%H:%M:%S"), level, redact(ANSI_RE.sub("", str(msg)))))
    except Exception:
        pass


def paint_line(s):
    # автоматическая раскраска строки по виду ([+] [!] [*] [?], пункты меню)
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
    if MF_DEBUG or ST.g("verbose"):
        dlog(text, "OUT")
    with _OUT:
        sys.stdout.write("\n".join(paint_line(x) for x in text.split("\n")) + end)
        if flush or end == "":
            sys.stdout.flush()


print = tprint


def redact(s):
    # маскировка секретов в логах: токены, cookies, пароли в URL
    s = re.sub(r"(?i)(sessionid|csrftoken|authorization|cookie|token|passw(?:or)?d|secret|api[_-]?key)(\s*[=:]\s*)([^\s;&\"']{4,})", r"\1\2<masked>", s)
    s = re.sub(r"(://[^/\s:@]+:)([^@\s/]+)(@)", r"\1<masked>\3", s)
    s = re.sub(r"\beyJ[A-Za-z0-9_\-]{10,}\.[A-Za-z0-9_\-]{10,}\.[A-Za-z0-9_\-]*", "<jwt>", s)
    return s


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
    # заголовок раздела: рамка, текст с переливающимся градиентом (короткая анимация)
    w = term_w()
    star = U("✦ ", "* ")
    anim = animating() and ST.g("menu_anim")
    frames = 8 if anim else 1
    sys.stdout.write("\n")
    n = 0
    for f in range(frames):
        lines = [grad(trunc(star + str(title), w - 4), f * 2, True)]
        if sub:
            lines.append(dim(trunc(sub, w - 4)))
        if f > 0:
            sys.stdout.write("\033[%dA" % n)
        sys.stdout.write(box(lines, None, w) + "\n")
        sys.stdout.flush()
        n = len(lines) + 2
        if anim:
            time.sleep(0.03 / speed_k())


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


# ---------- крупный логотип (5×5 блочный шрифт) ----------
FONT = {
    "A": [" ███ ", "█   █", "█████", "█   █", "█   █"], "D": ["████ ", "█   █", "█   █", "█   █", "████ "], "E": ["█████", "█    ", "████ ", "█    ", "█████"],
    "F": ["█████", "█    ", "████ ", "█    ", "█    "], "G": [" ████", "█    ", "█  ██", "█   █", " ███ "], "I": ["█████", "  █  ", "  █  ", "  █  ", "█████"],
    "K": ["█   █", "█  █ ", "███  ", "█  █ ", "█   █"], "L": ["█    ", "█    ", "█    ", "█    ", "█████"], "M": ["█   █", "██ ██", "█ █ █", "█   █", "█   █"],
    "O": [" ███ ", "█   █", "█   █", "█   █", " ███ "], "R": ["████ ", "█   █", "████ ", "█  █ ", "█   █"], "T": ["█████", "  █  ", "  █  ", "  █  ", "  █  "],
}


def art_rows(word):
    # строки крупного текста из блочных букв
    rows = ["", "", "", "", ""]
    for ch in word.upper():
        g = FONT.get(ch)
        if not g:
            continue
        for i in range(5):
            rows[i] += g[i] + " "
    return [r.rstrip() for r in rows]


def banner():
    # баннер: крупный логотип с бегущим диагональным градиентом (или компактный вариант)
    w = term_w(30, 56)
    words = ["MEDIA", "FORGE"]
    big = ST.g("ascii_art") and ST.g("unicode") and w >= 36
    sub = "D O W N L O A D  ·  C O N V E R T" if w >= 40 else "DOWNLOAD · CONVERT"
    anim = ST.g("banner_anim") and animating()
    frames = 18 if anim else 1
    for f in range(frames):
        lines = []
        if big:
            for wd in words:
                for ri, row in enumerate(art_rows(wd)):
                    lines.append(" " * max(0, (w - 4 - vlen(row)) // 2) + grad(row, f + ri, True))
        else:
            t = "M E D I A   F O R G E"
            lines.append(" " * max(0, (w - 4 - vlen(t)) // 2) + grad(t, f, True))
        lines.append(" " * max(0, (w - 4 - vlen(sub)) // 2) + grad(sub, -f))
        stars = "".join(random.choice(["  ", " ✦", " ·", "  ", " ✧"]) if ST.g("unicode") else random.choice(["  ", " *", " ."]) for _ in range(w // 2 - 1))
        lines.append(dim(stars[:w - 4]))
        if anim and f > 0:
            sys.stdout.write("\033[%dA" % (len(lines) + 2))
        sys.stdout.write(box(lines, None, w) + "\n")
        sys.stdout.flush()
        if anim:
            time.sleep(0.045 / speed_k())


def rocket():
    if not (animating() and ST.g("banner_anim") and ST.g("unicode")):
        return
    w, p = term_w(30, 50), pal()
    for i in range(0, w - 4, 2):
        trail = "".join(c("~", p[(j + i) % len(p)]) for j in range(max(0, min(i, 8))))
        sys.stdout.write("\r\033[K" + " " * max(0, i - 8) + trail + "🚀")
        sys.stdout.flush()
        time.sleep(0.02 / speed_k())
    sys.stdout.write("\r\033[K")


# ---------- спиннер (градиентный текст, всегда с итоговой строкой) ----------
SPIN = {"braille": "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏", "dots": "⣾⣽⣻⢿⡿⣟⣯⣷", "line": "|/-\\", "arc": "◜◠◝◞◡◟", "pulse": "▏▎▍▌▋▊▉█▉▊▋▌▍▎", "bounce": "⠁⠂⠄⡀⢀⠠⠐⠈"}


class Spin:
    # with Spin("..."): — спиннер в потоке; quiet=True не печатает итоговую строку
    def __init__(self, msg, quiet=False):
        self.msg, self.t0, self._stop, self.th, self.quiet = msg, time.time(), False, None, quiet
        self.live = animating()
        self.final = None
        self.ok = True

    def update(self, m):
        self.msg = m

    def _run(self):
        fr = SPIN.get(ST.g("spinner"), SPIN["braille"]) if ST.g("unicode") else "|/-\\"
        i, p = 0, pal()
        while not self._stop:
            txt = trunc(self.msg, max(10, term_w() - 14))
            line = "\r\033[K %s %s %s" % (c(fr[i % len(fr)], p[pp(i // 2, len(p))], True), grad(txt, i // 2) if ST.g("menu_anim") else txt, dim("%.0fs" % (time.time() - self.t0)))
            with _OUT:
                sys.stdout.write(line)
                sys.stdout.flush()
            i += 1
            time.sleep(0.08 / speed_k())

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
        dlog("spin '%s' %.1fs ok=%s" % (self.msg, time.time() - self.t0, et is None))
        return False


def spin(m, **k):
    return Spin(m, **k)


def busy(msg, fn, *a, **k):
    # выполнить fn под спиннером (тихо) и вернуть результат
    with Spin(msg, quiet=True):
        return fn(*a, **k)


# ---------- прогресс-бар: градиент (бегущий), без эмодзи ----------
BAR_STYLES = {"blocks": ("█", "░"), "bars": ("▰", "▱"), "dots": ("●", "○"), "arrows": ("▶", "·"), "ascii": ("#", "-")}
PARTIAL = " ▏▎▍▌▋▊▉"


class Bar:
    # Bar(total, label, unit): unit 'B' байты, 's' секунды, '' штуки; total=None — неопределённый режим
    def __init__(self, total=None, label="", unit=""):
        self.total, self.label, self.unit = total, label, unit
        self.cur, self.t0, self.last, self.speed, self.lc, self.lt = 0, time.time(), 0.0, 0.0, 0, time.time()
        self.live = animating()
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
        flow = int(time.time() * 6 * speed_k()) if ST.g("bar_flow") and self.live else 0
        if self.total is None:
            pos = int((time.time() * 8) % (w * 2 - 2))
            pos = pos if pos < w else 2 * w - 2 - pos
            return "".join(c(U("█", "#"), p[pp(i + flow, len(p))]) if abs(i - pos) < 3 else dim(U("░", "-")) for i in range(w))
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
                out.append(c(ch, p[pp(int(i / max(1, w - 1) * (len(p) - 1)) + flow, len(p))]))
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
    # for x in track(items, "…"): — итерация с прогресс-баром
    it = list(it)
    b = Bar(len(it), label)
    for i, x in enumerate(it, 1):
        yield x
        b.update(i)
    b.close()


# ==========================================================================
#  ВВОД И МЕНЮ: q / Ctrl+C = шаг назад (не выход из программы)
# ==========================================================================
class Quit(Exception):
    pass


class Interrupt(Quit):
    pass


class EOFQuit(Quit):
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
    # запрос строки; Ctrl+C → Interrupt; 'q' → Quit (если quit_ok); Enter → default
    d = (" " + dim("[%s]" % default)) if default not in ("", None) else ""
    prompt = "%s %s%s%s%s " % (c(U("❯", ">"), accent(), True), label, (" " + dim(hint)) if hint and ST.g("hints") else "", d, c(":", accent()))
    try:
        sys.stdout.flush()
        v = clean_line(input(_rl(prompt)))
    except EOFError:
        raise EOFQuit()
    except KeyboardInterrupt:
        print()
        raise Interrupt()
    if quit_ok and v.lower() in ("q", "quit", "exit"):
        raise Quit()
    return v if v != "" else (default if default is not None else "")


UNATT = [False]


def confirm(q, default=False):
    if UNATT[0]:
        return default
    return ask("%s %s" % (q, dim("(y/n, Enter = %s)" % ("y" if default else "n"))), "y" if default else "n", quit_ok=False).lower() in ("y", "yes", "д", "да", "1")


def pause(msg=None):
    try:
        input(_rl(dim(msg or L("Enter — продолжить...", "Press Enter..."))) + " ")
    except (EOFError, KeyboardInterrupt):
        print()


def parse_multi(text, n):
    # '1,3-5' / 'all' → список номеров 1..n
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
        v = ask(label, default, hint=L("1,3-5 / all / b — назад", "1,3-5 / all / b = back"))
        if v.lower() in ("b", "back"):
            return None
        try:
            return parse_multi(v, n)
        except ValueError:
            print("[!] " + L("Неверный ввод. Пример: 1,3-5 или all", "Bad input. Example: 1,3-5 or all"))


HOTKEYS = {"t": "theme", "a": "anim", "s": "spinner", "y": "bar_style"}


def apply_hotkey(k):
    # быстрые клавиши в главном меню: t — тема, a — анимации, s — спиннер, y — стиль бара
    key = HOTKEYS[k]
    if key == "anim":
        ST.set("anim", not ST.g("anim"))
    else:
        opts = list(SCH[key][4])
        cur = ST.g(key)
        ST.set(key, opts[(opts.index(cur) + 1) % len(opts)] if cur in opts else opts[0])


def menu(title, items, sub=None, back=None, show=True, top=False, hotkeys=False):
    # цветное меню: items [(ключ, название, пояснение)]; 'q' или Ctrl+C — шаг назад (в top — подсказка, а не выход)
    if show:
        clear_screen()
        hdr(title, sub)
    for k, lab, desc in items:
        if k == "--":
            print("\n " + c(U("━━ ", "-- ") + lab + " " + U("━" * max(2, term_w() - vlen(lab) - 8), "-" * 6), accent(), True))
            continue
        row = " %s %s %s" % (c("%2s" % k, accent(), True), c(U("┃", "|"), pal()[0]), bold(lab))
        if desc and ST.g("hints"):
            row += "  " + dim(trunc(desc, max(8, term_w() - vlen(lab) - 9)))
        print(row)
    print(" %s %s %s" % (c(" q", ERR_C, True), c(U("┃", "|"), pal()[0]), dim(back or L("Назад", "Back"))))
    if hotkeys:
        print(dim(L(" t тема · a анимации · s спиннер · y стиль бара", " t theme · a anim · s spinner · y bar style")))
    keys = [str(k).lower() for k, _, _ in items if k != "--"]
    eofs = 0
    while True:
        try:
            v = ask(L("Выбор", "Choice") + (dim(L(" (q — выход)", " (q = quit)")) if top else ""), "", quit_ok=False).lower()
        except Interrupt:
            if top:
                print("[*] " + L("Ctrl+C: для выхода введите q", "Ctrl+C: type q to quit"))
                continue
            return "q"
        except Quit:
            eofs += 1
            if not top or eofs >= 2:
                return "q"
            continue
        if v in ("q", "quit", "exit", "b", "back"):
            return "q"
        if hotkeys and v in HOTKEYS:
            apply_hotkey(v)
            return "__refresh"
        if v in keys:
            return v
        print("[!] " + L("Неверный выбор — введите номер из списка", "Invalid choice — enter a number from the list"))


def resilient(fn):
    # обёртка меню-функции: Ctrl+C/q внутри действия возвращает в меню этой функции, а не выходит
    def w(*a, **k):
        quick = 0
        while True:
            t0 = time.time()
            try:
                return fn(*a, **k)
            except (Quit, KeyboardInterrupt):
                print("\n[*] " + L("↩ Назад в меню", "↩ Back to the menu"))
                quick = quick + 1 if time.time() - t0 < 0.5 else 0
                if quick >= 3:
                    return None
    w.__name__ = getattr(fn, "__name__", "w")
    return w


def pick_one(title, options, current=None, labels=None):
    # выбор одного варианта из списка (labels — подписи)
    print("\n" + c(title, accent(), True))
    for i, o in enumerate(options, 1):
        lab = labels[i - 1] if labels else (o if o != "" else dim(L("(пусто)", "(empty)")))
        print("  %s %s%s" % (c("%2d" % i, accent(), True), lab, c(" ◄", OK_C) if o == current else ""))
    v = ask(L("Номер (Enter — оставить)", "Number (Enter = keep)"), "", quit_ok=False)
    return options[int(v) - 1] if v.isdigit() and 1 <= int(v) <= len(options) else None


# ==========================================================================
#  АУДИТ, VAULT (шифрование cookies), СОСТОЯНИЕ
# ==========================================================================
AUDIT = CONF / "audit.log"


def audit(action, details=""):
    # запись в журнал аудита: время | пользователь | действие | детали | sha256(предыдущая строка)
    if not ST.g("audit"):
        return
    try:
        CONF.mkdir(parents=True, exist_ok=True)
        prev = b""
        if AUDIT.exists():
            with open(str(AUDIT), "rb") as f:
                f.seek(0, 2)
                sz = f.tell()
                f.seek(max(0, sz - 4096))
                ls = f.read().splitlines(True)
            prev = ls[-1] if ls else b""
        line = "%s | %s | %s | %s | %s\n" % (time.strftime("%Y-%m-%d %H:%M:%S"), os.environ.get("USER", "user"), action, redact(str(details))[:200].replace("\n", " "), hashlib.sha256(prev).hexdigest())
        with open(str(AUDIT), "a", encoding="utf-8") as f:
            f.write(line)
        if AUDIT.stat().st_size > 1048576:
            os.replace(str(AUDIT), str(AUDIT) + ".1")
        old = Path(str(AUDIT) + ".1")
        if old.exists() and old.stat().st_size > 10 * 1048576:
            old.unlink()
    except Exception:
        pass


def audit_verify():
    # проверка цепочки хэшей журнала аудита → (ok, число строк, номер первой битой)
    try:
        prev, n = b"", 0
        with open(str(AUDIT), "rb") as f:
            for raw in f:
                n += 1
                parts = raw.decode("utf-8", "replace").rstrip("\n").rsplit(" | ", 1)
                if len(parts) != 2 or parts[1] != hashlib.sha256(prev).hexdigest():
                    if n > 1 or prev:
                        return False, n, n
                prev = raw
        return True, n, 0
    except Exception:
        return True, 0, 0


def _hk(master, label):
    import hmac
    return hmac.new(master, label, hashlib.sha256).digest()


def _ks_xor(data, key, nonce):
    # потоковое шифрование BLAKE2b (как в Toolkit Vault, формат TKV1)
    out, ctr, pos = bytearray(len(data)), 0, 0
    while pos < len(data):
        chunk = data[pos:pos + 65536]
        cnt = (len(chunk) + 63) // 64
        ks = b"".join(hashlib.blake2b(nonce + struct.pack(">Q", ctr + i), key=key, digest_size=64).digest() for i in range(cnt))
        ctr += cnt
        n = len(chunk)
        out[pos:pos + n] = (int.from_bytes(chunk, "big") ^ int.from_bytes(ks[:n], "big")).to_bytes(n, "big")
        pos += n
    return bytes(out)


VAULT_KEY = CONF / "vault.key"


def vault_key():
    # 32-байтный ключ (chmod 600); создаётся при первом использовании
    try:
        return base64.b64decode(VAULT_KEY.read_text().strip())
    except Exception:
        k = os.urandom(32)
        CONF.mkdir(parents=True, exist_ok=True)
        VAULT_KEY.write_text(base64.b64encode(k).decode())
        os.chmod(str(VAULT_KEY), 0o600)
        audit("vault-key", "created")
        return k


def v_encrypt(data):
    import hmac
    salt, nonce = os.urandom(16), os.urandom(16)
    master = vault_key()
    ek, mk = _hk(master, b"enc"), _hk(master, b"mac")
    head = b"TKV1" + bytes([0]) + salt + nonce
    ct = _ks_xor(data, ek, nonce)
    return head + ct + hmac.new(mk, head + ct, hashlib.sha256).digest()


def v_decrypt(blob):
    import hmac
    if blob[:4] != b"TKV1" or len(blob) < 69:
        raise ValueError("not a vault file")
    nonce = blob[21:37]
    master = vault_key()
    ek, mk = _hk(master, b"enc"), _hk(master, b"mac")
    if not hmac.compare_digest(blob[-32:], hmac.new(mk, blob[:-32], hashlib.sha256).digest()):
        raise ValueError("bad key or damaged file")
    return _ks_xor(blob[37:-32], ek, nonce)


# ---------- cookies ----------
_TMP_CK = []


@atexit.register
def _wipe_tmp_cookies():
    for p in _TMP_CK:
        try:
            os.unlink(p)
        except OSError:
            pass


def cookie_candidates(host):
    h = host.lower().split(":")[0]
    parts = h.split(".")
    return [BASE / "cookies" / (".".join(parts[i:]) + ".txt") for i in range(len(parts) - 1)]


def cookies_for(host):
    # путь к Netscape-файлу cookies для домена (зашифрованный .tkv расшифровывается во временный файл)
    f = ST.g("cookies_file")
    if f and Path(f).expanduser().exists():
        return str(Path(f).expanduser())
    for p in cookie_candidates(host):
        if p.exists():
            return str(p)
        enc = Path(str(p) + ".tkv")
        if enc.exists():
            try:
                data = v_decrypt(enc.read_bytes())
                t = BASE / "tmp" / (".ck_%s.txt" % hashlib.sha1(str(p).encode()).hexdigest()[:8])
                t.parent.mkdir(parents=True, exist_ok=True)
                fd = os.open(str(t), os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
                with os.fdopen(fd, "wb") as fh:
                    fh.write(data)
                _TMP_CK.append(str(t))
                return str(t)
            except Exception as e:
                dlog("cookies decrypt failed: %s" % e, "WARN")
    return None


def cookie_jar_entries(host):
    # записи cookies, подходящие хосту: [(name, value)]
    path = cookies_for(host)
    out = []
    if not path:
        return out
    h = host.lower().split(":")[0]
    try:
        for ln in Path(path).read_text("utf-8", "replace").splitlines():
            if ln.startswith("#HttpOnly_"):
                ln = ln[len("#HttpOnly_"):]
            if not ln.strip() or ln.startswith("#"):
                continue
            p = ln.split("\t")
            if len(p) >= 7:
                dom = p[0].lstrip(".").lower()
                if h == dom or h.endswith("." + dom):
                    out.append((p[5], p[6]))
    except Exception:
        pass
    return out


def cookie_header(host):
    return "; ".join("%s=%s" % kv for kv in cookie_jar_entries(host))


def cookie_value(host, name):
    for k, v in cookie_jar_entries(host):
        if k == name:
            return v
    return ""


def cookies_save(domain, header_or_text):
    # сохранить cookies: строка 'a=b; c=d' или готовый Netscape-текст → cookies/<domain>.txt (или .tkv)
    txt = header_or_text.strip()
    if "\t" in txt and txt.count("\t") >= 6:
        net = txt if txt.startswith("#") else "# Netscape HTTP Cookie File\n" + txt
    else:
        exp = int(time.time()) + 365 * 86400
        lines = ["# Netscape HTTP Cookie File"]
        for part in re.split(r";\s*", re.sub(r"(?i)^cookie:\s*", "", txt)):
            if "=" in part:
                k, v = part.split("=", 1)
                lines.append("\t".join([".%s" % domain, "TRUE", "/", "TRUE", str(exp), k.strip(), v.strip()]))
        net = "\n".join(lines)
    d = BASE / "cookies"
    d.mkdir(parents=True, exist_ok=True)
    p = d / (domain + ".txt")
    if ST.g("encrypt_cookies"):
        Path(str(p) + ".tkv").write_bytes(v_encrypt(net.encode("utf-8")))
        os.chmod(str(p) + ".tkv", 0o600)
        if p.exists():
            p.unlink()
    else:
        p.write_text(net + "\n", "utf-8")
        os.chmod(str(p), 0o600)
    audit("cookies-save", domain)
    return p


# ---------- JSON-состояние ----------
def jload(p, default):
    try:
        return json.loads(Path(p).read_text("utf-8"))
    except Exception:
        return default


def jsave(p, data):
    try:
        t = Path(p).with_suffix(Path(p).suffix + ".tmp")
        t.write_text(json.dumps(data, ensure_ascii=False, indent=1), "utf-8")
        os.replace(str(t), str(p))
    except Exception:
        pass


HIST, QUEUE, HASHES, STATS, SCHED = CONF / "history.json", CONF / "queue.json", CONF / "hashes.json", CONF / "stats.json", CONF / "schedule.json"


def hist_done(url):
    e = jload(HIST, {}).get(url)
    return bool(e and e.get("status") == "ok" and e.get("path") and Path(e["path"].split(" (")[0]).exists())


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


def ensure_dirs():
    for d in DIRS:
        (BASE / d).mkdir(parents=True, exist_ok=True)
    CONF.mkdir(parents=True, exist_ok=True)


def outdir(kind):
    root = Path(ST.g("out_dir")).expanduser() if ST.g("out_dir") else BASE
    d = root / {"video": "videos", "audio": "audio", "photo": "photos", "text": "texts", "file": "files"}.get(kind, "videos")
    d.mkdir(parents=True, exist_ok=True)
    return d


def free_mb():
    try:
        return shutil.disk_usage(str(BASE)).free // 1048576
    except Exception:
        return 10 ** 9


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
    # выбор файлов из папки: 1,3-5 / all / b
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
            print("  %s %s  %s" % (c("%2d" % i, accent(), True), trunc(os.fsencode(f.name).decode("utf-8", "replace"), term_w() - 28), dim(inf)))
        v = ask(L("Номера", "Numbers") if multi else L("Номер", "Number"), "", hint=L("1,3-5 / all / b — назад", "1,3-5 / all / b = back"))
        if v.lower() in ("b", "back", ""):
            return None
        try:
            nums = parse_multi(v, len(fs))
        except ValueError:
            continue
        return [fs[i - 1] for i in (nums if multi else nums[:1])]


def rm_tree(p):
    # надёжное удаление (с исправлением прав)
    p = str(p)
    try:
        if os.path.islink(p) or os.path.isfile(p):
            os.unlink(p)
        else:
            shutil.rmtree(p)
        audit("delete", p)
        return True
    except Exception:
        pass
    try:
        subprocess.run(["chmod", "-R", "u+rwx", p], timeout=60)
        subprocess.run(["rm", "-rf", "--", p], timeout=300)
        audit("delete", p)
        return not os.path.lexists(p)
    except Exception:
        return False


# ==========================================================================
#  СЕТЬ: DNS (system → DoH → UDP), TLS, прокси (LAN/auth), MITM, пинг, HTTP с запасными способами
# ==========================================================================
_orig_gai = socket.getaddrinfo
_tl = threading.local()
DNS_CACHE = {}
INSECURE = set()
DOH_DEFAULT = ["https://1.1.1.1/dns-query", "https://8.8.8.8/dns-query", "https://dns.google/dns-query", "https://cloudflare-dns.com/dns-query", "https://9.9.9.9/dns-query"]
UDP_DEFAULT = ["1.1.1.1", "8.8.8.8", "77.88.8.8", "9.9.9.9"]
LAST_ERRS = collections.deque(maxlen=20)


def is_ip(h):
    for fam in (socket.AF_INET, socket.AF_INET6):
        try:
            socket.inet_pton(fam, h)
            return True
        except (OSError, ValueError):
            pass
    return False


def is_local_host(h):
    h = (h or "").lower()
    return h in ("localhost", "") or h.startswith(("127.", "192.168.", "10.")) or h.endswith((".local", ".lan")) or is_ip(h) and h.startswith("172.")


def _qtypes():
    return {"ipv4": ("A",), "ipv6": ("AAAA",)}.get(ST.g("ip_version"), ("A", "AAAA"))


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
    # DNS по UDP/53 → список IP
    try:
        tid, pkt = build_query(host, qt)
        s = socket.socket(socket.AF_INET6 if ":" in server else socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(timeout)
        try:
            s.sendto(pkt, (server, 53))
            data, _ = s.recvfrom(4096)
            return parse_response(data, tid, qt)
        finally:
            s.close()
    except Exception:
        return []


def doh_one(url, host, qtype):
    # DNS-over-HTTPS (JSON API), без прокси
    op = urllib.request.build_opener(urllib.request.ProxyHandler({}), urllib.request.HTTPSHandler(context=ssl.create_default_context()))
    req = urllib.request.Request("%s?name=%s&type=%s" % (url, host, qtype), headers={"accept": "application/dns-json", "user-agent": UA_DESK})
    with op.open(req, timeout=8) as r:
        d = json.loads(r.read().decode("utf-8", "replace"))
    return [a["data"] for a in d.get("Answer", []) if a.get("type") in (1, 28)]


def doh_resolve(host):
    urls = list(dict.fromkeys([ST.g("doh_url")] + DOH_DEFAULT))
    for u in urls:
        ips = []
        for qt in _qtypes():
            try:
                ips += doh_one(u, host, qt)
            except Exception:
                pass
        if ips:
            return list(dict.fromkeys(ips))
    return []


def udp_resolve(host):
    servers = [s.strip() for s in ST.g("dns_servers").split(",") if s.strip()] + UDP_DEFAULT
    for s in dict.fromkeys(servers):
        ips = []
        for qt in _qtypes():
            ips += udp_query(s, host, 1 if qt == "A" else 28)
        if ips:
            return list(dict.fromkeys(ips))
    return []


def patched_gai(host, port, family=0, type=0, proto=0, flags=0):
    # getaddrinfo с цепочкой DNS: system → DoH (5 серверов) → UDP (несколько серверов); кэш 2 мин
    mode = ST.g("dns_mode")
    if (not isinstance(host, str) or not host or host == "localhost" or is_ip(host) or getattr(_tl, "busy", False)
            or (mode == "system" and ST.g("ip_version") == "auto")):
        return _orig_gai(host, port, family, type, proto, flags)
    fam = {"ipv4": socket.AF_INET, "ipv6": socket.AF_INET6}.get(ST.g("ip_version"), family)
    order = {"auto": ("system", "doh", "udp"), "system": ("system",), "doh": ("doh", "udp", "system"), "udp": ("udp", "doh", "system")}[mode]
    v = DNS_CACHE.get(host)
    ips = v[0] if v and time.time() - v[1] < 120 else None
    if not ips:
        for m in order:
            if m == "system":
                try:
                    r = _orig_gai(host, port, fam, type, proto, flags)
                    if r:
                        return r
                except OSError:
                    pass
                continue
            _tl.busy = True
            try:
                ips = doh_resolve(host) if m == "doh" else udp_resolve(host)
            finally:
                _tl.busy = False
            if ips:
                dlog("dns %s via %s -> %s" % (host, m, ips[:2]))
                DNS_CACHE[host] = (ips, time.time())
                break
    if not ips:
        raise socket.gaierror(socket.EAI_NONAME, "Name does not resolve")
    p = int(port) if port and str(port).isdigit() else 0
    return [(socket.AF_INET6 if ":" in ip else socket.AF_INET, type or socket.SOCK_STREAM, proto or 0, "", (ip, p)) for ip in ips]


socket.getaddrinfo = patched_gai


# ---------- TLS ----------
def make_ctx(verify=True):
    # SSL-контекст: TLS ≥1.2, без слабых шифров, доп. CA из настроек
    ctx = ssl.create_default_context() if verify else ssl._create_unverified_context()
    try:
        ctx.minimum_version = ssl.TLSVersion.TLSv1_2
    except Exception:
        pass
    try:
        ctx.set_ciphers("DEFAULT:!RC4:!3DES:!MD5:!aNULL:!eNULL")
    except Exception:
        pass
    ca = ST.g("extra_ca")
    if verify and ca and os.path.exists(os.path.expanduser(ca)):
        try:
            ctx.load_verify_locations(cafile=os.path.expanduser(ca))
        except Exception:
            pass
    return ctx


def _der(buf, pos):
    tag = buf[pos]
    ln = buf[pos + 1]
    pos += 2
    if ln & 0x80:
        nb = ln & 0x7F
        ln = int.from_bytes(buf[pos:pos + nb], "big")
        pos += nb
    return tag, pos, pos + ln


def _der_strings(buf, s, e, out):
    while s < e:
        t, cs, ce = _der(buf, s)
        if t in (0x30, 0x31):
            _der_strings(buf, cs, ce, out)
        elif t in (0x0C, 0x13, 0x14, 0x16):
            out.append(buf[cs:ce].decode("utf-8", "replace"))
        s = ce


def der_issuer(der):
    # издатель сертификата из DER (мини-парсер ASN.1)
    try:
        t, s, e = _der(der, 0)
        t, s, e = _der(der, s)
        pos = s
        t, cs, ce = _der(der, pos)
        if t == 0xA0:
            pos = ce
            t, cs, ce = _der(der, pos)
        pos = ce
        t, cs, ce = _der(der, pos)
        pos = ce
        t, cs, ce = _der(der, pos)
        pos = ce
        t, cs, ce = _der(der, pos)
        out = []
        _der_strings(der, cs, ce, out)
        return " ".join(out)
    except Exception:
        return ""


def tls_der(host, port=443, timeout=6):
    # DER-сертификат сервера (без проверки цепочки)
    s = socket.create_connection((host, port), timeout)
    try:
        ss = ssl._create_unverified_context().wrap_socket(s, server_hostname=host)
        return ss.getpeercert(True)
    finally:
        s.close()


_MITM_CACHE = {}
MITM_MARKERS = ("shadowrocket", "surge", "quantumult", "stash", "loon", "mitmproxy", "charles", "fiddler", "clash", "proxy", "sing-box", "v2ray")


def detect_mitm(host="www.google.com"):
    # (mitm?, издатель, проверка пройдена?) — результат кэшируется на 10 минут
    v = _MITM_CACHE.get(host)
    if v and time.time() - v[0] < 600:
        return v[1]
    res = (False, "", None)
    try:
        s = socket.create_connection((host, 443), 6)
        try:
            make_ctx(True).wrap_socket(s, server_hostname=host).close()
            res = (False, "", True)
        finally:
            s.close()
    except ssl.SSLCertVerificationError:
        iss = ""
        try:
            iss = der_issuer(tls_der(host))
        except Exception:
            pass
        res = (True, iss or "unknown", False)
    except Exception:
        pass
    _MITM_CACHE[host] = (time.time(), res)
    return res


def check_mitm_state():
    # предупреждение о MITM при старте (если CA не доверен в iSH)
    mitm, iss, ok = detect_mitm()
    if mitm:
        low = iss.lower()
        known = any(m in low for m in MITM_MARKERS)
        print("[!] " + L("Обнаружена подмена TLS-сертификата (издатель: %s)%s." % (iss, " — похоже на HTTPS-расшифровку прокси-клиента" if known else ""),
                         "TLS certificate substitution detected (issuer: %s)%s." % (iss, " — looks like proxy-client HTTPS decryption" if known else "")))
        print(dim("    " + L("iSH не видит CA из iOS. Экспортируйте CA клиента (.crt/.pem) в папку certs/ и добавьте: Сеть → CA-сертификат.",
                             "iSH cannot see iOS CAs. Export the client CA (.crt/.pem) into certs/ and add it: Network → CA certificate.")))
    return mitm


def tls_policy(host):
    # политика при ошибке сертификата (учитывает MITM-политику)
    if host in INSECURE:
        return True
    mitm, iss, _ = detect_mitm()
    pol = {"allow": "auto", "reject": "never", "ask": "ask"}[ST.g("mitm_policy")] if mitm else ST.g("tls_fallback")
    if pol == "auto" or (pol == "ask" and not UNATT[0] and confirm(L("Ошибка TLS-сертификата для %s%s. Продолжить БЕЗ проверки?" % (host, (" (MITM: %s)" % iss) if mitm else ""), "TLS certificate error for %s%s. Continue WITHOUT verification?" % (host, (" (MITM: %s)" % iss) if mitm else "")))):
        INSECURE.add(host)
        audit("tls-insecure", host)
        print("[!] " + L("Проверка TLS отключена для ", "TLS verification disabled for ") + host)
        return True
    return False


def check_pin(host):
    # проверка закреплённого SHA-256 сертификата (pins в настройках)
    want = ST.d.get("pins", {}).get(host)
    if not want:
        return True
    try:
        got = hashlib.sha256(tls_der(host)).hexdigest()
        return got == want.lower().replace(":", "")
    except Exception:
        return False


# ---------- прокси: LAN, шаблоны (по одному адресу), auth, тест, лучший ----------
_LIP = [0, None]


def local_ip():
    # локальный IP (ip addr → ifconfig → UDP-сокет), кэш 5 минут
    if time.time() - _LIP[0] < 300 and _LIP[1] is not None:
        return _LIP[1]
    ip = None
    for cmd in (["ip", "-4", "addr", "show"], ["ifconfig"]):
        if not shutil.which(cmd[0]):
            continue
        try:
            r = subprocess.run(cmd, timeout=3)
            for m in re.finditer(r"inet\s+(?:addr:)?(\d+\.\d+\.\d+\.\d+)", r.stdout.decode("utf-8", "replace")):
                if not m.group(1).startswith(("127.", "169.254.")):
                    ip = m.group(1)
                    break
        except Exception:
            pass
        if ip:
            break
    if not ip:
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.settimeout(2)
            s.connect(("1.1.1.1", 80))
            cand = s.getsockname()[0]
            s.close()
            if not cand.startswith("127."):
                ip = cand
        except Exception:
            pass
    _LIP[0], _LIP[1] = time.time(), ip
    return ip


# (схема, адрес, порт, RU, EN) — каждый шаблон = ОДИН прокси; несколько выбираются цифрами
def proxy_templates():
    return [
        ("http", "{LOOP}", "1082", "HTTP loopback (Shadowrocket)", "HTTP loopback (Shadowrocket)"), ("http", "{LOOP}", "8080", "HTTP loopback 8080", "HTTP loopback 8080"),
        ("http", "{LOOP}", "8081", "HTTP loopback 8081", "HTTP loopback 8081"), ("http", "{LOOP}", "3128", "HTTP loopback (Squid)", "HTTP loopback (Squid)"),
        ("socks5", "{LOOP}", "1080", "SOCKS5 loopback", "SOCKS5 loopback"), ("socks5h", "{LOOP}", "1080", "SOCKS5h loopback (DNS через прокси)", "SOCKS5h loopback (DNS via proxy)"),
        ("socks5", "{LOOP}", "10808", "SOCKS5 loopback (v2rayN)", "SOCKS5 loopback (v2rayN)"), ("socks5h", "{LOOP}", "9050", "SOCKS5h loopback (Tor)", "SOCKS5h loopback (Tor)"),
        ("http", "{LAN}", "1082", "HTTP LAN 1082 (общий доступ)", "HTTP LAN 1082 (allow LAN)"), ("http", "{LAN}", "8080", "HTTP LAN 8080", "HTTP LAN 8080"),
        ("socks5", "{LAN}", "1080", "SOCKS5 LAN 1080", "SOCKS5 LAN 1080"), ("socks5h", "{LAN}", "1080", "SOCKS5h LAN 1080", "SOCKS5h LAN 1080"),
        ("http", "", "", "Ввести вручную", "Enter manually"), ("", "", "", "Отключить прокси", "Disable proxy"),
    ]


def render_proxy_template(t, loop="127.0.0.1", lan=None):
    sch, addr, port = t[0], t[1], t[2]
    if not sch or not addr:
        return ""
    if "{LAN}" in addr and not lan:
        return None
    return "%s://%s:%s" % (sch, addr.replace("{LOOP}", loop).replace("{LAN}", lan or ""), port)


def build_proxy_url(scheme, host, port, user=None, pw=None):
    cred = ""
    if user and pw:
        cred = "%s:%s@" % (quote(user, safe=""), quote(pw, safe=""))
    elif user:
        cred = "%s@" % quote(user, safe="")
    return "%s://%s%s:%s" % (scheme, cred, host, port)


def parse_proxy_url(url):
    if not url:
        return None
    p = urlparse(url)
    try:
        port = p.port
    except ValueError:
        port = None
    return (p.scheme, p.hostname, port, unquote(p.username) if p.username else None, unquote(p.password) if p.password else None)


def test_proxy(url, timeout=3):
    # функциональная проверка прокси (HTTP CONNECT / SOCKS5 CONNECT) → (ok, мс, ошибка)
    pr = parse_proxy_url(url)
    if not pr or not pr[1] or not pr[2]:
        return False, 0, "bad url"
    scheme, host, port, user, pw = pr
    t0 = time.time()
    try:
        s = socket.create_connection((host, port), timeout)
    except socket.timeout:
        return False, timeout * 1000, "timeout"
    except ConnectionRefusedError:
        return False, 0, "refused"
    except Exception as e:
        return False, 0, str(e)[:40]
    ms = int((time.time() - t0) * 1000)
    try:
        s.settimeout(timeout)
        if scheme.startswith("socks"):
            s.sendall(b"\x05\x02\x00\x02" if user else b"\x05\x01\x00")
            r = s.recv(2)
            if len(r) < 2 or r[0] != 5 or r[1] == 0xFF:
                return False, ms, "socks refused"
            if r[1] == 2:
                u, p = (user or "").encode(), (pw or "").encode()
                s.sendall(b"\x01" + bytes([len(u)]) + u + bytes([len(p)]) + p)
                if s.recv(2)[1:2] != b"\x00":
                    return False, ms, "auth failed"
            s.sendall(b"\x05\x01\x00\x01" + socket.inet_aton("1.1.1.1") + struct.pack(">H", 443))
            r = s.recv(10)
            return (len(r) > 1 and r[1] == 0), ms, "" if (len(r) > 1 and r[1] == 0) else "connect failed"
        hdrs = "CONNECT 1.1.1.1:443 HTTP/1.1\r\nHost: 1.1.1.1:443\r\n"
        if user:
            hdrs += "Proxy-Authorization: Basic %s\r\n" % base64.b64encode(("%s:%s" % (user, pw or "")).encode()).decode()
        s.sendall((hdrs + "\r\n").encode())
        resp = s.recv(128)
        parts = resp.split(b" ")
        if len(parts) > 1 and parts[1].startswith(b"2"):
            return True, ms, ""
        return False, ms, "auth required" if b"407" in resp[:16] else "proxy refused"
    except socket.timeout:
        return False, ms, "timeout"
    except Exception as e:
        return False, ms, str(e)[:40]
    finally:
        s.close()


def proxy_chain():
    # кандидаты: текущий → loopback↔LAN подмена → шаблоны
    chain = []
    cur = ST.g("proxy")
    lip = local_ip()
    if cur:
        chain.append(cur)
        if lip and "127.0.0.1" in cur:
            chain.append(cur.replace("127.0.0.1", lip))
        if lip and lip in cur:
            chain.append(cur.replace(lip, "127.0.0.1"))
    for t in proxy_templates():
        u = render_proxy_template(t, "127.0.0.1", lip if ST.g("proxy_allow_lan") else None)
        if u and u not in chain:
            chain.append(u)
    return chain


def find_best_proxy():
    # параллельная проверка кандидатов → таблица → выбор лучшего
    from concurrent.futures import ThreadPoolExecutor
    cands = proxy_chain()
    res = []
    bar = Bar(len(cands), L("Проверка прокси", "Testing proxies"))
    with ThreadPoolExecutor(max_workers=3) as ex:
        for i, (u, r) in enumerate(zip(cands, ex.map(lambda u: test_proxy(u, 2), cands)), 1):
            res.append((u, r))
            bar.update(i)
    bar.close()
    good = sorted([x for x in res if x[1][0]], key=lambda x: x[1][1])
    table([[trunc(u, 34), c("OK", OK_C) if r[0] else c(r[2] or "fail", ERR_C), "%d ms" % r[1] if r[0] else "-"] for u, r in sorted(res, key=lambda x: (not x[1][0], x[1][1]))], [L("Прокси", "Proxy"), "", "ping"])
    if not good:
        print("[!] " + L("Рабочих прокси не найдено. Включите прокси-клиент (VPN) и «Allow LAN», если нужен LAN-адрес.", "No working proxies. Turn on the proxy client (VPN) and 'Allow LAN' if you need the LAN address."))
        return False
    if confirm(L("Использовать лучший: %s (%d мс)?" % (good[0][0], good[0][1][1]), "Use the best: %s (%d ms)?" % (good[0][0], good[0][1][1])), True):
        ST.set("proxy", good[0][0])
        audit("proxy", good[0][0])
        print("[+] " + L("Прокси сохранён", "Proxy saved"))
        return True
    return False


def set_proxy_ui():
    # выбор прокси: шаблоны (по одному адресу), LAN, логин/пароль, проверка перед сохранением
    lip = local_ip()
    allow_lan = ST.g("proxy_allow_lan")
    cur = ST.g("proxy")
    tpls = proxy_templates()
    print("\n" + c(L("Прокси", "Proxy"), accent(), True))
    print(dim("  " + (L("LAN IP: %s" % lip, "LAN IP: %s" % lip) if lip else L("LAN IP не определён — LAN-шаблоны скрыты", "LAN IP unknown — LAN templates hidden"))))
    shown = []
    for i, t in enumerate(tpls, 1):
        u = render_proxy_template(t, "127.0.0.1", lip if allow_lan else None)
        if u is None:
            continue
        shown.append(i)
        mark = c(" ◄", OK_C) if (u and u == cur) else ""
        addr = dim(u) if u else dim(L("(вручную)" if t[0] else "(выкл)", "(manual)" if t[0] else "(off)"))
        print("  %s %-40s %s%s" % (c("%2d" % i, accent(), True), L(t[3], t[4]), addr, mark))
    if not allow_lan:
        print(dim("  " + L("LAN-шаблоны скрыты: включите «proxy_allow_lan» в настройках сети.", "LAN templates hidden: enable 'proxy_allow_lan' in network settings.")))
    v = ask(L("Номер шаблона", "Template number"), "", quit_ok=False, hint=L("Enter — оставить, b — назад", "Enter = keep, b = back"))
    if not v or not v.isdigit() or int(v) not in shown:
        return False
    t = tpls[int(v) - 1]
    if not t[0]:
        ST.set("proxy", "")
        audit("proxy", "off")
        print("[+] " + L("Прокси отключён", "Proxy disabled"))
        return True
    if not t[1]:
        scheme = ask(L("Тип (http / socks5 / socks5h)", "Type (http / socks5 / socks5h)"), "http", quit_ok=False)
        host = ask(L("Адрес (IP или домен)", "Address (IP or domain)"), "127.0.0.1", quit_ok=False)
        port = ask(L("Порт", "Port"), "1082", quit_ok=False)
        u = build_proxy_url(scheme, host, port)
    else:
        u = render_proxy_template(t, "127.0.0.1", lip if allow_lan else None)
        if "{LAN}" in t[1]:
            print("[!] " + L("Убедитесь, что в прокси-клиенте включён «Allow LAN connections». Иначе LAN-адрес не ответит.", "Make sure 'Allow LAN connections' is on in the proxy client, otherwise the LAN address will not answer."))
            audit("proxy-lan", u)
    if confirm(L("Прокси требует логин/пароль?", "Does the proxy need login/password?"), False):
        user = ask(L("Логин", "Login"), ST.mem("proxy_user", ""), quit_ok=False)
        pw = ask(L("Пароль (хранится в settings.json, chmod 600)", "Password (kept in settings.json, chmod 600)"), "", quit_ok=False)
        ST.setmem("proxy_user", user)
        pr = parse_proxy_url(u)
        u = build_proxy_url(pr[0], pr[1], pr[2], user, pw)
    with Spin(L("Проверяю прокси", "Testing proxy"), quiet=True):
        ok, ms, err = test_proxy(u)
    if ok:
        print("[+] " + L("Прокси отвечает (%d мс)" % ms, "Proxy answers (%d ms)" % ms))
    else:
        print("[!] " + L("Прокси не отвечает: %s" % err, "Proxy does not answer: %s" % err))
        if not confirm(L("Сохранить всё равно?", "Save anyway?"), False):
            return False
    ST.set("proxy", u)
    try:
        os.chmod(str(SETTINGS_FILE), 0o600)
    except OSError:
        pass
    audit("proxy", redact(u))
    print("[+] " + L("Прокси сохранён", "Proxy saved"))
    return True


DNS_PICK = [("1.1.1.1", "Cloudflare"), ("1.0.0.1", "Cloudflare #2"), ("8.8.8.8", "Google"), ("8.8.4.4", "Google #2"), ("9.9.9.9", "Quad9"), ("77.88.8.8", "Yandex"),
            ("94.140.14.14", "AdGuard"), ("208.67.222.222", "OpenDNS"), ("76.76.2.0", "ControlD"), ("223.5.5.5", "AliDNS")]


def set_dns_ui():
    # режим DNS + UDP-серверы: один адрес на пункт, несколько выбираются цифрами (1,3 / all)
    print("\n" + c(L("DNS: режим и серверы", "DNS: mode and servers"), accent(), True))
    modes = list(SCH["dns_mode"][4])
    m = pick_one(L("Режим DNS", "DNS mode"), modes, ST.g("dns_mode"), ["%s — %s" % (x, {"auto": L("system → DoH → UDP", "system → DoH → UDP"), "system": L("только системный", "system only"), "doh": L("DoH → UDP → system", "DoH → UDP → system"), "udp": L("UDP → DoH → system", "UDP → DoH → system")}[x]) for x in modes])
    if m:
        ST.set("dns_mode", m)
    print("\n" + c(L("UDP-серверы (выберите один или несколько: 1,3 / all)", "UDP servers (pick one or more: 1,3 / all)"), accent(), True))
    cur = [x.strip() for x in ST.g("dns_servers").split(",") if x.strip()]
    for i, (ip, nm) in enumerate(DNS_PICK, 1):
        print("  %s %-16s %s%s" % (c("%2d" % i, accent(), True), ip, dim(nm), c(" ◄", OK_C) if ip in cur else ""))
    v = ask(L("Номера", "Numbers"), "", quit_ok=False, hint=L("Enter — оставить, 0 — свой адрес", "Enter = keep, 0 = custom"))
    if v == "0":
        ip = ask(L("IP DNS-сервера", "DNS server IP"), "", quit_ok=False)
        if is_ip(ip):
            ST.set("dns_servers", ip)
    elif v:
        try:
            ST.set("dns_servers", ",".join(DNS_PICK[i - 1][0] for i in parse_multi(v, len(DNS_PICK))))
        except ValueError:
            print("[!] " + L("Неверный ввод", "Bad input"))
            return False
    DNS_CACHE.clear()
    print("[+] DNS: %s / %s" % (ST.g("dns_mode"), ST.g("dns_servers")))
    return True


# ---------- функциональный пинг и проверка интернета ----------
PING_HOSTS = [("1.1.1.1", 443), ("8.8.8.8", 443), ("77.88.8.8", 443), ("9.9.9.9", 443), ("captive.apple.com", 443), ("one.one.one.one", 443)]
LAST_PING = {"ts": 0.0, "ok": False}


def ping_once(host, port, timeout=2):
    t0 = time.time()
    try:
        socket.create_connection((host, port), timeout).close()
        return True, int((time.time() - t0) * 1000)
    except Exception:
        return False, 0


def functional_ping(timeout=3, stop_after=1):
    # параллельный TCP-пинг, останавливается при первом успехе
    results, lock, stop = [], threading.Lock(), threading.Event()

    def worker(host, port):
        if stop.is_set():
            return
        ok, ms = ping_once(host, port, timeout)
        with lock:
            results.append((host, ok, ms))
            if sum(1 for _, o, _ in results if o) >= stop_after:
                stop.set()
    ths = [threading.Thread(target=worker, args=hp, daemon=True) for hp in PING_HOSTS]
    for t in ths:
        t.start()
    t0 = time.time()
    while time.time() - t0 < timeout + 0.5 and not stop.is_set() and any(t.is_alive() for t in ths):
        time.sleep(0.05)
    stop.set()
    return sum(1 for _, o, _ in results if o) >= stop_after, list(results)


def ensure_internet(reason="", force=False):
    # проверка интернета перед сетевой операцией (кэш ping_cache_sec); при отказе — меню починки
    if not ST.g("ping_enabled"):
        return True
    if not force and LAST_PING["ok"] and time.time() - LAST_PING["ts"] < ST.g("ping_cache_sec"):
        return True
    with Spin(L("Проверяю подключение к интернету", "Checking internet"), quiet=True):
        ok, det = functional_ping(ST.g("ping_timeout"), 1)
    LAST_PING["ts"], LAST_PING["ok"] = time.time(), ok
    if ok:
        if ST.g("verbose_ping"):
            g = [(h, ms) for h, o, ms in det if o]
            print("[+] " + L("Интернет есть: %s (%d мс)" % g[0], "Internet OK: %s (%d ms)" % g[0]))
        return True
    print("[!] " + L("Нет доступа к интернету%s" % ((" (%s)" % reason) if reason else ""), "No internet access%s" % ((" (%s)" % reason) if reason else "")))
    for host, o, ms in det:
        print("  %s %-20s %s" % (c("✓" if o else "✗", OK_C if o else ERR_C), host, dim("%d мс" % ms if o else "-")))
    if not UNATT[0] and sys.stdin.isatty():
        return _fix_internet_menu()
    return False


def _fix_internet_menu():
    while True:
        k = menu(L("Нет интернета. Что делать?", "No internet. What to do?"), [
            ("1", L("Повторить проверку", "Retry check"), ""), ("2", L("Сменить прокси", "Change proxy"), ST.g("proxy") or "-"), ("3", L("Выключить прокси", "Disable proxy"), ""),
            ("4", L("DNS: режим и серверы", "DNS: mode and servers"), ST.g("dns_mode")), ("5", L("Найти лучший прокси", "Find best proxy"), ""), ("6", L("Продолжить без проверки", "Continue without check"), ""),
            ("7", L("VPN: обход и диагностика", "VPN: bypass & diagnostics"), L("если включён VPN/прокси-клиент", "if a VPN/proxy client is on"))], back=L("Отмена", "Cancel"))
        if k in ("q", "6"):
            return k == "6"
        if k == "7":
            vpn_fallback_menu()
        if k == "1":
            ok, _ = functional_ping(5, 1)
            LAST_PING["ts"], LAST_PING["ok"] = time.time(), ok
            if ok:
                print("[+] " + L("Интернет появился", "Internet is back"))
                return True
            print("[!] " + L("Всё ещё нет интернета", "Still no internet"))
        elif k == "2":
            set_proxy_ui()
        elif k == "3":
            ST.set("proxy", "")
            print("[+] " + L("Прокси выключен", "Proxy disabled"))
        elif k == "4":
            set_dns_ui()
        elif k == "5":
            find_best_proxy()


# ---------- классификатор ошибок ----------
def classify_error(err, url=""):
    # причина сбоя → (категория, подсказка RU, подсказка EN)
    m = str(err).lower()
    if "no internet" in m or "network is unreachable" in m:
        return "no_internet", "Нет подключения к интернету", "No internet connection"
    if "name does not resolve" in m or "name or service not known" in m or "nodename nor servname" in m or "errno -3" in m or "temporary failure in name" in m:
        return "dns", "DNS не разрешает имя (сбой или DNS-блокировка) — поможет режим DoH", "DNS cannot resolve the name (failure or DNS block) — DoH mode may help"
    if "certificate" in m or "ssl" in m and "verify" in m:
        return "tls", "Ошибка TLS-сертификата (MITM без доверенного CA или pinning)", "TLS certificate error (MITM without trusted CA or pinning)"
    if "proxy" in m or "socks" in m or "407" in m:
        return "proxy", "Ошибка прокси (недоступен или неверный логин/пароль)", "Proxy error (unreachable or bad credentials)"
    if "connection reset" in m or "connection aborted" in m or "broken pipe" in m:
        return "reset", "Соединение сброшено (вероятно, DPI-блокировка) — смените прокси/DNS", "Connection reset (likely DPI block) — change proxy/DNS"
    if "timed out" in m or "timeout" in m:
        return "timeout", "Таймаут: сервер не отвечает или блокировка", "Timeout: server not answering or blocked"
    if "refused" in m:
        return "refused", "Соединение отклонено", "Connection refused"
    if "429" in m or "too many requests" in m or "rate" in m and "limit" in m:
        return "rate", "HTTP 429: лимит запросов — подождите и повторите", "HTTP 429: rate limited — wait and retry"
    if "401" in m or "403" in m or "forbidden" in m or "login" in m or "sign in" in m or "cookies" in m or "login_required" in m:
        return "auth", "Нужен вход/cookies или доступ запрещён (HTTP 401/403)", "Login/cookies needed or access denied (HTTP 401/403)"
    if "404" in m or "not found" in m or "410" in m or "removed" in m or "unavailable" in m:
        return "gone", "Ресурс удалён, приватный или неверная ссылка (404/410)", "Resource removed, private or wrong link (404/410)"
    if re.search(r"\b5\d\d\b", m):
        return "server", "Ошибка на стороне сервера (5xx) — повторите позже", "Server-side error (5xx) — retry later"
    return "unknown", "Неизвестная ошибка (см. подробности: debug.log)", "Unknown error (see details: debug.log)"


def note_error(url, err):
    cat, ru, en = classify_error(err, url)
    LAST_ERRS.append((time.strftime("%H:%M:%S"), url, cat, str(err)[:160]))
    dlog("error[%s] %s :: %s" % (cat, url, err), "WARN")
    return cat


def show_last_errors():
    # последние ошибки с классификацией
    if not LAST_ERRS:
        print("[+] " + L("Ошибок нет", "No errors"))
        return
    for ts, url, cat, msg in list(LAST_ERRS)[-8:]:
        cat2, ru, en = classify_error(msg, url)
        print("  %s %s %s" % (dim(ts), c(cat, WARN_C, True), trunc(url, 40)))
        print("      %s" % dim(trunc(L(ru, en) + " | " + msg, term_w() - 8)))


# ---------- HTTP: urllib → curl → wget → busybox wget → openssl ----------
class HttpErr(IOError):
    def __init__(self, code, msg=""):
        IOError.__init__(self, "HTTP %s %s" % (code, msg))
        self.code = code


def proxy_url():
    # текущий прокси: временное переопределение → настройка → случайный из пула
    if "proxy" in ST.ov:
        return (ST.ov["proxy"] or "").strip()
    p = ST.g("proxy").strip()
    if p:
        return p
    pool = [x.strip() for x in ST.g("proxy_pool").split(",") if x.strip()]
    return random.choice(pool) if pool else ""


def opener(verify=True):
    p = proxy_url()
    hs = [urllib.request.ProxyHandler({"http": p, "https": p} if p and not p.lower().startswith("socks") else {})]
    hs.append(urllib.request.HTTPSHandler(context=make_ctx(verify)))
    return urllib.request.build_opener(*hs)


UA_POOL = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36 Edg/126.0.0.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:126.0) Gecko/20100101 Firefox/126.0",
    "Mozilla/5.0 (X11; Linux x86_64; rv:125.0) Gecko/20100101 Firefox/125.0",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (Linux; Android 14; Pixel 8) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Mobile Safari/537.36"]


def ua():
    m = ST.g("ua")
    return random.choice(UA_POOL) if m == "random" else (UA_IOS if m == "ios" else UA_DESK)


def rand_headers():
    # антибот: небольшая вариация заголовков, как у обычных браузеров
    if not ST.g("antibot"):
        return {}
    h = {"Accept-Language": random.choice(["en-US,en;q=0.9", "en-US,en;q=0.8,ru;q=0.6", "ru-RU,ru;q=0.9,en;q=0.7", "en-GB,en;q=0.9"]), "Upgrade-Insecure-Requests": "1"}
    if random.random() < 0.5:
        h["DNT"] = "1"
    return h


_RATE = collections.defaultdict(collections.deque)


def rate_wait(host):
    # лимит запросов на домен в минуту (по памяти процесса)
    lim = ST.g("rate_per_min")
    if not lim or is_local_host(host):
        return
    if ST.g("antibot_delay"):
        time.sleep(random.uniform(1, 3))
    dq = _RATE[host]
    now = time.time()
    while dq and now - dq[0] > 60:
        dq.popleft()
    if len(dq) >= lim:
        wait = max(0.0, 60 - (now - dq[0]))
        if wait > 0:
            with Spin(L("Лимит запросов к %s — пауза" % host, "Rate limit for %s — pausing" % host), quiet=True):
                time.sleep(min(wait, 20))
    dq.append(time.time())


def _cli_get(tool, url, hd, timeout, body, verify):
    # запасные клиенты: curl / wget / busybox wget / openssl s_client → (bytes, url)
    p = proxy_url()
    if tool == "curl":
        if not shutil.which("curl"):
            raise FileNotFoundError("curl")
        cmd = ["curl", "-sSL", "--fail", "--connect-timeout", str(timeout), "--max-time", str(timeout * 4), "-w", "\n__URL__%{url_effective}"]
        if p:
            cmd += ["-x", p]
        if not verify:
            cmd.append("-k")
        elif ST.g("extra_ca") and os.path.exists(os.path.expanduser(ST.g("extra_ca"))):
            cmd += ["--cacert", os.path.expanduser(ST.g("extra_ca"))]
        if ST.g("ip_version") != "auto":
            cmd.append("-4" if ST.g("ip_version") == "ipv4" else "-6")
        for k, v in hd.items():
            cmd += ["-H", "%s: %s" % (k, v)]
        kw = {}
        if body is not None:
            cmd += ["--data-binary", "@-"]
            kw["input"] = body
        r = subprocess.run(cmd + [url], timeout=timeout * 5, **kw)
        if r.returncode != 0:
            raise IOError((r.stderr or b"").decode("utf-8", "replace").strip()[-200:] or "curl exit %d" % r.returncode)
        data, _, fu = r.stdout.rpartition(b"\n__URL__")
        return data, fu.decode("utf-8", "replace") or url
    if tool in ("wget", "busybox"):
        exe = shutil.which("wget") if tool == "wget" else shutil.which("busybox")
        if not exe:
            raise FileNotFoundError(tool)
        cmd = ([exe] if tool == "wget" else [exe, "wget"]) + ["-q", "-O", "-", "-T", str(timeout), "-U", hd.get("User-Agent", ua())]
        if not verify and tool == "wget":
            cmd.append("--no-check-certificate")
        for k, v in hd.items():
            if k.lower() != "user-agent":
                cmd += ["--header", "%s: %s" % (k, v)]
        if body is not None:
            cmd += ["--post-data", body.decode("latin-1")]
        env = dict(os.environ)
        if p:
            env["http_proxy"] = env["https_proxy"] = p
        r = subprocess.run(cmd + [url], timeout=timeout * 5, env=env)
        if r.returncode != 0:
            raise IOError((r.stderr or b"").decode("utf-8", "replace").strip()[-200:] or "%s exit %d" % (tool, r.returncode))
        return r.stdout, url
    if tool == "openssl":
        ox = shutil.which("openssl")
        u = urlparse(url)
        if not ox or u.scheme != "https" or p:
            raise FileNotFoundError("openssl")
        path = (u.path or "/") + (("?" + u.query) if u.query else "")
        lines = ["%s %s HTTP/1.0" % ("POST" if body is not None else "GET", path), "Host: %s" % u.netloc, "Connection: close"]
        lines += ["%s: %s" % (k, v) for k, v in hd.items() if k.lower() not in ("host", "accept-encoding")]
        if body is not None:
            lines.append("Content-Length: %d" % len(body))
        req = ("\r\n".join(lines) + "\r\n\r\n").encode() + (body or b"")
        r = subprocess.run([ox, "s_client", "-quiet", "-connect", "%s:%d" % (u.hostname, u.port or 443), "-servername", u.hostname], input=req, timeout=timeout * 4)
        head, _, rest = r.stdout.partition(b"\r\n\r\n")
        m = re.match(rb"HTTP/\d\.\d (\d+)", head)
        if not m:
            raise IOError("openssl: no HTTP response")
        code = int(m.group(1))
        if code in (301, 302, 303, 307, 308):
            loc = re.search(rb"(?i)\r\nlocation:\s*(\S+)", head)
            if loc:
                return _cli_get("openssl", urljoin(url, loc.group(1).decode()), hd, timeout, None, verify)
        if code >= 400:
            raise HttpErr(code)
        return rest, url
    raise FileNotFoundError(tool)


def _urllib_get(url, hd, timeout, body, verify):
    req = urllib.request.Request(url, headers=hd, data=body)
    with opener(verify).open(req, timeout=timeout) as r:
        return r.read(), r.geturl()


def _get_one(url, hd, timeout, retries, body):
    host = urlparse(url).hostname or ""
    rate_wait(host)
    if host in ST.d.get("pins", {}) and not check_pin(host):
        raise IOError("certificate pin mismatch for %s" % host)
    socks = proxy_url().lower().startswith("socks")
    methods = (["curl"] if socks else ["urllib", "curl"]) + ["wget", "busybox", "openssl"]
    last = first = None
    for att in range(retries + 1):
        retry_tls = False
        for m in methods:
            try:
                if m == "urllib":
                    return _urllib_get(url, hd, timeout, body, host not in INSECURE)
                return _cli_get(m, url, hd, timeout, body, host not in INSECURE)
            except FileNotFoundError:
                continue
            except urllib.error.HTTPError as e:
                if e.code in (401, 403, 404, 410, 451):
                    raise HttpErr(e.code, e.reason)
                last = HttpErr(e.code, e.reason)
            except HttpErr as e:
                if e.code in (401, 403, 404, 410, 451):
                    raise
                last = e
            except Exception as e:
                last = e
                if "CERTIFICATE" in str(e).upper() and host not in INSECURE:
                    if tls_policy(host):
                        retry_tls = True
                        break
                    raise IOError("TLS certificate error: %s" % e)
                if isinstance(e, (socket.gaierror, OSError)) or "resolve" in str(e).lower():
                    DNS_CACHE.pop(host, None)
            if first is None and last is not None:
                first = last
            dlog("http %s via %s failed: %s" % (trunc(url, 60), m, last), "WARN")
        if retry_tls:
            continue
        if att < retries:
            time.sleep(min(1 + att, 4))
    raise IOError(str(first or last) if (first or last) else "download failed")


def http_get(url, headers=None, timeout=None, retries=2, post=None, jbody=None, want_url=False):
    # GET/POST с цепочкой: urllib → curl → wget → busybox → openssl; http→https с откатом; лимит запросов; пины
    timeout = timeout or ST.g("socket_timeout")
    hd = dict({"User-Agent": ua(), "Accept": "*/*", "Accept-Language": "en-US,en;q=0.8,ru;q=0.6"}, **rand_headers())
    hd.update(headers or {})
    body = None
    if jbody is not None:
        body = json.dumps(jbody).encode()
        hd.setdefault("Content-Type", "application/json")
    elif post is not None:
        body = urlencode(post).encode() if isinstance(post, dict) else post
        hd.setdefault("Content-Type", "application/x-www-form-urlencoded; charset=UTF-8")
    host = urlparse(url).hostname or ""
    urls = [url]
    if url.startswith("http://") and ST.g("https_upgrade") and not is_local_host(host):
        urls = ["https://" + url[7:], url]
    last = None
    for u in urls:
        try:
            data, fu = _get_one(u, hd, timeout, retries if len(urls) == 1 or u == urls[-1] else 0, body)
            return (data, fu) if want_url else data
        except HttpErr as e:
            note_error(u, e)
            raise
        except Exception as e:
            last = e
    note_error(url, last)
    raise IOError(str(last))


def get_text(url, **k):
    return http_get(url, **k).decode("utf-8", "replace")


def get_json(url, **k):
    return json.loads(get_text(url, **k))


def final_url(url, headers=None):
    # адрес после редиректов (короткие ссылки)
    try:
        return http_get(url, headers=headers, want_url=True, retries=1)[1]
    except Exception:
        return url


# ==========================================================================
#  МЕДИА: типы, поиск медиа на страницах, прямое скачивание, ffmpeg, yt-dlp, gallery-dl
# ==========================================================================
VEXT = {".mp4", ".mkv", ".webm", ".mov", ".m4v", ".avi", ".flv", ".ts", ".m3u8"}
AEXT = {".mp3", ".m4a", ".aac", ".opus", ".ogg", ".oga", ".flac", ".wav"}
IEXT = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".bmp", ".heic", ".avif"}
ICON = {"video": "🎬", "audio": "🎵", "photo": "🖼", "text": "📝", "file": "📎"}
CT_EXT = {"image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".webp", "image/gif": ".gif", "video/mp4": ".mp4", "video/webm": ".webm", "audio/mpeg": ".mp3", "audio/mp4": ".m4a", "audio/ogg": ".ogg"}
SLOW_HOSTS = ("instagram.com", "tiktok.com", "twitter.com", "x.com", "facebook.com", "threads.net", "threads.com")


def ext_of(u):
    return Path(urlparse(u).path).suffix.lower()


def type_of_ext(e):
    return "video" if e in VEXT else "audio" if e in AEXT else "photo" if e in IEXT else None


def unesc(s):
    # JSON-экранирование в HTML → обычный URL
    s = s.replace("\\u0026", "&").replace("\\u002F", "/").replace("\\/", "/").replace("&amp;", "&").replace("\\u003D", "=")
    return html.unescape(s)


def scrape_media(url, html_text=None):
    # поиск медиа на странице: og/twitter-теги, <video>/<audio>/<source>, <img>, ссылки, JSON-LD/встроенный JSON
    if html_text is None:
        html_text = http_get(url, {"Referer": url}).decode("utf-8", "replace")
    t = unesc(html_text)
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
    for m in re.finditer(r'"(?:contentUrl|video_url|display_url|playable_url|hd_src|sd_src|browser_native_hd_url|browser_native_sd_url)"\s*:\s*"([^"]+)"', t):
        add(m.group(1), "video" if re.search(r"video|play|_src|native|\.mp4", m.group(0)) or ext_of(m.group(1).split("?")[0]) in VEXT else "photo")
    return items


def wayback_url(url):
    try:
        d = json.loads(http_get("https://archive.org/wayback/available?url=" + quote(url, safe=""), retries=1).decode())
        return d.get("archived_snapshots", {}).get("closest", {}).get("url")
    except Exception:
        return None


def dl_direct(url, dest_dir, referer=None, label="", name=None, headers=None):
    # прямое скачивание с докачкой (.part), прогресс-баром, TLS-политикой и запасным curl
    p = urlparse(url)
    hd = {"User-Agent": ua(), "Referer": referer or "%s://%s/" % (p.scheme, p.netloc), "Accept": "*/*"}
    hd.update(headers or {})
    fname = sanitize(name) if name else (sanitize(unquote(Path(p.path).name)) or "file")
    dest_dir = Path(dest_dir)
    dest_dir.mkdir(parents=True, exist_ok=True)
    part = dest_dir / (fname + ".part")
    host = p.hostname or ""
    rate_wait(host)
    last = None
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
                if cdn and not name:
                    fname = sanitize(unquote(cdn.group(1)))
                if not Path(fname).suffix:
                    fname += CT_EXT.get((r.headers.get("Content-Type") or "").split(";")[0].strip(), "")
                bar = Bar(total, label or trunc(fname, 12), "B")
                bar.cur = have
                with open(str(part), "ab" if have else "wb") as f:
                    while True:
                        ch = r.read(65536)
                        if not ch:
                            break
                        f.write(ch)
                        bar.update(bar.cur + len(ch))
                bar.close()
            if total and part.stat().st_size < total * 0.98:
                raise IOError("incomplete download")
            final = uniq(dest_dir / fname)
            os.replace(str(part), str(final))
            return final
        except urllib.error.HTTPError as e:
            last = e
            if e.code == 416 and part.exists():
                final = uniq(dest_dir / fname)
                os.replace(str(part), str(final))
                return final
            if e.code in (401, 403, 404, 410):
                break
            time.sleep(1 + attempt)
        except Exception as e:
            last = e
            if "CERTIFICATE" in str(e).upper() and host not in INSECURE and tls_policy(host):
                continue
            DNS_CACHE.pop(host, None)
            time.sleep(1 + attempt)
    # запасной вариант: curl / wget (только если это не окончательный отказ сервера 401/403/404/410)
    final_refusal = isinstance(last, urllib.error.HTTPError) and last.code in (401, 403, 404, 410)
    for tool in ([] if final_refusal else ("curl", "wget")):
        if not shutil.which(tool):
            continue
        out = dest_dir / (fname + ".dl")
        cmd = ["curl", "-sSL", "--fail", "-o", str(out), "-A", hd["User-Agent"], "-e", hd["Referer"], url] if tool == "curl" else ["wget", "-q", "-O", str(out), "-U", hd["User-Agent"], "--referer", hd["Referer"], url]
        if proxy_url():
            cmd = (cmd[:1] + ["-x", proxy_url()] + cmd[1:]) if tool == "curl" else cmd
        try:
            with Spin(L("Запасной способ: %s" % tool, "Fallback: %s" % tool), quiet=True):
                r = subprocess.run(cmd, timeout=3600)
            if r.returncode == 0 and out.exists() and out.stat().st_size > 0:
                final = uniq(dest_dir / (fname if Path(fname).suffix else fname + ".bin"))
                os.replace(str(out), str(final))
                return final
            out.unlink(missing_ok=True)
        except Exception as e:
            last = e
            out.unlink(missing_ok=True)
    note_error(url, last)
    raise IOError(str(last) if last else L("не удалось скачать", "download failed"))


def probe_duration(path):
    if not shutil.which("ffprobe"):
        return None
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=nw=1:nk=1", str(path)], timeout=60)
    try:
        return float(r.stdout.decode().strip())
    except Exception:
        return None


def ff_run(args, label="ffmpeg", duration=None):
    # ffmpeg с прогресс-баром (градиент); Ctrl+C корректно прерывает
    ff = shutil.which("ffmpeg")
    if not ff:
        print("[!] ffmpeg " + L("не установлен (apk add ffmpeg)", "is not installed (apk add ffmpeg)"))
        return 1
    cmd = [ff, "-y", "-hide_banner", "-nostats", "-loglevel", "error", "-progress", "pipe:1"] + [str(a) for a in args]
    dlog("ffmpeg " + " ".join(cmd[1:])[:300])
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
        print("[!] " + trunc((err[0] if err and err[0].strip() else "ffmpeg error").strip().splitlines()[-1], term_w() - 6))
        if p.returncode >= 128:
            print("[*] " + L("ffmpeg упал (SIGSYS). Среда → «ffmpeg LD_PRELOAD-обход».", "ffmpeg crashed (SIGSYS). Environment → 'ffmpeg LD_PRELOAD hack'."))
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
#  yt-dlp: опции, цепочка запасных способов
# ==========================================================================
YT_CLIENTS = ["tv", "android_vr", "web_safari", "mweb", "ios", "android"]
FATAL = ("private video", "video unavailable", "been removed", "copyright", "not available in your country", "members-only", "this video is not available", "account has been terminated")
DEVICES = {"generic": (0, True, "mp4"), "iphone": (2160, True, "mp4"), "ipad": (2160, True, "mp4"), "android": (1080, True, "mp4"), "appletv": (2160, True, "mp4"), "chromecast": (1080, True, "mp4")}


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


def effective_height(q=None):
    # итоговая высота: настройка качества, ограниченная возможностями выбранного устройства
    q = q or ST.g("quality")
    mx = DEVICES.get(ST.g("device"), DEVICES["generic"])[0]
    h = 99999 if q == "best" else int(q)
    return min(h, mx) if mx else h


def vformat(q=None):
    hh = effective_height(q)
    h = "" if hh >= 99999 else "[height<=%s]" % hh
    c_ = []
    if ST.g("prefer_h264") or ST.g("device") != "generic":
        c_.append("bv*%s[vcodec^=avc1]+ba[ext=m4a]" % h)
    c_ += ["bv*%s+ba" % h, "b%s" % h, "bv*+ba", "b", "w"]
    return "/".join(c_)


def aformat():
    return "ba[ext=m4a]/ba/b" if ST.g("audio_format") in ("m4a", "best") else "ba/b"


def ydl_opts(kind, client=None, generic=False, q=None, nojs=False):
    o = {"quiet": True, "no_warnings": True, "noprogress": True, "logger": QLog(), "socket_timeout": ST.g("socket_timeout"), "retries": ST.g("retries"),
         "fragment_retries": ST.g("retries"), "concurrent_fragment_downloads": ST.g("fragments"), "continuedl": True, "noplaylist": True,
         "outtmpl": outtmpl(kind), "windowsfilenames": True, "http_headers": {"User-Agent": ua()}, "overwrites": False, "trim_file_name": 200}
    if proxy_url():
        o["proxy"] = proxy_url()
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
    if not nojs and (shutil.which("node") or shutil.which("qjs")):
        o["js_runtimes"] = {"node": {}} if shutil.which("node") else {"quickjs": {}}
    pp_ = []
    ff = have_ffmpeg()
    if kind == "audio":
        o["format"] = aformat()
        af = ST.g("audio_format")
        if ff and af != "best":
            pp_.append({"key": "FFmpegExtractAudio", "preferredcodec": af, "preferredquality": ST.g("audio_quality") if af in ("mp3", "m4a") else None})
    else:
        o["format"] = vformat(q)
        o["merge_output_format"] = ST.g("container") if ST.g("device") == "generic" else "mp4"
        if ST.g("subs"):
            o.update(writesubtitles=True, writeautomaticsub=True, subtitleslangs=[x.strip() for x in ST.g("sub_langs").split(",") if x.strip()])
            if ff and ST.g("container") in ("mp4", "mkv"):
                pp_.append({"key": "FFmpegEmbedSubtitle"})
    if ff and ST.g("embed_meta"):
        pp_.append({"key": "FFmpegMetadata", "add_metadata": True, "add_chapters": True})
    if ff and ST.g("embed_thumb") and not (kind == "audio" and ST.g("audio_format") in ("opus", "flac", "best")):
        o["writethumbnail"] = True
        pp_.insert(0, {"key": "FFmpegThumbnailsConvertor", "format": "jpg", "when": "before_dl"})
        pp_.append({"key": "EmbedThumbnail"})
    if ST.g("info_json"):
        o["writeinfojson"] = True
    o["postprocessors"] = pp_
    return o


def run_api(url, o):
    # yt-dlp через API: спиннер пока идёт анализ, затем градиентный прогресс-бар
    import yt_dlp
    ck = cookies_for(urlparse(url).netloc)
    if ck:
        o["cookiefile"] = ck
    if (urlparse(url).hostname or "") in INSECURE:
        o["nocheckcertificate"] = True
    bar = [None]
    sp = Spin(L("yt-dlp: получаю данные", "yt-dlp: fetching info"), quiet=True)

    def stop_spin():
        if sp.th and not sp._stop:
            sp._stop = True
            sp.th.join(0.5)
            with _OUT:
                sys.stdout.write("\r\033[K")

    def hook(d):
        if d.get("status") == "downloading":
            stop_spin()
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
    sp.__enter__()
    try:
        with yt_dlp.YoutubeDL(o) as y:
            info = y.extract_info(url, download=True)
            if info and info.get("entries"):
                info = [e for e in info["entries"] if e][0]
            rd = (info or {}).get("requested_downloads") or []
            path = rd[0].get("filepath") if rd else y.prepare_filename(info)
        return True, path
    except KeyboardInterrupt:
        raise
    except Exception as e:
        return False, ANSI_RE.sub("", str(e)).strip()[:300]
    finally:
        stop_spin()
        sp.__exit__(None, None, None)
        if bar[0]:
            bar[0].close()


def run_bin(url, kind, client=None, generic=False, impersonate=False):
    # yt-dlp как процесс (запасной способ при сбоях API-режима)
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
    if proxy_url():
        cmd += ["--proxy", proxy_url()]
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


def yt_manual(url, kind):
    # последний шанс для YouTube: прогрессивные форматы (с аудио) из ytInitialPlayerResponse без шифрования
    m = re.search(r"(?:v=|youtu\.be/|shorts/)([\w-]{11})", url)
    if not m:
        return False, "no id"
    t = get_text("https://www.youtube.com/watch?v=%s&hl=en" % m.group(1), headers={"User-Agent": UA_DESK})
    mm = re.search(r"ytInitialPlayerResponse\s*=\s*(\{.+?\});", t, re.S)
    if not mm:
        return False, "no player response"
    sd = json.loads(mm.group(1)).get("streamingData", {})
    fmts = [f for f in sd.get("formats", []) if f.get("url")]
    if not fmts:
        return False, "no direct formats (ciphered)"
    best = max(fmts, key=lambda f: f.get("height", 0))
    p = dl_direct(best["url"], outdir("video"), referer="https://www.youtube.com/", name="yt_%s.mp4" % m.group(1))
    return True, str(p)


def ytdlp_chain(url, kind, q=None):
    # API (клиенты YouTube) → API без JS → процесс → generic → impersonate → ручной разбор YouTube
    host = (urlparse(url).hostname or "").lower()
    yt = "youtube.com" in host or "youtu.be" in host
    steps = [("api", cl) for cl in ([None] + (YT_CLIENTS if yt else []))] + [("nojs", None), ("bin", None), ("gen", None)]
    if has_impersonate():
        steps.append(("imp", None))
    if yt:
        steps.append(("manual", None))
    last, tried_tls, i = "", False, 0
    while i < len(steps):
        st, cl = steps[i]
        i += 1
        dlog("yt-dlp step %s client=%s" % (st, cl))
        try:
            if st == "api":
                ok, res = run_api(url, ydl_opts(kind, cl, q=q))
            elif st == "nojs":
                ok, res = run_api(url, ydl_opts(kind, None, q=q, nojs=True))
            elif st == "gen":
                ok, res = run_api(url, ydl_opts(kind, None, True, q=q))
            elif st == "manual":
                ok, res = yt_manual(url, kind)
            else:
                ok, res = run_bin(url, kind, cl, impersonate=(st == "imp"))
        except KeyboardInterrupt:
            raise
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
        if any(w in low for w in FATAL):
            break
        if "login" in low or "log in" in low or "sign in" in low or "cookies" in low:
            if not cookies_for(host):
                last += " | " + L("нужны cookies: Сеть → Мастер cookies (%s)" % host.replace("www.", ""), "cookies needed: Network → Cookies wizard (%s)" % host.replace("www.", ""))
            break
    note_error(url, last)
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
    if proxy_url():
        cmd += ["--proxy", proxy_url()]
    ck = cookies_for(host)
    if ck:
        cmd += ["--cookies", ck]
    if any(h in host for h in SLOW_HOSTS):
        cmd += ["--sleep-request", "3-8"]
    for att in range(2):
        r = subprocess.run(cmd, timeout=3600)
        err = r.stderr.decode("utf-8", "replace")
        if "ModuleNotFoundError" in err or "No module named" in err:
            mod = re.search(r"No module named '([\w.]+)'", err)
            with Spin(L("Доустанавливаю зависимости gallery-dl", "Installing gallery-dl dependencies"), quiet=True):
                pip_install(GDL_DEPS + ["gallery-dl"] + ([mod.group(1).split(".")[0]] if mod else []))
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
    with Spin(L("gallery-dl: скачиваю галерею", "gallery-dl: downloading gallery"), quiet=True):
        rc, out, err = gdl(["-d", str(d), url], urlparse(url).netloc.lower())
    new = [p for p in d.rglob("*") if p.is_file() and p not in before]
    if new:
        return True, str(new[0].parent) + " (%d)" % len(new)
    return False, (err.strip().splitlines() or ["gallery-dl: nothing downloaded"])[-1][:200]


# ==========================================================================
#  СОЦСЕТИ: Instagram, TikTok, Threads, Likee, X/Twitter, Telegram (+форматированный текст), Bluesky, Reddit, Pinterest, Facebook
#  Каждая цепочка: несколько API/страниц по очереди; результат — список «элементов» (type/url/title/…)
# ==========================================================================
class NeedLogin(Exception):
    pass


def mkitem(typ, url, title="", referer=None, name=None, sub=None, headers=None, dur=None, **extra):
    d = {"type": typ, "url": url, "title": title or url, "referer": referer, "name": name, "sub": sub, "headers": headers, "dur": dur}
    d.update(extra)
    return d


def social_kind(url):
    # платформа по адресу
    h = (urlparse(url).hostname or "").lower().replace("www.", "")
    table_ = (("instagram", ("instagram.com", "instagr.am", "ig.me")), ("tiktok", ("tiktok.com",)), ("threads", ("threads.net", "threads.com")), ("likee", ("likee.video", "likee.com", "l.likee.video")),
              ("twitter", ("x.com", "twitter.com", "fxtwitter.com", "vxtwitter.com", "fixupx.com")), ("facebook", ("facebook.com", "fb.watch", "fb.com", "m.facebook.com")),
              ("reddit", ("reddit.com", "redd.it", "v.redd.it")), ("pinterest", ("pinterest.com", "pin.it", "pinterest.ru")), ("telegram", ("t.me", "telegram.me", "telegra.ph", "graph.org", "telegram.dog")),
              ("bluesky", ("bsky.app",)), ("gallery", ("fapello.com", "fapello.is", "fapello.su")), ("boosty", ("boosty.to",)), ("vk", ("vk.com", "vkvideo.ru", "vk.ru")), ("youtube", ("youtube.com", "youtu.be", "m.youtube.com")))
    for k, hs in table_:
        if any(h == x or h.endswith("." + x) for x in hs):
            return k
    return ""


CUSTOM_FIRST = ("instagram", "threads", "telegram", "bluesky", "twitter", "tiktok", "likee", "gallery", "boosty")   # сначала свой разбор, потом yt-dlp
ALT_SOCIAL = ("facebook", "reddit", "pinterest", "vk")                                       # сначала yt-dlp, потом свой разбор


# ---------- HTML-дерево: сохраняет теги, классы и style (шрифты, размеры) ----------
from html.parser import HTMLParser
VOID = {"br", "hr", "img", "input", "meta", "link", "source", "wbr", "area", "col", "embed", "param", "track"}


class Node:
    def __init__(self, tag, attrs=None, parent=None):
        self.tag, self.attrs, self.children, self.parent = tag, attrs or {}, [], parent


class TreeBuilder(HTMLParser):
    def __init__(self):
        HTMLParser.__init__(self, convert_charrefs=True)
        self.root = Node("root")
        self.cur = self.root

    def handle_starttag(self, tag, attrs):
        n = Node(tag, {k: (v if v is not None else "") for k, v in attrs}, self.cur)
        self.cur.children.append(n)
        if tag not in VOID:
            self.cur = n

    def handle_startendtag(self, tag, attrs):
        self.cur.children.append(Node(tag, {k: (v if v is not None else "") for k, v in attrs}, self.cur))

    def handle_endtag(self, tag):
        n = self.cur
        while n is not None and n.tag != tag:
            n = n.parent
        if n is not None and n.parent is not None:
            self.cur = n.parent

    def handle_data(self, data):
        self.cur.children.append(data)


def parse_html(s):
    tb = TreeBuilder()
    tb.feed(s)
    tb.close()
    return tb.root


def walk(n):
    for ch in n.children:
        if isinstance(ch, Node):
            yield ch
            for x in walk(ch):
                yield x


def has_cls(n, cls):
    return cls in n.attrs.get("class", "").split()


def cls_has(n, sub):
    return sub in n.attrs.get("class", "")


def node_html(n):
    # сериализация узла обратно в HTML (с атрибутами style/class)
    if isinstance(n, str):
        return html.escape(n, quote=False)
    if n.tag == "root":
        return "".join(node_html(c_) for c_ in n.children)
    a = "".join(' %s="%s"' % (k, html.escape(v, quote=True)) for k, v in n.attrs.items())
    if n.tag in VOID:
        return "<%s%s>" % (n.tag, a)
    return "<%s%s>%s</%s>" % (n.tag, a, "".join(node_html(c_) for c_ in n.children), n.tag)


def inner_html(n):
    return "".join(node_html(c_) for c_ in n.children)


def node_text(n):
    if isinstance(n, str):
        return n
    if n.tag in ("script", "style"):
        return ""
    if n.tag == "br":
        return "\n"
    return "".join(node_text(c_) for c_ in n.children)


def node_json(n):
    # дерево в JSON (ничего не теряется: теги, атрибуты, вложенность)
    if isinstance(n, str):
        return n
    return {"tag": n.tag, "attrs": n.attrs, "children": [node_json(c_) for c_ in n.children]}


def absolutize(root, base):
    # относительные ссылки → абсолютные
    for n in walk(root):
        for k in ("href", "src", "data-src", "poster"):
            v = n.attrs.get(k)
            if v and not v.startswith(("http", "data:", "#", "mailto:", "tg:")):
                n.attrs[k] = urljoin(base, v)
        if n.tag == "a" and n.attrs.get("href", "").lower().startswith("javascript:"):
            n.attrs["href"] = "#"
    return root


BLOCK = {"p", "div", "h1", "h2", "h3", "h4", "h5", "h6", "li", "tr", "blockquote", "pre", "ul", "ol", "table", "section", "article", "details", "summary", "figure", "figcaption", "hr"}


def to_md(n, depth=0, in_pre=False):
    # HTML → Markdown: заголовки, списки, таблицы, цитаты, код, формулы, спойлеры; шрифты/размеры/цвета сохраняются как inline-HTML
    if isinstance(n, str):
        return n.replace("\xa0", " ")
    t = n.tag
    kids = lambda: "".join(to_md(c_, depth, in_pre or t == "pre") for c_ in n.children)
    cl = n.attrs.get("class", "")
    st = n.attrs.get("style", "")
    if t in ("script", "style"):
        return ""
    if "emoji" in cl and t in ("i", "span", "tg-emoji"):
        return node_text(n)
    if t in ("tg-emoji",):
        return node_text(n) or n.attrs.get("emoji-id", "")
    if t in ("b", "strong"):
        return "**%s**" % kids() if kids().strip() else kids()
    if t in ("i", "em"):
        return "*%s*" % kids() if kids().strip() else kids()
    if t in ("u", "ins"):
        return "<u>%s</u>" % kids()
    if t in ("s", "strike", "del"):
        return "~~%s~~" % kids()
    if t == "mark":
        return "==%s==" % kids()
    if t in ("sub", "sup"):
        return "<%s>%s</%s>" % (t, kids(), t)
    if t == "code" and not in_pre:
        return "`%s`" % node_text(n)
    if t == "pre":
        lang = ""
        for c_ in n.children:
            if isinstance(c_, Node) and c_.tag == "code":
                lang = re.sub(r"^language-", "", c_.attrs.get("class", "").split(" ")[0]) if c_.attrs.get("class") else ""
        return "\n```%s\n%s\n```\n" % (lang, node_text(n).strip("\n"))
    if t == "a":
        return "[%s](%s)" % (kids() or n.attrs.get("href", ""), n.attrs.get("href", "")) if n.attrs.get("href") and not n.attrs["href"].startswith("#") else kids()
    if t == "br":
        return "  \n"
    if t == "hr":
        return "\n\n---\n\n"
    if t == "img":
        return "![%s](%s)" % (n.attrs.get("alt", ""), n.attrs.get("src", ""))
    if t in ("video", "audio", "source") and n.attrs.get("src"):
        return "[%s](%s)" % (t, n.attrs["src"])
    if re.match(r"h[1-6]$", t):
        return "\n\n%s %s\n\n" % ("#" * int(t[1]), kids().strip())
    if t == "blockquote":
        return "\n\n" + "\n".join("> " + l_ for l_ in kids().strip().split("\n")) + "\n\n"
    if t in ("ul", "ol"):
        out, i = [], 0
        for c_ in n.children:
            if isinstance(c_, Node) and c_.tag == "li":
                i += 1
                body = to_md(c_, depth + 1).strip().replace("\n", "\n" + "  ")
                out.append("  " * depth + ("%d. " % i if t == "ol" else "- ") + body)
        return "\n" + "\n".join(out) + "\n"
    if t == "table":
        rows = [[node_text(c_).strip().replace("\n", " ") for c_ in r.children if isinstance(c_, Node) and c_.tag in ("td", "th")] for r in walk(n) if r.tag == "tr"]
        rows = [r for r in rows if r]
        if not rows:
            return ""
        w = max(len(r) for r in rows)
        rows = [r + [""] * (w - len(r)) for r in rows]
        out = ["| " + " | ".join(rows[0]) + " |", "|" + " --- |" * w] + ["| " + " | ".join(r) + " |" for r in rows[1:]]
        return "\n\n" + "\n".join(out) + "\n\n"
    if t == "summary":
        return "**%s**\n\n" % kids().strip()
    if "math" in cl or t in ("tg-math", "math"):
        return "$%s$" % node_text(n).strip()
    if "spoiler" in cl or t == "tg-spoiler":
        return "||%s||" % kids()
    if t == "span" and re.search(r"font-(size|family|weight|style)|color|text-decoration", st):
        return '<span style="%s">%s</span>' % (html.escape(st, quote=True), kids())
    if t == "p":
        return "\n\n%s\n\n" % kids().strip()
    if t in ("div", "section", "article", "figure", "figcaption", "details", "tr"):
        k = kids()
        return ("\n" + k.strip("\n") + "\n") if k.strip() else ""
    return kids()


def to_txt(n):
    # HTML → простой текст (с переводами строк у блоков, таблицы через |)
    if isinstance(n, str):
        return n.replace("\xa0", " ")
    if n.tag in ("script", "style"):
        return ""
    if n.tag == "br":
        return "\n"
    if n.tag in ("td", "th"):
        return "".join(to_txt(c_) for c_ in n.children).strip() + " | "
    s = "".join(to_txt(c_) for c_ in n.children)
    if n.tag in BLOCK:
        return "\n" + s.strip("\n") + "\n"
    return s


def clean_md(s):
    s = re.sub(r"[ \t]+\n", "\n", s)
    return re.sub(r"\n{3,}", "\n\n", s).strip() + "\n"


def clean_txt(s):
    return re.sub(r"\n{3,}", "\n\n", s).strip() + "\n"


CSS = ("body{font:16px/1.6 -apple-system,system-ui,sans-serif;max-width:780px;margin:1.2em auto;padding:0 1em;color:#222;background:#fff}"
       "@media(prefers-color-scheme:dark){body{background:#16181c;color:#e6e6e6}a{color:#6cb6ff}}table{border-collapse:collapse;margin:.6em 0}td,th{border:1px solid #888;padding:.3em .6em}"
       "blockquote{border-left:3px solid #888;margin:.6em 0;padding:.1em .9em;opacity:.92}pre,code{background:rgba(127,127,127,.18);border-radius:4px}pre{padding:.6em;overflow:auto}"
       "tg-spoiler,.tg_spoiler{background:#888;color:transparent}tg-spoiler:hover,.tg_spoiler:hover{color:inherit;background:none}img,video{max-width:100%}.meta{opacity:.6;font-size:.85em}")


def safe_html(s):
    # убираем скрипты и inline-обработчики (стили и шрифты остаются)
    s = re.sub(r"(?is)<(script|iframe|object|embed)\b.*?</\1>", "", s)
    s = re.sub(r"(?i)\son\w+\s*=\s*(\"[^\"]*\"|'[^']*'|[^\s>]+)", "", s)
    return s


def make_text_item(htm, title, sub, name, base, meta=""):
    # форматированный текст → элемент 'text' (html + md + txt + json-дерево)
    root = absolutize(parse_html(htm), base)
    body = safe_html(inner_html(root))
    doc = "<!doctype html><meta charset=utf-8><meta name=viewport content='width=device-width,initial-scale=1'><title>%s</title><style>%s</style>%s<div class=content>%s</div>" % (
        html.escape(title), CSS, ("<p class=meta>%s</p>" % html.escape(meta)) if meta else "", body)
    return mkitem("text", "text:" + name, title, sub=sub, name=name, html=doc, md=clean_md(("_%s_\n\n" % meta if meta else "") + to_md(root)), txt=clean_txt(to_txt(root)),
                  tree=json.dumps(node_json(root), ensure_ascii=False))


# ---------- общие помощники ----------
def jpost(url, data, headers=None):
    return json.loads(http_get(url, post=data, headers=headers).decode("utf-8", "replace"))


def deep_media(t, sub, referer=None, prefix="media"):
    # встроенный JSON страницы: video_versions / image_versions2 / orig (Threads, Pinterest, Instagram embed…)
    t = unesc(t)
    vids = [(m.start(), m.group(1)) for m in re.finditer(r'"video_versions"\s*:\s*\[\s*\{[^\]]*?"url"\s*:\s*"([^"]+)"', t)]
    imgs = [(m.start(), m.group(1)) for m in re.finditer(r'"image_versions2"\s*:\s*\{\s*"candidates"\s*:\s*\[\s*\{[^\]]*?"url"\s*:\s*"([^"]+)"', t)]
    imgs += [(m.start(), m.group(1)) for m in re.finditer(r'"orig"\s*:\s*\{[^}]*?"url"\s*:\s*"([^"]+)"', t)]
    out, seen = [], set()
    for pos, u in vids:
        k = urlparse(u).path
        if k not in seen:
            seen.add(k)
            out.append(mkitem("video", u, "video %d" % (len(out) + 1), referer, "%s_%d.mp4" % (prefix, len(out) + 1), sub))
    for pos, u in imgs:
        if any(0 < pos - vp < 1200 for vp, _ in vids):
            continue
        k = urlparse(u).path
        if k not in seen:
            seen.add(k)
            out.append(mkitem("photo", u, "photo %d" % (len(out) + 1), referer, "%s_%d.jpg" % (prefix, len(out) + 1), sub))
    return out


def og_meta(t, key):
    m = re.search(r'<meta[^>]+(?:property|name)=["\']%s["\'][^>]*content=["\']([^"\']+)' % re.escape(key), t, re.I) or re.search(r'<meta[^>]+content=["\']([^"\']+)["\'][^>]*(?:property|name)=["\']%s["\']' % re.escape(key), t, re.I)
    return unesc(m.group(1)) if m else ""


# ==========================================================================
#  Instagram
# ==========================================================================
IG_UA = "Instagram 275.0.0.27.98 Android (33/13; 420dpi; 1080x2400; samsung; SM-G991B; o1s; exynos2100; en_US; 458229237)"
IG_APP = "936619743392459"
IG_ALPHA = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_"


def ig_media_id(code):
    n = 0
    for ch in code[:11] if len(code) > 28 else code:
        n = n * 64 + IG_ALPHA.index(ch)
    return n


def ig_headers(api=True):
    h = {"User-Agent": IG_UA if api else UA_DESK, "X-IG-App-ID": IG_APP, "Referer": "https://www.instagram.com/", "X-Requested-With": "XMLHttpRequest", "Accept": "*/*"}
    ck = cookie_header("instagram.com")
    if ck:
        h["Cookie"] = ck
        cs = cookie_value("instagram.com", "csrftoken")
        if cs:
            h["X-CSRFToken"] = cs
    return h


def ig_json(url, api=True):
    try:
        d = get_json(url, headers=ig_headers(api), retries=1)
    except HttpErr as e:
        if e.code in (401, 403) and not cookie_header("instagram.com"):
            raise NeedLogin("instagram.com")
        raise
    if isinstance(d, dict) and (d.get("message") == "login_required" or d.get("require_login")):
        raise NeedLogin("instagram.com")
    return d


def ig_best(lst):
    return max(lst, key=lambda v: (v.get("width") or 0) * (v.get("height") or 0)) if lst else None


def ig_items(m, sub, base, referer="https://www.instagram.com/"):
    # медиа-объект Instagram (API или GraphQL) → элементы; карусели разворачиваются
    out = []
    kids = m.get("carousel_media") or [e.get("node") for e in (m.get("edge_sidecar_to_children") or {}).get("edges", [])]
    if kids:
        for i, k in enumerate(kids, 1):
            out += ig_items(k, sub, "%s_%d" % (base, i), referer)
        return out
    cap = ((m.get("caption") or {}).get("text") or "") if isinstance(m.get("caption"), dict) else ""
    if not cap:
        try:
            cap = m["edge_media_to_caption"]["edges"][0]["node"]["text"]
        except Exception:
            cap = ""
    title = (cap.strip().split("\n")[0][:50] or base)
    v = ig_best(m.get("video_versions") or [])
    vu = v["url"] if v else m.get("video_url")
    if vu:
        out.append(mkitem("video", vu, title, referer, base + ".mp4", sub))
        return out
    i2 = ig_best((m.get("image_versions2") or {}).get("candidates") or [])
    iu = i2["url"] if i2 else m.get("display_url")
    if not iu and m.get("display_resources"):
        iu = ig_best(m["display_resources"])["src"]
    if iu:
        out.append(mkitem("photo", iu, title, referer, base + ".jpg", sub))
    return out


def ig_parse(url):
    parts = [x for x in urlparse(url).path.split("/") if x]
    if not parts:
        return ("none",)
    if parts[0] in ("p", "reel", "tv") and len(parts) > 1:
        return ("post", parts[1])
    if parts[0] == "stories":
        if len(parts) >= 3 and parts[1] == "highlights":
            return ("highlight", parts[2])
        if len(parts) >= 2:
            return ("stories", parts[1])
    if len(parts) >= 3 and parts[1] in ("p", "reel", "tv"):
        return ("post", parts[2])
    return ("profile", parts[0])


def ig_embed(code, sub):
    t = unesc(get_text("https://www.instagram.com/p/%s/embed/captioned/" % code, headers={"User-Agent": UA_DESK}))
    out, seen = [], set()
    for u in re.findall(r'"video_url"\s*:\s*"([^"]+)"', t):
        if u not in seen:
            seen.add(u)
            out.append(mkitem("video", u, code, "https://www.instagram.com/", "ig_%s_%d.mp4" % (code, len(out) + 1), sub))
    if not out:
        for tag in re.findall(r"<img[^>]+EmbeddedMediaImage[^>]*>", t):
            m = re.search(r'src="([^"]+)"', tag)
            if m and m.group(1) not in seen:
                seen.add(m.group(1))
                out.append(mkitem("photo", m.group(1), code, "https://www.instagram.com/", "ig_%s_%d.jpg" % (code, len(out) + 1), sub))
    return out


def ig_post(code, sub):
    # пост/рилс/IGTV: API → web-API → GraphQL → ?__a=1 → embed → сторонние зеркала
    mid = ig_media_id(code)
    need = None
    steps = [
        ("api", lambda: ig_json("https://i.instagram.com/api/v1/media/%d/info/" % mid)["items"][0]),
        ("web-api", lambda: ig_json("https://www.instagram.com/api/v1/media/%d/info/" % mid, False)["items"][0]),
        ("graphql", lambda: (lambda d: d["data"].get("xdt_shortcode_media") or d["data"]["shortcode_media"])(
            ig_json("https://www.instagram.com/graphql/query/?doc_id=8845758582119845&variables=" + quote(json.dumps({"shortcode": code}, separators=(",", ":"))), False))),
        ("graphql-old", lambda: ig_json("https://www.instagram.com/graphql/query/?query_hash=b3055c01b4b222b8a47dc12b090e4e64&variables=" + quote(json.dumps({"shortcode": code}, separators=(",", ":"))), False)["data"]["shortcode_media"]),
        ("a=1", lambda: (lambda d: (d.get("items") or [None])[0] or d.get("graphql", {}).get("shortcode_media"))(ig_json("https://www.instagram.com/p/%s/?__a=1&__d=dis" % code, False))),
    ]
    for nm, fn in steps:
        try:
            with Spin(L("Instagram: %s" % nm, "Instagram: %s" % nm), quiet=True):
                m = fn()
            items = ig_items(m, sub, "ig_" + code) if m else []
            if items:
                dlog("ig_post via %s -> %d" % (nm, len(items)))
                return items
        except NeedLogin as e:
            need = e
        except Exception as e:
            dlog("ig_post %s failed: %s" % (nm, e), "WARN")
    try:
        with Spin("Instagram: embed", quiet=True):
            items = ig_embed(code, sub)
        if items:
            return items
    except Exception as e:
        dlog("ig embed failed: %s" % e, "WARN")
    for base in ("https://imginn.com/p/%s/", "https://www.picuki.com/media/%s"):
        try:
            with Spin(L("Instagram: зеркало %s" % urlparse(base).hostname, "Instagram: mirror %s" % urlparse(base).hostname), quiet=True):
                found = [i for i in scrape_media(base % code) if i["type"] in ("video", "photo") and "avatar" not in i["url"]]
            if found:
                return [mkitem(i["type"], i["url"], code, base % code, "ig_%s_%d%s" % (code, n, ".mp4" if i["type"] == "video" else ".jpg"), sub) for n, i in enumerate(found, 1)]
        except Exception as e:
            dlog("ig mirror failed: %s" % e, "WARN")
    if need:
        raise need
    return []


def ig_user(username):
    # профиль: id, имя, аватар (HD), первые посты
    for url, api in (("https://i.instagram.com/api/v1/users/web_profile_info/?username=%s" % username, True), ("https://www.instagram.com/api/v1/users/web_profile_info/?username=%s" % username, False)):
        try:
            u = ig_json(url, api)["data"]["user"]
            if u:
                return {"id": u.get("id"), "username": u.get("username", username), "name": u.get("full_name", ""), "avatar": u.get("profile_pic_url_hd") or u.get("profile_pic_url"),
                        "posts": [e["node"] for e in (u.get("edge_owner_to_timeline_media") or {}).get("edges", [])], "private": u.get("is_private")}
        except NeedLogin:
            raise
        except Exception as e:
            dlog("ig_user failed: %s" % e, "WARN")
    t = get_text("https://www.instagram.com/%s/" % username, headers={"User-Agent": UA_DESK})
    m = re.search(r'"profile_pic_url_hd"\s*:\s*"([^"]+)"', unesc(t))
    av = unesc(m.group(1)) if m else og_meta(t, "og:image")
    if av:
        return {"id": None, "username": username, "name": og_meta(t, "og:title"), "avatar": av, "posts": [], "private": None}
    raise NeedLogin("instagram.com")


def ig_avatar(username, sub):
    u = ig_user(username)
    av = u["avatar"]
    if u.get("id") and cookie_header("instagram.com"):
        try:
            hd = ig_json("https://i.instagram.com/api/v1/users/%s/info/" % u["id"])["user"].get("hd_profile_pic_url_info", {}).get("url")
            av = hd or av
        except Exception:
            pass
    return [mkitem("photo", av, "avatar " + username, "https://www.instagram.com/", "avatar_%s.jpg" % sanitize(username), sub)]


def _ig_reel_items(reel_id, sub, base):
    d = ig_json("https://i.instagram.com/api/v1/feed/reels_media/?reel_ids=%s" % quote(str(reel_id), safe=""))
    reel = (d.get("reels") or {}).get(str(reel_id)) or ((d.get("reels_media") or [None])[0])
    items = []
    for i, m in enumerate((reel or {}).get("items", []), 1):
        items += ig_items(m, sub, "%s_%s" % (base, m.get("pk") or i))
    return items


def ig_stories(username, sub):
    if not cookie_header("instagram.com"):
        raise NeedLogin("instagram.com")
    u = ig_user(username)
    if not u.get("id"):
        raise IOError("no user id")
    items = _ig_reel_items(u["id"], sub, "story_" + sanitize(username))
    if not items:
        try:
            urls, err = gallery_list("https://www.instagram.com/stories/%s/" % username)
            items = [mkitem("video" if ext_of(x.split("?")[0]) in VEXT else "photo", x, "story", None, None, sub) for x in urls]
        except Exception:
            pass
    return items


def ig_highlights(username, sub, only=None):
    if not cookie_header("instagram.com"):
        raise NeedLogin("instagram.com")
    items = []
    if only:
        return _ig_reel_items("highlight:%s" % only, sub + "/highlights", "hl_%s" % only)
    u = ig_user(username)
    tray = ig_json("https://i.instagram.com/api/v1/highlights/%s/highlights_tray/" % u["id"]).get("tray", [])
    for t in tray:
        title = sanitize(t.get("title") or t.get("id", "hl"))
        items += _ig_reel_items(t["id"], "%s/highlights/%s" % (sub, title), "hl_" + title)
    return items


def ig_posts(username, sub):
    u = ig_user(username)
    items = []
    for n in u["posts"]:
        items += ig_items(n, sub + "/posts", "ig_" + (n.get("shortcode") or str(n.get("id"))))
    return items


def soc_instagram(url, want="auto"):
    k = ig_parse(url)
    if k[0] == "post":
        return ig_post(k[1], "social/instagram")
    if k[0] == "stories":
        return ig_stories(k[1], "social/instagram/%s" % k[1])
    if k[0] == "highlight":
        return ig_highlights("", "social/instagram", k[1])
    if k[0] == "profile":
        return ig_avatar(k[1], "social/instagram/%s" % k[1]) + ig_posts(k[1], "social/instagram/%s" % k[1])
    return []


# ==========================================================================
#  TikTok (tikwm API → страница)
# ==========================================================================
_TIKWM = [0.0]


def tikwm(url, data=None, method="POST"):
    # публичный API tikwm: не чаще 1 запроса/сек
    dt = time.time() - _TIKWM[0]
    if dt < 1.1:
        time.sleep(1.1 - dt)
    _TIKWM[0] = time.time()
    hd = {"Referer": "https://www.tikwm.com/", "User-Agent": UA_DESK}
    d = jpost(url, data, hd) if method == "POST" else get_json(url, headers=hd)
    if isinstance(d, dict) and d.get("code") not in (0, None):
        raise IOError("tikwm: %s" % d.get("msg"))
    return d.get("data") or {}


def _tw(u):
    return ("https://www.tikwm.com" + u) if u and u.startswith("/") else u


def tt_items(d, sub, want="auto"):
    vid = d.get("id") or d.get("video_id") or "tt"
    title = (d.get("title") or str(vid)).strip().split("\n")[0][:60]
    out = []
    if d.get("images"):
        out += [mkitem("photo", _tw(u), title, "https://www.tiktok.com/", "tt_%s_%d.jpg" % (vid, i), sub) for i, u in enumerate(d["images"], 1)]
    else:
        u = _tw(d.get("hdplay") or d.get("play"))
        if u:
            out.append(mkitem("video", u, title, "https://www.tiktok.com/", "tt_%s.mp4" % vid, sub, dur=d.get("duration")))
    if want == "audio" and d.get("music"):
        out = [mkitem("audio", _tw(d["music"]), (d.get("music_info") or {}).get("title") or title, "https://www.tiktok.com/", "tt_%s_music.mp3" % vid, sub)]
    return out


def tt_user_page(user):
    t = get_text("https://www.tiktok.com/@%s" % user, headers={"User-Agent": UA_DESK})
    m = re.search(r'<script id="__UNIVERSAL_DATA_FOR_REHYDRATION__"[^>]*>(.*?)</script>', t, re.S)
    if not m:
        return {}
    return json.loads(m.group(1)).get("__DEFAULT_SCOPE__", {}).get("webapp.user-detail", {}).get("userInfo", {}).get("user", {})


def tt_avatar(user, sub):
    av = ""
    try:
        d = tikwm("https://www.tikwm.com/api/user/info?unique_id=%s" % quote(user), method="GET")
        u = d.get("user") or {}
        av = u.get("avatarLarger") or u.get("avatarMedium") or u.get("avatar") or u.get("avatarThumb")
    except Exception as e:
        dlog("tt avatar tikwm failed: %s" % e, "WARN")
    if not av:
        u = tt_user_page(user)
        av = u.get("avatarLarger") or u.get("avatarMedium")
    return [mkitem("photo", av, "avatar " + user, "https://www.tiktok.com/", "avatar_%s.jpg" % sanitize(user), sub)] if av else []


def tt_posts(user, sub, count=30):
    d = tikwm("https://www.tikwm.com/api/user/posts", {"unique_id": user, "count": count, "cursor": 0, "hd": 1})
    out = []
    for v in d.get("videos", []):
        out += tt_items(v, sub + "/posts")
    return out


def soc_tiktok(url, want="auto"):
    p = urlparse(url)
    if p.hostname and p.hostname.split(".")[0] in ("vm", "vt") or "/t/" in p.path:
        url = final_url(url)
        p = urlparse(url)
    m = re.match(r"^/@([^/]+)/?$", p.path)
    if m:
        u = m.group(1)
        return tt_avatar(u, "social/tiktok/" + u) + tt_posts(u, "social/tiktok/" + u)
    d = tikwm("https://www.tikwm.com/api/", {"url": url, "hd": 1})
    author = (d.get("author") or {}).get("unique_id") or "tiktok"
    return tt_items(d, "social/tiktok/" + sanitize(author), want)


# ==========================================================================
#  Threads
# ==========================================================================
def soc_threads(url, want="auto"):
    m = re.search(r"/@([^/]+)(?:/post/([\w-]+))?", urlparse(url).path)
    user, code = (m.group(1), m.group(2)) if m else ("threads", None)
    sub = "social/threads/" + sanitize(user)
    base = urlparse(url)
    root = "%s://%s" % (base.scheme, base.netloc)
    if code:
        for u in (url, "%s/@%s/post/%s/embed/" % (root, user, code)):
            try:
                with Spin("Threads", quiet=True):
                    t = get_text(u, headers={"User-Agent": UA_DESK, "Accept-Language": "en-US,en;q=0.9"})
                items = deep_media(t, sub, url, "threads_" + code)
                if not items:
                    items = [mkitem(i["type"], i["url"], i["title"], url, "threads_%s_%d%s" % (code, n, ".mp4" if i["type"] == "video" else ".jpg"), sub) for n, i in enumerate(scrape_media(url, t), 1) if i["type"] in ("video", "photo") and "profile" not in i["url"]]
                if items:
                    return items
            except Exception as e:
                dlog("threads %s failed: %s" % (u, e), "WARN")
        return []
    t = get_text("%s/@%s" % (root, user), headers={"User-Agent": UA_DESK})
    m2 = re.search(r'"profile_pic_url"\s*:\s*"([^"]+)"', unesc(t))
    av = unesc(m2.group(1)) if m2 else og_meta(t, "og:image")
    return [mkitem("photo", av, "avatar " + user, root, "avatar_%s.jpg" % sanitize(user), sub)] if av else []


# ==========================================================================
#  Likee
# ==========================================================================
def soc_likee(url, want="auto"):
    if "l.likee" in url or "/v/" in url:
        url = final_url(url)
    m = re.search(r"(?:/video/|postId=|/v/)(\d{10,})", url)
    sub = "social/likee"
    if m:
        pid = m.group(1)
        for call in (lambda: jpost("https://api.like-video.com/likee-activity-flow-api/videoApi/getVideoInfo", {"postIds": pid}),
                     lambda: http_get("https://api.like-video.com/likee-activity-flow-api/videoApi/getVideoInfo", jbody={"postIds": pid})):
            try:
                d = call()
                d = json.loads(d.decode()) if isinstance(d, bytes) else d
                v = ((d.get("data") or {}).get("videoList") or [None])[0]
                if v and v.get("videoUrl"):
                    return [mkitem("video", v["videoUrl"], (v.get("msgText") or pid)[:60], "https://likee.video/", "likee_%s.mp4" % pid, sub)]
            except Exception as e:
                dlog("likee api failed: %s" % e, "WARN")
    t = get_text(url, headers={"User-Agent": UA_DESK})
    found = [i for i in scrape_media(url, t) if i["type"] == "video"]
    for mm in re.finditer(r'"(?:video_url|videoUrl|playUrl)"\s*:\s*"(https?:[^"]+)"', unesc(t)):
        found.append({"type": "video", "url": mm.group(1), "title": "likee"})
    return [mkitem("video", f["url"], f.get("title", "likee"), url, "likee_%d.mp4" % n, sub) for n, f in enumerate(found[:5], 1)]


# ==========================================================================
#  X / Twitter (fxtwitter → vxtwitter)
# ==========================================================================
def soc_twitter(url, want="auto"):
    p = urlparse(url)
    m = re.match(r"^/([^/]+)/status(?:es)?/(\d+)", p.path)
    if not m:
        u = [x for x in p.path.split("/") if x][:1]
        if not u:
            return []
        d = get_json("https://api.fxtwitter.com/%s" % u[0]).get("user", {})
        sub = "social/twitter/" + sanitize(u[0])
        out = []
        if d.get("avatar_url"):
            out.append(mkitem("photo", d["avatar_url"].replace("_normal", "_400x400"), "avatar " + u[0], None, "avatar_%s.jpg" % sanitize(u[0]), sub))
        if d.get("banner_url"):
            out.append(mkitem("photo", d["banner_url"], "banner " + u[0], None, "banner_%s.jpg" % sanitize(u[0]), sub))
        return out
    user, sid = m.group(1), m.group(2)
    sub = "social/twitter/" + sanitize(user)
    items = []
    try:
        tw = get_json("https://api.fxtwitter.com/%s/status/%s" % (user, sid)).get("tweet", {})
        media = (tw.get("media") or {}).get("all") or ((tw.get("media") or {}).get("photos") or []) + ((tw.get("media") or {}).get("videos") or [])
        for n, md in enumerate(media, 1):
            typ = "video" if md.get("type") in ("video", "gif") else "photo"
            items.append(mkitem(typ, md["url"], (tw.get("text") or sid)[:50], "https://x.com/", "tw_%s_%d%s" % (sid, n, ".mp4" if typ == "video" else ".jpg"), sub))
        if not items and tw.get("text"):
            items.append(make_text_item("<p>%s</p>" % html.escape(tw["text"]).replace("\n", "<br>"), "tweet %s" % sid, sub, "tw_%s" % sid, "https://x.com/", tw.get("created_at", "")))
    except Exception as e:
        dlog("fxtwitter failed: %s" % e, "WARN")
    if not items:
        tw = get_json("https://api.vxtwitter.com/%s/status/%s" % (user, sid))
        for n, md in enumerate(tw.get("media_extended") or [], 1):
            typ = "video" if md.get("type") in ("video", "gif") else "photo"
            items.append(mkitem(typ, md["url"], (tw.get("text") or sid)[:50], "https://x.com/", "tw_%s_%d%s" % (sid, n, ".mp4" if typ == "video" else ".jpg"), sub))
    return items


# ==========================================================================
#  Bluesky
# ==========================================================================
BSKY = "https://public.api.bsky.app/xrpc/"


def soc_bluesky(url, want="auto"):
    m = re.search(r"/profile/([^/]+)(?:/post/([\w]+))?", urlparse(url).path)
    if not m:
        return []
    handle, rkey = m.group(1), m.group(2)
    sub = "social/bluesky/" + sanitize(handle)
    if not rkey:
        pr = get_json(BSKY + "app.bsky.actor.getProfile?actor=" + quote(handle))
        out = []
        if pr.get("avatar"):
            out.append(mkitem("photo", pr["avatar"], "avatar " + handle, None, "avatar_%s.jpg" % sanitize(handle), sub))
        if pr.get("banner"):
            out.append(mkitem("photo", pr["banner"], "banner " + handle, None, "banner_%s.jpg" % sanitize(handle), sub))
        return out
    did = handle if handle.startswith("did:") else get_json(BSKY + "com.atproto.identity.resolveHandle?handle=" + quote(handle))["did"]
    post = get_json(BSKY + "app.bsky.feed.getPostThread?depth=0&uri=" + quote("at://%s/app.bsky.feed.post/%s" % (did, rkey), safe=""))["thread"]["post"]
    emb = post.get("embed") or {}
    if "media" in emb:
        emb = emb["media"]
    out = []
    for n, im in enumerate(emb.get("images") or [], 1):
        out.append(mkitem("photo", im.get("fullsize") or im.get("thumb"), im.get("alt") or "bsky", None, "bsky_%s_%d.jpg" % (rkey, n), sub))
    if emb.get("playlist"):
        out.append(mkitem("video", emb["playlist"], "bsky video", None, "bsky_%s.mp4" % rkey, sub))
    txt = (post.get("record") or {}).get("text", "")
    if txt and (not out or want == "text"):
        out.append(make_text_item("<p>%s</p>" % html.escape(txt).replace("\n", "<br>"), "bsky %s" % rkey, sub, "bsky_%s" % rkey, url, (post.get("author") or {}).get("handle", "")))
    return out


# ==========================================================================
#  Reddit / Pinterest / Facebook (запасной разбор)
# ==========================================================================
def soc_reddit(url, want="auto"):
    u = url.split("?")[0].rstrip("/") + ".json?raw_json=1"
    d = get_json(u, headers={"User-Agent": "Mozilla/5.0 (compatible; MediaForge/1.0)"})
    p = d[0]["data"]["children"][0]["data"]
    sub = "social/reddit/" + sanitize(p.get("subreddit", "r"))
    pid = p.get("id", "post")
    out = []
    mm = (p.get("media") or {}).get("reddit_video")
    if mm:
        out.append(mkitem("video", mm["fallback_url"].split("?")[0], p.get("title", pid)[:60], "https://www.reddit.com/", "rd_%s.mp4" % pid, sub))
        base = mm["fallback_url"].split("DASH_")[0]
        out.append(mkitem("audio", base + "DASH_AUDIO_128.mp4", "audio of " + pid, "https://www.reddit.com/", "rd_%s_audio.m4a" % pid, sub))
    if p.get("is_gallery"):
        for n, it in enumerate((p.get("gallery_data") or {}).get("items", []), 1):
            md = (p.get("media_metadata") or {}).get(it["media_id"], {})
            su = (md.get("s") or {}).get("u") or (md.get("s") or {}).get("gif")
            if su:
                out.append(mkitem("photo", unesc(su), p.get("title", pid)[:50], "https://www.reddit.com/", "rd_%s_%d.jpg" % (pid, n), sub))
    elif not mm:
        du = p.get("url_overridden_by_dest") or ""
        if ext_of(du.split("?")[0]) in IEXT | VEXT:
            out.append(mkitem(type_of_ext(ext_of(du.split("?")[0])), du, p.get("title", pid)[:60], "https://www.reddit.com/", "rd_" + pid + ext_of(du.split("?")[0]), sub))
        elif (p.get("preview") or {}).get("reddit_video_preview"):
            out.append(mkitem("video", p["preview"]["reddit_video_preview"]["fallback_url"], p.get("title", pid)[:60], None, "rd_%s.mp4" % pid, sub))
    if p.get("selftext_html") and not out:
        out.append(make_text_item(html.unescape(p["selftext_html"]), p.get("title", pid), sub, "rd_" + pid, "https://www.reddit.com/", p.get("author", "")))
    return out


def soc_pinterest(url, want="auto"):
    if "pin.it" in url:
        url = final_url(url)
    t = get_text(url, headers={"User-Agent": UA_DESK})
    items = deep_media(t, "social/pinterest", url, "pin")
    if not items:
        items = [mkitem(i["type"], i["url"], i["title"], url, None, "social/pinterest") for i in scrape_media(url, t) if i["type"] in ("video", "photo")]
    return items


def soc_generic_page(url, want="auto"):
    # запасной разбор страницы: Facebook (мобильная версия), VK и прочие
    u = url
    if "facebook.com" in url:
        u = re.sub(r"^https?://(www\.)?facebook\.com", "https://m.facebook.com", url)
    t = get_text(u, headers={"User-Agent": UA_IOS})
    sub = "social/" + (social_kind(url) or "web")
    return [mkitem(i["type"], i["url"], i["title"], url, None, sub) for i in scrape_media(u, t) if i["type"] in ("video", "photo", "audio")]


# ==========================================================================
#  Telegram: фото, видео, кружки, голосовые, GIF, стикеры, аватарки, текст с форматированием (в т.ч. Rich Text)
# ==========================================================================
TG_UA = {"User-Agent": UA_DESK, "Accept-Language": "en-US,en;q=0.9,ru;q=0.8"}


def _bgurl(style):
    m = re.search(r"url\(['\"]?([^'\")]+)", style or "")
    return html.unescape(m.group(1)) if m else ""


def tg_message_nodes(htm):
    root = parse_html(htm)
    nodes = [n for n in walk(root) if has_cls(n, "tgme_widget_message") and n.attrs.get("data-post")]
    return root, nodes


def tg_items_from_node(node, sub, base="https://t.me/"):
    # один пост виджета → (media-элементы, текстовый элемент или None, заметки)
    post = node.attrs.get("data-post", "x/0")
    chan, _, mid = post.partition("/")
    nm = "tg_%s_%s" % (sanitize(chan), mid)
    out, notes, n = [], [], 0

    def nxt():
        nonlocal n
        n += 1
        return n
    for pn in walk(node):
        c_ = pn.attrs.get("class", "")
        if "tgme_widget_message_photo_wrap" in c_:
            u = _bgurl(pn.attrs.get("style"))
            if u:
                out.append(mkitem("photo", u, "photo", "https://t.me/", "%s_%d.jpg" % (nm, nxt()), sub))
        elif pn.tag == "video" and pn.attrs.get("src"):
            par = pn.parent.attrs.get("class", "") if pn.parent else ""
            kind = "round video" if "roundvideo" in c_ + par else ("gif" if "gif" in c_ + par else "video")
            out.append(mkitem("video", pn.attrs["src"], kind, "https://t.me/", "%s_%d%s.mp4" % (nm, nxt(), "_round" if "round" in kind else ""), sub))
        elif pn.tag == "audio" and pn.attrs.get("src"):
            kind = "voice" if "voice" in c_ else "audio"
            out.append(mkitem("audio", pn.attrs["src"], kind, "https://t.me/", "%s_%d_%s.ogg" % (nm, nxt(), kind), sub))
        elif "tgme_widget_message_sticker" in c_:
            u = pn.attrs.get("data-webp") or _bgurl(pn.attrs.get("style"))
            if u:
                out.append(mkitem("photo", u, "sticker", "https://t.me/", "%s_%d_sticker.webp" % (nm, nxt()), sub))
        elif "link_preview_image" in c_ or "link_preview_right_image" in c_ or "link_preview_video_thumb" in c_:
            u = _bgurl(pn.attrs.get("style"))
            if u:
                out.append(mkitem("photo", u, "link preview", "https://t.me/", "%s_%d_preview.jpg" % (nm, nxt()), sub))
        elif "tgme_widget_message_document_title" in c_:
            notes.append(L("документ/музыка «%s» — веб-версия не отдаёт файл (нужен Telethon)" % node_text(pn).strip(), "document/music '%s' — web preview exposes no file (needs Telethon)" % node_text(pn).strip()))
    text = None
    for tn in walk(node):
        if has_cls(tn, "tgme_widget_message_text") or cls_has(tn, "js-message_text") or has_cls(tn, "tgme_widget_message_rich_text") or has_cls(tn, "rich_text"):
            html_inner = inner_html(tn)
            if html_inner.strip():
                who = ""
                for on in walk(node):
                    if has_cls(on, "tgme_widget_message_owner_name"):
                        who = node_text(on).strip()
                        break
                when = ""
                for tm in walk(node):
                    if tm.tag == "time" and tm.attrs.get("datetime"):
                        when = tm.attrs["datetime"]
                        break
                text = make_text_item(html_inner, "%s #%s" % (chan, mid), sub, nm, base, ("%s · %s" % (who, when)).strip(" ·"))
            break
    return out, text, notes


def telegraph_item(url, sub):
    # статья Telegraph/Instant View → форматированный текст
    path = urlparse(url).path.strip("/")
    d = get_json("https://api.telegra.ph/getPage/%s?return_content=true" % quote(path))
    res = d.get("result") or {}

    def render(nd):
        if isinstance(nd, str):
            return html.escape(nd, quote=False)
        a = "".join(' %s="%s"' % (k, html.escape(v, quote=True)) for k, v in (nd.get("attrs") or {}).items())
        t = nd.get("tag", "span")
        return "<%s%s>%s</%s>" % (t, a, "".join(render(c_) for c_ in nd.get("children", [])), t) if t not in VOID else "<%s%s>" % (t, a)
    body = "".join(render(c_) for c_ in res.get("content", []))
    return make_text_item("<h1>%s</h1>%s" % (html.escape(res.get("title", "")), body), res.get("title") or path, sub, "tgph_" + sanitize(path), url, res.get("author_name", ""))


def tg_fetch_message(chan, mid):
    # embed → t.me/s → обычная страница (og-теги)
    last = None
    for u in ("https://t.me/%s/%s?embed=1&mode=tme" % (chan, mid), "https://t.me/s/%s/%s" % (chan, mid)):
        try:
            htm = get_text(u, headers=TG_UA)
            root, nodes = tg_message_nodes(htm)
            nodes = [x for x in nodes if x.attrs.get("data-post", "").endswith("/" + str(mid))] or nodes
            if nodes:
                return nodes
            if "tgme_widget_message_error" in htm:
                last = IOError("post not found or private")
        except Exception as e:
            last = e
            dlog("tg fetch %s failed: %s" % (u, e), "WARN")
    if last:
        raise last
    return []


def tg_channel_posts(chan, limit=20):
    nodes, before = [], None
    for _ in range(max(1, limit // 15 + 1)):
        u = "https://t.me/s/%s" % chan + (("?before=%s" % before) if before else "")
        htm = get_text(u, headers=TG_UA)
        _, ns = tg_message_nodes(htm)
        if not ns:
            break
        nodes = ns + nodes
        ids = [int(x.attrs["data-post"].split("/")[1]) for x in ns if x.attrs.get("data-post", "/").split("/")[-1].isdigit()]
        if not ids or len(nodes) >= limit:
            break
        before = min(ids)
    return nodes[-limit:]


def tg_avatar(name, sub):
    t = get_text("https://t.me/%s" % name, headers=TG_UA)
    u = og_meta(t, "og:image")
    if not u or "telegram.org/img" in u:
        return []
    return [mkitem("photo", u, "avatar " + name, "https://t.me/", "avatar_%s.jpg" % sanitize(name), sub)]


def soc_telegram(url, want="auto"):
    p = urlparse(url)
    if (p.hostname or "").endswith(("telegra.ph", "graph.org")):
        return [telegraph_item(url, "social/telegram/telegraph")]
    parts = [x for x in p.path.split("/") if x]
    if parts and parts[0] == "s":
        parts = parts[1:]
    if not parts:
        return []
    if parts[0] == "c":
        raise IOError(L("Приватный канал (t.me/c/…) недоступен без входа — используйте Telethon", "Private channel (t.me/c/…) needs a login — use Telethon"))
    chan = parts[0]
    sub = "social/telegram/" + sanitize(chan)
    if len(parts) >= 2 and parts[1].isdigit():
        nodes = tg_fetch_message(chan, parts[1])
    else:
        out = tg_avatar(chan, sub)
        nodes = tg_channel_posts(chan, ST.g("playlist_limit") or 20)
        if not nodes and not out:
            raise IOError(L("Канал закрыт для веб-просмотра или не существует", "Channel is not web-previewable or does not exist"))
        return out + _tg_collect(nodes, sub, want, url)
    return _tg_collect(nodes, sub, want, url)


def _tg_collect(nodes, sub, want, url):
    items, hints = [], []
    for nd in nodes:
        media, text, notes = tg_items_from_node(nd, sub)
        items += media
        hints += notes
        if text and (want in ("text", "auto", "photo", "video", "audio")):
            items.append(text)
        for lk in (a for a in walk(nd) if a.tag == "a" and re.match(r"https?://(telegra\.ph|graph\.org)/", a.attrs.get("href", ""))):
            try:
                items.append(telegraph_item(lk.attrs["href"], sub + "/articles"))
            except Exception as e:
                dlog("telegraph failed: %s" % e, "WARN")
    for h in dict.fromkeys(hints):
        print("[*] " + h)
        if telethon_ready():
            items.append(mkitem("video", url, L("файл через Telethon", "file via Telethon"), None, None, sub, src="telethon"))
            break
    return items


# ---------- Telethon (по желанию): музыка, документы, приватные чаты ----------
TG_SESSION = CONF / "tg_session.txt"


def telethon_installed():
    try:
        import telethon  # noqa
        return True
    except Exception:
        return False


def telethon_ready():
    c_ = ST.d.get("_tg", {})
    return telethon_installed() and bool(c_.get("api_id") and c_.get("api_hash") and (TG_SESSION.exists() or Path(str(TG_SESSION) + ".tkv").exists()))


def _tg_session_str():
    try:
        if Path(str(TG_SESSION) + ".tkv").exists():
            return v_decrypt(Path(str(TG_SESSION) + ".tkv").read_bytes()).decode()
        return TG_SESSION.read_text().strip()
    except Exception:
        return ""


def _tg_session_save(s):
    if ST.g("encrypt_cookies"):
        Path(str(TG_SESSION) + ".tkv").write_bytes(v_encrypt(s.encode()))
        if TG_SESSION.exists():
            TG_SESSION.unlink()
    else:
        TG_SESSION.write_text(s)
        os.chmod(str(TG_SESSION), 0o600)


def tg_client():
    from telethon.sync import TelegramClient
    from telethon.sessions import StringSession
    c_ = ST.d.get("_tg", {})
    kw = {}
    pr = parse_proxy_url(proxy_url())
    if pr and pr[1]:
        try:
            import socks
            kw["proxy"] = ({"socks5": socks.SOCKS5, "socks5h": socks.SOCKS5, "http": socks.HTTP}.get(pr[0], socks.HTTP), pr[1], pr[2], True, pr[3], pr[4])
        except Exception:
            print("[*] " + L("PySocks не установлен — Telethon без прокси", "PySocks missing — Telethon without proxy"))
    return TelegramClient(StringSession(_tg_session_str()), int(c_["api_id"]), c_["api_hash"], **kw)


def tg_login():
    # однократный вход в Telegram (api_id/api_hash берутся на my.telegram.org)
    c_ = ST.d.get("_tg", {})
    print(dim(L("api_id и api_hash: https://my.telegram.org → API development tools. Сессия хранится локально (StringSession, без sqlite).", "api_id and api_hash: https://my.telegram.org → API development tools. Session stored locally (StringSession, no sqlite).")))
    c_["api_id"] = ask("api_id", str(c_.get("api_id", "")), quit_ok=False)
    c_["api_hash"] = ask("api_hash", c_.get("api_hash", ""), quit_ok=False)
    phone = ask(L("Телефон (+7…)", "Phone (+1…)"), c_.get("phone", ""), quit_ok=False)
    c_["phone"] = phone
    ST.d["_tg"] = c_
    ST.save()
    cl = tg_client()
    with Spin(L("Подключаюсь к Telegram", "Connecting to Telegram"), quiet=True):
        cl.connect()
    if not cl.is_user_authorized():
        cl.send_code_request(phone)
        code = ask(L("Код из Telegram", "Code from Telegram"), "", quit_ok=False)
        try:
            cl.sign_in(phone, code)
        except Exception as e:
            if "password" in str(e).lower() or "SessionPasswordNeeded" in type(e).__name__:
                cl.sign_in(password=ask(L("Пароль 2FA", "2FA password"), "", quit_ok=False))
            else:
                raise
    _tg_session_save(cl.session.save())
    audit("telegram-login", phone[:4] + "***")
    cl.disconnect()
    print("[+] " + L("Вход выполнен", "Logged in"))


def tg_telethon_download(link, sub="social/telegram"):
    # скачать пост ссылкой через Telethon: фото/видео/кружки/голосовые/музыка/файлы + текст с форматированием
    m = re.search(r"t\.me/(c/)?([^/]+)/(\d+)", link)
    if not m:
        raise IOError("bad telegram link")
    ent = int("-100" + m.group(2)) if m.group(1) else m.group(2)
    mid = int(m.group(3))
    cl = tg_client()
    with Spin(L("Telethon: подключение", "Telethon: connecting"), quiet=True):
        cl.connect()
    try:
        msg = cl.get_messages(ent, ids=mid)
        if not msg:
            raise IOError("message not found")
        group = [msg]
        if getattr(msg, "grouped_id", None):
            near = cl.get_messages(ent, ids=list(range(mid - 9, mid + 10)))
            group = [x for x in near if x and x.grouped_id == msg.grouped_id] or [msg]
        d = outdir("video") / sub
        d.mkdir(parents=True, exist_ok=True)
        paths = []
        for x in group:
            if x.media:
                bar = [None]

                def cb(cur, tot):
                    if bar[0] is None:
                        bar[0] = Bar(tot, "telegram", "B")
                    bar[0].update(cur)
                p = cl.download_media(x, file=str(d) + "/", progress_callback=cb)
                if bar[0]:
                    bar[0].close()
                if p:
                    paths.append(p)
        txt = next((x for x in group if x.raw_text), None)
        if txt:
            try:
                from telethon.extensions import html as thtml
                htm = thtml.unparse(txt.raw_text, txt.entities or [])
            except Exception:
                htm = html.escape(txt.raw_text).replace("\n", "<br>")
            it = make_text_item(htm, "%s #%s" % (m.group(2), mid), sub, "tg_%s_%s" % (sanitize(m.group(2)), mid), "https://t.me/")
            paths.append(write_text_item(it))
        return True, "%s (%d)" % (d, len(paths)) if paths else (False, "no media")
    finally:
        cl.disconnect()


def write_text_item(it):
    # сохранить текстовый элемент в texts/<sub>/: .html (шрифты/размеры), .md, .txt, .json — по настройке tg_text
    d = outdir("text") / (it.get("sub") or "social")
    d.mkdir(parents=True, exist_ok=True)
    fm = ST.g("tg_text")
    base = sanitize(it.get("name") or "text")
    first = None
    for ext, key, on in (("html", "html", fm in ("all", "html")), ("md", "md", fm in ("all", "md")), ("txt", "txt", fm in ("all", "txt")), ("rich.json", "tree", fm == "all")):
        if on and it.get(key):
            p = d / ("%s.%s" % (base, ext))
            p.write_text(it[key], "utf-8")
            first = first or p
    return first


# ==========================================================================
#  Диспетчер и профили
# ==========================================================================
def soc_dispatch(kind):
    return {"instagram": soc_instagram, "tiktok": soc_tiktok, "threads": soc_threads, "likee": soc_likee, "twitter": soc_twitter, "facebook": soc_generic_page,
            "reddit": soc_reddit, "pinterest": soc_pinterest, "telegram": soc_telegram, "bluesky": soc_bluesky, "vk": soc_generic_page, "gallery": soc_gallery, "boosty": soc_boosty}.get(kind)


def social_resolve(url, want="auto"):
    # адрес → (элементы, платформа). NeedLogin пробрасывается наверх
    kind = social_kind(url)
    fn = soc_dispatch(kind)
    if not fn:
        return [], kind
    with Spin(L("Разбираю %s" % kind, "Resolving %s" % kind), quiet=True):
        pass
    return fn(url, want), kind


def login_hint(host):
    h = host.replace("www.", "")
    print("[!] " + L("Для этого нужен вход: Сеть → Мастер cookies → %s (вставьте sessionid/Cookie из браузера)." % h, "Login needed: Network → Cookies wizard → %s (paste sessionid/Cookie from the browser)." % h))


PLATFORMS = ["instagram", "tiktok", "threads", "twitter", "telegram", "bluesky", "youtube", "github"]


def social_profile(platform, user, what):
    # what: avatar / stories / highlights / posts → список элементов
    user = user.strip().lstrip("@")
    sub = "social/%s/%s" % (platform, sanitize(user))
    if platform == "instagram":
        return {"avatar": lambda: ig_avatar(user, sub), "stories": lambda: ig_stories(user, sub), "highlights": lambda: ig_highlights(user, sub), "posts": lambda: ig_posts(user, sub)}[what]()
    if platform == "tiktok":
        return tt_avatar(user, sub) if what == "avatar" else tt_posts(user, sub)
    if platform == "threads":
        return soc_threads("https://www.threads.net/@%s" % user)
    if platform == "twitter":
        return soc_twitter("https://x.com/%s" % user)
    if platform == "telegram":
        return tg_avatar(user, sub) if what == "avatar" else _tg_collect(tg_channel_posts(user, ST.g("playlist_limit") or 20), sub, "auto", "https://t.me/%s" % user)
    if platform == "bluesky":
        return soc_bluesky("https://bsky.app/profile/%s" % user)
    if platform == "youtube":
        t = get_text("https://www.youtube.com/@%s" % user, headers={"User-Agent": UA_DESK})
        u = og_meta(t, "og:image")
        return [mkitem("photo", u, "avatar " + user, None, "avatar_%s.jpg" % sanitize(user), sub)] if u else []
    if platform == "github":
        return [mkitem("photo", "https://github.com/%s.png?size=460" % quote(user), "avatar " + user, None, "avatar_%s.png" % sanitize(user), sub)]
    return []


# ==========================================================================
#  ПЛАНИРОВАНИЕ (вопросы только здесь) → ЗАГРУЗКА БЕЗ ВОПРОСОВ
# ==========================================================================
def mkjob(url, kind, title="", src="ytdlp", typ=None, referer=None, dur=None, **extra):
    j = {"url": url, "kind": kind, "title": title or url, "src": src, "type": typ or kind, "referer": referer, "dur": dur}
    j.update({k: v for k, v in extra.items() if v is not None})
    return j


def item_to_job(it, page_url=None):
    # элемент соцсети/страницы → задание очереди
    t = it["type"]
    if t == "text":
        return mkjob(it["url"], "text", it["title"], "text", "text", sub=it.get("sub"), name=it.get("name"), html=it.get("html"), md=it.get("md"), txt=it.get("txt"), tree=it.get("tree"))
    if it.get("src") in ("telethon", "gallery", "ytdlp", "music"):
        return mkjob(it["url"], it.get("jkind", it["type"]), it["title"], it["src"], it["type"], sub=it.get("sub"), meta=it.get("meta"), query=it.get("query"), alts=it.get("alts"))
    return mkjob(it["url"], t, it["title"], "direct", t, referer=it.get("referer") or page_url, dur=it.get("dur"), sub=it.get("sub"), name=it.get("name"), headers=it.get("headers"), alts=it.get("alts"))


def select_items(items, what="auto"):
    # показать найденные медиа и дать выбрать (номера / all / v / a / p / t); режим ask_selection из настроек
    if len(items) <= 1:
        return items
    names = {"video": L("видео", "video"), "audio": L("аудио", "audio"), "photo": L("фото", "photo"), "text": L("текст", "text"), "file": L("файлы", "files")}
    cnt = {t: sum(1 for i in items if i["type"] == t) for t in names}
    print("[*] %s: %s" % (L("Найдено", "Found"), ", ".join("%s %d" % (names[t], n) for t, n in cnt.items() if n)))
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
        v = ask(L("Что скачать", "What to download"), "all", quit_ok=False, hint=L("номера 1,3-5 · all · v видео · a аудио · p фото · t текст · f файлы · b — пропустить", "numbers 1,3-5 · all · v video · a audio · p photo · t text · f files · b = skip")).lower()
        if v in ("b", "back"):
            return []
        flt = {"v": "video", "a": "audio", "p": "photo", "t": "text", "f": "file"}.get(v)
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
    if proxy_url():
        o["proxy"] = proxy_url()
    ck = cookies_for(urlparse(url).netloc)
    if ck:
        o["cookiefile"] = ck
    if ST.g("playlist_limit"):
        o["playlistend"] = ST.g("playlist_limit")
    if (urlparse(url).hostname or "") in INSECURE:
        o["nocheckcertificate"] = True
    with yt_dlp.YoutubeDL(o) as y:
        return y.extract_info(url, download=False)


def try_social(url, kind, sk):
    # свой разбор соцсети с понятными сообщениями; NeedLogin → подсказка про cookies
    want = kind if kind in ("video", "audio", "photo", "text") else "auto"
    try:
        items, _ = social_resolve(url, want)
    except NeedLogin as e:
        login_hint(str(e) or sk)
        return []
    except KeyboardInterrupt:
        raise
    except Exception as e:
        note_error(url, e)
        print("[!] %s: %s" % (sk, trunc(str(e), term_w() - 14)))
        return []
    if want in ("video", "audio", "photo", "text"):
        flt = [i for i in items if i["type"] == want]
        items = flt or items
    return items


def plan_url(url, kind):
    # анализ одной ссылки → задания (вопрос о выборе — только если медиа несколько)
    if not ensure_internet(L("анализ ссылки", "link analysis")):
        return []
    host = (urlparse(url).hostname or "").lower()
    sk = social_kind(url)
    e = ext_of(url.split("?")[0])
    if type_of_ext(e):
        t = type_of_ext(e)
        return [mkjob(url, t if kind == "auto" else kind, Path(urlparse(url).path).name, "direct", t)]
    social_tried = False
    if sk in CUSTOM_FIRST:
        social_tried = True
        its = try_social(url, kind, sk)
        if its:
            return [item_to_job(i, url) for i in select_items(its, kind)]
    if music_kind(url) and kind in ("audio", "auto") and music_kind(url) != "vkaudio":
        try:
            its = music_resolve(url)
            if its:
                return [item_to_job(i, url) for i in select_items(its, "audio")]
        except Exception as ex:
            note_error(url, ex)
    if creator_kind(url) and creator_kind(url) != "boosty":
        try:
            return [item_to_job(i, url) for i in creator_resolve(url)]
        except NeedLogin as ex:
            login_hint(str(ex))
    alts = [{"src": "social", "url": url, "kind": kind, "type": "video", "title": url}] if sk in ALT_SOCIAL else None
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
                        k2 = "audio" if kind == "audio" else "video"
                        items.append(mkjob(u, k2, x.get("title") or u, "ytdlp", k2, dur=x.get("duration"), alts=alts))
                if len(items) > 1:
                    print("[+] %s: %s" % (L("Плейлист/канал", "Playlist/channel"), trunc(info.get("title") or url, 40)))
            elif info:
                k2 = "audio" if kind == "audio" else "video"
                items = [mkjob(url, k2, info.get("title") or url, "ytdlp", k2, dur=info.get("duration"), alts=alts)]
        except KeyboardInterrupt:
            raise
        except Exception as ex:
            err = ANSI_RE.sub("", str(ex))[:200]
            note_error(url, err)
            if any(w in err.lower() for w in FATAL):
                print("[!] " + trunc(err, term_w() - 6))
                return []
            if "youtube" in host or "youtu.be" in host:
                items = [mkjob(url, "audio" if kind == "audio" else "video", url, "ytdlp")]
        if items:
            sel = select_items([dict(i, type=i["type"]) for i in items], kind)
            return sel
    media = []
    if kind in ("photo", "auto") and "youtube" not in host and sk != "telegram":
        with Spin(L("gallery-dl: список медиа", "gallery-dl: listing media"), quiet=True):
            try:
                urls, gerr = gallery_list(url)
            except Exception:
                urls, gerr = [], ""
        for u in urls:
            ee = ext_of(u.split("?")[0])
            media.append({"type": type_of_ext(ee) or "photo", "url": u, "title": unquote(Path(urlparse(u).path).name) or u[-30:]})
        if not media and gerr and ("login" in gerr.lower() or "401" in gerr or "403" in gerr) and not cookies_for(host):
            login_hint(host)
    if not media:
        pages = [url]
        for pg in pages:
            try:
                with Spin(L("Разбор страницы", "Parsing page"), quiet=True):
                    inv = page_inventory(pg)
                media = [dict(i, title=i["title"]) for i in inv["items"]]
                if inv["text"] and kind in ("auto", "text"):
                    media.append(inv["text"])
            except KeyboardInterrupt:
                raise
            except Exception as ex:
                err = str(ex)
                note_error(pg, ex)
                media = []
            if media:
                break
        if not media:
            wb = busy(L("Ищу копию в Wayback Machine", "Looking for a Wayback copy"), wayback_url, url)
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
        return [item_to_job(m, url) if "type" in m else mkjob(m["url"], m["type"], m["title"], "direct", m["type"], referer=url) for m in sel]
    if sk and not social_tried:
        its = try_social(url, kind, sk)
        if its:
            return [item_to_job(i, url) for i in select_items(its, kind)]
    if kind == "photo":
        return [mkjob(url, "photo", url, "gallery")]
    print("[!] %s %s" % (L("Медиа не найдено:", "No media found:"), trunc(err or url, term_w() - 24)))
    print(dim("    " + L("Подсказка: меню «Отладка» → «Анализ ссылки» покажет, что нашёл каждый способ.", "Hint: 'Debug' menu → 'Analyze link' shows what each method found.")))
    return []


def _do_one(job):
    src, url = job["src"], job["url"]
    if src == "ytdlp":
        return ytdlp_chain(url, "audio" if job.get("kind") == "audio" else "video", job.get("q"))
    if src == "gallery":
        return gallery_whole(url)
    if src == "text":
        p = write_text_item(job)
        return (True, str(p)) if p else (False, "empty text")
    if src == "telethon":
        return tg_telethon_download(url, job.get("sub") or "social/telegram")
    if src == "music":
        return music_download(job)
    if src == "social":
        items, _ = social_resolve(url, job.get("kind", "auto"))
        if not items:
            return False, "social: nothing found"
        ok_n, last = 0, ""
        for it in items:
            ok, res = _do_one(item_to_job(it, url))
            ok_n += 1 if ok else 0
            last = res
        return (ok_n > 0), (last if ok_n else "social: all failed")
    typ = job.get("type") or "video"
    d = outdir(typ)
    if job.get("sub"):
        d = d / job["sub"]
    if ext_of(url.split("?")[0]) == ".m3u8" or url.endswith("playlist.m3u8"):
        return True, str(hls_download(url, "audio" if typ == "audio" else "video", job.get("referer")))
    return True, str(dl_direct(url, d, job.get("referer"), name=job.get("name"), headers=job.get("headers")))


def do_job(job):
    # основное задание + запасные (alts), если основное не удалось
    last = ""
    if DRY[0]:
        print("[dry-run] %s %s" % (job.get("src"), trunc(job["url"], term_w() - 20)))
        return True, "(dry-run)"
    for j in [job] + list(job.get("alts") or []):
        try:
            ok, res = _do_one(dict(job, **j) if j is not job else j)
        except KeyboardInterrupt:
            raise
        except NeedLogin as e:
            login_hint(str(e))
            ok, res = False, "login_required"
        except Exception as ex:
            ok, res = False, str(ex)[:200]
        if ok:
            return True, res
        last = res
        note_error(j.get("url", ""), res)
    return False, last


# ---------- постобработка: дедупликация, метаданные, раскладка, сводка, статистика ----------
def hash_file(p, limit=3 * 1024 ** 3):
    if p.stat().st_size > limit:
        return None
    h = hashlib.sha256()
    with open(str(p), "rb") as f:
        for ch in iter(lambda: f.read(1 << 20), b""):
            h.update(ch)
    return h.hexdigest()


def ffprobe_json(p):
    if not shutil.which("ffprobe"):
        return {}
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration:format_tags=artist,album,title:stream=codec_name,width,height,codec_type", "-of", "json", str(p)], timeout=60)
    try:
        return json.loads(r.stdout.decode("utf-8", "replace"))
    except Exception:
        return {}


def strip_metadata(p):
    ex = shutil.which("exiftool")
    if ex:
        return subprocess.run([ex, "-all=", "-overwrite_original", str(p)], timeout=120).returncode == 0
    if p.suffix.lower() in IEXT and im_prefix():
        return subprocess.run(im_prefix() + [str(p), "-strip", str(p)], timeout=120).returncode == 0
    if have_ffmpeg() and p.suffix.lower() in VEXT | AEXT:
        t = p.with_name(p.stem + ".strip" + p.suffix)
        if ff_run(["-i", p, "-map_metadata", "-1", "-c", "copy", t], "strip") == 0:
            os.replace(str(t), str(p))
            return True
    return False


def sort_into_folders(p, typ):
    info = ffprobe_json(p) if typ in ("video", "audio") else {}
    if typ == "video":
        d = float((info.get("format") or {}).get("duration") or 0)
        sub = "shorts" if 0 < d < 60 else ("long" if d > 3600 else "")
    elif typ == "audio":
        tg = (info.get("format") or {}).get("tags") or {}
        tg = {k.lower(): v for k, v in tg.items()}
        sub = "/".join(sanitize(x) for x in (tg.get("artist"), tg.get("album")) if x)
    else:
        sub = ""
    if not sub:
        return p
    dst = p.parent / sub
    dst.mkdir(parents=True, exist_ok=True)
    q = uniq(dst / p.name)
    os.replace(str(p), str(q))
    return q


def make_summary(p):
    info = ffprobe_json(p)
    fm = info.get("format") or {}
    vs = [s for s in info.get("streams", []) if s.get("codec_type") == "video"]
    lines = ["file: %s" % p.name, "size: %s" % fmt_size(p.stat().st_size), "duration: %s" % fmt_dur(float(fm.get("duration") or 0))]
    if vs:
        lines.append("video: %s %sx%s" % (vs[0].get("codec_name"), vs[0].get("width"), vs[0].get("height")))
    for k, v in ((fm.get("tags") or {})).items():
        lines.append("%s: %s" % (k, v))
    srt = next(iter(p.parent.glob(p.stem + "*.srt")), None)
    if srt:
        txt = []
        for blk in srt.read_text("utf-8", "replace").split("\n\n")[:12]:
            ls = blk.strip().split("\n")
            if len(ls) >= 3:
                txt.append(" ".join(ls[2:]))
        lines += ["", "subtitles (start):", "\n".join(txt)]
    p.with_suffix(".summary.txt").write_text("\n".join(lines) + "\n", "utf-8")
    dur = float(fm.get("duration") or 0)
    if vs and dur > 5 and have_ffmpeg():
        ff_run(["-i", p, "-vf", "fps=1/%d,scale=160:-1,tile=3x3" % max(1, int(dur / 9)), "-frames:v", "1", p.with_suffix(".grid.jpg")], "grid")


def stats_add(p, typ):
    s = jload(STATS, {"files": 0, "bytes": 0, "by_type": {}, "by_site": {}, "by_day": {}})
    sz = p.stat().st_size
    s["files"] += 1
    s["bytes"] += sz
    s["by_type"][typ] = s["by_type"].get(typ, 0) + 1
    day = time.strftime("%Y-%m-%d")
    s["by_day"][day] = s["by_day"].get(day, 0) + 1
    jsave(STATS, s)


def postprocess(res, job):
    # (путь, заметка): дубликаты → метаданные → раскладка → сводка → статистика
    try:
        p = Path(str(res).split(" (")[0])
        if not p.is_file():
            return res, ""
        typ = job.get("type") or "video"
        notes = []
        if ST.g("auto_dedupe") and typ != "text":
            with Spin(L("Проверка дубликатов", "Checking duplicates"), quiet=True):
                h = hash_file(p)
            if h:
                idx = jload(HASHES, {})
                old = idx.get(h)
                if old and old != str(p) and Path(old).exists():
                    p.unlink()
                    print("[*] " + L("Дубликат — оставлен прежний файл: ", "Duplicate — kept the existing file: ") + trunc(old, term_w() - 40))
                    return old, "dup"
                idx[h] = str(p)
                jsave(HASHES, idx)
        if ST.g("strip_meta") and typ != "text":
            ok = busy(L("Стираю метаданные", "Stripping metadata"), strip_metadata, p)
            notes.append("meta-stripped" if ok else "strip-failed")
        if ST.g("sort_content") and typ in ("video", "audio"):
            p = busy(L("Раскладываю по содержимому", "Sorting by content"), sort_into_folders, p, typ)
        if ST.g("summary") and typ == "video":
            busy(L("Создаю сводку", "Creating summary"), make_summary, p)
        stats_add(p, typ)
        return str(p), ",".join(notes)
    except KeyboardInterrupt:
        raise
    except Exception as e:
        dlog("postprocess failed: %s" % e, "WARN")
        return res, ""


def build_library_html():
    # index.html медиатеки: карточки с поиском (фото/видео/аудио/тексты)
    rows = []
    for kind, folder in (("video", "videos"), ("audio", "audio"), ("photo", "photos"), ("text", "texts")):
        root = BASE / folder
        for r, ds, fs in os.walk(str(root)):
            ds[:] = [d for d in ds if not d.startswith(".")]
            if Path(r).relative_to(root).parts.__len__() > 5:
                continue
            for f in fs:
                if f.startswith(".") or f.endswith((".part", ".summary.txt")):
                    continue
                p = Path(r) / f
                rel = os.path.relpath(str(p), str(BASE))
                rows.append((kind, rel, p.stat().st_size, p.stat().st_mtime))
    rows.sort(key=lambda x: -x[3])
    cards = []
    for kind, rel, sz, mt in rows[:3000]:
        href = quote(rel)
        if kind == "photo":
            th = '<img loading=lazy src="%s">' % href
        elif kind == "video":
            th = '<video preload=metadata src="%s#t=0.5" controls></video>' % href
        elif kind == "audio":
            th = '<audio src="%s" controls></audio>' % href
        else:
            th = '<div class=txt>📝</div>'
        cards.append('<div class="c" data-n="%s"><a href="%s">%s</a><div class=n>%s</div><div class=m>%s · %s</div></div>' % (html.escape(rel.lower()), href, th, html.escape(os.path.basename(rel)), fmt_size(sz), time.strftime("%Y-%m-%d", time.localtime(mt))))
    doc = ("<!doctype html><meta charset=utf-8><meta name=viewport content='width=device-width,initial-scale=1'><title>MediaForge</title><style>body{font:15px system-ui;margin:1em;background:#16181c;color:#eee}"
           "input{width:100%%;padding:.6em;font-size:1em;border-radius:8px;border:0;margin-bottom:1em}.g{display:grid;grid-template-columns:repeat(auto-fill,minmax(160px,1fr));gap:10px}"
           ".c{background:#22262c;border-radius:10px;padding:6px;overflow:hidden}img,video{width:100%%;border-radius:8px}.n{font-size:.8em;word-break:break-all}.m{opacity:.6;font-size:.75em}a{color:inherit}.txt{font-size:3em;text-align:center}</style>"
           "<input id=q placeholder='search…' oninput=\"for(const e of document.querySelectorAll('.c'))e.style.display=e.dataset.n.includes(this.value.toLowerCase())?'':'none'\"><div class=g>%s</div>" % "".join(cards))
    (BASE / "index.html").write_text(doc, "utf-8")
    return BASE / "index.html", len(rows)


# ==========================================================================
#  ВЫПОЛНЕНИЕ: очередь без вопросов, повтор, сводка, подсказки по исправлению
# ==========================================================================
def run_jobs(jobs, depth=0):
    # загрузка без вопросов: очередь сохраняется, неудачные повторяются, затем меню починки причин
    if not jobs:
        return []
    if not ensure_internet(L("загрузка", "download")):
        jsave(QUEUE, {"jobs": jobs})
        print("[!] " + L("Очередь сохранена — запустите позже (меню «Очередь»).", "Queue saved — run it later ('Queue' menu)."))
        return jobs
    UNATT[0] = True
    jsave(QUEUE, {"jobs": jobs})
    results, pending = [], list(jobs)
    fail_info = {}
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
                if ST.g("skip_history") and hist_done(j["url"]) and j.get("src") != "text":
                    print("[*] " + L("Уже скачано — пропуск", "Already downloaded — skipped"))
                    results.append((j, "skip", ""))
                    continue
                ok, res = do_job(j)
                if ok:
                    res, note = postprocess(res, j)
                    if note == "corrupt":
                        ok, res = False, "corrupted download"
                if ok:
                    print("[+] %s %s" % (L("Готово:", "Done:"), trunc(res, term_w() - 14)))
                    hist_add(j["url"], j["title"], res, "ok")
                    results.append((j, "ok", res))
                    fail_info.pop(j["url"], None)
                else:
                    cat, ru, en = classify_error(res, j["url"])
                    print("[!] [%s] %s" % (cat, trunc(L(ru, en), term_w() - 12)))
                    print(dim("    " + trunc(str(res), term_w() - 6)))
                    failed.append(j)
                    fail_info[j["url"]] = res
                    if rnd == ST.g("retry_rounds") - 1:
                        hist_add(j["url"], j["title"], "", "fail")
                        results.append((j, "fail", res))
                done_urls = {r[0]["url"] for r in results}
                jsave(QUEUE, {"jobs": [x for x in jobs if x["url"] not in done_urls]})
                if i < len(pending):
                    slow = any(h in j["url"] for h in SLOW_HOSTS)
                    wait = ST.g("sleep_between") + (random.uniform(0.5, 1.5) * ST.g("sleep_slow") if slow else 0)
                    if wait > 0.5:
                        with Spin(L("Пауза %.0f с (чтобы не заблокировали)" % wait, "Pause %.0f s (avoid blocks)" % wait), quiet=True):
                            time.sleep(wait)
            pending = failed
            if not pending:
                break
            w = 5 * (rnd + 1)
            with Spin(L("Повтор неудачных (%d) через %d с" % (len(pending), w), "Retrying failed (%d) in %d s" % (len(pending), w)), quiet=True):
                time.sleep(w)
    except KeyboardInterrupt:
        print("\n[!] " + L("Прервано. Очередь сохранена (меню «Очередь»). Возврат в меню.", "Interrupted. Queue saved ('Queue' menu). Back to the menu."))
        UNATT[0] = False
        return [j for j in jobs if j["url"] not in {r[0]["url"] for r in results}]
    UNATT[0] = False
    jsave(QUEUE, {"jobs": [j for j in jobs if j in pending]})
    ok_n, sk_n, fl_n = (sum(1 for r in results if r[1] == s) for s in ("ok", "skip", "fail"))
    print("\n" + box([grad(L("Итог", "Summary"), 0, True),
                      "%s %d   %s %d   %s %d   %s" % (c(L("успешно", "ok"), OK_C, True), ok_n, c(L("пропущено", "skipped"), WARN_C), sk_n, c(L("ошибок", "failed"), ERR_C, True), fl_n, dim(fmt_dur(time.time() - t0)))]))
    for j, st, res in results:
        if st == "fail":
            print("  " + c("✗ ", ERR_C) + trunc(j["title"], 30) + dim(" — " + trunc(res, term_w() - 40)))
    jsave(BASE / "reports" / ("report_%s.json" % now_stamp()), [{"url": j["url"], "title": j["title"], "status": s, "result": r} for j, s, r in results])
    if ok_n and ST.g("library_html"):
        busy(L("Обновляю index.html", "Updating index.html"), build_library_html)
    if ST.g("bell"):
        sys.stdout.write("\a")
        sys.stdout.flush()
    bad = [(j, res) for j, st, res in results if st == "fail"]
    if bad and ST.g("remedy") and depth < 2 and sys.stdin.isatty():
        again = remedy_menu(bad)
        if again:
            return run_jobs(again, depth + 1)
    return [j for j, _ in bad]


def remedy_menu(bad):
    # группировка ошибок по причинам и способы починки
    groups = collections.defaultdict(list)
    for j, e in bad:
        groups[classify_error(e, j["url"])[0]].append(j)
    print("\n" + c(L("Причины ошибок", "Failure causes"), accent(), True))
    for cat, js in groups.items():
        sample = next(e for j, e in bad if classify_error(e, j["url"])[0] == cat)
        print("  %s ×%d  %s" % (c(cat, WARN_C, True), len(js), dim(trunc(L(*classify_error(sample)[1:]), term_w() - 14))))
    while True:
        k = menu(L("Что сделать с неудачными (%d)?" % len(bad), "What to do with failed (%d)?" % len(bad)), [
            ("1", L("Повторить сразу", "Retry now"), ""), ("2", L("Повторить через DoH-DNS", "Retry via DoH DNS"), L("если dns / reset", "if dns / reset")),
            ("3", L("Повторить без проверки TLS для этих хостов", "Retry without TLS check for these hosts"), L("если tls", "if tls")),
            ("4", L("Найти лучший прокси и повторить", "Find best proxy and retry"), L("если proxy / timeout / reset", "if proxy / timeout / reset")),
            ("5", L("Мастер cookies (вход в аккаунт)", "Cookies wizard (account login)"), L("если auth", "if auth")),
            ("6", L("Сохранить неудачные в «Список ссылок»", "Save failed to the 'Links list'"), "")], back=L("Закончить", "Finish"), show=False)
        if k == "q":
            return []
        jobs = [j for j, _ in bad]
        if k == "1":
            return jobs
        if k == "2":
            ST.ov["dns_mode"] = "doh"
            DNS_CACHE.clear()
            return jobs
        if k == "3":
            for j in jobs:
                INSECURE.add(urlparse(j["url"]).hostname or "")
            audit("tls-insecure-batch", ",".join(sorted(INSECURE))[:150])
            return jobs
        if k == "4":
            if find_best_proxy():
                return jobs
        if k == "5":
            cookies_wizard()
        if k == "6":
            links_add([j["url"] for j in jobs], "auto")
            print("[+] " + L("Сохранено в список ссылок", "Saved to the links list"))


# ==========================================================================
#  ПАМЯТЬ ССЫЛОК: добавляй сейчас — качай потом
# ==========================================================================
LINKS = CONF / "links.json"
URL_RE = re.compile(r"https?://[^\s\"'<>]+")


def links_load():
    d = jload(LINKS, [])
    return d if isinstance(d, list) else []


def links_save(lst):
    jsave(LINKS, lst)


def links_add(urls, kind="auto", note=""):
    # добавить ссылки в память (дубликаты пропускаются) → сколько добавлено
    lst = links_load()
    have = {x["url"] for x in lst}
    n = 0
    for u in urls:
        if u and u not in have:
            lst.append({"url": u, "kind": kind, "added": time.strftime("%Y-%m-%d %H:%M"), "note": note, "status": "new", "err": ""})
            have.add(u)
            n += 1
    links_save(lst)
    return n


def read_clipboard():
    try:
        return open("/dev/clipboard", "rb").read().decode("utf-8", "replace")
    except Exception:
        return ""


def read_urls(title=None):
    # накопление ссылок: пустая строка — конец ввода; 'clip' — из буфера iOS; путь к .txt — из файла
    print(dim(title or L("Вставляйте ссылки по одной. Пустая строка (Enter) — конец ввода. Также: путь к .txt, 'clip' — из буфера iOS, 'b' — отмена.",
                         "Paste URLs one per line. Blank line (Enter) = end. Also: .txt path, 'clip' = iOS clipboard, 'b' = cancel.")))
    urls = []
    while True:
        v = ask(L("Ссылка", "URL") + " #%d" % (len(urls) + 1), "", quit_ok=True, hint=L("(Enter — готово)", "(Enter = done)"))
        if not v:
            break
        if v.lower() in ("b", "back"):
            return []
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


def plan_many(urls, kind):
    # анализ списка ссылок (все вопросы — здесь) → список заданий без дубликатов
    jobs = []
    for n, u in enumerate(urls, 1):
        print("\n" + c("%s %d/%d" % (L("Анализ", "Analysis"), n, len(urls)), accent(), True) + " " + dim(trunc(u, term_w() - 16)))
        try:
            jobs += plan_url(u, kind)
        except Quit:
            raise
        except KeyboardInterrupt:
            raise Interrupt()
        except Exception as ex:
            note_error(u, ex)
            print("[!] %s" % trunc(str(ex), term_w() - 6))
    seen, out = set(), []
    for j in jobs:
        if j["url"] not in seen:
            seen.add(j["url"])
            out.append(j)
    return out


def run_saved_links(sel_idx=None, only_new=True, kind_override=None):
    # скачать ссылки из памяти: сначала анализ всех (вопросы), затем загрузка без вопросов
    lst = links_load()
    idx = sel_idx if sel_idx is not None else [i for i, x in enumerate(lst) if (x.get("status") != "done" or not only_new)]
    if not idx:
        print("[!] " + L("В списке нет ссылок для загрузки", "No links to download in the list"))
        return
    jobs, owner = [], {}
    print("[*] " + L("Ссылок к загрузке: %d. Сначала анализ (могут быть вопросы), затем загрузка сама." % len(idx), "Links to download: %d. Analysis first (may ask), then it runs on its own." % len(idx)))
    for n, i in enumerate(idx, 1):
        x = lst[i]
        print("\n" + c("%s %d/%d" % (L("Анализ", "Analysis"), n, len(idx)), accent(), True) + " " + dim(trunc(x["url"], term_w() - 16)))
        try:
            js = plan_url(x["url"], kind_override or x.get("kind", "auto"))
        except Quit:
            raise
        except KeyboardInterrupt:
            raise Interrupt()
        except Exception as ex:
            js = []
            x["err"] = str(ex)[:150]
        for j in js:
            owner[j["url"]] = i
        jobs += js
        if not js:
            x["status"] = "fail"
            x["err"] = x.get("err") or "nothing found"
    links_save(lst)
    jobs = [j for k, j in enumerate(jobs) if j["url"] not in {y["url"] for y in jobs[:k]}]
    if not jobs:
        print("[!] " + L("Нечего скачивать", "Nothing to download"))
        return
    left = run_jobs(jobs)
    left_urls = {j["url"] for j in left}
    lst = links_load()
    for j in jobs:
        i = owner.get(j["url"])
        if i is not None and i < len(lst):
            if j["url"] in left_urls:
                lst[i]["status"], lst[i]["err"] = "fail", str(jload(HIST, {}).get(j["url"], {}).get("status", "fail"))
            elif lst[i]["status"] != "fail":
                lst[i]["status"], lst[i]["err"] = "done", ""
    links_save(lst)


# ==========================================================================
#  ПЛАНИРОВЩИК (фоновый процесс без cron)
# ==========================================================================
SCHED_PID = CONF / "scheduler.pid"
SCHED_LOG = CONF / "scheduler.log"


def sched_log(msg):
    try:
        with open(str(SCHED_LOG), "a", encoding="utf-8") as f:
            f.write("%s %s\n" % (time.strftime("%Y-%m-%d %H:%M:%S"), msg))
        if SCHED_LOG.stat().st_size > 1048576:
            os.replace(str(SCHED_LOG), str(SCHED_LOG) + ".1")
    except Exception:
        pass


def scheduler_loop():
    # каждые 30 с проверяет расписание; для канала/плейлиста берёт последние N и скачивает новое (история пропускает старое)
    sched_log("scheduler started pid=%d" % os.getpid())
    UNATT[0] = True
    ST.ov.update({"ask_selection": "all", "playlist_limit": 10, "remedy": False})
    while True:
        try:
            now = time.localtime()
            hm, today = time.strftime("%H:%M", now), time.strftime("%Y-%m-%d", now)
            ent = jload(SCHED, [])
            changed = False
            for e in ent:
                if e.get("time") == hm and e.get("last") != today:
                    e["last"] = today
                    changed = True
                    sched_log("run %s" % e["url"])
                    try:
                        jobs = plan_url(e["url"], e.get("kind", "auto"))
                        run_jobs(jobs)
                    except Exception as ex:
                        sched_log("error %s" % ex)
            if changed:
                jsave(SCHED, ent)
        except Exception as ex:
            sched_log("loop error %s" % ex)
        time.sleep(30)


def scheduler_running():
    try:
        pid = int(SCHED_PID.read_text())
        os.kill(pid, 0)
        return pid
    except Exception:
        return 0


def scheduler_start():
    if scheduler_running():
        return scheduler_running()
    lf = open(str(SCHED_LOG), "a")
    p = subprocess.Popen([sys.executable, str(CORE / "mediaforge.py"), "--scheduler"], stdin=subprocess.DEVNULL, stdout=lf, stderr=lf, start_new_session=True)
    SCHED_PID.write_text(str(p.pid))
    audit("scheduler-start", p.pid)
    return p.pid


def scheduler_stop():
    pid = scheduler_running()
    if pid:
        try:
            os.kill(pid, 15)
        except OSError:
            pass
        audit("scheduler-stop", pid)
    try:
        SCHED_PID.unlink()
    except OSError:
        pass


# ==========================================================================
#  ПОЧИНКА ПАПОК И ФАЙЛОВ (повреждённые имена, права, JSON-состояние, ядро)
# ==========================================================================
STATE_FILES = ("settings.json", "history.json", "queue.json", "hashes.json", "stats.json", "schedule.json", "profiles.json", "links.json")


def repair_folders():
    # лечит: «файл вместо папки», права, нечитаемые имена, битые симлинки, битые JSON, «зависшие» .part, пустые папки, повреждённое ядро
    rep = []

    def note(s):
        rep.append(s)
        print("  " + s)
    stamp = now_stamp()
    with Spin(L("Проверяю структуру папок", "Checking folder structure"), quiet=True):
        for d in list(DIRS) + [".config", ".core"]:
            p = BASE / d
            try:
                if p.exists() and not p.is_dir():
                    os.replace(str(p), str(p) + ".bad_" + stamp)
                    note("[+] " + L("файл вместо папки %s → переименован" % d, "file instead of folder %s → renamed" % d))
                p.mkdir(parents=True, exist_ok=True)
            except OSError as e:
                note("[!] %s: %s" % (d, e))
        subprocess.run(["chmod", "-R", "u+rwX", str(BASE)], timeout=120)
    fixed = bad_links = 0
    with Spin(L("Ищу повреждённые имена и ссылки", "Looking for damaged names and links"), quiet=True):
        for root, dirs, files in os.walk(os.fsencode(str(BASE))):
            for name in list(dirs) + list(files):
                full = os.path.join(root, name)
                try:
                    bad_name = False
                    try:
                        s = name.decode("utf-8")
                        bad_name = bool(re.search(r"[\x00-\x1f]", s))
                    except UnicodeDecodeError:
                        bad_name = True
                    if os.path.islink(full) and not os.path.exists(full):
                        os.unlink(full)
                        bad_links += 1
                        continue
                    if bad_name:
                        ext = os.path.splitext(name)[1].decode("utf-8", "replace")
                        new = ("fixed_" + hashlib.sha1(name).hexdigest()[:10] + re.sub(r"[^\w.]", "", ext)).encode()
                        os.rename(full, os.path.join(root, new))
                        fixed += 1
                except OSError:
                    continue
    if fixed:
        note("[+] " + L("исправлено имён файлов/папок: %d" % fixed, "fixed file/folder names: %d" % fixed))
    if bad_links:
        note("[+] " + L("удалено битых ссылок: %d" % bad_links, "removed broken links: %d" % bad_links))
    cdir = CONF / "corrupt"
    for nm in STATE_FILES:
        p = CONF / nm
        if p.exists():
            try:
                json.loads(p.read_text("utf-8"))
            except Exception:
                cdir.mkdir(parents=True, exist_ok=True)
                os.replace(str(p), str(cdir / ("%s.%s" % (nm, stamp))))
                note("[+] " + L("повреждённый %s перемещён в .config/corrupt (создастся заново)" % nm, "damaged %s moved to .config/corrupt (will be recreated)" % nm))
    old = 0
    for d in ("videos", "audio", "photos", "tmp"):
        for p in (BASE / d).rglob("*"):
            try:
                if p.is_file() and (p.suffix in (".part", ".ytdl", ".tmp", ".dl") or p.name.endswith(".part")) and time.time() - p.stat().st_mtime > 3600:
                    p.unlink()
                    old += 1
            except OSError:
                pass
    if old:
        note("[+] " + L("удалено зависших недокачек: %d" % old, "removed stale partial downloads: %d" % old))
    empty = 0
    for d in ("videos", "audio", "photos", "texts", "collages"):
        for r, ds, fs in os.walk(str(BASE / d), topdown=False):
            if Path(r) != BASE / d and not ds and not fs:
                try:
                    os.rmdir(r)
                    empty += 1
                except OSError:
                    pass
    if empty:
        note("[+] " + L("удалено пустых папок: %d" % empty, "removed empty folders: %d" % empty))
    core = CORE / "mediaforge.py"
    try:
        if core.exists():
            compile(core.read_text("utf-8"), "mediaforge.py", "exec")
    except Exception as e:
        note("[!] " + L("ядро повреждено (%s) — будет распаковано заново" % e, "core is damaged (%s) — will be re-extracted" % e))
        try:
            (CORE / ".ver").unlink()
        except OSError:
            pass
        write_action("rewrite")
    audit("repair-folders", "%d notes" % len(rep))
    if not rep:
        print("[+] " + L("Проблем не найдено — папки в порядке", "No problems found — folders are fine"))
    return rep


def write_action(a):
    try:
        (CONF / "action").write_text(a)
    except Exception:
        pass


# ==========================================================================
#  СПИСОК ССЫЛОК (память) — добавить сейчас, скачать потом
# ==========================================================================
@resilient
def links_menu():
    while True:
        lst = links_load()
        new = sum(1 for x in lst if x.get("status") != "done")
        k = menu(L("Список ссылок (%d, не скачано: %d)" % (len(lst), new), "Links list (%d, pending: %d)" % (len(lst), new)), [
            ("1", L("Добавить ссылки (без загрузки)", "Add links (no download)"), L("вводите по одной, пустая строка — конец", "one per line, blank line = end")),
            ("2", L("▶ Скачать всё из списка", "▶ Download everything in the list"), L("сначала анализ, потом загрузка сама", "analysis first, then it runs alone")),
            ("3", L("Скачать выбранные", "Download selected"), "1,3-5 / all"), ("4", L("Показать список", "Show the list"), ""),
            ("5", L("Удалить: выбранные / скачанные / всё", "Remove: selected / done / all"), ""), ("6", L("Изменить тип ссылок", "Change link type"), "auto / video / audio / photo"),
            ("7", L("Добавить заметку к ссылке", "Add a note to a link"), ""), ("8", L("Экспорт списка в .txt", "Export the list to .txt"), "reports/")], back=L("Назад", "Back"))
        if k == "q":
            return
        if k == "1":
            urls = read_urls()
            if urls:
                kind = ask(L("Тип для этих ссылок", "Type for these links"), "auto", quit_ok=False, hint="auto / video / audio / photo")
                kind = kind if kind in ("auto", "video", "audio", "photo") else "auto"
                n = links_add(urls, kind)
                print("[+] " + L("Добавлено: %d (дубликаты пропущены). Всего: %d" % (n, len(links_load())), "Added: %d (duplicates skipped). Total: %d" % (n, len(links_load()))))
        elif k == "2":
            run_saved_links()
        elif k in ("3", "4", "5", "6", "7"):
            if not lst:
                print("[!] " + L("Список пуст", "The list is empty"))
                continue
            for i, x in enumerate(lst, 1):
                st = {"done": c("✓", OK_C), "fail": c("✗", ERR_C)}.get(x.get("status"), c("•", WARN_C))
                print("  %s %s %s %s %s" % (c("%3d" % i, accent(), True), st, dim("[%s]" % x.get("kind", "auto")), trunc(x["url"], term_w() - 22), dim(("— " + x["note"]) if x.get("note") else (("— " + x["err"][:30]) if x.get("err") else ""))))
            if k == "4":
                pause()
                continue
            if k == "5":
                v = ask(L("Что удалить", "What to remove"), "", quit_ok=False, hint=L("номера 1,3-5 · done · all · b", "numbers 1,3-5 · done · all · b"))
                if v.lower() == "done":
                    lst = [x for x in lst if x.get("status") != "done"]
                elif v.lower() == "all":
                    if confirm(L("Очистить весь список?", "Clear the whole list?")):
                        lst = []
                elif v and v.lower() not in ("b", "back"):
                    try:
                        rm = set(parse_multi(v, len(lst)))
                        lst = [x for i, x in enumerate(lst, 1) if i not in rm]
                    except ValueError:
                        print("[!] " + L("Неверный ввод", "Bad input"))
                links_save(lst)
                continue
            sel = ask_multi(L("Номера ссылок", "Link numbers"), len(lst))
            if not sel:
                continue
            if k == "3":
                run_saved_links([i - 1 for i in sel], only_new=False)
            elif k == "6":
                kind = ask(L("Новый тип", "New type"), "auto", quit_ok=False, hint="auto / video / audio / photo")
                for i in sel:
                    lst[i - 1]["kind"] = kind if kind in ("auto", "video", "audio", "photo") else "auto"
                links_save(lst)
            elif k == "7":
                note_ = ask(L("Заметка", "Note"), "", quit_ok=False)
                for i in sel:
                    lst[i - 1]["note"] = note_
                links_save(lst)
        elif k == "8":
            p = BASE / "reports" / ("links_%s.txt" % now_stamp())
            p.write_text("\n".join(x["url"] for x in links_load()) + "\n", "utf-8")
            print("[+] " + str(p))
        pause()


# ==========================================================================
#  ЗАГРУЗКА, ОЧЕРЕДЬ, ПОИСК, СОЦСЕТИ
# ==========================================================================
def download_menu(kind):
    clear_screen()
    hdr({"video": L("Скачать видео", "Download video"), "audio": L("Скачать аудио", "Download audio"), "photo": L("Скачать фото / галереи", "Download photos / galleries"), "auto": L("Умная загрузка", "Smart download")}[kind],
        L("Все вопросы — сразу после ввода ссылок, затем загрузка идёт сама", "All questions come right after the links, then it runs on its own"))
    if kind in ("video", "auto"):
        print(dim("%s: %s, %s, %s, H.264=%s" % (L("Профиль", "Profile"), ST.g("quality"), ST.g("container"), ST.g("device"), ST.g("prefer_h264"))))
        q = ask(L("Качество", "Quality"), ST.g("quality"), quit_ok=True, hint="best/2160/1440/1080/720/480/360")
        if q in SCH["quality"][4]:
            ST.set("quality", q)
    elif kind == "audio":
        f = ask(L("Формат", "Format"), ST.g("audio_format"), hint="m4a/mp3/opus/flac/best")
        if f in SCH["audio_format"][4]:
            ST.set("audio_format", f)
    urls = read_urls()
    if not urls:
        return
    mode = ask(L("Что делать со ссылками (%d)?" % len(urls), "What to do with the links (%d)?" % len(urls)), "1", quit_ok=False,
               hint=L("1 скачать сейчас · 2 только сохранить в список · 3 сохранить и скачать", "1 download now · 2 only save to the list · 3 save and download"))
    if mode in ("2", "3"):
        n = links_add(urls, kind)
        print("[+] " + L("В списке ссылок: %d (добавлено %d)" % (len(links_load()), n), "In the links list: %d (added %d)" % (len(links_load()), n)))
        if mode == "2":
            return
    if free_mb() < 500:
        print("[!] " + L("Свободно всего %d МБ" % free_mb(), "Only %d MB free" % free_mb()))
    jobs = plan_many(urls, kind)
    if not jobs:
        print("[!] " + L("Нечего скачивать", "Nothing to download"))
        return
    print("\n[+] " + L("К загрузке: %d. Дальше без вопросов (Ctrl+C — назад в меню)." % len(jobs), "To download: %d. No more questions (Ctrl+C = back to the menu)." % len(jobs)))
    when = ask(L("Старт", "Start"), "", quit_ok=False, hint=L("Enter — сразу, число — через N минут", "Enter = now, number = in N minutes"))
    if when.isdigit() and int(when) > 0:
        wait_minutes(int(when))
    left = run_jobs(jobs)
    if mode == "3":
        lst = links_load()
        left_u = {j["url"] for j in left}
        for x in lst:
            if x["url"] in urls:
                x["status"] = "fail" if any(j["url"] == x["url"] or j.get("alts") for j in left) and x["url"] in left_u else "done"
        links_save(lst)


def wait_minutes(m):
    end = time.time() + m * 60
    with Spin(L("Ожидание старта", "Waiting to start"), quiet=True) as s:
        while time.time() < end:
            s.update(L("Старт через %s (Ctrl+C — отмена)" % fmt_dur(end - time.time()), "Starting in %s (Ctrl+C to cancel)" % fmt_dur(end - time.time())))
            time.sleep(1)


@resilient
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
            txt = read_clipboard() if k == "3" else Path(ask(L("Путь к .txt", ".txt path"), "", quit_ok=False)).expanduser().read_text("utf-8", "replace")
            urls = list(dict.fromkeys(URL_RE.findall(txt)))
            kind = ask(L("Тип", "Type"), "auto", quit_ok=False, hint="auto/video/audio/photo")
            kind = kind if kind in ("auto", "video", "audio", "photo") else "auto"
            jobs = plan_many(urls, kind)
            jsave(QUEUE, {"jobs": q + jobs})
            print("[+] " + L("Добавлено: %d" % len(jobs), "Added: %d" % len(jobs)))
        elif k == "5" and confirm(L("Очистить?", "Clear?")):
            jsave(QUEUE, {"jobs": []})
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
    if not ensure_internet(L("поиск", "search")):
        return
    items = []
    with Spin(L("Ищу", "Searching"), quiet=True):
        try:
            if k == "3":
                d = get_json("https://rutube.ru/api/search/video/?query=%s" % quote(qy))
                items = [mkjob(r["video_url"], "video", r.get("title", ""), "ytdlp", "video", dur=r.get("duration")) for r in d.get("results", [])[:10]]
            else:
                import yt_dlp
                pre = "ytsearch10:" if k == "1" else "scsearch10:"
                with yt_dlp.YoutubeDL({"quiet": True, "extract_flat": True, "logger": QLog(), "proxy": proxy_url() or None}) as y:
                    info = y.extract_info(pre + qy, download=False)
                for e in info.get("entries", []):
                    u = e.get("url") or ""
                    if not u.startswith("http") and e.get("id"):
                        u = "https://www.youtube.com/watch?v=" + e["id"]
                    items.append(mkjob(u, "audio" if k == "2" else "video", e.get("title") or u, "ytdlp", "audio" if k == "2" else "video", dur=e.get("duration")))
        except Exception as ex:
            note_error("search", ex)
            print("[!] %s" % trunc(str(ex), term_w() - 6))
    if not items:
        return
    for i, it in enumerate(items, 1):
        print("  %s %s %s" % (c("%2d" % i, accent(), True), trunc(it["title"], term_w() - 16), dim(fmt_dur(it["dur"]) if it.get("dur") else "")))
    sel = ask_multi(L("Скачать (номера/all)", "Download (numbers/all)"), len(items))
    if sel:
        kind = ask(L("Как", "As"), "audio" if k == "2" else "video", quit_ok=False, hint="video / audio")
        for i in sel:
            items[i - 1]["kind"] = "audio" if kind == "audio" else "video"
            items[i - 1]["type"] = items[i - 1]["kind"]
        run_jobs([items[i - 1] for i in sel])


def run_items(items, label=""):
    # элементы соцсети → выбор → задания → загрузка
    if not items:
        print("[!] " + L("Ничего не найдено", "Nothing found"))
        return
    sel = select_items(items, "auto")
    if sel:
        run_jobs([item_to_job(i) for i in sel])


@resilient
def social_menu():
    while True:
        k = menu(L("Соцсети: аватарки, истории, посты, Telegram", "Social: avatars, stories, posts, Telegram"), [
            ("1", L("Ссылка на пост / рилс / видео / Telegram-пост", "Post / reel / video / Telegram post link"), L("Instagram, TikTok, Threads, Likee, X, Telegram, Bluesky…", "Instagram, TikTok, Threads, Likee, X, Telegram, Bluesky…")),
            ("2", L("Аватарка по нику или ссылке", "Avatar by username or link"), ""), ("3", L("Истории Instagram", "Instagram stories"), L("нужен вход (cookies)", "login (cookies) needed")),
            ("4", L("Актуальное (highlights) Instagram", "Instagram highlights"), L("нужен вход (cookies)", "login (cookies) needed")),
            ("5", L("Последние посты профиля / канала", "Latest posts of a profile / channel"), L("Instagram, TikTok, Telegram…", "Instagram, TikTok, Telegram…")),
            ("6", L("Профиль целиком через gallery-dl", "Whole profile via gallery-dl"), L("все посты, долго", "all posts, slow")), ("7", L("Telegram: установить Telethon и войти", "Telegram: install Telethon and log in"), L("музыка, файлы, приватные чаты", "music, files, private chats")),
            ("8", L("Мастер cookies (вход в аккаунт)", "Cookies wizard (account login)"), ""), ("9", L("Telegram: канал — последние N постов", "Telegram: channel — last N posts"), L("с текстом и форматированием", "with text and formatting"))], back=L("Назад", "Back"))
        if k == "q":
            return
        if k == "1":
            urls = read_urls()
            if urls:
                jobs = plan_many(urls, "auto")
                if jobs:
                    run_jobs(jobs)
        elif k in ("2", "3", "4", "5"):
            plat = pick_one(L("Платформа", "Platform"), PLATFORMS if k in ("2", "5") else ["instagram"], None)
            if not plat:
                continue
            who = ask(L("Ник или ссылка на профиль", "Username or profile link"), "", quit_ok=False, hint="@name")
            if who.startswith("http"):
                who = [x for x in urlparse(who).path.split("/") if x and x not in ("stories", "@")][:1] or [""]
                who = who[0].lstrip("@")
            if not who:
                continue
            what = {"2": "avatar", "3": "stories", "4": "highlights", "5": "posts"}[k]
            try:
                items = social_profile(plat, who, what)
            except NeedLogin as e:
                login_hint(str(e))
                continue
            except KeyboardInterrupt:
                raise Interrupt()
            except Exception as ex:
                note_error(who, ex)
                print("[!] %s" % trunc(str(ex), term_w() - 6))
                continue
            if what == "avatar":
                for it in items:
                    it["sub"] = "avatars"
                    it["name"] = "%s_%s.jpg" % (plat, sanitize(who))
            run_items(items)
        elif k == "6":
            u = ask(L("Ссылка на профиль/страницу", "Profile/page link"), "", quit_ok=False)
            if u and ensure_internet():
                ok, res = gallery_whole(u)
                print(("[+] " if ok else "[!] ") + str(res))
        elif k == "7":
            if not telethon_installed():
                if confirm(L("Установить Telethon (pip, небольшой чисто-питоновый пакет)?", "Install Telethon (pip, small pure-Python package)?"), True):
                    write_action("pip:telethon")
                    raise SystemExit(0)
            else:
                try:
                    tg_login()
                except KeyboardInterrupt:
                    raise Interrupt()
                except Exception as ex:
                    print("[!] %s" % trunc(str(ex), term_w() - 6))
        elif k == "8":
            cookies_wizard()
        elif k == "9":
            ch = ask(L("Канал (@name или t.me/name)", "Channel (@name or t.me/name)"), "", quit_ok=False).strip().replace("https://t.me/", "").replace("s/", "").lstrip("@").strip("/")
            n = ask(L("Сколько последних постов", "How many latest posts"), "20", quit_ok=False)
            if ch:
                ST.ov["playlist_limit"] = int(n) if n.isdigit() else 20
                try:
                    run_items(soc_telegram("https://t.me/%s" % ch))
                except Exception as ex:
                    print("[!] %s" % trunc(str(ex), term_w() - 6))
                finally:
                    ST.ov.pop("playlist_limit", None)
        pause()


# ==========================================================================
#  КОНВЕРТЕР, МЕДИА-ИНСТРУМЕНТЫ, ФОТО, МЕТАДАННЫЕ
# ==========================================================================
VPROF = {"h264 (iPhone/Android)": ("libx264", ["-crf", "23", "-preset", "fast", "-pix_fmt", "yuv420p", "-profile:v", "high"], "mp4"),
         "h264 baseline (старые)": ("libx264", ["-crf", "24", "-preset", "fast", "-pix_fmt", "yuv420p", "-profile:v", "baseline", "-level", "3.0"], "mp4"),
         "h265/HEVC": ("libx265", ["-crf", "28", "-preset", "fast", "-tag:v", "hvc1"], "mp4"), "vp9": ("libvpx-vp9", ["-crf", "32", "-b:v", "0"], "webm"), "av1": ("libsvtav1", ["-crf", "35"], "mkv")}
APROF = {"aac/m4a": ("aac", ["-b:a", "192k"], "m4a"), "mp3": ("libmp3lame", ["-b:a", "192k"], "mp3"), "opus": ("libopus", ["-b:a", "160k"], "opus"), "flac": ("flac", [], "flac"), "ac3": ("ac3", ["-b:a", "192k"], "ac3")}


def im_prefix():
    return ["magick"] if shutil.which("magick") else (["convert"] if shutil.which("convert") else None)


def pick_media(multi=True):
    k = menu(L("Папка", "Folder"), [("1", "videos", ""), ("2", "audio", ""), ("3", "photos", ""), ("4", "collages", ""), ("5", "tmp", ""), ("6", "texts", "")], show=False)
    if k == "q":
        return None
    d = BASE / {"1": "videos", "2": "audio", "3": "photos", "4": "collages", "5": "tmp", "6": "texts"}[k]
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
    try:
        for f in fs:
            out = uniq(f.with_name("%s_conv.%s" % (f.stem, ext)))
            dur = probe_duration(f)
            args = ["-i", f] + (["-vn", "-c:a", enc] + opts if audio_only else ["-c:v", enc] + opts + ["-c:a", "aac", "-b:a", "160k", "-movflags", "+faststart"]) + [out]
            print("[*] " + f.name)
            if ff_run(args, "conv", dur) == 0:
                ok += 1
                print("[+] " + out.name)
    finally:
        UNATT[0] = False
    print("[+] %d/%d" % (ok, len(fs)))


DEVICE_ENC = {"iphone": ["-c:v", "libx264", "-profile:v", "high", "-pix_fmt", "yuv420p", "-crf", "22", "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart"],
              "ipad": ["-c:v", "libx264", "-profile:v", "high", "-pix_fmt", "yuv420p", "-crf", "22", "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart"],
              "android": ["-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "23", "-vf", "scale='min(1920,iw)':-2", "-c:a", "aac", "-b:a", "160k", "-movflags", "+faststart"],
              "appletv": ["-c:v", "libx264", "-profile:v", "high", "-pix_fmt", "yuv420p", "-crf", "21", "-c:a", "aac", "-b:a", "256k", "-movflags", "+faststart"],
              "chromecast": ["-c:v", "libx264", "-profile:v", "high", "-pix_fmt", "yuv420p", "-crf", "23", "-vf", "scale='min(1920,iw)':-2", "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart"]}


def batch_device_convert():
    # пакетная перекодировка папки videos/ под выбранное устройство (только несовместимые файлы)
    dev = pick_one(L("Устройство", "Device"), list(DEVICE_ENC), ST.g("device") if ST.g("device") in DEVICE_ENC else None)
    if not dev:
        return
    vids = [f for f in list_files(BASE / "videos") if f.suffix.lower() in VEXT]
    if not vids:
        print("[!] " + L("В videos/ нет видео", "No videos in videos/"))
        return
    todo = []
    for f in track(vids, L("Проверка кодеков", "Checking codecs")):
        info = ffprobe_json(f)
        vs = [s.get("codec_name") for s in info.get("streams", []) if s.get("codec_type") == "video"]
        if not (vs and vs[0] == "h264" and f.suffix.lower() in (".mp4", ".m4v", ".mov")):
            todo.append(f)
    print("[*] " + L("Нужна перекодировка: %d из %d" % (len(todo), len(vids)), "Needs re-encode: %d of %d" % (len(todo), len(vids))))
    if not todo or not confirm(L("Перекодировать?", "Re-encode?"), True):
        return
    rep, UNATT[0] = [], True
    try:
        for f in todo:
            out = uniq(f.with_name(f.stem + "_" + dev + ".mp4"))
            ok = ff_run(["-i", f] + DEVICE_ENC[dev] + [out], trunc(f.name, 12), probe_duration(f)) == 0
            rep.append({"file": f.name, "out": out.name, "ok": ok})
    finally:
        UNATT[0] = False
    jsave(BASE / "reports" / ("convert_%s.json" % now_stamp()), rep)
    print("[+] %d/%d" % (sum(1 for r in rep if r["ok"]), len(rep)))


@resilient
def tools_menu():
    k = menu(L("Медиа-инструменты", "Media tools"), [("1", L("Конвертер (кодеки)", "Converter (codecs)"), ""), ("2", L("Извлечь аудио из видео", "Extract audio from video"), ""), ("3", L("Видео → GIF", "Video → GIF"), ""),
                                                     ("4", L("Кадр-превью", "Thumbnail frame"), ""), ("5", L("Сжать видео (CRF)", "Compress video (CRF)"), ""), ("6", L("Склеить видео", "Concat videos"), ""),
                                                     ("7", L("Нарезать на части", "Split into segments"), ""), ("8", L("Нормализовать громкость", "Normalize loudness"), ""), ("9", L("Заменить аудиодорожку", "Replace audio track"), ""),
                                                     ("10", L("Вшить/достать субтитры", "Embed / extract subtitles"), ""), ("11", L("Обрезать по времени", "Trim by time"), ""),
                                                     ("12", L("Папка → под устройство (iPhone, iPad…)", "Folder → for a device (iPhone, iPad…)"), ""), ("13", L("Субтитры по ссылке (авто-субтитры)", "Subtitles by link (auto subs)"), ""),
                                                     ("14", L("Нарезка по сменам сцен (кадры)", "Scene detection (frames)"), ""), ("15", L("Автообрезка чёрных полос (cropdetect)", "Auto-crop black bars (cropdetect)"), ""),
                                                     ("16", L("Удалить шум аудио", "Audio denoise"), ""), ("17", L("Стабилизировать видео", "Stabilize video"), "")])
    if k == "q":
        return
    if k == "1":
        return convert_menu()
    if k == "12":
        return batch_device_convert()
    if k == "13":
        return subs_by_link()
    if k in ("14", "15", "16", "17"):
        return video_tool({"14": "scenes", "15": "autocrop", "16": "denoise", "17": "stabilize"}[k])
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


def subs_by_link():
    # авто-субтитры (YouTube и др.) без скачивания видео → .srt
    u = ask(L("Ссылка на видео", "Video link"), "", quit_ok=False)
    if not u or not ensure_internet():
        return
    import yt_dlp
    o = {"quiet": True, "no_warnings": True, "logger": QLog(), "skip_download": True, "writesubtitles": True, "writeautomaticsub": True, "subtitleslangs": [x.strip() for x in ST.g("sub_langs").split(",")],
         "subtitlesformat": "srt/vtt/best", "outtmpl": str(BASE / "texts" / "subs" / "%(title).80B [%(id)s]"), "proxy": proxy_url() or None}
    if have_ffmpeg():
        o["postprocessors"] = [{"key": "FFmpegSubtitlesConvertor", "format": "srt"}]
    with Spin(L("Получаю субтитры", "Fetching subtitles"), quiet=True):
        try:
            with yt_dlp.YoutubeDL(o) as y:
                y.download([u])
        except Exception as e:
            print("[!] %s" % trunc(str(e), term_w() - 6))
            return
    fs = sorted((BASE / "texts" / "subs").glob("*"), key=lambda p: -p.stat().st_mtime)[:4]
    print("[+] " + (", ".join(p.name for p in fs) if fs else L("субтитров нет", "no subtitles")))


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
            tmps = []
            for i, f in enumerate(track(fs, L("Подготовка", "Preparing")), 1):
                t = tmp / ("c_%03d.jpg" % i)
                subprocess.run(pre + [str(f) + "[0]", "-auto-orient", "-resize", cell + "^", "-gravity", "center", "-extent", cell, "-quality", "88", str(t)], timeout=300)
                if t.exists():
                    tmps.append(t)
            mont = ["montage"] if shutil.which("montage") else (["magick", "montage"] if shutil.which("magick") else None)
            if not mont or not tmps:
                print("[!] montage ?")
                return
            with Spin(L("Собираю коллаж", "Building collage"), quiet=True):
                r = subprocess.run(mont + [str(t) for t in tmps] + ["-tile", "%dx" % cols, "-geometry", "%s+%d+%d" % (cell, gap, gap), "-background", bg, "-quality", "90", str(out)], timeout=1200)
            for t in tmps:
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


def ocr_photos():
    # распознавание текста (tesseract); если не установлен — предложить установку
    if not shutil.which("tesseract"):
        print("[!] " + L("tesseract не установлен (~300 МБ).", "tesseract is not installed (~300 MB)."))
        if confirm(L("Установить?", "Install?"), False):
            write_action("optional")
            raise SystemExit(0)
        return
    fs = pick_files(BASE / "photos", {".jpg", ".jpeg", ".png", ".webp", ".bmp"}, True, L("Фото для OCR", "Photos for OCR"))
    for f in track(fs or [], "ocr"):
        r = subprocess.run(["tesseract", str(f), "stdout", "-l", "rus+eng"], timeout=600)
        txt = r.stdout.decode("utf-8", "replace")
        (f.with_suffix(".txt")).write_text(txt, "utf-8")
        print("[+] %s: %d %s" % (f.name, len(txt), L("симв.", "chars")))


def photo_menu():
    pre = im_prefix()
    k = menu(L("Фото: правка и оптимизация", "Photos: edit & optimize"), [("1", L("Уменьшить (800x600 / 50%)", "Resize (800x600 / 50%)"), ""), ("2", L("Повернуть", "Rotate"), ""), ("3", L("Авто-поворот по EXIF", "Auto-orient by EXIF"), ""),
                                                                      ("4", L("Конвертировать (jpg/png/webp)", "Convert (jpg/png/webp)"), ""), ("5", L("Сжать JPEG (jpegoptim)", "Compress JPEG (jpegoptim)"), ""), ("6", L("Обрезать (100x100+10+10)", "Crop (100x100+10+10)"), ""),
                                                                      ("7", L("Распознать текст (OCR)", "Recognize text (OCR)"), "")])
    if k == "q":
        return
    if k == "7":
        return ocr_photos()
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
                with Spin(f.name, quiet=True):
                    r = subprocess.run([ex, "-overwrite_original"] + (["-all="] if k == "2" else ["-gps:all="]) + [str(f)], timeout=120)
                print(("[+] " if r.returncode == 0 else "[!] ") + f.name)
            elif k == "2":
                print(("[+] " if strip_metadata(f) else "[!] ") + f.name)
            else:
                print("[!] exiftool?")
        elif k == "4" and ex:
            r = subprocess.run([ex, "-n", "-gpslatitude", "-gpslongitude", "-s3", str(f)], timeout=60).stdout.decode().split()
            print("%s: %s" % (f.name, ("https://www.openstreetmap.org/?mlat=%s&mlon=%s#map=16/%s/%s" % (r[0], r[1], r[0], r[1])) if len(r) >= 2 else L("GPS нет", "no GPS")))
        elif k == "5":
            n = f.with_name(hashlib.sha1(os.urandom(16)).hexdigest()[:16] + f.suffix)
            f.rename(n)
            audit("rename", "%s -> %s" % (f.name, n.name))
            print("[+] %s → %s" % (f.name, n.name))
    if k == "6":
        seen = {}
        for f in track(fs, "sha256"):
            h = hash_file(f) or "big" + str(f.stat().st_size)
            seen.setdefault(h, []).append(f)
        dups = [v for v in seen.values() if len(v) > 1]
        for g in dups:
            print(c(L("Дубликаты:", "Duplicates:"), WARN_C) + " " + ", ".join(x.name for x in g))
        if dups and confirm(L("Удалить копии (оставить первый)?", "Delete copies (keep first)?")):
            for g in dups:
                for x in g[1:]:
                    x.unlink()
                    audit("delete-dup", x.name)
        if not dups:
            print("[+] " + L("Дубликатов нет", "No duplicates"))


# ==========================================================================
#  ФАЙЛЫ, ИСТОРИЯ, СТАТИСТИКА, МЕДИАТЕКА, ПЛАНИРОВЩИК
# ==========================================================================
@resilient
def files_menu():
    while True:
        k = menu(L("Файлы и починка", "Files & repair"), [("1", L("Просмотр папок и размеры", "Browse folders & sizes"), ""), ("2", L("Удалить файлы", "Delete files"), ""), ("3", L("Переименовать", "Rename"), ""),
                                       ("4", L("Очистить tmp и недокачанные .part (старше 1 ч)", "Clean tmp and partial .part (older than 1 h)"), ""), ("5", L("Показать путь для iOS «Файлы»", "Show path for iOS Files"), ""),
                                       ("6", L("🛠 Починить папки и файлы", "🛠 Repair folders and files"), L("битые имена, права, JSON, ядро", "bad names, permissions, JSON, core")),
                                       ("7", L("Обновить index.html медиатеки", "Update library index.html"), ""),
                                       ("8", L("Массовое переименование по regex", "Bulk rename by regex"), L("превью и dry-run", "preview and dry-run")), ("9", L("Корзина (восстановить удалённое)", "Trash (restore deleted)"), ""),
                                       ("10", L("Бэкапы настроек (восстановить)", "Settings backups (restore)"), "")])
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
                    print(("[+] " if rm_tree(f) else "[!] ") + f.name)
        elif k == "3":
            fs = pick_media(False)
            if fs:
                nn = ask(L("Новое имя", "New name"), fs[0].name, quit_ok=False)
                if nn and not (fs[0].parent / nn).exists():
                    fs[0].rename(fs[0].parent / sanitize(nn) if "." in nn else fs[0].parent / (sanitize(nn) + fs[0].suffix))
        elif k == "4":
            n = 0
            for p in [x for x in (BASE / "tmp").glob("*") if time.time() - x.stat().st_mtime > 3600] + [x for d in ("videos", "audio", "photos") for x in (BASE / d).rglob("*.part") if time.time() - x.stat().st_mtime > 3600]:
                try:
                    p.unlink()
                    n += 1
                except OSError:
                    pass
            print("[+] " + L("Удалено: %d" % n, "Removed: %d" % n))
        elif k == "5":
            print(str(BASE) + "\n" + dim(L("В iSH: mount -t ios . /mnt/files, затем cp -r %s/videos /mnt/files/" % BASE, "In iSH: mount -t ios . /mnt/files, then cp -r %s/videos /mnt/files/" % BASE)))
        elif k == "6":
            repair_folders()
            if (CONF / "action").exists():
                pause()
                raise SystemExit(0)
        elif k == "7":
            p, n = busy(L("Строю index.html", "Building index.html"), build_library_html)
            print("[+] %s (%d)" % (p, n))
        elif k == "8":
            regex_rename()
        elif k == "9":
            trash_menu()
        elif k == "10":
            restore_backup()
        pause()


@resilient
def history_menu():
    h = jload(HIST, {})
    items = sorted(h.items(), key=lambda x: x[1].get("ts", ""), reverse=True)
    if not items:
        print("[!] " + L("История пуста", "History is empty"))
        pause()
        return
    for i, (u, e) in enumerate(items[:30], 1):
        print("  %s %s %s %s" % (c("%2d" % i, accent(), True), c("✓" if e["status"] == "ok" else "✗", OK_C if e["status"] == "ok" else ERR_C), trunc(e.get("title") or u, term_w() - 28), dim(e.get("ts", ""))))
    k = ask(L("Действие", "Action"), "", quit_ok=False, hint=L("r повторить неудачные · c очистить · Enter — назад", "r retry failed · c clear · Enter = back")).lower()
    if k == "c" and confirm(L("Очистить?", "Clear?")):
        jsave(HIST, {})
        audit("history-clear")
    elif k == "r":
        run_jobs([mkjob(u, "video", e.get("title", u), "ytdlp") for u, e in items if e["status"] != "ok"])


@resilient
def stats_menu():
    s = jload(STATS, {"files": 0, "bytes": 0, "by_type": {}, "by_day": {}})
    print(c(L("Статистика медиатеки", "Library statistics"), accent(), True))
    table([[L("Файлов скачано", "Files downloaded"), str(s["files"])], [L("Общий размер", "Total size"), fmt_size(s["bytes"])]] + [[k, str(v)] for k, v in s.get("by_type", {}).items()], None)
    days = sorted(s.get("by_day", {}).items())[-10:]
    if days:
        mx = max(v for _, v in days)
        print(c(L("Последние дни", "Recent days"), INFO_C, True))
        for d, v in days:
            w = max(1, int(v / mx * (term_w() - 22)))
            print("  %s %s %d" % (d, grad(U("█", "#") * w, int(v)), v))
    print("[*] %s: %d | %s: %d" % (L("Ссылок в памяти", "Links in memory"), len(links_load()), L("в очереди", "in queue"), len(jload(QUEUE, {}).get("jobs", []))))
    pause()


@resilient
def schedule_menu():
    while True:
        ent = jload(SCHED, [])
        pid = scheduler_running()
        k = menu(L("Планировщик загрузок", "Download scheduler"), [
            ("1", L("Добавить задачу (канал/плейлист + время)", "Add task (channel/playlist + time)"), ""), ("2", L("Список задач", "Task list"), str(len(ent))), ("3", L("Удалить задачу", "Remove task"), ""),
            ("4", L("Запустить фонового демона", "Start background daemon"), L("работает: PID %d" % pid, "running: PID %d" % pid) if pid else L("остановлен", "stopped")),
            ("5", L("Остановить демона", "Stop daemon"), ""), ("6", L("Показать лог демона", "Show daemon log"), "")], sub=L("iSH должен оставаться активным (геолокация держит его в фоне)", "iSH must stay active (geolocation keeps it alive)"))
        if k == "q":
            return
        if k == "1":
            u = ask(L("Ссылка на канал/плейлист", "Channel/playlist link"), "", quit_ok=False)
            tm = ask(L("Время", "Time"), "03:00", quit_ok=False, hint="HH:MM")
            kind = ask(L("Тип", "Type"), "video", quit_ok=False, hint="video/audio/photo/auto")
            if u and re.fullmatch(r"\d{2}:\d{2}", tm):
                ent.append({"url": u, "time": tm, "kind": kind if kind in ("video", "audio", "photo", "auto") else "video", "last": ""})
                jsave(SCHED, ent)
                print("[+] " + L("Добавлено", "Added"))
        elif k == "2":
            for i, e in enumerate(ent, 1):
                print("  %s %s %s %s" % (c("%2d" % i, accent(), True), e["time"], dim("[%s]" % e["kind"]), trunc(e["url"], term_w() - 22)))
        elif k == "3":
            sel = ask_multi(L("Номера", "Numbers"), len(ent)) if ent else None
            if sel:
                jsave(SCHED, [e for i, e in enumerate(ent, 1) if i not in sel])
        elif k == "4":
            print("[+] PID %d" % scheduler_start())
        elif k == "5":
            scheduler_stop()
            print("[+] " + L("Остановлен", "Stopped"))
        elif k == "6":
            try:
                print(SCHED_LOG.read_text("utf-8")[-2500:])
            except Exception:
                print("[*] " + L("Лог пуст", "Log is empty"))
        pause()


# ==========================================================================
#  КРУЖКИ TELEGRAM (видеосообщения): создать из видео и править
# ==========================================================================
def circle_make(f, ss, dur, extra_vf="", rotate=0):
    # квадрат 384×384 по центру, H.264 crf 28, до 60 с → videos/circles/
    out = uniq(BASE / "videos" / "circles" / (f.stem + "_circle.mp4"))
    out.parent.mkdir(parents=True, exist_ok=True)
    vf = []
    if rotate:
        vf.append({90: "transpose=1", 180: "transpose=1,transpose=1", 270: "transpose=2"}.get(rotate, "null"))
    vf += ["crop='min(iw,ih)':'min(iw,ih)'", "scale=384:384"]
    if extra_vf:
        vf.append(extra_vf)
    vf.append("format=yuv420p")
    args = ["-ss", ss, "-t", str(min(60, int(dur))), "-i", f, "-vf", ",".join(vf), "-c:v", "libx264", "-crf", "28", "-preset", "fast", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "64k", "-ar", "44100", "-movflags", "+faststart", out]
    rc = ff_run(args, "circle", min(60, int(dur)))
    return out if rc == 0 and out.exists() else None


@resilient
def circles_menu():
    k = menu(L("Кружки Telegram (видеосообщения)", "Telegram circles (video messages)"), [
        ("1", L("Создать кружок из видео", "Make a circle from a video"), L("обрезка по времени, квадрат 384×384, ≤60 с", "time trim, 384×384 square, ≤60 s")),
        ("2", L("Править кружок (обрезка, поворот, текст)", "Edit a circle (trim, rotate, text)"), L("импортируйте MP4 из Telegram в videos/", "import an MP4 from Telegram into videos/")),
        ("3", L("Скачать кружки из поста/канала Telegram", "Download circles from a Telegram post/channel"), "")])
    if k == "q":
        return
    if k == "3":
        u = ask(L("Ссылка на пост/канал", "Post/channel link"), "", quit_ok=False)
        items = [i for i in (soc_telegram(u, "video") if u else []) if "round" in i.get("name", "") or i["title"] == "round video"] or (soc_telegram(u, "video") if u else [])
        return run_items([i for i in items if i["type"] == "video"])
    fs = pick_files(BASE / "videos", None, False, L("Видео", "Video"))
    if not fs:
        return
    f = fs[0]
    total = probe_duration(f) or 0
    print(dim(L("Длительность: %s" % fmt_dur(total), "Duration: %s" % fmt_dur(total))))
    ss = ask(L("Начало", "Start"), "00:00:00", quit_ok=False, hint="HH:MM:SS")
    dur = ask(L("Длительность, сек (макс. 60)", "Duration, s (max 60)"), "30", quit_ok=False)
    dur = int(dur) if dur.isdigit() else 30
    rot, vf = 0, ""
    if k == "2":
        r = ask(L("Поворот", "Rotate"), "0", quit_ok=False, hint="0 / 90 / 180 / 270")
        rot = int(r) if r in ("90", "180", "270") else 0
        txt = ask(L("Текст поверх (Enter — без текста)", "Text overlay (Enter = none)"), "", quit_ok=False)
        if txt:
            font = next((p for p in ("/usr/share/fonts/dejavu/DejaVuSans.ttf", "/usr/share/fonts/ttf-dejavu/DejaVuSans.ttf", "/usr/share/fonts/TTF/DejaVuSans.ttf") if os.path.exists(p)), "")
            if not font:
                print("[!] " + L("Нет шрифта для drawtext (apk add ttf-dejavu) — текст пропущен", "No font for drawtext (apk add ttf-dejavu) — text skipped"))
            else:
                safe = txt.replace("\\", "\\\\").replace(":", "\\:").replace("'", "")
                vf = "drawtext=fontfile=%s:text='%s':fontcolor=white:fontsize=28:box=1:boxcolor=black@0.5:x=(w-text_w)/2:y=h-text_h-24" % (font, safe)
    UNATT[0] = True
    try:
        out = circle_make(f, ss, dur, vf, rot)
    finally:
        UNATT[0] = False
    print(("[+] " + str(out)) if out else "[!] " + L("Не получилось (ffmpeg)", "Failed (ffmpeg)"))


# ==========================================================================
#  СЕТЬ: cookies, CA, пины, VPN, диагностика
# ==========================================================================
COOKIE_SITES = ["instagram.com", "tiktok.com", "threads.net", "facebook.com", "x.com", "youtube.com", "vk.com", "reddit.com", "pinterest.com", "other"]


def cookies_wizard():
    # мастер cookies: вставьте строку Cookie из браузера (или sessionid для Instagram) → Netscape-файл cookies/<домен>.txt
    print("\n" + c(L("Мастер cookies", "Cookies wizard"), accent(), True))
    have = sorted(p.name for p in (BASE / "cookies").glob("*.txt*"))
    if have:
        print(dim(L("Уже есть: ", "Existing: ") + ", ".join(have)))
    dom = pick_one(L("Сайт", "Site"), COOKIE_SITES)
    if not dom:
        return
    if dom == "other":
        dom = ask(L("Домен (example.com)", "Domain (example.com)"), "", quit_ok=False).lower().replace("www.", "")
        if not dom:
            return
    if dom == "instagram.com":
        print(dim(L("Instagram: откройте instagram.com в Safari/Chrome (вы вошли) → Инструменты разработчика → Storage/Cookies → sessionid. Либо вставьте всю строку Cookie ниже.", "Instagram: open instagram.com in the browser (logged in) → Developer tools → Storage/Cookies → sessionid. Or paste the whole Cookie string below.")))
        sid = ask("sessionid", "", quit_ok=False, hint=L("Enter — вставить строку целиком", "Enter = paste the whole string"))
        if sid:
            csrf = ask("csrftoken", "", quit_ok=False, hint=L("(необязательно)", "(optional)"))
            uid = ask("ds_user_id", "", quit_ok=False, hint=L("(необязательно)", "(optional)"))
            txt = "sessionid=%s" % sid + ("; csrftoken=%s" % csrf if csrf else "") + ("; ds_user_id=%s" % uid if uid else "")
        else:
            txt = ask(L("Строка Cookie", "Cookie string"), "", quit_ok=False)
    else:
        print(dim(L("Вставьте строку заголовка Cookie (a=b; c=d) или готовый Netscape-текст (несколько строк, пустая строка — конец).", "Paste the Cookie header (a=b; c=d) or Netscape text (several lines, blank line = end).")))
        txt = ask(L("Cookie", "Cookie"), "", quit_ok=False)
        if txt and "\t" not in txt and not txt.startswith("#") and "=" not in txt:
            txt = ""
    if not txt:
        print("[!] " + L("Пусто — отмена", "Empty — cancelled"))
        return
    p = cookies_save(dom, txt)
    print("[+] %s %s" % (L("Сохранено:", "Saved:"), p))
    if dom == "instagram.com":
        with Spin(L("Проверяю вход в Instagram", "Checking Instagram login"), quiet=True):
            try:
                d = ig_json("https://i.instagram.com/api/v1/accounts/current_user/?edit=true")
                print("[+] " + L("Вход работает: @%s" % (d.get("user") or {}).get("username", "?"), "Login works: @%s" % (d.get("user") or {}).get("username", "?")))
            except Exception as e:
                print("[!] " + L("Проверка не прошла: %s" % trunc(str(e), 50), "Check failed: %s" % trunc(str(e), 50)))


def cookies_delete():
    fs = sorted((BASE / "cookies").glob("*.txt*"))
    if not fs:
        print("[*] " + L("Cookies нет", "No cookies"))
        return
    for i, f in enumerate(fs, 1):
        print("  %s %s" % (c("%2d" % i, accent(), True), f.name))
    sel = ask_multi(L("Какие удалить", "Which to delete"), len(fs))
    for i in sel or []:
        fs[i - 1].unlink()
        audit("cookies-delete", fs[i - 1].name)
    print("[+] OK")


def ca_menu():
    # доверенные CA (сертификат прокси-клиента для MITM): файл из certs/ или вставка PEM → bundle → extra_ca
    d = BASE / "certs"
    d.mkdir(parents=True, exist_ok=True)
    print(dim(L("Положите .crt/.pem в %s или вставьте PEM. В Shadowrocket: Настройки → HTTPS-дешифровка → Экспорт сертификата." % d, "Put .crt/.pem into %s or paste PEM. In Shadowrocket: Settings → HTTPS decryption → export certificate." % d)))
    k = ask(L("Действие", "Action"), "1", quit_ok=False, hint=L("1 из файлов · 2 вставить PEM · 3 отключить · 4 проверить MITM", "1 from files · 2 paste PEM · 3 disable · 4 check MITM"))
    if k == "2":
        print(dim(L("Вставьте PEM (до -----END CERTIFICATE-----), затем пустая строка.", "Paste PEM (up to -----END CERTIFICATE-----), then a blank line.")))
        lines = []
        while True:
            x = input("")
            if not x.strip() and lines:
                break
            lines.append(x)
        if any("BEGIN CERTIFICATE" in x for x in lines):
            (d / ("pasted_%s.pem" % now_stamp())).write_text("\n".join(lines) + "\n")
        k = "1"
    if k == "1":
        pems = [p for p in d.iterdir() if p.suffix.lower() in (".crt", ".pem", ".cer") and p.name != "bundle.pem"]
        if not pems:
            print("[!] " + L("Сертификатов нет", "No certificates"))
            return
        bundle = "\n".join(p.read_text("utf-8", "replace") for p in pems if "BEGIN CERTIFICATE" in p.read_text("utf-8", "replace"))
        (d / "bundle.pem").write_text(bundle + "\n")
        ST.set("extra_ca", str(d / "bundle.pem"))
        _MITM_CACHE.clear()
        audit("extra-ca", str(len(pems)))
        print("[+] " + L("CA подключены: %d" % len(pems), "CAs enabled: %d" % len(pems)))
    elif k == "3":
        ST.set("extra_ca", "")
        _MITM_CACHE.clear()
    mitm, iss, ok = detect_mitm()
    print("[*] MITM: %s  (%s)" % (c(L("да", "yes"), WARN_C) if mitm else c(L("нет", "no"), OK_C), iss or ("OK" if ok else "?")))


def pins_menu():
    # закрепление сертификата (SHA-256) для критичных доменов
    pins = ST.d.get("pins", {})
    for h, v in pins.items():
        print("  %s %s" % (h, dim(v[:16] + "…")))
    k = ask(L("Действие", "Action"), "", quit_ok=False, hint=L("a добавить домен · d удалить · Enter — назад", "a add domain · d delete · Enter = back")).lower()
    if k == "a":
        h = ask(L("Домен", "Domain"), "", quit_ok=False).lower()
        if h:
            try:
                fp = hashlib.sha256(tls_der(h)).hexdigest()
                print("[*] sha256: " + fp)
                if confirm(L("Закрепить этот отпечаток?", "Pin this fingerprint?"), True):
                    pins[h] = fp
                    ST.d["pins"] = pins
                    ST.save()
                    audit("pin", h)
            except Exception as e:
                print("[!] %s" % e)
    elif k == "d":
        h = ask(L("Домен", "Domain"), "", quit_ok=False)
        if pins.pop(h, None):
            ST.d["pins"] = pins
            ST.save()


def detect_vpn():
    # VPN включён? — по tun-интерфейсам (utun/tun/wg/ppp/ipsec) и по доступному локальному прокси-порту
    names = []
    try:
        names = [l.split(":")[0].strip() for l in Path("/proc/net/dev").read_text().splitlines()[2:]]
    except Exception:
        pass
    for cmd in (["ip", "-o", "link"], ["ifconfig", "-a"]):
        if shutil.which(cmd[0]):
            try:
                names += re.findall(r"^\d*:?\s*([a-z]+\d+)", subprocess.run(cmd, timeout=3).stdout.decode("utf-8", "replace"), re.M)
            except Exception:
                pass
    tun = [n for n in set(names) if re.match(r"(utun|tun|tap|wg|ppp|ipsec|zt)\d*", n)]
    lp = [p for p in (1082, 8080, 1080, 10808, 7890, 9090) if ping_once("127.0.0.1", p, 0.3)[0]]
    return bool(tun or lp or proxy_url()), {"tun": tun, "local_proxy_ports": lp, "proxy": bool(proxy_url())}


@resilient
def vpn_fallback_menu():
    on, det = detect_vpn()
    print("[*] VPN/proxy: %s  %s" % (c(L("обнаружен", "detected"), WARN_C) if on else c(L("не обнаружен", "not detected"), OK_C), dim(json.dumps(det))))
    k = menu(L("Сеть и VPN", "Network and VPN"), [
        ("1", L("Прямое соединение (обойти прокси) на этот запуск", "Direct connection (bypass proxy) for this run"), ""), ("2", L("Вернуть прокси из настроек", "Restore the configured proxy"), ""),
        ("3", L("Проверка интернета сейчас", "Check internet now"), ""), ("4", L("Найти лучший прокси", "Find best proxy"), ""), ("5", L("Режим DoH-DNS на этот запуск", "DoH DNS for this run"), "")], back=L("Продолжить", "Continue"))
    if k == "1":
        ST.ov["proxy"] = ""
        print("[+] " + L("Прокси отключён до перезапуска. Если не помогло — отключите VPN вручную и повторите.", "Proxy bypassed until restart. If it did not help — turn the VPN off manually and retry."))
    elif k == "2":
        ST.ov.pop("proxy", None)
    elif k == "3":
        ok, _ = functional_ping(5, 1)
        print(("[+] " if ok else "[!] ") + (L("интернет есть", "internet OK") if ok else L("интернета нет", "no internet")))
    elif k == "4":
        find_best_proxy()
    elif k == "5":
        ST.ov["dns_mode"] = "doh"
        DNS_CACHE.clear()


@resilient
def net_menu():
    while True:
        k = menu(L("Сеть, прокси и cookies", "Network, proxy & cookies"), [
            ("1", L("Проверка доступности сервисов", "Service reachability test"), ""), ("2", L("Прокси (шаблоны, LAN, логин/пароль)", "Proxy (templates, LAN, login/password)"), ST.g("proxy") and redact(ST.g("proxy")) or "-"),
            ("3", L("Найти лучший прокси", "Find best proxy"), ""), ("4", L("DNS: режим и серверы", "DNS: mode and servers"), "%s" % ST.g("dns_mode")), ("5", L("Внешний IP", "External IP"), ""),
            ("6", L("Тест скорости", "Speed test"), ""), ("7", L("Записать DNS в /etc/resolv.conf", "Write DNS to /etc/resolv.conf"), ""),
            ("8", L("Мастер cookies (вход в аккаунты)", "Cookies wizard (account login)"), ""), ("9", L("Удалить cookies", "Delete cookies"), ""),
            ("10", L("CA-сертификаты / проверка MITM", "CA certificates / MITM check"), ST.g("extra_ca") and "on" or "off"), ("11", L("Закрепление сертификатов (pinning)", "Certificate pinning"), str(len(ST.d.get("pins", {})))),
            ("12", L("Проверка интернета (пинг)", "Internet check (ping)"), ""), ("13", L("VPN: обход и диагностика", "VPN: bypass & diagnostics"), ""), ("14", L("Последние ошибки с причинами", "Latest errors with causes"), "")])
        if k == "q":
            return
        if k == "1":
            hosts = ["www.youtube.com", "i.ytimg.com", "redirector.googlevideo.com", "www.instagram.com", "i.instagram.com", "www.tiktok.com", "www.tikwm.com", "t.me", "api.fxtwitter.com", "rutube.ru", "soundcloud.com", "github.com", "pypi.org", "dl-cdn.alpinelinux.org"]
            rows = []
            for h in track(hosts, "net"):
                t = time.time()
                try:
                    ip = patched_gai(h, 443)[0][4][0]
                    d1 = int((time.time() - t) * 1000)
                    t = time.time()
                    s = socket.create_connection((ip, 443), 5)
                    s = make_ctx(True).wrap_socket(s, server_hostname=h)
                    s.close()
                    rows.append([h, c("OK", OK_C), "%dms" % d1, "%dms" % int((time.time() - t) * 1000), ip])
                except Exception as e:
                    rows.append([h, c("FAIL", ERR_C), "-", "-", trunc(str(e), 24)])
            table(rows, ["host", "", "DNS", "TCP+TLS", "info"])
        elif k == "2":
            set_proxy_ui()
        elif k == "3":
            find_best_proxy()
        elif k == "4":
            set_dns_ui()
        elif k == "5":
            for u in ("https://api.ipify.org", "https://icanhazip.com", "https://ifconfig.me/ip"):
                try:
                    print("[+] " + busy(L("Определяю IP", "Detecting IP"), lambda: http_get(u, retries=0, timeout=8).decode().strip()))
                    break
                except Exception as e:
                    print("[!] %s" % trunc(str(e), 60))
        elif k == "6":
            t = time.time()
            try:
                with Spin(L("Скачиваю 5 МБ", "Downloading 5 MB"), quiet=True):
                    d = http_get("https://speed.cloudflare.com/__down?bytes=5000000", timeout=30)
                print("[+] %s/s (%.1f Mbit/s)" % (fmt_size(len(d) / (time.time() - t)), len(d) * 8 / 1e6 / (time.time() - t)))
            except Exception as e:
                print("[!] %s" % e)
        elif k == "7":
            try:
                srv = [x.strip() for x in ST.g("dns_servers").split(",") if x.strip()] or ["1.1.1.1"]
                open("/etc/resolv.conf", "w").write("".join("nameserver %s\n" % s for s in srv + ["8.8.8.8"]))
                audit("resolv.conf", ",".join(srv))
                print("[+] OK")
            except OSError as e:
                print("[!] %s" % e)
        elif k == "8":
            cookies_wizard()
        elif k == "9":
            cookies_delete()
        elif k == "10":
            ca_menu()
        elif k == "11":
            pins_menu()
        elif k == "12":
            ok, det = functional_ping(5, 2)
            for host, o, ms in det:
                print("  %s %-20s %s" % (c("✓" if o else "✗", OK_C if o else ERR_C), host, dim("%d мс" % ms if o else "-")))
            print(("[+] " if ok else "[!] ") + (L("интернет есть", "internet OK") if ok else L("интернета нет", "no internet")))
        elif k == "13":
            vpn_fallback_menu()
        elif k == "14":
            show_last_errors()
        pause()


# ==========================================================================
#  НАСТРОЙКИ, ПРОФИЛИ, ПАТЧИ
# ==========================================================================
def preview():
    print()
    b = Bar(100, L("Образец", "Sample"), "")
    for i in range(0, 101, 4):
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
        if key == "proxy_allow_lan" and not cur:
            if not confirm(L("Общий доступ к прокси: другие устройства в вашей Wi-Fi сети смогут использовать ваш VPN. Не включайте в публичных сетях. Продолжить?", "Shared proxy access: other devices on your Wi-Fi may use your VPN. Do not enable on public networks. Continue?"), False):
                return
        ST.set(key, not cur)
        audit("setting", "%s=%s" % (key, not cur))
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
            set_proxy_ui()
            return
        if key == "doh_url":
            v = pick_one(L(ru, en), DOH_DEFAULT + ["custom"], cur)
            if v == "custom":
                v = ask("DoH URL", cur, quit_ok=False)
            if v:
                ST.set(key, v)
            return
        v = ask(L(ru, en), cur, quit_ok=False, hint=L("'-' очистить", "'-' clear"))
        ST.set(key, "" if v == "-" else v)
    DNS_CACHE.clear()


def apply_profile(d):
    ok = bad = 0
    for k, v in d.items():
        if ST.valid(k, v):
            ST.d[k] = v
            ok += 1
        else:
            bad += 1
    ST.save()
    audit("profile", "applied %d keys, %d invalid" % (ok, bad))
    return ok, bad


@resilient
def profiles_menu():
    while True:
        user = jload(PROFILES_FILE, {})
        names = list(BUILTIN_PROFILES) + list(user)
        k = menu(L("Профили настроек", "Settings profiles"), [
            ("1", L("Применить профиль", "Apply a profile"), "paranoid / social / archive / minimal"), ("2", L("Сохранить текущие настройки как профиль", "Save current settings as a profile"), ""),
            ("3", L("Удалить свой профиль", "Delete a custom profile"), ""), ("4", L("Экспорт всех настроек в JSON", "Export all settings to JSON"), "reports/"), ("5", L("Импорт настроек из JSON (с проверкой)", "Import settings from JSON (validated)"), "")])
        if k == "q":
            return
        if k == "1":
            nm = pick_one(L("Профиль", "Profile"), names, None, ["%s%s" % (n, dim(" (" + L("встроенный", "built-in") + ")") if n in BUILTIN_PROFILES else "") for n in names])
            if nm:
                ok, bad = apply_profile(BUILTIN_PROFILES.get(nm) or user.get(nm, {}))
                print("[+] " + L("Применено ключей: %d, пропущено: %d" % (ok, bad), "Keys applied: %d, skipped: %d" % (ok, bad)))
        elif k == "2":
            nm = sanitize(ask(L("Имя профиля", "Profile name"), "", quit_ok=False))
            if nm:
                user[nm] = {s[1]: ST.g(s[1]) for s in SCHEMA if s[1] not in ("proxy", "cookies_file", "extra_ca", "update_url", "out_dir")}
                jsave(PROFILES_FILE, user)
                print("[+] " + L("Сохранён: ", "Saved: ") + nm)
        elif k == "3":
            nm = pick_one(L("Удалить", "Delete"), list(user)) if user else None
            if nm:
                user.pop(nm, None)
                jsave(PROFILES_FILE, user)
        elif k == "4":
            p = BASE / "reports" / ("settings_%s.json" % now_stamp())
            data = {s[1]: ST.g(s[1]) for s in SCHEMA}
            data["proxy"] = redact(data["proxy"]) if data["proxy"] else ""
            jsave(p, {"app": "MediaForge", "build": os.environ.get("MF_BUILD", ""), "settings": data})
            print("[+] " + str(p))
        elif k == "5":
            fs = pick_files(BASE / "reports", {".json"}, False, L("Файл настроек", "Settings file"))
            if fs:
                try:
                    d = json.loads(fs[0].read_text("utf-8")).get("settings", {})
                    ok, bad = apply_profile({k_: v for k_, v in d.items() if k_ != "proxy"})
                    print("[+] " + L("Импортировано: %d, отклонено проверкой: %d" % (ok, bad), "Imported: %d, rejected by validation: %d" % (ok, bad)))
                except Exception as e:
                    print("[!] %s" % e)
        pause()


@resilient
def settings_menu():
    while True:
        k = menu(L("Настройки", "Settings"), [(str(i), L(ru, en), "") for i, (g, ru, en) in enumerate(GROUPS, 1)] + [
            ("8", L("Профили настроек", "Settings profiles"), "paranoid / social / archive / minimal"), ("9", L("Сбросить все настройки", "Reset all settings"), ""),
            ("10", L("Фоновая геолокация (iSH)", "Background location (iSH)"), "off" if (CONF / "noloc").exists() else "on")])
        if k == "q":
            return
        if k == "8":
            profiles_menu()
            continue
        if k == "9":
            if confirm(L("Сбросить?", "Reset?")):
                ST.d = {"lang": ST.g("lang")}
                ST.save()
                audit("settings-reset")
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
                vs = (c("on", OK_C) if v else c("off", ERR_C)) if s[3] == "bool" else c(trunc(redact(str(v)) if v != "" else "-", 24), INFO_C)
                print(" %s %s  %s" % (c("%2d" % i, accent(), True), trunc(L(s[5], s[6]), term_w() - 36), vs))
            try:
                v = ask(L("Номер параметра (q — назад)", "Parameter # (q = back)"), "", quit_ok=False)
            except Quit:
                break
            if v.lower() in ("q", "b", ""):
                break
            if v.isdigit() and 1 <= int(v) <= len(items):
                try:
                    edit_setting(items[int(v) - 1])
                except Quit:
                    continue
                if grp == "design":
                    preview()


def apply_patch_menu():
    # самопатчинг: вставленный патч (Python или shell) проверяется, применяется к файлу скрипта с бэкапом, при ошибке откат
    me = Path(CONF.joinpath("self_path").read_text().strip()) if (CONF / "self_path").exists() else None
    if not me or not me.exists():
        print("[!] " + L("Не знаю, где лежит файл скрипта (запустите через sh MediaForge.sh)", "Cannot find the script file (run via sh MediaForge.sh)"))
        return
    print(dim(L("Вставьте патч (Python или shell). Окончание — строка EOF. Python-патч получает путь к скрипту в переменной окружения MF_SELF.", "Paste the patch (Python or shell). End with a line EOF. A Python patch gets the script path in env MF_SELF.")))
    lines = []
    while True:
        x = input("")
        if x.strip() == "EOF":
            break
        lines.append(x)
    code = "\n".join(lines) + "\n"
    if len(lines) < 1:
        return
    is_py = not code.lstrip().startswith(("#!/bin/sh", "#!/bin/bash", "#!/usr/bin/env sh"))
    try:
        if is_py:
            compile(code, "patch", "exec")
        else:
            pf = CONF / "patch_check.sh"
            pf.write_text(code)
            if subprocess.run(["sh", "-n", str(pf)], timeout=20).returncode != 0:
                raise SyntaxError("sh -n failed")
    except Exception as e:
        print("[!] " + L("Ошибка синтаксиса патча: %s" % e, "Patch syntax error: %s" % e))
        return
    print("[*] sha256: %s  (%d %s)" % (hashlib.sha256(code.encode()).hexdigest()[:16], len(lines), L("строк", "lines")))
    print(dim("    " + trunc(lines[0], term_w() - 6)))
    print("[!] " + L("Патч выполняет произвольный код на вашем устройстве. Применяйте только то, чему доверяете.", "A patch runs arbitrary code on your device. Apply only what you trust."))
    if ask(L("Введите yes для применения", "Type yes to apply"), "", quit_ok=False).lower() != "yes":
        return
    bak = me.with_name(me.name + ".bak_" + now_stamp())
    shutil.copy2(str(me), str(bak))
    for old in sorted(me.parent.glob(me.name + ".bak_*"))[:-3]:
        old.unlink()
    pf = CONF / ("patch_%s.%s" % (now_stamp(), "py" if is_py else "sh"))
    pf.write_text(code)
    env = dict(os.environ, MF_SELF=str(me))
    r = subprocess.run([sys.executable if is_py else "sh", str(pf)], timeout=600, env=env)
    print(r.stdout.decode("utf-8", "replace")[-800:])
    ok = r.returncode == 0 and subprocess.run(["sh", "-n", str(me)], timeout=30).returncode == 0
    if ok:
        audit("self-patch", "%s ok" % pf.name)
        print("[+] " + L("Патч применён. Перезапуск…", "Patch applied. Restarting…"))
        write_action("rewrite")
        raise SystemExit(0)
    shutil.copy2(str(bak), str(me))
    audit("self-patch", "%s FAILED, rolled back" % pf.name)
    print("[!] " + L("Патч не применился — файл восстановлен из бэкапа (%s)" % bak.name, "Patch failed — file restored from backup (%s)" % bak.name))
    if r.stderr:
        print(dim(r.stderr.decode("utf-8", "replace")[-400:]))


# ==========================================================================
#  СРЕДА, ОТЛАДКА, ДИАГНОСТИКА, ПОМОЩЬ
# ==========================================================================
def versions():
    rows = [["python", sys.version.split()[0]]]
    for name, mod in (("yt-dlp", "yt_dlp.version"), ("gallery-dl", "gallery_dl.version")):
        try:
            m = __import__(mod, fromlist=["__version__"])
            rows.append([name, m.__version__])
        except Exception:
            rows.append([name, c("нет/missing", ERR_C)])
    for name, mod in (("yt-dlp-ejs", "yt_dlp_ejs"), ("mutagen", "mutagen"), ("telethon", "telethon"), ("PySocks", "socks")):
        try:
            __import__(mod)
            rows.append([name, "ok"])
        except Exception:
            rows.append([name, "-"])
    for name, cmd in (("ffmpeg", ["ffmpeg", "-version"]), ("ffprobe", ["ffprobe", "-version"]), ("exiftool", ["exiftool", "-ver"]), ("node", ["node", "-v"]), ("imagemagick", ["magick", "-version"]), ("jpegoptim", ["jpegoptim", "--version"]),
                      ("mediainfo", ["mediainfo", "--Version"]), ("tesseract", ["tesseract", "--version"]), ("curl", ["curl", "--version"])):
        if shutil.which(cmd[0]):
            r = subprocess.run(cmd, timeout=20)
            rows.append([name, (r.stdout.decode("utf-8", "replace").strip().splitlines() or ["ok"])[0][:40] if r.returncode < 128 else c("SIGSYS (%d)" % r.returncode, ERR_C)])
        else:
            rows.append([name, c("нет/missing", WARN_C)])
    return rows


def diag_env():
    # 20+ проверок окружения
    rows = []

    def chk(name, ok, info=""):
        rows.append([c("✓", OK_C) if ok is True else (c("!", WARN_C) if ok is None else c("✗", ERR_C)), name, trunc(str(info), 36)])
    chk("Python ≥ 3.10", sys.version_info >= (3, 10), sys.version.split()[0])
    for m in ("json", "ssl", "socket", "select", "zlib", "hashlib", "threading", "sqlite3", "readline", "termios"):
        try:
            __import__(m)
            chk("import " + m, True)
        except Exception as e:
            chk("import " + m, False if m in ("json", "ssl", "socket") else None, e)
    for m in ("yt_dlp", "gallery_dl", "mutagen"):
        try:
            __import__(m)
            chk(m, True)
        except Exception as e:
            chk(m, False if m != "mutagen" else None, e)
    for b in ("ffmpeg", "ffprobe", "curl", "wget", "openssl", "node", "exiftool"):
        chk(b, bool(shutil.which(b)) or None, shutil.which(b) or "—")
    try:
        r = subprocess.run(["ffmpeg", "-version"], timeout=20) if shutil.which("ffmpeg") else None
        chk("ffmpeg запускается / runs", (r.returncode < 128) if r else None, "rc=%s" % (r.returncode if r else "-"))
    except Exception as e:
        chk("ffmpeg runs", False, e)
    try:
        chk("Alpine", None, Path("/etc/alpine-release").read_text().strip() if Path("/etc/alpine-release").exists() else "—")
        chk("repositories", "alpine/v3" in Path("/etc/apk/repositories").read_text() if Path("/etc/apk/repositories").exists() else None, (Path("/etc/apk/repositories").read_text().splitlines() or ["-"])[0][-40:] if Path("/etc/apk/repositories").exists() else "—")
    except Exception:
        pass
    chk("resolv.conf writable", os.access("/etc/resolv.conf", os.W_OK), "")
    chk("/dev/location", os.path.exists("/dev/location") or None, "")
    chk("/dev/clipboard", os.path.exists("/dev/clipboard") or None, "")
    chk(L("запись в %s" % BASE, "write to %s" % BASE), os.access(str(BASE), os.W_OK), "")
    chk(L("свободно места", "free space"), free_mb() > 300, "%d MB" % free_mb())
    for nm in STATE_FILES:
        p = CONF / nm
        if p.exists():
            try:
                json.loads(p.read_text("utf-8"))
                chk(nm, True)
            except Exception:
                chk(nm, False, L("повреждён → Файлы → Починить", "damaged → Files → Repair"))
    ok, det = functional_ping(3, 1)
    chk(L("интернет", "internet"), ok, "%d/%d" % (sum(1 for _, o, _ in det if o), len(det)))
    t = time.time()
    try:
        patched_gai("www.google.com", 443)
        chk("DNS", True, "%d ms" % int((time.time() - t) * 1000))
    except Exception as e:
        chk("DNS", False, e)
    if proxy_url():
        ok2, ms, err = test_proxy(proxy_url())
        chk(L("прокси", "proxy"), ok2, "%d ms %s" % (ms, err))
    mitm, iss, vok = detect_mitm()
    chk("TLS/MITM", None if mitm else vok, iss or "OK")
    table([[a, b, c_] for a, b, c_ in rows], ["", L("Проверка", "Check"), L("Детали", "Details")])


HELP = [
    ("Быстрый старт", "Quick start", "Введите номер пункта и Enter. q или Ctrl+C — шаг назад (программа не закрывается). В главном меню выход — q.\nЛюбые ссылки: 1 «Умная загрузка». Накопить ссылки на потом: 6 «Список ссылок».\nПустая строка при вводе ссылок = конец ввода.",
     "Type an item number and Enter. q or Ctrl+C = one step back (the program does not close). Quit from the main menu with q.\nAny links: 1 'Smart download'. Collect links for later: 6 'Links list'.\nA blank line while entering links = end of input."),
    ("Список ссылок", "Links list", "Пункт 6: добавляйте ссылки без загрузки — они сохраняются в памяти. Когда готовы: «Скачать всё из списка» — сначала анализ (если медиа несколько — спросит), затем загрузка идёт сама.",
     "Item 6: add links without downloading — they are kept in memory. When ready: 'Download everything' — analysis first (asks if there are several media), then it runs on its own."),
    ("Соцсети", "Social", "Instagram, TikTok, Threads, Likee, X, Telegram, Bluesky: посты, рилс, карусели, аватарки, истории, актуальное. Для историй и приватного нужны cookies (Сеть → Мастер cookies). Telegram: фото, видео, кружки, голосовые, текст с форматированием; музыка и файлы — через Telethon.",
     "Instagram, TikTok, Threads, Likee, X, Telegram, Bluesky: posts, reels, carousels, avatars, stories, highlights. Stories/private need cookies (Network → Cookies wizard). Telegram: photos, video, circles, voice, formatted text; music/files need Telethon."),
    ("Telegram: текст", "Telegram: text", "Текст поста сохраняется в texts/: .html (шрифты, размеры, цвета, таблицы, цитаты, код), .md, .txt и .rich.json (полное дерево разметки). Формат — настройка «Текст из Telegram».",
     "Post text is saved to texts/: .html (fonts, sizes, colors, tables, quotes, code), .md, .txt and .rich.json (full markup tree). Format — setting 'Telegram text'."),
    ("Если что-то сломалось", "Troubleshooting", "Файлы → «Починить папки и файлы» лечит битые имена, права, JSON и ядро. Среда → «Диагностика». Отладка: sh MediaForge.sh --debug, лог ~/MediaForge/.config/debug.log. Alpine без нужды не меняется: SIGSYS (159) — просто перезапуск ядра.",
     "Files → 'Repair folders and files' fixes bad names, permissions, JSON and the core. Environment → 'Diagnostics'. Debug: sh MediaForge.sh --debug, log ~/MediaForge/.config/debug.log. Alpine is not changed needlessly: SIGSYS (159) just restarts the core."),
    ("Прокси, LAN, MITM", "Proxy, LAN, MITM", "Сеть → Прокси: шаблоны loopback/LAN (LAN включается в настройках), логин/пароль, проверка. Если прокси-клиент расшифровывает HTTPS — добавьте его CA: Сеть → CA-сертификаты.",
     "Network → Proxy: loopback/LAN templates (enable LAN in settings), login/password, test. If the proxy client decrypts HTTPS — add its CA: Network → CA certificates."),
    ("Планировщик", "Scheduler", "Планировщик запускает фоновый процесс: в заданное время берёт новое с канала/плейлиста. iSH должен оставаться активным.", "The scheduler runs a background process: at the given time it fetches new items from a channel/playlist. iSH must stay active."),
    ("Профили", "Profiles", "paranoid — максимум приватности; social — быстрые загрузки для соцсетей; archive — максимум метаданных; minimal — без анимаций.", "paranoid — max privacy; social — quick social downloads; archive — max metadata; minimal — no animations."),
]


def help_menu():
    while True:
        items = [(str(i), L(h[0], h[1]), "") for i, h in enumerate(HELP, 1)] + [("s", L("Поиск по справке", "Search help"), "")]
        k = menu(L("Помощь", "Help"), items)
        if k == "q":
            return
        if k == "s":
            q = ask(L("Что найти", "Search for"), "", quit_ok=False).lower()
            for h in HELP:
                if q and (q in (h[2] + h[3] + h[0] + h[1]).lower()):
                    print(c(L(h[0], h[1]), accent(), True))
                    print("  " + L(h[2], h[3]))
        else:
            h = HELP[int(k) - 1]
            print("\n" + c(L(h[0], h[1]), accent(), True) + "\n" + L(h[2], h[3]))
        pause()


def tour():
    # короткий тур при первом запуске
    steps = [(L("Главное меню", "Main menu"), L("Вводите номер пункта. q или Ctrl+C — назад.", "Type an item number. q or Ctrl+C = back.")),
             (L("Скачать", "Download"), L("Пункт 1: вставьте ссылки по одной, пустая строка — старт. Много медиа на странице? Скрипт найдёт все и спросит, что качать.", "Item 1: paste links one by one, blank line = go. Many media on a page? The script finds them all and asks what to take.")),
             (L("Список ссылок", "Links list"), L("Пункт 6: копите ссылки сейчас, качайте потом.", "Item 6: collect links now, download later.")),
             (L("Настройки", "Settings"), L("Пункт 17: темы, градиенты, подсказки, профили. t/a/s/y в главном меню — быстрые клавиши дизайна.", "Item 17: themes, gradients, hints, profiles. t/a/s/y in the main menu are design hotkeys."))]
    for i, (t, d) in enumerate(steps, 1):
        print("\n" + c("%d/%d  %s" % (i, len(steps), t), accent(), True) + "\n   " + d)
        try:
            input(dim("   Enter →"))
        except (EOFError, KeyboardInterrupt):
            break
    ST.d["_tour"] = 1
    ST.save()


def debug_analyze(url):
    # что нашёл каждый способ на странице (для отладки обнаружения нескольких медиа)
    rows = []

    def step(name, fn):
        t = time.time()
        try:
            r = fn()
            n = len(r) if isinstance(r, (list, tuple)) else (1 if r else 0)
            prev = ""
            if isinstance(r, list) and r:
                f = r[0]
                prev = (f.get("type", "") + " " + (f.get("title") or f.get("url") or "")[:30]) if isinstance(f, dict) else str(f)[:30]
            elif isinstance(r, dict):
                prev = (r.get("title") or "")[:30]
            rows.append([name, c("OK", OK_C) if n else c("0", WARN_C), str(n), "%dms" % int((time.time() - t) * 1000), trunc(prev, 28)])
        except NeedLogin:
            rows.append([name, c("login", WARN_C), "-", "%dms" % int((time.time() - t) * 1000), "cookies"])
        except Exception as e:
            rows.append([name, c("ERR", ERR_C), "-", "%dms" % int((time.time() - t) * 1000), trunc(str(e), 28)])
    sk = social_kind(url)
    if soc_dispatch(sk):
        step("social:" + sk, lambda: soc_dispatch(sk)(url, "auto"))
    step("yt-dlp probe", lambda: (lambda i: (i.get("entries") or [i]) if i else [])(probe_ytdlp(url)))
    step("gallery-dl", lambda: gallery_list(url)[0])
    step("page scrape", lambda: scrape_media(url))
    step("wayback", lambda: [wayback_url(url)] if wayback_url(url) else [])
    table(rows, [L("способ", "method"), "", "n", "time", L("пример", "sample")])


@resilient
def debug_menu():
    while True:
        k = menu(L("Отладка", "Debug"), [
            ("1", L("Режим отладки: ", "Debug mode: ") + ("ON" if ST.g("verbose") else "off"), L("всё пишется в debug.log", "everything goes to debug.log")), ("2", L("Анализ ссылки: что нашёл каждый способ", "Analyze a link: what each method found"), ""),
            ("3", L("Показать debug.log (последние строки)", "Show debug.log (latest lines)"), ""), ("4", L("Живой просмотр лога (Ctrl+C — выход)", "Live log viewer (Ctrl+C = exit)"), ""),
            ("5", L("Последние ошибки с причинами", "Latest errors with causes"), ""), ("6", L("Диагностика окружения (20+ проверок)", "Environment diagnostics (20+ checks)"), ""),
            ("7", L("Журнал сбоев (crash.log / fault.log)", "Crash logs (crash.log / fault.log)"), ""), ("8", L("Очистить логи", "Clear logs"), "")])
        if k == "q":
            return
        if k == "1":
            ST.set("verbose", not ST.g("verbose"))
        elif k == "2":
            u = ask(L("Ссылка", "Link"), "", quit_ok=False)
            if u and ensure_internet():
                debug_analyze(u)
        elif k == "3":
            try:
                print("\n".join(DEBUG_LOG.read_text("utf-8").splitlines()[-40:]))
            except Exception:
                print("[*] " + L("Лог пуст — включите режим отладки (пункт 1)", "Log is empty — enable debug mode (item 1)"))
        elif k == "4":
            pos = DEBUG_LOG.stat().st_size if DEBUG_LOG.exists() else 0
            print(dim(L("Слежу за логом… (Ctrl+C — выход)", "Watching the log… (Ctrl+C to exit)")))
            try:
                while True:
                    if DEBUG_LOG.exists() and DEBUG_LOG.stat().st_size > pos:
                        with open(str(DEBUG_LOG), "r", encoding="utf-8", errors="replace") as f:
                            f.seek(pos)
                            for ln_ in f:
                                col = ERR_C if " ERROR" in ln_ else WARN_C if " WARN" in ln_ else None
                                sys.stdout.write((c(ln_.rstrip(), col) if col else dim(ln_.rstrip())) + "\n")
                            pos = f.tell()
                    time.sleep(0.5)
            except KeyboardInterrupt:
                print()
        elif k == "5":
            show_last_errors()
        elif k == "6":
            diag_env()
        elif k == "7":
            for n in ("crash.log", "fault.log"):
                try:
                    t = (CONF / n).read_text()[-1500:]
                    print(c(n, accent(), True) + "\n" + (t or dim("(empty)")))
                except Exception:
                    print(dim("%s: —" % n))
        elif k == "8":
            for n in ("debug.log", "debug.log.1", "crash.log", "fault.log"):
                try:
                    (CONF / n).unlink()
                except OSError:
                    pass
            print("[+] OK")
        pause()


@resilient
def env_menu():
    while True:
        k = menu(L("Среда, обновление, отладка", "Environment, update, debug"), [
            ("1", L("Версии и состояние", "Versions & status"), ""), ("2", L("Обновить yt-dlp / gallery-dl / ejs", "Update yt-dlp / gallery-dl / ejs"), ""), ("3", L("yt-dlp Nightly", "yt-dlp Nightly"), ""),
            ("4", L("Обновить пакеты системы (apk)", "Update system packages (apk)"), ""), ("5", L("Починить окружение (Alpine меняется только если Python падает)", "Repair environment (Alpine changes only if Python crashes)"), ""),
            ("6", L("Обновить скрипт по URL", "Update script from URL"), ""), ("7", L("Все настройки и пути", "All settings & paths"), ""), ("8", L("Отладка и диагностика", "Debug & diagnostics"), ""),
            ("9", L("Журнал аудита (проверка цепочки)", "Audit log (chain check)"), ""), ("10", L("Установить OCR (tesseract)", "Install OCR (tesseract)"), ""), ("11", L("ffmpeg: LD_PRELOAD-обход SIGSYS", "ffmpeg: LD_PRELOAD SIGSYS workaround"), ""),
            ("12", L("Применить патч (самопатчинг)", "Apply a patch (self-patching)"), ""), ("13", L("Справка", "Help"), ""), ("14", L("Тур по программе", "Program tour"), ""),
            ("15", L("Установить curl_cffi (подмена TLS-отпечатка)", "Install curl_cffi (TLS fingerprint)"), L("опционально; может не собраться в iSH", "optional; may fail to build in iSH")),
            ("16", L("Самотест (--test)", "Self-test (--test)"), ""), ("17", L("Замер скорости (--benchmark)", "Benchmark (--benchmark)"), ""), ("18", L("Установить Tor + lyrebird", "Install Tor + lyrebird"), "")])
        if k == "q":
            return
        if k == "1":
            table(versions(), [L("Компонент", "Component"), L("Версия", "Version")])
            print(dim("ENV=%s  LANG=%s  Alpine=%s  free=%dMB" % (os.environ.get("MF_ENV"), ST.g("lang"), (Path("/etc/alpine-release").read_text().strip() if Path("/etc/alpine-release").exists() else "-"), free_mb())))
        elif k == "2":
            write_action("upgrade_tools")
            raise SystemExit(0)
        elif k == "3":
            write_action("nightly")
            raise SystemExit(0)
        elif k == "4":
            write_action("pkgupdate")
            raise SystemExit(0)
        elif k == "5":
            write_action("repair")
            raise SystemExit(0)
        elif k == "6":
            url = ST.g("update_url") or os.environ.get("MF_UPDATE_URL", "") or ask(L("URL нового MediaForge.sh", "URL of the new MediaForge.sh"), "", quit_ok=False)
            if not url:
                continue
            ST.set("update_url", url)
            try:
                txt = get_text(url)
            except Exception as e:
                print("[!] %s" % e)
                pause()
                continue
            if not txt.startswith("#!/bin/sh") or "MF_BUILD=" not in txt[:3000]:
                print("[!] " + L("Это не MediaForge — отмена", "Not a MediaForge file — cancelled"))
            elif confirm(L("Установить (sha256 %s)?" % hashlib.sha256(txt.encode()).hexdigest()[:12], "Install (sha256 %s)?" % hashlib.sha256(txt.encode()).hexdigest()[:12]), True):
                (CONF / "MediaForge.new").write_text(txt)
                write_action("applyupdate")
                raise SystemExit(0)
        elif k == "7":
            for s in SCHEMA:
                print("  %-18s = %s" % (s[1], redact(str(ST.g(s[1])))))
            print(dim(str(BASE)))
        elif k == "8":
            debug_menu()
            continue
        elif k == "9":
            ok, n, bad = audit_verify()
            print(("[+] " if ok else "[!] ") + L("Записей: %d. Цепочка %s" % (n, "цела" if ok else "НАРУШЕНА на строке %d" % bad), "Entries: %d. Chain %s" % (n, "intact" if ok else "BROKEN at line %d" % bad)))
            try:
                print("\n".join(AUDIT.read_text("utf-8").splitlines()[-8:]))
            except Exception:
                pass
        elif k == "10":
            write_action("optional")
            raise SystemExit(0)
        elif k == "11":
            write_action("ffmpeghack")
            raise SystemExit(0)
        elif k == "12":
            apply_patch_menu()
        elif k == "13":
            help_menu()
            continue
        elif k == "14":
            tour()
        elif k == "15":
            write_action("pip:curl_cffi")
            raise SystemExit(0)
        elif k == "16":
            self_test()
        elif k == "17":
            benchmark()
        elif k == "18":
            write_action("tor")
            raise SystemExit(0)
        pause()


# ==========================================================================
#  ЗАПУСК
# ==========================================================================
def status_line():
    q = len(jload(QUEUE, {}).get("jobs", []))
    nl = sum(1 for x in links_load() if x.get("status") != "done")
    return "%s py %s · %s · %dMB free%s%s%s%s" % (c(U("◆", "*"), accent()), sys.version.split()[0], ST.g("lang").upper(), free_mb(), (" · " + c("proxy", WARN_C)) if proxy_url() else "",
                                                    (" · " + c(L("очередь: %d" % q, "queue: %d" % q), WARN_C)) if q else "", (" · " + c(L("ссылок: %d" % nl, "links: %d" % nl), INFO_C)) if nl else "",
                                                    (" · " + c("DEBUG", ERR_C)) if (MF_DEBUG or ST.g("verbose")) else "")


def guarded(fn):
    # действие главного меню: Ctrl+C / q / ошибка → возврат в меню (программа не закрывается)
    try:
        fn()
    except (Quit, KeyboardInterrupt):
        print("\n[*] " + L("↩ Назад в главное меню", "↩ Back to the main menu"))
        UNATT[0] = False
        return
    except SystemExit:
        raise
    except Exception:
        tb = traceback.format_exc()
        print("\n[!] " + L("Ошибка: ", "Error: ") + tb.strip().splitlines()[-1])
        note_error("internal", tb.strip().splitlines()[-1])
        try:
            with open(str(CONF / "crash.log"), "a") as f:
                f.write("== %s\n%s\n" % (time.ctime(), redact(tb)))
        except Exception:
            pass
    UNATT[0] = False
    pause()




# ==========================================================================
#  «ПРОБИВНОСТЬ»: каскад HTTP (curl_cffi → urllib/curl/wget/openssl), сессии Cloudflare, капча-сервисы
#  Всё опционально: без curl_cffi/ключей работает базовый режим.
# ==========================================================================
SESS_DIR = CONF / "sessions"
CF_BROWSERS = ["chrome124", "chrome120", "chrome119", "safari17_0", "edge101", "chrome110"]


class CFChallenge(HttpErr):
    pass


def cffi_usable():
    try:
        import curl_cffi.requests  # noqa
        return True
    except Exception:
        return False


def is_cf(headers, body):
    # признаки защитной страницы Cloudflare / DDoS-Guard / Akamai
    h = {str(k).lower(): str(v).lower() for k, v in dict(headers or {}).items()}
    b = (body or b"")[:6000].lower() if isinstance(body, bytes) else str(body)[:6000].lower()
    return (h.get("cf-mitigated") == "challenge" or ("cloudflare" in h.get("server", "") and (b"just a moment" in b.encode() if isinstance(b, str) else b"just a moment" in b))
            or "cf-chl" in str(b) or "ddos-guard" in h.get("server", "") or "attention required" in str(b) and "cloudflare" in str(b))


def session_load(host):
    # сохранённая сессия хоста (cookies + User-Agent) — только если прокси/сеть та же, что при получении
    try:
        d = json.loads((SESS_DIR / (host + ".json")).read_text("utf-8"))
        if d.get("via") == (proxy_url() or "direct") and time.time() - d.get("ts", 0) < 86400 * 7:
            return d
    except Exception:
        pass
    return None


def session_save(host, cookies, ua_):
    SESS_DIR.mkdir(parents=True, exist_ok=True)
    p = SESS_DIR / (host + ".json")
    p.write_text(json.dumps({"cookies": cookies, "ua": ua_, "via": proxy_url() or "direct", "ts": time.time()}), "utf-8")
    os.chmod(str(p), 0o600)
    audit("session-save", host)


def _cffi_get(url, hd, timeout, body, verify):
    from curl_cffi import requests as cr
    kw = {"headers": hd, "timeout": timeout, "allow_redirects": True, "verify": verify}
    p = proxy_url()
    if p:
        kw["proxies"] = {"http": p, "https": p}
    last = None
    for imp in random.sample(CF_BROWSERS, 2):
        try:
            r = cr.request("POST" if body is not None else "GET", url, data=body, impersonate=imp, **kw)
            dlog("cffi %s %s -> %s" % (imp, trunc(url, 50), r.status_code))
            if r.status_code in (403, 429, 503) and is_cf(r.headers, r.content[:6000]):
                raise CFChallenge(r.status_code, "challenge")
            if r.status_code >= 400:
                raise HttpErr(r.status_code)
            return r.content, str(r.url)
        except (CFChallenge, HttpErr):
            raise
        except Exception as e:
            last = e
    raise IOError(str(last))


def cf_flaresolverr(url):
    # FlareSolverr (если пользователь запустил его где-то в сети): возвращает cookies + User-Agent
    base = ST.g("flaresolverr_url").strip()
    if not base:
        raise IOError("flaresolverr_url empty")
    d = json.loads(http_get(base, jbody={"cmd": "request.get", "url": url, "maxTimeout": 60000}, timeout=90, retries=0).decode("utf-8", "replace"))
    s = d.get("solution") or {}
    if d.get("status") != "ok" or not s:
        raise IOError("flaresolverr: %s" % d.get("message"))
    return {c_["name"]: c_["value"] for c_ in s.get("cookies", [])}, s.get("userAgent", ua()), (s.get("response") or "").encode("utf-8", "replace")


def cf_capsolver(url):
    # CapSolver API (ключ в настройках): задача AntiCloudflareTask
    key = ST.g("capsolver_key").strip()
    if not key:
        raise IOError("capsolver_key empty")
    t = json.loads(http_get("https://api.capsolver.com/createTask", jbody={"clientKey": key, "task": {"type": "AntiCloudflareTask", "websiteURL": url, "proxy": ST.g("proxy") or ""}}, retries=0).decode())
    tid = t.get("taskId")
    if not tid:
        raise IOError("capsolver: %s" % t.get("errorDescription"))
    for _ in range(40):
        time.sleep(3)
        r = json.loads(http_get("https://api.capsolver.com/getTaskResult", jbody={"clientKey": key, "taskId": tid}, retries=0).decode())
        if r.get("status") == "ready":
            s = r.get("solution") or {}
            return dict(s.get("cookies") or {}) if isinstance(s.get("cookies"), dict) else {c_["name"]: c_["value"] for c_ in s.get("cookies", [])}, s.get("userAgent", ua()), b""
        if r.get("status") == "failed":
            break
    raise IOError("capsolver failed")


def cf_bypass(url, hd, timeout, body):
    # цепочка при челлендже: cloudscraper → FlareSolverr → CapSolver; результат кэшируется в sessions/<host>.json
    host = urlparse(url).hostname or ""
    errs = []
    steps = [("cloudscraper", None)]
    if ST.g("captcha_service") in ("flaresolverr", "capsolver"):
        steps.append((ST.g("captcha_service"), None))
    for name, _ in steps:
        try:
            with Spin(L("Cloudflare: %s" % name, "Cloudflare: %s" % name), quiet=True):
                if name == "cloudscraper":
                    import cloudscraper
                    r = cloudscraper.create_scraper().get(url, timeout=timeout)
                    if r.status_code >= 400:
                        raise HttpErr(r.status_code)
                    return r.content, url
                cookies, ua_, page = cf_flaresolverr(url) if name == "flaresolverr" else cf_capsolver(url)
            session_save(host, cookies, ua_)
            if page and body is None:
                return page, url
            hd2 = dict(hd, **{"User-Agent": ua_, "Cookie": "; ".join("%s=%s" % kv for kv in cookies.items())})
            return _get_one_basic(url, hd2, timeout, 1, body)
        except ImportError:
            errs.append("cloudscraper не установлен")
        except Exception as e:
            errs.append("%s: %s" % (name, str(e)[:60]))
    print("[!] " + L("Cloudflare-защита не пройдена (%s)." % "; ".join(errs), "Cloudflare protection not passed (%s)." % "; ".join(errs)))
    print(dim("    " + L("Что можно: (1) вставить cf_clearance и User-Agent из браузера: Сеть → Мастер cookies; (2) сменить прокси/Tor; (3) FlareSolverr или CapSolver в настройках сети; (4) установить curl_cffi (pip).",
                         "Options: (1) paste cf_clearance from the browser: Network → Cookies wizard; (2) change proxy/Tor; (3) FlareSolverr or CapSolver in network settings; (4) install curl_cffi (pip).")))
    raise CFChallenge(403, "cloudflare challenge")


_get_one_basic = _get_one


def _get_one(url, hd, timeout, retries, body):
    # новый каскад: сохранённая сессия → curl_cffi (подмена отпечатка TLS) → прежний каскад → обход челленджа
    host = urlparse(url).hostname or ""
    hd = dict(hd)
    if "Cookie" not in hd:
        ck = cookie_header(host)
        if ck:
            hd["Cookie"] = ck
    sess = session_load(host)
    if sess:
        hd["User-Agent"] = sess["ua"]
        hd["Cookie"] = "; ".join(filter(None, [hd.get("Cookie", ""), "; ".join("%s=%s" % kv for kv in sess["cookies"].items())]))
    if ST.g("impersonate") and cffi_usable() and not is_local_host(host):
        try:
            return _cffi_get(url, hd, timeout, body, host not in INSECURE)
        except HttpErr as e:
            if e.code in (401, 404, 410) and not isinstance(e, CFChallenge):
                raise
            dlog("cffi failed (%s), falling back" % e, "WARN")
        except Exception as e:
            dlog("cffi error: %s" % e, "WARN")
    try:
        return _get_one_basic(url, hd, timeout, retries, body)
    except HttpErr as e:
        if e.code in (403, 429, 503) and not is_local_host(host):
            return cf_bypass(url, hd, timeout, body)
        raise


# ==========================================================================
#  Галерейный сайт с API (JSON-пагинация), зеркала, запасной разбор — без упоминаний в интерфейсе
# ==========================================================================
GAL_HOSTS = ("fapello.com", "fapello.is", "fapello.su")


def soc_gallery(url, want="auto"):
    p = urlparse(url)
    parts = [x for x in p.path.split("/") if x]
    if not parts:
        return []
    slug = parts[0]
    sub = "social/gallery/" + sanitize(slug)
    hosts = [p.netloc] + [h for h in GAL_HOSTS if h != p.hostname]
    last = None
    for h in hosts:
        root = "%s://%s" % (p.scheme if h == p.netloc else "https", h)
        try:
            t = get_text("%s/%s/" % (root, slug), headers={"Referer": root + "/", "User-Agent": UA_DESK})
            m = re.search(r"/api/media/(\d+)/", t) or re.search(r'"(?:profile_id|profileId|user_id)"\s*:\s*"?(\d+)', t) or re.search(r'data-(?:profile-)?id="(\d+)"', t)
            if not m:
                last = IOError("profile id not found")
                items = [mkitem("video" if ext_of(i["url"].split("?")[0]) in VEXT else "photo", i["url"], i["title"], root + "/", None, sub) for i in scrape_media(root + "/%s/" % slug, t)
                         if ext_of(i["url"].split("?")[0]) in IEXT | VEXT and "/avatar" not in i["url"]]
                if items:
                    return items
                continue
            pid, out, seen, page = m.group(1), [], set(), 1
            bar = Bar(None, L("API-страницы", "API pages"))
            while page <= 300:
                d = json.loads(http_get("%s/api/media/%s/%d/1" % (root, pid, page), headers={"Referer": root + "/", "X-Requested-With": "XMLHttpRequest"}, retries=1).decode("utf-8", "replace") or "[]")
                rows = d if isinstance(d, list) else (d.get("data") or d.get("media") or [])
                new = [r_ for r_ in rows if isinstance(r_, dict) and (r_.get("newUrl") or r_.get("url")) and (r_.get("newUrl") or r_.get("url")) not in seen]
                if not new:
                    break
                for r_ in new:
                    u = r_.get("newUrl") or r_.get("url")
                    seen.add(u)
                    out.append(mkitem("video" if ext_of(u.split("?")[0]) in VEXT or str(r_.get("type")) == "2" else "photo", u, "%s #%d" % (slug, len(out) + 1), root + "/", "%s_%04d%s" % (sanitize(slug), len(out) + 1, ext_of(u.split("?")[0]) or ".jpg"), sub))
                bar.update(page)
                page += 1
                time.sleep(random.uniform(0.3, 1.0) if ST.g("antibot") else 0)
            bar.close()
            if out:
                return out
        except KeyboardInterrupt:
            raise
        except Exception as e:
            last = e
            dlog("gallery api %s failed: %s" % (h, e), "WARN")
    try:
        urls, err = gallery_list(url)
        if urls:
            return [mkitem("video" if ext_of(u.split("?")[0]) in VEXT else "photo", u, "item", url, None, sub) for u in urls]
    except Exception:
        pass
    if last:
        raise last
    return []


# ==========================================================================
#  Creator Platforms: Boosty (API + токен), остальные — gallery-dl/yt-dlp с cookies
# ==========================================================================
CREATORS = [("boosty", "Boosty", ("boosty.to",)), ("patreon", "Patreon", ("patreon.com",)), ("fanbox", "Fanbox", ("fanbox.cc",)), ("fantia", "Fantia", ("fantia.jp",)),
            ("gumroad", "Gumroad", ("gumroad.com",)), ("subscribestar", "SubscribeStar", ("subscribestar.com", "subscribestar.adult")), ("kofi", "Ko-fi", ("ko-fi.com",)), ("other", "Other / Другое", ())]


def creator_kind(url):
    h = (urlparse(url).hostname or "").lower().replace("www.", "")
    for k, _, hs in CREATORS:
        if any(h == x or h.endswith("." + x) for x in hs):
            return k
    return ""


def boosty_token():
    raw = cookie_value("boosty.to", "auth")
    if not raw:
        return ""
    try:
        return json.loads(unquote(raw)).get("accessToken", "")
    except Exception:
        return ""


def boosty_items(post, sub):
    out, pid = [], str(post.get("id", "post"))[:8]
    n = 0
    for blk in post.get("data") or []:
        t = blk.get("type")
        n += 1
        if t == "image" and blk.get("url"):
            out.append(mkitem("photo", blk["url"], post.get("title") or pid, "https://boosty.to/", "boosty_%s_%d.jpg" % (pid, n), sub))
        elif t in ("ok_video", "video"):
            urls = {u.get("type"): u.get("url") for u in blk.get("playerUrls", []) if u.get("url")}
            for q in ("ultra_hd", "quad_hd", "full_hd", "high", "medium", "low", "tiny"):
                if urls.get(q):
                    out.append(mkitem("video", urls[q], blk.get("title") or post.get("title") or pid, "https://boosty.to/", "boosty_%s_%d.mp4" % (pid, n), sub))
                    break
            else:
                hl = urls.get("hls") or urls.get("dash")
                if hl:
                    out.append(mkitem("video", hl, post.get("title") or pid, "https://boosty.to/", "boosty_%s_%d.mp4" % (pid, n), sub))
        elif t == "audio_file" and blk.get("url"):
            out.append(mkitem("audio", blk["url"], blk.get("title") or pid, "https://boosty.to/", "boosty_%s_%d.mp3" % (pid, n), sub))
        elif t == "text" and blk.get("content"):
            try:
                parts = json.loads(blk["content"])
                txt = "".join(p_[0] for p_ in parts if isinstance(p_, list) and p_ and isinstance(p_[0], str))
            except Exception:
                txt = ""
            if txt.strip():
                out.append(make_text_item("<p>%s</p>" % html.escape(txt).replace("\n", "<br>"), post.get("title") or pid, sub, "boosty_%s_text%d" % (pid, n), "https://boosty.to/"))
    return out


def soc_boosty(url, want="auto"):
    parts = [x for x in urlparse(url).path.split("/") if x]
    if not parts:
        return []
    user = parts[0]
    sub = "social/boosty/" + sanitize(user)
    tok = boosty_token()
    hd = {"Referer": "https://boosty.to/", "Authorization": "Bearer " + tok} if tok else {"Referer": "https://boosty.to/"}
    if len(parts) >= 3 and parts[1] == "posts":
        d = get_json("https://api.boosty.to/v1/blog/%s/post/%s" % (user, parts[2]), headers=hd)
        if d.get("hasAccess") is False and not tok:
            raise NeedLogin("boosty.to")
        if d.get("hasAccess") is False:
            print("[!] " + L("Нет доступа к посту (подписка не оформлена или токен устарел)", "No access to the post (no subscription or expired token)"))
        return boosty_items(d, sub)
    out, offset, pages = [], 0, 0
    while pages < max(1, (ST.g("playlist_limit") or 20) // 10):
        d = get_json("https://api.boosty.to/v1/blog/%s/post/?limit=10&offset=%s" % (user, offset), headers=hd)
        for post in d.get("data", []):
            if post.get("hasAccess") is False and not tok:
                continue
            out += boosty_items(post, sub)
        ex = d.get("extra") or {}
        pages += 1
        if ex.get("isLast") or not d.get("data"):
            break
        offset = ex.get("offset") or offset + 10
    if not out and not tok:
        raise NeedLogin("boosty.to")
    return out


def creator_resolve(url, want="auto"):
    # платформа → (элементы). Boosty: внутренний API; остальные: gallery-dl → yt-dlp (cookies берутся автоматически)
    k = creator_kind(url)
    if k == "boosty":
        try:
            it = soc_boosty(url, want)
            if it:
                return it
        except NeedLogin:
            raise
        except Exception as e:
            dlog("boosty api failed: %s" % e, "WARN")
    host = urlparse(url).hostname or ""
    if not cookies_for(host):
        print("[*] " + L("Для платного контента нужны cookies: Сеть → Мастер cookies (%s)." % host.replace("www.", ""), "Paid content needs cookies: Network → Cookies wizard (%s)." % host.replace("www.", "")))
    sub = "social/%s" % (k or "creators")
    ua_mobile = "Patreon/126.9.0.15 (Android; Android 14; Scale/2.10)" if k == "patreon" else None
    if ua_mobile:
        ST.ov["ua"] = "desktop"
    return [mkitem("photo", url, L("целиком через gallery-dl", "whole via gallery-dl"), None, None, sub, src="gallery", alts=[{"src": "ytdlp", "url": url, "kind": "video", "type": "video", "title": url}])]


@resilient
def creators_menu():
    while True:
        k = menu(L("Creator Platforms", "Creator Platforms"), [(str(i), nm, L("API + cookies/токен", "API + cookies/token") if key == "boosty" else "gallery-dl / yt-dlp") for i, (key, nm, _) in enumerate(CREATORS, 1)] + [("c", L("Мастер cookies / токен", "Cookies / token wizard"), "")],
                 sub=L("Закрытый контент требует вход: cookies (Netscape) или Cookie-строка из браузера", "Locked content needs login: cookies (Netscape) or the Cookie string from the browser"))
        if k == "q":
            return
        if k == "c":
            cookies_wizard()
            continue
        u = ask(L("Ссылка на пост, профиль или список", "Post, profile or list link"), "", quit_ok=False)
        if not u:
            continue
        try:
            items = creator_resolve(u)
        except NeedLogin as e:
            login_hint(str(e) or u)
            continue
        except KeyboardInterrupt:
            raise Interrupt()
        except Exception as e:
            note_error(u, e)
            print("[!] %s" % trunc(str(e), term_w() - 6))
            continue
        run_items(items)
        pause()


# ==========================================================================
#  МУЗЫКА: Spotify, Яндекс Музыка, VK, Apple Music, Deezer… → поиск на YouTube/SoundCloud; SoundCloud и YT Music напрямую
# ==========================================================================
def _walk_json(o, pred, out):
    if isinstance(o, dict):
        if pred(o):
            out.append(o)
        for v in o.values():
            _walk_json(v, pred, out)
    elif isinstance(o, list):
        for v in o:
            _walk_json(v, pred, out)


def spotify_tracks(url):
    # embed-страница Spotify (без входа): треки, альбомы, плейлисты → [(артист, название, альбом)]
    m = re.search(r"open\.spotify\.com/(?:intl-\w+/)?(track|album|playlist|episode)/(\w+)", url)
    if not m:
        raise IOError("unsupported spotify link")
    kind, sid = m.groups()
    t = get_text("https://open.spotify.com/embed/%s/%s" % (kind, sid), headers={"User-Agent": UA_DESK})
    mm = re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', t, re.S)
    tracks = []
    if mm:
        data = json.loads(mm.group(1))
        lst = []
        _walk_json(data, lambda d: "title" in d and "subtitle" in d and str(d.get("uri", "")).startswith("spotify:track"), lst)
        for d in lst:
            tracks.append((d["subtitle"], d["title"], ""))
        if not tracks:
            ents = []
            _walk_json(data, lambda d: d.get("type") == "track" and "name" in d and ("artists" in d or "subtitle" in d), ents)
            for d in ents[:1]:
                art = ", ".join(a.get("name", "") for a in d.get("artists", [])) or d.get("subtitle", "")
                tracks.append((art, d["name"], ""))
    if not tracks:
        og = og_meta(t, "og:title")
        ds = og_meta(t, "og:description")
        art = ds.split("·")[0].strip() if "·" in ds else ""
        if og:
            tracks.append((art, og, ""))
    return tracks


def og_music_meta(url):
    t = get_text(url, headers={"User-Agent": UA_DESK})
    title = og_meta(t, "og:title") or (re.search(r"<title>(.*?)</title>", t, re.S) or [None, ""])[1]
    title = re.sub(r"\s*[\|—-]\s*(Яндекс\s*Музык\w*|Spotify|Apple Music|Deezer|VK|ВКонтакте|Tidal).*$", "", html.unescape(title)).strip()
    m = re.match(r"(.+?)\s+(?:—|-|by|от)\s+(.+)", title)
    return (m.group(2), m.group(1), "") if m else ("", title, "")


MUSIC_SITES = {"spotify": ("open.spotify.com",), "yandex": ("music.yandex.ru", "music.yandex.com", "music.yandex.by", "music.yandex.kz"), "vkaudio": ("vk.com", "vk.ru"), "apple": ("music.apple.com",),
               "deezer": ("deezer.com",), "tidal": ("tidal.com", "listen.tidal.com"), "amazon": ("music.amazon.com",), "soundcloud": ("soundcloud.com",), "ytmusic": ("music.youtube.com",)}


def music_kind(url):
    h = (urlparse(url).hostname or "").lower().replace("www.", "")
    p = urlparse(url).path
    for k, hs in MUSIC_SITES.items():
        if any(h == x or h.endswith("." + x) for x in hs):
            if k == "vkaudio" and "/audio" not in p and "music" not in p:
                continue
            return k
    return ""


def music_item(artist, title, album="", sub="music"):
    q = ("%s - %s" % (artist, title)).strip(" -")
    return mkitem("audio", "music:" + q, q, None, None, sub, src="music", meta={"artist": artist, "title": title, "album": album}, query=q)


def vk_audio_items(url):
    # VK-музыка: нужен токен (настройка vk_token): audio.getById → m3u8 → ffmpeg; без токена — подсказка
    tok = ST.g("vk_token").strip()
    m = re.search(r"audio(-?\d+_\d+)", url)
    if not tok or not m:
        raise NeedLogin("vk.com")
    d = get_json("https://api.vk.com/method/audio.getById?audios=%s&access_token=%s&v=5.131" % (m.group(1), tok), headers={"User-Agent": "KateMobileAndroid/56 lite-460 (Android 4.4.2; SDK 19; x86; unknown Android SDK built for x86; en)"})
    r = (d.get("response") or [None])[0]
    if not r or not r.get("url"):
        raise IOError("vk audio: %s" % (d.get("error", {}).get("error_msg") or "no url"))
    return [mkitem("audio", r["url"], "%s - %s" % (r.get("artist", ""), r.get("title", "")), "https://vk.com/", sanitize("%s - %s" % (r.get("artist", ""), r.get("title", ""))) + ".m4a", "music/vk")]


def music_resolve(url):
    k = music_kind(url)
    if k in ("soundcloud", "ytmusic"):
        return [mkitem("audio", url, url, None, None, "music", src="ytdlp", jkind="audio")]
    if k == "spotify":
        return [music_item(a, t, al, "music/spotify") for a, t, al in spotify_tracks(url)]
    if k == "vkaudio":
        return vk_audio_items(url)
    if k in ("yandex", "apple", "deezer", "tidal", "amazon"):
        a, t, al = og_music_meta(url)
        alts = [{"src": "music", "url": "music:%s - %s" % (a, t), "kind": "audio", "type": "audio", "title": t, "meta": {"artist": a, "title": t, "album": al}, "query": ("%s - %s" % (a, t)).strip(" -")}] if t else None
        return [mkitem("audio", url, "%s - %s" % (a, t) if t else url, None, None, "music/" + k, src="ytdlp", jkind="audio", alts=alts)]
    return []


def tag_audio(path, meta):
    try:
        import mutagen
        f = mutagen.File(str(path), easy=True)
        if f is None:
            return
        for k_, v in (("artist", meta.get("artist")), ("title", meta.get("title")), ("album", meta.get("album"))):
            if v:
                f[k_] = v
        f.save()
    except Exception as e:
        dlog("tag failed: %s" % e, "WARN")


def music_download(job):
    # поиск трека по «артист — название»: YouTube → SoundCloud; теги записываются mutagen
    q = job.get("query") or job.get("title") or ""
    last = ""
    for pre in ("ytsearch1:%s official audio", "ytsearch1:%s", "scsearch1:%s"):
        ok, res = ytdlp_chain(pre % q, "audio")
        if ok:
            if job.get("meta"):
                tag_audio(res, job["meta"])
            return True, res
        last = res
    return False, last


@resilient
def music_menu():
    while True:
        k = menu(L("Музыка и стриминги", "Music & streaming"), [
            ("1", L("Ссылка на трек / альбом / плейлист", "Track / album / playlist link"), "Spotify, SoundCloud, YT Music, Яндекс, VK, Apple, Deezer…"),
            ("2", L("Поиск трека по названию", "Search a track by name"), "YouTube → SoundCloud"), ("3", L("Список «Артист - Название» (по строке)", "List 'Artist - Title' (one per line)"), ""),
            ("4", L("Токен VK для музыки", "VK token for music"), "vk_token"), ("5", L("Мастер cookies (Яндекс/SoundCloud/VK)", "Cookies wizard (Yandex/SoundCloud/VK)"), "")],
            sub=L("Spotify/Яндекс/Apple/Deezer: берутся название и артист → трек находится на YouTube/SoundCloud и скачивается с тегами", "Spotify/Yandex/Apple/Deezer: title and artist are read → the track is found on YouTube/SoundCloud and saved with tags"))
        if k == "q":
            return
        if k == "1":
            for u in read_urls():
                try:
                    its = music_resolve(u)
                except NeedLogin as e:
                    print("[!] " + L("VK-музыка: нужен токен (пункт 4) — иначе используйте ссылку на YouTube/SoundCloud", "VK music needs a token (item 4)"))
                    continue
                except Exception as e:
                    note_error(u, e)
                    print("[!] %s" % trunc(str(e), term_w() - 6))
                    continue
                if not its:
                    its = [i for i in [mkitem("audio", u, u, None, None, "music", src="ytdlp", jkind="audio")]]
                run_items(its)
        elif k == "2":
            q = ask(L("Название / артист", "Title / artist"), "", quit_ok=False)
            if q:
                run_items([music_item("", q)])
        elif k == "3":
            lines = []
            print(dim(L("Строки вида «Артист - Название», пустая строка — конец", "Lines like 'Artist - Title', blank line = end")))
            while True:
                x = ask("#%d" % (len(lines) + 1), "", quit_ok=True)
                if not x:
                    break
                lines.append(x)
            its = []
            for ln_ in lines:
                a, _, t = ln_.partition(" - ")
                its.append(music_item(a.strip(), t.strip()) if t else music_item("", ln_))
            run_items(its)
        elif k == "4":
            v = ask(L("Токен VK (Kate Mobile / access_token)", "VK token (Kate Mobile / access_token)"), "", quit_ok=False)
            if v:
                ST.set("vk_token", v)
        elif k == "5":
            cookies_wizard()
        pause()


# ==========================================================================
#  СОДЕРЖИМОЕ СТРАНИЦЫ / ВСЕГО САЙТА: фото (в оригинале), видео, аудио, файлы, текст
# ==========================================================================
FILE_EXT = {".pdf", ".zip", ".rar", ".7z", ".tar", ".gz", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx", ".apk", ".ipa", ".epub", ".mobi", ".fb2", ".iso", ".dmg", ".torrent", ".txt", ".csv", ".json", ".ttf", ".otf"}
IMG_ATTRS = ("data-original", "data-full", "data-fullsize", "data-large", "data-zoom-src", "data-hires", "data-orig", "data-image", "data-src-large", "data-lazy-src", "data-src", "src")
ORIG_RULES = CONF / "imgrules.json"


def srcset_best(s):
    best, bw = "", -1
    for part in (s or "").split(","):
        bits = part.strip().split()
        if not bits:
            continue
        w = 0
        if len(bits) > 1:
            m = re.match(r"([\d.]+)[wx]", bits[1])
            w = float(m.group(1)) * (1 if bits[1].endswith("w") else 1000) if m else 0
        if w >= bw:
            best, bw = bits[0], w
    return best


def derive_originals(u):
    # варианты «оригинала» по типичным шаблонам миниатюр (все проверяются при скачивании, порядок — от вероятного)
    out = []
    v = re.sub(r"-\d{2,4}x\d{2,4}(?=\.\w{3,4}(?:\?|$))", "", u)
    out.append(v)
    out.append(re.sub(r"([_-])(thumb|thumbnail|small|medium|preview|sm|s|t|mini)(?=\.\w{3,4}(?:\?|$))", "", u, flags=re.I))
    out.append(re.sub(r"/(thumbs?|thumbnails?|small|medium|preview|resized?|cache)/", "/original/", u, flags=re.I))
    out.append(re.sub(r"/(thumbs?|thumbnails?|small|medium|preview)/", "/", u, flags=re.I))
    out.append(re.sub(r"[?&](w|h|width|height|size|resize|quality|q)=[^&]*", "", u).rstrip("?&"))
    out.append(re.sub(r"=[swh]\d+(-[a-z0-9-]+)?$", "=s0", u))
    out.append(re.sub(r"/(?:w|h|c|q)_\d+(?:,[a-z]_[\w:]+)*/", "/", u))
    out.append(re.sub(r"/\d{2,4}x\d{2,4}/", "/", u))
    return [x for x in dict.fromkeys(out) if x and x != u]


def host_rules(host):
    d = jload(ORIG_RULES, {})
    return d.get(host, []) + d.get(host.replace("www.", ""), [])


def apply_rules(u, host):
    for r in host_rules(host):
        try:
            v = re.sub(r["find"], r["repl"], u) if r.get("regex") else u.replace(r["find"], r["repl"])
            if v != u:
                return v
        except re.error:
            continue
    return None


def learn_rule(thumb, orig):
    # из пары «миниатюра → оригинал» выводит правило замены (общий префикс/суффикс отбрасываются)
    i = 0
    while i < min(len(thumb), len(orig)) and thumb[i] == orig[i]:
        i += 1
    j = 0
    while j < min(len(thumb), len(orig)) - i and thumb[-1 - j] == orig[-1 - j]:
        j += 1
    a, b = thumb[i:len(thumb) - j], orig[i:len(orig) - j]
    if not a and not b:
        return None
    if not a:
        return {"find": thumb[max(0, i - 6):i], "repl": orig[max(0, i - 6):i + len(b)], "regex": False}
    return {"find": a, "repl": b, "regex": False}


def best_image(n, page, root):
    # для <img>: ссылка на оригинал → набор вариантов (первый — лучший), запасной — сама миниатюра
    cand = []
    par = n.parent
    while par is not None and par.tag != "a" and par.tag not in ("body", "root"):
        par = par.parent
    if par is not None and par.tag == "a" and ext_of(par.attrs.get("href", "").split("?")[0]) in IEXT:
        cand.append(par.attrs["href"])
    for k in ("data-srcset", "srcset"):
        if n.attrs.get(k):
            cand.append(srcset_best(n.attrs[k]))
    base = ""
    for k in IMG_ATTRS:
        if n.attrs.get(k) and not n.attrs[k].startswith("data:"):
            base = n.attrs[k]
            cand.append(base)
    host = urlparse(page).hostname or ""
    head = [urljoin(page, x) for x in cand if x and x != base][:2]
    out = list(head)
    if ST.g("original_quality"):
        for u in ([urljoin(page, x) for x in cand if x]):
            r = apply_rules(u, host)
            if r:
                out.append(r)
        if base:
            out += [urljoin(page, x) for x in derive_originals(urljoin(page, base))]
    out += [urljoin(page, x) for x in cand if x]
    return [x for x in dict.fromkeys(out) if x.startswith("http")]


def page_inventory(url, html_text=None):
    # всё, что есть на странице: фото (с вариантами оригинала), видео, аудио, файлы, текст, ссылки
    t = html_text if html_text is not None else get_text(url, headers={"Referer": url})
    root = absolutize(parse_html(t), url)
    host = urlparse(url).hostname or ""
    sub = "site/" + sanitize(host)
    items, seen = [], set()

    def add(it):
        if it["url"] not in seen:
            seen.add(it["url"])
            items.append(it)
    for n in walk(root):
        if n.tag == "img":
            c = best_image(n, url, root)
            if c:
                alts = [{"src": "direct", "url": x, "type": "photo", "kind": "photo", "title": "alt", "referer": url, "sub": sub} for x in c[1:4]]
                add(mkitem("photo", c[0], n.attrs.get("alt") or os.path.basename(urlparse(c[0]).path) or c[0], url, None, sub, alts=alts or None))
        elif n.tag in ("video", "audio", "source") and n.attrs.get("src"):
            e = ext_of(n.attrs["src"].split("?")[0])
            add(mkitem(type_of_ext(e) or ("audio" if n.tag == "audio" else "video"), n.attrs["src"], os.path.basename(urlparse(n.attrs["src"]).path), url, None, sub))
        elif n.tag == "a" and n.attrs.get("href"):
            e = ext_of(n.attrs["href"].split("?")[0])
            if e in FILE_EXT:
                add(mkitem("file", n.attrs["href"], os.path.basename(urlparse(n.attrs["href"]).path), url, None, sub))
            elif e in VEXT | AEXT:
                add(mkitem(type_of_ext(e), n.attrs["href"], os.path.basename(urlparse(n.attrs["href"]).path), url, None, sub))
            elif e in IEXT:
                add(mkitem("photo", n.attrs["href"], os.path.basename(urlparse(n.attrs["href"]).path), url, None, sub))
    for m in scrape_media(url, t) + deep_media(t, sub, url, "site"):
        u = m["url"]
        if u not in seen and not any(u.split("?")[0] == s.split("?")[0] for s in seen):
            add(mkitem(m["type"], u, m.get("title") or u, url, m.get("name"), sub))
    main_n = next((n for n in walk(root) if n.tag in ("article", "main")), None) or next((n for n in walk(root) if n.tag == "body"), root)
    for n in list(walk(main_n)):
        if n.tag in ("script", "style", "nav", "header", "footer", "aside", "form", "noscript", "svg") and n.parent is not None:
            n.parent.children = [c for c in n.parent.children if c is not n]
    title = (next((node_text(n).strip() for n in walk(root) if n.tag == "title"), "") or host)[:80]
    text = make_text_item(inner_html(main_n), title, sub + "/text", "page_%s" % hashlib.sha1(url.encode()).hexdigest()[:8], url, url) if node_text(main_n).strip() else None
    links = []
    for n in walk(root):
        if n.tag == "a" and n.attrs.get("href", "").startswith("http") and (urlparse(n.attrs["href"]).hostname or "").replace("www.", "") == host.replace("www.", ""):
            links.append(n.attrs["href"].split("#")[0])
    return {"items": items, "text": text, "links": list(dict.fromkeys(links)), "title": title}


def print_inventory(inv):
    cnt = collections.Counter(i["type"] for i in inv["items"])
    print("[+] %s: %s" % (L("Найдено", "Found"), ", ".join("%s %d" % kv for kv in cnt.items()) or "—") + (", " + L("текст", "text") if inv["text"] else ""))


def crawl_site(url, max_pages, depth):
    # обход сайта в пределах домена: очередь ссылок, пауза между страницами, общий список медиа
    host = (urlparse(url).hostname or "").replace("www.", "")
    todo, seen, items, texts, bar = [(url, 0)], {url}, [], [], Bar(max_pages, L("Страницы", "Pages"))
    got = 0
    while todo and got < max_pages:
        u, d = todo.pop(0)
        try:
            inv = page_inventory(u)
        except KeyboardInterrupt:
            raise
        except Exception as e:
            note_error(u, e)
            continue
        got += 1
        bar.update(got)
        items += inv["items"]
        if inv["text"]:
            texts.append(inv["text"])
        if d < depth:
            for l_ in inv["links"]:
                if l_ not in seen and ext_of(l_.split("?")[0]) not in FILE_EXT | IEXT | VEXT | AEXT and not re.search(r"logout|signout|login|\.(css|js)$", l_, re.I):
                    seen.add(l_)
                    todo.append((l_, d + 1))
        time.sleep(random.uniform(0.4, 1.2))
    bar.close()
    uniq_items, s = [], set()
    for it in items:
        if it["url"] not in s:
            s.add(it["url"])
            uniq_items.append(it)
    return uniq_items, texts


@resilient
def site_menu():
    while True:
        k = menu(L("Содержимое сайта", "Site contents"), [
            ("1", L("Найти всё на странице (фото, видео, аудио, файлы, текст)", "Find everything on a page (photos, video, audio, files, text)"), L("покажет список — выберете, что скачать", "shows a list — pick what to download")),
            ("2", L("Скачать весь сайт (обход ссылок)", "Download the whole site (crawl)"), L("в пределах домена, лимит страниц", "within the domain, page limit")),
            ("3", L("Оригиналы фото: научить правилу (пример миниатюра → оригинал)", "Original photos: teach a rule (thumbnail → original example)"), L("если авто-режим не угадал", "if auto mode misses")),
            ("4", L("Правила оригиналов (список / удалить)", "Original rules (list / delete)"), ""), ("5", L("Какой движок обработает ссылку", "Which engine handles a link"), "yt-dlp / gallery-dl / свой")],
            sub=L("Миниатюры автоматически заменяются на оригиналы (ссылка вокруг, srcset, data-*, шаблоны URL)", "Thumbnails are replaced with originals automatically (wrapping link, srcset, data-*, URL patterns)"))
        if k == "q":
            return
        if k in ("1", "2"):
            u = ask(L("Адрес страницы/сайта", "Page/site URL"), "", quit_ok=False)
            if not u:
                continue
            if not u.startswith("http"):
                u = "https://" + u
            if not ensure_internet(L("загрузка страницы", "page download")):
                continue
            try:
                if k == "1":
                    with Spin(L("Разбираю страницу", "Parsing the page"), quiet=True):
                        inv = page_inventory(u)
                    items = inv["items"] + ([inv["text"]] if inv["text"] else [])
                else:
                    n = ask(L("Максимум страниц", "Max pages"), str(ST.g("crawl_pages")), quit_ok=False)
                    dpt = ask(L("Глубина ссылок (0 — только эта страница)", "Link depth (0 = this page only)"), str(ST.g("crawl_depth")), quit_ok=False)
                    its, txts = crawl_site(u, int(n) if n.isdigit() else 30, int(dpt) if dpt.isdigit() else 2)
                    items = its + txts
                    inv = {"items": its, "text": None}
                print_inventory(inv)
            except KeyboardInterrupt:
                raise Interrupt()
            except Exception as e:
                note_error(u, e)
                print("[!] %s" % trunc(str(e), term_w() - 6))
                if "403" in str(e) or "challenge" in str(e):
                    print(dim("    " + L("Защита сайта: попробуйте Сеть → Мастер cookies (cf_clearance) или curl_cffi", "Site protection: try Network → Cookies wizard (cf_clearance) or curl_cffi")))
                continue
            if not items:
                print("[!] " + L("Ничего не найдено. Если фото — миниатюры без ссылок, обучите правилу (пункт 3).", "Nothing found. For thumbnails without links, teach a rule (item 3)."))
                continue
            run_items(items)
        elif k == "3":
            th = ask(L("Ссылка на миниатюру", "Thumbnail URL"), "", quit_ok=False)
            og = ask(L("Ссылка на оригинал этого же фото", "Original URL of the same photo"), "", quit_ok=False)
            r = learn_rule(th, og) if th and og else None
            if not r:
                print("[!] " + L("Не удалось вывести правило. Введите вручную.", "Could not infer a rule. Enter manually."))
                f_ = ask(L("Что заменить (текст)", "What to replace (text)"), "", quit_ok=False)
                t_ = ask(L("На что", "With"), "", quit_ok=False)
                r = {"find": f_, "repl": t_, "regex": confirm(L("Это regex?", "Is it a regex?"), False)} if f_ else None
            if r:
                host = urlparse(th or og).hostname or ""
                d = jload(ORIG_RULES, {})
                d.setdefault(host, []).append(r)
                jsave(ORIG_RULES, d)
                print("[+] %s %s: «%s» → «%s»" % (L("Правило для", "Rule for"), host, r["find"], r["repl"]))
        elif k == "4":
            d = jload(ORIG_RULES, {})
            rows = [(h, i, r) for h, rs in d.items() for i, r in enumerate(rs)]
            for n_, (h, i, r) in enumerate(rows, 1):
                print("  %s %s  «%s» → «%s»" % (c("%2d" % n_, accent(), True), h, r["find"], r["repl"]))
            if rows and confirm(L("Удалить правило?", "Delete a rule?"), False):
                sel = ask_multi(L("Номера", "Numbers"), len(rows))
                for n_ in sorted(sel or [], reverse=True):
                    h, i, _ = rows[n_ - 1]
                    d[h].pop(i)
                jsave(ORIG_RULES, d)
        elif k == "5":
            u = ask(L("Ссылка", "Link"), "", quit_ok=False)
            print(engine_for(u))
        pause()


def engine_for(url):
    # какой движок возьмётся за ссылку: свой разбор / yt-dlp (extractor) / gallery-dl
    res = []
    sk = social_kind(url)
    if soc_dispatch(sk) or creator_kind(url) or music_kind(url) or urlparse(url).hostname in GAL_HOSTS:
        res.append(L("свой разбор (%s)" % (sk or creator_kind(url) or music_kind(url) or "api"), "built-in resolver (%s)" % (sk or creator_kind(url) or music_kind(url) or "api")))
    try:
        import yt_dlp
        from yt_dlp.extractor import gen_extractor_classes
        for ie in gen_extractor_classes():
            if ie.ie_key() != "Generic" and ie.suitable(url):
                res.append("yt-dlp: %s" % ie.ie_key())
                break
    except Exception:
        pass
    try:
        from gallery_dl import extractor as gx
        ex = gx.find(url)
        if ex:
            res.append("gallery-dl: %s" % type(ex).__name__)
    except Exception:
        pass
    return ", ".join(res) or L("универсальный разбор страницы (фото/видео/текст)", "generic page parsing (photos/video/text)")


# ==========================================================================
#  API STUDIO — универсальный инструмент работы с API
# ==========================================================================
API_PRESETS = CONF / "api_presets.json"


def api_request(method, url, headers, body=None, timeout=30):
    # любой HTTP-метод; возвращает (код, заголовки, тело) и при ошибках HTTP (4xx/5xx) — тоже тело
    hd = dict(headers)
    data = body
    host = urlparse(url).hostname or ""
    if "Cookie" not in {k.title(): v for k, v in hd.items()} and cookie_header(host):
        hd["Cookie"] = cookie_header(host)
    if ST.g("impersonate") and cffi_usable():
        try:
            from curl_cffi import requests as cr
            kw = {"headers": hd, "timeout": timeout, "impersonate": random.choice(CF_BROWSERS)}
            if proxy_url():
                kw["proxies"] = {"http": proxy_url(), "https": proxy_url()}
            r = cr.request(method, url, data=data, **kw)
            return r.status_code, dict(r.headers), r.content
        except Exception as e:
            dlog("api cffi failed: %s" % e, "WARN")
    req = urllib.request.Request(url, headers=hd, data=data, method=method)
    try:
        with opener(host not in INSECURE).open(req, timeout=timeout) as r:
            return r.status, dict(r.headers), r.read()
    except urllib.error.HTTPError as e:
        return e.code, dict(e.headers), e.read()


def json_urls(obj, out=None, path=""):
    # все строковые значения-ссылки в JSON с путями
    out = [] if out is None else out
    if isinstance(obj, dict):
        for k, v in obj.items():
            json_urls(v, out, path + "." + str(k))
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            json_urls(v, out, path + "[%d]" % i)
    elif isinstance(obj, str) and re.match(r"https?://", obj):
        out.append((path, obj))
    return out


@resilient
def api_menu():
    state = {"method": "GET", "url": "", "headers": {}, "body": None}
    while True:
        k = menu("API Studio", [
            ("1", L("Новый запрос (метод, URL, заголовки, тело)", "New request (method, URL, headers, body)"), ""), ("2", L("Пагинация: собрать все страницы и найти ссылки на медиа", "Pagination: fetch all pages and find media links"), ""),
            ("3", L("Сохранённые запросы (пресеты)", "Saved requests (presets)"), str(len(jload(API_PRESETS, {})))), ("4", L("Скачать ссылки из последнего ответа", "Download links from the last response"), "")],
            sub=L("Универсальный клиент: любой JSON-API → ссылки на фото/видео/аудио → загрузка", "Universal client: any JSON API → photo/video/audio links → download"))
        if k == "q":
            return
        if k == "1":
            state["method"] = ask(L("Метод", "Method"), state["method"], quit_ok=False, hint="GET/POST/PUT/PATCH/DELETE").upper()
            state["url"] = ask("URL", state["url"], quit_ok=False)
            print(dim(L("Заголовки: «Имя: значение», пустая строка — конец. Готовые: ua / cookie / referer / json / mobile", "Headers: 'Name: value', blank = end. Shortcuts: ua / cookie / referer / json / mobile")))
            hd = {}
            while True:
                x = ask(L("Заголовок", "Header"), "", quit_ok=False)
                if not x:
                    break
                if x == "ua":
                    hd["User-Agent"] = ua()
                elif x == "mobile":
                    hd["User-Agent"] = UA_IOS
                elif x == "cookie":
                    hd["Cookie"] = cookie_header(urlparse(state["url"]).hostname or "")
                elif x == "referer":
                    hd["Referer"] = "%s://%s/" % (urlparse(state["url"]).scheme, urlparse(state["url"]).netloc)
                elif x == "json":
                    hd["Content-Type"] = "application/json"
                    hd["Accept"] = "application/json"
                elif ":" in x:
                    a, b = x.split(":", 1)
                    hd[a.strip()] = b.strip()
            state["headers"] = hd
            body = None
            if state["method"] in ("POST", "PUT", "PATCH"):
                bt = ask(L("Тело", "Body"), "none", quit_ok=False, hint="none / json / form / raw")
                if bt == "json":
                    body = ask("JSON", "{}", quit_ok=False).encode()
                    hd.setdefault("Content-Type", "application/json")
                elif bt == "form":
                    body = ask("a=1&b=2", "", quit_ok=False).encode()
                    hd.setdefault("Content-Type", "application/x-www-form-urlencoded")
                elif bt == "raw":
                    body = ask("raw", "", quit_ok=False).encode()
            state["body"] = body
            try:
                with Spin(L("Отправляю запрос", "Sending request"), quiet=True):
                    code, hh, bd = api_request(state["method"], state["url"], hd, body)
            except Exception as e:
                note_error(state["url"], e)
                print("[!] %s" % e)
                continue
            state["last"] = bd
            print("[%s] HTTP %s  %s  %s" % ("+" if code < 400 else "!", code, fmt_size(len(bd)), dim(hh.get("Content-Type", hh.get("content-type", "")))))
            try:
                obj = json.loads(bd.decode("utf-8", "replace"))
                state["json"] = obj
                print(json.dumps(obj, ensure_ascii=False, indent=1)[:1800])
                urls = json_urls(obj)
                state["urls"] = urls
                print("[*] " + L("Ссылок в JSON: %d (пункт 4 — скачать)" % len(urls), "Links in JSON: %d (item 4 — download)" % len(urls)))
            except Exception:
                print(bd.decode("utf-8", "replace")[:1200])
            if confirm(L("Сохранить как пресет?", "Save as a preset?"), False):
                nm = ask(L("Имя пресета", "Preset name"), "", quit_ok=False)
                pr = jload(API_PRESETS, {})
                pr[nm] = {"method": state["method"], "url": state["url"], "headers": {k_: v for k_, v in hd.items() if k_.lower() not in ("cookie", "authorization")}, "body": (body or b"").decode("utf-8", "replace")}
                jsave(API_PRESETS, pr)
            if confirm(L("Сохранить ответ в файл?", "Save the response to a file?"), False):
                p = BASE / "reports" / ("api_%s.json" % now_stamp())
                p.write_bytes(bd)
                print("[+] " + str(p))
        elif k == "2":
            u = ask(L("URL со страницей (подставьте {page}, {offset} или {cursor})", "URL with a page ({page}, {offset} or {cursor})"), state["url"], quit_ok=False, hint="https://api.site/x?page={page}")
            start = int(ask(L("Начальное значение", "Start value"), "1", quit_ok=False) or 1)
            step = int(ask(L("Шаг", "Step"), "1", quit_ok=False) or 1)
            cur_path = ask(L("Путь курсора в ответе (для {cursor}, напр. .next)", "Cursor path in the response (for {cursor}, e.g. .next)"), "", quit_ok=False)
            allu, seen, val, cursor = [], set(), start, ""
            bar = Bar(None, L("Страницы API", "API pages"))
            for i in range(500):
                url_i = u.replace("{page}", str(val)).replace("{offset}", str(val)).replace("{cursor}", quote(str(cursor)))
                try:
                    code, hh, bd = api_request("GET", url_i, state["headers"])
                    obj = json.loads(bd.decode("utf-8", "replace"))
                except Exception as e:
                    print("[!] %s" % trunc(str(e), 60))
                    break
                new = [x for x in json_urls(obj) if x[1] not in seen]
                if not new or code >= 400:
                    break
                for x in new:
                    seen.add(x[1])
                allu += new
                bar.update(i + 1)
                if cur_path:
                    cur = obj
                    for part in [p_ for p_ in cur_path.split(".") if p_]:
                        cur = cur.get(part) if isinstance(cur, dict) else None
                    if not cur:
                        break
                    cursor = cur
                val += step
                time.sleep(random.uniform(0.3, 0.9))
            bar.close()
            state["urls"] = allu
            print("[+] " + L("Ссылок собрано: %d" % len(allu), "Links collected: %d" % len(allu)))
        elif k == "3":
            pr = jload(API_PRESETS, {})
            names = list(pr)
            nm = pick_one(L("Пресет", "Preset"), names) if names else None
            if nm:
                state.update(method=pr[nm]["method"], url=pr[nm]["url"], headers=pr[nm]["headers"], body=pr[nm]["body"].encode() or None)
                print("[+] " + L("Загружен. Пункт 1 — изменить и отправить.", "Loaded. Item 1 — edit and send."))
        elif k == "4":
            urls = state.get("urls") or []
            media = [(p_, u_) for p_, u_ in urls if ext_of(u_.split("?")[0]) in IEXT | VEXT | AEXT] or urls
            if not media:
                print("[!] " + L("Нет ссылок. Сначала выполните запрос.", "No links. Send a request first."))
                continue
            its = [mkitem(type_of_ext(ext_of(u_.split("?")[0])) or "photo", u_, p_ + " " + os.path.basename(urlparse(u_).path), state["headers"].get("Referer"), None, "api") for p_, u_ in media]
            run_items(its)
        pause()


# ==========================================================================
#  MITM-ЛОГИ (Shadowrocket Spy/Spylog): импорт ссылок на медиа и заголовков сессии
# ==========================================================================
@resilient
def mitm_menu():
    d = BASE / "logs"
    d.mkdir(parents=True, exist_ok=True)
    while True:
        k = menu(L("MITM-логи Shadowrocket", "Shadowrocket MITM logs"), [
            ("1", L("Импорт лога → найти медиа и скачать", "Import a log → find media and download"), L("положите лог в папку logs/", "put the log into logs/")),
            ("2", L("Взять заголовки сессии из лога (Cookie/User-Agent/Authorization)", "Take session headers from the log (Cookie/User-Agent/Authorization)"), L("для закрытых сайтов", "for protected sites")),
            ("3", L("Импорт из буфера iOS", "Import from the iOS clipboard"), "")], sub=str(d))
        if k == "q":
            return
        if k == "3":
            txt = read_clipboard()
            if not txt:
                print("[!] " + L("Буфер пуст/недоступен", "Clipboard is empty/unavailable"))
                continue
        else:
            fs = pick_files(d, None, False, L("Лог", "Log"))
            if not fs:
                continue
            txt = fs[0].read_text("utf-8", "replace")
        t = unesc(txt)
        if k in ("1", "3"):
            urls = list(dict.fromkeys(re.findall(r"https?://[^\s\"'<>\\|]+", t)))
            media = []
            for u in urls:
                u = u.rstrip(",.;)")
                e = ext_of(u.split("?")[0])
                if e in IEXT | VEXT | AEXT or re.search(r"\.m3u8(\?|$)|/videoplayback|googlevideo\.com|cdninstagram|fbcdn|tiktokcdn|twimg\.com", u):
                    media.append(mkitem(type_of_ext(e) or ("video" if "m3u8" in u or "video" in u else "photo"), u, os.path.basename(urlparse(u).path) or u[-30:], None, None, "mitm/" + sanitize(urlparse(u).hostname or "x")))
            hosts = collections.Counter(urlparse(u).hostname for u in urls)
            print("[*] %s: %d, %s: %d" % (L("Ссылок в логе", "URLs in the log"), len(urls), L("медиа", "media"), len(media)))
            print(dim(", ".join("%s×%d" % kv for kv in hosts.most_common(6))))
            if media:
                run_items(media)
            else:
                print("[!] " + L("Медиа-ссылок не нашёл. Проверьте, что в логе есть ответы с URL.", "No media URLs found. Check that the log has responses with URLs."))
        else:
            hv = {}
            for m in re.finditer(r"(?im)^[|\s>]*(cookie|authorization|user-agent|referer):\s*(.+)$", t):
                hv.setdefault(m.group(1).lower(), m.group(2).strip())
            hosts = [h for h, _ in collections.Counter(re.findall(r"https?://([\w.-]+)", t)).most_common(8)]
            print("[*] " + L("Найдено заголовков: %s" % ", ".join(hv) or "—", "Headers found: %s" % ", ".join(hv) or "—"))
            if hv.get("cookie") and hosts:
                h = pick_one(L("Для какого домена сохранить cookies", "Save cookies for which domain"), hosts)
                if h:
                    cookies_save(".".join(h.split(".")[-2:]), hv["cookie"])
                    if hv.get("user-agent"):
                        session_save(h, {}, hv["user-agent"])
                    print("[+] " + L("Сохранено", "Saved"))
        pause()


# ==========================================================================
#  TOR: мосты obfs4 / webtunnel (lyrebird), SOCKS5 127.0.0.1:9050
# ==========================================================================
TOR_DIR = CONF / "tor"
TOR_PROXY = "socks5h://127.0.0.1:9050"
_orig_proxy_url = proxy_url


def tor_running():
    try:
        socket.create_connection(("127.0.0.1", 9050), 0.5).close()
        return True
    except Exception:
        return False


def proxy_url():
    # прокси с учётом Tor (use_tor) — иначе прежняя логика
    if ST.g("use_tor") and "proxy" not in ST.ov and tor_running():
        return TOR_PROXY
    return _orig_proxy_url()


def tor_bridges():
    try:
        return [x.strip() for x in (TOR_DIR / "bridges.txt").read_text("utf-8").splitlines() if x.strip() and not x.startswith("#")]
    except Exception:
        return []


def tor_write_torrc():
    TOR_DIR.mkdir(parents=True, exist_ok=True)
    lb = shutil.which("lyrebird") or shutil.which("obfs4proxy") or "/usr/bin/lyrebird"
    br = tor_bridges()
    lines = ["DataDirectory %s" % (TOR_DIR / "data"), "SocksPort 127.0.0.1:9050", "ClientOnly 1", "Log notice file %s" % (TOR_DIR / "tor.log"), "AvoidDiskWrites 1"]
    if br:
        lines += ["UseBridges 1", "ClientTransportPlugin obfs4,webtunnel,meek_lite exec %s" % lb] + ["Bridge " + b for b in br]
    (TOR_DIR / "torrc").write_text("\n".join(lines) + "\n")
    os.chmod(str(TOR_DIR), 0o700)
    return TOR_DIR / "torrc"


MEEK_AZURE = "meek_lite 192.0.2.18:80 BE776A53492E1E044A26F17306E1BC46A55A1625 url=https://meek.azureedge.net/ front=ajax.aspnetcdn.com"


def bridge_alive(line, timeout=3):
    if line.startswith("meek_lite"):
        return True
    um = re.search(r"url=https?://([^/\s:]+)", line) if line.startswith("webtunnel") else None
    if um:
        try:
            socket.create_connection((um.group(1), 443), timeout).close()
            return True
        except Exception:
            return False
    m = re.search(r"(\[[0-9a-fA-F:]+\]|\d+\.\d+\.\d+\.\d+):(\d+)", line)
    if not m:
        return None
    try:
        socket.create_connection((m.group(1).strip("[]"), int(m.group(2))), timeout).close()
        return True
    except Exception:
        return False


def bridges_auto(n=5):
    # автоподбор: список из bridges_url → TCP-проверка → первые рабочие obfs4/webtunnel
    src = ST.g("bridges_url").split(",")
    lines = []
    for u in [x.strip() for x in src if x.strip()]:
        try:
            lines += [x.strip() for x in get_text(u).splitlines() if re.match(r"^(obfs4|webtunnel)\s", x.strip())]
        except Exception as e:
            print("[!] %s: %s" % (trunc(u, 40), trunc(str(e), 40)))
    random.shuffle(lines)
    good = []
    bar = Bar(min(len(lines), 60), L("Проверка мостов", "Checking bridges"))
    for i, ln_ in enumerate(lines[:60], 1):
        if bridge_alive(ln_, 2.5):
            good.append(ln_)
        bar.update(i)
        if len(good) >= n:
            break
    bar.close()
    return good


def tor_start():
    if tor_running():
        return True
    tor = shutil.which("tor")
    if not tor:
        print("[!] " + L("tor не установлен — Среда → Установить Tor", "tor is not installed — Environment → Install Tor"))
        return False
    rc = tor_write_torrc()
    log = TOR_DIR / "tor.log"
    if log.exists():
        log.unlink()
    p = subprocess.Popen([tor, "-f", str(rc)], stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
    (TOR_DIR / "tor.pid").write_text(str(p.pid))
    bar = Bar(100, "Tor bootstrap")
    t0, pct = time.time(), 0
    try:
        while time.time() - t0 < 120:
            time.sleep(1)
            try:
                m = re.findall(r"Bootstrapped (\d+)%", log.read_text("utf-8", "replace"))
                pct = int(m[-1]) if m else pct
            except Exception:
                pass
            bar.update(pct)
            if pct >= 100 and tor_running():
                break
            if p.poll() is not None:
                break
    except KeyboardInterrupt:
        bar.close(False)
        raise
    bar.close(pct >= 100)
    ok = tor_running()
    audit("tor-start", "ok" if ok else "fail")
    if not ok:
        print("[!] " + L("Tor не поднялся. Лог: ", "Tor did not start. Log: ") + str(log) + L(". Проверьте мосты или смените их.", ". Check or change bridges."))
    return ok


def tor_stop():
    try:
        os.kill(int((TOR_DIR / "tor.pid").read_text()), 15)
    except Exception:
        pass
    time.sleep(1)
    audit("tor-stop")


@resilient
def tor_menu():
    while True:
        br = tor_bridges()
        k = menu(L("Tor и мосты", "Tor & bridges"), [
            ("1", L("Запустить Tor", "Start Tor"), L("работает" if tor_running() else "остановлен", "running" if tor_running() else "stopped")), ("2", L("Остановить Tor", "Stop Tor"), ""),
            ("3", L("Использовать Tor для всех запросов", "Use Tor for all requests"), "on" if ST.g("use_tor") else "off"), ("4", L("Добавить мост (obfs4 / webtunnel)", "Add a bridge (obfs4 / webtunnel)"), str(len(br))),
            ("5", L("Автоподбор мостов из публичного списка", "Auto-pick bridges from a public list"), "bridges_url"), ("6", L("Проверить мосты и удалить нерабочие", "Test bridges and drop dead ones"), ""),
            ("7", L("Показать / удалить мосты", "Show / delete bridges"), ""), ("8", L("Проверить работу Tor", "Test Tor"), ""), ("9", L("Установить tor + lyrebird", "Install tor + lyrebird"), "apk"), ("10", L("Добавить встроенный мост meek-azure (Tor Browser)", "Add the built-in meek-azure bridge (Tor Browser)"), L("без IP-мостов", "no IP bridges"))],
            sub=L("Мосты можно получить у бота @GetBridgesBot или на bridges.torproject.org", "Get bridges from @GetBridgesBot or bridges.torproject.org"))
        if k == "q":
            return
        if k == "1":
            print(("[+] " if tor_start() else "[!] ") + L("Tor", "Tor"))
        elif k == "2":
            tor_stop()
        elif k == "3":
            ST.set("use_tor", not ST.g("use_tor"))
            if ST.g("use_tor") and not tor_running():
                print("[*] " + L("Tor не запущен — запустите (пункт 1); пока запросы идут напрямую/через обычный прокси", "Tor is not running — start it (item 1); requests go direct/through the normal proxy meanwhile"))
        elif k == "4":
            print(dim(L("Вставьте строки мостов (obfs4 … / webtunnel …), пустая строка — конец.", "Paste bridge lines (obfs4 … / webtunnel …), blank line = end.")))
            add = []
            while True:
                x = ask(L("Мост", "Bridge"), "", quit_ok=False)
                if not x:
                    break
                x = re.sub(r"^Bridge\s+", "", x)
                if re.match(r"^(obfs4|webtunnel|meek_lite|snowflake)\s", x):
                    add.append(x)
                else:
                    print("[!] " + L("Неверный формат", "Bad format"))
            if add:
                TOR_DIR.mkdir(parents=True, exist_ok=True)
                (TOR_DIR / "bridges.txt").write_text("\n".join(list(dict.fromkeys(br + add))) + "\n")
                print("[+] " + L("Добавлено: %d" % len(add), "Added: %d" % len(add)))
        elif k == "5":
            if not ensure_internet():
                continue
            good = bridges_auto()
            if good:
                TOR_DIR.mkdir(parents=True, exist_ok=True)
                (TOR_DIR / "bridges.txt").write_text("\n".join(good) + "\n")
                print("[+] " + L("Подобрано рабочих мостов: %d" % len(good), "Working bridges found: %d" % len(good)))
            else:
                print("[!] " + L("Рабочих мостов не нашлось. Вставьте свои (пункт 4).", "No working bridges. Paste your own (item 4)."))
        elif k == "6":
            alive = [b for b in track(br, L("Проверка", "Testing")) if bridge_alive(b)]
            (TOR_DIR / "bridges.txt").write_text("\n".join(alive) + ("\n" if alive else ""))
            print("[+] %d/%d" % (len(alive), len(br)))
        elif k == "7":
            for i, b in enumerate(br, 1):
                print("  %s %s" % (c("%2d" % i, accent(), True), trunc(b, term_w() - 6)))
            if br and confirm(L("Удалить выбранные?", "Delete selected?"), False):
                sel = ask_multi(L("Номера", "Numbers"), len(br))
                (TOR_DIR / "bridges.txt").write_text("\n".join(b for i, b in enumerate(br, 1) if i not in (sel or [])) + "\n")
        elif k == "8":
            ok, ms, err = test_proxy(TOR_PROXY)
            print(("[+] " if ok else "[!] ") + "SOCKS5 127.0.0.1:9050 " + ("%d ms" % ms if ok else err))
            if ok:
                try:
                    r = _orig_get_with_proxy("https://check.torproject.org/api/ip")
                    print("[+] " + r)
                except Exception as e:
                    print("[!] %s" % trunc(str(e), 70))
        elif k == "9":
            write_action("tor")
            raise SystemExit(0)
        elif k == "10":
            TOR_DIR.mkdir(parents=True, exist_ok=True)
            (TOR_DIR / "bridges.txt").write_text("\n".join(list(dict.fromkeys(br + [MEEK_AZURE]))) + "\n")
            print("[+] " + L("Добавлено. Запустите Tor (пункт 1).", "Added. Start Tor (item 1)."))
        pause()


def _orig_get_with_proxy(url):
    r = subprocess.run(["curl", "-sS", "--max-time", "40", "-x", TOR_PROXY, url], timeout=50)
    return r.stdout.decode("utf-8", "replace").strip() or r.stderr.decode("utf-8", "replace")[:120]


# ==========================================================================
#  ДОПОЛНЕНИЯ: события, уведомления, корзина, бэкапы, переименование по regex, видео-инструменты, health-check, плагины, тесты
# ==========================================================================
EVENTS = CONF / "events.jsonl"
TRASH = CONF / "trash"
BACKUPS = CONF / "backups"
PLUGINS = CONF / "plugins"
HOOKS = CONF / "hooks"
DRY = [False]


def emit(typ, data=None):
    # шина событий: строка JSON в events.jsonl + необязательный hook-скрипт hooks/<событие>.sh
    try:
        with open(str(EVENTS), "a", encoding="utf-8") as f:
            f.write(json.dumps({"ts": int(time.time()), "script": "mediaforge", "type": typ, "data": data or {}}, ensure_ascii=False) + "\n")
        if EVENTS.stat().st_size > 2 * 1048576:
            os.replace(str(EVENTS), str(EVENTS) + ".1")
        h = HOOKS / (typ + ".sh")
        if ST.g("enable_hooks") and h.exists():
            subprocess.run(["sh", str(h)], timeout=60, env=dict(os.environ, MF_EVENT=typ, MF_DATA=json.dumps(data or {})))
    except Exception:
        pass


def notify(text):
    # уведомление в Telegram (только HTTPS; токен из настроек)
    if not (ST.g("notify_telegram") and ST.g("telegram_bot_token") and ST.g("telegram_chat_id")):
        return
    try:
        http_get("https://api.telegram.org/bot%s/sendMessage" % ST.g("telegram_bot_token"), post={"chat_id": ST.g("telegram_chat_id"), "text": text[:3500]}, retries=1, timeout=15)
    except Exception as e:
        dlog("notify failed: %s" % redact(str(e)), "WARN")


# ---------- корзина (undo для удаления) ----------
_orig_rm_tree = rm_tree


def rm_tree(p):
    # удаление через корзину (trash_ttl_days дней), если включено
    if ST.g("trash") and os.path.exists(str(p)):
        try:
            TRASH.mkdir(parents=True, exist_ok=True)
            dst = TRASH / ("%d__%s" % (int(time.time()), sanitize(os.path.basename(str(p)))))
            (TRASH / (dst.name + ".path")).write_text(str(p))
            os.replace(str(p), str(dst))
            audit("trash", str(p))
            return True
        except OSError:
            pass
    return _orig_rm_tree(p)


def trash_purge():
    ttl = ST.g("trash_ttl_days") * 86400
    for f in TRASH.glob("*") if TRASH.exists() else []:
        try:
            if time.time() - f.stat().st_mtime > ttl:
                (shutil.rmtree if f.is_dir() else os.unlink)(str(f))
        except OSError:
            pass


def trash_menu():
    items = sorted([f for f in TRASH.glob("*") if not f.name.endswith(".path")], key=lambda p: -p.stat().st_mtime)[:50] if TRASH.exists() else []
    if not items:
        print("[*] " + L("Корзина пуста", "Trash is empty"))
        return
    for i, f in enumerate(items, 1):
        print("  %s %s %s" % (c("%2d" % i, accent(), True), trunc(f.name.split("__", 1)[-1], term_w() - 22), dim(time.strftime("%m-%d %H:%M", time.localtime(f.stat().st_mtime)))))
    sel = ask_multi(L("Восстановить", "Restore"), len(items))
    for i in sel or []:
        f = items[i - 1]
        try:
            orig = Path((TRASH / (f.name + ".path")).read_text())
            orig.parent.mkdir(parents=True, exist_ok=True)
            os.replace(str(f), str(uniq(orig)))
            (TRASH / (f.name + ".path")).unlink()
            print("[+] " + str(orig))
        except Exception as e:
            print("[!] %s" % e)


# ---------- бэкап памяти ----------
def auto_backup():
    # раз в день: settings/history/profiles/links → backups/ГГГГ-ММ-ДД (без cookies и ключей), хранится 7 дней
    if not ST.g("auto_backup"):
        return
    d = BACKUPS / time.strftime("%Y-%m-%d")
    if d.exists():
        return
    try:
        d.mkdir(parents=True, exist_ok=True)
        for nm in ("settings.json", "history.json", "profiles.json", "links.json", "schedule.json", "imgrules.json", "api_presets.json"):
            if (CONF / nm).exists():
                shutil.copy2(str(CONF / nm), str(d / nm))
        for old in sorted(BACKUPS.iterdir())[:-7]:
            shutil.rmtree(str(old), ignore_errors=True)
    except OSError:
        pass


def restore_backup():
    ds = sorted(BACKUPS.iterdir())[-7:] if BACKUPS.exists() else []
    if not ds:
        print("[*] " + L("Бэкапов нет", "No backups"))
        return
    d = pick_one(L("Дата бэкапа", "Backup date"), [x.name for x in ds])
    if d and confirm(L("Восстановить настройки и списки из %s?" % d, "Restore settings and lists from %s?" % d), False):
        for f in (BACKUPS / d).glob("*.json"):
            shutil.copy2(str(f), str(CONF / f.name))
        ST.__init__()
        audit("restore-backup", d)
        print("[+] OK")


# ---------- массовое переименование по regex ----------
def regex_rename():
    fs = pick_media()
    if not fs:
        return
    pat = ask(L("Regex поиска", "Search regex"), r"(.+)_final\.mp4", quit_ok=False)
    rep = ask(L("Шаблон замены", "Replacement"), r"\1.mp4", quit_ok=False)
    try:
        rx = re.compile(pat)
    except re.error as e:
        print("[!] %s" % e)
        return
    plan = [(f, f.with_name(rx.sub(rep, f.name))) for f in fs if rx.search(f.name)]
    plan = [(a, b) for a, b in plan if a != b]
    if not plan:
        print("[!] " + L("Совпадений нет", "No matches"))
        return
    for a, b in plan[:5]:
        print("  %s → %s" % (a.name, c(b.name, OK_C)))
    if len(plan) > 5:
        print(dim("  … +%d" % (len(plan) - 5)))
    if ask(L("1 — применить, 2 — показать все (dry-run), Enter — отмена", "1 apply, 2 show all (dry-run), Enter cancel"), "", quit_ok=False) == "2":
        for a, b in plan:
            print("  %s → %s" % (a.name, b.name))
        if not confirm(L("Применить?", "Apply?"), False):
            return
    elif True:
        pass
    n = 0
    for a, b in plan:
        if not b.exists():
            a.rename(b)
            audit("rename", "%s -> %s" % (a.name, b.name))
            n += 1
    print("[+] %d/%d" % (n, len(plan)))


# ---------- видео-инструменты на ffmpeg ----------
def video_tool(kind):
    fs = pick_media()
    if not fs:
        return
    UNATT[0] = True
    try:
        for f in fs:
            d = probe_duration(f)
            if kind == "scenes":
                th = ask(L("Порог смены сцены (0.2–0.6)", "Scene threshold (0.2–0.6)"), "0.4", quit_ok=False)
                out = f.with_name(f.stem + "_scene%03d.mp4")
                ff_run(["-i", f, "-vf", "select='gt(scene,%s)',setpts=N/FRAME_RATE/TB" % th, "-vsync", "vfr", "-an", "-f", "image2", str(f.with_name(f.stem + "_scene%03d.jpg"))], "scenes", d)
                print("[+] " + L("Кадры смены сцен сохранены рядом (_sceneNNN.jpg). Для нарезки видео используйте «Нарезать на части».", "Scene frames saved next to the file (_sceneNNN.jpg). To cut video use 'Split into segments'."))
            elif kind == "autocrop":
                r = subprocess.run(["ffmpeg", "-hide_banner", "-i", str(f), "-t", "10", "-vf", "cropdetect=24:16:0", "-f", "null", "-"], timeout=300)
                m = re.findall(r"crop=(\d+:\d+:\d+:\d+)", r.stderr.decode("utf-8", "replace"))
                if not m:
                    print("[!] " + L("Чёрных полос не найдено", "No black bars found"))
                    continue
                ff_run(["-i", f, "-vf", "crop=" + m[-1], "-c:a", "copy", uniq(f.with_name(f.stem + "_crop.mp4"))], "autocrop", d)
            elif kind == "denoise":
                ff_run(["-i", f, "-af", "anlmdn=s=7:p=0.002:m=15,highpass=f=80", "-c:v", "copy", uniq(f.with_name(f.stem + "_denoise" + f.suffix))], "denoise", d)
            elif kind == "stabilize":
                trf = BASE / "tmp" / "vidstab.trf"
                if ff_run(["-i", f, "-vf", "vidstabdetect=shakiness=5:result=%s" % trf, "-f", "null", "-"], "stab 1/2", d) != 0:
                    print("[!] " + L("В этой сборке ffmpeg нет vidstab — используем deshake", "This ffmpeg has no vidstab — using deshake"))
                    ff_run(["-i", f, "-vf", "deshake", "-c:a", "copy", uniq(f.with_name(f.stem + "_stab.mp4"))], "deshake", d)
                else:
                    ff_run(["-i", f, "-vf", "vidstabtransform=smoothing=20:input=%s,unsharp=5:5:0.8" % trf, "-c:a", "copy", uniq(f.with_name(f.stem + "_stab.mp4"))], "stab 2/2", d)
    finally:
        UNATT[0] = False


# ---------- проверка файла, contact sheet ----------
def verify_media(p):
    # ffprobe: у валидного медиафайла есть длительность > 0
    if p.suffix.lower() not in VEXT | AEXT or not shutil.which("ffprobe"):
        return True
    d = probe_duration(p)
    return bool(d and d > 0)


_orig_postprocess = postprocess


def postprocess(res, job):
    # исходная постобработка + проверка целостности + contact sheet 3×3 + событие
    new, note = _orig_postprocess(res, job)
    try:
        p = Path(str(new).split(" (")[0])
        if p.is_file():
            if ST.g("verify_after_download") and not verify_media(p):
                emit("download_corrupt", {"path": str(p)})
                print("[!] " + L("Файл повреждён (нет длительности): %s" % p.name, "Damaged file (no duration): %s" % p.name))
                try:
                    p.unlink()
                except OSError:
                    pass
                return "", "corrupt"
            if ST.g("contact_sheet") and (job.get("type") == "video") and shutil.which("ffprobe") and have_ffmpeg():
                dur = probe_duration(p) or 0
                if dur > 5:
                    busy(L("Contact sheet 3×3", "Contact sheet 3×3"), lambda: ff_run(["-i", p, "-vf", "fps=1/%d,scale=200:-1,tile=3x3" % max(1, int(dur / 9)), "-frames:v", "1", p.with_name(p.stem + "_contact.jpg")], "contact", None))
            emit("download_complete", {"path": str(p), "size": p.stat().st_size, "url": job.get("url")})
    except Exception as e:
        dlog("postprocess ext failed: %s" % e, "WARN")
    return new, note


# ---------- health-check, тесты, benchmark ----------
def health_check():
    # быстрая проверка при старте (≈5 с): компактная таблица, при проблемах — подсказка
    rows = []
    t0 = time.time()
    rows.append(["python", sys.version.split()[0], True])
    for b in ("ffmpeg", "yt_dlp", "gallery_dl"):
        ok = bool(shutil.which(b)) if b == "ffmpeg" else bool(__import__("importlib").util.find_spec(b))
        rows.append([b, "OK" if ok else "—", ok])
    rows.append([L("место", "space"), "%d MB" % free_mb(), free_mb() > 100])
    ok, det = functional_ping(2, 1)
    rows.append([L("интернет", "internet"), "%d/%d" % (sum(1 for _, o, _ in det if o), len(det)), ok])
    if proxy_url():
        ok2, ms, err = test_proxy(proxy_url(), 2)
        rows.append([L("прокси", "proxy"), "%d ms" % ms if ok2 else err, ok2])
    bad = [r for r in rows if not r[2]]
    print(dim(" · ".join("%s %s" % (c("✓", OK_C) if r[2] else c("✗", ERR_C), "%s %s" % (r[0], r[1])) for r in rows)))
    if bad:
        print("[!] " + L("Есть проблемы: Среда → Отладка → Диагностика, Файлы → Починить.", "Problems found: Environment → Debug → Diagnostics, Files → Repair."))
    if free_mb() < 200:
        print("[!] " + L("Мало места (%d МБ). Файлы → очистка tmp/корзины." % free_mb(), "Low disk space (%d MB). Files → clean tmp/trash." % free_mb()))
    return not bad


def self_test():
    # --test: быстрые проверки ядра
    res = []

    def t(name, fn):
        t0 = time.time()
        try:
            ok = bool(fn())
        except Exception as e:
            ok, name = False, "%s (%s)" % (name, str(e)[:40])
        res.append((name, ok, int((time.time() - t0) * 1000)))
    t("json", lambda: json.loads('{"a":1}')["a"] == 1)
    t("dns", lambda: patched_gai("one.one.one.one", 443))
    t("ping", lambda: functional_ping(3, 1)[0])
    t("http 1.1.1.1", lambda: len(http_get("https://1.1.1.1/", retries=0, timeout=10)) > 0)
    t("download 1MB", lambda: len(http_get("https://speed.cloudflare.com/__down?bytes=1000000", retries=0, timeout=30)) >= 900000)
    t("ffmpeg", lambda: subprocess.run(["ffmpeg", "-version"], timeout=20).returncode == 0)
    t("html→md", lambda: "**x**" in to_md(parse_html("<b>x</b>")))
    t("regex original", lambda: derive_originals("https://a/b-300x200.jpg")[0] == "https://a/b.jpg")
    t("audit chain", lambda: audit_verify()[0])
    for n, ok, ms in res:
        print("  %s %-34s %d ms" % (c("✓", OK_C) if ok else c("✗", ERR_C), n, ms))
    print("[%s] %d/%d passed" % ("+" if all(r[1] for r in res) else "!", sum(1 for r in res if r[1]), len(res)))
    return all(r[1] for r in res)


def benchmark():
    # --benchmark: DNS, ping, загрузка, разбор; результат в benchmark.json
    out = {}
    t = time.time()
    try:
        DNS_CACHE.clear()
        patched_gai("www.google.com", 443)
        out["dns_ms"] = int((time.time() - t) * 1000)
    except Exception:
        out["dns_ms"] = None
    ok, det = functional_ping(3, 1)
    out["ping_ms"] = min([ms for _, o, ms in det if o] or [None]) if ok else None
    t = time.time()
    try:
        n = len(http_get("https://speed.cloudflare.com/__down?bytes=5000000", retries=0, timeout=40))
        out["download_mbit"] = round(n * 8 / 1e6 / max(0.01, time.time() - t), 2)
    except Exception:
        out["download_mbit"] = None
    t = time.time()
    for _ in range(50):
        to_md(parse_html("<div>" + "<p><b>x</b> y <a href='/a'>z</a></p>" * 200 + "</div>"))
    out["parse_ms"] = int((time.time() - t) * 1000)
    jsave(CONF / "benchmark.json", out)
    table([[k, str(v)] for k, v in out.items()], ["metric", "value"])
    slow = max((k for k in ("dns_ms", "ping_ms", "parse_ms") if out.get(k)), key=lambda k: out[k], default=None)
    if out.get("download_mbit") is not None and out["download_mbit"] < 3:
        print("[!] " + L("Узкое место: скорость канала", "Bottleneck: link speed"))
    elif slow:
        print("[*] " + L("Самый медленный этап: %s" % slow, "Slowest stage: %s" % slow))


# ---------- плагины ----------
def load_plugins():
    # ~/MediaForge/.config/plugins/*.py с функцией register() → [(название, описание, callback)]
    out = []
    if not ST.g("enable_plugins") or not PLUGINS.exists():
        return out
    for f in sorted(PLUGINS.glob("*.py")):
        try:
            ns = {"__name__": "mf_plugin_" + f.stem, "ST": ST, "L": L, "print": print, "ask": ask, "confirm": confirm, "http_get": http_get, "BASE": BASE}
            exec(compile(f.read_text("utf-8"), str(f), "exec"), ns)
            out += list(ns["register"]())
        except Exception as e:
            dlog("plugin %s failed: %s" % (f.name, e), "WARN")
    return out


def signal_setup():
    # корректное завершение: SIGTERM → как Ctrl+C (очередь сохраняется, временные файлы чистятся)
    import signal

    def h(sig, frm):
        raise KeyboardInterrupt()
    try:
        signal.signal(signal.SIGTERM, h)
    except Exception:
        pass


# ==========================================================================
#  ЗАПУСК
# ==========================================================================
def main():
    ensure_dirs()
    fix_tty()
    signal_setup()
    try:
        import faulthandler
        faulthandler.enable(open(str(CONF / "fault.log"), "a"))
    except Exception:
        pass
    trash_purge()
    auto_backup()
    clear_screen()
    rocket()
    banner()
    if ST.g("health_start") and ST.g("ping_enabled"):
        with Spin(L("Проверка окружения", "Environment check"), quiet=True):
            pass
        health_check()
        LAST_PING["ts"], LAST_PING["ok"] = time.time(), True
    if ST.g("mitm_warn_on_start") and ST.g("ping_enabled"):
        check_mitm_state()
    if not ST.d.get("_tour") and sys.stdin.isatty():
        try:
            tour()
        except Exception:
            pass
    plugins = load_plugins()
    emit("startup", {"build": os.environ.get("MF_BUILD", "")})
    while True:
        nl = sum(1 for x in links_load() if x.get("status") != "done")
        items = [("--", L("Загрузка", "Download"), ""), ("1", L("Умная загрузка (Media Vault)", "Smart download (Media Vault)"), L("авто: видео/аудио/фото/текст", "auto: video/audio/photo/text")),
                 ("2", L("Видео (Video Vault)", "Video (Video Vault)"), ""), ("3", L("Аудио (Audio Vault)", "Audio (Audio Vault)"), ""), ("4", L("Фото / галереи (Photo Vault)", "Photos / galleries (Photo Vault)"), ""),
                 ("5", L("Музыка и стриминги", "Music & streaming"), "Spotify, SoundCloud, YT Music, Яндекс, VK…"), ("6", L("Соцсети (Social Vault)", "Social (Social Vault)"), L("аватарки, истории, Telegram, Instagram…", "avatars, stories, Telegram, Instagram…")),
                 ("7", "Creator Platforms", "Boosty, Patreon, Fanbox, Fantia…"), ("8", L("Содержимое сайта / весь сайт", "Site contents / whole site"), L("фото в оригинале, видео, файлы, текст", "originals, video, files, text")),
                 ("9", L("Список ссылок", "Links list") + (" (%d)" % nl if nl else ""), L("добавить сейчас — скачать потом", "add now — download later")), ("10", L("Очередь и таймер", "Queue & timer"), ""),
                 ("11", L("Поиск (Media Search)", "Search (Media Search)"), "YouTube, SoundCloud, RuTube"),
                 ("--", L("Обработка", "Processing"), ""), ("12", L("Конвертер и инструменты (Transcode Studio)", "Converter & tools (Transcode Studio)"), ""), ("13", L("Коллаж / сшивание фото", "Photo collage / stitching"), ""),
                 ("14", L("Правка фото и OCR", "Photo editing & OCR"), ""), ("15", L("Метаданные и приватность (Metadata Lab)", "Metadata & privacy (Metadata Lab)"), ""), ("16", L("Кружки Telegram", "Telegram circles"), L("создать и править", "make and edit")),
                 ("--", L("Инструменты", "Tools"), ""), ("17", "API Studio", L("универсальный клиент API", "universal API client")), ("18", L("MITM-логи Shadowrocket", "Shadowrocket MITM logs"), L("импорт медиа и сессий", "import media and sessions")),
                 ("19", L("Tor и мосты", "Tor & bridges"), "obfs4 / webtunnel"),
                 ("--", L("Система", "System"), ""), ("20", L("Файлы и починка", "Files & repair"), L("🛠 лечит битые папки", "🛠 heals broken folders")), ("21", L("История и статистика", "History & statistics"), ""),
                 ("22", L("Планировщик", "Scheduler"), ""), ("23", L("Сеть, прокси и cookies", "Network, proxy & cookies"), L("LAN, MITM, VPN, cookies", "LAN, MITM, VPN, cookies")),
                 ("24", L("Настройки и профили", "Settings & profiles"), L("дизайн, подсказки, качество", "design, hints, quality")), ("25", L("Среда / отладка / помощь", "Environment / debug / help"), "")]
        for i, (nm, ds, cb) in enumerate(plugins, 1):
            if i == 1:
                items.append(("--", L("Плагины", "Plugins"), ""))
            items.append(("p%d" % i, nm, ds))
        clear_screen()
        print(status_line())
        k = menu(L("Главное меню", "Main menu"), items, back=L("Выход", "Quit"), top=True, hotkeys=True)
        if k == "q":
            emit("shutdown")
            print("[+] " + L("До встречи!", "See you!"))
            return
        if k == "__refresh":
            continue
        if k.startswith("p") and k[1:].isdigit() and int(k[1:]) <= len(plugins):
            guarded(plugins[int(k[1:]) - 1][2])
            continue
        direct = {"5": music_menu, "6": social_menu, "7": creators_menu, "8": site_menu, "9": links_menu, "10": queue_menu, "17": api_menu, "18": mitm_menu, "19": tor_menu,
                  "20": files_menu, "22": schedule_menu, "23": net_menu, "24": settings_menu, "25": env_menu, "16": circles_menu}
        if k in direct:
            try:
                direct[k]()
            except (Quit, KeyboardInterrupt):
                pass
            continue
        if k == "21":
            guarded(lambda: (history_menu(), stats_menu()))
            continue
        fn = {"1": lambda: download_menu("auto"), "2": lambda: download_menu("video"), "3": lambda: download_menu("audio"), "4": lambda: download_menu("photo"), "11": search_menu,
              "12": tools_menu, "13": collage_menu, "14": photo_menu, "15": meta_menu}.get(k)
        if fn:
            guarded(fn)


def selftest():
    # без subprocess и без YoutubeDL() (SIGSYS на iSH): только импорты и сокеты
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
    for mod in ("yt_dlp", "gallery_dl", "curl_cffi", "telethon"):
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
    if "--dry-run" in sys.argv:
        DRY[0] = True
    if "--scheduler" in sys.argv:
        try:
            ensure_dirs()
            scheduler_loop()
        except KeyboardInterrupt:
            pass
        sys.exit(0)
    if "--repair" in sys.argv:
        ensure_dirs()
        repair_folders()
        sys.exit(0)
    if "--test" in sys.argv:
        ensure_dirs()
        sys.exit(0 if self_test() else 1)
    if "--benchmark" in sys.argv:
        ensure_dirs()
        benchmark()
        sys.exit(0)
    if "--run-links" in sys.argv:
        ensure_dirs()
        UNATT[0] = True
        ST.ov["ask_selection"] = "all"
        run_saved_links()
        sys.exit(0)
    try:
        main()
    except (Quit, KeyboardInterrupt):
        print("\n[+] " + L("Выход.", "Bye."))
PYEOF
echo "$MF_BUILD" > "$CORE/.ver"
fi
chmod 700 "$CORE"/*.py 2>/dev/null

# ==========================================================================
#  ЗАПУСК: геолокация → окружение → главный цикл с «действиями», которые запрашивает меню
# ==========================================================================
printf '%b  ★ MediaForge  (%s)%b\n' "$C_AC" "$MF_ENV" "$C_RS"
cleanup() { [ -f "$CONF/loc.pid" ] && kill "$(cat "$CONF/loc.pid")" 2>/dev/null; rm -f "$CONF/loc.pid"; }
trap cleanup EXIT TERM
loc_keepalive
ensure_env

tries=0; crashes=0; sigsys=0
while [ "$tries" -lt 25 ]; do
  tries=$((tries + 1))
  rm -f "$CONF/action"
  python3 "$CORE/mediaforge.py" "$@"; rc=$?
  dbg "python rc=$rc"
  act=""
  if [ -f "$CONF/action" ]; then act="$(cat "$CONF/action")"; rm -f "$CONF/action"; fi
  case "$act" in
    repair)        find_alpine force; install_packages; ensure_pytools; ffmpeg_check; continue ;;
    upgrade_tools) run_spin "pip -U yt-dlp gallery-dl yt-dlp-ejs" pip_install yt-dlp gallery-dl yt-dlp-ejs; audit pip-upgrade tools; say_ok "$(T 'Инструменты обновлены.' 'Tools updated.')"; continue ;;
    nightly)       run_spin "yt-dlp nightly" pip_install --pre yt-dlp; audit pip-nightly yt-dlp; say_ok "yt-dlp nightly"; continue ;;
    pkgupdate)     update_pkgs; continue ;;
    applyupdate)   apply_update; continue ;;
    optional)      case "$MF_ENV" in ish|alpine) apk_update_retry; run_spin "tesseract (OCR)" apk_add_verify tesseract-ocr tesseract-ocr-data-rus tesseract-ocr-data-eng ;; termux) run_spin tesseract pkg install -y tesseract ;; debian) run_spin tesseract apt-get install -y tesseract-ocr tesseract-ocr-rus ;; esac; continue ;;
    tor)           case "$MF_ENV" in ish|alpine) apk_update_retry; run_spin "tor + lyrebird" apk_add_verify tor lyrebird || run_spin "tor + obfs4proxy" apk_add_verify tor obfs4proxy ;; termux) run_spin tor pkg install -y tor obfs4proxy ;; debian) run_spin tor apt-get install -y tor obfs4proxy ;; esac; audit tor-install "$MF_ENV"; continue ;;
    ffmpeghack)    run_spin "ffmpeg LD_PRELOAD" ffmpeg_hack; continue ;;
    pip:*)         _pk="${act#pip:}"; run_spin "pip $_pk" pip_install $_pk; audit pip-install "$_pk"; continue ;;
    rewrite)       if [ -f "$MF_SELF" ]; then MF_FORCE=1 exec sh "$MF_SELF"; else say_wn "$(T 'Перезапустите скрипт с MF_FORCE=1.' 'Re-run the script with MF_FORCE=1.')"; fi; continue ;;
  esac
  if [ "$rc" -eq 159 ]; then
    # SIGSYS (особенность iSH): менять Alpine бесполезно — просто перезапускаем ядро
    sigsys=$((sigsys + 1))
    say_wn "$(T 'SIGSYS (особенность iSH) — перезапуск ядра без смены Alpine.' 'SIGSYS (iSH quirk) — restarting core without switching Alpine.')"
    if [ "$sigsys" -ge 3 ]; then say_er "$(T 'Повторные SIGSYS. Запустите: sh MediaForge.sh --debug и пришлите ~/MediaForge/.config/debug.log' 'Repeated SIGSYS. Run: sh MediaForge.sh --debug and send ~/MediaForge/.config/debug.log')"; exit 159; fi
    continue
  fi
  if [ "$rc" -ge 128 ]; then
    crashes=$((crashes + 1))
    say_er "$(T "Python завершился аварийно (код $rc)." "Python crashed (code $rc).")"
    [ "$crashes" -ge 3 ] && { say_er "$(T 'Слишком много сбоев.' 'Too many crashes.')"; exit "$rc"; }
    # Alpine меняем только если сам Python не запускается
    if py_smoke; then say_wn "$(T 'Python исправен — Alpine не меняю, перезапуск.' 'Python is fine — keeping Alpine, restarting.')"; else find_alpine force || true; fi
    continue
  fi
  valid_alpine "$(alp_cur)" && is_apk && alp_cur > "$CONF/good_alpine" 2>/dev/null
  exit "$rc"
done
say_er "$(T 'Превышено число попыток.' 'Max retries reached.')"
exit 1
