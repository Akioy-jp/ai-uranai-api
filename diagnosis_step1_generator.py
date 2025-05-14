# diagnosis_step1_generator.py
from flask import Flask, request, jsonify
from flask_cors import CORS
from flatlib.chart import Chart
from flatlib.datetime import Datetime
from flatlib.geopos import GeoPos
from flatlib import const
from datetime import datetime
import json

app = Flask(__name__)
CORS(app)  # ★ これを追加！

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

# 宿曜（27宿）簡易版：生年月日からインデックスで決定
def get_sukuyou(birthdate):
    sukuyou_names = [
        "昴宿", "畢宿", "觜宿", "参宿", "井宿", "鬼宿", "柳宿", "星宿", "張宿",
        "翼宿", "軫宿", "角宿", "亢宿", "?宿", "房宿", "心宿", "尾宿", "箕宿",
        "斗宿", "女宿", "虚宿", "危宿", "室宿", "壁宿", "奎宿", "婁宿", "胃宿"
    ]
    base_date = datetime(1970, 1, 1)
    target_date = datetime.strptime(birthdate, "%Y-%m-%d")
    days_diff = (target_date - base_date).days
    index = days_diff % 27
    return sukuyou_names[index]

# カバラ数秘（簡易版：母音＝ソウル、全体＝デスティニー）
def calculate_kabbalah_numbers(name):
    letter_values = {
        'A':1,'B':2,'C':3,'D':4,'E':5,'F':8,'G':3,'H':5,'I':1,'J':1,'K':2,'L':3,'M':4,
        'N':5,'O':7,'P':8,'Q':1,'R':2,'S':3,'T':4,'U':6,'V':6,'W':6,'X':5,'Y':1,'Z':7
    }
    vowels = {'A', 'E', 'I', 'O', 'U'}
    name = name.upper()
    soul_total = sum(letter_values[ch] for ch in name if ch in vowels and ch in letter_values)
    destiny_total = sum(letter_values[ch] for ch in name if ch in letter_values)

    def reduce_number(n):
        while n >= 10 and n not in [11, 22, 33]:
            n = sum(int(d) for d in str(n))
        return n

    return {
        "soul_number": reduce_number(soul_total),
        "destiny_number": reduce_number(destiny_total)
    }

# マヤ暦（KIN番号、紋章、色、トーン）簡易版
MAYA_SIGILS = [
    "赤い龍", "白い風", "青い夜", "黄色い種", "赤い蛇", "白い世界の橋渡し", "青い手", "黄色い星",
    "赤い月", "白い犬", "青い猿", "黄色い人", "赤い空歩く者", "白い魔法使い", "青い鷲", "黄色い戦士",
    "赤い地球", "白い鏡", "青い嵐", "黄色い太陽"
]

MAYA_COLORS = ["赤", "白", "青", "黄"]

def calculate_maya_info(birthdate):
    base_date = datetime(1960, 7, 26)
    target_date = datetime.strptime(birthdate, "%Y-%m-%d")
    days_diff = (target_date - base_date).days
    kin = (days_diff % 260) + 1
    sigil = MAYA_SIGILS[(kin - 1) % 20]
    color = MAYA_COLORS[(kin - 1) % 4]
    tone = ((kin - 1) % 13) + 1
    return {
        "kin": kin,
        "sigil": sigil,
        "color": color,
        "tone": tone
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
        latitude=data['latitude'],
        longitude=data['longitude']
    )
    return jsonify(result)

# 診断値を生成する関数
def generate_step1_data(name, birthdate_str, birthtime_str, timezone, latitude, longitude):
    birthdate_str = birthdate_str.replace("-", "/")  # ←この1行を追加
    dt = Datetime(birthdate_str, birthtime_str, timezone)
    # 修正前（エラーの原因）
    # pos = GeoPos(str(latitude), str(longitude))

    # ✅ 修正後
    pos = GeoPos(str(int(float(latitude))), str(int(float(longitude))))
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

    from flatlib import houses  # 追加
    
    for obj in const.LIST_OBJECTS:
        p = chart.get(obj)
        sign = p.sign
        house = houses.houses(p.lon, chart.houses)  # ← 修正ここ
        planet_data[p.id] = {
            "sign": sign,
            "house": house,
            "degree": round(p.lon, 2)
        }
        element = ELEMENT_MAP.get(sign)
        if element:
            element_count[element] += 1
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
        "sukuyou": get_sukuyou(birthdate_str),
        "kabbalah": calculate_kabbalah_numbers(name),
        "maya": calculate_maya_info(birthdate_str),
        "planets": planet_data
    }

import os

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
