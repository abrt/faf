$(document).ready(function() {
    $('form#filter').submit(function() {
        var url = '';
        $('li.active a').each(function() {
          if($(this).attr('href').length > url.length) {
            url = $(this).attr('href');
          }
        });
        var options = $(this).find('select').map(function() {
                        return $(this).find('option:selected').map(function() {
                          return $(this).attr('value');
                        }).get().join(',');
                      }).get().join('/');
        window.location = url + options + '/';
        return false;
    });
});
