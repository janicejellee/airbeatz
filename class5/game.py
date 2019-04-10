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
from common.kivyparticle import ParticleSystem

import numpy as np
import random

# Choose your mode:
# MODE = 'kinect'
MODE = 'leap'

if MODE == 'leap':
    from common.leaputil import *
    import Leap

if MODE == 'kinect':
    from common.kinect import *

def parse_gem_data(gem_data_path):
    buffers = {}
    f = open(gem_data_path)
    lines = f.readlines()
    gems = []
    for line in lines:
        tokens = line.strip().split('\t')
        time = float(tokens[0])
        gems.append(time)
        # x_position = int(tokens[1])
        # gems.append((time, x_position))
    print(gems)
    return gems

line_y = 80
disappear_y = -25
falling_seconds = 2

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

        self.wave_file = WaveFile("../data/mario.wav")
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

        # draws hit line
        # i tried to make a gradient but didn't work out lol, might add later

        c1 = Color(77/255, 148/255, 255/255, 0.5)
        # c2 = Color(153/255, 255/255, 187, 0.5) # green
        # c3 = Color(204/255, 51/255, 0, 0.5) # lol i forgot

        # line_pts_top2 = [0, 86, Window.width, 86]
        # line_pts_top1 = [0, 83, Window.width, 83]
        line_pts_mid = [0, line_y, Window.width, line_y]
        # line_pts_bot1 = [0, 77, Window.width, 77]
        # line_pts_bot2 = [0, 76, Window.width, 76]

        # hit_line_top2 = Line(points=line_pts_top2, width=3)
        # hit_line_top1 = Line(points=line_pts_top1, width=3)
        hit_line_mid = Line(points=line_pts_mid, width=5)
        # hit_line_bot1 = Line(points=line_pts_bot1, width=3)
        # hit_line_bot2 = Line(points=line_pts_bot2, width=3)

        self.canvas.add(c1);
        self.canvas.add(hit_line_mid);
        # self.canvas.add(c2);
        # self.canvas.add(hit_line_top1);
        # self.canvas.add(hit_line_bot1);
        # self.canvas.add(c3);
        # self.canvas.add(hit_line_top2);
        # self.canvas.add(hit_line_bot2);

        self.x_positions = [(Window.width - 100) / 6 * i + 50 for i in range(6)]

        self.objects = AnimGroup()
        # circle = NoteCircle(20)
        # circle.fall()
        # self.objects.add(circle)
        # self.canvas.add(self.objects)

        # particle system
        self.particle_systems = []
        #
        # ps = ParticleSystem('particle/particle.pex')
        # ps.emitter_x = 100
        # ps.emitter_y = Window.height
        # ps.start()
        # self.add_widget(ps)
        # self.particle_systems.append([ps,True])

        self.star_index = 0
        self.time_checker_index = 0
        self.clock = Clock()

        self.gem_data_path = "../data/gem_data.txt"
        self.time_instants = parse_gem_data(self.gem_data_path)
        self.times = [(time, random.random() * (Window.width - 400) + 200) for time in self.time_instants]

    def add_falling_star(self, x, start_time):
        ps = ParticleSystem('particle/particle.pex')
        ps.emitter_x = x
        ps.emitter_y = Window.height
        ps.start()
        self.add_widget(ps)
        # self.particle_systems.append([ps, True])
        total_seconds = falling_seconds / (Window.height - line_y) * (Window.height - disappear_y)
        y_anim = KFAnim((0, Window.height), (total_seconds, disappear_y))
        self.particle_systems.append([ps, y_anim, start_time])

    def start(self):
        self.wave_gen = WaveGenerator(self.wave_file)
        self.mixer.add(self.wave_gen)

    def stop(self):
        self.mixer.remove(self.wave_gen)
        self.wave_gen = None
        for ps_info in self.particle_systems[self.star_index:]:
            # print (self.particle_systems)
            ps, y_anim, start_time = ps_info
            self.remove_widget(ps)
        self.particle_systems = []
        self.time_checker_index = 0

    def on_key_down(self, keycode, modifiers):
        if keycode[1] == 's':
            if self.wave_gen is None:
                self.start()
            else:
                self.stop()

    def on_update(self) :
        self.audio.on_update()

        self.objects.on_update()

        self.label.text = ''

        if MODE == 'leap':
            self.label.text += leap_info(self.leap)
            leap_frame = self.leap.frame()
            pt = leap_one_palm(leap_frame)
            norm_pt = scale_point(pt, kLeapRange)

        elif MODE == 'kinect':
            self.kinect.on_update()
            pt = self.kinect.get_joint(Kinect.kRightHand)
            norm_pt = scale_point(pt, kKinectRange)

        self.hand_disp.set_pos(norm_pt)

        self.label.text += 'x=%d y=%d z=%d\n' % (pt[0], pt[1], pt[2])
        self.label.text += 'x=%.2f y=%.2f z=%.2f\n' % (norm_pt[0], norm_pt[1], norm_pt[2])
        if self.wave_gen is not None:
            self.label.text += 'frame=%.2f\n' % (self.wave_gen.frame)
            self.label.text += 'seconds=%.2f\n' % (self.wave_gen.frame / Audio.sample_rate)

            seconds = self.wave_gen.frame / Audio.sample_rate
            
            # testing times
            if (self.time_checker_index < len(self.times)):
                time, x = self.times[self.time_checker_index]
                # current_time = self.clock.get_time()
                # if current_time > time:
                if seconds + falling_seconds > time:
                    # self.add_falling_star(x, current_time)
                    self.add_falling_star(x, seconds)
                    self.time_checker_index += 1

            for ps_info in self.particle_systems[self.star_index:]:
                ps, y_anim, start_time = ps_info
                y = y_anim.eval(seconds - start_time)
                # y = y_anim.eval(self.clock.get_time() - start_time)
                # ps.emitter_y = ps.emitter_y - 5
                ps.emitter_y = y
                if ps.emitter_y < disappear_y + 5:
                    self.star_index += 1
                    self.remove_widget(ps)
                    ps.stop()

        return True

# for use with scale_point:
# x, y, and z ranges to define a 3D bounding box
kKinectRange = ( (-250, 700), (-200, 700), (-500, 0) )
kLeapRange   = ( (-250, 250), (100, 500), (-200, 250) )

# run(NoteCircle)
run(MainWidget)
