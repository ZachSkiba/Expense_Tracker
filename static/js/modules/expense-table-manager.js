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
        if (this.errorElement) {
            this.errorElement.style.color = color;
            this.errorElement.innerHTML = message;
            setTimeout(() => {
                this.errorElement.innerHTML = '';
            }, 8000);
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
                if (window.loadBalancesData) window.loadBalancesData();
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
        
        const input = this.createInputForType(type, currentValue);
        
        // Style the input
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
    
    createInputForType(type, currentValue) {
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
        
        // Manage option
        const manageOpt = document.createElement('option');
        manageOpt.value = 'manage';
        manageOpt.textContent = `➕ Add/Remove ${type.charAt(0).toUpperCase() + type.slice(1)}s`;
        select.appendChild(manageOpt);
    }
    
    async saveEdit(cell, input, type, originalHTML, autocomplete) {
        // Clean up autocomplete
        if (autocomplete && autocomplete.cleanup) {
            autocomplete.cleanup();
        }
        
        const newValue = input.value.trim();
        const row = cell.closest('tr');
        const expenseId = row.getAttribute('data-expense-id');
        
        // Validation
        if (type === 'amount') {
            const numValue = parseFloat(newValue);
            if (isNaN(numValue) || numValue <= 0) {
                this.showMessage('Amount must be a positive number', 'red');
                cell.innerHTML = originalHTML;
                return;
            }
        }
        
        if (!newValue && type !== 'description') {
            this.showMessage(`${type} cannot be empty`, 'red');
            cell.innerHTML = originalHTML;
            return;
        }
        
        // Prepare data
        const data = {};
        data[type === 'user' ? 'user' : type] = type === 'amount' ? parseFloat(newValue) : newValue;
        
        // Show loading state
        input.disabled = true;
        input.style.backgroundColor = '#f0f0f0';
        
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
                // Update display
                if (type === 'amount') {
                    const numValue = parseFloat(newValue);
                    cell.innerHTML = `$${numValue.toFixed(2)}`;
                    cell.setAttribute('data-value', numValue.toFixed(2));
                } else {
                    cell.innerHTML = newValue || '';
                    cell.setAttribute('data-value', newValue);
                }
                this.showMessage('Updated successfully!', 'green');

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
    
    cancelEdit(cell, originalHTML, autocomplete) {
        if (autocomplete && autocomplete.cleanup) {
            autocomplete.cleanup();
        }
        cell.innerHTML = originalHTML;
    }
}

// Export for use
window.ExpenseTableManager = ExpenseTableManager;