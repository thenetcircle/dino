
$(document).ready(function() {
    $('#list-words').DataTable({
        "lengthMenu": [[100, 200, -1], [100, 200, "All"]],
        "order": [[ 0, "asc" ]]
    });
});
