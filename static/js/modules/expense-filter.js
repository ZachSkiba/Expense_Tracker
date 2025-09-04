// Expense Table Filter Manager
class ExpenseFilterManager {
    constructor(options = {}) {
        this.tableSelector = options.tableSelector || '.expenses-table';
        this.containerSelector = options.containerSelector || '.table-wrapper';
        this.onFilterChange = options.onFilterChange || (() => {});
        
        this.filters = {
            paidBy: null,
            category: [],
            description: [],
            amountSort: null, // 'asc' or 'desc'
            dateFilter: { year: null, month: null }
        };
        
        this.originalRows = [];
        this.filteredRows = [];
        
        this.init();
    }

    init() {
        this.cacheOriginalRows();
        this.createFilterUI();
        this.attachEventListeners();
    }

    cacheOriginalRows() {
        const table = document.querySelector(this.tableSelector);
        if (!table) return;
        
        const rows = table.querySelectorAll('tbody tr[data-expense-id]');
        this.originalRows = Array.from(rows).map(row => ({
            element: row.cloneNode(true),
            data: this.extractRowData(row)
        }));
        this.filteredRows = [...this.originalRows];
    }

    extractRowData(row) {
        const participantsElement = row.querySelector('.participants');
        let participantIds = '';
        let participantNames = '';
        
        if (participantsElement) {
            participantIds = participantsElement.dataset.participantIds || '';
            participantNames = participantsElement.dataset.value || '';
        }
        
        // If no participants column exists or no participants data, 
        // assume the payer is the only participant
        if (!participantNames || participantNames.trim() === '') {
            participantNames = row.querySelector('.user').dataset.value;
        }
        
        console.log('[DEBUG] Extracted row data:', {
            id: row.dataset.expenseId,
            paidBy: row.querySelector('.user').dataset.value,
            participants: participantNames,
            participantIds: participantIds
        });
        
        return {
            id: row.dataset.expenseId,
            amount: parseFloat(row.querySelector('.amount').dataset.value),
            category: row.querySelector('.category').dataset.value,
            description: row.querySelector('.description').dataset.value,
            paidBy: row.querySelector('.user').dataset.value,
            date: row.querySelector('.date').dataset.value,
            participants: participantNames,
            participantIds: participantIds
        };
    }

    createFilterUI() {
        const container = document.querySelector(this.containerSelector);
        if (!container) return;

        const filterContainer = document.createElement('div');
        filterContainer.className = 'expense-filters';
        filterContainer.innerHTML = this.generateFilterHTML();
        
        // Insert before the table
        container.insertBefore(filterContainer, container.firstChild);
    }

    generateFilterHTML() {
        const uniqueUsers = [...new Set(this.originalRows.map(row => row.data.paidBy))];
        const uniqueCategories = [...new Set(this.originalRows.map(row => row.data.category))];
        const uniqueDescriptions = [...new Set(this.originalRows.map(row => row.data.description).filter(d => d))];
        
        // Get unique years and months from dates
        const dates = this.originalRows.map(row => new Date(row.data.date));
        const uniqueYears = [...new Set(dates.map(d => d.getFullYear()))].sort((a, b) => b - a);
        const months = [
            'January', 'February', 'March', 'April', 'May', 'June',
            'July', 'August', 'September', 'October', 'November', 'December'
        ];

        return `
            <div class="filter-header">
                <h4>Filter Expenses</h4>
                <button class="clear-filters-btn" type="button">Clear All Filters</button>
            </div>
            <div class="filter-row">
                <div class="filter-group">
                    <label>Paid By</label>
                    <select class="filter-select" data-filter="paidBy">
                        <option value="">All Users</option>
                        ${uniqueUsers.map(user => `<option value="${user}">${user}</option>`).join('')}
                    </select>
                </div>
                
                <div class="filter-group">
                    <label>Category</label>
                    <div class="multi-select-container">
                        <button class="multi-select-btn" data-filter="category">
                            <span class="selected-text">All Categories</span>
                            <span class="arrow">▼</span>
                        </button>
                        <div class="multi-select-dropdown">
                            ${uniqueCategories.map(category => `
                                <label class="checkbox-item">
                                    <input type="checkbox" value="${category}" data-filter="category">
                                    <span>${category}</span>
                                </label>
                            `).join('')}
                        </div>
                    </div>
                </div>
                
                <div class="filter-group">
                    <label>Description</label>
                    <div class="multi-select-container">
                        <button class="multi-select-btn" data-filter="description">
                            <span class="selected-text">All Descriptions</span>
                            <span class="arrow">▼</span>
                        </button>
                        <div class="multi-select-dropdown">
                            ${uniqueDescriptions.map(desc => `
                                <label class="checkbox-item">
                                    <input type="checkbox" value="${desc}" data-filter="description">
                                    <span>${desc}</span>
                                </label>
                            `).join('')}
                        </div>
                    </div>
                </div>
                
                <div class="filter-group">
                    <label>Amount</label>
                    <select class="filter-select" data-filter="amountSort">
                        <option value="">No Sorting</option>
                        <option value="asc">Lowest to Highest</option>
                        <option value="desc">Highest to Lowest</option>
                    </select>
                </div>
                
                <div class="filter-group">
                    <label>Year</label>
                    <select class="filter-select" data-filter="year">
                        <option value="">All Years</option>
                        ${uniqueYears.map(year => `<option value="${year}">${year}</option>`).join('')}
                    </select>
                </div>
                
                <div class="filter-group">
                    <label>Month</label>
                    <select class="filter-select" data-filter="month">
                        <option value="">All Months</option>
                        ${months.map((month, index) => `<option value="${index + 1}">${month}</option>`).join('')}
                    </select>
                </div>
            </div>
        `;
    }

    attachEventListeners() {
        const filterContainer = document.querySelector('.expense-filters');
        if (!filterContainer) return;

        // Single select filters
        filterContainer.querySelectorAll('.filter-select').forEach(select => {
            select.addEventListener('change', (e) => {
                this.handleSingleSelectFilter(e.target);
            });
        });

        // Multi-select dropdowns
        filterContainer.querySelectorAll('.multi-select-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                e.stopPropagation();
                this.toggleMultiSelectDropdown(btn);
            });
        });

        // Multi-select checkboxes
        filterContainer.querySelectorAll('.multi-select-dropdown input[type="checkbox"]').forEach(checkbox => {
            checkbox.addEventListener('change', (e) => {
                this.handleMultiSelectFilter(e.target);
            });
        });

        // Clear filters button
        const clearBtn = filterContainer.querySelector('.clear-filters-btn');
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
    }

    handleSingleSelectFilter(select) {
        const filterType = select.dataset.filter;
        const value = select.value;

        switch (filterType) {
            case 'paidBy':
                this.filters.paidBy = value || null;
                break;
            case 'amountSort':
                this.filters.amountSort = value || null;
                break;
            case 'year':
                this.filters.dateFilter.year = value ? parseInt(value) : null;
                break;
            case 'month':
                this.filters.dateFilter.month = value ? parseInt(value) : null;
                break;
        }

        this.applyFilters();
    }

    handleMultiSelectFilter(checkbox) {
        const filterType = checkbox.dataset.filter;
        const value = checkbox.value;
        
        if (checkbox.checked) {
            if (!this.filters[filterType].includes(value)) {
                this.filters[filterType].push(value);
            }
        } else {
            this.filters[filterType] = this.filters[filterType].filter(v => v !== value);
        }

        this.updateMultiSelectDisplay(filterType);
        this.applyFilters();
    }

    updateMultiSelectDisplay(filterType) {
        const container = document.querySelector(`[data-filter="${filterType}"]`).closest('.multi-select-container');
        const selectedText = container.querySelector('.selected-text');
        const selected = this.filters[filterType];

        if (selected.length === 0) {
            selectedText.textContent = filterType === 'category' ? 'All Categories' : 'All Descriptions';
        } else if (selected.length === 1) {
            selectedText.textContent = selected[0];
        } else {
            selectedText.textContent = `${selected.length} selected`;
        }
    }

    toggleMultiSelectDropdown(btn) {
        const dropdown = btn.nextElementSibling;
        const isOpen = dropdown.style.display === 'block';
        
        this.closeAllDropdowns();
        
        if (!isOpen) {
            dropdown.style.display = 'block';
        }
    }

    closeAllDropdowns() {
        document.querySelectorAll('.multi-select-dropdown').forEach(dropdown => {
            dropdown.style.display = 'none';
        });
    }

    applyFilters() {
        let filtered = [...this.originalRows];

        // Apply paid by filter
        if (this.filters.paidBy) {
            filtered = filtered.filter(row => row.data.paidBy === this.filters.paidBy);
        }

        // Apply category filter
        if (this.filters.category.length > 0) {
            filtered = filtered.filter(row => this.filters.category.includes(row.data.category));
        }

        // Apply description filter
        if (this.filters.description.length > 0) {
            filtered = filtered.filter(row => this.filters.description.includes(row.data.description));
        }

        // Apply date filter
        if (this.filters.dateFilter.year || this.filters.dateFilter.month) {
            filtered = filtered.filter(row => {
                const date = new Date(row.data.date);
                const year = date.getFullYear();
                const month = date.getMonth() + 1;

                let yearMatch = true;
                let monthMatch = true;

                if (this.filters.dateFilter.year) {
                    yearMatch = year === this.filters.dateFilter.year;
                }

                if (this.filters.dateFilter.month) {
                    monthMatch = month === this.filters.dateFilter.month;
                }

                return yearMatch && monthMatch;
            });
        }

        // Apply amount sorting
        if (this.filters.amountSort) {
            filtered.sort((a, b) => {
                if (this.filters.amountSort === 'asc') {
                    return a.data.amount - b.data.amount;
                } else {
                    return b.data.amount - a.data.amount;
                }
            });
        }

        this.filteredRows = filtered;
        this.updateTableDisplay();
        this.updateFilterStats();
        this.onFilterChange(this.getFilteredData());
    }

    updateTableDisplay() {
        const table = document.querySelector(this.tableSelector);
        if (!table) return;

        const tbody = table.querySelector('tbody');
        tbody.innerHTML = '';

        if (this.filteredRows.length === 0) {
            const colCount = table.querySelectorAll('thead th').length;
            tbody.innerHTML = `
                <tr>
                    <td colspan="${colCount}" style="text-align: center; color: #888; padding: 40px 20px;">
                        No expenses match the current filters
                    </td>
                </tr>
            `;
        } else {
            this.filteredRows.forEach(row => {
                tbody.appendChild(row.element.cloneNode(true));
            });
        }

        // Reattach event listeners for the new rows if expense table manager exists
        if (window.expenseTableManager && window.expenseTableManager.attachEventListenersToContainer) {
            window.expenseTableManager.attachEventListenersToContainer(tbody);
        }
    }

    updateFilterStats() {
        const countElement = document.querySelector('.expense-count');
        if (countElement) {
            const total = this.originalRows.length;
            const filtered = this.filteredRows.length;
            countElement.textContent = `(${filtered} of ${total})`;
        }
    }

    getFilteredData() {
        return {
            expenses: this.filteredRows.map(row => row.data),
            totalAmount: this.filteredRows.reduce((sum, row) => sum + row.data.amount, 0),
            count: this.filteredRows.length
        };
    }

    clearAllFilters() {
        // Reset filter state
        this.filters = {
            paidBy: null,
            category: [],
            description: [],
            amountSort: null,
            dateFilter: { year: null, month: null }
        };

        // Reset UI
        document.querySelectorAll('.filter-select').forEach(select => {
            select.value = '';
        });

        document.querySelectorAll('.multi-select-dropdown input[type="checkbox"]').forEach(checkbox => {
            checkbox.checked = false;
        });

        document.querySelectorAll('.selected-text').forEach((text, index) => {
            text.textContent = index === 0 ? 'All Categories' : 'All Descriptions';
        });

        this.closeAllDropdowns();
        this.applyFilters();
        
        // Trigger callback to reload original data
        this.onFilterChange({ 
            expenses: this.originalRows.map(row => row.data), 
            totalAmount: this.originalRows.reduce((sum, row) => sum + row.data.amount, 0), 
            count: this.originalRows.length,
            isCleared: true 
        });
    }

    // Public method to refresh filters when data changes
    refresh() {
        this.cacheOriginalRows();
        
        // Remove old filter UI
        const oldFilters = document.querySelector('.expense-filters');
        if (oldFilters) {
            oldFilters.remove();
        }
        
        // Recreate filter UI
        this.createFilterUI();
        this.attachEventListeners();
        this.applyFilters();
    }
}

// Export for use in other modules
window.ExpenseFilterManager = ExpenseFilterManager;
