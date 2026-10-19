#!/bin/sh

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

setup_dns() {
    cat > /etc/resolv.conf << 'DNS_EOF'
nameserver 8.8.8.8
nameserver 8.8.4.4
nameserver 94.140.14.14
nameserver 94.140.15.15
nameserver 1.1.1.1
DNS_EOF
}

install_packages() {
    echo -e "${BLUE}[*] Обновление системы и установка пакетов...${NC}"
    apk update && apk upgrade
    apk add --no-cache python3 py3-pip curl wget bash ffmpeg ca-certificates
    pip install --upgrade yt-dlp tqdm
    echo -e "${GREEN}[+] Зависимости установлены.${NC}"
}

echo -e "${YELLOW}========================================${NC}"
echo -e "${YELLOW}  Универсальный загрузчик видео${NC}"
echo -e "${YELLOW}========================================${NC}"
printf "Обновить/установить пакеты и настроить DNS? [y/N]: "
read -r ANSWER
case "$ANSWER" in
    [yY]|[yY][eE][sS])
        setup_dns
        install_packages
        ;;
    *)
        echo -e "${BLUE}[*] Настройка DNS...${NC}"
        setup_dns
        echo -e "${GREEN}[+] DNS настроен.${NC}"
        ;;
esac

cat > /tmp/video_downloader.py << 'PYEOF'
import os
import sys
import subprocess
import shutil
import ssl
import urllib.request
import time
from pathlib import Path

try:
    import yt_dlp
    from tqdm import tqdm
except ImportError:
    print("\033[0;31m[!] Не установлены yt-dlp или tqdm. Установите: pip install yt-dlp tqdm\033[0m")
    sys.exit(1)

VIDEOS_DIR = Path("/root/videos")
FALLBACK_DIR = Path.home() / "videos"
RUSSIAN_CA_URL = "https://gu-st.ru/content/lending/russian_trusted_root_ca_pem.crt"
RUSSIAN_CA_PATH = "/usr/local/share/ca-certificates/russian_trusted_root_ca.crt"

RED = "\033[0;31m"
GREEN = "\033[0;32m"
YELLOW = "\033[1;33m"
BLUE = "\033[0;34m"
CYAN = "\033[0;36m"
NC = "\033[0m"

def c(text, color):
    return f"{color}{text}{NC}"

def is_root():
    return os.geteuid() == 0

def ensure_dir():
    global VIDEOS_DIR
    try:
        VIDEOS_DIR.mkdir(parents=True, exist_ok=True)
        test = VIDEOS_DIR / ".wtest"
        test.touch()
        test.unlink()
    except Exception:
        print(c(f"[!] Нет доступа к {VIDEOS_DIR}. Используем {FALLBACK_DIR}", YELLOW))
        VIDEOS_DIR = FALLBACK_DIR
        VIDEOS_DIR.mkdir(parents=True, exist_ok=True)

def install_russian_ca():
    if not is_root():
        return False
    if Path(RUSSIAN_CA_PATH).exists():
        return True
    try:
        print(c("[*] Установка сертификата Минцифры...", BLUE))
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        with urllib.request.urlopen(RUSSIAN_CA_URL, context=ctx, timeout=30) as r:
            data = r.read()
        Path(RUSSIAN_CA_PATH).write_bytes(data)
        subprocess.run(["update-ca-certificates"], check=True, capture_output=True)
        print(c("[+] Сертификат установлен.", GREEN))
        return True
    except Exception as e:
        print(c(f"[!] Не удалось установить сертификат: {e}", YELLOW))
        return False

def confirm_action(prompt):
    try:
        ans = input(c(prompt + " [y/N]: ", YELLOW)).strip().lower()
        return ans in ("y", "yes", "да", "д")
    except (EOFError, KeyboardInterrupt):
        return False

def get_video_info(url, extra_opts=None):
    opts = {
        "quiet": True,
        "no_warnings": True,
        "extract_flat": False,
        "noplaylist": True,
        "ignoreerrors": True,
        "socket_timeout": 30,
    }
    if extra_opts:
        opts.update(extra_opts)
    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=False)
            if info and "entries" in info:
                entries = list(info["entries"])
                if entries:
                    return entries[0]
            return info
    except Exception as e:
        print(c(f"[!] Не удалось получить информацию: {e}", RED))
        return None

def format_selector(ctx):
    formats = ctx.get("formats")[::-1]
    unique = {}
    for f in formats:
        if f.get("vcodec") == "none":
            continue
        key = (f.get("height"), f.get("ext"), f.get("format_note"))
        if key not in unique:
            unique[key] = f

    flist = list(unique.values())
    if not flist:
        return "bestvideo+bestaudio/best"

    print(c("\nДоступные форматы видео:", CYAN))
    for i, f in enumerate(flist, 1):
        h = f.get("height", "?")
        ext = f.get("ext", "?")
        note = f.get("format_note", "")
        size = f.get("filesize") or f.get("filesize_approx")
        sz = f"{size / 1024 / 1024:.1f} MB" if size else "N/A"
        print(f"  {i}. {h}p ({ext}) {note} - {sz}")

    audio_fmts = [f for f in formats if f.get("acodec") != "none" and f.get("vcodec") == "none"]
    if audio_fmts:
        print(c("\nДоступные аудиодорожки:", CYAN))
        for i, f in enumerate(audio_fmts, 1):
            lang = f.get("language", "unknown")
            abr = f.get("abr", "?")
            print(f"  {i}. Язык: {lang}, Битрейт: {abr} kbps")

    try:
        choice = input(c("\nВыберите номер видеоформата (Enter — лучший): ", YELLOW)).strip()
        if not choice:
            return "bestvideo+bestaudio/best"
        idx = int(choice) - 1
        sel = flist[max(0, min(idx, len(flist) - 1))]

        audio_sel = None
        if audio_fmts:
            ai = input(c("Выберите номер аудиодорожки (Enter — лучшая): ", YELLOW)).strip()
            if ai:
                aidx = int(ai) - 1
                audio_sel = audio_fmts[max(0, min(aidx, len(audio_fmts) - 1))]

        if audio_sel:
            return f"{sel['format_id']}+{audio_sel['format_id']}"
        return f"{sel['format_id']}+bestaudio/best"
    except (ValueError, IndexError):
        return "bestvideo+bestaudio/best"

def create_progress_hook(desc):
    pbar = None

    def hook(d):
        nonlocal pbar
        if d["status"] == "downloading":
            if pbar is None:
                total = d.get("total_bytes") or d.get("total_bytes_estimate")
                pbar = tqdm(total=total, unit="B", unit_scale=True, desc=desc, leave=False)
            pbar.n = d.get("downloaded_bytes", 0)
            pbar.refresh()
        elif d["status"] == "finished":
            if pbar:
                pbar.n = pbar.total
                pbar.close()
                pbar = None
            print(c(f"[+] Загрузка завершена: {d.get('filename', '')}", GREEN))

    return hook

def try_download_with_opts(url, opts):
    opts.setdefault("outtmpl", str(VIDEOS_DIR / "%(title)s.%(ext)s"))
    opts.setdefault("merge_output_format", "mp4")
    opts.setdefault("progress_hooks", [create_progress_hook("Загрузка")])
    opts.setdefault("quiet", True)
    opts.setdefault("no_warnings", True)
    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            ydl.download([url])
        return True
    except Exception as e:
        print(c(f"  [!] Ошибка: {e}", RED))
        return False

def attempt_download(url, use_cert=True):
    base_opts = {
        "format": format_selector,
        "nocheckcertificate": not use_cert,
        "legacy_server_connect": False,
        "prefer_insecure": False,
    }

    if try_download_with_opts(url, dict(base_opts)):
        return True

    if use_cert:
        print(c("[!] Не удалось скачать с проверкой сертификата.", YELLOW))
        if confirm_action("Разрешить скачать без проверки сертификата?"):
            base_opts["nocheckcertificate"] = True
            print(c("[*] Повторная попытка без проверки сертификата...", BLUE))
            if try_download_with_opts(url, dict(base_opts)):
                return True
        else:
            return False

    print(c("[*] Попытка с legacy_server_connect...", BLUE))
    base_opts["legacy_server_connect"] = True
    if try_download_with_opts(url, dict(base_opts)):
        return True

    print(c("[*] Попытка с prefer_insecure...", BLUE))
    base_opts["prefer_insecure"] = True
    if try_download_with_opts(url, dict(base_opts)):
        return True

    print(c("[!] Все попытки скачивания не удались.", RED))
    return False

def find_videos_on_page(page_url):
    print(c(f"\n[*] Поиск видео на странице: {page_url}", BLUE))
    opts = {
        "quiet": True,
        "no_warnings": True,
        "extract_flat": True,
        "nocheckcertificate": True,
        "socket_timeout": 30,
    }
    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(page_url, download=False)
            if info and "entries" in info:
                urls = [e["url"] for e in info["entries"] if e.get("url")]
                print(c(f"[+] Найдено видео: {len(urls)}", GREEN))
                return urls
            elif info and info.get("url"):
                return [info["url"]]
    except Exception as e:
        print(c(f"[!] Не удалось найти видео на странице: {e}", YELLOW))
    return []

def process_links(links):
    for url in links:
        if url.lower() == "q":
            return
        if not any(domain in url for domain in ["youtube.com", "youtu.be", "rutube.ru", ".mp4", ".m3u8"]):
            found = find_videos_on_page(url)
            if found:
                if len(found) == 1:
                    attempt_download(found[0])
                else:
                    print(c("\nНа странице найдено несколько видео:", CYAN))
                    for i, u in enumerate(found, 1):
                        print(f"  {i}. {u}")
                    try:
                        choice = input(c("Выберите номер видео (или 'all' для всех): ", YELLOW)).strip()
                        if choice.lower() == "all":
                            for u in found:
                                attempt_download(u)
                        else:
                            idx = int(choice) - 1
                            attempt_download(found[idx])
                    except (ValueError, IndexError):
                        print(c("[!] Неверный выбор.", RED))
            else:
                print(c(f"[!] Не удалось найти видео на странице: {url}", YELLOW))
        else:
            attempt_download(url)

def main_menu():
    ensure_dir()
    print(c(f"[*] Видео сохраняются в: {VIDEOS_DIR}", CYAN))
    while True:
        print(c("\n" + "=" * 40, YELLOW))
        print(c("  Главное меню", YELLOW))
        print(c("=" * 40, YELLOW))
        print("  1. Скачать видео")
        print("  2. Выход (q)")
        choice = input(c("Ваш выбор: ", GREEN)).strip().lower()
        if choice in ("2", "q", "quit", "exit"):
            print(c("[+] Выход.", GREEN))
            break
        if choice != "1":
            print(c("[!] Неверный выбор.", RED))
            continue

        links = []
        print(c("\n[*] Введите ссылки на видео (по одной на строку).", YELLOW))
        print(c("[*] Пустая строка — начать загрузку. 'q' — вернуться в меню.", YELLOW))
        while True:
            link = input(c("> ", GREEN)).strip()
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
    if not is_root():
        print(c("[!] Скрипт запущен без прав root. Установка сертификата и запись в /root могут быть недоступны.", YELLOW))
    install_russian_ca()
    main_menu()
PYEOF

echo -e "${BLUE}[*] Запуск загрузчика...${NC}"
python3 /tmp/video_downloader.py
