"""Blender entry point; all paths received as structured JSON, never shell code."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import struct
import sys
import time

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))

import bpy
from mathutils import Vector,Matrix
from bpy_extras.object_utils import world_to_camera_view
from history_pipeline.scene import make_scene,camera_at,configure


def write_json(path,data):
    path.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')


def scene_signature():
    """This generated scene animates visibility and transforms only.

    Identical evaluated states can reuse PNGs while overlays still advance.
    No rounding: any transform change, however small, forces a new render.
    """
    digest=hashlib.sha256()
    scene=bpy.context.scene
    camera=scene.camera
    digest.update(struct.pack('16d',*(value for row in camera.matrix_world for value in row)))
    digest.update(repr((camera.data.type,camera.data.lens,camera.data.ortho_scale,
                        camera.data.clip_start,camera.data.clip_end)).encode())
    for obj in scene.objects:
        if obj.type in ('MESH','FONT','CURVE') and not obj.hide_render:
            digest.update(obj.name.encode('utf-8'))
            digest.update(struct.pack('16d',*(value for row in obj.matrix_world for value in row)))
            if obj.type=='MESH' and obj.data.shape_keys:
                digest.update(repr([key.value for key in obj.data.shape_keys.key_blocks]).encode())
    return digest.digest()


def render_sequence(scene,out):
    frames=out/'frames'
    frames.mkdir(exist_ok=True)
    scene.render.use_file_extension=True
    previous_signature=None
    previous_path=None
    rendered=reused=0
    started=time.monotonic()
    for frame in range(scene.frame_start,scene.frame_end+1):
        scene.frame_set(frame)
        signature=scene_signature()
        target=frames/f'frame_{frame:04d}.png'
        if signature==previous_signature:
            shutil.copyfile(previous_path,target)
            reused+=1
        else:
            scene.render.filepath=str(target)
            bpy.ops.render.render(write_still=True)
            rendered+=1
        previous_signature,previous_path=signature,target
        if frame%30==0 or frame==scene.frame_end:
            report={'completed':frame,'total':scene.frame_end,'rendered':rendered,'reused':reused,
                    'elapsed_seconds':round(time.monotonic()-started,3)}
            write_json(out/'render_progress.json',report)
            print(f'FRAME {frame}/{scene.frame_end}; rendered={rendered}; reused={reused}',flush=True)
    write_json(out/'render_stats.json',report)


def model_portrait(subject,config,path):
    """Separate unanimated scene: keyed visibility cannot undo isolation."""
    main=bpy.context.scene
    portrait=bpy.data.scenes.new('Architecture_portrait')
    portrait.world=main.world
    created=[]
    try:
        with bpy.context.temp_override(scene=portrait):
            configure(config)
            shift=Matrix.Translation(-subject.root.location)
            for stage in subject.stages:
                for original in stage.children:
                    obj=original.copy()
                    obj.animation_data_clear()
                    obj.parent=None
                    obj.matrix_world=shift @ original.matrix_world
                    obj.hide_render=False
                    portrait.collection.objects.link(obj)
                    created.append(obj)
            for original in main.objects:
                if original.type=='LIGHT':
                    light=original.copy()
                    portrait.collection.objects.link(light)
                    created.append(light)
            height=subject.bounds[1][2]*subject.root.scale.z
            width=(subject.bounds[1][0]-subject.bounds[0][0])*subject.root.scale.x
            depth=(subject.bounds[1][1]-subject.bounds[0][1])*subject.root.scale.y
            scale=max(height*config['width']/config['height']*1.35,(width+depth)*.9,3.0)
            target=Vector((0,0,height*.47))
            cam=camera_at(target+Vector((9,-13,9)),target,scale)
            created.append(cam)
            portrait.view_layers[0].update()
            geometry=[obj for obj in created if obj.type=='MESH']
            def projected_bounds():
                points=[world_to_camera_view(portrait,cam,obj.matrix_world @ Vector(corner))
                        for obj in geometry for corner in obj.bound_box]
                return min(p.x for p in points),max(p.x for p in points),min(p.y for p in points),max(p.y for p in points)
            left,right,bottom,top=projected_bounds()
            cam.data.ortho_scale*=max(1,(right-left)/.86,(top-bottom)/.84)*1.02
            left,right,bottom,top=projected_bounds()
            rotation=cam.matrix_world.to_quaternion()
            cam.location+=(rotation @ Vector((1,0,0)))*(((left+right)/2-.5)*cam.data.ortho_scale)
            cam.location+=(rotation @ Vector((0,1,0)))*(((bottom+top)/2-.5)*cam.data.ortho_scale*config['height']/config['width'])
            portrait.view_layers[0].update()
            left,right,bottom,top=projected_bounds()
            assert .01<left<right<.99 and .01<bottom<top<.99,'Portrait camera clips architecture'
            portrait.render.filepath=str(path)
            bpy.ops.render.render(write_still=True,scene=portrait.name)
    finally:
        bpy.data.scenes.remove(portrait)
        for obj in created:
            bpy.data.objects.remove(obj,do_unlink=True)


def verify_animation(config,assemblies,animation_instances=None):
    checks=[]
    scheduled={}
    scene=bpy.context.scene
    def schedule(frame,kind,assembly,index=None):
        scheduled.setdefault(frame,[]).append((kind,assembly,index))
    def growth(stage):
        return stage.children[0].data.shape_keys.key_blocks['Full'].value if stage.get('deform_growth') else stage.scale.z
    for assembly,instance in zip(assemblies,animation_instances or config['timeline']['instances']):
        stages=assembly.stages
        if instance['start_frame']>1:
            schedule(instance['start_frame']-1,'hidden',assembly)
        start,end=instance['start_frame'],instance['end_frame']
        for i,stage in enumerate(stages):
            first=start+round(i*(end-start)/len(stages))
            last=start+round((i+1)*(end-start)/len(stages))
            schedule((first+last)//2,'growing',assembly,i)
        if end<=config['timeline']['frame_end']:
            schedule(end,'complete',assembly)
            schedule(config['timeline']['frame_end'],'complete',assembly)
        elif start>config['timeline']['frame_end']:
            schedule(config['timeline']['frame_end'],'hidden',assembly)
        checks.append(instance['id'])
    for frame,tasks in sorted(scheduled.items()):
        scene.frame_set(frame)
        for kind,assembly,index in tasks:
            stages=assembly.stages
            if kind=='hidden':
                assert all(obj.hide_render for stage in stages for obj in stage.children),assembly.root.name
            elif kind=='growing':
                stage=stages[index]
                assert all(not obj.hide_render for obj in stage.children),stage.name
                assert 0<growth(stage)<1,stage.name
                assert all(obj.hide_render for future in stages[index+1:] for obj in future.children),stage.name
            else:
                assert all(not obj.hide_render for stage in stages for obj in stage.children),assembly.root.name
                assert all(abs(growth(stage)-1)<1e-5 for stage in stages),assembly.root.name
    is_gis = bool(config['timeline'].get('gis_scene') or config['timeline'].get('scene_profile') == 'geographic')
    if is_gis:
        hero_frames = {'pagoda': 190, 'flag_tower': 720}
        for assembly, instance in zip(assemblies, animation_instances or config['timeline']['instances']):
            if instance['id'] not in hero_frames:
                continue
            check_frame = hero_frames[instance['id']]
            if check_frame <= config['timeline']['frame_end']:
                scene.frame_set(check_frame)
                bpy.context.view_layer.update()
                for stage in assembly.stages:
                    for obj in stage.children:
                        if obj.hide_render: continue
                        for corner in obj.bound_box:
                            uv = world_to_camera_view(scene, scene.camera, obj.matrix_world @ Vector(corner))
                            assert 0.0 < uv.x < 1.0 and 0.0 < uv.y < 1.0, (obj.name, tuple(uv), check_frame)
    else:
        scene.frame_set(config['timeline']['frame_end'])
        bpy.context.view_layer.update()
        for assembly in assemblies:
            for stage in assembly.stages:
                for obj in stage.children:
                    if obj.hide_render: continue
                    for corner in obj.bound_box:
                        uv = world_to_camera_view(scene, scene.camera, obj.matrix_world @ Vector(corner))
                        assert .02 < uv.x < .98 and .10 < uv.y < .80, (obj.name, tuple(uv))
    return {"visibility_and_completed_scale":checks,"camera_safe_area":True,"evaluated_check_frames":len(scheduled)}


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--config',required=True)
    parser.add_argument('--mode',choices=('smoke','preview','render','verify'),required=True)
    args=parser.parse_args(sys.argv[sys.argv.index('--')+1:])
    config=json.loads(Path(args.config).read_text(encoding='utf-8'))
    out=Path(config['run_dir'])
    out.mkdir(parents=True,exist_ok=True)
    start=time.monotonic()
    print('Building landscape and architecture...',flush=True)
    assemblies,stats=make_scene(config)
    print(f"Scene built: {stats['triangles']} triangles, {stats['mesh_objects']} mesh objects",flush=True)
    stats['blender_version']=bpy.app.version_string
    stats['engine']=config['engine']
    if args.mode=='smoke':
        smoke_width,smoke_height=config.get('preflight_resolution',[160,90])
        bpy.context.scene.render.resolution_x=smoke_width
        bpy.context.scene.render.resolution_y=smoke_height
        bpy.context.scene.render.filepath=str(out/f"smoke_{config['engine']}.png")
        bpy.ops.render.render(write_still=True)
        stats['seconds']=time.monotonic()-start
        write_json(out/f"smoke_{config['engine']}.json",stats)
        return
    print('Checking animation stages and camera...',flush=True)
    stats['checks']=verify_animation(config,assemblies,stats.get('animation_instances'))
    print('Checks passed.',flush=True)
    write_json(out/'scene_stats.json',stats)
    bpy.context.scene.render.filepath=str(out/'frames'/'frame_')
    bpy.ops.wm.save_as_mainfile(filepath=str(out/'scene.blend'))
    if args.mode=='verify':
        return
    scene=bpy.context.scene
    if args.mode=='render':
        render_sequence(scene,out)
    else:
        preview=out/'previews'
        preview.mkdir(exist_ok=True)
        frames={f for f in (1,120,121,140,180,295,475,660,661,687,720,835,900)
                if f<=config['timeline']['frame_end']}
        frames.add(config['timeline']['frame_end'])
        for instance in config['timeline']['instances']:
            if instance['model_id']!='nha_co':
                frames.update((max(1,instance['start_frame']-1),instance['start_frame'],
                               (instance['start_frame']+instance['end_frame'])//2,instance['end_frame']))
        for frame in sorted(frames):
            scene.frame_set(frame)
            scene.render.filepath=str(preview/f"frame_{frame:04d}.png")
            bpy.ops.render.render(write_still=True)
        scene.frame_set(config['timeline']['frame_end'])
        for model_id in ('chua_mot_cot','cot_co','nha_co'):
            subject=next((a for a in assemblies if a.root['model_id']==model_id),None)
            if subject is not None:
                model_portrait(subject,config,preview/f"model_{model_id}.png")
            elif model_id=='nha_co':
                from history_pipeline.models import build
                instance=next((i for i in config['timeline']['instances'] if i['model_id']=='nha_co'),None)
                if instance:
                    subject=build(instance)
                    bpy.context.view_layer.update()
                    model_portrait(subject,config,preview/f"model_{model_id}.png")
    print(f"PIPELINE COMPLETE: {time.monotonic()-start:.2f}s",flush=True)


if __name__=='__main__':
    main()
