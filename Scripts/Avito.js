if (typeof $response !== 'undefined' && $response.body) {
    try {
        let body = $response.body;
        if (body.includes('Доступ ограничен: проблема с IP')) {
            body = body.replace(/Доступ ограничен: проблема с IP/g, 'Бан по причине пидорас');
            body = body.replace(/<title>Доступ ограничен: проблема с IP<\/title>/g, '<title>Бан по причине пидорас</title>');
            $done({ body: body });
        } else {
            $done({});
        }
    } catch (e) {
        $done({});
    }
} else {
    $done({});
}
