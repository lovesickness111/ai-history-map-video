"""Georeferenced terrain, mapped streets/water, country fly-in and batched town."""
import math
from collections import defaultdict
import bpy
from mathutils import Vector,Matrix
from .geometry import mesh_object,material,ModelAssembly,cylinder,linear,box
from .geo import sample_height,point_in_ring
from .models import build,old_house
from .animation import animate


def terrain(geo):
    grid=geo['grid']
    rows,cols=grid['rows'],grid['cols']
    heights=[row[:] for row in grid['heights']]
    for r in range(rows):
        for c in range(cols):
            x,y=grid['x0']+c*grid['dx'],grid['y0']+r*grid['dy']
            for water in geo['water']:
                if point_in_ring(x,y,water['outer']) and not any(point_in_ring(x,y,hole) for hole in water['holes']):
                    heights[r][c]=water['level_z']-.025
                    break
    vertices=[(grid['x0']+c*grid['dx'],grid['y0']+r*grid['dy'],heights[r][c])
              for r in range(rows) for c in range(cols)]
    faces=[(r*cols+c,(r+1)*cols+c,(r+1)*cols+c+1,r*cols+c+1)
           for r in range(rows-1) for c in range(cols-1)]
    obj=mesh_object('Hanoi_Copernicus_metric_terrain',vertices,faces,'grass')
    for poly in obj.data.polygons: poly.use_smooth=True
    vertices,faces=[],[]
    for road in geo['roads']:
        for a,b in zip(road['points'],road['points'][1:]):
            direction=Vector((b[0]-a[0],b[1]-a[1]))
            if direction.length<1e-5: continue
            n=Vector((-direction.y,direction.x)).normalized()*road['width']/2
            k=len(vertices)
            for x,y in ((a[0]-n.x,a[1]-n.y),(b[0]-n.x,b[1]-n.y),(b[0]+n.x,b[1]+n.y),(a[0]+n.x,a[1]+n.y)):
                vertices.append((x,y,sample_height(grid,x,y)+.025))
            faces.append((k,k+1,k+2,k+3))
    mesh_object('OSM_mapped_streets',vertices,faces,'road')
    vertices,faces=[],[]
    for water in geo['water']:
        for triangle in water['triangles']:
            k=len(vertices)
            vertices.extend((x,y,water['level_z']) for x,y in triangle)
            a,b,c=triangle
            face=(k,k+1,k+2)
            if (b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0])<0: face=tuple(reversed(face))
            faces.append(face)
    mesh_object('OSM_actual_water_boundaries',vertices,faces,'water')


def overview(geo):
    country=geo['country']
    obj=mesh_object('Vietnam_geographic_overview',country['vertices'],country['faces'],'grass')
    mesh=obj.data
    colors=mesh.color_attributes.new(name='terrain_elevation',type='FLOAT_COLOR',domain='POINT')
    for item,color in zip(colors.data,country['colors']):
        item.color=(*linear(color[:3]),1)
    mat=bpy.data.materials.new('Vietnam_elevation_palette')
    mat.use_nodes=True
    nodes,links=mat.node_tree.nodes,mat.node_tree.links
    attr=nodes.new('ShaderNodeVertexColor')
    attr.layer_name='terrain_elevation'
    shader=nodes.get('Principled BSDF')
    links.new(attr.outputs['Color'],shader.inputs['Base Color'])
    shader.inputs['Roughness'].default_value=.9
    mesh.materials.clear()
    mesh.materials.append(mat)
    for poly in mesh.polygons: poly.use_smooth=True
    sea_z=-geo['metadata']['z_origin_m']/geo['metadata']['meters_per_unit']-.1
    left,bottom,right,top=country['bounds_scene']
    pad=400000
    mesh_object('Regional_sea',[(left-pad,bottom-pad,sea_z),(right+pad,bottom-pad,sea_z),
                               (right+pad,top+pad,sea_z),(left-pad,top+pad,sea_z)],[(0,1,2,3)],'water')
    # A geographic ring is visible only in the opening country view.
    marker=cylinder('Hanoi_locator',900,100,(0,0,sea_z+600),'gold',sides=40)
    marker.hide_render=False
    marker.keyframe_insert(data_path='hide_render',frame=1)
    marker.keyframe_insert(data_path='hide_render',frame=55)
    marker.hide_render=True
    marker.keyframe_insert(data_path='hide_render',frame=65)


def citadel_ramparts(geo):
    """Build ancient citadel ramparts and fortified enclosure around central royal area."""
    grid=geo['grid']
    # Ancient imperial citadel perimeter (Hoàng Thành Thăng Long rampart bounds)
    walls=[
        ((-165,-25),(-50,-25)),
        ((-50,-25),(-50,65)),
        ((-50,65),(-165,65)),
        ((-165,65),(-165,-25)),
    ]
    wall_verts,wall_faces=[],[]
    wall_w,wall_h=1.8,2.2
    for p1,p2 in walls:
        v1=Vector(p1)
        v2=Vector(p2)
        direction=(v2-v1).normalized()
        normal=Vector((-direction.y,direction.x))*wall_w/2
        z1=sample_height(grid,*p1)+0.05
        z2=sample_height(grid,*p2)+0.05
        base_idx=len(wall_verts)
        # 4 bottom vertices, 4 top vertices
        b1,b2=v1-normal,v1+normal
        b3,b4=v2+normal,v2-normal
        wall_verts.extend([
            (b1.x,b1.y,z1),(b2.x,b2.y,z1),(b3.x,b3.y,z2),(b4.x,b4.y,z2),
            (b1.x,b1.y,z1+wall_h),(b2.x,b2.y,z1+wall_h),(b3.x,b3.y,z2+wall_h),(b4.x,b4.y,z2+wall_h),
        ])
        # Bottom, Top, Front, Back, Left, Right faces
        wall_faces.extend([
            (base_idx+0,base_idx+1,base_idx+2,base_idx+3), # bottom
            (base_idx+7,base_idx+6,base_idx+5,base_idx+4), # top
            (base_idx+0,base_idx+3,base_idx+7,base_idx+4), # side 1
            (base_idx+2,base_idx+1,base_idx+5,base_idx+6), # side 2
            (base_idx+1,base_idx+0,base_idx+4,base_idx+5), # side 3
            (base_idx+3,base_idx+2,base_idx+6,base_idx+7), # side 4
        ])
    mesh_object('Imperial_Citadel_Walls',wall_verts,wall_faces,'brick')

    # Watchtowers and gates at rampart corners
    corners=[(-165,-25),(-50,-25),(-50,65),(-165,65),(-107,-25)]
    for idx,(cx,cy) in enumerate(corners):
        cz=sample_height(grid,cx,cy)
        cylinder(f'Citadel_Tower_{idx}',1.9,wall_h+1.2,(cx,cy,cz+(wall_h+1.2)/2),'stone',sides=8)
        cylinder(f'Citadel_Roof_{idx}',2.4,.5,(cx,cy,cz+wall_h+1.35),'tile',sides=8,top_radius=0.1)


def prototype(params,seed):
    assembly=old_house('__house_prototype',params,seed)
    stages=[]
    for stage in assembly.stages:
        obj=stage.children[0]
        matrix=stage.matrix_basis @ obj.matrix_basis
        stages.append({'base':stage.location.z,'vertices':[tuple(matrix @ v.co) for v in obj.data.vertices],
                       'faces':[tuple(p.vertices) for p in obj.data.polygons],
                       'materials':[m.name for m in obj.data.materials],
                       'indices':[p.material_index for p in obj.data.polygons]})
    for stage in assembly.stages:
        for obj in list(stage.children): bpy.data.objects.remove(obj,do_unlink=True)
        bpy.data.objects.remove(stage,do_unlink=True)
    bpy.data.objects.remove(assembly.root,do_unlink=True)
    return stages


def town_batches(instances):
    groups=defaultdict(list)
    for item in instances: groups[item['start_frame']].append(item)
    templates={}
    results=[]
    records=[]
    for start,houses in sorted(groups.items()):
        assembly=ModelAssembly.create(f'town_{start}')
        assembly.root['model_id']='town_batch'
        all_full=[]
        for stage_index in range(3):
            stage=assembly.stage(('walls','roof','joinery')[stage_index],0)
            stage['deform_growth']=True
            vertices,full,faces,indices,matnames=[],[],[],[],[]
            for house in houses:
                key=repr(sorted(house['params'].items()))
                if key not in templates: templates[key]=prototype(house['params'],house['seed'])
                source=templates[key][stage_index]
                angle=math.radians(house['rotation'][2])
                co,si=math.cos(angle),math.sin(angle)
                x,y,z=house['position']
                sx,sy,sz=house['scale']
                offset=len(vertices)
                for vx,vy,vz in source['vertices']:
                    xx,yy=x+co*vx*sx-si*vy*sy,y+si*vx*sx+co*vy*sy
                    vertices.append((xx,yy,z+source['base']*sz))
                    full.append((xx,yy,z+vz*sz))
                remap=[]
                for name in source['materials']:
                    if name not in matnames: matnames.append(name)
                    remap.append(matnames.index(name))
                faces.extend(tuple(offset+i for i in face) for face in source['faces'])
                indices.extend(remap[index] for index in source['indices'])
            mesh=bpy.data.meshes.new(stage.name+'/mesh')
            mesh.from_pydata(vertices,[],faces)
            for name in matnames: mesh.materials.append(bpy.data.materials[name])
            for poly,index in zip(mesh.polygons,indices): poly.material_index=index
            mesh.update()
            obj=bpy.data.objects.new(stage.name+'/geometry',mesh)
            bpy.context.scene.collection.objects.link(obj)
            obj.parent=stage
            obj.shape_key_add(name='Basis')
            growth=obj.shape_key_add(name='Full')
            for vertex,position in zip(growth.data,full): vertex.co=position
            growth.value=1
            all_full.extend(full)
        assembly.bounds=(tuple(min(p[i] for p in all_full) for i in range(3)),
                         tuple(max(p[i] for p in all_full) for i in range(3)))
        record={'id':assembly.root.name,'model_id':'town_batch','start_frame':start,'end_frame':start+24,
                'house_count':len(houses),'position':[0,0,0],'scale':[1,1,1]}
        animate(assembly,record)
        results.append(assembly)
        records.append(record)
    return results,records


def create(config):
    data=config['timeline']
    geo=data['gis']
    terrain(geo)
    overview(geo)
    citadel_ramparts(geo)
    assemblies=[]
    records=[]
    for instance in data['instances']:
        if instance['model_id']=='nha_co': continue
        a=build(instance)
        animate(a,instance)
        assemblies.append(a)
        records.append(instance)
    batches,batch_records=town_batches([i for i in data['instances'] if i['model_id']=='nha_co'])
    assemblies.extend(batches)
    records.extend(batch_records)
    # Historical square lotus pond (Hồ Linh Chiểu) centered under One Pillar Pagoda
    px,py,pz=next(p['position'] for p in geo['landmarks'] if p['id']=='pagoda')
    box("Pagoda_pond_rim",(4.6,4.6,.08),(px,py,pz-.02),"stone")
    box("Pagoda_pond",(4.35,4.35,.03),(px,py,pz+.01),"water")
    return assemblies,records


def animate_camera(config,assemblies):
    from .scene import camera_at
    scene=bpy.context.scene
    geo=config['timeline']['gis']
    grid=geo['grid']

    # Historical central targets
    hanoi_citadel=Vector((-107,20,0))
    targets={'pagoda':Vector(next(p['position'] for p in geo['landmarks'] if p['id']=='pagoda')),
             'flag_tower':Vector(next(p['position'] for p in geo['landmarks'] if p['id']=='flag_tower'))}
    p_loc=targets['pagoda']+Vector((0,0,.35))
    f_loc=targets['flag_tower']+Vector((0,0,1.2))

    cam=camera_at(Vector((0,0,100)),hanoi_citadel,perspective=True)
    cam.data.lens=42  # Cinematic 42mm lens with perspective depth

    country=geo['country']['bounds_scene']
    national_target=Vector(((country[0]+country[2])/2,(country[1]+country[3])/2,0))
    national_distance=max(country[2]-country[0],(country[3]-country[1])*config['width']/config['height'])*1.55

    def smooth(t):
        t=max(0.0,min(1.0,t))
        return t*t*(3.0-2.0*t)

    def set_camera(frame,focus,distance,elevation_deg,azimuth_deg):
        elev=math.radians(elevation_deg)
        azim=math.radians(azimuth_deg)
        dx=distance*math.cos(elev)*math.sin(azim)
        dy=-distance*math.cos(elev)*math.cos(azim)
        dz=distance*math.sin(elev)
        loc=focus+Vector((dx,dy,dz))
        cam.location=loc
        cam.rotation_euler=(focus-loc).to_track_quat('-Z','Y').to_euler()
        cam.keyframe_insert(data_path='location',frame=frame)
        cam.keyframe_insert(data_path='rotation_euler',frame=frame)
        cam.data.clip_start=max(.05,distance/80000)
        cam.data.clip_end=max(6000,distance*5)
        cam.data.keyframe_insert(data_path='clip_start',frame=frame)
        cam.data.keyframe_insert(data_path='clip_end',frame=frame)

    total_f=config['timeline']['frame_end']
    for f in range(1,total_f+1):
        if f<=24:
            # SHOT 1 Intro: National Vietnam territory view
            set_camera(f,national_target,national_distance,88.0,0.0)
        elif f<=70:
            # Satellite descent zoom smoothly focusing on Hanoi / Thang Long Citadel
            t=smooth((f-24)/46)
            foc=national_target.lerp(hanoi_citadel,t)
            dist=math.exp(math.log(national_distance)*(1-t)+math.log(300)*t)
            elev=88.0*(1-t)+65.0*t
            azim=-15.0*t
            set_camera(f,foc,dist,elev,azim)
        elif f<=120:
            # SHOT 1 Finale (1010): Low-angle tracking glide along Thang Long Imperial Citadel & Red River
            t=smooth((f-70)/50)
            foc=hanoi_citadel.lerp(Vector((-60,15,0)),t)
            dist=300.0*(1-t)+145.0*t
            elev=65.0*(1-t)+26.0*t
            azim=-15.0*(1-t)+(-5.0)*t
            set_camera(f,foc,dist,elev,azim)
        elif f<=240:
            # SHOT 2 (1049): Hero landmark orbit around One Pillar Pagoda rising from the lotus pond
            t=(f-120)/120
            foc=p_loc
            dist=5.4-0.7*math.sin(t*math.pi)
            elev=21.0+3.5*math.sin(t*math.pi)
            azim=-45.0+80.0*t
            set_camera(f,foc,dist,elev,azim)
        elif f<=300:
            # Transition from Pagoda to City Overview & 36 Guild Streets
            t=smooth((f-240)/60)
            foc=p_loc.lerp(Vector((-30,10,0)),t)
            dist=math.exp(math.log(5.2)*(1-t)+math.log(155)*t)
            elev=22.0*(1-t)+28.0*t
            azim=35.0*(1-t)+(-20.0)*t
            set_camera(f,foc,dist,elev,azim)
        elif f<=630:
            # SHOT 3: Continuous dynamic tracking flyover across town houses and rivers
            t=(f-300)/330
            foc=Vector((-30,10,0)).lerp(Vector((10,-5,0)),t)
            dist=155.0-15.0*math.sin(t*math.pi)
            elev=28.0-3.0*math.sin(t*math.pi)
            azim=-20.0+35.0*math.sin(t*math.pi*1.2)
            set_camera(f,foc,dist,elev,azim)
        elif f<=660:
            # Transition into Flag Tower
            t=smooth((f-630)/30)
            foc=Vector((10,-5,0)).lerp(f_loc,t)
            dist=math.exp(math.log(145)*(1-t)+math.log(20)*t)
            elev=26.0*(1-t)+20.0*t
            azim=15.0*(1-t)+(-35.0)*t
            set_camera(f,foc,dist,elev,azim)
        elif f<=750:
            # SHOT 4: Low-angle dramatic upward orbit around Hanoi Flag Tower
            t=(f-660)/90
            foc=f_loc
            azim=-35.0+70.0*t
            dist=20.0-2.5*math.sin(t*math.pi)
            elev=20.0+4.5*math.sin(t*math.pi)
            set_camera(f,foc,dist,elev,azim)
        else:
            # SHOT 5: Sweeping wide panoramic shot to 1900 horizon
            t=smooth((f-750)/max(1,total_f-750))
            foc=f_loc.lerp(Vector((-30,5,0)),t)
            dist=math.exp(math.log(18)*(1-t)+math.log(165)*t)
            elev=23.0*(1-t)+27.0*t
            azim=35.0*(1-t)+(-15.0)*t
            set_camera(f,foc,dist,elev,azim)

    for owner in (cam,cam.data):
        action=owner.animation_data.action
        for curve in action.fcurves:
            for key in curve.keyframe_points: key.interpolation='LINEAR'
    scene.frame_set(config['timeline']['frame_end'])
    bpy.context.view_layer.update()
    return cam
