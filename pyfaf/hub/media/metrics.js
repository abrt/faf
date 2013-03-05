metrics_more_buttons = function() {
  $('.btn-more').click(function() {
    $(this).parents('tr').hide();
    $(this).parents('table').find('tr.hide').show();
  });
}

$(document).ready(function() {
  metrics_more_buttons();
});
