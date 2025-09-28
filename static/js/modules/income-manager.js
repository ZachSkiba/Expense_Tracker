/**
 * Income Manager - Handles income tracking functionality
 */

class IncomeManager {
    constructor() {
        this.form = document.getElementById('income-form');
        this.tableBody = document.getElementById('income-entries-table-body');
        this.table = document.querySelector('.income-entries-table');
        this.isSubmitting = false;
        this.lastSubmissionTime = 0;
        
        this.incomeCategoriesData = this.getDataFromScript('income-categories-data');
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
        this.loadIncomeCategories().then(() => {
            this.loadIncomeEntries();
        });
    }
    
    bindEvents() {
        if (this.form) {
            this.form.addEventListener('submit', (e) => {
                e.preventDefault();
                e.stopImmediatePropagation();
                this.handleSubmit();
                return false;
            });
            
            const submitBtn = document.getElementById('income-submit-btn');
            if (submitBtn) {
                submitBtn.addEventListener('click', (e) => {
                    e.preventDefault();
                    e.stopImmediatePropagation();
                    this.handleSubmit();
                    return false;
                });
            }
        }
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
        console.log('Starting income form submission...');
        
        const formData = new FormData(this.form);
        const data = this.parseFormData(formData);
        
        // Validate form
        if (!this.validateForm(data)) {
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

            console.log('CREATING new income entry');
            const response = await this.createIncomeEntry(data, groupId);
            
            console.log('Server response:', response);
            
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
        data.income_category_id = formData.get('income_category_id');
        data.description = formData.get('description');
        data.user_id = formData.get('user_id');
        data.date = formData.get('date');
        
        return data;
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
        const response = await fetch(`/api/income/entries/${groupId}`, {
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

    async loadIncomeCategories() {
        try {
            const groupId = window.groupId;
            const response = await fetch(`/api/income/categories/${groupId}`);
            const data = await response.json();
            
            if (data.success) {
                this.incomeCategoriesData = data.income_categories;
                this.populateIncomeCategorySelect();
            } else {
                console.error('Error loading income categories:', data.message);
            }
        } catch (error) {
            console.error('Error loading income categories:', error);
        }
    }

    populateIncomeCategorySelect() {
        const select = this.form ? this.form.querySelector('[name="income_category_id"]') : null;
        if (!select) return;

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
        });
    }

    async loadIncomeEntries() {
        try {
            const groupId = window.groupId;
            const response = await fetch(`/api/income/entries/${groupId}`);
            const data = await response.json();
            
            if (data.success) {
                this.renderIncomeEntriesTable(data.income_entries);
                setTimeout(() => this.setupInlineEditing(), 200);
            } else {
                console.error('Error loading income entries:', data.message);
            }
        } catch (error) {
            console.error('Error loading income entries:', error);
        }
    }

    renderIncomeEntriesTable(incomeEntries) {
        console.log('[DEBUG] renderIncomeEntriesTable called with:', incomeEntries);
        console.log('[DEBUG] Table body element:', this.tableBody);
        
        if (!this.tableBody) {
            console.error('[ERROR] Income table body element not found!');
            return;
        }
        
        if (!incomeEntries || incomeEntries.length === 0) {
            console.log('[DEBUG] No income entries to display');
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
        
        console.log('[DEBUG] Rendering income table with', incomeEntries.length, 'entries');
        
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
                        <button class="income-action-btn income-delete-btn" onclick="incomeManager.deleteIncomeEntry(${entry.id})">
                            Delete
                        </button>
                    </td>
                </tr>
            `;
        }).join('');
        
        console.log('[DEBUG] Income table HTML updated, rows added:', incomeEntries.length);
    }

    setupInlineEditing() {
        console.log('Setting up income inline editing...');
        
        if (!this.tableBody) {
            console.error('Income table body not found for inline editing setup');
            return;
        }
        
        // Remove existing event listeners to prevent duplicates
        this.tableBody.removeEventListener('click', this.handleTableClick);
        
        // Add click event listener for inline editing
        this.handleTableClick = (e) => {
            const cell = e.target.closest('.editable');
            if (cell && !cell.querySelector('input, select')) {
                console.log('Clicked editable income cell:', cell.className);
                this.startEditCell(cell);
            }
        };
        
        this.tableBody.addEventListener('click', this.handleTableClick);
        
        console.log('Income inline editing setup complete');
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
        
        console.log('Editing income cell type:', type, 'current value:', currentValue);
        
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
            console.log('Updating income entry:', incomeEntryId, 'with data:', data);
            
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
            console.error('Error updating income entry:', error);
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
            console.error('Error deleting income entry:', error);
            this.showErrorMessage('Error deleting income entry');
        }
    }

    resetForm() {
        this.isSubmitting = false;
        
        if (this.form) {
            this.form.reset();
        }
        
        const submitBtn = document.getElementById('income-submit-btn');
        if (submitBtn) {
            submitBtn.textContent = 'Add Income Entry';
            submitBtn.disabled = false;
        }
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

// Global functions for template onclick handlers
function openIncomeModal() {
    const modal = document.getElementById('incomeModal');
    if (modal) {
        modal.style.display = 'block';
        
        if (window.incomeManager) {
            window.incomeManager.loadIncomeEntries();
        }
    }
}

function resetIncomeForm() {
    if (window.incomeManager) {
        window.incomeManager.resetForm();
    }
}

// Initialize when DOM is ready - ensure single initialization
if (!window.incomeManager) {
    document.addEventListener('DOMContentLoaded', () => {
        if (!window.incomeManager) {
            window.incomeManager = new IncomeManager();
        }
    });
}