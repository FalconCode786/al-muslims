// Enhanced Dashboard Manager with AI Integration
class DashboardManager {
    constructor() {
        this.apiBaseUrl = '/api';
        this.refreshInterval = 30000; // 30 seconds for real-time data
        this.forecastRefreshInterval = 300000; // 5 minutes for forecasts
        this.charts = {};
        this.currentTimeRange = '24h';
        this.init();
    }
    
    init() {
        this.initializeAllCharts();
        this.loadInitialData();
        this.setupAutoRefresh();
        this.setupEventListeners();
    }
    
    initializeAllCharts() {
        // Initialize power flow chart if element exists
        const powerFlowCtx = document.getElementById('powerFlowChart');
        if (powerFlowCtx) {
            this.charts.powerFlow = new Chart(powerFlowCtx.getContext('2d'), {
                type: 'line',
                data: {
                    labels: [],
                    datasets: [
                        {
                            label: 'Solar Generation',
                            data: [],
                            borderColor: '#EAB308',
                            backgroundColor: 'rgba(234, 179, 8, 0.1)',
                            fill: true,
                            tension: 0.4,
                            borderWidth: 2
                        },
                        {
                            label: 'Consumption',
                            data: [],
                            borderColor: '#3B82F6',
                            backgroundColor: 'rgba(59, 130, 246, 0.1)',
                            fill: true,
                            tension: 0.4,
                            borderWidth: 2
                        },
                        {
                            label: 'Grid Export',
                            data: [],
                            borderColor: '#22C55E',
                            backgroundColor: 'rgba(34, 197, 94, 0.1)',
                            fill: true,
                            tension: 0.4,
                            borderWidth: 2
                        }
                    ]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    interaction: {
                        intersect: false,
                        mode: 'index'
                    },
                    plugins: {
                        legend: { display: false },
                        tooltip: {
                            backgroundColor: '#0A1929',
                            padding: 12,
                            cornerRadius: 8
                        }
                    },
                    scales: {
                        x: { grid: { display: false } },
                        y: {
                            beginAtZero: true,
                            grid: { color: '#f3f4f6' },
                            ticks: {
                                callback: (value) => value + ' kW'
                            }
                        }
                    }
                }
            });
        }
    }
    
    loadInitialData() {
        this.fetchRealTimeData();
        this.fetchSolarForecast();
        this.fetchLoadSheddingPrediction();
        this.checkAnomalies();
    }
    
    setupAutoRefresh() {
        setInterval(() => this.fetchRealTimeData(), this.refreshInterval);
        setInterval(() => this.fetchSolarForecast(), this.forecastRefreshInterval);
        setInterval(() => this.fetchLoadSheddingPrediction(), this.forecastRefreshInterval * 2);
        setInterval(() => this.checkAnomalies(), this.refreshInterval * 10);
    }
    
    setupEventListeners() {
        // Time range buttons
        document.querySelectorAll('[id^="btn-"]').forEach(btn => {
            btn.addEventListener('click', (e) => {
                this.currentTimeRange = e.target.id.replace('btn-', '');
                this.fetchRealTimeData();
            });
        });
    }
    
    async fetchRealTimeData() {
        try {
            const response = await fetch(`${this.apiBaseUrl}/forecast/solar?lat=33.6844&lon=73.0479&capacity=5.0`);
            const data = await response.json();
            
            if (data.success) {
                this.updateDashboardStats(data);
                this.updatePowerFlowChart(data);
                this.generateAIInsights(data);
            }
        } catch (error) {
            console.error('Failed to fetch real-time data:', error);
            this.loadSimulatedData();
        }
    }
    
    async fetchSolarForecast() {
        try {
            const response = await fetch(`${this.apiBaseUrl}/forecast/solar?lat=33.6844&lon=73.0479`);
            const data = await response.json();
            
            if (data.success) {
                this.updateForecastCard(data);
            }
        } catch (error) {
            console.error('Failed to fetch forecast:', error);
        }
    }
    
    async fetchLoadSheddingPrediction() {
        try {
            const response = await fetch(`${this.apiBaseUrl}/load-shedding/predict`);
            const data = await response.json();
            
            if (data.success) {
                this.updateLoadSheddingCard(data);
            }
        } catch (error) {
            console.error('Failed to fetch load shedding prediction:', error);
        }
    }
    
    async checkAnomalies() {
        try {
            const currentGen = parseFloat(
                document.getElementById('current-generation')?.textContent?.replace(' kW', '') || 4.0
            );
            
            const response = await fetch(`${this.apiBaseUrl}/anomalies/detect`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    current_generation: currentGen,
                    expected_generation: 4.0,
                    threshold: 0.15
                })
            });
            
            const data = await response.json();
            
            if (data.success && data.has_anomalies) {
                this.displayAnomalyAlerts(data.anomalies);
            }
        } catch (error) {
            console.error('Failed to check anomalies:', error);
        }
    }
    
    updateDashboardStats(data) {
        if (!data.hourly_forecast || data.hourly_forecast.length === 0) return;
        
        const current = data.hourly_forecast[0];
        const generation = current.adjusted_generation || 0;
        const consumption = 2.5; // Would come from actual consumption data
        const exportToGrid = Math.max(0, generation - consumption);
        
        // Update text elements
        const elements = {
            'current-generation': generation.toFixed(1) + ' kW',
            'current-consumption': consumption.toFixed(1) + ' kW',
            'grid-export': exportToGrid.toFixed(1) + ' kW'
        };
        
        Object.entries(elements).forEach(([id, value]) => {
            const element = document.getElementById(id);
            if (element) element.textContent = value;
        });
        
        // Update progress bars
        const maxPower = 5.0; // System capacity
        this.updateProgressBar('generation-bar', (generation / maxPower) * 100);
        this.updateProgressBar('consumption-bar', (consumption / maxPower) * 100);
        this.updateProgressBar('export-bar', (exportToGrid / maxPower) * 100);
        
        // Calculate and update savings
        this.calculateAndUpdateSavings(generation, consumption);
    }
    
    updateProgressBar(id, percentage) {
        const bar = document.getElementById(id);
        if (bar) {
            bar.style.width = Math.min(100, Math.max(0, percentage)) + '%';
        }
    }
    
    async calculateAndUpdateSavings(solarGen, consumption) {
        try {
            const response = await fetch(`${this.apiBaseUrl}/savings/calculate`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    solar_generation: solarGen,
                    consumption: consumption,
                    disco_region: 'IESCO'
                })
            });
            
            const data = await response.json();
            
            if (data.success) {
                const savings = data.savings_breakdown;
                const dailySavings = document.getElementById('daily-savings');
                const monthlyEstimate = document.getElementById('savings-estimate');
                
                if (dailySavings) {
                    dailySavings.textContent = 'PKR ' + savings.total_savings.toFixed(0);
                }
                if (monthlyEstimate) {
                    monthlyEstimate.textContent = 'Estimated monthly: PKR ' + (savings.total_savings * 30).toFixed(0);
                }
            }
        } catch (error) {
            console.error('Failed to calculate savings:', error);
        }
    }
    
    updatePowerFlowChart(data) {
        if (!this.charts.powerFlow || !data.hourly_forecast) return;
        
        const forecast = data.hourly_forecast.slice(0, 24);
        const labels = forecast.map(f => {
            const date = new Date(f.ds);
            return date.getHours() + ':00';
        });
        
        const generationData = forecast.map(f => f.adjusted_generation || 0);
        const consumptionData = forecast.map(() => 1.5 + Math.random() * 2);
        const exportData = generationData.map((gen, i) => Math.max(0, gen - consumptionData[i]));
        
        this.charts.powerFlow.data.labels = labels;
        this.charts.powerFlow.data.datasets[0].data = generationData;
        this.charts.powerFlow.data.datasets[1].data = consumptionData;
        this.charts.powerFlow.data.datasets[2].data = exportData;
        this.charts.powerFlow.update();
    }
    
    updateForecastCard(data) {
        const forecastDiv = document.getElementById('tomorrow-forecast');
        if (!forecastDiv) return;
        
        const totalGen = data.total_generation_24h || 0;
        const confidence = data.confidence_score || 0;
        const peakHours = data.peak_hours || [];
        
        const confidenceClass = confidence > 80 ? 'text-green-400' : 
                               confidence > 60 ? 'text-yellow-400' : 'text-red-400';
        
        forecastDiv.innerHTML = `
            <div class="flex justify-between items-center">
                <span class="text-gray-400">Expected Generation</span>
                <span class="text-xl font-bold">${totalGen.toFixed(1)} kWh</span>
            </div>
            <div class="flex justify-between items-center">
                <span class="text-gray-400">Peak Hours</span>
                <span class="text-sm">${peakHours.length > 0 ? this.formatPeakHours(peakHours) : 'Calculating...'}</span>
            </div>
            <div class="flex justify-between items-center">
                <span class="text-gray-400">Confidence</span>
                <span class="text-sm ${confidenceClass}">${confidence}%</span>
            </div>
            ${confidence < 70 ? `
            <div class="mt-4 p-3 bg-red-500/20 rounded-lg text-sm">
                <i data-lucide="alert-triangle" class="h-4 w-4 inline mr-2"></i>
                <span>Low confidence due to variable weather conditions</span>
            </div>
            ` : ''}
        `;
        
        lucide.createIcons();
    }
    
    updateLoadSheddingCard(data) {
        const card = document.getElementById('load-shedding-card');
        const content = document.getElementById('load-shedding-content');
        
        if (!card || !content) return;
        
        if (data.outage_probability > 20) {
            card.classList.remove('hidden');
            content.innerHTML = `
                <div class="flex justify-between items-center">
                    <span class="text-sm text-gray-600">Outage Probability</span>
                    <span class="font-semibold ${data.outage_probability > 60 ? 'text-red-600' : 'text-yellow-600'}">
                        ${data.outage_probability}%
                    </span>
                </div>
                <div class="flex justify-between items-center">
                    <span class="text-sm text-gray-600">Avg. Duration</span>
                    <span class="font-semibold">${data.average_outage_duration} min</span>
                </div>
                ${data.battery_recommendation ? `
                <div class="mt-3 p-3 bg-blue-50 rounded-lg">
                    <p class="text-sm text-blue-800">
                        <i data-lucide="battery-charging" class="h-4 w-4 inline mr-2"></i>
                        ${data.battery_recommendation.charge_priority}
                    </p>
                </div>
                ` : ''}
            `;
            lucide.createIcons();
        } else {
            card.classList.add('hidden');
        }
    }
    
    generateAIInsights(data) {
        const banner = document.getElementById('ai-insights-banner');
        const message = document.getElementById('ai-insight-message');
        
        if (!banner || !message) return;
        
        const totalGen = data.total_generation_24h || 0;
        let insight = '';
        
        if (totalGen > 15) {
            insight = 'High solar generation expected. Schedule heavy appliance usage between 10 AM - 2 PM to maximize savings.';
        } else if (totalGen < 5) {
            insight = 'Low solar generation predicted. Minimize non-essential usage and ensure battery backup is fully charged.';
        } else {
            insight = 'Moderate solar generation expected. Normal usage patterns recommended with optional load shifting for additional savings.';
        }
        
        message.textContent = insight;
        banner.classList.remove('hidden');
        lucide.createIcons();
    }
    
    displayAnomalyAlerts(anomalies) {
        const alertsDiv = document.getElementById('anomaly-alerts');
        const listDiv = document.getElementById('anomaly-list');
        
        if (!alertsDiv || !listDiv) return;
        
        alertsDiv.classList.remove('hidden');
        listDiv.innerHTML = anomalies.map(anomaly => `
            <div class="flex items-start space-x-4 p-4 ${anomaly.severity === 'high' ? 'bg-red-50' : 'bg-yellow-50'} rounded-lg">
                <i data-lucide="${anomaly.severity === 'high' ? 'alert-triangle' : 'alert-circle'}" 
                   class="h-6 w-6 ${anomaly.severity === 'high' ? 'text-red-600' : 'text-yellow-600'} flex-shrink-0"></i>
                <div>
                    <p class="font-medium ${anomaly.severity === 'high' ? 'text-red-800' : 'text-yellow-800'}">
                        ${anomaly.type === 'underperformance' ? 'Underperformance Detected' : 'Overperformance Detected'}
                    </p>
                    <p class="text-sm ${anomaly.severity === 'high' ? 'text-red-700' : 'text-yellow-700'} mt-1">
                        Deviation: ${anomaly.deviation_percentage}% from expected generation
                    </p>
                    ${anomaly.possible_causes ? `
                    <div class="mt-2">
                        <p class="text-xs font-medium text-gray-600">Possible causes:</p>
                        <ul class="list-disc list-inside text-xs text-gray-600 mt-1">
                            ${anomaly.possible_causes.map(cause => `<li>${cause}</li>`).join('')}
                        </ul>
                    </div>
                    ` : ''}
                </div>
            </div>
        `).join('');
        
        lucide.createIcons();
    }
    
    formatPeakHours(peakHours) {
        if (!peakHours || peakHours.length === 0) return 'N/A';
        const start = new Date(peakHours[0].ds);
        const end = new Date(peakHours[peakHours.length - 1].ds);
        return `${start.getHours()}:00 - ${end.getHours()}:00`;
    }
    
    loadSimulatedData() {
        // Fallback simulated data for development
        const now = new Date();
        const hour = now.getHours();
        const solarGeneration = hour >= 6 && hour <= 18 ? 
            Math.random() * 5 * Math.sin((hour - 6) * Math.PI / 12) : 0;
        const consumption = 1 + Math.random() * 3;
        const gridExport = Math.max(0, solarGeneration - consumption);
        
        this.updateElement('current-generation', solarGeneration.toFixed(1) + ' kW');
        this.updateElement('current-consumption', consumption.toFixed(1) + ' kW');
        this.updateElement('grid-export', gridExport.toFixed(1) + ' kW');
        
        const savings = gridExport * 35; // Approximate PKR per kWh
        this.updateElement('daily-savings', 'PKR ' + savings.toFixed(0));
        this.updateElement('savings-estimate', 'Estimated monthly: PKR ' + (savings * 30).toFixed(0));
    }
    
    updateElement(id, value) {
        const element = document.getElementById(id);
        if (element) element.textContent = value;
    }
    
    destroy() {
        // Cleanup charts and intervals
        Object.values(this.charts).forEach(chart => chart.destroy());
    }
}

// Initialize dashboard when DOM is ready
let dashboard = null;
document.addEventListener('DOMContentLoaded', () => {
    if (document.querySelector('[data-dashboard]')) {
        dashboard = new DashboardManager();
    }
});