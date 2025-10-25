# main.py
from flask import Flask, request, jsonify
import swisseph as swe
import requests
from datetime import datetime
import pytz
from timezonefinder import TimezoneFinder
from dateutil.relativedelta import relativedelta

app = Flask(__name__)
swe.set_sid_mode(swe.SIDM_LAHIRI)
tf = TimezoneFinder()

# ---------------- Helper functions ----------------
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
    tzname = tf.timezone_at(lat=lat, lng=lon) or tf.closest_timezone_at(lat=lat, lng=lon)
    if not tzname:
        raise ValueError("Timezone not found for this location")
    tz = pytz.timezone(tzname)
    dt_local = tz.localize(dt_local_naive)
    offset_hours = dt_local.utcoffset().total_seconds() / 3600.0
    return tzname, offset_hours, dt_local

# Vimshottari constants
NAK_WIDTH = 13 + 1/3
VIM_MAHAS = {"Ketu":7,"Venus":20,"Sun":6,"Moon":10,"Mars":7,"Rahu":18,"Jupiter":16,"Saturn":19,"Mercury":17}
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

    return {"nak_index": nak_index, "degree_into_nak": round(degree_into,6), "nak_lord": nak_lord,
            "maha_sequence": seq, "current_maha": maha_current, "antardashas": antars}

# ---------------- API ----------------
@app.route("/compute_natal", methods=["POST"])
def compute_natal():
    payload = request.get_json(force=True)
    name = payload.get("name","Unknown")
    date = payload.get("date")
    time = payload.get("time")
    place = payload.get("place")

    if not (date and time and place):
        return jsonify({"error":"please provide date, time, place"}), 400

    dt_local_naive = None
    date_formats = ["%d/%m/%Y %I:%M %p","%d/%m/%Y %H:%M","%Y-%m-%d %I:%M %p","%Y-%m-%d %H:%M"]
    for fmt in date_formats:
        try:
            dt_local_naive = datetime.strptime(f"{date} {time}", fmt)
            break
        except Exception:
            continue
    if dt_local_naive is None:
        return jsonify({"error":"bad_date_time_format","details":f"Unable to parse date/time: {date} {time}"}), 400

    try:
        lat, lon, place_name = geocode_place(place)
        tzname, tz_offset, dt_local_with_tz = tz_from_latlon(lat, lon, dt_local_naive)
    except Exception as e:
        return jsonify({"error":"location_error","details":str(e)}), 400

    dt_utc = dt_local_with_tz.astimezone(pytz.utc).replace(tzinfo=None)
    jd = swe.julday(dt_utc.year, dt_utc.month, dt_utc.day, dt_utc.hour + dt_utc.minute/60.0 + dt_utc.second/3600.0)

    planet_codes = {
        "Sun":swe.SUN, "Moon":swe.MOON, "Mars":swe.MARS, "Mercury":swe.MERCURY,
        "Jupiter":swe.JUPITER, "Venus":swe.VENUS, "Saturn":swe.SATURN, "Rahu":swe.MEAN_NODE, "Ketu":swe.TRUE_NODE
    }
    planets = {}
    for pname, pcode in planet_codes.items():
        val = swe.calc_ut(jd, pcode)[0][0] % 360
        planets[pname] = round(val,6)

    try:
        _, ascmc = swe.houses_ex(jd, lat, lon, b'P')
        planets["Ascendant"] = round(ascmc[0] % 360,6)
    except:
        planets["Ascendant"] = round(swe.houses(jd, lat, lon)[0][0] % 360,6)

    dasha = compute_dasha(planets["Moon"], dt_local_naive)

    resp = {
        "input_received": {"place_name": place_name, "timezone": tzname, "tz_offset_hours": tz_offset},
        "planets": planets,
        "dasha": dasha,
        "ayanamsha": "Lahiri"
    }
    return jsonify(resp), 200

@app.route("/", methods=["GET"])
def home():
    return "JyotiPath Swiss Ephemeris API running."

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
