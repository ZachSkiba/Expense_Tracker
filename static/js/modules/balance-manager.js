// balance-manager.js - FIXED VERSION
class BalanceManager {
    constructor() {
        this.loadBalances();
        this.loadSettlementSuggestions(); // Load suggestions for "who should pay whom"
        
        // Reload balances every 30 seconds to keep them fresh
        setInterval(() => this.loadBalances(), 30000);
    }

    async loadBalances() {
        try {
            const response = await fetch('/api/balances');
            const data = await response.json();

            if (data.balances) {
                this.renderBalances(data.balances);
            }
        } catch (error) {
            console.error('Error loading balances:', error);
            this.renderBalances([]);
        }
    }

    async loadSettlementSuggestions() {
        try {
            // Use the correct endpoint for settlement suggestions
            const response = await fetch('/api/settlement-suggestions');
            const data = await response.json();

            if (data.suggestions) {
                this.renderSettlementSuggestions(data.suggestions);
            }
        } catch (error) {
            console.error('Error loading settlement suggestions:', error);
            this.renderSettlementSuggestions([]);
        }
    }

    renderBalances(balances) {
        const container = document.getElementById('balances-container');
        if (!container) return;

        if (!balances || balances.length === 0) {
            container.innerHTML = `
                <div style="text-align: center; padding: 20px; color: #7f8c8d;">
                    No balances found
                </div>
            `;
            return;
        }

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
        if (!container) return;

        if (!suggestions || suggestions.length === 0) {
            container.innerHTML = `
                <div class="no-settlements">
                    🎉 All settled! No payments needed.
                </div>
            `;
            return;
        }

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

    // Method to refresh both balances and settlement suggestions
    async refresh() {
        await Promise.all([
            this.loadBalances(),
            this.loadSettlementSuggestions()
        ]);
    }
}

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', function() {
    if (!window.balanceManager) {
        window.balanceManager = new BalanceManager();
    }
});

// CSS for settlement suggestions to fix spacing
const style = document.createElement('style');
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
`;
document.head.appendChild(style);