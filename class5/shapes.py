#####################################################################
#
# shapes.py
#
# Copyright (c) 2019, Eran Egozy
#
# Released under the MIT License (http://opensource.org/licenses/MIT)
#
#####################################################################


# common import
import sys
sys.path.append('..')
from common.core import *
from common.gfxutil import *
from common.leaputil import *

from kivy.uix.widget import Widget
from kivy.graphics import Color, Ellipse, Rectangle, Line, Translate
from kivy.graphics.instructions import InstructionGroup

import numpy as np
import Leap
import random

# for use with scale_point
kLeapRange = ( (-250, 250), (50, 600), (-200, 250) )


# create a closed line shape (with random color) 
# as a separate object that falls down.
class Blob(InstructionGroup):
    def __init__(self, points):
        super(Blob, self).__init__()
        self.points = points        

        self.color = Color(hsv = (random.random(), .7, 1))
        self.trans = Translate()
        self.line = Line(points = points.copy(), width = 3, close = True)

        self.add(PushMatrix())
        self.add(self.trans)
        self.add(self.color)
        self.add(self.line)
        self.add(PopMatrix())

        self.time = 0

    def on_update(self, dt):

        self.trans.y = -(self.time * 20) ** 2
        self.time += dt

        return self.trans.y > -1000


class Surface(InstructionGroup):
    def __init__(self, anim_group):
        super(Surface, self).__init__()
        
        self.line = Line(width = 3)
        self.add(self.line)

        self.anim_group = anim_group

        self.pen_down = False

        self.last_pt = np.zeros(2)
        self.line_points = []
        self.points = []

    def on_cursor_pos(self, pt, z):
        if z < .5:
            self.pen_down = True
        elif z > .6:
            self.pen_down = False
            self.last_pt = pt
            self.line_points = []
            self.points = []

        dist = np.linalg.norm( pt - self.last_pt )
        if self.pen_down and dist > 4:
            self._add_new_point( pt )
            self.last_pt = pt

    def is_active(self):
        return self.pen_down

    def _add_new_point(self, new_pt):
        self.points.append(new_pt)
        self.line_points += ( new_pt[0], new_pt[1] )
        self.line.points = self.line_points

        # check for closed loop:
        end_bit = 20
        if len(self.points) > end_bit:
            for i, p in enumerate(self.points[:-end_bit]):
                dist = np.linalg.norm( new_pt - p )
                if dist < 8:
                    self._close_shape(i*2)
                    break

    def _close_shape(self, start_idx):
        self.anim_group.add( Blob(self.line_points[start_idx:]) )
        self.line_points = []
        self.points = []



class MainWidget(BaseWidget) :
    def __init__(self):
        super(MainWidget, self).__init__()

        self.leap = Leap.Controller()

        margin    = Window.width * .025
        surface_pos  = (margin,margin)
        surface_size = (Window.width - 2 * margin, Window.height - 2 * margin)

        self.anim_group = AnimGroup()
        self.surface = Surface(self.anim_group) 
        self.hand = Cursor3D(surface_size, surface_pos, (.4, .4, .4))

        self.canvas.add(self.surface)
        self.canvas.add(self.hand)
        self.canvas.add(self.anim_group)

        self.label = topleft_label()
        self.add_widget(self.label)

    def on_update(self) :
        leap_frame = self.leap.frame()
        norm_pt = scale_point(leap_one_palm(leap_frame), kLeapRange)

        self.hand.set_pos(norm_pt)
        screen_xy = np.array( self.hand.get_screen_xy() )
        self.surface.on_cursor_pos(screen_xy, norm_pt[2])

        if self.surface.is_active():
            self.hand.set_color( (.8, .1, .1) )
        else:
            self.hand.set_color( (.4, .4, .4) )


        self.anim_group.on_update()

        self.label.text = leap_info(self.leap)
        self.label.text += 'x=%.2f y=%.2f z=%.2f\n' % tuple(norm_pt.tolist())



run(MainWidget)
