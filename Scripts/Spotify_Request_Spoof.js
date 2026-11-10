(function () {
    "use strict";
    function parseArgs() {
        try {
            if (typeof $argument === "string" && $argument.trim().length > 0) return JSON.parse($argument);
            if (typeof $argument === "object" && $argument !== null) return $argument;
        } catch (e) {}
        return {};
    }
    const args = parseArgs();
    const DEBUG = args.debug === true;
    function log() {
        if (!DEBUG) return;
        try { console.log("[Spotify-UA] " + Array.prototype.slice.call(arguments).join(" ")); } catch (e) {}
    }

    try {
        const headers = $request.headers || {};
        const url = String($request.url || "");
        const names = Object.keys(headers);

        let isWS = false;
        for (let i = 0; i < names.length; i++) {
            const low = names[i].toLowerCase();
            const val = String(headers[names[i]] || "").toLowerCase();
            if (low === "upgrade" && val.indexOf("websocket") !== -1) { isWS = true; break; }
            if (low === "connection" && val.indexOf("upgrade") !== -1 && val.indexOf("keep-alive") === -1) { isWS = true; break; }
        }
        if (isWS) {
            log("SKIP websocket:", url.slice(0, 60));
            $done({});
            return;
        }

        const PROFILES = {
            win10: {
                ua: "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
                chUa: '"Chromium";v="124", "Google Chrome";v="124", "Not-A.Brand";v="24"',
                chPlatform: '"Windows"',
                chMobile: "?0",
                chPlatformVersion: '"10.0.0"',
                chArch: '"x86"',
                chBitness: '"64"',
                chModel: '""'
            },
            win11: {
                ua: "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
                chUa: '"Chromium";v="126", "Google Chrome";v="126", "Not-A.Brand";v="99"',
                chPlatform: '"Windows"',
                chMobile: "?0",
                chPlatformVersion: '"15.0.0"',
                chArch: '"x86"',
                chBitness: '"64"',
                chModel: '""'
            },
            macos: {
                ua: "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
                chUa: '"Chromium";v="124", "Google Chrome";v="124", "Not-A.Brand";v="24"',
                chPlatform: '"macOS"',
                chMobile: "?0",
                chPlatformVersion: '"14.4.0"',
                chArch: '"arm"',
                chBitness: '"64"',
                chModel: '""'
            }
        };

        const profile = PROFILES[args.uaProfile] || PROFILES.win10;
        const desired = {
            "user-agent": profile.ua,
            "sec-ch-ua": profile.chUa,
            "sec-ch-ua-platform": profile.chPlatform,
            "sec-ch-ua-mobile": profile.chMobile,
            "sec-ch-ua-platform-version": profile.chPlatformVersion,
            "sec-ch-ua-arch": profile.chArch,
            "sec-ch-ua-bitness": profile.chBitness,
            "sec-ch-ua-model": profile.chModel
        };

        const existing = {};
        for (let i = 0; i < names.length; i++) existing[names[i].toLowerCase()] = names[i];

        let modified = 0;
        for (const low in desired) {
            const val = desired[low];
            if (existing[low]) {
                headers[existing[low]] = val;
            } else {
                headers[low] = val;
            }
            modified++;
        }

        log("MOD", modified, "hdrs ->", url.slice(0, 60));
        $done({ headers });
    } catch (e) {
        try { console.log("[Spotify-UA] ERR: " + (e && e.message ? e.message : e)); } catch (_) {}
        try { if (args.notify === true) $notification.post("Spotify Request", "error", String(e && e.message || e).slice(0, 100)); } catch (_) {}
        $done({});
    }
})();
