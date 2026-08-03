let body = $response.body;

try {
    // Очистка возможных артефактов логирования в ключах JSON
    let cleanBody = body.replace(/>>>premium<<</g, 'premium').replace(/>>>Token<<</g, 'token');
    let obj = JSON.parse(cleanBody);

    // Подмена данных профиля (эндпоинты /mobile/auth и /SetUserProfile)
    if (obj.user) {
        obj.user.is_gold = true;
        
        if (obj.user.premium_details !== undefined) {
            obj.user.premium_details.is_unlimited = 1;
            obj.user.premium_details.level = "premium";
            obj.user.premium_details.until = "2099-12-31T23:59:59";
        }
        
        obj.user.premium_level = "premium";
        obj.user.premium_unlimited = 1;
        obj.user.premium_until = "2099-12-31T23:59:59";
        
        // Дополнительная разблокировка разделов обучения
        if (obj.user.config) {
            for (let key in obj.user.config) {
                obj.user.config[key] = "enable";
            }
        }
    }

    // Подмена статуса в дашборде (/getDashboardData)
    if (obj.premiumAvailable !== undefined) {
        obj.premiumAvailable = "unlimited";
    }

    body = JSON.stringify(obj);
} catch (e) {
    console.log("JSON Parse Error: " + e.message);
}

$done({ body });
