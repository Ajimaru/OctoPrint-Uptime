# UI placements

Document where the navbar viewmodel is registered and how to adjust templates.

Navbar viewmodel registration:

The navbar viewmodel is registered in `octoprint_uptime/static/js/uptime.js` and exposed to the OctoPrint MVVM system. The viewmodel is pushed with:

```js
OCTOPRINT_VIEWMODELS.push([
  NavbarUptimeViewModel,
  ["settingsViewModel"],
  ["#navbar_plugin_navbar_uptime"],
]);
```

API usage note:

When calling the plugin from frontend code use the `OctoPrint` API helper and pass the plugin id only. Example:

```js
OctoPrint.simpleApiGet("octoprint_uptime").done(function (data) {
  /* ... */
});
```

Do not prefix the plugin id with `plugin/` when using `OctoPrint.simpleApiGet` — the helper automatically scopes requests to `/api/plugin/`.
