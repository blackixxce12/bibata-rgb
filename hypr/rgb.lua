-- RGB look: rainbow window borders.
-- `rgb-theme on|off borders` adds/removes the line require("config.rgb") in hyprland.lua;
-- decorations.lua keeps the original colours. `rgb-theme spin loop|focus|off` sets SPIN,
-- `rgb-theme speed borders <seconds>` sets TURN.

-- How the rainbow moves:
--   "loop"   turns all the time, one turn every TURN seconds. While a turning border is visible,
--            Hyprland redraws the screen at its refresh rate (e.g. 165 Hz) instead of idling, and
--            its animation timer wakes ~1000 times a second (measured ~4-6 % of a CPU core).
--            Windows opened while the borders did not move (borders off, or spin off) keep
--            turning only after they are reopened; until then they turn once per focus change.
--   "focus"  turns once whenever a window gets focus, then rests (no constant redraw).
--   "off"    stands still.
local SPIN = "loop"
-- Seconds for one full turn in "loop" mode (0.3-10; Hyprland caps the speed at 10 s)
local TURN = 5

local RAINBOW = {
    "rgba(ff1744ff)", "rgba(ff9100ff)", "rgba(ffea00ff)", "rgba(00e676ff)",
    "rgba(00e5ffff)", "rgba(2979ffff)", "rgba(d500f9ff)", "rgba(ff1744ff)",
}
-- Locked groups get a warm-only rainbow so they stay recognisable
local WARM = { "rgba(ff1744ff)", "rgba(ff9100ff)", "rgba(ffea00ff)", "rgba(ff9100ff)", "rgba(ff1744ff)" }

-- The same colours with a different alpha, e.g. faded for unfocused windows
local function with_alpha(colors, alpha)
    local out = {}
    for i, c in ipairs(colors) do
        out[i] = c:gsub("%x%x%)$", alpha .. ")")
    end
    return out
end

hl.config({
    general = {
        col = {
            active_border = { colors = RAINBOW, angle = 45 },
            inactive_border = { colors = with_alpha(RAINBOW, "66"), angle = 45 },
        },
    },
    group = {
        col = {
            border_active = { colors = RAINBOW, angle = 45 },
            border_inactive = { colors = with_alpha(RAINBOW, "66"), angle = 45 },
            border_locked_active = { colors = WARM, angle = 45 },
            border_locked_inactive = { colors = with_alpha(WARM, "66"), angle = 45 },
        },
        -- Hyprland draws the group tab indicators in one colour (the first of a gradient)
        groupbar = {
            col = {
                active = "rgba(d500f9ff)",
                inactive = "rgba(9e9e9e66)",
                locked_active = "rgba(ff9100ff)",
                locked_inactive = "rgba(ff910066)",
            },
        },
    },
})

-- speed is in 100 ms units: 50 = one turn in 5 s
if SPIN == "loop" then
    hl.animation({ leaf = "borderangle", enabled = true, speed = TURN * 10, bezier = "linear", style = "loop" })
elseif SPIN == "focus" then
    hl.animation({ leaf = "borderangle", enabled = true, speed = 15, bezier = "easeInOutCubic", style = "once" })
end
