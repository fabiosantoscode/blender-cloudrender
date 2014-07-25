# ##### BEGIN GPL LICENSE BLOCK #####
#
#  This program is free software; you can redistribute it and/or
#  modify it under the terms of the GNU General Public License
#  as published by the Free Software Foundation; either version 2
#  of the License, or (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software Foundation,
#  Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
#
# ##### END GPL LICENSE BLOCK #####

bl_info = {
    "name": "CloudRender (Crowdprocess-powered distributed rendering)",
    "author": "Fábio Santos <fabiosantosart@gmail.com>",
    "version": (0,),
    "blender": (2, 63, 0),
    "location": "Render > Engine > CloudRender",
    "description": "Render the current scene using CloudRender",
    "warning": "",
    "wiki_url": "",
    "category": "Render"}

import bpy
import math
from os.path import isabs, isfile, join, exists
import os
import time

from bpy.props import PointerProperty, StringProperty, BoolProperty, EnumProperty, IntProperty, CollectionProperty

from .panels import *
from .operators import *



bpy.CURRENT_VERSION = bl_info["version"][0]
bpy.found_newer_version = False
bpy.up_to_date = False
bpy.download_location = 'http://www.renderfarm.fi/blender'

bpy.rffi_creds_found = False
bpy.rffi_user = ''
bpy.rffi_hash = ''
bpy.passwordCorrect = False
bpy.loginInserted = False
bpy.rffi_accepting = False
bpy.rffi_motd = ''

bpy.errorMessages = {
    'missing_desc': 'You need to enter a title, short and long description',
    'missing_creds': 'You haven\'t entered your credentials yet'
}

bpy.statusMessage = {
    'title': 'TRIA_RIGHT',
    'shortdesc': 'TRIA_RIGHT',
    'tags': 'TRIA_RIGHT',
    'longdesc': 'TRIA_RIGHT',
    'username': 'TRIA_RIGHT',
    'password': 'TRIA_RIGHT'
}

bpy.errors = []
bpy.ore_sessions = []
bpy.ore_completed_sessions = []
bpy.ore_active_sessions = []
bpy.ore_rejected_sessions = []
bpy.ore_pending_sessions = []
bpy.ore_active_session_queue = []
bpy.ore_complete_session_queue = []
bpy.queue_selected = -1
bpy.errorStartTime = -1.0
bpy.infoError = False
bpy.cancelError = False
bpy.texturePackError = False
bpy.linkedFileError = False
bpy.uploadInProgress = False
try:
    bpy.originalFileName = bpy.data.filepath
except:
    bpy.originalFileName = 'untitled.blend'
bpy.particleBakeWarning = False
bpy.childParticleWarning = False
bpy.simulationWarning = False
bpy.file_format_warning = False
bpy.ready = False


def renderEngine(render_engine):
    bpy.utils.register_class(render_engine)
    return render_engine

class ORESession(bpy.types.PropertyGroup):
    name = StringProperty(name='Name', description='Name of the session', maxlen=128, default='[session]')

class ORESettings(bpy.types.PropertyGroup):
    username = StringProperty(name='E-mail', description='E-mail for Renderfarm.fi', maxlen=256, default='')
    password = StringProperty(name='Password', description='Renderfarm.fi password', maxlen=256, default='')

# session struct

class RENDERFARM_MT_Session(bpy.types.Menu):
    bl_label = "Show Session"

    def draw(self, context):
        layout = self.layout
        ore = context.scene.ore_render

        if (bpy.loginInserted == True):
            layout.operator('ore.completed_sessions')
            layout.operator('ore.accept_sessions')
            layout.operator('ore.active_sessions')
            layout.separator()
            layout.operator('ore.cancelled_sessions')
        else:
            row = layout.row()
            row.label(text="You must login first")


from itertools import zip_longest

def chunks(iterable, chunksize, filler=None):
    return zip_longest(*[iter(iterable)]*chunksize, fillvalue=filler)

class CloudRender(bpy.types.RenderEngine):
    bl_idname = 'RENDERFARMFI_RENDER'
    bl_label = 'CloudRender'
    bl_use_preview = False
    bl_use_shading_nodes = True

    def render(self, scene):
        import json

        resolution_fraction = (100 / scene.render.resolution_percentage)
        self.height, self.width = (
            int(scene.render.resolution_y / resolution_fraction),
            int(scene.render.resolution_x / resolution_fraction),
        )

        self.make_job(scene)

        self.image = [(0,0,0,1)] * self.height * self.width
        tiles_to_go = set(viewport_divisions(self.height, self.width))

        self.result = self.begin_result(0, 0, self.width, self.height)

        tiles_total = len(tiles_to_go)
        tiles_done = 1

        for retry in range(5):
            if not tiles_to_go:
                break

            if retry > 0:
                print('Retrying some tiles... %d' % retry)

            job_data = (
                { 'x': x, 'y': y, 'w': w, 'h': h }
                for x, y, w, h in tiles_to_go)

            for tile in self.job(job_data).results:
                tile_data = (tile['x'], tile['y'],
                    tile['w'], tile['h'])
                self.draw_tile(*tile_data, tile=tile['tile'])
                tiles_to_go.remove(tile_data)
                tiles_done += 1
                self.update_progress(tiles_done / tiles_total)

        self.result.layers[0].rect = self.image
        self.end_result(self.result)
        self.job.delete()

    def draw_tile(self, x, y, w, h, tile):
        pixel_colors = chunks((color / 255 for color in tile), 4)
        pixel_colors = [tuple(color) for color in pixel_colors]

        assert x >= 0 and x + w <= self.width
        assert y >= 0 and y + h <= self.height
        assert len(pixel_colors) == len(self.image)

        for y_coord in range(y, y + h):
            for x_coord in range(x, x + w):
                ind = (y_coord * self.width) + x_coord
                self.image[ind] = pixel_colors[ind]

        self.result.layers[0].rect = self.image
        self.update_result(self.result)


    def make_job(self, scene):
        from io import StringIO
        import json
        from .xml_exporter.io_scene_cycles.export_cycles import export_cycles
        from .crowdprocess import CrowdProcess

        fp = StringIO()

        export_cycles(fp=fp, scene=scene)
        scene_xml = fp.getvalue()

        # scene_xml = open('example_scene.xml').read()
        emcycles_core = open('cloudrender/emcycles/cloudrender_core.js').read()

        crowdprocess_func = '''
            function Run(data) {
                var Module = {
                    print: function () {},
                    tileX: data.x,
                    tileY: data.y,
                    tileH: data.h,
                    tileW: data.w
                }

                var SCENE = %s;
                var INCLUDES = [];

                %s;

                data.tile = Module.imageData

                return data
            }
        ''' % (json.dumps(scene_xml), emcycles_core)

        open('/tmp/wow.js', 'w').write(crowdprocess_func)

        crowdprocess = CrowdProcess(
            scene.ore_render.username, scene.ore_render.password)

        crowdprocess = CrowdProcess(
            scene.ore_render.username, scene.ore_render.password)

        self.job = crowdprocess.job(crowdprocess_func)



def register():
    bpy.utils.register_module(__name__)
    bpy.types.Scene.ore_render = PointerProperty(type=ORESettings, name='ORE Render', description='ORE Render Settings')

def unregister():
    bpy.utils.unregister_module(__name__)

if __name__ == "__main__":
    register()

# all panels, except render panel
# Example of wrapping every class 'as is'
from bl_ui import properties_scene
for member in dir(properties_scene):
    subclass = getattr(properties_scene, member)
    try:        subclass.COMPAT_ENGINES.add('RENDERFARMFI_RENDER')
    except:    pass
del properties_scene

from bl_ui import properties_world
for member in dir(properties_world):
    subclass = getattr(properties_world, member)
    try:        subclass.COMPAT_ENGINES.add('RENDERFARMFI_RENDER')
    except:    pass
del properties_world

from bl_ui import properties_material
for member in dir(properties_material):
    subclass = getattr(properties_material, member)
    try:        subclass.COMPAT_ENGINES.add('RENDERFARMFI_RENDER')
    except:    pass
del properties_material

from bl_ui import properties_object
for member in dir(properties_object):
    subclass = getattr(properties_object, member)
    try:        subclass.COMPAT_ENGINES.add('RENDERFARMFI_RENDER')
    except:    pass
del properties_object
