function showTooltip(x, y, contents) {
    $('<div id="tooltip">' + contents + '</div>').css( {
        top: y + 5,
        left: x + 5,
    }).appendTo("body").fadeIn(200);
}

function plotReportGraph(data, tick_unit) {
    var msday = 86400000; // one day in ms
    var temp_data = data[0].data;
    var x_min = temp_data[0][0];
    var x_max = temp_data[temp_data.length-1][0];
    var x_axis_options = {}

    if (tick_unit == 'week') {
        var x_margin = msday * 7;
        var my_ticks = [x_min - x_margin];

        for(var i=0; i<data[0].data.length; ++i) {
            my_ticks.push(data[0].data[i][0]); // ticks are dates
        }

        my_ticks.push(x_max + x_margin);
        my_ticks.push(x_max + x_margin*2);

        x_axis_options = {
            min: x_min - x_margin,
            max: x_max + x_margin*2,
            ticks: my_ticks,
            mode: "time",
        };
    } else if (tick_unit == 'day') {
        x_axis_options = {
            min: x_min - msday,
            max: x_max + msday*2,
            ticks: 20,
            mode: "time",
        };
    } else if (tick_unit == 'month') {
        x_axis_options = {
            min: x_min - msday*30,
            max: x_max + msday*60,
            ticks: 12,
            mode: "time",
        };
    } else {
        x_axis_options = {
            mode: "time",
            ticks: 12,
            autoscaleMargin: 0.1,
        };
    }

    var graph_options = {
        xaxis: x_axis_options,
        yaxis: {
            min: 0,
            tickDecimals: 0,
        },
        series: {
            points: {show: true},
            lines: {show: true},
        },
        grid: {
            hoverable: true,
            clickable: true,
            borderColor: '#aaa',
            borderWidth: 1,
        },
    };

    var data_config = [];
    for(var i=0; i<data.length; ++i) {
        data_config.push( {data: data[i].data, label: data[i].label} );
    }

    var previousPoint = null;
    $.plot($("#placeholder"), data_config, graph_options);
    $("#placeholder").bind("plothover", function (event, pos, item) {
        if (item) {
            if (previousPoint != item.dataIndex) {
                previousPoint = item.dataIndex;
                $("#tooltip").remove();
                var x = item.datapoint[0].toFixed(2),
                    y = item.datapoint[1].toFixed(2);
                showTooltip(item.pageX, item.pageY, parseInt(y) + " reports");
            }
        } else {
            $("#tooltip").remove();
            previousPoint = null;
        }
    });
}
