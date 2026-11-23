import unittest
from generator.local_profiles import generate,mynumber_check_digit,mynumber_valid,luhn_valid,PREFECTURES,validate_contacts
from generator.qwen import validate_profile

class LocalProfileTests(unittest.TestCase):
    def test_checksum_known_vectors(self):
        self.assertEqual(mynumber_check_digit('12345678901'),8)
        self.assertTrue(mynumber_valid('123456789018'))
        self.assertFalse(mynumber_valid('123456789019'))
        self.assertTrue(luhn_valid('4111111111111111'))
        self.assertFalse(luhn_valid('4111111111111112'))

    def test_numeric_generation_and_geographic_labels(self):
        used={key:set() for key in ('personal_number','payment_number','bank_account_number')}
        seen=set()
        for i in range(10000):
            p=generate({'person_id':f'test_{i}','age':30},20261124,used)
            self.assertEqual(len(p['personal_number']),12)
            self.assertEqual(len(p['payment_number']),16)
            self.assertEqual(len(p['bank_account_number']),7)
            self.assertFalse(mynumber_valid(p['personal_number']))
            self.assertFalse(luhn_valid(p['payment_number']))
            self.assertNotIn('架空',p['address'])
            self.assertTrue(p['address'].startswith(PREFECTURES))
            self.assertEqual(p['bank_routing_id'],'TEST')
            validate_profile(p,policy='real-prefecture')
            validate_contacts(p)
            seen.add(p['personal_number'])
        self.assertEqual(len(seen),10000)
        self.assertTrue(all(len(values)==10000 for values in used.values()))

    def test_reused_qwen_name_and_determinism(self):
        person={'person_id':'test_1','age':7,'name_cache':{'name':'佐藤 陽子','name_kana':'サトウ ヨウコ'}}
        first=generate(person,123)
        self.assertEqual(first,generate(person,123))
        self.assertEqual(first['name'],person['name_cache']['name'])
        self.assertEqual(first['occupation'],'小学生')
        self.assertEqual(first['employer'],'')
        self.assertEqual(first['workplace_address'],'')

    def test_designed_character_names_and_contacts(self):
        for presentation,expected in [('man',range(20)),('woman',range(20,40))]:
            p=generate({'person_id':presentation,'age':40,'portrait_spec':{'presentation':presentation}},20261124)
            validate_contacts(p)
            from generator.local_profiles import GIVEN_NAMES
            self.assertIn(p['name'].split()[1],{GIVEN_NAMES[i][0] for i in expected})

if __name__=='__main__':
    unittest.main()
