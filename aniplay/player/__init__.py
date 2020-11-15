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

from gi.repository import GLib, Gdk

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

        # Init Pipeline
        self._pipeline = Pipeline()
        self.video_widget = self._pipeline.get_widget()
        self.window.player_video_area.add(self.video_widget)
        self.video_widget.show()

        self._controls = Controls(self)

    def quit(self):
        self._pipeline.stop()
        self.window.player_video_area.remove(self.video_widget)
        self._controls.quit()
        self.disconnect()

    def play(self, uri, title, subtitle):
        self.window.headerbar_fullscreen_button.show()
        self.window.headerbar_volume_button.show()
        self.window.headerbar_player_title.set_text(title)
        self.window.headerbar_player_subtitle.set_text(subtitle)

        self.connect()

        self._pipeline.set_uri(uri)

        # Autoplay
        self._pipeline.play()
        self._controls.update_buttons_pause()

    def connect(self):
        self._on_map_signal = self.window.connect('map-event', self._on_map)
        self._on_key_press_signal = self.window.connect('key_press_event', self._on_key_press)
        self._on_window_state_event_signal = self.window.connect('window-state-event', self._on_window_state_event)

        self._player_on_mouse_move_signal = self.window.connect('motion_notify_event', self._on_mouse_move)
        self._headerbar_fullscreen_button_signal = self.window.headerbar_fullscreen_button.connect('clicked', self.toggle_fullscreen)
        self._headerbar_left_button_signal = self.window.headerbar_left_button.connect('clicked', self._headerbar_on_back_button_clicked)

        self._on_pipeline_play_signal = self._pipeline.connect('play', self._on_pipeline_play)
        self._on_pipeline_pause_signal = self._pipeline.connect('pause', self._on_pipeline_pause)

        self._controls.connect()

    def disconnect(self):
        self.window.disconnect(self._on_map_signal)
        self.window.disconnect(self._on_key_press_signal)
        self.window.disconnect(self._on_window_state_event_signal)

        self.window.disconnect(self._player_on_mouse_move_signal)
        self.window.headerbar_fullscreen_button.disconnect(self._headerbar_fullscreen_button_signal)
        self.window.headerbar_left_button.disconnect(self._headerbar_left_button_signal)

        self._pipeline.disconnect(self._on_pipeline_play_signal)
        self._pipeline.disconnect(self._on_pipeline_pause_signal)

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
            self.window.headerbar_revealer.add(self.window.headerbar)
            self._headerbar_fade_in()

    def _set_unfullscreen(self):
        if self.is_fullscreen:
            self.window.headerbar_revealer.remove(self.window.headerbar)
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
        self._player_on_mouse_move_timeout_signal_id = GLib.timeout_add_seconds(CONTROLS_FADE_OUT_TIMEOUT_SECONDS, self._controls.fade_out)

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

        if self._player_on_mouse_move_timeout_signal_id > 0:
            GLib.source_remove(self._player_on_mouse_move_timeout_signal_id)
            self._player_on_mouse_move_timeout_signal_id = 0
        if self._pipeline.is_playing():
            self._player_on_mouse_move_timeout_signal_id = GLib.timeout_add_seconds(CONTROLS_FADE_OUT_TIMEOUT_SECONDS, self._controls.fade_out)

        if self.is_fullscreen and event.y_root < 10:
            self._headerbar_fade_in()

    def _headerbar_fade_in(self):
        self.window.headerbar_revealer.set_reveal_child(True)

        if self._headerbar_on_mouse_move_timeout_signal_id > 0:
            GLib.source_remove(self._headerbar_on_mouse_move_timeout_signal_id)
        self._headerbar_on_mouse_move_timeout_signal_id = GLib.timeout_add_seconds(CONTROLS_FADE_OUT_TIMEOUT_SECONDS, self._headerbar_fade_out)

    def _headerbar_fade_out(self):
        self.window.headerbar_revealer.set_reveal_child(False)
        self._headerbar_on_mouse_move_timeout_signal_id = 0
        return False

    def _headerbar_on_back_button_clicked(self, widget):
        self.window.headerbar_fullscreen_button.hide()
        self.window.headerbar_volume_button.hide()
        self.window.go_back()
        
