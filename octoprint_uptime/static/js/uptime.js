/*
 * octoprint_uptime/static/js/uptime.js
 *
 * Displays uptime in the navbar.
 */
/**
 * Frontend module for the navbar uptime widget.
 * @module octoprint_uptime/navbar
 */
$(function () {
  /**
   * NavbarUptimeViewModel
   *
   * Displays the system uptime in the navbar and keeps it updated via polling.
   * @class
   * @memberof module:octoprint_uptime/navbar
   * @alias module:octoprint_uptime/navbar.NavbarUptimeViewModel
   * @param {Array} parameters - ViewModel parameters (expects `settingsViewModel`).
   */
  function NavbarUptimeViewModel(parameters) {
    var self = this;
    var settingsVM = parameters[0];
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

    /**
     * Check whether the navbar uptime widget is enabled in current settings.
     * @function isNavbarEnabled
     * @memberof module:octoprint_uptime/navbar.NavbarUptimeViewModel~
     * @returns {boolean} true when enabled, false otherwise
     */

    var displayFormat = function () {
      try {
        return settings.plugins.octoprint_uptime.display_format() || "full";
      } catch (e) {
        return "full";
      }
    };

    /**
     * Get the configured display format (fallback to "full").
     * @function displayFormat
     * @memberof module:octoprint_uptime/navbar.NavbarUptimeViewModel~
     * @returns {string} one of "full", "dhm", "dh", "d", or "short"
     */

    /**
     * Fetch uptime from the plugin API and update the navbar display and tooltip.
     * Silently updates polling interval based on server or local settings.
     * @function fetchUptime
     * @memberof module:octoprint_uptime/navbar.NavbarUptimeViewModel~
     * @returns {void}
     * @example
     * // Expected API response (partial):
     * // {
     * //   "seconds": 3600,
     * //   "uptime": "1 hour",
     * //   "uptime_dhm": "0d 1h 0m",
     * //   "uptime_short": "1h",
     * //   "navbar_enabled": true,
     * //   "display_format": "dhm",
     * //   "poll_interval_seconds": 5
     * // }
     */
    var fetchUptime = function () {
      // If local settings explicitly disable the navbar, hide immediately
      if (!isNavbarEnabled()) {
        navbarEl.hide();
        return;
      }

      OctoPrint.simpleApiGet("api/plugin/octoprint_uptime")
        .done(function (data) {
          // Prefer server-side settings
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

          // If server explicitly reports uptime unavailable, show localized "Unavailable"
          try {
            if (data && data.uptime_available === false) {
              if (typeof gettext === "function") {
                displayValue = gettext("Unavailable");
              } else if (typeof _ === "function") {
                displayValue = _("Unavailable");
              } else {
                displayValue = "Unavailable";
              }
            }
          } catch (e) {
            if (
              typeof window.UptimeDebug !== "undefined" &&
              window.UptimeDebug
            ) {
              console.error(
                "octoprint_uptime: error processing uptime_available flag",
                e,
                data,
              );
            } else {
              console.warn(
                "octoprint_uptime: error processing uptime_available flag",
              );
            }
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
              var startedText;
              if (typeof gettext === "function") {
                startedText =
                  gettext("Started:") + " " + started.toLocaleString();
              } else if (typeof _ === "function") {
                startedText = _("Started:") + " " + started.toLocaleString();
              } else {
                startedText = "Started: " + started.toLocaleString();
              }
              var anchor = navbarEl.find("a").first();
              try {
                // dispose existing tooltip if present (remove bootstrap tooltip)
                if (anchor.data("bs.tooltip")) {
                  anchor.tooltip("dispose");
                }
              } catch (disposeErr) {
                if (
                  typeof window.UptimeDebug !== "undefined" &&
                  window.UptimeDebug
                ) {
                  console.error(
                    "octoprint_uptime: failed to dispose existing tooltip",
                    disposeErr,
                  );
                } else {
                  console.warn(
                    "octoprint_uptime: failed to dispose existing tooltip",
                  );
                }
              }
              // Restore native browser tooltip by setting `title` and
              // removing any Bootstrap-specific attributes.
              anchor.attr("title", startedText);
              anchor.removeAttr("data-original-title");
            }
          } catch (e) {
            if (
              typeof window.UptimeDebug !== "undefined" &&
              window.UptimeDebug
            ) {
              console.error(
                "octoprint_uptime: tooltip calculation error",
                e,
                data,
              );
            }
          }
          // Determine poll interval from server or local settings
          try {
            var pollInterval = DEFAULT_POLL;
            if (data && typeof data.poll_interval_seconds !== "undefined") {
              pollInterval = Number(data.poll_interval_seconds) || DEFAULT_POLL;
            } else {
              try {
                var s =
                  settings.plugins.octoprint_uptime.poll_interval_seconds();
                if (s) pollInterval = Number(s) || DEFAULT_POLL;
              } catch (e) {}
            }
            scheduleNext(pollInterval);
          } catch (e) {
            if (
              typeof window.UptimeDebug !== "undefined" &&
              window.UptimeDebug
            ) {
              console.error(
                "octoprint_uptime: poll interval calculation error",
                e,
                data,
              );
            }
          }
        })
        .fail(function () {
          self.uptimeDisplay("Error");
          if (!isNavbarEnabled()) {
            navbarEl.hide();
          }
        });
    };

    var pollTimer = null;
    var DEFAULT_POLL = 5;

    /**
     * Schedule the next polling cycle.
     * @function scheduleNext
     * @memberof module:octoprint_uptime/navbar.NavbarUptimeViewModel~
     * @param {number} intervalSeconds - seconds until next poll (clamped by caller)
     * @returns {void}
     */
    function scheduleNext(intervalSeconds) {
      try {
        if (pollTimer) {
          clearTimeout(pollTimer);
        }
      } catch (e) {}
      pollTimer = setTimeout(fetchUptime, Math.max(1, intervalSeconds) * 1000);
    }

    // Start the polling loop; each fetch will reschedule itself based on
    // the server-provided `poll_interval_seconds` or local setting.
    fetchUptime();
    scheduleNext(DEFAULT_POLL);

    // Validate numeric settings on save: enforce integers in [1,120].
    try {
      if (settingsVM && typeof settingsVM.save === "function") {
        /**
         * Wrapped settings save that validates numeric plugin settings before
         * delegating to the original `settingsViewModel.save()`.
         * @function settingsVM.save
         * @memberof module:octoprint_uptime/navbar.NavbarUptimeViewModel~settingsVM
         * @returns {*} whatever the original `settingsViewModel.save()` returns
         * @example
         * // If validation fails, the wrapper shows an OctoPrint notification and
         * // does not call the original save. Example error messages:
         * // "Polling interval must be an integer between 1 and 120 seconds."
         */
        var origSave = settingsVM.save.bind(settingsVM);
        settingsVM.save = function () {
          try {
            var errors = [];
            try {
              var throttle = Number(
                settings.plugins.octoprint_uptime.debug_throttle_seconds(),
              );
              if (
                !Number.isFinite(throttle) ||
                throttle < 1 ||
                throttle > 120 ||
                Math.floor(throttle) !== throttle
              ) {
                errors.push(
                  typeof gettext === "function"
                    ? gettext(
                        "Debug throttle must be an integer between 1 and 120 seconds.",
                      )
                    : "Debug throttle must be an integer between 1 and 120 seconds.",
                );
              }
            } catch (e) {}
            try {
              var poll = Number(
                settings.plugins.octoprint_uptime.poll_interval_seconds(),
              );
              if (
                !Number.isFinite(poll) ||
                poll < 1 ||
                poll > 120 ||
                Math.floor(poll) !== poll
              ) {
                errors.push(
                  typeof gettext === "function"
                    ? gettext(
                        "Polling interval must be an integer between 1 and 120 seconds.",
                      )
                    : "Polling interval must be an integer between 1 and 120 seconds.",
                );
              }
            } catch (e) {}

            if (errors.length) {
              try {
                if (
                  typeof OctoPrint !== "undefined" &&
                  OctoPrint.notifications &&
                  OctoPrint.notifications.error
                ) {
                  OctoPrint.notifications.error(errors.join("\n"));
                } else {
                  alert(errors.join("\n"));
                }
              } catch (e) {
                alert(errors.join("\n"));
              }
              return;
            }
          } catch (e) {}
          return origSave();
        };
      }
    } catch (e) {}
  }

  OCTOPRINT_VIEWMODELS.push([
    NavbarUptimeViewModel,
    ["settingsViewModel"],
    ["#navbar_plugin_navbar_uptime"],
  ]);
});
