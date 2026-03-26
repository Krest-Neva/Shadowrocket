let body = $response.body;
if (body) {
    try {
        let obj = JSON.parse(body);
        let modified = false;
        const adPatterns = /^(?:ad|ads|advert|banner|promo|direct|sponsor|sponsored|metrica|statistics|analytics|survey|widget|tracking)/i;
        const adPattern2 = /@monetize|UrbanAds|HorizontalIncut|Madv|MediaCarousel|searchIncut/i;
        function scanner(node) {
            if (!node || typeof node !== 'object') return node;
            if (Array.isArray(node)) {
                return node.filter(item => {
                    if (item && typeof item === 'object') {
                        // Удаляем объект, если явно рекламный
                        if (item.is_ad === true || item.is_promoted === true ||
                            adPattern2.test(item.widgetName) || adPattern2.test(item.apiaryWidgetName) ||
                            item.dataAuto === 'searchIncut' || item.dataZoneData?.bannerUrl) {
                            modified = true;
                            return false;
                        }
                        scanner(item);
                    }
                    return true;
                });
            }
            Object.keys(node).forEach(key => {
                if (adPatterns.test(key)) {
                    delete node[key];
                    modified = true;
                } else {
                    // Например, если поле widgetName содержит рекламу
                    if ((key === 'widgetName' || key === 'apiaryWidgetName') && adPattern2.test(node[key])) {
                        delete node[key];
                        modified = true;
                    } else {
                        scanner(node[key]);
                    }
                }
            });
            return node;
        }
        obj = scanner(obj);
        if (modified) body = JSON.stringify(obj);
    } catch (e) {}
}
$done({ body });