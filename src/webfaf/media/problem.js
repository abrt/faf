backtrace_diff = function() {
  var ctab = $('.tab-content .tab-pane:first-child').attr('id');
  var ptab = ctab;
  var reports_url = $('#btn-view-report').attr('href').replace(/\d+\/$/g, '');
  var diff_btn = $('#btn-diff-reports');
  if(!diff_btn.length) return;
  var diff_url =  diff_btn.attr('href').replace(/\d+\/\d+\/$/g, '');
  var a = ctab;
  var b = ctab;

  /* Update 'View complete report' button URL and diff selection on tab change */
  $('a[data-toggle="tab"]').on('shown', function(e) {
    ctab = e.target.text;
    ptab = e.relatedTarget.text;
    $('#btn-view-report').attr('href', reports_url + ctab + '/');
    $('#select-b').val(ctab).change();
  });

  /* Show diff dropdowns and pre-select reports in current & previous tab */
  $('#btn-diff').click(function() {
    $('#btn-diff').hide();
    $('#select-a').val(ctab).change();
    $('#select-b').val(ptab).change();
    $('#diff-choice').css('display', 'inline');
  });

  /* Update 'Diff' button URL on changes of diff selects */
  $('#diff-choice select').change(function() {
    var selected = $(this).find('option:selected').attr('value')
    if($(this).attr('name') == 'select-a') {
      a = selected;
    } else {
      b = selected;
    }

    $('#btn-diff-reports').attr('href', diff_url + a + '/' + b + '/');
  });

  /* Handle browser history */
  $('#diff-choice select').change();
}

$(document).ready(function() {
  backtrace_diff();
});
