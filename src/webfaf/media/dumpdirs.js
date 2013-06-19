function dumpdiraction(action) {
    var url = '';
    $('li.active a').each(function() {
        if($(this).attr('href').length > url.length) {
            url = $(this).attr('href');
        }
    });

    var options = $('input:checked').map(function() {
        return $(this).attr('value');
    }).get().join(',');

    if (options) {
        window.location = url + action + '/' + options;
    }
    else {
        alert("Empty selection for action " + action);
    }
};

function toggleChecked(selector, checked) {
    $(selector).each(function(){$(this).attr('checked', checked);});
};
