"""
Utilities for fetching weather data and generating crop-specific advisories.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Tuple

import requests


# Bangla month names
BANGLA_MONTHS: Dict[int, str] = {
    1: "জানুয়ারি",
    2: "ফেব্রুয়ারি",
    3: "মার্চ",
    4: "এপ্রিল",
    5: "মে",
    6: "জুন",
    7: "জুলাই",
    8: "আগস্ট",
    9: "সেপ্টেম্বর",
    10: "অক্টোবর",
    11: "নভেম্বর",
    12: "ডিসেম্বর",
}

BANGLA_WEEKDAYS = [
    "সোমবার",
    "মঙ্গলবার",
    "বুধবার",
    "বৃহস্পতিবার",
    "শুক্রবার",
    "শনিবার",
    "রবিবার",
]

BANGLA_DIGITS = {
    "0": "০",
    "1": "১",
    "2": "২",
    "3": "৩",
    "4": "৪",
    "5": "৫",
    "6": "৬",
    "7": "৭",
    "8": "৮",
    "9": "৯",
}

DAY_LABELS = ["আজ", "আগামীকাল", "২ দিন", "৩ দিন", "৪ দিন", "৫ দিন", "৬ দিন"]

WEATHER_CODES = {
    0: "Clear",
    1: "Mainly Clear",
    2: "Partly Cloudy",
    3: "Overcast",
    45: "Foggy",
    48: "Foggy with Rime",
    51: "Light Drizzle",
    53: "Moderate Drizzle",
    55: "Heavy Drizzle",
    61: "Slight Rain",
    63: "Moderate Rain",
    65: "Heavy Rain",
    71: "Slight Snow",
    73: "Moderate Snow",
    75: "Heavy Snow",
    80: "Slight Rain Showers",
    81: "Moderate Rain Showers",
    82: "Heavy Rain Showers",
    85: "Snow Showers",
    86: "Heavy Snow Showers",
    95: "Thunderstorm",
    96: "Thunderstorm with Hail",
    99: "Thunderstorm with Heavy Hail",
}

BANGALDESH_LOCATIONS = {
    "dhaka": {"lat": 23.8103, "lon": 90.4125},
    "chittagong": {"lat": 22.3569, "lon": 91.7832},
    "rajshahi": {"lat": 24.3745, "lon": 88.6042},
    "khulna": {"lat": 22.8456, "lon": 89.5403},
    "barisal": {"lat": 22.7010, "lon": 90.3535},
    "sylhet": {"lat": 24.8949, "lon": 91.8687},
    "rangpur": {"lat": 25.7439, "lon": 89.2752},
    "mymensingh": {"lat": 24.7471, "lon": 90.4203},
    "palashbari": {"lat": 25.1222, "lon": 89.2542},
}

CROP_KEYS = (
    "ধান",
    "চাল/ধান মজুদ",
    "আলু",
    "গম",
    "ভুট্টা",
    "শাকসবজি",
)


@dataclass
class DailyWeather:
    date: str
    date_english: str
    date_label: str
    temperature: float
    temp_max: float
    temp_min: float
    humidity: float
    rainfall: float
    wind_speed: float
    condition: str


def _to_bangla_digits(value: str) -> str:
    """Convert any numeric string into Bangla digits."""
    return "".join(BANGLA_DIGITS.get(ch, ch) for ch in str(value))


def convert_to_bangla_date(date_obj: datetime) -> str:
    """Format a datetime object as Bangla weekday + date string."""
    weekday = BANGLA_WEEKDAYS[date_obj.weekday()]
    day = _to_bangla_digits(date_obj.day)
    month = BANGLA_MONTHS[date_obj.month]
    return f"{weekday}, {day} {month}"


def get_district_name_bangla(district_code: str) -> str:
    """Map English district aliases to Bangla display names."""
    district_names = {
        "dhaka": "ঢাকা",
        "chittagong": "চট্টগ্রাম",
        "rajshahi": "রাজশাহী",
        "khulna": "খুলনা",
        "barisal": "বরিশাল",
        "sylhet": "সিলেট",
        "rangpur": "রংপুর",
        "mymensingh": "ময়মনসিংহ",
        "jhenaidah": "ঝিনাইদহ",
        "noakhali": "নোয়াখালী",
        "comilla": "কুমিল্লা",
        "jashore": "যশোর",
        "bogra": "বগুড়া",
        "dinajpur": "দিনাজপুর",
        "pabna": "পাবনা",
    }
    return district_names.get(district_code.lower(), district_code)


def interpret_weather_code(code: int) -> str:
    """Convert a WMO weather code to human readable English."""
    return WEATHER_CODES.get(code, "Unknown")


def _day_label(idx: int) -> str:
    """Return Dhaka-style label for the ith forecast day."""
    if idx < len(DAY_LABELS):
        return DAY_LABELS[idx]
    return f"{_to_bangla_digits(idx)} দিন"


def fetch_weather_forecast(location: str) -> Dict[str, object]:
    """
    Pull a 7-day forecast from Open-Meteo and attach crop advisories.
    """
    try:
        coords = BANGALDESH_LOCATIONS.get(location.lower(), BANGALDESH_LOCATIONS["dhaka"])

        response = requests.get(
            "https://api.open-meteo.com/v1/forecast",
            params={
                "latitude": coords["lat"],
                "longitude": coords["lon"],
                "daily": ",".join(
                    [
                        "temperature_2m_max",
                        "temperature_2m_min",
                        "rainfall_sum",
                        "relative_humidity_2m_max",
                        "weather_code",
                        "wind_speed_10m_max",
                    ]
                ),
                "timezone": "Asia/Dhaka",
                "forecast_days": 7,
            },
            timeout=10,
        )
        response.raise_for_status()
        payload = response.json()

        if "daily" not in payload:
            return {
                "location": location,
                "forecast": [],
                "advisories": [],
                "current": {},
                "error": "Invalid API response",
            }

        forecast = _build_forecast(payload["daily"])
        advisories = build_weekly_agri_advisory(forecast)

        current = (
            {
                "temperature": forecast[0].temperature,
                "humidity": forecast[0].humidity,
                "rainfall": forecast[0].rainfall,
                "condition": forecast[0].condition,
            }
            if forecast
            else {}
        )

        return {
            "location": location,
            "location_bangla": get_district_name_bangla(location),
            "forecast": [dw.__dict__ for dw in forecast],
            "advisories": advisories,
            "current": current,
            "error": None,
        }

    except requests.RequestException as exc:
        return {
            "location": location,
            "forecast": [],
            "advisories": [],
            "current": {},
            "error": f"Weather service unavailable: {exc}",
        }
    except Exception as exc:  # pragma: no cover - defensive
        return {
            "location": location,
            "forecast": [],
            "advisories": [],
            "current": {},
            "error": f"Error processing weather data: {exc}",
        }


def _build_forecast(daily_block: Dict[str, List[float]]) -> List[DailyWeather]:
    """Transform API payload into DailyWeather objects."""
    forecast: List[DailyWeather] = []
    for idx, date_str in enumerate(daily_block["time"]):
        date_obj = datetime.strptime(date_str, "%Y-%m-%d")
        forecast.append(
            DailyWeather(
                date=convert_to_bangla_date(date_obj),
                date_english=date_str,
                date_label=_day_label(idx),
                temperature=round(
                    (daily_block["temperature_2m_max"][idx] + daily_block["temperature_2m_min"][idx])
                    / 2,
                    1,
                ),
                temp_max=daily_block["temperature_2m_max"][idx],
                temp_min=daily_block["temperature_2m_min"][idx],
                humidity=daily_block["relative_humidity_2m_max"][idx],
                rainfall=daily_block["rainfall_sum"][idx],
                wind_speed=daily_block["wind_speed_10m_max"][idx],
                condition=interpret_weather_code(daily_block["weather_code"][idx]),
            )
        )
    return forecast


def build_weekly_agri_advisory(forecast: List[DailyWeather]) -> List[Dict[str, object]]:
    """
    Generate AI-powered Bangla advisories for each crop for the next seven days.
    """
    advisories: List[Dict[str, object]] = []
    for day in forecast[:7]:
        crops: Dict[str, Dict[str, str]] = {}
        for crop in CROP_KEYS:
            risk, advice = _generate_ai_advisory(crop, day)
            crops[crop] = {"risk": risk, "advice": advice}

        advisories.append(
            {
                "label": day.date_label,
                "date": day.date,
                "date_english": day.date_english,
                "crops": crops,
            }
        )
    return advisories


def _generate_ai_advisory(crop: str, day: DailyWeather) -> Tuple[str, str]:
    """Generate AI-powered advisory following the Agricultural Advisory Generator rules."""
    
    # Extract weather conditions
    temp = day.temperature
    humidity = day.humidity
    rainfall = day.rainfall
    wind_speed = day.wind_speed
    condition = day.condition.lower()
    
    # Determine risk level based on conditions
    risk_level = _assess_risk_level(crop, temp, humidity, rainfall, wind_speed, condition)
    
    # Generate crop-specific advisory
    advice = _generate_crop_specific_advice(crop, risk_level, temp, humidity, rainfall, wind_speed, condition)
    
    return risk_level, advice


def _assess_risk_level(crop: str, temp: float, humidity: float, rainfall: float, wind_speed: float, condition: str) -> str:
    """Assess risk level based on crop type and weather conditions."""
    
    # Base risk assessment
    risk_factors = 0
    
    # Temperature factors
    if temp > 35 or temp < 10:
        risk_factors += 2
    elif temp > 30 or temp < 15:
        risk_factors += 1
        
    # Humidity factors
    if humidity > 85:
        risk_factors += 2
    elif humidity > 75:
        risk_factors += 1
        
    # Rainfall factors  
    if rainfall > 50:
        risk_factors += 2
    elif rainfall > 20:
        risk_factors += 1
        
    # Wind factors
    if wind_speed > 30:
        risk_factors += 2
    elif wind_speed > 20:
        risk_factors += 1
        
    # Condition factors
    if "thunderstorm" in condition or "heavy rain" in condition:
        risk_factors += 2
    elif "rain" in condition or "drizzle" in condition:
        risk_factors += 1
        
    # Crop-specific risk adjustments
    if crop in ["ধান", "rice"] and rainfall > 40:
        risk_factors += 1
    elif crop in ["আলু", "potato"] and humidity > 80:
        risk_factors += 1
    elif crop in ["টমেটো", "tomato"] and temp > 32:
        risk_factors += 1
    elif crop in ["ভুট্টা", "maize"] and wind_speed > 25:
        risk_factors += 1
        
    # Determine final risk level
    if risk_factors >= 5:
        return "Critical"
    elif risk_factors >= 3:
        return "High"
    elif risk_factors >= 2:
        return "Moderate"
    else:
        return "Low"


def _generate_crop_specific_advice(crop: str, risk_level: str, temp: float, humidity: float, 
                                 rainfall: float, wind_speed: float, condition: str) -> str:
    """Generate specific, actionable advice based on crop type and risk level."""
    
    # Crop mapping
    crop_map = {
        "ধান": "rice", "চাল/ধান মজুদ": "rice_storage",
        "আলু": "potato", "গম": "wheat", 
        "ভুট্টা": "maize", "শাকসবজি": "vegetable"
    }
    
    crop_type = crop_map.get(crop, "general")
    
    # Generate advice based on crop type and risk level
    if crop_type == "rice":
        return _generate_rice_advice(risk_level, temp, humidity, rainfall, wind_speed)
    elif crop_type == "rice_storage":
        return _generate_rice_storage_advice(risk_level, humidity, rainfall)
    elif crop_type == "potato":
        return _generate_potato_advice(risk_level, temp, humidity, rainfall)
    elif crop_type == "wheat":
        return _generate_wheat_advice(risk_level, temp, humidity, rainfall, condition)
    elif crop_type == "maize":
        return _generate_maize_advice(risk_level, wind_speed, rainfall, condition)
    elif crop_type == "vegetable":
        return _generate_vegetable_advice(risk_level, temp, rainfall, humidity)
    else:
        return _generate_general_advice(risk_level)


def _generate_rice_advice(risk_level: str, temp: float, humidity: float, rainfall: float, wind_speed: float) -> str:
    """Generate rice-specific advisory."""
    
    if risk_level == "Critical":
        if rainfall >= 90 or wind_speed >= 40:
            return "ভারী বৃষ্টি ও ঝড়ে জমির পানি দ্রুত বের করে দিন। গাছকে বাঁশের খুঁটি দিয়ে বেঁধে রাখুন।"
        return "জরুরি অবস্থা - জমি পর্যবেক্ষণ করুন এবং প্রয়োজনীয় ব্যবস্থা নিন।"
    
    elif risk_level == "High":
        if rainfall >= 60:
            return "জমিতে পানি জমার ঝুঁকি রয়েছে। নালা পরিষ্কার রাখুন এবং পানি নিষ্কাশন ব্যবস্থা চালু রাখুন।"
        elif humidity >= 85:
            return "উচ্চ আর্দ্রতায় ব্লাস্ট রোগের সম্ভাবনা। প্রতিরোধমূলক স্প্রে প্রয়োগ করুন।"
        return "ঝুঁকিপূর্ণ অবস্থা - বিশেষ সতর্কতা প্রয়োজন।"
    
    elif risk_level == "Moderate":
        if rainfall <= 5 and humidity < 55:
            return "মাঠ শুকিয়ে যাওয়ার迹象। সন্ধ্যায় হালকা সেচ দিন এবং মাটির আর্দ্রতা বজায় রাখুন।"
        return "সাধারণ পরিচর্যা চালিয়ে যান সাথে অতিরিক্ত সতর্কতা অবলম্বন করুন।"
    
    else:  # Low risk
        return "পর্যাপ্ত আর্দ্রতা রয়েছে। অনুকূল আবহাওয়ায় টপ ড্রেসিং ও আগাছা দমন চালিয়ে যান।"


def _generate_rice_storage_advice(risk_level: str, humidity: float, rainfall: float) -> str:
    """Generate rice storage advisory."""
    
    if risk_level == "Critical":
        return "গুদামে ডিহিউমিডিফায়ার চালু রাখুন এবং ধান প্লাস্টিক শিটে ঢেকে আর্দ্রতা রোধ করুন।"
    
    elif risk_level == "High":
        return "গুদামের দরজা-জানালা বন্ধ রেখে ভেন্টের মাধ্যমে শুকনা বাতাস চলাচল করান।"
    
    elif risk_level == "Moderate":
        return "ধানের বস্তা প্রতি দুই দিনে উল্টে দিন যাতে ফাঙ্গাস না ধরে।"
    
    else:  # Low risk
        return "শুকনা আবহাওয়ায় বস্তা প্যালেটে রেখে নিত্যদিন ধুলোময়লা পরিষ্কার করুন।"


def _generate_potato_advice(risk_level: str, temp: float, humidity: float, rainfall: float) -> str:
    """Generate potato-specific advisory."""
    
    if risk_level == "Critical":
        if humidity >= 92 or rainfall >= 60:
            return "কোল্ড স্টোরে আর্দ্রতা তৎক্ষণাৎ ৮৫% এর নিচে নামান। পচা আলু আলাদা করুন এবং বায়ু চলাচল বাড়ান।"
        return "জরুরি ব্যবস্থা প্রয়োজন - আলুর গুদাম দ্রুত পরীক্ষা করুন।"
    
    elif risk_level == "High":
        if humidity >= 85:
            return "গুদামে বায়ু চলাচল বাড়িয়ে দিন এবং অ্যান্টিফাঙ্গাল ধূম্রায়ন করুন।"
        return "আলুর সংরক্ষণে বিশেষ সতর্কতা প্রয়োজন।"
    
    elif risk_level == "Moderate":
        if temp <= 10:
            return "তাপমাত্রা কমে যাওয়ায় আলুর অঙ্কুরোদগম ধীর হবে। থার্মোস্ট্যাট ৮-১০°সে তে সমন্বয় করুন।"
        return "স্বাভাবিক পরিচর্যা চালিয়ে যান সাথে নিয়মিত পরীক্ষা করুন।"
    
    else:  # Low risk
        return "স্থিতিশীল আবহাওয়ায় আলু বাছাই ও প্যাকেজিং চালিয়ে যান।"


def _generate_wheat_advice(risk_level: str, temp: float, humidity: float, rainfall: float, condition: str) -> str:
    """Generate wheat-specific advisory."""
    
    if risk_level == "Critical":
        if rainfall >= 45 and "rain" in condition:
            return "দানা গঠন পর্যায়ে বৃষ্টি পড়ছে। ত্রিপল দিয়ে জমি ঢেকে দিন এবং পানি নিষ্কাশন ব্যবস্থা চালু রাখুন।"
        return "জরুরি ব্যবস্থা প্রয়োজন - গম ক্ষেত রক্ষা করুন।"
    
    elif risk_level == "High":
        if humidity >= 88 or "fog" in condition:
            return "কুয়াশা ও আর্দ্রতায় ব্লাইট রোগের ঝুঁকি। সকালেই কপার বা ম্যানকোজেব স্প্রে করুন।"
        elif temp >= 36:
            return "উচ্চ তাপমাত্রায় সেচ দিন এবং মালচ দিয়ে মাটি স্যাঁতসেঁতে রাখুন।"
        return "উচ্চ ঝুঁকির অবস্থা - বিশেষ যত্ন প্রয়োজন।"
    
    elif risk_level == "Moderate":
        if rainfall <= 5 and temp > 30:
            return "শুকনা দিনে হালকা সেচ দিন এবং টিলারিং বাড়ান।"
        return "সাধারণ পরিচর্যা চালিয়ে যান।"
    
    else:  # Low risk
        return "আবহাওয়া অনুকূল। টপ ড্রেসিং ও আগাছা দমন চালিয়ে যান।"


def _generate_maize_advice(risk_level: str, wind_speed: float, rainfall: float, condition: str) -> str:
    """Generate maize-specific advisory."""
    
    if risk_level == "Critical":
        if wind_speed >= 40:
            return "প্রবল বাতাসে ভুট্টা গাছ হেলে পড়ার ঝুঁকি। খুঁটি ও দড়ি ব্যবহার করে গাছ সাপোর্ট দিন।"
        return "জরুরি ব্যবস্থা প্রয়োজন - ভুট্টা ক্ষেত সুরক্ষিত করুন।"
    
    elif risk_level == "High":
        if wind_speed >= 30 or rainfall >= 55:
            return "দমকা হাওয়া/বৃষ্টিতে গাছ বাঁশের খুঁটিতে বেঁধে দিন এবং জমির পানি বের করুন।"
        return "উচ্চ ঝুঁকি - বিশেষ সতর্কতা প্রয়োজন।"
    
    elif risk_level == "Moderate":
        if "overcast" in condition or rainfall >= 35:
            return "মেঘলা আবহাওয়ায় পরাগায়নে সমস্যা হতে পারে। দুপুরে হালকা কাঁপুনি দিয়ে পলেন ঝরিয়ে দিন।"
        return "স্বাভাবিক পরিচর্যা চালিয়ে যান।"
    
    else:  # Low risk
        return "পর্যাপ্ত রোদে পাতায় জমা ধুলো ঝেড়ে সেচ সূচি বজায় রাখুন।"


def _generate_vegetable_advice(risk_level: str, temp: float, rainfall: float, humidity: float) -> str:
    """Generate vegetable-specific advisory."""
    
    if risk_level == "Critical":
        if temp >= 37 or rainfall >= 70:
            return "অত্যধিক গরম/বৃষ্টির воздействие। উঁচু বেডে পানি বের করে ছায়া জাল ব্যবহার করুন।"
        return "জরুরি ব্যবস্থা প্রয়োজন - শাকসবজি রক্ষা করুন।"
    
    elif risk_level == "High":
        if rainfall >= 50 or humidity >= 90:
            return "আর্দ্র পরিবেশে পোকার আক্রমণ বাড়ে। বেডের ড্রেন পরিষ্কার করুন এবং জৈব কীটনাশক স্প্রে করুন।"
        return "উচ্চ ঝুঁকি - বিশেষ যত্ন প্রয়োজন।"
    
    elif risk_level == "Moderate":
        if temp <= 16 or humidity >= 80:
            return "সকালে পাতার শিশির ঝেড়ে দিন এবং লিফ মাইনর/ডাউনি মিলডিউয়ের লক্ষণ দেখুন।"
        return "সাধারণ পরিচর্যা চালিয়ে যান।"
    
    else:  # Low risk
        return "মাঝারি আবহাওয়ায় নিয়মিত গাছ ছাঁটাই ও সুষম সেচ চালিয়ে যান।"


def _generate_general_advice(risk_level: str) -> str:
    """Generate general advisory for unspecified crops."""
    
    if risk_level == "Critical":
        return "জরুরি অবস্থা - ফসল সুরক্ষার জন্য অবিলম্বে ব্যবস্থা নিন। ক্ষেত পরিদর্শন করুন এবং প্রয়োজনীয় সুরক্ষা মজবুত করুন।"
    
    elif risk_level == "High":
        return "উচ্চ ঝুঁকিপূর্ণ অবস্থা। ফসলের বিশেষ যত্ন প্রয়োজন। নিয়মিত পর্যবেক্ষণ করুন এবং সমস্যা দেখা দিলে立即 ব্যবস্থা নিন।"
    
    elif risk_level == "Moderate":
        return "মধ্যম ঝুঁকির অবস্থা। সাধারণ পরিচর্যার সাথে অতিরিক্ত সতর্কতা অবলম্বন করুন।"
    
    else:  # Low risk
        return "স্বাভাবিক আবহাওয়া। নিয়মিত ফসল পরিচর্যা ও আগাছা দমন চালিয়ে যান।"


def is_favorable_weather(weather_data: Dict[str, float], crop_type: str = "general") -> Dict[str, object]:
    """
    Backwards compatible helper used elsewhere in the app.
    """
    temp = weather_data.get("temperature", 25)
    humidity = weather_data.get("humidity", 60)
    rainfall = weather_data.get("rainfall", 0)
    condition = weather_data.get("condition", "Clear")

    favorable = True
    reasons = []
    suggested_activity = "Routine crop management"

    if temp < 10 or temp > 40:
        favorable = False
        reasons.append(f"Temperature {temp}°C is outside optimal range (10-40°C)")
    elif temp < 15 or temp > 35:
        reasons.append(f"Suboptimal temperature {temp}°C")

    if humidity < 30:
        favorable = False
        reasons.append(f"Very low humidity {humidity}% - drought stress risk")
    elif humidity > 90:
        reasons.append(f"Very high humidity {humidity}% - disease risk")

    if rainfall > 100:
        favorable = False
        reasons.append(f"Heavy rainfall {rainfall}mm - waterlogging risk")
        suggested_activity = "Ensure proper drainage"
    elif rainfall > 50:
        reasons.append(f"Moderate rainfall {rainfall}mm - monitor waterlogging")
    elif rainfall < 5 and humidity < 50:
        suggested_activity = "Schedule irrigation"

    if condition in ["Thunderstorm", "Heavy Rain", "Heavy Snow"]:
        favorable = False
        reasons.append(f"Severe weather: {condition}")
        suggested_activity = "Protect crops, stay indoors"

    if favorable and not reasons:
        reasons.append("All conditions favorable for farming")
        suggested_activity = "Good day for field work"

    return {
        "favorable": favorable,
        "reasons": reasons,
        "suggested_activity": suggested_activity,
    }