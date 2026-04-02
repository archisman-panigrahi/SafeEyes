# Safe Eyes Feature TODO

This document captures product and engineering ideas based on a read-through of the current Safe Eyes codebase, especially the scheduler, break model, GTK UI, tray integration, and bundled plugins.

## Context

Safe Eyes already has a strong foundation:

- A central scheduler and state machine in `safeeyes/core.py`
- A break queue and break model in `safeeyes/model.py`
- A plugin lifecycle with hooks for pre-break, start-break, stop-break, countdown, and next-break updates in `safeeyes/plugin_manager.py`
- A configurable GTK settings flow in `safeeyes/ui/settings_dialog.py`
- A fullscreen break UI in `safeeyes/ui/break_screen.py`
- Existing plugins for notifications, smart pause, tray control, screensaver lock, media pause, and health statistics

Because of that architecture, the highest-value new features are likely to be additive and configurable rather than a full redesign.

## Highest-Leverage Ideas

### 1. Profile-Based Schedules

Allow users to define multiple named Safe Eyes profiles and switch between them quickly.

Examples:

- Workday
- Deep Work
- Reading
- Coding
- Gaming

Why it fits:

- Safe Eyes currently uses a single global config model.
- The tray plugin already exposes user actions and is a natural place for fast profile switching.
- The settings dialog already edits a rich config object, so profile support can build on that rather than replacing it.

Possible scope:

- Store multiple profiles in config
- Let users choose a default startup profile
- Add tray menu actions to switch profiles
- Show current profile in tray tooltip or status text
- Optionally support temporary profile switching for a set duration

Implementation notes:

- Likely touches `safeeyes/configuration.py`, `safeeyes/ui/settings_dialog.py`, `safeeyes/plugins/trayicon/plugin.py`, and restart logic in `safeeyes/safeeyes.py`

### 2. Guided Break Routines

Turn a break from a single message into a sequence of timed steps.

Examples:

- Look at a distant object for 10 seconds
- Blink slowly for 5 seconds
- Roll shoulders for 10 seconds
- Relax jaw and neck for 10 seconds
- Drink water

Why it fits:

- Current breaks already have names, durations, optional images, and plugin overrides.
- The break screen already updates every second and can display plugin-generated content.
- This would make breaks feel more purposeful and effective without changing the core schedule logic.

Possible scope:

- Add optional step lists to break definitions
- Show one step at a time during countdown
- Support text-only or image-backed steps
- Add preset routines users can choose from
- Let break packs include routines

Implementation notes:

- Likely touches `safeeyes/model.py`, `safeeyes/ui/break_screen.py`, `safeeyes/ui/settings_dialog.py`, and default config in `safeeyes/config/safeeyes.json`

### 3. Better Health Dashboard

Expand the existing health statistics into a dedicated user-facing dashboard.

Examples:

- Daily break count
- Skip rate
- Estimated screen time
- Weekly trends
- Streaks for compliant days
- “You skipped more breaks this week than last week”

Why it fits:

- The `healthstats` plugin already tracks useful session and aggregate metrics.
- Right now the information only appears as break-screen text, which hides its value.
- A dashboard would turn Safe Eyes from a reminder app into a habit-building tool.

Possible scope:

- Add a stats window accessible from tray and settings
- Show daily and weekly summaries
- Add streaks and rolling averages
- Surface “best day” and “high skip day” indicators
- Add export to JSON or CSV

Implementation notes:

- Likely touches `safeeyes/plugins/healthstats/plugin.py`, `safeeyes/ui/settings_dialog.py`, and a new dedicated stats window under `safeeyes/ui/`

## Additional Product Ideas

### 4. Time-of-Day and Day-of-Week Rules

Support schedules that change based on time and calendar patterns.

Examples:

- Softer break schedule in the morning
- Stricter afternoons
- Disable on weekends
- Lunchtime pause window

Why it matters:

- Current scheduling is static.
- Many users have different energy levels and workflows throughout the day.

Possible scope:

- Different short/long intervals by time range
- Day-specific enable/disable rules
- “Only run during working hours” mode

Implementation notes:

- This mostly belongs in the scheduler/config layers, especially `safeeyes/core.py`, `safeeyes/model.py`, and `safeeyes/configuration.py`

### 5. Adaptive Strictness

Make Safe Eyes respond to actual user behavior instead of applying one fixed enforcement level.

Examples:

- Increase warning time after repeated skips
- Temporarily disable postpone after too many postpones
- Schedule a longer recovery break after excessive avoidance
- Relax enforcement after a strong compliance streak

Why it matters:

- The existing consecutive skip limiting plugin already points in this direction.
- Adaptive behavior can feel more helpful than static strict mode.

Possible scope:

- Use recent skip/postpone history from session state
- Add configurable escalation policies
- Show a clear explanation when rules tighten

Implementation notes:

- Builds naturally on `safeeyes/plugins/limitconsecutiveskipping/plugin.py` and persisted session state

### 6. Quiet Hours and Meeting Mode

Allow Safe Eyes to automatically reduce interruptions during known focus or meeting periods.

Examples:

- Do not force breaks during scheduled meetings
- Light notifications only during focus hours
- Resume full behavior after the event ends

Why it matters:

- Current do-not-disturb handling is mostly based on fullscreen windows and battery state.
- Many real interruptions come from meetings, calls, and deliberate focus sessions rather than fullscreen apps.

Possible scope:

- Manual focus mode toggle
- Scheduled quiet hours
- Calendar-aware plugin
- “Soft break only” during meeting windows

Implementation notes:

- Could start as a new plugin using the existing break interception hooks in `safeeyes/plugin_manager.py`

### 7. Soft Break Mode

Offer a less disruptive alternative to the fullscreen break screen.

Examples:

- Top banner
- Corner timer
- Screen dimming overlay
- Small floating reminder with countdown

Why it matters:

- Full interruption is effective for some users and frustrating for others.
- A softer mode would broaden the app’s appeal without replacing strict mode.

Possible scope:

- Per-profile or per-break presentation mode
- “Soft short breaks, strict long breaks”
- Automatic fallback for unsupported desktops

Implementation notes:

- Most likely centered in `safeeyes/ui/break_screen.py` with config support and possibly a plugin hook

### 8. Custom Break Packs

Make it easier to install, import, export, and share sets of break content.

Examples:

- Eye strain pack
- RSI relief pack
- Stretching pack
- Standing desk pack
- Hydration pack

Why it matters:

- The settings UI already supports custom breaks.
- Packaging them cleanly would help non-technical users get value faster.

Possible scope:

- Import/export break packs as JSON
- Include optional images and routine steps
- Bundle a few curated packs by default

Implementation notes:

- Likely touches `safeeyes/ui/settings_dialog.py`, `safeeyes/model.py`, and config import/export helpers

### 9. Better Plugin Discoverability

Make plugins easier to understand, troubleshoot, and adopt.

Examples:

- Explain what each plugin does
- Show supported environments
- Explain missing dependencies in friendlier language
- Offer suggestions when a plugin is unavailable

Why it matters:

- The plugin system is powerful but somewhat hidden.
- Users can hit platform-specific limitations, especially around tray and idle detection.

Possible scope:

- Richer plugin details pane
- Dependency explanations with links
- Compatibility labels like X11, Wayland, GNOME, KDE, Sway
- “Recommended plugins” section

Implementation notes:

- Mostly centered in `safeeyes/ui/settings_dialog.py`, `safeeyes/utility.py`, and plugin metadata in each `config.json`

### 10. Automatic Break Actions

Extend the current “pause media” and “lock screen” ideas into a broader automation layer.

Examples:

- Pause media automatically at break start
- Restore media after break
- Mute notifications during breaks
- Launch a stretch video or breathing exercise
- Trigger desktop integrations like night light or focus mode

Why it matters:

- The existing plugins already prove that action-oriented break tooling works well.
- Users often want Safe Eyes to shape the environment around the break, not just show a reminder.

Possible scope:

- Pre-break actions
- Start-break actions
- End-break actions
- Tray actions during break

Implementation notes:

- Could be split into small focused plugins rather than one large automation system

## Engineering-Friendly “Quick Wins”

These seem especially compatible with the current architecture and likely lower-risk than the larger ideas above.

### 11. Tray-Switchable Temporary Modes

Let users quickly choose short-lived behavior changes from the tray menu.

Examples:

- Focus mode for 30 minutes
- Soft mode for 1 hour
- Aggressive mode until lunch

Why it fits:

- The tray plugin already supports temporary disable timers and nested menu actions.
- This is a natural extension of existing tray UX.

### 12. More Visible Stats in Tray Tooltip

Surface small useful metrics without building a full dashboard first.

Examples:

- Today: 6 breaks, 1 skipped
- Compliance streak: 4 days
- Screen time today: 5h 40m

Why it fits:

- The tray plugin already updates tooltip text and label text.
- Good intermediate step before a full stats window.

### 13. Preset Break Templates in Settings

When creating a new break, offer templates instead of starting from an empty text field.

Examples:

- Eye reset
- Stretch
- Hydrate
- Walk

Why it fits:

- The current break creation flow is already there.
- Improves usability without deep scheduler changes.

### 14. Per-Break Presentation Options

Let each break choose how it should look and behave.

Examples:

- Strict fullscreen
- Soft reminder
- Image-heavy mode
- Text-only minimal mode

Why it fits:

- Breaks already support per-break plugin overrides.
- Extending break config with presentation metadata would be consistent with the current model.

### 15. Better Defaults for Health Stats

Promote the health statistics plugin from a hidden optional extra into a first-class feature.

Possible steps:

- Enable it by default
- Show its value in the README and settings UI
- Improve the widget copy and formatting

Why it fits:

- The plugin already exists and persists useful data.

## Longer-Term Ideas

### 16. Calendar-Aware Scheduling

Shift or soften breaks automatically around active meetings or busy times.

This is stronger than simple quiet hours because it reacts to live calendar state rather than fixed rules.

### 17. Team or Shared Wellness Modes

Potentially support shared break rhythms for teams or families.

Examples:

- Shared “break now” signals
- Team wellness prompts
- Quiet office mode

This is more speculative and likely outside the current single-user architecture, but it could become a distinguishing feature.

### 18. Accessibility and Comfort Modes

Add more user comfort options for how breaks are presented.

Examples:

- Reduced motion
- High contrast
- Large text mode
- Screen reader friendly break content
- Gentler sound options

This would improve inclusivity and fits the GTK UI well.

## Suggested Prioritization

### Quick wins

- Preset break templates
- Better plugin discoverability
- More visible stats in tray tooltip
- Tray-switchable temporary modes

### Medium features

- Profile-based schedules
- Guided break routines
- Soft break mode
- Automatic break actions

### Big bets

- Better health dashboard
- Time-of-day and day-of-week rules
- Adaptive strictness
- Calendar-aware scheduling

## Suggested First Build Order

If starting implementation soon, this order looks practical:

1. Profile-based schedules
2. Preset break templates
3. Better plugin discoverability
4. Guided break routines
5. Better health dashboard

This sequence builds user-visible value early while reusing the existing configuration and plugin architecture.
