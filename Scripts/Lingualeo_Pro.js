if (typeof $response !== 'undefined' && $response.body) {
    try {
        let body = JSON.parse($response.body);
        let url = $request ? $request.url : '';
        function getFutureDate() {
            let d = new Date();
            d.setFullYear(d.getFullYear() + 10);
            return d.toISOString().split('T')[0];
        }
        let modified = false;
        if (url.includes('/mobile/auth') || url.includes('/mergeData') || url.includes('/v2/user/profile') || url.includes('/GetUserProfile')) {
            if (body.user) {
                body.user.is_gold = true;
                body.user.premium_level = 'premium';
                body.user.premium_unlimited = 0;
                body.user.premium_until = getFutureDate();
                body.user.have_trial = 0;
                if (!body.user.premium_details) {
                    body.user.premium_details = {};
                }
                body.user.premium_details.level = 'premium';
                body.user.premium_details.is_unlimited = 0;
                body.user.premium_details.until = getFutureDate();
                if (body.user.is_premium !== undefined) {
                    body.user.is_premium = true;
                } else {
                    body.user.is_premium = true;
                }
                modified = true;
            }
        } else if (url.includes('/ProcessTraining')) {
            if (body.data) {
                body.data.isPremium = 1;
                body.data.premiumDays = 365;
                body.data.trialAvailable = 0;
                if (body.data.premiumDiscount !== undefined) {
                    delete body.data.premiumDiscount;
                }
                if (body.data.premiumExpire !== undefined) {
                    delete body.data.premiumExpire;
                }
                modified = true;
            }
        } else if (url.includes('/getDashboardData')) {
            if (body.premiumAvailable !== undefined) {
                body.premiumAvailable = null;
                modified = true;
            }
            if (body.tasks && Array.isArray(body.tasks)) {
                for (let task of body.tasks) {
                    if (task.isPremium !== undefined) {
                        task.isPremium = false;
                    }
                }
                modified = true;
            }
        } else if (url.includes('/getLearningMain')) {
            if (body.data && Array.isArray(body.data)) {
                for (let section of body.data) {
                    const types = ['audio', 'word', 'reading'];
                    for (let type of types) {
                        if (section[type] && Array.isArray(section[type])) {
                            for (let item of section[type]) {
                                if (item.isPremium !== undefined) {
                                    item.isPremium = false;
                                }
                            }
                        }
                    }
                }
                modified = true;
            }
        }
        if (modified) {
            $done({ body: JSON.stringify(body) });
        } else {
            $done({});
        }
    } catch (e) {
        $done({});
    }
} else {
    $done({});
}
