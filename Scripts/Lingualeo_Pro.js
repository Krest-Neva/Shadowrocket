if (typeof $response !== 'undefined' && $response.body) {
    try {
        let body = JSON.parse($response.body);
        let url = $request ? $request.url : '';
        let modified = false;

        // Используем надежную дату в далеком будущем в формате ISO
        const futureDate = "2099-01-01T00:00:00.000Z"; 
        
        // 1. Подмена профиля пользователя и авторизации
        if (url.includes('/mobile/auth') || url.includes('/mergeData') || url.includes('/v2/user/profile') || url.includes('/GetUserProfile')) {
            if (body.user) {
                // Основные флаги
                body.user.is_gold = true;
                body.user.is_premium = true;
                body.user.premium_level = 'premium';
                body.user.premium_unlimited = 0;
                body.user.premium_until = futureDate;
                body.user.have_trial = 0;
                
                // Детали премиума для кнопки в профиле
                if (!body.user.premium_details) {
                    body.user.premium_details = {};
                }
                body.user.premium_details.level = 'premium';
                body.user.premium_details.is_unlimited = 0;
                body.user.premium_details.until = futureDate;

                // Удаляем баннеры со скидками из профиля
                if (body.user.premium_discount !== undefined) delete body.user.premium_discount;
                if (body.user.premium_expire !== undefined) delete body.user.premium_expire;
                if (body.user.banners !== undefined) body.user.banners = [];
                
                modified = true;
            }
        } 
        
        // 2. Тренировки (ProcessTraining)
        else if (url.includes('/ProcessTraining')) {
            if (body.data) {
                body.data.isPremium = true; 
                body.data.premiumDays = 36500;
                body.data.trialAvailable = 0;
                if (body.data.premiumDiscount !== undefined) delete body.data.premiumDiscount;
                if (body.data.premiumExpire !== undefined) delete body.data.premiumExpire;
                modified = true;
            }
            if (body.userStatus) {
                body.userStatus.isPremium = true;
                body.userStatus.premiumDays = 36500;
                body.userStatus.trialAvailable = 0;
                if (body.userStatus.premiumDiscount !== undefined) delete body.userStatus.premiumDiscount;
                if (body.userStatus.premiumExpire !== undefined) delete body.userStatus.premiumExpire;
                modified = true;
            }
        } 
        
        // 3. Дашборд (Снятие замочков с карточек на главной и удаление баннеров)
        else if (url.includes('/getDashboardData')) {
            if (body.premiumAvailable !== undefined) {
                body.premiumAvailable = null;
                modified = true;
            }
            if (body.tasks && Array.isArray(body.tasks)) {
                for (let task of body.tasks) {
                    if (task.hasOwnProperty('isPremium')) {
                        task.isPremium = false; // Снимаем визуальный замок
                    }
                }
                modified = true;
            }
            // Убираем баннер «забрать скидку» с дашборда
            if (body.banners) {
                body.banners = [];
                modified = true;
            }
            if (body.promos) {
                body.promos = [];
                modified = true;
            }
        } 
        
        // 4. Обучение (Аудирование, чтение, слова)
        else if (url.includes('/getLearningMain')) {
            if (body.data && Array.isArray(body.data)) {
                for (let section of body.data) {
                    const types = ['audio', 'word', 'reading', 'grammar'];
                    for (let type of types) {
                        if (section[type] && Array.isArray(section[type])) {
                            for (let item of section[type]) {
                                if (item.hasOwnProperty('isPremium')) {
                                    item.isPremium = false;
                                }
                            }
                        }
                    }
                }
                modified = true;
            }
        }

        // 5. Курсы (Разблокировка грамматики и джунглей)
        else if (url.includes('/GetCourses') || url.includes('/course/')) {
            if (body.courses && Array.isArray(body.courses)) {
                for (let course of body.courses) {
                    if (course.hasOwnProperty('isPremium')) course.isPremium = false;
                    if (course.hasOwnProperty('is_premium')) course.is_premium = false;
                }
                modified = true;
            }
        }
        
        // 6. Биллинг (Лечим ошибку "Нет интернета")
        else if (url.includes('/v2/billing/products/') || url.includes('/getProducts')) {
            // Вместо {} возвращаем корректную структуру пустого массива
            if (body.detail) {
                // Если прилетела ошибка токена, переписываем на пустые продукты
                body = { products: [] };
                modified = true;
            } else if (body.products) {
                body.products = [];
                modified = true;
            } else {
                body = { products: [] };
                modified = true;
            }
        }

        if (modified) {
            $done({ body: JSON.stringify(body) });
        } else {
            $done({});
        }
    } catch (e) {
        // В случае ошибки парсинга возвращаем оригинальный ответ, чтобы не сломать интернет в приложении
        $done({});
    }
} else {
    $done({});
}
