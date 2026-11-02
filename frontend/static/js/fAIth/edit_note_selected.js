// Fill the edit modal with the note the pencil button belongs to
document.getElementById('editNoteSelectedModal').addEventListener('show.bs.modal', function (event)
{
    const button = event.relatedTarget;
    document.getElementById('editNoteId').value = button.dataset.noteId;
    document.getElementById('editNote').value = button.dataset.noteText;
});
