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

class Controls:
    _position = 0
    _duration = 0

    def __init__(self, player):
        self.player = player
        self.window = self.player.window

    def quit(self):
        self.window.player_video_position_adjustment.set_value(0)
        self.window.player_actionbar_position_label.set_text('00:00')
        self.disconnect()

    def connect(self):
        self._player_play_button_signal = self.window.player_play_button.connect('clicked', self._on_play_button_clicked)
        self._player_action_bar_play_button_signal = self.window.player_action_bar_play_button.connect('clicked', self._on_play_button_clicked)
        self._player_volume_adjustment_signal = self.window.player_volume_adjustment.connect('value-changed', self._on_volume_adjustment_change)
        self._player_video_position_adjustment_signal = self.window.player_video_position_adjustment.connect('value-changed', self._on_video_position_adjustment_change)

        self._pipeline_on_volume_signal_id = self.player._pipeline.connect('volume', self._pipeline_on_volume)
        self._pipeline_on_duration_signal_id = self.player._pipeline.connect('duration', self._pipeline_on_duration)
        self._pipeline_on_position_signal_id = self.player._pipeline.connect('position', self._pipeline_on_position)

    def disconnect(self):
        self.window.player_play_button.disconnect(self._player_play_button_signal)
        self.window.player_action_bar_play_button.disconnect(self._player_action_bar_play_button_signal)
        self.window.player_volume_adjustment.disconnect(self._player_volume_adjustment_signal)
        self.window.player_video_position_adjustment.disconnect(self._player_video_position_adjustment_signal)

        self.player._pipeline.disconnect(self._pipeline_on_volume_signal_id)
        self.player._pipeline.disconnect(self._pipeline_on_duration_signal_id)
        self.player._pipeline.disconnect(self._pipeline_on_position_signal_id)

    def fade_in(self):
        self.window.player_action_bar_revealer.set_reveal_child(True)
        self.window.player_video_area_button_revealer.set_reveal_child(True)

    def fade_out(self):
        self.window.player_action_bar_revealer.set_reveal_child(False)
        self.window.player_video_area_button_revealer.set_reveal_child(False)
        self.player._player_on_mouse_move_timeout_signal_id = 0
        return False

    def update_buttons_play(self):
        self.window.player_action_bar_play_button_image.set_from_icon_name('media-playback-start-symbolic', Gtk.IconSize.BUTTON)
        self.window.player_play_button_image.set_from_icon_name('media-playback-start-symbolic', Gtk.IconSize.DIALOG)

    def update_buttons_pause(self):
        self.window.player_action_bar_play_button_image.set_from_icon_name('media-playback-pause-symbolic', Gtk.IconSize.BUTTON)
        self.window.player_play_button_image.set_from_icon_name('media-playback-pause-symbolic', Gtk.IconSize.DIALOG)

    def _on_play_button_clicked(self, widget):
        self.player._play_pause()

    def _on_volume_adjustment_change(self, widget):
        self.player._pipeline.set_volume(widget.get_value() / 100)

    def _on_video_position_adjustment_change(self, widget):
        position = widget.get_value() * self._duration / 100
        if abs(self._position - position) > 1:
            self.player._pipeline.seek(position)

    def _pipeline_on_volume(self, event, vol):
        self.window.player_volume_adjustment.set_value(vol*100)

    def _pipeline_on_duration(self, event, dur):
        hour, minutes, seconds = (dur//60)//60, (dur//60)%60, dur%60
        text = '' if hour == 0 else '{:02d}:'.format(hour)
        self.window.player_actionbar_duration_label.set_text('{}{:02d}:{:02d}'.format(text, minutes, seconds))

    def _pipeline_on_position(self, event, pos):
        try:
            self._duration = self.player._pipeline.get_duration()
            self._position = pos
            hour, minutes, seconds = (pos//60)//60, (pos//60)%60, pos%60
            if hour == 0:
                if (self._duration//60)//60 > 0:
                    text = '00:'
                else:
                    text = ''
            else:
                text = '{:02d}:'.format(hour)

            self.window.player_actionbar_position_label.set_text('{}{:02d}:{:02d}'.format(text, minutes, seconds))

            value = 100 * pos / self._duration
            if abs(value - self.window.player_video_position_adjustment.get_value()) <= 1:
                self.window.player_video_position_adjustment.set_value(100*pos/self._duration)
        except:
            self.window.player_actionbar_position_label.set_text('00:00')
            self.window.player_video_position_adjustment.set_value(0)
