if (typeof $response !== 'undefined' && $response.body) {
    try {
        let body = JSON.parse($response.body);
        let url = $request ? $request.url : '';
        console.log('[LingualeoPro] URL: ' + url);
        function getFutureDate() {
            let d = new Date();
            d.setFullYear(d.getFullYear() + 10);
            return d.toISOString().split('T')[0];
        }
        let modified = false;
        if (url.includes('/mobile/auth') || url.includes('/mergeData')) {
            console.log('[LingualeoPro] Обработка /mobile/auth или /mergeData');
            if (body.user) {
                body.user.is_gold = true;
                if (body.user.premium_details) {
                    body.user.premium_details.level = 'pro+';
                    body.user.premium_details.is_unlimited = 1;
                    body.user.premium_details.until = getFutureDate();
                    modified = true;
                }
                if (body.user.premium_level !== undefined) {
                    body.user.premium_level = 'pro+';
                    modified = true;
                }
                if (body.user.premium_unlimited !== undefined) {
                    body.user.premium_unlimited = 1;
                    modified = true;
                }
                if (body.user.premium_until !== undefined) {
                    body.user.premium_until = getFutureDate();
                    modified = true;
                }
                if (body.user.have_trial !== undefined) {
                    body.user.have_trial = 0;
                    modified = true;
                }
                console.log('[LingualeoPro] Модифицирован user');
            }
        } else if (url.includes('/getDashboardData')) {
            console.log('[LingualeoPro] Обработка /getDashboardData');
            if (body.premiumAvailable !== undefined) {
                body.premiumAvailable = 'trial';
                modified = true;
            }
            if (body.tasks && Array.isArray(body.tasks)) {
                body.tasks.forEach(task => {
                    if (task.isPremium !== undefined) {
                        task.isPremium = true;
                        modified = true;
                    }
                });
            }
            console.log('[LingualeoPro] Модифицирован /getDashboardData');
        } else if (url.includes('/ProcessTraining')) {
            console.log('[LingualeoPro] Обработка /ProcessTraining');
            if (body.data) {
                if (body.data.isPremium !== undefined) {
                    body.data.isPremium = 1;
                    modified = true;
                }
                if (body.data.premiumDiscount !== undefined) {
                    body.data.premiumDiscount = 50;
                    modified = true;
                }
                if (body.data.premiumExpire !== undefined) {
                    body.data.premiumExpire = getFutureDate();
                    modified = true;
                }
                console.log('[LingualeoPro] Модифицирован /ProcessTraining');
            }
        } else if (url.includes('/v2/user/profile')) {
            console.log('[LingualeoPro] Обработка /v2/user/profile');
            if (body.user) {
                body.user.is_gold = true;
                if (body.user.premium_details) {
                    body.user.premium_details.level = 'pro+';
                    body.user.premium_details.is_unlimited = 1;
                    body.user.premium_details.until = getFutureDate();
                    modified = true;
                }
                if (body.user.premium_level !== undefined) {
                    body.user.premium_level = 'pro+';
                    modified = true;
                }
                if (body.user.premium_unlimited !== undefined) {
                    body.user.premium_unlimited = 1;
                    modified = true;
                }
                if (body.user.premium_until !== undefined) {
                    body.user.premium_until = getFutureDate();
                    modified = true;
                }
                console.log('[LingualeoPro] Модифицирован /v2/user/profile');
            }
        } else if (url.includes('/v2/external-config/public-config/IOS_PREMIUM_CANCEL-BENEFITS')) {
            console.log('[LingualeoPro] Пропускаем IOS_PREMIUM_CANCEL-BENEFITS');
        } else {
            console.log('[LingualeoPro] URL не соответствует известным эндпоинтам, пропускаем');
        }
        if (modified) {
            console.log('[LingualeoPro] Скрипт выполнен, ответ изменён');
        } else {
            console.log('[LingualeoPro] Ни одно поле не было изменено');
        }
        $done({ body: JSON.stringify(body) });
    } catch (e) {
        console.log('[LingualeoPro] Ошибка: ' + e);
        $done({});
    }
} else {
    console.log('[LingualeoPro] Нет тела ответа');
    $done({});
}
