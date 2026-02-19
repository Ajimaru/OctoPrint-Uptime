# UI placements

This document describes where the navbar viewmodel is registered, how the plugin injects UI elements into OctoPrint pages, and how to customize or move the placement.

## ViewModel registration

The viewmodel is registered in `octoprint_uptime/static/js/uptime.js` using the OctoPrint MVVM registration array. The array elements are:

- Constructor function: the ViewModel class (e.g. `NavbarUptimeViewModel`).
- Dependencies: an array of other viewmodel names the constructor expects (e.g. `['settingsViewModel']`).
- Selectors: one or more DOM selectors where OctoPrint will bind the viewmodel.

## Example registration (excerpt)

```js
OCTOPRINT_VIEWMODELS.push([
  NavbarUptimeViewModel,
  ["settingsViewModel"],
  ["#navbar_plugin_navbar_uptime"],
]);
```

## What this does

- OctoPrint will instantiate `NavbarUptimeViewModel`, passing the `settingsViewModel` instance into the constructor.
- It will bind the generated viewmodel to the DOM element matching `#navbar_plugin_navbar_uptime`.

## Template anchor

The navbar template defines the anchor element where the ViewModel binds. The
actual template lives in `octoprint_uptime/templates/navbar.jinja2`:

```html
<li id="navbar_plugin_navbar_uptime" class="dropdown">
  <a href="#" class="dropdown-toggle" data-toggle="dropdown">
    <i class="fas fa-history"></i>
    <span data-bind="html: uptimeDisplayHtml"></span>
  </a>
</li>
```

Navbar visibility is controlled **in JavaScript** via `navbarEl.hide()` /
`navbarEl.show()` rather than a Knockout binding. The JavaScript evaluates
`show_system_uptime` and `show_octoprint_uptime` from the plugin settings on
every polling cycle and calls the appropriate jQuery method.

The same JavaScript path also injects the anchor `title` tooltip attribute at runtime in both normal
and compact display modes, so mouseover content remains consistent when
`compact_display` is enabled (the title is not present in the static template).

## Customizing placement

- Change the selector in the `OCTOPRINT_VIEWMODELS.push` call to bind elsewhere (e.g. a different navbar region or a settings panel).
- Alternatively, update `navbar.jinja2` to move the anchor to another location inside the OctoPrint template structure.
- If you need to insert a block dynamically from Python (server-side), use OctoPrint's template hooks or the plugin's `get_template_vars` / template injection points.

## Styling and assets

- Frontend sources live under `octoprint_uptime/static/js/` and `octoprint_uptime/static/less` (or `css`). Adjust styles in LESS sources and rebuild if necessary.
- When debugging, confirm the generated static files are packaged and served by OctoPrint (check the plugin assets path in browser DevTools).

## API usage (frontend)

Always use OctoPrint's helper to query the plugin's API; pass only the plugin identifier (the helper constructs the endpoint path automatically). Example:

```js
OctoPrint.simpleApiGet("octoprint_uptime").done(function (data) {
  if (!data.uptime_available) {
    // show data.uptime_note to user or fallback UI
  } else {
    // use data.uptime, data.uptime_dhm, etc.
  }
});
```

## Testing & debugging

- Open browser DevTools, check the Console for errors and the Network tab for
  the `/api/plugin/octoprint_uptime` request and its JSON response.
- If the element does not appear, verify that at least one of `show_system_uptime`
  or `show_octoprint_uptime` is enabled in the plugin settings
  (Settings → Plugin OctoPrint-Uptime).
- The ViewModel starts polling in `onStartupComplete`, not immediately in the
  constructor, so the navbar will only appear after OctoPrint's full startup
  sequence has completed.

## Troubleshooting checklist

- Is the plugin loaded? Check `octoprint.log` for plugin initialization messages.
- Are static assets served? Open the JS file URL shown in the page source and confirm 200 response.
- Does the API return `uptime_available: true`? If false, inspect `uptime_note` for hints.
- Are `show_system_uptime` or `show_octoprint_uptime` enabled? If both are false the
  navbar entry is hidden via `navbarEl.hide()`.
- Is `compact_display` enabled but only one uptime type is active? Compact mode
  only alternates when **both** uptime types are enabled; otherwise the single
  active type is displayed in regular mode.
