(function () {
    var OPT = (function () {
        var def = {
            color: true,
            time: true,
            size: true,
            contentType: true,
            headers: true,
            compactBody: false,
            maxLength: 0,
            highlight: ["his_max_score", "history_data", "premium", "token"],
            counter: false,
            ignoreTypes: ["image/", "font/", "text/css"],
            ignoreRequestTypes: false,
            maxPrintLength: 3000,
            showBody: true,
            showUrlParts: true,
            collapseWhitespace: true,
            binaryPreview: true,
            binaryPreviewLength: 240,
            hexPreviewLength: 96,
            maxDepth: 4,
            maxObjectKeys: 60,
            maxSnippets: 5,
            snippetRadius: 48,
            showHex: false,
            showAscii: true,
            showEmptyBinary: true,
            repairMojibake: true,
            patchBlockBlast: true,
            blockBlastScore: 9999999999
        };
        try {
            var raw = typeof $argument !== 'undefined' ? $argument : '{}';
            return Object.assign({}, def, JSON.parse(raw));
        } catch (e) {
            return def;
        }
    })();

    var url = $request.url;
    var method = $request.method;
    var reqHeaders = $request.headers;
    var hasResponse = typeof $response !== 'undefined';
    var resStatus = hasResponse ? $response.status : null;
    var resHeaders = hasResponse ? $response.headers : null;
    var originalReqBody = $request.body;
    var originalResBody = hasResponse ? $response.body : null;

    var safeString = function (v) {
        if (v === null || v === undefined) return '';
        if (typeof v === 'string') return v;
        try { return String(v); } catch (e) { return ''; }
    };

    var bytesToUtf8 = function (bytes) {
        try {
            if (typeof TextDecoder !== 'undefined') {
                return new TextDecoder('utf-8', { fatal: false }).decode(bytes);
            }
        } catch (e1) {}
        try {
            var bin = '';
            for (var i = 0; i < bytes.length; i++) bin += String.fromCharCode(bytes[i] & 0xff);
            return decodeURIComponent(escape(bin));
        } catch (e2) {
            var out = '';
            for (var j = 0; j < bytes.length; j++) out += String.fromCharCode(bytes[j] & 0xff);
            return out;
        }
    };

    var utf8Encode = function (str) {
        try {
            if (typeof TextEncoder !== 'undefined') return new TextEncoder().encode(str);
        } catch (e) {}
        var arr = [];
        for (var i = 0; i < str.length; i++) {
            var c = str.charCodeAt(i);
            if (c < 0x80) arr.push(c);
            else if (c < 0x800) arr.push(0xC0 | (c >> 6), 0x80 | (c & 0x3F));
            else arr.push(0xE0 | (c >> 12), 0x80 | ((c >> 6) & 0x3F), 0x80 | (c & 0x3F));
        }
        return new Uint8Array(arr);
    };

    var decodeBody = function (body) {
        if (body === null || body === undefined) return '';
        if (typeof body === 'string') return body;
        if (body instanceof Uint8Array) return bytesToUtf8(body);
        if (body instanceof ArrayBuffer) return bytesToUtf8(new Uint8Array(body));
        if (body && body.buffer instanceof ArrayBuffer) {
            try { return bytesToUtf8(new Uint8Array(body.buffer, body.byteOffset || 0, body.byteLength)); } catch (e) {}
        }
        return safeString(body);
    };

    var reqBodyForLog = decodeBody(originalReqBody);
    var resBodyForLog = hasResponse ? decodeBody(originalResBody) : null;

    var patchApplied = false;
    var patchedString = null;
    var patchedBytes = null;
    var patchDetail = '';

    var scoreValue = OPT.blockBlastScore;
    if (typeof scoreValue === 'string' && /^-?\d+$/.test(scoreValue)) {
        scoreValue = parseInt(scoreValue, 10);
    }

    var shouldPatch = hasResponse && OPT.patchBlockBlast &&
        /hella-game-gateway-server\.afafb\.com\/ug\/get_universal_data/i.test(url);

    if (shouldPatch && resBodyForLog) {
        try {
            var pd = JSON.parse(resBodyForLog);
            if (pd && pd.history_data) {
                pd.history_data.his_max_score = scoreValue;
                pd.history_data.his_active_days = 999999;
                pd.history_data.day_7_game_time = 9999999;
                pd.history_data.device_type = "Nokia 3310";
                pd.history_data.day_7_game_avg_score = scoreValue;
                pd.history_data.day_1_game_avg_score = scoreValue;
                patchedString = JSON.stringify(pd);
                patchedBytes = utf8Encode(patchedString);
                patchApplied = true;
                patchDetail = 'his_max_score=' + scoreValue + ', his_active_days=999999, day_7_game_time=9999999, device_type="Nokia 3310", avg_scores=' + scoreValue;
            }
        } catch (e) {
            patchDetail = 'failed: ' + e.message;
        }
    }

    var getMethodPrefix = function (m) {
        var map = { GET: '[GET]', POST: '[POST]', PUT: '[PUT]', DELETE: '[DEL]', PATCH: '[PATCH]', HEAD: '[HEAD]', OPTIONS: '[OPT]', CONNECT: '[CON]' };
        return map[m] || '[ANY]';
    };
    var getStatusPrefix = function (s) {
        if (!s) return '';
        var c = Math.floor(s / 100);
        return c === 2 ? '[OK]' : c === 3 ? '[REDIR]' : c === 4 ? '[ERR]' : c === 5 ? '[FAIL]' : '[?]';
    };
    var formatSize = function (b) {
        if (b < 1024) return b + ' B';
        if (b < 1048576) return (b / 1024).toFixed(1) + ' KB';
        return (b / 1048576).toFixed(2) + ' MB';
    };
    var collapseWS = function (t) { return safeString(t).replace(/\s+/g, ' ').trim(); };
    var getHeader = function (h, n) {
        if (!h) return '';
        var l = n.toLowerCase();
        for (var k in h) if (Object.prototype.hasOwnProperty.call(h, k) && k.toLowerCase() === l) return h[k];
        return '';
    };
    var getCT = function (h) { return safeString(getHeader(h, 'Content-Type')); };
    var checkIgnored = function (h, list) {
        if (!list || !list.length || !h) return false;
        var ct = getCT(h).toLowerCase();
        if (!ct) return false;
        for (var i = 0; i < list.length; i++) {
            if (ct.indexOf(safeString(list[i]).toLowerCase()) === 0) return true;
        }
        return false;
    };
    var isLikelyBinary = function (t, h) {
        var ct = getCT(h).toLowerCase();
        if (/(protobuf|octet-stream|zip|gzip|pdf|image\/|audio\/|video\/|font\/)/i.test(ct)) return true;
        var s = safeString(t);
        if (!s) return false;
        var sample = Math.min(s.length, 2048), bad = 0, nul = 0;
        for (var i = 0; i < sample; i++) {
            var c = s.charCodeAt(i);
            if (c === 0) nul++;
            if (c < 9 || (c > 13 && c < 32)) bad++;
        }
        return sample > 0 && (nul > 0 || (bad / sample) > 0.15);
    };
    var asciiPreview = function (t, lim) {
        var s = safeString(t), max = lim > 0 ? Math.min(lim, s.length) : s.length, out = '';
        for (var i = 0; i < max; i++) {
            var c = s.charCodeAt(i);
            out += (c >= 32 && c <= 126) ? s.charAt(i) : '.';
        }
        if (s.length > max) out += '…';
        return out;
    };
    var formatUrlParts = function (raw) {
        var m = safeString(raw).match(/^(https?):\/\/([^\/\?#]+)([^\?#]*)(\?[^#]*)?(#.*)?$/i);
        if (!m) return '';
        var p = ['scheme=' + m[1].toLowerCase(), 'host=' + m[2], 'path=' + (m[3] || '/')];
        if (m[4]) p.push('query=' + m[4].substring(1));
        return p.join(' ');
    };

    if (hasResponse && checkIgnored(resHeaders, OPT.ignoreTypes)) {
        $done({ body: originalResBody });
        return;
    }

    var counter = '';
    if (OPT.counter) {
        try {
            var c = $persistentStore.read('spy_counter');
            c = (c && parseInt(c, 10)) ? parseInt(c, 10) + 1 : 1;
            $persistentStore.write('spy_counter', c.toString());
            counter = ' #' + c;
        } catch (e) {}
    }

    var mp = OPT.color ? getMethodPrefix(method) + ' ' : '';
    var sp = hasResponse && OPT.color ? ' ' + getStatusPrefix(resStatus) : '';
    var tstr = OPT.time ? ' [' + new Date().toISOString() + ']' : '';
    var lines = [];
    var headerTag = patchApplied ? ', PATCHED' : '';
    lines.push('+---' + counter + ' [Spylog] ' + mp + method + ' ' + url + sp + tstr);
    if (!hasResponse) lines.push('| [REQ] ИСХОДЯЩИЙ ЗАПРОС');
    else lines.push('| [REQ/RES] ЗАПРОС И ОТВЕТ (статус: ' + resStatus + headerTag + ')');

    if (OPT.showUrlParts) {
        var up = formatUrlParts(url);
        if (up) lines.push('| URL: ' + up);
    }

    if (OPT.headers && resHeaders) {
        var hp = [];
        for (var k in resHeaders) {
            if (!Object.prototype.hasOwnProperty.call(resHeaders, k)) continue;
            var v = safeString(resHeaders[k]);
            if (OPT.maxPrintLength > 0 && v.length > OPT.maxPrintLength) v = v.substring(0, OPT.maxPrintLength) + '…';
            hp.push(k + ': ' + v);
        }
        if (hp.length) lines.push('| < Заголовки ответа: {' + hp.join('; ') + '}');
    }
    if (OPT.contentType && resHeaders) {
        var ct2 = getCT(resHeaders);
        if (ct2) lines.push('| TYPE: ' + ct2);
    }
    if (OPT.size) {
        var finalSize = patchApplied ? patchedString.length : (resBodyForLog ? resBodyForLog.length : 0);
        lines.push('| SIZE (Res): ' + formatSize(finalSize) + (patchApplied ? ' (patched)' : ''));
    }

    if (OPT.showBody) {
        var reqLog = safeString(reqBodyForLog);
        if (isLikelyBinary(reqLog, reqHeaders)) {
            lines.push('| > Body: binary[len=' + reqLog.length + '] ascii:"' + asciiPreview(reqLog, OPT.binaryPreviewLength) + '"');
        } else if (reqLog) {
            var rl = OPT.collapseWhitespace ? collapseWS(reqLog) : reqLog;
            if (OPT.maxLength > 0 && rl.length > OPT.maxLength) rl = rl.substring(0, OPT.maxLength) + '…';
            lines.push('| > Body: ' + rl);
        } else {
            lines.push('| > Body: пусто');
        }

        if (hasResponse) {
            var resLog = safeString(patchApplied ? patchedString : resBodyForLog);
            if (isLikelyBinary(resLog, resHeaders)) {
                lines.push('| < Body: binary[len=' + resLog.length + '] ascii:"' + asciiPreview(resLog, OPT.binaryPreviewLength) + '"');
            } else if (resLog) {
                var rl2 = OPT.collapseWhitespace ? collapseWS(resLog) : resLog;
                if (OPT.maxLength > 0 && rl2.length > OPT.maxLength) rl2 = rl2.substring(0, OPT.maxLength) + '…';
                lines.push('| < Body: ' + rl2);
            } else {
                lines.push('| < Body: пусто');
            }
        }
    }

    if (patchApplied) {
        lines.push('| 🔧 PATCH: ' + patchDetail);
    } else if (patchDetail) {
        lines.push('| ⚠️ PATCH ' + patchDetail);
    }

    lines.push('+---');
    console.log(lines.join('\n'));

    if (hasResponse) {
        if (patchApplied) {
            if (typeof originalResBody === 'string') {
                $done({ body: patchedString });
            } else {
                $done({ body: patchedBytes });
            }
        } else {
            $done({ body: originalResBody });
        }
    } else {
        $done({});
    }
})();
