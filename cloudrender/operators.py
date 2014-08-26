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

