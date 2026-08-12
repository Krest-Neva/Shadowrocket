if (typeof $response !== 'undefined' && $response.body && $response.status == 403) {
    try {
        let body = $response.body;
        if (body.indexOf('Доступ ограничен: проблема с IP') !== -1) {
            body = body.replace(/Доступ ограничен: проблема с IP/g, 'Бан по причине пидорас');
            body = body.replace(/<title>Доступ ограничен: проблема с IP<\/title>/g, '<title>Бан по причине пидорас</title>');
            $done({ body });
        } else {
            $done({});
        }
    } catch (e) {
        $done({});
    }
} else {
    $done({});
}
