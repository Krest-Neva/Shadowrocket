#!/bin/sh

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; BLUE='\033[0;34m'; CYAN='\033[0;36m'; NC='\033[0m'
say() { printf '%b\n' "$1"; }

LANG_FILE="$HOME/.video_downloader_lang"

if [ -f "$LANG_FILE" ]; then
    LANG=$(cat "$LANG_FILE" 2>/dev/null)
    if [ "$LANG" != "en" ] && [ "$LANG" != "ru" ]; then LANG="ru"; fi
else
    say "${YELLOW}========================================${NC}"
    say "${YELLOW}  Language / Язык${NC}"
    say "${YELLOW}========================================${NC}"
    say "  1 - Русский [по умолчанию]"
    say "  2 - English"
    printf '%s' "Выбор / Choice [1]: "
    IFS= read -r LC
    if [ "$LC" = "2" ]; then LANG="en"; else LANG="ru"; fi
    echo "$LANG" > "$LANG_FILE"
fi
export LANG

T() {
    if [ "$LANG" = "en" ]; then
        case "$1" in
            apk_update) echo "[*] apk update..." ;;
            apk_fail) echo "[!] apk update failed, continue" ;;
            apk_skip) echo "[!] apk" ;;
            not_installed) echo "not installed" ;;
            pip_install) echo "[*] pip: yt-dlp..." ;;
            pip_fail) echo "[!] pip install failed" ;;
            setup_header) echo "=== Video Downloader ===" ;;
            installing) echo "[*] yt-dlp not found — installing" ;;
            not_imported) echo "[!] yt-dlp/tqdm not importable, but fallback methods will be tried" ;;
            no_python) echo "[!] python3 not found" ;;
            *) echo "$1" ;;
        esac
    else
        case "$1" in
            apk_update) echo "[*] Обновление apk..." ;;
            apk_fail) echo "[!] apk update не удался, продолжаем" ;;
            apk_skip) echo "[!] apk" ;;
            not_installed) echo "не установлен" ;;
            pip_install) echo "[*] pip: установка yt-dlp..." ;;
            pip_fail) echo "[!] pip install не удался" ;;
            setup_header) echo "=== Универсальный загрузчик видео ===" ;;
            installing) echo "[*] yt-dlp не найден — устанавливаю" ;;
            not_imported) echo "[!] yt-dlp/tqdm не импортируются, но скрипт попробует запасные методы" ;;
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
        apk add --no-cache "$p" >/dev/null 2>&1 || say "${YELLOW}$(T apk_skip): $p $(T not_installed)${NC}"
    done

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

cat > /tmp/video_downloader.py << 'PYEOF'
import sys, re, json, socket, shutil, subprocess, urllib.request
from pathlib import Path
from urllib.parse import urlparse

_orig_gai = socket.getaddrinfo
def _gai_v4(host, port, family=0, type=0, proto=0, flags=0):
    return _orig_gai(host, port, socket.AF_INET, type, proto, flags)
socket.getaddrinfo = _gai_v4

try:
    import yt_dlp
except ImportError:
    yt_dlp = None
try:
    from tqdm import tqdm
except ImportError:
    tqdm = None

LANG_FILE = Path.home() / ".video_downloader_lang"
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
        "menu_download": "Скачать видео",
        "menu_files": "Управление файлами",
        "menu_language": "Сменить язык",
        "menu_exit": "Выход (q)",
        "choice": "Ваш выбор",
        "invalid_choice": "Неверный выбор",
        "videos_dir": "Видео сохраняются в",
        "enter_urls": "Введите ссылки на видео (по одной на строку).",
        "enter_urls_hint": "Пустая строка — начать загрузку. 'q' — меню.",
        "available_formats": "Доступные форматы видео",
        "select_video": "Номер видеоформата (Enter — совместимый с iPhone)",
        "available_audio": "Доступные аудиодорожки",
        "select_audio": "Номер аудио (Enter — лучшее)",
        "with_audio": "со звуком",
        "no_audio": "без звука",
        "invalid_default": "Неверный выбор, используется формат по умолчанию",
        "selector": "Селектор",
        "finished": "Загрузка завершена",
        "trying_generic": "Пробую generic-экстрактор...",
        "retry_tls": "Повторить без проверки TLS?",
        "all_exhausted": "Все попытки исчерпаны",
        "scanning": "Сканирование страницы",
        "found_videos": "Найдено видео",
        "no_videos": "Видео не найдены",
        "multiple_videos": "Найдено несколько видео",
        "number_or_all": "Номер или 'all'",
        "invalid_url": "Некорректная ссылка",
        "stopped": "Работа остановлена",
        "fm_title": "Управление файлами",
        "fm_path": "Папка",
        "fm_count": "Файлов",
        "fm_empty": "Папка пуста",
        "fm_1": "Удалить по номеру",
        "fm_2": "Удалить несколько (1,3-5)",
        "fm_3": "Удалить все",
        "fm_4": "Переименовать файл",
        "fm_5": "Переместить в fix (если видео не открывается)",
        "fm_6": "Вернуть из fix",
        "fm_back": "Назад",
        "fm_delete_file": "Удалить файл",
        "fm_delete_all": "Удалить ВСЕ файлы?",
        "fm_deleted": "Удалено",
        "fm_numbers": "Номера для удаления",
        "fm_failed": "Не удалось удалить",
        "lang_title": "Выбор языка",
        "lang_ru": "Русский",
        "lang_en": "English",
        "lang_saved": "Язык сохранён",
        "video_ready": "Видео готово",
        "file": "Файл",
        "size": "Размер",
        "rename_prompt": "Переименовать файл?",
        "rename_new_name": "Новое имя (с расширением или без, Enter — отмена)",
        "renamed": "Переименовано в",
        "rename_exists": "Файл с таким именем уже существует",
        "rename_failed": "Не удалось переименовать",
        "rename_empty": "Пустое имя",
        "junk_cleaned": "Очищено временных файлов",
        "press_enter": "Enter — продолжить",
        "file_index": "Номер файла",
        "move_to_fix_prompt": "Если видео не открывается в Files, переместить в папку fix?",
        "moved_to_fix": "Перемещено в fix",
        "fix_empty": "Папка fix пуста",
        "fix_dir": "Папка fix",
        "move_failed": "Не удалось переместить",
        "compat_warning": "Формат может быть несовместим с iPhone (не H.264/AAC). Рекомендуется VLC или переместить в fix.",
    },
    "en": {
        "app_title": "Universal Video Downloader",
        "menu_download": "Download video",
        "menu_files": "File manager",
        "menu_language": "Change language",
        "menu_exit": "Exit (q)",
        "choice": "Choice",
        "invalid_choice": "Invalid choice",
        "videos_dir": "Videos saved to",
        "enter_urls": "Enter video URLs (one per line).",
        "enter_urls_hint": "Empty line to start download. 'q' to menu.",
        "available_formats": "Available video formats",
        "select_video": "Video format number (Enter = iPhone-compatible)",
        "available_audio": "Available audio tracks",
        "select_audio": "Audio number (Enter = best)",
        "with_audio": "with audio",
        "no_audio": "no audio",
        "invalid_default": "Invalid choice, using default format",
        "selector": "Selector",
        "finished": "Download finished",
        "trying_generic": "Trying generic extractor...",
        "retry_tls": "Retry without TLS verification?",
        "all_exhausted": "All attempts exhausted",
        "scanning": "Scanning page",
        "found_videos": "Videos found",
        "no_videos": "No videos found",
        "multiple_videos": "Multiple videos found",
        "number_or_all": "Number or 'all'",
        "invalid_url": "Invalid URL",
        "stopped": "Stopped",
        "fm_title": "File manager",
        "fm_path": "Directory",
        "fm_count": "Files",
        "fm_empty": "Directory is empty",
        "fm_1": "Delete by number",
        "fm_2": "Delete multiple (1,3-5)",
        "fm_3": "Delete all",
        "fm_4": "Rename file",
        "fm_5": "Move to fix (if video won't open)",
        "fm_6": "Restore from fix",
        "fm_back": "Back",
        "fm_delete_file": "Delete file",
        "fm_delete_all": "Delete ALL files?",
        "fm_deleted": "Deleted",
        "fm_numbers": "Numbers to delete",
        "fm_failed": "Failed to delete",
        "lang_title": "Language selection",
        "lang_ru": "Русский",
        "lang_en": "English",
        "lang_saved": "Language saved",
        "video_ready": "Video ready",
        "file": "File",
        "size": "Size",
        "rename_prompt": "Rename file?",
        "rename_new_name": "New name (with or without extension, Enter = cancel)",
        "renamed": "Renamed to",
        "rename_exists": "File with this name already exists",
        "rename_failed": "Failed to rename",
        "rename_empty": "Empty name",
        "junk_cleaned": "Cleaned temp files",
        "press_enter": "Enter — continue",
        "file_index": "File number",
        "move_to_fix_prompt": "If video won't open in Files, move to fix folder?",
        "moved_to_fix": "Moved to fix",
        "fix_empty": "fix folder is empty",
        "fix_dir": "fix folder",
        "move_failed": "Failed to move",
        "compat_warning": "Format may be incompatible with iPhone (not H.264/AAC). Use VLC or move to fix.",
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

YTDLP_BINARY = shutil.which("yt-dlp")
BASE_DIR = Path("/root/VideoDownloader")
VIDEOS_DIR = BASE_DIR / "videos"
FIX_DIR = BASE_DIR / "fix"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"

COMPAT_FORMAT = "bv*[vcodec^=avc1]+ba[ext=m4a]/b[ext=mp4]/bv*+ba/b"

RED, GREEN, YELLOW, BLUE, CYAN, NC = ("\033[0;31m", "\033[0;32m", "\033[1;33m",
                                      "\033[0;34m", "\033[0;36m", "\033[0m")
def c(t, col): return f"{col}{t}{NC}"

def trunc(s, n):
    s = str(s)
    return s if len(s) <= n else s[:n-3] + "..."

def header(title):
    line = "=" * 40
    print(c(line, YELLOW))
    print(c(f"  {title}", YELLOW))
    print(c(line, YELLOW))

def ensure_dir():
    global VIDEOS_DIR, FIX_DIR
    for d in (VIDEOS_DIR, FIX_DIR):
        d.mkdir(parents=True, exist_ok=True)
    return VIDEOS_DIR

def fmt_size(n):
    if n < 1024: return f"{n} B"
    if n < 1024 * 1024: return f"{n/1024:.1f} KiB"
    if n < 1024 * 1024 * 1024: return f"{n/1048576:.1f} MiB"
    return f"{n/1073741824:.2f} GiB"

def confirm(prompt):
    try:
        return input(c(prompt + " [y/N]: ", YELLOW)).strip().lower() in ("y", "yes", "д", "да")
    except (EOFError, KeyboardInterrupt):
        return False

def valid_url(u):
    try:
        p = urlparse(u)
        return p.scheme in ("http", "https") and bool(p.netloc)
    except (ValueError, TypeError):
        return False

def cleanup_junk():
    removed = []
    patterns = ["*.part", "*.ytdl", "*.temp.mp4", "*.temp.m4a", "*.temp.webm"]
    for pat in patterns:
        try:
            for f in VIDEOS_DIR.glob(pat):
                try:
                    if f.is_file():
                        f.unlink()
                        removed.append(f.name)
                except OSError:
                    pass
        except OSError:
            pass
    try:
        for f in VIDEOS_DIR.iterdir():
            if not f.is_file():
                continue
            stem = f.stem
            if re.search(r'\.f\d+$', stem) and f.suffix in (".mp4", ".m4a", ".webm"):
                try:
                    f.unlink()
                    removed.append(f.name)
                except OSError:
                    pass
    except OSError:
        pass
    if removed:
        print(c(f"[*] {T('junk_cleaned')}: {len(removed)}", YELLOW))
    return removed

def find_newest_mp4():
    try:
        files = [f for f in VIDEOS_DIR.glob("*.mp4") if f.is_file()]
    except OSError:
        return None
    if not files:
        return None
    try:
        return max(files, key=lambda p: p.stat().st_mtime)
    except OSError:
        return files[0]

def base_opts(**extra):
    o = {
        "quiet": True, "no_warnings": True, "noplaylist": True,
        "socket_timeout": 30, "retries": 5, "fragment_retries": 5,
        "source_address": "0.0.0.0",
        "http_headers": {"User-Agent": UA},
    }
    o.update(extra)
    return o

def first_entry(info):
    if isinstance(info, dict) and info.get("entries") is not None:
        return next((e for e in info["entries"] if isinstance(e, dict) and e.get("formats")), None)
    return info

def get_video_info(url, **extra):
    if yt_dlp is not None:
        try:
            with yt_dlp.YoutubeDL(base_opts(**extra)) as ydl:
                return first_entry(ydl.extract_info(url, download=False))
        except Exception as e:
            print(c(f"[!] info: {trunc(str(e), 60)}", YELLOW))
    return None

def select_format(url):
    default = COMPAT_FORMAT
    info = get_video_info(url)
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
        size_t = f", {size/1048576:.0f}M" if isinstance(size, (int, float)) else ""
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
        print(c(f"[!] {T('invalid_default')}", YELLOW))
        return default

    vid = str(sel["format_id"])
    if sel.get("acodec") not in (None, "none"):
        return vid
    if not audios:
        return f"{vid}+ba/b"
    print(c(f"\n{T('available_audio')}:", CYAN))
    for i, f in enumerate(audios, 1):
        abr = f.get("abr")
        abr_t = f", {abr:g}kbps" if isinstance(abr, (int, float)) else ""
        print(f"  {i}. {trunc(f.get('language') or 'unknown', 15)}, {f.get('ext') or '?'}{abr_t}")
    try:
        a = input(c(f"{T('select_audio')}: ", YELLOW)).strip()
        if not a:
            return f"{vid}+ba/b"
        return f"{vid}+{audios[int(a)-1]['format_id']}"
    except (ValueError, IndexError, EOFError, KeyboardInterrupt):
        return f"{vid}+ba/b"

def progress_hook():
    if tqdm is None:
        return None
    state = {"bar": None}
    def hook(d):
        st = d.get("status")
        if st == "downloading":
            total = d.get("total_bytes") or d.get("total_bytes_estimate")
            if state["bar"] is None:
                state["bar"] = tqdm(total=total, unit="B", unit_scale=True,
                                    leave=False, ncols=42, desc="dl")
            elif total:
                state["bar"].total = total
            dl = d.get("downloaded_bytes") or 0
            state["bar"].update(max(0, dl - state["bar"].n))
        elif st in ("finished", "error"):
            if state["bar"]:
                state["bar"].close()
                state["bar"] = None
                sys.stdout.write("\n")
                sys.stdout.flush()
    return hook

OUT_TMPL = "%(title).150B [%(id)s].%(ext)s"

def run_module(url, selector, **extra):
    if yt_dlp is None:
        return False
    opts = base_opts(format=selector, outtmpl=str(VIDEOS_DIR / OUT_TMPL),
                     merge_output_format="mp4", continuedl=True, overwrites=False, **extra)
    h = progress_hook()
    if h:
        opts["progress_hooks"] = [h]
    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            return ydl.download([url]) in (None, 0)
    except Exception as e:
        print(c(f"[!] yt-dlp: {trunc(str(e), 70)}", RED))
        return False

def run_binary(url, selector, *flags):
    if not YTDLP_BINARY:
        return False
    cmd = [YTDLP_BINARY, "-f", selector, "--merge-output-format", "mp4", "--force-ipv4",
           "--quiet", "--no-progress",
           "-o", str(VIDEOS_DIR / OUT_TMPL), "--no-warnings", "--no-playlist", *flags, url]
    try:
        result = subprocess.run(cmd, timeout=3600, capture_output=True, text=True)
        if result.returncode != 0 and result.stderr:
            for line in result.stderr.strip().split("\n")[:2]:
                if line.strip():
                    print(c(f"[!] {trunc(line, 70)}", RED))
        return result.returncode == 0
    except Exception as e:
        print(c(f"[!] binary: {trunc(str(e), 70)}", RED))
        return False

def http_json(url, referer="https://rutube.ru/"):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Referer": referer, "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode("utf-8", "replace"))

def rutube_download(url):
    m = re.search(r"rutube\.ru/(?:video|play/embed|video/private)/([0-9a-f]{32})", url)
    if not m:
        return False
    vid = m.group(1)
    p = re.search(r"[?&]p=([\w-]+)", url)
    private = f"&p={p.group(1)}" if p else ""
    print(c("[*] RuTube: API...", BLUE))

    title = vid
    try:
        meta = http_json(f"https://rutube.ru/api/video/{vid}/?format=json")
        title = meta.get("title") or vid
    except Exception:
        pass
    title = re.sub(r'[\\/:*?"<>|%\n\r]+', "_", title).strip()[:150] or vid

    m3u8 = None
    variants = [
        f"https://rutube.ru/api/play/options/{vid}/?no_404=true&referer=https%3A%2F%2Frutube.ru&pver=v2&client=wdp{private}",
        f"https://rutube.ru/api/play/options/{vid}/?no_404=true&referer=https%3A%2F%2Frutube.ru&pver=v2{private}",
        f"https://rutube.ru/api/play/options/{vid}/?no_404=true&referer=https%3A%2F%2Frutube.ru{private}",
        f"https://rutube.ru/api/play/options/{vid}/?format=json{private}",
        f"https://rutube.ru/api/play/options/{vid}/?no_404=true&referer=https%3A%2F%2Frutube.ru%2Fplay%2Fembed%2F{vid}&pver=v2",
    ]
    for u in variants:
        try:
            data = http_json(u)
            vb = data.get("video_balancer") or {}
            m3u8 = (vb.get("m3u8") or vb.get("default")) if isinstance(vb, dict) else None
            if m3u8:
                break
        except Exception:
            pass
    if not m3u8:
        print(c("[!] RuTube: no m3u8", YELLOW))
        return False

    print(c("[*] RuTube: HLS...", BLUE))
    hdrs = {"User-Agent": UA, "Referer": "https://rutube.ru/", "Origin": "https://rutube.ru"}
    out = VIDEOS_DIR / f"{title} [{vid}].mp4"
    if yt_dlp is not None:
        for sel in (COMPAT_FORMAT, "bv*+ba/b"):
            opts = base_opts(format=sel, outtmpl=str(VIDEOS_DIR / f"{title} [{vid}].%(ext)s"),
                             merge_output_format="mp4", http_headers=hdrs, continuedl=True)
            h = progress_hook()
            if h:
                opts["progress_hooks"] = [h]
            try:
                with yt_dlp.YoutubeDL(opts) as ydl:
                    if ydl.download([m3u8]) in (None, 0):
                        return True
            except Exception:
                pass
    if shutil.which("ffmpeg"):
        print(c("[*] RuTube: ffmpeg", BLUE))
        hs = "".join(f"{k}: {v}\r\n" for k, v in hdrs.items())
        cmd = ["ffmpeg", "-y", "-headers", hs, "-i", m3u8, "-c", "copy", "-bsf:a", "aac_adtstoasc", str(out)]
        try:
            if subprocess.run(cmd, timeout=7200, capture_output=True).returncode == 0 \
               and out.exists() and out.stat().st_size > 0:
                return True
        except Exception:
            pass
    return False

def check_compat(filepath):
    if not filepath or not filepath.exists():
        return False
    if not shutil.which("ffprobe"):
        return True
    try:
        r = subprocess.run(
            ["ffprobe", "-v", "error", "-select_streams", "v:0",
             "-show_entries", "stream=codec_name", "-of", "default=nw=1:nk=1",
             str(filepath)],
            capture_output=True, text=True, timeout=30
        )
        vcodec = r.stdout.strip().lower()
        if vcodec and vcodec not in ("h264", "avc1"):
            return False
    except Exception:
        pass
    return True

def attempt_download(url):
    if not valid_url(url):
        print(c(f"[!] {T('invalid_url')}: {trunc(url, 40)}", RED))
        return False, None

    before = {}
    try:
        for f in VIDEOS_DIR.glob("*.mp4"):
            try:
                before[f.name] = f.stat().st_mtime
            except OSError:
                pass
    except OSError:
        pass

    selector = select_format(url)
    print(c(f"[*] {T('selector')}: {trunc(selector, 35)}", BLUE))

    success = False
    if run_module(url, selector) or run_binary(url, selector):
        success = True
    elif "rutube.ru" in url and rutube_download(url):
        success = True
    else:
        print(c(f"[!] {T('trying_generic')}", YELLOW))
        if run_module(url, COMPAT_FORMAT, force_generic_extractor=True) or \
           run_binary(url, COMPAT_FORMAT, "--force-generic-extractor"):
            success = True
        elif confirm(T("retry_tls")):
            if run_module(url, COMPAT_FORMAT, nocheckcertificate=True) or \
               run_binary(url, COMPAT_FORMAT, "--no-check-certificate"):
                success = True

    if not success:
        print(c(f"[!] {T('all_exhausted')}", RED))
        return False, None

    cleanup_junk()

    newest_file = None
    newest_mtime = 0
    try:
        for f in VIDEOS_DIR.glob("*.mp4"):
            try:
                mt = f.stat().st_mtime
                if mt > before.get(f.name, 0) and mt > newest_mtime:
                    newest_mtime = mt
                    newest_file = f
            except OSError:
                pass
    except OSError:
        pass

    if newest_file is None:
        newest_file = find_newest_mp4()

    if newest_file and not check_compat(newest_file):
        print(c(f"[!] {T('compat_warning')}", YELLOW))

    return True, newest_file

def move_to_fix(filepath):
    if not filepath or not filepath.exists():
        return False
    try:
        dest = FIX_DIR / filepath.name
        if dest.exists():
            stem = filepath.stem
            suffix = filepath.suffix
            counter = 1
            while dest.exists():
                dest = FIX_DIR / f"{stem}_{counter}{suffix}"
                counter += 1
        filepath.rename(dest)
        print(c(f"[+] {T('moved_to_fix')}: {trunc(dest.name, 34)}", GREEN))
        return True
    except OSError as e:
        print(c(f"[!] {T('move_failed')}: {trunc(str(e), 50)}", RED))
        return False

def show_ready_and_rename(filepath):
    if not filepath or not filepath.exists():
        return filepath
    try:
        size = filepath.stat().st_size
    except OSError:
        size = 0
    print()
    print(c("=" * 40, GREEN))
    print(c(f"  {T('video_ready')}", GREEN))
    print(c("=" * 40, GREEN))
    print(c(f"  {T('file')}: {trunc(filepath.name, 34)}", CYAN))
    print(c(f"  {T('size')}: {fmt_size(size)}", CYAN))
    print()
    try:
        do_rename = confirm(T("rename_prompt"))
    except (EOFError, KeyboardInterrupt):
        return filepath
    if do_rename:
        try:
            new_name = input(c(f"{T('rename_new_name')}: ", YELLOW)).strip()
        except (EOFError, KeyboardInterrupt):
            new_name = ""
        if new_name:
            if not new_name.endswith(filepath.suffix):
                new_name += filepath.suffix
            new_name = re.sub(r'[\\/:*?"<>|]', "_", new_name)
            new_path = filepath.parent / new_name
            if new_path.exists() and new_path != filepath:
                print(c(f"[!] {T('rename_exists')}", RED))
            else:
                try:
                    filepath.rename(new_path)
                    print(c(f"[+] {T('renamed')}: {trunc(new_name, 34)}", GREEN))
                    filepath = new_path
                except OSError as e:
                    print(c(f"[!] {T('rename_failed')}: {trunc(str(e), 50)}", RED))

    if confirm(T("move_to_fix_prompt")):
        move_to_fix(filepath)
    return filepath

def find_videos_on_page(page_url):
    print(c(f"\n[*] {T('scanning')}: {trunc(page_url, 40)}", BLUE))
    if yt_dlp is None:
        return []
    try:
        with yt_dlp.YoutubeDL(base_opts(extract_flat=True, noplaylist=False)) as ydl:
            info = ydl.extract_info(page_url, download=False)
    except Exception as e:
        print(c(f"[!] scan: {trunc(str(e), 60)}", YELLOW))
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
        print(c(f"[+] {T('found_videos')}: {len(urls)}", GREEN))
        return urls
    u = info.get("webpage_url") or info.get("original_url") or info.get("url")
    return [u] if isinstance(u, str) and valid_url(u) else []

DIRECT = ("youtube.com/", "youtu.be/", "rutube.ru/video/", "rutube.ru/play/", ".mp4", ".m3u8")

def process_links(links):
    for url in links:
        if not valid_url(url):
            print(c(f"[!] {T('invalid_url')}: {trunc(url, 40)}", RED))
            continue
        if not any(m in url.lower() for m in DIRECT):
            found = find_videos_on_page(url)
            if not found:
                print(c(f"[!] {T('no_videos')}: {trunc(url, 40)}", YELLOW))
                continue
            if len(found) == 1:
                ok, fp = attempt_download(found[0])
                if ok and fp:
                    show_ready_and_rename(fp)
                continue
            print(c(f"\n{T('multiple_videos')}:", CYAN))
            for i, u in enumerate(found, 1):
                print(f"  {i}. {trunc(u, 38)}")
            try:
                ch = input(c(f"{T('number_or_all')}: ", YELLOW)).strip().lower()
                if ch == "all":
                    for u in found:
                        ok, fp = attempt_download(u)
                        if ok and fp:
                            show_ready_and_rename(fp)
                else:
                    ok, fp = attempt_download(found[int(ch) - 1])
                    if ok and fp:
                        show_ready_and_rename(fp)
            except (ValueError, IndexError, EOFError, KeyboardInterrupt):
                print(c(f"[!] {T('invalid_choice')}", RED))
        else:
            ok, fp = attempt_download(url)
            if ok and fp:
                show_ready_and_rename(fp)

def list_video_files():
    try:
        files = sorted(VIDEOS_DIR.iterdir(), key=lambda p: p.name.lower())
    except OSError:
        return []
    return [f for f in files if f.is_file() and not f.name.startswith(".")]

def parse_numbers(text, max_index):
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
            if a > b: a, b = b, a
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

def file_manager():
    ensure_dir()
    while True:
        files = list_video_files()
        header(T("fm_title"))
        print(c(f"{T('fm_path')}: {trunc(str(VIDEOS_DIR), 34)}", CYAN))
        print(c(f"{T('fm_count')}: {len(files)}", CYAN))
        print("-" * 40)
        if not files:
            print(c(f"[!] {T('fm_empty')}", YELLOW))
        else:
            for i, f in enumerate(files, 1):
                try:
                    size = f.stat().st_size
                except OSError:
                    size = 0
                print(f"  {i}. {trunc(f.name, 28)} ({fmt_size(size)})")
        print("-" * 40)
        print(f"  1. {T('fm_1')}")
        print(f"  2. {T('fm_2')}")
        print(f"  3. {T('fm_3')}")
        print(f"  4. {T('fm_4')}")
        print(f"  5. {T('fm_5')}")
        print(f"  6. {T('fm_6')}")
        print(f"  0. {T('fm_back')}")
        try:
            ch = input(c(f"{T('choice')}: ", GREEN)).strip().lower()
        except (EOFError, KeyboardInterrupt):
            return
        if ch in ("0", "q", "back", "назад"):
            return
        if ch not in ("1", "2", "3", "4", "5", "6"):
            print(c(f"[!] {T('invalid_choice')}", RED))
            continue
        if not files and ch not in ("6",):
            continue
        if ch == "1":
            try:
                idx = input(c(f"{T('fm_numbers')} (1-{len(files)}): ", YELLOW)).strip()
                nums = parse_numbers(idx, len(files))
            except (ValueError, EOFError, KeyboardInterrupt):
                print(c(f"[!] {T('invalid_choice')}", RED))
                continue
            target = files[nums[0] - 1]
            if confirm(f"{T('fm_delete_file')} '{trunc(target.name, 25)}'?"):
                try:
                    target.unlink()
                    print(c(f"[+] {T('fm_deleted')}: {trunc(target.name, 34)}", GREEN))
                except OSError as e:
                    print(c(f"[!] {T('fm_failed')}: {trunc(str(e), 50)}", RED))
        elif ch == "2":
            try:
                idx = input(c(f"{T('fm_numbers')} (1,3-5): ", YELLOW)).strip()
                nums = parse_numbers(idx, len(files))
            except (ValueError, EOFError, KeyboardInterrupt):
                print(c(f"[!] {T('invalid_choice')}", RED))
                continue
            if confirm(f"{T('fm_delete_file')} {len(nums)}?"):
                count = 0
                for n in sorted(nums, reverse=True):
                    try:
                        files[n - 1].unlink()
                        count += 1
                    except OSError as e:
                        print(c(f"[!] {T('fm_failed')}: {trunc(str(e), 50)}", RED))
                print(c(f"[+] {T('fm_deleted')}: {count}", GREEN))
        elif ch == "3":
            if confirm(f"{T('fm_delete_all')} ({len(files)})?"):
                count = 0
                for f in files:
                    try:
                        f.unlink()
                        count += 1
                    except OSError as e:
                        print(c(f"[!] {T('fm_failed')}: {trunc(str(e), 50)}", RED))
                print(c(f"[+] {T('fm_deleted')}: {count}", GREEN))
        elif ch == "4":
            try:
                idx = input(c(f"{T('file_index')} (1-{len(files)}): ", YELLOW)).strip()
                nums = parse_numbers(idx, len(files))
            except (ValueError, EOFError, KeyboardInterrupt):
                print(c(f"[!] {T('invalid_choice')}", RED))
                continue
            target = files[nums[0] - 1]
            try:
                new_name = input(c(f"{T('rename_new_name')}: ", YELLOW)).strip()
            except (EOFError, KeyboardInterrupt):
                continue
            if not new_name:
                continue
            if not new_name.endswith(target.suffix):
                new_name += target.suffix
            new_name = re.sub(r'[\\/:*?"<>|]', "_", new_name)
            new_path = target.parent / new_name
            if new_path.exists() and new_path != target:
                print(c(f"[!] {T('rename_exists')}", RED))
                continue
            try:
                target.rename(new_path)
                print(c(f"[+] {T('renamed')}: {trunc(new_name, 34)}", GREEN))
            except OSError as e:
                print(c(f"[!] {T('rename_failed')}: {trunc(str(e), 50)}", RED))
        elif ch == "5":
            try:
                idx = input(c(f"{T('file_index')} (1-{len(files)}): ", YELLOW)).strip()
                nums = parse_numbers(idx, len(files))
            except (ValueError, EOFError, KeyboardInterrupt):
                print(c(f"[!] {T('invalid_choice')}", RED))
                continue
            move_to_fix(files[nums[0] - 1])
        elif ch == "6":
            try:
                fix_files = sorted(FIX_DIR.iterdir(), key=lambda p: p.name.lower())
            except OSError:
                fix_files = []
            fix_files = [f for f in fix_files if f.is_file() and not f.name.startswith(".")]
            if not fix_files:
                print(c(f"[!] {T('fix_empty')}", YELLOW))
                continue
            header(T("fix_dir"))
            for i, f in enumerate(fix_files, 1):
                try:
                    size = f.stat().st_size
                except OSError:
                    size = 0
                print(f"  {i}. {trunc(f.name, 28)} ({fmt_size(size)})")
            try:
                idx = input(c(f"{T('file_index')} (1-{len(fix_files)}): ", YELLOW)).strip()
                nums = parse_numbers(idx, len(fix_files))
            except (ValueError, EOFError, KeyboardInterrupt):
                print(c(f"[!] {T('invalid_choice')}", RED))
                continue
            target = fix_files[nums[0] - 1]
            try:
                target.rename(VIDEOS_DIR / target.name)
                print(c(f"[+] {T('renamed')}: {trunc(target.name, 34)}", GREEN))
            except OSError as e:
                print(c(f"[!] {T('move_failed')}: {trunc(str(e), 50)}", RED))

def language_menu():
    while True:
        header(T("lang_title"))
        print(f"  1. {T('lang_ru')}")
        print(f"  2. {T('lang_en')}")
        print(f"  0. {T('fm_back')}")
        try:
            ch = input(c(f"{T('choice')}: ", GREEN)).strip().lower()
        except (EOFError, KeyboardInterrupt):
            return
        if ch in ("0", "q"):
            return
        if ch == "1":
            save_lang("ru")
            print(c(f"[+] {T('lang_saved')}: {T('lang_ru')}", GREEN))
            return
        if ch == "2":
            save_lang("en")
            print(c(f"[+] {T('lang_saved')}: {T('lang_en')}", GREEN))
            return

def main_menu():
    ensure_dir()
    while True:
        cleanup_junk()
        header(T("app_title"))
        print(c(f"{T('videos_dir')}: {trunc(str(VIDEOS_DIR), 34)}", CYAN))
        print("-" * 40)
        print(f"  1. {T('menu_download')}")
        print(f"  2. {T('menu_files')}")
        print(f"  3. {T('menu_language')}")
        print(f"  0. {T('menu_exit')}")
        try:
            ch = input(c(f"{T('choice')}: ", GREEN)).strip().lower()
        except (EOFError, KeyboardInterrupt):
            print(c(f"\n[+] {T('stopped')}", GREEN))
            break
        if ch in ("0", "q", "quit", "exit"):
            print(c(f"[+] {T('menu_exit')}", GREEN))
            break
        if ch == "2":
            file_manager()
            continue
        if ch == "3":
            language_menu()
            continue
        if ch != "1":
            print(c(f"[!] {T('invalid_choice')}", RED))
            continue
        links = []
        print(c(f"\n[*] {T('enter_urls')}", YELLOW))
        print(c(f"[*] {T('enter_urls_hint')}", YELLOW))
        while True:
            try:
                line = input(c("> ", GREEN)).strip()
            except (EOFError, KeyboardInterrupt):
                break
            if not line or line.lower() == "q":
                break
            links.append(line)
        if links:
            process_links(links)
            print()

if __name__ == "__main__":
    try:
        main_menu()
    except KeyboardInterrupt:
        print(c(f"\n[+] {T('stopped')}", GREEN))
PYEOF

chmod 700 /tmp/video_downloader.py
command -v python3 >/dev/null 2>&1 || { say "${RED}$(T no_python)${NC}"; exit 1; }
exec python3 /tmp/video_downloader.py
