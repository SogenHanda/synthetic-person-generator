"""Compare synthetic face features only; no real-person gallery or attribute labels."""
import cv2
import copy
import random
import numpy as np
from .common import ROOT,read_json,sha256

def candidate_spec(base,attempt,seed):
    spec=copy.deepcopy(base)
    if attempt<2 or spec.get('capture_style')!='diverse-v3':
        return spec
    rng=random.Random(seed)
    spec.update({
        'face_structure':rng.choice(['round full face','long narrow face','square angular jaw','broad cheekbones, short chin','triangular face, pointed chin','oval face, prominent chin','wide jaw, narrow forehead','broad forehead, small chin']),
        'nose':rng.choice(['broad flat nose','narrow straight nose','short rounded nose','long prominent nose','small upturned nose','wide low nose']),
        'eyes':rng.choice(['narrow monolid eyes','round open eyes','small hooded eyes','wide-set eyes','close-set eyes','downturned eyes','unequal eyelid folds']),
        'mouth':rng.choice(['thin tight lips','full lips','wide mouth','small mouth','uneven lips']),
        'brows':rng.choice(['thick straight brows','sparse eyebrows','arched eyebrows','low heavy brows']),
        'accessory':rng.choice(['no glasses']*6+['wire glasses','thick glasses','rimless glasses'])})
    age=spec['photo_age']
    male=spec['presentation']=='man'
    if age>=65:
        hair=['bald head','short white hair','sparse grey hair','short wavy grey hair','short dark hair','salt-and-pepper hair'] if male else ['short white hair','wavy grey hair','short black bob','dark wavy hair','tied-back dark hair','short cropped hair']
        skin=['deep wrinkles, sun spots','dry age-spotted skin','weathered wrinkled skin','sagging mottled skin']
    else:
        hair=['buzz cut','short wavy hair','side-parted hair','shaggy short hair','slicked-back hair','uneven fringe'] if male else ['tied-back hair','short bob','long straight hair','short cropped hair','wavy shoulder-length hair','uneven bangs']
        skin=['natural freckled skin','pale natural skin','uneven natural skin'] if age<20 else ['oily acne-marked skin','dry freckled skin','tanned uneven skin','pale blemished skin'] if age<35 else ['rough sun-tanned skin','pale wrinkled skin','uneven freckled skin','dry mottled skin']
    spec['appearance']=rng.choice(hair)
    spec['skin']=rng.choice(skin)
    spec['lighting']=rng.choice(['office light','booth flash','uneven fluorescent light','direct flash'])
    spec['clothes']=rng.choice(['white shirt','school blazer','plain cardigan'] if age<20 else ['navy suit','grey jacket','plain cardigan','white shirt'] if male else ['grey jacket','dark cardigan','beige jacket','plain blouse'])
    if attempt>=8:
        spec['guidance_scale']=rng.choice([5.5,6.0])
    if attempt>=16:
        current_age=spec['age']
        minimum=6 if current_age<=15 else 16 if current_age<=19 else 80 if current_age>=80 else 18
        years=1 if current_age<=15 else 2 if current_age<=19 else 4 if current_age>=80 else 8
        spec['photo_age']=rng.randint(max(minimum,current_age-years),current_age)
        spec['years_before_reference']=current_age-spec['photo_age']
        spec['guidance_scale']=rng.choice([4.0,4.5,5.0])
    return spec

class FaceDiversity:
    def __init__(self,threshold=.5):
        cv2.setNumThreads(2)
        inventory=read_json(ROOT/'models/face_similarity/assets.json')
        for entry in inventory['assets']:
            if sha256(ROOT/entry['path'])!=entry['sha256']:
                raise ValueError('Face similarity model hash changed')
        directory=ROOT/'models/face_similarity'
        self.detector=cv2.FaceDetectorYN.create(str(directory/'face_detection_yunet_2023mar.onnx'),'',(512,512),.85,.3,5000)
        self.recognizer=cv2.FaceRecognizerSF.create(str(directory/'face_recognition_sface_2021dec.onnx'),'')
        self.threshold=threshold
        self.vectors=[]
        self.ids=[]
        self.metadata={'model':'OpenCV SFace + YuNet','repository':inventory['repository'],
                       'revision':inventory['revision'],'assets':inventory['assets'],
                       'cosine_reject_threshold':threshold,
                       'retry_strategy':'v4: resample morphology and appearance; hard retries vary plausible capture age and CFG; preserve current age, finish and profile',
                       'scope':'Synthetic portraits in this batch only. Similarity screen, not proof of separate identities.'}

    def feature(self,path):
        image=cv2.imdecode(np.fromfile(str(path),dtype=np.uint8),cv2.IMREAD_COLOR)
        image=cv2.resize(image,(512,512))
        _,faces=self.detector.detect(image)
        if faces is None or len(faces)!=1:
            return None
        aligned=self.recognizer.alignCrop(image,faces[0])
        vector=self.recognizer.feature(aligned).reshape(-1).astype(np.float32)
        return vector/np.linalg.norm(vector)

    def assess(self,path):
        vector=self.feature(path)
        if vector is None:
            return {'accepted':False,'reason':'not_exactly_one_detectable_face'},None
        if not self.vectors:
            return {'accepted':True,'max_cosine':None,'nearest_person_id':None},vector
        scores=np.asarray(self.vectors)@vector
        index=int(np.argmax(scores))
        score=float(scores[index])
        return {'accepted':score<self.threshold,'reason':'similar_face' if score>=self.threshold else 'passed',
                'max_cosine':round(score,6),'nearest_person_id':self.ids[index]},vector

    def add(self,person_id,vector):
        self.ids.append(person_id)
        self.vectors.append(vector)
