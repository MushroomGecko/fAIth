// Once the user confirms they've saved the recovery codes, the button has done its job, so hide it.
document.getElementById('authenticator-setup').addEventListener('shown.bs.collapse', function () {
    document.getElementById('reveal-authenticator').classList.add('d-none');
});
