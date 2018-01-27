var gaescaffold = gaescaffold || {};

gaescaffold.logout = function(e) {
    e.preventDefault();
    document.getElementById("logout-form").submit();
};

gaescaffold.logout_link = document.getElementById("logout-link");
if (gaescaffold.logout_link) {
    gaescaffold.logout_link.addEventListener('click', gaescaffold.logout);
}

gaescaffold.ajax = function(method, url, data, callback) {
    // compatible with IE7+, Firefox, Chrome, Opera, Safari
    var request = new XMLHttpRequest();
    request.onreadystatechange = function() {
        if (request.readyState == 4 && request.status == 200) {
            if (callback != null) {
                callback(request.responseText);
            }
        }
    };
    
    request.open(method, url, true);
    if (data != null) {
        request.setRequestHeader('Content-type', 'application/x-www-form-urlencoded');

        var query = [];
        for (var key in data) {
            if (data.hasOwnProperty(key)) {
                query.push(encodeURIComponent(key) + '=' + encodeURIComponent(data[key]));
            }
        }

        request.send(query.join('&'));
    }
    else {
        request.send();
    }
};

gaescaffold.upload = function(e) {
    // at the time of submit swaps out a regular url for a blobstore one, then re-submits
    var form = this;
    if (form.getAttribute("data-ready")) {
        return;
    }

    e.preventDefault();
    var inputs = form.getElementsByTagName('input');
    for (var i=0; i < inputs.length; i++) {
        var input = inputs[i];
        if (input.type == 'submit') {
            if (input.disabled) {
                return;
            }
            else {
                input.disabled = true;
                break;
            }
        }
    }

    var data = {'url': form.action, 'csrf': form.csrf.value};
    gaescaffold.ajax('POST', '/api/upload', data, function(response) {
        var response_json = JSON.parse(response);
        form.action = response_json.url;
        form.setAttribute("data-ready", true);
        form.submit();
    });
};

gaescaffold.upload_forms = document.getElementsByClassName("upload-form");
for (var i=0; i < gaescaffold.upload_forms.length; i++) {
    gaescaffold.upload_forms[i].addEventListener('submit', gaescaffold.upload);
}

gaescaffold.error_name = document.getElementById("error-name");
if (gaescaffold.error_name) {
    var reason = gaescaffold.error_name.textContent || gaescaffold.error_name.innerText;
    gaescaffold.ajax("POST", "/logerror", {"reason": reason});
}

gaescaffold.MONTHS = ["January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December"];

gaescaffold.convert_timestamp = function(el) {
    var iso = el.getAttribute("datetime");
    var local = new Date(iso);
    var month = gaescaffold.MONTHS[local.getMonth()];
    var date_string = month + " " + local.getDate().toString() + ", " + local.getFullYear().toString();

    var hours = local.getHours();
    var ampm = "AM";
    if (hours > 11) {ampm = "PM";}
    if (hours > 12) {hours -= 12;}
    if (hours === 0) {hours = 12;}

    var minutes = local.getMinutes().toString();
    if (minutes.length < 2) {minutes = "0" + minutes;}

    var time_string = hours.toString() + ":" + minutes + " " + ampm;

    el.innerHTML = date_string + " " + time_string;
};

gaescaffold.times = document.getElementsByTagName("time");
for (var i=0; i < gaescaffold.times.length; i++) {
    gaescaffold.convert_timestamp(gaescaffold.times[i]);
}
