import sys
sys.path.append('..')
from common.core import *
from common.audio import *
from common.mixer import *
from common.wavegen import *
from common.wavesrc import *
from common.gfxutil import *

from kivy.graphics.instructions import InstructionGroup
from kivy.graphics import Color, Ellipse, Line, Rectangle
from kivy.graphics import PushMatrix, PopMatrix, Translate, Scale, Rotate
from kivy.clock import Clock as kivyClock

import random
import numpy as np
import bisect

from common.leaputil import *
import Leap

num_seconds = 3  # how long it takes for lines to move from center to bars

class MainWidget(BaseWidget) :
    def __init__(self):
        super(MainWidget, self).__init__()

        self.song_data = SongData()
        gem_data = self.song_data.read_gem_data('../data/gem_data.txt')
        barline_times = self.song_data.read_barline_data('../data/barline_data.txt')
        self.display = BeatMatchDisplay(gem_data, barline_times, self.on_end_game)
        self.canvas.add(self.display)

        self.audio_ctrl = AudioController('../data/SmokeOnTheWater')
        self.audio_ctrl.toggle()
        self.audio = self.audio_ctrl.audio

        self.player = Player(gem_data, self.display, self.audio_ctrl)

        self.label = topleft_label()
        self.add_widget(self.label)

        self.leap = Leap.Controller()

        # set up size / location of 3DCursor object
        kMargin = Window.width * 0.05
        kCursorSize = Window.width - 2 * kMargin, Window.height - 2 * kMargin
        kCursorPos = kMargin, kMargin

        self.left_hand_disp = Cursor3D(kCursorSize, kCursorPos, (.2, .2, .6))
        self.canvas.add(self.left_hand_disp)

        self.right_hand_disp = Cursor3D(kCursorSize, kCursorPos, (.2, .6, .2))
        self.canvas.add(self.right_hand_disp)
        
        self.left_hand_pos = [0,0,0]
        self.right_hand_pos = [0,0,0]


    def on_key_down(self, keycode, modifiers):
        # play / pause toggle
        if keycode[1] == 'p':
            self.audio_ctrl.toggle()

        # button down
        button_idx = lookup(keycode[1], '12345', (0,1,2,3,4))
        if button_idx is not None:
            self.player.on_button_down(button_idx)

    def on_key_up(self, keycode):
        # button up
        button_idx = lookup(keycode[1], '12345', (0,1,2,3,4))
        if button_idx is not None:
            self.player.on_button_up(button_idx)

    def on_end_game(self):
        self.audio_ctrl.on_end_game()
        self.display.on_end_game()
        self.player.on_end_game()

    def on_update(self):
        leap_frame = self.leap.frame()
        pts = list(leap_two_palms(leap_frame))
        # pts.sort(key=lambda pt: pt[0])  # sort by increasing x (hand with smaller x is first)
        norm_pts = [scale_point(pt, kLeapRange) for pt in pts]
        self.left_hand_pos = norm_pts[0]
        self.right_hand_pos = norm_pts[1]
        self.left_hand_disp.set_pos(self.left_hand_pos)
        self.right_hand_disp.set_pos(self.right_hand_pos)

        frame = self.audio_ctrl.get_frame()
        self.display.on_update(frame)
        self.audio_ctrl.on_update()
        self.player.on_update()
        self.label.text = ''
        self.label.text += 'Score: %s\n' % (self.player.score)


# creates the Audio driver
# creates a song and loads it with solo and bg audio tracks
# creates snippets for audio sound fx
class AudioController(object):
    def __init__(self, song_path):  # song_path is without the "_bg.wav", "_solo.wav"
        super(AudioController, self).__init__()
        self.audio = Audio(2)
        self.mixer = Mixer()
        self.mixer.set_gain(0.2)
        self.audio.set_generator(self.mixer)
        self.song_path = song_path
        
        self.wave_file_bg = WaveFile(song_path + "_bg.wav")
        self.wave_gen_bg = WaveGenerator(self.wave_file_bg)
        self.mixer.add(self.wave_gen_bg)
        
        self.wave_file_solo = WaveFile(song_path +  "_solo.wav")
        self.wave_gen_solo = WaveGenerator(self.wave_file_solo)
        self.mixer.add(self.wave_gen_solo)

    # start / stop the song
    def toggle(self):
        self.wave_gen_bg.play_toggle()
        self.wave_gen_solo.play_toggle()

    # mute / unmute the solo track
    def set_mute(self, mute):
        if mute:
            self.wave_gen_solo.set_gain(0)
        else:
            self.wave_gen_solo.set_gain(1)

    # play a sound-fx (miss sound)
    def play_sfx(self):
        buffers = make_wave_buffers("../data/mario.wav", "../data/miss_region.txt")
        miss_buffer = buffers['miss']
        gen = WaveGenerator(miss_buffer)
        self.mixer.add(gen)

    def get_frame(self):
        return self.wave_gen_bg.frame

    def on_end_game(self):  # reset
        self.wave_gen_bg.reset()
        self.wave_gen_solo.reset()
        self.wave_gen_solo.set_gain(1)

    # needed to update audio
    def on_update(self):
        self.audio.on_update()


# holds data for gems and barlines.
class SongData(object):
    def __init__(self):
        super(SongData, self).__init__()

    # read the gems and song data. You may want to add a secondary filepath
    # argument if your barline data is stored in a different txt file.
    def read_gem_data(self, filepath):
        f = open(filepath)
        lines = f.readlines()
        gems = []
        for line in lines:
            tokens = line.strip().split('\t')
            time = float(tokens[0])
            if time > num_seconds:
                button = int(tokens[1])
                gems.append((time, button))
        return gems

    def read_barline_data(self, filepath):
        f = open(filepath)
        lines = f.readlines()
        times = []
        for line in lines:
            tokens = line.strip().split('\t')
            time = float(tokens[0])
            if time > num_seconds:
                times.append(time)
        return times
    # TODO: figure out how gem and barline data should be accessed...

bar_y = 80
gem_r = 30

# display for a single gem at a position with a color (if desired)
class GemDisplay(InstructionGroup):
    def __init__(self, pos, color):
        super(GemDisplay, self).__init__()
        self.x = pos[0]
        self.orig_a = 0.5

        self.color = Color(color[0], color[1], color[2], self.orig_a)
        self.add(self.color)

        self.circle = CEllipse(cpos = pos, size = (2*gem_r, 2*gem_r), segments = 40)
        self.add(self.circle)

        self.time = 0
        self.hit = False
        self.size_anim = None

    # change to display this gem being hit
    def on_hit(self):
        self.color.a = 1
        self.hit = True
        self.size_anim = KFAnim((0, 2*gem_r), (1, 4*gem_r))
        self.time = 0
        self.on_update(0)

    # change to display a passed gem
    def on_pass(self):
        self.color.a = 0.2  # decrease color alpha

    def set_y(self, y):
        if not self.hit:
            self.circle.cpos = (self.x, y)

    # useful if gem is to animate
    def on_update(self, dt):
        if self.hit:
            size = self.size_anim.eval(self.time)
            self.circle.set_csize((size, size))
            self.time += dt
            return self.size_anim.is_active(self.time)
        return True


# display for a single barline
class BarlineDisplay(InstructionGroup):
    def __init__(self):
        super(BarlineDisplay, self).__init__()
        color = (192/255, 192/255, 192/255, 0.5)
        self.color = Color(*color)
        self.add(self.color)

        line_pts = [0, Window.height, Window.width, Window.height]
        self.line = Line(points=line_pts, width = 1)
        self.add(self.line)

    def set_y(self, y):
        self.line.points = [0, y, Window.width, y]

    def on_update(self, dt):
        return True


# Displays one button on the nowbar
class ButtonDisplay(InstructionGroup):
    def __init__(self, pos, color):
        super(ButtonDisplay, self).__init__()

        self.orig_a = 0.5

        self.color = Color(color[0], color[1], color[2], self.orig_a)
        self.add(self.color)

        self.circle = CEllipse(cpos = pos, size = (2*gem_r, 2*gem_r), segments = 40)
        self.add(self.circle)

        self.miss_color = Color(0, 0, 0, 1)
        self.miss_circle = CEllipse(cpos = pos, size = (1.5*gem_r, 1.5*gem_r), segments = 40)

        self.miss = True

    # displays when button is down (and if it hit a gem)
    def on_down(self, hit):
        if hit:
            self.color.a = 1
        else:
            self.miss = True
            self.add(self.miss_color)
            self.add(self.miss_circle)

    # back to normal state
    def on_up(self):
        self.color.a = self.orig_a
        if self.miss:
            self.remove(self.miss_color)
            self.remove(self.miss_circle)
            self.miss = False


class Translate(InstructionGroup):
    def __init__(self):
        super(Translate, self).__init__()
        self.anim_group = AnimGroup()
        self.obj_anims = []
        self.obj_index = 0
        self.add(self.anim_group)

    def add_obj(self, obj, second):
        self.anim_group.add(obj)
        y_anim = KFAnim((second, Window.height), (second + num_seconds / (Window.height - bar_y) * Window.height, 0))
        self.obj_anims.append((obj, y_anim))

    def on_end_game(self):  # reset
        self.obj_anims = []
        self.anim_group.clear()
        self.obj_index = 0

    def on_update(self, second):
        new_obj_index = self.obj_index
        for i in range(self.obj_index, len(self.obj_anims)):
            obj, y_anim = self.obj_anims[i]
            y = y_anim.eval(second)
            obj.set_y(y)
            if y == 0:
                new_obj_index = i
                self.anim_group.remove(obj)
        self.obj_index = new_obj_index
        self.anim_group.on_update()


# Displays and controls all game elements: Nowbar, Buttons, BarLines, Gems.
class BeatMatchDisplay(InstructionGroup):
    def __init__(self, gem_data, barline_times, end_game_callback):
        super(BeatMatchDisplay, self).__init__()
        self.now_bar_color = (1, 1, 1, 0.5)
        line_pts = [0, bar_y, Window.width, bar_y]
        self.now_bar = Line(points=line_pts, width=5)
        
        self.add(Color(*self.now_bar_color))
        self.add(self.now_bar)

        x_s = [ Window.width / 5 * i + Window.width / 10 for i in range(5) ]
        # pastels red, orange, yellow, green, blue
        rgb_colors = [(255,179,186), (255,223,186), (255,255,186), (186,255,201), (186,225,255)]
        self.colors = [[rgb/255 for rgb in rgb_color] for rgb_color in rgb_colors]
        self.buttons = [ ButtonDisplay((x_s[i], bar_y), self.colors[i]) for i in range(len(x_s)) ]
        for button in self.buttons:
            self.add(button)

        self.gem_data = gem_data
        self.gem_index = 0
        self.barline_times = barline_times
        self.barline_index = 0

        self.gems = []

        self.trans = Translate()
        self.add(self.trans)

        self.end_game_callback = end_game_callback

    # called by Player. Causes the right thing to happen
    def gem_hit(self, gem_idx):
        if gem_idx < len(self.gems):
            self.gems[gem_idx].on_hit()

    # called by Player. Causes the right thing to happen
    def gem_pass(self, gem_idx):
        if gem_idx < len(self.gems):
            self.gems[gem_idx].on_pass()

    # called by Player. Causes the right thing to happen
    def on_button_down(self, lane, hit):
        self.buttons[lane].on_down(hit)

    # called by Player. Causes the right thing to happen
    def on_button_up(self, lane):
        self.buttons[lane].on_up()

    def on_end_game(self):
        self.clear()
        self.gem_index = 0
        self.barline_index = 0
        self.trans.on_end_game()

    # call every frame to make gems and barlines flow down the screen
    def on_update(self, frame):
        second = frame / Audio.sample_rate
        if self.gem_index < len(self.gem_data):
            gem_time, gem_lane = self.gem_data[self.gem_index]
            if gem_time - num_seconds < second:
                gem = GemDisplay((Window.width / 5 * gem_lane + Window.width / 10, Window.height), self.colors[gem_lane])
                self.gems.append(gem)
                self.trans.add_obj(gem, second)
                self.gem_index += 1
        if self.barline_index < len(self.barline_times):
            barline_time = self.barline_times[self.barline_index]
            if barline_time - num_seconds < second:
                self.trans.add_obj(BarlineDisplay(), second)
                self.barline_index += 1
        else:  # End game when no more barlines
            self.end_game_callback()
        self.trans.on_update(second)


# Handles game logic and keeps score.
# Controls the display and the audio
class Player(object):
    def __init__(self, gem_data, display, audio_ctrl):
        super(Player, self).__init__()
        self.score = 0
        self.gem_data = gem_data
        self.display = display
        self.audio_ctrl = audio_ctrl
        self.pass_gem_index = -1  # most recent gem that went past the slop window
        self.slop_window = 0.1 # +-100 ms

    # called by MainWidget
    def on_button_down(self, lane):
        second = self.audio_ctrl.get_frame() / Audio.sample_rate
        hit = False
        gem_index = self.pass_gem_index + 1
        new_pass_gem_index = self.pass_gem_index
        while gem_index < len(self.gem_data) and self.gem_data[gem_index][0] <= second + self.slop_window:
            gem_lane = self.gem_data[gem_index][1]
            # TODO: edit to use tapping gestures
            if gem_lane == lane:  # Hit
                hit = True
                self.display.gem_hit(gem_index)
                self.score += 1
            else: # Else, it's a Lane miss
                self.display.gem_pass(gem_index)  # gem can no longer by hit
            new_pass_gem_index = gem_index
            gem_index += 1
        self.pass_gem_index = new_pass_gem_index
        self.display.on_button_down(lane, hit)
        self.audio_ctrl.set_mute(not hit)
        if not hit:  # Temporal miss or Lane miss
            self.audio_ctrl.play_sfx()

    # called by MainWidget
    def on_button_up(self, lane):
        self.display.on_button_up(lane)

    def on_end_game(self):
        self.score = 0
        self.pass_gem_index = -1

    # needed to check if for pass gems (ie, went past the slop window)
    def on_update(self):
        second = self.audio_ctrl.get_frame() / Audio.sample_rate
        gem_index = self.pass_gem_index + 1
        while gem_index < len(self.gem_data) and self.gem_data[gem_index][0] <= second - self.slop_window:
            self.display.gem_pass(gem_index)
            self.audio_ctrl.set_mute(True)
            gem_index += 1
        self.pass_gem_index = gem_index - 1


# for use with scale_point:
# x, y, and z ranges to define a 3D bounding box
kLeapRange   = ( (-250, 250), (100, 500), (-200, 250) )

run(MainWidget)
