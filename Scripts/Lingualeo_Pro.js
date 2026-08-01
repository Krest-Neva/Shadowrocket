if (typeof $response !== 'undefined' && $response.body) {
    try {
        let arg = {};
        try { arg = JSON.parse($argument || '{}'); } catch (e) {}
        let debug = arg.debug === true;
        let log = debug ? console.log : function() {};
        console.log('[LingualeoPro] Скрипт запущен, URL: ' + ($request ? $request.url : 'нет URL'));
        if (debug) {
            let url = $request ? $request.url : '';
            let method = $request ? $request.method : 'UNKNOWN';
            let reqHeaders = $request ? $request.headers : {};
            let reqBody = $request ? $request.body : null;
            let resStatus = $response.status;
            let resHeaders = $response.headers;
            let resBody = $response.body;
            let lines = [];
            lines.push('+--- [LingualeoPro Debug] ' + method + ' ' + url + ' [' + new Date().toISOString() + ']');
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
        let body = JSON.parse($response.body);
        let url = $request ? $request.url : '';
        let modified = false;
        function getFutureDate() {
            let d = new Date();
            d.setFullYear(d.getFullYear() + 10);
            return d.toISOString().split('T')[0];
        }
        function injectPremium(obj) {
            if (typeof obj !== 'object' || obj === null) return false;
            let changed = false;
            if (obj.isPremium !== undefined) { obj.isPremium = 1; changed = true; }
            if (obj.premium !== undefined) { obj.premium = true; changed = true; }
            if (obj.premium_level !== undefined) { obj.premium_level = 'pro+'; changed = true; }
            if (obj.premium_unlimited !== undefined) { obj.premium_unlimited = 1; changed = true; }
            if (obj.premium_until !== undefined) { obj.premium_until = getFutureDate(); changed = true; }
            if (obj.premiumExpire !== undefined) { obj.premiumExpire = getFutureDate(); changed = true; }
            if (obj.premiumAvailable !== undefined) { obj.premiumAvailable = 'active'; changed = true; }
            if (obj.paywall_type !== undefined) { obj.paywall_type = 'none'; changed = true; }
            if (obj.have_trial !== undefined) { obj.have_trial = 0; changed = true; }
            if (obj.premium_details !== undefined) {
                obj.premium_details.level = 'pro+';
                obj.premium_details.is_unlimited = 1;
                obj.premium_details.until = getFutureDate();
                changed = true;
            } else {
                obj.premium_details = { level: 'pro+', is_unlimited: 1, until: getFutureDate() };
                changed = true;
            }
            return changed;
        }
        if (url.includes('/mergeData') || url.includes('/mobile/auth')) {
            console.log('[LingualeoPro] Попали в /mergeData или /mobile/auth');
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
                if (injectPremium(body.user)) modified = true;
                if (injectPremium(body)) modified = true;
                console.log('[LingualeoPro] /mergeData или /mobile/auth модифицированы');
            }
        } else if (url.includes('/getDashboardData')) {
            console.log('[LingualeoPro] Попали в /getDashboardData');
            if (body.stories !== undefined) { body.stories = []; modified = true; }
            if (injectPremium(body)) modified = true;
            console.log('[LingualeoPro] /getDashboardData модифицирован');
        } else if (url.includes('/ProcessTraining')) {
            console.log('[LingualeoPro] Попали в /ProcessTraining');
            if (body.data) {
                if (injectPremium(body.data)) modified = true;
                if (injectPremium(body)) modified = true;
                console.log('[LingualeoPro] /ProcessTraining модифицирован');
            }
        } else if (url.includes('/v2/user/profile')) {
            console.log('[LingualeoPro] Попали в /v2/user/profile');
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
                if (injectPremium(body.user)) modified = true;
                if (injectPremium(body)) modified = true;
                console.log('[LingualeoPro] /v2/user/profile модифицирован');
            } else {
                body = { user: { is_gold: true, meatballs: 99999, address: 'Minsk', birth: '2004-01-15', nickname: 'Pupochek', fname: 'Kristina', sname: 'Nevskaya', xp_title: 'Молодчинка!', fullname: 'Krest-Neva', avatar: 'https://i.pinimg.com/736x/97/6e/3d/976e3ddff4cf700b1449f262cf15865f.jpg', avatar_mini: 'https://i.pinimg.com/736x/97/6e/3d/976e3ddff4cf700b1449f262cf15865f.jpg' } };
                injectPremium(body.user);
                injectPremium(body);
                modified = true;
                console.log('[LingualeoPro] /v2/user/profile создан с нуля');
            }
        } else if (url.includes('/v2/billing/products/')) {
            console.log('[LingualeoPro] Попали в /v2/billing/products/');
            if (body.products !== undefined) {
                body.products = [{ "id": "premium_subscription", "name": "Premium", "productType": "subs", "status": "active", "expires": getFutureDate() }];
                modified = true;
                console.log('[LingualeoPro] /v2/billing/products/ подменён');
            }
        } else if (url.includes('/GetUserProfile')) {
            console.log('[LingualeoPro] Попали в /GetUserProfile');
            if (body.data) {
                if (injectPremium(body.data)) modified = true;
                if (injectPremium(body)) modified = true;
                console.log('[LingualeoPro] /GetUserProfile модифицирован');
            }
        } else if (url.includes('/getLearningMain')) {
            console.log('[LingualeoPro] Попали в /getLearningMain');
            let sections = ['word', 'audio', 'reading', 'grammar'];
            sections.forEach(function(section) {
                if (body[section] && Array.isArray(body[section])) {
                    body[section].forEach(function(item) {
                        if (item.isPremium !== undefined) { item.isPremium = false; modified = true; }
                    });
                }
            });
            if (modified) console.log('[LingualeoPro] /getLearningMain модифицирован');
        } else if (url.includes('/getProducts')) {
            console.log('[LingualeoPro] Попали в /getProducts');
            if (body.campaign && Array.isArray(body.campaign)) {
                body.campaign.forEach(function(c) { c.purchased = true; });
                modified = true;
            }
            if (body.purchased === undefined) { body.purchased = true; modified = true; }
            if (modified) console.log('[LingualeoPro] /getProducts модифицирован');
        } else if (url.includes('/get/chat/messages')) {
            console.log('[LingualeoPro] Попали в /get/chat/messages');
            if (body.error || body.status === 'error') {
                body = { messages: [] };
                modified = true;
            } else if (body.messages === undefined) {
                body.messages = [];
                modified = true;
            }
            if (modified) console.log('[LingualeoPro] /get/chat/messages модифицирован');
        } else if (url.includes('/v2/external-config/public-config/')) {
            console.log('[LingualeoPro] Попали в /v2/external-config/public-config/');
            if (body.content && body.content.is_enabled !== undefined) {
                body.content.is_enabled = true;
                modified = true;
                console.log('[LingualeoPro] Конфиг модифицирован');
            }
        } else if (url.includes('/v2/user/subscription')) {
            console.log('[LingualeoPro] Попали в /v2/user/subscription');
            body = { "status": "active", "level": "pro+", "expires": getFutureDate(), "is_unlimited": true };
            modified = true;
            console.log('[LingualeoPro] /v2/user/subscription подменён');
        } else if (url.includes('/v2/billing/active')) {
            console.log('[LingualeoPro] Попали в /v2/billing/active');
            body = { "active": true, "product_id": "premium", "expires": getFutureDate() };
            modified = true;
            console.log('[LingualeoPro] /v2/billing/active подменён');
        } else if (url.includes('/v2/billing/subscription')) {
            console.log('[LingualeoPro] Попали в /v2/billing/subscription');
            body = { "status": "active", "plan": "premium", "expires": getFutureDate() };
            modified = true;
            console.log('[LingualeoPro] /v2/billing/subscription подменён');
        } else if (url.includes('/v2/payments/status')) {
            console.log('[LingualeoPro] Попали в /v2/payments/status');
            body = { "has_active_subscription": true, "subscription": { "product": "premium", "expires": getFutureDate() } };
            modified = true;
            console.log('[LingualeoPro] /v2/payments/status подменён');
        } else if (url.includes('/v2/premium/status')) {
            console.log('[LingualeoPro] Попали в /v2/premium/status');
            body = { "is_premium": true, "premium_level": "pro+", "premium_until": getFutureDate() };
            modified = true;
            console.log('[LingualeoPro] /v2/premium/status подменён');
        } else if (url.includes('/user/status')) {
            console.log('[LingualeoPro] Попали в /user/status');
            if (body.user) {
                if (injectPremium(body.user)) modified = true;
                if (injectPremium(body)) modified = true;
                console.log('[LingualeoPro] /user/status модифицирован');
            }
        } else if (url.includes('/v2/account/info')) {
            console.log('[LingualeoPro] Попали в /v2/account/info');
            if (body.user) {
                if (injectPremium(body.user)) modified = true;
                if (injectPremium(body)) modified = true;
                console.log('[LingualeoPro] /v2/account/info модифицирован');
            }
        } else {
            console.log('[LingualeoPro] URL не соответствует известным эндпоинтам: ' + url);
        }
        if (modified) {
            console.log('[LingualeoPro] Ответ изменён');
        } else {
            console.log('[LingualeoPro] Ничего не изменено');
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
