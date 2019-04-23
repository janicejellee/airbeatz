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
from kivy.core.text import Label as CoreLabel

import random
import numpy as np
import bisect

from common.leaputil import *
import Leap

num_seconds = 3  # how long it takes for lines to move from center to bars
bottom_y = 100
left_x = Window.width/2-300
right_x = Window.width/2+300
directions = ['up_left', 'left', 'right', 'up_right']
direction_number_map = {
    0: "up_left",
    1: "left",
    2: "right",
    3: "up_right"
}  # labels are numbers 0 to 4 in gem_data.txt, which correspond to the directions

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

    def on_end_game(self):
        self.audio_ctrl.on_end_game()
        self.display.on_end_game()
        self.player.on_end_game()

    # set the hand position as a 3D vector ranging from [0,0,0] to [1,1,1]
    def set_right_hand_pos(self, pos):
        self.right_hand_disp.set_pos(pos)
        screen_pos = self.right_hand_disp.to_screen_coords(pos)
        for tap_gesture in self.player.tap_gestures:
            tap_gesture.set_hand_pos(screen_pos, "right")

    def set_left_hand_pos(self, pos):
        self.left_hand_disp.set_pos(pos)
        screen_pos = self.left_hand_disp.to_screen_coords(pos)
        for tap_gesture in self.player.tap_gestures:
            tap_gesture.set_hand_pos(screen_pos, "left")

    def on_update(self):
        leap_frame = self.leap.frame()
        pts = list(leap_two_palms(leap_frame))
        # pts.sort(key=lambda pt: pt[0])  # sort by increasing x (hand with smaller x is first)
        norm_pts = [scale_point(pt, kLeapRange) for pt in pts]
        self.left_hand_pos = norm_pts[0]
        self.right_hand_pos = norm_pts[1]

        # self.left_hand_disp.set_pos(self.left_hand_pos)
        # self.right_hand_disp.set_pos(self.right_hand_pos)

        self.set_left_hand_pos(self.left_hand_pos)
        self.set_right_hand_pos(self.right_hand_pos)

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
                direction = int(tokens[1])
                gems.append((time, direction))
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


# Perfect, Good, Miss, etc
class AccuracyDisplay(InstructionGroup):
    def __init__(self, accuracy, pos, second):
        super(AccuracyDisplay, self).__init__()
        self.accuracy = accuracy
        font_size = 25
        self.pos = pos
        self.size = (100, 25)
        self.box = Rectangle(pos=pos, size=self.size)
        box_color = Color(0, 0, 0, 0)
        self.add(box_color)
        self.add(self.box)

        label = CoreLabel(text=self.accuracy, font_size=font_size)
        # the label is usually not drawn until needed, so force it to draw
        label.refresh()
        # now access the texture of the label and use it
        texture = label.texture
        if accuracy == "Perfect":
            self.color = Color(0, 1, 0)
        elif accuracy == "Good":
            self.color = Color(1, 127/255, 80/255)
        elif accuracy == "Miss":
            self.color = Color(1, 0, 0)
        self.add(self.color)
        text_pos = list(self.pos[i] + (self.size[i] - texture.size[i]) / 2 for i in range(2))
        self.label = Rectangle(size=texture.size, pos=text_pos, texture=texture)
        self.add(self.label)
        max_time = 2
        self.alpha_anim = KFAnim((second, 1), (second + max_time, 0)) # color disappears
        self.set_second(second)

    def set_second(self, second):
        alpha = self.alpha_anim.eval(second)
        self.color.a = alpha
        return self.alpha_anim.is_active(second)

    def on_update(self, dt):
        return True


# display for a single gem at a position with a color (if desired)
class GemDisplay(InstructionGroup):
    def __init__(self, second, direction):
        super(GemDisplay, self).__init__()
        self.orig_a = 0.5

        # self.color = Color(color[0], color[1], color[2], self.orig_a)
        # self.add(self.color)

        # directions = ['up_left', 'left', 'right', 'up_right']
        # self.direction = random.choice(directions)

        self.time = second
        self.direction = direction

        if self.direction == 'up_left' or self.direction == 'up_right':
            starting_pts = [Window.width/2, Window.height/2, Window.width/2, Window.height/2]
        else:
            starting_pts = [Window.width/2-50, Window.height/2, Window.width/2+50, Window.height/2]

        self.width = 5
        self.line = Line(points=starting_pts, width=self.width)
        colors = {
            'left': Color(255/255, 255/255, 77/255, self.orig_a),
            'right': Color(77/255, 148/255, 255/255, self.orig_a),
            'up_left': Color(255/255, 102/255, 102/255, self.orig_a),
            'up_right': Color(102/255, 255/255, 102/255, self.orig_a)
        }
        self.color = colors[self.direction]
        # self.color = Color(242, 242, 242, self.orig_a)
        self.add(self.color)
        self.add(self.line)

        self.time = second

        num_seconds_to_screen_edge_bottom = num_seconds / (Window.height/2 - bottom_y) * Window.height/2
        num_seconds_to_screen_edge_sides = num_seconds / (Window.width/2 - left_x) * Window.width/2
        if self.direction == 'left':
            self.pos_anim_0 = KFAnim((self.time, Window.width/2, Window.height/2), (self.time + num_seconds_to_screen_edge_bottom, Window.width/2-400, 0))
            self.pos_anim_1 = KFAnim((self.time, Window.width/2, Window.height/2), (self.time + num_seconds_to_screen_edge_bottom, Window.width/2-100, 0))
        elif self.direction == 'right':
            self.pos_anim_0 = KFAnim((self.time, Window.width/2, Window.height/2), (self.time + num_seconds_to_screen_edge_bottom, Window.width/2+400, 0))
            self.pos_anim_1 = KFAnim((self.time, Window.width/2, Window.height/2), (self.time + num_seconds_to_screen_edge_bottom, Window.width/2+100, 0))
        elif self.direction == 'up_left':
            self.pos_anim_0 = KFAnim((self.time, Window.width/2, Window.height/2), (self.time + num_seconds_to_screen_edge_sides, 0, Window.height/2+100))
            self.pos_anim_1 = KFAnim((self.time, Window.width/2, Window.height/2), (self.time + num_seconds_to_screen_edge_sides, 0, Window.height/2-150))
        elif self.direction == 'up_right':
            self.pos_anim_0 = KFAnim((self.time, Window.width/2, Window.height/2), (self.time + num_seconds_to_screen_edge_sides, Window.width, Window.height/2+100))
            self.pos_anim_1 = KFAnim((self.time, Window.width/2, Window.height/2), (self.time + num_seconds_to_screen_edge_sides, Window.width, Window.height/2-150))

        self.time = 0
        self.hit = False

        self.width_anim = None

    # change to display this gem being hit
    def on_hit(self):
        self.color.a = 1
        self.hit = True
        self.width_anim = KFAnim((0, self.width), (1, 3 * self.width))
        self.pos_anim = False  # stop moving
        self.time = 0
        self.on_update(0)

    # change to display a passed gem
    def on_pass(self):
        self.color.a = 0.2  # decrease color alpha

    # return midpoint
    def get_pos(self):
        x1, y1, x2, y2 = self.line.points
        return (x1+x2)/2, (y1+y2)/2

    def set_second(self, second):
        if self.pos_anim_0:
            p0 = self.pos_anim_0.eval(second)
            p1 = self.pos_anim_1.eval(second)
            self.line.points = [p0[0], p0[1], p1[0], p1[1]]
            return self.pos_anim_0.is_active(second)
        return True

    # useful if gem is to animate
    def on_update(self, dt):
        if self.hit:
            width = self.width_anim.eval(self.time)
            self.line.width = width
            self.time += dt
            return self.width_anim.is_active(self.time)
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
        # self.add(self.line)

    def set_y(self, y):
        self.line.points = [0, y, Window.width, y]

    def on_update(self, dt):
        return True


# Displays one of the 4 side bars
class SideBarDisplay(InstructionGroup):
    def __init__(self, direction):
        super(SideBarDisplay, self).__init__()
        self.direction = direction
        direction_line_points = {
            'left': [Window.width/2-275, bottom_y, Window.width/2-25, bottom_y],
            'right': [Window.width/2+25, bottom_y, Window.width/2+275, bottom_y],
            'up_left': [left_x, 150, left_x, 400],
            'up_right': [right_x, 150, right_x, 400]
        }
        self.points = direction_line_points[self.direction]
        self.line = Line(points=self.points, width=10)
        self.orig_a = 0.5
        colors = {
            'left': Color(255/255, 255/255, 77/255, self.orig_a),
            'right': Color(77/255, 148/255, 255/255, self.orig_a),
            'up_left': Color(255/255, 102/255, 102/255, self.orig_a),
            'up_right': Color(102/255, 255/255, 102/255, self.orig_a)
        }
        self.color = colors[self.direction]
        # self.color = Color(242, 242, 242, self.orig_a)
        self.add(self.color)
        self.add(self.line)

        self.miss = True
        # Detecting TapGesture
        self.tapped = False

    # displays when side bar is tapped (and if it hit a gem)
    def on_tap(self, hit):
        if hit:
            # self.color.a = 1
            print("hit!")
        else:
            self.miss = True

    # back to normal state
    def on_release_tap(self):
        if self.miss:
            self.miss = False

    def set_tapped(self, tapped):
        if tapped:
            self.color.a = 1
        else:
            self.color.a = self.orig_a
        self.tapped = tapped


# This class monitors the location of the hand and determines if a tap on
# a SideBar happened. Each TapGesture is associated with a SideBar (one-to-one
# correspondence).
# the callback function takes a single argument: SideBar being tapped
class TapGesture(object):
    def __init__(self, side_bar, tap_callback, release_tap_callback):
        super(TapGesture, self).__init__()
        self.side_bar = side_bar
        self.tap_callback = tap_callback
        self.release_tap_callback = release_tap_callback

        x1, y1, x2, y2 = self.side_bar.points
        self.x_range = sorted([x1, x2])
        self.y_range = sorted([y1, y2])

        self.x_threshold = 50 # room for error in x
        self.y_threshold = 50  # room for error in y

    def set_hand_pos(self, pos, hand):
        # check if x and y is between allowed range & room for error
        if pos[0] > self.x_range[0] - self.x_threshold and pos[0] < self.x_range[1] + self.x_threshold and \
            pos[1] > self.y_range[0] - self.y_threshold and pos[1] < self.y_range[1] + self.y_threshold:
            if not self.side_bar.tapped:
                self.tap_callback(self.side_bar, hand)
        # if hand position is outside side bar and side_bar was tapped, mark as untapped
        elif self.side_bar.tapped:
            self.release_tap_callback(self.side_bar, hand)


class Translate(InstructionGroup):
    def __init__(self):
        super(Translate, self).__init__()
        self.anim_group = AnimGroup()
        self.objs = []
        self.inactive_indices = []
        self.add(self.anim_group)

    def add_obj(self, obj):
        self.anim_group.add(obj)
        self.objs.append(obj)

    def on_end_game(self):  # reset
        self.objs = []
        self.anim_group.clear()
        self.inactive_indices = []

    def on_update(self, second):
        for i in range(len(self.objs)):
            if i not in self.inactive_indices:
                obj = self.objs[i]
                active = obj.set_second(second)
                if not active:
                    self.inactive_indices.append(i)
                    self.anim_group.remove(obj)
        self.anim_group.on_update()


# Displays and controls all game elements: SideBars, BarLines?, Gems.
class BeatMatchDisplay(InstructionGroup):
    def __init__(self, gem_data, barline_times, end_game_callback):
        super(BeatMatchDisplay, self).__init__()

        self.side_bars = {}
        for direction in directions:
            side_bar = SideBarDisplay(direction)
            self.add(side_bar)
            self.side_bars[direction] = side_bar

        self.gem_data = gem_data
        self.gem_index = 0
        self.barline_times = barline_times
        self.barline_index = 0

        self.gems = []

        self.trans = Translate()
        self.add(self.trans)

        self.end_game_callback = end_game_callback
        self.side_bars_tapped = {
            "right": None,
            "left": None
        }

    # called by Player. Causes the right thing to happen
    def gem_hit(self, gem_idx, accuracy, second):
        if gem_idx < len(self.gems):
            self.gems[gem_idx].on_hit()
            self.trans.add_obj(AccuracyDisplay(accuracy, self.gems[gem_idx].get_pos(), second))

    # called by Player. Causes the right thing to happen
    def gem_pass(self, gem_idx, second):
        if gem_idx < len(self.gems):
            self.gems[gem_idx].on_pass()
            self.trans.add_obj(AccuracyDisplay("Miss", self.gems[gem_idx].get_pos(), second))

    # called by Player. Causes the right thing to happen
    def on_tap(self, direction, hit, hand):
        self.side_bars_tapped[hand] = direction
        self.side_bars[direction].on_tap(hit)
        self.side_bars[direction].set_tapped(True)

    # called by Player. Causes the right thing to happen
    def on_release_tap(self, direction, hand):
        self.side_bars_tapped[hand] = None
        if self.side_bars_tapped["right"] != direction and self.side_bars_tapped["left"] != direction:
            self.side_bars[direction].on_release_tap()
            self.side_bars[direction].set_tapped(False)

    def on_end_game(self):
        self.clear()
        self.gem_index = 0
        self.barline_index = 0
        self.trans.on_end_game()

    # call every frame to make gems and barlines flow down the screen
    def on_update(self, frame):
        second = frame / Audio.sample_rate
        if self.gem_index < len(self.gem_data):
            gem_time, gem_label = self.gem_data[self.gem_index]
            gem_direction = direction_number_map[int(gem_label)]
            if gem_time - num_seconds < second:
                # print("release")
                # direction = random.choice(directions)
                gem = GemDisplay(second, gem_direction)
                self.gems.append(gem)
                self.trans.add_obj(gem)
                self.gem_index += 1
        if self.barline_index < len(self.barline_times):
            barline_time = self.barline_times[self.barline_index]
            if barline_time - num_seconds < second:
                # self.trans.add_obj(BarlineDisplay(), second)
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
        self.good_slop_window = 0.15 # +-150 ms
        self.perfect_slop_window = 0.08 # +-80 ms

        self.tap_gestures = [TapGesture(side_bar, self.on_tap, self.on_release_tap) for direction, side_bar in self.display.side_bars.items()]

    def on_tap(self, side_bar, hand):
        second = self.audio_ctrl.get_frame() / Audio.sample_rate
        hit = False
        gem_index = self.pass_gem_index + 1
        new_pass_gem_index = self.pass_gem_index
        while gem_index < len(self.gem_data) and self.gem_data[gem_index][0] <= second + self.good_slop_window:
            gem_label = self.gem_data[gem_index][1]
            gem_direction = direction_number_map[int(gem_label)]
            if gem_direction == side_bar.direction:  # Hit
                hit = True
                gem_second = self.gem_data[gem_index][0]
                if abs(gem_second - second) <= self.perfect_slop_window:
                    self.display.gem_hit(gem_index, "Perfect", second)
                    self.score += 1
                elif abs(gem_second - second) <= self.good_slop_window:
                    self.display.gem_hit(gem_index, "Good", second)
                    self.score += 0.5
            # else: # Else, it's a Lane miss
            #     self.display.gem_pass(gem_index)  # gem can no longer by hit
            new_pass_gem_index = gem_index
            gem_index += 1
        self.pass_gem_index = new_pass_gem_index
        self.display.on_tap(side_bar.direction, hit, hand)
        # self.audio_ctrl.set_mute(not hit)
        # if not hit:  # Temporal miss or Lane miss
        #     self.audio_ctrl.play_sfx()

    def on_release_tap(self, side_bar, hand):
        self.display.on_release_tap(side_bar.direction, hand)

    def on_end_game(self):
        self.score = 0
        self.pass_gem_index = -1

    # needed to check if for pass gems (ie, went past the slop window)
    def on_update(self):
        second = self.audio_ctrl.get_frame() / Audio.sample_rate
        gem_index = self.pass_gem_index + 1
        while gem_index < len(self.gem_data) and self.gem_data[gem_index][0] <= second - self.good_slop_window:
            self.display.gem_pass(gem_index, second)
            # self.audio_ctrl.set_mute(True)
            gem_index += 1
        self.pass_gem_index = gem_index - 1


# for use with scale_point:
# x, y, and z ranges to define a 3D bounding box
kLeapRange   = ( (-250, 250), (100, 500), (-200, 250) )

run(MainWidget)
