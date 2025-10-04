/**
 * Budget Analytics - Main JavaScript Controller
 * Coordinates all budget analytics functionality
 */

class BudgetAnalytics {
    constructor() {
        this.groupId = window.budgetData.groupId;
        this.userId = window.budgetData.userId;
        this.currentYear = parseInt(window.budgetData.currentYear);
        this.currentMonth = parseInt(window.budgetData.currentMonth);
        this.apiBaseUrl = window.budgetData.apiBaseUrl;
        
        // Initialize services
        this.dataService = new BudgetDataService(this.apiBaseUrl, this.groupId, this.userId);
        this.chartManager = new BudgetChartManager();
        this.filterManager = new BudgetFilterManager(
            this.dataService,
            () => this.onFilterChange()
        );
        
        this.currentData = null;
        
        this.init();
    }
    
    async init() {
        console.log('[BUDGET_ANALYTICS] Initializing...');
        
        // Initialize filters
        const filtersReady = await this.filterManager.initialize(this.currentYear, this.currentMonth);
        
        if (filtersReady) {
            // Load initial data
            await this.loadData();
        } else {
            BudgetUIHelpers.showError('Failed to load filter options');
        }
        
        // Bind error close button
        const errorClose = document.querySelector('.error-close');
        if (errorClose) {
            errorClose.addEventListener('click', () => {
                document.getElementById('error-container').style.display = 'none';
            });
        }
    }
    
    async onFilterChange() {
        // Called whenever filters change
        await this.loadData();
    }
    
    async loadData() {
        BudgetUIHelpers.showLoading(true);
        
        // Clear detailed breakdown when loading new data
        this.chartManager.clearDetailedBreakdown();
        
        try {
            const years = this.filterManager.getSelectedYears();
            const months = this.filterManager.getSelectedMonths();
            
            if (years.length === 0 || months.length === 0) {
                console.warn('[BUDGET_ANALYTICS] No years or months selected');
                BudgetUIHelpers.showLoading(false);
                return;
            }
            
            console.log('[BUDGET_ANALYTICS] Loading data for years:', years, 'months:', months);
            
            const result = await this.dataService.fetchSummary(years, months);
            
            if (result.success) {
                this.currentData = result.data;
                console.log('[BUDGET_ANALYTICS] Data loaded:', this.currentData);
                this.updateUI();
            } else {
                throw new Error(result.error || 'Failed to load data');
            }
            
        } catch (error) {
            console.error('[BUDGET_ANALYTICS] Error loading data:', error);
            BudgetUIHelpers.showError('Failed to load budget data: ' + error.message);
        } finally {
            BudgetUIHelpers.showLoading(false);
        }
    }
    
    updateUI() {
        if (!this.currentData) {
            console.warn('[BUDGET_ANALYTICS] No data to display');
            return;
        }
        
        this.updateKPIs();
        this.chartManager.setCurrentData(this.currentData);
        this.chartManager.updateAllCharts();
        this.update503020Breakdown();
        this.loadRecommendations();
    }
    
    updateKPIs() {
        const { income, expenses, net_summary } = this.currentData;
        
        // Total Income
        const incomeEl = document.getElementById('kpi-income');
        if (incomeEl) {
            incomeEl.textContent = BudgetUIHelpers.formatCurrency(income.total);
        }
        
        // Total Spending
        const spendingEl = document.getElementById('kpi-spending');
        if (spendingEl) {
            spendingEl.textContent = BudgetUIHelpers.formatCurrency(expenses.total);
        }
        
        // Net Savings (Income - Expenses)
        const savingsEl = document.getElementById('kpi-savings');
        if (savingsEl) {
            const netSavings = income.total - expenses.total;
            savingsEl.textContent = BudgetUIHelpers.formatCurrency(netSavings);
        }
        
        // Update savings change indicator
        const savingsChangeEl = document.getElementById('kpi-savings-change');
        if (savingsChangeEl && net_summary) {
            const netSavings = income.total - expenses.total;
            if (netSavings > 0) {
                savingsChangeEl.textContent = `↑ ${BudgetUIHelpers.formatCurrency(netSavings)} saved`;
                savingsChangeEl.className = 'kpi-change positive';
            } else if (netSavings < 0) {
                savingsChangeEl.textContent = `↓ ${BudgetUIHelpers.formatCurrency(Math.abs(netSavings))} overspent`;
                savingsChangeEl.className = 'kpi-change negative';
            } else {
                savingsChangeEl.textContent = 'Break even';
                savingsChangeEl.className = 'kpi-change';
            }
        }
        
        // Total spending in bottom card
        const totalSpendingEl = document.getElementById('total-spending');
        if (totalSpendingEl) {
            totalSpendingEl.textContent = BudgetUIHelpers.formatCurrency(expenses.total);
        }
        
        console.log('[BUDGET_ANALYTICS] KPIs updated');
    }
    
    update503020Breakdown() {
        const container = document.getElementById('breakdown-503020-list');
        if (!container) return;
        
        const { income, expenses } = this.currentData;
        const totalIncome = income.total;
        
        // Handle no income case
        if (totalIncome === 0) {
            container.innerHTML = '<div class="no-income-message">Add income entries to see your 50/30/20 breakdown</div>';
            return;
        }
        
        // Calculate expenses by type
        const expensesByType = expenses.by_budget_type || {};
        
        // Needs = essential + debt + emergency
        const needsAmount = (expensesByType.essential || 0) + 
                            (expensesByType.debt || 0) + 
                            (expensesByType.emergency || 0);
        
        // Wants = personal
        const wantsAmount = expensesByType.personal || 0;
        
        // Savings = Income - Needs - Wants (includes investment expenses automatically)
        const savingsAmount = totalIncome - needsAmount - wantsAmount;
        
        // Calculate percentages
        const needsPercent = (needsAmount / totalIncome * 100);
        const wantsPercent = (wantsAmount / totalIncome * 100);
        const savingsPercent = (savingsAmount / totalIncome * 100);
        
        // Recommended values
        const recommendedNeeds = totalIncome * 0.50;
        const recommendedWants = totalIncome * 0.30;
        const recommendedSavings = totalIncome * 0.20;
        
        // Build the breakdown
        const categories = [
            {
                name: 'Needs (Essential)',
                actual: needsAmount,
                percent: needsPercent,
                recommended: 50,
                recommendedAmount: recommendedNeeds,
                className: 'needs',
                tolerance: 5 // ±5% is acceptable
            },
            {
                name: 'Wants (Personal)',
                actual: wantsAmount,
                percent: wantsPercent,
                recommended: 30,
                recommendedAmount: recommendedWants,
                className: 'wants',
                tolerance: 5
            },
            {
                name: 'Savings (What You Kept)',
                actual: savingsAmount,
                percent: savingsPercent,
                recommended: 20,
                recommendedAmount: recommendedSavings,
                className: 'savings',
                tolerance: 5
            }
        ];
        
        container.innerHTML = '';
        
        categories.forEach(cat => {
            const item = document.createElement('div');
            item.className = `breakdown-item ${cat.className}`;
            
            // Determine status
            let status = '';
            let statusClass = '';
            const diff = cat.percent - cat.recommended;
            
            if (cat.name.includes('Savings') && cat.actual < 0) {
                // Negative savings = overspending
                status = '❌ Overspending - you\'re going into debt';
                statusClass = 'status-danger';
            } else if (Math.abs(diff) <= cat.tolerance) {
                status = '✅ Right on target!';
                statusClass = 'status-success';
            } else if (Math.abs(diff) <= cat.tolerance * 2) {
                if (cat.name.includes('Savings')) {
                    status = diff < 0 ? '⚠️ Below target - try to save more' : '✅ Above target - great job!';
                } else {
                    status = diff > 0 ? '⚠️ Slightly above target' : '✅ Below target - you have room!';
                }
                statusClass = 'status-warning';
            } else {
                if (cat.name.includes('Savings')) {
                    status = diff < 0 ? '❌ Well below target' : '✅ Excellent savings rate!';
                } else {
                    status = diff > 0 ? '❌ Well above target - try to reduce' : '✅ Well below target';
                }
                statusClass = diff > 0 && !cat.name.includes('Savings') ? 'status-danger' : 'status-success';
            }
            
            // Calculate bar width (cap at 100%)
            const barWidth = Math.min(cat.percent, 100);
            
            item.innerHTML = `
                <div class="breakdown-header">
                    <div class="breakdown-name">${cat.name}</div>
                    <div class="breakdown-values">
                        <span class="breakdown-percent">${cat.percent.toFixed(1)}%</span>
                        <span class="breakdown-amount">${BudgetUIHelpers.formatCurrency(cat.actual)}</span>
                    </div>
                </div>
                <div class="breakdown-bar-container">
                    <div class="breakdown-bar" style="width: ${barWidth}%"></div>
                </div>
                <div class="breakdown-footer">
                    <div class="breakdown-recommended">
                        Recommended: ${cat.recommended}% | ${BudgetUIHelpers.formatCurrency(cat.recommendedAmount)}
                    </div>
                    <div class="breakdown-status ${statusClass}">${status}</div>
                </div>
            `;
            
            container.appendChild(item);
        });
        
        console.log('[BUDGET_ANALYTICS] 50/30/20 breakdown updated');
    }
    
    async loadRecommendations() {
        const recommendationEl = document.getElementById('recommendation-text');
        if (!recommendationEl) return;
        
        try {
            // Generate 50/30/20-specific recommendations
            const customRecommendations = this.generate503020Recommendations();
            
            // Fetch backend recommendations
            const years = this.filterManager.getSelectedYears();
            const months = this.filterManager.getSelectedMonths();
            
            const year = years[0] || this.currentYear;
            const month = months[0] || this.currentMonth;
            
            const result = await this.dataService.fetchRecommendations(year, month);
            
            let allRecommendations = [...customRecommendations];
            
            if (result.success && result.recommendations) {
                allRecommendations = allRecommendations.concat(result.recommendations);
            }
            
            if (allRecommendations.length > 0) {
                recommendationEl.innerHTML = allRecommendations
                    .map(rec => `<p>${BudgetUIHelpers.escapeHtml(rec)}</p>`)
                    .join('');
            } else {
                recommendationEl.innerHTML = '<p>✅ You\'re on track! Keep up the good work.</p>';
            }
            
        } catch (error) {
            console.error('[BUDGET_ANALYTICS] Error loading recommendations:', error);
            recommendationEl.textContent = 'Unable to load recommendations at this time.';
        }
    }

    generate503020Recommendations() {
        if (!this.currentData) return [];
        
        const { income, expenses } = this.currentData;
        const totalIncome = income.total;
        
        if (totalIncome === 0) {
            return ['💡 Add income entries to get personalized spending recommendations.'];
        }
        
        const recommendations = [];
        
        // Calculate expenses by type
        const expensesByType = expenses.by_budget_type || {};
        
        const needsAmount = (expensesByType.essential || 0) + 
                            (expensesByType.debt || 0) + 
                            (expensesByType.emergency || 0);
        
        const wantsAmount = expensesByType.personal || 0;
        const savingsAmount = totalIncome - needsAmount - wantsAmount;
        
        const needsPercent = (needsAmount / totalIncome * 100);
        const wantsPercent = (wantsAmount / totalIncome * 100);
        const savingsPercent = (savingsAmount / totalIncome * 100);
        
        // Needs recommendations
        if (needsPercent > 55) {
            const excess = needsAmount - (totalIncome * 0.50);
            recommendations.push(
                `💰 Your essential expenses (${needsPercent.toFixed(1)}%) are above the recommended 50%. ` +
                `Try to reduce by ${BudgetUIHelpers.formatCurrency(excess)} by reviewing subscriptions, ` +
                `utilities, or finding more affordable alternatives.`
            );
        } else if (needsPercent < 45) {
            recommendations.push(
                `✅ Great job! Your essential expenses are only ${needsPercent.toFixed(1)}% of your income, ` +
                `which is below the 50% target. You have room for additional savings or discretionary spending.`
            );
        }
        
        // Wants recommendations
        if (wantsPercent > 35) {
            const excess = wantsAmount - (totalIncome * 0.30);
            recommendations.push(
                `🎭 Your discretionary spending (${wantsPercent.toFixed(1)}%) exceeds the recommended 30%. ` +
                `Consider reducing by ${BudgetUIHelpers.formatCurrency(excess)} in areas like dining out, ` +
                `entertainment, or shopping.`
            );
        } else if (wantsPercent < 20) {
            recommendations.push(
                `🎉 You're spending only ${wantsPercent.toFixed(1)}% on wants. ` +
                `You have room to enjoy yourself more while staying within budget!`
            );
        }
        
        // Savings recommendations
        if (savingsAmount < 0) {
            recommendations.push(
                `⚠️ You're spending more than you earn! You need to reduce expenses by ` +
                `${BudgetUIHelpers.formatCurrency(Math.abs(savingsAmount))} to break even, ` +
                `or increase your income.`
            );
        } else if (savingsPercent < 15) {
            const shortfall = (totalIncome * 0.20) - savingsAmount;
            recommendations.push(
                `📈 Your savings rate (${savingsPercent.toFixed(1)}%) is below the recommended 20%. ` +
                `Try to save an additional ${BudgetUIHelpers.formatCurrency(shortfall)} per month ` +
                `to reach your target.`
            );
        } else if (savingsPercent >= 20) {
            recommendations.push(
                `🌟 Excellent! You're saving ${savingsPercent.toFixed(1)}% of your income, ` +
                `which meets or exceeds the 20% target. Keep it up!`
            );
        }
        
        // Overall health check
        const totalPercent = needsPercent + wantsPercent;
        if (totalPercent > 95 && savingsPercent > 0) {
            recommendations.push(
                `⚖️ You're using ${totalPercent.toFixed(1)}% of your income for expenses. ` +
                `While you're still saving, consider creating more cushion in your budget.`
            );
        }
        
        return recommendations;
    }
}

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    console.log('[BUDGET_ANALYTICS] DOM ready, initializing...');
    window.budgetAnalytics = new BudgetAnalytics();
});