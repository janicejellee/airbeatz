# lecture5.py


# For complete documentation on Leap Motion see:
# https://developer.leapmotion.com/documentation/v2/python/index.html

# common import
import sys
sys.path.append('..')
from common.core import *
from common.gfxutil import *

from kivy.uix.widget import Widget
from kivy.graphics import Color, Ellipse, Line
from kivy.graphics.instructions import InstructionGroup

import numpy as np

# Kinect import
from common.kinect import *

# leap motion imports
from common.leaputil import *
import Leap


# get basic Kinect module working - showing data from right-hand position
class MainWidget1(BaseWidget) :
    def __init__(self):
        super(MainWidget1, self).__init__()

        self.label = topleft_label()
        self.add_widget(self.label)

        self.kinect = Kinect()
        self.kinect.add_joint(Kinect.kRightHand)

    def on_update(self) :
        self.kinect.on_update()
        pt = self.kinect.get_joint(Kinect.kRightHand)
        self.label.text = 'x:%d\ny:%d\nz:%d\n' % (pt[0], pt[1], pt[2])



# for use with scale_point
# x, y, and z ranges to define a 3D bounding box
kKinectRange = ( (-250, 700), (-200, 700), (-500, 0) )

# set up size / location of 3DCursor object
kMargin = Window.width * 0.05
kCursorSize = Window.width - 2 * kMargin, Window.height - 2 * kMargin
kCursorPos = kMargin, kMargin

# show a single hand graphically with cursor3D
class MainWidget2(BaseWidget) :
    def __init__(self):
        super(MainWidget2, self).__init__()

        self.label = topleft_label()
        self.add_widget(self.label)

        self.kinect = Kinect()
        self.kinect.add_joint(Kinect.kRightHand)

        self.right_hand = Cursor3D(kCursorSize, kCursorPos, (.2, .6, .2))
        self.canvas.add(self.right_hand)

    def on_update(self) :
        self.kinect.on_update()

        pt = self.kinect.get_joint(Kinect.kRightHand)
        norm_pt = scale_point(pt, kKinectRange)

        self.label.text = 'x:%d   %.2f\ny:%d   %.2f\nz:%d   %.2f\n' %  (pt[0], norm_pt[0], pt[1], norm_pt[1], pt[2], norm_pt[2])

        self.right_hand.set_pos(norm_pt)


kKinectRange2 = ( (-750, 750), (-200, 1000), (-500, 0) )

# More points - left, right hands and head
class MainWidget3(BaseWidget) :
    def __init__(self):
        super(MainWidget3, self).__init__()

        self.label = topleft_label()
        self.add_widget(self.label)

        self.kinect = Kinect()
        self.kinect.add_joint(Kinect.kRightHand)
        self.kinect.add_joint(Kinect.kLeftHand)
        self.kinect.add_joint(Kinect.kHead)

        self.left_hand = Cursor3D(kCursorSize, kCursorPos, (.6, .2, .2))
        self.canvas.add(self.left_hand)

        self.right_hand = Cursor3D(kCursorSize, kCursorPos, (.2, .6, .2))
        self.canvas.add(self.right_hand)

        self.head = Cursor3D(kCursorSize, kCursorPos, (.2, .2, .6))
        self.canvas.add(self.head)

    def on_update(self) :
        self.kinect.on_update()

        left_pt =  scale_point( self.kinect.get_joint(Kinect.kRightHand), kKinectRange2)
        right_pt = scale_point( self.kinect.get_joint(Kinect.kLeftHand), kKinectRange2)
        head_pt =  scale_point( self.kinect.get_joint(Kinect.kHead), kKinectRange2)

        self.left_hand.set_pos(right_pt)
        self.right_hand.set_pos(left_pt)
        self.head.set_pos(head_pt)



# Leap Controller is very similar to Kinect. Define a smaller range for the hands bounding box
kLeapRange = ( (-250, 250), (50, 600), (-200, 250) )

class MainWidget4(BaseWidget) :
    def __init__(self):
        super(MainWidget4, self).__init__()

        self.label = topleft_label()
        self.add_widget(self.label)

        self.leap = Leap.Controller()

        self.left_hand = Cursor3D(kCursorSize, kCursorPos, (.6, .2, .2))
        self.canvas.add(self.left_hand)

        self.right_hand = Cursor3D(kCursorSize, kCursorPos, (.2, .6, .2))
        self.canvas.add(self.right_hand)


    def on_update(self) :
        leap_frame = self.leap.frame()

        pt1, pt2 = leap_two_palms(leap_frame)

        norm_pt1 = scale_point(pt1, kLeapRange)
        norm_pt2 = scale_point(pt2, kLeapRange)

        self.left_hand.set_pos(norm_pt1)
        self.right_hand.set_pos(norm_pt2)

        self.label.text = leap_info(self.leap)
        self.label.text += 'x=%.2f y=%.2f z=%.2f\n' % tuple(norm_pt1.tolist())
        self.label.text += 'x=%.2f y=%.2f z=%.2f\n' % tuple(norm_pt2.tolist())



# show 5 finger positions of a single hand graphically
class MainWidget5(BaseWidget) :
    def __init__(self):
        super(MainWidget5, self).__init__()

        self.label = topleft_label()
        self.add_widget(self.label)

        self.leap = Leap.Controller()

        self.finger_disp = []
        for x in range(5):
            disp = Cursor3D(kCursorSize, kCursorPos, (.2, .6, .2), size_range=(5, 20))
            self.canvas.add(disp)
            self.finger_disp.append(disp)

    def on_update(self) :
        leap_frame = self.leap.frame()

        pts = leap_fingers(leap_frame)
        norm_pts = [scale_point(pt, kLeapRange) for pt in pts]

        for i, pt in enumerate(norm_pts):
            self.finger_disp[i].set_pos(pt)

        self.label.text = leap_info(self.leap)



# Demonstrate the Clap Gesture: Tracks the 2 hands and displays the Pop object
# when the hands clap
class MainWidget6(BaseWidget) :
    def __init__(self):
        super(MainWidget6, self).__init__()

        self.label = topleft_label()
        self.add_widget(self.label)

        self.leap = Leap.Controller()

        self.left_hand = Cursor3D(kCursorSize, kCursorPos, (.6, .2, .2))
        self.canvas.add(self.left_hand)

        self.right_hand = Cursor3D(kCursorSize, kCursorPos, (.2, .6, .2))
        self.canvas.add(self.right_hand)

        self.anims = AnimGroup()
        self.canvas.add(self.anims)

        self.clap = ClapGesture(self.on_clap)

    def on_update(self) :
        leap_frame = self.leap.frame()

        pt1, pt2 = leap_two_palms(leap_frame)

        # feed data to clap gesture detector
        self.clap.on_set_positions(pt1, pt2)

        norm_pt1 = scale_point(pt1, kLeapRange)
        norm_pt2 = scale_point(pt2, kLeapRange)

        self.left_hand.set_pos(norm_pt1)
        self.right_hand.set_pos(norm_pt2)

        self.label.text = leap_info(self.leap)
        self.label.text += 'x=%d y=%d z=%d\n' % tuple(pt1.tolist())
        self.label.text += 'x=%d y=%d z=%d\n' % tuple(pt2.tolist())
        self.label.text += 'dist = %d\n' % np.linalg.norm(pt1 - pt2)

        self.anims.on_update()

    # callback happens when a clap is detected.
    def on_clap(self, pos):
        norm_pos = scale_point(pos, kLeapRange)[0:2]

        # convert to screen coordinates for display
        screen_pos = self.left_hand.to_screen_coords(norm_pos)

        # create a graphic that shows the clap
        pop = Pop(screen_pos)
        self.anims.add(pop)





# A clap gesture detector. Notifies a callback when a clap is detected.
# the callback function takes a single argument: pos (3D point)
class ClapGesture(object):
    def __init__(self, callback):
        super(ClapGesture, self).__init__()
        self.callback = callback

        self.clap_thresh = 70
        self.unclap_thresh = 100

        self.is_clapped = False

    def on_set_positions(self, left_pt, right_pt):
        
        # both hands must be active to proceed
        if np.all(left_pt == 0) or np.all(right_pt == 0):
            return

        dist = np.linalg.norm( left_pt - right_pt )
        if dist < self.clap_thresh and not self.is_clapped:
            print("clap!!")

            mid_point = (left_pt + right_pt) / 2

            self.callback(mid_point)

            self.is_clapped = True

        if dist > self.unclap_thresh and self.is_clapped:
            self.is_clapped = False
            print("UN clap!!")


# An animation / display to go along with the Clap Gesture
class Pop(InstructionGroup) :
    def __init__(self, pos):
        super(Pop, self).__init__()

        self.color = Color(1,0,0,1)
        self.add(self.color)

        self.circle = CEllipse(cpos = pos)
        self.add(self.circle)

        # create keyframe animation: a frame is: (time, alpha radius)
        self.anim = KFAnim((0,   1, 30),
                           (0.5, 0, 60),)

        self.time = 0
        self.on_update(0)

    def on_update(self, dt):
        values = self.anim.eval(self.time)
        self.color.a = values[0]
        self.circle.csize = values[1] * 2, values[1] * 2
        self.time += dt

        return self.anim.is_active(self.time)



# Example using Leap's built-in Circle Gesture
class MainWidget7(BaseWidget) :
    def __init__(self):
        super(MainWidget7, self).__init__()

        self.label = topleft_label()
        self.add_widget(self.label)

        self.leap = Leap.Controller()
        self.leap.enable_gesture(Leap.Gesture.TYPE_CIRCLE)

        self.hand = Cursor3D(kCursorSize, kCursorPos, (.2, .6, .2))
        self.canvas.add(self.hand)

        self.expired_gestures = []

        self.anims = AnimGroup()
        self.canvas.add(self.anims)

    def _on_circle(self, pt) :
        print('CIRCLE')
        norm_pt = scale_point(pt, kLeapRange)[0:2]

        # convert to screen coordinates for display
        screen_pos = self.hand.to_screen_coords(norm_pt)

        # create a graphic that shows the gestures
        pop = Pop(screen_pos)
        self.anims.add(pop)

    def on_update(self) :
        self.anims.on_update()
        leap_frame = self.leap.frame()

        pt = leap_one_palm(leap_frame)
        norm_pt = scale_point(pt, kLeapRange)

        self.hand.set_pos(norm_pt)

        # Gather all currently active circle gestures
        gestures = leap_frame.gestures()
        circles = [Leap.CircleGesture(g) for g in gestures if g.type is Leap.Gesture.TYPE_CIRCLE]

        if len(circles) == 0:
            self.expired_gestures = []

        self.label.text = leap_info(self.leap)

        for g in circles:
            # show progress of all current active circles.
            self.label.text += 'circle id:%d state:%d prog:%.1f\n' % (g.id, g.state, g.progress)

            # if we see a completed circle (a bit more than a full circle), 
            # call the callback, and make sure to not call it again for this particular gesture.
            if g.progress > 1.2 and g.id not in self.expired_gestures:
                self.expired_gestures.append(g.id)
                self._on_circle(pt)


# pass in which MainWidget to run as a command-line arg
run(eval('MainWidget' + sys.argv[1]))
