const url = $request.url;
const responseBody = $response.body;

console.log(`\n[Nymechat-Spy] -------------------------------`);
console.log(`[Nymechat-Spy] URL запроса: ${url}`);
console.log(`[Nymechat-Spy] Статус ответа: ${$response.status}`);

if (responseBody) {
    try {
        const jsonObj = JSON.parse(responseBody);
        console.log(`[Nymechat-Spy] Тип данных: JSON`);
        console.log(`[Nymechat-Spy] Тело ответа:\n${JSON.stringify(jsonObj, null, 2)}`);
    } catch (e) {
        console.log(`[Nymechat-Spy] Тип данных: Текст/Сырые данные`);
        console.log(`[Nymechat-Spy] Тело ответа:\n${responseBody}`);
    }
} else {
    console.log(`[Nymechat-Spy] Тело ответа пустое.`);
}
console.log(`[Nymechat-Spy] -------------------------------\n`);
$done({ body: responseBody });