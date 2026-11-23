import unittest
from unittest.mock import patch
import numpy as np
from generator.face_similarity import FaceDiversity,candidate_spec

class SimilarityTests(unittest.TestCase):
    def test_hard_retry_keeps_youth_and_elderly_capture_constraints(self):
        for age in (8,15,16,18,25,79,80,89):
            base={'capture_style':'diverse-v3','photo_age':age,'age':age,'presentation':'woman',
                  'appearance':'short hair','finish':{'delivery_size':240}}
            for seed in range(20):
                p=candidate_spec(base,20,seed)
                self.assertLessEqual(p['photo_age'],age)
                self.assertEqual(p['age'],age)
                self.assertEqual(p['finish'],base['finish'])
                if 16<=age<=19:self.assertGreaterEqual(p['photo_age'],16)
                if age>=80:self.assertGreaterEqual(p['photo_age'],80)
                if age<16:self.assertLessEqual(age-p['photo_age'],1)
                self.assertEqual(p['years_before_reference'],age-p['photo_age'])

    def test_morphology_retry_preserves_age_and_finishing(self):
        base={'capture_style':'diverse-v3','photo_age':16,'age':18,'presentation':'woman',
              'appearance':'tied-back hair','finish':{'delivery_size':240,'delivery_jpeg_quality':30}}
        candidate=candidate_spec(base,2,123)
        self.assertEqual(candidate['photo_age'],16)
        self.assertEqual(candidate['presentation'],'woman')
        self.assertEqual(candidate['finish'],base['finish'])
        self.assertEqual(candidate,candidate_spec(base,2,123))
        self.assertNotEqual(candidate,candidate_spec(base,2,124))
        self.assertNotIn('nose',base)

    def test_duplicate_and_missing_faces_rejected_distinct_face_accepted(self):
        gate=FaceDiversity.__new__(FaceDiversity)
        gate.threshold=.65
        gate.ids=[]
        gate.vectors=[]
        gate.add('accepted_synthetic',np.array([1,0,0],dtype=np.float32))
        with patch.object(gate,'feature',return_value=np.array([1,0,0],dtype=np.float32)):
            decision,_=gate.assess('unused')
            self.assertFalse(decision['accepted'])
            self.assertEqual(decision['nearest_person_id'],'accepted_synthetic')
        with patch.object(gate,'feature',return_value=np.array([0,1,0],dtype=np.float32)):
            decision,_=gate.assess('unused')
            self.assertTrue(decision['accepted'])
        with patch.object(gate,'feature',return_value=None):
            decision,_=gate.assess('unused')
            self.assertFalse(decision['accepted'])

if __name__=='__main__': unittest.main()
