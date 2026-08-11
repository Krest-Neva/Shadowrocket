if (typeof $response !== 'undefined' && $response.body) {
    try {
        let body = JSON.parse($response.body);
        let url = $request ? $request.url : '';
        let modified = false;

        const futureDate = "2099-12-31";
        const futureDateIso = "2099-12-31T23:59:59Z";

        const unlockItems = (items) => {
            if (Array.isArray(items)) {
                items.forEach(item => {
                    if (item.isPremium !== undefined) item.isPremium = false;
                    if (item.is_premium !== undefined) item.is_premium = false;
                    if (item.isPaid !== undefined) item.isPaid = false;
                    if (item.is_paid !== undefined) item.is_paid = false;
                    if (item.isPurchased !== undefined) item.isPurchased = true;
                    if (item.is_purchased !== undefined) item.is_purchased = true;
                });
            }
        };

        if (url.includes('/mobile/auth') || url.includes('/mergeData') || url.includes('/v2/user/profile') || url.includes('/GetUserProfile')) {
            if (body.user) {
                body.user.is_premium = true;
                body.user.is_gold = true;
                body.user.premium_level = 'premium';
                body.user.premium_unlimited = 1; 
                body.user.premium_until = futureDate;
                body.user.have_trial = 0;
                
                if (!body.user.premium_details) {
                    body.user.premium_details = {};
                }
                body.user.premium_details.level = 'premium';
                body.user.premium_details.is_unlimited = 1; 
                body.user.premium_details.until = futureDateIso;
                
                modified = true;
            }
            if (body.banner !== undefined) { delete body.banner; modified = true; }
            if (body.banners !== undefined) { delete body.banners; modified = true; }
            if (body.offers !== undefined) { body.offers = []; modified = true; }
        } 
        
        else if (url.includes('/ProcessTraining')) {
            if (body.data) {
                body.data.isPremium = 1;
                body.data.premiumDays = 9999;
                body.data.trialAvailable = 0;
                if (body.data.premiumDiscount !== undefined) delete body.data.premiumDiscount;
                if (body.data.premiumExpire !== undefined) delete body.data.premiumExpire;
                modified = true;
            }
            if (body.userStatus) {
                body.userStatus.isPremium = 1;
                body.userStatus.premiumDays = 9999;
                body.userStatus.trialAvailable = 0;
                if (body.userStatus.premiumDiscount !== undefined) delete body.userStatus.premiumDiscount;
                if (body.userStatus.premiumExpire !== undefined) delete body.userStatus.premiumExpire;
                modified = true;
            }
        } 
        
        else if (url.includes('/getDashboardData')) {
            if (body.premiumAvailable !== undefined) {
                body.premiumAvailable = null;
                modified = true;
            }
            if (body.tasks) {
                unlockItems(body.tasks);
                modified = true;
            }
            if (body.offers !== undefined) { body.offers = []; modified = true; }
            if (body.banners !== undefined) { body.banners = []; modified = true; }
        } 
        
        else if (url.includes('/getLearningMain') || url.includes('/getGrammar') || url.includes('/getCourses') || url.includes('/v2/courses')) {
            if (body.data) {
                if (Array.isArray(body.data)) {
                    body.data.forEach(section => {
                        const types = ['audio', 'word', 'reading', 'video', 'grammar', 'course'];
                        types.forEach(type => {
                            if (section[type]) unlockItems(section[type]);
                        });
                    });
                    unlockItems(body.data); 
                } else if (typeof body.data === 'object') {
                    const types = ['audio', 'word', 'reading', 'video', 'grammar', 'courses'];
                    types.forEach(type => {
                        if (body.data[type]) unlockItems(body.data[type]);
                    });
                }
                modified = true;
            }
            
            if (body.courses) { unlockItems(body.courses); modified = true; }
            if (body.grammar) { unlockItems(body.grammar); modified = true; }
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
