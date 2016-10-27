
$(document).ready(function() {
    $('#list-global-bans').DataTable({
        "lengthMenu": [[10, 50, 200, -1], [10, 50, 200, "All"]],
        "order": [[ 3, "asc" ]]
    });

    $('#list-channel-bans').DataTable({
        "lengthMenu": [[10, 50, 200, -1], [10, 50, 200, "All"]],
        "order": [[ 6, "asc" ]]
    });

    $('#list-room-bans').DataTable({
        "lengthMenu": [[10, 50, 200, -1], [10, 50, 200, "All"]],
        "order": [[ 6, "asc" ]]
    });

    $('td.timeleft').each(function() {
        var timestamp_element = $($(this).parent().children('td.timestamp')[0]);
        var utcdate = timestamp_element.html().trim();
        var localdate = moment(utcdate).local();
        var formatted = localdate.format('YYYY/MM/DD HH:mm:ss');
        timestamp_element.html(localdate.format('YYYY-MM-DD HH:mm:ss'));

        $(this).countdown(formatted, {
        }).on('update.countdown', function(event) {
            $(this).html(event.strftime('%-D days %H:%M:%S'));
        }).on('finish.countdown', function() {
            $(this).parent('tr').remove();
        });
    });
});
