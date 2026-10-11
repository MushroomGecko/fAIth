// Leaving the Security page with an unfinished two-factor setup drops that setup, like signup does.
// Sidebar links swap content without leaving the page, so the server handles those (see the Account section view).
// This covers the other ways out: the navbar link, reloading, and closing the tab.
window.addEventListener("pagehide", function () {
    var setupCode = document.getElementById("totp-setup-otp");
    if (!setupCode) {
        return;
    }

    var csrfInput = document.querySelector("input[name=csrfmiddlewaretoken]");
    var body = new URLSearchParams();
    body.append("csrfmiddlewaretoken", csrfInput ? csrfInput.value : "");

    // keepalive lets the request finish even while the page is unloading.
    fetch(setupCode.dataset.cancelUrl, {
        method: "POST",
        body: body,
        keepalive: true,
        credentials: "same-origin",
    });
});
