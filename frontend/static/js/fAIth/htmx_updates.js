// Show loading message and switch modals before HTMX request
// Generalized handler for all AI forms with data-input-modal attribute
document.querySelectorAll('[data-input-modal]').forEach(form => 
{
    form.addEventListener('htmx:beforeRequest', function() 
    {
        const modalId = this.dataset.inputModal;
        
        // Close the prompt modal
        const inputModal = bootstrap.Modal.getInstance(document.getElementById(modalId));
        if (inputModal) inputModal.hide();
        
        // Set loading content
        document.getElementById('serverResponseContent').innerHTML = 'Loading...';
        
        // Show the response modal with loading message
        const responseModal = bootstrap.Modal.getOrCreateInstance(document.getElementById('serverResponseModal'));
        responseModal.show();
    });
});

// When response modal closes, ensure input modals are also closed
document.getElementById('serverResponseModal').addEventListener('hide.bs.modal', function()
{
    document.querySelectorAll('[data-input-modal]').forEach(form =>
    {
        const modalId = form.dataset.inputModal;
        const inputModal = bootstrap.Modal.getInstance(document.getElementById(modalId));
        if (inputModal) inputModal.hide();
    });
});