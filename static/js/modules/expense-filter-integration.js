// Updated Expense Filter Integration Module - FIXED VERSION
// This module integrates the expense filter with the existing expense table and balance systems

class ExpenseFilterIntegration {
    constructor(options = {}) {
        this.filterManager = null;
        this.onFilterChange = options.onFilterChange || this.handleFilterChange.bind(this);
        this.urls = options.urls || window.urls || {};
        this.usersData = this.loadUsersData();
        
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
            // If filters were cleared, reload original data
            if (filteredData.isCleared) {
                await this.loadOriginalBalancesAndSettlements();
                return;
            }

            // Always update total expenses card and count
            this.updateTotalExpensesCard(filteredData);
            this.updateExpenseCount(filteredData);

            // FIXED: Update balances and settlements if YEAR or MONTH filter is applied
            if (filteredData.dateFilter && (filteredData.dateFilter.year || filteredData.dateFilter.month)) {
                // Fetch settlements data for the exact filtered period only
                const settlementsData = await this.fetchSettlementsData(filteredData.dateFilter);

                // Update recent payments table with settlements from exact period only
                this.updateRecentPaymentsTable(settlementsData);

                // Recalculate and update balances based on filtered expenses AND settlements from exact period
                await this.updateBalancesFromFilteredData(filteredData, settlementsData);

                // Update settlements based on new balances from exact period
                await this.updateSettlementsFromFilteredData(filteredData, settlementsData);
            }

        } catch (error) {
            console.error('[ERROR] Failed to update data after filter change:', error);
        }
    }

    hasMonthFilter(dateFilter) {
        // FIXED: Return true if month is specifically selected (not just year)
        return dateFilter && dateFilter.month;
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
            } else {
                countElement.textContent = `(${total})`;
                countElement.style.background = '#f8f9fa';
                countElement.style.color = '#6c757d';
            }
        }
    }

    async updateBalancesFromFilteredData(filteredData, settlementsData = []) {
        try {
            // FIXED: Use proper balance calculation that includes ALL participants
            const calculatedBalances = this.calculateBalancesFromExpensesAndSettlements(filteredData.expenses, settlementsData);
            
            // Update balances display
            this.updateBalancesDisplay(calculatedBalances, filteredData.dateFilter);
            
            // Update header status
            this.updateHeaderStatus(calculatedBalances);
            
        } catch (error) {
            console.error('[ERROR] Failed to update balances from filtered data:', error);
        }
    }

    async updateSettlementsFromFilteredData(filteredData, settlementsData = []) {
        try {
            // Calculate balances first (including settlements)
            const balances = this.calculateBalancesFromExpensesAndSettlements(filteredData.expenses, settlementsData);
            
            // Calculate settlement suggestions from the net balances
            const suggestions = this.calculateSettlementSuggestions(balances);
            
            // Update settlements display
            this.updateSettlementsDisplay(suggestions, filteredData.dateFilter);
            
        } catch (error) {
            console.error('[ERROR] Failed to update settlements from filtered data:', error);
        }
    }

    // FIXED: Proper balance calculation that includes ALL participants like Aaron
    calculateBalancesFromExpensesAndSettlements(expenses, settlements = []) {
        const balances = {};

        // FIXED: Initialize balances for ALL users from users data (like settlement-manager does)
        // This ensures users like Aaron appear even if they don't pay expenses in filtered period
        this.usersData.forEach(user => {
            balances[user.name] = { user_name: user.name, balance: 0 };
        });

        // Also get any additional participants from expense data
        if (this.filterManager && this.filterManager.originalRows) {
            this.filterManager.originalRows.forEach(row => {
                // Add payer
                if (!balances[row.data.paidBy]) {
                    balances[row.data.paidBy] = { user_name: row.data.paidBy, balance: 0 };
                }

                // Add all participants
                if (row.data.participants && row.data.participants.trim()) {
                    row.data.participants.split(',').forEach(participant => {
                        const participantName = participant.trim();
                        if (participantName && !balances[participantName]) {
                            balances[participantName] = { user_name: participantName, balance: 0 };
                        }
                    });
                }
            });
        }

        // Calculate balances from filtered expenses
        expenses.forEach(expense => {
            const paidBy = expense.paidBy;
            const amount = expense.amount;

            // FIXED: Get participants properly
            let participants = [];
            if (expense.participants && expense.participants.trim()) {
                participants = expense.participants.split(',').map(p => p.trim()).filter(p => p);
            }

            // If no participants, assume the payer is the only participant
            if (participants.length === 0) {
                participants = [paidBy];
            }

            // FIXED: Ensure payer is included in participants (critical for correct balance calculation)
            if (!participants.includes(paidBy)) {
                participants.push(paidBy);
            }

            const sharePerPerson = amount / participants.length;

            // Initialize balances if somehow not exists (safety check)
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

// Process settlements (payments) - same logic as settlement-manager
settlements.forEach(settlement => {
    const payerName = settlement.payer_name;
    const receiverName = settlement.receiver_name;
    const amount = settlement.amount;

    // Initialize balances if not exists (safety check)
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
        return result;
    }

    // Use same logic as balance-manager for rendering
    updateBalancesDisplay(balances, dateFilter) {
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

        // Add filtered indicator ONLY for month filters (not year-only)
        let indicatorHTML = '';
        if (this.hasMonthFilter(dateFilter)) {
            const months = [
                'January', 'February', 'March', 'April', 'May', 'June',
                'July', 'August', 'September', 'October', 'November', 'December'
            ];
            
            let periodText = '';
            if (dateFilter.year && dateFilter.month) {
                periodText = `${months[dateFilter.month - 1]} ${dateFilter.year}`;
            } else if (dateFilter.month) {
                periodText = `${months[dateFilter.month - 1]}`;
            }
            
            indicatorHTML = `
                <div class="filter-indicator" style="
                    background: linear-gradient(135deg, #e3f2fd, #bbdefb);
                    color: #1565c0;
                    padding: 10px 12px;
                    border-radius: 8px;
                    font-size: 0.9rem;
                    font-weight: 600;
                    margin-bottom: 16px;
                    text-align: center;
                    border: 1px solid #90caf9;
                    box-shadow: 0 2px 4px rgba(21, 101, 192, 0.1);
                ">
                    📅 Balances for ${periodText}
                </div>
            `;
        }

        // Use same rendering logic as balance-manager
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
                        <div class="amount">${amount.toFixed(2)}</div>
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

    // Use same settlement calculation logic as settlement-manager
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

    updateSettlementsDisplay(suggestions, dateFilter) {
        console.log('[DEBUG] Updating settlements display with:', suggestions);
        const container = document.getElementById('settlements-container');
        if (!container) {
            console.log('[DEBUG] No settlements container found');
            return;
        }
        
        // Add filtered indicator ONLY for month filters (not year-only)
        let indicatorHTML = '';
        if (this.hasMonthFilter(dateFilter)) {
            const months = [
                'January', 'February', 'March', 'April', 'May', 'June',
                'July', 'August', 'September', 'October', 'November', 'December'
            ];
            
            let periodText = '';
            if (dateFilter.year && dateFilter.month) {
                periodText = `${months[dateFilter.month - 1]} ${dateFilter.year}`;
            } else if (dateFilter.month) {
                periodText = `${months[dateFilter.month - 1]}`;
            }
            
            indicatorHTML = `
                <div class="filter-indicator" style="
                    background: linear-gradient(135deg, #e8f5e8, #c8e6c9);
                    color: #2e7d32;
                    padding: 10px 12px;
                    border-radius: 8px;
                    font-size: 0.9rem;
                    font-weight: 600;
                    margin-bottom: 16px;
                    text-align: center;
                    border: 1px solid #a5d6a7;
                    box-shadow: 0 2px 4px rgba(46, 125, 50, 0.1);
                ">
                    💰 Settlements for ${periodText}
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
                <span class="settlement-amount">${suggestion.amount.toFixed(2)}</span>
            </div>
        `).join('');

        container.innerHTML = indicatorHTML + suggestionItems;
        console.log('[DEBUG] Settlements display updated');
    }

    // FIXED: Update recent payments table with filtered data
    updateRecentPaymentsTable(settlementsData) {
        console.log('[DEBUG] Updating recent payments table with:', settlementsData);
        
        // Find the recent payments table - try multiple selectors
        const paymentsTable = document.querySelector(
            '.settlements-history table tbody, .recent-payments table tbody, .payments-history table tbody, .settlements-table tbody'
        );
        
        if (!paymentsTable) {
            console.log('[DEBUG] No recent payments table found');
            return;
        }

        if (!settlementsData || settlementsData.length === 0) {
            paymentsTable.innerHTML = `
                <tr>
                    <td colspan="5" style="text-align: center; color: #888; padding: 20px;">
                        No payments found for this period
                    </td>
                </tr>
            `;
            return;
        }

        // Sort settlements by date (newest first)
        const sortedSettlements = settlementsData.sort((a, b) => new Date(b.date) - new Date(a.date));

        const rows = sortedSettlements.map(settlement => {
            const date = new Date(settlement.date).toLocaleDateString();
            return `
                <tr>
                    <td>${date}</td>
                    <td>${settlement.payer_name}</td>
                    <td>${settlement.receiver_name}</td>
                    <td>${settlement.amount.toFixed(2)}</td>
                    <td>${settlement.description || '-'}</td>
                </tr>
            `;
        }).join('');

        paymentsTable.innerHTML = rows;
        console.log('[DEBUG] Recent payments table updated with filtered data');
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

    // FIXED: Fetch settlements data for filtered period (exact period only, not cumulative)
    async fetchSettlementsData(dateFilter) {
        try {
            // Fetch all settlements from the API
            const response = await fetch('/api/settlements');
            if (!response.ok) {
                console.warn('[WARN] Could not fetch settlements data');
                return [];
            }

            const data = await response.json();
            let settlements = data.settlements || [];

            // Filter settlements for the exact filtered period only
            if (dateFilter && (dateFilter.year || dateFilter.month)) {
                settlements = settlements.filter(settlement => {
                    const settlementDate = new Date(settlement.date);
                    const settlementYear = settlementDate.getFullYear();
                    const settlementMonth = settlementDate.getMonth() + 1;

                    const filterYear = parseInt(dateFilter.year);
                    const filterMonth = parseInt(dateFilter.month);

                    // Filter for exact period match only
                    if (dateFilter.year && dateFilter.month) {
                        // Both year and month specified: exact month match
                        return settlementYear === filterYear && settlementMonth === filterMonth;
                    } else if (dateFilter.year && !dateFilter.month) {
                        // Only year specified: all months in that year
                        return settlementYear === filterYear;
                    }

                    return true;
                });
            }

            console.log('[DEBUG] Filtered settlements for exact period only:', dateFilter, settlements);
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
            
            // Use the global refresh function if available
            if (window.globalRefreshBalances) {
                await window.globalRefreshBalances();
            } else if (window.balanceManager && typeof window.balanceManager.refresh === 'function') {
                await window.balanceManager.refresh();
            } else {
                // Fallback: fetch balances and settlements directly
                const [balancesResponse, suggestionsResponse] = await Promise.all([
                    fetch('/api/balances'),
                    fetch('/api/settlement-suggestions')
                ]);
                
                if (balancesResponse.ok && suggestionsResponse.ok) {
                    const balancesData = await balancesResponse.json();
                    const suggestionsData = await suggestionsResponse.json();
                    
                    // Update displays
                    this.updateBalancesDisplay(balancesData.balances, null);
                    this.updateSettlementsDisplay(suggestionsData.suggestions, null);
                    this.updateHeaderStatus(balancesData.balances);
                }
            }

            // Also restore original payments table
            const allSettlements = await this.fetchSettlementsData(null); // Get all settlements
            this.updateRecentPaymentsTable(allSettlements);
            
        } catch (error) {
            console.error('[ERROR] Failed to load original balances and settlements:', error);
        }
    }
}

// Export for use in other modules
window.ExpenseFilterIntegration = ExpenseFilterIntegration;