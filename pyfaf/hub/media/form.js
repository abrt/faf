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

        options = options + '/'
        options = options.replace(/\/\//g, '/*/');
        window.location = url + options;
        return false;
    });

    var sel = $('select[multiple] option:selected[value="*"]').removeAttr('selected');
    $('select[multiple]').select2({placeholder: sel.text()});

    // if filter is enabled, update both Hot & Longterm problem links to preserve it
    var match;
    if(match = window.location.pathname.match('/problems/(hot|longterm)/(.*)')) {
        // find button with href ending like this
        var second_button=$('a[href$="/problems/'+
            (match[1] == 'hot' ? 'longterm' : 'hot') +'/"]');

        // skip top nav button
        if(second_button.length >= 2)
            second_button = $(second_button[1]);

        // append filter string
        second_button.attr('href',
            second_button.attr('href') + match[2]);
    }
});
