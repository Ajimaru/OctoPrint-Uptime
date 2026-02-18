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
    // Dynamic accessor: always re-resolves settingsVM.settings to avoid stale
    // captures when the ViewModel is constructed before settings are loaded.
    /**
     * Return the plugin-specific settings object (`settings.plugins.octoprint_uptime`).
     * Re-resolves on every call so that the ViewModel never holds a stale
     * reference captured before `settingsViewModel.settings` was ready.
     * @function getPluginSettings
     * @memberof module:octoprint_uptime/navbar.NavbarUptimeViewModel~
     * @returns {Object|null} The KO-mapped plugin settings node, or `null` when
     *   unavailable (e.g. during early startup before settings are loaded).
     */
    var getPluginSettings = function () {
      try {
        var s =
          settingsVM && settingsVM.settings ? settingsVM.settings : settingsVM;
        return s && s.plugins ? s.plugins.octoprint_uptime : null;
      } catch (e) {
        return null;
      }
    };
    self.uptimeDisplay = ko.observable("Loading...");
    self.octoprintUptimeDisplay = ko.observable("Loading...");
    self.uptimeDisplayHtml = ko.observable("Loading...");

    var navbarEl = $("#navbar_plugin_navbar_uptime");
    var DEFAULT_POLL = 5;
    var DEFAULT_COMPACT_TOGGLE_INTERVAL = 5; // seconds, used as fallback
    var compactToggleTimer = null;
    var compactDisplayUptimeType = "system"; // "system" or "octoprint"

    /**
     * Return the configured compact toggle interval in seconds.
     * Reads `compact_toggle_interval_seconds` from plugin settings and validates
     * the result against the allowed range (5–60). Falls back to
     * `DEFAULT_COMPACT_TOGGLE_INTERVAL` when settings are unavailable or the
     * stored value is out of range.
     * @function getCompactToggleInterval
     * @memberof module:octoprint_uptime/navbar.NavbarUptimeViewModel~
     * @returns {number} interval in seconds (integer, 5–60)
     */
    function getCompactToggleInterval() {
      try {
        var ps = getPluginSettings();
        if (!ps) return DEFAULT_COMPACT_TOGGLE_INTERVAL;
        var raw = ps.compact_toggle_interval_seconds();
        var n = parseInt(raw, 10);
        if (!Number.isFinite(n) || n < 5 || n > 60)
          return DEFAULT_COMPACT_TOGGLE_INTERVAL;
        return n;
      } catch (e) {
        return DEFAULT_COMPACT_TOGGLE_INTERVAL;
      }
    }

    /**
     * Determine whether the navbar widget should be visible.
     * Returns `true` when at least one of `show_system_uptime` or
     * `show_octoprint_uptime` is enabled in the plugin settings, or when
     * settings are not yet available (fail-safe: show by default).
     * @function isNavbarEnabled
     * @memberof module:octoprint_uptime/navbar.NavbarUptimeViewModel~
     * @returns {boolean}
     */
    var isNavbarEnabled = function () {
      try {
        var ps = getPluginSettings();
        if (!ps) return true; // default: show navbar when settings unavailable
        return ps.show_system_uptime() || ps.show_octoprint_uptime();
      } catch (e) {
        return true;
      }
    };

    /**
     * Check whether the system uptime entry should be shown.
     * @function showSystemUptime
     * @memberof module:octoprint_uptime/navbar.NavbarUptimeViewModel~
     * @returns {boolean} true when enabled, false otherwise
     */
    var showSystemUptime = function () {
      try {
        var ps = getPluginSettings();
        return ps ? ps.show_system_uptime() : true;
      } catch (e) {
        return true;
      }
    };

    /**
     * Check whether OctoPrint uptime should be shown alongside system uptime.
     * @function showOctoprintUptime
     * @memberof module:octoprint_uptime/navbar.NavbarUptimeViewModel~
     * @returns {boolean} true when enabled, false otherwise
     */
    var showOctoprintUptime = function () {
      try {
        var ps = getPluginSettings();
        return ps ? ps.show_octoprint_uptime() : true;
      } catch (e) {
        return true;
      }
    };

    /**
     * Check whether compact display mode is enabled.
     * In compact mode, system and OctoPrint uptime alternate in the navbar
     * instead of being shown side-by-side.
     * @function isCompactDisplay
     * @memberof module:octoprint_uptime/navbar.NavbarUptimeViewModel~
     * @returns {boolean} true when compact display is enabled, false otherwise
     */
    var isCompactDisplay = function () {
      try {
        var ps = getPluginSettings();
        return ps ? ps.compact_display() : false;
      } catch (e) {
        return false;
      }
    };

    /**
     * Get the configured display format (fallback to "full").
     * @function displayFormat
     * @memberof module:octoprint_uptime/navbar.NavbarUptimeViewModel~
     * @returns {string} one of "full", "dhm", "dh", "d", or "short"
     */
    var displayFormat = function () {
      try {
        var ps = getPluginSettings();
        return (ps && ps.display_format()) || "full";
      } catch (e) {
        return "full";
      }
    };

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
     * Schedule the next polling cycle using the poll interval from the last API
     * response. Falls back to the local setting or `DEFAULT_POLL` if the
     * response does not include `poll_interval_seconds`.
     * @function scheduleNextFromData
     * @memberof module:octoprint_uptime/navbar.NavbarUptimeViewModel~
     * @param {Object|null} data - The API response object, or null/undefined.
     * @returns {void}
     */
    function scheduleNextFromData(data) {
      try {
        var pollInterval = DEFAULT_POLL;
        if (data && typeof data.poll_interval_seconds !== "undefined") {
          pollInterval = Number(data.poll_interval_seconds) || DEFAULT_POLL;
        } else {
          try {
            var ps = getPluginSettings();
            var s = ps ? ps.poll_interval_seconds() : null;
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
    }

    /**
     * Render the current frame of the compact display.
     * Reads `compactDisplayUptimeType` ("system" or "octoprint") and updates
     * `uptimeDisplayHtml` with the corresponding uptime string.
     * @function renderCompactDisplay
     * @memberof module:octoprint_uptime/navbar.NavbarUptimeViewModel~
     * @returns {void}
     */
    function renderCompactDisplay() {
      var htmlDisplay;
      var uptimeLabel = "Uptime:";
      if (typeof gettext === "function") {
        uptimeLabel = gettext("Uptime:");
      } else if (typeof _ === "function") {
        uptimeLabel = _("Uptime:");
      }

      if (
        compactDisplayUptimeType === "system" &&
        self.uptimeDisplay() !== "Loading..." &&
        self.uptimeDisplay() !== "Error"
      ) {
        var systemLabel = "System";
        if (typeof gettext === "function") {
          systemLabel = gettext("System");
        } else if (typeof _ === "function") {
          systemLabel = _("System");
        }
        htmlDisplay =
          uptimeLabel + " " + systemLabel + " " + self.uptimeDisplay();
      } else if (
        compactDisplayUptimeType === "octoprint" &&
        self.octoprintUptimeDisplay() !== "Loading..." &&
        self.octoprintUptimeDisplay() !== "Error"
      ) {
        var octoprintLabel = "OctoPrint";
        if (typeof gettext === "function") {
          octoprintLabel = gettext("OctoPrint");
        } else if (typeof _ === "function") {
          octoprintLabel = _("OctoPrint");
        }
        htmlDisplay =
          uptimeLabel +
          " " +
          octoprintLabel +
          " " +
          self.octoprintUptimeDisplay();
      }

      if (htmlDisplay) {
        self.uptimeDisplayHtml(htmlDisplay);
      }
    }

    /**
     * Schedule the compact display toggle timer.
     * Alternates `compactDisplayUptimeType` between "system" and "octoprint"
     * using the interval from `getCompactToggleInterval()` (reads the
     * `compact_toggle_interval_seconds` plugin setting on every cycle, 5–60 s).
     * No-ops if already scheduled.
     * @function scheduleCompactToggle
     * @memberof module:octoprint_uptime/navbar.NavbarUptimeViewModel~
     * @returns {void}
     */
    function scheduleCompactToggle() {
      if (compactToggleTimer) {
        return;
      }
      compactToggleTimer = setTimeout(function () {
        compactToggleTimer = null;
        compactDisplayUptimeType =
          compactDisplayUptimeType === "system" ? "octoprint" : "system";
        renderCompactDisplay();
        scheduleCompactToggle();
      }, getCompactToggleInterval() * 1000);
    }

    /**
     * Cancel any pending compact toggle timer.
     * Safe to call when no timer is active.
     * @function stopCompactToggleLoop
     * @memberof module:octoprint_uptime/navbar.NavbarUptimeViewModel~
     * @returns {void}
     */
    function stopCompactToggleLoop() {
      try {
        if (compactToggleTimer) {
          clearTimeout(compactToggleTimer);
        }
      } catch (e) {}
      compactToggleTimer = null;
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
     * //   "display_format": "dhm",
     * //   "poll_interval_seconds": 5
     * // }
     */
    var fetchUptime = function () {
      // If local settings explicitly disable the navbar, hide immediately
      if (!isNavbarEnabled()) {
        navbarEl.hide();
        stopCompactToggleLoop();
        scheduleNext(DEFAULT_POLL);
        return;
      }

      OctoPrint.simpleApiGet("octoprint_uptime")
        .done(function (data) {
          if (!isNavbarEnabled()) {
            navbarEl.hide();
            stopCompactToggleLoop();
            scheduleNextFromData(data);
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
            // Use dh format for OctoPrint uptime in legacy "short" mode
            octoprintDisplayValue =
              data.octoprint_uptime_dh || data.octoprint_uptime || "unknown";
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

          // Build HTML display based on settings
          var htmlDisplay;
          var showSystem = showSystemUptime();
          var showOctoprint = showOctoprintUptime();
          var useCompactDisplay = isCompactDisplay();

          // Get localized labels
          var uptimeLabel = "Uptime:";
          var systemLabel = "System";
          var octoprintLabel = "OctoPrint";
          if (typeof gettext === "function") {
            uptimeLabel = gettext("Uptime:");
            systemLabel = gettext("System");
            octoprintLabel = gettext("OctoPrint");
          } else if (typeof _ === "function") {
            uptimeLabel = _("Uptime:");
            systemLabel = _("System");
            octoprintLabel = _("OctoPrint");
          }

          // Handle compact display (toggling between system and octoprint)
          if (useCompactDisplay && showSystem && showOctoprint) {
            renderCompactDisplay();
            scheduleCompactToggle();
            scheduleNextFromData(data);
            return;
          }

          // Cancel any pending compact toggle timer if not in compact mode
          stopCompactToggleLoop();

          // Regular display logic: show selected uptimes
          if (showSystem && showOctoprint) {
            htmlDisplay =
              uptimeLabel +
              " " +
              systemLabel +
              " " +
              displayValue +
              " | " +
              octoprintLabel +
              " " +
              octoprintDisplayValue;
          } else if (showSystem) {
            htmlDisplay = uptimeLabel + " " + systemLabel + " " + displayValue;
          } else if (showOctoprint) {
            htmlDisplay =
              uptimeLabel + " " + octoprintLabel + " " + octoprintDisplayValue;
          } else {
            navbarEl.hide();
            stopCompactToggleLoop();
            scheduleNextFromData(data);
            return;
          }
          self.uptimeDisplayHtml(htmlDisplay);

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

            if (
              showOctoprint &&
              octoprintSecs !== null &&
              !isNaN(octoprintSecs)
            ) {
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
          scheduleNextFromData(data);
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

    /**
     * OctoPrint lifecycle hook – called once after all ViewModels have been
     * bound and the settings are fully populated.
     *
     * Polling is deliberately deferred to this hook instead of starting
     * immediately in the constructor, so that `getPluginSettings()` can
     * resolve the Knockout observables from `settingsViewModel.settings`
     * reliably on the very first call.
     * @function onStartupComplete
     * @memberof module:octoprint_uptime/navbar.NavbarUptimeViewModel
     * @returns {void}
     */
    self.onStartupComplete = function () {
      fetchUptime();
    };

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

        // Helper: Validate compact toggle interval
        function validateCompactToggleInterval() {
          var raw;
          try {
            var ps = getPluginSettings();
            raw = ps ? ps.compact_toggle_interval_seconds() : undefined;
          } catch (e) {
            return typeof gettext === "function"
              ? gettext("Unable to read compact toggle interval setting.")
              : "Unable to read compact toggle interval setting.";
          }
          return validateIntegerRange(
            raw,
            5,
            60,
            "Compact toggle interval must be an integer between 5 and 60 seconds.",
          );
        }

        // Helper: Validate debug throttle
        function validateDebugThrottle() {
          try {
            var ps = getPluginSettings();
            var raw = ps ? ps.debug_throttle_seconds() : undefined;
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
            var ps = getPluginSettings();
            raw = ps ? ps.poll_interval_seconds() : undefined;
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
          var compactToggleError = validateCompactToggleInterval();
          if (compactToggleError) errors.push(compactToggleError);
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
