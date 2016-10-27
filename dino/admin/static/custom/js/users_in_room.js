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

    $('#list-users').DataTable({
        "lengthMenu": [[50, 200, -1], [50, 200, "All"]],
        "order": [[ 1, "desc" ]]
    });
});
