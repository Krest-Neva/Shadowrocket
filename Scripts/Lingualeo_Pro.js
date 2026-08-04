if (typeof $response !== 'undefined' && $response.body) {
    try {
        let body = JSON.parse($response.body);
        let url = $request ? $request.url : '';
        function getFutureDate() {
            let d = new Date();
            d.setFullYear(d.getFullYear() + 10);
            return d.toISOString().split('T')[0];
        }
        function getFutureISO() {
            let d = new Date();
            d.setFullYear(d.getFullYear() + 10);
            return d.toISOString();
        }
        let modified = false;
        if (url.includes('/mobile/auth') || url.includes('/mergeData') || url.includes('/v2/user/profile')) {
            if (body.user) {
                body.user.is_gold = true;
                if (body.user.premium_details) {
                    body.user.premium_details.level = 'premium';
                    body.user.premium_details.is_unlimited = 0;
                    body.user.premium_details.until = getFutureDate();
                } else {
                    body.user.premium_details = {
                        level: 'premium',
                        is_unlimited: 0,
                        until: getFutureDate()
                    };
                }
                if (body.user.premium_level !== undefined) {
                    body.user.premium_level = 'premium';
                } else {
                    body.user.premium_level = 'premium';
                }
                if (body.user.premium_unlimited !== undefined) {
                    body.user.premium_unlimited = 0;
                } else {
                    body.user.premium_unlimited = 0;
                }
                if (body.user.premium_until !== undefined) {
                    body.user.premium_until = getFutureDate();
                } else {
                    body.user.premium_until = getFutureDate();
                }
                if (body.user.have_trial !== undefined) {
                    body.user.have_trial = 0;
                } else {
                    body.user.have_trial = 0;
                }
                modified = true;
            }
        } else if (url.includes('/ProcessTraining')) {
            if (body.data) {
                if (body.data.isPremium !== undefined) {
                    body.data.isPremium = 1;
                } else {
                    body.data.isPremium = 1;
                }
                if (body.data.premiumDays !== undefined) {
                    body.data.premiumDays = 365;
                } else {
                    body.data.premiumDays = 365;
                }
                if (body.data.premiumExpire !== undefined) {
                    delete body.data.premiumExpire;
                }
                if (body.data.premiumDiscount !== undefined) {
                    delete body.data.premiumDiscount;
                }
                if (body.data.trialAvailable !== undefined) {
                    body.data.trialAvailable = 0;
                } else {
                    body.data.trialAvailable = 0;
                }
                modified = true;
            }
        } else if (url.includes('/getDashboardData')) {
            if (body.tasks && Array.isArray(body.tasks)) {
                for (let task of body.tasks) {
                    task.isPremium = false;
                }
                modified = true;
            }
            if (body.premiumAvailable !== undefined) {
                body.premiumAvailable = null;
                modified = true;
            }
        } else if (url.includes('/getLearningMain')) {
            if (body.data && Array.isArray(body.data)) {
                for (let section of body.data) {
                    if (section.audio && Array.isArray(section.audio)) {
                        for (let item of section.audio) {
                            item.isPremium = false;
                        }
                    }
                    if (section.word && Array.isArray(section.word)) {
                        for (let item of section.word) {
                            item.isPremium = false;
                        }
                    }
                    if (section.reading && Array.isArray(section.reading)) {
                        for (let item of section.reading) {
                            item.isPremium = false;
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
