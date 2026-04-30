from flask import Blueprint, render_template, redirect, url_for, flash
from flask_login import login_required, current_user
from services.supabase_service import SupabaseService
from utils.decorators import login_required_with_message

dashboard_bp = Blueprint('dashboard', __name__, url_prefix='/dashboard')

@dashboard_bp.route('/')
@login_required_with_message
def index():
    user_data = SupabaseService.get_user_by_id(current_user.id)
    return render_template('dashboard/index.html', user=user_data)

@dashboard_bp.route('/metering')
@login_required_with_message
def metering():
    return render_template('dashboard/metering.html')

@dashboard_bp.route('/analytics')
@login_required_with_message
def analytics():
    return render_template('dashboard/analytics.html')