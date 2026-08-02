if (typeof $response !== 'undefined' && $response.body) {
    try {
        let body = JSON.parse($response.body);
        let url = $request ? $request.url : '';
        let modified = false;

        function getFutureDate() {
            let d = new Date();
            d.setFullYear(d.getFullYear() + 10);
            return d.toISOString().split('T')[0];
        }

        function unlockUser(u) {
            if (!u) return;
            u.is_gold = true;
            u.premium_level = 'premium';
            u.premium_unlimited = 1;
            u.premium_until = getFutureDate();
            u.have_trial = 0;
            if (u.premium_details) {
                u.premium_details.level = 'premium';
                u.premium_details.is_unlimited = 1;
                u.premium_details.until = getFutureDate();
            } else {
                u.premium_details = {
                    level: 'premium',
                    is_unlimited: 1,
                    until: getFutureDate()
                };
            }
        }

        // Рекурсивный обход для разблокировки элементов в списках тренировок/курсов
        function unlockRecursive(obj) {
            if (!obj || typeof obj !== 'object') return;
            
            for (let key in obj) {
                if (Object.prototype.hasOwnProperty.call(obj, key)) {
                    let val = obj[key];
                    
                    // Снимаем распространенные флаги блокировок
                    if (key === 'is_locked' || key === 'locked' || key === 'isLocked') {
                        obj[key] = false;
                        modified = true;
                    }
                    if (key === 'is_free' || key === 'free' || key === 'isFree') {
                        obj[key] = true;
                        modified = true;
                    }
                    if (key === 'access_type' || key === 'accessType') {
                        obj[key] = 'open'; // или полный доступ
                        modified = true;
                    }
                    if (key === 'is_premium' || key === 'isPremium') {
                        obj[key] = 0; // убираем требование премиума как отдельного барьера на элемент
                        modified = true;
                    }

                    if (val && typeof val === 'object') {
                        unlockRecursive(val);
                    }
                }
            }
        }

        // 1. Всегда правим профиль, если он есть в ответе
        if (body.user) {
            unlockUser(body.user);
            modified = true;
        }
        if (body.data && body.data.user) {
            unlockUser(body.data.user);
            modified = true;
        }

        // 2. Применяем глубокую рекурсивную разблокировку для списков тренировок, курсов и разделов
        if (url.includes('training') || url.includes('grammar') || url.includes('courses') || url.includes('dashboard') || url.includes('getLearningMain')) {
            unlockRecursive(body);
        }

        // 3. Точечные правки для эндпоинтов тренировок
        if (url.includes('/ProcessTraining') || url.includes('Training')) {
            if (body.data) {
                body.data.isPremium = 1;
                body.data.premiumDays = 3650;
                body.data.trialAvailable = 0;
                delete body.data.premiumExpire;
                delete body.data.premiumDiscount;
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
