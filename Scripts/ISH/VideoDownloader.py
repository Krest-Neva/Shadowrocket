#!/bin/sh

set -u

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

say() { printf '%b\n' "$1"; }

setup_dns() {
    say "${BLUE}[*] Настройка DNS для iSH (musl)...${NC}"
    cat > /etc/resolv.conf << 'EOF'
nameserver 1.1.1.1
nameserver 8.8.8.8
nameserver 94.140.14.14
options single-request-reopen
EOF
    say "${GREEN}[+] DNS настроен.${NC}"
}

install_packages() {
    say "${BLUE}[*] Обновление индексов Alpine...${NC}"
    apk update || { say "${RED}[!] apk update не удался.${NC}"; return 1; }

    say "${BLUE}[*] Установка системных зависимостей...${NC}"
    apk add --no-cache python3 py3-pip ffmpeg ca-certificates openssl py3-pycryptodome || {
        say "${RED}[!] Не удалось установить системные пакеты.${NC}"
        return 1
    }

    VENV_DIR="/opt/video-downloader-venv"
    say "${BLUE}[*] Создание/обновление venv...${NC}"
    python3 -m venv "$VENV_DIR" || { say "${RED}[!] Не удалось создать venv.${NC}"; return 1; }
    VENV_PY="$VENV_DIR/bin/python"

    "$VENV_PY" -m pip install --upgrade pip setuptools wheel || {
        say "${RED}[!] Не удалось обновить pip.${NC}"; return 1
    }

    if "$VENV_PY" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)'; then
        say "${BLUE}[*] Установка yt-dlp из master (самая свежая версия)...${NC}"
        "$VENV_PY" -m pip install --force-reinstall --upgrade \
            "yt-dlp[default] @ https://github.com/yt-dlp/yt-dlp/archive/master.tar.gz" tqdm || {
            say "${RED}[!] Не удалось установить yt-dlp из master.${NC}"
            return 1
        }
    else
        say "${YELLOW}[!] Python < 3.10. Устанавливаем последнюю совместимую версию yt-dlp (2025.09.26)...${NC}"
        "$VENV_PY" -m pip install --force-reinstall --upgrade \
            "yt-dlp[default]==2025.09.26" tqdm || {
            say "${RED}[!] Не удалось установить yt-dlp.${NC}"
            return 1
        }
    fi

    say "${GREEN}[+] Все зависимости установлены.${NC}"
}

say "${YELLOW}========================================${NC}"
say "${YELLOW}  Универсальный загрузчик видео${NC}"
say "${YELLOW}========================================${NC}"

printf 'Настроить DNS и установить/обновить зависимости? [y/N]: '
IFS= read -r ANSWER || ANSWER='n'

case "$ANSWER" in
    y|Y|yes|YES|Yes|д|Д|да|Да|ДА)
        setup_dns
        if ! install_packages; then
            say "${RED}[!] Установка не завершена. Скрипт продолжит работу, но могут быть ошибки.${NC}"
        fi
        ;;
    *)
        say "${BLUE}[*] Пропускаем установку. Настраиваем DNS на всякий случай...${NC}"
        setup_dns
        ;;
esac

if [ -x /opt/video-downloader-venv/bin/python ]; then
    PYTHON_BIN="/opt/video-downloader-venv/bin/python"
else
    PYTHON_BIN="python3"
fi

if ! "$PYTHON_BIN" -c 'import yt_dlp, tqdm' >/dev/null 2>&1; then
    say "${RED}[!] yt-dlp или tqdm не найдены в $PYTHON_BIN.${NC}"
    say "${YELLOW}[*] Перезапустите скрипт и подтвердите установку зависимостей.${NC}"
    exit 1
fi

cat > /tmp/video_downloader.py << 'PYEOF'
import sys
import subprocess
import shutil
import time
from pathlib import Path
from urllib.parse import urlparse

try:
    import yt_dlp
    from tqdm import tqdm
except ImportError:
    print("\033[0;31m[!] Не установлены yt-dlp или tqdm.\033[0m")
    sys.exit(1)

VIDEOS_DIR = Path("/root/videos")
FALLBACK_DIR = Path.home() / "videos"

RED = "\033[0;31m"
GREEN = "\033[0;32m"
YELLOW = "\033[1;33m"
BLUE = "\033[0;34m"
CYAN = "\033[0;36m"
NC = "\033[0m"


def c(text, color):
    return f"{color}{text}{NC}"


def ensure_dir():
    global VIDEOS_DIR
    for directory in (VIDEOS_DIR, FALLBACK_DIR):
        try:
            directory.mkdir(parents=True, exist_ok=True)
            test = directory / ".write_test"
            test.touch()
            test.unlink()
            VIDEOS_DIR = directory
            return
        except OSError:
            continue
    raise OSError("Не удалось найти доступную папку для сохранения видео.")


def confirm_action(prompt):
    try:
        answer = input(c(prompt + " [y/N]: ", YELLOW)).strip().lower()
        return answer in ("y", "yes", "да", "д")
    except (EOFError, KeyboardInterrupt):
        return False


def valid_url(url):
    try:
        parsed = urlparse(url)
        return parsed.scheme in ("http", "https") and bool(parsed.netloc)
    except (ValueError, TypeError):
        return False


def get_video_info(url, extra_opts=None):
    options = {
        "quiet": True,
        "no_warnings": True,
        "noplaylist": True,
        "socket_timeout": 30,
        "ignoreerrors": False,
        "retries": 3,
        "fragment_retries": 3,
    }
    if extra_opts:
        options.update(extra_opts)

    try:
        with yt_dlp.YoutubeDL(options) as ydl:
            info = ydl.extract_info(url, download=False)
        if not isinstance(info, dict):
            return None
        entries = info.get("entries")
        if entries is not None:
            return next((e for e in entries if isinstance(e, dict) and e.get("formats")), None)
        return info
    except Exception as exc:
        print(c(f"[!] Не удалось получить информацию: {type(exc).__name__}: {exc}", YELLOW))
        return None


def select_format(url):
    default_selector = "bv*+ba/b"
    info = get_video_info(url)
    if not isinstance(info, dict):
        return default_selector

    formats = info.get("formats", [])
    if not isinstance(formats, list):
        return default_selector

    videos = [f for f in formats if isinstance(f, dict) and f.get("format_id") and f.get("vcodec") not in (None, "none")]
    audios = [f for f in formats if isinstance(f, dict) and f.get("format_id") and f.get("vcodec") == "none" and f.get("acodec") not in (None, "none")]

    if not videos:
        print(c("[*] Список форматов недоступен. Будет выбран лучший вариант.", YELLOW))
        return default_selector

    unique = {}
    for f in videos:
        key = (f.get("height"), f.get("ext"), f.get("fps"), f.get("vcodec"), f.get("acodec"))
        unique[key] = f
    vlist = sorted(unique.values(), key=lambda x: (x.get("height") or 0, x.get("fps") or 0))

    print(c("\nДоступные форматы видео:", CYAN))
    for i, f in enumerate(vlist, 1):
        h = f.get("height") or "?"
        ext = f.get("ext") or "?"
        fps = f.get("fps")
        size = f.get("filesize") or f.get("filesize_approx")
        size_txt = f", {size / (1024*1024):.1f} MiB" if isinstance(size, (int, float)) else ""
        fps_txt = f", {fps} fps" if fps else ""
        audio_txt = "со звуком" if f.get("acodec") not in (None, "none") else "без звука"
        print(f"  {i}. {h}p ({ext}, {audio_txt}{fps_txt}{size_txt})")

    try:
        choice = input(c("\nВыберите номер видеоформата (Enter — лучший): ", YELLOW)).strip()
    except (EOFError, KeyboardInterrupt):
        return default_selector
    if not choice:
        return default_selector

    try:
        sel = vlist[int(choice) - 1]
    except (ValueError, IndexError):
        print(c("[!] Неверный выбор. Используется лучший формат.", YELLOW))
        return default_selector

    vid = str(sel["format_id"])
    if sel.get("acodec") not in (None, "none"):
        return vid

    if not audios:
        return default_selector

    print(c("\nДоступные аудиодорожки:", CYAN))
    for i, f in enumerate(audios, 1):
        lang = f.get("language") or "не указан"
        ext = f.get("ext") or "?"
        abr = f.get("abr")
        abr_txt = f", {abr:g} kbps" if isinstance(abr, (int, float)) else ""
        print(f"  {i}. Язык: {lang}, {ext}{abr_txt}")

    try:
        aid = input(c("Выберите номер аудио (Enter — лучшее): ", YELLOW)).strip()
    except (EOFError, KeyboardInterrupt):
        return f"{vid}+bestaudio/best"
    if not aid:
        return f"{vid}+bestaudio/best"

    try:
        audio = audios[int(aid) - 1]
        return f"{vid}+{audio['format_id']}"
    except (ValueError, IndexError, KeyError):
        return f"{vid}+bestaudio/best"


def create_progress_hook(desc):
    pbar = None
    def hook(d):
        nonlocal pbar
        status = d.get("status")
        if status == "downloading":
            total = d.get("total_bytes") or d.get("total_bytes_estimate")
            if pbar is None:
                pbar = tqdm(total=total, unit="B", unit_scale=True, desc=desc, leave=False)
            elif total and pbar.total != total:
                pbar.total = total
            downloaded = d.get("downloaded_bytes", 0)
            if isinstance(downloaded, (int, float)):
                pbar.update(max(0, downloaded - pbar.n))
            pbar.refresh()
        elif status == "finished":
            if pbar:
                if pbar.total and pbar.n < pbar.total:
                    pbar.update(pbar.total - pbar.n)
                pbar.close()
                pbar = None
            print(c(f"[+] Загрузка завершена: {d.get('filename', '')}", GREEN))
        elif status == "error":
            if pbar:
                pbar.close()
                pbar = None
    return hook


def try_ytdlp(url, selector):
    options = {
        "format": selector,
        "outtmpl": str(VIDEOS_DIR / "%(title).180B [%(id)s].%(ext)s"),
        "merge_output_format": "mp4",
        "progress_hooks": [create_progress_hook("Загрузка")],
        "quiet": True,
        "no_warnings": True,
        "noplaylist": True,
        "socket_timeout": 30,
        "retries": 5,
        "fragment_retries": 5,
        "file_access_retries": 3,
        "continuedl": True,
        "overwrites": False,
        "nocheckcertificate": False,
    }
    try:
        with yt_dlp.YoutubeDL(options) as ydl:
            result = ydl.download([url])
        if result not in (None, 0):
            print(c(f"[!] yt-dlp завершился с кодом {result}.", RED))
            return False
        return True
    except Exception as exc:
        print(c(f"[!] Ошибка yt-dlp: {type(exc).__name__}: {exc}", RED))
        return False


def try_external(url):
    info = get_video_info(url, {"nocheckcertificate": True})
    if not info:
        return False

    direct = info.get("url")
    if not direct:
        formats = info.get("formats", [])
        best = None
        best_h = -1
        for f in formats:
            if isinstance(f, dict) and f.get("url"):
                h = f.get("height") or 0
                if h > best_h:
                    best_h = h
                    best = f
        if best:
            direct = best["url"]

    if not direct:
        return False

    ext = info.get("ext", "mp4")
    title = info.get("title", "video").replace("/", "_").replace("\\", "_")
    out = VIDEOS_DIR / f"{title}.{ext}"

    for tool, cmd in (
        ("curl", ["curl", "-L", "-k", "--connect-timeout", "30", "-o", str(out), direct]),
        ("wget", ["wget", "--no-check-certificate", "-O", str(out), direct]),
        ("aria2c", ["aria2c", "--check-certificate=false", "-d", str(VIDEOS_DIR), "-o", out.name, direct]),
    ):
        if not shutil.which(tool):
            continue
        print(c(f"[*] Fallback: {tool}...", BLUE))
        try:
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
            if res.returncode == 0 and out.exists() and out.stat().st_size > 0:
                print(c(f"[+] Скачано через {tool}: {out}", GREEN))
                return True
        except Exception:
            pass
    return False


def attempt_download(url):
    if not valid_url(url):
        print(c(f"[!] Некорректная ссылка: {url}", RED))
        return False

    selector = select_format(url)
    print(c(f"[*] Формат: {selector}", BLUE))

    if try_ytdlp(url, selector):
        return True

    print(c("[!] yt-dlp не справился. Пробуем fallback (curl/wget)...", YELLOW))
    if try_external(url):
        return True

    if confirm_action("Разрешить повторную попытку без проверки TLS?"):
        print(c("[*] Повтор без проверки TLS...", BLUE))
        opts = {
            "format": selector,
            "outtmpl": str(VIDEOS_DIR / "%(title).180B [%(id)s].%(ext)s"),
            "merge_output_format": "mp4",
            "quiet": True,
            "no_warnings": True,
            "noplaylist": True,
            "nocheckcertificate": True,
            "retries": 5,
        }
        try:
            with yt_dlp.YoutubeDL(opts) as ydl:
                ydl.download([url])
            return True
        except Exception as exc:
            print(c(f"[!] Ошибка: {exc}", RED))

    print(c("[!] Все попытки исчерпаны.", RED))
    return False


def find_videos_on_page(page_url):
    print(c(f"\n[*] Поиск видео на странице: {page_url}", BLUE))
    options = {
        "quiet": True,
        "no_warnings": True,
        "extract_flat": True,
        "socket_timeout": 30,
        "noplaylist": False,
    }
    try:
        with yt_dlp.YoutubeDL(options) as ydl:
            info = ydl.extract_info(page_url, download=False)
        if not isinstance(info, dict):
            return []
        entries = info.get("entries")
        if entries is not None:
            urls = []
            for e in entries:
                if not isinstance(e, dict):
                    continue
                u = e.get("webpage_url") or e.get("url")
                if isinstance(u, str) and u.startswith(("http://", "https://")):
                    urls.append(u)
                elif e.get("ie_key") in ("Youtube", "YoutubeTab") and e.get("id"):
                    urls.append(f"https://www.youtube.com/watch?v={e['id']}")
            urls = list(dict.fromkeys(urls))
            print(c(f"[+] Найдено видео: {len(urls)}", GREEN))
            return urls
        u = info.get("webpage_url") or info.get("original_url") or info.get("url")
        if isinstance(u, str) and valid_url(u):
            return [u]
    except Exception as exc:
        print(c(f"[!] Ошибка поиска: {exc}", YELLOW))
    return []


def process_links(links):
    markers = ("youtube.com/", "youtu.be/", "rutube.ru/", ".mp4", ".m3u8")
    for url in links:
        if url.lower() == "q":
            return
        if not valid_url(url):
            print(c(f"[!] Некорректная ссылка: {url}", RED))
            continue
        if not any(m in url.lower() for m in markers):
            found = find_videos_on_page(url)
            if not found:
                print(c(f"[!] Видео не найдены: {url}", YELLOW))
                continue
            if len(found) == 1:
                attempt_download(found[0])
                continue
            print(c("\nНайдено несколько видео:", CYAN))
            for i, u in enumerate(found, 1):
                print(f"  {i}. {u}")
            try:
                ch = input(c("Номер или 'all': ", YELLOW)).strip().lower()
                if ch == "all":
                    for u in found:
                        attempt_download(u)
                else:
                    idx = int(ch) - 1
                    if 0 <= idx < len(found):
                        attempt_download(found[idx])
                    else:
                        print(c("[!] Не сверный номер.", RED))
            except (ValueError, EOFError, KeyboardInterrupt):
                print(c("[!] Неверный выбор.", RED))
        else:
            attempt_download(url)


def main_menu():
    try:
        ensure_dir()
    except OSError as exc:
        print(c(f"[!] Ошибка папки: {exc}", RED))
        return
    print(c(f"[*] Видео сохраняются в: {VIDEOS_DIR}", CYAN))

    while True:
        print(c("\n" + "=" * 40, YELLOW))
        print(c("  Главное меню", YELLOW))
        print(c("=" * 40, YELLOW))
        print("  1. Скачать видео")
        print("  2. Выход (q)")
        try:
            ch = input(c("Ваш выбор: ", GREEN)).strip().lower()
        except (EOFError, KeyboardInterrupt):
            print(c("\n[+] Выход.", GREEN))
            break
        if ch in ("2", "q", "quit", "exit"):
            print(c("[+] Выход.", GREEN))
            break
        if ch != "1":
            print(c("[!] Неверный выбор.", RED))
            continue

        links = []
        print(c("\n[*] Введите ссылки (по одной). Пустая строка — загрузка, 'q' — меню.", YELLOW))
        while True:
            try:
                link = input(c("> ", GREEN)).strip()
            except (EOFError, KeyboardInterrupt):
                link = "q"
            if link.lower() == "q":
                break
            if not link:
                break
            links.append(link)
        if links:
            process_links(links)
        else:
            print(c("[!] Ссылки не введены.", YELLOW))


if __name__ == "__main__":
    try:
        main_menu()
    except KeyboardInterrupt:
        print(c("\n[+] Работа остановлена.", GREEN))
PYEOF

chmod 700 /tmp/video_downloader.py
say "${BLUE}[*] Запуск...${NC}"
exec "$PYTHON_BIN" /tmp/video_downloader.py
