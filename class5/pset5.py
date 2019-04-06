#pset5: Magic Harp

# common import
import sys
sys.path.append('..')

from common.core import *
from common.gfxutil import *
from common.audio import *
from common.synth import *
from common.clock import *

from kivy.graphics import Color, Line
from kivy.graphics.instructions import InstructionGroup
from kivy.clock import Clock as kivyClock

import numpy as np

# Part 0: Choose your mode:
# MODE = 'kinect'
MODE = 'leap'


if MODE == 'leap':
    from common.leaputil import *
    import Leap

if MODE == 'kinect':
    from common.kinect import *


# This class displays a single string on screen. It knows how to draw the
# string and how to bend it, and animate it
class String(InstructionGroup):
    def __init__(self, idx, pitch, x, topY, bottomY):
        super(String, self).__init__()
        self.idx = idx
        self.pitch = pitch

        self.x = x
        self.topY = topY
        self.bottomY = bottomY
        self.middleY = (topY + bottomY) / 2
        self.line = Line(points=[x, topY, x, self.middleY, x, bottomY])
        self.add(self.line)
        
        self.grabbed = False
        self.time = 0  

        self.max_time = 0.25
        self.x_anim = None
        self.on_update(0)

    def set_grabbed(self, grabbed):
        self.grabbed = grabbed

    def pluck(self, initial_x):
        self.x_anim = KFAnim((0, initial_x), (self.max_time, 0)) # color disappears
        self.time = 0
        self.on_update(0)

    # if the string is going to animate (say, when it is plucked), on_update is
    # necessary
    def on_update(self, dt):
        self.time += dt
        if self.x_anim:
            dx = self.x_anim.eval(self.time)
            self.line.points = [self.x, self.topY, self.x + dx, self.middleY, self.x, self.bottomY]
        return True

# This class monitors the location of the hand and determines if a pluck of
# the string happened. Each PluckGesture is associated with a string (one-to-one
# correspondence). The PluckGesture also controls controls the movement of the
# String it is connected to (to show the string bending)
class PluckGesture(object):
    def __init__(self, string, idx, callback):
        super(PluckGesture, self).__init__()
        self.string = string
        self.idx = idx
        self.callback = callback

        self.grab_threshold = 20
        self.pluck_threshold = 40

    def set_hand_pos(self, pos):
        # check difference in x
        displacement = pos[0] - self.string.x
        dist = abs(displacement)
        if dist < self.pluck_threshold:
            if dist < self.grab_threshold and not self.string.grabbed:
                self.string.set_grabbed(True)
        elif self.string.grabbed:
            self.callback(self.idx)
            # determine which direction to animate
            if displacement < 0:
                self.string.pluck(-self.pluck_threshold)
            else:
                self.string.pluck(self.pluck_threshold)
            self.string.set_grabbed(False)
        
# This class determines if a fret is being pressed. A harp has many PressGestures
# (one for each fret).
class PressGesture(object):
    def __init__(self, fret_idx, string_x, top_y, bottom_y, x_threshold, callback):
        super(PressGesture, self).__init__()
        self.fret_idx = fret_idx
        self.string_x = string_x
        self.top_y = top_y
        self.bottom_y = bottom_y
        self.callback = callback

        self.x_threshold = x_threshold

    def set_hand_pos(self, pos):
        # check difference in x, and if y is within bounds of fret
        dist_x = abs(pos[0] - self.string_x)
        if dist_x < self.x_threshold and pos[1] < self.top_y and pos[1] >= self.bottom_y:
            self.callback(self.fret_idx)
        if dist_x >= self.x_threshold:
            self.callback(None)

# The Harp class combines the above classes into a fully working harp. It
# instantiates the strings and pluck gestures as well as a hand cursor display
class Harp(InstructionGroup):
    def __init__(self, synth):
        super(Harp, self).__init__()
        self.synth = synth

        # set up size / location of 3DCursor object
        kMargin = Window.width * 0.05
        kCursorSize = Window.width - 2 * kMargin, Window.height - 2 * kMargin
        kCursorPos = kMargin, kMargin
        
        self.inactive_alpha = 0.3

        self.left_hand_disp = Cursor3D(kCursorSize, kCursorPos, (.2, .2, .6))
        self.left_hand_disp.set_alpha(self.inactive_alpha)
        self.add(self.left_hand_disp)

        self.right_hand_disp = Cursor3D(kCursorSize, kCursorPos, (.2, .6, .2))
        self.right_hand_disp.set_alpha(self.inactive_alpha)
        self.add(self.right_hand_disp)

        self.right_hand_active = False
        self.left_hand_active = False

        # self.tuning = [60, 62, 64, 65, 67, 69, 71, 72]  # C major scale
        # num_strings = len(self.tuning)
        num_frets = 4
        num_strings = 4
        self.tuning = [60 + (num_frets + 1) * i for i in range(num_strings)]

        string_x = [(kCursorSize[0] - 2 * kMargin) / (num_strings + 2) * (i + 2) + 2 * kMargin for i in range(num_strings)]
        top_y = Window.height - kMargin
        bottom_y = kMargin
        self.strings = [String(i, self.tuning[i], string_x[i], top_y, bottom_y) for i in range(num_strings)]

        self.objects = AnimGroup()
        for string in self.strings:
            self.objects.add(string)
        self.add(self.objects)

        self.pluck_gestures = [PluckGesture(string, string.idx, self.on_pluck) for string in self.strings]
        self.playing_pitches = set()

        # add pitch changing
        self.fret = None  # number fret index 0, 1, etc.
        fret_height = kCursorSize[1] / num_frets
        fret_width = 60
        # (top y, bottom y) coordinates for each fret
        y_coords = [(top_y - fret_height * i, top_y - fret_height * (i+1)) for i in range(num_frets)]
        # (left x, right x) coordinate for all frets
        x_coords = (kMargin * 3.5, kMargin * 3.5 + fret_width)
        self.press_gestures = [PressGesture(i, sum(x_coords)/2, y_coords[i][0], y_coords[i][1], fret_width/2, self.set_fret) for i in range(num_frets)]
        self.buttons = [Button((x_coords[0], y_coords[i][1]), (fret_width, fret_height), (0, 0, 1), 0.5) for i in range(num_frets)]
        for button in self.buttons:
            self.objects.add(button)

    # set the hand position as a 3D vector ranging from [0,0,0] to [1,1,1]
    # right hand is in charge of plucking
    def set_right_hand_pos(self, pos):
        self.right_hand_disp.set_pos(pos)

        # active:
        if pos[2] < 0.48 and not self.right_hand_active:
            self.right_hand_active = True
            self.right_hand_disp.set_alpha(1)
        # inactive:
        if pos[2] > 0.49 and self.right_hand_active:
            self.right_hand_active = False
            self.right_hand_disp.set_alpha(self.inactive_alpha)

        if self.right_hand_active:
            screen_pos = self.right_hand_disp.to_screen_coords(pos)
            for pluck_gesture in self.pluck_gestures:
                pluck_gesture.set_hand_pos(screen_pos)

        # string returns to neutral if hand becomes inactive during a grab
        else:
            for string in self.strings:
                if string.grabbed:
                    string.set_grabbed(False)

    # left hand is in charge of pressing frets
    def set_left_hand_pos(self, pos):
        self.left_hand_disp.set_pos(pos)

        # active:
        if pos[2] < 0.48 and not self.left_hand_active:
            self.left_hand_active = True
            self.left_hand_disp.set_alpha(1)
        # inactive:
        if pos[2] > 0.49 and self.left_hand_active:
            self.left_hand_active = False
            self.left_hand_disp.set_alpha(self.inactive_alpha)

        if self.left_hand_active:
            screen_pos = self.left_hand_disp.to_screen_coords(pos)
            for press_gesture in self.press_gestures:
                press_gesture.set_hand_pos(screen_pos)

        # reset string to open string if hand becomes inactive
        else:
            self.set_fret(None)

    # callback to be called from a PluckGesture when a pluck happens
    def on_pluck(self, idx):
        pitch = self.tuning[idx]
        if self.fret is not None:
            pitch += (self.fret + 1)
        if pitch in self.playing_pitches:
            self.synth.noteoff(0, pitch)
        else:
            self.playing_pitches.add(pitch)
        self.synth.noteon(0, pitch, 100)

    # callback to be called from a PressGesture
    def set_fret(self, fret):
        if fret != self.fret:
            if self.fret is not None:
                self.buttons[self.fret].set_alpha(0.5) # reset prev fret button
            self.fret = fret
            if self.fret is not None:
                self.buttons[self.fret].set_alpha(1)

    # this might be needed if Harp's internal objects need on_update()
    def on_update(self):
        self.objects.on_update()


class Button(InstructionGroup):
    def __init__(self, pos, size, color, alpha):
        super(Button, self).__init__()
        self.pos = pos 
        self.size = size
        self.color = color
        self.box = Rectangle(pos=pos, size=size)

        self.color_obj = Color(*self.color[:3], alpha)
        self.add(self.color_obj)
        self.add(self.box)

    # turn buttons on/off
    def set_alpha(self, alpha):
        self.color_obj.a = alpha

    def on_update(self, dt):
        return True


class MainWidget(BaseWidget) :
    def __init__(self):
        super(MainWidget, self).__init__()

        self.info = topleft_label()
        self.add_widget(self.info)

        self.audio = Audio(2)
        self.synth = Synth("../data/FluidR3_GM.sf2")
        self.audio.set_generator(self.synth)
        self.synth.program(0, 0, 46)

        self.harp = Harp(self.synth)
        self.canvas.add(self.harp)

        if MODE == 'leap':
            self.leap = Leap.Controller()
        elif MODE == 'kinect':
            self.kinect = Kinect()
            self.kinect.add_joint(Kinect.kRightHand)

    def on_update(self) :
        self.info.text = ''

        if MODE == 'leap':
            # self.info.text += leap_info(self.leap)            
            leap_frame = self.leap.frame()
            # pt = leap_one_palm(leap_frame)
            pts = list(leap_two_palms(leap_frame))
            pts.sort(key=lambda pt: pt[0])  # sort by increasing x (hand with smaller x is first)
            norm_pts = [scale_point(pt, kLeapRange) for pt in pts]
        elif MODE == 'kinect':
            self.kinect.on_update()
            pt = self.kinect.get_joint(Kinect.kRightHand)

        # norm_pt = pt # TODO convert pt (in millimeters) to unit-based coordinates

        self.harp.set_left_hand_pos(norm_pts[0])
        self.harp.set_right_hand_pos(norm_pts[1])
        self.harp.on_update()

        self.audio.on_update()

        # self.info.text += 'x:%d\ny:%d\nz:%d\n' % tuple(pt.tolist())

# for use with scale_point:
# x, y, and z ranges to define a 3D bounding box
kKinectRange = ( (-250, 700), (-200, 700), (-500, 0) )
kLeapRange   = ( (-250, 250), (100, 500), (-200, 250) )

# pass in which MainWidget to run as a command-line arg
run(MainWidget)