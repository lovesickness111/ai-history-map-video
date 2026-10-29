"""One-command Windows-friendly procedural history video pipeline."""
from __future__ import annotations
import argparse
from datetime import datetime
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time
import uuid

from history_pipeline.timeline import ROOT,DEFAULT_TIMELINE,load_timeline
from history_pipeline.postprocess import FONT_DIR,write_ass,video_command,check_frames,validate_probe,filter_path,poster_command


def write_json(path,data):
    Path(path).write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')


def find_blender(override=None):
    candidates=([Path(override)] if override else [])
    if not override:
        if os.environ.get('BLENDER_PATH'):
            candidates.append(Path(os.environ['BLENDER_PATH']))
        if shutil.which('blender'):
            candidates.append(Path(shutil.which('blender')))
        candidates.extend(sorted((ROOT/'tools').glob('blender-4.5.*-windows-x64/blender.exe'),
                                 key=lambda p:int(p.parent.name.split('-')[1].split('.')[-1]),reverse=True))
        candidates.extend(Path('C:/Program Files/Blender Foundation').glob('Blender 4.5*/blender.exe'))
    for candidate in candidates:
        if candidate.is_file():
            return candidate.resolve()
    raise ValueError('Blender 4.5 LTS not found. Run python scripts/bootstrap.py or pass --blender PATH')


def run_logged(command,log,cwd=ROOT):
    write_json(Path(log).with_suffix('.command.json'),[str(x) for x in command])
    started=time.monotonic()
    with Path(log).open('w',encoding='utf-8') as handle:
        process=subprocess.Popen([str(x) for x in command],cwd=cwd,stdout=handle,stderr=subprocess.STDOUT,
                                 env={**os.environ,'PYTHONUTF8':'1'})
        try:
            last=started
            while process.poll() is None:
                time.sleep(.5)
                if time.monotonic()-last>30:
                    frames=len(list((Path(log).parent/'frames').glob('*.png')))
                    print(f'  Working: {frames} frames written; {time.monotonic()-started:.0f}s elapsed. Log: {log}',flush=True)
                    last=time.monotonic()
        except BaseException:
            process.terminate()
            process.wait()
            raise
    if process.returncode:
        tail=Path(log).read_text(encoding='utf-8',errors='replace')[-5000:]
        raise RuntimeError(f'Command failed ({process.returncode}). Log: {log}\n{tail}')
    return time.monotonic()-started


def blender_command(blender,config,mode):
    return [blender,'--background','--factory-startup','--threads','4','--python-exit-code','1',
            '--python',ROOT/'scripts'/'blender_entry.py','--','--config',config,'--mode',mode]


def inspect_tools(blender):
    version=subprocess.check_output([str(blender),'--version'],text=True,encoding='utf-8').splitlines()[0]
    if not re.search(r'Blender 4\.5\.',version):
        raise ValueError(f'Unsupported {version}; this project is tested against Blender 4.5 LTS')
    ffmpeg=shutil.which('ffmpeg')
    ffprobe=shutil.which('ffprobe')
    if not ffmpeg or not ffprobe:
        raise ValueError('FFmpeg and ffprobe must be in PATH')
    ffmpeg_version=subprocess.check_output([ffmpeg,'-version'],text=True,encoding='utf-8').splitlines()[0]
    match=re.search(r'ffmpeg version (\d+)',ffmpeg_version)
    if match and int(match.group(1))<7:
        raise ValueError('FFmpeg 7+ is required for file-loaded filtergraphs')
    filters=subprocess.check_output([ffmpeg,'-hide_banner','-filters'],text=True,encoding='utf-8',stderr=subprocess.STDOUT)
    encoders=subprocess.check_output([ffmpeg,'-hide_banner','-encoders'],text=True,encoding='utf-8',stderr=subprocess.STDOUT)
    if ' ass ' not in filters or 'libx264' not in encoders or ' aac ' not in encoders:
        raise ValueError('FFmpeg needs the ass filter, libx264 and AAC encoders')
    if not (FONT_DIR/'BeVietnamPro-Bold.ttf').is_file() or not (FONT_DIR/'OFL.txt').is_file():
        raise ValueError('Missing font/license. Run python scripts/bootstrap.py')
    return {'blender':str(blender),'blender_version':version,'ffmpeg':ffmpeg,
            'ffmpeg_version':ffmpeg_version,'ffprobe':ffprobe}


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command',choices=('doctor','preview','render','fetch-gis'))
    parser.add_argument('--preset',choices=('draft','final'),default='draft')
    parser.add_argument('--blender')
    parser.add_argument('--timeline',type=Path,default=DEFAULT_TIMELINE)
    parser.add_argument('--output',type=Path,default=ROOT/'output')
    parser.add_argument('--music',type=Path)
    parser.add_argument('--sfx',type=Path)
    parser.add_argument('--engine',choices=('auto','eevee','cycles'),default='auto')
    parser.add_argument('--bbox',nargs=4,type=float)
    parser.add_argument('--frames',type=int,help='Render up to N frames (e.g. 240 frames for first 2 shots)')
    args=parser.parse_args(argv)
    if args.command=='fetch-gis':
        python=ROOT/'.venv'/'Scripts'/'python.exe'
        python=python if python.exists() else Path(sys.executable)
        command=[str(python),str(ROOT/'scripts'/'fetch_gis.py')]
        if args.bbox: command+=['--bbox',*map(str,args.bbox)]
        subprocess.run(command,cwd=ROOT,check=True)
        return 0
    # Data and asset validation precede any expensive render or run-directory mutation.
    data=load_timeline(args.timeline)
    if args.frames:
        if args.frames<30 or args.frames%data['fps']!=0:
            raise ValueError(f'--frames must be a positive multiple of {data["fps"]}')
        data['frame_end']=min(args.frames,data['frame_end'])
        data['events']=[e for e in data.get('events',[]) if e['frame']<=data['frame_end']]
        for e in data['events']: e['end_frame']=min(e['end_frame'],data['frame_end'])
        data['anchors']=[a for a in data['anchors'] if a['frame']<=data['frame_end']]
        if not any(a['frame']==data['frame_end'] for a in data['anchors']):
            data['anchors'].append({'frame':data['frame_end'],'year':data['anchors'][-1]['year']})
    for audio in (args.music,args.sfx):
        if audio and not audio.is_file():
            raise ValueError(f'Audio file not found: {audio}')
    blender=find_blender(args.blender)
    tools=inspect_tools(blender)
    for audio in (args.music,args.sfx):
        if audio:
            probe=json.loads(subprocess.check_output([tools['ffprobe'],'-v','error','-show_streams','-of','json',str(audio.resolve())]))
            if not any(s['codec_type']=='audio' for s in probe['streams']):
                raise ValueError(f'Input contains no audio stream: {audio}')
    run_dir=args.output.resolve()/(datetime.now().strftime('%Y%m%d_%H%M%S')+'_'+args.command+'_'+uuid.uuid4().hex[:6])
    run_dir.mkdir(parents=True)
    width,height=(1920,1080) if args.preset=='final' else (1280,720)
    if args.command=='preview':
        width,height=960,540
    config={'timeline':data,'preset':args.preset,'width':width,'height':height,'engine':'eevee',
            'run_dir':str(run_dir),'timeline_source':str(args.timeline.resolve()),'tools':tools,
            'preflight_resolution':[width,height] if args.command=='render' else [160,90],
            'audio':{'music':str(args.music.resolve()) if args.music else None,
                     'sfx':str(args.sfx.resolve()) if args.sfx else None}}
    config_path=run_dir/'config.json'
    print(f'Output: {run_dir}',flush=True)
    engines=('eevee','cycles') if args.engine=='auto' else (args.engine,)
    failures=[]
    for engine in engines:
        config['engine']=engine
        write_json(config_path,config)
        try:
            seconds=run_logged(blender_command(blender,config_path,'smoke'),run_dir/f'preflight_{engine}.log')
            config['preflight_seconds']=seconds
            break
        except RuntimeError as exc:
            failures.append(str(exc))
            print(f'Preflight {engine} failed; see {run_dir / ("preflight_"+engine+".log")}',flush=True)
    else:
        raise RuntimeError('\n'.join(failures))
    config['preflight_failures']=failures
    write_json(config_path,config)
    print(f'Renderer: {config["engine"]}; preflight: {config["preflight_seconds"]:.1f}s',flush=True)
    if args.command=='doctor':
        run_logged(blender_command(blender,config_path,'verify'),run_dir/'verify.log')
        write_json(run_dir/'doctor.json',{'passed':True,**tools,'engine':config['engine']})
    elif args.command=='preview':
        run_logged(blender_command(blender,config_path,'preview'),run_dir/'blender.log')
        write_ass(data,run_dir/'overlay.ass')
        overlay=f"setpts={data['frame_end']/data['fps']-1/data['fps']}/TB,ass=filename={filter_path(run_dir/'overlay.ass')}:fontsdir={filter_path(FONT_DIR)}"
        run_logged([tools['ffmpeg'],'-hide_banner','-y','-i',
                    run_dir/'previews'/f"frame_{data['frame_end']:04d}.png",'-vf',overlay,
                    '-frames:v','1',run_dir/'preview.png'],run_dir/'preview_overlay.log')
    else:
        run_logged(blender_command(blender,config_path,'render'),run_dir/'blender.log')
        check_frames(run_dir,data['frame_end'])
        write_ass(data,run_dir/'overlay.ass')
        run_logged(video_command(tools['ffmpeg'],run_dir,data,
                                 args.music.resolve() if args.music else None,
                                 args.sfx.resolve() if args.sfx else None),run_dir/'ffmpeg.log')
        probe=json.loads(subprocess.check_output([tools['ffprobe'],'-v','error','-count_frames',
                         '-show_streams','-show_format','-of','json',str(run_dir/'final_video.mp4')]))
        write_json(run_dir/'ffprobe.json',probe)
        report=validate_probe(probe,data,width,height,bool(args.music or args.sfx))
        write_json(run_dir/'verification.json',report)
        run_logged(poster_command(tools['ffmpeg'],run_dir/'final_video.mp4',run_dir/'preview.png',data['frame_end']),run_dir/'poster.log')
    write_json(args.output.resolve()/f'latest_{args.command}.json',{'run_dir':str(run_dir)})
    print(f'Completed: {run_dir}',flush=True)
    return 0


if __name__=='__main__':
    if hasattr(sys.stdout,'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8',errors='replace')
    try:
        sys.exit(main())
    except (ValueError,RuntimeError,AssertionError,OSError,subprocess.SubprocessError) as exc:
        print(f'ERROR: {exc}',file=sys.stderr)
        sys.exit(1)
