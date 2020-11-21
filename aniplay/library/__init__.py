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
import cloudscraper
import requests
import json
import re
import os
import pysubs2
from collections import OrderedDict

import gi

from gi.repository import Gtk
from gi.repository import GLib

class Library:
    def __init__(self, window):
        self.window = window
        self._player = None


        # get ui widgets
        self._get_widgets()

        # connect ui events
        self._register_connectors()

    def prepare_page(self):
        self.headerbar_left_button_image.set_from_icon_name('list-add-symbolic', Gtk.IconSize.BUTTON)

        self._on_headerbar_left_button_cicked_signal_id = self.headerbar_left_button.connect('clicked', self._headerbar_on_left_button_clicked)

    def close_page(self):
        self.headerbar_left_button.disconnect(self._on_headerbar_left_button_cicked_signal_id)

    def _get_player(self):
        if not self._player:
            try:
                self._player = self.window.get_page('player')
            except PageNotFound:
                exit(1)
        return self._player

    def _get_widgets(self):
        # headerbar
        self.headerbar_title_label = self.window.headerbar_library_title_label
        self.headerbar_subtitle_label = self.window.headerbar_library_subtitle_label
        self.headerbar_left_button = self.window.headerbar_left_button
        self.headerbar_left_button_image = self.window.headerbar_left_button_image

        # page
        self.url_entry = self.window.library_url_entry
        self.play_button = self.window.library_play_button

    def _register_connectors(self):
        self.play_button.connect('clicked', self._on_play_button_clicked)

    def _on_play_button_clicked(self, widget):
        url = self.url_entry.get_text()
        try:
            video_info = get_video_info(url)
            if len(video_info) == 0:
                raise Exception("Episode doesn't found!")
        except Exception as e:
            self.window.show_notification(str(e))
        else:
            player = self._get_player()

            suburi = download_subtitle(video_info['suburi'], video_info['subformat'])

            player.play(
                video_info['url'],
                suburi,
                video_info['title'].title(),
                video_info['subtitle'].title())
            self.window.go_page('player')

    def _headerbar_on_left_button_clicked(self, widget):
        pass

def download_subtitle(url, sub_format):
    cache_dir_path = GLib.get_user_cache_dir()
    cache_dir_path = os.path.join(cache_dir_path, 'aniplay')

    if not os.path.exists(cache_dir_path):
        os.mkdir(cache_dir_path)

    subtitle_ass_path = os.path.join(cache_dir_path, 'subtitle.ass')
    subtitle_webvtt_path = os.path.join(cache_dir_path, 'subtitle.vtt')

    print(url)

    req = requests.get(url)
    if req.status_code == 200:
        with open(subtitle_ass_path, 'wb') as fp:
            fp.write(req.content)

        subtitle = pysubs2.load(subtitle_ass_path)

        #for line in subtitle:
        #    print(line.text)

        subtitle.save(subtitle_webvtt_path, format='vtt')
        return 'file://'+subtitle_webvtt_path

def get_video_info(url):
    session = cloudscraper.create_scraper()
    session.headers = {
        'Host': 'www.crunchyroll.com',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; WOW64) Gecko/20100101 Firefox/60',
    }
    req = session.get(url)
    if req.status_code != 200:
        raise Exception('HTTP {}'.format(req.status_code))

    info = dict()
    trailer = False

    r = re.search(
        r'vilos.config.media = (.*);',
        req.text
    )

    if r.groups:
        j = json.loads(r.group(1))
        #print(j)
        for stream in j['streams']:
            if 'm3u8' in stream['url'] and stream['hardsub_lang'] == None:
                if stream['format'] == 'vo_adaptive_hls':
                    info['url'] = stream['url']
                    break
                if stream['format'] == 'trailer_hls':
                    info['url'] = stream['url']
                    trailer = True
                    break
        for subtitle in j['subtitles']:
            if 'ptBR' in subtitle['language']:
                info['suburi'] = subtitle['url']
                info['subformat'] = subtitle['format']
                break

    r = re.findall(
        r'<h4 id="showmedia_about_episode_num">\s*<a href=".*" class="text-link">(.*)<\/a>\s*<\/h4>\s*<h4>\s*(.*)\s*(.*)?<\/h4>|<h4 id="showmedia_about_name" class="strong">&ldquo;(.*)&rdquo;<\/h4>',
        req.text
    )
    if len(r) == 2:
        info['title'] = r[0][0]
        if trailer:
            info['title'] += ' (Trailer)'

        epi = r[0][1]
        if epi[-1] == ',':
            epi = epi[:-1]

        if len(r[0][2]) > 0:
            info['subtitle'] = '{} - {} - {}'.format(epi, r[0][2], r[1][3])
        else:
            info['subtitle'] = '{} - {}'.format(epi, r[1][3])
        return info
