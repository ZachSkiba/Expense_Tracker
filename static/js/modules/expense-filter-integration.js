class ExpenseFilterManager {
    constructor(options = {}) {
        this.tableSelector = options.tableSelector || '.expenses-table';
        this.containerSelector = options.containerSelector || '.table-wrapper';
        this.onFilterChange = options.onFilterChange || (() => {});
        
        // Add search styles
        const style = document.createElement('style');
        style.textContent = `
            .search-container {
                padding: 8px;
                border-bottom: 1px solid #ddd;
                position: sticky;
                top: 0;
                background: white;
                z-index: 1;
            }
            .description-search {
                width: 100%;
                padding: 6px;
                border: 1px solid #ddd;
                border-radius: 4px;
                font-size: 14px;
            }
            .description-search:focus {
                outline: none;
                border-color: #007bff;
            }
            .checkbox-list {
                max-height: 200px;
                overflow: auto;
                scrollbar-width: thin;  /* For Firefox */
            }
            /* Make both vertical and horizontal scrollbars small */
            .checkbox-list::-webkit-scrollbar,
            .multi-select-dropdown::-webkit-scrollbar {
                width: 4px;
                height: 4px;
            }
            .checkbox-list::-webkit-scrollbar-track,
            .multi-select-dropdown::-webkit-scrollbar-track {
                background: #f1f1f1;
                border-radius: 2px;
            }
            .checkbox-list::-webkit-scrollbar-thumb,
            .multi-select-dropdown::-webkit-scrollbar-thumb {
                background: #888;
                border-radius: 2px;
            }
            .checkbox-list::-webkit-scrollbar-thumb:hover,
            .multi-select-dropdown::-webkit-scrollbar-thumb:hover {
                background: #555;
            }
            /* Corner where scrollbars meet */
            .checkbox-list::-webkit-scrollbar-corner,
            .multi-select-dropdown::-webkit-scrollbar-corner {
                background: #f1f1f1;
            }
            .multi-select-dropdown {
                max-height: none;
                overflow: auto;
                scrollbar-width: thin;  /* For Firefox */
            }
        `;
        document.head.appendChild(style);
        
        this.filters = {
            paidBy: null,
            category: [],
            description: [],
            amountSort: null, // 'asc' or 'desc'
            dateFilter: { year: null, month: null },
            dateRange: { start: null, end: null }
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
        const cells = row.querySelectorAll('td');
        
        // Get participants from data-value attribute, not text content
        const participantsCell = row.querySelector('td.participants');
        let participants = '';
        if (participantsCell) {
            // Use data-value attribute which contains the comma-separated participant names
            participants = participantsCell.getAttribute('data-value') || '';
            console.log('[DEBUG] Extracted participants from data-value:', participants);
        }
        
        return {
            id: row.dataset.expenseId,
            amount: parseFloat(cells[0]?.dataset.value || cells[0]?.textContent.replace('$', '') || 0),
            category: cells[1]?.dataset.value || cells[1]?.textContent.trim() || '',
            description: cells[2]?.dataset.value || cells[2]?.textContent.trim() || '',
            paidBy: cells[3]?.dataset.value || cells[3]?.textContent.trim() || '',
            participants: participants, // Now correctly extracted from data-value
            date: cells[participantsCell ? 5 : 4]?.dataset.value || cells[participantsCell ? 5 : 4]?.textContent.trim() || ''
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
        
        // Get unique years and months from dates (assuming YYYY-MM-DD format)
        const dates = this.originalRows.map(row => {
            const [year, month] = row.data.date.split('-').map(num => parseInt(num));
            return { year, month };
        });
        const uniqueYears = [...new Set(dates.map(d => d.year))].sort((a, b) => b - a);
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
                            <div class="search-container">
                                <input type="text" class="description-search" placeholder="Search descriptions...">
                            </div>
                            <div class="checkbox-list">
                                ${uniqueDescriptions.map(desc => `
                                    <label class="checkbox-item">
                                        <input type="checkbox" value="${desc}" data-filter="description">
                                        <span>${desc}</span>
                                    </label>
                                `).join('')}
                            </div>
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
                
                <div class="filter-group date-filter-group">
                    <label>Date Period</label>
                    <div class="date-filter-container">
                        <select class="filter-select date-year" data-filter="year">
                            <option value="">All Years</option>
                            ${uniqueYears.map(year => `<option value="${year}">${year}</option>`).join('')}
                        </select>
                        <select class="filter-select date-month" data-filter="month" disabled>
                            <option value="">All Months</option>
                            ${months.map((month, i) => `<option value="${i + 1}">${month}</option>`).join('')}
                        </select>
                    </div>
                </div>
            </div>
        `;
    }

    filterDescriptionOptions(searchText) {
        const checkboxContainer = document.querySelector('.multi-select-dropdown .checkbox-list');
        if (!checkboxContainer) return;

        const items = checkboxContainer.querySelectorAll('.checkbox-item');
        const searchLower = searchText.toLowerCase();

        items.forEach(item => {
            const description = item.querySelector('span').textContent.toLowerCase();
            if (description.includes(searchLower)) {
                item.style.display = '';
            } else {
                item.style.display = 'none';
            }
        });
    }

    attachEventListeners() {
        const filterContainer = document.querySelector('.expense-filters');
        if (!filterContainer) return;

        // Description search
        const searchInput = filterContainer.querySelector('.description-search');
        if (searchInput) {
            searchInput.addEventListener('input', (e) => {
                this.filterDescriptionOptions(e.target.value);
            });
            // Prevent dropdown from closing when clicking in search
            searchInput.addEventListener('click', (e) => {
                e.stopPropagation();
            });
        }

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
                this.handleYearChange(value);
                break;
            case 'month':
                this.filters.dateFilter.month = value ? parseInt(value) : null;
                console.log(`[DEBUG] Month filter set to: ${this.filters.dateFilter.month}`);
                break;
        }

        this.applyFilters();
    }

    handleYearChange(yearValue) {
        const monthSelect = document.querySelector('.date-month');
        if (!monthSelect) return;

        if (yearValue) {
            // Enable month selector and populate with available months for the selected year
            monthSelect.disabled = false;
            this.populateAvailableMonths(parseInt(yearValue));
        } else {
            // Disable month selector and reset
            monthSelect.disabled = true;
            monthSelect.value = '';
            this.filters.dateFilter.month = null;
        }
    }

    populateAvailableMonths(selectedYear) {
        const monthSelect = document.querySelector('.date-month');
        if (!monthSelect) return;

        // Get months that have expenses for the selected year
        const availableMonths = new Set();
        this.originalRows.forEach(row => {
            // Parse date directly from YYYY-MM-DD format
            const [year, month] = row.data.date.split('-').map(num => parseInt(num));
            if (year === selectedYear) {
                availableMonths.add(month); // month is already 1-based
            }
        });

        const months = [
            'January', 'February', 'March', 'April', 'May', 'June',
            'July', 'August', 'September', 'October', 'November', 'December'
        ];

        // Clear and repopulate month options
        monthSelect.innerHTML = '<option value="">All Months</option>';
        
        Array.from(availableMonths).sort((a, b) => a - b).forEach(monthNum => {
            const option = document.createElement('option');
            option.value = monthNum;
            option.textContent = months[monthNum - 1]; // monthNum is 1-based, so subtract 1 for array index
            console.log(`[DEBUG] Adding month option: ${monthNum} = ${months[monthNum - 1]}`);
            monthSelect.appendChild(option);
        });

        // If current month filter is not available for this year, reset it
        if (this.filters.dateFilter.month && !availableMonths.has(this.filters.dateFilter.month)) {
            this.filters.dateFilter.month = null;
            monthSelect.value = '';
        }
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
                // Parse date directly from YYYY-MM-DD format
                const [rowYear, rowMonth] = row.data.date.split('-').map(num => parseInt(num));
                if (!rowYear || !rowMonth) return false;

                let yearMatch = true;
                let monthMatch = true;

                if (this.filters.dateFilter.year) {
                    yearMatch = rowYear === this.filters.dateFilter.year;
                }

                if (this.filters.dateFilter.month) {
                    monthMatch = rowMonth === this.filters.dateFilter.month;
                }

                console.log(`[DEBUG] Date filter: Row date ${row.data.date} (${rowYear}-${rowMonth}) against filter year: ${this.filters.dateFilter.year}, month: ${this.filters.dateFilter.month} -> Match: ${yearMatch && monthMatch}`);
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
        this.notifyFilterChange();
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
        if (window.expenseTableManager) {
            window.expenseTableManager.setupEditableCells();
            window.expenseTableManager.setupDeleteButtons();
        }
    }

    updateFilterStats() {
        const total = this.originalRows.length;
        const filtered = this.filteredRows.length;
        
        // Calculate total amount for filtered expenses
        const totalAmount = this.filteredRows.reduce((sum, row) => sum + row.data.amount, 0);
        
        // Prepare filter change data
        const filterChangeData = {
            count: filtered,
            totalAmount: totalAmount,
            expenses: this.filteredRows.map(row => row.data),
            dateFilter: this.filters.dateFilter,
            isCleared: false
        };
        
        // Notify about filter change
        if (this.onFilterChange) {
            this.onFilterChange(filterChangeData);
        }
    }

    notifyFilterChange() {
        // Already handled in updateFilterStats
    }

    clearAllFilters() {
        // Reset filter state
        this.filters = {
            paidBy: null,
            category: [],
            description: [],
            amountSort: null,
            dateFilter: { year: null, month: null },
            dateRange: { start: null, end: null }
        };

        // Reset UI
        document.querySelectorAll('.filter-select').forEach(select => {
            select.value = '';
            if (select.classList.contains('date-month')) {
                select.disabled = true;
            }
        });

        document.querySelectorAll('.multi-select-dropdown input[type="checkbox"]').forEach(checkbox => {
            checkbox.checked = false;
        });

        document.querySelectorAll('.selected-text').forEach((text, index) => {
            text.textContent = index === 0 ? 'All Categories' : 'All Descriptions';
        });

        this.closeAllDropdowns();
        this.applyFilters();
        
        // Notify that filters were cleared
        const totalAmount = this.originalRows.reduce((sum, row) => sum + row.data.amount, 0);
        if (this.onFilterChange) {
            this.onFilterChange({
                count: this.originalRows.length,
                totalAmount: totalAmount,
                expenses: this.originalRows.map(row => row.data),
                dateFilter: null,
                isCleared: true
            });
        }
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