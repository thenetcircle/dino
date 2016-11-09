var allRenameFields = null;
var renameUrlField = null;
var renameTips = null;
var renameElement = null;

var allEditFields = null;
var editUrlField = null;
var editTips = null;
var editElement = null;

var allBanFields = null;
var banUrlField = null;
var banTips = null;
var baneElement = null;

$(document).ready(function() {
    renameTips = $('.validateRenameTips');
    editTips = $('.validateEditTips');
    banTips = $('.validateBanTips');

    renameElement = $('div#rename-form').find('input#rename-name');
    editElement = $('div#edit-form').find('input#edit-value');
    banElement = $('div#ban-form').find('input#ban-duration');

    allRenameFields = $([]).add(renameElement);
    allEditFields = $([]).add(editElement);
    allBanFields = $([]).add(banElement);

    $('#list-users').DataTable({
        "lengthMenu": [[50, 200, -1], [50, 200, "All"]],
        "order": [[ 1, "desc" ]]
    });

    $('#api_action').change(function() {
        var api_action = $(this).find(':selected').val();

        $.ajax({
            type: 'GET',
            url: '/acl/room/action/' + api_action + '/types',
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
