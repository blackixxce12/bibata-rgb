#!/usr/bin/env bash
# Install Bibata-RGB: build the theme if needed, then install the theme, the border module and
# the rgb-theme switch. Installs the original Bibata-Modern-Ice from vendor/ when the system
# has none (rgb-theme off switches back to it). Switches nothing on; run `rgb-theme on` for that.
set -euo pipefail
here=$(CDPATH='' cd -- "$(dirname -- "$0")" && pwd)
src=$here/build/Bibata-RGB
# libhyprcursor looks in ~/.local/share/icons (not $XDG_DATA_HOME), so install there
icons=$HOME/.local/share/icons
module=${XDG_CONFIG_HOME:-$HOME/.config}/hypr/config/rgb.lua

missing=()
command -v python3 >/dev/null || missing+=(python)
python3 -c 'import gi; gi.require_version("Rsvg", "2.0"); from gi.repository import Rsvg' 2>/dev/null ||
    missing+=(python-gobject librsvg)
python3 -c 'import cairo' 2>/dev/null || missing+=(python-cairo)
command -v hyprcursor-util >/dev/null || missing+=(hyprcursor)

built=""
[[ -f $src/manifest.hl && -f $src/index.theme && -d $src/cursors ]] && built=1
stale=""
if [[ -n $built ]] && [[ $here/generate.py -nt $src/manifest.hl ||
    -n $(find "$here/vendor" -newer "$src/manifest.hl" -print -quit) ]]; then
    stale=1
fi

if [[ -z $built || -n $stale ]]; then
    if ((${#missing[@]})); then
        if [[ -n $built ]]; then
            echo "note: the sources are newer than build/, but the build tools are missing; installing the existing build" >&2
        else
            echo "To build the theme, install: ${missing[*]}" >&2
            echo "  e.g. shelly install standard --needed ${missing[*]}   (or: sudo pacman -S --needed ${missing[*]})" >&2
            echo "Or use the prebuilt theme from the Releases page (see README)." >&2
            exit 1
        fi
    else
        echo "building the theme (a few seconds)..."
        python3 "$here/generate.py" >/dev/null
    fi
fi

mkdir -p "$icons" "$HOME/.local/bin" "$(dirname "$module")"

# the theme rgb-theme off switches back to
have_ice=""
for d in "$icons" "$HOME/.icons" /usr/share/icons; do
    [[ -d $d/Bibata-Modern-Ice ]] && have_ice=$d/Bibata-Modern-Ice
done
if [[ -z $have_ice ]]; then
    cp -a "$here/vendor/Bibata-Modern-Ice" "$icons/"
    echo "installed $icons/Bibata-Modern-Ice (the original, from vendor/)"
fi

rm -rf "$icons/.Bibata-RGB.new"
cp -a "$src" "$icons/.Bibata-RGB.new"
# swap in one step so a running session never sees a missing or half-copied theme
if [[ -d $icons/Bibata-RGB ]] && mv --exchange "$icons/.Bibata-RGB.new" "$icons/Bibata-RGB" 2>/dev/null; then
    rm -rf "$icons/.Bibata-RGB.new"  # now holds the previous version
else
    rm -rf "$icons/.Bibata-RGB.old"
    [[ -d $icons/Bibata-RGB ]] && mv "$icons/Bibata-RGB" "$icons/.Bibata-RGB.old"
    mv "$icons/.Bibata-RGB.new" "$icons/Bibata-RGB"
    rm -rf "$icons/.Bibata-RGB.old"
fi

# border module: keep the SPIN mode chosen with `rgb-theme spin`; other edits made to the
# installed copy are kept in a dated backup (edit hypr/rgb.lua here to make them stick)
spin=""
if [[ -f $module ]]; then
    spin=$(sed -n -E 's/^local SPIN = "([a-z]+)".*/\1/p' "$module" | head -n1)
    if ! cmp -s <(grep -v '^local SPIN = ' "$module") <(grep -v '^local SPIN = ' "$here/hypr/rgb.lua"); then
        bak=$module.bak-$(date +%Y%m%d-%H%M%S)
        cp -a "$module" "$bak"
        echo "note: $module had local edits, saved as $bak" >&2
    fi
fi
# write through a symlink (stow/chezmoi-managed dotfiles) instead of replacing it
if [[ -L $module ]]; then
    cat "$here/hypr/rgb.lua" >"$(readlink -f "$module")"
else
    install -m 644 "$here/hypr/rgb.lua" "$module"
fi
[[ -n $spin ]] && sed -i --follow-symlinks -E "s/^(local SPIN = \")[a-z]+(\".*)/\\1$spin\\2/" "$module"

install -m 755 "$here/rgb-theme" "$HOME/.local/bin/rgb-theme"
echo "installed $icons/Bibata-RGB, $module (spin: ${spin:-loop}) and ~/.local/bin/rgb-theme"
case ":$PATH:" in
    *":$HOME/.local/bin:"*) echo "next: rgb-theme on" ;;
    *) echo "next: ~/.local/bin/rgb-theme on   (~/.local/bin is not in PATH yet; new terminals will have it)" ;;
esac
