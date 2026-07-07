if (typeof $response !== 'undefined' && $response.body) {
    let body = $response.body;
    try {
        let obj = JSON.parse(body);

        function upgradeToPremium(target) {
            for (let key in target) {
                if (target.hasOwnProperty(key)) {
                    if (key === 'marketingUserType') {
                        target[key] = "premium";
                    }
                    if (key.toLowerCase().indexOf('premium') !== -1 || key.toLowerCase().indexOf('subscriber') !== -1) {
                        if (typeof target[key] === 'boolean') target[key] = true;
                        if (typeof target[key] === 'string') target[key] = "true";
                        if (typeof target[key] === 'number') target[key] = 1;
                    }
                    if (typeof target[key] === 'object' && target[key] !== null) {
                        upgradeToPremium(target[key]);
                    }
                }
            }
        }

        upgradeToPremium(obj);

        obj.marketingUserType = "premium";
        obj.isPremium = true;
        obj.premium = true;

        $done({ body: JSON.stringify(obj) });
    } catch (e) {
        $done({});
    }
} else {
    $done({});
}