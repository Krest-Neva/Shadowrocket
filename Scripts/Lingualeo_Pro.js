if (typeof $response !== 'undefined' && $response.body) {
    try {
        let arg = {};
        try { arg = JSON.parse($argument || '{}'); } catch (e) {}
        let debug = arg.debug === true;
        let log = debug ? console.log : function() {};
        let url = $request ? $request.url : '';
        let body = null;
        let modified = false;
        function getFutureDate() {
            let d = new Date();
            d.setFullYear(d.getFullYear() + 10);
            return d.toISOString().split('T')[0];
        }
        if (debug) {
            let lines = [];
            lines.push('+--- [LingualeoPro] ' + ($request ? $request.method : 'UNKNOWN') + ' ' + url + ' [' + new Date().toISOString() + ']');
            lines.push('| Статус ответа: ' + $response.status);
            if ($response.body && $response.body.length < 2000) {
                lines.push('| Тело ответа: ' + $response.body);
            } else if ($response.body) {
                lines.push('| Тело ответа: (слишком длинное, усечено) ' + $response.body.substring(0, 500) + '...');
            }
            log(lines.join('\n'));
        }
        if ($response.status === 200) {
            try {
                body = JSON.parse($response.body);
            } catch (e) {
                log('[LingualeoPro] Тело не JSON, пропускаем');
                $done({ body: $response.body });
                return;
            }
        } else if ($response.status === 404 && url.includes('/v2/user/profile')) {
            log('[LingualeoPro] Пропускаем 404 для /v2/user/profile');
            $done({ body: $response.body });
            return;
        } else {
            $done({ body: $response.body });
            return;
        }
        if (url.includes('/mergeData') || url.includes('/mobile/auth')) {
            log('[LingualeoPro] Обработка /mergeData или /mobile/auth');
            if (body.user) {
                body.user.is_gold = true;
                body.user.meatballs = 99999;
                body.user.premium_level = 'pro+';
                body.user.premium_unlimited = 1;
                body.user.premium_until = getFutureDate();
                body.user.have_trial = 0;
                if (body.user.premium_details) {
                    body.user.premium_details.level = 'pro+';
                    body.user.premium_details.is_unlimited = 1;
                    body.user.premium_details.until = getFutureDate();
                } else {
                    body.user.premium_details = {
                        level: 'pro+',
                        is_unlimited: 1,
                        until: getFutureDate()
                    };
                }
                modified = true;
                log('[LingualeoPro] /mergeData или /mobile/auth изменён');
            }
        } else if (url.includes('/ProcessTraining')) {
            log('[LingualeoPro] Обработка /ProcessTraining');
            if (body.data) {
                body.data.isPremium = 1;
                body.data.premiumDiscount = 50;
                body.data.premiumExpire = getFutureDate();
                modified = true;
                log('[LingualeoPro] /ProcessTraining изменён');
            }
        } else if (url.includes('/getDashboardData')) {
            log('[LingualeoPro] Обработка /getDashboardData');
            if (body.stories !== undefined) {
                body.stories = [];
                modified = true;
            }
            if (body.premiumAvailable !== undefined) {
                body.premiumAvailable = 'active';
                modified = true;
            }
            if (body.paywall_type !== undefined) {
                body.paywall_type = 'none';
                modified = true;
            }
            if (modified) log('[LingualeoPro] /getDashboardData изменён');
        } else if (url.includes('/v2/billing/products/')) {
            log('[LingualeoPro] Обработка /v2/billing/products/');
            if (body.products !== undefined) {
                body.products = [{
                    "id": "premium_subscription",
                    "name": "Premium",
                    "productType": "subs_active",
                    "status": "active",
                    "expires": getFutureDate()
                }];
                modified = true;
                log('[LingualeoPro] /v2/billing/products/ изменён');
            }
        } else if (url.includes('/v2/user/profile')) {
            log('[LingualeoPro] Обработка /v2/user/profile');
            if (body.user) {
                body.user.is_gold = true;
                body.user.meatballs = 99999;
                body.user.premium_level = 'pro+';
                body.user.premium_unlimited = 1;
                body.user.premium_until = getFutureDate();
                body.user.have_trial = 0;
                if (body.user.premium_details) {
                    body.user.premium_details.level = 'pro+';
                    body.user.premium_details.is_unlimited = 1;
                    body.user.premium_details.until = getFutureDate();
                } else {
                    body.user.premium_details = {
                        level: 'pro+',
                        is_unlimited: 1,
                        until: getFutureDate()
                    };
                }
                modified = true;
                log('[LingualeoPro] /v2/user/profile изменён');
            }
        } else if (url.includes('/GetUserProfile')) {
            log('[LingualeoPro] Обработка /GetUserProfile');
            if (body.data) {
                body.data.isPremium = 1;
                body.data.premiumExpire = getFutureDate();
                modified = true;
                log('[LingualeoPro] /GetUserProfile изменён');
            }
        } else if (url.includes('/getProducts')) {
            log('[LingualeoPro] Обработка /getProducts');
            if (body.purchased === undefined) {
                body.purchased = true;
                modified = true;
            }
            if (body.campaign && Array.isArray(body.campaign)) {
                body.campaign.forEach(c => { c.purchased = true; });
                modified = true;
            }
            if (modified) log('[LingualeoPro] /getProducts изменён');
        } else if (url.includes('/getLearningMain')) {
            log('[LingualeoPro] Обработка /getLearningMain');
            let sections = ['word', 'audio', 'reading', 'grammar'];
            sections.forEach(function(section) {
                if (body[section] && Array.isArray(body[section])) {
                    body[section].forEach(function(item) {
                        if (item.isPremium !== undefined) {
                            item.isPremium = false;
                            modified = true;
                        }
                    });
                }
            });
            if (modified) log('[LingualeoPro] /getLearningMain изменён (снята блокировка)');
        } else {
            log('[LingualeoPro] URL не обрабатывается: ' + url);
        }
        if (modified) {
            log('[LingualeoPro] Ответ изменён');
        } else {
            log('[LingualeoPro] Ничего не изменено');
        }
        $done({ body: JSON.stringify(body) });
    } catch (e) {
        console.log('[LingualeoPro] Ошибка: ' + e);
        $done({ body: $response.body });
    }
} else {
    $done({});
}
