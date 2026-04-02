let url = $request.url;
let body = $response.body;
let headers = $response.headers || {};

// 1. УБИЙЦА ТРЕКЕРОВ (Mocking)
// Вместо обрыва соединения отдаем пустой успешный ответ. Приложения перестают зависать.
const trackers = /appmetrica|startup\.mobile\.yandex\.net\/analytics|mc\.yandex\.(ru|com)\/(watch|metrika)|api\.browser\.yandex\.ru\/uma_proto|log\.strm\.yandex\.ru|adfstat\.yandex\.(ru|com)/i;

if (trackers.test(url)) {
    $done({ 
        status: "HTTP/1.1 200 OK", 
        headers: { "Content-Type": "application/json" }, 
        body: "{}" 
    });
    return;
}

// Если тела ответа нет, просто выходим
if (!body) {
    $done({});
    return;
}

// 2. БЕЛЫЙ СПИСОК (Safety Bypass)
// КРИТИЧЕСКИ ВАЖНО: Не трогаем авторизацию, чаты, карты, оплату и видео-стримы.
const safePaths = /passport|auth|login|token|chat|support|billing|wallet|order|payment|mapkit|static-maps|strm\.yandex|video\.cloud/i;
if (safePaths.test(url)) {
    $done({});
    return;
}

// 3. ПРОВЕРКА ФОРМАТА
// Обрабатываем только текстовые JSON-данные. Картинки и бинарные карты пропускаем.
let contentType = headers["Content-Type"] || headers["content-type"] || "";
if (!contentType.includes("application/json")) {
    $done({});
    return;
}

// 4. ХИРУРГИЧЕСКАЯ ОЧИСТКА РЕКЛАМЫ В ЛЕНТЕ И ПОИСКЕ
try {
    let obj = JSON.parse(body);
    let modified = false;

    function cleanAds(data) {
        if (!data || typeof data !== 'object') return;

        if (Array.isArray(data)) {
            for (let i = data.length - 1; i >= 0; i--) {
                let item = data[i];
                if (item && typeof item === 'object') {
                    // Ищем метки рекламы Яндекса
                    let isAd = item.is_ad === true ||
                               item.is_promoted === true ||
                               item.type === 'ad' ||
                               item.type === 'native_ad' ||
                               item.layout === 'ad' ||
                               item.dataAuto === 'searchIncut' ||
                               (item.widgetName && typeof item.widgetName === 'string' && item.widgetName.toLowerCase().includes('searchincut'));

                    if (isAd) {
                        data.splice(i, 1); // Удаляем только сам рекламный блок
                        modified = true;
                    } else {
                        cleanAds(item); // Идем глубже
                    }
                }
            }
        } else {
            for (let key in data) {
                // Просто проходим по всем вложенным объектам
                cleanAds(data[key]);
            }
        }
    }

    cleanAds(obj);

    if (modified) {
        body = JSON.stringify(obj);
    }
} catch (e) {
    // Если JSON не распарсился, отдаем как есть, чтобы ничего не сломать
}

$done({ body });