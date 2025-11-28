"""
Risk Assessment Module

This module handles:
- Risk level calculation from weather data
- Weather-based risk scoring (0-100)
- Risk classification (high, medium, low)
- Agricultural advisories based on current conditions
- Risk mitigation recommendations
"""

from .database import get_supabase


def calculate_risk_level(weather_data):
    """
    Calculate risk level (0-100) from current weather conditions.
    
    Risk factors:
    - Temperature: Too hot (>35°C) or too cold (<10°C) increases risk
    - Humidity: Too high (>80%) increases disease risk, too low (<40%) increases crop stress
    - Rainfall: Heavy rain (>100mm) increases waterlogging risk
    
    Args:
        weather_data (dict): {
            'temperature': float (°C),
            'humidity': float (%),
            'rainfall': float (mm),
            'condition': str (e.g., 'Clear', 'Rainy')
        }
        
    Returns:
        dict: {
            'risk_score': int (0-100),
            'risk_level': str ('low', 'medium', 'high'),
            'factors': list of risk factors,
            'top_concerns': list of top 3 risk factors
        }
    """
    risk_score = 0
    factors = []
    factor_scores = {}
    
    temp = weather_data.get('temperature', 25)
    humidity = weather_data.get('humidity', 60)
    rainfall = weather_data.get('rainfall', 0)
    condition = weather_data.get('condition', 'Clear')
    
    # Temperature risk
    if temp > 35:
        temp_risk = min(30, (temp - 35) * 3)
        factor_scores['High Temperature'] = temp_risk
        factors.append(f"High temperature ({temp}°C)")
    elif temp < 10:
        temp_risk = min(25, (10 - temp) * 2.5)
        factor_scores['Low Temperature'] = temp_risk
        factors.append(f"Low temperature ({temp}°C)")
    else:
        # Ideal temperature range reduces risk
        factor_scores['Temperature'] = max(0, 15 - abs(temp - 25)) / 2
    
    # Humidity risk
    if humidity > 80:
        humidity_risk = min(25, (humidity - 80) * 2)
        factor_scores['High Humidity (Disease Risk)'] = humidity_risk
        factors.append(f"High humidity ({humidity}%) - disease risk")
    elif humidity < 40:
        humidity_risk = min(20, (40 - humidity) * 1.5)
        factor_scores['Low Humidity (Crop Stress)'] = humidity_risk
        factors.append(f"Low humidity ({humidity}%) - drought stress")
    else:
        # Ideal humidity reduces risk
        factor_scores['Humidity'] = max(0, 20 - abs(humidity - 60)) / 3
    
    # Rainfall risk
    if rainfall > 100:
        rainfall_risk = min(30, (rainfall - 100) * 0.2)
        factor_scores['Heavy Rainfall (Waterlogging)'] = rainfall_risk
        factors.append(f"Heavy rainfall ({rainfall}mm) - waterlogging risk")
    elif rainfall > 50:
        rainfall_risk = min(15, (rainfall - 50) * 0.3)
        factor_scores['Moderate Rainfall'] = rainfall_risk
        factors.append(f"Moderate rainfall ({rainfall}mm)")
    else:
        # Light rain is beneficial
        factor_scores['Rainfall'] = max(0, min(10, rainfall / 10))
    
    # Weather condition risk
    if condition in ['Thunderstorm', 'Heavy Rain', 'Hail']:
        factor_scores['Severe Weather'] = 25
        factors.append(f"Severe weather condition: {condition}")
    elif condition in ['Rainy', 'Cloudy']:
        factor_scores['Adverse Condition'] = 10
    
    # Calculate total risk score from factors
    risk_score = sum(factor_scores.values())
    risk_score = min(100, max(0, risk_score))  # Clamp between 0-100
    
    # Classify risk level
    if risk_score >= 60:
        risk_level = 'high'
    elif risk_score >= 35:
        risk_level = 'medium'
    else:
        risk_level = 'low'
    
    # Get top 3 concerns
    sorted_factors = sorted(factor_scores.items(), key=lambda x: x[1], reverse=True)
    top_concerns = [f[0] for f in sorted_factors[:3]]
    
    return {
        'risk_score': round(risk_score),
        'risk_level': risk_level,
        'factors': factors,
        'top_concerns': top_concerns,
        'factor_breakdown': dict(sorted_factors)
    }


def get_weather_advisory(crop_type, weather_data, risk_info):
    """
    Generate crop-specific weather advisory and recommendations.
    
    Args:
        crop_type (str): Type of crop (e.g., 'Rice', 'Wheat', 'Vegetables')
        weather_data (dict): Current weather conditions
        risk_info (dict): Risk assessment result from calculate_risk_level()
        
    Returns:
        dict: {
            'advisory_title': str,
            'risk_level': str,
            'current_conditions': str,
            'recommendations': list,
            'critical_actions': list (if risk is high),
            'monitoring_notes': list
        }
    """
    risk_level = risk_info.get('risk_level', 'medium')
    temp = weather_data.get('temperature', 25)
    humidity = weather_data.get('humidity', 60)
    rainfall = weather_data.get('rainfall', 0)
    top_concerns = risk_info.get('top_concerns', [])
    
    # Crop-specific thresholds
    crop_thresholds = {
        'rice': {'temp_min': 15, 'temp_max': 35, 'humidity_ideal': 70},
        'wheat': {'temp_min': 5, 'temp_max': 30, 'humidity_ideal': 50},
        'vegetables': {'temp_min': 15, 'temp_max': 30, 'humidity_ideal': 65},
        'maize': {'temp_min': 8, 'temp_max': 32, 'humidity_ideal': 60},
    }
    
    crop_lower = crop_type.lower()
    thresholds = crop_thresholds.get(crop_lower, crop_thresholds['vegetables'])
    
    recommendations = []
    critical_actions = []
    monitoring_notes = []
    
    # Generate recommendations based on risk factors
    if 'High Temperature' in top_concerns:
        recommendations.append('Increase irrigation frequency to prevent water stress')
        recommendations.append('Apply mulch to maintain soil moisture and reduce temperature')
        if temp > 40:
            critical_actions.append('URGENT: Provide emergency irrigation - extreme heat detected')
            monitoring_notes.append('Monitor for heat-induced crop wilting every 2-3 hours')
    
    if 'Low Temperature' in top_concerns:
        recommendations.append('Reduce irrigation to prevent frost damage')
        recommendations.append('Apply protective measures (straw, covers) if frost expected')
        if temp < 5:
            critical_actions.append('URGENT: Install frost protection measures immediately')
    
    if 'High Humidity (Disease Risk)' in top_concerns:
        recommendations.append('Ensure proper drainage to reduce waterlogging')
        recommendations.append('Increase air circulation by pruning excess foliage')
        recommendations.append('Monitor for fungal diseases and apply preventive spray if needed')
        recommendations.append('Avoid overhead irrigation - use drip irrigation instead')
        if humidity > 85:
            critical_actions.append('URGENT: High disease risk - apply fungicide preventively')
    
    if 'Low Humidity (Crop Stress)' in top_concerns:
        recommendations.append('Increase irrigation to prevent drought stress')
        recommendations.append('Apply mulch to conserve soil moisture')
        monitoring_notes.append('Check soil moisture at least once daily')
    
    if 'Heavy Rainfall (Waterlogging)' in top_concerns:
        recommendations.append('Ensure drainage channels are clear and functioning')
        recommendations.append('Check for standing water in field - drain if present')
        critical_actions.append('URGENT: Waterlogging detected - monitor crop health closely')
        if rainfall > 150:
            critical_actions.append('Consider immediate drainage intervention if water levels rising')
        monitoring_notes.append('Watch for root rot and fungal infection symptoms')
    
    if 'Moderate Rainfall' in top_concerns and rainfall > 0:
        monitoring_notes.append(f'Optimal rainfall ({rainfall}mm) - continue normal monitoring')
    
    if 'Severe Weather' in top_concerns:
        critical_actions.append('URGENT: Severe weather approaching - take protective measures')
        recommendations.append('Secure plants and protective structures')
        recommendations.append('Remove weak or damaged branches')
        monitoring_notes.append('Monitor weather updates every hour')
    
    # Add general monitoring based on risk level
    if risk_level == 'high':
        monitoring_notes.append('HIGH RISK: Monitor crop health every 4-6 hours')
        monitoring_notes.append('Document any damage or changes in crop condition')
    elif risk_level == 'medium':
        monitoring_notes.append('MEDIUM RISK: Monitor crop health daily')
    else:
        monitoring_notes.append('Conditions favorable - continue normal management')
    
    # Default advisory if no specific concerns
    if not recommendations:
        recommendations = [
            'Maintain regular irrigation schedule',
            'Continue standard crop management practices',
            'Monitor for any signs of pest or disease'
        ]
    
    return {
        'advisory_title': f'Weather Advisory for {crop_type}',
        'risk_level': risk_level.upper(),
        'current_conditions': f'Temp: {temp}°C, Humidity: {humidity}%, Rainfall: {rainfall}mm',
        'recommendations': recommendations,
        'critical_actions': critical_actions,
        'monitoring_notes': monitoring_notes
    }


def update_crop_risk_level(crop_batch_id, weather_data):
    """
    Update a crop's risk level in the database based on current weather.
    
    Args:
        crop_batch_id (str): Crop batch ID
        weather_data (dict): Current weather conditions
        
    Returns:
        bool: True if updated successfully, False otherwise
    """
    try:
        risk_info = calculate_risk_level(weather_data)
        supabase = get_supabase()
        
        # Update crop_batches table with current risk level
        result = supabase.table('crop_batches')\
            .update({
                'current_risk_level': risk_info['risk_level'],
                'risk_score': risk_info['risk_score']
            })\
            .eq('id', crop_batch_id)\
            .execute()
        
        return bool(result.data)
        
    except Exception as e:
        print(f"Error updating crop risk level: {e}")
        return False


def get_crop_risk_history(crop_batch_id, days=7):
    """
    Get risk assessment history for a crop over specified days.
    
    Args:
        crop_batch_id (str): Crop batch ID
        days (int): Number of days to retrieve history for
        
    Returns:
        list: Risk history entries (if tracking table exists)
    """
    try:
        supabase = get_supabase()
        
        # Note: This requires a risk_history table to exist
        # For now, return empty as we track risk in crop_batches
        result = supabase.table('crop_batches')\
            .select('current_risk_level, risk_score')\
            .eq('id', crop_batch_id)\
            .execute()
        
        return result.data if result.data else []
        
    except Exception as e:
        print(f"Error fetching risk history: {e}")
        return []
