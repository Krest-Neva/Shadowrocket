#!/bin/sh

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; BLUE='\033[0;34m'; NC='\033[0m'
say() { printf '%b\n' "$1"; }

setup_dns() {
    cat > /etc/resolv.conf << 'EOF'
nameserver 1.1.1.1
nameserver 8.8.8.8
nameserver 94.140.14.14
EOF
}

have_ytdlp() {
    python3 - << 'EOF' >/dev/null 2>&1
import yt_dlp, tqdm
EOF
}

install_packages() {
    say "${BLUE}[*] apk update...${NC}"
    apk update || say "${YELLOW}[!] apk update failed, continue${NC}"
    for p in python3 py3-pip ffmpeg ca-certificates curl \
             py3-brotli py3-pycryptodomex py3-mutagen py3-websockets; do
        apk add --no-cache "$p" >/dev/null 2>&1 || say "${YELLOW}[!] apk: $p not installed${NC}"
    done

    say "${BLUE}[*] pip: yt-dlp...${NC}"
    pip3 install -U --no-deps --disable-pip-version-check yt-dlp tqdm \
      || pip3 install -U --no-deps --break-system-packages yt-dlp tqdm \
      || say "${RED}[!] pip install failed${NC}"
}

say "${YELLOW}=== Video Downloader ===${NC}"
setup_dns

if ! have_ytdlp; then
    say "${YELLOW}[*] yt-dlp не найден — устанавливаю${NC}"
    install_packages
elif [ "${1:-}" = "--update" ]; then
    install_packages
fi

have_ytdlp || say "${RED}[!] yt-dlp/tqdm не импортируются, но скрипт попробует запасные методы${NC}"

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

YTDLP_BINARY = shutil.which("yt-dlp")
VIDEOS_DIR = Path("/root/videos")
FALLBACK_DIR = Path.home() / "videos"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"

RED, GREEN, YELLOW, BLUE, CYAN, NC = ("\033[0;31m", "\033[0;32m", "\033[1;33m",
                                      "\033[0;34m", "\033[0;36m", "\033[0m")
def c(t, col): return f"{col}{t}{NC}"

def ensure_dir():
    global VIDEOS_DIR
    for d in (VIDEOS_DIR, FALLBACK_DIR):
        try:
            d.mkdir(parents=True, exist_ok=True)
            t = d / ".write_test"; t.touch(); t.unlink()
            VIDEOS_DIR = d
            return
        except OSError:
            continue
    raise OSError("no writable video directory")

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
            print(c(f"[!] info: {type(e).__name__}: {str(e)[:200]}", YELLOW))
    return None

def select_format(url):
    default = "bv*+ba/b"
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

    print(c("\nAvailable video formats:", CYAN))
    for i, f in enumerate(vlist, 1):
        size = f.get("filesize") or f.get("filesize_approx")
        size_t = f", {size/1048576:.1f} MiB" if isinstance(size, (int, float)) else ""
        fps_t = f", {f['fps']} fps" if f.get("fps") else ""
        aud = "with audio" if f.get("acodec") not in (None, "none") else "no audio"
        print(f"  {i}. {f.get('height') or '?'}p ({f.get('ext') or '?'}, {aud}{fps_t}{size_t})")
    try:
        ch = input(c("\nSelect video format (Enter = best): ", YELLOW)).strip()
    except (EOFError, KeyboardInterrupt):
        return default
    if not ch:
        return default
    try:
        sel = vlist[int(ch) - 1]
    except (ValueError, IndexError):
        print(c("[!] invalid choice, using default", YELLOW))
        return default

    vid = str(sel["format_id"])
    if sel.get("acodec") not in (None, "none"):
        return vid
    if not audios:
        return f"{vid}+ba/b"
    print(c("\nAvailable audio tracks:", CYAN))
    for i, f in enumerate(audios, 1):
        abr = f.get("abr")
        abr_t = f", {abr:g} kbps" if isinstance(abr, (int, float)) else ""
        print(f"  {i}. {f.get('language') or 'unknown'}, {f.get('ext') or '?'}{abr_t}")
    try:
        a = input(c("Select audio (Enter = best): ", YELLOW)).strip()
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
                state["bar"] = tqdm(total=total, unit="B", unit_scale=True, leave=False)
            elif total:
                state["bar"].total = total
            dl = d.get("downloaded_bytes") or 0
            state["bar"].update(max(0, dl - state["bar"].n))
        elif st in ("finished", "error"):
            if state["bar"]:
                state["bar"].close(); state["bar"] = None
            if st == "finished":
                print(c(f"[+] finished: {d.get('filename','')}", GREEN))
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
        print(c(f"[!] yt-dlp: {type(e).__name__}: {str(e)[:250]}", RED))
        return False

def run_binary(url, selector, *flags):
    if not YTDLP_BINARY:
        return False
    cmd = [YTDLP_BINARY, "-f", selector, "--merge-output-format", "mp4", "--force-ipv4",
           "-o", str(VIDEOS_DIR / OUT_TMPL), "--no-warnings", "--no-playlist", *flags, url]
    try:
        return subprocess.run(cmd, timeout=3600).returncode == 0
    except Exception as e:
        print(c(f"[!] yt-dlp binary: {e}", RED))
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
    print(c("[*] RuTube: пробую API напрямую...", BLUE))

    title = vid
    try:
        meta = http_json(f"https://rutube.ru/api/video/{vid}/?format=json")
        title = meta.get("title") or vid
    except Exception as e:
        print(c(f"[!] meta: {str(e)[:120]}", YELLOW))
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
            m3u8 = vb.get("m3u8") or vb.get("default") if isinstance(vb, dict) else None
            if m3u8:
                break
        except Exception as e:
            print(c(f"[!] api: {str(e)[:120]}", YELLOW))
    if not m3u8:
        print(c("[!] RuTube API не вернул ссылку на поток", YELLOW))
        return False

    print(c("[*] RuTube: найден HLS-поток, качаю...", BLUE))
    hdrs = {"User-Agent": UA, "Referer": "https://rutube.ru/", "Origin": "https://rutube.ru"}
    out = VIDEOS_DIR / f"{title} [{vid}].mp4"
    if yt_dlp is not None:
        for sel in ("bv*+ba/b", "best"):
            opts = base_opts(format=sel, outtmpl=str(VIDEOS_DIR / f"{title} [{vid}].%(ext)s"),
                             merge_output_format="mp4", http_headers=hdrs, continuedl=True)
            h = progress_hook()
            if h:
                opts["progress_hooks"] = [h]
            try:
                with yt_dlp.YoutubeDL(opts) as ydl:
                    if ydl.download([m3u8]) in (None, 0):
                        return True
            except Exception as e:
                print(c(f"[!] hls ({sel}): {str(e)[:200]}", YELLOW))
    if shutil.which("ffmpeg"):
        print(c("[*] запасной вариант: ffmpeg", BLUE))
        hs = "".join(f"{k}: {v}\r\n" for k, v in hdrs.items())
        cmd = ["ffmpeg", "-y", "-headers", hs, "-i", m3u8, "-c", "copy", "-bsf:a", "aac_adtstoasc", str(out)]
        try:
            if subprocess.run(cmd, timeout=7200).returncode == 0 and out.exists() and out.stat().st_size > 0:
                print(c(f"[+] saved: {out}", GREEN))
                return True
        except Exception as e:
            print(c(f"[!] ffmpeg: {e}", RED))
    return False

def attempt_download(url):
    if not valid_url(url):
        print(c(f"[!] invalid url: {url}", RED)); return False

    selector = select_format(url)
    print(c(f"[*] selector: {selector}", BLUE))
    if run_module(url, selector) or run_binary(url, selector):
        return True

    if "rutube.ru" in url and rutube_download(url):
        return True

    print(c("[!] пробую generic-экстрактор...", YELLOW))
    if run_module(url, "bv*+ba/b", force_generic_extractor=True) or run_binary(url, "bv*+ba/b", "--force-generic-extractor"):
        return True

    if confirm("Retry without TLS verification?"):
        if run_module(url, "bv*+ba/b", nocheckcertificate=True) or run_binary(url, "bv*+ba/b", "--no-check-certificate"):
            return True

    print(c("[!] all attempts exhausted", RED))
    return False

def find_videos_on_page(page_url):
    print(c(f"\n[*] scanning page: {page_url}", BLUE))
    if yt_dlp is None:
        return []
    try:
        with yt_dlp.YoutubeDL(base_opts(extract_flat=True, noplaylist=False)) as ydl:
            info = ydl.extract_info(page_url, download=False)
    except Exception as e:
        print(c(f"[!] scan: {str(e)[:200]}", YELLOW)); return []
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
        print(c(f"[+] found {len(urls)} videos", GREEN))
        return urls
    u = info.get("webpage_url") or info.get("original_url") or info.get("url")
    return [u] if isinstance(u, str) and valid_url(u) else []

DIRECT = ("youtube.com/", "youtu.be/", "rutube.ru/video/", "rutube.ru/play/", ".mp4", ".m3u8")

def process_links(links):
    for url in links:
        if not valid_url(url):
            print(c(f"[!] invalid url: {url}", RED)); continue
        if not any(m in url.lower() for m in DIRECT):
            found = find_videos_on_page(url)
            if not found:
                print(c(f"[!] no videos found: {url}", YELLOW)); continue
            if len(found) == 1:
                attempt_download(found[0]); continue
            for i, u in enumerate(found, 1):
                print(f"  {i}. {u}")
            try:
                ch = input(c("number or 'all': ", YELLOW)).strip().lower()
                if ch == "all":
                    for u in found: attempt_download(u)
                else:
                    attempt_download(found[int(ch) - 1])
            except (ValueError, IndexError, EOFError, KeyboardInterrupt):
                print(c("[!] invalid choice", RED))
        else:
            attempt_download(url)

def main_menu():
    try:
        ensure_dir()
    except OSError as e:
        print(c(f"[!] directory error: {e}", RED)); return
    print(c(f"[*] videos directory: {VIDEOS_DIR}", CYAN))
    while True:
        print(c("\n" + "=" * 40 + "\n  Main menu\n" + "=" * 40, YELLOW))
        print("  1. Download video\n  2. Exit (q)")
        try:
            ch = input(c("choice: ", GREEN)).strip().lower()
        except (EOFError, KeyboardInterrupt):
            break
        if ch in ("2", "q", "quit", "exit"):
            break
        if ch != "1":
            print(c("[!] invalid choice", RED)); continue
        links = []
        print(c("\n[*] enter URLs (one per line). Empty line to start.", YELLOW))
        while True:
            try:
                l = input(c("> ", GREEN)).strip()
            except (EOFError, KeyboardInterrupt):
                break
            if not l or l.lower() == "q":
                break
            links.append(l)
        if links:
            process_links(links)

if __name__ == "__main__":
    try:
        main_menu()
    except KeyboardInterrupt:
        print(c("\n[+] stopped", GREEN))
PYEOF

chmod 700 /tmp/video_downloader.py
command -v python3 >/dev/null 2>&1 || { say "${RED}[!] python3 не найден${NC}"; exit 1; }
exec python3 /tmp/video_downloader.py
