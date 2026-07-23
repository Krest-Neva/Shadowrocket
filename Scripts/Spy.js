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
            showBody: true
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
    var reqBody = $request.body;
    var hasResponse = typeof $response !== 'undefined';
    var resStatus = hasResponse ? $response.status : null;
    var resHeaders = hasResponse ? $response.headers : null;
    var resBody = hasResponse ? $response.body : null;

    var getMethodPrefix = function (m) {
        var map = { GET: '[GET]', POST: '[POST]', PUT: '[PUT]', DELETE: '[DEL]', PATCH: '[PATCH]', HEAD: '[HEAD]', OPTIONS: '[OPT]' };
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

    var tryParse = function (data) {
        if (!data) return null;
        try { return JSON.parse(data); } catch (e) {
            try { return JSON.parse(data.replace(/^[0-9]+/, '')); } catch (e2) { return data; }
        }
    };

    var highlightText = function (text, words) {
        if (!words.length) return text;
        var result = text;
        words.forEach(function (w) {
            var escaped = w.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
            var regex = new RegExp(escaped, 'gi');
            result = result.replace(regex, '>>>$&<<<');
        });
        return result;
    };

    var findHighlightKeys = function (obj, words) {
        var found = new Set();
        var walk = function (o) {
            if (typeof o !== 'object' || o === null) return;
            for (var key in o) {
                if (words.some(function (w) { return key.toLowerCase().includes(w.toLowerCase()); })) found.add(key);
                walk(o[key]);
            }
        };
        walk(obj);
        return Array.from(found);
    };

    var checkIgnored = function (headers, ignoreList) {
        if (!ignoreList.length || !headers) return false;
        var ct = (headers['Content-Type'] || headers['content-type'] || '').toLowerCase();
        return ignoreList.some(function (prefix) { return ct.startsWith(prefix.toLowerCase()); });
    };

    if (hasResponse && checkIgnored(resHeaders, OPT.ignoreTypes)) {
        $done({ body: resBody });
        return;
    }
    if (!hasResponse && OPT.ignoreRequestTypes && checkIgnored(reqHeaders, OPT.ignoreTypes)) {
        $done({});
        return;
    }

    var counter = '';
    if (OPT.counter) {
        try {
            var c = $persistentStore.read('spy_counter');
            c = (c && parseInt(c)) ? parseInt(c) + 1 : 1;
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

    var printHeaders = function (label, headers) {
        if (!OPT.headers || !headers) return;
        var headerParts = [];
        for (var k in headers) {
            headerParts.push(k + ': ' + headers[k]);
        }
        if (headerParts.length) {
            logLines.push('| ' + label + ' {' + headerParts.join('; ') + '}');
        }
    };

    var printContentType = function (headers) {
        if (!OPT.contentType || !headers) return;
        var ct = headers['Content-Type'] || headers['content-type'];
        if (ct) logLines.push('| TYPE: ' + ct);
    };

    var printSize = function (label, body) {
        if (!OPT.size) return;
        var len = body ? body.length : 0;
        logLines.push('| SIZE ' + label + ': ' + formatSize(len));
    };

    var getBodySummary = function (body, highlightWords) {
        if (!body) return 'пусто';
        var parsed = tryParse(body);
        if (typeof parsed === 'object' && parsed !== null) {
            var keys = Object.keys(parsed);
            var isArray = Array.isArray(parsed);
            var length = isArray ? parsed.length : keys.length;
            var summary = (isArray ? 'array[' + length + ']' : 'object{' + keys.join(',') + '}');
            if (isArray && length > 0) {
                var sample = JSON.stringify(parsed[0]);
                if (sample.length > 50) sample = sample.substring(0, 50) + '...';
                summary += ' sample: ' + sample;
            }
            if (highlightWords.length) {
                var found = findHighlightKeys(parsed, highlightWords);
                if (found.length) summary += ' highlights: [' + found.join(',') + ']';
            }
            return summary;
        } else {
            var text = String(parsed);
            if (OPT.maxPrintLength > 0 && text.length > OPT.maxPrintLength) {
                text = text.substring(0, OPT.maxPrintLength) + '... (' + (text.length - OPT.maxPrintLength) + ' more)';
            }
            if (highlightWords.length) {
                text = highlightText(text, highlightWords);
            }
            return 'text: ' + text;
        }
    };

    if (OPT.showBody) {
        if (OPT.compactBody) {
            logLines.push('| > Body: ' + getBodySummary(reqBody, OPT.highlight));
        } else {
            var text = String(reqBody || '');
            if (OPT.maxLength > 0 && text.length > OPT.maxLength) {
                text = text.substring(0, OPT.maxLength) + '... (усечено)';
            }
            text = highlightText(text, OPT.highlight);
            logLines.push('| > Body: ' + text);
        }
    } else {
        logLines.push('| > Body: скрыто (showBody=false)');
    }

    if (hasResponse) {
        logLines.push('|');
        printHeaders('< Заголовки ответа:', resHeaders);
        printContentType(resHeaders);
        printSize('(Res)', resBody);
        if (OPT.showBody) {
            if (OPT.compactBody) {
                logLines.push('| < Body: ' + getBodySummary(resBody, OPT.highlight));
            } else {
                var text = String(resBody || '');
                if (OPT.maxLength > 0 && text.length > OPT.maxLength) {
                    text = text.substring(0, OPT.maxLength) + '... (усечено)';
                }
                text = highlightText(text, OPT.highlight);
                logLines.push('| < Body: ' + text);
            }
        } else {
            logLines.push('| < Body: скрыто (showBody=false)');
        }
    }

    logLines.push('+---');

    console.log(logLines.join('\n'));

    if (hasResponse) {
        $done({ body: resBody });
    } else {
        $done({});
    }
})();
