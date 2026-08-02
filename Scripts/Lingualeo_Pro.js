if (typeof $response !== 'undefined' && $response.body) {
    try {
        let body = JSON.parse($response.body);
        let modified = false;

        function applyRealPremium(u) {
            if (!u) return;
            u.is_gold = true;
            u.premium_level = 'premium';
            u.premium_unlimited = 1;
            u.have_trial = 0;
            
            if (!u.premium_details) {
                u.premium_details = {};
            }
            u.premium_details.level = 'premium';
            u.premium_details.is_unlimited = 1;
        }

        if (body.user) {
            applyRealPremium(body.user);
            modified = true;
        }
        if (body.data && body.data.user) {
            applyRealPremium(body.data.user);
            modified = true;
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
