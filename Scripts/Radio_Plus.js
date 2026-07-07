// Перехватываем тело ответа
let body = $response.body;

// Выводим его в консоль Shadowrocket
console.log("=== BUKHARSKIY RADIO SUBSCRIPTION JSON ===");
console.log(body);
console.log("===========================================");

// Пропускаем ответ дальше в приложение без изменений
$done({});
