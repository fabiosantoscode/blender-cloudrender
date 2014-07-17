
import bpy

import sys; sys.path.append('.')

from cloudrender.crowdprocess import CrowdProcess

from cloudrender.operators import render, viewport_divisions

import testconfig

scene = bpy.data.scenes['Scene']
crowdprocess = CrowdProcess(testconfig.USERNAME, testconfig.PASSWORD)

# print(list(viewport_divisions(100, 100, 11)))


render(scene=scene, crowdprocess=crowdprocess)

