import unittest
import numpy as np
from PIL import Image
from generator.photo_finish import finish

class PhotoFinishTests(unittest.TestCase):
    def test_framing_moves_marker_without_edge_fill(self):
        # An asymmetric marker verifies the crop direction and actual positioning.
        pixels=np.full((200,200,3),100,dtype=np.uint8)
        pixels[95:105,95:105]=255
        source=Image.fromarray(pixels)
        settings={'effective_size':200,'frame_crop':[0,.1,.8,.9],'scan_angle':0,
                  'grain':0,'chroma_noise':0,'softness':0,'saturation':1,
                  'contrast':1,'camera_jpeg_enabled':False}
        result=np.asarray(finish(source,settings,200,1))
        y,x=np.where(result[:,:,0]>220)
        self.assertGreater(x.mean(),120)
        self.assertAlmostEqual(y.mean(),99.5,delta=1)
        self.assertTrue(np.all(result[:5]==100))
        np.testing.assert_array_equal(np.asarray(source),pixels)
        with self.assertRaises(ValueError):
            finish(source,{**settings,'frame_crop':[-.1,0,1,1]},200,1)

    def test_repeatable_and_source_preserved(self):
        yy,xx=np.mgrid[:512,:512]
        source=Image.fromarray(np.stack([xx//2,yy//2,(xx+yy)//4],axis=-1).astype('uint8'))
        before=np.asarray(source).copy()
        settings={'effective_size':256,'softness':0.25,'grain':2.1,'color_shift':[3,1,-3],
                  'camera_jpeg_quality':65,'scan_angle':0.5,'vignette':0.02}
        a=finish(source,settings,384,123)
        b=finish(source,settings,384,123)
        c=finish(source,settings,384,124)
        self.assertEqual(a.size,(384,384))
        self.assertEqual(a.mode,'RGB')
        np.testing.assert_array_equal(np.asarray(a),np.asarray(b))
        np.testing.assert_array_equal(np.asarray(source),before)
        self.assertFalse(np.array_equal(np.asarray(a),np.asarray(c)))
        self.assertFalse(np.array_equal(np.asarray(a),np.asarray(source.resize((384,384)))))

if __name__=='__main__':
    unittest.main()
