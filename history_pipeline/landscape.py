"""Continuous historical landscape, district streets and broadleaf vegetation.

The layout is illustrative, not a GIS reconstruction of historical Hanoi.
"""
import math
import random
import bpy
from .geometry import box,cylinder,mesh_object,material


def elevation(x,y):
    distance=max(abs(x)/1.1,abs(y))
    blend=max(0,min(1,(distance-33)/25))
    blend*=max(0,min(1,(abs(x-river_x(y))-2.5)/5))
    lake_distance=math.sqrt(((x-39)/7)**2+((y-8)/10)**2)
    blend*=max(0,min(1,(lake_distance-1.05)/.3))
    return blend*(.20*math.sin(x*.21)*math.cos(y*.17)
                  + max(0,math.sin(x*.065+y*.025))**2*6.0)


def river_x(y):
    return 27.6+1.3*math.sin(y*.085)+.65*math.sin(y*.17)


def surface():
    count=161
    verts=[(-80+i,-65+j,elevation(-80+i,-65+j)) for j in range(count) for i in range(count)]
    faces=[(j*count+i,j*count+i+1,(j+1)*count+i+1,(j+1)*count+i)
           for j in range(count-1) for i in range(count-1)]
    land=mesh_object('Continuous_alluvial_landscape',verts,faces,'grass')
    for p in land.data.polygons:
        p.use_smooth=True
    # Water follows terrain outside the flat urban plain.
    rows=[-65+i for i in range(161)]
    verts=[(river_x(y)+side*2.0,y,elevation(river_x(y)+side*2.,y)+.025)
           for y in rows for side in (-1,1)]
    faces=[(2*i,2*i+1,2*i+3,2*i+2) for i in range(len(rows)-1)]
    mesh_object('Red_River_surface',verts,faces,'water')
    for side in (-1,1):
        verts=[(river_x(y)+side*width,y,elevation(river_x(y)+side*width,y)+.03)
               for y in rows for width in (2.,2.35)]
        mesh_object('Alluvial_river_bank',verts,faces,'bank')
    # Organic lake in open countryside, distinct from the pagoda's square pond.
    rng=random.Random(91)
    ring=[(39+math.cos(i*math.tau/56)*5.8*(1+rng.uniform(-.08,.08)),
           8+math.sin(i*math.tau/56)*8.2*(1+rng.uniform(-.08,.08)),.04) for i in range(56)]
    mesh_object('Floodplain_lake',[(39,8,.04)]+ring,[(0,i+1,(i+1)%56+1) for i in range(56)],'water')
    fields()


def fields():
    rng=random.Random(824)
    buckets={name:([],[]) for name in ('earth','field','field_dry','field_green')}
    for row in range(48):
        for col in range(50):
            x,y=-70+col*2.9,-56+row*2.9
            if -23<x<24 and -18<y<18:
                continue
            if abs(x-river_x(y))<4 or ((x-39)/7)**2+((y-8)/10)**2<1:
                continue
            if rng.random()<.46:
                continue
            w,d=rng.uniform(1.0,2.45),rng.uniform(1.3,2.6)
            angle=.06*math.sin(y*.1)+rng.uniform(-.07,.07)
            vertices,faces=buckets[rng.choice(tuple(buckets))]
            offset=len(vertices)
            for dx,dy in ((-w/2,-d/2),(w/2,-d/2),(w/2,d/2),(-w/2,d/2)):
                xx=x+dx*math.cos(angle)-dy*math.sin(angle)
                yy=y+dx*math.sin(angle)+dy*math.cos(angle)
                vertices.append((xx,yy,elevation(xx,yy)+.018))
            faces.append(tuple(range(offset,offset+4)))
    for name,(vertices,faces) in buckets.items():
        mesh_object('Cultivated_plots_'+name,vertices,faces,name)


def streets_and_precinct():
    for x in (-5.7,-1.05,3.6,8.25,12.9,17.55,22.2):
        box('District_street',(.40,29.0,.028),(x,-.75,.014),'road')
    for y in (-15.05,-7.95,-.85,6.25,13.35):
        box('District_cross_street',(28.15,.40,.028),(8.15,y,.014),'road')
    box('Ceremonial_axis',(.7,27,.035),(-12.4,0,.018),'road')
    box('Gate_approach',(13,.65,.03),(-11,-12.2,.017),'road')
    box('Pagoda_pond_rim',(4.6,4.6,.08),(-12,7,.04),'stone')
    box('Pagoda_pond',(4.35,4.35,.022),(-12,7,.09),'water')
    # Modest enclosure, built from brick walls with stone coping.
    for x in (-19.0,-6.5):
        box('Precinct_wall',(.26,22,.56),(x,0,.28),'brick')
        box('Wall_coping',(.34,22,.075),(x,0,.59),'stone_light')
    for y in (-11,11):
        for x,width in ((-16,6),(-9.7,4.1)):
            box('Enclosure_wall',(width,.26,.56),(x,y,.28),'brick')
            box('Wall_coping',(width,.34,.075),(x,y,.59),'stone_light')
    for x in (-19,-6.5):
        for y in (-11,11):
            box('Corner_guard_base',(.8,.8,.70),(x,y,.35),'brick')
            cylinder('Corner_guard_roof',.69,.30,(x,y,.86),'tile',sides=4,top_radius=.07)
    for y in (-11,11):
        for x in (-13.0,-11.75):
            box('Precinct_gate_pier',(.22,.50,1.05),(x,y,.525),'stone')
        box('Precinct_gate_lintel',(1.55,.50,.18),(-12.375,y,1.10),'stone_light')
        cylinder('Precinct_gate_roof',1.02,.35,(-12.375,y,1.38),'tile',sides=4,top_radius=.10)
    # The wall is scene context, introduced at the same time as the first town wave.
    for obj in list(bpy.context.scene.objects):
        if obj.name.startswith(('Precinct_wall','Wall_coping','Enclosure_wall','Corner_guard','District_','Precinct_gate')):
            obj.hide_render=True
            obj.keyframe_insert(data_path='hide_render',frame=1)
            obj.keyframe_insert(data_path='hide_render',frame=240)
            obj.hide_render=False
            obj.keyframe_insert(data_path='hide_render',frame=241)
    box('Courtyard',(6.7,6.9,.04),(-11,-6,.02),'earth')


def vegetation():
    rng=random.Random(1954)
    positions=[]
    for _ in range(1900):
        x,y=rng.uniform(-65,65),rng.uniform(-49,79)
        if -20.5<x<23.5 and -16.5<y<15.5:
            continue
        if abs(x-river_x(y))<2.6 or ((x-39)/7)**2+((y-8)/10)**2<1:
            continue
        positions.append((x,y))
    for x,y in ((-17,9),(-17,4),(-17,-1),(-17,-7),(-15,0),(-9,1),(-10,10),
                (-6,-16),(0,-17),(7,-17),(14,-17),(22,-17),(23,0),(23,5),(23,10)):
        positions.append((x,y))
    phi=(1+math.sqrt(5))/2
    ico=[(-1,phi,0),(1,phi,0),(-1,-phi,0),(1,-phi,0),(0,-1,phi),(0,1,phi),
         (0,-1,-phi),(0,1,-phi),(phi,0,-1),(phi,0,1),(-phi,0,-1),(-phi,0,1)]
    ico=[tuple(c/math.sqrt(1+phi*phi) for c in p) for p in ico]
    triangles=[(0,11,5),(0,5,1),(0,1,7),(0,7,10),(0,10,11),(1,5,9),(5,11,4),
               (11,10,2),(10,7,6),(7,1,8),(3,9,4),(3,4,2),(3,2,6),(3,6,8),
               (3,8,9),(4,9,5),(2,4,11),(6,2,10),(8,6,7),(9,8,1)]
    leaves={key:([],[]) for key in ('leaf','field_green','bank')}
    trunk_v,trunk_f=[],[]
    for x,y in positions:
        z=elevation(x,y)
        height=rng.uniform(.85,1.65)
        radius=rng.uniform(.33,.58)
        for cluster in range(3):
            verts,faces=leaves[rng.choice(tuple(leaves))]
            offset=len(verts)
            dx,dy=rng.uniform(-.22,.22),rng.uniform(-.22,.22)
            for vx,vy,vz in ico:
                jitter=rng.uniform(.85,1.15)
                verts.append((x+dx+vx*radius*jitter,y+dy+vy*radius*jitter,z+height+cluster*.12+vz*radius*.85*jitter))
            faces.extend(tuple(offset+i for i in f) for f in triangles)
        offset=len(trunk_v)
        for zz,r in ((z,.045),(z+height,.025)):
            trunk_v.extend((x+r*math.cos(i*math.tau/5),y+r*math.sin(i*math.tau/5),zz) for i in range(5))
        trunk_f.extend((offset+i,offset+(i+1)%5,offset+(i+1)%5+5,offset+i+5) for i in range(5))
    for key,(verts,faces) in leaves.items():
        obj=mesh_object('Broadleaf_canopies_'+key,verts,faces,key)
        for poly in obj.data.polygons:
            poly.use_smooth=True
    mesh_object('Tree_trunks',trunk_v,trunk_f,'wood')


def create():
    surface()
    streets_and_precinct()
    vegetation()
