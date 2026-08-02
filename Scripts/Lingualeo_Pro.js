if (typeof $response !== 'undefined' && $response.body) {
    try {
        let body = JSON.parse($response.body);
        let url = $request ? $request.url : '';
        let modified = false;

        function getFutureDate() {
            let d = new Date();
            d.setFullYear(d.getFullYear() + 10);
            return d.toISOString().split('T')[0];
        }

        function unlockUser(u) {
            if (!u) return;
            u.is_gold = true;
            u.premium_level = 'premium';
            u.premium_unlimited = 1;
            u.premium_until = getFutureDate();
            u.have_trial = 0;
            if (u.premium_details) {
                u.premium_details.level = 'premium';
                u.premium_details.is_unlimited = 1;
                u.premium_details.until = getFutureDate();
            } else {
                u.premium_details = {
                    level: 'premium',
                    is_unlimited: 1,
                    until: getFutureDate()
                };
            }
        }

        if (body.user) {
            unlockUser(body.user);
            modified = true;
        }

        if (body.data && body.data.user) {
            unlockUser(body.data.user);
            modified = true;
        }

        if (url.includes('/ProcessTraining')) {
            if (body.data) {
                body.data.isPremium = 1;
                body.data.premiumDays = 3650;
                body.data.trialAvailable = 0;
                delete body.data.premiumExpire;
                delete body.data.premiumDiscount;
                modified = true;
            }
        } else if (url.includes('/getDashboardData')) {
            if (body.premiumAvailable !== undefined) {
                body.premiumAvailable = null;
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
