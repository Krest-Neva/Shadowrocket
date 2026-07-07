if (typeof $response !== 'undefined' && $response.body) {
    let body = $response.body;
    try {
        let obj = JSON.parse(body);
        if (obj.marketingUserType) {
            obj.marketingUserType = "registered premium";
        }
        $done({ body: JSON.stringify(obj) });
    } catch (e) {
        $done({});
    }
} else {
    $done({});
}