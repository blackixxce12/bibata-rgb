#!/usr/bin/env bash
# Install Bibata-RGB: build the theme if needed, then install the theme, the border module and
# the rgb-theme switch. Installs the original Bibata-Modern-Ice from vendor/ when the system
# has none. Switches nothing on; run `rgb-theme on` for that.
#
# usage: ./install.sh [--lite|--full]
#   --lite  XCursor sizes 24-64 px (~54 MB, the default for a first install)
#   --full  XCursor sizes 16-96 px like the original theme (~235 MB)
# Without a flag it keeps the variant that is installed, else uses the one in build/. The
# cursor and border speeds and the spin mode chosen with rgb-theme are kept too.
set -euo pipefail
here=$(CDPATH='' cd -- "$(dirname -- "$0")" && pwd)
src=$here/build/Bibata-RGB
# libhyprcursor looks in ~/.local/share/icons (not $XDG_DATA_HOME), so install there
icons=$HOME/.local/share/icons
installed=$icons/Bibata-RGB
module=${XDG_CONFIG_HOME:-$HOME/.config}/hypr/config/rgb.lua

info_value() { [[ -f $1/BUILD-INFO ]] && sed -n "s/^$2=//p" "$1/BUILD-INFO" | head -n1 || true; }

profile=""
for arg; do
    case $arg in
        --lite) profile=lite ;;
        --full) profile=full ;;
        -h | --help) sed -n '2,/^[^#]/{/^#/s/^# \{0,1\}//p}' "$0"; exit 0 ;;
        *) echo "unknown option $arg (--lite, --full)" >&2; exit 1 ;;
    esac
done
[[ -n $profile ]] || profile=$(info_value "$installed" xcursor)
[[ -n $profile ]] || profile=$(info_value "$src" xcursor)
[[ -n $profile ]] || profile=lite

missing=()
command -v python3 >/dev/null || missing+=(python)
python3 -c 'import gi; gi.require_version("Rsvg", "2.0"); from gi.repository import Rsvg' 2>/dev/null ||
    missing+=(python-gobject librsvg)
python3 -c 'import cairo' 2>/dev/null || missing+=(python-cairo)
command -v hyprcursor-util >/dev/null || missing+=(hyprcursor)

built=""
[[ -f $src/manifest.hl && -f $src/index.theme && -d $src/cursors ]] && built=1
stale=""
if [[ -n $built ]]; then
    if [[ $here/generate.py -nt $src/manifest.hl || -n $(find "$here/vendor" -newer "$src/manifest.hl" -print -quit) ]]; then
        stale="the sources are newer than build/"
    elif [[ $(info_value "$src" xcursor) != "$profile" ]]; then
        stale="build/ has the $(info_value "$src" xcursor || true) XCursor sizes, $profile was asked for"
    fi
fi

if [[ -z $built || -n $stale ]]; then
    if ((${#missing[@]})); then
        if [[ -n $built ]]; then
            echo "note: $stale, but the build tools are missing; installing the existing build" >&2
        else
            echo "To build the theme, install: ${missing[*]}" >&2
            echo "  e.g. shelly install standard --needed ${missing[*]}   (or: sudo pacman -S --needed ${missing[*]})" >&2
            echo "Or use a prebuilt theme from the Releases page (see README)." >&2
            exit 1
        fi
    else
        echo "building the theme ($profile XCursor sizes, a few seconds)..."
        python3 "$here/generate.py" --xcursor "$profile" >/dev/null
    fi
fi

mkdir -p "$icons" "$HOME/.local/bin" "$(dirname "$module")"

# the theme a system without saved state falls back to
have_ice=""
for d in "$icons" "$HOME/.icons" /usr/share/icons; do
    [[ -d $d/Bibata-Modern-Ice ]] && have_ice=$d/Bibata-Modern-Ice
done
if [[ -z $have_ice ]]; then
    cp -a "$here/vendor/Bibata-Modern-Ice" "$icons/"
    echo "installed $icons/Bibata-Modern-Ice (the original, from vendor/)"
fi

# keep the cursor speed chosen with `rgb-theme speed cursor`
old_cycle=$(info_value "$installed" cycle_ms)

rm -rf "$icons/.Bibata-RGB.new"
cp -a "$src" "$icons/.Bibata-RGB.new"
# swap in one step so a running session never sees a missing or half-copied theme
if [[ -d $installed ]] && mv --exchange "$icons/.Bibata-RGB.new" "$installed" 2>/dev/null; then
    rm -rf "$icons/.Bibata-RGB.new"  # now holds the previous version
else
    rm -rf "$icons/.Bibata-RGB.old"
    [[ -d $installed ]] && mv "$installed" "$icons/.Bibata-RGB.old"
    mv "$icons/.Bibata-RGB.new" "$installed"
    rm -rf "$icons/.Bibata-RGB.old"
fi

# border module: keep SPIN and TURN chosen with rgb-theme; other edits made to the installed
# copy are kept in a dated backup (edit hypr/rgb.lua here to make them stick)
module_value() { sed -n -E "s/^local $1 = \"?([^\" ]+)\"?.*/\\1/p" "$module" | head -n1; }
spin="" turn=""
if [[ -f $module ]]; then
    spin=$(module_value SPIN)
    turn=$(module_value TURN)
    # checksums (without the SPIN and TURN lines) of the modules earlier releases installed:
    # replacing one of those is an upgrade, not a loss of local edits
    shipped=" c7e907fafa5d5e085b2199ab43f839ff2fe8471bcec42e25b797ec54a1d09b8a 3ed958781e8e401160437a1b9d3b79d186a8da48acfa872669128702d732172b "
    current=$(grep -vE '^local (SPIN|TURN) = ' "$module" | sha256sum | cut -d' ' -f1)
    if [[ $shipped != *" $current "* ]] &&
        ! cmp -s <(grep -vE '^local (SPIN|TURN) = ' "$module") <(grep -vE '^local (SPIN|TURN) = ' "$here/hypr/rgb.lua"); then
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
if [[ $spin =~ ^[a-z]+$ ]]; then
    sed -i --follow-symlinks -E "s/^(local SPIN = \")[a-z]+(\".*)/\\1$spin\\2/" "$module"
fi
if [[ $turn =~ ^[0-9.]+$ ]]; then
    sed -i --follow-symlinks -E "s/^(local TURN = )[0-9.]+/\\1$turn/" "$module"
fi

install -m 755 "$here/rgb-theme" "$HOME/.local/bin/rgb-theme"

# a build made with its own --cycle-ms keeps that; a default build gets the installed speed
new_cycle=$(info_value "$installed" cycle_ms)
if [[ $old_cycle =~ ^[0-9]+$ && $new_cycle == 2160 && $old_cycle != "$new_cycle" ]]; then
    "$HOME/.local/bin/rgb-theme" speed cursor "$(awk -v ms="$old_cycle" 'BEGIN { printf "%g", ms / 1000 }')" --no-reload >/dev/null ||
        echo "note: could not keep the cursor speed ($old_cycle ms); set it again with rgb-theme speed cursor" >&2
fi

variant=$(info_value "$installed" xcursor)
[[ -z $variant || $variant == "$profile" ]] || echo "note: installed the $variant XCursor sizes from build/, not $profile" >&2
echo "installed $installed (${variant:-?} XCursor sizes, $("$HOME/.local/bin/rgb-theme" speed | head -n1 | sed 's/^cursor: *//')),"
echo "  $module (spin: $(module_value SPIN), $(module_value TURN) s per turn) and ~/.local/bin/rgb-theme"
case ":$PATH:" in
    *":$HOME/.local/bin:"*) echo "next: rgb-theme on" ;;
    *) echo "next: ~/.local/bin/rgb-theme on   (~/.local/bin is not in PATH yet; new terminals will have it)" ;;
esac
echo "(if the RGB cursor is already on, rgb-theme on reloads it)"
