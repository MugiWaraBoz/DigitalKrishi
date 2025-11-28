"""
Weather Module

This module handles:
- Weather API integration
- Bangla date formatting
- Weather forecast retrieval
- Weather data parsing
"""

import requests
from datetime import datetime, timedelta


# Bangla month names
BANGLA_MONTHS = {
    1: 'জানুয়ারি',
    2: 'ফেব্রুয়ারি',
    3: 'মার্চ',
    4: 'এপ্রিল',
    5: 'মে',
    6: 'জুন',
    7: 'জুলাই',
    8: 'আগস্ট',
    9: 'সেপ্টেম্বর',
    10: 'অক্টোবর',
    11: 'নভেম্বর',
    12: 'ডিসেম্বর'
}

BANGLA_WEEKDAYS = ['সোমবার', 'মঙ্গলবার', 'বুধবার', 'বৃহস্পতিবার', 'শুক্রবার', 'শনিবার', 'রবিবার']

BANGLA_NUMBERS = {
    '0': '০', '1': '১', '2': '२', '3': '३', '4': '४',
    '5': '५', '6': '६', '7': '७', '8': '८', '9': '९'
}


def convert_to_bangla_date(date_obj):
    """
    Convert Python date object to Bangla formatted string.
    
    Args:
        date_obj (datetime): Python datetime object
        
    Returns:
        str: Formatted date in Bangla (e.g., "সোমবার, ১৫ জানুয়ারি")
    """
    weekday = BANGLA_WEEKDAYS[date_obj.weekday()]
    day = date_obj.day
    month = BANGLA_MONTHS[date_obj.month]
    
    # Convert day to Bangla numerals
    day_str = str(day)
    bangla_day = ''.join(BANGLA_NUMBERS.get(d, d) for d in day_str)
    
    return f"{weekday}, {bangla_day} {month}"


def get_district_name_bangla(district_code):
    """
    Get Bangla name of a district from code.
    
    Args:
        district_code (str): District code or name
        
    Returns:
        str: District name in Bangla
    """
    district_names = {
        'dhaka': 'ঢাকা',
        'chittagong': 'চট্টগ্রাম',
        'rajshahi': 'রাজশাহী',
        'khulna': 'খুলনা',
        'barisal': 'বরিশাল',
        'sylhet': 'সিলেট',
        'rangpur': 'রংপুর',
        'mymensingh': 'ময়মনসিংহ',
        'jhenaidah': 'ঝিনাইদহ',
        'noakhali': 'নোয়াখালী',
        'comilla': 'কুমিল্লা',
        'jashore': 'যশোর',
        'bogra': 'বগুড়া',
        'dinajpur': 'দিনাজপুর',
        'pabna': 'পাবনা'
    }
    
    return district_names.get(district_code.lower(), district_code)


def fetch_weather_forecast(location):
    """
    Fetch 7-day weather forecast from Open-Meteo API.
    
    Args:
        location (str): Location name or coordinates
        
    Returns:
        dict: {
            'location': str,
            'forecast': list of {
                'date': str (Bangla formatted),
                'temperature': float,
                'humidity': float,
                'rainfall': float,
                'condition': str,
                'wind_speed': float
            },
            'current': dict of current conditions,
            'error': str (if error occurred)
        }
    """
    try:
        # Use Open-Meteo API (free, no key required)
        # First, we need to geocode the location
        
        # Common Bangladesh locations with coordinates
        locations = {
            'dhaka': {'lat': 23.8103, 'lon': 90.4125},
            'chittagong': {'lat': 22.3569, 'lon': 91.7832},
            'rajshahi': {'lat': 24.3745, 'lon': 88.6042},
            'khulna': {'lat': 22.8456, 'lon': 89.5403},
            'barisal': {'lat': 22.7010, 'lon': 90.3535},
            'sylhet': {'lat': 24.8949, 'lon': 91.8687},
            'rangpur': {'lat': 25.7439, 'lon': 89.2752},
        }
        
        loc_lower = location.lower()
        if loc_lower in locations:
            coords = locations[loc_lower]
        else:
            # Default to Dhaka if location not found
            coords = locations['dhaka']
        
        # Fetch forecast from Open-Meteo
        base_url = 'https://api.open-meteo.com/v1/forecast'
        params = {
            'latitude': coords['lat'],
            'longitude': coords['lon'],
            'daily': 'temperature_2m_max,temperature_2m_min,rainfall_sum,relative_humidity_2m_max,weather_code,wind_speed_10m_max',
            'timezone': 'Asia/Dhaka',
            'forecast_days': 7
        }
        
        response = requests.get(base_url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        if 'daily' not in data:
            return {
                'location': location,
                'forecast': [],
                'current': {},
                'error': 'Invalid API response'
            }
        
        daily = data['daily']
        forecast = []
        
        for i in range(len(daily['time'])):
            date_str = daily['time'][i]
            date_obj = datetime.strptime(date_str, '%Y-%m-%d')
            
            # Convert weather code to condition
            weather_code = daily['weather_code'][i]
            condition = interpret_weather_code(weather_code)
            
            forecast.append({
                'date': convert_to_bangla_date(date_obj),
                'date_english': date_str,
                'temperature': round((daily['temperature_2m_max'][i] + daily['temperature_2m_min'][i]) / 2, 1),
                'temp_max': daily['temperature_2m_max'][i],
                'temp_min': daily['temperature_2m_min'][i],
                'humidity': daily['relative_humidity_2m_max'][i],
                'rainfall': daily['rainfall_sum'][i],
                'condition': condition,
                'wind_speed': daily['wind_speed_10m_max'][i]
            })
        
        return {
            'location': location,
            'location_bangla': get_district_name_bangla(location),
            'forecast': forecast,
            'current': {
                'temperature': forecast[0]['temperature'] if forecast else 0,
                'humidity': forecast[0]['humidity'] if forecast else 0,
                'rainfall': forecast[0]['rainfall'] if forecast else 0,
                'condition': forecast[0]['condition'] if forecast else 'Unknown'
            },
            'error': None
        }
        
    except requests.RequestException as e:
        print(f"Error fetching weather: {e}")
        return {
            'location': location,
            'forecast': [],
            'current': {},
            'error': f'Weather service unavailable: {str(e)}'
        }
    except Exception as e:
        print(f"Unexpected error in fetch_weather_forecast: {e}")
        return {
            'location': location,
            'forecast': [],
            'current': {},
            'error': f'Error processing weather data: {str(e)}'
        }


def interpret_weather_code(code):
    """
    Convert WMO weather code to human-readable condition.
    
    Args:
        code (int): WMO weather code
        
    Returns:
        str: Human-readable weather condition
    """
    weather_codes = {
        0: 'Clear',
        1: 'Mainly Clear',
        2: 'Partly Cloudy',
        3: 'Overcast',
        45: 'Foggy',
        48: 'Foggy with Rime',
        51: 'Light Drizzle',
        53: 'Moderate Drizzle',
        55: 'Heavy Drizzle',
        61: 'Slight Rain',
        63: 'Moderate Rain',
        65: 'Heavy Rain',
        71: 'Slight Snow',
        73: 'Moderate Snow',
        75: 'Heavy Snow',
        80: 'Slight Rain Showers',
        81: 'Moderate Rain Showers',
        82: 'Heavy Rain Showers',
        85: 'Snow Showers',
        86: 'Heavy Snow Showers',
        95: 'Thunderstorm',
        96: 'Thunderstorm with Hail',
        99: 'Thunderstorm with Heavy Hail'
    }
    
    return weather_codes.get(code, 'Unknown')


def is_favorable_weather(weather_data, crop_type='general'):
    """
    Check if current weather is favorable for farming activities.
    
    Args:
        weather_data (dict): Current weather conditions
        crop_type (str): Type of crop for specific checks
        
    Returns:
        dict: {
            'favorable': bool,
            'reasons': list of reasons,
            'suggested_activity': str
        }
    """
    temp = weather_data.get('temperature', 25)
    humidity = weather_data.get('humidity', 60)
    rainfall = weather_data.get('rainfall', 0)
    condition = weather_data.get('condition', 'Clear')
    
    favorable = True
    reasons = []
    suggested_activity = 'Routine crop management'
    
    # Temperature check
    if temp < 10 or temp > 40:
        favorable = False
        reasons.append(f'Temperature {temp}°C is outside optimal range (10-40°C)')
    elif temp < 15 or temp > 35:
        reasons.append(f'Suboptimal temperature {temp}°C')
    
    # Humidity check
    if humidity < 30:
        favorable = False
        reasons.append(f'Very low humidity {humidity}% - drought stress risk')
    elif humidity > 90:
        reasons.append(f'Very high humidity {humidity}% - disease risk')
    
    # Rainfall check
    if rainfall > 100:
        favorable = False
        reasons.append(f'Heavy rainfall {rainfall}mm - waterlogging risk')
        suggested_activity = 'Ensure proper drainage'
    elif rainfall > 50:
        reasons.append(f'Moderate rainfall {rainfall}mm - monitor waterlogging')
    elif rainfall < 5 and humidity < 50:
        suggested_activity = 'Schedule irrigation'
    
    # Weather condition check
    if condition in ['Thunderstorm', 'Heavy Rain', 'Heavy Snow']:
        favorable = False
        reasons.append(f'Severe weather: {condition}')
        suggested_activity = 'Protect crops, stay indoors'
    
    if favorable and not reasons:
        reasons.append('All conditions favorable for farming')
        suggested_activity = 'Good day for field work'
    
    return {
        'favorable': favorable,
        'reasons': reasons,
        'suggested_activity': suggested_activity
    }
