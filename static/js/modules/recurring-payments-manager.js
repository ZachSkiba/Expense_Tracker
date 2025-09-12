/**
 * Recurring Payments Manager - WITH IMMEDIATE EXPENSE TABLE REFRESH
 * Fixed to immediately refresh main expense table after creating recurring payments
 */

class RecurringPaymentsManager {
    constructor() {
        this.form = document.getElementById('recurring-payment-form');
        this.tableBody = document.getElementById('recurring-payments-table-body');
        this.table = document.querySelector('.recurring-payments-table');
        this.isSubmitting = false;
        this.lastSubmissionTime = 0;
        
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
        this.bindEvents();
        this.loadRecurringPayments();
    }
    
    bindEvents() {
        if (this.form) {
            // Remove the form's default submit behavior entirely
            this.form.addEventListener('submit', (e) => {
                e.preventDefault();
                e.stopImmediatePropagation();
                this.handleSubmit();
                return false;
            });
            
            // Also handle button clicks directly to prevent any form submission
            const submitBtn = document.getElementById('recurring-submit-btn');
            if (submitBtn) {
                submitBtn.addEventListener('click', (e) => {
                    e.preventDefault();
                    e.stopImmediatePropagation();
                    this.handleSubmit();
                    return false;
                });
            }
        }
        
        // Frequency change handler
        const frequencySelect = this.form ? this.form.querySelector('[name="frequency"]') : null;
        if (frequencySelect) {
            frequencySelect.addEventListener('change', (e) => this.handleFrequencyChange(e));
        }
    }
    
    handleSubmit() {
        const currentTime = Date.now();
        
        // Prevent rapid successive clicks (within 2 seconds)
        if (currentTime - this.lastSubmissionTime < 2000) {
            console.log('BLOCKED: Submission too soon after last one');
            return;
        }
        
        // Prevent if already submitting
        if (this.isSubmitting) {
            console.log('BLOCKED: Already submitting');
            return;
        }
        
        this.lastSubmissionTime = currentTime;
        this.handleFormSubmit();
    }
    
    async handleFormSubmit() {
        console.log('Starting form submission...');
        
        const formData = new FormData(this.form);
        const data = this.parseFormData(formData);
        
        // Validate form
        if (!this.validateForm(data)) {
            return;
        }
        
        try {
            this.isSubmitting = true;
            this.setLoadingState(true);
            
            // Only create new recurring payments, never update from form
            console.log('CREATING new recurring payment');
            const response = await this.createRecurringPayment(data);
            
            console.log('Server response:', response);
            
            if (response && response.success) {
                this.showSuccessMessage('Recurring payment created successfully!');
                
                // Reset form
                this.resetForm();
                
                // Reload recurring payments data
                await this.loadRecurringPayments();
                


                // SIMPLE RELOAD: Just reload the current page content
                console.log('Reloading page to show new expenses...');
                setTimeout(() => {
                    window.location.reload();
                });
            }

            else {
                            this.showErrorMessage(response?.message || 'An error occurred while saving');
                        }
                    } catch (error) {
                        console.error('Error in form submission:', error);
                        this.showErrorMessage('Network error occurred while saving');
                    } finally {
                        this.isSubmitting = false;
                        this.setLoadingState(false);
                    }
                }
    
    parseFormData(formData) {
        const data = {};
        
        data.amount = formData.get('amount');
        data.category_id = formData.get('category_id');
        data.category_description = formData.get('category_description');
        data.user_id = formData.get('user_id');
        data.frequency = formData.get('frequency');
        data.interval_value = formData.get('interval_value');
        data.start_date = formData.get('start_date');
        data.end_date = formData.get('end_date');
        data.is_active = formData.get('is_active') === 'true';
        
        // Participants
        const participantIds = formData.getAll('participant_ids');
        data.participant_ids = participantIds;
        
        return data;
    }
    
    validateForm(data) {
        const errors = [];
        
        if (!data.amount || parseFloat(data.amount) <= 0) {
            errors.push('Amount must be greater than 0');
        }
        
        if (!data.category_id) {
            errors.push('Category is required');
        }
        
        if (!data.user_id) {
            errors.push('Payer is required');
        }
        
        if (!data.frequency) {
            errors.push('Frequency is required');
        }
        
        if (!data.start_date) {
            errors.push('Start date is required');
        }
        
        if (data.participant_ids.length === 0) {
            errors.push('At least one participant must be selected');
        }
        
        if (data.end_date && new Date(data.end_date) < new Date(data.start_date)) {
            errors.push('End date must be after start date');
        }
        
        if (errors.length > 0) {
            this.showErrorMessage(errors.join('\n'));
            return false;
        }
        
        return true;
    }
    
    async createRecurringPayment(data) {
        const response = await fetch(window.urls.recurringPaymentsApi, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(data)
        });
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        
        return await response.json();
    }
    
    // NEW METHOD: Immediate refresh without delays
        refreshMainTableImmediate() {
            console.log('Refreshing main expense table immediately...');
            
            let refreshSuccess = false;
            
            try {
                // Method 1: Try to reload the entire expenses section via fetch
                const expensesTableContainer = document.querySelector('.expenses-section, #expenses-table-container, .expenses-table');
                if (expensesTableContainer && !refreshSuccess) {
                    console.log('Found expenses table container, attempting to reload...');
                    
                    // Look for a reload URL or try common endpoints
                    const reloadUrl = '/expenses/table' || window.location.pathname;
                    fetch(reloadUrl)
                        .then(response => response.text())
                        .then(html => {
                            // Parse the HTML to get just the table part
                            const tempDiv = document.createElement('div');
                            tempDiv.innerHTML = html;
                            const newTable = tempDiv.querySelector('table tbody, .expenses-table tbody');
                            const currentTable = document.querySelector('table tbody, .expenses-table tbody');
                            
                            if (newTable && currentTable) {
                                currentTable.innerHTML = newTable.innerHTML;
                                console.log('Successfully updated expense table via fetch');
                                refreshSuccess = true;
                                
                                // Re-trigger the expense filter to attach listeners
                                if (window.expenseFilter && window.expenseFilter.handleFilterChange) {
                                    setTimeout(() => window.expenseFilter.handleFilterChange(), 100);
                                }
                            }
                        })
                        .catch(error => console.log('Fetch reload failed:', error));
                }
                
                // Method 2: Trigger a page refresh of just the expenses data
                if (window.location.pathname.includes('expenses') || window.location.pathname === '/') {
                    console.log('Attempting to reload current page data...');
                    
                    // Make an AJAX call to get fresh expense data
                    fetch(window.location.pathname)
                        .then(response => response.text())
                        .then(html => {
                            const parser = new DOMParser();
                            const doc = parser.parseFromString(html, 'text/html');
                            const newTableBody = doc.querySelector('table tbody, .expenses-table tbody');
                            const currentTableBody = document.querySelector('table tbody, .expenses-table tbody');
                            
                            if (newTableBody && currentTableBody) {
                                currentTableBody.innerHTML = newTableBody.innerHTML;
                                console.log('Successfully refreshed table content');
                                refreshSuccess = true;
                                
                                // Re-run any initialization scripts
                                setTimeout(() => {
                                    // Re-trigger expense filter
                                    if (window.expenseFilter) {
                                        window.expenseFilter.handleFilterChange();
                                    }
                                    
                                    // Re-trigger settlement manager
                                    if (window.settlementManager) {
                                        window.settlementManager.attachEditingListeners();
                                    }
                                }, 200);
                            }
                        })
                        .catch(error => console.log('Page reload failed:', error));
                }
                
                // Method 3: Force a browser refresh as last resort (with confirmation)
                if (!refreshSuccess) {
                    setTimeout(() => {
                        console.log('All refresh methods failed, the table will update on next page load');
                        // Don't force refresh automatically, but log that manual refresh is needed
                    }, 2000);
                }
                
            } catch (error) {
                console.error('Error refreshing main table:', error);
            }
}
    
    // MISSING METHOD - This was causing the inline editing to not work!
    setupInlineEditing() {
        console.log('Setting up inline editing...');
        
        if (!this.tableBody) {
            console.error('Table body not found for inline editing setup');
            return;
        }
        
        // Remove existing event listeners to prevent duplicates
        this.tableBody.removeEventListener('click', this.handleTableClick);
        
        // Add click event listener for inline editing
        this.handleTableClick = (e) => {
            const cell = e.target.closest('.editable');
            if (cell && !cell.querySelector('input, select, div[style*="border"]')) {
                console.log('Clicked editable cell:', cell.className);
                this.startEditCell(cell);
            }
        };
        
        this.tableBody.addEventListener('click', this.handleTableClick);
        
        console.log('Inline editing setup complete');
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
        
        console.log('Editing cell type:', type, 'current value:', currentValue);
        
        const input = this.createInputForType(type, currentValue, cell);
        
        // Handle participants differently (no blur event)
        if (type === 'participants') {
            cell.setAttribute('data-original-html', originalHTML);
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
        
        const saveEdit = () => this.saveInlineEdit(cell, input, type, originalHTML);
        const cancelEdit = () => this.cancelInlineEdit(cell, originalHTML);
        
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
            input.addEventListener('change', saveEdit);
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
                
            case 'frequency':
                input = document.createElement('select');
                const frequencies = [
                    { value: 'daily', label: 'Daily' },
                    { value: 'weekly', label: 'Weekly' },
                    { value: 'monthly', label: 'Monthly' },
                    { value: 'yearly', label: 'Yearly' }
                ];
                frequencies.forEach(freq => {
                    const option = document.createElement('option');
                    option.value = freq.value;
                    option.textContent = freq.label;
                    option.selected = freq.value === currentValue;
                    input.appendChild(option);
                });
                break;
                
            case 'interval_value':
                input = document.createElement('input');
                input.type = 'number';
                input.min = '1';
                input.value = parseInt(currentValue || '1');
                break;
                
            case 'start_date':
            case 'end_date':
            case 'next_due_date':
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
                
            case 'is_active':
                input = document.createElement('select');
                const activeOptions = [
                    { value: 'true', label: 'Active' },
                    { value: 'false', label: 'Inactive' }
                ];
                activeOptions.forEach(opt => {
                    const option = document.createElement('option');
                    option.value = opt.value;
                    option.textContent = opt.label;
                    option.selected = opt.value === currentValue;
                    input.appendChild(option);
                });
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
        
        // Checkboxes for each user
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
        
        // Buttons
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
            
            container._selectedParticipants = selectedIds;
            this.handleParticipantsSave(container, cell);
        });
        
        cancelBtn.addEventListener('click', (e) => {
            e.preventDefault();
            e.stopPropagation();
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
        select.appendChild(placeholder);
        
        // Data options
        data.forEach(item => {
            const option = document.createElement('option');
            option.value = item.id;
            option.textContent = item.name;
            option.selected = item.id.toString() === currentValue.toString();
            select.appendChild(option);
        });
    }
    
    async saveInlineEdit(cell, input, type, originalHTML) {
        const row = cell.closest('tr');
        const recurringPaymentId = row.getAttribute('data-recurring-id');
        
        if (!recurringPaymentId) {
            this.showErrorMessage('Error: No recurring payment ID found');
            cell.innerHTML = originalHTML;
            return;
        }
        
        let newValue, data = {};
        
        if (type === 'participants') {
            // Handle participants editing
            const container = input;
            return; // Participants handled separately
        } else {
            // Handle other field types
            newValue = input.value.trim();
            
            // Validation
            if (type === 'amount') {
                const numValue = parseFloat(newValue);
                if (isNaN(numValue) || numValue <= 0) {
                    this.showErrorMessage('Amount must be a positive number');
                    cell.innerHTML = originalHTML;
                    return;
                }
                newValue = numValue;
            }
            
            if (type === 'interval_value') {
                const intValue = parseInt(newValue);
                if (isNaN(intValue) || intValue < 1) {
                    this.showErrorMessage('Interval must be a positive number');
                    cell.innerHTML = originalHTML;
                    return;
                }
                newValue = intValue;
            }
            
            if (!newValue && type !== 'description' && type !== 'end_date') {
                this.showErrorMessage(`${type} cannot be empty`);
                cell.innerHTML = originalHTML;
                return;
            }
            
            // Map form field names to data keys
            const fieldMap = {
                'user': 'user_id',
                'category': 'category_id',
                'description': 'category_description',
                'is_active': 'is_active'
            };
            
            const dataKey = fieldMap[type] || type;
            
            // Handle special cases
            if (type === 'is_active') {
                data[dataKey] = newValue === 'true';
            } else {
                data[dataKey] = newValue;
            }
            
            await this.performInlineSave(cell, data, recurringPaymentId, type, originalHTML, input, newValue);
        }
    }
    
    async performInlineSave(cell, data, recurringPaymentId, type, originalHTML, input, newValue) {
        // Show loading state
        if (input.disabled !== undefined) {
            input.disabled = true;
            input.style.backgroundColor = '#f0f0f0';
        }
        
        try {
            console.log('Updating recurring payment:', recurringPaymentId, 'with data:', data);
            
            const response = await fetch(`${window.urls.recurringPaymentsApi}/${recurringPaymentId}`, {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(data)
            });
            
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            const result = await response.json();
            
            if (result.success) {
                // Update display based on type
                this.updateCellDisplay(cell, type, newValue);
                this.showMessage('Updated successfully!', 'green');
            } else {
                this.showMessage(result.message || 'Update failed', 'red');
                cell.innerHTML = originalHTML;
            }
        } catch (error) {
            console.error('Error updating recurring payment:', error);
            this.showMessage('Network error: ' + error.message, 'red');
            cell.innerHTML = originalHTML;
        }
    }
    
    updateCellDisplay(cell, type, newValue) {
        switch (type) {
            case 'amount':
                const numValue = parseFloat(newValue);
                cell.innerHTML = `$${numValue.toFixed(2)}`;
                cell.setAttribute('data-value', numValue.toFixed(2));
                break;
                
            case 'frequency':
                const frequencyLabels = {
                    'daily': 'Daily',
                    'weekly': 'Weekly', 
                    'monthly': 'Monthly',
                    'yearly': 'Yearly'
                };
                cell.innerHTML = `<span class="frequency-display">${frequencyLabels[newValue] || newValue}</span>`;
                cell.setAttribute('data-value', newValue);
                break;
                
            case 'is_active':
                const isActive = newValue === true || newValue === 'true';
                cell.innerHTML = `<span class="status-badge ${isActive ? 'status-active' : 'status-inactive'}">${isActive ? 'Active' : 'Inactive'}</span>`;
                cell.setAttribute('data-value', newValue);
                break;
                
            case 'start_date':
            case 'end_date':
            case 'next_due_date':
                if (newValue) {
                    cell.innerHTML = this.formatDate(newValue);
                } else {
                    // If it's the sentinel date or null/empty
                    cell.innerHTML = type === 'end_date' ? 'Never' : '';
                }

                // Store the actual value including the sentinel for backend consistency
                cell.setAttribute('data-value', newValue);
                break;
                
            case 'user':
                const user = this.usersData.find(u => u.id.toString() === newValue.toString());
                cell.innerHTML = user ? user.name : newValue;
                cell.setAttribute('data-value', newValue);
                break;
                
            case 'category':
                const category = this.categoriesData.find(c => c.id.toString() === newValue.toString());
                cell.innerHTML = category ? category.name : newValue;
                cell.setAttribute('data-value', newValue);
                break;
                
            default:
                cell.innerHTML = newValue || '';
                cell.setAttribute('data-value', newValue);
        }
    }
    
    cancelInlineEdit(cell, originalHTML) {
        cell.innerHTML = originalHTML;
    }
    
    async handleParticipantsSave(container, cell) {
        const selectedIds = container._selectedParticipants || [];
        
        if (selectedIds.length === 0) {
            this.showMessage('At least one participant is required', 'red');
            return;
        }
        
        const row = cell.closest('tr');
        const recurringPaymentId = row.getAttribute('data-recurring-id');
        const data = { participant_ids: selectedIds };
        
        try {
            const response = await fetch(`${window.urls.recurringPaymentsApi}/${recurringPaymentId}`, {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(data)
            });
            
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            const result = await response.json();
            
            if (result.success) {
                this.showMessage('Participants updated successfully!', 'green');
                // Reload the table to show updated participant info
                await this.loadRecurringPayments();
            } else {
                this.showMessage(result.message || 'Update failed', 'red');
                this.handleParticipantsCancel(container, cell);
            }
        } catch (error) {
            console.error('Error updating participants:', error);
            this.showMessage('Network error: ' + error.message, 'red');
            this.handleParticipantsCancel(container, cell);
        }
    }
    
    handleParticipantsCancel(container, cell) {
        const originalHTML = cell.getAttribute('data-original-html');
        if (originalHTML) {
            cell.innerHTML = originalHTML;
        } else {
            this.loadRecurringPayments();
        }
    }
    
    async deleteRecurringPayment(id) {
        if (!confirm('Are you sure you want to delete this recurring payment?')) {
            return;
        }
        
        try {
            const response = await fetch(`${window.urls.recurringPaymentsApi}/${id}`, {
                method: 'DELETE'
            });
            
            const result = await response.json();
            
            if (result.success) {
                this.showSuccessMessage('Recurring payment deleted successfully');
                await this.loadRecurringPayments();
            } else {
                this.showErrorMessage(result.message || 'Error deleting recurring payment');
            }
        } catch (error) {
            console.error('Error deleting recurring payment:', error);
            this.showErrorMessage('Error deleting recurring payment');
        }
    }
    
    async loadRecurringPayments() {
        try {
            const response = await fetch(window.urls.getRecurringPaymentsApi);
            const data = await response.json();
            
            if (data.success) {
                this.renderRecurringPaymentsTable(data.recurring_payments);
                // Set up inline editing after rendering
                setTimeout(() => this.setupInlineEditing(), 200);
            } else {
                console.error('Error loading recurring payments:', data.message);
            }
        } catch (error) {
            console.error('Error loading recurring payments:', error);
        }
    }
    
    renderRecurringPaymentsTable(recurringPayments) {
        if (!this.tableBody) return;
        
        if (recurringPayments.length === 0) {
            this.tableBody.innerHTML = `
                <tr>
                    <td colspan="10" class="empty-state">
                        <div class="empty-state-icon">🔄</div>
                        <div class="empty-state-text">No recurring payments found</div>
                        <div class="empty-state-subtext">Create your first recurring payment above</div>
                    </td>
                </tr>
            `;
            return;
        }
        
        this.tableBody.innerHTML = recurringPayments.map(payment => {
            const nextDueDate = new Date(payment.next_due_date);
            const today = new Date();
            const dueDateClass = this.getDueDateClass(nextDueDate, today);
            
            return `
                <tr data-recurring-id="${payment.id}">
                    <td class="editable category" data-value="${payment.category_id}" title="Click to edit category">
                        <strong>${this.escapeHtml(payment.category_name)}</strong>
                        ${payment.category_description ? `<br><small class="editable description" data-value="${this.escapeHtml(payment.category_description)}" title="Click to edit description">${this.escapeHtml(payment.category_description)}</small>` : ''}
                    </td>
                    <td class="editable amount" data-value="${payment.amount}" title="Click to edit amount">$${parseFloat(payment.amount).toFixed(2)}</td>
                    <td class="editable user" data-value="${payment.user_id}" title="Click to edit payer">${this.escapeHtml(payment.user_name)}</td>
                    <td class="editable frequency" data-value="${payment.frequency}" title="Click to edit frequency">
                        <span class="frequency-display">
                            ${this.formatFrequency(payment.frequency, payment.interval_value)}
                        </span>
                    </td>
                    <td class="editable start_date" data-value="${payment.start_date}" title="Click to edit start date">${this.formatDate(payment.start_date)}</td>
                    <td class="editable end_date" data-value="${payment.end_date || ''}" title="Click to edit end date">${payment.end_date ? this.formatDate(payment.end_date) : 'Never'}</td>
                    <td class="editable next_due_date" data-value="${payment.next_due_date}" title="Click to edit next due date">
                        <span class="due-date ${dueDateClass}">
                            ${this.formatDate(payment.next_due_date)}
                        </span>
                    </td>
                    <td class="editable is_active" data-value="${payment.is_active}" title="Click to edit status">
                        <span class="status-badge ${payment.is_active ? 'status-active' : 'status-inactive'}">
                            ${payment.is_active ? 'Active' : 'Inactive'}
                        </span>
                    </td>
                    <td class="editable participants" data-participant-ids="${(payment.participant_ids || []).join(',')}" title="Click to edit participants">
                        <div class="participants-display">
                            ${payment.participants && payment.participants.length > 0 ? payment.participants.join(', ') : 'All users'}
                        </div>
                    </td>
                    <td>
                        <button class="action-btn delete-btn" onclick="recurringPaymentsManager.deleteRecurringPayment(${payment.id})">
                            Delete
                        </button>
                        ${payment.is_active ? `
                            <button class="action-btn process-btn" onclick="recurringPaymentsManager.processPayment(${payment.id})"
                                    title="Process this payment now to create an expense">
                                Process
                            </button>
                        ` : ''}
                    </td>
                </tr>
            `;
        }).join('');
    }
    
    async processPayment(id) {
        if (!confirm('Process this recurring payment now? This will create a new expense for today.')) {
            return;
        }
        
        try {
            const response = await fetch(`${window.urls.recurringPaymentsApi}/${id}/process`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                }
            });
            
            const result = await response.json();
            
            if (result.success) {
                this.showSuccessMessage('Recurring payment processed successfully! Expense created for today.');
                await this.loadRecurringPayments();
                
                // IMMEDIATE REFRESH: Also refresh main table when processing a payment
                this.refreshMainTableImmediate();
            } else {
                this.showErrorMessage(result.message || 'Error processing payment');
            }
            setTimeout(() => {
                window.location.reload();
            });
        } catch (error) {
            console.error('Error processing payment:', error);
            this.showErrorMessage('Error processing payment');
        }
    }
    
    resetForm() {
        this.isSubmitting = false;
        
        if (this.form) {
            this.form.reset();
        }
        
        // Reset form title and button
        const title = document.getElementById('recurring-form-title');
        if (title) title.textContent = 'Add New Recurring Payment';
        
        const submitBtn = document.getElementById('recurring-submit-btn');
        if (submitBtn) {
            submitBtn.textContent = 'Add Recurring Payment';
            submitBtn.disabled = false;
        }
        
        // Hide interval group
        const intervalGroup = document.getElementById('interval-group');
        if (intervalGroup) intervalGroup.style.display = 'none';
        
        // Clear all checkboxes
        if (this.form) {
            this.form.querySelectorAll('[name="participant_ids"]').forEach(checkbox => {
                checkbox.checked = false;
            });
        }
    }
    
    handleFrequencyChange(event) {
        const frequency = event.target.value;
        const intervalGroup = document.getElementById('interval-group');
        const intervalLabel = document.getElementById('interval-label');
        
        if (frequency && intervalGroup && intervalLabel) {
            intervalGroup.style.display = 'block';
            
            switch (frequency) {
                case 'daily':
                    intervalLabel.textContent = 'Every X days';
                    break;
                case 'weekly':
                    intervalLabel.textContent = 'Every X weeks';
                    break;
                case 'monthly':
                    intervalLabel.textContent = 'Every X months';
                    break;
                case 'yearly':
                    intervalLabel.textContent = 'Every X years';
                    break;
                default:
                    intervalLabel.textContent = 'Interval';
            }
        }
    }
    
    // Utility methods
    getDueDateClass(nextDueDate, today) {
        const diffTime = nextDueDate - today;
        const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));
        
        if (diffDays <= 0) return 'due-today';
        if (diffDays <= 7) return 'due-soon';
        return '';
    }
    
    formatFrequency(frequency, intervalValue) {
        const interval = intervalValue || 1;
        
        if (interval === 1) {
            return frequency.charAt(0).toUpperCase() + frequency.slice(1);
        }
        
        return `Every ${interval} ${frequency}`;
    }
    
    formatDate(dateString) {
        if (!dateString) return '';

        // Split YYYY-MM-DD into parts
        const [year, month, day] = dateString.split('-').map(Number);

        // Create a Date object using local time
        const date = new Date(year, month - 1, day);

        // Format as "Sep 9, 2025"
        return date.toLocaleDateString('en-US', {
            month: 'short',
            day: 'numeric',
            year: 'numeric'
        });
    }
    
    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
    
    setLoadingState(loading) {
        const submitBtn = document.getElementById('recurring-submit-btn');
        if (submitBtn) {
            if (loading) {
                submitBtn.disabled = true;
                submitBtn.innerHTML = '<span class="spinner"></span> Saving...';
            } else {
                submitBtn.disabled = false;
                submitBtn.innerHTML = 'Add Recurring Payment';
            }
        }
    }
    
    showSuccessMessage(message) {
        this.showMessage(message, 'green');
    }
    
    showErrorMessage(message) {
        this.showMessage(message, 'red');
    }
    
    showMessage(message, color = 'black') {
        // Create a temporary floating message
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

// Global functions for template onclick handlers
function openRecurringPaymentsModal() {
    const modal = document.getElementById('recurringPaymentsModal');
    if (modal) {
        modal.style.display = 'block';
        
        if (window.recurringPaymentsManager) {
            window.recurringPaymentsManager.loadRecurringPayments();
        }
    }
}

function handleFrequencyChange(selectElement) {
    if (window.recurringPaymentsManager) {
        window.recurringPaymentsManager.handleFrequencyChange({ target: selectElement });
    }
}

function toggleAllRecurringParticipants() {
    const checkboxes = document.querySelectorAll('#recurring-participants-list input[name="participant_ids"]');
    const allChecked = Array.from(checkboxes).every(cb => cb.checked);
    
    checkboxes.forEach(checkbox => {
        checkbox.checked = !allChecked;
    });
}

function resetRecurringForm() {
    if (window.recurringPaymentsManager) {
        window.recurringPaymentsManager.resetForm();
    }
}

// Initialize when DOM is ready - ensure single initialization
if (!window.recurringPaymentsManager) {
    document.addEventListener('DOMContentLoaded', () => {
        if (!window.recurringPaymentsManager) {
            window.recurringPaymentsManager = new RecurringPaymentsManager();
        }
    });
}

// ADDITIONAL: Listen for custom refresh events from other parts of the app
document.addEventListener('expenseTableRefresh', (event) => {
    console.log('Received expenseTableRefresh event:', event.detail);
    
    // If the main expense table manager exists, refresh it
    if (window.expenseTableManager && typeof window.expenseTableManager.loadExpenses === 'function') {
        console.log('Refreshing expense table via event listener');
        window.expenseTableManager.loadExpenses();
    }
});