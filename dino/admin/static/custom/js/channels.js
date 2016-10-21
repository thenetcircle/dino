
$(document).ready(function() {
    $('#list-leagues').DataTable({
        "lengthMenu": [[50, 200, -1], [50, 200, "All"]],
        "order": [[ 1, "desc" ]]
    });

    $('a.league-link').click(function() {
        league_uuid = $(this).attr('href').split('divisions-for-league-')[1]
    })
});

