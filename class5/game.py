import sys
sys.path.append('..')
from common.core import *
from common.audio import *
from common.synth import *
from common.mixer import *
from common.wavegen import *
from common.wavesrc import *
from common.gfxutil import *

from kivy.graphics.instructions import InstructionGroup
from kivy.graphics import Color, Ellipse, Line, Rectangle
from kivy.graphics import PushMatrix, PopMatrix, Translate, Scale, Rotate
from kivy.clock import Clock as kivyClock
from kivy.core.text import Label as CoreLabel
from kivy.uix.image import Image

import random
import numpy as np
import bisect

from common.leaputil import *
import Leap

NUM_GEMS = None
NUM_SECONDS = 2  # how long it takes for lines to move from center to bars
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
center = (Window.width/2, Window.height/2 + 50)

# current_song_index = 0
songs = [
    {
        'wav_path': '../data/thank_u_next_1_min.wav',
        'gem_data_path': '../data/gem_data_thank_u_next_'  # 'easy.txt'
    },
    {
        'wav_path': '../data/flower_dance.wav',
        'gem_data_path': '../data/gem_data_flower_dance_'  # 'easy.txt'
    }
]

index_to_song = {
    0: 'Thank u, Next',
    1: 'Flower Song',
    2: 'Umaru'
}

index_to_data = {
    0: 'thank u, next',
    1: 'flower song',
    2: 'umaru'
}

index_to_img = {
    0: "../images/thanku_next.jpeg",
    1: "../images/flower_dance.jpg",
    2: "../images/umaru.jpg"
}

index_to_img_label = {
    0: "../images/thanku_next_label.png",
    1: "../images/flower_song_label.png",
    2: "../images/umaru_label.png"
}

# gem_data_path = '../data/gem_data_thank_u_next_easy.txt'
# gem_data_path = '../data/gem_data_thank_u_next_medium.txt'
# gem_data_path = '../data/gem_data_thank_u_next_hard.txt'
# wav_path = '../data/thank_u_next_1_min.wav'
# gem_data_path = '../data/gem_data_flower_dance_medium.txt'
# gem_data_path = '../data/gem_data_flower_dance_easy.txt'
gem_data_path = '../data/gem_data_flower_dance_hard.txt'
wav_path = '../data/flower_dance.wav'

class MainWidget(BaseWidget) :
    def __init__(self):
        super(MainWidget, self).__init__()

        # image_path = "../images/bongo_cat_raised_paws.png"
        # self.image = Image(100, 105, center, image_path)
        # self.canvas.add(self.image)

        self.left_hand_pos = [0,0,0]
        self.right_hand_pos = [0,0,0]
        self.song_selected = False
        self.in_game = False
        self.song_menu = SongMenu()

        logo_path = "../images/airbeatz_logo.png"
        self.logo = Image(193, 36, [center[0], Window.height - 50], logo_path)
        self.canvas.add(self.logo)

        self.song_data = SongData()
        self.gem_data = self.song_data.read_gem_data(gem_data_path)
        # barline_times = self.song_data.read_barline_data('../data/barline_data.txt')
        # self.display = BeatMatchDisplay(self.gem_data, barline_times, self.on_end_game)
        self.display = BeatMatchDisplay(self.gem_data, self.on_end_game)
        # self.canvas.add(self.display)

        self.audio_ctrl = AudioController(wav_path)
        self.audio_ctrl.toggle()
        self.audio = self.audio_ctrl.audio

        self.player = Player(self.gem_data, self.display, self.audio_ctrl, self.audio_ctrl.on_tap)

        # self.score_display = CoreLabel(text='Score: %d'%(self.player.score), font_size=25)
        # self.score_display.refresh()
        # self.score_texture = self.score_display.texture
        # self.canvas.add(Color(1, 1, 1))
        # score_text_pos = [Window.width * 7/9, Window.height * 4/5]
        # self.score_label = Rectangle(size=self.score_texture.size, pos=score_text_pos, texture=self.score_texture)
        # self.canvas.add(self.score_label)

        self.label = topleft_label()
        self.label.text = ""
        self.add_widget(self.label)

        self.leap = Leap.Controller()

        # set up size / location of 3DCursor object
        kMargin = Window.width * 0.05
        kCursorSize = Window.width - 2 * kMargin, Window.height - 2 * kMargin
        kCursorPos = kMargin, kMargin

        # hand_color = (148/255,0,211/255)
        hand_color = (1,1,1, 0.7)
        self.left_hand_disp = Cursor3D(kCursorSize, kCursorPos, hand_color)
        self.canvas.add(self.left_hand_disp)

        self.right_hand_disp = Cursor3D(kCursorSize, kCursorPos, hand_color)
        self.canvas.add(self.right_hand_disp)

        self.difficulty = 'Easy'
        self.difficulty_rec_label = None
        self.set_difficulty_label()

    def set_difficulty_label(self):
        if self.difficulty_rec_label is not None:
            self.canvas.remove(self.difficulty_rec_label)
        self.difficulty_label = CoreLabel(text=self.difficulty, font_size=25)
        self.difficulty_label.refresh()
        self.difficulty_texture = self.difficulty_label.texture
        self.canvas.add(Color(1,1,1))
        text_pos = [Window.width*0.5, Window.height*0.2]
        self.difficulty_rec_label = Rectangle(size=self.difficulty_texture.size, pos=text_pos, texture=self.difficulty_texture)
        self.canvas.add(self.difficulty_rec_label)

    def on_key_down(self, keycode, modifiers):
        # play / pause toggle
        self.song_menu.on_key_down(keycode, modifiers)
        if keycode[1] == 'p' and self.in_game:
            self.audio_ctrl.toggle()
        elif keycode[1] == 'q' and self.in_game:
            self.in_game = False
            self.on_end_game()
        elif keycode[1] == 's':
            self.song_menu.clear()
            self.in_game = True
            # self.canvas.add(self.display)
            self.on_restart()
            # self.on_start_game()
        elif keycode[1] == 'r':
            self.on_restart()
        elif keycode[1] == 'enter':
            pass
        elif keycode[1] == 'up':
            if self.difficulty == 'Medium':
                self.difficulty = 'Easy'
            elif self.difficulty == 'Hard':
                self.difficulty = 'Medium'
            self.set_difficulty_label()
        elif keycode[1] == 'down':
            if self.difficulty == 'Easy':
                self.difficulty = 'Medium'
            elif self.difficulty == 'Medium':
                self.difficulty = 'Hard'
            self.set_difficulty_label()

    def on_start_game(self):
        self.canvas.clear()
        self.song_menu.clear()
        self.song_data = SongData()

    def on_restart(self):
        self.canvas.clear()
        self.audio_ctrl.set_song(songs[self.song_menu.current_song_index]['wav_path'])
        self.gem_data = self.song_data.read_gem_data(songs[self.song_menu.current_song_index]['gem_data_path'] + self.difficulty.lower() + '.txt')
        self.audio_ctrl.on_restart()
        self.display.on_restart()
        self.canvas.add(self.logo)
        self.canvas.add(self.display)
        self.player.on_restart()
        self.canvas.add(self.left_hand_disp)
        self.canvas.add(self.right_hand_disp)
        self.left_hand_pos = [0,0,0]
        self.right_hand_pos = [0,0,0]


    def on_end_game(self):
        self.song_selected = False
        self.in_game = False
        self.audio_ctrl.on_end_game()
        self.display.on_end_game()

        font_colors = {
            'Normal': Color(217/255, 217/255, 217/255),
            'Perfect': Color(0, 1, 0),
            'Good': Color(1, 127/255, 80/255),
            'Miss': Color(1, 0, 0),
            'Combo': Color(0, 0, 1)
        }

        text_height = 200

        label = CoreLabel(text='Score', font_size=50)
        label.refresh()
        texture = label.texture
        self.canvas.add(font_colors['Normal'])
        text_pos = [100, Window.height-text_height]
        rec_label = Rectangle(size=texture.size, pos=text_pos, texture=texture)
        self.canvas.add(rec_label)

        label = CoreLabel(text=str(self.player.score), font_size=50)
        label.refresh()
        texture = label.texture
        text_pos = [300, Window.height-text_height]
        rec_label = Rectangle(size=texture.size, pos=text_pos, texture=texture)
        self.canvas.add(rec_label)

        nums = {
            'Perfect': self.player.num_perfects,
            'Good': self.player.num_goods,
            'Miss': self.player.num_misses,
            'Combo': self.player.highest_combo
        }

        for acc in ['Perfect', 'Good', 'Miss', 'Combo']:
            color = font_colors[acc]
            label = CoreLabel(text=acc, font_size=30)
            label.refresh()
            texture = label.texture
            self.canvas.add(color)
            text_height += 60
            text_pos = [100, Window.height-text_height]
            rec_label = Rectangle(size=texture.size, pos=text_pos, texture=texture)
            self.canvas.add(rec_label)


            label = CoreLabel(text=str(nums[acc]), font_size=30)
            label.refresh()
            texture = label.texture
            text_pos = [300, Window.height-text_height]
            rec_label = Rectangle(size=texture.size, pos=text_pos, texture=texture)
            self.canvas.add(rec_label)

        total_poss_score = len(self.gem_data) * 10
        percent = self.player.score / total_poss_score

        if percent > 0.85:
            grade = 'A'
        elif percent > 0.7:
            grade = 'B'
        elif percent > 0.55:
            grade = 'C'
        elif percent > 0.4:
            grade = 'D'
        else:
            grade = 'F'

        label = CoreLabel(text=grade, font_size=300)
        label.refresh()
        texture = label.texture
        text_pos = [475, Window.height-425]
        rec_label = Rectangle(size=texture.size, pos=text_pos, texture=texture)
        self.canvas.add(font_colors['Normal'])
        self.canvas.add(rec_label)

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
        if not self.in_game:
            # display song menu
            self.canvas.add(self.song_menu)
            self.song_menu.on_update()

        else:
            song_ended = not self.audio_ctrl.on_update()
            if song_ended:
                self.on_end_game()
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
            self.player.on_update()
            self.label.text = ''
            if not song_ended:
                self.label.text += 'Score: %s\n' % (self.player.score)


# Basic songs menu
class SongMenu(InstructionGroup):
    def __init__(self):
        super(SongMenu, self).__init__()

        self.current_song_index = 0
        self.num_songs = 3

        self.trans = Translate()
        self.add(self.trans)

        self.img_locations = [center, (center[0]+400, center[1]), (center[0]+800, center[1])]
        self.label_locations = [(center[0], center[1]-170), (center[0]+400, center[1]-170), (center[0]+800, center[1]-170)]

        self.list_imgs = []
        self.list_labels = []
        self.anim_group = AnimGroup()

        for i in range(3):
            image_path = index_to_img[i]
            label_path = index_to_img_label[i]
            image = Image(250, 250, self.img_locations[i], image_path)
            label = Image(250, 45, self.label_locations[i], label_path)

            self.add(image)
            self.add(label)
            self.list_imgs.append(image)
            self.list_labels.append(label)

        for im in self.list_imgs:
            self.anim_group.add(im)
        for label in self.list_labels:
            self.anim_group.add(label)

    def on_key_down(self, keycode, modifiers):
        print (keycode)
        if keycode[1] == 's':
            print ("Song was selected")
            current_song_index = self.current_song_index
        elif keycode[1] == 'right' and self.current_song_index<2:
            self.current_song_index += 1
            print ("right")
            for i in range(3):
                img = self.list_imgs[i]
                img.move_right(1)
                label = self.list_labels[i]
                label.move_right(1)
            # self.move_right = True
        elif keycode[1] == 'left' and self.current_song_index>0:
            self.current_song_index -= 1
            print ("left")
            for i in range(3):
                img = self.list_imgs[i]
                img.move_left(1)
                label = self.list_labels[i]
                label.move_left(1)
            # self.move_left = True

    def on_update(self):
        self.anim_group.on_update()
        return True

# creates the Audio driver
# creates a song and loads it
# creates snippets for audio sound fx
class AudioController(object):
    def __init__(self, song_path):
        super(AudioController, self).__init__()
        self.audio = Audio(2)
        self.mixer = Mixer()
        self.mixer.set_gain(0.2)
        self.audio.set_generator(self.mixer)
        self.song_path = song_path

        self.wave_file = WaveFile(song_path)
        self.wave_gen = WaveGenerator(self.wave_file)
        self.mixer.add(self.wave_gen)

        # for tapping noise
        self.synth = Synth('../data/FluidR3_GM.sf2')
        self.synth.program(0, 128, 48)
        self.mixer.add(self.synth)
        self.max_sound_timestep = 20
        self.sound_timestep = -1

    def set_song(self, song_path):
        if song_path != self.song_path:
            self.mixer.remove(self.wave_gen)
            self.wave_file = WaveFile(song_path)
            self.wave_gen = WaveGenerator(self.wave_file)
            self.mixer.add(self.wave_gen)

    # start / stop the song
    def toggle(self):
        self.wave_gen.play_toggle()

    # # play a sound-fx (miss sound)
    # def play_sfx(self):
    #     buffers = make_wave_buffers("../data/mario.wav", "../data/miss_region.txt")
    #     miss_buffer = buffers['miss']
    #     gen = WaveGenerator(miss_buffer)
    #     self.mixer.add(gen)

    def get_frame(self):
        return self.wave_gen.frame

    def on_restart(self):
        self.wave_gen.reset()
        self.wave_gen.set_gain(1)
        self.wave_gen.play()

    def on_end_game(self):  # reset
        self.wave_gen.reset()
        self.wave_gen.set_gain(1)

    def on_tap(self):
        self.synth.noteon(0, 76, 80)
        self.sound_timestep = 20

    def sound_off(self):
        self.synth.noteoff(0, 36)

    # needed to update audio
    def on_update(self):
        if self.sound_timestep == 0:
            self.sound_off()
        elif self.sound_timestep > -1:
            self.sound_timestep -= 1
        if self.wave_gen not in self.mixer.generators:
            return False
        self.audio.on_update()
        return True


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
            if time > NUM_SECONDS:
                direction = int(tokens[1])
                gems.append((time, direction))
        NUM_GEMS = len(gems)
        return gems

    def read_barline_data(self, filepath):
        f = open(filepath)
        lines = f.readlines()
        times = []
        for line in lines:
            tokens = line.strip().split('\t')
            time = float(tokens[0])
            if time > NUM_SECONDS:
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


class ComboDisplay(InstructionGroup):
    def __init__(self, combo, second):
        super(ComboDisplay, self).__init__()
        self.combo = combo
        font_size = 25
        self.pos = [Window.width/2, Window.height/2+100]
        self.size = (100, 25)
        self.box = Rectangle(pos=self.pos, size=self.size)
        box_color = Color(0, 0, 0, 0)
        self.add(box_color)
        self.add(self.box)

        label = CoreLabel(text='Combo %d'%(self.combo), font_size=font_size)
        # the label is usually not drawn until needed, so force it to draw
        label.refresh()
        # now access the texture of the label and use it
        texture = label.texture
        self.color = Color(0, 0, 1)
        self.add(self.color)
        text_pos = list(self.pos[i] + (self.size[i] - texture.size[i]) / 2 for i in range(2))
        self.label = Rectangle(size=texture.size, pos=text_pos, texture=texture)
        self.add(self.label)
        max_time = 1
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

        # line points
        if self.direction == 'up_left' or self.direction == 'up_right':
            starting_pts = [Window.width/2, Window.height/2, Window.width/2, Window.height/2]
        else:
            starting_pts = [Window.width/2-50, Window.height/2, Window.width/2+50, Window.height/2]

        self.width = 1
        self.line = Line(points=starting_pts, width=self.width)

        # line colors
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


        # animations
        self.time = second
        NUM_SECONDS_to_screen_edge_bottom = NUM_SECONDS / (center[1] - bottom_y) * center[1]
        NUM_SECONDS_to_screen_edge_sides = NUM_SECONDS / (center[0] - left_x) * center[0]
        if self.direction == 'left':
            self.pos_anim_0 = KFAnim((self.time, center[0], center[1]), (self.time + NUM_SECONDS_to_screen_edge_bottom, Window.width/2-350, 0))
            self.pos_anim_1 = KFAnim((self.time, center[0], center[1]), (self.time + NUM_SECONDS_to_screen_edge_bottom, Window.width/2-50, 0))
        elif self.direction == 'right':
            self.pos_anim_0 = KFAnim((self.time, center[0], center[1]), (self.time + NUM_SECONDS_to_screen_edge_bottom, Window.width/2+350, 0))
            self.pos_anim_1 = KFAnim((self.time, center[0], center[1]), (self.time + NUM_SECONDS_to_screen_edge_bottom, Window.width/2+50, 0))
        elif self.direction == 'up_left':
            self.pos_anim_0 = KFAnim((self.time, center[0], center[1]), (self.time + NUM_SECONDS_to_screen_edge_sides, 0, Window.height/2+50))
            self.pos_anim_1 = KFAnim((self.time, center[0], center[1]), (self.time + NUM_SECONDS_to_screen_edge_sides, 0, Window.height/2-175))
        elif self.direction == 'up_right':
            self.pos_anim_0 = KFAnim((self.time, center[0], center[1]), (self.time + NUM_SECONDS_to_screen_edge_sides, Window.width, Window.height/2+50))
            self.pos_anim_1 = KFAnim((self.time, center[0], center[1]), (self.time + NUM_SECONDS_to_screen_edge_sides, Window.width, Window.height/2-175))

        self.width_anim = KFAnim((self.time, 1), (self.time + NUM_SECONDS_to_screen_edge_bottom, 10))

        self.time = 0
        self.hit = False

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
            w = self.width_anim.eval(second)
            self.line.points = [p0[0], p0[1], p1[0], p1[1]]
            self.line.width = w
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


# for 3D background
class Star(InstructionGroup):
    def __init__(self, second):
        super(Star, self).__init__()
        color = (1, 1, 1, 0.5)
        self.color = Color(*color)
        self.add(self.color)
        self.circle = CEllipse(cpos = center, size = (0, 0), segments = 5)
        self.add(self.circle)
        floating_num_seconds = 7
        self.side = random.choice(["top", "bottom", "left", "right"])
        # TODO: randomize?
        max_r = 5
        self.r_anim = KFAnim((second, 0), (second + floating_num_seconds, max_r))
        if self.side == "top":
            self.pos_anim = KFAnim((second, center[0], center[1]), \
                (second + floating_num_seconds, random.random() * Window.width, Window.height))
        if self.side == "bottom":
            self.pos_anim = KFAnim((second, center[0], center[1]), \
                (second + floating_num_seconds, random.random() * Window.width, 0))
        if self.side == "left":
            self.pos_anim = KFAnim((second, center[0], center[1]), \
                (second + floating_num_seconds, 0, random.random() * Window.height))
        if self.side == "right":
            self.pos_anim = KFAnim((second, center[0], center[1]), \
                (second + floating_num_seconds, Window.width, random.random() * Window.height))

    def set_second(self, second):
        pos = self.pos_anim.eval(second)
        self.circle.cpos = pos
        r = self.r_anim.eval(second)
        self.circle.size = (2 * r, 2 * r)
        return self.pos_anim.is_active(second)

    def on_update(self, dt):
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
            # print("hit!")
            pass
        else:
            self.miss = True

    # back to normal state
    def on_release_tap(self):
        if self.miss:
            self.miss = False

    def set_tapped(self, tapped):
        # if not tapped:
        #     print(self.direction)
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
    def __init__(self, side_bar, tap_callback, release_tap_callback, sound_tap_callback):
        super(TapGesture, self).__init__()
        self.side_bar = side_bar
        self.tap_callback = tap_callback
        self.release_tap_callback = release_tap_callback
        self.sound_tap_callback = sound_tap_callback

        x1, y1, x2, y2 = self.side_bar.points
        self.x_range = sorted([x1, x2])
        self.y_range = sorted([y1, y2])

        self.x_threshold = 30 # room for error in x
        self.y_threshold = 30  # room for error in y

    def set_hand_pos(self, pos, hand):
        # check if x and y is between allowed range & room for error
        if pos[0] > self.x_range[0] - self.x_threshold and pos[0] < self.x_range[1] + self.x_threshold and \
            pos[1] > self.y_range[0] - self.y_threshold and pos[1] < self.y_range[1] + self.y_threshold:
            if not self.side_bar.tapped:
                self.tap_callback(self.side_bar, hand)
                self.sound_tap_callback()
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

    def on_restart(self):
        self.objs = []
        self.anim_group.clear()
        self.inactive_indices = []

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
    # def __init__(self, gem_data, barline_times, end_game_callback):
    def __init__(self, gem_data, end_game_callback):
        super(BeatMatchDisplay, self).__init__()

        self.end_game_callback = end_game_callback
        self.gem_data = gem_data
        self.side_bars = {}
        for direction in directions:
            side_bar = SideBarDisplay(direction)
            self.add(side_bar)
            self.side_bars[direction] = side_bar
        self.trans = Translate()
        self.add(self.trans)

        self.gem_index = 0
        # self.barline_times = barline_times
        # self.barline_index = 0
        self.gems = []
        self.side_bars_tapped = {
            "right": None,
            "left": None
        }
        self.star_seconds_counter = 0

    # called by Player. Causes the right thing to happen
    def gem_hit(self, gem_idx, accuracy, second, combo=None):
        if gem_idx < len(self.gems):
            self.gems[gem_idx].on_hit()
            self.trans.add_obj(AccuracyDisplay(accuracy, self.gems[gem_idx].get_pos(), second))
            if combo is not None:
                self.trans.add_obj(ComboDisplay(combo, second))

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
        if self.side_bars_tapped[hand] == direction:
            self.side_bars_tapped[hand] = None
        if self.side_bars_tapped["right"] != direction and self.side_bars_tapped["left"] != direction:
            self.side_bars[direction].on_release_tap()
            self.side_bars[direction].set_tapped(False)

    def on_restart(self):
        self.clear()
        for direction in self.side_bars:
            self.add(self.side_bars[direction])
        self.gem_index = 0
        self.gems = []
        self.side_bars_tapped = {
            "right": None,
            "left": None
        }
        self.star_seconds_counter = 0
        self.trans.on_restart()
        self.add(self.trans)

    def on_end_game(self):
        self.clear()
        self.gem_index = 0
        # self.barline_index = 0
        self.trans.on_end_game()

    # call every frame to make gems and barlines flow down the screen
    def on_update(self, frame):
        second = frame / Audio.sample_rate
        if self.star_seconds_counter / 10 < second:
            self.trans.add_obj(Star(second))
            self.star_seconds_counter += 1
        if self.gem_index < len(self.gem_data):
            gem_time, gem_label = self.gem_data[self.gem_index]
            gem_direction = direction_number_map[int(gem_label)]
            if gem_time - NUM_SECONDS < second:
                # print("release")
                # direction = random.choice(directions)
                gem = GemDisplay(second, gem_direction)
                self.gems.append(gem)
                self.trans.add_obj(gem)
                self.gem_index += 1
        # if self.barline_index < len(self.barline_times):
        #     barline_time = self.barline_times[self.barline_index]
        #     if barline_time - NUM_SECONDS < second:
        #         # self.trans.add_obj(BarlineDisplay(), second)
        #         self.barline_index += 1
        # else:  # End game when no more barlines
        #     self.end_game_callback()
        self.trans.on_update(second)


# Handles game logic and keeps score.
# Controls the display and the audio
class Player(object):
    def __init__(self, gem_data, display, audio_ctrl, sound_tap_callback):
        super(Player, self).__init__()
        self.gem_data = gem_data
        self.display = display
        self.audio_ctrl = audio_ctrl
        self.good_slop_window = 0.15 # +-150 ms
        self.perfect_slop_window = 0.08 # +-80 ms
        self.tap_gestures = [TapGesture(side_bar, self.on_tap, self.on_release_tap, sound_tap_callback) for direction, side_bar in self.display.side_bars.items()]
        self.min_combo = 5

        self.pass_gem_index = -1  # most recent gem that went past the slop window
        self.score = 0
        self.num_perfects = 0
        self.num_goods = 0
        self.num_misses = 0
        self.combo = 0
        self.highest_combo = 0
        # self.previous_hit = False  # True if last tap was a hit, False if was a miss

    def on_restart(self):
        self.pass_gem_index = -1  # most recent gem that went past the slop window
        self.score = 0
        self.num_perfects = 0
        self.num_goods = 0
        self.num_misses = 0
        self.combo = 0
        self.highest_combo = 0

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
                self.combo += 1  # Add on to combo
                if abs(gem_second - second) <= self.perfect_slop_window:
                    if self.combo >= self.min_combo:  # Display combo if > minimum combo
                        self.display.gem_hit(gem_index, "Perfect", second, self.combo)
                    else:
                        self.display.gem_hit(gem_index, "Perfect", second, None)
                    self.score += 10
                    self.num_perfects += 1
                elif abs(gem_second - second) <= self.good_slop_window:
                    if self.combo >= self.min_combo:
                        self.display.gem_hit(gem_index, "Good", second, self.combo)
                    else:
                        self.display.gem_hit(gem_index, "Good", second, None)
                    self.score += 5
                    self.num_goods += 1
            # else: # Else, it's a Lane miss
            #     self.display.gem_pass(gem_index)  # gem can no longer by hit
            new_pass_gem_index = gem_index
            gem_index += 1
        self.pass_gem_index = new_pass_gem_index
        self.display.on_tap(side_bar.direction, hit, hand)
        # if not hit:  # Temporal miss or Lane miss
        #     self.audio_ctrl.play_sfx()

    def on_release_tap(self, side_bar, hand):
        self.display.on_release_tap(side_bar.direction, hand)

    def on_end_game(self):
        self.pass_gem_index = -1

    # needed to check if for pass gems (ie, went past the slop window)
    def on_update(self):
        second = self.audio_ctrl.get_frame() / Audio.sample_rate
        gem_index = self.pass_gem_index + 1
        while gem_index < len(self.gem_data) and self.gem_data[gem_index][0] <= second - self.good_slop_window:
            self.display.gem_pass(gem_index, second)
            self.num_misses += 1
            # self.previous_hit = False
            if self.combo > self.highest_combo:  # Record highest combo before resetting combo
                self.highest_combo = self.combo
            self.combo = 0
            # self.audio_ctrl.set_mute(True)
            gem_index += 1
        self.pass_gem_index = gem_index - 1


class Image(InstructionGroup):
    def __init__(self, width, height, center_pos, image_path):
        super(Image, self).__init__()
        self.width = width
        self.height = height
        self.size = (self.width, self.height)
        self.image_path = image_path
        self.image = Rectangle(source=image_path, pos=[center_pos[0]-width/2, center_pos[1]-height/2], size=self.size)
        self.add(self.image)
        self.active = True
        self.time = 0
        self.x_anim = None

    def set_pos(self, pos):
        self.image.pos = pos

    def get_pos(self):
        return self.image.pos

    def move_left(self, time_move):
        self.x_anim = KFAnim((0, self.image.pos[0]), (time_move, self.image.pos[0] + 400))
        self.time = 0
        self.on_update(0)

    def move_right(self, time_move):
        self.x_anim = KFAnim((0, self.image.pos[0]), (time_move, self.image.pos[0] - 400))
        self.time = 0
        self.on_update(0)

    # change image
    def set_image_path(self, image_path):
        self.image_path = image_path
        self.image.source = image_path

    def delete(self):
        self.active = False

    def on_update(self, dt):
        if self.x_anim is not None:
            x = self.x_anim.eval(self.time)
            self.image.pos = (x, self.image.pos[1])
            self.time += dt
        return self.active


# for use with scale_point:
# x, y, and z ranges to define a 3D bounding box
kLeapRange   = ( (-250, 250), (100, 500), (-200, 250) )

run(MainWidget)
