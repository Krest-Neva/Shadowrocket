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
        if (url.includes('/mobile/auth') || url.includes('/mergeData')) {
            log('Обработка /mobile/auth или /mergeData');
            if (body.user) {
                body.user.is_gold = true;
                body.user.meatballs = 99999;
                body.user.address = 'Minsk';
                body.user.birth = '2004-01-15';
                body.user.nickname = 'Pupochek';
                body.user.fname = 'Kristina';
                body.user.sname = 'Nevskaya';
                body.user.xp_title = 'Молодчинка!';
                body.user.fullname = 'Krest-Neva';
                body.user.avatar = 'https://i.pinimg.com/736x/97/6e/3d/976e3ddff4cf700b1449f262cf15865f.jpg';
                body.user.avatar_mini = 'https://i.pinimg.com/736x/97/6e/3d/976e3ddff4cf700b1449f262cf15865f.jpg';
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
            log('Обработка /getDashboardData');
            if (body.stories && Array.isArray(body.stories) && body.stories.length > 0) {
                body.stories.forEach(function(story) {
                    if (story.autoShow !== undefined) story.autoShow = 0;
                    if (story.stories && Array.isArray(story.stories)) {
                        story.stories.forEach(function(item) {
                            if (item.button !== undefined) item.button = 0;
                            if (item.buttonText !== undefined) item.buttonText = '';
                            if (item.buttonContent !== undefined) item.buttonContent = '';
                        });
                    }
                });
                modified = true;
                log('stories скрыты (autoShow=0, кнопки отключены)');
            }
            log('Модифицирован /getDashboardData (paywall скрыт)');
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
                log('Модифицирован /ProcessTraining');
            }
        } else if (url.includes('/v2/user/profile')) {
            log('Обработка /v2/user/profile');
            if (body.user) {
                body.user.is_gold = true;
                body.user.meatballs = 99999;
                body.user.address = 'Minsk';
                body.user.birth = '2004-01-15';
                body.user.nickname = 'Pupochek';
                body.user.fname = 'Kristina';
                body.user.sname = 'Nevskaya';
                body.user.xp_title = 'Молодчинка!';
                body.user.fullname = 'Krest-Neva';
                body.user.avatar = 'https://i.pinimg.com/736x/97/6e/3d/976e3ddff4cf700b1449f262cf15865f.jpg';
                body.user.avatar_mini = 'https://i.pinimg.com/736x/97/6e/3d/976e3ddff4cf700b1449f262cf15865f.jpg';
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
                log('Модифицирован /v2/user/profile');
            }
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
