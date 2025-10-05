# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

"""Zoom plugin skips breaks while Zoom is running.

Simplified Wayland-friendly approach:
- Just checks if a Zoom process exists (zoom/Zoom/zoom-real or Flatpak com.zoom.Zoom).
"""

import logging
import os
import re
import subprocess

context = None

# Exact names commonly used by Zoom binaries
_ZOOM_NAMES = {"zoom", "Zoom", "zoom-real"}

# Patterns to catch Flatpak/Snap or wrapper invocations
_ZOOM_CMDLINE_PATTERNS = (
    r"\bcom\.zoom\.Zoom\b",  # Flatpak app ID
    r"(^|/)(zoom|zoom-real)(\s|$)",  # direct path to zoom binary
)


def _zoom_process_running():
    """
    Returns True if a Zoom process appears to be running, based on:
    - pgrep exact-name matches (zoom/Zoom/zoom-real)
    - pgrep -f for 'com.zoom.Zoom' (Flatpak)
    - /proc scan fallback for name/cmdline
    """
    # Try pgrep first if available (procps)
    for args in (
        ["pgrep", "-x", "zoom"],
        ["pgrep", "-x", "Zoom"],
        ["pgrep", "-x", "zoom-real"],
        ["pgrep", "-f", "com.zoom.Zoom"],
    ):
        try:
            subprocess.check_output(args)
            logging.debug("Detected Zoom via pgrep: %r", args)
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            pass

    # Fallback: scan /proc
    patterns = [re.compile(p) for p in _ZOOM_CMDLINE_PATTERNS]
    try:
        for pid in os.listdir("/proc"):
            if not pid.isdigit():
                continue
            proc_dir = os.path.join("/proc", pid)

            # Check /proc/<pid>/comm for exact binary name
            try:
                with open(os.path.join(proc_dir, "comm"), "r", encoding="utf-8", errors="ignore") as f:
                    comm = f.read().strip()
                if comm in _ZOOM_NAMES:
                    logging.debug("Detected Zoom via /proc/%s/comm = %s", pid, comm)
                    return True
            except Exception:
                # Process may have exited or permission denied
                pass

            # Check cmdline for Flatpak or path to zoom binary
            try:
                with open(os.path.join(proc_dir, "cmdline"), "rb") as f:
                    raw = f.read()
                cmdline = raw.decode("utf-8", errors="ignore").replace("\x00", " ")
                for pat in patterns:
                    if pat.search(cmdline):
                        logging.debug("Detected Zoom via /proc/%s/cmdline = %r", pid, cmdline)
                        return True
            except Exception:
                pass
    except Exception:
        logging.exception("Failed scanning /proc for Zoom")

    return False


def in_zoom_meeting():
    # In this simplified plugin, treat "Zoom process is running" as "in meeting"
    return _zoom_process_running()


def init(ctx, safeeyes_config, plugin_config):
    global context
    logging.debug("Initialize Zoom plugin (process-based)")
    context = ctx
    # Best-effort reordering so 'zoom' runs before notifications; safe-guarded.
    try:
        api = ctx.get("api", {}) if isinstance(ctx, dict) else {}
        show_about = api.get("show_about") if isinstance(api, dict) else None

        if not callable(show_about):
            logging.debug("show_about API not callable; skipping plugin reordering")
            return

        closure = getattr(show_about, "__closure__", None)
        if not closure:
            logging.debug("show_about has no closure; skipping plugin reordering")
            return

        safeeyes = closure[0].cell_contents
        on_pre_break = getattr(
            safeeyes.plugins_manager, "_PluginManager__plugins_on_pre_break", None
        )
        if isinstance(on_pre_break, list):
            for i, plugin in enumerate(on_pre_break):
                if isinstance(plugin, dict) and plugin.get("id") == "zoom":
                    on_pre_break.insert(0, on_pre_break.pop(i))
                    break
            logging.debug(
                "on_pre_break plugin order: %r",
                [i.get("id") for i in on_pre_break if isinstance(i, dict)],
            )
        else:
            logging.debug("plugins_on_pre_break not accessible; skipping reordering")
    except Exception:
        logging.exception("Error updating the order of on_pre_break plugins")


def on_pre_break(break_obj):
    return in_zoom_meeting()


def on_start_break(break_obj):
    return in_zoom_meeting()
