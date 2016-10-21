
$(document).ready(function() {
    $('#list-rooms').DataTable({
        "lengthMenu": [[50, 200, -1], [50, 200, "All"]],
        "order": [[ 1, "desc" ]]
    });
});
