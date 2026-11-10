(function () {
    "use strict";

    function parseArgs() {
        try {
            if (typeof $argument === "string" && $argument.trim().length > 0) {
                return JSON.parse($argument);
            }
            if (typeof $argument === "object" && $argument !== null) {
                return $argument;
            }
        } catch (e) {}
        return {};
    }

    const args = parseArgs();
    const DEBUG = args.debug === true;

    function log() {
        if (!DEBUG) return;
        try {
            console.log("[Spotify-Inject] " + Array.prototype.slice.call(arguments).join(" "));
        } catch (e) {}
    }

    try {
        const body = $response.body;
        const headers = $response.headers || {};
        const url = String($request.url || "");
        const names = Object.keys(headers);

        if (typeof body !== "string" || body.length === 0) {
            log("SKIP empty body:", url.slice(0, 60));
            $done({});
            return;
        }

        let ct = "";
        for (let i = 0; i < names.length; i++) {
            if (names[i].toLowerCase() === "content-type") {
                ct = String(headers[names[i]] || "").toLowerCase();
                break;
            }
        }

        if (ct.indexOf("text/html") === -1) {
            log("SKIP non-html ct=" + ct + " url=" + url.slice(0, 60));
            $done({});
            return;
        }

        const head = body.slice(0, 500).toLowerCase();
        if (head.indexOf("<!doctype") === -1 && head.indexOf("<html") === -1) {
            log("SKIP not-real-html url=" + url.slice(0, 60));
            $done({});
            return;
        }

        if (!/<head[^>]*>/i.test(body)) {
            log("SKIP no <head> url=" + url.slice(0, 60));
            $done({});
            return;
        }

        const PROFILES = {
            win10: {
                ua: "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
                platform: "Win32",
                touch: 0
            },
            win11: {
                ua: "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
                platform: "Win32",
                touch: 0
            },
            macos: {
                ua: "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
                platform: "MacIntel",
                touch: 0
            }
        };

        const profile = PROFILES[args.uaProfile] || PROFILES.win10;

        const injection = '<script>(function(){try{' +
            'var _ua=' + JSON.stringify(profile.ua) + ';' +
            'var _pf=' + JSON.stringify(profile.platform) + ';' +
            'var _tp=' + profile.touch + ';' +
            'try{Object.defineProperty(navigator,"userAgent",{get:function(){return _ua;}});}catch(e){}' +
            'try{Object.defineProperty(navigator,"appVersion",{get:function(){return _ua.replace(/^Mozilla\\//,"");}});}catch(e){}' +
            'try{Object.defineProperty(navigator,"platform",{get:function(){return _pf;}});}catch(e){}' +
            'try{Object.defineProperty(navigator,"maxTouchPoints",{get:function(){return _tp;}});}catch(e){}' +
            'try{Object.defineProperty(window.screen,"width",{get:function(){return 1920;}});}catch(e){}' +
            'try{Object.defineProperty(window.screen,"height",{get:function(){return 1080;}});}catch(e){}' +
            'try{Object.defineProperty(window.screen,"availWidth",{get:function(){return 1920;}});}catch(e){}' +
            'try{Object.defineProperty(window.screen,"availHeight",{get:function(){return 1040;}});}catch(e){}' +
            'try{var _mm=window.matchMedia.bind(window);window.matchMedia=function(q){if(q&&String(q).indexOf("touch")!==-1){return{matches:false,media:q,addListener:function(){},removeListener:function(){},addEventListener:function(){},removeEventListener:function(){}};}return _mm(q);};}catch(e){}' +
            '}catch(e){}})();</script>';

        const newBody = body.replace(/<head[^>]*>/i, function (m) { return m + injection; });

        log("INJECT ok", body.length, "->", newBody.length, "url=" + url.slice(0, 60));
        if (args.notify === true) {
            try { $notification.post("Spotify Inject", "OK", url.slice(0, 60)); } catch (_) {}
        }

        $done({ body: newBody });
    } catch (e) {
        try { console.log("[Spotify-Inject] ERR: " + (e && e.message ? e.message : e)); } catch (_) {}
        try { if (args.notify === true) $notification.post("Spotify Inject", "error", String(e && e.message || e).slice(0, 100)); } catch (_) {}
        $done({});
    }
})();
