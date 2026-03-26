let body = $response.body;
if (body) {
    try {
        let obj = JSON.parse(body);
        let modified = false;
        const adPatterns = /^(ad|ads|advert|banner|promo|direct|sponsor|metrica|statistics|analytics|survey)/i;
        function scanner(node) {
            if (!node || typeof node !== 'object') return node;
            if (Array.isArray(node)) {
                return node.filter(item => {
                    if (item && typeof item === 'object') {
                        const isAd = item.type?.toString().match(adPatterns) || 
                                     item.layout?.toString().match(adPatterns) || 
                                     item.is_ad === true || item.ad_info || item.is_promoted === true;
                        if (isAd) { modified = true; return false; }
                        scanner(item);
                    }
                    return true;
                });
            }
            Object.keys(node).forEach(key => {
                if (key.match(adPatterns)) {
                    delete node[key];
                    modified = true;
                } else if (typeof node[key] === 'object') {
                    scanner(node[key]);
                }
            });
            return node;
        }
        obj = scanner(obj);
        if (modified) body = JSON.stringify(obj);
    } catch (e) {}
}
$done({ body });