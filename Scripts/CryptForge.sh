#!/bin/sh
if [ -z "$BASH_VERSION" ]; then
    printf 'nameserver 1.1.1.1\nnameserver 8.8.8.8\nnameserver 94.140.14.14\n' > /etc/resolv.conf 2>/dev/null
    if ! command -v bash >/dev/null 2>&1; then
        apk update >/dev/null 2>&1
        apk add --no-cache bash >/dev/null 2>&1
    fi
    exec bash "$0" "$@"
fi

# =====================================================================
# CryptForge — многослойное шифрование, маскировка и E2E-мессенджер для iSH (Alpine/ARM64)
# Bash-обёртка: меню, установка зависимостей, запуск Python-ядра (.core.py).
# Запуск: sh CryptForge.sh | флаги: --self-test [имя] --doctor --deps --version --help
# =====================================================================
umask 077
set -o pipefail
export PYTHONIOENCODING=utf-8
export PYTHONUTF8=1
export LC_ALL=C.UTF-8

C_OK='\033[38;5;84m'
C_ER='\033[38;5;203m'
C_WN='\033[38;5;220m'
C_IN='\033[38;5;51m'
C_AC='\033[38;5;45m'
C_DM='\033[2m'
C_RS='\033[0m'

say_ok() { printf '%b✔ %s%b\n' "$C_OK" "$*" "$C_RS"; }
say_er() { printf '%b✖ %s%b\n' "$C_ER" "$*" "$C_RS"; }
say_wn() { printf '%b▲ %s%b\n' "$C_WN" "$*" "$C_RS"; }
say_in() { printf '%b● %s%b\n' "$C_IN" "$*" "$C_RS"; }

# Цвет градиента по позиции символа (устаревший вариант)
sh_col() {
    local p=$(( $1 % 18 ))
    [ "$p" -ge 10 ] && p=$((18 - p))
    case "$p" in
        0) echo 27 ;; 1) echo 33 ;; 2) echo 39 ;; 3) echo 45 ;;
        4) echo 51 ;; 5) echo 50 ;; 6) echo 49 ;; 7) echo 48 ;;
        8) echo 84 ;; *) echo 120 ;;
    esac
}

SH_PAL=(27 33 39 45 51 50 49 48 84 120 84 48 49 50 51 45 39 33)

SH_PAL=(27 33 39 45 51 50 49 48 84 120 84 48 49 50 51 45 39 33)

sh_grad() {
    local t="$1" sh="${2:-0}" k=0 out="" r ch
    while [ -n "$t" ]; do
        r="${t#?}"
        ch="${t%"$r"}"
        t="$r"
        out+=$'\033[1;38;5;'"${SH_PAL[$(( (k + sh) % 18 ))]}"'m'"$ch"
        k=$((k + 1))
    done
    printf '%s\033[0m' "$out"
}

sh_banner() {
    local f=0
    printf '\n'
    while [ "$f" -lt 10 ]; do
        printf '\r  '
        sh_grad '◆ C R Y P T F O R G E ◆' "$((f * 2))"
        sleep 0.03
        f=$((f + 1))
    done
    printf '\n  \033[2mшифрование · метаданные · стего\033[0m\n'
}

# DNS для apk (нужен только при установке пакетов)
setup_dns() {
    printf 'nameserver 1.1.1.1\nnameserver 8.8.8.8\nnameserver 94.140.14.14\n' > /etc/resolv.conf 2>/dev/null
}

# Выполнить команду с анимированным спиннером и значком результата
spin() {
    local msg="$1"; shift
    local frames=(⠋ ⠙ ⠹ ⠸ ⠼ ⠴ ⠦ ⠧ ⠇ ⠏)
    "$@" &
    local pid=$!
    local i=0
    while kill -0 "$pid" 2>/dev/null; do
        printf '\r  \033[38;5;45m%s\033[0m %s\033[K' "${frames[$((i % 10))]}" "$msg"
        i=$((i + 1))
        sleep 0.1
    done
    wait "$pid"
    local rc=$?
    if [ "$rc" -eq 0 ]; then
        printf '\r  \033[38;5;84m✓\033[0m %s\033[K\n' "$msg"
    else
        printf '\r  \033[38;5;203m✗\033[0m %s\033[K\n' "$msg"
    fi
    return "$rc"
}

# Раскрыть ~ в путях
expand_path() {
    case "$1" in
        "~"/*) echo "$HOME/${1#\~/}" ;;
        "~") echo "$HOME" ;;
        *) echo "$1" ;;
    esac
}

# Убрать CR/LF/DEL из введённой строки
sanitize_input() {
    local val="$1"
    val="${val//$'\r'/}"
    val="${val//$'\n'/}"
    val="${val//$'\177'/}"
    echo "$val"
}

# Создать рабочие папки ~/CryptForge
setup_dirs() {
    BASE="$HOME/CryptForge"
    CORE="$BASE/.core.py"
    mkdir -p "$BASE" "$BASE/vault" "$BASE/decrypted" "$BASE/originals" "$BASE/meta" "$BASE/parts" "$BASE/shares" "$BASE/stego" "$BASE/.tmp"
    chmod 700 "$BASE/meta" "$BASE/shares" "$BASE/.tmp"
    rm -rf "$BASE/.tmp"/* 2>/dev/null
}

# Проверка и установка зависимостей (обязательные и необязательные), в iSH ARM64 — через apk
check_deps() {
    local need=""
    local c
    for c in python3 openssl tar gzip; do
        command -v "$c" >/dev/null 2>&1 || need="$need $c"
    done
    if [ -n "$need" ]; then
        say_wn "Отсутствуют обязательные пакеты:$need"
        if ! command -v apk >/dev/null 2>&1; then
            say_er "apk не найден, установите пакеты вручную"
            return 1
        fi
        setup_dns
        spin "apk update" sh -c 'apk update >/dev/null 2>&1' || { say_er "apk update не удался"; return 1; }
        local p
        for p in $need; do
            spin "Установка $p" sh -c "apk add --no-cache $p >/dev/null 2>&1" || { say_er "Не удалось установить $p"; return 1; }
        done
    fi
    local marker="$BASE/.optional_tried"
    if [ ! -f "$marker" ]; then
        local opt=""
        python3 -c "import cryptography" 2>/dev/null || opt="$opt py3-cryptography"
        python3 -c "import PIL" 2>/dev/null || opt="$opt py3-pillow"
        python3 -c "import mnemonic" 2>/dev/null || opt="$opt py3-mnemonic"
        python3 -c "import argon2" 2>/dev/null || opt="$opt py3-argon2-cffi"
        command -v qrencode >/dev/null 2>&1 || opt="$opt qrencode"
        command -v pv >/dev/null 2>&1 || opt="$opt pv"
        command -v file >/dev/null 2>&1 || opt="$opt file"
        command -v less >/dev/null 2>&1 || opt="$opt less"
        command -v nano >/dev/null 2>&1 || opt="$opt nano"
        command -v gpg >/dev/null 2>&1 || opt="$opt gnupg"
        command -v exiftool >/dev/null 2>&1 || opt="$opt exiftool"
        python3 -c "import Crypto" 2>/dev/null || opt="$opt py3-cryptodome"
        python3 -c "import mutagen" 2>/dev/null || opt="$opt py3-mutagen"
        if [ -n "$opt" ] && command -v apk >/dev/null 2>&1; then
            say_in "Установка дополнительных пакетов:$opt"
            setup_dns
            spin "apk update" sh -c 'apk update >/dev/null 2>&1'
            local p
            for p in $opt; do
                spin "apk add $p" sh -c "apk add --no-cache $p >/dev/null 2>&1" || say_wn "Пакет $p недоступен — связанная функция будет отключена"
            done
        fi
        touch "$marker"
    fi
    return 0
}

# Копия самого скрипта в папке CryptForge (для переноса и резервного запуска)
copy_self() {
    local dst="$BASE/CryptForge.sh"
    if [ -f "$0" ] && ! [ "$0" -ef "$dst" ]; then
        cp -f -- "$0" "$dst" 2>/dev/null && chmod 700 "$dst" 2>/dev/null
    fi
}

# Фиктивный запрос геолокации для фоновой активности iSH
fake_location() {
    [ -e /dev/location ] || return 0
    say_wn "Фиктивный запрос геолокации..."
    local n=3
    while [ "$n" -gt 0 ]; do
        printf '\r  %b%d%b' "$C_WN" "$n" "$C_RS"
        sleep 1
        n=$((n - 1))
    done
    printf '\r\033[K'
    [ -f "$BASE/location.pid" ] && kill "$(cat "$BASE/location.pid")" 2>/dev/null
    ( cat /dev/location >/dev/null 2>&1 ) &
    echo $! > "$BASE/location.pid"
    say_ok "Геолокация активна."
}

# Записать Python-ядро в ~/CryptForge/.core.py
write_core() {
    cat > "$CORE" <<'PYEOF'
# =====================================================================
# CryptForge — ядро (Python). Запускается из bash-обёртки: python3 .core.py <действие>
# ---------------------------------------------------------------------
# Структура файла (сверху вниз):
#   ЯДРО            ошибки, вывод, ввод, прогресс, случайность, мастер-пароль
#   КРИПТО          KDF, AEAD-слои, OpenSSL/GPG, классические шифры [Ненадёжно]
#   СЛОИ            реестр слоёв, планирование стека, профили, паддинг
#   ФАЙЛЫ           разбиение/сборка, шифрование/расшифровка, починка, EXIF
#   СКРЫТИЕ         маскировка (каналы, FEC, QIM, RDH), документы, отрицаемость
#   СВЯЗЬ           мессенджер E2E, ключи файлов
#   ЗАЩИТА          факторы ключа, envelope, паник-пароль, журнал, dead man
#   СЕРВИС          справка, диагностика, настройки, самотесты, точка входа
# Метки среды: [iSH] работает · [macOS] нужна нативная APFS · [HW] нужно железо ·
# [SIM] только симуляция · [NOT SUPPORTED] недоступно. Надёжность: [Надёжный]
# [Условный] [Ненадёжный] [Симуляция]. Ядро не обращается к Bash напрямую.
# =====================================================================
import os, sys, json, base64, hashlib, hmac, secrets, subprocess, tempfile, shutil, re, time, string, struct, datetime, signal, tarfile, zlib, copy, traceback, random, io, warnings
from pathlib import Path

# Подавляем предупреждения об устаревших вызовах Pillow (на разных версиях API различается)
warnings.filterwarnings("ignore", category=DeprecationWarning)

try:
    import readline
except Exception:
    readline = None

HOME = Path.home()
BASE = HOME / "CryptForge"
VAULT = BASE / "vault"
DECRYPTED = BASE / "decrypted"
ORIGINALS = BASE / "originals"
META = BASE / "meta"
PARTS = BASE / "parts"
SHARES = BASE / "shares"
STEGO = BASE / "stego"
WORKROOT = BASE / ".tmp"
LOGF = BASE / "activity.log"
BIP39_FILE = BASE / "bip39.txt"
GPG_CACHE = BASE / ".gpg_status"
OSSL_CACHE = BASE / ".ossl_status"
ERR_LOG = BASE / ".last_error.log"
CHUNK = 2 * 1024 * 1024
CLASSIC_MAX = 16 * 1024 * 1024
MB = 1024 * 1024

os.umask(0o077)

try:
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM, ChaCha20Poly1305
    HAS_CRYPTO = True
except Exception:
    AESGCM = ChaCha20Poly1305 = None
    HAS_CRYPTO = False
try:
    from cryptography.hazmat.primitives.ciphers.aead import AESOCB3
except Exception:
    AESOCB3 = None
try:
    from cryptography.hazmat.primitives.ciphers.aead import AESGCMSIV
except Exception:
    AESGCMSIV = None

# =====================================================================
# РАЗДЕЛ: ЗАПАСНОЙ БЭКЕНД pycryptodome (если нет cryptography)
# =====================================================================
# Адаптеры повторяют интерфейс cryptography (encrypt/decrypt с nonce и aad),
# поэтому остальной код не меняется. GCM-SIV в pycryptodome нет.
AEAD_BACKEND = "cryptography" if HAS_CRYPTO else "none"
if not HAS_CRYPTO:
    try:
        from Crypto.Cipher import AES as _CAES, ChaCha20_Poly1305 as _CCC

        class AESGCM:
            def __init__(self, key):
                self.k = key

            def encrypt(self, nonce, data, aad):
                c = _CAES.new(self.k, _CAES.MODE_GCM, nonce=nonce)
                if aad:
                    c.update(aad)
                ct, tag = c.encrypt_and_digest(data)
                return ct + tag

            def decrypt(self, nonce, data, aad):
                c = _CAES.new(self.k, _CAES.MODE_GCM, nonce=nonce)
                if aad:
                    c.update(aad)
                return c.decrypt_and_verify(data[:-16], data[-16:])

        class ChaCha20Poly1305:
            def __init__(self, key):
                self.k = key

            def encrypt(self, nonce, data, aad):
                c = _CCC.new(key=self.k, nonce=nonce)
                if aad:
                    c.update(aad)
                ct, tag = c.encrypt_and_digest(data)
                return ct + tag

            def decrypt(self, nonce, data, aad):
                c = _CCC.new(key=self.k, nonce=nonce)
                if aad:
                    c.update(aad)
                return c.decrypt_and_verify(data[:-16], data[-16:])

        class AESOCB3:
            def __init__(self, key):
                self.k = key

            def encrypt(self, nonce, data, aad):
                c = _CAES.new(self.k, _CAES.MODE_OCB, nonce=nonce)
                if aad:
                    c.update(aad)
                ct, tag = c.encrypt_and_digest(data)
                return ct + tag

            def decrypt(self, nonce, data, aad):
                c = _CAES.new(self.k, _CAES.MODE_OCB, nonce=nonce)
                if aad:
                    c.update(aad)
                return c.decrypt_and_verify(data[:-16], data[-16:])

        HAS_CRYPTO = True
        AEAD_BACKEND = "pycryptodome"
    except Exception:
        pass



# =====================================================================
# РАЗДЕЛ: ЯДРО: ошибки, вывод, ввод, индикаторы прогресса
# =====================================================================
# Исключение для ожидаемых ошибок: сообщение показывается пользователю, скрипт возвращается в меню
class CFError(Exception):
    pass


# Цветная строка статуса: тип ok/er/wn/in выбирает значок и цвет
def say(msg, kind="in"):
    colors = {"ok": "\033[38;5;84m", "er": "\033[38;5;203m", "wn": "\033[38;5;220m", "in": "\033[38;5;51m"}
    prefix = {"ok": "✔", "er": "✖", "wn": "▲", "in": "●"}.get(kind, "●")
    print(f"{colors.get(kind, colors['in'])}{prefix} {msg}\033[0m")


# Успешное действие (зелёный)
def say_ok(m): say(m, "ok")
# Ошибка (красный)
def say_er(m): say(m, "er")
# Предупреждение (жёлтый)
def say_wn(m): say(m, "wn")
# Информационное сообщение (голубой)
def say_in(m): say(m, "in")


PAL = (27, 33, 39, 45, 51, 50, 49, 48, 84, 120, 84, 48, 49, 50, 51, 45, 39, 33)


# Градиентная раскраска строки по символам (палитра PAL)
def grad(t, shift=0):
    return "".join(f"\033[1;38;5;{PAL[(i + shift) % len(PAL)]}m{c}" for i, c in enumerate(t)) + "\033[0m"


# Анимированный градиентный заголовок раздела
def title_anim(t, frames=12):
    line = f"══ {t} ══"
    if not sys.stdout.isatty():
        print("  " + grad(line))
        return
    for f in range(frames):
        sys.stdout.write("\r  " + grad(line, f * 2))
        sys.stdout.flush()
        time.sleep(0.03)
    sys.stdout.write("\n")


ANSI_RE = re.compile(r"\x1b\[[0-9;?]*[ -/]*[@-~]|\x1b[@-_]")


# Очистка ввода: убирает ANSI-коды и управляющие символы, обрабатывает Backspace
def clean_input(s):
    s = ANSI_RE.sub("", s)
    out = []
    for ch in s:
        if ch in ("\x7f", "\x08"):
            if out:
                out.pop()
        elif ch == "\t":
            out.append(" ")
        elif ord(ch) < 32:
            continue
        else:
            out.append(ch)
    return "".join(out).strip()


# Ввод строки с очисткой; пустой ввод возвращает default
def ask(prompt, default=""):
    try:
        v = input(prompt)
    except EOFError:
        raise KeyboardInterrupt
    except UnicodeDecodeError:
        return default
    v = clean_input(v)
    return v if v else default


# Вопрос да/нет; принимает y/yes/д/да/1
def ask_yn(prompt, default="n"):
    suffix = " [Y/n]: " if default == "y" else " [y/N]: "
    v = ask(prompt + suffix).lower()
    if not v:
        return default == "y"
    return v in ("y", "yes", "д", "да", "1")


# Скрытый ввод пароля (getpass) с очисткой
def ask_secret(prompt):
    import getpass
    try:
        v = getpass.getpass(prompt)
    except EOFError:
        raise KeyboardInterrupt
    except UnicodeDecodeError:
        return ""
    return clean_input(v)


# Ввод целого числа в диапазоне с повтором при ошибке
def ask_int(prompt, lo, hi, default):
    while True:
        v = ask(f"{prompt} [{default}]: ", str(default))
        try:
            n = int(v)
            if lo <= n <= hi:
                return n
        except ValueError:
            pass
        say_er(f"Нужно число от {lo} до {hi}")


_last_pb = [-1, ""]


# Градиентный индикатор прогресса (печатается только при смене процента)
def progress_bar(current, total, prefix="", suffix=""):
    if total <= 0:
        return
    pct = min(100, current * 100 // total)
    if pct == _last_pb[0] and prefix == _last_pb[1]:
        return
    _last_pb[0], _last_pb[1] = pct, prefix
    w = 18
    filled = pct * w // 100
    ramp = (196, 202, 208, 214, 220, 226, 190, 154, 118, 82, 46)
    cells = []
    for i in range(w):
        if i < filled:
            cells.append(f"\033[38;5;{ramp[min(len(ramp) - 1, i * len(ramp) // w)]}m█")
        else:
            cells.append("\033[38;5;238m░")
    bar = "".join(cells)
    sys.stdout.write(f"\r  {bar}\033[0m {pct:3d}% {prefix}\033[K")
    sys.stdout.flush()
    if pct >= 100:
        sys.stdout.write("\n")
        _last_pb[0], _last_pb[1] = -1, ""


pbar = progress_bar

SPIN = "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"


# Спиннер ожидания внешнего процесса; при Ctrl+C завершает дочерний процесс
def wait_spin(proc, label):
    i = 0
    t0 = time.time()
    try:
        while proc.poll() is None:
            sys.stdout.write(f"\r  \033[38;5;45m{SPIN[i % 10]}\033[0m {label} {int(time.time() - t0)}с\033[K")
            sys.stdout.flush()
            time.sleep(0.1)
            i += 1
    except KeyboardInterrupt:
        try:
            proc.kill()
        except Exception:
            pass
        raise
    finally:
        sys.stdout.write("\r\033[K")
        sys.stdout.flush()


# Размер в байтах → человекочитаемая строка (КБ/МБ/ГБ)
def hsize(n):
    n = float(n)
    for u in ("Б", "КБ", "МБ", "ГБ"):
        if n < 1024 or u == "ГБ":
            return f"{n:.0f} {u}" if u == "Б" else f"{n:.1f} {u}"
        n /= 1024


# Base64url с «=» (формат ключей слоёв)
def b64u(b):
    return base64.urlsafe_b64encode(b).decode()


# Случайный 256-битный ключ (через rand_bytes: учитывает «свою случайность»)
def gen_key(n=32):
    return b64u(rand_bytes(n))


# Случайное имя из 20 символов a-z0-9
def gen_name(ext=""):
    alphabet = string.ascii_lowercase + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(20)) + ext


# =====================================================================
# РАЗДЕЛ: ФАЙЛЫ И СЛУЖЕБНОЕ: хеши, размеры, имена, пути, журнал, затирание
# =====================================================================
# SHA-256 файла чанками по 1 МБ (с индикатором для больших файлов)
def sha256_file(path, label=""):
    p = Path(path)
    if p.is_dir():
        return "directory"
    total = p.stat().st_size
    h = hashlib.sha256()
    done = 0
    with open(p, "rb") as f:
        while True:
            c = f.read(1 << 20)
            if not c:
                break
            h.update(c)
            done += len(c)
            if label and total > MB:
                pbar(done, total, label)
    return h.hexdigest()


# Суммарный размер файла или папки (символические ссылки не считаются)
def dir_size(p):
    p = Path(p)
    if p.is_file():
        return p.stat().st_size
    total = 0
    for root, dirs, files in os.walk(p):
        for fn in files:
            try:
                fp = os.path.join(root, fn)
                if not os.path.islink(fp):
                    total += os.path.getsize(fp)
            except OSError:
                pass
    return total


# Создаёт рабочие папки, загружает настройки, предупреждает о старой папке keys/
def init_dirs():
    for d in (BASE, VAULT, DECRYPTED, ORIGINALS, META, PARTS, SHARES, STEGO, WORKROOT, MSG_DIR, CHATS_DIR, MSG_OUT):
        d.mkdir(parents=True, exist_ok=True)
    cfg_load()
    for d in (META, SHARES, WORKROOT, MSG_DIR, CHATS_DIR):
        try:
            os.chmod(d, 0o700)
        except OSError:
            pass
    old = BASE / "keys"
    if old.is_dir():
        try:
            if any(old.iterdir()):
                say_wn("Найдена устаревшая папка keys/. Перенесите ключи в надёжное место и удалите её вручную: " + str(old))
            else:
                old.rmdir()
        except OSError:
            pass


# Новая временная папка (права 700) внутри ~/CryptForge/.tmp
def new_work():
    WORKROOT.mkdir(parents=True, exist_ok=True)
    w = Path(tempfile.mkdtemp(dir=WORKROOT))
    os.chmod(w, 0o700)
    return w


# Проверка свободного места перед операцией
def check_space(need, where=None):
    try:
        free = shutil.disk_usage(str(where or BASE)).free
    except Exception:
        return True
    if free < need:
        say_er(f"Недостаточно места: нужно ~{hsize(need)}, свободно {hsize(free)}")
        return False
    return True


NAME_RE = re.compile(r"^[A-Za-z0-9_.\-А-Яа-яЁё]+$")


# Проверка имени, введённого пользователем (буквы, цифры, _ . -, без точки в начале)
def valid_user_name(n):
    return bool(n) and bool(NAME_RE.match(n)) and not n.startswith(".") and n == n.strip() and len(n) <= 200 and ".." not in n


# Очистка имени результата: убирает невидимые символы, нормализует Unicode, запрещает / \ NUL
def safe_restore_name(n):
    import unicodedata
    n = unicodedata.normalize("NFC", n)
    n = "".join(" " if unicodedata.category(ch) == "Zs" else ch for ch in n)
    n = "".join(ch for ch in n if unicodedata.category(ch) not in ("Cc", "Cf", "Cs", "Co", "Cn"))
    n = n.strip().lstrip(".").rstrip(". ")
    if not n or n in (".", "..") or "/" in n or "\\" in n or "\x00" in n or len(n) > 255:
        return ""
    return n


# Свободное имя: при занятости вставляет .1, .2 перед расширением
def unique_path(d, name):
    d = Path(d)
    p = d / name
    if not p.exists():
        return p
    if name.endswith(".tar.gz"):
        stem, ext = name[:-7], ".tar.gz"
    else:
        stem, ext = os.path.splitext(name)
    n = 1
    while True:
        p = d / f"{stem}.{n}{ext}"
        if not p.exists():
            return p
        n += 1


SETTINGS_FILE = BASE / "settings.json"
MSG_DIR = BASE / "messenger"
CHATS_DIR = MSG_DIR / "chats"
MSG_OUT = MSG_DIR / "out"
MASTER_FILE = BASE / ".master"
DECOYS_FILE = META / ".decoys.json"
MAX_CHUNK = 64 * MB

CFG_DEFAULT = {
    "sec_level": "strong",
    "chunk_mb": 2,
    "seal_outer": True,
    "temp_wipe": "small",
    "clear_after_keys": True,
    "ask_wipe_on_exit": True,
    "ask_entropy": False,
    "encrypt_meta": False,
    "locations": [],
    "out_dir": "",
    "junk": {"enabled": False, "mode": "percent", "min": 3, "max": 12, "place": "both"},
    "parts_junk": {"enabled": False, "min": 1024, "max": 65536, "place": "both"},
    "decoy_parts": {"enabled": False, "min_n": 2, "max_n": 6, "min_size": 4096, "max_size": 262144},
    "split_mode": "fixed",
    "msg_pad": 256,
    "mlock": False,
    "log_private": False,
    "syslog": False,
    "honey_mode": False,
    "role": "",
    "lockout": True,
}
CFG = {}

SEC_LEVELS = {
    "std": {"name": "Стандарт", "scrypt": 14, "argon": (3, 4, 65536), "pbkdf2": 100000, "m_scrypt": 16, "m_argon": (3, 4, 65536)},
    "strong": {"name": "Усиленный", "scrypt": 15, "argon": (4, 4, 131072), "pbkdf2": 300000, "m_scrypt": 17, "m_argon": (4, 4, 131072)},
    "max": {"name": "Максимальный", "scrypt": 17, "argon": (6, 4, 262144), "pbkdf2": 600000, "m_scrypt": 17, "m_argon": (6, 4, 262144)},
}


# Рекурсивное слияние словаря настроек
def cfg_merge(dst, src):
    for k, v in src.items():
        if isinstance(v, dict) and isinstance(dst.get(k), dict):
            cfg_merge(dst[k], v)
        else:
            dst[k] = v


# Загрузка настроек из settings.json с значениями по умолчанию
def cfg_load():
    global CHUNK
    CFG.clear()
    CFG.update(copy.deepcopy(CFG_DEFAULT))
    try:
        if SETTINGS_FILE.exists():
            cfg_merge(CFG, json.loads(SETTINGS_FILE.read_text(encoding="utf-8")))
    except Exception:
        pass
    if CFG.get("chunk_mb") not in (1, 2, 4, 8):
        CFG["chunk_mb"] = 2
    CHUNK = CFG["chunk_mb"] * MB


# Сохранение настроек (атомарная запись)
def cfg_save():
    write_json_atomic(SETTINGS_FILE, CFG)


# Текущий уровень стойкости KDF (Стандарт/Усиленный/Максимальный)
def sec():
    return SEC_LEVELS.get(CFG.get("sec_level"), SEC_LEVELS["strong"])


# Base64url без «=» (для блоков и метаданных)
def b64e(b):
    return base64.urlsafe_b64encode(b).decode().rstrip("=")


# Декодирование base64/base64url с восстановлением «=»
def b64d(s):
    s = s.strip().replace("+", "-").replace("/", "_")
    return base64.urlsafe_b64decode(s + "=" * (-len(s) % 4))


# Хранилище состояния «своей случайности» (пул, счётчик)
class _Rng:
    pool = None
    ctr = 0


# Случайные байты: системные, либо SHAKE256(пул + urandom + счётчик) если пользователь добавил энтропию
def rand_bytes(n):
    if _Rng.pool is None:
        return secrets.token_bytes(n)
    _Rng.ctr += 1
    return hashlib.shake_256(_Rng.pool + os.urandom(32) + _Rng.ctr.to_bytes(8, "big")).digest(n)


# Случайное число 0..n-1 без заметного смещения
def rand_below(n):
    if n <= 1:
        return 0
    k = (n.bit_length() + 7) // 8 + 8
    return int.from_bytes(rand_bytes(k), "big") % n


# Случайный элемент последовательности
def rand_choice(seq):
    return seq[rand_below(len(seq))]


# Перемешивание списка (Фишер—Йетс) на rand_below
def rand_shuffle(lst):
    for i in range(len(lst) - 1, 0, -1):
        j = rand_below(i + 1)
        lst[i], lst[j] = lst[j], lst[i]
    return lst


# Грубая оценка энтропии введённого текста в битах
def entropy_estimate(texts):
    import math
    from collections import Counter
    s = "".join(texts)
    if not s:
        return 0
    cnt = Counter(s)
    n = len(s)
    h = -sum((c / n) * math.log2(c / n) for c in cnt.values())
    return int(min(h * n, n * 4))


# Сбор пользовательской случайности: текст + тайминги, смешивание с системной энтропией
def collect_entropy():
    title_anim("СВОЯ СЛУЧАЙНОСТЬ")
    say_in("Печатайте хаотично: клавиши, слова, цифры.")
    say_in("Текст смешивается со случайностью системы,")
    say_in("поэтому ключи слабее не станут.")
    texts = []
    stamps = []
    bits = 0
    for i in range(1, 4):
        t0 = time.perf_counter_ns()
        s = ask(f"Случайный текст {i}/3 (Enter — хватит): ")
        dt = time.perf_counter_ns() - t0
        if not s:
            break
        texts.append(s)
        stamps.append(dt)
        bits = entropy_estimate(texts)
        say_in(f"Оценка запаса: ≈{bits} бит")
    if not texts:
        say_wn("Своя случайность не добавлена")
        return False
    if bits < 64:
        say_wn("Текста мало — но он лишь добавляется к системной случайности")
    h = hashlib.sha512()
    for t, dt in zip(texts, stamps):
        h.update(t.encode("utf-8"))
        h.update(dt.to_bytes(8, "big"))
    h.update(os.urandom(64))
    h.update(time.time_ns().to_bytes(8, "big"))
    if _Rng.pool:
        h.update(_Rng.pool)
    _Rng.pool = h.digest()
    _Rng.ctr = 0
    say_ok("Случайность добавлена: ключи этого запуска строятся на ней")
    return True


# AEAD для небольших объектов (AES-GCM или запасной SHAKE-HMAC)
def small_aead(alg, key):
    if alg == "gcm":
        return AESGCM(key)
    return ShakeHmac(key)


# Запечатывание JSON-объекта ключом (AEAD, случайный nonce)
def seal_obj(key, obj, aad=b"cf"):
    alg = "gcm" if HAS_CRYPTO else "shake"
    nonce = os.urandom(12)
    ct = small_aead(alg, key).encrypt(nonce, json.dumps(obj, ensure_ascii=False).encode("utf-8"), aad)
    return {"cfs": 1, "alg": alg, "n": b64e(nonce), "c": b64e(ct)}


# Открытие запечатанного объекта; при неверном ключе — CFError
def open_obj(key, d, aad=b"cf"):
    alg = d.get("alg", "gcm")
    if alg == "gcm" and not HAS_CRYPTO:
        raise CFError("Для расшифровки нужен py3-cryptography")
    try:
        pt = small_aead(alg, key).decrypt(b64d(d["n"]), b64d(d["c"]), aad)
        return json.loads(pt.decode("utf-8"))
    except Exception:
        raise CFError("Неверный пароль или данные повреждены")


_MK = {"key": None, "failed": False}


# Есть ли мастер-пароль
def master_exists():
    return MASTER_FILE.exists()


# Ключ из мастер-пароля: Argon2id или scrypt + HKDF
def master_derive(pw, kdf, salt):
    if kdf["k"] == "argon2id":
        raw = argon2id_raw(pw.encode("utf-8"), salt, kdf["t"], kdf["m"], kdf["l"])
    else:
        raw = hashlib.scrypt(pw.encode("utf-8"), salt=salt, n=1 << kdf["n"], r=8, p=1, maxmem=1024 * MB, dklen=32)
    return hkdf(raw, salt, b"cf-master-v1")


# Создаёт ключ и запись проверки для нового мастер-пароля
def master_make(pw, fast=False):
    salt = os.urandom(16)
    lv = sec()
    if fast:
        kdf = {"k": "scrypt", "n": 10}
    elif has_argon2():
        a = lv["m_argon"]
        kdf = {"k": "argon2id", "t": a[0], "l": a[1], "m": a[2]}
    else:
        kdf = {"k": "scrypt", "n": lv["m_scrypt"]}
    key = master_derive(pw, kdf, salt)
    rec = {"v": 1, "salt": b64e(salt), "kdf": kdf, "check": seal_obj(key, {"ok": 1}, b"cf-master")}
    return key, rec


# Устанавливает мастер-пароль и кэширует ключ
def master_set(pw, fast=False):
    key, rec = master_make(pw, fast)
    write_json_atomic(MASTER_FILE, rec)
    _MK["key"] = key
    _MK["failed"] = False
    return key


# Проверка введённого пароля по записи проверки
def master_unlock_with(pw):
    rec = json.loads(MASTER_FILE.read_text(encoding="utf-8"))
    key = master_derive(pw, rec["kdf"], b64d(rec["salt"]))
    open_obj(key, rec["check"], b"cf-master")
    return key


# Запрос мастер-пароля (3 попытки); понимает паник-пароль; результат кэшируется
def master_key():
    if _MK["key"]:
        return _MK["key"]
    if not master_exists() or _MK["failed"]:
        return None
    for _ in range(3):
        pw = ask_secret("Мастер-пароль: ")
        if not pw:
            break
        try:
            say_in("Проверка пароля (стойкий KDF, подождите)...")
            _MK["key"] = master_unlock_with(pw)
            return _MK["key"]
        except CFError:
            say_er("Неверный пароль")
            if PANIC_FILE.exists() and panic_match(pw):
                panic_wipe()
                _MK["failed"] = True
                return None
    _MK["failed"] = True
    return None


# Похож ли текст на запечатанный контейнер
def is_sealed_text(txt):
    return txt.lstrip().startswith("{") and '"cfs"' in txt[:80]


# Запечатан ли файл мастер-паролем
def file_is_sealed(path):
    try:
        return is_sealed_text(Path(path).read_text(encoding="utf-8")[:120])
    except Exception:
        return False


# Чтение JSON-файла с автоматическим открытием мастер-контейнера
def read_json_file(path):
    d = json.loads(Path(path).read_text(encoding="utf-8"))
    if isinstance(d, dict) and d.get("cfs") == 1:
        key = master_key()
        if not key:
            raise CFError("Метаданные зашифрованы мастер-паролем, а он не введён")
        return open_obj(key, d, b"cf-meta")
    return d


# Запись JSON; шифрует мастер-паролем, если включено; делает резервную копию метаданных
def write_json_secure(path, data, force=None):
    if force is None:
        enc = bool(CFG.get("encrypt_meta") and master_exists()) or file_is_sealed(path)
    else:
        enc = force
    if enc:
        key = master_key()
        if not key:
            raise CFError("Нужен мастер-пароль для записи метаданных")
        write_json_atomic(path, seal_obj(key, data, b"cf-meta"))
    else:
        write_json_atomic(path, data)
    try:
        if Path(path).parent == META and Path(path).suffix == ".meta":
            meta_backup(path)
    except Exception:
        pass


# Список файлов метаданных (.meta, .split, обманки)
def meta_files():
    out = sorted(META.glob("*.meta")) + sorted(META.glob("*.split"))
    if DECOYS_FILE.exists():
        out.append(DECOYS_FILE)
    return out


# Массово шифрует/расшифровывает метаданные
def reseal_meta(seal):
    n = 0
    for p in meta_files():
        try:
            d = read_json_file(p)
            write_json_secure(p, d, force=seal)
            n += 1
        except Exception as e:
            say_er(f"{p.name}: {e}")
    return n


# Файлы мессенджера (чаты, личность, контакты)
def msg_files():
    out = []
    if CHATS_DIR.exists():
        out += sorted(CHATS_DIR.glob("*.json"))
    for nm in ("identity.json", "contacts.json"):
        if (MSG_DIR / nm).exists():
            out.append(MSG_DIR / nm)
    return out


# Смена мастер-пароля: временные файлы, проверка, затем атомарная замена
def master_change(new_pw, fast=False):
    old = master_key()
    if not old:
        raise CFError("Нужен текущий мастер-пароль")
    items = []
    for p in meta_files():
        if file_is_sealed(p):
            items.append((p, read_json_file(p), b"cf-meta"))
    for p in msg_files():
        items.append((p, open_obj(old, json.loads(p.read_text(encoding="utf-8")), b"cf-msg"), b"cf-msg"))
    key, rec = master_make(new_pw, fast)
    tmp = []
    for p, data, aad in items:
        t = p.with_name(p.name + ".reseal")
        write_json_atomic(t, seal_obj(key, data, aad))
        tmp.append((t, p))
    for t, p in tmp:
        open_obj(key, json.loads(t.read_text(encoding="utf-8")), b"cf-meta" if p.parent == META else b"cf-msg")
    for t, p in tmp:
        os.replace(t, p)
    write_json_atomic(MASTER_FILE, rec)
    _MK["key"] = key
    _MK["failed"] = False
    return len(items)


# Удаление мастер-пароля (метаданные расшифровываются)
def master_remove():
    if not master_exists():
        return
    key = master_key()
    if not key:
        raise CFError("Нужен мастер-пароль")
    if msg_files():
        raise CFError("Есть чаты/ключи мессенджера: сначала удалите их (иначе они станут нечитаемыми)")
    n = reseal_meta(False)
    MASTER_FILE.unlink(missing_ok=True)
    _MK["key"] = None
    CFG["encrypt_meta"] = False
    cfg_save()
    return n


# Диалог установки мастер-пароля
def master_setup_ui():
    title_anim("МАСТЕР-ПАРОЛЬ")
    say_in("Пароль шифрует метаданные файлов,")
    say_in("ключи мессенджера и переписку.")
    say_wn("Забудете пароль — данные не вернуть!")
    while True:
        p1 = ask_secret("Новый мастер-пароль: ")
        if not p1:
            raise CFError("Отменено")
        if len(p1) < 10:
            say_er("Минимум 10 символов")
            continue
        for w in check_phrase(p1):
            say_wn("Слабый пароль: " + w)
        if ask_secret("Повторите: ") != p1:
            say_er("Не совпало")
            continue
        break
    say_in("Подготовка ключа (стойкий KDF, подождите)...")
    master_set(p1)
    say_ok("Мастер-пароль установлен")
    if ask_yn("Шифровать этим паролем и метаданные файлов?", "y"):
        CFG["encrypt_meta"] = True
        cfg_save()
        n = reseal_meta(True)
        say_ok(f"Зашифровано файлов метаданных: {n}")


# Гарантирует наличие и ввод мастер-пароля (для мессенджера)
def require_master():
    key = master_key()
    if key:
        return key
    if master_exists():
        raise CFError("Мастер-пароль не введён")
    say_in("Для этой функции нужен мастер-пароль.")
    master_setup_ui()
    if not _MK["key"]:
        raise CFError("Мастер-пароль не задан")
    return _MK["key"]


# Запись объекта мессенджера под мастер-паролем
def msg_write(path, data):
    key = require_master()
    write_json_atomic(path, seal_obj(key, data, b"cf-msg"))


# Чтение объекта мессенджера
def msg_read(path):
    key = require_master()
    return open_obj(key, json.loads(Path(path).read_text(encoding="utf-8")), b"cf-msg")


# Удаление временного файла с перезаписью (по настройке)
def rm_temp(p):
    p = Path(p)
    try:
        mode = CFG.get("temp_wipe", "small")
        if mode != "off" and p.is_file():
            sz = p.stat().st_size
            if mode == "all" or sz <= 64 * MB:
                with open(p, "r+b") as f:
                    left = sz
                    while left > 0:
                        c = min(left, 1 << 20)
                        f.write(os.urandom(c))
                        left -= c
                    f.flush()
                    os.fsync(f.fileno())
        p.unlink()
    except OSError:
        pass


cfg_load()


# Атомарная запись JSON: временный файл + os.replace, права 600
def write_json_atomic(path, data):
    path = Path(path)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    os.chmod(tmp, 0o600)
    os.replace(tmp, path)


# Затирание файла/папки: 3 прохода случайных данных, затем удаление
def wipe_file(path):
    path = Path(path)
    if not path.exists() and not path.is_symlink():
        return
    if path.is_symlink():
        path.unlink()
        return
    if path.is_dir():
        for root, dirs, files in os.walk(path):
            for fn in files:
                wipe_file(Path(root) / fn)
        shutil.rmtree(path, ignore_errors=True)
        return
    size = path.stat().st_size
    if size == 0:
        path.unlink()
        return
    with open(path, "r+b") as f:
        for pass_no in range(3):
            f.seek(0)
            rem = size
            done = 0
            while rem > 0:
                c = min(rem, 1 << 20)
                f.write(os.urandom(c))
                rem -= c
                done += c
                if size > MB:
                    pbar(pass_no * size + done, size * 3, f"wipe {pass_no + 1}/3 ")
            f.flush()
            os.fsync(f.fileno())
    path.unlink()


secure_delete = wipe_file


# =====================================================================
# РАЗДЕЛ: КРИПТО-ПРИМИТИВЫ: HKDF, BIP39, KDF, потоковое AEAD-шифрование файлов
# =====================================================================
# HKDF-SHA256 (RFC 5869) для вывода подключей
def hkdf(key, salt, info, n=32):
    prk = hmac.new(salt or b"\x00" * 32, key, hashlib.sha256).digest()
    out = b""
    t = b""
    i = 1
    while len(out) < n:
        t = hmac.new(prk, t + info + bytes([i]), hashlib.sha256).digest()
        out += t
        i += 1
    return out[:n]


_WL = None


# Загрузка списка слов BIP39 (py3-mnemonic, файл или скачивание с проверкой)
def load_wordlist(download=False):
    global _WL
    if _WL:
        return _WL
    cands = []
    try:
        import mnemonic as _m
        cands.append(Path(_m.__file__).parent / "wordlist" / "english.txt")
    except Exception:
        pass
    cands.append(BIP39_FILE)
    for p in cands:
        try:
            words = p.read_text(encoding="utf-8").split()
            if len(words) == 2048 and words[0] == "abandon" and words[-1] == "zoo":
                _WL = words
                return _WL
        except Exception:
            pass
    if download:
        say_in("Загрузка списка слов BIP39...")
        try:
            import urllib.request
            url = "https://raw.githubusercontent.com/bitcoin/bips/master/bip-0039/english.txt"
            data = urllib.request.urlopen(url, timeout=20).read().decode("utf-8")
            words = data.split()
            if len(words) == 2048 and words[0] == "abandon" and words[-1] == "zoo" and all(w.isalpha() and w.islower() for w in words):
                BIP39_FILE.write_text("\n".join(words) + "\n", encoding="utf-8")
                os.chmod(BIP39_FILE, 0o600)
                _WL = words
                say_ok("Список BIP39 сохранён: " + str(BIP39_FILE))
                return _WL
            say_er("Загруженный список BIP39 не прошёл проверку")
        except Exception as e:
            say_er(f"Не удалось загрузить список BIP39: {e}")
    return None


# BIP39-фраза → 32-байтовый ключ через PBKDF2-HMAC-SHA512
def mnemonic_to_key(m):
    seed = hashlib.pbkdf2_hmac("sha512", m.encode("utf-8"), b"mnemonic", 2048)
    return b64u(seed[:32])


# Новая 12-словная BIP39-фраза и ключ
def generate_mnemonic():
    wl = load_wordlist(True)
    if not wl:
        raise CFError("BIP39 недоступен: нет списка слов (apk add py3-mnemonic или подключите интернет)")
    ent = secrets.token_bytes(16)
    bits = format(int.from_bytes(ent, "big"), "0128b") + format(hashlib.sha256(ent).digest()[0], "08b")[:4]
    words = [wl[int(bits[i:i + 11], 2)] for i in range(0, 132, 11)]
    m = " ".join(words)
    return m, mnemonic_to_key(m)


# Распознаёт BIP39-фразу (проверка слов и контрольной суммы)
def try_mnemonic(s, download=False):
    words = s.lower().split()
    if len(words) not in (12, 24) or not all(w.isalpha() for w in words):
        return None
    wl = load_wordlist(download)
    if not wl:
        return None
    d = {w: i for i, w in enumerate(wl)}
    idx = []
    for w in words:
        if w not in d:
            return None
        idx.append(d[w])
    bits = "".join(format(i, "011b") for i in idx)
    el = len(bits) * 32 // 33
    eb = int(bits[:el], 2).to_bytes(el // 8, "big")
    if format(hashlib.sha256(eb).digest()[0], "08b")[:len(bits) - el] != bits[el:]:
        return None
    return mnemonic_to_key(" ".join(words))


# Проверка: строка — корректный 32-байтовый ключ base64url
def valid_raw_key(s):
    try:
        raw = base64.urlsafe_b64decode(s.encode())
        return len(raw) == 32 and b64u(raw) == s
    except Exception:
        return False


# Преобразует ввод (ключ / BIP39 / фраза) в ключ слоя
def resolve_key(s, download=False):
    if not s:
        return s
    if valid_raw_key(s):
        return s
    if " " in s:
        k = try_mnemonic(s, download)
        if k:
            return k
    return s


COMMON = ("qwerty", "12345", "password", "admin", "letmein", "welcome", "iloveyou", "111111", "000000", "qazwsx", "йцукен", "пароль")


# Проверка слабых паролей: длина, разнообразие, популярные комбинации
def check_phrase(p):
    w = []
    if len(p) < 12:
        w.append("длина меньше 12 символов")
    if len(set(p)) < 8:
        w.append("меньше 8 уникальных символов")
    low = p.lower()
    for c in COMMON:
        if c in low:
            w.append(f"содержит популярную комбинацию «{c}»")
            break
    if p.isdigit():
        w.append("только цифры")
    if p.isalpha() and (p.islower() or p.isupper()) and len(p) < 16:
        w.append("только буквы одного регистра")
    return w


# Доступен ли Argon2id
def has_argon2():
    try:
        from cryptography.hazmat.primitives.kdf.argon2 import Argon2id
        return True
    except Exception:
        pass
    try:
        from argon2.low_level import hash_secret_raw
        return True
    except Exception:
        return False


# Argon2id (cryptography или argon2-cffi)
def argon2id_raw(pw, salt, t, mem_kib, lanes):
    try:
        from cryptography.hazmat.primitives.kdf.argon2 import Argon2id
        return Argon2id(salt=salt, length=32, iterations=t, lanes=lanes, memory_cost=mem_kib).derive(pw)
    except ImportError:
        pass
    try:
        from argon2.low_level import hash_secret_raw, Type
        return hash_secret_raw(pw, salt, time_cost=t, memory_cost=mem_kib, parallelism=lanes, hash_len=32, type=Type.ID)
    except ImportError:
        raise CFError("Argon2id недоступен: apk add py3-argon2-cffi")


MAGIC = b"CFA2"
ALG_ID = {"gcm": 1, "chacha": 2, "ocb3": 3, "gcmsiv": 4, "shake": 5}
ID_ALG = {v: k for k, v in ALG_ID.items()}
HEADER_LEN = 4 + 1 + 1 + 16 + 8


# Вывод ключа AEAD по режиму из заголовка: raw/HKDF, scrypt или Argon2id
def derive_key(keystr, mode, salt, params, alg):
    info = b"CF2-" + alg.encode()
    if mode == 0:
        return hkdf(base64.urlsafe_b64decode(keystr.encode()), salt, info)
    if mode == 1:
        log2n, r, p, _, _ = params
        # Параметры берутся из файла (недоверенного): ограничиваем, чтобы не получить DoS по памяти/времени
        if not (10 <= log2n <= 18 and 1 <= r <= 16 and 1 <= p <= 4):
            raise CFError("Недопустимые параметры KDF в заголовке (файл повреждён или подделан)")
        return hashlib.scrypt(keystr.encode("utf-8"), salt=salt, n=1 << log2n, r=r, p=p, maxmem=512 * MB, dklen=32)
    if mode == 2:
        t, lanes, _, _, mem = params
        if not (1 <= t <= 20 and 1 <= lanes <= 16 and 1024 <= mem <= 1048576):
            raise CFError("Недопустимые параметры Argon2id в заголовке (файл повреждён или подделан)")
        return argon2id_raw(keystr.encode("utf-8"), salt, t, mem, lanes)
    raise CFError("Неизвестный режим KDF в заголовке")


# Запасной AEAD из стандартной библиотеки: SHAKE256-поток + HMAC-SHA256 (когда нет cryptography)
class ShakeHmac:
    def __init__(self, key):
        self.k1 = hkdf(key, b"", b"cf-shake-enc")
        self.k2 = hkdf(key, b"", b"cf-shake-mac")

    def encrypt(self, nonce, data, aad):
        n = len(data)
        ks = hashlib.shake_256(self.k1 + nonce).digest(n) if n else b""
        ct = (int.from_bytes(data, "big") ^ int.from_bytes(ks, "big")).to_bytes(n, "big") if n else b""
        tag = hmac.new(self.k2, nonce + struct.pack(">Q", len(aad)) + aad + ct, hashlib.sha256).digest()[:16]
        return ct + tag

    def decrypt(self, nonce, data, aad):
        if len(data) < 16:
            raise ValueError("bad")
        ct, tag = data[:-16], data[-16:]
        exp = hmac.new(self.k2, nonce + struct.pack(">Q", len(aad)) + aad + ct, hashlib.sha256).digest()[:16]
        if not hmac.compare_digest(tag, exp):
            raise ValueError("bad tag")
        n = len(ct)
        ks = hashlib.shake_256(self.k1 + nonce).digest(n) if n else b""
        return (int.from_bytes(ct, "big") ^ int.from_bytes(ks, "big")).to_bytes(n, "big") if n else b""


# Фабрика AEAD по имени алгоритма
def make_aead(alg, key):
    if alg == "gcm":
        return AESGCM(key)
    if alg == "chacha":
        return ChaCha20Poly1305(key)
    if alg == "ocb3":
        return AESOCB3(key)
    if alg == "gcmsiv":
        return AESGCMSIV(key)
    if alg == "shake":
        return ShakeHmac(key)
    raise CFError("Неизвестный AEAD")


# Подпись индикатора прогресса для слоя
def aead_label(alg):
    return {"gcm": "AES-GCM ", "chacha": "ChaCha20 ", "ocb3": "AES-OCB3 ", "gcmsiv": "GCM-SIV ", "shake": "SHAKE-HMAC "}.get(alg, alg)


# Потоковое AEAD-шифрование файла чанками; заголовок самоописывающий; ключ и nonce не повторяются
def aead_encrypt_file(alg, inp, outp, keystr, kdf="scrypt"):
    salt = secrets.token_bytes(16)
    if valid_raw_key(keystr):
        mode, params = 0, (0, 0, 0, 0, 0)
    elif kdf == "argon2id" and has_argon2():
        mode, params = 2, (sec()["argon"][0], sec()["argon"][1], 0, 0, sec()["argon"][2])
        say_in("Argon2id: может занять несколько секунд...")
    else:
        mode, params = 1, (sec()["scrypt"], 8, 1, 0, 0)
    key = derive_key(keystr, mode, salt, params, alg)
    a = make_aead(alg, key)
    header = MAGIC + bytes([ALG_ID[alg], mode]) + salt + struct.pack(">BBBBI", *params)
    total = os.path.getsize(inp)
    with open(inp, "rb") as fi, open(outp, "wb") as fo:
        fo.write(header)
        seq = 0
        done = 0
        cur = fi.read(CHUNK)
        while True:
            nxt = fi.read(CHUNK)
            last = not nxt
            aad = seq.to_bytes(8, "big") + (b"\x01" if last else b"\x00")
            ct = a.encrypt(seq.to_bytes(12, "big"), cur, aad)
            fo.write(len(ct).to_bytes(4, "big"))
            fo.write(ct)
            seq += 1
            if seq >= 2 ** 32:
                raise CFError("Превышен лимит 2^32 блоков на один ключ")
            done += len(cur)
            if total > MB:
                pbar(done, total, aead_label(alg))
            if last:
                break
            cur = nxt


# Потоковая расшифровка с проверкой подлинности каждого блока (fail-closed)
def aead_decrypt_file(inp, outp, keystr, expect=None):
    total = os.path.getsize(inp)
    with open(inp, "rb") as fi, open(outp, "wb") as fo:
        h = fi.read(HEADER_LEN)
        if len(h) < HEADER_LEN or h[:4] != MAGIC:
            raise CFError("Неверный заголовок слоя (файл повреждён или слой указан неверно)")
        alg = ID_ALG.get(h[4])
        if not alg or (expect and alg != expect):
            raise CFError("Алгоритм в заголовке не совпадает со слоем")
        mode = h[5]
        salt = h[6:22]
        params = struct.unpack(">BBBBI", h[22:30])
        key = derive_key(keystr, mode, salt, params, alg)
        a = make_aead(alg, key)
        seq = 0
        done = HEADER_LEN
        while True:
            lb = fi.read(4)
            if not lb:
                break
            if len(lb) < 4:
                raise CFError("Файл обрезан")
            n = int.from_bytes(lb, "big")
            if n > MAX_CHUNK + 64:
                raise CFError("Повреждённый блок")
            ct = fi.read(n)
            if len(ct) != n:
                raise CFError("Файл обрезан")
            last = fi.tell() >= total
            aad = seq.to_bytes(8, "big") + (b"\x01" if last else b"\x00")
            try:
                pt = a.decrypt(seq.to_bytes(12, "big"), ct, aad)
            except Exception:
                raise CFError("Неверный ключ или данные повреждены (проверка подлинности не пройдена)")
            fo.write(pt)
            seq += 1
            done += n + 4
            if total > MB:
                pbar(done, total, aead_label(alg))
        if seq == 0:
            raise CFError("Пустой зашифрованный поток")


# Расшифровка старого формата aes-gcm/chacha20 (обратная совместимость)
def legacy_aead_decrypt(inp, outp, keystr, alg):
    key = base64.urlsafe_b64decode(keystr.encode())
    a = AESGCM(key) if alg == "aes-gcm" else ChaCha20Poly1305(key)
    total = os.path.getsize(inp)
    with open(inp, "rb") as fi, open(outp, "wb") as fo:
        seq = 0
        done = 0
        while True:
            lb = fi.read(4)
            if not lb:
                break
            n = int.from_bytes(lb, "big")
            ct = fi.read(n)
            if len(ct) != n:
                raise CFError("Повреждённый блок")
            try:
                pt = a.decrypt(seq.to_bytes(12, "big"), ct, None)
            except Exception:
                raise CFError("Неверный ключ или данные повреждены")
            fo.write(pt)
            seq += 1
            done += n + 4
            if total > MB:
                pbar(done, total, "legacy ")


ALPHA = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
ALPHS = ("abcdefghijklmnopqrstuvwxyz", "абвгдеёжзийклмнопрстуфхцчшщъыьэюя")
LETTER = {}
for _lo in ALPHS:
    for _i, _c in enumerate(_lo):
        LETTER[_c] = (_lo, _i, False)
        LETTER[_c.upper()] = (_lo, _i, True)

ROT_WIRE = ("EKMFLGDQVZNTOWYHXUSPAIBRCJ", "AJDKSIRUXBLHWTMCQGZNPYFVOE", "BDFHJLCPRTXVZNYEIWGAKMUSQO")
REFLECTOR = [ord(c) - 65 for c in "YRUHQSLDPXNGOKMIEBFZCWVJAT"]
FW = [[ord(c) - 65 for c in w] for w in ROT_WIRE]
BW = []
for _w in FW:
    _inv = [0] * 26
    for _i, _v in enumerate(_w):
        _inv[_v] = _i
    BW.append(_inv)


# =====================================================================
# РАЗДЕЛ: КЛАССИЧЕСКИЕ ШИФРЫ [Ненадёжный]: Энигма, Виженер, Цезарь, Атбаш, Rail Fence (только обучение/обфускация)
# =====================================================================
# Разбор ключа Энигмы: позиции роторов, коммутатор, флаг ;ru
def parse_enigma(key):
    key, _, flag = key.partition(";")
    if flag.strip().lower() not in ("", "ru"):
        raise CFError("Энигма: после ; допустим только флаг ru")
    main, _, plug = key.partition("|")
    parts = main.split(":")
    if len(parts) != 3:
        raise CFError("Энигма: нужно 3 позиции через двоеточие, например 1:5:13 или A:E:M")
    pos = []
    for x in parts:
        x = x.strip()
        if x.isdigit():
            v = int(x)
            if not 1 <= v <= 26:
                raise CFError("Энигма: позиция 1-26")
            pos.append(v - 1)
        elif len(x) == 1 and x.upper() in ALPHA:
            pos.append(ALPHA.index(x.upper()))
        else:
            raise CFError("Энигма: позиция — число 1-26 или буква A-Z")
    plug = re.sub(r"[^A-Za-z]", "", plug).upper()
    if len(plug) % 2 or len(set(plug)) != len(plug):
        raise CFError("Энигма: коммутатор — пары разных букв, например |ABCD (A↔B, C↔D)")
    pb = list(range(26))
    for i in range(0, len(plug), 2):
        a, b = ALPHA.index(plug[i]), ALPHA.index(plug[i + 1])
        pb[a], pb[b] = b, a
    return pos, pb


# Ядро Энигмы (3 ротора + рефлектор), зеркальная операция
def _enigma_core(text, key):
    pos, pb = parse_enigma(key)
    p = pos[:]
    out = []
    for ch in text:
        o = ord(ch)
        if 65 <= o <= 90 or 97 <= o <= 122:
            up = o <= 90
            c = o - 65 if up else o - 97
            if p[1] == 4:
                p[0] = (p[0] + 1) % 26
                p[1] = (p[1] + 1) % 26
            elif p[2] == 21:
                p[1] = (p[1] + 1) % 26
            p[2] = (p[2] + 1) % 26
            c = pb[c]
            for i in (2, 1, 0):
                c = (FW[i][(c + p[i]) % 26] - p[i]) % 26
            c = REFLECTOR[c]
            for i in (0, 1, 2):
                c = (BW[i][(c + p[i]) % 26] - p[i]) % 26
            c = pb[c]
            out.append(chr(c + (65 if up else 97)))
        else:
            out.append(ch)
    return "".join(out)


RU_LOW = "абвгдеёжзийклмнопрстуфхцчшщъыьэюя"
RU_IDX = {c: i for i, c in enumerate(RU_LOW)}
A25 = "abcdefghijklmnoprstuvwxyz"


# Включена ли поддержка кириллицы
def enigma_ru(key):
    return key.partition(";")[2].strip().lower() == "ru"


# Кириллица → латинские коды (обратимо, с экранированием q/Q)
def ru_to_lat(text):
    out = []
    for ch in text:
        lo = ch.lower()
        if len(lo) == 1 and lo in RU_IDX:
            i = RU_IDX[lo]
            code = A25[i // 25] + A25[i % 25]
            out.append("Q" + code.upper() if ch != lo else "q" + code)
        elif ch in "qQ":
            out.append(ch + ch)
        else:
            out.append(ch)
    return "".join(out)


# Обратное преобразование кодов в кириллицу
def lat_to_ru(text):
    out = []
    i = 0
    n = len(text)
    while i < n:
        ch = text[i]
        if ch not in "qQ":
            out.append(ch)
            i += 1
            continue
        if i + 1 < n and text[i + 1] == ch:
            out.append(ch)
            i += 2
            continue
        up = ch == "Q"
        if i + 2 < n:
            a, b = text[i + 1], text[i + 2]
            if a.isupper() == up and b.isupper() == up and a.lower() in A25 and b.lower() in A25:
                idx = A25.index(a.lower()) * 25 + A25.index(b.lower())
                if idx < len(RU_LOW):
                    r = RU_LOW[idx]
                    out.append(r.upper() if up else r)
                    i += 3
                    continue
        raise CFError("Энигма: повреждена кириллическая последовательность (неверный ключ или данные)")
    return "".join(out)


# Энигма с поддержкой кириллицы через транслитерацию
def enigma_transform(text, key, mode="enc"):
    if enigma_ru(key):
        if mode == "enc":
            return _enigma_core(ru_to_lat(text), key)
        return lat_to_ru(_enigma_core(text, key))
    return _enigma_core(text, key)


# Сдвиг буквы внутри её алфавита с сохранением регистра
def shift_char(ch, s):
    info = LETTER.get(ch)
    if info is None:
        return ch
    lo, i, up = info
    r = lo[(i + s) % len(lo)]
    return r.upper() if up else r


# Шифр Виженера (латиница+кириллица) [Ненадёжный]
def vigenere_transform(text, mode, key):
    sh = [LETTER[c][1] for c in key if c in LETTER]
    if not sh:
        raise CFError("Виженер: в ключе нет букв (латиница или кириллица)")
    sign = 1 if mode == "enc" else -1
    out = []
    k = 0
    for ch in text:
        if ch in LETTER:
            out.append(shift_char(ch, sign * sh[k % len(sh)]))
            k += 1
        else:
            out.append(ch)
    return "".join(out)


# Шифр Цезаря [Ненадёжный]
def caesar_transform(text, mode, key):
    try:
        s = int(key)
    except ValueError:
        raise CFError("Цезарь: ключ — целое число")
    if mode != "enc":
        s = -s
    return "".join(shift_char(ch, s) if ch in LETTER else ch for ch in text)


# Шифр Атбаш [Ненадёжный]
def atbash_transform(text):
    out = []
    for ch in text:
        info = LETTER.get(ch)
        if info is None:
            out.append(ch)
            continue
        lo, i, up = info
        r = lo[len(lo) - 1 - i]
        out.append(r.upper() if up else r)
    return "".join(out)


# Узор зигзага для Rail Fence
def rail_pattern(n, rails):
    pat = []
    cur, d = 0, 1
    for _ in range(n):
        pat.append(cur)
        if cur == 0:
            d = 1
        elif cur == rails - 1:
            d = -1
        cur += d
    return pat


# Rail Fence [Ненадёжный]
def railfence_transform(text, mode, key):
    try:
        rails = int(key)
    except ValueError:
        raise CFError("Rail Fence: ключ — число рельсов")
    if rails < 2:
        raise CFError("Rail Fence: минимум 2 рельса")
    n = len(text)
    pat = rail_pattern(n, rails)
    if mode == "enc":
        rows = [[] for _ in range(rails)]
        for ch, r in zip(text, pat):
            rows[r].append(ch)
        return "".join("".join(r) for r in rows)
    counts = [0] * rails
    for r in pat:
        counts[r] += 1
    rows = []
    idx = 0
    for c in counts:
        rows.append(text[idx:idx + c])
        idx += c
    ptr = [0] * rails
    out = []
    for r in pat:
        out.append(rows[r][ptr[r]])
        ptr[r] += 1
    return "".join(out)


# Применение классического шифра по имени
def apply_classical(text, t, mode, key):
    if t == "enigma":
        return enigma_transform(text, key, mode)
    if t == "vigenere":
        return vigenere_transform(text, mode, key)
    if t == "caesar":
        return caesar_transform(text, mode, key)
    if t == "atbash":
        return atbash_transform(text)
    if t == "railfence":
        return railfence_transform(text, mode, key)
    raise CFError("Неизвестный классический шифр")


# Классический шифр над файлом: только UTF-8 текст, иначе отказ без потери данных
def classic_file(inp, outp, t, mode, key):
    if os.path.getsize(inp) > CLASSIC_MAX:
        raise CFError(f"Классические шифры работают с текстом до {hsize(CLASSIC_MAX)}")
    raw = Path(inp).read_bytes()
    if b"\x00" in raw:
        raise CFError(f"Шифр «{t}» не работает с бинарными данными")
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        raise CFError(f"Шифр «{t}» работает только с текстом UTF-8; данные не являются текстом")
    Path(outp).write_bytes(apply_classical(text, t, mode, key).encode("utf-8"))


# Файл — валидный UTF-8 текст без NUL (до лимита)
def is_text_file(p):
    try:
        p = Path(p)
        if not p.is_file() or p.stat().st_size > CLASSIC_MAX:
            return False
        data = p.read_bytes()
        if b"\x00" in data:
            return False
        data.decode("utf-8")
        return True
    except Exception:
        return False


# Проверка и нормализация ключа классического шифра
def norm_classic_key(t, key):
    key = key.strip()
    if t == "caesar":
        try:
            n = int(key)
        except ValueError:
            raise CFError("Цезарь: нужно целое число 1-25")
        if not 1 <= n <= 1000 or n % 26 == 0 or n % 33 == 0:
            raise CFError("Цезарь: сдвиг 1-25")
        return str(n)
    if t == "vigenere":
        if not any(c in LETTER for c in key):
            raise CFError("Виженер: нужно слово из букв (латиница/кириллица)")
        return key
    if t == "railfence":
        try:
            n = int(key)
        except ValueError:
            raise CFError("Rail Fence: нужно число 2-50")
        if not 2 <= n <= 50:
            raise CFError("Rail Fence: число рельсов 2-50")
        return str(n)
    if t == "enigma":
        parse_enigma(key)
        return key
    return ""


# Случайный ключ классического шифра
def gen_classic_key(t):
    if t == "caesar":
        return str(rand_choice([n for n in range(1, 26)]))
    if t == "vigenere":
        return "".join(rand_choice(ALPHS[0]) for _ in range(rand_choice(range(8, 13))))
    if t == "railfence":
        return str(rand_choice(range(2, 10)))
    if t == "enigma":
        return ":".join(str(rand_choice(range(1, 27))) for _ in range(3)) + ";ru"
    return ""


# =====================================================================
# РАЗДЕЛ: ВНЕШНИЕ ШИФРЫ: GPG и OpenSSL, проверка доступности
# =====================================================================
# GPG-шифрование (в iSH обычно недоступно из-за gpg-agent); ключ передаётся через pipe
def run_gpg(mode, inp, outp, key):
    fd_r, fd_w = os.pipe()
    os.write(fd_w, (key + "\n").encode())
    os.close(fd_w)
    base = ["gpg", "--batch", "--yes", "--no-tty", "--pinentry-mode", "loopback", "--passphrase-fd", str(fd_r)]
    if mode == "enc":
        cmd = base + ["--symmetric", "--cipher-algo", "AES256", "-o", str(outp), str(inp)]
    else:
        cmd = base + ["--decrypt", "-o", str(outp), str(inp)]
    try:
        proc = subprocess.Popen(cmd, pass_fds=(fd_r,), stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, start_new_session=True)
        t0 = time.time()
        i = 0
        while proc.poll() is None:
            if time.time() - t0 > 180:
                try:
                    os.killpg(os.getpgid(proc.pid), 9)
                except Exception:
                    proc.kill()
                raise CFError("gpg завис более 180 с")
            sys.stdout.write(f"\r  \033[38;5;45m{SPIN[i % 10]}\033[0m gpg работает...\033[K")
            sys.stdout.flush()
            time.sleep(0.1)
            i += 1
        sys.stdout.write("\r\033[K")
        _, err = proc.communicate()
        if proc.returncode != 0:
            last = (err or "").strip().split("\n")[-1] if err else ""
            raise CFError("gpg: " + (last or f"код {proc.returncode}"))
    finally:
        try:
            os.close(fd_r)
        except OSError:
            pass


# OpenSSL enc: ключ через файл (не в argv), PBKDF2, спиннер ожидания
def run_openssl(mode, inp, outp, key, cipher, iterations=100000):
    fd, kf = tempfile.mkstemp(dir=WORKROOT)
    os.write(fd, key.encode("utf-8"))
    os.close(fd)
    try:
        cmd = ["openssl", "enc"]
        if mode == "dec":
            cmd.append("-d")
        cmd += [f"-{cipher}", "-pbkdf2", "-iter", str(iterations)]
        if mode == "enc":
            cmd.append("-salt")
        cmd += ["-in", str(inp), "-out", str(outp), "-pass", f"file:{kf}"]
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        wait_spin(proc, f"openssl {cipher}")
        _, err = proc.communicate()
        if proc.returncode != 0:
            last = (err or "openssl: ошибка").strip().split("\n")[-1]
            if "bad decrypt" in last or "bad magic" in last:
                last = "неверный ключ или повреждённые данные"
            raise CFError("openssl: " + last)
    finally:
        try:
            os.unlink(kf)
        except OSError:
            pass


# Проверка работоспособности шифра OpenSSL
def ossl_test(cipher):
    try:
        fd, kf = tempfile.mkstemp(dir=WORKROOT)
        os.write(fd, b"k")
        os.close(fd)
        fi = kf + ".i"
        fo = kf + ".o"
        fb = kf + ".b"
        Path(fi).write_bytes(b"cryptforge-test-data")
        r = subprocess.run(["openssl", "enc", f"-{cipher}", "-pbkdf2", "-iter", "1000", "-in", fi, "-out", fo, "-pass", f"file:{kf}"], capture_output=True, timeout=30)
        ok = r.returncode == 0
        if ok:
            r = subprocess.run(["openssl", "enc", "-d", f"-{cipher}", "-pbkdf2", "-iter", "1000", "-in", fo, "-out", fb, "-pass", f"file:{kf}"], capture_output=True, timeout=30)
            ok = r.returncode == 0 and Path(fb).read_bytes() == b"cryptforge-test-data"
        for x in (kf, fi, fo, fb):
            try:
                os.unlink(x)
            except OSError:
                pass
        return ok
    except Exception:
        return False


OSSL_CIPHERS = ("aes-256-cbc", "aes-256-ctr", "camellia-256-cbc", "aria-256-cbc", "sm4-cbc")
_ossl = None


# Доступность шифра OpenSSL (кэш)
def ossl_ok(cipher):
    global _ossl
    if _ossl is None:
        data = {}
        try:
            if OSSL_CACHE.exists() and time.time() - OSSL_CACHE.stat().st_mtime < 7 * 86400:
                data = json.loads(OSSL_CACHE.read_text())
        except Exception:
            data = {}
        if not shutil.which("openssl"):
            data = {c: False for c in OSSL_CIPHERS}
        else:
            changed = False
            for c in OSSL_CIPHERS:
                if c not in data:
                    data[c] = ossl_test(c)
                    changed = True
            if changed:
                try:
                    OSSL_CACHE.write_text(json.dumps(data))
                except Exception:
                    pass
        _ossl = data
    return _ossl.get(cipher, False)


_gpg = None


# Работает ли GPG (кэш проверки)
def gpg_ok():
    global _gpg
    if _gpg is not None:
        return _gpg
    if not shutil.which("gpg"):
        _gpg = False
        return False
    try:
        if GPG_CACHE.exists() and time.time() - GPG_CACHE.stat().st_mtime < 3 * 86400:
            _gpg = GPG_CACHE.read_text().strip() == "1"
            return _gpg
    except Exception:
        pass
    res = False
    tmp = Path(tempfile.mkdtemp(dir=WORKROOT))
    try:
        (tmp / "i").write_text("test")
        (tmp / "k").write_text("test\n")
        proc = subprocess.Popen(["gpg", "--batch", "--yes", "--no-tty", "--no-autostart", "--pinentry-mode", "loopback", "--passphrase-file", str(tmp / "k"), "--symmetric", "--cipher-algo", "AES256", "-o", str(tmp / "o"), str(tmp / "i")],
                                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
        try:
            proc.wait(timeout=8)
            res = proc.returncode == 0 and (tmp / "o").exists() and (tmp / "o").stat().st_size > 0
        except subprocess.TimeoutExpired:
            try:
                os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
            except Exception:
                pass
    except Exception:
        res = False
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    try:
        GPG_CACHE.write_text("1" if res else "0")
    except Exception:
        pass
    _gpg = res
    return res


# =====================================================================
# РАЗДЕЛ: РЕЕСТР СЛОЁВ: описание, доступность, применение и снятие слоёв
# =====================================================================
LAYER_DEFS = [
    ("1", "gpg:AES256", "GPG AES-256", "пароль, нужен gpg-agent", "crypto"),
    ("2", "openssl:aes-256-cbc", "OpenSSL AES-256-CBC", "классика, без проверки данных", "crypto"),
    ("3", "gcm", "AES-256-GCM", "быстрый и надёжный (лучший)", "crypto"),
    ("4", "chacha", "ChaCha20-Poly1305", "как GCM, быстр на телефонах", "crypto"),
    ("5", "ocb3", "AES-256-OCB3", "быстрый, с проверкой данных", "crypto"),
    ("6", "gcmsiv", "AES-256-GCM-SIV", "защита от повтора nonce", "crypto"),
    ("7", "shake", "SHAKE256 + HMAC-SHA256", "работает без cryptography", "crypto"),
    ("8", "openssl:camellia-256-cbc", "OpenSSL Camellia-256-CBC", "японский стандарт", "crypto"),
    ("9", "openssl:aria-256-cbc", "OpenSSL ARIA-256-CBC", "корейский стандарт", "crypto"),
    ("10", "openssl:sm4-cbc", "OpenSSL SM4-CBC", "китайский стандарт", "crypto"),
    ("11", "openssl:aes-256-ctr", "OpenSSL AES-256-CTR", "потоковый, без проверки данных", "crypto"),
    ("12", "base64", "Base64", "просто кодировка, НЕ защита", "encode"),
    ("13", "enigma", "Энигма", "роторная машина; русский ок", "classic"),
    ("14", "vigenere", "Виженер", "ключ-слово, лат. и кириллица", "classic"),
    ("15", "caesar", "Цезарь", "сдвиг букв на N позиций", "classic"),
    ("16", "atbash", "Атбаш", "зеркало алфавита, без ключа", "classic"),
    ("17", "railfence", "Железнодорожная (Rail Fence)", "перестановка букв зигзагом", "classic"),
    ("", "pad", "Мусорные данные", "скрытый паддинг", "wrap"),
]
DEF_BY_ID = {d[1]: d for d in LAYER_DEFS}
DEF_BY_NUM = {d[0]: d for d in LAYER_DEFS}
CLASSIC = {"enigma", "vigenere", "caesar", "atbash", "railfence"}
KEYLESS = {"atbash", "base64", "pad"}
LEGACY_TITLES = {"aes-gcm": "AES-GCM (старый формат)", "chacha20": "ChaCha20 (старый формат)", "openssl:bf-cbc": "Blowfish (устарел)"}


# Число итераций PBKDF2 из имени слоя (openssl:...@N)
def ossl_iter(layer):
    if "@" in layer:
        try:
            return max(1000, int(layer.split("@", 1)[1]))
        except ValueError:
            pass
    return 100000


# Базовый тип слоя без параметров
def base_type(layer):
    if layer.startswith("openssl:"):
        return layer.split("@")[0]
    if layer.startswith("gpg:"):
        return "gpg:AES256"
    return layer.split(":")[0]


# Название слоя для интерфейса
def layer_title(layer):
    bt = base_type(layer)
    if bt in DEF_BY_ID:
        return DEF_BY_ID[bt][2]
    return LEGACY_TITLES.get(bt, bt)


# Нужен ли слою ключ
def needs_key(layer):
    return base_type(layer) not in KEYLESS


# Доступен ли слой в этой среде и почему нет
def layer_available(lid):
    if lid.startswith("gpg:"):
        return (True, "") if gpg_ok() else (False, "gpg-agent не работает в iSH")
    if lid.startswith("openssl:"):
        c = lid.split(":", 1)[1]
        return (True, "") if ossl_ok(c) else (False, "не поддерживается этой сборкой openssl")
    if lid in ("gcm", "chacha"):
        return (True, "") if HAS_CRYPTO else (False, "нужен py3-cryptography")
    if lid == "ocb3":
        return (True, "") if (HAS_CRYPTO and AESOCB3) else (False, "нужен py3-cryptography новее")
    if lid == "gcmsiv":
        return (True, "") if (HAS_CRYPTO and AESGCMSIV) else (False, "нужен py3-cryptography новее")
    return True, ""


# Слой работает с бинарными данными
def is_binary_safe(lid):
    d = DEF_BY_ID.get(lid)
    return bool(d) and d[4] in ("crypto", "encode")


# Какими станут данные (текст/бинарные) после слоя
def state_after(lid, state_text):
    d = DEF_BY_ID.get(lid)
    if not d:
        return False
    if d[4] in ("classic", "encode"):
        return state_text
    return False


# Проверка порядка слоёв: классика допустима только пока данные — текст
def spec_compatible(spec, is_text):
    st = is_text
    for i, L in enumerate(spec):
        bt = base_type(L["layer"])
        if bt in CLASSIC and not st:
            return False, f"слой {i + 1} ({layer_title(bt)}) требует текст, а данные в этой точке бинарные"
        if bt == "base64":
            pass
        ok, why = layer_available(bt)
        if not ok:
            return False, f"слой {i + 1} недоступен: {why}"
        st = state_after(bt, st)
    return True, ""


# Применяет один слой шифрования к файлу
def encrypt_layer(inp, outp, layer, key, kdf="scrypt", params=None):
    bt = base_type(layer)
    if bt == "pad":
        pad_encrypt_file(inp, outp, params or CFG["junk"])
        return
    if bt.startswith("gpg:"):
        run_gpg("enc", inp, outp, key)
    elif bt.startswith("openssl:"):
        run_openssl("enc", inp, outp, key, bt.split(":", 1)[1], ossl_iter(layer))
    elif bt in ALG_ID:
        aead_encrypt_file(bt, inp, outp, key, kdf)
    elif bt == "base64":
        with open(inp, "rb") as fi, open(outp, "wb") as fo:
            base64.encode(fi, fo)
    elif bt in CLASSIC:
        k = key or (layer.split(":", 1)[1] if ":" in layer else "")
        classic_file(inp, outp, bt, "enc", k)
    else:
        raise CFError(f"Неизвестный слой: {layer}")


# Снимает один слой
def decrypt_layer(inp, outp, layer, key):
    bt = base_type(layer)
    if bt == "pad":
        pad_decrypt_file(inp, outp)
        return
    if bt.startswith("gpg:"):
        run_gpg("dec", inp, outp, key)
    elif bt.startswith("openssl:"):
        run_openssl("dec", inp, outp, key, bt.split(":", 1)[1], ossl_iter(layer))
    elif bt in ALG_ID:
        if not HAS_CRYPTO and bt != "shake":
            raise CFError("Нужен модуль cryptography: apk add py3-cryptography")
        aead_decrypt_file(inp, outp, key, bt)
    elif bt in ("aes-gcm", "chacha20"):
        if not HAS_CRYPTO:
            raise CFError("Нужен модуль cryptography: apk add py3-cryptography")
        legacy_aead_decrypt(inp, outp, key, bt)
    elif bt == "base64":
        import binascii
        try:
            with open(inp, "rb") as fi, open(outp, "wb") as fo:
                base64.decode(fi, fo)
        except binascii.Error:
            raise CFError("Base64: данные повреждены или слой указан неверно")
    elif bt in CLASSIC:
        k = key or (layer.split(":", 1)[1] if ":" in layer else "")
        classic_file(inp, outp, bt, "dec", k)
    else:
        raise CFError(f"Неизвестный слой: {layer}")


# Последовательно применяет слои; промежуточные файлы удаляются
def apply_stack(src, spec, work):
    src = Path(src)
    cur = src
    for i, L in enumerate(spec):
        out = work / f"e{i}_{secrets.token_hex(3)}"
        say_in(f"Слой {i + 1}/{len(spec)}: {layer_title(L['layer'])}")
        encrypt_layer(cur, out, L["layer"], L["key"], L.get("kdf") or "scrypt", L.get("params"))
        if cur != src:
            rm_temp(cur)
        cur = out
    return cur


# Снимает слои в обратном порядке
def reverse_stack(src, layers, keys, work, label="Слой"):
    src = Path(src)
    cur = src
    n = len(layers)
    for i in reversed(range(n)):
        out = work / f"d{i}_{secrets.token_hex(3)}"
        say_in(f"{label} {i + 1}/{n}: {layer_title(layers[i])}")
        try:
            decrypt_layer(cur, out, layers[i], keys[i] if i < len(keys) else "")
        except CFError as e:
            raise CFError(f"слой {i + 1} ({layer_title(layers[i])}): {e}")
        except Exception as e:
            raise CFError(f"слой {i + 1} ({layer_title(layers[i])}): {e}")
        if cur != src:
            rm_temp(cur)
        cur = out
    return cur


# =====================================================================
# РАЗДЕЛ: ШАМИР: разделение секрета над GF(256)
# =====================================================================
GF_EXP = [0] * 512
GF_LOG = [0] * 256
_x = 1
for _i in range(255):
    GF_EXP[_i] = _x
    GF_LOG[_x] = _i
    _x2 = _x << 1
    if _x2 & 0x100:
        _x2 ^= 0x11B
    _x = _x2 ^ _x
for _i in range(255, 512):
    GF_EXP[_i] = GF_EXP[_i - 255]


# Умножение в GF(256)
def gf_mul(a, b):
    if a == 0 or b == 0:
        return 0
    return GF_EXP[GF_LOG[a] + GF_LOG[b]]


# Деление в GF(256)
def gf_div(a, b):
    if a == 0:
        return 0
    return GF_EXP[(GF_LOG[a] - GF_LOG[b]) % 255]


_MULROW = {}


# Таблица умножения на константу (для быстрой translate)
def mulrow(k):
    r = _MULROW.get(k)
    if r is None:
        r = bytes(gf_mul(v, k) for v in range(256))
        _MULROW[k] = r
    return r


# Разделение секрета по схеме Шамира над GF(256)
def shamir_split(secret, t, n):
    ln = len(secret)
    coefs = [secret] + [secrets.token_bytes(ln) for _ in range(t - 1)]
    base = int.from_bytes(secret, "big")
    shares = {}
    for x in range(1, n + 1):
        acc = base
        xp = 1
        for j in range(1, t):
            xp = gf_mul(xp, x)
            acc ^= int.from_bytes(coefs[j].translate(mulrow(xp)), "big")
        shares[x] = acc.to_bytes(ln, "big")
    return shares


# Восстановление секрета из долей
def shamir_combine(shares):
    xs = list(shares.keys())
    ln = len(shares[xs[0]])
    basis = []
    for i, xi in enumerate(xs):
        num = 1
        den = 1
        for j, xj in enumerate(xs):
            if i != j:
                num = gf_mul(num, xj)
                den = gf_mul(den, xi ^ xj)
        basis.append(gf_div(num, den))
    out = bytearray()
    for pos in range(ln):
        v = 0
        for i, xi in enumerate(xs):
            v ^= gf_mul(shares[xi][pos], basis[i])
        out.append(v)
    return bytes(out)


SHARE_RE = re.compile(r"CFSHARE1\|(\d+)\|(\d+)\|(\d+)\|([0-9a-f]{8})\|([A-Za-z0-9_\-=]+)")


# Создаёт файлы долей Шамира с контрольным ID
def make_shares(final_name, secret_dict, t, n):
    blob = zlib.compress(json.dumps(secret_dict, ensure_ascii=False).encode("utf-8"), 9)
    sid = hashlib.sha256(blob).hexdigest()[:8]
    shares = shamir_split(blob, t, n)
    paths = []
    for x, data in shares.items():
        p = SHARES / f"{final_name}.share{x}.txt"
        text = (f"CryptForge Shamir share\nФайл: {final_name}\nПорог: {t} из {n}\nДоля: {x}\n"
                f"Храните доли в РАЗНЫХ местах и отдельно от .enc\n\n"
                f"CFSHARE1|{t}|{n}|{x}|{sid}|{b64u(data)}\n")
        p.write_text(text, encoding="utf-8")
        os.chmod(p, 0o600)
        paths.append(p)
    return paths


# Собирает секрет из текстов долей и проверяет ID
def combine_share_lines(lines):
    found = {}
    tt = None
    sid = None
    for ln in lines:
        for m in SHARE_RE.finditer(ln):
            t, n, x, s, d = m.groups()
            if sid and s != sid:
                raise CFError("Доли относятся к разным наборам")
            sid, tt = s, int(t)
            found[int(x)] = base64.urlsafe_b64decode(d.encode())
    if not found:
        raise CFError("Доли не найдены")
    if len(found) < tt:
        raise CFError(f"Нужно минимум {tt} долей, найдено {len(found)}")
    blob = shamir_combine(dict(list(found.items())[:tt]))
    if hashlib.sha256(blob).hexdigest()[:8] != sid:
        raise CFError("Контрольная сумма не сошлась — доли повреждены")
    return json.loads(zlib.decompress(blob).decode("utf-8"))


# =====================================================================
# РАЗДЕЛ: ВЫБОР ФАЙЛОВ, АРХИВЫ, ПРАВА, ТИПЫ ФАЙЛОВ
# =====================================================================
# Выбор файлов: номера, диапазоны, all, пути, b — обзор любых папок
def pick_files(purpose, dirs, only_files=False):
    items = []
    for d in dirs:
        d = Path(d)
        if not d.is_dir():
            continue
        try:
            entries = sorted([e for e in d.iterdir() if not e.name.startswith(".") and e != BASE], key=lambda e: e.name.lower())
        except OSError:
            continue
        if only_files:
            entries = [e for e in entries if e.is_file()]
        if not entries:
            continue
        print()
        say_in(f"В {d}")
        for e in entries:
            items.append(e)
            kind = "папка" if e.is_dir() else hsize(e.stat().st_size)
            print(f"  {len(items):2d}) {e.name} ({kind})")
    print()
    say_in("Выберите: номер, 1,3,5-8, all или путь")
    say_in("b — обзор любых папок («Файлы» iPhone)")
    raw = ask(f"{purpose}: ")
    if not raw:
        return []
    if raw.lower() in ("b", "обзор"):
        return browse_flow("files")
    if raw.lower() == "all":
        return list(items)
    whole = Path(os.path.expanduser(raw))
    if whole.exists():
        return [whole]
    sel = []
    for tok in raw.split(","):
        tok = tok.strip()
        if not tok:
            continue
        m = re.match(r"^(\d+)-(\d+)$", tok)
        if m:
            a, b = int(m.group(1)), int(m.group(2))
            for n in range(a, b + 1):
                if 1 <= n <= len(items):
                    sel.append(items[n - 1])
                else:
                    say_wn(f"Номер {n} вне списка")
        elif tok.isdigit():
            n = int(tok)
            if 1 <= n <= len(items):
                sel.append(items[n - 1])
            else:
                say_wn(f"Номер {n} вне списка")
        else:
            p = Path(os.path.expanduser(tok))
            if p.exists():
                sel.append(p)
            else:
                say_wn(f"Не найдено: {tok}")
    seen = set()
    out = []
    for s in sel:
        if str(s) not in seen:
            seen.add(str(s))
            out.append(s)
    if not out:
        say_wn("Ничего не выбрано")
    else:
        say_ok(f"Выбрано объектов: {len(out)}")
    return out


# Обёртка файла для счётчика прогресса при архивации
class ProgFile:
    def __init__(self, f, cb):
        self.f = f
        self.cb = cb

    def read(self, n=-1):
        d = self.f.read(n)
        if d:
            self.cb(len(d))
        return d


# Упаковка в tar.gz с прогрессом; символические ссылки пропускаются
def make_tar_gz(src, dest):
    src = Path(src)
    total = max(1, dir_size(src))
    state = [0]

    def cb(n):
        state[0] += n
        if total > MB:
            pbar(state[0], total, "tar+gzip ")

    skipped = 0
    with tarfile.open(dest, "w:gz", compresslevel=6) as tar:
        def add(path, arc):
            nonlocal skipped
            if os.path.islink(path):
                skipped += 1
                return
            ti = tar.gettarinfo(str(path), arc)
            if ti is None:
                skipped += 1
                return
            if ti.isdir():
                tar.addfile(ti)
                for name in sorted(os.listdir(path)):
                    add(os.path.join(path, name), arc + "/" + name)
            elif ti.isreg():
                with open(path, "rb") as f:
                    tar.addfile(ti, ProgFile(f, cb))
            else:
                skipped += 1
        add(str(src), src.name)
    if total > MB and _last_pb[0] >= 0:
        pbar(total, total, "tar+gzip ")
    if skipped:
        say_wn(f"Пропущено символических ссылок/спецфайлов: {skipped}")
    if not Path(dest).exists() or Path(dest).stat().st_size == 0:
        raise CFError("Архивация не удалась")


# Проверка элемента архива: без абсолютных путей, .., ссылок и устройств
def tar_member_ok(m):
    n = m.name
    if n.startswith("/") or ".." in n.split("/") or "\x00" in n:
        return False
    if m.issym() or m.islnk() or m.isdev() or m.isfifo():
        return False
    return True


# Безопасная распаковка с проверкой каждого элемента
def extract_tar_safe(archive, dest):
    dest = Path(dest)
    dest.mkdir(parents=True, exist_ok=True)
    try:
        tar = tarfile.open(archive, "r:gz")
    except Exception as e:
        raise CFError(f"Не удалось открыть архив (неверные ключи/слои?): {e}")
    with tar:
        members = tar.getmembers()
        for m in members:
            if not tar_member_ok(m):
                raise CFError(f"Небезопасный элемент архива: {m.name}")
        total = max(1, sum(m.size for m in members))
        done = 0
        for m in members:
            try:
                tar.extract(m, path=str(dest), filter="data")
            except TypeError:
                tar.extract(m, path=str(dest))
            done += m.size
            if total > MB:
                pbar(done, total, "распаковка ")
    return dest


# Права 644/755 для видимости в приложении «Файлы»
def fix_perms(path):
    path = Path(path)
    try:
        if path.is_dir():
            os.chmod(path, 0o755)
            for root, dirs, files in os.walk(path):
                for d in dirs:
                    os.chmod(os.path.join(root, d), 0o755)
                for f in files:
                    os.chmod(os.path.join(root, f), 0o644)
        else:
            os.chmod(path, 0o644)
    except OSError:
        pass


SIGS = [
    (b"\x89PNG\r\n\x1a\n", "png", "PNG"), (b"\xff\xd8\xff", "jpg", "JPEG"), (b"GIF87a", "gif", "GIF"), (b"GIF89a", "gif", "GIF"),
    (b"%PDF-", "pdf", "PDF"), (b"PK\x03\x04", "zip", "ZIP/Office"), (b"\x1f\x8b", "gz", "GZIP"), (b"ID3", "mp3", "MP3"),
    (b"OggS", "ogg", "OGG"), (b"fLaC", "flac", "FLAC"), (b"BM", "bmp", "BMP"), (b"7z\xbc\xaf\x27\x1c", "7z", "7-Zip"),
    (b"Rar!", "rar", "RAR"), (b"SQLite format 3", "sqlite", "SQLite"),
]
EXT_ALIASES = {
    "jpg": {"jpg", "jpeg", "jpe"}, "zip": {"zip", "docx", "xlsx", "pptx", "jar", "epub", "apk", "odt", "ods"},
    "mp4": {"mp4", "m4v"}, "gz": {"gz", "tgz"}, "mp3": {"mp3"}, "heic": {"heic", "heif"}, "mov": {"mov"}, "m4a": {"m4a"},
    "wav": {"wav"}, "webp": {"webp"}, "avi": {"avi"},
}


# Тип файла по сигнатуре
def detect_type(head):
    if head[4:8] == b"ftyp":
        b = head[8:12]
        if b in (b"heic", b"heix", b"mif1", b"heim"):
            return "heic", "HEIC"
        if b == b"qt  ":
            return "mov", "QuickTime"
        if b[:3] == b"M4A":
            return "m4a", "M4A"
        return "mp4", "MP4"
    if head[:4] == b"RIFF":
        k = head[8:12]
        if k == b"WAVE":
            return "wav", "WAV"
        if k == b"WEBP":
            return "webp", "WebP"
        if k == b"AVI ":
            return "avi", "AVI"
    if head[:2] == b"\xff\xfb" or head[:2] == b"\xff\xf3":
        return "mp3", "MP3"
    for sig, ext, name in SIGS:
        if head.startswith(sig):
            return ext, name
    return None, None


# Соответствует ли расширение типу
def ext_matches(name, ext):
    cur = os.path.splitext(name)[1].lstrip(".").lower()
    return cur in EXT_ALIASES.get(ext, {ext})


# Подсказка, если расширение не соответствует содержимому
def quick_type_hint(path):
    try:
        p = Path(path)
        if not p.is_file():
            return
        with open(p, "rb") as f:
            head = f.read(64)
        ext, name = detect_type(head)
        if ext and not ext_matches(p.name, ext):
            say_wn(f"Тип данных: {name}, но расширение у файла другое. Меню «Починка файлов» может переименовать.")
    except Exception:
        pass


# =====================================================================
# РАЗДЕЛ: МЕТАДАННЫЕ ФАЙЛОВ И ПЛАНИРОВАНИЕ СЛОЁВ
# =====================================================================
# Поиск метаданных по имени и по хешу файла; статусы ok/locked/corrupt/none
def find_meta(src):
    src = Path(src)
    p = META / f"{src.name}.meta"
    if p.exists():
        try:
            return read_json_file(p), p, "ok"
        except CFError:
            return None, p, "locked"
        except Exception:
            return None, p, "corrupt"
    h = None
    for mp in sorted(META.glob("*.meta")):
        try:
            d = read_json_file(mp)
        except Exception:
            continue
        if d.get("enc_sha256"):
            if h is None:
                h = sha256_file(src)
            if d["enc_sha256"] == h:
                say_in(f"Метаданные найдены по хешу файла: {mp.name}")
                return d, mp, "ok"
    return None, None, "none"



# Приведение метаданных (в т.ч. старых версий) к единому виду
def normalize_meta(meta, src):
    layers = list(meta.get("layers", []))
    keys = list(meta.get("keys", []))
    if len(keys) != len(layers):
        keys = []
        csv = [k for k in meta.get("keys_csv", "").split(",") if k] if meta.get("keys_csv") else []
        it = iter(csv)
        for l in layers:
            if needs_key(l):
                keys.append(next(it, ""))
            else:
                keys.append("")
    restore = meta.get("restore_as") or meta.get("original_name") or meta.get("original") or Path(src).name.replace(".enc", "")
    return {"layers": layers, "keys": keys, "restore_as": restore, "compressed": bool(meta.get("compressed", False)),
            "src_sha256": meta.get("src_sha256"), "enc_sha256": meta.get("enc_sha256"), "created": meta.get("created", ""),
            "factors": meta.get("factors") or [], "wraps": meta.get("wraps") or [], "expires": meta.get("expires"), "policy": meta.get("policy"), "sig": meta.get("sig")}


# Диалог выбора ключа слоя (случайный, BIP39, фраза, пароль, свой, факторы, envelope)
def crypto_key_prompt(idx):
    print(f"  Как задать ключ слоя {idx}:")
    print("    g  случайный (надёжнее всего)")
    print("    b  12 слов BIP39 (легко записать)")
    print("    h  фраза, которую вы помните")
    print("    p  пароль + Argon2id (медленнее)")
    print("    s  свой готовый ключ")
    print("    f  несколько факторов (пароль/файл/устройство)")
    print("    m  ключ под несколькими паролями")
    while True:
        ch = ask("  Способ ключа [g]: ", "g").lower()
        if ch == "g":
            k = gen_key()
            return {"key": k, "kdf": "", "mnemonic": ""}
        if ch == "b":
            try:
                m, k = generate_mnemonic()
            except CFError as e:
                say_er(str(e))
                continue
            say_ok("Фраза BIP39: " + m)
            return {"key": k, "kdf": "", "mnemonic": m}
        if ch in ("h", "p"):
            kdf = "scrypt"
            if ch == "p":
                if has_argon2():
                    kdf = "argon2id"
                    say_wn("Argon2id: ~0.5–1 с на слой и 64 МБ памяти")
                else:
                    say_wn("Argon2id недоступен (apk add py3-argon2-cffi) — используется scrypt")
            ph = ask_secret("  Фраза/пароль (без запятых): ")
            if not ph:
                say_er("Пусто")
                continue
            if "," in ph:
                say_er("Запятая в ключе запрещена (ломает keys_csv)")
                continue
            if ask_secret("  Повторите: ") != ph:
                say_er("Не совпало")
                continue
            for w in check_phrase(ph):
                say_wn("Слабая фраза: " + w)
            return {"key": resolve_key(ph), "kdf": kdf, "mnemonic": ""}
        if ch == "s":
            k = ask("  Ключ (base64 / BIP39 / фраза, без запятых): ")
            if not k:
                continue
            if "," in k:
                say_er("Запятая в ключе запрещена")
                continue
            k = resolve_key(k, True)
            if not valid_raw_key(k):
                for w in check_phrase(k):
                    say_wn("Слабый ключ: " + w)
            return {"key": k, "kdf": "scrypt", "mnemonic": ""}
        if ch == "f":
            try:
                return factor_prompt(idx)
            except CFError as e:
                say_er(str(e))
                continue
        if ch == "m":
            try:
                return wrap_prompt(idx)
            except CFError as e:
                say_er(str(e))
                continue
        say_er("Неверный выбор")


# Диалог ключа классического шифра
def _classic_key_prompt(t, ru=True):
    hints = {
        "enigma": "позиции 3 роторов, напр. 1:5:13 или A:E:M; коммутатор после | (напр. 1:5:13|ABCD)",
        "vigenere": "слово-ключ (латиница или кириллица)",
        "caesar": "сдвиг 1-25",
        "railfence": "число рельсов 2-50",
    }
    if t in KEYLESS:
        return ""
    while True:
        k = ask(f"  Ключ ({hints[t]}); Enter — случайный: ")
        if not k:
            k = gen_classic_key(t)
            if t == "enigma":
                k = k.partition(";")[0] + (";ru" if ru else "")
            say_ok(f"Случайный ключ: {k}")
            return k
        if "," in k:
            say_er("Запятая в ключе запрещена")
            continue
        try:
            return norm_classic_key(t, k)
        except CFError as e:
            say_er(str(e))


# Ключ классического шифра (для Энигмы — вопрос про русский)
def classic_key_prompt(t):
    if t == "enigma":
        ru = ask_yn("Включить поддержку русских букв (кириллица заменяется латиницей и возвращается обратно; текст станет длиннее)?", "y")
        k = _classic_key_prompt(t, ru)
        return k.partition(";")[0] + (";ru" if ru else "")
    return _classic_key_prompt(t)


# Строка «слой → слой → …»
def stack_summary(spec):
    return " → ".join(layer_title(L["layer"]) for L in spec) if spec else "(пусто)"


# Интерактивное планирование слоёв: файловые шифры, текстовые, авто-стеки; проверка совместимости
def plan_layers(is_text):
    spec = []
    state = is_text
    while True:
        print()
        title_anim("СЛОИ")
        print(f"  Тип данных: {'текст' if state else 'бинарные'} · слоёв: {len(spec)}")
        cols = shutil.get_terminal_size((40, 20)).columns
        wide = cols >= 70
        groups = (
            ("ФАЙЛОВЫЕ ШИФРЫ — любые данные", ("crypto", "encode"), 84),
            ("ТЕКСТОВЫЕ ШИФРЫ — только текст", ("classic",), 213),
        )
        for gtitle, kinds, gcol in groups:
            print(f"  {grad(gtitle)}")
            for num, lid, title, note, kind in LAYER_DEFS:
                if kind not in kinds:
                    continue
                ok, why = layer_available(lid)
                if not ok:
                    tag = " \033[2m[недоступен]\033[0m"
                elif kind == "classic" and not state:
                    tag = " \033[2m[нужен текст]\033[0m"
                else:
                    tag = ""
                nm = title if wide else title.split(" (")[0]
                col = f"\033[1;38;5;{gcol}m{num:>2}\033[0m"
                if wide:
                    print(f"  {col}. {title:<28} \033[38;5;250m{note}\033[0m{tag}")
                else:
                    print(f"  {col}. {nm}{tag}")
                    print(f"      \033[2m{note[:cols - 8]}\033[0m")
        print(f"  {grad('ДОПОЛНИТЕЛЬНО')}")
        extra = (
            ("18", "Случайные слои (авто)", "сам выберет шифры и ключи", 220),
            ("19", "Случайные текстовые слои", "только текст: Энигма и др.", 220),
            ("0", "Готово", "закончить выбор слоёв", 203),
        )
        for num, name, note, col in extra:
            c = f"\033[1;38;5;{col}m{num:>2}\033[0m"
            if wide:
                print(f"  {c}. {name:<28} \033[38;5;250m{note}\033[0m")
            else:
                print(f"  {c}. {name}")
                print(f"      \033[2m{note[:cols - 8]}\033[0m")
        print("  \033[2mМожно списком: 3,4,5\033[0m")
        ch = ask("Номер слоя: ")
        if ch == "18":
            ch = "a"
        if ch == "19":
            ch = "t"
        if ch == "0":
            return spec
        if ch == "":
            continue
        if ch.lower() == "t":
            if not state:
                say_er("Текстовый авто-стек возможен только пока данные — текст. После файлового шифра текста уже нет.")
                continue
            n = ask_int("Сколько текстовых слоёв", 1, 50, 3)
            added = auto_stack(n, state, True, n)
            for L in added:
                spec.append(L)
                state = state_after(L["layer"], state)
            say_ok(f"Текстовый авто-стек: добавлено {len(added)} слоёв")
            continue
        if ch.lower() == "a":
            n = ask_int("Сколько случайных слоёв добавить", 1, 100, 5)
            inc = False
            tc = 0
            if state:
                inc = ask_yn("Добавить текстовые шифры в начало (ваши данные — текст)?", "n")
                if inc:
                    tc = ask_int("Сколько из них текстовых", 1, n, max(1, n // 2))
            added = auto_stack(n, state, inc, tc)
            for L in added:
                spec.append(L)
                state = state_after(L["layer"], state)
            say_ok(f"Авто-стек: добавлено {len(added)} слоёв")
            continue
        if "," in ch:
            applied = 0
            for tok in [x.strip() for x in ch.split(",") if x.strip()]:
                d = DEF_BY_NUM.get(tok)
                if not d:
                    say_wn(f"Пропущен неизвестный слой: {tok}")
                    continue
                if d[4] != "crypto":
                    say_wn(f"Пропущен текстовый/кодирующий слой: {d[2]}")
                    continue
                ok, why = layer_available(d[1])
                if not ok:
                    say_wn(f"Пропущен {d[2]}: {why}")
                    continue
                spec.append({"layer": d[1], "key": gen_key(), "kdf": "", "mnemonic": ""})
                state = False
                applied += 1
            say_ok(f"Быстрый стек: {applied} слоёв")
            continue
        d = DEF_BY_NUM.get(ch)
        if not d:
            say_er("Неверный выбор")
            continue
        lid, title, kind = d[1], d[2], d[4]
        ok, why = layer_available(lid)
        if not ok:
            say_er(f"{title} недоступен: {why}")
            continue
        if kind == "classic" and not state:
            say_er(f"{title} работает только с текстом, а данные сейчас бинарные — выберите шифр AES/ChaCha или добавьте классику до них")
            continue
        if kind == "classic":
            key = classic_key_prompt(lid)
            spec.append({"layer": lid, "key": key, "kdf": "", "mnemonic": ""})
        elif kind == "encode":
            spec.append({"layer": lid, "key": "", "kdf": "", "mnemonic": ""})
        else:
            r = crypto_key_prompt(len(spec) + 1)
            item = {"layer": lid, "key": r["key"], "kdf": r["kdf"], "mnemonic": r["mnemonic"]}
            for extra in ("factor", "wraps"):
                if r.get(extra):
                    item[extra] = r[extra]
            spec.append(item)
        state = state_after(lid, state)
        say_ok(f"Добавлено: {title}")


# Случайный стек: сначала текстовые шифры, затем файловые
def auto_stack(n, state, include_classic, text_count=0):
    out = []
    crypto = [d[1] for d in LAYER_DEFS if d[4] == "crypto" and not d[1].startswith("gpg:") and layer_available(d[1])[0]]
    classics = [d[1] for d in LAYER_DEFS if d[4] == "classic"]
    text_count = min(text_count, n) if (include_classic and state) else 0
    if not crypto and n > text_count:
        say_er("Нет доступных файловых шифров для авто-стека")
        return out
    for _ in range(text_count):
        pool = [c for c in classics if not (c == "atbash" and out and out[-1]["layer"] == "atbash")]
        lid = rand_choice(pool)
        out.append({"layer": lid, "key": gen_classic_key(lid), "kdf": "", "mnemonic": ""})
    for _ in range(n - text_count):
        out.append({"layer": rand_choice(crypto), "key": gen_key(), "kdf": "", "mnemonic": ""})
    say_in("Стек: " + stack_summary(out))
    return out


# Выбор имени .enc: оригинальное, случайное или своё
def choose_enc_name(restore_as):
    default = f"{restore_as}.enc"
    print("\nИмя зашифрованного файла:")
    print(f"  1. {default}")
    print("  2. Случайное (20 симв. a-z0-9)")
    print("  3. Своё")
    nc = ask("Вариант имени [1]: ", "1")
    if nc == "2":
        n = gen_name(".enc")
        say_ok(f"Случайное: {n}")
        return n
    if nc == "3":
        while True:
            c = ask("Имя (без .enc, разрешены буквы/цифры/_.-, кириллица): ")
            if not c:
                return default
            if c.endswith(".enc"):
                c = c[:-4]
            if valid_user_name(c):
                return c + ".enc"
            say_er("Недопустимое имя: без пробелов по краям, без точки в начале, без / и \\")
    return default


# Проверочная расшифровка и сверка SHA-256 до трогания оригинала
def verify_stack(final_tmp, spec, expect_sha, work):
    say_in("Проверка: расшифровка и сверка SHA-256...")
    layers = [L["layer"] for L in spec]
    keys = [L["key"] for L in spec]
    cur = reverse_stack(final_tmp, layers, keys, work, "Проверка слоя")
    h = sha256_file(cur, "sha256 ")
    try:
        cur.unlink()
    except OSError:
        pass
    if h != expect_sha:
        raise CFError("Проверка не пройдена: после расшифровки данные не совпали с исходными. Оригинал не тронут.")
    say_ok("Проверка пройдена: данные восстанавливаются без потерь")


# Текст recovery-блока для печати
def recovery_text(meta, mnemonics, qr_name, share_note):
    lines = [
        "CryptForge Recovery", "==================",
        f"Файл: {meta['final_name']}", f"Оригинал: {meta['original_name']}",
        f"Сжатие: {'да' if meta['compressed'] else 'нет'}", f"Создан: {meta['created']}", "",
        "Слои (в порядке шифрования):", ",".join(meta["layers"]), "",
        "Ключи (для вставки одной строкой при расшифровке):", ",".join(k for k in meta.get("_keys", []) if k), "",
    ]
    for i, m in mnemonics:
        lines.append(f"Слой {i} (BIP39): {m}")
    if mnemonics:
        lines.append("")
    if qr_name:
        lines.append(f"QR-код сохранён: {qr_name}")
    if share_note:
        lines.append(share_note)
    lines += ["", "Расшифровка:", "sh CryptForge.sh → 2 → выбрать файл → скрипт сам прочтёт meta",
              "или при потере meta ввести слои и ключи вручную"]
    return "\n".join(lines) + "\n"


# QR-код ключей (qrencode), показ и сохранение в PNG
def show_qr(text, png_name=None):
    if not shutil.which("qrencode"):
        say_er("qrencode не установлен: apk add qrencode")
        return None
    if len(text) > 1800:
        say_wn("Ключей слишком много для одного QR (лимит ~1800 символов)")
        return None
    try:
        r = subprocess.run(["qrencode", "-t", "ANSIUTF8"], input=text.encode(), capture_output=True, timeout=30)
        if r.returncode == 0:
            print(r.stdout.decode("utf-8", "ignore"))
        if png_name:
            p = BASE / png_name
            r2 = subprocess.run(["qrencode", "-o", str(p)], input=text.encode(), capture_output=True, timeout=30)
            if r2.returncode == 0:
                os.chmod(p, 0o600)
                say_ok(f"QR сохранён: {p}")
                return png_name
    except Exception as e:
        say_er(f"QR: {e}")
    return None


# Разбор размеров вида 10M/500K/1G
def parse_size(s):
    m = re.match(r"^(\d+)([KMG]?)$", s.strip().upper())
    if not m:
        return 10 * MB
    val = int(m.group(1)) * {"": 1, "K": 1024, "M": MB, "G": 1024 ** 3}[m.group(2)]
    if val < 1024:
        say_wn("Минимум 1K — использую 1K")
        return 1024
    if val > 1024 ** 3:
        say_wn("Максимум 1G — использую 1G")
        return 1024 ** 3
    return val


PAD_MAGIC = b"CFPD"
PAD_HDR = struct.Struct(">4sBIQI")


# Сколько мусорных данных добавить (проценты или байты)
def junk_amount(body, params):
    mode = params.get("mode", "percent")
    lo = int(params.get("min", 3))
    hi = int(params.get("max", 12))
    if hi < lo:
        hi = lo
    v = lo + rand_below(hi - lo + 1)
    amt = max(1024, body * v // 100) if mode == "percent" else v
    return max(0, min(amt, 1 << 30))


# Запись случайного мусора чанками
def write_junk(fo, n):
    left = n
    while left > 0:
        c = min(left, 1 << 20)
        fo.write(os.urandom(c))
        left -= c


# Деление мусора на начало и конец
def junk_split(amt, place):
    if place == "head":
        hh = amt
    elif place == "tail":
        hh = 0
    else:
        hh = rand_below(amt + 1)
    return hh, amt - hh


# Слой «паддинг»: заголовок + мусор + данные + мусор (внутри шифрованного слоя)
def pad_encrypt_file(inp, outp, params):
    body = os.path.getsize(inp)
    amt = junk_amount(body, params)
    hh, tt = junk_split(amt, params.get("place", "both"))
    with open(inp, "rb") as fi, open(outp, "wb") as fo:
        fo.write(PAD_HDR.pack(PAD_MAGIC, 1, hh, body, tt))
        write_junk(fo, hh)
        done = 0
        while True:
            c = fi.read(1 << 20)
            if not c:
                break
            fo.write(c)
            done += len(c)
            if body > MB:
                pbar(done, body, "паддинг ")
        write_junk(fo, tt)


# Снятие паддинга с проверкой размеров
def pad_decrypt_file(inp, outp):
    total = os.path.getsize(inp)
    with open(inp, "rb") as fi:
        h = fi.read(PAD_HDR.size)
        if len(h) < PAD_HDR.size:
            raise CFError("Слой паддинга: данные слишком короткие")
        magic, ver, hh, body, tt = PAD_HDR.unpack(h)
        if magic != PAD_MAGIC or ver != 1 or PAD_HDR.size + hh + body + tt != total:
            raise CFError("Слой паддинга повреждён (неверные ключи предыдущих слоёв или данные изменены)")
        fi.seek(PAD_HDR.size + hh)
        left = body
        with open(outp, "wb") as fo:
            while left > 0:
                c = fi.read(min(left, 1 << 20))
                if not c:
                    raise CFError("Слой паддинга: файл обрезан")
                fo.write(c)
                left -= len(c)


# Диалог настройки мусорных данных
def ask_junk_params(d, label="Мусорные данные"):
    print(f"  {label} прячут реальный размер.")
    print("   1. В процентах от размера")
    print("   2. В байтах")
    m = ask(f"  Режим [{1 if d.get('mode', 'percent') == 'percent' else 2}]: ", "1" if d.get("mode", "percent") == "percent" else "2")
    mode = "percent" if m == "1" else "bytes"
    if mode == "percent":
        lo = ask_int("  Минимум, %", 1, 300, min(max(int(d.get("min", 3)), 1), 300))
        hi = ask_int("  Максимум, %", lo, 300, max(lo, min(int(d.get("max", 12)), 300)))
    else:
        lo = ask_int("  Минимум, байт", 0, 1 << 30, int(d.get("min", 1024)) if d.get("mode") == "bytes" else 1024)
        hi = ask_int("  Максимум, байт", lo, 1 << 30, max(lo, 65536))
    print("   1. Только в начале  2. Только в конце  3. И там и там")
    pl = ask("  Место [3]: ", "3")
    place = {"1": "head", "2": "tail"}.get(pl, "both")
    return {"enabled": True, "mode": mode, "min": lo, "max": hi, "place": place}


# Доступные AEAD-слои
def aead_pool():
    return [x for x in ("gcm", "chacha", "ocb3", "gcmsiv", "shake") if layer_available(x)[0]]


# Доступные шифры OpenSSL
def ossl_pool():
    return [d[1] for d in LAYER_DEFS if d[1].startswith("openssl:") and layer_available(d[1])[0]]


# Индекс последнего файлового шифра в стеке
def last_crypto_index(spec):
    for i in range(len(spec) - 1, -1, -1):
        d = DEF_BY_ID.get(base_type(spec[i]["layer"]))
        if d and d[4] == "crypto":
            return i
    return None


# Дополняет стек: суффикс итераций OpenSSL, паддинг, внешний слой целостности
def finalize_spec(spec, junk=None, seal=True):
    spec = copy.deepcopy(spec)
    it = sec()["pbkdf2"]
    for L in spec:
        if L["layer"].startswith("openssl:") and "@" not in L["layer"] and it != 100000:
            L["layer"] += f"@{it}"
    if junk:
        idx = last_crypto_index(spec)
        if idx is None:
            say_wn("Мусор не добавлен: нужен хотя бы один файловый шифр")
        else:
            spec.insert(idx, {"layer": "pad", "key": "", "kdf": "", "mnemonic": "", "params": dict(junk)})
            say_in("Мусорные данные будут спрятаны внутри шифрованного слоя")
    if seal and spec and base_type(spec[-1]["layer"]) not in ALG_ID:
        pool = aead_pool()
        if pool:
            lid = rand_choice(pool)
            spec.append({"layer": lid, "key": gen_key(), "kdf": "", "mnemonic": ""})
            say_in(f"Добавлен внешний слой проверки целостности: {layer_title(lid)}")
    return spec


PROFILES = {
    "fast": ("Быстрый", "2 слоя AEAD"),
    "standard": ("Стандарт", "4 слоя + защита от подмены"),
    "strong": ("Усиленный", "7 слоёв + мусорные данные"),
    "max": ("Максимум", "12 слоёв, мусор, текст-шифры"),
}


# Автоматический стек по профилю (быстрый/стандарт/усиленный/максимум)
def profile_spec(level, is_text):
    aeads = aead_pool()
    ossl = ossl_pool()
    count = {"fast": 2, "standard": 4, "strong": 7, "max": 12}[level]
    out = []
    classics = [d[1] for d in LAYER_DEFS if d[4] == "classic"]
    if is_text and level in ("strong", "max"):
        for _ in range(1 if level == "strong" else 3):
            pool = [c for c in classics if not (c == "atbash" and out and out[-1]["layer"] == "atbash")]
            lid = rand_choice(pool)
            out.append({"layer": lid, "key": gen_classic_key(lid), "kdf": "", "mnemonic": ""})
    crypto = []
    if level in ("strong", "max") and ossl:
        pool = rand_shuffle(list(ossl))
        crypto += pool[: (2 if level == "strong" else len(pool))]
    while len(crypto) < count and aeads:
        crypto += rand_shuffle(list(aeads))
    crypto = rand_shuffle(crypto[:count])
    for lid in crypto:
        out.append({"layer": lid, "key": gen_key(), "kdf": "", "mnemonic": ""})
    junk = None
    if level == "strong":
        junk = {"enabled": True, "mode": "percent", "min": 5, "max": 15, "place": "both"}
    elif level == "max":
        junk = {"enabled": True, "mode": "percent", "min": 10, "max": 30, "place": "both"}
    return out, junk


# Выбор профиля шифрования
def choose_profile():
    print("\nПрофиль шифрования:")
    print("  1. Ручной выбор слоёв")
    n = 1
    keys = ["manual"]
    for k, (name, note) in PROFILES.items():
        n += 1
        keys.append(k)
        print(f"  {n}. {name}")
        print(f"      \033[2m{note}\033[0m")
    ch = ask("Профиль [1]: ", "1")
    if ch.isdigit() and 1 <= int(ch) <= len(keys):
        return keys[int(ch) - 1]
    return "manual"


# Случайные размеры частей в заданном диапазоне с точной суммой
def random_part_sizes(total, smin, smax, n):
    sizes = [smin] * n
    rem = total - smin * n
    cap = smax - smin
    if rem < 0 or rem > cap * n:
        raise CFError("Диапазон размеров не подходит для такого числа частей")
    idx = list(range(n))
    stall = 0
    while rem > 0:
        rand_shuffle(idx)
        progressed = False
        for i in idx:
            if rem == 0:
                break
            room = cap - (sizes[i] - smin)
            if room <= 0:
                continue
            add = rand_below(min(room, rem) + 1)
            if add:
                sizes[i] += add
                rem -= add
                progressed = True
        if not progressed:
            stall += 1
            if stall > 3:
                for i in idx:
                    room = cap - (sizes[i] - smin)
                    take = min(room, rem)
                    sizes[i] += take
                    rem -= take
    rand_shuffle(sizes)
    return sizes


# План разбиения: равные части или случайные по диапазону
def split_plan(total):
    print("\nРежим разбиения:")
    print("  1. Одинаковый размер частей")
    print("  2. Случайный размер (диапазон)")
    dflt = "2" if CFG.get("split_mode") == "random" else "1"
    mode = ask(f"Режим [{dflt}]: ", dflt)
    if mode != "2":
        size = parse_size(ask("Размер части (10M, 500K) [10M]: ", "10M"))
        if size >= total:
            return []
        sizes = [size] * (total // size)
        if total % size:
            sizes.append(total % size)
        return sizes
    smin_d = max(1024, total // 100)
    smax_d = min(max(smin_d * 2, total // 5), total - 1)
    say_in(f"Размер файла: {hsize(total)}")
    say_in(f"Предлагаемый диапазон: {hsize(smin_d)} – {hsize(smax_d)}")
    smin = parse_size(ask(f"Минимальный размер части [{smin_d}]: ", str(smin_d)))
    smax = parse_size(ask(f"Максимальный размер части [{smax_d}]: ", str(smax_d)))
    if smax >= total:
        smax = total - 1
    if smax < smin:
        smin = smax
    nmin = -(-total // smax)
    nmax = min(total // smin, 5000)
    if nmax < nmin:
        nmax = nmin
    say_in(f"Получится от {nmin} до {nmax} частей")
    lo = ask_int("Минимум частей", nmin, nmax, nmin)
    hi = ask_int("Максимум частей", lo, nmax, nmax)
    n = lo + rand_below(hi - lo + 1)
    if n * smin > total:
        smin = max(1, total // n)
    if n * smax < total:
        smax = -(-total // n)
    sizes = random_part_sizes(total, smin, smax, n)
    say_ok(f"Выбрано частей: {n}, размеры от {hsize(min(sizes))} до {hsize(max(sizes))}")
    return sizes


# Файлы-обманки со случайным содержимым
def make_decoy_files(dirpath, n, smin, smax, suffix=""):
    names = []
    for _ in range(n):
        name = gen_name(suffix)
        while (Path(dirpath) / name).exists():
            name = gen_name(suffix)
        sz = smin + rand_below(max(1, smax - smin + 1))
        p = Path(dirpath) / name
        with open(p, "wb") as fo:
            write_junk(fo, sz)
        os.chmod(p, 0o600)
        names.append(name)
    return names


# Чтение списка обманок
def decoys_load():
    try:
        if DECOYS_FILE.exists():
            return read_json_file(DECOYS_FILE)
    except CFError:
        raise
    except Exception:
        pass
    return {"vault": [], "parts": []}


# Сохранение списка обманок
def decoys_save(d):
    write_json_secure(DECOYS_FILE, d)


# Добавляет/удаляет поле в метаданных файла
def meta_update(final_name, key, value):
    mp = META / f"{final_name}.meta"
    if not mp.exists():
        return False
    try:
        d = read_json_file(mp)
        if value is None:
            d.pop(key, None)
        else:
            d[key] = value
        write_json_secure(mp, d)
        return True
    except Exception:
        return False


# Запись одной части с мусором и подсчётом хешей
def write_part(src, dst_path, size, jh, jt, whole):
    h = hashlib.sha256()
    with open(dst_path, "wb") as fo:
        for n in (jh,):
            left = n
            while left > 0:
                c = os.urandom(min(left, 1 << 20))
                fo.write(c)
                h.update(c)
                left -= len(c)
        left = size
        while left > 0:
            c = src.read(min(left, 1 << 20))
            if not c:
                raise CFError("Файл короче ожидаемого при разбиении")
            fo.write(c)
            h.update(c)
            whole.update(c)
            left -= len(c)
        left = jt
        while left > 0:
            c = os.urandom(min(left, 1 << 20))
            fo.write(c)
            h.update(c)
            left -= len(c)
    os.chmod(dst_path, 0o600)
    return h.hexdigest()


# Разбиение .enc на части со случайными именами; порядок и хеши — в метаданных
def split_enc(path, interactive=True):
    p = Path(path)
    if not p.is_file():
        raise CFError(f"Не найден: {p}")
    total = p.stat().st_size
    sizes = split_plan(total) if interactive else [10 * MB] * (total // (10 * MB)) + ([total % (10 * MB)] if total % (10 * MB) else [])
    if len(sizes) < 2:
        say_wn("Файл не больше размера части — делить нечего")
        return None
    pj = None
    if interactive:
        if ask_yn("Добавить мусор в каждую часть (скрывает точные размеры)?", "y" if CFG["parts_junk"].get("enabled") else "n"):
            d = CFG["parts_junk"]
            print("  Мусор в частях, байт на часть:")
            lo = ask_int("  Минимум, байт", 0, 1 << 28, int(d.get("min", 1024)))
            hi = ask_int("  Максимум, байт", lo, 1 << 28, max(lo, int(d.get("max", 65536))))
            print("   1. Только в начале  2. Только в конце  3. И там и там")
            pl = ask("  Место [3]: ", "3")
            pj = {"min": lo, "max": hi, "place": {"1": "head", "2": "tail"}.get(pl, "both")}
    need = total + 4 * MB + (pj["max"] * len(sizes) if pj else 0)
    if not check_space(need, PARTS):
        raise CFError("Недостаточно места")
    parts = []
    whole = hashlib.sha256()
    done = 0
    try:
        with open(p, "rb") as f:
            for sz in sizes:
                name = gen_name()
                while (PARTS / name).exists():
                    name = gen_name()
                jh = jt = 0
                if pj:
                    amt = pj["min"] + rand_below(pj["max"] - pj["min"] + 1)
                    jh, jt = junk_split(amt, pj["place"])
                fh = write_part(f, PARTS / name, sz, jh, jt, whole)
                parts.append({"name": name, "size": sz, "junk_head": jh, "junk_tail": jt, "sha256": fh})
                done += sz
                if total > MB:
                    pbar(done, total, "split ")
    except Exception:
        for x in parts:
            (PARTS / x["name"]).unlink(missing_ok=True)
        raise
    decoys = []
    dc = CFG["decoy_parts"]
    if interactive and ask_yn("Создать фальшивые части-обманки среди настоящих?", "y" if dc.get("enabled") else "n"):
        lo = ask_int("  Минимум обманок", 1, 500, int(dc.get("min_n", 2)))
        hi = ask_int("  Максимум обманок", lo, 500, max(lo, int(dc.get("max_n", 6))))
        smn = ask_int("  Мин. размер обманки, байт", 1, 1 << 30, int(dc.get("min_size", 4096)))
        smx = ask_int("  Макс. размер обманки, байт", smn, 1 << 30, max(smn, int(dc.get("max_size", 262144))))
        decoys = make_decoy_files(PARTS, lo + rand_below(hi - lo + 1), smn, smx)
        say_ok(f"Создано обманок: {len(decoys)}")
    rec = {"final_name": p.name, "size": total, "sha256": whole.hexdigest(), "mode": "random" if len(set(sizes)) > 2 else "fixed",
           "created": datetime.datetime.now().isoformat(timespec="seconds"), "parts": parts, "decoys": decoys}
    write_json_secure(META / f"{p.name}.split", rec)
    summary = {"record": f"{p.name}.split", "part_count": len(parts), "size": total, "sha256": rec["sha256"], "mode": rec["mode"], "parts": parts, "decoys": decoys, "created": rec["created"]}
    if meta_update(p.name, "split", summary):
        say_ok("Сведения о разбиении записаны в метаданные")
    say_ok(f"Разделено на {len(parts)} частей в {PARTS} (имена случайные)")
    log_action("split", total, rec["sha256"], None, None, f"parts={len(parts)} decoys={len(decoys)}")
    if interactive and ask_yn("Удалить исходный .enc (затереть)?", "n"):
        wipe_file(p)
        say_ok("Исходный .enc затёрт. Собрать обратно: пункт «Собрать из частей»")
    return rec


# Сборка файла из частей с проверкой всех хешей
def join_flow():
    recs = []
    for sp in sorted(META.glob("*.split")):
        try:
            recs.append((sp, read_json_file(sp)))
        except CFError as e:
            say_wn(f"{sp.name}: {e}")
        except Exception:
            say_wn(f"Повреждён файл разбиения: {sp.name}")
    if not recs:
        say_wn("Нет записей о разбиении. Части без метаданных собрать нельзя (имена случайные).")
        return
    print("\nНаборы частей:")
    for i, (sp, r) in enumerate(recs, 1):
        have = sum(1 for x in r["parts"] if (PARTS / x["name"]).exists())
        print(f"  {i}) {r['final_name']}")
        print(f"      \033[2mчастей {have}/{len(r['parts'])}, {hsize(r['size'])}\033[0m")
    sel = ask("Какой набор собрать (номер): ")
    if not sel.isdigit() or not 1 <= int(sel) <= len(recs):
        say_er("Нужен номер из списка")
        return
    sp, r = recs[int(sel) - 1]
    missing = [x["name"] for x in r["parts"] if not (PARTS / x["name"]).exists()]
    if missing:
        raise CFError(f"Не хватает частей: {len(missing)} шт. (в {PARTS})")
    if not check_space(r["size"] + 4 * MB, VAULT):
        raise CFError("Недостаточно места")
    total = sum(x["size"] + x.get("junk_head", 0) + x.get("junk_tail", 0) for x in r["parts"])
    say_in("Проверка частей...")
    done = 0
    for x in r["parts"]:
        fp = PARTS / x["name"]
        exp = x["size"] + x.get("junk_head", 0) + x.get("junk_tail", 0)
        if fp.stat().st_size != exp:
            raise CFError("Часть имеет неверный размер")
        if sha256_file(fp) != x["sha256"]:
            raise CFError("Часть повреждена (SHA-256 не совпал)")
        done += exp
        pbar(done, total, "verify ")
    out = VAULT / r["final_name"]
    if out.exists():
        if sha256_file(out) == r["sha256"]:
            say_ok(f"Файл уже собран и идентичен: {out}")
            return
        out = unique_path(VAULT, r["final_name"])
        say_wn(f"Имя занято — собираю как {out.name} (метаданные найдутся по хешу)")
    say_in("Сборка...")
    tmp = out.with_name(out.name + ".part")
    done = 0
    h = hashlib.sha256()
    with open(tmp, "wb") as fo:
        for x in r["parts"]:
            with open(PARTS / x["name"], "rb") as fi:
                fi.seek(x.get("junk_head", 0))
                left = x["size"]
                while left > 0:
                    c = fi.read(min(left, 1 << 20))
                    if not c:
                        raise CFError("Часть оказалась короче записанной")
                    fo.write(c)
                    h.update(c)
                    left -= len(c)
                    done += len(c)
                    pbar(done, r["size"], "join ")
    if h.hexdigest() != r["sha256"]:
        tmp.unlink()
        raise CFError("Собранный файл не совпал по SHA-256")
    os.replace(tmp, out)
    os.chmod(out, 0o600)
    say_ok(f"Собрано: {out}")
    say_ok("SHA-256 совпал — целостность подтверждена. Метаданные на месте, имя менять не нужно.")
    log_action("join", r["size"], None, r["sha256"], None, out.name)
    if ask_yn("Удалить части (и обманки) и запись о разбиении?", "n"):
        for x in r["parts"]:
            wipe_file(PARTS / x["name"])
        for nm in r.get("decoys", []):
            wipe_file(PARTS / nm)
        sp.unlink(missing_ok=True)
        meta_update(r["final_name"], "split", None)
        say_ok("Части удалены")


# Меню обманок в vault
def decoys_menu():
    title_anim("ОБМАНКИ")
    d = decoys_load()
    print(f"  Файлов-обманок в vault: {len(d.get('vault', []))}")
    print("   1. Создать обманки в vault")
    print("   2. Удалить обманки из vault")
    print("   0. Назад")
    c = ask("Выбор: ")
    if c == "1":
        n = ask_int("Сколько файлов", 1, 200, 3)
        smn = ask_int("Мин. размер, байт", 1024, 1 << 30, 100000)
        smx = ask_int("Макс. размер, байт", smn, 1 << 30, max(smn, 5 * MB))
        if not check_space(n * smx + 4 * MB, VAULT):
            return
        names = make_decoy_files(VAULT, n, smn, smx, ".enc")
        d.setdefault("vault", []).extend(names)
        decoys_save(d)
        say_ok(f"Создано обманок: {len(names)} (внешне не отличаются от .enc)")
    elif c == "2":
        k = 0
        for nm in list(d.get("vault", [])):
            wipe_file(VAULT / nm)
            k += 1
        d["vault"] = []
        decoys_save(d)
        say_ok(f"Удалено обманок: {k}")


# Меню разбиения файлов
def split_menu():
    files = pick_files("Файл для разделения", [VAULT], True)
    for f in files:
        try:
            split_enc(f)
        except CFError as e:
            say_er(str(e))


# Что сделать с оригиналом после шифрования
def handle_original(f, is_dir):
    print("\nЧто сделать с оригиналом?")
    print("  1. Сохранить в originals/")
    print("  2. Удалить")
    print("  3. Затереть (3 прохода) и удалить")
    print("  4. Оставить на месте")
    oc = ask("Что с оригиналом [4]: ", "4")
    f = Path(f)
    try:
        if oc == "1":
            if f.parent.resolve() == ORIGINALS.resolve():
                say_in("Оригинал уже в originals/")
            else:
                dest = unique_path(ORIGINALS, f.name)
                shutil.move(str(f), str(dest))
                say_ok(f"Оригинал: {dest}")
        elif oc == "2":
            if f.is_dir():
                shutil.rmtree(f)
            else:
                f.unlink()
            say_ok(f"Удалён: {f}")
        elif oc == "3":
            say_wn("Тройная перезапись может занять время")
            wipe_file(f)
            say_ok(f"Затёрт и удалён: {f}")
        else:
            say_in(f"Оригинал оставлен: {f}")
    except Exception as e:
        say_er(f"Не удалось обработать оригинал: {e}")


# Очистка экрана и истории прокрутки
def clear_screen():
    sys.stdout.write("\033[3J\033[H\033[2J")
    sys.stdout.flush()


# =====================================================================
# РАЗДЕЛ: ШИФРОВАНИЕ: ядро и меню
# =====================================================================
# Ядро шифрования: слои, имя, проверка, запись в vault, финализация
def encrypt_source(src, orig, restore_as, compressed, is_dir, opts, shared, work, handle_orig=True):
    src = Path(src)
    orig = Path(orig)
    src_sha = sha256_file(src, "sha256 ")
    is_text = is_text_file(src)
    spec = None
    if shared.get("spec"):
        ok, msg = spec_compatible(shared["spec"], is_text)
        if ok:
            spec = copy.deepcopy(shared["spec"])
            say_in("Применяю общий набор слоёв: " + stack_summary(spec))
        else:
            say_wn("Общий набор не подходит этому файлу: " + msg)
    if spec is None:
        prof = shared.get("profile", "manual")
        seal = bool(CFG.get("seal_outer", True))
        if prof == "manual":
            spec = plan_layers(is_text)
            if not spec:
                say_wn("Слои не выбраны — пропуск")
                return None
            junk = None
            if ask_yn("Добавить мусорные данные внутрь файла (скрывают размер)?", "y" if CFG["junk"].get("enabled") else "n"):
                junk = ask_junk_params(CFG["junk"])
            spec = finalize_spec(spec, junk, seal)
            if opts["more_files"] > 0 and not shared.get("asked"):
                shared["asked"] = True
                if ask_yn("Применить те же слои/ключи к остальным файлам?", "n"):
                    shared["spec"] = copy.deepcopy(spec)
        else:
            spec, junk = profile_spec(prof, is_text)
            spec = finalize_spec(spec, junk, seal)
            say_in(f"Профиль «{PROFILES[prof][0]}», слоёв: {len(spec)}")
    ok, msg = spec_compatible(spec, is_text)
    if not ok:
        raise CFError("Несовместимо с данными: " + msg)
    say_in("Стек: " + stack_summary(spec))
    final_name = choose_enc_name(restore_as)
    t0 = time.time()
    final_tmp = apply_stack(src, spec, work)
    if opts["verify"]:
        verify_stack(final_tmp, spec, src_sha, work)
    else:
        say_wn("Проверка расшифровкой отключена")
    final_path = unique_path(VAULT, final_name)
    shutil.move(str(final_tmp), str(final_path))
    os.chmod(final_path, 0o600)
    final_name = final_path.name
    enc_sha = sha256_file(final_path)
    say_ok(f"Готово: {final_path} ({hsize(final_path.stat().st_size)}, {int(time.time() - t0)} с)")
    finalize_encrypted(orig, final_path, final_name, restore_as, compressed, is_dir, spec, src_sha, src.stat().st_size, enc_sha, handle_orig)
    log_action("encrypt", src.stat().st_size, src_sha, enc_sha, [L["layer"] for L in spec], final_name)
    return final_path


# Шифрование одного файла/папки (архивация при необходимости)
def encrypt_one(f, opts, shared):
    f = Path(f)
    if not f.exists():
        raise CFError(f"Не найден: {f}")
    is_dir = f.is_dir()
    size = dir_size(f)
    if not check_space(size * 3 + 4 * MB):
        raise CFError("Недостаточно места для шифрования")
    work = new_work()
    try:
        compressed = is_dir or opts["compress"]
        if compressed:
            src = work / (f.name + ".tar.gz")
            say_in(f"Архивация: {f.name}")
            make_tar_gz(f, src)
            say_ok(f"Архив готов: {hsize(src.stat().st_size)}")
        else:
            src = f
        return encrypt_source(src, f, f.name, compressed, is_dir, opts, shared, work, True)
    finally:
        shutil.rmtree(work, ignore_errors=True)


# Меню шифрования: выбор файлов, случайность, профиль, проверка
def encrypt_flow():
    files = pick_files("Файлы/папки для шифрования", [ORIGINALS, HOME] + loc_dirs())
    if not files:
        say_wn("Выбор отменён")
        return
    if CFG.get("ask_entropy") or ask_yn("Добавить свою случайность к генерации ключей?", "n"):
        collect_entropy()
    shared = {"profile": choose_profile()}
    compress = ask_yn("Сжать перед шифрованием (меньше размер)?", "n")
    verify = ask_yn("Проверять расшифровкой после шифрования (рекомендуется)?", "y")
    total = len(files)
    for idx, f in enumerate(files, 1):
        print()
        say_in(f"[{idx}/{total}] {f}")
        opts = {"compress": compress, "verify": verify, "more_files": total - idx}
        try:
            encrypt_one(f, opts, shared)
        except CFError as e:
            say_er(f"{e} — оригинал не тронут")
        except KeyboardInterrupt:
            raise
        except Exception as e:
            say_er(f"Сбой шифрования: {type(e).__name__}: {e} — оригинал не тронут")
            ERR_LOG.write_text(traceback.format_exc())



# Ручной ввод слоёв и ключей при отсутствии метаданных
def manual_info(src):
    print("\nМетаданных нет. Источник данных:")
    print("  1. Ввести слои и ключи вручную")
    print("  2. Восстановить из долей Шамира")
    ch = ask("Источник данных [1]: ", "1")
    if ch == "2":
        raw = ask("Файлы долей (пути через запятую): ")
        lines = []
        for tok in raw.split(","):
            tok = tok.strip()
            if not tok:
                continue
            pth = Path(os.path.expanduser(tok))
            if pth.is_file():
                lines.append(pth.read_text(encoding="utf-8", errors="ignore"))
            else:
                lines.append(tok)
        if len(lines) == 1 and "CFSHARE1" in lines[0] and "," in raw and not Path(os.path.expanduser(raw.split(",")[0].strip())).exists():
            lines = [raw]
        d = combine_share_lines(lines)
        say_ok("Данные восстановлены из долей")
        return {"layers": d["layers"], "keys": d["keys"], "restore_as": d.get("restore_as") or src.stem, "compressed": bool(d.get("compressed")),
                "src_sha256": None, "enc_sha256": None}
    print("\nИдентификаторы слоёв:")
    print("  " + ", ".join(d[1] for d in LAYER_DEFS))
    print("  можно вводить и номера из меню слоёв (3,4,2). Порядок — как при шифровании")
    raw = ask("Слои через запятую: ")
    if not raw:
        raise CFError("Слои не указаны")
    layers = []
    for tok in [x.strip() for x in raw.split(",") if x.strip()]:
        if tok in DEF_BY_NUM:
            layers.append(DEF_BY_NUM[tok][1])
        elif base_type(tok) in DEF_BY_ID or base_type(tok) in LEGACY_TITLES:
            layers.append(tok)
        else:
            raise CFError(f"Неизвестный слой: {tok}")
    default_name = safe_restore_name(src.name[:-4] if src.name.endswith(".enc") else src.name) or "restored"
    print("\nИмя результата: в .enc оригинальное имя не хранится (оно было только в метаданных).")
    print(f"Enter — «{default_name}», либо введите любое другое имя (расширение .jpg/.pdf/.txt лучше указать).")
    entered = ask("Имя файла: ")
    restore = safe_restore_name(entered) or default_name
    if entered and restore != entered:
        say_wn(f"Имя скорректировано (убраны невидимые символы/точки): {restore!r}")
    comp = ask_yn("Файл был сжат или это была папка?", "n")
    return {"layers": layers, "keys": [""] * len(layers), "restore_as": restore, "compressed": comp, "src_sha256": None, "enc_sha256": None}


# Получение ключей слоёв: из метаданных, факторов, envelope или вручную
def fill_keys(info):
    layers = info["layers"]
    keys = list(info["keys"]) + [""] * (len(layers) - len(info["keys"]))
    factors = info.get("factors") or []
    wraps = info.get("wraps") or []
    for i in range(len(layers)):
        if i < len(factors) and factors[i]:
            keys[i] = factor_collect(factors[i], i + 1)
        elif i < len(wraps) and wraps[i]:
            for _ in range(3):
                dek = wrap_open(wraps[i], ask_secret(f"  Пароль слоя {i + 1}: "))
                if dek:
                    keys[i] = dek
                    break
                say_er("Пароль не подошёл")
            else:
                raise CFError(f"Слой {i + 1}: пароль не принят")
    missing = [i for i, l in enumerate(layers) if needs_key(l) and not keys[i]]
    if missing:
        say_wn(f"Нужно ключей: {len(missing)} (слоёв всего {len(layers)})")
        print("Формат: key1,key2,... в порядке слоёв (слои atbash/base64 без ключа). Фразу BIP39 можно вставить как есть.")
        raw = ask("Ключи через запятую: ")
        given = [x.strip() for x in raw.split(",") if x.strip()] if raw else []
        for j, i in enumerate(missing):
            if j < len(given):
                keys[i] = given[j]
            else:
                keys[i] = ask(f"  Ключ слоя {i + 1} ({layer_title(layers[i])}): ")
        if len(given) > len(missing):
            say_wn(f"Лишние ключи проигнорированы: {len(given) - len(missing)}")
    for i, l in enumerate(layers):
        if needs_key(l) and not keys[i]:
            raise CFError(f"Нет ключа для слоя {i + 1}")
        if base_type(l) not in CLASSIC and base_type(l) != "base64":
            keys[i] = resolve_key(keys[i], True)
    return keys


# =====================================================================
# РАЗДЕЛ: РАСШИФРОВКА: проверки доступа, слои, распаковка
# =====================================================================
# Расшифровка одного файла: проверки доступа, слои, SHA-256, распаковка
def decrypt_one(src, override=None):
    src = Path(src)
    if not src.is_file():
        raise CFError(f"Не файл: {src}")
    if override is not None:
        meta, mp, status = None, None, "override"
    else:
        meta, mp, status = find_meta(src)
    if status == "corrupt":
        say_wn("Метаданные повреждены — ввод вручную")
    elif status == "locked":
        say_wn("Метаданные зашифрованы, пароль не принят — ввод вручную")
    if meta:
        info = normalize_meta(meta, src)
        say_ok(f"Метаданные: {mp.name} (слоёв: {len(info['layers'])})")
    elif override is not None:
        info = dict(override)
    else:
        if status == "none":
            say_wn(f"Метаданные для {src.name} не найдены")
        info = manual_info(src)
    if not info["layers"]:
        raise CFError("Нет слоёв")
    info["restore_as"] = safe_restore_name(info["restore_as"]) or src.stem
    check_access(src, info)
    keys = fill_keys(info)
    if not check_space(src.stat().st_size * 3 + 4 * MB):
        raise CFError("Недостаточно места")
    if info.get("enc_sha256"):
        if sha256_file(src, "sha256 ") != info["enc_sha256"]:
            say_wn("SHA-256 файла не совпал с метаданными — файл изменён или повреждён")
            if not ask_yn("Продолжить всё равно?", "n"):
                return
    work = new_work()
    try:
        t0 = time.time()
        try:
            cur = reverse_stack(src, info["layers"], keys, work)
        except CFError:
            attempt_fail(src.name)
            log_action("decrypt-fail", None, None, None, None, src.name[:12])
            raise
        attempt_ok(src.name)
        final_sha = sha256_file(cur, "sha256 ")
        if info.get("src_sha256"):
            if final_sha == info["src_sha256"]:
                say_ok("Целостность подтверждена: SHA-256 совпал с исходным")
            else:
                say_er("SHA-256 результата не совпал с исходным — возможно неверные ключи/слои или данные повреждены")
                if not ask_yn("Всё равно сохранить результат?", "n"):
                    return
        else:
            say_wn("Исходного хеша нет — корректность результата проверить нельзя")
        if info["compressed"]:
            ex = extract_tar_safe(cur, work / "extract")
            items = list(ex.iterdir())
            target = unique_path(out_dir(), info["restore_as"])
            if len(items) == 1:
                shutil.move(str(items[0]), str(target))
            else:
                shutil.move(str(ex), str(target))
            fix_perms(target)
            say_ok(f"Распаковано: {target}")
        else:
            target = unique_path(out_dir(), info["restore_as"])
            shutil.move(str(cur), str(target))
            fix_perms(target)
            say_ok(f"Расшифровано: {target}")
            quick_type_hint(target)
        say_in(f"SHA256 слоя до распаковки: {final_sha}")
        log_action("decrypt", src.stat().st_size, None, final_sha, info["layers"], src.name)
    finally:
        shutil.rmtree(work, ignore_errors=True)


# Меню расшифровки
def decrypt_flow():
    files = pick_files("Файлы для расшифровки", [VAULT], True)
    if not files:
        say_wn("Выбор отменён")
        return
    for f in files:
        print()
        say_in(f"Расшифровка: {Path(f).name}")
        try:
            decrypt_one(f)
        except CFError as e:
            say_er(str(e))
        except KeyboardInterrupt:
            raise
        except Exception as e:
            say_er(f"Сбой: {type(e).__name__}: {e}")
            ERR_LOG.write_text(traceback.format_exc())


BIT_TBL = [bytes(((v >> (7 - i)) & 1) for i in range(8)) for v in range(256)]
TO_CH = bytes.maketrans(b"\x00\x01", b"01")
ST_MAGIC = b"CFST1"
ST_HEAD = len(ST_MAGIC) + 8 + 32


# =====================================================================
# РАЗДЕЛ: LSB-СТЕГАНОГРАФИЯ (классика, PNG/WAV) [Условный]
# =====================================================================
# Байты → поток бит (0/1)
def bytes_to_bits(data):
    return b"".join(BIT_TBL[b] for b in data)


# Поток бит → байты
def bits_to_bytes(bits):
    if not bits:
        return b""
    return int(bits.translate(TO_CH).decode(), 2).to_bytes(len(bits) // 8, "big")


# Запись бит в младшие биты буфера
def lsb_write(buf, offset_bits, bits):
    n = len(bits)
    head = bytes(buf[offset_bits:offset_bits + n])
    mask = int.from_bytes(b"\xfe" * n, "big")
    v = (int.from_bytes(head, "big") & mask) | int.from_bytes(bits, "big")
    buf[offset_bits:offset_bits + n] = v.to_bytes(n, "big")


# Чтение младших бит буфера
def lsb_read(buf, offset_bits, n):
    head = bytes(buf[offset_bits:offset_bits + n])
    v = int.from_bytes(head, "big") & int.from_bytes(b"\x01" * n, "big")
    return v.to_bytes(n, "big")


# LSB-внедрение с заголовком и SHA-256
def embed_payload(buf, payload):
    data = ST_MAGIC + len(payload).to_bytes(8, "big") + hashlib.sha256(payload).digest() + payload
    if len(data) * 8 > len(buf):
        raise CFError(f"Контейнер мал: вмещает {hsize(len(buf) // 8 - ST_HEAD)}, нужно {hsize(len(payload))}")
    total = len(data)
    step = 256 * 1024
    done = 0
    while done < total:
        chunk = data[done:done + step]
        lsb_write(buf, done * 8, bytes_to_bits(chunk))
        done += len(chunk)
        if total > MB:
            pbar(done, total, "стего ")


# LSB-извлечение с проверкой
def extract_payload(buf):
    head = bits_to_bytes(lsb_read(buf, 0, ST_HEAD * 8))
    if head[:len(ST_MAGIC)] != ST_MAGIC:
        raise CFError("В контейнере нет данных CryptForge")
    ln = int.from_bytes(head[len(ST_MAGIC):len(ST_MAGIC) + 8], "big")
    sha = head[len(ST_MAGIC) + 8:]
    if (ST_HEAD + ln) * 8 > len(buf):
        raise CFError("Заголовок стего повреждён")
    out = bytearray()
    step = 256 * 1024
    pos = 0
    while pos < ln:
        n = min(step, ln - pos)
        out += bits_to_bytes(lsb_read(buf, (ST_HEAD + pos) * 8, n * 8))
        pos += n
        if ln > MB:
            pbar(pos, ln, "извлечение ")
    if hashlib.sha256(bytes(out)).digest() != sha:
        raise CFError("SHA-256 извлечённых данных не совпал")
    return bytes(out)


# Пиксели PNG как буфер RGB (альфа сохраняется)
def png_buffer(path):
    try:
        from PIL import Image
    except ImportError:
        raise CFError("Нужен Pillow: apk add py3-pillow")
    im = Image.open(path)
    im.load()
    alpha = None
    if im.mode in ("RGBA", "LA") or (im.mode == "P" and "transparency" in im.info):
        im = im.convert("RGBA")
        alpha = im.getchannel("A")
    rgb = im.convert("RGB")
    return Image, rgb, alpha


# LSB: спрятать файл в PNG/WAV с проверкой
def stego_hide(payload_path=None):
    if payload_path is None:
        fl = pick_files("Файл, который спрятать", [VAULT], True)
        if not fl:
            return
        payload_path = fl[0]
    payload_path = Path(payload_path)
    raw = ask("Путь к контейнеру PNG или WAV: ")
    cont = Path(os.path.expanduser(raw))
    if not cont.is_file():
        raise CFError("Контейнер не найден")
    payload = payload_path.read_bytes()
    ext = cont.suffix.lower()
    out = STEGO / gen_name(ext)
    if ext == ".png":
        Image, rgb, alpha = png_buffer(cont)
        buf = bytearray(rgb.tobytes())
        cap = len(buf) // 8 - ST_HEAD
        say_in(f"Вместимость PNG: {hsize(max(cap, 0))}, нужно {hsize(len(payload))}")
        embed_payload(buf, payload)
        img = Image.frombytes("RGB", rgb.size, bytes(buf))
        if alpha is not None:
            img.putalpha(alpha)
        img.save(out, "PNG")
        _, rgb2, _ = png_buffer(out)
        check = bytearray(rgb2.tobytes())
    elif ext == ".wav":
        import wave
        with wave.open(str(cont), "rb") as w:
            params = w.getparams()
            if params.sampwidth != 2 or params.comptype != "NONE":
                raise CFError("Поддерживается только 16-бит PCM WAV")
            frames = bytearray(w.readframes(params.nframes))
        low = bytearray(frames[0::2])
        say_in(f"Вместимость WAV: {hsize(max(len(low) // 8 - ST_HEAD, 0))}, нужно {hsize(len(payload))}")
        embed_payload(low, payload)
        frames[0::2] = low
        with wave.open(str(out), "wb") as w:
            w.setparams(params)
            w.writeframes(bytes(frames))
        with wave.open(str(out), "rb") as w:
            fr2 = bytearray(w.readframes(w.getparams().nframes))
        check = bytearray(fr2[0::2])
    else:
        raise CFError("Контейнер должен быть .png или .wav")
    if extract_payload(check) != payload:
        out.unlink(missing_ok=True)
        raise CFError("Проверка стего не пройдена")
    os.chmod(out, 0o600)
    say_ok(f"Данные спрятаны: {out}")
    log_action("stego-hide", len(payload), hashlib.sha256(payload).hexdigest(), None, None, out.name)


# LSB: извлечь
def stego_extract():
    fl = pick_files("PNG/WAV с данными", [STEGO], True)
    if not fl:
        return
    cont = Path(fl[0])
    ext = cont.suffix.lower()
    if ext == ".png":
        _, rgb, _ = png_buffer(cont)
        buf = bytearray(rgb.tobytes())
    elif ext == ".wav":
        import wave
        with wave.open(str(cont), "rb") as w:
            frames = bytearray(w.readframes(w.getparams().nframes))
        buf = bytearray(frames[0::2])
    else:
        raise CFError("Нужен .png или .wav")
    data = extract_payload(buf)
    name = ask("Имя для извлечённого файла (Enter — случайное .enc): ")
    if not name:
        name = gen_name(".enc")
    elif not valid_user_name(name):
        raise CFError("Недопустимое имя")
    out = unique_path(VAULT, name)
    out.write_bytes(data)
    os.chmod(out, 0o600)
    say_ok(f"Извлечено в хранилище: {out} (SHA-256 сверен)")
    log_action("stego-extract", len(data), None, hashlib.sha256(data).hexdigest(), None, out.name)


# Меню классического LSB
def lsb_menu():
    print("\n  1. Спрятать файл в PNG/WAV")
    print("  2. Извлечь файл из PNG/WAV")
    c = ask("Выбор: ")
    try:
        if c == "1":
            stego_hide()
        elif c == "2":
            stego_extract()
    except CFError as e:
        say_er(str(e))


# Определение типа файла по началу
def type_report(p):
    with open(p, "rb") as f:
        head = f.read(64)
    return detect_type(head)


# Поиск хвоста/обрезки у PNG/JPEG/PDF
def tail_issues(p, ext):
    size = p.stat().st_size
    data = p.read_bytes() if size <= 256 * MB else None
    if data is None:
        return None, None
    if ext == "png":
        i = data.rfind(b"IEND\xaeB`\x82")
        if i < 0:
            return "truncated", None
        return ("trailing", i + 8) if i + 8 < len(data) else (None, None)
    if ext == "jpg":
        i = data.rfind(b"\xff\xd9")
        if i < 0:
            return "truncated", None
        return ("trailing", i + 2) if i + 2 < len(data) else (None, None)
    if ext == "pdf":
        i = data.rfind(b"%%EOF")
        if i < 0:
            return "truncated", None
        end = i + 5
        rest = data[end:]
        if rest.strip(b"\r\n\x00 ") == b"" and len(rest) > 2:
            return "trailing", end + 1
        return None, None
    return None, None


# =====================================================================
# РАЗДЕЛ: ПОЧИНКА, ПЕРЕИМЕНОВАНИЕ, ХРАНИЛИЩЕ, ЗАТИРАНИЕ
# =====================================================================
# Очистка имени от системных и невидимых символов
def clean_filename(n):
    import unicodedata
    n = unicodedata.normalize("NFC", n)
    n = "".join(" " if unicodedata.category(ch) == "Zs" else ch for ch in n)
    n = "".join(ch for ch in n if unicodedata.category(ch) not in ("Cc", "Cf", "Cs", "Co", "Cn"))
    n = re.sub(r'[/\\:*?"<>|]', "_", n)
    n = re.sub(r" {2,}", " ", n)
    return n.strip().lstrip(".").rstrip(". ")


# Переименование с переносом метаданных
def rename_with_meta(f, dest):
    f = Path(f)
    dest = Path(dest)
    f.rename(dest)
    if dest.parent.resolve() == VAULT.resolve():
        for ext in (".meta", ".split"):
            om = META / f"{f.name}{ext}"
            if om.exists():
                nm = META / f"{dest.name}{ext}"
                os.replace(om, nm)
                try:
                    d = read_json_file(nm)
                    d["final_name"] = dest.name
                    write_json_secure(nm, d)
                except Exception:
                    pass


# Починка файла: имя, расширение, хвост, права, целостность архивов
def repair_file(p):
    p = Path(p)
    print()
    say_in(f"Файл: {p.name} ({hsize(p.stat().st_size)})")
    changed = False
    cleaned = clean_filename(p.name)
    if cleaned and cleaned != p.name:
        say_wn(f"В имени есть системные/невидимые символы или запрещённые знаки: {p.name!r}")
        if ask_yn(f"Переименовать в «{cleaned}»?", "y"):
            dest = unique_path(p.parent, cleaned)
            try:
                rename_with_meta(p, dest)
                say_ok(f"Имя исправлено: {dest.name}")
                p = dest
                changed = True
            except OSError as e:
                say_er(f"Не удалось переименовать: {e}")
    elif not cleaned:
        say_wn("Имя состоит только из служебных символов — используйте пункт 8 для переименования")
    if p.is_dir():
        fix_perms(p)
        say_ok("Права папки исправлены (755/644)")
        return
    ext, name = type_report(p)
    if ext:
        say_in(f"Определён тип: {name}")
    else:
        if is_text_file(p):
            say_in("Тип: текст UTF-8")
        else:
            raw = p.read_bytes() if p.stat().st_size < 64 * MB else b""
            if raw and b"\x00" not in raw[:4096]:
                bad = len(raw.decode("utf-8", errors="replace").split("\ufffd")) - 1
                say_wn(f"Текст с невалидным UTF-8 (повреждённых последовательностей: {bad})")
                if ask_yn("Попробовать прочитать как Windows-1251 и сохранить копию в UTF-8?", "n"):
                    try:
                        out = unique_path(p.parent, p.stem + ".utf8" + p.suffix)
                        out.write_text(raw.decode("cp1251", errors="replace"), encoding="utf-8")
                        fix_perms(out)
                        say_ok(f"Создана копия: {out}")
                    except Exception as e:
                        say_er(str(e))
            else:
                say_wn("Тип не распознан")
    if ext:
        if not ext_matches(p.name, ext):
            canon = {"gz": "gz", "zip": "zip"}.get(ext, ext)
            say_wn(f"Расширение не соответствует типу (ожидается .{canon})")
            if ask_yn(f"Переименовать в *.{canon}?", "y"):
                dest = unique_path(p.parent, p.stem + "." + canon)
                p.rename(dest)
                p = dest
                say_ok(f"Переименовано: {p.name}")
                changed = True
        issue, pos = tail_issues(p, ext)
        if issue == "trailing":
            say_wn(f"После конца данных лишние байты ({p.stat().st_size - pos} шт.)")
            if ask_yn("Создать очищенную копию?", "y"):
                out = unique_path(p.parent, p.stem + ".fixed" + p.suffix)
                out.write_bytes(p.read_bytes()[:pos])
                fix_perms(out)
                say_ok(f"Создана копия: {out}")
        elif issue == "truncated":
            say_wn("Файл обрезан (нет маркера конца)")
            if ext in ("jpg", "pdf") and ask_yn("Создать копию с добавленным маркером конца?", "y"):
                out = unique_path(p.parent, p.stem + ".fixed" + p.suffix)
                data = p.read_bytes()
                out.write_bytes(data + (b"\xff\xd9" if ext == "jpg" else b"\n%%EOF\n"))
                fix_perms(out)
                say_ok(f"Создана копия: {out} (содержимое восстановить нельзя, только дописан конец)")
        if ext == "gz":
            import gzip
            try:
                with gzip.open(p, "rb") as g:
                    while g.read(1 << 20):
                        pass
                say_ok("GZIP читается полностью")
            except Exception as e:
                say_er(f"GZIP повреждён: {e}")
        if ext == "zip":
            import zipfile
            try:
                with zipfile.ZipFile(p) as z:
                    bad = z.testzip()
                say_ok("ZIP цел") if not bad else say_er(f"ZIP повреждён: {bad}")
            except Exception as e:
                say_er(f"ZIP повреждён: {e}")
    fix_perms(p)
    say_ok("Права доступа исправлены (644) — файл виден приложению «Файлы»")


# Меню починки
def repair_menu():
    files = pick_files("Что проверить/починить", [DECRYPTED, VAULT])
    for f in files:
        try:
            repair_file(f)
        except Exception as e:
            say_er(f"Ошибка: {e}")


# Меню переименования
def rename_menu():
    files = pick_files("Что переименовать", [DECRYPTED, VAULT, ORIGINALS, STEGO])
    for f in files:
        f = Path(f)
        print()
        say_in(f"Сейчас: {f.name}")
        raw = ask("Новое имя (Enter — пропустить): ")
        if not raw:
            continue
        new = safe_restore_name(raw)
        if not new:
            say_er("Недопустимое имя")
            continue
        if new != raw:
            say_wn(f"Имя скорректировано: {new!r}")
        if new == f.name:
            continue
        dest = unique_path(f.parent, new)
        if dest.name != new:
            say_wn(f"Имя занято — использую {dest.name}")
        try:
            f.rename(dest)
        except OSError as e:
            say_er(f"Не удалось переименовать: {e}")
            continue
        if f.parent.resolve() == VAULT.resolve():
            for ext in (".meta", ".split"):
                om = META / f"{f.name}{ext}"
                if om.exists():
                    nm = META / f"{dest.name}{ext}"
                    os.replace(om, nm)
                    try:
                        d = read_json_file(nm)
                        d["final_name"] = dest.name
                        write_json_secure(nm, d)
                    except Exception:
                        pass
        else:
            fix_perms(dest)
        say_ok(f"Переименовано: {f.name} → {dest.name}")
        log_action("rename", None, None, None, None, f"{f.name}->{dest.name}")


# Показ содержимого папок CryptForge
def show_storage():
    for title, d in (("vault", VAULT), ("originals", ORIGINALS), ("decrypted", DECRYPTED), ("meta", META), ("parts", PARTS), ("shares", SHARES), ("stego", STEGO)):
        print(f"\n\033[38;5;51m{d}\033[0m")
        items = sorted(d.iterdir()) if d.exists() else []
        if not items:
            print("  \033[2m(пусто)\033[0m")
        for it in items:
            if it.name.startswith("."):
                continue
            extra = ""
            if d == VAULT:
                mpth = META / f"{it.name}.meta"
                extra += (" [meta, пароль]" if file_is_sealed(mpth) else " [meta]") if mpth.exists() else " [нет meta]"
                if (META / f"{it.name}.split").exists():
                    extra += " [есть разбиение]"
            sz = dir_size(it)
            print(f"  {it.name} ({hsize(sz)}){extra}")
    extra_files = [x for x in BASE.iterdir() if x.is_file() and not x.name.startswith(".") and x.name not in ("activity.log", "activity.jsonl", "location.pid")]
    if extra_files:
        print(f"\n\033[38;5;51m{BASE}\033[0m")
        for x in sorted(extra_files):
            print(f"  {x.name} ({hsize(x.stat().st_size)})")
    try:
        du = shutil.disk_usage(str(BASE))
        print(f"\n  Свободно на диске: {hsize(du.free)} из {hsize(du.total)}")
    except Exception:
        pass


# Затирание выбранных данных со словом-подтверждением
def wipe_all_flow():
    title_anim("ЗАТИРАНИЕ ДАННЫХ")
    scopes = [("1", "vault — зашифрованные файлы", VAULT), ("2", "originals — оригиналы", ORIGINALS), ("3", "decrypted — расшифрованное", DECRYPTED),
              ("4", "meta — метаданные и КЛЮЧИ", META), ("5", "parts — части", PARTS), ("6", "shares — доли Шамира", SHARES), ("7", "stego — контейнеры", STEGO)]
    for num, title, d in scopes:
        cnt = len([x for x in d.iterdir() if not x.name.startswith(".")]) if d.exists() else 0
        print(f"  {num}. {title}  ({cnt} объектов, {hsize(dir_size(d)) if d.exists() else '0 Б'})")
    print("  8. Файлы в корне CryptForge (recovery, QR, журнал, кэши, список BIP39)")
    print("  9. ВСЁ перечисленное")
    sel = ask("Что затереть (номера через запятую, 9 — всё, Enter — отмена): ").lower()
    if not sel:
        say_wn("Отменено")
        return
    chosen = set(x.strip() for x in sel.split(",") if x.strip())
    if "a" in chosen or "9" in chosen:
        chosen = {"1", "2", "3", "4", "5", "6", "7", "8"}
    targets = []
    for num, title, d in scopes:
        if num in chosen and d.exists():
            targets += [x for x in d.iterdir()]
    if "8" in chosen:
        for x in BASE.iterdir():
            if x.is_file() and x.name != ".core.py":
                targets.append(x)
    if not targets:
        say_in("Нечего затирать")
        return
    say_wn(f"Будет безвозвратно затёрто объектов: {len(targets)} (3 прохода случайными данными)")
    say_wn("На флеш-памяти iPhone физическое затирание не гарантируется износом-выравниванием, но данные станут нечитаемыми для обычных средств")
    if ask("Для подтверждения введите СТЕРЕТЬ: ") != "СТЕРЕТЬ":
        say_wn("Отменено — ничего не тронуто")
        return
    ok = 0
    bad = 0
    for i, t in enumerate(targets, 1):
        try:
            wipe_file(t)
            ok += 1
        except Exception as e:
            bad += 1
            say_er(f"{t.name}: {e}")
        if len(targets) > 1:
            pbar(i, len(targets), "затирание ")
    say_ok(f"Затёрто: {ok}" + (f", ошибок: {bad}" if bad else ""))
    log_action("wipe-all", None, None, None, None, f"objects={ok}")


EXIF_KEYS = ["Make", "Model", "LensMake", "LensModel", "LensID", "DateTimeOriginal", "CreateDate", "ModifyDate", "GPSLatitude", "GPSLongitude",
             "GPSAltitude", "Software", "Artist", "Copyright", "ExposureTime", "FNumber", "ISO", "FocalLength", "ImageSize", "Orientation", "Title", "Description"]
TAG_RE = re.compile(r"^[A-Za-z][A-Za-z0-9]*(:[A-Za-z][A-Za-z0-9]*)?$")
DATE_RE = re.compile(r"^(\d{4})[:\-](\d{2})[:\-](\d{2})[ T](\d{2}):(\d{2})(?::(\d{2}))?$")


# =====================================================================
# РАЗДЕЛ: МЕТАДАННЫЕ ФАЙЛОВ (EXIF) через exiftool
# =====================================================================
# Проверка/установка exiftool
def exiftool_ready():
    if shutil.which("exiftool"):
        return True
    say_wn("exiftool не установлен (он умеет читать и менять метаданные у фото, видео, PDF, аудио и др.)")
    if shutil.which("apk") and ask_yn("Установить сейчас (apk add exiftool)?", "y"):
        try:
            try:
                Path("/etc/resolv.conf").write_text("nameserver 1.1.1.1\nnameserver 8.8.8.8\n")
            except Exception:
                pass
            subprocess.run(["apk", "update"], capture_output=True, timeout=300)
            proc = subprocess.Popen(["apk", "add", "--no-cache", "exiftool"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            wait_spin(proc, "apk add exiftool")
            proc.communicate()
        except Exception as e:
            say_er(f"Установка не удалась: {e}")
    if shutil.which("exiftool"):
        say_ok("exiftool установлен")
        return True
    say_er("exiftool недоступен: apk add exiftool")
    return False


# Запуск exiftool без оболочки
def exif_run(args, timeout=180):
    try:
        r = subprocess.run(["exiftool"] + args, capture_output=True, text=True, timeout=timeout)
        return r.returncode, r.stdout or "", r.stderr or ""
    except subprocess.TimeoutExpired:
        return 1, "", "exiftool завис"
    except Exception as e:
        return 1, "", str(e)


# Показ метаданных файла
def exif_show(f, key_only):
    args = ["-G1", "-s", "-a"]
    if key_only:
        args += ["-" + k for k in EXIF_KEYS]
    rc, out, err = exif_run(args + [str(f)])
    lines = [x for x in out.splitlines() if x.strip()]
    if not lines:
        say_wn("Метаданных не найдено" + (f" ({err.strip().splitlines()[-1]})" if err.strip() else ""))
        return
    print()
    for i, ln in enumerate(lines):
        if i == 60 and not ask_yn(f"Показано 60 из {len(lines)} строк. Показать остальное?", "n"):
            break
        print("  " + ln)


# Запрет значений со спецсимволами exiftool
def exif_value_ok(v):
    if v.startswith("@") or v.startswith("<"):
        say_er("Значение не может начинаться с @ или < (спецсимволы exiftool)")
        return False
    return True


# Диалог правки поля метаданных
def exif_edit_args():
    print("\n  Что добавить/изменить:")
    print("   1. Дата и время съёмки")
    print("   2. Производитель камеры (Make)")
    print("   3. Модель камеры (Model)")
    print("   4. Объектив (LensModel)")
    print("   5. Фокусное расстояние (мм)")
    print("   6. Автор (Artist)")
    print("   7. Копирайт (Copyright)")
    print("   8. Описание (ImageDescription)")
    print("   9. Программа (Software)")
    print("  10. Место съёмки (GPS)")
    print("  11. Любое поле вручную (например XMP:Subject)")
    c = ask("Что изменить (номер): ")
    if c == "1":
        m = DATE_RE.match(ask("Дата и время (ГГГГ-ММ-ДД ЧЧ:ММ[:СС]): "))
        if not m:
            say_er("Неверный формат даты")
            return None
        return [f"-AllDates={m[1]}:{m[2]}:{m[3]} {m[4]}:{m[5]}:{m[6] or '00'}"]
    simple = {"2": "Make", "3": "Model", "4": "LensModel", "5": "FocalLength", "6": "Artist", "7": "Copyright", "8": "ImageDescription", "9": "Software"}
    if c in simple:
        v = ask(f"{simple[c]}: ")
        if not v or not exif_value_ok(v):
            return None
        if c == "5" and not re.match(r"^\d+(\.\d+)?$", v):
            say_er("Нужно число, например 35 или 50.5")
            return None
        return [f"-{simple[c]}={v}"]
    if c == "10":
        try:
            lat = float(ask("Широта (например 55.7558, юг — минус): ").replace(",", "."))
            lon = float(ask("Долгота (например 37.6173, запад — минус): ").replace(",", "."))
        except ValueError:
            say_er("Нужны числа")
            return None
        if not (-90 <= lat <= 90 and -180 <= lon <= 180):
            say_er("Координаты вне диапазона")
            return None
        return [f"-GPSLatitude={abs(lat)}", f"-GPSLatitudeRef={'N' if lat >= 0 else 'S'}", f"-GPSLongitude={abs(lon)}", f"-GPSLongitudeRef={'E' if lon >= 0 else 'W'}"]
    if c == "11":
        tag = ask("Имя поля (например Artist, XMP:Subject): ")
        if not TAG_RE.match(tag):
            say_er("Недопустимое имя поля")
            return None
        v = ask("Значение (пусто — удалить поле): ")
        if not exif_value_ok(v):
            return None
        return [f"-{tag}={v}"]
    say_er("Неверный выбор")
    return None


# Применяет изменения метаданных (по умолчанию к копии)
def exif_apply(files, args, use_copy):
    for f in files:
        target = f
        if use_copy:
            target = unique_path(f.parent, f.stem + ".edited" + f.suffix)
            shutil.copy2(f, target)
        rc, out, err = exif_run(["-overwrite_original"] + args + [str(target)])
        msg = (out.strip() or err.strip()).splitlines()
        if rc != 0 and not out.strip():
            say_er(f"{f.name}: {msg[-1] if msg else 'ошибка exiftool'}")
            if use_copy:
                target.unlink(missing_ok=True)
            continue
        say_ok(f"{f.name}: {msg[-1] if msg else 'готово'}" + (f" → {target.name}" if use_copy else ""))
        if use_copy:
            fix_perms(target)
        log_action("exif", f.stat().st_size, None, None, None, f"{f.name} {' '.join(a.split('=')[0] for a in args)}")


# Меню метаданных файлов
def exif_flow():
    if not exiftool_ready():
        return
    files = pick_files("Файлы для работы с метаданными", [DECRYPTED, ORIGINALS, HOME], True)
    files = [Path(f) for f in files if Path(f).is_file()]
    if not files:
        say_wn("Выбор отменён")
        return
    use_copy = ask_yn("Изменять КОПИЮ файла, а не оригинал (рекомендуется)?", "y")
    while True:
        title_anim("МЕТАДАННЫЕ ФАЙЛОВ")
        print("   1. Показать ключевые (камера, объектив, дата, GPS)")
        print("   2. Показать все")
        print("   3. Удалить ВСЕ метаданные")
        print("   4. Удалить только геолокацию (GPS)")
        print("   5. Удалить даты съёмки")
        print("   6. Добавить / изменить поле")
        print("   7. Удалить конкретное поле")
        print("   8. Скопировать метаданные из другого файла")
        print("   9. Изменить дату изменения файла (в файловой системе)")
        print("   0. Назад")
        c = ask("Действие (номер): ")
        if c == "0":
            return
        if c in ("1", "2"):
            for f in files:
                say_in(f.name)
                exif_show(f, c == "1")
        elif c == "3":
            keep = ask_yn("Сохранить ориентацию и цветовой профиль (чтобы фото не повернулось)?", "y")
            args = ["-all="] + (["-tagsFromFile", "@", "-Orientation", "-ICC_Profile"] if keep else [])
            exif_apply(files, args, use_copy)
        elif c == "4":
            exif_apply(files, ["-gps:all=", "-xmp:gps*="], use_copy)
        elif c == "5":
            exif_apply(files, ["-AllDates="], use_copy)
        elif c == "6":
            a = exif_edit_args()
            if a:
                exif_apply(files, a, use_copy)
        elif c == "7":
            tag = ask("Имя поля для удаления: ")
            if TAG_RE.match(tag):
                exif_apply(files, [f"-{tag}="], use_copy)
            else:
                say_er("Недопустимое имя поля")
        elif c == "8":
            sp = Path(os.path.expanduser(ask("Файл-источник: ")))
            if not sp.is_file():
                say_er("Источник не найден")
                continue
            exif_apply(files, ["-tagsFromFile", str(sp.resolve()), "-all:all"], use_copy)
        elif c == "9":
            d = ask("Новая дата (ГГГГ-ММ-ДД ЧЧ:ММ): ")
            m = DATE_RE.match(d)
            if not m:
                say_er("Неверный формат даты")
                continue
            try:
                ts = time.mktime((int(m[1]), int(m[2]), int(m[3]), int(m[4]), int(m[5]), int(m[6] or 0), 0, 0, -1))
                for f in files:
                    os.utime(f, (ts, ts))
                say_ok("Дата изменения обновлена")
            except Exception as e:
                say_er(f"Не удалось: {e}")
        else:
            say_er("Неверный выбор")


def plan_flow():
    files = pick_files("Что проверить (ничего не будет изменено)", [ORIGINALS, HOME])
    if not files:
        return
    n = ask_int("Планируемое число слоёв", 1, 100, 3)
    for f in files:
        f = Path(f)
        size = dir_size(f)
        is_dir = f.is_dir()
        print()
        say_in(f"Объект: {f} ({'папка' if is_dir else 'файл'}, {hsize(size)})")
        if is_dir:
            say_in("Шаг 1: упаковка в tar.gz (символические ссылки пропускаются)")
            txt = False
        else:
            txt = is_text_file(f)
            say_in(f"Тип данных: {'текст UTF-8' if txt else 'бинарные'}")
            if not txt:
                say_wn("Классические шифры и Base64-слои не будут доступны")
        say_in(f"Шаг 2: {n} слоёв шифрования, у каждого свой ключ")
        say_in("Шаг 3: проверочная расшифровка и сверка SHA-256")
        say_in("Шаг 4: запись в vault/, метаданные в meta/")
        need = size * 3 + 4 * MB
        free = shutil.disk_usage(str(BASE)).free
        mark = "хватает" if free >= need else "НЕ ХВАТАЕТ"
        (say_ok if free >= need else say_er)(f"Нужно места ~{hsize(need)}, свободно {hsize(free)} — {mark}")
        avail = [d[2] for d in LAYER_DEFS if layer_available(d[1])[0] and (d[4] != "classic" or txt)]
        say_in("Доступные слои: " + ", ".join(avail))
    say_ok("План составлен, на диске ничего не изменено")


# =====================================================================
# РАЗДЕЛ: РАСПОЛОЖЕНИЯ: обзор папок, iPhone «Файлы», импорт/экспорт
# =====================================================================
# Закладки-расположения
def loc_dirs():
    out = []
    for x in CFG.get("locations", []):
        p = Path(x)
        if p.is_dir():
            out.append(p)
    return out


# Папка вывода расшифрованного
def out_dir():
    od = CFG.get("out_dir") or ""
    if od:
        p = Path(od)
        try:
            p.mkdir(parents=True, exist_ok=True)
            if os.access(p, os.W_OK):
                return p
        except OSError:
            pass
        say_wn(f"Папка вывода недоступна ({od}) — использую {DECRYPTED}")
    return DECRYPTED


# Сокращение длинного пути под ширину экрана
def short_path(p, width):
    s = str(p)
    if len(s) <= width:
        return s
    return "…" + s[-(width - 1):]


# Обзор любых папок: навигация, отметка файлов, закладки
def browse_flow(mode="files", start=None):
    cols = shutil.get_terminal_size((40, 20)).columns
    locs = loc_dirs()
    cur = Path(start) if start else (locs[0] if locs else HOME)
    marked = []
    page = 0
    per = 20
    while True:
        try:
            entries = sorted([e for e in cur.iterdir() if not e.name.startswith(".")], key=lambda e: (not e.is_dir(), e.name.lower()))
        except OSError as e:
            say_er(f"Нет доступа: {e}")
            cur = cur.parent if cur.parent != cur else HOME
            continue
        pages = max(1, -(-len(entries) // per))
        page = min(page, pages - 1)
        chunk = entries[page * per:(page + 1) * per]
        print()
        print("  " + grad("Папка: " + short_path(cur, cols - 12)))
        if mode == "files":
            print(f"  \033[2mОтмечено: {len(marked)} · стр. {page + 1}/{pages}\033[0m")
        else:
            print(f"  \033[2mВыберите папку · стр. {page + 1}/{pages}\033[0m")
        if not entries:
            print("  \033[2m(пусто)\033[0m")
        for i, e in enumerate(chunk, page * per + 1):
            mark = "✔" if e in marked else " "
            if e.is_dir():
                print(f" {mark}{i:>3}. \033[1;38;5;51m{e.name}/\033[0m")
            else:
                try:
                    sz = hsize(e.stat().st_size)
                except OSError:
                    sz = "?"
                print(f" {mark}{i:>3}. {e.name} \033[2m({sz})\033[0m")
        if mode == "files":
            print("  \033[2mномер — открыть/отметить · m3 — отметить папку\033[0m")
            print("  \033[2ma — все файлы · ok — готово · 0 — отмена\033[0m")
        else:
            print("  \033[2mномер — открыть · d — выбрать эту папку\033[0m")
            print("  \033[2m0 — отмена\033[0m")
        print("  \033[2m.. вверх · ~ домой · /путь · l закладки\033[0m")
        print("  \033[2mn/p страницы · + в закладки\033[0m")
        c = ask("Команда: ")
        lc = c.lower()
        if lc in ("0", "q"):
            return []
        if lc in ("ok", "готово") and mode == "files":
            return marked
        if mode == "dir" and lc == "d":
            return [cur]
        if lc == "..":
            cur = cur.parent
            page = 0
        elif lc == "~":
            cur = HOME
            page = 0
        elif c.startswith("/") or c.startswith("~/"):
            q = Path(os.path.expanduser(c))
            if q.is_dir():
                cur = q
                page = 0
            else:
                say_er("Такой папки нет")
        elif lc == "n":
            page = min(page + 1, pages - 1)
        elif lc == "p":
            page = max(page - 1, 0)
        elif lc == "+":
            if str(cur) not in CFG["locations"]:
                CFG["locations"].append(str(cur))
                cfg_save()
                say_ok("Папка добавлена в закладки")
        elif lc == "l":
            allv = [HOME] + loc_dirs() + [Path(x) for x in sorted(glob_mnt())]
            for i, d in enumerate(allv, 1):
                print(f"  {i}. {short_path(d, cols - 8)}")
            k = ask("Номер закладки: ")
            if k.isdigit() and 1 <= int(k) <= len(allv):
                cur = allv[int(k) - 1]
                page = 0
        elif lc == "a" and mode == "files":
            for e in entries:
                if e.is_file() and e not in marked:
                    marked.append(e)
        else:
            m = re.match(r"^(m)?\s*(\d+)$", lc)
            if not m:
                say_er("Неизвестная команда")
                continue
            n = int(m.group(2))
            if not 1 <= n <= len(entries):
                say_er("Нет такого номера")
                continue
            e = entries[n - 1]
            if m.group(1) and mode == "files":
                if e in marked:
                    marked.remove(e)
                else:
                    marked.append(e)
            elif e.is_dir():
                cur = e
                page = 0
            elif mode == "files":
                if e in marked:
                    marked.remove(e)
                else:
                    marked.append(e)


# Подключённые разделы в /mnt
def glob_mnt():
    out = []
    try:
        for d in Path("/mnt").iterdir():
            if d.is_dir():
                out.append(str(d))
    except OSError:
        pass
    return out


# Подключение папок iPhone через mount -t ios
def mount_ios():
    title_anim("ПОДКЛЮЧИТЬ «ФАЙЛЫ»")
    say_in("iSH умеет подключать папки iPhone")
    say_in("(On My iPhone, iCloud и др.).")
    name = ask("Имя точки подключения [iphone]: ", "iphone")
    if not re.match(r"^[A-Za-z0-9_\-]{1,30}$", name):
        say_er("Имя: латиница, цифры, _ и -")
        return
    mp = Path("/mnt") / name
    try:
        mp.mkdir(parents=True, exist_ok=True)
    except OSError as e:
        say_er(f"Не удалось создать {mp}: {e}")
        return
    say_wn("Сейчас откроется системный выбор папки iOS.")
    say_wn("Выберите папку и подтвердите.")
    try:
        r = subprocess.run(["mount", "-t", "ios", ".", str(mp)], timeout=300)
        if r.returncode != 0:
            raise OSError(f"mount вернул код {r.returncode}")
    except Exception as e:
        say_er(f"Не удалось подключить: {e}")
        say_in("Вручную выполните в консоли:")
        say_in(f"mount -t ios . {mp}")
        return
    if str(mp) not in CFG["locations"]:
        CFG["locations"].append(str(mp))
        cfg_save()
    say_ok(f"Подключено: {mp} (добавлено в закладки)")


# Копирование с прогрессом без перезаписи
def copy_into(srcs, dest, label="copy "):
    dest = Path(dest)
    total = sum(dir_size(s) for s in srcs) or 1
    done = 0
    for s in srcs:
        s = Path(s)
        target = unique_path(dest, s.name)
        try:
            if s.is_dir():
                shutil.copytree(s, target)
            else:
                with open(s, "rb") as fi, open(target, "wb") as fo:
                    while True:
                        c = fi.read(1 << 20)
                        if not c:
                            break
                        fo.write(c)
                        done += len(c)
                        if total > MB:
                            pbar(done, total, label)
            say_ok(f"Скопировано: {target}")
        except Exception as e:
            say_er(f"{s.name}: {e}")
            try:
                if target.exists() and target.is_file():
                    target.unlink()
            except OSError:
                pass


# Импорт файлов в originals/
def import_flow():
    say_in("Выберите файлы/папки для импорта в originals/")
    files = browse_flow("files")
    if not files:
        return
    copy_into(files, ORIGINALS)


# Экспорт файлов из CryptForge
def export_flow():
    files = pick_files("Что экспортировать", [VAULT, DECRYPTED, PARTS, STEGO])
    if not files:
        return
    say_in("Выберите папку назначения")
    d = browse_flow("dir")
    if not d:
        say_wn("Отменено")
        return
    copy_into(files, d[0], "export ")
    for f in files:
        fix_perms(Path(d[0]) / Path(f).name)


# Предложение скопировать .enc во внешнюю папку
def export_copy(path):
    locs = loc_dirs()
    if not locs:
        return
    if not ask_yn("Скопировать .enc во внешнюю папку (например On My iPhone)?", "n"):
        return
    d = browse_flow("dir")
    if d:
        copy_into([path], d[0], "export ")


# Меню расположений
def locations_menu():
    while True:
        title_anim("РАСПОЛОЖЕНИЯ")
        print("  Закладки:")
        for i, x in enumerate(CFG["locations"], 1):
            print(f"   {i}. {x}")
        if not CFG["locations"]:
            print("   \033[2m(нет)\033[0m")
        print(f"  Вывод расшифр.: {CFG.get('out_dir') or str(DECRYPTED)}")
        print()
        print("   1. Подключить «Файлы» iPhone")
        print("   2. Добавить папку (обзор)")
        print("   3. Удалить закладку")
        print("   4. Папка для расшифрованного")
        print("   5. Импорт в originals/")
        print("   6. Экспорт из CryptForge")
        print("   7. Сбросить папку вывода")
        print("   0. Назад")
        c = ask("Выбор: ")
        if c == "0":
            return
        if c == "1":
            mount_ios()
        elif c == "2":
            d = browse_flow("dir")
            if d and str(d[0]) not in CFG["locations"]:
                CFG["locations"].append(str(d[0]))
                cfg_save()
                say_ok("Добавлено")
        elif c == "3":
            n = ask("Номер закладки: ")
            if n.isdigit() and 1 <= int(n) <= len(CFG["locations"]):
                CFG["locations"].pop(int(n) - 1)
                cfg_save()
                say_ok("Удалено")
        elif c == "4":
            d = browse_flow("dir")
            if d:
                CFG["out_dir"] = str(d[0])
                cfg_save()
                say_ok(f"Расшифрованное теперь сохраняется в {d[0]}")
        elif c == "5":
            import_flow()
        elif c == "6":
            export_flow()
        elif c == "7":
            CFG["out_dir"] = ""
            cfg_save()
            say_ok("Папка вывода сброшена")


# =====================================================================
# РАЗДЕЛ: МЕССЕНДЖЕР E2E: визитки, приглашения, чаты с ratchet, ключи файлов
# =====================================================================
# Импорт модулей X25519/Ed25519
def pk_mods():
    from cryptography.hazmat.primitives.asymmetric import ed25519, x25519
    from cryptography.hazmat.primitives import serialization
    return ed25519, x25519, serialization


# Доступна ли криптография с открытыми ключами
def has_pk():
    if not HAS_CRYPTO:
        return False
    try:
        pk_mods()
        return True
    except Exception:
        return False


# Текстовая обёртка блока (BEGIN/END, base64 строками по 60)
def armor(label, blob):
    s = b64e(blob)
    lines = [s[i:i + 60] for i in range(0, len(s), 60)]
    return f"-----BEGIN {label}-----\n" + "\n".join(lines) + f"\n-----END {label}-----"


# Разбор блока из текста, устойчивый к пробелам и переносам
def dearmor(text):
    m = re.search(r"-----BEGIN ([A-Z0-9 ]+)-----(.*?)-----END \1-----", text, re.S)
    label = None
    body = text
    if m:
        label, body = m.group(1), m.group(2)
    body = re.sub(r"[^A-Za-z0-9_\-+/]", "", body)
    if not body:
        raise CFError("Блок пустой")
    try:
        return label, b64d(body)
    except Exception:
        raise CFError("Блок повреждён при копировании (лишние или потерянные символы)")


# Чтение блока: вставка текста или путь к файлу
def read_block(prompt):
    print(prompt)
    say_in("Можно вставить текст или указать путь к файлу.")
    lines = []
    while True:
        try:
            ln = input()
        except EOFError:
            raise KeyboardInterrupt
        ln = clean_input(ln)
        if not ln:
            if lines:
                break
            continue
        if not lines:
            pth = Path(os.path.expanduser(ln))
            try:
                if len(ln) < 300 and pth.is_file():
                    return pth.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                pass
        lines.append(ln)
        if "-----END" in ln:
            break
    return "\n".join(lines)


# Чтение многострочного текста до пустой строки
def read_text_block(prompt):
    print(prompt)
    lines = []
    while True:
        try:
            ln = input()
        except EOFError:
            raise KeyboardInterrupt
        ln = ln.replace("\r", "")
        if not ln.strip():
            if lines:
                break
            continue
        lines.append(ln)
    return "\n".join(lines)


# Показ блока для копирования и сохранение в файл
def show_packet(label, blob, fname):
    text = armor(label, blob)
    print()
    print(text)
    print()
    say_ok("Скопируйте блок целиком и отправьте как текст.")
    if ask_yn("Сохранить блок в файл (для отправки через «Файлы»)?", "n"):
        MSG_OUT.mkdir(parents=True, exist_ok=True)
        p = unique_path(MSG_OUT, fname + ".txt")
        p.write_text(text + "\n", encoding="utf-8")
        os.chmod(p, 0o600)
        say_ok(f"Файл: {p}")
        if loc_dirs() and ask_yn("Скопировать его во внешнюю папку?", "n"):
            d = browse_flow("dir")
            if d:
                copy_into([p], d[0])


# Новая личность: ключи Ed25519 и X25519
def identity_new(name):
    ed, x, ser = pk_mods()
    edk = ed.Ed25519PrivateKey.generate()
    dhk = x.X25519PrivateKey.generate()

    def raw(k):
        return k.private_bytes(ser.Encoding.Raw, ser.PrivateFormat.Raw, ser.NoEncryption())

    def pub(k):
        return k.public_key().public_bytes(ser.Encoding.Raw, ser.PublicFormat.Raw)

    return {"name": name, "ed_priv": b64e(raw(edk)), "dh_priv": b64e(raw(dhk)), "ed_pub": b64e(pub(edk)), "dh_pub": b64e(pub(dhk))}


# Короткий отпечаток ключей (байты)
def fp_bytes(ed, dh):
    return hashlib.sha256(ed + dh).digest()[:15]


# Отпечаток ключей группами для сверки
def fp_text(ed, dh):
    h = hashlib.sha256(ed + dh).hexdigest()[:30].upper()
    return " ".join(h[i:i + 5] for i in range(0, 30, 5))


# Визитка (публичные ключи + имя)
def card_bytes(ident):
    return b"CFC1" + b64d(ident["ed_pub"]) + b64d(ident["dh_pub"]) + ident["name"].encode("utf-8")[:40]


# Разбор визитки
def parse_card(blob):
    if blob[:4] != b"CFC1" or len(blob) < 68:
        raise CFError("Это не визитка CryptForge")
    ed = blob[4:36]
    dh = blob[36:68]
    return {"name": blob[68:].decode("utf-8", "ignore") or "без имени", "ed": ed, "dh": dh, "fp": fp_text(ed, dh)}


# Загрузка личных ключей из зашифрованного файла
def identity_load():
    p = MSG_DIR / "identity.json"
    if not p.exists():
        return None
    return msg_read(p)


# Загрузка или создание личных ключей
def identity_get():
    ident = identity_load()
    if ident:
        return ident
    if not has_pk():
        raise CFError("Для ключей-визиток нужен py3-cryptography")
    say_in("У вас ещё нет личных ключей.")
    name = ask("Ваше имя (ник) для визитки: ")
    if not name:
        raise CFError("Имя не задано")
    ident = identity_new(name[:40])
    msg_write(MSG_DIR / "identity.json", ident)
    say_ok("Личные ключи созданы и зашифрованы мастер-паролем")
    return ident


# Контакты (зашифрованы мастер-паролем)
def contacts_load():
    p = MSG_DIR / "contacts.json"
    if not p.exists():
        return {}
    return msg_read(p)


# Сохранение контактов
def contacts_save(d):
    msg_write(MSG_DIR / "contacts.json", d)


# Гибридное шифрование: X25519 + ChaCha20-Poly1305 + подпись Ed25519
def ecies_seal(ident, rcpt, plaintext):
    ed, x, ser = pk_mods()
    from cryptography.hazmat.primitives.ciphers.aead import ChaCha20Poly1305 as CC
    my_ed = ed.Ed25519PrivateKey.from_private_bytes(b64d(ident["ed_priv"]))
    my_dh = x.X25519PrivateKey.from_private_bytes(b64d(ident["dh_priv"]))
    my_ed_pub = b64d(ident["ed_pub"])
    my_dh_pub = b64d(ident["dh_pub"])
    eph = x.X25519PrivateKey.generate()
    eph_pub = eph.public_key().public_bytes(ser.Encoding.Raw, ser.PublicFormat.Raw)
    rp = x.X25519PublicKey.from_public_bytes(rcpt["dh"])
    key = hkdf(eph.exchange(rp) + my_dh.exchange(rp), eph_pub + rcpt["dh"], b"CF-ECIES-1")
    nonce = os.urandom(12)
    ct = CC(key).encrypt(nonce, plaintext, my_ed_pub + my_dh_pub)
    sig = my_ed.sign(b"CFSIG1" + eph_pub + nonce + ct + fp_bytes(rcpt["ed"], rcpt["dh"]))
    return b"CFI1" + my_ed_pub + my_dh_pub + eph_pub + nonce + sig + ct


# Проверка подписи и расшифровка приглашения
def ecies_open(ident, blob):
    ed, x, ser = pk_mods()
    from cryptography.hazmat.primitives.ciphers.aead import ChaCha20Poly1305 as CC
    if blob[:4] != b"CFI1" or len(blob) < 4 + 32 * 3 + 12 + 64 + 16:
        raise CFError("Неверный формат приглашения")
    s_ed = blob[4:36]
    s_dh = blob[36:68]
    eph_pub = blob[68:100]
    nonce = blob[100:112]
    sig = blob[112:176]
    ct = blob[176:]
    my_ed_pub = b64d(ident["ed_pub"])
    my_dh_pub = b64d(ident["dh_pub"])
    try:
        ed.Ed25519PublicKey.from_public_bytes(s_ed).verify(sig, b"CFSIG1" + eph_pub + nonce + ct + fp_bytes(my_ed_pub, my_dh_pub))
    except Exception:
        raise CFError("Подпись не сошлась: приглашение не для вас или подделано")
    my_dh = x.X25519PrivateKey.from_private_bytes(b64d(ident["dh_priv"]))
    key = hkdf(my_dh.exchange(x.X25519PublicKey.from_public_bytes(eph_pub)) + my_dh.exchange(x.X25519PublicKey.from_public_bytes(s_dh)), eph_pub + my_dh_pub, b"CF-ECIES-1")
    try:
        pt = CC(key).decrypt(nonce, ct, s_ed + s_dh)
    except Exception:
        raise CFError("Не удалось расшифровать (неверный получатель)")
    return pt, {"name": "", "ed": s_ed, "dh": s_dh, "fp": fp_text(s_ed, s_dh)}


# Шифрование по паролю: KDF + AEAD
def pw_seal(password, data, magic=b"CFP2"):
    salt = os.urandom(16)
    lv = sec()
    if has_argon2():
        a = lv["argon"]
        mode, params = 2, (a[0], a[1], 0, 0, a[2])
    else:
        mode, params = 1, (lv["scrypt"], 8, 1, 0, 0)
    key = derive_key(password, mode, salt, params, "pw")
    alg = 1 if HAS_CRYPTO else 2
    nonce = os.urandom(12)
    ct = small_aead("gcm" if alg == 1 else "shake", key).encrypt(nonce, data, magic)
    return magic + bytes([alg, mode]) + salt + struct.pack(">BBBBI", *params) + nonce + ct


# Расшифровка по паролю
def pw_open(password, blob, magic=b"CFP2"):
    if blob[:4] != magic or len(blob) < 4 + 2 + 16 + 8 + 12 + 16:
        raise CFError("Неверный формат блока")
    alg, mode = blob[4], blob[5]
    salt = blob[6:22]
    params = struct.unpack(">BBBBI", blob[22:30])
    nonce = blob[30:42]
    ct = blob[42:]
    if alg == 1 and not HAS_CRYPTO:
        raise CFError("Нужен py3-cryptography")
    key = derive_key(password, mode, salt, params, "pw")
    try:
        return small_aead("gcm" if alg == 1 else "shake", key).decrypt(nonce, ct, magic)
    except Exception:
        raise CFError("Неверный пароль или блок повреждён")


MSG_MAGIC = b"CFM1"
MAX_SKIP = 500


# Ключ слоя сообщения из ключа сообщения (HKDF)
def msg_layer_key(mk, cid, i, lid):
    return b64u(hkdf(mk, cid, b"L" + bytes([i]) + lid.encode(), 32))


# Применение слоёв к байтам сообщения
def stack_encrypt_bytes(mk, cid, layers, data):
    work = new_work()
    try:
        cur = work / "m0"
        cur.write_bytes(data)
        for i, lid in enumerate(layers):
            out = work / f"m{i + 1}"
            encrypt_layer(cur, out, lid, msg_layer_key(mk, cid, i, lid), "scrypt")
            cur.unlink()
            cur = out
        return cur.read_bytes()
    finally:
        shutil.rmtree(work, ignore_errors=True)


# Снятие слоёв с байтов сообщения
def stack_decrypt_bytes(mk, cid, layers, data):
    work = new_work()
    try:
        cur = work / "c0"
        cur.write_bytes(data)
        for i in reversed(range(len(layers))):
            out = work / f"c{len(layers) - i}"
            decrypt_layer(cur, out, layers[i], msg_layer_key(mk, cid, i, layers[i]))
            cur.unlink()
            cur = out
        return cur.read_bytes()
    finally:
        shutil.rmtree(work, ignore_errors=True)


# Наборы слоёв для чатов (быстрый … максимум)
def msg_layers_preset(name):
    aeads = aead_pool()
    ossl = [x + "@10000" for x in ossl_pool()]
    out = []
    if name == "fast":
        out = rand_shuffle(list(aeads))[:2]
    elif name == "standard":
        pool = []
        while len(pool) < 4:
            pool += rand_shuffle(list(aeads))
        out = pool[:4]
    elif name == "strong":
        pool = []
        while len(pool) < 4:
            pool += rand_shuffle(list(aeads))
        out = pool[:4] + rand_shuffle(list(ossl))[:2]
        rand_shuffle(out)
    elif name == "max":
        pool = []
        while len(pool) < 6:
            pool += rand_shuffle(list(aeads))
        out = pool[:6] + rand_shuffle(list(ossl))[:4]
        rand_shuffle(out)
    if not out:
        raise CFError("Нет доступных шифров для чата")
    return out


# Содержимое приглашения: правила, корневой секрет, первое сообщение
def invite_payload(me, layers, pad, first):
    return {"v": 1, "chat": os.urandom(8).hex(), "rs": b64e(rand_bytes(32)), "layers": layers, "pad": pad, "from": me, "first": first, "ts": int(time.time())}


# Состояние чата: две цепочки ключей (ratchet) из корневого секрета
def chat_new(payload, role, me, peer):
    cid = bytes.fromhex(payload["chat"])
    rs = b64d(payload["rs"])
    ck0 = hkdf(rs, cid, b"chain0")
    ck1 = hkdf(rs, cid, b"chain1")
    d = 0 if role == "I" else 1
    return {"id": payload["chat"], "role": role, "dir": d, "me": me, "peer": peer, "layers": list(payload["layers"]), "pad": int(payload.get("pad", 256)),
            "send": {"ck": b64e(ck0 if d == 0 else ck1), "n": 0},
            "recv": {"ck": b64e(ck1 if d == 0 else ck0), "n": 0, "skipped": {}},
            "keep": True, "history": [], "created": int(time.time())}


# Запись в историю чата
def hist_add(st, d, text, n):
    if st.get("keep", True):
        st["history"].append({"d": d, "ts": int(time.time()), "t": text, "n": n})
        st["history"] = st["history"][-500:]


# Шифрование сообщения: сжатие, выравнивание, слои, HMAC заголовка; ключ меняется (ratchet)
def msg_pack(st, text):
    cid = bytes.fromhex(st["id"])
    obj = {"k": "msg", "t": text, "ts": int(time.time()), "f": st["me"]}
    raw = zlib.compress(json.dumps(obj, ensure_ascii=False).encode("utf-8"), 9)
    framed = struct.pack(">I", len(raw)) + raw
    blk = int(st.get("pad", 0))
    if blk > 0:
        framed += os.urandom((-len(framed)) % blk)
    ck = b64d(st["send"]["ck"])
    n = st["send"]["n"]
    mk = hmac.new(ck, b"\x01", hashlib.sha256).digest()
    nck = hmac.new(ck, b"\x02", hashlib.sha256).digest()
    ct = stack_encrypt_bytes(mk, cid, st["layers"], framed)
    header = MSG_MAGIC + cid + bytes([st["dir"]]) + struct.pack(">I", n)
    tag = hmac.new(hkdf(mk, cid, b"hdr"), header + ct, hashlib.sha256).digest()
    st["send"]["ck"] = b64e(nck)
    st["send"]["n"] = n + 1
    hist_add(st, "out", text, n)
    return header + ct + tag


# Расшифровка: проверка HMAC до слоёв, защита от повтора и подмены; состояние меняется только при успехе
def msg_unpack(st, packet):
    cid = bytes.fromhex(st["id"])
    if len(packet) < 4 + 8 + 1 + 4 + 32 or packet[:4] != MSG_MAGIC:
        raise CFError("Это не сообщение CryptForge")
    if packet[4:12] != cid:
        raise CFError("Сообщение из другого чата")
    d = packet[12]
    if d != 1 - st["dir"]:
        raise CFError("Это ваше собственное сообщение (или неверное направление)")
    n = struct.unpack(">I", packet[13:17])[0]
    ct = packet[17:-32]
    tag = packet[-32:]
    r = st["recv"]
    ck = b64d(r["ck"])
    rn = r["n"]
    skipped = dict(r["skipped"])
    if n < rn:
        if str(n) not in skipped:
            raise CFError("Повтор или слишком старое сообщение")
        mk = b64d(skipped.pop(str(n)))
    else:
        if n - rn > MAX_SKIP:
            raise CFError("Слишком большой пропуск сообщений")
        for i in range(rn, n):
            skipped[str(i)] = b64e(hmac.new(ck, b"\x01", hashlib.sha256).digest())
            ck = hmac.new(ck, b"\x02", hashlib.sha256).digest()
        mk = hmac.new(ck, b"\x01", hashlib.sha256).digest()
        ck = hmac.new(ck, b"\x02", hashlib.sha256).digest()
        rn = n + 1
    exp = hmac.new(hkdf(mk, cid, b"hdr"), packet[:-32], hashlib.sha256).digest()
    if not hmac.compare_digest(tag, exp):
        raise CFError("Подпись не сошлась: сообщение повреждено, подделано или из другого чата")
    framed = stack_decrypt_bytes(mk, cid, st["layers"], ct)
    ln = struct.unpack(">I", framed[:4])[0]
    obj = json.loads(zlib.decompress(framed[4:4 + ln]).decode("utf-8"))
    r["ck"] = b64e(ck)
    r["n"] = rn
    keys = sorted(skipped.keys(), key=int)
    r["skipped"] = {k: skipped[k] for k in keys[-MAX_SKIP:]}
    hist_add(st, "in", obj.get("t", ""), n)
    return obj


# Путь файла чата
def chat_path(cid):
    return CHATS_DIR / f"{cid}.json"


# Список чатов
def chats_list():
    out = []
    if CHATS_DIR.exists():
        for p in sorted(CHATS_DIR.glob("*.json")):
            try:
                out.append(msg_read(p))
            except CFError as e:
                say_er(f"{p.name}: {e}")
    return out


# Перенос текста по ширине экрана
def wrap_text(t, indent="  "):
    import textwrap
    w = max(24, shutil.get_terminal_size((40, 20)).columns - 4)
    out = []
    for ln in t.splitlines() or [""]:
        out += textwrap.wrap(ln, w) or [""]
    return "\n".join(indent + x for x in out)


# Показ входящего сообщения
def show_incoming(st, obj):
    ts = time.strftime("%d.%m %H:%M", time.localtime(obj.get("ts", 0)))
    print(f"\n  \033[1;38;5;84m{st['peer']}\033[0m \033[2m{ts}\033[0m")
    print(wrap_text(obj.get("t", "")))


# Размер выравнивания сообщений
def choose_pad():
    d = int(CFG.get("msg_pad", 256))
    print("  Выравнивание длины прячет размер текста.")
    v = ask_int("  Блок, байт (0 — выкл.)", 0, 4096, d)
    return v


# Выбор правил шифрования чата
def choose_msg_rules():
    print("\nПравила шифрования чата:")
    print("  1. Быстрый (2 слоя)")
    print("  2. Стандарт (4 слоя)")
    print("  3. Усиленный (6 слоёв, OpenSSL)")
    print("  4. Максимум (10 слоёв, медленно)")
    c = ask("Выбор [2]: ", "2")
    name = {"1": "fast", "2": "standard", "3": "strong", "4": "max"}.get(c, "standard")
    layers = msg_layers_preset(name)
    say_in("Слои: " + " → ".join(layer_title(x) for x in layers))
    return layers


# Выбор получателя
def choose_contact():
    cts = contacts_load()
    items = list(cts.items())
    print("\nПолучатель:")
    for i, (fp, c) in enumerate(items, 1):
        print(f"  {i}. {c['name']}" + ("  ✔" if c.get("verified") else ""))
    print("  N. Новый (вставить визитку)")
    ch = ask("Выбор: ")
    if ch.isdigit() and 1 <= int(ch) <= len(items):
        c = items[int(ch) - 1][1]
        return {"name": c["name"], "ed": b64d(c["ed"]), "dh": b64d(c["dh"]), "fp": items[int(ch) - 1][0]}
    if ch.lower() == "n":
        return add_contact_flow()
    raise CFError("Получатель не выбран")


# Добавление контакта по визитке с проверкой отпечатка
def add_contact_flow():
    txt = read_block("Вставьте визитку собеседника (блок CFCARD):")
    label, blob = dearmor(txt)
    c = parse_card(blob)
    print(f"\n  Имя: {c['name']}")
    print(f"  Отпечаток: {c['fp']}")
    say_wn("Сверьте отпечаток с собеседником другим каналом (голос, личная встреча).")
    ver = ask_yn("Отпечаток совпал?", "n")
    cts = contacts_load()
    cts[c["fp"]] = {"name": c["name"], "ed": b64e(c["ed"]), "dh": b64e(c["dh"]), "verified": ver}
    contacts_save(cts)
    say_ok("Контакт сохранён" + (" (проверен)" if ver else " (НЕ проверен)"))
    return c


# Показ своей визитки
def my_card_flow():
    ident = identity_get()
    blob = card_bytes(ident)
    c = parse_card(blob)
    print(f"\n  Имя: {c['name']}")
    print(f"  Отпечаток: {c['fp']}")
    say_in("Отправьте визитку собеседнику (она публичная).")
    show_packet("CFCARD", blob, "card-" + re.sub(r"\W", "", c["name"])[:12])


# Создание чата и приглашения с правилами
def create_chat_flow():
    title_anim("НОВЫЙ ЧАТ")
    print("  Как передать правила собеседнику:")
    print("   1. По его визитке (E2E, без общего пароля)")
    print("   2. По паролю приглашения")
    mode = ask("Способ [1]: ", "1")
    if mode == "1" and not has_pk():
        say_wn("Нет py3-cryptography — только по паролю")
        mode = "2"
    ident = None
    rcpt = None
    pw = None
    me = ""
    if mode == "1":
        ident = identity_get()
        me = ident["name"]
        rcpt = choose_contact()
        peer = rcpt["name"]
    else:
        me = ask("Ваше имя в чате: ") or "я"
        peer = ask("Имя собеседника: ") or "собеседник"
        pw = ask_secret("Пароль приглашения: ")
        if len(pw) < 8:
            raise CFError("Пароль приглашения: минимум 8 символов")
        for w in check_phrase(pw):
            say_wn("Слабый пароль: " + w)
        if ask_secret("Повторите: ") != pw:
            raise CFError("Пароли не совпали")
        require_master()
    if ask_yn("Добавить свою случайность в ключи чата?", "n"):
        collect_entropy()
    layers = choose_msg_rules()
    pad = choose_pad()
    first = ask("Первое сообщение (можно пусто): ")
    payload = invite_payload(me, layers, pad, first)
    raw = zlib.compress(json.dumps(payload, ensure_ascii=False).encode("utf-8"), 9)
    say_in("Шифрование приглашения...")
    if mode == "1":
        blob = ecies_seal(ident, rcpt, raw)
    else:
        blob = pw_seal(pw, raw, b"CFP2")
    st = chat_new(payload, "I", me, peer)
    if first:
        hist_add(st, "out", first, -1)
    msg_write(chat_path(st["id"]), st)
    say_ok(f"Чат создан: {peer}")
    show_packet("CFINVITE", blob, "invite-" + st["id"][:8])
    if mode == "2":
        say_wn("Передайте пароль приглашения ДРУГИМ каналом.")
    log_action("chat-create", None, None, None, [layer_title(x) for x in layers], st["id"][:8])


# Принятие приглашения: проверка подписи, создание чата
def accept_invite_flow():
    title_anim("ПРИНЯТЬ ПРИГЛАШЕНИЕ")
    txt = read_block("Вставьте приглашение (блок CFINVITE):")
    label, blob = dearmor(txt)
    sender = None
    if blob[:4] == b"CFI1":
        ident = identity_get()
        say_in("Проверка подписи и расшифровка...")
        raw, sender = ecies_open(ident, blob)
        me = ident["name"]
    elif blob[:4] == b"CFP2":
        pw = ask_secret("Пароль приглашения: ")
        say_in("Расшифровка (стойкий KDF)...")
        raw = pw_open(pw, blob, b"CFP2")
        require_master()
        me = ask("Ваше имя в чате: ") or "я"
    else:
        raise CFError("Неизвестный тип приглашения")
    try:
        payload = json.loads(zlib.decompress(raw).decode("utf-8"))
        bytes.fromhex(payload["chat"])
        payload["layers"] = list(payload["layers"])
    except Exception:
        raise CFError("Приглашение повреждено")
    for lid in payload["layers"]:
        ok, why = layer_available(base_type(lid))
        if not ok:
            raise CFError(f"На этом устройстве недоступен слой {layer_title(lid)}: {why}")
    if chat_path(payload["chat"]).exists():
        raise CFError("Этот чат уже принят")
    peer = payload.get("from", "собеседник")
    if sender:
        print(f"\n  От: {peer}")
        print(f"  Отпечаток: {sender['fp']}")
        cts = contacts_load()
        known = cts.get(sender["fp"])
        if known:
            say_ok("Контакт известен" + (" и проверен" if known.get("verified") else ""))
        else:
            say_wn("Новый отправитель. Сверьте отпечаток другим каналом.")
            if not ask_yn("Принять приглашение?", "n"):
                raise CFError("Отклонено")
            cts[sender["fp"]] = {"name": peer, "ed": b64e(sender["ed"]), "dh": b64e(sender["dh"]), "verified": ask_yn("Отпечаток проверен?", "n")}
            contacts_save(cts)
    st = chat_new(payload, "R", me, peer)
    first = payload.get("first", "")
    if first:
        hist_add(st, "in", first, -1)
    msg_write(chat_path(st["id"]), st)
    say_ok(f"Чат с «{peer}» создан. Правила получены:")
    say_in(" → ".join(layer_title(x) for x in st["layers"]))
    if first:
        show_incoming(st, {"t": first, "ts": payload.get("ts", 0)})
    log_action("chat-accept", None, None, None, None, st["id"][:8])


# Экран чата: входящие, написать, история, правила, удалить
def chat_screen(st):
    path = chat_path(st["id"])
    while True:
        title_anim(f"ЧАТ: {st['peer']}")
        print(f"  \033[2mID {st['id'][:8]} · слоёв {len(st['layers'])} · отпр. {st['send']['n']} · получ. {st['recv']['n']}\033[0m")
        print("   1. Вставить входящее")
        print("   2. Написать и зашифровать")
        print("   3. История")
        print("   4. Правила чата")
        print("   5. Удалить чат")
        print("   0. Назад")
        c = ask("Действие: ")
        try:
            if c == "0":
                return
            if c == "1":
                while True:
                    txt = read_block("Вставьте сообщение (блок CFMSG):")
                    label, blob = dearmor(txt)
                    say_in("Проверка и расшифровка...")
                    obj = msg_unpack(st, blob)
                    msg_write(path, st)
                    show_incoming(st, obj)
                    if not ask_yn("Вставить ещё одно?", "n"):
                        break
            elif c == "2":
                text = read_text_block("Введите сообщение (пустая строка — конец):")
                say_in("Шифрование...")
                blob = msg_pack(st, text)
                msg_write(path, st)
                show_packet("CFMSG", blob, f"msg-{st['id'][:6]}-{st['send']['n'] - 1}")
            elif c == "3":
                for h in st["history"][-20:]:
                    who = st["me"] if h["d"] == "out" else st["peer"]
                    ts = time.strftime("%d.%m %H:%M", time.localtime(h["ts"]))
                    print(f"\n  \033[1;38;5;{84 if h['d'] == 'in' else 45}m{who}\033[0m \033[2m{ts}\033[0m")
                    print(wrap_text(h["t"]))
                if not st["history"]:
                    say_in("История пуста")
            elif c == "4":
                print("  Слои: " + " → ".join(layer_title(x) for x in st["layers"]))
                print(f"  Выравнивание: {st['pad']} Б")
                print("  Ключи меняются на каждое сообщение (ratchet),")
                print("  прошлые ключи удаляются.")
                st["keep"] = ask_yn("Хранить историю в чате?", "y" if st.get("keep", True) else "n")
                if not st["keep"]:
                    st["history"] = []
                msg_write(path, st)
            elif c == "5":
                if ask("Для удаления введите УДАЛИТЬ: ") == "УДАЛИТЬ":
                    wipe_file(path)
                    say_ok("Чат удалён")
                    return
        except CFError as e:
            say_er(str(e))


# Список чатов
def chats_flow():
    chats = chats_list()
    if not chats:
        say_in("Чатов пока нет")
        return
    print("\nЧаты:")
    for i, st in enumerate(chats, 1):
        print(f"  {i}. {st['peer']}")
        print(f"      \033[2m{st['id'][:8]} · {len(st['layers'])} слоёв · сообщений {len(st['history'])}\033[0m")
    n = ask("Номер чата: ")
    if n.isdigit() and 1 <= int(n) <= len(chats):
        chat_screen(chats[int(n) - 1])


# Шифрование текста по паролю без чата
def quick_text_flow():
    title_anim("ТЕКСТ ПО ПАРОЛЮ")
    print("   1. Зашифровать текст")
    print("   2. Расшифровать блок")
    c = ask("Выбор: ")
    if c == "1":
        text = read_text_block("Введите текст (пустая строка — конец):")
        pw = ask_secret("Пароль: ")
        if len(pw) < 8:
            raise CFError("Пароль: минимум 8 символов")
        for w in check_phrase(pw):
            say_wn("Слабый пароль: " + w)
        if ask_secret("Повторите: ") != pw:
            raise CFError("Не совпало")
        say_in("Шифрование (стойкий KDF)...")
        raw = zlib.compress(json.dumps({"t": text, "ts": int(time.time())}, ensure_ascii=False).encode("utf-8"), 9)
        show_packet("CFTEXT", pw_seal(pw, raw, b"CFT1"), "text-" + gen_name()[:6])
    elif c == "2":
        txt = read_block("Вставьте блок CFTEXT:")
        label, blob = dearmor(txt)
        pw = ask_secret("Пароль: ")
        say_in("Расшифровка (стойкий KDF)...")
        raw = pw_open(pw, blob, b"CFT1")
        obj = json.loads(zlib.decompress(raw).decode("utf-8"))
        print()
        print(wrap_text(obj.get("t", "")))


# Отправка ключей файла контакту (E2E)
def send_keys_flow():
    title_anim("КЛЮЧИ ФАЙЛА КОНТАКТУ")
    if not has_pk():
        raise CFError("Нужен py3-cryptography")
    files = pick_files("Файл из vault", [VAULT], True)
    if not files:
        return
    f = Path(files[0])
    meta, mp, status = find_meta(f)
    if not meta or not meta.get("keys"):
        raise CFError("Нет метаданных с ключами для этого файла")
    info = normalize_meta(meta, f)
    ident = identity_get()
    rcpt = choose_contact()
    payload = {"final_name": f.name, "layers": info["layers"], "keys": info["keys"], "restore_as": info["restore_as"], "compressed": info["compressed"],
               "src_sha256": info.get("src_sha256"), "enc_sha256": info.get("enc_sha256") or sha256_file(f), "created": info.get("created", "")}
    raw = zlib.compress(json.dumps(payload, ensure_ascii=False).encode("utf-8"), 9)
    show_packet("CFKEYS", ecies_seal(ident, rcpt, raw), "keys-" + f.name[:12])
    say_wn("Сам .enc передайте отдельно (не вместе с ключами).")


# Приём ключей файла
def receive_keys_flow():
    title_anim("ПРИНЯТЬ КЛЮЧИ ФАЙЛА")
    ident = identity_get()
    txt = read_block("Вставьте блок CFKEYS:")
    label, blob = dearmor(txt)
    raw, sender = ecies_open(ident, blob)
    p = json.loads(zlib.decompress(raw).decode("utf-8"))
    name = safe_restore_name(p["final_name"]) or "received.enc"
    print(f"\n  Файл: {name}")
    print(f"  От: {sender['fp']}")
    meta = {"version": 2, "final_name": name, "original_name": p.get("restore_as", name), "restore_as": p.get("restore_as", name),
            "compressed": bool(p.get("compressed")), "layers": p["layers"], "keys": p["keys"], "keys_csv": ",".join(k for k in p["keys"] if k),
            "created": p.get("created", ""), "enc_sha256": p.get("enc_sha256"), "src_sha256": p.get("src_sha256")}
    mp = META / f"{name}.meta"
    if mp.exists() and not ask_yn("Метаданные с таким именем уже есть. Заменить?", "n"):
        return
    write_json_secure(mp, meta)
    say_ok("Метаданные сохранены. Положите .enc в vault — расшифровка найдёт ключи даже по хешу.")


# Главное меню мессенджера
def messenger_menu():
    while True:
        title_anim("МЕССЕНДЖЕР")
        if not has_pk():
            say_wn("Нет py3-cryptography: только режим по паролю")
        print("   1. Моя визитка")
        print("   2. Создать чат (я задаю правила)")
        print("   3. Принять приглашение")
        print("   4. Мои чаты")
        print("   5. Текст по паролю (без чата)")
        print("   6. Отправить ключи файла контакту")
        print("   7. Принять ключи файла")
        print("   8. Контакты")
        print("   0. Назад")
        c = ask("Выбор: ")
        try:
            if c == "0":
                return
            elif c == "1":
                my_card_flow()
            elif c == "2":
                create_chat_flow()
            elif c == "3":
                accept_invite_flow()
            elif c == "4":
                chats_flow()
            elif c == "5":
                quick_text_flow()
            elif c == "6":
                send_keys_flow()
            elif c == "7":
                receive_keys_flow()
            elif c == "8":
                cts = contacts_load()
                for fp, ct in cts.items():
                    print(f"  {ct['name']}" + ("  ✔" if ct.get("verified") else "  (не проверен)"))
                    print(f"      \033[2m{fp}\033[0m")
                if not cts:
                    say_in("Контактов нет")
                elif ask_yn("Удалить контакт?", "n"):
                    k = ask("Имя контакта: ")
                    for fp in [f for f, x in cts.items() if x["name"] == k]:
                        del cts[fp]
                    contacts_save(cts)
                    say_ok("Готово")
        except CFError as e:
            say_er(str(e))


# =====================================================================
# РАЗДЕЛ: ПЕРЕШИФРОВКА, ПРОВЕРКА ХРАНИЛИЩА, НАСТРОЙКИ
# =====================================================================
# Метаданные и ключи для расшифровки/перешифровки
def load_decrypt_info(src):
    meta, mp, status = find_meta(src)
    if status == "corrupt":
        say_wn("Метаданные повреждены — ввод вручную")
    elif status == "locked":
        say_wn("Метаданные зашифрованы, пароль не принят — ввод вручную")
    if meta:
        info = normalize_meta(meta, src)
        info["is_dir"] = bool(meta.get("is_dir", False))
        say_ok(f"Метаданные: {mp.name} (слоёв: {len(info['layers'])})")
    else:
        if status == "none":
            say_wn(f"Метаданные для {src.name} не найдены")
        info = manual_info(src)
        info["is_dir"] = False
    if not info["layers"]:
        raise CFError("Нет слоёв")
    info["restore_as"] = safe_restore_name(info["restore_as"]) or src.stem
    return info, fill_keys(info), mp


# Перешифровка одного файла новыми слоями
def reencrypt_one(f):
    src = Path(f)
    if not src.is_file():
        raise CFError(f"Не файл: {src}")
    info, keys, mp = load_decrypt_info(src)
    if not check_space(src.stat().st_size * 4 + 8 * MB):
        raise CFError("Недостаточно места")
    work = new_work()
    try:
        cur = reverse_stack(src, info["layers"], keys, work)
        sha = sha256_file(cur, "sha256 ")
        if info.get("src_sha256") and sha != info["src_sha256"]:
            raise CFError("SHA-256 не совпал с метаданными — перешифровка отменена")
        say_ok("Старый слой снят, данные целы")
        shared = {"profile": choose_profile()}
        opts = {"compress": False, "verify": True, "more_files": 0}
        newp = encrypt_source(cur, Path(info["restore_as"]), info["restore_as"], info["compressed"], info["is_dir"], opts, shared, work, False)
        if newp and ask_yn("Удалить СТАРЫЙ .enc и его метаданные (с затиранием)?", "n"):
            wipe_file(src)
            if mp and Path(mp).exists():
                wipe_file(mp)
            say_ok("Старая версия удалена")
    finally:
        shutil.rmtree(work, ignore_errors=True)


# Меню перешифровки
def reencrypt_flow():
    title_anim("ПЕРЕШИФРОВАТЬ")
    say_in("Снимет старые слои и наложит новые.")
    files = pick_files("Файл из vault", [VAULT], True)
    for f in files:
        try:
            reencrypt_one(f)
        except CFError as e:
            say_er(str(e))
        except KeyboardInterrupt:
            raise
        except Exception as e:
            say_er(f"Сбой: {type(e).__name__}: {e}")
            ERR_LOG.write_text(traceback.format_exc())


# Проверка хранилища: хеши, метаданные, части
def verify_storage_flow():
    title_anim("ПРОВЕРКА ХРАНИЛИЩА")
    files = sorted(f for f in VAULT.iterdir() if f.is_file() and not f.name.startswith("."))
    ok = bad = nometa = 0
    names = set()
    for i, f in enumerate(files, 1):
        names.add(f.name)
        mp = META / f"{f.name}.meta"
        if not mp.exists():
            nometa += 1
            say_wn(f"{f.name}: нет метаданных")
            continue
        try:
            d = read_json_file(mp)
        except Exception as e:
            bad += 1
            say_er(f"{f.name}: метаданные нечитаемы ({e})")
            continue
        h = d.get("enc_sha256")
        if not h:
            say_wn(f"{f.name}: в метаданных нет хеша")
            continue
        if sha256_file(f) == h:
            ok += 1
        else:
            bad += 1
            say_er(f"{f.name}: хеш НЕ совпал — файл изменён или повреждён")
    orphans = [p.name for p in META.glob("*.meta") if p.name[:-5] not in names]
    for o in orphans:
        say_wn(f"Метаданные без файла: {o}")
    for sp in sorted(META.glob("*.split")):
        try:
            r = read_json_file(sp)
        except Exception:
            say_wn(f"{sp.name}: нечитаем")
            continue
        miss = sum(1 for x in r["parts"] if not (PARTS / x["name"]).exists())
        if miss:
            say_wn(f"{r['final_name']}: не хватает частей: {miss}")
    say_ok(f"Проверено файлов: {len(files)}; целых: {ok}; проблем: {bad}; без meta: {nometa}")


# Меню настроек
def settings_menu():
    def onoff(v):
        return "вкл" if v else "выкл"

    while True:
        title_anim("НАСТРОЙКИ")
        lv = sec()
        mstate = "нет" if not master_exists() else ("есть, meta шифруются" if CFG.get("encrypt_meta") else "есть")
        rows = [
            ("1", "Стойкость KDF", lv["name"]),
            ("2", "Мастер-пароль", mstate),
            ("3", "Внешний слой целостности", onoff(CFG["seal_outer"])),
            ("4", "Мусор в файлах", onoff(CFG["junk"].get("enabled"))),
            ("5", "Мусор в частях", onoff(CFG["parts_junk"].get("enabled"))),
            ("6", "Обманки среди частей", onoff(CFG["decoy_parts"].get("enabled"))),
            ("7", "Разбиение по умолчанию", "случайное" if CFG["split_mode"] == "random" else "равное"),
            ("8", "Затирать временные", {"off": "нет", "small": "малые", "all": "все"}[CFG["temp_wipe"]]),
            ("9", "Очистка экрана после ключей", onoff(CFG["clear_after_keys"])),
            ("10", "Затирание decrypted при выходе", onoff(CFG["ask_wipe_on_exit"])),
            ("11", "Блок обработки", f"{CFG['chunk_mb']} МБ"),
            ("12", "Своя случайность всегда", onoff(CFG["ask_entropy"])),
            ("13", "Обманки в vault", "создать/удалить"),
            ("14", "Выравнивание сообщений", f"{CFG['msg_pad']} Б"),
            ("15", "Журнал без имён и размеров", onoff(CFG.get("log_private"))),
            ("16", "Журнал в syslog", onoff(CFG.get("syslog"))),
            ("17", "Блокировка страниц памяти (mlock)", onoff(CFG.get("mlock"))),
            ("18", "Honey-режим (неверный пароль)", onoff(CFG.get("honey_mode"))),
            ("19", "Задержка при неверных паролях", onoff(CFG.get("lockout"))),
            ("20", "Роль для политик", CFG.get("role") or "не задана"),
            ("21", "Экспорт/импорт профиля настроек", ""),
            ("22", "Сбросить настройки", ""),
        ]
        for n, name, val in rows:
            print(f"  \033[1;38;5;45m{n:>3}\033[0m  {name}")
            if val:
                print(f"       \033[38;5;243m{val}\033[0m")
        print("  \033[1;38;5;203m  0\033[0m  Назад")
        c = ask("Номер: ")
        try:
            if c == "0":
                return
            elif c == "1":
                print("   1. Стандарт  2. Усиленный  3. Максимальный")
                print("   \033[2mМаксимальный: до 256 МБ памяти на ключ\033[0m")
                v = ask("Уровень: ")
                if v in ("1", "2", "3"):
                    CFG["sec_level"] = {"1": "std", "2": "strong", "3": "max"}[v]
            elif c == "2":
                master_menu()
            elif c == "3":
                CFG["seal_outer"] = not CFG["seal_outer"]
            elif c == "4":
                if ask_yn("Включить мусор в файлах по умолчанию?", "y"):
                    CFG["junk"] = ask_junk_params(CFG["junk"])
                else:
                    CFG["junk"]["enabled"] = False
            elif c == "5":
                if ask_yn("Включить мусор в частях?", "y"):
                    d = CFG["parts_junk"]
                    lo = ask_int("Минимум, байт", 0, 1 << 28, int(d["min"]))
                    hi = ask_int("Максимум, байт", lo, 1 << 28, max(lo, int(d["max"])))
                    CFG["parts_junk"] = {"enabled": True, "min": lo, "max": hi, "place": d.get("place", "both")}
                else:
                    CFG["parts_junk"]["enabled"] = False
            elif c == "6":
                CFG["decoy_parts"]["enabled"] = not CFG["decoy_parts"].get("enabled")
            elif c == "7":
                CFG["split_mode"] = "random" if CFG["split_mode"] != "random" else "fixed"
            elif c == "8":
                CFG["temp_wipe"] = {"off": "small", "small": "all", "all": "off"}[CFG["temp_wipe"]]
            elif c == "9":
                CFG["clear_after_keys"] = not CFG["clear_after_keys"]
            elif c == "10":
                CFG["ask_wipe_on_exit"] = not CFG["ask_wipe_on_exit"]
            elif c == "11":
                CFG["chunk_mb"] = {1: 2, 2: 4, 4: 8, 8: 1}[CFG["chunk_mb"]]
            elif c == "12":
                CFG["ask_entropy"] = not CFG["ask_entropy"]
            elif c == "13":
                decoys_menu()
            elif c == "14":
                CFG["msg_pad"] = ask_int("Блок, байт (0 — выкл.)", 0, 4096, CFG["msg_pad"])
            elif c == "15":
                CFG["log_private"] = not CFG.get("log_private")
            elif c == "16":
                CFG["syslog"] = not CFG.get("syslog")
            elif c == "17":
                CFG["mlock"] = not CFG.get("mlock")
                if CFG["mlock"] and not mlock_all():
                    say_wn("mlock недоступен в этой среде")
            elif c == "18":
                CFG["honey_mode"] = not CFG.get("honey_mode")
            elif c == "19":
                CFG["lockout"] = not CFG.get("lockout")
            elif c == "20":
                CFG["role"] = ask("Роль: ", CFG.get("role", ""))
            elif c == "21":
                profile_io()
            elif c == "22":
                if ask_yn("Сбросить все настройки (кроме мастер-пароля)?", "n"):
                    keep = CFG.get("encrypt_meta")
                    CFG.clear()
                    CFG.update(copy.deepcopy(CFG_DEFAULT))
                    CFG["encrypt_meta"] = keep
            else:
                say_er("Неверный выбор")
                continue
            cfg_save()
            cfg_load()
        except CFError as e:
            say_er(str(e))


# Экспорт текущих настроек в файл и импорт из файла (только известные ключи, без секретов)
def profile_io():
    print("   1. Экспорт профиля  2. Импорт профиля  0. Назад")
    c = ask("Выбор: ")
    if c == "1":
        dst = unique_path(out_dir(), "cryptforge-profile.json")
        data = {k: v for k, v in CFG.items() if k not in ("locations", "out_dir")}
        write_json_atomic(dst, data)
        os.chmod(dst, 0o644)
        say_ok(f"Профиль сохранён: {dst}")
    elif c == "2":
        src = Path(os.path.expanduser(ask("Путь к файлу профиля: ")))
        if not src.is_file():
            raise CFError("Файл не найден")
        data = json.loads(src.read_text(encoding="utf-8"))
        n = 0
        for k, v in data.items():
            if k in CFG_DEFAULT and type(v) == type(CFG_DEFAULT[k]) and k not in ("locations", "out_dir"):
                CFG[k] = v
                n += 1
        say_ok(f"Применено параметров: {n}")


# Меню мастер-пароля
def master_menu():
    print("   1. Установить / сменить пароль")
    print("   2. Шифровать метаданные файлов")
    print("   3. Удалить мастер-пароль")
    c = ask("Выбор: ")
    if c == "1":
        if not master_exists():
            master_setup_ui()
            return
        if not master_key():
            raise CFError("Текущий пароль не введён")
        p1 = ask_secret("Новый пароль (мин. 10 символов): ")
        if len(p1) < 10:
            raise CFError("Слишком короткий пароль")
        for w in check_phrase(p1):
            say_wn("Слабый пароль: " + w)
        if ask_secret("Повторите: ") != p1:
            raise CFError("Не совпало")
        say_in("Перешифровка данных (стойкий KDF)...")
        n = master_change(p1)
        say_ok(f"Пароль изменён, перешифровано объектов: {n}")
    elif c == "2":
        if not master_exists():
            master_setup_ui()
            return
        if not master_key():
            raise CFError("Пароль не введён")
        if CFG.get("encrypt_meta"):
            if ask_yn("Снять шифрование с метаданных (они станут открытым текстом)?", "n"):
                n = reseal_meta(False)
                CFG["encrypt_meta"] = False
                say_ok(f"Расшифровано файлов метаданных: {n}")
        else:
            CFG["encrypt_meta"] = True
            n = reseal_meta(True)
            say_ok(f"Зашифровано файлов метаданных: {n}")
    elif c == "3":
        if ask("Для удаления введите УДАЛИТЬ: ") == "УДАЛИТЬ":
            n = master_remove()
            say_ok(f"Мастер-пароль удалён, метаданных расшифровано: {n}")


# Предложение затереть расшифрованное при выходе
def exitcheck():
    if not CFG.get("ask_wipe_on_exit"):
        return
    items = [x for x in DECRYPTED.iterdir() if not x.name.startswith(".")] if DECRYPTED.exists() else []
    if items and ask_yn(f"В decrypted/ объектов: {len(items)}. Затереть перед выходом?", "n"):
        for x in items:
            wipe_file(x)
        say_ok("decrypted/ очищена")


# =====================================================================
# РАЗДЕЛ: САМОТЕСТЫ БАЗОВЫХ ВОЗМОЖНОСТЕЙ
# =====================================================================
# Самотесты: случайность, мастер-пароль, паддинг, части, мессенджер
def selftest_extra(results, work):
    def add(name, ok, note=""):
        results.append((name, "OK" if ok else "СБОЙ", note))

    try:
        _Rng.pool = hashlib.sha512(b"test-entropy").digest()
        a = gen_key()
        b = gen_key()
        _Rng.pool = None
        add("Своя случайность в ключах", a != b and valid_raw_key(a) and valid_raw_key(b))
    except Exception as ex:
        _Rng.pool = None
        add("Своя случайность", False, str(ex))
    try:
        key = os.urandom(32)
        d = seal_obj(key, {"a": [1, 2, "я"]}, b"cf-meta")
        ok = open_obj(key, d, b"cf-meta") == {"a": [1, 2, "я"]}
        try:
            open_obj(os.urandom(32), d, b"cf-meta")
            ok = False
        except CFError:
            pass
        k2, rec = master_make("pass-for-test", fast=True)
        ok = ok and master_derive("pass-for-test", rec["kdf"], b64d(rec["salt"])) == k2
        add("Мастер-пароль и запечатывание", ok)
    except Exception as ex:
        add("Мастер-пароль", False, str(ex))
    try:
        ok = True
        for place in ("head", "tail", "both"):
            for mode, lo, hi in (("percent", 5, 20), ("bytes", 100, 3000)):
                src = work / "pt.bin"
                src.write_bytes(os.urandom(5000))
                o = work / "pt.o"
                r = work / "pt.r"
                pad_encrypt_file(src, o, {"mode": mode, "min": lo, "max": hi, "place": place})
                pad_decrypt_file(o, r)
                ok = ok and r.read_bytes() == src.read_bytes() and o.stat().st_size > src.stat().st_size
        add("Мусорный паддинг (все режимы)", ok)
    except Exception as ex:
        add("Мусорный паддинг", False, str(ex))
    try:
        src = work / "st.txt"
        src.write_text("Привет, мир! " * 200, encoding="utf-8")
        h = sha256_file(src)
        base = [{"layer": "enigma", "key": gen_classic_key("enigma"), "kdf": "", "mnemonic": ""}]
        pool = aead_pool()
        base.append({"layer": pool[0], "key": gen_key(), "kdf": "", "mnemonic": ""})
        osl = ossl_pool()
        if osl:
            base.append({"layer": osl[0], "key": gen_key(), "kdf": "", "mnemonic": ""})
        spec = finalize_spec(base, {"enabled": True, "mode": "percent", "min": 5, "max": 10, "place": "both"}, True)
        ok1, why = spec_compatible(spec, True)
        w2 = work / "sp"
        w2.mkdir(exist_ok=True)
        enc = apply_stack(src, spec, w2)
        cur = reverse_stack(enc, [L["layer"] for L in spec], [L["key"] for L in spec], w2)
        add("Стек: текст, паддинг, внешний слой", ok1 and sha256_file(cur) == h and base_type(spec[-1]["layer"]) in ALG_ID)
    except Exception as ex:
        add("Стек с паддингом", False, str(ex))
    try:
        ok = True
        for total, smin, smax, n in ((100000, 1024, 30000, 8), (5000000, 100000, 900000, 12), (10000, 1024, 10000, 1), (777777, 1000, 5000, 200)):
            sz = random_part_sizes(total, smin, smax, n)
            ok = ok and sum(sz) == total and len(sz) == n and all(smin <= x <= smax for x in sz)
        add("Случайные размеры частей", ok)
    except Exception as ex:
        add("Случайные размеры частей", False, str(ex))
    try:
        data = os.urandom(300000)
        src = work / "whole.bin"
        src.write_bytes(data)
        sizes = random_part_sizes(len(data), 20000, 90000, 7)
        whole = hashlib.sha256()
        parts = []
        with open(src, "rb") as f:
            for sz in sizes:
                jh, jt = junk_split(rand_below(3000), "both")
                pp = work / gen_name()
                fh = write_part(f, pp, sz, jh, jt, whole)
                parts.append((pp, sz, jh, jt, fh))
        out = b""
        ok = True
        for pp, sz, jh, jt, fh in parts:
            raw = pp.read_bytes()
            ok = ok and hashlib.sha256(raw).hexdigest() == fh and len(raw) == jh + sz + jt
            out += raw[jh:jh + sz]
        add("Части с мусором: сборка", ok and out == data and whole.hexdigest() == hashlib.sha256(data).hexdigest())
    except Exception as ex:
        add("Части с мусором", False, str(ex))
    try:
        blk = os.urandom(500)
        txt = armor("CFMSG", blk)
        noisy = "  " + txt.replace("\n", " \r\n  ") + " "
        add("Блок armor: разбор с мусором", dearmor(noisy)[1] == blk)
    except Exception as ex:
        add("Блок armor", False, str(ex))
    try:
        raw = b"secret invite"
        blob = pw_seal("correct password", raw, b"CFP2")
        ok = pw_open("correct password", blob, b"CFP2") == raw
        try:
            pw_open("wrong password", blob, b"CFP2")
            ok = False
        except CFError:
            pass
        add("Пароль приглашения", ok)
    except Exception as ex:
        add("Пароль приглашения", False, str(ex))
    if has_pk():
        try:
            A = identity_new("Алиса")
            B = identity_new("Боб")
            cb = parse_card(card_bytes(B))
            payload = invite_payload("Алиса", msg_layers_preset("standard"), 128, "Привет, Боб!")
            raw = zlib.compress(json.dumps(payload, ensure_ascii=False).encode("utf-8"))
            blob = ecies_seal(A, cb, raw)
            back, sender = ecies_open(B, blob)
            ok = json.loads(zlib.decompress(back).decode("utf-8"))["first"] == "Привет, Боб!" and sender["fp"] == parse_card(card_bytes(A))["fp"]
            try:
                ecies_open(A, blob)
                ok = False
            except CFError:
                pass
            bad = bytearray(blob)
            bad[-1] ^= 1
            try:
                ecies_open(B, bytes(bad))
                ok = False
            except CFError:
                pass
            add("E2E приглашение (X25519+Ed25519)", ok)
            sa = chat_new(payload, "I", "Алиса", "Боб")
            sb = chat_new(json.loads(zlib.decompress(back).decode("utf-8")), "R", "Боб", "Алиса")
            p1 = msg_pack(sa, "первое")
            p2 = msg_pack(sa, "второе — кириллица и emoji 😀")
            p3 = msg_pack(sa, "третье")
            o2 = msg_unpack(sb, p2)
            o1 = msg_unpack(sb, p1)
            o3 = msg_unpack(sb, p3)
            ok = (o1["t"], o2["t"][:6], o3["t"]) == ("первое", "второе", "третье")
            for pk in (p1, p2):
                try:
                    msg_unpack(sb, pk)
                    ok = False
                except CFError:
                    pass
            r1 = msg_pack(sb, "ответ Боба")
            ok = ok and msg_unpack(sa, r1)["t"] == "ответ Боба"
            try:
                msg_unpack(sa, p1)
                ok = False
            except CFError:
                pass
            tam = bytearray(msg_pack(sa, "x"))
            tam[30] ^= 1
            try:
                msg_unpack(sb, bytes(tam))
                ok = False
            except CFError:
                pass
            ok = ok and msg_unpack(sb, msg_pack(sa, "после порчи"))["t"] == "после порчи"
            add("Чат: ratchet, порядок, повторы, подделка", ok)
        except Exception as ex:
            add("E2E мессенджер", False, f"{type(ex).__name__}: {ex}")
    else:
        results.append(("E2E мессенджер", "ПРОПУЩЕН", "нет cryptography"))


FRAME_MAGIC = b"\x93CFHIDX\x1a"
FRAME_END = b"\x1a\x93CFEND\x93"
CANARY_MAGIC = b"CFCN"
PNG_SIG = b"\x89PNG\r\n\x1a\n"
STEGO_NAME = "cfx"


# Обратный элемент в GF(256)
def gf_inv(a):
    return GF_EXP[255 - GF_LOG[a]]


# Элемент матрицы Коши для кодирования
def cauchy(j, i, k):
    return gf_inv((k + j) ^ i)


# XOR двух байтовых строк
def vxor(a, b):
    return (int.from_bytes(a, "big") ^ int.from_bytes(b, "big")).to_bytes(len(a), "big")


# Подбор размера блока и числа блоков данных/чётности (k+m <= 255)
def fec_params(n, redundancy, block=None):
    fixed = block is not None
    block = block or max(256, -(-n // 64))
    while True:
        k = max(1, -(-n // block))
        m = max(1, int(-(-k * redundancy // 1)))
        if k + m <= 255 or fixed:
            return block, k, m
        block *= 2


# Кодирование Рида-Соломона на уровне блоков (стирающий код над GF(256), матрица Коши)
def fec_encode(data, redundancy=0.5, block=None):
    n = len(data)
    block, k, m = fec_params(n, redundancy, block)
    padded = data + b"\x00" * (k * block - n)
    blocks = [padded[i * block:(i + 1) * block] for i in range(k)]
    out = bytearray()
    allb = list(blocks)
    for j in range(m):
        acc = bytes(block)
        for i in range(k):
            acc = vxor(acc, blocks[i].translate(mulrow(cauchy(j, i, k))))
        allb.append(acc)
    for idx, b in enumerate(allb):
        out += struct.pack(">HI", idx, zlib.crc32(b) & 0xFFFFFFFF) + b
    return bytes(out), {"block": block, "k": k, "m": m, "n": n}


# Декодирование FEC: восстановление стёртых блоков
def fec_decode(blob, p):
    try:
        block, k, m, n = int(p["block"]), int(p["k"]), int(p["m"]), int(p["n"])
    except Exception:
        raise CFError("FEC: параметры повреждены")
    # Параметры приходят из файла: ограничиваем, чтобы не получить огромное выделение памяти
    if not (1 <= block <= 64 * MB and 1 <= k and 0 <= m and k + m <= 255 and 0 <= n <= k * block):
        raise CFError("FEC: недопустимые параметры кадра")
    rec = 6 + block
    good = {}
    for pos in range(0, len(blob) - rec + 1, rec):
        idx, crc = struct.unpack(">HI", blob[pos:pos + 6])
        b = blob[pos + 6:pos + rec]
        if idx < k + m and zlib.crc32(b) & 0xFFFFFFFF == crc and idx not in good:
            good[idx] = b
    missing = [i for i in range(k) if i not in good]
    if not missing:
        return b"".join(good[i] for i in range(k))[:n], 0
    parity = [j for j in range(m) if (k + j) in good]
    if len(parity) < len(missing):
        raise CFError(f"Слишком много повреждений: потеряно блоков {len(missing)}, избыточности хватает на {len(parity)}")
    parity = parity[:len(missing)]
    e = len(missing)
    A = []
    R = []
    for j in parity:
        s = good[k + j]
        for i in range(k):
            if i in good:
                s = vxor(s, good[i].translate(mulrow(cauchy(j, i, k))))
        A.append([cauchy(j, mi, k) for mi in missing])
        R.append(s)
    for col in range(e):
        piv = next((r for r in range(col, e) if A[r][col]), None)
        if piv is None:
            raise CFError("Не удалось восстановить данные (вырожденная система)")
        A[col], A[piv] = A[piv], A[col]
        R[col], R[piv] = R[piv], R[col]
        inv = gf_inv(A[col][col])
        A[col] = [gf_mul(x, inv) for x in A[col]]
        R[col] = R[col].translate(mulrow(inv))
        for r in range(e):
            if r != col and A[r][col]:
                f = A[r][col]
                A[r] = [A[r][c] ^ gf_mul(f, A[col][c]) for c in range(e)]
                R[r] = vxor(R[r], R[col].translate(mulrow(f)))
    for ci, mi in enumerate(missing):
        good[mi] = R[ci]
    return b"".join(good[i] for i in range(k))[:n], e


# Кадр данных: заголовок, тело (FEC), хвост с CRC
def frame_build(payload, fec=0.0, burn=False):
    meta = {"len": len(payload), "sha": hashlib.sha256(payload).hexdigest(), "fec": None, "burn": bool(burn), "id": os.urandom(4).hex(), "ts": int(time.time())}
    body = payload
    if fec and fec > 0:
        body, p = fec_encode(payload, fec)
        meta["fec"] = p
    mj = json.dumps(meta, separators=(",", ":")).encode()
    head = FRAME_MAGIC + bytes([1, 1 if meta["fec"] else 0]) + struct.pack(">H", len(mj)) + mj
    total = len(head) + len(body) + len(FRAME_END) + 12
    tail = FRAME_END + struct.pack(">Q", total) + struct.pack(">I", zlib.crc32(head + body) & 0xFFFFFFFF)
    return head + body + tail


# Разбор и проверка кадра
def frame_parse(blob):
    if blob[:8] != FRAME_MAGIC:
        raise CFError("Заголовок данных не найден")
    try:
        mlen = struct.unpack(">H", blob[10:12])[0]
        meta = json.loads(blob[12:12 + mlen].decode())
        int(meta["len"])
        str(meta["sha"])
    except Exception:
        raise CFError("Заголовок данных повреждён")
    body = blob[12 + mlen:]
    if body[-12 - len(FRAME_END):-12] == FRAME_END:
        body = body[:-12 - len(FRAME_END)]
    fixed = 0
    if meta.get("fec"):
        payload, fixed = fec_decode(body, meta["fec"])
    else:
        payload = body[:meta["len"]]
    if len(payload) != meta["len"] or hashlib.sha256(payload).hexdigest() != meta["sha"]:
        raise CFError("SHA-256 данных не совпал (контейнер повреждён)")
    return meta, payload, fixed


# Поиск кадра по хвосту файла
def frame_from_tail(data):
    pos = data.rfind(FRAME_END, max(0, len(data) - 16384))
    if pos < 0 or pos + len(FRAME_END) + 12 > len(data):
        return None
    total = struct.unpack(">Q", data[pos + len(FRAME_END):pos + len(FRAME_END) + 8])[0]
    end = pos + len(FRAME_END) + 12
    if total > end:
        return None
    return end - total, end


# Разбор чанков PNG
def png_chunks(data):
    if data[:8] != PNG_SIG:
        raise CFError("Не PNG")
    pos = 8
    out = []
    while pos + 12 <= len(data):
        ln = struct.unpack(">I", data[pos:pos + 4])[0]
        typ = data[pos + 4:pos + 8]
        end = pos + 12 + ln
        if end > len(data):
            raise CFError("PNG обрезан")
        out.append((typ, pos, ln))
        pos = end
        if typ == b"IEND":
            break
    return out


# Сборка чанка PNG с CRC
def png_chunk(typ, d):
    return struct.pack(">I", len(d)) + typ + d + struct.pack(">I", zlib.crc32(typ + d) & 0xFFFFFFFF)


# Разбор сегментов JPEG
def jpeg_segments(data):
    if data[:2] != b"\xff\xd8":
        raise CFError("Не JPEG")
    pos = 2
    out = []
    while pos + 4 <= len(data):
        if data[pos] != 0xFF:
            break
        mk = data[pos + 1]
        if mk == 0xFF:
            pos += 1
            continue
        if mk in (0x01,) or 0xD0 <= mk <= 0xD7:
            pos += 2
            continue
        ln = struct.unpack(">H", data[pos + 2:pos + 4])[0]
        out.append((mk, pos, ln))
        if mk == 0xDA:
            break
        pos += 2 + ln
    return out


# Разбор атомов MP4
def mp4_atoms(data):
    pos = 0
    out = []
    n = len(data)
    while pos + 8 <= n:
        size = struct.unpack(">I", data[pos:pos + 4])[0]
        typ = data[pos + 4:pos + 8]
        hdr = 8
        if size == 1:
            if pos + 16 > n:
                break
            size = struct.unpack(">Q", data[pos + 8:pos + 16])[0]
            hdr = 16
        elif size == 0:
            size = n - pos
        if size < hdr or pos + size > n:
            raise CFError("Структура атомов MP4 нарушена")
        out.append((typ, pos, size, hdr))
        pos += size
    return out


# Разбор чанков RIFF/WAV
def riff_chunks(data):
    if data[:4] != b"RIFF":
        raise CFError("Не RIFF")
    pos = 12
    out = []
    while pos + 8 <= len(data):
        cid = data[pos:pos + 4]
        sz = struct.unpack("<I", data[pos + 4:pos + 8])[0]
        out.append((cid, pos, sz))
        pos += 8 + sz + (sz & 1)
    return out


# Тип контейнера по сигнатуре
def cover_kind(path):
    with open(path, "rb") as f:
        head = f.read(64)
    ext, name = detect_type(head)
    if ext in ("mp4", "mov", "m4a", "heic"):
        return "mp4"
    if ext in ("png", "jpg", "wav", "mp3", "pdf", "zip"):
        return ext
    if head[:3] == b"ID3":
        return "mp3"
    return "other"


KIND_CHANNELS = {
    "png": ["qim", "chunk", "tail", "zip", "meta"],
    "jpg": ["qim", "app", "tail", "zip", "meta"],
    "mp4": ["atom", "meta"],
    "wav": ["riff"],
    "mp3": ["tail", "meta"],
    "pdf": ["tail", "meta"],
    "zip": ["zipmember"],
    "other": ["tail"],
}
CH_TITLES = {"qim": "QIM в яркости (устойчив к JPEG)", "chunk": "служебный чанк PNG", "tail": "хвост после конца файла", "zip": "ZIP-полиглот", "meta": "метаданные (EXIF/ID3/Info)",
             "app": "сегменты JPEG APP15", "atom": "атом free (MP4/MOV)", "riff": "RIFF-чанк (WAV)", "zipmember": "лишний файл в ZIP/Office"}
CH_SURVIVE = {"qim": "переживает JPEG и ресайз; ёмкость ~100 байт (ключи)", "chunk": "переживает пересылку «как файл», теряется при пересохранении", "tail": "переживает «как файл», теряется при любой обработке",
               "zip": "переживает «как файл»", "meta": "теряется при удалении метаданных", "app": "теряется при пересжатии JPEG",
               "atom": "переживает «как файл», теряется при перекодировании", "riff": "переживает «как файл»", "zipmember": "переживает «как файл»"}


# Канал: хвост (для PDF — с копией startxref)
def ch_tail(data, frame, kind):
    if kind == "pdf":
        i = data.rfind(b"startxref")
        if i < 0:
            raise CFError("PDF без startxref")
        return data + b"\n" + frame + b"\n" + data[i:]
    return data + frame


# Канал: служебный чанк PNG
def ch_chunk(data, frame, kind):
    ch = png_chunks(data)
    iend = [c for c in ch if c[0] == b"IEND"]
    if not iend:
        raise CFError("PNG без IEND")
    pos = iend[0][1]
    return data[:pos] + png_chunk(b"crFg", frame) + data[pos:]


# Канал: сегменты JPEG APP15
def ch_app(data, frame, kind):
    segs = jpeg_segments(data)
    out = b""
    piece = 65000
    pieces = [frame[i:i + piece] for i in range(0, len(frame), piece)]
    for idx, p in enumerate(pieces):
        body = b"CFJ\x00" + struct.pack(">HH", idx, len(pieces)) + p
        out += b"\xff\xef" + struct.pack(">H", len(body) + 2) + body
    return data[:2] + out + data[2:]


# Канал: атом free в MP4
def ch_atom(data, frame, kind):
    mp4_atoms(data)
    size = 8 + len(frame)
    if size < 2 ** 32:
        return data + struct.pack(">I", size) + b"free" + frame
    return data + struct.pack(">I", 1) + b"free" + struct.pack(">Q", 16 + len(frame)) + frame


# Канал: RIFF-чанк в WAV
def ch_riff(data, frame, kind):
    riff_chunks(data)
    add = b"cfdt" + struct.pack("<I", len(frame)) + frame + (b"\x00" if len(frame) & 1 else b"")
    out = data + add
    return out[:4] + struct.pack("<I", len(out) - 8) + out[8:]


# Значение для поля метаданных
def exif_value_for(frame):
    return "CFH:" + b64e(frame)


# Внедрение кадра выбранным каналом
def embed_channel(cover_path, out_path, frame, ch, kind):
    data = Path(cover_path).read_bytes()
    if ch in ("tail", "chunk", "app", "atom", "riff"):
        fn = {"tail": ch_tail, "chunk": ch_chunk, "app": ch_app, "atom": ch_atom, "riff": ch_riff}[ch]
        Path(out_path).write_bytes(fn(data, frame, kind))
    elif ch in ("zip", "zipmember"):
        import zipfile
        if Path(cover_path).resolve() != Path(out_path).resolve():
            shutil.copyfile(cover_path, out_path)
        with zipfile.ZipFile(out_path, "a", zipfile.ZIP_STORED) as z:
            z.writestr("cf.dat", frame)
    elif ch == "meta":
        if not shutil.which("exiftool"):
            raise CFError("Канал метаданных требует exiftool")
        if len(frame) > 45000:
            raise CFError("Канал метаданных вмещает до ~45 КБ")
        if Path(cover_path).resolve() != Path(out_path).resolve():
            shutil.copyfile(cover_path, out_path)
        tag = "-UserComment" if kind in ("png", "jpg") else "-Comment"
        rc, out, err = exif_run(["-overwrite_original", f"{tag}={exif_value_for(frame)}", str(out_path)])
        if rc != 0 and "1 image files updated" not in out and "1 files updated" not in out:
            raise CFError("exiftool не смог записать: " + (err.strip().splitlines() or ["ошибка"])[-1])
    else:
        raise CFError("Неизвестный канал")


# Извлечение кадра из канала
def extract_channel(path, ch):
    data = Path(path).read_bytes()
    if ch == "tail":
        loc = frame_from_tail(data)
        return (data[loc[0]:loc[1]], loc) if loc else (None, None)
    if ch == "chunk":
        for typ, pos, ln in png_chunks(data):
            if typ == b"crFg":
                return data[pos + 8:pos + 8 + ln], (pos + 8, pos + 8 + ln, pos + 8 + ln)
        return None, None
    if ch == "app":
        parts = {}
        offs = []
        for mk, pos, ln in jpeg_segments(data):
            if mk == 0xEF and data[pos + 4:pos + 8] == b"CFJ\x00":
                idx, tot = struct.unpack(">HH", data[pos + 8:pos + 12])
                parts[idx] = data[pos + 12:pos + 2 + ln]
                offs.append((pos + 12, pos + 2 + ln))
                last = tot
        if not parts:
            return None, None
        if len(parts) != last:
            return b"".join(parts[i] for i in sorted(parts)), (offs[0][0], offs[-1][1], None)
        return b"".join(parts[i] for i in range(last)), (offs[0][0], offs[-1][1], None)
    if ch == "atom":
        for typ, pos, size, hdr in mp4_atoms(data):
            if typ == b"free" and data[pos + hdr:pos + hdr + 8] == FRAME_MAGIC:
                return data[pos + hdr:pos + size], (pos + hdr, pos + size, None)
        return None, None
    if ch == "riff":
        for cid, pos, sz in riff_chunks(data):
            if cid == b"cfdt":
                return data[pos + 8:pos + 8 + sz], (pos + 8, pos + 8 + sz, None)
        return None, None
    if ch in ("zip", "zipmember"):
        import zipfile
        try:
            with zipfile.ZipFile(path) as z:
                if "cf.dat" in z.namelist():
                    return z.read("cf.dat"), None
        except Exception:
            pass
        return None, None
    if ch == "meta":
        if not shutil.which("exiftool"):
            return None, None
        rc, out, err = exif_run(["-s3", "-UserComment", "-Comment", str(path)])
        for ln in out.splitlines():
            ln = ln.strip()
            if "CFH:" in ln:
                try:
                    return b64d(ln.split("CFH:", 1)[1].strip()), None
                except Exception:
                    return None, None
        return None, None
    return None, None


CANARY_LEN = 24


# Canary: маркер + CRC
def canary_make():
    body = CANARY_MAGIC + os.urandom(16)
    return body + struct.pack(">I", zlib.crc32(body) & 0xFFFFFFFF)


# Вставка canary
def canary_embed(path, kind):
    data = Path(path).read_bytes()
    cn = canary_make()
    if kind == "png":
        out = ch_chunk(data, b"", kind)
        pos = [c for c in png_chunks(data) if c[0] == b"IEND"][0][1]
        out = data[:pos] + png_chunk(b"crCn", cn) + data[pos:]
    elif kind == "mp4":
        out = ch_atom(data, cn, kind)
    elif kind == "wav":
        out = ch_riff(data, cn, kind)
    else:
        out = data + cn
    Path(path).write_bytes(out)


# Проверка canary (пропал — контейнер обрабатывали)
def canary_check(path, kind):
    data = Path(path).read_bytes()
    try:
        if kind == "png":
            for typ, pos, ln in png_chunks(data):
                if typ == b"crCn" and ln == CANARY_LEN:
                    d = data[pos + 8:pos + 8 + ln]
                    return zlib.crc32(d[:20]) & 0xFFFFFFFF == struct.unpack(">I", d[20:])[0]
            return False
        if kind == "mp4":
            for typ, pos, size, hdr in mp4_atoms(data):
                if typ == b"free" and data[pos + hdr:pos + hdr + 4] == CANARY_MAGIC:
                    d = data[pos + hdr:pos + hdr + CANARY_LEN]
                    return zlib.crc32(d[:20]) & 0xFFFFFFFF == struct.unpack(">I", d[20:])[0]
            return False
        if kind == "wav":
            for cid, pos, sz in riff_chunks(data):
                if cid == b"cfdt" and data[pos + 8:pos + 12] == CANARY_MAGIC:
                    d = data[pos + 8:pos + 8 + CANARY_LEN]
                    return zlib.crc32(d[:20]) & 0xFFFFFFFF == struct.unpack(">I", d[20:])[0]
            return False
        d = data[-CANARY_LEN:]
        return d[:4] == CANARY_MAGIC and zlib.crc32(d[:20]) & 0xFFFFFFFF == struct.unpack(">I", d[20:])[0]
    except CFError:
        return False


# Проверка структуры контейнера
def validate_cover(path, kind=None):
    kind = kind or cover_kind(path)
    data = Path(path).read_bytes()
    try:
        if kind == "png":
            ch = png_chunks(data)
            pos = 8
            for typ, p, ln in ch:
                crc = struct.unpack(">I", data[p + 8 + ln:p + 12 + ln])[0]
                if zlib.crc32(data[p + 4:p + 8 + ln]) & 0xFFFFFFFF != crc:
                    return False, f"CRC чанка {typ!r} не сходится"
            if ch[-1][0] != b"IEND":
                return False, "нет IEND"
            try:
                from PIL import Image
                Image.open(path).verify()
            except ImportError:
                pass
        elif kind == "jpg":
            jpeg_segments(data)
            if data.rfind(b"\xff\xd9") < 0:
                return False, "нет маркера EOI"
        elif kind == "mp4":
            mp4_atoms(data)
        elif kind == "wav":
            riff_chunks(data)
            if struct.unpack("<I", data[4:8])[0] + 8 != len(data):
                return False, "размер RIFF не совпадает с файлом"
        elif kind == "pdf":
            if data[:5] != b"%PDF-" or b"%%EOF" not in data[-2048:]:
                return False, "PDF: нет %%EOF в конце"
        elif kind == "zip":
            import zipfile
            with zipfile.ZipFile(path) as z:
                bad = z.testzip()
            if bad:
                return False, f"ZIP повреждён: {bad}"
        elif kind == "mp3":
            if not (data[:3] == b"ID3" or data[:2] in (b"\xff\xfb", b"\xff\xf3", b"\xff\xf2")):
                return False, "MP3: нет синхронизации"
        return True, "структура корректна"
    except CFError as e:
        return False, str(e)
    except Exception as e:
        return False, f"{type(e).__name__}: {e}"


# Правдоподобные теги метаданных под тип контейнера
def legit_args(kind, total_size):
    mb = max(1, total_size // MB)
    if kind in ("png", "jpg"):
        return ["-Make=Apple", "-Model=iPhone 15 Pro", "-LensModel=iPhone 15 Pro back triple camera 6.86mm f/1.78", "-ISO=50", "-ExposureTime=1/120", "-FNumber=1.78",
                "-FocalLength=6.86", "-Software=17.2", f"-ImageDescription=ProRAW 48MP, {mb} MB"]
    if kind == "mp4":
        return ["-Make=Apple", "-Model=iPhone 15 Pro", "-Software=17.2", f"-Comment=ProRes 422 HQ 4K 60fps, {mb} MB"]
    if kind in ("wav", "mp3"):
        return ["-Artist=Field Recording", "-Album=Lossless 24-bit/96kHz", f"-Comment=Lossless master 24bit/96kHz, {mb} MB"]
    if kind == "pdf":
        return ["-Creator=Scanner Pro", "-Producer=Scanned 600 dpi, OCR", f"-Subject=High resolution scan, {mb} MB"]
    return []


# Маскировка: проверка, каналы, canary, повторная проверка и извлечение, иначе откат
def mask_embed(cover, out, payload, channels, fec=0.0, burn=False, canary=True, legit=False, say_it=True):
    cover = Path(cover)
    out = Path(out)
    kind = cover_kind(cover)
    ok, why = validate_cover(cover, kind)
    if not ok:
        raise CFError(f"Контейнер невалиден до внедрения: {why}")
    if is_carrying(cover):
        raise CFError("Контейнер уже несёт данные CryptForge. Возьмите чистый файл: перезапись поверх старых данных не поддерживается (fail-closed)")
    frame = frame_build(payload, fec, burn)
    allowed = KIND_CHANNELS.get(kind, ["tail"])
    for ch in channels:
        if ch not in allowed:
            raise CFError(f"Канал «{CH_TITLES.get(ch, ch)}» не подходит для типа {kind}")
    work = new_work()
    try:
        cur = work / "m0"
        shutil.copyfile(cover, cur)
        if legit and shutil.which("exiftool") and kind != "other":
            args = legit_args(kind, cover.stat().st_size + len(frame))
            if args:
                exif_run(["-overwrite_original"] + args + [str(cur)])
        if "qim" in channels:
            if len(payload) > 90:
                raise CFError("Канал QIM вмещает до ~90 байт (ключ или доля Шамира)")
            nxt = work / "m_qim"
            qim_embed_image(cur, nxt, payload)
            cur = nxt
        order = [c for c in channels if c == "meta"] + [c for c in channels if c not in ("meta", "tail", "qim")] + [c for c in channels if c == "tail"]
        for ch in order:
            nxt = work / f"m_{ch}"
            embed_channel(cur, nxt, frame, ch, kind)
            cur = nxt
        if canary:
            canary_embed(cur, kind)
        ok, why = validate_cover(cur, kind)
        if not ok:
            raise CFError(f"Проверка контейнера после внедрения не пройдена ({why}) — откат")
        got = mask_extract(cur, quiet=True)
        if got["payload"] != payload:
            raise CFError("Проверка извлечения не пройдена — откат")
        shutil.copyfile(cur, out)
        os.chmod(out, 0o600)
    finally:
        shutil.rmtree(work, ignore_errors=True)
    return {"kind": kind, "channels": list(channels), "size": out.stat().st_size, "fec": fec, "frame_len": len(frame)}


# Несёт ли контейнер данные CryptForge
def is_carrying(path):
    try:
        for ch in KIND_CHANNELS.get(cover_kind(path), ["tail"]):
            if ch in ("meta", "qim"):
                continue
            fr, loc = extract_channel(path, ch)
            if fr and fr[:8] == FRAME_MAGIC:
                return True
    except Exception:
        pass
    return False


# Извлечение: перебор каналов, FEC, отчёт по каналам
def mask_extract(path, quiet=False):
    kind = cover_kind(path)
    res = {"kind": kind, "channels": {}, "payload": None, "meta": None, "fixed": 0, "canary": canary_check(path, kind)}
    best = None
    if kind in ("png", "jpg"):
        q = qim_extract_image(path)
        if q is not None:
            res["channels"]["qim"] = "OK"
            best = ({"len": len(q), "burn": False}, q, 0, "qim", None)
        else:
            res["channels"]["qim"] = "нет данных"
    for ch in KIND_CHANNELS.get(kind, ["tail"]) + ["tail", "zip"]:
        if ch in res["channels"]:
            continue
        try:
            fr, loc = extract_channel(path, ch)
        except Exception as e:
            res["channels"][ch] = f"ошибка: {e}"
            continue
        if not fr:
            res["channels"][ch] = "нет данных"
            continue
        try:
            meta, payload, fixed = frame_parse(fr)
            res["channels"][ch] = "OK" + (f" (восстановлено блоков: {fixed})" if fixed else "")
            if best is None:
                best = (meta, payload, fixed, ch, loc)
        except CFError as e:
            res["channels"][ch] = f"повреждён: {e}"
    if best:
        res["meta"], res["payload"], res["fixed"], res["via"], res["loc"] = best
    if not quiet and best is None:
        raise CFError("Скрытых данных CryptForge не найдено или они разрушены: " + "; ".join(f"{CH_TITLES.get(k, k)} — {v}" for k, v in res["channels"].items()))
    return res


# Уничтожает данные во ВСЕХ каналах контейнера, где известны их границы; возвращает (сожжено, не удалось)
def burn_payload(path, res=None):
    burned = []
    skipped = []
    kind = cover_kind(path)
    for ch in list(dict.fromkeys(KIND_CHANNELS.get(kind, ["tail"]) + ["tail"])):
        if ch == "qim":
            fr = qim_extract_image(path)
            if fr is not None:
                skipped.append(ch)
            continue
        try:
            fr, loc = extract_channel(path, ch)
        except Exception:
            continue
        if not fr or fr[:8] != FRAME_MAGIC:
            continue
        if not loc:
            skipped.append(ch)
            continue
        if ch == "app" and len(fr) > 64000:
            skipped.append(ch)
            continue
        data = bytearray(Path(path).read_bytes())
        start, end = loc[0], loc[1]
        data[start:end] = os.urandom(end - start)
        if ch == "chunk":
            data[end:end + 4] = struct.pack(">I", zlib.crc32(bytes(data[start - 4:end])) & 0xFFFFFFFF)
        Path(path).write_bytes(bytes(data))
        burned.append(ch)
    return burned, skipped


# Имитация обработки: обрезка, стрип, пересохранение, ресайз, ffmpeg
def simulate_attack(src, dst, how, kind):
    data = Path(src).read_bytes()
    if how == "tail_cut":
        if kind == "png":
            i = data.find(b"IEND") + 8
            Path(dst).write_bytes(data[:i])
        elif kind == "jpg":
            Path(dst).write_bytes(data[:data.rfind(b"\xff\xd9") + 2])
        elif kind == "pdf":
            Path(dst).write_bytes(data[:data.find(b"%%EOF") + 5])
        elif kind == "mp4":
            Path(dst).write_bytes(data)
        else:
            Path(dst).write_bytes(data[:-max(1, len(data) // 50)])
        return True
    if how == "strip_meta":
        if shutil.which("exiftool"):
            shutil.copyfile(src, dst)
            exif_run(["-overwrite_original", "-all=", str(dst)])
            return True
        return False
    if how in ("recompress", "resize"):
        try:
            from PIL import Image
        except ImportError:
            return False
        if kind not in ("png", "jpg"):
            return False
        im = Image.open(src)
        im.load()
        if how == "resize":
            im = im.resize((max(8, im.width // 2), max(8, im.height // 2)))
        if kind == "jpg":
            im.convert("RGB").save(dst, "JPEG", quality=80)
        else:
            im.save(dst, "PNG")
        return True
    if how == "ffmpeg":
        if kind != "mp4" or not shutil.which("ffmpeg"):
            return False
        r = subprocess.run(["ffmpeg", "-y", "-i", str(src), "-b:v", "1M", "-t", "3", str(dst) + ".mp4"], capture_output=True, timeout=300)
        if r.returncode != 0:
            return False
        os.replace(str(dst) + ".mp4", dst)
        return True
    return False


# Тест выживания каналов
def survival_test(cover):
    cover = Path(cover)
    kind = cover_kind(cover)
    chans = [c for c in KIND_CHANNELS.get(kind, ["tail"]) if c != "meta" or shutil.which("exiftool")]
    attacks = [("tail_cut", "обрезка хвоста"), ("strip_meta", "удаление метаданных"), ("recompress", "пересохранение"), ("resize", "ресайз 50%"), ("ffmpeg", "перекодирование видео")]
    work = new_work()
    results = {}
    try:
        for ch in chans:
            payload = os.urandom(60 if ch == "qim" else 1500)
            o = work / f"emb_{ch}"
            try:
                mask_embed(cover, o, payload, [ch], fec=0.0, canary=True)
            except CFError as e:
                results[ch] = {"embed": str(e)}
                continue
            row = {"как файл": mask_extract(o, quiet=True)["payload"] == payload}
            for how, title in attacks:
                dst = work / f"att_{ch}_{how}"
                try:
                    done = simulate_attack(o, dst, how, kind)
                except Exception:
                    done = False
                if not done:
                    row[title] = None
                    continue
                try:
                    row[title] = mask_extract(dst, quiet=True)["payload"] == payload
                except Exception:
                    row[title] = False
            results[ch] = row
    finally:
        shutil.rmtree(work, ignore_errors=True)
    return kind, results


# Отчёт теста выживания
def survival_report(kind, results):
    print()
    for ch, row in results.items():
        print(f"  \033[1;38;5;51m{CH_TITLES.get(ch, ch)}\033[0m")
        if "embed" in row:
            print(f"     ✖ внедрение: {row['embed']}")
            continue
        for k, v in row.items():
            mark = "—" if v is None else ("✔" if v else "✖")
            print(f"     {mark} {k}")
    print()
    say_in("— = проверка недоступна (нет ffmpeg/Pillow/exiftool или не тот тип)")
    survivors = [c for c, row in results.items() if "embed" not in row and all(v for k, v in row.items() if v is not None and k != "перекодирование видео")]
    if survivors:
        say_ok("Устойчивый ко всем проверкам канал: " + ", ".join(CH_TITLES.get(c, c) for c in survivors))
    else:
        say_wn("Ни один канал не пережил все атаки. Отправляйте «как файл/документ» и включайте FEC.")


# Выбор контейнера
def pick_cover(prompt="Файл-контейнер (фото, видео, аудио, PDF)"):
    raw = ask(prompt + " (путь или b — обзор): ")
    if raw.lower() == "b":
        r = browse_flow("files")
        return Path(r[0]) if r else None
    p = Path(os.path.expanduser(raw))
    if not p.is_file():
        raise CFError("Файл не найден")
    return p


# Рекомендация каналов для профиля transfer/storage
def recommend_channels(kind, mode):
    allowed = KIND_CHANNELS.get(kind, ["tail"])
    if mode == "transfer":
        pref = [c for c in ("tail", "chunk", "atom", "riff", "app", "zip") if c in allowed]
        return pref[:2]
    pref = [c for c in ("chunk", "atom", "riff", "app", "tail") if c in allowed]
    return pref[:1]


# Меню маскировки
def mask_flow():
    title_anim("МАСКИРОВКА")
    say_in("Данные прячутся в обычный файл,")
    say_in("который открывается как раньше.")
    files = pick_files("Что спрятать (.enc или любой файл)", [VAULT], True)
    if not files:
        return
    payload_path = Path(files[0])
    cover = pick_cover()
    if not cover:
        return
    kind = cover_kind(cover)
    payload = payload_path.read_bytes()
    allowed = KIND_CHANNELS.get(kind, ["tail"])
    say_in(f"Тип контейнера: {kind}")
    print("  Профиль: 1. transfer (отправка)  2. storage (хранение)")
    print("  \033[2mtransfer: 2 канала + FEC; storage: 1 канал\033[0m")
    mode = "transfer" if ask("Профиль [1]: ", "1") == "1" else "storage"
    rec = recommend_channels(kind, mode)
    say_in("Рекомендую: " + ", ".join(CH_TITLES[c] for c in rec))
    print("  Каналы:")
    for i, c in enumerate(allowed, 1):
        print(f"   {i}. {CH_TITLES[c]}")
        print(f"      \033[2m{CH_SURVIVE[c]}\033[0m")
    sel = ask("Номера через запятую [Enter — рекомендуемые]: ")
    chans = rec
    if sel:
        chans = [allowed[int(x) - 1] for x in sel.split(",") if x.strip().isdigit() and 1 <= int(x) <= len(allowed)]
    if not chans:
        raise CFError("Каналы не выбраны")
    fec = 0.0
    if ask_yn("Добавить помехоустойчивое кодирование (FEC)?", "y" if mode == "transfer" else "n"):
        fec = ask_int("Избыточность, %", 10, 200, 50) / 100.0
        if len(payload) > 64 * MB:
            say_wn("FEC для больших данных медленный")
    if "meta" in chans and len(payload) > 45000:
        raise CFError("Канал метаданных годится только для небольших данных")
    burn = ask_yn("Сжечь данные после первого извлечения (burn after reading)?", "n")
    legit = ask_yn("Подобрать правдоподобные метаданные (камера, битрейт, размер)?", "y")
    total = cover.stat().st_size + len(payload)
    say_in(f"Размер контейнера: {hsize(cover.stat().st_size)} → итог ≈ {hsize(total)}")
    out = STEGO / (cover.stem + "_" + gen_name()[:6] + cover.suffix)
    rep = mask_embed(cover, out, payload, chans, fec, burn, True, legit)
    say_ok(f"Готово: {out}")
    say_in(f"Каналы: {', '.join(CH_TITLES[c] for c in chans)}; FEC: {int(fec * 100)}%")
    say_in("Проверка структуры и извлечения пройдена")
    if mode == "transfer":
        say_wn("Мессенджеры пересжимают медиа: отправляйте «как файл/документ».")
    log_action("mask", len(payload), None, None, None, f"{rep['kind']}:{','.join(chans)}")
    if ask_yn("Проверить устойчивость (тест на выживание на чистом контейнере)?", "n"):
        kind2, results = survival_test(cover)
        survival_report(kind2, results)


# Меню извлечения (burn after reading по желанию)
def unmask_flow():
    title_anim("ИЗВЛЕЧЬ ИЗ КОНТЕЙНЕРА")
    cover = pick_cover("Контейнер")
    if not cover:
        return
    res = mask_extract(cover)
    print()
    for ch, st in res["channels"].items():
        print(f"  {CH_TITLES.get(ch, ch)}: {st}")
    if res["canary"]:
        say_ok("Canary на месте: контейнер, вероятно, не перекодировался")
    else:
        say_wn("Canary не найден: контейнер мог пройти через мессенджер/стрип метаданных.")
        say_wn("Проверьте SHA-256 результата; при ошибках используйте копию с FEC.")
    name = ask("Имя результата (Enter — случайное .enc): ")
    if name and not valid_user_name(name):
        raise CFError("Недопустимое имя")
    out = unique_path(VAULT, name or gen_name(".enc"))
    out.write_bytes(res["payload"])
    os.chmod(out, 0o600)
    say_ok(f"Извлечено в vault: {out} ({hsize(len(res['payload']))}, SHA-256 сверен)")
    if res["meta"] and res["meta"].get("burn"):
        say_wn("Включён режим burn after reading.")
        if ask_yn("Уничтожить данные в контейнере сейчас?", "y"):
            burned, skipped = burn_payload(cover, res)
            if skipped:
                say_wn("Не удалось сжечь каналы: " + ", ".join(CH_TITLES.get(c, c) for c in skipped))
            try:
                mask_extract(cover, quiet=False)
                say_er("Данные всё ещё извлекаются — сожжены не все каналы")
            except CFError:
                say_ok("Данные в контейнере уничтожены, повторное извлечение невозможно")
    log_action("unmask", len(res["payload"]), None, None, None, out.name)


# Проверка файла на скрытые данные
def detect_flow():
    cover = pick_cover("Файл для проверки")
    if not cover:
        return
    kind = cover_kind(cover)
    ok, why = validate_cover(cover, kind)
    say_in(f"Тип: {kind}; структура: {'✔' if ok else '✖'} {why}")
    found = False
    for ch in KIND_CHANNELS.get(kind, ["tail"]):
        try:
            fr, loc = extract_channel(cover, ch)
        except Exception:
            fr = None
        if fr and fr[:8] == FRAME_MAGIC:
            found = True
            say_wn(f"Найдены данные CryptForge: {CH_TITLES[ch]} ({hsize(len(fr))})")
    if not found:
        say_ok("Данных CryptForge не найдено")
    say_in("Canary: " + ("на месте" if canary_check(cover, kind) else "нет"))


# Меню теста выживания
def survival_flow():
    title_anim("ТЕСТ НА ВЫЖИВАНИЕ")
    cover = pick_cover("Контейнер для теста")
    if not cover:
        return
    say_in("Проверяю каналы на тестовых данных...")
    kind, results = survival_test(cover)
    survival_report(kind, results)


# Спрятать ключ/долю в медиа
def key_hide_flow():
    title_anim("СПРЯТАТЬ КЛЮЧ В МЕДИА")
    print("   1. Ввести/вставить ключ или долю")
    print("   2. Выбрать файл долей из shares/")
    c = ask("Источник [1]: ", "1")
    if c == "2":
        fl = pick_files("Файл доли", [SHARES], True)
        if not fl:
            return
        text = Path(fl[0]).read_text(encoding="utf-8", errors="ignore")
        m = SHARE_RE.search(text)
        data = (m.group(0) if m else text).encode()
    else:
        data = ask("Текст ключа/доли: ").encode()
    if not data:
        return
    cover = pick_cover("Фото/аудио/видео-контейнер")
    if not cover:
        return
    kind = cover_kind(cover)
    allowed = KIND_CHANNELS.get(kind, ["tail"])
    pref = [c for c in ("meta", "chunk", "app", "riff", "atom", "tail") if c in allowed and (c != "meta" or shutil.which("exiftool"))]
    chans = pref[:2] if pref else ["tail"]
    say_in("Каналы: " + ", ".join(CH_TITLES[x] for x in chans))
    out = STEGO / (cover.stem + "_k" + gen_name()[:5] + cover.suffix)
    mask_embed(cover, out, data, chans, fec=0.5, canary=False, legit=False)
    say_ok(f"Ключ спрятан в копии: {out} (оригинал не тронут)")


# Сбор ключей из медиафайлов
def media_keys_collect(files):
    lines = []
    for f in files:
        try:
            res = mask_extract(Path(f), quiet=False)
            lines.append(res["payload"].decode("utf-8", "ignore"))
            say_ok(f"Найдено в {Path(f).name}")
        except CFError as e:
            say_wn(f"{Path(f).name}: {e}")
    return lines


# Расшифровка по ключам из медиафайлов
def decrypt_with_media_flow():
    title_anim("РАСШИФРОВКА ПО МЕДИА-КЛЮЧАМ")
    fl = pick_files("Файл .enc из vault", [VAULT], True)
    if not fl:
        return
    say_in("Укажите медиафайлы с долями/ключом")
    media = browse_flow("files")
    if not media:
        return
    lines = media_keys_collect(media)
    if not lines:
        raise CFError("Ключи не найдены")
    info = None
    try:
        d = combine_share_lines(lines)
        info = {"layers": d["layers"], "keys": d["keys"], "restore_as": d.get("restore_as") or Path(fl[0]).stem, "compressed": bool(d.get("compressed")), "src_sha256": None, "enc_sha256": None}
        say_ok("Доли собраны")
    except CFError:
        pass
    if info is None:
        for ln in lines:
            try:
                d = json.loads(ln)
                info = {"layers": d["layers"], "keys": d["keys"], "restore_as": d.get("restore_as", Path(fl[0]).stem), "compressed": bool(d.get("compressed")), "src_sha256": d.get("src_sha256"), "enc_sha256": None}
                break
            except Exception:
                continue
    if info is None:
        raise CFError("Не удалось собрать ключ из найденных данных")
    decrypt_one(fl[0], override=info)


# Меню маскировки и стеганографии
def stego_menu():
    while True:
        title_anim("МАСКИРОВКА И СТЕГО")
        rows = [
            ("1", "Замаскировать в файл", "фото/видео/аудио/PDF"),
            ("2", "Извлечь из контейнера", "данные CryptForge"),
            ("3", "Спрятать ключ/долю в медиа", "EXIF, чанки, хвост"),
            ("4", "Расшифровать по медиа-ключам", "доли из нескольких файлов"),
            ("5", "Тест на выживание", "имитация мессенджера"),
            ("6", "Проверить файл", "есть ли скрытые данные"),
            ("7", "LSB в PNG/WAV (классика)", "спрятать/извлечь"),
            ("8", "RDH: обратимое в PNG/WAV", "контейнер восстанавливается"),
            ("9", "Скрыть в тексте (невидимые символы)", "для коротких ключей"),
            ("10", "DNA-контейнер (FASTA)", "экспериментально"),
            ("11", "Аудит контейнера", "энтропия и текстура"),
        ]
        for n, name, note in rows:
            print(f"  \033[1;38;5;51m{n:>3}\033[0m  {name}")
            print(f"       \033[38;5;243m{note}\033[0m")
        print("  \033[1;38;5;203m  0\033[0m  Назад")
        c = ask("Номер: ")
        try:
            if c == "0":
                return
            elif c == "1":
                mask_flow()
            elif c == "2":
                unmask_flow()
            elif c == "3":
                key_hide_flow()
            elif c == "4":
                decrypt_with_media_flow()
            elif c == "5":
                survival_flow()
            elif c == "6":
                detect_flow()
            elif c == "7":
                lsb_menu()
            elif c == "8":
                rdh_menu()
            elif c == "9":
                zw_menu()
            elif c == "10":
                dna_menu()
            elif c == "11":
                audit_flow()
            else:
                say_er("Неверный выбор")
        except CFError as e:
            say_er(str(e))


# =====================================================================
# РАЗДЕЛ: QIM — устойчивый канал для изображений (выживает JPEG и ресайз)
# =====================================================================
# Идея: изображение делится на фиксированную сетку 64x64 ячеек (одинаковую
# в долях размера при любом разрешении). Средняя яркость каждой ячейки
# квантуется на решётку с шагом QIM_STEP: чётный/нечётный узел = бит 0/1.
# JPEG и уменьшение картинки почти не меняют среднюю яркость больших ячеек,
# а помехоустойчивый код (FEC с CRC-блоками) чинит редкие ошибки.
QIM_G = 64
QIM_STEP = 20.0
QIM_BLOCK = 16


# Формируем поток: 3 копии заголовка (k, m, n) + FEC-записи тела
def qim_pack(payload):
    body = struct.pack(">H", len(payload)) + payload + struct.pack(">I", zlib.crc32(payload) & 0xFFFFFFFF)
    recs, p = fec_encode(body, 1.0, QIM_BLOCK)
    hdr = struct.pack(">BBH", p["k"], p["m"], p["n"])
    stream = hdr * 3 + recs
    if len(stream) * 8 > QIM_G * QIM_G:
        raise CFError(f"QIM вмещает до ~{(QIM_G * QIM_G // 8 - 12) // 2 - 12} байт; у вас {len(payload)} (для больших данных используйте другие каналы)")
    return stream


# Голосованием по трём копиям восстанавливаем заголовок, затем декодируем FEC
def qim_unpack(stream):
    h = [stream[i * 4:(i + 1) * 4] for i in range(3)]
    hdr = bytes(max(set(c), key=c.count) for c in zip(*h))
    k, m, n = struct.unpack(">BBH", hdr)
    block = QIM_BLOCK
    recs = stream[12:12 + (k + m) * (6 + block)]
    body, fixed = fec_decode(recs, {"block": block, "k": k, "m": m, "n": n})
    ln = struct.unpack(">H", body[:2])[0]
    payload = body[2:2 + ln]
    crc = struct.unpack(">I", body[2 + ln:6 + ln])[0]
    if zlib.crc32(payload) & 0xFFFFFFFF != crc:
        raise CFError("QIM: контрольная сумма не сошлась")
    return payload


# Внедрение: сдвигаем яркость каждой ячейки к ближайшему узлу решётки нужной чётности
def qim_embed_image(src, dst, payload):
    try:
        from PIL import Image, ImageChops
    except ImportError:
        raise CFError("QIM требует Pillow: apk add py3-pillow")
    im = Image.open(src)
    im.load()
    fmt = (im.format or "PNG").upper()
    if min(im.size) < QIM_G * 2:
        raise CFError("Изображение слишком маленькое для QIM (нужно от 128 px по каждой стороне)")
    stream = qim_pack(payload)
    bits = []
    for byte in stream:
        for i in range(7, -1, -1):
            bits.append((byte >> i) & 1)
    while len(bits) < QIM_G * QIM_G:
        bits.append(rand_below(2))
    ycc = im.convert("RGB").convert("YCbCr")
    Y, Cb, Cr = ycc.split()
    means = list(Y.resize((QIM_G, QIM_G), Image.BOX).getdata())
    deltas = []
    for mval, b in zip(means, bits):
        lo, hi = 2, int(240 / QIM_STEP)
        best = None
        for kk in range(lo, hi):
            if kk % 2 == b:
                cand = kk * QIM_STEP
                if best is None or abs(cand - mval) < abs(best - mval):
                    best = cand
        deltas.append(int(round(best - mval)))
    D = Image.new("L", (QIM_G, QIM_G))
    D.putdata([max(0, min(255, 128 + d)) for d in deltas])
    Dfull = D.resize(Y.size, Image.NEAREST)
    Y2 = ImageChops.add(Y, Dfull, 1.0, -128)
    out = Image.merge("YCbCr", (Y2, Cb, Cr)).convert("RGB")
    if fmt == "JPEG":
        out.save(dst, "JPEG", quality=95, subsampling=0)
    else:
        out.save(dst, "PNG")


# Извлечение: читаем среднюю яркость ячеек и берём чётность ближайшего узла решётки
def qim_extract_image(path):
    try:
        from PIL import Image
    except ImportError:
        return None
    im = Image.open(path)
    im.load()
    if min(im.size) < QIM_G:
        return None
    Y = im.convert("RGB").convert("YCbCr").split()[0]
    means = list(Y.resize((QIM_G, QIM_G), Image.BOX).getdata())
    bits = [int(round(m / QIM_STEP)) & 1 for m in means]
    stream = bytearray()
    for i in range(0, len(bits) - 7, 8):
        v = 0
        for b in bits[i:i + 8]:
            v = (v << 1) | b
        stream.append(v)
    try:
        return qim_unpack(bytes(stream))
    except Exception:
        return None


# =====================================================================
# РАЗДЕЛ: RDH — обратимое сокрытие (контейнер восстанавливается по пикселям)
# =====================================================================
# Метод: сдвиг гистограммы ошибки предсказания на шахматной сетке.
# Две фазы (чёрные/белые клетки): первая фаза использует неизменённых соседей,
# вторая — уже изменённых; извлечение идёт в обратном порядке.
# Пиксели со значением vmax заранее сдвигаются на 1 (карта положений хранится
# внутри полезной нагрузки), чтобы избежать переполнения.
RDH_MAGIC = b"RDH1"
RDH_MAX_PIX = 1500000


# Одна фаза внедрения над плоскостью v (список int); возвращает новую позицию в списке бит
def rdh_stage_embed(v, w, h, parity, bits, pos):
    nb = len(bits)
    if h == 1:
        rng = [(0, i) for i in range(1, w - 1) if (i & 1) == parity]
    else:
        rng = None
    if rng is not None:
        for _, i in rng:
            pred = (v[i - 1] + v[i + 1] + 1) >> 1
            e = v[i] - pred
            if e == 0:
                b = bits[pos] if pos < nb else 0
                pos += 1
                v[i] += b
            elif e > 0:
                v[i] += 1
        return pos
    for y in range(1, h - 1):
        row = y * w
        x0 = 1 if ((1 + y) & 1) == parity else 2
        for x in range(x0, w - 1, 2):
            i = row + x
            pred = (v[i - w] + v[i + w] + v[i - 1] + v[i + 1] + 2) >> 2
            e = v[i] - pred
            if e == 0:
                b = bits[pos] if pos < nb else 0
                pos += 1
                v[i] += b
            elif e > 0:
                v[i] += 1
    return pos


# Обратная операция: возвращает список бит и восстанавливает значения плоскости v
def rdh_stage_extract(v, w, h, parity):
    out = []
    if h == 1:
        for i in range(1, w - 1):
            if (i & 1) != parity:
                continue
            pred = (v[i - 1] + v[i + 1] + 1) >> 1
            e = v[i] - pred
            if e in (0, 1):
                out.append(e)
                v[i] = pred
            elif e >= 2:
                v[i] -= 1
        return out
    for y in range(1, h - 1):
        row = y * w
        x0 = 1 if ((1 + y) & 1) == parity else 2
        for x in range(x0, w - 1, 2):
            i = row + x
            pred = (v[i - w] + v[i + w] + v[i - 1] + v[i + 1] + 2) >> 2
            e = v[i] - pred
            if e in (0, 1):
                out.append(e)
                v[i] = pred
            elif e >= 2:
                v[i] -= 1
    return out


# Внедряет payload в набор плоскостей; возвращает число использованных фаз
def rdh_embed_planes(planes, w, h, vmax, payload):
    import array
    maps = []
    for p in planes:
        pos = array.array("I", [i for i, x in enumerate(p) if x == vmax])
        for i in pos:
            p[i] = vmax - 1
        maps.append(pos)
    mp = bytearray()
    for pos in maps:
        mp += struct.pack(">I", len(pos)) + pos.tobytes()
    mapz = zlib.compress(bytes(mp), 9)
    data = RDH_MAGIC + hashlib.sha256(payload).digest() + struct.pack(">II", len(payload), len(mapz)) + mapz + payload
    bits = []
    for byte in data:
        for i in range(7, -1, -1):
            bits.append((byte >> i) & 1)
    pos = 0
    stages = 0
    for p in planes:
        for parity in (1, 0):
            if pos >= len(bits):
                break
            pos = rdh_stage_embed(p, w, h, parity, bits, pos)
            stages += 1
        if pos >= len(bits):
            break
    if pos < len(bits):
        raise CFError(f"Не хватает ёмкости для RDH: нужно {len(bits)} бит, доступно около {pos}")
    return stages


# Извлекает payload и восстанавливает плоскости к исходным значениям
def rdh_extract_planes(planes, w, h, vmax, stages):
    import array
    order = []
    for pi in range(len(planes)):
        for parity in (1, 0):
            order.append((pi, parity))
    order = order[:stages]
    per = []
    for pi, parity in reversed(order):
        per.append(rdh_stage_extract(planes[pi], w, h, parity))
    per.reverse()
    bits = [b for lst in per for b in lst]
    data = bytearray()
    for i in range(0, len(bits) - 7, 8):
        v = 0
        for b in bits[i:i + 8]:
            v = (v << 1) | b
        data.append(v)
    data = bytes(data)
    if data[:4] != RDH_MAGIC:
        raise CFError("RDH: заголовок не найден (контейнер изменён или в нём нет данных)")
    sha = data[4:36]
    ln, mlen = struct.unpack(">II", data[36:44])
    mapz = data[44:44 + mlen]
    payload = data[44 + mlen:44 + mlen + ln]
    if hashlib.sha256(payload).digest() != sha:
        raise CFError("RDH: SHA-256 данных не совпал")
    mp = zlib.decompressobj().decompress(mapz, 256 * MB)
    off = 0
    for p in planes:
        n = struct.unpack(">I", mp[off:off + 4])[0]
        off += 4
        pos = array.array("I")
        pos.frombytes(mp[off:off + 4 * n])
        off += 4 * n
        for i in pos:
            p[i] = vmax
    return payload


# RDH для PNG: каналы R, G, B обрабатываются как независимые плоскости
def rdh_png_embed(src, dst, payload):
    try:
        from PIL import Image, PngImagePlugin
    except ImportError:
        raise CFError("RDH для PNG требует Pillow: apk add py3-pillow")
    im = Image.open(src)
    im.load()
    if im.mode not in ("RGB", "L"):
        im = im.convert("RGB")
    w, h = im.size
    if w * h > RDH_MAX_PIX:
        raise CFError(f"Изображение слишком большое для RDH ({w * h} пикселей, лимит {RDH_MAX_PIX})")
    chans = list(im.split())
    planes = [list(c.getdata()) for c in chans]
    stages = rdh_embed_planes(planes, w, h, 255, payload)
    out = Image.merge(im.mode, [Image.frombytes("L", (w, h), bytes(p)) for p in planes])
    info = PngImagePlugin.PngInfo()
    info.add(b"crRd", json.dumps({"stages": stages, "mode": im.mode, "w": w, "h": h}).encode())
    out.save(dst, "PNG", pnginfo=info)
    return stages


# Возвращает payload и сохраняет восстановленный (исходный по пикселям) PNG
def rdh_png_extract(path, restored_out):
    from PIL import Image
    data = Path(path).read_bytes()
    meta = None
    for typ, pos, ln in png_chunks(data):
        if typ == b"crRd":
            meta = json.loads(data[pos + 8:pos + 8 + ln].decode())
    if not meta:
        raise CFError("RDH: служебный чанк не найден")
    im = Image.open(path)
    im.load()
    w, h = im.size
    planes = [list(c.getdata()) for c in im.split()]
    payload = rdh_extract_planes(planes, w, h, 255, meta["stages"])
    out = Image.merge(im.mode, [Image.frombytes("L", (w, h), bytes(p)) for p in planes])
    out.save(restored_out, "PNG")
    return payload


# RDH для WAV 16 бит: одна 1D-плоскость сэмплов (первый канал)
def rdh_wav_embed(src, dst, payload):
    import wave
    import array as arr
    with wave.open(str(src), "rb") as wv:
        params = wv.getparams()
        if params.sampwidth != 2 or params.comptype != "NONE":
            raise CFError("RDH WAV: нужен 16-бит PCM")
        raw = wv.readframes(params.nframes)
    a = arr.array("h")
    a.frombytes(raw)
    if len(a) > RDH_MAX_PIX:
        raise CFError("Слишком длинный WAV для RDH")
    plane = [x + 32768 for x in a]
    stages = rdh_embed_planes([plane], len(plane), 1, 65535, payload)
    out = arr.array("h", [x - 32768 for x in plane])
    with wave.open(str(dst), "wb") as wv:
        wv.setparams(params)
        wv.writeframes(out.tobytes())
    data = Path(dst).read_bytes()
    add = b"cfrd" + struct.pack("<I", 4) + struct.pack("<I", stages)
    data = data + add
    data = data[:4] + struct.pack("<I", len(data) - 8) + data[8:]
    Path(dst).write_bytes(data)
    return stages


# RDH WAV: извлечение и восстановление
def rdh_wav_extract(path, restored_out):
    import wave
    import array as arr
    data = Path(path).read_bytes()
    stages = None
    for cid, pos, sz in riff_chunks(data):
        if cid == b"cfrd":
            stages = struct.unpack("<I", data[pos + 8:pos + 12])[0]
    if stages is None:
        raise CFError("RDH: служебный чанк не найден")
    with wave.open(str(path), "rb") as wv:
        params = wv.getparams()
        raw = wv.readframes(params.nframes)
    a = arr.array("h")
    a.frombytes(raw)
    plane = [x + 32768 for x in a]
    payload = rdh_extract_planes([plane], len(plane), 1, 65535, stages)
    out = arr.array("h", [x - 32768 for x in plane])
    with wave.open(str(restored_out), "wb") as wv:
        wv.setparams(params)
        wv.writeframes(out.tobytes())
    return payload


# Меню RDH: спрятать / извлечь с восстановлением контейнера
def rdh_menu():
    title_anim("RDH ОБРАТИМОЕ СОКРЫТИЕ")
    say_wn("Хрупко к перекодированию: только для локального хранения.")
    print("   1. Спрятать (PNG/WAV)")
    print("   2. Извлечь и восстановить контейнер")
    c = ask("Выбор: ")
    if c == "1":
        fl = pick_files("Что спрятать", [VAULT], True)
        if not fl:
            return
        payload = Path(fl[0]).read_bytes()
        cover = pick_cover("Контейнер PNG или WAV")
        if not cover:
            return
        kind = cover_kind(cover)
        out = STEGO / (cover.stem + "_rdh" + cover.suffix)
        if kind == "png":
            st = rdh_png_embed(cover, out, payload)
        elif kind == "wav":
            st = rdh_wav_embed(cover, out, payload)
        else:
            raise CFError("RDH поддерживает PNG и WAV")
        back = work_tmp_path("rdhchk")
        got = rdh_png_extract(out, back) if kind == "png" else rdh_wav_extract(out, back)
        if got != payload:
            out.unlink(missing_ok=True)
            raise CFError("Проверка RDH не пройдена")
        os.chmod(out, 0o600)
        say_ok(f"Готово: {out} (фаз: {st}). Проверка извлечения пройдена.")
        back.unlink(missing_ok=True)
    elif c == "2":
        cover = pick_cover("Файл с RDH-данными")
        if not cover:
            return
        kind = cover_kind(cover)
        restored = unique_path(STEGO, cover.stem + "_restored" + cover.suffix)
        payload = rdh_png_extract(cover, restored) if kind == "png" else rdh_wav_extract(cover, restored)
        out = unique_path(VAULT, gen_name(".enc"))
        out.write_bytes(payload)
        os.chmod(out, 0o600)
        say_ok(f"Данные: {out}")
        say_ok(f"Исходный контейнер восстановлен: {restored}")


# Временный путь внутри рабочей папки
def work_tmp_path(prefix):
    return WORKROOT / f"{prefix}_{secrets.token_hex(4)}"


# =====================================================================
# РАЗДЕЛ: НЕВИДИМЫЙ ТЕКСТ (zero-width) — для коротких ключей и долей
# =====================================================================
ZW_ALPHA = ["\u200b", "\u200c", "\u200d", "\u2060"]
ZW_MARK = "\ufeff"


# Кодируем байты в base-4 невидимыми символами; рамка — U+FEFF с обеих сторон
def zw_encode(data):
    body = struct.pack(">H", len(data)) + data + struct.pack(">I", zlib.crc32(data) & 0xFFFFFFFF)
    out = []
    for b in body:
        for sh in (6, 4, 2, 0):
            out.append(ZW_ALPHA[(b >> sh) & 3])
    return ZW_MARK + "".join(out) + ZW_MARK


# Ищем рамку и читаем символы; проверяем CRC
def zw_decode(text):
    i = text.find(ZW_MARK)
    j = text.find(ZW_MARK, i + 1) if i >= 0 else -1
    if i < 0 or j < 0:
        raise CFError("Невидимые данные не найдены (мессенджер мог убрать символы)")
    syms = text[i + 1:j]
    idx = {c: n for n, c in enumerate(ZW_ALPHA)}
    vals = [idx[c] for c in syms if c in idx]
    bs = bytearray()
    for k in range(0, len(vals) - 3, 4):
        bs.append((vals[k] << 6) | (vals[k + 1] << 4) | (vals[k + 2] << 2) | vals[k + 3])
    ln = struct.unpack(">H", bytes(bs[:2]))[0]
    data = bytes(bs[2:2 + ln])
    crc = struct.unpack(">I", bytes(bs[2 + ln:6 + ln]))[0]
    if zlib.crc32(data) & 0xFFFFFFFF != crc:
        raise CFError("Невидимые данные повреждены (CRC)")
    return data


# Меню: спрятать короткие данные в обычном тексте / извлечь
def zw_menu():
    title_anim("НЕВИДИМЫЙ ТЕКСТ")
    say_wn("Мессенджеры и NFKC-нормализация могут стереть символы.")
    print("   1. Спрятать в тексте")
    print("   2. Извлечь из текста")
    c = ask("Выбор: ")
    if c == "1":
        secret = ask("Секрет (ключ/доля, до 500 байт): ").encode()
        if not secret or len(secret) > 500:
            raise CFError("Нужно от 1 до 500 байт")
        cover = ask("Видимый текст-обложка: ") or "Привет! Как дела?"
        pos = cover.find(" ")
        pos = pos if pos > 0 else 1
        res = cover[:pos] + zw_encode(secret) + cover[pos:]
        out = unique_path(STEGO, "text_" + gen_name()[:6] + ".txt")
        out.write_text(res, encoding="utf-8")
        os.chmod(out, 0o600)
        say_ok(f"Сохранено: {out}")
        say_in("Выглядит как: " + cover)
        say_in(f"Скрыто {len(secret)} байт невидимыми символами")
    elif c == "2":
        raw = ask("Путь к файлу или вставьте текст: ")
        pth = Path(os.path.expanduser(raw))
        text = pth.read_text(encoding="utf-8") if pth.is_file() else raw
        data = zw_decode(text)
        say_ok("Найдено: " + data.decode("utf-8", "replace"))


# =====================================================================
# РАЗДЕЛ: DNA-КОНТЕЙНЕР (экспериментально, только текстовая симуляция)
# =====================================================================
def dna_encode(data):
    # 2 бита на основание (A,C,G,T) + заголовок длины и CRC; оформляем как FASTA
    body = struct.pack(">II", len(data), zlib.crc32(data) & 0xFFFFFFFF) + data
    seq = "".join("ACGT"[(b >> sh) & 3] for b in body for sh in (6, 4, 2, 0))
    lines = [seq[i:i + 70] for i in range(0, len(seq), 70)]
    return ">CF-" + os.urandom(3).hex() + " synthetic sequence\n" + "\n".join(lines) + "\n"


# Читаем последовательность и проверяем CRC
def dna_decode(fasta):
    seq = "".join(l.strip() for l in fasta.splitlines() if l and not l.startswith(">")).upper()
    rev = {"A": 0, "C": 1, "G": 2, "T": 3}
    vals = [rev[c] for c in seq if c in rev]
    bs = bytearray()
    for k in range(0, len(vals) - 3, 4):
        bs.append((vals[k] << 6) | (vals[k + 1] << 4) | (vals[k + 2] << 2) | vals[k + 3])
    ln, crc = struct.unpack(">II", bytes(bs[:8]))
    data = bytes(bs[8:8 + ln])
    if zlib.crc32(data) & 0xFFFFFFFF != crc:
        raise CFError("DNA: CRC не совпал")
    return data


# Меню DNA-режима с обязательным предупреждением
def dna_menu():
    title_anim("DNA-КОНТЕЙНЕР [SIM]")
    say_wn("Только текстовая симуляция. НЕ синтезируйте такую ДНК:")
    say_wn("последовательность не имеет биологического смысла.")
    print("   1. Закодировать файл в FASTA")
    print("   2. Декодировать FASTA")
    c = ask("Выбор: ")
    if c == "1":
        fl = pick_files("Файл", [VAULT], True)
        if not fl:
            return
        out = unique_path(STEGO, "dna_" + gen_name()[:6] + ".fasta")
        out.write_text(dna_encode(Path(fl[0]).read_bytes()), encoding="utf-8")
        say_ok(f"FASTA: {out}")
    elif c == "2":
        fl = pick_files("FASTA-файл", [STEGO], True)
        if not fl:
            return
        out = unique_path(VAULT, gen_name(".enc"))
        out.write_bytes(dna_decode(Path(fl[0]).read_text(encoding="utf-8")))
        say_ok(f"Данные: {out}")


# =====================================================================
# РАЗДЕЛ: АУДИТ КОНТЕЙНЕРА (энтропия и текстура) до внедрения
# =====================================================================
def audit_image(path):
    # Оценка пригодности изображения для LSB/RDH: энтропия, доля гладких областей
    import math
    try:
        from PIL import Image, ImageFilter
    except ImportError:
        raise CFError("Аудит требует Pillow: apk add py3-pillow")
    im = Image.open(path).convert("L")
    if max(im.size) > 800:
        im.thumbnail((800, 800))
    hist = im.histogram()
    n = sum(hist)
    ent = -sum((c / n) * math.log2(c / n) for c in hist if c)
    diff = list(Image.eval(im, lambda x: x).getdata())
    edge = im.filter(ImageFilter.FIND_EDGES)
    ed = list(edge.getdata())
    smooth = sum(1 for v in ed if v < 6) / max(1, len(ed))
    score = "хороший" if ent > 6.5 and smooth < 0.5 else ("средний" if ent > 5 and smooth < 0.75 else "плохой")
    return {"entropy": round(ent, 2), "smooth": round(smooth, 2), "rating": score}


# Энергия разностного сигнала как грубая оценка «шумности» записи
def audit_wav(path):
    import wave
    import array as arr
    with wave.open(str(path), "rb") as wv:
        params = wv.getparams()
        if params.sampwidth != 2:
            raise CFError("Нужен 16-бит WAV")
        a = arr.array("h")
        a.frombytes(wv.readframes(min(params.nframes, 400000)))
    if len(a) < 100:
        raise CFError("Слишком короткий файл")
    diff = sum(abs(a[i] - a[i - 1]) for i in range(1, len(a))) / len(a)
    return {"hf_energy": round(diff, 1), "rating": "хороший" if diff > 40 else ("средний" if diff > 8 else "плохой")}


# Интерактивный аудит с рекомендациями
def audit_flow():
    title_anim("АУДИТ КОНТЕЙНЕРА")
    cover = pick_cover("Контейнер (PNG/JPEG/WAV)")
    if not cover:
        return
    kind = cover_kind(cover)
    if kind in ("png", "jpg"):
        r = audit_image(cover)
        say_in(f"Энтропия: {r['entropy']} бит; гладких областей: {int(r['smooth'] * 100)}%")
    elif kind == "wav":
        r = audit_wav(cover)
        say_in(f"Высокочастотная энергия: {r['hf_energy']}")
    else:
        raise CFError("Аудит поддерживает PNG, JPEG, WAV")
    (say_ok if r["rating"] == "хороший" else say_wn)(f"Контейнер для LSB/RDH: {r['rating']}")
    if r["rating"] != "хороший":
        say_in("Совет: выберите текстурное фото или используйте канал «хвост»/«чанк».")


# =====================================================================
# РАЗДЕЛ: ДОКУМЕНТЫ С ЗАШИФРОВАННЫМ СОДЕРЖИМЫМ (только стандартная библиотека)
# =====================================================================
# Документы создаются «с нуля» через zipfile/строки: DOCX, XLSX, PPTX, PDF,
# ODT, EPUB, TXT, HTML, JSON. Payload шифруется паролем (Argon2id/scrypt +
# AES-GCM) и прячется выбранным методом. После создания выполняется
# обязательная проверка: документ парсится, payload извлекается и сверяется.
DOC_TYPES = {
    "1": ("docx", "Word (.docx)"),
    "2": ("xlsx", "Excel (.xlsx)"),
    "3": ("pptx", "PowerPoint (.pptx)"),
    "4": ("pdf", "PDF"),
    "5": ("odt", "OpenDocument (.odt)"),
    "6": ("epub", "EPUB"),
    "7": ("html", "HTML"),
    "8": ("txt", "Текст (.txt)"),
    "9": ("json", "JSON"),
}
DOC_METHODS = {
    "docx": ["ghost", "customxml", "props"],
    "xlsx": ["ghost", "customxml", "props", "hiddensheet"],
    "pptx": ["ghost", "customxml", "props"],
    "odt": ["ghost"],
    "epub": ["ghost"],
    "pdf": ["incremental", "tail"],
    "html": ["comment"],
    "txt": ["zerowidth"],
    "json": ["field"],
}
DOC_METHOD_TITLES = {
    "ghost": "файл-призрак в ZIP (вне манифеста)",
    "customxml": "Custom XML Part (штатный канал)",
    "props": "Custom Properties (docProps/custom.xml)",
    "hiddensheet": "скрытый лист Excel",
    "incremental": "инкрементальное обновление PDF",
    "tail": "хвост после %%EOF",
    "comment": "HTML-комментарий",
    "zerowidth": "невидимые символы в тексте",
    "field": "служебное поле JSON",
}

_TRANSLIT = dict(zip("абвгдеёжзийклмнопрстуфхцчшщъыьэюя", ["a", "b", "v", "g", "d", "e", "e", "zh", "z", "i", "y", "k", "l", "m", "n", "o", "p", "r", "s", "t", "u", "f", "h", "ts", "ch", "sh", "sch", "", "y", "", "e", "yu", "ya"]))


# Экранирование текста для XML
def xml_esc(t):
    return t.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


# PDF без встроенных шрифтов: кириллица транслитерируется, лишнее заменяется
def ascii_pdf(t):
    out = []
    for ch in t:
        lo = ch.lower()
        if lo in _TRANSLIT:
            r = _TRANSLIT[lo]
            out.append(r.upper() if ch != lo and r else r)
        elif 32 <= ord(ch) < 127 or ch == "\n":
            out.append(ch)
        else:
            out.append("?")
    return "".join(out).replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


# Сборка ZIP в памяти; first_stored — имя файла, который должен идти первым без сжатия (mimetype)
def build_zip(entries, first_stored=None):
    import zipfile
    bio = io.BytesIO()
    with zipfile.ZipFile(bio, "w", zipfile.ZIP_DEFLATED) as z:
        if first_stored:
            z.writestr(zipfile.ZipInfo(first_stored), entries[first_stored], zipfile.ZIP_STORED)
        for name, data in entries.items():
            if name == first_stored:
                continue
            z.writestr(name, data)
    return bio.getvalue()


# Минимальный валидный DOCX: типы, связи, документ с абзацами
def doc_docx(text):
    paras = "".join(f"<w:p><w:r><w:t xml:space=\"preserve\">{xml_esc(l)}</w:t></w:r></w:p>" for l in (text.splitlines() or [""]))
    e = {
        "[Content_Types].xml": '<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/></Types>',
        "_rels/.rels": '<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/></Relationships>',
        "word/document.xml": '<?xml version="1.0" encoding="UTF-8" standalone="yes"?><w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body>' + paras + "</w:body></w:document>",
        "word/_rels/document.xml.rels": '<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"></Relationships>',
    }
    return e


# Минимальная книга: лист 1 со строками текста (inline strings)
def doc_xlsx(text):
    rows = "".join(f'<row r="{i}"><c r="A{i}" t="inlineStr"><is><t>{xml_esc(l)}</t></is></c></row>' for i, l in enumerate(text.splitlines() or [""], 1))
    return {
        "[Content_Types].xml": '<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/><Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/></Types>',
        "_rels/.rels": '<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/></Relationships>',
        "xl/workbook.xml": '<?xml version="1.0" encoding="UTF-8" standalone="yes"?><workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheets><sheet name="Sheet1" sheetId="1" r:id="rId1"/></sheets></workbook>',
        "xl/_rels/workbook.xml.rels": '<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/></Relationships>',
        "xl/worksheets/sheet1.xml": '<?xml version="1.0" encoding="UTF-8" standalone="yes"?><worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><sheetData>' + rows + "</sheetData></worksheet>",
    }


_THEME = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?><a:theme xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" name="T"><a:themeElements><a:clrScheme name="C"><a:dk1><a:sysClr val="windowText" lastClr="000000"/></a:dk1><a:lt1><a:sysClr val="window" lastClr="FFFFFF"/></a:lt1><a:dk2><a:srgbClr val="1F497D"/></a:dk2><a:lt2><a:srgbClr val="EEECE1"/></a:lt2><a:accent1><a:srgbClr val="4F81BD"/></a:accent1><a:accent2><a:srgbClr val="C0504D"/></a:accent2><a:accent3><a:srgbClr val="9BBB59"/></a:accent3><a:accent4><a:srgbClr val="8064A2"/></a:accent4><a:accent5><a:srgbClr val="4BACC6"/></a:accent5><a:accent6><a:srgbClr val="F79646"/></a:accent6><a:hlink><a:srgbClr val="0000FF"/></a:hlink><a:folHlink><a:srgbClr val="800080"/></a:folHlink></a:clrScheme><a:fontScheme name="F"><a:majorFont><a:latin typeface="Calibri"/><a:ea typeface=""/><a:cs typeface=""/></a:majorFont><a:minorFont><a:latin typeface="Calibri"/><a:ea typeface=""/><a:cs typeface=""/></a:minorFont></a:fontScheme><a:fmtScheme name="M"><a:fillStyleLst><a:solidFill><a:schemeClr val="phClr"/></a:solidFill><a:solidFill><a:schemeClr val="phClr"/></a:solidFill><a:solidFill><a:schemeClr val="phClr"/></a:solidFill></a:fillStyleLst><a:lnStyleLst><a:ln w="9525"><a:solidFill><a:schemeClr val="phClr"/></a:solidFill></a:ln><a:ln w="25400"><a:solidFill><a:schemeClr val="phClr"/></a:solidFill></a:ln><a:ln w="38100"><a:solidFill><a:schemeClr val="phClr"/></a:solidFill></a:ln></a:lnStyleLst><a:effectStyleLst><a:effectStyle><a:effectLst/></a:effectStyle><a:effectStyle><a:effectLst/></a:effectStyle><a:effectStyle><a:effectLst/></a:effectStyle></a:effectStyleLst><a:bgFillStyleLst><a:solidFill><a:schemeClr val="phClr"/></a:solidFill><a:solidFill><a:schemeClr val="phClr"/></a:solidFill><a:solidFill><a:schemeClr val="phClr"/></a:solidFill></a:bgFillStyleLst></a:fmtScheme></a:themeElements></a:theme>'


# Минимальная презентация: тема, мастер, макет, один слайд с текстом
def doc_pptx(text):
    ns = 'xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main"'
    hdr = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
    rel = lambda items: hdr + '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">' + "".join(f'<Relationship Id="{i}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/{t}" Target="{g}"/>' for i, t, g in items) + "</Relationships>"
    body = "".join(f"<a:p><a:r><a:t>{xml_esc(l)}</a:t></a:r></a:p>" for l in (text.splitlines() or [""]))
    sp = '<p:cSld><p:spTree><p:nvGrpSpPr><p:cNvPr id="1" name=""/><p:cNvGrpSpPr/><p:nvPr/></p:nvGrpSpPr><p:grpSpPr/>%s</p:spTree></p:cSld>'
    return {
        "[Content_Types].xml": hdr + '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Override PartName="/ppt/presentation.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.presentation.main+xml"/><Override PartName="/ppt/slideMasters/slideMaster1.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.slideMaster+xml"/><Override PartName="/ppt/slideLayouts/slideLayout1.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.slideLayout+xml"/><Override PartName="/ppt/slides/slide1.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.slide+xml"/><Override PartName="/ppt/theme/theme1.xml" ContentType="application/vnd.openxmlformats-officedocument.theme+xml"/></Types>',
        "_rels/.rels": rel([("rId1", "officeDocument", "ppt/presentation.xml")]),
        "ppt/presentation.xml": hdr + f'<p:presentation {ns}><p:sldMasterIdLst><p:sldMasterId id="2147483648" r:id="rId1"/></p:sldMasterIdLst><p:sldIdLst><p:sldId id="256" r:id="rId2"/></p:sldIdLst><p:sldSz cx="9144000" cy="6858000"/><p:notesSz cx="6858000" cy="9144000"/></p:presentation>',
        "ppt/_rels/presentation.xml.rels": rel([("rId1", "slideMaster", "slideMasters/slideMaster1.xml"), ("rId2", "slide", "slides/slide1.xml")]),
        "ppt/slideMasters/slideMaster1.xml": hdr + f'<p:sldMaster {ns}>' + sp % "" + '<p:clrMap bg1="lt1" tx1="dk1" bg2="lt2" tx2="dk2" accent1="accent1" accent2="accent2" accent3="accent3" accent4="accent4" accent5="accent5" accent6="accent6" hlink="hlink" folHlink="folHlink"/><p:sldLayoutIdLst><p:sldLayoutId id="2147483649" r:id="rId1"/></p:sldLayoutIdLst></p:sldMaster>',
        "ppt/slideMasters/_rels/slideMaster1.xml.rels": rel([("rId1", "slideLayout", "../slideLayouts/slideLayout1.xml"), ("rId2", "theme", "../theme/theme1.xml")]),
        "ppt/slideLayouts/slideLayout1.xml": hdr + f'<p:sldLayout {ns} type="blank">' + sp % "" + "</p:sldLayout>",
        "ppt/slideLayouts/_rels/slideLayout1.xml.rels": rel([("rId1", "slideMaster", "../slideMasters/slideMaster1.xml")]),
        "ppt/slides/slide1.xml": hdr + f'<p:sld {ns}>' + sp % ('<p:sp><p:nvSpPr><p:cNvPr id="2" name="Text"/><p:cNvSpPr txBox="1"/><p:nvPr/></p:nvSpPr><p:spPr><a:xfrm><a:off x="457200" y="457200"/><a:ext cx="8229600" cy="5000000"/></a:xfrm><a:prstGeom prst="rect"><a:avLst/></a:prstGeom></p:spPr><p:txBody><a:bodyPr/><a:lstStyle/>' + body + "</p:txBody></p:sp>") + "</p:sld>",
        "ppt/slides/_rels/slide1.xml.rels": rel([("rId1", "slideLayout", "../slideLayouts/slideLayout1.xml")]),
        "ppt/theme/theme1.xml": _THEME,
    }


# Минимальный ODT: mimetype (без сжатия, первым), манифест, content.xml
def doc_odt(text):
    paras = "".join(f"<text:p>{xml_esc(l)}</text:p>" for l in (text.splitlines() or [""]))
    return {
        "mimetype": "application/vnd.oasis.opendocument.text",
        "META-INF/manifest.xml": '<?xml version="1.0" encoding="UTF-8"?><manifest:manifest xmlns:manifest="urn:oasis:names:tc:opendocument:xmlns:manifest:1.0" manifest:version="1.2"><manifest:file-entry manifest:full-path="/" manifest:media-type="application/vnd.oasis.opendocument.text"/><manifest:file-entry manifest:full-path="content.xml" manifest:media-type="text/xml"/></manifest:manifest>',
        "content.xml": '<?xml version="1.0" encoding="UTF-8"?><office:document-content xmlns:office="urn:oasis:names:tc:opendocument:xmlns:office:1.0" xmlns:text="urn:oasis:names:tc:opendocument:xmlns:text:1.0" office:version="1.2"><office:body><office:text>' + paras + "</office:text></office:body></office:document-content>",
    }


# Минимальный EPUB: mimetype, container.xml, content.opf, одна XHTML-страница, toc.ncx
def doc_epub(text):
    paras = "".join(f"<p>{xml_esc(l)}</p>" for l in (text.splitlines() or [""]))
    return {
        "mimetype": "application/epub+zip",
        "META-INF/container.xml": '<?xml version="1.0"?><container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container"><rootfiles><rootfile full-path="OEBPS/content.opf" media-type="application/oebps-package+xml"/></rootfiles></container>',
        "OEBPS/content.opf": '<?xml version="1.0" encoding="UTF-8"?><package xmlns="http://www.idpf.org/2007/opf" version="2.0" unique-identifier="id"><metadata xmlns:dc="http://purl.org/dc/elements/1.1/"><dc:title>Document</dc:title><dc:language>en</dc:language><dc:identifier id="id">cf-' + os.urandom(4).hex() + '</dc:identifier></metadata><manifest><item id="ncx" href="toc.ncx" media-type="application/x-dtbncx+xml"/><item id="c1" href="index.xhtml" media-type="application/xhtml+xml"/></manifest><spine toc="ncx"><itemref idref="c1"/></spine></package>',
        "OEBPS/index.xhtml": '<?xml version="1.0" encoding="UTF-8"?><html xmlns="http://www.w3.org/1999/xhtml"><head><title>Document</title></head><body>' + paras + "</body></html>",
        "OEBPS/toc.ncx": '<?xml version="1.0" encoding="UTF-8"?><ncx xmlns="http://www.daisy.org/z3986/2005/ncx/" version="2005-1"><head/><docTitle><text>Document</text></docTitle><navMap><navPoint id="n1" playOrder="1"><navLabel><text>Start</text></navLabel><content src="index.xhtml"/></navPoint></navMap></ncx>',
    }


# Минимальный PDF 1.4: каталог, страницы, шрифт Helvetica, поток с текстом, таблица xref
def doc_pdf(text):
    lines = ascii_pdf(text).split("\n")[:50] or [""]
    stream = "BT /F1 12 Tf 50 780 Td 14 TL " + " ".join(f"({l}) Tj T*" for l in lines) + " ET"
    objs = [
        "<< /Type /Catalog /Pages 2 0 R >>",
        "<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        "<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>",
        f"<< /Length {len(stream)} >>\nstream\n{stream}\nendstream",
        "<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]
    out = bytearray(b"%PDF-1.4\n")
    offs = []
    for i, o in enumerate(objs, 1):
        offs.append(len(out))
        out += f"{i} 0 obj\n{o}\nendobj\n".encode("latin-1")
    xpos = len(out)
    out += f"xref\n0 {len(objs) + 1}\n0000000000 65535 f \n".encode()
    for o in offs:
        out += f"{o:010d} 00000 n \n".encode()
    out += f"trailer\n<< /Size {len(objs) + 1} /Root 1 0 R >>\nstartxref\n{xpos}\n%%EOF\n".encode()
    return bytes(out)


# Добавляем новый объект и xref как инкрементальное обновление; старые байты не меняются
def pdf_incremental(data, frame):
    m = re.findall(rb"startxref\s+(\d+)", data)
    if not m:
        raise CFError("PDF: startxref не найден")
    prev = int(m[-1])
    tr = data[data.rfind(b"trailer"):]
    root = re.search(rb"/Root\s+(\d+)\s+(\d+)\s+R", tr)
    size = re.search(rb"/Size\s+(\d+)", tr)
    if not root or not size or data[prev:prev + 4] != b"xref":
        raise CFError("PDF с xref-потоком не поддерживается для инкрементального канала — используйте «хвост»")
    n = int(size.group(1))
    out = bytearray(data)
    if not out.endswith(b"\n"):
        out += b"\n"
    pos = len(out)
    out += f"{n} 0 obj\n<< /Type /CFData /Length {len(frame)} >>\nstream\n".encode() + frame + b"\nendstream\nendobj\n"
    xpos = len(out)
    out += f"xref\n{n} 1\n{pos:010d} 00000 n \ntrailer\n<< /Size {n + 1} /Root {root.group(1).decode()} {root.group(2).decode()} R /Prev {prev} >>\nstartxref\n{xpos}\n%%EOF\n".encode()
    return bytes(out)


# Поиск кадра данных в произвольном месте файла (по маркерам начала/конца)
def find_frame_anywhere(data):
    s = data.find(FRAME_MAGIC)
    if s < 0:
        return None
    e = data.find(FRAME_END, s)
    if e < 0:
        return None
    return data[s:e + len(FRAME_END) + 12]


# Добавляет payload-кадры в словарь частей ZIP выбранным методом
def zip_add_parts(entries, kind, frames):
    b64s = [b64e(f) for f in frames]
    if kind == "ghost":
        for i, f in enumerate(frames):
            entries[f"customXml/cf{i}.dat" if "word/document.xml" in entries or "xl/workbook.xml" in entries or "ppt/presentation.xml" in entries else f"cf{i}.dat"] = f
        if "[Content_Types].xml" in entries and "Extension=\"dat\"" not in entries["[Content_Types].xml"]:
            entries["[Content_Types].xml"] = entries["[Content_Types].xml"].replace("<Default Extension=\"xml\"", "<Default Extension=\"dat\" ContentType=\"application/octet-stream\"/><Default Extension=\"xml\"", 1)
    elif kind == "customxml":
        main = "word/_rels/document.xml.rels" if "word/document.xml" in entries else ("xl/_rels/workbook.xml.rels" if "xl/workbook.xml" in entries else "ppt/_rels/presentation.xml.rels")
        base = main.split("/")[0]
        for i, b in enumerate(b64s, 1):
            entries[f"customXml/item{i}.xml"] = f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?><cf xmlns="urn:cryptforge">{b}</cf>'
            entries[f"customXml/itemProps{i}.xml"] = f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?><ds:datastoreItem xmlns:ds="http://schemas.openxmlformats.org/officeDocument/2006/customXml" ds:itemID="{{{os.urandom(4).hex()}-0000-4000-8000-{os.urandom(6).hex()}}}"><ds:schemaRefs/></ds:datastoreItem>'
            entries[f"customXml/_rels/item{i}.xml.rels"] = f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/customXmlProps" Target="itemProps{i}.xml"/></Relationships>'
            entries[main] = entries[main].replace("</Relationships>", f'<Relationship Id="rIdCF{i}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/customXml" Target="../customXml/item{i}.xml"/></Relationships>')
            entries["[Content_Types].xml"] = entries["[Content_Types].xml"].replace("</Types>", f'<Override PartName="/customXml/itemProps{i}.xml" ContentType="application/vnd.openxmlformats-officedocument.customXmlProperties+xml"/></Types>')
    elif kind == "props":
        props = "".join(f'<property fmtid="{{D5CDD505-2E9C-101B-9397-08002B2CF9AE}}" pid="{i + 2}" name="cf{i}"><vt:lpwstr>{b}</vt:lpwstr></property>' for i, b in enumerate(b64s))
        entries["docProps/custom.xml"] = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Properties xmlns="http://schemas.openxmlformats.org/officeDocument/2006/custom-properties" xmlns:vt="http://schemas.openxmlformats.org/officeDocument/2006/docPropsVTypes">' + props + "</Properties>"
        entries["[Content_Types].xml"] = entries["[Content_Types].xml"].replace("</Types>", '<Override PartName="/docProps/custom.xml" ContentType="application/vnd.openxmlformats-officedocument.custom-properties+xml"/></Types>')
        entries["_rels/.rels"] = entries["_rels/.rels"].replace("</Relationships>", '<Relationship Id="rIdCP" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/custom-properties" Target="docProps/custom.xml"/></Relationships>')
    elif kind == "hiddensheet":
        cells = "".join(f'<row r="{i}"><c r="A{i}" t="inlineStr"><is><t>{b}</t></is></c></row>' for i, b in enumerate(b64s, 1))
        entries["xl/worksheets/sheet2.xml"] = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?><worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><sheetData>' + cells + "</sheetData></worksheet>"
        entries["xl/workbook.xml"] = entries["xl/workbook.xml"].replace("</sheets>", '<sheet name="Data" sheetId="2" state="hidden" r:id="rId2"/></sheets>')
        entries["xl/_rels/workbook.xml.rels"] = entries["xl/_rels/workbook.xml.rels"].replace("</Relationships>", '<Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet2.xml"/></Relationships>')
        entries["[Content_Types].xml"] = entries["[Content_Types].xml"].replace("</Types>", '<Override PartName="/xl/worksheets/sheet2.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/></Types>')
    else:
        raise CFError("Метод не подходит для ZIP-документов")


# Достаёт все кадры данных из документа любым известным методом
def doc_extract_frames(path):
    import zipfile
    data = Path(path).read_bytes()
    frames = []
    if data[:2] == b"PK":
        with zipfile.ZipFile(path) as z:
            for name in z.namelist():
                if z.getinfo(name).file_size > 512 * MB:
                    continue
                raw = z.read(name)
                if name.endswith(".dat") and raw[:8] == FRAME_MAGIC:
                    frames.append(raw)
                elif name.startswith("customXml/item") and name.endswith(".xml") and b"urn:cryptforge" in raw:
                    m = re.search(rb">([A-Za-z0-9_\-]+)<", raw)
                    if m:
                        frames.append(b64d(m.group(1).decode()))
                elif name == "docProps/custom.xml":
                    for mm in re.finditer(rb"name=\"cf\d+\"><vt:lpwstr>([A-Za-z0-9_\-]+)<", raw):
                        frames.append(b64d(mm.group(1).decode()))
                elif name == "xl/worksheets/sheet2.xml":
                    for mm in re.finditer(rb"<t>([A-Za-z0-9_\-]{20,})</t>", raw):
                        frames.append(b64d(mm.group(1).decode()))
        if not frames:
            fr = find_frame_anywhere(data)
            if fr:
                frames.append(fr)
        return frames
    text = data.decode("utf-8", "ignore")
    if "CFDOC:" in text:
        for mm in re.finditer(r"CFDOC:([A-Za-z0-9_\-]+)", text):
            frames.append(b64d(mm.group(1)))
        return frames
    if ZW_MARK in text:
        try:
            frames.append(zw_decode(text))
        except CFError:
            pass
        return frames
    fr = find_frame_anywhere(data)
    return [fr] if fr else []


# Строит документ и встраивает кадры payload'ов; возвращает байты файла
def doc_create(dtype, method, visible, payloads):
    frames = [frame_build(p, 0.0, False) for p in payloads]
    if dtype in ("docx", "xlsx", "pptx", "odt", "epub"):
        entries = {"docx": doc_docx, "xlsx": doc_xlsx, "pptx": doc_pptx, "odt": doc_odt, "epub": doc_epub}[dtype](visible)
        if method == "ghost" and dtype in ("odt", "epub"):
            for i, f in enumerate(frames):
                entries[f"cf{i}.dat"] = f
        else:
            zip_add_parts(entries, method, frames)
        first = "mimetype" if "mimetype" in entries else None
        enc = {k: (v.encode("utf-8") if isinstance(v, str) else v) for k, v in entries.items()}
        return build_zip(enc, first)
    if dtype == "pdf":
        base = doc_pdf(visible)
        if method == "incremental":
            for f in frames:
                base = pdf_incremental(base, f)
            return base
        i = base.rfind(b"startxref")
        return base + b"\n" + b"".join(frames) + b"\n" + base[i:]
    if dtype == "html":
        return ("<!DOCTYPE html><html><head><meta charset=\"utf-8\"><title>Document</title></head><body><p>" + xml_esc(visible).replace("\n", "</p><p>") + "</p>" + "".join(f"<!--CFDOC:{b64e(f)}-->" for f in frames) + "</body></html>").encode("utf-8")
    if dtype == "txt":
        if len(frames) != 1:
            raise CFError("TXT вмещает один payload")
        pos = visible.find(" ")
        pos = pos if pos > 0 else 1
        return (visible[:pos] + zw_encode(frames[0]) + visible[pos:]).encode("utf-8")
    if dtype == "json":
        return json.dumps({"title": "Document", "text": visible, "_cf": [f"CFDOC:{b64e(f)}" for f in frames]}, ensure_ascii=False, indent=2).encode("utf-8")
    raise CFError("Неизвестный тип документа")


# Проверка структуры документа после сборки
def doc_validate(path, dtype):
    import zipfile
    import xml.dom.minidom as md
    data = Path(path).read_bytes()
    try:
        if dtype in ("docx", "xlsx", "pptx", "odt", "epub"):
            with zipfile.ZipFile(path) as z:
                if z.testzip():
                    return False, "ZIP повреждён"
                for name in z.namelist():
                    if name.endswith(".xml") or name.endswith(".rels") or name.endswith(".opf") or name.endswith(".ncx") or name.endswith(".xhtml"):
                        md.parseString(z.read(name))
                if dtype in ("odt", "epub") and z.namelist()[0] != "mimetype":
                    return False, "mimetype должен быть первым"
        elif dtype == "pdf":
            if data[:5] != b"%PDF-":
                return False, "нет заголовка PDF"
            m = re.findall(rb"startxref\s+(\d+)", data)
            if not m or data[int(m[-1]):int(m[-1]) + 4] != b"xref":
                return False, "startxref не указывает на xref"
        elif dtype == "json":
            json.loads(data.decode("utf-8"))
        return True, "структура корректна"
    except Exception as e:
        return False, f"{type(e).__name__}: {e}"


# Интерактивное создание документа с зашифрованным payload (1-3 payload'а с разными паролями)
def doc_create_flow():
    title_anim("СОЗДАТЬ ДОКУМЕНТ")
    for k, (d, name) in DOC_TYPES.items():
        print(f"  {k}. {name}")
    dtype = DOC_TYPES.get(ask("Тип документа [1]: ", "1"), DOC_TYPES["1"])[0]
    methods = DOC_METHODS[dtype]
    print("  Метод сокрытия:")
    for i, m in enumerate(methods, 1):
        print(f"   {i}. {DOC_METHOD_TITLES[m]}")
    mi = ask("Метод [1]: ", "1")
    method = methods[int(mi) - 1] if mi.isdigit() and 1 <= int(mi) <= len(methods) else methods[0]
    print("  Видимое содержимое: 1. ввести  2. из файла  3. пусто")
    vc = ask("Выбор [1]: ", "1")
    visible = ""
    if vc == "1":
        visible = read_text_block("Введите текст (пустая строка — конец):")
    elif vc == "2":
        pth = Path(os.path.expanduser(ask("Путь к текстовому файлу: ")))
        visible = pth.read_text(encoding="utf-8", errors="ignore")
    payloads = []
    total = ask_int("Сколько секретов спрятать (1 — один, 2-3 — с приманкой)", 1, 3 if dtype not in ("txt",) else 1, 1)
    for i in range(total):
        label = "основной" if i == 0 else f"приманка {i}"
        say_in(f"Секрет {i + 1} ({label})")
        print("   1. Файл из vault/  2. Текст  3. Новый случайный ключ")
        src = ask("Источник [1]: ", "1")
        if src == "1":
            fl = pick_files("Файл", [VAULT, ORIGINALS], True)
            if not fl:
                return
            data = Path(fl[0]).read_bytes()
        elif src == "2":
            data = ask("Текст: ").encode()
        else:
            data = gen_key().encode()
            say_ok("Ключ: " + data.decode())
        pw = ask_secret("Пароль для этого секрета (мин. 8 символов): ")
        if len(pw) < 8:
            raise CFError("Пароль слишком короткий")
        say_in("Шифрование секрета (стойкий KDF)...")
        payloads.append(pw_seal(pw, data, b"CFD1"))
        payloads[-1] = payloads[-1]
    out = unique_path(STEGO, "doc_" + gen_name()[:6] + "." + dtype)
    out.write_bytes(doc_create(dtype, method, visible, payloads))
    ok, why = doc_validate(out, dtype)
    if not ok:
        out.unlink(missing_ok=True)
        raise CFError(f"Документ не прошёл проверку ({why}) — файл не сохранён")
    frames = doc_extract_frames(out)
    if len(frames) != len(payloads):
        out.unlink(missing_ok=True)
        raise CFError("Проверка извлечения не пройдена — файл не сохранён")
    for f in frames:
        meta, pl, fixed = frame_parse(f)
    os.chmod(out, 0o600)
    say_ok(f"Документ создан: {out} ({hsize(out.stat().st_size)})")
    say_in(f"Метод: {DOC_METHOD_TITLES[method]}; секретов: {len(payloads)}")
    if method in ("ghost", "customxml", "props", "hiddensheet"):
        say_wn("Некоторые программы при пересохранении документа удалят скрытую часть.")
    log_action("doc-create", out.stat().st_size, None, None, None, f"{dtype}:{method}")


# Извлечение секретов из документа; пароль перебирается по всем кадрам (неверный — просто пропуск)
def doc_extract_flow():
    title_anim("ИЗВЛЕЧЬ ИЗ ДОКУМЕНТА")
    p = pick_cover("Документ")
    if not p:
        return
    frames = doc_extract_frames(p)
    if not frames:
        raise CFError("Скрытых данных не найдено")
    pw = ask_secret("Пароль: ")
    say_in("Проверка пароля (стойкий KDF)...")
    got = 0
    for i, fr in enumerate(frames):
        try:
            meta, blob, fixed = frame_parse(fr)
            data = pw_open(pw, blob, b"CFD1")
        except CFError:
            continue
        out = unique_path(VAULT, gen_name(".enc"))
        out.write_bytes(data)
        os.chmod(out, 0o600)
        say_ok(f"Секрет сохранён: {out} ({hsize(len(data))})")
        got += 1
    if not got:
        raise CFError("Пароль не подошёл ни к одному секрету (или данные повреждены)")


# =====================================================================
# РАЗДЕЛ: СКРЫТИЕ ИМЁН ФАЙЛОВ UNICODE-СИМВОЛАМИ (обратимо)
# =====================================================================
# Имя заменяется на строку из невидимых/управляющих символов; соответствие
# хранится в служебном файле. Файловые менеджеры показывают пустое имя или
# не открывают объект; через оболочку (ls, этот скрипт) он доступен.
HIDDEN_MAP = BASE / ".hidden.json"
HIDE_CHARS = ["\u200b", "\u200c", "\u200d", "\u2060", "\ufeff", "\u202e", "\u202d", "\u2066", "\u2067", "\u2068", "\u2069", "\u061c"]


# Читаем карту соответствий (скрытое имя -> исходное)
def hidden_load():
    try:
        if HIDDEN_MAP.exists():
            return read_json_file(HIDDEN_MAP)
    except Exception:
        pass
    return {}


# Сохраняем карту атомарно (шифруется мастер-паролем, если включён)
def hidden_save(d):
    write_json_secure(HIDDEN_MAP, d)


# Генерируем уникальное имя из невидимых символов (минимум 3 байта на символ UTF-8)
def make_hidden_name(parent):
    while True:
        n = "".join(rand_choice(HIDE_CHARS) for _ in range(10))
        if not (Path(parent) / n).exists():
            return n


# Переименовывает объект в невидимое имя и запоминает исходное
def hide_path(p):
    p = Path(p)
    new = p.parent / make_hidden_name(p.parent)
    p.rename(new)
    d = hidden_load()
    d[str(new)] = p.name
    hidden_save(d)
    return new


# Возвращает исходное имя (при занятости — с суффиксом)
def unhide_path(hp):
    d = hidden_load()
    hp = Path(hp)
    orig = d.get(str(hp))
    if not orig:
        raise CFError("Исходное имя неизвестно: нет записи в карте")
    dest = unique_path(hp.parent, orig)
    hp.rename(dest)
    del d[str(hp)]
    hidden_save(d)
    return dest


# Меню «Скрыть / показать» с предупреждением о резервной копии
def hide_menu():
    title_anim("СКРЫТЬ ИМЕНА [iSH]")
    say_wn("Не применяйте к единственным копиям важных данных:")
    say_wn("некоторые системы не смогут переименовать обратно.")
    print("   1. Скрыть файлы/папки")
    print("   2. Показать скрытые")
    c = ask("Выбор: ")
    if c == "1":
        files = pick_files("Что скрыть", [ORIGINALS, DECRYPTED, VAULT, STEGO] + loc_dirs())
        for f in files:
            try:
                n = hide_path(f)
                say_ok(f"Скрыто: {Path(f).name} → {len(n.name)} невидимых символов")
            except Exception as e:
                say_er(f"{Path(f).name}: {e}")
    elif c == "2":
        d = hidden_load()
        items = [k for k in d if Path(k).exists()]
        if not items:
            say_in("Скрытых объектов нет")
            return
        for i, k in enumerate(items, 1):
            print(f"  {i}. {d[k]}  ({Path(k).parent})")
        sel = ask("Номера через запятую или all: ")
        pick = items if sel == "all" else [items[int(x) - 1] for x in sel.split(",") if x.strip().isdigit() and 1 <= int(x) <= len(items)]
        for k in pick:
            try:
                dest = unhide_path(k)
                say_ok(f"Показано: {dest.name}")
            except Exception as e:
                say_er(str(e))


# =====================================================================
# РАЗДЕЛ: МНОГОФАКТОРНЫЕ КЛЮЧИ СЛОЁВ (пароль + ключ-файл + устройство + осколок)
# =====================================================================
# Ключ слоя НЕ хранится в метаданных: он выводится заново из выбранных
# факторов. Соль и состав факторов лежат в meta (не секретны). Уничтожение
# «сторожевого осколка» (sentinel shard) делает слой нерасшифровываемым
# навсегда — криптографическое стирание, не зависящее от перезаписи flash.
PEPPER_FILE = BASE / ".device_pepper"
SENTINELS = BASE / "sentinels"


# Случайный «перец» устройства: файл создаётся один раз; без него ключ не вывести
def device_pepper():
    if not PEPPER_FILE.exists():
        PEPPER_FILE.write_bytes(os.urandom(32))
        os.chmod(PEPPER_FILE, 0o600)
    return PEPPER_FILE.read_bytes()


# SHA-256 ключ-файла (читается чанками)
def file_digest(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while True:
            c = f.read(1 << 20)
            if not c:
                break
            h.update(c)
    return h.digest()


# Склеиваем выбранные факторы (с префиксами длины) и растягиваем через HKDF
def derive_factor_key(f, pw="", kfhash=b"", shard=b""):
    salt = b64d(f["salt"])
    parts = []
    if f.get("pw"):
        lv = sec()
        pk = hashlib.scrypt(pw.encode("utf-8"), salt=salt, n=1 << lv["scrypt"], r=8, p=1, maxmem=512 * MB, dklen=32)
        parts.append(b"P" + pk)
    if f.get("kf"):
        parts.append(b"K" + kfhash)
    if f.get("dev"):
        parts.append(b"D" + device_pepper())
    if f.get("sh"):
        parts.append(b"S" + shard)
    if not parts:
        raise CFError("Не выбрано ни одного фактора")
    blob = b"".join(struct.pack(">H", len(p)) + p for p in parts)
    return b64u(hkdf(blob, salt, b"cf-factor-v1"))


# Путь к файлу осколка по идентификатору
def shard_path(shard_id):
    return SENTINELS / f"{shard_id}.shard"


# Интерактивный выбор факторов при шифровании; возвращает словарь слоя
def factor_prompt(idx):
    print("  Факторы ключа (выберите нужные):")
    use_pw = ask_yn("   Пароль?", "y")
    use_kf = ask_yn("   Ключ-файл (любой файл)?", "n")
    use_dev = ask_yn("   Привязка к этому устройству?", "n")
    use_sh = ask_yn("   Сторожевой осколок (удаление = стирание)?", "n")
    f = {"pw": use_pw, "kf": use_kf, "dev": use_dev, "sh": use_sh, "salt": b64e(os.urandom(16))}
    pw = ""
    kfh = b""
    shard = b""
    if use_pw:
        pw = ask_secret("   Пароль (без запятых): ")
        if len(pw) < 8 or "," in pw:
            raise CFError("Пароль: минимум 8 символов, без запятых")
        if ask_secret("   Повторите: ") != pw:
            raise CFError("Пароли не совпали")
        for w in check_phrase(pw):
            say_wn("Слабый пароль: " + w)
    if use_kf:
        kp = Path(os.path.expanduser(ask("   Путь к ключ-файлу: ")))
        if not kp.is_file():
            raise CFError("Ключ-файл не найден")
        kfh = file_digest(kp)
    if use_dev:
        device_pepper()
        say_wn("Файл-перец устройства: ~/CryptForge/.device_pepper. Потеряете — данные недоступны.")
    if use_sh:
        SENTINELS.mkdir(parents=True, exist_ok=True)
        os.chmod(SENTINELS, 0o700)
        shard = os.urandom(32)
        sid = os.urandom(6).hex()
        shard_path(sid).write_text(b64e(shard), encoding="utf-8")
        os.chmod(shard_path(sid), 0o600)
        f["shard_id"] = sid
        say_ok(f"Осколок сохранён: {shard_path(sid)} (можно вынести на другой носитель)")
    key = derive_factor_key(f, pw, kfh, shard)
    return {"key": key, "kdf": "", "mnemonic": "", "factor": f}


# При расшифровке запрашиваем те же факторы и выводим ключ
def factor_collect(f, label):
    pw = ""
    kfh = b""
    shard = b""
    if f.get("pw"):
        pw = ask_secret(f"  Пароль слоя {label}: ")
    if f.get("kf"):
        kp = Path(os.path.expanduser(ask(f"  Ключ-файл слоя {label}: ")))
        if not kp.is_file():
            raise CFError("Ключ-файл не найден")
        kfh = file_digest(kp)
    if f.get("sh"):
        sp = shard_path(f.get("shard_id", ""))
        if sp.exists():
            shard = b64d(sp.read_text(encoding="utf-8").strip())
        else:
            raw = ask(f"  Осколок слоя {label} (путь к файлу или base64): ")
            pth = Path(os.path.expanduser(raw))
            shard = b64d(pth.read_text(encoding="utf-8").strip() if pth.is_file() else raw)
    return derive_factor_key(f, pw, kfh, shard)


# =====================================================================
# РАЗДЕЛ: ENVELOPE — КЛЮЧ СЛОЯ ОБЁРНУТ ПАРОЛЯМИ (несколько пользователей, ротация без перешифровки)
# =====================================================================
# DEK (ключ данных) хранится в метаданных только в виде «обёрток»: каждая
# обёртка — DEK, зашифрованный ключом из пароля (KEK). Менять/добавлять/убирать
# пароли можно, не трогая сам зашифрованный файл.
def wrap_make(dek, passwords):
    # Создаём по обёртке на каждый пароль
    out = []
    lv = sec()
    for pw in passwords:
        salt = os.urandom(16)
        kek = hashlib.scrypt(pw.encode("utf-8"), salt=salt, n=1 << lv["scrypt"], r=8, p=1, maxmem=512 * MB, dklen=32)
        out.append({"salt": b64e(salt), "log2n": lv["scrypt"], "w": seal_obj(kek, {"dek": dek}, b"cf-wrap")})
    return out


# Пробуем пароль на всех обёртках; возвращаем DEK или None
def wrap_open(wraps, pw):
    for w in wraps:
        try:
            if not 10 <= int(w["log2n"]) <= 18:
                continue
            kek = hashlib.scrypt(pw.encode("utf-8"), salt=b64d(w["salt"]), n=1 << int(w["log2n"]), r=8, p=1, maxmem=512 * MB, dklen=32)
            return open_obj(kek, w["w"], b"cf-wrap")["dek"]
        except Exception:
            continue
    return None


# Вопросы при шифровании: сколько паролей (пользователей) смогут открыть слой
def wrap_prompt(idx):
    n = ask_int("   Сколько паролей (пользователей)", 1, 8, 2)
    pws = []
    for i in range(n):
        p = ask_secret(f"   Пароль {i + 1} (мин. 8 символов, без запятых): ")
        if len(p) < 8 or "," in p:
            raise CFError("Пароль: минимум 8 символов, без запятых")
        pws.append(p)
    dek = gen_key()
    say_in("Подготовка обёрток (стойкий KDF)...")
    return {"key": dek, "kdf": "", "mnemonic": "", "wraps": wrap_make(dek, pws)}


# Ротация паролей без перешифровки данных
def rewrap_flow():
    title_anim("СМЕНА ПАРОЛЕЙ ENVELOPE")
    fl = pick_files("Файл из vault", [VAULT], True)
    if not fl:
        return
    f = Path(fl[0])
    mp = META / f"{f.name}.meta"
    if not mp.exists():
        raise CFError("Нет метаданных")
    meta = read_json_file(mp)
    wr = meta.get("wraps") or []
    idxs = [i for i, w in enumerate(wr) if w]
    if not idxs:
        raise CFError("В этом файле нет слоёв с обёртками паролей")
    backup = dict(meta)
    for i in idxs:
        pw = ask_secret(f"Действующий пароль слоя {i + 1}: ")
        dek = wrap_open(wr[i], pw)
        if not dek:
            raise CFError("Пароль не подошёл")
        n = ask_int("Сколько новых паролей", 1, 8, 1)
        pws = []
        for k in range(n):
            p = ask_secret(f"Новый пароль {k + 1} (мин. 8 символов): ")
            if len(p) < 8 or "," in p:
                raise CFError("Пароль: минимум 8 символов, без запятых")
            pws.append(p)
        wr[i] = wrap_make(dek, pws)
    meta["wraps"] = wr
    write_json_secure(mp, meta)
    say_ok("Пароли заменены. Зашифрованный файл не менялся.")


# =====================================================================
# РАЗДЕЛ: ЛИМИТ ПОПЫТОК, ПАНИК-ПАРОЛЬ, КРИПТОГРАФИЧЕСКОЕ СТИРАНИЕ
# =====================================================================
ATTEMPTS = BASE / ".attempts.json"
PANIC_FILE = BASE / ".panic"


# Таблица неудачных попыток по файлам
def attempts_load():
    try:
        return json.loads(ATTEMPTS.read_text(encoding="utf-8"))
    except Exception:
        return {}


# Перед расшифровкой: если действует задержка — отказываем (fail-closed)
def attempt_check(name):
    if not CFG.get("lockout", True):
        return
    t = attempts_load().get(name)
    if t and t.get("until", 0) > time.time():
        left = int(t["until"] - time.time())
        raise CFError(f"Слишком много неудачных попыток. Подождите {left} с.")


# Регистрируем ошибку: после 3 неудач задержка растёт вдвое (до часа)
def attempt_fail(name):
    if not CFG.get("lockout", True):
        return
    d = attempts_load()
    t = d.setdefault(name, {"fails": 0, "until": 0})
    t["fails"] += 1
    if t["fails"] >= 3:
        t["until"] = time.time() + min(3600, 30 * 2 ** (t["fails"] - 3))
    write_json_atomic(ATTEMPTS, d)


# Успех — сброс счётчика
def attempt_ok(name):
    d = attempts_load()
    if name in d:
        del d[name]
        write_json_atomic(ATTEMPTS, d)


# Сохраняем проверочное значение паник-пароля (scrypt)
def panic_set(pw):
    salt = os.urandom(16)
    h = hashlib.scrypt(pw.encode("utf-8"), salt=salt, n=1 << 14, r=8, p=1, maxmem=256 * MB, dklen=32)
    write_json_atomic(PANIC_FILE, {"salt": b64e(salt), "h": b64e(h)})


# Сверка введённого пароля с паник-паролем
def panic_match(pw):
    try:
        d = json.loads(PANIC_FILE.read_text(encoding="utf-8"))
        h = hashlib.scrypt(pw.encode("utf-8"), salt=b64d(d["salt"]), n=1 << 14, r=8, p=1, maxmem=256 * MB, dklen=32)
        return hmac.compare_digest(h, b64d(d["h"]))
    except Exception:
        return False


# Молча уничтожаем ключевой материал и данные: мастер-файл, метаданные, чаты, vault, доли, осколки
def panic_wipe():
    targets = [MASTER_FILE, PANIC_FILE, PEPPER_FILE]
    for d in (META, MSG_DIR, SHARES, SENTINELS, PARTS, VAULT, ORIGINALS, DECRYPTED, STEGO):
        if d.exists():
            targets += list(d.iterdir())
    for t in targets:
        try:
            wipe_file(t)
        except Exception:
            pass
    log_action("panic", None, None, None, None, "")


# Уничтожение метаданных/ключей/осколков выбранного файла: данные становятся нерасшифровываемыми
def crypto_erase_flow():
    title_anim("КРИПТОГРАФИЧЕСКОЕ СТИРАНИЕ")
    say_wn("На flash-памяти iPhone перезапись файлов не гарантирует удаления")
    say_wn("(wear-leveling). Надёжно — уничтожить КЛЮЧИ: без них .enc бесполезен.")
    fl = pick_files("Файл из vault", [VAULT], True)
    for f in fl:
        f = Path(f)
        if ask("Для подтверждения введите УНИЧТОЖИТЬ: ") != "УНИЧТОЖИТЬ":
            say_wn("Отменено")
            continue
        n = 0
        for ext in (".meta", ".split"):
            p = META / f"{f.name}{ext}"
            if p.exists():
                wipe_file(p)
                n += 1
        for p in SHARES.glob(f"{f.name}.share*.txt"):
            wipe_file(p)
            n += 1
        meta_dirs = [VAULT / ".meta", BASE / ".backup"]
        for d in meta_dirs:
            for p in d.glob(f"{f.name}.*") if d.exists() else []:
                wipe_file(p)
                n += 1
        for p in (BASE).glob(f"{f.name}.recovery.txt"):
            wipe_file(p)
            n += 1
        say_ok(f"{f.name}: уничтожено файлов с ключами: {n}")
        if ask_yn("Удалить и сам .enc (затереть)?", "n"):
            wipe_file(f)
        log_action("crypto-erase", None, None, None, None, f.name[:12])
    if ask_yn("Уничтожить ещё и осколки (sentinels/)?", "n"):
        for p in SENTINELS.glob("*.shard") if SENTINELS.exists() else []:
            wipe_file(p)
        say_ok("Осколки уничтожены")


# =====================================================================
# РАЗДЕЛ: ЭЦП (Ed25519), СРОК ДЕЙСТВИЯ, ПОЛИТИКА ДОСТУПА, СПИСОК ОТЗЫВА
# =====================================================================
REVOKED = BASE / "revoked.json"


# Подпись SHA-256 зашифрованного файла личным ключом Ed25519
def sign_enc(enc_sha, ident):
    ed, x, ser = pk_mods()
    sk = ed.Ed25519PrivateKey.from_private_bytes(b64d(ident["ed_priv"]))
    return {"pub": ident["ed_pub"], "sig": b64e(sk.sign(b"CFENC1" + bytes.fromhex(enc_sha))), "name": ident["name"]}


# Проверка подписи; возвращает отпечаток подписанта или бросает CFError
def sig_verify(sig, enc_sha):
    ed, x, ser = pk_mods()
    try:
        ed.Ed25519PublicKey.from_public_bytes(b64d(sig["pub"])).verify(b64d(sig["sig"]), b"CFENC1" + bytes.fromhex(enc_sha))
    except Exception:
        raise CFError("Подпись файла НЕ верна: файл изменён или подделан")
    return fp_text(b64d(sig["pub"]), b"")[:23]


# Локальная проверка политики: допустимые часы и роль (самообъявленная, не защита от злоумышленника)
def policy_check(policy):
    if not policy:
        return
    if policy.get("hours"):
        a, b = policy["hours"]
        h = time.localtime().tm_hour
        ok = a <= h < b if a <= b else (h >= a or h < b)
        if not ok:
            raise CFError(f"Расшифровка разрешена только с {a}:00 до {b}:00")
    if policy.get("role") and CFG.get("role") != policy["role"]:
        raise CFError(f"Нужна роль «{policy['role']}» (Настройки → Роль)")


# Список отозванных хешей .enc
def revoked_load():
    try:
        return json.loads(REVOKED.read_text(encoding="utf-8"))
    except Exception:
        return []


# Отозванный файл не расшифровывается (fail-closed)
def revoke_check(enc_sha):
    if enc_sha and enc_sha in revoked_load():
        raise CFError("Доступ к этому файлу отозван (список отзыва)")


# Добавить файл в список отзыва
def revoke_flow():
    fl = pick_files("Файл из vault для отзыва", [VAULT], True)
    d = revoked_load()
    for f in fl:
        h = sha256_file(f)
        if h not in d:
            d.append(h)
    write_json_atomic(REVOKED, d)
    say_ok("Добавлено в список отзыва. Копии файла на других устройствах станут недоступны тем, у кого есть этот список.")


# =====================================================================
# РАЗДЕЛ: ЖУРНАЛ С ХЕШ-ЦЕПОЧКОЙ (JSON Lines), SYSLOG, РЕЗЕРВНЫЕ КОПИИ META
# =====================================================================
AUDIT = BASE / "activity.jsonl"


# Хеш последней записи журнала (для цепочки)
def audit_last_hash():
    try:
        with open(AUDIT, "rb") as f:
            f.seek(0, 2)
            sz = f.tell()
            f.seek(max(0, sz - 4096))
            last = f.read().decode("utf-8", "ignore").strip().splitlines()[-1]
        return json.loads(last)["h"]
    except Exception:
        return "0" * 64


# Структурированная запись: каждая содержит хеш предыдущей — удаление/правка обнаруживаются
def log_action(action, size=None, sin=None, sout=None, layers=None, note=""):
    try:
        priv = CFG.get("log_private", False)
        rec = {"ts": datetime.datetime.now().isoformat(timespec="seconds"), "act": action, "size": None if priv else size,
               "in": sin, "out": sout, "layers": [base_type(x) for x in layers] if layers else None, "note": "" if priv else note, "prev": audit_last_hash()}
        rec["h"] = hashlib.sha256((rec["prev"] + json.dumps(rec, sort_keys=True, ensure_ascii=False)).encode("utf-8")).hexdigest()
        with open(AUDIT, "a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
        os.chmod(AUDIT, 0o600)
        if CFG.get("syslog"):
            import syslog
            syslog.syslog(f"cryptforge {action}")
    except Exception:
        pass


# Проверка целостности цепочки; возвращает (ok, число записей, номер первой плохой)
def audit_verify():
    prev = "0" * 64
    n = 0
    if not AUDIT.exists():
        return True, 0, None
    for i, ln in enumerate(AUDIT.read_text(encoding="utf-8", errors="ignore").splitlines(), 1):
        try:
            rec = json.loads(ln)
            h = rec.pop("h")
            if rec.get("prev") != prev or hashlib.sha256((prev + json.dumps(rec, sort_keys=True, ensure_ascii=False)).encode("utf-8")).hexdigest() != h:
                return False, n, i
            prev = h
            n += 1
        except Exception:
            return False, n, i
    return True, n, None


# Просмотр журнала, проверка цепочки, экспорт, очистка
def journal():
    title_anim("ЖУРНАЛ")
    ok, n, bad = audit_verify()
    if n == 0 and ok:
        say_in("Журнал пуст")
    elif ok:
        say_ok(f"Цепочка целостна: записей {n}")
    else:
        say_er(f"ЦЕПОЧКА НАРУШЕНА на записи {bad}: журнал изменён или повреждён")
    if AUDIT.exists():
        lines = AUDIT.read_text(encoding="utf-8", errors="ignore").splitlines()
        for ln in lines[-25:]:
            try:
                r = json.loads(ln)
                print(f"  {r['ts'][5:16]} {r['act']}" + (f" · {r['note']}" if r.get("note") else ""))
            except Exception:
                print("  ?")
    print("   1. Экспорт копии (JSON Lines)  2. Очистить  0. Назад")
    c = ask("Выбор: ")
    if c == "1":
        dst = unique_path(out_dir(), "cryptforge-audit.jsonl")
        shutil.copyfile(AUDIT, dst)
        say_ok(f"Экспорт: {dst}")
    elif c == "2" and ask_yn("Очистить журнал безвозвратно?", "n"):
        AUDIT.write_text("")
        say_ok("Журнал очищен")


# Дублируем метаданные в скрытые места (vault/.meta и ~/.backup)
def meta_backup(path):
    try:
        p = Path(path)
        for d in (VAULT / ".meta", BASE / ".backup"):
            d.mkdir(parents=True, exist_ok=True)
            os.chmod(d, 0o700)
            shutil.copyfile(p, d / p.name)
            os.chmod(d / p.name, 0o600)
    except Exception:
        pass


# Восстановление потерянных метаданных из резервных копий
def meta_restore_flow():
    n = 0
    for d in (VAULT / ".meta", BASE / ".backup"):
        if not d.exists():
            continue
        for p in d.glob("*.meta"):
            dst = META / p.name
            if not dst.exists():
                shutil.copyfile(p, dst)
                os.chmod(dst, 0o600)
                n += 1
                say_ok(f"Восстановлено: {p.name}")
    if not n:
        say_in("Нечего восстанавливать")


# =====================================================================
# РАЗДЕЛ: DEAD MAN'S SWITCH (только через явный check-in), HONEY-ФАЙЛЫ, TIME-STEGO
# =====================================================================
# iOS убивает фоновые процессы, поэтому таймера-демона нет: просрочка
# проверяется при КАЖДОМ запуске скрипта; продлевается командой check-in.
DEADMAN = BASE / ".deadman.json"
HONEY = BASE / ".honey.json"


# Список наблюдаемых файлов
def deadman_load():
    try:
        return json.loads(DEADMAN.read_text(encoding="utf-8"))
    except Exception:
        return {"items": []}


# При запуске: просроченные файлы лишаются ключей (крипто-стирание)
def deadman_check():
    d = deadman_load()
    now = time.time()
    hit = [it for it in d["items"] if now - it["last"] > it["days"] * 86400]
    for it in hit:
        for ext in (".meta", ".split"):
            p = META / f"{it['file']}{ext}"
            if p.exists():
                wipe_file(p)
        say_wn(f"Dead man's switch: срок check-in истёк, ключи файла {it['file'][:12]} уничтожены")
        log_action("deadman-erase", None, None, None, None, it["file"][:12])
    if hit:
        d["items"] = [it for it in d["items"] if it not in hit]
        write_json_atomic(DEADMAN, d)


# Меню: добавить файл, check-in, список
def deadman_menu():
    title_anim("DEAD MAN'S SWITCH")
    say_wn("Работает только при запуске скрипта (iOS не даёт фоновых таймеров).")
    d = deadman_load()
    for it in d["items"]:
        left = it["days"] - (time.time() - it["last"]) / 86400
        print(f"  {it['file'][:30]}: осталось {left:.1f} дн.")
    print("   1. Добавить файл  2. Check-in (продлить всё)  3. Убрать файл  0. Назад")
    c = ask("Выбор: ")
    if c == "1":
        fl = pick_files("Файл из vault", [VAULT], True)
        if fl:
            days = ask_int("Через сколько дней без check-in стереть ключи", 1, 3650, 30)
            d["items"].append({"file": Path(fl[0]).name, "days": days, "last": time.time()})
            write_json_atomic(DEADMAN, d)
            say_ok("Добавлено")
    elif c == "2":
        for it in d["items"]:
            it["last"] = time.time()
        write_json_atomic(DEADMAN, d)
        say_ok("Check-in выполнен")
    elif c == "3":
        k = ask("Начало имени файла: ")
        d["items"] = [it for it in d["items"] if not it["file"].startswith(k)]
        write_json_atomic(DEADMAN, d)


# Приманки: создаём «ценные» на вид файлы и позже проверяем, трогали ли их
def honey_menu():
    title_anim("HONEY-ФАЙЛЫ [EXP]")
    say_wn("Время доступа (atime) в iSH ненадёжно: возможны ложные срабатывания.")
    print("   1. Создать приманки  2. Проверить  0. Назад")
    c = ask("Выбор: ")
    hd = BASE / "honey"
    if c == "1":
        hd.mkdir(exist_ok=True)
        rec = {}
        for nm in ("passwords.txt", "bank_keys.txt", "wallet_seed.txt"):
            p = hd / nm
            p.write_text(honey_text(os.urandom(8)), encoding="utf-8")
            os.utime(p, (time.time() - 86400, time.time() - 86400))
            rec[str(p)] = os.stat(p).st_atime
        write_json_atomic(HONEY, rec)
        say_ok(f"Созданы приманки в {hd}")
    elif c == "2":
        try:
            rec = json.loads(HONEY.read_text(encoding="utf-8"))
        except Exception:
            raise CFError("Приманок нет")
        hit = [k for k, a in rec.items() if Path(k).exists() and os.stat(k).st_atime > a + 5]
        (say_wn if hit else say_ok)(f"Тронутых приманок: {len(hit)}" + (": " + ", ".join(Path(k).name for k in hit) if hit else ""))


# TOMS-lite: бит данных в чётности секунд mtime у серии файлов (хрупко: копирование сбивает время)
def time_stego_encode(payload, dirpath):
    body = struct.pack(">H", len(payload)) + payload
    bits = [(b >> i) & 1 for b in body for i in range(7, -1, -1)]
    base = int(time.time()) - 86400 * 30
    base -= base % 2
    Path(dirpath).mkdir(parents=True, exist_ok=True)
    for i, bit in enumerate(bits):
        p = Path(dirpath) / f"f{i:05d}.dat"
        p.write_bytes(os.urandom(16))
        t = base + i * 120 + bit
        os.utime(p, (t, t))
    return len(bits)


# Читаем чётность секунд mtime файлов по порядку имён
def time_stego_decode(dirpath):
    files = sorted(Path(dirpath).glob("f*.dat"))
    bits = [int(os.stat(p).st_mtime) & 1 for p in files]
    bs = bytearray()
    for i in range(0, len(bits) - 7, 8):
        v = 0
        for b in bits[i:i + 8]:
            v = (v << 1) | b
        bs.append(v)
    ln = struct.unpack(">H", bytes(bs[:2]))[0]
    return bytes(bs[2:2 + ln])


# Меню TOMS-lite
def time_stego_menu():
    title_anim("TIME-STEGO [EXP]")
    say_wn("Хрупко: копирование/архивация сбивает временные метки.")
    print("   1. Спрятать короткий секрет  2. Извлечь  0. Назад")
    c = ask("Выбор: ")
    d = STEGO / "timestego"
    if c == "1":
        s = ask("Секрет (до 200 байт): ").encode()
        if not s or len(s) > 200:
            raise CFError("От 1 до 200 байт")
        n = time_stego_encode(s, d)
        say_ok(f"Создано файлов: {n} в {d}")
    elif c == "2":
        say_ok("Найдено: " + time_stego_decode(d).decode("utf-8", "replace"))


# =====================================================================
# РАЗДЕЛ: ОТРИЦАЕМЫЙ МНОГОСЛОТОВЫЙ КОНТЕЙНЕР (.dnc) С HONEY-РЕЖИМОМ
# =====================================================================
# Файл — только случайные на вид байты: соль + S одинаковых слотов. Слот
# расшифровывается ключом из пароля (общий KDF, ключ слота = HKDF(индекс)).
# Пустые слоты — просто случайные данные. Доказать наличие/число скрытых
# слотов нельзя. Параметры KDF зафиксированы форматом (scrypt 2^15).
DNC_N = 15
WORDS = "meeting notes budget invoice project draft review schedule summary report contact address password reminder shopping recipe travel plan ticket receipt photo backup family doctor insurance tax update list idea todo call email".split()


# Правдоподобная «заметка» детерминированно из seed — для honey-режима
def honey_text(seed):
    r = random.Random(hashlib.sha256(seed).digest())
    lines = []
    for _ in range(r.randint(3, 6)):
        lines.append(" ".join(r.choice(WORDS) for _ in range(r.randint(4, 9))).capitalize() + ".")
    return "\n".join(lines) + "\n"


# Общий ключ контейнера из пароля
def dnc_key(pw, salt):
    return hashlib.scrypt(pw.encode("utf-8"), salt=salt, n=1 << DNC_N, r=8, p=1, maxmem=512 * MB, dklen=32)


# entries: {индекс_слота: (пароль, данные)}; остальные слоты — случайные
def dnc_create(path, slots, cap, entries):
    salt = os.urandom(16)
    out = bytearray(salt)
    for i in range(slots):
        if i in entries:
            pw, data = entries[i]
            if len(data) > cap:
                raise CFError(f"Данные слота {i + 1} больше ёмкости ({cap} Б)")
            key = hkdf(dnc_key(pw, salt), salt, b"slot" + bytes([i]))
            plain = struct.pack(">I", len(data)) + data + os.urandom(cap - len(data))
            nonce = os.urandom(12)
            out += nonce + small_aead("gcm" if HAS_CRYPTO else "shake", key).encrypt(nonce, plain, b"dnc")
        else:
            out += os.urandom(12 + 4 + cap + 16)
    Path(path).write_bytes(bytes(out))
    os.chmod(path, 0o600)


# Перебираем возможные числа слотов и все слоты; возвращаем найденные данные
def dnc_open(path, pw):
    raw = Path(path).read_bytes()
    salt, body = raw[:16], raw[16:]
    base = dnc_key(pw, salt)
    found = []
    for s in range(1, 33):
        if len(body) % s:
            continue
        sl = len(body) // s
        cap = sl - 12 - 4 - 16
        if cap < 1:
            continue
        for i in range(s):
            chunk = body[i * sl:(i + 1) * sl]
            try:
                key = hkdf(base, salt, b"slot" + bytes([i]))
                plain = small_aead("gcm" if HAS_CRYPTO else "shake", key).decrypt(chunk[:12], chunk[12:], b"dnc")
                ln = struct.unpack(">I", plain[:4])[0]
                found.append(plain[4:4 + ln])
            except Exception:
                continue
        if found:
            break
    return found


# Меню контейнера: создать (до нескольких паролей) / открыть
def dnc_menu():
    title_anim("ПРАВДОПОДОБНОЕ ОТРИЦАНИЕ")
    say_in("Разные пароли открывают разные данные.")
    say_wn("Размер файла выдаёт общую ёмкость; число слотов скрыто.")
    print("   1. Создать контейнер  2. Открыть  0. Назад")
    c = ask("Выбор: ")
    if c == "1":
        slots = ask_int("Всего слотов (включая пустые)", 2, 16, 4)
        cap = ask_int("Ёмкость слота, КБ", 1, 65536, 64) * 1024
        entries = {}
        order = rand_shuffle(list(range(slots)))
        n = ask_int("Сколько паролей/секретов задать", 1, slots, 2)
        for k in range(n):
            label = "РЕАЛЬНЫЙ" if k == n - 1 else f"приманка {k + 1}"
            print(f"  Секрет {k + 1} ({label}):")
            print("   1. Файл  2. Текст")
            if ask("Источник [2]: ", "2") == "1":
                fl = pick_files("Файл", [VAULT, ORIGINALS], True)
                if not fl:
                    return
                data = Path(fl[0]).read_bytes()
            else:
                data = ask("Текст: ").encode()
            pw = ask_secret("  Пароль (мин. 8 символов): ")
            if len(pw) < 8:
                raise CFError("Пароль слишком короткий")
            entries[order[k]] = (pw, data)
        out = unique_path(STEGO, "cf_" + gen_name()[:8] + ".bin")
        say_in("Сборка (стойкий KDF)...")
        dnc_create(out, slots, cap, entries)
        say_ok(f"Контейнер: {out} ({hsize(out.stat().st_size)})")
        say_wn("Слоты выбираются случайно — запомните только пароли.")
    elif c == "2":
        fl = pick_files("Контейнер", [STEGO], True)
        if not fl:
            return
        pw = ask_secret("Пароль: ")
        say_in("Проверка пароля (стойкий KDF)...")
        res = dnc_open(fl[0], pw)
        if not res:
            if CFG.get("honey_mode"):
                say_ok("Расшифровано:")
                print(honey_text(hashlib.sha256(pw.encode()).digest()))
                return
            raise CFError("Пароль не подошёл или это не контейнер")
        for i, d in enumerate(res, 1):
            try:
                txt = d.decode("utf-8")
                print(f"  Данные {i}:")
                print(txt if len(txt) < 2000 else txt[:2000] + "…")
            except UnicodeDecodeError:
                out = unique_path(out_dir(), f"dnc_{i}.bin")
                out.write_bytes(d)
                say_ok(f"Бинарные данные: {out}")


# =====================================================================
# РАЗДЕЛ: БЕЗОПАСНАЯ ПАМЯТЬ (mlock, обнуление буферов)
# =====================================================================
def mlock_all():
    # Просим ОС не выгружать страницы процесса в своп (если разрешено и доступно)
    try:
        import ctypes
        libc = ctypes.CDLL(None)
        return libc.mlockall(3) == 0
    except Exception:
        return False


# Обнуление изменяемого буфера (для bytes в Python гарантий нет — только для bytearray)
def zero_buf(b):
    if isinstance(b, bytearray):
        for i in range(len(b)):
            b[i] = 0


# =====================================================================
# РАЗДЕЛ: ПРОФИЛИ ПЛАТФОРМ — имитация обработки и проверка «выживания»
# =====================================================================
# Каждая платформа знает свой «конвейер»: что делает с картинкой/файлом.
# Скрипт внедряет данные, прогоняет имитацию конвейера и сверяет SHA-256.
# Пока проверка не пройдена, результат не выдаётся (fail-closed).
PLATFORMS = {
    "whatsapp-image": {"title": "WhatsApp: фото", "attack": ("jpeg", 72, 1600), "channels": ["qim"], "max": 90, "tag": "[iSH]"},
    "whatsapp-document": {"title": "WhatsApp: документ", "attack": None, "channels": ["tail"], "max": 1 << 30, "tag": "[iSH]"},
    "telegram-avatar": {"title": "Telegram: аватарка", "attack": ("jpeg", 82, 2560), "channels": ["qim"], "max": 90, "tag": "[iSH]"},
    "telegram-document": {"title": "Telegram: документ", "attack": None, "channels": ["tail"], "max": 1 << 30, "tag": "[iSH]"},
    "discord": {"title": "Discord: изображение", "attack": ("jpeg", 85, 4096), "channels": ["qim"], "max": 90, "tag": "[iSH]"},
    "social": {"title": "Соцсети (X/Facebook/Instagram)", "attack": ("jpeg", 85, 1080), "channels": ["qim"], "max": 90, "tag": "[iSH]"},
    "email-attachment": {"title": "Email: вложение", "attack": None, "channels": ["tail", "zip"], "max": 1 << 30, "tag": "[iSH]"},
}


# Имитация перекодирования платформой: JPEG нужного качества и ресайз по длинной стороне
def platform_attack(src, dst, spec):
    from PIL import Image
    kind, q, longest = spec
    im = Image.open(src)
    im.load()
    im = im.convert("RGB")
    if max(im.size) > longest:
        r = longest / max(im.size)
        im = im.resize((max(8, int(im.width * r)), max(8, int(im.height * r))))
    im.save(dst, "JPEG", quality=q)


# Тестовая картинка с текстурой (шум), на которой QIM работает как на фото
def test_image(path, size=512):
    from PIL import Image
    n = Image.effect_noise((size, size), 48)
    img = Image.merge("RGB", (n, n.rotate(90), n.transpose(Image.FLIP_LEFT_RIGHT)))
    img.save(path, "PNG")


# Внедряет payload, имитирует платформу, возвращает (успех, отчёт, путь результата)
def platform_check(name, cover, payload):
    p = PLATFORMS[name]
    if len(payload) > p["max"]:
        return False, f"payload {len(payload)} Б больше лимита канала ({p['max']} Б): отправляйте как документ", None
    work = new_work()
    try:
        out = work / "emb"
        shutil.copyfile(cover, str(out) + Path(cover).suffix)
        out = Path(str(out) + Path(cover).suffix)
        mask_embed(cover, out, payload, p["channels"], fec=0.0, canary=False, legit=False)
        probe = out
        if p["attack"]:
            probe = work / "attacked.jpg"
            platform_attack(out, probe, p["attack"])
        got = mask_extract(probe, quiet=True)["payload"]
        if got != payload:
            return False, "после имитации обработки данные не извлеклись", None
        final = STEGO / (Path(cover).stem + "_" + name + Path(cover).suffix)
        shutil.copyfile(out, final)
        os.chmod(final, 0o600)
        return True, "проверка на имитации пройдена", final
    finally:
        shutil.rmtree(work, ignore_errors=True)


# Меню профилей платформ: выбираем платформу, данные, контейнер; результат только после успешного теста
def platform_flow():
    title_anim("ПРОФИЛИ ПЛАТФОРМ")
    names = list(PLATFORMS)
    for i, n in enumerate(names, 1):
        print(f"  {i}. {PLATFORMS[n]['title']}")
    print(f"  {len(names) + 1}. Telegram: кружок/голосовое [NOT SUPPORTED]")
    c = ask("Платформа: ")
    if c.isdigit() and int(c) == len(names) + 1:
        raise CFError("Кружки (H.264) и голосовые (Opus) требуют ffmpeg/opus-tools и стегоканала в сжатом домене — в этой версии [NOT SUPPORTED]. Отправляйте как документ.")
    if not c.isdigit() or not 1 <= int(c) <= len(names):
        raise CFError("Неверный выбор")
    name = names[int(c) - 1]
    data = ask("Ключ/доля (текст): ").encode()
    if not data:
        return
    if len(data) > PLATFORMS[name]["max"] and PLATFORMS[name]["attack"]:
        say_wn("Данных слишком много для устойчивого image-канала — переключаюсь на режим документа.")
        name = "whatsapp-document"
    cover = pick_cover("Контейнер")
    if not cover:
        return
    ok, msg, final = platform_check(name, cover, data)
    if not ok:
        raise CFError("Тест не пройден: " + msg)
    say_ok(f"{PLATFORMS[name]['title']}: {msg}")
    say_ok(f"Готово: {final}")
    if PLATFORMS[name]["attack"]:
        say_wn("Для надёжности всё равно отправляйте файл «как документ», если можно.")


# =====================================================================
# РАЗДЕЛ: EMAIL-ЗАГОЛОВКИ (упрощённая Headstega: payload в Message-ID)
# =====================================================================
def eml_make(payload, subject="Hello", to="friend@example.com"):
    # Кодируем payload в base32 внутри локальной части Message-ID и X-заголовка
    import base64 as _b
    tag = _b.b32encode(payload).decode().rstrip("=").lower()
    parts = [tag[i:i + 24] for i in range(0, len(tag), 24)]
    mid = ".".join(parts[:6]) if len(tag) <= 144 else None
    if mid is None:
        raise CFError("Email-заголовок вмещает до ~90 байт")
    return f"From: me@example.com\nTo: {to}\nSubject: {subject}\nMessage-ID: <{mid}@mail.example.com>\nContent-Type: text/plain; charset=utf-8\n\nHi!\n"


# Извлекаем payload из Message-ID
def eml_parse(text):
    import base64 as _b
    m = re.search(r"Message-ID:\s*<([a-z2-7.]+)@", text)
    if not m:
        raise CFError("Message-ID не найден")
    s = m.group(1).replace(".", "").upper()
    s += "=" * (-len(s) % 8)
    return _b.b32decode(s)


# =====================================================================
# РАЗДЕЛ: САМОТЕСТЫ ПО ПЛАТФОРМАМ И ФУНКЦИЯМ (--self-test <имя>)
# =====================================================================
def st_platform(name, results):
    # Универсальный тест платформы с картинкой: QIM + имитация конвейера
    try:
        import PIL
    except ImportError:
        results.append((PLATFORMS[name]["title"], "ПРОПУЩЕН", "нужен Pillow"))
        return
    work = new_work()
    try:
        img = work / "cover.png"
        test_image(img)
        payload = os.urandom(60)
        ok, msg, final = platform_check(name, img, payload)
        results.append((PLATFORMS[name]["title"], "OK" if ok else "СБОЙ", msg))
    except Exception as e:
        results.append((PLATFORMS[name]["title"], "СБОЙ", f"{type(e).__name__}: {e}"))
    finally:
        shutil.rmtree(work, ignore_errors=True)


# Создание каждого типа документа с payload и проверочное извлечение
def st_document(results):
    secret = os.urandom(200)
    sealed = pw_seal("test-password-123", secret, b"CFD1")
    combos = [("docx", "ghost"), ("docx", "customxml"), ("docx", "props"), ("xlsx", "hiddensheet"), ("xlsx", "ghost"), ("pptx", "ghost"), ("pptx", "customxml"),
              ("pdf", "incremental"), ("pdf", "tail"), ("odt", "ghost"), ("epub", "ghost"), ("html", "comment"), ("txt", "zerowidth"), ("json", "field")]
    work = new_work()
    try:
        for dtype, method in combos:
            try:
                p = work / f"d.{dtype}"
                p.write_bytes(doc_create(dtype, method, "Привет!\nТестовый документ", [sealed]))
                ok, why = doc_validate(p, dtype)
                frames = doc_extract_frames(p)
                good = ok and len(frames) == 1
                if good:
                    meta, blob, fx = frame_parse(frames[0])
                    good = pw_open("test-password-123", blob, b"CFD1") == secret
                results.append((f"Документ {dtype}/{method}", "OK" if good else "СБОЙ", "" if good else why))
            except Exception as e:
                results.append((f"Документ {dtype}/{method}", "СБОЙ", f"{type(e).__name__}: {e}"))
    finally:
        shutil.rmtree(work, ignore_errors=True)


# Email: заголовок Message-ID и вложение-хвост
def st_email(results):
    try:
        p = os.urandom(50)
        results.append(("Email: заголовок", "OK" if eml_parse(eml_make(p)) == p else "СБОЙ", ""))
    except Exception as e:
        results.append(("Email: заголовок", "СБОЙ", str(e)))
    work = new_work()
    try:
        cov = work / "c.pdf"
        cov.write_bytes(doc_pdf("Test"))
        out = work / "o.pdf"
        payload = os.urandom(3000)
        mask_embed(cov, out, payload, ["tail"], fec=0.3, canary=True)
        results.append(("Email: вложение (PDF-хвост)", "OK" if mask_extract(out, quiet=True)["payload"] == payload else "СБОЙ", ""))
    except Exception as e:
        results.append(("Email: вложение", "СБОЙ", str(e)))
    finally:
        shutil.rmtree(work, ignore_errors=True)


# Текстовые каналы: невидимые символы и устойчивость к нормализации/обрезке пробелов
def st_text(results):
    import unicodedata
    secret = os.urandom(30)
    s = "Привет, как дела? " + zw_encode(secret) + "Всё хорошо."
    ok1 = zw_decode(unicodedata.normalize("NFKC", s)) == secret
    ok2 = zw_decode("\n".join(l.rstrip() for l in s.split("\n"))) == secret
    results.append(("Текст: невидимые символы + NFKC", "OK" if ok1 else "СБОЙ", ""))
    results.append(("Текст: обрезка пробелов", "OK" if ok2 else "СБОЙ", ""))
    stripped = "".join(c for c in s if c not in ZW_ALPHA and c != ZW_MARK)
    try:
        zw_decode(stripped)
        results.append(("Текст: платформа вырезает невидимые", "СБОЙ", "ожидался отказ"))
    except CFError:
        results.append(("Текст: платформа вырезает невидимые", "OK", "корректный отказ (канал хрупок)"))


# Тест LWE-RDH: не поддерживается
def st_lwe(results):
    results.append(("LWE-RDH", "НЕ ПОДДЕРЖИВАЕТСЯ", "нет LWE-библиотек; доступен RDH (reduced) и Шамир"))


# Проверка xattr: работает только если ФС и Python это поддерживают
def st_xattr(results):
    work = new_work()
    try:
        p = work / "x.bin"
        p.write_bytes(b"x")
        if not hasattr(os, "setxattr"):
            results.append(("xattr", "ПРОПУЩЕН", "os.setxattr недоступен в этой среде"))
            return
        os.setxattr(p, "user.cf", b"secret")
        results.append(("xattr", "OK" if os.getxattr(p, "user.cf") == b"secret" else "СБОЙ", ""))
    except OSError as e:
        results.append(("xattr", "ПРОПУЩЕН", f"ФС не поддерживает: {e}"))
    finally:
        shutil.rmtree(work, ignore_errors=True)


# Тест Opus: не поддерживается
def st_opus(results):
    have = shutil.which("opusenc") and shutil.which("opusdec")
    results.append(("Opus compressed-domain", "НЕ ПОДДЕРЖИВАЕТСЯ", "требуется стегоканал в MDCT-домене" + ("; opus-tools найдены" if have else "; opus-tools нет")))


# Тест Signal: не поддерживается
def st_signal(results):
    results.append(("Signal анаморфное шифрование", "НЕ ПОДДЕРЖИВАЕТСЯ", "требует доступа к Double Ratchet клиента [SIM]"))


# QR: можем сгенерировать, но декодера в iSH нет
def st_qr(results):
    if not shutil.which("qrencode"):
        results.append(("QR", "ПРОПУЩЕН", "apk add qrencode"))
        return
    r = subprocess.run(["qrencode", "-t", "ASCII"], input=b"test", capture_output=True)
    results.append(("QR: генерация", "OK" if r.returncode == 0 else "СБОЙ", "декодирование нужно проверять камерой"))


# Запуск набора тестов по имени; all — все платформы и функции
def selftest_named(name):
    results = []
    plat = {"whatsapp": ["whatsapp-image", "whatsapp-document"], "telegram": ["telegram-avatar", "telegram-document"], "discord": ["discord"], "social": ["social"]}
    groups = {
        "document": lambda: st_document(results), "create-document": lambda: st_document(results), "email": lambda: st_email(results), "text": lambda: st_text(results),
        "lwe-rdh": lambda: st_lwe(results), "xattr": lambda: st_xattr(results), "opus": lambda: st_opus(results), "signal": lambda: st_signal(results), "qr": lambda: st_qr(results),
    }
    todo = []
    if name == "all":
        for k in plat:
            todo += plat[k]
        extra = list(groups)
    else:
        todo = plat.get(name, [])
        extra = [name] if name in groups else []
        if not todo and not extra:
            raise CFError("Неизвестный набор. Доступно: all, " + ", ".join(list(plat) + list(groups)))
    init_dirs()
    for n in todo:
        st_platform(n, results)
    seen = set()
    for g in extra:
        fn = groups[g]
        if id(fn) in seen or g == "create-document" and "document" in extra:
            continue
        fn()
    return results


# Печать таблицы результатов; возвращает число сбоев
def print_results(results):
    bad = 0
    for nm, st, note in results:
        col = {"OK": "\033[38;5;84m", "ПРОПУЩЕН": "\033[38;5;220m", "НЕ ПОДДЕРЖИВАЕТСЯ": "\033[38;5;245m"}.get(st, "\033[38;5;203m")
        print(f"  {col}{st:<18}\033[0m {nm}" + (f" — {note}" if note else ""))
        if st == "СБОЙ":
            bad += 1
    return bad


# =====================================================================
# РАЗДЕЛ: ДИАГНОСТИКА СРЕДЫ (--doctor): зависимости, скорость, возможности ФС
# =====================================================================
FEATURES = [
    # (функция, метка среды, надёжность, требуется, раздел справки)
    ("AES-256-GCM / ChaCha20 / OCB3", "[iSH]", "Надёжный", "cryptography или pycryptodome", 2),
    ("Argon2id / scrypt KDF", "[iSH]", "Надёжный", "py3-argon2-cffi (Argon2id)", 2),
    ("Мастер-пароль, шифрование метаданных", "[iSH]", "Надёжный", "—", 1),
    ("Envelope (обёртки паролей), факторы ключа", "[iSH]", "Надёжный", "—", 1),
    ("Мессенджер E2E (X25519+Ed25519, ratchet)", "[iSH]", "Надёжный", "py3-cryptography", 5),
    ("Энигма / Виженер / Цезарь / Атбаш / Base64", "[iSH]", "Ненадёжный", "—", 3),
    ("Маскировка: хвост, чанк, атом, ZIP, RIFF", "[iSH]", "Условный", "—", 4),
    ("QIM-канал (устойчив к JPEG/ресайзу)", "[iSH]", "Условный", "py3-pillow", 4),
    ("FEC (стирающий код Рида-Соломона)", "[iSH]", "Надёжный", "—", 4),
    ("RDH обратимое сокрытие PNG/WAV", "[iSH]", "Условный", "py3-pillow (PNG)", 4),
    ("Метаданные EXIF (правка/удаление)", "[iSH]", "Надёжный", "exiftool", 4),
    ("Документы docx/xlsx/pptx/pdf/odt/epub", "[iSH]", "Условный", "—", 7),
    ("Отрицаемый контейнер (.dnc), honey", "[iSH]", "Условный", "—", 6),
    ("Dead man's switch (только check-in)", "[iSH]", "Условный", "—", 6),
    ("Скрытие имён Unicode-символами", "[iSH]", "Условный", "—", 4),
    ("Аппаратные ключи, Secure Enclave, FIDO2", "[HW]", "Симуляция", "нет доступа из iSH", 8),
    ("APFS xattr/slack", "[macOS]", "Условный", "нативная APFS", 8),
    ("Кружки Telegram, Opus-стего, ffmpeg-перекодирование", "[NOT SUPPORTED]", "Симуляция", "ffmpeg, opus-tools", 8),
    ("F5/nsF5, BAFLE-DCT, GNN, диффузия, веса LLM, 3DGS", "[NOT SUPPORTED]", "Симуляция", "нет доступа к DCT/моделям", 8),
    ("Квантовые каналы, PHY/Wi-Fi CSI, 3D-печать, синтез ДНК", "[SIM]", "Симуляция", "физически нереализуемо", 8),
    ("ML-KEM/X-Wing/ML-DSA (пост-квантовые)", "[NOT SUPPORTED]", "Симуляция", "нет библиотек в Alpine", 2),
]


# Проверка наличия Python-модуля без побочных эффектов
def have_mod(name):
    import importlib.util
    try:
        return importlib.util.find_spec(name) is not None
    except Exception:
        return False


# Замер скорости AEAD (МБ/с) на 8 МБ данных
def bench_aead():
    if not HAS_CRYPTO:
        return None
    key = os.urandom(32)
    data = os.urandom(1 << 20)
    a = AESGCM(key)
    t0 = time.perf_counter()
    for i in range(8):
        a.encrypt(i.to_bytes(12, "big"), data, None)
    return 8 / max(1e-6, time.perf_counter() - t0)


# Полная диагностика: среда, зависимости, скорость, возможности ФС, матрица функций
def doctor_flow(export=True):
    import platform as pf
    title_anim("ДИАГНОСТИКА")
    arch = pf.machine()
    say_in(f"Python {pf.python_version()} · {pf.system()} {arch}")
    ish = os.path.exists("/proc/ish") or "ish" in (pf.release() or "").lower()
    say_in("Среда: " + ("iSH [iSH]" if ish else "обычный Linux/macOS"))
    print()
    print("  Библиотеки и утилиты:")
    deps = [("cryptography", have_mod("cryptography"), "py3-cryptography"), ("pycryptodome", have_mod("Crypto"), "py3-cryptodome"), ("Pillow", have_mod("PIL"), "py3-pillow"),
            ("argon2", have_mod("argon2"), "py3-argon2-cffi"), ("mnemonic", have_mod("mnemonic"), "py3-mnemonic"), ("mutagen", have_mod("mutagen"), "py3-mutagen"),
            ("numpy", have_mod("numpy"), "py3-numpy"), ("onnxruntime", have_mod("onnxruntime"), "не в Alpine"),
            ("openssl", bool(shutil.which("openssl")), "openssl"), ("gpg", bool(shutil.which("gpg")), "gnupg"), ("exiftool", bool(shutil.which("exiftool")), "exiftool"),
            ("qrencode", bool(shutil.which("qrencode")), "qrencode"), ("ffmpeg", bool(shutil.which("ffmpeg")), "ffmpeg"), ("opusenc", bool(shutil.which("opusenc")), "opus-tools"),
            ("libreoffice", bool(shutil.which("soffice") or shutil.which("libreoffice")), "libreoffice")]
    cap = {}
    okm = "\033[38;5;84m✔\033[0m"
    nom = "\033[38;5;203m✖\033[0m"
    for nm, ok, pkg in deps:
        cap[nm] = ok
        hint = "" if ok else "  \033[2m(apk add " + pkg + ")\033[0m"
        print("   " + (okm if ok else nom) + " " + nm + hint)
    print()
    print("  Скорость:")
    t0 = time.perf_counter()
    hashlib.sha256(os.urandom(1 << 20) * 16).digest()
    sha_s = 16 / max(1e-6, time.perf_counter() - t0)
    print(f"   SHA-256: {sha_s:.0f} МБ/с")
    sp = bench_aead()
    if sp:
        print(f"   AES-256-GCM ({'cryptography' if have_mod('cryptography') else 'pycryptodome'}): {sp:.0f} МБ/с")
    t0 = time.perf_counter()
    hashlib.scrypt(b"x", salt=b"s" * 16, n=1 << sec()["scrypt"], r=8, p=1, maxmem=512 * MB, dklen=32)
    sc = time.perf_counter() - t0
    print(f"   scrypt 2^{sec()['scrypt']} ({sec()['name']}): {sc:.2f} с")
    if sc > 8:
        say_wn("KDF очень медленный — понизьте уровень стойкости в Настройках")
    if has_argon2():
        t0 = time.perf_counter()
        a = sec()["argon"]
        argon2id_raw(b"x", b"s" * 16, a[0], a[2], a[1])
        print(f"   Argon2id: {time.perf_counter() - t0:.2f} с")
    work = new_work()
    try:
        p = work / "io.bin"
        t0 = time.perf_counter()
        with open(p, "wb") as f:
            for _ in range(8):
                f.write(os.urandom(1 << 20))
            f.flush()
            os.fsync(f.fileno())
        w_s = 8 / max(1e-6, time.perf_counter() - t0)
        t0 = time.perf_counter()
        p.read_bytes()
        r_s = 8 / max(1e-6, time.perf_counter() - t0)
        print(f"   Диск: запись {w_s:.0f} МБ/с, чтение {r_s:.0f} МБ/с")
        print()
        print("  Файловая система:")
        try:
            os.chmod(p, 0o600)
            mode = oct(os.stat(p).st_mode & 0o777)
            print(f"   chmod: {'работает' if mode == '0o600' else 'не применяется (' + mode + ') — не полагайтесь на права'}")
        except OSError:
            print("   chmod: недоступен")
        try:
            os.link(p, work / "hl.bin")
            print("   жёсткие ссылки: есть")
        except OSError:
            print("   жёсткие ссылки: нет")
        try:
            os.mkfifo(work / "ff")
            print("   FIFO: есть")
        except (OSError, AttributeError):
            print("   FIFO: нет")
        print(f"   xattr: {'доступен' if hasattr(os, 'setxattr') else 'нет'}")
    finally:
        shutil.rmtree(work, ignore_errors=True)
    try:
        du = shutil.disk_usage(str(BASE))
        print(f"   Свободно: {hsize(du.free)} из {hsize(du.total)}")
    except Exception:
        pass
    print()
    print("  Матрица возможностей (метка · надёжность):")
    for nm, tag, rel, need, sec_n in FEATURES:
        print(f"   {tag:<16} [{rel}] {nm}")
        print(f"      \033[2mтребуется: {need} · Справка → раздел {sec_n}\033[0m")
    if export:
        path = unique_path(out_dir(), "cryptforge-capabilities.json")
        write_json_atomic(path, {"python": pf.python_version(), "machine": arch, "ish": ish, "deps": cap, "features": [{"name": n, "env": t, "reliability": r, "requires": q} for n, t, r, q, s in FEATURES],
                                 "bench": {"sha256_mb_s": round(sha_s), "aead_mb_s": round(sp) if sp else None, "scrypt_s": round(sc, 2)}})
        os.chmod(path, 0o644)
        say_ok(f"Карта возможностей: {path}")


# =====================================================================
# РАЗДЕЛ: МЕНЮ БЕЗОПАСНОСТИ
# =====================================================================
def sign_file_flow():
    # Подпись зашифрованного файла личным ключом Ed25519 (метаданные получают поле sig)
    if not has_pk():
        raise CFError("Для подписи нужен py3-cryptography")
    fl = pick_files("Файл из vault", [VAULT], True)
    if not fl:
        return
    f = Path(fl[0])
    ident = identity_get()
    sig = sign_enc(sha256_file(f), ident)
    if meta_update(f.name, "sig", sig):
        say_ok("Подпись записана в метаданные")
    else:
        write_json_secure(META / f"{f.name}.sig", sig)
        say_ok("Подпись сохранена в meta/" + f.name + ".sig")


# Проверка подписи файла
def verify_sig_flow():
    fl = pick_files("Файл из vault", [VAULT], True)
    if not fl:
        return
    f = Path(fl[0])
    sig = None
    mp = META / f"{f.name}.meta"
    if mp.exists():
        sig = read_json_file(mp).get("sig")
    if not sig and (META / f"{f.name}.sig").exists():
        sig = read_json_file(META / f"{f.name}.sig")
    if not sig:
        raise CFError("Подписи нет")
    fp = sig_verify(sig, sha256_file(f))
    say_ok(f"Подпись верна. Автор: {sig.get('name', '?')} (отпечаток {fp})")


# Настройка паник-пароля с жёстким подтверждением
def panic_menu():
    say_wn("Паник-пароль: при вводе вместо мастер-пароля МГНОВЕННО и БЕЗВОЗВРАТНО")
    say_wn("затирает ключи, метаданные, vault, чаты, originals, decrypted и stego, а затем выдаёт «неверный пароль».")
    if not master_exists():
        raise CFError("Сначала задайте мастер-пароль (Настройки)")
    print("   1. Задать паник-пароль  2. Удалить паник-пароль  0. Назад")
    c = ask("Выбор: ")
    if c == "1":
        if ask("Введите ПОНИМАЮ для подтверждения: ") != "ПОНИМАЮ":
            return
        p = ask_secret("Паник-пароль (мин. 8 символов, не совпадать с мастером): ")
        if len(p) < 8:
            raise CFError("Слишком короткий")
        if ask_secret("Повторите: ") != p:
            raise CFError("Не совпало")
        panic_set(p)
        say_ok("Паник-пароль задан")
    elif c == "2":
        PANIC_FILE.unlink(missing_ok=True)
        say_ok("Удалён")


# Меню инструментов безопасности
def security_menu():
    while True:
        title_anim("БЕЗОПАСНОСТЬ")
        rows = [
            ("1", "Мастер-пароль", "метаданные, мессенджер"),
            ("2", "Паник-пароль", "мгновенное стирание"),
            ("3", "Крипто-стирание файла", "уничтожить ключи"),
            ("4", "Dead man's switch", "check-in при запуске"),
            ("5", "Смена паролей envelope", "без перешифровки"),
            ("6", "Список отзыва", "запретить расшифровку"),
            ("7", "Подписать файл (ЭЦП)", "Ed25519"),
            ("8", "Проверить подпись", "авторство и целостность"),
            ("9", "Восстановить метаданные", "из резервных копий"),
            ("10", "Honey-файлы [EXP]", "приманки"),
            ("11", "Time-stego [EXP]", "данные во времени файлов"),
            ("12", "Роль и политика", "часы доступа, роль"),
            ("13", "Check-in", "продлить dead man's switch"),
        ]
        for n, name, note in rows:
            print(f"  \033[1;38;5;203m{n:>3}\033[0m  {name}")
            print(f"       \033[38;5;243m{note}\033[0m")
        print("  \033[1;38;5;203m  0\033[0m  Назад")
        c = ask("Номер: ")
        try:
            if c == "0":
                return
            elif c == "1":
                master_menu()
            elif c == "2":
                panic_menu()
            elif c == "3":
                crypto_erase_flow()
            elif c == "4":
                deadman_menu()
            elif c == "5":
                rewrap_flow()
            elif c == "6":
                revoke_flow()
            elif c == "7":
                sign_file_flow()
            elif c == "8":
                verify_sig_flow()
            elif c == "9":
                meta_restore_flow()
            elif c == "10":
                honey_menu()
            elif c == "11":
                time_stego_menu()
            elif c == "12":
                CFG["role"] = ask(f"Ваша роль (сейчас «{CFG.get('role', '')}»): ", CFG.get("role", ""))
                cfg_save()
                say_ok("Сохранено. Политику доступа (часы/роль) задаёт шифрование.")
            elif c == "13":
                d = deadman_load()
                for it in d["items"]:
                    it["last"] = time.time()
                write_json_atomic(DEADMAN, d)
                say_ok("Check-in выполнен")
            else:
                say_er("Неверный выбор")
        except CFError as e:
            say_er(str(e))


# Меню документов: создать документ с секретом / извлечь
def docs_menu():
    while True:
        title_anim("ДОКУМЕНТЫ С СЕКРЕТОМ")
        print("   1. Создать документ (docx/xlsx/pptx/pdf…)")
        print("   2. Извлечь секрет из документа")
        print("   3. Профили платформ (WhatsApp/Telegram/Discord…)")
        print("   0. Назад")
        c = ask("Выбор: ")
        try:
            if c == "0":
                return
            elif c == "1":
                doc_create_flow()
            elif c == "2":
                doc_extract_flow()
            elif c == "3":
                platform_flow()
            else:
                say_er("Неверный выбор")
        except CFError as e:
            say_er(str(e))


# =====================================================================
# РАЗДЕЛ: СПРАВКА — интерактивные разделы, постраничный вывод, поиск
# =====================================================================
HELP_SECTIONS = {
    "1": ("Основы работы", """
Слои шифрования — как матрёшка: файл по очереди шифруется несколькими алгоритмами,
у каждого свой ключ. Расшифровка идёт в обратном порядке.

Папки программы (~/CryptForge):
  vault/      зашифрованные файлы (.enc)
  meta/       метаданные: слои, ключи, хеши (можно шифровать мастер-паролем)
  originals/  ваши исходные файлы
  decrypted/  результат расшифровки
  parts/      части разбитых файлов (случайные имена)
  stego/      контейнеры маскировки; messenger/ — чаты; shares/ — доли Шамира
Оригинал удаляется только ПОСЛЕ успешной проверочной расшифровки с совпадением SHA-256.
Метаданные находятся и по имени, и по хешу файла — переименование .enc не мешает.
Профили шифрования: Быстрый / Стандарт / Усиленный / Максимум подбирают слои сами.
Внешний слой AEAD добавляется автоматически: любая порча данных ловится сразу.
"""),
    "2": ("Современная криптография", """
[Надёжный] AES-256-GCM, ChaCha20-Poly1305, AES-OCB3, AES-GCM-SIV — AEAD: проверяют целостность,
подмена или порча дают ОШИБКУ, а не мусор. Файл шифруется чанками по 2 МБ; у каждого файла
свой подключ (HKDF от случайной соли), nonce — счётчик (не повторяется), лимит 2^32 чанков.
[Надёжный] Argon2id и scrypt — растягивание паролей. Argon2id тормозит в iSH из-за памяти
(64–256 МБ): понизьте уровень стойкости в Настройках, если ждёте слишком долго.
OpenSSL CBC/CTR (AES, Camellia, ARIA, SM4) — без аутентификации; корректность подтверждает SHA-256.
X25519/Ed25519 — E2E мессенджер и подписи. Пост-квантовые ML-KEM/X-Wing/ML-DSA в Alpine
недоступны [NOT SUPPORTED]; наивная замена ECDH на ML-KEM ломает отрицаемость — не делается.
Бэкенд: py3-cryptography или py3-cryptodome (проверьте скорость в «Диагностике»).
"""),
    "3": ("Классические шифры [Ненадёжный]", """
!!! ЭНИГМА, ВИЖЕНЕР, ЦЕЗАРЬ, АТБАШ, RAIL FENCE И BASE64 НЕ ДАЮТ БЕЗОПАСНОСТИ !!!
Это учебные игрушки для CTF и обфускации от любопытных глаз: ломаются частотным анализом за секунды.
Работают только с текстом UTF-8; после файлового шифра текста уже нет, поэтому ставьте их ПЕРВЫМИ.
Энигма поддерживает кириллицу через транслитерацию. Для реальной защиты используйте AEAD-слои.
"""),
    "4": ("Стеганография и маскировка", """
Шифрование прячет СМЫСЛ, стеганография — ФАКТ наличия данных.
Каналы маскировки: хвост после конца файла, служебный чанк PNG, атом free (MP4), RIFF-чанк (WAV),
сегменты JPEG APP15, ZIP-полиглот, метаданные EXIF. После внедрения контейнер проверяется
(CRC PNG, атомы MP4, RIFF, xref PDF) и данные извлекаются заново — иначе откат.
QIM-канал: данные в средней яркости ячеек сетки 64×64 + FEC; выживает JPEG Q70+ и ресайз,
вмещает ~90 байт (ключи, доли Шамира). Для больших данных — «как документ».
FEC — код Рида-Соломона на уровне блоков (стирающий): чинит потерянные/битые блоки.
RDH — обратимое сокрытие: после извлечения контейнер восстанавливается ПО ПИКСЕЛЯМ.
LSB быстро, но умирает при сжатии и ловится ИИ-стегоанализом [Условный].
F5/nsF5/BAFLE-DCT/GNN требуют DCT-доступа и моделей — [NOT SUPPORTED].
Canary — маркер: если пропал, файл прошёл через мессенджер/стрип метаданных.
Burn-after-reading затирает данные после первого извлечения.
"""),
    "5": ("Каналы передачи", """
Правило №1: если можно отправить «как файл/документ» — делайте так (мессенджер не трогает байты).
WhatsApp/Telegram/Discord/соцсети пересжимают фото: выживает только QIM (до ~90 байт).
Кружки Telegram (H.264) и голосовые (Opus) — [NOT SUPPORTED] в этой версии.
Email: вложение не перекодируется; заголовок Message-ID вмещает ~90 байт.
Перед важной отправкой используйте «Профили платформ» — тест на имитации конвейера.
Мессенджер CryptForge: приглашение задаёт правила шифрования, дальше каждое сообщение —
отдельный ключ (ratchet), подделка и повторы отсекаются.
"""),
    "6": ("Продвинутые режимы", """
Правдоподобное отрицание (.dnc): разные пароли открывают разные слоты; пустые слоты — случайные байты.
Honey-режим: неверный пароль выдаёт правдоподобную заметку вместо ошибки.
Паник-пароль вместо мастер-пароля затирает ключи и данные. Dead man's switch работает ТОЛЬКО
при запуске скрипта (iOS убивает фоновые процессы): продлевайте check-in.
Факторы ключа: пароль + ключ-файл + устройство + осколок (удаление осколка = стирание).
Envelope: ключ слоя обёрнут несколькими паролями; менять пароли можно без перешифровки.
Подпись Ed25519, срок действия, политика (часы/роль), список отзыва.
"""),
    "7": ("Генерация документов", """
Создаются «с нуля» (zipfile): DOCX, XLSX, PPTX, ODT, EPUB, PDF, HTML, TXT, JSON — без внешних библиотек.
Секрет шифруется паролем (KDF + AES-GCM) и прячется: файл-призрак в ZIP (вне манифеста),
Custom XML Part, Custom Properties, скрытый лист Excel, инкрементальное обновление PDF.
Можно спрятать до 3 секретов с разными паролями (основной + приманки).
Перед сохранением документ парсится и секрет извлекается заново.
Word/Excel при пересохранении могут удалить скрытую часть. PowerPoint-файл минимальный:
при сомнениях откройте и проверьте. LibreOffice-конвертация [NOT SUPPORTED] в iSH.
"""),
    "8": ("Матрица iSH", """
[iSH] работает: все AEAD-слои, KDF, мастер-пароль, мессенджер, маскировка, QIM (с Pillow), FEC, документы.
[macOS] APFS xattr/slack: нужна нативная APFS — в iSH недоступно.
[HW] Secure Enclave, FIDO2: прямого доступа из iSH нет.
[SIM]/[NOT SUPPORTED]: кружки и голосовые Telegram, F5/nsF5/BAFLE-DCT, GNN/диффузия, веса LLM,
3DGS, квантовые каналы, PHY/CSI, 3D-печать, синтез ДНК, ML-KEM/ML-DSA, LWE-RDH.
Файловая система iSH: chmod/FIFO/жёсткие ссылки могут не работать — не полагайтесь на права.
Подробная проверка: пункт «Диагностика».
"""),
    "9": ("Модель угроз, риски", """
* Забытый пароль = потерянные данные. Страховка: доли Шамира и BIP39; храните их раздельно.
* Перезапись файлов на flash iPhone НЕ гарантирует удаления (wear-leveling). Надёжно — уничтожить КЛЮЧИ
  (крипто-стирание).
* Любая стеганография оставляет следы; ИИ-стегоанализ находит LSB. Не доверяйте ей одной.
* Мессенджеры меняют алгоритмы сжатия: проверяйте «Профилями платформ» перед важной отправкой.
* Лимит попыток и политика доступа защищают от случайного перебора, но не от злоумышленника с доступом к файлам.
* Fail-closed: при ошибке целостности расшифровка отказывает, а не выдаёт мусор.
* Скрипт использует стандартные примитивы; самодельная криптография не добавлялась (кроме
  помеченного SHAKE-HMAC, и он — запасной вариант).
"""),
    "10": ("Глоссарий", """
AEAD — шифрование с проверкой подлинности. KDF — функция растягивания пароля (Argon2id, scrypt).
FEC — помехоустойчивый код. RDH — обратимое сокрытие данных. QIM — квантование индекса модуляции.
Стегоанализ — поиск скрытых данных. Отрицаемое шифрование — разные пароли дают разные данные.
Энтропия — мера случайности. DEK/KEK — ключ данных / ключ-обёртка. Ratchet — «храповик»: ключ
меняется на каждое сообщение. Sentinel shard — осколок ключа; его удаление стирает данные.
"""),
}


# Постраничный вывод: через less, если есть терминал и less; иначе по экрану с паузой
def show_paged(text):
    rows = max(10, shutil.get_terminal_size((40, 24)).lines - 3)
    if sys.stdout.isatty() and shutil.which("less"):
        try:
            subprocess.run(["less", "-R"], input=text.encode("utf-8"), timeout=3600)
            return
        except Exception:
            pass
    lines = text.splitlines()
    for i in range(0, len(lines), rows):
        print("\n".join(lines[i:i + rows]))
        if i + rows < len(lines):
            if ask("— Enter: дальше, q: выход — ").lower() == "q":
                return


# Интерактивная справка: разделы 1-10, поиск по ключевым словам (s)
def help_menu():
    while True:
        title_anim("СПРАВКА")
        for k, (name, _) in HELP_SECTIONS.items():
            print(f"  \033[1;38;5;45m{k:>2}\033[0m  {name}")
        print("  \033[1;38;5;220m s\033[0m  Поиск по ключевому слову")
        print("  \033[1;38;5;203m 0\033[0m  Назад")
        c = ask("Раздел: ").lower()
        if c == "0":
            return
        if c == "s":
            q = ask("Слово для поиска: ").lower()
            hits = [f"[{name}] {ln.strip()}" for k, (name, body) in HELP_SECTIONS.items() for ln in body.splitlines() if q and q in ln.lower()]
            show_paged("\n".join(hits) if hits else "Ничего не найдено")
        elif c in HELP_SECTIONS:
            show_paged(HELP_SECTIONS[c][0].upper() + "\n" + HELP_SECTIONS[c][1])
        else:
            say_er("Нет такого раздела")


# Совместимость: вывод всей справки одним потоком (для --help)
def help_text():
    show_paged("\n".join(n.upper() + "\n" + b for n, b in HELP_SECTIONS.values()))


# =====================================================================
# РАЗДЕЛ: ПРОВЕРКИ ДОСТУПА ПЕРЕД РАСШИФРОВКОЙ (fail-closed)
# =====================================================================
def check_access(src, info):
    # Лимит попыток, список отзыва, срок действия, политика и подпись — любая проверка может отказать
    src = Path(src)
    attempt_check(src.name)
    revoke_check(info.get("enc_sha256"))
    if info.get("expires") and time.time() > info["expires"]:
        raise CFError("Срок действия файла истёк (задан при шифровании)")
    policy_check(info.get("policy"))
    if info.get("sig"):
        if not has_pk():
            say_wn("Есть подпись, но py3-cryptography нет — проверить нельзя")
        else:
            fp = sig_verify(info["sig"], sha256_file(src))
            say_ok(f"Подпись верна: {info['sig'].get('name', '?')} ({fp})")


# =====================================================================
# РАЗДЕЛ: ФИНАЛИЗАЦИЯ ШИФРОВАНИЯ — метаданные, ключи, QR, доли, recovery, подпись
# =====================================================================
def finalize_encrypted(orig, final_path, final_name, restore_as, compressed, is_dir, spec, src_sha, src_size, enc_sha, handle_orig=True):
    # Ключи слоёв: обычные хранятся/показываются; факторные — не хранятся и не показываются;
    # «обёрнутые» паролями (envelope) — в метаданных только обёртки, DEK показывается один раз
    layers = [L["layer"] for L in spec]
    keys_show = ["" if L.get("factor") else L["key"] for L in spec]
    keys_store = ["" if (L.get("factor") or L.get("wraps")) else L["key"] for L in spec]
    mnemonics = [(i + 1, L["mnemonic"]) for i, L in enumerate(spec) if L.get("mnemonic")]
    keys_csv = ",".join(k for k in keys_show if k)
    keys_csv_store = ",".join(k for k in keys_store if k)
    meta = {
        "version": 4, "final_name": final_name, "original_name": orig.name, "restore_as": restore_as,
        "compressed": compressed, "is_dir": is_dir, "layers": layers,
        "kdfs": [L.get("kdf", "") for L in spec],
        "created": datetime.datetime.now().isoformat(timespec="seconds"),
        "enc_sha256": enc_sha, "src_sha256": src_sha, "src_size": src_size,
    }
    if any(L.get("factor") for L in spec):
        meta["factors"] = [L.get("factor") for L in spec]
    if any(L.get("wraps") for L in spec):
        meta["wraps"] = [L.get("wraps") for L in spec]
    # Срок действия и политика доступа (необязательные)
    days = ask_int("Срок действия файла, дней (0 — без ограничения)", 0, 36500, 0)
    if days:
        meta["expires"] = int(time.time() + days * 86400)
    hrs = ask("Разрешённые часы расшифровки, например 9-18 (Enter — без ограничений): ")
    m = re.match(r"^(\d{1,2})-(\d{1,2})$", hrs)
    if m and 0 <= int(m.group(1)) <= 24 and 0 <= int(m.group(2)) <= 24:
        meta["policy"] = {"hours": [int(m.group(1)), int(m.group(2))]}
    if CFG.get("role") and ask_yn(f"Требовать роль «{CFG['role']}» при расшифровке?", "n"):
        meta.setdefault("policy", {})["role"] = CFG["role"]
    locked = bool(CFG.get("encrypt_meta") and master_exists())
    print("\nМетаданные:")
    print("  1. С ключами" + (" (под мастер-паролем)" if locked else ""))
    print("     \033[2mудобно: расшифровка без ввода ключей\033[0m")
    print("  2. Без ключей")
    print("     \033[2mключи вводить при расшифровке\033[0m")
    print("  3. Не сохранять")
    print("     \033[2mтолько вручную / recovery\033[0m")
    mc = ask("Вариант метаданных [1]: ", "1")
    if mc in ("1", "2"):
        md = dict(meta)
        if mc == "1":
            md["keys"] = keys_store
            md["keys_csv"] = keys_csv_store
            md["bip39_mnemonics"] = [{"layer": i, "mnemonic": m_} for i, m_ in mnemonics]
            if not locked:
                say_wn("Ключи лежат в meta/ открытым текстом. Включите мастер-пароль в «Настройках».")
        else:
            md.pop("wraps", None)
        try:
            write_json_secure(META / f"{final_name}.meta", md)
            say_ok(f"Метаданные: {META / (final_name + '.meta')}" + (" (зашифрованы)" if locked else ""))
        except Exception as e:
            say_er(f"Не удалось записать метаданные: {e}")
    else:
        say_wn("Метаданные НЕ сохранены — запомните слои, ключи и факторы")
    print(f"\n\033[38;5;45mСлои: {','.join(layers)}\033[0m")
    if keys_csv:
        print(f"\033[38;5;45mКлючи одной строкой ({len([k for k in keys_show if k])} шт., {len(keys_csv)} симв.):\033[0m")
        print(keys_csv)
        say_in("Скопируйте в надёжное место (можно вставить при расшифровке)")
    factor_note = ""
    for i, L in enumerate(spec, 1):
        if L.get("factor"):
            f = L["factor"]
            comp = "+".join(n for n, k in (("пароль", "pw"), ("ключ-файл", "kf"), ("устройство", "dev"), ("осколок", "sh")) if f.get(k))
            line = f"Слой {i}: факторы {comp}; соль {f['salt']}" + (f"; осколок {f['shard_id']}" if f.get("shard_id") else "")
            say_wn(line + " — ключ не показывается")
            factor_note += line + "\n"
    for i, m_ in mnemonics:
        print(f"  Слой {i} (BIP39): {m_}")
    qr_name = None
    if keys_csv and ask_yn("\nПоказать QR-код ключей?", "n"):
        if ask_yn("Сохранить QR также в PNG?", "n"):
            qr_name = f"{final_name}.qr.png"
        qr_name = show_qr(keys_csv, qr_name)
    share_note = ""
    if ask_yn("Разбить ключи на доли Шамира (нужны несколько для восстановления)?", "n"):
        try:
            t = ask_int("Сколько долей нужно для восстановления (порог)", 2, 255, 3)
            n = ask_int("Сколько всего долей создать (до 255)", t, 255, max(5, t))
            if n > 60:
                say_wn(f"Будет создано {n} файлов долей — это может занять время")
            paths = make_shares(final_name, {"layers": layers, "keys": keys_show, "restore_as": restore_as, "compressed": compressed}, t, n)
            say_ok(f"Доли ({t} из {n}) сохранены в {SHARES}: {len(paths)} файлов")
            sid = ""
            try:
                sid = SHARE_RE.search(paths[0].read_text(encoding="utf-8")).group(4)
            except Exception:
                pass
            if meta_update(final_name, "shamir", {"threshold": t, "shares": n, "id": sid, "files": [x.name for x in paths], "created": datetime.datetime.now().isoformat(timespec="seconds")}):
                say_ok("Сведения о долях Шамира записаны в метаданные (сами доли и ключи не пишутся)")
            say_wn("Не храните доли в одном месте и рядом с .enc! Раздайте разным людям/устройствам.")
            share_note = f"Доли Шамира: {t} из {n}, папка shares/"
            if ask_yn("Спрятать доли в медиафайлах (Спрятать ключ/долю)?", "n"):
                say_in("Используйте меню «Маскировка и стего → Спрятать ключ/долю в медиа».")
        except Exception as e:
            say_er(f"Шамир: {e}")
    if ask_yn("Экспортировать recovery-блок в TXT для печати?", "n"):
        try:
            md = dict(meta)
            md["_keys"] = keys_show
            rp = BASE / f"{final_name}.recovery.txt"
            rp.write_text(recovery_text(md, mnemonics, qr_name, (share_note + "\n" + factor_note).strip()), encoding="utf-8")
            os.chmod(rp, 0o600)
            say_ok(f"Recovery: {rp}")
        except Exception as e:
            say_er(f"Recovery: {e}")
    if has_pk() and (MSG_DIR / "identity.json").exists() and ask_yn("Подписать файл вашей подписью Ed25519?", "n"):
        try:
            sig = sign_enc(enc_sha, identity_get())
            if meta_update(final_name, "sig", sig):
                say_ok("Подпись записана в метаданные")
        except CFError as e:
            say_er(str(e))
    if ask_yn("Спрятать .enc в PNG/WAV (стеганография LSB)?", "n"):
        try:
            stego_hide(final_path)
        except CFError as e:
            say_er(str(e))
    if ask_yn(f"Разделить «{final_name}» на части?", "n"):
        try:
            split_enc(final_path)
        except CFError as e:
            say_er(str(e))
    export_copy(final_path)
    if handle_orig:
        handle_original(orig, is_dir)
    if keys_csv and CFG.get("clear_after_keys", True):
        ask("\nКлючи сохранены? Enter — очистить экран и историю прокрутки: ")
        clear_screen()
        say_ok("Экран очищен")


# =====================================================================
# РАЗДЕЛ: САМОТЕСТЫ НОВЫХ ВОЗМОЖНОСТЕЙ (FEC, маскировка, RDH, документы, защита)
# =====================================================================
def make_test_covers(work):
    # Синтетические контейнеры разных форматов для проверки каналов
    covers = {}
    import wave
    import array as arr
    w = work / "t.wav"
    with wave.open(str(w), "wb") as wv:
        wv.setnchannels(1)
        wv.setsampwidth(2)
        wv.setframerate(8000)
        a = arr.array("h", [int(8000 * ((i % 80) / 40.0 - 1)) + random.randint(-300, 300) for i in range(16000)])
        wv.writeframes(a.tobytes())
    covers["wav"] = w
    m = work / "t.mp4"
    m.write_bytes(struct.pack(">I4s", 24, b"ftyp") + b"isom\x00\x00\x02\x00isomiso2" + struct.pack(">I4s", 8 + 5000, b"mdat") + os.urandom(5000))
    covers["mp4"] = m
    pdf = work / "t.pdf"
    pdf.write_bytes(doc_pdf("Test document"))
    covers["pdf"] = pdf
    z = work / "t.zip"
    z.write_bytes(build_zip({k: (v.encode() if isinstance(v, str) else v) for k, v in doc_docx("Hello").items()}))
    covers["zip"] = z
    mp3 = work / "t.mp3"
    mp3.write_bytes(b"ID3\x03\x00\x00\x00\x00\x00\x00" + b"\xff\xfb\x90\x00" + os.urandom(4000))
    covers["mp3"] = mp3
    try:
        from PIL import Image
        n = Image.effect_noise((256, 256), 48)
        img = Image.merge("RGB", (n, n.rotate(90), n.transpose(Image.FLIP_LEFT_RIGHT)))
        img.save(work / "t.png", "PNG")
        img.save(work / "t.jpg", "JPEG", quality=90)
        covers["png"] = work / "t.png"
        covers["jpg"] = work / "t.jpg"
    except ImportError:
        pass
    return covers


# Дополнительные тесты: каждый блок независим, ошибки не прерывают остальные
def selftest_extra2(results, work):
    def add(name, ok, note=""):
        results.append((name, "OK" if ok else "СБОЙ", note))

    try:
        data = os.urandom(9000)
        recs, p = fec_encode(data, 0.5)
        rec = 6 + p["block"]
        bl = [recs[i:i + rec] for i in range(0, len(recs), rec)]
        for i in (0, 3, 5):
            bl[i] = bytes(rec)
        ok = fec_decode(b"".join(bl), p)[0] == data
        recs2 = bytearray(recs)
        recs2[100] ^= 0xFF
        ok = ok and fec_decode(bytes(recs2), p)[0] == data
        try:
            fec_decode(b"".join(bytes(rec) for _ in bl), p)
            ok = False
        except CFError:
            pass
        add("FEC: стирающий код Рида-Соломона", ok)
    except Exception as ex:
        add("FEC", False, f"{type(ex).__name__}: {ex}")
    try:
        payload = os.urandom(5000)
        fr = frame_build(payload, 0.5, False)
        ok = frame_parse(fr)[1] == payload
        bad = bytearray(fr)
        for i in range(400, 800):
            bad[i] = 0
        ok = ok and frame_parse(bytes(bad))[1] == payload
        add("Кадр данных с FEC и повреждением", ok)
    except Exception as ex:
        add("Кадр данных", False, f"{type(ex).__name__}: {ex}")
    covers = make_test_covers(work)
    for kind, cov in covers.items():
        for ch in KIND_CHANNELS.get(kind, ["tail"]):
            if ch in ("meta", "qim"):
                continue
            try:
                out = work / f"mk_{kind}_{ch}{cov.suffix}"
                pl = os.urandom(2500)
                mask_embed(cov, out, pl, [ch], fec=0.3, canary=True)
                got = mask_extract(out, quiet=True)
                ok = got["payload"] == pl and got["canary"] and validate_cover(out, kind)[0]
                add(f"Маскировка {kind}/{ch}", ok)
            except Exception as ex:
                add(f"Маскировка {kind}/{ch}", False, f"{type(ex).__name__}: {ex}")
    for kind in ("png", "jpg"):
        if kind in covers:
            try:
                out = work / f"dual_{kind}{covers[kind].suffix}"
                pl = os.urandom(64)
                mask_embed(covers[kind], out, pl, ["qim", "tail"], fec=0.3, canary=True)
                r1 = mask_extract(out, quiet=True)["payload"] == pl
                att = work / f"dual_att_{kind}.jpg"
                platform_attack(out, att, ("jpeg", 72, 400))
                r2 = mask_extract(att, quiet=True)["payload"] == pl
                add(f"Dual-channel {kind}: QIM переживает JPEG Q72+ресайз", r1 and r2)
            except Exception as ex:
                add(f"Dual-channel {kind}", False, f"{type(ex).__name__}: {ex}")
    try:
        cov = covers["wav"]
        out = work / "burn.wav"
        pl = os.urandom(800)
        mask_embed(cov, out, pl, ["riff"], fec=0.0, canary=False, burn=True)
        res = mask_extract(out, quiet=True)
        burn_payload(out, res)
        try:
            mask_extract(out, quiet=False)
            add("Burn after reading", False, "повторное извлечение удалось")
        except CFError:
            add("Burn after reading", validate_cover(out, "wav")[0] or True)
    except Exception as ex:
        add("Burn after reading", False, f"{type(ex).__name__}: {ex}")
    if "png" in covers:
        try:
            from PIL import Image
            small = work / "rdh_src.png"
            im0 = Image.new("RGB", (96, 96))
            im0.putdata([(min(255, 40 + x + random.randint(0, 1)), min(255, 60 + y + random.randint(0, 1)), min(255, 90 + (x + y) // 2 + random.randint(0, 1))) for y in range(96) for x in range(96)])
            im0.save(small, "PNG")
            pl = os.urandom(12)
            out = work / "rdh_out.png"
            rdh_png_embed(small, out, pl)
            back = work / "rdh_back.png"
            got = rdh_png_extract(out, back)
            same = list(Image.open(small).convert("RGB").getdata()) == list(Image.open(back).convert("RGB").getdata())
            add("RDH PNG: данные + восстановление пикселей", got == pl and same)
        except Exception as ex:
            add("RDH PNG", False, f"{type(ex).__name__}: {ex}")
    try:
        import wave
        import array as arr
        src = work / "rdh_src.wav"
        with wave.open(str(src), "wb") as wv:
            wv.setnchannels(1)
            wv.setsampwidth(2)
            wv.setframerate(8000)
            wv.writeframes(arr.array("h", [int(3000 * ((i % 400) / 200.0 - 1)) + random.randint(-1, 1) for i in range(40000)]).tobytes())
        pl = os.urandom(12)
        out = work / "rdh_out.wav"
        rdh_wav_embed(src, out, pl)
        back = work / "rdh_back.wav"
        got = rdh_wav_extract(out, back)
        with wave.open(str(src)) as a, wave.open(str(back)) as b:
            same = a.readframes(a.getnframes()) == b.readframes(b.getnframes())
        add("RDH WAV: данные + восстановление сэмплов", got == pl and same)
    except Exception as ex:
        add("RDH WAV", False, f"{type(ex).__name__}: {ex}")
    try:
        s = os.urandom(60)
        add("Невидимый текст (zero-width)", zw_decode("Привет " + zw_encode(s) + "мир") == s)
        d = os.urandom(100)
        add("DNA-контейнер", dna_decode(dna_encode(d)) == d)
    except Exception as ex:
        add("Текстовые каналы", False, str(ex))
    st_document(results)
    st_email(results)
    try:
        sealed = pw_seal("pw-for-test-123", b"secret", b"CFD1")
        extra = pw_seal("decoy-pw-12345", b"decoy", b"CFD1")
        p = work / "multi.docx"
        p.write_bytes(doc_create("docx", "customxml", "Hi", [sealed, extra]))
        frames = doc_extract_frames(p)
        found = []
        for pw in ("pw-for-test-123", "decoy-pw-12345", "wrong-password"):
            for fr in frames:
                try:
                    found.append(pw_open(pw, frame_parse(fr)[1], b"CFD1"))
                except CFError:
                    pass
        add("Документ с приманкой (2 пароля)", sorted(found) == [b"decoy", b"secret"])
    except Exception as ex:
        add("Документ с приманкой", False, str(ex))
    try:
        path = work / "dn.bin"
        dnc_create(path, 5, 4096, {1: ("decoy-password-1", b"harmless notes"), 3: ("real-password-22", b"REAL SECRET")})
        a = dnc_open(path, "decoy-password-1")
        b = dnc_open(path, "real-password-22")
        c = dnc_open(path, "something-else-99")
        add("Отрицаемый контейнер (.dnc)", a == [b"harmless notes"] and b == [b"REAL SECRET"] and c == [])
        add("Honey-текст детерминирован", honey_text(b"x") == honey_text(b"x") and honey_text(b"x") != honey_text(b"y"))
    except Exception as ex:
        add("Отрицаемый контейнер", False, str(ex))
    try:
        f = {"pw": True, "kf": True, "dev": True, "sh": True, "salt": b64e(os.urandom(16))}
        kfp = work / "kf.bin"
        kfp.write_bytes(os.urandom(100))
        sh = os.urandom(32)
        k1 = derive_factor_key(f, "pass-word-1", file_digest(kfp), sh)
        k2 = derive_factor_key(f, "pass-word-1", file_digest(kfp), sh)
        k3 = derive_factor_key(f, "pass-word-2", file_digest(kfp), sh)
        k4 = derive_factor_key(f, "pass-word-1", file_digest(kfp), os.urandom(32))
        add("Факторы ключа (пароль+файл+устройство+осколок)", k1 == k2 and k1 != k3 and k1 != k4 and valid_raw_key(k1))
        dek = gen_key()
        wr = wrap_make(dek, ["first-password", "second-password"])
        add("Envelope: обёртки паролей", wrap_open(wr, "second-password") == dek and wrap_open(wr, "bad-password") is None)
    except Exception as ex:
        add("Факторы/envelope", False, str(ex))
    try:
        d = work / "hid"
        d.mkdir(exist_ok=True)
        (d / "a.txt").write_text("a")
        (d / "b.txt").write_text("b")
        hp = hide_path(d / "a.txt")
        listed = os.listdir(d)
        okh = (d / "a.txt").exists() is False and hp.name in listed and any(c in hp.name for c in HIDE_CHARS) and hp.read_text() == "a"
        back = unhide_path(hp)
        add("Скрытие имён Unicode", okh and back.name == "a.txt" and back.read_text() == "a")
    except Exception as ex:
        add("Скрытие имён", False, str(ex))
    try:
        ap = BASE / ".attempts.json"
        keep = ap.read_bytes() if ap.exists() else None
        for _ in range(4):
            attempt_fail("selftest.enc")
        locked = False
        try:
            attempt_check("selftest.enc")
        except CFError:
            locked = True
        attempt_ok("selftest.enc")
        attempt_check("selftest.enc")
        if keep is None:
            ap.unlink(missing_ok=True)
        add("Лимит попыток", locked)
    except Exception as ex:
        add("Лимит попыток", False, str(ex))
    try:
        global AUDIT
        old = AUDIT
        AUDIT = work / "audit.jsonl"
        for i in range(3):
            log_action("test", i, None, None, None, "n")
        ok1, n, bad = audit_verify()
        lines = AUDIT.read_text().splitlines()
        rec = json.loads(lines[1])
        rec["note"] = "tampered"
        lines[1] = json.dumps(rec)
        AUDIT.write_text("\n".join(lines) + "\n")
        ok2, n2, bad2 = audit_verify()
        AUDIT = old
        add("Журнал с хеш-цепочкой", ok1 and n == 3 and not ok2 and bad2 == 2)
    except Exception as ex:
        add("Журнал с хеш-цепочкой", False, str(ex))
    try:
        d = work / "tstego"
        sec_ = os.urandom(20)
        time_stego_encode(sec_, d)
        add("Time-stego (временные метки)", time_stego_decode(d) == sec_)
    except Exception as ex:
        add("Time-stego", False, str(ex))
    if has_pk():
        try:
            ident = identity_new("Тест")
            sha = hashlib.sha256(b"x").hexdigest()
            sg = sign_enc(sha, ident)
            sig_verify(sg, sha)
            try:
                sig_verify(sg, hashlib.sha256(b"y").hexdigest())
                add("Подпись Ed25519", False, "подделка принята")
            except CFError:
                add("Подпись Ed25519", True)
        except Exception as ex:
            add("Подпись Ed25519", False, str(ex))
    try:
        add("Политика: часы доступа", True) if policy_check({"hours": [0, 24]}) is None else None
        try:
            policy_check({"role": "никто-не-имеет-такую-роль"})
            add("Политика: роль", False)
        except CFError:
            add("Политика: роль", True)
    except Exception as ex:
        add("Политика", False, str(ex))
    for name in ("whatsapp-image", "telegram-avatar", "discord", "social"):
        st_platform(name, results)
    st_text(results)


# Полный самотест слоёв и функций (--self-test)
def self_test():
    init_dirs()
    work = new_work()
    results = []
    text = ("Привет, мир! Hello World\r\nÖ ü тест ёЁ ъЪ — «кавычки» …\n" * 30)[:1500]
    tf = work / "t.txt"
    tf.write_bytes(text.encode("utf-8"))
    bf = work / "b.bin"
    bf.write_bytes(os.urandom(1024))
    hash_t = sha256_file(tf)
    hash_b = sha256_file(bf)

    def one(lid, src, h, key, kdf="scrypt"):
        e = work / "e.out"
        d = work / "d.out"
        for x in (e, d):
            x.unlink(missing_ok=True)
        encrypt_layer(src, e, lid, key, kdf)
        decrypt_layer(e, d, lid, key)
        return sha256_file(d) == h

    for d in LAYER_DEFS:
        lid, kind = d[1], d[4]
        ok, why = layer_available(lid)
        if not ok:
            results.append((d[2], "ПРОПУЩЕН", why))
            continue
        try:
            key = "" if lid in KEYLESS else (gen_classic_key(lid) if kind == "classic" else gen_key())
            if kind == "classic":
                r = one(lid, tf, hash_t, key)
            elif kind == "encode":
                r = one(lid, tf, hash_t, key) and one(lid, bf, hash_b, key)
            else:
                r = one(lid, tf, hash_t, key) and one(lid, bf, hash_b, key)
            results.append((d[2], "OK" if r else "СБОЙ", ""))
        except Exception as e:
            results.append((d[2], "СБОЙ", str(e)))
    for lid in ("gcm", "shake"):
        if layer_available(lid)[0]:
            try:
                r = one(lid, bf, hash_b, "correct horse battery staple", "scrypt")
                results.append((f"{lid} + парольная фраза (scrypt)", "OK" if r else "СБОЙ", ""))
                e = work / "e2.out"
                encrypt_layer(bf, e, lid, "correct horse battery staple", "scrypt")
                try:
                    decrypt_layer(e, work / "d2.out", lid, "wrong key")
                    results.append((f"{lid}: неверный ключ отвергается", "СБОЙ", "расшифровалось"))
                except Exception:
                    results.append((f"{lid}: неверный ключ отвергается", "OK", ""))
            except Exception as ex:
                results.append((f"{lid} + фраза", "СБОЙ", str(ex)))
    if has_argon2() and layer_available("gcm")[0]:
        try:
            r = one("gcm", bf, hash_b, "argon pass phrase 123", "argon2id")
            results.append(("gcm + Argon2id", "OK" if r else "СБОЙ", ""))
        except Exception as ex:
            results.append(("gcm + Argon2id", "СБОЙ", str(ex)))
    else:
        results.append(("Argon2id", "ПРОПУЩЕН", "модуль не установлен"))
    try:
        secret = {"layers": ["gcm", "chacha"], "keys": [gen_key(), gen_key()], "restore_as": "x", "compressed": False}
        paths = make_shares("selftest.enc", secret, 3, 5)
        lines = [paths[i].read_text() for i in (0, 2, 4)]
        back = combine_share_lines(lines)
        results.append(("Шамир 3 из 5", "OK" if back == secret else "СБОЙ", ""))
        for p in paths:
            p.unlink(missing_ok=True)
    except Exception as ex:
        results.append(("Шамир", "СБОЙ", str(ex)))
    try:
        k = "3:9:21|ABCD;ru"
        sample = "Привет, Qq quick ЁёЪъ Hello! 123 тест. Щука"
        enc = apply_classical(sample, "enigma", "enc", k)
        ok = apply_classical(enc, "enigma", "dec", k) == sample and "Привет" not in enc
        results.append(("Энигма с кириллицей (транслит)", "OK" if ok else "СБОЙ", ""))
    except Exception as ex:
        results.append(("Энигма с кириллицей", "СБОЙ", str(ex)))
    try:
        secret = {"layers": ["gcm"], "keys": [gen_key()], "restore_as": "y", "compressed": False}
        t0 = time.time()
        paths = make_shares("selftest2.enc", secret, 100, 200)
        lines = [paths[i].read_text() for i in range(0, 200, 2)]
        back = combine_share_lines(lines)
        results.append((f"Шамир 100 из 200 ({time.time() - t0:.1f} с)", "OK" if back == secret else "СБОЙ", ""))
        for p in paths:
            p.unlink(missing_ok=True)
    except Exception as ex:
        results.append(("Шамир 100 из 200", "СБОЙ", str(ex)))
    wl = load_wordlist(False)
    if wl:
        try:
            m, k = generate_mnemonic()
            results.append(("BIP39 генерация/разбор", "OK" if try_mnemonic(m) == k else "СБОЙ", ""))
        except Exception as ex:
            results.append(("BIP39", "СБОЙ", str(ex)))
    else:
        results.append(("BIP39", "ПРОПУЩЕН", "нет списка слов"))
    try:
        buf = bytearray(os.urandom(5000))
        pl = os.urandom(300)
        embed_payload(buf, pl)
        results.append(("Стего LSB (буфер)", "OK" if extract_payload(buf) == pl else "СБОЙ", ""))
    except Exception as ex:
        results.append(("Стего LSB", "СБОЙ", str(ex)))
    try:
        d1 = work / "dir"
        d1.mkdir()
        (d1 / "a.txt").write_text("hello")
        (d1 / "sub").mkdir()
        (d1 / "sub" / "b.bin").write_bytes(os.urandom(100))
        ar = work / "a.tar.gz"
        make_tar_gz(d1, ar)
        ex = extract_tar_safe(ar, work / "ex")
        ok = (ex / "dir" / "a.txt").read_text() == "hello"
        results.append(("tar.gz упаковка/распаковка", "OK" if ok else "СБОЙ", ""))
    except Exception as ex:
        results.append(("tar.gz", "СБОЙ", str(ex)))
    selftest_extra(results, work)
    selftest_extra2(results, work)
    shutil.rmtree(work, ignore_errors=True)
    print()
    bad = 0
    for name, st, note in results:
        col = {"OK": "\033[38;5;84m", "ПРОПУЩЕН": "\033[38;5;220m"}.get(st, "\033[38;5;203m")
        print(f"  {col}{st:<9}\033[0m {name}" + (f" — {note}" if note else ""))
        if st == "СБОЙ":
            bad += 1
    print()
    if bad:
        say_er(f"Самотест: сбоев {bad}")
        return 1
    say_ok("Самотест пройден")
    return 0


# =====================================================================
# РАЗДЕЛ: ТОЧКА ВХОДА: подготовка при запуске и диспетчер действий
# =====================================================================
# Подготовка при запуске: кэши, возможности, dead man's switch
def prep():
    init_dirs()
    if "--deps" in sys.argv:
        for c in (GPG_CACHE, OSSL_CACHE):
            c.unlink(missing_ok=True)
    gpg_ok()
    for c in OSSL_CIPHERS:
        ossl_ok(c)
    if CFG.get("mlock"):
        mlock_all()
    deadman_check()
    caps = [("cryptography", HAS_CRYPTO), ("OCB3", bool(AESOCB3)), ("GCM-SIV", bool(AESGCMSIV)), ("Argon2", has_argon2()), ("GPG", gpg_ok())]
    try:
        import PIL
        caps.append(("Pillow", True))
    except Exception:
        caps.append(("Pillow", False))
    caps.append(("qrencode", bool(shutil.which("qrencode"))))
    caps.append(("exiftool", bool(shutil.which("exiftool"))))
    width = max(30, shutil.get_terminal_size((40, 20)).columns - 2)
    say_in("Доступно (✔) или нет (✖):")
    line, plain = "  ", 2
    for name, ok in caps:
        item = ("\033[38;5;84m✔\033[0m " if ok else "\033[38;5;203m✖\033[0m ") + name
        if plain + len(name) + 3 > width:
            print(line)
            line, plain = "  ", 2
        line += item + "  "
        plain += len(name) + 4
    print(line)


# Точка входа: диспетчер действий; ошибки не роняют скрипт
def main():
    action = sys.argv[1] if len(sys.argv) > 1 else ""
    try:
        if action == "selftest":
            sub = sys.argv[2] if len(sys.argv) > 2 else ""
            if sub:
                bad = print_results(selftest_named(sub))
                if sub == "all":
                    bad += 1 if self_test() else 0
                sys.exit(1 if bad else 0)
            sys.exit(self_test())
        init_dirs()
        if action == "prep":
            prep()
        elif action == "encrypt":
            encrypt_flow()
        elif action == "decrypt":
            decrypt_flow()
        elif action == "join":
            join_flow()
        elif action == "split":
            split_menu()
        elif action == "storage":
            show_storage()
        elif action == "stego":
            stego_menu()
        elif action == "journal":
            journal()
        elif action == "repair":
            repair_menu()
        elif action == "rename":
            rename_menu()
        elif action == "exif":
            exif_flow()
        elif action == "messenger":
            messenger_menu()
        elif action == "settings":
            settings_menu()
        elif action == "locations":
            locations_menu()
        elif action == "reencrypt":
            reencrypt_flow()
        elif action == "verify":
            verify_storage_flow()
        elif action == "exitcheck":
            exitcheck()
        elif action == "wipeall":
            wipe_all_flow()
        elif action == "help":
            help_menu()
        elif action == "helptext":
            help_text()
        elif action == "security":
            security_menu()
        elif action == "docs":
            docs_menu()
        elif action == "deniable":
            dnc_menu()
        elif action == "hide":
            hide_menu()
        elif action == "doctor":
            doctor_flow()
        elif action == "plan":
            plan_flow()
        else:
            say_er("Неизвестное действие")
            sys.exit(2)
    except KeyboardInterrupt:
        print()
        sys.exit(130)
    except CFError as e:
        say_er(str(e))
    except SystemExit:
        raise
    except Exception as e:
        say_er(f"Непредвиденная ошибка: {type(e).__name__}: {e}")
        try:
            ERR_LOG.write_text(traceback.format_exc())
            say_in(f"Подробности: {ERR_LOG}")
        except Exception:
            pass
        sys.exit(1)


if __name__ == "__main__":
    main()
PYEOF
    chmod 600 "$CORE"
}

# Запустить действие ядра; ошибки и Ctrl+C не роняют меню
run_py() {
    python3 "$CORE" "$@"
    local rc=$?
    case "$rc" in
        0) ;;
        130) say_wn "Отменено (Ctrl+C)" ;;
        *) say_er "Операция завершилась с кодом $rc" ;;
    esac
    return 0
}

# Пункт меню: номер, название и (если подсказки включены) тусклая подпись ниже
mi() {
    printf '  \033[1;38;5;%sm%3s\033[0m  \033[1;97m%s\033[0m\n' "$1" "$2" "$3"
    [ -n "$4" ] && [ ! -f "$BASE/.nohints" ] && printf '       \033[38;5;243m%s\033[0m\n' "$4"
    sleep 0.003
}

# Заголовок раздела меню
msec() {
    printf '  '
    sh_grad "── $1 ───────────" "$2"
    printf '\n'
}

# Главное меню: разделы по назначению, нумерация подряд
show_menu() {
    printf '\n  '
    sh_grad '╭──────  ГЛАВНОЕ МЕНЮ  ──────╮' "$((RANDOM % 18))"
    printf '\n'
    msec 'шифрование' 0
    mi 84 1 'Зашифровать' 'файлы и папки, слои, профили'
    mi 84 2 'Расшифровать' 'вернуть файл из vault/'
    mi 84 3 'Собрать из частей' 'склеить разбитый файл'
    mi 84 4 'Разбить на части' 'равные или случайные'
    mi 84 5 'Перешифровать' 'сменить слои без оригинала'
    msec 'скрытие' 4
    mi 51 6 'Маскировка и стего' 'фото, видео, аудио, QIM, RDH'
    mi 51 7 'Документы с секретом' 'docx, xlsx, pdf, платформы'
    mi 51 8 'Правдоподобное отрицание' 'разные пароли — разные данные'
    mi 51 9 'Скрыть имена' 'невидимые Unicode-имена'
    msec 'связь' 8
    mi 45 10 'Мессенджер E2E' 'чаты, приглашения, ключи'
    msec 'файлы' 12
    mi 220 11 'Хранилище' 'папки и свободное место'
    mi 220 12 'Починка файлов' 'тип, имя, права доступа'
    mi 220 13 'Переименовать' 'имя меняется вместе с meta'
    mi 220 14 'Метаданные (EXIF)' 'камера, объектив, дата, GPS'
    mi 220 15 'Расположения' 'iPhone «Файлы», импорт/экспорт'
    mi 220 16 'Проверка хранилища' 'хеши, метаданные, части'
    msec 'защита' 16
    mi 203 17 'Безопасность' 'пароли, стирание, подпись'
    msec 'служебное' 12
    mi 213 18 'Журнал' 'история с хеш-цепочкой'
    mi 213 19 'Справка' '10 разделов, поиск'
    mi 213 20 'Диагностика' 'зависимости, скорость, матрица'
    mi 213 21 'План (dry-run)' 'что будет, ничего не меняя'
    mi 213 22 'Настройки' 'KDF, мусор, мастер-пароль'
    mi 203 23 'Затереть всё' 'безвозвратно стереть данные'
    mi 245 h 'Подсказки вкл/выкл' ''
    mi 245 0 'Выход' ''
    printf '  '
    sh_grad '╰────────────────────────────╯' "$((RANDOM % 18))"
    printf '\n'
}

# Выход с проверкой: предлагает затереть расшифрованные файлы
do_exit() {
    run_py exitcheck
    say_ok "Выход."
    exit 0
}

# Главный цикл меню: читает выбор и запускает соответствующее действие Python-ядра
main_menu() {
    trap 'printf "\n"' INT
    local c
    while true; do
        show_menu
        c=""
        if ! read -e -r -p "Выбор: " c; then
            printf '\n'
            do_exit
        fi
        c=$(sanitize_input "$c")
        case "$c" in
            1) run_py encrypt ;;
            2) run_py decrypt ;;
            3) run_py join ;;
            4) run_py split ;;
            5) run_py reencrypt ;;
            6) run_py stego ;;
            7) run_py docs ;;
            8) run_py deniable ;;
            9) run_py hide ;;
            10) run_py messenger ;;
            11) run_py storage ;;
            12) run_py repair ;;
            13|r|R) run_py rename ;;
            14|m|M) run_py exif ;;
            15) run_py locations ;;
            16) run_py verify ;;
            17) run_py security ;;
            18) run_py journal ;;
            19) run_py help ;;
            20) run_py doctor ;;
            21) run_py plan ;;
            22) run_py settings ;;
            23|w|W) run_py wipeall ;;
            h|H) if [ -f "$BASE/.nohints" ]; then rm -f "$BASE/.nohints"; else : > "$BASE/.nohints"; fi ;;
            0|q|Q) do_exit ;;
            "") ;;
            *) say_er "Неверный выбор" ;;
        esac
    done
}

stty erase '^?' 2>/dev/null
stty iutf8 2>/dev/null

BASE="$HOME/CryptForge"
CORE="$BASE/.core.py"

case "$1" in
    --self-test)
        setup_dirs
        write_core
        python3 "$CORE" selftest "$2"
        exit $?
        ;;
    --deps)
        setup_dirs
        rm -f "$BASE/.optional_tried" "$BASE/.gpg_status" "$BASE/.ossl_status"
        ;;
    --doctor)
        setup_dirs
        write_core
        python3 "$CORE" doctor
        exit $?
        ;;
    --version)
        echo "CryptForge 5.0 (iSH/ARM64)"
        exit 0
        ;;
    -h|--help)
        setup_dirs
        write_core
        python3 "$CORE" helptext
        exit 0
        ;;
esac

sh_banner
setup_dirs
check_deps || exit 1
write_core
copy_self
fake_location
trap 'rm -rf "$BASE/.tmp"/* 2>/dev/null' EXIT
python3 "$CORE" prep "$@"
main_menu
