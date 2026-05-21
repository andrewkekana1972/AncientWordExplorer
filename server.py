"""
Ancient Word Explorer - Flask Backend
- Hebrew words, transliterations, Bantu matches come from YOUR dictionary
- Claude only provides ancient letter meanings and composite meaning
- Verse text comes from bible-api (via browser) or KJV cache
"""

import os, json, re, urllib.request, urllib.error, threading, time
from flask import Flask, request, jsonify, send_from_directory

app = Flask(__name__, static_folder='.')

# ── Load full dictionary from GitHub ─────────────────────────────────────────
GITHUB_CSV_URL = os.environ.get(
    'BANTU_CSV_URL',
    'https://raw.githubusercontent.com/andrewkekana1972/ancientwordexplorer/main/bantu_dictionary_HNumbers.csv'
)

def load_dictionary(url):
    print('Loading dictionary from:', url)
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'AncientWordExplorer/1.0'})
        with urllib.request.urlopen(req, timeout=30) as r:
            raw = r.read().decode('utf-8')

        # Build two lookups:
        # DICT_FULL: H-number -> {transliteration, hebrew_chars, meanings, bantu}
        # BANTU_DB:  H-number -> [{word, language, meaning}]  (for frontend)
        dict_full = {}
        bantu_db = {}

        for line in raw.splitlines():
            parts = line.split(',')
            if len(parts) < 9:
                continue
            hnum        = parts[0].strip().strip('"')
            #translit    = parts[2].strip().strip('"')
            heb_chars   = parts[8].strip().strip('"')
            letter_grp  = parts[4].strip().strip('"')
            meaning     = parts[5].strip().strip('"')
            bantu_word  = parts[6].strip().strip('"')
            language    = parts[7].strip().strip('"')

            if not hnum or not hnum.startswith('H'):
                continue

            # Initialise entry
            if hnum not in dict_full:
                dict_full[hnum] = {
                    'strongs': hnum,
                    'transliteration': translit,
                    'hebrew_chars': heb_chars,
                    'letter_group': letter_grp,
                    'meanings': [],
                    'bantu': []
                }
            if hnum not in bantu_db:
                bantu_db[hnum] = []

            if language in ('Hebrew', 'Aramaic', 'Greek', 'language'):
                # Hebrew rows give additional English meanings
                if meaning and meaning not in dict_full[hnum]['meanings']:
                    dict_full[hnum]['meanings'].append(meaning)
            else:
                # Bantu rows
                if bantu_word and bantu_word != 'nan':
                    entry = {'word': bantu_word, 'language': language, 'meaning': meaning,
                             'transliteration': translit}
                    dict_full[hnum]['bantu'].append(entry)
                    bantu_db[hnum].append(entry)

        print('Loaded {} H-numbers ({} with Bantu matches)'.format(
            len(dict_full), sum(1 for v in dict_full.values() if v['bantu'])))
        return dict_full, bantu_db

    except Exception as e:
        print('ERROR loading dictionary:', e)
        return {}, {}

DICT_FULL, BANTU_DB = load_dictionary(GITHUB_CSV_URL)

# ── Result cache ──────────────────────────────────────────────────────────────
CACHE = {}

# ── Load pre-computed Bible cache from GitHub ─────────────────────────────────
BIBLE_CACHE_URL = os.environ.get(
    'BIBLE_CACHE_URL',
    'https://raw.githubusercontent.com/andrewkekana1972/ancientwordexplorer/main/bible_cache.json'
)

def load_bible_cache(url):
    print('Loading Bible cache from:', url)
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'AncientWordExplorer/1.0'})
        with urllib.request.urlopen(req, timeout=30) as r:
            data = json.loads(r.read().decode('utf-8'))
        print('Bible cache loaded: {} verses'.format(len(data)))
        return data
    except Exception as e:
        print('Bible cache not found:', e)
        return {}

CACHE.update(load_bible_cache(BIBLE_CACHE_URL))

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
                    word['strongs'] = correct_h
    return result

def normalise_hnum(h):
    """Strip leading zeros: H0430 -> H430"""
    if not h:
        return h
    return re.sub(r'^H0+', 'H', h.strip().upper())

def enrich_from_dictionary(result):
    """Replace Claude's Hebrew data with accurate data from our dictionary."""
    for verse in result.get('verses', []):
        for word in verse.get('words', []):
            hnum = normalise_hnum(word.get('strongs', ''))
            if not hnum:
                continue
            entry = DICT_FULL.get(hnum)
            if not entry:
                continue
            # Override with our accurate data
            word['strongs'] = hnum
            if entry.get('transliteration'):
                word['hebrew_transliteration'] = entry['transliteration']
            if entry.get('hebrew_chars'):
                word['hebrew_word'] = entry['hebrew_chars']
            if entry.get('meanings'):
                word['english_meaning'] = ', '.join(entry['meanings'][:5])
    return result

# ── Claude prompt — ONLY asks for H-numbers and letter meanings ───────────────
PROMPT = """You are a scholar of ancient Hebrew and the Ancient Hebrew Lexicon of the Bible by Jeff Benner.

Analyse this Bible verse: "{verse}"
KJV text: "{verse_text}"

Your task:
1. Identify 5-8 key Hebrew words in this verse
2. For each word provide the correct Strong's H-number
3. For each word break it into constituent Hebrew letters with their ancient pictographic meanings from Jeff Benner's Ancient Hebrew Lexicon
4. Provide a composite meaning from the letter pictographs

You do NOT need to provide the Hebrew characters, transliteration or English meaning - those come from our dictionary.
Return ONLY raw JSON, no markdown:
{{"verses":[{{"reference":"{verse}","text":"{verse_text}","words":[{{"strongs":"H0000","hebrew_letters":[{{"letter":"Name","hebrew_char":"char","ancient_meaning":"Benner pictograph meaning"}}],"composite_meaning":"combined pictographic meaning"}}]}}]}}"""

PROMPT_NO_TEXT = """You are a scholar of ancient Hebrew and the Ancient Hebrew Lexicon of the Bible by Jeff Benner.

Analyse this Bible verse: "{verse}"
Provide the complete KJV text.

Your task:
1. Identify 5-8 key Hebrew words in this verse
2. For each word provide the correct Strong's H-number
3. For each word break it into constituent Hebrew letters with their ancient pictographic meanings from Jeff Benner's Ancient Hebrew Lexicon
4. Provide a composite meaning from the letter pictographs

Return ONLY raw JSON, no markdown:
{{"verses":[{{"reference":"{verse}","text":"COMPLETE KJV TEXT","words":[{{"strongs":"H0000","hebrew_letters":[{{"letter":"Name","hebrew_char":"char","ancient_meaning":"Benner pictograph meaning"}}],"composite_meaning":"combined pictographic meaning"}}]}}]}}"""


def api_call(messages, max_tokens=3000):
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


def clean_json(raw):
    raw = raw.strip()
    if raw.startswith('```'):
        raw = '\n'.join(raw.split('\n')[1:])
    if raw.endswith('```'):
        raw = raw[:-3].strip()
    raw = raw.replace('\u2018', "'").replace('\u2019', "'")
    raw = raw.replace('\u201c', '"').replace('\u201d', '"')
    raw = raw.replace('\u2014', '-').replace('\u2013', '-')
    start = raw.find('{')
    end = raw.rfind('}')
    if start != -1 and end != -1:
        raw = raw[start:end+1]
    return raw


def repair_json(bad):
    try:
        fixed = api_call([{'role': 'user', 'content': 'Fix this JSON and return ONLY valid JSON:\n\n' + bad[:3000]}])
        return json.loads(clean_json(fixed))
    except:
        raise Exception('Could not parse response. Please try again.')


def call_claude(verse, verse_text=''):
    if verse_text:
        safe = verse_text.replace('"', "'")
        prompt = PROMPT.format(verse=verse, verse_text=safe)
    else:
        prompt = PROMPT_NO_TEXT.format(verse=verse)
    raw = api_call([{'role': 'user', 'content': prompt}])
    raw = clean_json(raw)
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return repair_json(raw)


def prewarm_cache():
    def warm():
        time.sleep(3)
        popular = [
            'Genesis 1:1', 'John 1:1', 'Psalm 23:1', 'Exodus 3:14',
            'Isaiah 40:31', 'Deuteronomy 33:29', 'John 3:16',
            'Psalm 23:4', 'Proverbs 3:5', 'Romans 8:28',
            'Philippians 4:13', 'Hebrews 11:1', 'Jeremiah 29:11',
            'Isaiah 53:5', 'Psalm 91:1',
        ]
        for verse in popular:
            key = verse.lower().strip()
            if key not in CACHE:
                try:
                    print('Pre-warming:', verse)
                    verse_text = lookup_verse(verse)
                    result = call_claude(verse, verse_text)
                    if verse_text and result.get('verses'):
                        result['verses'][0]['text'] = verse_text
                    result = correct_strongs(result, verse)
                    result = enrich_from_dictionary(result)
                    CACHE[key] = result
                    print('Pre-warmed:', verse)
                    time.sleep(1)
                except Exception as e:
                    print('Pre-warm failed for', verse, ':', e)
    threading.Thread(target=warm, daemon=True).start()

prewarm_cache()


@app.route('/')
def index():
    return send_from_directory('.', 'ancient_word_explorer.html')


@app.route('/bantu-db')
def bantu_db():
    """Serve Bantu-only lookup to frontend for instant H-number matching."""
    return jsonify(BANTU_DB)


@app.route('/analyse', methods=['POST'])
def analyse():
    body = request.json or {}
    verse = body.get('verse', '').strip()
    verse_text_from_client = body.get('verse_text', '').strip()
    if not verse:
        return jsonify({'error': 'No verse provided'}), 400

    cache_key = verse.lower().strip()
    #if cache_key in CACHE:
    #    print('Cache hit:', verse)
    #    return jsonify(CACHE[cache_key])

    try:
        verse_text = lookup_verse(verse) or verse_text_from_client
        result = call_claude(verse, verse_text)

        # Force accurate verse text
        if verse_text and result.get('verses'):
            result['verses'][0]['text'] = verse_text

        # Fix any wrong Strong's numbers
        result = correct_strongs(result, verse)

        # Enrich with accurate data from YOUR dictionary
        result = enrich_from_dictionary(result)

        CACHE[cache_key] = result
        return jsonify(result)

    except urllib.error.HTTPError as e:
        return jsonify({'error': 'API error ' + str(e.code) + ': ' + e.read().decode()}), 500
    except Exception as e:
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    print('\n' + '='*55)
    print('  Ancient Word Explorer')
    print('  Dictionary: {} H-numbers loaded'.format(len(DICT_FULL)))
    print('  Bantu entries: {}'.format(sum(len(v) for v in BANTU_DB.values())))
    print('  Model: claude-haiku (letter meanings only)')
    print('='*55)
    key = os.environ.get('ANTHROPIC_API_KEY', '')
    print('  API key:', ('found (' + key[:12] + '...)') if key else 'NOT SET')
    print('  Open: http://localhost:' + str(port))
    print('='*55 + '\n')
    app.run(debug=False, host='0.0.0.0', port=port)
