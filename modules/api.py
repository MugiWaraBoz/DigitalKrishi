from flask import Blueprint, request, jsonify, session
import requests
import os
from datetime import datetime

from modules.database import get_supabase
from modules.weather import fetch_weather_forecast

api_bp = Blueprint('api', __name__)

# ==================== HELPER FUNCTIONS ====================

def get_upazila_coords():
    """Map of Bangladeshi upazilas to coordinates and names"""
    return {
        'dhaka': {'lat': 23.8103, 'lon': 90.4125, 'name': 'ঢাকা'},
        'chittagong': {'lat': 22.3569, 'lon': 91.7832, 'name': 'চট্টগ্রাম'},
        'rajshahi': {'lat': 24.3745, 'lon': 88.6042, 'name': 'রাজশাহী'},
        'khulna': {'lat': 22.8456, 'lon': 89.5644, 'name': 'খুলনা'},
        'barisal': {'lat': 22.7010, 'lon': 90.3535, 'name': 'বরিশাল'},
        'sylhet': {'lat': 24.8949, 'lon': 91.8687, 'name': 'সিলেট'},
        'rangpur': {'lat': 25.7439, 'lon': 89.2752, 'name': 'রংপুর'},
        'mymensingh': {'lat': 24.7465, 'lon': 90.4082, 'name': 'ময়মনসিংহ'}
    }

def calculate_risk_level(forecasts):
    """
    Calculate risk level based on weather forecast data
    Returns: (risk_level: str, risk_score: int, factors: list)
    """
    if not forecasts:
        return 'low', 0, []
    
    risk_factors = []
    risk_score = 0
    
    for forecast in forecasts:
        temp = forecast.get('temp', 0)
        humidity = forecast.get('humidity', 0)
        rain_chance = forecast.get('rain_chance', 0)
        
        # Temperature risks
        if temp > 38:
            risk_score += 20
            risk_factors.append(f"অত্যধিক তাপমাত্রা ({temp}°C)")
        elif temp > 35:
            risk_score += 10
            risk_factors.append(f"উচ্চ তাপমাত্রা ({temp}°C)")
        elif temp < 5:
            risk_score += 15
            risk_factors.append(f"অত্যধিক ঠান্ডা ({temp}°C)")
        elif temp < 10:
            risk_score += 8
            risk_factors.append(f"শীত ({temp}°C)")
        
        # Humidity risks (fungal diseases)
        if humidity > 90:
            risk_score += 18
            risk_factors.append(f"অত্যধিক আর্দ্রতা ({humidity}%) - ছত্রাক রোগের ঝুঁকি")
        elif humidity > 80:
            risk_score += 12
            risk_factors.append(f"উচ্চ আর্দ্রতা ({humidity}%)")
        elif humidity < 40:
            risk_score += 5
            risk_factors.append(f"কম আর্দ্রতা ({humidity}%)")
        
        # Rain risks
        if rain_chance > 90:
            risk_score += 25
            risk_factors.append(f"খুব বেশি বৃষ্টির সম্ভাবনা ({rain_chance:.0f}%)")
        elif rain_chance > 70:
            risk_score += 15
            risk_factors.append(f"বৃষ্টির সম্ভাবনা ({rain_chance:.0f}%)")
        elif rain_chance > 50:
            risk_score += 8
            risk_factors.append(f"মাঝারি বৃষ্টির সম্ভাবনা ({rain_chance:.0f}%)")
    
    # Average the risk score
    risk_score = int(risk_score / len(forecasts))
    
    # Determine risk level
    if risk_score >= 60:
        risk_level = 'high'
    elif risk_score >= 35:
        risk_level = 'medium'
    else:
        risk_level = 'low'
    
    return risk_level, risk_score, list(set(risk_factors))[:3]  # Unique top 3 factors


def update_crop_risk_level(crop_id, farmer_id, risk_level):
    """Update crop risk level in database"""
    try:
        supabase = get_supabase()
        supabase.table('crop_batches')\
            .update({'current_risk_level': risk_level})\
            .eq('id', crop_id)\
            .eq('farmer_id', farmer_id)\
            .execute()
        return True
    except Exception as e:
        print(f"Error updating risk level: {e}")
        return False


def get_bengali_date(date_str):
    """Convert YYYY-MM-DD to Bangla formatted date"""
    try:
        date_obj = datetime.strptime(date_str, '%Y-%m-%d')
        bengali_months = [
            'জানু', 'ফেব', 'মার্চ', 'এপ্রি', 'মে', 'জুন',
            'জুলা', 'আগ', 'সেপ', 'অক্টো', 'নভে', 'ডিসে'
        ]
        bengali_days = ['সোম', 'মঙ্গল', 'বুধ', 'বৃহস্প', 'শুক্র', 'শনি', 'রবি']
        
        day_of_week = bengali_days[date_obj.weekday()]
        month = bengali_months[date_obj.month - 1]
        
        return f"{day_of_week}, {date_obj.day} {month}"
    except:
        return date_str


# ==================== USER ENDPOINTS ====================

@api_bp.route('/api/user/info')
def get_user_info():
    """Get user profile information including registration date"""
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    try:
        supabase = get_supabase()
        farmer_id = session['user_id']
        
        # Fetch farmer info
        result = supabase.table('farmers')\
            .select('*')\
            .eq('id', farmer_id)\
            .single()\
            .execute()
        
        if not result.data:
            return jsonify({'error': 'User not found'}), 404
        
        farmer = result.data
        
        # Format created_at date
        created_date = None
        if farmer.get('created_at'):
            try:
                # Parse ISO format date
                date_obj = datetime.fromisoformat(farmer['created_at'].replace('Z', '+00:00'))
                # Format as: 15 নভেম্বর, 2025
                bengali_months = [
                    'জানুয়ারি', 'ফেব্রুয়ারি', 'মার্চ', 'এপ্রিল', 'মে', 'জুন',
                    'জুলাই', 'আগস্ট', 'সেপ্টেম্বর', 'অক্টোবর', 'নভেম্বর', 'ডিসেম্বর'
                ]
                month_bn = bengali_months[date_obj.month - 1]
                created_date = f"{date_obj.day} {month_bn}, {date_obj.year}"
            except:
                created_date = farmer['created_at']
        
        return jsonify({
            'id': farmer.get('id'),
            'name': farmer.get('name'),
            'email': farmer.get('email'),
            'phone': farmer.get('phone'),
            'created_at': farmer.get('created_at'),
            'created_at_bn': created_date,
            'preferred_language': farmer.get('preferred_language', 'en')
        })
        
    except Exception as e:
        print(f"Error fetching user info: {e}")
        return jsonify({'error': str(e)}), 500


# ==================== WEATHER ENDPOINTS ====================

@api_bp.route('/api/weather/<location>')
def get_weather(location):
    """Fetch 7-day weather forecast with district name"""
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    try:
        api_key = os.getenv('OPENWEATHER_API_KEY')
        if not api_key:
            return jsonify({'error': 'Weather API not configured'}), 500
        
        upazilas = get_upazila_coords()
        loc_lower = location.lower()
        
        if loc_lower not in upazilas:
            return jsonify({'error': 'Invalid location'}), 400
        
        coords = upazilas[loc_lower]
        district_name_bn = coords['name']
        
        # Fetch 7-day weather forecast (16 data points = ~2 days, so we need to request more)
        url = f"https://api.openweathermap.org/data/2.5/forecast?lat={coords['lat']}&lon={coords['lon']}&appid={api_key}&units=metric"
        
        response = requests.get(url, timeout=5)
        response.raise_for_status()
        
        weather_data = response.json()
        
        # Process forecast data - get 7 days
        forecasts = []
        seen_dates = set()
        
        for item in weather_data.get('list', []):
            date = item['dt_txt'][:10]  # YYYY-MM-DD
            
            if date not in seen_dates and len(forecasts) < 7:
                seen_dates.add(date)
                bengali_date = get_bengali_date(date)
                
                forecasts.append({
                    'date': date,
                    'date_bn': bengali_date,
                    'temp': round(item['main']['temp']),
                    'temp_min': round(item['main']['temp_min']),
                    'temp_max': round(item['main']['temp_max']),
                    'humidity': item['main']['humidity'],
                    'rain_chance': item.get('pop', 0) * 100,
                    'rain_mm': item.get('rain', {}).get('3h', 0),
                    'wind_speed': item.get('wind', {}).get('speed', 0),
                    'description': item['weather'][0]['description'],
                    'icon': item['weather'][0]['icon']
                })
        
        return jsonify({
            'location': location,
            'location_bn': district_name_bn,
            'forecasts': forecasts,
            'current_temp': weather_data['list'][0]['main']['temp'],
            'current_humidity': weather_data['list'][0]['main']['humidity']
        })
        
    except requests.exceptions.RequestException as req_err:
        print(f"Weather API error: {req_err}")
        return jsonify({'error': 'Failed to fetch weather data', 'details': str(req_err)}), 500
    except Exception as e:
        print(f"Error in get_weather: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e), 'type': type(e).__name__}), 500


@api_bp.route('/api/weather/agri/<location>')
def get_weather_agri(location):
    """
    Fetch 7-day agricultural advisory for all major crops.

    Uses Open-Meteo via modules.weather.fetch_weather_forecast and returns
    Dhaka-style date labels plus crop-wise risk/advice in Bangla.
    """
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401

    try:
        data = fetch_weather_forecast(location)
        if data.get('error'):
            return jsonify({'error': data['error']}), 500
        return jsonify(data)
    except Exception as e:
        print(f"Error in get_weather_agri: {e}")
        return jsonify({'error': str(e)}), 500


@api_bp.route('/api/weather-advisory/<crop_id>')
def get_weather_advisory(crop_id):
    """Generate weather advisory with risk assessment and district info"""
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    try:
        supabase = get_supabase()
        farmer_id = session['user_id']
        
        # Fetch crop
        print(f"Fetching crop with ID: {crop_id}")
        crop_result = supabase.table('crop_batches')\
            .select('*')\
            .eq('id', crop_id)\
            .eq('farmer_id', farmer_id)\
            .single()\
            .execute()
        
        if not crop_result.data:
            return jsonify({'error': 'Crop not found'}), 404
        
        crop = crop_result.data
        print(f"Crop found: {crop}")
        
        upazilas = get_upazila_coords()
        loc_lower = crop['storage_location'].lower() if crop['storage_location'] else 'dhaka'
        
        if loc_lower not in upazilas:
            loc_lower = 'dhaka'
        
        coords = upazilas[loc_lower]
        district_name_bn = coords['name']
        
        # Fetch weather
        api_key = os.getenv('OPENWEATHER_API_KEY')
        weather_url = f"https://api.openweathermap.org/data/2.5/forecast?lat={coords['lat']}&lon={coords['lon']}&appid={api_key}&units=metric"
        
        weather_response = requests.get(weather_url, timeout=5)
        weather_response.raise_for_status()
        weather_data = weather_response.json()
        
        # Process weather data for advisories
        advisories = []
        risk_days = []
        processed_dates = set()
        
        for item in weather_data.get('list', []):
            date = item['dt_txt'][:10]
            
            if date in processed_dates or len(processed_dates) >= 7:
                continue
            processed_dates.add(date)
            
            temp = item['main']['temp']
            humidity = item['main']['humidity']
            rain_chance = item.get('pop', 0) * 100
            description = item['weather'][0]['description']
            bengali_date = get_bengali_date(date)
            
            # Build advisory for this day
            day_advisory = []
            day_risk = 'low'
            
            # Temperature advisory
            if temp > 38:
                day_advisory.append(f"🔴 {bengali_date}: অত্যধিক তাপমাত্রা ({temp}°C)! দ্রুত ঠান্ডা করুন এবং বায়ুচলাচল বাড়ান।")
                day_risk = 'high'
            elif temp > 35:
                day_advisory.append(f"🟡 {bengali_date}: উচ্চ তাপমাত্রা ({temp}°C)। দিনের বেলায় ঢেকে দিন এবং নিয়মিত বায়ুচলাচল নিশ্চিত করুন।")
                day_risk = 'medium'
            elif temp < 5:
                day_advisory.append(f"🔴 {bengali_date}: অত্যধিক ঠান্ডা ({temp}°C)! শীতের ক্ষতি প্রতিরোধ করুন, ঢেকে রাখুন।")
                day_risk = 'high'
            elif temp < 10:
                day_advisory.append(f"🟡 {bengali_date}: শীত ({temp}°C)। ফসল সুরক্ষিত রাখুন।")
                if day_risk != 'high':
                    day_risk = 'medium'
            
            # Humidity advisory
            if humidity > 90:
                day_advisory.append(f"⚠️ {bengali_date}: অত্যধিক আর্দ্রতা ({humidity}%)! ছত্রাক রোগের ঝুঁকি বেশি। বায়ুচলাচল ম্যাক্সিমাম করুন।")
                if day_risk != 'high':
                    day_risk = 'medium'
            elif humidity > 80:
                day_advisory.append(f"🟡 {bengali_date}: উচ্চ আর্দ্রতা ({humidity}%)। ছত্রাক প্রতিরোধে সতর্ক থাকুন।")
                if day_risk != 'high':
                    day_risk = 'medium'
            
            # Rain advisory
            if rain_chance > 90:
                day_advisory.append(f"🌧️ {bengali_date}: প্রচুর বৃষ্টির সম্ভাবনা ({rain_chance:.0f}%)! ছাউনি/পলিথিন প্রস্তুত রাখুন এবং নালা ঠিক করুন।")
                if day_risk != 'high':
                    day_risk = 'medium'
            elif rain_chance > 70:
                day_advisory.append(f"💧 {bengali_date}: বৃষ্টির সম্ভাবনা ({rain_chance:.0f}%)। জল নিকাশী ভালো রাখুন।")
                if day_risk != 'high':
                    day_risk = 'medium'
            elif rain_chance > 40:
                day_advisory.append(f"🌤️ {bengali_date}: হালকা বৃষ্টির সম্ভাবনা ({rain_chance:.0f}%)।")
            
            # Add day's advisory
            if day_advisory:
                for adv in day_advisory:
                    advisories.append(adv)
            else:
                advisories.append(f"✅ {bengali_date}: স্বাভাবিক আবহাওয়া। নিয়মিত যত্ন অব্যাহত রাখুন।")
            
            risk_days.append(day_risk)
        
        # Calculate overall risk level
        all_forecasts = []
        seen_dates = set()
        
        for item in weather_data.get('list', []):
            date = item['dt_txt'][:10]
            
            if date not in seen_dates and len(all_forecasts) < 7:
                seen_dates.add(date)
                all_forecasts.append({
                    'temp': item['main']['temp'],
                    'humidity': item['main']['humidity'],
                    'rain_chance': item.get('pop', 0) * 100
                })
        
        overall_risk, risk_score, risk_factors = calculate_risk_level(all_forecasts)
        
        # Update crop risk level in database
        update_crop_risk_level(crop_id, farmer_id, overall_risk)
        
        # Add general advice based on risk level
        if overall_risk == 'high':
            advisories.insert(0, f"🚨 এই সপ্তাহের ঝুঁকি স্তর: উচ্চ ({risk_score}/100)")
        elif overall_risk == 'medium':
            advisories.insert(0, f"⚠️ এই সপ্তাহের ঝুঁকি স্তর: মাঝারি ({risk_score}/100)")
        else:
            advisories.insert(0, f"✅ এই সপ্তাহের ঝুঁকি স্তর: কম ({risk_score}/100)")
        
        return jsonify({
            'crop_id': crop_id,
            'crop_type': crop['crop_type'],
            'location': loc_lower,
            'location_bn': district_name_bn,
            'risk_level': overall_risk,
            'risk_score': risk_score,
            'risk_factors': risk_factors,
            'advisories': advisories
        })
        
    except Exception as e:
        print(f"Error in get_weather_advisory: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e), 'type': type(e).__name__}), 500


# ==================== CROP ENDPOINTS ====================

@api_bp.route('/api/crops/active')
def active_crops():
    """Get active crops for logged-in user"""
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    try:
        supabase = get_supabase()
        farmer_id = session['user_id']
        
        crops = supabase.table('crop_batches')\
            .select('*')\
            .eq('farmer_id', farmer_id)\
            .eq('status', 'active')\
            .execute()
        
        return jsonify(crops.data if crops.data else [])
        
    except Exception as e:
        print(f"Error in active_crops: {e}")
        return jsonify({'error': str(e)}), 500


@api_bp.route('/api/crops/all')
def all_crops():
    """Get all crops for logged-in user"""
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    try:
        supabase = get_supabase()
        farmer_id = session['user_id']
        
        crops = supabase.table('crop_batches')\
            .select('*')\
            .eq('farmer_id', farmer_id)\
            .order('created_at', desc=True)\
            .execute()
        
        return jsonify(crops.data if crops.data else [])
        
    except Exception as e:
        print(f"Error in all_crops: {e}")
        return jsonify({'error': str(e)}), 500


@api_bp.route('/api/dashboard/stats')
def dashboard_stats():
    """Get dashboard statistics"""
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    try:
        supabase = get_supabase()
        farmer_id = session['user_id']
        
        # Get active batches
        active_result = supabase.table('crop_batches')\
            .select('*')\
            .eq('farmer_id', farmer_id)\
            .eq('status', 'active')\
            .execute()
        
        active_count = len(active_result.data) if active_result.data else 0
        total_weight = sum(b['estimated_weight'] for b in active_result.data) if active_result.data else 0
        
        # Get completed batches for success rate calculation
        completed_result = supabase.table('crop_batches')\
            .select('*')\
            .eq('farmer_id', farmer_id)\
            .eq('status', 'completed')\
            .execute()
        
        completed_count = len(completed_result.data) if completed_result.data else 0
        
        # Calculate success rate based on completed batches
        # Success rate = (completed_count / (active_count + completed_count)) * 100
        # If no batches, default to 0
        total_batches = active_count + completed_count
        if total_batches > 0:
            success_rate = round((completed_count / total_batches) * 100)
        else:
            success_rate = 0
        
        # Get loss data from loss_events table for saved food calculation
        loss_result = supabase.table('loss_events')\
            .select('loss_percentage')\
            .eq('farmer_id', farmer_id)\
            .execute()
        
        # Calculate average loss percentage (actual loss from records)
        # If no loss events, assume 0% loss (no data yet)
        if loss_result.data and len(loss_result.data) > 0:
            avg_loss_percentage = sum(e.get('loss_percentage', 0) for e in loss_result.data) / len(loss_result.data)
        else:
            avg_loss_percentage = 0  # No loss data = 0% loss
        
        # Saved food = total_weight * (1 - loss_percentage/100)
        # For example: 100kg * (1 - 15/100) = 85kg saved
        loss_prevention_rate = max(0, 100 - avg_loss_percentage)
        saved_food = total_weight * (loss_prevention_rate / 100)
        
        stats = {
            'active_batches': active_count,
            'total_weight': round(total_weight, 2),
            'saved_food': round(saved_food, 2),
            'success_rate': success_rate
        }
        
        return jsonify(stats)
        
    except Exception as e:
        print(f"Error in dashboard_stats: {e}")
        return jsonify({'error': str(e)}), 500


@api_bp.route('/api/crops/<batch_id>/complete', methods=['POST'])
def complete_crop(batch_id):
    """Mark crop as completed"""
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401

    try:
        supabase = get_supabase()
        farmer_id = session['user_id']

        # Verify ownership
        result = supabase.table('crop_batches')\
            .select('*')\
            .eq('id', batch_id)\
            .eq('farmer_id', farmer_id)\
            .single()\
            .execute()
        
        if not result.data:
            return jsonify({'error': 'Batch not found'}), 404

        update = supabase.table('crop_batches')\
            .update({'status': 'completed'})\
            .eq('id', batch_id)\
            .execute()
        
        if update.data:
            return jsonify({'success': True, 'batch': update.data[0]})
        else:
            return jsonify({'error': 'Failed to update batch'}), 500

    except Exception as e:
        print(f"Error completing batch: {e}")
        return jsonify({'error': str(e)}), 500


@api_bp.route('/api/crops/<batch_id>/reactivate', methods=['POST'])
def reactivate_crop(batch_id):
    """Reactivate a completed batch"""
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401

    try:
        supabase = get_supabase()
        farmer_id = session['user_id']

        result = supabase.table('crop_batches')\
            .select('*')\
            .eq('id', batch_id)\
            .eq('farmer_id', farmer_id)\
            .single()\
            .execute()
        
        if not result.data:
            return jsonify({'error': 'Batch not found'}), 404

        update = supabase.table('crop_batches')\
            .update({'status': 'active'})\
            .eq('id', batch_id)\
            .execute()
        
        if update.data:
            return jsonify({'success': True, 'batch': update.data[0]})
        else:
            return jsonify({'error': 'Failed to update batch'}), 500

    except Exception as e:
        print(f"Error reactivating batch: {e}")
        return jsonify({'error': str(e)}), 500


@api_bp.route('/api/crops/<batch_id>', methods=['DELETE'])
def delete_crop(batch_id):
    """Delete a crop batch"""
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401

    try:
        supabase = get_supabase()
        farmer_id = session['user_id']

        # Verify ownership
        result = supabase.table('crop_batches')\
            .select('*')\
            .eq('id', batch_id)\
            .eq('farmer_id', farmer_id)\
            .single()\
            .execute()
        
        if not result.data:
            return jsonify({'error': 'Batch not found'}), 404

        deleted = supabase.table('crop_batches')\
            .delete()\
            .eq('id', batch_id)\
            .execute()
        
        if deleted.data:
            return jsonify({'success': True})
        else:
            return jsonify({'error': 'Failed to delete batch'}), 500

    except Exception as e:
        print(f"Error deleting batch: {e}")
        return jsonify({'error': str(e)}), 500


@api_bp.route('/api/crops/export', methods=['GET'])
def export_crops_csv():
    """Export crops as CSV"""
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401

    try:
        import csv
        import io
        from flask import make_response
        
        supabase = get_supabase()
        farmer_id = session['user_id']

        rows = supabase.table('crop_batches')\
            .select('*')\
            .eq('farmer_id', farmer_id)\
            .order('created_at', desc=True)\
            .execute()

        data = rows.data if rows.data else []
        headers = ['id','crop_type','status','estimated_weight','harvest_date','storage_location','created_at','current_risk_level','notes']

        output = io.StringIO()
        writer = csv.writer(output, quoting=csv.QUOTE_MINIMAL)
        writer.writerow(headers)

        for item in data:
            row = [item.get(h, '') for h in headers]
            writer.writerow(row)

        csv_text = output.getvalue()
        output.close()

        bom = '\ufeff'
        response = make_response(bom + csv_text)
        response.headers['Content-Type'] = 'text/csv; charset=utf-8'
        from datetime import datetime
        date = datetime.utcnow().strftime('%Y-%m-%d')
        response.headers['Content-Disposition'] = f'attachment; filename=batches-{date}.csv'
        return response

    except Exception as e:
        print(f"Error exporting CSV: {e}")
        return jsonify({'error': str(e)}), 500


@api_bp.route('/api/export/loss-events')
def export_loss_events_csv():
    """Export loss/damage events as CSV"""
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401

    try:
        import csv
        import io
        from flask import make_response
        
        supabase = get_supabase()
        farmer_id = session['user_id']

        # Get all loss events for this farmer
        loss_result = supabase.table('loss_events')\
            .select('*')\
            .eq('farmer_id', farmer_id)\
            .order('recorded_at', desc=True)\
            .execute()

        data = loss_result.data if loss_result.data else []
        
        # Get crop details for each loss event
        enriched_data = []
        for loss_event in data:
            crop_id = loss_event.get('crop_batch_id')
            crop_result = supabase.table('crop_batches')\
                .select('crop_type')\
                .eq('id', crop_id)\
                .single()\
                .execute()
            
            crop_type = crop_result.data.get('crop_type', 'N/A') if crop_result.data else 'N/A'
            enriched_data.append({
                **loss_event,
                'crop_type': crop_type
            })
        
        headers = ['crop_batch_id', 'crop_type', 'loss_percentage', 'loss_reason', 'recorded_at']

        output = io.StringIO()
        writer = csv.writer(output, quoting=csv.QUOTE_MINIMAL)
        writer.writerow(headers)

        for item in enriched_data:
            row = [item.get(h, '') for h in headers]
            writer.writerow(row)

        csv_text = output.getvalue()
        output.close()

        bom = '\ufeff'
        response = make_response(bom + csv_text)
        response.headers['Content-Type'] = 'text/csv; charset=utf-8'
        from datetime import datetime
        date = datetime.utcnow().strftime('%Y-%m-%d')
        response.headers['Content-Disposition'] = f'attachment; filename=loss-events-{date}.csv'
        return response

    except Exception as e:
        print(f"Error exporting loss events: {e}")
        return jsonify({'error': str(e)}), 500


# ==================== LOSS TRACKING ENDPOINTS ====================

@api_bp.route('/api/crops/<crop_id>/record-loss', methods=['POST'])
def record_loss(crop_id):
    """Record a loss event for a crop"""
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    try:
        supabase = get_supabase()
        farmer_id = session['user_id']
        data = request.get_json()
        
        # Verify crop ownership
        crop_result = supabase.table('crop_batches')\
            .select('*')\
            .eq('id', crop_id)\
            .eq('farmer_id', farmer_id)\
            .single()\
            .execute()
        
        if not crop_result.data:
            return jsonify({'error': 'Crop not found'}), 404
        
        crop = crop_result.data
        
        # Record loss event
        loss_data = {
            'farmer_id': farmer_id,
            'crop_batch_id': crop_id,
            'loss_percentage': float(data.get('loss_percentage', 0)),
            'loss_reason': data.get('loss_reason', 'Not specified'),
            'recorded_at': datetime.utcnow().isoformat()
        }
        
        loss_result = supabase.table('loss_events')\
            .insert(loss_data)\
            .execute()
        
        if loss_result.data:
            return jsonify({
                'success': True,
                'loss_event': loss_result.data[0]
            })
        else:
            return jsonify({'error': 'Failed to record loss'}), 500
    
    except Exception as e:
        print(f"Error recording loss: {e}")
        return jsonify({'error': str(e)}), 500


@api_bp.route('/api/crops/<crop_id>/loss-history')
def get_loss_history(crop_id):
    """Get loss history for a crop"""
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    try:
        supabase = get_supabase()
        farmer_id = session['user_id']
        
        # Verify crop ownership
        crop_result = supabase.table('crop_batches')\
            .select('*')\
            .eq('id', crop_id)\
            .eq('farmer_id', farmer_id)\
            .single()\
            .execute()
        
        if not crop_result.data:
            return jsonify({'error': 'Crop not found'}), 404
        
        # Get all loss events for this crop
        loss_result = supabase.table('loss_events')\
            .select('*')\
            .eq('crop_batch_id', crop_id)\
            .execute()
        
        return jsonify({
            'crop_id': crop_id,
            'loss_events': loss_result.data if loss_result.data else [],
            'total_loss_percentage': crop_result.data.get('loss_percentage', 0)
        })
    
    except Exception as e:
        print(f"Error fetching loss history: {e}")
        return jsonify({'error': str(e)}), 500


@api_bp.route('/api/crops/<crop_id>/update-actual-weight', methods=['POST'])
def update_actual_weight(crop_id):
    """Update actual weight when completing batch and calculate loss"""
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    try:
        supabase = get_supabase()
        farmer_id = session['user_id']
        data = request.get_json()
        
        # Verify crop ownership
        crop_result = supabase.table('crop_batches')\
            .select('*')\
            .eq('id', crop_id)\
            .eq('farmer_id', farmer_id)\
            .single()\
            .execute()
        
        if not crop_result.data:
            return jsonify({'error': 'Crop not found'}), 404
        
        crop = crop_result.data
        estimated_weight = crop.get('estimated_weight', 0)
        actual_weight = float(data.get('actual_weight', 0))
        
        # Calculate loss percentage
        if estimated_weight > 0:
            loss_percentage = max(0, ((estimated_weight - actual_weight) / estimated_weight) * 100)
        else:
            loss_percentage = 0
        
        # Update crop batch
        update_result = supabase.table('crop_batches')\
            .update({
                'actual_weight': actual_weight,
                'status': 'completed'
            })\
            .eq('id', crop_id)\
            .execute()
        
        # Record loss event
        if loss_percentage > 0:
            loss_data = {
                'farmer_id': farmer_id,
                'crop_batch_id': crop_id,
                'loss_percentage': round(loss_percentage, 2),
                'loss_reason': 'Actual weight difference',
                'recorded_at': datetime.utcnow().isoformat()
            }
            supabase.table('loss_events')\
                .insert(loss_data)\
                .execute()
        
        return jsonify({
            'success': True,
            'estimated_weight': estimated_weight,
            'actual_weight': actual_weight,
            'loss_percentage': round(loss_percentage, 2),
            'loss_kg': round(estimated_weight - actual_weight, 2)
        })
    
    except Exception as e:
        print(f"Error updating actual weight: {e}")
        return jsonify({'error': str(e)}), 500


@api_bp.route('/api/loss-reasons')
def get_loss_reasons():
    """Get common loss reasons for dropdown"""
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    reasons = [
        'মোল্ড/ছত্রাক সংক্রমণ (Mold/Fungal infection)',
        'ইঁদুর/কীটপতঙ্গ (Rodent/Pest damage)',
        'আর্দ্রতা ক্ষতি (Moisture damage)',
        'তাপমাত্রা ক্ষতি (Temperature damage)',
        'যান্ত্রিক ক্ষতি (Mechanical damage)',
        'চুরি/হারানো (Theft/Loss)',
        'অন্যান্য (Other)'
    ]
    
    return jsonify({'reasons': reasons})
