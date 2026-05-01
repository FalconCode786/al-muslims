# ============================================
# COMPLETE SUPABASE SERVICE WITH ALL QUERIES
# ============================================

import os
from typing import Dict, Optional, Any
from models.user import User
from datetime import datetime
import uuid
import logging

try:
    from supabase import create_client, Client
except ImportError:
    create_client = None
    Client = Any

logger = logging.getLogger(__name__)

class SupabaseService:
    """Main Supabase service for authentication and database operations"""
    
    _client: Optional[Client] = None
    
    @classmethod
    def get_client(cls) -> Client:
        """Get or create Supabase client"""
        if cls._client is None:
            supabase_url = os.getenv('SUPABASE_URL')
            supabase_key = os.getenv('SUPABASE_KEY')
            
            if not supabase_url or not supabase_key:
                raise ValueError("Missing Supabase credentials in environment variables")

            if create_client is None:
                raise ImportError("supabase package is not installed")
            
            cls._client = create_client(supabase_url, supabase_key)
        
        return cls._client
    
    @staticmethod
    def login_user(email: str, password: str) -> Dict:
        """Login user with email and password"""
        try:
            client = SupabaseService.get_client()
            response = client.auth.sign_in_with_password({
                'email': email,
                'password': password
            })
            
            if response and response.user:
                user_data = SupabaseService.get_user_by_id(response.user.id)
                return {
                    'success': True,
                    'user': user_data,
                    'access_token': response.session.access_token if response.session else None
                }
            
            return {'success': False, 'error': 'Invalid credentials'}
        
        except (ImportError, ValueError) as e:
            logger.warning(f"Login unavailable: {str(e)}")
            return {
                'success': False,
                'error': 'Authentication service is unavailable. Please check your backend connection.'
            }
        except Exception as e:
            logger.error(f"Login error: {str(e)}")
            return {
                'success': False,
                'error': 'Invalid email or password. Please try again.'
            }
    
    @staticmethod
    def register_user(email: str, password: str, full_name: str) -> Dict:
        """Register new user"""
        try:
            client = SupabaseService.get_client()
            
            # Sign up with auth
            response = client.auth.sign_up({
                'email': email,
                'password': password
            })
            
            if response and response.user:
                user_id = response.user.id
                
                # Create user profile
                profile_data = {
                    'id': user_id,
                    'email': email,
                    'full_name': full_name,
                    'is_active': True,
                    'is_admin': False,
                    'created_at': datetime.now().isoformat()
                }
                
                client.table('profiles').insert(profile_data).execute()
                
                return {'success': True, 'user_id': user_id}
            
            return {'success': False, 'error': 'Registration failed'}
        
        except (ImportError, ValueError) as e:
            logger.warning(f"Registration unavailable: {str(e)}")
            return {
                'success': False,
                'error': 'Registration service is unavailable. Please check your backend connection.'
            }
        except Exception as e:
            logger.error(f"Registration error: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    @staticmethod
    def logout_user(access_token: str) -> Dict:
        """Logout user"""
        try:
            client = SupabaseService.get_client()
            client.auth.sign_out()
            return {'success': True}
        except Exception as e:
            logger.error(f"Logout error: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    @staticmethod
    def get_user_by_id(user_id: str) -> Optional[User]:
        """Get user from database by ID"""
        try:
            client = SupabaseService.get_client()
            response = client.table('profiles') \
                .select('*') \
                .eq('id', user_id) \
                .single() \
                .execute()
            
            if response and response.data:
                data = response.data
                return User(
                    id=data.get('id'),
                    email=data.get('email'),
                    full_name=data.get('full_name'),
                    phone=data.get('phone'),
                    address=data.get('address'),
                    cnic=data.get('cnic'),
                    disco_region=data.get('disco_region'),
                    is_active=data.get('is_active', True),
                    is_admin=data.get('is_admin', False)
                )
            
            return None
        
        except Exception as e:
            logger.error(f"Error getting user {user_id}: {str(e)}")
            return None


class SupabaseQueries:
    """All database queries for Almuslim platform"""
    
    @staticmethod
    def get_user_profile(user_id: str) -> Dict:
        """Get complete user profile"""
        return SupabaseService.get_client().table('profiles') \
            .select('*') \
            .eq('id', user_id) \
            .single() \
            .execute()
    
    @staticmethod
    def update_user_profile(user_id: str, data: Dict):
        """Update user profile"""
        return SupabaseService.get_client().table('profiles') \
            .update(data) \
            .eq('id', user_id) \
            .execute()
    
    @staticmethod
    def get_power_readings(user_id: str, hours: int = 24):
        """Get power readings for last n hours"""
        from datetime import datetime, timedelta
        since = datetime.utcnow() - timedelta(hours=hours)
        
        return SupabaseService.get_client().table('power_readings') \
            .select('*') \
            .eq('user_id', user_id) \
            .gte('timestamp', since.isoformat()) \
            .order('timestamp', desc=False) \
            .execute()
    
    @staticmethod
    def get_latest_power_reading(user_id: str):
        """Get most recent power reading"""
        return SupabaseService.get_client().table('power_readings') \
            .select('*') \
            .eq('user_id', user_id) \
            .order('timestamp', desc=True) \
            .limit(1) \
            .single() \
            .execute()
    
    @staticmethod
    def insert_power_reading(user_id: str, data: Dict):
        """Insert new power reading"""
        data['user_id'] = user_id
        return SupabaseService.get_client().table('power_readings') \
            .insert(data) \
            .execute()
    
    @staticmethod
    def get_latest_forecast(user_id: str):
        """Get latest forecast for user"""
        return SupabaseService.get_client().table('forecasts') \
            .select('*') \
            .eq('user_id', user_id) \
            .order('created_at', desc=True) \
            .limit(1) \
            .single() \
            .execute()
    
    @staticmethod
    def insert_forecast(user_id: str, data: Dict):
        """Insert new forecast"""
        data['user_id'] = user_id
        return SupabaseService.get_client().table('forecasts') \
            .insert(data) \
            .execute()
    
    @staticmethod
    def get_unread_alerts(user_id: str):
        """Get unread alerts for user"""
        return SupabaseService.get_client().table('alerts') \
            .select('*') \
            .eq('user_id', user_id) \
            .eq('is_read', False) \
            .order('created_at', desc=True) \
            .execute()
    
    @staticmethod
    def mark_alert_read(alert_id: str):
        """Mark alert as read"""
        return SupabaseService.get_client().table('alerts') \
            .update({'is_read': True}) \
            .eq('id', alert_id) \
            .execute()
    
    @staticmethod
    def insert_alert(user_id: str, data: Dict):
        """Insert new alert"""
        data['user_id'] = user_id
        return SupabaseService.get_client().table('alerts') \
            .insert(data) \
            .execute()
    
    @staticmethod
    def get_outage_history(user_id: str, days: int = 30):
        """Get outage history for last n days"""
        from datetime import datetime, timedelta
        since = datetime.utcnow() - timedelta(days=days)
        
        return SupabaseService.get_client().table('power_outages') \
            .select('*') \
            .eq('user_id', user_id) \
            .gte('start_time', since.isoformat()) \
            .order('start_time', desc=True) \
            .execute()
    
    @staticmethod
    def insert_outage(user_id: str, data: Dict):
        """Record power outage"""
        data['user_id'] = user_id
        return SupabaseService.get_client().table('power_outages') \
            .insert(data) \
            .execute()
    
    @staticmethod
    def get_appliances(user_id: str):
        """Get user's appliances"""
        return SupabaseService.get_client().table('appliances') \
            .select('*') \
            .eq('user_id', user_id) \
            .execute()
    
    @staticmethod
    def insert_appliance(user_id: str, data: Dict):
        """Add new appliance"""
        data['user_id'] = user_id
        return SupabaseService.get_client().table('appliances') \
            .insert(data) \
            .execute()
    
    @staticmethod
    def get_metering_applications(user_id: str):
        """Get net metering applications"""
        return SupabaseService.get_client().table('net_metering_applications') \
            .select('*') \
            .eq('user_id', user_id) \
            .order('created_at', desc=True) \
            .execute()
    
    @staticmethod
    def create_metering_application(user_id: str, data: Dict):
        """Create new net metering application"""
        data['user_id'] = user_id
        data['application_number'] = f"NMA-{datetime.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"
        return SupabaseService.get_client().table('net_metering_applications') \
            .insert(data) \
            .execute()
    
    @staticmethod
    def update_application_status(application_id: str, status: str, step: int = None):
        """Update application status"""
        update_data = {
            'application_status': status,
            'updated_at': datetime.now().isoformat()
        }
        if step:
            update_data['current_step'] = step
        
        # Append to status history
        current = SupabaseService.get_client().table('net_metering_applications') \
            .select('status_history') \
            .eq('id', application_id) \
            .single() \
            .execute()
        
        history = current.data.get('status_history', [])
        history.append({
            'status': status,
            'step': step,
            'timestamp': datetime.now().isoformat()
        })
        update_data['status_history'] = history
        
        return SupabaseService.get_client().table('net_metering_applications') \
            .update(update_data) \
            .eq('id', application_id) \
            .execute()
    
    @staticmethod
    def upload_document(user_id: str, application_id: str, doc_type: str, file_path: str, file_name: str):
        """Upload document"""
        data = {
            'user_id': user_id,
            'application_id': application_id,
            'document_type': doc_type,
            'file_name': file_name,
            'file_path': file_path
        }
        return SupabaseService.get_client().table('documents') \
            .insert(data) \
            .execute()
    
    @staticmethod
    def get_documents(user_id: str, application_id: str = None):
        """Get user documents"""
        query = SupabaseService.get_client().table('documents') \
            .select('*') \
            .eq('user_id', user_id)
        
        if application_id:
            query = query.eq('application_id', application_id)
        
        return query.order('uploaded_at', desc=True).execute()
    
    @staticmethod
    def get_daily_savings(user_id: str, date: str = None):
        """Get savings for specific date"""
        if not date:
            date = datetime.now().strftime('%Y-%m-%d')
        
        return SupabaseService.get_client().table('savings_history') \
            .select('*') \
            .eq('user_id', user_id) \
            .eq('savings_date', date) \
            .single() \
            .execute()
    
    @staticmethod
    def insert_daily_savings(user_id: str, data: Dict):
        """Record daily savings"""
        data['user_id'] = user_id
        data['savings_date'] = datetime.now().strftime('%Y-%m-%d')
        return SupabaseService.get_client().table('savings_history') \
            .insert(data) \
            .execute()
    
    @staticmethod
    def get_monthly_savings(user_id: str, months: int = 12):
        """Get monthly savings summary"""
        return SupabaseService.get_client() \
            .from_('monthly_savings_summary') \
            .select('*') \
            .eq('user_id', user_id) \
            .order('month', desc=True) \
            .limit(months) \
            .execute()
    
    @staticmethod
    def get_tariff_rates(disco_name: str = None):
        """Get current tariff rates"""
        query = SupabaseService.get_client().table('tariff_rates') \
            .select('*') \
            .eq('is_active', True)
        
        if disco_name:
            query = query.eq('disco_name', disco_name.upper())
        
        return query.execute()
    
    @staticmethod
    def get_user_settings(user_id: str):
        """Get user settings"""
        return SupabaseService.get_client().table('user_settings') \
            .select('*') \
            .eq('user_id', user_id) \
            .single() \
            .execute()
    
    @staticmethod
    def update_user_settings(user_id: str, data: Dict):
        """Update user settings"""
        return SupabaseService.get_client().table('user_settings') \
            .update(data) \
            .eq('user_id', user_id) \
            .execute()
    
    @staticmethod
    def get_daily_generation_summary(user_id: str, days: int = 30):
        """Get daily generation summary"""
        from datetime import datetime, timedelta
        since = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
        
        return SupabaseService.get_client() \
            .from_('daily_generation_summary') \
            .select('*') \
            .eq('user_id', user_id) \
            .gte('date', since) \
            .order('date', desc=True) \
            .execute()
    
    @staticmethod
    def get_active_alerts_count(user_id: str):
        """Get count of unread alerts"""
        return SupabaseService.get_client().table('alerts') \
            .select('id', count='exact') \
            .eq('user_id', user_id) \
            .eq('is_read', False) \
            .execute()
    
    @staticmethod
    def search_users(search_term: str):
        """Search users by name or email (admin only)"""
        return SupabaseService.get_client().table('profiles') \
            .select('*') \
            .or_(f"full_name.ilike.%{search_term}%,email.ilike.%{search_term}%") \
            .execute()
    
    @staticmethod
    def get_system_statistics():
        """Get overall system statistics (admin)"""
        client = SupabaseService.get_client()
        
        total_users = client.table('profiles').select('id', count='exact').execute().count
        active_users = client.table('profiles').select('id', count='exact').eq('is_active', True).execute().count
        total_applications = client.table('net_metering_applications').select('id', count='exact').execute().count
        
        return {
            'total_users': total_users,
            'active_users': active_users,
            'total_applications': total_applications
        }