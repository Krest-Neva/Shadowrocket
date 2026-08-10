(function () {
    var OPT = (function () {
        var def = {
            color: true,
            time: true,
            size: true,
            contentType: true,
            headers: true,
            compactBody: true,
            maxLength: 0,
            highlight: [],
            counter: false,
            ignoreTypes: [],
            ignoreRequestTypes: false,
            maxPrintLength: 2000,
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
            showEmptyBinary: true
        };
        try {
            var raw = typeof $argument !== 'undefined' ? $argument : '{}';
            var arg = JSON.parse(raw);
            var opt = Object.assign({}, def, arg);
            if (opt.compact !== undefined && opt.compactBody === undefined) {
                opt.compactBody = opt.compact;
            }
            return opt;
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

    var decodeBody = function(body) {
        if (!body) return body;
        if (typeof body === 'string') return body;
        if (body instanceof Uint8Array) {
            try { return new TextDecoder('utf-8', { fatal: false }).decode(body); }
            catch(e) { return String.fromCharCode.apply(null, body); }
        }
        if (body instanceof ArrayBuffer) {
            var uint8 = new Uint8Array(body);
            try { return new TextDecoder('utf-8', { fatal: false }).decode(uint8); }
            catch(e) { return String.fromCharCode.apply(null, uint8); }
        }
        return String(body);
    };

    var reqBodyForLog = decodeBody(originalReqBody);
    var resBodyForLog = hasResponse ? decodeBody(originalResBody) : null;

    var getMethodPrefix = function (m) {
        var map = { GET: '[GET]', POST: '[POST]', PUT: '[PUT]', DELETE: '[DEL]', PATCH: '[PATCH]', HEAD: '[HEAD]', OPTIONS: '[OPT]', TRACE: '[TRC]', CONNECT: '[CON]' };
        return map[m] || '[ANY]';
    };

    var getStatusPrefix = function (s) {
        if (!s) return '';
        var code = Math.floor(s / 100);
        return code === 2 ? '[OK]' : code === 3 ? '[REDIR]' : code === 4 ? '[ERR]' : code === 5 ? '[FAIL]' : '[?]';
    };

    var formatSize = function (bytes) {
        if (bytes < 1024) return bytes + ' B';
        if (bytes < 1048576) return (bytes / 1024).toFixed(1) + ' KB';
        return (bytes / 1048576).toFixed(2) + ' MB';
    };

    var safeString = function (value) {
        if (value === null || value === undefined) return '';
        if (typeof value === 'string') return value;
        try { return String(value); } catch (e) { return ''; }
    };

    var normalizeBody = function (body) {
        return safeString(body);
    };

    var escapeRegExp = function (s) {
        return safeString(s).replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
    };

    var highlightText = function (text, words) {
        var result = safeString(text);
        if (!words || !words.length) return result;
        words.forEach(function (w) {
            if (w === undefined || w === null || w === '') return;
            var regex = new RegExp(escapeRegExp(w), 'gi');
            result = result.replace(regex, '>>>$&<<<');
        });
        return result;
    };

    var collapseWhitespace = function (text) {
        return safeString(text).replace(/\s+/g, ' ').trim();
    };

    var tryParse = function (data) {
        if (!data) return null;
        try { return JSON.parse(data); } catch (e) {
            try { return JSON.parse(data.replace(/^[0-9]+/, '')); } catch (e2) { return data; }
        }
    };

    var findHighlightKeys = function (obj, words) {
        var found = [];
        var seen = [];
        var walk = function (o) {
            if (!o || typeof o !== 'object') return;
            for (var si = 0; si < seen.length; si++) {
                if (seen[si] === o) return;
            }
            seen.push(o);
            for (var key in o) {
                if (!Object.prototype.hasOwnProperty.call(o, key)) continue;
                if (words.some(function (w) { return safeString(key).toLowerCase().indexOf(safeString(w).toLowerCase()) !== -1; })) {
                    if (found.indexOf(key) === -1) found.push(key);
                }
                walk(o[key]);
            }
        };
        walk(obj);
        return found;
    };

    var summarizeJsonPaths = function (obj, maxDepth, maxKeys) {
        var out = [];
        var seen = [];
        var walk = function (o, prefix, depth) {
            if (out.length >= maxKeys) return;
            if (!o || typeof o !== 'object') return;
            for (var i = 0; i < seen.length; i++) {
                if (seen[i] === o) return;
            }
            seen.push(o);
            if (Array.isArray(o)) {
                var arrLabel = prefix ? prefix + '[' + o.length + ']' : 'array[' + o.length + ']';
                out.push(arrLabel);
                if (depth > 0 && o.length > 0) {
                    walk(o[0], prefix ? prefix + '[0]' : '[0]', depth - 1);
                }
                return;
            }
            for (var key in o) {
                if (!Object.prototype.hasOwnProperty.call(o, key)) continue;
                var path = prefix ? prefix + '.' + key : key;
                out.push(path);
                if (out.length >= maxKeys) return;
                if (depth > 0) walk(o[key], path, depth - 1);
            }
        };
        walk(obj, '', maxDepth);
        return out;
    };

    var getHeaderValue = function (headers, name) {
        if (!headers) return '';
        var target = name.toLowerCase();
        for (var k in headers) {
            if (!Object.prototype.hasOwnProperty.call(headers, k)) continue;
            if (safeString(k).toLowerCase() === target) return headers[k];
        }
        return '';
    };

    var getContentType = function (headers) {
        return safeString(getHeaderValue(headers, 'Content-Type') || getHeaderValue(headers, 'content-type'));
    };

    var checkIgnored = function (headers, ignoreList) {
        if (!ignoreList || !ignoreList.length || !headers) return false;
        var ct = getContentType(headers).toLowerCase();
        if (!ct) return false;
        for (var i = 0; i < ignoreList.length; i++) {
            var prefix = safeString(ignoreList[i]).toLowerCase();
            if (prefix && ct.indexOf(prefix) === 0) return true;
        }
        return false;
    };

    var isLikelyBinary = function (text, headers) {
        var ct = getContentType(headers).toLowerCase();
        if (/(application\/x-protobuf|application\/octet-stream|application\/zip|application\/gzip|application\/pdf|image\/|audio\/|video\/|font\/)/i.test(ct)) return true;
        var str = safeString(text);
        if (!str) return false;
        var sample = Math.min(str.length, 2048);
        var bad = 0;
        var nul = 0;
        for (var i = 0; i < sample; i++) {
            var code = str.charCodeAt(i);
            if (code === 0) nul++;
            if (code < 9 || (code > 13 && code < 32)) bad++;
        }
        return sample > 0 && (nul > 0 || (bad / sample) > 0.15);
    };

    var printableAscii = function (code) {
        return code >= 32 && code <= 126;
    };

    var asciiPreview = function (text, limit) {
        var s = safeString(text);
        var max = limit > 0 ? Math.min(limit, s.length) : s.length;
        var out = '';
        for (var i = 0; i < max; i++) {
            var code = s.charCodeAt(i);
            out += printableAscii(code) ? s.charAt(i) : '.';
        }
        if (s.length > max) out += '…';
        return out;
    };

    var hexPreview = function (text, limit) {
        var s = safeString(text);
        var max = limit > 0 ? Math.min(limit, s.length) : s.length;
        var out = [];
        for (var i = 0; i < max; i++) {
            var h = s.charCodeAt(i).toString(16);
            if (h.length < 2) h = '0' + h;
            out.push(h);
        }
        if (s.length > max) out.push('…');
        return out.join(' ');
    };

    var collectSnippets = function (text, words, radius, maxMatches) {
        var src = safeString(text);
        if (!src || !words || !words.length) return [];
        var lower = src.toLowerCase();
        var snippets = [];
        for (var i = 0; i < words.length; i++) {
            var word = safeString(words[i]);
            if (!word) continue;
            var needle = word.toLowerCase();
            var from = 0;
            while (snippets.length < maxMatches) {
                var idx = lower.indexOf(needle, from);
                if (idx < 0) break;
                var start = Math.max(0, idx - radius);
                var end = Math.min(src.length, idx + word.length + radius);
                var sn = src.substring(start, end);
                if (snippets.indexOf(sn) === -1) snippets.push(sn);
                from = idx + word.length;
                if (from >= src.length) break;
            }
            if (snippets.length >= maxMatches) break;
        }
        return snippets;
    };

    var summarizeBody = function (body, headers, highlightWords) {
        var text = normalizeBody(body);
        if (!text) return 'пусто';

        var parsed = tryParse(text);
        if (parsed && typeof parsed === 'object') {
            var isArray = Array.isArray(parsed);
            var keys = summarizeJsonPaths(parsed, OPT.maxDepth, OPT.maxObjectKeys);
            var base = isArray ? 'array[' + parsed.length + ']' : 'object{' + keys.join(',') + '}';
            if (isArray && parsed.length > 0) {
                var sample = '';
                try { sample = JSON.stringify(parsed[0]); } catch (e) { sample = ''; }
                if (sample) {
                    if (OPT.maxPrintLength > 0 && sample.length > OPT.maxPrintLength) sample = sample.substring(0, OPT.maxPrintLength) + '…';
                    base += ' sample:' + sample;
                }
            }
            if (highlightWords && highlightWords.length) {
                var found = findHighlightKeys(parsed, highlightWords);
                if (found.length) base += ' highlights:[' + found.join(',') + ']';
            }
            return base;
        }

        if (isLikelyBinary(text, headers)) {
            var parts = [];
            parts.push('binary[len=' + text.length + ']');
            if (highlightWords && highlightWords.length) {
                var snippets = collectSnippets(text, highlightWords, OPT.snippetRadius, OPT.maxSnippets);
                if (snippets.length) {
                    var rendered = [];
                    for (var i = 0; i < snippets.length; i++) {
                        rendered.push('"' + highlightText(snippets[i], highlightWords) + '"');
                    }
                    parts.push('matches:[' + rendered.join(' | ') + ']');
                }
            }
            if (OPT.binaryPreview && OPT.showAscii) {
                parts.push('ascii:"' + highlightText(asciiPreview(text, OPT.binaryPreviewLength), highlightWords || []) + '"');
            }
            if (OPT.showHex) {
                parts.push('hex:' + hexPreview(text, OPT.hexPreviewLength));
            }
            if (OPT.showEmptyBinary && parts.length === 1) {
                parts.push('preview:' + asciiPreview(text, OPT.binaryPreviewLength));
            }
            return parts.join(' ');
        }

        var output = text;
        if (OPT.collapseWhitespace) output = collapseWhitespace(output);
        if (OPT.maxPrintLength > 0 && output.length > OPT.maxPrintLength) {
            output = output.substring(0, OPT.maxPrintLength) + '… (' + (output.length - OPT.maxPrintLength) + ' more)';
        }
        if (highlightWords && highlightWords.length) {
            output = highlightText(output, highlightWords);
        }
        return 'text: ' + output;
    };

    var formatUrlParts = function (rawUrl) {
        var m = safeString(rawUrl).match(/^(https?):\/\/([^\/\?#]+)([^\?#]*)(\?[^#]*)?(#.*)?$/i);
        if (!m) return '';
        var parts = [];
        parts.push('scheme=' + m[1].toLowerCase());
        parts.push('host=' + m[2]);
        parts.push('path=' + (m[3] || '/'));
        if (m[4]) parts.push('query=' + m[4].substring(1));
        if (m[5]) parts.push('hash=' + m[5].substring(1));
        return parts.join(' ');
    };

    var counter = '';
    if (OPT.counter) {
        try {
            var c = $persistentStore.read('spy_counter');
            c = (c && parseInt(c, 10)) ? parseInt(c, 10) + 1 : 1;
            $persistentStore.write('spy_counter', c.toString());
            counter = ' #' + c;
        } catch (e) {}
    }

    var methodPrefix = OPT.color ? getMethodPrefix(method) + ' ' : '';
    var statusPrefix = hasResponse && OPT.color ? ' ' + getStatusPrefix(resStatus) : '';
    var timeStr = OPT.time ? ' [' + new Date().toISOString() + ']' : '';

    var logLines = [];
    var headerStr = '+---' + counter + ' [Spylog] ' + methodPrefix + method + ' ' + url + statusPrefix + timeStr;
    logLines.push(headerStr);

    if (!hasResponse) {
        logLines.push('| [REQ] ИСХОДЯЩИЙ ЗАПРОС');
    } else {
        logLines.push('| [REQ/RES] ЗАПРОС И ОТВЕТ (статус: ' + resStatus + ')');
    }

    if (OPT.showUrlParts) {
        var urlParts = formatUrlParts(url);
        if (urlParts) logLines.push('| URL: ' + urlParts);
    }

    var printHeaders = function (label, headers) {
        if (!OPT.headers || !headers) return;
        var headerParts = [];
        for (var k in headers) {
            if (!Object.prototype.hasOwnProperty.call(headers, k)) continue;
            var value = safeString(headers[k]);
            if (OPT.maxPrintLength > 0 && value.length > OPT.maxPrintLength) {
                value = value.substring(0, OPT.maxPrintLength) + '…';
            }
            headerParts.push(k + ': ' + value);
        }
        if (headerParts.length) {
            logLines.push('| ' + label + ' {' + headerParts.join('; ') + '}');
        }
    };

    var printContentType = function (headers) {
        if (!OPT.contentType || !headers) return;
        var ct = getContentType(headers);
        if (ct) logLines.push('| TYPE: ' + ct);
    };

    var printSize = function (label, body) {
        if (!OPT.size) return;
        var len = body ? safeString(body).length : 0;
        logLines.push('| SIZE ' + label + ': ' + formatSize(len));
    };

    if (hasResponse && checkIgnored(resHeaders, OPT.ignoreTypes)) {
        $done({ body: originalResBody });
        return;
    }
    if (!hasResponse && OPT.ignoreRequestTypes && checkIgnored(reqHeaders, OPT.ignoreTypes)) {
        $done({});
        return;
    }

    if (OPT.showBody) {
        if (OPT.compactBody) {
            logLines.push('| > Body: ' + summarizeBody(reqBodyForLog, reqHeaders, OPT.highlight));
        } else {
            var reqText = normalizeBody(reqBodyForLog);
            if (isLikelyBinary(reqText, reqHeaders)) {
                logLines.push('| > Body: ' + summarizeBody(reqText, reqHeaders, OPT.highlight));
            } else {
                if (OPT.maxLength > 0 && reqText.length > OPT.maxLength) {
                    reqText = reqText.substring(0, OPT.maxLength) + '… (усечено)';
                }
                reqText = highlightText(reqText, OPT.highlight);
                logLines.push('| > Body: ' + reqText);
            }
        }
    } else {
        logLines.push('| > Body: скрыто (showBody=false)');
    }

    if (hasResponse) {
        logLines.push('|');
        printHeaders('< Заголовки ответа:', resHeaders);
        printContentType(resHeaders);
        printSize('(Res)', originalResBody);
        if (OPT.showBody) {
            if (OPT.compactBody) {
                logLines.push('| < Body: ' + summarizeBody(resBodyForLog, resHeaders, OPT.highlight));
            } else {
                var resText = normalizeBody(resBodyForLog);
                if (isLikelyBinary(resText, resHeaders)) {
                    logLines.push('| < Body: ' + summarizeBody(resText, resHeaders, OPT.highlight));
                } else {
                    if (OPT.maxLength > 0 && resText.length > OPT.maxLength) {
                        resText = resText.substring(0, OPT.maxLength) + '… (усечено)';
                    }
                    resText = highlightText(resText, OPT.highlight);
                    logLines.push('| < Body: ' + resText);
                }
            }
        } else {
            logLines.push('| < Body: скрыто (showBody=false)');
        }
    }

    logLines.push('+---');
    console.log(logLines.join('\n'));

    if (hasResponse) {
        $done({ body: originalResBody });
    } else {
        $done({});
    }
})();
