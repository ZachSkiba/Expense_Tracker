// balance-manager.js
class BalanceManager {
    constructor() {
        this.loadBalances();
        this.loadSettlements();
        
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

    async loadSettlements() {
        try {
            const response = await fetch('/api/settlements');
            const data = await response.json();

            if (data.settlements) {
                this.renderSettlements(data.settlements);
            }
        } catch (error) {
            console.error('Error loading settlement suggestions:', error);
            this.renderSettlements([]);
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
            let statusClass = 'balance-even';
            let statusText = 'Even';
            let amountText = '$0.00';

            if (balance.balance > 0.01) {
                statusClass = 'balance-positive';
                statusText = 'Is owed';
                amountText = `+$${balance.balance.toFixed(2)}`;
            } else if (balance.balance < -0.01) {
                statusClass = 'balance-negative';
                statusText = 'Owes';
                amountText = `-$${Math.abs(balance.balance).toFixed(2)}`;
            }

            return `
                <div class="balance-item">
                    <div class="balance-info">
                        <div class="balance-name">${balance.user_name}</div>
                        <div class="balance-status ${statusClass}">${statusText}</div>
                    </div>
                    <div class="balance-amount ${statusClass}">${amountText}</div>
                </div>
            `;
        }).join('');

        container.innerHTML = balanceHTML;
    }

    renderSettlements(settlements) {
        const container = document.getElementById('settlements-container');
        if (!container) return;

        if (!settlements || settlements.length === 0) {
            container.innerHTML = `
                <div class="no-settlements">
                    🎉 All settled! No payments needed.
                </div>
            `;
            return;
        }

        const settlementsHTML = settlements.map(settlement => `
            <div class="settlement-suggestion">
                <span class="settlement-from">${settlement.from}</span> 
                <span class="settlement-arrow">→</span> 
                <span class="settlement-to">${settlement.to}</span>
                <span class="settlement-amount">$${settlement.amount.toFixed(2)}</span>
            </div>
        `).join('');

        container.innerHTML = settlementsHTML;
    }

    // Method to refresh both balances and settlements
    async refresh() {
        await Promise.all([
            this.loadBalances(),
            this.loadSettlements()
        ]);
    }
}

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', function() {
    window.balanceManager = new BalanceManager();
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