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
        function modifyUser(user) {
            if (!user) return;
            user.is_gold = true;
            user.meatballs = 99999;
            user.address = 'Minsk';
            user.birth = '2004-01-15';
            user.nickname = 'Pupochek';
            user.fname = 'Kristina';
            user.sname = 'Nevskaya';
            user.xp_title = 'Молодчинка!';
            user.fullname = 'Krest-Neva';
            user.avatar = 'https://i.pinimg.com/736x/97/6e/3d/976e3ddff4cf700b1449f262cf15865f.jpg';
            user.avatar_mini = 'https://i.pinimg.com/736x/97/6e/3d/976e3ddff4cf700b1449f262cf15865f.jpg';
            if (user['>>>premium<<<_details']) {
                user['>>>premium<<<_details'].level = 'pro+';
                user['>>>premium<<<_details'].is_unlimited = 1;
                user['>>>premium<<<_details'].until = getFutureDate();
                modified = true;
            }
            if (user['>>>premium<<<_level'] !== undefined) {
                user['>>>premium<<<_level'] = 'pro+';
                modified = true;
            }
            if (user['>>>premium<<<_unlimited'] !== undefined) {
                user['>>>premium<<<_unlimited'] = 1;
                modified = true;
            }
            if (user['>>>premium<<<_until'] !== undefined) {
                user['>>>premium<<<_until'] = getFutureDate();
                modified = true;
            }
            if (user.premium_details) {
                user.premium_details.level = 'pro+';
                user.premium_details.is_unlimited = 1;
                user.premium_details.until = getFutureDate();
                modified = true;
            }
            if (user.premium_level !== undefined) {
                user.premium_level = 'pro+';
                modified = true;
            }
            if (user.premium_unlimited !== undefined) {
                user.premium_unlimited = 1;
                modified = true;
            }
            if (user.premium_until !== undefined) {
                user.premium_until = getFutureDate();
                modified = true;
            }
            if (user.have_trial !== undefined) {
                user.have_trial = 0;
                modified = true;
            }
            log('Модифицирован user');
        }
        if (url.includes('/mobile/auth') || url.includes('/mergeData')) {
            log('Обработка /mobile/auth или /mergeData');
            if (body.user) {
                modifyUser(body.user);
            }
        } else if (url.includes('/v2/user/profile')) {
            log('Обработка /v2/user/profile');
            if (body.user) {
                modifyUser(body.user);
            }
        } else if (url.includes('/ProcessTraining')) {
            log('Обработка /ProcessTraining');
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
                if (body.data['is>>>Premium<<<'] !== undefined) {
                    body.data['is>>>Premium<<<'] = 1;
                    modified = true;
                }
                if (body.data['>>>premium<<<Discount'] !== undefined) {
                    body.data['>>>premium<<<Discount'] = 50;
                    modified = true;
                }
                if (body.data['>>>premium<<<Expire'] !== undefined) {
                    body.data['>>>premium<<<Expire'] = getFutureDate();
                    modified = true;
                }
                log('Модифицирован /ProcessTraining');
            }
        } else if (url.includes('/getDashboardData')) {
            log('Обработка /getDashboardData');
            if (body['>>>premium<<<Available'] !== undefined) {
                body['>>>premium<<<Available'] = 'premium';
                modified = true;
            }
            if (body.premiumAvailable !== undefined) {
                body.premiumAvailable = 'premium';
                modified = true;
            }
            if (body.paywall_type !== undefined) {
                body.paywall_type = 'none';
                modified = true;
            }
            if (body.stories !== undefined) {
                body.stories = [];
                modified = true;
                log('stories удалены');
            }
            log('Модифицирован /getDashboardData');
        } else if (url.includes('/v2/external-config/public-config/IOS_PREMIUM_CANCEL-BENEFITS')) {
            log('Пропускаем IOS_PREMIUM_CANCEL-BENEFITS');
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
