let body = $response.body;
if (!body) { $done({}); return; }
try {
    let obj = JSON.parse(body);
    let modified = false;
    const adKeyPattern = /^(?:ad|ads|advert|banner|promo|direct|sponsor|sponsored|metrica|statistics|analytics|survey|widget|tracking)/i;
    const monetizePattern = /@monetize|UrbanAds|HorizontalIncut|Madv|MediaCarousel|searchIncut/i;
    function scan(node) {
        if (!node || typeof node !== 'object') return node;
        if (Array.isArray(node)) {
            return node.filter(item => {
                if (item && typeof item === 'object') {
                    if (item.is_ad === true || item.is_promoted === true ||
                        (item.type && adKeyPattern.test(item.type.toString())) ||
                        (item.layout && adKeyPattern.test(item.layout.toString())) ||
                        (item.widgetName && monetizePattern.test(item.widgetName.toString())) ||
                        (item.apiaryWidgetName && monetizePattern.test(item.apiaryWidgetName.toString())) ||
                        item.dataAuto === 'searchIncut' ||
                        item.dataZoneData?.bannerUrl
                    ) {
                        modified = true;
                        return false;
                    }
                    scan(item);
                }
                return true;
            });
        }
        for (let key of Object.keys(node)) {
            if (adKeyPattern.test(key) ||
                (key === 'widgetName' && monetizePattern.test(node[key])) ||
                (key === 'apiaryWidgetName' && monetizePattern.test(node[key])) ||
                key === 'dataAuto' || key === 'dataZoneData' ||
                key === 'banner' || key === 'banners'
            ) {
                delete node[key];
                modified = true;
            } else {
                scan(node[key]);
            }
        }
        return node;
    }
    obj = scan(obj);
    if (modified) {
        body = JSON.stringify(obj);
    }
} catch(e) {
}
$done({ body });