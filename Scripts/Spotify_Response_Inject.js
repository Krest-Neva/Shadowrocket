(function () {
    "use strict";
    let body = $response.body;
    const injection = `
        Object.defineProperty(navigator, 'platform', { get: function() { return 'Win32'; } });
        Object.defineProperty(navigator, 'userAgent', { get: function() { return 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/146.0.7680.179 Spotify/1.2.99.317 Safari/537.36'; } });
        Object.defineProperty(navigator, 'maxTouchPoints', { get: function() { return 0; } });
        Object.defineProperty(window.screen, 'width', { get: function() { return 1920; } });
        Object.defineProperty(window.screen, 'height', { get: function() { return 1080; } });
    `;
    if (body && typeof body === "string") {
        body = body.replace(/(<head[^>]*>)/i, `$1<script>${injection}</script>`);
    }
    $done({ body });
})();
