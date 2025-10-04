/**
 * Filter Manager - Handles all filter UI and logic
 */

class BudgetFilterManager {
    constructor(dataService, onFilterChange) {
        this.dataService = dataService;
        this.onFilterChange = onFilterChange; // Callback when filters change
        
        this.selectedYears = [];
        this.selectedMonths = [];
        this.availableYears = [];
        this.availableMonths = [];
        this.currentAvailableMonths = [];
        
        this.bindEvents();
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
    }
    
    async initialize(currentYear, currentMonth) {
        // Load available data
        const result = await this.dataService.fetchAvailablePeriods();
        
        if (result.success) {
            this.availableYears = result.years;
            this.availableMonths = result.months;
            
            // Set defaults to current year/month
            this.selectedYears = [parseInt(currentYear)];
            this.selectedMonths = [parseInt(currentMonth)];
            
            this.populateFilters();
            return true;
        }
        
        return false;
    }
    
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
            
            // Attach event listeners
            yearsDropdown.querySelectorAll('input[type="checkbox"]').forEach(cb => {
                cb.addEventListener('change', (e) => {
                    this.handleYearFilterChange(e.target);
                });
            });
            
            this.updateMultiSelectDisplay('years');
        }
        
        // Populate months if years are selected
        if (this.selectedYears.length > 0) {
            this.updateAvailableMonths();
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
    
    async handleYearFilterChange(checkbox) {
        const year = parseInt(checkbox.value);
        
        if (checkbox.checked) {
            if (!this.selectedYears.includes(year)) {
                this.selectedYears.push(year);
            }
        } else {
            this.selectedYears = this.selectedYears.filter(y => y !== year);
        }
        
        this.updateMultiSelectDisplay('years');
        
        // Clear previously selected months since year changed
        this.selectedMonths = [];
        
        await this.updateAvailableMonths();
        
        // Auto-select all available months for the new year selection
        if (this.currentAvailableMonths && this.currentAvailableMonths.length > 0) {
            this.selectedMonths = [...this.currentAvailableMonths];
            // Update month checkboxes
            document.querySelectorAll('[data-filter="months"]').forEach(cb => {
                cb.checked = this.selectedMonths.includes(parseInt(cb.value));
            });
            this.updateMultiSelectDisplay('months');
        }
        
        // Trigger callback
        this.onFilterChange();
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
        
        // Trigger callback
        this.onFilterChange();
    }
    
    async updateAvailableMonths() {
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

        // Fetch months specific to selected years
        try {
            const result = await this.dataService.fetchAvailablePeriods(this.selectedYears);
            
            if (result.success) {
                const availableMonths = result.months || [];
                
                const monthNames = BudgetUIHelpers.getMonthNames();

                monthsDropdown.innerHTML = '';
                
                if (availableMonths.length === 0) {
                    monthsBtn.disabled = true;
                    monthsBtn.querySelector('.selected-text').textContent = 'No data for selected years';
                    this.selectedMonths = [];
                    monthsBtn.classList.remove('has-selection');
                    return;
                }
                
                availableMonths.sort((a, b) => a - b).forEach(monthNum => {
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
                
                // Store available months for this year selection
                this.currentAvailableMonths = availableMonths;

                this.updateMultiSelectDisplay('months');
            }
        } catch (error) {
            console.error('[FILTER_MANAGER] Error fetching available months:', error);
            monthsBtn.disabled = true;
            monthsBtn.querySelector('.selected-text').textContent = 'Error loading months';
        }
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
                const monthNames = BudgetUIHelpers.getMonthNames();
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
    
    async clearAllFilters() {
        // Get current year/month from window data
        const currentYear = parseInt(window.budgetData.currentYear);
        const currentMonth = parseInt(window.budgetData.currentMonth);
        
        // Reset to current year and month (defaults)
        this.selectedYears = [currentYear];
        this.selectedMonths = [currentMonth];
        
        // Update all year checkboxes
        document.querySelectorAll('[data-filter="years"]').forEach(cb => {
            cb.checked = this.selectedYears.includes(parseInt(cb.value));
        });
        
        // Update displays
        this.updateMultiSelectDisplay('years');
        
        // Update available months for current year
        await this.updateAvailableMonths();
        
        // Update month checkboxes to show current month selected
        document.querySelectorAll('[data-filter="months"]').forEach(cb => {
            cb.checked = this.selectedMonths.includes(parseInt(cb.value));
        });
        
        this.updateMultiSelectDisplay('months');
        
        this.closeAllDropdowns();
        
        // Trigger callback
        this.onFilterChange();
    }
    
    getSelectedYears() {
        return this.selectedYears;
    }
    
    getSelectedMonths() {
        // If years selected but no months, return all available months
        if (this.selectedYears.length > 0 && this.selectedMonths.length === 0) {
            if (this.currentAvailableMonths && this.currentAvailableMonths.length > 0) {
                this.selectedMonths = [...this.currentAvailableMonths];
                // Update month checkboxes
                document.querySelectorAll('[data-filter="months"]').forEach(cb => {
                    cb.checked = true;
                });
                this.updateMultiSelectDisplay('months');
            }
        }
        
        return this.selectedMonths;
    }
}