let body = $response.body;
if (!body) $done({});
try {
    let obj = JSON.parse(body);
    let modified = false;
    function cleanAds(data) {
        if (!data || typeof data !== 'object') return;

        if (Array.isArray(data)) {
            for (let i = data.length - 1; i >= 0; i--) {
                let item = data[i];
                if (item && typeof item === 'object') {
                    let isAd = item.is_ad === true ||
                               item.is_promoted === true ||
                               item.type === 'ad' ||
                               item.layout === 'ad' ||
                               item.dataAuto === 'searchIncut' ||
                               (item.widgetName && typeof item.widgetName === 'string' && item.widgetName.toLowerCase().includes('searchincut'));
                    if (isAd) {
                        data.splice(i, 1);
                        modified = true;
                    } else {
                        cleanAds(item);
                    }
                }
            }
        } else {
            for (let key in data) {
                cleanAds(data[key]);
            }
        }
    }
    cleanAds(obj);
    if (modified) {
        body = JSON.stringify(obj);
    }
} catch (e) {
}
$done({ body });
