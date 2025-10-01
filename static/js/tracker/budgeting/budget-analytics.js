/**
 * Budget Analytics - Main JavaScript Controller
 * Handles data loading, UI updates, and chart rendering
 */

class BudgetAnalytics {
    constructor() {
        this.groupId = window.budgetData.groupId;
        this.userId = window.budgetData.userId;
        this.currentYear = window.budgetData.currentYear;
        this.selectedMonths = window.budgetData.selectedMonths || [];
        this.apiBaseUrl = window.budgetData.apiBaseUrl;
        
        this.currentData = null;
        this.selectedCategory = null;
        this.categoryPieChart = null;
        
        this.init();
    }
    
    init() {
        console.log('[BUDGET_ANALYTICS] Initializing...');
        this.bindEvents();
        this.loadData();
    }
    
    bindEvents() {
        // Apply filters button
        const applyBtn = document.getElementById('apply-filters');
        if (applyBtn) {
            applyBtn.addEventListener('click', () => this.applyFilters());
        }
        
        // Year select change
        const yearSelect = document.getElementById('year-select');
        if (yearSelect) {
            yearSelect.addEventListener('change', () => {
                this.currentYear = parseInt(yearSelect.value);
            });
        }
        
        // Month select all/clear buttons
        document.querySelectorAll('.month-toggle').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const action = e.target.dataset.action;
                this.toggleMonths(action);
            });
        });
        
        // Error close button
        const errorClose = document.querySelector('.error-close');
        if (errorClose) {
            errorClose.addEventListener('click', () => {
                document.getElementById('error-container').style.display = 'none';
            });
        }
    }
    
    toggleMonths(action) {
        const checkboxes = document.querySelectorAll('.month-checkboxes input[type="checkbox"]');
        
        if (action === 'select-all') {
            checkboxes.forEach(cb => cb.checked = true);
        } else if (action === 'clear') {
            checkboxes.forEach(cb => cb.checked = false);
        }
    }
    
    applyFilters() {
        // Get selected year
        const yearSelect = document.getElementById('year-select');
        this.currentYear = parseInt(yearSelect.value);
        
        // Get selected months
        const monthCheckboxes = document.querySelectorAll('.month-checkboxes input[type="checkbox"]:checked');
        this.selectedMonths = Array.from(monthCheckboxes).map(cb => parseInt(cb.value));
        
        if (this.selectedMonths.length === 0) {
            this.showError('Please select at least one month');
            return;
        }
        
        console.log('[BUDGET_ANALYTICS] Applying filters:', {
            year: this.currentYear,
            months: this.selectedMonths
        });
        
        this.loadData();
    }
    
    async loadData() {
        this.showLoading(true);
        
        try {
            // Build query parameters
            const monthsParam = this.selectedMonths.join(',');
            const url = `${this.apiBaseUrl}/api/summary?year=${this.currentYear}&months=${monthsParam}`;
            
            console.log('[BUDGET_ANALYTICS] Fetching data from:', url);
            
            const response = await fetch(url);
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
            const result = await response.json();
            
            if (result.success) {
                this.currentData = result.data;
                console.log('[BUDGET_ANALYTICS] Data loaded:', this.currentData);
                this.updateUI();
            } else {
                throw new Error(result.error || 'Failed to load data');
            }
            
        } catch (error) {
            console.error('[BUDGET_ANALYTICS] Error loading data:', error);
            this.showError('Failed to load budget data: ' + error.message);
        } finally {
            this.showLoading(false);
        }
    }
    
    updateUI() {
        if (!this.currentData) {
            console.warn('[BUDGET_ANALYTICS] No data to display');
            return;
        }
        
        this.updateKPIs();
        this.updateEssentials();
        this.updateAllocations();
        this.loadRecommendations();
    }
    
    updateKPIs() {
        const { income, expenses, net_summary } = this.currentData;
        
        // Monthly Income
        const incomeEl = document.getElementById('kpi-income');
        if (incomeEl) {
            incomeEl.textContent = this.formatCurrency(income.total);
        }
        
        // Essentials Total
        const essentialsEl = document.getElementById('kpi-essentials');
        if (essentialsEl) {
            essentialsEl.textContent = this.formatCurrency(expenses.essentials);
        }
        
        // Discretionary Left
        const discretionaryEl = document.getElementById('kpi-discretionary');
        if (discretionaryEl) {
            discretionaryEl.textContent = this.formatCurrency(net_summary.discretionary_left);
        }
        
        // Income display in right column
        const incomeDisplayEl = document.getElementById('income-display');
        if (incomeDisplayEl) {
            incomeDisplayEl.textContent = this.formatCurrency(income.total);
        }
        
        // Total essentials in bottom card
        const totalEssentialsEl = document.getElementById('total-essentials');
        if (totalEssentialsEl) {
            totalEssentialsEl.textContent = this.formatCurrency(expenses.essentials);
        }
        
        console.log('[BUDGET_ANALYTICS] KPIs updated');
    }
    
    updateEssentials() {
        const container = document.getElementById('essentials-list');
        if (!container) return;
        
        const { expenses } = this.currentData;
        const categoryDetails = expenses.category_details || {};
        
        // Filter to only essential categories
        const essentialCategories = Object.entries(categoryDetails)
            .filter(([name, data]) => {
                // Check if any item in this category is marked as essential
                return data.items && data.items.some(item => item.budget_type === 'essential');
            });
        
        if (essentialCategories.length === 0) {
            container.innerHTML = '<div class="loading">No essential expenses found for this period</div>';
            return;
        }
        
        container.innerHTML = '';
        
        essentialCategories.forEach(([categoryName, data]) => {
            const item = this.createCategoryItem(categoryName, data, true);
            container.appendChild(item);
        });
        
        console.log('[BUDGET_ANALYTICS] Essentials updated:', essentialCategories.length, 'categories');
    }
    
    createCategoryItem(categoryName, data, isEssential = false) {
        const div = document.createElement('div');
        div.className = `category-item ${isEssential ? 'essential' : ''}`;
        div.dataset.category = categoryName;
        
        // Determine source (recurring or manual)
        const hasRecurring = data.items.some(item => 
            item.description && item.description.toLowerCase().includes('recurring')
        );
        const source = hasRecurring ? 'Recurring transaction' : 'Manual entry';
        
        div.innerHTML = `
            <div class="category-info">
                <div class="category-name">${this.escapeHtml(categoryName)}</div>
                <div class="category-source">${source}</div>
            </div>
            <div class="category-amount">
                ${this.formatCurrency(data.total)}
                <div class="category-budget">Budgeted</div>
            </div>
        `;
        
        // Click handler to show breakdown
        div.addEventListener('click', () => {
            this.showCategoryBreakdown(categoryName, data);
            
            // Update active state
            document.querySelectorAll('.category-item').forEach(el => el.classList.remove('active'));
            div.classList.add('active');
        });
        
        return div;
    }
    
    showCategoryBreakdown(categoryName, data) {
        this.selectedCategory = categoryName;
        
        const contentDiv = document.getElementById('category-detail-content');
        const instructionText = document.querySelector('.instruction-text');
        const categoryNameEl = document.getElementById('selected-category-name');
        const subcategoryList = document.getElementById('subcategory-list');
        
        if (instructionText) instructionText.style.display = 'none';
        if (contentDiv) contentDiv.style.display = 'block';
        if (categoryNameEl) categoryNameEl.textContent = categoryName;
        
        // Group items by description (subcategory)
        const subcategories = {};
        data.items.forEach(item => {
            const subcatName = item.description || 'Other';
            if (!subcategories[subcatName]) {
                subcategories[subcatName] = {
                    total: 0,
                    count: 0,
                    items: []
                };
            }
            subcategories[subcatName].total += item.amount;
            subcategories[subcatName].count += 1;
            subcategories[subcatName].items.push(item);
        });
        
        // Update pie chart
        this.updatePieChart(subcategories);
        
        // Update subcategory list
        if (subcategoryList) {
            subcategoryList.innerHTML = '';
            
            Object.entries(subcategories)
                .sort((a, b) => b[1].total - a[1].total)
                .forEach(([subcatName, subcatData]) => {
                    const percentage = (subcatData.total / data.total * 100).toFixed(1);
                    
                    const item = document.createElement('div');
                    item.className = 'subcategory-item';
                    item.innerHTML = `
                        <div class="subcategory-name">${this.escapeHtml(subcatName)}</div>
                        <div class="subcategory-details">
                            <span class="subcategory-amount">${this.formatCurrency(subcatData.total)}</span>
                            <span class="subcategory-percentage">${percentage}%</span>
                            <span class="subcategory-count">${subcatData.count} transaction${subcatData.count > 1 ? 's' : ''}</span>
                        </div>
                    `;
                    
                    subcategoryList.appendChild(item);
                });
        }
        
        console.log('[BUDGET_ANALYTICS] Category breakdown shown:', categoryName);
    }
    
    updatePieChart(subcategories) {
        const canvas = document.getElementById('category-pie-chart');
        if (!canvas) return;
        
        // Destroy existing chart
        if (this.categoryPieChart) {
            this.categoryPieChart.destroy();
        }
        
        // Prepare data
        const labels = Object.keys(subcategories);
        const data = Object.values(subcategories).map(s => s.total);
        
        // Generate colors
        const colors = this.generateColors(labels.length);
        
        // Create chart
        const ctx = canvas.getContext('2d');
        this.categoryPieChart = new Chart(ctx, {
            type: 'pie',
            data: {
                labels: labels,
                datasets: [{
                    data: data,
                    backgroundColor: colors,
                    borderWidth: 2,
                    borderColor: '#ffffff'
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: true,
                plugins: {
                    legend: {
                        position: 'bottom',
                        labels: {
                            padding: 15,
                            font: {
                                size: 12
                            }
                        }
                    },
                    tooltip: {
                        callbacks: {
                            label: (context) => {
                                const label = context.label || '';
                                const value = this.formatCurrency(context.parsed);
                                const percentage = ((context.parsed / data.reduce((a, b) => a + b, 0)) * 100).toFixed(1);
                                return `${label}: ${value} (${percentage}%)`;
                            }
                        }
                    }
                }
            }
        });
        
        console.log('[BUDGET_ANALYTICS] Pie chart updated');
    }
    
    updateAllocations() {
        const container = document.getElementById('allocations-list');
        if (!container) return;
        
        const { income, allocations } = this.currentData;
        const totalIncome = income.total;
        
        if (totalIncome === 0) {
            container.innerHTML = '<div class="loading">No income data for this period</div>';
            return;
        }
        
        // Get allocation breakdown by budget type
        const allocationsByType = allocations.by_budget_type || {};
        
        // Define allocation types and recommended percentages (50/30/20 rule adapted)
        const allocationTypes = [
            { name: 'Investments', key: 'investment', recommended: 20, className: 'investment' },
            { name: 'Emergency Fund', key: 'emergency', recommended: 10, className: 'emergency' },
            { name: 'Personal/Fun', key: 'personal', recommended: 15, className: 'personal' },
            { name: 'Debt Payment', key: 'debt', recommended: 5, className: 'debt' }
        ];
        
        container.innerHTML = '';
        
        allocationTypes.forEach(type => {
            const actual = allocationsByType[type.key] || 0;
            const recommended = (totalIncome * type.recommended / 100);
            const actualPercent = totalIncome > 0 ? (actual / totalIncome * 100).toFixed(1) : 0;
            
            const item = document.createElement('div');
            item.className = `allocation-item ${type.className}`;
            
            item.innerHTML = `
                <div class="allocation-header">
                    <div class="allocation-name">${type.name}</div>
                    <div class="allocation-values">
                        <div class="allocation-actual">
                            <div class="allocation-label">Actual</div>
                            <div class="allocation-amount">${this.formatCurrency(actual)}</div>
                        </div>
                        <div class="allocation-recommended">
                            <div class="allocation-label">Recommended</div>
                            <div class="allocation-amount">${this.formatCurrency(recommended)}</div>
                        </div>
                    </div>
                </div>
                <div class="allocation-slider">
                    <input type="range" min="0" max="100" value="${type.recommended}" 
                           data-type="${type.key}" disabled>
                    <div class="allocation-percentage">${actualPercent}% of remaining income</div>
                </div>
            `;
            
            container.appendChild(item);
        });
        
        console.log('[BUDGET_ANALYTICS] Allocations updated');
    }
    
    async loadRecommendations() {
        const recommendationEl = document.getElementById('recommendation-text');
        if (!recommendationEl) return;
        
        try {
            const monthsParam = this.selectedMonths[0] || this.currentData.period?.month || this.currentData.currentMonth;
            const url = `${this.apiBaseUrl}/api/recommendations?year=${this.currentYear}&month=${monthsParam}`;
            
            const response = await fetch(url);
            const result = await response.json();
            
            if (result.success && result.recommendations) {
                const recommendations = result.recommendations;
                
                if (recommendations.length > 0) {
                    recommendationEl.innerHTML = recommendations
                        .map(rec => `<p>${this.escapeHtml(rec)}</p>`)
                        .join('');
                } else {
                    recommendationEl.textContent = "You're on track! Keep up the good work.";
                }
            }
            
        } catch (error) {
            console.error('[BUDGET_ANALYTICS] Error loading recommendations:', error);
            recommendationEl.textContent = 'Unable to load recommendations at this time.';
        }
    }
    
    // Utility methods
    
    formatCurrency(amount) {
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
    
    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
    
    generateColors(count) {
        // Generate a nice color palette
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
    
    showLoading(show) {
        const indicator = document.getElementById('loading-indicator');
        if (indicator) {
            indicator.style.display = show ? 'flex' : 'none';
        }
    }
    
    showError(message) {
        const container = document.getElementById('error-container');
        const messageEl = container?.querySelector('.error-message');
        
        if (container && messageEl) {
            messageEl.textContent = message;
            container.style.display = 'block';
            
            // Auto-hide after 5 seconds
            setTimeout(() => {
                container.style.display = 'none';
            }, 5000);
        } else {
            console.error('[BUDGET_ANALYTICS] Error:', message);
            alert(message);
        }
    }
}

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    console.log('[BUDGET_ANALYTICS] DOM ready, initializing...');
    window.budgetAnalytics = new BudgetAnalytics();
});