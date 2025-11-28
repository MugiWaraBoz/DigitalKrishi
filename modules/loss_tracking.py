"""
Loss and Damage Tracking Module

This module handles:
- Loss/damage recording and tracking
- Loss percentage calculations
- Loss reason management
- Historical loss data
- Loss event exports
"""

from datetime import datetime
from .database import get_supabase


def calculate_harvest_loss(estimated_weight, actual_weight):
    """
    Calculate loss percentage from harvest data.
    
    When farmer provides actual harvested weight, we calculate:
    Loss % = (Estimated - Actual) / Estimated * 100
    
    Args:
        estimated_weight (float): Original estimated weight in kg
        actual_weight (float): Actual harvested weight in kg
        
    Returns:
        dict: {
            'loss_percentage': float (0-100),
            'loss_kg': float (amount lost in kg),
            'saved_kg': float (amount saved in kg)
        }
    """
    if estimated_weight <= 0:
        return {
            'loss_percentage': 0,
            'loss_kg': 0,
            'saved_kg': 0
        }
    
    loss_percentage = max(0, ((estimated_weight - actual_weight) / estimated_weight) * 100)
    loss_kg = max(0, estimated_weight - actual_weight)
    saved_kg = max(0, actual_weight)
    
    return {
        'loss_percentage': round(loss_percentage, 2),
        'loss_kg': round(loss_kg, 2),
        'saved_kg': round(saved_kg, 2)
    }


def record_loss_event(farmer_id, crop_batch_id, loss_percentage, loss_reason='Not specified'):
    """
    Record a loss event in the database.
    
    Args:
        farmer_id (str): Farmer's user ID
        crop_batch_id (str): Crop batch ID
        loss_percentage (float): Loss percentage (0-100)
        loss_reason (str): Reason for loss (e.g., 'Disease', 'Weather', 'Storage')
        
    Returns:
        dict: Recorded loss event with ID and timestamp, or None if failed
    """
    try:
        supabase = get_supabase()
        
        loss_data = {
            'farmer_id': farmer_id,
            'crop_batch_id': crop_batch_id,
            'loss_percentage': float(loss_percentage),
            'loss_reason': loss_reason,
            'recorded_at': datetime.utcnow().isoformat()
        }
        
        result = supabase.table('loss_events').insert(loss_data).execute()
        
        if result.data:
            return result.data[0]
        return None
        
    except Exception as e:
        print(f"Error recording loss event: {e}")
        return None


def get_crop_loss_history(crop_batch_id):
    """
    Retrieve all loss events for a specific crop batch.
    
    Args:
        crop_batch_id (str): Crop batch ID
        
    Returns:
        list: Loss events sorted by date (newest first)
    """
    try:
        supabase = get_supabase()
        
        result = supabase.table('loss_events')\
            .select('*')\
            .eq('crop_batch_id', crop_batch_id)\
            .order('recorded_at', desc=True)\
            .execute()
        
        return result.data if result.data else []
        
    except Exception as e:
        print(f"Error fetching loss history: {e}")
        return []


def get_farmer_loss_summary(farmer_id):
    """
    Get loss summary for a farmer (all crops).
    
    Args:
        farmer_id (str): Farmer's user ID
        
    Returns:
        dict: {
            'total_loss_events': int,
            'average_loss_percentage': float,
            'highest_loss_percentage': float,
            'most_common_reason': str,
            'loss_reasons': dict (reason -> count)
        }
    """
    try:
        supabase = get_supabase()
        
        result = supabase.table('loss_events')\
            .select('loss_percentage, loss_reason')\
            .eq('farmer_id', farmer_id)\
            .execute()
        
        if not result.data:
            return {
                'total_loss_events': 0,
                'average_loss_percentage': 0,
                'highest_loss_percentage': 0,
                'most_common_reason': 'None',
                'loss_reasons': {}
            }
        
        data = result.data
        
        # Calculate statistics
        total_events = len(data)
        avg_loss = sum(e.get('loss_percentage', 0) for e in data) / total_events
        max_loss = max(e.get('loss_percentage', 0) for e in data)
        
        # Count reasons
        reason_counts = {}
        for event in data:
            reason = event.get('loss_reason', 'Not specified')
            reason_counts[reason] = reason_counts.get(reason, 0) + 1
        
        most_common = max(reason_counts.items(), key=lambda x: x[1])[0] if reason_counts else 'None'
        
        return {
            'total_loss_events': total_events,
            'average_loss_percentage': round(avg_loss, 2),
            'highest_loss_percentage': round(max_loss, 2),
            'most_common_reason': most_common,
            'loss_reasons': reason_counts
        }
        
    except Exception as e:
        print(f"Error calculating loss summary: {e}")
        return None


def get_loss_reasons():
    """
    Get available loss reason categories.
    
    Returns:
        dict: Reasons grouped by category with Bengali and English labels
    """
    return {
        'Disease': {
            'en': 'Crop Disease',
            'bn': 'ফসলের রোগ'
        },
        'Weather': {
            'en': 'Adverse Weather',
            'bn': 'খারাপ আবহাওয়া'
        },
        'Pest': {
            'en': 'Pest Damage',
            'bn': 'কীটপতঙ্গ দ্বারা ক্ষতি'
        },
        'Storage': {
            'en': 'Storage Problems',
            'bn': 'সংরক্ষণ সমস্যা'
        },
        'Handling': {
            'en': 'Poor Handling',
            'bn': 'খারাপ হ্যান্ডলিং'
        },
        'Spoilage': {
            'en': 'Spoilage/Rot',
            'bn': 'পচন/সড়ন'
        },
        'Unknown': {
            'en': 'Unknown Cause',
            'bn': 'অজানা কারণ'
        }
    }


def export_loss_events_to_csv(farmer_id):
    """
    Prepare loss events data for CSV export.
    
    Args:
        farmer_id (str): Farmer's user ID
        
    Returns:
        tuple: (headers list, data list of dicts) or (None, None) if failed
    """
    try:
        supabase = get_supabase()
        
        # Get all loss events for this farmer
        result = supabase.table('loss_events')\
            .select('*')\
            .eq('farmer_id', farmer_id)\
            .order('recorded_at', desc=True)\
            .execute()
        
        data = result.data if result.data else []
        
        # Enrich with crop type information
        enriched_data = []
        for loss_event in data:
            crop_id = loss_event.get('crop_batch_id')
            try:
                crop_result = supabase.table('crop_batches')\
                    .select('crop_type')\
                    .eq('id', crop_id)\
                    .single()\
                    .execute()
                
                crop_type = crop_result.data.get('crop_type', 'N/A') if crop_result.data else 'N/A'
            except:
                crop_type = 'N/A'
            
            enriched_data.append({
                **loss_event,
                'crop_type': crop_type
            })
        
        headers = ['crop_batch_id', 'crop_type', 'loss_percentage', 'loss_reason', 'recorded_at']
        
        return headers, enriched_data
        
    except Exception as e:
        print(f"Error preparing loss export: {e}")
        return None, None
