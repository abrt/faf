function showTooltip(x, y, contents) {
    $('<div id="tooltip">' + contents + '</div>').css( {
        position: 'absolute',
        display: 'none',
        top: y + 5,
        left: x + 5,
        border: '1px solid #fdd',
        padding: '10px',
        'background-color': '#fee',
        opacity: 0.90
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

    $.plot($("#placeholder"), [{data: data, color: '#08C', label: 'Report count'}], graph_options);
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
