if (typeof $response !== 'undefined') {
    try {
        let arg = {};
        try { arg = JSON.parse($argument || '{}'); } catch (e) {}
        let debug = arg.debug === true;
        let log = debug ? console.log : function() {};
        console.log('[LingualeoPro] Скрипт запущен, URL: ' + ($request ? $request.url : 'нет URL') + ', статус: ' + $response.status);
        let url = $request ? $request.url : '';
        let resStatus = $response.status;
        let body = null;
        let modified = false;
        function getFutureDate() {
            let d = new Date();
            d.setFullYear(d.getFullYear() + 10);
            return d.toISOString().split('T')[0];
        }
        function injectPremium(obj) {
            if (typeof obj !== 'object' || obj === null) return false;
            let changed = false;
            let keys = Object.keys(obj);
            for (let key of keys) {
                let lowerKey = key.toLowerCase();
                if (lowerKey.includes('premium') || lowerKey.includes('purchased') || lowerKey.includes('paywall') || lowerKey.includes('trial')) {
                    if (lowerKey.includes('level')) { obj[key] = 'pro+'; changed = true; }
                    else if (lowerKey.includes('unlimited')) { obj[key] = 1; changed = true; }
                    else if (lowerKey.includes('until') || lowerKey.includes('expire')) { obj[key] = getFutureDate(); changed = true; }
                    else if (lowerKey.includes('available')) { obj[key] = 'active'; changed = true; }
                    else if (lowerKey.includes('paywall_type')) { obj[key] = 'none'; changed = true; }
                    else if (lowerKey.includes('have_trial')) { obj[key] = 0; changed = true; }
                    else if (lowerKey === 'ispremium' || lowerKey === 'premium' || lowerKey === 'is_premium') { obj[key] = true; changed = true; }
                    else if (lowerKey === 'purchased') { obj[key] = true; changed = true; }
                    else if (lowerKey === 'status' && obj[key] === 'trial') { obj[key] = 'active'; changed = true; }
                    else if (lowerKey === 'producttype' && obj[key] === 'subs') { obj[key] = 'subs_active'; changed = true; }
                }
                if (typeof obj[key] === 'object' && obj[key] !== null) {
                    if (injectPremium(obj[key])) changed = true;
                }
            }
            return changed;
        }
        if (debug) {
            let reqHeaders = $request ? $request.headers : {};
            let reqBody = $request ? $request.body : null;
            let resHeaders = $response.headers;
            let resBody = $response.body;
            let lines = [];
            lines.push('+--- [LingualeoPro Debug] ' + ($request ? $request.method : 'UNKNOWN') + ' ' + url + ' [' + new Date().toISOString() + ']');
            lines.push('| [REQ] ЗАПРОС');
            if (reqHeaders) {
                let h = Object.keys(reqHeaders).map(k => k + ': ' + reqHeaders[k]).join('; ');
                lines.push('| > Headers: {' + h + '}');
            }
            if (reqBody) {
                let bodyStr = reqBody.length > 2000 ? reqBody.substring(0, 2000) + '... (усечено)' : reqBody;
                lines.push('| > Body: ' + bodyStr);
            } else {
                lines.push('| > Body: (пусто)');
            }
            lines.push('|');
            lines.push('| [RES] ОТВЕТ (статус: ' + resStatus + ')');
            if (resHeaders) {
                let h = Object.keys(resHeaders).map(k => k + ': ' + resHeaders[k]).join('; ');
                lines.push('| < Headers: {' + h + '}');
            }
            if (resBody) {
                let bodyStr = resBody.length > 2000 ? resBody.substring(0, 2000) + '... (усечено)' : resBody;
                lines.push('| < Body: ' + bodyStr);
            } else {
                lines.push('| < Body: (пусто)');
            }
            lines.push('+---');
            log(lines.join('\n'));
        }
        if (resStatus === 200 || resStatus === 404 || resStatus === 422) {
            try {
                body = JSON.parse($response.body);
            } catch (e) {
                body = null;
            }
        }
        if (body) {
            if (injectPremium(body)) {
                modified = true;
                log('[LingualeoPro] Внедрены премиум-поля в ответ');
            }
            if (Array.isArray(body.products)) {
                body.products = [{
                    "id": "premium_subscription",
                    "name": "Premium",
                    "productType": "subs_active",
                    "status": "active",
                    "expires": getFutureDate()
                }];
                modified = true;
                log('[LingualeoPro] Массив products заменён на активную подписку');
            }
            if (body.campaign && Array.isArray(body.campaign)) {
                body.campaign.forEach(c => { c.purchased = true; });
                modified = true;
                log('[LingualeoPro] Добавлен флаг purchased в кампании');
            }
            if (body.data && Array.isArray(body.data)) {
                body.data.forEach(item => { if (item.isPremium !== undefined) { item.isPremium = false; } });
                modified = true;
                log('[LingualeoPro] Снята блокировка isPremium в data');
            }
            if (body.stories !== undefined) {
                body.stories = [];
                modified = true;
                log('[LingualeoPro] Удалены stories');
            }
        } else {
            if (resStatus === 404 && url.includes('/v2/user/profile')) {
                body = { user: { is_gold: true, meatballs: 99999, address: 'Minsk', birth: '2004-01-15', nickname: 'Pupochek', fname: 'Kristina', sname: 'Nevskaya', xp_title: 'Молодчинка!', fullname: 'Krest-Neva', avatar: 'https://i.pinimg.com/736x/97/6e/3d/976e3ddff4cf700b1449f262cf15865f.jpg', avatar_mini: 'https://i.pinimg.com/736x/97/6e/3d/976e3ddff4cf700b1449f262cf15865f.jpg' } };
                injectPremium(body.user);
                injectPremium(body);
                modified = true;
                log('[LingualeoPro] Создан новый user для /v2/user/profile');
            } else if (resStatus === 422 && url.includes('/v2/analytics/auth')) {
                body = { status: 'ok' };
                modified = true;
                log('[LingualeoPro] Исправлен ответ /v2/analytics/auth');
            }
        }
        if (modified) {
            console.log('[LingualeoPro] Ответ изменён');
        } else {
            console.log('[LingualeoPro] Ничего не изменено');
        }
        if (body) {
            $done({ body: JSON.stringify(body) });
        } else {
            $done({});
        }
    } catch (e) {
        console.log('[LingualeoPro] Ошибка: ' + e);
        $done({});
    }
} else {
    console.log('[LingualeoPro] Нет ответа');
    $done({});
}
