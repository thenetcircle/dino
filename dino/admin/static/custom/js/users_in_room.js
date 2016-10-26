
var tips = null;
var name_element = null;
var allFields = null;

$(document).ready(function() {
    tips = $('.validateTips');
    name_element = $('div#rename-form').find('input#rename-name');
    allFields = $([]).add(name_element);

    $('#list-users').DataTable({
        "lengthMenu": [[50, 200, -1], [50, 200, "All"]],
        "order": [[ 1, "desc" ]]
    });
});

function updateTips(t) {
    tips.text(t) .addClass('ui-state-highlight');
    setTimeout(function() {
        tips.removeClass('ui-state-highlight', 1500);
    }, 500);
}

function rename() {
    var name = name_element.val();
    var rename_url = $('div#rename-form').find('input#rename-url').val();
    var valid = true;

    allFields.removeClass('ui-state-error');
    valid = valid && checkLength(name_element, 'username', 1, 128);

    if (valid) {
        $.ajax({
            method: 'PUT',
            url: rename_url,
            data: JSON.stringify({'name': name}),
            contentType: 'application/json;charset=UTF-8'
        }).done(function(data) {
            if (data.status_code == 200) {
                location.reload();
            }
        });
    }
    else {
        return valid;
    }
}
