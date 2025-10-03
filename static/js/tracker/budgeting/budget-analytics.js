/**
 * Budget Analytics - Main JavaScript Controller
 * Handles data loading, UI updates, and chart rendering
 */

class BudgetAnalytics {
    constructor() {
        this.groupId = window.budgetData.groupId;
        this.userId = window.budgetData.userId;
        this.currentYear = parseInt(window.budgetData.currentYear);
        
        // Parse selected months - handle both JSON string and array
        try {
            const parsedMonths = JSON.parse(window.budgetData.selectedMonths || '[]');
            this.selectedMonths = Array.isArray(parsedMonths) ? parsedMonths : [];
        } catch (e) {
            this.selectedMonths = [];
        }
        
        this.selectedYears = [parseInt(window.budgetData.selectedYear || window.budgetData.currentYear)];
        this.apiBaseUrl = window.budgetData.apiBaseUrl;
        
        this.currentData = null;
        this.selectedCategory = null;
        this.expensePieChart = null;
        this.allocationPieChart = null;
        this.drillDownChart = null;
        this.availableMonths = [];
        this.availableYears = [];
        
        this.init();
    }
    
    
    init() {
        console.log('[BUDGET_ANALYTICS] Initializing...');
        this.loadAvailableData();
        this.bindEvents();
    }
    
    async loadAvailableData() {
        // Load available months and years for filters
        try {
            const url = `${this.apiBaseUrl}/api/available-periods`;
            const response = await fetch(url);
            const result = await response.json();
            
            if (result.success) {
                this.availableMonths = result.data.months || [];
                this.availableYears = result.data.years || [];
                this.populateFilters();
                this.loadData();
            }
        } catch (error) {
            console.error('[BUDGET_ANALYTICS] Error loading available data:', error);
            // Continue with defaults
            this.loadData();
        }
    

    document.addEventListener('change', (e) => {
                if (e.target.matches('[data-filter="years"]')) {
                    this.handleYearFilterChange(e.target);
                } else if (e.target.matches('[data-filter="months"]')) {
                    this.handleMonthFilterChange(e.target);
                }
            });
        }

    // After filters are populated, attach checkbox event listeners
   
    
    populateFilters() {
        // Populate year multi-select dropdown
        const yearsDropdown = document.getElementById('years-dropdown');
        if (yearsDropdown && this.availableYears.length > 0) {
            yearsDropdown.innerHTML = '';
            this.availableYears.forEach(year => {
                const label = document.createElement('label');
                label.className = 'checkbox-item';
                label.innerHTML = `
                    <input type="checkbox" value="${year}" data-filter="years" ${this.selectedYears.includes(year) ? 'checked' : ''}>
                    <span>${year}</span>
                `;
                yearsDropdown.appendChild(label);
            });
            
            // Update display text
            this.updateMultiSelectDisplay('years');
        }
        
        // Populate months if years are selected
        if (this.selectedYears.length > 0) {
            this.updateAvailableMonths();
        }
    }

    bindEvents() {
        // Multi-select dropdown toggle
        document.querySelectorAll('.multi-select-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                e.stopPropagation();
                if (!btn.disabled) {
                    this.toggleMultiSelectDropdown(btn);
                }
            });
        });
    
        
        // Clear filters button
        const clearBtn = document.getElementById('clear-filters-btn');
        if (clearBtn) {
            clearBtn.addEventListener('click', () => {
                this.clearAllFilters();
            });
        }
        
        // Close dropdowns when clicking outside
        document.addEventListener('click', (e) => {
            if (!e.target.closest('.multi-select-container')) {
                this.closeAllDropdowns();
            }
        });
        
        // Close dropdowns on scroll
        window.addEventListener('scroll', () => {
            this.closeAllDropdowns();
        }, true);
        
        // Error close button
        const errorClose = document.querySelector('.error-close');
        if (errorClose) {
            errorClose.addEventListener('click', () => {
                document.getElementById('error-container').style.display = 'none';
            });
        }
    }

    toggleMultiSelectDropdown(btn) {
        const dropdown = btn.nextElementSibling;
        const isOpen = dropdown.style.display === 'block';
        
        this.closeAllDropdowns();
        
        if (!isOpen) {
            dropdown.style.display = 'block';
            
            // Position the dropdown
            const btnRect = btn.getBoundingClientRect();
            const viewportHeight = window.innerHeight;
            const dropdownMaxHeight = 300;
            
            dropdown.style.left = `${btnRect.left}px`;
            dropdown.style.width = `${Math.max(btnRect.width, 200)}px`;
            
            const spaceBelow = viewportHeight - btnRect.bottom;
            const spaceAbove = btnRect.top;
            
            if (spaceBelow < dropdownMaxHeight && spaceAbove > spaceBelow) {
                dropdown.style.bottom = `${viewportHeight - btnRect.top}px`;
                dropdown.style.top = 'auto';
                dropdown.style.maxHeight = `${Math.min(spaceAbove - 10, dropdownMaxHeight)}px`;
            } else {
                dropdown.style.top = `${btnRect.bottom + 2}px`;
                dropdown.style.bottom = 'auto';
                dropdown.style.maxHeight = `${Math.min(spaceBelow - 10, dropdownMaxHeight)}px`;
            }
        }
    }

    closeAllDropdowns() {
        document.querySelectorAll('.multi-select-dropdown').forEach(dropdown => {
            dropdown.style.display = 'none';
        });
    }

    handleYearFilterChange(checkbox) {
        const year = parseInt(checkbox.value);
        
        if (checkbox.checked) {
            if (!this.selectedYears.includes(year)) {
                this.selectedYears.push(year);
            }
        } else {
            this.selectedYears = this.selectedYears.filter(y => y !== year);
        }
        
        this.updateMultiSelectDisplay('years');
        this.updateAvailableMonths();
        this.loadData(); // Auto-apply
    }

    handleMonthFilterChange(checkbox) {
        const month = parseInt(checkbox.value);
        
        if (checkbox.checked) {
            if (!this.selectedMonths.includes(month)) {
                this.selectedMonths.push(month);
            }
        } else {
            this.selectedMonths = this.selectedMonths.filter(m => m !== month);
        }
        
        this.updateMultiSelectDisplay('months');
        this.loadData(); // Auto-apply
    }

    updateAvailableMonths() {
        const monthsBtn = document.querySelector('[data-filter="months"]');
        const monthsDropdown = document.getElementById('months-dropdown');
        if (!monthsBtn || !monthsDropdown) return;

        if (this.selectedYears.length === 0) {
            monthsBtn.disabled = true;
            monthsBtn.querySelector('.selected-text').textContent = 'Select Year First';
            monthsDropdown.innerHTML = '';
            this.selectedMonths = [];
            monthsBtn.classList.remove('has-selection');
            return;
        }

        monthsBtn.disabled = false;

        // ✅ Use backend-provided months instead of 1–12
        const availableMonths = new Set(this.availableMonths);

        const monthNames = ['January', 'February', 'March', 'April', 'May', 'June',
                            'July', 'August', 'September', 'October', 'November', 'December'];

        monthsDropdown.innerHTML = '';
        Array.from(availableMonths).sort((a, b) => a - b).forEach(monthNum => {
            const label = document.createElement('label');
            label.className = 'checkbox-item';
            label.innerHTML = `
                <input type="checkbox" value="${monthNum}" data-filter="months" ${this.selectedMonths.includes(monthNum) ? 'checked' : ''}>
                <span>${monthNames[monthNum - 1]}</span>
            `;
            monthsDropdown.appendChild(label);

            const checkbox = label.querySelector('input[type="checkbox"]');
            checkbox.addEventListener('change', (e) => {
                this.handleMonthFilterChange(e.target);
            });
        });

        this.updateMultiSelectDisplay('months');
    }


    updateMultiSelectDisplay(filterType) {
        let btn, selected, defaultText;
        
        if (filterType === 'years') {
            btn = document.querySelector('[data-filter="years"]');
            selected = this.selectedYears;
            defaultText = 'All Years';
        } else if (filterType === 'months') {
            btn = document.querySelector('[data-filter="months"]');
            selected = this.selectedMonths;
            defaultText = this.selectedYears.length === 0 ? 'Select Year First' : 'All Months';
        }
        
        if (!btn) return;
        
        const selectedText = btn.querySelector('.selected-text');
        
        if (selected.length === 0) {
            selectedText.textContent = defaultText;
            btn.classList.remove('has-selection');
        } else if (selected.length === 1) {
            if (filterType === 'months') {
                const monthNames = ['January', 'February', 'March', 'April', 'May', 'June', 
                                'July', 'August', 'September', 'October', 'November', 'December'];
                selectedText.textContent = monthNames[selected[0] - 1];
            } else {
                selectedText.textContent = selected[0];
            }
            btn.classList.add('has-selection');
        } else {
            selectedText.textContent = `${selected.length} selected`;
            btn.classList.add('has-selection');
        }
    }

    clearAllFilters() {
        this.selectedYears = [];
        this.selectedMonths = [];
        
        // Uncheck all checkboxes
        document.querySelectorAll('.multi-select-dropdown input[type="checkbox"]').forEach(cb => {
            cb.checked = false;
        });
        
        // Update displays
        this.updateMultiSelectDisplay('years');
        this.updateMultiSelectDisplay('months');
        
        // Disable months
        const monthsBtn = document.querySelector('[data-filter="months"]');
        if (monthsBtn) {
            monthsBtn.disabled = true;
            document.getElementById('months-dropdown').innerHTML = '';
        }
        
        this.closeAllDropdowns();
        
        // Load data with defaults (current year/month)
        this.selectedYears = [parseInt(this.currentYear)];
        this.selectedMonths = [parseInt(window.budgetData.currentMonth)];
        this.loadData();
    }
    
    async loadData() {
        this.showLoading(true);
        
        try {
            // Build query parameters
            const yearsParam = this.selectedYears.join(',');
            const monthsParam = this.selectedMonths.join(',');
            const url = `${this.apiBaseUrl}/api/summary?years=${yearsParam}&months=${monthsParam}`;
            
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
        this.updateExpensesPieChart();
        this.updateAllocationsPieChart();
        this.updateAllocations();
        this.loadRecommendations();
    }
    
    updateKPIs() {
        const { income, expenses, net_summary } = this.currentData;
        
        // Total Income
        const incomeEl = document.getElementById('kpi-income');
        if (incomeEl) {
            incomeEl.textContent = this.formatCurrency(income.total);
        }
        
        // Total Spending
        const spendingEl = document.getElementById('kpi-spending');
        if (spendingEl) {
            spendingEl.textContent = this.formatCurrency(expenses.total);
        }
        
        // Net Savings (Income - Expenses)
        const savingsEl = document.getElementById('kpi-savings');
        if (savingsEl) {
            const netSavings = income.total - expenses.total;
            savingsEl.textContent = this.formatCurrency(netSavings);
        }
        
        // Update savings change indicator
        const savingsChangeEl = document.getElementById('kpi-savings-change');
        if (savingsChangeEl && net_summary) {
            const netSavings = income.total - expenses.total;
            if (netSavings > 0) {
                savingsChangeEl.textContent = `↑ ${this.formatCurrency(netSavings)} saved`;
                savingsChangeEl.className = 'kpi-change positive';
            } else if (netSavings < 0) {
                savingsChangeEl.textContent = `↓ ${this.formatCurrency(Math.abs(netSavings))} overspent`;
                savingsChangeEl.className = 'kpi-change negative';
            } else {
                savingsChangeEl.textContent = 'Break even';
                savingsChangeEl.className = 'kpi-change';
            }
        }
        
        // Total spending in bottom card
        const totalSpendingEl = document.getElementById('total-spending');
        if (totalSpendingEl) {
            totalSpendingEl.textContent = this.formatCurrency(expenses.total);
        }
        
        console.log('[BUDGET_ANALYTICS] KPIs updated');
    }
    
    updateExpensesPieChart() {
        const canvas = document.getElementById('expenses-pie-chart');
        if (!canvas) return;
        
        const { expenses } = this.currentData;
        const categoryDetails = expenses.category_details || {};
        
        // Destroy existing chart
        if (this.expensePieChart) {
            this.expensePieChart.destroy();
            this.expensePieChart = null;
        }
        
        // Get the container
        const container = canvas.parentElement;
        
        // Check if there's data
        const labels = Object.keys(categoryDetails);
        const data = Object.values(categoryDetails).map(d => d.total);
        
        if (labels.length === 0 || data.every(d => d === 0)) {
            // No data - show message and clear canvas
            const ctx = canvas.getContext('2d');
            ctx.clearRect(0, 0, canvas.width, canvas.height);
            
            // Add a message overlay
            let messageDiv = container.querySelector('.no-data-message');
            if (!messageDiv) {
                messageDiv = document.createElement('div');
                messageDiv.className = 'no-data-message';
                messageDiv.style.cssText = 'position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%); text-align: center; color: #a0aec0; font-style: italic;';
                container.style.position = 'relative';
                container.appendChild(messageDiv);
            }
            messageDiv.textContent = 'No expense data for selected period';
            canvas.style.opacity = '0.3';
            return;
        }
        
        // Remove any "no data" message
        const messageDiv = container.querySelector('.no-data-message');
        if (messageDiv) {
            messageDiv.remove();
        }
        canvas.style.opacity = '1';
        
        const colors = this.generateColors(labels.length);
        
        // Create chart
        const ctx = canvas.getContext('2d');
        this.expensePieChart = new Chart(ctx, {
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
                    title: {
                        display: true,
                        text: 'Expenses by Category',
                        font: {
                            size: 16,
                            weight: 'bold'
                        }
                    },
                    tooltip: {
                        callbacks: {
                            label: (context) => {
                                const label = context.label || '';
                                const value = this.formatCurrency(context.parsed);
                                const total = data.reduce((a, b) => a + b, 0);
                                const percentage = total > 0 ? ((context.parsed / total) * 100).toFixed(1) : 0;
                                return `${label}: ${value} (${percentage}%)`;
                            }
                        }
                    }
                },
                onClick: (event, elements) => {
                    if (elements.length > 0) {
                        const index = elements[0].index;
                        const categoryName = labels[index];
                        this.drillDownExpenseCategory(categoryName, categoryDetails[categoryName]);
                    }
                }
            }
        });
        
        console.log('[BUDGET_ANALYTICS] Expenses pie chart updated');
    }
    
    updateAllocationsPieChart() {
        const canvas = document.getElementById('allocations-pie-chart');
        if (!canvas) return;
        
        const { income, allocations } = this.currentData;
        
        // Destroy existing chart
        if (this.allocationPieChart) {
            this.allocationPieChart.destroy();
            this.allocationPieChart = null;
        }
        
        // Get bucket data
        const bucketData = allocations.by_bucket || {};
        const bucketDetails = allocations.bucket_details || {};
        
        // Calculate allocated vs unallocated
        const totalAllocated = allocations.total_allocated || 0;
        const totalIncome = income.total || 0;
        
        let investmentsAmount = bucketData.investments || 0;
        let savingsAmount = bucketData.savings || 0;
        let spendingAmount = bucketData.spending || 0;
        let notAllocatedAmount = 0;
        
        // Calculate unallocated amount
        if (totalIncome > totalAllocated) {
            notAllocatedAmount = totalIncome - totalAllocated;
        }
        
        const labels = ['Investments', 'Savings', 'Spending', 'Not Allocated'];
        const data = [investmentsAmount, savingsAmount, spendingAmount, notAllocatedAmount];
        const colors = ['#48bb78', '#4299e1', '#9f7aea', '#c3c8cfff'];
        
        // Get the container
        const container = canvas.parentElement;
        
        // Check if there's data
        if (totalIncome === 0 || data.every(d => d === 0)) {
            // No data - show message
            const ctx = canvas.getContext('2d');
            ctx.clearRect(0, 0, canvas.width, canvas.height);
            
            let messageDiv = container.querySelector('.no-data-message');
            if (!messageDiv) {
                messageDiv = document.createElement('div');
                messageDiv.className = 'no-data-message';
                messageDiv.style.cssText = 'position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%); text-align: center; color: #a0aec0; font-style: italic;';
                container.style.position = 'relative';
                container.appendChild(messageDiv);
            }
            messageDiv.textContent = 'No income data for selected period';
            canvas.style.opacity = '0.3';
            return;
        }
        
        // Remove any "no data" message
        const messageDiv = container.querySelector('.no-data-message');
        if (messageDiv) {
            messageDiv.remove();
        }
        canvas.style.opacity = '1';
        
        // Create chart
        const ctx = canvas.getContext('2d');
        this.allocationPieChart = new Chart(ctx, {
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
                    title: {
                        display: true,
                        text: 'Income Allocations',
                        font: {
                            size: 16,
                            weight: 'bold'
                        }
                    },
                    tooltip: {
                        callbacks: {
                            label: (context) => {
                                const label = context.label || '';
                                const value = this.formatCurrency(context.parsed);
                                const total = data.reduce((a, b) => a + b, 0);
                                const percentage = total > 0 ? ((context.parsed / total) * 100).toFixed(1) : 0;
                                return `${label}: ${value} (${percentage}%)`;
                            }
                        }
                    }
                },
                onClick: (event, elements) => {
                    if (elements.length > 0) {
                        const index = elements[0].index;
                        const bucketName = labels[index];
                        
                        // Don't drill down on "Not Allocated"
                        if (bucketName === 'Not Allocated') {
                            this.showNotAllocatedMessage();
                            return;
                        }
                        
                        const bucketKey = bucketName.toLowerCase();
                        const bucketCategoryData = bucketDetails[bucketKey] || {};
                        this.drillDownAllocationBucket(bucketName, bucketCategoryData, data[index]);
                    }
                }
            }
        });
        
        console.log('[BUDGET_ANALYTICS] Allocations pie chart updated');
    }
    
    drillDownExpenseCategory(categoryName, categoryData) {
        console.log('[BUDGET_ANALYTICS] Drilling down expense category:', categoryName);
        
        const contentDiv = document.getElementById('category-detail-content');
        const instructionText = document.querySelector('.drill-down-instruction');
        const categoryNameEl = document.getElementById('selected-category-name');
        const subcategoryList = document.getElementById('subcategory-list');
        
        if (instructionText) instructionText.style.display = 'none';
        if (contentDiv) contentDiv.style.display = 'block';
        if (categoryNameEl) categoryNameEl.textContent = categoryName + ' (Expense)';
        
        // Group by description
        const subcategories = this.groupByDescription(categoryData.items || []);
        
        // Update drill-down chart
        this.updateDrillDownChart(subcategories, categoryName);
        
        // Update subcategory list
        if (subcategoryList) {
            subcategoryList.innerHTML = '';
            
            Object.entries(subcategories)
                .sort((a, b) => b[1].total - a[1].total)
                .forEach(([subcatName, subcatData]) => {
                    const percentage = (subcatData.total / categoryData.total * 100).toFixed(1);
                    
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
    }
    
    drillDownAllocationBucket(bucketName, bucketCategoryData, totalAmount) {
        console.log('[BUDGET_ANALYTICS] Drilling down allocation bucket:', bucketName);
        
        const contentDiv = document.getElementById('category-detail-content');
        const instructionText = document.querySelector('.drill-down-instruction');
        const categoryNameEl = document.getElementById('selected-category-name');
        const subcategoryList = document.getElementById('subcategory-list');
        
        if (instructionText) instructionText.style.display = 'none';
        if (contentDiv) contentDiv.style.display = 'block';
        if (categoryNameEl) categoryNameEl.textContent = bucketName;
        
        // If spending with no allocations, show message
        if (Object.keys(bucketCategoryData).length === 0 && bucketName === 'Spending') {
            if (subcategoryList) {
                subcategoryList.innerHTML = '<p class="instruction-text">No specific allocations. All unallocated income goes to spending.</p>';
            }
            
            // Clear drill-down chart
            if (this.drillDownChart) {
                this.drillDownChart.destroy();
                this.drillDownChart = null;
            }
            return;
        }
        
        // Prepare data for drill-down (allocation categories within this bucket)
        const categoryData = {};
        Object.entries(bucketCategoryData).forEach(([categoryName, data]) => {
            categoryData[categoryName] = {
                total: data.total,
                count: data.items ? data.items.length : 0,
                items: data.items || []
            };
        });
        
        // Update drill-down chart
        this.updateDrillDownChart(categoryData, bucketName);
        
        // Update subcategory list
        if (subcategoryList) {
            subcategoryList.innerHTML = '';
            
            Object.entries(categoryData)
                .sort((a, b) => b[1].total - a[1].total)
                .forEach(([categoryName, data]) => {
                    const percentage = (data.total / totalAmount * 100).toFixed(1);
                    
                    const item = document.createElement('div');
                    item.className = 'subcategory-item';
                    item.innerHTML = `
                        <div class="subcategory-name">${this.escapeHtml(categoryName)}</div>
                        <div class="subcategory-details">
                            <span class="subcategory-amount">${this.formatCurrency(data.total)}</span>
                            <span class="subcategory-percentage">${percentage}%</span>
                            <span class="subcategory-count">${data.count} allocation${data.count > 1 ? 's' : ''}</span>
                        </div>
                    `;
                    
                    subcategoryList.appendChild(item);
                });
        }
    }

    showNotAllocatedMessage() {
    console.log('[BUDGET_ANALYTICS] Showing not allocated message');
    
    const contentDiv = document.getElementById('category-detail-content');
    const instructionText = document.querySelector('.drill-down-instruction');
    const categoryNameEl = document.getElementById('selected-category-name');
    const subcategoryList = document.getElementById('subcategory-list');
    
    if (instructionText) instructionText.style.display = 'none';
    if (contentDiv) contentDiv.style.display = 'block';
    if (categoryNameEl) categoryNameEl.textContent = 'Not Allocated';
    
    // Clear drill-down chart
    if (this.drillDownChart) {
        this.drillDownChart.destroy();
        this.drillDownChart = null;
    }
    
    // Show message
    if (subcategoryList) {
        subcategoryList.innerHTML = `
            <div class="not-allocated-message">
                <p>💡 This income has not been allocated to any specific category.</p>
                <p>Consider allocating your income to track where your money goes:</p>
                <ul>
                    <li>Investments (401k, IRA, etc.)</li>
                    <li>Savings (Emergency fund, etc.)</li>
                    <li>Spending (Checking account, etc.)</li>
                </ul>
            </div>
        `;
    }
    
    // Clear chart canvas
    const canvas = document.getElementById('category-pie-chart');
    if (canvas) {
        const ctx = canvas.getContext('2d');
        ctx.clearRect(0, 0, canvas.width, canvas.height);
    }
}
    
    groupByDescription(items) {
        // Group expense items by description (or "Other" if no description)
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
    
    updateDrillDownChart(subcategories, categoryName) {
        const canvas = document.getElementById('category-pie-chart');
        if (!canvas) return;
        
        // Destroy existing drill-down chart
        if (this.drillDownChart) {
            this.drillDownChart.destroy();
        }
        
        // Prepare data
        const labels = Object.keys(subcategories);
        const data = Object.values(subcategories).map(s => s.total);
        const colors = this.generateColors(labels.length);
        
        if (labels.length === 0) {
            return;
        }
        
        // Create drill-down chart
        const ctx = canvas.getContext('2d');
        this.drillDownChart = new Chart(ctx, {
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
                    title: {
                        display: true,
                        text: `${categoryName} Breakdown`,
                        font: {
                            size: 16,
                            weight: 'bold'
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
        
        console.log('[BUDGET_ANALYTICS] Drill-down chart updated for:', categoryName);
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
            const year = this.selectedYears[0] || this.currentYear;
            const month = this.selectedMonths[0] || 1;
            const url = `${this.apiBaseUrl}/api/recommendations?year=${year}&month=${month}`;
            
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