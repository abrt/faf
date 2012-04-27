function showTooltip(x, y, contents) {
    $('<div id="tooltip">' + contents + '</div>').css( {
        top: y + 5,
        left: x + 5,
    }).appendTo("body").fadeIn(200);
}

function plotRepotGraph(data, minTickSizeLabel) {
    var graph_options = {
       xaxis: {
           mode: "time", minTickSize: [1, minTickSizeLabel], autoscaleMargin: 0.02,
       },
       series: {
           points: {show: true},
           lines: {show: true},
       },
       yaxis: {
           tickDecimals: 0
       },
       grid: {
           hoverable: true,
           clickable: true,
           borderColor: '#aaa',
           borderWidth: 1,
       },
    };

    var data_config = [];
    for(var i=0;i<data.length;++i) {
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
            showTooltip(item.pageX, item.pageY,
                        parseInt(y) + " problems");
        }
      } else {
          $("#tooltip").remove();
          previousPoint = null;
      }
    });
}
