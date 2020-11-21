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
import time

import gi

from gi.repository import Gtk
from gi.repository import GLib
from gi.repository import Gdk

from aniplay.player.controls import Controls
from aniplay.player.pipeline import Pipeline

CONTROLS_FADE_OUT_TIMEOUT_SECONDS = 2

class Player:
    is_maximized = False
    is_fullscreen = False
    _previous_size = None
    _previous_position = None
    _previous_maximize = False

    _player_on_mouse_move_timeout_signal_id = 0
    _headerbar_on_mouse_move_timeout_signal_id = 0

    def __init__(self, window):
        self.window = window

        self._get_widgets()

        # Init Pipeline
        self._pipeline = Pipeline()
        self.gst_widget = self._pipeline.get_widget()
        self.overlay.add(self.gst_widget)
        self.gst_widget.show()

        self._controls = Controls(self)
        self._register_connectors()

    def prepare_page(self):
        self.headerbar_fullscreen_button.show()
        self.headerbar_volume_button.show()
        self.headerbar_left_button_image.set_from_icon_name('go-previous-symbolic', Gtk.IconSize.BUTTON)

        self._on_map_signal_id = self.window.connect('map-event', self._on_map)
        self._on_key_press_signal_id = self.window.connect('key_press_event', self._on_key_press)
        self._on_window_state_event_signal_id = self.window.connect('window-state-event', self._on_window_state_event)
        self._on_mouse_move_signal_id = self.window.connect('motion_notify_event', self._on_mouse_move)
        self._on_headerbar_left_button_cicked_signal_id = self.headerbar_left_button.connect('clicked', self._headerbar_on_left_button_clicked)


        self._controls.prepare_page()

    def close_page(self):
        self._pipeline.stop()
        self.headerbar_fullscreen_button.hide()
        self.headerbar_volume_button.hide()

        self.window.disconnect(self._on_map_signal_id)
        self.window.disconnect(self._on_key_press_signal_id)
        self.window.disconnect(self._on_window_state_event_signal_id)
        self.window.disconnect(self._on_mouse_move_signal_id)
        self.headerbar_left_button.disconnect(self._on_headerbar_left_button_cicked_signal_id)

        self._controls.close_page()

    def _get_widgets(self):
        # headerbar
        self.headerbar_fullscreen_button = self.window.headerbar_player_fullscreen_button
        self.headerbar_volume_button = self.window.headerbar_player_volume_button
        self.headerbar_left_button = self.window.headerbar_left_button
        self.headerbar_left_button_image = self.window.headerbar_left_button_image
        self.headerbar_title_label = self.window.headerbar_player_title_label
        self.headerbar_subtitle_label = self.window.headerbar_player_subtitle_label

        # page
        self.overlay = self.window.player_overlay
        self.overlay_headerbar_revealer = self.window.player_headerbar_revealer
        # Player Mid
        self.mid_revealer = self.window.player_mid_revealer
        self.play_button = self.window.player_play_button
        self.play_button_image = self.window.player_play_button_image
        # Player Bottom
        self.bottom_revealer = self.window.player_bottom_revealer
        self.position_label = self.window.player_position_label
        self.seekbar = self.window.player_seekbar
        self.duration_label = self.window.player_duration_label

    def _register_connectors(self):
        self.headerbar_fullscreen_button.connect('clicked', self.toggle_fullscreen)

        self._pipeline.connect('play', self._on_pipeline_play)
        self._pipeline.connect('pause', self._on_pipeline_pause)

    def play(self, uri, suburi, title, subtitle):
        self.headerbar_title_label.set_text(title)
        self.headerbar_subtitle_label.set_text(subtitle)

        self._pipeline.set_uri(uri, suburi)

        # Autoplay
        self._pipeline.play()
        self._controls.update_buttons_pause()

    def toggle_fullscreen(self, *args):
        if self.is_fullscreen:
            self._set_unfullscreen()
        else:
            self._set_fullscreen()

    def _set_fullscreen(self):
        if not self.is_fullscreen:
            self._previous_size = self.window.get_size()
            self._previous_position = self.window.get_position()
            self._previous_maximize = self.is_maximized

            self.window.fullscreen()
            self.window.remove(self.window.headerbar)
            self.overlay_headerbar_revealer.add(self.window.headerbar)
            self._headerbar_fade_in()

    def _set_unfullscreen(self):
        if self.is_fullscreen:
            self.overlay_headerbar_revealer.remove(self.window.headerbar)
            self.window.set_titlebar(self.window.headerbar)
            self.window.unfullscreen()

    def _play_pause(self):
        if self._pipeline.is_playing():
            self._controls.update_buttons_play()
            self._pipeline.pause()
        else:
            self._controls.update_buttons_pause()
            self._pipeline.play()

    def _on_map(self, widget, event):
        # Prevent error on start up
        if not self._previous_size or not self._previous_position:
            return

        if not self._previous_maximize:
            self.window.unmaximize()

        # Restore size from before fullscreen
        w, h = self._previous_size
        self.window.resize(w, h)

        # Restore position
        x, y = self._previous_position
        self.window.move(x, y)

    def _on_window_state_event(self, widget, event):
        self.is_maximized = bool(event.new_window_state & Gdk.WindowState.MAXIMIZED)
        self.is_fullscreen = bool(event.new_window_state & Gdk.WindowState.FULLSCREEN)

    def _on_pipeline_play(self, event):
        self._on_mouse_move_timeout_signal_id = GLib.timeout_add_seconds(CONTROLS_FADE_OUT_TIMEOUT_SECONDS, self._controls.fade_out)

    def _on_pipeline_pause(self, event):
        self._controls.fade_in()

    def _on_key_press(self, widget, event):
        keycode = event.get_keycode()[1]

        # F
        if keycode == 41:
            self.toggle_fullscreen()
        # Space
        elif keycode == 65:
            self._play_pause()

    def _on_mouse_move(self, widget, event):
        self._controls.fade_in()

        if self._on_mouse_move_timeout_signal_id > 0:
            GLib.source_remove(self._on_mouse_move_timeout_signal_id)
            self._on_mouse_move_timeout_signal_id = 0
        if self._pipeline.is_playing():
            self._on_mouse_move_timeout_signal_id = GLib.timeout_add_seconds(CONTROLS_FADE_OUT_TIMEOUT_SECONDS, self._controls.fade_out)

        if self.is_fullscreen and event.y_root < 10:
            self._headerbar_fade_in()

    def _headerbar_fade_in(self):
        self.overlay_headerbar_revealer.set_reveal_child(True)

        if self._headerbar_on_mouse_move_timeout_signal_id > 0:
            GLib.source_remove(self._headerbar_on_mouse_move_timeout_signal_id)
        self._headerbar_on_mouse_move_timeout_signal_id = GLib.timeout_add_seconds(CONTROLS_FADE_OUT_TIMEOUT_SECONDS, self._headerbar_fade_out)

    def _headerbar_fade_out(self):
        self.overlay_headerbar_revealer.set_reveal_child(False)
        self._headerbar_on_mouse_move_timeout_signal_id = 0
        return False

    def _headerbar_on_left_button_clicked(self, widget):
        if self.is_fullscreen:
            self._set_unfullscreen()

        def back_page():
            self.window.back_page()
            return False

        GLib.timeout_add(250, back_page)
        
