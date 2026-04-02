# Safe Eyes is a utility to remind you to take break frequently
# to protect your eyes from eye strain.

# Copyright (C) 2016  Gobinath

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

import math
import os
import typing

import gi
from safeeyes import utility
from safeeyes.configuration import Config
from safeeyes.model import PluginDependency
from safeeyes.translations import translate as _

gi.require_version("Gtk", "4.0")
from gi.repository import Gtk, Gio
from gi.repository import GdkPixbuf


SETTINGS_DIALOG_GLADE = os.path.join(
    utility.BIN_DIRECTORY, "glade/settings_dialog.glade"
)
SETTINGS_DIALOG_PLUGIN_GLADE = os.path.join(
    utility.BIN_DIRECTORY, "glade/settings_plugin.glade"
)
SETTINGS_DIALOG_BREAK_GLADE = os.path.join(
    utility.BIN_DIRECTORY, "glade/settings_break.glade"
)
SETTINGS_DIALOG_NEW_BREAK_GLADE = os.path.join(
    utility.BIN_DIRECTORY, "glade/new_break.glade"
)
SETTINGS_BREAK_ITEM_GLADE = os.path.join(
    utility.BIN_DIRECTORY, "glade/item_break.glade"
)
SETTINGS_PLUGIN_ITEM_GLADE = os.path.join(
    utility.BIN_DIRECTORY, "glade/item_plugin.glade"
)
SETTINGS_ITEM_INT_GLADE = os.path.join(utility.BIN_DIRECTORY, "glade/item_int.glade")
SETTINGS_ITEM_TEXT_GLADE = os.path.join(utility.BIN_DIRECTORY, "glade/item_text.glade")
SETTINGS_ITEM_BOOL_GLADE = os.path.join(utility.BIN_DIRECTORY, "glade/item_bool.glade")

BREAK_SETTINGS_SEARCH_TERMS = [
    _("Break Settings"),
    _("Break"),
    _("Type"),
    _("Image"),
    _("Time to wait"),
    _("Override"),
    _("Time (in minutes)"),
    _("Duration"),
    _("Time (in seconds)"),
    _("Plugins"),
]
SEARCHABLE_PLUGIN_SETTING_TYPES = {"INT", "TEXT", "BOOL"}


@Gtk.Template(filename=SETTINGS_DIALOG_GLADE)
class SettingsDialog(Gtk.ApplicationWindow):
    """Create and initialize SettingsDialog instance."""

    __gtype_name__ = "SettingsDialog"

    stack: Gtk.Stack = Gtk.Template.Child()
    search_bar: Gtk.SearchBar = Gtk.Template.Child()
    search_entry: Gtk.SearchEntry = Gtk.Template.Child()
    scrolledwindow_settings: Gtk.ScrolledWindow = Gtk.Template.Child()
    frame_short_breaks: Gtk.Frame = Gtk.Template.Child()
    frame_long_breaks: Gtk.Frame = Gtk.Template.Child()
    frame_options: Gtk.Frame = Gtk.Template.Child()
    box7: Gtk.Box = Gtk.Template.Child()
    box2: Gtk.Box = Gtk.Template.Child()
    box8: Gtk.Box = Gtk.Template.Child()
    box3: Gtk.Box = Gtk.Template.Child()
    box6: Gtk.Box = Gtk.Template.Child()
    box16_random_order: Gtk.Box = Gtk.Template.Child()
    box9: Gtk.Box = Gtk.Template.Child()
    box11: Gtk.Box = Gtk.Template.Child()
    box10: Gtk.Box = Gtk.Template.Child()
    box5: Gtk.Box = Gtk.Template.Child()
    box1: Gtk.Box = Gtk.Template.Child()
    expander_short_breaks: Gtk.Expander = Gtk.Template.Child()
    expander_long_breaks: Gtk.Expander = Gtk.Template.Child()
    separator_breaks: Gtk.Separator = Gtk.Template.Child()
    box_break: Gtk.Box = Gtk.Template.Child()
    box_short_breaks: Gtk.Box = Gtk.Template.Child()
    box_long_breaks: Gtk.Box = Gtk.Template.Child()
    scrolledwindow_plugins: Gtk.ScrolledWindow = Gtk.Template.Child()
    box_plugins: Gtk.Box = Gtk.Template.Child()
    popover: Gtk.MenuButton = Gtk.Template.Child()

    spin_short_break_duration: Gtk.SpinButton = Gtk.Template.Child()
    spin_long_break_duration: Gtk.SpinButton = Gtk.Template.Child()
    spin_short_break_interval: Gtk.SpinButton = Gtk.Template.Child()
    spin_long_break_interval: Gtk.SpinButton = Gtk.Template.Child()
    spin_time_to_prepare: Gtk.SpinButton = Gtk.Template.Child()
    spin_postpone_duration: Gtk.SpinButton = Gtk.Template.Child()
    dropdown_postpone_unit: Gtk.DropDown = Gtk.Template.Child()
    spin_disable_keyboard_shortcut: Gtk.SpinButton = Gtk.Template.Child()
    switch_strict_break: Gtk.Switch = Gtk.Template.Child()
    switch_random_order: Gtk.Switch = Gtk.Template.Child()
    switch_postpone: Gtk.Switch = Gtk.Template.Child()
    switch_persist: Gtk.Switch = Gtk.Template.Child()
    info_bar_long_break: Gtk.InfoBar = Gtk.Template.Child()

    plugin_items: dict[str, "PluginItem"]
    plugin_map: dict[str, str]
    settings_search_sections: list[
        tuple[Gtk.Frame, str, list[tuple[Gtk.Widget, str]]]
    ]
    stack_pages: dict[str, Gtk.Widget]
    config: Config

    def __init__(
        self,
        application: Gtk.Application,
        config: Config,
        on_save_settings: typing.Callable[[Config], None],
    ):
        super().__init__(application=application)

        self.config = config
        self.on_save_settings = on_save_settings
        self.plugin_items = {}
        self.plugin_map = {}
        self.settings_search_sections = []
        self.stack_pages = {
            "Settings": self.scrolledwindow_settings,
            "Breaks": self.box_break,
            "Plugins": self.scrolledwindow_plugins,
        }
        self.last_short_break_interval = config.get("short_break_interval")
        self.initializing = True
        self.infobar_long_break_shown = False

        self.info_bar_long_break.hide()
        self.search_bar.connect_entry(self.search_entry)
        self.search_bar.set_key_capture_widget(self)
        self.search_bar.connect(
            "notify::search-mode-enabled", self.__on_search_mode_changed
        )

        # Set the current values of input fields
        self.__initialize(config)

        self.initializing = False

    def __initialize(self, config: Config) -> None:
        # Don't show infobar for changes made internally
        self.infobar_long_break_shown = True
        self.plugin_items = {}
        plugin_configs = utility.load_plugins_config(config)
        self.plugin_map = {
            plugin_config["id"]: plugin_config["meta"]["name"]
            for plugin_config in plugin_configs
            if plugin_config.get("break_override_allowed", False)
        }
        for short_break in config.get("short_breaks"):
            self.__create_break_item(short_break, True)
        for long_break in config.get("long_breaks"):
            self.__create_break_item(long_break, False)

        for plugin_config in plugin_configs:
            self.box_plugins.append(self.__create_plugin_item(plugin_config))

        self.spin_short_break_duration.set_value(config.get("short_break_duration"))
        self.spin_long_break_duration.set_value(config.get("long_break_duration"))
        self.spin_short_break_interval.set_value(config.get("short_break_interval"))
        self.spin_long_break_interval.set_value(config.get("long_break_interval"))
        self.spin_time_to_prepare.set_value(config.get("pre_break_warning_time"))
        self.spin_postpone_duration.set_value(config.get("postpone_duration"))
        # Set the active item in the dropdown based on the postpone unit
        if config.get("postpone_unit") == "seconds":
            self.dropdown_postpone_unit.set_selected(1)
        else:
            self.dropdown_postpone_unit.set_selected(0)
        self.spin_disable_keyboard_shortcut.set_value(
            config.get("shortcut_disable_time")
        )
        self.switch_strict_break.set_active(config.get("strict_break"))
        self.switch_random_order.set_active(config.get("random_order"))
        self.switch_postpone.set_active(config.get("allow_postpone"))
        self.switch_persist.set_active(config.get("persist_state"))
        self.settings_search_sections = [
            self.__build_settings_search_section(
                self.frame_short_breaks, self.box7, self.box2
            ),
            self.__build_settings_search_section(
                self.frame_long_breaks, self.box8, self.box3
            ),
            self.__build_settings_search_section(
                self.frame_options,
                self.box6,
                self.box16_random_order,
                self.box9,
                self.box11,
                self.box10,
                self.box5,
                self.box1,
            ),
        ]
        self.__apply_search_filter()
        self.infobar_long_break_shown = False

    def __create_break_item(self, break_config: dict, is_short: bool) -> None:
        """Create an entry for break to be listed in the break tab."""
        parent_box = self.box_long_breaks
        if is_short:
            parent_box = self.box_short_breaks

        box: "BreakItem" = BreakItem(
            break_name=break_config["name"],
            search_text=self.__build_break_search_text(break_config, is_short),
            on_properties=lambda: self.__show_break_properties_dialog(
                break_config,
                is_short,
                self.config,
                on_close=lambda cfg: self.__update_break_item(box, cfg, is_short),
                on_add=lambda is_short, break_config: self.__create_break_item(
                    break_config, is_short
                ),
                on_remove=lambda: self.__remove_child(parent_box, box),
            ),
            on_delete=lambda: self.__delete_break(
                break_config,
                is_short,
                lambda: self.__remove_child(parent_box, box),
            ),
        )

        box.set_visible(True)
        parent_box.append(box)
        if not self.initializing:
            self.__apply_search_filter()

    @Gtk.Template.Callback()
    def on_reset_menu_clicked(self, button: Gtk.Button) -> None:
        self.popover.hide()

        def __confirmation_dialog_response(dialog, result) -> None:
            response_id = dialog.choose_finish(result)
            if response_id == 1:
                self.config = Config.reset_config()
                # Remove breaks from the container
                self.__clear_children(self.box_short_breaks)
                self.__clear_children(self.box_long_breaks)
                self.__clear_children(self.box_plugins)
                # Initialize again
                self.__initialize(self.config)

        messagedialog = Gtk.AlertDialog()
        messagedialog.set_modal(True)
        messagedialog.set_buttons(["_Cancel", _("Reset")])
        messagedialog.set_message(
            _("Are you sure you want to reset all settings to default?")
        )
        messagedialog.set_detail(_("You can't undo this action."))

        messagedialog.set_cancel_button(0)
        messagedialog.set_default_button(0)

        messagedialog.choose(self, None, __confirmation_dialog_response)

    def __clear_children(self, widget: Gtk.Box) -> None:
        while (child := widget.get_last_child()) is not None:
            widget.remove(child)

    def __remove_child(self, parent: Gtk.Box, child: Gtk.Widget) -> None:
        parent.remove(child)
        self.__apply_search_filter()

    def __update_break_item(
        self, box: "BreakItem", break_config: dict, is_short: bool
    ) -> None:
        box.set_break_name(break_config["name"])
        box.set_search_text(self.__build_break_search_text(break_config, is_short))
        self.__apply_search_filter()

    def __build_break_search_text(self, break_config: dict, is_short: bool) -> str:
        search_terms = [
            break_config["name"],
            _(break_config["name"]),
            *BREAK_SETTINGS_SEARCH_TERMS,
            _("Short") if is_short else _("Long"),
        ]

        if break_config.get("plugins") is not None:
            for plugin_id in break_config["plugins"]:
                if plugin_id in self.plugin_map:
                    search_terms.extend(
                        [self.plugin_map[plugin_id], _(self.plugin_map[plugin_id])]
                    )

        return self.__normalize_search_text(*search_terms)

    def __build_plugin_search_text(self, plugin_config: dict) -> str:
        search_terms = [
            plugin_config["meta"]["name"],
            _(plugin_config["meta"]["name"]),
            plugin_config["meta"]["description"],
            _(plugin_config["meta"]["description"]),
        ]
        for setting in plugin_config.get("settings", []):
            setting_type = setting.get("type", "").upper()
            if setting_type in SEARCHABLE_PLUGIN_SETTING_TYPES and "label" in setting:
                search_terms.extend([setting["label"], _(setting["label"])])
        return self.__normalize_search_text(*search_terms)

    def __iter_children(self, widget: Gtk.Widget) -> typing.Iterator[Gtk.Widget]:
        child = widget.get_first_child()
        while child is not None:
            yield child
            child = child.get_next_sibling()

    def __get_frame_title(self, frame: Gtk.Frame) -> str:
        label_widget = frame.get_label_widget()
        if isinstance(label_widget, Gtk.Label):
            return label_widget.get_label()
        return ""

    def __build_settings_search_section(
        self, frame: Gtk.Frame, *rows: Gtk.Widget
    ) -> tuple[Gtk.Frame, str, list[tuple[Gtk.Widget, str]]]:
        return (
            frame,
            self.__normalize_search_text(self.__get_frame_title(frame)),
            [(row, self.__widget_search_text(row)) for row in rows],
        )

    def __normalize_search_text(self, *parts: str) -> str:
        return " ".join(part for part in parts if part).casefold()

    def __widget_search_text(self, widget: Gtk.Widget) -> str:
        parts: list[str] = []
        self.__collect_widget_search_text(widget, parts)
        return self.__normalize_search_text(*parts)

    def __collect_widget_search_text(
        self, widget: Gtk.Widget, parts: list[str]
    ) -> None:
        if isinstance(widget, Gtk.Label):
            label = widget.get_label()
            if label:
                parts.append(label)
        elif isinstance(widget, Gtk.LinkButton):
            label = widget.get_label()
            if label:
                parts.append(label)

        for child in self.__iter_children(widget):
            self.__collect_widget_search_text(child, parts)

    def __matches_query(self, text: str, query: str) -> bool:
        return not query or query in text

    def __apply_search_filter(self) -> None:
        query = self.search_entry.get_text().strip().casefold()
        has_matches = {
            "Settings": self.__apply_settings_search_filter(query),
            "Breaks": self.__apply_break_search_filter(query),
            "Plugins": self.__apply_plugin_search_filter(query),
        }
        self.__update_stack_page_visibility(query, has_matches)

    def __apply_settings_search_filter(self, query: str) -> bool:
        has_visible_frame = False
        for frame, title, rows in self.settings_search_sections:
            show_all_rows = self.__matches_query(title, query)
            visible_row_found = False
            for row, row_search_text in rows:
                is_visible = show_all_rows or self.__matches_query(
                    row_search_text, query
                )
                row.set_visible(is_visible)
                visible_row_found = visible_row_found or is_visible
            frame.set_visible(visible_row_found)
            has_visible_frame = has_visible_frame or visible_row_found
        return has_visible_frame

    def __apply_break_search_filter(self, query: str) -> bool:
        short_visible = self.__apply_break_section_filter(
            self.expander_short_breaks,
            self.box_short_breaks,
            self.__normalize_search_text(self.expander_short_breaks.get_label() or ""),
            query,
        )
        long_visible = self.__apply_break_section_filter(
            self.expander_long_breaks,
            self.box_long_breaks,
            self.__normalize_search_text(self.expander_long_breaks.get_label() or ""),
            query,
        )
        self.separator_breaks.set_visible(short_visible and long_visible)
        return short_visible or long_visible

    def __apply_break_section_filter(
        self, expander: Gtk.Expander, container: Gtk.Box, title: str, query: str
    ) -> bool:
        show_all_rows = self.__matches_query(title, query)
        visible_row_found = False
        for child in self.__iter_children(container):
            is_visible = show_all_rows or (
                isinstance(child, BreakItem) and child.matches_query(query)
            )
            child.set_visible(is_visible)
            visible_row_found = visible_row_found or is_visible
        expander.set_visible(visible_row_found)
        if query and visible_row_found:
            expander.set_expanded(True)
        return visible_row_found

    def __apply_plugin_search_filter(self, query: str) -> bool:
        has_visible_plugin = False
        for child in self.__iter_children(self.box_plugins):
            is_visible = isinstance(child, PluginItem) and child.matches_query(query)
            child.set_visible(is_visible)
            has_visible_plugin = has_visible_plugin or is_visible
        return has_visible_plugin

    def __update_stack_page_visibility(
        self, query: str, has_matches: dict[str, bool]
    ) -> None:
        visible_page_names: list[str] = []
        for page_name, page_widget in self.stack_pages.items():
            page = self.stack.get_page(page_widget)
            is_visible = not query or has_matches[page_name]
            page.set_visible(is_visible)
            if is_visible:
                visible_page_names.append(page_name)

        if not visible_page_names:
            return

        current_page_name = self.stack.get_visible_child_name()
        if current_page_name not in visible_page_names:
            self.stack.set_visible_child_name(visible_page_names[0])

    def __on_search_mode_changed(self, search_bar, _param_spec) -> None:
        if search_bar.get_search_mode():
            self.search_entry.grab_focus()
            return

        if self.search_entry.get_text():
            self.search_entry.set_text("")
        else:
            self.__apply_search_filter()

    def __delete_break(
        self, break_config: dict, is_short: bool, on_remove: typing.Callable[[], None]
    ) -> None:
        """Remove the break after a confirmation."""

        def __confirmation_dialog_response(dialog, result) -> None:
            response_id = dialog.choose_finish(result)
            if response_id == 1:
                if is_short:
                    self.config.get("short_breaks").remove(break_config)
                else:
                    self.config.get("long_breaks").remove(break_config)
                on_remove()

        messagedialog = Gtk.AlertDialog()
        messagedialog.set_modal(True)
        messagedialog.set_buttons(["_Cancel", _("Delete")])
        messagedialog.set_message(_("Are you sure you want to delete this break?"))
        messagedialog.set_detail(_("You can't undo this action."))

        messagedialog.set_cancel_button(0)
        messagedialog.set_default_button(0)

        messagedialog.choose(self, None, __confirmation_dialog_response)

    def __create_plugin_item(self, plugin_config: dict) -> "PluginItem":
        """Create an entry for plugin to be listed in the plugin tab."""
        box = PluginItem(
            plugin_config,
            self.__build_plugin_search_text(plugin_config),
            on_properties=lambda: self.__show_plugins_properties_dialog(plugin_config),
        )

        self.plugin_items[plugin_config["id"]] = box

        if plugin_config.get("break_override_allowed", False):
            self.plugin_map[plugin_config["id"]] = plugin_config["meta"]["name"]

        box.set_visible(True)
        return box

    def __show_plugins_properties_dialog(self, plugin_config: dict) -> None:
        """Show the PluginProperties dialog."""
        dialog = PluginSettingsDialog(self, plugin_config)
        dialog.show()

    def __show_break_properties_dialog(
        self,
        break_config: dict,
        is_short: bool,
        parent: Config,
        on_close: typing.Callable[[dict], None],
        on_add: typing.Callable[[bool, dict], None],
        on_remove: typing.Callable[[], None],
    ) -> None:
        """Show the BreakProperties dialog."""
        dialog = BreakSettingsDialog(
            self,
            break_config,
            is_short,
            parent,
            self.plugin_map,
            on_close,
            on_add,
            on_remove,
        )
        dialog.show()

    def show(self) -> None:
        """Show the SettingsDialog."""
        self.present()

    @Gtk.Template.Callback()
    def on_search_button_clicked(self, button: Gtk.Button) -> None:
        should_enable_search = not self.search_bar.get_search_mode()
        self.search_bar.set_search_mode(should_enable_search)
        if should_enable_search:
            self.search_entry.grab_focus()

    @Gtk.Template.Callback()
    def on_search_changed(self, entry: Gtk.SearchEntry) -> None:
        self.__apply_search_filter()

    @Gtk.Template.Callback()
    def on_switch_postpone_activate(self, switch, state) -> None:
        """Event handler to the state change of the postpone switch.

        Enable or disable the self.spin_postpone_duration based on the
        state of the postpone switch.
        """
        self.spin_postpone_duration.set_sensitive(self.switch_postpone.get_active())
        self.dropdown_postpone_unit.set_sensitive(self.switch_postpone.get_active())

    @Gtk.Template.Callback()
    def on_spin_short_break_interval_change(self, spin_button, *value) -> None:
        """Event handler for value change of short break interval."""
        short_break_interval = self.spin_short_break_interval.get_value_as_int()
        long_break_interval = self.spin_long_break_interval.get_value_as_int()
        self.spin_long_break_interval.set_range(short_break_interval * 2, 120)
        self.spin_long_break_interval.set_increments(
            short_break_interval, short_break_interval * 2
        )
        self.spin_long_break_interval.set_value(
            short_break_interval
            * math.ceil(long_break_interval / self.last_short_break_interval)
        )
        self.last_short_break_interval = short_break_interval
        if not self.initializing and not self.infobar_long_break_shown:
            self.infobar_long_break_shown = True
            self.info_bar_long_break.show()

    @Gtk.Template.Callback()
    def on_spin_long_break_interval_change(self, spin_button, *value) -> None:
        """Event handler for value change of long break interval."""
        if not self.initializing and not self.infobar_long_break_shown:
            self.infobar_long_break_shown = True
            self.info_bar_long_break.show()

    @Gtk.Template.Callback()
    def on_info_bar_long_break_close(self, infobar, *user_data) -> None:
        """Event handler for info bar close action."""
        self.info_bar_long_break.hide()

    @Gtk.Template.Callback()
    def add_break(self, button) -> None:
        """Event handler for add break button."""
        dialog = NewBreakDialog(
            self,
            self.config,
            lambda is_short, break_config: self.__create_break_item(
                break_config, is_short
            ),
        )
        dialog.show()

    @Gtk.Template.Callback()
    def on_window_delete(self, *args) -> None:
        """Event handler for Settings dialog close action."""
        self.config.set(
            "short_break_duration", self.spin_short_break_duration.get_value_as_int()
        )
        self.config.set(
            "long_break_duration", self.spin_long_break_duration.get_value_as_int()
        )
        self.config.set(
            "short_break_interval", self.spin_short_break_interval.get_value_as_int()
        )
        self.config.set(
            "long_break_interval", self.spin_long_break_interval.get_value_as_int()
        )
        self.config.set(
            "pre_break_warning_time", self.spin_time_to_prepare.get_value_as_int()
        )
        self.config.set(
            "postpone_duration", self.spin_postpone_duration.get_value_as_int()
        )
        self.config.set(
            "postpone_unit",
            # the model is a GtkStringList - so get_selected_item will return a
            # StringObject
            typing.cast(
                Gtk.StringObject, self.dropdown_postpone_unit.get_selected_item()
            ).get_string(),
        )
        self.config.set(
            "shortcut_disable_time",
            self.spin_disable_keyboard_shortcut.get_value_as_int(),
        )
        self.config.set("strict_break", self.switch_strict_break.get_active())
        self.config.set("random_order", self.switch_random_order.get_active())
        self.config.set("allow_postpone", self.switch_postpone.get_active())
        self.config.set("persist_state", self.switch_persist.get_active())
        for plugin in self.config.get("plugins"):
            if plugin["id"] in self.plugin_items:
                plugin["enabled"] = self.plugin_items[plugin["id"]].is_enabled()

        self.on_save_settings(self.config)  # Call the provided save method
        self.destroy()


@Gtk.Template(filename=SETTINGS_BREAK_ITEM_GLADE)
class BreakItem(Gtk.Box):
    __gtype_name__ = "BreakItem"

    lbl_name: Gtk.Label = Gtk.Template.Child()

    def __init__(
        self,
        break_name: str,
        search_text: str,
        on_properties: typing.Callable[[], None],
        on_delete: typing.Callable[[], None],
    ):
        super().__init__()

        self.on_properties = on_properties
        self.on_delete = on_delete
        self.search_text = search_text

        self.lbl_name.set_label(_(break_name))

    def set_break_name(self, break_name: str) -> None:
        self.lbl_name.set_label(_(break_name))

    def set_search_text(self, search_text: str) -> None:
        self.search_text = search_text

    def matches_query(self, query: str) -> bool:
        return query in self.search_text

    @Gtk.Template.Callback()
    def on_properties_clicked(self, button) -> None:
        self.on_properties()

    @Gtk.Template.Callback()
    def on_delete_clicked(self, button) -> None:
        self.on_delete()


@Gtk.Template(filename=SETTINGS_PLUGIN_ITEM_GLADE)
class PluginItem(Gtk.Box):
    __gtype_name__ = "PluginItem"

    lbl_plugin_name: Gtk.Label = Gtk.Template.Child()
    lbl_plugin_description: Gtk.Label = Gtk.Template.Child()
    switch_enable: Gtk.Switch = Gtk.Template.Child()
    btn_properties: Gtk.Button = Gtk.Template.Child()
    btn_disable_errored: Gtk.Button = Gtk.Template.Child()
    btn_plugin_extra_link: Gtk.LinkButton = Gtk.Template.Child()
    img_plugin_icon: Gtk.Image = Gtk.Template.Child()

    def __init__(
        self,
        plugin_config: dict,
        search_text: str,
        on_properties: typing.Callable[[], None],
    ):
        super().__init__()

        self.on_properties = on_properties
        self.plugin_config = plugin_config
        self.search_text = search_text

        self.lbl_plugin_name.set_label(_(plugin_config["meta"]["name"]))
        self.switch_enable.set_active(plugin_config["enabled"])

        if plugin_config["error"]:
            message = plugin_config["meta"]["dependency_description"]
            if isinstance(message, PluginDependency):
                self.lbl_plugin_description.set_label(_(message.message))
                if message.link is not None:
                    self.btn_plugin_extra_link.set_uri(message.link)
                self.btn_plugin_extra_link.set_visible(True)
            else:
                self.lbl_plugin_description.set_label(_(message))
            self.lbl_plugin_name.set_sensitive(False)
            self.lbl_plugin_description.set_sensitive(False)
            self.switch_enable.set_sensitive(False)
            self.btn_properties.set_sensitive(False)
            if plugin_config["enabled"]:
                self.btn_disable_errored.set_visible(True)
        else:
            self.lbl_plugin_description.set_label(
                _(plugin_config["meta"]["description"])
            )
            if plugin_config["settings"]:
                self.btn_properties.set_sensitive(True)
            else:
                self.btn_properties.set_sensitive(False)

        if plugin_config["icon"]:
            self.img_plugin_icon.set_from_file(plugin_config["icon"])

    def is_enabled(self) -> bool:
        return self.switch_enable.get_active()

    def matches_query(self, query: str) -> bool:
        return query in self.search_text

    @Gtk.Template.Callback()
    def on_disable_errored(self, button) -> None:
        """Permanently disable errored plugin."""
        self.btn_disable_errored.set_sensitive(False)
        self.switch_enable.set_active(False)

    @Gtk.Template.Callback()
    def on_properties_clicked(self, button) -> None:
        if not self.plugin_config["error"] and self.plugin_config["settings"]:
            self.on_properties()


@Gtk.Template(filename=SETTINGS_ITEM_INT_GLADE)
class IntItem(Gtk.Box):
    __gtype_name__ = "IntItem"

    lbl_name: Gtk.Label = Gtk.Template.Child()
    spin_value: Gtk.SpinButton = Gtk.Template.Child()

    def __init__(self, name: str, value: float, min_value: float, max_value: float):
        super().__init__()

        self.lbl_name.set_label(_(name))
        self.spin_value.set_range(min_value, max_value)
        self.spin_value.set_value(value)

    def get_value(self) -> float:
        return self.spin_value.get_value()


@Gtk.Template(filename=SETTINGS_ITEM_TEXT_GLADE)
class TextItem(Gtk.Box):
    __gtype_name__ = "TextItem"

    lbl_name: Gtk.Label = Gtk.Template.Child()
    txt_value: Gtk.Entry = Gtk.Template.Child()

    def __init__(self, name: str, value: str):
        super().__init__()

        self.lbl_name.set_label(_(name))
        self.txt_value.set_text(value)

    def get_value(self) -> str:
        return self.txt_value.get_text()


@Gtk.Template(filename=SETTINGS_ITEM_BOOL_GLADE)
class BoolItem(Gtk.Box):
    __gtype_name__ = "BoolItem"

    lbl_name: Gtk.Label = Gtk.Template.Child()
    switch_value: Gtk.Switch = Gtk.Template.Child()

    def __init__(self, name: str, value: bool):
        super().__init__()

        self.lbl_name.set_label(_(name))
        self.switch_value.set_active(value)

    def get_value(self) -> bool:
        return self.switch_value.get_active()


@Gtk.Template(filename=SETTINGS_DIALOG_PLUGIN_GLADE)
class PluginSettingsDialog(Gtk.Window):
    """Builds a settings dialog based on the configuration of a plugin."""

    __gtype_name__ = "PluginSettingsDialog"

    box_settings: Gtk.Box = Gtk.Template.Child()

    def __init__(self, parent: Gtk.Window, config: typing.Any):
        super().__init__(transient_for=parent)

        self.config = config
        self.property_controls = []

        for setting in config.get("settings"):
            box: typing.Union[IntItem, BoolItem, TextItem]
            if setting["type"].upper() == "INT":
                box = IntItem(
                    setting["label"],
                    config["active_plugin_config"][setting["id"]],
                    setting.get("min", 0),
                    setting.get("max", 120),
                )
            elif setting["type"].upper() == "TEXT":
                box = TextItem(
                    setting["label"], config["active_plugin_config"][setting["id"]]
                )
            elif setting["type"].upper() == "BOOL":
                box = BoolItem(
                    setting["label"], config["active_plugin_config"][setting["id"]]
                )
            else:
                continue

            self.property_controls.append({"key": setting["id"], "box": box})
            self.box_settings.append(box)

    @Gtk.Template.Callback()
    def on_window_delete(self, *args) -> None:
        """Event handler for Properties dialog close action."""
        for property_control in self.property_controls:
            self.config["active_plugin_config"][property_control["key"]] = (
                property_control["box"].get_value()
            )
        self.destroy()

    def show(self) -> None:
        """Show the Properties dialog."""
        self.present()


@Gtk.Template(filename=SETTINGS_DIALOG_BREAK_GLADE)
class BreakSettingsDialog(Gtk.Window):
    """Builds a settings dialog based on the configuration of a plugin."""

    __gtype_name__ = "BreakSettingsDialog"

    txt_break: Gtk.Entry = Gtk.Template.Child()
    switch_override_interval: Gtk.Switch = Gtk.Template.Child()
    switch_override_duration: Gtk.Switch = Gtk.Template.Child()
    switch_override_plugins: Gtk.Switch = Gtk.Template.Child()
    spin_interval: Gtk.SpinButton = Gtk.Template.Child()
    spin_duration: Gtk.SpinButton = Gtk.Template.Child()
    btn_image: Gtk.Button = Gtk.Template.Child()
    cmb_type: Gtk.ComboBox = Gtk.Template.Child()
    grid_plugins: Gtk.Grid = Gtk.Template.Child()
    lst_break_types: Gtk.ComboBox = Gtk.Template.Child()

    def __init__(
        self,
        parent: Gtk.Window,
        break_config: dict,
        is_short: bool,
        parent_config: Config,
        plugin_map: dict[str, str],
        on_close: typing.Callable[[dict], None],
        on_add: typing.Callable[[bool, dict], None],
        on_remove: typing.Callable[[], None],
    ):
        super().__init__(transient_for=parent)

        self.break_config = break_config
        self.parent_config = parent_config
        self.plugin_check_buttons = {}
        self.on_close = on_close
        self.is_short = is_short
        self.on_add = on_add
        self.on_remove = on_remove

        interval_overriden = break_config.get("interval", None) is not None
        duration_overriden = break_config.get("duration", None) is not None
        plugins_overriden = break_config.get("plugins", None) is not None

        # Set the values
        self.txt_break.set_text(_(break_config["name"]))
        self.switch_override_interval.set_active(interval_overriden)
        self.switch_override_duration.set_active(duration_overriden)
        self.switch_override_plugins.set_active(plugins_overriden)
        self.cmb_type.set_active(0 if is_short else 1)

        if interval_overriden:
            self.spin_interval.set_value(break_config["interval"])
        else:
            if is_short:
                self.spin_interval.set_value(parent_config.get("short_break_interval"))
            else:
                self.spin_interval.set_value(parent_config.get("long_break_interval"))

        if duration_overriden:
            self.spin_duration.set_value(break_config["duration"])
        else:
            if is_short:
                self.spin_duration.set_value(parent_config.get("short_break_duration"))
            else:
                self.spin_duration.set_value(parent_config.get("long_break_duration"))
        row = 0
        col = 0
        for plugin_id in plugin_map.keys():
            chk_button = Gtk.CheckButton.new_with_label(_(plugin_map[plugin_id]))
            self.plugin_check_buttons[plugin_id] = chk_button
            self.grid_plugins.attach(chk_button, row, col, 1, 1)
            if plugins_overriden:
                chk_button.set_active(plugin_id in break_config["plugins"])
            else:
                chk_button.set_active(True)
            row += 1
            if row > 2:
                col += 1
                row = 0

        if "image" in self.break_config:
            pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_scale(
                self.break_config["image"], 16, 16, True
            )
            image = Gtk.Image.new_from_pixbuf(pixbuf)
            self.btn_image.set_child(image)

        self.on_switch_override_interval_activate(
            self.switch_override_interval, self.switch_override_interval.get_active()
        )
        self.on_switch_override_duration_activate(
            self.switch_override_duration, self.switch_override_duration.get_active()
        )
        self.on_switch_override_plugins_activate(
            self.switch_override_plugins, self.switch_override_plugins.get_active()
        )

    @Gtk.Template.Callback()
    def on_switch_override_interval_activate(self, switch_button, state) -> None:
        """switch_override_interval state change event handler."""
        self.spin_interval.set_sensitive(state)

    @Gtk.Template.Callback()
    def on_switch_override_duration_activate(self, switch_button, state) -> None:
        """switch_override_duration state change event handler."""
        self.spin_duration.set_sensitive(state)

    @Gtk.Template.Callback()
    def on_switch_override_plugins_activate(self, switch_button, state) -> None:
        """switch_override_plugins state change event handler."""
        for chk_box in self.plugin_check_buttons.values():
            chk_box.set_sensitive(state)

    @Gtk.Template.Callback()
    def select_image(self, button) -> None:
        """Show a file chooser dialog and let the user to select an image."""
        dialog = Gtk.FileDialog()
        dialog.set_title(_("Please select an image"))

        png_filter = Gtk.FileFilter()
        png_filter.set_name("PNG files")
        png_filter.add_mime_type("image/png")
        png_filter.add_pattern("*.png")
        filters = Gio.ListStore.new(Gtk.FileFilter)
        filters.append(png_filter)
        dialog.set_filters(filters)

        dialog.open(self, None, self.select_image_callback)

    def select_image_callback(
        self, dialog: Gtk.FileDialog, result: Gio.AsyncResult
    ) -> None:
        response = None

        try:
            response = dialog.open_finish(result)
        except Exception:
            # user pressing "Cancel" throws a generic exception here
            pass

        if response is not None:
            self.break_config["image"] = response.get_path()
            pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_scale(
                self.break_config["image"], 16, 16, True
            )
            image = Gtk.Image.new_from_pixbuf(pixbuf)
            self.btn_image.set_child(image)
        else:
            self.break_config.pop("image", None)
            self.btn_image.set_icon_name("gtk-missing-image")

    @Gtk.Template.Callback()
    def on_window_delete(self, *args) -> None:
        """Event handler for Properties dialog close action."""
        break_name = self.txt_break.get_text().strip()
        if break_name:
            self.break_config["name"] = break_name
        if self.switch_override_interval.get_active():
            self.break_config["interval"] = int(self.spin_interval.get_value())
        else:
            self.break_config.pop("interval", None)
        if self.switch_override_duration.get_active():
            self.break_config["duration"] = int(self.spin_duration.get_value())
        else:
            self.break_config.pop("duration", None)
        if self.switch_override_plugins.get_active():
            selected_plugins = []
            for plugin_id in self.plugin_check_buttons:
                if self.plugin_check_buttons[plugin_id].get_active():
                    selected_plugins.append(plugin_id)
            self.break_config["plugins"] = selected_plugins
        else:
            self.break_config.pop("plugins", None)

        if self.is_short and self.cmb_type.get_active() == 1:
            # Changed from short to long
            self.parent_config.get("short_breaks").remove(self.break_config)
            self.parent_config.get("long_breaks").append(self.break_config)
            self.on_remove()
            self.on_add(not self.is_short, self.break_config)
        elif not self.is_short and self.cmb_type.get_active() == 0:
            # Changed from long to short
            self.parent_config.get("long_breaks").remove(self.break_config)
            self.parent_config.get("short_breaks").append(self.break_config)
            self.on_remove()
            self.on_add(not self.is_short, self.break_config)
        else:
            self.on_close(self.break_config)
        self.destroy()

    def show(self) -> None:
        """Show the Properties dialog."""
        self.present()


@Gtk.Template(filename=SETTINGS_DIALOG_NEW_BREAK_GLADE)
class NewBreakDialog(Gtk.Window):
    """Builds a new break dialog."""

    __gtype_name__ = "NewBreakDialog"

    txt_break: Gtk.Entry = Gtk.Template.Child()
    cmb_type: Gtk.ComboBox = Gtk.Template.Child()

    def __init__(
        self,
        parent: Gtk.Window,
        parent_config: Config,
        on_add: typing.Callable[[bool, dict], None],
    ):
        super().__init__(transient_for=parent)

        self.parent_config = parent_config
        self.on_add = on_add

    @Gtk.Template.Callback()
    def discard(self, button) -> None:
        """Close the dialog."""
        self.destroy()

    @Gtk.Template.Callback()
    def save(self, button) -> None:
        """Event handler for Properties dialog close action."""
        break_config = {"name": self.txt_break.get_text().strip()}

        if self.cmb_type.get_active() == 0:
            self.parent_config.get("short_breaks").append(break_config)
            self.on_add(True, break_config)
        else:
            self.parent_config.get("long_breaks").append(break_config)
            self.on_add(False, break_config)
        self.destroy()

    @Gtk.Template.Callback()
    def on_window_delete(self, *args) -> None:
        """Event handler for dialog close action."""
        self.destroy()

    def show(self) -> None:
        """Show the Properties dialog."""
        self.present()
