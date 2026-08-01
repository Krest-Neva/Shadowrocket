if (typeof $response !== 'undefined' && $response.body) {
    try {
        let body = JSON.parse($response.body);
        let url = $request ? $request.url : '';
        console.log('[LingualeoPro] Обработка URL: ' + url);

        function getFutureDate() {
            let d = new Date();
            d.setFullYear(d.getFullYear() + 10);
            return d.toISOString().split('T')[0];
        }

        function upgradeRecursive(obj) {
            if (!obj || typeof obj !== 'object') return;
            for (let key in obj) {
                if (!obj.hasOwnProperty(key)) continue;
                let lowerKey = key.toLowerCase();
                if (lowerKey.includes('premium') || lowerKey.includes('gold')) {
                    let val = obj[key];
                    if (typeof val === 'boolean') {
                        obj[key] = true;
                    } else if (typeof val === 'number') {
                        obj[key] = 1;
                    } else if (typeof val === 'string') {
                        if (val === 'none' || val === 'trial') {
                            obj[key] = 'pro+';
                        } else if (val === 'false' || val === '0') {
                            obj[key] = 'true';
                        }
                    }
                }
                if (typeof obj[key] === 'object' && obj[key] !== null) {
                    upgradeRecursive(obj[key]);
                }
            }
        }

        let modified = false;

        if (url.includes('/mobile/auth') || url.includes('/mergeData')) {
            console.log('[LingualeoPro] Обнаружен /mobile/auth или /mergeData');
            if (body.user) {
                body.user.is_gold = true;
                body.user.isPremium = true;
                body.user.premium = true;
                if (body.user.premium_details) {
                    body.user.premium_details.level = 'pro+';
                    body.user.premium_details.is_unlimited = 1;
                    body.user.premium_details.until = getFutureDate();
                }
                if (body.user.premium_level !== undefined) body.user.premium_level = 'pro+';
                if (body.user.premium_unlimited !== undefined) body.user.premium_unlimited = 1;
                if (body.user.premium_until !== undefined) body.user.premium_until = getFutureDate();
                if (body.user.have_trial !== undefined) body.user.have_trial = 0;
                modified = true;
                console.log('[LingualeoPro] Модифицирован user в /mobile/auth или /mergeData');
            }
            body.isPremium = true;
            body.premium = true;
        } else if (url.includes('/getDashboardData')) {
            console.log('[LingualeoPro] Обнаружен /getDashboardData');
            if (body.premiumAvailable !== undefined) {
                body.premiumAvailable = 'premium';
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
            if (body.isPremium !== undefined) {
                body.isPremium = true;
                modified = true;
            }
            if (body.premium !== undefined) {
                body.premium = true;
                modified = true;
            }
            console.log('[LingualeoPro] Модифицирован /getDashboardData');
        } else if (url.includes('/ProcessTraining')) {
            console.log('[LingualeoPro] Обнаружен /ProcessTraining');
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
            console.log('[LingualeoPro] Обнаружен /v2/user/profile');
            if (body.user) {
                body.user.is_gold = true;
                body.user.isPremium = true;
                body.user.premium = true;
                if (body.user.premium_details) {
                    body.user.premium_details.level = 'pro+';
                    body.user.premium_details.is_unlimited = 1;
                    body.user.premium_details.until = getFutureDate();
                }
                modified = true;
                console.log('[LingualeoPro] Модифицирован /v2/user/profile');
            }
        } else if (url.includes('/v2/external-config/public-config/IOS_PREMIUM_CANCEL-BENEFITS')) {
            console.log('[LingualeoPro] Обнаружен IOS_PREMIUM_CANCEL-BENEFITS (пропускаем)');
        } else {
            console.log('[LingualeoPro] URL не соответствует известным эндпоинтам, применяем рекурсивный обход');
        }
        upgradeRecursive(body);

        if (!modified) {
            console.log('[LingualeoPro] Внимание: ни одно известное поле не было изменено, но рекурсивный обход выполнен');
        } else {
            console.log('[LingualeoPro] Скрипт успешно выполнен, ответ изменён');
        }

        $done({ body: JSON.stringify(body) });
    } catch (e) {
        console.log('[LingualeoPro] Ошибка: ' + e);
        $done({});
    }
} else {
    console.log('[LingualeoPro] Нет тела ответа или ответ отсутствует');
    $done({});
}
