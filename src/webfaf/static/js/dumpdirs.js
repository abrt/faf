function dumpdiraction(action) {
    var url = window.location;

    var options = null;
    if (RegExp("all$").test(action)) {
        options = 'all';
        action = action.substring(0, action.length - 3);

    }
    else {
        options = $('input:checked').map(function() {
            return $(this).attr('value');
        }).get().join(',');
    }

    if (options) {
        window.location = url + action + '/' + options;
    }
    else {
        alert("Empty selection for action " + action);
    }
};
