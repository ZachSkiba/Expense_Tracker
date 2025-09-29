/**
 * Income Manager - Handles income tracking functionality
 * UPDATED: Fixed initialization and category loading
 */

class IncomeManager {
    constructor() {
        this.form = document.getElementById('income-form');
        this.tableBody = document.getElementById('income-entries-table-body');
        this.table = document.querySelector('.income-entries-table');
        this.isSubmitting = false;
        this.lastSubmissionTime = 0;
        
        // Get data from template scripts - fallback to window data
        this.incomeCategoriesData = this.getDataFromScript('income-categories-data') || [];
        this.usersData = this.getDataFromScript('users-data') || window.usersData || [];
        this.allocationEnabled = false;

        
        console.log('[INCOME_MANAGER] Initializing with data:', {
            categories: this.incomeCategoriesData.length,
            users: this.usersData.length,
            form: !!this.form,
            tableBody: !!this.tableBody
        });
        
        this.init();
    }
    
    getDataFromScript(id) {
        try {
            const script = document.getElementById(id);
            if (script && script.textContent.trim()) {
                return JSON.parse(script.textContent);
            }
        } catch (e) {
            console.warn(`Error parsing ${id}:`, e);
        }
        return [];
    }
    
    init() {
        // Always try to load categories first
        this.loadIncomeCategories().then(() => {
            console.log('[INCOME_MANAGER] Categories loaded, now binding events');
            this.bindEvents();
            // Only load entries if we have a table
            if (this.tableBody) {
                this.loadIncomeEntries();
            }
        }).catch(error => {
            console.error('[INCOME_MANAGER] Error during initialization:', error);
            // Still bind events even if category loading fails
            this.bindEvents();
        });
    }
    
    bindEvents() {
        if (this.form) {
            // Remove existing listeners to prevent duplicates
            const existingHandler = this.form.onsubmit;
            if (existingHandler) {
                this.form.removeEventListener('submit', existingHandler);
            }
            
            // Add submit handler
            this.form.addEventListener('submit', (e) => {
                e.preventDefault();
                e.stopImmediatePropagation();
                this.handleSubmit();
                return false;
            });
            
            const submitBtn = document.getElementById('income-submit-btn');
            if (submitBtn) {
                // Remove existing click handler
                submitBtn.onclick = null;
                submitBtn.addEventListener('click', (e) => {
                    e.preventDefault();
                    e.stopImmediatePropagation();
                    this.handleSubmit();
                    return false;
                });
            }
            
            console.log('[INCOME_MANAGER] Event handlers bound successfully');
        } else {
            console.warn('[INCOME_MANAGER] No income form found, skipping event binding');
        }
    }
    
    handleSubmit() {
        const currentTime = Date.now();
        
        // Prevent rapid successive clicks (within 2 seconds)
        if (currentTime - this.lastSubmissionTime < 2000) {
            console.log('[INCOME_MANAGER] BLOCKED: Submission too soon after last one');
            return;
        }
        
        // Prevent if already submitting
        if (this.isSubmitting) {
            console.log('[INCOME_MANAGER] BLOCKED: Already submitting');
            return;
        }
        
        this.lastSubmissionTime = currentTime;
        this.handleFormSubmit();
    }
    
    async handleFormSubmit() {
        console.log('[INCOME_MANAGER] Starting income form submission...');
        
        const formData = new FormData(this.form);
        const data = this.parseFormData(formData);
        
        console.log('[INCOME_MANAGER] Form data parsed:', data);
        
        // Validate form
        if (!this.validateFormWithAllocations(data)) {
            return;
        }

        const groupId = window.groupId;
        if (!groupId) {
            this.showErrorMessage('Group ID not found. Please refresh the page.');
            return;
        }

        try {
            this.isSubmitting = true;
            this.setLoadingState(true);

            console.log('[INCOME_MANAGER] CREATING new income entry for group:', groupId);
            const response = await this.createIncomeEntry(data, groupId);
            
            console.log('[INCOME_MANAGER] Server response:', response);
            
            if (response && response.success) {
                this.showSuccessMessage('Income entry created successfully!');
                
                // Reset form
                this.resetForm();
                
                // Reload income entries data
                await this.loadIncomeEntries();
            } else {
                this.showErrorMessage(response?.message || 'An error occurred while saving');
            }
        } catch (error) {
            console.error('[INCOME_MANAGER] Error in form submission:', error);
            this.showErrorMessage('Network error occurred while saving: ' + error.message);
        } finally {
            this.isSubmitting = false;
            this.setLoadingState(false);
        }
    }
    
    parseFormData(formData) {
        const data = {};
        
        data.amount = formData.get('amount');
        data.income_category_id = formData.get('income_category_id');
        data.description = formData.get('description');
        data.user_id = formData.get('user_id');
        data.date = formData.get('date');

        const allocationEnabled = document.getElementById('enable-allocation')?.checked;
        if (allocationEnabled) {
            data.allocations = this.parseAllocationData();
        }
        
        return data;
    }

    // ADD this new method:
    parseAllocationData() {
        const allocations = [];
        const entries = document.querySelectorAll('#allocation-entries .allocation-entry');
        
        entries.forEach(entry => {
            const categoryId = entry.querySelector('select[name="allocation_category_id[]"]')?.value;
            const amount = entry.querySelector('input[name="allocation_amount[]"]')?.value;
            const notes = entry.querySelector('input[name="allocation_notes[]"]')?.value;
            
            if (categoryId && amount && parseFloat(amount) > 0) {
                allocations.push({
                    allocation_category_id: parseInt(categoryId),
                    amount: parseFloat(amount),
                    notes: notes?.trim() || null
                });
            }
        });
        
        return allocations;
}
    
    validateForm(data) {
        const errors = [];
        
        if (!data.amount || parseFloat(data.amount) <= 0) {
            errors.push('Amount must be greater than 0');
        }
        
        if (!data.income_category_id) {
            errors.push('Income category is required');
        }
        
        if (!data.user_id) {
            errors.push('User is required');
        }
        
        if (!data.date) {
            errors.push('Date is required');
        }
        
        if (errors.length > 0) {
            this.showErrorMessage(errors.join('\n'));
            return false;
        }
        
        return true;
    }

    async createIncomeEntry(data, groupId) {
        const url = `/api/income/entries/${groupId}`;
        console.log('[INCOME_MANAGER] Making POST request to:', url);
        
        const response = await fetch(url, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(data)
        });
        
        if (!response.ok) {
            const errorText = await response.text();
            console.error('[INCOME_MANAGER] HTTP Error:', response.status, errorText);
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        
        return await response.json();
    }

    async loadIncomeCategories() {
        try {
            const groupId = window.groupId;
            if (!groupId) {
                console.error('[INCOME_MANAGER] No group ID available for loading categories');
                return;
            }
            
            const url = `/api/income/categories/${groupId}`;
            console.log('[INCOME_MANAGER] Loading income categories from:', url);
            
            const response = await fetch(url);
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
            const data = await response.json();
            console.log('[INCOME_MANAGER] Categories API response:', data);
            
            if (data.success) {
                this.incomeCategoriesData = data.income_categories;
                console.log('[INCOME_MANAGER] Loaded categories:', this.incomeCategoriesData);
                this.populateIncomeCategorySelect();
            } else {
                console.error('[INCOME_MANAGER] Error loading income categories:', data.message);
                this.showErrorMessage('Failed to load income categories: ' + data.message);
            }
        } catch (error) {
            console.error('[INCOME_MANAGER] Error loading income categories:', error);
            this.showErrorMessage('Error loading income categories: ' + error.message);
        }
    }

    populateIncomeCategorySelect() {
        const select = this.form ? this.form.querySelector('[name="income_category_id"]') : null;
        if (!select) {
            console.warn('[INCOME_MANAGER] No income category select found');
            return;
        }

        console.log('[INCOME_MANAGER] Populating category select with', this.incomeCategoriesData.length, 'categories');

        // Clear existing options except the first placeholder
        while (select.children.length > 1) {
            select.removeChild(select.lastChild);
        }

        // Add income categories
        this.incomeCategoriesData.forEach(category => {
            const option = document.createElement('option');
            option.value = category.id;
            option.textContent = category.name;
            select.appendChild(option);
            console.log('[INCOME_MANAGER] Added category option:', category.name, category.id);
        });
        
        console.log('[INCOME_MANAGER] Category select populated, total options:', select.children.length);
    }

    async loadIncomeEntries() {
        try {
            const groupId = window.groupId;
            if (!groupId) {
                console.error('[INCOME_MANAGER] No group ID available for loading entries');
                return;
            }
            
            const url = `/api/income/entries/${groupId}`;
            console.log('[INCOME_MANAGER] Loading income entries from:', url);
            
            const response = await fetch(url);
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
            const data = await response.json();
            console.log('[INCOME_MANAGER] Entries API response:', data);
            
            if (data.success) {
                this.renderIncomeEntriesTable(data.income_entries);
                setTimeout(() => this.setupInlineEditing(), 200);
            } else {
                console.error('[INCOME_MANAGER] Error loading income entries:', data.message);
                this.showErrorMessage('Failed to load income entries: ' + data.message);
            }
        } catch (error) {
            console.error('[INCOME_MANAGER] Error loading income entries:', error);
            this.showErrorMessage('Error loading income entries: ' + error.message);
        }
    }

    renderIncomeEntriesTable(incomeEntries) {
        console.log('[INCOME_MANAGER] renderIncomeEntriesTable called with:', incomeEntries?.length, 'entries');
        console.log('[INCOME_MANAGER] Table body element:', this.tableBody);
        
        if (!this.tableBody) {
            console.error('[INCOME_MANAGER] Income table body element not found!');
            return;
        }
        
        if (!incomeEntries || incomeEntries.length === 0) {
            console.log('[INCOME_MANAGER] No income entries to display');
            this.tableBody.innerHTML = `
                <tr>
                    <td colspan="6" class="income-empty-state">
                        <div class="income-empty-state-icon">💰</div>
                        <div class="income-empty-state-text">No income entries found</div>
                        <div class="income-empty-state-subtext">Add your first income entry above</div>
                    </td>
                </tr>
            `;
            return;
        }
        
        console.log('[INCOME_MANAGER] Rendering income table with', incomeEntries.length, 'entries');
        
        this.tableBody.innerHTML = incomeEntries.map(entry => {
            return `
                <tr data-income-id="${entry.id}">
                    <td class="editable income_category_id" data-value="${entry.income_category_id}" title="Click to edit category">
                        <span class="income-category-display">${this.escapeHtml(entry.income_category_name)}</span>
                    </td>
                    <td class="editable amount" data-value="${entry.amount}" title="Click to edit amount">
                        <span class="income-amount">+$${parseFloat(entry.amount).toFixed(2)}</span>
                    </td>
                    <td class="editable description" data-value="${entry.description || ''}" title="Click to edit description">
                        ${entry.description ? this.escapeHtml(entry.description) : '<em>No description</em>'}
                    </td>
                    <td class="editable user_id" data-value="${entry.user_id}" title="Click to edit user">
                        ${this.escapeHtml(entry.user_name)}
                    </td>
                    <td class="editable date" data-value="${entry.date}" title="Click to edit date">
                        ${this.formatDate(entry.date)}
                    </td>
                    <td>
                    <button class="income-action-btn view-allocations-btn" onclick="window.incomeAllocationManager.viewAllocations(${entry.id})">
                        View Allocations
                    </button>
                    <button class="income-action-btn income-delete-btn" onclick="window.incomeManager.deleteIncomeEntry(${entry.id})">
                        Delete
                    </button>
                </td>
                </tr>
            `;
        }).join('');
        
        console.log('[INCOME_MANAGER] Income table HTML updated, rows added:', incomeEntries.length);
    }

    setupInlineEditing() {
        console.log('[INCOME_MANAGER] Setting up income inline editing...');
        
        if (!this.tableBody) {
            console.error('[INCOME_MANAGER] Income table body not found for inline editing setup');
            return;
        }
        
        // Remove existing event listeners to prevent duplicates
        if (this.handleTableClick) {
            this.tableBody.removeEventListener('click', this.handleTableClick);
        }
        
        // Add click event listener for inline editing
        this.handleTableClick = (e) => {
            const cell = e.target.closest('.editable');
            if (cell && !cell.querySelector('input, select')) {
                console.log('[INCOME_MANAGER] Clicked editable income cell:', cell.className);
                this.startEditCell(cell);
            }
        };
        
        this.tableBody.addEventListener('click', this.handleTableClick);
        
        console.log('[INCOME_MANAGER] Income inline editing setup complete');
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
        
        console.log('[INCOME_MANAGER] Editing income cell type:', type, 'current value:', currentValue);
        
        const input = this.createInputForType(type, currentValue, cell);
        
        // Style the input
        input.style.width = '100%';
        input.style.border = '2px solid #27ae60';
        input.style.padding = '4px';
        input.style.boxSizing = 'border-box';
        
        // Replace content with input
        cell.innerHTML = '';
        cell.appendChild(input);
        input.focus();
        
        const saveEdit = () => this.saveInlineEdit(cell, input, type, originalHTML);
        const cancelEdit = () => this.cancelInlineEdit(cell, originalHTML);
        
        // Event listeners
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
        
        if (type === 'income_category_id' || type === 'user_id') {
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
                input.placeholder = 'Optional description';
                input.autocomplete = 'off';
                break;
                
            case 'date':
                input = document.createElement('input');
                input.type = 'date';
                input.value = currentValue;
                break;
                
            case 'income_category_id':
                input = document.createElement('select');
                this.populateSelect(input, this.incomeCategoriesData, currentValue, 'income category');
                break;
                
            case 'user_id':
                input = document.createElement('select');
                this.populateSelect(input, this.usersData, currentValue, 'user');
                break;
                
            default:
                input = document.createElement('input');
                input.type = 'text';
                input.value = currentValue;
        }
        
        return input;
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
        const incomeEntryId = row.getAttribute('data-income-id');
        
        if (!incomeEntryId) {
            this.showErrorMessage('Error: No income entry ID found');
            cell.innerHTML = originalHTML;
            return;
        }
        
        let newValue = input.value.trim();
        let data = {};
        
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
        
        if (!newValue && type !== 'description') {
            this.showErrorMessage(`${type} cannot be empty`);
            cell.innerHTML = originalHTML;
            return;
        }
        
        // Map form field names to data keys
        const fieldMap = {
            'user_id': 'user_id',
            'income_category_id': 'income_category_id',
            'description': 'description'
        };
        
        const dataKey = fieldMap[type] || type;
        data[dataKey] = newValue;
        
        await this.performInlineSave(cell, data, incomeEntryId, type, originalHTML, input, newValue);
    }

    async performInlineSave(cell, data, incomeEntryId, type, originalHTML, input, newValue) {
        // Show loading state
        if (input.disabled !== undefined) {
            input.disabled = true;
            input.style.backgroundColor = '#f0f0f0';
        }
        
        try {
            console.log('[INCOME_MANAGER] Updating income entry:', incomeEntryId, 'with data:', data);
            
            const groupId = window.groupId;
            const response = await fetch(`/api/income/entries/${groupId}/${incomeEntryId}`, {
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
            console.error('[INCOME_MANAGER] Error updating income entry:', error);
            this.showMessage('Network error: ' + error.message, 'red');
            cell.innerHTML = originalHTML;
        }
    }

    updateCellDisplay(cell, type, newValue) {
        switch (type) {
            case 'amount':
                const numValue = parseFloat(newValue);
                cell.innerHTML = `<span class="income-amount">+$${numValue.toFixed(2)}</span>`;
                cell.setAttribute('data-value', numValue.toFixed(2));
                break;
                
            case 'date':
                cell.innerHTML = this.formatDate(newValue);
                cell.setAttribute('data-value', newValue);
                break;
                
            case 'user_id':
                const user = this.usersData.find(u => u.id.toString() === newValue.toString());
                cell.innerHTML = user ? user.name : newValue;
                cell.setAttribute('data-value', newValue);
                break;
                
            case 'income_category_id':
                const category = this.incomeCategoriesData.find(c => c.id.toString() === newValue.toString());
                cell.innerHTML = `<span class="income-category-display">${category ? category.name : newValue}</span>`;
                cell.setAttribute('data-value', newValue);
                break;
                
            case 'description':
                cell.innerHTML = newValue ? this.escapeHtml(newValue) : '<em>No description</em>';
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

    async deleteIncomeEntry(id) {
        if (!confirm('Are you sure you want to delete this income entry?')) {
            return;
        }
        
        try {
            const groupId = window.groupId;
            const response = await fetch(`/api/income/entries/${groupId}/${id}`, {
                method: 'DELETE'
            });
            
            const result = await response.json();
            
            if (result.success) {
                this.showSuccessMessage('Income entry deleted successfully');
                await this.loadIncomeEntries();
            } else {
                this.showErrorMessage(result.message || 'Error deleting income entry');
            }
        } catch (error) {
            console.error('[INCOME_MANAGER] Error deleting income entry:', error);
            this.showErrorMessage('Error deleting income entry');
        }
    }


    resetForm() {
    this.isSubmitting = false;
    
    if (this.form) {
        this.form.reset();
    }
    
    // Close and reset allocation section
    const enableAllocationCheckbox = document.getElementById('enable-allocation');
    if (enableAllocationCheckbox) {
        enableAllocationCheckbox.checked = false;
    }
    
    const allocationEntries = document.getElementById('allocation-entries');
    if (allocationEntries) {
        allocationEntries.classList.remove('show');
        
        // Remove all allocation entries except the first one
        const entries = allocationEntries.querySelectorAll('.allocation-entry');
        entries.forEach((entry, index) => {
            if (index === 0) {
                // Clear the first entry's values
                entry.querySelector('select[name="allocation_category_id[]"]').value = '';
                entry.querySelector('input[name="allocation_amount[]"]').value = '';
                entry.querySelector('input[name="allocation_notes[]"]').value = '';
            } else {
                // Remove all other entries
                entry.remove();
            }
        });
    }
    
    const submitBtn = document.getElementById('income-submit-btn');
    if (submitBtn) {
        submitBtn.textContent = 'Add Income Entry';
        submitBtn.disabled = false;
    }
    
    console.log('[INCOME_MANAGER] Form reset completed');
}

    validateFormWithAllocations(data) {
    // First do regular validation
    if (!this.validateForm(data)) {
        return false;
    }
    
    // If allocations are enabled, validate them
    const allocationEnabled = document.getElementById('enable-allocation')?.checked;
    if (allocationEnabled) {
        const incomeAmount = parseFloat(data.amount);
        const allocations = data.allocations || [];
        
        if (allocations.length === 0) {
            this.showErrorMessage('Please add at least one allocation or disable allocation tracking');
            return false;
        }
        
        // Check total allocation amount doesn't exceed income
        const totalAllocated = allocations.reduce((sum, allocation) => sum + allocation.amount, 0);
        if (totalAllocated > incomeAmount) {
            this.showErrorMessage(`Total allocated ($${totalAllocated.toFixed(2)}) cannot exceed income amount ($${incomeAmount.toFixed(2)})`);
            return false;
        }
    }
    
    return true;

    }

    // Utility methods
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
        const submitBtn = document.getElementById('income-submit-btn');
        if (submitBtn) {
            if (loading) {
                submitBtn.disabled = true;
                submitBtn.innerHTML = '<span class="spinner"></span> Saving...';
            } else {
                submitBtn.disabled = false;
                submitBtn.innerHTML = 'Add Income Entry';
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

// Initialize when DOM is ready - ensure single initialization
if (!window.incomeManager) {
    // Don't auto-initialize here - let main.js handle it
    console.log('[INCOME_MANAGER] Class definition loaded, waiting for main.js initialization');
}

// Make IncomeManager available globally
window.IncomeManager = IncomeManager;