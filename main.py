# main.py
from flask import Flask, request, jsonify
import swisseph as swe
import requests
from datetime import datetime
import pytz
from timezonefinder import TimezoneFinder
from dateutil.relativedelta import relativedelta

app = Flask(__name__)

# Use Lahiri sidereal
swe.set_sid_mode(swe.SIDM_LAHIRI)
tf = TimezoneFinder()

# --------------------------------------------
# Utility Functions
# --------------------------------------------
def geocode_place(place):
    url = "https://nominatim.openstreetmap.org/search"
    params = {"q": place, "format": "json", "limit": 1}
    headers = {"User-Agent": "JyotiPath/1.0 (nitindotnijhawan@gmail.com)"}
    resp = requests.get(url, params=params, headers=headers, timeout=15)
    resp.raise_for_status()
    data = resp.json()
    if not data:
        raise ValueError("Place not found")
    return float(data[0]["lat"]), float(data[0]["lon"]), data[0].get("display_name", place)

def tz_from_latlon(lat, lon, dt_local_naive):
    tzname = tf.timezone_at(lat=lat, lng=lon)
    if not tzname:
        tzname = tf.closest_timezone_at(lat=lat, lng=lon)
    if not tzname:
        raise ValueError("Timezone not found for this location")
    tz = pytz.timezone(tzname)
    dt_local = tz.localize(dt_local_naive)
    offset_hours = dt_local.utcoffset().total_seconds() / 3600.0
    return tzname, offset_hours, dt_local

# --------------------------------------------
# Vimshottari Dasha Calculations
# --------------------------------------------
NAK_WIDTH = 13 + 1/3
VIM_MAHAS = {
    "Ketu":7,"Venus":20,"Sun":6,"Moon":10,"Mars":7,
    "Rahu":18,"Jupiter":16,"Saturn":19,"Mercury":17
}
LORD_SEQUENCE = ["Ketu","Venus","Sun","Moon","Mars","Rahu","Jupiter","Saturn","Mercury"]

def compute_dasha(moon_lon, birth_local_naive):
    nak_index = int(moon_lon // NAK_WIDTH)
    degree_into = moon_lon % NAK_WIDTH
    nak_lord = LORD_SEQUENCE[nak_index % 9]
    fraction_left = (NAK_WIDTH - degree_into) / NAK_WIDTH
    first_maha_years = VIM_MAHAS[nak_lord] * fraction_left

    seq = []
    current_start = birth_local_naive
    start_idx = LORD_SEQUENCE.index(nak_lord)
    seq.append({
        "lord": nak_lord,
        "start": current_start.isoformat(),
        "end": (current_start + relativedelta(days=int(first_maha_years * 365.2425))).isoformat(),
        "years": round(first_maha_years, 6)
    })
    current_start = datetime.fromisoformat(seq[-1]["end"])
    idx = (start_idx + 1) % 9
    while current_start.year <= 2055:
        lord = LORD_SEQUENCE[idx]
        years = VIM_MAHAS[lord]
        end = current_start + relativedelta(days=int(years * 365.2425))
        seq.append({"lord": lord, "start": current_start.isoformat(), "end": end.isoformat(), "years": years})
        current_start = end
        idx = (idx + 1) % 9

    now = datetime.utcnow()
    maha_current = None
    for s in seq:
        sstart = datetime.fromisoformat(s["start"])
        send = datetime.fromisoformat(s["end"])
        if sstart <= now < send:
            maha_current = s
            break

    antars = []
    if maha_current:
        maha_len = maha_current["years"]
        start = datetime.fromisoformat(maha_current["start"])
        start_idx = LORD_SEQUENCE.index(maha_current["lord"])
        for i in range(9):
            lord = LORD_SEQUENCE[(start_idx + i) % 9]
            antar_years = (VIM_MAHAS[lord] / 120.0) * maha_len
            end = start + relativedelta(days=int(antar_years * 365.2425))
            antars.append({"lord": lord, "start": start.isoformat(), "end": end.isoformat(), "years": round(antar_years, 6)})
            start = end

    return {
        "nak_index": nak_index, "degree_into_nak": round(degree_into,6),
        "nak_lord": nak_lord, "maha_sequence": seq,
        "current_maha": maha_current, "antardashas": antars
    }

# --------------------------------------------
# Human-readable Astrology Report Generator
# --------------------------------------------
def generate_readable_report(planets, dasha):
    """Return a detailed, easy-to-understand reading for client reports."""
    asc = planets.get("Ascendant", 0)
    moon = planets.get("Moon", 0)
    sun = planets.get("Sun", 0)

    # Very simplified sign detection
    signs = [
        "Aries","Taurus","Gemini","Cancer","Leo","Virgo",
        "Libra","Scorpio","Sagittarius","Capricorn","Aquarius","Pisces"
    ]
    asc_sign = signs[int(asc // 30)]
    moon_sign = signs[int(moon // 30)]
    sun_sign = signs[int(sun // 30)]

    summary = (
        f"You are born with {asc_sign} rising, {moon_sign} Moon and {sun_sign} Sun. "
        "This forms the foundation of your personality. "
        f"As an ascendant of {asc_sign}, you tend to express yourself through "
        f"{'initiative and courage' if asc_sign=='Aries' else 'practical stability' if asc_sign=='Taurus' else 'mental curiosity' if asc_sign=='Gemini' else 'emotional depth and care' if asc_sign=='Cancer' else 'confidence and creativity' if asc_sign=='Leo' else 'precision and service' if asc_sign=='Virgo' else 'balance and diplomacy' if asc_sign=='Libra' else 'intensity and transformation' if asc_sign=='Scorpio' else 'vision and optimism' if asc_sign=='Sagittarius' else 'discipline and strategy' if asc_sign=='Capricorn' else 'innovation and freedom' if asc_sign=='Aquarius' else 'sensitivity and imagination'}. "
        f"The Moon in {moon_sign} shows your emotional world, while the Sun in {sun_sign} represents your soul purpose."
    )

    current_maha = dasha.get("current_maha", {}).get("lord", "Unknown")
    timeline = [
        {"phase": "Past (≈3.5 years before)", "influence": "Themes of closure, emotional lessons, and karmic resolution."},
        {"phase": "Present", "influence": f"You are currently in the influence of {current_maha} Mahadasha, focusing on its key lessons and growth areas."},
        {"phase": "Future (≈3.5 years ahead)", "influence": "Expansion into new opportunities, clarity of purpose, and spiritual renewal."}
    ]

    remedies = [
        "Practice gratitude meditation daily to balance your emotional field.",
        "Chant 'Om Namah Shivaya' or your planetary mantra on auspicious days.",
        "Keep a balance between material and spiritual pursuits.",
        "Offer water to the rising Sun every morning with mindfulness."
    ]

    return {
        "summary": summary,
        "timeline": timeline,
        "remedies": remedies
    }

# --------------------------------------------
# Main API Endpoint
# --------------------------------------------
@app.route("/compute_natal", methods=["POST"])
def compute_natal():
    payload = request.get_json(force=True)
    name = payload.get("name","Unknown")
    date = payload.get("date")   # expected DD/MM/YYYY
    time = payload.get("time")   # e.g. 12:30 AM
    place = payload.get("place")

    if not (date and time and place):
        return jsonify({"error":"please provide date, time, place"}), 400

    # Parse date
    dt_local_naive = None
    for fmt in ["%d/%m/%Y %I:%M %p", "%d/%m/%Y %H:%M", "%Y-%m-%d %I:%M %p", "%Y-%m-%d %H:%M"]:
        try:
            dt_local_naive = datetime.strptime(f"{date} {time}", fmt)
            break
        except Exception:
            continue
    if dt_local_naive is None:
        return jsonify({"error":"bad_date_time_format","details":f"Unable to parse date/time: {date} {time}"}), 400

    # Geocode
    try:
        lat, lon, place_name = geocode_place(place)
    except Exception as e:
        return jsonify({"error":"geocode_failed","details":str(e)}), 400

    # Timezone
    try:
        tzname, tz_offset, dt_local_with_tz = tz_from_latlon(lat, lon, dt_local_naive)
    except Exception as e:
        return jsonify({"error":"timezone_failed","details":str(e)}), 400

    # Convert to UTC
    dt_utc = dt_local_with_tz.astimezone(pytz.utc).replace(tzinfo=None)
    jd = swe.julday(dt_utc.year, dt_utc.month, dt_utc.day,
                    dt_utc.hour + dt_utc.minute/60.0 + dt_utc.second/3600.0)

    # Planetary longitudes
    planet_codes = {
        "Sun":swe.SUN,"Moon":swe.MOON,"Mars":swe.MARS,"Mercury":swe.MERCURY,
        "Jupiter":swe.JUPITER,"Venus":swe.VENUS,"Saturn":swe.SATURN,
        "Rahu":swe.MEAN_NODE,"Ketu":swe.TRUE_NODE
    }
    planets = {}
    for pname, pcode in planet_codes.items():
        val = swe.calc_ut(jd, pcode)[0][0] % 360
        planets[pname] = round(val,6)

    # Ascendant
    try:
        _, ascmc = swe.houses_ex(jd, lat, lon, b'P')
        asc = ascmc[0]
    except Exception:
        asc = swe.houses(jd, lat, lon)[0][0]
    planets["Ascendant"] = round(asc % 360,6)

    # Dasha & Readable Report
    dasha = compute_dasha(planets["Moon"], dt_local_naive)
    readable = generate_readable_report(planets, dasha)

    # Final Response
    resp = {
        "input_received": {"place_name": place_name, "timezone": tzname, "tz_offset_hours": tz_offset},
        "planets": planets,
        "dasha": dasha,
        "ayanamsha": "Lahiri",
        "readable_report": readable
    }
    return jsonify(resp), 200

@app.route("/", methods=["GET"])
def home():
    return "JyotiPath Swiss Ephemeris API running."

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
