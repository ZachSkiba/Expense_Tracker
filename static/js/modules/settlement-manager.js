// settlement-manager.js - FIXED VERSION (DOM conflicts resolved + auto refresh)
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
                
                // Reload settlement history and refresh balances
                await this.refreshAllData();
                
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
            console.log('[DEBUG] Already editing, ignoring new edit request');
            return;
        }

        this.isEditing = true;
        this.editingCell = cell;
        
        const currentValue = cell.getAttribute('data-value') || '';
        const fieldType = cell.getAttribute('data-field');
        
        console.log(`[DEBUG] Starting edit: ${fieldType} = "${currentValue}"`);
        
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
            console.log('[DEBUG] Save triggered');
            await this.saveEdit(inputElement);
        };
        
        const handleCancel = () => {
            console.log('[DEBUG] Cancel triggered');
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
            console.log('[DEBUG] Not in editing mode, ignoring save');
            return;
        }

        const newValue = inputElement.value.trim();
        const cell = this.editingCell;
        const settlementId = cell.closest('tr').getAttribute('data-settlement-id');
        const fieldType = cell.getAttribute('data-field');
        const originalValue = cell.getAttribute('data-value') || '';
        
        console.log(`[DEBUG] Saving edit: ${fieldType} = "${newValue}" (was "${originalValue}")`);
        
        // If no change, just cancel
        if (newValue === originalValue) {
            console.log('[DEBUG] No change detected, canceling edit');
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
                console.log('[DEBUG] Server update successful');
                
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
                
                // Refresh balances and settlement suggestions after edit
                await this.refreshBalancesOnly();
                
            } else {
                throw new Error(data.error || 'Update failed');
            }
        } catch (error) {
            console.error('[DEBUG] Error updating settlement:', error);
            this.cancelEdit();
            this.showTableMessage('Failed to update settlement: ' + error.message, 'error');
        }
    }

    cancelEdit() {
        if (!this.isEditing || !this.editingCell) {
            console.log('[DEBUG] Not in editing mode, ignoring cancel');
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
                // Refresh all data after deletion
                await this.refreshAllData();
                this.showSuccessMessage('Payment deleted successfully');
            } else {
                this.showError(data.error || 'Failed to delete settlement');
            }
        } catch (error) {
            console.error('Error deleting settlement:', error);
            this.showError('Network error. Please try again.');
        }
    }

    // Refresh both settlements and balances
    async refreshAllData() {
        console.log('[DEBUG] Refreshing all data (settlements + balances)');
        await Promise.all([
            this.loadActualSettlements(),
            this.refreshBalancesOnly()
        ]);
    }

    // Refresh only balances and settlement suggestions
    async refreshBalancesOnly() {
        console.log('[DEBUG] Refreshing balances only');
        if (window.balanceManager) {
            await window.balanceManager.refresh();
        }
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