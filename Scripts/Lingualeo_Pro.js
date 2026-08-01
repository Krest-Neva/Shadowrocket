if (typeof $response !== 'undefined' && $response.body) {
    try {
        let body = JSON.parse($response.body);
        function getFutureDate() {
            let d = new Date();
            d.setFullYear(d.getFullYear() + 10);
            return d.toISOString().split('T')[0];
        }
        if (body.user) {
            body.user.is_gold = true;
            body.user.isPremium = true;
            body.user.premium = true;
            if (body.user.premium_details) {
                body.user.premium_details.level = 'pro+';
                body.user.premium_details.is_unlimited = 1;
                body.user.premium_details.until = getFutureDate();
            }
            if (body.user.premium_level !== undefined) {
                body.user.premium_level = 'pro+';
            }
            if (body.user.premium_unlimited !== undefined) {
                body.user.premium_unlimited = 1;
            }
            if (body.user.premium_until !== undefined) {
                body.user.premium_until = getFutureDate();
            }
            if (body.user.have_trial !== undefined) {
                body.user.have_trial = 0;
            }
        }
        body.isPremium = true;
        body.premium = true;
        $done({ body: JSON.stringify(body) });
    } catch (e) {
        $done({});
    }
} else {
    $done({});
}
