"""Recognizable low-poly landmarks, with independent construction groups."""
import math
import bpy
from .geometry import ModelAssembly


def pagoda(name, params, seed):
    a = ModelAssembly.create(name)
    p = a.stage("01_stone_pillar", 0)
    a.cyl(p,"pillar_foot", .39,.16,(0,0,.08),"stone_light")
    a.cyl(p,"single_pillar", .22,1.20,(0,0,.69),"stone",sides=12)
    for z in (.22,.82,1.19):
        a.cyl(p,"stone_collar",.232,.035,(0,0,z),"stone_light",sides=16)
    s = a.stage("02_floor_and_braces", .20)
    for x,y in ((-.65,-.65),(-.65,.65),(.65,-.65),(.65,.65)):
        a.bar(s,"diagonal_brace",(0,0,.8),(x,y,1.35),.105,"wood")
    a.cube(s,"floor",(1.9,1.9,.16),(0,0,1.40),"wood_light")
    for i in range(9):
        a.cube(s,"floor_board",(.19,1.88,.018),(-.8+i*.20,0,1.49),"wood_light")
    for i in range(9):
        a.cube(s,"access_step",(.65,.22,.075),(0,-1.03-i*.19,1.37-i*.155),"stone_light")
    for x in (-.27,.27):
        a.bar(s,"stair_stringer",(x,-.96,1.31),(x,-2.68,.055),.105,"stone")
    a.cube(s,"stair_landing",(.75,.32,.07),(0,-2.7,.035),"stone")
    t = a.stage("03_timber_pavilion",1.48)
    for x in (-.73,.73):
        for y in (-.73,.73):
            a.cube(t,"timber_post",(.105,.105,.86),(x,y,1.91),"wood")
    a.cube(t,"back_wall",(1.5,.09,.75),(0,.72,1.86),"wood_light")
    for x in (-.73,.73):
        a.cube(t,"side_wall",(.09,1.5,.55),(x,0,1.76),"wood_light")
        a.cube(t,"rail",(.07,1.8,.07),(x,0,1.75),"gold")
    a.cube(t,"lintel",(1.6,.12,.17),(0,-.72,2.22),"wood")
    a.cube(t,"door_shadow",(.65,.02,.61),(0,.66,1.82),"dark")
    for side in (-1,1):
        for i in range(9):
            a.cube(t,"balustrade_spindle",(.035,.035,.29),(side*.88,-.8+i*.20,1.68),"wood")
        a.cube(t,"balustrade_top",(.055,1.80,.055),(side*.88,0,1.84),"wood_light")
    for i in range(9):
        a.cube(t,"front_lattice",(.024,.035,.28),(-.64+i*.16,-.735,2.0),"wood_light")
    for x in (-.73,0,.73):
        a.bar(t,"eave_bracket",(x,-.70,2.10),(x,-1.07,2.35),.045,"wood")
    r = a.stage("04_curved_hip_roof",2.23)
    # Eight points per square ring: corners and midpoints. Eaves lift at corners.
    directions = [(-1,-1),(0,-1),(1,-1),(1,0),(1,1),(0,1),(-1,1),(-1,0)]
    rings = [(.055,3.05),(.3,2.98),(.60,2.80),(.91,2.57),(1.12,2.43),(1.28,2.40),(1.41,2.44),(1.48,2.55)]
    vertices = [(x*rad,y*rad,z+(.11*(rad/1.48)**3 if x and y else 0))
                for rad,z in rings for x,y in directions]
    faces = [(i*8+j,i*8+(j+1)%8,(i+1)*8+(j+1)%8,(i+1)*8+j)
             for i in range(len(rings)-1) for j in range(8)]
    faces += [tuple(reversed(range(8))),tuple(range((len(rings)-1)*8,len(rings)*8))]
    faces=[tuple(reversed(face)) for face in faces]
    a.mesh(r,"curved_roof",vertices,faces,"tile")
    # Tile courses use a single joined mesh, not one object per tile.
    vv, ff = [], []
    for i in range(1,len(rings)-1):
        rad,z = rings[i]
        for j,(x,y) in enumerate(directions):
            nx,ny = directions[(j+1)%8]
            k=len(vv)
            vv += [(x*rad,y*rad,z+.018+(.11*(rad/1.48)**3 if x and y else 0)),
                   (nx*rad,ny*rad,z+.018+(.11*(rad/1.48)**3 if nx and ny else 0)),
                   (nx*(rad+.025),ny*(rad+.025),z+.006+(.11*(rad/1.48)**3 if nx and ny else 0)),
                   (x*(rad+.025),y*(rad+.025),z+.006+(.11*(rad/1.48)**3 if x and y else 0))]
            ff.append((k,k+1,k+2,k+3))
    a.mesh(r,"tile_courses",vv,ff,"tile_light")
    for x,y in ((-1,-1),(-1,1),(1,-1),(1,1)):
        for (rad,z),(next_rad,next_z) in zip(rings,rings[1:]):
            a.bar(r,"hip_ridge",(x*rad,y*rad,z+.11*(rad/1.48)**3+.03),
                  (x*next_rad,y*next_rad,next_z+.11*(next_rad/1.48)**3+.03),.04,"tile_light")
        a.bar(r,"raised_roof_corner",(x*1.43,y*1.43,2.65),(x*1.56,y*1.56,2.85),.055,"tile_light")
    a.cyl(r,"roof_finial",.065,.21,(0,0,3.14),"gold",sides=8,top_radius=.015)
    size=params.get("size",1.)
    a.root.scale=(size,)*3
    return a.finish().consolidate()


def flag_tower(name, params, seed):
    a = ModelAssembly.create(name)
    z=0
    for i,(width,top,height) in enumerate(((3.25,3.04,.36),(2.45,2.27,.38),(1.72,1.55,.42))):
        s=a.stage(f"0{i+1}_terrace",z)
        verts=[(x*w/2,y*w/2,zz) for w,zz in ((width,z),(top,z+height))
               for x,y in ((-1,-1),(1,-1),(1,1),(-1,1))]
        faces=[(3,2,1,0),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)]
        a.mesh(s,"tapered_base",verts,faces,"brick")
        a.cube(s,"terrace_cap",(top+.08,top+.08,.07),(0,0,z+height+.015),"stone_light")
        for side in (-1,1):
            a.cube(s,"parapet",(.075,top,.12),(side*(top/2-.055),0,z+height+.09),"brick")
            a.cube(s,"parapet_coping",(.10,top,.045),(side*(top/2-.055),0,z+height+.16),"stone_light")
        a.cube(s,"rear_parapet",(top,.075,.13),(0,top/2-.05,z+height+.10),"brick")
        for j in range(9):
            a.cube(s,"stairs",(.42,.095,(j+1)*height/9),(0,-width/2-.33+j*.065,z+(j+1)*height/18),"stone")
        if i>0:
            a.cube(s,"entry",(.21,.025,.22),(0,-width/2-.01,z+.15),"dark")
        z+=height+.06
    s=a.stage("04_octagonal_shaft",z)
    a.cyl(s,"shaft",.47,1.87,(0,0,z+.935),"brick",sides=8,top_radius=.36)
    for level in (.43,.94,1.42):
        for side in range(8):
            angle=(side+.5)*math.pi/4
            rad=.45-(level/1.87)*.1
            obj=a.cube(s,"shaft_window",(.12,.018,.17),(math.sin(angle)*rad,-math.cos(angle)*rad,z+level),"dark")
            obj.rotation_euler.z=angle
    z+=1.87
    s=a.stage("05_watchtower_and_pole",z)
    a.cyl(s,"viewing_ledge",.57,.14,(0,0,z+.04),"stone_light",sides=8)
    a.cyl(s,"watch_chamber",.43,.40,(0,0,z+.29),"brick",sides=8)
    for side in range(8):
        angle=(side+.5)*math.pi/4
        obj=a.cube(s,"watch_window",(.18,.018,.22),(math.sin(angle)*.405,-math.cos(angle)*.405,z+.30),"dark")
        obj.rotation_euler.z=angle
    a.cyl(s,"watch_roof",.57,.22,(0,0,z+.60),"stone_light",sides=8,top_radius=.19)
    a.cyl(s,"flagpole",.024,.91,(0,0,z+1.12),"wood",sides=8)
    a.root.scale=(params.get("size",1.),)*3
    return a.finish().consolidate()


def old_house(name, params, seed):
    a=ModelAssembly.create(name)
    w,d,h=params.get("width",.76),params.get("depth",1.),params.get("height",.8)
    variant=params.get("variant",seed%5)%5
    roof_material=('tile','tile_aged','tile_dark','tile','tile_light')[variant]
    s=a.stage("01_walls",0)
    a.cube(s,"plinth",(w+.035,d+.035,.08),(0,0,.04),"stone")
    a.cube(s,"walls",(w,d,h),(0,0,h/2+.08),f"wall{variant}")
    s=a.stage("02_tiled_roof",h+.08)
    eave=h+.10
    ridge=eave+.30
    verts=[(-w/2-.06,-d/2-.06,eave),(w/2+.06,-d/2-.06,eave),(0,-d/2-.06,ridge),
           (-w/2-.06,d/2+.06,eave),(w/2+.06,d/2+.06,eave),(0,d/2+.06,ridge)]
    a.mesh(s,"gable_roof",verts,[(2,5,3,0),(1,4,5,2),(1,2,0),(5,4,3),(3,4,1,0)],roof_material)
    a.cube(s,"ridge",(.045,d+.16,.045),(0,0,ridge+.01),roof_material)
    # Joined rows follow each slope, with no duplicated coplanar surfaces.
    vv,ff=[],[]
    for side in (-1,1):
        for j in range(1,5):
            fraction=j/5
            x=side*(w/2+.06)*fraction
            z=ridge-.30*fraction+.008
            k=len(vv)
            vv += [(x,-d/2-.065,z),(x,d/2+.065,z),
                   (x+side*.014,d/2+.065,z-.007),(x+side*.014,-d/2-.065,z-.007)]
            ff.append((k,k+1,k+2,k+3))
    a.mesh(s,"tile_rows",vv,ff,roof_material)
    s=a.stage("03_joinery",.08)
    a.cube(s,"door",(.22,.025,h*.65),(-w*.15,-d/2-.015,.08+h*.325),"wood")
    a.cube(s,"window",(.18,.028,.20),(w*.27,-d/2-.018,.08+h*.63),"dark")
    for dx in (-.05,0,.05):
        a.cube(s,"window_bar",(.012,.035,.20),(w*.27+dx,-d/2-.025,.08+h*.63),"wood_light")
    a.cube(s,"awning",(w*.85,.13,.045),(0,-d/2-.045,.08+h*.80),"wood_light")
    for side in (-1,1):
        a.cube(s,"door_frame",(.025,.04,h*.67),(-w*.15+side*.12,-d/2-.035,.08+h*.335),"wood_light")
        a.cube(s,"roof_fascia",(.035,d+.13,.045),(side*(w/2+.055),0,eave),"wood")
    if h>.9:
        for x in (-w*.22,w*.22):
            a.cube(s,"upper_window",(.16,.035,.19),(x,-d/2-.02,h-.09),"dark")
            for side in (-1,1):
                a.cube(s,"timber_shutter",(.045,.045,.20),(x+side*.10,-d/2-.025,h-.09),"wood_light")
        a.cube(s,"floor_band",(w+.02,.035,.035),(0,-d/2-.01,h*.58),"stone_light")
    return a.finish().consolidate()


BUILDERS={"chua_mot_cot":pagoda,"cot_co":flag_tower,"nha_co":old_house}
_TEMPLATES={}


def clear_templates():
    _TEMPLATES.clear()


def build(instance):
    kind=instance['model_id']
    params=dict(instance.get('params',{}))
    if kind=='nha_co':
        params.setdefault('variant',instance['seed']%5)
    key=(kind,repr(sorted(params.items())))
    template=_TEMPLATES.get(key)
    if template is None:
        assembly=BUILDERS[kind](instance["id"],params,instance["seed"])
        _TEMPLATES[key]=assembly
    else:
        assembly=ModelAssembly.create(instance['id'])
        assembly.bounds=template.bounds
        assembly.root['bounds_min'],assembly.root['bounds_max']=assembly.bounds
        assembly.root.scale=(params.get('size',1.),)*3
        for original in template.stages:
            stage=assembly.stage(original.name.split('/')[-1],original.location.z)
            for child in original.children:
                obj=child.copy()
                obj.name=stage.name+'/geometry'
                obj.animation_data_clear()
                obj.hide_render=False
                bpy.context.scene.collection.objects.link(obj)
                obj.parent=stage
    assembly.root.location=instance["position"]
    assembly.root.rotation_euler=[math.radians(v) for v in instance["rotation"]]
    assembly.root.scale=tuple(x*y for x,y in zip(assembly.root.scale,instance["scale"]))
    if instance.get('dimensions_m'):
        dimensions=instance['dimensions_m']
        units=dimensions['meters_per_unit']
        xy=(dimensions['floor_width_m']/1.9 if 'floor_width_m' in dimensions else dimensions['base_width_m']/3.25)/units
        assembly.root.scale=(xy,xy,dimensions['height_m']/(assembly.bounds[1][2]*units))
    assembly.root["model_id"]=instance["model_id"]
    return assembly
