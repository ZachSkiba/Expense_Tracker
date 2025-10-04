/**
 * UI Helpers - Utility functions for formatting and UI operations
 */

class BudgetUIHelpers {
    static formatCurrency(amount) {
        if (typeof amount !== 'number') {
            amount = parseFloat(amount) || 0;
        }
        return new Intl.NumberFormat('en-US', {
            style: 'currency',
            currency: 'USD',
            minimumFractionDigits: 0,
            maximumFractionDigits: 0
        }).format(amount);
    }
    
    static formatPercentage(value) {
        return `${value.toFixed(1)}%`;
    }
    
    static escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
    
    static generateColors(count) {
        const baseColors = [
            '#667eea', '#764ba2', '#f093fb', '#4facfe',
            '#43e97b', '#fa709a', '#fee140', '#30cfd0',
            '#a8edea', '#fed6e3', '#c471ed', '#12c2e9'
        ];
        
        const colors = [];
        for (let i = 0; i < count; i++) {
            colors.push(baseColors[i % baseColors.length]);
        }
        
        return colors;
    }
    
    static showLoading(show) {
        const indicator = document.getElementById('loading-indicator');
        if (indicator) {
            indicator.style.display = show ? 'flex' : 'none';
        }
    }
    
    static showError(message) {
        const container = document.getElementById('error-container');
        const messageEl = container?.querySelector('.error-message');
        
        if (container && messageEl) {
            messageEl.textContent = message;
            container.style.display = 'block';
            
            setTimeout(() => {
                container.style.display = 'none';
            }, 5000);
        } else {
            console.error('[UI_HELPERS] Error:', message);
            alert(message);
        }
    }
    
    static getMonthNames() {
        return ['January', 'February', 'March', 'April', 'May', 'June',
                'July', 'August', 'September', 'October', 'November', 'December'];
    }
    
    static groupByDescription(items) {
        const grouped = {};
        items.forEach(item => {
            const key = item.description || 'Other';
            if (!grouped[key]) {
                grouped[key] = { total: 0, count: 0, items: [] };
            }
            grouped[key].total += item.amount;
            grouped[key].count += 1;
            grouped[key].items.push(item);
        });
        return grouped;
    }
}