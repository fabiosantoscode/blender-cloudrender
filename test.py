
import bpy

import sys; sys.path.append('.')

from cloudrender.crowdprocess import CrowdProcess

from cloudrender.operators import render, viewport_divisions

import testconfig

scene = bpy.data.scenes['Scene']
crowdprocess = CrowdProcess(testconfig.USERNAME, testconfig.PASSWORD)

assert list(viewport_divisions(10, 10, 5)) == [
    (0, 0, 5, 5), (5, 0, 5, 5),
    (0, 5, 5, 5), (5, 5, 5, 5)
]

assert list(viewport_divisions(9, 9, 5)) == [
    (0, 0, 5, 5), (5, 0, 4, 5),
    (0, 5, 5, 4), (5, 5, 4, 4)
]

assert list(viewport_divisions(1, 1, 5)) == [ (0, 0, 1, 1) ]

# render(scene=scene, crowdprocess=crowdprocess)

