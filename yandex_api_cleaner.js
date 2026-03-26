let body = $response.body;
if (!body) $done({});
try {
    let json = JSON.parse(body);
    let modified = false;
    const adPattern = /^(?:ad|ads|advert|banner|promo|direct|sponsor|sponsored|metrica|statistics|analytics|survey|widget|tracking)/i;
    const monetPattern = /@monetize|UrbanAds|HorizontalIncut|Madv|MediaCarousel|searchIncut/i;

    function scanner(obj) {
        if (!obj || typeof obj !== 'object') return obj;
        if (Array.isArray(obj)) {
            return obj.filter(item => {
                if (item && typeof item === 'object') {
                    if (
                        item.is_ad === true ||
                        item.is_promoted === true ||
                        (item.type && adPattern.test(item.type.toString())) ||
                        (item.layout && adPattern.test(item.layout.toString())) ||
                        (item.widgetName && monetPattern.test(item.widgetName.toString())) ||
                        (item.apiaryWidgetName && monetPattern.test(item.apiaryWidgetName.toString())) ||
                        item.dataAuto === 'searchIncut' ||
                        item.dataZoneData?.bannerUrl
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
            if (adPattern.test(key) ||
                (key === 'widgetName' && monetPattern.test(obj[key])) ||
                (key === 'apiaryWidgetName' && monetPattern.test(obj[key])) ||
                key === 'dataAuto' ||
                key === 'dataZoneData' ||
                key === 'banner' ||
                key === 'banners'
            ) {
                delete obj[key];
                modified = true;
            } else {
                scanner(obj[key]);
            }
        }
        return obj;
    }

    json = scanner(json);
    if (modified) body = JSON.stringify(json);
} catch(e) {}
$done({ body });