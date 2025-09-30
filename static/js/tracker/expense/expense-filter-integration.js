class ExpenseFilterManager {
    constructor(options = {}) {
        this.tableSelector = options.tableSelector || '.expenses-table';
        this.containerSelector = options.containerSelector || '.table-wrapper';
        this.onFilterChange = options.onFilterChange || (() => {});
        

        this.filters = {
            paidBy: [],
            category: [],
            description: [],
            participants: [],
            amountSort: [],
            dateFilter: { years: [], months: [] },
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
        
        // Get unique participants from all expenses
        const allParticipants = new Set();
        this.originalRows.forEach(row => {
            if (row.data.participants) {
                // participants is a comma-separated string
                row.data.participants.split(',').forEach(p => {
                    const name = p.trim();
                    if (name) allParticipants.add(name);
                });
            }
        });
        const uniqueParticipants = [...allParticipants].sort();

        // Get unique years from dates (assuming YYYY-MM-DD format)
        const dates = this.originalRows.map(row => {
            const [year, month] = row.data.date.split('-').map(num => parseInt(num));
            return { year, month };
        });
        const uniqueYears = [...new Set(dates.map(d => d.year))].sort((a, b) => b - a);

        // Amount sort options
        const amountSortOptions = [
            { value: 'asc', label: 'Lowest to Highest' },
            { value: 'desc', label: 'Highest to Lowest' }
        ];

        return `
            <div class="filter-header">
                <h4>Filter Expenses</h4>
                <button class="clear-filters-btn" type="button">Clear All Filters</button>
            </div>
            <div class="filter-row">
                <div class="filter-group">
                    <label>Paid By</label>
                    <div class="multi-select-container">
                        <button class="multi-select-btn" data-filter="paidBy">
                            <span class="selected-text">All Users</span>
                            <span class="arrow">▼</span>
                        </button>
                        <div class="multi-select-dropdown">
                            ${uniqueUsers.map(user => `
                                <label class="checkbox-item">
                                    <input type="checkbox" value="${user}" data-filter="paidBy">
                                    <span>${user}</span>
                                </label>
                            `).join('')}
                        </div>
                    </div>
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
                    <label>Participants</label>
                    <div class="multi-select-container">
                        <button class="multi-select-btn" data-filter="participants">
                            <span class="selected-text">All Participants</span>
                            <span class="arrow">▼</span>
                        </button>
                        <div class="multi-select-dropdown">
                            ${uniqueParticipants.map(participant => `
                                <label class="checkbox-item">
                                    <input type="checkbox" value="${participant}" data-filter="participants">
                                    <span>${participant}</span>
                                </label>
                            `).join('')}
                        </div>
                    </div>
                </div>

                <div class="filter-group">
                    <label>Amount Sort</label>
                    <div class="multi-select-container">
                        <button class="multi-select-btn" data-filter="amountSort">
                            <span class="selected-text">No Sorting</span>
                            <span class="arrow">▼</span>
                        </button>
                        <div class="multi-select-dropdown">
                            ${amountSortOptions.map(option => `
                                <label class="checkbox-item">
                                    <input type="checkbox" value="${option.value}" data-filter="amountSort">
                                    <span>${option.label}</span>
                                </label>
                            `).join('')}
                        </div>
                    </div>
                </div>
                
                <div class="filter-group date-filter-group">
                    <label>Year</label>
                    <div class="multi-select-container">
                        <button class="multi-select-btn" data-filter="year">
                            <span class="selected-text">All Years</span>
                            <span class="arrow">▼</span>
                        </button>
                        <div class="multi-select-dropdown">
                            ${uniqueYears.map(year => `
                                <label class="checkbox-item">
                                    <input type="checkbox" value="${year}" data-filter="year">
                                    <span>${year}</span>
                                </label>
                            `).join('')}
                        </div>
                    </div>
                </div>
                
                <div class="filter-group date-filter-group">
                    <label>Month</label>
                    <div class="multi-select-container">
                        <button class="multi-select-btn" data-filter="month" disabled>
                            <span class="selected-text">Select Year First</span>
                            <span class="arrow">▼</span>
                        </button>
                        <div class="multi-select-dropdown" id="month-dropdown">
                            <!-- Months will be populated dynamically based on selected years -->
                        </div>
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

        // Close dropdowns on scroll/resize
        window.addEventListener('scroll', () => {
            this.closeAllDropdowns();
        }, true);

        window.addEventListener('resize', () => {
            this.closeAllDropdowns();
        });

    }

    handleMultiSelectFilter(checkbox) {
        const filterType = checkbox.dataset.filter;
        const value = checkbox.value;
        
        // Handle different filter types
        if (filterType === 'year') {
            if (checkbox.checked) {
                if (!this.filters.dateFilter.years.includes(parseInt(value))) {
                    this.filters.dateFilter.years.push(parseInt(value));
                }
            } else {
                this.filters.dateFilter.years = this.filters.dateFilter.years.filter(v => v !== parseInt(value));
            }
            
            // Update available months based on selected years
            this.updateAvailableMonths();
            
        } else if (filterType === 'month') {
            if (checkbox.checked) {
                if (!this.filters.dateFilter.months.includes(parseInt(value))) {
                    this.filters.dateFilter.months.push(parseInt(value));
                }
            } else {
                this.filters.dateFilter.months = this.filters.dateFilter.months.filter(v => v !== parseInt(value));
            }
        } else if (filterType === 'amountSort') {
            // Amount sort should be single selection, so clear others first
            this.filters[filterType] = [];
            if (checkbox.checked) {
                this.filters[filterType].push(value);
                // Uncheck other amount sort options
                const container = checkbox.closest('.multi-select-dropdown');
                container.querySelectorAll('input[type="checkbox"]').forEach(cb => {
                    if (cb !== checkbox) {
                        cb.checked = false;
                    }
                });
            }
        } else {
            // Handle regular multi-select filters
            if (checkbox.checked) {
                if (!this.filters[filterType].includes(value)) {
                    this.filters[filterType].push(value);
                }
            } else {
                this.filters[filterType] = this.filters[filterType].filter(v => v !== value);
            }
        }

        this.updateMultiSelectDisplay(filterType);
        this.applyFilters();
    }

    updateAvailableMonths() {
        const monthButton = document.querySelector('[data-filter="month"]');
        const monthDropdown = document.getElementById('month-dropdown');
        
        if (!monthButton || !monthDropdown) return;
        
        // If no years are selected, disable months
        if (this.filters.dateFilter.years.length === 0) {
            monthButton.disabled = true;
            monthButton.querySelector('.selected-text').textContent = 'Select Year First';
            monthDropdown.innerHTML = '';
            this.filters.dateFilter.months = []; // Clear selected months
            monthButton.classList.remove('has-selection');
            return;
        }
        
        // Enable months and populate with available months for selected years
        monthButton.disabled = false;
        
        // Get months that have expenses for the selected years
        const availableMonths = new Set();
        this.originalRows.forEach(row => {
            const [year, month] = row.data.date.split('-').map(num => parseInt(num));
            if (this.filters.dateFilter.years.includes(year)) {
                availableMonths.add(month);
            }
        });
        
        const months = [
            'January', 'February', 'March', 'April', 'May', 'June',
            'July', 'August', 'September', 'October', 'November', 'December'
        ];
        
        // Clear and repopulate month options
        monthDropdown.innerHTML = '';
        
        Array.from(availableMonths).sort((a, b) => a - b).forEach(monthNum => {
            const checkbox = document.createElement('label');
            checkbox.className = 'checkbox-item';
            checkbox.innerHTML = `
                <input type="checkbox" value="${monthNum}" data-filter="month" ${this.filters.dateFilter.months.includes(monthNum) ? 'checked' : ''}>
                <span>${months[monthNum - 1]}</span>
            `;
            monthDropdown.appendChild(checkbox);
        });
        
        // Remove months from filter that are no longer available
        this.filters.dateFilter.months = this.filters.dateFilter.months.filter(month => 
            availableMonths.has(month)
        );
        
        // Re-attach event listeners to new month checkboxes
        monthDropdown.querySelectorAll('input[type="checkbox"]').forEach(checkbox => {
            checkbox.addEventListener('change', (e) => {
                this.handleMultiSelectFilter(e.target);
            });
        });
        
        // Update display
        this.updateMultiSelectDisplay('month');
        
        console.log(`[DEBUG] Updated available months for years [${this.filters.dateFilter.years}]: [${Array.from(availableMonths).sort()}]`);
    }

    updateMultiSelectDisplay(filterType) {
        let container, selected, defaultText;
        
        if (filterType === 'year') {
            container = document.querySelector(`[data-filter="year"]`).closest('.multi-select-container');
            selected = this.filters.dateFilter.years;
            defaultText = 'All Years';
        } else if (filterType === 'month') {
            container = document.querySelector(`[data-filter="month"]`).closest('.multi-select-container');
            selected = this.filters.dateFilter.months;
            
            // Special handling for month display
            if (this.filters.dateFilter.years.length === 0) {
                defaultText = 'Select Year First';
            } else {
                defaultText = 'All Months';
            }
        } else {
            container = document.querySelector(`[data-filter="${filterType}"]`).closest('.multi-select-container');
            selected = this.filters[filterType];
            defaultText = {
                'paidBy': 'All Users',
                'category': 'All Categories',
                'description': 'All Descriptions',
                'participants': 'All Participants',
                'amountSort': 'No Sorting'
            }[filterType];
        }

        const selectedText = container.querySelector('.selected-text');
        
        if (selected.length === 0) {
            selectedText.textContent = defaultText;
            container.querySelector('.multi-select-btn').classList.remove('has-selection');
        } else if (selected.length === 1) {
            if (filterType === 'month') {
                const months = ['January', 'February', 'March', 'April', 'May', 'June',
                               'July', 'August', 'September', 'October', 'November', 'December'];
                selectedText.textContent = months[selected[0] - 1];
            } else if (filterType === 'amountSort') {
                const sortLabels = { 'asc': 'Lowest to Highest', 'desc': 'Highest to Lowest' };
                selectedText.textContent = sortLabels[selected[0]];
            } else {
                selectedText.textContent = selected[0];
            }
            container.querySelector('.multi-select-btn').classList.add('has-selection');
        } else {
            selectedText.textContent = `${selected.length} selected`;
            container.querySelector('.multi-select-btn').classList.add('has-selection');
        }
    }

    toggleMultiSelectDropdown(btn) {
    // Don't open month dropdown if it's disabled
    if (btn.disabled) {
        return;
    }
    
    const dropdown = btn.nextElementSibling;
    const isOpen = dropdown.style.display === 'block';
    
    this.closeAllDropdowns();
    
    if (!isOpen) {
        dropdown.style.display = 'block';
        
        // Position the dropdown relative to the button
        const btnRect = btn.getBoundingClientRect();
        const viewportHeight = window.innerHeight;
        const dropdownMaxHeight = 300;
        
        // Calculate if there's enough space below
        const spaceBelow = viewportHeight - btnRect.bottom;
        const spaceAbove = btnRect.top;
        
        // Position dropdown
        dropdown.style.left = `${btnRect.left}px`;
        dropdown.style.width = `${Math.max(btnRect.width, 200)}px`;
        
        // If not enough space below, show above
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

    applyFilters() {
        let filtered = [...this.originalRows];

        // Apply paid by filter
        if (this.filters.paidBy.length > 0) {
            filtered = filtered.filter(row => this.filters.paidBy.includes(row.data.paidBy));
        }

        // Apply category filter
        if (this.filters.category.length > 0) {
            filtered = filtered.filter(row => this.filters.category.includes(row.data.category));
        }

        // Apply description filter
        if (this.filters.description.length > 0) {
            filtered = filtered.filter(row => this.filters.description.includes(row.data.description));
        }

        if (this.filters.participants.length > 0) {
            filtered = filtered.filter(row => {
                // Check if ANY selected participant is in the expense
                const rowParticipants = row.data.participants.split(',').map(p => p.trim());
                return this.filters.participants.some(selectedParticipant => 
                    rowParticipants.includes(selectedParticipant)
                );
            });
        }

        // Apply date filter
        if (this.filters.dateFilter.years.length > 0 || this.filters.dateFilter.months.length > 0) {
            filtered = filtered.filter(row => {
                // Parse date directly from YYYY-MM-DD format
                const [rowYear, rowMonth] = row.data.date.split('-').map(num => parseInt(num));
                if (!rowYear || !rowMonth) return false;

                let yearMatch = this.filters.dateFilter.years.length === 0 || this.filters.dateFilter.years.includes(rowYear);
                let monthMatch = this.filters.dateFilter.months.length === 0 || this.filters.dateFilter.months.includes(rowMonth);

                console.log(`[DEBUG] Date filter: Row date ${row.data.date} (${rowYear}-${rowMonth}) against filter years: [${this.filters.dateFilter.years}], months: [${this.filters.dateFilter.months}] -> Match: ${yearMatch && monthMatch}`);
                return yearMatch && monthMatch;
            });
        }

        // Apply amount sorting
        if (this.filters.amountSort.length > 0) {
            const sortType = this.filters.amountSort[0]; // Should only have one selection
            filtered.sort((a, b) => {
                if (sortType === 'asc') {
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
        
        // Prepare filter change data - convert to old format for compatibility
        const filterChangeData = {
            count: filtered,
            totalAmount: totalAmount,
            expenses: this.filteredRows.map(row => row.data),
            dateFilter: {
                year: this.filters.dateFilter.years.length === 1 ? this.filters.dateFilter.years[0] : null,
                month: this.filters.dateFilter.months.length === 1 ? this.filters.dateFilter.months[0] : null,
                years: this.filters.dateFilter.years,
                months: this.filters.dateFilter.months
            },
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
            paidBy: [],
            category: [],
            description: [],
            participants: [],
            amountSort: [],
            dateFilter: { years: [], months: [] },
            dateRange: { start: null, end: null }
        };

        // Reset UI checkboxes
        document.querySelectorAll('.multi-select-dropdown input[type="checkbox"]').forEach(checkbox => {
            checkbox.checked = false;
        });

        // Reset display text
        document.querySelectorAll('.selected-text').forEach((text, index) => {
            const btn = text.closest('.multi-select-btn');
            const filterType = btn.dataset.filter;
            
            const defaultTexts = {
                'paidBy': 'All Users',
                'category': 'All Categories', 
                'description': 'All Descriptions',
                'participants': 'All Participants',
                'amountSort': 'No Sorting',
                'year': 'All Years',
                'month': 'Select Year First'
            };
            
            text.textContent = defaultTexts[filterType];
            btn.classList.remove('has-selection');
        });

        // Disable month filter and clear its options
        const monthButton = document.querySelector('[data-filter="month"]');
        const monthDropdown = document.getElementById('month-dropdown');
        if (monthButton && monthDropdown) {
            monthButton.disabled = true;
            monthDropdown.innerHTML = '';
        }

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