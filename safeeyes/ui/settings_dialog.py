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
gi.require_version("Adw", "1")
from gi.repository import Adw, Gtk, Gio
from gi.repository import GdkPixbuf


SETTINGS_DIALOG_PLUGIN_GLADE = os.path.join(
    utility.BIN_DIRECTORY, "glade/settings_plugin.glade"
)
SETTINGS_DIALOG_BREAK_GLADE = os.path.join(
    utility.BIN_DIRECTORY, "glade/settings_break.glade"
)
SETTINGS_DIALOG_NEW_BREAK_GLADE = os.path.join(
    utility.BIN_DIRECTORY, "glade/new_break.glade"
)
SETTINGS_ITEM_INT_GLADE = os.path.join(utility.BIN_DIRECTORY, "glade/item_int.glade")
SETTINGS_ITEM_TEXT_GLADE = os.path.join(utility.BIN_DIRECTORY, "glade/item_text.glade")
SETTINGS_ITEM_BOOL_GLADE = os.path.join(utility.BIN_DIRECTORY, "glade/item_bool.glade")


class SettingsDialog(Adw.PreferencesWindow):
    """Create and initialize SettingsDialog instance."""

    __gtype_name__ = "SettingsDialog"

    plugin_items: dict[str, "PluginItem"]
    plugin_map: dict[str, str]
    config: Config

    def __init__(
        self,
        application: Gtk.Application,
        config: Config,
        on_save_settings: typing.Callable[[Config], None],
    ):
        Adw.init()
        super().__init__(application=application)

        self.set_title("Safe Eyes")
        self.set_icon_name("io.github.slgobinath.SafeEyes")
        self.set_default_size(620, 760)
        self.set_search_enabled(True)
        self.connect("close-request", self.on_window_delete)

        self.config = config
        self.on_save_settings = on_save_settings
        self.plugin_items = {}
        self.plugin_map = {}
        self.last_short_break_interval = config.get("short_break_interval")
        self.initializing = True
        self.infobar_long_break_shown = False

        self.__build_ui()

        # Set the current values of input fields
        self.__initialize(config)

        self.initializing = False

    def __build_ui(self) -> None:
        self.spin_short_break_interval = self.__create_spin_button(1, 60, 1, 5)
        self.spin_short_break_duration = self.__create_spin_button(1, 1800, 1, 5)
        self.spin_long_break_interval = self.__create_spin_button(2, 120, 1, 5)
        self.spin_long_break_interval.set_snap_to_ticks(True)
        self.spin_long_break_interval.set_wrap(True)
        self.spin_long_break_duration = self.__create_spin_button(1, 3600, 5, 10)
        self.spin_time_to_prepare = self.__create_spin_button(1, 60, 1, 5)
        self.spin_postpone_duration = self.__create_spin_button(1, 15, 1, 5)
        self.spin_disable_keyboard_shortcut = self.__create_spin_button(0, 15, 1, 5)

        self.dropdown_postpone_unit = Gtk.DropDown.new_from_strings(
            [_("minutes"), _("seconds")]
        )
        self.dropdown_postpone_unit.set_valign(Gtk.Align.CENTER)

        self.switch_random_order = Gtk.Switch()
        self.switch_random_order.set_valign(Gtk.Align.CENTER)
        self.switch_strict_break = Gtk.Switch()
        self.switch_strict_break.set_valign(Gtk.Align.CENTER)
        self.switch_postpone = Gtk.Switch()
        self.switch_postpone.set_valign(Gtk.Align.CENTER)
        self.switch_persist = Gtk.Switch()
        self.switch_persist.set_valign(Gtk.Align.CENTER)

        self.spin_short_break_interval.connect(
            "value-changed", self.on_spin_short_break_interval_change
        )
        self.spin_long_break_interval.connect(
            "value-changed", self.on_spin_long_break_interval_change
        )
        self.switch_postpone.connect(
            "notify::active", self.on_switch_postpone_activate
        )

        settings_page = Adw.PreferencesPage.new()
        settings_page.set_name("settings")
        settings_page.set_title(_("Settings"))
        settings_page.set_icon_name("preferences-system-symbolic")
        self.add(settings_page)

        short_break_group = Adw.PreferencesGroup.new()
        short_break_group.set_title(_("Short Breaks"))
        short_break_group.add(
            self.__create_action_row(
                _("Interval between two breaks (in minutes)"),
                self.spin_short_break_interval,
            )
        )
        short_break_group.add(
            self.__create_action_row(
                _("Break duration (in seconds)"),
                self.spin_short_break_duration,
            )
        )
        settings_page.add(short_break_group)

        long_break_group = Adw.PreferencesGroup.new()
        long_break_group.set_title(_("Long Breaks"))
        self.info_bar_long_break = self.__create_long_break_notice_row()
        self.info_bar_long_break.set_visible(False)
        long_break_group.add(self.info_bar_long_break)
        long_break_group.add(
            self.__create_action_row(
                _("Interval between two breaks (in minutes)"),
                self.spin_long_break_interval,
            )
        )
        long_break_group.add(
            self.__create_action_row(
                _("Break duration (in seconds)"),
                self.spin_long_break_duration,
            )
        )
        settings_page.add(long_break_group)

        options_group = Adw.PreferencesGroup.new()
        options_group.set_title(_("Options"))
        reset_button = Gtk.Button.new_with_label(_("Reset"))
        reset_button.add_css_class("destructive-action")
        reset_button.connect("clicked", self.on_reset_menu_clicked)
        options_group.set_header_suffix(reset_button)
        options_group.add(
            self.__create_action_row(
                _("Time to prepare for a break (in seconds)"),
                self.spin_time_to_prepare,
            )
        )
        options_group.add(
            self.__create_switch_row(
                _("Show breaks in random order"), self.switch_random_order
            )
        )
        options_group.add(
            self.__create_switch_row(
                _("Strict break (No way to skip breaks)"), self.switch_strict_break
            )
        )
        options_group.add(
            self.__create_switch_row(
                _("Allow postponing breaks"), self.switch_postpone
            )
        )
        options_group.add(self.__create_postpone_row())
        options_group.add(
            self.__create_action_row(
                _("Skipping/postponing disabled period (in seconds)"),
                self.spin_disable_keyboard_shortcut,
            )
        )
        options_group.add(
            self.__create_switch_row(
                _("Persist the internal state"), self.switch_persist
            )
        )
        settings_page.add(options_group)

        breaks_page = Adw.PreferencesPage.new()
        breaks_page.set_name("breaks")
        breaks_page.set_title(_("Breaks"))
        breaks_page.set_icon_name("preferences-system-time-symbolic")
        self.add(breaks_page)

        self.box_short_breaks = Adw.PreferencesGroup.new()
        self.box_short_breaks.set_title(_("Short Breaks"))
        add_break_button = Gtk.Button.new_from_icon_name("list-add-symbolic")
        add_break_button.add_css_class("flat")
        add_break_button.connect("clicked", self.add_break)
        self.box_short_breaks.set_header_suffix(add_break_button)
        breaks_page.add(self.box_short_breaks)

        self.box_long_breaks = Adw.PreferencesGroup.new()
        self.box_long_breaks.set_title(_("Long Breaks"))
        breaks_page.add(self.box_long_breaks)

        plugins_page = Adw.PreferencesPage.new()
        plugins_page.set_name("plugins")
        plugins_page.set_title(_("Plugins"))
        plugins_page.set_icon_name("application-x-addon-symbolic")
        self.add(plugins_page)

        self.box_plugins = Adw.PreferencesGroup.new()
        plugins_page.add(self.box_plugins)

    def __create_spin_button(
        self, lower: float, upper: float, step: float, page: float
    ) -> Gtk.SpinButton:
        adjustment = Gtk.Adjustment(
            lower=lower,
            upper=upper,
            step_increment=step,
            page_increment=page,
            value=lower,
        )
        spin_button = Gtk.SpinButton.new(adjustment, 1, 0)
        spin_button.set_numeric(True)
        spin_button.set_update_policy(Gtk.SpinButtonUpdatePolicy.IF_VALID)
        spin_button.set_valign(Gtk.Align.CENTER)
        return spin_button

    def __create_action_row(
        self, title: str, suffix: Gtk.Widget, *, activatable: bool = True
    ) -> Adw.ActionRow:
        row = Adw.ActionRow.new()
        row.set_title(title)
        row.add_suffix(suffix)
        row.set_activatable_widget(suffix)
        row.set_activatable(activatable)
        return row

    def __create_switch_row(self, title: str, switch: Gtk.Switch) -> Adw.ActionRow:
        return self.__create_action_row(title, switch)

    def __create_postpone_row(self) -> Adw.ActionRow:
        row = Adw.ActionRow.new()
        row.set_title(_("Postponement duration in"))
        row.add_suffix(self.dropdown_postpone_unit)
        row.add_suffix(self.spin_postpone_duration)
        row.set_activatable(False)
        return row

    def __create_long_break_notice_row(self) -> Adw.ActionRow:
        row = Adw.ActionRow.new()
        row.set_title(
            _("Long break interval must be a multiple of short break interval")
        )
        row.set_activatable(False)

        icon = Gtk.Image.new_from_icon_name("dialog-information-symbolic")
        icon.set_valign(Gtk.Align.CENTER)
        row.add_prefix(icon)

        close_button = Gtk.Button.new_from_icon_name("window-close-symbolic")
        close_button.add_css_class("flat")
        close_button.set_valign(Gtk.Align.CENTER)
        close_button.connect("clicked", self.on_info_bar_long_break_close)
        row.add_suffix(close_button)
        return row

    def __initialize(self, config: Config) -> None:
        # Don't show infobar for changes made internally
        self.infobar_long_break_shown = True
        for short_break in config.get("short_breaks"):
            self.__create_break_item(short_break, True)
        for long_break in config.get("long_breaks"):
            self.__create_break_item(long_break, False)

        for plugin_config in utility.load_plugins_config(config):
            self.box_plugins.add(self.__create_plugin_item(plugin_config))

        self.spin_short_break_duration.set_value(config.get("short_break_duration"))
        self.spin_long_break_duration.set_value(config.get("long_break_duration"))
        self.spin_short_break_interval.set_value(config.get("short_break_interval"))
        self.spin_long_break_interval.set_value(config.get("long_break_interval"))
        self.spin_time_to_prepare.set_value(config.get("pre_break_warning_time"))
        self.spin_postpone_duration.set_value(config.get("postpone_duration"))
        self.dropdown_postpone_unit.set_selected(
            1 if config.get("postpone_unit") == "seconds" else 0
        )
        self.spin_disable_keyboard_shortcut.set_value(
            config.get("shortcut_disable_time")
        )
        self.switch_strict_break.set_active(config.get("strict_break"))
        self.switch_random_order.set_active(config.get("random_order"))
        self.switch_postpone.set_active(config.get("allow_postpone"))
        self.switch_persist.set_active(config.get("persist_state"))
        self.infobar_long_break_shown = False
        self.on_switch_postpone_activate(self.switch_postpone, None)

    def __create_break_item(self, break_config: dict, is_short: bool) -> None:
        """Create an entry for break to be listed in the break tab."""
        parent_box = self.box_long_breaks
        if is_short:
            parent_box = self.box_short_breaks

        box: "BreakItem" = BreakItem(
            break_name=break_config["name"],
            on_properties=lambda: self.__show_break_properties_dialog(
                break_config,
                is_short,
                self.config,
                on_close=lambda cfg: box.set_break_name(cfg["name"]),
                on_add=lambda is_short, break_config: self.__create_break_item(
                    break_config, is_short
                ),
                on_remove=lambda: parent_box.remove(box),
            ),
            on_delete=lambda: self.__delete_break(
                break_config,
                is_short,
                lambda: parent_box.remove(box),
            ),
        )

        parent_box.add(box)

    def on_reset_menu_clicked(self, button: Gtk.Button) -> None:
        def __confirmation_dialog_response(dialog, result) -> None:
            response_id = dialog.choose_finish(result)
            if response_id == 1:
                self.config = Config.reset_config()
                self.plugin_items = {}
                self.plugin_map = {}
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

    def __clear_children(self, group: Adw.PreferencesGroup) -> None:
        rows = []
        index = 0
        while (row := group.get_row(index)) is not None:
            rows.append(row)
            index += 1

        for row in rows:
            group.remove(row)

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

    def on_switch_postpone_activate(
        self, switch: Gtk.Switch, _active_param: typing.Any
    ) -> None:
        """Event handler to the state change of the postpone switch.

        Enable or disable the self.spin_postpone_duration based on the
        state of the postpone switch.
        """
        self.spin_postpone_duration.set_sensitive(self.switch_postpone.get_active())
        self.dropdown_postpone_unit.set_sensitive(self.switch_postpone.get_active())

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
            self.info_bar_long_break.set_visible(True)

    def on_spin_long_break_interval_change(self, spin_button, *value) -> None:
        """Event handler for value change of long break interval."""
        if not self.initializing and not self.infobar_long_break_shown:
            self.infobar_long_break_shown = True
            self.info_bar_long_break.set_visible(True)

    def on_info_bar_long_break_close(self, _button, *user_data) -> None:
        """Event handler for info bar close action."""
        self.info_bar_long_break.set_visible(False)

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
            "seconds" if self.dropdown_postpone_unit.get_selected() == 1 else "minutes",
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
        return False


class BreakItem(Adw.ActionRow):
    __gtype_name__ = "BreakItem"

    def __init__(
        self,
        break_name: str,
        on_properties: typing.Callable[[], None],
        on_delete: typing.Callable[[], None],
    ):
        super().__init__()

        self.on_properties = on_properties
        self.on_delete = on_delete

        self.set_title(_(break_name))
        self.set_activatable(False)

        properties_button = Gtk.Button.new_from_icon_name("document-properties-symbolic")
        properties_button.add_css_class("flat")
        properties_button.set_valign(Gtk.Align.CENTER)
        properties_button.connect("clicked", self.on_properties_clicked)
        self.add_suffix(properties_button)

        delete_button = Gtk.Button.new_from_icon_name("user-trash-symbolic")
        delete_button.add_css_class("flat")
        delete_button.add_css_class("destructive-action")
        delete_button.set_valign(Gtk.Align.CENTER)
        delete_button.connect("clicked", self.on_delete_clicked)
        self.add_suffix(delete_button)

    def set_break_name(self, break_name: str) -> None:
        self.set_title(_(break_name))

    def on_properties_clicked(self, button) -> None:
        self.on_properties()

    def on_delete_clicked(self, button) -> None:
        self.on_delete()


class PluginItem(Adw.ActionRow):
    __gtype_name__ = "PluginItem"

    def __init__(self, plugin_config: dict, on_properties: typing.Callable[[], None]):
        super().__init__()

        self.on_properties = on_properties
        self.plugin_config = plugin_config
        self.set_activatable(False)

        self.set_title(_(plugin_config["meta"]["name"]))

        self.img_plugin_icon = Gtk.Image()
        self.img_plugin_icon.set_valign(Gtk.Align.CENTER)
        self.add_prefix(self.img_plugin_icon)

        self.switch_enable = Gtk.Switch()
        self.switch_enable.set_valign(Gtk.Align.CENTER)
        self.switch_enable.set_active(plugin_config["enabled"])
        self.add_suffix(self.switch_enable)

        self.btn_disable_errored = Gtk.Button.new_from_icon_name(
            "edit-delete-symbolic"
        )
        self.btn_disable_errored.add_css_class("flat")
        self.btn_disable_errored.add_css_class("destructive-action")
        self.btn_disable_errored.set_valign(Gtk.Align.CENTER)
        self.btn_disable_errored.set_visible(False)
        self.btn_disable_errored.connect("clicked", self.on_disable_errored)
        self.add_suffix(self.btn_disable_errored)

        self.btn_properties = Gtk.Button.new_from_icon_name(
            "document-properties-symbolic"
        )
        self.btn_properties.add_css_class("flat")
        self.btn_properties.set_valign(Gtk.Align.CENTER)
        self.btn_properties.connect("clicked", self.on_properties_clicked)
        self.add_suffix(self.btn_properties)

        self.btn_plugin_extra_link = Gtk.LinkButton.new_with_label(
            "https://slgobinath.github.io/safeeyes",
            _("Click here for more information"),
        )
        self.btn_plugin_extra_link.set_valign(Gtk.Align.CENTER)
        self.btn_plugin_extra_link.set_visible(False)
        self.add_suffix(self.btn_plugin_extra_link)

        if plugin_config["error"]:
            message = plugin_config["meta"]["dependency_description"]
            if isinstance(message, PluginDependency):
                self.set_subtitle(_(message.message))
                if message.link is not None:
                    self.btn_plugin_extra_link.set_uri(message.link)
                self.btn_plugin_extra_link.set_visible(True)
            else:
                self.set_subtitle(_(message))
            self.switch_enable.set_sensitive(False)
            self.btn_properties.set_sensitive(False)
            if plugin_config["enabled"]:
                self.btn_disable_errored.set_visible(True)
        else:
            self.set_subtitle(_(plugin_config["meta"]["description"]))
            if plugin_config["settings"]:
                self.btn_properties.set_sensitive(True)
            else:
                self.btn_properties.set_sensitive(False)

        if plugin_config["icon"]:
            self.img_plugin_icon.set_from_file(plugin_config["icon"])
        else:
            self.img_plugin_icon.set_icon_name("application-x-addon-symbolic")

    def is_enabled(self) -> bool:
        return self.switch_enable.get_active()

    def on_disable_errored(self, button) -> None:
        """Permanently disable errored plugin."""
        self.btn_disable_errored.set_sensitive(False)
        self.switch_enable.set_active(False)

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
