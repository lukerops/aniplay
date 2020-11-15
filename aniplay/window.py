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
import cloudscraper
import json
import re
from collections import OrderedDict

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, Gdk, GLib

from aniplay.player import Player

@Gtk.Template(resource_path='/com/github/lucasscvvieira/aniplay/ui/window.ui')
class AniplayWindow(Gtk.ApplicationWindow):
    __gtype_name__ = 'AniplayWindow'

    # Headerbar
    headerbar = Gtk.Template.Child('headerbar')
    headerbar_revealer = Gtk.Template.Child('headerbar_revealer')
    headerbar_fullscreen_button = Gtk.Template.Child('headerbar_fullscreen_button')
    headerbar_volume_button = Gtk.Template.Child('headerbar_volume_button')
    headerbar_left_button = Gtk.Template.Child('headerbar_left_button')

    # Player headerbar
    headerbar_player_title = Gtk.Template.Child('headerbar_player_title')
    headerbar_player_subtitle = Gtk.Template.Child('headerbar_player_subtitle')

    page_stack = Gtk.Template.Child('page_stack')
    main_page = Gtk.Template.Child('main_page')
    main_button = Gtk.Template.Child('main_button')
    url = Gtk.Template.Child('url')

    player_volume_adjustment = Gtk.Template.Child('player_volume_adjustment')
    player_video_position_adjustment = Gtk.Template.Child('player_video_position_adjustment')
    player_actionbar_position_scale = Gtk.Template.Child('player_actionbar_position_scale')


    player_video_area = Gtk.Template.Child('player_video_area')
    player_video_area_button_revealer = Gtk.Template.Child('player_video_area_button_revealer')
    player_play_button = Gtk.Template.Child('player_play_button')
    player_play_button_image = Gtk.Template.Child('player_play_button_image')


    # ActionBar
    player_action_bar = Gtk.Template.Child('player_action_bar')
    #player_actionbar_volume_button = Gtk.Template.Child('player_actionbar_volume_button')
    player_actionbar_duration_label = Gtk.Template.Child('player_actionbar_duration_label')
    player_actionbar_position_label = Gtk.Template.Child('player_actionbar_position_label')
    player_volume_adjustment = Gtk.Template.Child('player_volume_adjustment')
    player_action_bar_revealer = Gtk.Template.Child('player_action_bar_revealer')
    player_action_bar_play_button = Gtk.Template.Child('player_action_bar_play_button')
    player_action_bar_play_button_image = Gtk.Template.Child('player_action_bar_play_button_image')

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._page_order = [(self.main_page, None)]

        self.headerbar_volume_button.hide()

        #Window
        self.main_button.connect('clicked', self._on_button_clicked)

    def go_back(self):
        page, widget = self._page_order.pop(-1)
        widget.quit()
        self.page_stack.set_visible_child(self._page_order[-1][0])

    def go_page(self, page, widget):
        self._page_order.append((page, widget))
        self.page_stack.set_visible_child(page)

    def _on_button_clicked(self, widget):
        url = self.url.get_text()
        video_info = get_video_info(url)
        if len(video_info) == 0:
            exit(1)
        player = Player(self)
        player.play(video_info['url'], video_info['title'].title(), video_info['subtitle'].title())
        self.go_page(self.player_video_area, player)

def get_video_info(url):
    session = cloudscraper.create_scraper()
    session.headers = headers = OrderedDict(
    [
        ('Host', 'www.crunchyroll.com'),
        ('User-Agent', 'Mozilla/5.0 (Windows NT 10.0; WOW64) Gecko/20100101 Firefox/60'),
        ('Accept', 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8'),
        ('Accept-Language', 'en,en-US;q=0.9'),
        ('Accept-Encoding', 'gzip, deflate, br'),
    ])
    req = session.get(url)
    if req.status_code != 200:
        exit(1)

    info = dict()
    trailer = False

    r = re.search(
        r'vilos.config.media = (.*);',
        req.text
    )

    if r.groups:
        j = json.loads(r.group(1))
        for stream in j['streams']:
            if 'm3u8' in stream['url'] and stream['hardsub_lang'] == 'ptBR':
                if stream['format'] == 'vo_adaptive_hls':
                    info['url'] = stream['url']
                    break
                if stream['format'] == 'trailer_hls':
                    info['url'] = stream['url']
                    trailer = True
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
    
