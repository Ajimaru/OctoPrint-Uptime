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
    self.octoprintUptimeDisplay = ko.observable("Loading...");

    var navbarEl = $("#navbar_plugin_navbar_uptime");
    var DEFAULT_POLL = 5;
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

    var pollTimer = null;

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

      OctoPrint.simpleApiGet("octoprint_uptime")
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
          var octoprintDisplayValue;

          // Format system uptime
          if (fmt === "full") {
            displayValue = data.uptime || "unknown";
            octoprintDisplayValue = data.octoprint_uptime || "unknown";
          } else if (fmt === "dhm") {
            displayValue = data.uptime_dhm || data.uptime || "unknown";
            octoprintDisplayValue =
              data.octoprint_uptime_dhm || data.octoprint_uptime || "unknown";
          } else if (fmt === "dh") {
            displayValue = data.uptime_dh || data.uptime || "unknown";
            octoprintDisplayValue =
              data.octoprint_uptime_dh || data.octoprint_uptime || "unknown";
          } else if (fmt === "d") {
            displayValue = data.uptime_d || data.uptime || "unknown";
            octoprintDisplayValue =
              data.octoprint_uptime_d || data.octoprint_uptime || "unknown";
          } else if (fmt === "short") {
            // legacy value: keep days+hours behaviour
            displayValue = data.uptime_short || data.uptime || "unknown";
            octoprintDisplayValue =
              data.octoprint_uptime_short || data.octoprint_uptime || "unknown";
          } else {
            displayValue = data.uptime || "unknown";
            octoprintDisplayValue = data.octoprint_uptime || "unknown";
          }

          // If server explicitly reports uptime unavailable, show localized "Unavailable"
          try {
            if (data && data.uptime_available === false) {
              if (typeof gettext === "function") {
                displayValue = gettext("Unavailable");
              } else {
                displayValue = "Unavailable";
              }
            }
          } catch (e) {
            if (typeof globalThis !== "undefined" && globalThis?.UptimeDebug) {
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
          self.octoprintUptimeDisplay(octoprintDisplayValue);

          // compute start time for tooltip from seconds if available
          try {
            var secs =
              data && typeof data.seconds !== "undefined"
                ? Number(data.seconds)
                : null;
            var octoprintSecs =
              data && typeof data.octoprint_seconds !== "undefined"
                ? Number(data.octoprint_seconds)
                : null;

            var tooltipLines = [];

            if (secs !== null && !isNaN(secs)) {
              var started = new Date(Date.now() - secs * 1000);
              var systemStartedLabel = "System Started:";
              if (typeof gettext === "function") {
                systemStartedLabel = gettext("System Started:");
              } else if (typeof _ === "function") {
                systemStartedLabel = _("System Started:");
              }
              tooltipLines.push(
                systemStartedLabel + " " + started.toLocaleString(),
              );
            }

            if (octoprintSecs !== null && !isNaN(octoprintSecs)) {
              var octoprintStarted = new Date(
                Date.now() - octoprintSecs * 1000,
              );
              var octoprintStartedLabel = "OctoPrint Started:";
              if (typeof gettext === "function") {
                octoprintStartedLabel = gettext("OctoPrint Started:");
              } else if (typeof _ === "function") {
                octoprintStartedLabel = _("OctoPrint Started:");
              }
              tooltipLines.push(
                octoprintStartedLabel + " " + octoprintStarted.toLocaleString(),
              );
            }

            if (tooltipLines.length > 0) {
              var startedText = tooltipLines.join("\n");
              var anchor = navbarEl.find("a").first();
              try {
                // dispose existing tooltip if present (remove bootstrap tooltip)
                if (anchor.data("bs.tooltip")) {
                  anchor.tooltip("dispose");
                }
              } catch (disposeErr) {
                if (
                  typeof globalThis !== "undefined" &&
                  globalThis.UptimeDebug
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
            if (typeof globalThis !== "undefined" && globalThis.UptimeDebug) {
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
            if (typeof globalThis !== "undefined" && globalThis?.UptimeDebug) {
              console.error(
                "octoprint_uptime: poll interval calculation error",
                e,
                data,
              );
            }
            // Ensure polling continues even if interval calculation fails
            scheduleNext(DEFAULT_POLL);
          }
        })
        .fail(function () {
          self.uptimeDisplay("Error");
          if (!isNavbarEnabled()) {
            navbarEl.hide();
          }
          // Continue polling even after failure (with default interval)
          scheduleNext(DEFAULT_POLL);
        });
    };

    // Start the polling loop; the initial fetch will reschedule itself based on
    // the server-provided `poll_interval_seconds` or local setting.
    fetchUptime();

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
        // Helper: Validate integer in range with localized message on failure.
        function validateIntegerRange(rawValue, min, max, message) {
          try {
            if (
              rawValue === "" ||
              rawValue === null ||
              rawValue === undefined
            ) {
              return typeof gettext === "function" ? gettext(message) : message;
            }
            var n = Number(rawValue);
            if (
              !Number.isFinite(n) ||
              n < min ||
              n > max ||
              Math.floor(n) !== n
            ) {
              return typeof gettext === "function" ? gettext(message) : message;
            }
          } catch (e) {}
          return null;
        }

        // Helper: Validate debug throttle
        function validateDebugThrottle() {
          try {
            var raw =
              settings.plugins.octoprint_uptime.debug_throttle_seconds();
          } catch (e) {
            return typeof gettext === "function"
              ? gettext("Unable to read debug throttle setting.")
              : "Unable to read debug throttle setting.";
          }
          return validateIntegerRange(
            raw,
            1,
            120,
            "Debug throttle must be an integer between 1 and 120 seconds.",
          );
        }

        // Helper: Validate poll interval
        function validatePollInterval() {
          var raw;
          try {
            raw = settings.plugins.octoprint_uptime.poll_interval_seconds();
          } catch (e) {
            return typeof gettext === "function"
              ? gettext("Unable to read polling interval setting.")
              : "Unable to read polling interval setting.";
          }
          return validateIntegerRange(
            raw,
            1,
            120,
            "Polling interval must be an integer between 1 and 120 seconds.",
          );
        }

        // Helper: Show error notification
        function showValidationErrors(errors) {
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
        }

        settingsVM.save = function () {
          var errors = [];
          var throttleError = validateDebugThrottle();
          if (throttleError) errors.push(throttleError);
          var pollError = validatePollInterval();
          if (pollError) errors.push(pollError);

          if (errors.length) {
            showValidationErrors(errors);
            return Promise.reject(new Error("validation failed"));
          }
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
