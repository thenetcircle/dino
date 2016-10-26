
function checkLength(o, n, min, max) {
    if (o.val().length > max || o.val().length < min) {
        o.addClass('ui-state-error');
        updateTips('Length of ' + n + ' must be between ' +
            min + ' and ' + max + '.');
        return false;
    } else {
        return true;
    }
}

function rename() {
}

function updateTips(t) {
    tips.text(t) .addClass('ui-state-highlight');
    setTimeout(function() {
        tips.removeClass('ui-state-highlight', 1500);
    }, 500);
}

$(document).ready(function(){
    $('a.remove-button').each(function() {
        $(this).confirm({
            text: "Are you sure you want to delete?",
            title: "Confirmation required",
            confirm: function(button) {
                remove_url = $(button).find('input.remove-url').val();
                redirect_url = $(button).find('input.redirect-url');
                $.ajax({
                    method: 'DELETE',
                    url: remove_url
                }).done(function(data) {
                    if (redirect_url.length == 0) {
                        $(button).closest('tr').remove();
                    }
                    else if (data.status_code == 200) {
                        $(location).attr('href', redirect_url.val());
                    }
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

    dialog = $('#rename-form').dialog({
      autoOpen: false,
      height: 220,
      width: 300,
      modal: true,
      buttons: {
        'Rename': rename,
        Cancel: function() {
          dialog.dialog('close');
        }
      },
      close: function() {
        form[0].reset();
        allFields.removeClass('ui-state-error');
      }
    });

    form = dialog.find('form').on('submit', function(event) {
        event.preventDefault();
        rename();
    });

    $('.rename-button').button().on('click', function() {
        dialog.dialog('open');
    });
});
