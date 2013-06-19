metrics_more_buttons = function() {
  $('.btn-more').click(function() {
    $(this).parents('table').find('tr.hide').show();
    $(this).parents('tr').remove();
  });
}

$(document).ready(function() {
  metrics_more_buttons();
});
