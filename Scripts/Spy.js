const url = $request.url;
const method = $request.method;
const reqHeaders = $request.headers;
const reqBody = $request.body;
const hasResponse = typeof $response !== 'undefined';
const resStatus = hasResponse ? $response.status : null;
const resHeaders = hasResponse ? $response.headers : null;
const resBody = hasResponse ? $response.body : null;

function tryParse(data) {
    if (!data) return null;
    try {
        return JSON.parse(data);
    } catch (e) {
        try {
            return JSON.parse(data.replace(/^[0-9]+/, ''));
        } catch (e2) {
            return data;
        }
    }
}

console.log(`\n╔══════════════════════════════════════════════════════════╗`);
console.log(`║ [Spy] ${method} ${url}`);
if (!hasResponse) {
    console.log(`║ [Spy] ⬆️  ИСХОДЯЩИЙ ЗАПРОС (нет ответа)`);
} else {
    console.log(`║ [Spy] ⬆️⬇️  ЗАПРОС И ОТВЕТ (статус: ${resStatus})`);
}
console.log(`╠══════════════════════════════════════════════════════════╣`);

if (reqHeaders) {
    console.log(`║ [Spy] ▶️  ЗАГОЛОВКИ ЗАПРОСА:`);
    for (const [k, v] of Object.entries(reqHeaders)) {
        console.log(`║ [Spy]   ${k}: ${v}`);
    }
}

if (reqBody) {
    const parsed = tryParse(reqBody);
    if (typeof parsed === 'object') {
        console.log(`║ [Spy] ▶️  ТЕЛО ЗАПРОСА (JSON):\n${JSON.stringify(parsed, null, 2).split('\n').map(l => `║ [Spy]   ${l}`).join('\n')}`);
    } else {
        console.log(`║ [Spy] ▶️  ТЕЛО ЗАПРОСА (Raw): ${parsed}`);
    }
} else {
    console.log(`║ [Spy] ▶️  ТЕЛО ЗАПРОСА: пусто`);
}

if (hasResponse) {
    console.log(`╠══════════════════════════════════════════════════════════╣`);
    if (resHeaders) {
        console.log(`║ [Spy] ◀️  ЗАГОЛОВКИ ОТВЕТА:`);
        for (const [k, v] of Object.entries(resHeaders)) {
            console.log(`║ [Spy]   ${k}: ${v}`);
        }
    }
    if (resBody) {
        const parsed = tryParse(resBody);
        if (typeof parsed === 'object') {
            console.log(`║ [Spy] ◀️  ТЕЛО ОТВЕТА (JSON):\n${JSON.stringify(parsed, null, 2).split('\n').map(l => `║ [Spy]   ${l}`).join('\n')}`);
        } else {
            console.log(`║ [Spy] ◀️  ТЕЛО ОТВЕТА (Raw): ${parsed}`);
        }
    } else {
        console.log(`║ [Spy] ◀️  ТЕЛО ОТВЕТА: пусто`);
    }
}

console.log(`╚══════════════════════════════════════════════════════════╝`);
$done({ body: resBody });
