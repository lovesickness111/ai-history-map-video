"""Stage-by-stage growth with visibility explicitly keyed on mesh children."""


def animate(assembly, instance):
    start,end=instance["start_frame"],instance["end_frame"]
    count=len(assembly.stages)
    windows=[]
    for i,stage in enumerate(assembly.stages):
        first=start+round(i*(end-start)/count)
        last=start+round((i+1)*(end-start)/count)
        if stage.get('deform_growth'):
            for obj in stage.children:
                key=obj.data.shape_keys.key_blocks['Full']
                key.value=.001
                key.keyframe_insert(data_path='value',frame=max(1,first-1))
                key.value=1
                key.keyframe_insert(data_path='value',frame=last)
        else:
            stage.scale=(1,1,.001)
            stage.keyframe_insert(data_path="scale",frame=max(1,first-1))
            stage.scale=(1,1,1)
            stage.keyframe_insert(data_path="scale",frame=last)
        for obj in stage.children:
            obj.hide_render=True
            if first>1:
                obj.keyframe_insert(data_path="hide_render",frame=1)
                obj.keyframe_insert(data_path="hide_render",frame=first-1)
            obj.hide_render=False
            obj.keyframe_insert(data_path="hide_render",frame=first)
            # Boolean keyframes use constant interpolation by default in Blender.
        windows.append({"name":stage.name,"start":first,"end":last})
    return windows
