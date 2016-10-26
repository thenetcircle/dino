
$(document).ready(function(){
    $('a.remove-button').each(function() {
        $(this).confirm({
            text: "Are you sure you want to delete?",
            title: "Confirmation required",
            confirm: function(button) {
                remove_url = $(button).find('input.remove-url').val()
                $.ajax({
                    method: 'DELETE',
                    url: remove_url
                }).done(function(data) {
                    $(button).closest('tr').remove();
                });
            },
            cancel: function(button) {
                // nothing to do
            },
            confirmButton: "Yes",
            cancelButton: "No",
            post: true,
            confirmButtonClass: "btn-danger",
            cancelButtonClass: "btn-default",
            dialogClass: "modal-dialog modal-lg" // Bootstrap classes for large modal
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
});
