from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, session
from flask_login import login_required, current_user
from services.supabase_service import SupabaseService
from utils.decorators import admin_required
from datetime import datetime, timedelta
import json
import uuid

admin_bp = Blueprint('admin', __name__, url_prefix='/admin-portal-2024')

# ============================================
# BEFORE REQUEST - Verify Admin Access
# ============================================
@admin_bp.before_request
def verify_admin_access():
    """Verify admin access before each request with multiple security checks"""
    
    # Check if user is authenticated
    if not current_user.is_authenticated:
        session['next_url'] = request.url
        flash('Please login to access the admin panel.', 'warning')
        return redirect(url_for('auth.login'))
    
    # Check if user is admin
    if not current_user.is_admin:
        flash('Access denied. This area is restricted to administrators only.', 'danger')
        return redirect(url_for('dashboard.index'))
    
    # Log admin activity (optional)
    admin_activity_log(current_user.id, request.endpoint, request.method)

def admin_activity_log(admin_id, endpoint, method):
    """Log admin activities for audit trail"""
    try:
        log_data = {
            'admin_id': admin_id,
            'action': f"{method} {endpoint}",
            'ip_address': request.remote_addr,
            'user_agent': request.user_agent.string,
            'timestamp': datetime.now().isoformat()
        }
        # Store in database if needed
        # SupabaseService.get_client().table('admin_logs').insert(log_data).execute()
    except Exception as e:
        pass  # Don't block if logging fails

# ============================================
# DASHBOARD ROUTES
# ============================================

@admin_bp.route('/')
@login_required
def index():
    """Admin dashboard with system overview"""
    try:
        stats = get_system_statistics()
        recent_applications = get_recent_applications()
        recent_users = get_recent_users()
        recent_alerts = get_recent_alerts()
        
        return render_template('admin/index.html',
                             stats=stats,
                             recent_applications=recent_applications,
                             recent_users=recent_users,
                             recent_alerts=recent_alerts)
    except Exception as e:
        flash(f'Error loading dashboard: {str(e)}', 'danger')
        return render_template('admin/index.html', 
                             stats={}, 
                             recent_applications={'data': []}, 
                             recent_users={'data': []})

@admin_bp.route('/api/stats')
@login_required
def api_stats():
    """API endpoint for real-time stats"""
    try:
        stats = get_system_statistics()
        return jsonify({'success': True, 'data': stats})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# ============================================
# APPLICATION MANAGEMENT ROUTES
# ============================================

@admin_bp.route('/applications')
@login_required
def applications():
    """View all net metering applications with filters"""
    try:
        status_filter = request.args.get('status', 'all')
        disco_filter = request.args.get('disco', 'all')
        search = request.args.get('search', '')
        page = int(request.args.get('page', 1))
        per_page = 20
        
        applications = get_all_applications(
            status=status_filter, 
            disco=disco_filter, 
            search=search,
            page=page,
            per_page=per_page
        )
        
        # Get counts for sidebar
        status_counts = get_application_status_counts()
        disco_list = get_disco_list()
        
        return render_template('admin/applications.html',
                             applications=applications,
                             current_status=status_filter,
                             current_disco=disco_filter,
                             search=search,
                             page=page,
                             status_counts=status_counts,
                             disco_list=disco_list)
    except Exception as e:
        flash(f'Error loading applications: {str(e)}', 'danger')
        return render_template('admin/applications.html', 
                             applications={'data': []}, 
                             current_status='all',
                             current_disco='all')

@admin_bp.route('/applications/<application_id>')
@login_required
def application_detail(application_id):
    """View application details"""
    try:
        application = get_application_by_id(application_id)
        
        if not application or not application.data:
            flash('Application not found.', 'danger')
            return redirect(url_for('admin.applications'))
        
        documents = get_application_documents(application_id)
        history = get_application_status_history(application_id)
        user_details = get_user_details(application.data.get('user_id'))
        related_applications = get_user_applications(application.data.get('user_id'))
        
        return render_template('admin/application_detail.html',
                             application=application,
                             documents=documents,
                             history=history,
                             user_details=user_details,
                             related_applications=related_applications)
    except Exception as e:
        flash(f'Error loading application details: {str(e)}', 'danger')
        return redirect(url_for('admin.applications'))

@admin_bp.route('/applications/<application_id>/update-status', methods=['POST'])
@login_required
def update_application_status(application_id):
    """Update application status with validation"""
    try:
        status = request.form.get('status')
        step = request.form.get('step')
        notes = request.form.get('notes', '')
        notify_user = request.form.get('notify_user') == 'on'
        
        # Validate status
        valid_statuses = ['draft', 'submitted', 'survey_scheduled', 'demand_notice', 
                         'inspection', 'approved', 'rejected']
        if status not in valid_statuses:
            flash('Invalid status provided.', 'danger')
            return redirect(url_for('admin.application_detail', application_id=application_id))
        
        # Get current application
        current_app = SupabaseService.get_client().table('net_metering_applications') \
            .select('*') \
            .eq('id', application_id) \
            .single() \
            .execute()
        
        if not current_app.data:
            flash('Application not found.', 'danger')
            return redirect(url_for('admin.applications'))
        
        # Prepare update data
        update_data = {
            'application_status': status,
            'updated_at': datetime.now().isoformat()
        }
        
        if step:
            update_data['current_step'] = int(step)
            
            # Update specific step timestamps
            step_dates = {
                '1': 'submitted_at',
                '2': 'survey_date',
                '3': 'demand_notice_date',
                '4': 'inspection_date',
                '5': 'green_meter_date'
            }
            
            if step in step_dates:
                update_data[step_dates[step]] = datetime.now().isoformat()
        
        # Update status history
        history = current_app.data.get('status_history', [])
        if isinstance(history, str):
            history = json.loads(history)
        
        history_entry = {
            'status': status,
            'step': step,
            'notes': notes,
            'updated_by': current_user.id,
            'updated_by_name': current_user.full_name,
            'timestamp': datetime.now().isoformat()
        }
        history.append(history_entry)
        update_data['status_history'] = json.dumps(history)
        
        if notes:
            # Append notes
            existing_notes = current_app.data.get('notes', '')
            update_data['notes'] = f"{existing_notes}\n[{datetime.now().strftime('%Y-%m-%d %H:%M')}] {current_user.full_name}: {notes}"
        
        # Update database
        SupabaseService.get_client().table('net_metering_applications') \
            .update(update_data) \
            .eq('id', application_id) \
            .execute()
        
        # Create alert for user if requested
        if notify_user:
            user_id = current_app.data.get('user_id')
            create_user_notification(user_id, status, application_id)
        
        # Log admin action
        log_admin_action('update_application_status', {
            'application_id': application_id,
            'old_status': current_app.data.get('application_status'),
            'new_status': status
        })
        
        flash('Application status updated successfully.', 'success')
        
    except Exception as e:
        flash(f'Failed to update application status: {str(e)}', 'danger')
    
    return redirect(url_for('admin.application_detail', application_id=application_id))

@admin_bp.route('/applications/<application_id>/assign', methods=['POST'])
@login_required
def assign_application(application_id):
    """Assign application to a DISCO officer"""
    try:
        officer_name = request.form.get('officer_name')
        officer_contact = request.form.get('officer_contact')
        survey_date = request.form.get('survey_date')
        
        update_data = {
            'assigned_officer': officer_name,
            'officer_contact': officer_contact,
            'updated_at': datetime.now().isoformat()
        }
        
        if survey_date:
            update_data['survey_date'] = survey_date
        
        SupabaseService.get_client().table('net_metering_applications') \
            .update(update_data) \
            .eq('id', application_id) \
            .execute()
        
        flash('Application assigned successfully.', 'success')
    except Exception as e:
        flash(f'Failed to assign application: {str(e)}', 'danger')
    
    return redirect(url_for('admin.application_detail', application_id=application_id))

@admin_bp.route('/applications/bulk-update', methods=['POST'])
@login_required
def bulk_update_applications():
    """Bulk update application statuses"""
    try:
        application_ids = request.form.getlist('application_ids[]')
        new_status = request.form.get('new_status')
        notes = request.form.get('notes', '')
        
        if not application_ids or not new_status:
            flash('Please select applications and a status.', 'danger')
            return redirect(url_for('admin.applications'))
        
        for app_id in application_ids:
            update_data = {
                'application_status': new_status,
                'notes': notes,
                'updated_at': datetime.now().isoformat()
            }
            
            SupabaseService.get_client().table('net_metering_applications') \
                .update(update_data) \
                .eq('id', app_id) \
                .execute()
        
        flash(f'Successfully updated {len(application_ids)} applications.', 'success')
    except Exception as e:
        flash(f'Bulk update failed: {str(e)}', 'danger')
    
    return redirect(url_for('admin.applications'))

@admin_bp.route('/applications/<application_id>/documents/verify', methods=['POST'])
@login_required
def verify_document(application_id):
    """Verify or reject uploaded documents"""
    try:
        document_id = request.form.get('document_id')
        action = request.form.get('action')  # 'verify' or 'reject'
        rejection_reason = request.form.get('rejection_reason', '')
        
        if action == 'verify':
            update_data = {
                'is_verified': True,
                'verified_by': current_user.id,
                'verified_at': datetime.now().isoformat()
            }
            flash('Document verified successfully.', 'success')
        elif action == 'reject':
            update_data = {
                'is_verified': False,
                'verified_by': current_user.id,
                'rejection_reason': rejection_reason,
                'verified_at': datetime.now().isoformat()
            }
            flash('Document rejected.', 'warning')
        else:
            flash('Invalid action.', 'danger')
            return redirect(url_for('admin.application_detail', application_id=application_id))
        
        SupabaseService.get_client().table('documents') \
            .update(update_data) \
            .eq('id', document_id) \
            .execute()
        
    except Exception as e:
        flash(f'Document verification failed: {str(e)}', 'danger')
    
    return redirect(url_for('admin.application_detail', application_id=application_id))

# ============================================
# USER MANAGEMENT ROUTES
# ============================================

@admin_bp.route('/users')
@login_required
def users():
    """View all users with filters"""
    try:
        search = request.args.get('search', '')
        status_filter = request.args.get('status', 'all')
        role_filter = request.args.get('role', 'all')
        disco_filter = request.args.get('disco', 'all')
        page = int(request.args.get('page', 1))
        
        users = get_all_users(
            search=search, 
            status=status_filter, 
            role=role_filter,
            disco=disco_filter,
            page=page
        )
        
        # Get statistics
        user_stats = get_user_statistics()
        
        return render_template('admin/users.html',
                             users=users,
                             search=search,
                             current_status=status_filter,
                             current_role=role_filter,
                             current_disco=disco_filter,
                             page=page,
                             user_stats=user_stats)
    except Exception as e:
        flash(f'Error loading users: {str(e)}', 'danger')
        return render_template('admin/users.html', users={'data': []})

@admin_bp.route('/users/<user_id>')
@login_required
def user_detail(user_id):
    """View detailed user information"""
    try:
        user = SupabaseService.get_user_by_id(user_id)
        
        if not user:
            flash('User not found.', 'danger')
            return redirect(url_for('admin.users'))
        
        applications = get_user_all_applications(user_id)
        readings = get_user_power_readings(user_id)
        alerts = get_user_alerts(user_id)
        savings = get_user_savings(user_id)
        activity_log = get_user_activity_log(user_id)
        
        return render_template('admin/user_detail.html',
                             user=user,
                             applications=applications,
                             readings=readings,
                             alerts=alerts,
                             savings=savings,
                             activity_log=activity_log)
    except Exception as e:
        flash(f'Error loading user details: {str(e)}', 'danger')
        return redirect(url_for('admin.users'))

@admin_bp.route('/users/<user_id>/toggle-status', methods=['POST'])
@login_required
def toggle_user_status(user_id):
    """Activate or deactivate a user"""
    try:
        if user_id == current_user.id:
            flash('You cannot modify your own account status.', 'danger')
            return redirect(url_for('admin.user_detail', user_id=user_id))
        
        user = SupabaseService.get_user_by_id(user_id)
        
        if not user:
            flash('User not found.', 'danger')
            return redirect(url_for('admin.users'))
        
        new_status = not user.is_active
        
        SupabaseService.get_client().table('profiles') \
            .update({
                'is_active': new_status,
                'updated_at': datetime.now().isoformat()
            }) \
            .eq('id', user_id) \
            .execute()
        
        # Log action
        log_admin_action('toggle_user_status', {
            'user_id': user_id,
            'new_status': new_status
        })
        
        status_text = 'activated' if new_status else 'deactivated'
        flash(f'User {status_text} successfully.', 'success')
        
    except Exception as e:
        flash(f'Failed to update user status: {str(e)}', 'danger')
    
    return redirect(url_for('admin.user_detail', user_id=user_id))

@admin_bp.route('/users/<user_id>/toggle-admin', methods=['POST'])
@login_required
def toggle_admin_status(user_id):
    """Toggle admin privileges"""
    try:
        if user_id == current_user.id:
            flash('You cannot modify your own admin status.', 'danger')
            return redirect(url_for('admin.user_detail', user_id=user_id))
        
        user = SupabaseService.get_user_by_id(user_id)
        
        if not user:
            flash('User not found.', 'danger')
            return redirect(url_for('admin.users'))
        
        new_admin_status = not user.is_admin
        
        SupabaseService.get_client().table('profiles') \
            .update({
                'is_admin': new_admin_status,
                'updated_at': datetime.now().isoformat()
            }) \
            .eq('id', user_id) \
            .execute()
        
        # Log action
        log_admin_action('toggle_admin_status', {
            'user_id': user_id,
            'new_admin_status': new_admin_status
        })
        
        status_text = 'granted admin privileges' if new_admin_status else 'revoked admin privileges'
        flash(f'Successfully {status_text}.', 'success')
        
    except Exception as e:
        flash(f'Failed to update admin status: {str(e)}', 'danger')
    
    return redirect(url_for('admin.user_detail', user_id=user_id))

@admin_bp.route('/users/<user_id>/update', methods=['POST'])
@login_required
def update_user_details(user_id):
    """Update user details"""
    try:
        update_data = {
            'full_name': request.form.get('full_name'),
            'phone': request.form.get('phone'),
            'address': request.form.get('address'),
            'disco_region': request.form.get('disco_region'),
            'sanctioned_load': float(request.form.get('sanctioned_load', 0)),
            'updated_at': datetime.now().isoformat()
        }
        
        SupabaseService.get_client().table('profiles') \
            .update(update_data) \
            .eq('id', user_id) \
            .execute()
        
        flash('User details updated successfully.', 'success')
    except Exception as e:
        flash(f'Failed to update user: {str(e)}', 'danger')
    
    return redirect(url_for('admin.user_detail', user_id=user_id))

@admin_bp.route('/users/<user_id>/reset-password', methods=['POST'])
@login_required
def reset_user_password(user_id):
    """Send password reset email to user"""
    try:
        # Get user email
        user = SupabaseService.get_user_by_id(user_id)
        
        if not user:
            flash('User not found.', 'danger')
            return redirect(url_for('admin.users'))
        
        # Send password reset via Supabase Auth
        SupabaseService.get_admin_client().auth.admin.generate_link({
            'type': 'recovery',
            'email': user.email
        })
        
        flash(f'Password reset link sent to {user.email}.', 'success')
    except Exception as e:
        flash(f'Failed to send reset link: {str(e)}', 'danger')
    
    return redirect(url_for('admin.user_detail', user_id=user_id))

@admin_bp.route('/users/<user_id>/delete', methods=['POST'])
@login_required
def delete_user(user_id):
    """Delete user account (soft delete)"""
    try:
        if user_id == current_user.id:
            flash('You cannot delete your own account.', 'danger')
            return redirect(url_for('admin.user_detail', user_id=user_id))
        
        # Soft delete - just deactivate
        SupabaseService.get_client().table('profiles') \
            .update({
                'is_active': False,
                'deleted_at': datetime.now().isoformat(),
                'updated_at': datetime.now().isoformat()
            }) \
            .eq('id', user_id) \
            .execute()
        
        # Log action
        log_admin_action('delete_user', {'user_id': user_id})
        
        flash('User account deactivated successfully.', 'success')
    except Exception as e:
        flash(f'Failed to delete user: {str(e)}', 'danger')
    
    return redirect(url_for('admin.users'))

# ============================================
# ANALYTICS ROUTES
# ============================================

@admin_bp.route('/analytics')
@login_required
def analytics():
    """System analytics and reports"""
    try:
        stats = get_detailed_statistics()
        application_stats = get_application_analytics()
        user_analytics = get_user_analytics()
        financial_analytics = get_financial_analytics()
        
        return render_template('admin/analytics.html',
                             stats=stats,
                             application_stats=application_stats,
                             user_analytics=user_analytics,
                             financial_analytics=financial_analytics)
    except Exception as e:
        flash(f'Error loading analytics: {str(e)}', 'danger')
        return render_template('admin/analytics.html')

@admin_bp.route('/api/analytics/applications')
@login_required
def api_application_analytics():
    """API endpoint for application analytics"""
    try:
        period = request.args.get('period', '30d')
        data = get_application_analytics(period)
        return jsonify({'success': True, 'data': data})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@admin_bp.route('/api/analytics/users')
@login_required
def api_user_analytics():
    """API endpoint for user analytics"""
    try:
        period = request.args.get('period', '30d')
        data = get_user_analytics(period)
        return jsonify({'success': True, 'data': data})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# ============================================
# TARIFF MANAGEMENT ROUTES
# ============================================

@admin_bp.route('/tariffs')
@login_required
def tariffs():
    """Manage NEPRA tariff rates"""
    try:
        tariff_rates = get_all_tariffs()
        disco_list = get_disco_list()
        
        return render_template('admin/tariffs.html', 
                             tariff_rates=tariff_rates,
                             disco_list=disco_list)
    except Exception as e:
        flash(f'Error loading tariffs: {str(e)}', 'danger')
        return render_template('admin/tariffs.html')

@admin_bp.route('/tariffs/update', methods=['POST'])
@login_required
def update_tariff():
    """Update tariff rates"""
    try:
        disco_name = request.form.get('disco_name')
        base_tariff = float(request.form.get('base_tariff', 0))
        fca_rate = float(request.form.get('fca_rate', 0))
        gst_rate = float(request.form.get('gst_rate', 18.0))
        tv_fee = float(request.form.get('tv_fee', 35.0))
        loss_factor = float(request.form.get('loss_factor', 0))
        
        # Update existing tariff
        SupabaseService.get_client().table('tariff_rates') \
            .update({
                'base_tariff': base_tariff,
                'fca_rate': fca_rate,
                'gst_rate': gst_rate,
                'tv_fee': tv_fee,
                'loss_factor': loss_factor,
                'effective_from': datetime.now().strftime('%Y-%m-%d')
            }) \
            .eq('disco_name', disco_name) \
            .eq('is_active', True) \
            .execute()
        
        # Log action
        log_admin_action('update_tariff', {
            'disco': disco_name,
            'base_tariff': base_tariff
        })
        
        flash(f'Tariff rates updated for {disco_name}.', 'success')
        
    except Exception as e:
        flash(f'Failed to update tariff: {str(e)}', 'danger')
    
    return redirect(url_for('admin.tariffs'))

@admin_bp.route('/tariffs/add', methods=['POST'])
@login_required
def add_tariff():
    """Add new tariff rate"""
    try:
        tariff_data = {
            'disco_name': request.form.get('disco_name'),
            'base_tariff': float(request.form.get('base_tariff', 0)),
            'fca_rate': float(request.form.get('fca_rate', 0)),
            'gst_rate': float(request.form.get('gst_rate', 18.0)),
            'tv_fee': float(request.form.get('tv_fee', 35.0)),
            'loss_factor': float(request.form.get('loss_factor', 0)),
            'effective_from': request.form.get('effective_from', datetime.now().strftime('%Y-%m-%d')),
            'is_active': True
        }
        
        SupabaseService.get_client().table('tariff_rates') \
            .insert(tariff_data) \
            .execute()
        
        flash('New tariff rate added successfully.', 'success')
    except Exception as e:
        flash(f'Failed to add tariff: {str(e)}', 'danger')
    
    return redirect(url_for('admin.tariffs'))

# ============================================
# ALERTS MANAGEMENT ROUTES
# ============================================

@admin_bp.route('/alerts')
@login_required
def alerts():
    """View all system alerts"""
    try:
        alert_type = request.args.get('type', 'all')
        severity = request.args.get('severity', 'all')
        status = request.args.get('status', 'active')  # active, resolved, all
        
        all_alerts = get_all_alerts(alert_type, severity, status)
        
        return render_template('admin/alerts.html', 
                             alerts=all_alerts,
                             current_type=alert_type,
                             current_severity=severity,
                             current_status=status)
    except Exception as e:
        flash(f'Error loading alerts: {str(e)}', 'danger')
        return render_template('admin/alerts.html')

@admin_bp.route('/alerts/<alert_id>/resolve', methods=['POST'])
@login_required
def resolve_alert(alert_id):
    """Resolve a system alert"""
    try:
        resolution_notes = request.form.get('resolution_notes', '')
        
        SupabaseService.get_client().table('alerts') \
            .update({
                'is_resolved': True,
                'resolved_at': datetime.now().isoformat(),
                'resolved_by': current_user.id,
                'resolution_notes': resolution_notes
            }) \
            .eq('id', alert_id) \
            .execute()
        
        flash('Alert resolved successfully.', 'success')
    except Exception as e:
        flash(f'Failed to resolve alert: {str(e)}', 'danger')
    
    return redirect(url_for('admin.alerts'))

@admin_bp.route('/alerts/bulk-resolve', methods=['POST'])
@login_required
def bulk_resolve_alerts():
    """Resolve multiple alerts at once"""
    try:
        alert_ids = request.form.getlist('alert_ids[]')
        
        for alert_id in alert_ids:
            SupabaseService.get_client().table('alerts') \
                .update({
                    'is_resolved': True,
                    'resolved_at': datetime.now().isoformat(),
                    'resolved_by': current_user.id
                }) \
                .eq('id', alert_id) \
                .execute()
        
        flash(f'Successfully resolved {len(alert_ids)} alerts.', 'success')
    except Exception as e:
        flash(f'Bulk resolve failed: {str(e)}', 'danger')
    
    return redirect(url_for('admin.alerts'))

# ============================================
# REPORTS ROUTES
# ============================================

@admin_bp.route('/reports')
@login_required
def reports():
    """Generate and view reports"""
    return render_template('admin/reports.html')

@admin_bp.route('/reports/generate', methods=['POST'])
@login_required
def generate_report():
    """Generate a custom report"""
    try:
        report_type = request.form.get('report_type')
        date_from = request.form.get('date_from')
        date_to = request.form.get('date_to')
        format_type = request.form.get('format', 'pdf')
        
        # Generate report based on type
        if report_type == 'applications':
            data = generate_application_report(date_from, date_to)
        elif report_type == 'users':
            data = generate_user_report(date_from, date_to)
        elif report_type == 'financial':
            data = generate_financial_report(date_from, date_to)
        else:
            flash('Invalid report type.', 'danger')
            return redirect(url_for('admin.reports'))
        
        flash(f'Report generated successfully.', 'success')
        
    except Exception as e:
        flash(f'Failed to generate report: {str(e)}', 'danger')
    
    return redirect(url_for('admin.reports'))

# ============================================
# SETTINGS ROUTES
# ============================================

@admin_bp.route('/settings')
@login_required
def settings():
    """Admin settings page"""
    try:
        system_settings = get_system_settings()
        return render_template('admin/settings.html', settings=system_settings)
    except Exception as e:
        flash(f'Error loading settings: {str(e)}', 'danger')
        return render_template('admin/settings.html')

@admin_bp.route('/settings/update', methods=['POST'])
@login_required
def update_settings():
    """Update system settings"""
    try:
        settings_data = {
            'system_name': request.form.get('system_name'),
            'maintenance_mode': request.form.get('maintenance_mode') == 'on',
            'max_applications_per_user': int(request.form.get('max_applications', 5)),
            'auto_approve_threshold': float(request.form.get('auto_approve', 0)),
        }
        
        # Store settings in database or config
        for key, value in settings_data.items():
            SupabaseService.get_client().table('system_settings') \
                .upsert({'setting_key': key, 'setting_value': str(value)}) \
                .execute()
        
        flash('Settings updated successfully.', 'success')
    except Exception as e:
        flash(f'Failed to update settings: {str(e)}', 'danger')
    
    return redirect(url_for('admin.settings'))

# ============================================
# HELPER FUNCTIONS
# ============================================

def get_system_statistics():
    """Get comprehensive system statistics"""
    client = SupabaseService.get_client()
    
    # User statistics
    total_users = client.table('profiles').select('id', count='exact').execute().count
    active_users = client.table('profiles').select('id', count='exact').eq('is_active', True).execute().count
    admin_users = client.table('profiles').select('id', count='exact').eq('is_admin', True).execute().count
    
    # Application statistics
    applications = client.table('net_metering_applications').select('application_status').execute()
    total_apps = len(applications.data)
    
    status_counts = {}
    for app in applications.data:
        status = app.get('application_status', 'unknown')
        status_counts[status] = status_counts.get(status, 0) + 1
    
    pending_count = status_counts.get('submitted', 0) + status_counts.get('survey_scheduled', 0)
    approved_count = status_counts.get('approved', 0)
    rejected_count = status_counts.get('rejected', 0)
    
    # Alert statistics
    active_alerts = client.table('alerts').select('id', count='exact') \
        .eq('is_resolved', False).execute().count
    
    high_severity_alerts = client.table('alerts').select('id', count='exact') \
        .eq('is_resolved', False).eq('severity', 'high').execute().count
    
    # Today's data
    today = datetime.now().strftime('%Y-%m-%d')
    today_readings = client.table('power_readings') \
        .select('solar_generation') \
        .gte('timestamp', today) \
        .execute()
    
    total_generation_today = sum(r.get('solar_generation', 0) for r in today_readings.data)
    
    # New users this month
    first_of_month = datetime.now().replace(day=1).strftime('%Y-%m-%d')
    new_users_month = client.table('profiles').select('id', count='exact') \
        .gte('created_at', first_of_month).execute().count
    
    return {
        'total_users': total_users,
        'active_users': active_users,
        'admin_users': admin_users,
        'total_applications': total_apps,
        'pending_applications': pending_count,
        'approved_applications': approved_count,
        'rejected_applications': rejected_count,
        'status_counts': status_counts,
        'active_alerts': active_alerts,
        'high_severity_alerts': high_severity_alerts,
        'total_generation_today': round(total_generation_today, 2),
        'new_users_this_month': new_users_month
    }

def get_recent_applications(limit=10):
    """Get recent applications with user details"""
    return SupabaseService.get_client().table('net_metering_applications') \
        .select('*, profiles!inner(full_name, email, phone)') \
        .order('created_at', desc=True) \
        .limit(limit) \
        .execute()

def get_recent_users(limit=10):
    """Get recently registered users"""
    return SupabaseService.get_client().table('profiles') \
        .select('*') \
        .order('created_at', desc=True) \
        .limit(limit) \
        .execute()

def get_recent_alerts(limit=5):
    """Get recent unresolved alerts"""
    return SupabaseService.get_client().table('alerts') \
        .select('*, profiles(full_name)') \
        .eq('is_resolved', False) \
        .order('created_at', desc=True) \
        .limit(limit) \
        .execute()

def get_all_applications(status='all', disco='all', search='', page=1, per_page=20):
    """Get filtered and paginated applications"""
    query = SupabaseService.get_client().table('net_metering_applications') \
        .select('*, profiles(full_name, email, phone, disco_region)', count='exact')
    
    if status != 'all':
        query = query.eq('application_status', status)
    
    if disco != 'all':
        query = query.eq('disco_name', disco.upper())
    
    if search:
        query = query.or_(f"application_number.ilike.%{search}%")
    
    # Add pagination
    offset = (page - 1) * per_page
    query = query.range(offset, offset + per_page - 1)
    
    return query.order('created_at', desc=True).execute()

def get_application_status_counts():
    """Get count of applications by status"""
    client = SupabaseService.get_client()
    applications = client.table('net_metering_applications').select('application_status').execute()
    
    counts = {}
    for app in applications.data:
        status = app.get('application_status', 'unknown')
        counts[status] = counts.get(status, 0) + 1
    
    return counts

def get_disco_list():
    """Get list of all DISCOs"""
    client = SupabaseService.get_client()
    discos = client.table('tariff_rates').select('disco_name').eq('is_active', True).execute()
    return [d['disco_name'] for d in discos.data]

def get_application_by_id(application_id):
    """Get single application with all details"""
    return SupabaseService.get_client().table('net_metering_applications') \
        .select('*, profiles(*)') \
        .eq('id', application_id) \
        .single() \
        .execute()

def get_application_documents(application_id):
    """Get documents for an application"""
    return SupabaseService.get_client().table('documents') \
        .select('*') \
        .eq('application_id', application_id) \
        .order('uploaded_at', desc=True) \
        .execute()

def get_application_status_history(application_id):
    """Get status change history"""
    app = SupabaseService.get_client().table('net_metering_applications') \
        .select('status_history') \
        .eq('id', application_id) \
        .single() \
        .execute()
    
    if app.data and app.data.get('status_history'):
        history = app.data['status_history']
        if isinstance(history, str):
            history = json.loads(history)
        return history
    
    return []

def get_user_details(user_id):
    """Get user details"""
    return SupabaseService.get_user_by_id(user_id)

def get_user_applications(user_id):
    """Get applications for a specific user"""
    return SupabaseService.get_client().table('net_metering_applications') \
        .select('*') \
        .eq('user_id', user_id) \
        .order('created_at', desc=True) \
        .execute()

def get_all_users(search='', status='all', role='all', disco='all', page=1, per_page=20):
    """Get filtered and paginated users"""
    query = SupabaseService.get_client().table('profiles') \
        .select('*', count='exact')
    
    if status == 'active':
        query = query.eq('is_active', True)
    elif status == 'inactive':
        query = query.eq('is_active', False)
    
    if role == 'admin':
        query = query.eq('is_admin', True)
    elif role == 'user':
        query = query.eq('is_admin', False)
    
    if disco != 'all':
        query = query.eq('disco_region', disco)
    
    if search:
        query = query.or_(f"full_name.ilike.%{search}%,email.ilike.%{search}%,phone.ilike.%{search}%")
    
    offset = (page - 1) * per_page
    query = query.range(offset, offset + per_page - 1)
    
    return query.order('created_at', desc=True).execute()

def get_user_statistics():
    """Get user statistics"""
    client = SupabaseService.get_client()
    
    total = client.table('profiles').select('id', count='exact').execute().count
    active = client.table('profiles').select('id', count='exact').eq('is_active', True).execute().count
    admins = client.table('profiles').select('id', count='exact').eq('is_admin', True).execute().count
    
    # Users by DISCO
    users_by_disco = {}
    discos = client.table('profiles').select('disco_region').execute()
    for u in discos.data:
        disco = u.get('disco_region', 'Unknown')
        users_by_disco[disco] = users_by_disco.get(disco, 0) + 1
    
    return {
        'total': total,
        'active': active,
        'inactive': total - active,
        'admins': admins,
        'by_disco': users_by_disco
    }

def get_user_all_applications(user_id):
    """Get all applications for a user"""
    return SupabaseService.get_client().table('net_metering_applications') \
        .select('*') \
        .eq('user_id', user_id) \
        .order('created_at', desc=True) \
        .execute()

def get_user_power_readings(user_id, limit=20):
    """Get user's power readings"""
    return SupabaseService.get_client().table('power_readings') \
        .select('*') \
        .eq('user_id', user_id) \
        .order('timestamp', desc=True) \
        .limit(limit) \
        .execute()

def get_user_alerts(user_id, limit=10):
    """Get user's alerts"""
    return SupabaseService.get_client().table('alerts') \
        .select('*') \
        .eq('user_id', user_id) \
        .order('created_at', desc=True) \
        .limit(limit) \
        .execute()

def get_user_savings(user_id, limit=30):
    """Get user's savings history"""
    return SupabaseService.get_client().table('savings_history') \
        .select('*') \
        .eq('user_id', user_id) \
        .order('savings_date', desc=True) \
        .limit(limit) \
        .execute()

def get_user_activity_log(user_id, limit=50):
    """Get user activity log"""
    return SupabaseService.get_client().table('activity_logs') \
        .select('*') \
        .eq('user_id', user_id) \
        .order('timestamp', desc=True) \
        .limit(limit) \
        .execute()

def get_all_alerts(alert_type='all', severity='all', status='active', limit=100):
    """Get filtered alerts"""
    query = SupabaseService.get_client().table('alerts') \
        .select('*, profiles(full_name, email)')
    
    if alert_type != 'all':
        query = query.eq('type', alert_type)
    
    if severity != 'all':
        query = query.eq('severity', severity)
    
    if status == 'active':
        query = query.eq('is_resolved', False)
    elif status == 'resolved':
        query = query.eq('is_resolved', True)
    
    return query.order('created_at', desc=True).limit(limit).execute()

def get_all_tariffs():
    """Get all tariff rates"""
    return SupabaseService.get_client().table('tariff_rates') \
        .select('*') \
        .order('disco_name') \
        .execute()

def get_detailed_statistics():
    """Get detailed system statistics"""
    stats = get_system_statistics()
    
    # Add monthly trends
    client = SupabaseService.get_client()
    
    # Monthly application trends
    monthly_apps = []
    for i in range(6):
        month = (datetime.now() - timedelta(days=30*i)).strftime('%Y-%m')
        count = client.table('net_metering_applications').select('id', count='exact') \
            .like('created_at', f'{month}%').execute().count
        monthly_apps.append({'month': month, 'count': count})
    
    stats['monthly_applications'] = monthly_apps
    
    return stats

def get_application_analytics(period='30d'):
    """Get application analytics"""
    client = SupabaseService.get_client()
    
    # Applications by DISCO
    apps_by_disco = {}
    applications = client.table('net_metering_applications').select('disco_name').execute()
    for app in applications.data:
        disco = app.get('disco_name', 'Unknown')
        apps_by_disco[disco] = apps_by_disco.get(disco, 0) + 1
    
    # Average processing time
    completed = client.table('net_metering_applications') \
        .select('submitted_at, green_meter_date') \
        .not_.is_('green_meter_date', 'null') \
        .execute()
    
    total_days = 0
    for app in completed.data:
        if app.get('submitted_at') and app.get('green_meter_date'):
            submitted = datetime.fromisoformat(app['submitted_at'].replace('Z', '+00:00'))
            completed_date = datetime.fromisoformat(app['green_meter_date'].replace('Z', '+00:00'))
            total_days += (completed_date - submitted).days
    
    avg_days = total_days / len(completed.data) if completed.data else 0
    
    return {
        'by_disco': apps_by_disco,
        'average_processing_days': round(avg_days, 1),
        'total_completed': len(completed.data)
    }

def get_user_analytics(period='30d'):
    """Get user analytics"""
    client = SupabaseService.get_client()
    
    # User growth over time
    # Registration by DISCO
    # Active vs inactive ratio
    
    return {
        'total_users': client.table('profiles').select('id', count='exact').execute().count,
        'active_users': client.table('profiles').select('id', count='exact').eq('is_active', True).execute().count,
    }

def get_financial_analytics():
    """Get financial analytics"""
    client = SupabaseService.get_client()
    
    total_savings = 0
    savings = client.table('savings_history').select('total_savings').execute()
    for s in savings.data:
        total_savings += s.get('total_savings', 0)
    
    return {
        'total_savings_all_users': round(total_savings, 2),
        'average_savings_per_user': round(total_savings / max(1, len(savings.data)), 2)
    }

def create_user_notification(user_id, status, application_id):
    """Create notification for user"""
    try:
        status_messages = {
            'submitted': 'Your application has been submitted for review.',
            'survey_scheduled': 'A site survey has been scheduled for your application.',
            'demand_notice': 'Demand notice has been issued for your application.',
            'inspection': 'Inspection has been completed for your application.',
            'approved': 'Congratulations! Your net metering application has been approved.',
            'rejected': 'Your application has been rejected. Please check the notes for details.'
        }
        
        message = status_messages.get(status, f'Application status updated to: {status}')
        
        alert_data = {
            'user_id': user_id,
            'type': 'application_update',
            'severity': 'info',
            'title': 'Application Status Update',
            'message': message,
            'data': json.dumps({'application_id': application_id, 'new_status': status}),
            'is_read': False,
            'is_resolved': False
        }
        
        SupabaseService.get_client().table('alerts').insert(alert_data).execute()
    except Exception as e:
        print(f"Failed to create notification: {str(e)}")

def log_admin_action(action, details):
    """Log admin actions for audit"""
    try:
        log_data = {
            'admin_id': current_user.id,
            'admin_name': current_user.full_name,
            'action': action,
            'details': json.dumps(details),
            'ip_address': request.remote_addr,
            'timestamp': datetime.now().isoformat()
        }
        
        SupabaseService.get_client().table('admin_audit_logs').insert(log_data).execute()
    except Exception as e:
        print(f"Failed to log admin action: {str(e)}")

def get_system_settings():
    """Get system settings"""
    try:
        settings = {}
        result = SupabaseService.get_client().table('system_settings').select('*').execute()
        for row in result.data:
            settings[row['setting_key']] = row['setting_value']
        return settings
    except:
        return {}