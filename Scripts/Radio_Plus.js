(function() {
    var body = $response.body;
    var url = $request.url;
    var newBody = body;
    try {
        console.log("Radio_Plus: Original body = " + (body || "(empty)"));
        if (!body || body.length === 0) {
            var fake = {};
            if (url.indexOf('/api/v1/user/active_products') !== -1) {
                fake = [{ productId: "product.onetime.lifetime", expires: "2099-01-01", status: "active" }];
            } else if (url.indexOf('/api/v1/products/all') !== -1) {
                fake = [{
                    data: { productId: "product.onetime.lifetime", projectId: "ru.bukharskiy.radio" },
                    description: "Premium (активировано)",
                    currency: "RUB",
                    publicId: "pk_3198c0f676a9975ad6208eaad76f4",
                    amount: 0,
                    isPremium: true,
                    premium: true
                }];
            } else if (url.indexOf('/api/v1/check/isAvailable') !== -1) {
                fake = { isAvailable: true, premium: true, isPremium: true };
            } else {
                fake = {};
            }
            console.log("Radio_Plus: Empty body -> created fake response");
            $done({ body: JSON.stringify(fake) });
            return;
        }
        var obj = JSON.parse(body);
        console.log("Radio_Plus: Original JSON = " + body);

        // Функция для установки всех булевых флагов в true
        function forceTrue(data) {
            if (data === null || typeof data !== 'object') return;
            if (Array.isArray(data)) {
                data.forEach(function(item) { forceTrue(item); });
            } else {
                for (var key in data) {
                    if (data.hasOwnProperty(key)) {
                        var val = data[key];
                        var lowerKey = key.toLowerCase();
                        var truthyKeys = [
                            'isavailable', 'premium', 'ispremium', 'subscribed',
                            'issubscribed', 'active', 'enabled', 'haspremium',
                            'ispro', 'ispayed', 'trial', 'trialactive', 'valid',
                            'access', 'hasaccess', 'isactive', 'subscriptionactive'
                        ];
                        if (truthyKeys.indexOf(lowerKey) !== -1) {
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

        // Заменяем строковые статусы на активные
        function forceActiveStrings(data) {
            if (data === null || typeof data !== 'object') return;
            if (Array.isArray(data)) {
                data.forEach(function(item) { forceActiveStrings(item); });
            } else {
                for (var key in data) {
                    if (data.hasOwnProperty(key)) {
                        var val = data[key];
                        if (typeof val === 'string') {
                            var lower = val.toLowerCase();
                            if (lower.indexOf('inactive') !== -1 || lower.indexOf('expired') !== -1 || lower.indexOf('cancelled') !== -1 || lower.indexOf('none') !== -1) {
                                data[key] = 'active';
                            } else if (lower.indexOf('premium') !== -1 || lower.indexOf('pro') !== -1) {
                                data[key] = 'premium';
                            }
                        } else if (typeof val === 'object') {
                            forceActiveStrings(val);
                        }
                    }
                }
            }
        }

        // Помечаем продукты как премиумные, обнуляем цену
        function markProductsPremium(data) {
            if (data === null || typeof data !== 'object') return;
            if (Array.isArray(data)) {
                data.forEach(function(item) {
                    if (item && typeof item === 'object') {
                        if (item.data && item.data.productId) {
                            item.data.isPremium = true;
                            item.data.premium = true;
                        } else if (item.productId) {
                            item.isPremium = true;
                            item.premium = true;
                        }
                        if (item.amount !== undefined) item.amount = 0;
                    }
                });
            } else {
                for (var key in data) {
                    if (data.hasOwnProperty(key)) {
                        var val = data[key];
                        if (Array.isArray(val)) {
                            val.forEach(function(item) {
                                if (item && typeof item === 'object') {
                                    if (item.data && item.data.productId) {
                                        item.data.isPremium = true;
                                        item.data.premium = true;
                                    } else if (item.productId) {
                                        item.isPremium = true;
                                        item.premium = true;
                                    }
                                    if (item.amount !== undefined) item.amount = 0;
                                }
                            });
                        } else if (typeof val === 'object') {
                            markProductsPremium(val);
                        }
                    }
                }
            }
        }

        // Обработка /api/v1/user/active_products
        function handleActiveProducts(data) {
            if (data === null || typeof data !== 'object') return false;
            // Если массив
            if (Array.isArray(data)) {
                var hasValidProduct = data.some(function(item) {
                    var pid = item.productId || (item.data && item.data.productId);
                    return pid && (pid.indexOf('product.onetime.lifetime') !== -1 || pid.indexOf('product.subscription') !== -1);
                });
                if (!hasValidProduct) {
                    // Используем реальный productId из первого элемента, если есть, иначе по умолчанию
                    var first = data[0] || {};
                    var realId = first.productId || (first.data && first.data.productId) || "product.onetime.lifetime";
                    // Добавляем новый объект с правильной структурой
                    data.push({ productId: realId, expires: "2099-01-01", status: "active" });
                    console.log("Radio_Plus: Added real product to active_products: " + realId);
                }
                return true;
            } else {
                // Объект с ключами active_products и т.п.
                var keys = ['active_products', 'subscriptions', 'active_subscriptions', 'purchases'];
                for (var i = 0; i < keys.length; i++) {
                    var k = keys[i];
                    if (data[k] && Array.isArray(data[k])) {
                        var arr = data[k];
                        var hasValidProduct = arr.some(function(item) {
                            var pid = item.productId || (item.data && item.data.productId);
                            return pid && (pid.indexOf('product.onetime.lifetime') !== -1 || pid.indexOf('product.subscription') !== -1);
                        });
                        if (!hasValidProduct) {
                            var first = arr[0] || {};
                            var realId = first.productId || (first.data && first.data.productId) || "product.onetime.lifetime";
                            arr.push({ productId: realId, expires: "2099-01-01", status: "active" });
                            console.log("Radio_Plus: Added real product to " + k + ": " + realId);
                        }
                        return true;
                    }
                }
                // Если не нашли массив, но сам объект может быть массивом (уже обработано выше)
                return false;
            }
        }

        forceTrue(obj);
        forceActiveStrings(obj);

        if (url.indexOf('/api/v1/user/active_products') !== -1) {
            // Обрабатываем active_products
            var handled = handleActiveProducts(obj);
            if (!handled) {
                // Если не удалось обработать, создаём новый массив
                if (Array.isArray(obj)) {
                    if (obj.length === 0 || !obj.some(function(item) { return item.productId || (item.data && item.data.productId); })) {
                        obj = [{ productId: "product.onetime.lifetime", expires: "2099-01-01", status: "active" }];
                    }
                } else if (typeof obj === 'object') {
                    if (!obj.active_products) {
                        obj.active_products = [{ productId: "product.onetime.lifetime", expires: "2099-01-01", status: "active" }];
                    } else if (Array.isArray(obj.active_products)) {
                        var hasValid = obj.active_products.some(function(item) {
                            var pid = item.productId || (item.data && item.data.productId);
                            return pid && (pid.indexOf('product.onetime.lifetime') !== -1 || pid.indexOf('product.subscription') !== -1);
                        });
                        if (!hasValid) {
                            obj.active_products.push({ productId: "product.onetime.lifetime", expires: "2099-01-01", status: "active" });
                        }
                    }
                } else {
                    obj = [{ productId: "product.onetime.lifetime", expires: "2099-01-01", status: "active" }];
                }
            }
            console.log("Radio_Plus: Forced active_products with real productId");
        } else if (url.indexOf('/api/v1/products/all') !== -1) {
            // Помечаем все продукты как премиумные
            markProductsPremium(obj);
            console.log("Radio_Plus: Marked products as premium");
        } else if (url.indexOf('/api/v1/check/isAvailable') !== -1) {
            // Принудительно ставим isAvailable и флаги
            if (typeof obj === 'object' && obj !== null) {
                obj.isAvailable = true;
                if (obj.hasOwnProperty('available')) obj.available = true;
                if (obj.hasOwnProperty('success')) obj.success = true;
                obj.premium = true;
                obj.isPremium = true;
            } else {
                obj = { isAvailable: true, premium: true, isPremium: true };
            }
            console.log("Radio_Plus: Forced isAvailable = true and premium flags");
        }

        newBody = JSON.stringify(obj);
        console.log("Radio_Plus: Modified = " + newBody);
        $done({ body: newBody });
    } catch (e) {
        console.log("Radio_Plus: Error = " + e);
        $done({ body: body });
    }
})();