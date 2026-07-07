let body = $response.body;
let url = $request.url;
try {
    let obj = JSON.parse(body);
    console.log("Radio_Plus: Original = " + body);
    console.log("Radio_Plus: URL = " + url);
    
    if (url.includes('/api/v1/user/active_products')) {
        if (Array.isArray(obj)) {
            if (obj.length === 0) {
                obj = [{ productId: "premium", expires: "2099-01-01" }];
            }
        } else if (obj.active_products && obj.active_products.length === 0) {
            obj.active_products = [{ productId: "premium", expires: "2099-01-01" }];
        }
    } else {
        function updateKeys(obj) {
            if (obj && typeof obj === 'object') {
                for (let key in obj) {
                    if (obj.hasOwnProperty(key)) {
                        if (key === 'isAvailable' || key === 'premium' || key === 'isPremium' || key === 'subscribed' || key === 'active') {
                            if (typeof obj[key] === 'boolean') obj[key] = true;
                            else if (typeof obj[key] === 'string') obj[key] = "true";
                            else if (typeof obj[key] === 'number') obj[key] = 1;
                        }
                        if (typeof obj[key] === 'object') {
                            updateKeys(obj[key]);
                        }
                    }
                }
            }
        }
        updateKeys(obj);
        if (url.includes('/api/v1/products/all')) {
            if (Array.isArray(obj)) {
                if (obj.length === 0) {
                    obj = [{ id: "premium", name: "Premium", price: 0 }];
                }
            } else {
                if (!obj.products || obj.products.length === 0) {
                    obj.products = [{ id: "premium", name: "Premium", price: 0 }];
                }
            }
        }
    }
    
    let newBody = JSON.stringify(obj);
    console.log("Radio_Plus: Modified = " + newBody);
    $done({ body: newBody });
} catch (e) {
    console.log("Radio_Plus: Error = " + e);
    $done({ body: body });
}