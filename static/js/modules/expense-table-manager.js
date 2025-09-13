// Expense Table Management Module
class ExpenseTableManager {
    constructor(options = {}) {
        this.tableSelector = options.tableSelector || 'table';
        this.errorSelector = options.errorSelector || '#table-error';
        this.urls = options.urls || {};
        
        this.table = document.querySelector(this.tableSelector);
        this.errorElement = document.querySelector(this.errorSelector);
        
        if (!this.table) {
            console.warn('Expense table not found');
            return;
        }
        
        this.categoriesData = this.getDataFromScript('categories-data');
        this.usersData = this.getDataFromScript('users-data');
        
        this.init();
    }
    
    getDataFromScript(id) {
        try {
            const script = document.getElementById(id);
            return script ? JSON.parse(script.textContent) : [];
        } catch (e) {
            console.error(`Error parsing ${id}:`, e);
            return [];
        }
    }
    
    init() {
        this.setupDeleteButtons();
        this.setupEditableCells();
    }
    
    showMessage(message, color = 'black') {
        // Try to find the error element if not already cached
        if (!this.errorElement) {
            this.errorElement = document.querySelector('#table-error');
        }
        
        if (this.errorElement) {
            this.errorElement.style.color = color;
            this.errorElement.innerHTML = message;
            this.errorElement.style.display = 'block';
            
            // Update background color based on message type
            if (color === 'green') {
                this.errorElement.style.backgroundColor = '#d5f4e6';
                this.errorElement.style.borderLeftColor = '#27ae60';
            } else if (color === 'red') {
                this.errorElement.style.backgroundColor = '#ffeaea';
                this.errorElement.style.borderLeftColor = '#e74c3c';
            }
            
            setTimeout(() => {
                this.errorElement.innerHTML = '';
                this.errorElement.style.display = 'none';
            }, 5000);
        } else {
            // Fallback: create a temporary floating message
            const tempMessage = document.createElement('div');
            tempMessage.style.cssText = `
                position: fixed;
                top: 20px;
                right: 20px;
                background: ${color === 'green' ? '#d5f4e6' : '#ffeaea'};
                color: ${color};
                padding: 12px 16px;
                border-radius: 6px;
                border-left: 4px solid ${color === 'green' ? '#27ae60' : '#e74c3c'};
                box-shadow: 0 4px 12px rgba(0,0,0,0.15);
                z-index: 10000;
                font-weight: 500;
                max-width: 300px;
            `;
            tempMessage.textContent = message;
            document.body.appendChild(tempMessage);
            
            setTimeout(() => {
                if (tempMessage.parentNode) {
                    tempMessage.parentNode.removeChild(tempMessage);
                }
            }, 5000);
        }
    }
    
    setupDeleteButtons() {
        const deleteButtons = this.table.querySelectorAll('.delete-btn');
        
        deleteButtons.forEach((btn) => {
            // Remove existing listeners by cloning
            const newBtn = btn.cloneNode(true);
            btn.parentNode.replaceChild(newBtn, btn);
            
            newBtn.addEventListener('click', (e) => {
                e.preventDefault();
                e.stopPropagation();
                
                const row = newBtn.closest('tr');
                const expenseId = newBtn.getAttribute('data-expense-id') || row.getAttribute('data-expense-id');
                
                if (!expenseId) {
                    this.showMessage('Error: No expense ID found', 'red');
                    return;
                }
                
                if (!confirm("Are you sure you want to delete this expense?")) {
                    return;
                }
                
                this.deleteExpense(expenseId, newBtn, row);
            });
        });
    }
    
    async deleteExpense(expenseId, button, row) {
    // Show loading state
    button.disabled = true;
    button.textContent = "Deleting...";
    
    try {
        const response = await fetch(`/delete_expense/${expenseId}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-Requested-With': 'XMLHttpRequest'
            }
        });
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const result = await response.json();
        
        if (result.success) {
            row.remove();
            this.showMessage('Expense deleted successfully!', 'green');
            
            // Update the filter manager's cached data
            this.updateFilterManagerAfterDelete(expenseId);
            
            // **ADD THIS NEW CODE** - Update expense count directly
            this.updateExpenseCountAfterDelete();
            
            // Update expense count after deletion
            if (window.updateExpenseCount) window.updateExpenseCount();
            if (window.loadBalancesData) window.loadBalancesData();
            
            // Dispatch custom event for filter integration
            document.dispatchEvent(new CustomEvent('expenseDeleted', {
                detail: { expenseId: expenseId }
            }));
            
        } else {
            this.showMessage(result.error || 'Error deleting expense', 'red');
            button.disabled = false;
            button.textContent = "❌ Delete";
        }
    } catch (error) {
        this.showMessage('Network error deleting expense: ' + error.message, 'red');
        button.disabled = false;
        button.textContent = "❌ Delete";
    }
}
    
    // Update filter manager's cached data after deletion
    updateFilterManagerAfterDelete(expenseId) {
        // Update the global filter integration if it exists
        if (window.expenseFilterIntegration && window.expenseFilterIntegration.filterManager) {
            const filterManager = window.expenseFilterIntegration.filterManager;
            
            // Remove the deleted expense from both originalRows and filteredRows
            filterManager.originalRows = filterManager.originalRows.filter(row => 
                row.data.id !== expenseId && row.element.getAttribute('data-expense-id') !== expenseId
            );
            
            filterManager.filteredRows = filterManager.filteredRows.filter(row => 
                row.data.id !== expenseId && row.element.getAttribute('data-expense-id') !== expenseId
            );
            
            // Reapply current filters with updated data
            if (window.expenseFilterIntegration.currentFilter && !window.expenseFilterIntegration.currentFilter.isCleared) {
                filterManager.applyFilters();
            }
            
            console.log(`[DEBUG] Updated filter cache after deleting expense ${expenseId}`);
        }
    }

    // Update expense count display after deletion
        updateExpenseCountAfterDelete() {
            // Get current table row count
            const currentRows = this.table.querySelectorAll('tbody tr[data-expense-id]');
            const currentCount = currentRows.length;
            
            // Update the expense count display
            const countElement = document.querySelector('.expense-count');
            if (countElement) {
                countElement.textContent = `(${currentCount})`;
                // Reset to normal styling since this is unfiltered data
                countElement.style.background = '#f8f9fa';
                countElement.style.color = '#6c757d';
                countElement.style.padding = '2px 6px';
                countElement.style.borderRadius = '3px';
            }
            
            // Update the total expense amount
            let totalAmount = 0;
            currentRows.forEach(row => {
                const amountCell = row.querySelector('td[data-value]');
                if (amountCell) {
                    const amount = parseFloat(amountCell.getAttribute('data-value') || '0');
                    totalAmount += amount;
                }
            });
            
            // Update the total display
            const totalElement = document.getElementById('expenses-total');
            if (totalElement) {
                totalElement.textContent = totalAmount.toFixed(2);
                // Reset to normal styling since this is unfiltered data
                totalElement.style.background = 'linear-gradient(135deg, #27ae60, #2ecc71)';
                totalElement.title = 'Total of all expenses';
            }
            
            console.log(`[DEBUG] Updated expense count to ${currentCount} and total to $${totalAmount.toFixed(2)}`);
        }
    
    setupEditableCells() {
        const editableCells = this.table.querySelectorAll('td.editable');
        
        editableCells.forEach((cell) => {
            cell.style.cursor = 'pointer';
            cell.style.backgroundColor = '#f9f9f9';
            cell.title = 'Click to edit';
            
            // Remove existing listeners by cloning
            const newCell = cell.cloneNode(true);
            cell.parentNode.replaceChild(newCell, cell);
            
            newCell.addEventListener('click', (e) => {
                e.stopPropagation();
                this.startEditCell(newCell);
            });
        });
    }
    
    startEditCell(cell) {
        // Check if already editing
        if (cell.querySelector('input, select')) {
            return;
        }
        
        const classes = Array.from(cell.classList);
        const type = classes.find(c => c !== 'editable');
        const currentValue = cell.getAttribute('data-value') || '';
        const originalHTML = cell.innerHTML;
        
        // Store original HTML for participants editing
        if (type === 'participants') {
            cell.setAttribute('data-original-html', originalHTML);
        }
        
        const input = this.createInputForType(type, currentValue, cell);
        
        // Handle participants differently (no blur event)
        if (type === 'participants') {
            // Replace content with participants editor
            cell.innerHTML = '';
            cell.appendChild(input);
            return; // Exit early for participants
        }
        
        // Style the input for non-participants
        input.style.width = '100%';
        input.style.border = '2px solid blue';
        input.style.padding = '4px';
        input.style.boxSizing = 'border-box';
        
        // Replace content with input
        cell.innerHTML = '';
        cell.appendChild(input);
        input.focus();
        
        // Set up autocomplete for description fields
        let autocomplete = null;
        if (type === 'description' && window.createAutocomplete) {
            setTimeout(() => {
                autocomplete = window.createAutocomplete(input);
            }, 10);
        }
        
        const saveEdit = () => this.saveEdit(cell, input, type, originalHTML, autocomplete);
        const cancelEdit = () => this.cancelEdit(cell, originalHTML, autocomplete);
        
        // Event listeners for non-participants
        input.addEventListener('blur', () => setTimeout(saveEdit, 100));
        input.addEventListener('keydown', (e) => {
            if (e.key === 'Enter') {
                e.preventDefault();
                saveEdit();
            } else if (e.key === 'Escape') {
                e.preventDefault();
                cancelEdit();
            }
        });
        
        if (type === 'category' || type === 'user') {
            input.addEventListener('change', () => {
                if (input.value === 'manage') {
                    const dest = type === 'category' ? this.urls.manageCategories : this.urls.manageUsers;
                    const nextUrl = encodeURIComponent(window.location.href);
                    window.location.href = `${dest}?next=${nextUrl}`;
                    return;
                }
                saveEdit();
            });
        }
    }
    
    createInputForType(type, currentValue, cell) {
        let input;
        
        switch (type) {
            case 'amount':
                input = document.createElement('input');
                input.type = 'number';
                input.step = '0.01';
                input.min = '0.01';
                input.value = parseFloat(currentValue || '0').toFixed(2);
                break;
                
            case 'description':
                input = document.createElement('input');
                input.type = 'text';
                input.value = currentValue;
                input.autocomplete = 'off';
                break;
                
            case 'date':
                input = document.createElement('input');
                input.type = 'date';
                input.value = currentValue;
                break;
                
            case 'category':
                input = document.createElement('select');
                this.populateSelect(input, this.categoriesData, currentValue, 'category');
                break;
                
            case 'user':
                input = document.createElement('select');
                this.populateSelect(input, this.usersData, currentValue, 'user');
                break;
                
            case 'participants':
                input = this.createParticipantsEditor(cell);
                break;
                
            default:
                input = document.createElement('input');
                input.type = 'text';
                input.value = currentValue;
        }
        
        return input;
    }
    
    createParticipantsEditor(cell) {
        const container = document.createElement('div');
        container.style.cssText = 'background: white; border: 2px solid #3498db; border-radius: 6px; padding: 8px; max-height: 180px; overflow-y: auto; min-width: 200px; box-shadow: 0 4px 12px rgba(0,0,0,0.15);';
        
        // Get current participant IDs
        const currentParticipantIds = (cell.getAttribute('data-participant-ids') || '').split(',').filter(id => id);
        
        // Title
        const title = document.createElement('div');
        title.textContent = 'Select Participants:';
        title.style.cssText = 'font-weight: bold; margin-bottom: 6px; font-size: 0.85rem; color: #2c3e50;';
        container.appendChild(title);
        
        // Checkboxes for each user - more compact layout
        this.usersData.forEach(user => {
            const wrapper = document.createElement('label');
            wrapper.style.cssText = 'display: flex; align-items: center; margin: 2px 0; padding: 3px 6px; background: #f8f9fa; border-radius: 3px; cursor: pointer; font-size: 0.8rem; transition: background-color 0.2s;';
            
            const checkbox = document.createElement('input');
            checkbox.type = 'checkbox';
            checkbox.value = user.id;
            checkbox.checked = currentParticipantIds.includes(user.id.toString());
            checkbox.style.cssText = 'margin-right: 6px; transform: scale(0.9);';
            
            const labelText = document.createElement('span');
            labelText.textContent = user.name;
            labelText.style.cssText = 'flex: 1; color: #2c3e50;';
            
            wrapper.appendChild(checkbox);
            wrapper.appendChild(labelText);
            
            // Add hover effect
            wrapper.addEventListener('mouseenter', () => {
                wrapper.style.backgroundColor = '#e9ecef';
            });
            wrapper.addEventListener('mouseleave', () => {
                wrapper.style.backgroundColor = '#f8f9fa';
            });
            
            container.appendChild(wrapper);
        });
        
        // Buttons - more compact
        const buttonContainer = document.createElement('div');
        buttonContainer.style.cssText = 'display: flex; gap: 6px; margin-top: 8px;';
        
        const saveBtn = document.createElement('button');
        saveBtn.textContent = 'Save';
        saveBtn.style.cssText = 'background: #27ae60; color: white; border: none; padding: 4px 8px; border-radius: 3px; cursor: pointer; font-size: 0.75rem; flex: 1;';
        
        const cancelBtn = document.createElement('button');
        cancelBtn.textContent = 'Cancel';
        cancelBtn.style.cssText = 'background: #95a5a6; color: white; border: none; padding: 4px 8px; border-radius: 3px; cursor: pointer; font-size: 0.75rem; flex: 1;';
        
        buttonContainer.appendChild(saveBtn);
        buttonContainer.appendChild(cancelBtn);
        container.appendChild(buttonContainer);
        
        // Store reference to container for event handlers
        container._saveBtn = saveBtn;
        container._cancelBtn = cancelBtn;
        
        // Add event listeners with proper context
        saveBtn.addEventListener('click', (e) => {
            e.preventDefault();
            e.stopPropagation();
            
            const selectedIds = Array.from(container.querySelectorAll('input[type="checkbox"]:checked')).map(cb => parseInt(cb.value));
            
            // Validate at least one participant
            if (selectedIds.length === 0) {
                alert('Please select at least one participant');
                return;
            }
            
            // Set the selected participants on the container
            container._selectedParticipants = selectedIds;
            
            // Call the save handler directly
            this.handleParticipantsSave(container, cell);
        });
        
        cancelBtn.addEventListener('click', (e) => {
            e.preventDefault();
            e.stopPropagation();
            
            // Call the cancel handler directly  
            this.handleParticipantsCancel(container, cell);
        });
        
        return container;
    }
    
    populateSelect(select, data, currentValue, type) {
        // Placeholder option
        const placeholder = document.createElement('option');
        placeholder.value = '';
        placeholder.textContent = `Select ${type}`;
        placeholder.disabled = true;
        placeholder.selected = true;
        select.appendChild(placeholder);
        
        // Data options
        data.forEach(item => {
            const option = document.createElement('option');
            option.value = item.name;
            option.textContent = item.name;
            option.selected = item.name === currentValue;
            select.appendChild(option);
        });
        
    }
    
    async saveEdit(cell, input, type, originalHTML, autocomplete) {
        // Clean up autocomplete
        if (autocomplete && autocomplete.cleanup) {
            autocomplete.cleanup();
        }
        
        const row = cell.closest('tr');
        const expenseId = row.getAttribute('data-expense-id');
        
        let newValue, data = {};
        
        if (type === 'participants') {
            // Handle participants editing - use direct method calls
            const container = input;
            
            // Don't use setTimeout, handle directly
            return;
        } else {
            // Handle other field types
            newValue = input.value.trim();
            
            // Validation
            if (type === 'amount') {
                const numValue = parseFloat(newValue);
                if (isNaN(numValue) || numValue <= 0) {
                    this.showMessage('Amount must be a positive number', 'red');
                    cell.innerHTML = originalHTML;
                    return;
                }
                newValue = numValue;
            }
            
            if (!newValue && type !== 'description') {
                this.showMessage(`${type} cannot be empty`, 'red');
                cell.innerHTML = originalHTML;
                return;
            }
            
            // Prepare data
            data[type === 'user' ? 'user' : type] = newValue;
            await this.performSave(cell, data, expenseId, type, originalHTML, input, newValue);
        }
    }
    
    async performSave(cell, data, expenseId, type, originalHTML, input, newValue) {
        // Show loading state
        if (input.disabled !== undefined) {
            input.disabled = true;
            input.style.backgroundColor = '#f0f0f0';
        }
        
        try {
            const response = await fetch(`/edit_expense/${expenseId}`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-Requested-With': 'XMLHttpRequest'
                },
                body: JSON.stringify(data)
            });
            
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            const result = await response.json();
            
            if (result.success) {
                // Update display based on type
                if (type === 'amount') {
                    const numValue = parseFloat(newValue);
                    cell.innerHTML = `$${numValue.toFixed(2)}`;
                    cell.setAttribute('data-value', numValue.toFixed(2));
                } else if (type === 'participants') {
                    // Refresh the entire row to get updated participant info
                    window.location.reload();
                    return;
                } else {
                    cell.innerHTML = newValue || '';
                    cell.setAttribute('data-value', newValue);
                }
                
                // Update filter manager's cached data after edit
                this.updateFilterManagerAfterEdit(expenseId, type, newValue, cell);
                
                this.showMessage('Updated successfully!', 'green');
                // Update expense count after edit
                if (window.updateExpenseCount) window.updateExpenseCount();
                if (window.loadBalancesData) window.loadBalancesData();
            } else {
                this.showMessage(result.error || 'Update failed', 'red');
                cell.innerHTML = originalHTML;
            }
        } catch (error) {
            this.showMessage('Network error: ' + error.message, 'red');
            cell.innerHTML = originalHTML;
        }
    }
    
    // Update filter manager's cached data after edit
    updateFilterManagerAfterEdit(expenseId, type, newValue, cell) {
        if (window.expenseFilterIntegration && window.expenseFilterIntegration.filterManager) {
            const filterManager = window.expenseFilterIntegration.filterManager;
            
            // Update both originalRows and filteredRows
            [filterManager.originalRows, filterManager.filteredRows].forEach(rowsArray => {
                const rowToUpdate = rowsArray.find(row => 
                    row.data.id === expenseId || row.element.getAttribute('data-expense-id') === expenseId
                );
                
                if (rowToUpdate) {
                    // Update the data object
                    if (type === 'user') {
                        rowToUpdate.data.paidBy = newValue;
                    } else {
                        rowToUpdate.data[type] = newValue;
                    }
                    
                    // Update the element's data-value attribute
                    const cellInElement = rowToUpdate.element.querySelector(`td.${type}`);
                    if (cellInElement) {
                        cellInElement.setAttribute('data-value', newValue);
                        if (type === 'amount') {
                            cellInElement.textContent = `$${parseFloat(newValue).toFixed(2)}`;
                        } else {
                            cellInElement.textContent = newValue;
                        }
                    }
                }
            });
            
            console.log(`[DEBUG] Updated filter cache after editing ${type} for expense ${expenseId}`);
        }
    }
    
    cancelEdit(cell, originalHTML, autocomplete) {
        if (autocomplete && autocomplete.cleanup) {
            autocomplete.cleanup();
        }
        cell.innerHTML = originalHTML;
    }
    
    // Handler methods for participants editing
    async handleParticipantsSave(container, cell) {
        const selectedIds = container._selectedParticipants || [];
        
        if (selectedIds.length === 0) {
            this.showMessage('At least one participant is required', 'red');
            return;
        }
        
        const row = cell.closest('tr');
        const expenseId = row.getAttribute('data-expense-id');
        const data = { participants: selectedIds };
        
        try {
            const response = await fetch(`/edit_expense/${expenseId}`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-Requested-With': 'XMLHttpRequest'
                },
                body: JSON.stringify(data)
            });
            
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            const result = await response.json();
            
            if (result.success) {
                this.showMessage('Participants updated successfully!', 'green');
                // Update expense count after participant edit
                if (window.updateExpenseCount) window.updateExpenseCount();
                // Refresh the page to show updated participant info
                setTimeout(() => {
                    window.location.reload();
                }, 1000);
                
                if (window.loadBalancesData) {
                    window.loadBalancesData();
                }
            } else {
                this.showMessage(result.error || 'Update failed', 'red');
                this.handleParticipantsCancel(container, cell);
            }
        } catch (error) {
            this.showMessage('Network error: ' + error.message, 'red');
            this.handleParticipantsCancel(container, cell);
        }
    }
    
    handleParticipantsCancel(container, cell) {
        // Restore original HTML
        const originalHTML = cell.getAttribute('data-original-html');
        if (originalHTML) {
            cell.innerHTML = originalHTML;
        } else {
            // Fallback: reload the page if we can't restore
            window.location.reload();
        }
    }
}

// Export for use
window.ExpenseTableManager = ExpenseTableManager;