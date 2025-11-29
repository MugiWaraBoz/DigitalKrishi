from flask import Blueprint, render_template, session, redirect, url_for, flash

from config.gemini_config import get_gemini_client, get_default_gemini_model

gemini_bp = Blueprint('gemini', __name__)


@gemini_bp.route('/ai-helper')
def ai_helper():
    """Render the Gemini AI helper dashboard page."""
    if 'user_id' not in session:
        flash("Please login first", 'warning')
        return redirect(url_for('auth.login'))

    return render_template('ai_helper.html')


@gemini_bp.route('/voice')
def voice():
    """Render the voice assistant page. Requires login."""
    if 'user_id' not in session:
        flash("Please login first", 'warning')
        return redirect(url_for('auth.login'))

    return render_template('voice.html')


