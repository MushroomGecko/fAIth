// HTMX skips swapping 4xx responses by default. The username form returns 400 with its error message,
// so swap that response into the account section to show the error next to the field.
document.body.addEventListener("htmx:beforeSwap", function (event) {
    if (event.detail.target.id === "accountPartialLoader" && event.detail.xhr.status === 400) {
        event.detail.shouldSwap = true;
        event.detail.isError = false;
    }
});
