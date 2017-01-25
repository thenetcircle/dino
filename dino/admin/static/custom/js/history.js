
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
