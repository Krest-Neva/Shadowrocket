(function() {
    let body = $response.body;
    let url = $request.url;
    let newBody = body;

    try {
        if (!body || body.length === 0) {
            let fake = {};
            if (url.includes('/api/v1/user/active_products')) {
                fake = [{ productId: "premium", expires: "2099-01-01" }];
            } else if (url.includes('/api/v1/products/all')) {
                fake = [{ id: "premium", name: "Premium", price: 0 }];
            } else if (url.includes('/api/v1/check/isAvailable')) {
                fake = { isAvailable: true };
            } else {
                fake = {};
            }
            console.log("Radio_Plus: Empty body -> created fake response");
            $done({ body: JSON.stringify(fake) });
            return;
        }

        let obj = JSON.parse(body);
        console.log("Radio_Plus: URL = " + url);
        console.log("Radio_Plus: Original = " + body);

        function forceTrue(data) {
            if (data === null || typeof data !== 'object') return;
            if (Array.isArray(data)) {
                data.forEach(item => forceTrue(item));
            } else {
                for (let key in data) {
                    if (data.hasOwnProperty(key)) {
                        let val = data[key];
                        let lowerKey = key.toLowerCase();
                        let truthyKeys = [
                            'isavailable', 'premium', 'ispremium', 'subscribed',
                            'issubscribed', 'active', 'enabled', 'haspremium',
                            'ispro', 'ispayed', 'trial', 'trialactive', 'valid',
                            'access', 'hasaccess', 'isactive', 'subscriptionactive'
                        ];
                        if (truthyKeys.includes(lowerKey)) {
                            if (typeof val === 'boolean') data[key] = true;
                            else if (typeof val === 'string') data[key] = "true";
                            else if (typeof val === 'number') data[key] = 1;
                        }
                        if (typeof val === 'object') {
                            forceTrue(val);
                        }
                    }
                }
            }
        }

        function addPremiumToProducts(data) {
            if (data === null || typeof data !== 'object') return;
            if (Array.isArray(data)) {
                let isProductList = data.some(item =>
                    item && typeof item === 'object' &&
                    (item.id || item.productId) &&
                    (item.name || item.title || item.description)
                );
                if (isProductList) {
                    let hasPremium = data.some(item =>
                        (item.id && item.id.toLowerCase().includes('premium')) ||
                        (item.productId && item.productId.toLowerCase().includes('premium'))
                    );
                    if (!hasPremium) {
                        data.unshift({ id: "premium", name: "Premium", price: 0 });
                        console.log("Radio_Plus: Added premium product to array");
                    }
                } else {
                    data.forEach(item => addPremiumToProducts(item));
                }
            } else {
                for (let key in data) {
                    if (data.hasOwnProperty(key)) {
                        let val = data[key];
                        let lowerKey = key.toLowerCase();
                        let productKeys = ['products', 'items', 'offers', 'plans', 'subscriptions', 'productlist'];
                        if (Array.isArray(val) && productKeys.includes(lowerKey)) {
                            let hasPremium = val.some(item =>
                                (item.id && item.id.toLowerCase().includes('premium')) ||
                                (item.productId && item.productId.toLowerCase().includes('premium'))
                            );
                            if (!hasPremium) {
                                val.unshift({ id: "premium", name: "Premium", price: 0 });
                                console.log("Radio_Plus: Added premium product to " + key);
                            }
                        } else if (typeof val === 'object') {
                            addPremiumToProducts(val);
                        }
                    }
                }
            }
        }

        function ensureActiveProducts(data) {
            if (data === null || typeof data !== 'object') return false;
            if (Array.isArray(data)) {
                let isActiveList = data.some(item => item && typeof item === 'object' && item.productId);
                if (isActiveList) {
                    let hasPremium = data.some(item =>
                        item.productId && item.productId.toLowerCase().includes('premium')
                    );
                    if (!hasPremium) {
                        data.push({ productId: "premium", expires: "2099-01-01" });
                        console.log("Radio_Plus: Added premium to active_products array");
                    }
                    return true;
                }
            } else {
                let activeKeys = ['active_products', 'subscriptions', 'active_subscriptions', 'purchases'];
                for (let key of activeKeys) {
                    if (data[key] && Array.isArray(data[key])) {
                        let arr = data[key];
                        let hasPremium = arr.some(item =>
                            (item.productId && item.productId.toLowerCase().includes('premium')) ||
                            (item.id && item.id.toLowerCase().includes('premium'))
                        );
                        if (!hasPremium) {
                            arr.push({ productId: "premium", expires: "2099-01-01" });
                            console.log("Radio_Plus: Added premium to " + key);
                        }
                        return true;
                    }
                }
            }
            return false;
        }

        forceTrue(obj);
        addPremiumToProducts(obj);
        let activeHandled = ensureActiveProducts(obj);

        if (url.includes('/api/v1/user/active_products') && !activeHandled) {
            if (Array.isArray(obj)) {
                let hasPremium = obj.some(item => item.productId && item.productId.includes('premium'));
                if (!hasPremium) {
                    obj.push({ productId: "premium", expires: "2099-01-01" });
                }
            } else if (typeof obj === 'object') {
                if (!obj.active_products) {
                    obj.active_products = [{ productId: "premium", expires: "2099-01-01" }];
                } else if (Array.isArray(obj.active_products)) {
                    let hasPremium = obj.active_products.some(item => item.productId && item.productId.includes('premium'));
                    if (!hasPremium) {
                        obj.active_products.push({ productId: "premium", expires: "2099-01-01" });
                    }
                }
            } else {
                obj = [{ productId: "premium", expires: "2099-01-01" }];
            }
            console.log("Radio_Plus: Forced active_products structure");
        }

        if (url.includes('/api/v1/check/isAvailable')) {
            if (typeof obj === 'object' && obj !== null) {
                obj.isAvailable = true;
                if (obj.hasOwnProperty('available')) obj.available = true;
                if (obj.hasOwnProperty('success')) obj.success = true;
            } else {
                obj = { isAvailable: true };
            }
            console.log("Radio_Plus: Forced isAvailable = true");
        }

        newBody = JSON.stringify(obj);
        console.log("Radio_Plus: Modified = " + newBody);
        $done({ body: newBody });

    } catch (e) {
        console.log("Radio_Plus: Error = " + e);
        $done({ body: body });
    }
})();