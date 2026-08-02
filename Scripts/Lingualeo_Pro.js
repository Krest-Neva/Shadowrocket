if (typeof $response !== 'undefined' && $response.body) {
    try {
        let body = JSON.parse($response.body);
        let url = $request ? $request.url : '';
        let status = $response.status || 200;

        function getFutureDate() {
            let d = new Date();
            d.setFullYear(d.getFullYear() + 10);
            let iso = d.toISOString().split('T')[0];
            return iso + 'T00:00:00+0000';
        }

        const premiumDetails = {
            is_unlimited: 0,
            level: 'premium',
            until: getFutureDate(),
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
                body.user['>>>premium<<<_level'] = 'premium';
                body.user['>>>premium<<<_unlimited'] = 0;
                body.user['>>>premium<<<_until'] = getFutureDate();
                body.user['>>>premium<<<_details'] = premiumDetails;
                modified = true;
            }
        } else if (url.includes('/GetUserProfile')) {
            if (body.data) {
                body.data['>>>premium<<<_level'] = 'premium';
                body.data['>>>premium<<<_unlimited'] = 0;
                body.data['>>>premium<<<_until'] = getFutureDate();
                body.data['>>>premium<<<_details'] = premiumDetails;
                modified = true;
            }
        } else if (url.includes('/ProcessTraining')) {
            if (body.data) {
                body.data['is>>>Premium<<<'] = 1;
                body.data['>>>premium<<<Days'] = 7;
                body.data.trialAvailable = 0;
                delete body.data.premiumExpire;
                delete body.data.premiumDiscount;
                modified = true;
            }
        } else if (url.includes('/grammar/getRules')) {
            if (Array.isArray(body)) {
                for (let rule of body) {
                    if (rule.hasOwnProperty('isGoldRequired')) {
                        rule.isGoldRequired = false;
                    }
                }
                modified = true;
            }
        } else if (url.includes('/grammar/getRuleExpressions')) {
            if (Array.isArray(body)) {
                for (let item of body) {
                    if (item.hasOwnProperty('isPremiumRequired')) {
                        item.isPremiumRequired = false;
                    }
                }
                modified = true;
            }
        } else if (url.includes('/course/grammar')) {
            if (body.courses && Array.isArray(body.courses)) {
                for (let course of body.courses) {
                    if (course.hasOwnProperty('isGoldRequired')) {
                        course.isGoldRequired = false;
                    }
                }
                modified = true;
            }
        } else if (url.includes('/listening/getStorySets')) {
            if (Array.isArray(body)) {
                for (let set of body) {
                    if (set.set && set.set.hasOwnProperty('is>>>Premium<<<Required')) {
                        set.set['is>>>Premium<<<Required'] = false;
                    }
                    if (set.progress && set.progress.hasOwnProperty('is>>>Premium<<<Required')) {
                        set.progress['is>>>Premium<<<Required'] = false;
                    }
                }
                modified = true;
            }
        } else if (url.includes('/listening/getStory')) {
            if (body.config && body.config.hasOwnProperty('is>>>Premium<<<Required')) {
                body.config['is>>>Premium<<<Required'] = false;
                modified = true;
            }
        } else if (url.includes('/reading/getSetList')) {
            if (Array.isArray(body)) {
                for (let item of body) {
                    if (item.hasOwnProperty('is>>>Premium<<<Required')) {
                        item['is>>>Premium<<<Required'] = false;
                    }
                }
                modified = true;
            }
        } else if (url.includes('/reading/loadTraining')) {
            if (!body.text) {
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
        } else if (url.includes('/getDashboardData')) {
            if (body.hasOwnProperty('>>>premium<<<Available')) {
                body['>>>premium<<<Available'] = null;
                modified = true;
            }
            if (body.stories !== undefined) {
                body.stories = [];
                modified = true;
            }
            if (body.tasks && Array.isArray(body.tasks)) {
                for (let task of body.tasks) {
                    if (task.hasOwnProperty('is>>>Premium<<<')) {
                        task['is>>>Premium<<<'] = false;
                    }
                }
                modified = true;
            }
        } else if (url.includes('/getLearningMain')) {
            if (body.data && Array.isArray(body.data)) {
                for (let section of body.data) {
                    if (section.audio) {
                        for (let item of section.audio) {
                            if (item.hasOwnProperty('is>>>Premium<<<')) {
                                item['is>>>Premium<<<'] = false;
                            }
                        }
                    }
                    if (section.word) {
                        for (let item of section.word) {
                            if (item.hasOwnProperty('is>>>Premium<<<')) {
                                item['is>>>Premium<<<'] = false;
                            }
                        }
                    }
                    if (section.reading) {
                        for (let item of section.reading) {
                            if (item.hasOwnProperty('is>>>Premium<<<')) {
                                item['is>>>Premium<<<'] = false;
                            }
                        }
                    }
                }
                modified = true;
            }
        } else if (url.includes('/getProducts') || url.includes('/getproducts')) {
            if (status === 200) {
                if (body.products && Array.isArray(body.products)) {
                    for (let product of body.products) {
                        if (product.recurrent !== undefined) {
                            product.recurrent = true;
                        }
                    }
                    modified = true;
                } else if (body.campaign && Array.isArray(body.campaign)) {
                    for (let camp of body.campaign) {
                        if (camp.recurrent !== undefined) {
                            camp.recurrent = true;
                        }
                        if (camp.baseProduct && camp.baseProduct.length) {
                            for (let prod of camp.baseProduct) {
                                if (prod.recurrent !== undefined) {
                                    prod.recurrent = true;
                                }
                            }
                        }
                    }
                    modified = true;
                }
            }
        } else if (url.includes('/GetCourses')) {
            if (body.thematic) {
                for (let category of body.thematic) {
                    if (category.courses) {
                        for (let course of category.courses) {
                            if (course.hasOwnProperty('is>>>Premium<<<')) {
                                course['is>>>Premium<<<'] = 0;
                            }
                            if (course.hasOwnProperty('paymentStatus')) {
                                course.paymentStatus = 1;
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
