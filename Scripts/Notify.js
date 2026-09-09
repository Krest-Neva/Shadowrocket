(function() {
    var def = {
        title: "Уведомление",
        message: "я всё вижу куда ты заходишь",
        cooldown: 86400
    };
    try {
        var raw = typeof $argument !== 'undefined' ? $argument : '{}';
        var arg = JSON.parse(raw);
        var opt = Object.assign({}, def, arg);
    } catch (e) {
        var opt = def;
    }
    var STORE_KEY = 'notify_last_time_' + opt.title;
    var now = Math.floor(Date.now() / 1000);
    var last = parseInt($persistentStore.read(STORE_KEY)) || 0;
    if (now - last >= opt.cooldown) {
        $notification.post(opt.title, opt.message, "");
        $persistentStore.write(STORE_KEY, now.toString());
    }
    $done({});
})();
