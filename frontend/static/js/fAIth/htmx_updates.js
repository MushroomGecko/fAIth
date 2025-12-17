// Show loading message and switch modals before HTMX request
document.getElementById('promptUserForm')?.addEventListener('htmx:beforeRequest', function() {
    // Close the prompt modal
    const promptModal = bootstrap.Modal.getInstance(document.getElementById('promptUserModal'));
    if (promptModal) promptModal.hide();

    // Set loading content
    document.getElementById('serverResponseContent').innerHTML = 'Loading...';
    
    // Show the response modal with loading message
    const responseModal = new bootstrap.Modal(document.getElementById('serverResponseModal'));
    responseModal.show();
});