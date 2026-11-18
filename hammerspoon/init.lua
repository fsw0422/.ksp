-- Hammerspoon config. ~/.hammerspoon links to this folder (~/.ksp/hammerspoon).
-- Each feature is its own module.

-- Start at login, so the hotkeys keep working after a restart.
hs.autoLaunch(true)

require("silent_screenshot")
