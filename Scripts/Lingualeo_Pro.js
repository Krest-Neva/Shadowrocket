if (typeof $response !== 'undefined' && $response.body) {
    try {
        let body = JSON.parse($response.body);
        let url = $request ? $request.url : '';
        let status = $response.status || 200;

        function getFutureISO() {
            let d = new Date();
            d.setFullYear(d.getFullYear() + 10);
            let iso = d.toISOString();
            return iso.replace('Z', '+0000');
        }

        const premiumDetails = {
            level: 'premium',
            is_unlimited: 0,
            until: getFutureISO(),
            payment_id: 16802865,
            product: [{ id: 258, price: 1 }],
            provider: 'cloudpayments'
        };

        let modified = false;

        if (url.includes('/mobile/auth') || url.includes('/mergeData')) {
            if (body.user) {
                body.user.is_gold = true;
                body.user.meatballs = 111;
                body.user.have_trial = 0;
                body.user.premium_level = 'premium';
                body.user.premium_unlimited = 0;
                body.user.premium_until = getFutureISO();
                body.user.premium_details = premiumDetails;
                modified = true;
            }
        } else if (url.includes('/GetUserProfile')) {
            if (body.data) {
                body.data.premium_level = 'premium';
                body.data.premium_unlimited = 0;
                body.data.premium_until = getFutureISO();
                body.data.premium_details = premiumDetails;
                modified = true;
            }
        } else if (url.includes('/ProcessTraining')) {
            if (body.data) {
                body.data.isPremium = 1;
                body.data.premiumDays = 7;
                body.data.trialAvailable = 0;
                delete body.data.premiumExpire;
                delete body.data.premiumDiscount;
                modified = true;
            }
        } else if (url.includes('/getDashboardData')) {
            if (body.premiumAvailable !== undefined) {
                body.premiumAvailable = null;
                modified = true;
            }
            if (body.stories !== undefined) {
                body.stories = [];
                modified = true;
            }
        } else if (url.includes('/reading/getSetList')) {
            if (status === 200 && Array.isArray(body)) {
                for (let item of body) {
                    if (item.hasOwnProperty('isPremiumRequired')) {
                        item.isPremiumRequired = false;
                    }
                }
                modified = true;
            } else {
                body = [
                    {
                        id: 1,
                        name: "Sample Reading",
                        level: 1,
                        images: { orig: "" },
                        isPremiumRequired: false,
                        textsTrained: {},
                        totalCount: 1,
                        trainedCount: 0
                    }
                ];
                modified = true;
            }
        } else if (url.includes('/reading/loadTraining')) {
            // Подменяем только если статус не 200 или нет текста
            if (status !== 200 || !body.text) {
                body = {
                    "apiVersion": "1.0.0",
                    "config": {
                        "constrains": {
                            "lives": 3,
                            "time": 300
                        },
                        "omittedWordsCount": 15
                    },
                    "status": "ok",
                    "text": {
                        "id": 786433,
                        "items": [
                            {"position":0,"spelling":"This","type":2},
                            {"position":1,"spelling":" ","type":6},
                            {"position":2,"spelling":"is","type":2},
                            {"position":3,"spelling":" ","type":6},
                            {"position":4,"spelling":"a","type":4},
                            {"position":5,"spelling":" ","type":6},
                            {"position":6,"spelling":"dummy","type":2},
                            {"position":7,"spelling":" ","type":6},
                            {"position":8,"spelling":"text.","type":1}
                        ]
                    }
                };
                modified = true;
            }
        } else if (url.includes('/getProducts') || url.includes('/getproducts')) {
            if (status === 200 && body.products) {
                for (let product of body.products) {
                    if (product.recurrent !== undefined) {
                        product.recurrent = true;
                    }
                }
                modified = true;
            }
        } else if (url.includes('/v2/user/profile')) {
            if (status === 401 || status === 404) {
                body = {
                    user: {
                        is_gold: true,
                        meatballs: 111,
                        have_trial: 0,
                        premium_level: 'premium',
                        premium_unlimited: 0,
                        premium_until: getFutureISO(),
                        premium_details: premiumDetails
                    }
                };
                modified = true;
            } else if (body.user) {
                body.user.is_gold = true;
                body.user.meatballs = 111;
                body.user.have_trial = 0;
                body.user.premium_level = 'premium';
                body.user.premium_unlimited = 0;
                body.user.premium_until = getFutureISO();
                body.user.premium_details = premiumDetails;
                modified = true;
            }
        } else if (url.includes('/getLearningMain')) {
            if (body.data && Array.isArray(body.data)) {
                for (let section of body.data) {
                    if (section.audio) {
                        for (let item of section.audio) {
                            if (item.hasOwnProperty('isPremium')) {
                                item.isPremium = false;
                            }
                        }
                    }
                    if (section.word) {
                        for (let item of section.word) {
                            if (item.hasOwnProperty('isPremium')) {
                                item.isPremium = false;
                            }
                        }
                    }
                    if (section.reading) {
                        for (let item of section.reading) {
                            if (item.hasOwnProperty('isPremium')) {
                                item.isPremium = false;
                            }
                        }
                    }
                }
                modified = true;
            }
        } else if (url.includes('/GetSurveyUserLevel')) {
            if (body.data && body.data.level !== undefined) {
                body.data.level = 2;
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
