$(document).ready(() => {
  // Prepare checkbox-style dropdowns for multiselect fields.
  // Multiselect fields with no special powers.
  $('.multiselect[id]').each((_index, element) => {
    $(element).multiselect({
      includeSelectAllOption: true,
      selectAllValue: 'select-all',
      nonSelectedText: $(`label[for='${element.id}']`).text(),
    });
  });

  // Multiselect fields with filtering.
  $('.multiselect-filtered[id]').each((_index, element) => {
    $(element).multiselect({
      includeSelectAllOption: true,
      selectAllValue: 'select-all',
      enableFiltering: true,
      maxHeight: 200,
      nonSelectedText: $(`label[for='${element.id}']`).text(),
    });
  });

  // Multiselect fields with dynamic filtering.
  $('.multiselect-filtered-dynamic[id]').each((_index, element) => {
    const $this = $(element);
    const innerHtml = $this.html();

    // Keep only items that were selected previously.
    $this.find('option:not(:selected)').remove();
    $this.multiselect({
      includeSelectAllOption: true,
      selectAllValue: 'select-all',
      enableFiltering: true,
      maxHeight: 200,
      nonSelectedText: $(`label[for='${element.id}']`).text(),
      onDropdownShow: () => {
        // TODO: Why do we do this?
        $this.multiselect('destroy')
          .html(innerHtml)
          .multiselect({
            includeSelectAllOption: true,
            selectAllValue: 'select-all',
            enableFiltering: true,
            enableCaseInsensitiveFiltering: true,
            maxHeight: 200,
            nonSelectedText: $(`label[for='${element.id}']`).text(),
          })
          .parent()
          .find('.btn.multiselect')
          .click();
      }
    });
  });

  // Set up autocomplete for component names.
  const component_names = new Bloodhound({
    datumTokenizer: Bloodhound.tokenizers.obj.whitespace('name'),
    queryTokenizer: Bloodhound.tokenizers.whitespace,
    prefetch: {
      url: `${ROOT_URL}component_names.json`,
      filter: list => (
        list.map(componentName => ({ name: componentName }))
      )
    }
  });
  component_names.initialize();

  $('input.component-names').tagsinput({
    typeaheadjs: {
      name: 'component_names',
      displayKey: 'name',
      valueKey: 'name',
      source: component_names.ttAdapter()
    }
  });

  // Set up fields for picking dates.
  $('input.daterange').daterangepicker({
    locale: {
      // Set Monday as the first day of the week.
      firstDay: 1
    },
    ranges: {
      //'Today': [moment(), moment()],
      'Yesterday': [moment().subtract(1, 'days'), moment().subtract(1, 'days')],
      'Last 7 Days': [moment().subtract(6, 'days'), moment()],
      'Last 14 Days': [moment().subtract(13, 'days'), moment()],
      'Last 30 Days': [moment().subtract(29, 'days'), moment()],
      'This Month': [moment().startOf('month'), moment().endOf('month')],
      'Last Month': [moment().subtract(1, 'month').startOf('month'), moment().subtract(1, 'month').endOf('month')]
    },
    startDate: moment().subtract(13, 'days'),
    endDate: moment(),
    format: 'YYYY-MM-DD',
    separator: ':',
  });

  // Button that shows all the hidden rows in a table, e.g. on a report or problem
  // page and the statics page.
  $('.btn-more').click(function() {
    $(this).parents('table').find('tr.package.hide').removeClass('hide');
    $(this).parents('tr').remove();
    // Don't trigger the default action of the button.
    return false;
  });

  // Button for toggling the display of component versions in tables on report and
  // problem pages.
  $('.btn-toggle-versions').click(function() {
    const $parentTable = $(this).parent('table');

    if ($parentTable.data('versionsShown')) {
      $parentTable.find('tr.version').addClass('hide');
      $parentTable.find('tr.package').removeClass('stripe');
      $(this).text('Show versions');
      $parentTable.data('versionsShown', 0);
    } else {
      $parentTable.find('.btn-more').click();
      $parentTable.find('tr.version').removeClass('hide');
      $parentTable.find('tr.package').addClass('stripe');
      $(this).text('Hide versions');
      $parentTable.data('versionsShown', 1);
    }
  });

  // Helper functions for sorting the rows of a table based on the values of the
  // given column.
  const sort_table = ($table, column) => {
    let order = 'asc';
    if ($table.data('sortColumn') == column && $table.data('sortOrder') == 'asc') {
      // Toggle the order between ascending and descending if sorting on the same
      // column was requested.
      order = 'desc';
    }

    // Save current state in the DOM and reflect it in the display of UI elements.
    $table.data('sortColumn', column);
    $table.data('sortOrder', order);
    $table.find('.sort-indicator').addClass('hide');
    $table.find(`.sort-indicator.sort-${column}-${order}`).removeClass('hide');

    const rows = $table.find('tbody tr');
    const packages = [];
    let versions = [];

    // Pull out packages and versions for each package in the table. These are the
    // rows following the package name row in the DOM, hidden by default.
    rows.each((_index, row) => {
      if (row.classList.contains('package') && versions.length > 0) {
        packages.push(versions);
        versions = [];
      }
      versions.push(row);
    });
    packages.push(versions);

    // Do the sorting.
    packages.sort((a, b) => {
      // FIXME: Numbers in tables are currently rendered as '55,001', hence we need
      // to get rid of the commas or something.
      // NOTE: The data-numericValue thingie below might be a solution. Actually, we
      // already have the `cell-count` class.
      const cell_a = a[0].querySelector(`td:nth-child(${column})`);
      let value_a = cell_a.innerText;
      if ('numericValue' in cell_a.dataset) {
        value_a = cell_a.dataset['numericValue'];
      }

      const cell_b = b[0].querySelector(`td:nth-child(${column})`);
      let value_b = cell_b.innerText;
      if ('numericValue' in cell_b.dataset) {
        value_b = cell_b.dataset['numericValue'];
      }

      if (value_a == value_b) {
        return 0;
      }

      if (order == 'asc') {
        return (value_a > value_b) ? 1 : -1;
      }

      return (value_a > value_b) ? -1 : 1;
    });

    // Refill the table with the rows in sorted order.
    const $tbody = $table.find('tbody');
    $tbody.html('');
    for (let versions of packages) {
      for (let element of versions) {
        $tbody.append(element);
      }
    }

    if (!$table.data('showVersions')) {
      // FIXME: Striping is currently broken when sorting or showing/hiding
      // versions in between.
      $tbody.find('tr.package').removeClass('stripe');
      $tbody.find('tr.package:odd').addClass('stripe');
    }
  }

  // Bind the sorting function to the correponding buttons.
  $('.btn-sort-packages').click(function(e) {
    const $table = $(this).parent('table');
    $table.find('.btn-more').click();
    sort_table($table, 1);
    e.preventDefault();
  });

  $('.btn-sort-count').click(function(e) {
    const $table = $(this).parents('table');
    $table.find('.btn-more').click();
    sort_table($table, 2);
    e.preventDefault();
  });

  $('#show-advanced-filters').click(function() {
    $('#advanced-filters').removeClass('hide');
    $(this).addClass('hide');
  });

  // Truncate long function names
  const observer = new ResizeObserver(entries => {
    for (let entry of entries) {
      const container = entry.target.querySelector('.crash-fn');
      const expander = entry.target.querySelector('.expander');
      const expanded = container.classList.contains('expanded');
      if (expanded && (container.scrollHeight == expander.scrollHeight)) {
        container.classList.remove('expanded');
        return;
      }

      const showExpander = !expanded && (container.scrollHeight > container.clientHeight);
      const showCollapser = expanded;
      if (showExpander) {
        expander.innerHTML = 'show more';
      }
      else if (showCollapser) {
        expander.innerHTML = 'show less';
      }

      expander.hidden = !(showExpander || showCollapser);
    }
  });

  document.querySelectorAll('.crash-fn-container').forEach(element => {
    expander = element.querySelector('.expander');
    if (expander == null) {
      return;
    }

    expander.addEventListener('click', event => {
      element.querySelector('.crash-fn').classList.toggle('expanded');
      event.preventDefault();
    });
    observer.observe(element);
  });

  // Plotting of history charts on report and problem pages.

  // Format ticks for counts more readably using SI prefixes for thousands (k)
  // and millions (M).
  const si_tick_formatter = (y) => {
    if (y >= 1_000_000) {
      return (y / 1_000_000) + 'M';
    }
    if (y >= 1_000) {
      return (y / 1_000) + 'k';
    }
    return y.toFixed(0);
  };

  // Calculate ticks on the y axis slightly more intelligently for small
  // counts. Note that this fixes the lower bound to zero. Inspired by
  // flot's original tick generator.
  const tick_generator = (axis) => {
    if (axis.max < 1) {
      return [0, 1];
    }

    let tickSize = axis.tickSize;
    if (axis.max <= 5) {
      tickSize = 1;
    }

    const ticks = [];
    let i = 0;
    let v = null;
    do {
      v = i * tickSize;
      ticks.push(v);
      ++i;
    } while (v <= axis.max);

    return ticks;
  };

  // Create configuration parameters for a flot chart from the given input
  // parameters.
  const configure_plot = (frequency, from_date, count, show_unique) => {
    // Length of the specified period (day/week/month) in milliseconds.
    let period_ms = 24 * 60 * 60 * 1000;
    if (frequency == 'weekly') {
      period_ms *= 7;
    } else if (frequency == 'monthly') {
      period_ms *= 30;
    }

    // Format of the date displayed on the x axis.
    let date_format = '%b %Y'
    if (frequency == 'daily' || frequency == 'weekly') {
      date_format = '%d %b';
    }

    // Configure the chart display.
    const from_timestamp = +from_date;
    return {
      xaxis: {
        max: from_timestamp + period_ms * count,
        min: from_timestamp,
        mode: 'time',
        timeformat: date_format,
      },
      yaxis: {
        tickFormatter: si_tick_formatter,
        ticks: tick_generator,
      },
      series: {
        bars: {
          align: 'left',
          barWidth: .8 * period_ms,
          fill: .8,
          lineWidth: 0,
          show: true,
        },
        stack: true,
      },
      grid: {
        borderWidth: 0,
        color: '#aaa',
      },
      legend: {
        container: $(`#${frequency}${show_unique?'_unique':''}_legend`),
        labelBoxBorderColor: 'transparent',
        show: true,
      },
    };
  };

  $('.history_graph').each((_index, element) => {
    // The chart data are stored in the element's data attributes.
    const frequency = element.dataset.frequency;
    const history = JSON.parse(element.dataset.history);
    const show_unique = !!+element.dataset.showUnique;

    const num_opsys = Object.keys(history.by_opsys).length;
    const colors = getColors(num_opsys);

    const data = [];

    Object.entries(history.by_opsys).forEach(([opsys, counts], index) => {
      data.push({
        color: colors[index],
        data: counts.map(d => (
          [+Date.parse(d.date), show_unique ? (d.count - d.unique) : d.count]
        )),
        label: opsys + (show_unique ? ' – Recurrence' : '')
      });

      if (show_unique) {
        const darker_color = LightenDarkenColor(rgbToHex(colors[index].r,
          colors[index].g, colors[index].b), -40);
        data.push({
          color: darker_color,
          data: counts.map(d => (
            [+Date.parse(d.date), d.unique]
          )),
          label: `${opsys} – Unique`
        });
      }
    });

    const chart_options = configure_plot(frequency, Date.parse(history.from_date),
      history.period_count, show_unique);

    // Finally plot the data.
    $.plot(element, data, chart_options);
  });
});

function postData(url, data, success) {
  $.ajax({
    type: 'POST',
    contentType: 'application/json',
    url: url,
    data: JSON.stringify(data),
    success: success
  })
}
