let url = $request.url;
const NEW_TZ = "Europe/Amsterdam";

if (/[?&](?:client-)?timezone=/i.test(url)) {
    const before = url;
    url = url.replace(/([?&](?:client-)?timezone=)([^&#]*)/gi, function (m, prefix, oldValue) {
        const newValue = oldValue.indexOf('%') >= 0
            ? encodeURIComponent(NEW_TZ)
            : NEW_TZ;
        return prefix + newValue;
    });
    if (url !== before) {
        $done({ url });
    } else {
        $done({});
    }
} else {
    $done({});
}
