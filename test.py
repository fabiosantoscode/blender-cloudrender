
import bpy

import sys; sys.path.append('.')

from cloudrender.crowdprocess import CrowdProcess

from cloudrender.operators import render

import testconfig

scene = bpy.data.scenes['Scene']
crowdprocess = CrowdProcess(testconfig.USERNAME, testconfig.PASSWORD)

render(scene=scene, crowdprocess=crowdprocess)

