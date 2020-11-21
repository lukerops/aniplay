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

gi.require_version("Gst", "1.0")
from gi.repository import Gst

gi.require_version('GstVideo', '1.0')
from gi.repository import GstVideo
from gi.repository import GObject
from gi.repository import GLib

class PipelineError(Exception):
    pass

PIPELINE_POSITION_LISTENNING_INTERVAL = 500
PIPELINE_DURATION_LISTENNING_INTERVAL = 250

PIPELINE_SIGNALS = {
    'play': (GObject.SignalFlags.RUN_LAST, None, ()),
    'pause': (GObject.SignalFlags.RUN_LAST, None, ()),
    'stop': (GObject.SignalFlags.RUN_LAST, None, ()),
    'position': (GObject.SignalFlags.RUN_LAST, None, (GObject.TYPE_UINT64,)),
    'duration': (GObject.SignalFlags.RUN_LAST, None, (GObject.TYPE_UINT64,)),
    'volume': (GObject.SignalFlags.RUN_LAST, None, (GObject.TYPE_FLOAT,)),
}

class Pipeline(GObject.Object):
    __gsignals__ = PIPELINE_SIGNALS

    _last_position = None
    _last_duration = None
    _listening_signal_id = 0
    _listening = False

    _seeking = False

    def __init__(self):
        GObject.Object.__init__(self)
        Gst.init(None)

        self._pipeline = Gst.ElementFactory.make('playbin3', 'playbin')

        self.gstbin = Gst.Bin.new('my-bin')

        #videosink = Gst.ElementFactory.make("autovideosink")
        #self.gstbin.add(videosink)
        #pad = videosink.get_static_pad("sink")
        #ghostpad = Gst.GhostPad.new("sink", pad)
        #self.gstbin.add_pad(ghostpad)

        self.gtksink = Gst.ElementFactory.make('gtksink')

        self.gstbin.add(self.gtksink)

        pad = self.gtksink.get_static_pad("sink")
        ghostpad = Gst.GhostPad.new("sink", pad)
        self.gstbin.add_pad(ghostpad)

        self._pipeline.set_property("video-sink", self.gstbin)

        bus = self._pipeline.get_bus()
        bus.add_signal_watch()
        bus.connect("message", self._on_message)

    def set_state(self, state):
        res = self._pipeline.set_state(state)
        if res == Gst.StateChangeReturn.FAILURE:
            # reset to NULL
            self._pipeline.set_state(Gst.State.NULL)
            print('set_state error')

    def is_playing(self):
        return self._pipeline.get_state(1)[1] == Gst.State.PLAYING

    def set_uri(self, uri, suburi):
        self._pipeline.set_property('uri', uri)
        self._pipeline.set_property('suburi', suburi)
        self._pipeline.set_property('subtitle-font-desc', 'DejaVu Sans, bold')

        self._volume = self._pipeline.get_property('volume')
        self.emit('volume', self._volume)

    def get_volume(self):
        return self._volume

    def set_volume(self, volume):
        if 0 <= volume <= 1.5:
            self._volume = volume
            self._pipeline.set_property('volume', volume)

    def play(self):
        self.set_state(Gst.State.PLAYING)
        self.activate_position_listener()
        self.emit('play')

    def pause(self):
        self.set_state(Gst.State.PAUSED)
        self.deactivate_position_listener()
        self.emit('pause')

    def stop(self):
        self.set_state(Gst.State.NULL)
        self.deactivate_position_listener()
        self.emit('stop')

    def seek(self, position):
        duration = self.get_duration()
        if position > duration:
            self.stop()
            return

        ns = position * Gst.SECOND

        if not self._seeking:
            res = self._pipeline.seek_simple(Gst.Format.TIME, Gst.SeekFlags.FLUSH | Gst.SeekFlags.KEY_UNIT, ns)
            if res:
                self._seeking = True

    def get_widget(self):
        return self.gtksink.props.widget

    def get_position(self):
        try:
            res, cur = self._pipeline.query_position(Gst.Format.TIME)
        except Exception as e:
            self.handle_exception(e)
            raise PipelineError("Couldn't get position")

        if res:
            self._last_position = cur / Gst.SECOND
        else:
            raise PipelineError("Position not available")

        return self._last_position

    def get_duration(self):
        try:
            res, cur = self._pipeline.query_duration(Gst.Format.TIME)
        except Exception as e:
            self.handle_exception(e)
            raise PipelineError("Couldn't get position")

        if res:
            if self._last_duration != cur / Gst.SECOND:
                self._last_duration = cur / Gst.SECOND
                self.emit('duration', self._last_duration)
        else:
            raise PipelineError("Position not available")

        return self._last_duration

    def _position_listener_callback(self):
        try:
            try:
                position = self.get_position()
            except PipelineError as e:
                print("Could not get position because:", e)
            else:
                if position != Gst.CLOCK_TIME_NONE:
                    self.emit("position", position)
        finally:
            # Call me again.
            return True

    def _listen_to_position(self, listen=True):
        if listen:
            if self._listening and self._listening_signal_id == 0:
                self._listening_signal_id = GLib.timeout_add(
                    PIPELINE_POSITION_LISTENNING_INTERVAL,
                    self._position_listener_callback)

        elif self._listening_signal_id != 0:
            GLib.source_remove(self._listening_signal_id)
            self._listening_signal_id = 0

    def deactivate_position_listener(self):
        self._listen_to_position(False)
        self._listening = False

    def activate_position_listener(self):
        if self._listening:
            return True
        self._listening = True
        # if we're in playing, switch it on
        self._listen_to_position(True)

    def _on_message(self, bus, message):
        t = message.type
        if t == Gst.MessageType.EOS:
            self._pipeline.set_state(Gst.State.NULL)

        elif t == Gst.MessageType.ERROR:
            self._pipeline.set_state(Gst.State.NULL)
            err, debug = message.parse_error()
            print("Error: %s" % err, debug)

        elif t == Gst.MessageType.ASYNC_DONE:
            self._seeking = False
