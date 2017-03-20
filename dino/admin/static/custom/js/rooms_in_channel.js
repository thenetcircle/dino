
var renameTips = null;
var editTips = null;
var renameElement = null;
var editElement = null;
var allRenameFields = null;
var allEditFields = null;

var renameUrlField = null;
var editUrlField = null;

$(document).ready(function() {
    renameTips = $('.validateRenameTips');
    editTips = $('.validateEditTips');
    
    renameElement = $('div#rename-form').find('input#rename-name');
    editElement = $('div#edit-form').find('input#edit-value');
    
    allRenameFields = $([]).add(renameElement);
    allEditFields = $([]).add(editElement);

    $('#list-rooms').DataTable({
        'lengthMenu': [[50, 200, -1], [50, 200, 'All']],
        'order': [[ 1, 'desc' ]]
    });

    $('input[type=checkbox]').switchButton({
        on_label: 'Yes',
        off_label: 'No'
    });

    $('input[name="default-room"]').change(function() {
        var room_id = $($(this).parent().find('input.room-id')[0]).val();
        var state = $(this).is(':checked');
        var change_url = '/room/' + room_id + '/'
        if (state) {
            change_url += 'set-default'
        }
        else {
            change_url += 'unset-default'
        }

        $.ajax({
            method: 'PUT',
            url: change_url,
            contentType: 'application/json;charset=UTF-8'
        }).done(function(data) {
            console.log(data)
        });
    });

    $('input[name="ephemeral-room"]').change(function() {
        var room_id = $($(this).parent().find('input.room-id')[0]).val();
        var state = $(this).is(':checked');
        var change_url = '/room/' + room_id + '/'
        if (state) {
            change_url += 'set-ephemeral'
        }
        else {
            change_url += 'unset-ephemeral'
        }

        $.ajax({
            method: 'PUT',
            url: change_url,
            contentType: 'application/json;charset=UTF-8'
        }).done(function(data) {
            console.log(data)
        });
    });

    $('#api_action').change(function() {
        var api_action = $(this).find(':selected').val();

        $.ajax({
            type: 'GET',
            url: '/acl/channel/action/' + api_action + '/types',
        }).done(function(data) {
            types = [];
            for (var i = 0; i < data.length; i++) {
                types.push([data[i].acl_type, data[i].name])
            }

            var option_list = [['', '--- Select One ---']].concat(types);

            $('#acl_type').empty();
            for (var i = 0; i < option_list.length; i++) {
                $('#acl_type').append(
                    $('<option></option>').attr(
                        'value', option_list[i][0]).text(option_list[i][1])
                );
            }
        });
    });
});
