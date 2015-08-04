var ajax = function(method, url, data, callback) {
    // compatible with IE7+, Firefox, Chrome, Opera, Safari
    var request = new XMLHttpRequest();
    request.onreadystatechange = function() {
        if (request.readyState == 4 && request.status == 200) {
            if (callback != null) {
                callback(request.responseText);
            }
        }
    }
    
    request.open(method, url, true);
    if (data != null) {
        request.setRequestHeader("Content-type", "application/x-www-form-urlencoded");

        var query = [];
        for (var key in data) {
            if (data.hasOwnProperty(key)) {
                query.push(encodeURIComponent(key) + '=' + encodeURIComponent(data[key]));
            }
        }

        request.send(query.join("&"));
    }
    else {
        request.send();
    }
};
