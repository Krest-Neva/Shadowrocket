(function () {
    if (typeof $response === 'undefined' || !$response.body) {
        $done({});
        return;
    }

    var url = $request ? $request.url : 'UNKNOWN URL';
    var method = $request ? $request.method : 'GET';
    var status = $response.status || 200;
    var rawReqBody = $request && $request.body ? $request.body : null;
    var rawResBody = $response.body;

    var logLines = [];
    logLines.push('+--- [Lingualeo MITM Debug & Unlock] [' + method + '] ' + url + ' (Status: ' + status + ')');

    if (rawReqBody) {
        logLines.push('| > REQ Body: ' + rawReqBody);
    } else {
        logLines.push('| > REQ Body: (empty)');
    }

    var modifiedBodyStr = rawResBody;
    var changes = [];

    try {
        var bodyObj = JSON.parse(rawResBody);

        var futureTimestamp = 2000000000; // 2033 год
        var futureISO = '2033-01-01T00:00:00.000Z';
        var futureDateStr = '2033-01-01';

        function trackChange(path, oldVal, newVal) {
            changes.push(path + ': ' + JSON.stringify(oldVal) + ' => ' + JSON.stringify(newVal));
        }

        function unlockNode(obj, path) {
            if (!obj || typeof obj !== 'object') return;

            if (Array.isArray(obj)) {
                for (var i = 0; i < obj.length; i++) {
                    unlockNode(obj[i], path + '[' + i + ']');
                }
                return;
            }

            for (var key in obj) {
                if (!Object.prototype.hasOwnProperty.call(obj, key)) continue;
                var currentPath = path ? path + '.' + key : key;
                var val = obj[key];

                // 1. Флаги доступа и премиума
                if (/^(is_gold|isGold|is_premium|isPremium|has_premium|hasPremium|has_access|hasAccess|is_available|isAvailable)$/i.test(key)) {
                    if (val !== true && val !== 1) {
                        trackChange(currentPath, val, true);
                        obj[key] = true;
                    }
                }
                // 2. Снятие замков и блокировок
                else if (/^(is_locked|isLocked|locked)$/i.test(key)) {
                    if (val !== false && val !== 0) {
                        trackChange(currentPath, val, false);
                        obj[key] = false;
                    }
                }
                else if (/^(lock_type|lockType|lock_reason|lockReason)$/i.test(key)) {
                    if (val !== null && val !== '') {
                        trackChange(currentPath, val, null);
                        obj[key] = null;
                    }
                }
                // 3. Уровни подписки и типы
                else if (/^(premium_level|premiumLevel)$/i.test(key) || (key === 'level' && typeof val === 'string')) {
                    if (val !== 'premium' && val !== 'gold') {
                        trackChange(currentPath, val, 'premium');
                        obj[key] = 'premium';
                    }
                }
                // 4. Даты истечения
                else if (/^(premium_until|until|expire|expireDate|expires_at)$/i.test(key)) {
                    if (typeof val === 'number' && val !== futureTimestamp) {
                        trackChange(currentPath, val, futureTimestamp);
                        obj[key] = futureTimestamp;
                    } else if (typeof val === 'string' && val !== futureISO && val !== futureDateStr) {
                        var newVal = val.includes('T') ? futureISO : futureDateStr;
                        trackChange(currentPath, val, newVal);
                        obj[key] = newVal;
                    }
                }
                // 5. Лимиты слов и тренировок
                else if (/^(words_limit|limit|max_limit|daily_limit|available_count)$/i.test(key)) {
                    if (typeof val === 'number' && val < 999999) {
                        trackChange(currentPath, val, 999999);
                        obj[key] = 999999;
                    }
                }
                // Рекурсивный проход
                else if (typeof val === 'object' && val !== null) {
                    unlockNode(val, currentPath);
                }
            }
        }

        // Инъекция в объект пользователя, если он есть в корне
        if (bodyObj && bodyObj.user && typeof bodyObj.user === 'object') {
            var u = bodyObj.user;
            if (!u.premium_details) u.premium_details = {};
            u.premium_details.level = 'premium';
            u.premium_details.is_unlimited = 1;
            u.premium_details.until = futureDateStr;
            u.premium_details.type = 'premium';
            u.is_gold = true;
            u.is_premium = true;
            u.subscriptions = [{
                type: 'premium',
                status: 'active',
                level: 'premium',
                until: futureDateStr,
                until_timestamp: futureTimestamp
            }];
            trackChange('user (root)', 'standard profile', 'full premium profile injected');
        }

        unlockNode(bodyObj, '');
        modifiedBodyStr = JSON.stringify(bodyObj);

        logLines.push('| < ORIGINAL RES Body:\n' + rawResBody);
        logLines.push('|');
        logLines.push('| MODIFICATIONS (' + changes.length + ' applied):');
        if (changes.length > 0) {
            changes.forEach(function (c) { logLines.push('|   - ' + c); });
        } else {
            logLines.push('|   (No matching flags found to modify)');
        }
        logLines.push('|');
        logLines.push('| < MODIFIED RES Body:\n' + modifiedBodyStr);

    } catch (e) {
        logLines.push('| [!] PARSE ERROR: ' + e.message);
        logLines.push('| < ORIGINAL RES Body:\n' + rawResBody);
    }

    logLines.push('+---');
    console.log(logLines.join('\n'));

    $done({ body: modifiedBodyStr });
})();
