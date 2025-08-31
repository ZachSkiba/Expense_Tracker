// settlement-manager.js - UPDATED VERSION (Immediate balance updates after edits)
class SettlementManager {
    constructor() {
        this.usersData = this.loadUsersData();
        this.isEditing = false; // Prevent multiple simultaneous edits
        this.editingCell = null; // Track which cell is being edited
        this.initializeEventListeners();
        this.loadActualSettlements();
        
        // Set today's date as default
        const today = new Date().toISOString().split('T')[0];
        const dateInput = document.getElementById('settlement-date');
        if (dateInput) {
            dateInput.value = today;
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
            if (errorDiv) {
                errorDiv.textContent = 'Payer and receiver cannot be the same person';
                errorDiv.style.display = 'block';
            }
            return false;
        } else {
            if (errorDiv) {
                errorDiv.style.display = 'none';
            }
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
            const response = await fetch('/api/settlements', {
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
                if (typeof closeModal === 'function') {
                    closeModal('settleUpModal');
                }
                
                // **KEY FIX**: Refresh all data immediately after new settlement
                console.log('[DEBUG] New settlement created, refreshing all data...');
                await this.refreshAllDataImmediate();
                
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

    async loadActualSettlements() {
        try {
            const response = await fetch('/api/settlements?limit=10');
            const data = await response.json();

            console.log('Loaded settlement data:', data);

            if (data.settlements) {
                this.renderSettlementsTable(data.settlements);
            } else {
                console.error('No settlements data in response:', data);
                this.renderSettlementsTable([]);
            }
        } catch (error) {
            console.error('Error loading settlements:', error);
            this.renderSettlementsTable([]);
        }
    }

    renderSettlementsTable(settlements) {
        const container = document.getElementById('settlements-table-container');
        if (!container) return;

        const isCompact = container.closest('.compact-mode') !== null;

        if (!settlements || settlements.length === 0) {
            container.innerHTML = `
                <div class="no-settlements">
                    💸 No recent payments
                </div>
            `;
            return;
        }

        const tableHTML = `
            <div id="table-error" style="display: none;"></div>
            <table class="settlements-table-main">
                <thead>
                    <tr>
                        <th>Amount</th>
                        <th>From</th>
                        <th>To</th>
                        ${!isCompact ? '<th>Description</th>' : ''}
                        <th>Date</th>
                        <th>Actions</th>
                    </tr>
                </thead>
                <tbody>
                    ${settlements.map(settlement => `
                        <tr data-settlement-id="${settlement.id}">
                            <td class="editable amount" data-field="amount" data-value="${settlement.amount}">
                                $${parseFloat(settlement.amount).toFixed(2)}
                            </td>
                            <td class="editable payer" data-field="payer" data-value="${settlement.payer_name}">
                                ${settlement.payer_name}
                            </td>
                            <td class="editable receiver" data-field="receiver" data-value="${settlement.receiver_name}">
                                ${settlement.receiver_name}
                            </td>
                            ${!isCompact ? `
                            <td class="editable description" data-field="description" data-value="${settlement.description || ''}">
                                ${settlement.description || '-'}
                            </td>` : ''}
                            <td class="editable date settlement-date" data-field="date" data-value="${settlement.date}">
                                ${settlement.date}
                            </td>
                            <td>
                                <button class="delete-btn" data-settlement-id="${settlement.id}">❌</button>
                            </td>
                        </tr>
                    `).join('')}
                </tbody>
            </table>
        `;

        container.innerHTML = tableHTML;
        this.attachEventListeners(container);
    }

    attachEventListeners(container) {
        // Add delete event listeners
        container.querySelectorAll('.delete-btn').forEach(button => {
            button.addEventListener('click', (e) => {
                e.stopPropagation();
                const settlementId = button.getAttribute('data-settlement-id');
                this.deleteSettlement(settlementId);
            });
        });

        // Add editing event listeners
        container.querySelectorAll('.editable').forEach(cell => {
            cell.addEventListener('click', (e) => {
                e.stopPropagation();
                this.startEditing(cell);
            });
        });
    }

    startEditing(cell) {
        // Prevent multiple simultaneous edits
        if (this.isEditing) {
            return;
        }

        this.isEditing = true;
        this.editingCell = cell;
        
        const currentValue = cell.getAttribute('data-value') || '';
        const fieldType = cell.getAttribute('data-field');
        
        console.log(`[DEBUG] Starting edit for ${fieldType}: ${currentValue}`);
        cell.classList.add('editing');
        
        let inputElement;
        
        if (fieldType === 'amount') {
            inputElement = document.createElement('input');
            inputElement.type = 'number';
            inputElement.step = '0.01';
            inputElement.min = '0.01';
            inputElement.value = currentValue;
        } else if (fieldType === 'date') {
            inputElement = document.createElement('input');
            inputElement.type = 'date';
            inputElement.value = currentValue;
        } else if (fieldType === 'payer' || fieldType === 'receiver') {
            inputElement = document.createElement('select');
            this.usersData.forEach(user => {
                const option = document.createElement('option');
                option.value = user.name;
                option.textContent = user.name;
                option.selected = user.name === currentValue;
                inputElement.appendChild(option);
            });
        } else {
            inputElement = document.createElement('input');
            inputElement.type = 'text';
            inputElement.value = currentValue;
        }
        
        inputElement.style.width = '100%';
        inputElement.style.border = '2px solid #3498db';
        inputElement.style.padding = '4px';
        inputElement.style.borderRadius = '4px';
        inputElement.style.boxSizing = 'border-box';
        
        // Store original content for cancellation
        this.originalContent = cell.innerHTML;
        
        // Replace cell content with input
        cell.innerHTML = '';
        cell.appendChild(inputElement);
        
        inputElement.focus();
        if (inputElement.type === 'text' || inputElement.type === 'number') {
            inputElement.select();
        }
        
        // Set up event handlers with proper cleanup
        const handleSave = async () => {
            await this.saveEdit(inputElement);
        };
        
        const handleCancel = () => {
            this.cancelEdit();
        };
        
        // Use addEventListener with once: true to prevent multiple handlers
        inputElement.addEventListener('blur', handleSave, { once: true });
        
        inputElement.addEventListener('keydown', (e) => {
            if (e.key === 'Enter') {
                e.preventDefault();
                e.stopPropagation();
                inputElement.blur(); // This will trigger save
            } else if (e.key === 'Escape') {
                e.preventDefault();
                e.stopPropagation();
                handleCancel();
            }
        });
    }

    async saveEdit(inputElement) {
        if (!this.isEditing || !this.editingCell) {
            return;
        }

        const newValue = inputElement.value.trim();
        const cell = this.editingCell;
        const settlementId = cell.closest('tr').getAttribute('data-settlement-id');
        const fieldType = cell.getAttribute('data-field');
        const originalValue = cell.getAttribute('data-value') || '';
        
        console.log(`[DEBUG] Saving edit for ${fieldType}: ${originalValue} -> ${newValue}`);
        
        // If no change, just cancel
        if (newValue === originalValue) {
            this.cancelEdit();
            return;
        }

        try {
            const updateData = {};
            updateData[fieldType] = newValue;

            const response = await fetch(`/edit_settlement/${settlementId}`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(updateData)
            });

            const data = await response.json();

            if (data.success) {
                console.log(`[DEBUG] Settlement edit successful for ${fieldType}`);
                
                // Update the data attribute
                cell.setAttribute('data-value', newValue);
                
                // Update the cell display
                if (fieldType === 'amount') {
                    cell.innerHTML = `$${parseFloat(newValue).toFixed(2)}`;
                } else if (fieldType === 'description' && !newValue) {
                    cell.innerHTML = '-';
                } else {
                    cell.innerHTML = newValue;
                }
                
                // Clean up editing state
                cell.classList.remove('editing');
                this.isEditing = false;
                this.editingCell = null;
                
                this.showTableMessage('Settlement updated successfully', 'success');
                
                // **KEY FIX**: Force immediate balance refresh with a small delay to ensure backend processing
                console.log('[DEBUG] Refreshing balances after settlement edit...');
                setTimeout(async () => {
                    await this.refreshBalancesImmediately();
                }, 100); // Small delay to ensure backend has processed the change
                
            } else {
                throw new Error(data.error || 'Update failed');
            }
        } catch (error) {
            console.error('Error saving settlement edit:', error);
            this.cancelEdit();
            this.showTableMessage('Failed to update settlement: ' + error.message, 'error');
        }
    }

    cancelEdit() {
        if (!this.isEditing || !this.editingCell) {
            return;
        }

        console.log('[DEBUG] Canceling edit');
        const cell = this.editingCell;
        
        // Restore original content
        cell.innerHTML = this.originalContent;
        cell.classList.remove('editing');
        
        // Clean up state
        this.isEditing = false;
        this.editingCell = null;
        this.originalContent = null;
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
                console.log('[DEBUG] Settlement deleted, refreshing all data...');
                // Refresh all data after deletion
                await this.refreshAllDataImmediate();
                this.showSuccessMessage('Payment deleted successfully');
            } else {
                this.showError(data.error || 'Failed to delete settlement');
            }
        } catch (error) {
            console.error('Error deleting settlement:', error);
            this.showError('Network error. Please try again.');
        }
    }

    // **NEW METHOD**: Immediate balance refresh with better error handling
    async refreshBalancesImmediately() {
        try {
            console.log('[DEBUG] Starting immediate balance refresh...');
            
            // First, force backend recalculation to ensure accuracy
            const recalcResponse = await fetch('/api/balances/recalculate', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                }
            });
            
            if (!recalcResponse.ok) {
                console.warn('[WARNING] Balance recalculation request failed, continuing with normal refresh');
            } else {
                console.log('[DEBUG] Backend balance recalculation completed');
            }
            
            // Now refresh the displayed data
            if (window.balanceManager && typeof window.balanceManager.refresh === 'function') {
                console.log('[DEBUG] Refreshing balance manager...');
                await window.balanceManager.refresh();
                console.log('[DEBUG] Balance manager refresh completed');
            } else {
                console.warn('[WARNING] BalanceManager not available, loading data manually');
                await this.loadBalancesDataDirectly();
            }
            
        } catch (error) {
            console.error('[ERROR] Failed to refresh balances immediately:', error);
            // Fallback: try to refresh without forced recalculation
            if (window.balanceManager && typeof window.balanceManager.refresh === 'function') {
                await window.balanceManager.refresh();
            }
        }
    }

    // **NEW METHOD**: Direct balance loading as fallback
    async loadBalancesDataDirectly() {
        try {
            const [balancesResponse, suggestionsResponse] = await Promise.all([
                fetch('/api/balances'),
                fetch('/api/settlement-suggestions')
            ]);
            
            if (balancesResponse.ok && suggestionsResponse.ok) {
                const balancesData = await balancesResponse.json();
                const suggestionsData = await suggestionsResponse.json();
                
                // Update displays if containers exist
                this.updateBalancesDisplay(balancesData.balances);
                this.updateSettlementSuggestionsDisplay(suggestionsData.suggestions);
                this.updateHeaderStatus(balancesData.balances);
                
                console.log('[DEBUG] Direct balance loading completed');
            }
        } catch (error) {
            console.error('[ERROR] Direct balance loading failed:', error);
        }
    }

    // **NEW METHODS**: Direct display update methods (fallback for when BalanceManager isn't available)
    updateBalancesDisplay(balances) {
        const container = document.getElementById('balances-container');
        if (!container || !balances) return;

        if (balances.length === 0) {
            container.innerHTML = '<div style="text-align: center; padding: 20px; color: #7f8c8d;">No users found</div>';
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

    updateSettlementSuggestionsDisplay(suggestions) {
        const container = document.getElementById('settlements-container');
        if (!container) return;
        
        if (!suggestions || suggestions.length === 0) {
            container.innerHTML = '<div class="no-settlements">🎉 All settled! No payments needed.</div>';
            return;
        }

        // Use the SAME format as the original BalanceManager to maintain consistent styling
        const suggestionsHTML = suggestions.map(suggestion => `
            <div class="settlement-item">
                <strong>${suggestion.from}</strong> should pay <strong>${suggestion.to}</strong> 
                <span class="settlement-amount">${suggestion.amount.toFixed(2)}</span>
            </div>
        `).join('');

        container.innerHTML = suggestionsHTML;
    }

    updateHeaderStatus(balances) {
        const statusIndicator = document.querySelector('.status-indicator');
        if (!statusIndicator || !balances) return;

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

    // **UPDATED METHOD**: Enhanced refresh for immediate updates
    async refreshAllDataImmediate() {
        console.log('[DEBUG] Starting immediate refresh of all data...');
        
        try {
            // Refresh settlements table first
            await this.loadActualSettlements();
            console.log('[DEBUG] Settlements table refreshed');
            
            // Then refresh balances immediately
            await this.refreshBalancesImmediately();
            console.log('[DEBUG] All data refresh completed');
            
        } catch (error) {
            console.error('[ERROR] Failed to refresh all data immediately:', error);
        }
    }

    // Legacy method for backward compatibility
    async refreshAllData() {
        return this.refreshAllDataImmediate();
    }

    // Legacy method for backward compatibility
    async refreshBalancesOnly() {
        return this.refreshBalancesImmediately();
    }

    showTableMessage(message, type = 'error') {
        const errorDiv = document.getElementById('table-error');
        if (errorDiv) {
            errorDiv.className = type;
            errorDiv.style.display = 'block';
            errorDiv.innerHTML = `<div style="padding: 8px; border-radius: 4px; ${
                type === 'success' ? 'background: #efe; border: 1px solid #cfc; color: #3c3;' 
                : 'background: #fee; border: 1px solid #fcc; color: #c33;'
            }">${message}</div>`;
            
            setTimeout(() => {
                errorDiv.style.display = 'none';
            }, type === 'success' ? 3000 : 5000);
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
        } else {
            this.showTableMessage(message, 'error');
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
            if (successDiv.parentNode) {
                successDiv.parentNode.removeChild(successDiv);
            }
        }, 3000);
    }
}

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', function() {
    if (!window.settlementManager) {
        console.log('[DEBUG] Initializing SettlementManager...');
        window.settlementManager = new SettlementManager();
    }
});

// Function to open settle up modal (called by button)
function openSettleUpModal() {
    const modal = document.getElementById('settleUpModal');
    if (modal) {
        modal.style.display = 'block';
        
        // Set today's date
        const today = new Date().toISOString().split('T')[0];
        const dateInput = document.getElementById('settlement-date');
        if (dateInput) {
            dateInput.value = today;
        }
    }
}