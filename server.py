"""
Ancient Word Explorer - Flask Backend
Loads Bantu dictionary from GitHub at startup.
No extra packages needed beyond flask and gunicorn.
Locally: python3 server.py
Render:  gunicorn server:app
"""

import os, json, re, urllib.request, urllib.error
from flask import Flask, request, jsonify, send_from_directory

app = Flask(__name__, static_folder='.')

# ── Load Bantu dictionary from GitHub ────────────────────────────────────────
# Update this URL to match your GitHub username and repo
GITHUB_CSV_URL = os.environ.get(
    'BANTU_CSV_URL',
    'https://raw.githubusercontent.com/andrewkekana1972/ancientwordexplorer/main/bantu_dictionary.csv'
)

def load_bantu_db(url):
    """Fetch and parse the Bantu dictionary CSV from GitHub."""
    print('Loading Bantu dictionary from:', url)
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'AncientWordExplorer/1.0'})
        with urllib.request.urlopen(req, timeout=30) as r:
            raw = r.read().decode('utf-8')

        lookup = {}
        for line in raw.splitlines():
            parts = line.split(',')
            if len(parts) < 8:
                continue
            strongs_id = parts[5].strip().strip('"')
            bantu_word = parts[6].strip().strip('"')
            language   = parts[7].strip().strip('"')
            meaning    = parts[4].strip().strip('"')
            translit   = parts[1].strip().strip('"')

            if not strongs_id or not bantu_word or not language:
                continue
            if language in ('Hebrew', 'Aramaic', 'Greek', 'language'):
                continue
            if not strongs_id.startswith('H'):
                continue

            if strongs_id not in lookup:
                lookup[strongs_id] = []
            lookup[strongs_id].append({
                'word': bantu_word,
                'language': language,
                'meaning': meaning,
                'transliteration': translit
            })

        print(f'Loaded {len(lookup)} H-numbers, {sum(len(v) for v in lookup.values())} entries')
        return lookup

    except Exception as e:
        print('ERROR loading Bantu dictionary:', e)
        return {}

# Load at startup
BANTU_DB = load_bantu_db(GITHUB_CSV_URL)

# ── KJV verse lookup ──────────────────────────────────────────────────────────
KJV = {
    "genesis 1:1": "In the beginning God created the heaven and the earth.",
    "genesis 1:2": "And the earth was without form, and void; and darkness was upon the face of the deep. And the Spirit of God moved upon the face of the waters.",
    "genesis 1:3": "And God said, Let there be light: and there was light.",
    "exodus 3:14": "And God said unto Moses, I AM THAT I AM: and he said, Thus shalt thou say unto the children of Israel, I AM hath sent me unto you.",
    "deuteronomy 33:29": "Happy art thou, O Israel: who is like unto thee, O people saved by the LORD, the shield of thy help, and who is the sword of thy excellency! and thine enemies shall be found liars unto thee; and thou shalt tread upon their high places.",
    "psalm 23:1": "The LORD is my shepherd; I shall not want.",
    "psalm 23:2": "He maketh me to lie down in green pastures: he leadeth me beside the still waters.",
    "psalm 23:3": "He restoreth my soul: he leadeth me in the paths of righteousness for his name's sake.",
    "psalm 23:4": "Yea, though I walk through the valley of the shadow of death, I will fear no evil: for thou art with me; thy rod and thy staff they comfort me.",
    "psalm 23:5": "Thou preparest a table before me in the presence of mine enemies: thou anointest my head with oil; my cup runneth over.",
    "psalm 23:6": "Surely goodness and mercy shall follow me all the days of my life: and I will dwell in the house of the LORD for ever.",
    "psalm 91:1": "He that dwelleth in the secret place of the most High shall abide under the shadow of the Almighty.",
    "psalm 119:105": "Thy word is a lamp unto my feet, and a light unto my path.",
    "proverbs 3:5": "Trust in the LORD with all thine heart; and lean not unto thine own understanding.",
    "proverbs 3:6": "In all thy ways acknowledge him, and he shall direct thy paths.",
    "isaiah 40:31": "But they that wait upon the LORD shall renew their strength; they shall mount up with wings as eagles; they shall run, and not be weary; and they shall walk, and not faint.",
    "isaiah 53:5": "But he was wounded for our transgressions, he was bruised for our iniquities: the chastisement of our peace was upon him; and with his stripes we are healed.",
    "jeremiah 29:11": "For I know the thoughts that I think toward you, saith the LORD, thoughts of peace, and not of evil, to give you an expected end.",
    "john 1:1": "In the beginning was the Word, and the Word was with God, and the Word was God.",
    "john 3:16": "For God so loved the world, that he gave his only begotten Son, that whosoever believeth in him should not perish, but have everlasting life.",
    "romans 8:28": "And we know that all things work together for good to them that love God, to them who are the called according to his purpose.",
    "philippians 4:13": "I can do all things through Christ which strengtheneth me.",
    "hebrews 11:1": "Now faith is the substance of things hoped for, the evidence of things not seen.",
    "revelation 1:8": "I am Alpha and Omega, the beginning and the ending, saith the Lord, which is, and which was, and which is to come, the Almighty.",
}

VERIFIED_STRONGS = {
    "deuteronomy 33:29": {
        "happy": "H835", "israel": "H3478", "saved": "H3467",
        "lord": "H3068", "shield": "H4043", "help": "H5828",
        "sword": "H2719", "excellency": "H1346", "enemies": "H341",
        "liars": "H3584", "found liars": "H3584",
        "tread": "H1869", "high places": "H1116",
    },
    "genesis 1:1": {
        "beginning": "H7225", "created": "H1254",
        "god": "H430", "heaven": "H8064", "earth": "H776",
    },
    "isaiah 40:31": {
        "wait": "H6960", "lord": "H3068", "renew": "H2498",
        "strength": "H3581", "eagles": "H5404",
        "run": "H7323", "walk": "H1980",
    },
}


def lookup_verse(reference):
    key = reference.lower().strip()
    if key in KJV:
        return KJV[key]
    abbrev = {
        'gen': 'genesis', 'exo': 'exodus', 'ex': 'exodus',
        'deut': 'deuteronomy', 'deu': 'deuteronomy', 'dt': 'deuteronomy',
        'ps': 'psalm', 'psa': 'psalm', 'prov': 'proverbs', 'pro': 'proverbs',
        'isa': 'isaiah', 'jer': 'jeremiah', 'jn': 'john', 'joh': 'john',
        'rom': 'romans', 'phil': 'philippians', 'heb': 'hebrews', 'rev': 'revelation',
    }
    for short, full in abbrev.items():
        if key.startswith(short + ' ') or key.startswith(short + '.'):
            expanded = full + key[len(short):]
            if expanded in KJV:
                return KJV[expanded]
    return ''


def correct_strongs(result, verse_key):
    verified = VERIFIED_STRONGS.get(verse_key.lower().strip(), {})
    if not verified:
        return result
    for verse in result.get('verses', []):
        for word in verse.get('words', []):
            meaning = (word.get('english_meaning') or '').lower()
            for phrase, correct_h in verified.items():
                if phrase in meaning and word.get('strongs') != correct_h:
                    print(f'Correcting: {word.get("strongs")} -> {correct_h} for "{phrase}"')
                    word['strongs'] = correct_h
    return result


PROMPT = """You are a scholar of ancient Hebrew, Biblical linguistics, and Bantu languages.

Verse: "{verse}"
KJV text: "{verse_text}"

CRITICAL: Use the CORRECT Strong's H-number for each specific Hebrew word in this verse.
Example: in Deuteronomy 33:29 "found liars" is H3584 (kachash), NOT H8267 (sheqer).

Task:
- Select 5-8 key Hebrew words
- Correct Strong's H-number for each
- Related Bantu word (cognate, phonetic, or thematic)
- Letters with ancient pictographic meanings from Jeff Benner's Ancient Hebrew Lexicon
- Return ONLY raw JSON, no markdown, no backticks
- Use only straight ASCII double quotes

{{"verses":[{{"reference":"{verse}","text":"{verse_text}","words":[{{"hebrew_word":"chars","hebrew_transliteration":"english","hebrew_root":"root","strongs":"H0000","english_meaning":"meaning","hebrew_letters":[{{"letter":"Name","hebrew_char":"char","ancient_meaning":"Benner meaning"}}],"composite_meaning":"combined meaning"}}]}}]}}"""

PROMPT_NO_TEXT = """You are a scholar of ancient Hebrew, Biblical linguistics, and Bantu languages.

Verse: "{verse}"

CRITICAL: Use the CORRECT Strong's H-number for each specific Hebrew word.
Provide the COMPLETE full KJV verse text - never truncate.

Task:
- Complete full KJV verse text
- Select 5-8 key Hebrew words
- Correct Strong's H-number for each
- Related Bantu word (cognate, phonetic, or thematic)
- Letters with ancient pictographic meanings from Jeff Benner's Ancient Hebrew Lexicon
- Return ONLY raw JSON, no markdown, no backticks
- Use only straight ASCII double quotes

{{"verses":[{{"reference":"{verse}","text":"COMPLETE VERSE TEXT","words":[{{"hebrew_word":"chars","hebrew_transliteration":"english","hebrew_root":"root","strongs":"H0000","english_meaning":"meaning","hebrew_letters":[{{"letter":"Name","hebrew_char":"char","ancient_meaning":"Benner meaning"}}],"composite_meaning":"combined meaning"}}]}}]}}"""


def api_call(messages, max_tokens=6000):
    key = os.environ.get('ANTHROPIC_API_KEY', '').strip()
    if not key:
        raise Exception('ANTHROPIC_API_KEY not set.')
    payload = json.dumps({
        'model': 'claude-haiku-4-5-20251001',
        'max_tokens': max_tokens,
        'messages': messages
    }).encode('utf-8')
    req = urllib.request.Request(
        'https://api.anthropic.com/v1/messages',
        data=payload,
        headers={
            'Content-Type': 'application/json',
            'x-api-key': key,
            'anthropic-version': '2023-06-01'
        },
        method='POST'
    )
    with urllib.request.urlopen(req, timeout=60) as r:
        body = json.loads(r.read().decode('utf-8'))
    return body['content'][0]['text']


def clean_json_text(raw):
    raw = raw.strip()
    if raw.startswith('```'):
        raw = '\n'.join(raw.split('\n')[1:])
    if raw.endswith('```'):
        raw = raw[:-3]
    raw = raw.strip()
    raw = raw.replace('\u2018', "'").replace('\u2019', "'")
    raw = raw.replace('\u201c', '"').replace('\u201d', '"')
    raw = raw.replace('\u2014', '-').replace('\u2013', '-')
    start = raw.find('{')
    end = raw.rfind('}')
    if start != -1 and end != -1:
        raw = raw[start:end+1]
    return raw


def repair_json(bad_json):
    print('Attempting JSON repair...')
    fix_prompt = 'Fix this invalid JSON and return ONLY valid JSON, nothing else:\n\n' + bad_json[:3000]
    try:
        fixed = api_call([{'role': 'user', 'content': fix_prompt}], max_tokens=6000)
        return json.loads(clean_json_text(fixed))
    except Exception as e:
        print('Repair failed:', e)
        raise Exception('Could not parse response. Please try again.')


def call_claude(verse, verse_text=''):
    if verse_text:
        safe_text = verse_text.replace('"', "'")
        prompt = PROMPT.format(verse=verse, verse_text=safe_text)
    else:
        prompt = PROMPT_NO_TEXT.format(verse=verse)
    raw = api_call([{'role': 'user', 'content': prompt}])
    raw = clean_json_text(raw)
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return repair_json(raw)


@app.route('/')
def index():
    return send_from_directory('.', 'ancient_word_explorer.html')


@app.route('/bantu-db')
def bantu_db():
    """Serve the Bantu dictionary to the frontend as JSON."""
    return jsonify(BANTU_DB)


@app.route('/analyse', methods=['POST'])
def analyse():
    body = request.json or {}
    verse = body.get('verse', '').strip()
    verse_text_from_client = body.get('verse_text', '').strip()
    if not verse:
        return jsonify({'error': 'No verse provided'}), 400
    try:
        verse_text = lookup_verse(verse) or verse_text_from_client
        result = call_claude(verse, verse_text)
        if verse_text and result.get('verses'):
            result['verses'][0]['text'] = verse_text
        result = correct_strongs(result, verse)
        return jsonify(result)
    except urllib.error.HTTPError as e:
        return jsonify({'error': 'API error ' + str(e.code) + ': ' + e.read().decode()}), 500
    except Exception as e:
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    print('\n' + '='*55)
    print('  Ancient Word Explorer')
    print(f'  Bantu DB: {sum(len(v) for v in BANTU_DB.values())} entries, {len(BANTU_DB)} H-numbers')
    print('  Model: claude-haiku (fast!)')
    print('='*55)
    key = os.environ.get('ANTHROPIC_API_KEY', '')
    print('  API key:', ('found (' + key[:12] + '...)') if key else 'NOT SET')
    print('  Open: http://localhost:' + str(port))
    print('='*55 + '\n')
    app.run(debug=False, host='0.0.0.0', port=port)
