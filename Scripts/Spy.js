(function () {
    const OPT = (() => {
        const def = {
            color: true,
            time: true,
            size: true,
            contentType: true,
            headers: true,
            compact: false,
            maxLength: 0,
            highlight: [],
            counter: false,
            ignoreTypes: [],
            ignoreRequestTypes: false
        };
        try {
            const raw = typeof $argument !== 'undefined' ? $argument : '{}';
            const arg = JSON.parse(raw);
            return Object.assign({}, def, arg);
        } catch (e) {
            return def;
        }
    })();

    const url = $request.url;
    const method = $request.method;
    const reqHeaders = $request.headers;
    const reqBody = $request.body;
    const hasResponse = typeof $response !== 'undefined';
    const resStatus = hasResponse ? $response.status : null;
    const resHeaders = hasResponse ? $response.headers : null;
    const resBody = hasResponse ? $response.body : null;

    const getMethodPrefix = (m) => {
        const map = { GET: '[GET]', POST: '[POST]', PUT: '[PUT]', DELETE: '[DEL]', PATCH: '[PATCH]', HEAD: '[HEAD]', OPTIONS: '[OPT]' };
        return map[m] || '[ANY]';
    };

    const getStatusPrefix = (s) => {
        if (!s) return '';
        const code = Math.floor(s / 100);
        return code === 2 ? '[OK]' : code === 3 ? '[REDIR]' : code === 4 ? '[ERR]' : code === 5 ? '[FAIL]' : '[?]';
    };

    const formatSize = (bytes) => {
        if (bytes < 1024) return `${bytes} B`;
        if (bytes < 1048576) return `${(bytes / 1024).toFixed(1)} KB`;
        return `${(bytes / 1048576).toFixed(2)} MB`;
    };

    const tryParse = (data) => {
        if (!data) return null;
        try { return JSON.parse(data); } catch (e) {
            try { return JSON.parse(data.replace(/^[0-9]+/, '')); } catch (e2) { return data; }
        }
    };

    const highlightText = (text, words) => {
        if (!words.length) return text;
        let result = text;
        words.forEach(w => {
            const escaped = w.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
            const regex = new RegExp(escaped, 'gi');
            result = result.replace(regex, '>>>$&<<<');
        });
        return result;
    };

    const findHighlightKeys = (obj, words) => {
        const found = new Set();
        const walk = (o) => {
            if (typeof o !== 'object' || o === null) return;
            for (const key of Object.keys(o)) {
                if (words.some(w => key.toLowerCase().includes(w.toLowerCase()))) found.add(key);
                walk(o[key]);
            }
        };
        walk(obj);
        return [...found];
    };

    const checkIgnored = (headers, ignoreList) => {
        if (!ignoreList.length || !headers) return false;
        const ct = (headers['Content-Type'] || headers['content-type'] || '').toLowerCase();
        return ignoreList.some(prefix => ct.startsWith(prefix.toLowerCase()));
    };

    // Проверка игнорируемых типов – если совпало, завершаем скрипт
    if (hasResponse && checkIgnored(resHeaders, OPT.ignoreTypes)) {
        $done({ body: resBody });
        return; // теперь return внутри функции IIFE
    }
    if (!hasResponse && OPT.ignoreRequestTypes && checkIgnored(reqHeaders, OPT.ignoreTypes)) {
        $done({});
        return;
    }

    let counter = '';
    if (OPT.counter) {
        try {
            let c = $persistentStore.read('spy_counter');
            c = (c && parseInt(c)) ? parseInt(c) + 1 : 1;
            $persistentStore.write('spy_counter', c.toString());
            counter = ` #${c}`;
        } catch (e) {}
    }

    const methodPrefix = OPT.color ? getMethodPrefix(method) + ' ' : '';
    const statusPrefix = hasResponse && OPT.color ? ' ' + getStatusPrefix(resStatus) : '';
    const timeStr = OPT.time ? `\n| TIME: ${new Date().toISOString()}` : '';

    console.log(`+---${counter} [Spy] ${methodPrefix}${method} ${url}${statusPrefix}${timeStr}`);

    if (!hasResponse) {
        console.log(`| [REQ] ИСХОДЯЩИЙ ЗАПРОС`);
    } else {
        console.log(`| [REQ/RES] ЗАПРОС И ОТВЕТ (статус: ${resStatus})`);
    }

    const printHeaders = (label, headers) => {
        if (!OPT.headers || !headers) return;
        console.log(`| ${label}`);
        for (const [k, v] of Object.entries(headers)) {
            console.log(`|   ${k}: ${v}`);
        }
    };

    const printContentType = (headers) => {
        if (!OPT.contentType || !headers) return;
        const ct = headers['Content-Type'] || headers['content-type'];
        if (ct) console.log(`| TYPE: ${ct}`);
    };

    const printSize = (label, body) => {
        if (!OPT.size) return;
        const len = body ? body.length : 0;
        console.log(`| SIZE ${label}: ${formatSize(len)}`);
    };

    const printBody = (label, body, highlightWords) => {
        if (!body) {
            console.log(`| ${label}: пусто`);
            return;
        }
        const parsed = tryParse(body);
        if (OPT.compact && typeof parsed === 'object') {
            const keys = Object.keys(parsed);
            console.log(`| ${label} (ключи): [${keys.join(', ')}]`);
            if (highlightWords.length) {
                const found = findHighlightKeys(parsed, highlightWords);
                if (found.length) console.log(`| KEYS FOUND: ${found.join(', ')}`);
            }
            return;
        }
        if (typeof parsed === 'object') {
            let text = JSON.stringify(parsed, null, 2);
            if (OPT.maxLength > 0 && text.length > OPT.maxLength) {
                text = text.substring(0, OPT.maxLength) + '... (усечено)';
            }
            text = highlightText(text, highlightWords);
            console.log(`| ${label} (JSON):`);
            text.split('\n').forEach(line => console.log(`|   ${line}`));
            if (highlightWords.length) {
                const found = findHighlightKeys(parsed, highlightWords);
                if (found.length) console.log(`| KEYS FOUND: ${found.join(', ')}`);
            }
        } else {
            let text = String(parsed);
            if (OPT.maxLength > 0 && text.length > OPT.maxLength) {
                text = text.substring(0, OPT.maxLength) + '... (усечено)';
            }
            text = highlightText(text, highlightWords);
            console.log(`| ${label} (Raw): ${text}`);
        }
    };

    printHeaders('> Заголовки запроса:', reqHeaders);
    printContentType(reqHeaders);
    printSize('(Req)', reqBody);
    printBody('> Тело запроса', reqBody, OPT.highlight);

    if (hasResponse) {
        console.log(`|`);
        printHeaders('< Заголовки ответа:', resHeaders);
        printContentType(resHeaders);
        printSize('(Res)', resBody);
        printBody('< Тело ответа', resBody, OPT.highlight);
    }

    console.log(`+---`);

    if (hasResponse) {
        $done({ body: resBody });
    } else {
        $done({});
    }
})();
