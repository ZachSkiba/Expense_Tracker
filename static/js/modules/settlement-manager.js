// settlement-manager.js
class SettlementManager {
    constructor() {
        this.initializeEventListeners();
        this.loadSettlements();
        
        // Set today's date as default
        const today = new Date().toISOString().split('T')[0];
        const dateInput = document.getElementById('settlement-date');
        if (dateInput) {
            dateInput.value = today;
        }
    }

    initializeEventListeners() {
        // Handle settlement form submission
        const settlementForm = document.getElementById('settlement-form');
        if (settlementForm) {
            settlementForm.addEventListener('submit', (e) => this.handleSettlementSubmit(e));
        }

        // Handle payer/receiver change to prevent same person selection
        const payerSelect = document.getElementById('settlement-payer');
        const receiverSelect = document.getElementById('settlement-receiver');
        
        if (payerSelect && receiverSelect) {
            payerSelect.addEventListener('change', () => this.validatePayerReceiver());
            receiverSelect.addEventListener('change', () => this.validatePayerReceiver());
        }
    }

    validatePayerReceiver() {
        const payerId = document.getElementById('settlement-payer').value;
        const receiverId = document.getElementById('settlement-receiver').value;
        const errorDiv = document.getElementById('settlement-error');

        if (payerId && receiverId && payerId === receiverId) {
            errorDiv.textContent = 'Payer and receiver cannot be the same person';
            errorDiv.style.display = 'block';
            return false;
        } else {
            errorDiv.style.display = 'none';
            return true;
        }
    }

    async handleSettlementSubmit(e) {
        e.preventDefault();
        
        // Validate payer/receiver first
        if (!this.validatePayerReceiver()) {
            return;
        }

        const formData = {
            amount: document.getElementById('settlement-amount').value,
            payer_id: document.getElementById('settlement-payer').value,
            receiver_id: document.getElementById('settlement-receiver').value,
            description: document.getElementById('settlement-description').value,
            date: document.getElementById('settlement-date').value
        };

        try {
            const response = await fetch(window.urls.settlementsApi, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(formData)
            });

            const data = await response.json();

            if (data.success) {
                // Clear form
                document.getElementById('settlement-form').reset();
                
                // Set today's date again
                const today = new Date().toISOString().split('T')[0];
                document.getElementById('settlement-date').value = today;
                
                // Close modal
                closeModal('settleUpModal');
                
                // Reload both settlement history and balance manager
                await this.loadSettlements();
                if (window.balanceManager) {
                    await window.balanceManager.refresh();
                }
                
                // Show success message
                this.showSuccessMessage('Payment recorded successfully!');
            } else {
                this.showError(data.error || 'Failed to record settlement');
            }
        } catch (error) {
            console.error('Error recording settlement:', error);
            this.showError('Network error. Please try again.');
        }
    }

    async loadSettlements() {
        try {
            const response = await fetch(window.urls.getSettlementsApi + '?limit=5');
            const data = await response.json();

            if (data.settlements) {
                this.renderSettlementsTable(data.settlements);
            }
        } catch (error) {
            console.error('Error loading settlements:', error);
            this.renderSettlementsTable([]);
        }
    }

    renderSettlementsTable(settlements) {
        const container = document.getElementById('settlements-table-container');
        if (!container) return;

        if (!settlements || settlements.length === 0) {
            container.innerHTML = `
                <div class="no-settlements">
                    💸 No recent payments
                </div>
            `;
            return;
        }

        const tableHTML = `
            <table class="settlements-table-main">
                <thead>
                    <tr>
                        <th>Amount</th>
                        <th>From</th>
                        <th>To</th>
                        <th>Date</th>
                        <th>Actions</th>
                    </tr>
                </thead>
                <tbody>
                    ${settlements.map(settlement => `
                        <tr data-settlement-id="${settlement.id}">
                            <td class="amount">$${parseFloat(settlement.amount).toFixed(2)}</td>
                            <td>${settlement.payer_name}</td>
                            <td>${settlement.receiver_name}</td>
                            <td class="settlement-date">${settlement.date}</td>
                            <td>
                                <button class="delete-btn" data-settlement-id="${settlement.id}">❌</button>
                            </td>
                        </tr>
                    `).join('')}
                </tbody>
            </table>
        `;

        container.innerHTML = tableHTML;

        // Add delete event listeners
        container.querySelectorAll('.delete-btn').forEach(button => {
            button.addEventListener('click', (e) => {
                e.stopPropagation();
                const settlementId = button.getAttribute('data-settlement-id');
                this.deleteSettlement(settlementId);
            });
        });
    }

    async deleteSettlement(settlementId) {
        if (!confirm('Are you sure you want to delete this payment? This will recalculate all balances.')) {
            return;
        }

        try {
            const response = await fetch(`/delete_settlement/${settlementId}`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                }
            });

            const data = await response.json();

            if (data.success) {
                // Reload settlements and balances
                await this.loadSettlements();
                if (window.balanceManager) {
                    await window.balanceManager.refresh();
                }
                this.showSuccessMessage('Payment deleted successfully');
            } else {
                this.showError(data.error || 'Failed to delete settlement');
            }
        } catch (error) {
            console.error('Error deleting settlement:', error);
            this.showError('Network error. Please try again.');
        }
    }

    showError(message) {
        const errorDiv = document.getElementById('settlement-error');
        if (errorDiv) {
            errorDiv.textContent = message;
            errorDiv.style.display = 'block';
            setTimeout(() => {
                errorDiv.style.display = 'none';
            }, 5000);
        }
    }

    showSuccessMessage(message) {
        // Create a temporary success message
        const successDiv = document.createElement('div');
        successDiv.className = 'success-message';
        successDiv.textContent = message;
        successDiv.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            background: #27ae60;
            color: white;
            padding: 15px 20px;
            border-radius: 5px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.15);
            z-index: 10000;
            font-weight: 500;
        `;
        
        document.body.appendChild(successDiv);
        
        setTimeout(() => {
            successDiv.remove();
        }, 3000);
    }
}

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', function() {
    window.settlementManager = new SettlementManager();
});

// Function to open settle up modal (called by button)
function openSettleUpModal() {
    document.getElementById('settleUpModal').style.display = 'block';
    
    // Set today's date
    const today = new Date().toISOString().split('T')[0];
    document.getElementById('settlement-date').value = today;
}