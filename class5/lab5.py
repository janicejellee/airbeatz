# lab5.py


# For complete documentation see:
# https://developer.leapmotion.com/documentation/v2/python/index.html

# common import
import sys
sys.path.append('..')
from common.core import *
from common.gfxutil import *
from common.synth import *
from common.audio import *

import numpy as np

# Choose your mode:
# MODE = 'kinect'
MODE = 'leap'

if MODE == 'leap':
    from common.leaputil import *
    import Leap

if MODE == 'kinect':
    from common.kinect import *


# Create a "one-handed Leap Theramin" according to this spec:
#
#  a. When the hand breaks through the XY plane (at some value of z), a note will play.
#     The pitch of the note is determined by the height of the hand, and mapped to a 
#     1-octave c-major scale. The note turns off when the hand is pulled out of the XY plane.
#     Also, choose a sustaining sound - like a string, wind, or brass instrument.
#
#  b. Modify the system so as the hand moves up and down, the sounding note changes according
#     to the same mapping of height to c-major scale.
#
#  c. Add volume control, mapping the x position of the hand to volume. Recall that volume is 
#     sent as: synth.cc(channel, 7, v) where v = [0, 127]

cmaj = [60, 62, 64, 65, 67, 69, 71, 72]
class MainWidget(BaseWidget) :
    def __init__(self):
        super(MainWidget, self).__init__()

        self.audio = Audio(2)
        self.synth = Synth("../data/FluidR3_GM.sf2")
        self.audio.set_generator(self.synth)

        self.volume = 60
        self.channel = 0

        self.synth.program(self.channel, 0, 22)

        if MODE == 'leap':
            self.leap = Leap.Controller()
        elif MODE == 'kinect':
            self.kinect = Kinect()
            self.kinect.add_joint(Kinect.kRightHand)

        # set up size / location of 3DCursor object
        kMargin = Window.width * 0.05
        kCursorSize = Window.width - 2 * kMargin, Window.height - 2 * kMargin
        kCursorPos = kMargin, kMargin

        self.hand_disp = Cursor3D(kCursorSize, kCursorPos, (.2, .6, .2))
        self.canvas.add(self.hand_disp)

        self.label = topleft_label()
        self.add_widget(self.label)

        self.idx = 0
        self.playing = False

    def on_update(self) :
        self.audio.on_update()

        self.label.text = ''

        if MODE == 'leap':
            self.label.text += leap_info(self.leap)            
            leap_frame = self.leap.frame()
            pt = leap_one_palm(leap_frame)
            norm_pt = scale_point(pt, kLeapRange)
            
            if norm_pt[2] >= 1:
                self.playing = False
                self.synth.noteoff(self.channel, cmaj[self.idx])
            else:
                idx = int((norm_pt[1] + 1) * len(cmaj) / 2)
                if self.idx != idx:
                    self.synth.noteoff(self.channel, cmaj[self.idx])
                    self.idx = idx
                    self.synth.noteon(self.channel, cmaj[self.idx], self.volume)
            # delta_pitch = abs(kLeapRange[0][0] - kLeapRange[0][1])

        elif MODE == 'kinect':
            self.kinect.on_update()
            pt = self.kinect.get_joint(Kinect.kRightHand)
            norm_pt = scale_point(pt, kKinectRange)

        self.hand_disp.set_pos(norm_pt)

        self.label.text += 'x=%d y=%d z=%d\n' % (pt[0], pt[1], pt[2])
        self.label.text += 'x=%.2f y=%.2f z=%.2f\n' % (norm_pt[0], norm_pt[1], norm_pt[2])


# for use with scale_point:
# x, y, and z ranges to define a 3D bounding box
kKinectRange = ( (-250, 700), (-200, 700), (-500, 0) )
kLeapRange   = ( (-250, 250), (100, 500), (-200, 250) )


run(MainWidget)