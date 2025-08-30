// balance-manager.js - FIXED VERSION (No Auto-Recalculation)
class BalanceManager {
    constructor() {
        this.isInitialized = false;
        this.init();
    }

    async init() {
        if (this.isInitialized) {
            console.log('[DEBUG] BalanceManager already initialized, skipping');
            return;
        }

        console.log('[DEBUG] Initializing BalanceManager...');
        
        await this.loadBalances();
        await this.loadSettlementSuggestions();
        
        this.isInitialized = true;
        
        // Optional: Reload balances every 2 minutes to keep them reasonably fresh
        // but not so often as to cause performance issues
        setInterval(() => {
            if (document.visibilityState === 'visible') {
                this.loadBalances();
                this.loadSettlementSuggestions();
            }
        }, 120000); // 2 minutes
    }

    async loadBalances() {
        try {
            console.log('[DEBUG] BalanceManager: Loading balances...');
            
            // Use READ-ONLY API endpoint that doesn't trigger recalculation
            const response = await fetch('/api/balances');
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
            const data = await response.json();

            if (data.balances) {
                this.renderBalances(data.balances);
                this.updateHeaderStatus(data.balances);
            } else {
                console.warn('[WARNING] No balances data in API response');
                this.renderBalances([]);
            }
        } catch (error) {
            console.error('[ERROR] BalanceManager: Error loading balances:', error);
            this.renderBalances([]);
        }
    }

    async loadSettlementSuggestions() {
        try {
            console.log('[DEBUG] BalanceManager: Loading settlement suggestions...');
            
            // Use READ-ONLY API endpoint for settlement suggestions
            const response = await fetch('/api/settlement-suggestions');
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
            const data = await response.json();

            if (data.suggestions) {
                this.renderSettlementSuggestions(data.suggestions);
            } else {
                console.warn('[WARNING] No settlement suggestions in API response');
                this.renderSettlementSuggestions([]);
            }
        } catch (error) {
            console.error('[ERROR] BalanceManager: Error loading settlement suggestions:', error);
            this.renderSettlementSuggestions([]);
        }
    }

    renderBalances(balances) {
        const container = document.getElementById('balances-container');
        if (!container) {
            console.log('[DEBUG] No balances-container found, skipping balance rendering');
            return;
        }

        if (!balances || balances.length === 0) {
            container.innerHTML = `
                <div style="text-align: center; padding: 20px; color: #7f8c8d;">
                    No balances found
                </div>
            `;
            return;
        }

        console.log('[DEBUG] Rendering balances for', balances.length, 'users');

        const balanceHTML = balances.map(balance => {
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

        container.innerHTML = balanceHTML;
    }

    renderSettlementSuggestions(suggestions) {
        const container = document.getElementById('settlements-container');
        if (!container) {
            console.log('[DEBUG] No settlements-container found, skipping suggestions rendering');
            return;
        }

        if (!suggestions || suggestions.length === 0) {
            container.innerHTML = `
                <div class="no-settlements">
                    🎉 All settled! No payments needed.
                </div>
            `;
            return;
        }

        console.log('[DEBUG] Rendering', suggestions.length, 'settlement suggestions');

        const suggestionsHTML = suggestions.map(suggestion => `
            <div class="settlement-suggestion">
                <span class="settlement-from">${suggestion.from}</span> 
                <span class="settlement-arrow">→</span> 
                <span class="settlement-to">${suggestion.to}</span>
                <span class="settlement-amount">$${suggestion.amount.toFixed(2)}</span>
            </div>
        `).join('');

        container.innerHTML = suggestionsHTML;
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
            statusIndicator.style.background = '#e8f5e8';
            statusIndicator.style.color = '#2d5a2d';
        }
    }

    // Method to manually refresh both balances and settlement suggestions
    async refresh() {
        console.log('[DEBUG] BalanceManager: Manual refresh requested');
        await Promise.all([
            this.loadBalances(),
            this.loadSettlementSuggestions()
        ]);
    }

    // Method to force recalculation on the backend (admin function)
    async forceRecalculation() {
        try {
            console.log('[DEBUG] BalanceManager: Forcing backend recalculation...');
            
            const response = await fetch('/api/balances/recalculate', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                }
            });

            if (response.ok) {
                console.log('[DEBUG] Backend recalculation successful');
                // Refresh data after recalculation
                await this.refresh();
                return true;
            } else {
                throw new Error('Recalculation failed');
            }
        } catch (error) {
            console.error('[ERROR] Failed to force recalculation:', error);
            return false;
        }
    }
}

// Initialize when DOM is ready - but only once
document.addEventListener('DOMContentLoaded', function() {
    if (!window.balanceManager) {
        window.balanceManager = new BalanceManager();
    }
});

// CSS for settlement suggestions
if (!document.getElementById('balance-manager-styles')) {
    const style = document.createElement('style');
    style.id = 'balance-manager-styles';
    style.textContent = `
    .settlement-suggestion {
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding: 8px 12px;
        margin: 4px 0;
        background: #f8f9fa;
        border-radius: 6px;
        border-left: 3px solid #3498db;
    }

    .settlement-from, .settlement-to {
        font-weight: 500;
        color: #2c3e50;
    }

    .settlement-arrow {
        color: #3498db;
        margin: 0 8px;
        font-weight: bold;
    }

    .settlement-amount {
        font-weight: 600;
        color: #27ae60;
        background: white;
        padding: 4px 8px;
        border-radius: 4px;
    }

    .no-settlements {
        text-align: center;
        padding: 20px;
        color: #7f8c8d;
        font-style: italic;
        background: #f8f9fa;
        border-radius: 6px;
        border: 1px dashed #bdc3c7;
    }

    .balance-item.positive .amount {
        color: #27ae60;
    }

    .balance-item.negative .amount {
        color: #e74c3c;
    }

    .balance-item.even .amount {
        color: #7f8c8d;
    }

    .status-indicator.all-even {
        background: #e8f5e8 !important;
        color: #2d5a2d !important;
    }

    .status-indicator.pending {
        background: #fff3cd !important;
        color: #856404 !important;
    }
    `;
    document.head.appendChild(style);
}