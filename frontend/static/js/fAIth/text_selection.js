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
// Selections that touch .verses-container reduce to only the touched verse(s), regardless of
// drag direction or whether the selection also spans unrelated elements (e.g. the sidebar).
document.addEventListener('selectionchange', () => {
    const selection = document.getSelection();
    let text = selection.toString();
    let verses_text = '';
    const range = selection.rangeCount ? selection.getRangeAt(0) : null;
    const container = document.querySelector('.verses-container');
    if (range && container && range.intersectsNode(container))
    {
        const verses = Array.from(container.querySelectorAll('p'))
            .filter(p => range.intersectsNode(p))
            .map(p => p.textContent.trim())
            .filter(verse => verse !== '');
        verses_text = verses.join('\n');
    }
    const selectedTextInputs = document.querySelectorAll('input[name="selected_text"]');
    const versesTextInputs = document.querySelectorAll('input[name="verses_text"]');
    if (text !== '')
    {
        selectedTextInputs.forEach(input => { input.value = text; });
        versesTextInputs.forEach(input => { input.value = verses_text; });
        enableTextHighlightInteractables();
    }
    else if (!document.querySelector('.modal.show'))
    {
        selectedTextInputs.forEach(input => { input.value = ''; });
        versesTextInputs.forEach(input => { input.value = ''; });
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
