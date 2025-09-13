// Updated Expense Filter Integration Module
// This module integrates the expense filter with the existing expense table and balance systems

class ExpenseFilterIntegration {
    constructor(options = {}) {
        this.filterManager = null;
        this.onFilterChange = options.onFilterChange || this.handleFilterChange.bind(this);
        this.urls = options.urls || window.urls || {};
        this.usersData = this.loadUsersData();
        this.originalPaymentsHTML = null; // Store original payments table HTML
        this.currentFilter = null; // Store current filter state
        
        // Listen for payments table updates
        document.addEventListener('paymentAdded', () => {
            // Wait a moment for the table to be updated
            setTimeout(() => {
                this.storeOriginalPaymentsTable();
                if (this.currentFilter) {
                    this.handleFilterChange(this.currentFilter);
                }
            }, 100);
        });
        
        document.addEventListener('paymentDeleted', () => {
            // Wait a moment for the table to be updated
            setTimeout(() => {
                this.storeOriginalPaymentsTable();
                if (this.currentFilter) {
                    this.handleFilterChange(this.currentFilter);
                }
            }, 100);
        });
        
        document.addEventListener('paymentUpdated', () => {
            // Wait a moment for the table to be updated
            setTimeout(() => {
                this.storeOriginalPaymentsTable();
                if (this.currentFilter) {
                    this.handleFilterChange(this.currentFilter);
                }
            }, 100);
        });
        
        // Listen for expense deletions to refresh filter cache
        document.addEventListener('expenseDeleted', (event) => {
            console.log('[DEBUG] ExpenseFilterIntegration received expenseDeleted event', event.detail);
            // The ExpenseTableManager already handles updating the filter cache,
            // but we need to refresh our stored payments table too
            setTimeout(() => {
                this.storeOriginalPaymentsTable();
                if (this.currentFilter) {
                    this.handleFilterChange(this.currentFilter);
                }
            }, 100);
        });
        
        this.init();
    }

    init() {
        // Wait for DOM to be ready and other managers to be initialized
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', () => this.initializeFilter());
        } else {
            this.initializeFilter();
        }
    }

    loadUsersData() {
        const usersScript = document.getElementById('users-data');
        if (usersScript) {
            try {
                return JSON.parse(usersScript.textContent || '[]');
            } catch (e) {
                console.error('Error parsing users data:', e);
                return [];
            }
        }
        return [];
    }

    initializeFilter() {
        // Store original payments table HTML before any filtering
        this.storeOriginalPaymentsTable();
        
        // Initialize the filter manager
        this.filterManager = new window.ExpenseFilterManager({
            tableSelector: '.expenses-table',
            containerSelector: '.table-wrapper',
            onFilterChange: this.onFilterChange
        });

        // Set up integration with existing systems
        this.setupIntegrations();
    }

    storeOriginalPaymentsTable() {
        // Try each possible table container first
        const containers = [
            document.querySelector('.settlements-history'),
            document.querySelector('.recent-payments'),
            document.querySelector('.payments-history'),
            document.querySelector('.settlements-table-container')
        ];

        // Find the first container that exists and has a tbody
        let paymentsTable = null;
        for (const container of containers) {
            if (container) {
                const tbody = container.querySelector('table tbody');
                if (tbody) {
                    paymentsTable = tbody;
                    break;
                }
            }
        }
        
        if (paymentsTable) {
            this.originalPaymentsHTML = paymentsTable.innerHTML;
            console.log('[DEBUG] Stored original payments table HTML from', paymentsTable.closest('div').className);
            this.paymentsTableSelector = this.getTableSelector(paymentsTable);
        } else {
            console.log('[DEBUG] No payments table found in any container');
        }
    }

    getTableSelector(tbody) {
        // Get the container class to ensure we find the same table later
        const container = tbody.closest('div');
        if (container) {
            return `${container.className} table tbody`;
        }
        return null;
    }

    setupIntegrations() {
        // Listen for expense table updates to refresh filters
        document.addEventListener('expenseTableUpdated', () => {
            if (this.filterManager) {
                // Store the original payments table again
                this.storeOriginalPaymentsTable();
                // Refresh and maintain current filter
                this.filterManager.refresh();
                if (this.currentFilter) {
                    this.handleFilterChange(this.currentFilter);
                }
            }
        });

        // Listen for new expenses added
        document.addEventListener('expenseAdded', () => {
            if (this.filterManager) {
                // Store the original payments table again
                this.storeOriginalPaymentsTable();
                // Refresh and maintain current filter
                this.filterManager.refresh();
                if (this.currentFilter) {
                    this.handleFilterChange(this.currentFilter);
                }
            }
        });
    }

    async handleFilterChange(filteredData) {
        try {
            console.log('[DEBUG] === HANDLEFILTERCHANGE START ===');
            console.log('[DEBUG] Filtered data:', filteredData);
            
            // Store the current filter
            this.currentFilter = filteredData;
            
            // Update total expenses card and count
            this.updateTotalExpensesCard(filteredData);
            this.updateExpenseCount(filteredData);
            
            // Try to initialize the payments table if not already done
            if (!this.originalPaymentsHTML) {
                const tableContainer = document.getElementById('settlements-table-container');
                if (tableContainer) {
                    const tbody = tableContainer.querySelector('table tbody');
                    if (tbody && tbody.children.length > 0) {
                        this.originalPaymentsHTML = tbody.innerHTML;
                        console.log('[DEBUG] Late initialization: stored original payments table HTML');
                    }
                }
            }

            // Now try to filter the payments table
            if (filteredData.dateFilter) {
                const tableContainer = document.getElementById('settlements-table-container');
                const tbody = tableContainer?.querySelector('table tbody');
                
                if (tbody && this.originalPaymentsHTML) {
                    console.log('[DEBUG] Found payments table, applying filter...');
                    console.log('[DEBUG] Filter state:', JSON.stringify(filteredData.dateFilter));
                    if (filteredData.isCleared) {
                        tbody.innerHTML = this.originalPaymentsHTML;
                        console.log('[DEBUG] Reset payments table to original content');
                    } else {
                        const tempDiv = document.createElement('div');
                        tempDiv.innerHTML = `<table><tbody>${this.originalPaymentsHTML}</tbody></table>`;
                        const allRows = Array.from(tempDiv.querySelectorAll('tr'));
                        
                        console.log('[DEBUG] Processing', allRows.length, 'payment rows');
                        
                        const filteredRows = allRows.filter(row => {
                            // Skip the "no data" row if present
                            if (row.querySelector('.no-data')) {
                                console.log('[DEBUG] Skipping no-data row');
                                return false;
                            }
                            
                            // Get the date cell (it's either the 4th or 5th cell depending on compact mode)
                            const isCompact = document.querySelector('.settlements-history.compact-mode') !== null;
                            const dateCellIndex = isCompact ? 3 : 4;
                            const dateCell = row.cells?.[dateCellIndex];
                            
                            if (!dateCell) {
                                console.log('[DEBUG] No date cell found in row:', row.innerHTML);
                                return false;
                            }
                            
                            // Try to get date from data-value first, then fallback to text content
                            const dateText = dateCell.getAttribute('data-value') || dateCell.textContent.trim();
                            if (!dateText) {
                                console.log('[DEBUG] Empty date text in cell');
                                return false;
                            }
                            
                            console.log('[DEBUG] Processing row date:', dateText);
                            
                            // Parse date in YYYY-MM-DD format
                            const dateParts = dateText.split('-');
                            if (dateParts.length < 2) {
                                console.log('[DEBUG] Invalid date format:', dateText);
                                return false;
                            }
                            
                            const rowYear = parseInt(dateParts[0]);
                            const rowMonth = parseInt(dateParts[1]);
                            
                            console.log(`[DEBUG] Parsed date: year=${rowYear}, month=${rowMonth}`);
                            console.log(`[DEBUG] Filter: year=${filteredData.dateFilter?.year}, month=${filteredData.dateFilter?.month}`);
                            
                            if (filteredData.dateFilter?.year && filteredData.dateFilter?.month) {
                                const yearMatch = rowYear === parseInt(filteredData.dateFilter.year);
                                const monthMatch = rowMonth === parseInt(filteredData.dateFilter.month);
                                console.log(`[DEBUG] Match check: year=${yearMatch}, month=${monthMatch}`);
                                return yearMatch && monthMatch;
                            } else if (filteredData.dateFilter?.year) {
                                return rowYear === parseInt(filteredData.dateFilter.year);
                            } else if (filteredData.dateFilter?.month) {
                                return rowMonth === parseInt(filteredData.dateFilter.month);
                            }
                            return true;
                        });
                        
                        if (filteredRows.length === 0) {
                            tbody.innerHTML = `<tr><td colspan="5" class="no-data">No payments found for this period</td></tr>`;
                        } else {
                            tbody.innerHTML = filteredRows.map(row => row.outerHTML).join('');
                        }
                        console.log(`[DEBUG] Filtered payments table: ${filteredRows.length} rows shown`);
                    }
                } else {
                    console.log('[DEBUG] Could not find payments table or no original content stored');
                }
            }
            
            // Re-attach event listeners for editable cells after filtering
            this.reattachEditableListeners();

        } catch (error) {
            console.error('[ERROR] Failed to update data after filter change:', error);
        }
    }

    reattachEditableListeners() {
        // Re-initialize the expense table manager for the filtered rows
        if (window.expenseTableManager) {
            // Setup editable cells for the filtered rows
            window.expenseTableManager.setupEditableCells();
            window.expenseTableManager.setupDeleteButtons();
        } else if (window.ExpenseTableManager) {
            // Create a new instance if needed
            const tableManager = new window.ExpenseTableManager({
                tableSelector: '.expenses-table',
                errorSelector: '#table-error',
                urls: this.urls
            });
            window.expenseTableManager = tableManager;
        }

        // Re-initialize the settlements table manager for the filtered rows
        if (window.combinedPageManager) {
            window.combinedPageManager.initializeTableEditing();
            window.combinedPageManager.initializeDeleteButtons();
        } else if (window.CombinedPageManager) {
            // Create a new instance if needed
            const pageManager = new window.CombinedPageManager();
            window.combinedPageManager = pageManager;
        }
        
        console.log('[DEBUG] Re-attached editable listeners to filtered rows');
    }
    
    // Method to reapply current filter
    reapplyFilter() {
        if (this.currentFilter) {
            console.log('[DEBUG] Reapplying current filter after table update');
            this.handleFilterChange(this.currentFilter);
        }
    }

    filterRecentPaymentsTable(dateFilter, isCleared) {
        console.log('[DEBUG] Filtering recent payments table:', dateFilter, isCleared);
        
        // Use the stored selector to find the same table
        if (!this.paymentsTableSelector || !this.originalPaymentsHTML) {
            console.log('[DEBUG] No table selector or original HTML stored');
            return;
        }
        
        const paymentsTable = document.querySelector(this.paymentsTableSelector);
        if (!paymentsTable) {
            console.log('[DEBUG] Could not find payments table with selector:', this.paymentsTableSelector);
            return;
        }
        
        console.log('[DEBUG] Found payments table, applying filter');

        // If filters are cleared or no date filter is active, restore original table
        if (isCleared || (!dateFilter || (!dateFilter.year && !dateFilter.month))) {
            paymentsTable.innerHTML = this.originalPaymentsHTML;
            console.log('[DEBUG] Restored original payments table');
            return;
        }
        
        console.log('[DEBUG] Applying date filter to payments:', dateFilter);

        // Get all rows from the original HTML
        const tempDiv = document.createElement('div');
        tempDiv.innerHTML = `<table><tbody>${this.originalPaymentsHTML}</tbody></table>`;
        const allRows = Array.from(tempDiv.querySelectorAll('tr'));
        
        // Filter rows based on date
        const filteredRows = allRows.filter(row => {
            const dateCell = row.querySelector('td:first-child');
            if (!dateCell) return false;
            
            const dateText = dateCell.textContent.trim();
            if (!dateText || dateText === 'No payments found for this period') return false;
            
            // Parse the date - format should be YYYY-MM-DD
            const dateParts = dateText.split('-');
            if (dateParts.length !== 3) return false;
            
            const rowYear = parseInt(dateParts[0]);
            const rowMonth = parseInt(dateParts[1]); // This is already 1-based (1-12)
            
            console.log(`[DEBUG] Row date: ${dateText} (year: ${rowYear}, month: ${rowMonth})`);
            console.log(`[DEBUG] Filter: year: ${dateFilter.year}, month: ${dateFilter.month}`);
            
            if (dateFilter.year && dateFilter.month) {
                const filterYear = parseInt(dateFilter.year);
                const filterMonth = parseInt(dateFilter.month);
                console.log(`[DEBUG] Comparing ${rowYear}-${rowMonth} with ${filterYear}-${filterMonth}`);
                return rowYear === filterYear && rowMonth === filterMonth;
            } else if (dateFilter.year) {
                return rowYear === parseInt(dateFilter.year);
            } else if (dateFilter.month) {
                return rowMonth === parseInt(dateFilter.month);
            }
            
            return true;
        });

        // Update the table with filtered rows
        if (filteredRows.length === 0) {
            paymentsTable.innerHTML = `
                <tr>
                    <td colspan="5" style="text-align: center; color: #888; padding: 20px;">
                        No payments found for the filtered period
                    </td>
                </tr>
            `;
        } else {
            paymentsTable.innerHTML = filteredRows.map(row => row.outerHTML).join('');
        }
        
        console.log(`[DEBUG] Filtered payments: ${filteredRows.length} rows shown`);
    }

    updateTotalExpensesCard(filteredData) {
        const totalElement = document.getElementById('expenses-total');
        if (totalElement) {
            totalElement.textContent = `${filteredData.totalAmount.toFixed(2)}`;
            
            // Add visual indicator that this is filtered data
            if (filteredData.count < this.filterManager.originalRows.length) {
                totalElement.style.background = 'linear-gradient(135deg, #f39c12, #e67e22)';
                totalElement.title = `Filtered total (${filteredData.count} of ${this.filterManager.originalRows.length} expenses)`;
            } else {
                totalElement.style.background = 'linear-gradient(135deg, #27ae60, #2ecc71)';
                totalElement.title = 'Total of all expenses';
            }
        }
    }

    updateExpenseCount(filteredData) {
        const countElement = document.querySelector('.expense-count');
        if (countElement) {
            const total = this.filterManager.originalRows.length;
            const filtered = filteredData.count;
            
            if (filtered < total) {
                countElement.textContent = `(${filtered} of ${total})`;
                countElement.style.background = '#fff3cd';
                countElement.style.color = '#856404';
                countElement.style.padding = '2px 6px';
                countElement.style.borderRadius = '3px';
            } else {
                countElement.textContent = `(${total})`;
                countElement.style.background = '#f8f9fa';
                countElement.style.color = '#6c757d';
                countElement.style.padding = '2px 6px';
                countElement.style.borderRadius = '3px';
            }
        }
    }

    // Public method to get current filter state
    getFilterState() {
        return this.filterManager ? this.filterManager.filters : null;
    }

    // Public method to clear all filters
    async clearFilters() {
        if (this.filterManager) {
            console.log('[DEBUG] Clearing all filters');
            this.currentFilter = null;
            this.filterManager.clearAllFilters();
            
            // Get fresh copy of payments table
            const tableContainer = document.getElementById('settlements-table-container');
            const tbody = tableContainer?.querySelector('table tbody');
            if (tbody) {
                // Update our stored original HTML before resetting
                this.storeOriginalPaymentsTable();
                tbody.innerHTML = this.originalPaymentsHTML;
                console.log('[DEBUG] Reset payments table to original content');
            }
            
            // Make sure the filter UI is reset too
            const yearSelect = document.querySelector('select[name="year"]');
            const monthSelect = document.querySelector('select[name="month"]');
            if (yearSelect) yearSelect.value = '';
            if (monthSelect) monthSelect.value = '';
        }
    }

    // Store the original payments table HTML
    storeOriginalPaymentsTable() {
        const tableContainer = document.getElementById('settlements-table-container');
        if (tableContainer) {
            const tbody = tableContainer.querySelector('table tbody');
            if (tbody) {
                // For empty tables, store the "no payments" message
                if (tbody.children.length === 0) {
                    this.originalPaymentsHTML = `<tr><td colspan="5" class="no-data">No payments found for this period</td></tr>`;
                } else {
                    this.originalPaymentsHTML = tbody.innerHTML;
                }
                console.log('[DEBUG] Stored original payments table HTML, rows:', tbody.children.length);
            }
        }
    }

    // Public method to refresh the entire system
    refresh() {
        if (this.filterManager) {
            // Store the original payments table again before refresh
            this.storeOriginalPaymentsTable();
            // If we have an active filter, reapply it
            if (this.currentFilter && !this.currentFilter.isCleared) {
                this.handleFilterChange(this.currentFilter);
            }
            this.filterManager.refresh();
        }
    }
}

// Export for use in other modules
window.ExpenseFilterIntegration = ExpenseFilterIntegration;