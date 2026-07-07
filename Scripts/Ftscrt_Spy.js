// Проверяем, что ответ вообще пришел и в нем есть тело
if (typeof $response !== 'undefined' && $response.body) {
    let body = $response.body;
    
    console.log("=== FATSECRET PROFILE JSON ===");
    console.log(body);
    console.log("==============================");
} else {
    console.log("=== FATSECRET ERROR: NO BODY ===");
}

// Обязательно возвращаем управление приложению
$done({});
