
$(document).ready(function() {
    $('#list-superusers').DataTable({
        "lengthMenu": [[50, 200, -1], [50, 200, "All"]],
        "order": [[ 1, "desc" ]]
    });

    var user_results_table = $('#user-results-table').DataTable({
        "order": [[ 1, "desc" ]],
        'bSort': true,
        'bFilter' : false,
        'bLengthChange': false,
        'bPaginate': true,
        'bInfo': false
    });

    var typingTimer;
    var doneTypingInterval = 5000;
    var searchField = $('#search-user');

    searchField.on('keyup', function () {
        clearTimeout(typingTimer);
        typingTimer = setTimeout(doneTyping(), doneTypingInterval);
    });

    function doneTyping () {
        if (searchField.val().trim().length < 3) {
            return;
        }
        $.ajax({
            type: 'POST',
            data: JSON.stringify({
                query: searchField.val().trim()
            }),
            url: '/users/search',
            contentType: 'application/json;charset=UTF-8'
        }).done(function(data) {
            user_results_table.clear();

            for (i = 0; i < data.length; i++) {
                if (i == 100) {
                    break;
                }
                user = data[i];
                $('#user-results-table').dataTable().fnAddData([
                    user.id,
                    user.name,
                    '<a class="pure-button ui-button select-button ui-button ui-corner-all ui-widget" href="' + '/user/' + user.id + '/set/superuser">' +
                    '<i class="fa fa-user-plus fa-lg" aria-hidden="true"></i></a>' +
                    '<a class="pure-button ui-button select-button ui-button ui-corner-all ui-widget" href="' + '/user/' + user.id + '/del/superuser">' +
                    '<i class="fa fa-user-times fa-lg" aria-hidden="true"></i></a>',
                ]);
            }
            user_results_table.draw();

            if (data.length > 100) {
                $('#user-results').append('<small>(limiting to 100 results)</small>');
            }
        });
    };
});
