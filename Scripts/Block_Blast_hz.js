let body = $response.body;
if (body) {
    try {
        let jsonString = body;
        if (typeof body !== 'string') {
            const uint8Array = new Uint8Array(body);
            jsonString = String.fromCharCode.apply(null, uint8Array);
        }
        let data = JSON.parse(jsonString);
        if (data && data.history_data) {
            data.history_data.his_max_score = "999999";
            data.history_data.his_active_days = 999999;
            data.history_data.day_7_game_time = 9999999;
            data.history_data.device_type = "Nokia 3310";
            data.history_data.day_7_game_avg_score = 999999;
            data.history_data.day_1_game_avg_score = 999999;
        }
        $done({ body: JSON.stringify(data) });
    } catch (e) {
        $done({});
    }
} else {
    $done({});
}
