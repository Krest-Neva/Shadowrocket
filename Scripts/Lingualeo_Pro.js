if (typeof $response !== 'undefined' && $response.body) {
    try {
        let url = $request ? $request.url : '';
        let body = JSON.parse($response.body);
        let now = new Date();
        let futureDate = new Date(now.getFullYear() + 10, now.getMonth(), now.getDate());
        let dateStr = futureDate.toISOString().split('T')[0];
        let isoStr = futureDate.toISOString();
        let timestamp = Math.floor(futureDate.getTime() / 1000);

        let logEntries = [];

        function logChange(path, oldVal, newVal) {
            logEntries.push(path + ": " + JSON.stringify(oldVal) + " => " + JSON.stringify(newVal));
        }

        function deepUnlock(obj, path = '') {
            if (!obj || typeof obj !== 'object') return;

            if (Array.isArray(obj)) {
                for (let i = 0; i < obj.length; i++) {
                    deepUnlock(obj[i], path + '[' + i + ']');
                }
                return;
            }

            for (let key in obj) {
                if (!Object.prototype.hasOwnProperty.call(obj, key)) continue;
                let currentPath = path ? path + '.' + key : key;
                let val = obj[key];

                if (key === 'is_gold' || key === 'isGold' || key === 'is_premium' || key === 'isPremium' || key === 'has_premium' || key === 'hasPremium') {
                    if (val !== true && val !== 1) {
                        logChange(currentPath, val, true);
                        obj[key] = true;
                    }
                } else if (key === 'is_locked' || key === 'isLocked' || key === 'locked') {
                    if (val !== false && val !== 0) {
                        logChange(currentPath, val, false);
                        obj[key] = false;
                    }
                } else if (key === 'has_access' || key === 'hasAccess' || key === 'is_available' || key === 'isAvailable') {
                    if (val !== true && val !== 1) {
                        logChange(currentPath, val, true);
                        obj[key] = true;
                    }
                } else if (key === 'lock_type' || key === 'lock_reason' || key === 'lockType' || key === 'lockReason') {
                    if (val !== null) {
                        logChange(currentPath, val, null);
                        obj[key] = null;
                    }
                } else if (key === 'premium_level' || key === 'premiumLevel' || key === 'level') {
                    if (typeof val === 'string' && val !== 'premium') {
                        logChange(currentPath, val, 'premium');
                        obj[key] = 'premium';
                    }
                } else if (key === 'premium_until' || key === 'premiumUntil' || key === 'until' || key === 'expire' || key === 'expireDate') {
                    if (typeof val === 'number') {
                        if (val !== timestamp) {
                            logChange(currentPath, val, timestamp);
                            obj[key] = timestamp;
                        }
                    } else if (typeof val === 'string') {
                        let newDate = val.includes('T') ? isoStr : dateStr;
                        if (val !== newDate) {
                            logChange(currentPath, val, newDate);
                            obj[key] = newDate;
                        }
                    }
                } else if (key === 'is_unlimited' || key === 'isUnlimited' || key === 'unlimited') {
                    if (val !== 1 && val !== true) {
                        logChange(currentPath, val, 1);
                        obj[key] = 1;
                    }
                } else if (typeof val === 'object' && val !== null) {
                    deepUnlock(val, currentPath);
                }
            }
        }

        if (body.user && typeof body.user === 'object') {
            if (!body.user.premium_details) {
                body.user.premium_details = {};
            }
            body.user.premium_details.level = 'premium';
            body.user.premium_details.is_unlimited = 1;
            body.user.premium_details.until = dateStr;
            body.user.premium_details.type = 'premium';

            body.user.subscriptions = [{
                type: 'premium',
                status: 'active',
                level: 'premium',
                until: dateStr,
                until_timestamp: timestamp
            }];
            logEntries.push("user.premium_details & subscriptions injected");
        }

        deepUnlock(body);

        console.log("=== [Lingualeo MITM Log] ===");
        console.log("URL: " + url);
        if (logEntries.length > 0) {
            console.log("Modifications:\n" + logEntries.join("\n"));
        } else {
            console.log("No fields modified for this endpoint.");
        }
        console.log("=== [End Log] ===");

        $done({ body: JSON.stringify(body) });
    } catch (e) {
        console.log("[Lingualeo MITM Error]: " + e.message);
        $done({});
    }
} else {
    $done({});
}
