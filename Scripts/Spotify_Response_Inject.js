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
        try { console.log("[Spotify-Inject] " + Array.prototype.slice.call(arguments).join(" ")); } catch (e) {}
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
                touch: 0,
                chPlatform: "Windows",
                chVersion: "124",
                chBrand: "Google Chrome"
            },
            win11: {
                ua: "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
                platform: "Win32",
                touch: 0,
                chPlatform: "Windows",
                chVersion: "126",
                chBrand: "Google Chrome"
            },
            macos: {
                ua: "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
                platform: "MacIntel",
                touch: 0,
                chPlatform: "macOS",
                chVersion: "124",
                chBrand: "Google Chrome"
            }
        };
        const profile = PROFILES[args.uaProfile] || PROFILES.win10;

        const uaJson = JSON.stringify(profile.ua);
        const pfJson = JSON.stringify(profile.platform);
        const chPlatformJson = JSON.stringify(profile.chPlatform);
        const chVersionJson = JSON.stringify(profile.chVersion);
        const chBrandJson = JSON.stringify(profile.chBrand);
        const touchStr = String(profile.touch);

        const injection = '<script>(function(){' +
            'var UA=' + uaJson + ';' +
            'var PF=' + pfJson + ';' +
            'var TP=' + touchStr + ';' +
            'var CP=' + chPlatformJson + ';' +
            'var CV=' + chVersionJson + ';' +
            'var CB=' + chBrandJson + ';' +
            'function setNav(p,v){' +
            'try{Object.defineProperty(navigator,p,{get:function(){return v;},configurable:true});}catch(e){}' +
            'try{Object.defineProperty(Navigator.prototype,p,{get:function(){return v;},configurable:true});}catch(e){}' +
            '}' +
            'setNav("userAgent",UA);' +
            'setNav("appVersion",UA.replace(/^Mozilla\\//,""));' +
            'setNav("platform",PF);' +
            'setNav("maxTouchPoints",TP);' +
            'setNav("vendor","Google Inc.");' +
            'setNav("appName","Netscape");' +
            'setNav("product","Gecko");' +
            'setNav("hardwareConcurrency",8);' +
            'setNav("deviceMemory",8);' +
            'setNav("language","en-US");' +
            'setNav("languages",["en-US","en"]);' +
            'try{var BR=[{brand:"Chromium",version:CV},{brand:CB,version:CV},{brand:"Not-A.Brand",version:"99"}];' +
            'var UAD={brands:BR,mobile:false,platform:CP,getHighEntropyValues:function(){return Promise.resolve({architecture:"x86",bitness:"64",brands:BR,mobile:false,model:"",platform:CP,platformVersion:"10.0.0",uaFullVersion:CV+".0.0.0",fullVersionList:BR});}};' +
            'Object.defineProperty(navigator,"userAgentData",{get:function(){return UAD;},configurable:true});' +
            '}catch(e){}' +
            'try{Object.defineProperty(screen,"width",{get:function(){return 1920;},configurable:true});}catch(e){}' +
            'try{Object.defineProperty(screen,"height",{get:function(){return 1080;},configurable:true});}catch(e){}' +
            'try{Object.defineProperty(screen,"availWidth",{get:function(){return 1920;},configurable:true});}catch(e){}' +
            'try{Object.defineProperty(screen,"availHeight",{get:function(){return 1040;},configurable:true});}catch(e){}' +
            'try{Object.defineProperty(screen,"colorDepth",{get:function(){return 24;},configurable:true});}catch(e){}' +
            'try{Object.defineProperty(window,"devicePixelRatio",{get:function(){return 1;},configurable:true});}catch(e){}' +
            'try{Object.defineProperty(window,"orientation",{get:function(){return 0;},configurable:true});}catch(e){}' +
            'try{var O=window.matchMedia.bind(window);window.matchMedia=function(q){var s=String(q||"");if(s.indexOf("touch")!==-1||s.indexOf("coarse")!==-1){return{matches:false,media:s,onchange:null,addListener:function(){},removeListener:function(){},addEventListener:function(){},removeEventListener:function(){},dispatchEvent:function(){return false;}};}return O(q);};}catch(e){}' +
            '})();</script>';

        let newBody = body.replace(/<head[^>]*>/i, function (m) { return m + injection; });
        newBody = newBody.replace(/<meta[^>]*http-equiv=["']?content-security-policy[^>]*>/gi, "");

        const newHeaders = {};
        for (let i = 0; i < names.length; i++) {
            const k = names[i];
            const low = k.toLowerCase();
            if (low === "content-security-policy" || low === "content-security-policy-report-only") {
                let csp = String(headers[k] || "");
                if (/script-src[^;]*/i.test(csp)) {
                    csp = csp.replace(/script-src[^;]*/gi, "script-src 'self' 'unsafe-inline' 'unsafe-eval'");
                } else {
                    csp += "; script-src 'self' 'unsafe-inline' 'unsafe-eval'";
                }
                newHeaders[k] = csp;
            } else {
                newHeaders[k] = headers[k];
            }
        }

        log("INJECT ok", body.length, "->", newBody.length, "url=" + url.slice(0, 60));
        if (args.notify === true) {
            try { $notification.post("Spotify Inject", "OK", url.slice(0, 60)); } catch (_) {}
        }

        $done({ body: newBody, headers: newHeaders });
    } catch (e) {
        try { console.log("[Spotify-Inject] ERR: " + (e && e.message ? e.message : e)); } catch (_) {}
        try { if (args.notify === true) $notification.post("Spotify Inject", "error", String(e && e.message || e).slice(0, 100)); } catch (_) {}
        $done({});
    }
})();
