// Keep scroll positions across page reloads.
// Saves the window and every scrolled element that has an id, then restores them after a reload.
const scrollStorageKey = 'scrollPositions:' + location.pathname;

// pagehide fires before any reload or navigation, so the current positions get saved
window.addEventListener('pagehide', function ()
{
    const scrollPositions = { window: window.scrollY };
    document.querySelectorAll('[id]').forEach(function (scrollableElement)
    {
        if (scrollableElement.scrollHeight > scrollableElement.clientHeight)
        {
            scrollPositions[scrollableElement.id] = scrollableElement.scrollTop;
        }
    });
    sessionStorage.setItem(scrollStorageKey, JSON.stringify(scrollPositions));
});

// Only restore on a reload, not when arriving at the page by a normal navigation
const navigationEntry = performance.getEntriesByType('navigation')[0];
const savedScrollPositions = sessionStorage.getItem(scrollStorageKey);
if (navigationEntry && navigationEntry.type === 'reload' && savedScrollPositions !== null)
{
    const scrollPositions = JSON.parse(savedScrollPositions);
    window.scrollTo(0, scrollPositions.window || 0);
    Object.entries(scrollPositions).forEach(function ([id, savedScrollTop])
    {
        if (id === 'window') return;
        const restoredElement = document.getElementById(id);
        if (restoredElement) restoredElement.scrollTop = savedScrollTop;
    });
}
sessionStorage.removeItem(scrollStorageKey);
