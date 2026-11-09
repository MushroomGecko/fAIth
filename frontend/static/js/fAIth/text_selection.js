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

// Build {verse_number: {beginning, end}} for every verse the selection touches.
// beginning and end are character offsets into that verse's textContent (the <p> element, including its "1) " prefix),
// so they can be used to wrap the same characters in <mark> later.
// Returns {beginning, end} for the part of the selection inside one verse <p>, or null if the selection
// doesn't cover any of its text. Called from the selectionchange loop, once per verse.
function getVerseHighlight(range, p)
{
    const verseRange = document.createRange();
    verseRange.selectNodeContents(p);

    // Clamp the selection to this verse, so a multi-verse selection only covers the part inside this <p>.
    const clamped = range.cloneRange();
    if (range.compareBoundaryPoints(Range.START_TO_START, verseRange) < 0)
    {
        clamped.setStart(verseRange.startContainer, verseRange.startOffset);
    }
    if (range.compareBoundaryPoints(Range.END_TO_END, verseRange) > 0)
    {
        clamped.setEnd(verseRange.endContainer, verseRange.endOffset);
    }

    // Measure from the start of the verse to the clamped selection.
    const beforeRange = document.createRange();
    beforeRange.setStart(p, 0);
    beforeRange.setEnd(clamped.startContainer, clamped.startOffset);
    const beginning = beforeRange.toString().length;
    const end = beginning + clamped.toString().length;

    return end > beginning ? { beginning: beginning, end: end } : null;
}

// Span classes kept in saved notes. Must match ALLOWED_SPAN_CLASSES in backend/utils/note_html.py.
const SAVED_SPAN_CLASSES = ['wj', 'header'];

// Returns the selected verse HTML (keeping spans like <span class="wj">), clamped to the verses container.
// Existing highlight <mark> wrappers are removed so a saved note doesn't carry the highlight.
// The server sanitizes this HTML before saving it.
function getSelectedHtml(range, container)
{
    const containerRange = document.createRange();
    containerRange.selectNodeContents(container);

    const clamped = range.cloneRange();
    if (range.compareBoundaryPoints(Range.START_TO_START, containerRange) < 0)
    {
        clamped.setStart(container, 0);
    }
    if (range.compareBoundaryPoints(Range.END_TO_END, containerRange) > 0)
    {
        clamped.setEnd(container, container.childNodes.length);
    }

    // cloneContents() only keeps ancestors that are partly inside the selection. When the selection is
    // entirely inside one span (e.g. a few words of red text), that span is left out, so re-wrap the
    // selection in clones of the allowed span ancestors above it.
    let fragment = clamped.cloneContents();
    let ancestor = clamped.commonAncestorContainer;
    if (ancestor.nodeType === Node.TEXT_NODE)
    {
        ancestor = ancestor.parentNode;
    }
    while (ancestor && ancestor !== container)
    {
        if (ancestor.tagName === 'SPAN' && SAVED_SPAN_CLASSES.some(cls => ancestor.classList.contains(cls)))
        {
            const outer = ancestor.cloneNode(false);
            outer.appendChild(fragment);
            fragment = outer;
        }
        ancestor = ancestor.parentNode;
    }

    const wrapper = document.createElement('div');
    wrapper.appendChild(fragment);
    wrapper.querySelectorAll('mark').forEach(mark => mark.replaceWith(...mark.childNodes));
    return wrapper.innerHTML;
}

// Update the hidden input and button state on any selection change (mouse, touch, or keyboard).
// When the selection clears, only reset if a modal is not open, otherwise clicking into the
// modal's question input would wipe the stored selection before the form is submitted.
// Selections that touch .verses-container reduce to only the touched verse(s), regardless of
// drag direction or whether the selection also spans unrelated elements (e.g. the sidebar).
document.addEventListener('selectionchange', () => {
    const selection = document.getSelection();
    let text = selection.toString();
    let verses_text = '';
    let highlight_coordinates = {};
    let selected_html = '';
    const range = selection.rangeCount ? selection.getRangeAt(0) : null;
    const container = document.querySelector('.verses-container');
    if (range && container && range.intersectsNode(container))
    {
        selected_html = getSelectedHtml(range, container);
        // One pass over the verses the selection touches: collect the verse text and its highlight range together.
        const verses = [];
        container.querySelectorAll('p').forEach(p => {
            if (!range.intersectsNode(p))
            {
                return;
            }
            const verseText = p.textContent.trim();
            if (verseText !== '')
            {
                verses.push(verseText);
            }
            // Headers (ids like "header_1") are saved as text only. The server accepts verse numbers as highlight keys.
            const isVerse = /^\d+$/.test(p.id);
            const highlight = isVerse && getVerseHighlight(range, p);
            if (highlight)
            {
                highlight_coordinates[p.id] = highlight;
            }
        });
        verses_text = verses.join('\n');
    }
    const selectedTextInputs = document.querySelectorAll('input[name="selected_text"]');
    const versesTextInputs = document.querySelectorAll('input[name="verses_text"]');
    const highlightCoordinatesInputs = document.querySelectorAll('input[name="highlight_coordinates"]');
    const selectedHtmlInputs = document.querySelectorAll('input[name="selected_html"]');
    if (text !== '')
    {
        // Selections outside the verses have no HTML, so fall back to the plain text, escaped
        if (selected_html === '')
        {
            const escaped = document.createElement('div');
            escaped.textContent = text;
            selected_html = escaped.innerHTML;
        }
        selectedTextInputs.forEach(input => { input.value = text; });
        versesTextInputs.forEach(input => { input.value = verses_text; });
        highlightCoordinatesInputs.forEach(input => { input.value = JSON.stringify(highlight_coordinates); });
        selectedHtmlInputs.forEach(input => { input.value = selected_html; });
        enableTextHighlightInteractables();
    }
    else if (!document.querySelector('.modal.show'))
    {
        selectedTextInputs.forEach(input => { input.value = ''; });
        versesTextInputs.forEach(input => { input.value = ''; });
        highlightCoordinatesInputs.forEach(input => { input.value = '{}'; });
        selectedHtmlInputs.forEach(input => { input.value = ''; });
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
