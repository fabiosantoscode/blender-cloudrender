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


base_64_enc = '''
// From: http://www.webtoolkit.info/
function base64(input) {
  var keyStr = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/=";
  var output = "";
  var chr1, chr2, chr3, enc1, enc2, enc3, enc4;
  var i = 0;

  while (i < input.length) {
    chr1 = input[i++];
    chr2 = input[i++];
    chr3 = input[i++];

    enc1 = chr1 >> 2;
    enc2 = ((chr1 & 3) << 4) | (chr2 >> 4);
    enc3 = ((chr2 & 15) << 2) | (chr3 >> 6);
    enc4 = chr3 & 63;

    if (isNaN(chr2)) {
      enc3 = enc4 = 64;
    } else if (isNaN(chr3)) {
      enc4 = 64;
    }

    output = output +
      keyStr.charAt(enc1) + keyStr.charAt(enc2) +
      keyStr.charAt(enc3) + keyStr.charAt(enc4);
  }

  return output;
}
'''


bpy.passwordCorrect = False

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


def renderEngine(render_engine):
    bpy.utils.register_class(render_engine)
    return render_engine

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


class CloudRender(bpy.types.RenderEngine):
    bl_idname = 'CLOUDRENDER'
    bl_label = 'CloudRender'
    bl_use_preview = False
    bl_use_shading_nodes = True

    def render(self, scene):
        import json
        import math

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

        retries = int(math.sqrt(tiles_total) + 5)

        for retry in range(retries):
            if not tiles_to_go:
                break

            if retry > 0:
                print('Retrying %d tiles... %d' % (len(tiles_to_go), retry))

            job_data = (
                { 'x': x, 'y': y, 'w': w, 'h': h }
                for x, y, w, h in tiles_to_go)

            for tile in self.job(list(job_data)).results:
                tile_data = (tile['x'], tile['y'],
                    tile['w'], tile['h'])
                if tile_data not in tiles_to_go:
                    print('???? We\'ve already rendered this tile: %r' % tile_data)
                    continue

                import base64

                self.draw_tile(*tile_data, tile=base64.b64decode(tile['tile']), hasAlpha=tile['hasAlpha'])
                tiles_to_go.remove(tile_data)
                tiles_done += 1
                self.update_progress(tiles_done / tiles_total)

        self.result.layers[0].rect = self.image
        self.end_result(self.result)
        self.job.delete()

    def draw_tile(self, x, y, w, h, tile, hasAlpha):
        assert x >= 0 and x + w <= self.width
        assert y >= 0 and y + h <= self.height

        width = self.width
        image = self.image
        img_size = len(image)

        for y_coord in range(h):
            row = y_coord * w
            rev_row = (self.height - (y + y_coord) - 1) * width
            for x_coord in range(w):
                ind = row + x_coord
                rev_ind = rev_row + x_coord + x
                if hasAlpha:
                    ind *= 4
                    image[rev_ind] = (
                        tile[ind    ] / 255,
                        tile[ind + 1] / 255,
                        tile[ind + 2] / 255,
                        tile[ind + 3] / 255,
                        )
                else:
                    ind *= 3
                    image[rev_ind] = (
                        tile[ind    ] / 255,
                        tile[ind + 1] / 255,
                        tile[ind + 2] / 255,
                        )

        self.result.layers[0].rect = image
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
                var console = {
                    log: function(){},
                    error: function(){},
                    warn: function(){},
                    assert: function(){}
                };
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

                var tile = data.tile = Module.imageData

                data.hasAlpha = false;

                for (var i = 0, len = tile.length; i < len; i += 4) {
                    if (tile[i] !== 255) {
                        data.hasAlpha = true;
                        break;
                    }
                }

                if (!data.hasAlpha) {
                    data.tile = [];

                    for (var i = 0, len = tile.length; i < len; i+=4) {
                        data.tile.push(tile[i], tile[i+1], tile[i+2]);
                    }
                }

                %s;

                data.tile = base64(data.tile)

                return data
            }
        ''' % (json.dumps(scene_xml), emcycles_core, base_64_enc)

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

from bl_ui import properties_render
for member in dir(properties_render):
    subclass = getattr(properties_render, member)
    try:        subclass.COMPAT_ENGINES.add('CLOUDRENDER')
    except:    pass
del properties_render

from bl_ui import properties_scene
for member in dir(properties_scene):
    subclass = getattr(properties_scene, member)
    try:        subclass.COMPAT_ENGINES.add('CLOUDRENDER')
    except:    pass
del properties_scene

from bl_ui import properties_world
for member in dir(properties_world):
    subclass = getattr(properties_world, member)
    try:        subclass.COMPAT_ENGINES.add('CLOUDRENDER')
    except:    pass
del properties_world

from bl_ui import properties_material
for member in dir(properties_material):
    subclass = getattr(properties_material, member)
    try:        subclass.COMPAT_ENGINES.add('CLOUDRENDER')
    except:    pass
del properties_material

from bl_ui import properties_object
for member in dir(properties_object):
    subclass = getattr(properties_object, member)
    try:        subclass.COMPAT_ENGINES.add('CLOUDRENDER')
    except:    pass
del properties_object
