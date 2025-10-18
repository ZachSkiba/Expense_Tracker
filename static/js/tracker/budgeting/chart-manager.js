/**
 * Chart Manager - Handles all chart rendering and interactions
 */

class BudgetChartManager {
    constructor() {
        this.expensePieChart = null;
        this.allocationPieChart = null;
        this.drillDownChart = null;
        this.currentData = null;
    }
    
    setCurrentData(data) {
        this.currentData = data;
    }
    
    updateAllCharts() {
        if (!this.currentData) {
            console.warn('[CHART_MANAGER] No data to display');
            return;
        }
        
        this.updateExpensesPieChart();
        
        // Only update allocations chart if it exists (personal trackers only)
        const allocCanvas = document.getElementById('allocations-pie-chart');
        if (allocCanvas) {
            this.updateAllocationsPieChart();
        }
    }
    
    clearDetailedBreakdown() {
        const detailCard = document.querySelector('.category-details-card');
        
        if (detailCard) {
            detailCard.style.display = 'none';
        }
        
        // Destroy drill-down chart if it exists
        if (this.drillDownChart) {
            this.drillDownChart.destroy();
            this.drillDownChart = null;
        }
        
        // Clear the canvas
        const canvas = document.getElementById('category-pie-chart');
        if (canvas) {
            const ctx = canvas.getContext('2d');
            ctx.clearRect(0, 0, canvas.width, canvas.height);
        }
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
        
        const colors = BudgetUIHelpers.generateColors(labels.length);
        
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
                                const value = BudgetUIHelpers.formatCurrency(context.parsed);
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
        
        console.log('[CHART_MANAGER] Expenses pie chart updated');
    }
    
    updateAllocationsPieChart() {
        const canvas = document.getElementById('allocations-pie-chart');
        if (!canvas) return;
        
        const { income, allocations } = this.currentData;
        
        // Safety check: if no income data (group trackers), skip
        if (!income || !allocations) {
            console.log('[CHART_MANAGER] No income/allocation data - skipping allocations chart');
            return;
        }
        
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
                                const value = BudgetUIHelpers.formatCurrency(context.parsed);
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
        
        console.log('[CHART_MANAGER] Allocations pie chart updated');
    }
    
    drillDownExpenseCategory(categoryName, categoryData) {
        console.log('[CHART_MANAGER] Drilling down expense category:', categoryName);
        
        const detailCard = document.querySelector('.category-details-card');
        const contentDiv = document.getElementById('category-detail-content');
        const categoryNameEl = document.getElementById('selected-category-name');
        const subcategoryList = document.getElementById('subcategory-list');
        const rightColumn = document.querySelector('.right-column');

        if (detailCard) {
            detailCard.style.display = 'block';
            
            // For personal trackers, move detail card into right column
            if (rightColumn && !detailCard.parentElement.classList.contains('right-column')) {
                rightColumn.insertBefore(detailCard, rightColumn.firstChild);
            }
        }

        if (contentDiv) contentDiv.style.display = 'block';
        if (categoryNameEl) categoryNameEl.textContent = categoryName + ' (Expense)';
        
        // Group by description
        const subcategories = BudgetUIHelpers.groupByDescription(categoryData.items || []);
        
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
                        <div class="subcategory-name">${BudgetUIHelpers.escapeHtml(subcatName)}</div>
                        <div class="subcategory-details">
                            <span class="subcategory-amount">${BudgetUIHelpers.formatCurrency(subcatData.total)}</span>
                            <span class="subcategory-percentage">${percentage}%</span>
                            <span class="subcategory-count">${subcatData.count} transaction${subcatData.count > 1 ? 's' : ''}</span>
                        </div>
                    `;
                    
                    subcategoryList.appendChild(item);
                });
        }
    }
    
    drillDownAllocationBucket(bucketName, bucketCategoryData, totalAmount) {
        console.log('[CHART_MANAGER] Drilling down allocation bucket:', bucketName);
        
        const detailCard = document.querySelector('.category-details-card');
        const contentDiv = document.getElementById('category-detail-content');
        const categoryNameEl = document.getElementById('selected-category-name');
        const subcategoryList = document.getElementById('subcategory-list');
        
        const rightColumn = document.querySelector('.right-column');

        if (detailCard) {
            detailCard.style.display = 'block';
            
            // For personal trackers, move detail card into right column
            if (rightColumn && !detailCard.parentElement.classList.contains('right-column')) {
                rightColumn.insertBefore(detailCard, rightColumn.firstChild);
            }
        }

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
                        <div class="subcategory-name">${BudgetUIHelpers.escapeHtml(categoryName)}</div>
                        <div class="subcategory-details">
                            <span class="subcategory-amount">${BudgetUIHelpers.formatCurrency(data.total)}</span>
                            <span class="subcategory-percentage">${percentage}%</span>
                            <span class="subcategory-count">${data.count} allocation${data.count > 1 ? 's' : ''}</span>
                        </div>
                    `;
                    
                    subcategoryList.appendChild(item);
                });
        }
    }
    
    showNotAllocatedMessage() {
        console.log('[CHART_MANAGER] Showing not allocated message');
        
        const detailCard = document.querySelector('.category-details-card');
        const contentDiv = document.getElementById('category-detail-content');
        const categoryNameEl = document.getElementById('selected-category-name');
        const subcategoryList = document.getElementById('subcategory-list');
        
        const rightColumn = document.querySelector('.right-column');

        if (detailCard) {
            detailCard.style.display = 'block';
            
            // For personal trackers, move detail card into right column
            if (rightColumn && !detailCard.parentElement.classList.contains('right-column')) {
                rightColumn.insertBefore(detailCard, rightColumn.firstChild);
            }
        }

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
        const colors = BudgetUIHelpers.generateColors(labels.length);
        
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
                                const value = BudgetUIHelpers.formatCurrency(context.parsed);
                                const percentage = ((context.parsed / data.reduce((a, b) => a + b, 0)) * 100).toFixed(1);
                                return `${label}: ${value} (${percentage}%)`;
                            }
                        }
                    }
                }
            }
        });
        
        console.log('[CHART_MANAGER] Drill-down chart updated for:', categoryName);
    }
}