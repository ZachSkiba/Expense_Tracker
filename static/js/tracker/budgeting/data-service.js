/**
 * Data Service - Handles all API calls and data fetching
 */

class BudgetDataService {
    constructor(apiBaseUrl, groupId, userId) {
        this.apiBaseUrl = apiBaseUrl;
        this.groupId = groupId;
        this.userId = userId;
    }
    
    async fetchAvailablePeriods(years = null) {
        try {
            let url = `${this.apiBaseUrl}/api/available-periods`;
            if (years && years.length > 0) {
                url += `?years=${years.join(',')}`; 
            }
            
            const response = await fetch(url);
            const result = await response.json();
            
            if (result.success) {
                return {
                    success: true,
                    years: result.data.years || [],
                    months: result.data.months || []
                };
            }
            
            throw new Error(result.error || 'Failed to fetch available periods');
        } catch (error) {
            console.error('[DATA_SERVICE] Error fetching available periods:', error);
            return { success: false, error: error.message };
        }
    }
    
    async fetchSummary(years, months) {
        try {
            const yearsParam = years.join(',');
            const monthsParam = months.join(',');
            const url = `${this.apiBaseUrl}/api/summary?years=${yearsParam}&months=${monthsParam}`;
            
            console.log('[DATA_SERVICE] Fetching summary from:', url);
            
            const response = await fetch(url);
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
            const result = await response.json();
            
            if (result.success) {
                return { success: true, data: result.data };
            }
            
            throw new Error(result.error || 'Failed to load data');
        } catch (error) {
            console.error('[DATA_SERVICE] Error fetching summary:', error);
            return { success: false, error: error.message };
        }
    }

    async fetchTimeSeries(years, months) {
        try {
            const yearsParam = years.join(',');
            const monthsParam = months.join(',');
            const url = `${this.apiBaseUrl}/api/time-series?years=${yearsParam}&months=${monthsParam}`;
            
            console.log('[DATA_SERVICE] Fetching time series from:', url);
            
            const response = await fetch(url);
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
            const result = await response.json();
            
            if (result.success) {
                return { success: true, data: result.data };
            }
            
            throw new Error(result.error || 'Failed to load time series data');
        } catch (error) {
            console.error('[DATA_SERVICE] Error fetching time series:', error);
            return { success: false, error: error.message };
        }
    }
    
    async fetchRecommendations(year, month) {
        try {
            const url = `${this.apiBaseUrl}/api/recommendations?year=${year}&month=${month}`;
            
            const response = await fetch(url);
            const result = await response.json();
            
            if (result.success && result.recommendations) {
                return { success: true, recommendations: result.recommendations };
            }
            
            return { success: true, recommendations: [] };
        } catch (error) {
            console.error('[DATA_SERVICE] Error fetching recommendations:', error);
            return { success: false, recommendations: [] };
        }
    }
}