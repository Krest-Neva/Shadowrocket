const url = $request.url;
const reqBody = $request.body;
const resBody = typeof $response !== 'undefined' ? $response.body : null;

console.log(`\n[Nymechat-Spy] ==========================================`);
console.log(`[Nymechat-Spy] URL: ${url}`);
console.log(`[Nymechat-Spy] Метод: ${$request.method}`);

if (reqBody) {
    try {
        const reqJson = JSON.parse(reqBody);
        console.log(`[Nymechat-Spy] ---> ТЕЛО ЗАПРОСА (JSON):\n${JSON.stringify(reqJson, null, 2)}`);
    } catch (e) {
        console.log(`[Nymechat-Spy] ---> ТЕЛО ЗАПРОСА (Raw):\n${reqBody}`);
    }
} else {
    console.log(`[Nymechat-Spy] ---> ТЕЛО ЗАПРОСА: Пусто`);
}

if (resBody) {
    try {
        const resJson = JSON.parse(resBody);
        console.log(`[Nymechat-Spy] <--- ТЕЛО ОТВЕТА (JSON):\n${JSON.stringify(resJson, null, 2)}`);
    } catch (e) {
        console.log(`[Nymechat-Spy] <--- ТЕЛО ОТВЕТА (Raw):\n${resBody}`);
    }
} else if (typeof $response !== 'undefined') {
    console.log(`[Nymechat-Spy] <--- ТЕЛО ОТВЕТА: Пусто (Статус: ${$response.status})`);
}

console.log(`[Nymechat-Spy] ==========================================\n`);

if (typeof $response !== 'undefined') {
    $done({ body: resBody });
} else {
    $done({ body: reqBody });
}