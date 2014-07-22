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
    for i in range(0, width, size):
        if i + size > width:
            yield i, width - i
        else:
            yield i, size

def viewport_divisions(height, width, bucket_size=10):
    assert height > 0 and width > 0 and bucket_size > 0

    for y in range(0, height, bucket_size):
        for x, col_width in viewport_columns(width, bucket_size):
            last = y + bucket_size
            if y + bucket_size > height:
                yield (x, y, col_width, height - y)
            else:
                yield (x, y, col_width, bucket_size)



class ORE_LoginOp(bpy.types.Operator):
    bl_idname = 'ore.login'
    bl_label = 'Login'

    def execute(self, context):
        sce = context.scene
        ore = sce.ore_render

        ore.password = ore.password.strip()
        ore.username = ore.username.strip()

        from .crowdprocess import CrowdProcess
        crowdprocess = CrowdProcess(ore.username, ore.password)

        try:
            crowdprocess.list_jobs()
            bpy.loginInserted = True
            bpy.passwordCorrect = True
        except:
            bpy.loginInserted = False
            bpy.passwordCorrect = False
            self.report({'WARNING'}, "Incorrect login for crowdprocess. Wrong password?")
            return {'CANCELLED'}

        return {'FINISHED'}

