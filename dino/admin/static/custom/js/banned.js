
$(document).ready(function() {
    $('#list-global-bans').DataTable({
        "lengthMenu": [[10, 50, 200, -1], [10, 50, 200, "All"]],
        "order": [[ 1, "desc" ]]
    });

    $('#list-channel-bans').DataTable({
        "lengthMenu": [[10, 50, 200, -1], [10, 50, 200, "All"]],
        "order": [[ 1, "desc" ]]
    });

    $('#list-room-bans').DataTable({
        "lengthMenu": [[10, 50, 200, -1], [10, 50, 200, "All"]],
        "order": [[ 1, "desc" ]]
    });
});
