
$(document).ready(function(){
    $('a.acl-remove').confirm({
        text: "Are you sure you want to delete the permission?",
        title: "Confirmation required",
        confirm: function(button) {
            remove_url = $(button).find('input.acl-url').val()
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
});
