$(document).ready(function() {
  alert ('bitch');
});

$('#idSubmitButton').click(function() {

    $.ajax({
      type: 'get',
      url: '/search',
      dataType: 'json',
      success: function(data) {
        $("#idBody").html(data);
      },
      error: function(request, status, error) {
        $("#idBody").html(error);
      }
    });
});
