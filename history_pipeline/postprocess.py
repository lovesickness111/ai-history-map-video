"""ASS timeline overlays and shell-free FFmpeg video/audio assembly."""
from __future__ import annotations
import json
import math
from pathlib import Path
from .timeline import ROOT,year_at,event_at,frame_seconds

FONT_DIR=ROOT/'assets'/'fonts'


def ass_time(seconds):
    centis=math.floor(seconds*100+1e-7)
    h,rem=divmod(centis,360000)
    m,rem=divmod(rem,6000)
    s,cs=divmod(rem,100)
    return f'{h}:{m:02}:{s:02}.{cs:02}'


def ass_text(text):
    # Prevent ASS overrides and accidental escape sequences from timeline input.
    return text.replace('\\','\\\u200b').replace('{','｛').replace('}','｝').replace('\r','').replace('\n',r'\N')


def write_ass(data,path):
    lines=['[Script Info]','ScriptType: v4.00+','PlayResX: 1920','PlayResY: 1080',
           'ScaledBorderAndShadow: yes','WrapStyle: 2','','[V4+ Styles]',
           'Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding',
           'Style: Title,Be Vietnam Pro,52,&H00FFFFFF,&H00FFFFFF,&H00181512,&H80000000,-1,0,0,0,100,100,2,0,1,2.0,2.5,7,0,0,0,1',
           'Style: Year,Be Vietnam Pro,76,&H00FFFFFF,&H00FFFFFF,&H00181512,&H90000000,-1,0,0,0,100,100,1,0,1,2.5,3.0,7,0,0,0,1',
           'Style: Era,Be Vietnam Pro,34,&H0042D7FF,&H0042D7FF,&H00181512,&H80000000,-1,0,0,0,100,100,1,0,1,1.8,2.0,7,0,0,0,1',
           'Style: Note,Be Vietnam Pro,22,&H00E0E0E0,&H00E0E0E0,&H00181512,&H80000000,0,0,0,0,100,100,0,0,1,1.2,1.5,7,0,0,0,1',
           'Style: BigCity,Be Vietnam Pro,72,&H00FFFFFF,&H00FFFFFF,&H00181512,&H80000000,-1,0,0,0,100,100,4,0,1,3.0,4.0,7,0,0,0,1',
           '','[Events]','Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text']

    duration=data['frame_end']/data['fps']
    def add(start,end,style,text,x=None,y=None):
        pos=f'{{\\pos({x},{y})}}' if (x is not None and y is not None) else ''
        lines.append(f'Dialogue: 1,{ass_time(start)},{ass_time(end)},{style},,0,0,0,,{pos}{ass_text(text)}')

    geographic=data.get('scene_profile')=='geographic'
    # Prominent bottom cinematic title banner (like JERUSALEM in reference)
    add(0,duration,'BigCity','THĂNG LONG — HÀ NỘI',480,980)

    # Top-left major documentary historical indicator
    if geographic:
        intro_end=data['gis']['metadata']['intro']['zoom_end']/data['fps']
        add(0,intro_end,'Era','ĐỊNH VỊ ĐỊA LÝ · CHÂU THỔ SÔNG HỒNG',80,48)
        add(intro_end,duration,'Era','3D HISTORICAL TIMELAPSE',80,48)
    else:
        add(0,duration,'Era','3D HISTORICAL TIMELAPSE',80,48)

    # Dynamic year ticker in prominent bold style
    for frame in range(1,data['frame_end']+1):
        if geographic and frame<121:
            add(frame_seconds(frame,data['fps']),frame/data['fps'],'Year','NĂM 1010',80,92)
        else:
            add(frame_seconds(frame,data['fps']),frame/data['fps'],'Year',f"NĂM {year_at(data,frame)}",80,92)

    # Historical event descriptions with gold accent
    for event in data.get('events',[]):
        add(frame_seconds(event['frame'],data['fps']),event['end_frame']/data['fps'],'Note',event['text'],80,185)

    Path(path).write_text('\n'.join(lines)+'\n',encoding='utf-8-sig')


def filter_path(path):
    # FFmpeg filtergraph quoting is separate from subprocess argument quoting.
    value=Path(path).resolve().as_posix()
    return "'"+value.replace('\\','\\\\').replace(':','\\:').replace("'", "'\\\\\\''")+"'"


def video_command(ffmpeg,run_dir,data,music=None,sfx=None):
    run_dir=Path(run_dir)
    duration=data['frame_end']/data['fps']
    command=[str(ffmpeg),'-hide_banner','-y','-framerate',str(data['fps']),
             '-start_number','1','-i',str(run_dir/'frames'/'frame_%04d.png')]
    index=1
    filters=[]
    labels=[]
    if music:
        command+=['-stream_loop','-1','-i',str(music)]
        filters.append(f'[{index}:a]atrim=duration={duration},asetpts=PTS-STARTPTS,volume=0.22,afade=t=in:d=0.6,afade=t=out:st={duration-1}:d=1[music]')
        labels.append('[music]')
        index+=1
    if sfx:
        command+=['-i',str(sfx)]
        # Repeat the user-provided one-shot at each assembly activation.
        starts=[item['start_frame'] for item in data['instances']]
        branches=''.join(f'[one{i}]' for i in range(len(starts)))
        filters.append(f'[{index}:a]atrim=duration=1.5,asetpts=PTS-STARTPTS,volume=0.35,asplit={len(starts)}{branches}')
        for i,frame in enumerate(starts):
            delay=round(frame_seconds(frame,data['fps'])*1000)
            gain=.12 if data['instances'][i]['model_id']=='nha_co' else 1
            filters.append(f'[one{i}]volume={gain},adelay={delay}:all=1[sfx{i}]')
            labels.append(f'[sfx{i}]')
    overlay=f"ass=filename={filter_path(run_dir/'overlay.ass')}:fontsdir={filter_path(FONT_DIR)}"
    filters.append(f'[0:v]{overlay}[video]')
    if labels:
        filters.append(f"{''.join(labels)}amix=inputs={len(labels)}:normalize=0,alimiter=limit=0.95,apad,atrim=duration={duration}[audio]")
    script=run_dir/'ffmpeg_filters.txt'
    script.write_text(';\n'.join(filters),encoding='utf-8')
    command+=['-/filter_complex',str(script),'-map','[video]']
    if labels:
        command+=['-map','[audio]','-c:a','aac','-b:a','192k','-ar','48000']
    command+=['-c:v','libx264','-preset','fast','-crf','19','-pix_fmt','yuv420p',
              '-frames:v',str(data['frame_end']),'-t',str(duration),'-movflags','+faststart',str(run_dir/'final_video.mp4')]
    return command


def check_frames(run_dir,total):
    frames=Path(run_dir)/'frames'
    expected={f'frame_{i:04d}.png' for i in range(1,total+1)}
    actual={p.name for p in frames.glob('*.png') if p.stat().st_size>0}
    if actual!=expected:
        raise ValueError(f'Incomplete frame sequence: missing {len(expected-actual)}, unexpected {len(actual-expected)}')


def poster_command(ffmpeg,video,path,last_frame):
    return [str(ffmpeg),'-hide_banner','-y','-i',str(video),'-vf',f'select=eq(n\\,{last_frame-1})',
            '-frames:v','1','-fps_mode','vfr',str(path)]


def validate_probe(probe,data,width,height,expect_audio):
    video=next(s for s in probe['streams'] if s['codec_type']=='video')
    assert (video['width'],video['height'])==(width,height),'Wrong video dimensions'
    num,den=map(int,video['avg_frame_rate'].split('/'))
    assert abs(num/den-data['fps'])<1e-7,'Wrong frame rate'
    assert int(video.get('nb_read_frames',video.get('nb_frames',0)))==data['frame_end'],'Wrong frame count'
    assert abs(float(probe['format']['duration'])-data['frame_end']/data['fps'])<.06,'Wrong duration'
    assert video['codec_name']=='h264' and video['pix_fmt']=='yuv420p','Wrong video format'
    audio=any(s['codec_type']=='audio' for s in probe['streams'])
    assert audio==expect_audio,'Unexpected audio stream state'
    return {'width':width,'height':height,'fps':data['fps'],'frames':data['frame_end'],
            'duration':float(probe['format']['duration']),'audio':audio,'passed':True}
