const url = $request.url;
const reqBody = $request.body;
const resBody = typeof $response !== 'undefined' ? $response.body : null;

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

console.log(`\n[Nymechat-Spy] ==========================================`);
console.log(`[Nymechat-Spy] URL: ${url}`);
console.log(`[Nymechat-Spy] Метод: ${$request.method}`);

if (reqBody) {
    const parsed = tryParse(reqBody);
    if (typeof parsed === 'object') {
        console.log(`[Nymechat-Spy] ---> ТЕЛО ЗАПРОСА (JSON):\n${JSON.stringify(parsed, null, 2)}`);
    } else {
        console.log(`[Nymechat-Spy] ---> ТЕЛО ЗАПРОСА (Raw):\n${parsed}`);
    }
} else {
    console.log(`[Nymechat-Spy] ---> ТЕЛО ЗАПРОСА: Пусто`);
}

if (resBody) {
    const parsed = tryParse(resBody);
    if (typeof parsed === 'object') {
        console.log(`[Nymechat-Spy] <--- ТЕЛО ОТВЕТА (JSON):\n${JSON.stringify(parsed, null, 2)}`);
    } else {
        console.log(`[Nymechat-Spy] <--- ТЕЛО ОТВЕТА (Raw):\n${parsed}`);
    }
} else if (typeof $response !== 'undefined') {
    console.log(`[Nymechat-Spy] <--- ТЕЛО ОТВЕТА: Пусто (Статус: ${$response.status})`);
}

console.log(`[Nymechat-Spy] ==========================================\n`);

$done({ body: resBody });
