(function () {
    "use strict";
    const PROFILE = {
        ua: "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/146.0.7680.179 Spotify/1.2.99.317 Safari/537.36",
        secChUa: '"Chromium";v="146", "Google Chrome";v="146", "Not-A.Brand";v="24"',
        secChUaPlatform: '"Windows"',
        secChUaMobile: "?0",
        appPlatform: "WebPlayer"
    };
    let headers = $request.headers || {};
    for (let h in headers) {
        const low = h.toLowerCase();
        if (low === "user-agent") headers[h] = PROFILE.ua;
        if (low === "sec-ch-ua") headers[h] = PROFILE.secChUa;
        if (low === "sec-ch-ua-platform") headers[h] = PROFILE.secChUaPlatform;
        if (low === "sec-ch-ua-mobile") headers[h] = PROFILE.secChUaMobile;
        if (low === "app-platform") headers[h] = PROFILE.appPlatform;
    }
    let url = ($request.url || "").replace(/([?&]platform=)(iphone|android|ipod|web)/gi, "$1web");
    $done({ url, headers });
})();
