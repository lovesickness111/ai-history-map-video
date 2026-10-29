"""Stylized diorama, camera, light and render configuration."""
import math
import bpy
from mathutils import Vector
from bpy_extras.object_utils import world_to_camera_view
from .geometry import box,cylinder,mesh_object,beam
from .models import build,clear_templates
from .animation import animate


def camera_at(location,target,scale=24.7,perspective=False):
    scene=bpy.context.scene
    cam=scene.camera
    if cam is None:
        data=bpy.data.cameras.new("Isometric")
        cam=bpy.data.objects.new("Isometric",data)
        scene.collection.objects.link(cam)
        scene.camera=cam
    cam.data.type='PERSP' if perspective else 'ORTHO'
    cam.data.ortho_scale=scale
    cam.location=location
    cam.rotation_euler=(Vector(target)-cam.location).to_track_quat('-Z','Y').to_euler()
    cam.data.lens=50
    cam.data.clip_end=500
    return cam


def terrain():
    box("Diorama_base",(20,14,.70),(0,0,-.40),"base")
    box("Earth_surface",(20,14,.10),(0,0,-.05),"grass")
    # Smooth polyline ribbon, a horizontal river surface rather than a cylinder.
    rows=[(-7+i*.5,7.35+.5*math.sin((-7+i*.5)*.55)) for i in range(29)]
    verts=[(x+side*.83,y,.018) for y,x in rows for side in (-1,1)]
    faces=[(2*i,2*i+1,2*i+3,2*i+2) for i in range(len(rows)-1)]
    mesh_object("Red_River",verts,faces,"water")
    for side in (-1,1):
        v=[(x+side*offset,y,.023) for y,x in rows for offset in (.83,.98)]
        mesh_object("River_bank",v,faces,"bank")
    box("Pagoda_pond_rim",(4.6,4.6,.07),(-4.7,1.5,.015),"stone")
    box("Pagoda_pond",(4.35,4.35,.025),(-4.7,1.5,.057),"water")
    for x in (-1.4,5.6):
        box("Street",(.4,12.6,.025),(x,0,.018),"road")
    for y in (-6,-3,0,3,6):
        box("Lane",(7.4,.20,.025),(2.1,y,.018),"road")
    box("Landmark_walk",(3.2,.38,.025),(-3.4,-.95,.018),"road")
    # A few emblematic trees outside reserved building lots.
    for i,(x,y) in enumerate(((-8,-5),(-8,-2),(-8,1),(-8,4),(-7,5.5),(-4.8,5.5),(-2.8,5.5),(6.0,-5),(6,2),(6,5))):
        cylinder(f"Tree_{i}_trunk",.055,.42,(x,y,.21),"wood",sides=6)
        cylinder(f"Tree_{i}_crown",.36,.80,(x,y,.81),"leaf",sides=7,top_radius=.03)
    # Discrete stylized ripples, staying within the river footprint.
    for i in range(11):
        y=-6+i*1.15
        x=7.35+.5*math.sin(y*.55)
        box("River_glint",(.38,.025,.007),(x,y,.025),"stone_light")


def lighting(landscape=False):
    world=bpy.data.worlds.new("Cinematic_sky")
    bpy.context.scene.world=world
    world.use_nodes=True
    nodes,links=world.node_tree.nodes,world.node_tree.links
    nodes.clear()
    out=nodes.new('ShaderNodeOutputWorld')
    bg=nodes.new('ShaderNodeBackground')
    sky=nodes.new('ShaderNodeTexSky')
    sky.sky_type='NISHITA'
    sky.sun_elevation=math.radians(26)
    sky.sun_rotation=math.radians(135)
    sky.altitude=15
    sky.air_density=1.1
    sky.dust_density=1.5
    sky.ozone_density=1.2
    sky.sun_intensity=1.2
    bg.inputs['Strength'].default_value=.65
    links.new(sky.outputs['Color'],bg.inputs['Color'])
    links.new(bg.outputs['Background'],out.inputs['Surface'])

    # Warm directional sunlight for dramatic long cast shadows
    sun_data=bpy.data.lights.new('Sun_Key','SUN')
    sun_data.energy=4.8 if landscape else 3.2
    sun_data.color=(1.0,.92,.78)
    sun_data.angle=math.radians(1.5)
    sun_obj=bpy.data.objects.new('Sun_Key',sun_data)
    bpy.context.scene.collection.objects.link(sun_obj)
    sun_obj.location=(-80,-120,90)
    sun_obj.rotation_euler=(Vector((15,10,0))-sun_obj.location).to_track_quat('-Z','Y').to_euler()

    if landscape:
        fill_data=bpy.data.lights.new('Sky_fill','AREA')
        fill_data.energy=65000
        fill_data.size=350
        fill_data.color=(.68,.82,1.0)
        fill_obj=bpy.data.objects.new('Sky_fill',fill_data)
        bpy.context.scene.collection.objects.link(fill_obj)
        fill_obj.location=(0,0,450)
        fill_obj.rotation_euler=(0,0,0)


def fit_camera(assemblies):
    """Fit once at completion; keep camera fixed throughout the animation."""
    scene=bpy.context.scene
    cam=scene.camera
    corners=[obj.matrix_world @ Vector(corner) for a in assemblies for stage in a.stages
             for obj in stage.children for corner in obj.bound_box]
    def bounds():
        uv=[world_to_camera_view(scene,cam,p) for p in corners]
        return min(p.x for p in uv),max(p.x for p in uv),min(p.y for p in uv),max(p.y for p in uv)
    if cam.data.type=='PERSP':
        center=Vector((3,0,1))
        direction=cam.location-center
        for _ in range(12):
            bpy.context.view_layer.update()
            left,right,bottom,top=bounds()
            if left>.04 and right<.96 and bottom>.13 and top<.80:
                break
            direction*=1.06
            cam.location=center+direction
        return
    left,right,bottom,top=bounds()
    cam.data.ortho_scale*=max(1.,(right-left)/.84,(top-bottom)/.64)
    left,right,bottom,top=bounds()
    rotation=cam.matrix_world.to_quaternion()
    aspect=scene.render.resolution_x/scene.render.resolution_y
    cam.location+=(rotation @ Vector((1,0,0)))*(((left+right)/2-.5)*cam.data.ortho_scale)
    cam.location+=(rotation @ Vector((0,1,0)))*(((bottom+top)/2-.46)*cam.data.ortho_scale/aspect)
    bpy.context.view_layer.update()


def configure(config):
    scene=bpy.context.scene
    scene.render.engine='BLENDER_EEVEE_NEXT' if config['engine']=='eevee' else 'CYCLES'
    scene.render.resolution_x=config['width']
    scene.render.resolution_y=config['height']
    scene.render.resolution_percentage=100
    scene.render.fps=config['timeline']['fps']
    scene.frame_start=1
    scene.frame_end=config['timeline']['frame_end']
    scene.render.image_settings.file_format='PNG'
    scene.render.image_settings.color_mode='RGB'
    scene.render.image_settings.color_depth='8'
    scene.render.image_settings.compression=15
    scene.render.film_transparent=False
    scene.render.threads_mode='FIXED'
    scene.render.threads=4
    scene.view_settings.view_transform='AgX'
    if scene.render.engine=='CYCLES':
        scene.cycles.device='CPU'
        scene.cycles.samples=16 if config.get('preset')=='final' else 8
        scene.cycles.use_denoising=True
        scene.cycles.max_bounces=4
    else:
        scene.eevee.taa_render_samples=8
        scene.eevee.use_raytracing=False


def make_scene(config):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    clear_templates()
    configure(config)
    geographic=config['timeline'].get('scene_profile')=='geographic'
    landscape=config['timeline'].get('scene_profile')=='landscape'
    if geographic:
        from .geoscene import create,animate_camera
        assemblies,animation_instances=create(config)
        lighting(landscape=True)
        # Scene distances are geographic; the broad fill light tracks the city.
        fill=bpy.data.objects.get('Sky_fill')
        fill.location=(0,0,800)
        fill.data.energy=8_000_000
        fill.data.size=900
        animate_camera(config,assemblies)
        records=[{'id':a.root.name,'bounds':a.bounds} for a in assemblies]
        bpy.context.scene.frame_set(config['timeline']['frame_end'])
        bpy.context.view_layer.update()
        meshes=[o for o in bpy.context.scene.objects if o.type=='MESH']
        triangles=sum(sum(len(p.vertices)-2 for p in o.data.polygons) for o in meshes)
        if triangles>=1_500_000:
            raise ValueError(f'GIS triangle budget exceeded: {triangles}')
        return assemblies,{'mesh_objects':len(meshes),'triangles':triangles,'assemblies':records,
                           'animation_instances':animation_instances,'geographic':config['timeline']['gis']['metadata']}
    if landscape:
        from .landscape import create
        create()
        lighting(landscape=True)
        camera_at((49,-66,58),(3,0,1),perspective=True)
    else:
        terrain()
        lighting()
        camera_at((19,-26,25),(0,0,1.5),27.7)
    assemblies=[]
    records=[]
    for instance in config['timeline']['instances']:
        assembly=build(instance)
        windows=animate(assembly,instance)
        assemblies.append(assembly)
        records.append({"id":instance['id'],"bounds":assembly.bounds,"stages":windows})
    bpy.context.scene.frame_set(config['timeline']['frame_end'])
    bpy.context.view_layer.update()
    fit_camera(assemblies)
    meshes=[obj for obj in bpy.context.scene.objects if obj.type=='MESH']
    triangles=sum(sum(len(p.vertices)-2 for p in obj.data.polygons) for obj in meshes)
    budget=750_000 if landscape else 100_000
    if triangles>=budget:
        raise ValueError(f"Triangle budget exceeded: {triangles}")
    return assemblies,{"mesh_objects":len(meshes),"triangles":triangles,"assemblies":records}
