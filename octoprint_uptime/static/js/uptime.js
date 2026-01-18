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

  // Settings ViewModel for plugin settings panel
  function UptimeSettingsViewModel(parameters) {
    var self = this;

    // Keep reference to OctoPrint's settingsViewModel wrapper
    self.settingsViewModel = parameters[0];

    // Resolve to the real settings object (handles different OctoPrint versions)
    self._resolveSettingsRoot = function () {
      var s = null;
      try {
        s = self.settingsViewModel && self.settingsViewModel.settings;
        if (typeof s === "function") {
          s = s();
        }
      } catch (e) {
        s = null;
      }

      if (s && s.plugins) {
        return s;
      }
      if (s && s.settings && s.settings.plugins) {
        return s.settings;
      }
      return {};
    };

    // Expose settings so template data-bind="settings.plugins.octoprint_uptime..." works
    self.settings = self._resolveSettingsRoot();

    // No fallback save helper; rely on OctoPrint settings flow (as in example project)

    self._getSettingsDialogRoot = function () {
      var $root = $("#settings_plugin_octoprint_uptime");
      if (!$root.length) {
        $root = $(".section");
      }
      return $root.length ? $root : null;
    };

    self._bindSettingsIfNeeded = function () {
      // Refresh reference to settings root before attempting to bind
      self.settings = self._resolveSettingsRoot();

      // Only attempt to bind once the Settings object from OctoPrint has
      // loaded and contains the plugin entry we expect. If not yet present
      // bail out and let the retry logic kick in.
      if (
        !self.settings ||
        !self.settings.plugins ||
        !self.settings.plugins.octoprint_uptime
      ) {
        return;
      }

      var $root = self._getSettingsDialogRoot();
      if (!$root) {
        return;
      }
      var rootEl = $root.get(0);
      if ($(rootEl).data("uptimeKoBound")) {
        return;
      }
      try {
        ko.applyBindings(self, rootEl);
        $(rootEl).data("uptimeKoBound", true);
        // Notify backend for debug: indicate bindings were applied
        try {
          if (window.OctoPrint && OctoPrint.simpleApiCommand) {
            OctoPrint.simpleApiCommand("octoprint_uptime", "bound", {}).always(
              function () {},
            );
          }
        } catch (e) {}

        // No fallback save UI inserted; use OctoPrint's native settings save behavior (as in the example project)
      } catch (e) {
        // Ignore - binding may be retried
      }
    };

    self._unbindSettingsIfBound = function () {
      var $root = self._getSettingsDialogRoot();
      if (!$root) {
        return;
      }
      var rootEl = $root.get(0);
      if (!$(rootEl).data("uptimeKoBound")) {
        return;
      }
      try {
        ko.cleanNode(rootEl);
      } catch (e) {}
      $(rootEl).removeData("uptimeKoBound");
    };

    self._bindSettingsWithRetry = function () {
      var start = Date.now();
      var timeoutMs = 10000; // total time to keep trying (ms)
      var delayMs = 200; // poll interval
      var tick = function () {
        self._bindSettingsIfNeeded();
        var $root = self._getSettingsDialogRoot();
        if ($root && $root.data && $root.data("uptimeKoBound")) {
          return;
        }
        if (Date.now() - start < timeoutMs) {
          window.setTimeout(tick, delayMs);
        } else {
          // Final attempt/time out; send a non-blocking diagnostic ping so
          // backend logs can capture that we failed to bind in time.
          try {
            if (window.OctoPrint && OctoPrint.simpleApiCommand) {
              OctoPrint.simpleApiCommand("octoprint_uptime", "bound", {
                timeout: true,
              }).always(function () {});
            }
          } catch (e) {}
        }
      };
      tick();
    };

    self._installSettingsDialogHooks = function () {
      if (self._settingsDialogHooksInstalled) {
        return;
      }
      self._settingsDialogHooksInstalled = true;

      $(document).on("shown", "#settings_dialog", function () {
        self._bindSettingsWithRetry();
      });
      $(document).on("shown.bs.modal", "#settings_dialog", function () {
        self._bindSettingsWithRetry();
      });

      $(document).on("hidden", "#settings_dialog", function () {
        self._unbindSettingsIfBound();
      });
      $(document).on("hidden.bs.modal", "#settings_dialog", function () {
        self._unbindSettingsIfBound();
      });
    };

    // Hooks called by OctoPrint's settings dialog lifecycle
    self.onSettingsShown = function () {
      self._bindSettingsWithRetry();
    };

    self.onSettingsBeforeSave = function () {
      // Refresh cached reference to settings before save
      self.settings = self._resolveSettingsRoot();

      // Send a lightweight debug payload to the backend so we can verify
      // what values the frontend is about to save. This is non-blocking
      // and temporary (will be removed once debugging is complete).
      try {
        if (window.OctoPrint && OctoPrint.simpleApiCommand) {
          var payload = null;
          try {
            // Prefer a KO -> plain JS conversion when available
            payload = ko.toJS(self.settings.plugins.octoprint_uptime);
          } catch (e) {
            // Fallback: construct a minimal payload safely
            payload = {
              debug: !!(
                self.settings &&
                self.settings.plugins &&
                self.settings.plugins.octoprint_uptime &&
                (typeof self.settings.plugins.octoprint_uptime.debug ===
                "function"
                  ? self.settings.plugins.octoprint_uptime.debug()
                  : self.settings.plugins.octoprint_uptime.debug)
              ),
              navbar_enabled: !!(
                self.settings &&
                self.settings.plugins &&
                self.settings.plugins.octoprint_uptime &&
                (typeof self.settings.plugins.octoprint_uptime
                  .navbar_enabled === "function"
                  ? self.settings.plugins.octoprint_uptime.navbar_enabled()
                  : self.settings.plugins.octoprint_uptime.navbar_enabled)
              ),
              display_format:
                (self.settings &&
                  self.settings.plugins &&
                  self.settings.plugins.octoprint_uptime &&
                  (typeof self.settings.plugins.octoprint_uptime
                    .display_format === "function"
                    ? self.settings.plugins.octoprint_uptime.display_format()
                    : self.settings.plugins.octoprint_uptime.display_format)) ||
                "full",
              debug_throttle_seconds: parseInt(
                (self.settings &&
                  self.settings.plugins &&
                  self.settings.plugins.octoprint_uptime &&
                  (typeof self.settings.plugins.octoprint_uptime
                    .debug_throttle_seconds === "function"
                    ? self.settings.plugins.octoprint_uptime.debug_throttle_seconds()
                    : self.settings.plugins.octoprint_uptime
                        .debug_throttle_seconds)) ||
                  60,
                10,
              ),
            };
          }

          OctoPrint.simpleApiCommand(
            "octoprint_uptime",
            "saveAttempt",
            payload,
          ).always(function () {});
        }
      } catch (e) {}
      // Return true to allow save to proceed (no blocking validation here)
      return true;
    };

    self.onSettingsHidden = function () {
      self._unbindSettingsIfBound();
    };

    // Ensure we install hooks once when the viewmodel is initialized
    self._installSettingsDialogHooks();

    // No extra client debug pings or save interception; rely on OctoPrint's
    // native settings dialog save flow (as in the working example).

    // Removed fallback 'Save (force)' click handler per user's request — rely on OctoPrint's native settings save flow.
  }

  OCTOPRINT_VIEWMODELS.push([
    NavbarUptimeViewModel,
    ["settingsViewModel"],
    ["#navbar_plugin_navbar_uptime"],
  ]);

  // Ensure the settings VM is constructed early by also attaching it to the navbar element
  OCTOPRINT_VIEWMODELS.push([
    UptimeSettingsViewModel,
    ["settingsViewModel"],
    ["#settings_plugin_octoprint_uptime"],
  ]);
});
