# dictionary_app.py
import csv
import streamlit as st
from collections import defaultdict
import streamlit as st

def search_strongs(h):
    st.write("Searching:", h)
# =========================
# 1. READ URL PARAMS (AWE → HB)
# =========================
# 1. URL PARAMS
params = st.query_params
strongs = params.get("strongs")

if isinstance(strongs, list):
    strongs = strongs[0]

# 2. STORE TRIGGER
if strongs:
    st.session_state["pending_strongs"] = strongs

# 3. YOUR FUNCTION
def search_strongs(h):
    st.write("Searching:", h)
    # your real logic

# 4. AUTO EXECUTE ONCE
if "pending_strongs" in st.session_state:
    search_strongs(st.session_state["pending_strongs"])
    del st.session_state["pending_strongs"]

# ---------------- CONFIG ----------------
CSV_FILE = "bantu_dictionary_HNumbers.csv" # Path to the CSV file
IMAGE_BASE_URL = "https://raw.githubusercontent.com/andrewkekana1972/ahlb_images/main"

# ---------------- PICTOGRAPHS_MEANINGS ----------------
PICTOGRAPHS_MEANINGS = {
    "א": ["head of an ox - first, leader, strength"], # aleph
    "ב": ["tent - house, family, inside"], # bet
    "ג": ["foot - gather, lift, walk"], # gimel
    "ה": ["man with hands raised - wonder, behold, reveal"], # hey
    "ח": ["wall - outside, protection, secular"],  # chet
    "ט": ["basket - contain, store, clay"], # thete
    "י": ["hand and arm - work, lift, power, make, throw"], # yad
    "ש": ["two front teeth - sharp, press, two, again"],   # shin
    "כ": ["open palm - subdue, bend, curve, tame"],  # kaf
    "ל": ["shepherd's staff - toward, authority, tie, bind"], # lamed
    "מ": ["water - might, unknown, liquid, question"], # mem
    "נ": ["sprouting seed - continuity, heir, son, generation, offspring"], # nun
    "ס": ["thornbush - pierce, sharp, shield, protect"], # samekh
    "ד": ["door - dangle, movement, poor, weak"],  # dalet
    "ז": ["mattock - plow, harvest, food, cut"],  # zayin
    "פ": ["open mouth - speak, blow, scatter"],  # peh
    "ר": ["head of man - authority, top, beginning, head, man"],  # resh
    "ע": ["eye - see, understand, knowledge, watching"],  # ayin
    "צ": ["man lying on side - side, hunt, chasing"], # tsade
    "ק": ["sun on horizon - circle, time, revolution, condense"],  # qof
    "ו": ["tent peg - connect, hook, and"],  # waw
    "ת": ["a mark - mark, sign, signature, agreement"], # tav
}

# ---------------- ALTERNATIVE SOUNDS ----------------
ALT_SOUNDS = {
    "א": ["n"], # aleph
    "ח": ["hl", "kh", "kg", "s", "tsh", "ch", "g", "h"],  # chet
    "ש": ["gc", "x" ,"c"],   # shin
    "כ": ["kh", "b"],  # kaf
    "ד": ["tl", "l", "r"],  # dalet
    "ז": ["tsh"],  # zayin
    "פ": ["f"],  # peh
    "ר": ["l", "d"],  # resh
    "ע": ["g", "ts", "y"],  # ayin
    "ק": ["g", "kh"],  # qof
    "ו": ["w", "o"],  # waw
    "ה": ["hl", "kg", "kh", "g"], # hey
    "ב": ["kh"],  # bet
}

# ---------------- LOAD DICTIONARY ----------------
def load_dictionary():
    data = []
    with open(CSV_FILE, "r", encoding="utf-8") as f:
        reader = csv.reader(f)
        for row in reader:
            if len(row) >= 9:
                data.append({
                    "ahlb": row[1].strip(),
                    "root": row[2].strip(),
                    "letters": row[3].strip(),
                    "hebrew": row[4].strip(),
                    "english": row[5].strip(),
                    "strongs": row[0].strip(),
                    "bantu_word": row[6].strip(),
                    "dialect": row[7].strip(),
                    "hebrew_full": row[8].strip(),
                })
    return data

# ---------------- GROUP BY ROOT ----------------
def group_by_root(results):
    grouped = defaultdict(lambda: {
        "ahlb": None,
        "hebrew": None,
        "hebrew_full": None,
        "letters": None,
        "english": set(),
        "strongs": set(),
        "bantu": []
    })
    for row in results:
        root = row["root"]
        grouped[root]["ahlb"] = row["ahlb"]
        grouped[root]["hebrew"] = row["hebrew"]
        grouped[root]["hebrew_full"] = row["hebrew_full"]
        grouped[root]["letters"] = row["letters"]
        grouped[root]["english"].add(row["english"])
        grouped[root]["strongs"].add(row["strongs"])
        grouped[root]["bantu"].append(f"{row['bantu_word']} ({row['dialect']})")
    return grouped

# ---------------- SEARCH FUNCTION (Exact Match Only) ----------------
def search_dictionary(query, dictionary):
    query_lower = query.lower().strip()
    results = []

    for row in dictionary:
        if (
            query_lower == row["english"].lower()
            or query_lower == row["bantu_word"].lower()
            or query_lower == row["root"].lower()
        ):
            results.append(row)

        # ✅ Only return all with same H# if user *typed an H number directly*
        elif query_lower.startswith("h") and query_lower == row["strongs"].lower():
            results.append(row)

    return results

# ---------------- GROUP BY ROOT (Merge All Dialects) ----------------
def group_by_root(results):
    grouped = {}
    for row in results:
        root = row["root"]

        if root not in grouped:
            grouped[root] = {
                "ahlb": row["ahlb"],
                "hebrew": row["hebrew"],
                "hebrew_full": row["hebrew_full"],
                "letters": row["letters"],
                "english": set(),
                "strongs": set(),
                "bantu": set()
            }

        # ✅ Merge all dialects and meanings for this root
        grouped[root]["english"].add(row["english"])
        grouped[root]["strongs"].add(row["strongs"])
        grouped[root]["bantu"].add(f"{row['bantu_word']} ({row['dialect']})")

    return grouped


# ---------------- ALT SOUND FUNCTION ----------------
def get_alt_spellings(hebrew_letters):
    alternatives = []
    for char in hebrew_letters:
        if char in ALT_SOUNDS:
            alternatives.append(f"{char} → {', '.join(ALT_SOUNDS[char])}")
    return alternatives

# ---------------- PICTOGRAPH MEANINGS FUNCTION ----------------
def get_pictograph_meanings(hebrew_word):
    meanings = []
    for char in hebrew_word:
        if char in PICTOGRAPHS_MEANINGS:
            meanings.append(f"{char} – {', '.join(PICTOGRAPHS_MEANINGS[char])}")
    return meanings

# ---------------- IMAGE URL ----------------
def get_image_url(ahlb_number):
    return f"{IMAGE_BASE_URL}/{ahlb_number}.png"

# ---------------- STREAMLIT APP ----------------
st.set_page_config(page_title="Hebrew–Bantu Dictionary", layout="wide")
# --- Force consistent light theme (fix dark mobile background) ---
st.markdown("""
<style>
/* General app background */
html, body, [class*="stAppViewContainer"], [class*="stMainBlockContainer"] {
    background-color: #ffffff !important;
    color: #3D230A !important;
}

/* Input text box (search) */
input, textarea {
    background-color: #fff !important;
    color: #3D230A !important;
    border: 1px solid #dcdcdc !important;
    border-radius: 6px !important;
}

/* Buttons (like Refresh Random Words) */
button[kind="secondary"], button[kind="primary"], .stButton>button {
    background-color: #f8f9fa !important;
    color: #3D230A !important;
    border: 1px solid #d0d7df !important;
    border-radius: 8px !important;
}

/* Hover effect for buttons */
.stButton>button:hover {
    background-color: #FFD700 !important;
    color: #000 !important;
}

/* Input label and small spacing fixes */
label, .stTextInput>div>div>input {
    color: #3D230A !important;
}

</style>
""", unsafe_allow_html=True)

st.markdown("""
    <style>
    div[data-testid="stTextInput"] label {
        margin-bottom: -10px !important;
    }
    </style>
    """, unsafe_allow_html=True)

st.markdown("""
    <style>
    body, .stApp {
        background-color: white !important;
        color: black !important;
    }
    </style>
    """,
    unsafe_allow_html=True
)
# 3 columns: Title | Donations | Placeholder
col1, col2, col3 = st.columns([3,2,1])

with col1:
    st.markdown(
        """
        <p style='color:#3D230A; font-size:24px; font-weight:bold; margin:0;'>
            📖 Hebrew-Bantu Dictionary
        </p>
        </br>
        """,
        unsafe_allow_html=True
    )
    st.markdown(
        """
        <p style='color:#3D230A; font-size:18px; font-weight:bold; margin:0;'>
            This work aims to achieve three objectives:
        </p>
        """,
        unsafe_allow_html=True
    )
    st.markdown(
        """
        <p style='color:#3D230A; font-size:16px;margin:0;'>
            1. Demonstrate the oneness of Bantu languages.
        </p>
        </br>
        <p style='color:#3D230A; font-size:16px; margin:0;'>
            2. Trace the etymology of Bantu languages to the Hebrew alephbet.
        </p>
        </br>
        <p style='color:#3D230A; font-size:16px; margin:0;'>
            3. Help the Bible student understand the original text.
        </p>
        </br>
        """,
        unsafe_allow_html=True
    )
    print()
    st.markdown(
    """
    <p style='color:#3D23OA; font-size:18px; font-weight:bold; margin-top:8px;'>
        All praise to the Most High YHWH!
    </p>

    """,
    unsafe_allow_html=True  
    )
    
with col2:
    st.markdown(
        """
        <p style='color:#3D230A; font-size:16px; font-weight:bold; margin:0;'>
            Please support our work through the following platforms:
        </p>
        <div style="text-align:left;">
            <a href="https://www.buymeacoffee.com/AKTheHebrew" target="_blank">
                <img src="https://cdn.buymeacoffee.com/buttons/v2/default-yellow.png"
                     alt="Buy Me A Coffee"
                     style="width:140px; height:auto;">
            </a>
        </div>
        """,
        unsafe_allow_html=True
    )
    st.markdown(
    """
    <p style='color:#3D23OA; font-size:16px; font-weight:bold; margin-top:8px;'>
        Your support keeps this project alive. Thank you! 🙏
    </p>

    <div style='
        background-color:#f8f9fa;
        border-left: 4px solid #FFDD00;
        padding:10px 15px;
        border-radius:8px;
        margin-top:10px;
        text-align:center;
    '>
        “For then I will restore to the people a pure language, that they all may call on the name of YHWH, to serve Him with one accord. From beyond the rivers of Ethiopia My worshipers, the daughter of My dispersed ones, shall bring My offering.”
    </p>
    <p style='color:#1261A0; font-size:16px; font-style:italic; text-align:center; margin-top:8px;'>
        Zephaniah 3:9-10
    </p>
    """,
    unsafe_allow_html=True
)


dictionary = load_dictionary()
# replace the old line `query = st.text_input("Enter a word ...")` with this:
from urllib.parse import urlparse, parse_qs

# --- Capture ?query= from URL if user clicks a random word ---
query_params = st.query_params
query_from_url = query_params.get("query", [None])
if isinstance(query_from_url, list):
    query_from_url = query_from_url[0]
query_from_url = query_from_url or ""

# --- Preserve value in session ---
if query_from_url and query_from_url != st.session_state.get("query"):
    st.session_state["query"] = query_from_url
    st.rerun()

# --- Main text input ---
st.markdown(
    "<p style='font-size:16px; font-weight:bold; color:#3D230A;'>"
    "Enter a word (<span style='color:#0b66c3;'>English</span>, "
    "<span style='color:#0b66c3;'>Bantu</span>, or "
    "<span style='color:#0b66c3;'>Strong’s H#</span>):"
    "</p>",
    unsafe_allow_html=True
)
query = st.text_input("", value=st.session_state.get("query", ""))


# keep using `query` afterwards as before

if query:
    results = search_dictionary(query, dictionary)

    if results:
        grouped = group_by_root(results)
        st.success(f"Found {len(results)} matches across {len(grouped)} Hebrew roots for **{query}**:")

        # ✅ Toggle to show/hide related words
        show_related = st.toggle("🔁 Show related words (same Strong’s number)", value=True)

        for root, info in grouped.items():
            image_url = get_image_url(info['ahlb'])
            col1, col2 = st.columns([4, 1])

            with col1:
                # --- MAIN ENTRY ---
                st.markdown(f"<h3 style='color:#FFD700; font-size:20px;'>🟨 Main Entry</h3>", unsafe_allow_html=True)
                st.markdown(f"<div style='font-size:18px'><b>Root:</b> <span style='color:blue'>{root}</span></div>", unsafe_allow_html=True)
                st.markdown(f"<div style='font-size:18px'><b>AHLB:</b> {info['ahlb']}</div>", unsafe_allow_html=True)
                st.markdown(
                    f"<div style='font-size:20px'><b>Hebrew:</b> "
                    f"<span style='color:orange; font-size:24px;'>{info['hebrew']}</span> "
                    f"({info['letters']})</div>",
                    unsafe_allow_html=True
                )
                st.markdown(f"<div style='font-size:18px'><b>Full Hebrew word:</b> {info['hebrew_full']}</div>", unsafe_allow_html=True)
                st.markdown(f"<div style='font-size:18px'><b>English:</b> {', '.join(info['english'])}</div>", unsafe_allow_html=True)

                strongs_links = ', '.join([
                    f'<a href="https://www.blueletterbible.org/lexicon/{s}/kjv/" target="_blank">{s}</a>'
                    for s in info['strongs']
                ])
                st.markdown(
                    f"<div style='font-size:18px'><b>Strong’s:</b> {strongs_links}</div>",
                    unsafe_allow_html=True
                )

                st.markdown(
                    f"<div style='font-size:20px'><b>Bantu words:</b> {', '.join(sorted(info['bantu']))}</div>",
                    unsafe_allow_html=True
                )

                # 🎨 Better formatted Alternative Sounds
                alt_spellings = get_alt_spellings(info['hebrew'])
                if alt_spellings:
                    formatted_alts = []
                    for a in alt_spellings:
                        letter, sounds = a.split(" → ")
                        formatted_alts.append(
                            f"<span style='color:orange; font-weight:bold;'>{letter}</span> → "
                            f"<span style='color:green; font-style:italic;'>{sounds}</span>"
                        )
                    st.markdown(
                        f"<div style='font-size:20px;'><b>Alternative sounds:</b> {', '.join(formatted_alts)}</div>",
                        unsafe_allow_html=True
                    )

            with col2:
                st.markdown(
                        """
                            <p style='color:#3D230A; font-size:16px; font-weight:bold; margin:0;'>
                              📖 WORD ETYMOLOGY WITH ANCIENT HEBREW:
                            </p>
                            """,
                            unsafe_allow_html=True
                        )
                try:                    
                    st.image(image_url, width=100)
                    if st.button("🔍 View full image", key=f"{info['ahlb']}_full"):
                        st.image(image_url, width=400)
                except Exception:
                    st.warning("No image found")

                pictograph_meanings = get_pictograph_meanings(info['hebrew'])
                if pictograph_meanings:
                    st.markdown(
                        f"<div style='font-size:18px;'><b>Ancient Hebrew Pictograph Meanings:</b></div>",
                        unsafe_allow_html=True
                    )
                    for meaning in pictograph_meanings:
                        st.markdown(
                            f"<div style='font-size:18px; color:#3D230A;'>{meaning}</div>",
                            unsafe_allow_html=True
                        )

            # --- RELATED WORDS SECTION (Optional) ---
            if show_related:
                related = [
                    r for r in dictionary
                    if r["strongs"] in info["strongs"]
                    and r["bantu_word"] not in [b.split(' ')[0] for b in info["bantu"]]
                ]

                if related:
                    st.markdown("<hr>", unsafe_allow_html=True)
                    st.markdown(f"<h3 style='color:#00BFFF; font-size:18px;'>🟦 Related Words (Same Strong’s)</h3>", unsafe_allow_html=True)
                    for r in related:
                        st.markdown(
                            f"<div style='font-size:18px; margin-left:20px;'>"
                            f"<b style='color:#008B8B'>{r['bantu_word']} ({r['dialect']})</b> → "
                            f"{r['english']} "
                            f"<span style='color:orange;'>[{r['hebrew']}]</span>"
                            f"</div>",
                            unsafe_allow_html=True
                        )
            st.markdown("---")
    else:
        st.error("No results found.")

import random

# ---------- DAILY SAMPLE 10 (5 English + 5 Bantu, left-aligned & styled) ----------
st.markdown(
        """
        <p style='color:#3D230A; font-size:18px; font-weight:bold; margin:0;'>
            📖 Explore sample words.
        </p>
        """,
        unsafe_allow_html=True
    )

# Split words into English-based and Bantu-based entries
english_entries = [row for row in dictionary if row.get("english") and row["english"].strip()]
bantu_entries = [row for row in dictionary if row.get("bantu_word") and row["bantu_word"].strip()]

# Pick 5 random English + 5 random Bantu
import random
if "sample_words" not in st.session_state or not st.session_state["sample_words"]:
    st.session_state["sample_words"] = random.sample(english_entries, min(5, len(english_entries))) + \
                                       random.sample(bantu_entries, min(5, len(bantu_entries)))

# Refresh button
if st.button("🔄 Refresh Random Words"):
    st.session_state["sample_words"] = random.sample(english_entries, min(5, len(english_entries))) + \
                                       random.sample(bantu_entries, min(5, len(bantu_entries)))

# CSS for chip-like buttons (compact, left aligned)
st.markdown(
    """
    <style>
    .chip {
      display:inline-block;
      padding:5px 10px;
      border-radius:10px;
      background:#f8f9fa;
      border:1px solid #ccc;
      color:#0b66c3;
      text-decoration:none;
      font-size:15px;
      margin:3px;
    }
    .chip:hover { background:#0b66c3; color:#fff; border-color:#094f8a; }
    .chip-container { text-align:left; margin-top:5px; }
    </style>
    """,
    unsafe_allow_html=True,
)

# Create HTML string for chips
chips_html = "<div class='chip-container'>"
for entry in st.session_state["sample_words"]:
    if entry:
        # Use English or Bantu word depending on which type
        word = entry["english"] if random.random() < 0.5 else entry["bantu_word"]
        chips_html += f"<a class='chip' href='?query={word}' target='_self'>{word}</a>"
chips_html += "</div>"

st.markdown(chips_html, unsafe_allow_html=True)