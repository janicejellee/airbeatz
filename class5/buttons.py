#####################################################################
#
# buttons.py
#
# Copyright (c) 2018, Eran Egozy
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

from common.kinect import *
import Leap



# change button type here
kButtonType = 'push'
# kButtonType = 'relpush'
# kButtonType = 'hover'

# for use with scale_point
kLeapRange = ( (-250, 250), (50, 600), (-200, 250) )



# UI Button for use with a 3D sensor
class SensorButton(InstructionGroup) :
    border_color = (.4, .6, .5)
    active_color = (.4, .6, .3)
    on_color     = (.4, .6, .7)

    def __init__(self, size = (150,100), pos = (200,200), btype='push'):
        super(SensorButton, self).__init__()

        # button type
        self.btype = btype

        # button state
        self.is_on = False
        self.active_progress = 0

        # bounds of this button, for intersection detection
        self.x_bounds = (pos[0], pos[0] + size[0])
        self.y_bounds = (pos[1], pos[1] + size[1])

        # inside rectange coordinates
        margin = int(.1 * size[0])
        self.size2 = np.array(size) - margin
        self.pos2 = np.array(pos) + 0.5*margin

        # inside part
        self.inside_color = Color(hsv=SensorButton.active_color)
        self.add( self.inside_color )
        self.inside_rect = Rectangle(size = (0,0), pos = self.pos2) 
        self.add( self.inside_rect )

        # border of button
        half_m = int(margin/2)
        self.add( Color(hsv=SensorButton.border_color) )
        self.add( Line(rectangle = (pos[0]+half_m, pos[1]+half_m, size[0]-margin, size[1]-margin), width=half_m))

    def on_cursor_pos(self, pos, z) :
        # collision detection
        x,y = pos
        collide = self.x_bounds[0] < x and x < self.x_bounds[1] and self.y_bounds[0] < y and y < self.y_bounds[1]

        if not collide:
            self.is_on = False
            self.active_progress = 0

        # push behavior: z-based activation
        if collide and self.btype == 'push':
            if not self.is_on and z < 0.5:
                self.is_on = True
                self.active_progress = 1
            if self.is_on and z > 0.52:
                self.is_on = False
                self.active_progress = 0

        # hover behavior: timer-based activation
        if collide and self.btype == 'hover':
            self.active_progress += (kivyClock.frametime / 1.0)
            if self.active_progress > 1.0:
                self.is_on = True
                self.active_progress = 1

        # relative push:
        if collide and self.btype == 'relpush' and not self.is_on:
            if self.active_progress == 0:
                self.z_anchor = z
            self.active_progress = np.clip( 5. * (self.z_anchor - z), 0.01, 1)
            if self.active_progress == 1.0:
                self.is_on = True


        # button look based on state:
        self.inside_rect.size = (self.size2[0], self.size2[1] * self.active_progress)
        self.inside_color.hsv = SensorButton.on_color if self.is_on else SensorButton.active_color


# creates a 2D grid of SensorButtons
class Grid(InstructionGroup) :
    def __init__(self, pos, size, grid_dimensions):
        super(Grid, self).__init__()

        self.pos = np.array(pos)

        # grid geometry calculations
        num_x, num_y = grid_dimensions
        but_w = size[0] / float(num_x)
        but_h = size[1] / float(num_y)

        margin = but_w * 0.1
        but_size = (but_w - margin, but_h - margin)

        # locate entire grid to position pos
        self.add(PushMatrix())
        self.add(Translate(*pos))

        self.buttons = [ SensorButton( size=but_size, pos=(x*but_w, y*but_h), btype=kButtonType ) 
                         for x in range(num_x) for y in range(num_y)  ]
        for b in self.buttons:
            self.add(b)

        self.add(PopMatrix())

    def on_cursor_pos(self, pos, z):
        trans_pos = np.array(pos) - self.pos
        for b in self.buttons:
            b.on_cursor_pos(trans_pos, z)


class MainWidget1(BaseWidget) :
    def __init__(self):
        super(MainWidget1, self).__init__()

        self.leap = Leap.Controller()

        grid_dims = (6, 4)
        margin    = 20
        grid_pos  = (margin,margin)
        grid_size = (Window.width - 2 * margin, Window.height - 2 * margin)
        self.grid = Grid( pos = grid_pos, 
                          size = grid_size,
                          grid_dimensions = grid_dims) 
        self.canvas.add(self.grid)

        self.hand_disp = Cursor3D(grid_size, grid_pos, (.4, .4, .4))
        self.canvas.add(self.hand_disp)

        self.label = topleft_label()
        self.add_widget(self.label)

    def on_update(self) :
        leap_frame = self.leap.frame()
        norm_pt = scale_point(leap_one_palm(leap_frame), kLeapRange)

        self.hand_disp.set_pos(norm_pt)
        screen_xy = self.hand_disp.get_screen_xy()
        self.grid.on_cursor_pos(screen_xy, norm_pt[2])

        self.label.text = leap_info(self.leap)
        self.label.text += 'x=%.2f y=%.2f z=%.2f\n' % tuple(norm_pt.tolist())



run(MainWidget1)
