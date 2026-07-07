if (typeof $response !== 'undefined' && $response.body) {
    let body = $response.body;
    let url = $request.url;

    try {
        let obj = JSON.parse(body);

        // 1. Обработка основного запроса деталей аккаунта
        if (url.indexOf('user-account-details') !== -1) {
            if (obj.marketingUserType) {
                obj.marketingUserType = "registered premium"; // Пробуем также вариант "premium" ниже, если не сработает
            }
            // Добавляем скрытые свойства на случай, если приложение их ищет
            obj.isPremium = true;
            obj.premium = true;
            obj.premiumUser = true;
        }

        // 2. Обработка запроса настроек пользователя (вторая строка с вашего скриншота)
        if (url.indexOf('user-settings/v1/select') !== -1) {
            // Если сервер возвращает массив или объект настроек, внедряем премиум-флаги
            if (typeof obj === 'object') {
                obj.isPremium = true;
                obj.marketingUserType = "registered premium";
                if (obj.data) {
                    obj.data.isPremium = true;
                    obj.data.marketingUserType = "registered premium";
                }
            }
        }

        $done({ body: JSON.stringify(obj) });
    } catch (e) {
        $done({});
    }
} else {
    $done({});
}
