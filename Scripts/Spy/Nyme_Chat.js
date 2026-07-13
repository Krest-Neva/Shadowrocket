const url = $request.url;
const method = $request.method;
const reqBody = $request.body;
const reqHeaders = $request.headers;
const res = typeof $response !== 'undefined' ? $response : null;
const resBody = res ? res.body : null;
const resHeaders = res ? res.headers : null;

function formatData(data) {
    if (!data) return "Пусто";
    try {
        return JSON.stringify(JSON.parse(data), null, 2);
    } catch (e) {
        const cleaned = data.replace(/^[0-9]+/, "");
        if (cleaned.length > 0) {
            try {
                return `[Socket.IO JSON]\n${JSON.stringify(JSON.parse(cleaned), null, 2)}`;
            } catch (err) {
                return `[Raw]\n${data}`;
            }
        }
        return `[Raw]\n${data}`;
    }
}

console.log(`\n[Nymechat-Spy-ALL] ==========================================`);
console.log(`[URL] ${url}`);
console.log(`[METHOD] ${method}`);
console.log(`[REQ HEADERS]\n${JSON.stringify(reqHeaders, null, 2)}`);
console.log(`[REQ BODY]\n${formatData(reqBody)}`);

if (res) {
    console.log(`[RES STATUS] ${res.status}`);
    console.log(`[RES HEADERS]\n${JSON.stringify(resHeaders, null, 2)}`);
    console.log(`[RES BODY]\n${formatData(resBody)}`);
    console.log(`[Nymechat-Spy-ALL] ==========================================\n`);
    $done({ body: resBody });
} else {
    console.log(`[Nymechat-Spy-ALL] ==========================================\n`);
    $done({ body: reqBody });
}
