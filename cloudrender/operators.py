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

import hashlib

import bpy

from .utils import _write_credentials, _read_credentials
from .prepare import _prepare_scene
from .upload import _ore_upload
from .rpc import rffi, _do_refresh
from .exceptions import LoginFailedException, SessionCancelFailedException
from .xml_exporter.io_scene_cycles.export_cycles import export_cycles

def render(scene, crowdprocess):
    from io import StringIO
    fp = StringIO()
    export_cycles(fp=fp, scene=scene)

class ORE_LoginOp(bpy.types.Operator):
    bl_idname = 'ore.login'
    bl_label = 'Login'

    def execute(self, context):
        sce = context.scene
        ore = sce.ore_render

        ore.password = ore.password.strip()
        ore.username = ore.username.strip()

        print("writing new credentials")
        _write_credentials(hashlib.md5(ore.password.encode() + ore.username.encode()).hexdigest(),ore.username)
        _read_credentials()
        ore.password = ''
        ore.username = ''
        bpy.loginInserted = False
        bpy.passwordCorrect = False

        try:
            _do_refresh(self, True)

            bpy.passwordCorrect = True
            bpy.loginInserted = True

        except LoginFailedException as v:
            bpy.ready = False
            bpy.loginInserted = False
            bpy.passwordCorrect = False
            ore.username = bpy.rffi_user
            _write_credentials('', '')
            _read_credentials()
            ore.hash = ''
            ore.password = ''
            self.report({'WARNING'}, "Incorrect login: " + str(v))
            print(v)
            return {'CANCELLED'}

        return {'FINISHED'}

class ORE_UploaderOp(bpy.types.Operator):
    bl_idname = "ore.upload"
    bl_label = "Render on Renderfarm.fi"

    def execute(self, context):
        bpy.uploadInProgress = True
        _prepare_scene()

        returnValue = _ore_upload(self, context)
        bpy.uploadInProgress = False
        return returnValue

class ORE_ChangeUser(bpy.types.Operator):
    bl_idname = "ore.change_user"
    bl_label = "Change user"

    def execute(self, context):
        ore = context.scene.ore_render
        _write_credentials('', '')
        _read_credentials()
        ore.password = ''
        bpy.ore_sessions = []
        ore.hash = ''
        bpy.rffi_user = ''
        bpy.rffi_hash = ''
        bpy.rffi_creds_found = False
        bpy.passwordCorrect = False
        bpy.loginInserted = False
        bpy.rffi_accepts = False
        bpy.rffi_motd = ''

        return {'FINISHED'}

