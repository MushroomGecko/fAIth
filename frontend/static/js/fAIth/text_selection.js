// Enable all .text-highlight elements
function enableTextHighlightInteractables()
{
    document.querySelectorAll('.text-highlight').forEach(element => {
        if (element.tagName === 'BUTTON')
        {
            // Native disabled property works directly on <button> elements
            element.disabled = false;
        }
        else
        {
            // For non-button elements (e.g. <a>), remove Bootstrap's disabled class and
            // ARIA attributes since the native disabled property has no effect on them.
            element.classList.remove('disabled');
            element.removeAttribute('aria-disabled');
            element.removeAttribute('tabindex');
        }
    });
}

// Disable all .text-highlight elements
function disableTextHighlightInteractables()
{
    document.querySelectorAll('.text-highlight').forEach(element => {
        if (element.tagName === 'BUTTON')
        {
            // Native disabled property works directly on <button> elements
            element.disabled = true;
        }
        else
        {
            // For non-button elements (e.g. <a>), Bootstrap's disabled class adds
            // pointer-events: none and reduced opacity. aria-disabled and tabindex="-1"
            // additionally block keyboard focus and screen reader activation.
            element.classList.add('disabled');
            element.setAttribute('aria-disabled', 'true');
            element.setAttribute('tabindex', '-1');
        }
    });
}

// Disable text-highlight interactables on page load
disableTextHighlightInteractables();

// Update the hidden input and button state on any selection change (mouse, touch, or keyboard).
// When the selection clears, only reset if a modal is not open, otherwise clicking into the
// modal's question input would wipe the stored selection before the form is submitted.
document.addEventListener('selectionchange', () => {
    const text = document.getSelection().toString();
    if (text !== '')
    {
        document.getElementById('selectedTextInput').value = text;
        document.getElementById('selectedTextImageSearch').value = text;
        enableTextHighlightInteractables();
    }
    else if (!document.querySelector('.modal.show'))
    {
        document.getElementById('selectedTextInput').value = '';
        document.getElementById('selectedTextImageSearch').value = '';
        disableTextHighlightInteractables();
    }
});

// Preserve selection when clicking a .text-highlight element (mousedown clears selection by default).
// Disable interactables when starting an interaction outside modals and .text-highlight elements.
document.addEventListener('mousedown', (event) => {
    if (event.target.closest('.text-highlight'))
    {
        event.preventDefault();
    }
    else if (!event.target.closest('.modal') && !event.target.closest('.modal-backdrop'))
    {
        disableTextHighlightInteractables();
    }
});

// Same logic for touch: { passive: false } is required to allow preventDefault().
// Without it, modern browsers silently ignore the call and the selection is cleared.
document.addEventListener('touchstart', (event) => {
    if (event.target.closest('.text-highlight'))
    {
        // Preserve selection by preventing default browser touch handling.
        // Because this suppresses the synthesized click, touchend manually opens the modal below.
        event.preventDefault();
    }
    else if (!event.target.closest('.modal') && !event.target.closest('.modal-backdrop'))
    {
        disableTextHighlightInteractables();
    }
}, { passive: false });

// Manually trigger Bootstrap modal on touch because touchstart's preventDefault suppresses the
// synthesized click that data-bs-toggle="modal" relies on.
document.addEventListener('touchend', (event) => {
    const target = event.target.closest('.text-highlight[data-bs-toggle="modal"]');
    if (target)
    {
        const modalEl = document.querySelector(target.getAttribute('data-bs-target'));
        if (modalEl)
        {
            bootstrap.Modal.getOrCreateInstance(modalEl).show();
        }
    }
});
