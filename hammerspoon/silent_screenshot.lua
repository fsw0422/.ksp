-- Silent screenshot: ⌃⌘S saves the whole screen to ~/OneDrive, with no shutter sound.
-- Replaces the "Silent screenshot" shortcut from the Shortcuts app.

local folder = os.getenv("HOME") .. "/OneDrive"
local task -- keeps the running capture alive until it finishes

local function onDone(exitCode, _, stdErr)
  if exitCode ~= 0 then
    hs.alert.show("Silent screenshot failed (exit " .. exitCode .. ")\n" .. stdErr)
  end
end

local function take()
  -- Same name as macOS uses, e.g. "Screenshot 2026-11-18 at 01.44.35.png"
  local path = folder .. os.date("/Screenshot %Y-%m-%d at %H.%M.%S.png")
  -- -x: no sound. With one file name, it captures the main display only.
  task = hs.task.new("/usr/sbin/screencapture", onDone, { "-x", path })
  task:start()
end

-- screencapture runs on Hammerspoon's behalf, so Hammerspoon needs Screen Recording access.
-- This asks for it once, while it's missing.
hs.screenRecordingState(true)

hs.hotkey.bind({ "ctrl", "cmd" }, "s", take)

return { take = take }
