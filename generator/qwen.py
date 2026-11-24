import json
import time
import requests

FIELDS = ['name','name_kana','address','occupation','bank_name','bank_branch','account_holder_kana']
PROFILE_SCHEMA = {'type':'object','properties':{key:{'type':'string','minLength':1,'maxLength':100} for key in FIELDS},'required':FIELDS,'additionalProperties':False}
for key in ('name_kana','account_holder_kana'):
    PROFILE_SCHEMA['properties'][key]['pattern']='^[ァ-ヿ 　]+$'

class QwenAdapter:
    def __init__(self, config):
        from urllib.parse import urlparse
        self.config = config
        self.endpoint = config['endpoint'].rstrip('/')
        endpoint = urlparse(self.endpoint)
        if endpoint.scheme!='http' or endpoint.hostname not in ('127.0.0.1','localhost','::1'):
            raise ValueError('Qwen endpoint must be a local HTTP server')
        response = requests.get(self.endpoint+'/v1/models',timeout=15)
        response.raise_for_status()
        self.served_model = response.json()['data'][0]['id']
        if config['model'].lower() not in self.served_model.lower():
            raise ValueError(f'Wrong local model: {self.served_model}')

    def generate(self, spec, seed):
        import jsonschema
        system = ('あなたはテスト用の架空人物データを生成します。実在人物の情報は参照しません。'
                  '自然な日本語の氏名と読み、架空住所、職業、架空銀行と支店、口座名義カナを作成します。'
                  '住所は必ず「架空県」から始め、町名も創作してください。'
                  'bank_nameは必ず「架空」から始めてください。'
                  'bank_nameは「架空花月銀行」のような銀行名だけとし、必ず「銀行」で終えて支店名を含めないでください。'
                  'bank_branchは「花月支店」のような支店名だけとし、銀行名を含めず必ず「支店」で終えてください。'
                  '人名は自然な日本の姓名とし、名字と名前の間は半角スペースを1つ入れてください。'
                  '設定にavoid_namesがあれば、それらの氏名は使用せず別の名字と名前の組み合わせを考えてください。'
                  '設定にsurname_hintがあれば、その名字を必ず使用してください。名前と読みは自分で考えてください。'
                  'カナは全角カタカナと空白だけを使ってください。'
                  '銀行口座名義は氏名の読みと一致させてください。'
                  '数値の個人識別番号、カード番号、電話番号は出力しません。'
                  '指定されたJSONオブジェクトだけを返してください。/no_think')
        user = f'架空人物の設定: {json.dumps(spec,ensure_ascii=False)}。氏名と職業に多様性を持たせ、設定年齢に合う名前を作成してください。/no_think'
        # Native completion avoids a llama.cpp b12651 chat-parser/JSON-grammar
        # conflict with the Qwen3 non-thinking prefill. The model's ChatML and
        # explicit closed thinking prefix are preserved; schema sampling remains.
        prompt=f'<|im_start|>system\n{system}<|im_end|>\n<|im_start|>user\n{user}<|im_end|>\n<|im_start|>assistant\n'
        if 'qwen3' in self.config['model'].lower():
            prompt+='<think>\n\n</think>\n\n'
        payload = {'prompt':prompt,'temperature':self.config['temperature'],'top_p':self.config['top_p'],
                   'top_k':20,'min_p':0.0,'n_predict':self.config['max_tokens'],'seed':seed,
                   'stop':['<|im_end|>'],'json_schema':PROFILE_SCHEMA,'cache_prompt':True}
        error = None
        for attempt in range(3):
            payload['seed'] = seed+attempt
            start = time.perf_counter()
            try:
                response = requests.post(self.endpoint+'/completion',json=payload,timeout=600)
                response.raise_for_status()
                result = response.json()
                if result.get('truncated') or result.get('stop_type')=='limit' or not result.get('stop'):
                    raise ValueError('Incomplete LLM response')
                profile = json.loads(result['content'])
                jsonschema.validate(profile,PROFILE_SCHEMA)
                validate_profile(profile)
                if spec.get('surname_hint') and not profile['name'].startswith(spec['surname_hint']+' '):
                    raise ValueError('Surname hint was not followed')
                return profile,{'seconds':round(time.perf_counter()-start,4),'seed':seed+attempt,'attempt':attempt+1,
                                'usage':{'prompt_tokens':result.get('tokens_evaluated'),'completion_tokens':result.get('tokens_predicted')},
                                'timings':result.get('timings'),'served_model':self.served_model,
                                'protocol':'llama.cpp /completion, Qwen ChatML with non-thinking prefill'}
            except (ValueError,requests.RequestException,jsonschema.ValidationError) as e:
                error = e
                print(f'  profile retry {attempt+1}: {type(e).__name__}: {str(e)[:180]}',flush=True)
        raise RuntimeError(f'Qwen profile failed: {error}')

def validate_profile(profile,policy='fictional-prefix'):
    import re
    if policy=='real-prefecture':
        from .local_profiles import PREFECTURES
        if not profile['address'].startswith(PREFECTURES) or any('架空' in profile[k] for k in ('address','bank_name','bank_branch')):
            raise ValueError('Expected real prefecture label and generated street/bank labels')
    elif not profile['address'].startswith('架空県') or not profile['bank_name'].startswith('架空'):
        raise ValueError('Fictional address/bank prefix missing')
    if not profile['bank_name'].endswith('銀行') or '支店' in profile['bank_name'] or not profile['bank_branch'].endswith('支店') or '銀行' in profile['bank_branch']:
        raise ValueError('Bank and branch names must be separate')
    if not re.fullmatch(r'[\u30a0-\u30ff 　]+',profile['name_kana']):
        raise ValueError('name_kana must be katakana')
    if profile['account_holder_kana'].replace(' ','').replace('　','') != profile['name_kana'].replace(' ','').replace('　',''):
        raise ValueError('Account holder reading does not match name_kana')
    if any(any(ord(c)<32 for c in value) for value in profile.values() if isinstance(value,str)):
        raise ValueError('Control character in profile')
