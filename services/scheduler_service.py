from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from datetime import datetime
import logging
from typing import Dict, Optional
from services.ai_service import AIService
from services.supabase_service import SupabaseService
import pandas as pd

logger = logging.getLogger(__name__)

class SchedulerService:
    """Background job scheduler for AI predictions and data updates"""
    
    def __init__(self):
        self.scheduler = BackgroundScheduler()
        self.ai_service = AIService()
        self.jobs_started = False
    
    def start_jobs(self):
        """Start all scheduled background jobs"""
        if self.jobs_started:
            return
        
        # Schedule daily solar forecast at midnight
        self.scheduler.add_job(
            func=self.daily_solar_forecast,
            trigger=CronTrigger(hour=0, minute=5),
            id='daily_forecast',
            name='Daily Solar Forecast',
            replace_existing=True
        )
        
        # Schedule hourly power flow updates
        self.scheduler.add_job(
            func=self.hourly_power_update,
            trigger=CronTrigger(minute=0),
            id='hourly_update',
            name='Hourly Power Update',
            replace_existing=True
        )
        
        # Schedule anomaly detection every 30 minutes
        self.scheduler.add_job(
            func=self.check_anomalies,
            trigger=CronTrigger(minute='*/30'),
            id='anomaly_detection',
            name='Anomaly Detection',
            replace_existing=True
        )
        
        # Schedule load shedding pattern analysis every 4 hours
        self.scheduler.add_job(
            func=self.update_load_shedding_predictions,
            trigger=CronTrigger(hour='*/4'),
            id='load_shedding_update',
            name='Load Shedding Update',
            replace_existing=True
        )
        
        # Schedule tariff update check daily at 6 AM
        self.scheduler.add_job(
            func=self.check_tariff_updates,
            trigger=CronTrigger(hour=6, minute=0),
            id='tariff_update',
            name='Tariff Update Check',
            replace_existing=True
        )
        
        self.scheduler.start()
        self.jobs_started = True
        logger.info("All scheduled jobs started successfully")
    
    def stop_jobs(self):
        """Stop all scheduled jobs"""
        if self.scheduler.running:
            self.scheduler.shutdown()
            self.jobs_started = False
            logger.info("All scheduled jobs stopped")
    
    def daily_solar_forecast(self):
        """Generate daily solar forecast for all active users"""
        try:
            logger.info("Starting daily solar forecast generation")
            
            # Get all active users from database
            response = SupabaseService.get_client().table('profiles') \
                .select('*') \
                .eq('is_active', True) \
                .execute()
            
            users = response.data
            
            for user in users:
                if user.get('latitude') and user.get('longitude'):
                    # Fetch weather forecast
                    weather = self.ai_service.fetch_weather_forecast(
                        user['latitude'],
                        user['longitude'],
                        days=2
                    )
                    
                    if weather['success']:
                        # Get historical data for model training
                        historical = self._get_user_historical_data(user['id'])
                        
                        if not historical.empty:
                            # Train model
                            model = self.ai_service.train_solar_forecast_model(historical)
                            
                            if model:
                                # Generate prediction
                                prediction = self.ai_service.predict_solar_generation(
                                    model,
                                    weather,
                                    system_capacity=user.get('system_capacity', 5.0),
                                    panel_efficiency=user.get('panel_efficiency', 0.20)
                                )
                                
                                # Store prediction in database
                                SupabaseService.get_admin_client().table('forecasts').insert({
                                    'user_id': user['id'],
                                    'forecast_data': prediction,
                                    'created_at': datetime.now().isoformat()
                                }).execute()
            
            logger.info("Daily solar forecast generation completed")
            
        except Exception as e:
            logger.error(f"Daily forecast job failed: {str(e)}")
    
    def hourly_power_update(self):
        """Update real-time power flow data"""
        try:
            # This would typically fetch from IoT devices or inverter APIs
            logger.info("Hourly power update executed")
            
        except Exception as e:
            logger.error(f"Hourly power update failed: {str(e)}")
    
    def check_anomalies(self):
        """Check for anomalies in system performance"""
        try:
            response = SupabaseService.get_client().table('profiles') \
                .select('*') \
                .eq('is_active', True) \
                .execute()
            
            for user in response.data:
                # Get latest power reading
                latest_reading = self._get_latest_power_reading(user['id'])
                
                # Get latest forecast
                latest_forecast = self._get_latest_forecast(user['id'])
                
                if latest_reading and latest_forecast:
                    anomalies = self.ai_service.detect_anomalies(
                        latest_reading['power_generation'],
                        latest_forecast.get('expected_generation', 0)
                    )
                    
                    if anomalies['success'] and anomalies['has_anomalies']:
                        # Store anomaly alert
                        SupabaseService.get_admin_client().table('alerts').insert({
                            'user_id': user['id'],
                            'type': 'anomaly',
                            'data': anomalies,
                            'read': False,
                            'created_at': datetime.now().isoformat()
                        }).execute()
            
        except Exception as e:
            logger.error(f"Anomaly check failed: {str(e)}")
    
    def update_load_shedding_predictions(self):
        """Update load shedding predictions"""
        try:
            logger.info("Updating load shedding predictions")
            
            response = SupabaseService.get_client().table('profiles') \
                .select('*') \
                .eq('is_active', True) \
                .execute()
            
            for user in response.data:
                historical_outages = self._get_user_outage_history(user['id'])
                
                if not historical_outages.empty:
                    prediction = self.ai_service.predict_load_shedding(historical_outages)
                    
                    # Store prediction
                    SupabaseService.get_admin_client().table('load_shedding_predictions').insert({
                        'user_id': user['id'],
                        'prediction_data': prediction,
                        'created_at': datetime.now().isoformat()
                    }).execute()
            
        except Exception as e:
            logger.error(f"Load shedding prediction update failed: {str(e)}")
    
    def check_tariff_updates(self):
        """Check for NEPRA tariff updates"""
        try:
            # This would typically fetch from NEPRA API or web scraping
            logger.info("Tariff update check executed")
            
        except Exception as e:
            logger.error(f"Tariff update check failed: {str(e)}")
    
    def _get_user_historical_data(self, user_id: str) -> pd.DataFrame:
        """Get historical generation data for a user"""
        try:
            response = SupabaseService.get_client().table('power_readings') \
                .select('*') \
                .eq('user_id', user_id) \
                .order('timestamp', desc=True) \
                .limit(8760) \
                .execute()
            
            if response.data:
                return pd.DataFrame(response.data)
            return pd.DataFrame()
            
        except Exception as e:
            logger.error(f"Failed to fetch historical data: {str(e)}")
            return pd.DataFrame()
    
    def _get_latest_power_reading(self, user_id: str) -> Optional[Dict]:
        """Get latest power reading for anomaly detection"""
        try:
            response = SupabaseService.get_client().table('power_readings') \
                .select('*') \
                .eq('user_id', user_id) \
                .order('timestamp', desc=True) \
                .limit(1) \
                .execute()
            
            return response.data[0] if response.data else None
            
        except Exception as e:
            logger.error(f"Failed to fetch latest reading: {str(e)}")
            return None
    
    def _get_latest_forecast(self, user_id: str) -> Optional[Dict]:
        """Get latest forecast data"""
        try:
            response = SupabaseService.get_client().table('forecasts') \
                .select('*') \
                .eq('user_id', user_id) \
                .order('created_at', desc=True) \
                .limit(1) \
                .execute()
            
            return response.data[0] if response.data else None
            
        except Exception as e:
            logger.error(f"Failed to fetch latest forecast: {str(e)}")
            return None
    
    def _get_user_outage_history(self, user_id: str) -> pd.DataFrame:
        """Get historical outage data for a user"""
        try:
            response = SupabaseService.get_client().table('power_outages') \
                .select('*') \
                .eq('user_id', user_id) \
                .order('timestamp', desc=True) \
                .limit(1000) \
                .execute()
            
            if response.data:
                return pd.DataFrame(response.data)
            return pd.DataFrame()
            
        except Exception as e:
            logger.error(f"Failed to fetch outage history: {str(e)}")
            return pd.DataFrame()