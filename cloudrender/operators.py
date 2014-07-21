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

import bpy


def viewport_columns(width, size=10):
    last = 0

    for i in range(width // size):
        last = (i * size) + size
        yield (i * size, size)

    if last < width:  # uneven row div
        yield (last, width - last)


def viewport_divisions(height, width, bucket_size=10):
    assert height > 0 and width > 0 and bucket_size > 0

    last = 0
    for row in range(height // bucket_size):
        y = row * bucket_size
        for x, col_width in viewport_columns(width, bucket_size):
            last = y + bucket_size
            yield (x, y, col_width, bucket_size)

    if last < height:
        for x, col_width in viewport_columns(width, bucket_size):
            yield (x, last, col_width, height - last)



def render(scene, crowdprocess):
    from io import StringIO
    import json
    fp = StringIO()

    #resolution_fraction = (100 / scene.render.resolution_percentage)
    resolution_fraction = 0.025

    height, width = (
        int(scene.render.resolution_x * resolution_fraction),
        int(scene.render.resolution_y * resolution_fraction),
    )
        
    # export_cycles(fp=fp, scene=scene)
    # scene_xml = fp.getvalue()
    scene_xml = open('example_scene.xml').read()#
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

    job = crowdprocess.job(crowdprocess_func)

    job_data = ({ 'x': x, 'y': y, 'w': w, 'h': h } for x, y, w, h in viewport_divisions(height, width))

    responses = job(job_data)
    tiles, errors = list(responses.results), list(responses.errors)

    print('%d tiles:' % len(tiles), list(tiles))
    print('%d errors:' % len(errors), list(errors))

    open('/tmp/tiles.json', 'w').write(json.dumps(tiles))


class ORE_LoginOp(bpy.types.Operator):
    bl_idname = 'ore.login'
    bl_label = 'Login'

    def execute(self, context):
        sce = context.scene
        ore = sce.ore_render

        ore.password = ore.password.strip()
        ore.username = ore.username.strip()

        crowdprocess = CrowdProcess(ore.username, ore.password)

        try:
            crowdprocess.list_jobs()
            bpy.loginInserted = True
            bpy.passwordCorrect = True
        except:
            bpy.loginInserted = False
            bpy.passwordCorrect = False
            self.report({'WARNING'}, "Incorrect login for crowdprocess. Wrong password? Lel")
            return {'CANCELLED'}

        return {'FINISHED'}

