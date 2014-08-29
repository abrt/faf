$(document).ready(function() {
    $('.multiselect').multiselect({
        includeSelectAllOption: true,
        selectAllValue: 'select-all',
    });

    $('.multiselect-filtered').multiselect({
        includeSelectAllOption: true,
        selectAllValue: 'select-all',
        enableFiltering: true,
        maxHeight: 200,
    });

    $('input.daterange').daterangepicker({
      ranges: {
        //'Today': [moment(), moment()],
        'Yesterday': [moment().subtract('days', 1), moment().subtract('days', 1)],
        'Last 7 Days': [moment().subtract('days', 6), moment()],
        'Last 14 Days': [moment().subtract('days', 13), moment()],
        'Last 30 Days': [moment().subtract('days', 29), moment()],
        'This Month': [moment().startOf('month'), moment().endOf('month')],
        'Last Month': [moment().subtract('month', 1).startOf('month'), moment().subtract('month', 1).endOf('month')]
      },
      startDate: moment().subtract('days', 13),
      endDate: moment(),
      format: 'YYYY-MM-DD',
      separator: ':',
    });

    $('.btn-more').click(function() {
      $(this).parents('table').find('tr.hide').removeClass('hide');
      $(this).parents('tr').remove();
  });
});
