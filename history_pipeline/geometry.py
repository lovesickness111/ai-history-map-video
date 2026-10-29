"""Small bpy data-API geometry toolkit. Imported only inside Blender."""
from dataclasses import dataclass, field
import math
import bpy
from mathutils import Vector

COLORS = {
    "stone": (.37, .38, .33), "stone_light": (.69, .66, .56),
    "brick": (.42, .29, .20), "wood": (.18, .085, .038),
    "wood_light": (.34, .20, .09), "tile": (.43, .16, .075),
    "tile_light": (.56, .25, .12), "gold": (.67, .45, .15),
    "tile_dark": (.24, .23, .20), "tile_aged": (.36, .24, .14),
    "wall0": (.82, .77, .63), "wall1": (.71, .67, .52),
    "wall2": (.87, .85, .76), "wall3": (.69, .71, .65),
    "wall4": (.77, .66, .51), "dark": (.035, .042, .035),
    "water": (.14, .25, .19), "bank": (.35, .39, .23),
    "grass": (.40, .42, .29), "base": (.19, .27, .23),
    "road": (.47, .40, .28), "leaf": (.14, .26, .10),
    "earth": (.42, .38, .25), "field": (.38, .42, .17),
    "field_dry": (.51, .44, .25), "field_green": (.24, .33, .12),
}


def linear(rgb):
    return tuple(v/12.92 if v<=.04045 else ((v+.055)/1.055)**2.4 for v in rgb)


def material(key):
    name = f"Hanoi_{key}"
    mat = bpy.data.materials.get(name)
    if mat is None:
        mat = bpy.data.materials.new(name)
        mat.use_nodes = True
        rgba = (*linear(COLORS[key]), 1)
        mat.diffuse_color = rgba
        bsdf = mat.node_tree.nodes.get("Principled BSDF")
        bsdf.inputs["Base Color"].default_value = rgba
        bsdf.inputs["Roughness"].default_value = .82
        nodes,links=mat.node_tree.nodes,mat.node_tree.links
        coords=nodes.new('ShaderNodeTexCoord')
        noise=nodes.new('ShaderNodeTexNoise')
        noise.inputs['Scale'].default_value=60 if key=='grass' else (9 if key in ('earth','field','field_dry','field_green') else 17)
        noise.inputs['Detail'].default_value=3
        links.new(coords.outputs['Generated'],noise.inputs['Vector'])
        ramp=nodes.new('ShaderNodeValToRGB')
        ramp.color_ramp.elements[0].position=.15
        ramp.color_ramp.elements[0].color=tuple(v*.58 for v in rgba[:3])+(1,)
        ramp.color_ramp.elements[1].position=.85
        ramp.color_ramp.elements[1].color=tuple(min(1,v*1.22) for v in rgba[:3])+(1,)
        links.new(noise.outputs['Fac'],ramp.inputs['Fac'])
        links.new(ramp.outputs['Color'],bsdf.inputs['Base Color'])
        bump=nodes.new('ShaderNodeBump')
        bump.inputs['Strength'].default_value=.20
        bump.inputs['Distance'].default_value=.035
        links.new(noise.outputs['Fac'],bump.inputs['Height'])
        links.new(bump.outputs['Normal'],bsdf.inputs['Normal'])
        if key in ('brick','stone','stone_light') or key.startswith('wall'):
            sep=nodes.new('ShaderNodeSeparateXYZ')
            combine=nodes.new('ShaderNodeCombineXYZ')
            position=nodes.new('ShaderNodeNewGeometry')
            links.new(position.outputs['Position'],sep.inputs[0])
            links.new(sep.outputs['X'],combine.inputs['X'])
            links.new(sep.outputs['Z'],combine.inputs['Y'])
            brick=nodes.new('ShaderNodeTexBrick')
            brick.inputs['Scale'].default_value=16 if key=='brick' else 3
            brick.inputs['Mortar Size'].default_value=.012
            brick.inputs['Mortar Smooth'].default_value=.005
            brick.inputs['Brick Width'].default_value=.47
            brick.inputs['Row Height'].default_value=.15
            brick.inputs['Color1'].default_value=tuple(v*.72 for v in rgba[:3])+(1,)
            brick.inputs['Color2'].default_value=rgba
            brick.inputs['Mortar'].default_value=tuple(v*.4 for v in rgba[:3])+(1,)
            links.new(combine.outputs[0],brick.inputs['Vector'])
            if key=='brick':
                links.new(brick.outputs['Color'],bsdf.inputs['Base Color'])
                links.new(brick.outputs['Fac'],bump.inputs['Height'])
                bump.inputs['Distance'].default_value=.012
        if key=='water':
            bsdf.inputs['Roughness'].default_value=.24
            bsdf.inputs['IOR'].default_value=1.333
            bump.inputs['Distance'].default_value=.012
            noise.inputs['Scale'].default_value=70
        if key in ('wood','wood_light'):
            stretch=nodes.new('ShaderNodeVectorMath')
            stretch.operation='MULTIPLY'
            stretch.inputs[1].default_value=(3,65,8)
            links.new(coords.outputs['Generated'],stretch.inputs[0])
            links.new(stretch.outputs[0],noise.inputs['Vector'])
            noise.inputs['Scale'].default_value=2
            bump.inputs['Distance'].default_value=.008
        if key=='leaf':
            bsdf.inputs['Roughness'].default_value=.95
    return mat


def mesh_object(name, vertices, faces, mat, parent=None):
    # Immutable mesh cache lets identical primitives share their datablock.
    key = repr((vertices, faces, mat))
    import hashlib
    mesh_name = "mesh_" + hashlib.sha1(key.encode()).hexdigest()[:18]
    mesh = bpy.data.meshes.get(mesh_name)
    if mesh is None:
        mesh = bpy.data.meshes.new(mesh_name)
        mesh.from_pydata(vertices, [], faces)
        mesh.materials.append(material(mat))
        mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.scene.collection.objects.link(obj)
    if parent is not None:
        obj.parent = parent
    return obj


CUBE_VERTS = [(-.5,-.5,-.5),(-.5,-.5,.5),(-.5,.5,-.5),(-.5,.5,.5),
              (.5,-.5,-.5),(.5,-.5,.5),(.5,.5,-.5),(.5,.5,.5)]
CUBE_FACES = [(2,6,4,0),(5,7,3,1),(4,5,1,0),(3,7,6,2),(1,3,2,0),(6,7,5,4)]


def box(name, size, location, mat, parent=None):
    obj = mesh_object(name, CUBE_VERTS, CUBE_FACES, mat, parent)
    obj.location = location
    obj.scale = size
    return obj


def cylinder(name, radius, depth, location, mat, parent=None, sides=12, top_radius=None):
    top_radius = radius if top_radius is None else top_radius
    vertices = [(r*math.cos(2*math.pi*i/sides), r*math.sin(2*math.pi*i/sides), z)
                for r, z in ((radius,-depth/2),(top_radius,depth/2)) for i in range(sides)]
    faces = [tuple(reversed(range(sides))), tuple(range(sides,2*sides))]
    faces += [(i,(i+1)%sides,(i+1)%sides+sides,i+sides) for i in range(sides)]
    obj = mesh_object(name, vertices, faces, mat, parent)
    obj.location = location
    return obj


def beam(name, start, end, width, mat, parent=None):
    a, b = Vector(start), Vector(end)
    obj = box(name, (width,width,(b-a).length), (a+b)/2, mat, parent)
    obj.rotation_euler = (b-a).to_track_quat('Z','Y').to_euler()
    return obj


@dataclass
class ModelAssembly:
    root: object
    stages: list = field(default_factory=list)
    bounds: tuple = ((0,0,0),(0,0,0))

    @classmethod
    def create(cls, name):
        root = bpy.data.objects.new(name, None)
        bpy.context.scene.collection.objects.link(root)
        root["assembly"] = True
        return cls(root)

    def stage(self, name, base):
        group = bpy.data.objects.new(f"{self.root.name}/{name}", None)
        bpy.context.scene.collection.objects.link(group)
        group.parent = self.root
        group.location.z = base
        group["stage_index"] = len(self.stages)
        self.stages.append(group)
        return group

    def place(self, obj, stage):
        obj.parent = stage
        obj.location.z -= stage.location.z
        return obj

    def cube(self, stage, name, size, loc, mat):
        return self.place(box(f"{self.root.name}/{name}", size, loc, mat), stage)

    def cyl(self, stage, name, r, depth, loc, mat, sides=12, top_radius=None):
        return self.place(cylinder(f"{self.root.name}/{name}", r, depth, loc, mat,
                                   sides=sides, top_radius=top_radius), stage)

    def bar(self, stage, name, a, b, width, mat):
        return self.place(beam(f"{self.root.name}/{name}", a,b,width,mat), stage)

    def mesh(self, stage, name, vertices, faces, mat):
        return self.place(mesh_object(f"{self.root.name}/{name}", vertices,faces,mat), stage)

    def finish(self):
        points = [stage.matrix_basis @ obj.matrix_basis @ vertex.co
                  for stage in self.stages for obj in stage.children if obj.type == 'MESH'
                  for vertex in obj.data.vertices]
        self.bounds = (tuple(min(p[i] for p in points) for i in range(3)),
                       tuple(max(p[i] for p in points) for i in range(3)))
        self.root["bounds_min"], self.root["bounds_max"] = self.bounds
        return self

    def consolidate(self):
        """One mesh per construction stage, with shared material slots."""
        import hashlib
        for stage in self.stages:
            children=list(stage.children)
            verts,faces,indices,mats=[],[],[],[]
            for obj in children:
                if obj.type!='MESH':
                    continue
                mapping=[]
                for mat in obj.data.materials:
                    if mat not in mats:
                        mats.append(mat)
                    mapping.append(mats.index(mat))
                offset=len(verts)
                verts.extend(tuple(obj.matrix_basis @ v.co) for v in obj.data.vertices)
                for poly in obj.data.polygons:
                    faces.append(tuple(offset+i for i in poly.vertices))
                    indices.append(mapping[poly.material_index])
            key=hashlib.sha256(repr((verts,faces,indices,[m.name for m in mats])).encode()).hexdigest()[:20]
            mesh=bpy.data.meshes.get('joined_'+key)
            if mesh is None:
                mesh=bpy.data.meshes.new('joined_'+key)
                mesh.from_pydata(verts,[],faces)
                for mat in mats:
                    mesh.materials.append(mat)
                for poly,index in zip(mesh.polygons,indices):
                    poly.material_index=index
                mesh.update()
            obj=bpy.data.objects.new(stage.name+'/geometry',mesh)
            bpy.context.scene.collection.objects.link(obj)
            obj.parent=stage
            for old in children:
                bpy.data.objects.remove(old,do_unlink=True)
        return self
