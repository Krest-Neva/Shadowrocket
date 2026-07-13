try {
    console.log(`[Nyme-Spy] URL: ${$request.url}`);
    
    if (typeof $request !== 'undefined' && $request.body) {
        console.log(`[Nyme-Spy] Req Body: ${$request.body}`);
    }
    
    if (typeof $response !== 'undefined' && $response.body) {
        console.log(`[Nyme-Spy] Res Body: ${$response.body}`);
    }
} catch (err) {
    console.log(`[Nyme-Spy] Error: ${err.message}`);
}

$done({});
