"""
Ancient Word Explorer - Flask Backend
No extra packages needed beyond flask and gunicorn.
Locally: python3 server.py
Render:  gunicorn server:app
"""

import os, json, re, urllib.request, urllib.error
from flask import Flask, request, jsonify, send_from_directory

app = Flask(__name__, static_folder='.')

# ── KJV verse lookup (server-side, guaranteed accurate) ──────────────────────
KJV = {
    "genesis 1:1": "In the beginning God created the heaven and the earth.",
    "genesis 1:2": "And the earth was without form, and void; and darkness was upon the face of the deep. And the Spirit of God moved upon the face of the waters.",
    "genesis 1:3": "And God said, Let there be light: and there was light.",
    "exodus 3:14": "And God said unto Moses, I AM THAT I AM: and he said, Thus shalt thou say unto the children of Israel, I AM hath sent me unto you.",
    "exodus 20:3": "Thou shalt have no other gods before me.",
    "deuteronomy 33:29": "Happy art thou, O Israel: who is like unto thee, O people saved by the LORD, the shield of thy help, and who is the sword of thy excellency! and thine enemies shall be found liars unto thee; and thou shalt tread upon their high places.",
    "psalm 23:1": "The LORD is my shepherd; I shall not want.",
    "psalm 23:2": "He maketh me to lie down in green pastures: he leadeth me beside the still waters.",
    "psalm 23:3": "He restoreth my soul: he leadeth me in the paths of righteousness for his name's sake.",
    "psalm 23:4": "Yea, though I walk through the valley of the shadow of death, I will fear no evil: for thou art with me; thy rod and thy staff they comfort me.",
    "psalm 23:5": "Thou preparest a table before me in the presence of mine enemies: thou anointest my head with oil; my cup runneth over.",
    "psalm 23:6": "Surely goodness and mercy shall follow me all the days of my life: and I will dwell in the house of the LORD for ever.",
    "psalm 91:1": "He that dwelleth in the secret place of the most High shall abide under the shadow of the Almighty.",
    "psalm 91:2": "I will say of the LORD, He is my refuge and my fortress: my God; in him will I trust.",
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

# ── Verified Strong's numbers for key verses ─────────────────────────────────
# Format: { "verse_key": { "english_phrase": "Hxxxx" } }
# Used to cross-check and correct Claude's Strong's assignments
VERIFIED_STRONGS = {
    "deuteronomy 33:29": {
        "happy": "H835",
        "blessed": "H835",
        "israel": "H3478",
        "saved": "H3467",
        "salvation": "H3468",
        "lord": "H3068",
        "shield": "H4043",
        "help": "H5828",
        "sword": "H2719",
        "excellency": "H1346",
        "enemies": "H341",
        "liars": "H3584",
        "found liars": "H3584",
        "tread": "H1869",
        "high places": "H1116",
    },
    "genesis 1:1": {
        "beginning": "H7225",
        "created": "H1254",
        "god": "H430",
        "heaven": "H8064",
        "earth": "H776",
    },
    "exodus 3:14": {
        "i am": "H1961",
    },
    "psalm 23:1": {
        "lord": "H3068",
        "shepherd": "H7462",
        "want": "H2637",
    },
    "isaiah 40:31": {
        "wait": "H6960",
        "lord": "H3068",
        "renew": "H2498",
        "strength": "H3581",
        "mount up": "H5927",
        "eagles": "H5404",
        "run": "H7323",
        "weary": "H3021",
        "walk": "H1980",
        "faint": "H3286",
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
        'isa': 'isaiah', 'jer': 'jeremiah',
        'jn': 'john', 'joh': 'john',
        'rom': 'romans', 'phil': 'philippians', 'php': 'philippians',
        'heb': 'hebrews', 'rev': 'revelation',
    }
    for short, full in abbrev.items():
        if key.startswith(short + ' ') or key.startswith(short + '.'):
            expanded = full + key[len(short):]
            if expanded in KJV:
                return KJV[expanded]
    return ''


def correct_strongs(result, verse_key):
    """Cross-check Claude's Strong's numbers against our verified table."""
    verified = VERIFIED_STRONGS.get(verse_key.lower().strip(), {})
    if not verified:
        return result
    for verse in result.get('verses', []):
        for word in verse.get('words', []):
            meaning = (word.get('english_meaning') or '').lower()
            translit = (word.get('hebrew_transliteration') or '').lower()
            for phrase, correct_h in verified.items():
                if phrase in meaning or phrase in translit:
                    if word.get('strongs') != correct_h:
                        print(f'Correcting Strong\'s: {word.get("strongs")} -> {correct_h} for "{phrase}"')
                        word['strongs'] = correct_h
    return result


PROMPT = """You are a scholar of ancient Hebrew, Biblical linguistics, and Bantu languages.

Verse: "{verse}"
KJV text: "{verse_text}"

CRITICAL INSTRUCTIONS for Strong's numbers:
- You MUST use the correct Strong's number for each specific Hebrew word as it appears in THIS verse
- Do NOT guess or approximate - use the exact lexical form and its correct H-number
- For example in Deuteronomy 33:29: "found liars" is H3584 (kachash), NOT H8267 (sheqer)
- Double-check each Strong's number before including it

Task:
- Select 5-8 key Hebrew words from this verse
- For each word provide the CORRECT Strong's H-number for that exact word
- For each word find a related Bantu language word (cognate, phonetic, or thematic)
- Break each word into letters with ancient pictographic meanings from Jeff Benner's Ancient Hebrew Lexicon
- Return ONLY raw JSON, no markdown, no backticks

Use ONLY straight ASCII double quotes. No smart quotes. No special dashes.

{{"verses":[{{"reference":"{verse}","text":"{verse_text}","words":[{{"hebrew_word":"chars","hebrew_transliteration":"english","hebrew_root":"root","strongs":"H0000","english_meaning":"meaning","hebrew_letters":[{{"letter":"Name","hebrew_char":"char","ancient_meaning":"Benner meaning"}}],"composite_meaning":"combined meaning"}}]}}]}}"""

PROMPT_NO_TEXT = """You are a scholar of ancient Hebrew, Biblical linguistics, and Bantu languages.

Verse: "{verse}"

CRITICAL INSTRUCTIONS for Strong's numbers:
- You MUST use the correct Strong's number for each specific Hebrew word as it appears in THIS verse
- Do NOT guess or approximate - use the exact lexical form and its correct H-number
- Double-check each Strong's number before including it

Task:
- Provide the COMPLETE full KJV verse text - every single word, never truncate
- Select 5-8 key Hebrew words from this verse
- For each word provide the CORRECT Strong's H-number
- For each word find a related Bantu language word (cognate, phonetic, or thematic)
- Break each word into letters with ancient pictographic meanings from Jeff Benner's Ancient Hebrew Lexicon
- Return ONLY raw JSON, no markdown, no backticks

Use ONLY straight ASCII double quotes. No smart quotes.

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
        lines = raw.split('\n')
        raw = '\n'.join(lines[1:])
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
    fix_prompt = (
        'The following JSON is invalid. Fix it and return ONLY valid JSON, '
        'nothing else, no markdown:\n\n' + bad_json[:3000]
    )
    try:
        fixed = api_call([{'role': 'user', 'content': fix_prompt}], max_tokens=6000)
        fixed = clean_json_text(fixed)
        return json.loads(fixed)
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
    except json.JSONDecodeError as e:
        print('Initial parse failed:', e)
        return repair_json(raw)


@app.route('/')
def index():
    return send_from_directory('.', 'ancient_word_explorer.html')


@app.route('/analyse', methods=['POST'])
def analyse():
    body = request.json or {}
    verse = body.get('verse', '').strip()
    verse_text_from_client = body.get('verse_text', '').strip()
    if not verse:
        return jsonify({'error': 'No verse provided'}), 400
    try:
        # 1. Server-side KJV lookup (guaranteed accurate)
        verse_text = lookup_verse(verse)
        if not verse_text:
            verse_text = verse_text_from_client

        result = call_claude(verse, verse_text)

        # 2. Force accurate verse text into result
        if verse_text and result.get('verses'):
            result['verses'][0]['text'] = verse_text

        # 3. Correct any wrong Strong's numbers
        result = correct_strongs(result, verse)

        return jsonify(result)
    except urllib.error.HTTPError as e:
        return jsonify({'error': 'API error ' + str(e.code) + ': ' + e.read().decode()}), 500
    except Exception as e:
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    print('\n' + '='*50)
    print('  Ancient Word Explorer')
    print('  KJV lookup: ' + str(len(KJV)) + ' verses cached')
    print('  Verified Strong\'s: ' + str(len(VERIFIED_STRONGS)) + ' verses')
    print('  Model: claude-haiku (fast!)')
    print('='*50)
    key = os.environ.get('ANTHROPIC_API_KEY', '')
    if key:
        print('  API key: found (' + key[:12] + '...)')
    else:
        print('  !! API key NOT SET. Run:')
        print('     export ANTHROPIC_API_KEY=sk-ant-...')
    print('  Open: http://localhost:' + str(port))
    print('='*50 + '\n')
    app.run(debug=False, host='0.0.0.0', port=port)
