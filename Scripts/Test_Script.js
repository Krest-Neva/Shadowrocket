// Оставляем след в логах
console.log("---SCRIPT_START---");

// Собираем всю доступную информацию о запросе в одну строку
let requestInfo = "Script triggered!";
if ($request) {
    requestInfo = requestInfo + " URL: " + $request.url;
}

// Выводим информацию в лог
console.log(requestInfo);

// Завершаем скрипт, НЕ изменяя политику
$done({});