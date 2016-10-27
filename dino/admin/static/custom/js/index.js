
function checkLength(o, n, min, max, tipsFunc) {
    if (o.val().length > max || o.val().length < min) {
        o.addClass('ui-state-error');
        tipsFunc('Length of ' + n + ' must be between ' +
            min + ' and ' + max + '.');
        return false;
    } else {
        return true;
    }
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

    editDialog = $('#edit-form').dialog({
      autoOpen: false,
      height: 220,
      width: 300,
      modal: true,
      buttons: {
        'Edit': edit,
        Cancel: function() {
          editDialog.dialog('close');
        }
      },
      close: function() {
        editForm[0].reset();
        allEditFields.removeClass('ui-state-error');
      }
    });

    editForm = editDialog.find('form').on('submit', function(event) {
        event.preventDefault();
        edit();
    });

    $('.edit-button').button().on('click', function() {
        editUrlField = $(this).find('input.edit-url')[0];
        editDialog.dialog('open');
    });

    renameDialog = $('#rename-form').dialog({
      autoOpen: false,
      height: 220,
      width: 300,
      modal: true,
      buttons: {
        'Rename': rename,
        Cancel: function() {
          renameDialog.dialog('close');
        }
      },
      close: function() {
        renameForm[0].reset();
        allRenameFields.removeClass('ui-state-error');
      }
    });

    renameForm = renameDialog.find('form').on('submit', function(event) {
        event.preventDefault();
        rename();
    });

    $('.rename-button').button().on('click', function() {
        renameUrlField = $(this).find('input.rename-url')[0];
        renameDialog.dialog('open');
    });
});


function renameUpdateTips(t) {
    renameTips.text(t) .addClass('ui-state-highlight');
    setTimeout(function() {
        renameTips.removeClass('ui-state-highlight', 1500);
    }, 500);
}

function editUpdateTips(t) {
    editTips.text(t) .addClass('ui-state-highlight');
    setTimeout(function() {
        editTips.removeClass('ui-state-highlight', 1500);
    }, 500);
}

function rename() {
    var name = renameElement.val();
    var rename_url = $(renameUrlField).val();
    var valid = true;

    allRenameFields.removeClass('ui-state-error');
    valid = valid && checkLength(renameElement, 'name', 1, 128, renameUpdateTips);

    if (valid) {
        $.ajax({
            method: 'PUT',
            url: rename_url,
            data: JSON.stringify({'name': name}),
            contentType: 'application/json;charset=UTF-8'
        }).done(function(data) {
            console.log(data)
            if (data.status_code == 200) {
                location.reload();
            }
            else {
                renameUpdateTips(data.message);
            }
        });
    }
    else {
        return valid;
    }
}

function edit() {
    var value = editElement.val();
    var edit_url = $(editUrlField).val();
    var valid = true;

    allEditFields.removeClass('ui-state-error');
    valid = valid && checkLength(editElement, 'value', 1, 128, editUpdateTips);

    if (valid) {
        $.ajax({
            method: 'PUT',
            url: edit_url,
            data: JSON.stringify({'value': value}),
            contentType: 'application/json;charset=UTF-8'
        }).done(function(data) {
            if (data.status_code == 200) {
                location.reload();
            }
            else {
                editUpdateTips(data.message);
            }
        });
    }
    else {
        return valid;
    }
}
