(function ($) {
    function init(plot) {
        plot.hooks.draw.push(function (plot, ctx) {
            $.each(plot.getAxes(), function(axisName, axis) {
                if(axisName.charAt(0) == 'y') {
                    elem = plot.getPlaceholder().parent().find('#ylabel');

                    elem.css('top',
                        plot.getPlaceholder().offset().top
                        + plot.height()/2 - elem.outerHeight()/2
                        + 'px');

                    elem.css('left',
                        plot.getPlaceholder().offset().left
                        - (elem.outerWidth()/2 + 15)
                        + 'px');
                }
            });
        });
    }

    $.plot.plugins.push({
        init: init,
        name: 'simplelabel',
        version: '0.1'
    });

})(jQuery);
