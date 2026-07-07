(function() {
    let body = $response.body;
    let url = $request.url;
    let newBody = body;

    try {
        if (!body || body.length === 0) {
            let fake = {};
            if (url.includes('/api/v1/user/active_products')) {
                fake = [{ data: { productId: "premium", expires: "2099-01-01" } }];
            } else if (url.includes('/api/v1/products/all')) {
                fake = [{ data: { productId: "premium", projectId: "ru.bukharskiy.radio" }, description: "Premium", currency: "RUB", publicId: "pk_premium", amount: 0 }];
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

        function ensurePremiumInProducts(data) {
            if (data === null || typeof data !== 'object') return;
            if (Array.isArray(data)) {
                let hasProductFields = data.some(item => {
                    if (item && typeof item === 'object') {
                        if (item.productId !== undefined) return true;
                        if (item.data && item.data.productId !== undefined) return true;
                        if (item.id !== undefined) return true;
                        if (item.data && item.data.id !== undefined) return true;
                    }
                    return false;
                });
                if (hasProductFields) {
                    let hasPremium = data.some(item => {
                        let pid = item.productId || (item.data && item.data.productId) || item.id || (item.data && item.data.id);
                        return pid && pid.toLowerCase().includes('premium');
                    });
                    if (!hasPremium) {
                        let first = data[0] || {};
                        let premiumItem = JSON.parse(JSON.stringify(first));
                        if (premiumItem.productId !== undefined) {
                            premiumItem.productId = "premium";
                        } else if (premiumItem.data && premiumItem.data.productId !== undefined) {
                            premiumItem.data.productId = "premium";
                        } else if (premiumItem.id !== undefined) {
                            premiumItem.id = "premium";
                        } else if (premiumItem.data && premiumItem.data.id !== undefined) {
                            premiumItem.data.id = "premium";
                        } else {
                            premiumItem = {
                                data: { productId: "premium", projectId: "ru.bukharskiy.radio" },
                                description: "Premium",
                                currency: "RUB",
                                publicId: "pk_premium",
                                amount: 0
                            };
                        }
                        data.unshift(premiumItem);
                        console.log("Radio_Plus: Added premium product to products array");
                    }
                } else {
                    data.forEach(item => ensurePremiumInProducts(item));
                }
            } else {
                for (let key in data) {
                    if (data.hasOwnProperty(key)) {
                        let val = data[key];
                        let lowerKey = key.toLowerCase();
                        let productKeys = ['products', 'items', 'offers', 'plans', 'subscriptions', 'productlist'];
                        if (Array.isArray(val) && productKeys.includes(lowerKey)) {
                            let hasProductFields = val.some(item => {
                                if (item && typeof item === 'object') {
                                    if (item.productId !== undefined) return true;
                                    if (item.data && item.data.productId !== undefined) return true;
                                    if (item.id !== undefined) return true;
                                    if (item.data && item.data.id !== undefined) return true;
                                }
                                return false;
                            });
                            if (hasProductFields) {
                                let hasPremium = val.some(item => {
                                    let pid = item.productId || (item.data && item.data.productId) || item.id || (item.data && item.data.id);
                                    return pid && pid.toLowerCase().includes('premium');
                                });
                                if (!hasPremium) {
                                    let first = val[0] || {};
                                    let premiumItem = JSON.parse(JSON.stringify(first));
                                    if (premiumItem.productId !== undefined) {
                                        premiumItem.productId = "premium";
                                    } else if (premiumItem.data && premiumItem.data.productId !== undefined) {
                                        premiumItem.data.productId = "premium";
                                    } else if (premiumItem.id !== undefined) {
                                        premiumItem.id = "premium";
                                    } else if (premiumItem.data && premiumItem.data.id !== undefined) {
                                        premiumItem.data.id = "premium";
                                    } else {
                                        premiumItem = {
                                            data: { productId: "premium", projectId: "ru.bukharskiy.radio" },
                                            description: "Premium",
                                            currency: "RUB",
                                            publicId: "pk_premium",
                                            amount: 0
                                        };
                                    }
                                    val.unshift(premiumItem);
                                    console.log("Radio_Plus: Added premium product to " + key);
                                }
                            } else {
                                val.forEach(item => ensurePremiumInProducts(item));
                            }
                        } else if (typeof val === 'object') {
                            ensurePremiumInProducts(val);
                        }
                    }
                }
            }
        }

        function ensureActiveProducts(data) {
            if (data === null || typeof data !== 'object') return false;
            if (Array.isArray(data)) {
                let isActiveList = data.some(item => item && typeof item === 'object' && (item.productId !== undefined || (item.data && item.data.productId !== undefined) || item.id !== undefined || (item.data && item.data.id !== undefined)));
                if (isActiveList) {
                    let hasPremium = data.some(item => {
                        let pid = item.productId || (item.data && item.data.productId) || item.id || (item.data && item.data.id);
                        return pid && pid.toLowerCase().includes('premium');
                    });
                    if (!hasPremium) {
                        let first = data[0] || {};
                        let premiumItem = JSON.parse(JSON.stringify(first));
                        if (premiumItem.productId !== undefined) {
                            premiumItem.productId = "premium";
                        } else if (premiumItem.data && premiumItem.data.productId !== undefined) {
                            premiumItem.data.productId = "premium";
                        } else if (premiumItem.id !== undefined) {
                            premiumItem.id = "premium";
                        } else if (premiumItem.data && premiumItem.data.id !== undefined) {
                            premiumItem.data.id = "premium";
                        } else {
                            premiumItem = { data: { productId: "premium", expires: "2099-01-01" } };
                        }
                        data.push(premiumItem);
                        console.log("Radio_Plus: Added premium to active_products array");
                    }
                    return true;
                }
            } else {
                let activeKeys = ['active_products', 'subscriptions', 'active_subscriptions', 'purchases'];
                for (let key of activeKeys) {
                    if (data[key] && Array.isArray(data[key])) {
                        let arr = data[key];
                        let isActiveList = arr.some(item => item && typeof item === 'object' && (item.productId !== undefined || (item.data && item.data.productId !== undefined) || item.id !== undefined || (item.data && item.data.id !== undefined)));
                        if (isActiveList) {
                            let hasPremium = arr.some(item => {
                                let pid = item.productId || (item.data && item.data.productId) || item.id || (item.data && item.data.id);
                                return pid && pid.toLowerCase().includes('premium');
                            });
                            if (!hasPremium) {
                                let first = arr[0] || {};
                                let premiumItem = JSON.parse(JSON.stringify(first));
                                if (premiumItem.productId !== undefined) {
                                    premiumItem.productId = "premium";
                                } else if (premiumItem.data && premiumItem.data.productId !== undefined) {
                                    premiumItem.data.productId = "premium";
                                } else if (premiumItem.id !== undefined) {
                                    premiumItem.id = "premium";
                                } else if (premiumItem.data && premiumItem.data.id !== undefined) {
                                    premiumItem.data.id = "premium";
                                } else {
                                    premiumItem = { data: { productId: "premium", expires: "2099-01-01" } };
                                }
                                arr.push(premiumItem);
                                console.log("Radio_Plus: Added premium to " + key);
                            }
                            return true;
                        }
                    }
                }
            }
            return false;
        }

        forceTrue(obj);
        ensurePremiumInProducts(obj);
        let activeHandled = ensureActiveProducts(obj);

        if (url.includes('/api/v1/user/active_products') && !activeHandled) {
            if (Array.isArray(obj)) {
                let hasPremium = obj.some(item => {
                    let pid = item.productId || (item.data && item.data.productId);
                    return pid && pid.includes('premium');
                });
                if (!hasPremium) {
                    obj.push({ data: { productId: "premium", expires: "2099-01-01" } });
                }
            } else if (typeof obj === 'object') {
                if (!obj.active_products) {
                    obj.active_products = [{ data: { productId: "premium", expires: "2099-01-01" } }];
                } else if (Array.isArray(obj.active_products)) {
                    let hasPremium = obj.active_products.some(item => {
                        let pid = item.productId || (item.data && item.data.productId);
                        return pid && pid.includes('premium');
                    });
                    if (!hasPremium) {
                        obj.active_products.push({ data: { productId: "premium", expires: "2099-01-01" } });
                    }
                }
            } else {
                obj = [{ data: { productId: "premium", expires: "2099-01-01" } }];
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