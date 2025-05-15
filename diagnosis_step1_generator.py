from flask import Flask, request, jsonify
from flask_cors import CORS
from flatlib.chart import Chart
from flatlib.datetime import Datetime
from flatlib.geopos import GeoPos
from flatlib import const
from datetime import datetime
import os

app = Flask(__name__)
CORS(app)

# 数秘術：ライフパスナンバー計算
def calculate_life_path_number(birthdate):
    digits = [int(ch) for ch in birthdate if ch.isdigit()]
    total = sum(digits)
    while total >= 10 and total not in [11, 22, 33]:
        total = sum(int(d) for d in str(total))
    return total

# 干支計算（年干支、簡易版）
def get_eto(year):
    eto_jikkan = ["甲", "乙", "丙", "丁", "戊", "己", "庚", "辛", "壬", "癸"]
    eto_junishi = ["子", "丑", "寅", "卯", "辰", "巳", "午", "未", "申", "酉", "戌", "亥"]
    base_year = 1984  # 甲子年
    diff = year - base_year
    jikkan = eto_jikkan[diff % 10]
    junishi = eto_junishi[diff % 12]
    return jikkan + junishi

from datetime import datetime

SUKUYO_STARS = [
    "昴宿", "畢宿", "觜宿", "参宿", "井宿", "鬼宿", "柳宿", "星宿", "張宿",
    "翼宿", "軫宿", "角宿", "亢宿", "氐宿", "房宿", "心宿", "尾宿", "箕宿",
    "斗宿", "女宿", "虚宿", "危宿", "室宿", "壁宿", "奎宿", "婁宿", "胃宿"
]

def calculate_sukuyo_star(birthdate):
    base_date = datetime(1880, 1, 27)  # ✅ 昴宿スタート日（心宿判定と整合）
    target_date = datetime.strptime(birthdate, "%Y-%m-%d")
    days_diff = (target_date - base_date).days
    index = (days_diff % 27 + 27) % 27
    return SUKUYO_STARS[index]

from datetime import datetime

MAYA_SIGILS = [
    "赤い龍", "白い風", "青い夜", "黄色い種", "赤い蛇",
    "白い世界の橋渡し", "青い手", "黄色い星", "赤い月", "白い犬",
    "青い猿", "黄色い人", "赤い空歩く者", "白い魔法使い", "青い鷲",
    "黄色い戦士", "赤い地球", "白い鏡", "青い嵐", "黄色い太陽"
]
MAYA_COLORS = ["赤", "白", "青", "黄"]

def calculate_maya_info(birthdate):
    base_date = datetime(1880, 9, 9)  # ✅ KIN 1 の基準日（13moon.net 準拠）
    target_date = datetime.strptime(birthdate, "%Y-%m-%d")
    days_diff = (target_date - base_date).days
    kin = (days_diff % 260 + 260) % 260 + 1

    tone = ((kin - 1) % 13) + 1
    sigil_index = (kin - 1) % 20
    sigil = MAYA_SIGILS[sigil_index]
    color = MAYA_COLORS[sigil_index % 4]

    wavespell_start_kin = kin - ((kin - 1) % 13)
    wavespell_sigil_index = (wavespell_start_kin - 1) % 20
    wavespell = MAYA_SIGILS[wavespell_sigil_index]

    return {
        "kin": kin,
        "tone": tone,
        "sigil": sigil,
        "color": color,
        "wavespell": wavespell
    }



# 診断APIエンドポイント
@app.route('/api/diagnose', methods=['POST'])
def diagnose():
    data = request.json
    result = generate_step1_data(
        name=data['name'],
        birthdate_str=data['birthdate'],
        birthtime_str=data['birthtime'],
        timezone=data['timezone'],
        latitude=str(data['latitude']),
        longitude=str(data['longitude'])
    )
    return jsonify(result)

# 診断ロジック
def generate_step1_data(name, birthdate_str, birthtime_str, timezone, latitude, longitude):
    birthdate_slash = birthdate_str.replace("-", "/")
    dt = Datetime(birthdate_slash, birthtime_str, timezone)

    def decimal_to_dms(value):
        deg = int(float(value))
        min_float = abs(float(value) - deg) * 60
        minutes = int(min_float)
        seconds = int((min_float - minutes) * 60)
        return f"{deg}:{minutes}:{seconds}"

    lat = decimal_to_dms(latitude)
    lon = decimal_to_dms(longitude)
    pos = GeoPos(lat, lon)
    chart = Chart(dt, pos, IDs=const.LIST_OBJECTS)

    planet_data = {}
    house_distribution = {}
    element_count = {"Fire": 0, "Earth": 0, "Air": 0, "Water": 0}
    ELEMENT_MAP = {
        "Aries": "Fire", "Leo": "Fire", "Sagittarius": "Fire",
        "Taurus": "Earth", "Virgo": "Earth", "Capricorn": "Earth",
        "Gemini": "Air", "Libra": "Air", "Aquarius": "Air",
        "Cancer": "Water", "Scorpio": "Water", "Pisces": "Water"
    }

    for obj in const.LIST_OBJECTS:
        p = chart.get(obj)
        sign = p.sign
        degree = round(p.lon, 2)

        try:
            house_num = chart.houses.getHouse(p.lon)
            house = house_num.num
        except Exception:
            house = None

        planet_data[p.id] = {
            "sign": sign,
            "house": house,
            "degree": degree
        }

        element = ELEMENT_MAP.get(sign)
        if element:
            element_count[element] += 1

        if house is not None:
            house_distribution.setdefault(house, []).append(p.id)

    most_element = max(element_count, key=element_count.get)
    year = int(birthdate_str.split("-")[0])

    return {
        "name": name,
        "birthdate": birthdate_str,
        "birthtime": birthtime_str,
        "timezone": timezone,
        "latitude": latitude,
        "longitude": longitude,
        "sun_sign": chart.get(const.SUN).sign,
        "moon_sign": chart.get(const.MOON).sign,
        "ascendant": chart.get(const.ASC).sign,
        "north_node_sign": chart.get(const.NORTH_NODE).sign,
        "house_planets": house_distribution,
        "element_balance": element_count,
        "dominant_element": most_element,
        "life_path_number": calculate_life_path_number(birthdate_str),
        "eto_year": get_eto(year),
        "sukuyou": calculate_sukuyo_star(birthdate_str),
        "maya": calculate_maya_info(birthdate_str),
        "planets": planet_data
    }

# アプリ起動
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
