if (typeof $response !== 'undefined' && $response.body) {
    try {
        let body = JSON.parse($response.body);
        let url = $request ? $request.url : '';
        let arg = {};
        try { arg = JSON.parse($argument || '{}'); } catch (e) {}
        let debug = arg.debug === true;
        function log(msg) { if (debug) console.log('[LingualeoPro] ' + msg); }
        function getFutureDate() {
            let d = new Date();
            d.setFullYear(d.getFullYear() + 10);
            return d.toISOString().split('T')[0];
        }
        let modified = false;
        log('URL: ' + url);
        if (url.includes('/ProcessTraining')) {
            if (body.data) {
                if (body.data.isPremium !== undefined) {
                    body.data.isPremium = 1;
                    modified = true;
                }
                if (body.data.premiumExpire !== undefined) {
                    body.data.premiumExpire = getFutureDate();
                    modified = true;
                }
                if (body.data.trialAvailable !== undefined) {
                    body.data.trialAvailable = 0;
                    modified = true;
                }
                if (body.data.premium_level !== undefined) {
                    body.data.premium_level = 'pro+';
                    modified = true;
                }
                if (body.data.premium_unlimited !== undefined) {
                    body.data.premium_unlimited = 1;
                    modified = true;
                }
                if (body.data.premium_until !== undefined) {
                    body.data.premium_until = getFutureDate();
                    modified = true;
                }
                if (body.data.is_gold !== undefined) {
                    body.data.is_gold = true;
                    modified = true;
                }
                log('Модифицирован /ProcessTraining');
            }
        } else if (url.includes('/mergeData') || url.includes('/v2/user/profile') || url.includes('/mobile/auth')) {
            if (body.user) {
                if (body.user.is_gold !== undefined) {
                    body.user.is_gold = true;
                    modified = true;
                }
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
                log('Модифицирован user');
            }
        } else if (url.includes('/getDashboardData')) {
            if (body.premiumAvailable !== undefined) {
                body.premiumAvailable = 'active';
                modified = true;
            }
            if (body.stories !== undefined) {
                body.stories = [];
                modified = true;
            }
            log('Модифицирован /getDashboardData');
        } else {
            log('URL не соответствует известным эндпоинтам, пропускаем');
        }
        if (modified) {
            log('Скрипт выполнен, ответ изменён');
        } else {
            log('Ни одно поле не было изменено');
        }
        $done({ body: JSON.stringify(body) });
    } catch (e) {
        if (debug) console.log('[LingualeoPro] Ошибка: ' + e);
        $done({});
    }
} else {
    if (debug) console.log('[LingualeoPro] Нет тела ответа');
    $done({});
}
