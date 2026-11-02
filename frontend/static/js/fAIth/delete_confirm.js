// Generalized delete confirmation. Any button can open #deleteConfirmModal with these data attributes:
//   data-bs-toggle="modal" data-bs-target="#deleteConfirmModal"
//   data-delete-url      URL to POST the deletion to
//   data-delete-field    form field name that holds the item's ID (e.g. note_id)
//   data-delete-value    the item's ID
//   data-delete-title    optional modal title (e.g. "Delete this note?")
document.getElementById('deleteConfirmModal').addEventListener('show.bs.modal', function (event)
{
    const trigger = event.relatedTarget;
    const form = document.getElementById('deleteConfirmForm');
    const input = document.getElementById('deleteConfirmValue');

    form.setAttribute('hx-post', trigger.dataset.deleteUrl);
    input.name = trigger.dataset.deleteField;
    input.value = trigger.dataset.deleteValue;
    document.getElementById('deleteConfirmTitle').textContent = trigger.dataset.deleteTitle || 'Delete this item?';

    // Tell htmx about the new hx-post URL
    htmx.process(form);
});
