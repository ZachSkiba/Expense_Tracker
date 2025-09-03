// settlement-manager.js - COMPLETE VERSION FOR COMBINED PAGE
// Handles ALL functionality: form submission, inline editing, deleting, balance refreshing

class CombinedPageManager {
    constructor() {
        this.usersData = this.loadUsersData();
        this.isEditing = false; // Prevent multiple simultaneous edits
        this.editingCell = null; // Track which cell is being edited
        this.originalContent = null;
        
        this.init();
    }

    async init() {
        // Initialize all functionality
        this.initializeFormHandling();
        this.initializeTableEditing();
        this.initializeDeleteButtons();
        this.setDefaultDate();
        
        // Load initial data for both main page and sidebar
        await this.loadActualSettlements();
        
        // Check if we need to render settlements table (for sidebar)
        this.renderSidebarSettlementsIfNeeded();
        
        console.log('[DEBUG] CombinedPageManager initialized successfully');
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

    setDefaultDate() {
        // Set today's date as default for any date inputs
        const today = new Date().toISOString().split('T')[0];
        const dateInputs = document.querySelectorAll('input[type="date"]');
        dateInputs.forEach(input => {
            if (!input.value) {
                input.value = today;
            }
        });
    }

    // ==========================================
    // FORM HANDLING (New Payment Submission)
    // ==========================================

    initializeFormHandling() {
        // Handle settlement form submission - check both class and ID selectors
        const settlementForm = document.querySelector('.settlement-form') || document.querySelector('#settlement-form');
        if (settlementForm) {
            settlementForm.addEventListener('submit', (e) => this.handleFormSubmit(e));
            console.log('[DEBUG] Form handler attached');
        }

        // Handle payer/receiver validation
        const payerSelect = document.querySelector('select[name="payer_id"]');
        const receiverSelect = document.querySelector('select[name="receiver_id"]');
        
        if (payerSelect && receiverSelect) {
            payerSelect.addEventListener('change', () => this.validatePayerReceiver());
            receiverSelect.addEventListener('change', () => this.validatePayerReceiver());
        }
    }

    validatePayerReceiver() {
        const payerSelect = document.querySelector('select[name="payer_id"]');
        const receiverSelect = document.querySelector('select[name="receiver_id"]');
        
        if (!payerSelect || !receiverSelect) return true;
        
        const payerId = payerSelect.value;
        const receiverId = receiverSelect.value;
        
        if (payerId && receiverId && payerId === receiverId) {
            this.showError('Payer and receiver cannot be the same person');
            return false;
        }
        
        return true;
    }

    async handleFormSubmit(e) {
        e.preventDefault();
        
        console.log('[DEBUG] Form submission started');
        
        // Validate payer/receiver first
        if (!this.validatePayerReceiver()) {
            return;
        }

        // Get form data
        const formData = new FormData(e.target);
        const settlementData = {
            amount: formData.get('amount'),
            payer_id: formData.get('payer_id'),
            receiver_id: formData.get('receiver_id'),
            description: formData.get('description'),
            date: formData.get('date') || new Date().toISOString().split('T')[0]
        };

        try {
            const response = await fetch('/api/settlements', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(settlementData)
            });

            const data = await response.json();

            if (data.success) {
                console.log('[DEBUG] Settlement created successfully');
                
                // Clear form
                e.target.reset();
                this.setDefaultDate();
                
                // Close modal if it exists
                const modal = document.getElementById('settleUpModal');
                if (modal) {
                    modal.style.display = 'none';
                }
                
                // Refresh all data
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

    // ==========================================
    // TABLE EDITING (Inline Edit Functionality)
    // ==========================================

    initializeTableEditing() {
        // This will be called after table is rendered
        this.attachEditingEventListeners();
    }

    attachEditingEventListeners() {
        const editableCells = document.querySelectorAll('.settlements-table .editable, .settlements-table-main .editable');
        
        editableCells.forEach(cell => {
            // Clone the cell to remove all existing event listeners
            const newCell = cell.cloneNode(true);
            cell.parentNode.replaceChild(newCell, cell);
            
            // Add new listener to the cloned cell
            newCell.addEventListener('click', (e) => {
                e.stopPropagation();
                this.startEditing(newCell);
            });
        });
        
        console.log(`[DEBUG] Attached editing listeners to ${editableCells.length} cells`);
    }

    startEditing(cell) {
        if (this.isEditing) {
            console.log('[DEBUG] Already editing, ignoring click');
            return;
        }

        this.isEditing = true;
        this.editingCell = cell;
        
        const currentValue = cell.getAttribute('data-value') || '';
        const fieldType = cell.getAttribute('data-field');
        
        console.log(`[DEBUG] Starting edit for ${fieldType}: ${currentValue}`);
        
        cell.classList.add('editing');
        
        let inputElement = this.createInputElement(fieldType, currentValue);
        
        // Store original content for cancellation
        this.originalContent = cell.innerHTML;
        
        // Replace cell content with input
        cell.innerHTML = '';
        cell.appendChild(inputElement);
        
        inputElement.focus();
        if (inputElement.type === 'text' || inputElement.type === 'number') {
            inputElement.select();
        }
        
        // Set up event handlers
        this.setupInputEventHandlers(inputElement);
    }

    createInputElement(fieldType, currentValue) {
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
        
        // Style the input
        inputElement.style.width = '100%';
        inputElement.style.border = '2px solid #3498db';
        inputElement.style.padding = '4px';
        inputElement.style.borderRadius = '4px';
        inputElement.style.boxSizing = 'border-box';
        
        return inputElement;
    }

    setupInputEventHandlers(inputElement) {
        const handleSave = async () => {
            await this.saveEdit(inputElement);
        };
        
        const handleCancel = () => {
            this.cancelEdit();
        };
        
        inputElement.addEventListener('blur', handleSave, { once: true });
        
        inputElement.addEventListener('keydown', (e) => {
            if (e.key === 'Enter') {
                e.preventDefault();
                e.stopPropagation();
                inputElement.blur();
            } else if (e.key === 'Escape') {
                e.preventDefault();
                e.stopPropagation();
                handleCancel();
            }
        });
    }

    async saveEdit(inputElement) {
        if (!this.isEditing || !this.editingCell) return;

        const newValue = inputElement.value.trim();
        const cell = this.editingCell;
        const settlementId = cell.closest('tr').getAttribute('data-settlement-id');
        const fieldType = cell.getAttribute('data-field');
        const originalValue = cell.getAttribute('data-value') || '';
        
        console.log(`[DEBUG] Saving edit for ${fieldType}: ${originalValue} -> ${newValue}`);
        
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
                console.log(`[DEBUG] Settlement edit successful`);
                
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
                this.finishEditing();
                
                this.showTableMessage('Settlement updated successfully', 'success');
                
                // Refresh balances after edit
                setTimeout(() => this.refreshBalancesOnly(), 500);
                
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
        if (!this.isEditing || !this.editingCell) return;

        console.log('[DEBUG] Canceling edit');
        
        const cell = this.editingCell;
        cell.innerHTML = this.originalContent;
        
        this.finishEditing();
    }

    finishEditing() {
        if (this.editingCell) {
            this.editingCell.classList.remove('editing');
        }
        
        this.isEditing = false;
        this.editingCell = null;
        this.originalContent = null;
    }

    // ==========================================
    // DELETE FUNCTIONALITY
    // ==========================================

    initializeDeleteButtons() {
        // This will be called after table is rendered
        this.attachDeleteEventListeners();
    }

    attachDeleteEventListeners() {
        // Only select delete buttons that are specifically for settlements
        const deleteButtons = document.querySelectorAll('.settlements-table .delete-btn, .settlements-table-main .delete-btn, .delete-settlement-btn');
        
        deleteButtons.forEach(button => {
            // Clone the button to remove all existing event listeners
            const newButton = button.cloneNode(true);
            button.parentNode.replaceChild(newButton, button);
            
            // Add new listener to the cloned button
            newButton.addEventListener('click', (e) => {
                e.stopPropagation();
                const settlementId = newButton.getAttribute('data-settlement-id');
                this.deleteSettlement(settlementId);
            });
        });
        
        console.log(`[DEBUG] Attached delete listeners to ${deleteButtons.length} settlement buttons`);
    }

    async deleteSettlement(settlementId) {
        if (!confirm('Are you sure you want to delete this settlement? This will reverse the balance changes.')) {
            return;
        }

        console.log(`[DEBUG] Deleting settlement ${settlementId}`);

        try {
            const response = await fetch(`/delete_settlement/${settlementId}`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                }
            });

            const data = await response.json();

            if (data.success) {
                this.showSuccessMessage('Payment deleted successfully');
                
                // Refresh all data after deletion
                await this.refreshAllDataImmediate();
                
            } else {
                this.showError('Error deleting settlement: ' + data.error);
            }
        } catch (error) {
            console.error('Error deleting settlement:', error);
            this.showError('Error deleting settlement: ' + error.message);
        }
    }

    // ==========================================
    // DATA LOADING & REFRESHING
    // ==========================================

    async loadActualSettlements() {
        try {
            console.log('[DEBUG] Loading settlements data...');
            
            const response = await fetch('/api/settlements?limit=10');
            const data = await response.json();

            if (data.settlements) {
                console.log(`[DEBUG] Loaded ${data.settlements.length} settlements`);
                
                // Store settlements data for use
                this.settlementsData = data.settlements;
                
                // Check if we need to render the sidebar table
                this.renderSidebarSettlementsIfNeeded();
                
                // Attach event listeners to existing tables (for combined page)
                setTimeout(() => {
                    this.attachEditingEventListeners();
                    this.attachDeleteEventListeners();
                }, 100);
            }
        } catch (error) {
            console.error('Error loading settlements:', error);
            this.settlementsData = [];
        }
    }

    // New method to handle sidebar settlements table rendering
    renderSidebarSettlementsIfNeeded() {
        const sidebarContainer = document.getElementById('settlements-table-container');
        
        // Render if container exists (either loading or needs refresh)
        if (sidebarContainer) {
            console.log('[DEBUG] Rendering sidebar settlements table');
            this.renderSettlementsTable(this.settlementsData || []);
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
                                ${parseFloat(settlement.amount).toFixed(2)}
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
        
        // Attach event listeners to the newly rendered table
        this.attachEventListenersToContainer(container);
    }

    // Helper method to attach listeners to a specific container
    attachEventListenersToContainer(container) {
        // Add delete event listeners
        container.querySelectorAll('.delete-btn').forEach(button => {
            // Clone the button to remove all existing event listeners
            const newButton = button.cloneNode(true);
            button.parentNode.replaceChild(newButton, button);
            
            newButton.addEventListener('click', (e) => {
                e.stopPropagation();
                const settlementId = newButton.getAttribute('data-settlement-id');
                this.deleteSettlement(settlementId);
            });
        });

        // Add editing event listeners
        container.querySelectorAll('.editable').forEach(cell => {
            // Clone the cell to remove all existing event listeners
            const newCell = cell.cloneNode(true);
            cell.parentNode.replaceChild(newCell, cell);
            
            newCell.addEventListener('click', (e) => {
                e.stopPropagation();
                this.startEditing(newCell);
            });
        });
    }

    async refreshAllDataImmediate() {
        console.log('[DEBUG] Starting immediate refresh of all data...');
        
        try {
            // Reload settlements data first
            await this.loadActualSettlements();
            
            // Check if we're on the combined page (has .settlement-form class) or main page (has modal)
            const isCombinedPage = document.querySelector('.settlement-form') !== null;
            const isMainPage = document.getElementById('settleUpModal') !== null;
            
            if (isCombinedPage) {
                // For combined page, do full page reload to refresh all server-side data
                window.location.reload();
            } else if (isMainPage) {
                // For main page, refresh balances and settlements data
                console.log('[DEBUG] Refreshing main page data...');
                
                // First reload the settlements data
                await this.loadActualSettlements();
                
                // Use the global refresh function from main.js
                if (window.globalRefreshBalances) {
                    await window.globalRefreshBalances();
                } else if (window.AppUtils && window.AppUtils.refreshBalances) {
                    await window.AppUtils.refreshBalances();
                }
                
                // Force refresh the sidebar settlements table
                this.renderSidebarSettlementsIfNeeded();
            } else {
                // Fallback: just refresh the sidebar table
                this.renderSidebarSettlementsIfNeeded();
                
                // Also refresh balances if balance manager is available
                if (window.balanceManager && typeof window.balanceManager.refresh === 'function') {
                    await window.balanceManager.refresh();
                }
            }
            
        } catch (error) {
            console.error('[ERROR] Failed to refresh all data immediately:', error);
        }
    }

    async refreshBalancesOnly() {
        try {
            console.log('[DEBUG] Refreshing balances only...');
            
            // For balance-only updates, we can use the API
            const [balancesResponse, suggestionsResponse] = await Promise.all([
                fetch('/api/balances'),
                fetch('/api/settlement-suggestions')
            ]);
            
            if (balancesResponse.ok && suggestionsResponse.ok) {
                const balancesData = await balancesResponse.json();
                const suggestionsData = await suggestionsResponse.json();
                
                // Update displays
                this.updateBalancesDisplay(balancesData.balances);
                this.updateSettlementSuggestionsDisplay(suggestionsData.suggestions);
                
                console.log('[DEBUG] Balances refreshed successfully');
            }
            
        } catch (error) {
            console.error('[ERROR] Failed to refresh balances:', error);
        }
    }

    // ==========================================
    // UI UPDATE METHODS
    // ==========================================

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
            let statusText, amountText;
            
            if (balance.balance > 0.01) {
                statusText = 'is owed';
                amountText = `+$${balance.balance.toFixed(2)}`;
            } else if (balance.balance < -0.01) {
                statusText = 'owes';
                amountText = `-$${Math.abs(balance.balance).toFixed(2)}`;
            } else {
                statusText = 'even';
                amountText = '$0.00';
            }

            return `
                <div class="balance-item ${status}">
                    <div class="user-info">
                        <div class="user-avatar">${initial}</div>
                        <div>
                            <div class="user-name">${balance.user_name}</div>
                        </div>
                    </div>
                    <div class="balance-amount">
                        <div class="amount">${amountText}</div>
                        <div class="status">${statusText}</div>
                    </div>
                </div>
            `;
        }).join('');

        container.innerHTML = balanceHTML;
    }

    updateSettlementSuggestionsDisplay(suggestions) {
        const container = document.querySelector('.settlement-suggestions');
        if (!container) return;
        
        if (!suggestions || suggestions.length === 0) {
            container.innerHTML = `
                <div class="settlement-card" style="background: #e8f5e8; border-color: #c3e6cb;">
                    🎉 All Settled! Everyone is even - no settlements needed!
                </div>
            `;
            return;
        }

        const title = '<h3 style="color: #2c3e50; margin-bottom: 15px; font-size: 1.1rem;">💡 Suggested Settlements</h3>';
        const subtitle = '<p style="margin-bottom: 15px; color: #6c757d; font-size: 0.9rem;">To settle all debts with minimum transactions:</p>';
        
        const suggestionsHTML = suggestions.map(suggestion => `
            <div class="settlement-card">
                <strong>${suggestion.from}</strong> should pay <strong>${suggestion.to}</strong> 
                <span class="balance-positive">$${suggestion.amount.toFixed(2)}</span>
            </div>
        `).join('');

        container.innerHTML = title + subtitle + suggestionsHTML;
    }

    // ==========================================
    // MESSAGE DISPLAY METHODS
    // ==========================================

    showTableMessage(message, type = 'error') {
        const errorDiv = document.getElementById('table-error');
        if (errorDiv) {
            errorDiv.className = type;
            errorDiv.style.display = 'block';
            errorDiv.innerHTML = `<div style="padding: 8px; border-radius: 4px; ${
                type === 'success' ? 'background: #d4edda; border: 1px solid #c3e6cb; color: #155724;' 
                : 'background: #f8d7da; border: 1px solid #f5c6cb; color: #721c24;'
            }">${message}</div>`;
            
            setTimeout(() => {
                errorDiv.style.display = 'none';
            }, type === 'success' ? 3000 : 5000);
        }
    }

    showError(message) {
        // Look for existing error div or create one
        let errorDiv = document.querySelector('.error-message');
        if (!errorDiv) {
            // Create error div if it doesn't exist
            errorDiv = document.createElement('div');
            errorDiv.className = 'error-message';
            const form = document.querySelector('.settlement-form');
            if (form) {
                form.parentNode.insertBefore(errorDiv, form);
            }
        }
        
        errorDiv.textContent = message;
        errorDiv.style.display = 'block';
        
        setTimeout(() => {
            errorDiv.style.display = 'none';
        }, 5000);
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

// ==========================================
// INITIALIZATION
// ==========================================

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', function() {
    console.log('[DEBUG] DOM loaded, initializing CombinedPageManager...');
    
    if (!window.combinedPageManager) {
        window.combinedPageManager = new CombinedPageManager();
    }
});

// Legacy compatibility - expose some methods globally if needed
window.openSettleUpModal = function() {
    console.log('[DEBUG] openSettleUpModal called - not needed for combined page');
};

// Expose refresh method globally in case other scripts need it
window.refreshBalances = function() {
    if (window.combinedPageManager) {
        return window.combinedPageManager.refreshBalancesOnly();
    }
};