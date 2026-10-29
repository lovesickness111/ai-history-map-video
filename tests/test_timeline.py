import copy
import json
from pathlib import Path
import tempfile
import unittest

from history_pipeline.timeline import ROOT,load_timeline,validate,town_instances,year_at,frame_seconds,event_at
from history_pipeline.postprocess import write_ass,check_frames,validate_probe,video_command,ass_time


class TimelineTests(unittest.TestCase):
    def setUp(self):
        self.data=load_timeline(ROOT/'data'/'hanoi_illustrative_timeline.json')

    def test_expected_demo_and_reproducibility(self):
        self.assertEqual(len(self.data['instances']),482)
        self.assertEqual(town_instances(1049),town_instances(1049))
        self.assertNotEqual(town_instances(1049),town_instances(1050))
        for seed in range(10):
            data=copy.deepcopy(self.data)
            data['instances']=data['instances'][:2]+town_instances(seed,layout='district')
            validate(data)

    def test_years_and_video_frame_origin(self):
        for frame,year in ((1,1010),(121,1049),(661,1812),(841,1900),(900,1900)):
            self.assertEqual(year_at(self.data,frame),year)
        self.assertEqual(frame_seconds(121,30),4)
        self.assertEqual(frame_seconds(661,30),22)
        self.assertIn('1049',event_at(self.data,121))
        self.assertNotIn('1049',event_at(self.data,120))
        with self.assertRaises(ValueError):
            year_at(self.data,901)

    def test_reject_duplicate_unknown_scale_and_invalid_frames(self):
        for key,value in (('id','flag_tower'),('model_id','unknown'),('scale',[1,0,1]),
                          ('end_frame',901),('start_frame',True),('position',[0,float('nan'),0]),
                          ('params',{'size':-1}),('params',{'surprise':1})):
            with self.subTest(key=key,value=value):
                data=copy.deepcopy(self.data)
                data['instances'][0][key]=value
                with self.assertRaises(ValueError):
                    validate(data)

    def test_reject_overlapping_house(self):
        data=copy.deepcopy(self.data)
        data['instances'][2]['position']=list(data['instances'][3]['position'])
        with self.assertRaisesRegex(ValueError,'overlaps'):
            validate(data)

    def test_reject_road_water_and_pond_placement(self):
        for pos in ((3.6,0,.025),(27,4,.025),(-12,7,.025)):
            with self.subTest(pos=pos):
                data=copy.deepcopy(self.data)
                data['instances'][2]['position']=list(pos)
                with self.assertRaises(ValueError):
                    validate(data)

    def test_reject_bad_anchors_and_overlapping_events(self):
        for edit in ('first','last','reverse','event'):
            data=copy.deepcopy(self.data)
            if edit=='first': data['anchors'][0]['frame']=2
            if edit=='last': data['anchors'][-1]['frame']=899
            if edit=='reverse': data['anchors'][2]['year']=1048
            if edit=='event': data['events'][1]['frame']=120
            with self.assertRaises(ValueError):
                validate(data)

    def test_reject_malformed_shapes_and_too_short_construction(self):
        for key,value in (('anchors',[None,None]),('instances',[]),('instances',[None]),
                          ('events',[None]),('events',{}),('schema_version',True),('fps',1000)):
            with self.subTest(key=key,value=value):
                data=copy.deepcopy(self.data)
                data[key]=value
                with self.assertRaises(ValueError): validate(data)
        self.data['instances'][0]['end_frame']=122
        with self.assertRaisesRegex(ValueError,'two frames'):
            validate(self.data)

    def test_subtitle_frame_alignment_and_vietnamese(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'overlay.ass'
            write_ass(self.data,path)
            text=path.read_text(encoding='utf-8-sig')
            self.assertIn('0:00:04.00,0:00:04.03,Year',text)
            self.assertIn('NĂM 1049',text)
            self.assertIn('0:00:22.00,0:00:22.03,Year',text)
            self.assertIn('Chùa Một Cột',text)
            for line in text.splitlines():
                if line.startswith('Style: '):
                    fields=line.split(': ',1)[1].split(',')
                    self.assertEqual(fields[18],'7')
            # Floor timestamps so a subtitle never starts after its actual video frame.
            self.assertEqual(ass_time(2/30),'0:00:00.06')

    def test_missing_empty_and_unexpected_frames(self):
        with tempfile.TemporaryDirectory() as folder:
            frames=Path(folder)/'frames'
            frames.mkdir()
            with self.assertRaises(ValueError): check_frames(folder,2)
            for n in (1,2): (frames/f'frame_{n:04d}.png').write_bytes(b'png')
            check_frames(folder,2)
            (frames/'frame_0003.png').write_bytes(b'png')
            with self.assertRaises(ValueError): check_frames(folder,2)

    def test_audio_timing_and_shell_free_arguments(self):
        with tempfile.TemporaryDirectory(prefix='history space ') as folder:
            cmd=video_command('ffmpeg',folder,self.data,music=Path('music space.wav'),sfx=Path('sfx.wav'))
            self.assertIn('music space.wav',cmd)
            self.assertIn('final_video.mp4',cmd[-1])
            graph=(Path(folder)/'ffmpeg_filters.txt').read_text()
            self.assertIn('adelay=4000:all=1',graph)
            self.assertIn('adelay=22000:all=1',graph)
            self.assertIn('atrim=duration=30.0',graph)

    def test_probe_rejects_wrong_dimensions_or_audio(self):
        probe={'streams':[{'codec_type':'video','width':1920,'height':1080,'avg_frame_rate':'30/1',
                           'nb_read_frames':'900','codec_name':'h264','pix_fmt':'yuv420p'}],
               'format':{'duration':'30.000'}}
        self.assertTrue(validate_probe(probe,self.data,1920,1080,False)['passed'])
        with self.assertRaises(AssertionError): validate_probe(probe,self.data,1280,720,False)
        with self.assertRaises(AssertionError): validate_probe(probe,self.data,1920,1080,True)


if __name__=='__main__':
    unittest.main()
