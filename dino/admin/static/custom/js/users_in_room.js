
$(document).ready(function() {
    $('#list-users').DataTable({
        "lengthMenu": [[50, 200, -1], [50, 200, "All"]],
        "order": [[ 1, "desc" ]]
    });

    $('.toggle-form').click(function() {
        img = $($(this).find('i')[0]);
        if (img.hasClass('fa-caret-square-o-right')) {
            $($(this).find('span')[0]).html('Hide forms');
            $('.form-container').toggle();
            img.removeClass('fa-caret-square-o-right');
            img.addClass('fa-caret-square-o-down');
        }
        else {
            $($(this).find('span')[0]).html('Show forms');
            $('.form-container').toggle();
            img.removeClass('fa-caret-square-o-down');
            img.addClass('fa-caret-square-o-right');
        }
    });
});
