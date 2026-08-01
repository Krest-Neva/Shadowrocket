if (typeof $response !== 'undefined' && $response.body) {
    try {
        let body = $response.body;
        let url = $request ? $request.url : '';
        let modified = false;
        if (body.trim().startsWith('{') || body.trim().startsWith('[')) {
            try {
                let json = JSON.parse(body);
                function traverse(obj) {
                    if (typeof obj !== 'object' || obj === null) return;
                    for (let key in obj) {
                        if (key === 'is_unlimited' && typeof obj[key] === 'boolean') {
                            obj[key] = true;
                            modified = true;
                        } else if (key === 'balance_rub' && typeof obj[key] === 'string') {
                            obj[key] = '30000000.00';
                            modified = true;
                        } else if (typeof obj[key] === 'object') {
                            traverse(obj[key]);
                        }
                    }
                }
                traverse(json);
                if (modified) {
                    body = JSON.stringify(json);
                }
            } catch (e) {}
        }
        if (!modified && body.includes('window.DJANGO_DATA')) {
            let regex = /window\.DJANGO_DATA\s*=\s*({[^;]*});/;
            let match = body.match(regex);
            if (match) {
                let jsonStr = match[1];
                try {
                    let data = JSON.parse(jsonStr);
                    let dataModified = false;
                    function traverseData(obj) {
                        if (typeof obj !== 'object' || obj === null) return;
                        for (let key in obj) {
                            if (key === 'is_unlimited' && typeof obj[key] === 'boolean') {
                                obj[key] = true;
                                dataModified = true;
                            } else if (key === 'balance_rub' && typeof obj[key] === 'string') {
                                obj[key] = '30000000.00';
                                dataModified = true;
                            } else if (typeof obj[key] === 'object') {
                                traverseData(obj[key]);
                            }
                        }
                    }
                    traverseData(data);
                    if (dataModified) {
                        let newJsonStr = JSON.stringify(data);
                        body = body.replace(match[0], `window.DJANGO_DATA = ${newJsonStr};`);
                        modified = true;
                    }
                } catch (e) {}
            }
        }
        if (modified) {
            $done({ body: body });
        } else {
            $done({});
        }
    } catch (e) {
        $done({});
    }
} else {
    $done({});
}
