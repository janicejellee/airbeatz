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
from common.mixer import *
from common.modifier import *
from common.clock import *
from common.metro import *
from common.wavesrc import *
from common.wavegen import *

import numpy as np

# Choose your mode:
# MODE = 'kinect'
MODE = 'leap'

if MODE == 'leap':
    from common.leaputil import *
    import Leap

if MODE == 'kinect':
    from common.kinect import *

cmaj = [60, 62, 64, 65, 67, 69, 71, 72]
class MainWidget(BaseWidget) :
    def __init__(self):
        super(MainWidget, self).__init__()

        self.audio = Audio(2)
        self.synth = Synth("../data/FluidR3_GM.sf2")
        self.tempo_map  = SimpleTempoMap(120)
        self.sched = AudioScheduler(self.tempo_map)
        self.sched.set_generator(self.synth)

        # create mixer to use wave buffers
        self.mixer = Mixer()
        self.mixer.set_gain(0.2)
        self.mixer.add(self.sched)
        self.audio.set_generator(self.mixer)

        self.wave_file = WaveFile("../data/daft_punk.wav")
        self.wave_gen = None

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

    def start(self):
        self.wave_gen = WaveGenerator(self.wave_file)
        self.mixer.add(self.wave_gen)

    def stop(self):
      self.mixer.remove(self.wave_gen)
      self.wave_gen = None

    def on_key_down(self, keycode, modifiers):
        if keycode[1] == 's':
          if self.wave_gen is None:
            self.start()
          else:
            self.stop()

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
