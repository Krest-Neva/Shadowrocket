let body = $response.body;
if (!body) $done({});
try {
    let json = JSON.parse(body);
    let modified = false;
    const adKeyPattern = /^(?:ad|ads|advert|direct|sponsor|sponsored|metrica|statistics|analytics|survey|tracking)$/i;
    const monetPattern = /@monetize|UrbanAds|HorizontalIncut|Madv|MediaCarousel|searchIncut/i;
    function scanner(obj) {
        if (!obj || typeof obj !== 'object') return obj;
        if (Array.isArray(obj)) {
            return obj.filter(item => {
                if (item && typeof item === 'object') {
                    if (
                        item.is_ad === true ||
                        item.is_promoted === true ||
                        (item.type && item.type === 'ad') ||           // точно 'ad', а не содержит
                        (item.layout && item.layout === 'ad') ||       // точно 'ad'
                        (item.widgetName && monetPattern.test(item.widgetName.toString())) ||
                        (item.apiaryWidgetName && monetPattern.test(item.apiaryWidgetName.toString())) ||
                        (item.dataAuto === 'searchIncut') ||
                        (item.dataZoneData && item.dataZoneData.bannerUrl)
                    ) {
                        modified = true;
                        return false;
                    }
                    scanner(item);
                }
                return true;
            });
        }
        for (let key in obj) {
            if (adKeyPattern.test(key)) {
                delete obj[key];
                modified = true;
            } else {
                scanner(obj[key]);
            }
        }
        return obj;
    }
    json = scanner(json);
    if (modified) {
        body = JSON.stringify(json);
    }
} catch(e) {
}
$done({ body });