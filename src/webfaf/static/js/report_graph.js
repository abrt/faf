const showTooltip = (x, y, contents) => (
  $('<div id="tooltip"></div>')
  .html(contents)
  .css({
    top: y + 5,
    left: x + 5,
  }).appendTo('body').fadeIn(200)
);

const slugify = (input_string) => (
  input_string
  .replace(/\s+/g, '-')
  .replace(/[^a-zA-Z0-9\-]/g,'')
  .toLowerCase()
);

const plotReportGraph = (data, tick_unit) => {
  tick_unit = {'d': 'day', 'w': 'week', 'm': 'month', '*': '*'}[tick_unit];

  const msday = 86400000; // one day in ms
  const temp_data = data[0].data;
  const x_min = temp_data[0][0];
  const x_max = temp_data[temp_data.length-1][0];
  let x_axis_options = {};

  if (tick_unit == 'week') {
    const x_margin = msday * 7;
    const my_ticks = [x_min - x_margin];

    for(var i=0; i<data[0].data.length; ++i) {
      my_ticks.push(data[0].data[i][0]); // ticks are dates
    }

    my_ticks.push(x_max + x_margin);
    my_ticks.push(x_max + x_margin * 2);

    x_axis_options = {
      min: x_min - x_margin,
      max: x_max + x_margin*2,
      ticks: my_ticks,
      mode: 'time',
      timeformat: '%b %d',
    };
  } else if (tick_unit == 'day') {
    x_axis_options = {
      min: x_min - msday,
      max: x_max + msday * 2,
      ticks: 20,
      mode: 'time',
    };
  } else if (tick_unit == 'month') {
    x_axis_options = {
      min: x_min - msday * 30,
      max: x_max + msday * 60,
      ticks: 12,
      mode: 'time',
    };
  } else {
    x_axis_options = {
      mode: 'time',
      ticks: 12,
      autoscaleMargin: 0.1,
    };
  }

  const graph_options = {
    axisLabels: {
      show: true
    },
    xaxes: [{
      axisLabel: 'Date',
    }],
    yaxes: [{
      axisLabel: 'Number of incoming reports',
      position: 'left',
    }],
    xaxis: x_axis_options,
    yaxis: {
      min: 0,
      tickDecimals: 0,
    },
    colors: [
      '#edc240', '#edc240', '#afd8f8', '#afd8f8', '#cb4b4b',
      '#cb4b4b', '#4da74d', '#4da74d', '#9440ed', '#9440ed',
    ],
    series: {
      points: { show: true },
      lines: { show: true },
    },
    grid: {
      hoverable: true,
      clickable: true,
      borderColor: '#aaa',
      borderWidth: 0,
    },
    legend: {
      labelBoxBorderColor: 'transparent',
    },
  };

  const data_config = [];
  data.forEach((value) => {
    data_config.push({
      data: value.data.slice(0, -1),
      label: value.label
    });
    data_config.push({
      data: value.data.slice(-1),
      points: { symbol: 'triangle' }
    });
  });

  $.plot($('#placeholder'), data_config, graph_options);

  let previousPoint = null;
  $('#placeholder').bind('plothover', (event, pos, item) => {
    if (item) {
      if (previousPoint != item.dataIndex) {
        previousPoint = item.dataIndex;
        $('#tooltip').remove();
        var x = item.datapoint[0].toFixed(2),
          y = item.datapoint[1].toFixed(2);
        showTooltip(item.pageX, item.pageY, parseInt(y) + ' reports');
      }
    } else {
      $('#tooltip').remove();
      previousPoint = null;
    }
  });

  $('#placeholder').bind('plotclick', (event, pos, item) => {
    if(!item) return;

    // Get OpSysReleas id from the data label
    var $options = $('#opsysreleases option');
    var opsysrelease_id = false;
    for(var i=0; i<$options.length;i++) {
      var opt = $options[i];
      if($(opt).text()==item.series.label) {
        opsysrelease_id = $(opt).attr('value');
        break;
      }
    }

    const date_since = moment(item.datapoint[0]);
    const date_since_string = date_since.format('YYYY-MM-DD');
    const date_to_string = date_since_string;
    if (minTickSizeLabel == 'week') {
      date_to_string = date_since.add(1, 'weeks').format('YYYY-MM-DD');
    } else if (minTickSizeLabel == 'month') {
      date_to_string = date_since.add(1, 'months').format('YYYY-MM-DD');
    }

    const url = $('#href_problems').attr('href') +
      `?opsysreleases=${opsysrelease_id}&daterange=${date_since_string}:${date_to_string}`;

    window.location = url;
    return;
  });
}
