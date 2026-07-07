let body = $response.body;
let url = $request.url;
let newBody = body;

try {
    if (!body || body.length === 0) {
        if (url.includes('/api/v1/user/active_products')) {
            newBody = JSON.stringify([{ productId: "premium", expires: "2099-01-01" }]);
        } else if (url.includes('/api/v1/products/all')) {
            newBody = JSON.stringify([{ id: "premium", name: "Premium", price: 0 }]);
        } else if (url.includes('/api/v1/check/isAvailable')) {
            newBody = JSON.stringify({ isAvailable: true });
        } else {
            newBody = JSON.stringify({});
        }
        console.log("Radio_Plus: Empty body, created fake response");
        $done({ body: newBody });
        return;
    }

    let obj = JSON.parse(body);
    console.log("Radio_Plus: Original = " + body);
    console.log("Radio_Plus: URL = " + url);

    function setTrue(obj) {
        if (obj && typeof obj === 'object') {
            for (let key in obj) {
                if (obj.hasOwnProperty(key)) {
                    let truthyKeys = ['isAvailable', 'premium', 'isPremium', 'subscribed', 'active', 'enabled', 'hasPremium'];
                    if (truthyKeys.includes(key)) {
                        if (typeof obj[key] === 'boolean') obj[key] = true;
                        else if (typeof obj[key] === 'string') obj[key] = "true";
                        else if (typeof obj[key] === 'number') obj[key] = 1;
                    }
                    if (typeof obj[key] === 'object') {
                        setTrue(obj[key]);
                    }
                }
            }
        }
    }

    if (url.includes('/api/v1/user/active_products')) {
        if (Array.isArray(obj)) {
            if (obj.length === 0) {
                obj.push({ productId: "premium", expires: "2099-01-01" });
            } else {
                let hasPremium = obj.some(item => item.productId && item.productId.includes('premium'));
                if (!hasPremium) {
                    obj.push({ productId: "premium", expires: "2099-01-01" });
                }
            }
        } else if (typeof obj === 'object' && obj !== null) {
            if (obj.active_products && Array.isArray(obj.active_products)) {
                if (obj.active_products.length === 0) {
                    obj.active_products.push({ productId: "premium", expires: "2099-01-01" });
                } else {
                    let hasPremium = obj.active_products.some(item => item.productId && item.productId.includes('premium'));
                    if (!hasPremium) {
                        obj.active_products.push({ productId: "premium", expires: "2099-01-01" });
                    }
                }
            } else if (obj.subscriptions && Array.isArray(obj.subscriptions)) {
                if (obj.subscriptions.length === 0) {
                    obj.subscriptions.push({ id: "premium", status: "active" });
                } else {
                    let hasPremium = obj.subscriptions.some(item => item.id && item.id.includes('premium'));
                    if (!hasPremium) {
                        obj.subscriptions.push({ id: "premium", status: "active" });
                    }
                }
            } else {
                obj = { active_products: [{ productId: "premium", expires: "2099-01-01" }] };
            }
        } else {
            obj = [{ productId: "premium", expires: "2099-01-01" }];
        }
    }

    if (url.includes('/api/v1/products/all')) {
        if (Array.isArray(obj)) {
            let hasPremium = obj.some(item => item.id && item.id.includes('premium'));
            if (!hasPremium) {
                obj.unshift({ id: "premium", name: "Premium", price: 0 });
            }
        } else if (typeof obj === 'object' && obj !== null) {
            if (obj.products && Array.isArray(obj.products)) {
                let hasPremium = obj.products.some(item => item.id && item.id.includes('premium'));
                if (!hasPremium) {
                    obj.products.unshift({ id: "premium", name: "Premium", price: 0 });
                }
            } else {
                obj.products = [{ id: "premium", name: "Premium", price: 0 }];
            }
        } else {
            obj = [{ id: "premium", name: "Premium", price: 0 }];
        }
    }

    setTrue(obj);

    if (url.includes('/api/v1/check/isAvailable')) {
        if (typeof obj === 'object' && obj !== null) {
            obj.isAvailable = true;
            if (obj.hasOwnProperty('available')) obj.available = true;
            if (obj.hasOwnProperty('success')) obj.success = true;
        } else {
            obj = { isAvailable: true };
        }
    }

    newBody = JSON.stringify(obj);
    console.log("Radio_Plus: Modified = " + newBody);
    $done({ body: newBody });
} catch (e) {
    console.log("Radio_Plus: Error = " + e);
    $done({ body: body });
}