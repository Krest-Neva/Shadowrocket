if (typeof $response !== 'undefined') {
    try {
        console.log('[AvitoBan] URL: ' + $request.url);
        console.log('[AvitoBan] Status: ' + $response.status);
        console.log('[AvitoBan] Headers: ' + JSON.stringify($response.headers));

        if ($response.status == 403 && $response.body) {
            let body = $response.body;
            if (body instanceof Uint8Array) {
                let decoder = new TextDecoder('utf-8', { fatal: false });
                body = decoder.decode(body);
                console.log('[AvitoBan] Body decoded from Uint8Array');
            } else if (typeof body === 'string') {
                console.log('[AvitoBan] Body is string');
            } else {
                console.log('[AvitoBan] Body type: ' + typeof body);
                try { body = String(body); } catch (e) { body = ''; }
            }

            if (body && body.includes('Доступ ограничен: проблема с IP')) {
                console.log('[AvitoBan] Target phrase found, replacing...');
                body = body.replace(/Доступ ограничен: проблема с IP/g, 'Бан по причине пидорас');
                body = body.replace(/<title>Доступ ограничен: проблема с IP<\/title>/g, '<title>Бан по причине пидорас</title>');
                console.log('[AvitoBan] Replacement done. New body length: ' + body.length);
                $done({ body: body });
            } else {
                console.log('[AvitoBan] Target phrase NOT found in body.');
                if (body) {
                    let preview = body.substring(0, 300);
                    console.log('[AvitoBan] Body preview: ' + preview);
                } else {
                    console.log('[AvitoBan] Body is empty');
                }
                $done({});
            }
        } else {
            console.log('[AvitoBan] Status not 403 or no body. Status: ' + $response.status);
            $done({});
        }
    } catch (e) {
        console.log('[AvitoBan] Error: ' + e.message);
        $done({});
    }
} else {
    console.log('[AvitoBan] No response object');
    $done({});
}
