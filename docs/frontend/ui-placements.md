# UI placements

This document describes where the navbar viewmodel is registered, how the plugin injects UI elements into OctoPrint pages, and how to customize or move the placement.

ViewModel registration

The viewmodel is registered in `octoprint_uptime/static/js/uptime.js` using the OctoPrint MVVM registration array. The array elements are:

- Constructor function: the ViewModel class (e.g. `NavbarUptimeViewModel`).
- Dependencies: an array of other viewmodel names the constructor expects (e.g. `['settingsViewModel']`).
- Selectors: one or more DOM selectors where OctoPrint will bind the viewmodel.

Example registration (excerpt):

```js
OCTOPRINT_VIEWMODELS.push([
  NavbarUptimeViewModel,
  ["settingsViewModel"],
  ["#navbar_plugin_navbar_uptime"],
]);
```

What this does

- OctoPrint will instantiate `NavbarUptimeViewModel`, passing the `settingsViewModel` instance into the constructor.
- It will bind the generated viewmodel to the DOM element matching `#navbar_plugin_navbar_uptime`.

Template anchor

The navbar template defines an anchor element with an ID where the viewmodel binds. The template file lives in the plugin package at `octoprint_uptime/templates/navbar.jinja2`. A minimal example:

```html
<li id="navbar_plugin_navbar_uptime" data-bind="visible: isNavbarEnabled">
  <a title="Uptime" data-bind="text: uptime"></a>
</li>
```

Customizing placement

- Change the selector in the `OCTOPRINT_VIEWMODELS.push` call to bind elsewhere (e.g. a different navbar region or a settings panel).
- Alternatively, update `navbar.jinja2` to move the anchor to another location inside the OctoPrint template structure.
- If you need to insert a block dynamically from Python (server-side), use OctoPrint's template hooks or the plugin's `get_template_vars` / template injection points.

Styling and assets

- Frontend sources live under `octoprint_uptime/static/js/` and `octoprint_uptime/static/less` (or `css`). Adjust styles in LESS sources and rebuild if necessary.
- When debugging, confirm the generated static files are packaged and served by OctoPrint (check the plugin assets path in browser DevTools).

API usage (frontend)

Always use OctoPrint's helper API to query plugin endpoints — pass the plugin id only. Example:

```js
OctoPrint.simpleApiGet("octoprint_uptime").done(function (data) {
  if (!data.uptime_available) {
    // show data.uptime_note to user or fallback UI
  } else {
    // use data.uptime, data.uptime_dhm, etc.
  }
});
```

Testing & debugging

- Restart your development OctoPrint instance (for example with `.development/restart_octoprint_dev.sh`) after code or template changes.
- Open browser DevTools, check the Console for errors and Network tab for the `/api/plugin/octoprint_uptime` request and its JSON response.
- If the element does not appear, verify the selector used in `OCTOPRINT_VIEWMODELS.push` matches an element present on the page and that `isNavbarEnabled` is true in settings.

Troubleshooting checklist

- Is the plugin loaded? Check `octoprint.log` for plugin initialization messages.
- Are static assets served? Open the JS file URL shown in the page source and confirm 200 response.
- Does the API return `uptime_available: true`? If false, inspect `uptime_note` for hints.
