if (typeof $response !== 'undefined' && $response.body) {
    let body = $response.body;
    try {
        let obj = JSON.parse(body);

        // Функция для рекурсивного поиска и подмены премиум-флагов в любых объектах
        function upgradeToPremium(target) {
            for (let key in target) {
                if (target.hasOwnProperty(key)) {
                    // 1. Изменяем текстовый статус маркетологов
                    if (key === 'marketingUserType') {
                        target[key] = "premium"; // Пробуем чистый "premium" вместо "registered premium"
                    }
                    // 2. Ищем любые булевы флаги премиума и включаем их
                    if (key.toLowerCase().indexOf('premium') !== -1 || key.toLowerCase().indexOf('subscriber') !== -1) {
                        if (typeof target[key] === 'boolean') target[key] = true;
                        if (typeof target[key] === 'string') target[key] = "true";
                        if (typeof target[key] === 'number') target[key] = 1;
                    }
                    // Если внутри есть вложенный объект или массив, идем вглубь
                    if (typeof target[key] === 'object' && target[key] !== null) {
                        upgradeToPremium(target[key]);
                    }
                }
            }
        }

        // Запускаем полную модификацию объекта
        upgradeToPremium(obj);

        // Для надежности жестко пропишем свойства в корень ответа
        obj.marketingUserType = "premium";
        obj.isPremium = true;
        obj.premium = true;

        $done({ body: JSON.stringify(obj) });
    } catch (e) {
        $done({});
    }
} else {
    $done({});
}
