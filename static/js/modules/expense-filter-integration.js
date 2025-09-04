// Expense Filter Integration Module
// This module integrates the expense filter with the existing expense table and balance systems

class ExpenseFilterIntegration {
    constructor(options = {}) {
        this.filterManager = null;
        this.onFilterChange = options.onFilterChange || this.handleFilterChange.bind(this);
        this.urls = options.urls || window.urls || {};
        
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

    initializeFilter() {
        // Initialize the filter manager
        this.filterManager = new window.ExpenseFilterManager({
            tableSelector: '.expenses-table',
            containerSelector: '.table-wrapper',
            onFilterChange: this.onFilterChange
        });

        // Set up integration with existing systems
        this.setupIntegrations();
    }

    setupIntegrations() {
        // Listen for expense table updates to refresh filters
        document.addEventListener('expenseTableUpdated', () => {
            if (this.filterManager) {
                this.filterManager.refresh();
            }
        });

        // Listen for new expenses added
        document.addEventListener('expenseAdded', () => {
            if (this.filterManager) {
                this.filterManager.refresh();
            }
        });
    }

    async handleFilterChange(filteredData) {
        try {
            console.log('[DEBUG] Filter change triggered with data:', filteredData);
            
            // If filters were cleared, reload original data
            if (filteredData.isCleared) {
                await this.loadOriginalBalancesAndSettlements();
                return;
            }
            
            // Always update total expenses card and count
            this.updateTotalExpensesCard(filteredData);
            this.updateExpenseCount(filteredData);
            
            // Only update balances and settlements if date filter is applied
            const dateRange = this.getFilteredDateRange();
            if (dateRange && (dateRange.year || dateRange.month)) {
                console.log('[DEBUG] Date filter detected, updating balances and settlements for period:', dateRange);
                
                // Fetch settlements data for the filtered period
                const settlementsData = await this.fetchSettlementsData(dateRange);
                
                // Recalculate and update balances based on filtered expenses AND settlements
                await this.updateBalancesFromFilteredData(filteredData, settlementsData);
                
                // Update settlements based on new balances
                await this.updateSettlementsFromFilteredData(filteredData);
            } else {
                console.log('[DEBUG] No date filter applied, keeping original balances and settlements');
            }
            
        } catch (error) {
            console.error('[ERROR] Failed to update data after filter change:', error);
        }
    }

    updateTotalExpensesCard(filteredData) {
        const totalElement = document.getElementById('expenses-total');
        if (totalElement) {
            totalElement.textContent = `$${filteredData.totalAmount.toFixed(2)}`;
            
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
            } else {
                countElement.textContent = `(${total})`;
                countElement.style.background = '#f8f9fa';
                countElement.style.color = '#6c757d';
            }
        }
    }

    async updateBalancesFromFilteredData(filteredData, settlementsData = []) {
        try {
            // Calculate balances based on filtered expenses AND settlements
            const calculatedBalances = this.calculateBalancesFromExpensesAndSettlements(filteredData.expenses, settlementsData);
            
            // Update balances display
            this.updateBalancesDisplay(calculatedBalances);
            
            // Update header status
            this.updateHeaderStatus(calculatedBalances);
            
        } catch (error) {
            console.error('[ERROR] Failed to update balances from filtered data:', error);
        }
    }

    calculateBalancesFromExpensesAndSettlements(expenses, settlements = []) {
        console.log('[DEBUG] Calculating balances from expenses and settlements:', { expenses, settlements });
        const balances = {};
        
        // Initialize balances for all users
        if (this.filterManager && this.filterManager.originalRows) {
            const allUsers = [...new Set(this.filterManager.originalRows.map(row => row.data.paidBy))];
            allUsers.forEach(user => {
                balances[user] = { user_name: user, balance: 0 };
            });
        }

        // Calculate balances from filtered expenses
        expenses.forEach(expense => {
            console.log('[DEBUG] Processing expense:', expense);
            const paidBy = expense.paidBy;
            const amount = expense.amount;
            
            // Get participants - handle both participant names and IDs
            let participants = [];
            if (expense.participants && expense.participants.trim()) {
                participants = expense.participants.split(',').map(p => p.trim()).filter(p => p);
            }
            
            // If no participants, assume the payer is the only participant
            if (participants.length === 0) {
                participants = [paidBy];
            }
            
            console.log('[DEBUG] Participants for expense:', participants);
            
            const sharePerPerson = amount / participants.length;
            
            // Initialize balances if not exists
            if (!balances[paidBy]) {
                balances[paidBy] = { user_name: paidBy, balance: 0 };
            }
            
            participants.forEach(participant => {
                if (!balances[participant]) {
                    balances[participant] = { user_name: participant, balance: 0 };
                }
            });
            
            // Payer gets credited the full amount
            balances[paidBy].balance += amount;
            
            // Each participant (including payer) gets debited their share
            participants.forEach(participant => {
                balances[participant].balance -= sharePerPerson;
            });
        });

        // Process settlements (payments)
        settlements.forEach(settlement => {
            console.log('[DEBUG] Processing settlement:', settlement);
            const payerName = settlement.payer_name;
            const receiverName = settlement.receiver_name;
            const amount = settlement.amount;
            
            // Initialize balances if not exists
            if (!balances[payerName]) {
                balances[payerName] = { user_name: payerName, balance: 0 };
            }
            if (!balances[receiverName]) {
                balances[receiverName] = { user_name: receiverName, balance: 0 };
            }
            
            // Settlement logic: payer owes less (+), receiver is owed less (-)
            balances[payerName].balance += amount;
            balances[receiverName].balance -= amount;
        });

        const result = Object.values(balances);
        console.log('[DEBUG] Final calculated balances with settlements:', result);
        return result;
    }

    updateBalancesDisplay(balances) {
        console.log('[DEBUG] Updating balances display with:', balances);
        const container = document.getElementById('balances-container');
        if (!container) {
            console.log('[DEBUG] No balances container found');
            return;
        }
        
        if (!balances || balances.length === 0) {
            container.innerHTML = '<div style="text-align: center; padding: 20px; color: #7f8c8d;">No balance data for filtered expenses</div>';
            return;
        }

        // Add filtered indicator first
        const isFiltered = this.filterManager && 
                          this.filterManager.filteredRows.length < this.filterManager.originalRows.length;
        
        let indicatorHTML = '';
        if (isFiltered) {
            indicatorHTML = `
                <div class="filter-indicator" style="
                    background: #fff3cd;
                    color: #856404;
                    padding: 8px 12px;
                    border-radius: 6px;
                    font-size: 0.85rem;
                    margin-bottom: 12px;
                    text-align: center;
                    border: 1px solid #ffeaa7;
                ">
                    📊 Showing balances for filtered expenses only
                </div>
            `;
        }

        const balanceItems = balances.map(balance => {
            const initial = balance.user_name.charAt(0).toUpperCase();
            const status = balance.balance > 0.01 ? 'positive' : balance.balance < -0.01 ? 'negative' : 'even';
            const statusText = balance.balance > 0.01 ? 'owed' : balance.balance < -0.01 ? 'owes' : 'even';
            const amount = Math.abs(balance.balance);

            return `
                <div class="balance-item ${status}">
                    <div class="user-info">
                        <div class="user-avatar">${initial}</div>
                        <div>
                            <div class="user-name">${balance.user_name}</div>
                        </div>
                    </div>
                    <div class="balance-amount">
                        <div class="amount">$${amount.toFixed(2)}</div>
                        <div class="status">${statusText}</div>
                    </div>
                </div>
            `;
        }).join('');

        container.innerHTML = indicatorHTML + balanceItems;
        console.log('[DEBUG] Balances display updated');
    }

    updateHeaderStatus(balances) {
        const statusIndicator = document.querySelector('.status-indicator');
        if (!statusIndicator) return;

        const hasImbalances = balances.some(b => Math.abs(b.balance) > 0.01);
        
        if (hasImbalances) {
            statusIndicator.textContent = 'Pending Settlements';
            statusIndicator.className = 'status-indicator pending';
            statusIndicator.style.background = '#fff3cd';
            statusIndicator.style.color = '#856404';
        } else {
            statusIndicator.textContent = 'All Even';
            statusIndicator.className = 'status-indicator all-even';
        }
    }

    async updateSettlementsFromFilteredData(filteredData) {
        try {
            // Calculate balances first
            const balances = this.calculateBalancesFromExpenses(filteredData.expenses);
            
            // Calculate settlement suggestions
            const suggestions = this.calculateSettlementSuggestions(balances);
            
            // Update settlements display
            this.updateSettlementsDisplay(suggestions);
            
        } catch (error) {
            console.error('[ERROR] Failed to update settlements from filtered data:', error);
        }
    }

    calculateSettlementSuggestions(balances) {
        const suggestions = [];
        
        // Separate creditors (positive balance) and debtors (negative balance)
        const creditors = balances.filter(b => b.balance > 0.01).sort((a, b) => b.balance - a.balance);
        const debtors = balances.filter(b => b.balance < -0.01).sort((a, b) => a.balance - b.balance);
        
        // Create copies to avoid modifying original data
        const creditorsQueue = creditors.map(c => ({ ...c }));
        const debtorsQueue = debtors.map(d => ({ ...d, balance: Math.abs(d.balance) }));
        
        while (creditorsQueue.length > 0 && debtorsQueue.length > 0) {
            const creditor = creditorsQueue[0];
            const debtor = debtorsQueue[0];
            
            const amount = Math.min(creditor.balance, debtor.balance);
            
            if (amount > 0.01) {
                suggestions.push({
                    from: debtor.user_name,
                    to: creditor.user_name,
                    amount: amount
                });
            }
            
            creditor.balance -= amount;
            debtor.balance -= amount;
            
            if (creditor.balance <= 0.01) {
                creditorsQueue.shift();
            }
            if (debtor.balance <= 0.01) {
                debtorsQueue.shift();
            }
        }
        
        return suggestions;
    }

    updateSettlementsDisplay(suggestions) {
        console.log('[DEBUG] Updating settlements display with:', suggestions);
        const container = document.getElementById('settlements-container');
        if (!container) {
            console.log('[DEBUG] No settlements container found');
            return;
        }
        
        // Add filtered indicator first
        const isFiltered = this.filterManager && 
                          this.filterManager.filteredRows.length < this.filterManager.originalRows.length;
        
        let indicatorHTML = '';
        if (isFiltered) {
            indicatorHTML = `
                <div class="filter-indicator" style="
                    background: #fff3cd;
                    color: #856404;
                    padding: 8px 12px;
                    border-radius: 6px;
                    font-size: 0.85rem;
                    margin-bottom: 12px;
                    text-align: center;
                    border: 1px solid #ffeaa7;
                ">
                    📊 Showing settlements for filtered expenses only
                </div>
            `;
        }
        
        if (!suggestions || suggestions.length === 0) {
            container.innerHTML = indicatorHTML + '<div class="no-settlements">🎉 All settled! No payments needed.</div>';
            return;
        }

        const suggestionItems = suggestions.map(suggestion => `
            <div class="settlement-item">
                <strong>${suggestion.from}</strong> should pay <strong>${suggestion.to}</strong> 
                <span class="settlement-amount">$${suggestion.amount.toFixed(2)}</span>
            </div>
        `).join('');

        container.innerHTML = indicatorHTML + suggestionItems;
        console.log('[DEBUG] Settlements display updated');
    }

    // Public method to get current filter state
    getFilterState() {
        return this.filterManager ? this.filterManager.filters : null;
    }

    // Public method to clear all filters
    async clearFilters() {
        if (this.filterManager) {
            this.filterManager.clearAllFilters();
            // Reload original balances and settlements when filters are cleared
            await this.loadOriginalBalancesAndSettlements();
        }
    }

    // Public method to refresh the entire system
    refresh() {
        if (this.filterManager) {
            this.filterManager.refresh();
        }
    }

    // Get filtered date range for settlements
    getFilteredDateRange() {
        if (!this.filterManager || !this.filterManager.filters.dateFilter) {
            return null;
        }
        
        const { year, month } = this.filterManager.filters.dateFilter;
        return { year, month };
    }

    // Fetch settlements data for filtered period
    async fetchSettlementsData(dateRange) {
        try {
            // Fetch all settlements from the API
            const response = await fetch('/api/settlements');
            if (!response.ok) {
                console.warn('[WARN] Could not fetch settlements data');
                return [];
            }

            const data = await response.json();
            let settlements = data.settlements || [];

            // Filter settlements by date range if specified
            if (dateRange && (dateRange.year || dateRange.month)) {
                settlements = settlements.filter(settlement => {
                    const settlementDate = new Date(settlement.date);
                    const settlementYear = settlementDate.getFullYear();
                    const settlementMonth = settlementDate.getMonth() + 1;

                    let yearMatch = true;
                    let monthMatch = true;

                    if (dateRange.year) {
                        yearMatch = settlementYear === parseInt(dateRange.year);
                    }

                    if (dateRange.month) {
                        monthMatch = settlementMonth === parseInt(dateRange.month);
                    }

                    return yearMatch && monthMatch;
                });
            }

            console.log('[DEBUG] Filtered settlements for date range:', dateRange, settlements);
            return settlements;

        } catch (error) {
            console.error('[ERROR] Failed to fetch settlements data:', error);
            return [];
        }
    }

    // Load original balances and settlements (when filters are cleared)
    async loadOriginalBalancesAndSettlements() {
        try {
            console.log('[DEBUG] Loading original balances and settlements');
            
            // Use the same function from main.js to load balances
            if (window.globalRefreshBalances) {
                await window.globalRefreshBalances();
            } else {
                // Fallback: fetch balances and settlements directly
                const [balancesResponse, suggestionsResponse] = await Promise.all([
                    fetch('/api/balances'),
                    fetch('/api/settlement-suggestions')
                ]);
                
                if (balancesResponse.ok && suggestionsResponse.ok) {
                    const balancesData = await balancesResponse.json();
                    const suggestionsData = await suggestionsResponse.json();
                    
                    // Update displays using the functions from main.js
                    if (window.updateBalancesDisplay) {
                        window.updateBalancesDisplay(balancesData.balances);
                    }
                    if (window.updateSettlementSuggestionsDisplay) {
                        window.updateSettlementSuggestionsDisplay(suggestionsData.suggestions);
                    }
                    if (window.updateHeaderStatus) {
                        window.updateHeaderStatus(balancesData.balances);
                    }
                }
            }
            
        } catch (error) {
            console.error('[ERROR] Failed to load original balances and settlements:', error);
        }
    }
}

// Export for use in other modules
window.ExpenseFilterIntegration = ExpenseFilterIntegration;
