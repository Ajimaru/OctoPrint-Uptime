/*
 * octoprint_uptime/static/js/uptime.js
 *
 * Displays uptime in the navbar.
 */
$(function () {
  function NavbarUptimeViewModel(parameters) {
    var self = this;
    var settings =
      parameters[0] && parameters[0].settings
        ? parameters[0].settings
        : parameters[0];
    self.uptimeDisplay = ko.observable("Loading...");

    var navbarEl = $("#navbar_plugin_navbar_uptime");

    var isNavbarEnabled = function () {
      try {
        return settings.plugins.octoprint_uptime.navbar_enabled();
      } catch (e) {
        return true;
      }
    };

    var displayFormat = function () {
      try {
        return settings.plugins.octoprint_uptime.display_format() || "full";
      } catch (e) {
        return "full";
      }
    };

    var fetchUptime = function () {
      // If local settings explicitly disable the navbar, hide immediately
      if (!isNavbarEnabled()) {
        navbarEl.hide();
        return;
      }

      var url = "/api/plugin/octoprint_uptime";
      $.get(url)
        .done(function (data) {
          // Prefer server-side settings (reflect saved values immediately)
          var navbarEnabled =
            data && typeof data.navbar_enabled !== "undefined"
              ? data.navbar_enabled
              : isNavbarEnabled();
          if (!navbarEnabled) {
            // Server says navbar disabled — keep it hidden
            navbarEl.hide();
            return;
          }

          var fmt =
            data && data.display_format ? data.display_format : displayFormat();
          navbarEl.show();
          if (fmt === "short") {
            self.uptimeDisplay(data.uptime_short || data.uptime || "unknown");
          } else {
            self.uptimeDisplay(data.uptime || "unknown");
          }
        })
        .fail(function () {
          self.uptimeDisplay("Error");
          // If request fails, respect local setting
          if (!isNavbarEnabled()) {
            navbarEl.hide();
          }
        });
    };

    fetchUptime();
    setInterval(fetchUptime, 2 * 1000);
  }

  OCTOPRINT_VIEWMODELS.push([
    NavbarUptimeViewModel,
    ["settingsViewModel"],
    ["#navbar_plugin_navbar_uptime"],
  ]);
});
