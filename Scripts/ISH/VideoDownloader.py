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
    echo -e "${BLUE}[*] Установка Python-библиотек...${NC}"
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
import re
import time
import json
import subprocess
import shutil
import ssl
import urllib.request
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

def color(text, c):
    return f"{c}{text}{NC}"

def print_banner():
    print(color("=" * 44, YELLOW))
    print(color("  Универсальный загрузчик видео", YELLOW))
    print(color("=" * 44, YELLOW))

def is_root():
    return os.geteuid() == 0

def ensure_dir():
    global VIDEOS_DIR
    try:
        VIDEOS_DIR.mkdir(parents=True, exist_ok=True)
        test_file = VIDEOS_DIR / ".write_test"
        test_file.touch()
        test_file.unlink()
    except Exception:
        print(color(f"[!] Нет доступа к {VIDEOS_DIR}. Используем {FALLBACK_DIR}", YELLOW))
        VIDEOS_DIR = FALLBACK_DIR
        VIDEOS_DIR.mkdir(parents=True, exist_ok=True)

def install_russian_ca():
    if not is_root():
        return False
    if Path(RUSSIAN_CA_PATH).exists():
        return True
    try:
        print(color("[*] Установка сертификата Минцифры для RuTube...", BLUE))
        urllib.request.urlretrieve(RUSSIAN_CA_URL, RUSSIAN_CA_PATH)
        subprocess.run(["update-ca-certificates"], check=True, capture_output=True)
        print(color("[+] Сертификат установлен.", GREEN))
        return True
    except Exception as e:
        print(color(f"[!] Не удалось установить сертификат: {e}", YELLOW))
        return False

def get_video_info(url):
    ydl_opts = {
        "quiet": True,
        "no_warnings": True,
        "extract_flat": False,
        "noplaylist": True,
        "ignoreerrors": True,
        "nocheckcertificate": not Path(RUSSIAN_CA_PATH).exists(),
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            if info and "entries" in info:
                entries = list(info["entries"])
                if entries:
                    return entries[0]
            return info
    except Exception as e:
        print(color(f"[!] Не удалось получить информацию: {e}", RED))
        return None

def format_selector(ctx):
    formats = ctx.get("formats")[::-1]
    unique_formats = {}
    for f in formats:
        if f.get("vcodec") == "none":
            continue
        key = (f.get("height"), f.get("ext"), f.get("format_note"))
        if key not in unique_formats:
            unique_formats[key] = f

    format_list = list(unique_formats.values())
    if not format_list:
        return "bestvideo+bestaudio/best"

    print(color("\nДоступные форматы видео:", CYAN))
    for i, f in enumerate(format_list, 1):
        height = f.get("height", "?")
        ext = f.get("ext", "?")
        note = f.get("format_note", "")
        filesize = f.get("filesize") or f.get("filesize_approx")
        size_str = f"{filesize / 1024 / 1024:.1f} MB" if filesize else "N/A"
        print(f"  {i}. {height}p ({ext}) {note} - {size_str}")

    audio_formats = [f for f in formats if f.get("acodec") != "none" and f.get("vcodec") == "none"]
    if audio_formats:
        print(color("\nДоступные аудиодорожки:", CYAN))
        for i, f in enumerate(audio_formats, 1):
            lang = f.get("language", "unknown")
            abr = f.get("abr", "?")
            print(f"  {i}. Язык: {lang}, Битрейт: {abr} kbps")

    try:
        choice = input(color("\nВыберите номер видеоформата (Enter — лучший): ", YELLOW)).strip()
        if not choice:
            return "bestvideo+bestaudio/best"
        idx = int(choice) - 1
        selected = format_list[max(0, min(idx, len(format_list) - 1))]

        audio_choice = None
        if audio_formats:
            a_input = input(color("Выберите номер аудиодорожки (Enter — лучшая): ", YELLOW)).strip()
            if a_input:
                a_idx = int(a_input) - 1
                audio_choice = audio_formats[max(0, min(a_idx, len(audio_formats) - 1))]

        if audio_choice:
            return f"{selected['format_id']}+{audio_choice['format_id']}"
        return f"{selected['format_id']}+bestaudio/best"
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
            print(color(f"[+] Загрузка завершена: {d.get('filename', '')}", GREEN))

    return hook

def download_video(url):
    print(color(f"\n[*] Обработка ссылки: {url}", BLUE))
    info = get_video_info(url)
    if not info:
        return False

    title = info.get("title", "video")
    print(color(f"[*] Название: {title}", CYAN))

    ydl_opts = {
        "outtmpl": str(VIDEOS_DIR / "%(title)s.%(ext)s"),
        "progress_hooks": [create_progress_hook(title)],
        "format": format_selector,
        "merge_output_format": "mp4",
        "nocheckcertificate": not Path(RUSSIAN_CA_PATH).exists(),
        "writethumbnail": False,
        "quiet": True,
        "no_warnings": True,
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
        print(color(f"[+] Видео сохранено в {VIDEOS_DIR}", GREEN))
        return True
    except Exception as e:
        print(color(f"[!] Ошибка скачивания: {e}", RED))
        return False

def find_videos_on_page(page_url):
    print(color(f"\n[*] Поиск видео на странице: {page_url}", BLUE))
    ydl_opts = {
        "quiet": True,
        "no_warnings": True,
        "extract_flat": True,
        "nocheckcertificate": not Path(RUSSIAN_CA_PATH).exists(),
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(page_url, download=False)
            if info and "entries" in info:
                urls = [e["url"] for e in info["entries"] if e.get("url")]
                print(color(f"[+] Найдено видео: {len(urls)}", GREEN))
                return urls
            elif info and info.get("url"):
                return [info["url"]]
    except Exception as e:
        print(color(f"[!] Не удалось найти видео на странице: {e}", YELLOW))
    return []

def main_loop():
    ensure_dir()
    print(color(f"[*] Видео будут сохраняться в: {VIDEOS_DIR}", CYAN))

    links = []
    print(color("\n[*] Введите ссылки на видео (по одной на строку).", YELLOW))
    print(color("[*] Оставьте строку пустой и нажмите Enter, чтобы начать загрузку.", YELLOW))
    while True:
        link = input(color("> ", GREEN)).strip()
        if not link:
            break
        links.append(link)

    if not links:
        print(color("[!] Не введено ни одной ссылки. Выход.", RED))
        return

    for url in links:
        if not any(domain in url for domain in ["youtube.com", "youtu.be", "rutube.ru", ".mp4", ".m3u8"]):
            found = find_videos_on_page(url)
            if found:
                if len(found) == 1:
                    download_video(found[0])
                else:
                    print(color("\nНа странице найдено несколько видео:", CYAN))
                    for i, u in enumerate(found, 1):
                        print(f"  {i}. {u}")
                    try:
                        choice = input(color("Выберите номер видео (или 'all' для всех): ", YELLOW)).strip()
                        if choice.lower() == "all":
                            for u in found:
                                download_video(u)
                        else:
                            idx = int(choice) - 1
                            download_video(found[idx])
                    except (ValueError, IndexError):
                        print(color("[!] Неверный выбор.", RED))
            else:
                print(color(f"[!] Не удалось найти видео на странице: {url}", YELLOW))
        else:
            download_video(url)

    print(color("\n[*] Все задачи выполнены.", GREEN))

if __name__ == "__main__":
    if not is_root():
        print(color("[!] Скрипт запущен без прав root. Установка сертификата и запись в /root могут быть недоступны.", YELLOW))
    install_russian_ca()
    main_loop()
PYEOF

echo -e "${BLUE}[*] Запуск загрузчика...${NC}"
python3 /tmp/video_downloader.py
