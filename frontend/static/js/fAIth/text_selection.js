// Function to enable all elements with text-highlight class
function enableTextHighlightInteractables()
{
    document.querySelectorAll('.text-highlight').forEach(element => {
        if (element.tagName === 'BUTTON') 
        {
            element.disabled = false;
        } 
        else 
        {
            element.classList.remove('disabled');
        }
    });
}

// Function to disable all elements with text-highlight class
function disableTextHighlightInteractables()
{
    document.querySelectorAll('.text-highlight').forEach(element => {
        if (element.tagName === 'BUTTON') 
        {
            element.disabled = true;
        } 
        else 
        {
            element.classList.add('disabled');
        }
    });
}

// Initialize selected data variable
var selectedText = "";

// Disable text highlight interactables on page load
disableTextHighlightInteractables();

document.addEventListener("mouseup", (event) => {
    handleTouch(event);
});
document.addEventListener("touchend", (event) => {
    handleTouch(event);
});

document.addEventListener("mousedown", (event) => {
    // Don't disable if clicking inside a modal or on a text-highlight element
    if (!event.target.closest('.text-highlight') && !event.target.closest('.modal') && !event.target.closest('.modal-backdrop'))
    {
        disableTextHighlightInteractables();
    }
});
document.addEventListener("touchstart", (event) => {
    // Don't disable if clicking inside a modal or on a text-highlight element
    if (!event.target.closest('.text-highlight') && !event.target.closest('.modal') && !event.target.closest('.modal-backdrop'))
    {
        disableTextHighlightInteractables();
    }
});

function handleTouch(event)
{
    // Get the selected text
    selectedText = document.getSelection();

    if (selectedText.toString() !== "") { // check if selectedText is not an empty string

        // Set the selected text in the hidden input field
        console.log(selectedText);
        document.getElementById('selectedTextInput').value = selectedText;
        // Enable the text highlight buttons
        enableTextHighlightInteractables();
    }
    else
    {
        // Disable when no text is selected
        disableTextHighlightInteractables();
    }
}

// Maintain highlighted content data while mouse clicking on highlight button to prevent internal deselection
document.addEventListener('mousedown', (event) => {
    if (event.target.closest('.text-highlight'))
    {
        // Prevent the button from clearing the selection
        event.preventDefault();
    }
});

// Maintain highlighted content data while screen tapping on highlight button to prevent internal deselection
document.addEventListener('touchstart', (event) => {
    if (event.target.closest('.text-highlight'))
    {
        // Prevent the button from clearing the selection
        event.preventDefault();
    }
});
