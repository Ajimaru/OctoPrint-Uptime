// @ts-nocheck
/* oxlint-disable */
/*
 * octoprint_uptime/static/js/uptime.js
 *
 * Displays uptime in the navbar.
 */
/**
 * Frontend module for the navbar uptime widget.
 * @module octoprint_uptime/navbar
 */
/* global $, ko, OctoPrint, OCTOPRINT_VIEWMODELS, gettext, _, alert, Promise */
const localize = (text) => {
  if (typeof window.gettext === "function") {
    return window.gettext(text);
  }
  if (typeof window._ === "function") {
    return window._(text);
  }
  return text;
};

/**
 * NavbarUptimeViewModel
 *
 * Displays the system uptime in the navbar and keeps it updated via polling.
 * @class
 * @memberof module:octoprint_uptime/navbar
 * @alias module:octoprint_uptime/navbar.NavbarUptimeViewModel
 * @param {Array} parameters - ViewModel parameters (expects `settingsViewModel`).
 */
const NavbarUptimeViewModel = function (parameters = []) {
  /**
   * Dynamic accessor: always re-resolves settingsVM.settings to avoid stale
   * captures when the ViewModel is constructed before settings are loaded.
   */
  const settingsVM = parameters[0];
  /**
   * Return the plugin-specific settings object (`settings.plugins.octoprint_uptime`).
   * Re-resolves on every call so that the ViewModel never holds a stale
   * reference captured before `settingsViewModel.settings` was ready.
   * @function getPluginSettings
   * @memberof module:octoprint_uptime/navbar.NavbarUptimeViewModel~
   * @returns {Object|boolean} The KO-mapped plugin settings node, or `false` when
   *   unavailable (e.g. during early startup before settings are loaded).
   */
  function getPluginSettings() {
    try {
      if (!settingsVM) {
        return false;
      }
      if (!settingsVM.settings) {
        return false;
      }
      const s = settingsVM.settings;
      return s && s.plugins ? s.plugins.octoprint_uptime : false;
    } catch {
      return false;
    }
    return false;
  }

  const uptimeDisplay = window.ko.observable("Loading...");
  const octoprintUptimeDisplay = window.ko.observable("Loading...");
  const uptimeDisplayText = window.ko.observable("Loading...");

  this.uptimeDisplay = uptimeDisplay;
  this.octoprintUptimeDisplay = octoprintUptimeDisplay;
  this.uptimeDisplayText = uptimeDisplayText;

  var navbarEl = $("#navbar_plugin_navbar_uptime");
  var DEFAULT_POLL = 5;
  var DEFAULT_COMPACT_TOGGLE_INTERVAL = 5; // seconds, used as fallback
  var compactToggleTimer = 0;
  var compactDisplayUptimeType = "system"; // "system" or "octoprint"

  /**
   * Return the configured compact toggle interval in seconds.
   * Reads `compact_toggle_interval_seconds` from plugin settings and validates
   * the result against the allowed range (5-60). Falls back to
   * `DEFAULT_COMPACT_TOGGLE_INTERVAL` when settings are unavailable or the
   * stored value is out of range.
   * @function getCompactToggleInterval
   * @memberof module:octoprint_uptime/navbar.NavbarUptimeViewModel~
   * @returns {number} interval in seconds (integer, 5-60)
   */
  function getCompactToggleInterval() {
    try {
      const ps = getPluginSettings();
      if (!ps) return DEFAULT_COMPACT_TOGGLE_INTERVAL;
      const raw = ps.compact_toggle_interval_seconds();
      const n = parseInt(raw, 10);
      if (!Number.isFinite(n) || n < 5 || n > 60)
        return DEFAULT_COMPACT_TOGGLE_INTERVAL;
      return n;
    } catch {
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
  function isNavbarEnabled() {
    try {
      const ps = getPluginSettings();
      if (!ps) return true; // default: show navbar when settings unavailable
      return ps.show_system_uptime() || ps.show_octoprint_uptime();
    } catch {
      return true;
    }
    return true;
  }

  /**
   * Check whether the system uptime entry should be shown.
   * @function showSystemUptime
   * @memberof module:octoprint_uptime/navbar.NavbarUptimeViewModel~
   * @returns {boolean} true when enabled, false otherwise
   */
  function showSystemUptime() {
    try {
      const ps = getPluginSettings();
      return ps ? ps.show_system_uptime() : true;
    } catch {
      return true;
    }
    return true;
  }

  /**
   * Check whether OctoPrint uptime should be shown alongside system uptime.
   * @function showOctoprintUptime
   * @memberof module:octoprint_uptime/navbar.NavbarUptimeViewModel~
   * @returns {boolean} true when enabled, false otherwise
   */
  function showOctoprintUptime() {
    try {
      const ps = getPluginSettings();
      return ps ? ps.show_octoprint_uptime() : true;
    } catch {
      return true;
    }
    return true;
  }

  /**
   * Check whether compact display mode is enabled.
   * In compact mode, system and OctoPrint uptime alternate in the navbar
   * instead of being shown side-by-side.
   * @function isCompactDisplay
   * @memberof module:octoprint_uptime/navbar.NavbarUptimeViewModel~
   * @returns {boolean} true when compact display is enabled, false otherwise
   */
  function isCompactDisplay() {
    try {
      const ps = getPluginSettings();
      return ps ? ps.compact_display() : false;
    } catch {
      return false;
    }
    return false;
  }

  /**
   * Get the configured display format (fallback to "full").
   * @function displayFormat
   * @memberof module:octoprint_uptime/navbar.NavbarUptimeViewModel~
   * @returns {string} one of "full", "dhm", "dh", or "d"
   */
  function displayFormat() {
    try {
      const ps = getPluginSettings();
      if (!ps) {
        return "full";
      }
      return ps.display_format() || "full";
    } catch {
      return "full";
    }
    return "full";
  }

  var pollTimer = 0;
  var fetchUptime = function () {
    return false;
  };

  /**
   * Schedule the next polling cycle.
   * @function scheduleNext
   * @memberof module:octoprint_uptime/navbar.NavbarUptimeViewModel~
   * @param {number} intervalSeconds - seconds until next poll (clamped by caller)
   * @returns {void}
   */
  const scheduleNext = function (intervalSeconds = DEFAULT_POLL) {
    const seconds = Number(intervalSeconds) || DEFAULT_POLL;
    try {
      if (pollTimer) {
        clearTimeout(pollTimer);
      }
    } catch {}
    pollTimer = setTimeout(() => fetchUptime(), Math.max(1, seconds) * 1000);
    return !!pollTimer;
  };

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
      let pollInterval = DEFAULT_POLL;
      if (data && typeof data.poll_interval_seconds !== "undefined") {
        pollInterval = Number(data.poll_interval_seconds) || DEFAULT_POLL;
      } else {
        try {
          const ps = getPluginSettings();
          const s = ps ? ps.poll_interval_seconds() : false;
          if (s) pollInterval = Number(s) || DEFAULT_POLL;
        } catch {}
      }
      return scheduleNext(pollInterval);
    } catch {
      if (typeof window !== "undefined" && window.UptimeDebug) {
        console.error(
          "octoprint_uptime: poll interval calculation error",
          data,
        );
      }
      // Ensure polling continues even if interval calculation fails
      return scheduleNext(DEFAULT_POLL);
    }
    return false;
  }

  /**
   * Render the current frame of the compact display.
   * Reads `compactDisplayUptimeType` ("system" or "octoprint") and updates
   * `uptimeDisplayText` with the corresponding uptime string.
   * @function renderCompactDisplay
   * @memberof module:octoprint_uptime/navbar.NavbarUptimeViewModel~
   * @returns {void}
   */
  function renderCompactDisplay() {
    var textDisplay;
    var uptimeLabel = localize("Uptime:");
    var systemLabel = localize("System");
    var octoprintLabel = localize("OctoPrint");

    if (
      compactDisplayUptimeType === "system" &&
      uptimeDisplay() !== "Loading..." &&
      uptimeDisplay() !== "Error"
    ) {
      textDisplay = uptimeLabel + " " + systemLabel + " " + uptimeDisplay();
    } else if (
      compactDisplayUptimeType === "octoprint" &&
      octoprintUptimeDisplay() !== "Loading..." &&
      octoprintUptimeDisplay() !== "Error"
    ) {
      textDisplay =
        uptimeLabel + " " + octoprintLabel + " " + octoprintUptimeDisplay();
    } else if (compactDisplayUptimeType === "system") {
      // Show system even if loading/error
      textDisplay = uptimeLabel + " " + systemLabel + " " + uptimeDisplay();
    } else {
      // Show octoprint even if loading/error
      textDisplay =
        uptimeLabel + " " + octoprintLabel + " " + octoprintUptimeDisplay();
    }

    uptimeDisplayText(textDisplay);
    return true;
  }

  /**
   * Schedule the compact display toggle timer.
   * Alternates `compactDisplayUptimeType` between "system" and "octoprint"
   * using the interval from `getCompactToggleInterval()` (reads the
   * `compact_toggle_interval_seconds` plugin setting on every cycle, 5-60 s).
   * No-ops if already scheduled.
   * @function scheduleCompactToggle
   * @memberof module:octoprint_uptime/navbar.NavbarUptimeViewModel~
   * @returns {void}
   */
  function scheduleCompactToggle() {
    if (compactToggleTimer) {
      return false;
    }
    compactToggleTimer = setTimeout(() => {
      compactToggleTimer = 0;
      compactDisplayUptimeType =
        compactDisplayUptimeType === "system" ? "octoprint" : "system";
      renderCompactDisplay();
      scheduleCompactToggle();
    }, getCompactToggleInterval() * 1000);
    return true;
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
    } catch {}
    compactToggleTimer = 0;
    return true;
  }

  /**
   * Update navbar anchor tooltip with localized start times.
   * Keeps tooltip behavior identical across compact and non-compact display.
   * @function updateNavbarTooltip
   * @memberof module:octoprint_uptime/navbar.NavbarUptimeViewModel~
   * @param {Object} data - API payload that may include uptime second counters.
   * @param {boolean} includeOctoprint - Whether to include OctoPrint start time.
   * @returns {void}
   */
  function updateNavbarTooltip(data, includeOctoprint) {
    try {
      const secs =
        data && data.seconds != null
          ? Number(data.seconds)
          : Number.NaN;
      const octoprintSecs =
        data && data.octoprint_seconds != null
          ? Number(data.octoprint_seconds)
          : Number.NaN;

      const tooltipLines = [];

      if (Number.isFinite(secs) && secs >= 0) {
        var started = new Date(new Date().getTime() - secs * 1000);
        const systemStartedLabel = localize("System Started:");
        tooltipLines.push(systemStartedLabel + " " + started.toLocaleString());
      }

      if (
        includeOctoprint &&
        Number.isFinite(octoprintSecs) &&
        octoprintSecs >= 0
      ) {
        var octoprintStarted = new Date(
          new Date().getTime() - octoprintSecs * 1000,
        );
        const octoprintStartedLabel = localize("OctoPrint Started:");
        tooltipLines.push(
          octoprintStartedLabel + " " + octoprintStarted.toLocaleString(),
        );
      }

      if (tooltipLines.length > 0) {
        const startedText = tooltipLines.join("\n");
        const anchor = navbarEl.find("a").first();
        try {
          if (anchor.data("bs.tooltip")) {
            anchor.tooltip("destroy");
          }
        } catch (disposeErr) {
          if (typeof window !== "undefined" && window.UptimeDebug) {
            console.error(
              "octoprint_uptime: failed to dispose existing tooltip: " +
                String(disposeErr),
            );
          } else {
            console.warn(
              "octoprint_uptime: failed to dispose existing tooltip",
            );
          }
          // Fallback: attempt safe cleanup if normal disposal failed
          try {
            anchor.tooltip("hide");
            anchor.removeData("bs.tooltip");
            anchor.removeAttr("data-original-title");
            anchor.removeAttr("data-bs-original-title");
          } catch (fallbackErr) {
            if (typeof window !== "undefined" && window.UptimeDebug) {
              console.error(
                "octoprint_uptime: fallback tooltip cleanup also failed",
                fallbackErr,
              );
            }
          }
        }
        anchor.attr("title", startedText);
        anchor.removeAttr("data-original-title");
      }
    } catch {
      if (typeof window !== "undefined" && window.UptimeDebug) {
        console.error(
          "octoprint_uptime: tooltip calculation error: " +
            JSON.stringify(data || {}),
        );
      }
    }
    return true;
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
   * //   "display_format": "dhm",
   * //   "poll_interval_seconds": 5
   * // }
   */
  fetchUptime = function () {
    // If local settings explicitly disable the navbar, hide immediately
    if (!isNavbarEnabled()) {
      navbarEl.hide();
      stopCompactToggleLoop();
      scheduleNext(DEFAULT_POLL);
      return false;
    }

    return window.OctoPrint.simpleApiGet("octoprint_uptime")
      .done((data) => {
        if (!isNavbarEnabled()) {
          navbarEl.hide();
          stopCompactToggleLoop();
          scheduleNextFromData(data);
          return false;
        }

        let fmt = displayFormat();
        if (data && data.display_format) {
          fmt = data.display_format;
        }
        navbarEl.show();
        let displayValue = "unknown";
        let octoprintDisplayValue = "unknown";

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
          // legacy value: keep days+hours behavior
          displayValue = data.uptime_dh || data.uptime || "unknown";
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
            displayValue = localize("Unavailable");
          }
        } catch {
          if (typeof window !== "undefined" && window.UptimeDebug) {
            console.error(
              "octoprint_uptime: error processing uptime_available flag: " +
                "data=" +
                JSON.stringify(data || {}),
            );
          } else {
            console.warn(
              "octoprint_uptime: error processing uptime_available flag",
            );
          }
        }

        // update visible text
        uptimeDisplay(displayValue);
        octoprintUptimeDisplay(octoprintDisplayValue);

        // Build HTML display based on settings
        let textDisplay;
        const showSystem = showSystemUptime();
        const showOctoprint = showOctoprintUptime();
        const useCompactDisplay = isCompactDisplay();

        // Get localized labels
        const uptimeLabel = localize("Uptime:");
        const systemLabel = localize("System");
        const octoprintLabel = localize("OctoPrint");

        // Handle compact display (toggling between system and octoprint)
        if (useCompactDisplay && showSystem && showOctoprint) {
          updateNavbarTooltip(data, showOctoprint);
          renderCompactDisplay();
          scheduleCompactToggle();
          scheduleNextFromData(data);
          return true;
        }

        // Cancel any pending compact toggle timer if not in compact mode
        stopCompactToggleLoop();

        // Regular display logic: show selected uptimes
        if (showSystem && showOctoprint) {
          textDisplay = `${uptimeLabel} ${systemLabel} ${displayValue} | ${octoprintLabel} ${octoprintDisplayValue}`;
        } else if (showSystem) {
          textDisplay = `${uptimeLabel} ${systemLabel} ${displayValue}`;
        } else if (showOctoprint) {
          textDisplay = `${uptimeLabel} ${octoprintLabel} ${octoprintDisplayValue}`;
        } else {
          navbarEl.hide();
          stopCompactToggleLoop();
          scheduleNextFromData(data);
          return false;
        }
        uptimeDisplayText(textDisplay);
        updateNavbarTooltip(data, showOctoprint);
        scheduleNextFromData(data);
        return true;
      })
      .fail(() => {
        uptimeDisplay("Error");
        if (!isNavbarEnabled()) {
          navbarEl.hide();
        }
        // Continue polling even after failure (with default interval)
        scheduleNext(DEFAULT_POLL);
        return false;
      });
  };

  /**
   * OctoPrint lifecycle hook - called once after all ViewModels have been
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
  this.onStartupComplete = () => {
    fetchUptime();
    return true;
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
      const origSave = settingsVM.save.bind(settingsVM);
      // Helper: Validate integer in range with localized message on failure.
      var validateIntegerRange = function (rawValue, min, max, message) {
        try {
          if (rawValue === "" || rawValue === null || rawValue === undefined) {
            return localize(message);
          }
          const n = Number(rawValue);
          if (
            !Number.isFinite(n) ||
            n < min ||
            n > max ||
            Math.floor(n) !== n
          ) {
            return localize(message);
          }
        } catch {}
        return false;
      };

      // Helper: Validate compact toggle interval
      var validateCompactToggleInterval = function () {
        var raw;
        try {
          const ps = getPluginSettings();
          raw = ps ? ps.compact_toggle_interval_seconds() : undefined;
        } catch {
          return localize("Unable to read compact toggle interval setting.");
        }
        return validateIntegerRange(
          raw,
          5,
          60,
          "Compact toggle interval must be an integer between 5 and 60 seconds.",
        );
      };

      // Helper: Validate debug throttle
      var validateDebugThrottle = function () {
        try {
          const ps = getPluginSettings();
          const raw = ps ? ps.debug_throttle_seconds() : undefined;
        } catch {
          return localize("Unable to read debug throttle setting.");
        }
        return validateIntegerRange(
          raw,
          1,
          120,
          "Debug throttle must be an integer between 1 and 120 seconds.",
        );
      };

      // Helper: Validate poll interval
      var validatePollInterval = function () {
        var raw;
        try {
          const ps = getPluginSettings();
          raw = ps ? ps.poll_interval_seconds() : undefined;
        } catch {
          return localize("Unable to read polling interval setting.");
        }
        return validateIntegerRange(
          raw,
          1,
          120,
          "Polling interval must be an integer between 1 and 120 seconds.",
        );
      };

      // Helper: Show error notification
      var showValidationErrors = function (errors) {
        try {
          if (
            typeof window.OctoPrint !== "undefined" &&
            window.OctoPrint.notifications &&
            window.OctoPrint.notifications.error
          ) {
            window.OctoPrint.notifications.error(errors.join("\n"));
          } else {
            alert(errors.join("\n"));
          }
        } catch {
          alert(errors.join("\n"));
        }
        return true;
      };

      settingsVM.save = () => {
        const errors = [];
        const compactToggleError = validateCompactToggleInterval();
        if (compactToggleError) errors.push(compactToggleError);
        const throttleError = validateDebugThrottle();
        if (throttleError) errors.push(throttleError);
        const pollError = validatePollInterval();
        if (pollError) errors.push(pollError);

        if (errors.length) {
          showValidationErrors(errors);
          return Promise.reject(new Error("validation failed"));
        }
        return Promise.resolve(origSave());
      };
    }
  } catch {}
  return this;
};

$(() => {
  window.OCTOPRINT_VIEWMODELS.push([
    NavbarUptimeViewModel,
    ["settingsViewModel"],
    ["#navbar_plugin_navbar_uptime"],
  ]);
  return true;
});
