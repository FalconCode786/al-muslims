import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import logging
import json
import os

try:
    from prophet import Prophet
except ImportError:
    Prophet = None

try:
    import openmeteo_requests
except ImportError:
    openmeteo_requests = None

try:
    import requests_cache
    from retry_requests import retry
except ImportError:
    requests_cache = None
    retry = None

logger = logging.getLogger(__name__)

class AIService:
    """AI and Predictive Analytics Service for Almuslim"""
    
    def __init__(self):
        self.cache_session = None
        self.retry_session = None
        self.openmeteo = None
        if requests_cache and retry and openmeteo_requests:
            self.cache_session = requests_cache.CachedSession('.cache', expire_after=3600)
            self.retry_session = retry(self.cache_session, retries=5, backoff_factor=0.2)
            self.openmeteo = openmeteo_requests.Client(session=self.retry_session)
        self.model_path = 'models/saved/'
        os.makedirs(self.model_path, exist_ok=True)
        
        # Pakistan-specific parameters
        self.base_tariff = 35.0  # PKR per kWh (average base tariff)
        self.fca_rate = 3.50  # Fuel Charges Adjustment per kWh
        self.gst_rate = 0.18  # 18% GST
        self.tv_fee = 35.0  # TV Fee per month
        
        # DISCO loss factors (percentage)
        self.disco_losses = {
            'IESCO': 0.12,
            'LESCO': 0.14,
            'GEPCO': 0.11,
            'FESCO': 0.13,
            'MEPCO': 0.15,
            'PESCO': 0.16,
            'HESCO': 0.17,
            'QESCO': 0.18,
            'SEPCO': 0.16,
            'TESCO': 0.15
        }
    
    def fetch_weather_forecast(self, latitude: float, longitude: float, days: int = 7) -> Dict:
        """Fetch weather forecast data from Open-Meteo API"""
        try:
            if not self.openmeteo:
                return {
                    'success': False,
                    'error': 'Weather forecasting service is unavailable in this environment.'
                }

            params = {
                "latitude": latitude,
                "longitude": longitude,
                "hourly": [
                    "temperature_2m",
                    "relative_humidity_2m",
                    "dew_point_2m",
                    "apparent_temperature",
                    "precipitation_probability",
                    "cloud_cover",
                    "cloud_cover_low",
                    "cloud_cover_mid",
                    "cloud_cover_high",
                    "wind_speed_10m",
                    "wind_direction_10m",
                    "shortwave_radiation",
                    "direct_radiation",
                    "diffuse_radiation",
                    "direct_normal_irradiance",
                    "global_tilted_irradiance",
                    "terrestrial_radiation"
                ],
                "timezone": "Asia/Karachi",
                "forecast_days": days
            }
            
            responses = self.openmeteo.weather_api(
                "https://api.open-meteo.com/v1/forecast", 
                params=params
            )
            
            response = responses[0]
            
            # Process hourly data
            hourly = response.Hourly()
            hourly_data = {
                "date": pd.date_range(
                    start=pd.Timestamp.fromtimestamp(hourly.Time()),
                    end=pd.Timestamp.fromtimestamp(hourly.TimeEnd()),
                    freq=pd.Timedelta(seconds=hourly.Interval()),
                    inclusive="left"
                ),
                "temperature": hourly.Variables(0).ValuesAsNumpy(),
                "humidity": hourly.Variables(1).ValuesAsNumpy(),
                "cloud_cover": hourly.Variables(5).ValuesAsNumpy(),
                "shortwave_radiation": hourly.Variables(11).ValuesAsNumpy(),
                "direct_radiation": hourly.Variables(12).ValuesAsNumpy(),
                "diffuse_radiation": hourly.Variables(13).ValuesAsNumpy(),
                "direct_normal_irradiance": hourly.Variables(14).ValuesAsNumpy(),
                "global_tilted_irradiance": hourly.Variables(15).ValuesAsNumpy(),
                "precipitation_probability": hourly.Variables(4).ValuesAsNumpy(),
                "wind_speed": hourly.Variables(9).ValuesAsNumpy()
            }
            
            return {
                'success': True,
                'data': hourly_data,
                'latitude': response.Latitude(),
                'longitude': response.Longitude(),
                'elevation': response.Elevation()
            }
            
        except Exception as e:
            logger.error(f"Weather forecast fetch failed: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def train_solar_forecast_model(self, historical_data: pd.DataFrame) -> Optional[Prophet]:
        """Train Prophet model for solar generation forecasting"""
        try:
            if Prophet is None:
                logger.warning("Prophet is unavailable; skipping model training")
                return None

            if historical_data.empty or len(historical_data) < 24:
                logger.warning("Insufficient historical data for model training")
                return None
            
            # Prepare data for Prophet
            df = historical_data.copy()
            df['ds'] = pd.to_datetime(df['timestamp'])
            df['y'] = df['power_generation']
            
            # Add weather features as regressors
            model = Prophet(
                yearly_seasonality=True,
                weekly_seasonality=True,
                daily_seasonality=True,
                seasonality_mode='multiplicative',
                changepoint_prior_scale=0.05,
                seasonality_prior_scale=10.0,
                holidays_prior_scale=10.0
            )
            
            # Add Pakistan-specific regressors
            if 'temperature' in df.columns:
                model.add_regressor('temperature')
            if 'cloud_cover' in df.columns:
                model.add_regressor('cloud_cover')
            if 'humidity' in df.columns:
                model.add_regressor('humidity')
            if 'shortwave_radiation' in df.columns:
                model.add_regressor('shortwave_radiation')
            
            # Add smog season indicator (Oct-Feb in Pakistan)
            df['is_smog_season'] = df['ds'].apply(
                lambda x: 1 if x.month in [10, 11, 12, 1, 2] else 0
            )
            model.add_regressor('is_smog_season')
            
            # Add monsoon season indicator (Jul-Sep)
            df['is_monsoon'] = df['ds'].apply(
                lambda x: 1 if x.month in [7, 8, 9] else 0
            )
            model.add_regressor('is_monsoon')
            
            # Fit the model
            model.fit(df)
            
            # Save model
            model_path = os.path.join(self.model_path, f'solar_model_{datetime.now().strftime("%Y%m%d")}.json')
            with open(model_path, 'w') as f:
                json.dump(model.to_json(), f)
            
            return model
            
        except Exception as e:
            logger.error(f"Model training failed: {str(e)}")
            return None
    
    def predict_solar_generation(self, model: Prophet, weather_forecast: Dict, 
                                 system_capacity: float = 5.0, 
                                 panel_efficiency: float = 0.20,
                                 inverter_efficiency: float = 0.95) -> Dict:
        """Predict solar generation for next 24-48 hours"""
        try:
            if not model or not weather_forecast.get('success'):
                return {'success': False, 'error': 'Invalid model or forecast data'}
            
            forecast_data = weather_forecast['data']
            
            # Create future dataframe with weather features
            future = model.make_future_dataframe(
                periods=len(forecast_data['date']),
                freq='H'
            )
            
            # Add weather features
            future['temperature'] = forecast_data['temperature']
            future['cloud_cover'] = forecast_data['cloud_cover']
            future['humidity'] = forecast_data['humidity']
            future['shortwave_radiation'] = forecast_data['shortwave_radiation']
            
            # Add seasonal indicators
            future['is_smog_season'] = future['ds'].apply(
                lambda x: 1 if x.month in [10, 11, 12, 1, 2] else 0
            )
            future['is_monsoon'] = future['ds'].apply(
                lambda x: 1 if x.month in [7, 8, 9] else 0
            )
            
            # Make prediction
            forecast = model.predict(future)
            
            # Apply system-specific adjustments
            forecast['adjusted_generation'] = (
                forecast['yhat'] * 
                system_capacity * 
                panel_efficiency * 
                inverter_efficiency
            )
            
            # Calculate confidence intervals
            forecast['lower_bound'] = (
                forecast['yhat_lower'] * 
                system_capacity * 
                panel_efficiency * 
                inverter_efficiency
            )
            forecast['upper_bound'] = (
                forecast['yhat_upper'] * 
                system_capacity * 
                panel_efficiency * 
                inverter_efficiency
            )
            
            # Aggregate to daily totals
            daily_forecast = forecast.set_index('ds').resample('D').agg({
                'adjusted_generation': 'sum',
                'lower_bound': 'sum',
                'upper_bound': 'sum',
                'yhat': 'sum'
            }).reset_index()
            
            # Calculate optimal generation windows
            hourly_forecast = forecast[['ds', 'adjusted_generation', 'lower_bound', 'upper_bound']].copy()
            hourly_forecast['hour'] = hourly_forecast['ds'].dt.hour
            
            # Find peak generation hours
            peak_hours = hourly_forecast.nlargest(6, 'adjusted_generation')
            
            return {
                'success': True,
                'daily_forecast': daily_forecast.to_dict('records'),
                'hourly_forecast': hourly_forecast.to_dict('records'),
                'peak_hours': peak_hours[['ds', 'adjusted_generation']].to_dict('records'),
                'total_generation_24h': float(forecast['adjusted_generation'].head(24).sum()),
                'confidence_score': self._calculate_confidence_score(forecast),
                'forecast_period': {
                    'start': forecast_data['date'][0].isoformat(),
                    'end': forecast_data['date'][-1].isoformat()
                }
            }
            
        except Exception as e:
            logger.error(f"Solar prediction failed: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def calculate_pkr_savings(self, solar_generation: float, consumption: float, 
                             disco_region: str = 'IESCO') -> Dict:
        """Calculate savings in PKR with all applicable charges"""
        try:
            # Get DISCO-specific loss factor
            loss_factor = self.disco_losses.get(disco_region.upper(), 0.13)
            
            # Calculate net metering credits
            export_to_grid = max(0, solar_generation - consumption)
            import_from_grid = max(0, consumption - solar_generation)
            
            # Calculate export credits (with DISCO losses)
            export_credits = export_to_grid * self.base_tariff * (1 - loss_factor)
            
            # Calculate import costs that were avoided
            import_savings = import_from_grid * self.base_tariff
            
            # Add FCA savings
            fca_savings = (export_to_grid + import_from_grid) * self.fca_rate
            
            # Calculate GST on savings
            total_unit_savings = export_credits + import_savings
            gst_amount = total_unit_savings * self.gst_rate
            
            # Total savings
            total_savings = total_unit_savings + fca_savings - gst_amount + self.tv_fee
            
            return {
                'success': True,
                'savings_breakdown': {
                    'export_credits': round(export_credits, 2),
                    'import_savings': round(import_savings, 2),
                    'fca_savings': round(fca_savings, 2),
                    'gst_deduction': round(gst_amount, 2),
                    'tv_fee_addition': round(self.tv_fee, 2),
                    'total_savings': round(total_savings, 2)
                },
                'energy_flow': {
                    'solar_generation': round(solar_generation, 2),
                    'home_consumption': round(consumption, 2),
                    'export_to_grid': round(export_to_grid, 2),
                    'import_from_grid': round(import_from_grid, 2)
                },
                'tariff_info': {
                    'base_tariff': self.base_tariff,
                    'fca_rate': self.fca_rate,
                    'gst_rate': self.gst_rate * 100,
                    'disco_loss_factor': loss_factor * 100,
                    'disco_region': disco_region.upper()
                }
            }
            
        except Exception as e:
            logger.error(f"PKR savings calculation failed: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def detect_anomalies(self, current_generation: float, expected_generation: float,
                        threshold_percentage: float = 0.15) -> Dict:
        """Detect anomalies in solar generation"""
        try:
            if expected_generation == 0:
                return {'success': False, 'error': 'Expected generation cannot be zero'}
            
            deviation = abs(current_generation - expected_generation) / expected_generation
            
            anomalies = []
            
            if deviation > threshold_percentage:
                severity = 'high' if deviation > 0.25 else 'medium'
                
                if current_generation < expected_generation:
                    anomaly_type = 'underperformance'
                    possible_causes = self._identify_underperformance_causes(deviation)
                else:
                    anomaly_type = 'overperformance'
                    possible_causes = ['System optimization', 'Weather model underestimation']
                
                anomalies.append({
                    'type': anomaly_type,
                    'severity': severity,
                    'deviation_percentage': round(deviation * 100, 2),
                    'current_generation': round(current_generation, 2),
                    'expected_generation': round(expected_generation, 2),
                    'possible_causes': possible_causes,
                    'timestamp': datetime.now().isoformat()
                })
            
            return {
                'success': True,
                'has_anomalies': len(anomalies) > 0,
                'anomalies': anomalies,
                'performance_ratio': round(current_generation / expected_generation, 3)
            }
            
        except Exception as e:
            logger.error(f"Anomaly detection failed: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def predict_load_shedding(self, historical_outages: pd.DataFrame, 
                             weather_data: Dict = None) -> Dict:
        """Predict load shedding patterns based on historical data"""
        try:
            if historical_outages.empty:
                return {'success': False, 'error': 'No historical outage data'}
            
            # Analyze outage patterns by time of day
            outage_patterns = historical_outages.groupby(
                historical_outages['timestamp'].dt.hour
            ).agg({
                'duration_minutes': 'mean',
                'frequency': 'count'
            }).reset_index()
            
            # Find high-risk periods
            high_risk_periods = outage_patterns.nlargest(4, 'frequency')
            
            # Predict today's outage probability
            current_hour = datetime.now().hour
            current_pattern = outage_patterns[outage_patterns['timestamp'] == current_hour]
            
            outage_probability = 0
            if not current_pattern.empty:
                outage_probability = min(100, (current_pattern['frequency'].values[0] / 
                                             historical_outages['timestamp'].dt.date.nunique()) * 100)
            
            # Battery backup recommendations
            battery_recommendation = self._calculate_battery_backup(
                high_risk_periods,
                historical_outages['duration_minutes'].mean()
            )
            
            return {
                'success': True,
                'outage_probability': round(outage_probability, 2),
                'high_risk_periods': high_risk_periods[['timestamp', 'duration_minutes']].to_dict('records'),
                'average_outage_duration': round(historical_outages['duration_minutes'].mean(), 1),
                'battery_recommendation': battery_recommendation,
                'predicted_outages_today': len(high_risk_periods)
            }
            
        except Exception as e:
            logger.error(f"Load shedding prediction failed: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def get_smart_load_shifting_advice(self, solar_forecast: Dict, 
                                      appliances: List[Dict]) -> Dict:
        """Provide smart load shifting recommendations"""
        try:
            if not solar_forecast.get('success'):
                return {'success': False, 'error': 'No valid solar forecast'}
            
            peak_hours = solar_forecast.get('peak_hours', [])
            
            recommendations = []
            total_energy_available = sum(
                hour['adjusted_generation'] for hour in peak_hours
            )
            
            # Sort appliances by power consumption (highest first)
            sorted_appliances = sorted(appliances, 
                                     key=lambda x: x.get('power_rating', 0), 
                                     reverse=True)
            
            for appliance in sorted_appliances:
                if appliance.get('power_rating', 0) <= total_energy_available:
                    recommendations.append({
                        'appliance': appliance['name'],
                        'power_rating': appliance['power_rating'],
                        'recommended_time': peak_hours[0]['ds'] if peak_hours else None,
                        'estimated_cost_savings': round(
                            appliance['power_rating'] * self.base_tariff, 2
                        ),
                        'priority': 'high' if appliance['power_rating'] > 2.0 else 'medium'
                    })
                    total_energy_available -= appliance['power_rating']
            
            return {
                'success': True,
                'recommendations': recommendations,
                'peak_solar_window': {
                    'start': peak_hours[0]['ds'] if peak_hours else None,
                    'end': peak_hours[-1]['ds'] if peak_hours else None
                },
                'total_savings_potential': round(
                    sum(rec['estimated_cost_savings'] for rec in recommendations), 2
                )
            }
            
        except Exception as e:
            logger.error(f"Load shifting advice failed: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def _calculate_confidence_score(self, forecast) -> float:
        """Calculate confidence score for predictions (0-100)"""
        try:
            # Calculate based on width of confidence intervals
            uncertainty = (forecast['yhat_upper'] - forecast['yhat_lower']).mean()
            prediction_mean = forecast['yhat'].mean()
            
            if prediction_mean > 0:
                confidence = 100 - (uncertainty / prediction_mean * 100)
            else:
                confidence = 50
            
            return round(max(0, min(100, confidence)), 2)
            
        except Exception:
            return 75.0  # Default confidence
    
    def _identify_underperformance_causes(self, deviation: float) -> List[str]:
        """Identify possible causes for underperformance"""
        causes = []
        
        if deviation > 0.30:
            causes.append('Major system fault or inverter failure')
            causes.append('Severe dust or debris accumulation on panels')
        elif deviation > 0.20:
            causes.append('Partial shading or obstructions')
            causes.append('Dust accumulation requiring cleaning')
            causes.append('Possible inverter efficiency degradation')
        else:
            causes.append('Minor dust accumulation')
            causes.append('Slight weather variations beyond model prediction')
            causes.append('Normal system degradation')
        
        return causes
    
    def _calculate_battery_backup(self, high_risk_periods, avg_duration_minutes) -> Dict:
        """Calculate recommended battery backup capacity"""
        # Estimate required battery capacity based on outage patterns
        required_capacity = avg_duration_minutes / 60 * 2.5  # kWh (assuming 2.5kW average load)
        
        return {
            'recommended_capacity_kwh': round(required_capacity, 2),
            'minimum_backup_hours': round(required_capacity / 2.5, 1),
            'charge_priority': 'Maintain at least 80% charge during high-risk periods',
            'suggested_charging_schedule': 'Charge from 10 AM to 2 PM (peak solar generation)'
        }