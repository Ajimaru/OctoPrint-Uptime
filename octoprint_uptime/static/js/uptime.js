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
          var displayValue;
          if (fmt === "full") {
            displayValue = data.uptime || "unknown";
          } else if (fmt === "dhm") {
            displayValue = data.uptime_dhm || data.uptime || "unknown";
          } else if (fmt === "dh") {
            displayValue = data.uptime_dh || data.uptime || "unknown";
          } else if (fmt === "d") {
            displayValue = data.uptime_d || data.uptime || "unknown";
          } else if (fmt === "short") {
            // legacy value: keep days+hours behaviour
            displayValue = data.uptime_short || data.uptime || "unknown";
          } else {
            displayValue = data.uptime || "unknown";
          }

          // update visible text
          self.uptimeDisplay(displayValue);

          // compute start time for tooltip from seconds if available
          try {
            var secs =
              data && typeof data.seconds !== "undefined"
                ? Number(data.seconds)
                : null;
            if (secs !== null && !isNaN(secs)) {
              var started = new Date(Date.now() - secs * 1000);
              // format like: "Started: 2026-01-19 12:34:56" using locale string
              var startedText = "Started: " + started.toLocaleString();
              var anchor = navbarEl.find("a").first();
              try {
                // dispose existing tooltip if present (remove bootstrap tooltip)
                if (anchor.data("bs.tooltip")) {
                  anchor.tooltip("dispose");
                }
              } catch (e) {}
              // Restore native browser tooltip by setting `title` and
              // removing any Bootstrap-specific attributes.
              anchor.attr("title", startedText);
              anchor.removeAttr("data-original-title");
            }
          } catch (e) {}
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
