from __future__ import annotations
import json,os,re,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
BASE_HOME=Path(os.environ.get('ALISA_HOME',Path(os.environ.get('LOCALAPPDATA',Path.home()/'AppData/Local'))/'AlisaVoice/state' if os.name=='nt' else Path.home()/'.local/state/alisa-voice'))
DEVICE=os.environ.get('ALISA_NATIVE_DEVICE','default')
if DEVICE!='default' and not re.fullmatch('[0-9a-f]{32}',DEVICE):raise ValueError('Некорректный профиль колонки')
HOME=BASE_HOME if DEVICE=='default' else BASE_HOME/'devices'/DEVICE
MODES=('native','bridge')
STYLES=('rainbow','red','blue','green','purple','white','pulse-red','pulse-blue','pulse-green','pulse-purple','pulse-white','off')
STYLE_NAMES={'rainbow':'Радуга','red':'Красный','blue':'Синий','green':'Зелёный','purple':'Фиолетовый','white':'Белый','off':'Выключена'}
LED_SCOPES=('speaking','active')
LED_SCOPE_NAMES={'speaking':'Только во время ответа','active':'Во время ответа и прослушивания'}
VOICES=('breeze','cove','ember','fathom','glimmer','juniper','maple','orbit','vale')
# One-shot question phrases. Every variant is the same action 5; the question
# follows the phrase. Kept as a list so adding a variant needs no new key.
DEFAULT_ASK_PHRASES=('спроси у чата','спроси нейросеть','спроси чатик','спроси у нейросети',
                     'спроси чат','спроси у джипити','спроси чатджипити','спроси у чатджипити')
DEFAULT_PHRASES={'open':'открой чат','close':'закрой чат','new':'создай новый чат','previous':'открой предыдущий чат',
                 'ask':list(DEFAULT_ASK_PHRASES)}
# Action 5 is a prefix: the rest of the utterance is the question.
PHRASE_ORDER=(('open',1),('new',2),('close',3),('previous',4),('ask',5))
ASK_KEY='ask'
MAX_ASK_PHRASES=16

def write_private(path,value):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True,mode=0o700)
    if os.name=='nt':
        from .windows import private_directory
        private_directory(path.parent)
    data=(json.dumps(value,ensure_ascii=False,indent=2)+'\n').encode() if not isinstance(value,bytes) else value
    fd,name=tempfile.mkstemp(prefix='.'+path.name,dir=path.parent)
    try:
        if hasattr(os,'fchmod'):os.fchmod(fd,0o600)
        with os.fdopen(fd,'wb') as f:f.write(data);f.flush();os.fsync(f.fileno())
        os.replace(name,path)
    finally:
        if os.path.exists(name):os.unlink(name)

def defaults(mode):
    if mode not in MODES:raise ValueError('Выберите native или bridge')
    return {'version':1,'mode':mode,'host':'','user':'root','port':2222,'identity':None,
        'autostart':False,'led':'rainbow','led_scope':'speaking','listen_led':False,'disable_stun':False,'display':'eyes','mic_gain':1.0,
        'phrases':{key:(list(value) if isinstance(value,list) else value) for key,value in DEFAULT_PHRASES.items()},'installed':False,
        'vpn':{'enabled':False,'autostart':False,'required':False}}

def normalize_phrase(value):
    value=value.lower().replace('ё','е')
    value=re.sub(r'[^a-zа-я0-9]+',' ',value).strip()
    if value.startswith('алиса '):value=value[6:]
    value=value.removesuffix(' пожалуйста').strip()
    if value=='алиса':raise ValueError('Укажите слова после обращения Алиса')
    if not value or len(value.encode())>200:raise ValueError('Фраза должна содержать от 1 до 200 байт текста')
    return value

def phrase_list(value):
    """A single phrase stays a string; the ask action keeps a list."""
    if isinstance(value,list):return [item for item in value if isinstance(item,str)]
    return [value] if isinstance(value,str) else []

def parse_phrase_list(text):
    return [part.strip() for part in re.split(r'[,;\n]+',text) if part.strip()]

def migrate_ask_phrases(phrases):
    """Accept the first one-shot config (ask/ask_gpt/ask_chatgpt) and older
    files without any ask phrase."""
    raw=phrases.get('ask')
    legacy=[phrases.pop(key) for key in ('ask_gpt','ask_chatgpt') if isinstance(phrases.get(key),str)]
    if isinstance(raw,list):
        merged=list(raw)
    else:
        # Defaults first so a migrated file keeps a stable, documented order.
        merged=list(DEFAULT_ASK_PHRASES)+([raw] if isinstance(raw,str) else [])+legacy
    others={normalize_phrase(value) for key,value in phrases.items()
            if key!=ASK_KEY and isinstance(value,str)}
    result=[]
    for text in merged:
        try:normalized=normalize_phrase(text)
        except (ValueError,TypeError):continue
        if normalized not in result and normalized not in others:result.append(normalized)
    phrases[ASK_KEY]=result[:MAX_ASK_PHRASES]

def load(mode):
    p=HOME/mode/'config.json'
    if not p.exists():return defaults(mode)
    value=json.loads(p.read_text(encoding='utf-8'));value.setdefault('listen_led',False);value.setdefault('led_scope','speaking')
    phrases=value.get('phrases')
    if not isinstance(phrases,dict):phrases=value['phrases']={}
    for key,text in DEFAULT_PHRASES.items():
        if isinstance(text,list):continue
        # Never shadow a phrase the user already assigned to another action.
        if key not in phrases and text not in phrases.values():phrases[key]=text
    migrate_ask_phrases(phrases)
    validate(value);return value

def save(value):
    validate(value);write_private(HOME/value['mode']/'config.json',value)

def command_file(phrases):
    values={}
    for key,value in (phrases or {}).items():
        values[key]=[normalize_phrase(text) for text in phrase_list(value)]
    flat=[text for texts in values.values() for text in texts]
    if len(set(flat))!=len(flat):raise ValueError('Фразы действий должны отличаться')
    return ''.join(f'{number}\t{text}\n' for key,number in PHRASE_ORDER
                   for text in values.get(key,[])[:MAX_ASK_PHRASES]).encode()

def validate(value):
    if 'password' in value:raise ValueError('Пароль SSH не сохраняется в настройках')
    if value.get('ssh_auth') not in (None,'password','empty-password'):raise ValueError('Неизвестный способ входа SSH')
    if value.get('mode') not in MODES:raise ValueError('Неизвестный режим')
    host=value.get('host','')
    if not isinstance(host,str) or not host or host.startswith('-') or re.search(r'\s|[\x00-\x1f]',host):raise ValueError('Некорректный SSH-адрес')
    if value.get('port') is not None and (not isinstance(value['port'],int) or not 1<=value['port']<=65535):raise ValueError('Некорректный SSH-порт')
    if value.get('user') and not re.fullmatch('[a-zA-Z0-9_-]+',value['user']):raise ValueError('Некорректный SSH-пользователь')
    if value.get('led') not in STYLES:raise ValueError('Неизвестный цвет/анимация')
    if value.get('led_scope','speaking') not in LED_SCOPES:raise ValueError('Неизвестный режим подсветки')
    if not isinstance(value.get('listen_led',False),bool):raise ValueError('Подсветка в паузах должна быть включена или выключена')
    if not isinstance(value.get('disable_stun',False),bool):raise ValueError('Отключение STUN должно быть включено или выключено')
    gain=value.get('mic_gain',1.0)
    if isinstance(gain,bool) or not isinstance(gain,(int,float)) or not 1.0<=float(gain)<=16.0:raise ValueError('Усиление микрофона должно быть от 1 до 16')
    if not isinstance(value.get('midi_matrix',False),bool):raise ValueError('Матрица Миди должна быть включена или выключена')
    if not isinstance(value.get('midi_eyes',False),bool):raise ValueError('Глаза Миди должны быть включены или выключены')
    if not isinstance(value.get('midi_fire',False),bool):raise ValueError('Пламя Миди должно быть включено или выключено')
    if value.get('display','eyes') not in ('eyes','clock'):raise ValueError('Неизвестный режим дисплея')
    command_file(value['phrases'])
