import numpy as np
from flask import Blueprint, jsonify, request
from flask_login import login_required, current_user
from services.ai_service import AIService
from services.supabase_service import SupabaseService
from functools import lru_cache
import pandas as pd

api_bp = Blueprint('api', __name__, url_prefix='/api')

ai_service = AIService()

@api_bp.route('/forecast/solar', methods=['GET'])
@login_required
def get_solar_forecast():
    """Get solar generation forecast for the next 24-48 hours"""
    try:
        # Get user's location and system details
        user_data = SupabaseService.get_user_by_id(current_user.id)
        
        latitude = request.args.get('lat', user_data.latitude if hasattr(user_data, 'latitude') else 33.6844)
        longitude = request.args.get('lon', user_data.longitude if hasattr(user_data, 'longitude') else 73.0479)
        system_capacity = float(request.args.get('capacity', getattr(user_data, 'system_capacity', 5.0)))
        
        # Fetch weather forecast
        weather = ai_service.fetch_weather_forecast(latitude, longitude, days=2)
        
        if not weather['success']:
            return jsonify({'error': 'Failed to fetch weather data'}), 500
        
        # Get historical data and train model
        historical_data = pd.DataFrame()  # Would fetch from database
        if not historical_data.empty:
            model = ai_service.train_solar_forecast_model(historical_data)
        else:
            # Use a pre-trained model if available
            model = ai_service.train_solar_forecast_model(_get_sample_training_data())
        
        if model:
            prediction = ai_service.predict_solar_generation(
                model, weather, system_capacity=system_capacity
            )
            return jsonify(prediction)
        else:
            return jsonify({'error': 'Model training failed'}), 500
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@api_bp.route('/savings/calculate', methods=['POST'])
@login_required
def calculate_savings():
    """Calculate PKR savings based on generation and consumption"""
    try:
        data = request.get_json()
        
        solar_generation = float(data.get('solar_generation', 0))
        consumption = float(data.get('consumption', 0))
        disco_region = data.get('disco_region', 'IESCO')
        
        savings = ai_service.calculate_pkr_savings(
            solar_generation, consumption, disco_region
        )
        
        return jsonify(savings)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@api_bp.route('/anomalies/detect', methods=['POST'])
@login_required
def detect_anomalies():
    """Detect anomalies in solar generation"""
    try:
        data = request.get_json()
        
        current_gen = float(data.get('current_generation', 0))
        expected_gen = float(data.get('expected_generation', 0))
        threshold = float(data.get('threshold', 0.15))
        
        anomalies = ai_service.detect_anomalies(
            current_gen, expected_gen, threshold
        )
        
        return jsonify(anomalies)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@api_bp.route('/load-shedding/predict', methods=['GET'])
@login_required
def predict_load_shedding():
    """Get load shedding predictions"""
    try:
        # Fetch historical outage data
        response = SupabaseService.get_client().table('power_outages') \
            .select('*') \
            .eq('user_id', current_user.id) \
            .order('timestamp', desc=True) \
            .limit(500) \
            .execute()
        
        if response.data:
            historical_outages = pd.DataFrame(response.data)
            prediction = ai_service.predict_load_shedding(historical_outages)
            return jsonify(prediction)
        else:
            return jsonify({'error': 'No historical outage data available'}), 404
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@api_bp.route('/load-shifting/recommendations', methods=['POST'])
@login_required
def get_load_shifting_recommendations():
    """Get smart load shifting recommendations"""
    try:
        data = request.get_json()
        appliances = data.get('appliances', [])
        
        # First get solar forecast
        user_data = SupabaseService.get_user_by_id(current_user.id)
        weather = ai_service.fetch_weather_forecast(
            getattr(user_data, 'latitude', 33.6844),
            getattr(user_data, 'longitude', 73.0479)
        )
        
        if weather['success']:
            model = ai_service.train_solar_forecast_model(_get_sample_training_data())
            if model:
                forecast = ai_service.predict_solar_generation(model, weather)
                recommendations = ai_service.get_smart_load_shifting_advice(forecast, appliances)
                return jsonify(recommendations)
        
        return jsonify({'error': 'Failed to generate recommendations'}), 500
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@api_bp.route('/weather/current', methods=['GET'])
@login_required
def get_current_weather():
    """Get current weather conditions"""
    try:
        lat = request.args.get('lat', 33.6844)
        lon = request.args.get('lon', 73.0479)
        
        weather = ai_service.fetch_weather_forecast(float(lat), float(lon), days=1)
        
        if weather['success']:
            # Return only current conditions
            current = {
                'temperature': float(weather['data']['temperature'][0]),
                'humidity': float(weather['data']['humidity'][0]),
                'cloud_cover': float(weather['data']['cloud_cover'][0]),
                'wind_speed': float(weather['data']['wind_speed'][0]),
                'shortwave_radiation': float(weather['data']['shortwave_radiation'][0])
            }
            return jsonify({'success': True, 'current': current})
        
        return jsonify({'error': 'Weather data unavailable'}), 500
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

def _get_sample_training_data():
    """Generate sample training data for initial model training"""
    dates = pd.date_range(start='2024-01-01', end='2024-01-31', freq='H')
    data = {
        'timestamp': dates,
        'power_generation': [max(0, 5 * (0.5 + 0.5 * np.sin(np.pi * (h - 6) / 12))) 
                           for h in range(len(dates))],
        'temperature': [25 + 10 * np.sin(np.pi * (h - 6) / 12) for h in range(len(dates))],
        'cloud_cover': [np.random.uniform(0, 0.5) for _ in range(len(dates))],
        'humidity': [40 + 20 * np.random.random() for _ in range(len(dates))],
        'shortwave_radiation': [max(0, 800 * (0.3 + 0.7 * np.sin(np.pi * (h - 6) / 12))) 
                               for h in range(len(dates))]
    }
    return pd.DataFrame(data)
