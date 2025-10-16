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
        this.budgetPreferences = { needs_percent: 50, wants_percent: 30, savings_percent: 20 };
        
        this.init();
    }
    
    async init() {
        console.log('[BUDGET_ANALYTICS] Initializing...');
        
        // Initialize filters
        const filtersReady = await this.filterManager.initialize(this.currentYear, this.currentMonth);
        
        if (filtersReady) {
            // Load budget preferences
            await this.loadBudgetPreferences();
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

    async loadBudgetPreferences() {
        try {
            const response = await fetch(`${this.apiBaseUrl}/api/budget-preferences`);
            const result = await response.json();
            
            if (result.success && result.preferences) {
                this.budgetPreferences = result.preferences;
                this.updateBudgetRuleDisplay();
                console.log('[BUDGET_ANALYTICS] Loaded preferences:', this.budgetPreferences);
            }
        } catch (error) {
            console.error('[BUDGET_ANALYTICS] Error loading preferences:', error);
            // Use defaults if loading fails
        }
    }
    
    updateBudgetRuleDisplay() {
        const displayEl = document.getElementById('budget-rule-display');
        if (displayEl) {
            const { needs_percent, wants_percent, savings_percent } = this.budgetPreferences;
            displayEl.textContent = `${Math.round(needs_percent)}/${Math.round(wants_percent)}/${Math.round(savings_percent)}`;
        }
    }
    
    async saveBudgetPreferences(needs, wants, savings) {
        try {
            const response = await fetch(`${this.apiBaseUrl}/api/budget-preferences`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    needs_percent: needs,
                    wants_percent: wants,
                    savings_percent: savings
                })
            });
            
            const result = await response.json();
            
            if (result.success) {
                this.budgetPreferences = result.preferences;
                this.updateBudgetRuleDisplay();
                this.update503020Breakdown(); // Refresh the breakdown
                return { success: true, message: result.message };
            } else {
                return { success: false, error: result.error };
            }
        } catch (error) {
            console.error('[BUDGET_ANALYTICS] Error saving preferences:', error);
            return { success: false, error: error.message };
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
        
        // Recommended values (using custom preferences)
        const recommendedNeedsPercent = this.budgetPreferences.needs_percent;
        const recommendedWantsPercent = this.budgetPreferences.wants_percent;
        const recommendedSavingsPercent = this.budgetPreferences.savings_percent;
        
        const recommendedNeeds = totalIncome * (recommendedNeedsPercent / 100);
        const recommendedWants = totalIncome * (recommendedWantsPercent / 100);
        const recommendedSavings = totalIncome * (recommendedSavingsPercent / 100);
        
        // Build the breakdown
        const categories = [
            {
                name: 'Needs (Essential)',
                actual: needsAmount,
                percent: needsPercent,
                recommended: recommendedNeedsPercent,
                recommendedAmount: recommendedNeeds,
                className: 'needs',
                tolerance: 5 // ±5% is acceptable
            },
            {
                name: 'Wants (Personal)',
                actual: wantsAmount,
                percent: wantsPercent,
                recommended: recommendedWantsPercent,
                recommendedAmount: recommendedWants,
                className: 'wants',
                tolerance: 5
            },
            {
                name: 'Savings (What You Kept)',
                actual: savingsAmount,
                percent: savingsPercent,
                recommended: recommendedSavingsPercent,
                recommendedAmount: recommendedSavings,
                className: 'savings',
                tolerance: 5
            }
        ];
        
        // Update the description text with custom percentages
        const descriptionEl = document.querySelector('.breakdown-description');
        if (descriptionEl) {
            const needsPct = Math.round(recommendedNeedsPercent);
            const wantsPct = Math.round(recommendedWantsPercent);
            const savingsPct = Math.round(recommendedSavingsPercent);
            descriptionEl.textContent = `The ${needsPct}/${wantsPct}/${savingsPct} rule suggests spending ${needsPct}% on needs, ${wantsPct}% on wants, and saving ${savingsPct}% of your income.`;
        }
        
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
                    statusClass = diff < 0 ? 'status-warning' : 'status-success';
                } else {
                    status = diff > 0 ? '⚠️ Slightly above target' : '✅ Below target - you have room!';
                    statusClass = 'status-warning';
                }
            } else {
                if (cat.name.includes('Savings')) {
                    status = diff < 0 ? '❌ Well below target' : '✅ Excellent savings rate!';
                    statusClass = diff < 0 ? 'status-danger' : 'status-success';
                } else {
                    status = diff > 0 ? '❌ Well above target - try to reduce' : '✅ Well below target';
                    statusClass = diff > 0 ? 'status-danger' : 'status-success';
                }
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

    // Budget preferences modal handlers
    const editBudgetBtn = document.getElementById('edit-budget-btn');
    const modal = document.getElementById('budget-pref-modal');
    const closeModalBtn = document.getElementById('close-pref-modal');
    const cancelModalBtn = document.getElementById('cancel-pref-modal');
    const saveBtn = document.getElementById('save-preferences');
    const resetBtn = document.getElementById('reset-to-default');
    
    const needsInput = document.getElementById('needs-input');
    const wantsInput = document.getElementById('wants-input');
    const savingsInput = document.getElementById('savings-input');
    const totalDisplay = document.getElementById('pref-total');
    const statusDisplay = document.getElementById('pref-status');
    const errorDiv = document.getElementById('pref-error');
    
    function updateTotal() {
        const needs = parseFloat(needsInput.value) || 0;
        const wants = parseFloat(wantsInput.value) || 0;
        const savings = parseFloat(savingsInput.value) || 0;
        const total = needs + wants + savings;
        
        totalDisplay.textContent = `${total.toFixed(1)}%`;
        
        if (Math.abs(total - 100) < 0.01) {
            totalDisplay.style.color = '#48bb78';
            statusDisplay.textContent = '✓';
            statusDisplay.style.color = '#48bb78';
            errorDiv.style.display = 'none';
        } else {
            totalDisplay.style.color = '#f56565';
            statusDisplay.textContent = '✗';
            statusDisplay.style.color = '#f56565';
            errorDiv.textContent = `Total must equal 100% (currently ${total.toFixed(1)}%)`;
            errorDiv.style.display = 'block';
        }
    }
    
    function openModal() {
        const analytics = window.budgetAnalytics;
        needsInput.value = analytics.budgetPreferences.needs_percent;
        wantsInput.value = analytics.budgetPreferences.wants_percent;
        savingsInput.value = analytics.budgetPreferences.savings_percent;
        updateTotal();
        modal.style.display = 'flex';
    }
    
    function closeModal() {
        modal.style.display = 'none';
        errorDiv.style.display = 'none';
    }
    
    if (editBudgetBtn) {
        editBudgetBtn.addEventListener('click', openModal);
    }
    
    if (closeModalBtn) {
        closeModalBtn.addEventListener('click', closeModal);
    }
    
    if (cancelModalBtn) {
        cancelModalBtn.addEventListener('click', closeModal);
    }
    
    if (needsInput) needsInput.addEventListener('input', updateTotal);
    if (wantsInput) wantsInput.addEventListener('input', updateTotal);
    if (savingsInput) savingsInput.addEventListener('input', updateTotal);
    
    if (resetBtn) {
        resetBtn.addEventListener('click', () => {
            needsInput.value = 50;
            wantsInput.value = 30;
            savingsInput.value = 20;
            updateTotal();
        });
    }
    
    if (saveBtn) {
        saveBtn.addEventListener('click', async () => {
            const needs = parseFloat(needsInput.value);
            const wants = parseFloat(wantsInput.value);
            const savings = parseFloat(savingsInput.value);
            const total = needs + wants + savings;
            
            if (Math.abs(total - 100) > 0.01) {
                errorDiv.textContent = 'Percentages must add up to 100%';
                errorDiv.style.display = 'block';
                return;
            }
            
            saveBtn.disabled = true;
            saveBtn.textContent = 'Saving...';
            
            const result = await window.budgetAnalytics.saveBudgetPreferences(needs, wants, savings);
            
            if (result.success) {
                closeModal();
                BudgetUIHelpers.showError('Budget preferences saved successfully!'); // Using error container for success message
            } else {
                errorDiv.textContent = result.error || 'Failed to save preferences';
                errorDiv.style.display = 'block';
            }
            
            saveBtn.disabled = false;
            saveBtn.textContent = 'Save Changes';
        });
    }
    
    // Close modal when clicking outside
    modal.addEventListener('click', (e) => {
        if (e.target === modal) {
            closeModal();
        }
    });
});