"""Real FFmpeg encode/probe checks, including Unicode, apostrophes and audio."""
import copy
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

from history_pipeline.timeline import ROOT,load_timeline
from history_pipeline.postprocess import write_ass,video_command,validate_probe,check_frames,FONT_DIR,poster_command


@unittest.skipUnless(shutil.which('ffmpeg') and shutil.which('ffprobe') and (FONT_DIR/'BeVietnamPro-Bold.ttf').exists(),
                     'FFmpeg, ffprobe and bundled font required')
class MediaIntegrationTests(unittest.TestCase):
    def test_real_encode_with_optional_audio_and_windows_paths(self):
        with tempfile.TemporaryDirectory(prefix="Hà Nội's demo ") as folder:
            root=Path(folder)
            (root/'frames').mkdir()
            def run(command):
                result=subprocess.run(command,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
                self.assertEqual(result.returncode,0,result.stdout.decode('utf-8','replace')[-4000:])
                return result
            run(['ffmpeg','-v','error','-f','lavfi','-i','color=c=0xc5cec3:s=128x72:r=30',
                 '-frames:v','30',str(root/'frames'/'frame_%04d.png')])
            for name in ('music','sfx'):
                run(['ffmpeg','-v','error','-f','lavfi','-i','sine=frequency=440:duration=0.2',str(root/f'{name}.wav')])
            data=copy.deepcopy(load_timeline(ROOT/'data'/'hanoi_illustrative_timeline.json'))
            data['frame_end']=30
            data['anchors']=[{'frame':1,'year':1049},{'frame':30,'year':1812}]
            data['events']=[{'frame':1,'end_frame':30,'text':"Chùa Một Cột: mái ngói, phố cổ {test} \\N"}]
            data['instances']=data['instances'][:2]
            for i,item in enumerate(data['instances']):
                item['start_frame']=1+i*15
                item['end_frame']=item['start_frame']+10
            check_frames(root,30)
            write_ass(data,root/'overlay.ass')
            for music,sfx in ((None,None),(root/'music.wav',None),(None,root/'sfx.wav'),(root/'music.wav',root/'sfx.wav')):
                with self.subTest(music=bool(music),sfx=bool(sfx)):
                    run(video_command('ffmpeg',root,data,music,sfx))
                    result=run(['ffprobe','-v','error','-count_frames','-show_streams','-show_format','-of','json',str(root/'final_video.mp4')])
                    probe=json.loads(result.stdout)
                    validate_probe(probe,data,128,72,bool(music or sfx))
            run(poster_command('ffmpeg',root/'final_video.mp4',root/'preview.png',30))
            self.assertGreater((root/'preview.png').stat().st_size,0)


if __name__=='__main__':
    unittest.main()
