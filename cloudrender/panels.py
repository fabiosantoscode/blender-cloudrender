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

class RenderButtonsPanel():
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = "render"
    # COMPAT_ENGINES must be defined in each subclass, external engines can add themselves here

class LOGIN_PT_RenderfarmFi(RenderButtonsPanel, bpy.types.Panel):
    bl_label = 'Login to CrowdProcess'
    COMPAT_ENGINES = set(['CLOUDRENDER'])

    @classmethod
    def poll(cls, context):
        rd = context.scene.render
        return (rd.use_game_engine==False) and (rd.engine in cls.COMPAT_ENGINES)

    def draw(self, context):
        # login
        layout = self.layout
        ore = context.scene.ore_render

        if bpy.passwordCorrect == False:
            row = layout.row()
            row.label(text="Email or password missing/incorrect", icon='ERROR')
            col = layout.column()
            col.prop(ore, 'username', icon=bpy.statusMessage['username'])
            col.prop(ore, 'password', icon=bpy.statusMessage['password'])
            layout.operator('ore.login')
        else:
            layout.label(text='Successfully logged in', icon='INFO')
            layout.operator('ore.change_user')

class RENDER_PT_RenderfarmFi(RenderButtonsPanel, bpy.types.Panel):
    bl_label = "Settings"
    COMPAT_ENGINES = set(['CLOUDRENDER'])

    @classmethod
    def poll(cls, context):
        rd = context.scene.render
        return (rd.use_game_engine==False) and (rd.engine in cls.COMPAT_ENGINES)

    def draw(self, context):
        layout = self.layout
        sce = context.scene
        ore = sce.ore_render
