$(document).ready(function() {
    $.each($('.multiselect'), function(index, value) {
      $(this).multiselect({
        includeSelectAllOption: true,
        selectAllValue: 'select-all',
        nonSelectedText: $("label[for='"+$(this).attr("id")+"']").text(),
      });
    });

    $.each($('.multiselect-filtered'), function(index, value) {
      $(this).multiselect({
        includeSelectAllOption: true,
        selectAllValue: 'select-all',
        enableFiltering: true,
        maxHeight: 200,
        nonSelectedText: $("label[for='"+$(this).attr("id")+"']").text(),
      });
    });
    $.each($('.multiselect-filtered-dynamic'), function(index, value) {
      var $this = $(this);
      var optionsHtml = $this.html();
      $this.find("option:not(:selected)").remove();
      $this.multiselect({
        includeSelectAllOption: true,
        selectAllValue: 'select-all',
        enableFiltering: true,
        maxHeight: 200,
        nonSelectedText: $("label[for='"+$this.attr("id")+"']").text(),
        onDropdownShow: function(event) {
          $this.multiselect('destroy');
          $this.html(optionsHtml);
          $this.multiselect({
            includeSelectAllOption: true,
            selectAllValue: 'select-all',
            enableFiltering: true,
            enableCaseInsensitiveFiltering: true,
            maxHeight: 200,
            nonSelectedText: $("label[for='"+$this.attr("id")+"']").text(),
          });
          $this.parent().find(".btn.multiselect").click();
        }
      });
    });

    var component_names = new Bloodhound({
      datumTokenizer: Bloodhound.tokenizers.obj.whitespace('name'),
      queryTokenizer: Bloodhound.tokenizers.whitespace,
      prefetch: {
        url: ROOT_URL+'component_names.json',
        filter: function(list) {
          return $.map(list, function(componentName) {
            return { name: componentName }; });
        }
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
