if (typeof $response !== 'undefined' && $response.body) {
    try {
        let body = JSON.parse($response.body);
        let url = $request ? $request.url : '';
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
        if (url.includes('/mobile/auth') || url.includes('/mergeData')) {
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
            }
            body.isPremium = true;
            body.premium = true;
        } else if (url.includes('/getDashboardData')) {
            if (body.premiumAvailable !== undefined) body.premiumAvailable = 'premium';
            if (body.tasks && Array.isArray(body.tasks)) {
                body.tasks.forEach(task => {
                    if (task.isPremium !== undefined) task.isPremium = true;
                });
            }
            if (body.isPremium !== undefined) body.isPremium = true;
            if (body.premium !== undefined) body.premium = true;
        } else if (url.includes('/ProcessTraining')) {
            if (body.data) {
                if (body.data.isPremium !== undefined) body.data.isPremium = 1;
                if (body.data.premiumDiscount !== undefined) body.data.premiumDiscount = 50;
                if (body.data.premiumExpire !== undefined) body.data.premiumExpire = getFutureDate();
            }
        } else if (url.includes('/v2/user/profile')) {
            if (body.user) {
                body.user.is_gold = true;
                body.user.isPremium = true;
                body.user.premium = true;
                if (body.user.premium_details) {
                    body.user.premium_details.level = 'pro+';
                    body.user.premium_details.is_unlimited = 1;
                    body.user.premium_details.until = getFutureDate();
                }
            }
        }
        upgradeRecursive(body);
        $done({ body: JSON.stringify(body) });
    } catch (e) {
        $done({});
    }
} else {
    $done({});
}
