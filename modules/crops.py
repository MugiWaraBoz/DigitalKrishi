from flask import Blueprint, render_template, redirect, url_for, flash, session
from modules.database import get_supabase

crops_bp = Blueprint('crops', __name__)

@crops_bp.route('/crop/add', methods=['GET', 'POST'])
def add_crop():
    """Add a new crop batch"""
    from flask import request
    
    if 'user_id' not in session:
        flash("Please login first", 'warning')
        return redirect(url_for('auth.login'))
    
    if request.method == 'POST':
        try:
            supabase = get_supabase()
            if not supabase:
                flash("Database connection failed", 'error')
                return redirect(url_for('crops.add_crop'))
            
            print(f"User {session['user_id']} is adding crop...")
            
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
            
            print(f"Crop data: {crop_data}")
            
            result = supabase.table('crop_batches').insert(crop_data).execute()
            
            print(f"Insert result: {result}")
            
            if result.data:
                flash("✅ Crop batch added successfully!", 'success')
                return redirect(url_for('dashboard'))
            else:
                flash(f"Error adding crop batch: {result}", 'danger')
            
        except Exception as e:
            print(f"Exception in add_crop: {e}")
            flash(f"Error adding crop batch: {str(e)}", 'danger')
    
    return render_template('add_crop.html')


@crops_bp.route('/crop/<crop_id>')
def view_crop(crop_id):
    """View individual crop details with weather advisory"""
    if 'user_id' not in session:
        flash("Please login first", 'warning')
        return redirect(url_for('auth.login'))
    
    try:
        supabase = get_supabase()
        print(f"Fetching crop with ID: {crop_id} (type: {type(crop_id).__name__})")
        
        # Fetch crop details
        crop_result = supabase.table('crop_batches')\
            .select('*')\
            .eq('id', crop_id)\
            .eq('farmer_id', session['user_id'])\
            .single()\
            .execute()
        
        if not crop_result.data:
            print(f"Crop not found for ID: {crop_id}")
            flash("Crop not found", 'warning')
            return redirect(url_for('dashboard'))
        
        crop = crop_result.data
        print(f"Crop loaded: {crop}")
        return render_template('crop_detail.html', crop=crop)
        
    except Exception as e:
        print(f"Error in view_crop: {e}")
        import traceback
        traceback.print_exc()
        flash("Error loading crop details", 'danger')
        return redirect(url_for('dashboard'))
