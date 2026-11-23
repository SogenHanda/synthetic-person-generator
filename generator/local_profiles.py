"""Fast fictional profiles. Geographic labels are real; no person lookup occurs."""
import hashlib
import random
import re

PREFECTURE_CITIES = [tuple(line.split()) for line in '''北海道 札幌市中央区
青森県 青森市
岩手県 盛岡市
宮城県 仙台市青葉区
秋田県 秋田市
山形県 山形市
福島県 福島市
茨城県 水戸市
栃木県 宇都宮市
群馬県 前橋市
埼玉県 さいたま市浦和区
千葉県 千葉市中央区
東京都 杉並区
神奈川県 横浜市港北区
新潟県 新潟市中央区
富山県 富山市
石川県 金沢市
福井県 福井市
山梨県 甲府市
長野県 長野市
岐阜県 岐阜市
静岡県 静岡市葵区
愛知県 名古屋市千種区
三重県 津市
滋賀県 大津市
京都府 京都市左京区
大阪府 大阪市北区
兵庫県 神戸市灘区
奈良県 奈良市
和歌山県 和歌山市
鳥取県 鳥取市
島根県 松江市
岡山県 岡山市北区
広島県 広島市西区
山口県 山口市
徳島県 徳島市
香川県 高松市
愛媛県 松山市
高知県 高知市
福岡県 福岡市中央区
佐賀県 佐賀市
長崎県 長崎市
熊本県 熊本市中央区
大分県 大分市
宮崎県 宮崎市
鹿児島県 鹿児島市
沖縄県 那覇市'''.splitlines()]
PREFECTURES = tuple(p for p,c in PREFECTURE_CITIES)
TOWNS = '青葉 若葉 松原 桜台 緑町 東町 西町 南町 北町 本町 新町 旭町 高台 花園 川原 森下 中央 泉町 日向 港町'.split()
BANKS = '東都みらい銀行 青葉中央銀行 北辰つばさ銀行 みなと光銀行 南海しずく銀行 七瀬ひかり銀行'.split()
SURNAMES = [tuple(s.split(':')) for s in '佐藤:サトウ 鈴木:スズキ 高橋:タカハシ 田中:タナカ 伊藤:イトウ 渡辺:ワタナベ 山本:ヤマモト 中村:ナカムラ 小林:コバヤシ 加藤:カトウ 吉田:ヨシダ 山田:ヤマダ 佐々木:ササキ 山口:ヤマグチ 松本:マツモト 井上:イノウエ 木村:キムラ 林:ハヤシ 清水:シミズ 山崎:ヤマザキ 森:モリ 池田:イケダ 橋本:ハシモト 阿部:アベ 石川:イシカワ 山下:ヤマシタ 中島:ナカジマ 石井:イシイ 小川:オガワ 前田:マエダ 岡田:オカダ 長谷川:ハセガワ 藤田:フジタ 後藤:ゴトウ 近藤:コンドウ 村上:ムラカミ 遠藤:エンドウ 青木:アオキ 坂本:サカモト 斎藤:サイトウ'.split()]
GIVEN_NAMES = [tuple(s.split(':')) for s in '健一:ケンイチ 和也:カズヤ 直人:ナオト 拓也:タクヤ 大輔:ダイスケ 浩二:コウジ 誠:マコト 修一:シュウイチ 明:アキラ 悠:ユウ 翔太:ショウタ 亮介:リョウスケ 智也:トモヤ 達也:タツヤ 洋平:ヨウヘイ 正樹:マサキ 翔:ショウ 翼:ツバサ 薫:カオル 司:ツカサ 美咲:ミサキ 愛:アイ 恵:メグミ 陽子:ヨウコ 由美:ユミ 真理:マリ 直子:ナオコ 香織:カオリ 優子:ユウコ 理恵:リエ 智子:トモコ 千尋:チヒロ 美穂:ミホ 彩:アヤ 玲奈:レナ 春香:ハルカ 菜々子:ナナコ 結衣:ユイ 美紀:ミキ 久美子:クミコ'.split()]
JOBS = '会社員 公務員 自営業 販売員 看護師 介護職 調理師 事務職 配送員 教員 エンジニア パート勤務 建設作業員 農業 理容師 無職'.split()

def romanize_kana(value):
    pairs={'キャ':'kya','キュ':'kyu','キョ':'kyo','シャ':'sha','シュ':'shu','ショ':'sho','チャ':'cha','チュ':'chu','チョ':'cho','ニャ':'nya','ニュ':'nyu','ニョ':'nyo','ヒャ':'hya','ヒュ':'hyu','ヒョ':'hyo','ミャ':'mya','ミュ':'myu','ミョ':'myo','リャ':'rya','リュ':'ryu','リョ':'ryo','ギャ':'gya','ギュ':'gyu','ギョ':'gyo','ジャ':'ja','ジュ':'ju','ジョ':'jo'}
    chars=dict(zip('アイウエオカキクケコサシスセソタチツテトナニヌネノハヒフヘホマミムメモヤユヨラリルレロワヲンガギグゲゴザジズゼゾダヂヅデドバビブベボパピプペポ',
                   'a i u e o ka ki ku ke ko sa shi su se so ta chi tsu te to na ni nu ne no ha hi fu he ho ma mi mu me mo ya yu yo ra ri ru re ro wa o n ga gi gu ge go za ji zu ze zo da ji zu de do ba bi bu be bo pa pi pu pe po'.split()))
    result=''
    i=0
    while i<len(value):
        if value[i:i+2] in pairs:
            result+=pairs[value[i:i+2]]; i+=2
        elif value[i]=='ッ' and i+1<len(value):
            result+=chars.get(value[i+1],'')[0:1]; i+=1
        else:
            result+=chars.get(value[i],''); i+=1
    return result or 'user'

def mynumber_check_digit(body):
    if not re.fullmatch(r'[0-9]{11}',body):
        raise ValueError('My Number body must have 11 digits')
    remainder=sum(int(d)*(i+1 if i<=6 else i-5) for i,d in enumerate(reversed(body),1))%11
    return 0 if remainder<=1 else 11-remainder

def mynumber_valid(value):
    return bool(re.fullmatch(r'[0-9]{12}',value)) and int(value[-1])==mynumber_check_digit(value[:-1])

def luhn_valid(value):
    if not re.fullmatch(r'[0-9]+',value):
        return False
    total=0
    for i,ch in enumerate(reversed(value)):
        digit=int(ch)
        if i%2:
            digit*=2
            digit-=9 if digit>9 else 0
        total+=digit
    return total%10==0

def invalid_card(rng):
    body='9900'+''.join(str(rng.randrange(10)) for _ in range(11))
    correct=next(d for d in range(10) if luhn_valid(body+str(d)))
    return body+str((correct+1)%10)

def occupation(age,rng):
    if age<6: return '未就学児'
    if age<12: return '小学生'
    if age<15: return '中学生'
    if age<18: return '高校生'
    if age<23: return rng.choice(['大学生','専門学校生','会社員','販売員'])
    if age>=65: return rng.choice(['無職','自営業','パート勤務','農業'])
    return rng.choice(JOBS)

def validate_contacts(profile):
    if not re.fullmatch(r'[a-z0-9][a-z0-9._+-]*@(gmail\.com|yahoo\.co\.jp|outlook\.jp|icloud\.com|example\.jp|example\.ne\.jp|example\.com)',profile['email']):
        raise ValueError('Malformed synthetic email address')
    if not re.fullmatch(r'(070|080|090)-[0-9]{4}-[0-9]{4}',profile['phone']):
        raise ValueError('Malformed display-only mobile number')
    if profile['employer']:
        if not profile['workplace_address'].startswith(PREFECTURES) or not re.fullmatch(r'(03|050)-[0-9]{4}-[0-9]{4}',profile['workplace_phone']):
            raise ValueError('Missing employer contact details')
    elif profile['workplace_address'] or profile['workplace_phone']:
        raise ValueError('Work contact details without an employer')

def generate(person,master_seed,used_numbers=None):
    rng=random.Random(int(hashlib.sha256(f'{master_seed}:{person["person_id"]}'.encode()).hexdigest(),16))
    cached=person.get('name_cache')
    if cached:
        name,kana=cached['name'],cached['name_kana']
        name_source=cached.get('source','reused Qwen name/readings from source batch')
    else:
        surname,surname_kana=rng.choice(SURNAMES)
        presentation=person.get('portrait_spec',{}).get('presentation')
        candidates=GIVEN_NAMES[:20] if presentation=='man' else GIVEN_NAMES[20:] if presentation=='woman' else GIVEN_NAMES
        given,given_kana=rng.choice(candidates)
        name,kana=surname+' '+given,surname_kana+' '+given_kana
        name_source='local paired name/kana dictionary'
    prefecture,city=rng.choice(PREFECTURE_CITIES)
    town=rng.choice(TOWNS)
    address=f'{prefecture}{city}{town}{rng.randint(1,7)}丁目{rng.randint(1,40)}番{rng.randint(1,30)}号'
    if rng.random()<0.35:
        address+=' '+rng.choice(['メゾン','コーポ','ハイツ','レジデンス'])+rng.choice(['青葉','桜','若葉','中央'])+f' {rng.randint(1,9)}0{rng.randint(1,9)}号室'
    used_numbers=used_numbers if used_numbers is not None else {'personal_number':set(),'payment_number':set(),'bank_account_number':set()}
    numbers={}
    for key in used_numbers:
        for _ in range(1000):
            if key=='personal_number':
                body=str(rng.randrange(10**10,10**11))
                value=body+str((mynumber_check_digit(body)+1)%10)
            elif key=='payment_number':
                value=invalid_card(rng)
            else:
                value=str(rng.randrange(10**6,10**7))
            if value not in used_numbers[key]:
                used_numbers[key].add(value)
                numbers[key]=value
                break
        else:
            raise ValueError('Number uniqueness retry exhausted')
    profile={'name':name,'name_kana':kana,'address':address,'occupation':occupation(person['age'],rng),
             'bank_name':rng.choice(BANKS),'bank_branch':rng.choice(TOWNS)+'支店','account_holder_kana':kana,
             **numbers,'bank_account_type':'普通','bank_routing_id':'TEST',
             'personal_number_checksum_valid':False,'payment_number_luhn_valid':False,
             'number_policy':'invalid-numeric-v1','address_policy':'real-prefecture-city-generated-street-v1',
             'name_source':name_source}
    parts=kana.split()
    surname_email=romanize_kana(parts[0])
    given_email=romanize_kana(parts[-1])
    local=rng.choice([f'{given_email}.{surname_email}{rng.randint(100,9999)}',f'{given_email[0]}.{surname_email}{rng.randint(100,9999)}',f'{surname_email}_{given_email}{rng.randint(100,9999)}'])
    profile['email']=local+'@'+rng.choice(['gmail.com','yahoo.co.jp','outlook.jp','icloud.com'])
    profile['phone']=rng.choice(['070','080','090'])+f'-{rng.randint(1000,9999)}-{rng.randrange(10000):04d}'
    profile['contact_policy']='synthetic-unverified-realistic-format-v1'
    profile['contact_verified']=False
    if profile['occupation'] in ('未就学児','小学生','中学生','高校生','大学生','専門学校生','無職'):
        profile.update({'employer':'','workplace_address':'','workplace_phone':''})
    else:
        stem=rng.choice(['青葉','霞野','星川','東都','朝凪','北辰','晴海','若葉','桜丘','緑葉'])
        kind=rng.choice(['システムズ','ロジスティクス','テクノサービス','フーズ','商事','ライフサポート','設備工業','デザイン'])
        profile['employer']='株式会社'+stem+kind
        job=profile['occupation']
        if job=='看護師': profile['employer']='医療法人'+stem+'会 '+stem+'総合病院'
        elif job=='介護職': profile['employer']='社会福祉法人'+stem+'会'
        elif job=='教員': profile['employer']=stem+'学園'
        elif job=='農業': profile['employer']=stem+'農園'
        elif job=='理容師': profile['employer']='ヘアーサロン'+stem
        elif job=='建設作業員': profile['employer']=stem+'建設株式会社'
        elif job=='調理師': profile['employer']='株式会社'+stem+'フーズ'
        elif job=='エンジニア': profile['employer']='株式会社'+stem+'システムズ'
        elif job=='配送員': profile['employer']='株式会社'+stem+'ロジスティクス'
        elif job=='公務員': profile['employer']=stem+'地域行政サービスセンター'
        profile['workplace_address']=prefecture+city+rng.choice(TOWNS)+f'{rng.randint(1,6)}丁目{rng.randint(1,35)}番{rng.randint(1,20)}号'
        profile['workplace_phone']=('03' if prefecture=='東京都' else '050')+f'-{rng.randint(1000,9999)}-{rng.randrange(10000):04d}'
    return profile
