
function checkLength(o, n, min, max, tipsFunc) {
    if (o.val().length > max || o.val().length < min) {
        o.addClass('ui-state-error');
        tipsFunc('Length of ' + n + ' must be between ' + min + ' and ' + max + '.');
        return false;
    } else {
        return true;
    }
}

function checkLastCharIsIn(o, n, possibles, tipsFunc) {
    if (possibles.indexOf(o.val().slice(-1)) >= 0) {
        return true;
    } else {
        o.addClass('ui-state-error');
        tipsFunc('Invalid unit for duration, use one of "' + possibles.join() + '"');
        return false;
    }
}

function checkAllButLastIsDigit(o, n, tipsFunc) {
    if (/^\d+$/.test(o.val().slice(0, -1))) {
        return true;
    } else {
        o.addClass('ui-state-error');
        tipsFunc('Value before duration is not a number');
        return false;
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

    $('a.kick-button').each(function() {
        $(this).confirm({
            text: "Are you sure you want to kick the user?",
            title: "Confirmation required",
            confirm: function(button) {
                kick_url = $(button).find('input.kick-url').val();
                $.ajax({
                    method: 'PUT',
                    url: kick_url
                }).done(function(data) {
                    if (data.status_code == 200) {
                        $(button).closest('tr').remove();
                    }
                    else {
                        console.log(data);
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

    // EDIT
    editDialog = $('#edit-form').dialog({
      autoOpen: false,
      height: 220,
      width: 350,
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

    // RENAME
    renameDialog = $('#rename-form').dialog({
      autoOpen: false,
      height: 220,
      width: 350,
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

    // BAN
    banDialog = $('#ban-form').dialog({
      autoOpen: false,
      height: 220,
      width: 350,
      modal: true,
      buttons: {
        'Ban': ban,
        Cancel: function() {
          banDialog.dialog('close');
        }
      },
      close: function() {
        banForm[0].reset();
        allBanFields.removeClass('ui-state-error');
      }
    });
    banForm = banDialog.find('form').on('submit', function(event) {
        event.preventDefault();
        ban();
    });
    $('.ban-button').button().on('click', function() {
        banUrlField = $(this).find('input.ban-url')[0];
        banDialog.dialog('open');
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

function banUpdateTips(t) {
    banTips.text(t) .addClass('ui-state-highlight');
    setTimeout(function() {
        banTips.removeClass('ui-state-highlight', 1500);
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

function ban() {
    var value = banElement.val();
    var ban_url = $(banUrlField).val();
    var valid = true;

    allBanFields.removeClass('ui-state-error');
    valid = valid && checkLength(banElement, 'duration', 2, 6, banUpdateTips);
    valid = valid && checkLastCharIsIn(banElement, 'duration', ['d', 'h', 'm', 's'], banUpdateTips);
    valid = valid && checkAllButLastIsDigit(banElement, 'duration', banUpdateTips);

    if (valid) {
        var user_id = $($(banUrlField).closest('tr')[0]).attr('id').split('user-id-', 2)[1]
        data_to_send = {
            'duration': value,
            'user_id': user_id,
            'room_id': $('span#room-id').val()
        }
        console.log(data_to_send);
        console.log(ban_url)
        $.ajax({
            method: 'PUT',
            url: ban_url,
            data: JSON.stringify(data_to_send),
            contentType: 'application/json;charset=UTF-8'
        }).done(function(data) {
            if (data.status_code == 200) {
                $('tr#user-id-' + user_id).remove();
                banDialog.dialog('close');
            }
            else {
                banUpdateTips(data.message);
            }
        });
    }
    else {
        return valid;
    }
}