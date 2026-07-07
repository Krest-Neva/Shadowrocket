let body = $response.body;
try {
    let obj = JSON.parse(body);
    console.log("Radio_Plus: Original = " + body);
    if (obj && typeof obj === 'object' && obj.hasOwnProperty('isAvailable')) {
        obj.isAvailable = true;
        let newBody = JSON.stringify(obj);
        console.log("Radio_Plus: Modified = " + newBody);
        $done({body: newBody});
    } else {
        console.log("Radio_Plus: No 'isAvailable' field, passing through");
        $done({body: body});
    }
} catch (e) {
    console.log("Radio_Plus: Error = " + e);
    $done({body: body});
}
