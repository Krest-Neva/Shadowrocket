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
                        {"position":0,"spelling":"The","type":2},
                        {"position":1,"spelling":" ","type":6},
                        {"position":2,"spelling":"soldier","type":2},
                        {"position":3,"spelling":" ","type":6},
                        {"position":4,"spelling":"took","type":2},
                        {"position":5,"spelling":" ","type":6},
                        {"position":6,"spelling":"Dantes","type":2},
                        {"position":7,"spelling":" ","type":6},
                        {"position":8,"spelling":"to","type":3},
                        {"position":9,"spelling":" ","type":6},
                        {"position":10,"spelling":"a","type":4},
                        {"position":11,"spelling":" ","type":6},
                        {"position":12,"spelling":"small","type":2},
                        {"position":13,"spelling":" ","type":6},
                        {"position":14,"spelling":"room","type":2},
                        {"position":15,"spelling":".","type":1},
                        {"position":16,"spelling":" ","type":6},
                        {"position":17,"spelling":"Then","type":2},
                        {"position":18,"spelling":",","type":1},
                        {"position":19,"spelling":" ","type":6},
                        {"position":20,"spelling":"at","type":3},
                        {"position":21,"spelling":" ","type":6},
                        {"position":22,"spelling":"about","type":3},
                        {"position":23,"spelling":" ","type":6},
                        {"position":24,"spelling":"ten","type":2},
                        {"position":25,"spelling":" ","type":6},
                        {"position":26,"spelling":"o'clock","type":2},
                        {"position":27,"spelling":",","type":1},
                        {"position":28,"spelling":" ","type":6},
                        {"position":29,"spelling":"an","type":4},
                        {"position":30,"spelling":" ","type":6},
                        {"position":31,"spelling":"officer","type":2},
                        {"position":32,"spelling":" ","type":6},
                        {"position":33,"spelling":"and","type":2},
                        {"position":34,"spelling":" ","type":6},
                        {"position":35,"spelling":"four","type":2},
                        {"position":36,"spelling":" ","type":6},
                        {"position":37,"spelling":"soldiers","type":2},
                        {"position":38,"spelling":" ","type":6},
                        {"position":39,"spelling":"took","type":2},
                        {"position":40,"spelling":" ","type":6},
                        {"position":41,"spelling":"him","type":2},
                        {"position":42,"spelling":" ","type":6},
                        {"position":43,"spelling":"through","type":3},
                        {"position":44,"spelling":" ","type":6},
                        {"position":45,"spelling":"the","type":4},
                        {"position":46,"spelling":" ","type":6},
                        {"position":47,"spelling":"streets","type":2},
                        {"position":48,"spelling":" ","type":6},
                        {"position":49,"spelling":"to","type":3},
                        {"position":50,"spelling":" ","type":6},
                        {"position":51,"spelling":"the","type":4},
                        {"position":52,"spelling":" ","type":6},
                        {"position":53,"spelling":"shore","type":2},
                        {"position":54,"spelling":".","type":1},
                        {"position":55,"spelling":" ","type":6},
                        {"position":56,"spelling":"They","type":2},
                        {"position":57,"spelling":" ","type":6},
                        {"position":58,"spelling":"put","type":2},
                        {"position":59,"spelling":" ","type":6},
                        {"position":60,"spelling":"Dantes","type":2},
                        {"position":61,"spelling":" ","type":6},
                        {"position":62,"spelling":"in","type":3},
                        {"position":63,"spelling":" ","type":6},
                        {"position":64,"spelling":"a","type":4},
                        {"position":65,"spelling":" ","type":6},
                        {"position":66,"spelling":"boat","type":2},
                        {"position":67,"spelling":".","type":1},
                        {"position":68,"spelling":"\n","type":6},
                        {"position":69,"spelling":"Then","type":2},
                        {"position":70,"spelling":" ","type":6},
                        {"position":71,"spelling":"they","type":2},
                        {"position":72,"spelling":" ","type":6},
                        {"position":73,"spelling":"watched","type":2},
                        {"position":74,"spelling":" ","type":6},
                        {"position":75,"spelling":"him","type":2},
                        {"position":76,"spelling":" ","type":6},
                        {"position":77,"spelling":"as","type":2},
                        {"position":78,"spelling":" ","type":6},
                        {"position":79,"spelling":"the","type":4},
                        {"position":80,"spelling":" ","type":6},
                        {"position":81,"spelling":"boat","type":2},
                        {"position":82,"spelling":" ","type":6},
                        {"position":83,"spelling":"moved","type":2},
                        {"position":84,"spelling":" ","type":6},
                        {"position":85,"spelling":"away","type":2},
                        {"position":86,"spelling":".","type":1},
                        {"position":87,"spelling":"\n","type":6},
                        {"position":88,"spelling":"'","type":1},
                        {"position":89,"spelling":"What","type":2},
                        {"position":90,"spelling":" ","type":6},
                        {"position":91,"spelling":"is","type":2},
                        {"position":92,"spelling":" ","type":6},
                        {"position":93,"spelling":"happening","type":2},
                        {"position":94,"spelling":"?","type":1},
                        {"position":95,"spelling":"'","type":1},
                        {"position":96,"spelling":" ","type":6},
                        {"position":97,"spelling":"Edmond","type":2},
                        {"position":98,"spelling":" ","type":6},
                        {"position":99,"spelling":"thought","type":2},
                        {"position":100,"spelling":" ","type":6},
                        {"position":101,"spelling":"wildly","type":2},
                        {"position":102,"spelling":".","type":1},
                        {"position":103,"spelling":" ","type":6},
                        {"position":104,"spelling":"'","type":1},
                        {"position":105,"spelling":"The","type":2},
                        {"position":106,"spelling":" ","type":6},
                        {"position":107,"spelling":"judge","type":2},
                        {"position":108,"spelling":" ","type":6},
                        {"position":109,"spelling":"was","type":2},
                        {"position":110,"spelling":" ","type":6},
                        {"position":111,"spelling":"kind","type":2},
                        {"position":112,"spelling":" ","type":6},
                        {"position":113,"spelling":"to","type":3},
                        {"position":114,"spelling":" ","type":6},
                        {"position":115,"spelling":"me","type":2},
                        {"position":116,"spelling":".","type":1},
                        {"position":117,"spelling":" ","type":6},
                        {"position":118,"spelling":"He","type":2},
                        {"position":119,"spelling":" ","type":6},
                        {"position":120,"spelling":"told","type":2},
                        {"position":121,"spelling":" ","type":6},
                        {"position":122,"spelling":"me","type":2},
                        {"position":123,"spelling":" ","type":6},
                        {"position":124,"spelling":"not","type":2},
                        {"position":125,"spelling":" ","type":6},
                        {"position":126,"spelling":"to","type":3},
                        {"position":127,"spelling":" ","type":6},
                        {"position":128,"spelling":"be","type":2},
                        {"position":129,"spelling":" ","type":6},
                        {"position":130,"spelling":"afraid","type":2},
                        {"position":131,"spelling":".","type":1},
                        {"position":132,"spelling":" ","type":6},
                        {"position":133,"spelling":"He","type":2},
                        {"position":134,"spelling":" ","type":6},
                        {"position":135,"spelling":"only","type":2},
                        {"position":136,"spelling":" ","type":6},
                        {"position":137,"spelling":"told","type":2},
                        {"position":138,"spelling":" ","type":6},
                        {"position":139,"spelling":"me","type":2},
                        {"position":140,"spelling":" ","type":6},
                        {"position":141,"spelling":"not","type":2},
                        {"position":142,"spelling":" ","type":6},
                        {"position":143,"spelling":"to","type":3},
                        {"position":144,"spelling":" ","type":6},
                        {"position":145,"spelling":"say","type":2},
                        {"position":146,"spelling":" ","type":6},
                        {"position":147,"spelling":"the","type":4},
                        {"position":148,"spelling":" ","type":6},
                        {"position":149,"spelling":"name","type":2},
                        {"position":150,"spelling":" ","type":6},
                        {"position":151,"spelling":"Noirtier","type":2},
                        {"position":152,"spelling":".","type":1},
                        {"position":153,"spelling":" ","type":6},
                        {"position":154,"spelling":"And","type":2},
                        {"position":155,"spelling":" ","type":6},
                        {"position":156,"spelling":"he","type":2},
                        {"position":157,"spelling":" ","type":6},
                        {"position":158,"spelling":"destroyed","type":2},
                        {"position":159,"spelling":" ","type":6},
                        {"position":160,"spelling":"the","type":4},
                        {"position":161,"spelling":" ","type":6},
                        {"position":162,"spelling":"letter","type":2},
                        {"position":163,"spelling":" ","type":6},
                        {"position":164,"spelling":"in","type":3},
                        {"position":165,"spelling":" ","type":6},
                        {"position":166,"spelling":"front","type":2},
                        {"position":167,"spelling":" ","type":6},
                        {"position":168,"spelling":"of","type":3},
                        {"position":169,"spelling":" ","type":6},
                        {"position":170,"spelling":"me","type":2},
                        {"position":171,"spelling":".","type":1},
                        {"position":172,"spelling":"'","type":1},
                        {"position":173,"spelling":"\n","type":6},
                        {"position":174,"spelling":"Dantes","type":2},
                        {"position":175,"spelling":" ","type":6},
                        {"position":176,"spelling":"looked","type":2},
                        {"position":177,"spelling":" ","type":6},
                        {"position":178,"spelling":"into","type":3},
                        {"position":179,"spelling":" ","type":6},
                        {"position":180,"spelling":"the","type":4},
                        {"position":181,"spelling":" ","type":6},
                        {"position":182,"spelling":"darkness","type":2},
                        {"position":183,"spelling":".","type":1},
                        {"position":184,"spelling":" ","type":6},
                        {"position":185,"spelling":"They","type":2},
                        {"position":186,"spelling":" ","type":6},
                        {"position":187,"spelling":"were","type":2},
                        {"position":188,"spelling":" ","type":6},
                        {"position":189,"spelling":"going","type":2},
                        {"position":190,"spelling":" ","type":6},
                        {"position":191,"spelling":"out","type":2},
                        {"position":192,"spelling":" ","type":6},
                        {"position":193,"spelling":"to","type":3},
                        {"position":194,"spelling":" ","type":6},
                        {"position":195,"spelling":"sea","type":2},
                        {"position":196,"spelling":".","type":1},
                        {"position":197,"spelling":" ","type":6},
                        {"position":198,"spelling":"They","type":2},
                        {"position":199,"spelling":" ","type":6},
                        {"position":200,"spelling":"were","type":2},
                        {"position":201,"spelling":" ","type":6},
                        {"position":202,"spelling":"sailing","type":2},
                        {"position":203,"spelling":" ","type":6},
                        {"position":204,"spelling":"away","type":2},
                        {"position":205,"spelling":" ","type":6},
                        {"position":206,"spelling":"from","type":3},
                        {"position":207,"spelling":" ","type":6},
                        {"position":208,"spelling":"everything","type":2},
                        {"position":209,"spelling":" ","type":6},
                        {"position":210,"spelling":"that","type":2},
                        {"position":211,"spelling":" ","type":6},
                        {"position":212,"spelling":"he","type":2},
                        {"position":213,"spelling":" ","type":6},
                        {"position":214,"spelling":"loved","type":2},
                        {"position":215,"spelling":".","type":1},
                        {"position":216,"spelling":" ","type":6},
                        {"position":217,"spelling":"He","type":2},
                        {"position":218,"spelling":" ","type":6},
                        {"position":219,"spelling":"turned","type":2},
                        {"position":220,"spelling":" ","type":6},
                        {"position":221,"spelling":"to","type":3},
                        {"position":222,"spelling":" ","type":6},
                        {"position":223,"spelling":"the","type":4},
                        {"position":224,"spelling":" ","type":6},
                        {"position":225,"spelling":"nearest","type":2},
                        {"position":226,"spelling":" ","type":6},
                        {"position":227,"spelling":"soldier","type":2},
                        {"position":228,"spelling":".","type":1},
                        {"position":229,"spelling":"\n","type":6},
                        {"position":230,"spelling":"'","type":1},
                        {"position":231,"spelling":"Friend","type":2},
                        {"position":232,"spelling":",","type":1},
                        {"position":233,"spelling":"'","type":1},
                        {"position":234,"spelling":" ","type":6},
                        {"position":235,"spelling":"he","type":2},
                        {"position":236,"spelling":" ","type":6},
                        {"position":237,"spelling":"said","type":2},
                        {"position":238,"spelling":",","type":1},
                        {"position":239,"spelling":" ","type":6},
                        {"position":240,"spelling":"'","type":1},
                        {"position":241,"spelling":"please","type":2},
                        {"position":242,"spelling":" ","type":6},
                        {"position":243,"spelling":"tell","type":2},
                        {"position":244,"spelling":" ","type":6},
                        {"position":245,"spelling":"me","type":2},
                        {"position":246,"spelling":" ","type":6},
                        {"position":247,"spelling":"where","type":2},
                        {"position":248,"spelling":" ","type":6},
                        {"position":249,"spelling":"we","type":2},
                        {"position":250,"spelling":" ","type":6},
                        {"position":251,"spelling":"are","type":2},
                        {"position":252,"spelling":" ","type":6},
                        {"position":253,"spelling":"going","type":2},
                        {"position":254,"spelling":".","type":1},
                        {"position":255,"spelling":" ","type":6},
                        {"position":256,"spelling":"I","type":2},
                        {"position":257,"spelling":" ","type":6},
                        {"position":258,"spelling":"am","type":2},
                        {"position":259,"spelling":" ","type":6},
                        {"position":260,"spelling":"Edmond","type":2},
                        {"position":261,"spelling":" ","type":6},
                        {"position":262,"spelling":"Dantes","type":2},
                        {"position":263,"spelling":",","type":1},
                        {"position":264,"spelling":" ","type":6},
                        {"position":265,"spelling":"a","type":4},
                        {"position":266,"spelling":" ","type":6},
                        {"position":267,"spelling":"seaman","type":2},
                        {"position":268,"spelling":",","type":1},
                        {"position":269,"spelling":" ","type":6},
                        {"position":270,"spelling":"and","type":2},
                        {"position":271,"spelling":" ","type":6},
                        {"position":272,"spelling":"a","type":4},
                        {"position":273,"spelling":" ","type":6},
                        {"position":274,"spelling":"man","type":2},
                        {"position":275,"spelling":" ","type":6},
                        {"position":276,"spelling":"who","type":2},
                        {"position":277,"spelling":" ","type":6},
                        {"position":278,"spelling":"loves","type":2},
                        {"position":279,"spelling":" ","type":6},
                        {"position":280,"spelling":"the","type":4},
                        {"position":281,"spelling":" ","type":6},
                        {"position":282,"spelling":"king","type":2},
                        {"position":283,"spelling":".","type":1},
                        {"position":284,"spelling":" ","type":6},
                        {"position":285,"spelling":"Tell","type":2},
                        {"position":286,"spelling":" ","type":6},
                        {"position":287,"spelling":"me","type":2},
                        {"position":288,"spelling":" ","type":6},
                        {"position":289,"spelling":"where","type":2},
                        {"position":290,"spelling":" ","type":6},
                        {"position":291,"spelling":"we","type":2},
                        {"position":292,"spelling":" ","type":6},
                        {"position":293,"spelling":"are","type":2},
                        {"position":294,"spelling":" ","type":6},
                        {"position":295,"spelling":"going","type":2},
                        {"position":296,"spelling":".","type":1},
                        {"position":297,"spelling":"'","type":1},
                        {"position":298,"spelling":"\n","type":6},
                        {"position":299,"spelling":"'","type":1},
                        {"position":300,"spelling":"You","type":2},
                        {"position":301,"spelling":" ","type":6},
                        {"position":302,"spelling":"were","type":2},
                        {"position":303,"spelling":" ","type":6},
                        {"position":304,"spelling":"born","type":2},
                        {"position":305,"spelling":" ","type":6},
                        {"position":306,"spelling":"in","type":3},
                        {"position":307,"spelling":" ","type":6},
                        {"position":308,"spelling":"Marseilles","type":2},
                        {"position":309,"spelling":" ","type":6},
                        {"position":310,"spelling":"and","type":2},
                        {"position":311,"spelling":" ","type":6},
                        {"position":312,"spelling":"you","type":2},
                        {"position":313,"spelling":" ","type":6},
                        {"position":314,"spelling":"are","type":2},
                        {"position":315,"spelling":" ","type":6},
                        {"position":316,"spelling":"a","type":4},
                        {"position":317,"spelling":" ","type":6},
                        {"position":318,"spelling":"seaman","type":2},
                        {"position":319,"spelling":".","type":1},
                        {"position":320,"spelling":" ","type":6},
                        {"position":321,"spelling":"Look","type":2},
                        {"position":322,"spelling":"!","type":1},
                        {"position":323,"spelling":"'","type":1},
                        {"position":324,"spelling":"\n","type":6},
                        {"position":325,"spelling":"They","type":2},
                        {"position":326,"spelling":" ","type":6},
                        {"position":327,"spelling":"were","type":2},
                        {"position":328,"spelling":" ","type":6},
                        {"position":329,"spelling":"going","type":2},
                        {"position":330,"spelling":" ","type":6},
                        {"position":331,"spelling":"to","type":3},
                        {"position":332,"spelling":" ","type":6},
                        {"position":333,"spelling":"the","type":4},
                        {"position":334,"spelling":" ","type":6},
                        {"position":335,"spelling":"prison","type":2},
                        {"position":336,"spelling":".","type":1}
                    ]
                }
            };
            modified = true;
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
