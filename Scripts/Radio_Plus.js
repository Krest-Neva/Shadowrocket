let body = $response.body;
try {
    let obj = JSON.parse(body);
    console.log("Radio_Plus: Original = " + body);
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
    if (body.includes('"products"')) {
        if (!obj.products || obj.products.length === 0) {
            obj.products = [{ id: "premium", name: "Premium", price: 0 }];
        }
    }
    if (body.includes('"active_products"') || body.includes('"activeProducts"')) {
        if (!obj.active_products || obj.active_products.length === 0) {
            obj.active_products = [{ productId: "premium", expires: "2099-01-01" }];
        }
    }
    let newBody = JSON.stringify(obj);
    console.log("Radio_Plus: Modified = " + newBody);
    $done({ body: newBody });
} catch (e) {
    console.log("Radio_Plus: Error = " + e);
    $done({ body: body });
}