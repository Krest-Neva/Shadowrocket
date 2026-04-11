// Получаем аргумент, переданный из модуля
let params = JSON.parse($argument);
let block = params.BlockGoogle;

if (block === true) {
    // Блокируем запрос
    $done({ policy: "REJECT" });
} else {
    // Отправляем через прокси (или можно заменить на "Proxy")
    $done({ policy: "PROXY" });
}