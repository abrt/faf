$(document).ready(function() {
    $('form#filter').submit(function() {
        var url = '';
        $('li.active a').each(function() {
          if($(this).attr('href').length > url.length) {
            url = $(this).attr('href');
          }
        });
        if(url == '/') {
            url = '/summary/';
        }
        $(this).find('select option:selected').each(function() {
            url += $(this).attr('value') + '/';
        });
        window.location = url;
        return false;
    });
});
