
$(document).ready(function() {
    form = $('form#search-history');

    form.find('input#from_time').datetimepicker({
        timeFormat: "HH:mm:ssz",
        dateFormat: 'yy-mm-dd',
        showTimezone: true
    });
    form.find('input#to_time').datetimepicker({
        timeFormat: "HH:mm:ssz",
        dateFormat: 'yy-mm-dd',
        showTimezone: true
    });

    $('input[type=checkbox]').switchButton({
        on_label: 'Yes',
        off_label: 'No'
    });

    $('span.datetime').each(function() {
        $(this).html(moment($(this).html()).format('LLLL'))
    });

    $('input[name="message-deleted"]').change(function() {
        var message_id = $($(this).parent().find('input.message-id')[0]).val();
        var state = $(this).is(':checked');
        var change_url = '/history/' + message_id + '/';
        if (state) {
            change_url += 'delete'
        }
        else {
            change_url += 'undelete'
        }

        $.ajax({
            method: 'PUT',
            url: change_url,
            contentType: 'application/json;charset=UTF-8'
        }).done(function(data) {
            console.log(data)
        });
    });

    $('#list-history').DataTable({
        lengthMenu: [[100, 200, -1], [100, 200, 'All']],
        order: [[ 2, 'desc' ]],
        dom: 'Blfrtip',
        buttons: [
            {
                extend: 'collection',
                text: 'Export',
                buttons: [
                    'copyHtml5',
                    'excelHtml5',
                    'csvHtml5'
                ]
            }
        ]
    });
});
