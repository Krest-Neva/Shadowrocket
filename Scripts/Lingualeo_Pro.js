if (typeof $response !== 'undefined' && $response.body) {
    try {
        let arg = {};
        try { arg = JSON.parse($argument || '{}'); } catch (e) {}
        let debug = arg.debug === true;
        let log = debug ? console.log : function() {};
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
        log('[LingualeoPro] Обработка URL: ' + url);
        if (url.indexOf('/mobile/auth') !== -1 || url.indexOf('/mergeData') !== -1) {
            log('[LingualeoPro] Попали в блок /mobile/auth или /mergeData');
            if (body.user) {
                log('[LingualeoPro] body.user существует, начинаем модификацию');
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
                    log('[LingualeoPro] Изменены premium_details');
                }
                if (body.user.premium_level !== undefined) {
                    body.user.premium_level = 'pro+';
                    modified = true;
                    log('[LingualeoPro] Изменен premium_level');
                }
                if (body.user.premium_unlimited !== undefined) {
                    body.user.premium_unlimited = 1;
                    modified = true;
                    log('[LingualeoPro] Изменен premium_unlimited');
                }
                if (body.user.premium_until !== undefined) {
                    body.user.premium_until = getFutureDate();
                    modified = true;
                    log('[LingualeoPro] Изменен premium_until');
                }
                if (body.user.have_trial !== undefined) {
                    body.user.have_trial = 0;
                    modified = true;
                    log('[LingualeoPro] Изменен have_trial');
                }
                if (!modified) {
                    log('[LingualeoPro] Ни одно из полей не было изменено (возможно, поля отсутствуют)');
                }
            } else {
                log('[LingualeoPro] body.user отсутствует!');
            }
        } else if (url.indexOf('/getDashboardData') !== -1) {
            log('[LingualeoPro] Попали в блок /getDashboardData');
            if (body.stories !== undefined) {
                body.stories = [];
                modified = true;
                log('[LingualeoPro] Удалены stories');
            }
        } else if (url.indexOf('/ProcessTraining') !== -1) {
            log('[LingualeoPro] Попали в блок /ProcessTraining');
            if (body.data) {
                if (body.data.isPremium !== undefined) {
                    body.data.isPremium = 1;
                    modified = true;
                    log('[LingualeoPro] Изменен isPremium');
                }
                if (body.data.premiumDiscount !== undefined) {
                    body.data.premiumDiscount = 50;
                    modified = true;
                    log('[LingualeoPro] Изменен premiumDiscount');
                }
                if (body.data.premiumExpire !== undefined) {
                    body.data.premiumExpire = getFutureDate();
                    modified = true;
                    log('[LingualeoPro] Изменен premiumExpire');
                }
                if (body.data.premium_level !== undefined) {
                    body.data.premium_level = 'pro+';
                    modified = true;
                    log('[LingualeoPro] Изменен premium_level в data');
                }
                if (body.data.premium_unlimited !== undefined) {
                    body.data.premium_unlimited = 1;
                    modified = true;
                    log('[LingualeoPro] Изменен premium_unlimited в data');
                }
            }
        } else if (url.indexOf('/v2/user/profile') !== -1) {
            log('[LingualeoPro] Попали в блок /v2/user/profile');
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
            }
        } else if (url.indexOf('/v2/billing/products/') !== -1) {
            log('[LingualeoPro] Попали в блок /v2/billing/products/');
            if (body.products !== undefined) {
                body.products = [{
                    "id": "premium_subscription",
                    "name": "Premium",
                    "productType": "subs",
                    "status": "active",
                    "expires": getFutureDate()
                }];
                modified = true;
                log('[LingualeoPro] Подменены products');
            }
        } else if (url.indexOf('/GetUserProfile') !== -1) {
            log('[LingualeoPro] Попали в блок /GetUserProfile');
            if (body.data) {
                body.data.isPremium = 1;
                body.data.premiumExpire = getFutureDate();
                body.data.premium_level = 'pro+';
                body.data.premium_unlimited = 1;
                modified = true;
                log('[LingualeoPro] Добавлены премиум-поля в data');
            }
        } else if (url.indexOf('/getLearningMain') !== -1) {
            log('[LingualeoPro] Попали в блок /getLearningMain');
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
        } else if (url.indexOf('/getProducts') !== -1) {
            log('[LingualeoPro] Попали в блок /getProducts');
            if (body.campaign && Array.isArray(body.campaign)) {
                body.campaign.forEach(function(c) {
                    c.purchased = true;
                });
                modified = true;
            }
            if (body.purchased === undefined) {
                body.purchased = true;
                modified = true;
            }
        } else if (url.indexOf('/get/chat/messages') !== -1) {
            log('[LingualeoPro] Попали в блок /get/chat/messages');
            if (body.error || body.status === 'error') {
                body = { messages: [] };
                modified = true;
            } else if (body.messages === undefined) {
                body.messages = [];
                modified = true;
            }
        } else if (url.indexOf('/v2/external-config/public-config/') !== -1) {
            log('[LingualeoPro] Попали в блок /v2/external-config/public-config/');
            if (body.content && body.content.is_enabled !== undefined) {
                body.content.is_enabled = true;
                modified = true;
            }
        } else {
            log('[LingualeoPro] URL не соответствует известным эндпоинтам');
        }
        if (modified) {
            log('[LingualeoPro] Ответ изменён');
        } else {
            log('[LingualeoPro] Ничего не изменено');
        }
        $done({ body: JSON.stringify(body) });
    } catch (e) {
        if (debug) console.log('[LingualeoPro] Ошибка: ' + e);
        $done({});
    }
} else {
    $done({});
}
