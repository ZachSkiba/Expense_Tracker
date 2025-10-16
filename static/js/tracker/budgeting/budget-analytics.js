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
            
            console.log('[BUDGET_ANALYTICS] ===== LOADING DATA =====');
            console.log('[BUDGET_ANALYTICS] Years:', years, 'Months:', months);
            
            const result = await this.dataService.fetchSummary(years, months);
            
            if (result.success) {
                this.currentData = result.data;
                console.log('[BUDGET_ANALYTICS] ===== DATA LOADED =====');
                console.log('[BUDGET_ANALYTICS] Income total:', this.currentData.income.total);
                console.log('[BUDGET_ANALYTICS] Expenses total:', this.currentData.expenses.total);
                console.log('[BUDGET_ANALYTICS] Expenses by_budget_type:', JSON.stringify(this.currentData.expenses.by_budget_type, null, 2));
                console.log('[BUDGET_ANALYTICS] =========================');
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
    }
    
    update503020Breakdown() {
        const container = document.getElementById('breakdown-503020-list');
        if (!container) return;
        
        const { income, expenses } = this.currentData;
        const totalIncome = income.total || 0;
        
        console.log('[BUDGET_ANALYTICS] ===== 50/30/20 BREAKDOWN =====');
        console.log('[BUDGET_ANALYTICS] Total Income:', totalIncome);
        console.log('[BUDGET_ANALYTICS] Total Expenses:', expenses.total);
        console.log('[BUDGET_ANALYTICS] by_budget_type:', JSON.stringify(expenses.by_budget_type, null, 2));
        
        // Handle no income case
        if (totalIncome === 0) {
            container.innerHTML = '<div class="no-income-message">Add income entries to see your 50/30/20 breakdown</div>';
            console.log('[BUDGET_ANALYTICS] No income - skipping breakdown');
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
            
            // Get detail items for this category
            const detailItems = this.get503020DetailItems(cat.className);
            
            item.innerHTML = `
                <div class="breakdown-header">
                    <div class="breakdown-name">
                        <span class="breakdown-toggle">▼</span>
                        ${cat.name}
                    </div>
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
                <div class="breakdown-details">
                    ${detailItems}
                </div>
            `;
            
            // Add click handler for toggle
            const header = item.querySelector('.breakdown-header');
            const details = item.querySelector('.breakdown-details');
            const toggle = item.querySelector('.breakdown-toggle');
            
            header.addEventListener('click', () => {
                details.classList.toggle('show');
                toggle.classList.toggle('expanded');
            });
            
            container.appendChild(item);
        });
        
        console.log('[BUDGET_ANALYTICS] 50/30/20 breakdown updated');
    }

get503020DetailItems(categoryType) {
        if (!this.currentData) return '<div class="breakdown-no-data">No data available</div>';
        
        const { expenses, income, allocations } = this.currentData;
        const expensesByType = expenses.by_budget_type || {};
        const categoryDetails = expenses.category_details || {};
        const allocationDetails = allocations.allocation_details || {};
        
        let html = '';
        
        if (categoryType === 'needs') {
            // Show essential, debt, and emergency expenses
            html += '<h4>Essential Expenses:</h4>';
            html += '<div class="breakdown-detail-list">';
            
            let hasItems = false;
            
            // Collect all items from essential categories
            for (const [catName, catData] of Object.entries(categoryDetails)) {
                const items = catData.items || [];
                const essentialItems = items.filter(item => 
                    item.budget_type === 'essential' || 
                    item.budget_type === 'debt' || 
                    item.budget_type === 'emergency'
                );
                
                essentialItems.forEach(item => {
                    hasItems = true;
                    // Format: Category (Description) or just Category if no description
                    const label = item.description ? 
                        `${catName} (${BudgetUIHelpers.escapeHtml(item.description)})` : 
                        catName;
                    
                    html += `
                        <div class="breakdown-detail-item">
                            <span class="breakdown-detail-desc">${label}</span>
                            <span class="breakdown-detail-date">${item.date}</span>
                            <span class="breakdown-detail-amount">${BudgetUIHelpers.formatCurrency(item.amount)}</span>
                        </div>
                    `;
                });
            }
            
            if (!hasItems) {
                html += '<div class="breakdown-no-data">No essential expenses in this period</div>';
            }
            
            html += '</div>';
            
        } else if (categoryType === 'wants') {
            // Show personal/discretionary expenses
            html += '<h4>Discretionary Expenses:</h4>';
            html += '<div class="breakdown-detail-list">';
            
            let hasItems = false;
            
            for (const [catName, catData] of Object.entries(categoryDetails)) {
                const items = catData.items || [];
                const personalItems = items.filter(item => item.budget_type === 'personal');
                
                personalItems.forEach(item => {
                    hasItems = true;
                    // Format: Category (Description) or just Category if no description
                    const label = item.description ? 
                        `${catName} (${BudgetUIHelpers.escapeHtml(item.description)})` : 
                        catName;
                    
                    html += `
                        <div class="breakdown-detail-item">
                            <span class="breakdown-detail-desc">${label}</span>
                            <span class="breakdown-detail-date">${item.date}</span>
                            <span class="breakdown-detail-amount">${BudgetUIHelpers.formatCurrency(item.amount)}</span>
                        </div>
                    `;
                });
            }
            
            if (!hasItems) {
                html += '<div class="breakdown-no-data">No discretionary expenses in this period</div>';
            }
            
            html += '</div>';
            
        } else if (categoryType === 'savings') {
            // Show calculation breakdown
            const totalIncome = income.total || 0;
            const totalExpenses = expenses.total || 0;
            const needsAmount = (expensesByType.essential || 0) + 
                                (expensesByType.debt || 0) + 
                                (expensesByType.emergency || 0);
            const wantsAmount = expensesByType.personal || 0;
            const savingsAmount = totalIncome - needsAmount - wantsAmount;
            
            html += '<h4>Savings Calculation:</h4>';
            html += '<div class="breakdown-detail-list">';
            
            html += `
                <div class="breakdown-detail-item" style="background: #e6fffa; border-left: 3px solid #48bb78;">
                    <span class="breakdown-detail-desc">💰 Total Income</span>
                    <span class="breakdown-detail-amount" style="color: #48bb78;">${BudgetUIHelpers.formatCurrency(totalIncome)}</span>
                </div>
                <div class="breakdown-detail-item" style="background: #fff5f5; border-left: 3px solid #f56565;">
                    <span class="breakdown-detail-desc">➖ Needs (Essential Expenses)</span>
                    <span class="breakdown-detail-amount" style="color: #f56565;">${BudgetUIHelpers.formatCurrency(needsAmount)}</span>
                </div>
                <div class="breakdown-detail-item" style="background: #faf5ff; border-left: 3px solid #9f7aea;">
                    <span class="breakdown-detail-desc">➖ Wants (Discretionary)</span>
                    <span class="breakdown-detail-amount" style="color: #9f7aea;">${BudgetUIHelpers.formatCurrency(wantsAmount)}</span>
                </div>
                <div class="breakdown-detail-item" style="background: #ebf8ff; border-left: 3px solid #4299e1; font-weight: 600;">
                    <span class="breakdown-detail-desc">💵 = Net Savings (What You Kept)</span>
                    <span class="breakdown-detail-amount" style="color: #4299e1; font-size: 1.1rem;">${BudgetUIHelpers.formatCurrency(savingsAmount)}</span>
                </div>
            `;
            
            html += '</div>';
            
            // Show income details - use by_category since entries may not be available when combining months
            html += '<h4 style="margin-top: 16px;">Income Sources:</h4>';
            html += '<div class="breakdown-detail-list">';
            
            const incomeByCategory = income.by_category || {};
            const incomeEntries = income.entries || [];
            
            if (incomeEntries.length > 0) {
                // If we have detailed entries, show them
                incomeEntries.forEach(entry => {
                    html += `
                        <div class="breakdown-detail-item">
                            <span class="breakdown-detail-desc">${BudgetUIHelpers.escapeHtml(entry.category)}${entry.description ? ' (' + BudgetUIHelpers.escapeHtml(entry.description) + ')' : ''}</span>
                            <span class="breakdown-detail-date">${entry.date}</span>
                            <span class="breakdown-detail-amount">${BudgetUIHelpers.formatCurrency(entry.amount)}</span>
                        </div>
                    `;
                });
            } else if (Object.keys(incomeByCategory).length > 0) {
                // If combining months, show category totals
                Object.entries(incomeByCategory).forEach(([category, amount]) => {
                    html += `
                        <div class="breakdown-detail-item">
                            <span class="breakdown-detail-desc">${BudgetUIHelpers.escapeHtml(category)}</span>
                            <span class="breakdown-detail-amount">${BudgetUIHelpers.formatCurrency(amount)}</span>
                        </div>
                    `;
                });
            } else {
                html += '<div class="breakdown-no-data">No income in this period</div>';
            }
            
            html += '</div>';
            
            // Show where savings were allocated (if any)
            const savingsAllocations = Object.entries(allocationDetails).filter(([catName, catData]) => {
                const items = catData.items || [];
                return items.some(item => item.bucket === 'investments' || item.bucket === 'savings');
            });
            
            if (savingsAllocations.length > 0) {
                html += '<h4 style="margin-top: 16px;">Savings & Investments Allocated:</h4>';
                html += '<div class="breakdown-detail-list">';
                
                savingsAllocations.forEach(([catName, catData]) => {
                    const items = catData.items || [];
                    items.forEach(item => {
                        if (item.bucket === 'investments' || item.bucket === 'savings') {
                            html += `
                                <div class="breakdown-detail-item">
                                    <span class="breakdown-detail-desc">${BudgetUIHelpers.escapeHtml(item.notes || catName)}</span>
                                    <span class="breakdown-detail-date">${item.income_entry_date || ''}</span>
                                    <span class="breakdown-detail-amount">${BudgetUIHelpers.formatCurrency(item.amount)}</span>
                                </div>
                            `;
                        }
                    });
                });
                
                html += '</div>';
            }
        }
        
        return html;
    }
}

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    console.log('[BUDGET_ANALYTICS] DOM ready, initializing...');
    window.budgetAnalytics = new BudgetAnalytics();
});