let body = $response.body;
try {
    let obj = JSON.parse(body);
    if (obj.hasOwnProperty('isAvailable')) {
        obj.isAvailable = true;
    }
    $done({ body: JSON.stringify(obj) });
} catch (e) {
    $done({});
}
