# window.py
#
# Copyright 2020 Lucas Campos Vieira
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
import gi

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk
from gi.repository import GLib

from aniplay.library import Library
from aniplay.player import Player

class PageNotFound(Exception):
    pass

@Gtk.Template(resource_path='/com/github/lucasscvvieira/aniplay/ui/window.ui')
class AniplayWindow(Gtk.ApplicationWindow):
    __gtype_name__ = 'AniplayWindow'

    # adjustment
    player_video_position_adjustment = Gtk.Template.Child()
    player_volume_adjustment = Gtk.Template.Child()

    # Headerbar
    headerbar = Gtk.Template.Child()
    headerbar_title_stack = Gtk.Template.Child()
    headerbar_menu_button = Gtk.Template.Child()
    headerbar_left_button = Gtk.Template.Child()
    headerbar_left_button_image = Gtk.Template.Child()

    # Library Headerbar
    headerbar_library_title_label = Gtk.Template.Child()
    headerbar_library_subtitle_label = Gtk.Template.Child()

    # Player Headerbar
    headerbar_player_fullscreen_button = Gtk.Template.Child()
    headerbar_player_volume_button = Gtk.Template.Child()
    headerbar_player_title_label = Gtk.Template.Child()
    headerbar_player_subtitle_label = Gtk.Template.Child()

    # Notification
    notification_overlay = Gtk.Template.Child()
    notification_revealer = Gtk.Template.Child()
    notification_label = Gtk.Template.Child()

    # Page
    page_stack = Gtk.Template.Child()

    # Library Page
    library_url_entry = Gtk.Template.Child()
    library_play_button = Gtk.Template.Child()

    # Player Page
    player_overlay = Gtk.Template.Child()
    player_headerbar_revealer = Gtk.Template.Child()
    # Player Mid
    player_mid_revealer = Gtk.Template.Child()
    player_play_button = Gtk.Template.Child()
    player_play_button_image = Gtk.Template.Child()
    # Player Bottom
    player_bottom_revealer = Gtk.Template.Child()
    player_position_label = Gtk.Template.Child()
    player_seekbar = Gtk.Template.Child()
    player_duration_label = Gtk.Template.Child()

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self._page_order = []
        self._pages = {
            'library': Library(self),
            'player': Player(self),
        }

        self.headerbar_player_volume_button.hide()

        # initiate in libraby page
        self.go_page('library')

    def get_page(self, name):
        if name not in self._pages.keys():
            raise PageNotFound
        return self._pages[name]

    def go_page(self, page_name):
        try:
            page = self.get_page(page_name)
        except PageNotFound:
            self.show_notification("Page not found!")
        else:
            try:
                prev_page_name = self._page_order[-1]
                prev_page = self.get_page(prev_page_name)
            except PageNotFound:
                exit(1)
            except IndexError:
                pass
            else:
                prev_page.close_page()

            self._page_order.append(page_name)
            page.prepare_page()
            self.headerbar_title_stack.set_visible_child_name(page_name)
            self.page_stack.set_visible_child_name(page_name)

    def back_page(self):
        page_name = self._page_order.pop(-1)

        # close previous page
        try:
            page = self.get_page(page_name)
            page.close_page()
        except PageNotFound:
            exit(1)

        # open page
        try:
            prev_page_name = self._page_order[-1]
            prev_page = self.get_page(prev_page_name)
        except PageNotFound:
            exit(1)
        except IndexError:
            self.show_notification("Root page can't go back!")
            self._page_order.append(page_name)
        else:
            prev_page.prepare_page()
            self.headerbar_title_stack.set_visible_child_name(prev_page_name)
            self.page_stack.set_visible_child_name(prev_page_name)

    def show_notification(self, string, interval=5):
        self.notification_label.set_text(string)
        self.notification_revealer.set_reveal_child(True)
        GLib.timeout_add_seconds(interval, self.hide_notification)

    def hide_notification(self):
        self.notification_revealer.set_reveal_child(False)
        return False # disable timeout
