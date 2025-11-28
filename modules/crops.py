from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify, make_response
import csv
import io
from modules.database import get_supabase

crops_bp = Blueprint('crops', __name__)

@crops_bp.route('/crop/add', methods=['GET', 'POST'])
def add_crop():
    if 'user_id' not in session:
        flash("Please login first", 'warning')
        return redirect(url_for('auth.login'))
    
    if request.method == 'POST':
        try:
            supabase = get_supabase()
            if not supabase:
                flash("Database connection failed", 'error')
                return redirect(url_for('crops.add_crop'))
            
            print(f"User {session['user_id']} is adding crop...")  # Debug
            
            crop_data = {
                'farmer_id': session['user_id'],
                'crop_type': request.form['crop_type'],
                'estimated_weight': float(request.form['estimated_weight']),
                'harvest_date': request.form['harvest_date'],
                'storage_location': request.form['storage_location'],
                'storage_type': request.form['storage_type'],
                'notes': request.form.get('notes', ''),
                'status': 'active',
                'current_risk_level': 'low'
            }
            
            print(f"Crop data: {crop_data}")  # Debug
            
            result = supabase.table('crop_batches').insert(crop_data).execute()
            
            print(f"Insert result: {result}")  # Debug
            
            if result.data:
                flash("✅ Crop batch added successfully!", 'success')
                return redirect(url_for('dashboard'))
            else:
                flash(f"Error adding crop batch: {result}", 'danger')
            
        except Exception as e:
            print(f"Exception in add_crop: {e}")  # Debug
            flash(f"Error adding crop batch: {str(e)}", 'danger')
    
    return render_template('add_crop.html')

@crops_bp.route('/api/crops/active')
def active_crops():
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    try:
        supabase = get_supabase()
        farmer_id = session['user_id']
        
        print(f"Fetching crops for user: {farmer_id}")  # Debug
        
        crops = supabase.table('crop_batches')\
            .select('*')\
            .eq('farmer_id', farmer_id)\
            .eq('status', 'active')\
            .execute()
        
        print(f"Found crops: {crops.data}")  # Debug
        
        return jsonify(crops.data if crops.data else [])
        
    except Exception as e:
        print(f"Error in active_crops: {e}")  # Debug
        return jsonify({'error': str(e)}), 500

@crops_bp.route('/api/dashboard/stats')
def dashboard_stats():
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    try:
        supabase = get_supabase()
        farmer_id = session['user_id']
        
        print(f"Fetching stats for user: {farmer_id}")  # Debug
        
        # Get all active batches (we'll count them ourselves)
        active_batches_result = supabase.table('crop_batches')\
            .select('*')\
            .eq('farmer_id', farmer_id)\
            .eq('status', 'active')\
            .execute()
        
        # Count the batches
        active_count = len(active_batches_result.data) if active_batches_result.data else 0
        
        # Calculate total weight from the same result
        total_weight = sum(batch['estimated_weight'] for batch in active_batches_result.data) if active_batches_result.data else 0
        
        stats = {
            'active_batches': active_count,
            'total_weight': round(total_weight, 2),
            'saved_food': round(total_weight * 0.85, 2),
            'success_rate': 85
        }
        
        print(f"Stats: {stats}")  # Debug
        
        return jsonify(stats)
        
    except Exception as e:
        print(f"Error in dashboard_stats: {e}")  # Debug
        return jsonify({'error': str(e)}), 500

@crops_bp.route('/api/crops/all')
def all_crops():
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    try:
        supabase = get_supabase()
        farmer_id = session['user_id']
        
        print(f"🔍 Fetching all crops for user: {farmer_id}")  # Debug
        
        crops = supabase.table('crop_batches')\
            .select('*')\
            .eq('farmer_id', farmer_id)\
            .order('created_at', desc=True)\
            .execute()
        
        print(f"📦 Found {len(crops.data) if crops.data else 0} crops")  # Debug
        
        if crops.data:
            print(f"📋 Crop data: {crops.data}")  # Debug
        
        return jsonify(crops.data if crops.data else [])
        
    except Exception as e:
        print(f"❌ Error in all_crops: {e}")  # Debug
        return jsonify({'error': str(e)}), 500


# Update batch status to completed
@crops_bp.route('/api/crops/<batch_id>/complete', methods=['POST'])
def complete_crop(batch_id):
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401

    try:
        supabase = get_supabase()
        farmer_id = session['user_id']

        # Fetch the batch to verify ownership
        result = supabase.table('crop_batches').select('*').eq('id', batch_id).execute()
        if not result.data:
            return jsonify({'error': 'Batch not found'}), 404

        batch = result.data[0]
        if batch.get('farmer_id') != farmer_id:
            return jsonify({'error': 'Forbidden'}), 403

        update = supabase.table('crop_batches').update({'status': 'completed'}).eq('id', batch_id).execute()
        if update.data:
            return jsonify({'success': True, 'batch': update.data[0]})
        else:
            return jsonify({'error': 'Failed to update batch'}), 500

    except Exception as e:
        print(f"Error completing batch: {e}")
        return jsonify({'error': str(e)}), 500


# Reactivate a completed batch
@crops_bp.route('/api/crops/<batch_id>/reactivate', methods=['POST'])
def reactivate_crop(batch_id):
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401

    try:
        supabase = get_supabase()
        farmer_id = session['user_id']

        result = supabase.table('crop_batches').select('*').eq('id', batch_id).execute()
        if not result.data:
            return jsonify({'error': 'Batch not found'}), 404

        batch = result.data[0]
        if batch.get('farmer_id') != farmer_id:
            return jsonify({'error': 'Forbidden'}), 403

        update = supabase.table('crop_batches').update({'status': 'active'}).eq('id', batch_id).execute()
        if update.data:
            return jsonify({'success': True, 'batch': update.data[0]})
        else:
            return jsonify({'error': 'Failed to update batch'}), 500

    except Exception as e:
        print(f"Error reactivating batch: {e}")
        return jsonify({'error': str(e)}), 500


# Delete a batch
@crops_bp.route('/api/crops/<batch_id>', methods=['DELETE'])
def delete_crop(batch_id):
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401

    try:
        supabase = get_supabase()
        farmer_id = session['user_id']

        # Verify ownership
        result = supabase.table('crop_batches').select('*').eq('id', batch_id).execute()
        if not result.data:
            return jsonify({'error': 'Batch not found'}), 404

        batch = result.data[0]
        if batch.get('farmer_id') != farmer_id:
            return jsonify({'error': 'Forbidden'}), 403

        deleted = supabase.table('crop_batches').delete().eq('id', batch_id).execute()
        if deleted.data:
            return jsonify({'success': True})
        else:
            return jsonify({'error': 'Failed to delete batch'}), 500

    except Exception as e:
        print(f"Error deleting batch: {e}")
        return jsonify({'error': str(e)}), 500

# Debug route to check all crops in database
@crops_bp.route('/api/debug/all-crops')
def debug_all_crops():
    try:
        supabase = get_supabase()
        
        # Get ALL crops from database (no user filter)
        result = supabase.table('crop_batches').select('*').execute()
        
        return jsonify({
            'total_crops': len(result.data) if result.data else 0,
            'crops': result.data if result.data else []
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Debug route to check current user's crops
@crops_bp.route('/api/debug/my-crops')
def debug_my_crops():
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    try:
        supabase = get_supabase()
        farmer_id = session['user_id']
        
        # Get current user's crops
        result = supabase.table('crop_batches')\
            .select('*')\
            .eq('farmer_id', farmer_id)\
            .execute()
        
        return jsonify({
            'user_id': farmer_id,
            'total_my_crops': len(result.data) if result.data else 0,
            'my_crops': result.data if result.data else []
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# Export current user's batches as CSV
@crops_bp.route('/api/crops/export')
def export_crops_csv():
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401

    try:
        supabase = get_supabase()
        farmer_id = session['user_id']

        rows = supabase.table('crop_batches')\
            .select('*')\
            .eq('farmer_id', farmer_id)\
            .order('created_at', desc=True)\
            .execute()

        data = rows.data if rows.data else []

        # Define CSV headers and ordering
        headers = ['id','crop_type','status','estimated_weight','loss_percentage','harvest_date','storage_location','created_at','current_risk_level','notes']

        output = io.StringIO()
        writer = csv.writer(output, quoting=csv.QUOTE_MINIMAL)

        # Write BOM for Excel compatibility and header row
        # We'll return bytes with UTF-8 BOM in response later
        writer.writerow(headers)

        for item in data:
            row = [item.get(h, '') for h in headers]
            writer.writerow(row)

        csv_text = output.getvalue()
        output.close()

        # Prepare response with UTF-8 BOM so Excel recognizes UTF-8
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